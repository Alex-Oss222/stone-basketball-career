"""The final audit of 2006-06-20, group 1: a league move the engine never applied assigns no contract (Eddie Jones in the
2005-01-31 Utah-Houston trade), the league's desks leave a pinned player out of their candidates from 2006-06-21, and an
ended League period without a game reads complete."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from runtime import league_market, league_moves, league_trades, player_contracts, write_back

ROOT = Path(__file__).resolve().parents[1]
LEAGUE = Path("career/Dwyane_Wade/Stats_and_Awards/League")
EMPTY = dict(holdings={"entries": []}, departures={"entries": []}, transactions={})
VET = {"name": "Example Veteran", "bbr_id": "examve01", "registry_id": "examve01", "team_name": "Boston Celtics",
       "team_code": "BOS", "cohort": "end_2002_03_roster", "position": "PG", "birth_date": "1984-01-17"}


def assignments(profile):
    contracts = ([profile["current"]] if profile["current"] else []) + profile["history"]
    return sorted({(a["date"], a["from"], a["to"]) for c in contracts for a in c.get("assignment_history", [])})


class PinnedTests(unittest.TestCase):
    def test_miami_departures_are_pinned_for_their_window(self):
        self.assertIn("jonesed02", league_moves.pinned("2004-05", "2005-01-31", ROOT))
        self.assertNotIn("jonesed02", league_moves.pinned("2004-05", "2005-01-23", ROOT))
        self.assertEqual(sorted(league_moves.pinned("2005-06", "2006-06-20", ROOT)), ["grantbr01", "harprma01"])


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        catalog = player_contracts.build_contract_catalog(ROOT, "career/Dwyane_Wade", "2006-06-20")
        cls.profiles = {p["id"]: p for p in catalog["players"]}

    def test_the_trade_the_engine_never_applied_assigns_nothing(self):
        # Miami's departure pinned Eddie Jones to Utah until Miami traded for him again: the league trade of 2005-01-31
        # moved its three other players only
        self.assertEqual(assignments(self.profiles["jonesed02"]),
                         [("2005-01-24", "Miami Heat", "Utah Jazz"), ("2005-08-05", "Utah Jazz", "Miami Heat")])
        self.assertIn(("2005-01-31", "Utah Jazz", "Houston Rockets"), assignments(self.profiles["jonesfr01"]))
        self.assertIn(("2005-01-31", "Houston Rockets", "Utah Jazz"), assignments(self.profiles["nachbbo01"]))
        self.assertIn(("2005-01-31", "Houston Rockets", "Utah Jazz"), assignments(self.profiles["robingl01"]))
        self.assertEqual(self.profiles["jonesed02"]["team"], "Miami Heat")

    def test_only_assignments_are_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            player = root / "career/Dwyane_Wade"
            ledger = player / "2004-05/League/league_moves.json"
            ledger.parent.mkdir(parents=True)
            entries = [{"date": "2005-02-01", "kind": "trade", "player": "Pinned", "bbr_id": "pinned01", "from": "Utah Jazz", "to": "Houston Rockets"},
                       {"date": "2005-02-01", "kind": "trade", "player": "Other", "bbr_id": "other01", "from": "Houston Rockets", "to": "Utah Jazz"},
                       {"date": "2005-02-02", "kind": "claim", "player": "Pinned", "bbr_id": "pinned01", "from": None, "to": "Boston Celtics"},
                       {"date": "2005-02-03", "kind": "waive", "player": "Pinned", "bbr_id": "pinned01", "from": "Utah Jazz", "to": None},
                       {"date": "2005-02-04", "kind": "expire", "player": "Pinned", "bbr_id": "pinned01", "from": "Utah Jazz", "to": None}]
            ledger.write_text(json.dumps({"season": "2004-05", "entries": entries}), encoding="utf-8")
            departures = player / "2004-05/00_Team/Team/Roster/departures.json"
            departures.parent.mkdir(parents=True)
            departures.write_text(json.dumps({"entries": [{"player": "Pinned", "bbr_id": "pinned01", "club": "Utah Jazz",
                                                           "from": "2005-01-24", "until": None}]}), encoding="utf-8")
            profiles = {b: {"name": b} for b in ("pinned01", "other01")}
            moves = []
            player_contracts._league_moves(player, "2006-06-20", lambda row: row["bbr_id"], profiles, "Dwyane Wade", root, moves)
        self.assertEqual([(m["kind"], m["bbr_id"]) for m in moves], [("trade", "other01"), ("waive", "pinned01"), ("expire", "pinned01")])


def contract(bbr, season):
    return {"bbr_id": bbr, "player": bbr, "status": "under_contract", "schedule": {season: 1000000}}


class DeskTests(unittest.TestCase):
    """The league's trade desk and market on a date: from PINNED_FROM a pinned player is no candidate."""
    ROSTER = [{"bbr_id": "keep01", "player_id": "Keep", "minutes": 2000, "games": 80},
              {"bbr_id": "pinned01", "player_id": "Pinned", "minutes": 1000, "games": 80}]

    def desk(self, day):
        from runtime.seasons import season_of_date
        season = season_of_date(day)
        assets = SimpleNamespace(contracts={"Utah Jazz": {"players": [contract("keep01", season), contract("pinned01", season)]}})
        with mock.patch.object(league_trades, "Assets", return_value=assets), \
                mock.patch.object(league_trades, "LeagueBook", return_value=SimpleNamespace(club=lambda c: {"payroll": 0})), \
                mock.patch("runtime.skill_fit.SkillFit"), \
                mock.patch.object(league_trades, "effective_roster", return_value=[dict(p) for p in self.ROSTER]), \
                mock.patch.object(league_trades, "ConsentBook"), mock.patch.object(league_trades, "read_json", return_value={}), \
                mock.patch.object(league_trades, "market_signings", return_value={}), \
                mock.patch.object(league_trades, "in_season_signings", return_value={}), \
                mock.patch.object(league_trades, "pinned", return_value=frozenset({"pinned01"})):
            return league_trades.LeagueTradeDesk(day, None, ROOT)

    def market(self, day):
        assets = SimpleNamespace(form_value=lambda b: {"keep01": 5.0, "pinned01": 1.0}[b])
        with mock.patch.object(league_market, "_rules", return_value={}), \
                mock.patch.object(league_market, "Assets", return_value=assets), \
                mock.patch.object(league_market, "LeagueBook", return_value=SimpleNamespace(inventory={"Utah Jazz": {}})), \
                mock.patch("runtime.skill_fit.SkillFit"), \
                mock.patch.object(league_market, "read_moves", return_value={"entries": []}), \
                mock.patch.object(league_market, "effective_roster", return_value=[dict(p) for p in self.ROSTER]), \
                mock.patch("runtime.league_moves._protected_contracts", return_value=set()), \
                mock.patch("runtime.standings.worst_first", return_value=["Utah Jazz"]), \
                mock.patch.object(league_market, "pinned", return_value=frozenset({"pinned01"})):
            return league_market.LeagueMarket(day, None, ROOT)

    def test_trade_candidates_leave_a_pinned_player_out_from_the_gate(self):
        self.assertEqual(league_moves.PINNED_FROM, "2006-06-21")
        after = self.desk("2006-11-06")
        self.assertEqual([g for g, _ in after._packages("Utah Jazz")], [["keep01"]])
        self.assertTrue(after.blocked("pinned01"))
        self.assertIsNone(after.evaluate("Utah Jazz", ["pinned01"], "Utah Jazz", ["keep01"]))
        before = self.desk("2005-11-07")                  # every earlier scan replays unchanged
        self.assertEqual([g for g, _ in before._packages("Utah Jazz")], [["keep01"], ["pinned01"], ["keep01", "pinned01"]])
        self.assertIsNone(before.blocked("pinned01"))

    def test_the_market_never_waives_a_pinned_player_from_the_gate(self):
        after = self.market("2006-11-06")
        self.assertEqual(after._weakest("Utah Jazz", waiving=True)["bbr_id"], "keep01")
        self.assertEqual(after._weakest("Utah Jazz")["bbr_id"], "pinned01")      # a claim still has to beat him
        before = self.market("2006-02-06")
        self.assertEqual(before.pinned, frozenset())
        self.assertEqual(before._weakest("Utah Jazz", waiving=True)["bbr_id"], "pinned01")


