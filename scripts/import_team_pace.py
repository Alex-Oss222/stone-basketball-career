#!/usr/bin/env python3
"""Import each club's pace from the Basketball-Reference team tables (engine problem E6).

Reads library/incoming/**/nba_<YYYY>_team_advanced.csv (the Advanced Stats team
table of the season ending in YYYY) and writes, for the season that follows it,
library/<year>/league/nba_<YYYY>_<YY>_team_pace.json.

A season uses each club's pace from the season before, the same rule as the
league environment (AGENTS.md: a season is never calibrated on its own final
numbers). Only Pace is kept, as a club's style of play; wins, margins, ratings
and every other column are real results and are dropped. Miami's row is
ignored (Miami is simulated). Each club's pace is stored relative to the mean of
the clubs in the table, so the league as a whole keeps the calibration
environment's pace. A club with no row the season before (Charlotte in
2004-05) plays at the league pace. The raw CSVs are removed after a clean run.

Usage: python scripts/import_team_pace.py
"""
import csv
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.rotations import load_rosters, pace_path, pace_errors

SOURCE = "Basketball-Reference season pages, Advanced Stats team table (https://www.basketball-reference.com/leagues/NBA_<year>.html)"
SIMULATED_CLUB = "Miami Heat"
# A franchise that moved or was renamed, and the names it played under next.
SUCCESSORS = {"New Orleans Hornets": ("New Orleans/Oklahoma City Hornets", "New Orleans Pelicans"),
              "New Orleans/Oklahoma City Hornets": ("New Orleans Hornets",),
              "Seattle SuperSonics": ("Oklahoma City Thunder",), "New Jersey Nets": ("Brooklyn Nets",)}
FIRST_SEASON, LAST_SEASON = 2003, 2013    # simulated seasons 2003-04 to 2013-14


def read_pace(path):
    rows = list(csv.reader(path.open(encoding="utf-8-sig")))
    header = next(r for r in rows if "Pace" in r and "Team" in r)
    team, pace = header.index("Team"), header.index("Pace")
    out = {}
    for r in rows:
        if len(r) > pace and r[0].strip().isdigit():
            out[r[team].rstrip("*").strip()] = float(r[pace])
    return out


def main():
    files = {int(re.search(r"nba_(\d{4})_team_advanced", p.name).group(1)): p
             for p in (ROOT / "library/incoming").rglob("nba_*_team_advanced.csv")}
    written = []
    for start in range(FIRST_SEASON, LAST_SEASON + 1):
        source_year = start            # the table of the season ending in `start` is the season before
        if source_year not in files:
            raise SystemExit(f"missing nba_{source_year}_team_advanced.csv for {start}-{str(start + 1)[-2:]}")
        season = f"{start}-{str(start + 1)[-2:]}"
        before = {k: v for k, v in read_pace(files[source_year]).items() if k != SIMULATED_CLUB}
        mean = sum(before.values()) / len(before)
        clubs = {}
        for club in load_rosters(season, ROOT):
            source = club if club in before else next(
                (old for old, new in SUCCESSORS.items() if club in new and old in before), None)
            clubs[club] = {"relative_pace": round(before[source] / mean, 4) if source else 1.0,
                           "source_club": source, "source_pace": before.get(source)}
        data = {"schema_version": 1, "league": "NBA", "season": season, "kind": "team_pace",
                "source_season": f"{source_year - 1}-{str(source_year)[-2:]}", "source": SOURCE,
                "source_league_mean_pace": round(mean, 2),
                "usage": ("Each real club's pace from the season before, relative to that season's mean; "
                          "a club's style of play for the engine, not a result. Miami is simulated and excluded."),
                "clubs": clubs}
        out = ROOT / pace_path(season)
        out.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        written.append(out)
        new = [c for c, v in clubs.items() if v["source_club"] is None]
        print(f"{season}: {len(clubs)} clubs from {data['source_season']}"
              + (f"; league pace for {', '.join(new)}" if new else ""))
    errors = pace_errors(ROOT)
    if errors:
        raise SystemExit("team pace validation failed: " + "; ".join(errors[:10]))
    for path in files.values():
        path.unlink()
    for folder in {p.parent for p in files.values()}:
        if folder != ROOT / "library/incoming" and not any(folder.iterdir()):
            folder.rmdir()
    print(f"{len(written)} team pace files written; raw tables removed from library/incoming")


if __name__ == "__main__":
    main()
