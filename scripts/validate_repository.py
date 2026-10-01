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


def require(errors, condition, message):
    if not condition:
        errors.append(message)


def front_matter(path):
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


def discover():
    career = ROOT / "career"
    players = [p for p in career.iterdir() if p.is_dir()]
    if len(players) != 1:
        raise ValueError("career must contain exactly one player directory")
    years = [p for p in players[0].iterdir() if p.is_dir()]
    if len(years) != 1:
        raise ValueError("player directory must contain exactly one active season directory")
    return players[0], years[0]


def validate_game(path, errors, play_in_game_1=False):
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


def validate_sequence(folder, errors, maximum=None):
    nums = sorted(int(m.group(1)) for path in folder.glob("Game_*.md") if (m := GAME_RE.match(path.name)))
    if maximum is not None:
        require(errors, all(n <= maximum for n in nums), f"{folder.relative_to(ROOT)}: game number exceeds {maximum}")
    if nums:
        require(errors, nums == list(range(1,max(nums)+1)), f"{folder.relative_to(ROOT)}: game files must be sequential without gaps")


def validate():
    errors=[]
    try:
        config=json.loads((ROOT/"foundation/season_structure.json").read_text(encoding="utf-8"))
        player,season=discover()
    except (OSError,ValueError,json.JSONDecodeError) as exc:
        return [f"cannot load required structure: {exc}"]

    require(errors, player.name == "Dwyane_Wade", "active player directory must be Dwyane_Wade")
    require(errors, season.name == "2003-04", "active season directory must be 2003-04")
    require(errors, (player/"Dwyane Wade: Player Profile.md").is_file(), "missing Dwyane Wade player profile")

    state_path=season/"current_state.json"
    require(errors,state_path.is_file(),"missing season current state")
    if state_path.is_file():
        try:
            state=json.loads(state_path.read_text(encoding="utf-8"))
            require(errors,state.get("initialized") is True,"career must be initialized")
            require(errors,state.get("season")=="2003-04","current state season mismatch")
            require(errors,state.get("current_date")=="2003-06-26","current checkpoint date mismatch")
            require(errors,state.get("team")=="Miami Heat","current team mismatch")
        except json.JSONDecodeError as exc:
            errors.append(f"current_state.json invalid: {exc}")

    team=season/"00_Team"
    required_team_files=(
        "team_config.json",
        "Organization/organization.json",
        "Organization/Micky_Arison.md",
        "Organization/Pat_Riley.md",
        "Organization/Randy_Pfund.md",
        "Organization/Andy_Elisburg.md",
        "Organization/Chet_Kammerer.md",
        "Team/Roster/roster.json",
        "Team/Depth_Chart/depth_chart.json",
        "Team/Depth_Chart/depth_chart.md",
        "Team/Player_Cards/TEMPLATE.md",
        "Finances/finance.json",
        "Finances/cap_tracker.md",
        "Finances/contract_schedules.json",
        "Finances/league_cap_history.json",
    )
    for rel in required_team_files:
        require(errors,(team/rel).is_file(),f"missing AI/GM team file: 00_Team/{rel}")

    for rel in ("team_config.json","Organization/organization.json","Team/Roster/roster.json","Team/Depth_Chart/depth_chart.json","Finances/finance.json"):
        path=team/rel
        if path.is_file():
            try:
                data=json.loads(path.read_text(encoding="utf-8"))
                require(errors,data.get("owner")=="ai_gm",f"{path.relative_to(ROOT)} must be AI/GM-owned")
            except json.JSONDecodeError as exc:
                errors.append(f"{path.relative_to(ROOT)}: invalid JSON: {exc}")

    roster_path=team/"Team/Roster/roster.json"
    if roster_path.is_file():
        roster=json.loads(roster_path.read_text(encoding="utf-8"))
        players=roster.get("players",[])
        ids=[p.get("id") for p in players]
        require(errors,len(ids)==len(set(ids)),"roster player ids must be unique")
        require(errors,{"dwyane_wade","jerome_beasley"} <= set(ids),"draft picks missing from roster/control register")
        for p in players:
            card=team/"Team/Player_Cards"/f"{p.get('id')}.md"
            require(errors,card.is_file(),f"missing player card for {p.get('name')}")

    finance_path=team/"Finances/finance.json"
    if finance_path.is_file():
        finance=json.loads(finance_path.read_text(encoding="utf-8"))
        require(errors,finance.get("as_of")=="2003-06-26","finance snapshot date mismatch")
        require(errors,finance.get("cap_room") is None,"June 26 cap room must remain unresolved")
        pending={x.get("player"):x for x in finance.get("pending_control_items",[])}
        require(errors,pending.get("Anthony Carter",{}).get("status")=="pending","Anthony Carter option must still be pending on June 26")
        require(errors,finance.get("live_official_salary_cap") is None,"June 26 live official cap must remain unpublished")
        require(errors,finance.get("historical_actual_salary_cap")==43840000,"2003-04 historical actual cap must be $43.84M")
        require(errors,finance.get("known_counted_salary_before_free_agent_holds")==28466078,"known June 26 counted baseline changed")

    history_path=team/"Finances/league_cap_history.json"
    if history_path.is_file():
        history=json.loads(history_path.read_text(encoding="utf-8"))
        expected_caps={
            "2003-04":43840000,
            "2004-05":43870000,
            "2005-06":49500000,
            "2006-07":53135000,
            "2007-08":55630000,
            "2008-09":58680000,
        }
        actual={row.get("season"):row.get("salary_cap") for row in history.get("seasons",[])}
        require(errors,actual==expected_caps,"six-season historical cap reference changed")

    schedules_path=team/"Finances/contract_schedules.json"
    if schedules_path.is_file():
        schedules=json.loads(schedules_path.read_text(encoding="utf-8"))
        require(errors,schedules.get("known_baseline",{}).get("2003-04")==28466078,"contract schedule baseline mismatch")
        wade=next((x for x in schedules.get("players",[]) if x.get("player")=="Dwyane Wade"),{})
        require(errors,wade.get("current_cap_hold")==2197000,"Wade unsigned rookie-scale cap hold must be $2.197M")

    require(errors, config.get("week_definition") == {"1":"1-7","2":"8-14","3":"15-21","4":"22-end"}, "week definition changed")
    require(errors, month_week(1)==1 and month_week(7)==1, "Week 1 rule failed")
    require(errors, month_week(8)==2 and month_week(14)==2, "Week 2 rule failed")
    require(errors, month_week(15)==3 and month_week(21)==3, "Week 3 rule failed")
    require(errors, month_week(22)==4 and month_week(31)==4, "Week 4 rule failed")

    for area in config["areas"]:
        folder=season/area["folder"]
        require(errors,folder.is_dir(),f"missing season area: {area['folder']}")
        if area["order"] in {1,2,3,4,5,9}:
            note=folder/"note.md"
            require(errors,note.is_file(),f"missing phase note: {note.relative_to(ROOT)}")
            if note.is_file():
                try:
                    data=front_matter(note)
                    require(errors,data.get("type")=="phase",f"{note.relative_to(ROOT)}: wrong type")
                    require(errors,data.get("status") in NOTE_STATUSES,f"{note.relative_to(ROOT)}: bad status")
                except ValueError as exc:
                    errors.append(f"{note.relative_to(ROOT)}: {exc}")

    regular=season/"06_Regular_Season"
    day_ranges={1:"1-7",2:"8-14",3:"15-21",4:"22-end"}
    for month,spec in config["regular_season"].items():
        mdir=regular/spec["folder"]
        for week in spec["weeks"]:
            wdir=mdir/f"Week_{week}"
            note=wdir/"note.md"
            require(errors,note.is_file(),f"missing week note: {note.relative_to(ROOT)}")
            if note.is_file():
                try:
                    data=front_matter(note)
                    require(errors,data.get("type")=="regular_season_week",f"{note.relative_to(ROOT)}: wrong type")
                    require(errors,data.get("status") in NOTE_STATUSES,f"{note.relative_to(ROOT)}: bad status")
                    require(errors,data.get("month")==month,f"{note.relative_to(ROOT)}: month mismatch")
                    require(errors,data.get("week")==str(week),f"{note.relative_to(ROOT)}: week mismatch")
                    require(errors,data.get("days")==day_ranges[week],f"{note.relative_to(ROOT)}: days mismatch")
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
        validate_sequence(rdir,errors,7)
        for game in rdir.glob("Game_*.md"):
            validate_game(game,errors)

    return errors


def main():
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
