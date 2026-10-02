import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from runtime.schedule import read_games, schedule_errors, schedule_path, validate_schedule

ROOT = Path(__file__).resolve().parents[1]
CLUBS = sorted(json.loads((ROOT / "library/2003/league/nba_2003_end_of_season.json").read_text())["clubs"])


def synthetic_season():
    """A legal 29-team, 82-game schedule: 41 circular pairing rounds, greedy dates."""
    rounds = [d for d in range(1, 15)] * 2 + list(range(1, 14))
    pairs = []
    for r, d in enumerate(rounds):
        for i in range(29):
            a, b = CLUBS[i], CLUBS[(i + d) % 29]
            pairs.append((a, b) if r % 2 else (b, a))
    busy, games = {}, []
    for away, home in pairs:
        day = 0
        while (away, day) in busy or (home, day) in busy:
            day += 1
        busy[(away, day)] = busy[(home, day)] = True
        games.append((date(2003, 10, 28) + timedelta(days=day), away, home))
    return games


class ScheduleImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        league = self.root / "library/2003/league"
        league.mkdir(parents=True)
        (league / "nba_2003_end_of_season.json").write_bytes(
            (ROOT / "library/2003/league/nba_2003_end_of_season.json").read_bytes())
        self.games = synthetic_season()

    def tearDown(self):
        self.tmp.cleanup()

    def write_bref_csv(self, games):
        lines = ["Date,Start (ET),Visitor/Neutral,PTS,Home/Neutral,PTS,,,Attend.,Notes"]
        for day, away, home in games:
            lines.append(f"\"{day.strftime('%a, %b %d, %Y')}\",7:30p,{away},101,{home},99,Box Score,,18000,")
        lines += ["Playoffs", "\"Sat, Apr 17, 2004\",8:00p,Milwaukee Bucks,96,Detroit Pistons,108,Box Score,,22076,"]
        path = self.root / "schedule.csv"
        path.write_text("\n".join(lines))
        return path

    def canonical(self, games):
        data = {"schema_version": 1, "league": "NBA", "season": "2003-04", "kind": "regular_season_schedule",
                "source": "test", "games": games}
        path = schedule_path("2003-04", self.root)
        path.write_text(json.dumps(data))
        return data

    def test_bref_export_imports_without_results_or_playoffs(self):
        games, stripped = read_games(self.write_bref_csv(self.games), set(CLUBS))
        self.assertEqual(len(games), 1189)
        self.assertIn("PTS", stripped)
        self.assertIn("Attend.", stripped)
        self.assertEqual(set(games[0]), {"game_id", "date", "away", "home"})
        data = self.canonical(games)
        self.assertEqual(validate_schedule(data, "2003-04", self.root), [])
        self.assertEqual(schedule_errors(self.root), [])

    def test_abbreviations_and_iso_dates(self):
        path = self.root / "s.csv"
        path.write_text("date,away,home\n2003-10-28,TOR,MIA\n")
        games, _ = read_games(path, set(CLUBS))
        self.assertEqual(games[0]["game_id"], "2003-10-28-toronto-raptors-at-miami-heat")

    def test_results_and_bad_counts_are_refused(self):
        games, _ = read_games(self.write_bref_csv(self.games), set(CLUBS))
        games[0] = dict(games[0], home_score=101)
        errors = validate_schedule(self.canonical(games), "2003-04", self.root)
        self.assertTrue(any("no results" in e for e in errors))
        games, _ = read_games(self.write_bref_csv(self.games[:-1]), set(CLUBS))
        errors = validate_schedule(self.canonical(games), "2003-04", self.root)
        self.assertTrue(any("expected 82" in e for e in errors))
        self.assertTrue(any("expected 1189" in e for e in errors))

    def test_unknown_team_is_refused(self):
        path = self.root / "s.csv"
        path.write_text("date,away,home\n2003-10-28,Charlotte Bobcats,Miami Heat\n")
        with self.assertRaises(ValueError):
            read_games(path, set(CLUBS))


class RepositorySchedules(unittest.TestCase):
    def test_2003_04_schedules(self):
        self.assertEqual(schedule_errors(ROOT), [])
        regular = json.loads((ROOT / "library/2003/league/nba_2003_04_schedule.json").read_text())
        miami = [g for g in regular["games"] if "Miami Heat" in (g["home"], g["away"])]
        self.assertEqual((len(regular["games"]), len(miami)), (1189, 82))
        self.assertEqual(miami[0]["game_id"], "2003-10-28-miami-heat-at-philadelphia-76ers")
        preseason = json.loads((ROOT / "library/2003/league/nba_2003_04_preseason_schedule.json").read_text())
        self.assertEqual(preseason["kind"], "preseason_schedule")
        self.assertEqual(len(preseason["games"]), 114)


    def test_eleven_seasons_on_file_with_real_exceptions(self):
        regular = sorted((ROOT / "library").glob("*/league/nba_*_??_schedule.json"))
        self.assertEqual(len(regular), 11)
        counts = {p.name[4:11]: len(json.loads(p.read_text())["games"]) for p in regular}
        self.assertEqual(counts["2011_12"], 990)
        self.assertEqual(counts["2012_13"], 1229)
        self.assertEqual(counts["2004_05"], 1230)


if __name__ == "__main__":
    unittest.main()
