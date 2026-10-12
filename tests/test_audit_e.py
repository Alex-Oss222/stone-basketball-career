"""Audit group E (career date 2006-06-20): stored rule texts, the FIBA 2005 page and ranking, the prior-season evidence,
the 2006-07 trajectory feedback, Wade's scoring incentives and where an earned bonus flows, and the library's birth-date
conflicts. Every correction is forward-only: what played games and recorded decisions read stays as it was."""
from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path
import re
import unittest
from unittest import mock

from tests import live_season

ROOT = Path(__file__).resolve().parents[1]
PLAYER = ROOT / "career/Dwyane_Wade"
LEAGUE = PLAYER / "Stats_and_Awards/League"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def one_line(text):
    return " ".join((text or "").split())


class SeasonAwardRuleTests(unittest.TestCase):
    """awards-standings/F4: each season's record states the rule it was decided under."""

    def test_each_record_states_its_own_evidence_end_and_baseline(self):
        from runtime import season_awards
        own = {"2004-05": ("through April 20, 2005", "the simulated 2003-04 season", "over 2003-04"),
               "2005-06": ("through April 19, 2006", "the simulated 2004-05 season", "over 2004-05")}
        for season, phrases in own.items():
            with self.subTest(season=season):
                rule = one_line(read(LEAGUE / season / "season_awards.json")["rule"])
                for phrase in phrases:
                    self.assertIn(phrase, rule)
                self.assertNotIn("through April 14", rule)
                self.assertNotIn("2002-03", rule)
                self.assertEqual(read(LEAGUE / season / "season_awards.json")["rule"], season_awards.rule_text(season, ROOT))
                self.assertTrue(season_awards.states_own_rule(read(LEAGUE / season / "season_awards.json")["rule"], season, ROOT))
        first = read(LEAGUE / "2003-04/season_awards.json")["rule"]           # decided under its own text, kept
        self.assertIn("through April 14", one_line(first))
        self.assertTrue(season_awards.states_own_rule(first, "2003-04", ROOT))
        self.assertIn("real 2002-03 season", one_line(season_awards.rule_text("2003-04", ROOT)))


class DraftOrderRuleTests(unittest.TestCase):
    """awards-standings/F5: each draft order states its own year's lottery."""

    def test_2005_and_2006_orders_state_their_own_lottery(self):
        from runtime import lottery
        for year, season, seeds in ((2005, "2004-05", 14), (2006, "2005-06", 14)):
            with self.subTest(year=year):
                record = read(PLAYER / season / f"09_Draft/draft_order_{year}.json")
                rule = one_line(record["rule"])
                self.assertEqual(len(record["lottery_seeds"]), seeds)
                self.assertIn(f"the {seeds} clubs that missed the simulated {season} playoffs", rule)
                self.assertIn(f"nba_{year}_lottery_rules.json", rule)
                self.assertIn(f"draft_order_{year}.json", rule)
                self.assertIn("all 30 clubs", rule)
                self.assertNotIn("holds No. 4", rule)
                self.assertNotIn("Minnesota", rule)
                self.assertIn("enters the lottery like any other non-playoff club", rule)
                self.assertTrue(lottery.states_own_rule(record["rule"], year))
                self.assertEqual(record["rule"], lottery.rule_text(ROOT, year, seeds))
        with mock.patch.object(lottery, "codes", lambda root=ROOT, y=None: {"Carolina Test Club": "CHA"}):
            self.assertIn("Carolina, the expansion club, enters the lottery", one_line(lottery.rule_text(ROOT, 2006, 14, 30)))
        rule_2004 = one_line(lottery.rule_text(ROOT, 2004, 13, 29))
        self.assertIn("the 13 clubs", rule_2004)
        self.assertIn("holds No. 4 in the first round and No. 33 in the second", rule_2004)
        self.assertIn("forfeited and skipped: the first-round pick of the Minnesota Timberwolves", rule_2004)
        self.assertTrue(lottery.states_own_rule(read(PLAYER / "2003-04/09_Draft/draft_order_2004.json")["rule"], 2004))


