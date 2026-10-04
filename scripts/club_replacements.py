#!/usr/bin/env python3
"""Disturbed clubs sign their replacements (`runtime/club_replacements.py`).

    python scripts/club_replacements.py --write     make every replacement due
    python scripts/club_replacements.py --check     list disturbed clubs without one; write nothing
"""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime import club_replacements                                   # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        errors = club_replacements.replacement_errors(ROOT)
        print("\n".join(errors) or "No disturbed club is waiting for a replacement.")
        return 1 if errors else 0
    new = club_replacements.replace(ROOT)
    for e in new:
        print(f"{e['from']}  {e['club']} signs {e['player']} ({e['terms']['route']}, ${e['terms']['salary_2003_04']:,}) to replace {e['replaces']}")
    print(f"{len(new)} replacement(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
