"""Spatial inputs are journaled prospectively without changing legacy packets."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from runtime import game_runner, private_service
from runtime.game_requests import load_request
from runtime.packets import canonical
from runtime.private_service import Store, play_requests


ROOT = Path(__file__).resolve().parents[1]


class SpatialReplayTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        library = self.root / "library/2003/league"
        library.mkdir(parents=True)
        for name in ("nba_2003_end_of_season.json", "nba_2002_03_league_environment.json",
                     "nba_2002_03_player_stats.json", "nba_2003_veteran_ratings.json"):
            (library / name).write_bytes((ROOT / "library/2003/league" / name).read_bytes())
        request = {"event_id": "spatial-replay-fixture", "game_date": "2003-10-28",
                   "game_type": "regular", "venue": "home",
                   "home": {"team": "Miami Heat", "baseline": "library/2003/league/nba_2003_end_of_season.json"},
                   "away": {"team": "Orlando Magic", "baseline": "library/2003/league/nba_2003_end_of_season.json"}}
        self.path = self.root / "career/Game_1.request.json"
        self.path.parent.mkdir(parents=True)
        self.path.write_text(json.dumps(request))
        self.home, self.away, self.kwargs = load_request(self.path, self.root)
        self.store = Store(self.root / "engine.sqlite3")
        self.store.initialize()

    def freeze(self, version):
        return game_runner.freeze_inputs(self.home, self.away, self.store,
                                         kernel_version=version, **self.kwargs)[2]

    def save(self, packet):
        self.store.close_event(packet)
        result = {"event_id": packet["event_id"], "kernel": packet["procedure"],
                  "game_date": packet["game_date"], "unchanged_fixture": True}
        self.store.save_result(packet["event_id"], hashlib.sha256(canonical(packet)).hexdigest(), result)
        return result

    def test_legacy_replay_never_loads_new_spatial_data_or_draws_a_game(self):
        packet = self.freeze("2003.6")
        self.assertNotIn("spatial_environment", packet)
        original = self.save(packet)
        with mock.patch("runtime.spatial_shots.load_spatial_environment",
                        side_effect=AssertionError("legacy replay read future spatial inputs")), \
                mock.patch.object(game_runner, "resolve_game", side_effect=AssertionError("redraw")):
            status = play_requests(self.store, self.root)
        self.assertEqual(status[packet["event_id"]]["status"], "already_played")
        self.assertEqual(self.store.result(packet["event_id"]), original)
        self.assertEqual(self.freeze("2003.6"), packet)

    def test_spatial_configuration_is_frozen_and_changed_inputs_refused(self):
        prior = {"model_version": "test-spatial-prior", "source_digest": "original"}
        with mock.patch("runtime.spatial_shots.load_spatial_environment", return_value=prior):
            packet = self.freeze("2003.7")
            self.assertEqual(packet["spatial_environment"], prior)
            original = self.save(packet)
            with mock.patch.object(game_runner, "resolve_game", side_effect=AssertionError("redraw")):
                status = play_requests(self.store, self.root)
            self.assertEqual(status[packet["event_id"]]["status"], "already_played")
        changed = {**prior, "source_digest": "edited"}
        with mock.patch("runtime.spatial_shots.load_spatial_environment", return_value=changed), \
                mock.patch.object(game_runner, "resolve_game", side_effect=AssertionError("redraw")):
            entry = next(iter(play_requests(self.store, self.root).values()))
        self.assertEqual(entry["status"], "error")
        self.assertIn("altered packet refused", entry["error"])
        self.assertEqual(self.store.result(packet["event_id"]), original)

    def test_unfinished_legacy_event_is_not_redrawn_with_spatial_inputs(self):
        packet = self.freeze("2003.6")
        reference = self.store.close_event(packet)
        with mock.patch("runtime.spatial_shots.load_spatial_environment", return_value={"fixture": True}), \
                mock.patch.object(game_runner, "resolve_game", side_effect=AssertionError("redraw")):
            entry = next(iter(play_requests(self.store, self.root).values()))
        self.assertEqual(entry["status"], "error")
        self.assertIn("altered packet refused", entry["error"])
        self.assertIsNone(self.store.result(packet["event_id"]))
        self.assertEqual(self.store.close_event(packet), reference)


if __name__ == "__main__":
    unittest.main()
