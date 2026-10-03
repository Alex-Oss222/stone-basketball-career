"""Shooting geometry, box reconciliation, coverage and appearance denominators."""
from copy import deepcopy
import json
import math
import unittest

from runtime.shot_chart import (
    NBA_GEOMETRY, aggregate_shots, classify_zone, make_illustrative_shots,
)


def game(game_id="game-1", day="2003-11-01", *, fgm=1, fga=2, tpm=0, tpa=1,
         ftm=2, appeared=True, **changes):
    line = {"fgm": fgm, "fga": fga, "tpm": tpm, "tpa": tpa,
            "ftm": ftm, "fta": ftm, "pts": 2 * fgm + tpm + ftm,
            "appeared": appeared, "seconds": 1200 if appeared else 0}
    record = {"event_id": game_id, "date": day, "status": "played", "coverage": "complete",
              "line": line, "appearance": "Played", "competition": "regular", "season": "2003-04"}
    record.update(changes)
    return record


def shot(shot_id="shot-1", game_id="game-1", day="2003-11-01", *, x=0, y=2, made=True, value=2, **changes):
    row = {"shot_id": shot_id, "game_id": game_id, "date": day, "x": x, "y": y,
           "made": made, "value": value, "source_ref": f"test:source/{game_id}"}
    row.update(changes)
    return row


def basic_shots():
    return [shot(), shot("shot-2", x=23, y=1, made=False, value=3)]


def zone(result, zone_id):
    return next(z for z in result["zones"] if z["id"] == zone_id)


class GeometryTests(unittest.TestCase):
    def test_paint_precedes_distance_bands(self):
        for point in ((0, 0), (-8, -5.25), (8, 13.75), (0, 12), (-8, 13)):
            with self.subTest(point=point):
                self.assertEqual(classify_zone(*point), "paint")
        self.assertEqual(classify_zone(8.0001, 1), "under_12")
        self.assertEqual(classify_zone(0, 13.7501), "12_to_18")

    def test_nonoverlapping_distance_boundaries_outside_paint(self):
        self.assertEqual(classify_zone(11.9999, 0), "under_12")
        self.assertEqual(classify_zone(12, 0), "12_to_18")
        self.assertEqual(classify_zone(17.9999, 0), "12_to_18")
        self.assertEqual(classify_zone(18, 0), "18_to_3pt")
        self.assertEqual(classify_zone(0, 23.75), "18_to_3pt")
        self.assertEqual(classify_zone(0, 23.7501), "three")

    def test_corner_three_is_not_a_23_75_foot_circle(self):
        self.assertLess(math.hypot(22.5, 0), 23.75)
        self.assertEqual(classify_zone(22.5, 0), "three")
        self.assertEqual(classify_zone(-22.5, -4), "three")
        self.assertEqual(classify_zone(22, 3), "18_to_3pt")
        join = NBA_GEOMETRY["three_point_join_y"]
        self.assertEqual(classify_zone(22, join), "18_to_3pt")
        self.assertEqual(classify_zone(22, join + .001), "three")
        self.assertEqual(classify_zone(21, join + .001), "18_to_3pt")

    def test_trigonometric_line_points_handle_numeric_roundoff(self):
        for degrees in range(23, 158):
            angle = math.radians(degrees)
            point = (23.75 * math.cos(angle), 23.75 * math.sin(angle))
            with self.subTest(degrees=degrees):
                self.assertEqual(classify_zone(*point), "18_to_3pt")
                self.assertEqual(classify_zone(point[0] * 1.00001, point[1] * 1.00001), "three")
        self.assertEqual(classify_zone(12 * math.cos(.5), 12 * math.sin(.5)), "12_to_18")
        self.assertEqual(classify_zone(18 * math.cos(.5), 18 * math.sin(.5)), "18_to_3pt")

    def test_missing_and_outside_view_are_not_mapped_to_a_zone(self):
        for point in ((None, None), (None, 10), (3, None), (25.1, 0),
                      (0, -5.26), (0, 42), (0, 75)):
            with self.subTest(point=point):
                self.assertIsNone(classify_zone(*point))
        for point in ((True, 2), ("0", 1), (0, float("nan")), (float("inf"), None)):
            with self.subTest(point=point), self.assertRaises(ValueError):
                classify_zone(*point)


