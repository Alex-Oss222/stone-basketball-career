"""Contract options on their deadlines, retirement and availability from real careers, larger league trades."""
import unittest
from pathlib import Path
from types import SimpleNamespace

from runtime import options
from runtime.availability import signable, status

ROOT = Path(__file__).resolve().parents[1]


class AvailabilityTests(unittest.TestCase):
    def test_retired_unavailable_and_available(self):
        self.assertEqual(status("malonka01", "2004-05", ROOT), "retired")       # Karl Malone sat out 2004-05 and retired
        self.assertEqual(status("fishede01", "2004-05", ROOT), "available")
        self.assertEqual(status("mihmch01", "2006-07", ROOT), "unavailable")    # missed that season, played after it
        self.assertEqual(status("boshch01", "2015-16", ROOT), "available")      # past the data, still active at its end
        self.assertFalse(signable("malonka01", "2004-05", ROOT))


class DeadlineTests(unittest.TestCase):
    def test_rookie_options_by_october_31_and_veterans_in_june(self):
        self.assertEqual(options.deadline("team_option", "2005-06", True), "2004-10-31")
        self.assertEqual(options.deadline("team_option", "2005-06", False), "2005-06-29")
        self.assertEqual(options.deadline("player_option", "2005-06", False), "2005-06-29")


class DecideTests(unittest.TestCase):
    def valuation(self, value, age=27):
        return SimpleNamespace(age=lambda b: age, value=lambda b: value, market_price=lambda v, b: v)

    def test_clear_cut_decisions_need_no_draw_and_close_ones_are_drawn(self):
        row = ("Club", "fishede01", "P", "2005-06", "team_option", 1_000_000, True)
        d, packet = options.decide("2004-10-31", row, self.valuation(2_000_000), ROOT)
        self.assertEqual((d["decision"], packet), ("exercise", None))
        d, packet = options.decide("2004-10-31", row, self.valuation(500_000), ROOT)
        self.assertEqual((d["decision"], packet), ("decline", None))
        d, packet = options.decide("2004-10-31", row, self.valuation(1_000_000), ROOT)
        self.assertIsNone(d["decision"])
        self.assertAlmostEqual(packet["options"]["exercise"], 0.5)

    def test_a_retired_player_is_declined_without_a_draw(self):
        row = ("Club", "malonka01", "Karl Malone", "2005-06", "team_option", 1_000_000, False)
        d, packet = options.decide("2005-06-29", row, self.valuation(9_000_000), ROOT)
        self.assertEqual((d["decision"], packet), ("decline", None))

    def test_a_player_option_is_the_player_s_call(self):
        row = ("Club", "fishede01", "P", "2005-06", "player_option", 2_000_000, False)
        d, _ = options.decide("2005-06-29", row, self.valuation(1_000_000), ROOT)   # paid double his worth: he stays
        self.assertEqual(d["decision"], "stay")


class LeagueTradeTests(unittest.TestCase):
    def test_packages_go_up_to_three_for_two(self):
        from runtime import league_trades
        self.assertEqual(league_trades.MAX_PLAYERS, 5)
        self.assertGreaterEqual(league_trades.TRIPLE_CANDIDATES, 3)


if __name__ == "__main__":
    unittest.main()


class DatedHolderTests(unittest.TestCase):
    def test_option_follows_a_traded_contract(self):
        from unittest import mock
        key = (str(ROOT.resolve()), "2005-06-29")
        with mock.patch.dict(options._HOLDERS, {key: {"x01": "Utah Jazz"}}), \
             mock.patch("runtime.rotations.miami_holds", return_value=[]):
            row = ("Boston Celtics", "x01", "Player X", "2005-06", "team_option", 1_000_000, False)
            self.assertEqual(options._dated_holder(row, "2005-06-29", ROOT)[0], "Utah Jazz")
            waived = ("Boston Celtics", "y01", "Player Y", "2005-06", "team_option", 1_000_000, False)
            self.assertEqual(options._dated_holder(waived, "2005-06-29", ROOT)[0], "Boston Celtics")
