#!/usr/bin/env python3
"""Roll the career into the next season once the summer market has closed (`runtime/rollover.py`).

    python scripts/rollover.py --check        what blocks the rollover today
    python scripts/rollover.py --write        build the new season and make it live

The write runs the rollover, then finishes in a fresh process (every module then reads the new live season):
Miami's finance summary and cap sheet, the season's statistics and award pages, and the detailed views. It prints
Miami's summer: re-signings, signings, rookies, trades, options and departures.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def finish():
    """Second stage, in a process whose live season is the new one."""
    from runtime import season_market, season_pages, signing
    from runtime.gm import FrontOffice
    from runtime.seasons import state
    day = state(None, ROOT)["current_date"]
    writer = signing.Writer(ROOT)
    signing.refresh_finance(writer, FrontOffice(day, season_market.for_date(day, ROOT), ROOT), day)
    writer.commit()
    pages = season_pages.write(signing.SEASON, day, ROOT)
    print(f"{len(pages)} statistics and award pages written for {signing.SEASON}")
    from runtime import write_back
    from runtime.playoff_stats import write_pages as write_playoff_pages
    from runtime.seasons import previous_season
    write_playoff_pages(ROOT, previous_season(signing.SEASON))      # the closed season's pages, as of its close
    report = write_back.run(ROOT, write=True)
    print(f"write-back: {len(report['written'])} result(s), {report['pages']} page(s), {report['reports']} report(s)")
    from scripts.refresh_career_views import refresh_career_views
    print(f"Updated {len(refresh_career_views(ROOT))} detailed career views.")


def report(summary):
    from runtime.rollover import miami_summer
    from runtime.free_agency_2004 import RECORD
    from runtime.seasons import previous_season
    record = json.loads((ROOT / RECORD).read_text(encoding="utf-8"))
    old = json.loads((ROOT / f"career/Dwyane_Wade/{previous_season(summary['season'])}/00_Team/Team/Roster/roster.json").read_text(encoding="utf-8"))
    s = miami_summer(record, old)

    def money(e):
        return f"${e.get('salary') or e.get('amount') or 0:,}" + (f" x {e['years']}" if e.get("years") else "")
    print(f"\nMiami's {summary['season'][:4]} summer")
    for key, label in (("options", "Options"), ("re_signed", "Re-signed"), ("rookies", "Rookies signed"), ("signed", "Signed"),
                       ("traded_in", "Traded for"), ("traded_out", "Traded away")):
        for e in s[key]:
            extra = f" ({e.get('decision')})" if key == "options" else f" from {e['from']}" if e.get("from") and e["from"] != "Miami Heat" else ""
            print(f"  {label}: {e['player']} {money(e) if key != 'options' else ''}{extra} [{e['date']}]")
    for e in s["left"]:
        print(f"  Left: {e['player']} -> {e['to'] or 'unsigned'}" + (f" ({money(e['row'])})" if e.get("row") else ""))
    print(f"\n{summary['season']} register ({len(summary['players'])}): " + ", ".join(summary["players"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--write", action="store_true")
    group.add_argument("--finish", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.finish:
        finish()
        return 0
    from runtime.rollover import Rollover
    from runtime.write_back import clock
    r = Rollover(ROOT)
    blockers = r.blockers(clock(ROOT))
    if args.check or blockers:
        print("\n".join(blockers) or f"Ready: {r.old} rolls into {r.new} on {r.day}.")
        return 1 if blockers else 0
    summary = r.run()
    subprocess.run([sys.executable, str(Path(__file__)), "--finish"], cwd=ROOT, check=True)
    report(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
