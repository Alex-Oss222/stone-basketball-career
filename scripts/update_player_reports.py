#!/usr/bin/env python3
"""Build player identity/statistics reports from canonical career evidence."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.player_reports import build_reports, report_errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="read-only freshness and source validation")
    args = parser.parse_args()
    players = [p for p in (ROOT / "career").iterdir() if p.is_dir()]
    changed = 0
    for player in players:
        if args.check:
            errors = report_errors(ROOT, player)
            if errors:
                print("\n".join(errors))
                return 1
        else:
            # Build everything before writing: malformed evidence cannot leave a half-rendered report set.
            outputs = build_reports(ROOT, player)
            for page, text in outputs.items():
                if not page.is_file() or page.read_text(encoding="utf-8") != text:
                    page.parent.mkdir(parents=True, exist_ok=True)
                    page.write_text(text, encoding="utf-8")
                    changed += 1
    print("Player reports are current." if args.check else f"Updated {changed} player reports. Career state and results were not changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
