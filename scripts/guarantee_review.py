#!/usr/bin/env python3
"""Miami's January 10, 2004 guarantee review (`runtime/roster_moves.py`).

    python scripts/guarantee_review.py --write 2004-01-07    keep-or-waive decisions (last day a waiver clears)
    python scripts/guarantee_review.py --write 2004-01-10    kept contracts become guaranteed
    python scripts/guarantee_review.py --check               report what is due; write nothing

Each run does what is due on or before the date and refuses a date after the career clock. The
front office keeps every non-guaranteed player unless guaranteeing him would take the payroll over
the owner's ceiling; then the lowest-valued are waived first (`roster_moves.guarantee_plan`). A
waiver closes the contract with the salary for the days he was on the roster; the player goes back
to his real career path. Miami's game builder stops at the review until it is recorded.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime import roster_moves, signing                             # noqa: E402
from runtime.camp import GUARANTEE_DATE                               # noqa: E402
from runtime.contract_archive import archive_contract                 # noqa: E402
from runtime.gm import FrontOffice                                    # noqa: E402
from runtime.market import Market                                     # noqa: E402
from scripts.refresh_career_views import refresh_career_views         # noqa: E402

STATE = Path("career/Dwyane_Wade/2003-04/current_state.json")


def review(root, day):
    root = Path(root)
    clock = json.loads((root / STATE).read_text(encoding="utf-8"))["current_date"]
    if day > clock:
        raise SystemExit(f"{day} is after the career clock ({clock}); the review is written on its date, not before")
    note = f"career/Dwyane_Wade/2003-04/{json.loads((root / STATE).read_text(encoding='utf-8'))['current_note']}"
    record = roster_moves.read(roster_moves.GUARANTEES, root) or {
        "schema_version": 1, "owner": "ai_gm", "kind": "guarantee_review", "season": "2003-04",
        "guarantee_date": GUARANTEE_DATE, "waive_by": roster_moves.WAIVE_BY, "rule": roster_moves.__doc__.split("The guarantee review")[1].strip()}
    (root / roster_moves.GUARANTEES).parent.mkdir(parents=True, exist_ok=True)
    done = []
    if day >= roster_moves.WAIVE_BY and not record.get("decided_on"):
        writer = signing.Writer(root)
        fo = FrontOffice(roster_moves.WAIVE_BY, Market(roster_moves.WAIVE_BY, root), root)
        plan = roster_moves.guarantee_plan(writer.load(signing.TEAM / "Finances/contract_schedules.json"), fo)
        for row in plan:
            if row["decision"] == "waive":
                row["charge"] = roster_moves.waive(writer, row["player"], roster_moves.WAIVE_BY, row["basis"], note)
        record.update(decided_on=roster_moves.WAIVE_BY, decisions=plan)
        signing.dump(root / roster_moves.GUARANTEES, record)
        writer.commit()
        signing.refresh_finance(writer, FrontOffice(roster_moves.WAIVE_BY, Market(roster_moves.WAIVE_BY, root), root), roster_moves.WAIVE_BY)
        writer.commit()
        done.append(f"decisions dated {roster_moves.WAIVE_BY}: " + ", ".join(f"{r['player']} {r['decision']}" for r in plan))
    if day >= GUARANTEE_DATE and record.get("decided_on") and not record.get("guaranteed_on"):
        writer = signing.Writer(root)
        sheet = writer.load(signing.TEAM / "Finances/contract_schedules.json")
        roster = writer.load(signing.TEAM / "Team/Roster/roster.json")
        archive = writer.load("career/Dwyane_Wade/Contracts/contract_records.json")
        made = []
        for entry in roster_moves.non_guaranteed(sheet):
            salary = entry["schedule"][signing.SEASON]
            entry["guaranteed"] = {**entry.get("guaranteed", {}), signing.SEASON: salary}
            entry["notes"] = entry.get("notes", "") + f" Guaranteed {GUARANTEE_DATE}: on the roster on the guarantee date."
            reg = next(p for p in roster["players"] if p["name"] == entry["player"])
            reg["control"] = reg["control"].rstrip(".") + f"; guaranteed {GUARANTEE_DATE} (guarantee_review.json)."
            base = next((r for r in archive["records"] if r["player"] == entry["player"] and r["event"] == "signed"), None)
            if base:
                archive_contract(writer, {**entry, "contract_id": base["contract_id"]}, GUARANTEE_DATE, event="amended",
                                 source=str(roster_moves.GUARANTEES), player_id=base["player_id"])
            made.append({"player": entry["player"], "guaranteed": salary})
        roster["as_of"] = GUARANTEE_DATE
        signing.note_event(writer, note, GUARANTEE_DATE, "Guarantee date: " + (", ".join(m["player"] for m in made) or "no contract") +
                           " guaranteed for 2003-04.")
        record.update(guaranteed_on=GUARANTEE_DATE, guaranteed=made)
        signing.dump(root / roster_moves.GUARANTEES, record)
        writer.commit()
        signing.refresh_finance(writer, FrontOffice(GUARANTEE_DATE, Market(GUARANTEE_DATE, root), root), GUARANTEE_DATE)
        writer.commit()
        done.append(f"guaranteed {GUARANTEE_DATE}: " + ", ".join(m["player"] for m in made))
    return done


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", metavar="DATE")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        errors = roster_moves.guarantee_errors(ROOT)
        print("\n".join(errors) or "guarantee review: nothing due")
        return 1 if errors else 0
    done = review(ROOT, args.write)
    print("\n".join(done) or "nothing due on " + args.write)
    if done:
        print(f"Updated {len(refresh_career_views(ROOT))} detailed career views.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
