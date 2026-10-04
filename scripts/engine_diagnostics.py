#!/usr/bin/env python3
"""Engine diagnostics: play the real 2003-04 schedule between real rosters and compare with benchmarks.

Analysis only. Games here are resolved with made-up entropy and are never
written anywhere: career results come only from the Railway engine
(AGENTS.md, "Game engine"). Real-player development swings are stand-in draws
from a hash of the player id, for the same reason. Every non-Miami game of the
schedule is played on its date with both clubs' real rotations on that date
(`runtime/rotations.py`), so traded players are with one club at a time.

Usage: python scripts/engine_diagnostics.py [seasons] [--defense-test | --home-test]
       python scripts/engine_diagnostics.py 4 --check --summary-json /tmp/engine-summary.json

Output contains league aggregates only. Diagnostic games are not career
results or evidence available to the front office (AGENTS.md, option C).

Benchmarks are general NBA figures for the era (judgement, not 2003-04
results): final-margin SD about 13-14, overtime in about 6% of games, 0.2-0.3
foul-outs per game, spread of team average margins over a season about 4-5,
home win rate about 60%.
"""
import argparse
import collections
import hashlib
import json
import math
import statistics
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.era import environment_for, rules_for
from runtime import KERNEL_VERSION
from runtime.injuries import rest_days
from runtime.kernel import resolve_game, validate_result
from runtime.player_stats import load_rating_index
from runtime.rotations import club_pace, load_rosters, miami_holds, real_rotation, season_fraction
from runtime.schedule import games_per_team, schedule_path
from runtime.shot_events import spatial_result_errors
from runtime.spatial_shots import (SPATIAL_ZONES, load_spatial_environment,
                                   tracking_metadata, zone_probabilities)
from runtime.trajectories import develop_profile, needs_development

SEASON, DATE = "2003-04", "2003-11-05"
BENCHMARKS = {"margin SD": (13, 14), "overtime rate": (0.05, 0.07), "foul-outs per game": (0.2, 0.3),
              "team net SD": (4, 5), "home win rate": (0.57, 0.63)}
BOX_TARGETS = (("pts", "points", .03), ("fga", "fga", .03), ("tpa", "three_pa", .06),
               ("fta", "fta", .06), ("tov", "tov", .06), ("orb", "orb", .06),
               ("drb", "drb", .06), ("ast", "ast", .06), ("stl", "stl", .06),
               ("blk", "blk", .06), ("pf", "pf", .06))


class SpatialDiagnostics:
    """Aggregate native model bands without retaining diagnostic game results."""

    def __init__(self, environment):
        self.environment = environment
        self.metadata = tracking_metadata(environment)
        self.games = 0
        self.attempts, self.makes = collections.Counter(), collections.Counter()

    def add(self, result):
        errors = spatial_result_errors(result)
        if errors:
            raise ValueError("invalid diagnostic shot feed: " + "; ".join(errors))
        if result.get("shot_tracking") != self.metadata:
            raise ValueError("diagnostic shot feed has missing or different spatial provenance")
        self.games += 1
        for shot in result["shots"]:
            self.attempts[shot["zone"]] += 1
            self.makes[shot["zone"]] += shot["made"]

    def summary(self):
        errors, zones = [], {}
        rows = {zone["id"]: zone for zone in self.environment["zones"]}
        value_totals = {value: sum(self.attempts[zone] for zone, row in rows.items()
                                   if row["shot_value"] == value) for value in (2, 3)}
        all_attempts = sum(value_totals.values())
        for zone in SPATIAL_ZONES:
            row = rows[zone]
            attempts, makes = self.attempts[zone], self.makes[zone]
            n, p = value_totals[row["shot_value"]], row["attempt_share_within_value"]
            share = attempts / n if n else None
            # Independent zone draws are conditional on shot value. Five
            # binomial standard errors plus one count allow sampling noise;
            # even across six tests the normal-tail false-alarm bound is
            # below 4e-6. This is not an empirical tuning tolerance.
            tolerance = 5 * math.sqrt(p * (1 - p) / n) + 1 / n if n else None
            zones[zone] = {"shot_value": row["shot_value"], "attempts": attempts,
                           "makes": makes, "fg_pct": makes / attempts if attempts else None,
                           "share_all_attempts": attempts / all_attempts if all_attempts else None,
                           "share_within_value": share, "source_share_within_value": p,
                           "share_tolerance": tolerance, "source_fg_pct": row["fg_pct"]}
            if not n:
                errors.append(f"spatial {row['shot_value']}-point attempts are absent")
            elif abs(share - p) > tolerance:
                errors.append(f"spatial {zone}: share {share:.6f} outside {p:.6f} +/- {tolerance:.6f}")
        # Exercise the water-filling bounds as well as normal NBA make rates.
        # Zone FG% differs with each player's base ability, defense and game
        # situation; its weighted mean must preserve that exact base target.
        targets = (0, .000001, .001, .01, .1, .25, .4, .5, .6, .75, .9, .99, .999, .999999, 1)
        mean_error = max(abs(sum(weight * probability for _, weight, probability
                                 in zone_probabilities(self.environment, value, target)) - target)
                         for value in (2, 3) for target in targets)
        if mean_error > 1e-12:
            errors.append(f"spatial weighted make probabilities do not preserve base target: {mean_error}")
        return {"games_with_complete_tracking": self.games, "attempts": all_attempts,
                "makes": sum(self.makes.values()), "attempts_by_value": value_totals,
                "tracking": self.metadata, "source_season": self.environment["season"],
                "source_provenance": self.environment["provenance"], "zones": zones,
                "conditional_share_check": "5 binomial standard errors plus one attempt",
                "max_weighted_make_probability_error": mean_error,
                "calibration_errors": sorted(set(errors))}


