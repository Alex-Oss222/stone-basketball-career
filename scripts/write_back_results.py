#!/usr/bin/env python3
"""Write the engine's results into the career record (roadmap item 13).

  python scripts/write_back_results.py --write    write every collected result into its records
  python scripts/write_back_results.py --check    verify every result is written; write nothing

For every Miami game note (preseason, regular season) whose result file sits beside it and
whose status is still `scheduled`, and whose date is on or before the career clock: the note
becomes `played` with the score, opponent, venue, the plain-text box score and the Miami
injuries the result reports; the game and the injuries are logged in the owning phase/week
note; each injury goes on the player's Miami card. Then the player reports are rebuilt
(`scripts/update_player_reports.py`), the Miami team pages and the league pages are
aggregated from the closed regular-season results (Miami's notes and the league slate), and
the league player cards are regenerated (`scripts/build_league_cards.py --write`).

The write-back never runs the engine, never advances the clock, never edits a request or a
result file, and never invents data; a result dated after the clock waits. Re-running changes
nothing. `--check` reports an unwritten result, a played note that does not reflect its
result, a stale statistics page or card, and the reporter's own freshness check
(`runtime/write_back.py`).
"""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from runtime import write_back  # noqa: E402
from runtime.player_reports import report_errors  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true", help="write every collected result into the career record")
    group.add_argument("--check", action="store_true", help="verify without writing")
    args = parser.parse_args()
    if args.check:
        problems = write_back.write_back_errors(ROOT, cards=True) + report_errors(ROOT, ROOT / write_back.PLAYER_DIR)
        for p in problems:
            print(f"- {p}")
        print("Every collected result is written into the career record." if not problems else f"{len(problems)} problem(s)")
        return 1 if problems else 0
    report = write_back.run(ROOT, write=True)
    for line in report["written"]:
        print(f"written  {line}")
    for line in report["waiting"]:
        print(f"waiting  {line}")
    for line in report["problems"]:
        print(f"problem  {line}")
    if report["unmatched"]:
        print(f"{len(report['unmatched'])} player(s) in closed results are outside the registry and are not tabulated: "
              + ", ".join(report["unmatched"]))
    print(f"{len(report['written'])} result(s) written; {report['reports']} player report page(s), "
          f"{report['pages']} statistics page(s) and {report['cards']} league card(s) refreshed. "
          "No game was played, no request or result edited, and the clock did not move.")
    return 1 if report["problems"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
