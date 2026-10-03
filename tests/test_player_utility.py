import unittest

from runtime import player_utility as pu
from runtime.club_strength import League
from runtime.decisions import decision_errors
from runtime.market import Market
from runtime.valuation import Valuation


PLAYER = {"ask": 5000000, "years_wanted": 4, "prior_minutes": 30.0, "start_share": 0.9, "prior_club": "Boston Celtics", "age": 27}


class UtilityTests(unittest.TestCase):
    def test_weights_sum_to_one_and_follow_stage_and_trait(self):
        for age in (22, 27, 33):
            for trait in ("money", "fame", "loyalty", "winning"):
                self.assertAlmostEqual(sum(pu.weights(age, trait).values()), 1.0, places=3)
        self.assertGreater(pu.weights(33, "money")["contention"], pu.weights(22, "money")["contention"])
        self.assertGreater(pu.weights(27, "winning")["contention"], pu.weights(27, "money")["contention"])
        self.assertGreater(pu.weights(27, "loyalty")["loyalty"], pu.weights(27, "fame")["loyalty"])

    def test_scores_use_only_recorded_facts(self):
        s = pu.scores({"guaranteed": 22000000, "years": 4}, {"club": "Miami Heat", "role_minutes": 30, "strength": 45}, PLAYER)
        self.assertEqual(s["net_income"], 100)                       # Florida: no state income tax
        self.assertEqual(s["loyalty"], 50)                           # not his 2002-03 club
        self.assertEqual(s["role"], 100.0)
        home = pu.scores({"guaranteed": 22000000, "years": 4}, {"club": "Boston Celtics", "role_minutes": 30, "strength": 45}, PLAYER)
        self.assertEqual(home["loyalty"], 100)
        self.assertEqual(set(s), {"money", "security", "net_income", "role", "contention", "loyalty", "market"})

    def test_odds_are_ordered_and_sum_to_one(self):
        low, mid, high = pu.odds(-25, 1, 3), pu.odds(-3, 1, 3), pu.odds(20, 1, 3)
        for o in (low, mid, high):
            self.assertAlmostEqual(sum(o.values()), 1.0, places=3)
        self.assertGreater(low["reject"], mid.get("reject", 0))
        self.assertGreater(high["accept"], mid["accept"])
        self.assertGreater(mid["counter"], low.get("counter", 0))
        self.assertNotIn("counter", pu.odds(-3, 3, 3))                # no counter in the last round he hears

    def test_dealbreaker_is_an_established_starter_offered_the_bench(self):
        self.assertIsNotNone(pu.dealbreaker({"role_minutes": 14}, PLAYER))
        self.assertIsNone(pu.dealbreaker({"role_minutes": 26}, PLAYER))
        self.assertIsNone(pu.dealbreaker({"role_minutes": 14}, dict(PLAYER, age=33)))


class RosterTests(unittest.TestCase):
    def test_strength_line_is_fitted_on_last_season_and_moves_with_signings(self):
        v = Valuation("2003-07-03")
        league = League("2003-07-03", v.value)
        self.assertEqual(league.line["clubs"], 29)
        self.assertGreater(league.line["slope"], 0)
        self.assertGreater(league.wins("Miami Heat", add=["kiddja01"]), league.wins("Miami Heat"))
        self.assertGreater(league.wins("Los Angeles Lakers"), league.wins("Miami Heat"))
        self.assertNotIn("jonesed02", league.rosters["Phoenix Suns"])   # Miami's own players are only Miami's

    def test_answer_packet_keeps_the_decision_schema_and_explains_itself(self):
        m = Market("2003-07-03")
        found = m.assess("kiddja01", {"first_year": 11000000, "years": 3, "guaranteed": 34000000},
                         {"club": "Miami Heat", "role_minutes": 34, "ask": 10626721}, m.alternative("kiddja01"), {}, "money", "t", 1)
        self.assertEqual(decision_errors(found["packet"]), [])
        self.assertIn("projected wins", found["packet"]["basis"])
        self.assertEqual(found["analysis"]["situations"]["alternative"]["club"], "New Jersey Nets")
        self.assertIn(found["counter_focus"]["factor"], pu.CATEGORY)


if __name__ == "__main__":
    unittest.main()
