import hashlib
import json
import statistics
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from runtime import KERNEL_VERSION, private_service
from runtime.boxscore import render
from runtime.game_requests import request_errors
from runtime.era import allowed_game_types, environment_for, rules_for, season_for_date
from runtime.game_runner import architecture_errors, build_game_packet
from runtime.kernel import PlayerInput, TeamInput, resolve_game, validate_result
from runtime.league import baseline_team, load_clubs
from runtime.private_service import Store, handler, play_requests

ROOT = Path(__file__).resolve().parents[1]
TOKEN = "t" * 40
GAME_DATE = "2003-10-28"


def neutral_team(team_id):
    minutes = [34, 34, 34, 34, 34, 18, 16, 12, 12, 8, 4, 0]
    positions = ["PG", "SG", "SF", "PF", "C", "PG", "SG", "SF", "PF", "C", "SF", "C"]
    return TeamInput(team_id, tuple(PlayerInput(f"{team_id}_{i}", positions[i], minutes[i]) for i in range(12)))


class EraTests(unittest.TestCase):
    def test_2003_04_rules(self):
        rules = rules_for("2003-04")
        self.assertEqual(rules["game_day_actives"], 12)
        self.assertEqual(rules["first_round_best_of"], 7)
        self.assertFalse(rules["hand_check_emphasis"])
        self.assertNotIn("play_in", allowed_game_types("2003-04"))

    def test_unencoded_season_fails_closed(self):
        with self.assertRaises(ValueError):
            rules_for("2004-05")

    def test_environment_is_prior_season_and_date_gated(self):
        env = environment_for("2003-04", GAME_DATE)
        self.assertEqual(env["season"], "2002-03")
        with self.assertRaises(ValueError):
            environment_for("2003-04", "2003-04-01")

    def test_league_year_boundary(self):
        self.assertEqual(season_for_date("2003-06-26"), "2002-03")
        self.assertEqual(season_for_date("2003-10-28"), "2003-04")
        self.assertEqual(season_for_date("2004-04-14"), "2003-04")


class KernelTests(unittest.TestCase):
    rules = rules_for("2003-04")
    env = environment_for("2003-04", GAME_DATE)

    def play(self, entropy, home=None, away=None, venue="home"):
        return resolve_game(home or neutral_team("H"), away or neutral_team("A"), entropy=entropy,
                            event_id="test", rules=self.rules, environment=self.env, venue=venue)

    def test_deterministic_and_valid(self):
        first = self.play(b"x" * 32)
        self.assertEqual(first, self.play(b"x" * 32))
        self.assertNotEqual(first["final_score"], self.play(b"y" * 32)["final_score"])
        self.assertEqual(validate_result(first), [])

    def test_era_calibration(self):
        totals = {}
        for i in range(300):
            result = self.play(hashlib.sha256(str(i).encode()).digest(), venue="neutral")
            self.assertEqual(validate_result(result), [])
            for side in ("home", "away"):
                for key, value in result["team_stats"][side].items():
                    totals.setdefault(key, []).append(value)
        averages = self.env["averages"]
        for key, target, tolerance in (("pts", averages["points"], 0.03), ("fga", averages["fga"], 0.03),
                                       ("tpa", averages["three_pa"], 0.06), ("fta", averages["fta"], 0.06),
                                       ("tov", averages["tov"], 0.06), ("orb", averages["orb"], 0.06),
                                       ("ast", averages["ast"], 0.06)):
            with self.subTest(stat=key):
                self.assertAlmostEqual(statistics.mean(totals[key]) / target, 1, delta=tolerance)

    def test_minutes_follow_targets(self):
        result = self.play(b"m" * 32)
        rows = {r["player_id"]: r for r in result["player_stats"]["home"]}
        self.assertEqual(rows["H_11"]["seconds"], 0)
        self.assertGreater(rows["H_0"]["minutes"], rows["H_9"]["minutes"])

    def test_illegal_team_refused(self):
        team = TeamInput("X", neutral_team("X").players + (PlayerInput("extra", "C", 0),))
        with self.assertRaises(ValueError):
            self.play(b"z" * 32, home=team)

    def test_ratings_shift_outcomes(self):
        shooters = TeamInput("S", tuple(PlayerInput(p.player_id, p.position, p.minutes,
                                                    {"three_point_shooting": 75, "mid_range_shooting": 75,
                                                     "rim_finishing": 75}) for p in neutral_team("S").players))
        good = [self.play(hashlib.sha256(b"r%d" % i).digest(), home=shooters, venue="neutral")
                for i in range(60)]
        base = [self.play(hashlib.sha256(b"r%d" % i).digest(), venue="neutral") for i in range(60)]
        self.assertGreater(statistics.mean(r["final_score"]["home"] for r in good),
                           statistics.mean(r["final_score"]["home"] for r in base) + 5)


REQUEST = {
    "event_id": "2003-10-28-orl-at-mia",
    "game_date": GAME_DATE,
    "game_type": "regular",
    "venue": "home",
    "home": {"team": "Miami Heat", "baseline": "library/2003/league/nba_2003_end_of_season.json"},
    "away": {"team": "Orlando Magic", "baseline": "library/2003/league/nba_2003_end_of_season.json"},
}


