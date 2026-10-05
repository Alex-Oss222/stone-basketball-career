#!/usr/bin/env python3
"""Run the dated offseason events due on a day (2004): Miami's draft on June 24 (runtime/draft.py).

    python scripts/offseason_day.py --write DATE

Idempotent: an event already recorded is not decided again. Nothing here plays a game or signs a contract.
"""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime import draft                                               # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--write", metavar="DATE", required=True)
    args = parser.parse_args()
    made = draft.record(ROOT, args.write)
    if made:
        for c in made["choices"]:
            extra = f"; {c['displaced']['club']} receives {c['displaced']['receives']}" if c.get("displaced") else ""
            print(f"Miami picks {c['player']} ({c['position']}) at No. {c['slot']}{extra}")
    print("offseason events closed for", args.write)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
