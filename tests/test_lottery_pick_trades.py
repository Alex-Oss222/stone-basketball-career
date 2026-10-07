"""The draft order follows Miami's simulated pick trades, which the activation-dated ownership file never sees."""
import json
import tempfile
import unittest
from pathlib import Path

from runtime import lottery

ROOT = Path(__file__).resolve().parents[1]
CODE = {"Miami Heat": "MIA", "Utah Jazz": "UTA"}


def ledger(root, picks):
    path = Path(root) / "career/Dwyane_Wade/2004-05/00_Team/Finances/draft_picks.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"picks": picks}), encoding="utf-8")


class MiamiPickTradesTests(unittest.TestCase):
    def test_traded_first_goes_to_its_last_holder(self):
        with tempfile.TemporaryDirectory() as root:
            ledger(root, [{"year": 2005, "round": 1, "owned": False, "original_club": "Miami Heat",
                           "history": [{"date": "2005-01-24", "to": "Utah Jazz", "trade": "t"}]},
                          {"year": 2005, "round": 2, "owned": True, "original_club": "Miami Heat", "history": []}])
            self.assertEqual(lottery.miami_pick_trades(root, "2004-05", 2005, CODE), {(1, "MIA"): "UTA"})

    def test_owned_pick_and_other_years_ignored(self):
        with tempfile.TemporaryDirectory() as root:
            ledger(root, [{"year": 2006, "round": 1, "owned": False, "original_club": "Miami Heat",
                           "history": [{"date": "2005-01-24", "to": "Utah Jazz"}]},
                          {"year": 2005, "round": 2, "owned": True, "original_club": "Miami Heat",
                           "history": [{"date": "2001-08-22", "event": "acquired before the career"}]}])
            self.assertEqual(lottery.miami_pick_trades(root, "2004-05", 2005, CODE), {})

    def test_recorded_2005_order_gives_miamis_first_to_utah(self):
        order = json.loads((ROOT / "career/Dwyane_Wade/2004-05/09_Draft/draft_order_2005.json").read_text())
        mia = [p for p in order["picks"] if p["original"] == "MIA"]
        self.assertEqual([(p["round"], p["owner"]) for p in mia], [(1, "UTA"), (2, "MIA")])


if __name__ == "__main__":
    unittest.main()
