"""Roadmap 17 (the user's design): the 2004 lottery and a draft where every club picks for itself on draft night."""
from pathlib import Path
import unittest

from runtime import draft as D, lottery as L

ROOT = Path(__file__).resolve().parents[1]


def prospect(name, group, age, consensus, second=False):
    import math
    median = D.MEDIAN_TOP * math.exp(-D.MEDIAN_DECAY * (consensus - 1))
    spread = D.SPREAD_BASE * median * (1 + (23 - age) / 4)
    return {"player": name, "group": group, "age": age, "consensus": consensus, "second_position": second,
            "median": median, "floor": max(D.FLOOR_MIN, median - spread), "ceiling": median + 1.6 * spread}


def club(stance="middle", need=None, cornerstone=None):
    return {"stance": stance, "need": need or {"G": 0.2, "F": 0.2, "C": 0.2},
            "cornerstone": cornerstone or {"G": False, "F": False, "C": False}}


class DraftEngineTests(unittest.TestCase):
    def test_cross_tier_dominance(self):
        """The Jordan rule: a Tier 1 guard beats a Tier 2 centre even for a club with Wade at guard and no centre."""
        pool = {"g": prospect("Guard", "G", 19, 1), "c": prospect("Centre", "C", 21, 12)}
        tiers = D.tiers(pool)
        self.assertLess(tiers["g"], tiers["c"])
        # The pick is taken from the best available tier, so the centre is never in the choice.
        best = min(tiers.values())
        self.assertEqual([k for k in pool if tiers[k] == best], ["g"])

    def test_same_tier_need_breaks_the_tie(self):
        ctx = club(need={"G": 0.05, "F": 0.2, "C": 0.6})
        centre, guard = prospect("C", "C", 21, 10), prospect("G", "G", 21, 10)
        self.assertGreater(D.utility(centre, ctx), D.utility(guard, ctx))

    def test_younger_prospect_has_a_wider_spread_and_higher_ceiling(self):
        young, old = prospect("Young", "F", 18.5, 10), prospect("Old", "F", 22.5, 10)
        self.assertGreater(young["ceiling"] - young["floor"], old["ceiling"] - old["floor"])
        self.assertGreater(young["ceiling"], old["ceiling"])

    def test_cornerstone_at_the_position_costs_fit(self):
        ctx = club(cornerstone={"G": True, "F": False, "C": False})
        self.assertLess(D.utility(prospect("G", "G", 21, 10), ctx), D.utility(prospect("G2", "G", 21, 10, second=True), ctx))

    def test_contenders_weight_floor_rebuilders_ceiling(self):
        raw, polished = prospect("Raw", "F", 18.5, 10), prospect("Polished", "F", 22.5, 10)
        self.assertGreater(D.utility(raw, club("rebuilding")), D.utility(polished, club("rebuilding")))
        self.assertGreater(D.utility(polished, club("contending")) / D.utility(raw, club("contending")),
                           D.utility(polished, club("rebuilding")) / D.utility(raw, club("rebuilding")))

    def test_board_uses_only_pre_draft_evidence(self):
        pool = D.prospects(ROOT)
        self.assertGreaterEqual(len(pool), 59)
        self.assertTrue(all(p["floor"] <= p["median"] <= p["ceiling"] for p in pool.values()))
        for p in pool.values():
            self.assertNotIn("actual_pick", p)

    def test_options_are_a_valid_draw(self):
        probs = D._options({"a": 2.0, "b": 1.9, "c": 1.0})
        self.assertAlmostEqual(sum(probs.values()), 1.0, places=9)
        self.assertGreater(probs["a"], probs["b"])


class LotteryTests(unittest.TestCase):
    def test_rules(self):
        rules = L._read(ROOT / L.RULES)
        self.assertEqual(rules["combinations_by_seed"], [250, 200, 157, 120, 89, 64, 44, 29, 18, 11, 7, 6, 5])
        self.assertEqual(sum(rules["combinations_by_seed"]), 1000)
        own = L._read(ROOT / L.OWNERSHIP)
        self.assertEqual(own["round_2"]["DAL"]["owner"], "MIA")          # the 2001 Hardaway trade
        self.assertEqual(own["round_1"]["NYK"]["owner"], "NYK")          # the January 2004 trade is not applied

    def test_nothing_is_decided_before_the_dates(self):
        self.assertIsNone(L.run(ROOT, "2004-05-25"))
        self.assertIsNone(D.run(ROOT, "2004-06-23"))

    def test_packets_sum_to_one(self):
        packet = L._packet("x", "q", {"a": 1, "b": 1, "c": 1}, "b")
        self.assertAlmostEqual(sum(packet["options"].values()), 1.0, places=9)


if __name__ == "__main__":
    unittest.main()
