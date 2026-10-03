#!/usr/bin/env python3
"""Wade's standing with Miami's front office (runtime/standing.py).

  python scripts/update_standing.py --check 2003-07-20                      print the rule's computation on a date
  python scripts/update_standing.py --write 2003-07-20 [--trigger T] [--source REL]
                                                                            append a dated snapshot to career/Dwyane_Wade/standing.json

A write only dates a snapshot: its value is always the rule's computation from closed simulated
results and recorded honors, so a manual write cannot choose a standing. The trigger defaults to
`manual`; the drivers write `signing` and `season_close` snapshots themselves. A write refuses a
date after the career clock or before the last snapshot. Validation replays every snapshot and
refuses a stale file, which is what makes the triggers binding.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from runtime import standing   # noqa: E402


def main(argv, root=ROOT):
    if len(argv) < 3 or argv[1] not in ("--check", "--write"):
        raise SystemExit(__doc__)
    day = argv[2]
    if argv[1] == "--check":
        print(json.dumps(standing.compute(root, day), indent=1))
        return
    trigger, source = "manual", None
    rest = argv[3:]
    while rest:
        flag = rest.pop(0)
        if flag == "--trigger" and rest:
            trigger = rest.pop(0)
        elif flag == "--source" and rest:
            source = rest.pop(0)
        else:
            raise SystemExit(__doc__)
    snap = standing.record(root, day, trigger, source)
    print(json.dumps(snap, indent=1) if snap else f"standing.json already carries the {day} snapshot; nothing written")


if __name__ == "__main__":
    main(sys.argv)
