"""Roadmap 15a: honors move a player's price, and a contract's incentive clauses are judged from dated records."""
from pathlib import Path
import unittest

from runtime import valuation as V
from runtime.incentives import evaluate_clause
from runtime.playoff_stats import pages, page_errors

ROOT = Path(__file__).resolve().parents[1]


class HonorPremiumTests(unittest.TestCase):
    def setUp(self):
        self.v = object.__new__(V.Valuation)
        self.v.honors = {"a": ["All-NBA First Team", "Rookie of the Year"], "b": ["Most Valuable Player", "All-NBA First Team",
                         "Finals MVP", "Defensive Player of the Year"], "c": []}

    def test_largest_counts_in_full_the_rest_at_a_quarter(self):
        self.assertAlmostEqual(self.v.honor_factor("a"), 1 + 0.25 + 0.25 * 0.05)
        self.assertAlmostEqual(self.v.honor_factor("c"), 1.0)
        self.assertAlmostEqual(self.v.honor_factor("nobody"), 1.0)

    def test_premium_is_capped(self):
        self.assertAlmostEqual(self.v.honor_factor("b"), 1 + V.HONOR_CAP)

    def test_weekly_and_monthly_honors_carry_no_premium(self):
        self.assertNotIn("Eastern Conference Player of the Week", V.HONOR_PREMIUM)

    def test_honors_count_only_once_announced(self):
        before = V.Valuation("2004-04-14", ROOT)
        self.assertEqual(before.honors, {})


class IncentiveTests(unittest.TestCase):
    def clause(self, kind, text):
        return {"id": "x", "kind": kind, "classification": "unlikely", "benchmarks": {"2003-04": text}, "amounts": {"2003-04": 1}}

    def test_minutes_and_honor_benchmarks_read_the_record(self):
        self.assertEqual(evaluate_clause(self.clause("performance", "At least 1,200 regular-season minutes played."),
                                         "2003-04", "2004-04-28", ROOT)["status"], "met")
        self.assertEqual(evaluate_clause(self.clause("performance", "At least 99,999 regular-season minutes played."),
                                         "2003-04", "2004-04-28", ROOT)["status"], "not_met")
        self.assertEqual(evaluate_clause(self.clause("performance", "Selection to an NBA All-Rookie Team."),
                                         "2003-04", "2004-04-19", ROOT)["status"], "not_met")    # announced April 27

    def test_unreadable_benchmark_is_unrecorded_not_assumed(self):
        self.assertEqual(evaluate_clause(self.clause("performance", "Team reaches the conference finals."),
                                         "2003-04", "2004-04-28", ROOT)["status"], "unrecorded")


class PlayoffStatsTests(unittest.TestCase):
    def test_pages_are_fresh_and_playoff_only(self):
        self.assertEqual(page_errors(ROOT), [])
        built = pages(ROOT)
        if built:
            team = next(t for p, t in built.items() if p.name == "Team_Playoff_Stats.md")
            self.assertIn("Playoff games only", team)


if __name__ == "__main__":
    unittest.main()
