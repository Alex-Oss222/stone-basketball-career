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
from runtime.player_stats import repository_rating_errors

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
    years = [p for p in players[0].iterdir() if p.is_dir() and re.fullmatch(r"\d{4}-\d{2}", p.name)]
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
    errors=repository_rating_errors(ROOT)
    try:
        config=json.loads((ROOT/"foundation/season_structure.json").read_text(encoding="utf-8"))
        player,season=discover()
    except (OSError,ValueError,json.JSONDecodeError) as exc:
        return [f"cannot load required structure: {exc}"]

    require(errors, player.name == "Dwyane_Wade", "active player directory must be Dwyane_Wade")
    require(errors, season.name == "2003-04", "active season directory must be 2003-04")
    require(errors, (player/"Dwyane_Wade_Player_Profile.md").is_file(), "missing Dwyane Wade player profile")

    league_dir=ROOT/"library/2003/league"
    draft_library=league_dir/"nba_2003_draft_class.json"
    end_library=league_dir/"nba_2003_end_of_season.json"
    require(errors,draft_library.is_file(),"missing 2003 draft-class league source")
    require(errors,end_library.is_file(),"missing 2003 end-of-season league source")
    require(errors,not (season/"nba_2003_draft_class.json").exists(),"league draft source must not live in season root")
    require(errors,not (season/"nba_2003_end_of_season.json").exists(),"league roster source must not live in season root")
    for source_path, expected_as_of, expected_clubs, expected_players in (
        (draft_library,"2003 NBA draft (June 26, 2003), after draft-night trades",27,58),
        (end_library,"end of 2002-03 season (each club's final game)",29,350),
    ):
        if source_path.is_file():
            try:
                source=json.loads(source_path.read_text(encoding="utf-8"))
                require(errors,source.get("league")=="NBA",f"{source_path.relative_to(ROOT)}: league must be NBA")
                require(errors,source.get("season")==2003,f"{source_path.relative_to(ROOT)}: season must be 2003")
                require(errors,source.get("as_of")==expected_as_of,f"{source_path.relative_to(ROOT)}: as_of mismatch")
                clubs=source.get("clubs")
                require(errors,isinstance(clubs,dict) and len(clubs)==expected_clubs,f"{source_path.relative_to(ROOT)}: club count mismatch")
                if isinstance(clubs,dict):
                    player_count=sum(len(club.get("players",[])) for club in clubs.values() if isinstance(club,dict))
                    require(errors,player_count==expected_players,f"{source_path.relative_to(ROOT)}: player count mismatch")
            except json.JSONDecodeError as exc:
                errors.append(f"{source_path.relative_to(ROOT)}: invalid JSON: {exc}")

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
        "Finances/cap_sheet.md",
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
        required_card_sections=[
            "## Scouting report",
            "## Player grades",
            "## Changes and coaching notes",
            "## Sources and uncertainty",
            "## Regular-season statistics by year",
            "## Playoff statistics by year",
            "## Awards and honors",
        ]
        for p in players:
            card=team/"Team/Player_Cards"/f"{p.get('id')}.md"
            require(errors,card.is_file(),f"missing player card for {p.get('name')}")
            if card.is_file():
                text=card.read_text(encoding="utf-8")
                positions=[text.find(section) for section in required_card_sections]
                require(errors,all(pos >= 0 for pos in positions),f"{card.relative_to(ROOT)}: missing canonical template section")
                if all(pos >= 0 for pos in positions):
                    require(errors,positions==sorted(positions),f"{card.relative_to(ROOT)}: template section order changed")
                    require(errors,re.findall(r"^## .+$",text,re.M)[-3:]==required_card_sections[-3:],f"{card.relative_to(ROOT)}: regular-season stats, playoffs and awards must remain the final sections")

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

    cap_sheet_path=team/"Finances/cap_sheet.md"
    if cap_sheet_path.is_file():
        cap_sheet=cap_sheet_path.read_text(encoding="utf-8")
        for heading in ("## Current cap position","## Active contracts","## Options and draft holds","## Free-agent holds still to reconcile","## Six-year summary"):
            require(errors,heading in cap_sheet,f"Finances/cap_sheet.md missing {heading}")
        require(errors,"2003-04" in cap_sheet and "2008-09" in cap_sheet,"cap sheet must show the six-year window")

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

    stats_root=player/"Stats_and_Awards"
    stats_year=stats_root/season.name
    require(errors,(stats_root/"README.md").is_file(),"missing Stats_and_Awards index")
    require(errors,(stats_year/"README.md").is_file(),"missing yearly stats and awards page")
    for month,spec in config["regular_season"].items():
        month_dir=stats_year/spec["folder"]
        require(errors,(month_dir/"README.md").is_file(),f"missing monthly stats page: {month}")
        for week in spec["weeks"]:
            require(errors,(month_dir/f"Week_{week}"/"README.md").is_file(),f"missing weekly stats page: {month} Week {week}")

    league_stats_root=player/"Stats_and_Awards"/"League"
    league_registry=league_stats_root/"player_registry.json"
    require(errors,league_registry.is_file(),"missing league player registry")
    if league_registry.is_file():
        registry=json.loads(league_registry.read_text(encoding="utf-8"))
        require(errors,registry.get("player_count")==407,"league player registry count changed")
        positions=[p.get("position") for p in registry.get("players",[])]
        require(errors,all(pos in {"PG","SG","SF","F","PF","C"} for pos in positions),"league registry has unsupported position")
    league_year=league_stats_root/season.name
    require(errors,(league_year/"League_Stats.md").is_file(),"missing yearly league stats page")
    require(errors,(league_year/"League_Awards.md").is_file(),"missing yearly league awards page")
    for month,spec in config["regular_season"].items():
        league_month=league_year/spec["folder"]
        require(errors,(league_month/"League_Stats.md").is_file(),f"missing monthly league stats page: {month}")
        require(errors,(league_month/"League_Awards.md").is_file(),f"missing monthly league awards page: {month}")
        for week in spec["weeks"]:
            league_week=league_month/f"Week_{week}"
            require(errors,(league_week/"League_Stats.md").is_file(),f"missing weekly league stats page: {month} Week {week}")
            require(errors,(league_week/"League_Awards.md").is_file(),f"missing weekly league awards page: {month} Week {week}")

    team_stats_root=player/"Stats_and_Awards"/"Team"
    team_stats_year=team_stats_root/season.name
    require(errors,(team_stats_root/"README.md").is_file(),"missing Team stats index")
    require(errors,(team_stats_year/"Team_Stats.md").is_file(),"missing yearly team stats page")
    for month,spec in config["regular_season"].items():
        team_month=team_stats_year/spec["folder"]
        require(errors,(team_month/"Team_Stats.md").is_file(),f"missing monthly team stats page: {month}")
        for week in spec["weeks"]:
            team_week=team_month/f"Week_{week}"
            require(errors,(team_week/"Team_Stats.md").is_file(),f"missing weekly team stats page: {month} Week {week}")

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

    from runtime.prospects import rookie_errors
    errors.extend(rookie_errors(ROOT))

    from runtime.schedule import schedule_errors
    errors.extend(schedule_errors(ROOT))

    from runtime.game_requests import find_requests, request_errors
    errors.extend(request_errors(ROOT))
    for request in find_requests(ROOT):
        note=request.with_name(request.name.replace(".request.json",".md"))
        require(errors,note.is_file(),f"{request.relative_to(ROOT)}: no matching game note {note.name}")

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
