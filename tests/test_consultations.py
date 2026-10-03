"""The franchise consultation gate (runtime/consultations.py): the rule, the free-agency plan and the trade proposal.

The driver flows run with the rule's computation patched to `franchise` (so the drivers and the replay
agree) and the star line lowered: the 2003 market gives no star a franchise-standing Miami could reach,
so `STAR_PRODUCTION_VALUE` is patched down for the flow tests only; the real line is tested directly.
"""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from runtime import consultations, signing, standing
from runtime.negotiation import slug
from runtime.private_service import Store
from runtime.signing import trade_record_errors
from scripts import run_trade
from scripts.run_free_agency import Run, local_draw

ROOT = Path(__file__).resolve().parents[1]
SEASON = "2003-04"
SEASON_DIR = Path(f"career/Dwyane_Wade/{SEASON}")
FRANCHISE = {"standing": "franchise", "as_of": None, "basis": {"honors": [], "closed_seasons": [], "rule": "test fixture: the rule is patched"}}
LOWERED_STAR_LINE = 12.0


def copy_repo():
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    shutil.copytree(ROOT / "library", root / "library")
    shutil.copytree(ROOT / "career", root / "career")
    return tmp, root


def franchise_patches():
    return (mock.patch("runtime.standing.compute", return_value=dict(FRANCHISE)),
            mock.patch.object(consultations, "STAR_PRODUCTION_VALUE", LOWERED_STAR_LINE))


def answer(root, record, value, day):
    path = consultations.folder(root, SEASON) / f"{record['id']}.json"
    data = json.loads(path.read_text())
    data.update(answer=value, answered=day, status="closed", note="test answer")
    path.write_text(json.dumps(data, indent=1) + "\n")


class RuleTests(unittest.TestCase):
    def test_consultation_required(self):
        self.assertTrue(consultations.consultation_required("franchise", 20.0))
        self.assertFalse(consultations.consultation_required("franchise", 19.9))
        self.assertFalse(consultations.consultation_required("franchise", None))       # no 2002-03 evidence: never a star
        self.assertFalse(consultations.consultation_required("all_star", 28.5))
        self.assertEqual(consultations.STAR_PRODUCTION_VALUE, 20.0)
        self.assertEqual(consultations.KINDS, ("free_agent", "trade", "sign_and_trade"))
        self.assertEqual(consultations.consultation_id("2004-02-10", "trade", "Kevin Garnett"), "2004-02-10-kevin_garnett-trade")
        with self.assertRaises(ValueError):
            consultations.ask(ROOT, {}, "2004-02-10", "re_sign", "X", None, None, basis="", evidence={})

    def test_no_records_means_no_answers(self):
        tmp, root = copy_repo()
        self.addCleanup(tmp.cleanup)
        self.assertIsNone(consultations.answer_of(root, SEASON, "Kevin Garnett", "2004-02-10"))
        self.assertFalse(consultations.objected(root, SEASON, "Kevin Garnett", "2004-02-10"))
        self.assertEqual(consultations.consultation_errors(root), [])


