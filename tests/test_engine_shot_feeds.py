"""Engine locations remain prospective, source-bound and exactly reconciled."""
from copy import deepcopy
import json
import math
import unittest

from runtime.player_cards import load_recorded_shots
from runtime.shot_events import build_tracking_cohort, engine_result_shots, spatial_result_errors
from tests.test_live_player_cards import LiveCardFixtures, box


class EngineShotFeedTests(LiveCardFixtures):
    def tracked_game(self, name="Game_1", day="2003-11-12", *, player_line=None):
        note, path, result = self.game(name, day, line=player_line)
        result.update(kernel="2003.7", periods=4, period_scores={"home": [25] * 4, "away": [20, 20, 25, 25]},
            shot_tracking=dict(schema_version=1, model_version="spatial-2003.1",
                coordinate_system="nba_feet_from_basket", source_type="engine_generated",
                prior_sha256="a" * 64, coverage="complete"), shots=[])
        # Another player with identical shooting buckets must never leak into
        # Wade's chart even though box-score-only matching could pass.
        result["player_stats"]["away"] = [{"player_id": "other_player", **box()}]
        result["team_stats"] = {}
        for side in ("home", "away"):
            result["team_stats"][side] = {k: sum(r[k] for r in result["player_stats"][side])
                                         for k in ("fgm", "fga", "tpm", "tpa")}
            for player in result["player_stats"][side]:
                specs = [(2, True, 1.125, 2.25, "distance_0_3")] * (player["fgm"] - player["tpm"])
                specs += [(2, False, 10, 2, "distance_10_16")] * (player["fga"] - player["tpa"] - player["fgm"] + player["tpm"])
                specs += [(3, True, 0, 25, "arc_three")] * player["tpm"]
                specs += [(3, False, 23.25, 1.75, "corner_three")] * (player["tpa"] - player["tpm"])
                for value, made, x, y, zone in specs:
                    index = len(result["shots"]) + 1
                    result["shots"].append(dict(shot_id=f"{result['event_id']}:shot:{index:06d}",
                        player_id=player["player_id"], side=side, period=1, clock_seconds=720-index*10,
                        x=x, y=y, zone=zone, value=value, made=made, transition=False))
        path.write_text(json.dumps(result))
        return note, path, result

    def test_closed_result_events_populate_player_card_without_a_sidecar(self):
        note, path, result = self.tracked_game()
        before = {p: p.read_bytes() for p in (note, path)}
        self.assertEqual(spatial_result_errors(result), [])
        period = self.season(self.data())
        self.assertEqual(len(period["shots"]), 2)
        self.assertEqual({s["player_id"] for s in period["shots"]}, {"dwyane_wade"})
        self.assertEqual(period["shooting"]["coverage"]["status"], "complete")
        self.assertEqual(period["shot_source_type"], "engine_generated")
        self.assertIn("Simulated engine shot locations", period["source_note"])
        self.assertEqual(len(period["shots"][0]["source_digest"]), 64)
        self.assertTrue(period["source_games"][0]["shot_href"].endswith("Game_1.result.json"))
        self.assertEqual(before, {p: p.read_bytes() for p in (note, path)})
        self.assertFalse(note.with_suffix(".shots.json").exists())

    def test_legacy_games_keep_full_season_partial_but_tracked_cohort_has_own_totals(self):
        self.game("Game_1", "2003-11-01")
        self.tracked_game("Game_2")
        period = self.season(self.data())
        self.assertEqual(period["appearances"], 2)
        self.assertEqual(period["shooting"]["coverage"]["status"], "partial")
        self.assertTrue(all(z["fg_pct"] is None for z in period["shooting"]["zones"]))
        tracked = period["tracked"]
        self.assertEqual((tracked["appearances"], tracked["box"]["fga"]), (1, 2))
        self.assertEqual(tracked["pg"]["fga"], 2)
        self.assertEqual(tracked["shooting"]["coverage"]["status"], "complete")
        self.assertEqual(tracked["start"], "2003-11-12")
        self.assertEqual(len(tracked["source_games"]), 1)
        self.assertEqual(period["tracking_cohort"]["excluded_games"], 1)

    def test_old_boxes_and_undeclared_sidecars_remain_untracked(self):
        note, _, _ = self.game()
        note.with_suffix(".shots.json").write_text(json.dumps({"shots": [{"x": 1, "y": 1}]}))
        period = self.season(self.data())
        self.assertEqual(period["shots"], [])
        self.assertIsNone(period["tracked"])
        self.assertEqual(period["shooting"]["coverage"]["status"], "unavailable")

    def test_empty_attempt_appearance_stays_in_tracked_denominator(self):
        self.tracked_game(player_line=box(fgm=0, fga=0, tpm=0, tpa=0, ftm=0, fta=0, pts=0))
        period = self.season(self.data())
        self.assertEqual(period["shot_source_type"], "engine_generated")
        self.assertIn("Simulated engine shot locations", period["source_note"])
        self.assertNotIn("No declared recorded shot feed", period["source_note"])
        self.assertEqual(period["tracked"]["appearances"], 1)
        self.assertEqual(period["tracked"]["box"]["fga"], 0)
        self.assertEqual(period["tracked"]["shot_source_type"], "engine_generated")
        self.assertEqual(period["tracked"]["shooting"]["coverage"]["status"], "complete")

    def test_unknown_box_without_an_event_id_remains_outside_tracking_cohort(self):
        unknown = dict(status="played", coverage="missing_box", line=None, date="2003-11-12",
                       competition="regular", season="2003-04", appearance="Unknown: missing player box")
        for record in (unknown, {**unknown, "event_id": None}):
            with self.subTest(record=record):
                cohort = build_tracking_cohort([record], [], tracked_game_ids=set())
                self.assertIsNone(cohort["tracked"])
                self.assertEqual(cohort["tracking_cohort"]["total_games"], 1)
                self.assertEqual(cohort["tracking_cohort"]["excluded_games"], 1)
                self.assertIsNone(cohort["tracking_cohort"]["total_appearances"])

    def test_external_feed_conflict_fails_instead_of_double_counting(self):
        note, _, result = self.tracked_game()
        self.feed(note, result)
        with self.assertRaisesRegex(ValueError, "cannot combine"):
            self.data()

    def test_unclosed_or_wrong_result_source_cannot_supply_engine_shots(self):
        note, path, result = self.tracked_game()
        records = self.records()
        note.write_text(note.read_text().replace("status: played", "status: scheduled"))
        with self.assertRaisesRegex(ValueError, "closed game note"):
            load_recorded_shots(self.player, self.identity, records, "2003-11-30")
        note.write_text(note.read_text().replace("status: scheduled", "status: played"))
        wrong = path.with_name("Different.result.json")
        wrong.write_text(json.dumps(result))
        records[0]["source"] = wrong
        with self.assertRaisesRegex(ValueError, "declared by its closed game"):
            load_recorded_shots(self.player, self.identity, records, "2003-11-30")

    def test_legacy_backfill_and_new_result_missing_tracking_are_rejected(self):
        _, _, result = self.tracked_game()
        result["kernel"] = "2003.6"
        self.assertTrue(any("legacy" in e for e in spatial_result_errors(result)))
        result["kernel"] = "2003.7"
        result.pop("shot_tracking")
        result.pop("shots")
        self.assertTrue(spatial_result_errors(result))
        result["kernel"] = "2003.6"
        self.assertEqual(engine_result_shots(result, source_ref="old.result.json"), [])

    def test_geometry_identity_clock_provenance_and_reconciliation_tampering_fail(self):
        _, _, valid = self.tracked_game()
        mutations = [
            lambda r: r["shots"][0].update(player_id="unlisted"),
            lambda r: r["shots"][0].update(side="away"),
            lambda r: r["shots"][0].update(x=math.nan),
            lambda r: r["shots"][0].update(x=True),
            lambda r: r["shots"][0].update(x=26),
            lambda r: r["shots"][0].update(zone="corner_three"),
            lambda r: r["shots"][0].update(value=3),
            lambda r: r["shots"][0].update(made=False),
            lambda r: r["shots"][0].update(made=1),
            lambda r: r["shots"][0].update(period=5),
            lambda r: r["shots"][0].update(clock_seconds=721),
            lambda r: r["shots"][1].update(clock_seconds=719),
            lambda r: r["shots"][0].update(transition=1),
            lambda r: r["shots"][1].update(shot_id=r["shots"][0]["shot_id"]),
            lambda r: r["shots"].pop(),
            lambda r: r["shots"][0].update(synthetic=True),
            lambda r: r["shot_tracking"].update(source_type="recorded_event_feed"),
            lambda r: r["shot_tracking"].update(prior_sha256="bad"),
            lambda r: r["team_stats"]["home"].update(fga=3),
            lambda r: r["player_stats"]["home"][0].update(seconds=0),
            lambda r: r["period_scores"]["home"].__setitem__(0, 1),
            lambda r: r["shots"][2].update(made=False),  # corrupt opponent, not displayed player
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(mutation=index):
                raw = deepcopy(valid)
                mutate(raw)
                self.assertTrue(spatial_result_errors(raw))
                with self.assertRaises(ValueError):
                    engine_result_shots(raw, source_ref="Game_1.result.json")

    def test_reader_requires_versioned_completed_dated_result(self):
        _, _, valid = self.tracked_game()
        for changes in ({"kernel": None}, {"terminated": False}, {"game_date": "2003-99-99"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                engine_result_shots({**valid, **changes}, source_ref="Game_1.result.json")


if __name__ == "__main__":
    unittest.main()