class League:
    """Real rotations on each scheduled date, with stand-in development swings."""

    def __init__(self):
        self.index = load_rating_index(DATE, SEASON, ROOT)
        self.rosters = load_rosters(SEASON, ROOT)

        schedule = json.loads(schedule_path(SEASON, ROOT).read_text(encoding="utf-8"))["games"]
        self.games = [g for g in schedule if "Miami Heat" not in (g["home"], g["away"])]
        self.cache, self.profiles = {}, {}

    def profile(self, p):
        key = p.stat_profile.get("bbr_id")
        if key not in self.profiles:
            ref = hashlib.sha256(f"diagnostic:{key}".encode()).hexdigest()
            self.profiles[key] = develop_profile(p.stat_profile, {SEASON: ref})
        return self.profiles[key]

    def team(self, name, game_date, shift=None):
        fraction = season_fraction(SEASON, game_date, ROOT)
        team = real_rotation(name, self.rosters[name], games_per_team(SEASON, name), self.index,
                             fraction=fraction, exclude=miami_holds(SEASON, game_date, ROOT), pace=club_pace(SEASON, name, ROOT))
        team = replace(team, rest_days=rest_days(SEASON, name, game_date, ROOT))
        key = (name, tuple(p.player_id for p in team.players), tuple(p.availability for p in team.players), shift,
               team.rest_days)
        if key not in self.cache:
            players = []
            for p in team.players:
                if p.stat_profile and needs_development(p.stat_profile):
                    profile = self.profile(p)
                    if shift:
                        profile = dict(profile, defense=profile["defense"] + shift)
                    p = replace(p, stat_profile=profile)
                players.append(p)
            self.cache[key] = replace(team, players=tuple(players))
        return self.cache[key]


def play(league, seasons, venue="home", better=None, spatial_environment=None):
    """Every non-Miami game of the schedule, `seasons` times with fresh entropy.
    `better`: clubs whose players are all one point better on defense."""
    rules, env = rules_for(SEASON), environment_for(SEASON, DATE)
    if spatial_environment is None:
        spatial_environment = load_spatial_environment(SEASON, DATE, ROOT)
    shift = lambda name: 1.0 if better and name in better else None
    for s in range(seasons):
        for g in league.games:
            home = league.team(g["home"], g["date"], shift(g["home"]))
            away = league.team(g["away"], g["date"], shift(g["away"]))
            event = f"diag-{s}-{g['game_id']}"
            result = resolve_game(home, away, entropy=hashlib.sha256(event.encode()).digest(), event_id=event,
                                  rules=rules, environment=env, venue=venue,
                                  spatial_environment=spatial_environment)
            errors = validate_result(result)
            if errors:
                raise SystemExit(f"invalid result: {errors}")
            yield s, result


