"""Audit of 2006-06-20, group B (Miami's desk): personnel cards, the register, the team desk and the Team pages.

The record tests read the repository's committed records (read-only) for the career's real live season; the unit tests
use small inputs. Each fails on the code and records before the audit's fixes.
"""
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest import mock

from tests import live_season

ROOT = Path(__file__).resolve().parents[1]
CAREER = ROOT / "career/Dwyane_Wade"


def register(season):
    return {p["name"]: p for p in json.loads((CAREER / season / "00_Team/Team/Roster/roster.json").read_text(encoding="utf-8"))["players"]}


def card(season, name):
    return (CAREER / season / "00_Team/Team/Player_Cards" / f"{name}.md").read_text(encoding="utf-8")


class DatedRegisterFacts(unittest.TestCase):
    """Played games froze Telfair at SF and eight Miami players without a birth date: corrections count from 2006-06-21."""

    def test_position_correction_counts_from_its_date(self):
        from runtime.miami_register import carried, positions_on, with_positions_on
        row = register("2005-06")["Sebastian Telfair"]
        self.assertEqual(row["positions"], ["SF"])                      # what every played game read
        self.assertEqual(positions_on(row, "2006-06-20"), ["SF"])
        self.assertEqual(positions_on(row, "2006-06-21"), ["PG"])
        self.assertEqual(with_positions_on([row], "2006-04-12")[0]["positions"], ["SF"])
        nxt = carried(row, "2006-10-01")                                  # the 2006 rollover's register row
        self.assertEqual(nxt["positions"], ["PG"])
        self.assertNotIn("positions_corrected_from", nxt)

    def test_a_missing_position_is_guessed_only_through_the_clock(self):
        from runtime.miami_register import required_position
        self.assertEqual(required_position("PG", "2006-07-01", "X"), "PG")
        self.assertEqual(required_position(None, "2006-06-20", "X"), "SF")      # recorded decisions replay as made
        with self.assertRaises(ValueError):
            required_position(None, "2006-06-21", "X")

    def test_need_score_reads_the_correction_from_its_date(self):
        from runtime import gm
        market = SimpleNamespace(valuation=SimpleNamespace(value=lambda b: None))
        with mock.patch.object(gm, "TEAM", Path("career/Dwyane_Wade/2005-06/00_Team")), mock.patch.object(gm, "SEASON", "2005-06"):
            before = gm.FrontOffice("2006-06-20", market, ROOT).roster_values()["Sebastian Telfair"]["position"]
            after = gm.FrontOffice("2006-06-21", market, ROOT).roster_values()["Sebastian Telfair"]["position"]
        self.assertEqual((before, after), ("SF", "PG"))

    def test_birth_dates_back_filled_without_changing_played_games(self):
        from runtime.injuries import simulated_ages
        rows = register("2004-05")
        born = {n: rows[n].get("date_of_birth") for n in ("Dorell Wright", "John Thomas", "Maurice Evans", "Maurice Baker",
                                                          "John Edwards", "Bernard Robinson", "Christian Drejer")}
        self.assertEqual(born["Dorell Wright"], "1985-12-02")
        self.assertEqual(born["Christian Drejer"], "1982-12-08")
        self.assertTrue(all(born.values()), born)
        self.assertTrue(all(rows[n]["date_of_birth_from"] == "2006-06-21" for n in born))
        self.assertEqual(register("2005-06")["Uroš Slokar"]["date_of_birth"], "1983-05-14")
        self.assertNotIn("dorell_wright", simulated_ages("2004-05", "2004-11-03", ROOT))   # the frozen null age stands
        self.assertEqual(simulated_ages("2004-05", "2006-07-01", ROOT).get("dorell_wright"), 20)

    def test_identity_lookups_read_prospect_evidence_and_researched_births(self):
        from runtime import signing
        self.assertEqual(signing.league_identity(ROOT, "drejech01")["birth_date"], "1982-12-08")
        self.assertEqual(signing.league_identity(ROOT, "slokaur01")["birth_date"], "1983-05-14")
        self.assertEqual(signing.prospect_identities(ROOT)["slokaur01"]["position"], "F")


