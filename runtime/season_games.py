"""Regular-season game builders (roadmap items 10 and 11).

Miami (item 10): for every Miami regular-season game in the season schedule
dated on or before the run date and not yet written, the game note
`06_Regular_Season/<month>/Week_N/Game_N.md` (the `scripts/create_game_note.py`
record with the engine fields filled: status scheduled, competition regular,
event_id, result_file) and the request `Game_N.request.json` next to it, in the
format `runtime/game_requests.py` documents. Miami's side is the explicit
`players` list from the dated staff rotation (camp's `rotation.json`, then
`Depth_Chart/Reviews/<date>/rotation.json`), with 240 minutes in rotation order;
players the engine's injury draws keep out
(`runtime.injuries.injured_out` over Miami's closed results, in order) are left
out, the next man on the staff's depth chart takes the last rotation slot, and
the minutes are re-scaled to 240. Wade's `perimeter_defense` rating is carried
from `00_Team/Team/defensive_grades.json` while a grade is in force on the game
date. The opponent plays its real roster (`"rotation": "real"`).

League (item 11): every non-Miami regular-season game on or before the run date
gets a request under `Stats_and_Awards/League/<season>/Games/<game_id>.request.json`
(both clubs `"rotation": "real"`), so Railway plays the whole slate and
`scripts/collect_results.py` writes `<game_id>.result.json` beside it. These
are simulation records of the world (standings need all 1,189 games), never
player or team statistics pages.

Both builders write a game only on or before its date, never a blank
placeholder, and never touch a request that already exists (a played request
must not change). Everything read is dated on or before the run date.
"""
from datetime import date
import json
from pathlib import Path

from .injuries import injured_out
from .rosters import SIMULATED_CLUB
from .rotations import load_rosters
from .schedule import game_id as schedule_game_id, schedule_path
from .season_rules import month_week

ROOT = Path(__file__).resolve().parents[1]
SEASON = "2003-04"
MIAMI = SIMULATED_CLUB
PLAYER_DIR = Path("career/Dwyane_Wade")
MONTH_FOLDERS = {10: "10_October", 11: "11_November", 12: "12_December", 1: "01_January", 2: "02_February",
                 3: "03_March", 4: "04_April"}
GAME_DAY_ACTIVES = 12
SIMULATION_SOURCE = "Railway engine (runtime/private_service.py)"
SLATE_SAMPLE_EVERY = 25          # league slate: every 25th request (plus the first and last) gets the full engine check


def season_base(season=SEASON):
    return PLAYER_DIR / season


def regular_season_dir(season=SEASON):
    return season_base(season) / "06_Regular_Season"


def slate_dir(season=SEASON):
    return PLAYER_DIR / "Stats_and_Awards/League" / season / "Games"


def is_league_slate(path):
    """A request under the league slate folder (no game note of its own)."""
    parts = Path(path).parts
    return "Stats_and_Awards" in parts and "Games" in parts and Path(path).name.endswith(".request.json")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def season_games(season=SEASON, root=ROOT):
    """The season's regular-season schedule, in date order."""
    games = read_json(schedule_path(season, root))["games"]
    return sorted(games, key=lambda g: (g["date"], g["game_id"]))


def check_date(value):
    try:
        date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError(f"run date must be YYYY-MM-DD, not {value!r}")
    return value


# -- game notes ----------------------------------------------------------------------------------
def note_meta(path):
    text = Path(path).read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{path}: missing front matter")
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        raise ValueError(f"{path}: unterminated front matter")
    data = {}
    for line in parts[1].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()
    return data


def week_dir(day, season=SEASON):
    """The season folder that owns a regular-season date."""
    d = date.fromisoformat(day)
    if d.month not in MONTH_FOLDERS:
        raise ValueError(f"{day} is outside the regular-season calendar")
    return regular_season_dir(season) / MONTH_FOLDERS[d.month] / f"Week_{month_week(d.day)}"


def month_name(day):
    return date.fromisoformat(day).strftime("%B")


