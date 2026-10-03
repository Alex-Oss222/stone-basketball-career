"""Live milestone source gates, real response ownership and report-only output."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from runtime.player_milestones import SCREEN_IDS, build_milestone_pages, build_milestone_payload
from runtime.rookie_contract import rookie_terms

ROOT = Path(__file__).resolve().parents[1]


def screen(payload, identifier):
    return next(s for s in payload["screens"] if s["id"] == identifier)


def section(payload, identifier, title):
    return next(s for s in screen(payload, identifier)["sections"] if s["title"] == title)


class LiveMilestonesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.player = self.root / "career/Dwyane_Wade"
        self.season = self.player / "2003-04"
        files = [
            "career/Dwyane_Wade/professional_identity.json",
            "career/Dwyane_Wade/2003-04/current_state.json",
            "career/Dwyane_Wade/2003-04/00_Team/Finances/contract_schedules.json",
            "career/Dwyane_Wade/2003-04/00_Team/Team/Depth_Chart/depth_chart.json",
            "career/Dwyane_Wade/2003-04/09_Draft/note.md",
            "career/Dwyane_Wade/2003-04/01_Free_Agency/note.md",
            "career/Dwyane_Wade/2003-04/01_Free_Agency/wade_requests.json",
            "career/Dwyane_Wade/2003-04/03_Offseason/note.md",
            "career/Dwyane_Wade/2003-04/04_Training_Camp/note.md",
            "library/2003/league/nba_2003_04_cap_rules.json",
        ]
        for relative in files:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)
        self.identity = json.loads((self.player / "professional_identity.json").read_text())

    def pin_checkpoint(self):
        state = json.loads((self.season / "current_state.json").read_text())
        state["current_date"] = "2003-06-26"            # the fixture describes the June 26 checkpoint
        self.write("current_state.json", state)

    def write(self, relative, data):
        path = self.season / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def advance(self, day, **updates):
        state = json.loads((self.season / "current_state.json").read_text())
        state.update(current_date=day, **updates)
        self.write("current_state.json", state)

    def payload(self, records=()):
        return build_milestone_payload(self.player, self.identity, list(records), root=self.root)

    def rookie_log(self, entries):
        return self.write("01_Free_Agency/Wade_Rookie_Contract/negotiation_log.json",
                          {"player": "Dwyane Wade", "entries": entries})

    def offer(self):
        return {"date": "2003-07-01", "party": "miami", "action": "offer",
                "terms": rookie_terms(5, 120, self.root), "note": "Actual test club offer"}

    def test_current_checkpoint_has_nine_detailed_live_views_without_fiction(self):
        self.pin_checkpoint()
        payload = self.payload()
        self.assertEqual([s["id"] for s in payload["screens"]], list(SCREEN_IDS))
        self.assertEqual(payload["as_of"], "2003-06-26")
        self.assertEqual(payload["mode"], "live")
        self.assertFalse(payload["execution_enabled"])
        self.assertTrue(all(len(s["sections"]) >= 4 and s["trigger"] and s["next_checkpoint"] for s in payload["screens"]))
        self.assertEqual(screen(payload, "contract_negotiation")["status"], "inactive")
        self.assertEqual(section(payload, "contract_negotiation", "Actual latest club proposal")["rows"], [])
        self.assertIn("Andre Miller", json.dumps(payload))
        self.assertIn("$2,197,000", json.dumps(payload))
        self.assertNotIn("{{", json.dumps(payload))
        self.assertNotIn("43840000", json.dumps(payload))
        self.assertNotIn("43,840,000", json.dumps(payload))

    def test_fixed_scale_projection_does_not_expose_unpublished_cap_file(self):
        outputs = build_milestone_pages(self.player, self.identity, [], root=self.root)
        projection = json.loads(outputs[self.player / "Milestones/rookie_scale_reference.json"])
        self.assertTrue(projection["reference_only"])
        self.assertEqual(projection["terms_by_scale_percent"]["120"]["schedule"]["2003-04"], 2636400)
        self.assertNotIn("salary_cap", json.dumps(projection))
        payload = json.loads(outputs[self.player / "Milestones/data.json"])
        hrefs = [s["href"] for s in payload["screens"][0]["sources"]]
        self.assertIn("rookie_scale_reference.json", hrefs)
        self.assertFalse(any("nba_2003_04_cap_rules.json" in href for href in hrefs))

    def test_future_rookie_offer_and_future_request_do_not_enter_current_view(self):
        self.pin_checkpoint()
        entry = self.offer()
        entry["note"] = "FUTURE OFFER SECRET"
        self.rookie_log([entry])
        self.write("01_Free_Agency/wade_requests.json", {"requests": [
            {"date": "2003-07-01", "subject": "FUTURE REQUEST SECRET"}]})
        rendered = json.dumps(self.payload())
        self.assertNotIn("FUTURE OFFER SECRET", rendered)
        self.assertNotIn("FUTURE REQUEST SECRET", rendered)
        self.assertEqual(screen(self.payload(), "contract_negotiation")["status"], "inactive")

    def test_real_offer_activates_contract_and_updates_calendar(self):
        self.advance("2003-07-01")
        self.rookie_log([self.offer()])
        payload = self.payload()
        self.assertEqual(screen(payload, "contract_negotiation")["status"], "awaiting_response")
        rows = section(payload, "contract_negotiation", "Actual latest club proposal")["rows"]
        self.assertEqual(rows[0][1], "$2,636,400")
        calendar = section(payload, "calendar", "Milestone calendar")["rows"]
        proposal = next(r for r in calendar if r[1] == "Rookie-contract proposal")
        self.assertEqual(proposal[0], "2003-07-01")
        self.assertEqual(proposal[3], "awaiting response")

    def test_player_counter_does_not_replace_club_offer_or_ask_player_again(self):
        self.advance("2003-07-02")
        self.rookie_log([self.offer(), {"date": "2003-07-02", "party": "wade", "action": "counter",
                                       "terms": rookie_terms(5, 100, self.root)}])
        payload = self.payload()
        self.assertEqual(screen(payload, "contract_negotiation")["status"], "awaiting_club")
        self.assertIn("Miami must answer", screen(payload, "contract_negotiation")["next_checkpoint"])
        rows = section(payload, "contract_negotiation", "Actual latest club proposal")["rows"]
        self.assertEqual(rows[0][1], "$2,636,400")

    def test_acceptance_waits_for_execution_and_signing_checks_control(self):
        self.advance("2003-07-02")
        entries = [self.offer(), {"date": "2003-07-02", "party": "wade", "action": "accept"}]
        self.rookie_log(entries)
        self.assertEqual(screen(self.payload(), "contract_negotiation")["status"], "awaiting_execution")
        entries.append({"date": "2003-07-02", "party": "miami", "action": "sign", "terms": self.offer()["terms"]})
        self.rookie_log(entries)
        payload = self.payload()
        self.assertEqual(screen(payload, "contract_negotiation")["status"], "recorded")
        self.assertIn("authoritative state still shows draft rights",
                      section(payload, "contract_negotiation", "Registration check")["notice"])

    def test_future_effective_dates_cannot_activate_old_as_of_snapshot(self):
        self.pin_checkpoint()
        self.write("03_Offseason/exit_meeting.json", {"as_of": "2003-06-26", "date": "2003-07-01", "goal": "FUTURE EXIT SECRET"})
        self.write("03_Offseason/training_plan.json", {"as_of": "2003-06-26", "date": "2003-07-01", "focus": "FUTURE TRAINING SECRET"})
        self.write("04_Training_Camp/camp_roster.json", {"as_of": "2003-06-26", "opened": "2003-09-30", "players": []})
        payload = self.payload()
        for identifier in ("exit_meeting", "training_camp", "offseason_training"):
            self.assertEqual(screen(payload, identifier)["status"], "inactive")
        self.assertNotIn("FUTURE EXIT SECRET", json.dumps(payload))
        self.assertNotIn("FUTURE TRAINING SECRET", json.dumps(payload))

    def test_recorded_camp_and_exit_activate_and_refresh_calendar(self):
        self.advance("2003-09-30")
        self.write("04_Training_Camp/camp_roster.json", {"opened": "2003-09-30", "status": "open",
            "players": [{"player": "Dwyane Wade", "status": "roster", "injured_through": None}]})
        self.write("03_Offseason/exit_meeting.json", {"date": "2003-07-01", "goal": "Recorded meeting goal"})
        payload = self.payload()
        self.assertEqual(screen(payload, "training_camp")["status"], "active")
        self.assertEqual(screen(payload, "exit_meeting")["status"], "active")
        rows = section(payload, "calendar", "Milestone calendar")["rows"]
        self.assertEqual(next(r for r in rows if r[1] == "Camp reporting")[0], "2003-09-30")
        self.assertEqual(next(r for r in rows if r[1] == "Season exit meeting")[0], "2003-07-01")

    def test_future_mutable_camp_evaluation_is_not_presented_as_current(self):
        self.advance("2003-10-01")
        self.write("04_Training_Camp/camp_roster.json", {"opened": "2003-09-30", "evaluated": "2003-10-24",
            "players": [{"player": "Dwyane Wade", "status": "FUTURE ROLE SECRET"}]})
        payload = self.payload()
        self.assertNotIn("FUTURE ROLE SECRET", json.dumps(payload))
        self.assertEqual(screen(payload, "training_camp")["status"], "inactive")

    def test_outgoing_wade_trade_reports_actual_involvement_and_completion(self):
        self.advance("2003-07-20")
        self.write("00_Team/Transactions/Trades/actual.json", {
            "date": "2003-07-19", "status": "completed", "applied": "2003-07-20",
            "trade": {"partner": "Recorded Club", "miami_out": ["Dwyane Wade"], "miami_in": ["Recorded Player"]}})
        payload = self.payload()
        self.assertEqual(screen(payload, "trade_update")["status"], "active")
        row = next(r for r in section(payload, "trade_update", "What this changes for you")["rows"] if r[0] == "Trade involving Wade")
        self.assertIn("completed", row[1])
        self.assertIn("Recorded Club", row[1])
        self.assertFalse(any("approve" in a["label"].lower() for a in screen(payload, "trade_update")["actions"]))

    def test_future_trade_execution_remains_a_proposal(self):
        self.advance("2003-07-19")
        self.write("00_Team/Transactions/Trades/actual.json", {
            "date": "2003-07-19", "status": "completed", "applied": "2003-07-20",
            "trade": {"partner": "Recorded Club", "miami_out": ["Dwyane Wade"]}})
        row = section(self.payload(), "trade_update", "Actual transaction register")["rows"][0]
        self.assertIn("Proposal", row[1])
        self.assertEqual(row[5], "Not recorded")

    def test_declined_and_void_trades_are_closed_only_after_dated_answer(self):
        self.advance("2003-07-20")
        for status in ("declined", "void"):
            self.write(f"00_Team/Transactions/Trades/{status}.json", {
                "date": "2003-07-19", "status": status, "applied": None,
                "answer": {"date": "2003-07-20", "outcome": "decline" if status == "declined" else "accept"},
                "void_reason": ["Recorded eligibility failure"] if status == "void" else None,
                "trade": {"partner": "Recorded Club", "miami_out": ["Recorded Player"]}})
        rows = section(self.payload(), "trade_update", "Actual transaction register")["rows"]
        self.assertEqual({r[1] for r in rows}, {"Declined", "Void"})
        self.assertIn("Recorded eligibility failure", next(r for r in rows if r[1] == "Void")[6])
        self.advance("2003-07-19")
        rows = section(self.payload(), "trade_update", "Actual transaction register")["rows"]
        self.assertTrue(all("Proposal" in r[1] for r in rows))
        self.assertNotIn("Recorded eligibility failure", json.dumps(rows))

    def test_pending_consultation_is_real_player_action_and_future_answer_hidden(self):
        self.pin_checkpoint()
        self.write("Wade_Consultations/asked.json", {
            "date": "2003-06-26", "kind": "trade", "player": "Recorded Star", "basis": "Actual asking record",
            "status": "closed", "answer": "object", "answered": "2003-06-27"})
        payload = self.payload()
        rows = section(payload, "calendar", "Franchise consultations")["rows"]
        self.assertEqual(rows[0][3], "Awaiting your answer")
        self.assertTrue(any(a["label"] == "Answer the recorded consultation" for a in screen(payload, "trade_update")["actions"]))
        self.advance("2003-06-27")
        self.assertEqual(section(self.payload(), "calendar", "Franchise consultations")["rows"][0][3], "object")

    def test_dated_training_results_future_blocks_and_phase_bullets(self):
        self.pin_checkpoint()
        self.write("03_Offseason/training_plan.json", {"as_of": "2003-06-26", "focus": "Recorded focus", "blocks": [
            {"date": "2003-06-26", "focus": "Recorded block", "result": "Observed result"},
            {"date": "2003-07-01", "focus": "FUTURE BLOCK SECRET"}]})
        note = self.season / "03_Offseason/note.md"
        note.write_text("---\nstatus: in_progress\n---\n\n- 2003-06-26: A real player preference.\n- 2003-07-01: FUTURE NOTE SECRET\n")
        payload = self.payload()
        self.assertEqual(screen(payload, "offseason_training")["status"], "active")
        self.assertIn("Recorded block", json.dumps(payload))
        self.assertIn("A real player preference", json.dumps(payload))
        self.assertNotIn("FUTURE BLOCK SECRET", json.dumps(payload))
        self.assertNotIn("FUTURE NOTE SECRET", json.dumps(payload))

    def test_build_is_deterministic_read_only_and_works_without_root_assets(self):
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        identity_before = deepcopy(self.identity)
        outputs = build_milestone_pages(self.player, self.identity, [], root=self.root)
        self.assertEqual(outputs, build_milestone_pages(self.player, self.identity, [], root=self.root))
        self.assertEqual(self.identity, identity_before)
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()})
        self.assertEqual(len(outputs), 13)
        html = outputs[self.player / "Milestones/index.html"]
        self.assertNotIn("__CAREER_MILESTONES_DATA__", html)
        self.assertIn('"mode": "live"', html)
        self.assertIn("index.html#contract_negotiation", outputs[self.player / "Milestones/calendar.md"])
        self.assertIn("../Stats_and_Awards/player_cards.html", outputs[self.player / "Milestones/stats_review.md"])

    def test_embedded_json_escapes_script_termination_from_recorded_text(self):
        self.write("01_Free_Agency/wade_requests.json", {"requests": [{
            "date": "2003-06-26", "note": "</script><script>bad()</script>", "subject": "recorded text"}]})
        outputs = build_milestone_pages(self.player, self.identity, [], root=self.root)
        self.assertNotIn("</script><script>bad()", outputs[self.player / "Milestones/index.html"])
        self.assertIn("\\u003c/script\\u003e", outputs[self.player / "Milestones/index.html"])


if __name__ == "__main__":
    unittest.main()
