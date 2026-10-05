"""Weekly and monthly awards: periods, Game Score ranking, engine-drawn ties and Wade's honor register."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from runtime import award_decisions as A


def line(pid, pts, **kw):
    base = dict(player_id=pid, pts=pts, fgm=pts // 2, fga=pts // 2 + 6, ftm=0, fta=0, orb=1, drb=4, ast=3, stl=1, blk=0,
                tov=2, pf=2, minutes=34.0, seconds=2040.0)
    return dict(base, **kw)


def game(day, home, away, home_lines, away_lines, score=(100, 90)):
    return {"result": {"game_date": day, "event_id": f"{day}-{away}-{home}", "home": home, "away": away,
                       "final_score": {"home": score[0], "away": score[1]},
                       "player_stats": {"home": home_lines, "away": away_lines}}}


CONF = {"Miami Heat": "East", "Boston Celtics": "East", "Utah Jazz": "West", "Dallas Mavericks": "West"}


class PeriodTests(unittest.TestCase):
    def test_weeks_run_monday_to_sunday_from_opening_night_and_months_fold_october_into_november(self):
        periods = A.periods("2003-04")
        weeks = [p for p in periods if p[0] == "player_of_week"]
        self.assertEqual(weeks[0][1:], ("2003-10-28", "2003-11-02", "2003-11-03"))
        self.assertEqual(weeks[-1][2], "2004-04-14")
        first_month = [p for p in periods if p[0] == "rookie_of_month"][0]
        self.assertEqual(first_month[1:], ("2003-10-28", "2003-11-30", "2003-12-02"))
        self.assertEqual(A.filed_page("player_of_week", "2003-11-30", "2003-04").as_posix().split("/")[-3:],
                         ["11_November", "Week_4", "League_Awards.md"])
        self.assertEqual(A.filed_page("player_of_week", "2003-11-02", "2003-04").parent.name, "Week_1")

    def test_game_score_is_hollingers(self):
        p = dict(pts=20, fgm=8, fga=15, ftm=4, fta=5, orb=2, drb=6, stl=1, ast=5, blk=1, pf=3, tov=2)
        self.assertAlmostEqual(A.game_score(p), 20 + 3.2 - 10.5 - 0.4 + 1.4 + 1.8 + 1 + 3.5 + 0.7 - 1.2 - 2)


class RankingTests(unittest.TestCase):
    def test_week_needs_two_games_and_counts_wins_alike_for_every_player(self):
        rows = [game("2003-11-04", "Miami Heat", "Boston Celtics", [line("Wade", 30)], [line("Pierce", 30)]),
                game("2003-11-06", "Miami Heat", "Boston Celtics", [line("Wade", 20)], [line("Pierce", 20)], (90, 100)),
                game("2003-11-06", "Utah Jazz", "Dallas Mavericks", [line("Kirilenko", 40)], [line("Nowitzki", 10)])]
        table = A.rank("player_of_week", "2003-11-03", "2003-11-09", rows, CONF, set())
        self.assertEqual({x["player"] for x in table["East"]}, {"Wade", "Pierce"})
        self.assertEqual(table["East"][0]["score"], table["East"][1]["score"])     # one win each, same lines
        self.assertNotIn("West", table)                                             # one game is not a week

    def test_rookie_of_month_reads_only_first_season_players(self):
        rows = [game(f"2003-11-{d:02d}", "Miami Heat", "Boston Celtics", [line("Wade", 10), line("Jones", 30)],
                     [line("Pierce", 30)]) for d in (3, 5, 7)]
        table = A.rank("rookie_of_month", "2003-10-28", "2003-11-30", rows, CONF, {"Wade"})
        self.assertEqual([x["player"] for x in table["East"]], ["Wade"])


class DecideTests(unittest.TestCase):
    def test_a_tie_waits_for_the_engine_draw_and_a_wade_win_reaches_his_register(self):
        rows = [game(f"2003-11-{d:02d}", "Miami Heat", "Boston Celtics", [line("Dwyane Wade", 25)], [line("Paul Pierce", 25)],
                     (100, 90) if d == 4 else (90, 100)) for d in (4, 6)]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / A.PLAYER).mkdir(parents=True)
            (root / A.league_dir("2003-04")).mkdir(parents=True)
            (root / A.PLAYER / "awards.json").write_text(json.dumps({"schema_version": 1, "awards": []}))
            due = [("player_of_week", "2003-11-03", "2003-11-09", "2003-11-10")]
            with mock.patch.object(A, "due", lambda clock, *a, **k: due), \
                    mock.patch("runtime.write_back.closed_results", lambda *a, **k: rows), \
                    mock.patch.object(A, "conferences", lambda root=None, season=None: CONF), \
                    mock.patch.object(A, "rookies", lambda root=None, season=None: set()):
                new = A.decide(root, "2003-11-10")
                self.assertEqual([(d["conference"], d["winner"]) for d in new], [("West", None)])   # East tied: waits
                packet = root / A.draws_dir("2003-04") / "2003-04-player_of_week-2003-11-03-east.decision.json"
                self.assertEqual(json.loads(packet.read_text())["options"], {"Dwyane Wade": 0.5, "Paul Pierce": 0.5})
                packet.with_name("2003-04-player_of_week-2003-11-03-east.decision.result.json").write_text(
                    json.dumps({"outcome": "Dwyane Wade"}))
                new = A.decide(root, "2003-11-10")
                east = next(d for d in new if d["conference"] == "East")
                self.assertEqual((east["winner"], east["shortlist"][0]["player"]), ("Dwyane Wade", "Dwyane Wade"))
                self.assertIn("tie_draw", east)
                self.assertEqual(A.decide(root, "2003-11-10"), [])               # closed once, never recomputed
            honors = json.loads((root / A.PLAYER / "awards.json").read_text())["awards"]
            self.assertEqual([(h["name"], h["awarded_on"], h["status"]) for h in honors],
                             [("Eastern Conference Player of the Week", "2003-11-10", "earned")])


if __name__ == "__main__":
    unittest.main()
