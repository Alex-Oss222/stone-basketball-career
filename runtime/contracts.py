"""League-wide contracts and the salary cap (stage 1 of simulating every team).

Reads the June 26, 2003 contract inventory and each season's cap rules, and
answers the questions every simulated front office asks: what a club has
committed, what is conditional, what holds sit on its books, and whether the
cap figures it would need are public yet.

Miami's own sheet (`00_Team/Finances/contract_schedules.json`) stays
authoritative for Miami; this module never overrides it.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS_PATH = Path("library/2003/league/nba_2003_contracts.json")
EXPIRING_PATH = Path("library/2003/league/nba_2003_expiring_contracts.json")
CAP_HISTORY_PATH = Path("career/Dwyane_Wade/2003-04/00_Team/Finances/league_cap_history.json")
MIAMI_SHEET_PATH = Path("career/Dwyane_Wade/2003-04/00_Team/Finances/contract_schedules.json")
CHECKPOINT = "2003-06-26"

COMMITTED = {"contract_salary", "early_termination_option"}
CONDITIONAL = {"team_option", "player_option"}
UNVERIFIED = {"unverified_minimum_contract_year"}
HOLDS = {"draft_hold"}
DEAD = {"dead_money"}
KNOWN_KINDS = COMMITTED | CONDITIONAL | UNVERIFIED | HOLDS | DEAD | {"unsigned_rights"}
# Phrases that would reveal a post-checkpoint transaction. Validation refuses them.
LEAK_PATTERNS = (r"signed a new contract after", r"after the checkpoint\)", r"signed_elsewhere_after",
                 r"released \d+/\d+/0[4-9]", r"released (0?[7-9]|1[0-2])/\d+/03")


def read(path, root=ROOT):
    return json.loads((Path(root) / path).read_text(encoding="utf-8"))


def cap_rules_path(season):
    start = int(season[:4])
    return Path(f"library/{start}/league/nba_{start}_{season[-2:]}_cap_rules.json")


def cap_rules(season, as_of, root=ROOT):
    """Cap figures a front office may use on `as_of`. Refused before the real publication date."""
    rules = read(cap_rules_path(season), root)
    history = {row["season"]: row for row in read(CAP_HISTORY_PATH, root)["seasons"]}
    published = history.get(season, {}).get("published_date")
    if not published:
        raise ValueError(f"{season} cap publication date is not recorded; the figures are reference only")
    if as_of < published:
        raise ValueError(f"{season} cap is not published until {published}")
    return rules


def rookie_scale(pick, root=ROOT, season="2003-04"):
    scale = read(cap_rules_path(season), root)["rookie_scale"]
    if not scale:
        raise ValueError(f"no rookie scale recorded for {season}")
    return next(row for row in scale["picks"] if row["pick"] == pick)


def club_ledger(club_name, season, root=ROOT):
    """Amounts on a club's books for `season`, by kind. Unresolved players are listed, never priced."""
    club = read(CONTRACTS_PATH, root)["clubs"][club_name]
    ledger = {"committed": 0, "conditional": 0, "unverified": 0, "holds": 0, "dead_money": 0,
              "expiring": [], "unresolved": [], "missing_amounts": []}
    rows = club["players"] + club.get("draft_rights", []) + club.get("released_players", [])
    if club_name == "Miami Heat":
        # Miami's own sheet is authoritative; it resolves rows the league inventory could not.
        sheet = {p["player"]: p for p in read(MIAMI_SHEET_PATH, root)["players"]}
        rows = [dict(sheet[p["player"]], status="miami_sheet") if p["player"] in sheet and
                p["status"] in ("expired_or_unresolved", "free_agent_unlisted") else p for p in rows]
    for p in rows:
        if p["status"] == "free_agent_expiring":
            ledger["expiring"].append(p["player"])
            continue
        if p["status"] in ("expired_or_unresolved", "free_agent_unlisted"):
            ledger["unresolved"].append(p["player"])
            continue
        amount, kind = p.get("schedule", {}).get(season), p.get("amount_kind", {}).get(season)
        if kind is None:
            continue
        if amount is None:
            if kind != "unsigned_rights":
                ledger["missing_amounts"].append(p["player"])
            continue
        bucket = ("committed" if kind in COMMITTED else "conditional" if kind in CONDITIONAL
                  else "unverified" if kind in UNVERIFIED else "holds" if kind in HOLDS
                  else "dead_money" if kind in DEAD else None)
        if bucket:
            ledger[bucket] += amount
    for p in club["players"]:
        if p["status"] == "under_contract_unverified" and p.get("schedule", {}).get(season) is not None:
            # Counted as committed above, but flagged: continuity from before the checkpoint is unconfirmed.
            ledger.setdefault("unconfirmed_continuity", []).append(p["player"])
    ledger["known_total"] = ledger["committed"] + ledger["conditional"] + ledger["unverified"] + ledger["holds"] + ledger["dead_money"]
    return ledger


