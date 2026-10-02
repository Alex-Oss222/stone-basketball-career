#!/usr/bin/env python3
"""Import every club's basketball staff, season by season (league organization).

Source: each club's Basketball-Reference season page (head coach(es), top
basketball executive, and the "Assistant Coaches and Staff" list), collected
into one raw JSON file keyed "<season end year>-<club code>". Writes
library/<year>/league/nba_<season>_staffs.json for 2002-03 to 2013-14.

Kept: names, roles, and the order of a club's head coaches. A club that changed
head coach during a season gets each coach's part of the season (`window`),
placed by his games coached, the same way traded players are placed. Dropped:
win-loss records, which are real results. Miami's real staff is kept only for
2002-03, the season completed before the career began; from 2003-04 Miami's
staff is simulated (career/Dwyane_Wade/<season>/00_Team/Organization/).

These are reference records for the world, not decisions: the other clubs have
no simulated front office. A coach, assistant or executive counts as with his
real club only on dates the career clock has reached, and once simulated Miami
hires him he leaves his real club from that date (as AGENTS.md rule 2 does for
players).

Head coaches' games coached and IDs come from the uploaded Basketball-Reference
season coaches tables (library/incoming/nba_coaches_2003_2014/); the club
pages give their order within a season.

Usage: python scripts/import_staffs.py <raw.json>
"""
import csv
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SOURCE = "Basketball-Reference team season pages (https://www.basketball-reference.com/teams/<code>/<year>.html)"
SIMULATED = "MIA"
# The end-of-2002-03 baseline uses ESPN-style codes; Basketball-Reference's differ for these clubs.
BBR_CODES = {"GS": "GSW", "NJ": "NJN", "NO": "NOH", "NY": "NYK", "PHX": "PHO", "SA": "SAS", "UTAH": "UTA", "WSH": "WAS"}
ROLE_WORDS = ("Assistant", "Associate", "Head", "Lead", "Trainer", "Athletic", "Strength", "Player", "Scout",
              "Advance", "Director", "Video", "Coach", "Consultant", "Special", "Shooting", "Development",
              "Equipment", "Team", "General", "Vice", "President", "Physical", "Massage", "Manager", "Coordinator")


def split_role(line):
    words = line.split()
    for i, word in enumerate(words[1:], start=1):
        if word.strip(",/") in ROLE_WORDS:
            return " ".join(words[:i]), " ".join(words[i:])
    return line, "Staff"


def head_coaches(text):
    """'A (11-16), B (24-31)' -> [(name, games)] in order; records are only used for games coached."""
    out = []
    for name, wins, losses in re.findall(r"([^,(]+?)\s*\((\d+)-(\d+)\)", text or ""):
        out.append((name.strip(), int(wins) + int(losses)))
    if not out and text:
        out = [(text.split("(")[0].strip(), 0)]
    return out


def club_names():
    names = {BBR_CODES.get(c["code"], c["code"]): n for n, c in json.loads(
        (ROOT / "library/2003/league/nba_2003_end_of_season.json").read_text(encoding="utf-8"))["clubs"].items()}
    by_season = {2003: dict(names)}
    for path in (ROOT / "library").glob("*/league/*_team_rosters.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        year = int(data["season"][:4]) + 1
        by_season[year] = {c["code"]: n for n, c in data["clubs"].items()}
        by_season[year][SIMULATED] = "Miami Heat"
    return by_season


def coach_tables(folder):
    """(season end year, club code) -> [(coach, games, bbr coach id)] from the uploaded coaches tables."""
    out = {}
    for path in sorted(Path(folder).glob("nba_*_coaches.csv")):
        year = int(re.search(r"nba_(\d{4})_coaches", path.name).group(1))
        rows = list(csv.reader(path.open(encoding="utf-8-sig")))
        header = next(r for r in rows if r and r[0] == "Coach")
        team, games, ident = header.index("Tm"), header.index("G"), header.index("Coach-additional")
        for r in rows:
            if len(r) == len(header) and r[0] and r[0] != "Coach" and r[team]:
                out.setdefault((year, r[team]), []).append((r[0], int(r[games] or 0), r[ident]))
    return out


def main(raw_path, coaches_folder=ROOT / "library/incoming/nba_coaches_2003_2014"):
    raw = json.loads(Path(raw_path).read_text(encoding="utf-8"))
    tables = coach_tables(coaches_folder)
    names = club_names()
    seasons = {}
    for key, page in raw.items():
        year, code = int(key[:4]), key[5:]
        if not page.get("ok"):
            raise SystemExit(f"{key}: page was not fetched")
        if code == SIMULATED and year > 2003:
            continue
        # Order from the club's page; games and IDs from the coaches table (records are dropped).
        table = {name: (games, ident) for name, games, ident in tables.get((year, code), [])}
        order = [name for name, _ in head_coaches(page.get("coach"))]
        if set(order) != set(table):
            raise SystemExit(f"{key}: club page coaches {order} differ from the coaches table {sorted(table)}")
        total = sum(g for g, _ in table.values()) or 1
        done, head = 0, []
        for name in order:
            games, ident = table[name]
            head.append({"name": name, "bbr_id": ident or None,
                         "window": [round(done / total, 4), round((done + games) / total, 4)]})
            done += games
        if head:
            head[-1]["window"][1] = 1.0
        staff = [dict(zip(("name", "role"), split_role(line))) for line in page.get("staff", [])]
        executives = [e.strip() for e in (page.get("executive") or "").split(",") if e.strip()]
        seasons.setdefault(year, {})[names[year][code]] = {"code": code, "head_coaches": head,
                                                           "executives": executives, "staff": staff}
    written = []
    for year, clubs in sorted(seasons.items()):
        season = f"{year - 1}-{str(year)[-2:]}"
        data = {"schema_version": 1, "league": "NBA", "season": season, "kind": "league_staffs", "source": SOURCE,
                "usage": ("Each club's head coaches (in order, with the part of the season each coached), top "
                          "basketball executives and assistant/support staff. Reference for the world and the "
                          "hiring pool; no win-loss records. Counts only on dates the career clock has reached; "
                          "Miami's staff from 2003-04 is simulated."),
                "clubs": dict(sorted(clubs.items()))}
        # The 2003 cycle keeps 2002-03 sources in library/2003, like the 2002-03 environment and statistics.
        out = ROOT / f"library/{max(year - 1, 2003)}/league/nba_{year - 1}_{str(year)[-2:]}_staffs.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        written.append(out)
        people = sum(len(c["staff"]) + len(c["head_coaches"]) for c in clubs.values())
        print(f"{season}: {len(clubs)} clubs, {people} coaches and staff")
    print(f"{len(written)} staff files written")


if __name__ == "__main__":
    main(sys.argv[1])
