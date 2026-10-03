#!/usr/bin/env python3
"""Review Miami's rotation every fourteen days after the camp decision.

  python scripts/review_rotation.py --write 2003-11-07
  python scripts/review_rotation.py --check 2003-11-07

Reviews consume only closed regular-season games strictly before their date.
Close battles write ordinary *.decision.json packets; commit and send those
unchanged packets through scripts/draw_decisions.py, collect the engine's
answers, then repeat this command. Existing game requests retain their lineup.
No game, decision draw, or career-clock change is performed by this command.
"""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from runtime import rotation_reviews as reviews  # noqa: E402
from runtime.standing import current_date        # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", metavar="DATE")
    group.add_argument("--check", metavar="DATE")
    parser.add_argument("--season", default=reviews.SEASON)
    args = parser.parse_args()
    on = args.write or args.check
    try:
        reviews.check_date(on)
        if args.check:
            errors = reviews.review_errors(ROOT, args.season)
            errors += [f"staff review due {day}" for day in reviews.pending_reviews(on, ROOT, args.season)]
            for error in errors:
                print(error)
            if not errors:
                print("Staff rotation reviews complete through " + on)
            return int(bool(errors))
        if on > current_date(ROOT):
            raise ValueError(f"review date {on} is after the career clock ({current_date(ROOT)})")
        written, pending = reviews.run_reviews(on, ROOT, args.season)
        for day in written:
            print("Dated staff rotation written: " + day)
        if pending:
            print("Awaiting engine starting-battle draws: " + ", ".join(pending))
            return 1
        if not written:
            print("No staff rotation reviews due through " + on)
        return 0
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
