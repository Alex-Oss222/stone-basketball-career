"""Miami's in-season roster moves: game-day lists, the injured list, waivers and the guarantee date.

2003-04 rules (1999 CBA era, `runtime/era.py`): a club dresses 12 players for a game, and up to
three more sit on the injured list; a player placed on it misses at least five games. Clubs of the
era also used the list for healthy reserves (an injury had to be claimed); the staff here places
injured players first and fills the rest with the lowest healthy reserves, so the list is never
used to hide a rotation player.

Every list and move is the AI/GM's decision by the rules below; nothing here is chosen by the user
or drawn. Each change is dated in `00_Team/Transactions/injured_list.json`, which is also the
stored injury and roster state the rest of the career reads (`list_on`). Played games keep the
inputs they were played with: the lists start with the first game built on or after
`LISTS_FROM`.

Waivers (`waive`) close the contract on its date. A non-guaranteed contract waived before its
guarantee date leaves the salary for the days the player was on the regular-season roster; a
guaranteed one leaves its full remaining salary (1999 CBA, judgement on daily proration). A
waived player is a free agent and goes back to his real career path (AGENTS.md, Career continuity).

The guarantee review (`guarantee_review`): non-guaranteed contracts still on the roster on
January 10, 2004 become guaranteed. The last day to waive one without that happening is January 7
(waivers take 48 hours). The front office keeps a non-guaranteed player unless guaranteeing him
would take the payroll over the owner's ceiling; then the lowest-valued are waived first.
"""
from datetime import date
import json
from pathlib import Path

from .camp import playable
from .contract_archive import archive_contract
from .contracts import counted_amount

ROOT = Path(__file__).resolve().parents[1]


def ctx(root=None, day=None):
    """The season's files and dated gates (runtime/seasons.py): the season of `day` when given, else the live one."""
    from types import SimpleNamespace
    from . import seasons
    season = seasons.season_of_date(day) if day else seasons.active(root or ROOT)
    gates = seasons.dates(season, root or ROOT)
    team = Path(f"career/Dwyane_Wade/{season}/00_Team")
    return SimpleNamespace(season=season, team=team, ledger=team / "Transactions/injured_list.json",
                           guarantees=team / "Transactions/guarantee_review.json", waive_by=gates["waive_by"],
                           guarantee=gates["guarantee"], days=(gates["opening_night"], gates["regular_season_end"]))


def __getattr__(name):
    """The old module constants, now the live season's: SEASON, TEAM, LEDGER, GUARANTEES, WAIVE_BY, GUARANTEE_DATE,
    SEASON_DAYS."""
    c = ctx()
    table = {"SEASON": c.season, "TEAM": c.team, "LEDGER": c.ledger, "GUARANTEES": c.guarantees, "WAIVE_BY": c.waive_by,
             "GUARANTEE_DATE": c.guarantee, "SEASON_DAYS": c.days}
    if name in table:
        return table[name]
    raise AttributeError(name)

GAME_DAY_ACTIVES = 12
IL_MAX = 3
IL_MIN_GAMES = 5


def min_games(game_date):
    """Games a player placed on the list must miss: five under the 1999 agreement's injured list, none on the 2005
    agreement's inactive list (era rules `reserve_list_minimum_games`, from 2005-06)."""
    from .era import rules_for
    from .seasons import season_of_date
    return rules_for(season_of_date(game_date)).get("reserve_list_minimum_games", IL_MIN_GAMES)
LISTS_FROM = "2003-11-12"           # first game day built under the lists; earlier games keep their inputs


def read(rel, root=ROOT):
    path = Path(root) / rel
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def empty_ledger(season=None):
    return {"schema_version": 1, "owner": "ai_gm", "kind": "injured_list", "season": season or ctx().season, "lists_from": LISTS_FROM,
            "rule": (f"{GAME_DAY_ACTIVES} active for each game, up to {IL_MAX} on the injured list, at least {IL_MIN_GAMES} games "
                     "on it once placed. Injured players are placed first; the remaining places go to the lowest healthy "
                     "reserves (runtime/roster_moves.py)."),
            "entries": []}


