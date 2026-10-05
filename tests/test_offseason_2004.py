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
