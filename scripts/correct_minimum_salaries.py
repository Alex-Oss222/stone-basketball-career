#!/usr/bin/env python3
"""Correct Miami's minimum contracts to the 1999 CBA scale, and record the camp voids and releases.

    python scripts/correct_minimum_salaries.py --write 2003-11-11

1. Minimum salaries. Before this correction the front office priced every veteran with three to nine
   years of service at the two-year minimum, and an unattached veteran without recorded service at
   the rookie minimum. The legal minimum depends on each year of service
   (`library/2003/league/nba_1999_cba_minimum_salary_scale.json`, FAQ Q9). Each affected contract is
   amended to the scale amount for the player's recorded service. The signing, its date and its
   non-guaranteed terms stand, and so does every drawn answer: the corrected salary is never lower
   than the one the player accepted. A one-year minimum for a player with five or more years counts
   only the four-year minimum in team salary, because the league reimburses the rest (`cap_amount`).
2. Contract history. Each camp contract voided or released on October 27, 2003 gets a dated `voided`
   or `released` event in `Contracts/contract_records.json`, so no contract page still shows it as
   Miami's current contract.

The finance summary and cap sheet are then rebuilt from the ledger (`signing.refresh_finance`).
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime import signing                                           # noqa: E402
from runtime.cba import minimum_cap_amount, minimum_salary            # noqa: E402
from runtime.contract_archive import ARCHIVE, archive_contract        # noqa: E402
from runtime.gm import FrontOffice                                    # noqa: E402
from runtime.market import Market                                     # noqa: E402
from scripts.refresh_career_views import refresh_career_views         # noqa: E402

RECORD = signing.TEAM / "Finances/minimum_salary_corrections.json"
CAMP_RECORD = "career/Dwyane_Wade/2003-04/04_Training_Camp/signing_corrections.json"
SEASON = signing.SEASON
# Years of NBA service before 2003-04: the free-agent rights file, or the unattached identities file.
SERVICE_SOURCES = {
    "Stephen Jackson": (3, "library/2003/league/nba_2003_free_agent_rights.json"),
    "Scott Padgett": (4, "library/2003/league/nba_2003_free_agent_rights.json"),
    "Cherokee Parks": (8, "library/2003/league/nba_2003_free_agent_rights.json"),
    "Shawn Kemp": (14, "library/2003/league/nba_2003_free_agent_rights.json"),
    "John Wallace": (6, "library/2003/league/nba_2003_unattached_identities.json"),
    "Udonis Haslem": (0, "library/2003/league/nba_2003_unattached_identities.json"),
}
ENDED = {"Keon Clark": "voided", "Jumaine Jones": "voided", "Reggie Evans": "voided", "Chris Andersen": "voided",
         "Mike Batiste": "voided", "Dion Glover": "released", "Tyrone Hill": "released"}
ENDED_ON = "2003-10-27"


def signed_record(archive, name):
    return next(r for r in archive["records"] if r["player"] == name and r["event"] == "signed")


def correct(root, day):
    writer = signing.Writer(root)
    if (Path(root) / RECORD).exists():
        return None
    sheet = writer.load(signing.TEAM / "Finances/contract_schedules.json")
    roster = writer.load(signing.TEAM / "Team/Roster/roster.json")
    archive = writer.load(ARCHIVE)
    by_name = {p["player"]: p for p in sheet["players"]}
    rows = []
    for name, (service, source) in SERVICE_SOURCES.items():
        entry = by_name[name]
        before = entry["schedule"][SEASON]
        salary = minimum_salary(service)
        counted = minimum_cap_amount(service, salary, 1)
        entry["schedule"][SEASON] = salary
        entry["years_of_service"] = service
        if counted != salary:
            entry["cap_amount"] = {SEASON: counted}
        old = f"${before:,}"
        entry["notes"] = (entry["notes"].replace(old, f"${salary:,}") +
                          (f" Amended {day}: the 1999 CBA minimum for {service} years of service is ${salary:,} "
                           f"(was ${before:,}); minimum_salary_corrections.json." if salary != before else "")
                          + (f" Counts ${counted:,} in team salary (one-year minimum, 5+ years: the league reimburses the rest)."
                             if counted != salary else ""))
        reg = next(p for p in roster["players"] if p["name"] == name)
        reg["control"] = reg["control"].replace(old, f"${salary:,}")
        if salary != before and "minimum_salary_corrections.json" not in reg["control"]:
            reg["control"] = reg["control"].rstrip(".") + f"; amended {day} to the CBA minimum for {service} years of service (minimum_salary_corrections.json)."
        changed = salary != before or counted != salary
        if changed:
            base = signed_record(archive, name)
            amended = {**entry, "contract_id": base["contract_id"]}
            archive_contract(writer, amended, day, event="amended", source=str(RECORD), player_id=base["player_id"])
        rows.append({"player": name, "years_of_service": service, "service_source": source,
                     "signed": entry["signed_date"], "salary_before": before, "salary_after": salary,
                     "counted_in_team_salary": counted, "amended": changed})
    ended = []
    for name, event in ENDED.items():
        base = signed_record(archive, name)
        contract = {**base["contract"], "contract_id": base["contract_id"], "status": event, "ended_on": ENDED_ON,
                    "notes": base["contract"].get("notes", "") + f" {event.capitalize()} {ENDED_ON} ({CAMP_RECORD}); no dead money."}
        archive_contract(writer, contract, ENDED_ON, event=event, source=CAMP_RECORD, player_id=base["player_id"])
        ended.append({"player": name, "event": event, "date": ENDED_ON, "contract_id": base["contract_id"]})
    record = {
        "schema_version": 1, "owner": "ai_gm", "date": day, "kind": "minimum_salary_correction",
        "rule": ("1999 CBA minimum salary by years of NBA service before the season (FAQ Q9; "
                 "library/2003/league/nba_1999_cba_minimum_salary_scale.json). A one-year minimum for a player with five "
                 "or more years counts the four-year minimum in team salary; the league reimburses the rest."),
        "cause": ("The front office priced every veteran with 3 to 9 years of service at the two-year minimum, and an "
                  "unattached veteran without recorded service at the rookie minimum (runtime/valuation.py before this date)."),
        "answers": ("Each signing, its date and its terms stand. No drawn answer is re-drawn: every corrected salary is at "
                    "least the amount the player accepted."),
        "contracts": rows, "contract_history_events": ended}
    signing.dump(Path(root) / RECORD, record)
    writer.commit()
    signing.refresh_finance(writer, FrontOffice(day, Market(day, root), root), day)
    writer.commit()
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--write", action="store_true")
    parser.add_argument("day")
    args = parser.parse_args()
    if not args.write:
        parser.error("pass --write to apply the correction")
    record = correct(ROOT, args.day)
    print("Already corrected." if record is None else json.dumps(record["contracts"], indent=1))
    print(f"Updated {len(refresh_career_views(ROOT))} detailed career views.")


if __name__ == "__main__":
    main()
