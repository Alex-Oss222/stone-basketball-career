"""League player cards: dated club, era colours, card content, page links and the check mode."""
import json
from pathlib import Path
import re
import unittest
from xml.etree import ElementTree

from runtime.league_cards import (CARDS_DIR, FINAL_SECTIONS, CardContext, SILHOUETTE, build_cards, card_data,
                                  card_errors, check_cards, club_colors, club_on, html_card, markdown_card)
from scripts.format_league_reports import COLUMNS, format_page, player_name, read_tables
from scripts.validate_repository import markdown_tables

ROOT = Path(__file__).resolve().parents[1]
MIAMI = "Miami Heat"


class ClubOnTests(unittest.TestCase):
    vet = {"name": "Example Veteran", "bbr_id": "examve01", "registry_id": "examve01", "team_name": "Boston Celtics",
           "team_code": "BOS", "cohort": "end_2002_03_roster", "position": "SG", "birth_date": "1978-01-01"}
    rookie = {"name": "T.J. Rookie", "bbr_id": "rookitj01", "registry_id": "rookitj01", "team_name": "Chicago Bulls",
              "team_code": "CHI", "cohort": "2003_draft_rights", "position": "PG", "birth_date": "1983-03-03"}
    empty = {"entries": []}

    def on(self, player, day, **kw):
        kw.setdefault("holdings", self.empty)
        kw.setdefault("departures", self.empty)
        kw.setdefault("transactions", {})
        return club_on(player, day, root=ROOT, **kw)

    def test_registry_source_club_and_draft_rights_are_the_starting_point(self):
        self.assertEqual(self.on(self.vet, "2003-06-26")["club"], "Boston Celtics")
        held = self.on(self.rookie, "2003-06-26")
        self.assertEqual((held["club"], held["rights"]), ("Chicago Bulls", True))

    def test_real_moves_apply_on_their_dates_and_never_to_miami(self):
        tx = {"signings": [
            {"date": "2003-07-20", "kind": "signing", "player": "Example Veteran", "bbr_id": "examve01",
             "from": "Boston Celtics", "to": "Utah Jazz", "involves_miami": False},
            {"date": "2003-08-01", "kind": "signing", "player": "Example Veteran", "bbr_id": "examve01",
             "from": "Utah Jazz", "to": MIAMI, "involves_miami": True},
            {"date": "2003-07-05", "kind": "offer_sheet", "player": "Example Veteran", "bbr_id": "examve01",
             "from": "Boston Celtics", "to": "Denver Nuggets", "involves_miami": False}]}
        self.assertEqual(self.on(self.vet, "2003-07-19", transactions=tx)["club"], "Boston Celtics")
        self.assertEqual(self.on(self.vet, "2003-07-20", transactions=tx)["club"], "Utah Jazz")
        # Rule 1: the real move to Miami is skipped; he stays with the club that had him.
        self.assertEqual(self.on(self.vet, "2003-09-01", transactions=tx)["club"], "Utah Jazz")

    def test_trades_use_names_and_skip_miami_while_waivers_free_the_player(self):
        tx = {"trades": [
            {"date": "2003-06-27", "involves_miami": False, "clubs": {
                "Chicago Bulls": {"out": ["T. J. Rookie (draft rights)"], "in": ["cash"]},
                "Phoenix Suns": {"out": ["cash"], "in": ["T. J. Rookie (draft rights)"]}}},
            {"date": "2003-07-10", "involves_miami": True, "clubs": {
                "Phoenix Suns": {"out": ["T. J. Rookie (draft rights)"], "in": ["Someone"]},
                MIAMI: {"out": ["Someone"], "in": ["T. J. Rookie (draft rights)"]}}}],
            "waivers": [{"date": "2003-10-30", "player": "T.J. Rookie", "bbr_id": "rookitj01", "club": "Phoenix Suns"}]}
        moved = self.on(self.rookie, "2003-07-15", transactions=tx)
        self.assertEqual((moved["club"], moved["rights"]), ("Phoenix Suns", True))
        waived = self.on(self.rookie, "2003-10-30", transactions=tx)
        self.assertEqual((waived["club"], waived["code"], waived["rights"]), (None, None, False))

    def test_miami_holdings_and_departures_override_the_world(self):
        holdings = {"entries": [{"player": "Example Veteran", "bbr_id": "examve01", "from": "2003-07-02", "until": "2003-09-01"}]}
        tx = {"signings": [{"date": "2003-07-20", "kind": "signing", "player": "Example Veteran", "bbr_id": "examve01",
                            "from": "Boston Celtics", "to": "Utah Jazz", "involves_miami": False}]}
        self.assertEqual(self.on(self.vet, "2003-07-01", holdings=holdings, transactions=tx)["club"], "Boston Celtics")
        self.assertEqual(self.on(self.vet, "2003-07-25", holdings=holdings, transactions=tx)["club"], MIAMI)
        # After Miami's holding ends, the real move he skipped does not come back: he is a free agent.
        self.assertIsNone(self.on(self.vet, "2003-09-02", holdings=holdings, transactions=tx)["club"])
        departures = {"entries": [{"player": "Example Veteran", "bbr_id": "examve01", "club": "Dallas Mavericks",
                                   "from": "2003-09-02", "until": None, "games": 60, "minutes": 1200}]}
        sent = self.on(self.vet, "2003-09-02", holdings=holdings, departures=departures, transactions=tx)
        self.assertEqual(sent["club"], "Dallas Mavericks")


