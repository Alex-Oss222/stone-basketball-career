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
from runtime.trajectories import (CAREERS_PATH, DEFENSE_SPREAD, FEEDBACK_SHARE, SPREAD, TRAJECTORY_MODEL_VERSION,
                                  apply_feedback, careers_errors, develop, develop_profile, feedback_adjustments,
                                  feedback_errors, feedback_path, load_trajectories, season_feedback, swings,
                                  trajectory_errors)

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
    return {"minutes": minutes, "rates": rates, "dbpm": 1.2}


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

    def test_defense_is_shrunk_dbpm_moved_by_the_swing(self):
        trajectories = load_trajectories(self.root, "2003-04")
        profile = trajectories.expected_profile("jamesle01", "2003-04", BASE)
        self.assertAlmostEqual(profile["defense"], 1.2 * 3100 / 3400)
        ref = hashlib.sha256(b"d").hexdigest()
        moved = develop_profile(profile, {"2003-04": ref})
        self.assertAlmostEqual(moved["defense"] - profile["defense"], DEFENSE_SPREAD * swings({"2003-04": ref})["defense"])
        self.assertEqual(moved["rates"], develop(profile["rates"], {"2003-04": ref}))   # rate draws unchanged

    def test_tampered_defense_is_refused(self):
        home, away, kwargs = self.request()
        journal = Journal()
        players = []
        for p in home.players:
            if p.player_id == "LeBron James":
                refs = {"2003-04": journal.close_event({"event_id": "development:2003-04:jamesle01",
                                                        "procedure": TRAJECTORY_MODEL_VERSION,
                                                        "bbr_id": "jamesle01", "season": "2003-04"})}
                p = replace(p, stat_profile=dict(develop_profile(p.stat_profile, refs), defense=5.0))
            players.append(p)
        with self.assertRaises(ValueError):
            build_game_packet(replace(home, players=tuple(players)), away, **kwargs)

    def test_careers_rows_need_a_valid_dbpm(self):
        for bad in ("1.0", 99, float("nan")):
            row = dict(star_row(), dbpm=bad)
            data = {"kind": "player_career_rates", "players": {"jamesle01": {"seasons": {"2003-04": row}}}}
            self.assertTrue(careers_errors(data), bad)
        careers = read_json(ROOT / CAREERS_PATH)
        self.assertTrue(all("dbpm" in row for p in careers["players"].values() for row in p["seasons"].values()))