class TeamDesk(unittest.TestCase):
    def test_unsigned_rights_are_not_a_contract_and_have_no_role(self):
        from runtime import team_status
        reg = {p["name"]: (a, role) for p, a, role in team_status.register(ROOT, "2006-06-20", "2005-06")}
        self.assertEqual(reg["Uroš Slokar"], ("Unsigned draft rights; not on the roster", "N/A"))
        with live_season():
            blocks = team_status.blocks(ROOT, "2006-06-20")
        team = next(v for k, v in blocks.items() if str(k).endswith("00_Team/Team/README.md"))
        self.assertIn("15 under contract (12 active, 3 on the injured list)", team)

    def test_contracts_ending_june_30_are_labelled_after_the_regular_season(self):
        from runtime import team_status
        ending = team_status.expiring(ROOT, "2006-06-20", "2005-06")
        self.assertEqual(set(ending), {"Mike James", "Caron Butler", "Eddie Gill", "Mike Wilks", "Matt Carroll"})
        self.assertIn("qualifying-offer decision", ending["Caron Butler"])
        self.assertEqual(team_status.expiring(ROOT, "2006-03-01", "2005-06"), {})       # in season: no label

    def test_register_term_clauses_follow_the_contract_sheet(self):
        from runtime.miami_cards import control_texts
        from runtime.rollover import contract_head
        rows = register("2004-05")
        self.assertIn("3 season(s) from 2004-05, $43,008,660 scheduled", rows["Brian Grant"]["control"])
        self.assertIn("2 season(s) from 2004-05, $4,392,297 scheduled", rows["Caron Butler"]["control"])
        self.assertEqual(control_texts(ROOT, "2004-05")[1], [])
        self.assertEqual(contract_head({"2004-05": 1930680, "2005-06": 2461617}, "2004-05"),
                         "2 season(s) from 2004-05, $4,392,297 scheduled ($1,930,680 in 2004-05)")
        self.assertIn("3 season(s) from 2004-05, $43,008,660", card("2004-05", "brian_grant"))

    def test_payroll_ceiling_recorded_without_changing_a_decision(self):
        from runtime import gm
        from runtime.rollover import season_budget
        cfg = json.loads((CAREER / "2005-06/00_Team/team_config.json").read_text(encoding="utf-8"))["budget"]
        self.assertEqual((cfg["payroll_ceiling"], cfg["payroll_ceiling_through_2004_05"]), (61700000, 57000000))
        market = SimpleNamespace(valuation=SimpleNamespace(value=lambda b: None))
        with mock.patch.object(gm, "TEAM", Path("career/Dwyane_Wade/2005-06/00_Team")), mock.patch.object(gm, "SEASON", "2005-06"):
            self.assertEqual(gm.FrontOffice("2005-03-01", market, ROOT).payroll_ceiling(), 57000000)   # a 2004-05 date
            self.assertEqual(gm.FrontOffice("2006-01-07", market, ROOT).payroll_ceiling(), 61700000)
        nxt = season_budget(cfg, "2005-06", "2006-07", ROOT)
        self.assertEqual(nxt["payroll_ceiling_through_2004_05"], 57000000)
        self.assertGreater(nxt["payroll_ceiling"], 61700000)


class PersonnelCards(unittest.TestCase):
    def test_wade_card_has_his_playoffs_and_honors(self):
        text = card("2005-06", "dwyane_wade")
        self.assertIn("| 2003-04 | Miami Heat | 2 | 2 | 26.0 | 10.5 |", text)
        self.assertIn("| 2004-05 | Miami Heat | 12 | 12 | 36.8 |", text)
        self.assertIn("| 2005-06 | Miami Heat | 17 | 17 | 35.2 |", text)
        self.assertIn("36 honor(s) earned", text)
        self.assertIn("Most Valuable Player", text)
        self.assertNotIn("has not started", text)

    def test_arrivals_get_every_season_and_one_percentage_format(self):
        okur = card("2005-06", "mehmet_okur")
        self.assertIn("| 2004-05 | Miami Heat | 12 | 0 | 19.1 |", okur)
        self.assertIn("| 2005-06 | Miami Heat | 17 | 17 | 33.6 |", okur)
        self.assertIn("| 2003-04 | Detroit Pistons | 70 | 40 | 24.4 | 9.7 | 5.5 | 1.2 | 0.5 | 0.8 | 1.3 | 45.3% | 46.7% | 75.7% |", okur)
        self.assertNotIn("not started", okur.split("## Regular-season statistics by year")[1])
        brown = card("2005-06", "pj_brown")
        self.assertIn("| 2003-04 |", brown)
        self.assertIn("| 2004-05 |", brown)
        self.assertIn("2 honor(s) earned", card("2005-06", "mike_james"))

    def test_rights_holder_card_and_ages(self):
        slokar = card("2005-06", "uros_slokar")
        self.assertIn("**Role:** Not on the roster (unsigned draft rights)", slokar)
        self.assertIn("**Age at assessment:** 22", slokar)
        self.assertIn("**Age at assessment:** 18", card("2004-05", "dorell_wright"))

    def test_percent_cells_only_in_the_shooting_columns(self):
        from runtime.miami_cards import percent_cell
        self.assertEqual(percent_cell("0.461"), "46.1%")
        self.assertEqual(percent_cell(".381"), "38.1%")
        self.assertEqual(percent_cell("N/A"), "N/A")
        self.assertEqual(percent_cell("45.2%"), "45.2%")

    def test_cards_are_current_and_each_season_has_a_card_index(self):
        from runtime import miami_cards
        with live_season():
            self.assertEqual(miami_cards.refresh(ROOT, write=False), [])
        for season in ("2004-05", "2005-06"):
            self.assertTrue((CAREER / season / "00_Team/Team/Player_Cards/README.md").is_file())

    def test_arrival_template_uses_one_format_and_no_stale_coverage(self):
        from runtime.rollover import arrival_card
        prior = {"team_codes": ["Utah Jazz"], "totals": {"games": 10, "games_started": 0, "minutes": 100, "points": 50,
                 "offensive_rebounds": 5, "defensive_rebounds": 10, "assists": 5, "steals": 1, "blocks": 1, "turnovers": 3,
                 "field_goals_made": 9, "field_goals_attempted": 20, "three_point_field_goals_made": 1,
                 "three_point_field_goals_attempted": 4, "free_throws_made": 3, "free_throws_attempted": 4}}
        text = arrival_card("Test Player", {"position": "PG"}, "2006-10-01", "Existing contract.", "x", prior, "2006-07", "Joined")
        self.assertIn("| 45.0% | 25.0% | 75.0% |", text)
        self.assertNotIn("not started.", text)
        self.assertNotIn("No playoff appearances recorded", text)


