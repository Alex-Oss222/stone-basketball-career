"""Cross-season continuity of contracts, clubs, players and uniform numbers (the user's request, October 2026).

A season's records are rebuilt at every rollover from the summer market. This module checks that what carries over
carries over intact, for every pair of consecutive live seasons and for the live date:

Contracts
- A Miami contract that continues into the new season (the previous cap sheet schedules it there and the player is
  still Miami's) keeps every remaining season and amount of its signed schedule; a new contract (re-signing,
  extension, option decision) must name a signing date in the new league year or a route other than `existing`. The
  seasons of an extension signed in the new league year (`runtime/extensions.py`, its `extension` record dated on or
  after July 1) are its own agreement and are left out of the comparison; any other added season is refused.
- An `existing` (carried) contract is never dated as signed in the new league year.
- The league contract ledger lists each player once, and each Miami entry in it carries the full schedule, from the
  season on, of one of his rows on Miami's cap sheet (`league_contracts.miami_sheet_errors`; Wade by his NBA id).
- No player under contract to Miami on the previous sheet disappears without a record: he is on the new sheet,
  or the summer market placed him with another club, or he left with a recorded status.
Clubs
- On the live date no player is on two clubs: a player on Miami's active register is on no other club's roster,
  and no player is on two real clubs' rosters.
Players
- A player on both seasons' Miami registers keeps his identity (Basketball-Reference id and date of birth).
Numbers
- Every active Miami player has a uniform number and no two share one; Wade's number on the register is the one
  his dated identity carries, and it changes between seasons only through a jersey record.

`errors(root)` returns the problems (validation and the rollover's finish refuse them);
`python scripts/audit_continuity.py` prints them with a summary.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAYER = Path("career/Dwyane_Wade")
MIAMI = "Miami Heat"
WADE = "Dwyane Wade"
GONE = ("released", "traded", "signed_elsewhere", "voided", "waived", "renounced", "declined", "unsigned", "free_agent")


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8")) if Path(path).is_file() else None


def _sheet(root, season):
    data = _read(Path(root) / PLAYER / season / "00_Team/Finances/contract_schedules.json")
    return data["players"] if data else None


def _register(root, season):
    data = _read(Path(root) / PLAYER / season / "00_Team/Team/Roster/roster.json")
    return data["players"] if data else None


def _ids(register):
    return {p["name"]: p.get("bbr_id") for p in register or []}


def _later(schedule, season):
    return {s: int(v) for s, v in (schedule or {}).items() if s >= season and v}


def contract_errors(root, prev, new):
    old_sheet, new_sheet = _sheet(root, prev), _sheet(root, new)
    if old_sheet is None or new_sheet is None:
        return []
    old_ids, new_ids = _ids(_register(root, prev)), _ids(_register(root, new))
    key = lambda p, ids: p.get("bbr_id") or ids.get(p["player"]) or p["player"]
    old = {key(p, old_ids): p for p in old_sheet}
    errors = []
    july = f"{new[:4]}-07-01"
    placed_elsewhere = set()
    from .free_agency_2004 import record_for
    record = _read(Path(root) / record_for(new))
    if record:
        placed_elsewhere = {r["bbr_id"] for c, rows in record["clubs"].items() if c != MIAMI for r in rows}
    seen = set()
    for p in new_sheet:
        k = key(p, new_ids)
        seen.add(k)
        o = old.get(k)
        route, signed = p.get("route"), p.get("signed_date") or ""
        if route == "existing" and signed >= july:
            errors.append(f"{new}: {p['player']}'s carried contract is dated as signed {signed}, inside the new league year")
        if o is None or any(w in (o.get("status") or "") for w in GONE):
            continue
        carried = _later(o.get("schedule"), new)
        if not carried:
            continue
        renewed = signed >= july and route not in (None, "existing")
        current = _later(p.get("schedule"), new)
        extended = _extension_seasons(p, july)
        if extended:
            current = {s: v for s, v in current.items() if s not in extended}
        if not renewed and current != carried:
            errors.append(f"{new}: {p['player']}'s carried contract lost or changed seasons: {prev} sheet {carried}, {new} sheet "
                          f"{current}")
    for k, o in old.items():
        if k in seen or any(w in (o.get("status") or "") for w in GONE) or not _later(o.get("schedule"), new):
            continue
        if k not in placed_elsewhere:
            errors.append(f"{new}: {o['player']} was under contract to Miami for {new} on the {prev} sheet and is on no record now")
    return errors


def _extension_seasons(entry, since):
    """Seasons added by the entry's extensions signed on or after `since` (`runtime/extensions.py`)."""
    from .extensions import extensions_of
    return {s for ext in extensions_of(entry) if ext.get("signed_date", "") >= since for s in ext.get("schedule", {})}