def ledger(root=ROOT):
    c = ctx(root)
    return read(c.ledger, root) or empty_ledger(c.season)


def list_on(data, game_date):
    """Entries on the injured list for a game on `game_date`."""
    return [e for e in data["entries"] if e["placed"] <= game_date and (e.get("activated") is None or game_date < e["activated"])]


def games_missed(entry, game_date, game_dates):
    """Miami games the player has missed on the list before `game_date`."""
    return sum(1 for d in game_dates if entry["placed"] <= d < game_date)


def held_on_list(data, game_date, game_dates):
    """Players who must stay on the list for this game (fewer than IL_MIN_GAMES games missed)."""
    return {e["player"] for e in list_on(data, game_date) if games_missed(e, game_date, game_dates) < e.get("minimum_games", min_games(game_date))}


def game_day(game_date, kept, depth_entries, injured, data, game_dates):
    """The game-day lists: (actives in request order, injured list, placements, activations).

    `kept`: the rotation players after injuries (`season_games.rotation_for`), in rotation order.
    `depth_entries`: every playable register entry in depth-chart order. `injured`: player -> games out.
    The actives are the rotation, then the next healthy players by depth order until twelve dress;
    the injured list takes injured players first, then players who must stay on it, then the lowest
    healthy reserves, preferring those already on it (no needless moves)."""
    names = [e["name"] for e in depth_entries]
    current = {e["player"]: e for e in list_on(data, game_date)}
    must_stay = held_on_list(data, game_date, game_dates)
    rotation = [p["player_id"] for p in kept]
    if must_stay & set(rotation):
        raise ValueError(f"{sorted(must_stay & set(rotation))} must stay on the injured list; pass them as unavailable to the rotation")
    hurt = [n for n in names if n in injured]
    il = [n for n in names if n in must_stay]
    for n in hurt:
        if n not in il and len(il) < IL_MAX:
            il.append(n)
    out_of_game = set(hurt)                         # an injured player beyond the list's places does not dress
    healthy = [n for n in names if n not in rotation and n not in il and n not in out_of_game]
    spare = len(rotation) + len(healthy) - GAME_DAY_ACTIVES
    # Reserves to list: those already on it first, then from the bottom of the depth order.
    order = [n for n in reversed(healthy) if n in current] + [n for n in reversed(healthy) if n not in current]
    for n in order:
        if spare <= 0 or len(il) >= IL_MAX:
            break
        il.append(n)
        spare -= 1
    extra = [n for n in healthy if n not in il][:max(0, GAME_DAY_ACTIVES - len(rotation))]
    actives = rotation + extra
    if len(actives) > GAME_DAY_ACTIVES:
        raise ValueError(f"{len(actives)} players would dress on {game_date}; the roster is over the dressed limit")
    placements = [(n, "injury" if n in injured else "reserve") for n in il if n not in current]
    activations = [n for n in current if n not in il]
    return actives, il, placements, activations


def record_lists(data, game_date, il, placements, activations, injured, event_id):
    """Write the day's placements and activations into the ledger (in place)."""
    for name in activations:
        for e in data["entries"]:
            if e["player"] == name and e.get("activated") is None:
                e["activated"] = game_date
    for name, why in placements:
        games = injured.get(name)
        data["entries"].append({
            "player": name, "placed": game_date, "activated": None, "first_game_missed": event_id,
            "reason": (f"injury: {games} more game(s) out on the engine's draw" if why == "injury" else
                       "reserve: not among the twelve the staff dresses (clubs of the era listed healthy reserves on the injured list)"),
            "minimum_games": min_games(game_date)})
    data["as_of"] = max(data.get("as_of", game_date), game_date)
    return data


