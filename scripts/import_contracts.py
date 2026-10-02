#!/usr/bin/env python3
"""One-time import of the uploaded 2003 contract inventory, free-agent list and cap rules.

Reads the raw uploads under docs/ and writes library files with every piece of
information dated after the June 26, 2003 checkpoint removed or recast:

* notes and bases that say a player signed elsewhere after June 30, 2003;
* the description of the June 27, 2003 trade;
* a release dated after the checkpoint;
* "restricted" free-agent marks. A player is restricted only if his club made a
  qualifying offer, which is a June 30 club decision the simulation makes for
  itself. The mark is kept only as evidence that he was *eligible* for
  restricted free agency.

The raw uploads are deleted after a successful import; the report records what
was changed and why.
"""
import json
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "docs/nba_2003_contracts_and_rules/library"
RAW_FA = ROOT / "docs/nba_2003_free_agents.json"
OUT = ROOT / "library"
CHECKPOINT = "2003-06-26"
UNRESOLVED_NOTE = ("No 2003-04 commitment could be established from sources dated on or before the "
                   "checkpoint. How the player's status resolves is a simulated event.")
EXPIRING_NOTE = ("Contract expires June 30, 2003. The free-agent list published 2003-07-01 is used only "
                 "to identify expiring contracts; no qualifying-offer or cap-hold decision is implied.")


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def sanitize_contracts(data, report):
    data["not_applied"] = ["Every transaction, option decision, qualifying offer, waiver and signing dated after "
                           f"{CHECKPOINT} is excluded; those are simulated events."]
    legend = data["status_legend"]
    for key in ("free_agent_restricted", "free_agent_unrestricted"):
        legend.pop(key, None)
    legend["free_agent_expiring"] = ("Contract expires June 30, 2003 (identified from the list published "
                                     "2003-07-01). Field rfa_eligible is true when that list marked the player "
                                     "restricted, which shows eligibility for restricted free agency; whether "
                                     "Miami or any club tenders a qualifying offer is a simulated June 30 decision. "
                                     "null means eligibility is not established.")
    legend["retired_salary_on_books"] = "Retired player whose salary is still carried on the club's 2003-04 list."
    for club, entry in data["clubs"].items():
        for p in entry["players"]:
            if p.get("basis") == "signed_elsewhere_after_june_2003":
                report.append(f"{club}: {p['player']}: removed post-checkpoint signing note; basis recast to unresolved_at_checkpoint")
                p["basis"], p["notes"] = "unresolved_at_checkpoint", UNRESOLVED_NOTE
            if p["status"] in ("free_agent_restricted", "free_agent_unrestricted"):
                p["rfa_eligible"] = True if p["status"] == "free_agent_restricted" else None
                p["status"] = "free_agent_expiring"
                if "free agent list published 2003-07-01" in (p.get("notes") or ""):
                    p["notes"] = EXPIRING_NOTE
        for p in entry.get("released_players", []):
            note = p.get("notes") or ""
            dates = re.findall(r"released (\d+)/(\d+)/(\d+)", note)
            late = [d for d in dates if 2000 + int(d[2]) > 2003 or (int(d[2]) == 3 and int(d[0]) > 6)]
            if late:
                report.append(f"{club}: {p['player']}: release dated after the checkpoint removed; status recast to retired_salary_on_books")
                p["status"] = "retired_salary_on_books"
                p["amount_kind"] = {k: "contract_salary" for k in p["schedule"]}
                p["notes"] = "Retired; salary still carried on the club's 2003-04 list. How it is resolved is a later event."
    by_status, by_basis = {}, {}
    for entry in data["clubs"].values():
        for p in entry["players"]:
            by_status[p["status"]] = by_status.get(p["status"], 0) + 1
            by_basis[p.get("basis")] = by_basis.get(p.get("basis"), 0) + 1
        counts = {}
        for p in entry["players"]:
            counts[p["status"]] = counts.get(p["status"], 0) + 1
        entry["counts"] = counts
    data["coverage"]["by_status"], data["coverage"]["by_basis"] = by_status, by_basis
    data["sanitized_for_checkpoint"] = CHECKPOINT
    return data


def sanitize_free_agents(data):
    for p in data["players"]:
        p["rfa_eligible"] = True if p.pop("status") == "restricted" else None
    data["kind"] = "expiring_contracts"
    data["usage"] = ("Identifies contracts expiring June 30, 2003. rfa_eligible true means the published list marked "
                     "the player restricted, read only as eligibility; qualifying offers and signings are simulated. "
                     "null means eligibility is not established.")
    data["source"] = data["source"].replace("the list marks restricted free agents only, so all others are recorded as unrestricted",
                                            "the list marks restricted free agents only")
    return data


def main():
    report = []
    contracts = sanitize_contracts(json.loads((RAW / "2003/league/nba_2003_contracts.json").read_text()), report)
    dump(OUT / "2003/league/nba_2003_contracts.json", contracts)
    dump(OUT / "2003/league/nba_2003_expiring_contracts.json", sanitize_free_agents(json.loads(RAW_FA.read_text())))
    rules = sorted(RAW.glob("*/league/nba_*_cap_rules.json"))
    for path in rules:
        dump(OUT / path.relative_to(RAW), json.loads(path.read_text()))
    report.append("Residual risk: 37 under_contract_unverified amounts are read from the 2003-04 salary list without "
                  "confirmed continuity; a few may reflect deals signed after the checkpoint. The ledger flags them.")
    report.append("Residual risk: the 2003-07-01 list may include players whose option was declined on June 30; "
                  "their pre-decision option status could not be reconstructed and is treated as expiring.")
    dump(OUT / "2003/league/nba_2003_contracts_import_report.json",
         {"checkpoint": CHECKPOINT, "changes": report,
          "files": ["2003/league/nba_2003_contracts.json", "2003/league/nba_2003_expiring_contracts.json"]
                   + [str(p.relative_to(RAW)) for p in rules]})
    print("\n".join(report))
    print(f"{len(rules)} cap-rule seasons imported")


if __name__ == "__main__":
    sys.exit(main())
