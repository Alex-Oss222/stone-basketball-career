"""League layout changes must preserve evidence and full registry coverage."""
from pathlib import Path
import unittest

from scripts.format_league_reports import COLUMNS, format_page, read_tables


class LeagueLayoutTests(unittest.TestCase):
    def setUp(self):
        self.page = Path("career/Player/Stats_and_Awards/League/2003-04/11_November/Week_1/League_Stats.md")
        self.asset = self.page.parents[3] / "assets/per_game.svg"
        self.registry = {"positions": ["PG"], "players": [
            {"name": "Example Player", "position": "PG", "birth_date": "1980-11-09"}]}
        self.text = """# NBA players | November | Week 1

## Players by position

<details>
<summary>PG · Point guards · 1 players</summary>

| Player | Club / rights | G | MPG | PPG | RPG | APG | SPG | BPG | TOV/G |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Example Player | TEST rights | 2 | 30.5 | 21.5 | 4.0 | 7.0 | 1.0 | 0.5 | 2.0 |

| Player | GS | FG% | 3P% | FT% |
| --- | --- | --- | --- | --- |
| Example Player | 1 | 45.5% | 33.3% | 80.0% |

</details>

[Award decisions](League_Awards.md)
"""

    def format(self, text=None):
        return format_page(text or self.text, self.page, self.registry, "2003-11-12", self.asset)

    def test_migration_preserves_values_and_does_not_invent_attempts(self):
        result = self.format()
        headers, rows = next(read_tables(result))
        self.assertEqual(headers, COLUMNS)
        row = rows[0]
        self.assertEqual((row["G"], row["GS"], row["MP"], row["PTS"], row["TRB"]), ("2", "1", "30.5", "21.5", "4.0"))
        self.assertEqual((row["FG%"], row["3P%"], row["FT%"]), (".455", ".333", ".800"))
        self.assertEqual((row["FGA"], row["2P"], row["eFG%"], row["PF"]), ("N/A",) * 4)
        self.assertEqual(row["Club / rights"], "TEST rights")
        self.assertEqual(row["Age"], "22")
        self.assertIn("[Award decisions](League_Awards.md)", result)
        self.assertEqual(result, self.format(result))

    def test_missing_or_duplicate_player_rows_stop_migration(self):
        duplicate = "| Example Player | TEST rights | 2 | 30.5 | 21.5 | 4.0 | 7.0 | 1.0 | 0.5 | 2.0 |\n"
        for changed in (self.text.replace("| Example Player | TEST rights", "| Someone Else | TEST rights"),
                        self.text.replace(duplicate, duplicate * 2)):
            with self.assertRaises(ValueError):
                self.format(changed)


if __name__ == "__main__":
    unittest.main()
