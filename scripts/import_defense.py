#!/usr/bin/env python3
"""Build a completed season's Defensive Box Plus/Minus file for the front office's skill-fit read.

  python scripts/import_defense.py --check                    # 2002-03 (default)
  python scripts/import_defense.py --season 2003-04 --write

Reads the pinned Basketball-Reference advanced table (sumitrodatta/nba-alt-awards copy), verifies its
SHA-256, keeps only that season's NBA rows, takes a traded player's season-total row (TOT/2TM/3TM) once
and otherwise his sole team row. The historical Dwyane Wade (wadedw01) is never recorded: his real
statistics never enter the simulation. Each file is dated the day its season was known closed; later
seasons' values are never used. --source reads an already downloaded copy of the same pinned file.
"""
import argparse
from collections import defaultdict
import csv
import hashlib
import io
import json
from pathlib import Path
import sys
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from runtime.trajectories import PROTAGONIST_IDS  # noqa: E402

REVISION = "7f9b3375439b79cb4e62f66ae7d12160275c2863"
URL = f"https://raw.githubusercontent.com/sumitrodatta/nba-alt-awards/{REVISION}/2026/Data/Advanced.csv"
UPSTREAM_SHA256 = "e1616ffe7759c22b014cbbb7c7ce10a591615e7ef1e08cc0dba4d2a02872948d"
AGGREGATE_TEAMS = {"TOT", "2TM", "3TM", "4TM", "5TM"}
NOTE = ("Defensive Box Plus/Minus for the completed {season} regular season (a traded player's season total row), "
        "for the front office's skill-fit read. Known on the date: the season had closed. Never {later} or later "
        "values; the engine's talent trajectories keep their own DBPM and are never read by the front office.")
SEASONS = {
    "2002-03": {"as_of": "2003-06-26", "retrieved_on": "2026-10-04"},
    "2003-04": {"as_of": "2004-04-15", "retrieved_on": "2026-10-05",
                "excluded": {"wadedw01": "the historical Dwyane Wade: his real statistics never enter the simulation"}},
}
DEFAULT_SEASON = "2002-03"


def output_path(season):
    start = int(season[:4])
    return Path(f"library/{start + 1}/league/nba_{start}_{str(start + 1)[-2:]}_defense.json")


def read_source(path=None):
    if path:
        raw = Path(path).read_bytes()
    else:
        with urlopen(URL, timeout=120) as response:
            raw = response.read()
    if hashlib.sha256(raw).hexdigest() != UPSTREAM_SHA256:
        raise ValueError("Advanced.csv: SHA-256 mismatch with the pinned revision")
    return list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))


def build(rows, season):
    start = int(season[:4])
    year = str(start + 1)
    grouped = defaultdict(list)
    for row in rows:
        if row["season"] == year and row["lg"] == "NBA" and row["player_id"] not in PROTAGONIST_IDS:
            grouped[row["player_id"]].append(row)
    if not grouped:
        raise ValueError(f"source contains no NBA {season} rows")
    players = {}
    for bbr, group in sorted(grouped.items()):
        total = [row for row in group if row["team"] in AGGREGATE_TEAMS]
        if len(total) > 1 or (not total and len(group) != 1):
            raise ValueError(f"ambiguous season rows for {bbr}")
        row = (total or group)[0]
        players[bbr] = {"dbpm": float(row["dbpm"]) if row["dbpm"] not in ("", "NA") else None,
                        "minutes": int(row["mp"])}
    spec = SEASONS[season]
    later = f"{start + 1}-{str(start + 2)[-2:]}"
    out = {
        "schema_version": 1, "season": season, "kind": "defensive_box_plus_minus", "as_of": spec["as_of"],
        "note": NOTE.format(season=season, later=later),
        "source": {"url": URL,
                   "provider": f"Basketball-Reference advanced table (NBA_{year}_advanced.html), via the sumitrodatta/nba-alt-awards GitHub copy",
                   "retrieved_on": spec["retrieved_on"]},
    }
    if "excluded" in spec:
        out["excluded"] = spec["excluded"]
    out["players"] = players
    return out


def rendered(rows, season):
    return json.dumps(build(rows, season), indent=1, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    parser.add_argument("--season", default=DEFAULT_SEASON, choices=sorted(SEASONS))
    parser.add_argument("--source", help="a downloaded copy of the pinned Advanced.csv (checksum-verified)")
    args = parser.parse_args()
    expected = rendered(read_source(args.source), args.season)
    target = ROOT / output_path(args.season)
    if args.write:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(expected, encoding="utf-8")
        print(f"Wrote {output_path(args.season)}; {len(json.loads(expected)['players'])} players.")
        return 0
    if not target.is_file() or target.read_text(encoding="utf-8") != expected:
        print(f"Stale or missing {output_path(args.season)}; run with --season {args.season} --write.")
        return 1
    print(f"{output_path(args.season)} matches the pinned source.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
