"""Final audit fix 2 (the 2006-06-20 integration review, summer role): R1, a Miami draft pick without an NBA id through
the rollover and the draft-rights records; R4, the driver stops on the rollover day when the next season cannot open.

R1: 21 of the 2006 class's 88 prospects have no NBA id, clustered around Miami's No. 58 pick. The rollover keyed every
entry by `bbr_id or WADE_ID`, so such a pick became a second "Dwyane Wade" row and was lost (no holding, no card, the
draft-rights check refusing "Dwyane Wade"). He is keyed by his name now (`rollover.entry_key`), never written with a
name as his bbr_id. The stand-in pick is Curtis Stinson, the scratch draft's modal choice at No. 58, written exactly as
`runtime/draft.py` writes a pick (bbr_id None, position "G")."""
import contextlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

from runtime import draft_rights, rollover as R
from runtime.free_agency_2004 import record_for
from runtime.rollover import Rollover, WADE_ID, entry_key
import scripts.advance as A
from tests import live_season

ROOT = Path(__file__).resolve().parents[1]
PLAYER = Path("career/Dwyane_Wade")
MIAMI = "Miami Heat"
PICK = {"pick": 58, "round": 2, "club": MIAMI, "player": "Curtis Stinson", "bbr_id": None, "position": "G"}
OTHER = {"pick": 57, "round": 2, "club": "Detroit Pistons", "player": "Gerry McNamara", "bbr_id": None, "position": "PG"}


