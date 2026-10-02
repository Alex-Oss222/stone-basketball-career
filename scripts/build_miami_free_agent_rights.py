#!/usr/bin/env python3
"""Compute Miami's expiring players' Bird status, cap holds and qualifying offers (June 26, 2003).

Inputs: the 1999 rules (library/2003/league/nba_1999_cba_rules.json), the tenure
facts (library/2003/league/miami_expiring_tenure.csv), the league contract
inventory and the 2003-04 cap rules. Output:
career/Dwyane_Wade/2003-04/00_Team/Finances/free_agent_rights.json. --check compares only.
"""
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from runtime.cba import bird_seasons, bird_status, cap_hold, first_season_with_team, qualifying_offer, rfa_eligible, rules

OUT = Path("career/Dwyane_Wade/2003-04/00_Team/Finances/free_agent_rights.json")


def build(root=ROOT):
    cba = rules(root)
    inventory = json.loads((root / "library/2003/league/nba_2003_contracts.json").read_text())
    cap = json.loads((root / "library/2003/league/nba_2003_04_cap_rules.json").read_text())
    average = cba["average_salary"]["2003-04_threshold"]
    minimums = json.loads((root / "library/2003/league/nba_1999_cba_minimum_salary_scale.json").read_text())["seasons"]["2003-04"]
    miami = {p["bbr_id"]: p for p in inventory["clubs"]["Miami Heat"]["players"] if p["status"] == "free_agent_expiring"}
    tenure = list(csv.DictReader((root / "library/2003/league/miami_expiring_tenure.csv").open(encoding="utf-8")))
    players = []
    for row in (r for r in tenure if r["how_joined_miami"]):
        contract = miami[row["bbr_id"]]
        prior = contract["prior_season_salary"]["amount"]
        seasons_played = [r for r in tenure if r["bbr_id"] == row["bbr_id"] and r["season"]]
        nba_seasons = int(row["nba_seasons_before_2003_04"])
        with_team = bird_seasons(row["join_date"])
        status = bird_status(with_team)
        max_key = "10_plus_years" if nba_seasons >= 10 else "7_to_9_years" if nba_seasons >= 7 else "0_to_6_years"
        # Maximum salary: the greater of the service-tier maximum and 105% of previous salary (FAQ Q22).
        max_salary = max(cap["maximum_salary"][max_key], round(prior * 1.05))
        hold, percent, notes = cap_hold(prior, status, rookie_scale=False, above_average=prior >= average,
                                        max_salary=max_salary, cba=cba)
        minimum = minimums["10_plus" if nba_seasons >= 10 else str(nba_seasons)]
        if prior <= minimum + 150000:
            notes.append("previous salary is minimum-level; a separate minimum-contract hold rule is unverified (rules file, unverified[0])")
        entered = min(r["season"] for r in seasons_played)
        eligible = rfa_eligible(entered, nba_seasons, cba)
        qo, qo_basis = (None, "not eligible for restricted free agency")
        if eligible:
            qo, qo_basis = qualifying_offer(prior, minimum, cba)
        players.append({
            "player": row["player"], "bbr_id": row["bbr_id"], "previous_salary": prior,
            "joined_miami": {"how": row["how_joined_miami"], "date": row["join_date"],
                             "first_season": f"{first_season_with_team(row['join_date'])}-{str(first_season_with_team(row['join_date']) + 1)[-2:]}"},
            "seasons_with_miami_for_bird": with_team, "nba_seasons_before_2003_04": nba_seasons,
            "bird_status": status, "cap_hold": hold, "cap_hold_percent": percent,
            "above_league_average_salary": prior >= average,
            "restricted_free_agency_eligible": eligible, "qualifying_offer": qo, "qualifying_offer_basis": qo_basis,
            "notes": notes,
        })
    return {
        "schema_version": 1, "owner": "ai_gm", "as_of": "2003-06-26", "team": "Miami Heat",
        "purpose": "Rights and cap holds for Miami's expiring contracts. Facts and rule computations only; no decision is recorded here.",
        "rules": str(Path("library/2003/league/nba_1999_cba_rules.json")),
        "tenure_source": "library/2003/league/miami_expiring_tenure.csv",
        "average_salary_threshold": average,
        "average_salary_note": "2003-04 mid-level exception, which equals the average salary under the 1999 agreement (rules file, average_salary).",
        "special_cases": {
            "Mike James": "Waived 2001-10-25 and re-signed 2001-12-18; a waiver restarts the Bird clock, so 2001-02 counts from the re-signing.",
            "Alonzo Mourning": "Under contract through 2002-03 although he missed the season; his Bird clock continues.",
        },
        "players": players,
        "total_cap_holds": sum(p["cap_hold"] for p in players),
    }


def main():
    data = json.dumps(build(), indent=1) + "\n"
    path = ROOT / OUT
    if "--check" in sys.argv:
        ok = path.exists() and path.read_text() == data
        print("free_agent_rights.json is current" if ok else "free_agent_rights.json is stale")
        raise SystemExit(0 if ok else 1)
    path.write_text(data)
    for p in json.loads(data)["players"]:
        print(f"{p['player']:18} {p['bird_status']:10} hold {p['cap_hold']:>10,} ({p['cap_hold_percent']}%)  QO {p['qualifying_offer'] or '-':>9}  {p['qualifying_offer_basis']}")
    print("total holds", f"{json.loads(data)['total_cap_holds']:,}")


if __name__ == "__main__":
    main()
