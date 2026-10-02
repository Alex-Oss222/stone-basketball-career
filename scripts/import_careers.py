#!/usr/bin/env python3
"""Import the Basketball-Reference season tables (totals + advanced, 2003-04 to 2013-14).

Writes two kinds of library files:

* library/careers/nba_player_careers.json: every real player's season rates for
  the engine (option C), plus his Defensive Box Plus/Minus (DBPM, points per
  100 possessions against a league-average defender) for the engine's defense.
  One row per player-season, from the combined row of a traded player.
* library/<year>/league/nba_<YYYY>_<YY>_team_rosters.json: every non-Miami
  club's real roster and minutes for that season (option D).

Removed on import:
* the historical Dwyane Wade (`wadedw01`): the career's Wade is alternate
  history and his real statistics must never enter;
* the Awards column (real honors are results, not ability);
* Miami's real roster (Miami is simulated).

Usage: python scripts/import_careers.py [folder]   (default docs/nba_careers_2004_2014)
"""
import csv
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.player_stats import RATE_KEYS
from runtime.trajectories import CAREERS_PATH, PROTAGONIST_IDS, careers_errors

MULTI = re.compile(r"^(TOT|\d+TM)$")
SIMULATED_CLUB = "MIA"
CODES = {
    "ATL": "Atlanta Hawks", "BOS": "Boston Celtics", "BRK": "Brooklyn Nets", "CHA": "Charlotte Bobcats",
    "CHI": "Chicago Bulls", "CLE": "Cleveland Cavaliers", "DAL": "Dallas Mavericks", "DEN": "Denver Nuggets",
    "DET": "Detroit Pistons", "GSW": "Golden State Warriors", "HOU": "Houston Rockets", "IND": "Indiana Pacers",
    "LAC": "Los Angeles Clippers", "LAL": "Los Angeles Lakers", "MEM": "Memphis Grizzlies", "MIA": "Miami Heat",
    "MIL": "Milwaukee Bucks", "MIN": "Minnesota Timberwolves", "NJN": "New Jersey Nets",
    "NOH": "New Orleans Hornets", "NOK": "New Orleans/Oklahoma City Hornets", "NOP": "New Orleans Pelicans",
    "NYK": "New York Knicks", "OKC": "Oklahoma City Thunder", "ORL": "Orlando Magic",
    "PHI": "Philadelphia 76ers", "PHO": "Phoenix Suns", "POR": "Portland Trail Blazers",
    "SAC": "Sacramento Kings", "SAS": "San Antonio Spurs", "SEA": "Seattle SuperSonics",
    "TOR": "Toronto Raptors", "UTA": "Utah Jazz", "WAS": "Washington Wizards",
}
SOURCE = "Basketball-Reference season totals and advanced tables (https://www.basketball-reference.com/leagues/NBA_<year>_totals.html and _advanced.html)"


def rows(path):
    table = list(csv.reader(path.open(encoding="utf-8-sig")))
    header = table[0]
    out = []
    for raw in table[1:]:
        if not raw or len(raw) != len(header) or raw[1] in ("Player", "") or raw[0] == "Rk":
            continue
        out.append(dict(zip(header, raw)))
    return out


def num(value):
    value = (value or "").strip()
    return float(value) if value not in ("", "-") else None


def ratio(a, b):
    return a / b if a is not None and b else None


def rates(total, adv):
    t = {k: num(total.get(k)) for k in ("MP", "FGA", "3P", "3PA", "2P", "2PA", "FT", "FTA", "TOV", "PF")}
    pct = lambda key: None if num(adv.get(key)) is None else num(adv[key]) / 100
    out = {
        "two_point_pct": ratio(t["2P"], t["2PA"]), "three_point_pct": ratio(t["3P"], t["3PA"]),
        "free_throw_pct": ratio(t["FT"], t["FTA"]),
        "three_point_attempt_rate": ratio(t["3PA"], t["FGA"]), "free_throw_attempt_rate": ratio(t["FTA"], t["FGA"]),
        "turnovers_per_fga": ratio(t["TOV"], t["FGA"]),
        "usage_pct": pct("USG%"), "assist_pct": pct("AST%"), "offensive_rebound_pct": pct("ORB%"),
        "defensive_rebound_pct": pct("DRB%"), "steal_pct": pct("STL%"), "block_pct": pct("BLK%"),
        "fouls_per_minute": ratio(t["PF"], t["MP"]),
    }
    assert set(out) == set(RATE_KEYS)
    return out


