import json
import unittest
from pathlib import Path

from runtime.cba import bird_seasons, bird_status, cap_hold, qualifying_offer, rfa_eligible, rules

ROOT = Path(__file__).resolve().parents[1]
CBA = rules(ROOT)
RIGHTS = json.loads((ROOT / "career/Dwyane_Wade/2003-04/00_Team/Finances/free_agent_rights.json").read_text())


class CbaRuleTests(unittest.TestCase):
    def test_bird_clock_counts_seasons_after_joining(self):
        self.assertEqual(bird_seasons("2000-06-28"), 3)   # drafted in June, first season 2000-01
        self.assertEqual(bird_seasons("2001-12-18"), 2)   # re-signed mid-season after a waiver
        self.assertEqual(bird_seasons("2002-09-05"), 1)
        self.assertEqual([bird_status(n) for n in (1, 2, 3, 8)], ["non_bird", "early_bird", "larry_bird", "larry_bird"])

    def test_holds_follow_q28_and_cap_at_maximum(self):
        self.assertEqual(cap_hold(637435, "larry_bird", rookie_scale=False, above_average=False,
                                  max_salary=10960000, cba=CBA)[0], 1274870)
        amount, _, notes = cap_hold(20629800, "larry_bird", rookie_scale=False, above_average=True,
                                    max_salary=15344000, cba=CBA)
        self.assertEqual(amount, 15344000)
        self.assertTrue(notes)
        self.assertEqual(cap_hold(1400000, "non_bird", rookie_scale=False, above_average=False,
                                  max_salary=13152000, cba=CBA)[0], 1680000)

    def test_qualifying_offer_is_the_greater_amount(self):
        self.assertEqual(qualifying_offer(512435, 638679, CBA), (788679, "minimum salary plus $150,000"))
        self.assertEqual(qualifying_offer(2000000, 638679, CBA)[0], 2500000)
        self.assertIsNone(qualifying_offer(637435, None, CBA)[0])

    def test_restricted_eligibility(self):
        self.assertTrue(rfa_eligible("2001-02", 2, CBA))
        self.assertFalse(rfa_eligible("1995-96", 8, CBA))

    def test_miami_rights_file(self):
        by_name = {p["player"]: p for p in RIGHTS["players"]}
        self.assertEqual(len(by_name), 7)
        self.assertEqual(by_name["Mike James"]["bird_status"], "early_bird")
        self.assertEqual(by_name["Alonzo Mourning"]["cap_hold"], 21661290)   # 105% of previous salary beats the tier maximum
        self.assertEqual(by_name["Eddie House"]["qualifying_offer"], 813679)   # 3-year minimum + $150,000
        self.assertEqual(RIGHTS["total_cap_holds"], sum(p["cap_hold"] for p in RIGHTS["players"]))
        self.assertNotIn("decision", json.dumps(RIGHTS).replace("no decision", ""))


if __name__ == "__main__":
    unittest.main()
