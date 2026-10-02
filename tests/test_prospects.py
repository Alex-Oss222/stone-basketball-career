import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from runtime.game_requests import load_request
from runtime.game_runner import run_game
from runtime.player_stats import RATE_KEYS, load_rating_index, read_json
from runtime.prospects import (PROSPECTS_PATH, ROOKIE_MODEL_VERSION, VETERAN_PATH, build_rookie_estimates,
                               rookie_errors)

ROOT = Path(__file__).resolve().parents[1]


class Journal:
    def close_event(self, packet):
        return hashlib.sha256(json.dumps(packet, sort_keys=True).encode()).hexdigest()


class RookieEstimateTests(unittest.TestCase):
    def setUp(self):
        self.prospects = read_json(ROOT / PROSPECTS_PATH)
        self.veterans = read_json(ROOT / VETERAN_PATH)

    def test_generated_file_is_current(self):
        self.assertEqual(rookie_errors(ROOT), [])

    def test_wade_record_matches_profile_totals(self):
        seasons = self.prospects["records"][0]["seasons"]
        totals = {k: sum(s[k] for s in seasons) for k in ("games", "minutes", "points", "rebounds", "assists",
                                                           "steals", "blocks", "turnovers")}
        self.assertEqual(totals, {"games": 98, "minutes": 3178, "points": 1753, "rebounds": 539,
                                  "assists": 467, "steals": 173, "blocks": 99, "turnovers": 276})

    def test_estimates_sit_between_translation_and_baseline(self):
        wade = build_rookie_estimates(self.prospects, "x", self.veterans)["players"]["wadedw01"]
        base = self.veterans["rate_baselines"]
        for key in RATE_KEYS:
            t, e = wade["translated"][key], wade["estimated"][key]
            if t is None:
                self.assertEqual(e, base[key])
            else:
                self.assertLessEqual(min(t, base[key]) - 1e-12, e)
                self.assertLessEqual(e, max(t, base[key]) + 1e-12)

    def test_unknown_level_and_existing_nba_record_are_refused(self):
        bad = copy.deepcopy(self.prospects)
        bad["records"][0]["level"] = "high_school"
        with self.assertRaises(ValueError):
            build_rookie_estimates(bad, "x", self.veterans)
        bad = copy.deepcopy(self.prospects)
        bad["records"][0]["bbr_id"] = next(iter(self.veterans["players"]))
        with self.assertRaises(ValueError):
            build_rookie_estimates(bad, "x", self.veterans)

    def test_index_returns_rookie_profile(self):
        profile = load_rating_index("2003-10-28", "2003-04", ROOT).engine_profile("Dwyane Wade")
        self.assertEqual(profile["model_version"], ROOKIE_MODEL_VERSION)
        self.assertEqual(set(profile["rates"]), set(RATE_KEYS))

    def test_wade_plays_on_his_estimate(self):
        miami = [("Travis Best", "PG", 30), ("Dwyane Wade", "SG", 34), ("Caron Butler", "SF", 34),
                 ("Malik Allen", "PF", 30), ("Brian Grant", "C", 32), ("Rasual Butler", "SG", 20),
                 ("Eddie House", "PG", 18), ("Sean Lampley", "SF", 12), ("LaPhonso Ellis", "PF", 14),
                 ("Vladimir Stepania", "C", 16)]
        request = {"event_id": "test-wade", "game_date": "2003-10-28", "game_type": "regular", "venue": "home",
                   "home": {"team": "Miami Heat", "players": [{"player_id": n, "position": p, "minutes": m}
                                                              for n, p, m in miami]},
                   "away": {"team": "Philadelphia 76ers", "baseline": "library/2003/league/nba_2003_end_of_season.json"}}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "Game_1.request.json"
            path.write_text(json.dumps(request))
            home, away, kwargs = load_request(path, ROOT)
        wade = next(p for p in home.players if p.player_id == "Dwyane Wade")
        self.assertEqual(wade.stat_profile["model_version"], ROOKIE_MODEL_VERSION)
        result = run_game(home, away, journal=Journal(), **kwargs)
        self.assertTrue(result["terminated"])


if __name__ == "__main__":
    unittest.main()
