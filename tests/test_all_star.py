"""All-Star selections: ballot shape, own-player exclusion, and the recorded 2004 record."""
import json
from pathlib import Path
import unittest

from runtime import all_star as A

ROOT = Path(__file__).resolve().parents[1]


class AllStarTests(unittest.TestCase):
    def test_a_ballot_fills_the_shape(self):
        scored = [("g1", 2, 0), ("g2", 1, 0), ("g3", 0.5, 0), ("f1", 1.5, 0), ("f2", 0.2, 0), ("c1", 0.1, 0)]
        positions = {"g1": "G", "g2": "G", "g3": "G", "f1": "F", "f2": "F", "c1": "C"}
        picks = A._ballot(scored, 0.0, {"G": 2, "F": 2, "C": 1}, positions)
        self.assertEqual(sorted(picks), ["c1", "f1", "f2", "g1", "g2"])

    def test_a_coach_never_votes_for_his_own_player(self):
        scored = [("g1", 3, 0), ("g2", 1, 0), ("g3", 0.5, 0)]
        positions = {n: "G" for n, *_ in scored}
        votes, _ = A.tally(scored, [("coach", 0.3)], {"G": 2}, positions, {"coach": {"g1"}})
        self.assertNotIn("g1", votes)

    def test_wild_cards_come_after_positions(self):
        votes = {"g1": 5, "g2": 4, "g3": 3, "f1": 2, "c1": 1}
        total = {n: 0.0 for n in votes}
        positions = {"g1": "G", "g2": "G", "g3": "G", "f1": "F", "c1": "C"}
        self.assertEqual(A.elect(votes, total, {"G": 1, "F": 1, "C": 1, "any": 1}, positions), ["g1", "f1", "c1", "g2"])

    def test_the_recorded_season_has_twelve_a_side(self):
        path = ROOT / "career/Dwyane_Wade/Stats_and_Awards/League/2003-04/all_star.json"
        if not path.is_file():
            self.skipTest("no record")
        record = json.loads(path.read_text())
        for conf in ("East", "West"):
            n = sum(a["conference"] == conf and a["role"] != "injury replacement" for a in record["all_stars"])
            self.assertEqual(n, 12)
        self.assertEqual([s["step"] for s in record["steps"]], ["starters", "coaches", "reserves", "rookie_challenge", "replacements"])


if __name__ == "__main__":
    unittest.main()
