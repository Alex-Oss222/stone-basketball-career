import json
import unittest
from copy import deepcopy
from pathlib import Path

from runtime.season_rules import month_week, next_series_game_number, series_over
from scripts.validate_repository import finance_errors

ROOT=Path(__file__).resolve().parents[1]
PLAYER=ROOT/"career/Dwyane_Wade"
SEASON=PLAYER/"2003-04"
TEAM=SEASON/"00_Team"


class CalendarWeekTests(unittest.TestCase):
    def test_week_boundaries(self):
        expected={1:1,7:1,8:2,14:2,15:3,21:3,22:4,28:4,29:4,30:4,31:4}
        for day,week in expected.items():
            with self.subTest(day=day):
                self.assertEqual(month_week(day),week)


class BestOfSevenTests(unittest.TestCase):
    def test_series_rules(self):
        self.assertTrue(series_over(4,0))
        self.assertFalse(series_over(3,3))
        self.assertEqual(next_series_game_number(2,2),5)
        self.assertEqual(next_series_game_number(3,2),6)
        self.assertEqual(next_series_game_number(3,3),7)
        self.assertIsNone(next_series_game_number(4,2))


class InitializedCareerTests(unittest.TestCase):
    def test_player_and_team(self):
        self.assertTrue((PLAYER/"Dwyane_Wade_Player_Profile.md").is_file())
        state=json.loads((SEASON/"current_state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["team"],"Miami Heat")
        self.assertEqual(state["draft"]["overall"],5)

    def test_organization_files(self):
        for name in ("Micky_Arison","Pat_Riley","Randy_Pfund","Andy_Elisburg","Chet_Kammerer"):
            self.assertTrue((TEAM/"Organization"/f"{name}.md").is_file())

    def test_every_roster_player_has_card(self):
        roster=json.loads((TEAM/"Team/Roster/roster.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(roster["players"]),17)
        for player in roster["players"]:
            self.assertTrue((TEAM/"Team/Player_Cards"/f"{player['id']}.md").is_file())

    def test_player_cards_follow_current_template(self):
        roster=json.loads((TEAM/"Team/Roster/roster.json").read_text(encoding="utf-8"))
        sections=[
            "## Scouting report",
            "## Player grades",
            "## Changes and coaching notes",
            "## Sources and uncertainty",
            "## Regular-season statistics by year",
            "## Playoff statistics by year",
            "## Awards and honors",
        ]
        for player in roster["players"]:
            text=(TEAM/"Team/Player_Cards"/f"{player['id']}.md").read_text(encoding="utf-8")
            positions=[text.index(section) for section in sections]
            self.assertEqual(positions,sorted(positions))
            self.assertEqual(text.rfind("## Awards and honors"),positions[-1])

    def test_depth_chart_is_holding_chart(self):
        depth=json.loads((TEAM/"Team/Depth_Chart/depth_chart.json").read_text(encoding="utf-8"))
        self.assertFalse(depth["game_ready"])
        names={p["name"] for p in depth["unassigned_draft_rights"]}
        self.assertEqual(names,{"Dwyane Wade","Jerome Beasley"})

    def test_cap_room_stays_unresolved_on_draft_day(self):
        finance=json.loads((TEAM/"Finances/finance.json").read_text(encoding="utf-8"))
        self.assertIsNone(finance["cap_room"])
        carter=next(x for x in finance["pending_control_items"] if x["player"]=="Anthony Carter")
        self.assertEqual(carter["status"],"pending")
        self.assertEqual(carter["deadline"],"2003-06-30")

    def test_cap_sheet_structure(self):
        cap=(TEAM/"Finances/cap_sheet.md").read_text(encoding="utf-8")
        for heading in ("## Current cap position","## Eight-season commitments","## Signed contract schedules","## Options and draft rights","## Cap reconciliation"):
            self.assertIn(heading,cap)
        self.assertIn("2003-04",cap)
        self.assertIn("2010-11",cap)
        self.assertFalse((TEAM/"Finances/cap_tracker.md").exists())

    def test_stats_awards_hierarchy(self):
        root=PLAYER/"Stats_and_Awards"/"2003-04"
        self.assertTrue((root/"README.md").is_file())
        mapping={
            "10_October":[3,4],
            "11_November":[1,2,3,4],
            "12_December":[1,2,3,4],
            "01_January":[1,2,3,4],
            "02_February":[1,2,3,4],
            "03_March":[1,2,3,4],
            "04_April":[1,2],
        }
        for month,weeks in mapping.items():
            self.assertTrue((root/month/"README.md").is_file())
            for week in weeks:
                self.assertTrue((root/month/f"Week_{week}"/"README.md").is_file())

    def test_league_stats_and_awards_hierarchy(self):
        root=PLAYER/"Stats_and_Awards"/"League"
        registry=json.loads((root/"player_registry.json").read_text(encoding="utf-8"))
        self.assertEqual(registry["player_count"],407)
        self.assertEqual(set(registry["positions"]),{"PG","SG","SF","F","PF","C"})
        year=root/"2003-04"
        self.assertTrue((year/"League_Stats.md").is_file())
        self.assertTrue((year/"League_Awards.md").is_file())
        mapping={
            "10_October":[3,4],
            "11_November":[1,2,3,4],
            "12_December":[1,2,3,4],
            "01_January":[1,2,3,4],
            "02_February":[1,2,3,4],
            "03_March":[1,2,3,4],
            "04_April":[1,2],
        }
        for month,weeks in mapping.items():
            self.assertTrue((year/month/"League_Stats.md").is_file())
            self.assertTrue((year/month/"League_Awards.md").is_file())
            for week in weeks:
                self.assertTrue((year/month/f"Week_{week}"/"League_Stats.md").is_file())
                self.assertTrue((year/month/f"Week_{week}"/"League_Awards.md").is_file())

    def test_team_stats_hierarchy(self):
        root=PLAYER/"Stats_and_Awards"/"Team"/"2003-04"
        self.assertTrue((root/"Team_Stats.md").is_file())
        mapping={
            "10_October":[3,4],
            "11_November":[1,2,3,4],
            "12_December":[1,2,3,4],
            "01_January":[1,2,3,4],
            "02_February":[1,2,3,4],
            "03_March":[1,2,3,4],
            "04_April":[1,2],
        }
        for month,weeks in mapping.items():
            self.assertTrue((root/month/"Team_Stats.md").is_file())
            for week in weeks:
                self.assertTrue((root/month/f"Week_{week}"/"Team_Stats.md").is_file())

    def test_team_stats_only_list_current_team_pool(self):
        text=(PLAYER/"Stats_and_Awards"/"Team"/"2003-04"/"Team_Stats.md").read_text(encoding="utf-8")
        roster=json.loads((TEAM/"Team/Roster/roster.json").read_text(encoding="utf-8"))
        for player in roster["players"]:
            self.assertIn(f"| {player['name']} |",text)
        self.assertNotIn("| LeBron James |",text)

    def test_eight_year_cap_reference(self):
        history=json.loads((TEAM/"Finances/league_cap_history.json").read_text(encoding="utf-8"))
        caps={row["season"]:row["salary_cap"] for row in history["seasons"]}
        self.assertEqual(caps,{
            "2003-04":43840000,
            "2004-05":43870000,
            "2005-06":49500000,
            "2006-07":53135000,
            "2007-08":55630000,
            "2008-09":58680000,
            "2009-10":57700000,
            "2010-11":58044000,
        })

    def test_draft_day_finance_baseline(self):
        finance=json.loads((TEAM/"Finances/finance.json").read_text(encoding="utf-8"))
        self.assertIsNone(finance["live_official_salary_cap"])
        self.assertEqual(finance["historical_actual_salary_cap"],43840000)
        self.assertEqual(finance["known_counted_salary_before_free_agent_holds"],28466078)
        schedules=json.loads((TEAM/"Finances/contract_schedules.json").read_text(encoding="utf-8"))
        wade=next(x for x in schedules["players"] if x["player"]=="Dwyane Wade")
        self.assertEqual(wade["current_cap_hold"],2197000)

    def test_league_sources_are_in_library(self):
        league=ROOT/"library/2003/league"
        draft=json.loads((league/"nba_2003_draft_class.json").read_text(encoding="utf-8"))
        end=json.loads((league/"nba_2003_end_of_season.json").read_text(encoding="utf-8"))
        self.assertEqual(draft["league"],"NBA")
        self.assertEqual(end["league"],"NBA")
        self.assertEqual(draft["season"],2003)
        self.assertEqual(end["season"],2003)
        self.assertFalse((SEASON/"nba_2003_draft_class.json").exists())
        self.assertFalse((SEASON/"nba_2003_end_of_season.json").exists())

    def test_no_empty_postseason_placeholders(self):
        self.assertFalse(any((SEASON/"07_Play_In_Tournament").glob("Game_*.md")))
        for folder in ("First_Round","Conference_Semifinals","Conference_Finals","Finals"):
            self.assertFalse(any((SEASON/"08_Playoffs"/folder).glob("Game_*.md")))


class FinanceProjectionTests(unittest.TestCase):
    def setUp(self):
        folder=TEAM/"Finances"
        self.finance=json.loads((folder/"finance.json").read_text(encoding="utf-8"))
        self.schedules=json.loads((folder/"contract_schedules.json").read_text(encoding="utf-8"))
        self.history=json.loads((folder/"league_cap_history.json").read_text(encoding="utf-8"))

    def errors(self):
        return finance_errors(self.finance,self.schedules,self.history)

    def test_existing_commitments_reconcile(self):
        self.assertEqual(self.errors(),[])

    def test_draft_hold_cannot_be_counted_twice_as_salary(self):
        self.schedules["projection"][0]["scheduled_contract_salary"]+=2197000
        self.assertTrue(any("scheduled_contract_salary" in e for e in self.errors()))

    def test_option_year_cannot_become_unconditional_silently(self):
        grant=next(p for p in self.schedules["players"] if p["player"]=="Brian Grant")
        grant["amount_kind"]["2006-07"]="contract_salary"
        self.assertTrue(any("2006-07" in e and "reconcile" in e for e in self.errors()))

    def test_no_commitments_does_not_mean_zero_payroll_or_known_cap_space(self):
        original=deepcopy(self.schedules)
        for key in ("total_team_salary","cap_space","free_agent_holds","other_cap_charges"):
            with self.subTest(field=key):
                self.schedules=deepcopy(original)
                self.schedules["projection"][-1][key]=0
                self.assertTrue(any(f"unresolved {key}" in e for e in self.errors()))

    def test_archive_without_publication_date_is_not_live(self):
        self.history["seasons"][1]["live_at_checkpoint"]=True
        self.assertTrue(any("publication/activation gate" in e for e in self.errors()))

    def test_partial_inventory_cannot_report_cap_room(self):
        self.finance["cap_room"]=15373922
        self.assertTrue(any("cap_room must remain unresolved" in e for e in self.errors()))

    def test_unpriced_option_must_remain_visible(self):
        self.schedules["projection"][0]["unpriced_option_count"]=0
        self.assertTrue(any("unpriced_option_count" in e for e in self.errors()))


if __name__=="__main__":
    unittest.main()
