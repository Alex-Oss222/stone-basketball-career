"""The season award hubs and month status lines (`runtime/award_pages.py`): built from the source records only, dated by
the career clock, WINNER only after a vote's close date, and validated against the records they show."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from runtime import award_decisions as A
from runtime import award_pages as P
from runtime.seasons import month_weeks

ROOT = Path(__file__).resolve().parents[1]
SEASON = "2005-06"
LEAGUE = P.LEAGUE / SEASON
STALE = ("# NBA awards | 2003-04\n\n[Stats hub](../../README.md)\n\n2003-04 · Calendar coverage: 2003-04\n\n"
         "As of October 1, 2005: no award decisions closed.\n\n## By month\n\n| Period | Calendar dates | Closed decisions | Status |\n"
         "| --- | --- | ---: | --- |\n| [November 2005](11_November/League_Awards.md) | November 1-30, 2005 | 0 | No award filed |\n")
MONTH = ("# NBA awards | {label}\n\n2005-06 · Calendar coverage: {label}\n\nAs of October 1, 2005: no award decisions closed.\n\n"
         "## Player of the Month\n\nbody\n")


def decisions(clock):
    """Every weekly and monthly decision the 2005-06 calendar closes by the clock, filed where the rule files it."""
    out = []
    for award, start, end, announced in A.periods(SEASON, ROOT):
        if announced > clock:
            continue
        for conf in ("East", "West"):
            out.append({"id": f"{SEASON}-{award}-{start}-{conf.lower()}", "award": award, "name": A.AWARDS[award],
                        "conference": conf, "period_start": start, "period_end": end, "announced_on": announced,
                        "filed_on": A.filed_page(award, end, SEASON).as_posix(), "shortlist": [], "winner": f"{conf} {award}"})
    return out


def tally(names):
    return [{"player": n, "team": f"{n} Club", "points": 100 - i, "first_place": 10 - i} for i, n in enumerate(names)]


class Scratch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.set_clock("2005-12-12")
        self.put(LEAGUE / "award_decisions.json", {"season": SEASON, "decisions": decisions("2005-12-12")})
        (self.root / LEAGUE / "League_Awards.md").write_text(STALE, encoding="utf-8")
        for name, m, y, folder, weeks in month_weeks(SEASON, ROOT):
            path = self.root / LEAGUE / folder / "League_Awards.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(MONTH.format(label=f"{name} {y}"), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def put(self, rel, data):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=1), encoding="utf-8")

    def set_clock(self, day):
        self.put(Path("career/Dwyane_Wade") / SEASON / "current_state.json", {"season": SEASON, "current_date": day})

    def page(self):
        return (self.root / LEAGUE / "League_Awards.md").read_text(encoding="utf-8")

    def month(self, folder):
        return (self.root / LEAGUE / folder / "League_Awards.md").read_text(encoding="utf-8")


class SeasonPageTests(Scratch):
    def test_its_own_season_the_clock_and_counts_by_filed_page(self):
        P.write_pages(self.root)
        text = self.page()
        self.assertTrue(text.startswith("# NBA awards | 2005-06\n"))
        self.assertIn("\n2005-06 · Calendar coverage: 2005-06\n", text)
        self.assertNotIn("2003-04", text)
        self.assertIn("As of December 12, 2005: 16 weekly and monthly award decision(s) closed; 0 of 10 season awards decided.", text)
        # November holds its 8 weekly and 4 monthly decisions; December's first two weeks are filed, its month award is not.
        self.assertIn("| [November 2005](11_November/League_Awards.md) | November 1-30, 2005 | 12 | Decided |", text)
        self.assertIn("| [December 2005](12_December/League_Awards.md) | December 1-31, 2005 | 4 | In progress |", text)
        self.assertIn("| [January 2006](01_January/League_Awards.md) | January 1-31, 2006 | 0 | No award filed |", text)

    def test_an_open_vote_keeps_empty_slots_with_its_close_date(self):
        P.write_pages(self.root)
        text = self.page()
        self.assertIn("| 1 | Pending | N/A | N/A | N/A | Awaiting vote (closes May 7, 2006) |", text)
        self.assertIn("Selection closes May 17, 2006", text)
        self.assertNotIn("| **WINNER** |", text)
        self.assertIn("No All-Star selection announced yet: starters February 2, 2006", text)
        self.assertIn("Not decided yet. The playoffs open April 22, 2006.", text)

    def test_winner_only_once_the_announcement_date_has_passed(self):
        mvp = {"id": f"{SEASON}-mvp", "award": "mvp", "name": "Most Valuable Player", "announced_on": "2006-05-07",
               "electorate": 125, "voters": "media", "ballot": [10, 7, 5, 3, 1], "evidence_through": "2006-04-19",
               "winners": ["B"], "tally": tally(["A", "B", "C", "D"])}
        self.put(LEAGUE / "season_awards.json", {"season": SEASON, "decisions": [mvp]})
        P.write_pages(self.root)                                            # a record dated after the clock is not shown
        self.assertNotIn("| **WINNER** |", self.page())
        self.set_clock("2006-05-07")
        P.write_pages(self.root)
        text = self.page()
        self.assertIn("| 1 | B | B Club | 9 | 99 | **WINNER** |", text)     # the winner leads, the tally order kept
        self.assertIn("| 2 | A | A Club | 10 | 100 | Runner-up |", text)
        self.assertIn("| 3 | C | C Club | 8 | 98 | Third |", text)
        self.assertIn("1 of 10 season awards decided", text)
        self.assertEqual(P.page_errors(self.root), [])

    def test_teams_all_stars_champion_and_finals_mvp(self):
        team = lambda names, pos: [{"player": n, "team": "X", "position": p} for n, p in zip(names, pos)]
        self.put(LEAGUE / "season_awards.json", {"season": SEASON, "decisions": [
            {"id": f"{SEASON}-all_nba", "award": "all_nba", "name": "All-NBA Teams", "announced_on": "2006-05-17", "electorate": 126,
             "voters": "media", "ballot": [5, 3, 1], "teams": [{"team": "First Team", "players": team(
                 ["F1", "G1", "C1", "G2", "F2", "G3"], ["F", "G", "C", "G", "F", "G"])}]},     # a tie at the cut: three guards
            {"id": f"{SEASON}-finals_mvp", "award": "finals_mvp", "name": "Finals MVP", "announced_on": "2006-06-20",
             "electorate": 10, "voters": "media panel", "ballot": [1], "winners": ["Z"], "tally": tally(["Y", "Z"]),
             "tie_draw": "career/x/Award_Draws/2005-06-finals_mvp.decision.result.json"}]})
        self.put(LEAGUE / "all_star.json", {"season": SEASON, "steps": [{"step": "starters", "announced_on": "2006-02-02"},
                                                                          {"step": "reserves", "announced_on": "2006-02-09"}],
                                             "all_stars": [{"player": "S1", "team": "T", "conference": "East", "role": "starter",
                                                            "selected_on": "2006-02-02"},
                                                           {"player": "R1", "team": "T", "conference": "West", "role": "reserve",
                                                            "selected_on": "2006-02-09"}]})
        stars = LEAGUE / "all_star.json"
        record = json.loads((self.root / stars).read_text())
        self.set_clock("2006-02-17")
        record["steps"].append({"step": "replacements", "announced_on": "2006-02-17", "conferences": {"East": [], "West": []}})
        self.put(stars, record)
        P.write_pages(self.root)                       # a replacements step that names nobody is worded as such
        self.assertIn("(head coaches), no injury replacement named by the Commissioner (February 17, 2006).", self.page())
        record["steps"][-1]["conferences"]["East"] = [{"out": "S1", "replacement": "R2", "replacement_team": "T"}]
        record["all_stars"].append({"player": "R2", "team": "T", "conference": "East", "role": "injury replacement",
                                    "selected_on": "2006-02-17", "replacing": "S1"})
        self.put(stars, record)
        P.write_pages(self.root)
        text = self.page()
        self.assertIn("(head coaches), 1 injury replacement named February 17, 2006 (the Commissioner).", text)
        self.assertIn("| East | Injury replacement for S1 | R2 | T | February 17, 2006 |", text)
        self.put(LEAGUE / "playoffs.json", {"season": SEASON, "series": [
            {"round": "finals", "clubs": ["East Club", "West Club"], "wins": {"East Club": 2, "West Club": 4},
             "winner": "West Club", "clinched_on": "2006-06-20"}]})
        self.set_clock("2006-06-21")
        P.write_pages(self.root)
        text = self.page()
        self.assertIn("| First | G1 (X) | G2 (X) / G3 (X) | F1 (X) | F2 (X) | C1 (X) |", text)
        self.assertIn("| East | Starter | S1 | T | February 2, 2006 |", text)
        self.assertIn("**West Club**, Finals clinched June 20, 2006 over the East Club, 4-2.", text)
        self.assertIn("| 1 | Z | Z Club | 9 | 99 | **WINNER** |", text)           # the engine-drawn winner on No. 1
        self.assertIn("winner was drawn by the engine (`2005-06-finals_mvp.decision.result.json`)", text)
        self.assertEqual(P.page_errors(self.root), [])

    def test_the_rollover_builds_the_page_without_the_previous_seasons(self):
        from runtime.season_pages import Builder
        built = Builder(SEASON, self.root).awards("season", clock="2005-10-01")
        self.assertEqual(built, P.season_page(SEASON, self.root, "2005-10-01"))
        self.assertTrue(built.startswith("# NBA awards | 2005-06\n"))
        self.assertIn("As of October 1, 2005: no award decisions closed.", built)      # nothing announced by that date
        self.assertFalse((self.root / P.LEAGUE / "2004-05").exists())


class MonthStatusTests(Scratch):
    def test_each_month_line_is_restated_from_the_records(self):
        P.write_pages(self.root)
        self.assertIn("As of December 12, 2005: 4 award decision(s) closed, announced December 2, 2005; "
                      "8 Player of the Week decision(s) closed on this month's week pages.", self.month("11_November"))
        self.assertIn("As of December 12, 2005: no month award decision closed (Player and Rookie of the Month announced "
                      "January 2, 2006); 4 Player of the Week decision(s) closed on this month's week pages, announced "
                      "December 5, 2005, December 12, 2005.", self.month("12_December"))
        self.assertIn("As of December 12, 2005: no award decisions closed.", self.month("01_January"))
        self.assertIn("## Player of the Month\n\nbody\n", self.month("12_December"))          # only the status line moves

    def test_a_closed_season_is_dated_at_the_end_of_its_league_year(self):
        self.assertEqual(P.as_of("2004-05", "2005-12-12", ROOT), "2005-06-30")
        self.assertEqual(P.as_of(SEASON, "2005-12-12", ROOT), "2005-12-12")


class ValidationTests(Scratch):
    def test_a_stale_page_and_a_contradicting_month_line_are_refused(self):
        errors = P.page_errors(self.root)
        self.assertTrue(any("title reads '# NBA awards | 2003-04'" in e for e in errors))
        self.assertTrue(any("decisions by month" in e for e in errors))
        self.assertTrue(any("closed decisions reads (0, 0)" in e for e in errors))
        self.assertTrue(any("12_December/League_Awards.md: status" in e for e in errors))
        self.assertNotEqual(P.write_pages(self.root, write=False), [])
        P.write_pages(self.root)
        self.assertEqual(P.page_errors(self.root), [])
        self.assertEqual(P.write_pages(self.root), [])                       # a second run changes nothing

    def test_the_month_line_award_decisions_writes_is_accepted(self):
        P.write_pages(self.root)
        path = self.root / LEAGUE / "11_November/League_Awards.md"
        text = path.read_text(encoding="utf-8")
        line = "As of December 12, 2005: 4 award decision(s) closed, announced December 2, 2005."    # render_pages' words
        path.write_text(P._with_status(text, line), encoding="utf-8")
        self.assertEqual(P.page_errors(self.root), [])
        path.write_text(P._with_status(text, "As of December 12, 2005: 3 award decision(s) closed, announced December 2, 2005."),
                        encoding="utf-8")
        self.assertEqual(len(P.page_errors(self.root)), 1)


class WriteBackTests(Scratch):
    """The write-back owns the pages: a light (daily) run restates them on a decision day, and its --check reports a
    stale one. The write-back's other steps need a career copy and are replaced by no-ops here."""

    def no_other_steps(self):
        from runtime import miami_cards, team_status, write_back
        return [mock.patch.object(write_back, "pending_notes", return_value=([], [])),
                mock.patch.object(write_back, "extend_registry", return_value=[]),
                mock.patch.object(write_back, "sync_note_statuses", return_value=0),
                mock.patch.object(write_back, "closed_lines", return_value=([], [])),
                mock.patch.object(write_back, "miami_notes", return_value=[]),
                mock.patch.object(write_back, "miami_card_paths", return_value={}),
                mock.patch.object(write_back, "statistics_pages", return_value={}),
                mock.patch.object(miami_cards, "refresh", return_value=[]),
                mock.patch.object(miami_cards, "sync_register_roles", return_value=[]),
                mock.patch.object(team_status, "refresh", return_value=[]),
                mock.patch("runtime.league_cards.check_cards", return_value=[])]

    def test_a_light_run_restates_the_pages_on_a_decision_day(self):
        from runtime import write_back
        for patch in self.no_other_steps():
            patch.start()
            self.addCleanup(patch.stop)
        P.write_pages(self.root)
        self.set_clock("2005-12-19")                  # the day's Player of the Week closes and renders its week rows
        self.put(LEAGUE / "award_decisions.json", {"season": SEASON, "decisions": decisions("2005-12-19")})
        self.assertTrue(any("12_December/League_Awards.md: status" in e for e in P.page_errors(self.root)))
        stale = write_back.write_back_errors(self.root, SEASON, cards=True)
        self.assertIn(f"{(LEAGUE / 'League_Awards.md').as_posix()}: stale award page; run scripts/write_back_results.py --write",
                      stale)
        self.assertEqual(write_back.write_back_errors(self.root, SEASON), [])     # validation reads page_errors instead
        report = write_back.run(self.root, SEASON, write=True, pages=False)
        self.assertGreater(report["pages"], 0)
        self.assertIn("6 Player of the Week decision(s) closed on this month's week pages", self.month("12_December"))
        self.assertIn("| [December 2005](12_December/League_Awards.md) | December 1-31, 2005 | 6 | In progress |", self.page())
        self.assertEqual(P.page_errors(self.root), [])
        self.assertEqual(write_back.write_back_errors(self.root, SEASON, cards=True), [])
        self.assertEqual(write_back.run(self.root, SEASON, write=True, pages=False)["pages"], 0)


class RecordedSeasonsTests(unittest.TestCase):
    """The closed seasons' recorded decisions, read only: what the rebuilt hubs show."""

    def test_the_page_shows_what_the_records_hold(self):
        for season in P.seasons_on_file(ROOT):
            m = P.model(season, ROOT, "2005-12-12")
            self.assertEqual(P.page_facts(P.season_page(season, ROOT, m=m)), P.facts(m), season)

    def test_2004_05(self):
        m = P.model("2004-05", ROOT, "2005-12-12")
        facts = P.facts(m)
        self.assertEqual(facts["title"], "# NBA awards | 2004-05")
        self.assertEqual(facts["closed decisions"], (74, 10))
        self.assertEqual(list(facts["decisions by month"].values()), [12, 12, 14, 12, 12, 12])
        self.assertEqual(facts["Most Valuable Player winner"], ["Vince Carter"])
        self.assertEqual(facts["Finals MVP winner"], ["Mike Bibby"])
        self.assertEqual(facts["champion"], "Sacramento Kings")
        self.assertEqual(len(facts["All-Star selections"]), 25)
        self.assertIn("As of June 30, 2005:", P.season_page("2004-05", ROOT, m=m))


if __name__ == "__main__":
    unittest.main()
