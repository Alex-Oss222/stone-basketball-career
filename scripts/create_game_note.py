#!/usr/bin/env python3
"""Create a scheduled or explicit not-played game record."""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date as calendar_date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from runtime.season_rules import month_week, play_in_format, statistics_bucket
from scripts.refresh_career_views import refresh_career_views


def season_dir(requested: str | None = None) -> Path:
    career = ROOT / "career"
    players = [p for p in career.iterdir() if p.is_dir()]
    if len(players) != 1:
        raise SystemExit("expected exactly one player directory under career")
    years = [p for p in players[0].iterdir() if p.is_dir() and re.fullmatch(r"\d{4}-\d{2}", p.name)]
    if requested:
        years = [p for p in years if p.name == requested]
    if len(years) != 1:
        raise SystemExit("select one existing season with --season YYYY-YY")
    return years[0]


def parse_meta(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{path}: missing front matter")
    block = text.split("---\n", 2)[1]
    data = {}
    for line in block.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()
    return data


def game_text(title: str, status: str, date: str, opponent: str, venue: str, reason: str, play_in_game_1: bool,
              competition: str = "regular", cup_stage: str = "") -> str:
    next_line = "next_game_required: false\n" if play_in_game_1 else ""
    return f"""---
type: game
status: {status}
date: {date}
opponent: {opponent}
venue: {venue}
competition: {competition}
cup_stage: {cup_stage}
player_team:
result:
reason: {reason}
simulation_source:
event_id:
result_file:
{next_line}---

# {title}

Player identity and statistics are generated here by `python scripts/update_player_reports.py`.
Decisions remain in the owning phase/week note. A scheduled game has no statistical result.
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--area", choices=("summer-league", "preseason", "regular", "play-in", "playoffs", "cup-championship"), required=True)
    parser.add_argument("--season", help="existing season; defaults only when one season exists")
    parser.add_argument("--cup-stage", choices=("group", "quarterfinal", "semifinal", "championship"), default="")
    parser.add_argument("--month", choices=("October","November","December","January","February","March","April"))
    parser.add_argument("--week", type=int)
    parser.add_argument("--round", choices=("First_Round","Conference_Semifinals","Conference_Finals","Finals"))
    parser.add_argument("--game", type=int, required=True)
    parser.add_argument("--status", choices=("scheduled","not_played"), required=True)
    parser.add_argument("--date", default="")
    parser.add_argument("--opponent", default="")
    parser.add_argument("--venue", choices=("home", "away", "neutral"), default="")
    parser.add_argument("--reason", default="")
    args = parser.parse_args()

    season = season_dir(args.season)
    play_in_game_1 = False
    kind = {"summer-league": "summer_league", "preseason": "preseason", "regular": "regular",
            "play-in": "play_in", "playoffs": "playoff", "cup-championship": "nba_cup_championship"}[args.area]
    cup_stage = args.cup_stage or ("championship" if kind == "nba_cup_championship" else "")
    try:
        statistics_bucket(kind, season.name, cup_stage or None)
        day = calendar_date.fromisoformat(args.date) if args.date else None
    except ValueError as exc:
        parser.error(str(exc))
    if args.game < 1:
        parser.error("game number must be positive")

    if args.status == "scheduled" and (not args.date or not args.opponent or not args.venue):
        parser.error("scheduled games require --date, --opponent and --venue")
    if args.status == "not_played" and not args.reason:
        parser.error("not_played games require --reason")

    if args.area == "regular":
        if args.month is None or args.week is None:
            parser.error("regular games require --month and --week")
        month_folder = {
            "October":"10_October","November":"11_November","December":"12_December",
            "January":"01_January","February":"02_February","March":"03_March","April":"04_April"
        }[args.month]
        target_dir = season / "06_Regular_Season" / month_folder / f"Week_{args.week}"
        if day and (day.strftime("%B") != args.month or month_week(day.day) != args.week or
                    day.year != int(season.name[:4]) + (day.month < 7)):
            parser.error("date does not belong to the requested season/month/week")
        if not target_dir.is_dir():
            parser.error("requested month/week does not exist in the season structure")
        if args.game < 1:
            parser.error("regular-season game number must be positive")
        title = f"{args.month} Week {args.week} Game {args.game}"
    elif args.area == "play-in":
        if play_in_format(season.name) == "2020_restart":
            parser.error("2019-20 requires its verified restart bracket; this helper supports the 2020-21 onward format")
        if args.game not in (1,2):
            parser.error("play-in game must be 1 or 2")
        target_dir = season / "07_Play_In_Tournament"
        title = f"Play-In Game {args.game}"
        play_in_game_1 = args.game == 1
        if args.game == 2:
            first = target_dir / "Game_1.md"
            if not first.exists():
                parser.error("Play-In Game 2 requires Game 1")
            data = parse_meta(first)
            if data.get("status") != "played" or data.get("next_game_required") != "true":
                parser.error("Play-In Game 2 requires played Game 1 with next_game_required: true")
    elif args.area == "playoffs":
        if args.round is None:
            parser.error("playoff games require --round")
        if args.game < 1 or args.game > 7:
            parser.error("playoff game must be 1 through 7")
        target_dir = season / "08_Playoffs" / args.round
        title = f"{args.round.replace('_',' ')} Game {args.game}"
        if args.game >= 5:
            prior = [target_dir / f"Game_{n}.md" for n in range(1, args.game)]
            if any(not p.is_file() for p in prior):
                parser.error("conditional playoff games require all prior games")
            metadata = [parse_meta(p) for p in prior]
            if args.status == "scheduled":
                wins = sum(m.get("result", "").startswith("W") for m in metadata)
                losses = sum(m.get("result", "").startswith("L") for m in metadata)
                if any(m.get("status") != "played" for m in metadata) or wins + losses != len(prior) or max(wins, losses) >= 4:
                    parser.error("conditional game needs a played, undecided series with W/L results")
    elif args.area == "cup-championship":
        if args.game != 1:
            parser.error("NBA Cup championship is one game")
        target_dir = season / "10_NBA_Cup" / "Championship"
        title = "NBA Cup Championship"
    else:
        folder = "02_Summer_League" if args.area == "summer-league" else "05_Preseason"
        target_dir = season / folder
        title = f"{args.area.replace('-', ' ').title()} Game {args.game}"

    target = target_dir / f"Game_{args.game}.md"
    if target.exists():
        parser.error(f"{target.relative_to(ROOT)} already exists")
    if args.game > 1 and not (target_dir / f"Game_{args.game - 1}.md").is_file():
        parser.error("game numbers must be sequential within their owning folder")
    target_dir.mkdir(parents=True, exist_ok=True)
    target.write_text(game_text(title,args.status,args.date,args.opponent,args.venue,args.reason,play_in_game_1,kind,cup_stage), encoding="utf-8")
    refreshed = refresh_career_views(ROOT)
    print(target.relative_to(ROOT))
    print(f"Updated {len(refreshed)} detailed career views.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
