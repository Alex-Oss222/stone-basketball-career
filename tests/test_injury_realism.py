"""Item 19-21: injuries during the game, the return window, real clubs' absence spells, Early Bird limit and
Required Tenders."""
import hashlib
import json
from pathlib import Path
import unittest

from runtime.absence_spells import SPELLS_FROM, plan
from runtime.cba import rules, terms_errors
from runtime.era import environment_for, rules_for
from runtime.injuries import RETURN_MINUTES, returning_from
from runtime.kernel import PlayerInput, TeamInput, resolve_game, team_errors, team_packet
from runtime.season_games import return_restrictions

ROOT = Path(__file__).resolve().parents[1]


def team(name, injuries, returning=0):
    return TeamInput(name, tuple(PlayerInput(f"{name}{i}", ("PG", "SG", "SF", "PF", "C")[i % 5], 240 / 12, {}, {}, age=33,
                                             returning=returning if i == 0 else 0) for i in range(12)), injuries=injuries)


class InGameInjuryTests(unittest.TestCase):
    def test_a_player_hurt_in_a_period_sits_out_the_rest_of_the_game(self):
        rules_, env = rules_for("2003-04"), environment_for("2003-04", "2003-11-12")
        seen = 0
        for i in range(400):
            result = resolve_game(team("M", True), team("R", False), entropy=hashlib.sha256(f"inj-{i}".encode()).digest(),
                                  event_id=f"i{i}", rules=rules_, environment=env)
            for injury in result["injuries"]:
                self.assertEqual(injury["side"], "home")
                self.assertIn(injury["period"], range(1, 4 + result["overtimes"] + 1))
                if injury["period"] < 4:
                    seen += 1
            if seen >= 3:
                break
        self.assertGreaterEqual(seen, 1)          # injuries now happen before the final quarter, not only after the game

    def test_the_return_field_is_validated_and_absent_from_historical_packets(self):
        self.assertNotIn("returning", team_packet(team("M", True))["players"][0])
        self.assertEqual(team_packet(team("M", True, returning=2))["players"][0]["returning"], 2)
        self.assertTrue(team_errors(team("M", True, returning=11), rules_for("2003-04")))


class ReturnWindowTests(unittest.TestCase):
    def game(self, injuries=()):
        return {"home": "Miami Heat", "away": "X", "injuries": [{"side": "home", **i} for i in injuries]}

    def test_a_long_injury_opens_a_ten_game_return_window_and_a_short_one_does_not(self):
        games = [self.game([{"player_id": "A", "games_out": 8}, {"player_id": "B", "games_out": 2}])] + [self.game()] * 8
        back = returning_from(games)
        self.assertEqual(back.get("A"), 1)          # next game is his first back
        self.assertNotIn("B", back)
        self.assertEqual(returning_from(games + [self.game()] * 9).get("A"), 10)
        self.assertNotIn("A", returning_from(games + [self.game()] * 10))

    def test_the_first_games_back_are_restricted_and_the_minutes_still_add_up(self):
        players = [{"player_id": n, "minutes": m} for n, m in (("A", 34), ("B", 34), ("C", 34), ("D", 34), ("E", 34),
                                                              ("F", 30), ("G", 20), ("H", 20))]
        games = [self.game([{"player_id": "A", "games_out": 8}])] + [self.game()] * 8
        out = return_restrictions(players, games, "2003-04", ROOT)
        a = next(p for p in out if p["player_id"] == "A")
        self.assertEqual(a["returning"], 1)
        self.assertAlmostEqual(a["minutes"], 34 * RETURN_MINUTES[0], places=1)
        self.assertAlmostEqual(sum(p["minutes"] for p in out), 240, places=1)


class SpellTests(unittest.TestCase):
    def test_spells_keep_the_real_total_and_come_in_runs(self):
        ref = hashlib.sha256(b"spell").hexdigest()
        out = plan(ref, 82, 30)
        self.assertEqual(len(out), 30)
        self.assertEqual(out, plan(ref, 82, 30))      # the journaled reference fixes the layout
        runs = sum(1 for i in sorted(out) if i - 1 not in out)
        self.assertLess(runs, 30)                    # runs, not thirty single games
        self.assertEqual(SPELLS_FROM, "2003-11-12")


class RulesTests(unittest.TestCase):
    def test_early_bird_is_limited_to_the_greater_of_175_percent_and_the_average_salary(self):
        cap = json.loads((ROOT / "library/2003/league/nba_2003_04_cap_rules.json").read_text())
        errors = terms_errors({"schedule": [6000000, 6750000]}, route="early_bird", years_of_service=3, prior_salary=1000000,
                              cap_rules=cap, cba=rules())
        self.assertTrue(any("early bird" in e for e in errors))
        self.assertEqual(terms_errors({"schedule": [4917000, 5531625]}, route="early_bird", years_of_service=3,
                                      prior_salary=1000000, cap_rules=cap, cba=rules()), [])

    def test_unsigned_picks_need_a_tender_in_its_window(self):
        from runtime import draft_rights
        self.assertEqual(draft_rights.draft_rights_errors(ROOT), [])
        tenders = {t["player"]: t for t in json.loads((ROOT / draft_rights.TENDERS).read_text())["tenders"]}
        self.assertEqual(tenders["Jerome Beasley"]["round"], 2)
        start, end = draft_rights.window(2)
        self.assertTrue(start <= tenders["Jerome Beasley"]["date"] <= end)
        self.assertLessEqual(tenders["Dwyane Wade"]["date"], draft_rights.FIRST_ROUND_BY)


if __name__ == "__main__":
    unittest.main()
