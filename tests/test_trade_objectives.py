"""Club objectives in trades: stances, dated payrolls, untouchables, the acceptance floor and the search filter."""
from pathlib import Path
import unittest

from runtime.gm import FrontOffice
from runtime.market import Market
from runtime.trades import (ACCEPT_FLOOR, SEARCH_MIN_ACCEPT, UNTOUCHABLE_MARGIN, TradeDesk, acceptance)

ROOT = Path(__file__).resolve().parents[1]
DAY = "2003-11-12"


def trade(partner, outs, ins, picks_out=()):
    return {"partner": partner, "miami_out": list(outs), "miami_in": list(ins), "picks_out": list(picks_out), "picks_in": []}


class AcceptanceTests(unittest.TestCase):
    def test_below_the_floor_is_a_flat_no_and_a_flat_deal_is_usually_passed(self):
        self.assertIsNone(acceptance({"objective_gain": ACCEPT_FLOOR - 0.01, "untouchable": []}))
        self.assertLess(acceptance({"objective_gain": 0.0, "untouchable": []}), 0.5)
        self.assertGreater(acceptance({"objective_gain": 0.15, "untouchable": []}), 0.85)

    def test_an_untouchable_needs_a_clear_margin(self):
        held = [("Star", "top-ten pick on his rookie scale")]
        self.assertIsNone(acceptance({"objective_gain": UNTOUCHABLE_MARGIN - 0.01, "untouchable": held}))
        self.assertIsNotNone(acceptance({"objective_gain": UNTOUCHABLE_MARGIN + 0.01, "untouchable": held}))


class LiveDeskTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.desk = TradeDesk(DAY, FrontOffice(DAY, Market(DAY, ROOT), ROOT), ROOT)

    def test_young_top_picks_are_kept(self):
        for partner, outs, star in (("Phoenix Suns", ["Caron Butler"], "Amare Stoudemire"),
                                    ("Memphis Grizzlies", ["Caron Butler", "Rasual Butler"], "Pau Gasol")):
            packet, why = self.desk.acceptance_packet(trade(partner, outs, [star]))
            self.assertIsNone(packet)
            self.assertIn(f"keeps {star}", why[0])

    def test_a_club_losing_on_its_own_objective_says_no_without_a_draw(self):
        packet, why = self.desk.acceptance_packet(trade("Toronto Raptors", ["Rasual Butler", "Sean Lampley"], ["Michael Bradley"]))
        self.assertIsNone(packet)
        self.assertIn("below its floor", why[0])

    def test_miami_values_this_season_while_it_tries_to_win(self):
        v = self.desk.valuation(trade("San Antonio Spurs", ["Eddie Jones"], ["Malik Rose"]))
        self.assertLess(v["miami_gain"], 0)

    def test_partner_payroll_is_the_dated_roster_with_summer_terms(self):
        spurs = self.desk.assets.contracts["San Antonio Spurs"]["players"]
        duncan = next(p for p in spurs if p["player"] == "Tim Duncan")
        self.assertEqual(duncan["terms_source"], "reported total, spread flat")
        self.assertGreater(self.desk.assets.payroll("San Antonio Spurs"), 45000000)
        self.assertEqual(self.desk.assets.posture("San Antonio Spurs"), "contending")

    def test_the_search_offers_only_what_the_partner_would_take(self):
        for f in self.desk.search(limit=20):
            self.assertGreaterEqual(f["accept"], SEARCH_MIN_ACCEPT)
            self.assertGreaterEqual(f["partner_gain"], ACCEPT_FLOOR)
            self.assertGreater(f["miami_gain"], 0)
            v = self.desk.valuation(f["trade"])
            self.assertTrue(not v["untouchable"] or v["objective_gain"] >= UNTOUCHABLE_MARGIN)


if __name__ == "__main__":
    unittest.main()
