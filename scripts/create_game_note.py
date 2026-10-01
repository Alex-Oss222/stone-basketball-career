#!/usr/bin/env python3
"""Create a scheduled or explicit not-played game record."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def season_dir() -> Path:
    career = ROOT / "career"
    players = [p for p in career.iterdir() if p.is_dir()]
    if len(players) != 1:
        raise SystemExit("expected exactly one player directory under career")
    years = [p for p in players[0].iterdir() if p.is_dir()]
    if len(years) != 1:
        raise SystemExit("expected exactly one year directory under the player")
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


def game_text(title: str, status: str, date: str, opponent: str, venue: str, reason: str, play_in_game_1: bool) -> str:
    next_line = "next_game_required: false\n" if play_in_game_1 else ""
    return f"""---
type: game
status: {status}
date: {date}
opponent: {opponent}
venue: {venue}
result:
reason: {reason}
simulation_source:
{next_line}---

# {title}

## Pre-game

## Player decisions

## Result

## Consequences
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--area", choices=("regular", "play-in", "playoffs"), required=True)
    parser.add_argument("--month", choices=("October","November","December","January","February","March","April"))
    parser.add_argument("--week", type=int)
    parser.add_argument("--round", choices=("First_Round","Conference_Semifinals","Conference_Finals","Finals"))
    parser.add_argument("--game", type=int, required=True)
    parser.add_argument("--status", choices=("scheduled","not_played"), required=True)
    parser.add_argument("--date", default="")
    parser.add_argument("--opponent", default="")
    parser.add_argument("--venue", default="")
    parser.add_argument("--reason", default="")
    args = parser.parse_args()

    season = season_dir()
    play_in_game_1 = False

    if args.status == "scheduled" and (not args.date or not args.opponent):
        parser.error("scheduled games require --date and --opponent")
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
        if not target_dir.is_dir():
            parser.error("requested month/week does not exist in the season structure")
        if args.game < 1:
            parser.error("regular-season game number must be positive")
        title = f"{args.month} Week {args.week} Game {args.game}"
    elif args.area == "play-in":
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
    else:
        if args.round is None:
            parser.error("playoff games require --round")
        if args.game < 1 or args.game > 7:
            parser.error("playoff game must be 1 through 7")
        target_dir = season / "08_Playoffs" / args.round
        title = f"{args.round.replace('_',' ')} Game {args.game}"

    target = target_dir / f"Game_{args.game}.md"
    if target.exists():
        parser.error(f"{target.relative_to(ROOT)} already exists")
    target.write_text(game_text(title,args.status,args.date,args.opponent,args.venue,args.reason,play_in_game_1), encoding="utf-8")
    print(target.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
