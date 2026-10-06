#!/usr/bin/env python3
"""Build a season's real uniform numbers, club by club, from Basketball-Reference team pages.

  python scripts/import_jerseys.py --season 2004-05 --pages DIR --fetch --write
  python scripts/import_jerseys.py --season 2003-04 --pages DIR --check
  python scripts/import_jerseys.py --season 2005-06 --pages DIR --fetch --write

Team pages (https://www.basketball-reference.com/teams/{ABBR}/{YEAR}.html) are cached as DIR/{ABBR}.html;
--fetch downloads the missing ones, one request every 3.5 seconds (Basketball-Reference crawl limit). Only the
roster table is read. Miami's real roster is recorded as reference, as in 2003-04. The historical Dwyane Wade
(wadedw01) is never recorded with a number: the simulated Wade's number is set by a simulated decision
(runtime/jerseys.py). A player listed with two numbers keeps both, noted as a change during the season.
"""
import argparse
import html
import json
from pathlib import Path
import re
import sys
import time
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from runtime.trajectories import PROTAGONIST_IDS  # noqa: E402

CLUBS = [("ATL", "Atlanta Hawks"), ("BOS", "Boston Celtics"), ("CHA", "Charlotte Bobcats"), ("CHI", "Chicago Bulls"),
         ("CLE", "Cleveland Cavaliers"), ("DAL", "Dallas Mavericks"), ("DEN", "Denver Nuggets"),
         ("DET", "Detroit Pistons"), ("GSW", "Golden State Warriors"), ("HOU", "Houston Rockets"),
         ("IND", "Indiana Pacers"), ("LAC", "Los Angeles Clippers"), ("LAL", "Los Angeles Lakers"),
         ("MEM", "Memphis Grizzlies"), ("MIA", "Miami Heat"), ("MIL", "Milwaukee Bucks"),
         ("MIN", "Minnesota Timberwolves"), ("NJN", "New Jersey Nets"), ("NOH", "New Orleans Hornets"),
         ("NYK", "New York Knicks"), ("ORL", "Orlando Magic"), ("PHI", "Philadelphia 76ers"), ("PHO", "Phoenix Suns"),
         ("POR", "Portland Trail Blazers"), ("SAC", "Sacramento Kings"), ("SAS", "San Antonio Spurs"),
         ("SEA", "Seattle SuperSonics"), ("TOR", "Toronto Raptors"), ("UTA", "Utah Jazz"), ("WAS", "Washington Wizards")]
SEASONS = {
    "2003-04": {"researched": "2026-10-05", "clubs": [c for c in CLUBS if c[0] != "CHA"]},
    "2004-05": {"researched": "2026-10-05", "clubs": CLUBS},
    # The Hornets played 2005-06 in Oklahoma City after Hurricane Katrina (Basketball-Reference code NOK).
    "2005-06": {"researched": "2026-10-06",
                "clubs": [("NOK", "New Orleans/Oklahoma City Hornets") if c[0] == "NOH" else c for c in CLUBS]},
}
PATTERN = "https://www.basketball-reference.com/teams/{ABBR}/%d.html"
WADE_NOTE = ("The real Dwyane Wade is not recorded here: the simulated Wade's uniform number is set by a "
             "simulated decision (runtime/jerseys.py).")
CRAWL_DELAY = 3.5


def end_year(season):
    return int(season[:4]) + 1


def output_path(season):
    start = int(season[:4])
    return Path(f"library/{start}/league/nba_{start}_{str(start + 1)[-2:]}_jerseys.json")


def fetch_pages(season, pages):
    pages.mkdir(parents=True, exist_ok=True)
    first = True
    for abbr, _ in SEASONS[season]["clubs"]:
        target = pages / f"{abbr}.html"
        if target.is_file():
            continue
        if not first:
            time.sleep(CRAWL_DELAY)
        first = False
        url = (PATTERN % end_year(season)).replace("{ABBR}", abbr)
        request = Request(url, headers={"User-Agent": "Mozilla/5.0 (stone-basketball-career research import)"})
        with urlopen(request, timeout=60) as response:
            target.write_bytes(response.read())
        print(f"fetched {url}")


def build(season, pages):
    pattern = PATTERN % end_year(season)
    players, unresolved = {}, []
    for abbr, club in SEASONS[season]["clubs"]:
        page = (pages / f"{abbr}.html").read_text(encoding="utf-8")
        start = page.find('id="roster"')
        if start < 0:
            raise ValueError(f"{abbr}: no roster table")
        table = page[start:page.find("</table>", start)]
        url = pattern.replace("{ABBR}", abbr)
        count = 0
        for row in re.findall(r"<tr[^>]*>(.*?)</tr>", table, re.S):
            number = re.search(r'data-stat="number"[^>]*>(.*?)</th>', row)
            player = re.search(r'data-append-csv="([^"]+)"[^>]*><a[^>]*>(.*?)</a>', row)
            if not player:
                continue
            count += 1
            num = html.unescape(re.sub("<[^>]+>", "", number.group(1))).strip() if number else ""
            bbr, name = player.group(1), html.unescape(player.group(2))
            if bbr in PROTAGONIST_IDS:
                unresolved.append({"bbr_id": bbr, "player": name, "club": club, "source": url, "note": WADE_NOTE})
                continue
            if not num:
                unresolved.append({"bbr_id": bbr, "player": name, "club": club, "source": url,
                                   "note": "No uniform number listed on the team page."})
                continue
            entry = {"player": name, "club": club, "number": num, "source": url}
            if "," in num:
                entry["note"] = "Two numbers listed on the team page: changed number during the season."
            players.setdefault(bbr, []).append(entry)
        if not count:
            raise ValueError(f"{abbr}: empty roster table")
    return {"schema_version": 1, "season": season, "kind": "jersey_numbers",
            "researched": SEASONS[season]["researched"], "source_pattern": pattern,
            "players": dict(sorted(players.items())), "unresolved": unresolved}


def rendered(season, pages):
    return json.dumps(build(season, pages), indent=1, ensure_ascii=False) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    parser.add_argument("--season", default="2003-04", choices=sorted(SEASONS))
    parser.add_argument("--pages", required=True, help="directory of cached team pages, {ABBR}.html")
    parser.add_argument("--fetch", action="store_true", help="download missing team pages (3.5 s apart)")
    args = parser.parse_args()
    pages = Path(args.pages)
    if args.fetch:
        fetch_pages(args.season, pages)
    expected = rendered(args.season, pages)
    target = ROOT / output_path(args.season)
    if args.write:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(expected, encoding="utf-8")
        data = json.loads(expected)
        print(f"Wrote {output_path(args.season)}; {len(data['players'])} players, "
              f"{sum(len(v) for v in data['players'].values())} club entries, {len(data['unresolved'])} unresolved.")
        return 0
    if not target.is_file() or target.read_text(encoding="utf-8") != expected:
        print(f"Stale or missing {output_path(args.season)}; run with --season {args.season} --write.")
        return 1
    print(f"{output_path(args.season)} matches the team pages.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
