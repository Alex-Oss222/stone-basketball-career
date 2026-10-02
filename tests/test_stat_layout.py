import copy
import json
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree

from runtime.award_records import badge_labels, honors_in_scope, load_awards
from runtime.career_stats import COUNTS, normalize_line
from runtime.stat_layout import ReportStyle, personal_header
from scripts.validate_repository import markdown_tables

ROOT = Path(__file__).resolve().parents[1]
IDENTITY = json.loads((ROOT / "career/Dwyane_Wade/professional_identity.json").read_text())


def honor(**changes):
    value = dict(id="weekly-one", name="Player of the Week", short_name="POTW", status="earned",
                 competition="regular", season="2003-04", period_start="2003-11-01", period_end="2003-11-07",
                 awarded_on="2003-11-10", source="decision.md")
    value.update(changes)
    return value


def game(event_id, made, attempts, seconds):
    box = dict.fromkeys(COUNTS, 0)
    box.update(fgm=made, fga=attempts, pts=made*2, seconds=seconds, started=True)
    return dict(status="played", event_id=event_id, competition="regular", season="2003-04", date="2003-11-05",
                coverage="complete", appearance="Played", team="Miami Heat", line=normalize_line(box))


class HonorDateTests(unittest.TestCase):
    def test_announcement_and_period_end_are_separate(self):
        awards = [honor()]
        self.assertEqual(badge_labels(awards, "2003-11-07"), [])
        self.assertEqual(badge_labels(awards, "2003-11-10"), ["Player of the Week"])
        self.assertEqual(honors_in_scope(awards, known_on="2003-11-09", start="2003-11-01", end="2003-11-07"), [])
        self.assertEqual(honors_in_scope(awards, known_on="2003-11-10", start="2003-11-01", end="2003-11-07"), awards)
        self.assertEqual(honors_in_scope(awards, known_on="2003-11-10", start="2003-11-08", end="2003-11-14"), [])
        self.assertEqual(honors_in_scope(awards, known_on="2003-11-10", competition="playoff"), [])

    def test_only_sourced_earned_nonduplicate_honors_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "decision.md").write_text("# Closed award decision\nPlayer of the Week awarded.\n")
            def write(values):
                (root / "awards.json").write_text(json.dumps(dict(schema_version=1, awards=values)))
            write([honor()])
            self.assertEqual(len(load_awards(root, "2003-11-10")), 1)
            for bad in (honor(status="nominated"), honor(awarded_on="2003-11-11"), honor(source="missing.md"),
                        honor(period_start="2003-11-08"), honor(competition="nba_cup_championship")):
                write([bad])
                with self.subTest(bad=bad), self.assertRaises(ValueError):
                    load_awards(root, "2003-11-10")
            write([honor(), honor(id="second-id-same-honor")])
            with self.assertRaisesRegex(ValueError, "duplicate"):
                load_awards(root, "2003-11-10")

    def test_badges_group_repeated_honors_and_keep_full_names(self):
        awards = [honor(), honor(id="two", period_start="2003-11-08", period_end="2003-11-14", awarded_on="2003-11-17")]
        self.assertEqual(badge_labels(awards, "2003-11-17"), ["2× Player of the Week"])
        svg = personal_header(IDENTITY, "2003-11-17", awards)
        ElementTree.fromstring(svg)
        self.assertIn("2× Player of the", svg)
        self.assertIn("Week", svg)


class PerGameLayoutTests(unittest.TestCase):
    def test_reference_columns_keep_pooled_rates_and_per_game_counts(self):
        records = [game("one", 1, 2, 600), game("two", 4, 10, 1800)]
        style = ReportStyle(IDENTITY, [], "2003-11-10", {}, Path("assets"))
        md = style.per_game(Path("README.md"), [("Sample", records, None)])
        columns, rows = next(markdown_tables(md))
        row = dict(zip(columns, rows[0]))
        self.assertEqual(row["G"], "2")
        self.assertEqual(row["GS"], "2")
        self.assertEqual(row["MP"], "20.0")
        self.assertEqual(row["FG"], "2.5")
        self.assertEqual(row["FGA"], "6.0")
        self.assertEqual(row["FG%"], ".417")
        self.assertEqual(row["PTS"], "5.0")
        self.assertEqual(row["3P%"], "N/A")
        self.assertEqual(len(columns), len(rows[0]))

    def test_period_identity_does_not_take_a_later_jersey_or_age(self):
        identity = copy.deepcopy(IDENTITY)
        identity["snapshots"].append({**identity["snapshots"][0], "as_of": "2004-01-17", "team": "Later Team", "jersey": 3})
        style = ReportStyle(identity, [], "2004-02-01", {}, Path("assets"))
        page = Path("career/Dwyane_Wade/Stats_and_Awards/2003-04/01_January/Week_1/README.md")
        columns, rows = next(markdown_tables(style.per_game(page, [("Week 1", [], None)])))
        row = dict(zip(columns, rows[0]))
        self.assertEqual((row["Age"], row["Team"]), ("19", "Miami Heat"))
        asset = style.header(page, "2004-01-07")
        self.assertIn("2004-01-07.svg", asset)
        self.assertNotIn("Later Team", next(v for p, v in style.outputs.items() if p.name.startswith("personal_")))

    def test_empty_national_rows_do_not_assign_an_nba_club(self):
        style = ReportStyle(IDENTITY, [], "2003-06-26", {}, Path("assets"))
        page = Path("National_Team/World_Cup/README.md")
        columns, rows = next(markdown_tables(style.per_game(page, [("Qualifiers", [], None, {"competition": "world_cup_qualifier"})])))
        row = dict(zip(columns, rows[0]))
        self.assertEqual((row["Team"], row["Lg"], row["G"], row["PTS"]), ("Not selected", "FIBA", "0", "N/A"))

    def test_week_table_can_reference_later_confirmed_honor_without_backdating_banner(self):
        outputs = {}
        style = ReportStyle(IDENTITY, [honor()], "2003-11-10", outputs, Path("assets"))
        page = Path("Stats_and_Awards/2003-04/11_November/Week_1/README.md")
        md = style.per_game(page, [("Week 1", [], None)], as_of="2003-11-07")
        self.assertIn("POTW (example)", md)
        style.header(page, "2003-11-07")
        svg = next(v for p, v in outputs.items() if p.name.startswith("personal_"))
        self.assertIn("No earned professional honors", svg)
        self.assertNotIn("Player of the Week", svg)


if __name__ == "__main__":
    unittest.main()