class FibaAmericasTests(unittest.TestCase):
    """awards-standings/F1 and F8: the 2005 Americas page's sides and the final ranking's places 9-10."""
    FOLDER = PLAYER / "FIBA/Continental_Cups/2005"
    ROW = re.compile(r"^\| (\d+) \| (\d{4}-\d{2}-\d{2}) \| ([^|]+?) \| ([^|]+?) \| (\d+)-(\d+) \| \[box\]\((Games/[^)]+)\) \|$", re.M)

    def edition(self):
        from runtime import national
        e = national.editions(ROOT)["continental_qualifier_2005"]
        return e, national.read_record(e, ROOT)

    def check_rows(self, text):
        rows = self.ROW.findall(text)
        self.assertEqual(len(rows), 40)
        for number, _day, home, away, hs, as_, box in rows:
            r = read(self.FOLDER / box)
            with self.subTest(game=int(number)):
                self.assertEqual((home.replace("*", ""), away.replace("*", ""), int(hs), int(as_)),
                                 (r["home"], r["away"], r["final_score"]["home"], r["final_score"]["away"]))
        return {int(n): (h.replace("*", ""), a.replace("*", ""), int(x), int(y)) for n, _d, h, a, x, y, _b in rows}

    def test_every_score_sits_with_the_team_that_scored_it(self):
        from runtime.national_pages import page
        rows = self.check_rows((self.FOLDER / "README.md").read_text(encoding="utf-8"))
        self.assertEqual(rows[37], ("Dominican Republic", "United States", 66, 73))   # the host at home; the USA won
        self.assertEqual(rows[39], ("Dominican Republic", "Panama", 82, 68))          # the DR's bronze
        e, rec = self.edition()
        self.check_rows(page(e, rec, ROOT))

    def test_places_nine_and_ten_follow_the_group_records(self):
        from runtime import national
        e, rec = self.edition()
        self.assertEqual(rec["ranking"][8:], ["Venezuela", "Uruguay"])
        self.assertEqual(national.final_ranking(e, rec, ROOT), rec["ranking"])
        self.assertEqual(rec["ranking"][:4], ["Brazil", "United States", "Dominican Republic", "Panama"])   # medals, places

    def test_a_stale_tournament_page_is_refused_and_rebuilt_by_reconcile(self):
        """The merge of 2006-06-20 left the old page in place: no rebuild rendered tournament pages, and validation passed.
        Now a page that no longer reads as its record renders is a validation error and a reconcile step."""
        import importlib.util
        from runtime import national, national_pages
        self.assertEqual(national_pages.stale_pages(ROOT), [])
        readme = self.FOLDER / "README.md"
        rendered = lambda e, rec, root=ROOT: "rendered by a changed renderer\n"
        with mock.patch.object(national_pages, "page", rendered):
            stale = [path for path, _ in national_pages.stale_pages(ROOT)]
            self.assertIn(readme, stale)
            self.assertIn(f"{readme.relative_to(ROOT)}: stale tournament page; run scripts/reconcile.py",
                          national.national_errors(ROOT))
            spec = importlib.util.spec_from_file_location("reconcile_script", ROOT / "scripts/reconcile.py")
            script = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(script)
            self.assertIn(readme, script.tournament_pages(ROOT, write=False))     # --check reports, writes nothing
        self.assertEqual(national_pages.stale_pages(ROOT), [])


class SeasonEvidenceTests(unittest.TestCase):
    """league-stats/LS-4: from 2005-06 the prior-season totals count every appearance; earlier files stand."""

    def test_appearances_counted_from_2005_06_and_earlier_files_reproduced(self):
        from runtime.season_evidence import APPEARANCE_RULE_FROM, compute_totals, totals_path
        self.assertEqual(APPEARANCE_RULE_FROM, "2005-06")
        totals = compute_totals("2005-06", ROOT)
        games = {b: totals[b]["totals"]["games"] for b in ("holcora01", "woodslo01", "greenor01", "turiaro01",
                                                            "maxieja01", "duprero01", "sweetmi01")}
        self.assertEqual(games, {"holcora01": 1, "woodslo01": 14, "greenor01": 74, "turiaro01": 50, "maxieja01": 53,
                                 "duprero01": 71, "sweetmi01": 63})
        for season in ("2003-04", "2004-05"):                     # the evidence their decisions read
            with self.subTest(season=season):
                stored = {r["bbr_id"]: r for r in read(ROOT / totals_path(season))["records"]}
                self.assertEqual(compute_totals(season, ROOT), stored)
        self.assertNotIn("allenma01", compute_totals("2004-05", ROOT))


