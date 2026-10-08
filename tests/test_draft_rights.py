"""Draft rights by draft year (roadmap S1): Required Tender windows from each agreement's rules file, the 2003 records
unchanged, 2004 picks under the 1999 agreement, 2005 picks under the 2005 agreement, rights ending at the next draft,
and the writers that keep those records through a summer and a rollover."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

from runtime import draft_rights
from runtime.draft_rights import (agreement_for, draft_date, draft_rights_errors, end_rights, record_tenders, season_errors,
                                  tender_rules, window)
from tests import live_season

ROOT = Path(__file__).resolve().parents[1]
PLAYER = Path("career/Dwyane_Wade")


def write(root, rel, data):
    path = Path(root) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")


def pick(name, status="unsigned_draft_rights", **extra):
    return dict({"id": name.lower().replace(" ", "_"), "name": name, "positions": ["SF"], "status": status}, **extra)


def scaffold(root, season, today, players, tenders=None, draft=None):
    """A scratch season: its state, Miami's register, its tenders (None: no file) and its simulated draft record
    ({year: [picks]})."""
    write(root, PLAYER / season / "current_state.json", {"season": season, "current_date": today})
    write(root, PLAYER / season / "00_Team/Team/Roster/roster.json", {"season": season, "team": "Miami Heat", "players": players})
    book = Path(root) / PLAYER / season / "00_Team/Transactions/required_tenders.json"
    if tenders is None:
        book.unlink(missing_ok=True)
    else:
        write(root, book.relative_to(root), {"season": season, "tenders": tenders})
    for year, picks in (draft or {}).items():
        write(root, PLAYER / season / f"09_Draft/draft_{year}.json",
              {"date": draft_date(year), "picks": [dict(p, club="Miami Heat") for p in picks]})


class RulesFromDataTests(unittest.TestCase):
    def test_2003_constants_are_unchanged_and_now_read_from_the_1999_rules_file(self):
        self.assertEqual(draft_rights.FIRST_ROUND_BY, "2003-07-15")
        self.assertEqual(draft_rights.SECOND_ROUND_WINDOW, ("2003-08-22", "2003-09-05"))
        self.assertEqual(draft_rights.NEXT_DRAFT, "2004-06-24")
        self.assertEqual(window(1), (None, "2003-07-15"))
        self.assertEqual(window(2), ("2003-08-22", "2003-09-05"))
        agreement, rules = tender_rules(2003)
        self.assertEqual(agreement, "1999")
        self.assertEqual(rules["second_round"]["tender_by"]["source_ref"], "Art. X §3(b)")

    def test_2003_and_2004_drafts_follow_1999_and_2005_follows_the_2005_agreement(self):
        self.assertEqual([agreement_for(y) for y in (2003, 2004, 2005, 2006)], ["1999", "1999", "2005", "2005"])
        self.assertEqual(window(1, 2004), (None, "2004-07-15"))
        self.assertEqual(window(2, 2004), ("2004-08-22", "2004-09-05"))
        self.assertEqual(window(1, 2005), (None, "2005-07-15"))
        self.assertEqual(window(2, 2005), ("2005-08-22", "2005-09-05"))
        _, rules = tender_rules(2005)
        # Deadlines sourced from the 2005 FAQ (Q102); the window's start is the 1999 rule kept as a documented assumption.
        self.assertEqual((rules["first_round"]["tender_by"]["source_ref"], rules["second_round"]["tender_by"]["source_ref"]), ("Q102", "Q102"))
        self.assertEqual(rules["second_round"]["window_from"]["status"], "unverified")
        self.assertIn("assumption", rules["second_round"]["window_from"]["note"])
        self.assertEqual(rules["rights_until"]["source_ref"], "Q43")

    def test_draft_dates_come_from_the_calendars(self):
        self.assertEqual(draft_date(2004), "2004-06-24")      # 2004 offseason calendar
        self.assertEqual(draft_date(2005), "2005-06-28")      # 2005 offseason calendar
        self.assertEqual(draft_date(2006), "2006-06-28")      # 2005-06 league calendar, draft_2006


class Draft2003Tests(unittest.TestCase):
    CHECKPOINT = ROOT / "tests/fixtures/checkpoint_2003-06-26"

    def test_the_archived_2003_records_validate_as_before(self):
        self.assertEqual(season_errors("2003-04", ROOT), [])
        self.assertEqual(draft_rights_errors(ROOT, through="2003-04"), [])

    def test_the_real_2003_tenders_hold_the_checkpoint_picks(self):
        """The June 26, 2003 register (Wade and Beasley unsigned) against the real 2003-04 tender file, on a day both
        windows have closed: the data-driven windows accept the two recorded tenders, and refuse the picks without them."""
        season = PLAYER / "2003-04"
        with tempfile.TemporaryDirectory() as tmp:
            for rel in ("current_state.json", "00_Team/Team/Roster/roster.json", "00_Team/Finances/contract_schedules.json"):
                (Path(tmp) / season / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(self.CHECKPOINT / season / rel, Path(tmp) / season / rel)
            held = [p["name"] for p in json.loads((Path(tmp) / season / "00_Team/Team/Roster/roster.json").read_text())["players"]
                    if p["status"] in draft_rights.HELD]
            self.assertEqual(held, ["Dwyane Wade", "Jerome Beasley"])
            book = Path(tmp) / season / "00_Team/Transactions/required_tenders.json"
            book.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / draft_rights.TENDERS, book)
            self.assertEqual(season_errors("2003-04", tmp, today="2003-11-01"), [])
            book.unlink()
            errors = season_errors("2003-04", tmp, today="2003-11-01")
            self.assertEqual(len(errors), 2)
            self.assertIn("Dwyane Wade: unsigned draft rights without a Required Tender", errors[0])
            self.assertIn("his window closed 2003-07-15", errors[0])
            # Only his tender recorded Beasley's round: without it the earlier, first-round deadline applies.
            self.assertIn("Jerome Beasley: unsigned draft rights without a Required Tender", errors[1])
            self.assertIn("round not recorded pick of the 2003 draft (2003-04 register); his window closed 2003-07-15", errors[1])

    def test_2003_scenarios_keep_their_errors(self):
        tenders = [{"player": "Dwyane Wade", "pick": 5, "round": 1, "date": "2003-07-15"},
                   {"player": "Jerome Beasley", "pick": 33, "round": 2, "date": "2003-09-05"}]
        players = [pick("Dwyane Wade", "unsigned_first_round_draft_rights"), pick("Jerome Beasley", "draft_rights_unsigned")]
        with tempfile.TemporaryDirectory() as tmp:
            scaffold(tmp, "2003-04", "2003-06-26", players)
            self.assertEqual(season_errors("2003-04", tmp), [])   # the draft-day checkpoint: no tender yet, no error
            scaffold(tmp, "2003-04", "2003-11-01", players, tenders)
            self.assertEqual(season_errors("2003-04", tmp), [])
            late = [tenders[0], dict(tenders[1], date="2003-08-01")]
            scaffold(tmp, "2003-04", "2003-11-01", players, late)
            self.assertEqual(season_errors("2003-04", tmp),
                             ["Jerome Beasley: Required Tender dated 2003-08-01 is outside its window (2003-08-22 to 2003-09-05)"])
            scaffold(tmp, "2003-04", "2004-06-24", players[1:], tenders)
            self.assertEqual(season_errors("2003-04", tmp),
                             ["Jerome Beasley: exclusive rights ended at the 2004-06-24 draft; he cannot stay on the register unsigned"])
            scaffold(tmp, "2003-04", "2003-11-01", players, [])
            errors = season_errors("2003-04", tmp)
            self.assertEqual(len(errors), 2)
            self.assertTrue(all("without a Required Tender (1999 CBA Art. X §3; required_tenders.json)" in e for e in errors))


class Draft2004Tests(unittest.TestCase):
    PICK = {"pick": 51, "round": 2, "player": "Bernard Robinson", "bbr_id": "robinbe01"}

    def season(self, tmp, today, tenders=None, summer_tenders=None):
        scaffold(tmp, "2003-04", "2004-10-01", [], summer_tenders, draft={2004: [self.PICK]})
        scaffold(tmp, "2004-05", today, [pick("Bernard Robinson", bbr_id="robinbe01")], tenders)

    def test_a_tender_inside_the_window_holds_the_rights(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.season(tmp, "2005-01-15", [{"player": "Bernard Robinson", "round": 2, "date": "2004-09-01"}])
            self.assertEqual(season_errors("2004-05", tmp), [])
            # A tender filed with the summer's (closed season's) records counts the same.
            self.season(tmp, "2005-01-15", None, [{"player": "Bernard Robinson", "round": 2, "date": "2004-09-05"}])
            self.assertEqual(season_errors("2004-05", tmp), [])
            self.assertEqual(draft_rights_errors(tmp, through="2004-05"), [])

    def test_a_tender_outside_the_window_or_for_the_wrong_round_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.season(tmp, "2005-01-15", [{"player": "Bernard Robinson", "round": 2, "date": "2004-09-10"}])
            self.assertEqual(season_errors("2004-05", tmp),
                             ["Bernard Robinson: Required Tender dated 2004-09-10 is outside its window (2004-08-22 to 2004-09-05)"])
            self.season(tmp, "2005-01-15", [{"player": "Bernard Robinson", "round": 2, "date": "2004-08-15"}])
            self.assertEqual(len(season_errors("2004-05", tmp)), 1)
            self.season(tmp, "2005-01-15", [{"player": "Bernard Robinson", "round": 1, "date": "2004-07-10"}])
            self.assertIn("recorded for round 1", season_errors("2004-05", tmp)[0])

    def test_no_tender_is_refused_once_the_window_closes(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.season(tmp, "2005-01-15")
            errors = season_errors("2004-05", tmp)
            self.assertEqual(len(errors), 1)
            self.assertIn("No. 51 round-2 pick of the 2004 draft", errors[0])
            self.assertIn("his window closed 2004-09-05", errors[0])
            self.assertEqual(season_errors("2004-05", tmp, today="2004-09-05"), [])   # the window is still open

    def test_a_first_round_pick_has_until_july_15_and_no_tender_before_the_draft(self):
        first = {"pick": 23, "round": 1, "player": "First Pick", "bbr_id": "firstpi01"}
        with tempfile.TemporaryDirectory() as tmp:
            scaffold(tmp, "2003-04", "2004-10-01", [], None, draft={2004: [first]})
            scaffold(tmp, "2004-05", "2004-11-01", [pick("First Pick", bbr_id="firstpi01")],
                     [{"player": "First Pick", "round": 1, "date": "2004-07-15"}])
            self.assertEqual(season_errors("2004-05", tmp), [])
            scaffold(tmp, "2004-05", "2004-11-01", [pick("First Pick", bbr_id="firstpi01")],
                     [{"player": "First Pick", "round": 1, "date": "2004-06-20"}])
            self.assertEqual(season_errors("2004-05", tmp),
                             ["First Pick: Required Tender dated 2004-06-20 is outside its window (draft to 2004-07-15)"])
            scaffold(tmp, "2004-05", "2004-11-01", [pick("First Pick", bbr_id="firstpi01")], [])
            self.assertEqual(season_errors("2004-05", tmp, today="2004-07-15"), [])
            self.assertIn("No. 23 round-1 pick of the 2004 draft", season_errors("2004-05", tmp, today="2004-07-16")[0])

    def test_rights_end_at_the_2005_draft(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.season(tmp, "2005-06-27", [{"player": "Bernard Robinson", "round": 2, "date": "2004-09-01"}])
            self.assertEqual(season_errors("2004-05", tmp), [])
            self.assertEqual(season_errors("2004-05", tmp, today="2005-06-28"),
                             ["Bernard Robinson: exclusive rights ended at the 2005-06-28 draft; he cannot stay on the register unsigned"])


class Draft2005Tests(unittest.TestCase):
    def season(self, tmp, today, tenders, round_=2):
        scaffold(tmp, "2004-05", "2005-10-01", [], None,
                 draft={2005: [{"pick": 40 if round_ == 2 else 20, "round": round_, "player": "Test Pick", "bbr_id": "testpi01"}]})
        scaffold(tmp, "2005-06", today, [pick("Test Pick", bbr_id="testpi01")], tenders)

    def test_a_2005_pick_is_checked_against_the_2005_agreement(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.season(tmp, "2005-11-01", [{"player": "Test Pick", "round": 2, "date": "2005-09-02"}])
            self.assertEqual(season_errors("2005-06", tmp), [])
            self.season(tmp, "2005-11-01", [{"player": "Test Pick", "round": 2, "date": "2005-09-06"}])
            self.assertEqual(season_errors("2005-06", tmp),
                             ["Test Pick: Required Tender dated 2005-09-06 is outside its window (2005-08-22 to 2005-09-05)"])
            self.season(tmp, "2005-11-01", [])
            self.assertIn("(2005 CBA, FAQ Q102; required_tenders.json)", season_errors("2005-06", tmp)[0])
            self.season(tmp, "2005-11-01", [{"player": "Test Pick", "round": 1, "date": "2005-07-16"}], round_=1)
            self.assertIn("outside its window (draft to 2005-07-15)", season_errors("2005-06", tmp)[0])

    def test_rights_end_at_the_2006_draft(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.season(tmp, "2006-06-27", [{"player": "Test Pick", "round": 2, "date": "2005-09-02"}])
            self.assertEqual(season_errors("2005-06", tmp), [])
            self.assertEqual(season_errors("2005-06", tmp, today="2006-06-28"),
                             ["Test Pick: exclusive rights ended at the 2006-06-28 draft; he cannot stay on the register unsigned"])

    def test_a_next_draft_the_library_lacks_is_an_error_not_a_guess(self):
        real = draft_rights.draft_date
        lacking = lambda year, root=draft_rights.ROOT: None if int(year) == 2006 else real(year, root)   # noqa: E731
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(draft_rights, "draft_date", side_effect=lacking):
            self.season(tmp, "2005-11-01", [{"player": "Test Pick", "round": 2, "date": "2005-09-02"}])
            self.assertEqual(season_errors("2005-06", tmp),
                             ["Test Pick: his rights end at the 2006 draft, whose date is not in the library "
                              "(library/2006/league/nba_2006_offseason_calendar.json `draft` or the 2005-06 calendar `draft_2006`)"])

    def test_another_drafts_tender_is_not_checked_against_this_window(self):
        """A player Miami tendered after an earlier draft and drafted again: the old tender neither satisfies nor fails
        the new draft's window."""
        with tempfile.TemporaryDirectory() as tmp:
            old = [{"player": "Test Pick", "bbr_id": "testpi01", "round": 2, "date": "2003-09-05"}]
            scaffold(tmp, "2003-04", "2004-10-01", [], old)
            self.season(tmp, "2005-08-01", [])
            self.assertEqual(season_errors("2005-06", tmp), [])          # his 2005 window is still open
            errors = season_errors("2005-06", tmp, today="2005-11-01")
            self.assertEqual(len(errors), 1)
            self.assertIn("without a Required Tender (2005 CBA, FAQ Q102; required_tenders.json): No. 40 round-2 pick of the 2005 draft", errors[0])


