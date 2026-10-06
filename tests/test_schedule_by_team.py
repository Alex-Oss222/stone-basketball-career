"""The 2004-05 schedule by team agrees with the game schedule the builders play from."""
import json
from pathlib import Path
import tempfile
import unittest

from runtime.schedule import by_team_errors

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "library/2004/league/nba_2004_05_schedule_by_team.json"


class ByTeamTests(unittest.TestCase):
    def test_the_real_file_agrees(self):
        self.assertEqual(by_team_errors(FILE, ROOT), [])

    def test_a_one_sided_game_is_caught(self):
        teams = json.loads(FILE.read_text(encoding="utf-8"))
        teams["Miami Heat"][0]["date"] = "2004-11-04"
        with tempfile.TemporaryDirectory() as tmp:
            league = Path(tmp) / "library/2004/league"
            league.mkdir(parents=True)
            (league / FILE.name).write_text(json.dumps(teams), encoding="utf-8")
            (league / "nba_2004_05_schedule.json").write_text(
                (ROOT / "library/2004/league/nba_2004_05_schedule.json").read_text(encoding="utf-8"), encoding="utf-8")
            errors = by_team_errors(league / FILE.name, Path(tmp))
        self.assertTrue(any("not both" in e for e in errors))
        self.assertTrue(any("differs from" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
