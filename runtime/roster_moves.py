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

from .camp import GUARANTEE_DATE, playable
from .contract_archive import archive_contract
from .contracts import counted_amount

ROOT = Path(__file__).resolve().parents[1]
SEASON = "2003-04"
TEAM = Path(f"career/Dwyane_Wade/{SEASON}/00_Team")
LEDGER = TEAM / "Transactions/injured_list.json"
GUARANTEES = TEAM / "Transactions/guarantee_review.json"
GAME_DAY_ACTIVES = 12
IL_MAX = 3
IL_MIN_GAMES = 5
LISTS_FROM = "2003-11-12"           # first game day built under the lists; earlier games keep their inputs
WAIVE_BY = "2004-01-07"             # last day a waiver clears before the guarantee date
SEASON_DAYS = ("2003-10-28", "2004-04-14")   # 2003-04 regular season, for daily proration


def read(rel, root=ROOT):
    path = Path(root) / rel
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def empty_ledger():
    return {"schema_version": 1, "owner": "ai_gm", "kind": "injured_list", "season": SEASON, "lists_from": LISTS_FROM,
            "rule": (f"{GAME_DAY_ACTIVES} active for each game, up to {IL_MAX} on the injured list, at least {IL_MIN_GAMES} games "
                     "on it once placed. Injured players are placed first; the remaining places go to the lowest healthy "
                     "reserves (runtime/roster_moves.py)."),
            "entries": []}


def ledger(root=ROOT):
    return read(LEDGER, root) or empty_ledger()


def list_on(data, game_date):
    """Entries on the injured list for a game on `game_date`."""
    return [e for e in data["entries"] if e["placed"] <= game_date and (e.get("activated") is None or game_date < e["activated"])]


def games_missed(entry, game_date, game_dates):
    """Miami games the player has missed on the list before `game_date`."""
    return sum(1 for d in game_dates if entry["placed"] <= d < game_date)


def held_on_list(data, game_date, game_dates):
    """Players who must stay on the list for this game (fewer than IL_MIN_GAMES games missed)."""
    return {e["player"] for e in list_on(data, game_date) if games_missed(e, game_date, game_dates) < IL_MIN_GAMES}


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
        raise ValueError(f"{len(actives)} players would dress on {game_date}; the roster is over the 2003-04 limit")
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
                       "reserve: not among the twelve the staff dresses (2003-04 clubs listed healthy reserves on the injured list)"),
            "minimum_games": IL_MIN_GAMES})
    data["as_of"] = max(data.get("as_of", game_date), game_date)
    return data


def ledger_errors(root=ROOT):
    """The list never exceeds its places, every stay lasts its minimum, and listed players never play."""
    data = read(LEDGER, root)
    if data is None:
        return []
    errors = []
    from .season_games import miami_game_dates, miami_results
    dates = [d for d in miami_game_dates(root) if d >= data["lists_from"]]
    for d in dates:
        if len(list_on(data, d)) > IL_MAX:
            errors.append(f"injured_list.json: more than {IL_MAX} players on the list for {d}")
    for e in data["entries"]:
        if e.get("activated") and games_missed(e, e["activated"], dates) < IL_MIN_GAMES:
            errors.append(f"injured_list.json: {e['player']} activated {e['activated']} after fewer than {IL_MIN_GAMES} games")
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
    start, end = (date.fromisoformat(d) for d in SEASON_DAYS)
    d = date.fromisoformat(day)
    return min(1.0, max(0.0, (d - start).days / ((end - start).days + 1)))


def waived_charge(entry, day):
    """Salary a waived contract leaves on Miami's books for the season."""
    salary = counted_amount(entry, SEASON) or 0
    guaranteed = (entry.get("guaranteed") or {}).get(SEASON)
    if guaranteed is None or guaranteed >= (entry["schedule"].get(SEASON) or 0):
        return salary                                   # guaranteed: the full season's salary stays
    return round(salary * season_share(day))           # non-guaranteed: the days on the roster


def waive(writer, name, day, reason, note_rel):
    """Waive a Miami player: dead money booked, contract closed, holding ended, register and depth updated."""
    from .signing import _close_holding, long_date, note_event
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
    entry["notes"] = entry.get("notes", "") + f" Waived {day}: ${charge:,} stays on the 2003-04 books ({reason})."
    reg = next(p for p in roster["players"] if p["name"] == name)
    reg["status"], reg["control"] = "waived", f"{long_date(day)}: waived ({reason}); ${charge:,} remains on the 2003-04 books."
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
    note_event(writer, note_rel, day, f"Miami waived {name} ({reason}); ${charge:,} remains on the 2003-04 books.")
    return charge


def non_guaranteed(sheet):
    return [p for p in sheet["players"] if playable(p["status"]) and (p.get("guaranteed") or {}).get(SEASON) == 0
            and p["schedule"].get(SEASON)]


def guarantee_plan(sheet, front_office):
    """The front office's keep-or-waive decision for each non-guaranteed contract (rule, no draw)."""
    committed, _ = front_office.committed()
    ceiling = front_office.payroll_ceiling()
    rows = sorted(non_guaranteed(sheet), key=lambda p: front_office.valuation.value(p.get("bbr_id")) or 0.0)
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
    data = read(GUARANTEES, root)
    state = read(f"career/Dwyane_Wade/{SEASON}/current_state.json", root) or {}
    today = today or state.get("current_date", "")
    if today < GUARANTEE_DATE:
        return []
    if not data or not data.get("guaranteed_on"):
        return [f"guarantee review: contracts on the roster on {GUARANTEE_DATE} are not recorded as guaranteed (scripts/guarantee_review.py)"]
    sheet = read(TEAM / "Finances/contract_schedules.json", root)
    return [f"{p['player']}: non-guaranteed contract left on the roster past {GUARANTEE_DATE}" for p in non_guaranteed(sheet)]


def required_before(game_date, root=ROOT):
    """The guarantee step a game on `game_date` waits for, or None."""
    data = read(GUARANTEES, root) or {}
    if game_date > WAIVE_BY and not data.get("decided_on"):
        return f"the January 10 guarantee review is due by {WAIVE_BY}; run scripts/guarantee_review.py --write {WAIVE_BY}"
    if game_date >= GUARANTEE_DATE and not data.get("guaranteed_on"):
        return f"guarantees take effect {GUARANTEE_DATE}; run scripts/guarantee_review.py --write {GUARANTEE_DATE}"
    return None
