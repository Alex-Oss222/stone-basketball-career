"""Roadmap 18 (season close), 19 (2005 agreement gating) and 14b phase 5 (the 2004-05 opening book)."""
from pathlib import Path
import unittest

from runtime import cba, offseason, season_close

ROOT = Path(__file__).resolve().parents[1]


class AgreementGateTests(unittest.TestCase):
    def test_2005_rules_apply_only_from_ratification(self):
        before, after = cba.rules_on("2005-07-29", ROOT), cba.rules_on(cba.RATIFIED_2005, ROOT)
        self.assertEqual(before["exceptions"]["larry_bird"]["max_years"], 7)
        self.assertEqual(before["exceptions"]["larry_bird"]["raise_percent"], 12.5)
        self.assertEqual(after["exceptions"]["larry_bird"]["max_years"], 6)
        self.assertEqual(after["exceptions"]["larry_bird"]["raise_percent"], 10.5)
        self.assertEqual(after["exceptions"]["non_bird"]["max_years"], 5)
        self.assertEqual(after["exceptions"]["non_bird"]["raise_percent"], 8)
        self.assertEqual(cba.rules(ROOT)["exceptions"]["larry_bird"]["max_years"], 7)      # the file itself is untouched

    def test_terms_checked_under_the_agreement_of_the_date(self):
        caps = {"maximum_salary": {"0_to_6_years": 10_000_000, "7_to_9_years": 12_000_000, "10_plus_years": 14_000_000},
                "exceptions": {"mid_level": 4_917_000, "biennial": 1_600_000}}
        seven = {"schedule": [5_000_000 + i * 500_000 for i in range(7)]}
        self.assertEqual(cba.terms_errors(seven, route="bird", years_of_service=4, prior_salary=None, cap_rules=caps,
                                          cba=cba.rules_on("2004-07-14", ROOT)), [])
        self.assertTrue(cba.terms_errors(seven, route="bird", years_of_service=4, prior_salary=None, cap_rules=caps,
                                         cba=cba.rules_on("2005-08-02", ROOT)))

    def test_2005_06_minimum_scale(self):
        self.assertEqual(cba.minimum_salary(0, "2005-06", ROOT), 398762)
        self.assertEqual(cba.minimum_salary(12, "2005-06", ROOT), 1138500)


class SeasonCloseTests(unittest.TestCase):
    def test_no_close_before_the_finals_are_decided(self):
        if season_close.close_date(ROOT) is None:
            self.assertIsNone(season_close.close(root=ROOT, write=False))

    def test_record_shape(self):
        record = season_close.build(root=ROOT, on="2004-04-28")
        self.assertEqual(record["competitions_closed"], ["regular", "playoff"])
        self.assertEqual(record["regular_season_games_scheduled"], 82)
        self.assertTrue(all(e["status"] in ("met", "not_met", "unrecorded") for e in record["incentive_evaluation"]))


class OpeningBookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.book = offseason.opening_book(ROOT, "2004-04-28")

    def test_every_real_2004_05_player_has_a_club_or_the_pool(self):
        new = offseason.real_clubs("2004-05", ROOT)
        placed = {p["bbr_id"] for players in self.book["clubs"].values() for p in players} | {p["bbr_id"] for p in self.book["pool"]}
        miami = {p["bbr_id"] for p in self.book["not_placed"] if p["club"] == offseason.MIAMI}
        self.assertEqual(set(new) - placed - miami, set())

    def test_rosters_within_the_limit_and_miami_never_placed(self):
        self.assertNotIn(offseason.MIAMI, self.book["clubs"])
        self.assertTrue(all(len(v) <= offseason.ROSTER_MAX for v in self.book["clubs"].values()))

    def test_real_miami_trade_is_skipped(self):
        rows = {p["bbr_id"]: p for players in self.book["clubs"].values() for p in players}
        if "odomla01" in rows:
            self.assertNotEqual(rows["odomla01"]["club"], "Los Angeles Lakers")


if __name__ == "__main__":
    unittest.main()


class NextSeasonExpectationTests(unittest.TestCase):
    def test_wade_profile_uses_only_simulated_evidence(self):
        from runtime.protagonist import build_profile
        profile = build_profile(ROOT, on="2004-04-28")
        wade = profile["players"]["wadedw01"]
        self.assertEqual(wade["season_end_year"], 2005)
        self.assertGreater(wade["sample"]["games"], 0)
        self.assertEqual(set(wade["estimated"]), set(__import__("runtime.player_stats", fromlist=["RATE_KEYS"]).RATE_KEYS))

    def test_real_player_feedback_is_capped_and_excludes_wade(self):
        from runtime.trajectories import feedback_errors
        data = season_close.feedback(ROOT, on="2004-04-14")
        self.assertEqual(feedback_errors(data), [])
        self.assertNotIn("wadedw01", data["players"])
        self.assertEqual((data["from_season"], data["applies_to"]), ("2003-04", "2004-05"))

    def test_2004_05_rating_index_loads_after_the_cutoff_only(self):
        from runtime.player_stats import load_rating_index
        with self.assertRaises(ValueError):
            load_rating_index("2004-04-01", "2004-05", ROOT)
        self.assertIsNotNone(load_rating_index("2004-11-02", "2004-05", ROOT))


class HistoricalWadeExcludedTests(unittest.TestCase):
    def test_real_wade_is_never_in_season_baselines(self):
        import json
        for rel in ("library/2004/league/nba_2003_04_player_stats.json", "library/2004/league/nba_2004_veteran_ratings.json"):
            data = json.loads((ROOT / rel).read_text(encoding="utf-8"))
            ids = {r["bbr_id"] for r in data["records"]} if "records" in data else set(data["players"])
            self.assertNotIn("wadedw01", ids, rel)

    def test_wade_profile_keeps_the_player_profile_traits(self):
        from runtime.protagonist import build_profile
        wade = build_profile(ROOT, on="2004-04-28")["players"]["wadedw01"]
        self.assertIn("paint_pressure", wade["scouting"]["traits"])
        self.assertIn("spatial_weights", wade["style"])


class NextSeasonFolderTests(unittest.TestCase):
    def test_a_season_folder_without_a_state_is_not_live(self):
        """The season close writes 2004-05 expectations before the rollover; the live season stays 2003-04."""
        from runtime import standing
        live = standing.live_folders(ROOT)
        self.assertTrue(all((ROOT / "career/Dwyane_Wade" / f / "current_state.json").is_file() for f in live))
        if (ROOT / "career/Dwyane_Wade/2004-05").is_dir() and not (ROOT / "career/Dwyane_Wade/2004-05/current_state.json").is_file():
            self.assertNotIn("2004-05", live)
