import json
import unittest
from pathlib import Path

from runtime.award_records import (CATALOG_PATH, FACT_STATUSES, SCOPES, awards_in_force, load_catalog,
                                   rules_in_force, season_start)
from runtime.standing import HONOR_NAMES

ROOT = Path(__file__).resolve().parents[1]
SEASON_RE = r"^\d{4}-\d{2}$"


def facts(node):
    """Every {value, status, sources} fact nested in a catalogue entry."""
    if isinstance(node, dict):
        if set(node) >= {"value", "status", "sources"}:
            yield node
        else:
            for v in node.values():
                yield from facts(v)
    elif isinstance(node, list):
        for v in node:
            yield from facts(v)


class CatalogSchemaTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load_catalog()
        self.by_id = {a["id"]: a for a in self.catalog["awards"]}

    def test_location_and_purpose(self):
        self.assertEqual(CATALOG_PATH, ROOT / "library/2003/league/nba_awards_catalog.json")
        self.assertIn("league_cap_history", self.catalog["location_note"])
        self.assertIn("never applies retroactively", self.catalog["era_gating"])

    def test_every_award_has_identity_scope_and_first_season(self):
        ids = [a["id"] for a in self.catalog["awards"]]
        self.assertEqual(len(ids), len(set(ids)))
        for a in self.catalog["awards"]:
            with self.subTest(award=a["id"]):
                for key in ("name", "short_name"):
                    self.assertTrue(isinstance(a[key], str) and a[key].strip())
                self.assertIn(a["scope"], SCOPES)
                self.assertIn(a["category"], ("performance", "non_performance"))
                self.assertRegex(a["first_season"]["value"], SEASON_RE)
                self.assertIn(a["first_season"]["status"], FACT_STATUSES)
                if a["last_season"] is not None:
                    self.assertRegex(a["last_season"]["value"], SEASON_RE)
                    self.assertLessEqual(season_start(a["first_season"]["value"]), season_start(a["last_season"]["value"]))
                self.assertTrue(a["honor_names"])
                self.assertIn("kind", a["electorate"])
                self.assertIn("size", a["electorate"])
                self.assertIn("rule", a["scoring"])
                self.assertIn(a["period"], self.catalog["periods"])
                self.assertTrue(a["sources"], "an award names at least one fetched source")

    def test_every_fact_is_marked_and_every_source_is_registered(self):
        registry = self.catalog["sources"]
        for key, src in registry.items():
            self.assertTrue(src["url"].startswith("https://"), key)
            self.assertIn(src["kind"], ("nba", "basketball_reference", "wikipedia"))
            self.assertRegex(src["verified_on"], r"^\d{4}-\d{2}-\d{2}$")
        for section in ("awards", "rules", "periods"):
            for f in facts(self.catalog[section]):
                self.assertIn(f["status"], FACT_STATUSES)
                for s in f["sources"]:
                    self.assertIn(s, registry)
                if f["status"] in ("sourced", "derived"):
                    self.assertTrue(f["sources"] or f.get("note"), f"a sourced fact names its page: {f}")
        for a in self.catalog["awards"]:
            for s in a["sources"] + a["era_rules"]:
                self.assertTrue(s in registry or s in {r["id"] for r in self.catalog["rules"]}, s)
        for r in self.catalog["rules"]:
            self.assertRegex(r["first_season"], SEASON_RE)
            self.assertIn(r["status"], FACT_STATUSES)
            for award_id in r["applies_to"]:
                self.assertIn(award_id, self.by_id)

    def test_electorate_sizes_and_scoring_rules_are_never_bare_numbers_without_a_source(self):
        for a in self.catalog["awards"]:
            size = a["electorate"]["size"]
            if isinstance(size["value"], int):
                self.assertIn(size["status"], ("sourced", "derived"), a["id"])
                self.assertTrue(size["sources"], a["id"])
            rule = a["scoring"]["rule"]
            if rule["status"] == "unverified":
                self.assertIsNone(rule["value"], a["id"])

    def test_standing_honor_names_exist_in_the_catalogue(self):
        names = {n for a in self.catalog["awards"] for n in a["honor_names"]}
        for name in HONOR_NAMES:
            self.assertIn(name, names)
        self.assertEqual(self.by_id["all_star_selection"]["competition"], "regular")
        self.assertEqual(self.by_id["finals_mvp"]["competition"], "playoff")


class EraGatingTests(unittest.TestCase):
    def test_2003_04_in_force_set(self):
        ids = {a["id"] for a in awards_in_force("2003-04")}
        for wanted in ("mvp", "roy", "dpoy", "smoy", "mip", "coy", "eoy", "all_nba", "all_defensive", "all_rookie",
                       "player_of_month", "rookie_of_month", "player_of_week", "finals_mvp", "all_star_selection",
                       "all_star_game_mvp", "rising_stars_mvp", "sportsmanship", "kennedy_citizenship",
                       "scoring_title", "steals_title", "three_pct_title"):
            self.assertIn(wanted, ids)
        for later in ("clutch_poy", "hustle", "teammate_of_year", "nba_cup_mvp", "nba_cup_all_tournament",
                      "social_justice_champion", "bob_lanier_community_assist"):
            self.assertNotIn(later, ids)
        self.assertNotIn("comeback_poy", ids, "discontinued in 1986-87")
        self.assertIn("comeback_poy", {a["id"] for a in awards_in_force("1983-84")})

    def test_first_seasons_gate_exactly(self):
        self.assertIn("clutch_poy", {a["id"] for a in awards_in_force("2022-23")})
        self.assertNotIn("clutch_poy", {a["id"] for a in awards_in_force("2021-22")})
        self.assertIn("nba_cup_mvp", {a["id"] for a in awards_in_force("2023-24")})

    def test_65_game_rule_is_not_in_force_in_2003_04(self):
        rules_2003 = {r["id"] for r in rules_in_force("2003-04")}
        self.assertNotIn("games_played_65_2023_24", rules_2003)
        self.assertNotIn("all_nba_positionless_2023_24", rules_2003)
        self.assertNotIn("all_defensive_media_vote_2013_14", rules_2003)
        self.assertNotIn("stat_titles_58_games_2013_14", rules_2003)
        self.assertIn("mvp_media_vote_1980_81", rules_2003)
        self.assertIn("all_nba_third_team_1988_89", rules_2003)
        self.assertIn("games_played_65_2023_24", {r["id"] for r in rules_in_force("2023-24")})
        rule = next(r for r in load_catalog()["rules"] if r["id"] == "games_played_65_2023_24")
        self.assertEqual(rule["first_season"], "2023-24")
        self.assertNotIn("roy", rule["applies_to"])

    def test_season_format(self):
        self.assertEqual(season_start("1999-00"), 1999)
        for bad in ("2003", "2003-05", "03-04", 2003):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                season_start(bad)


if __name__ == "__main__":
    unittest.main()
