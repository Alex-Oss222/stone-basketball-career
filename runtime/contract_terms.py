"""Which real players carry an existing contract into 2004-05, and on what terms (roadmap 14b phase 5).

"Existing" means signed on or before June 30, 2004: the simulated offseason decides everything after. Sources, in
order, every one reconstructing a term that already existed (AGENTS.md: a later source may do that, never reveal a
later choice):
1. the June 2003 contract inventory (`nba_2003_contracts.json`): a 2004-05 salary of kind `contract_salary`;
2. a summer-2003 signing with reported years and total (`nba_2003_offseason_transactions.json`, not involving Miami);
3. the 2004-05 salary list (`nba_2004_05_salaries.json`), only for a player who made no 2004 offseason move
   (signing, re-signing, offer sheet or match, sign-and-trade, rookie or undrafted signing, accepted qualifying offer)
   and was not a 2004 free agent or option case (`nba_2004_free_agent_rights.json`).
An option year for 2004-05 (team, player or early termination) is an `option`: decided in the simulated offseason,
never by the real outcome, with one exception: a rookie-scale fourth-year team option (1999 agreement) was due by
October 31 of the third season, so a 2004-05 rookie option was decided in history on or before October 31, 2003, before
the simulated league began; it counts as exercised when the player is on the 2004-05 salary list, else declined.
A 2003 first-round pick (2003 draft rights, listed above the second-year minimum) is on the 1999 rookie scale: three
guaranteed seasons through 2005-06 (the 2005-06 amount unknown, held as None) and a 2006-07 team option.
Miami's contracts are its own ledger and are not read here.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEASON = "2004-05"
INVENTORY = Path("library/2003/league/nba_2003_contracts.json")
SIGNINGS_2003 = Path("library/2003/league/nba_2003_offseason_transactions.json")
SIGNINGS_2004 = Path("library/2004/league/nba_2004_offseason_transactions.json")
RIGHTS_2004 = Path("library/2004/league/nba_2004_free_agent_rights.json")
SALARIES = Path("library/2004/league/nba_2004_05_salaries.json")
OPTION_KINDS = ("team_option", "player_option", "early_termination_option")
REGISTRY = Path("career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json")
SECOND_YEAR_MINIMUM = 620_046
MOVE_KINDS = ("signing", "re_sign", "offer_sheet", "match", "match_declined", "sign_and_trade", "rookie_signing",
              "undrafted_rookie_signing", "qualifying_offer_accepted")


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _later_seasons(schedule):
    return {s: v for s, v in schedule.items() if s >= SEASON and v}


def existing_terms(root=ROOT):
    """{bbr_id: {"salary", "kind" ("contract" or "option"), "option_kind", "schedule", "source"}}."""
    root = Path(root)
    out = {}
    listed = {p.get("bbr_id"): p["salary"] for e in _read(root / SALARIES)["clubs"].values() for p in e["players"] if p.get("bbr_id")}
    for club, entry in _read(root / INVENTORY)["clubs"].items():
        if club == "Miami Heat":
            continue
        for p in entry["players"]:
            b, sched = p.get("bbr_id"), p.get("schedule") or {}
            if not b or not sched.get(SEASON):
                continue
            kind = (p.get("amount_kind") or {}).get(SEASON)
            if kind == "team_option" and p.get("status") == "under_rookie_contract":
                if b not in listed:                         # declined by October 31, 2003, in history
                    continue
                out[b] = {"salary": int(sched[SEASON]), "kind": "contract", "option_kind": None, "schedule": {SEASON: int(sched[SEASON])},
                          "source": f"{INVENTORY.as_posix()} (rookie option exercised by 2003-10-31: on the 2004-05 list)"}
                continue
            out[b] = {"salary": int(sched[SEASON]), "kind": "option" if kind in OPTION_KINDS else "contract",
                      "option_kind": kind if kind in OPTION_KINDS else None, "schedule": _later_seasons(sched),
                      "source": INVENTORY.as_posix()}
    for row in _read(root / SIGNINGS_2003)["signings"]:
        b = row.get("bbr_id")
        if not b or row.get("involves_miami") or not (row.get("years") and row.get("total")) or b in out:
            continue
        if row["years"] >= 2:                               # a 2003 signing that covers 2004-05
            per = int(round(row["total"] / row["years"]))
            seasons = [f"{2003 + i}-{str(2004 + i)[-2:]}" for i in range(row["years"])]
            out[b] = {"salary": per, "kind": "contract", "option_kind": None, "schedule": {s: per for s in seasons if s >= SEASON},
                      "source": f"{SIGNINGS_2003.as_posix()} (reported total, spread flat)"}
    moved = {r.get("bbr_id") for r in _read(root / SIGNINGS_2004)["signings"] if r.get("kind") in MOVE_KINDS}
    rights = _read(root / RIGHTS_2004)
    free = {fa.get("bbr_id") for club in rights.get("clubs", {}).values() for fa in club.get("free_agents", [])}
    registry = _read(root / REGISTRY)
    rookies = {p["bbr_id"] for p in (registry["players"] if isinstance(registry, dict) else registry)
               if p.get("cohort") == "2003_draft_rights" and p.get("bbr_id")}
    for club, entry in _read(root / SALARIES)["clubs"].items():
        if club == "Miami Heat":
            continue
        for p in entry["players"]:
            b = p.get("bbr_id")
            if not b or b in out or b in moved or b in free or (p.get("note") or "").startswith(("released", "retired")):
                continue
            row = {"salary": p["salary"], "kind": "contract", "option_kind": None, "schedule": {SEASON: p["salary"]},
                   "source": f"{SALARIES.as_posix()} (reconstructed: no 2004 offseason move)"}
            if b in rookies and p["salary"] > SECOND_YEAR_MINIMUM:
                row["schedule"]["2005-06"] = None           # guaranteed, amount unknown
                row["team_option"] = "2006-07"
                row["source"] += "; 1999 rookie scale"
            out[b] = row
    return out


def free_agents(root=ROOT):
    """{bbr_id: {"type", "club", "service", "prior_salary", "birth_date"}}: the 2004 free agents by rights (world data
    for who was free and with whose rights, never where they went)."""
    out = {}
    for club, entry in _read(Path(root) / RIGHTS_2004).get("clubs", {}).items():
        for fa in entry.get("free_agents", []):
            if fa.get("bbr_id"):
                out[fa["bbr_id"]] = {"player": fa["player"], "type": fa.get("type"), "rights_club": club,
                                     "service": fa.get("nba_seasons_before_2004_05"), "prior_salary": fa.get("prior_salary_2003_04"),
                                     "birth_date": fa.get("birth_date"), "real_miami": bool(fa.get("real_miami_player"))}
    return out
