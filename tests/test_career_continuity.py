"""Career continuity: a real player keeps playing his real path wherever Miami's moves leave him."""
import json
from pathlib import Path
import unittest

from runtime.game_requests import _club
from runtime.gm import FrontOffice
from runtime.league_cards import club_on
from runtime.market import Market
from runtime.trades import TradeDesk

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = {p["bbr_id"]: p for p in json.loads((ROOT / "career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json").read_text())["players"]
            if p.get("bbr_id")}
DAY = "2003-11-12"


class ReleasedPlayersTests(unittest.TestCase):
    def test_a_player_miami_released_is_back_on_his_real_path_in_cards_and_games(self):
        glover = club_on(REGISTRY["glovedi01"], DAY)
        self.assertEqual(glover["club"], "Atlanta Hawks")
        self.assertEqual(club_on(REGISTRY["glovedi01"], "2004-03-20")["club"], "Toronto Raptors")
        self.assertEqual(club_on(REGISTRY["hillty01"], DAY)["club"], "Philadelphia 76ers")
        hawks = _club({"team": "Atlanta Hawks", "rotation": "real"}, None, ROOT, None, "2003-04", DAY)
        self.assertIn("Dion Glover", [p.player_id for p in hawks.players])

    def test_a_void_camp_contract_never_made_the_player_miamis(self):
        self.assertEqual(club_on(REGISTRY["clarkke01"], "2003-10-15")["club"], "Utah Jazz")
        self.assertEqual(club_on(REGISTRY["anderch01"], "2003-10-15")["club"], "Denver Nuggets")


class TradeDeskTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.desk = TradeDesk(DAY, FrontOffice(DAY, Market(DAY, ROOT), ROOT), ROOT)

    def test_partner_rosters_follow_the_dated_world(self):
        self.assertIsNone(self.desk.partner_player("Milwaukee Bucks", "Sam Cassell"))     # traded June 27
        self.assertIsNotNone(self.desk.partner_player("Minnesota Timberwolves", "Sam Cassell"))
        self.assertIsNone(self.desk.partner_player("Atlanta Hawks", "Stephen Jackson"))  # Miami holds him

    def test_unsigned_draft_rights_are_not_a_roster_spot_in_a_trade(self):
        trade = {"partner": "Minnesota Timberwolves", "miami_out": ["Brian Grant"], "miami_in": ["Sam Cassell"],
                 "picks_out": [], "picks_in": []}
        self.assertFalse(any("more than" in e for e in self.desk.errors(trade, ignore_timing=True)))


class PositionTests(unittest.TestCase):
    def test_a_player_outside_the_2002_03_baseline_keeps_his_listed_position(self):
        positions = FrontOffice(DAY, Market(DAY, ROOT), ROOT)._positions()
        self.assertEqual(positions["parksch02"], "C")
        roster = json.loads((ROOT / "career/Dwyane_Wade/2003-04/00_Team/Team/Roster/roster.json").read_text())
        self.assertEqual(next(p for p in roster["players"] if p["name"] == "Cherokee Parks")["positions"], ["C"])


if __name__ == "__main__":
    unittest.main()