def game_note(number, game, venue, season=SEASON):
    """The scheduled game note, as scripts/create_game_note.py writes it, with the engine fields filled."""
    opponent = game["away"] if venue == "home" else game["home"]
    title = f"{month_name(game['date'])} Week {month_week(date.fromisoformat(game['date']).day)} Game {number}"
    return f"""---
type: game
status: scheduled
date: {game['date']}
opponent: {opponent}
venue: {venue}
competition: regular
cup_stage:
player_team: {MIAMI}
result:
reason:
simulation_source: {SIMULATION_SOURCE}
event_id: {game['game_id']}
result_file: Game_{number}.result.json
---

# {title}

Player identity and statistics are generated here by `python scripts/update_player_reports.py`.
Decisions remain in the owning phase/week note. A scheduled game has no statistical result.
"""


def written_notes(root=ROOT, season=SEASON):
    """Every regular-season game note: event_id -> (path, number, date)."""
    out = {}
    for path in sorted((Path(root) / regular_season_dir(season)).rglob("Game_*.md")):
        if not path.stem.startswith("Game_") or not path.stem[5:].isdigit():
            continue
        meta = note_meta(path)
        key = meta.get("event_id") or f"{path}"
        out[key] = (path, int(path.stem[5:]), meta.get("date", ""))
    return out


def week_numbers(folder):
    """(existing game numbers, latest date) in a week folder."""
    numbers, latest = [], ""
    for path in Path(folder).glob("Game_*.md"):
        if path.stem[5:].isdigit():
            numbers.append(int(path.stem[5:]))
            latest = max(latest, note_meta(path).get("date", ""))
    return sorted(numbers), latest


# -- Miami's side --------------------------------------------------------------------------------
def miami_results(root=ROOT, season=SEASON):
    """Miami's closed results in order: preseason, then regular season, by game date.

    An injury drawn in the last preseason game keeps a player out of the first regular-season games,
    so both folders feed `injured_out`."""
    base = Path(root) / season_base(season)
    results = []
    for folder in ("05_Preseason", "06_Regular_Season"):
        for path in (base / folder).rglob("Game_*.result.json"):
            data = read_json(path)
            if MIAMI in (data.get("home"), data.get("away")):
                results.append((data.get("game_date", ""), str(path), data))
    return [data for _, _, data in sorted(results, key=lambda r: (r[0], r[1]))]


def miami_game_dates(root=ROOT, season=SEASON):
    """Every Miami game date on the season's calendars (preseason and regular season)."""
    from .camp import PRESEASON_SCHEDULE
    dates = [g["date"] for g in season_games(season, root) if MIAMI in (g["home"], g["away"])]
    preseason = Path(root) / PRESEASON_SCHEDULE
    if preseason.exists():
        dates += [g["date"] for g in read_json(preseason)["games"] if MIAMI in (g["home"], g["away"])]
    return sorted(dates)


def grades_in_force(game_date, root=ROOT, season=SEASON):
    """Player -> perimeter-defense grade from the staff's dated grades in force on the game date."""
    path = Path(root) / season_base(season) / "00_Team/Team/defensive_grades.json"
    if not path.exists():
        return {}
    return {g["player"]: g["grade"] for g in read_json(path)["players"]
            if g.get("from") and g["from"] <= game_date and g.get("grade") is not None}


def depth_order(depth, roster):
    """Roster entries in depth-chart order (position by position), for the next man up."""
    by_name = {p["name"]: p for p in roster["players"]}
    out = []
    for pos, names in depth.get("positions", {}).items():
        for name in names:
            if name in by_name and name not in [p["name"] for p in out]:
                entry = dict(by_name[name])
                entry["depth_position"] = pos
                out.append(entry)
    return out


