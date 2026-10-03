"""Shot creation and defensive specialization; synthetic draws never enter career records."""
from copy import deepcopy
from dataclasses import replace
import random
import unittest
from unittest.mock import patch

from runtime.kernel import (
    TRANSITION_SECONDS, PlayerInput, _Club, _defensive_split, _expected_points,
    _passing_adjustment, _transition_adjustment, _usage_adjustment, calibrate,
    team_packet, validate_result,
)
from tests.test_engine_model import ENV, RULES, games, team


def with_rate(player, key, value):
    profile = deepcopy(player.stat_profile)
    profile["rates"][key] = value
    return replace(player, stat_profile=profile)


class ShotCreationTests(unittest.TestCase):
    def setUp(self):
        self.cal = calibrate(ENV)
        self.player = team("H").players[0]

    def test_usage_costs_efficiency_relative_to_the_players_own_estimate(self):
        scorer = with_rate(self.player, "usage_pct", ENV["player_rate_baselines"]["usage_pct"] * 1.5)
        self.assertEqual(_usage_adjustment(scorer, 5, self.cal), 0)
        self.assertLess(_usage_adjustment(scorer, 4, self.cal), 0)
        self.assertGreater(_usage_adjustment(scorer, 6, self.cal), 0)
        self.assertGreaterEqual(_usage_adjustment(scorer, .1, self.cal), -.06)

    def test_better_teammate_passing_improves_shot_quality(self):
        teammates = [(p, 1) for p in team("H").players[1:5]]
        self.assertAlmostEqual(_passing_adjustment(teammates, self.cal), 0)
        strong = [(with_rate(teammates[0][0], "assist_pct", .60), 1), *teammates[1:]]
        weak = [(with_rate(teammates[0][0], "assist_pct", .01), 1), *teammates[1:]]
        self.assertGreater(_passing_adjustment(strong, self.cal), _passing_adjustment(weak, self.cal))
        # A shooter's own passing rate is deliberately absent from his shot's creators.
        self.assertEqual(_passing_adjustment(teammates, self.cal),
                         _passing_adjustment([(p, .5) for p, _ in teammates], self.cal))

    def test_expected_margin_keeps_the_playmaking_advantage(self):
        ordinary = team("H")
        gifted = replace(ordinary, players=tuple(with_rate(p, "assist_pct", .50) if p.position == "PG" else p
                                                 for p in ordinary.players))
        club = lambda t: _Club(t, "home", random.Random(0), RULES)
        opponent = club(team("A"))
        self.assertGreater(_expected_points(club(gifted), opponent, self.cal),
                           _expected_points(club(ordinary), opponent, self.cal))

    def test_increased_load_produces_more_attempts_at_lower_efficiency(self):
        ordinary = team("H")
        overloaded = replace(ordinary, players=(ordinary.players[0], *[
            with_rate(p, "usage_pct", p.stat_profile["rates"]["usage_pct"] * .5)
            for p in ordinary.players[1:]]))
        totals = {}
        for label, roster in (("normal", ordinary), ("high", overloaded)):
            lines = [next(r for r in g["player_stats"]["home"] if r["player_id"] == "H_0")
                     for g in games(roster, team("A"), 400, tag="usage-cost")]
            totals[label] = sum(r["fgm"] for r in lines), sum(r["fga"] for r in lines)
        self.assertGreater(totals["high"][1], totals["normal"][1] * 1.35)
        self.assertLess(totals["high"][0] / totals["high"][1],
                        totals["normal"][0] / totals["normal"][1] - .015)

    def test_teammate_passing_improves_the_unchanged_shooters_actual_game_efficiency(self):
        ordinary = team("H")
        totals = {}
        # Disable score compression so an analytic-margin improvement alone
        # cannot satisfy this check if passing is disconnected from live shots.
        with patch("runtime.kernel.LEAD_EFFECT", 0):
            for label, assist_rate in (("weak", .03), ("strong", .50)):
                roster = replace(ordinary, players=(ordinary.players[0], *[
                    with_rate(p, "assist_pct", assist_rate) for p in ordinary.players[1:]]))
                self.assertIs(roster.players[0], ordinary.players[0])
                lines = [next(r for r in g["player_stats"]["home"] if r["player_id"] == "H_0")
                         for g in games(roster, team("A"), 400, tag="passer-shot-quality")]
                totals[label] = sum(r["fgm"] for r in lines), sum(r["fga"] for r in lines)
        self.assertGreater(totals["strong"][0] / totals["strong"][1],
                           totals["weak"][0] / totals["weak"][1] + .02)


