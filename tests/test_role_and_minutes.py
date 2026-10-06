"""Role growth for model-built players and the staff's minutes by gap (the user's request, November 2004)."""
import unittest

from runtime.protagonist import USAGE_BOUNDS, role_growth
from runtime.rotation_reviews import GAP_MAX_EXTRA, minutes_by_gap

LEAGUE = {"points": 1000, "field_goals_attempted": 850, "free_throws_attempted": 250}   # true shooting about 0.52



def season(pts, fga=1000, fta=300):
    ftm = 240
    fgm = (pts - ftm) / 2
    return {"fga": fga, "fta": fta, "fgm": fgm, "tpm": 0, "ftm": ftm}


class RoleGrowthTests(unittest.TestCase):
    def test_not_before_2005_06(self):
        self.assertIsNone(role_growth({"usage_pct": .2}, season(1300), LEAGUE, "2004-05"))

    def test_efficient_gains_inefficient_loses_and_accuracy_pays(self):
        up = {"usage_pct": .20, "two_point_pct": .50, "three_point_pct": .36}
        basis = role_growth(up, season(1400), LEAGUE, "2005-06")
        self.assertGreater(up["usage_pct"], .20)
        self.assertLessEqual(up["usage_pct"], .20 * 1.2 + 1e-9)               # at most +20% a season
        self.assertLess(up["two_point_pct"], .50)
        self.assertEqual(round(basis["usage_after"], 4), round(up["usage_pct"], 4))
        down = {"usage_pct": .20, "two_point_pct": .45, "three_point_pct": .30}
        role_growth(down, season(1000), LEAGUE, "2005-06")
        self.assertLess(down["usage_pct"], .20)
        self.assertEqual(down["two_point_pct"], .45)                          # losing shots costs no accuracy

    def test_usage_ceiling(self):
        r = {"usage_pct": .33, "two_point_pct": .5, "three_point_pct": .35}
        role_growth(r, season(1500), LEAGUE, "2006-07")
        self.assertLessEqual(r["usage_pct"], USAGE_BOUNDS[1])


class MinutesByGapTests(unittest.TestCase):
    def rotation(self):
        starters = [{"player_id": n, "minutes": 34.0, "starter": True} for n in "ABCDE"]
        bench = [{"player_id": n, "minutes": m, "starter": False} for n, m in zip("FGHIJK", (20, 16, 12, 10, 8, 4))]
        return starters + bench

    def test_clear_leader_gains_from_reserves(self):
        players = self.rotation()
        basis = minutes_by_gap(players, {"A": 20, "B": 16.5, "C": 13, "D": 12, "E": 11, "F": 12})
        self.assertAlmostEqual(sum(p["minutes"] for p in players), 240, places=6)
        a = players[0]["minutes"]
        self.assertGreater(a, 37)
        self.assertLessEqual(a, 34 + GAP_MAX_EXTRA)
        self.assertEqual([p["minutes"] for p in players[1:5]], [34.0] * 4)
        self.assertEqual(basis["player"], "A")

    def test_close_leaders_keep_the_template(self):
        players = self.rotation()
        minutes_by_gap(players, {"A": 15, "B": 14.9, "C": 13, "D": 12, "E": 11})
        self.assertEqual(players[0]["minutes"], 34.0)

    def test_extra_is_capped(self):
        players = self.rotation()
        minutes_by_gap(players, {"A": 40, "B": 10, "C": 9, "D": 8, "E": 7})
        self.assertAlmostEqual(players[0]["minutes"], 34 + GAP_MAX_EXTRA, places=1)


if __name__ == "__main__":
    unittest.main()


class ArrivalEstimateTests(unittest.TestCase):
    """A player who joins after camp gets the staff's arrival estimate (efficiency per 30 minutes, the camp scale)."""

    def test_trade_arrival_has_an_estimate_from_evidence_before_he_joined(self):
        from pathlib import Path
        from runtime.rotation_reviews import arrival_estimate
        root = Path(__file__).resolve().parents[1]
        if not (root / "career/Dwyane_Wade/2004-05/current_state.json").is_file():
            self.skipTest("no 2004-05 season")
        value = arrival_estimate("Donyell Marshall", "marshdo01", "2004-12-23", root, "2004-05")
        self.assertIsNotNone(value)
        self.assertGreater(value, 0)
        self.assertLess(value, 40)
        self.assertEqual(value, arrival_estimate("Donyell Marshall", "marshdo01", "2004-12-23", root, "2004-05"))  # deterministic
