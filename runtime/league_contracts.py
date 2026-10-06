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
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAYER = Path("career/Dwyane_Wade")
BIRD_RAISE, OTHER_RAISE = 0.125, 0.10
SCALE_SHARE = 1.20


def ledger_path(season):
    return PLAYER / season / "League/contracts.json"


def _season_after(season, n):
    from .seasons import label, start_year
    return label(start_year(season) + n)


def schedule_for(first_salary, years, start_season, route):
    """{season: salary} for a new contract from its first-year salary and the route it was signed by."""
    raise_share = 0.0 if route in ("minimum", "qualifying_offer") else BIRD_RAISE if route == "bird" else OTHER_RAISE
    return {_season_after(start_season, i): int(round(first_salary * (1 + raise_share * i))) for i in range(max(1, years))}


def rookie_schedule(pick, start_season, scale):
    """A first-round pick's three scale seasons at 120% of the scale amounts (year 4 is a team option)."""
    row = scale.get(pick) or scale[max(scale)]
    return {_season_after(start_season, i): int(round(row[f"year{i + 1}"] * SCALE_SHARE)) for i in range(3)}


def build(season, root=ROOT, market=None):
    """The ledger for `season` from the summer market's record: {bbr_id: entry}."""
    from .contract_terms import existing_terms
    from .free_agency_2004 import calendar, market_year, record_for, year_context
    from .seasons import previous_season
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
    # Miami's carried contracts keep the schedule on its own previous cap sheet (AI/GM records), keyed by the register.
    from .seasons import previous_season
    prev_team = root / PLAYER / previous_season(season) / "00_Team"
    miami_sheet = {}
    if (prev_team / "Finances/contract_schedules.json").is_file():
        ids = {p["name"]: p.get("bbr_id") for p in json.loads((prev_team / "Team/Roster/roster.json").read_text(encoding="utf-8"))["players"]}
        for p in json.loads((prev_team / "Finances/contract_schedules.json").read_text(encoding="utf-8"))["players"]:
            key = p.get("bbr_id") or ids.get(p["player"])
            later = {s_: v for s_, v in (p.get("schedule") or {}).items() if s_ >= season and v}
            if key and later:
                miami_sheet[key] = later
    out = {}
    for club, rows in market["clubs"].items():
        for r in rows:
            b, route = r["bbr_id"], r.get("route")
            if club == "Miami Heat" and route in ("existing", "option") and b in miami_sheet:
                sched, kind = dict(miami_sheet[b]), "existing"
            elif route in ("existing", "option") and b in terms:
                sched = {s: v for s, v in terms[b]["schedule"].items() if v}
                sched.setdefault(season, r["salary"])
                kind = "existing"
            elif route == "rookie_scale" and b in picks:
                sched, kind = rookie_schedule(picks[b], season, scale), "rookie_scale"
            else:
                sched, kind = schedule_for(r["salary"], r.get("years") or 1, season, route), "new"
            out[b] = {"player": r["player"], "bbr_id": b, "club": club, "route": route, "kind": kind,
                      "schedule": dict(sorted(sched.items())), "source": r.get("source")}
            if kind == "rookie_scale":
                out[b]["team_option"] = _season_after(season, 3)
                out[b]["rookie_scale"] = True
            carried_options = (terms.get(b) or {}).get("options") if kind == "existing" else None
            if carried_options:
                out[b]["options"] = dict(carried_options)
            if (terms.get(b) or {}).get("rookie_scale"):
                out[b]["rookie_scale"] = True
    from .options import annotate_ledger, reapply
    annotate_ledger(out, season, root)              # option seasons and the 2003 first-round picks' scale years
    reapply(out, season, root)                      # option decisions already recorded for the season
    return out


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
            out[b] = {"club": c["club"], "salary": c["schedule"][season], "kind": "option" if option else "contract",
                      "option_kind": "team_option" if option else None,
                      "schedule": {s: v for s, v in c["schedule"].items() if s >= season},
                      "options": {s: k for s, k in (c.get("options") or {}).items() if s >= season},
                      "rookie_scale": bool(c.get("rookie_scale")),
                      "source": f"{ledger_path(prev).as_posix()} ({c['kind']})"}
    return out


def under_contract(season, root=ROOT):
    """{bbr_id: {"club", "salary"}} under contract for the season: the season's ledger once written, else the existing
    contracts carried into it (the first offseason: `contract_terms`)."""
    ledger = read(season, root)
    if ledger is not None:
        return {b: {"club": c["club"], "salary": c["schedule"].get(season)} for b, c in ledger.items() if c["schedule"].get(season)}
    if season == "2004-05":
        from .contract_terms import existing_terms
        return {b: {"club": t["club"], "salary": t["salary"]} for b, t in existing_terms(root).items() if t["kind"] == "contract"}
    return {b: {"club": t["club"], "salary": t["salary"]} for b, t in carried(season, root).items() if t["kind"] == "contract"}


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
