"""Injury types from the researched sheet (runtime/injury_types.py)."""
import unittest

from runtime.injury_types import fit, options, packet_for
from runtime.decisions import decision_errors


class InjuryTypeTests(unittest.TestCase):
    def test_options_are_a_valid_decision_and_fit_the_length(self):
        for games, kind in ((1, "injury"), (5, "injury"), (36, "injury"), (70, "injury"), (1, "illness")):
            o = options(games, kind)
            self.assertGreaterEqual(len(o), 2)
            self.assertAlmostEqual(sum(o.values()), 1.0, places=6)
            self.assertTrue(all(0 < v < 1 for v in o.values()))
        self.assertNotIn("torn_acl", options(2, "injury"))          # a torn ACL never costs two games
        self.assertNotIn("ankle_sprain_incl_high_ankle_sprain", options(70, "injury"))

    def test_fit_bands(self):
        g = {"min": 1, "p25": 3, "typical": 7, "p75": 17, "max": 34, "fastest_recorded": 1, "slowest_recorded": 38}
        self.assertEqual(fit(10, g), 1.0)
        self.assertEqual(fit(30, g), 0.4)
        self.assertEqual(fit(37, g), 0.1)
        self.assertEqual(fit(60, g), 0.0)

    def test_packet_is_a_decision(self):
        r = {"season": "2004-05", "event_id": "2004-12-21-boston-celtics-at-miami-heat", "game_date": "2004-12-21"}
        p = packet_for(r, {"player_id": "Dwyane Wade", "kind": "long", "games_out": 36}, "injury")
        self.assertEqual(decision_errors(p), [])


if __name__ == "__main__":
    unittest.main()
