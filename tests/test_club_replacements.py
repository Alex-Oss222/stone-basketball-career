"""Disturbed clubs: a real club that loses a rotation player to Miami signs a replacement from the dated pool."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from runtime import club_replacements as R
from runtime.rotations import holdings_path

ROOT = Path(__file__).resolve().parents[1]
DAY = "2003-12-05"


class ReplacementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        for folder in ("library", "career", "foundation"):
            shutil.copytree(ROOT / folder, cls.root / folder, ignore=shutil.ignore_patterns("*.html", "Players"))
        holdings = json.loads((cls.root / holdings_path("2003-04")).read_text())
        holdings["entries"].append({"player": "Clifford Robinson", "bbr_id": "robincl02", "from": DAY, "until": None,
                                    "basis": "test fixture: acquired by trade"})
        (cls.root / holdings_path("2003-04")).write_text(json.dumps(holdings, indent=1))
        # Fixture statuses (the live file is researched): one healthy free agent, one retired.
        (cls.root / R.STATUS_PATH).write_text(json.dumps({"schema_version": 1, "as_of": "2003-12-01", "players": {
            "williwa02": {"player": "Walt Williams", "status": "unsigned_available", "since": "2003-07-01"},
            "kerrst01": {"player": "Steve Kerr", "status": "retired", "since": "2003-06"}}}))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_a_rotation_loss_is_replaced_once_from_unsigned_players(self):
        hit = R.disturbed("2003-04", self.root)
        self.assertEqual([(club, s["player_id"]) for _, club, s in hit], [("Golden State Warriors", "Clifford Robinson")])
        self.assertTrue(R.replacement_errors(self.root))
        pool = R.pool(DAY, "2003-04", self.root)
        new = R.replace(self.root)
        self.assertEqual(len(new), 1)
        e = new[0]
        self.assertEqual((e["club"], e["replaces"], e["from"]), ("Golden State Warriors", "Clifford Robinson", DAY))
        self.assertEqual(set(pool), {"williwa02"})                         # a retired player is never signed
        self.assertEqual(e["player"], "Walt Williams")
        self.assertIn(e["terms"]["route"], ("cap room", "minimum exception"))
        self.assertEqual(R.replace(self.root), [])                         # once
        self.assertEqual(R.replacement_errors(self.root), [])
        self.assertIn(e["bbr_id"], R.held("2003-04", DAY, self.root))
        self.assertNotIn(e["bbr_id"], R.held("2003-04", "2003-12-04", self.root))
        self.assertEqual([a["bbr_id"] for a in R.arrivals("2003-04", "Golden State Warriors", DAY, self.root)], [e["bbr_id"]])

    def test_the_replacement_dresses_for_his_new_club_in_game_inputs(self):
        from runtime.game_requests import _club
        from runtime.player_stats import load_rating_index
        R.replace(self.root)
        index = load_rating_index(DAY, "2003-04", self.root)
        names = lambda day: {p.player_id for p in _club({"team": "Golden State Warriors", "rotation": "real"}, None,
                                                        self.root, load_rating_index(day, "2003-04", self.root),
                                                        "2003-04", day).players}
        self.assertIn("Walt Williams", names(DAY))
        self.assertNotIn("Clifford Robinson", names(DAY))
        self.assertNotIn("Walt Williams", names("2003-12-03"))
        self.assertIsNotNone(index)

    def test_a_stale_status_snapshot_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "research a snapshot"):
            R.pool("2004-02-01", "2003-04", self.root)

    def test_the_live_career_has_no_disturbed_club_yet(self):
        self.assertEqual(R.replacement_errors(ROOT), [])


if __name__ == "__main__":
    unittest.main()
