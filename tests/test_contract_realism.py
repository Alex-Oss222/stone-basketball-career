"""Contract length and role pricing for markets after 2004 (runtime/contract_realism.py)."""
import json
from pathlib import Path
import unittest

from runtime import contract_realism as R

ROOT = Path(__file__).resolve().parents[1]


class LengthTests(unittest.TestCase):
    def test_prime_stars_get_long_bird_deals_and_veterans_short_ones(self):
        self.assertEqual(R.contract_years(26, 0.05, "bird"), 6)
        self.assertEqual(R.contract_years(24, 0.05, "bird"), 7)
        self.assertEqual(R.contract_years(24, 0.05, "mid_level"), 6)        # another club's player: six at most
        self.assertEqual(R.contract_years(33, 0.9, "cap_room"), 1)
        self.assertEqual(R.contract_years(30, 0.3, "non_bird"), 4)

    def test_minimum_and_early_bird_limits(self):
        self.assertEqual(R.contract_years(22, 0.1, "minimum", service=0), 2)
        self.assertEqual(R.contract_years(30, 0.1, "minimum", service=8), 1)
        self.assertEqual(R.contract_years(36, 0.9, "early_bird"), 2)

    def test_caps_agree_with_the_agreement_file(self):
        cba = json.loads((ROOT / "library/2003/league/nba_1999_cba_rules.json").read_text())["exceptions"]
        self.assertEqual(R.ROUTE_MAX_YEARS["bird"], cba["larry_bird"]["max_years"])
        self.assertEqual(R.ROUTE_MAX_YEARS["early_bird"], cba["early_bird"]["max_years"])
        self.assertEqual(R.ROUTE_MIN_YEARS["early_bird"], cba["early_bird"]["min_years"])
        self.assertEqual(R.ROUTE_MAX_YEARS["non_bird"], cba["non_bird"]["max_years"])
        self.assertEqual(R.ROUTE_MAX_YEARS["minimum"], cba["minimum"]["max_years"])


class RoleTests(unittest.TestCase):
    def test_minutes_raise_but_never_lower_a_value(self):
        table = [(m / 2, 4 + m / 4) for m in range(20, 80)]          # value rises with minutes
        low = R.role_value(6.0, 34.0, table)
        self.assertGreater(low, 6.0)
        self.assertEqual(R.role_value(30.0, 34.0, table), 30.0)
        self.assertEqual(R.role_value(6.0, None, table), 6.0)


if __name__ == "__main__":
    unittest.main()


class MarketPageTests(unittest.TestCase):
    def test_every_market_signing_is_on_its_contract_page(self):
        from runtime.free_agency_2004 import RECORD
        from runtime.player_contracts import build_contract_catalog
        from tests import live_season
        if not (ROOT / RECORD).is_file():
            self.skipTest("the summer market has not closed")
        record = json.loads((ROOT / RECORD).read_text())
        with live_season():
            catalog = build_contract_catalog(ROOT, ROOT / "career/Dwyane_Wade")
        players = catalog["players"]
        players = list(players.values()) if isinstance(players, dict) else players
        by_name = {p["name"]: p for p in players}
        checked = 0
        for e in record["events"]:
            if e["kind"] not in ("signing", "re_sign", "offer_sheet_matched") or e["player"] not in by_name:
                continue
            current = by_name[e["player"]]["current"] or {}
            if current.get("signed_on") != e["date"]:
                continue                          # a later move (a summer trade) may have followed
            self.assertEqual(current["salary_rows"][0]["salary"], e["salary"], e["player"])
            self.assertIsNone((current.get("reported_total") or {}).get("amount"), e["player"])   # no real total merged
            checked += 1
        self.assertGreater(checked, 20)