class FeedbackTests(unittest.TestCase):
    """critic/COMP-01: the 2006-07 feedback matches every player as the league pages do; 2005-06's stands."""

    def test_2006_07_feedback_has_every_matched_player_and_reproduces(self):
        from runtime.season_close import FEEDBACK_MATCH_FROM, feedback
        self.assertEqual(FEEDBACK_MATCH_FROM, "2005-06")
        stored = PLAYER / "2006-07/trajectory_feedback.json"
        data = read(stored)
        for bbr in ("sweetmi01", "medvest01"):
            self.assertIn(bbr, data["players"])
        self.assertAlmostEqual(data["players"]["sweetmi01"]["minutes"], 1193.5, places=1)
        fresh = feedback(ROOT, "2005-06", "2006-07", "2006-06-20")
        self.assertEqual(json.dumps(fresh, indent=1, ensure_ascii=False) + "\n", stored.read_text(encoding="utf-8"))
        old = read(PLAYER / "2005-06/trajectory_feedback.json")             # its games carry its hash: it stands
        self.assertNotIn("medvest01", old["players"])
        self.assertNotIn("allenma01", old["players"])
        replay = feedback(ROOT, "2004-05", "2005-06", "2005-06-16")         # the earlier matcher, unchanged
        self.assertEqual(set(replay["players"]), set(old["players"]))
        self.assertEqual({b: p["minutes"] for b, p in replay["players"].items()},
                         {b: p["minutes"] for b, p in old["players"].items()})

    def test_frozen_ids_read_the_stat_profile_the_engine_played(self):
        from runtime.season_close import frozen_ids
        request = {"frozen": {"home": {"players": [{"player_id": "Mike Sweetney", "stat_profile": {"bbr_id": "sweetmi01"}},
                                                   {"player_id": "No Profile", "stat_profile": None}]},
                              "away": {"players": [{"player_id": "Stanislav Medvedenko",
                                                    "stat_profile": {"bbr_id": "medvest01"}}]}}}
        from runtime.write_back import _key
        self.assertEqual(frozen_ids(request), {("home", _key("Mike Sweetney")): "sweetmi01",
                                               ("away", _key("Stanislav Medvedenko")): "medvest01"})
        self.assertEqual(frozen_ids({"home": {"players": []}}), {})


