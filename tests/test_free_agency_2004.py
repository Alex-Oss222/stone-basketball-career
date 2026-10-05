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
        cls.saved = F._draw, F.Market.consulted, F.Market.trade_consulted
        F._draw = favourite
        F.Market.consulted = lambda self, club, b, day, amount: True          # Wade's consultations are never written by tests
        F.Market.trade_consulted = lambda self, row, day: "ok"
        cls.market = F.Market(ROOT, "2004-10-01")
        cls.market.store = False
        cls.record = cls.market.run()

    @classmethod
    def tearDownClass(cls):
        F._draw, F.Market.consulted, F.Market.trade_consulted = cls.saved

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
            if e["kind"] in ("signing", "re_sign") and e.get("route") != "trade":
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

    def test_every_free_agent_has_a_drawn_priority(self):
        self.assertEqual(set(self.market.trait), set(self.market.pool))
        self.assertTrue(set(self.market.trait.values()) <= {"money", "fame", "loyalty", "winning"})

    def test_location_and_priority_change_a_players_view(self):
        b = next(iter(self.market.pool))
        offer = {"club": "Miami Heat", "salary": 2_000_000, "years": 2}
        other = dict(offer, club="Toronto Raptors")                  # no state tax vs the high tier, mid market both
        self.assertNotEqual(self.market.assess(b, offer, 3)[0], self.market.assess(b, other, 3)[0])
        saved = self.market.trait.get(b)
        self.market.trait[b] = "money"
        money = self.market.assess(b, offer, 3)[0]
        self.market.trait[b] = "loyalty"
        loyalty = self.market.assess(b, offer, 3)[0]
        self.market.trait[b] = saved
        self.assertNotEqual(money, loyalty)

    def test_summer_trades_are_legal_and_mutual(self):
        for e in self.record["events"]:
            if e["kind"] == "trade":
                self.assertGreaterEqual(e["date"], F.TRADE_FROM)
                self.assertNotIn(e["bbr_id"], F.UNTOUCHABLE)
        moved = [e["bbr_id"] for e in self.record["events"] if e["kind"] == "trade"]
        self.assertEqual(len(moved), len(set(moved)))                 # nobody is traded twice in a summer

    def test_wades_requests_are_weighed_by_standing(self):
        from runtime.standing import STANDING_WEIGHT, standing_on
        path = ROOT / F.REQUESTS
        if not path.is_file():
            self.skipTest("no 2004 request recorded")
        wanted = self.market.requested("2004-07-01")
        weight = STANDING_WEIGHT[standing_on(ROOT, "2004-07-01")["standing"]]
        self.assertTrue(wanted and all(w == weight for w in wanted.values()))
        self.assertEqual(self.market.requested("2004-06-23"), {})                 # nothing before it was asked

    def test_a_keep_request_against_the_rule_is_a_weighted_draw(self):
        seen = []
        saved = F._draw
        F._draw = lambda root, packet: seen.append(packet) or "tender"
        try:
            self.market.price["test-player"] = 600_000
            self.market.ident["test-player"] = {"name": "Test Player", "service": 1}
            self.assertTrue(self.market.request_draw("test-player", 900_000, 0.8))
        finally:
            F._draw = saved
            self.market.price.pop("test-player")
            self.market.ident.pop("test-player")
        from runtime.standing import STANDING_WEIGHT, standing_on
        weight = STANDING_WEIGHT[standing_on(ROOT, F.OPTIONS_DATE)["standing"]]
        self.assertAlmostEqual(seen[0]["options"]["tender"], round(weight * (1 - 300_000 / 900_000), 3), places=3)

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