class FreeAgencyGateTests(unittest.TestCase):
    def test_plan_asks_wade_and_stops_the_day(self):
        tmp, root = copy_repo()
        self.addCleanup(tmp.cleanup)
        store = Store(root / "data/e.sqlite3")
        store.initialize()
        patches = franchise_patches()
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        standing.record(root, "2003-06-26", "manual")
        self.assertEqual(standing.standing_on(root, "2003-07-01")["standing"], "franchise")
        report = Run(root).advance("2003-07-01")
        self.assertIn("June 30", report["stopped"])
        local_draw(store, root)
        report = Run(root).advance("2003-07-01")
        self.assertIn("awaiting Wade's answer on", report["stopped"], report)
        self.assertEqual(report["date"], "2003-07-01")
        records = consultations.records(root, SEASON)
        self.assertTrue(records)
        folder = consultations.folder(root, SEASON)
        state = json.loads((root / SEASON_DIR / "current_state.json").read_text())
        negotiations = root / SEASON_DIR / "01_Free_Agency/Negotiations"
        plan = json.loads((root / SEASON_DIR / "01_Free_Agency/Plans/plan_2003-07-01.json").read_text())
        self.assertEqual(plan["standing"]["standing"], "franchise")
        asked = {t["player"] for t in plan["targets"] if t.get("consultation") == "asked"}
        self.assertEqual(asked, {r["player"] for r in records})
        for r in records:
            self.assertIn(r["kind"], ("free_agent", "sign_and_trade"))
            self.assertEqual((r["status"], r["answer"], r["answered"]), ("asked", None, None))
            self.assertEqual(r["standing"]["standing"], "franchise")
            self.assertGreaterEqual(r["star_basis"]["value"], LOWERED_STAR_LINE)
            self.assertTrue((folder / consultations.page_name(r)).exists())
            self.assertIn("Awaiting your response", (folder / consultations.page_name(r)).read_text())
            self.assertIn(consultations.PENDING_PREFIX + r["id"], state["pending_player_decisions"])
            self.assertFalse((negotiations / f"{slug(r['player'])}.json").exists())    # nothing opened without his answer
        self.assertEqual(consultations.consultation_errors(root), [])
        self.assertEqual(standing.standing_errors(root), [])
        # the same day again: the same ids, nothing new written
        files = sorted(p.name for p in folder.iterdir())
        decisions = sorted(p.name for p in (root / "career").rglob("*.decision.json"))
        again = Run(root).advance("2003-07-01")
        self.assertEqual(again["stopped"], report["stopped"])
        self.assertEqual(sorted(p.name for p in folder.iterdir()), files)
        self.assertEqual(sorted(p.name for p in (root / "career").rglob("*.decision.json")), decisions)
        # Wade objects to the first and approves the rest
        objected, approved = records[0], records[1:]
        answer(root, objected, "object", "2003-07-01")
        for r in approved:
            answer(root, r, "approve", "2003-07-01")
        transient = consultations.consultation_errors(root)             # answered records stay pending until the next run closes them
        self.assertEqual(len(transient), len(records), transient)
        self.assertTrue(all("answered but still in pending_player_decisions" in e for e in transient))
        report = Run(root).advance("2003-07-01")
        self.assertNotIn("awaiting Wade's answer", report["stopped"] or "")
        state = json.loads((root / SEASON_DIR / "current_state.json").read_text())
        self.assertFalse([d for d in state["pending_player_decisions"] if d.startswith(consultations.PENDING_PREFIX)])
        note = (root / SEASON_DIR / "01_Free_Agency/note.md").read_text()
        self.assertIn(f"{objected['player']}: Wade objected to adding him this season", note)
        self.assertFalse((negotiations / f"{slug(objected['player'])}.json").exists())
        for r in approved:
            self.assertTrue((negotiations / f"{slug(r['player'])}.json").exists())
        plan = json.loads((root / SEASON_DIR / "01_Free_Agency/Plans/plan_2003-07-01.json").read_text())
        marks = {t["player"]: t.get("consultation") for t in plan["targets"]}
        self.assertEqual(marks[objected["player"]], "objected")
        answers = consultations.answers(root, SEASON, "2003-07-01")
        self.assertEqual(answers("trade", objected["player"]), "object")           # an objection is kind-agnostic
        self.assertEqual(answers("sign_and_trade", objected["player"]), "object")
        for r in approved:
            self.assertEqual(answers(r["kind"], r["player"]), "approve")           # an approval covers its kind only
            other = "trade" if r["kind"] != "trade" else "free_agent"
            self.assertIsNone(answers(other, r["player"]))
        self.assertEqual(consultations.consultation_errors(root), [])
        self.assertEqual(standing.standing_errors(root), [])


class TradeGateTests(unittest.TestCase):
    def test_propose_waits_for_wade_then_writes_the_proposal(self):
        tmp, root = copy_repo()
        self.addCleanup(tmp.cleanup)
        patches = franchise_patches()
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        standing.record(root, "2003-06-26", "manual")
        writer = signing.Writer(root)
        signing.open_market(writer, "2003-07-01")
        writer.commit()
        day = "2003-07-20"
        state_path = root / SEASON_DIR / "current_state.json"
        state = json.loads(state_path.read_text())
        state["current_date"] = day                                         # the proposal is made on the career date
        state_path.write_text(json.dumps(state, indent=1) + "\n")
        self.assertIsNone(run_trade.propose(day, root))
        records = consultations.records(root, SEASON)
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual((record["kind"], record["status"], record["answer"]), ("trade", "asked", None))
        self.assertGreaterEqual(record["star_basis"]["value"], LOWERED_STAR_LINE)
        trades = root / SEASON_DIR / "00_Team/Transactions/Trades"
        self.assertFalse(trades.exists() and list(trades.glob("*.json")))       # the top choice waits; no other proposal that day
        desk, found = run_trade.search(day, root)
        self.assertNotIn(record["player"], [f["trade"]["miami_in"][0] for f in found])
        self.assertIn(record["player"], [f["trade"]["miami_in"][0] for f in desk.needing_consultation])
        self.assertIsNone(run_trade.propose(day, root))                            # the same ask again, nothing new
        self.assertEqual(len(consultations.records(root, SEASON)), 1)
        self.assertEqual(consultations.consultation_errors(root), [])
        self.assertEqual(standing.standing_errors(root), [])
        # an objection removes him from the desk's candidates altogether
        objected = desk.search([], "franchise", limit=10, consultations=lambda kind, player: "object" if player == record["player"] else None)
        self.assertNotIn(record["player"], [f["trade"]["miami_in"][0] for f in objected + desk.needing_consultation])
        # the next day, still unanswered: no second question, no proposal, the clock waits on the first ask
        next_day = "2003-07-21"
        state = json.loads(state_path.read_text())                            # the ask added its pending entry
        state["current_date"] = next_day
        state_path.write_text(json.dumps(state, indent=1) + "\n")
        self.assertIsNone(run_trade.propose(next_day, root))
        self.assertEqual([r["id"] for r in consultations.records(root, SEASON)], [record["id"]])
        self.assertEqual(consultations.unanswered(root, SEASON, next_day), [record["id"]])
        self.assertEqual(run_trade.shop(next_day, root), (None, []))
        self.assertEqual(consultations.consultation_errors(root), [])
        self.assertEqual(standing.standing_errors(root), [])
        # Wade approves the first (and only) ask: the proposal is written on the later day, cites the consultation, and the pending entry is closed
        answer(root, record, "approve", next_day)
        self.assertEqual(consultations.answers(root, SEASON, next_day)("trade", record["player"]), "approve")
        proposal = run_trade.propose(next_day, root)
        self.assertIsNotNone(proposal)
        state = json.loads(state_path.read_text())
        self.assertNotIn(consultations.PENDING_PREFIX + record["id"], state["pending_player_decisions"])
        self.assertEqual(proposal["trade"]["miami_in"], [record["player"]])
        self.assertEqual(proposal["consultation"], record["id"])
        self.assertEqual(proposal["standing"]["standing"], "franchise")
        self.assertTrue((trades / f"{proposal['decision_event']}.decision.json").exists())
        self.assertEqual(proposal["date"], next_day)
        self.assertEqual(trade_record_errors(root), [])
        self.assertEqual(consultations.consultation_errors(root), [])
        self.assertEqual(consultations.unanswered(root, SEASON, next_day), [])


