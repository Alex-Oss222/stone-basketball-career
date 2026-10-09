"""The league's contract ledger: every player's contract in force for a season, year by year (roadmap 18, R3).

The rollover writes `career/Dwyane_Wade/<season>/League/contracts.json` from the summer market's result
(`runtime/free_agency_2004.py`, or its successor for a later year): each player's club on the opening day and his
salary for each season of the contract. In-season moves change a player's club in `league_moves.json`; the contract
travels with him (a trade assigns it). The next offseason reads the ledger to know who is already under contract:
that is what makes the career roll from one year to the next without real contract data.

Salary by season: an existing contract keeps its recorded schedule (`runtime/contract_terms.py` for the first
offseason). A new contract's later years rise from its first-year salary by the agreement's raise limit (1999
agreement: 12.5% of the first year for a club re-signing its own free agent with Bird rights, 10% otherwise; a minimum
contract stays at the minimum scale). A first-round pick's scale contract runs three seasons at the scale's amounts
(120% of scale, era practice) with a fourth-year team option. Option years stay options: decided on their dates.
A contract extension (`runtime/extensions.py`, from October 31, 2005) adds its seasons to the contract it extends and
travels with it: `extension` names it, the rollover carries it, a rebuild re-applies it; a contract without one reads as
before.

Miami's contracts are its own cap sheet's (AI/GM records): a Miami row the market carried (`existing` or `option`) takes
the previous sheet's schedule from the season on and its rookie-scale flag (route or status, until an extension's first
season); its option seasons are the carried ledger row's still in that schedule with the sheet's open ones
(`amount_kind`) laid over them (a contract Miami took by trade is on its sheet with every season `contract_salary`). Wade is keyed by his NBA id, wadedw01, like every other player
(`ledger_key`): his sheet and register rows carry no bbr_id (alternate history) and the summer market names him by his
register key, dwyane_wade. Until the 2005-10-31 repair the sheet lookup missed him, so the 2004-05 build priced his
rookie-scale contract as a new one from the market's first-year salary (2,361,800 raised 10% a season: 2,597,980 and
2,834,160 for 2005-06 and 2006-07, where the sheet holds 2,526,600 and 3,201,202) and the 2005-06 build carried those
figures; `repair_wade_rows` rewrote both rows to the sheet. The closed 2004-05 ledger keeps the register key: the
recorded 2005 market and the 2004-05 valuations read it under that key, which no evidence record carries, so neither
priced him, and a new key would change their replay. For the same reason the 2005-06 valuation fit (`under_contract`)
leaves his re-keyed row out; it counts from FIT_FROM like every contract. `miami_sheet_errors` holds every Miami row of
every season's ledger to the full schedule of one of his rows on Miami's sheet of that season.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAYER = Path("career/Dwyane_Wade")
BIRD_RAISE, OTHER_RAISE = 0.125, 0.10
SCALE_SHARE = 1.20
MIAMI = "Miami Heat"
WADE, WADE_BBR, WADE_REGISTER = "Dwyane Wade", "wadedw01", "dwyane_wade"
WADE_KEYS = (WADE_BBR, WADE_REGISTER)
NBA_KEY_FROM = "2005-06"               # the first ledger keyed by Wade's NBA id (the repair; later seasons by `build`)
FIT_FROM = "2006-07"                   # the first season whose valuation fit counts his row (`under_contract`)
SHEET_GONE = ("released", "traded", "waived", "voided", "renounced", "signed_elsewhere")   # as `options.open_options`


def ledger_path(season):
    return PLAYER / season / "League/contracts.json"


# -- keys ----------------------------------------------------------------------------------------------------------------
def ledger_key(b, name=None):
    """The ledger key for a market, register or sheet key: Wade's register key (the summer market's and Miami register's
    id for him, `free_agency_2004.miami_contracts`) and a keyless row named Dwyane Wade are his NBA id; any other key is
    itself."""
    if b == WADE_REGISTER or (not b and name == WADE):
        return WADE_BBR
    return b


def wade_key(entries):
    """Wade's key in a ledger's {key: entry}: his NBA id, or the register key of a ledger written before the 2005-10-31
    repair (the closed 2004-05 ledger keeps it, see the module note)."""
    return WADE_REGISTER if WADE_REGISTER in entries and WADE_BBR not in entries else WADE_BBR


def find(entries, b):
    """A player's entry in a ledger's {key: entry} by any of his keys (Wade: his NBA id, else an older ledger's register
    key), or None."""
    return entries.get(wade_key(entries)) if b in WADE_KEYS else entries.get(b)


def sheet_key(p, ids):
    """A Miami cap-sheet row's key: its bbr_id, else the register's for the name ({name: bbr_id}), else Wade's NBA id for
    his row (his sheet and register rows carry none: alternate history)."""
    return p.get("bbr_id") or ids.get(p["player"]) or (WADE_BBR if p["player"] == WADE else None)


def sheet_terms(p, season):
    """(schedule from `season` on, open option seasons, rookie-scale flag) of a Miami cap-sheet row, Miami's own record of
    the contract: the option seasons are its `amount_kind` options still in the schedule; a rookie-scale contract (route
    or status) stops being one from its extension's first season, as `carried` reads it."""
    from .options import OPTION_KINDS
    sched = {s: v for s, v in (p.get("schedule") or {}).items() if s >= season and v}
    options = {s: k for s, k in sorted((p.get("amount_kind") or {}).items()) if s in sched and k in OPTION_KINDS}
    ext = p.get("extension")
    rookie = (p.get("route") == "rookie_scale" or p.get("status") == "under_rookie_contract") \
        and not (ext and season >= ext["first_season"])
    return sched, options, bool(rookie)


