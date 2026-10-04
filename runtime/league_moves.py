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


STRADDLE = 0.05        # season fraction (about 8 games): a real trade this close after the switch date is completed
ROSTER_MAX = 15        # 1999 CBA: fifteen under contract (twelve active, up to three injured)


def _activation(season, root, start):
    """(holder {bbr_id: club}, extras [roster entries]) on the activation date.

    A player is with the club whose real stint covers the date; if his next real stint begins within STRADDLE
    after it, the trade that moved him is completed (stints are placed by order and games, not dates, so a trade
    near the switch would otherwise be frozen half-done). Each club then keeps its ROSTER_MAX largest real roles
    for the season; the others start as unsigned free agents whom the league market signs as clubs need players."""
    start = start or league_book.SYMMETRIC_FROM
    fraction = season_fraction(season, start, root)
    stints = {}
    for club, entry in load_rosters(season, root).items():
        for p in entry["players"]:
            stints.setdefault(p["bbr_id"], []).append((club, p))
    holder = {}
    for bbr, rows in stints.items():
        rows.sort(key=lambda r: (r[1].get("window") or [0.0, 1.0])[0])
        present = [r for r in rows if _present(r[1], fraction)]
        soon = [r for r in rows if fraction < (r[1].get("window") or [0.0, 1.0])[0] <= fraction + STRADDLE]
        pick = soon[-1] if soon else (present[-1] if present else None)
        if pick is None:
            later = [r for r in rows if (r[1].get("window") or [0.0, 1.0])[0] > fraction]
            pick = later[0] if later else rows[-1]
        holder[bbr] = pick[0]
    roles = season_roles(season, root)
    protected = _protected_contracts(root)
    extras = []
    for club in {c for c in holder.values()}:
        # Over fifteen, a club lets go of minimum and unsigned players first (smallest real role first); a first-round
        # rookie or a contract above the minimum is kept (its salary would stay on the books anyway).
        members = sorted((b for b, c in holder.items() if c == club),
                         key=lambda b: (b not in protected, -roles[b]["minutes"], b))
        for b in members[ROSTER_MAX:]:
            extras.append(dict(roles[b], released_by=club))
            del holder[b]
    return holder, sorted(extras, key=lambda e: e["bbr_id"])


def _protected_contracts(root):
    """bbr_ids under a rookie-scale contract, a 2003 first-round pick, or a 2003-04 salary above the highest minimum."""
    path = Path(root) / "library/2003/league/nba_2003_contracts.json"
    # Above the highest minimum on the scale (10+ years of service): a veteran on his own minimum is not protected.
    minimum = json.loads((Path(root) / "library/2003/league/nba_1999_cba_minimum_salary_scale.json").read_text(encoding="utf-8"))["seasons"][SEASON]["10_plus"] / 1.5 * 1.05
    out = set()
    for club in json.loads(path.read_text(encoding="utf-8"))["clubs"].values():
        for p in club["players"]:
            salary = (p.get("schedule") or {}).get(SEASON) or 0
            if p.get("bbr_id") and (p.get("status") == "under_rookie_contract" or salary > 1.5 * minimum):
                out.add(p["bbr_id"])
    # The summer's rookie-scale and above-minimum signings (after the June inventory was compiled).
    moves = json.loads((Path(root) / "library/2003/league/nba_2003_offseason_transactions.json").read_text(encoding="utf-8"))
    for row in moves.get("signings", []):
        per = (row.get("total") or 0) / max(1, row.get("years") or 1)
        if row.get("bbr_id") and (row.get("kind") == "rookie_signing" or per > 1.5 * minimum):
            out.add(row["bbr_id"])
    # 2003 first-round picks (rookie scale is guaranteed for two seasons): names from the June draft-rights entries.
    from .player_stats import alias
    contracts = json.loads(path.read_text(encoding="utf-8"))["clubs"]
    first_round = {alias(r["player"]) for club in contracts.values() for r in club.get("draft_rights", []) if r.get("pick", 99) <= 29}
    draft = json.loads((Path(root) / "library/2003/league/nba_2003_draft_class.json").read_text(encoding="utf-8"))
    out |= {p["bbr_id"] for club in draft["clubs"].values() for p in club["players"]
            if p.get("bbr_id") and alias(p["player_id"]) in first_round}
    return out


def clubs_at_activation(season=SEASON, root=ROOT, start=None):
    """{bbr_id: club} on the activation date (`_activation`)."""
    return _activation(season, root, start)[0]


def activation_free_agents(season=SEASON, root=ROOT, start=None):
    """Real players on no club at activation: beyond a club's fifteen. The league market signs them."""
    return _activation(season, root, start)[1]


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
