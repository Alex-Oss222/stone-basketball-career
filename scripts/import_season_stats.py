#!/usr/bin/env python3
"""Import a completed season's real player totals and advanced rates (league-wide world data).

    python scripts/import_season_stats.py --season-end 2004 --write

Writes `library/<end>/league/nba_<YYYY>_<YY>_player_stats.json` in the shape of the 2002-03 file: one record per
player (the combined row when he played for several clubs, with every club code), regular season only, from the
Basketball-Reference tables in the pinned sumitrodatta/nba-alt-awards copy. The file is dated the day after the
season's last game; nothing reads it before then (`runtime/player_stats.py` gates on `as_of_date`). League averages
come from the season's league-environment file, which records its own sources.
"""
import argparse
import csv
import io
import json
from pathlib import Path
import sys
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "7f9b3375439b79cb4e62f66ae7d12160275c2863"
BASE = f"https://raw.githubusercontent.com/sumitrodatta/nba-alt-awards/{COMMIT}/2026/Data/"
LAST_DAY = {2004: "2004-04-14", 2005: "2005-04-20"}
EXCLUDED = {"wadedw01"}
TOTALS = {"games": "g", "games_started": "gs", "minutes": "mp", "points": "pts", "field_goals_made": "fg",
          "field_goals_attempted": "fga", "three_pointers_made": "x3p", "three_pointers_attempted": "x3pa",
          "free_throws_made": "ft", "free_throws_attempted": "fta", "offensive_rebounds": "orb",
          "defensive_rebounds": "drb", "assists": "ast", "steals": "stl", "blocks": "blk", "turnovers": "tov",
          "personal_fouls": "pf"}
ADVANCED = {"true_shooting_pct": ("ts_percent", 1), "usage_pct": ("usg_percent", 100), "assist_pct": ("ast_percent", 100),
            "offensive_rebound_pct": ("orb_percent", 100), "defensive_rebound_pct": ("drb_percent", 100),
            "steal_pct": ("stl_percent", 100), "block_pct": ("blk_percent", 100), "turnover_pct": ("tov_percent", 100),
            "three_point_attempt_rate": ("x3p_ar", 1), "free_throw_attempt_rate": ("f_tr", 1)}


def fetch(name):
    with urlopen(BASE + name.replace(" ", "%20"), timeout=120) as r:
        return list(csv.DictReader(io.StringIO(r.read().decode("utf-8"))))


def _num(v, div=1):
    if v in (None, "", "NA"):
        return None
    x = float(v) / div
    return round(x, 3) if div != 1 or "." in v else int(x)


def combine(rows):
    """{bbr_id: (main row, team codes)}: the TOT row when a player has one, else his single row."""
    by = {}
    for r in rows:
        by.setdefault(r["player_id"], []).append(r)
    out = {}
    for pid, rs in by.items():
        tot = [r for r in rs if r["team"] in ("TOT", "2TM", "3TM", "4TM")]
        teams = [r["team"] for r in rs if r["team"] not in ("TOT", "2TM", "3TM", "4TM")]
        out[pid] = (tot[0] if tot else rs[0], teams)
    return out


def build(end):
    season = f"{end - 1}-{str(end)[-2:]}"
    totals = combine([r for r in fetch("Player Totals.csv") if r["season"] == str(end) and r["lg"] == "NBA"])
    advanced = combine([r for r in fetch("Advanced.csv") if r["season"] == str(end) and r["lg"] == "NBA"])
    src = lambda table, page: {"table": table, "url": BASE + ("Player%20Totals.csv" if table == "totals" else "Advanced.csv"),
                               "provider": "Basketball-Reference, via the sumitrodatta/nba-alt-awards GitHub copy",
                               "notes": f"Bulk copy of the table at https://www.basketball-reference.com/leagues/NBA_{end}_{page}.html"}
    records = []
    for pid, (row, teams) in sorted(totals.items()):
        if pid in EXCLUDED:
            continue                     # the historical Wade's statistics never enter the simulation (AGENTS.md)
        adv = advanced.get(pid, (None, None))[0] or {}
        records.append({"player_name": row["player"], "bbr_id": pid, "season_end_year": end, "team_codes": teams,
                        "totals": {k: int(float(row[v])) if row[v] not in ("", "NA") else 0 for k, v in TOTALS.items()},
                        "advanced": {k: _num(adv.get(col), div) for k, (col, div) in ADVANCED.items()},
                        "sources": [src("totals", "totals"), src("advanced", "advanced")], "shooting_by_distance": []})
    env = json.loads((ROOT / f"library/{end}/league/nba_{season.replace('-', '_')}_league_environment.json").read_text(encoding="utf-8"))
    return {"schema_version": "1.0", "dataset_kind": "collected_stats", "as_of_date": LAST_DAY[end][:8] + f"{int(LAST_DAY[end][8:]) + 1:02d}",
            "league": "NBA", "season_type": "regular", "season": season, "records": records,
            "excluded": {"wadedw01": "the historical Dwyane Wade: his real statistics never enter the simulation"},
            "league_averages": [{"season_end_year": end, "averages": env["averages"],
                                 "sources": [{"table": "league_averages", "file": f"library/{end}/league/nba_{season.replace('-', '_')}_league_environment.json"}]}]}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--season-end", type=int, required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    data = build(args.season_end)
    season = data["season"]
    path = ROOT / f"library/{args.season_end}/league/nba_{season.replace('-', '_')}_player_stats.json"
    print(f"{len(data['records'])} players for {season}")
    if args.write:
        path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"written {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
