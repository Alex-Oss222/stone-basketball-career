"""Offers other clubs make to Miami (TradeDesk.offers): each a gain for the club, never Wade, Miami's answer by rule."""
import unittest
from pathlib import Path

from runtime.gm import FrontOffice
from runtime.season_market import for_date
from runtime.trades import IN_SEASON_MIN_GAIN, OFFER_MIN_GAIN, TradeDesk

ROOT = Path(__file__).resolve().parents[1]
DAY = "2004-11-23"


class OfferTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.desk = TradeDesk(DAY, FrontOffice(DAY, for_date(DAY, ROOT), ROOT), ROOT)
        cls.offers = cls.desk.offers([], "starter")

    def test_each_club_offers_at_most_once_for_its_own_gain(self):
        clubs = [o["trade"]["partner"] for o in self.offers]
        self.assertEqual(len(clubs), len(set(clubs)))
        for o in self.offers:
            self.assertGreaterEqual(o["partner_gain"], OFFER_MIN_GAIN)
            self.assertNotIn("Dwyane Wade", o["trade"]["miami_out"])
            self.assertEqual(self.desk.errors(o["trade"]), [])

    def test_miami_answers_by_its_own_rule(self):
        for o in self.offers:
            self.assertEqual(o["accepted"], o["miami_gain"] >= IN_SEASON_MIN_GAIN and "star" not in o["reason"]
                             and "ceiling" not in o["reason"])
        gains = [o["miami_gain"] for o in self.offers]
        self.assertEqual(gains, sorted(gains, reverse=True))

    def test_opposed_request_lowers_miami_gain(self):
        if not self.offers:
            self.skipTest("no offers on the date")
        o = self.offers[0]
        name = o["trade"]["miami_out"][0]
        again = self.desk.offers([{"subject": "trade_opposed", "player": name}], "starter")
        match = next((x for x in again if x["trade"] == o["trade"]), None)
        if match:
            self.assertLess(match["miami_gain"], o["miami_gain"])


if __name__ == "__main__":
    unittest.main()
