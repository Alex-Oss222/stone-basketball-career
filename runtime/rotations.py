"""Rotations for real clubs (roadmap item 8, world model D).

A real club's game input is its real season roster for that season
(`library/<year>/league/nba_<season>_team_rosters.json`): each player brings
his minutes per game played and his availability, the share of the club's
games he played for it. The engine draws who is available for a given game,
dresses the top of the rotation and fills the 240 minutes in rotation order
(`runtime/kernel.py`). Season-share minutes would give a star who missed half
the season half his minutes every night; this gives him his real minutes on
the nights he plays.

Conflict rules (AGENTS.md, option D) are applied by the caller through
`exclude` (players simulated Miami holds) and `arrivals` (players who reach a
real club because of a Miami transaction, with the minutes they take over).
Miami's own rotation comes from its depth chart, never from this module.
"""
import json
from pathlib import Path

from .kernel import POSITIONS, PlayerInput, TeamInput

ROOT = Path(__file__).resolve().parents[1]
MAX_MINUTES_PER_GAME = 44.0     # input sanity bound; the kernel's caps decide game minutes
MIN_GAMES = 1


def rosters_path(season):
    start = int(season[:4])
    return Path(f"library/{start}/league/nba_{start}_{str(start + 1)[-2:]}_team_rosters.json")


def load_rosters(season, root=ROOT):
    return json.loads((Path(root) / rosters_path(season)).read_text(encoding="utf-8"))["clubs"]


def primary_position(label):
    """Basketball-Reference positions such as 'SG-SF' use their first listed position."""
    position = label.split("-")[0]
    return position if position in POSITIONS else "SF"


def real_rotation(club_name, club, season_games, rating_index=None, exclude=(), arrivals=()):
    """TeamInput for a real club: minutes per game and availability per player, rotation order first.

    `club` is the roster file entry; `season_games` the club's regular-season games.
    `exclude`: bbr_ids that are not with this club in the simulation (rule 2).
    `arrivals`: extra roster entries (same shape) for players who joined in the simulation.
    """
    exclude, arrivals = set(exclude), list(arrivals)
    staying = [p for p in club["players"] if p["bbr_id"] not in exclude]
    # Rule 3: departing minutes go to the arrivals up to their own previous share; the rest is
    # spread over the staying rotation in proportion to real minutes.
    share = lambda group: sum(p["minutes"] for p in group) / season_games
    remainder = max(0.0, share(p for p in club["players"] if p["bbr_id"] in exclude) - share(arrivals))
    factor = 1 + remainder / share(staying) if staying and remainder else 1.0
    players = []
    for p in staying + arrivals:
        if p["games"] < MIN_GAMES or p["minutes"] <= 0:
            continue
        per_game = min(MAX_MINUTES_PER_GAME, p["minutes"] / p["games"] * (factor if p in staying else 1.0))
        availability = min(1.0, p["games"] / season_games)
        profile = rating_index.engine_profile(p["player_id"], p["bbr_id"]) if rating_index else {}
        players.append((per_game, availability, PlayerInput(p["player_id"], primary_position(p["position"]),
                                                            round(per_game, 2), {}, profile,
                                                            round(availability, 4))))
    # Rotation order: who plays the most when he plays.
    players.sort(key=lambda item: (-item[0], -item[1], item[2].player_id))
    return TeamInput(club_name, tuple(p for _, _, p in players))