class EngineHarness(unittest.TestCase):
    """A throwaway repository with the real library and one game request."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "library/2003/league").mkdir(parents=True)
        for name in ("nba_2003_end_of_season.json", "nba_2002_03_league_environment.json"):
            (self.root / "library/2003/league" / name).write_bytes((ROOT / "library/2003/league" / name).read_bytes())
        self.week = self.root / "career/Dwyane_Wade/2003-04/06_Regular_Season/10_October/Week_4"
        self.week.mkdir(parents=True)
        (self.week / "Game_1.md").write_text("---\ntype: game\nstatus: scheduled\n---\n")
        self.write_request(REQUEST)
        self.store = Store(self.root / "data/engine.sqlite3")
        self.store.initialize()
        self.servers = []

    def tearDown(self):
        for server in self.servers:
            server.shutdown()
            server.server_close()
        self.tmp.cleanup()

    def write_request(self, data):
        (self.week / "Game_1.request.json").write_text(json.dumps(data))

    def serve(self, games):
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler(self.store, TOKEN, games))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.servers.append(server)
        return f"http://127.0.0.1:{server.server_address[1]}"

    def get(self, url, token=None):
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        try:
            with urlopen(Request(url, headers=headers)) as response:
                return response.status, response.read().decode()
        except HTTPError as exc:
            return exc.code, exc.read().decode()


class PushToPlayTests(EngineHarness):
    def test_request_is_played_once_and_replayed_identically(self):
        first = play_requests(self.store, self.root)
        self.assertEqual(first[REQUEST["event_id"]]["status"], "played")
        result = self.store.result(REQUEST["event_id"])
        self.assertEqual(validate_result(result), [])
        self.assertEqual(result["calibration"]["baseline_season"], "2002-03")
        second = play_requests(Store(self.root / "data/engine.sqlite3"), self.root)
        self.assertEqual(second[REQUEST["event_id"]]["status"], "already_played")
        self.assertEqual(self.store.result(REQUEST["event_id"]), result)

    def test_edited_request_is_refused_and_result_kept(self):
        play_requests(self.store, self.root)
        original = self.store.result(REQUEST["event_id"])
        self.write_request(dict(REQUEST, venue="neutral"))
        status = play_requests(self.store, self.root)
        entry = next(iter(status.values()))
        self.assertEqual(entry["status"], "error")
        self.assertIn("altered packet refused", entry["error"])
        self.assertEqual(self.store.result(REQUEST["event_id"]), original)

    def test_bad_request_does_not_stop_the_service(self):
        self.write_request(dict(REQUEST, game_type="play_in"))
        entry = next(iter(play_requests(self.store, self.root).values()))
        self.assertEqual(entry["status"], "error")
        self.assertIn("play_in", entry["error"])
        self.assertEqual(len(request_errors(self.root)), 1)

    def test_results_are_public_and_seed_endpoints_are_not(self):
        url = self.serve(play_requests(self.store, self.root))
        status, body = self.get(url + "/games")
        self.assertEqual(status, 200)
        self.assertIn(REQUEST["event_id"], body)
        status, body = self.get(url + "/games/" + REQUEST["event_id"])
        self.assertEqual(json.loads(body)["event_id"], REQUEST["event_id"])
        status, box = self.get(url + "/games/" + REQUEST["event_id"] + "/box")
        self.assertIn("Orlando Magic", box)
        self.assertEqual(self.get(url + "/games/missing")[0], 404)
        self.assertEqual(self.get(url + "/ready")[0], 401)
        status, body = self.get(url + "/ready", TOKEN)
        self.assertTrue(json.loads(body)["ready"])

    def test_seed_survives_restart(self):
        ref = self.store.close_digest("g", "0" * 64)
        restarted = Store(self.root / "data/engine.sqlite3")
        restarted.initialize()
        self.assertEqual(restarted.close_digest("g", "0" * 64), ref)

    def test_kernel_change_is_journaled(self):
        with mock.patch.object(private_service, "KERNEL_VERSION", "2003.2"):
            Store(self.root / "data/engine.sqlite3").initialize()
        self.assertEqual(self.store.kernel_history(), [(KERNEL_VERSION, "2003.2")])

    def test_box_score_renders(self):
        play_requests(self.store, self.root)
        text = render(self.store.result(REQUEST["event_id"]))
        self.assertIn("Miami Heat", text)
        self.assertIn("TEAM", text)


class ArchitectureTests(unittest.TestCase):
    def test_architecture(self):
        self.assertEqual(architecture_errors(), [])

    def test_invalid_packet_fails_before_journal(self):
        team = neutral_team("A")
        with self.assertRaises(ValueError):
            build_game_packet(team, team, event_id="same", game_date=GAME_DATE)

    def test_repository_requests_are_valid(self):
        self.assertEqual(request_errors(ROOT), [])

    def test_engine_image_files(self):
        railway = json.loads((ROOT / "railway.json").read_text())
        self.assertEqual(railway["build"]["dockerfilePath"], "Dockerfile.engine")
        dockerfile = (ROOT / "Dockerfile.engine").read_text()
        self.assertIn("unittest discover", dockerfile)
        self.assertIn("COPY --from=verify /app/career/ career/", dockerfile)
        self.assertNotIn("ENGINE_API_TOKEN=", dockerfile)


if __name__ == "__main__":
    unittest.main()
