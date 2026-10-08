"""1999 CBA minimum salaries by years of service, the reimbursed veteran minimum, and the live ledger."""
import json
from pathlib import Path
import unittest

from runtime.cba import minimum_cap_amount, minimum_salary
from runtime.contracts import counted_amount
from runtime.signing import ledger_aggregates
from runtime.valuation import Valuation

ROOT = Path(__file__).resolve().parents[1]
TEAM = ROOT / "career/Dwyane_Wade/2003-04/00_Team"


class MinimumScaleTests(unittest.TestCase):
    def test_every_year_of_service_has_its_own_minimum(self):
        self.assertEqual([minimum_salary(y) for y in (0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 14)],
                         [366931, 563679, 638679, 663679, 688679, 751179, 813679, 938679, 1000000, 1070000, 1070000])
        with self.assertRaises(ValueError):
            minimum_salary(None)

    def test_a_veteran_one_year_minimum_counts_the_four_year_minimum(self):
        self.assertEqual(minimum_cap_amount(8, 938679, 1), 688679)
        self.assertEqual(minimum_cap_amount(14, 1070000, 1), 688679)
        self.assertEqual(minimum_cap_amount(4, 688679, 1), 688679)       # under five years: full salary
        self.assertEqual(minimum_cap_amount(8, 938679, 2), 938679)       # two-year deal: full salary
        self.assertEqual(minimum_cap_amount(8, 1200000, 1), 1200000)     # above the minimum: full salary

    def test_a_veteran_without_recorded_service_cannot_be_signed(self):
        valuation = Valuation("2003-10-27", ROOT)
        with self.assertRaises(ValueError):
            valuation.signing_minimum(None)
        self.assertEqual(valuation.signing_minimum(None, nba_history=False), 366931)
        self.assertEqual(valuation.signing_minimum(6), 813679)


class LiveLedgerTests(unittest.TestCase):
    def setUp(self):
        self.sheet = json.loads((TEAM / "Finances/contract_schedules.json").read_text())
        self.finance = json.loads((TEAM / "Finances/finance.json").read_text())

    def test_aggregates_skip_closed_entries_and_use_counted_amounts(self):
        sheet = {"players": [
            {"player": "A", "status": "camp_contract", "schedule": {"2003-04": 938679}, "cap_amount": {"2003-04": 688679},
             "amount_kind": {"2003-04": "contract_salary"}},
            {"player": "B", "status": "voided", "schedule": {"2003-04": 638679}, "amount_kind": {"2003-04": "contract_salary"}},
            {"player": "C", "status": "team_option_exercised", "schedule": {"2003-04": 563679}, "amount_kind": {"2003-04": "team_option"}},
            {"player": "D", "status": "under_contract", "schedule": {"2003-04": 1000000, "2004-05": 1100000},
             "amount_kind": {"2003-04": "contract_salary", "2004-05": "team_option"}}]}
        totals, components = ledger_aggregates(sheet)
        self.assertEqual(totals["2003-04"]["contract_salary"], 688679 + 563679 + 1000000)
        self.assertEqual(totals["2004-05"]["options"], 1100000)
        self.assertEqual([c["player"] for c in components], ["A", "C", "D"])
        self.assertEqual(counted_amount(sheet["players"][0], "2003-04"), 688679)

    def test_live_finance_matches_the_ledger_and_every_miami_minimum_is_legal(self):
        totals, components = ledger_aggregates(self.sheet)
        base = totals["2003-04"]["contract_salary"] + totals["2003-04"]["draft_hold"]
        if self.finance["as_of"] > "2003-06-26":
            self.assertEqual(self.finance["known_counted_salary"], base)
            self.assertEqual(sum(c["amount"] for c in self.finance["known_current_components"]), base)
        for p in self.sheet["players"]:
            if p.get("route") == "minimum" and p["status"] == "camp_contract":
                self.assertIsNotNone(p.get("years_of_service"), p["player"])
                self.assertEqual(p["schedule"]["2003-04"], minimum_salary(p["years_of_service"]), p["player"])


    def test_voided_and_released_camp_contracts_are_not_current(self):
        catalog = json.loads((ROOT / "career/Dwyane_Wade/Contracts/catalog.json").read_text())
        ended = {p["player"]: p for p in self.sheet["players"] if p["status"] in ("voided", "released")}
        rows = [p for p in catalog["players"] if p["name"] in ended]
        self.assertTrue(rows)
        for row in rows:
            current = row["current_contract_id"]
            if current is None:
                self.assertIn(row["status"], ("voided", "released"))
                continue
            # A later contract may be current, with another club (a summer signing) or with Miami again (Jumaine Jones's
            # 2005 camp invitation); the ended Miami one never is.
            self.assertGreater(current.rsplit("-", 3)[-3:], ended[row["name"]]["signed_date"].split("-"), row["name"])


if __name__ == "__main__":
    unittest.main()
