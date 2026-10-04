#!/usr/bin/env python3
"""The symmetric league's day (docs/symmetric_league_design.md): the market every day, the trade scan on Mondays.

    python scripts/league_day.py --write 2004-01-05     run the day; nothing happens while the switch is off

The trade scan writes engine decision packets (`League/Trade_Draws/`); draw them with
`python scripts/draw_decisions.py`, then run this command again for the same date to execute accepted deals.
"""
import argparse
from datetime import date
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime import league_book                                        # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--write", metavar="DATE", required=True)
    day = parser.parse_args().write
    if not league_book.active(day):
        print(f"symmetric league off on {day} (SYMMETRIC_FROM {league_book.SYMMETRIC_FROM}); nothing to do")
        return 0
    from runtime.league_market import LeagueMarket
    from runtime.market import Market
    for e in LeagueMarket(day, Market(day, ROOT), ROOT).run():
        print(f"{e['date']}  {e['kind']:15} {e['player']}  {e['from'] or 'free agent'} -> {e['to'] or 'free agent'}")
    if date.fromisoformat(day).weekday() == 0:
        from runtime.league_trades import DEADLINE, weekly
        if day <= DEADLINE:
            written, executed = weekly(ROOT, day)
            print(f"trade scan: {len(written)} packet(s) written, {len(executed)} deal(s) executed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