def ledger_errors(root=ROOT):
    """The list never exceeds its places, every stay lasts its minimum, and listed players never play."""
    data = read(ctx(root).ledger, root)
    if data is None:
        return []
    errors = []
    from .season_games import miami_game_dates, miami_results
    dates = [d for d in miami_game_dates(root) if d >= data["lists_from"]]
    for d in dates:
        if len(list_on(data, d)) > IL_MAX:
            errors.append(f"injured_list.json: more than {IL_MAX} players on the list for {d}")
    for e in data["entries"]:
        if e.get("activated") and games_missed(e, e["activated"], dates) < e.get("minimum_games", IL_MIN_GAMES):
            errors.append(f"injured_list.json: {e['player']} activated {e['activated']} after fewer than {e.get('minimum_games', IL_MIN_GAMES)} games")
    for result in miami_results(root):
        d = result.get("game_date", "")
        if d < data["lists_from"]:
            continue
        side = "home" if result.get("home") == "Miami Heat" else "away"
        played = {line["player_id"] for line in (result.get("player_stats") or {}).get(side, []) if line.get("minutes", 0) > 0}
        listed = {e["player"] for e in list_on(data, d)}
        if played & listed:
            errors.append(f"{result.get('event_id')}: {sorted(played & listed)} played while on the injured list")
    return errors


# -- waivers and the guarantee date ------------------------------------------------------------------
def season_share(day):
    """Share of the regular season's days before `day` (daily proration of a waived salary)."""
    start, end = (date.fromisoformat(d) for d in ctx(day=day).days)
    d = date.fromisoformat(day)
    return min(1.0, max(0.0, (d - start).days / ((end - start).days + 1)))


def waived_charge(entry, day):
    """Salary a waived contract leaves on Miami's books for the season."""
    season = ctx(day=day).season
    salary = counted_amount(entry, season) or 0
    guaranteed = (entry.get("guaranteed") or {}).get(season)
    if guaranteed is None or guaranteed >= (entry["schedule"].get(season) or 0):
        return salary                                   # guaranteed: the full season's salary stays
    return round(salary * season_share(day))           # non-guaranteed: the days on the roster


def waive(writer, name, day, reason, note_rel):
    """Waive a Miami player: dead money booked, contract closed, holding ended, register and depth updated."""
    from .signing import _close_holding, long_date, note_event
    c = ctx(day=day)
    TEAM, SEASON, GUARANTEES = c.team, c.season, c.guarantees
    sheet = writer.load(TEAM / "Finances/contract_schedules.json")
    roster = writer.load(TEAM / "Team/Roster/roster.json")
    holdings = writer.load(TEAM / "Team/Roster/holdings.json")
    depth = writer.load(TEAM / "Team/Depth_Chart/depth_chart.json")
    entry = next(p for p in sheet["players"] if p["player"] == name)
    if not playable(entry["status"]):
        raise ValueError(f"{name} is not on Miami's roster ({entry['status']})")
    charge = waived_charge(entry, day)
    entry.update(status="waived", waived_date=day, dead_money={SEASON: charge})
    entry["cap_amount"] = {SEASON: charge}
    entry["notes"] = entry.get("notes", "") + f" Waived {day}: ${charge:,} stays on the {SEASON} books ({reason})."
    reg = next(p for p in roster["players"] if p["name"] == name)
    reg["status"], reg["control"] = "waived", f"{long_date(day)}: waived ({reason}); ${charge:,} remains on the {SEASON} books."
    _close_holding(holdings, name, day)
    for names in depth["positions"].values():
        if name in names:
            names.remove(name)
    depth.setdefault("departed", []).append({"name": name, "date": day, "status": "waived"})
    depth["as_of"] = roster["as_of"] = day
    base = next((r for r in (writer.load("career/Dwyane_Wade/Contracts/contract_records.json")["records"])
                 if r["player"] == name and r["event"] == "signed"), None)
    if base:
        archive_contract(writer, {**entry, "contract_id": base["contract_id"], "ended_on": day}, day, event="released",
                         source=str(GUARANTEES), player_id=base["player_id"])
    note_event(writer, note_rel, day, f"Miami waived {name} ({reason}); ${charge:,} remains on the {SEASON} books.")
    return charge


def non_guaranteed(sheet, season=None):
    season = season or ctx().season
    return [p for p in sheet["players"] if playable(p["status"]) and (p.get("guaranteed") or {}).get(season) == 0
            and p["schedule"].get(season)]


