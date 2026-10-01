import hashlib
import json
import statistics
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

from runtime import KERNEL_VERSION, private_service
from runtime.era import allowed_game_types, environment_for, rules_for, season_for_date
from runtime.game_runner import architecture_errors, build_game_packet, run_game
from runtime.kernel import PlayerInput, TeamInput, resolve_game, validate_result
from runtime.league import baseline_team, load_clubs
from runtime.private_client import Client, EngineUnavailable
from runtime.private_service import Store, handler

ROOT = Path(__file__).resolve().parents[1]
TOKEN = "t" * 40
SNAPSHOT = "a" * 64
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


class ServiceHarness(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "engine.sqlite3"
        self.servers = []

    def tearDown(self):
        for server in self.servers:
            server.shutdown()
            server.server_close()
        self.tmp.cleanup()

    def serve(self, snapshot=SNAPSHOT):
        store = Store(self.db)
        locked = snapshot if store.initialize(snapshot) else None
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler(store, TOKEN, locked))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.servers.append(server)
        return store, f"http://127.0.0.1:{server.server_address[1]}"


class PrivateServiceTests(ServiceHarness):
    def test_readiness_and_auth(self):
        _, url = self.serve()
        self.assertTrue(Client(url, TOKEN, SNAPSHOT).readiness()["ready"])
        with self.assertRaises(EngineUnavailable):
            Client(url, "wrong" * 10, SNAPSHOT).readiness()

    def test_close_is_idempotent_and_refuses_altered_packets(self):
        _, url = self.serve()
        client = Client(url, TOKEN, SNAPSHOT)
        ref = client.close_event({"event_id": "g1", "x": 1})
        self.assertEqual(ref, client.close_event({"event_id": "g1", "x": 1}))
        with self.assertRaisesRegex(EngineUnavailable, "altered packet"):
            client.close_event({"event_id": "g1", "x": 2})

    def test_seed_survives_restart(self):
        store, _ = self.serve()
        ref = store.close_event("g", "0" * 64)
        self.assertEqual(Store(self.db).close_event("g", "0" * 64), ref)

    def test_new_image_starts_locked_until_advance(self):
        store, _ = self.serve()
        _, url = self.serve("b" * 64)
        client = Client(url, TOKEN, "b" * 64)
        with self.assertRaisesRegex(EngineUnavailable, "locked"):
            client.readiness()
        with self.assertRaisesRegex(EngineUnavailable, "previous snapshot"):
            client.advance_snapshot("c" * 64, "b" * 64, "wrong base")
        client.advance_snapshot(SNAPSHOT, "b" * 64, "draft closed")
        self.assertEqual(client.advance_snapshot(SNAPSHOT, "b" * 64, "draft closed"), "b" * 64)
        self.assertTrue(client.readiness()["ready"])

    def test_kernel_change_is_journaled(self):
        store, _ = self.serve()
        with mock.patch.object(private_service, "KERNEL_VERSION", "2003.2"):
            Store(self.db).initialize(SNAPSHOT)
        self.assertEqual(store.kernel_history(), [(KERNEL_VERSION, "2003.2", SNAPSHOT)])


class GameRunnerTests(ServiceHarness):
    def library_teams(self):
        clubs = load_clubs(ROOT / "library/2003/league/nba_2003_end_of_season.json")
        return (baseline_team("Miami Heat", clubs["Miami Heat"], 12),
                baseline_team("Orlando Magic", clubs["Orlando Magic"], 12))

    def test_architecture(self):
        self.assertEqual(architecture_errors(), [])

    def test_run_game_end_to_end_and_replay(self):
        _, url = self.serve()
        client = Client(url, TOKEN, SNAPSHOT)
        home, away = self.library_teams()
        result = run_game(home, away, event_id="2003-10-28-orl-at-mia", game_date=GAME_DATE, client=client)
        self.assertEqual(result["calibration"]["baseline_season"], "2002-03")
        self.assertEqual(result, run_game(home, away, event_id="2003-10-28-orl-at-mia",
                                          game_date=GAME_DATE, client=client))
        changed = TeamInput(home.team_id, home.players[:-1] + (PlayerInput(home.players[-1].player_id,
                                                                           home.players[-1].position,
                                                                           home.players[-1].minutes,
                                                                           {"usage": 80}),))
        with self.assertRaises(EngineUnavailable):
            run_game(changed, away, event_id="2003-10-28-orl-at-mia", game_date=GAME_DATE, client=client)

    def test_invalid_inputs_never_reach_the_journal(self):
        store, url = self.serve()
        client = Client(url, TOKEN, SNAPSHOT)
        home, away = self.library_teams()
        with self.assertRaisesRegex(ValueError, "play_in"):
            run_game(home, away, event_id="pi", game_date="2004-04-15", game_type="play_in", client=client)
        with self.assertRaises(ValueError):
            build_game_packet(home, home, event_id="same", snapshot=SNAPSHOT, game_date=GAME_DATE)
        with self.assertRaisesRegex(ValueError, "altered|unknown"):
            store.correct("pi", "should not exist")

    def test_engine_image_files_exist(self):
        railway = json.loads((ROOT / "railway.json").read_text())
        self.assertEqual(railway["build"]["dockerfilePath"], "Dockerfile.engine")
        self.assertEqual(railway["deploy"]["healthcheckPath"], "/health")
        dockerfile = (ROOT / "Dockerfile.engine").read_text()
        self.assertIn("unittest discover", dockerfile)
        self.assertNotIn("ENGINE_API_TOKEN=", dockerfile)


if __name__ == "__main__":
    unittest.main()
