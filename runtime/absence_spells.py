"""Real clubs' absences as spells (games from November 12, 2003).

A real club's player misses his real share of games (`rotations._availability`: games played over
the club's games during his stint). Drawn game by game, those absences came as scattered single
games; real absences come in runs (an injury keeps a player out for a stretch). So once per player,
club and season the engine journals one event, like a development swing, and its reference lays the
season's missed games out as spells: lengths from the injury-length bands (`kernel.INJURY_LENGTHS`),
starts spread over his stint's games. For each game the player is in or out of a spell, so his
availability input is 1 or 0. The season total stays his real one; the draw cannot be chosen or
re-rolled; real injury dates are never used. The simulated club keeps its engine injuries instead.
"""
import json
import random
from dataclasses import replace
from pathlib import Path

from .kernel import INJURY_LENGTHS
from .player_stats import ROOT, alias

SPELLS_FROM = "2003-11-12"
SPELL_MODEL = "absence-spells.1"


def spell_packet(club, key, season):
    return {"event_id": f"absence-spells:{season}:{club}:{key}", "procedure": SPELL_MODEL,
            "club": club, "player": key, "season": season}


def _club_dates(season, club, root):
    from .schedule import schedule_path
    games = json.loads(schedule_path(season, root).read_text(encoding="utf-8"))["games"]
    return sorted(g["date"] for g in games if club in (g["home"], g["away"]))


def plan(ref, games, missed):
    """Indexes of the stint's games the player misses: `missed` games in spells, from the journaled ref."""
    rng = random.Random(int(ref, 16))
    out, attempts = set(), 0
    weights = [band[0] for band in INJURY_LENGTHS]
    while len(out) < missed and attempts < 1000:
        attempts += 1
        _, low, high, _ = rng.choices(INJURY_LENGTHS, weights)[0]
        length = min(rng.randint(low, high), missed - len(out))
        start = rng.randrange(0, max(1, games - length + 1))
        span = range(start, min(games, start + length))
        if any(i in out for i in span):
            continue
        out.update(span)
    for i in range(games):                      # crowded schedules: fill single games to the exact total
        if len(out) >= missed:
            break
        out.add(i)
    return out


def apply_spells(team, season, game_date, journal, root=ROOT):
    """The team with each partly-available player's input set to 1 or 0 for this game from his spells."""
    if game_date < SPELLS_FROM or team.injuries or not any(p.availability < 1 for p in team.players):
        return team
    from .rotations import load_rosters, season_fraction
    rosters = load_rosters(season, root)
    club = rosters.get(team.team_id)
    if club is None:
        return team
    dates = _club_dates(season, team.team_id, root)
    fractions = [season_fraction(season, d, root) for d in dates]
    today = season_fraction(season, game_date, root)
    players = []
    for p in team.players:
        if p.availability >= 1:
            players.append(p)
            continue
        bbr = (p.stat_profile or {}).get("bbr_id")
        mine = lambda s: (bbr and s.get("bbr_id") == bbr) or alias(s["player_id"]) == alias(p.player_id)
        stint = next((s for s in club["players"] if mine(s)
                      and (s.get("window") or [0, 1])[0] <= today
                      and (today < (s.get("window") or [0, 1])[1] or (s.get("window") or [0, 1])[1] >= 1.0)), None)
        if stint is None:
            players.append(p)
            continue
        lo, hi = stint.get("window") or [0.0, 1.0]
        stint_dates = [d for d, f in zip(dates, fractions) if lo <= f < hi or (hi >= 1.0 and f >= lo)]
        if game_date not in stint_dates:
            players.append(p)
            continue
        missed = round((1 - p.availability) * len(stint_dates))
        key = stint.get("bbr_id") or alias(stint["player_id"])
        ref = journal.close_event(spell_packet(team.team_id, key, season))
        out = plan(ref, len(stint_dates), missed)
        players.append(replace(p, availability=0.0 if stint_dates.index(game_date) in out else 1.0))
    return replace(team, players=tuple(players))
