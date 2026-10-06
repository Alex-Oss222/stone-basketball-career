"""One club answer (runtime/club_truth.py): cards, options and the contract ledger agree with the engine's rosters."""
import unittest
from pathlib import Path

from runtime import club_truth
from runtime.league_cards import club_on
from runtime.seasons import state
from runtime.write_back import registry

ROOT = Path(__file__).resolve().parents[1]


class ClubTruthTests(unittest.TestCase):
    SEASON = "2004-05"                     # the suite pins the live season to 2003-04; this answer applies from 2004-05

    def setUp(self):
        if not (ROOT / f"career/Dwyane_Wade/{self.SEASON}/current_state.json").is_file():
            self.skipTest("no 2004-05 season")
        self.on = state(self.SEASON, ROOT)["current_date"]

    def test_every_card_reads_the_engine_rosters(self):
        rosters = club_truth.rosters_on(self.on, ROOT)
        for p in registry(ROOT)["players"]:
            card = (club_on(p, self.on, root=ROOT) or {}).get("club")
            expected, _ = club_truth.holder(p.get("bbr_id"), p["name"], self.on, ROOT)
            self.assertEqual(card, expected, p["name"])
            if p.get("bbr_id") in rosters and expected != "Miami Heat":
                self.assertEqual(card, rosters[p["bbr_id"]], p["name"])     # on a roster: never a free agent

    def test_traded_away_miami_players_follow_the_departures(self):
        import json
        from runtime.league_cards import departures_path
        path = ROOT / departures_path(self.SEASON)
        if not path.is_file():
            self.skipTest("no departures")
        for e in json.loads(path.read_text())["entries"]:
            if e.get("bbr_id") and e["from"] <= self.on and (e.get("until") is None or self.on < e["until"]):
                club, _ = club_truth.holder(e["bbr_id"], e["player"], self.on, ROOT)
                self.assertEqual(club, e["club"], e["player"])


if __name__ == "__main__":
    unittest.main()
