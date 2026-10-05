#!/usr/bin/env python3
"""Import each tracked player's first NBA season (Basketball-Reference player index) as identity data.

    python scripts/import_service_years.py --write

Writes `library/2004/league/nba_2004_service_years.json`: for every player in the registry or on the 2003-04 and
2004-05 real rosters, his first season (`year_min` on the index) and the seasons from it to 2003-04, which the 2004
market uses as years of service where the 2004 or 2003 free-agent rights files have no sourced count. The index's
last-season column is never stored (it would be hindsight). Seasons since debut overstate service for a player who
missed whole seasons; a sourced count always wins (`runtime/free_agency_2004.identity`).
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
OUT = ROOT / "library/2004/league/nba_2004_service_years.json"
INDEX = "https://www.basketball-reference.com/players/{}/"
ROW = re.compile(r'data-append-csv="([a-z0-9]+)"[^>]*>.*?data-stat="year_min" >(\d{4})<', re.S)


def tracked():
    from runtime.rotations import load_rosters
    out = set()
    registry = json.loads((ROOT / "career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json").read_text(encoding="utf-8"))
    out |= {p["bbr_id"] for p in (registry["players"] if isinstance(registry, dict) else registry) if p.get("bbr_id")}
    for season in ("2003-04", "2004-05"):
        out |= {p["bbr_id"] for c in load_rosters(season, ROOT).values() for p in c["players"] if p.get("bbr_id")}
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    want, first = tracked(), {}
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
    players = {b: {"first_season": f"{y - 1}-{str(y)[-2:]}", "seasons_through_2003_04": max(0, 2004 - y + 1)}
               for b, y in sorted(first.items())}
    data = {"schema_version": 1, "kind": "service_years", "source": "https://www.basketball-reference.com/players/<letter>/ (year_min)",
            "use": __doc__.split("\n\n", 2)[2].strip(), "players": players, "missing": sorted(want - set(first))}
    print(f"{len(players)} players, {len(data['missing'])} missing")
    if args.write:
        OUT.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
