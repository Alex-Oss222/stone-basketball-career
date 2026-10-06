"""Symmetric league phases 3 and 4: weekly trades between real clubs and the simulated rosters games read."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

import runtime.league_book as LB
from runtime import league_moves, league_trades
from runtime.market import Market

ROOT = Path(__file__).resolve().parents[1]
START, WEEK = "2003-12-01", "2003-12-08"


class ActivationTests(unittest.TestCase):
    def test_a_real_trade_straddling_the_switch_is_completed_and_rosters_hold_fifteen(self):
        holder, extras = league_moves._activation("2003-04", ROOT, "2003-12-03")
        self.assertEqual(holder["roseja01"], "Toronto Raptors")          # Rose-Marshall for Davis-Williams, December 1
        self.assertEqual(holder["willije01"], "Chicago Bulls")
        counts = {}
        for club in holder.values():
            counts[club] = counts.get(club, 0) + 1
        self.assertLessEqual(max(counts.values()), league_moves.ROSTER_MAX)
        protected = league_moves._protected_contracts(ROOT)
        self.assertFalse({e["bbr_id"] for e in extras} & protected)          # a real contract is never let go
        self.assertNotIn("waltolu01", {e["bbr_id"] for e in extras})        # a 72-game rookie stays
        self.assertEqual(len({*holder} & {e["bbr_id"] for e in extras}), 0)


class LeagueTradeTests(unittest.TestCase):
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

    @classmethod
    def tearDownClass(cls):
        cls.switch.stop()
        cls.tmp.cleanup()

    def test_off_by_default_and_on_only_from_its_date(self):
        self.assertTrue(LB.active(WEEK))
        self.assertFalse(LB.active("2003-11-30"))
        with self.assertRaises(ValueError):
            league_trades.LeagueTradeDesk("2003-11-30", Market("2003-11-30", self.root), self.root)

    def test_a_drawn_trade_moves_both_players_and_the_games_follow(self):
        written, executed = league_trades.weekly(self.root, WEEK)
        self.assertTrue(1 <= len(written) <= league_trades.MAX_PER_WEEK)
        deal = written[0]
        seen = set()
        for w in written:                                                    # a club or player in one deal a week
            row = json.loads((self.root / league_trades.draws_dir("2003-04") / f"{w}.proposal.json").read_text())
            keys = set(row["clubs"]) | set(row["a"]["bbr_ids"]) | set(row["b"]["bbr_ids"])
            self.assertFalse(keys & seen)
            seen |= keys
        draws = self.root / league_trades.draws_dir("2003-04")
        proposal = json.loads((draws / f"{deal}.proposal.json").read_text())
        packet = json.loads((draws / f"{deal}.decision.json").read_text())
        self.assertAlmostEqual(packet["options"]["accept"] + packet["options"]["decline"], 1.0, places=5)
        for club, gain in proposal["gain"].items():
            self.assertGreaterEqual(gain, league_trades.MIN_MUTUAL_GAIN)
        self.assertEqual(league_trades.weekly(self.root, WEEK), ([], []))           # one packet a week, nothing drawn yet
        (draws / f"{deal}.decision.result.json").write_text(json.dumps({"outcome": "accept"}))
        _, executed = league_trades.weekly(self.root, WEEK)
        self.assertEqual(executed, [deal])
        a, b = proposal["a"], proposal["b"]
        for bbr in a["bbr_ids"]:
            self.assertEqual(league_moves.club_of(bbr, WEEK, root=self.root), b["club"])
        for bbr in b["bbr_ids"]:
            self.assertEqual(league_moves.club_of(bbr, "2003-12-07", root=self.root), b["club"])  # before the date
        names = {p["player_id"] for p in league_moves.effective_roster(b["club"], WEEK, root=self.root)}
        self.assertTrue(set(a["sends"]) <= names)
        self.assertFalse(set(b["sends"]) & names)
        from runtime.league_trades import MAX_PLAYERS
        self.assertLessEqual(len(a["sends"]) + len(b["sends"]), MAX_PLAYERS)       # up to three for two
        self.assertLessEqual(max(len(a["sends"]), len(b["sends"])), 3)

    def test_no_player_miami_holds_is_ever_traded_between_real_clubs(self):
        from runtime.rotations import miami_holds
        held = miami_holds("2003-04", WEEK, self.root)
        desk = league_trades.LeagueTradeDesk(WEEK, Market(WEEK, self.root), self.root)
        for players in desk.rosters.values():
            self.assertFalse({p["bbr_id"] for p in players} & set(held))


if __name__ == "__main__":
    unittest.main()
