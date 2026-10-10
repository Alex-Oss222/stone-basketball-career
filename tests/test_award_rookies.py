"""Rookie pool and the stated rule of the weekly and monthly awards (`runtime/award_decisions.py`).

The pool resolves every first-season bbr_id to each name the season's records give him, wherever the simulated league
placed him (the 2005-06 audit: Wayne Simien, Matt Walsh, Gerald Fitch and Earl Barron, real Miami players sent to other
clubs by rule 1, were left out because names came only from the real rosters and Miami's register). Each season's
record states the rule with its own calendar and the identity sources that named its rookies; `repair_rules` rewrites
only that field, and only of a record whose stated opening night is not its own (the 2003-04 record is kept).
"""
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from runtime import award_decisions as A

SEASON = "2005-06"


def put(root, rel, data):
    path = Path(root) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def role(pid, bbr, club=None):
    return {"player_id": pid, "bbr_id": bbr, "position": "SF", "games": 60, "minutes": 1200, "span": [0.0, 1.0],
            "window": [0.0, 1.0], **({"club": club} if club else {})}


def frozen_player(pid, bbr):
    return {"player_id": pid, "position": "SF", "minutes": 20.0, "ratings": {}, "stat_profile": {"bbr_id": bbr}}


def world(root):
    """A 2005-06 league: veterans and rookies placed by each record the game inputs are built from."""
    careers = {b: {"player_name": n, "seasons": {s: {"minutes": 500} for s in seasons}} for b, n, seasons in (
        ("veteran01", "Vera Veteran", ["2003-04", "2004-05", "2005-06"]),
        ("rookreal01", "Rory Realroster", ["2005-06"]),
        ("simiewa01", "Wayne Simien", ["2005-06", "2006-07"]),
        ("poolro01", "Polly Pool", ["2005-06"]),
        ("moveda01", "Moe Movedsign", ["2005-06"]),
        ("heatro01", "Hal Heatrookie", ["2005-06"]),
        ("frozro01", "Fred Frozen", ["2005-06"]),
        ("ghostro01", "Gus Ghost", ["2005-06"]),
        ("wadedw01", "Dwyane Wade", ["2003-04", "2004-05", "2005-06"]))}
    put(root, "library/careers/nba_player_careers.json", {"schema_version": 1, "players": careers})
    put(root, "library/2005/league/nba_2005_service_years.json",
        {"schema_version": 1, "players": {"veteran01": {"first_season": "2003-04"}, "wadedw01": {"first_season": "2003-04"}}})
    put(root, "library/2005/league/nba_2005_06_team_rosters.json", {"schema_version": 1, "clubs": {
        "Atlanta Hawks": {"code": "ATL", "players": [role("Vera Veteran", "veteran01"), role("Rory Realroster", "rookreal01")]}}})
    put(root, "career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json", {"players": [
        {"name": "Vera Veteran", "bbr_id": "veteran01", "cohort": "end_2002_03_roster"},
        {"name": "Dwyane Wade", "bbr_id": "wadedw01", "cohort": "2003_draft_rights"},
        {"name": "simiewa01", "bbr_id": "simiewa01", "cohort": "2003_04_appearance"}]})
    # Real Miami's 2005 rookie, sent to Toronto by the summer market (rule 1): his book row and game rows key him by id.
    put(root, f"career/Dwyane_Wade/{SEASON}/League/opening_rosters.json", {
        "season": SEASON, "kind": "opening_rosters",
        "clubs": {"Toronto Raptors": [dict(role("simiewa01", "simiewa01", "Toronto Raptors"), games=0, minutes=0)]},
        "pool": [dict(role("Polly Pool", "poolro01"), club=None)], "not_placed": []})
    put(root, f"career/Dwyane_Wade/{SEASON}/League/league_moves.json", {"season": SEASON, "kind": "league_moves", "entries": [
        {"id": "m1", "date": "2005-11-10", "kind": "rest_of_season", "player": "Moe Movedsign", "bbr_id": "moveda01",
         "from": None, "to": "Atlanta Hawks", "role": role("Moe Movedsign", "moveda01")}]})
    put(root, f"career/Dwyane_Wade/{SEASON}/00_Team/Team/Roster/roster.json", {"players": [
        {"name": "Dwyane Wade", "bbr_id": None}, {"name": "Hal Heatrookie", "bbr_id": "heatro01"}]})
    # A first-season player seen only in a committed request's frozen inputs (the ids the rows carry).
    put(root, f"career/Dwyane_Wade/Stats_and_Awards/League/{SEASON}/Games/2005-11-20-x.request.json", {
        "event_id": "x", "game_date": "2005-11-20", "game_type": "regular", "venue": "home",
        "home": {"team": "Atlanta Hawks", "rotation": "real"}, "away": {"team": "Toronto Raptors", "rotation": "real"},
        "frozen": {"home": {"team_id": "Atlanta Hawks", "players": [frozen_player("Vera Veteran", "veteran01")]},
                   "away": {"team_id": "Toronto Raptors", "players": [frozen_player("Fred Frozen", "frozro01")]}}})