class IncentiveTests(unittest.TestCase):
    """wade-stats/WADE-STATS-02: the scoring clauses are evaluated, corrected by dated records, and flow forward."""

    def setUp(self):
        from runtime import incentives
        self.inc = incentives
        self.entry = incentives.wade_entry("2005-06", ROOT)

    def test_scoring_benchmark_is_read_from_closed_results(self):
        clause = next(c for c in self.entry["incentives"] if c["id"] == "achievement")
        for season, close, ppg in (("2004-05", "2005-06-16", "21.29"), ("2005-06", "2006-06-20", "27.56")):
            with self.subTest(season=season):
                out = self.inc.evaluate_clause(clause, season, close, ROOT)
                self.assertEqual(out["status"], "met")
                self.assertIn(f"{ppg} per game", out["evidence"])
        short = dict(clause, benchmarks={"2005-06": "At least 17.0 points per game while appearing in at least 83 games."})
        self.assertEqual(self.inc.evaluate_clause(short, "2005-06", "2006-06-20", ROOT)["status"], "not_met")

    def test_dated_corrections_leave_the_closes_and_take_effect_on_2006_06_21(self):
        self.assertEqual(self.inc.incentive_errors(ROOT), [])
        for season, amount in (("2004-05", 236180), ("2005-06", 252660)):
            with self.subTest(season=season):
                close = read(PLAYER / season / "season_close.json")
                achievement = next(e for e in close["incentive_evaluation"] if e["id"] == "achievement")
                self.assertEqual((achievement["status"], achievement["amount"]), ("unrecorded", amount))   # not rewritten
                record = read(PLAYER / season / "season_close_corrections.json")
                self.assertEqual((record["corrected_on"], [c["id"] for c in record["incentive_evaluation"]]),
                                 ("2006-06-21", ["achievement"]))
                before = {e["id"]: e["status"] for e in self.inc.season_evaluation(season, "2006-06-20", ROOT)}
                after = {e["id"]: e for e in self.inc.season_evaluation(season, "2006-06-21", ROOT)}
                self.assertEqual(before["achievement"], "unrecorded")
                self.assertEqual(after["achievement"]["status"], "met")
                self.assertEqual(after["achievement"]["correction"]["corrected_on"], "2006-06-21")
                self.assertEqual(after["minutes"]["status"], "met")

    def test_a_correction_reads_the_contract_its_season_was_played_under(self):
        """A later contract with other incentives never changes a closed season's correction."""
        from runtime import season_close
        later = {"incentives": [{"id": "achievement", "kind": "performance", "classification": "unlikely",
                                 "benchmarks": {}, "amounts": {}}]}
        with mock.patch.object(season_close, "wade_contract", lambda root=ROOT: later):
            self.assertEqual(self.inc.incentive_errors(ROOT), [])
            for season in ("2004-05", "2005-06"):
                with self.subTest(season=season):
                    self.assertEqual(self.inc.correction_record(season, ROOT),
                                     read(PLAYER / season / "season_close_corrections.json"))

    def test_a_correction_that_differs_from_the_evaluator_is_refused(self):
        real = read(PLAYER / "2005-06/season_close_corrections.json")
        bad = deepcopy(real)
        bad["incentive_evaluation"][0]["status"] = "not_met"
        early = dict(real, corrected_on="2006-06-20")
        original = self.inc._read
        for record, words in ((bad, "does not match"), (early, "no earlier than")):
            with self.subTest(words=words):
                def fake(path, record=record):
                    return record if Path(path).name == "season_close_corrections.json" and "2005-06" in str(path) else original(path)
                with mock.patch.object(self.inc, "_read", fake):
                    self.assertTrue(any(words in e for e in self.inc.incentive_errors(ROOT)))

    def test_earned_bonuses_reach_the_finance_summary_only_from_2006_06_21(self):
        self.assertEqual(self.inc.BONUS_FLOW_FROM, "2006-06-21")
        self.assertEqual(self.inc.finance_bonuses("2005-06", "2006-06-20", ROOT), [])
        earned = self.inc.finance_bonuses("2005-06", "2006-06-21", ROOT)
        self.assertEqual([(e["clause"], e["amount"], e.get("corrected_on")) for e in earned],
                         [("minutes", 252660, None), ("achievement", 252660, "2006-06-21")])
        self.assertEqual(sum(e["amount"] for e in self.inc.finance_bonuses("2004-05", "2006-06-21", ROOT)), 472360)
        self.assertEqual(self.inc.finance_bonuses("2006-07", "2006-10-01", ROOT), [])
        evaluation = self.inc.bonus_evaluation(self.entry, "2006-06-21", ROOT)
        self.assertEqual({s: v["earned_unlikely"] for s, v in evaluation.items()},
                         {"2003-04": 439400, "2004-05": 472360, "2005-06": 505320})
        self.assertEqual(evaluation["2005-06"]["unresolved"], ["conditioning_program"])

    def test_the_cap_sheet_lists_earned_bonuses_outside_the_counted_salary(self):
        from runtime import signing
        room = {"cap": 49500000, "committed": 0, "holds": 0, "roster_charge": 0, "room": 49500000, "cap_known": True}
        plain = signing.cap_sheet_text({"players": []}, {"players": []}, room, "2006-06-21")
        earned = self.inc.finance_bonuses("2005-06", "2006-06-21", ROOT)
        text = signing.cap_sheet_text({"players": []}, {"players": []}, room, "2006-06-21", earned)
        self.assertNotIn("Earned Unlikely bonuses", plain)
        self.assertIn("Earned Unlikely bonuses", text)
        self.assertIn("$505,320", text)
        self.assertIn("corrected June 21, 2006, [2005-06/season_close_corrections.json](../../../2005-06/season_close_corrections.json)",
                      text)                                          # the corrected value's evidence, beside the close
        self.assertEqual(text.count("[2005-06/season_close.json]"), 2)
        self.assertEqual(plain.split("## Eight-season commitments")[1].split("## Payroll notes")[0],
                         text.split("## Eight-season commitments")[1].split("## Payroll notes")[0])
        for heading in ("## Current cap position", "## Eight-season commitments", "## Payroll notes", "## Cap reconciliation"):
            self.assertIn(heading, text)

    def test_the_live_finance_check_asks_for_the_bonuses_from_2006_06_21(self):
        from runtime import signing
        original_read = signing.read
        try:
            with live_season():
                live = importlib.reload(signing)
                self.assertEqual(live.SEASON, "2005-06")
                self.assertFalse([e for e in live.ledger_errors(ROOT) if "earned_unlikely_bonuses" in e])
                state = original_read(live.STATE, ROOT)

                def later(path, root=ROOT):
                    if Path(path) == live.STATE:
                        return dict(state, current_date="2006-06-21")
                    return original_read(path, root)
                with mock.patch.object(live, "read", later):
                    self.assertTrue([e for e in live.ledger_errors(ROOT) if "earned_unlikely_bonuses" in e])
        finally:
            importlib.reload(signing)

    def test_the_rollover_writes_bonus_records_from_the_2006_rollover_only(self):
        from runtime.rollover import Rollover
        roll = object.__new__(Rollover)
        roll.root, roll.old = ROOT, "2004-05"
        roll.day = "2005-10-01"                                             # the 2005 rollover replays unchanged
        entry = deepcopy(self.entry)
        placeholder = entry["bonus_evaluation"]
        self.assertEqual(roll.bonus_records([entry]), [])
        self.assertEqual(entry["bonus_evaluation"], placeholder)
        roll.old, roll.day = "2005-06", "2006-10-01"
        earned = roll.bonus_records([entry])
        self.assertEqual([(e["season"], e["clause"], e["amount"]) for e in earned],
                         [("2005-06", "minutes", 252660), ("2005-06", "achievement", 252660)])
        self.assertEqual(sorted(entry["bonus_evaluation"]), ["2003-04", "2004-05", "2005-06"])