class AggregationTests(unittest.TestCase):
    def test_all_appearances_include_zero_zone_games_and_exclude_dnp(self):
        records = [game(), game("zero", "2003-11-03", fgm=0, fga=0, tpm=0, tpa=0, ftm=0),
                   game("dnp", "2003-11-05", line=None, appearance="DNP: inactive")]
        result = aggregate_shots(records, basic_shots())
        self.assertEqual((result["games"], result["recorded_appearances"], result["dnp"]), (2, 2, 1))
        self.assertEqual(zone(result, "paint")["fg_ppg"], 1)
        self.assertEqual(zone(result, "paint")["fga_per_game"], .5)
        self.assertEqual(zone(result, "three")["fga_per_game"], .5)
        self.assertEqual(zone(result, "three")["fg_pct"], 0)
        self.assertEqual(zone(result, "under_12")["fga"], 0)
        self.assertIsNone(zone(result, "under_12")["fg_pct"])

    def test_zone_points_exclude_free_throws_including_weighted_ones(self):
        record = game()
        record["line"].update(ftm=1, fta=1, ft_points=3, pts=5)
        result = aggregate_shots([record], basic_shots())
        self.assertEqual(sum(z["fg_points"] for z in result["zones"]), 2)
        self.assertEqual(result["totals"]["fg_ppg"], 2)
        self.assertNotEqual(result["totals"]["fg_ppg"], record["line"]["pts"])

    def test_zone_and_bin_counts_reconcile_to_complete_box(self):
        record = game(fgm=3, fga=5, tpm=1, tpa=1, ftm=0)
        shots = [shot(), shot("s2", x=10, y=0, made=False),
                 shot("s3", x=12, y=5), shot("s4", x=18, y=5, made=False),
                 shot("s5", x=23, y=0, value=3)]
        result = aggregate_shots([record], shots)
        self.assertEqual(result["coverage"]["status"], "complete")
        for key in ("fgm", "fga", "fg_points", "tpm", "tpa"):
            self.assertEqual(sum(z[key] for z in result["zones"]), result["totals"][key])
            self.assertEqual(sum(b[key] for b in result["bins"]), result["totals"][key])
        self.assertEqual(result["totals"]["fg_points"], 7)

    def test_fg_percentage_pools_makes_and_attempts(self):
        records = [game(fgm=1, fga=1, tpa=0, ftm=0),
                   game("g2", "2003-11-02", fgm=1, fga=3, tpa=0, ftm=0)]
        shots = [shot()] + [shot(f"g2-{i}", "g2", "2003-11-02", made=i == 0) for i in range(3)]
        result = aggregate_shots(records, shots)
        self.assertEqual(zone(result, "paint")["fg_pct"], .5)
        self.assertNotEqual(zone(result, "paint")["fg_pct"], (1 + 1 / 3) / 2)

    def test_bin_area_uses_fixed_frequency_across_different_length_periods(self):
        records = [game(fgm=1, fga=2, tpa=0, ftm=0),
                   game("g2", "2003-11-02", fgm=1, fga=2, tpa=0, ftm=0)]
        shots = [shot(), shot("m1", made=False), shot("a2", "g2", "2003-11-02"),
                 shot("m2", "g2", "2003-11-02", made=False)]
        one = aggregate_shots(records, shots, end="2003-11-01")["bins"][0]
        two = aggregate_shots(records, shots)["bins"][0]
        self.assertEqual((one["fga"], two["fga"]), (2, 4))
        self.assertEqual((one["area_weight"], two["area_weight"]), (2, 2))
        self.assertEqual(two["area_unit"], "attempts_per_appearance")

    def test_bin_keys_keep_zones_separate_and_centers_are_observed_points(self):
        record = game(fgm=2, fga=2, tpa=0, ftm=0)
        shots = [shot(x=7.9, y=13.7), shot("s2", x=8.1, y=13.7)]
        result = aggregate_shots([record], shots, bin_size=3)
        self.assertEqual(len(result["bins"]), 2)
        for b in result["bins"]:
            self.assertIn((b["x"], b["y"]), [(s["x"], s["y"]) for s in shots])
            self.assertEqual(classify_zone(b["x"], b["y"]), b["zone"])

    def test_zero_attempt_appearance_and_empty_period_are_not_missing_feed(self):
        record = game(fgm=0, fga=0, tpm=0, tpa=0, ftm=0)
        played = aggregate_shots([record], [])
        self.assertEqual(played["coverage"]["status"], "complete")
        self.assertEqual(zone(played, "paint")["fga_per_game"], 0)
        empty = aggregate_shots([], [])
        self.assertEqual((empty["games"], empty["totals"]["fga"]), (0, 0))
        self.assertIsNone(zone(empty, "paint")["fga_per_game"])
        self.assertIsNone(zone(empty, "paint")["fg_pct"])

    def test_unknown_tracking_is_not_zero_zone_production(self):
        result = aggregate_shots([game()], [])
        self.assertEqual(result["coverage"]["status"], "unavailable")
        self.assertEqual(result["coverage"]["missing_attempts"], 2)
        self.assertEqual(result["totals"]["fga"], 2)
        self.assertIsNone(zone(result, "paint")["fga"])
        self.assertIsNone(zone(result, "paint")["fg_ppg"])
        self.assertEqual(zone(result, "paint")["observed_fga"], 0)
        self.assertEqual(result["bins"], [])

    def test_partial_events_show_raw_counts_without_full_period_zone_rates(self):
        result = aggregate_shots([game()], [shot()])
        self.assertEqual(result["coverage"]["status"], "partial")
        self.assertEqual((result["coverage"]["located_attempts"], result["coverage"]["missing_attempts"]), (1, 1))
        paint = zone(result, "paint")
        self.assertEqual((paint["observed_fga"], paint["observed_fg_points"]), (1, 2))
        self.assertIsNone(paint["fg_ppg"])
        self.assertIsNone(paint["fg_pct"])
        self.assertIsNone(result["bins"][0]["fga_per_game"])
        self.assertIsNone(result["bins"][0]["area_weight"])
        self.assertEqual(result["bins"][0]["fg_pct"], 1)

    def test_unlocated_and_outside_view_attempts_are_counted_not_projected(self):
        shots = basic_shots()
        shots[1].update(x=None, y=None)
        result = aggregate_shots([game()], shots)
        self.assertEqual(result["coverage"]["unlocated_attempts"], 1)
        self.assertEqual(result["coverage"]["recorded_attempts"], 2)
        self.assertEqual(result["coverage"]["missing_attempts"], 0)
        self.assertEqual(result["observed"]["tpa"], 1)
        self.assertEqual(sum(b["fga"] for b in result["bins"]), 1)
        shots[1].update(x=0, y=60)
        result = aggregate_shots([game()], shots)
        self.assertEqual(result["coverage"]["outside_view_attempts"], 1)
        self.assertIsNone(zone(result, "three")["fga_per_game"])

    def test_missing_box_coverage_does_not_invent_appearance_denominator(self):
        records = [game(), game(None, "2003-11-02", coverage="missing_box", line=None, appearance="Unknown")]
        result = aggregate_shots(records, basic_shots())
        self.assertIsNone(result["games"])
        self.assertEqual(result["recorded_appearances"], 1)
        self.assertEqual(len(result["coverage"]["missing_box_games"]), 1)
        self.assertIsNone(result["coverage"]["box_fga"])
        self.assertIsNone(result["coverage"]["missing_attempts"])
        self.assertIsNone(result["totals"]["fg_ppg"])
        self.assertIsNone(zone(result, "paint")["fg_ppg"])

    def test_date_scopes_are_inclusive_and_hide_later_attempts(self):
        records = [game(), game("g2", "2003-11-08", fgm=0, fga=1, tpa=0, ftm=0)]
        shots = basic_shots() + [shot("future-period-shot", "g2", "2003-11-08", made=False)]
        week = aggregate_shots(records, shots, start="2003-11-01", end="2003-11-07")
        self.assertEqual((week["games"], week["totals"]["fga"]), (1, 2))
        self.assertNotIn("future-period-shot", [s for b in week["bins"] for s in b["shot_ids"]])
        self.assertNotIn("test:source/g2", week["source_refs"])
        with self.assertRaises(ValueError):
            aggregate_shots(records, shots, start="2003-11-08", end="2003-11-01")

    def test_no_mutation_and_json_safe_output(self):
        records, shots = [game()], basic_shots()
        before = deepcopy((records, shots))
        first = aggregate_shots(records, shots)
        self.assertEqual(first, aggregate_shots(records, shots))
        self.assertEqual((records, shots), before)
        json.dumps(first, allow_nan=False)


