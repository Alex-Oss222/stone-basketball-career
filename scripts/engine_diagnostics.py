#!/usr/bin/env python3
"""Engine diagnostics: play many games between real 2003-04 rosters and compare with benchmarks.

Analysis only. Games here are resolved with made-up entropy and are never
written anywhere: career results come only from the Railway engine
(AGENTS.md, "Game engine"). Real-player development swings are stand-in draws
from a hash of the player id, for the same reason.

Usage: python scripts/engine_diagnostics.py [games] [--defense-test]

Benchmarks are general NBA figures for the era (judgement, not 2003-04
results): final-margin SD about 13-14, overtime in about 6% of games, 0.2-0.3
foul-outs per game, spread of team average margins over an 82-game season about
4-5, home win rate about 60%.
"""
import collections
import hashlib
import random
import statistics
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.era import environment_for, rules_for
from runtime.kernel import TeamInput, resolve_game, validate_result
from runtime.player_stats import load_rating_index
from runtime.rotations import load_rosters, real_rotation
from runtime.trajectories import develop_profile, needs_development

SEASON, DATE, GAMES_PER_CLUB = "2003-04", "2003-11-05", 82
BENCHMARKS = {"margin SD": (13, 14), "overtime rate": (0.05, 0.07), "foul-outs per game": (0.2, 0.3),
              "team net SD": (4, 5), "home win rate": (0.57, 0.63)}


def stand_in_development(team):
    players = []
    for p in team.players:
        if p.stat_profile and needs_development(p.stat_profile):
            ref = hashlib.sha256(f"diagnostic:{p.stat_profile['bbr_id']}".encode()).hexdigest()
            p = replace(p, stat_profile=develop_profile(p.stat_profile, {SEASON: ref}))
        players.append(p)
    return replace(team, players=tuple(players))


def clubs():
    index = load_rating_index(DATE, SEASON, ROOT)
    return {name: stand_in_development(real_rotation(name, club, GAMES_PER_CLUB, index))
            for name, club in load_rosters(SEASON, ROOT).items()}


def play(teams, games, seed=7):
    rules, env = rules_for(SEASON), environment_for(SEASON, DATE)
    names, rng = sorted(teams), random.Random(seed)
    for i in range(games):
        home, away = rng.sample(names, 2)
        result = resolve_game(teams[home], teams[away], entropy=hashlib.sha256(f"diag{i}".encode()).digest(),
                              event_id=f"diag{i}", rules=rules, environment=env)
        errors = validate_result(result)
        if errors:
            raise SystemExit(f"invalid result: {errors}")
        yield result


def season_spread(team_margins, margins):
    """Spread of team average margins as an 82-game season would show it: the simulated
    between-team variance, less this sample's noise, plus the noise of 82 games."""
    noise = statistics.pvariance(margins)
    observed = statistics.pvariance([statistics.mean(v) for v in team_margins.values()])
    between = observed - statistics.mean(noise / len(v) for v in team_margins.values())
    return max(0.0, between + noise / GAMES_PER_CLUB) ** 0.5


def report(teams, games):
    env = environment_for(SEASON, DATE)["averages"]
    margins, team_margins, totals = [], collections.defaultdict(list), collections.defaultdict(list)
    lines, overtimes, home_wins, foul_outs, possessions = collections.defaultdict(list), 0, 0, 0, []
    for g in play(teams, games):
        h, a = g["final_score"]["home"], g["final_score"]["away"]
        margins.append(h - a)
        team_margins[g["home"]].append(h - a)
        team_margins[g["away"]].append(a - h)
        overtimes += g["overtimes"] > 0
        home_wins += h > a
        for side in ("home", "away"):
            for key, value in g["team_stats"][side].items():
                totals[key].append(value)
            for row in g["player_stats"][side]:
                foul_outs += row["fouled_out"]
                if row["seconds"] > 0:
                    lines[(g[side], row["player_id"])].append(row)
    out = {
        "points": statistics.mean(totals["pts"]),
        "margin SD": statistics.pstdev(margins),
        "mean absolute margin": statistics.mean(abs(m) for m in margins),
        "overtime rate": overtimes / games,
        "home win rate": home_wins / games,
        "home margin": statistics.mean(margins),
        "foul-outs per game": foul_outs / games,
        "team net SD": season_spread(team_margins, margins),
    }
    print(f"{games} games between real {SEASON} rosters")
    for key, value in out.items():
        bench = BENCHMARKS.get(key)
        print(f"  {key:<22} {value:7.3f}" + (f"   benchmark {bench[0]}-{bench[1]}" if bench else ""))
    print("  per team per game, simulated vs environment:")
    for key, target in (("pts", "points"), ("fga", "fga"), ("tpa", "three_pa"), ("fta", "fta"), ("tov", "tov"),
                        ("orb", "orb"), ("ast", "ast"), ("stl", "stl"), ("blk", "blk"), ("pf", "pf")):
        print(f"    {key:<4} {statistics.mean(totals[key]):6.1f}  {env[target]:6.1f}")
    print(f"    possessions {statistics.mean(totals['possessions']):.1f} (published pace {env['pace']})")
    real = {(name, p.player_id): p.minutes for name, team in teams.items() for p in team.players}
    rows = [(statistics.mean(r["minutes"] for r in v), real[k], k, v) for k, v in lines.items() if len(v) >= 15]
    print("  most minutes per game played (simulated, real):")
    for minutes, target, (club, pid), v in sorted(rows, reverse=True)[:10]:
        print(f"    {pid:<24} {club:<24} {minutes:5.1f} {target:5.1f}  {statistics.mean(r['pts'] for r in v):5.1f} pts")
    over = sum(1 for v in lines.values() for r in v if r["minutes"] > 44) / games
    print(f"  player-games over 44 minutes per game: {over:.2f}")
    nets = sorted(((statistics.mean(v), k) for k, v in team_margins.items()), reverse=True)
    print("  best:", ", ".join(f"{k} {x:+.1f}" for x, k in nets[:5]))
    print("  worst:", ", ".join(f"{k} {x:+.1f}" for x, k in nets[-5:]))
    return out


def defense_test(teams, games):
    """Every player one point better on defense (five on the floor = +5): points allowed should fall about 5 per 100."""
    def shifted(team, delta):
        return TeamInput(team.team_id, tuple(replace(p, stat_profile=dict(p.stat_profile, defense=p.stat_profile.get("defense", 0) + delta))
                                             if p.stat_profile else p for p in team.players))
    allowed = {}
    for delta in (0.0, 1.0):
        better = {k: shifted(t, delta) if k < "M" else t for k, t in teams.items()}
        pts = poss = 0
        for g in play(better, games):
            for side, opp in (("home", "away"), ("away", "home")):
                if g[side] < "M":
                    pts += g["final_score"][opp]
                    poss += g["team_stats"][opp]["possessions"]
        allowed[delta] = 100 * pts / poss
    print(f"defense +5 on the floor: {allowed[1.0] - allowed[0.0]:+.2f} points allowed per 100 (target about -5)")


if __name__ == "__main__":
    count = int(next((a for a in sys.argv[1:] if a.isdigit()), 1500))
    teams = clubs()
    if "--defense-test" in sys.argv:
        defense_test(teams, count)
    else:
        report(teams, count)