def guarantee_plan(sheet, front_office):
    """The front office's keep-or-waive decision for each non-guaranteed contract (rule, no draw)."""
    c = ctx(getattr(front_office, "root", None))
    SEASON, WAIVE_BY = c.season, c.waive_by
    committed, _ = front_office.committed()
    ceiling = front_office.payroll_ceiling()
    rows = sorted(non_guaranteed(sheet, SEASON), key=lambda p: front_office.valuation.value(p.get("bbr_id")) or 0.0)
    plan, payroll = [], committed
    over = max(0, payroll - ceiling)
    for p in rows:
        if over > 0:
            plan.append({"player": p["player"], "decision": "waive",
                         "basis": f"payroll ${payroll:,} is over the owner's ceiling ${ceiling:,}; lowest value waived first"})
            saved = counted_amount(p, SEASON) - round(counted_amount(p, SEASON) * season_share(WAIVE_BY))
            over -= saved
            payroll -= saved
        else:
            plan.append({"player": p["player"], "decision": "keep",
                         "basis": f"payroll ${payroll:,} stays under the owner's ceiling ${ceiling:,}; he stays for depth"})
    return plan


def guarantee_errors(root=ROOT, today=None):
    """After the guarantee date, a contract still on the roster must be recorded as guaranteed."""
    c = ctx(root)
    GUARANTEES, GUARANTEE_DATE, TEAM = c.guarantees, c.guarantee, c.team
    data = read(GUARANTEES, root)
    state = read(f"career/Dwyane_Wade/{c.season}/current_state.json", root) or {}
    today = today or state.get("current_date", "")
    if today < GUARANTEE_DATE:
        return []
    if not data or not data.get("guaranteed_on"):
        return [f"guarantee review: contracts on the roster on {GUARANTEE_DATE} are not recorded as guaranteed (scripts/guarantee_review.py)"]
    sheet = read(TEAM / "Finances/contract_schedules.json", root)
    return [f"{p['player']}: non-guaranteed contract left on the roster past {GUARANTEE_DATE}" for p in non_guaranteed(sheet, c.season)]


def required_before(game_date, root=ROOT):
    """The guarantee step a game on `game_date` waits for, or None."""
    c = ctx(root, game_date)
    GUARANTEES, WAIVE_BY, GUARANTEE_DATE = c.guarantees, c.waive_by, c.guarantee
    if not (c.days[0] <= game_date):
        return None
    data = read(GUARANTEES, root) or {}
    if game_date > WAIVE_BY and not data.get("decided_on"):
        return f"the January 10 guarantee review is due by {WAIVE_BY}; run scripts/guarantee_review.py --write {WAIVE_BY}"
    if game_date >= GUARANTEE_DATE and not data.get("guaranteed_on"):
        return f"guarantees take effect {GUARANTEE_DATE}; run scripts/guarantee_review.py --write {GUARANTEE_DATE}"
    return None


# -- readable depth chart ----------------------------------------------------------------------------
def _carried_depth_view(root, folder, today):
    """Before training camp decides (a season's rollover carries last season's order): the order only, no minutes."""
    path = folder / "depth_chart.json"
    if not path.is_file():
        return {}
    depth = json.loads(path.read_text(encoding="utf-8"))
    width = max([len(v) for v in depth["positions"].values()] + [1])
    rows = "\n".join(f"| {pos} | " + " | ".join(names + [""] * (width - len(names))) + " |" for pos, names in depth["positions"].items())
    arrivals = [u["name"] if isinstance(u, dict) else u for u in depth.get("unassigned_arrivals", [])]
    rights = [u["name"] if isinstance(u, dict) else u for u in depth.get("unassigned_draft_rights", [])]
    md = f"""# Miami Heat working depth chart

**As of:** {today} · **Staff decision in force:** none yet; training camp decides  
**Status:** {depth.get('status', 'carried_over').replace('_', ' ')}: {depth.get('basis', '')}

| Position | {' | '.join(str(i) for i in range(1, width + 1))} |
|---|{'---|' * width}
{rows}

## Unassigned

Arrivals: {', '.join(arrivals) or 'none'}. Unsigned draft rights: {', '.join(rights) or 'none'}.

Generated by `scripts/update_player_reports.py` from [depth_chart.json](depth_chart.json).
"""
    readme = (f"# Working depth chart\n\nNo staff decision is in force on {today}: training camp sets the order and the rotation.\n\n"
              "- [Readable depth chart](depth_chart.md)\n- [Carried-over order (machine-readable)](depth_chart.json)\n")
    return {folder / "depth_chart.md": md, folder / "README.md": readme}


