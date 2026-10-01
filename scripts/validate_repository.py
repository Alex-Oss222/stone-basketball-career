#!/usr/bin/env python3
"""Read-only continuity validation for the player-career repository."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.season_rules import month_week

NOTE_STATUSES = {"not_started","active","complete"}
GAME_STATUSES = {"scheduled","played","not_played"}
GAME_RE = re.compile(r"^Game_(\d+)\.md$")


def require(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def front_matter(path: Path) -> dict[str,str]:
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError("empty file")
    if not text.startswith("---\n"):
        raise ValueError("missing front matter")
    parts = text.split("---\n",2)
    if len(parts) < 3:
        raise ValueError("unterminated front matter")
    data = {}
    for line in parts[1].splitlines():
        if ":" in line:
            k,v = line.split(":",1)
            data[k.strip()] = v.strip()
    return data


def discover() -> tuple[Path,Path]:
    career = ROOT / "career"
    players = [p for p in career.iterdir() if p.is_dir()]
    if len(players) != 1:
        raise ValueError("career must contain exactly one player directory")
    years = [p for p in players[0].iterdir() if p.is_dir()]
    if len(years) != 1:
        raise ValueError("player directory must contain exactly one year directory in the empty skeleton")
    return players[0], years[0]


def validate_game(path: Path, errors: list[str], play_in_game_1: bool = False) -> dict[str,str] | None:
    try:
        data = front_matter(path)
    except ValueError as exc:
        errors.append(f"{path.relative_to(ROOT)}: {exc}")
        return None
    require(errors, data.get("type") == "game", f"{path.relative_to(ROOT)}: wrong type")
    status = data.get("status")
    require(errors, status in GAME_STATUSES, f"{path.relative_to(ROOT)}: invalid status")
    if status == "scheduled":
        require(errors, bool(data.get("date")), f"{path.relative_to(ROOT)}: scheduled game needs date")
        require(errors, bool(data.get("opponent")), f"{path.relative_to(ROOT)}: scheduled game needs opponent")
        require(errors, not data.get("result"), f"{path.relative_to(ROOT)}: scheduled game cannot have result")
    elif status == "played":
        require(errors, bool(data.get("date")), f"{path.relative_to(ROOT)}: played game needs date")
        require(errors, bool(data.get("opponent")), f"{path.relative_to(ROOT)}: played game needs opponent")
        require(errors, bool(data.get("result")), f"{path.relative_to(ROOT)}: played game needs result")
    elif status == "not_played":
        require(errors, bool(data.get("reason")), f"{path.relative_to(ROOT)}: not_played game needs reason")
        require(errors, not data.get("result"), f"{path.relative_to(ROOT)}: not_played game cannot have result")
    if play_in_game_1:
        require(errors, data.get("next_game_required") in {"true","false"}, f"{path.relative_to(ROOT)}: next_game_required must be true/false")
    return data


def validate_sequence(folder: Path, errors: list[str], maximum: int | None = None) -> None:
    nums = sorted(
        int(m.group(1))
        for path in folder.glob("Game_*.md")
        if (m := GAME_RE.match(path.name))
    )
    if maximum is not None:
        require(errors, all(n <= maximum for n in nums), f"{folder.relative_to(ROOT)}: game number exceeds {maximum}")
    if nums:
        require(errors, nums == list(range(1,max(nums)+1)), f"{folder.relative_to(ROOT)}: game files must be sequential without gaps")


def validate() -> list[str]:
    errors: list[str] = []
    try:
        config = json.loads((ROOT/"foundation/season_structure.json").read_text(encoding="utf-8"))
        player, season = discover()
    except (OSError,ValueError,json.JSONDecodeError) as exc:
        return [f"cannot load required structure: {exc}"]

    for root_name in ("01_Free_Agency","02_Summer_League","03_Offseason","04_Training_Camp","05_Preseason","06_Regular_Season","07_Play_In_Tournament","08_Playoffs","09_Draft"):
        require(errors, not (ROOT/root_name).exists(), f"season area must not live at repository root: {root_name}")

    require(errors, (player/"player_profile.md").is_file(), "missing career player profile")
    require(errors, (season/"current_state.json").is_file(), "missing season current state")

    team = season/"00_Team"
    for rel in ("team_config.json","Team/roster.json","Team/rotation.json","Team/Player_Cards/TEMPLATE.md","Finances/finance.json"):
        require(errors, (team/rel).is_file(), f"missing AI/GM team file: 00_Team/{rel}")

    for rel in ("team_config.json","Team/roster.json","Team/rotation.json","Finances/finance.json"):
        path = team/rel
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                require(errors, data.get("owner") == "ai_gm", f"{path.relative_to(ROOT)} must be AI/GM-owned")
            except json.JSONDecodeError as exc:
                errors.append(f"{path.relative_to(ROOT)}: invalid JSON: {exc}")

    try:
        state = json.loads((season/"current_state.json").read_text(encoding="utf-8"))
        require(errors, isinstance(state.get("pending_player_decisions"),list), "pending_player_decisions must be a list")
        if state.get("initialized") is False:
            for key in ("season","current_date","current_area","current_note","team","last_closed_event"):
                require(errors, state.get(key) is None, f"{key} must be null before initialization")
    except json.JSONDecodeError as exc:
        errors.append(f"current_state.json invalid: {exc}")

    require(errors, config.get("nesting") == "career/<player>/<year>", "career nesting config changed")
    require(errors, config.get("team_owner") == "ai_gm", "team ownership config changed")
    require(errors, config.get("week_definition") == {"1":"1-7","2":"8-14","3":"15-21","4":"22-end"}, "week definition changed")
    require(errors, month_week(1)==1 and month_week(7)==1, "Week 1 rule failed")
    require(errors, month_week(8)==2 and month_week(14)==2, "Week 2 rule failed")
    require(errors, month_week(15)==3 and month_week(21)==3, "Week 3 rule failed")
    require(errors, month_week(22)==4 and month_week(31)==4, "Week 4 rule failed")

    for area in config["areas"]:
        folder = season/area["folder"]
        require(errors, folder.is_dir(), f"missing season area: {area['folder']}")
        require(errors, (folder/"README.md").is_file(), f"missing README: {area['folder']}")
        if area["order"] in {1,2,3,4,5,9}:
            note = folder/"note.md"
            require(errors, note.is_file(), f"missing phase note: {note.relative_to(ROOT)}")
            if note.is_file():
                try:
                    data = front_matter(note)
                    require(errors, data.get("type")=="phase", f"{note.relative_to(ROOT)}: wrong type")
                    require(errors, data.get("status") in NOTE_STATUSES, f"{note.relative_to(ROOT)}: bad status")
                except ValueError as exc:
                    errors.append(f"{note.relative_to(ROOT)}: {exc}")

    regular = season/"06_Regular_Season"
    day_ranges={1:"1-7",2:"8-14",3:"15-21",4:"22-end"}
    for month,spec in config["regular_season"].items():
        mdir=regular/spec["folder"]
        require(errors, mdir.is_dir(), f"missing month: {month}")
        for week in spec["weeks"]:
            wdir=mdir/f"Week_{week}"
            note=wdir/"note.md"
            require(errors, note.is_file(), f"missing week note: {note.relative_to(ROOT)}")
            if note.is_file():
                try:
                    data=front_matter(note)
                    require(errors, data.get("type")=="regular_season_week", f"{note.relative_to(ROOT)}: wrong type")
                    require(errors, data.get("status") in NOTE_STATUSES, f"{note.relative_to(ROOT)}: bad status")
                    require(errors, data.get("month")==month, f"{note.relative_to(ROOT)}: month mismatch")
                    require(errors, data.get("week")==str(week), f"{note.relative_to(ROOT)}: week mismatch")
                    require(errors, data.get("days")==day_ranges[week], f"{note.relative_to(ROOT)}: days mismatch")
                except ValueError as exc:
                    errors.append(f"{note.relative_to(ROOT)}: {exc}")
            validate_sequence(wdir,errors)
            for game in wdir.glob("Game_*.md"):
                validate_game(game,errors)

    playin=season/"07_Play_In_Tournament"
    validate_sequence(playin,errors,2)
    g1=playin/"Game_1.md"
    g2=playin/"Game_2.md"
    g1meta=validate_game(g1,errors,True) if g1.exists() else None
    if g2.exists():
        validate_game(g2,errors)
        require(errors,g1meta is not None,"Play-In Game 2 exists without Game 1")
        if g1meta is not None:
            require(errors,g1meta.get("status")=="played","Play-In Game 2 requires played Game 1")
            require(errors,g1meta.get("next_game_required")=="true","Play-In Game 2 requires next_game_required: true")

    playoffs=season/"08_Playoffs"
    for rnd in config["playoffs"]["rounds"]:
        rdir=playoffs/rnd["folder"]
        require(errors,rdir.is_dir(),f"missing playoff round: {rnd['folder']}")
        validate_sequence(rdir,errors,7)
        for game in rdir.glob("Game_*.md"):
            validate_game(game,errors)

    return errors


def main() -> int:
    errors=validate()
    if errors:
        print("Repository validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Repository validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
