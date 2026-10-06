"""FIBA tournament mechanics (runtime/fiba_tournament.py) and the national pipeline's pure parts (runtime/national.py)."""
import unittest

from runtime.fiba_tournament import apply_draws, group_table, resolve_slot


def g(home, away, hs, as_, stage="group_A"):
    return {"home": home, "away": away, "home_score": hs, "away_score": as_, "stage": stage}


class StandingsTests(unittest.TestCase):
    def test_points_two_for_a_win_one_for_a_loss(self):
        table = group_table(["A", "B"], [g("A", "B", 80, 70)])
        self.assertEqual([(r["team"], r["pts"], r["position"]) for r in table], [("A", 2, 1), ("B", 1, 2)])

    def test_three_way_tie_is_broken_among_the_tied_teams(self):
        games = [g("A", "B", 80, 70), g("B", "C", 75, 70), g("C", "A", 72, 70),
                 g("A", "D", 90, 60), g("B", "D", 88, 60), g("C", "D", 85, 60)]
        table = group_table(["A", "B", "C", "D"], games)
        # Among A, B, C: A +8, C -3, B -5 (point difference in their games against each other).
        self.assertEqual([r["team"] for r in table], ["A", "C", "B", "D"])
        self.assertEqual([r["position"] for r in table], [1, 2, 3, 4])

    def test_two_way_tie_goes_to_the_head_to_head_winner(self):
        # A and B 2-1 (B beat A), C and D 1-2 (D beat C), whatever the margins elsewhere.
        games = [g("A", "C", 90, 50), g("A", "D", 90, 50), g("B", "A", 61, 60), g("B", "D", 70, 69),
                 g("C", "B", 71, 70), g("D", "C", 66, 65)]
        table = group_table(["A", "B", "C", "D"], games)
        self.assertEqual([r["team"] for r in table], ["B", "A", "D", "C"])

    def test_unbreakable_tie_waits_for_an_engine_draw(self):
        games = [g("A", "B", 80, 70), g("B", "C", 80, 70), g("C", "A", 80, 70)]
        table = group_table(["A", "B", "C"], games)
        self.assertTrue(all(r["position"] is None for r in table))
        self.assertIsNone(apply_draws(table, {}))
        drawn = apply_draws(table, {("A", "B", "C"): ["C", "A", "B"]})
        self.assertEqual([(r["team"], r["position"]) for r in drawn], [("C", 1), ("A", 2), ("B", 3)])


class SlotTests(unittest.TestCase):
    def test_slots(self):
        tables = {"A": [{"team": "Spain", "position": 1}, {"team": "Greece", "position": 2}], "QR": None}
        self.assertEqual(resolve_slot("A2", tables, {}, {}), "Greece")
        self.assertIsNone(resolve_slot("QR1", tables, {}, {}))
        self.assertEqual(resolve_slot("W:41", tables, {"41": "Spain"}, {}), "Spain")
        self.assertIsNone(resolve_slot("L:41", tables, {}, {}))


class RotationTests(unittest.TestCase):
    def test_twelve_fill_two_hundred_minutes(self):
        from runtime.national import MINUTES_BY_RANK, rotation
        players = [{"player": f"P{i}", "trust": 30 - i} for i in range(12)]
        rows = rotation(players)
        self.assertEqual(sum(r["minutes"] for r in rows), 200)
        self.assertEqual([r["minutes"] for r in rows], list(MINUTES_BY_RANK))
        self.assertEqual(rows[0]["player"], "P0")

    def test_a_short_roster_still_covers_the_game(self):
        from runtime.national import rotation
        rows = rotation([{"player": f"P{i}", "trust": 30 - i} for i in range(10)])
        self.assertAlmostEqual(sum(r["minutes"] for r in rows), 200)
        self.assertTrue(all(r["minutes"] <= 40 for r in rows))

    def test_committee_invites_by_positional_need_first(self):
        from runtime.national import invite_order
        board = ([{"player": f"G{i}", "group": "G", "score": 20 - i} for i in range(6)]
                 + [{"player": f"F{i}", "group": "F", "score": 10 - i} for i in range(5)]
                 + [{"player": f"C{i}", "group": "C", "score": 5 - i} for i in range(3)])
        board.sort(key=lambda r: -r["score"])
        order = [r["player"] for r in invite_order(board)]
        self.assertEqual(order[:10], ["G0", "G1", "G2", "G3", "F0", "F1", "F2", "F3", "C0", "C1"])


class EngineRulesTests(unittest.TestCase):
    def test_fiba_rules_by_date(self):
        from runtime.era import ability_season, national_rules
        r = national_rules("2006-08-20")
        self.assertEqual((r["quarter_minutes"], r["foul_out_limit"], r["three_point_m"], r["season"]), (10, 5, 6.25, "2005-06"))
        self.assertEqual(national_rules("2014-09-01")["three_point_m"], 6.75)
        self.assertEqual(ability_season("2006-08-20"), "2005-06")
        self.assertEqual(ability_season("2017-11-24"), "2017-18")

    def test_minutes_allocation_scales_with_game_length(self):
        from runtime.kernel import PlayerInput, _allocate
        players = [PlayerInput(f"p{i}", "SF", 20.0) for i in range(8)]
        nba = _allocate(players, 240)
        fiba = _allocate(players, 200, 40)
        self.assertAlmostEqual(sum(nba.values()), 240)
        self.assertAlmostEqual(sum(fiba.values()), 200)
        self.assertTrue(max(fiba.values()) <= 40)

    def test_fiba_court_geometry(self):
        from runtime.spatial_shots import classify_spatial_zone
        from runtime.shot_chart import GEOMETRIES, classify_zone
        fiba = GEOMETRIES["fiba_2006_feet_from_basket"]
        self.assertEqual(classify_zone(0, 21.5, fiba), "three")       # beyond 6.25 m
        self.assertNotEqual(classify_zone(0, 21.5), "three")          # inside the NBA's 23.75 ft arc
        self.assertEqual(classify_spatial_zone(21.0, 1.0, fiba), "arc_three")      # past the line, level with the rim
        self.assertEqual(classify_spatial_zone(21.0, 1.0), "distance_16_three")    # a long two on an NBA court



class BuiltEditionsTests(unittest.TestCase):
    def test_engine_editions_match_a_fresh_build(self):
        import subprocess, sys
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        out = subprocess.run([sys.executable, str(root / "scripts/build_fiba_engine.py"), "--check"], cwd=root,
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)

    def test_eligibility_follows_the_date_a_player_changed_country(self):
        from runtime.national import non_usa
        self.assertNotIn("kamanch01", non_usa("2006-08-17"))          # Germany from July 2008
        self.assertIn("kamanch01", non_usa("2008-07-20"))
        self.assertIn("nowitdi01", non_usa("2006-08-17"))


if __name__ == "__main__":
    unittest.main()
