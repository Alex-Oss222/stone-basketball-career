#!/usr/bin/env python3
"""Cross-season continuity of contracts, clubs, players and uniform numbers (`runtime/continuity.py`).

    python scripts/audit_continuity.py          print every problem; exit 1 if any

Read-only. Validation and the rollover run the same checks.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from runtime.continuity import errors  # noqa: E402


def main():
    problems = errors(ROOT)
    for p in problems:
        print(p)
    print(f"continuity: {len(problems)} problem(s)" if problems else "continuity: contracts, clubs, players and numbers carry over intact")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
