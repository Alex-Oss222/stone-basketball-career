#!/usr/bin/env python3
"""Convert raw schedule exports in library/incoming/ into canonical season files.

Reads every CSV, TSV, JSON or XLSX file in library/incoming/ (or the paths
given), groups games by season, strips every result column, and writes
library/<start year>/league/nba_<YYYY>_<YY>_schedule.json. Prints each
season's validation result. Raw files are left in place for review.
"""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from datetime import date
from runtime.schedule import read_games, schedule_path, season_of_date, validate_schedule

SUFFIXES = {".csv", ".tsv", ".json", ".xlsx"}
paths = [Path(p) for p in sys.argv[1:]] or sorted(p for p in (ROOT / "library/incoming").rglob("*")
                                                  if p.suffix.lower() in SUFFIXES)
seasons, failures = {}, 0
for path in paths:
    try:
        games, stripped = read_games(path)
    except (ValueError, StopIteration, KeyError, IndexError) as exc:
        print(f"SKIP {path.name}: {exc}")
        failures += 1
        continue
    print(f"read {path.name}: {len(games)} games; dropped columns: {', '.join(stripped) or 'none'}")
    for g in games:
        entry = seasons.setdefault(season_of_date(date.fromisoformat(g["date"])), {"games": {}, "sources": set()})
        entry["games"][g["game_id"]] = g
        entry["sources"].add(path.name)

for season, entry in sorted(seasons.items()):
    data = {
        "schema_version": 1, "league": "NBA", "season": season, "kind": "regular_season_schedule",
        "source": "Imported from " + ", ".join(sorted(entry["sources"])) + " by scripts/import_schedules.py; result columns stripped.",
        "games": sorted(entry["games"].values(), key=lambda g: (g["date"], g["home"])),
    }
    out = schedule_path(season, ROOT)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    errors = validate_schedule(data, season, ROOT)
    failures += bool(errors)
    print(f"{season}: {len(data['games'])} games -> {out.relative_to(ROOT)}  " + ("OK" if not errors else f"{len(errors)} problem(s)"))
    for e in errors[:15]:
        print("   ", e)
raise SystemExit(1 if failures else 0)