def _miami_rows(season, root):
    """({key: [sheet rows]}, {name: [sheet rows]}) of Miami's cap sheet for `season`, or None without one."""
    team = Path(root) / PLAYER / season / "00_Team"
    path = team / "Finances/contract_schedules.json"
    if not path.is_file():
        return None
    register = team / "Team/Roster/roster.json"
    ids = ({p["name"]: p.get("bbr_id") for p in json.loads(register.read_text(encoding="utf-8"))["players"]}
           if register.is_file() else {})
    by_key, by_name = {}, {}
    for p in json.loads(path.read_text(encoding="utf-8"))["players"]:
        k = sheet_key(p, ids)
        if k:
            by_key.setdefault(k, []).append(p)
        by_name.setdefault(p["player"], []).append(p)
    return by_key, by_name


def _season_after(season, n):
    from .seasons import label, start_year
    return label(start_year(season) + n)


def schedule_for(first_salary, years, start_season, route):
    """{season: salary} for a new contract from its first-year salary and the route it was signed by."""
    from .agreement import raise_share as agreement_raise                 # 12.5/10% (1999); 10.5/8% from the 2005 agreement
    if route == "minimum" and years > 1:
        steps = minimum_steps(first_salary, years, start_season)
        if steps:
            return steps
    raise_share = agreement_raise(route, start_season)
    return {_season_after(start_season, i): int(round(first_salary * (1 + raise_share * i))) for i in range(max(1, years))}


def minimum_steps(first_salary, years, start_season):
    """A multi-season minimum contract pays each season's minimum for the player's service that season (one more year
    each season), so a later season never falls under the league minimum. The first-year salary names his service on
    the scale; None when it is not a scale amount (then the flat schedule stands)."""
    from .cba import minimum_salary
    service = next((n for n in range(11) if minimum_salary(n, start_season) == first_salary), None)
    if service is None:
        return None
    return {_season_after(start_season, i): minimum_salary(service + i, _season_after(start_season, i)) for i in range(years)}


def rookie_schedule(pick, start_season, scale):
    """A first-round pick's scale seasons at 120% of the scale amounts: three (1999 agreement; year 4 a team option
    recorded apart) or all four from the 2005 agreement (two guaranteed, team options on years 3 and 4, `rookie_options`)."""
    from .agreement import terms
    row = scale.get(pick) or scale[max(scale)]
    t = terms(start_season)
    n = 3 if t["agreement"] == "1999" else max(t["rookie_option_years"])
    return {_season_after(start_season, i): int(round(row[f"year{i + 1}"] * SCALE_SHARE)) for i in range(n) if f"year{i + 1}" in row}


def rookie_options(start_season):
    """{season: "team_option"} for a rookie-scale contract signed for `start_season` (`agreement.terms`)."""
    from .agreement import terms
    return {_season_after(start_season, n - 1): "team_option" for n in terms(start_season)["rookie_option_years"]}


