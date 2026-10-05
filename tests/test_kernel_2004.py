"""Roadmap 18a: the 2004-05 engine changes are gated by season and leave 2003-04 untouched."""
import unittest

from runtime import kernel


def result(season, seconds, stl):
    row = {"player_id": "a", "seconds": seconds, "pts": 0, "fga": 0, "fta": 0, "orb": 0, "drb": 0, "ast": 0,
           "stl": stl, "blk": 0, "tov": 0, "pf": 0}
    return {"season": season, "player_stats": {"home": [row], "away": []}}


class Kernel2004Tests(unittest.TestCase):
    def test_gate(self):
        self.assertFalse(kernel._new_era("2003-04"))
        self.assertTrue(kernel._new_era("2004-05"))
        self.assertEqual(kernel.USAGE_EXPONENT, 1.15)

    def test_credited_player_under_a_second(self):
        self.assertEqual(len(kernel.credited_time_errors(result("2004-05", 0.0, 1))), 1)
        self.assertEqual(kernel.credited_time_errors(result("2004-05", 1.0, 1)), [])
        self.assertEqual(kernel.credited_time_errors(result("2004-05", 0.0, 0)), [])
        self.assertEqual(kernel.credited_time_errors(result("2003-04", 0.0, 1)), [])   # 2003-04 results stand as played


if __name__ == "__main__":
    unittest.main()