def line(pid, pts):
    return dict(player_id=pid, pts=pts, fgm=pts // 2, fga=pts // 2 + 5, ftm=0, fta=0, orb=1, drb=4, ast=2, stl=1, blk=0,
                tov=1, pf=2, minutes=24.0, seconds=1440.0)


class PoolTests(unittest.TestCase):
    def test_every_first_season_player_is_named_as_his_records_name_him_wherever_he_was_placed(self):
        with tempfile.TemporaryDirectory() as tmp:
            world(tmp)
            first = A.first_season_ids(tmp, SEASON)
            self.assertEqual(first, {"rookreal01", "simiewa01", "poolro01", "moveda01", "heatro01", "frozro01", "ghostro01"})
            pool = A.rookies(tmp, SEASON)
            # Real roster, opening book (keyed by id), pool, dated move, Miami's register and frozen inputs alike.
            for name in ("Rory Realroster", "simiewa01", "Polly Pool", "Moe Movedsign", "Hal Heatrookie", "Fred Frozen"):
                self.assertIn(name, pool)
            self.assertNotIn("Vera Veteran", pool)
            self.assertNotIn("Dwyane Wade", pool)                      # a 2003-04 rookie, not a 2005-06 one
            self.assertNotIn("Gus Ghost", pool)                        # no identity record names him: never inferred

    def test_a_rookie_keyed_by_his_id_in_the_game_rows_is_ranked_for_rookie_of_the_month(self):
        rows = [{"result": {"game_date": f"2005-11-{d:02d}", "event_id": f"g{d}", "home": "Toronto Raptors",
                            "away": "Atlanta Hawks", "final_score": {"home": 100, "away": 90},
                            "player_stats": {"home": [line("simiewa01", 14)], "away": [line("Rory Realroster", 10)]}}}
                for d in (2, 4, 6)]
        conf = {"Toronto Raptors": "East", "Atlanta Hawks": "East"}
        with tempfile.TemporaryDirectory() as tmp:
            world(tmp)
            table = A.rank("rookie_of_month", "2005-11-01", "2005-11-30", rows, conf, A.rookies(tmp, SEASON))
        self.assertEqual([x["player"] for x in table["East"]], ["simiewa01", "Rory Realroster"])

    def test_wade_is_a_rookie_in_2003_04_by_his_records_key_and_no_later(self):
        self.assertIn(A.WADE, A.rookies(A.ROOT, "2003-04"))
        self.assertNotIn(A.WADE, A.rookies(A.ROOT, "2004-05"))
        self.assertNotIn(A.WADE, A.rookies(A.ROOT, "2005-06"))

    def test_real_miami_rookies_placed_elsewhere_in_2005_06_are_in_the_pool(self):
        pool = A.rookies(A.ROOT, "2005-06")
        self.assertLessEqual({"simiewa01", "walshma01", "fitchge01", "barroea01"}, pool)
        names = A.season_names(A.ROOT, "2005-06")
        unnamed = sorted(b for b in A.first_season_ids(A.ROOT, "2005-06") if b not in names)
        book = json.loads((A.ROOT / "career/Dwyane_Wade/2005-06/League/opening_rosters.json").read_text(encoding="utf-8"))
        placed = {p["bbr_id"] for rows in book["clubs"].values() for p in rows}
        self.assertEqual([b for b in unnamed if b in placed], [])     # every placed first-season player has his name

    def test_a_rookie_is_named_by_his_dated_record_name_and_his_roster_spelling(self):
        # The registry spelling (what the All-Star rookie pool compares) and the real-roster spelling (what the rows
        # carry) both enter: the wider 2003-04 All-Star pool is reported, the recorded Rookie Challenge stands.
        pool = A.rookies(A.ROOT, "2003-04")
        self.assertLessEqual({"Mickael Pietrus", "Darko Milicic"}, pool)
        self.assertIn("pietrmi01", A.first_season_ids(A.ROOT, "2003-04"))