def report(league, seasons):
    env = environment_for(SEASON, DATE)["averages"]
    margins, overtimes, home_wins, foul_outs = [], 0, 0, 0
    season_margins = collections.defaultdict(lambda: collections.defaultdict(list))
    totals, lines = collections.defaultdict(list), collections.defaultdict(list)
    transitions = collections.Counter()
    spatial = SpatialDiagnostics(load_spatial_environment(SEASON, DATE, ROOT))
    for s, g in play(league, seasons, spatial_environment=spatial.environment):
        spatial.add(g)
        h, a = g["final_score"]["home"], g["final_score"]["away"]
        margins.append(h - a)
        season_margins[s][g["home"]].append(h - a)
        season_margins[s][g["away"]].append(a - h)
        overtimes += g["overtimes"] > 0
        home_wins += h > a
        for side in ("home", "away"):
            for key, value in g.get("transition_stats", {}).get(side, {}).items():
                if isinstance(value, (int, float)):
                    transitions[key] += value
        for side in ("home", "away"):
            for key, value in g["team_stats"][side].items():
                totals[key].append(value)
            for row in g["player_stats"][side]:
                foul_outs += row["fouled_out"]
                if row["seconds"] > 0:
                    lines[(g[side], row["player_id"])].append(row["minutes"])
    games = len(margins)
    # Spread of club average margins within a season, the way a standings table shows it.
    spreads = [statistics.pvariance([statistics.mean(v) for v in clubs.values()]) for clubs in season_margins.values()]
    per_club = statistics.mean(len(v) for clubs in season_margins.values() for v in clubs.values())
    out = {
        "points": statistics.mean(totals["pts"]),
        "margin SD": statistics.pstdev(margins),
        "mean absolute margin": statistics.mean(abs(m) for m in margins),
        "overtime rate": overtimes / games,
        "home win rate": home_wins / games,
        "home margin": statistics.mean(margins),
        "foul-outs per game": foul_outs / games,
        "team net SD": statistics.mean(spreads) ** 0.5,
    }
    print(f"{seasons} season(s) of the real {SEASON} schedule without Miami: {games} games, "
          f"{per_club:.0f} per club per season")
    for key, value in out.items():
        bench = BENCHMARKS.get(key)
        print(f"  {key:<22} {value:7.3f}" + (f"   benchmark {bench[0]}-{bench[1]}" if bench else ""))
    print(f"  home margin standard error {statistics.pstdev(margins) / games ** 0.5:.2f} "
          "(use --home-test for a paired measurement)")
    print("  per team per game, simulated vs environment:")
    for key, target, _ in BOX_TARGETS:
        print(f"    {key:<4} {statistics.mean(totals[key]):6.1f}  {env[target]:6.1f}")
    shooting = {key: sum(totals[made]) / max(1, sum(totals[attempted]))
                for key, made, attempted in (("fg_pct", "fgm", "fga"), ("three_pct", "tpm", "tpa"),
                                              ("ft_pct", "ftm", "fta"))}
    for key, value in shooting.items():
        print(f"    {key:<9} {value:.4f}  {env[key]:.4f}")
    print(f"    possessions {statistics.mean(totals['possessions']):.1f} (published pace {env['pace']})")
    inputs = {(name, p["player_id"]): p["minutes"] / max(1, p["games"])
              for name, club in league.rosters.items() for p in club["players"]}
    regulars = [(statistics.mean(v), inputs[k]) for k, v in lines.items()
                if len(v) >= 20 * seasons and inputs.get(k, 0) >= 30]
    print(f"  players with 30+ input minutes per game: simulated {statistics.mean(m for m, _ in regulars):.1f}, "
          f"input {statistics.mean(i for _, i in regulars):.1f}, mean absolute gap "
          f"{statistics.mean(abs(m - i) for m, i in regulars):.1f} ({len(regulars)} player stints)")
    over = sum(1 for v in lines.values() for m in v if m > 44) / games
    print(f"  player-games over 44 minutes per game: {over:.2f}")
    box = {key: statistics.mean(values) for key, values in totals.items()}
    errors = [f"{key}: {box[key]:.3f} outside {env[target]:.3f} +/- {tolerance:.0%}"
              for key, target, tolerance in BOX_TARGETS
              if abs(box[key] / env[target] - 1) > tolerance]
    errors += [f"{key}: {value:.4f} outside {env[key]:.4f} +/- 0.0100"
               for key, value in shooting.items() if abs(value - env[key]) > .01]
    spatial_summary = spatial.summary()
    if spatial_summary["games_with_complete_tracking"] != games:
        errors.append("spatial tracking did not cover every diagnostic game")
    if spatial_summary["attempts"] != sum(totals["fga"]) or spatial_summary["makes"] != sum(totals["fgm"]):
        errors.append("spatial totals do not reconcile with league field goals")
    errors += spatial_summary["calibration_errors"]
    print(f"  spatial tracking: {spatial_summary['games_with_complete_tracking']}/{games} games, "
          f"{spatial_summary['attempts']} attempts, prior {spatial_summary['tracking']['prior_sha256']}")
    print("  native spatial bands: attempts, FG%, share within shot value (source share)")
    for zone, row in spatial_summary["zones"].items():
        print(f"    {zone:<20} {row['attempts']:7d}  {row['fg_pct']:.4f}  "
              f"{row['share_within_value']:.4f} ({row['source_share_within_value']:.4f})")
    return {"kernel": KERNEL_VERSION, "season": SEASON, "baseline_season": "2002-03",
            "seasons": seasons, "games": games, "metrics": out, "box_per_team": box,
            "shooting": shooting, "environment": env, "calibration_errors": errors,
            "spatial": spatial_summary,
            "transitions_per_team": {key: value / (games * 2) for key, value in transitions.items()}}


