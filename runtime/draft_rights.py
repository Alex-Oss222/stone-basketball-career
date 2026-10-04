"""Draft rights under the 1999 CBA (Article X, Section 3): Required Tenders and how long rights last.

A team keeps the exclusive right to sign its pick until the next draft only if it makes a Required
Tender: a First Round Pick's by July 15 after the draft (a rookie-scale offer of three seasons plus an
option year at 80% or more of scale), a Second Round Pick's in the two weeks before September 5 (one
season at the minimum, Article I (vv)). Without one, a first-round pick becomes a rookie free agent on
July 16 and a second-round pick on September 6. A tendered pick who has not signed by the next draft
leaves the team's exclusive rights and may be drafted again (Section 3(a)). A pick under contract
abroad is governed by Section 4 and is not modelled.

`required_tenders.json` (00_Team/Transactions) holds Miami's tenders with their dates. Validation
refuses an unsigned pick on the register without a tender in its window, and one still held after
the next draft.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEASON = "2003-04"
TEAM = Path(f"career/Dwyane_Wade/{SEASON}/00_Team")
TENDERS = TEAM / "Transactions/required_tenders.json"
# 2003 draft (June 26, 2003) deadlines and the next draft's date.
FIRST_ROUND_BY = "2003-07-15"
SECOND_ROUND_WINDOW = ("2003-08-22", "2003-09-05")
NEXT_DRAFT = "2004-06-24"


def read(rel, root=ROOT):
    path = Path(root) / rel
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def window(round_):
    return (None, FIRST_ROUND_BY) if round_ == 1 else SECOND_ROUND_WINDOW


def draft_rights_errors(root=ROOT):
    state = read(f"career/Dwyane_Wade/{SEASON}/current_state.json", root) or {}
    today = state.get("current_date", "")
    if today <= "2003-06-26":
        return []
    roster = read(TEAM / "Team/Roster/roster.json", root)
    tenders = {t["player"]: t for t in (read(TENDERS, root) or {}).get("tenders", [])}
    errors = []
    for p in roster["players"]:
        if "draft_rights" not in (p.get("status") or ""):
            continue
        tender = tenders.get(p["name"])
        start, end = window(tender["round"]) if tender else (None, None)
        if tender is None:
            errors.append(f"{p['name']}: unsigned draft rights without a Required Tender (1999 CBA Art. X §3; required_tenders.json)")
        elif tender["date"] > end or (start and tender["date"] < start):
            errors.append(f"{p['name']}: Required Tender dated {tender['date']} is outside its window ({start or 'draft'} to {end})")
        if today >= NEXT_DRAFT:
            errors.append(f"{p['name']}: exclusive rights ended at the {NEXT_DRAFT} draft; he cannot stay on the register unsigned")
    return errors
