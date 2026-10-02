#!/usr/bin/env python3
"""Convert raw schedule exports in library/incoming/ into canonical season files.

Reads every CSV, TSV, JSON or XLSX file in library/incoming/ (or the paths
given), groups games by season and kind (regular season or preseason),
strips every result column, writes
library/<start year>/league/nba_<YYYY>_<YY>_[preseason_]schedule.json and
validates it. A raw file whose output validates is removed from incoming/;
anything that fails stays there for review.
"""
from datetime import date
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.schedule import KINDS, read_games, schedule_path, season_of_date, source_header, validate_schedule

SUFFIXES = {".csv", ".tsv", ".json", ".xlsx"}
paths = [Path(p) for p in sys.argv[1:]] or sorted(p for p in (ROOT / "library/incoming").rglob("*")
                                                  if p.suffix.lower() in SUFFIXES)
groups, failures = {}, 0
for path in paths:
    try:
        kind, source = source_header(path)
        if kind not in KINDS:
            raise ValueError(f"unsupported kind {kind!r}")
        games, stripped = read_games(path)
    except (ValueError, StopIteration, KeyError, IndexError) as exc:
        print(f"SKIP {path.name}: {exc}")
        failures += 1
        continue
    print(f"read {path.name} ({kind}): {len(games)} games; dropped columns: {', '.join(stripped) or 'none'}")
    for g in games:
        key = (season_of_date(date.fromisoformat(g["date"])), kind)
        entry = groups.setdefault(key, {"games": {}, "files": [], "sources": []})
        entry["games"][g["game_id"]] = g
        if path not in entry["files"]:
            entry["files"].append(path)
            entry["sources"].append(source or f"{path.name} (no source recorded)")

for (season, kind), entry in sorted(groups.items()):
    data = {
        "schema_version": 1, "league": "NBA", "season": season, "kind": kind,
        "source": " | ".join(entry["sources"]),
        "games": sorted(entry["games"].values(), key=lambda g: (g["date"], g["home"])),
    }
    out = schedule_path(season, ROOT, kind)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    errors = validate_schedule(data, season, ROOT, kind)
    print(f"{season} {kind}: {len(data['games'])} games -> {out.relative_to(ROOT)}  "
          + ("OK" if not errors else f"{len(errors)} problem(s)"))
    for e in errors[:15]:
        print("   ", e)
    if errors:
        failures += 1
    else:
        for path in entry["files"]:
            if path.is_relative_to(ROOT / "library/incoming"):
                path.unlink()
raise SystemExit(1 if failures else 0)