class ValidationTests(unittest.TestCase):
    def write(self, root, day, kind, player, answer=None):
        state = {"pending_player_decisions": []}
        record = consultations.ask(root, state, day, kind, player, "x01", "Some Club", basis="test",
                                   evidence={"value": 25.0}, season=SEASON, standing=dict(FRANCHISE))
        if answer:
            path = consultations.folder(root, SEASON) / f"{record['id']}.json"
            data = json.loads(path.read_text())
            data.update(answer=answer, answered=day, status="closed")
            path.write_text(json.dumps(data, indent=1) + "\n")
        return record, state

    def pending(self, root, entries):
        state_path = root / SEASON_DIR / "current_state.json"
        state = json.loads(state_path.read_text())
        state["current_date"] = "2003-07-20"
        state["pending_player_decisions"] = [consultations.PENDING_PREFIX + e for e in entries]
        state_path.write_text(json.dumps(state, indent=1) + "\n")

    def test_one_question_at_a_time_and_never_ahead_of_the_clock(self):
        tmp, root = copy_repo()
        self.addCleanup(tmp.cleanup)
        first, state = self.write(root, "2003-07-20", "trade", "Kevin Garnett")
        self.assertEqual(state["pending_player_decisions"], [consultations.PENDING_PREFIX + first["id"]])
        again, state = self.write(root, "2003-07-21", "trade", "Kevin Garnett")        # the same open question is returned, not asked twice
        self.assertEqual(again["id"], first["id"])
        self.assertEqual([r["id"] for r in consultations.records(root, SEASON)], [first["id"]])
        self.assertIsNone(consultations.answer_of(root, SEASON, "Kevin Garnett", "2003-07-21"))   # a question is not an answer
        self.pending(root, [first["id"]])
        self.assertEqual(consultations.consultation_errors(root), [])
        # a record dated after the career clock, and two unanswered questions for one player, are validation errors
        path = consultations.folder(root, SEASON) / f"{first['id']}.json"
        late = json.loads(path.read_text())
        late.update(id=consultations.consultation_id("2003-07-25", "trade", "Kevin Garnett"), date="2003-07-25")
        late_path = consultations.folder(root, SEASON) / f"{late['id']}.json"
        late_path.write_text(json.dumps(late, indent=1) + "\n")
        (consultations.folder(root, SEASON) / consultations.page_name(late)).write_text(consultations.page(late, {"value": 25.0}))
        self.pending(root, [first["id"], late["id"]])
        errors = consultations.consultation_errors(root)
        self.assertTrue(any("after the career date 2003-07-20" in e for e in errors), errors)
        self.assertTrue(any("already has the unanswered consultation" in e and first["id"] in e for e in errors), errors)
        late_path.unlink()
        (consultations.folder(root, SEASON) / consultations.page_name(late)).unlink()
        self.pending(root, [first["id"]])
        self.assertEqual(consultations.consultation_errors(root), [])
        # once answered, the answer is found even when a later record of another kind is open
        data = json.loads(path.read_text())
        data.update(answer="approve", answered="2003-07-20", status="closed")
        path.write_text(json.dumps(data, indent=1) + "\n")
        other, _ = self.write(root, "2003-07-20", "free_agent", "Kevin Garnett")
        self.pending(root, [other["id"]])
        self.assertEqual(consultations.answers(root, SEASON, "2003-07-20")("trade", "Kevin Garnett"), "approve")
        self.assertIsNone(consultations.answers(root, SEASON, "2003-07-20")("free_agent", "Kevin Garnett"))
        self.assertEqual(consultations.consultation_errors(root), [])


if __name__ == "__main__":
    unittest.main()
