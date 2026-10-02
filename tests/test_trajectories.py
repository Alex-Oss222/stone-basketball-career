import hashlib
import json
import math
import shutil
import statistics
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from runtime.game_requests import load_request
from runtime.game_runner import build_game_packet, run_game
from runtime.player_stats import RATE_KEYS, read_json
from runtime.trajectories import (CAREERS_PATH, SPREAD, TRAJECTORY_MODEL_VERSION, careers_errors, develop,
                                  swings, trajectory_errors)

ROOT = Path(__file__).resolve().parents[1]
BASE = read_json(ROOT / "library/2003/league/nba_2003_veteran_ratings.json")["rate_baselines"]


class Journal:
    def __init__(self):
        self.closed = {}

    def close_event(self, packet):
        ref = hashlib.sha256(json.dumps(packet, sort_keys=True).encode()).hexdigest()
        if self.closed.setdefault(packet["event_id"], ref) != ref:
            raise ValueError("altered packet refused")
        return ref


def star_row(minutes=3100):
    rates = {k: BASE[k] for k in RATE_KEYS}
    rates.update(usage_pct=0.28, assist_pct=0.27, two_point_pct=0.44)
    return {"minutes": minutes, "rates": rates}


class TrajectoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        shutil.copytree(ROOT / "library", self.root / "library")
        careers = {"schema_version": 1, "kind": "player_career_rates", "source": "synthetic test data",
                   "players": {"jamesle01": {"player_name": "LeBron James", "seasons": {"2003-04": star_row()}}}}
        (self.root / CAREERS_PATH).parent.mkdir(parents=True, exist_ok=True)
        (self.root / CAREERS_PATH).write_text(json.dumps(careers))

    def tearDown(self):
        self.tmp.cleanup()

    def request(self):
        lineup = [("Kevin Ollie", "PG", 30), ("Ricky Davis", "SG", 34), ("LeBron James", "SF", 38),
                  ("Carlos Boozer", "PF", 34), ("Zydrunas Ilgauskas", "C", 32), ("Jeff McInnis", "PG", 18),
                  ("Darius Miles", "SF", 22), ("DeSagana Diop", "C", 16), ("Chris Mihm", "C", 16)]
        data = {"event_id": "t-cle", "game_date": "2003-10-29", "game_type": "regular", "venue": "home",
                "home": {"team": "Cleveland Cavaliers",
                         "players": [{"player_id": n, "position": p, "minutes": m} for n, p, m in lineup]},
                "away": {"team": "Phoenix Suns", "baseline": "library/2003/league/nba_2003_end_of_season.json"}}
        path = self.root / "Game_1.request.json"
        path.write_text(json.dumps(data))
        return load_request(path, self.root)

    def test_real_career_sets_expected_path_and_engine_draws_swing(self):
        home, away, kwargs = self.request()
        lebron = next(p for p in home.players if p.player_id == "LeBron James")
        self.assertEqual(lebron.stat_profile["model_version"], TRAJECTORY_MODEL_VERSION)
        expected = lebron.stat_profile["rates"]["usage_pct"]
        self.assertGreater(expected, BASE["usage_pct"])      # pulled toward the real 0.28
        journal = Journal()
        result = run_game(home, away, journal=journal, **kwargs)
        self.assertIn("development:2003-04:jamesle01", journal.closed)
        self.assertEqual(result, run_game(home, away, journal=journal, **kwargs))  # replay is identical

    def test_service_redeploy_replays_trajectory_game(self):
        """Regression: the replay check must rebuild the developed packet, not the undeveloped one."""
        from runtime.private_service import Store, play_requests
        week = self.root / "career/X/2003-04/06_Regular_Season/10_October/Week_4"
        week.mkdir(parents=True)
        (week / "Game_1.md").write_text("---\ntype: game\nstatus: scheduled\n---\n")
        self.request()  # writes the request file at the repository root
        (self.root / "Game_1.request.json").rename(week / "Game_1.request.json")
        store = Store(self.root / "data/engine.sqlite3")
        store.initialize()
        self.assertEqual(play_requests(store, self.root)["t-cle"]["status"], "played")
        restarted = Store(self.root / "data/engine.sqlite3")
        restarted.initialize()
        self.assertEqual(play_requests(restarted, self.root)["t-cle"]["status"], "already_played")

    def test_tampered_development_is_refused(self):
        home, away, kwargs = self.request()
        journal = Journal()
        refs = {"2003-04": journal.close_event({"event_id": "development:2003-04:jamesle01", "procedure": TRAJECTORY_MODEL_VERSION,
                                                "bbr_id": "jamesle01", "season": "2003-04"})}
        players = []
        for p in home.players:
            if p.player_id == "LeBron James":
                rates = develop(p.stat_profile["rates"], refs)
                rates["usage_pct"] = 0.40
                p = replace(p, stat_profile=dict(p.stat_profile, rates=rates, development=refs))
            players.append(p)
        with self.assertRaises(ValueError):
            build_game_packet(replace(home, players=tuple(players)), away, **kwargs)

    def test_swings_have_designed_spread_and_persist(self):
        refs = [hashlib.sha256(str(i).encode()).hexdigest() for i in range(4000)]
        first = [swings({"2003-04": r})["usage_pct"] for r in refs]
        self.assertAlmostEqual(statistics.mean(first), 0, delta=0.06)
        self.assertAlmostEqual(statistics.pstdev(first), 1, delta=0.06)
        second = [swings({"2003-04": r, "2004-05": refs[-i - 1]})["usage_pct"] for i, r in enumerate(refs)]
        corr = statistics.correlation(first, second)
        self.assertAlmostEqual(corr, 0.5, delta=0.06)
        moved = develop({k: BASE[k] for k in RATE_KEYS}, {"2003-04": refs[0]})
        for key in RATE_KEYS:
            self.assertLess(abs(math.log(moved[key] / BASE[key])), 5 * SPREAD[key])

    def test_protagonist_cannot_have_a_trajectory(self):
        data = {"kind": "player_career_rates", "players": {"wadedw01": {"player_name": "Dwyane Wade",
                                                                       "seasons": {"2003-04": star_row()}}}}
        self.assertTrue(any("protagonist" in e for e in careers_errors(data)))

    def test_repository_careers_file_is_valid_and_excludes_wade(self):
        self.assertEqual(trajectory_errors(ROOT), [])
        careers = read_json(ROOT / CAREERS_PATH)
        self.assertNotIn("wadedw01", careers["players"])
        self.assertNotIn("wadedw01", json.dumps(careers))
        self.assertEqual(len(careers["players"]["jamesle01"]["seasons"]), 11)

if __name__ == "__main__":
    unittest.main()