def _put(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")


def stand_in_market(old_team):
    """A closed 2006 market record that leaves Miami every contract running into 2006-07 (in memory)."""
    sheet = json.loads((old_team / "Finances/contract_schedules.json").read_text(encoding="utf-8"))
    rows = [{"bbr_id": p.get("bbr_id") or WADE_ID, "player": p["player"], "route": "existing", "salary": p["schedule"]["2006-07"]}
            for p in sheet["players"] if (p.get("schedule") or {}).get("2006-07")
            and p.get("status") in ("under_contract", "under_rookie_contract")]
    return {"events": [], "clubs": {MIAMI: rows}, "from": "2006-07-01", "to": "2006-09-30", "unsigned_pool": [],
            "left_the_league": []}


def summer_2006(tmp, picks=(PICK, OTHER)):
    """The 2005-06 to 2006-07 rollover over the repository's 2005-06 records, with a stand-in draft record (in `tmp`)
    and market record: nothing in the repository is read for the summer or written."""
    with live_season():
        ro = Rollover(ROOT)
    ro.old, ro.new, ro.year, ro.day = "2005-06", "2006-07", 2006, "2006-10-01"
    ro.old_dir = tmp / "old"
    ro.old_team = ROOT / PLAYER / "2005-06/00_Team"
    ro.new_dir = tmp / "new"
    ro.team = ro.new_dir / "00_Team"
    ro.record_path = ROOT / record_for("2006-07")
    _put(ro.old_dir / "09_Draft/draft_2006.json", {"date": "2006-06-28", "picks": list(picks), "trades": []})
    ro.record = stand_in_market(ro.old_team)
    return ro


class IdlessPickRolloverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.ro = summer_2006(cls.tmp)
        cls.ids = cls.ro.identities()
        cls.entries = cls.ro.contract_entries({})
        cls.register = cls.ro.register(cls.entries, cls.ids)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_the_key_never_takes_a_pick_for_wade(self):
        self.assertEqual(entry_key({"player": "Dwyane Wade", "bbr_id": None}), WADE_ID)
        self.assertEqual(entry_key({"player": "Curtis Stinson", "bbr_id": None}), "curtis_stinson")
        self.assertEqual(entry_key({"player": "Uroš Slokar", "bbr_id": "slokaur01"}), "slokaur01")

    def test_his_identity_comes_from_the_draft_record_and_the_prospect_evidence(self):
        ident = self.ids["curtis_stinson"]
        self.assertEqual((ident["name"], ident["position"], ident["birth_date"], ident["draft_pick"], ident["draft_round"]),
                         ("Curtis Stinson", "G", "1983-02-15", 58, 2))
        self.assertNotIn("gerry_mcnamara", self.ids)            # another club's id-less pick is not Miami's identity

    def test_the_register_holds_wade_once_and_the_pick_by_name(self):
        rows = self.register["players"]
        self.assertEqual([p["id"] for p in rows if p["name"] == "Dwyane Wade"], [WADE_ID])
        wade = next(p for p in rows if p["name"] == "Dwyane Wade")
        self.assertEqual(wade["status"], "under_contract")
        pick = next(p for p in rows if p["name"] == "Curtis Stinson")
        self.assertEqual((pick["id"], pick["positions"], pick["date_of_birth"], pick["status"], pick["control"]),
                         ("curtis_stinson", ["G"], "1983-02-15", "unsigned_draft_rights",
                          "Unsigned draft rights: No. 58 pick of the 2006 draft."))
        self.assertNotIn("bbr_id", pick)                        # a name key is never written as an NBA id
        self.assertEqual(len({p["id"] for p in rows}), len(rows))

    def test_the_depth_chart_names_the_pick(self):
        dc = self.ro.depth_chart(self.register)
        self.assertEqual(dc["unassigned_draft_rights"], [{"name": "Curtis Stinson", "positions": ["G"], "status": "draft_rights_unsigned"}])

    def test_miami_holds_his_rights_by_name_from_draft_night(self):
        new, _ = self.ro.holdings(self.entries)
        mine = [h for h in new["entries"] if h["player"] == "Curtis Stinson"]
        self.assertEqual(mine, [{"player": "Curtis Stinson", "bbr_id": None, "from": "2006-06-28", "until": None,
                                 "basis": "draft rights (No. 58 pick), unsigned"}])
        self.assertEqual(len([h for h in new["entries"] if h["player"] == "Dwyane Wade"]), 1)

    def test_his_card_is_his_own(self):
        self.ro.write_cards(self.entries, self.register, self.ids, {})
        cards = self.ro.team / "Team/Player_Cards"
        text = (cards / "curtis_stinson.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("# Curtis Stinson | 2006-07 Player Profile"))
        self.assertIn("**Position:** G", text)
        self.assertIn("Unsigned draft rights: No. 58 pick of the 2006 draft.", text)
        self.assertIn("# Dwyane Wade | 2006-07 Player Profile", (cards / "dwyane_wade.md").read_text(encoding="utf-8"))
        self.assertEqual(len(list(cards.glob("*.md"))), len(self.register["players"]))

    def test_a_pick_the_market_never_saw_stays_unsigned(self):
        # a stray row without an id in the record is not him: he never entered the market (draft.drafted_clubs)
        self.ro.record["clubs"]["Detroit Pistons"] = [{"bbr_id": None, "player": "someone", "route": "minimum", "salary": 1}]
        try:
            self.assertEqual([p["player"] for p in self.ro.unsigned_picks()], ["Curtis Stinson"])
        finally:
            del self.ro.record["clubs"]["Detroit Pistons"]


class IdlessPickDraftRightsTests(unittest.TestCase):
    """The rights records hold him by name: the routine Required Tender, the season check at the rollover, the end of his
    rights at the next draft (holding, sheet row and depth chart closed by name)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        ro = summer_2006(self.tmp / "scratch")
        ids, entries = ro.identities(), ro.contract_entries({})
        register = ro.register(entries, ids)
        root, base = self.tmp / "root", self.tmp / "root" / PLAYER
        _put(base / "2005-06/current_state.json", {"season": "2005-06", "current_date": "2006-10-01"})
        _put(base / "2005-06/09_Draft/draft_2006.json", {"date": "2006-06-28", "picks": [PICK, OTHER], "trades": []})
        _put(base / "2005-06/10_Free_Agency/free_agency_2006.json", ro.record)
        _put(base / "2006-07/current_state.json", {"season": "2006-07", "current_date": "2006-10-01"})
        _put(base / "2006-07/00_Team/Team/Roster/roster.json", register)
        _put(base / "2006-07/00_Team/Finances/contract_schedules.json", {"players": entries})
        _put(base / "2006-07/00_Team/Team/Roster/holdings.json", ro.holdings(entries)[0])
        _put(base / "2006-07/00_Team/Team/Depth_Chart/depth_chart.json", ro.depth_chart(register))
        # the 2007 draft's date: the 2006-07 calendar is not in the library yet (roadmap 18)
        _put(root / "library/2007/league/nba_2007_offseason_calendar.json", {"draft": "2007-06-28"})
        self.root = root

    def test_his_tender_and_the_season_check_accept_him(self):
        tenders = draft_rights.record_tenders(self.root, 2006, day="2006-09-30")
        self.assertEqual([(t["player"], t["bbr_id"], t["round"], t["pick"]) for t in tenders], [("Curtis Stinson", None, 2, 58)])
        self.assertEqual(draft_rights.season_errors("2006-07", self.root, today="2006-10-01"), [])
        later = draft_rights.season_errors("2006-07", self.root, today="2007-06-28")
        self.assertEqual(later, ["Curtis Stinson: exclusive rights ended at the 2007-06-28 draft; he cannot stay on the register unsigned"])

    def test_his_rights_end_by_name_at_the_next_draft(self):
        draft_rights.record_tenders(self.root, 2006, day="2006-09-30")
        ended = draft_rights.end_rights(self.root, day="2007-06-28", season="2006-07")
        self.assertEqual([(e["player"], e["date"]) for e in ended], [("Curtis Stinson", "2007-06-28")])
        team = self.root / PLAYER / "2006-07/00_Team"
        holding = next(h for h in json.loads((team / "Team/Roster/holdings.json").read_text())["entries"] if h["player"] == "Curtis Stinson")
        self.assertEqual(holding["until"], "2007-06-28")
        wade = next(h for h in json.loads((team / "Team/Roster/holdings.json").read_text())["entries"] if h["player"] == "Dwyane Wade")
        self.assertIsNone(wade["until"])                         # Wade's holding (no NBA id either) is not his
        sheet = {p["player"]: p["status"] for p in json.loads((team / "Finances/contract_schedules.json").read_text())["players"]}
        self.assertEqual((sheet["Curtis Stinson"], sheet["Dwyane Wade"]), (draft_rights.ENDED, "under_contract"))
        depth = json.loads((team / "Team/Depth_Chart/depth_chart.json").read_text())
        self.assertEqual(depth["unassigned_draft_rights"], [])
        self.assertEqual(draft_rights.season_errors("2006-07", self.root, today="2007-06-28"), [])


class DraftNightTests(unittest.TestCase):
    def test_draft_night_reports_him_and_the_market_never_lists_him(self):
        from runtime import draft
        from scripts.offseason_day import draft_news
        self.assertEqual(draft_news({"picks": [PICK, OTHER], "trades": []}, 2006),
                         ["MIAMI DRAFT: Miami selects Curtis Stinson (G) at No. 58"])
        with tempfile.TemporaryDirectory() as tmp, draft.year_context(2006, ROOT):
            _put(Path(tmp) / draft.RECORD, {"picks": [PICK, OTHER]})
            self.assertEqual(draft.drafted_clubs(tmp), {})        # the market covers picks with an NBA id only


class RolloverDayTests(unittest.TestCase):
    """R4: `scripts/advance.rollover_day` waits (False) only while the summer market runs or before the rollover's date;
    from that date, with the market's record written, every blocker left stops the run."""

    class Fake:
        def __init__(self, record, blockers):
            self.record, self._blockers = record, blockers
            self.old, self.new, self.day = "2005-06", "2006-07", "2006-10-01"

        def blockers(self, day):
            return list(self._blockers) + ([f"the rollover is dated {self.day}; the clock is {day}"] if day < self.day else [])

    DATA = ["2006-07 data missing: library/2006/league/nba_2006_07_calendar.json",
            "2006-07 data missing: runtime/era.py SEASON_RULES row for 2006-07"]

    def call(self, day, record, blockers):
        with mock.patch.object(R, "Rollover", lambda root: self.Fake(record, blockers)), \
                mock.patch.object(A, "run", return_value="rolled over") as run, \
                contextlib.redirect_stdout(io.StringIO()):
            return A.rollover_day(day), run

    def test_the_summer_waits_while_the_market_runs_or_before_the_date(self):
        open_market = ["the summer market has not closed (career/Dwyane_Wade/2005-06/10_Free_Agency/free_agency_2006.json)"]
        self.assertFalse(self.call("2006-10-05", None, open_market + self.DATA)[0])
        self.assertFalse(self.call("2006-09-30", {"events": []}, self.DATA)[0])

    def test_the_rollover_day_stops_with_every_blocker(self):
        with self.assertRaises(A.Stop) as stop:
            self.call("2006-10-01", {"events": []}, self.DATA)
        self.assertIn("rollover is due on 2006-10-01", str(stop.exception))
        for b in self.DATA:
            self.assertIn(b, str(stop.exception))
        with self.assertRaises(A.Stop):
            self.call("2006-10-12", {"events": []}, self.DATA)      # a later day stops the same way

    def test_a_clear_rollover_day_rolls_over(self):
        done, run = self.call("2006-10-01", {"events": []}, [])
        self.assertTrue(done)
        run.assert_called_once_with("scripts/rollover.py", "--write", show=False)

    def test_the_repository_rollover_with_a_stand_in_record(self):
        """The real blockers of the repository's next rollover, once a stand-in market record exists: on its date the
        driver stops and names each of them (the next season's library data among them while it is missing)."""
        from runtime.extensions import ExtensionError
        with live_season():
            ro = Rollover(ROOT)
            if ro.record is not None:
                self.skipTest("the next rollover's market record exists: no stand-in is needed")
            stand_in = {"events": [], "clubs": {MIAMI: []}, "to": f"{ro.year}-09-30", "unsigned_pool": []}
            ro.record = stand_in
            try:
                expected = ro.blockers(ro.day)
            except ExtensionError as e:                          # only an extension is left: the same stop
                expected = [str(e)]
        if not expected:
            self.skipTest("the next rollover has no blocker left: the driver would run it")
        real_init = Rollover.__init__

        def init(this, root=ROOT):
            real_init(this, root)
            this.record = stand_in
        with live_season(), mock.patch.object(Rollover, "__init__", init), mock.patch.object(A, "run") as run, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertFalse(A.rollover_day(f"{ro.year}-09-30"))     # the day before: still the summer
            with self.assertRaises(A.Stop) as stop:
                A.rollover_day(ro.day)
            run.assert_not_called()
        for b in expected:
            self.assertIn(b, str(stop.exception))


if __name__ == "__main__":
    unittest.main()
