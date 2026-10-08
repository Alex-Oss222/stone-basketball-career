#!/usr/bin/env python3
"""Run the dated offseason events due on a day: the draft lottery (runtime/lottery.py), the 2004 expansion draft
(runtime/expansion.py), the draft (runtime/draft.py) and the summer market from June 30 (runtime/free_agency_2004.py)
for every club. The year is the date's: each module runs in its year context (R5); expansion happened only in 2004.
Miami's draft-rights records follow (runtime/draft_rights.py): from the draft, the rights of an earlier pick still
unsigned end on the live register (`end_rights`); once the market record is closed, the year's routine Required
Tenders are entered on their deadlines (`record_tenders`).

    python scripts/offseason_day.py --write DATE

Each event writes engine decision packets one at a time (a lottery draw, a pick, a trade answer) and is completed by
running this again after `python scripts/draw_decisions.py`; `scripts/advance.py` loops until nothing is pending.
Idempotent: a recorded event is never decided again. Nothing here plays a game or signs a contract.
"""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime import draft, draft_rights, expansion, free_agency_2004, lottery                        # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--write", metavar="DATE", required=True)
    args = parser.parse_args()
    year = int(args.write[:4])
    calendar = ROOT / f"library/{year}/league/nba_{year}_offseason_calendar.json"
    if not calendar.is_file():
        if args.write < f"{year}-05-15":                # no offseason event before mid-May
            print("offseason events checked for", args.write)
            return 0
        # stop the clock rather than let it pass an unbuilt offseason
        print(f"no {year} offseason library data ({calendar.relative_to(ROOT)}): the {year} lottery, draft and market "
              "cannot run (docs/ROADMAP.md, R5)", file=sys.stderr)
        return 2
    order = lottery.run(ROOT, args.write, year=year)
    if order:
        print(f"{year} draft lottery: " + ", ".join(f"No. {i + 1} {c}" for i, c in enumerate(order["lottery_winners"])))
    if year == 2004:
        taken = expansion.run(ROOT, args.write)
        if taken:
            print(f"2004 expansion draft: Charlotte selects {len(taken['selections'])} players")
    with draft.year_context(year, ROOT):
        made = draft.run(ROOT, args.write)
    if made:
        for p in made["picks"]:
            if p["club"] == draft.MIAMI:
                print(f"Miami selects {p['player']} ({p['position']}) at No. {p['pick']}")
        print(f"{year} draft complete: {len(made['picks'])} picks, {len(made['trades'])} draft-night trade(s)")
    for e in draft_rights.end_rights(ROOT, args.write):
        print(f"{e['player']}: Miami's rights to the No. {e['pick']} pick of the {e['draft_year']} draft ended {e['date']}")
    market = free_agency_2004.run(ROOT, args.write, year=year)
    if market:
        miami = market["clubs"].get(draft.MIAMI, [])
        print(f"{year} free agency complete: {sum(len(v) for v in market['clubs'].values())} contracts; Miami {len(miami)} players, "
              f"payroll ${market['payroll'].get(draft.MIAMI, 0):,}")
    for t in draft_rights.record_tenders(ROOT, year, args.write):
        print(f"Required Tender to {t['player']} (No. {t['pick']}, round {t['round']}) entered on {t['date']}")
    print("offseason events checked for", args.write)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
