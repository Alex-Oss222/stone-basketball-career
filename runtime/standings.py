"""Simulated standings on a date, from closed regular-season results only (roadmap item 14, the dated part).

Used where a rule needs the order of clubs on a date (waiver claim priority in the symmetric league). It reads
`write_back.closed_results` up to the date, never later games and never real 2003-04 standings.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _active_season(root=None):
    """The career's live season (runtime/seasons.py), read from the repository a call works on."""
    from .seasons import active
    return active(root or ROOT)
SEASON = "2003-04"


def standings_on(day, root=ROOT, season=None):
    """{club: {"wins", "losses", "pct"}} from closed results dated on or before `day`."""
    season = season or _active_season(root)
    from .write_back import closed_results
    table = {}
    for row in closed_results(root, season, day):
        r = row["result"]
        home_won = r["final_score"]["home"] > r["final_score"]["away"]
        for side, won in (("home", home_won), ("away", not home_won)):
            t = table.setdefault(r[side], {"wins": 0, "losses": 0})
            t["wins" if won else "losses"] += 1
    for t in table.values():
        t["pct"] = round(t["wins"] / max(1, t["wins"] + t["losses"]), 3)
    return table


def worst_first(day, root=ROOT, season=None, clubs=None):
    """Clubs from the worst record to the best on the date (ties: fewer wins, then name)."""
    season = season or _active_season(root)
    table = standings_on(day, root, season)
    names = clubs or sorted(table)
    return sorted(names, key=lambda c: (table.get(c, {}).get("pct", 0.0), table.get(c, {}).get("wins", 0), c))
