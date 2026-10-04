"""Prospective engine shots: geometry, preserved efficiency and genuine events."""
from collections import Counter
from copy import deepcopy
import random
import unittest
from unittest.mock import patch

from runtime.kernel import validate_result
from runtime.shot_chart import NBA_GEOMETRY, classify_zone
from runtime.spatial_shots import (
    SPATIAL_ZONES, ZONE_VALUES, classify_spatial_zone, draw_location,
    draw_spatial_shot, load_spatial_environment, spatial_environment_errors,
    zone_probabilities,
)
from tests.test_engine_model import games, team


class SpatialProbabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.environment = load_spatial_environment("2003-04", "2003-10-28")

    def test_only_the_completed_prior_season_is_eligible(self):
        self.assertEqual(spatial_environment_errors(self.environment, "2003-04", "2003-10-28"), [])
        self.assertTrue(spatial_environment_errors(self.environment, "2004-05", "2004-10-28"))
        with self.assertRaisesRegex(ValueError, "available"):
            load_spatial_environment("2003-04", "2003-04-01")
        bad = deepcopy(self.environment)
        bad["zones"][0]["attempt_share_within_value"] /= 2
        self.assertTrue(spatial_environment_errors(bad, "2003-04"))

    def test_weighted_efficiency_is_preserved_even_when_zones_clip(self):
        for value in (2, 3):
            for target in (0, 1e-9, .01, .2, .35, .5, .9, .99, 1 - 1e-9, 1):
                with self.subTest(value=value, target=target):
                    probabilities = zone_probabilities(self.environment, value, target)
                    self.assertAlmostEqual(sum(share * make for _, share, make in probabilities), target, places=12)
                    self.assertTrue(all(0 <= make <= 1 for _, _, make in probabilities))
        self.assertTrue(any(probability == 0 for _, _, probability in zone_probabilities(self.environment, 2, .01)))
        self.assertTrue(any(probability == 1 for _, _, probability in zone_probabilities(self.environment, 2, .99)))

    def test_sourced_efficiency_differences_change_the_shot_chance(self):
        twos = {zone: probability for zone, _, probability in zone_probabilities(self.environment, 2, .5)}
        threes = {zone: probability for zone, _, probability in zone_probabilities(self.environment, 3, .35)}
        self.assertGreater(twos["distance_0_3"], twos["distance_10_16"] + .1)
        self.assertGreater(threes["corner_three"], threes["arc_three"])

    def test_sampled_coordinates_match_every_native_band_and_the_court(self):
        rng = random.Random(7193)
        for zone in SPATIAL_ZONES:
            with self.subTest(zone=zone):
                points = {draw_location(rng, zone) for _ in range(600)}
                self.assertGreater(len(points), 590)
                for x, y in points:
                    self.assertEqual(classify_spatial_zone(x, y), zone)
                    self.assertEqual(classify_zone(x, y) == "three", ZONE_VALUES[zone] == 3)
                    self.assertTrue(-25 <= x <= 25 and NBA_GEOMETRY["baseline_y"] <= y <= NBA_GEOMETRY["half_court_y"])
        # Native distance bands are not renamed paint or restricted-area zones.
        self.assertEqual(classify_spatial_zone(0, 3.5), "distance_3_10")
        self.assertEqual(classify_spatial_zone(23, 2), "corner_three")
        self.assertEqual(classify_spatial_zone(0, 24), "arc_three")


class SpatialGameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = list(games(team("H"), team("A"), 80, tag="spatial-kernel"))

    def test_all_actual_attempts_reconcile_and_replay_is_exact(self):
        result = self.results[0]
        self.assertEqual(result, next(games(team("H"), team("A"), 1, tag="spatial-kernel")))
        self.assertEqual(result["shot_tracking"]["source_type"], "engine_generated")
        for result in self.results:
            self.assertEqual(validate_result(result), [])
            self.assertEqual(len(result["shots"]), sum(t["fga"] for t in result["team_stats"].values()))
            self.assertEqual(len({shot["shot_id"] for shot in result["shots"]}), len(result["shots"]))
            for side, rows in result["player_stats"].items():
                for row in rows:
                    shots = [s for s in result["shots"] if s["side"] == side and s["player_id"] == row["player_id"]]
                    self.assertEqual(len(shots), row["fga"])
                    self.assertEqual(sum(s["made"] for s in shots), row["fgm"])
                    self.assertEqual(sum(s["value"] == 3 for s in shots), row["tpa"])
                    self.assertEqual(sum(s["value"] == 3 and s["made"] for s in shots), row["tpm"])
        self.assertTrue(any(t["fta"] > 0 for r in self.results for t in r["team_stats"].values()))

    def test_live_outcomes_use_the_preselected_location_probability(self):
        choices = []

        def controlled(rng, environment, value, target):
            zone, x, y, _ = draw_spatial_shot(rng, environment, value, target)
            # Deliberately controlled probabilities isolate the wiring: a
            # decorative location added after shooting would fail this test.
            probability = float(zone in ("distance_0_3", "corner_three"))
            choices.append((zone, x, y, bool(probability)))
            return zone, x, y, probability

        with patch("runtime.kernel.draw_spatial_shot", side_effect=controlled):
            result = next(games(team("H"), team("A"), 1, tag="spatial-live-probability"))
        actual = [(shot["zone"], shot["x"], shot["y"], shot["made"]) for shot in result["shots"]]
        self.assertEqual(actual, choices)
        self.assertEqual({shot["made"] for shot in result["shots"]}, {True, False})

    def test_game_distribution_uses_the_prior_and_close_shots_convert_better(self):
        counts, made, values = Counter(), Counter(), Counter()
        for result in self.results:
            for shot in result["shots"]:
                counts[shot["zone"]] += 1
                made[shot["zone"]] += shot["made"]
                values[shot["value"]] += 1
        environment = load_spatial_environment("2003-04")
        for zone in environment["zones"]:
            self.assertAlmostEqual(counts[zone["id"]] / values[zone["shot_value"]],
                                   zone["attempt_share_within_value"], delta=.035)
        self.assertGreater(made["distance_0_3"] / counts["distance_0_3"],
                           made["distance_10_16"] / counts["distance_10_16"] + .1)

    def test_missing_extra_and_geometrically_wrong_events_are_rejected(self):
        original = self.results[0]
        bad = deepcopy(original)
        bad["shots"].pop()
        self.assertTrue(validate_result(bad))
        bad = deepcopy(original)
        bad["shots"].append(deepcopy(bad["shots"][0]))
        self.assertTrue(validate_result(bad))
        bad = deepcopy(original)
        bad["shots"][0]["zone"] = "not_a_sourced_zone"
        self.assertTrue(validate_result(bad))
        # Historical result bodies remain valid without new prospective fields.
        old = deepcopy(original)
        old.pop("shots")
        old.pop("shot_tracking")
        old["kernel"] = "2003.6"
        self.assertEqual(validate_result(old), [])


if __name__ == "__main__":
    unittest.main()