def rotation_for(rotation, injured, grades, replacements=(), unavailable=()):
    """Miami's players and actual starters from the staff rotation.

    Injured players (`injured`: player -> games still out) leave the list; for each, the next man on
    the depth chart who is not in the rotation and not injured takes the last rotation slot's minutes
    (the staff's standing rule, judgement); the remaining minutes are re-scaled to 240 in order.
    An injured starter's job passes to the next healthy player at that position,
    including a reserve already in the rotation. Every request explicitly marks
    the five opening players; minutes and foul substitutions cannot erase a start.
    Ratings carry only the dated staff grades in force (`grades`: player -> perimeter_defense)."""
    original = rotation["players"]
    by_id = {p["player_id"]: p for p in original}
    assignments = dict(rotation.get("starters", {}))
    if assignments and (len(assignments) != 5 or len(set(assignments.values())) != 5):
        raise ValueError("staff rotation must name exactly five valid starters")
    if any("starter" in p for p in original):
        if any(type(p.get("starter")) is not bool for p in original) or sum(p["starter"] for p in original) != 5:
            raise ValueError("staff rotation must flag exactly five valid starters")
        if assignments and {p["player_id"] for p in original if p["starter"]} != set(assignments.values()):
            raise ValueError("staff rotation starter flags disagree with its positional assignments")
    if not assignments:
        explicit = [p for p in original if p.get("starter") is True]
        pool = explicit if explicit else original
        for p in pool:
            if p["position"] not in assignments and len(assignments) < 5:
                assignments[p["position"]] = p["player_id"]
        for p in pool:
            if len(assignments) == 5:
                break
            if p["player_id"] not in assignments.values():
                assignments[f"slot_{len(assignments)}"] = p["player_id"]
    excluded = set(injured) | set(unavailable)
    kept = [dict(p) for p in rotation["players"] if p["player_id"] not in excluded]
    if not kept:
        raise ValueError("every rotation player is injured; the staff must write a new rotation")
    slot_minutes = min(p["minutes"] for p in kept)
    dressed = {p["player_id"] for p in kept}
    out_count = len(rotation["players"]) - len(kept)
    for entry in replacements:
        if out_count <= 0 or len(kept) >= GAME_DAY_ACTIVES:
            break
        if entry["name"] in dressed or entry["name"] in excluded:
            continue
        player = {"player_id": entry["name"], "position": entry.get("depth_position") or entry["positions"][0],
                  "minutes": slot_minutes, "ratings": {}}
        if entry.get("bbr_id"):
            player["bbr_id"] = entry["bbr_id"]
        kept.append(player)
        dressed.add(entry["name"])
        out_count -= 1
    if len(kept) < 5:
        raise ValueError("fewer than five healthy rotation players; the staff must write a new rotation")
    dressed = {p["player_id"] for p in kept}
    starters = {name for name in assignments.values() if name in dressed}
    next_up = [p["name"] for p in replacements] + [p["player_id"] for p in kept]
    replacement_by_name = {p["name"]: p for p in replacements}
    kept_by_name = {p["player_id"]: p for p in kept}
    for pos, name in assignments.items():
        if name in starters:
            continue
        candidates = [n for n in next_up if n in dressed and n not in starters]
        def at_position(candidate):
            entry = replacement_by_name.get(candidate, {})
            return (entry.get("depth_position") == pos or pos in entry.get("positions", []) or
                    kept_by_name[candidate]["position"] == pos)
        preferred = [n for n in candidates if at_position(n)]
        if candidates:
            starters.add((preferred or candidates)[0])
    for p in kept:
        if len(starters) >= 5:
            break
        starters.add(p["player_id"])
    if len(starters) != 5 or any(name not in by_id for name in assignments.values()):
        raise ValueError("staff rotation must name exactly five valid starters")
    total = sum(p["minutes"] for p in kept)
    scale = 240 / total
    for p in kept:
        p["minutes"] = round(p["minutes"] * scale, 2)
    kept[0]["minutes"] = round(kept[0]["minutes"] + 240 - sum(p["minutes"] for p in kept), 2)
    for p in kept:
        if p["minutes"] > 48:
            raise ValueError(f"{p['player_id']} would play {p['minutes']} minutes; too few healthy players")
        grade = grades.get(p["player_id"])
        p["ratings"] = {"perimeter_defense": grade} if grade is not None else {}
        p["starter"] = p["player_id"] in starters
        p.pop("depth_position", None)
    return kept


