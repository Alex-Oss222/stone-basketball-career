"""Club objectives in trades: stances, dated payrolls, untouchables, the acceptance floor and the search filter."""
from pathlib import Path
import unittest

from runtime.gm import FrontOffice
from runtime.market import Market
from runtime.trades import (ACCEPT_FLOOR, INJURY_DISCOUNT, INJURY_FROM, SEARCH_MIN_ACCEPT, UNTOUCHABLE_MARGIN, TradeDesk,
                            acceptance)

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

    def setUp(self):
        # These cases name Miami players as of November 12; the desk reads the live register, so a case whose
        # player has since left Miami no longer describes this test.
        import json
        roster = json.loads((ROOT / "career/Dwyane_Wade/2003-04/00_Team/Team/Roster/roster.json").read_text())
        from runtime.trades import NOT_TRADEABLE_WORDS
        gone = {p["name"] for p in roster["players"] if any(w in (p.get("status") or "") for w in NOT_TRADEABLE_WORDS)}
        named = {"Caron Butler", "Rasual Butler", "Sean Lampley", "Eddie Jones"}
        if named & gone:
            self.skipTest(f"{', '.join(sorted(named & gone))} no longer tradeable on the live register")

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
        # A club trying to win weighs a veteran's current production above his shared (now plus future) value.
        v = self.desk.valuation(trade("San Antonio Spurs", ["Eddie Jones"], ["Malik Rose"]))
        jones = v["miami_out"][0]
        self.assertEqual(jones["age"], 32)                       # aged from Miami's register like every player
        self.assertGreater(v["miami_out_view"], jones["value"])
        self.assertGreater(jones["now"], jones["future"])

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



class DistressAndProofTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.desk = TradeDesk(INJURY_FROM, FrontOffice(INJURY_FROM, Market(INJURY_FROM, ROOT), ROOT), ROOT)

    def test_an_injured_player_counts_less_to_the_club_taking_him_on(self):
        deal = trade("Golden State Warriors", ["Caron Butler"], ["Clifford Robinson"])
        self.desk.assets._injured = set()
        healthy = self.desk.valuation(deal)["partner_gain"]
        self.desk.assets._injured = {("Miami Heat", "Caron Butler")}
        hurt = self.desk.valuation(deal)["partner_gain"]
        del self.desk.assets._injured
        self.assertLess(hurt, healthy)
        self.assertLess(INJURY_DISCOUNT, 0.86)                       # within the 15-40% discount
        self.assertGreater(INJURY_DISCOUNT, 0.59)

    def test_injury_evidence_is_dated_and_only_regulars_who_vanished(self):
        before = TradeDesk("2003-11-30", FrontOffice("2003-11-30", Market("2003-11-30", ROOT), ROOT), ROOT)
        self.assertFalse(before.assets.injured("Caron Butler", "Miami Heat"))     # before the adoption date
        self.assertTrue(self.desk.assets.injured("Caron Butler", "Miami Heat"))   # on Miami's list with an injury
        self.assertFalse(self.desk.assets.injured("Eddie Jones", "Miami Heat"))

    def test_live_search_keeps_untouchables_and_clears_every_partner_floor(self):
        for row in self.desk.search(limit=10):
            v = self.desk.valuation(row["trade"])
            self.assertLessEqual(len(v["untouchable"]), 1)               # never two cornerstones in one deal
            if v["untouchable"]:
                self.assertGreaterEqual(v["objective_gain"], UNTOUCHABLE_MARGIN)   # one only for the margin
            self.assertGreaterEqual(v["objective_gain"], ACCEPT_FLOOR)
            self.assertGreaterEqual(row["accept"], SEARCH_MIN_ACCEPT)


if __name__ == "__main__":
    unittest.main()
