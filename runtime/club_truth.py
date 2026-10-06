"""One answer to "which club has this player on this date" from 2004-05 on (the user's request, December 2004 on the
career clock, after the same "on a team but shown as a free agent" bug came back through a new transaction type).

Every reader asks this module: league and Miami cards (`league_cards.club_on`), option decisions (`options`), the
contract ledger's holding club (`league_contracts.refresh_holders`) and the identity check. Its answer is the engine's
own input, so a card can never disagree with the games:
1. Miami: the player is in Miami's dated holdings (rule 2).
2. Any other club: the player is on that club's effective roster on the date (`league_moves.effective_roster`: the
   opening book, every dated league move, and Miami's departures, rule 3).
3. Out for the season (injured all year, `availability` "unavailable"): the club whose contract he is under.
4. Otherwise no club: an unsigned free agent, or out of the league when his real career has ended.
A new transaction type only has to write its own source record (a move, a holding, a departure); it can never leave a
second copy of the club to update.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIAMI = "Miami Heat"
_ROSTERS = {}


def _season(on):
    from .seasons import season_of_date
    return season_of_date(on)


def rosters_on(on, root=ROOT):
    """{bbr_id: club} for every club but Miami on the date, from the effective rosters (cached per repository and date)."""
    from .league_moves import effective_roster
    from .seasons import clubs as season_clubs
    key = (str(Path(root).resolve()), on)
    if key not in _ROSTERS:
        season = _season(on)
        out = {}
        for club in season_clubs(season, root):
            if club != MIAMI:
                for p in effective_roster(club, on, season, root):
                    if p.get("bbr_id"):
                        out[p["bbr_id"]] = club
        _ROSTERS[key] = out
    return _ROSTERS[key]


def holder(bbr_id, name, on, root=ROOT):
    """(club or None, basis) for the player on the date."""
    from .availability import status
    from .league_moves import club_of
    from .player_stats import alias
    from .rotations import miami_holds
    season = _season(on)
    miami = miami_holds(season, on, root)
    if (bbr_id and bbr_id in miami) or (name and alias(name) in miami):
        return MIAMI, f"on Miami's {season} register"
    club = rosters_on(on, root).get(bbr_id) if bbr_id else None
    if club:
        return club, f"{club}: the {season} opening rosters and the league's dated moves (runtime/club_truth.py)"
    state = status(bbr_id, season, root) if bbr_id else "unknown"
    if state == "unavailable":
        club = club_of(bbr_id, on, season, root)
        if club:
            return club, f"{club}: under contract, out for the {season} season"
    if state in ("retired", "unknown") and bbr_id:
        return None, f"out of the league: his real career has no {season} season (runtime/availability.py)"
    return None, f"unsigned on {on} in the {season} league"


def clear_cache():
    _ROSTERS.clear()
