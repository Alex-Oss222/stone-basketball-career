#!/usr/bin/env python3
"""Miami's regular-season game notes and requests from the schedule, on their dates (roadmap item 10).

  python scripts/build_season_games.py --write 2003-10-31    write every Miami game due by October 31
  python scripts/build_season_games.py --check 2003-10-31    report what is due and unwritten; write nothing

For each Miami regular-season game on or before the date that has no note yet, the note
`06_Regular_Season/<month>/Week_N/Game_N.md` (scheduled, competition regular, result_file) and the
request `Game_N.request.json` next to it: Miami's players from the staff rotation
in force on the game date (camp's `rotation.json`, then `Depth_Chart/Reviews/<date>/rotation.json`),
less the players the engine's injury draws keep out,
re-scaled to 240 minutes, with Wade's perimeter-defense grade while it is in force; the opponent's
real roster. Every request is validated with `runtime.game_requests.load_request` before it is kept,
and the generated player report pages are rebuilt afterwards. A game is never written before its
date, a request is never rewritten, and nothing is committed here (`runtime/season_games.py`).
Before crossing a due fortnightly review, complete `scripts/review_rotation.py`
and collect any starting-battle draws. An injured starter's next healthy backup
gets an explicit start in the request and in the engine box score.
From November 12, 2003 each request carries the twelve who dress and the injured list
is dated in `00_Team/Transactions/injured_list.json` (`runtime/roster_moves.py`). One game at
a time: a game is refused while an earlier Miami request has no result. The guarantee review
(`scripts/guarantee_review.py`) must be recorded before games after January 7, 2004.
"""
import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from runtime import season_games  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", metavar="DATE", help="write every Miami game due on or before DATE")
    group.add_argument("--check", metavar="DATE", help="verify without writing")
    args = parser.parse_args()
    if args.check:
        problems = season_games.miami_check(args.check, ROOT)
        for p in problems:
            print(f"- {p}")
        print("Miami game records are complete through " + args.check if not problems else f"{len(problems)} problem(s)")
        return 1 if problems else 0
    plan = season_games.build_miami(args.write, ROOT, write=True)
    for row in plan:
        out = [p for p, n in row.get("injured_out", {}).items()]
        print(f"{row['request_path'].relative_to(ROOT)}  {row['game']['game_id']}" + (f"  out: {', '.join(out)}" if out else ""))
    if plan:
        changed = 0 if os.getenv("ADVANCE_LIGHT") else season_games.refresh_reports(ROOT)
        print(f"{len(plan)} game(s) written; {changed} player report page(s) refreshed")
        waiting = season_games.miami_games_due(args.write, ROOT)
        if waiting:
            print(f"{len(waiting)} later game(s) wait for the result of {plan[-1]['game']['date']} (one game at a time)")
    else:
        print("nothing due: every Miami game through " + args.write + " is written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