class RetainedRightsTests(unittest.TestCase):
    def test_a_recorded_non_nba_contract_is_checked_against_its_own_record(self):
        basis = {"rule": "non_nba_contract", "until": None, "source": "test: contract with a non-NBA club"}
        with tempfile.TemporaryDirectory() as tmp:
            scaffold(tmp, "2003-04", "2004-10-01", [], None, draft={2004: [{"pick": 54, "round": 2, "player": "Abroad Pick"}]})
            scaffold(tmp, "2004-05", "2005-07-01", [pick("Abroad Pick", draft_rights_retained=basis)], [])
            self.assertEqual(season_errors("2004-05", tmp), [])          # no tender, past the next draft: retained
            ended = dict(basis, until="2005-06-01")
            scaffold(tmp, "2004-05", "2005-07-01", [pick("Abroad Pick", draft_rights_retained=ended)], [])
            self.assertIn("ended on 2005-06-01", season_errors("2004-05", tmp)[0])
            scaffold(tmp, "2004-05", "2005-07-01", [pick("Abroad Pick", draft_rights_retained=dict(basis, rule="injury"))], [])
            self.assertIn("not one the agreement provides", season_errors("2004-05", tmp)[0])
            scaffold(tmp, "2004-05", "2005-07-01", [pick("Abroad Pick", draft_rights_retained=dict(basis, source=None))], [])
            self.assertEqual(season_errors("2004-05", tmp), ["Abroad Pick: draft_rights_retained has no source for the non_nba_contract basis"])
            scaffold(tmp, "2004-05", "2005-07-01", [pick("Abroad Pick", draft_rights_retained=True)], [])
            self.assertIn("must be a record", season_errors("2004-05", tmp)[0])

    def test_a_status_marking_him_abroad_needs_its_record(self):
        basis = {"rule": "non_nba_contract", "until": None, "source": "test: contract with a non-NBA club"}
        with tempfile.TemporaryDirectory() as tmp:
            scaffold(tmp, "2003-04", "2004-10-01", [], None, draft={2004: [{"pick": 54, "round": 2, "player": "Abroad Pick"}]})
            scaffold(tmp, "2004-05", "2005-07-01", [pick("Abroad Pick", "unsigned_draft_rights_abroad")], [])
            errors = season_errors("2004-05", tmp)
            # The mark alone is refused, and he is checked like any other pick: no tender, and past the 2005 draft.
            self.assertEqual(len(errors), 3)
            self.assertIn("marks him abroad, but no draft_rights_retained record", errors[0])
            self.assertIn("without a Required Tender", errors[1])
            self.assertIn("exclusive rights ended at the 2005-06-28 draft", errors[2])
            self.assertIsNone(draft_rights.retained_basis(pick("Abroad Pick", "unsigned_draft_rights_abroad")))
            scaffold(tmp, "2004-05", "2005-07-01", [pick("Abroad Pick", "unsigned_draft_rights_abroad", draft_rights_retained=basis)], [])
            self.assertEqual(season_errors("2004-05", tmp), [])          # the mark with its sourced record: held while abroad