def miami_side(game_date, root=ROOT, season=SEASON):
    """Miami's explicit players from the staff decision in force on this date."""
    from .rotation_reviews import rotation_in_force
    team = Path(root) / season_base(season) / "00_Team/Team"
    rotation, depth = rotation_in_force(game_date, root, season)
    results = [r for r in miami_results(root, season) if r.get("game_date", "") < game_date]
    injured = injured_out(results)
    if injured:
        # `injured_out` counts closed results only; the Miami games already on the calendar between the last
        # closed result and this game (requests written in the same run, not yet played) are games missed too.
        last = max(r.get("game_date", "") for r in results)
        between = sum(1 for d in miami_game_dates(root, season) if last < d < game_date)
        injured = {p: n - between for p, n in injured.items() if n - between > 0}
    roster = read_json(team / "Roster/roster.json")
    if roster.get("as_of", "") > game_date:
        raise ValueError("no historical roster for this game; the available register is dated after it")
    inactive = ("free_agent", "renounced", "released", "traded", "signed_elsewhere", "declined", "pending", "draft_rights")
    active = [p for p in roster["players"] if not any(word in p.get("status", "") for word in inactive)]
    active_names = {p["name"] for p in active}
    unavailable = {p["player_id"] for p in rotation["players"]} - active_names
    return rotation_for(rotation, injured, grades_in_force(game_date, root, season),
                        depth_order(depth, {"players": active}), unavailable), injured


def miami_request(game, players):
    venue = "home" if game["home"] == MIAMI else "away"
    miami = {"team": MIAMI, "players": players}
    other = {"team": game["away"] if venue == "home" else game["home"], "rotation": "real"}
    # The request's venue is the home club's: "home" for an arena game (neutral sites are not in the source).
    return {"event_id": game["game_id"], "game_date": game["date"], "game_type": "regular", "venue": "home",
            "home": miami if venue == "home" else other, "away": other if venue == "home" else miami}


def miami_games_due(until, root=ROOT, season=SEASON):
    """Miami's regular-season games on or before `until` that have no note or request yet, with their numbers."""
    check_date(until)
    notes = written_notes(root, season)
    plan = []
    counters = {}
    for game in season_games(season, root):
        if MIAMI not in (game["home"], game["away"]) or game["date"] > until:
            continue
        folder = Path(root) / week_dir(game["date"], season)
        if not folder.is_dir():
            raise ValueError(f"{folder.relative_to(root)} does not exist in the season structure")
        if folder not in counters:
            counters[folder] = week_numbers(folder)
        numbers, latest = counters[folder]
        if game["game_id"] in notes:
            path, number, _ = notes[game["game_id"]]
            if path.parent != folder:
                raise ValueError(f"{path.relative_to(root)} is filed outside its week folder")
            request = path.with_name(f"Game_{number}.request.json")
            if not request.exists():
                if note_meta(path).get("status") == "played" or path.with_suffix(".result.json").exists():
                    raise ValueError(f"{path.relative_to(root)}: cannot reconstruct a played or drawn game's missing request")
                plan.append({"game": game, "number": number, "folder": folder, "note": False, "request": True})
            continue
        if latest > game["date"]:
            raise ValueError(f"{folder.relative_to(root)} already holds a game dated {latest}, after {game['date']}")
        number = (numbers[-1] if numbers else 0) + 1
        if (folder / f"Game_{number}.request.json").exists() or (folder / f"Game_{number}.result.json").exists():
            raise ValueError(f"{folder.relative_to(root)}/Game_{number}: orphan request/result has no owning note; refusing to overwrite it")
        counters[folder] = (numbers + [number], game["date"])
        plan.append({"game": game, "number": number, "folder": folder, "note": True, "request": True})
    return plan


def build_miami(until, root=ROOT, season=SEASON, write=False):
    """Write (or, with write=False, list) Miami's due game notes and requests. Returns the plan rows."""
    from .game_requests import load_request
    plan = miami_games_due(until, root, season)
    for row in plan:
        game, number, folder = row["game"], row["number"], row["folder"]
        row["note_path"] = folder / f"Game_{number}.md"
        row["request_path"] = folder / f"Game_{number}.request.json"
        if not write:
            continue
        players, injured = miami_side(game["date"], root, season)
        row["injured_out"] = dict(injured)
        data = miami_request(game, players)
        if row["note"]:
            row["note_path"].write_text(game_note(number, game, "home" if game["home"] == MIAMI else "away", season), encoding="utf-8")
        row["request_path"].write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
        try:
            load_request(row["request_path"], root)
        except Exception:
            row["request_path"].unlink()
            if row["note"]:
                row["note_path"].unlink()
            raise
    return plan