class ColorTests(unittest.TestCase):
    def setUp(self):
        self.colors = json.loads((ROOT / "library/2003/league/nba_team_colors_2002_2014.json").read_text())

    def test_era_rows_select_by_season_start_year(self):
        self.assertEqual(club_colors(MIAMI, 2003, self.colors)["primary"], "#a6192e")
        self.assertEqual(club_colors(MIAMI, 2006, self.colors)["primary"], "#a6192e")
        self.assertEqual(club_colors(MIAMI, 2007, self.colors)["primary"], "#862633")
        self.assertEqual(club_colors("Atlanta Hawks", 2003, self.colors)["secondary"], "#ffcd00")
        self.assertEqual(club_colors("Atlanta Hawks", 2004, self.colors)["secondary"], "#ffc72c")

    def test_free_agents_and_unknown_clubs_use_the_placeholder(self):
        for club in (None, "Charlotte Bobcats"):
            with self.subTest(club=club):
                colors = club_colors(club, 2003, self.colors)
                self.assertEqual((colors["primary"], colors["secondary"]), ("#1d1d1f", "#c5c7cb"))


class CardContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ctx = CardContext(ROOT)
        cls.players = {p["registry_id"]: p for p in cls.ctx.registry["players"]}
        cls.allowed = {p["headshot_url"] for p in cls.ctx.photos.values()}

    def card(self, pid):
        data = card_data(self.ctx, self.players[pid])
        return data, markdown_card(self.ctx, data), html_card(self.ctx, data)

    def test_photo_player_card(self):
        data, md, html = self.card("terryja01")
        self.assertIn('<img src="https://commons.wikimedia.org/wiki/Special:FilePath/Jason_Terry_3.jpg?width=500"', md)
        self.assertIn("*Photo: Keith Allison, CC BY-SA 2.0", md)
        self.assertIn("**2002-03 (recorded, ATL):** 81 G, 81 GS", md)
        self.assertIn("| 2002-03 | ATL | 81 | 81 |", md)
        self.assertIn("[Interactive card](terryja01.html)", md)
        self.assertIn("GitHub shows it as source", md)
        self.assertEqual(re.findall(r"^## .+$", md, re.M)[-3:], FINAL_SECTIONS)
        self.assertEqual(data["colors"]["primary"], "#c8102e")
        for headers, rows in markdown_tables(md):
            self.assertTrue(all(len(row) == len(headers) for row in rows), headers)
        season = next(rows for headers, rows in markdown_tables(md) if headers[0] == "Scope")
        self.assertEqual(season[0][5], "0")
        self.assertEqual(set(season[0][6:31]), {"N/A"})
        self.assertNotIn("0.0", "".join(season[0][6:]))
        payload = json.loads(re.search(r'type="application/json">(.*?)</script>', html, re.S).group(1)
                             .replace("\\u003c", "<").replace("\\u003e", ">").replace("\\u0026", "&"))
        self.assertEqual(payload["identity"]["photo_url"], data["photo"]["headshot_url"])
        self.assertEqual(payload["identity"]["colors"], {"primary": "#c8102e", "secondary": "#ffcd00"})
        self.assertEqual([p["kind"] for p in payload["periods"]].count("month"), 7)
        self.assertNotIn("shooting", payload["periods"][0])
        self.assertNotIn("FICTIONAL EXAMPLE", html)
        self.assertNotIn("__PLAYER_CARD_DATA__", html)

    def test_no_photo_player_and_rookie_cards(self):
        data, md, html = self.card("sprewla01")
        self.assertIsNone(data["photo"])
        self.assertIn(f'<img src="{SILHOUETTE}"', md)
        self.assertNotIn("http", md.split("<!-- /photo -->")[0].split("<!-- photo -->")[1])
        rookie, rookie_md, _ = self.card("austima01")
        self.assertEqual((rookie["club"]["club"], rookie["club"]["rights"]), ("Chicago Bulls", True))
        self.assertIn("**2003 draft entry:** No. 36 overall, rights held by Chicago Bulls", rookie_md)
        self.assertIn("Unsigned No. 36 second-round draft rights", rookie_md)
        self.assertNotIn("2002-03 (recorded", rookie_md)

    def test_wade_and_miami_cards_link_home_and_never_use_history(self):
        data, md, _ = self.card("wadedw01")
        self.assertIn("[Career page](../../../README.md)", md)
        self.assertIn("UConn (simulation canon)", md)
        self.assertEqual(data["club"]["club"], MIAMI)
        self.assertNotIn("2002-03 (recorded", md)
        self.assertNotIn("Marquette", md)
        _, butler, _ = self.card("butleca01")
        self.assertIn("[Miami card](../../../2003-04/00_Team/Team/Player_Cards/caron_butler.md)", butler)

    def test_every_registry_player_has_both_cards_and_no_invented_photo(self):
        outputs = build_cards(ROOT, self.ctx)
        folder = ROOT / CARDS_DIR
        for pid in self.players:
            self.assertIn(folder / f"{pid}.md", outputs)
            self.assertIn(folder / f"{pid}.html", outputs)
            self.assertIn(folder / "assets" / f"{pid}_header.svg", outputs)
        for path, text in outputs.items():
            if path.suffix == ".svg":
                ElementTree.fromstring(text)
            if path.suffix == ".md" and path.name != "README.md":
                for src in re.findall(r'<img src="([^"]+)"', text):
                    self.assertTrue(src == SILHOUETTE or src in self.allowed, src)
        photos = sum(1 for path, text in outputs.items() if path.suffix == ".md" and 'src="https://' in text)
        self.assertEqual(photos, 331)
        self.assertEqual(check_cards(ROOT), [])
        self.assertEqual(card_errors(ROOT), [])


