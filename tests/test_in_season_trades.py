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



class ScoreTests(unittest.TestCase):
    def desk(self, flex):
        d = trades.TradeDesk.__new__(trades.TradeDesk)
        d.flexibility = lambda outs, ins, club: flex
        return d

    def test_later_room_counts_and_a_request_softens_a_loss(self):
        d = self.desk(0.5)
        v = {"miami_gain": -0.2}
        plain = d.scored_gain(v, ["A"], ["B"], "P")
        self.assertAlmostEqual(plain, -0.2 + trades.CAP_FLEXIBILITY_WEIGHT * 0.5)
        wanted = d.scored_gain(v, ["A"], ["B"], "P", wanted={"B"}, standing="franchise")
        self.assertGreater(wanted, plain)          # closer to zero, never turned into a gain
        self.assertLess(wanted, 0)


class RookieRestrictionTests(unittest.TestCase):
    def test_a_partner_rookie_waits_thirty_days_not_until_december(self):
        d = trades.TradeDesk.__new__(trades.TradeDesk)
        d.on, d.season = "2004-08-05", "2004-05"
        d.cba = {"trades": {"signed_first_round_pick_restriction_days": {"days": 30}}}
        d.signings = {"r": {"date": "2004-07-01", "kind": "rookie_signing"}, "v": {"date": "2004-07-20", "kind": "signing"}}
        self.assertIsNone(d.partner_blocked("P", {"bbr_id": "r"}))
        self.assertIn("2004-12-15", d.partner_blocked("P", {"bbr_id": "v"}))


if __name__ == "__main__":
    unittest.main()
