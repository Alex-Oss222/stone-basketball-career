#!/usr/bin/env python3
"""Build player identity/statistics reports from canonical career evidence."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.player_reports import report_errors
from scripts.refresh_career_views import refresh_career_views


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="read-only freshness and source validation")
    args = parser.parse_args()
    players = [p for p in (ROOT / "career").iterdir() if p.is_dir() and (p / "professional_identity.json").is_file()]
    if not args.check:
        changed = refresh_career_views(ROOT)
        print(f"Updated {len(changed)} detailed career views. Career state and results were not changed.")
        return 0
    for player in players:
        errors = report_errors(ROOT, player)
        if errors:
            print("\n".join(errors))
            return 1
    print("Detailed career views are current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
