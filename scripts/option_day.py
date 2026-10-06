#!/usr/bin/env python3
"""Contract options for every club on their deadlines (`runtime/options.py`).

    python scripts/option_day.py --write 2004-11-24     decide options due by the date, write close calls as engine
                                                        packets, apply drawn answers to the contracts

Idempotent: a decision is recorded once in `League/option_decisions.json`; draw packets with
`python scripts/draw_decisions.py`, then run again to apply them. Evidence is dated on each option's deadline.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from runtime import options  # noqa: E402


def main(argv):
    if len(argv) != 3 or argv[1] != "--write":
        raise SystemExit(__doc__)
    decided, written, applied = options.run(argv[2], ROOT)
    for d in decided:
        print(f"{d['deadline']}  {d['club']}: {d['player']} {d['option_season']} {d['kind'].replace('_', ' ')} "
              f"-> {d['decision'] or 'engine draw'} ({d['how']})")
    print(f"options: {len(decided)} decided, {len(written)} draw packet(s) written, {len(applied)} applied")


if __name__ == "__main__":
    main(sys.argv)
