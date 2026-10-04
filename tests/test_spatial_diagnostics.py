"""Diagnostics must reject incomplete tracking and expose spatial sampling drift."""
import copy
import unittest

from runtime.kernel import resolve_game
from runtime.spatial_shots import SPATIAL_ZONES, load_spatial_environment
from scripts.engine_diagnostics import SpatialDiagnostics
from tests.test_engine_model import ENV, RULES, team


class SpatialDiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.environment = load_spatial_environment("2003-04", "2003-11-05")
        cls.result = resolve_game(team("DiagnosticHome"), team("DiagnosticAway"),
                                  entropy=b"noncanonical-spatial-diagnostic-fixture",
                                  event_id="spatial-diagnostic-fixture", rules=RULES,
                                  environment=ENV, spatial_environment=cls.environment)

    def test_complete_feed_reconciles_and_reports_every_native_band(self):
        diagnostics = SpatialDiagnostics(self.environment)
        diagnostics.add(self.result)
        summary = diagnostics.summary()
        self.assertEqual(summary["games_with_complete_tracking"], 1)
        self.assertEqual(summary["attempts"], sum(row["fga"] for row in self.result["team_stats"].values()))
        self.assertEqual(summary["makes"], sum(row["fgm"] for row in self.result["team_stats"].values()))
        self.assertEqual(set(summary["zones"]), set(SPATIAL_ZONES))
        self.assertEqual(summary["source_season"], "2002-03")
        self.assertEqual(summary["tracking"], self.result["shot_tracking"])
        self.assertEqual(summary["source_provenance"], self.environment["provenance"])
        self.assertLess(summary["max_weighted_make_probability_error"], 1e-12)

    def test_legacy_game_cannot_silently_count_as_tracked(self):
        result = copy.deepcopy(self.result)
        del result["shots"], result["shot_tracking"]
        with self.assertRaisesRegex(ValueError, "missing or different spatial provenance"):
            SpatialDiagnostics(self.environment).add(result)

    def test_different_prior_cannot_be_mixed_into_aggregate(self):
        result = copy.deepcopy(self.result)
        result["shot_tracking"]["prior_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "different spatial provenance"):
            SpatialDiagnostics(self.environment).add(result)

    def test_missing_attempt_is_rejected_before_counting_game(self):
        result = copy.deepcopy(self.result)
        result["shots"].pop()
        diagnostics = SpatialDiagnostics(self.environment)
        with self.assertRaisesRegex(ValueError, "do not reconcile"):
            diagnostics.add(result)
        self.assertEqual(diagnostics.games, 0)

    def test_conditional_share_check_rejects_concentrated_sampling(self):
        diagnostics = SpatialDiagnostics(self.environment)
        diagnostics.attempts.update({"distance_0_3": 10000, "corner_three": 10000})
        errors = diagnostics.summary()["calibration_errors"]
        self.assertTrue(any("distance_0_3: share" in error for error in errors))
        self.assertTrue(any("arc_three: share" in error for error in errors))

    def test_no_attempts_do_not_pass_calibration(self):
        errors = SpatialDiagnostics(self.environment).summary()["calibration_errors"]
        self.assertIn("spatial 2-point attempts are absent", errors)
        self.assertIn("spatial 3-point attempts are absent", errors)


if __name__ == "__main__":
    unittest.main()