def build(season, root=ROOT, market=None):
    """The ledger for `season` from the summer market's record: {bbr_id: entry}."""
    from .contract_terms import existing_terms
    from .free_agency_2004 import calendar, market_year, record_for, year_context
    from .seasons import club_name, previous_season
    root = Path(root)
    year = market_year(season)
    market = market or json.loads((root / record_for(season)).read_text(encoding="utf-8"))
    terms = existing_terms(root) if season == "2004-05" else carried(season, root)
    with year_context(year, root):
        scale = calendar(root)["scale"]
    picks = {}
    draft = root / PLAYER / previous_season(season) / f"09_Draft/draft_{year}.json"
    if draft.is_file():
        picks = {p["bbr_id"]: p["pick"] for p in json.loads(draft.read_text(encoding="utf-8"))["picks"] if p.get("bbr_id") and p["round"] == 1}
    # Miami's carried contracts keep its own previous cap sheet's schedule and rookie-scale flag and add its open option
    # seasons (AI/GM records), keyed as the ledger keys them (`sheet_key`: Wade by his NBA id, as `ledger_key` keys the
    # market's row).
    prev_team = root / PLAYER / previous_season(season) / "00_Team"
    miami_sheet = {}
    if (prev_team / "Finances/contract_schedules.json").is_file():
        ids = {p["name"]: p.get("bbr_id") for p in json.loads((prev_team / "Team/Roster/roster.json").read_text(encoding="utf-8"))["players"]}
        for p in json.loads((prev_team / "Finances/contract_schedules.json").read_text(encoding="utf-8"))["players"]:
            key = sheet_key(p, ids)
            later, options, rookie = sheet_terms(p, season)
            if key and later:
                miami_sheet[key] = {"schedule": later, "options": options, "rookie": rookie}
    out = {}
    for club, rows in market["clubs"].items():
        for r in rows:
            b, route = ledger_key(r["bbr_id"], r.get("player")), r.get("route")
            t = find(terms, b) or {}                   # an older ledger carries Wade under his register key
            sheet = miami_sheet.get(b) if club == MIAMI and route in ("existing", "option") else None
            if sheet:
                sched, kind = dict(sheet["schedule"]), "existing"
            elif route in ("existing", "option") and t:
                sched = {s: v for s, v in t["schedule"].items() if v}
                sched.setdefault(season, r["salary"])
                kind = "existing"
            elif route == "rookie_scale" and b in picks:
                sched, kind = rookie_schedule(picks[b], season, scale), "rookie_scale"
            else:
                sched, kind = schedule_for(r["salary"], r.get("years") or 1, season, route), "new"
            out[b] = {"player": WADE if b == WADE_BBR else r["player"], "bbr_id": b, "club": club_name(club, season),
                      "route": route, "kind": kind, "schedule": dict(sorted(sched.items())), "source": r.get("source")}
            if kind == "rookie_scale":
                out[b]["team_option"] = _season_after(season, 3)
                out[b]["rookie_scale"] = True
                if season >= "2005-06":                     # 2005 agreement: options on years 3 and 4 (both in the schedule)
                    out[b]["options"] = rookie_options(season)
            carried_options = t.get("options") if kind == "existing" else None
            if sheet:
                # the carried ledger's option seasons still in the schedule, Miami's sheet's own laid over them: a
                # contract Miami took by trade is on its sheet with every season `contract_salary` (`trades._ledger_inventory`,
                # `rollover.traded_in`), so the sheet alone would erase his option; a decided option is gone from both
                # (`options._apply_schedule` writes the ledger row and the sheet row), so neither brings one back
                carried_options = {s: k for s, k in sorted({**(t.get("options") or {}), **sheet["options"]}.items()) if s in sched}
            if carried_options:
                out[b]["options"] = dict(carried_options)
            if t.get("rookie_scale") or (sheet and sheet["rookie"]):
                out[b]["rookie_scale"] = True
            if kind == "existing" and t.get("extension"):
                _carry_extension(out[b], t)
    from .options import annotate_ledger, reapply
    annotate_ledger(out, season, root)              # option seasons and the 2003 first-round picks' scale years
    reapply(out, season, root)                      # option decisions already recorded for the season
    from .extensions import reapply as reapply_extensions
    reapply_extensions(out, season, root)           # extensions already signed in the season
    return out


def _carry_extension(entry, carried_terms):
    """An extended contract carried into a new season keeps its extension record (`runtime/extensions.py`)."""
    from copy import deepcopy
    for field in ("extension", "earlier_extensions", "extended_on", "extension_history"):
        if carried_terms.get(field) is not None:
            entry[field] = deepcopy(carried_terms[field])
    entry["source"] = f"{entry.get('source') or ''}; extended {carried_terms.get('extended_on')}".lstrip("; ")


def write(season, root=ROOT, market=None):
    entries = build(season, root, market)
    path = Path(root) / ledger_path(season)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema_version": 1, "season": season, "kind": "league_contracts",
                                "rule": __doc__.split("\n\n", 1)[1].strip(),
                                "contracts": [entries[b] for b in sorted(entries)]}, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    return path


