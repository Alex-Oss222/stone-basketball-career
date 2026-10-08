#!/usr/bin/env python3
"""National-team tournaments (`runtime/national.py`): the day's selection, roster lock, ties and game requests.

    python scripts/national_day.py --write 2006-08-19     before the day's games
    python scripts/national_day.py --after 2006-08-19     after them: Wade's notes, bracket, awards and medals at the close
    python scripts/national_day.py --medals               rebuild every closed tournament's medal register (unchanged
                                                          unless its sources changed; a closed record without frozen
                                                          medal identities gets them, resolved on its close day;
                                                          runtime/national_medals.py)

Draw any packet it writes with `python scripts/draw_decisions.py`, then run it again for the same day.
"""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime import national                                          # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", metavar="DATE")
    group.add_argument("--after", metavar="DATE")
    group.add_argument("--medals", action="store_true")
    args = parser.parse_args()
    if args.medals:
        from runtime.national_medals import write_all
        for path in write_all(ROOT):
            print(f"medal register: {path.relative_to(ROOT)}")
    elif args.write:
        lines, pending = national.day(args.write, ROOT)
        for line in lines:
            print(line)
        if pending:
            print(f"national: {len(pending)} draw(s) pending")
    else:
        for line in national.after_games(args.after, ROOT):
            print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
