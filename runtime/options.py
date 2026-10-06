"""Contract options for every club (the user's request, October 2026): team options, player options and early
termination options are decided on their real deadlines, never silently treated as exercised.

Which seasons are options: the league contract ledger's `options` ({season: kind}) for each contract, from the
contract inventory's amount kinds (team_option, player_option, early_termination_option) and the rookie scale's
team option seasons. Miami's options are on its own cap sheet (`amount_kind`).

Deadlines (1999 agreement, the calendar files): a first-round pick's rookie-scale team option is decided by October 31
of the season before the option season; a veteran's team option, player option or early termination option at the end
of June before it (`VETERAN_DEADLINE`, decided by the summer market of that year, `runtime/season_market.py`).

The decision is the holder's, on its own valuation on the deadline (evidence dated on or before it, no hindsight):
- worth: the player's market price for his production value on the date (`valuation.market_price`), times
  YOUTH_PREMIUM for a player 24 or younger (development and control after the contract);
- team option: exercise when worth / option salary is at least HIGH, decline at or below LOW; in between the engine
  draws it, exercise with probability (ratio - LOW) / (HIGH - LOW);
- player option or early termination option: the player stays when option salary / worth is at least HIGH, leaves at
  or below LOW, the engine draws in between.
A clear-cut decision is recorded with its numbers and no draw; a close one is an engine decision packet
(`League/Option_Draws/`), drawn once and never re-rolled. A player history retired before the option season
(`runtime/availability.py`) is declined by the club, or opts out, without a draw.
"""
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAYER = Path("career/Dwyane_Wade")
OPTION_KINDS = ("team_option", "player_option", "early_termination_option")
LOW, HIGH = 0.80, 1.20                 # judgement: the close band in which the answer is a draw
YOUTH_PREMIUM, YOUNG_AGE = 1.25, 24    # judgement: a young player's development and control are worth more than his line
VETERAN_DEADLINE = "06-29"             # end of June before the option season (1999 agreement practice)


def draws_dir(season):
    return PLAYER / season / "League/Option_Draws"


def record_path(season):
    return PLAYER / season / "League/option_decisions.json"


def season_label(start):
    return f"{start}-{str(start + 1)[-2:]}"


def deadline(kind, option_season, rookie):
    """The decision date for an option season."""
    start = int(option_season[:4])
    if rookie and kind == "team_option":
        return f"{start - 1}-10-31"
    return f"{start}-{VETERAN_DEADLINE}"


def _read(path):
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def read_record(season, root=ROOT):
    return _read(Path(root) / record_path(season)) or {"schema_version": 1, "kind": "option_decisions", "season": season,
                                                        "rule": __doc__.split("\n\n", 1)[1].strip(), "decisions": []}


def open_options(season, root=ROOT):
    """[(holder, bbr_id, player, option season, kind, salary, rookie)] still open in the season's contracts."""
    from .league_contracts import read as read_ledger
    root = Path(root)
    out = []
    for b, c in (read_ledger(season, root) or {}).items():
        if c["club"] == "Miami Heat":
            continue
        for s, kind in (c.get("options") or {}).items():
            if kind in OPTION_KINDS and s > season and c["schedule"].get(s):
                out.append((c["club"], b, c["player"], s, kind, int(c["schedule"][s]), bool(c.get("rookie_scale"))))
    sheet = _read(root / PLAYER / season / "00_Team/Finances/contract_schedules.json") or {"players": []}
    roster = {p["name"]: p.get("bbr_id") for p in (_read(root / PLAYER / season / "00_Team/Team/Roster/roster.json") or {"players": []})["players"]}
    for p in sheet["players"]:
        if any(w in (p.get("status") or "") for w in ("released", "traded", "waived", "voided", "renounced", "signed_elsewhere")):
            continue
        for s, kind in (p.get("amount_kind") or {}).items():
            if kind in OPTION_KINDS and s > season and p["schedule"].get(s):
                rookie = p.get("route") == "rookie_scale" or "rookie" in (p.get("status") or "") or "rookie-scale" in (p.get("notes") or "")
                out.append(("Miami Heat", p.get("bbr_id") or roster.get(p["player"]), p["player"], s, kind, int(p["schedule"][s]), rookie))
    return out