def defense_test(league, seasons):
    """Every player of half the clubs one point better on defense (+5 on the floor), same games."""
    better = set(sorted(league.rosters)[::2])
    def allowed(results):
        pts = poss = 0
        for _, g in results:
            for side, opp in (("home", "away"), ("away", "home")):
                if g[side] in better:
                    pts += g["final_score"][opp]
                    poss += g["team_stats"][opp]["possessions"]
        return 100 * pts / poss
    base, changed = list(play(league, seasons)), list(play(league, seasons, better=better))
    print(f"defense +5 on the floor: {allowed(changed) - allowed(base):+.2f} points allowed per 100 "
          f"({seasons} season(s), same games)")
    return {"kernel": KERNEL_VERSION, "seasons": seasons, "games": len(base),
            "defense_change_per_100": allowed(changed) - allowed(base)}


def home_test(league, seasons):
    """Home minus neutral-site margin over the same games and entropy."""
    base, neutral = list(play(league, seasons)), list(play(league, seasons, venue="neutral"))
    diffs = [(g["final_score"]["home"] - g["final_score"]["away"]) - (n["final_score"]["home"] - n["final_score"]["away"])
             for (_, g), (_, n) in zip(base, neutral)]
    print(f"home edge (home minus neutral, same games): {statistics.mean(diffs):+.2f} "
          f"+- {statistics.pstdev(diffs) / len(diffs) ** 0.5:.2f} points")
    return {"kernel": KERNEL_VERSION, "seasons": seasons, "games": len(diffs),
            "home_edge": statistics.mean(diffs), "standard_error": statistics.pstdev(diffs) / len(diffs) ** 0.5}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("seasons", type=int, nargs="?", default=5)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--defense-test", action="store_true")
    mode.add_argument("--home-test", action="store_true")
    parser.add_argument("--summary-json", type=Path, help="write aggregate diagnostics only, never game results")
    parser.add_argument("--check", action="store_true", help="fail when league box totals, shooting or conditional spatial shares miss the prior-season targets")
    args = parser.parse_args()
    if args.seasons < 1:
        parser.error("seasons must be positive")
    if args.check and (args.defense_test or args.home_test):
        parser.error("--check applies to the league calibration report")
    league = League()
    if args.defense_test:
        summary = defense_test(league, args.seasons)
    elif args.home_test:
        summary = home_test(league, args.seasons)
    else:
        summary = report(league, args.seasons)
    if args.summary_json:
        args.summary_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if args.check:
        for error in summary["calibration_errors"]:
            print(error, file=sys.stderr)
        raise SystemExit(bool(summary["calibration_errors"]))
