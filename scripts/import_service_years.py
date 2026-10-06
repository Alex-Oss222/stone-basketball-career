#!/usr/bin/env python3
"""Import each tracked player's first NBA season (Basketball-Reference player index) as identity data.

    python scripts/import_service_years.py --write                 # the 2004 file
    python scripts/import_service_years.py --year 2005 --write     # the 2005 file

Writes `library/<year>/league/nba_<year>_service_years.json`: for every tracked player, his first season (`year_min`
on the index) and the seasons from it to the season before the offseason (2003-04 for 2004, 2004-05 for 2005), which
that offseason's market uses as years of service where the free-agent rights files have no sourced count. The index's
last-season column is never stored (it would be hindsight). Seasons since debut overstate service for a player who
missed whole seasons; a sourced count always wins (`runtime/free_agency_2004.identity`).

2004 tracks the registry and the 2003-04 and 2004-05 real rosters. 2005 tracks every player in
`library/careers/nba_player_careers.json`, the registry and the 2004-05 and 2005-06 real rosters, and keeps only
players who debuted by 2004-05 (anyone who could be a 2005 free agent with NBA service; a later debut would be
hindsight and is counted, not listed).
"""
import argparse
import json
from pathlib import Path
import re
import string
import sys
import time
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
INDEX = "https://www.basketball-reference.com/players/{}/"
ROW = re.compile(r'data-append-csv="([a-z0-9]+)"[^>]*>.*?data-stat="year_min" >(\d{4})<', re.S)
YEARS = {2004: ("2003-04", "2004-05"), 2005: ("2004-05", "2005-06")}


def out_path(year):
    return ROOT / f"library/{year}/league/nba_{year}_service_years.json"


def tracked(year=2004):
    from runtime.rotations import load_rosters
    out = set()
    registry = json.loads((ROOT / "career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json").read_text(encoding="utf-8"))
    out |= {p["bbr_id"] for p in (registry["players"] if isinstance(registry, dict) else registry) if p.get("bbr_id")}
    for season in YEARS[year]:
        out |= {p["bbr_id"] for c in load_rosters(season, ROOT).values() for p in c["players"] if p.get("bbr_id")}
    if year >= 2005:
        out |= set(json.loads((ROOT / "library/careers/nba_player_careers.json").read_text(encoding="utf-8"))["players"])
    return out


def use_text(year):
    doc = __doc__.split("\n\n", 2)[2].strip()
    last = f"{year - 1}-{str(year)[-2:]}"
    return doc if year == 2004 else doc.replace("the season before the offseason (2003-04 for 2004, 2004-05 for 2005)", last)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--year", type=int, default=2004, choices=sorted(YEARS))
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    year = args.year
    want, first = tracked(year), {}
    for letter in string.ascii_lowercase:
        try:
            html = urlopen(Request(INDEX.format(letter), headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read().decode()
        except Exception as exc:                                   # some letters (x) have no page
            print(f"{letter}: {exc}")
            continue
        for row in html.split("<tr")[1:]:
            m = ROW.search(row)
            if m and m.group(1) in want:
                first[m.group(1)] = int(m.group(2))
        time.sleep(3.5)                                            # the site's crawl limit
    key = f"seasons_through_{year - 1}_{str(year)[-2:]}"
    later = sorted(b for b, y in first.items() if y > year)        # debuted after the offseason: not listed
    players = {b: {"first_season": f"{y - 1}-{str(y)[-2:]}", key: max(0, year - y + 1)}
               for b, y in sorted(first.items()) if y <= year}
    data = {"schema_version": 1, "kind": "service_years", "source": "https://www.basketball-reference.com/players/<letter>/ (year_min)",
            "use": use_text(year), "players": players, "missing": sorted(want - set(first))}
    if year >= 2005:
        data["as_of"] = f"{year}-06-30"
        data["tracked"] = "library/careers/nba_player_careers.json, the player registry and the " + " and ".join(YEARS[year]) + " real rosters"
        data["debuted_later_not_listed"] = len(later)
    print(f"{len(players)} players, {len(data['missing'])} missing, {len(later)} debuted later")
    if args.write:
        out_path(year).write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
