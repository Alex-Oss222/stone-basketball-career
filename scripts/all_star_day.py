#!/usr/bin/env python3
"""All-Star weekend games (`runtime/all_star_games.py`): the day's locks and requests, and after the games the results,
the MVPs and the pages.

    python scripts/all_star_day.py --write 2007-02-16            lock and request the games dated on the day
    python scripts/all_star_day.py --write 2006-04-19 --retroactive
                                                                 the 2004-2006 weekends, locked on that career date
                                                                 from evidence dated before each game (only then)
    python scripts/all_star_day.py --after 2007-02-16            after the games: Wade's notes, MVPs, awards, pages
    python scripts/all_star_day.py --check                       validation only (exit 1 on any error)

Play the requests with `python scripts/play_games.py DATE`. A Rookie Challenge MVP tie writes an engine draw packet:
draw it with `python scripts/draw_decisions.py`, then run --after again for the same day.
"""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime import all_star_games                                          # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", metavar="DATE")
    group.add_argument("--after", metavar="DATE")
    group.add_argument("--check", action="store_true")
    parser.add_argument("--retroactive", action="store_true")
    args = parser.parse_args()
    if args.check:
        errors = all_star_games.errors(ROOT)
        for e in errors:
            print(e)
        print(f"all-star games: {len(errors)} error(s)")
        return 1 if errors else 0
    if args.write:
        try:
            lines = all_star_games.lock(ROOT, args.write, retroactive=args.retroactive)
        except ValueError as exc:
            print(f"all-star games: refused: {exc}")
            return 1
        for line in lines:
            print(line)
        print(f"all-star games: {len(lines)} locked and requested")
        return 0
    lines, pending = all_star_games.after(ROOT, args.after)
    for line in lines:
        print(line)
    if pending:
        print(f"all-star games: {len(pending)} draw(s) pending")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