class RuleTests(unittest.TestCase):
    def test_each_season_states_its_own_calendar(self):
        later = A.rule_text("2005-06")
        self.assertIn("opening night,\n  November 1, 2005, through Sunday, November 6, 2005", later)
        self.assertIn("no October is folded in", later)
        self.assertIn("The first month runs November 1 to November 30, 2005; the last runs April 1 to April 19, 2006.", later)
        self.assertNotIn("October 28", later)
        first = A.rule_text("2003-04")
        self.assertIn("October 28, 2003, through Sunday, November 2, 2003", first)
        self.assertIn("October is folded into November because the season opened October 28, 2003.", first)
        self.assertIn("The first month runs October 28 to November 30, 2003", first)

    def test_each_season_names_only_the_identity_sources_that_named_its_rookies(self):
        flat = {s: " ".join(A.rule_text(s).split()) for s in ("2003-04", "2004-05", "2005-06")}
        self.assertIn("the registry's 2003 draft-rights cohort, the unattached identities with no NBA season before "
                      "2003-04 (`nba_2003_unattached_identities.json`) and the players whose first NBA season the 2004 "
                      "service file gives as 2003-04", flat["2003-04"])
        # No registry draft-rights cohort exists after 2003: a later record never cites it.
        self.assertIn("the sourced identity records name: the players whose first NBA season the 2004 service file "
                      "gives as 2004-05 (`nba_2004_service_years.json`).", flat["2004-05"])
        self.assertIn("the players of the real careers table whose first season is 2005-06 and whom the 2005 service "
                      "file, which lists everyone with an earlier NBA season, does not list", flat["2005-06"])
        for season in ("2004-05", "2005-06"):
            self.assertNotIn("draft-rights cohort", flat[season])
            self.assertNotIn("draft class", flat[season])
        named = {s: [label for label, ids in A.first_season_sources(A.ROOT, s) if ids] for s in flat}
        for season, labels in named.items():
            self.assertTrue(labels)
            for label in labels:
                self.assertIn(" ".join(label.split()), flat[season])
        self.assertEqual(set().union(*(ids for _, ids in A.first_season_sources(A.ROOT, "2005-06"))),
                         A.first_season_ids(A.ROOT, "2005-06"))

    def test_a_rule_states_its_own_calendar_only_with_its_own_opening_night(self):
        legacy = ("- Player of the Week: Monday to Sunday (the opening week runs from opening night, October 28), "
                  "announced\n  the Monday after; the final week ends on the last regular-season day.")
        self.assertTrue(A.states_own_calendar(legacy, "2003-04"))      # the 2003-04 text is its own calendar
        self.assertFalse(A.states_own_calendar(legacy, "2004-05"))     # opened November 2, 2004
        self.assertFalse(A.states_own_calendar(legacy, "2005-06"))     # opened November 1, 2005
        self.assertTrue(A.states_own_calendar(A.rule_text("2005-06"), "2005-06"))
        self.assertFalse(A.states_own_calendar(A.rule_text("2005-06"), "2004-05"))
        self.assertFalse(A.states_own_calendar("old 2003-04 text", "2003-04"))
        self.assertFalse(A.states_own_calendar(None, "2003-04"))

    def test_a_new_record_states_its_own_season(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(A, "rule_text", lambda season, root=None: f"rule {season}"):
            self.assertEqual(A.read_decisions(tmp, "2006-07")["rule"], "rule 2006-07")

    def test_repair_rewrites_only_the_rule_field(self):
        decisions = [{"id": "x", "award": "rookie_of_month", "winner": "Chris Paul", "shortlist": [{"player": "Chris Paul"}]}]
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(A, "rule_text", lambda season, root=None: f"rule {season}"):
            for season in ("2004-05", "2005-06"):
                put(tmp, A.decisions_path(season), {"schema_version": 1, "season": season, "kind": "award_decisions",
                                                    "rule": "old 2003-04 text", "decisions": decisions})
            before = {s: json.loads((Path(tmp) / A.decisions_path(s)).read_text(encoding="utf-8")) for s in ("2004-05", "2005-06")}
            self.assertEqual(A.repair_rules(tmp), [A.decisions_path("2004-05").as_posix(), A.decisions_path("2005-06").as_posix()])
            for season, old in before.items():
                new = json.loads((Path(tmp) / A.decisions_path(season)).read_text(encoding="utf-8"))
                self.assertEqual(list(new), list(old))                   # the key keeps its place
                self.assertEqual(new["rule"], f"rule {season}")
                self.assertEqual({k: v for k, v in new.items() if k != "rule"}, {k: v for k, v in old.items() if k != "rule"})
            self.assertEqual(A.repair_rules(tmp), [])                    # idempotent

    def test_repair_keeps_a_record_that_already_states_its_own_calendar(self):
        legacy = "Player of the Week: Monday to Sunday (the opening week runs from opening night, October 28), announced"
        own = {"2003-04": legacy, "2004-05": legacy,
               "2005-06": "The opening week runs from opening night,\n  November 1, 2005, through Sunday"}
        openings = {"2003-04": "2003-10-28", "2004-05": "2004-11-02", "2005-06": "2005-11-01"}
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(A, "rule_text", lambda season, root=None: f"rule {season}"), \
                mock.patch.object(A, "periods", lambda season=None, root=None: [("player_of_week", openings[season], "", "")]):
            for season, rule in own.items():
                put(tmp, A.decisions_path(season), {"schema_version": 1, "season": season, "kind": "award_decisions",
                                                    "rule": rule, "decisions": []})
            before = {s: (Path(tmp) / A.decisions_path(s)).read_bytes() for s in own}
            self.assertEqual(A.repair_rules(tmp), [A.decisions_path("2004-05").as_posix()])
            self.assertEqual(A.repair_rules(tmp, seasons=["2003-04", "2005-06"]), [])   # named or not, kept as written
            for season in ("2003-04", "2005-06"):
                self.assertEqual((Path(tmp) / A.decisions_path(season)).read_bytes(), before[season])


if __name__ == "__main__":
    unittest.main()