class ExplicitStarterTests(unittest.TestCase):
    def test_small_staff_starting_five_survives_the_fallback_position_safeguard(self):
        ordinary = team("H")
        small_positions = ("PG", "SG", "SF", "SG", "SF")
        players = tuple(replace(p, position=small_positions[i]) if i < 5 else p
                        for i, p in enumerate(ordinary.players))
        starters = tuple(p.player_id for p in players[:5])
        roster = replace(ordinary, players=players, starters=starters)
        self.assertTrue(any(p.position in ("PF", "C") for p in players[5:]))
        result = next(games(roster, team("A"), 1, tag="explicit-small-starters"))
        actual = {p["player_id"] for p in result["player_stats"]["home"] if p["started"]}
        self.assertEqual(actual, set(starters))


class DefensiveSplitTests(unittest.TestCase):
    def setUp(self):
        self.cal = calibrate(ENV)
        self.player = team("H", defense=3).players[0]

    def test_blocks_and_steals_allocate_the_same_total_defensive_budget(self):
        blocker = with_rate(self.player, "block_pct", .15)
        thief = with_rate(self.player, "steal_pct", .15)
        interior = _defensive_split(blocker, self.cal)
        perimeter = _defensive_split(thief, self.cal)
        self.assertGreater(interior[0], interior[1])
        self.assertGreater(perimeter[1], perimeter[0])
        share = self.cal["defense_three_share"]
        for split in (interior, perimeter, _defensive_split(self.player, self.cal)):
            self.assertAlmostEqual((1 - share) * split[0] + share * split[1], 3)

    def test_ungraded_estimates_do_not_gain_defense_from_event_rates(self):
        ungraded = with_rate(team("H").players[0], "block_pct", .9)
        self.assertEqual(_defensive_split(ungraded, self.cal), (0, 0))
        self.assertEqual(_defensive_split(PlayerInput("ungraded rookie", "C", 20), self.cal), (0, 0))

    def test_rebounds_do_not_enter_defensive_allocation(self):
        elite_rebounder = with_rate(with_rate(self.player, "offensive_rebound_pct", .5), "defensive_rebound_pct", .8)
        self.assertEqual(_defensive_split(elite_rebounder, self.cal), _defensive_split(self.player, self.cal))


class TransitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = list(games(team("H"), team("A"), 100, tag="transition-context"))

    def test_transition_bonus_and_clock_are_centered_on_the_league_environment(self):
        cal = calibrate(ENV)
        share = cal["transition_play_share"]
        for is_three in (False, True):
            fast = _transition_adjustment(is_three, True, cal)
            slow = _transition_adjustment(is_three, False, cal)
            self.assertGreater(fast, slow)
            self.assertAlmostEqual(share * fast + (1 - share) * slow, 0)
        self.assertGreater(cal["possession_seconds"], TRANSITION_SECONDS)

    def test_fast_breaks_have_live_sources_shorter_clock_and_better_shots(self):
        fast = {k: 0 for k in ("possessions", "after_steal", "after_rebound", "seconds", "fga", "fgm")}
        fga = fgm = 0
        for result in self.results:
            self.assertEqual(validate_result(result), [])
            for side in ("home", "away"):
                transition = result["transition_stats"][side]
                for key in fast:
                    fast[key] += transition[key]
                fga += result["team_stats"][side]["fga"]
                fgm += result["team_stats"][side]["fgm"]
        self.assertGreater(fast["after_steal"], 0)
        self.assertGreater(fast["after_rebound"], 0)
        self.assertLess(fast["seconds"] / fast["possessions"], 9)
        self.assertGreater(fast["fgm"] / fast["fga"], (fgm - fast["fgm"]) / (fga - fast["fga"]) + .03)

    def test_context_and_started_markers_replay_exactly_and_validate(self):
        self.assertEqual(self.results[0], next(games(team("H"), team("A"), 1, tag="transition-context")))
        result = deepcopy(self.results[0])
        result["transition_stats"]["home"]["after_steal"] += 1
        self.assertTrue(any("transition" in e for e in validate_result(result)))
        result = deepcopy(self.results[0])
        for row in result["player_stats"]["home"]:
            row["started"] = False
        self.assertTrue(any("starters" in e for e in validate_result(result)))
        # Older closed boxes and request packets have neither optional field.
        result = deepcopy(self.results[0])
        result.pop("transition_stats")
        for rows in result["player_stats"].values():
            for row in rows:
                row.pop("started")
        self.assertEqual(validate_result(result), [])
        self.assertNotIn("starters", team_packet(team("H")))


if __name__ == "__main__":
    unittest.main()