class PageLinkTests(unittest.TestCase):
    def test_player_cells_become_card_links_and_are_read_back(self):
        page = Path("career/Player/Stats_and_Awards/League/2003-04/11_November/Week_1/League_Stats.md")
        league = page.parents[3]
        registry = {"positions": ["PG"], "players": [
            {"name": "Example Player", "position": "PG", "birth_date": "1980-11-09", "registry_id": "exampl01"}]}
        text = ("# NBA players\n\n## Players by position\n\n<details>\n<summary>PG · Point guards · 1 players</summary>\n\n"
                "| Player | Club / rights | G | MPG | PPG | RPG | APG | SPG | BPG | TOV/G |\n| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
                "| Example Player | TEST rights | 2 | 30.5 | 21.5 | 4.0 | 7.0 | 1.0 | 0.5 | 2.0 |\n\n</details>\n")
        result = format_page(text, page, registry, "2003-11-12", league / "assets/per_game.svg", league)
        headers, rows = next(read_tables(result))
        self.assertEqual(headers, COLUMNS)
        self.assertEqual(rows[0]["Player"], "[Example Player](../../../Players/exampl01.md)")
        self.assertEqual(player_name(rows[0]["Player"]), "Example Player")
        self.assertEqual(result, format_page(result, page, registry, "2003-11-12", league / "assets/per_game.svg", league))
        with self.assertRaises(ValueError):
            format_page(result.replace("[Example Player]", "[Someone Else]"), page, registry, "2003-11-12",
                        league / "assets/per_game.svg", league)

    def test_live_league_pages_link_every_registry_player(self):
        league = ROOT / "career/Dwyane_Wade/Stats_and_Awards/League"
        registry = json.loads((league / "player_registry.json").read_text())
        ids = {p["registry_id"] for p in registry["players"]}
        for page in league.rglob("League_Stats.md"):
            text = page.read_text(encoding="utf-8")
            targets = re.findall(r"^\| \[[^\]]+\]\(((?:\.\./)+Players/([a-z0-9]+)\.md)\)", text, re.M)
            self.assertEqual({pid for _, pid in targets}, ids, page)
            for href, _ in targets[:1]:
                self.assertTrue((page.parent / href).is_file(), href)


if __name__ == "__main__":
    unittest.main()
