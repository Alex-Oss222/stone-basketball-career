"""Symmetric league, phases 3 and 4: moves between real clubs and the simulated rosters games read.

Only while `league_book.active(date)`. From the activation date each real club starts from its real roster on
that date; real moves after it are not applied (the clubs now decide for themselves). Simulated moves between
real clubs (`league_moves.json`, written by `league_trades.py` and later the league market) move a player
from one club to another from their date. Miami's rules 2 and 3 and the disturbed-club replacements apply on
top, as under option D. A moved player keeps his real 2003-04 role: his minutes per game and games share of
his season (summed over his real stints), which `rotations.real_rotation` turns into the game input.

Off (the default), nothing here is read and every input is exactly option D's.
"""
import json
from pathlib import Path

from . import league_book
from .league_book import active
from .rotations import load_rosters, season_fraction

ROOT = Path(__file__).resolve().parents[1]
SEASON = "2003-04"


def ledger_path(season):
    return Path(f"career/Dwyane_Wade/{season}/League/league_moves.json")


def read(season=SEASON, root=ROOT):
    path = Path(root) / ledger_path(season)
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"schema_version": 1, "kind": "league_moves", "season": season, "entries": []}


def _present(stint, fraction):
    lo, hi = stint.get("window") or [0.0, 1.0]
    return lo <= fraction and (fraction < hi or hi >= 1.0)


def season_roles(season=SEASON, root=ROOT):
    """Each real player's season role: games and minutes summed over his real stints."""
    roles = {}
    for club, entry in load_rosters(season, root).items():
        for p in entry["players"]:
            r = roles.setdefault(p["bbr_id"], {"player_id": p["player_id"], "bbr_id": p["bbr_id"], "position": p["position"],
                                               "games": 0, "minutes": 0})
            r["games"] += p["games"]
            r["minutes"] += p["minutes"]
    return roles


def clubs_at_activation(season=SEASON, root=ROOT, start=None):
    """{bbr_id: club} from the real rosters on the activation date."""
    start = start or league_book.SYMMETRIC_FROM
    fraction = season_fraction(season, start, root)
    out = {}
    for club, entry in load_rosters(season, root).items():
        for p in entry["players"]:
            if _present(p, fraction):
                out.setdefault(p["bbr_id"], club)
    return out


def club_of(bbr_id, game_date, season=SEASON, root=ROOT, start=None):
    """A real player's club on the date in the symmetric league (before Miami's rules and replacements)."""
    club = clubs_at_activation(season, root, start).get(bbr_id)
    for e in sorted(read(season, root)["entries"], key=lambda e: e["date"]):
        if e["bbr_id"] == bbr_id and e["date"] <= game_date:
            club = e["to"]
    return club


def simulated_club(club, game_date, season=SEASON, root=ROOT, start=None):
    """A roster entry shaped like `load_rosters` for the club on the date: its activation roster plus the
    simulated moves to the date. Each player carries his whole-season real role, window [0, 1]."""
    if start is None and not active(game_date):
        raise ValueError("the symmetric league is not active on this date")
    roles = season_roles(season, root)
    at_start = clubs_at_activation(season, root, start)
    holder = dict(at_start)
    for e in sorted(read(season, root)["entries"], key=lambda e: e["date"]):
        if e["date"] <= game_date:
            holder[e["bbr_id"]] = e["to"]
    players = [dict(roles[b], span=[0.0, 1.0], window=[0.0, 1.0]) for b, c in holder.items() if c == club and b in roles]
    players.sort(key=lambda p: -p["minutes"])
    return {"players": players}


def effective_roster(club, game_date, season=SEASON, root=ROOT, start=None):
    """The club as its games and its front office see it: the simulated roster with Miami's rules 2 and 3 and
    the disturbed-club replacements applied, exactly as `game_requests._club` builds the game input."""
    from .club_replacements import arrivals as replacement_arrivals, held as replacements_held
    from .rotations import alias, miami_departed, miami_departures, miami_holds
    gone = set(miami_holds(season, game_date, root)) | set(miami_departed(season, game_date, root)) \
        | set(replacements_held(season, game_date, root))
    players = [p for p in simulated_club(club, game_date, season, root, start)["players"]
               if p["bbr_id"] not in gone and alias(p["player_id"]) not in gone]
    players += [dict(a) for a in miami_departures(season, club, game_date, root) + replacement_arrivals(season, club, game_date, root)]
    return players
