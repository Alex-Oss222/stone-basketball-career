"""Rotation model 2 (rule 3 cap, reserves dress), the one-game absence draw and injury carry-over."""
import hashlib
from pathlib import Path
import unittest

from runtime import KERNEL_VERSION
from runtime.era import environment_for, rules_for
from runtime.injuries import DAYS_PER_GAME, injured_out
from runtime.kernel import ABSENCE_PER_GAME, PlayerInput, TeamInput, resolve_game
from runtime.rotations import RULE3_RAISE_CAP, ROSTER_LIMIT, real_rotation, rotation_model
from runtime.write_back import injuries_table

ROOT = Path(__file__).resolve().parents[1]


def club(*rows):
    return {"players": [{"player_id": n, "bbr_id": None, "position": "SF", "games": g, "minutes": m,
                         "span": [0.0, 1.0], "window": [0.0, 1.0]} for n, g, m in rows]}


class RotationModelTests(unittest.TestCase):
    def test_the_model_switches_on_its_date_so_played_games_keep_their_inputs(self):
        self.assertEqual(rotation_model("2003-11-11"), 1)
        self.assertEqual(rotation_model("2003-11-12"), 2)

    def test_departed_minutes_raise_no_one_more_than_the_cap(self):
        rows = [("Star", 82, 82 * 37), ("Wing", 82, 82 * 30), ("Big", 82, 82 * 28), ("Gone", 82, 82 * 36),
                ("Sixth", 82, 82 * 22), ("Seventh", 82, 82 * 18), ("Eighth", 82, 82 * 15), ("Ninth", 82, 82 * 12),
                ("Tenth", 82, 82 * 30), ("Eleventh", 82, 82 * 25), ("Twelfth", 82, 82 * 25)]      # covers a game without Gone
        legacy = real_rotation("X", club(*rows), 82, fraction=0.2, exclude={"gone"}, model=1)
        capped = real_rotation("X", club(*rows), 82, fraction=0.2, exclude={"gone"}, model=2)
        star = lambda team: next(p.minutes for p in team.players if p.player_id == "Star")
        self.assertGreater(star(legacy), 37 + RULE3_RAISE_CAP)            # the uniform factor pushed him past it
        self.assertLessEqual(star(capped), 37 + RULE3_RAISE_CAP + 1e-6)
        self.assertGreater(sum(p.minutes for p in capped.players), sum(r[2] / r[1] for r in rows if r[0] != "Gone"))

    def test_reserves_dress_at_their_minutes_per_club_game_and_a_club_carries_fifteen(self):
        rows = [(f"R{i:02d}", 82 if i <= 9 else 30, 82 * (40 - 3 * i) if i <= 9 else 30 * 8) for i in range(1, 19)]
        team = real_rotation("X", club(*rows), 82, fraction=0.5, model=2)
        self.assertEqual(len(team.players), ROSTER_LIMIT)
        reserve = next(p for p in team.players if p.player_id == "R10")
        self.assertEqual(reserve.availability, 1.0)
        self.assertAlmostEqual(reserve.minutes, 30 * 8 / 82, places=2)  # season total kept
        self.assertLess(real_rotation("X", club(*rows), 82, fraction=0.5, model=1).players[-1].availability, 1.0)

    def test_a_stint_gap_short_of_a_game_is_raised_to_regulation_in_proportion(self):
        rows = [("Star", 82, 82 * 30), ("Wing", 82, 82 * 28), ("Big", 82, 82 * 26), ("Guard", 82, 82 * 24),
                ("Fifth", 82, 82 * 22), ("Sixth", 82, 82 * 20), ("Seventh", 82, 82 * 18), ("Eighth", 82, 82 * 16)]  # 184
        team = real_rotation("X", club(*rows), 82, fraction=0.5, model=2)
        self.assertAlmostEqual(sum(p.minutes for p in team.players), 240, places=1)
        minutes = {p.player_id: p.minutes for p in team.players}
        self.assertAlmostEqual(minutes["Star"] / minutes["Eighth"], 30 / 16, places=2)
        full = [("Star", 82, 82 * 40), ("Wing", 82, 82 * 40), ("Big", 82, 82 * 40), ("Guard", 82, 82 * 40),
                ("Fifth", 82, 82 * 40), ("Sixth", 82, 82 * 40)]                                  # already 240
        self.assertEqual([p.minutes for p in real_rotation("X", club(*full), 82, fraction=0.5, model=2).players], [40.0] * 6)


class AbsenceTests(unittest.TestCase):
    def team(self, name, injuries):
        return TeamInput(name, tuple(PlayerInput(f"{name}{i}", ("PG", "SG", "SF", "PF", "C")[i % 5], 240 / 12, {}, {}, age=27)
                                     for i in range(12)), injuries=injuries)

    def test_only_the_simulated_club_draws_one_game_absences_at_the_calibrated_rate(self):
        self.assertGreaterEqual(tuple(map(int, KERNEL_VERSION.split("."))), (2003, 9))
        rules, env = rules_for("2003-04"), environment_for("2003-04", "2003-11-12")
        absent = games = 0
        for i in range(150):
            entropy = hashlib.sha256(f"absence-{i}".encode()).digest()
            result = resolve_game(self.team("M", True), self.team("R", False), entropy=entropy, event_id=f"a{i}",
                                  rules=rules, environment=env)
            self.assertTrue(all(a["side"] == "home" and a["games_out"] == 1 for a in result["absences"]))
            for a in result["absences"]:
                self.assertIn(a["player_id"], result["inactive"]["home"])
            absent += len(result["absences"])
            games += 1
        rate = absent / (games * 12)
        self.assertLess(abs(rate - ABSENCE_PER_GAME), 0.012)

    def test_the_note_names_a_one_game_absence(self):
        result = {"home": "Miami Heat", "away": "X", "injuries": [],
                  "absences": [{"side": "home", "player_id": "Mike James", "kind": "illness or personal", "games_out": 1}]}
        self.assertIn("Did not dress: Mike James", injuries_table(result))
        self.assertEqual(injuries_table({"home": "Miami Heat", "away": "X", "injuries": []}), "No Miami injury was drawn in this game.\n")


class CarryOverTests(unittest.TestCase):
    def test_a_carried_injury_counts_down_from_the_first_game(self):
        result = {"home": "Miami Heat", "away": "X", "injuries": []}
        self.assertEqual(injured_out([result, result], start={"Kemp": 5}), {"Kemp": 3})
        self.assertAlmostEqual(DAYS_PER_GAME, 170 / 82)

    def test_the_offseason_heals_what_it_can(self):
        from runtime import injuries
        from unittest import mock
        last = [{"home": "Miami Heat", "away": "X", "game_date": "2004-06-10",       # a playoff game
                 "injuries": [{"side": "home", "player_id": "Long", "games_out": 82},
                              {"side": "home", "player_id": "Short", "games_out": 10}]}]
        with mock.patch("runtime.season_games.miami_results", return_value=last), \
             mock.patch("runtime.season_games.miami_game_dates", return_value=["2004-10-05"]), \
             mock.patch("pathlib.Path.is_dir", return_value=True):
            carried = injuries.carried_in("2004-05", ROOT)
        self.assertNotIn("Short", carried)                      # healed over the summer
        self.assertEqual(carried["Long"], round((82 * DAYS_PER_GAME - 117) / DAYS_PER_GAME))


if __name__ == "__main__":
    unittest.main()