class BirthDateConflictTests(unittest.TestCase):
    """ages-identity/BIRTH-01: each unresolved conflict is marked unverified with the other value cited; no value
    changes, and the research file the played 2005 edition hashes is untouched."""
    STATS = ROOT / "library/fiba/player_tournament_stats"
    ROWS = [("eurobasket_2005", "Roko Leni Ukic", "1984-12-05", "1984-05-12"),
            ("eurobasket_2003", "Ibrahim Kutluay", "1974-01-07", "1974-07-01"),
            ("fiba_2002_world_championship", "Ibrahim Kutluay", "1974-01-07", "1974-07-01"),
            ("eurobasket_2005", "Ibrahim Kutluay", "1974-01-07", "1974-07-01"),
            ("afrobasket_2005", "Boniface Ndong", "1977-09-03", "1977-03-09"),
            ("eurobasket_2003", "Dalibor Bagaric", "1980-07-02", "1980-02-07"),
            ("eurobasket_2005", "Dalibor Bagaric", "1980-07-02", "1980-02-07"),
            ("fiba_2005_americas_championship", "Francisco Garcia", "1980-12-31", "1981-12-31"),
            ("fiba_2005_americas_championship", "Peter Ramos", "1985-05-23", "1985-05-13"),
            ("olympics_2004", "Peter Ramos", "1985-05-23", "1985-05-13"),
            ("afrobasket_2005", "Julius Nwosu", "1971-01-05", "1971-05-01"),
            ("eurobasket_2005", "Mirza Teletovic", "1985-09-17", "1985-09-18"),
            ("fiba_2005_americas_championship", "Luis Julio", "1980-12-06", "1980-06-12"),
            ("fiba_2003_americas_championship", "Luis Julio", "1980-12-06", "1980-06-12"),
            ("fiba_2005_americas_championship", "Victor Diaz", "1968-02-04", "1968-04-02"),
            ("fiba_2003_americas_championship", "Victor Diaz", "1968-02-04", "1968-04-02"),
            ("fiba_2002_world_championship", "Victor Diaz", "1968-02-04", "1968-04-02"),
            ("fiba_2005_americas_championship", "Rafael Hettsheimeir", "1986-06-16", "1986-06-18"),
            ("fiba_2005_americas_championship", "Sebastian Izaguirre", "1985-12-04", "1985-04-12"),
            ("fiba_2005_asia_championship", "Khalid Masoud Al Nasr", "1980-10-09", "1980-09-10")]

    def test_tournament_statistics_rows_are_marked_with_the_alternative(self):
        for slug, name, birth, other in self.ROWS:
            with self.subTest(file=slug, player=name):
                data = read(self.STATS / f"{slug}.json")
                row = next(p for p in data["players"] if p["name"] == name)
                self.assertEqual(row["birth_date"], birth)                                  # the value is kept
                self.assertEqual(row["birth_date_status"], "unverified")
                self.assertIn(f"gives {other}", row["birth_date_source"])
                self.assertTrue(any(name in c and other in c for c in data["research"]["conflicts"] if isinstance(c, str)))

    def test_edition_research_rows_and_the_nba_side(self):
        wc = read(ROOT / "library/2006/fiba/fiba_2006_world_championship.json")["rosters"]["teams"]
        for code, i, name, birth, other in (("TUR", 6, "İbrahim Kutluay", "1974-01-07", "1974-07-01"),
                                            ("VEN", 0, "Víctor David Díaz", "1968-02-04", "1968-04-02"),
                                            ("QAT", 0, "Khalid Masoud Al Nasr", "1980-09-10", "1980-10-09")):
            p = wc[code]["players"][i]
            self.assertEqual((p["name"], p["birth_date"], p["field_sources"]["birth_date"]["status"]), (name, birth, "unverified"))
            self.assertIn(other, p["field_sources"]["birth_date"]["note"])
        uru = read(ROOT / "library/2007/fiba/fiba_2007_americas_championship.json")["rosters"]["URU"]["players"]
        izaguirre = next(p for p in uru if p["name"] == "Sebastián Izaguirre")
        self.assertEqual((izaguirre["birth_date"]["value"], izaguirre["birth_date"]["status"]), ("1985-04-12", "unverified"))
        self.assertIn("1985-12-04", izaguirre["birth_date"]["source"])
        ukic = next(p for p in read(ROOT / "library/2005/league/nba_2005_prospect_evidence.json")["players_drafted"]
                    if p.get("bbr_id") == "ukicro01")                     # the date the 2005 draft board read stands
        self.assertEqual((ukic["birth_date"], ukic["birth_date_status"], ukic["age_on_draft_day"]), ("1984-05-12", "sourced", 21))
        self.assertIn("1984-12-05", ukic["birth_date_conflict"])
        self.assertIn("Unresolved", ukic["birth_date_conflict"])
        births = read(ROOT / "library/careers/nba_player_births.json")["players"]        # basketball-reference stands
        self.assertEqual((births["kutluib01"]["birth_date"], births["ndongbo01"]["birth_date"]), ("1974-07-01", "1977-03-09"))
        registry = {p.get("bbr_id"): p for p in read(LEAGUE / "player_registry.json")["players"]}
        self.assertEqual((registry["bagarda01"]["birth_date"], registry["garcifr01"]["birth_date"]), ("1980-02-07", "1981-12-31"))

    def test_built_editions_still_hash_their_research_files(self):
        """The played 2005 edition reads its research file through its built hash: that file is unchanged; the 2006
        edition (no game built) carries its research file's new hash."""
        for edition, raw in (("continental_qualifier_2005", "library/2005/fiba/fiba_2005_americas_championship.json"),
                             ("world_cup_finals_2006", "library/2006/fiba/fiba_2006_world_championship.json")):
            with self.subTest(edition=edition):
                built = read(ROOT / f"library/fiba/engine/{edition}.json")
                self.assertEqual(built["source_sha256"], hashlib.sha256((ROOT / raw).read_bytes()).hexdigest())
        self.assertEqual(hashlib.sha256((ROOT / "library/2005/fiba/fiba_2005_americas_championship.json").read_bytes()).hexdigest(),
                         read(ROOT / "library/fiba/engine/continental_qualifier_2005.json")["source_sha256"])
        wc = read(ROOT / "library/2006/fiba/fiba_2006_world_championship.json")
        self.assertTrue(any("BIRTH-01" in c for c in wc["research"]["conflicts"]))


if __name__ == "__main__":
    unittest.main()
