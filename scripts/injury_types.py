#!/usr/bin/env python3
"""Name every Miami injury and absence the engine draws (runtime/injury_types.py).

    python scripts/injury_types.py --write     write a type draw packet for each new injury, record drawn types

Draw the packets with `python scripts/draw_decisions.py`, then run again to record them. Idempotent.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from runtime import injury_types  # noqa: E402


def main(argv):
    if argv[1:] != ["--write"]:
        raise SystemExit(__doc__)
    written, recorded = injury_types.run(ROOT)
    for e in recorded:
        print(f"{e['date']}  {e['player']}: {e['injury']} ({e['body_area']}), {e['games_out']} game(s) out ({e['engine_kind']})")
    print(f"injury types: {len(written)} draw packet(s) written, {len(recorded)} recorded")


if __name__ == "__main__":
    main(sys.argv)
