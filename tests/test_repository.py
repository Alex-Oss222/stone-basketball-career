import json
import shutil
import tempfile
import unittest

from tests import checkpoint
from copy import deepcopy
from pathlib import Path

from runtime import signing
from runtime.season_rules import month_week, next_series_game_number, series_over
from scripts.validate_repository import finance_errors, rights_errors

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
        depth=checkpoint.read("career/Dwyane_Wade/2003-04/00_Team/Team/Depth_Chart/depth_chart.json")
        self.assertFalse(depth["game_ready"])
        names={p["name"] for p in depth["unassigned_draft_rights"]}
        self.assertEqual(names,{"Dwyane Wade","Jerome Beasley"})

    def test_cap_room_stays_unresolved_on_draft_day(self):
        finance=checkpoint.read("career/Dwyane_Wade/2003-04/00_Team/Finances/finance.json")
        self.assertIsNone(finance["cap_room"])
        carter=next(x for x in finance["pending_control_items"] if x["player"]=="Anthony Carter")
        self.assertEqual(carter["status"],"pending")
        self.assertEqual(carter["deadline"],"2003-06-30")

    def test_cap_sheet_structure(self):
        cap=(TEAM/"Finances/cap_sheet.md").read_text(encoding="utf-8")
        for heading in ("## Current cap position","## Eight-season commitments","## Payroll notes","## Cap reconciliation"):
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
        self.assertEqual(sum(p["cohort"] in ("end_2002_03_roster","2003_draft_rights") for p in registry["players"]),407)
        self.assertEqual(registry["player_count"],len(registry["players"]))
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
        from runtime.write_back import register_names
        for name in register_names(roster["players"]):      # Miami's players on the date; departed and released leave
            self.assertIn(f"| {name} |",text)
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
        finance=checkpoint.read("career/Dwyane_Wade/2003-04/00_Team/Finances/finance.json")
        self.assertIsNone(finance["live_official_salary_cap"])
        self.assertEqual(finance["historical_actual_salary_cap"],43840000)
        self.assertEqual(finance["known_counted_salary_before_free_agent_holds"],32066078)
        self.assertEqual(finance["subtotal_precision"],"includes_rounded_report")
        schedules=checkpoint.read("career/Dwyane_Wade/2003-04/00_Team/Finances/contract_schedules.json")
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
        # A playoff game note exists only once its game is built: never a blank placeholder (AGENTS.md, Game records).
        for folder in ("First_Round","Conference_Semifinals","Conference_Finals","Finals"):
            for note in (SEASON/"08_Playoffs"/folder).glob("Game_*.md"):
                self.assertTrue(note.with_name(note.stem+".request.json").is_file(),note)
                self.assertRegex(note.read_text(encoding="utf-8"),r"(?m)^status: (scheduled|played|not_played)$")


