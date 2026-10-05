"""Roadmap 14b phase 5: existing 2004-05 contracts and the simulated Charlotte expansion draft."""
from pathlib import Path
import unittest

from runtime import contract_terms as C, expansion as E

ROOT = Path(__file__).resolve().parents[1]


class ContractTermsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.terms = C.existing_terms(ROOT)

    def test_a_2004_free_agent_has_no_contract(self):
        self.assertNotIn("foylead01", self.terms)            # re-signed in July 2004: decided by the sim, not history

    def test_rookie_option_decided_before_the_sim_stands(self):
        self.assertEqual(self.terms["parketo01"]["kind"], "contract")
        self.assertIn("2003-10-31", self.terms["parketo01"]["source"])

    def test_2003_first_round_pick_is_on_the_rookie_scale(self):
        t = self.terms["jamesle01"]
        self.assertIn("2005-06", t["schedule"])
        self.assertEqual(t["team_option"], "2006-07")

    def test_options_after_june_2004_stay_open(self):
        options = [t for t in self.terms.values() if t["kind"] == "option"]
        self.assertTrue(options)
        self.assertTrue(all(t["option_kind"] in C.OPTION_KINDS for t in options))


def row(name, value, salary=1_000_000, years=1):
    return {"name": name, "bbr_id": name, "salary": salary, "years_left": years, "value": value}


class ExpansionTests(unittest.TestCase):
    def lists(self, clubs=16, size=10):
        return {f"Club {c}": [row(f"c{c}p{i}", 10 - i + c / 100) for i in range(size)] for c in range(clubs)}

    def test_rules(self):
        record = E.decide(ROOT, self.lists())
        picks = record["selections"]
        self.assertGreaterEqual(len(picks), E.MIN_PICKS)
        self.assertLessEqual(len(picks), E.MAX_PICKS)
        self.assertEqual(len({p["from"] for p in picks}), len(picks))            # at most one per club
        for p in picks:
            self.assertNotIn(p["player"], record["protected"][p["from"]])
            self.assertEqual(p["trade_exception"], p["salary_2004_05"])
        self.assertTrue(all(len(v) <= E.PROTECT for v in record["protected"].values()))

    def test_a_club_with_eight_or_fewer_loses_no_one(self):
        record = E.decide(ROOT, {"Small": [row(f"s{i}", 5) for i in range(8)]})
        self.assertEqual(record["selections"], [])

    def test_miami_loss_is_refused_until_built(self):
        with self.assertRaises(NotImplementedError):
            E.decide(ROOT, {E.MIAMI: [row(f"m{i}", 9 - i) for i in range(9)]})

    def test_nothing_before_the_date(self):
        self.assertIsNone(E.run(ROOT, "2004-06-21"))


if __name__ == "__main__":
    unittest.main()
