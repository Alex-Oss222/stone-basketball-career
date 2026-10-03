"""Live integration: source ownership, date/version guards and event handoffs."""
from pathlib import Path
import shutil
import tempfile
import unittest

from tests import checkpoint

from runtime import consultations, signing
from runtime.milestone_records import PLAYER, SCREEN_MAP, read, version
from runtime.player_milestones import build_milestone_pages
from runtime.player_reports import report_errors
from runtime.career_stats import collect_games
from scripts.refresh_career_views import refresh_career_views as refresh
from runtime.career_stats import identity_at
from scripts.open_rookie_negotiation import open_negotiation
from scripts.player_milestone import dump, record_event, reply

ROOT = Path(__file__).resolve().parents[1]
SEASON = "2003-04"


class MilestoneReplyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / "career", self.root / "career")
        checkpoint.pin(self.root)
        shutil.copytree(ROOT / "foundation", self.root / "foundation")
        (self.root / "library/2003/league").mkdir(parents=True)
        for filename in ("nba_2003_04_calendar.json", "nba_2003_04_cap_rules.json"):
            shutil.copy(ROOT / "library/2003/league" / filename, self.root / "library/2003/league" / filename)
        self.player = self.root / PLAYER
        self.season = self.player / SEASON
        self.state_path = self.season / "current_state.json"
        self.registry_path = self.player / "milestones.json"
        dump(self.registry_path, {"schema_version": 1, "enabled": True, "events": []})
        self.source = f"{PLAYER}/{SEASON}/03_Offseason/note.md"

    def day(self, day):
        state = read(self.state_path)
        state["current_date"] = day
        dump(self.state_path, state)

    def page(self, key):
        return self.player / "Milestones" / (SCREEN_MAP[key] + ".md")

    def event(self, **changes):
        e = {"id": "focus-meeting", "season": SEASON, "kind": "training", "title": "Development planning",
             "recorded_on": read(self.state_path)["current_date"], "status": "planned", "owner": "player", "needs_response": True,
             "source_ref": self.source, "details": {"Focus": "Awaiting player choice"}, "prompt": "Which skill do you want to work on?",
             "next_checkpoint": {"date": None, "trigger": "Staff agree the plan"}}
        e.update(changes)
        return e

    def response(self, **changes):
        r = {"season": SEASON, "date": read(self.state_path)["current_date"], "kind": "working_record", "event_id": "focus-meeting",
             "action": "record", "text": "Test-fixture player reply", "source_ref": self.source}
        r.update(changes)
        return r

    def test_opening_is_empty_dated_and_read_only(self):
        paths = [self.state_path, self.player / "professional_identity.json", self.player / "awards.json", self.season / "00_Team/Finances/contract_schedules.json"]
        before = {p: p.read_bytes() for p in paths}
        identity = read(self.player / "professional_identity.json")
        outputs = build_milestone_pages(self.player, identity, collect_games(self.player, identity, read(self.state_path)["current_date"]), root=self.root)
        self.assertTrue(all(self.page(k) in outputs for k in SCREEN_MAP))
        self.assertIn("None recorded", outputs[self.page("calendar")])
        self.assertIn("No written rookie-contract offer", outputs[self.page("contract")])
        self.assertIn("draft", outputs[self.page("checkpoint")])
        for text in outputs.values():
            self.assertNotIn("43,840,000", text)
            self.assertNotIn("54,556,722", text)
        refresh(self.root)
        self.assertEqual(refresh(self.root), [])
        self.assertEqual(before, {p: p.read_bytes() for p in paths})
        phase = self.season / "03_Offseason/README.md"
        self.assertIn("Choose a development focus", phase.read_text())
        self.assertEqual(phase.read_text().count("<!-- career-desk:start -->"), 1)

    def test_early_or_future_rookie_offer_refused(self):
        before = self.state_path.read_bytes()
        for day in ("2003-06-26", "2003-07-01"):
            with self.assertRaises(ValueError):
                open_negotiation(day, self.root)
        self.assertEqual(before, self.state_path.read_bytes())
        self.assertFalse((self.season / "01_Free_Agency/Wade_Rookie_Contract/negotiation_log.json").exists())

    def test_offer_reply_updates_live_desk_but_does_not_sign(self):
        self.day("2003-07-16")
        log = open_negotiation("2003-07-16", self.root)
        refresh(self.root)
        self.assertIn("awaiting response", self.page("contract").read_text())
        token = version(log)
        salary = (self.season / "00_Team/Finances/contract_schedules.json").read_bytes()
        response = self.response(kind="rookie_contract", action="accept")
        reply(self.root, response, token)
        self.assertEqual(read(log)["entries"][-1]["terms"], read(log)["entries"][0]["terms"])
        self.assertEqual(read(log)["entries"][-1]["party"], "wade")
        self.assertIn("Waiting on Miami", self.page("calendar").read_text())
        self.assertNotIn("awaiting response", self.page("contract").read_text())
        self.assertEqual(salary, (self.season / "00_Team/Finances/contract_schedules.json").read_bytes())
        self.assertEqual(read(self.state_path)["current_date"], "2003-07-16")
        with self.assertRaisesRegex(ValueError, "record changed"):
            reply(self.root, response, token)
        with self.assertRaisesRegex(ValueError, "unanswered"):
            reply(self.root, response, version(log))

    def test_reply_date_source_and_scale_guards_leave_offer_unchanged(self):
        self.day("2003-07-16")
        log = open_negotiation("2003-07-16", self.root)
        refresh(self.root)
        before = log.read_bytes()
        invalid = [self.response(kind="rookie_contract", action="counter", percent_of_scale=121),
                   self.response(kind="rookie_contract", action="counter", percent_of_scale=float("nan")),
                   self.response(kind="rookie_contract", action="accept", date="2003-07-17"),
                   self.response(kind="rookie_contract", action="accept", source_ref="../outside.md")]
        for r in invalid:
            with self.assertRaises(ValueError):
                reply(self.root, r, version(log))
            self.assertEqual(log.read_bytes(), before)
        reply(self.root, self.response(kind="rookie_contract", action="counter", percent_of_scale=110), version(log))
        self.assertEqual(read(log)["entries"][-1]["terms"]["percent_of_scale"], 110)

    def test_franchise_answer_reaches_existing_gate(self):
        state = read(self.state_path)
        r = consultations.ask(self.root, state, "2003-06-26", "trade", "Test Star", "teststar", "Test Club",
                              basis="Test fixture only", evidence={"value": 25, "line": "Dated fixture evidence"},
                              standing={"standing": "franchise", "as_of": "2003-06-26"})
        dump(self.state_path, state)
        refresh(self.root)
        self.assertIn("Awaiting your answer", self.page("trade").read_text())
        path = consultations.folder(self.root, SEASON) / (r["id"] + ".json")
        reply(self.root, self.response(kind="consultation", event_id=r["id"], action="object"), version(path))
        self.assertTrue(consultations.objected(self.root, SEASON, "Test Star", "2003-06-26"))
        self.assertEqual(consultations.unanswered(self.root, SEASON, "2003-06-26"), [])
        self.assertEqual(consultations.consultation_errors(self.root), [])
        self.assertNotIn(consultations.PENDING_PREFIX + r["id"], read(self.state_path)["pending_player_decisions"])

    def test_training_handoff_preserves_history_and_no_ability_writes(self):
        before = (self.player / "professional_identity.json").read_bytes()
        record_event(self.root, self.event(), version(self.registry_path))
        self.assertIn("Which skill", self.page("calendar").read_text())
        reply(self.root, self.response(text="I want to focus on finishing through contact."), version(self.registry_path))
        self.assertIn("finishing through contact", self.page("training").read_text())
        followup = self.event(id="agreed-block", supersedes="focus-meeting", owner="staff", needs_response=False, status="active")
        record_event(self.root, followup, version(self.registry_path))
        self.assertIn("History; followed by agreed-block", self.page("training").read_text())
        with self.assertRaises(ValueError):
            reply(self.root, self.response(), version(self.registry_path))
        self.assertEqual((self.player / "professional_identity.json").read_bytes(), before)
        self.assertEqual(len(read(self.registry_path)["events"]), 2)

    def test_bad_working_events_are_rejected_before_write(self):
        before = self.registry_path.read_bytes()
        for event in (self.event(recorded_on="2003-07-01"), self.event(source_ref="docs/examples/player_stats_preview.md"),
                      self.event(owner="club"), self.event(starts_on="2003-07-02", ends_on="2003-07-01"),
                      self.event(supersedes="missing")):
            with self.assertRaises(ValueError):
                record_event(self.root, event, version(self.registry_path))
            self.assertEqual(before, self.registry_path.read_bytes())

    def test_archived_season_cannot_receive_a_new_reply(self):
        state = read(self.state_path)
        state.update(season="2004-05", current_date="2004-06-26")
        dump(self.player / "2004-05/current_state.json", state)
        before = self.registry_path.read_bytes()
        with self.assertRaisesRegex(ValueError, "active career season"):
            record_event(self.root, self.event(), version(self.registry_path))
        self.assertEqual(before, self.registry_path.read_bytes())

    def test_conflicts_and_successor_closure(self):
        dates = {"starts_on": "2003-07-01", "ends_on": "2003-07-03"}
        record_event(self.root, self.event(**dates), version(self.registry_path))
        record_event(self.root, self.event(id="meeting-two", title="Second appointment", **dates), version(self.registry_path))
        self.assertIn("Scheduling conflicts", self.page("calendar").read_text())
        record_event(self.root, self.event(id="meeting-canceled", supersedes="meeting-two", status="closed", needs_response=False, owner="none"), version(self.registry_path))
        self.assertNotIn("Scheduling conflicts", self.page("calendar").read_text())

    def test_camp_and_completed_trade_use_dated_sources_only(self):
        camp = self.season / "04_Training_Camp"
        dump(camp / "camp_roster.json", {"opened": "2003-09-30", "evaluated": "2003-10-24"})
        (camp / "Wade_Camp_Review.md").write_text("# Actual assessment in test fixture\n")
        trade = self.season / "00_Team/Transactions/Trades/test.json"
        dump(trade, {"date": "2003-07-16", "status": "proposed", "applied": "2003-07-16", "trade": {"partner": "Fixture Partner", "miami_out": ["Fixture Out"], "miami_in": ["Fixture In"]}})
        refresh(self.root)
        self.assertNotIn("Wade_Camp_Review.md", self.page("camp").read_text())
        self.assertNotIn("Fixture Partner", self.page("trade").read_text())
        data = read(trade)
        data["status"] = "completed"
        dump(trade, data)
        refresh(self.root)
        self.assertNotIn("Fixture Partner", self.page("trade").read_text())
        self.day("2003-10-24")
        refresh(self.root)
        self.assertIn("Wade_Camp_Review.md", self.page("camp").read_text())
        self.assertIn("Fixture Partner", self.page("trade").read_text())

    def test_executed_signing_dates_identity_without_rewriting_draft_identity(self):
        self.day("2003-07-16")
        path = open_negotiation("2003-07-16", self.root)
        log = read(path)
        writer = signing.Writer(self.root)
        signing.sign_rookie(writer, log, log["entries"][0]["terms"], "2003-07-16")
        writer.files[path.relative_to(self.root)] = log
        writer.commit()
        refresh(self.root)
        identity = read(self.player / "professional_identity.json")
        self.assertEqual(identity_at(identity, "2003-06-26")["roster_status"], "Draft rights; unsigned")
        self.assertEqual(identity_at(identity, "2003-07-16")["roster_status"], "Under contract")
        self.assertIn("recorded", self.page("contract").read_text())

    def test_repository_views_and_links_are_fresh(self):
        self.assertEqual(report_errors(ROOT, ROOT / PLAYER), [])


if __name__ == "__main__":
    unittest.main()