def decide(day, row, valuation, root=ROOT):
    """(decision dict, packet or None) for one option on its deadline."""
    from .availability import status
    club, bbr, name, s, kind, salary, rookie = row
    age = valuation.age(bbr) if bbr else None
    value = valuation.value(bbr) if bbr else None
    worth = valuation.market_price(value, bbr) if value is not None else 0.0
    if age is not None and age <= YOUNG_AGE:
        worth *= YOUTH_PREMIUM
    retired = bbr and status(bbr, s, root) in ("retired", "unknown")
    team = kind == "team_option"
    ratio = (worth / salary) if team else (salary / worth if worth else float("inf"))
    yes, no = ("exercise", "decline") if team else ("stay", "leave")
    base = {"id": f"{s}-option-{bbr or name}-{kind}", "club": club, "player": name, "bbr_id": bbr, "option_season": s,
            "kind": kind, "salary": salary, "deadline": day, "worth": round(worth), "age": age, "ratio": round(ratio, 3),
            "decider": club if team else name}
    if retired:
        return dict(base, decision=no, how=f"his real career ended before {s} (runtime/availability.py)"), None
    if ratio >= HIGH:
        return dict(base, decision=yes, how=f"clear: ratio {ratio:.2f} at or above {HIGH}"), None
    if ratio <= LOW:
        return dict(base, decision=no, how=f"clear: ratio {ratio:.2f} at or below {LOW}"), None
    p = round((ratio - LOW) / (HIGH - LOW), 3)
    packet = {"event_id": base["id"], "date": day,
              "question": (f"Does {club} exercise its {s} team option on {name} (${salary:,})?" if team else
                           f"Does {name} stay on his {s} {kind.replace('_', ' ')} with {club} (${salary:,})?"),
              "decider": base["decider"] + " (drawn by rule)", "options": {yes: p, no: round(1 - p, 3)},
              "basis": (f"worth ${worth:,.0f} (market price of his production on {day}"
                        + (f", x{YOUTH_PREMIUM} for a player {YOUNG_AGE} or younger" if age is not None and age <= YOUNG_AGE else "")
                        + f") against ${salary:,}: ratio {ratio:.3f} inside the close band {LOW}-{HIGH} (runtime/options.py)")}
    return dict(base, decision=None, how="engine draw"), packet


def _season_of(day):
    from .seasons import season_of_date
    return season_of_date(day)


def holders_on(day, root=ROOT):
    """{bbr_id: club} for every club's players on the date in the simulated league (`league_moves.effective_roster`):
    a contract travels with a traded player, so the club deciding his option is the one holding him on the deadline."""
    from .league_moves import effective_roster
    from .seasons import clubs as season_clubs
    season = _season_of(day)
    out = {}
    for club in season_clubs(season, root):
        if club != "Miami Heat":
            for p in effective_roster(club, day, season, root):
                if p.get("bbr_id"):
                    out[p["bbr_id"]] = club
    return out


_HOLDERS = {}


def _dated_holder(row, due, root):
    """The option row with the club holding the player on the deadline; None once simulated Miami holds him (its own
    sheet decides) . A player no club holds (waived) keeps the ledger's club, which still owes the contract."""
    if row[0] == "Miami Heat" or not row[1]:
        return row
    key = (str(Path(root).resolve()), due)
    if key not in _HOLDERS:
        _HOLDERS[key] = holders_on(due, root)
    holders = _HOLDERS[key]
    from .rotations import miami_holds
    if row[1] in set(miami_holds(_season_of(due), due, root)):
        return None
    return (holders.get(row[1]) or row[0],) + tuple(row[1:])


