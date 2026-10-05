#!/usr/bin/env python3
"""Run the dated offseason events due on a day (2004): the draft lottery on May 26 (runtime/lottery.py) and the draft
on June 24 (runtime/draft.py), for every club.

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

from runtime import draft, lottery                                      # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--write", metavar="DATE", required=True)
    args = parser.parse_args()
    order = lottery.run(ROOT, args.write)
    if order:
        print("2004 draft lottery: " + ", ".join(f"No. {i + 1} {c}" for i, c in enumerate(order["lottery_winners"])))
    made = draft.run(ROOT, args.write)
    if made:
        for p in made["picks"]:
            if p["club"] == draft.MIAMI:
                print(f"Miami selects {p['player']} ({p['position']}) at No. {p['pick']}")
        print(f"2004 draft complete: {len(made['picks'])} picks, {len(made['trades'])} draft-night trade(s)")
    print("offseason events checked for", args.write)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
