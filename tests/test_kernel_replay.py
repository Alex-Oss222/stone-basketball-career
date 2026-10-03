"""An engine upgrade preserves closed games and refuses changed or unfinished inputs."""
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
LEGACY_KERNEL = "2003.5"
REQUEST = {
    "event_id": "legacy-fixture", "game_date": "2003-10-28", "game_type": "regular", "venue": "home",
    "home": {"team": "Miami Heat", "baseline": "library/2003/league/nba_2003_end_of_season.json"},
    "away": {"team": "Orlando Magic", "baseline": "library/2003/league/nba_2003_end_of_season.json"},
}


class KernelReplayTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        library = self.root / "library/2003/league"
        library.mkdir(parents=True)
        for name in ("nba_2003_end_of_season.json", "nba_2002_03_league_environment.json",
                     "nba_2002_03_player_stats.json", "nba_2003_veteran_ratings.json"):
            (library / name).write_bytes((ROOT / "library/2003/league" / name).read_bytes())
        self.request = self.root / "career/Game_1.request.json"
        self.request.parent.mkdir(parents=True)
        self.request.write_text(json.dumps(REQUEST))
        self.store = Store(self.root / "engine.sqlite3")
        with mock.patch.object(private_service, "KERNEL_VERSION", LEGACY_KERNEL):
            self.store.initialize()
        home, away, kwargs = load_request(self.request, self.root)
        with mock.patch.object(game_runner, "KERNEL_VERSION", LEGACY_KERNEL):
            self.packet = game_runner.freeze_inputs(home, away, self.store, **kwargs)[2]
        # Pin the legacy packet shape independently of the evolving dataclasses.
        for side in ("home", "away"):
            self.assertEqual(set(self.packet[side]), {"team_id", "players", "pace", "rest_days", "injuries"})
            for player in self.packet[side]["players"]:
                self.assertEqual(set(player), {"player_id", "position", "minutes", "ratings", "stat_profile",
                                               "availability", "age"})
        self.packet_hash = hashlib.sha256(canonical(self.packet)).hexdigest()
        self.reference = self.store.close_event(self.packet)
        # Replay must serve the stored result as-is, including absent new fields.
        self.original = {"event_id": REQUEST["event_id"], "kernel": LEGACY_KERNEL,
                         "game_date": REQUEST["game_date"], "final_score": {"home": 90, "away": 89},
                         "player_stats": {"home": [{"player_id": "legacy", "seconds": 1800}], "away": []}}

    def save_result(self):
        self.store.save_result(REQUEST["event_id"], self.packet_hash, self.original)

    def upgraded_scan(self):
        with mock.patch.object(game_runner, "KERNEL_VERSION", "2003.6"), \
                mock.patch.object(private_service, "KERNEL_VERSION", "2003.6"), \
                mock.patch.object(game_runner, "resolve_game", side_effect=AssertionError("closed game redrawn")):
            restarted = Store(self.store.path)
            restarted.initialize()
            return play_requests(restarted, self.root)

    def test_upgrade_serves_old_result_and_verifies_its_original_packet(self):
        self.save_result()
        status = self.upgraded_scan()
        self.assertEqual(status[REQUEST["event_id"]]["status"], "already_played")
        self.assertEqual(self.store.result(REQUEST["event_id"]), self.original)
        self.assertEqual(self.store.close_event(self.packet), self.reference)
        self.assertEqual(self.store.kernel_history(), [(LEGACY_KERNEL, "2003.6")])

    def test_edited_request_still_refused_after_upgrade(self):
        self.save_result()
        self.request.write_text(json.dumps(dict(REQUEST, venue="neutral")))
        entry = next(iter(self.upgraded_scan().values()))
        self.assertEqual(entry["status"], "error")
        self.assertIn("altered packet refused", entry["error"])
        self.assertEqual(self.store.result(REQUEST["event_id"]), self.original)

    def test_changed_dated_environment_still_refused_after_upgrade(self):
        self.save_result()
        path = self.root / "library/2003/league/nba_2002_03_league_environment.json"
        data = json.loads(path.read_text())
        data["engine_assumptions"]["home_edge_points_per_game"] += 0.1
        path.write_text(json.dumps(data))
        entry = next(iter(self.upgraded_scan().values()))
        self.assertEqual(entry["status"], "error")
        self.assertIn("altered packet refused", entry["error"])
        self.assertEqual(self.store.result(REQUEST["event_id"]), self.original)

    def test_old_journal_without_result_fails_closed_before_drawing(self):
        entry = next(iter(self.upgraded_scan().values()))
        self.assertEqual(entry["status"], "error")
        self.assertIn("altered packet refused", entry["error"])
        self.assertIsNone(self.store.result(REQUEST["event_id"]))
        self.assertEqual(self.store.close_event(self.packet), self.reference)


if __name__ == "__main__":
    unittest.main()
