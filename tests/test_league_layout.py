"""League layout changes must preserve evidence and full registry coverage."""
from pathlib import Path
import unittest

from runtime.stat_layout import markdown_table
from scripts.format_league_reports import COLUMNS, format_page, ratio, read_tables


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

    def test_efficiency_over_100_percent_is_preserved_without_relaxing_shooting_percentages(self):
        values = dict.fromkeys(COLUMNS, "N/A")
        values.update({"Player": "Example Player", "Club / rights": "TEST rights", "FG%": ".750",
                       "eFG%": "1.250", "TS% (est.)": "1.125"})
        table = markdown_table(COLUMNS, [[values[key] for key in COLUMNS]])
        text = "# League\n\n## Players by position\n\n<details>\n<summary>PG · Point guards</summary>\n\n" + table + "\n</details>"
        formatted = self.format(text)
        _, rows = next(read_tables(formatted))
        self.assertEqual((rows[0]["FG%"], rows[0]["eFG%"], rows[0]["TS% (est.)"]), (".750", "1.250", "1.125"))
        self.assertEqual(formatted, self.format(formatted))
        self.assertEqual(ratio("125%", maximum=1.5), "1.250")
        with self.assertRaises(ValueError):
            ratio("125", maximum=1.5)     # an unlabeled percent is still ambiguous
        with self.assertRaises(ValueError):
            self.format(text.replace(".750", "1.250"))   # a raw FG percentage cannot exceed one


if __name__ == "__main__":
    unittest.main()
