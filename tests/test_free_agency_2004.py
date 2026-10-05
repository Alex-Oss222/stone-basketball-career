"""Roadmap 14b phase 5 (the user's decision): the 2004 summer market, fully simulated for every club."""
from pathlib import Path
import unittest

from runtime import free_agency_2004 as F

ROOT = Path(__file__).resolve().parents[1]


def favourite(root, packet):
    """Test stand-in for the engine: the likeliest option (never written, never committed)."""
    return max(packet["options"], key=lambda k: (packet["options"][k], k))


class MarketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.saved = F._draw, F.Market.consulted
        F._draw = favourite
        F.Market.consulted = lambda self, club, b, day, amount: True
        cls.market = F.Market(ROOT, "2004-10-01")
        cls.record = cls.market.run()

    @classmethod
    def tearDownClass(cls):
        F._draw, F.Market.consulted = cls.saved

    def test_nothing_before_june_30(self):
        self.assertIsNone(F.run(ROOT, "2004-06-29"))

    def test_market_completes(self):
        self.assertIsNotNone(self.record)
        self.assertIn(F.MIAMI, self.record["clubs"])

    def test_each_player_signs_once(self):
        seen = [r["bbr_id"] for rows in self.record["clubs"].values() for r in rows]
        self.assertEqual(len(seen), len(set(seen)))

    def test_contracts_respect_the_scale_and_exceptions(self):
        cal, mle = self.market.cal, {}
        for e in self.record["events"]:
            if e["kind"] in ("signing", "re_sign"):
                b = e["bbr_id"]
                self.assertGreaterEqual(e["salary"], F.minimum(self.market.service(b), cal) - 1)
                if e["route"] == "mid_level":
                    self.assertLessEqual(e["salary"], cal["mle"])
                    mle[e["club"]] = mle.get(e["club"], 0) + 1
                if e["route"] == "bird":
                    self.assertEqual(e["from"], e["club"])
        self.assertTrue(all(n == 1 for n in mle.values()))

    def test_qualifying_offers_only_for_eligible_players(self):
        for e in self.record["events"]:
            if e["kind"] == "qualifying_offer":
                self.assertTrue(F.rfa_eligible(e["bbr_id"], self.market.ident, self.market.rookie_scale))
            if e["kind"] == "qualifying_offer_accepted":
                self.assertIn(e["bbr_id"], self.market.qualifying)

    def test_a_matched_offer_sheet_keeps_the_player(self):
        for e in self.record["events"]:
            if e["kind"] == "offer_sheet_matched":
                club = next(c for c, rows in self.record["clubs"].items() if any(r["bbr_id"] == e["bbr_id"] for r in rows))
                self.assertEqual(club, e["club"])

    def test_every_club_reaches_the_roster_target_or_the_pool_is_empty(self):
        if self.record["unsigned_pool"]:
            self.assertTrue(all(len(rows) >= F.ROSTER_TARGET for c, rows in self.record["clubs"].items()))

    def test_players_without_a_real_role_are_not_signed(self):
        for rows in self.record["clubs"].values():
            for r in rows:
                if r["route"] not in ("existing", "option", "rookie_scale"):
                    self.assertIn(r["bbr_id"], self.market.roles)

    def test_real_2004_moves_are_never_read(self):
        source = (ROOT / "runtime/free_agency_2004.py").read_text(encoding="utf-8")
        self.assertNotIn("nba_2004_offseason_transactions", source)
        self.assertNotIn("option_outcome", source)


class PricingTests(unittest.TestCase):
    def test_price_is_monotone_in_value(self):
        evidence = {f"p{i}": {"games": 60, "minutes": 1800, "eff": 60 * (6 + 3 * i), "mpg": 30} for i in range(6)}
        terms = {f"p{i}": {"kind": "contract", "salary": 2_000_000 + i * 2_000_000, "source": "x"} for i in range(6)}
        pricing = F.Pricing(ROOT, evidence=evidence, ident={}, terms=terms)
        prices = [pricing.comparables_price(v) for v in (8, 10, 14, 18, 22)]
        self.assertEqual(prices, sorted(prices))
        self.assertAlmostEqual(pricing.comparables_price(pricing.values[2]), terms["p2"]["salary"], delta=1)

    def test_maximum_by_service(self):
        self.assertEqual(F.maximum(3, 43_870_000), round(43_870_000 * 0.25))
        self.assertEqual(F.maximum(8, 43_870_000), round(43_870_000 * 0.30))
        self.assertEqual(F.maximum(12, 43_870_000), round(43_870_000 * 0.35))


if __name__ == "__main__":
    unittest.main()
