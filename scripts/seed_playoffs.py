#!/usr/bin/env python3
"""Seed the 2004 playoffs once the regular season is complete (runtime/playoffs.py).

    python scripts/seed_playoffs.py --write     seeds, bracket and first-round calendar; writes playoffs.json and Playoffs.md
    python scripts/seed_playoffs.py --check     show the seeds without writing

A tie the 2003-04 procedure cannot break writes an engine decision packet (Playoff_Draws/); draw it with
`python scripts/draw_decisions.py`, then run this again. No playoff game is built or played here.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime import playoffs                                            # noqa: E402
from runtime.write_back import clock                                    # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    last = playoffs.rules(ROOT)["calendar"]["regular_season_last_day"]
    if args.write and clock(ROOT) < last:
        print(f"the regular season runs to {last}; the career clock is {clock(ROOT)}")
        return 1
    if args.write:
        from runtime.season_games import season_games
        from runtime.write_back import closed_results
        closed, scheduled = len(closed_results(ROOT, now=last)), len(season_games())
        if closed < scheduled:
            print(f"{scheduled - closed} regular-season game(s) are not closed yet; the playoffs are seeded after all {scheduled}")
            return 1
    record, pending = playoffs.build(ROOT, write=args.write)
    if pending:
        print("tiebreak drawing needed: " + ", ".join(pending) + " (python scripts/draw_decisions.py, then run again)")
        return 1
    for conf in ("East", "West"):
        print(conf)
        for row in record["seeds"][conf]:
            print(f"  {row['seed']}. {row['club']} {row['wins']}-{row['losses']}{'  division winner' if row['division_winner'] else ''}")
    if args.write:
        print(f"written: {playoffs.record_path(record['season'])} and {playoffs.page_path(record['season'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
