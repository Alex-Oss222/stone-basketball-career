"""The June 2006 audit, group C (league): dated Club / rights cells, page counts and captions, card period rows, the
registry names keyed by an NBA id, club codes, the closed seasons' card lines, the bracket's seeding rule and the
league hub."""
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from runtime import free_agency_2004, league_cards, offseason, playoffs, season_awards, write_back
from runtime.league_cards import (CardContext, NOT_IN_LEAGUE, appearance_clubs, card_data, club_code, dated_label,
                                  period_label, period_rows, repair_card_lines, roster_cache)
from runtime.season_pages import hub
from scripts.format_league_reports import format_page

ROOT = Path(__file__).resolve().parents[1]
LEAGUE = Path("career/Dwyane_Wade/Stats_and_Awards/League")
EMPTY = dict(holdings={"entries": []}, departures={"entries": []}, transactions={})
VET = {"name": "Example Veteran", "bbr_id": "examve01", "registry_id": "examve01", "team_name": "Boston Celtics",
       "team_code": "BOS", "cohort": "end_2002_03_roster", "position": "PG", "birth_date": "1984-01-17"}


def played(day, club):
    return {"date": day, "team": club, "event_id": f"{day}-{club}", "line": {"appeared": True}}


class DatedClubTests(unittest.TestCase):
    def test_appearances_name_the_clubs_in_stint_order(self):
        records = [played("2003-11-02", "Chicago Bulls"), played("2003-12-05", "Toronto Raptors"),
                   played("2003-11-04", "Chicago Bulls"), {"date": "2003-11-06", "team": "Miami Heat", "line": {"appeared": False}}]
        self.assertEqual(appearance_clubs(records), ["Chicago Bulls", "Toronto Raptors"])          # a DNP is no appearance
        self.assertEqual(period_label(VET, records, "2003-10-01", "2004-04-30", "2004-04-30", root=ROOT, **EMPTY), ("CHI/TOR", "NBA"))
        self.assertEqual(period_label(VET, records, "2003-12-01", "2003-12-31", "2003-12-31", root=ROOT, **EMPTY), ("TOR", "NBA"))

    def test_without_an_appearance_the_club_on_the_label_date(self):
        # 2003-04: a registry source club no real roster carries is no club (the engine's world on the date), never a
        # later season's first club; with no club and no record or holding yet, no league either.
        self.assertEqual(period_label(VET, (), "2003-11-01", "2003-11-07", "2003-11-07", root=ROOT, **EMPTY), ("FA", "NBA"))
        later = dict(VET, added_on="2004-11-03", cohort="2003_04_appearance")
        self.assertEqual(period_label(later, (), "2003-11-01", "2003-11-07", "2003-11-07", root=ROOT, **EMPTY),
                         (NOT_IN_LEAGUE, NOT_IN_LEAGUE))

    def test_renounced_rights_end_the_rights_label(self):
        beasley = {"name": "Jerome Beasley", "bbr_id": "beaslje01", "registry_id": "beaslje01", "team_name": "Miami Heat",
                   "team_code": "MIA", "cohort": "2003_draft_rights", "position": "PF", "birth_date": "1980-05-17"}
        holdings = {"entries": [{"player": "Jerome Beasley", "bbr_id": None, "from": "2003-06-26", "until": "2003-11-11",
                                 "basis": "draft rights"}]}
        sources = dict(EMPTY, holdings=holdings)
        self.assertEqual(period_label(beasley, (), "2003-10-01", "2003-10-31", "2003-10-31", root=ROOT, **sources), ("MIA rights", "NBA"))
        self.assertEqual(period_label(beasley, (), "2003-11-01", "2003-11-30", "2003-11-30", root=ROOT, **sources), ("FA", "NBA"))

    def test_club_codes_cover_later_clubs_and_are_never_none(self):
        self.assertEqual(club_code("Charlotte Bobcats"), "CHA")
        self.assertEqual(club_code("New Orleans/Oklahoma City Hornets"), "NOK")
        self.assertEqual((club_code("Golden State Warriors"), club_code("New Orleans Hornets"), club_code(None)), ("GS", "NO", None))


