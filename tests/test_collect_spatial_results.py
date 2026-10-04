"""Collection refuses broken spatial evidence before saving a result file."""
from copy import deepcopy

from scripts.collect_results import result_errors
from tests import test_engine_shot_feeds as feed_fixtures
from tests.test_live_player_cards import LiveCardFixtures


class CollectSpatialResultsTests(LiveCardFixtures):
    tracked_game = feed_fixtures.EngineShotFeedTests.tracked_game

    def test_collector_accepts_complete_engine_feed_and_refuses_a_missing_attempt(self):
        _, _, result = self.tracked_game()
        request = {"event_id": result["event_id"], "game_date": result["game_date"],
                   "game_type": result["game_type"],
                   "home": {"team": result["home"]}, "away": {"team": result["away"]}}
        self.assertEqual(result_errors(request, result, "game"), [])
        broken = deepcopy(result)
        broken["shots"].pop()
        self.assertTrue(any("reconcile" in error for error in result_errors(request, broken, "game")))

    def test_collector_cannot_silently_drop_all_tracking_from_a_spatial_result(self):
        _, _, result = self.tracked_game()
        result.pop("shots")
        result.pop("shot_tracking")
        self.assertTrue(result_errors({"event_id": result["event_id"]}, result, "game"))

    def test_collector_refuses_unfinished_or_misdated_spatial_evidence(self):
        _, _, result = self.tracked_game()
        request = {"event_id": result["event_id"], "game_date": result["game_date"],
                   "home": {"team": result["home"]}}
        for field, value in (("terminated", False), ("game_date", "2003-11-13"), ("home", "Wrong club")):
            with self.subTest(field=field):
                broken = deepcopy(result)
                broken[field] = value
                self.assertTrue(result_errors(request, broken, "game"))