def depth_views(root=ROOT, today=None):
    """The readable depth chart and its README from the staff's chart in force on the career date.

    Generated from the dated records (rotation reviews, the register, the injured-list ledger); never
    hand-edited. Returns {path: text}."""
    from .camp import playable as _playable
    from .rotation_reviews import rotation_in_force
    root = Path(root)
    c = ctx(root)
    TEAM, LEDGER = c.team, c.ledger
    state = read(f"career/Dwyane_Wade/{c.season}/current_state.json", root) or {}
    today = today or state.get("current_date")
    folder = root / TEAM / "Team/Depth_Chart"
    try:
        rotation, depth = rotation_in_force(today, root, c.season, require_review=False)
    except (OSError, ValueError, KeyError):
        return _carried_depth_view(root, folder, today)
    roster = read(TEAM / "Team/Roster/roster.json", root)
    register = {p["name"]: p for p in roster["players"]}
    listed = {e["player"] for e in list_on(ledger(root), today)} if read(LEDGER, root) else set()
    minutes = {p["player_id"]: p["minutes"] for p in rotation["players"]}
    starters = set((rotation.get("starters") or {}).values())
    width = max(len(v) for v in depth["positions"].values())
    rows = []
    for pos, names in depth["positions"].items():
        cells = []
        for name in names:
            tag = (" (starter, on the injured list)" if name in starters and name in listed else " (starter)" if name in starters
                   else " (injured list)" if name in listed else "")
            cells.append(name + tag)
        rows.append(f"| {pos} | " + " | ".join(cells + [""] * (width - len(cells))) + " |")
    rot = "\n".join(f"| {p['player_id']} | {p['position']} | {p['minutes']:g} | {('yes, on the injured list' if p['player_id'] in listed else 'yes') if p['player_id'] in starters else ''} |"
                     for p in rotation["players"])
    others = [n for n, p in register.items() if _playable(p.get("status")) and n not in minutes]
    unsigned = [n for n, p in register.items() if "draft_rights" in (p.get("status") or "")]
    ledger_link = " ([ledger](../../Transactions/injured_list.json))" if read(LEDGER, root) else " (no list kept yet: the lists start with the game of " + LISTS_FROM + ")"
    md = f"""# Miami Heat working depth chart

**As of:** {today} · **Staff decision in force:** {rotation['as_of']} ({'fortnightly review' if rotation.get('review') else 'training-camp decision'})  
**Status:** game-ready working view; a working basketball view, not a promise of minutes

| Position | {' | '.join(str(i) for i in range(1, width + 1))} |
|---|{'---|' * width}
{chr(10).join(rows)}

## Rotation in force

| Player | Slot | Minutes | Starter |
|---|---|---:|---|
{rot}

Outside the rotation (dressing as the twelfth man or on the injured list): {', '.join(others) or 'none'}.

## Injured list on {today}

{', '.join(sorted(listed)) or 'Nobody'}{ledger_link}. Up to three; at least five games once placed (`runtime/roster_moves.py`).

## Not on the active register

{('Unsigned draft rights: ' + ', '.join(unsigned) + '.') if unsigned else 'No unsigned draft rights.'}

Generated by `scripts/update_player_reports.py` from [the chart in force](Reviews/{rotation['as_of']}/depth_chart.json) when a review exists, else [depth_chart.json](depth_chart.json); the dated reviews are in [Reviews](Reviews/).
"""
    readme = f"""# Working depth chart

The staff's chart in force on {today} comes from its {rotation['as_of']} decision. The staff reviews the roster every fourteen days (`scripts/review_rotation.py`); each review is kept under `Reviews/<date>/`.

- [Readable depth chart](depth_chart.md)
- [Camp decision (machine-readable)](depth_chart.json) and [camp rotation](rotation.json)
""" + ("- [Injured list ledger](../../Transactions/injured_list.json)\n" if read(LEDGER, root) else "")
    return {folder / "depth_chart.md": md, folder / "README.md": readme}

