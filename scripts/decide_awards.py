#!/usr/bin/env python3
"""Close the weekly, monthly and season NBA awards announced on or before the career clock (`runtime/award_decisions.py`,
`runtime/season_awards.py`).

    python scripts/decide_awards.py --write     decide every award now due; record it and update the pages
    python scripts/decide_awards.py --check     list awards due but not decided; write nothing

Decisions read closed results only, are recorded once and are never recomputed. A Wade win is added to
`career/Dwyane_Wade/awards.json`; the player reports are then rebuilt.
"""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime import award_decisions, season_awards                    # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        errors = award_decisions.award_errors(ROOT) + season_awards.season_award_errors(ROOT)
        print("\n".join(errors) or "Every award due is decided.")
        return 1 if errors else 0
    new = award_decisions.decide(ROOT)
    for d in new:
        print(f"{d['announced_on']}  {d['conference']} {d['name']} ({d['period_start']} to {d['period_end']}): {d['winner'] or 'no award'}")
    season = season_awards.decide(ROOT)
    for d in season:
        named = d.get("winners") or [p["player"] for t in d["teams"] for p in t["players"]]
        print(f"{d['announced_on']}  {d['name']}: {', '.join(named)}")
    new = new + season
    print(f"{len(new)} decision(s) closed")
    if new:
        from scripts.refresh_career_views import refresh_career_views
        print(f"Updated {len(refresh_career_views(ROOT))} detailed career views.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