def miami_check(until, root=ROOT, season=SEASON):
    """Problems a `--check` run reports: games due but not written, notes and requests that disagree."""
    problems = []
    for row in miami_games_due(until, root, season):
        what = "note and request" if row["note"] else "request"
        problems.append(f"{row['game']['game_id']}: {what} not written (due {row['game']['date']})")
    for event_id, (path, number, day) in written_notes(root, season).items():
        request = path.with_name(f"Game_{number}.request.json")
        if not request.exists():
            continue
        data = read_json(request)
        if data.get("event_id") != event_id or data.get("game_date") != day:
            problems.append(f"{request.relative_to(root)}: does not match its note")
        meta = note_meta(path)
        if meta.get("result_file") != f"Game_{number}.result.json" or meta.get("competition") != "regular":
            problems.append(f"{path.relative_to(root)}: note fields are not the builder's")
    return problems


def refresh_reports(root=ROOT):
    """Rebuild the generated player report pages after notes were written (scripts/update_player_reports.py)."""
    from .player_reports import build_reports
    player = Path(root) / PLAYER_DIR
    changed = 0
    for page, text in build_reports(Path(root), player).items():
        if not page.is_file() or page.read_text(encoding="utf-8") != text:
            page.parent.mkdir(parents=True, exist_ok=True)
            page.write_text(text, encoding="utf-8")
            changed += 1
    return changed


# -- the league slate -----------------------------------------------------------------------------
def slate_request(game):
    return {"event_id": game["game_id"], "game_date": game["date"], "game_type": "regular", "venue": "home",
            "home": {"team": game["home"], "rotation": "real"}, "away": {"team": game["away"], "rotation": "real"}}


def slate_readme(season=SEASON):
    return f"""# NBA {season} | League slate

[League records](../../README.md) · [{season} players](../League_Stats.md) · [{season} awards](../League_Awards.md) · [Game engine](../../../../../../runtime/README.md)

Every regular-season game between two real clubs, as a game request for the engine, written by
`python scripts/build_league_slate.py --write <date>` on or before each game's date from the season
schedule (`library/{season[:4]}/league/nba_{season[:4]}_{season[-2:]}_schedule.json`). Both clubs play
their real roster on the game's date (`"rotation": "real"`, world model D in `AGENTS.md`); Miami's games
are not here, they live in Miami's season folder with their game notes.

`<game_id>.request.json` is the request; `scripts/collect_results.py` writes the engine's answer to
`<game_id>.result.json` beside it. A result here is a simulation record of the league (standings and
league statistics read it), not a statistics page and not a player's game record. A request is never
edited once written.
"""


def league_games_due(until, root=ROOT, season=SEASON):
    """Non-Miami games on or before `until`: (game, path, exists)."""
    check_date(until)
    folder = Path(root) / slate_dir(season)
    rows = []
    for game in season_games(season, root):
        if MIAMI in (game["home"], game["away"]) or game["date"] > until:
            continue
        path = folder / f"{game['game_id']}.request.json"
        rows.append((game, path, path.exists()))
    return rows


def slate_structure_errors(path, data, schedule_by_id, clubs, root=ROOT):
    """Structural checks for one league-slate request: shape, clubs, and agreement with the schedule."""
    rel = Path(path).relative_to(root) if Path(path).is_absolute() else path
    errors = []
    expected_fields = {"event_id", "game_date", "game_type", "venue", "home", "away"}
    if not isinstance(data, dict) or set(data) != expected_fields:
        return [f"{rel}: request fields must be exactly {sorted(expected_fields)}"]
    game = schedule_by_id.get(data["event_id"])
    if game is None:
        errors.append(f"{rel}: event_id is not a regular-season game in the schedule")
    elif Path(path).name != f"{game['game_id']}.request.json":
        errors.append(f"{rel}: file name must be the game id")
    elif data != slate_request(game):
        errors.append(f"{rel}: differs from the schedule's game (date, clubs, type or venue)")
    for side in ("home", "away"):
        club = data.get(side)
        if not isinstance(club, dict) or set(club) != {"team", "rotation"} or club.get("rotation") != "real":
            errors.append(f"{rel}: {side} must be a real club rotation")
        elif club["team"] == MIAMI:
            errors.append(f"{rel}: Miami's games belong in the season folder")
        elif club["team"] not in clubs:
            errors.append(f"{rel}: {club['team']} has no real {SEASON} roster")
    return errors


