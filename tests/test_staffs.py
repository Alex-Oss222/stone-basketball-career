import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class LeagueStaffTests(unittest.TestCase):
    def files(self):
        return sorted((ROOT / "library").glob("*/league/nba_*_staffs.json"))

    def test_every_season_and_club_has_a_staff_without_results(self):
        self.assertEqual(len(self.files()), 12)                 # 2002-03 to 2013-14
        for path in self.files():
            data = json.loads(path.read_text())
            season = data["season"]
            if season != "2002-03":
                rosters = json.loads((ROOT / f"library/{season[:4]}/league/nba_{season[:4]}_{season[-2:]}_team_rosters.json").read_text())
                self.assertEqual(set(data["clubs"]), set(rosters["clubs"]), season)   # Miami's staff is simulated
            for club, entry in data["clubs"].items():
                head = entry["head_coaches"]
                self.assertTrue(head, (season, club))
                self.assertEqual(head[0]["window"][0], 0.0)
                self.assertEqual(head[-1]["window"][1], 1.0)
                self.assertNotIn("(", json.dumps(entry))          # no win-loss records

    def test_miami_real_staff_only_before_the_career(self):
        early = json.loads((ROOT / "library/2003/league/nba_2002_03_staffs.json").read_text())
        self.assertEqual(early["clubs"]["Miami Heat"]["head_coaches"][0]["name"], "Pat Riley")
        later = json.loads((ROOT / "library/2003/league/nba_2003_04_staffs.json").read_text())
        self.assertNotIn("Miami Heat", later["clubs"])


if __name__ == "__main__":
    unittest.main()