class HeldClubTests(unittest.TestCase):
    """A club that holds a player comes before the "not reached" dash (the review of the group C branch): the registry
    `added_on` is a first appearance, not a first holding."""

    @classmethod
    def setUpClass(cls):
        cls.players = {p["name"]: p for p in write_back.registry(ROOT)["players"]}

    def label(self, name, on):
        with roster_cache():
            return dated_label(self.players[name], on, (), root=ROOT, signed=league_cards.signings(ROOT))

    def test_a_club_holding_him_before_his_first_appearance_is_shown(self):
        self.assertEqual(self.label("Udonis Haslem", "2003-10-31"), ("MIA", "NBA"))       # Miami's refill of 2003-10-27
        self.assertEqual(self.label("Eddie Jones", "2003-10-26"), ("MIA", "NBA"))
        self.assertEqual(self.label("Maurice Evans", "2004-11-30"), ("MIA", "NBA"))
        self.assertEqual(self.label("Bernard Robinson", "2005-04-30"), ("MIA rights", "NBA"))
        self.assertEqual(self.label("Bernard Robinson", "2004-06-30"), ("MIA rights", "NBA"))   # the June pick, before the rollover
        self.assertEqual(self.label("Bernard Robinson", "2006-01-31"), ("MIL", "NBA"))

    def test_a_player_held_before_and_unsigned_now_is_a_free_agent(self):
        self.assertEqual(self.label("Bernard Robinson", "2005-11-30"), ("FA", "NBA"))     # waived by Seattle on 2005-11-02
        self.assertEqual(self.label("Royal Ivey", "2005-01-31"), ("FA", "NBA"))           # placed in the 2004-05 opening book

    def test_the_league_had_not_reached_him(self):
        self.assertEqual(self.label("Chris Paul", "2003-10-31"), (NOT_IN_LEAGUE, NOT_IN_LEAGUE))
        self.assertEqual(self.label("Dwight Howard", "2004-06-30"), (NOT_IN_LEAGUE, NOT_IN_LEAGUE))

    def test_a_2003_04_page_shows_the_engines_world_not_the_2002_03_club(self):
        self.assertEqual(self.label("John Stockton", "2004-06-30"), ("FA", "NBA"))        # retired: club_truth.holder
        self.assertEqual(self.label("John Stockton", "2003-10-31"), ("FA", "NBA"))        # no real 2003-04 stint
        self.assertEqual(self.label("Jelani McCoy", "2003-11-07"), ("CLE", "NBA"))        # his real stint, not Toronto
        self.assertEqual(league_cards.club_on(self.players["John Stockton"], "2004-06-30")["club"], "Utah Jazz")  # unchanged