def read(season, root=ROOT):
    """{bbr_id: entry} for the season's ledger, or None before the rollover wrote it."""
    path = Path(root) / ledger_path(season)
    if not path.is_file():
        return None
    return {c["bbr_id"]: c for c in json.loads(path.read_text(encoding="utf-8"))["contracts"]}


def carried(season, root=ROOT):
    """Contracts running into `season` from the season before's ledger, shaped like `contract_terms.existing_terms`
    (club as the league held him at that season's end). A later offseason's existing contracts."""
    from .seasons import previous_season
    prev = previous_season(season)
    ledger = read(prev, root) or {}
    out = {}
    for b, c in ledger.items():
        if c["schedule"].get(season):
            option = c.get("team_option") == season
            extension = c.get("extension")
            out[b] = {"club": c["club"], "salary": c["schedule"][season], "kind": "option" if option else "contract",
                      "option_kind": "team_option" if option else None,
                      "schedule": {s: v for s, v in c["schedule"].items() if s >= season},
                      "options": {s: k for s, k in (c.get("options") or {}).items() if s >= season},
                      # an extended rookie-scale contract is a veteran contract from its first extension season
                      "rookie_scale": bool(c.get("rookie_scale")) and not (extension and season >= extension["first_season"]),
                      "source": f"{ledger_path(prev).as_posix()} ({c['kind']})"}
            if extension:
                for field in ("extension", "earlier_extensions", "extended_on", "extension_history"):
                    if c.get(field) is not None:
                        out[b][field] = c[field]
    return out


def under_contract(season, root=ROOT):
    """{bbr_id: {"club", "salary"}} under contract for the season: the season's ledger once written, else the existing
    contracts carried into it (the first offseason: `contract_terms`). Read by the valuation fit (`valuation.Valuation`):
    Wade's NBA-id row counts from FIT_FROM; the 2005-06 fit never saw his row (its register key matched no evidence
    record), so the season's recorded valuations replay unchanged (module note)."""
    ledger = read(season, root)
    if ledger is not None:
        return {b: {"club": c["club"], "salary": c["schedule"].get(season)} for b, c in ledger.items()
                if c["schedule"].get(season) and not (b == WADE_BBR and season < FIT_FROM)}
    if season == "2004-05":
        from .contract_terms import existing_terms
        return {b: {"club": t["club"], "salary": t["salary"]} for b, t in existing_terms(root).items() if t["kind"] == "contract"}
    return {b: {"club": t["club"], "salary": t["salary"]} for b, t in carried(season, root).items()
            if t["kind"] == "contract" and not (b == WADE_BBR and season < FIT_FROM)}


def refresh_holders(season, on, root=ROOT, write=True):
    """Set each contract's `club` to the club holding the player on `on` in the simulated league (a trade assigns the
    contract; `league_moves.effective_roster`, Miami's register for Miami). The club that signed it stays as
    `signed_club`. A player no club holds (waived) keeps the club that owes the contract. Derived from the dated moves,
    so `scripts/reconcile.py` rebuilds it; returns the bbr_ids whose club changed."""
    from .club_truth import holder
    root = Path(root)
    path = root / ledger_path(season)
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    changed = []
    for c in data["contracts"]:
        club, _ = holder(c["bbr_id"], c.get("player"), on, root)     # the one club answer (runtime/club_truth.py)
        if club and club != c["club"]:
            c.setdefault("signed_club", c["club"])
            c["club"] = club
            changed.append(c["bbr_id"])
    if changed and write:
        path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return changed


# -- Miami's rows against its own sheet ---------------------------------------------------------------------------------
def _live(rows):
    """The sheet rows Miami still holds (not released, traded, waived, voided...), else every row."""
    live = [p for p in rows if not any(w in (p.get("status") or "") for w in SHEET_GONE)]
    return live or rows


def _later(schedule, season):
    """{season: amount} of a schedule from `season` on, its non-zero amounts (`continuity._later`)."""
    return {s: int(v) for s, v in (schedule or {}).items() if s >= season and v}