class FinanceProjectionTests(unittest.TestCase):
    """The draft-day projection rules, checked on the frozen June 26 files (tests/checkpoint.py)."""
    def setUp(self):
        folder="career/Dwyane_Wade/2003-04/00_Team/Finances"
        self.finance=checkpoint.read(f"{folder}/finance.json")
        self.schedules=checkpoint.read(f"{folder}/contract_schedules.json")
        self.history=json.loads((TEAM/"Finances/league_cap_history.json").read_text(encoding="utf-8"))

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
        lampley=next(p for p in self.schedules["players"] if p["player"]=="Sean Lampley")
        lampley["schedule"]["2003-04"]=None
        self.assertTrue(any("unpriced_option_count" in e for e in self.errors()))

    def test_historical_contract_corrections(self):
        players={p["player"]:p for p in self.schedules["players"]}
        roster=checkpoint.read("career/Dwyane_Wade/2003-04/00_Team/Team/Roster/roster.json")
        control={p["name"]:p for p in roster["players"]}
        for name in ("Rasual Butler","Sean Lampley","Ken Johnson"):
            self.assertEqual(players[name]["schedule"]["2003-04"],563679)
            self.assertEqual(players[name]["amount_kind"]["2003-04"],"team_option")
            self.assertEqual(control[name]["status"],"team_option_pending")
        self.assertEqual(players["LaPhonso Ellis"]["amount_kind"]["2003-04"],"contract_salary")
        self.assertEqual(players["LaPhonso Ellis"]["amount_precision"]["2003-04"],"reported_rounded")
        self.assertEqual(control["LaPhonso Ellis"]["status"],"under_contract_guarantee_amended")
        holds={h["player"]:h["amount"] for h in self.finance["free_agent_holds"]}
        self.assertEqual(holds,{"Alonzo Mourning":None,"Malik Allen":638679,"Travis Best":1680000,
            "Eddie House":None,"Mike James":638679,"Sean Marks":688679,"Vladimir Stepania":1755000})

    def test_rounded_salary_cannot_be_presented_as_exact(self):
        self.schedules["projection"][0]["subtotal_precision"]="whole_dollars"
        self.assertTrue(any("subtotal_precision" in e for e in self.errors()))

    def test_source_conflict_cannot_silently_become_a_booked_hold(self):
        house=next(h for h in self.finance["free_agent_holds"] if h["player"]=="Eddie House")
        house["amount"]=1474870
        self.assertTrue(any("unresolved hold cannot be booked" in e for e in self.errors()))

    def test_modern_early_bird_multiplier_is_rejected(self):
        stepania=next(h for h in self.finance["free_agent_holds"] if h["player"]=="Vladimir Stepania")
        stepania["amount"]=2362500
        self.assertTrue(any("1999 CBA multiplier" in e for e in self.errors()))

    def test_contract_and_free_agent_hold_cannot_both_count(self):
        self.finance["free_agent_holds"][0]["player"]="Ken Johnson"
        self.assertTrue(any("also counted as a free-agent hold" in e for e in self.errors()))

    def test_no_early_option_result(self):
        self.finance["pending_control_items"][-1]["status"]="declined"
        self.assertTrue(any("option decision must remain pending" in e for e in self.errors()))


class RightsCheckTests(unittest.TestCase):
    """Miami's free-agent rights file against the rule builder: equality at the checkpoint, tolerance afterwards."""

    def copy(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        shutil.copytree(ROOT / "library", root / "library")
        shutil.copytree(ROOT / "career", root / "career")
        return checkpoint.pin(root)

    def test_checkpoint_copy_passes_and_drivers_state_is_tolerated(self):
        root = self.copy()
        rights_path = root / "career/Dwyane_Wade/2003-04/00_Team/Finances/free_agent_rights.json"
        state_path = root / "career/Dwyane_Wade/2003-04/current_state.json"
        state = json.loads(state_path.read_text())
        state["current_date"] = "2003-06-26"                 # the checkpoint rule is what this test exercises
        state_path.write_text(json.dumps(state, indent=1) + "\n")
        self.assertEqual(rights_errors(root), [])
        data = json.loads(rights_path.read_text())
        data["players"][0]["re_signed"] = True
        data["players"][0]["re_signed_date"] = "2003-07-16"
        rights_path.write_text(json.dumps(data, indent=1) + "\n")
        self.assertTrue(any("stale" in e for e in rights_errors(root)))          # at June 26 the file must equal the builder
        writer = signing.Writer(root)
        signing.open_market(writer, "2003-07-01")
        writer.commit()
        state = json.loads(state_path.read_text())
        state["current_date"] = "2003-07-16"
        state_path.write_text(json.dumps(state, indent=1) + "\n")
        data = json.loads(rights_path.read_text())
        data["players"][0]["re_signed"] = True
        data["players"][0]["re_signed_date"] = "2003-07-16"
        data["players"].append(dict(data["players"][1], player="Declined Option", bbr_id="declined01"))   # a row the drivers add
        rights_path.write_text(json.dumps(data, indent=1) + "\n")
        self.assertEqual(rights_errors(root), [])
        data["players"][0]["cap_hold"] += 1
        rights_path.write_text(json.dumps(data, indent=1) + "\n")
        errors = rights_errors(root)
        self.assertTrue(any("cap_hold disagrees with the rule builder" in e for e in errors), errors)
        self.assertTrue(any("disagree with the league rights file" in e for e in errors), errors)


if __name__=="__main__":
    unittest.main()