def ledger_errors(root, season):
    """The ledger lists each player once (Wade's NBA id and register key are one player, `league_contracts.ledger_key`)
    and each Miami row agrees with Miami's cap sheet (`league_contracts.miami_sheet_errors`, Wade by his NBA id)."""
    from .league_contracts import ledger_key, miami_sheet_errors
    path = Path(root) / PLAYER / season / "League/contracts.json"
    data = _read(path)
    if not data:
        return []
    errors, seen = [], set()
    for c in data["contracts"]:
        key = ledger_key(c["bbr_id"], c.get("player"))
        if key in seen:
            errors.append(f"{season}: {c['player']} appears twice in the league contract ledger")
        seen.add(key)
    return errors + miami_sheet_errors(season, root)


def club_errors(root, season, day):
    """No player on two clubs on the date (Miami's active register against every real club; real clubs pairwise)."""
    from .league_moves import effective_roster
    from .seasons import clubs
    register = _register(root, season) or []
    miami = {p.get("bbr_id") for p in register if p.get("bbr_id") and not any(w in (p.get("status") or "") for w in GONE)}
    holder, errors = {}, []
    for club in clubs(season, root):
        if club == MIAMI:
            continue
        for p in effective_roster(club, day, season, root):
            b = p.get("bbr_id")
            if not b:
                continue
            if b in miami:
                errors.append(f"{day}: {p.get('player_id', b)} is on Miami's register and on {club}'s roster")
            if b in holder and holder[b] != club:
                errors.append(f"{day}: {p.get('player_id', b)} is on both {holder[b]}'s and {club}'s rosters")
            holder[b] = club
    return errors


def player_errors(root, prev, new):
    old, cur = _register(root, prev), _register(root, new)
    if old is None or cur is None:
        return []
    by_name = {p["name"]: p for p in old}
    errors = []
    for p in cur:
        o = by_name.get(p["name"])
        if not o:
            continue
        for field in ("bbr_id", "date_of_birth"):
            if o.get(field) and p.get(field) and o[field] != p[field]:
                errors.append(f"{new}: {p['name']}'s {field} changed from {o[field]} to {p[field]}")
    return errors


def number_errors(root, season, day):
    from .jerseys import miami_numbers
    numbers = miami_numbers(root)
    errors = []
    taken = {}
    for name, n in numbers.items():
        if n is None and name != WADE:
            errors.append(f"{season}: {name} has no uniform number")
        if n is not None:
            if n in taken:
                errors.append(f"{season}: {taken[n]} and {name} both wear #{n}")
            taken[n] = name
    identity = _read(Path(root) / PLAYER / "professional_identity.json") or {}
    snaps = [s for s in identity.get("snapshots", []) if s["as_of"] <= day]
    if snaps:
        latest = max(snaps, key=lambda s: s["as_of"]).get("jersey")
        if numbers.get(WADE) and latest and str(latest) != str(numbers[WADE]):
            errors.append(f"{season}: Wade wears #{numbers[WADE]} on the register but his dated identity says #{latest}")
    return errors


def errors(root=ROOT, clubs=True):
    """Every continuity problem across the live seasons and on the live date."""
    from .seasons import active, live_seasons, state
    root = Path(root)
    seasons = [s for s in live_seasons(root) if (root / PLAYER / s / "00_Team").is_dir()]
    out = []
    for prev, new in zip(seasons, seasons[1:]):
        out += contract_errors(root, prev, new) + player_errors(root, prev, new)
    live = active(root)
    day = state(live, root)["current_date"]
    out += ledger_errors(root, live) + number_errors(root, live, day)
    from .league_book import active as league_active
    if clubs and league_active(day):                     # simulated rosters exist only while the symmetric league is on
        out += club_errors(root, live, day)
    return out