def miami_sheet_errors(season, root=ROOT):
    """Every Miami row of the season's ledger carries the full schedule of one of the player's rows on Miami's own cap
    sheet of the season (AI/GM records, the authority for Miami's contracts): the same seasons and amounts from the
    season on (`_later`, as continuity compared carried contracts), so a season the sheet dropped or kept (a declined
    option, an opt-out) and a sheet row with no schedule (draft rights) never pass for the ledger's contract. His rows
    are those of the same key (`sheet_key`; Wade by his NBA id, an older ledger's register key read as his,
    `ledger_key`), else of the same name. Any of them may carry it (the ledger holds one contract a player: a waived
    contract still owed stays his ledger row when he signs again, `refresh_holders`). A Miami row the sheet does not
    hold, or that no row of his carries, is an error."""
    root = Path(root)
    ledger = read(season, root)
    rows = _miami_rows(season, root)
    if ledger is None or rows is None:
        return []
    by_key, by_name = rows
    rel = ledger_path(season).as_posix()
    errors = []
    for b, c in sorted(ledger.items()):
        if c.get("club") != MIAMI:
            continue
        key = ledger_key(b, c.get("player"))
        found = by_key.get(key) or by_name.get(WADE if key == WADE_BBR else c.get("player")) or []
        if not found:
            errors.append(f"{rel}: {c.get('player')} ({b}) is Miami's in the ledger but has no row on Miami's {season} cap sheet")
            continue
        if not any(_later(c["schedule"], season) == _later(p.get("schedule"), season) for p in found):
            errors.append(f"{rel}: {c.get('player')} ({b}): the ledger's {_later(c['schedule'], season)} differs from Miami's "
                          f"{season} cap sheet {_later(_live(found)[-1].get('schedule'), season)} (Miami's sheet is the "
                          f"authority for Miami's contracts)")
    return errors


def sheet_errors(root=ROOT):
    """`miami_sheet_errors` for every season with a ledger."""
    root = Path(root)
    errors = []
    for path in sorted((root / PLAYER).glob("*/League/contracts.json")):
        errors += miami_sheet_errors(path.parts[-3], root)
    return errors


# -- the 2005-10-31 repair ----------------------------------------------------------------------------------------------
def wade_row(season, row, sheet_row, decisions, key):
    """Wade's ledger row for `season` from Miami's sheet row of that season (`sheet_terms`: schedule, open option seasons,
    rookie-scale flag), keyed `key`, keeping the row's club, route, source and extension fields; each applied option
    decision of his in the season's record leaves its `option_history` line once (`options.history_note`)."""
    from .options import history_note
    sched, options, rookie = sheet_terms(sheet_row, season)
    out = {k: v for k, v in row.items() if k not in ("options", "rookie_scale", "option_history")}
    out.update(player=WADE, bbr_id=key, kind="existing", schedule=dict(sorted(sched.items())))
    if options:
        out["options"] = options
    if rookie:
        out["rookie_scale"] = True
    history = list(row.get("option_history") or [])
    for d in decisions:
        if d.get("bbr_id") == WADE_BBR and d.get("club") == MIAMI and d.get("decision") and d.get("applied"):
            if history_note(d) not in history:
                history.append(history_note(d))
    if history:
        out["option_history"] = history
    return out


def repair_wade_rows(root=ROOT, seasons=None, write=True):
    """Data repair for the career clock of 2005-10-31: Wade's row in each season's ledger (default: every season with a
    ledger and a Miami sheet) is rewritten to Miami's sheet of that season (`wade_row`), keyed by his NBA id from
    NBA_KEY_FROM; the closed 2004-05 ledger keeps his register key (module note). A ledger holding him under both keys
    keeps one row. Idempotent: a second run changes nothing. Returns [{"season", "path", "before", "after"}] for the
    rows it changed (written unless `write` is False)."""
    from .options import read_record
    root = Path(root)
    wanted = seasons or sorted(p.parts[-3] for p in (root / PLAYER).glob("*/League/contracts.json"))
    changes = []
    for season in wanted:
        path = root / ledger_path(season)
        rows = _miami_rows(season, root)
        if not path.is_file() or rows is None:
            continue
        sheet_row = next(iter(_live(rows[0].get(WADE_BBR, []))[-1:]), None)
        data = json.loads(path.read_text(encoding="utf-8"))
        contracts = data["contracts"]
        mine = [i for i, c in enumerate(contracts) if c["bbr_id"] in WADE_KEYS]
        if sheet_row is None or not mine:
            continue
        entries = {contracts[i]["bbr_id"]: contracts[i] for i in mine}
        key = WADE_BBR if season >= NBA_KEY_FROM else wade_key(entries)
        before = entries.get(key) or contracts[mine[0]]
        after = wade_row(season, before, sheet_row, read_record(season, root)["decisions"], key)
        if len(mine) == 1 and contracts[mine[0]] == after:
            continue
        kept = [c for i, c in enumerate(contracts) if i not in mine]
        at = next((i for i, c in enumerate(kept) if c["bbr_id"] > key), len(kept))
        data["contracts"] = kept[:at] + [after] + kept[at:]
        if write:
            path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        changes.append({"season": season, "path": ledger_path(season).as_posix(), "before": [contracts[i] for i in mine],
                        "after": after})
    return changes
