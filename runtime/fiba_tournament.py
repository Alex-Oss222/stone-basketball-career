"""FIBA tournament mechanics: group standings with FIBA's tiebreak procedure, and bracket slots resolved to teams.

Pure functions over closed results; nothing here draws or writes. A tie the procedure cannot break is returned as such,
and the pipeline (`runtime/national.py`) settles it with one engine decision draw, like the NBA's playoff seeding.

Standings (FIBA Official Basketball Rules, classification of teams; each edition names its rule book): a win is worth
two classification points and a loss one (a forfeit none). Teams level on points are separated by their games against
each other only, restarting for any teams still level, then by criteria over all their group games (`PROCEDURES`:
goal average under the 2004 rules, point difference and points scored under later ones).
"""
from collections import defaultdict

WIN_POINTS, LOSS_POINTS = 2, 1


def _record(games, teams):
    """{team: {"w", "l", "pf", "pa", "pts"}} over games among `teams` only."""
    rows = {t: {"w": 0, "l": 0, "pf": 0, "pa": 0, "pts": 0} for t in teams}
    for g in games:
        h, a = g["home"], g["away"]
        if h not in rows or a not in rows:
            continue
        hs, as_ = g["home_score"], g["away_score"]
        for team, own, other in ((h, hs, as_), (a, as_, hs)):
            r = rows[team]
            r["pf"] += own
            r["pa"] += other
            if own > other:
                r["w"] += 1
                r["pts"] += WIN_POINTS
            else:
                r["l"] += 1
                r["pts"] += LOSS_POINTS
    return rows


def _split(tied, key):
    """Blocks of `tied` by descending `key`, or None when the key does not separate them."""
    values = sorted({key(t) for t in tied}, reverse=True)
    if len(values) == 1:
        return None
    return [[t for t in tied if key(t) == v] for v in values]


def _average(r):
    """FIBA goal average: points scored divided by points allowed (2004 rules, D.1.8)."""
    return r["pf"] / r["pa"] if r["pa"] else float("inf")


# Tiebreak procedures by rule book: criteria among the tied teams, then over all group games.
PROCEDURES = {
    # FIBA Official Basketball Rules 2004, Appendix D (in force for 2005-2010 events): head-to-head points, head-to-head
    # goal average, then goal average of all group games; restart for any block still tied.
    "fiba_2004": {"among": ("pts", "average"), "overall": ("average",)},
    # Later rule books (2010 on): head-to-head points, point difference, points scored; then the same over all games.
    "fiba_2010": {"among": ("pts", "difference", "scored"), "overall": ("difference", "scored")},
}
_KEYS = {"pts": lambda r: r["pts"], "average": _average, "difference": lambda r: r["pf"] - r["pa"], "scored": lambda r: r["pf"]}


def _order(tied, games, overall, procedure):
    """Order a group of teams level on classification points. Returns a list of blocks (lists of teams); a block of
    two or more is a tie the procedure cannot break."""
    if len(tied) == 1:
        return [list(tied)]
    among = _record(games, tied)
    for name in PROCEDURES[procedure]["among"]:
        blocks = _split(tied, lambda t: _KEYS[name](among[t]))
        if blocks:
            return [b for block in blocks for b in _order(block, games, overall, procedure)]   # restart for teams still level
    return _order_overall(tied, overall, procedure)


def _order_overall(block, overall, procedure):
    """Teams level on every head-to-head criterion, separated further only by the criteria over all group games."""
    for name in PROCEDURES[procedure]["overall"]:
        blocks = _split(block, lambda t: _KEYS[name](overall[t]))
        if blocks:
            return [b for sub in blocks for b in (_order_overall(sub, overall, procedure) if len(sub) > 1 else [sub])]
    return [sorted(block)]


def group_table(teams, games, procedure="fiba_2004"):
    """The group's table: [{"team", "w", "l", "pf", "pa", "pts", "position" or None, "tied_with"}], best first.
    `games` are closed group games {"home", "away", "home_score", "away_score"}. A row whose `tied_with` is non-empty
    is level with those teams after every criterion (an engine draw orders them)."""
    overall = _record(games, teams)
    by_points = defaultdict(list)
    for t in teams:
        by_points[overall[t]["pts"]].append(t)
    rows, position = [], 1
    for pts in sorted(by_points, reverse=True):
        for block in _order(sorted(by_points[pts]), games, overall, procedure):
            for t in block:
                rows.append(dict(overall[t], team=t, position=position if len(block) == 1 else None,
                                 tied_with=sorted(x for x in block if x != t)))
            position += len(block)
    return rows


def apply_draws(table, draws):
    """Positions for teams an engine draw ordered: `draws` maps a sorted tuple of tied teams to their drawn order."""
    out, position = [], 1
    i = 0
    while i < len(table):
        row = table[i]
        if row["tied_with"]:
            block = tuple(sorted([row["team"], *row["tied_with"]]))
            order = draws.get(block)
            if order is None:
                return None                                          # still waiting for the draw
            for t in order:
                r = next(x for x in table if x["team"] == t)
                out.append(dict(r, position=position, tied_with=[], drawn=True))
                position += 1
            i += len(block)
            continue
        out.append(dict(row, position=position))
        position += 1
        i += 1
    return out


def resolve_slot(slot, tables, winners, losers):
    """A bracket slot's team, or None while it is not decided. Slots: "A1" (group A, first place), "W:<game id>"
    (that game's winner), "L:<game id>" (its loser)."""
    if slot.startswith("W:"):
        return winners.get(slot[2:])
    if slot.startswith("L:"):
        return losers.get(slot[2:])
    group, place = slot[:-1], int(slot[-1])
    table = tables.get(group)
    if not table:
        return None
    row = next((r for r in table if r.get("position") == place), None)
    return row["team"] if row else None