def slate_sample(paths, every=SLATE_SAMPLE_EVERY):
    """The deterministic sample of slate requests that gets the full engine check: first, last, every Nth."""
    paths = sorted(paths)
    if not paths:
        return []
    picked = {paths[0], paths[-1]} | set(paths[::every])
    return sorted(picked)


def slate_errors(paths, root=ROOT, season=SEASON, every=SLATE_SAMPLE_EVERY):
    """Validate league-slate requests: structure for all, the engine's load_request on a sample.

    `load_request` builds both real rotations and the full packet (about 0.2 s each), so the whole
    1,189-game slate would take minutes; the structural checks catch every shape, club and schedule
    problem, and the sample proves the engine inputs on the dates. `every=1` checks everything."""
    from .game_requests import load_request
    paths = sorted(Path(p) for p in paths)
    if not paths:
        return []
    schedule_by_id = {g["game_id"]: g for g in season_games(season, root)}
    clubs = set(load_rosters(season, root))
    errors = []
    for path in paths:
        try:
            data = read_json(path)
        except (OSError, ValueError) as exc:
            errors.append(f"{path.relative_to(root)}: {exc}")
            continue
        errors.extend(slate_structure_errors(path, data, schedule_by_id, clubs, root))
    for path in slate_sample(paths, every):
        try:
            load_request(path, root)
        except (OSError, KeyError, TypeError, ValueError) as exc:
            errors.append(f"{path.relative_to(root)}: {exc}")
    return errors


def build_slate(until, root=ROOT, season=SEASON, write=False, every=SLATE_SAMPLE_EVERY):
    """Write (or list) the league requests due by `until`. Returns (written paths, validation errors)."""
    rows = league_games_due(until, root, season)
    clubs = set(load_rosters(season, root))
    for game, _, _ in rows:
        for club in (game["home"], game["away"]):
            if club not in clubs:
                raise ValueError(f"{club} is in the schedule but has no roster in {season}'s roster file")
    todo = [(game, path) for game, path, exists in rows if not exists]
    if not write:
        return [path for _, path in todo], []
    folder = Path(root) / slate_dir(season)
    folder.mkdir(parents=True, exist_ok=True)
    readme = folder / "README.md"
    if not readme.exists():
        readme.write_text(slate_readme(season), encoding="utf-8")
    written = []
    for game, path in todo:
        path.write_text(json.dumps(slate_request(game), indent=1) + "\n", encoding="utf-8")
        written.append(path)
    errors = slate_errors(written, root, season, every)
    if errors:
        for path in written:
            path.unlink()
        raise ValueError("league slate refused: " + "; ".join(errors[:5]))
    return written, errors


def slate_check(until, root=ROOT, season=SEASON, every=SLATE_SAMPLE_EVERY):
    """Problems a `--check` run reports: games due but not written, and validation of the written ones."""
    rows = league_games_due(until, root, season)
    problems = [f"{game['game_id']}: request not written (due {game['date']})" for game, _, exists in rows if not exists]
    problems.extend(slate_errors([path for _, path, exists in rows if exists], root, season, every))
    return problems


def club_name_errors(root=ROOT, season=SEASON):
    """The schedule's club names must be the roster file's (plus Miami)."""
    names = {t for g in season_games(season, root) for t in (g["home"], g["away"])}
    clubs = set(load_rosters(season, root))
    errors = []
    for name in sorted(names - clubs - {MIAMI}):
        errors.append(f"{name} is in the schedule but not in the roster file")
    for name in sorted(clubs - names):
        errors.append(f"{name} is in the roster file but not in the schedule")
    return errors