class TeamPages(unittest.TestCase):
    def test_closed_pages_list_only_players_held_and_an_empty_week_is_complete(self):
        from runtime import write_back
        with live_season():
            pages = write_back.closed_team_pages(ROOT)
        week = next(t for p, t in pages.items() if p.as_posix().endswith("Team/2003-04/10_October/Week_3/Team_Stats.md"))
        self.assertIn("complete; no Miami game in this period", week)
        for name in ("Malik Allen", "Cherokee Parks", "Udonis Haslem", "John Wallace"):     # production rows; the dated
            self.assertNotRegex(week, rf"\| {name} \| [A-Z/]+ \| \d")                    # June 26 table stays as labelled
        month = next(t for p, t in pages.items() if p.as_posix().endswith("Team/2003-04/10_October/Team_Stats.md"))
        self.assertIn("| October 15-21, 2003 | 0 | No games |", month)
        season = next(t for p, t in pages.items() if p.as_posix().endswith("Team/2004-05/Team_Stats.md"))
        self.assertNotRegex(season, r"\| (Bernard Robinson|Christian Drejer) \| [A-Z/]+ \| \d")

    def test_live_pages_drop_unsigned_rights(self):
        text = (CAREER / "Stats_and_Awards/Team/2005-06/Team_Stats.md").read_text(encoding="utf-8")
        self.assertNotIn("| Uroš Slokar |", text)

    def test_contract_holdings_exclude_rights_and_voids(self):
        from runtime.write_back import contract_holdings, register_names
        players = [{"name": "A", "status": "under_contract"}, {"name": "B", "status": "unsigned_draft_rights"},
                   {"name": "C", "status": "renounced"}, {"name": "D", "status": "under_contract"}]
        held = contract_holdings(players, [
            {"player": "A", "from": "2003-06-26", "until": None, "basis": "draft rights"},
            {"player": "B", "from": "2005-06-28", "until": None, "basis": "draft rights (No. 58 pick), unsigned"},
            {"player": "C", "from": "2003-06-26", "until": "2003-11-11", "basis": "draft rights"},
            {"player": "D", "from": "2003-09-30", "until": "2003-10-27", "basis": "camp contract", "void": True}])
        self.assertEqual(list(held), ["A"])
        self.assertEqual(register_names(players), ["A", "D"])

    def test_season_pages_state_the_playoff_record_and_the_hub_lists_every_season(self):
        from runtime import playoff_stats, team_status
        section = playoff_stats.team_season_section(ROOT, "2005-06", "2006-06-20")
        self.assertIn("17 closed Miami playoff game(s), 11-6", section)
        self.assertIn("(Playoffs/Team_Playoff_Stats.md)", section)
        text = (CAREER / "Stats_and_Awards/Team/2003-04/Team_Stats.md").read_text(encoding="utf-8")
        self.assertIn("5 closed Miami playoff game(s), 1-4", text)
        self.assertNotIn("No playoff games recorded", text)
        hub = team_status.team_stats_readme(ROOT)
        for season in ("2003-04", "2004-05", "2005-06"):
            self.assertIn(f"[{season}]({season}/Team_Stats.md)", hub)
        self.assertNotIn("June 26 checkpoint", hub)


if __name__ == "__main__":
    unittest.main()