class LeaguePageTests(unittest.TestCase):
    PAGE = ROOT / LEAGUE / "2003-04/10_October/Week_3/League_Stats.md"

    def page(self, line):
        row = "| [Example Veteran](../../../Players/examve01.md) | 30 | BOS | NBA | PG |" + " N/A |" * 26 + "\n"
        header = "| " + " | ".join(write_back.LEAGUE_COLUMNS) + " |\n| " + " | ".join("---" for _ in write_back.LEAGUE_COLUMNS) + " |\n"
        return (f"# NBA players | October 2003 | Week 3\n\n653 tracked players · 0 closed games in this record · {line}\n\n"
                "## Leaders\n\nx\n\n## Players by position\n\n"
                "Age is each player's age on 2003-10-21, the period's end.\n\n"
                "<details>\n<summary>PG · Point guards · 83 players</summary>\n\n### PG: per game\n\n" + header + row
                + "\n</details>\n\n## Coverage\n\nx\n")

    def test_an_ended_period_without_a_game_reads_complete_on_live_and_closed_pages(self):
        players = {"examve01": VET}
        for live in (True, False):
            text = write_back.league_page(self.page("Not started as of June 26, 2003."), self.PAGE, {}, "2006-06-20", [], {},
                                          players, ROOT, EMPTY, live=live)
            self.assertIn("1 tracked players · 0 closed games in this record · Complete; no NBA game in this period.", text)
            self.assertNotIn("Not started", text)

    def test_a_period_that_has_not_ended_keeps_its_line(self):
        text = write_back.league_page(self.page("Not started as of June 26, 2003."), self.PAGE, {}, "2003-10-16", [], {},
                                      {"examve01": VET}, ROOT, EMPTY, live=True)
        self.assertIn("1 tracked players · 0 closed games in this record · Not started as of June 26, 2003.", text)


if __name__ == "__main__":
    unittest.main()
