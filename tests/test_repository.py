import tempfile
import unittest
from pathlib import Path

from runtime.season_rules import month_week, next_series_game_number, series_over


class CalendarWeekTests(unittest.TestCase):
    def test_week_boundaries(self):
        expected = {
            1: 1, 7: 1,
            8: 2, 14: 2,
            15: 3, 21: 3,
            22: 4, 28: 4, 29: 4, 30: 4, 31: 4,
        }
        for day, week in expected.items():
            with self.subTest(day=day):
                self.assertEqual(month_week(day), week)

    def test_no_week_five(self):
        self.assertEqual(month_week(31), 4)


class BestOfSevenTests(unittest.TestCase):
    def test_series_ends_at_four_wins(self):
        self.assertTrue(series_over(4, 0))
        self.assertTrue(series_over(2, 4))
        self.assertFalse(series_over(3, 3))

    def test_next_game_is_conditional(self):
        self.assertEqual(next_series_game_number(2, 2), 5)
        self.assertEqual(next_series_game_number(3, 2), 6)
        self.assertEqual(next_series_game_number(3, 3), 7)
        self.assertIsNone(next_series_game_number(4, 2))


class EmptyRepositoryStateTests(unittest.TestCase):
    def test_player_profile_starts_empty(self):
        root = Path(__file__).resolve().parents[1]
        text = (root / "state/player_profile.md").read_text(encoding="utf-8")
        self.assertIn("status: empty", text)
        self.assertIn("No player has been established yet.", text)


if __name__ == "__main__":
    unittest.main()