class ValidationTests(unittest.TestCase):
    def test_duplicate_or_orphan_event_and_shot_ids_fail(self):
        with self.assertRaisesRegex(ValueError, "unique"):
            aggregate_shots([game(), game()], basic_shots())
        with self.assertRaisesRegex(ValueError, "unique"):
            aggregate_shots([game()], [shot(), shot()])
        with self.assertRaisesRegex(ValueError, "unknown or unplayed"):
            aggregate_shots([game()], [shot(game_id="missing")])
        with self.assertRaisesRegex(ValueError, "date"):
            aggregate_shots([game()], [shot(day="2003-11-02")])

    def test_source_value_is_never_silently_rewritten_from_coordinates(self):
        for attempt in (shot(x=23, y=0, value=2), shot(x=0, y=2, value=3)):
            with self.subTest(attempt=attempt), self.assertRaisesRegex(ValueError, "disagrees"):
                aggregate_shots([game()], [attempt])

    def test_missing_source_or_invalid_outcome_fails(self):
        for changes in ({"source_ref": ""}, {"value": 1}, {"value": 2.0}, {"made": 1},
                        {"x": float("nan")}, {"x": "3"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                aggregate_shots([game()], [shot(**changes)])

    def test_full_and_partial_shot_outcomes_must_fit_box_buckets(self):
        records = [game()]
        incorrect = basic_shots()
        incorrect[1]["made"] = True
        with self.assertRaisesRegex(ValueError, "reconcile"):
            aggregate_shots(records, incorrect)
        # The box contains one made two, so even one missed two is impossible.
        with self.assertRaisesRegex(ValueError, "reconcile"):
            aggregate_shots(records, [shot(made=False)])
        with self.assertRaisesRegex(ValueError, "reconcile"):
            aggregate_shots(records, basic_shots() + [shot("extra")])

    def test_box_points_and_shooting_totals_must_reconcile(self):
        record = game()
        record["line"]["pts"] = 99
        with self.assertRaisesRegex(ValueError, "reconcile"):
            aggregate_shots([record], basic_shots())
        record = game(fgm=3, fga=2)
        with self.assertRaisesRegex(ValueError, "impossible"):
            aggregate_shots([record], [])

    def test_dnp_with_attempts_and_cross_competition_totals_fail(self):
        dnp = game(line=None, appearance="DNP: inactive")
        with self.assertRaisesRegex(ValueError, "DNP"):
            aggregate_shots([dnp], basic_shots())
        false_dnp = game(appeared=False)
        with self.assertRaisesRegex(ValueError, "DNP"):
            aggregate_shots([false_dnp], [])
        for change in ({"competition": "playoff"}, {"season": "2004-05"}):
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, "different"):
                aggregate_shots([game(), game("g2", "2003-11-02", **change)], [])

    def test_unfinished_game_cannot_own_shots(self):
        with self.assertRaisesRegex(ValueError, "unknown or unplayed"):
            aggregate_shots([game(status="scheduled")], basic_shots())


class IllustrativeFixtureTests(unittest.TestCase):
    def test_fictional_generator_requires_explicit_opt_in_and_example_ids(self):
        with self.assertRaises(ValueError):
            make_illustrative_shots([game("illustrative-one")])
        with self.assertRaises(ValueError):
            make_illustrative_shots([game()], example_only=True)

    def test_six_fictional_boxes_reconcile_without_changing_career_or_records(self):
        values = [(8, 17, 1, 3), (9, 20, 2, 5), (7, 13, 0, 1),
                  (11, 21, 2, 4), (6, 15, 1, 4), (10, 18, 1, 2)]
        records = [game(f"illustrative-{i}", f"2003-11-{i:02d}", fgm=m, fga=a, tpm=tm, tpa=ta)
                   for i, (m, a, tm, ta) in enumerate(values, 1)]
        records.append(game("illustrative-dnp", "2003-11-07", line=None, appearance="DNP: inactive"))
        before = deepcopy(records)
        shots = make_illustrative_shots(records, example_only=True)
        self.assertEqual(shots, make_illustrative_shots(records, example_only=True))
        self.assertEqual(records, before)
        self.assertTrue(all(s["example_only"] for s in shots))
        result = aggregate_shots(records, shots)
        self.assertEqual((result["games"], result["dnp"]), (6, 1))
        self.assertEqual(result["totals"]["fga"], 104)
        self.assertEqual(result["totals"]["fgm"], 51)
        self.assertEqual(result["totals"]["tpa"], 19)
        self.assertEqual(result["totals"]["tpm"], 7)
        self.assertEqual(result["totals"]["fg_points"], 109)
        self.assertEqual(result["coverage"]["status"], "complete")


if __name__ == "__main__":
    unittest.main()