def season_label(year_end):
    return f"{year_end - 1}-{str(year_end)[-2:]}"


def main(folder):
    folder = Path(folder)
    careers = {"schema_version": 1, "kind": "player_career_rates", "source": SOURCE,
               "excluded": ["the alternate-history protagonist (historical Dwyane Wade rows)", "Awards column"], "players": {}}
    written, report = [], []
    for totals_path in sorted(folder.glob("nba_*_totals.csv")):
        year_end = int(re.search(r"nba_(\d{4})_totals", totals_path.name).group(1))
        season = season_label(year_end)
        advanced = {(r["Player-additional"], r["Team"]): r for r in rows(folder / f"nba_{year_end}_advanced.csv")}
        totals = rows(totals_path)
        if len(advanced) != len(totals):
            raise ValueError(f"{season}: totals and advanced row counts differ")
        dropped = sum(1 for r in totals if r["Player-additional"] in PROTAGONIST_IDS)
        totals = [r for r in totals if r["Player-additional"] not in PROTAGONIST_IDS]
        by_player = {}
        for r in totals:
            by_player.setdefault(r["Player-additional"], []).append(r)
        for bbr_id, player_rows in by_player.items():
            combined = [r for r in player_rows if MULTI.match(r["Team"])]
            row = combined[0] if combined else player_rows[0]
            entry = careers["players"].setdefault(bbr_id, {"player_name": row["Player"], "seasons": {}})
            adv = advanced[(bbr_id, row["Team"])]
            entry["seasons"][season] = {"minutes": int(num(row["MP"]) or 0),
                                        "rates": rates(row, adv), "dbpm": num(adv.get("DBPM"))}
        clubs = {}
        for r in totals:
            if MULTI.match(r["Team"]) or r["Team"] == SIMULATED_CLUB:
                continue
            name = CODES[r["Team"]]
            clubs.setdefault(name, {"code": r["Team"], "players": []})["players"].append({
                "player_id": r["Player"], "bbr_id": r["Player-additional"], "position": r["Pos"],
                "games": int(num(r["G"]) or 0), "games_started": int(num(r["GS"]) or 0),
                "minutes": int(num(r["MP"]) or 0)})
        for club in clubs.values():
            club["players"].sort(key=lambda p: -p["minutes"])
        start = year_end - 1
        rosters = {"schema_version": 1, "league": "NBA", "season": season, "kind": "team_rosters",
                   "source": SOURCE,
                   "usage": ("Real rosters and minutes of every non-Miami club for this season (world model D). "
                             "Engine and roster world only: never read by Miami's front office or shown on cards "
                             "before the season is played. Miami is simulated and excluded."),
                   "clubs": dict(sorted(clubs.items()))}
        out = ROOT / f"library/{start}/league/nba_{start}_{str(year_end)[-2:]}_team_rosters.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(rosters, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        written.append(out.relative_to(ROOT))
        report.append(f"{season}: {len(by_player)} players, {len(clubs)} non-Miami clubs; dropped {dropped} historical Wade row(s)")
    errors = careers_errors(careers)
    if errors:
        raise SystemExit("careers validation failed: " + "; ".join(errors[:10]))
    path = ROOT / CAREERS_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(careers, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print("\n".join(report))
    print(f"{len(careers['players'])} players -> {CAREERS_PATH}; {len(written)} roster files")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ROOT / "docs/nba_careers_2004_2014")