def contract_errors(root=ROOT):
    errors = []
    try:
        data = read(CONTRACTS_PATH, root)
        expiring = read(EXPIRING_PATH, root)
    except (OSError, ValueError) as exc:
        return [f"cannot load contract inventory: {exc}"]
    if data.get("as_of") != CHECKPOINT or len(data.get("clubs", {})) != 29:
        errors.append("contract inventory must be dated 2003-06-26 and cover 29 clubs")
    text = json.dumps(data) + json.dumps(expiring)
    for pattern in LEAK_PATTERNS:
        if re.search(pattern, text, re.I):
            errors.append(f"contract data contains post-checkpoint information matching {pattern!r}")
    statuses = set(data["status_legend"])
    horizon = set(data["horizon"])
    ids = set()
    for club, entry in data["clubs"].items():
        for p in entry["players"] + entry.get("draft_rights", []) + entry.get("released_players", []):
            where = f"{club}: {p.get('player')}"
            if p.get("status") not in statuses | {"unsigned_first_round_draft_rights", "unsigned_second_round_draft_rights",
                                                  "released_before_checkpoint"}:
                errors.append(f"{where}: unknown status {p.get('status')!r}")
            for season, amount in p.get("schedule", {}).items():
                if season not in horizon:
                    errors.append(f"{where}: season {season} outside horizon")
                if amount is not None and (not isinstance(amount, int) or amount < 0):
                    errors.append(f"{where}: invalid amount for {season}")
                if p.get("amount_kind", {}).get(season) not in KNOWN_KINDS:
                    errors.append(f"{where}: unknown amount kind for {season}")
            if p.get("bbr_id"):
                if p["bbr_id"] in ids and p.get("status") != "released_before_checkpoint":
                    errors.append(f"{where}: duplicate bbr_id {p['bbr_id']}")
                ids.add(p["bbr_id"])
    expiring_ids = {p["bbr_id"] for p in expiring["players"]}
    inventory_expiring = {p["bbr_id"] for e in data["clubs"].values() for p in e["players"] if p["status"] == "free_agent_expiring"}
    if expiring_ids != inventory_expiring:
        errors.append("expiring-contract list and inventory disagree")
    for path in sorted((Path(root) / "library").glob("*/league/nba_*_cap_rules.json")):
        rules = json.loads(path.read_text(encoding="utf-8"))
        if cap_rules_path(rules.get("season", "0000-00")) != path.relative_to(root):
            errors.append(f"{path.relative_to(root)}: season label does not match file name")
        if not isinstance(rules.get("salary_cap"), int):
            errors.append(f"{path.relative_to(root)}: salary_cap missing")
    rules = read(cap_rules_path("2003-04"), root)
    history = {row["season"]: row["salary_cap"] for row in read(CAP_HISTORY_PATH, root)["seasons"]}
    for path in sorted((Path(root) / "library").glob("*/league/nba_*_cap_rules.json")):
        r = json.loads(path.read_text(encoding="utf-8"))
        if r["season"] in history and history[r["season"]] != r["salary_cap"]:
            errors.append(f"{r['season']}: cap rules and Miami's cap history disagree")
    wade = next((p for p in data["clubs"]["Miami Heat"]["draft_rights"] if p["player"] == "Dwyane Wade"), None)
    if not wade or wade["current_cap_hold"] != rules["rookie_scale"]["picks"][4]["year_1"]:
        errors.append("Wade's draft hold must equal the No. 5 rookie-scale first-year amount")
    return errors
