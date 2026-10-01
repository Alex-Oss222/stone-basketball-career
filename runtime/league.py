"""Baseline game inputs for clubs drawn from the league source library.

This is the default for background clubs whose rotation the simulation has not
otherwise decided: starters from the source depth order, a bench in depth
order, and conventional minute shares. It is a baseline, not a coaching
decision, and Miami's live rotation belongs to the AI/GM records instead.
"""
import json
from pathlib import Path

from .kernel import PlayerInput, TeamInput, POSITIONS

ROOT = Path(__file__).resolve().parents[1]
STARTER_MINUTES = 33
BENCH_MINUTES = (22, 18, 14, 10, 7, 4)


def load_clubs(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))["clubs"]


def baseline_team(club_name, club, actives):
    seen, players = set(), []
    for p in sorted(club["players"], key=lambda p: (p["depth"], POSITIONS.index(p["position"]))):
        if p["player_id"] not in seen:
            seen.add(p["player_id"])
            players.append(p)
    starters = []
    for position in POSITIONS:
        pick = next((p for p in players if p["position"] == position and p not in starters), None)
        if pick:
            starters.append(pick)
    starters += [p for p in players if p not in starters][:5 - len(starters)]
    bench = [p for p in players if p not in starters][:actives - 5]
    minutes = [STARTER_MINUTES] * len(starters) + list(BENCH_MINUTES[:len(bench)]) + [0] * max(0, len(bench) - len(BENCH_MINUTES))
    scale = 240 / sum(minutes)
    minutes = [round(m * scale, 2) for m in minutes]
    minutes[0] = round(minutes[0] + 240 - sum(minutes), 2)
    return TeamInput(club_name, tuple(PlayerInput(p["player_id"], p["position"], m)
                                      for p, m in zip(starters + bench, minutes)))
