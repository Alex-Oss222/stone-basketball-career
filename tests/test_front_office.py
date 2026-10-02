import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from runtime.decisions import decision_errors, draw
from runtime.front_office import player_option_probability, request_override, rule_margin, team_option
from runtime.private_service import Store, play_requests
from runtime.rookie_contract import log_errors, rookie_terms
from scripts import run_june30

ROOT = Path(__file__).resolve().parents[1]


class Journal:
    def close_event(self, packet):
        return hashlib.sha256(json.dumps(packet, sort_keys=True).encode()).hexdigest()


def copy_repo():
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    shutil.copytree(ROOT / "library", root / "library")
    shutil.copytree(ROOT / "career", root / "career")
    return tmp, root


class FrontOfficeTests(unittest.TestCase):
    def test_rules(self):
        self.assertEqual(team_option("x", 1514, 24)["decision"], "exercise")
        self.assertEqual(team_option("x", 156, 25)["decision"], "decline")
        self.assertGreater(rule_margin(2000, 400, 30, 24), rule_margin(420, 400, 30, 24))
        self.assertGreater(player_option_probability(4100000, 2600000), 0.5)
        self.assertLess(player_option_probability(1000000, 4000000), 0.5)
        self.assertEqual(request_override("exercise", "exercise", 0.1, "unsigned_rookie"), 0)
        self.assertAlmostEqual(request_override("exercise", "decline", 0.2, "unsigned_rookie"), 0.12)

    def test_june30_package_fails_closed_without_years_of_service(self):
        tmp, root = copy_repo()
        self.addCleanup(tmp.cleanup)
        sheet_path = root / "career/Dwyane_Wade/2003-04/00_Team/Finances/contract_schedules.json"
        sheet = json.loads(sheet_path.read_text())
        next(p for p in sheet["players"] if p["player"] == "Anthony Carter").pop("years_of_service", None)
        sheet_path.write_text(json.dumps(sheet))
        with self.assertRaisesRegex(ValueError, "years_of_service"):
            run_june30.build(root)

    def test_june30_package_and_wade_request(self):
        tmp, root = copy_repo()
        self.addCleanup(tmp.cleanup)
        sheet_path = root / "career/Dwyane_Wade/2003-04/00_Team/Finances/contract_schedules.json"
        sheet = json.loads(sheet_path.read_text())
        next(p for p in sheet["players"] if p["player"] == "Anthony Carter")["years_of_service"] = 4
        sheet_path.write_text(json.dumps(sheet))
        (root / "career/Dwyane_Wade/2003-04/01_Free_Agency/wade_requests.json").write_text(json.dumps({"requests": [
            {"date": "2003-06-28", "subject": "team_option", "player": "Ken Johnson", "requested": "exercise",
             "note": "test"}]}))
        package, draws = run_june30.build(root)
        kinds = {(d["kind"], d["player"]): d for d in package["decisions"]}
        self.assertEqual(len([k for k in kinds if k[0] == "team_option"]), 3)
        self.assertEqual(len([k for k in kinds if k[0] == "qualifying_offer"]), 3)
        self.assertEqual(kinds[("team_option", "Ken Johnson")]["status"], "pending_engine_draw")
        for d in draws:
            self.assertEqual(decision_errors(d), [])
        self.assertTrue(any("player-option" in d["event_id"] for d in draws))

    def test_service_draws_decisions_once_and_refuses_edits(self):
        tmp, root = copy_repo()
        self.addCleanup(tmp.cleanup)
        folder = root / "career/Dwyane_Wade/2003-04/01_Free_Agency/June_30"
        folder.mkdir(parents=True)
        request = {"event_id": "t-decision", "date": "2003-06-30", "question": "q?", "decider": "test",
                   "options": {"a": 0.5, "b": 0.5}, "basis": "test"}
        (folder / "t.decision.json").write_text(json.dumps(request))
        store = Store(root / "data/e.sqlite3")
        store.initialize()
        self.assertEqual(play_requests(store, root)["t-decision"]["status"], "decided")
        outcome = store.result("t-decision")["outcome"]
        self.assertEqual(play_requests(store, root)["t-decision"]["status"], "already_decided")
        self.assertEqual(store.result("t-decision")["outcome"], outcome)
        (folder / "t.decision.json").write_text(json.dumps(dict(request, options={"a": 0.9, "b": 0.1})))
        self.assertEqual(next(iter(play_requests(store, root).values()))["status"], "error")

    def test_draw_follows_probabilities(self):
        picks = [draw({"event_id": f"e{i}", "date": "d", "question": "q", "decider": "x",
                       "options": {"a": 0.7, "b": 0.3}, "basis": "b"}, Journal()) for i in range(2000)]
        self.assertAlmostEqual(picks.count("a") / 2000, 0.7, delta=0.04)


class RookieContractTests(unittest.TestCase):
    def test_terms_at_120_percent(self):
        terms = rookie_terms(5, 120)
        self.assertEqual(terms["schedule"]["2003-04"], 2636400)
        self.assertEqual(terms["schedule"]["2005-06"], 3031920)
        self.assertEqual(terms["amount_kind"]["2006-07"], "team_option")
        with self.assertRaises(ValueError):
            rookie_terms(5, 125)

    def test_log_rules(self):
        offer = {"date": "2003-07-01", "party": "miami", "action": "offer", "terms": rookie_terms(5, 120)}
        self.assertEqual(log_errors({"entries": [offer]}), [])
        bad = dict(offer, terms=dict(rookie_terms(5, 120), percent_of_scale=110))
        self.assertTrue(log_errors({"entries": [bad]}))
        backwards = [offer, {"date": "2003-06-30", "party": "wade", "action": "accept"}]
        self.assertTrue(log_errors({"entries": backwards}))


if __name__ == "__main__":
    unittest.main()
