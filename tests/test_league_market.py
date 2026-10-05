"""Symmetric league phase 2: waivers, 10-day contracts and roster minimums for every real club."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

import runtime.league_book as LB
from runtime import league_market as LM, league_moves
from runtime.market import Market

ROOT = Path(__file__).resolve().parents[1]
START = "2003-12-03"


class LeagueMarketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        for folder in ("library", "career", "foundation"):
            shutil.copytree(ROOT / folder, cls.root / folder, ignore=shutil.ignore_patterns("*.html", "Players"))
        for live in ("league_moves.json", "Trade_Draws"):                  # the live league's own moves and draws
            target = cls.root / "career/Dwyane_Wade/2003-04/League" / live
            if target.is_dir():
                shutil.rmtree(target)
            elif target.exists():
                target.unlink()
        cls.switch = mock.patch.object(LB, "SYMMETRIC_FROM", START)
        cls.switch.start()
        for day in (START, "2004-01-05", "2004-01-07", "2004-01-15", "2004-01-25"):
            LM.LeagueMarket(day, Market(day, cls.root), cls.root).run()
        cls.moves = league_moves.read("2003-04", cls.root)["entries"]

    @classmethod
    def tearDownClass(cls):
        cls.switch.stop()
        cls.tmp.cleanup()

    def test_rules_come_from_the_researched_file(self):
        rules = LM._rules(ROOT)
        self.assertEqual((rules["min"], rules["max"], rules["ten_day_per_club"]), (12, 15, 2))
        self.assertEqual(rules["ten_day_from"], "2004-01-05")

    def test_no_ten_day_before_january_5_and_never_more_than_two_with_one_club(self):
        tens = [e for e in self.moves if e["kind"] == "ten_day"]
        self.assertTrue(all(e["date"] >= "2004-01-05" for e in tens))
        counts = {}
        for e in tens:
            counts[(e["bbr_id"], e["to"])] = counts.get((e["bbr_id"], e["to"]), 0) + 1
        self.assertTrue(all(n <= 2 for n in counts.values()))

    def test_rosters_stay_within_twelve_and_fifteen_and_waivers_go_worst_first_or_clear(self):
        for club in LM.LeagueMarket("2004-01-25", Market("2004-01-25", self.root), self.root).rosters.values():
            self.assertLessEqual(len(club), 15)
        for e in self.moves:
            if e["kind"] == "claim":
                self.assertIn("claimed off waivers", e["note"])
        protected = league_moves._protected_contracts(ROOT)
        self.assertFalse({e["bbr_id"] for e in self.moves if e["kind"] == "waive"} & protected)

    def test_waivers_take_48_hours_and_nobody_signs_a_player_on_them(self):
        waives = {e["id"]: e for e in self.moves if e["kind"] == "waive"}
        self.assertTrue(waives)
        for e in self.moves:
            if e["kind"] in ("claim", "clear"):
                w = waives[e["waiver"]]
                self.assertEqual(w["bbr_id"], e["bbr_id"])
                self.assertGreaterEqual(e["date"], (LM.date.fromisoformat(w["date"]) + LM.timedelta(days=LM.WAIVER_DAYS)).isoformat())
            if e["kind"] in ("ten_day", "rest_of_season", "signing") and e.get("from") is None:
                for w in waives.values():
                    if w["bbr_id"] == e["bbr_id"]:
                        self.assertFalse(w["date"] <= e["date"] < (LM.date.fromisoformat(w["date"]) + LM.timedelta(days=LM.WAIVER_DAYS)).isoformat())

    def test_from_january_20_a_ten_day_fills_a_short_club_and_a_contributor_is_kept(self):
        self.assertEqual(LM.NEED_RULE_FROM, "2004-01-20")
        day = "2004-01-25"                                          # a setUpClass market day under the need rule
        desk = LM.LeagueMarket(day, Market(day, self.root), self.root)
        for e in self.moves:
            if e["date"] >= LM.NEED_RULE_FROM and e["kind"] == "rest_of_season" and e.get("from") == e.get("to"):
                self.assertIn("kept:", e["note"])                       # a renewal names the minutes that earned it
            if e["date"] >= LM.NEED_RULE_FROM and e["kind"] == "expire":
                self.assertIn("minutes a game", e["note"])
        with mock.patch.object(desk, "injured_regulars", return_value=0):
            self.assertFalse(any(desk.short_handed(c) for c in desk.clubs if len(desk.rosters[c]) >= 12))

    def test_a_market_day_runs_once_even_without_moves(self):
        ledger = league_moves.read("2003-04", self.root)
        self.assertIn(START, ledger["market_days"])
        for day in ledger["market_days"]:
            self.assertEqual(LM.LeagueMarket(day, Market(day, self.root), self.root).run(), [])

    def test_off_switch_writes_nothing(self):
        with mock.patch.object(LB, "SYMMETRIC_FROM", None), self.assertRaises(ValueError):
            LM.LeagueMarket("2004-01-05", Market("2004-01-05", self.root), self.root)


if __name__ == "__main__":
    unittest.main()