class LeaguePageTests(unittest.TestCase):
    PAGE = ROOT / LEAGUE / "2003-04/11_November/Week_1/League_Stats.md"

    def page(self):
        row = "| [{}](../../../Players/{}.md) | 30 | {} | NBA | PG |" + " N/A |" * 26 + "\n"
        header = "| " + " | ".join(write_back.LEAGUE_COLUMNS) + " |\n| " + " | ".join("---" for _ in write_back.LEAGUE_COLUMNS) + " |\n"
        return ("# NBA players | November 2003 | Week 1\n\n407 tracked players · 0 closed games in this record · Not started.\n\n"
                "## Leaders\n\nx\n\n## Players by position\n\n"
                "Open a position to see every tracked player. Age is recorded at the period's identity cutoff (2003-06-26); Club / rights is the recorded source label.\n\n"
                "<details>\n<summary>PG · Point guards · 83 players</summary>\n\n### PG: per game\n\n" + header
                + row.format("zzid01", "zzid01", "TOR") + row.format("Example Veteran", "examve01", "UTAH")
                + row.format("Later Rookie", "laterro01", "ORL") + "\n</details>\n\n## Coverage\n\nx\n")

    def test_rows_counts_caption_and_names_follow_the_registry(self):
        players = {"examve01": VET, "zzid01": dict(VET, name="Zed Named", bbr_id="zzid01", registry_id="zzid01"),
                   "laterro01": dict(VET, name="Later Rookie", bbr_id="laterro01", registry_id="laterro01",
                                     added_on="2005-11-01", cohort="2003_04_appearance")}
        text = write_back.league_page(self.page(), self.PAGE, {}, "2006-06-20", [], {}, players, ROOT, EMPTY, live=False)
        self.assertIn("3 tracked players · 0 closed games in this record · Complete; no NBA game in this period.", text)
        self.assertIn("<summary>PG · Point guards · 3 players</summary>", text)
        self.assertIn("Age is each player's age on 2003-11-07", text)
        self.assertNotIn("2003-06-26", text)
        rows = [line for line in text.splitlines() if line.startswith("| [")]
        self.assertEqual([r.split("]")[0][3:] for r in rows], ["Example Veteran", "Later Rookie", "Zed Named"])   # renamed, sorted
        self.assertIn("| [Example Veteran](../../../Players/examve01.md) | 19 | FA | NBA | PG |", rows[0])
        self.assertIn(f"| {NOT_IN_LEAGUE} | {NOT_IN_LEAGUE} | PG |", rows[1])
        self.assertEqual(text, write_back.league_page(text, self.PAGE, {}, "2006-06-20", [], {}, players, ROOT, EMPTY, live=False))

    def test_the_formatter_states_the_page_date_and_recounts(self):
        registry = {"positions": ["PG"], "players": [dict(VET, registry_id="examve01")]}
        text = ("# x\n\n## Players by position\n\nOpen a position to see every tracked player. Age is recorded at the period's "
                "identity cutoff (2003-06-26).\n\n<details>\n<summary>PG · Point guards · 9 players</summary>\n\n"
                "| Player | Club / rights | G | PTS |\n| --- | --- | --- | --- |\n| [Old Name](../../../Players/examve01.md) | BOS | 0 | N/A |\n\n</details>\n")
        out = format_page(text, self.PAGE, registry, "2006-06-20", ROOT / LEAGUE / "assets/per_game.svg", ROOT / LEAGUE)
        self.assertIn("Age is each player's age on 2003-11-07", out)
        self.assertIn("<summary>PG · Point guards · 1 players</summary>", out)
        self.assertIn("[Example Veteran](../../../Players/examve01.md)", out)


class NameOrderTests(unittest.TestCase):
    def test_accents_and_case_do_not_move_a_name_out_of_order(self):
        names = ["Will Bynum", "Šarūnas Jasikevičius", "Andrés Nocioni", "Andre Barrett", "DeShawn Stevenson"]
        self.assertEqual(sorted(names, key=write_back.name_order),
                         ["Andre Barrett", "Andrés Nocioni", "DeShawn Stevenson", "Šarūnas Jasikevičius", "Will Bynum"])


