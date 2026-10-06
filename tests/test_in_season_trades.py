"""Miami's in-season trades: carried contracts are tradable, packages are keyed without a date, the scan cadence."""
import unittest
from types import SimpleNamespace

from runtime import trades


class BlockTests(unittest.TestCase):
    def desk(self):
        d = trades.TradeDesk.__new__(trades.TradeDesk)
        d.on, d.season = "2004-11-08", "2004-05"
        d.cba = {"trades": {"signed_first_round_pick_restriction_days": {"days": 30, "status": "x"},
                            "newly_signed_free_agent_restriction": {"status": "x"}}}
        return d

    def test_a_contract_carried_over_at_the_rollover_is_not_newly_signed(self):
        d = self.desk()
        self.assertIsNone(d.blocked({"player": "A", "signed_date": "2004-10-01", "route": "existing"}))
        self.assertIn("newly signed", d.blocked({"player": "B", "signed_date": "2004-07-14", "route": "bird"}))

    def test_wade_is_never_traded(self):
        self.assertIn("simulated club", self.desk().blocked({"player": "Dwyane Wade", "route": "rookie_scale"}))


class KeyTests(unittest.TestCase):
    def test_the_same_package_is_the_same_key_in_any_order(self):
        a = {"partner": "P", "miami_out": ["X", "Y"], "miami_in": ["Z"], "picks_out": [{"year": 2005, "round": 1}], "picks_in": []}
        b = dict(a, miami_out=["Y", "X"])
        self.assertEqual(trades.package_key(a), trades.package_key(b))
        self.assertNotEqual(trades.package_key(a), trades.package_key(dict(a, picks_out=[])))


class BudgetTests(unittest.TestCase):
    def test_a_trade_may_not_push_a_season_over_the_ceiling(self):
        d = trades.TradeDesk.__new__(trades.TradeDesk)
        d.fo = SimpleNamespace(payroll_ceiling=lambda: 57)
        d.payroll_after = lambda outs, ins, club: {"2004-05": (52, 56), "2005-06": (36, 58)}
        self.assertFalse(d.within_budget([], [], "P"))
        d.payroll_after = lambda outs, ins, club: {"2004-05": (60, 59)}
        self.assertTrue(d.within_budget([], [], "P"))   # a season already over may come down


if __name__ == "__main__":
    unittest.main()
