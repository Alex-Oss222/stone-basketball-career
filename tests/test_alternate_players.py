"""Alternate-history players: Bosh keeps his real path through 2003-04 and his own model from 2004-05."""
import unittest

from runtime import trajectories
from runtime.trajectories import alternate, development_seasons, needs_development


class GateTests(unittest.TestCase):
    def test_bosh_switches_only_from_2004_05(self):
        self.assertFalse(alternate("boshch01", "2003-04"))
        self.assertTrue(alternate("boshch01", "2004-05"))
        self.assertTrue(alternate("wadedw01", "2003-04"))
        self.assertFalse(alternate("cartevi01", "2004-05"))

    def test_his_2003_04_swing_chain_is_unchanged(self):
        self.assertEqual(development_seasons("boshch01", "2003-04"), ["2003-04"])
        self.assertEqual(development_seasons("cartevi01", "2004-05"), ["2003-04", "2004-05"])
        self.assertEqual(development_seasons("boshch01", "2004-05"), ["2004-05"])   # his own season's draw only

    def test_his_own_profile_draws_a_swing(self):
        self.assertTrue(needs_development({"bbr_id": "boshch01", "model_version": "protagonist-2004.1", "season_end_year": 2005}))
        self.assertFalse(needs_development({"bbr_id": "cartevi01", "model_version": "protagonist-2004.1", "season_end_year": 2005}))


class ProfileTests(unittest.TestCase):
    def test_the_engine_reads_his_own_profile_in_2004_05(self):
        from tests import live_season
        from runtime.player_stats import load_rating_index
        with live_season():
            index = load_rating_index("2004-11-03", "2004-05")
            bosh = index.engine_profile("Chris Bosh", "boshch01")
            self.assertEqual(bosh["model_version"], "protagonist-2004.1")
            self.assertEqual(index.engine_profile("Vince Carter", "cartevi01")["model_version"], trajectories.TRAJECTORY_MODEL_VERSION)

    def test_targets_translate_to_rates(self):
        from runtime.protagonist import target_rates
        prior = {"three_point_attempt_rate": 0.1, "two_point_pct": 0.48}
        out = target_rates({"ft_pct": 0.9, "fg_pct": 0.5, "three_pct": 0.4}, prior, {}, {}, {}, {})
        self.assertAlmostEqual(out["free_throw_pct"], 0.9)
        self.assertAlmostEqual(out["two_point_pct"], (0.5 - 0.1 * 0.4) / 0.9)


if __name__ == "__main__":
    unittest.main()