def run(day, root=ROOT, evidence_day=None):
    """Decide every option whose deadline is on or before `day` and not yet decided; apply drawn answers.
    Returns (decided now, packets written, applied)."""
    from .season_market import for_date
    root = Path(root)
    season = _season_of(day)
    record = read_record(season, root)
    done = {d["id"] for d in record["decisions"]}
    decided, written = [], []
    rows = [r for r in open_options(season, root) if deadline(r[4], r[3], r[6]) <= day]
    rows = [r for r in (_dated_holder(r, deadline(r[4], r[3], r[6]), root) for r in rows) if r]
    folder = root / draws_dir(season)
    valuations = {}
    for row in rows:
        due = deadline(row[4], row[3], row[6])
        if f"{row[3]}-option-{row[1] or row[2]}-{row[4]}" in done:
            continue
        if due not in valuations:
            valuations[due] = for_date(evidence_day or due, root).valuation   # evidence dated on the deadline
        valuation = valuations[due]
        decision, packet = decide(due, row, valuation, root)
        if decision["id"] in done:
            continue
        if packet:
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / f"{packet['event_id']}.decision.json"
            if not path.exists():
                path.write_text(json.dumps(packet, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
                written.append(packet["event_id"])
            decision["packet"] = path.relative_to(root).as_posix()
        record["decisions"].append(dict(decision, recorded_on=day))
        decided.append(decision)
        done.add(decision["id"])
    applied = apply(record, season, root, day)
    path = root / record_path(season)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return decided, written, applied


def apply(record, season, root, day):
    """Write every decided option into the contracts: an exercised or kept option becomes a contract season; a
    declined option or an opt-out removes it (and every later season of that contract). Returns the applied ids."""
    from .league_contracts import ledger_path
    root = Path(root)
    ledger_file = root / ledger_path(season)
    ledger = json.loads(ledger_file.read_text(encoding="utf-8"))
    by_bbr = {c["bbr_id"]: c for c in ledger["contracts"]}
    sheet_file = root / PLAYER / season / "00_Team/Finances/contract_schedules.json"
    sheet = json.loads(sheet_file.read_text(encoding="utf-8")) if sheet_file.is_file() else {"players": []}
    applied = []
    for d in record["decisions"]:
        if d.get("applied"):
            continue
        if d["decision"] is None:
            result = root / d["packet"].replace(".decision.json", ".decision.result.json")
            if not result.is_file():
                continue
            d["decision"] = json.loads(result.read_text(encoding="utf-8"))["outcome"]
        keep = d["decision"] in ("exercise", "stay")
        s = d["option_season"]
        if d["club"] == "Miami Heat":
            for p in sheet["players"]:
                if p["player"] == d["player"]:
                    _apply_schedule(p, s, keep, d)
        c = by_bbr.get(d["bbr_id"])
        if c:
            _apply_schedule(c, s, keep, d, ledger=True)
        d["applied"] = day
        applied.append(d["id"])
    if applied:
        ledger_file.write_text(json.dumps(ledger, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        if sheet_file.is_file():
            if any(d["club"] == "Miami Heat" for d in record["decisions"] if d["id"] in applied):
                from .signing import refresh_schedule_totals
                refresh_schedule_totals(sheet)
            sheet_file.write_text(json.dumps(sheet, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return applied



def _apply_schedule(entry, s, keep, d, ledger=False):
    note = (f"{d['option_season']} {d['kind'].replace('_', ' ')}: {d['decision']} ({d['deadline']}; {d['how']}; "
            f"runtime/options.py, League/option_decisions.json)")
    if keep:
        if ledger:
            entry.setdefault("options", {}).pop(s, None)
        else:
            entry.setdefault("amount_kind", {})[s] = "contract_salary"
    else:
        for later in [k for k in entry["schedule"] if k >= s]:
            entry["schedule"].pop(later, None)
            (entry.get("options") or {}).pop(later, None)
            (entry.get("amount_kind") or {}).pop(later, None)
            if isinstance(entry.get("guaranteed"), dict):
                entry["guaranteed"].pop(later, None)
    entry.setdefault("option_history", []).append(note)


# -- the ledger's option seasons -----------------------------------------------------------------------------------------
INVENTORY = Path("library/2003/league/nba_2003_contracts.json")
SCALE_2003 = Path("library/2003/league/nba_2003_04_cap_rules.json")
SCALE_SHARE = 1.2


def annotate_ledger(entries, season, root=ROOT):
    """Record each contract's option seasons (`options`) and rookie-scale flag on the ledger entries, in place.

    - Existing contracts from the June 2003 inventory carry its amount kinds for this season on.
    - The 2003 first-round picks (identified by a 2004-05 salary exactly 120% of a pick's second scale year) were
      rebuilt with that one season only: their third scale year (guaranteed) and fourth-year team option (the scale's
      option increase over year three) are restored, the option decided by October 31 of the year before."""
    root = Path(root)
    if season != "2004-05":
        return entries
    inventory = _read(root / INVENTORY) or {"clubs": {}}
    kinds, rookie = {}, set()
    for club in inventory["clubs"].values():
        for p in club["players"]:
            b = p.get("bbr_id")
            if not b:
                continue
            k = {s: v for s, v in (p.get("amount_kind") or {}).items() if s > season and v in OPTION_KINDS}   # this season's were settled in its summer
            if k:
                kinds[b] = k
            if p.get("status") == "under_rookie_contract":
                rookie.add(b)
    scale = (_read(root / SCALE_2003) or {}).get("rookie_scale", {}).get("picks", [])
    for b, c in entries.items():
        if c.get("kind") == "existing" and b in kinds:
            c["options"] = {**kinds[b], **(c.get("options") or {})}
        if b in rookie:
            c["rookie_scale"] = True
        salary = c["schedule"].get("2004-05")
        if c.get("kind") == "existing" and salary and len(c["schedule"]) == 1:
            pick = next((p for p in scale if abs(salary - round(p["year_2"] * SCALE_SHARE)) <= 2), None)
            if pick:
                year3 = round(pick["year_3"] * SCALE_SHARE)
                c["schedule"]["2005-06"] = year3
                c["schedule"]["2006-07"] = round(year3 * (1 + pick["fourth_year_option_increase_percent"] / 100))
                c.setdefault("options", {})["2006-07"] = "team_option"
                c["rookie_scale"] = True
                c["scale_pick_2003"] = pick["pick"]
    return entries


def reapply(entries, season, root=ROOT):
    """Apply the season's recorded option decisions to rebuilt ledger entries (a rebuild never undoes a decision)."""
    for d in read_record(season, root)["decisions"]:
        if d.get("applied") and d.get("bbr_id") in entries and d["club"] != "Miami Heat":
            _apply_schedule(entries[d["bbr_id"]], d["option_season"], d["decision"] in ("exercise", "stay"), d, ledger=True)
    return entries
