import json
import shutil
import tempfile
import unittest
from pathlib import Path

from runtime.contracts import cap_rules, club_ledger, contract_errors, rookie_scale

ROOT = Path(__file__).resolve().parents[1]


class ContractInventoryTests(unittest.TestCase):
    def test_inventory_is_clean(self):
        self.assertEqual(contract_errors(ROOT), [])

    def test_miami_ledger_matches_miami_sheet(self):
        # The league inventory is the June 26 snapshot, so it matches Miami's June 26 finance summary.
        ledger = club_ledger("Miami Heat", "2003-04")
        finance = json.loads((ROOT / "tests/fixtures/checkpoint_2003-06-26/career/Dwyane_Wade/2003-04/00_Team/Finances/finance.json").read_text())
        self.assertEqual(ledger["committed"] + ledger["holds"], finance["known_counted_salary_before_free_agent_holds"])
        self.assertEqual(ledger["conditional"], 1691037 + 4100000)   # three team options + Carter's player option
        self.assertEqual(ledger["unresolved"], [])

    def test_cap_figures_are_gated_by_publication(self):
        with self.assertRaises(ValueError):
            cap_rules("2003-04", "2003-07-14")
        self.assertEqual(cap_rules("2003-04", "2003-07-15")["salary_cap"], 43840000)
        with self.assertRaises(ValueError):
            cap_rules("2004-05", "2004-09-01")   # publication date not yet researched

    def test_rookie_scale(self):
        self.assertEqual(rookie_scale(5)["year_1"], 2197000)
        self.assertEqual(rookie_scale(1)["year_1"], 3349100)

    def test_restricted_marks_are_eligibility_only(self):
        data = json.loads((ROOT / "library/2003/league/nba_2003_contracts.json").read_text())
        statuses = {p["status"] for c in data["clubs"].values() for p in c["players"]}
        self.assertNotIn("free_agent_restricted", statuses)
        self.assertTrue(any(p.get("rfa_eligible") for c in data["clubs"].values() for p in c["players"]))

    def test_leaked_signing_note_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(ROOT / "library", root / "library")
            target = root / "career/Dwyane_Wade/2003-04/00_Team/Finances"
            target.mkdir(parents=True)
            shutil.copy(ROOT / "career/Dwyane_Wade/2003-04/00_Team/Finances/league_cap_history.json", target)
            path = root / "library/2003/league/nba_2003_contracts.json"
            data = json.loads(path.read_text())
            data["clubs"]["Miami Heat"]["players"][0]["notes"] = "Signed a new contract after June 30, 2003."
            path.write_text(json.dumps(data))
            self.assertTrue(any("post-checkpoint" in e for e in contract_errors(root)))


if __name__ == "__main__":
    unittest.main()
