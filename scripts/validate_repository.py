#!/usr/bin/env python3
"""Read-only repository continuity checks."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.season_rules import month_week

NOTE_STATUSES = {"not_started", "active", "complete"}
GAME_STATUSES = {"scheduled", "played", "not_played"}
GAME_RE = re.compile(r"^Game_([1-7])\.md$")


def meta(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError("file is empty")
    if not text.startswith("---\n"):
        raise ValueError("missing front matter")
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        raise ValueError("unterminated front matter")
    data = {}
    for line in parts[1].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip()
    return data


def require(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def validate_regular_season(config: dict, errors: list[str]) -> None:
    base = ROOT / "06_Regular_Season"
    day_ranges = {1: "1-7", 2: "8-14", 3: "15-21", 4: "22-end"}
    for month, spec in config["regular_season"].items():
        month_dir = base / spec["folder"]
        require(errors, month_dir.is_dir(), f"missing month folder: {month_dir.relative_to(ROOT)}")
        for week in spec["weeks"]:
            path = month_dir / f"Week_{week}" / "note.md"
            require(errors, path.is_file(), f"missing week note: {path.relative_to(ROOT)}")
            if not path.is_file():
                continue
            try:
                data = meta(path)
                require(errors, data.get("type") == "regular_season_week", f"{path}: wrong type")
                require(errors, data.get("status") in NOTE_STATUSES, f"{path}: invalid status")
                require(errors, data.get("month") == month, f"{path}: month metadata mismatch")
                require(errors, data.get("week") == str(week), f"{path}: week metadata mismatch")
                require(errors, data.get("days") == day_ranges[week], f"{path}: day range mismatch")
            except ValueError as exc:
                errors.append(f"{path.relative_to(ROOT)}: {exc}")


def validate_phase_notes(config: dict, errors: list[str]) -> None:
    for area in config["areas"]:
        folder = ROOT / area["folder"]
        require(errors, folder.is_dir(), f"missing area folder: {area['folder']}")
        require(errors, (folder / "README.md").is_file(), f"missing area README: {area['folder']}/README.md")
        if area["order"] in {1, 2, 3, 4, 5, 9}:
            note = folder / "note.md"
            require(errors, note.is_file(), f"missing phase note: {note.relative_to(ROOT)}")
            if note.is_file():
                try:
                    data = meta(note)
                    require(errors, data.get("type") == "phase", f"{note}: wrong type")
                    require(errors, data.get("status") in NOTE_STATUSES, f"{note}: invalid status")
                except ValueError as exc:
                    errors.append(f"{note.relative_to(ROOT)}: {exc}")


def validate_game(path: Path, errors: list[str], play_in: bool) -> dict[str, str] | None:
    try:
        data = meta(path)
    except ValueError as exc:
        errors.append(f"{path.relative_to(ROOT)}: {exc}")
        return None
    require(errors, data.get("type") == "game", f"{path}: wrong type")
    status = data.get("status")
    require(errors, status in GAME_STATUSES, f"{path}: invalid game status")
    if status == "scheduled":
        require(errors, bool(data.get("date")), f"{path}: scheduled game needs date")
        require(errors, bool(data.get("opponent")), f"{path}: scheduled game needs opponent")
        require(errors, not data.get("result"), f"{path}: scheduled game cannot already have a result")
    elif status == "played":
        require(errors, bool(data.get("date")), f"{path}: played game needs date")
        require(errors, bool(data.get("opponent")), f"{path}: played game needs opponent")
        require(errors, bool(data.get("result")), f"{path}: played game needs result")
    elif status == "not_played":
        require(errors, bool(data.get("reason")), f"{path}: not_played game needs reason")
        require(errors, not data.get("result"), f"{path}: not_played game cannot have result")
    if play_in and path.name == "Game_1.md":
        require(errors, data.get("next_game_required") in {"true", "false"}, f"{path}: Game 1 needs next_game_required true/false")
    return data


def validate_postseason(config: dict, errors: list[str]) -> None:
    play_in_dir = ROOT / "07_Play_In_Tournament"
    game1 = play_in_dir / "Game_1.md"
    game2 = play_in_dir / "Game_2.md"
    game1_meta = validate_game(game1, errors, True) if game1.exists() else None
    if game2.exists():
        validate_game(game2, errors, True)
        require(errors, game1_meta is not None, "Play-In Game 2 exists without Game 1")
        if game1_meta is not None:
            require(errors, game1_meta.get("status") == "played", "Play-In Game 2 requires played Game 1")
            require(errors, game1_meta.get("next_game_required") == "true", "Play-In Game 2 requires next_game_required: true")

    playoff_root = ROOT / "08_Playoffs"
    allowed_rounds = {r["folder"] for r in config["playoffs"]["rounds"]}
    for round_spec in config["playoffs"]["rounds"]:
        round_dir = playoff_root / round_spec["folder"]
        require(errors, round_dir.is_dir(), f"missing playoff round: {round_dir.relative_to(ROOT)}")
        require(errors, (round_dir / "README.md").is_file(), f"missing playoff README: {round_dir.relative_to(ROOT)}/README.md")
        if not round_dir.is_dir():
            continue
        for path in round_dir.iterdir():
            match = GAME_RE.match(path.name)
            if not match:
                continue
            number = int(match.group(1))
            require(errors, 1 <= number <= 7, f"{path}: invalid game number")
            validate_game(path, errors, False)

    for path in playoff_root.iterdir():
        if path.is_dir():
            require(errors, path.name in allowed_rounds, f"unexpected playoff round folder: {path.name}")


def validate_state(errors: list[str]) -> None:
    state_path = ROOT / "state/career_state.json"
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"invalid career state: {exc}")
        return
    required = {
        "schema_version", "active_season", "current_date", "current_area",
        "current_note", "team", "contract_status", "roster_status",
        "last_closed_event", "pending_player_decisions"
    }
    require(errors, required <= set(state), "career_state.json is missing required fields")
    if state.get("active_season") is None:
        for key in ("current_date", "current_area", "current_note", "team", "last_closed_event"):
            require(errors, state.get(key) is None, f"{key} must stay null while active_season is null")
    require(errors, isinstance(state.get("pending_player_decisions"), list), "pending_player_decisions must be a list")


def validate() -> list[str]:
    errors: list[str] = []
    try:
        config = json.loads((ROOT / "config/season_structure.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot read season structure: {exc}"]

    require(errors, config.get("week_definition") == {"1":"1-7","2":"8-14","3":"15-21","4":"22-end"}, "week definition changed")
    require(errors, month_week(1) == 1 and month_week(7) == 1, "Week 1 rule failed")
    require(errors, month_week(8) == 2 and month_week(14) == 2, "Week 2 rule failed")
    require(errors, month_week(15) == 3 and month_week(21) == 3, "Week 3 rule failed")
    require(errors, month_week(22) == 4 and month_week(31) == 4, "Week 4 rule failed")

    for path in (
        "README.md", "AGENTS.md", "foundation/01_Project_Instructions.md",
        "docs/season_structure.md", "docs/update_workflow.md",
        "state/career_state.json", "state/player_profile.md",
        "templates/phase-note.md", "templates/week-note.md", "templates/game-note.md"
    ):
        require(errors, (ROOT / path).is_file(), f"missing required file: {path}")

    validate_phase_notes(config, errors)
    validate_regular_season(config, errors)
    validate_postseason(config, errors)
    validate_state(errors)
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("Repository validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Repository validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