class FeedbackTests(unittest.TestCase):
    expected = {k: BASE[k] for k in RATE_KEYS}

    def test_feedback_is_a_capped_share_of_the_shrunk_surprise(self):
        doubled = {k: 2 * v for k, v in self.expected.items()}
        big = feedback_adjustments(self.expected, doubled, {k: 100000 for k in RATE_KEYS})
        for key in RATE_KEYS:
            self.assertAlmostEqual(big[key], min(SPREAD[key], FEEDBACK_SHARE * math.log(2)), places=3)
        small = feedback_adjustments(self.expected, doubled, {k: 5 for k in RATE_KEYS})
        self.assertTrue(all(abs(small[k]) <= abs(big[k]) for k in RATE_KEYS))
        self.assertLess(sum(map(abs, small.values())), sum(map(abs, big.values())))
        missing = feedback_adjustments(self.expected, {k: None for k in RATE_KEYS}, {k: 0 for k in RATE_KEYS})
        self.assertEqual(set(missing.values()), {0.0})
        zero = feedback_adjustments(self.expected, {k: 0.0 for k in RATE_KEYS}, {k: 100000 for k in RATE_KEYS})
        self.assertTrue(all(-SPREAD[k] - 1e-12 <= zero[k] < 0 for k in RATE_KEYS))

    def test_feedback_file_must_be_finite(self):
        adjust = {k: 0.0 for k in RATE_KEYS}
        good = {"kind": "trajectory_feedback", "share": FEEDBACK_SHARE, "players": {"jamesle01": {"adjust": adjust}}}
        self.assertEqual(feedback_errors(good), [])
        for bad in ({"jamesle01": {"adjust": dict(adjust, usage_pct=float("nan"))}}, {"jamesle01": []},
                    {"jamesle01": {"adjust": None}}, {"jamesle01": {"adjust": dict(adjust, usage_pct=10 ** 400)}}):
            self.assertTrue(feedback_errors(dict(good, players=bad)), bad)
        for bad in ([], "x", 3, None):
            self.assertEqual(feedback_errors(bad), ["feedback file must be a JSON object"])

    def test_a_league_wide_level_is_nobodys_surprise(self):
        """If the engine adds threes for everyone, no player's three-point rate is adjusted for it."""
        line = {"seconds": 2160, "fgm": 9, "fga": 18, "tpm": 1, "tpa": 4, "ftm": 6, "fta": 8, "orb": 1, "drb": 5,
                "ast": 7, "stl": 2, "blk": 1, "tov": 3, "pf": 2}
        from runtime.protagonist import observed_rates, season_totals
        per_minute = {"usage": 1, "assists": 1, "offensive_rebounds": 1, "defensive_rebounds": 1, "steals": 1, "blocks": 1}
        observed = observed_rates(season_totals([line] * 70), BASE, per_minute)[0]
        lower = dict(observed, three_point_attempt_rate=observed["three_point_attempt_rate"] * 0.8)
        data = season_feedback({"aaaaa01": [line] * 70, "bbbbb01": [line] * 70}, {"aaaaa01": lower, "bbbbb01": lower},
                               BASE, "2003-04", "2004-05")
        for entry in data["players"].values():
            self.assertAlmostEqual(entry["adjust"]["three_point_attempt_rate"], 0.0, places=9)

    def test_feedback_cannot_spiral(self):
        """A player who keeps beating his real path settles; the adjustment never accumulates past the cap."""
        adjust = {k: 0.0 for k in RATE_KEYS}
        for _ in range(12):
            used = apply_feedback(self.expected, adjust)
            observed = {k: v * 1.5 for k, v in self.expected.items()}
            adjust = feedback_adjustments(used, observed, {k: 100000 for k in RATE_KEYS})
            self.assertTrue(all(abs(adjust[k]) <= SPREAD[k] + 1e-12 for k in RATE_KEYS))

    def test_season_feedback_file_applies_to_the_next_season_only(self):
        line = {"seconds": 2160, "fgm": 9, "fga": 18, "tpm": 1, "tpa": 3, "ftm": 6, "fta": 8, "orb": 1, "drb": 5,
                "ast": 7, "stl": 2, "blk": 1, "tov": 3, "pf": 2}
        bench = dict(line, fgm=3, fga=8, ast=1, ftm=1, fta=2)
        data = season_feedback({"jamesle01": [line] * 70, "wadedw01": [line] * 70, "benchxx01": [bench] * 70},
                               {"jamesle01": self.expected, "benchxx01": self.expected, "wadedw01": self.expected},
                               BASE, "2003-04", "2004-05")
        self.assertNotIn("wadedw01", data["players"])
        self.assertEqual(feedback_errors(data), [])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / CAREERS_PATH).parent.mkdir(parents=True)
            careers = {"schema_version": 1, "kind": "player_career_rates", "source": "synthetic test data",
                       "players": {"jamesle01": {"player_name": "LeBron James",
                                                 "seasons": {"2003-04": star_row(), "2004-05": star_row()}}}}
            (root / CAREERS_PATH).write_text(json.dumps(careers))
            (root / feedback_path("2004-05")).parent.mkdir(parents=True)
            (root / feedback_path("2004-05")).write_text(json.dumps(data))
            plain = load_trajectories(root, "2003-04").expected_profile("jamesle01", "2003-04", BASE)
            self.assertNotIn("feedback_sha256", plain)
            fed = load_trajectories(root, "2004-05").expected_profile("jamesle01", "2004-05", BASE)
            self.assertIn("feedback_sha256", fed)
            unfed = load_trajectories(root, None).expected_profile("jamesle01", "2004-05", BASE)
            self.assertEqual(fed["rates"], apply_feedback(unfed["rates"], data["players"]["jamesle01"]["adjust"]))
            (root / feedback_path("2004-05")).write_text(json.dumps(dict(data, from_season="2002-03")))
            with self.assertRaises(ValueError):
                load_trajectories(root, "2004-05")


if __name__ == "__main__":
    unittest.main()