class RegistryNameTests(unittest.TestCase):
    def test_no_registry_row_is_named_by_its_id_and_its_results_still_match(self):
        players = write_back.registry(ROOT)["players"]
        self.assertEqual([p["registry_id"] for p in players if p["name"] == p.get("bbr_id")], [])
        names = {p["bbr_id"]: p["name"] for p in players if p.get("bbr_id")}
        self.assertEqual((names["simiewa01"], names["walshma01"], names["fitchge01"]), ("Wayne Simien", "Matt Walsh", "Gerald Fitch"))
        lines, unmatched = write_back.closed_lines(ROOT, "2005-06", "2006-06-20")
        self.assertEqual(unmatched, [])
        self.assertEqual((len(lines["simiewa01"]), len(lines["walshma01"]), len(lines["fitchge01"])), (82, 21, 2))

    def test_an_id_keyed_result_still_reaches_his_award_identity(self):
        ids = season_awards.identities(ROOT, "2005-06")
        self.assertEqual(ids["simiewa01"], ("simiewa01", "simiewa01", "F"))      # the answer before the rename
        self.assertEqual(ids["Wayne Simien"][1:], ("simiewa01", "F"))
        # Only a renamed row keeps its id: Malik Allen's id-keyed 2004-05 games stay unmatched, as the 2005 market read them.
        self.assertNotIn("allenma01", season_awards.identities(ROOT, "2004-05"))

    def test_the_market_names_an_unregistered_id_from_the_2006_summer(self):
        names = {"zzsynth01": "Synthetic Player"}
        with mock.patch("runtime.write_back.id_names", return_value=names):
            market = SimpleNamespace(ident={"knownpl01": {"name": "Known Player"}}, root=ROOT)
            with mock.patch.object(free_agency_2004, "YEAR", 2005):
                self.assertEqual(free_agency_2004.Market.name(market, "zzsynth01"), "zzsynth01")   # 2005 replays as written
            with mock.patch.object(free_agency_2004, "YEAR", 2006):
                self.assertEqual(free_agency_2004.Market.name(market, "zzsynth01"), "Synthetic Player")
                self.assertEqual(free_agency_2004.Market.name(market, "knownpl01"), "Known Player")
                self.assertEqual(free_agency_2004.Market.name(market, "zznone01"), "zznone01")

    def test_the_market_identity_names_an_id_keyed_roster_player_from_2006(self):
        from runtime import rotations
        real = rotations.load_rosters

        def rosters(season, root=ROOT):
            out = dict(real(season, root))
            out["Synthetic Club"] = {"players": [{"player_id": "zzsynth01", "bbr_id": "zzsynth01", "position": "SF"}]}
            return out
        with mock.patch.object(rotations, "load_rosters", rosters), \
                mock.patch("runtime.write_back.id_names", return_value={"zzsynth01": "Synthetic Player"}):
            self.assertEqual(free_agency_2004.identity(ROOT, year=2005)["zzsynth01"]["name"], "zzsynth01")
            self.assertEqual(free_agency_2004.identity(ROOT, year=2006)["zzsynth01"]["name"], "Synthetic Player")

    def test_an_addition_keyed_by_its_id_takes_the_careers_name(self):
        row = {"result": {"home": "Toronto Raptors", "away": "Boston Celtics", "game_date": "2006-11-01", "event_id": "e1"}}
        with mock.patch.object(write_back, "registry", return_value={"players": []}), \
                mock.patch.object(write_back, "closed_results", return_value=[row]), \
                mock.patch.object(write_back, "game_records", return_value=[("home", "simiewa01", "simiewa01", {})]), \
                mock.patch.object(write_back, "position_sources", return_value=[]):
            added = write_back.registry_additions(ROOT, "2005-06", "2006-11-01")
        self.assertEqual([(p["name"], p["bbr_id"], p["team_code"]) for p in added], [("Wayne Simien", "simiewa01", "TOR")])

    def test_a_later_book_names_an_id_keyed_player_from_2006_07_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel in ("library/careers/nba_player_careers.json", "library/careers/nba_player_births.json",
                        "library/2005/league/nba_2005_06_team_rosters.json", "library/2006/league/nba_2006_07_team_rosters.json"):
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                os.symlink(ROOT / rel, root / rel)
            for year, season in ((2005, "2005-06"), (2006, "2006-07")):
                path = root / f"career/Dwyane_Wade/{year - 1}-{str(year)[-2:]}/10_Free_Agency/free_agency_{year}.json"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps({"clubs": {"Toronto Raptors": [{"player": "simiewa01", "bbr_id": "simiewa01"}]}}))
            ids = lambda season: [p["player_id"] for p in offseason.later_book(season, root)["clubs"]["Toronto Raptors"]]
            self.assertEqual(ids("2005-06"), ["simiewa01"])                  # the played 2005-06 book stands as written
            self.assertEqual(ids("2006-07"), ["Wayne Simien"])


