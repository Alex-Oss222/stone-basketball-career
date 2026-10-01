#!/usr/bin/env python3
"""Create a non-ambiguous play-in or playoff game note."""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def parse_meta(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{path}: missing front matter")
    block = text.split("---\n", 2)[1]
    data = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip()
    return data


def game_text(title: str, status: str, date: str, opponent: str, venue: str, reason: str, play_in: bool) -> str:
    next_required = "false" if play_in else ""
    return f"""---
type: game
status: {status}
date: {date}
opponent: {opponent}
venue: {venue}
result:
reason: {reason}
next_game_required: {next_required}
---

# {title}

## Pre-game

## Player decisions

## Result

## Consequences
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--area", choices=("play-in", "playoffs"), required=True)
    parser.add_argument("--round", choices=("First_Round", "Conference_Semifinals", "Conference_Finals", "Finals"))
    parser.add_argument("--game", type=int, required=True)
    parser.add_argument("--status", choices=("scheduled", "not_played"), required=True)
    parser.add_argument("--date", default="")
    parser.add_argument("--opponent", default="")
    parser.add_argument("--venue", default="")
    parser.add_argument("--reason", default="")
    args = parser.parse_args()

    if args.area == "play-in":
        if args.round:
            parser.error("--round is not used for play-in")
        if args.game not in (1, 2):
            parser.error("play-in game must be 1 or 2")
        target_dir = ROOT / "07_Play_In_Tournament"
        if args.game == 2:
            game1 = target_dir / "Game_1.md"
            if not game1.exists():
                parser.error("Game 2 requires an existing Game 1 record")
            meta = parse_meta(game1)
            if meta.get("status") != "played" or meta.get("next_game_required") != "true":
                parser.error("Game 2 requires played Game 1 with next_game_required: true")
        title = f"Play-In Game {args.game}"
        play_in = True
    else:
        if not args.round:
            parser.error("--round is required for playoffs")
        if args.game < 1 or args.game > 7:
            parser.error("playoff game must be between 1 and 7")
        target_dir = ROOT / "08_Playoffs" / args.round
        title = f"{args.round.replace('_', ' ')} Game {args.game}"
        play_in = False

    if args.status == "scheduled" and (not args.date or not args.opponent):
        parser.error("scheduled games require --date and --opponent")
    if args.status == "not_played" and not args.reason:
        parser.error("not_played games require --reason")

    target = target_dir / f"Game_{args.game}.md"
    if target.exists():
        parser.error(f"{target.relative_to(ROOT)} already exists")
    target.write_text(
        game_text(title, args.status, args.date, args.opponent, args.venue, args.reason, play_in),
        encoding="utf-8",
    )
    print(target.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
