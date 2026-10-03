"""Actual write commands refresh live screens without inventing career evidence."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from runtime import KERNEL_VERSION, signing
from scripts import collect_results, open_rookie_negotiation, run_camp, run_free_agency, run_june30, run_trade
from scripts.refresh_career_views import refresh_career_views


class LiveWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.output = io.StringIO()
        self.quiet = contextlib.redirect_stdout(self.output)
        self.quiet.__enter__()
        self.addCleanup(self.quiet.__exit__, None, None, None)

    def player(self, name="Player"):
        player = self.root / "career" / name
        player.mkdir(parents=True)
        (player / "professional_identity.json").write_text("{}")
        return player

    def test_render_failure_keeps_all_previously_published_pages(self):
        first = self.player("A")
        self.player("B")
        page = first / "Player_Cards.html"
        page.write_text("previous complete screen")
        with patch("scripts.refresh_career_views.build_reports", side_effect=[{page: "new screen"}, ValueError("bad source")]):
            with self.assertRaisesRegex(ValueError, "bad source"):
                refresh_career_views(self.root)
        self.assertEqual(page.read_text(), "previous complete screen")

    def test_refresh_replaces_stale_views_and_does_not_rewrite_current_pages(self):
        player = self.player()
        page = player / "Milestones/index.html"
        with patch("scripts.refresh_career_views.build_reports", return_value={page: "detailed current checkpoint"}):
            self.assertEqual(refresh_career_views(self.root), [page])
            stamp = page.stat().st_mtime_ns
            self.assertEqual(refresh_career_views(self.root), [])
            self.assertEqual(page.stat().st_mtime_ns, stamp)

    def test_free_agency_cli_refreshes_after_stopping_for_player_answer(self):
        committed = []
        def advance(day):
            committed.append(day)
            return {"date": day, "log": [], "stopped": "awaiting Wade's answer"}
        def refresh(root):
            self.assertEqual(committed, ["2003-07-20"])
            return []
        with patch.object(run_free_agency, "Run") as driver, patch.object(run_free_agency, "refresh_career_views", side_effect=refresh) as render:
            driver.return_value.advance.side_effect = advance
            run_free_agency.main(["run_free_agency.py", "--write", "2003-07-20"])
            render.assert_called_once_with(run_free_agency.ROOT)

    def test_read_only_free_agency_plan_does_not_refresh(self):
        with patch.object(run_free_agency, "Market"), patch.object(run_free_agency, "FrontOffice") as office, \
                patch.object(run_free_agency.standing, "standing_on", return_value={"standing": "rookie"}), \
                patch.object(run_free_agency, "refresh_career_views") as render:
            office.return_value.plan.return_value = {"targets": []}
            run_free_agency.main(["run_free_agency.py", "--plan", "2003-07-20"])
            render.assert_not_called()

    def test_trade_cli_refreshes_once_after_answers_are_applied(self):
        applied = []
        def write(day):
            applied.append(day)
            return [("trade-1", "completed")], []
        with patch.object(run_trade, "write", side_effect=write), patch.object(run_trade, "refresh_career_views", return_value=[]) as render:
            run_trade.main(["run_trade.py", "--write", "2003-07-22"])
            self.assertEqual(applied, ["2003-07-22"])
            render.assert_called_once_with(run_trade.ROOT)

    def test_camp_cli_refreshes_even_while_waiting_for_draws(self):
        with patch.object(run_camp, "CampRun") as driver, patch.object(run_camp, "refresh_career_views", return_value=[]) as render:
            driver.return_value.write.return_value = ["awaiting camp injury draws"]
            run_camp.main(["run_camp.py", "--write", "2003-09-30"])
            driver.return_value.write.assert_called_once_with("2003-09-30")
            render.assert_called_once_with(run_camp.ROOT)

    def test_collector_refresh_does_not_close_raw_sidecar(self):
        note = self.root / "Game_1.md"
        note.write_text("---\nstatus: scheduled\nresult_file:\n---\nAwaiting canonical closure.\n")
        request = self.root / "Game_1.request.json"
        result = self.root / "Game_1.result.json"
        packet = {"event_id": "game-1", "home_score": 101, "away_score": 90}
        with patch.object(collect_results, "ROOT", self.root), \
                patch.object(collect_results, "pending", return_value=[(request, result, "game-1", "game")]), \
                patch.object(collect_results, "fetch", side_effect=[{"kernel": KERNEL_VERSION}, {"games": {}}, packet]), \
                patch.object(collect_results, "refresh_career_views", return_value=[]) as render:
            collect_results.main()
            render.assert_called_once_with(self.root)
        self.assertEqual(json.loads(result.read_text()), packet)
        self.assertIn("status: scheduled", note.read_text())
        self.assertIn("result_file:\n", note.read_text())

    def test_june30_cli_refreshes_after_writing_decision_requests(self):
        folder = self.root / "June_30"
        def refresh(root):
            self.assertTrue((folder / "front_office_decisions.json").is_file())
            self.assertTrue((folder / "june-30.decision.json").is_file())
            return []
        with patch.object(run_june30, "ROOT", self.root), patch.object(run_june30, "OUT", folder), \
                patch.object(run_june30, "build", return_value=({"decisions": []}, [{"event_id": "june-30"}])), \
                patch.object(run_june30, "refresh_career_views", side_effect=refresh) as render, \
                patch("sys.argv", ["run_june30.py", "--write"]):
            run_june30.main()
            render.assert_called_once_with(self.root)

    def rookie_state(self, day):
        path = self.root / signing.STATE
        path.parent.mkdir(parents=True, exist_ok=True)
        state = {"current_date": day, "contract_status": "draft_rights_unsigned", "pending_player_decisions": ["another_player_choice"]}
        path.write_text(json.dumps(state))
        note = self.root / signing.PHASE / "note.md"
        note.parent.mkdir(parents=True, exist_ok=True)
        note.write_text("---\nstatus: not_started\n---\n## Events\n\n## Consequences\n")
        return path

    def test_rookie_offer_refuses_future_and_pre_market_dates_without_writes(self):
        state = self.rookie_state("2003-06-26")
        before = state.read_text()
        for day in ("2003-06-26", "2003-07-01"):
            with self.subTest(day=day), self.assertRaises(ValueError):
                open_rookie_negotiation.open_negotiation(day, self.root)
        self.assertEqual(state.read_text(), before)
        self.assertFalse((self.root / open_rookie_negotiation.LOG).exists())

    def test_rookie_offer_is_pending_and_refreshes_at_same_career_date(self):
        state_path = self.rookie_state("2003-07-01")
        def refresh(root):
            log = json.loads((root / open_rookie_negotiation.LOG).read_text())
            self.assertEqual([e["action"] for e in log["entries"]], ["offer"])
            return []
        with patch.object(open_rookie_negotiation, "refresh_career_views", side_effect=refresh) as render:
            open_rookie_negotiation.main(["open_rookie_negotiation.py", "--write", "2003-07-01"], self.root)
            render.assert_called_once_with(self.root)
        state = json.loads(state_path.read_text())
        self.assertEqual(state["current_date"], "2003-07-01")
        self.assertEqual(state["contract_status"], "draft_rights_unsigned")
        self.assertEqual(state["pending_player_decisions"], ["another_player_choice", "rookie_contract_offer"])
        self.assertIn("Milestones/index.html#contract_negotiation", (self.root / signing.PHASE / "note.md").read_text())


if __name__ == "__main__":
    unittest.main()