class StatusTests(unittest.TestCase):
    def test_held_rights_are_an_explicit_set_and_an_ended_status_is_not_held(self):
        with tempfile.TemporaryDirectory() as tmp:
            scaffold(tmp, "2003-04", "2004-10-01", [], None, draft={2004: [{"pick": 51, "round": 2, "player": "Some Pick"}]})
            for status in (draft_rights.ENDED, "draft_rights_expired", "renounced", "released", "under_contract"):
                scaffold(tmp, "2004-05", "2005-07-01", [pick("Some Pick", status)], [])
                self.assertEqual(season_errors("2004-05", tmp), [], status)
            scaffold(tmp, "2004-05", "2005-07-01", [pick("Some Pick", "draft_rights_pending")], [])
            self.assertEqual(season_errors("2004-05", tmp),
                             ["Some Pick: register status 'draft_rights_pending' is not a known draft-rights status (held: "
                              + ", ".join(draft_rights.HELD) + "; ended: one naming released, renounced, expired, ended, lapsed)"])


def market(root, year, to, events=(), miami=()):
    """A closed summer market record in its season's 10_Free_Agency folder."""
    write(root, PLAYER / f"{year - 1}-{str(year)[-2:]}" / f"10_Free_Agency/free_agency_{year}.json",
          {"kind": "summer_market", "from": f"{year}-06-30", "to": to, "events": list(events),
           "clubs": {"Miami Heat": list(miami)}})