class CardRowTests(unittest.TestCase):
    def test_period_rows_read_like_their_linked_pages(self):
        ctx = mock.Mock(root=ROOT, on="2006-06-20", season="2005-06", signed={}, periods=[
            dict(id="season", kind="season", start="2005-11-01", end="2006-04-30", folder="2005-06"),
            dict(id="month-11", kind="month", start="2005-11-01", end="2005-11-30", folder="2005-06/11_November")])
        records = [played("2005-11-02", "Miami Heat"), played("2006-01-20", "Boston Celtics")]
        rows = period_rows(ctx, VET, records)
        self.assertEqual(rows["month-11"], (21, "MIA", "NBA"))             # born 1984-01-17: 21 on November 30, 2005
        self.assertEqual(rows["season"], (22, "MIA/BOS", "NBA"))           # the season page's date: the career date
        later = dict(VET, added_on="2006-02-01", cohort="2003_04_appearance")
        with roster_cache():
            self.assertEqual(period_rows(ctx, later, ())["month-11"], (21, NOT_IN_LEAGUE, NOT_IN_LEAGUE))   # Lg as the page

    def test_closed_seasons_card_lines_name_the_clubs_of_their_appearances(self):
        for season in ("2003-04", "2004-05"):
            self.assertEqual(repair_card_lines(ROOT, season, write=False), [], season)
        rows = json.loads((ROOT / LEAGUE / "2003-04/card_lines.json").read_text())["players"]
        self.assertEqual((rows["marshdo01"]["regular"][1], rows["hillty01"]["regular"][1]), ("CHI/TOR", "PHI"))


class CardDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tests import live_season
        with live_season():
            cls.ctx = CardContext(ROOT)
            cls.records, _ = league_cards.closed_card_feeds(cls.ctx)
        cls.players = {p["registry_id"]: p for p in cls.ctx.registry["players"]}

    def card(self, pid):
        from tests import live_season
        with live_season(), roster_cache():
            return card_data(self.ctx, self.players[pid], self.records.get(pid, ()))

    def test_jersey_is_looked_up_by_nba_id(self):
        data = self.card("sebastiantelfair")
        self.assertEqual((data["club"]["club"], str(data["jersey"])), ("Miami Heat", "31"))

    def test_a_club_without_a_registry_code_has_a_code(self):
        data = self.card("shaunlivingston")
        self.assertNotIn(None, [team for _, team, _ in data["rows"].values()])
        self.assertIsNotNone(data["club_label"])

    def test_playoff_rows_of_an_id_keyed_result_reach_the_registry_name(self):
        self.assertTrue(self.ctx.playoff_lines.get(league_cards._key("Wayne Simien")))
        self.assertFalse(self.ctx.playoff_lines.get(league_cards._key("simiewa01")))


class PlayoffAndHubTests(unittest.TestCase):
    def test_bracket_pages_state_their_seasons_seeding_rule(self):
        for season in ("2003-04", "2004-05", "2005-06"):
            record = playoffs.read(ROOT, season)
            rule = json.loads((ROOT / record["rules"]).read_text())["qualification"]["seeding"]
            text = playoffs.page(record, ROOT)
            self.assertIn(rule, text)
            self.assertEqual("seeds 3 to 8 are the next six records" in text, season == "2003-04", season)

    def test_the_hub_links_every_season_and_counts_the_registry(self):
        text = next(iter(hub(ROOT).values()))
        for season, year in (("2003-04", 2004), ("2004-05", 2005), ("2005-06", 2006)):
            for link in (f"[{season} players]({season}/League_Stats.md)", f"[{season} standings]({season}/Standings.md)",
                         f"[{year} playoffs]({season}/Playoffs.md)"):
                self.assertIn(link, text)
        count = len(write_back.registry(ROOT)["players"])
        self.assertIn(f"The league pages cover {count} registered players.", text)
        self.assertNotIn("407 registered players", text)


if __name__ == "__main__":
    unittest.main()
