import json
import unittest
from pathlib import Path

from runtime.season_rules import month_week, next_series_game_number, series_over

ROOT = Path(__file__).resolve().parents[1]


class CalendarWeekTests(unittest.TestCase):
    def test_week_boundaries(self):
        expected={1:1,7:1,8:2,14:2,15:3,21:3,22:4,28:4,29:4,30:4,31:4}
        for day,week in expected.items():
            with self.subTest(day=day):
                self.assertEqual(month_week(day),week)

    def test_no_week_five(self):
        self.assertEqual(month_week(31),4)


class BestOfSevenTests(unittest.TestCase):
    def test_series_end(self):
        self.assertTrue(series_over(4,0))
        self.assertTrue(series_over(2,4))
        self.assertFalse(series_over(3,3))

    def test_conditional_games(self):
        self.assertEqual(next_series_game_number(2,2),5)
        self.assertEqual(next_series_game_number(3,2),6)
        self.assertEqual(next_series_game_number(3,3),7)
        self.assertIsNone(next_series_game_number(4,2))


class CareerLayoutTests(unittest.TestCase):
    def test_season_is_nested_under_player(self):
        self.assertTrue((ROOT/"career/PLAYER/YEAR/06_Regular_Season").is_dir())
        self.assertFalse((ROOT/"06_Regular_Season").exists())

    def test_team_state_is_ai_owned(self):
        base=ROOT/"career/PLAYER/YEAR/00_Team"
        for rel in ("team_config.json","Team/roster.json","Team/rotation.json","Finances/finance.json"):
            data=json.loads((base/rel).read_text(encoding="utf-8"))
            self.assertEqual(data["owner"],"ai_gm")

    def test_player_card_template_exists(self):
        self.assertTrue((ROOT/"career/PLAYER/YEAR/00_Team/Team/Player_Cards/TEMPLATE.md").is_file())

    def test_empty_postseason_has_no_game_placeholders(self):
        season=ROOT/"career/PLAYER/YEAR"
        self.assertFalse(any((season/"07_Play_In_Tournament").glob("Game_*.md")))
        for folder in ("First_Round","Conference_Semifinals","Conference_Finals","Finals"):
            self.assertFalse(any((season/"08_Playoffs"/folder).glob("Game_*.md")))


if __name__ == "__main__":
    unittest.main()