class WriterTests(unittest.TestCase):
    PICKS = [{"pick": 23, "round": 1, "player": "First Pick", "bbr_id": "firstpi01"},
             {"pick": 51, "round": 2, "player": "Bernard Robinson", "bbr_id": "robinbe01"},
             {"pick": 54, "round": 2, "player": "Late Signer", "bbr_id": "latesi01"},
             {"pick": 55, "round": 2, "player": "Early Signer", "bbr_id": "earlysi01"}]
    EVENTS = [{"date": "2004-07-01", "kind": "rookie_scale_signing", "player": "First Pick", "bbr_id": "firstpi01", "club": "Miami Heat"},
              {"date": "2004-09-20", "kind": "signing", "player": "Late Signer", "bbr_id": "latesi01", "club": "Miami Heat"},
              {"date": "2004-08-01", "kind": "signing", "player": "Early Signer", "bbr_id": "earlysi01", "club": "Miami Heat"}]

    def test_tenders_are_entered_on_their_deadlines_from_the_closed_market(self):
        with tempfile.TemporaryDirectory() as tmp:
            scaffold(tmp, "2003-04", "2004-09-30", [], None, draft={2004: self.PICKS})
            self.assertEqual(record_tenders(tmp, 2004, "2004-09-30"), [])          # no market record yet
            market(tmp, 2004, "2004-09-30", self.EVENTS)
            filed = record_tenders(tmp, 2004, "2004-09-30")
            # First Pick and Early Signer signed by their deadlines; Robinson never did, Late Signer only after September 5.
            self.assertEqual([(t["player"], t["round"], t["date"]) for t in filed],
                             [("Bernard Robinson", 2, "2004-09-05"), ("Late Signer", 2, "2004-09-05")])
            self.assertTrue(all(t["reconstructed"] and t["recorded"] == "2004-09-30" and t["draft_year"] == 2004 for t in filed))
            self.assertEqual(filed[0]["terms"], "one season at the Minimum Annual Salary")
            book = json.loads((Path(tmp) / PLAYER / "2003-04/00_Team/Transactions/required_tenders.json").read_text())
            self.assertEqual(book["kind"], "required_tenders")
            self.assertEqual(len(book["tenders"]), 2)
            self.assertEqual(record_tenders(tmp, 2004, "2004-10-01"), [])          # a rerun writes nothing

    def test_rights_end_at_the_next_draft_on_the_live_register(self):
        with tempfile.TemporaryDirectory() as tmp:
            scaffold(tmp, "2003-04", "2004-10-01", [], [{"player": "Bernard Robinson", "bbr_id": "robinbe01", "round": 2, "date": "2004-09-05"}],
                     draft={2004: self.PICKS[1:2]})
            scaffold(tmp, "2004-05", "2005-06-27", [pick("Bernard Robinson", bbr_id="robinbe01"),
                                                     pick("Kept Abroad", bbr_id="keptab01", draft_rights_retained={
                                                         "rule": "non_nba_contract", "until": None, "source": "test record"})], [])
            team = PLAYER / "2004-05/00_Team"
            write(tmp, team / "Team/Roster/holdings.json", {"entries": [
                {"player": "Bernard Robinson", "bbr_id": "robinbe01", "from": "2004-06-24", "until": None, "basis": "draft rights (No. 51 pick), unsigned"}]})
            write(tmp, team / "Finances/contract_schedules.json", {"players": [
                {"player": "Bernard Robinson", "bbr_id": "robinbe01", "status": "unsigned_draft_rights", "schedule": {}, "draft_pick": 51, "draft_round": 2}]})
            write(tmp, team / "Team/Depth_Chart/depth_chart.json", {"positions": {}, "unassigned_draft_rights": [
                {"name": "Bernard Robinson", "positions": ["SG"], "status": "draft_rights_unsigned"}]})
            self.assertEqual(end_rights(tmp, "2005-06-27"), [])                        # the day before the 2005 draft
            self.assertEqual(season_errors("2004-05", tmp, today="2005-06-28"),
                             ["Bernard Robinson: exclusive rights ended at the 2005-06-28 draft; he cannot stay on the register unsigned"])
            ended = end_rights(tmp, "2005-06-28")
            self.assertEqual([(e["player"], e["date"], e["draft_year"], e["pick"]) for e in ended], [("Bernard Robinson", "2005-06-28", 2004, 51)])
            read = lambda rel: json.loads((Path(tmp) / team / rel).read_text())     # noqa: E731
            robinson = read("Team/Roster/roster.json")["players"][0]
            self.assertEqual(robinson["status"], draft_rights.ENDED)
            self.assertIn("June 28, 2005: Miami's exclusive rights ended unsigned at the 2005 draft (1999 CBA Art. X §3(a); 1999 FAQ Q40)", robinson["control"])
            self.assertEqual(read("Team/Roster/roster.json")["players"][1]["status"], "unsigned_draft_rights")   # retained: kept
            self.assertEqual(read("Team/Roster/holdings.json")["entries"][0]["until"], "2005-06-28")
            self.assertEqual(read("Finances/contract_schedules.json")["players"][0]["status"], draft_rights.ENDED)
            depth = read("Team/Depth_Chart/depth_chart.json")
            self.assertEqual((depth["unassigned_draft_rights"], depth["departed"][0]["name"]), ([], "Bernard Robinson"))
            self.assertEqual(read("Transactions/required_tenders.json")["rights_ended"][0]["date"], "2005-06-28")
            self.assertEqual(season_errors("2004-05", tmp, today="2005-10-01"), [])  # the archived register stays valid
            self.assertEqual(end_rights(tmp, "2005-06-29"), [])                        # a rerun writes nothing

    def test_a_retained_basis_ends_on_its_own_date(self):
        basis = {"rule": "non_nba_contract", "until": "2006-07-01", "source": "test record"}
        with tempfile.TemporaryDirectory() as tmp:
            scaffold(tmp, "2003-04", "2004-10-01", [], None, draft={2004: [{"pick": 54, "round": 2, "player": "Abroad Pick"}]})
            scaffold(tmp, "2004-05", "2005-07-01", [pick("Abroad Pick", draft_rights_retained=basis)], [])
            self.assertEqual(end_rights(tmp, "2005-07-01", season="2004-05"), [])
            ended = end_rights(tmp, "2006-07-01", season="2004-05")
            self.assertEqual([(e["player"], e["date"]) for e in ended], [("Abroad Pick", "2006-07-01")])
            self.assertIn("retained under the non_nba_contract rule ended (test record; 1999 FAQ Q40", ended[0]["basis"])

    def test_a_pick_carried_by_the_rollover_arrives_with_his_tender_and_leaves_at_the_next_draft(self):
        """The 2005 summer through the real rollover code: the market closes with a second-round pick unsigned, the
        writer enters his tender, `Rollover` carries him onto the 2005-06 register, and the 2006 draft ends his rights,
        with no record edited by hand."""
        from runtime.rollover import Rollover
        picks = [{"pick": 20, "round": 1, "player": "Signed First", "bbr_id": "signefi01"},
                 {"pick": 40, "round": 2, "player": "Test Pick", "bbr_id": "testpi01"}]
        with tempfile.TemporaryDirectory() as tmp, live_season():
            for name in ("nba_2005_offseason_calendar.json", "nba_2005_prospect_evidence.json"):    # draft.year_context reads them
                (Path(tmp) / "library/2005/league").mkdir(parents=True, exist_ok=True)
                shutil.copy(ROOT / "library/2005/league" / name, Path(tmp) / "library/2005/league" / name)
            scaffold(tmp, "2004-05", "2005-09-30", [], None, draft={2005: picks})
            write(tmp, PLAYER / "2004-05/00_Team/Finances/contract_schedules.json", {"players": []})
            write(tmp, PLAYER / "2004-05/00_Team/Team/Roster/holdings.json", {"entries": []})
            market(tmp, 2005, "2005-09-30",
                   [{"date": "2005-07-01", "kind": "rookie_scale_signing", "player": "Signed First", "bbr_id": "signefi01", "club": "Miami Heat"}],
                   [{"player": "Signed First", "bbr_id": "signefi01", "salary": 1000000, "years": 2, "route": "rookie_scale"}])
            self.assertEqual([t["player"] for t in record_tenders(tmp, 2005, "2005-09-30")], ["Test Pick"])
            rollover = Rollover(tmp)
            self.assertEqual((rollover.old, rollover.new), ("2004-05", "2005-06"))
            with mock.patch.object(Rollover, "miami", return_value=[]):         # the market left no contract with Miami
                entries = rollover.contract_entries({})
            register = rollover.register(entries, {})
            holdings, _ = rollover.holdings(entries)
            self.assertEqual([(p["name"], p["status"]) for p in register["players"]], [("Test Pick", "unsigned_draft_rights")])
            team = PLAYER / "2005-06/00_Team"
            write(tmp, team / "Team/Roster/roster.json", register)
            write(tmp, team / "Team/Roster/holdings.json", holdings)
            write(tmp, team / "Finances/contract_schedules.json", {"players": entries})
            write(tmp, PLAYER / "2005-06/current_state.json", {"season": "2005-06", "current_date": rollover.day})
            self.assertEqual(draft_rights_errors(tmp), [])
            # Without the writer's tender the carried pick would be refused on arrival.
            book = Path(tmp) / PLAYER / "2004-05/00_Team/Transactions/required_tenders.json"
            saved = book.read_text()
            book.unlink()
            self.assertIn("window closed 2005-09-05", draft_rights_errors(tmp)[0])
            book.write_text(saved)
            write(tmp, PLAYER / "2005-06/current_state.json", {"season": "2005-06", "current_date": "2006-06-28"})
            self.assertIn("exclusive rights ended at the 2006-06-28 draft", draft_rights_errors(tmp)[0])
            ended = end_rights(tmp, "2006-06-28")
            self.assertEqual([e["player"] for e in ended], ["Test Pick"])
            self.assertIn("ended unsigned at the 2006 draft (2005 FAQ Q43)", ended[0]["basis"])     # the 2005 agreement's pick
            self.assertEqual(draft_rights_errors(tmp), [])
            self.assertEqual(json.loads((Path(tmp) / team / "Team/Roster/holdings.json").read_text())["entries"][0]["until"], "2006-06-28")


class LiveRecordsTests(unittest.TestCase):
    def test_the_live_registers_have_their_tenders(self):
        """The repository's own registers, every season through the live one, as validation reads them."""
        with live_season():
            self.assertEqual(draft_rights_errors(ROOT), [])


if __name__ == "__main__":
    unittest.main()
