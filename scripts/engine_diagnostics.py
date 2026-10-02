#!/usr/bin/env python3
"""Engine diagnostics: play the real 2003-04 schedule between real rosters and compare with benchmarks.

Analysis only. Games here are resolved with made-up entropy and are never
written anywhere: career results come only from the Railway engine
(AGENTS.md, "Game engine"). Real-player development swings are stand-in draws
from a hash of the player id, for the same reason. Every non-Miami game of the
schedule is played on its date with both clubs' real rotations on that date
(`runtime/rotations.py`), so traded players are with one club at a time.

Usage: python scripts/engine_diagnostics.py [seasons] [--defense-test] [--home-test]

Output names clubs and players: it is for checking the engine, not for the
career record or the front office (AGENTS.md, option C), so do not commit it.

Benchmarks are general NBA figures for the era (judgement, not 2003-04
results): final-margin SD about 13-14, overtime in about 6% of games, 0.2-0.3
foul-outs per game, spread of team average margins over a season about 4-5,
home win rate about 60%.
"""
import collections
import hashlib
import json
import statistics
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.era import environment_for, rules_for
from runtime.kernel import resolve_game, validate_result
from runtime.player_stats import load_rating_index
from runtime.rotations import club_pace, load_rosters, miami_holds, real_rotation, season_fraction
from runtime.schedule import games_per_team, schedule_path
from runtime.trajectories import develop_profile, needs_development

SEASON, DATE = "2003-04", "2003-11-05"
BENCHMARKS = {"margin SD": (13, 14), "overtime rate": (0.05, 0.07), "foul-outs per game": (0.2, 0.3),
              "team net SD": (4, 5), "home win rate": (0.57, 0.63)}


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
        key = (name, tuple(p.player_id for p in team.players), tuple(p.availability for p in team.players), shift)
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


def play(league, seasons, venue="home", better=None):
    """Every non-Miami game of the schedule, `seasons` times with fresh entropy.
    `better`: clubs whose players are all one point better on defense."""
    rules, env = rules_for(SEASON), environment_for(SEASON, DATE)
    shift = lambda name: 1.0 if better and name in better else None
    for s in range(seasons):
        for g in league.games:
            home = league.team(g["home"], g["date"], shift(g["home"]))
            away = league.team(g["away"], g["date"], shift(g["away"]))
            event = f"diag-{s}-{g['game_id']}"
            result = resolve_game(home, away, entropy=hashlib.sha256(event.encode()).digest(), event_id=event,
                                  rules=rules, environment=env, venue=venue)
            errors = validate_result(result)
            if errors:
                raise SystemExit(f"invalid result: {errors}")
            yield s, result


def report(league, seasons):
    env = environment_for(SEASON, DATE)["averages"]
    margins, overtimes, home_wins, foul_outs = [], 0, 0, 0
    season_margins = collections.defaultdict(lambda: collections.defaultdict(list))
    totals, lines = collections.defaultdict(list), collections.defaultdict(list)
    for s, g in play(league, seasons):
        h, a = g["final_score"]["home"], g["final_score"]["away"]
        margins.append(h - a)
        season_margins[s][g["home"]].append(h - a)
        season_margins[s][g["away"]].append(a - h)
        overtimes += g["overtimes"] > 0
        home_wins += h > a
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
    for key, target in (("pts", "points"), ("fga", "fga"), ("tpa", "three_pa"), ("fta", "fta"), ("tov", "tov"),
                        ("orb", "orb"), ("ast", "ast"), ("stl", "stl"), ("blk", "blk"), ("pf", "pf")):
        print(f"    {key:<4} {statistics.mean(totals[key]):6.1f}  {env[target]:6.1f}")
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
    return out


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


def home_test(league, seasons):
    """Home minus neutral-site margin over the same games and entropy."""
    base, neutral = list(play(league, seasons)), list(play(league, seasons, venue="neutral"))
    diffs = [(g["final_score"]["home"] - g["final_score"]["away"]) - (n["final_score"]["home"] - n["final_score"]["away"])
             for (_, g), (_, n) in zip(base, neutral)]
    print(f"home edge (home minus neutral, same games): {statistics.mean(diffs):+.2f} "
          f"+- {statistics.pstdev(diffs) / len(diffs) ** 0.5:.2f} points")


if __name__ == "__main__":
    count = int(next((a for a in sys.argv[1:] if a.isdigit()), 5))
    league = League()
    if "--defense-test" in sys.argv:
        defense_test(league, count)
    elif "--home-test" in sys.argv:
        home_test(league, count)
    else:
        report(league, count)
