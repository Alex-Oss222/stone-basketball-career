"""R5: the offseason pipelines by year (record paths, the later opening book, the driver's data guard)."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from runtime import free_agency_2004 as fa
from runtime import offseason

ROOT = Path(__file__).resolve().parents[1]


class RecordPathTests(unittest.TestCase):
    def test_market_year_and_record(self):
        self.assertEqual(fa.market_year("2005-06"), 2005)
        self.assertEqual(fa.record_for("2004-05"), fa.RECORD)                  # 2004 keeps its path
        self.assertEqual(fa.record_for("2005-06").as_posix(), "career/Dwyane_Wade/2004-05/10_Free_Agency/free_agency_2005.json")
        self.assertEqual(offseason.book_for("2005-06").as_posix(), "career/Dwyane_Wade/2005-06/League/opening_rosters.json")


class LaterBookTests(unittest.TestCase):
    def test_market_places_and_retired_players_stay_out(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel in ("library/careers/nba_player_careers.json", "library/2005/league/nba_2005_06_team_rosters.json"):
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                os.symlink(ROOT / rel, root / rel)
            record = {"clubs": {"Boston Celtics": [{"player": "Paul Pierce", "bbr_id": "piercpa01", "salary": 1}],
                                "Miami Heat": [{"player": "Dwyane Wade", "bbr_id": "wadedw01", "salary": 1}]},
                      "unsigned_pool": [{"player": "Karl Malone", "bbr_id": "malonka01"},           # retired after 2003-04
                                        {"player": "Derek Fisher", "bbr_id": "fishede01"}]}
            path = root / fa.record_for("2005-06")
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(record))
            book = offseason.later_book("2005-06", root)
            self.assertEqual([p["bbr_id"] for p in book["clubs"]["Boston Celtics"]], ["piercpa01"])
            self.assertEqual([p["bbr_id"] for p in book["not_placed"]], ["wadedw01"])
            self.assertEqual([p["bbr_id"] for p in book["pool"]], ["fishede01"])


class DriverGuardTests(unittest.TestCase):
    def run_day(self, day):
        return subprocess.run([sys.executable, str(ROOT / "scripts/offseason_day.py"), "--write", day], capture_output=True, text=True)

    @unittest.skipIf((ROOT / "library/2009/league/nba_2009_offseason_calendar.json").is_file(), "2009 data exists")
    def test_missing_year_data_stops_only_from_mid_may(self):
        self.assertEqual(self.run_day("2009-04-20").returncode, 0)
        late = self.run_day("2009-05-20")
        self.assertEqual(late.returncode, 2)
        self.assertIn("no 2009 offseason library data", late.stderr)


if __name__ == "__main__":
    unittest.main()
