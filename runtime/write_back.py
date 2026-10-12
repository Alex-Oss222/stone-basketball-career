"""Canonical result write-back (roadmap item 13).

A result file the collector saved beside a game request is the engine's answer; it counts
only once it is written into the career record. This module does that, in order:

1. Every Miami game note (preseason under `05_Preseason`, regular season under
   `06_Regular_Season/<month>/Week_N`) whose `result_file` exists beside it and whose
   status is still `scheduled` becomes `played`: the front matter gets the result label
   (`W 95-90` from Miami's side), the body gets the result block (score, opponent, venue,
   the plain-text box score from `runtime/boxscore.py`, the Miami injuries the result
   reports with games out), `simulation_source` and `event_id` stay, the request and the
   result files are never touched, and the game is appended to the owning phase/week note's
   events. A preseason result is evidence for the preseason record only
   (`docs/player_statistics.md`); it never enters regular-season statistics.
2. Each Miami injury in a result is recorded on the player's Miami card ("Changes and
   coaching notes") with the date and games out, and in the phase note.
3. Wade's statistics: the existing reporter (`runtime/player_reports.py`) reads the played
   notes and rebuilds the game, week, month and season pages.
4. Miami team pages and league pages (`Stats_and_Awards/Team/<season>/...`,
   `Stats_and_Awards/League/<season>/...`) are aggregated from the closed regular-season
   results: Miami's from its played notes, the other clubs' from the league slate results.
   Percentages are recomputed from summed makes and attempts; a player without an
   appearance keeps G = 0 and N/A, never zero. Players are matched to the registry by
   bbr_id, then by name; a player in a result who is not in the registry is added as a
   dated registry entry (`extend_registry`). A league row's Club / rights cell is a dated
   club (`club_cell`), and closed seasons' league pages follow the registry
   (`league_records`).
5. The league player cards are regenerated with the closed results.

A result dated after the career clock waits: the write-back never advances time, never
runs the engine and never invents data. Re-running changes nothing; `write_back_errors`
is the validator's view (an unwritten result beside a scheduled note is an error).
"""
from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import re

from .boxscore import render
from .career_stats import aggregate, normalize_line
from .miami_register import RIGHTS_ONLY
from .rosters import SIMULATED_CLUB
from .rotations import load_rosters
from .season_games import PLAYER_DIR, note_meta, read_json, season_base, slate_dir
from .stat_layout import PER_GAME_COLUMNS, scope_for

ROOT = Path(__file__).resolve().parents[1]


def _active_season(root=None):
    """The career's live season (runtime/seasons.py), read from the repository a call works on."""
    from .seasons import active
    return active(root or ROOT)
MIAMI = SIMULATED_CLUB
PHASES = {"05_Preseason": ("preseason", "## Events"), "06_Regular_Season": ("regular", "## Games and events"),
          "08_Playoffs": ("playoff", "## Games and events")}
RESULT_START, RESULT_END = "<!-- game-result:start -->", "<!-- game-result:end -->"
REPORT_START = "<!-- player-report:start -->"
CHANGES_HEADING = "## Changes and coaching notes"
LEAGUE_COLUMNS = ["Player", "Age", "Club / rights", "Lg", "Pos", *PER_GAME_COLUMNS[5:-1]]
TEAM_PRODUCTION = ["Player", "Pos", "G", "MPG", "PPG", "RPG", "APG", "SPG", "BPG", "TOV/G"]
TEAM_SHOOTING = ["Player", "GS", "FG", "FG%", "3P", "3P%", "FT", "FT%", "OREB", "DREB"]
TEAM_RECORD = ["G", "W", "L", "WIN%", "PPG", "OPP PPG", "DIFF"]
LEADER_CATEGORIES = (("PPG", "pts"), ("RPG", "reb"), ("APG", "ast"), ("SPG", "stl"), ("BPG", "blk"))
NO_LEADERS = ("No eligible results yet. Publish period leaders with G and sample size; apply the season's verified "
              "qualifications before calling a result an official season leader.")


# -- small helpers ---------------------------------------------------------------------------------
def clock(root=ROOT):
    """The career clock: the latest current_date over the player's seasons."""
    return max(json.loads(p.read_text(encoding="utf-8"))["current_date"]
               for p in (Path(root) / PLAYER_DIR).glob("*/current_state.json"))


def long_date(day):
    d = date.fromisoformat(day)
    return f"{d:%B} {d.day}, {d.year}"


def _key(name):
    """A name's match key: accents folded (Nájera = Najera, Türkoğlu = Turkoglu), letters only, lower case."""
    import unicodedata
    folded = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z]", "", folded.lower())


def _n(value, places=1):
    return "N/A" if value is None else f"{value:.{places}f}"


def _ratio(value):
    return "N/A" if value is None else f"{value:.3f}".removeprefix("0")


def _plural(n, word="game"):
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def miami_side(result):
    return "home" if result.get("home") == MIAMI else "away" if result.get("away") == MIAMI else None


def result_label(result, side):
    other = "away" if side == "home" else "home"
    scores = result["final_score"]
    return f"{'W' if scores[side] > scores[other] else 'L'} {scores[side]}-{scores[other]}"


def score_line(result):
    scores = result["final_score"]
    text = f"{result['away']} {scores['away']} at {result['home']} {scores['home']}"
    if result.get("overtimes"):
        text += f" ({result['overtimes']}OT)"
    return text


# -- the Miami game notes --------------------------------------------------------------------------
def miami_notes(root=ROOT, season=None):
    """Every Miami game note the write-back owns, in date order, with its result file and phase note."""
    season = season or _active_season(root)
    base = Path(root) / season_base(season)
    rows = []
    for folder, (kind, heading) in PHASES.items():
        for path in sorted((base / folder).rglob("Game_*.md")):
            if not re.fullmatch(r"Game_\d+\.md", path.name):
                continue
            meta = note_meta(path)
            number = int(path.stem[5:])
            result_file = meta.get("result_file") or ""
            rows.append(dict(note=path, meta=meta, number=number, kind=kind, heading=heading,
                             result_path=path.with_name(result_file) if result_file else None,
                             request_path=path.with_name(f"Game_{number}.request.json"),
                             phase_note=path.parent / "note.md"))
    return sorted(rows, key=lambda r: (r["meta"].get("date", ""), str(r["note"])))


def pending_notes(root=ROOT, season=None):
    """Scheduled notes with a result beside them: (ready to write, waiting for the clock)."""
    season = season or _active_season(root)
    now = clock(root)
    ready, waiting = [], []
    for info in miami_notes(root, season):
        if info["meta"].get("status") != "scheduled" or not info["result_path"] or not info["result_path"].is_file():
            continue
        (ready if info["meta"].get("date", "") <= now else waiting).append(info)
    return ready, waiting


def miami_injuries(result):
    side = miami_side(result)
    return [i for i in result.get("injuries", []) if side and i.get("side") == side]


def miami_absences(result):
    """Miami players the engine kept out of this game only (illness or personal, kernel 2003.9)."""
    side = miami_side(result)
    return [a for a in result.get("absences", []) if side and a.get("side") == side]


def injuries_table(result):
    rows = miami_injuries(result)
    away = miami_absences(result)
    absent = ("Did not dress: " + ", ".join(f"{a['player_id']} ({a.get('kind', 'absence')}, this game only)" for a in away) + ".\n"
              if away else "")
    if not rows:
        return "No Miami injury was drawn in this game.\n" + ("\n" + absent if absent else "")
    text = "| Player | Injury | Games out |\n| --- | --- | ---: |\n"
    for i in rows:
        text += f"| {i['player_id']} | {i.get('kind', 'injury')} | {i['games_out']} |\n"
    return text + ("\n" + absent if absent else "")


def result_block(info, result):
    """The result section written into a game note: score, venue, box score, Miami injuries."""
    side = miami_side(result)
    if side is None:
        raise ValueError(f"{info['note']}: the result does not involve {MIAMI}")
    other = "away" if side == "home" else "home"
    meta = info["meta"]
    venue = "neutral site" if result.get("venue") == "neutral" else f"{'home' if side == 'home' else 'away'} ({result['home']})"
    name = info["result_path"].name
    lines = [RESULT_START, "## Result", "",
             f"**{score_line(result)}** · {MIAMI} {result_label(result, side)} vs {result[other]} · {venue} · {result['game_date']}", "",
             f"Event `{result['event_id']}` · {meta.get('simulation_source', 'engine')} · result file [`{name}`]({name}) "
             f"(the engine's answer as served; the note is the canonical record)."]
    if info["kind"] == "preseason":
        lines += ["", "Preseason result: evidence for the preseason record and the camp decisions only; it does not count in regular-season statistics."]
    lines += ["", "### Box score", "", "```text", render(result).rstrip("\n"), "```", "", "### Miami injuries", "",
              injuries_table(result).rstrip("\n"), RESULT_END]
    return "\n".join(lines)


def played_note_text(text, info, result):
    """The note text with status played, the result label and the result block; everything else kept."""
    parts = text.split("---\n", 2)
    if not text.startswith("---\n") or len(parts) < 3:
        raise ValueError(f"{info['note']}: missing front matter")
    side = miami_side(result)
    header = []
    for line in parts[1].splitlines():
        key = line.split(":", 1)[0].strip() if ":" in line else None
        if key == "status":
            line = "status: played"
        elif key == "result":
            line = f"result: {result_label(result, side)}"
        header.append(line)
    body = parts[2]
    if RESULT_START in body:
        body = re.sub(re.escape(RESULT_START) + r".*?" + re.escape(RESULT_END), lambda _: result_block(info, result), body, count=1, flags=re.S)
    elif REPORT_START in body:
        head, tail = body.split(REPORT_START, 1)
        body = head.rstrip() + "\n\n" + result_block(info, result) + "\n\n" + REPORT_START + tail
    else:
        body = body.rstrip() + "\n\n" + result_block(info, result) + "\n"
    return "---\n" + "\n".join(header) + "\n---\n" + body


def add_section_line(text, heading, line, key):
    """Append `line` at the end of the `heading` section unless a line holding `key` is already there."""
    lines = text.split("\n")
    try:
        start = lines.index(heading)
    except ValueError:
        raise ValueError(f"no {heading!r} section")
    end = start + 1
    while end < len(lines) and not lines[end].startswith("## "):
        end += 1
    section = lines[start + 1:end]
    if any(key in item for item in section):
        return text
    while section and section[-1].strip() == "":
        section.pop()
    if not section:
        section = [""]
    section += [line, ""]
    return "\n".join(lines[:start + 1] + section + lines[end:])


def event_line(info, result):
    side = miami_side(result)
    text = (f"- {result['game_date']}: {score_line(result)} — {MIAMI} {result_label(result, side)} "
            f"([Game {info['number']}]({info['note'].name}), event `{result['event_id']}`)")
    injuries = miami_injuries(result)
    if injuries:
        text += "; injuries: " + ", ".join(f"{i['player_id']} ({i.get('kind', 'injury')}, out {_plural(i['games_out'])})" for i in injuries)
    if info["kind"] == "preseason":
        text += ". Preseason: evidence only, not regular-season statistics"
    return text


def miami_card_paths(root=ROOT, season=None):
    """Player name key -> Miami card path, from the team-control register."""
    season = season or _active_season(root)
    team = Path(root) / season_base(season) / "00_Team/Team"
    out = {}
    roster = team / "Roster/roster.json"
    if roster.is_file():
        for p in read_json(roster)["players"]:
            out[_key(p["name"])] = team / "Player_Cards" / f"{p['id']}.md"
    return out


def card_injury_row(info, injury, result, card):
    import os
    rel = Path(os.path.relpath(info["note"], card.parent)).as_posix()
    out = injury["games_out"]
    return (f"| {long_date(result['game_date'])} | Injured ({injury.get('kind', 'injury')}) in event `{result['event_id']}`: "
            f"out {_plural(out)}; the game builder leaves him out of Miami's next {_plural(out)}. No grade change. | "
            f"[Game {info['number']} result]({rel}) |")


def add_card_row(text, row, key):
    """Append a row to the card's 'Changes and coaching notes' table unless `key` is already in it."""
    lines = text.split("\n")
    try:
        start = lines.index(CHANGES_HEADING)
    except ValueError:
        raise ValueError(f"card has no {CHANGES_HEADING!r} section")
    i = start + 1
    while i < len(lines) and not lines[i].startswith("|"):
        if lines[i].startswith("## "):
            raise ValueError("card's changes section has no table")
        i += 1
    j = i
    while j < len(lines) and lines[j].startswith("|"):
        j += 1
    if any(key in item for item in lines[i:j]):
        return text
    return "\n".join(lines[:j] + [row] + lines[j:])


def write_note(info, result, root=ROOT, season=None, write=True):
    """Write one result into its note, the phase note and the injured players' cards. Returns problems."""
    season = season or _active_season(root)
    problems = []
    note, phase = info["note"], info["phase_note"]
    if write:
        note.write_text(played_note_text(note.read_text(encoding="utf-8"), info, result), encoding="utf-8")
    if phase.is_file():
        text = phase.read_text(encoding="utf-8")
        new = add_section_line(text, info["heading"], event_line(info, result), result["event_id"])
        if write and new != text:
            phase.write_text(new, encoding="utf-8")
    else:
        problems.append(f"{phase}: phase note missing; the game was not logged there")
    cards = miami_card_paths(root, season)
    for injury in miami_injuries(result):
        card = cards.get(_key(injury["player_id"]))
        if card is None or not card.is_file():
            problems.append(f"{injury['player_id']}: no Miami card; injury ({result['event_id']}) is recorded in the phase note only")
            continue
        text = card.read_text(encoding="utf-8")
        new = add_card_row(text, card_injury_row(info, injury, result, card), result["event_id"])
        if write and new != text:
            card.write_text(new, encoding="utf-8")
    return problems


# -- closed results and registry matching ---------------------------------------------------------
def closed_results(root=ROOT, season=None, now=None):
    """Closed regular-season results dated on or before the clock: Miami's from played notes, the league's
    from the slate. Each row: result, source ('miami' or 'league'), note, request."""
    season = season or _active_season(root)
    now = now or clock(root)
    rows, seen = [], set()
    for info in miami_notes(root, season):
        if info["kind"] != "regular" or info["meta"].get("status") != "played":
            continue
        if not info["result_path"] or not info["result_path"].is_file():
            continue
        result = read_json(info["result_path"])
        if result.get("game_date", "") > now or not result.get("terminated"):
            continue
        request = read_json(info["request_path"]) if info["request_path"].is_file() else None
        rows.append(dict(result=result, source="miami", note=info["note"], request=request))
    folder = Path(root) / slate_dir(season)
    for path in sorted(folder.glob("*.result.json")) if folder.is_dir() else []:
        result = read_json(path)
        if result.get("game_type") != "regular" or not result.get("terminated") or result.get("game_date", "") > now:
            continue
        rows.append(dict(result=result, source="league", note=None, request=None))
    out = []
    for row in sorted(rows, key=lambda r: (r["result"]["game_date"], r["result"]["event_id"])):
        if row["result"]["event_id"] in seen:
            raise ValueError(f"duplicate closed result {row['result']['event_id']}")
        seen.add(row["result"]["event_id"])
        out.append(row)
    return out


def bbr_lookup(root=ROOT, season=None):
    """(club, name key) -> bbr_id from the real roster file and Miami's register."""
    season = season or _active_season(root)
    lookup = {}
    try:
        for club, data in load_rosters(season, root).items():
            for p in data["players"]:
                if p.get("bbr_id"):
                    lookup[(club, _key(p["player_id"]))] = p["bbr_id"]
    except OSError:
        pass
    roster = Path(root) / season_base(season) / "00_Team/Team/Roster/roster.json"
    if roster.is_file():
        for p in read_json(roster)["players"]:
            if p.get("bbr_id"):
                lookup[(MIAMI, _key(p["name"]))] = p["bbr_id"]
    return lookup


def game_records(row, root=ROOT, season=None):
    """career_stats-style records for every player row of one closed result: (side, player_id, bbr_id, record)."""
    season = season or _active_season(root)
    result, request = row["result"], row["request"]
    weighted = result.get("free_throw_mode") == "weighted"
    out = []
    for side in ("home", "away"):
        other = "away" if side == "home" else "home"
        scores = result["final_score"]
        ids = {}
        if request and isinstance(request.get(side), dict):
            for p in request[side].get("players", []):
                if p.get("bbr_id"):
                    ids[_key(p["player_id"])] = p["bbr_id"]
        base = dict(note=row["note"], status="played", date=result["game_date"], season=result["season"], competition="regular",
                    opponent=result[other], venue="neutral" if result.get("venue") == "neutral" else side,
                    result=f"{'W' if scores[side] > scores[other] else 'L'} {scores[side]}-{scores[other]}",
                    event_id=result["event_id"], cup_stage=None, team=result[side], win=scores[side] > scores[other], href=None)
        for r in result["player_stats"][side]:
            line = normalize_line(r, weighted_free_throws=weighted)
            record = dict(base, line=line, coverage="complete", appearance="Played" if line["appeared"] else "DNP: active")
            out.append((side, r["player_id"], ids.get(_key(r["player_id"])), record))
        for pid in result.get("inactive", {}).get(side, []):
            record = dict(base, line=None, coverage="complete", appearance="DNP: inactive (reason not specified)")
            out.append((side, pid, ids.get(_key(pid)), record))
    return out


def registry(root=ROOT):
    return read_json(Path(root) / PLAYER_DIR / "Stats_and_Awards/League/player_registry.json")


APPEARANCE_COHORT = "2003_04_appearance"
ORIGINAL_COHORTS = ("end_2002_03_roster", "2003_draft_rights")


def identity_sources(root=ROOT):
    """({name key: bbr_id} for names that identify one player, {bbr_id: birth date}) from every world identity source:
    the real careers table, every season's real rosters and opening books, Miami's registers, the draft classes, the
    prospect evidence (drafted and undrafted), the end-of-season rosters and the unattached identities."""
    root = Path(root)
    names, births = {}, {}

    def name(n, b):
        if n and b:
            names.setdefault(_key(n), set()).add(b)

    careers = root / "library/careers/nba_player_careers.json"
    if careers.is_file():
        for b, e in read_json(careers)["players"].items():
            name(e.get("player_name"), b)
    for path in sorted(root.glob("library/*/league/nba_*_team_rosters.json")):
        for data in (read_json(path).get("clubs") or {}).values():
            for p in data.get("players", []):
                name(p.get("player_id"), p.get("bbr_id"))
    for path in sorted(root.glob("career/Dwyane_Wade/*/League/opening_rosters.json")):
        book = read_json(path)
        for rows in list(book.get("clubs", {}).values()) + [book.get("pool", []), book.get("not_placed", [])]:
            for p in rows:
                name(p.get("player_id"), p.get("bbr_id"))
    for path in sorted(root.glob("career/Dwyane_Wade/*/00_Team/Team/Roster/roster.json")):
        for p in read_json(path)["players"]:
            name(p.get("name"), p.get("bbr_id"))
            if p.get("bbr_id") and p.get("date_of_birth"):
                births.setdefault(p["bbr_id"], p["date_of_birth"])
    for path in sorted(root.glob("library/*/league/nba_*_end_of_season.json")) + sorted(root.glob("library/*/league/nba_*_draft_class.json")):
        for club in (read_json(path).get("clubs") or {}).values():
            for p in club["players"]:
                name(p.get("player_id") or p.get("name"), p.get("bbr_id"))
                if p.get("bbr_id") and p.get("birth_date"):
                    births.setdefault(p["bbr_id"], p["birth_date"])
    for path in sorted(root.glob("library/*/league/nba_*_prospect_evidence.json")):
        data = read_json(path)
        groups = [data.get("players_drafted"), data.get("undrafted_candidates")]
        rows = [r for g in groups for r in (g if isinstance(g, list) else (g or {}).get("players", []) if isinstance(g, dict) else [])]
        for p in rows:
            if not isinstance(p, dict):
                continue
            name(p.get("player_id"), p.get("bbr_id"))
            if p.get("bbr_id") and p.get("birth_date"):
                births.setdefault(p["bbr_id"], p["birth_date"])
    for path in sorted(root.glob("library/*/league/nba_*_unattached_identities.json")):
        for p in read_json(path)["players"]:
            name(p.get("player_id") or p.get("name"), p.get("bbr_id"))
            if p.get("bbr_id") and p.get("birth_date"):
                births.setdefault(p["bbr_id"], p["birth_date"])
    births.update({b: d for b, d in _researched_births(root).items() if b not in births})
    return {k: next(iter(v)) for k, v in names.items() if len(v) == 1}, births


def id_names(root=ROOT):
    """{bbr_id: name} from the real careers table, then the researched births file: the name of a player a record keys
    by his NBA id."""
    root = Path(root)
    out = {}
    for rel, field in (("library/careers/nba_player_careers.json", "player_name"), ("library/careers/nba_player_births.json", "name")):
        if (root / rel).is_file():
            for b, e in read_json(root / rel)["players"].items():
                if e.get(field):
                    out.setdefault(b, e[field])
    return out


def _researched_births(root):
    """Birth dates researched for registry players no other source dates (`library/careers/nba_player_births.json`)."""
    path = Path(root) / "library/careers/nba_player_births.json"
    return {b: e["birth_date"] for b, e in read_json(path)["players"].items() if e.get("birth_date")} if path.is_file() else {}


# -- registry positions ---------------------------------------------------------------------------
# A registry row's `position` is also its group on every league statistics page and card index, so it is always one of
# REGISTRY_POSITIONS (validation refuses any other). Its `position_basis` names the source file that recorded it. A row
# no source records is listed under UNKNOWN_SLOT with `position_basis` UNKNOWN_BASIS: the slot is a page group only, never
# a position, and a reader that selects by position reads `known_position` (None for him). The All-Star pool does
# (`all_star.pool`); the season awards' and USA Basketball's groups (`season_awards.identities`) and the trade market's
# (`trades._group`) still read the slot, a forward, until they move to `known_position`. Before this rule an
# addition without a known bbr_id took "SF" with no basis (most of the 2004-05 rookies, such as Ben Gordon SG and
# David Harrison C); `repair_positions` fills those from the same sources.
REGISTRY_POSITIONS = ("PG", "SG", "SF", "F", "PF", "C")
UNKNOWN_SLOT = "SF"
UNKNOWN_BASIS = "unknown"


def _slot(label):
    """A source's position label as a registry position: its first listed position ('SG-SF' is SG, 'C/PF' is C), or None
    when that names no registry group ('G', 'G/F', empty)."""
    first = re.split(r"[-/]", str(label or "").strip())[0].strip().upper()
    return first if first in REGISTRY_POSITIONS else None


def _season_distance(season, other):
    return abs(int(str(other)[:4]) - int(str(season)[:4]))


def position_sources(root=ROOT, season=None, through=None):
    """The sources that record a player's position, best first: [(basis path, {(bbr_id, club): slot}, {bbr_id: slot},
    {(club, name key): slot}, {name key: slot for a name only one slot answers})]. First the season's own: its real
    rosters, the career's opening book and Miami's register; then the draft classes and the unattached identities; then
    every other season's real rosters, opening books, Miami registers, end-of-season rosters and expiring-contract lists,
    nearest season first, none after `through` (the live season: a later season's roster is not yet known to the
    career). Dated moves are not read: the market and the disturbed-club replacements write "SF" for a player no roster
    records, a placeholder; the expiring list the market reads for a real position is read here directly."""
    root = Path(root)
    season = season or _active_season(root)
    upto = int(str(through or _active_season(root))[:4])
    found = []                                                  # (rank, season distance, kind, basis, rows)

    def add(kind, other, path, rows):
        """`kind` orders a season's files (real rosters 0, opening book 0.1, Miami's register 0.2, end of season 0.3,
        expiring contracts 0.4) and the undated ones (draft classes 1, identities 2); rows are (bbr_id, club, name,
        label, minutes), and a traded player's longest stint answers for his id."""
        year = int(str(other)[:4]) if other else int(path.parts[-3])            # a library file's folder year
        if year > max(upto, int(season[:4])):
            return
        rank = 0 if other == season else 3 if other else kind  # the season's own, draft classes, identities, the others
        rows = [(b, club, _key(n) if n else None, _slot(pos)) for b, club, n, pos, _ in sorted(rows, key=lambda r: -(r[4] or 0))]
        found.append((rank, _season_distance(season, other) if other else 0, kind, path.relative_to(root).as_posix(), rows))

    for path in sorted(root.glob("library/*/league/nba_*_team_rosters.json")):
        data = read_json(path)
        rows = [(p.get("bbr_id"), club, p.get("player_id"), p.get("position"), p.get("minutes"))
                for club, c in (data.get("clubs") or {}).items() for p in c.get("players", [])]
        add(0, data.get("season"), path, rows)
    for path in sorted(root.glob(f"{PLAYER_DIR.as_posix()}/*/League/opening_rosters.json")):
        book = read_json(path)
        rows = [(p.get("bbr_id"), p.get("club"), p.get("player_id"), p.get("position"), p.get("minutes"))
                for group in list((book.get("clubs") or {}).values()) + [book.get("pool") or [], book.get("not_placed") or []] for p in group]
        add(0.1, path.parts[-3], path, rows)
    for path in sorted(root.glob(f"{PLAYER_DIR.as_posix()}/*/00_Team/Team/Roster/roster.json")):
        rows = [(p.get("bbr_id"), MIAMI, p.get("name"), (p.get("positions") or [None])[0], 0) for p in read_json(path)["players"]]
        add(0.2, path.parts[-5], path, rows)
    for path in sorted(root.glob("library/*/league/nba_*_draft_class.json")):
        data = read_json(path)
        rows = [(p.get("bbr_id"), None, p.get("player"), p.get("position"), 0) for p in data.get("picks") or []]
        rows += [(p.get("bbr_id"), None, p.get("player_id") or p.get("name"), p.get("position"), 0)
                 for c in (data.get("clubs") or {}).values() for p in c.get("players", [])]
        add(1, None, path, rows)
    for path in sorted(root.glob("library/*/league/nba_*_unattached_identities.json")):
        rows = [(p.get("bbr_id"), None, p.get("player_id") or p.get("name"), p.get("position"), 0) for p in read_json(path)["players"]]
        add(2, None, path, rows)
    def closing(data, path):
        label = str(data.get("season") or path.parts[-3])
        return label if "-" in label else f"{int(label) - 1}-{label[-2:]}"       # the 2003 files close 2002-03

    for path in sorted(root.glob("library/*/league/nba_*_end_of_season.json")):
        data = read_json(path)
        rows = [(p.get("bbr_id"), club, p.get("player_id") or p.get("name"), p.get("position"), 0)
                for club, c in (data.get("clubs") or {}).items() for p in c.get("players", [])]
        add(0.3, closing(data, path), path, rows)
    # The free agents whose contracts ended with that season (the list the symmetric market reads for an unsigned
    # player's position, `league_market._role_from_stats`): dated by the season they closed, behind its end-of-season
    # rosters, so a later season's roster answers first. Its club is the former one, not a stint, so it answers by id.
    for path in sorted(root.glob("library/*/league/nba_*_expiring_contracts.json")):
        data = read_json(path)
        rows = [(p.get("bbr_id"), None, p.get("player_id") or p.get("name"), p.get("position"), 0) for p in data.get("players") or []]
        add(0.4, closing(data, path), path, rows)
    out = []
    for _, _, _, basis, rows in sorted(found, key=lambda f: f[:4]):
        stint, by_bbr, by_club, names = {}, {}, {}, {}
        for b, club, k, slot in rows:
            if not slot:
                continue
            if b:
                stint.setdefault((b, club), slot)
                by_bbr.setdefault(b, slot)
            if k:
                by_club.setdefault((club, k), slot)
                names.setdefault(k, set()).add(slot)
        out.append((basis, stint, by_bbr, by_club, {k: next(iter(v)) for k, v in names.items() if len(v) == 1}))
    return out


def registry_position(sources, bbr=None, name=None, club=None):
    """(position, basis) for a registry row from `position_sources`: the first source that records him, by bbr_id and
    the club of his first appearance (a traded player's stints can list different positions), by club and name, by
    bbr_id, then by a name that source gives one position; (None, None) when none does."""
    k = _key(name) if name else None
    for basis, stint, by_bbr, by_club, names in sources:
        slot = (stint.get((bbr, club)) if bbr else None) or (by_club.get((club, k)) if k else None) \
            or (by_bbr.get(bbr) if bbr else None) or (names.get(k) if k else None)
        if slot:
            return slot, basis
    return None, None


def position_on(entry, on=None):
    """A registry row's position as it stood on `on`: a row whose placeholder `repair_positions` corrected keeps the
    earlier value (`position_before`) for any date before `position_corrected_on`, so a reader replaying an earlier
    decision (a closed summer market, a recorded trade) reads what that decision read; on or after the correction, and
    with no date, the row's current position."""
    if on and entry.get("position_corrected_on") and on < entry["position_corrected_on"]:
        return entry.get("position_before")
    return entry.get("position")


def known_position(entry):
    """A registry row's position for any reader that selects by position: None for a row whose position no source records
    (UNKNOWN_BASIS), where `position` holds only the page slot."""
    return None if entry.get("position_basis") == UNKNOWN_BASIS else entry.get("position")


def _added_season(entry):
    m = re.search(r"first closed (\d{4}-\d{2}) appearance", entry.get("added_basis") or "")
    return m.group(1) if m else None


def repair_positions(root=ROOT, write=True):
    """Fill the position of a dated registry addition from `position_sources` (the season of his first appearance first)
    where the row holds a placeholder: "SF" with no `position_basis` (the earlier default for an addition without a known
    bbr_id) or UNKNOWN_BASIS. A sourced different position replaces it, with its basis; no source marks the row
    UNKNOWN_BASIS and keeps its page slot; a source that confirms "SF" leaves the row as it is. A row with any other
    position was sourced when added and is never changed, nor are the original 407. With `write`, each changed row's line
    moves to its new position group on every league statistics page (`move_registry_rows`), values unchanged.
    Returns [(registry_id, name, position before, after, basis)] for every row changed or marked."""
    root = Path(root)
    path = root / PLAYER_DIR / "Stats_and_Awards/League/player_registry.json"
    reg = read_json(path)
    changed = _fill_positions(root, reg)
    if changed and write:
        _write_positions(root, path, reg, changed)
    return changed


def _write_positions(root, path, reg, changed):
    move_registry_rows(root, {rid: (before, after) for rid, _, before, after, _ in changed if before != after})
    path.write_text(json.dumps(reg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _fill_positions(root, reg):
    """`repair_positions` on a registry already read: changes the rows in place and returns the changes."""
    sources, changed = {}, []
    for p in reg["players"]:
        if p.get("cohort") != APPEARANCE_COHORT:
            continue
        basis = p.get("position_basis")
        if not ((basis is None and p.get("position") == UNKNOWN_SLOT) or basis == UNKNOWN_BASIS):
            continue
        season = _added_season(p) or _active_season(root)
        if season not in sources:
            sources[season] = position_sources(root, season)
        pos, src = registry_position(sources[season], p.get("bbr_id"), p["name"], p.get("team_name"))
        if pos is None:
            if basis != UNKNOWN_BASIS:
                _date_correction(root, p)
                p["position_basis"] = UNKNOWN_BASIS
                changed.append((p["registry_id"], p["name"], p["position"], p["position"], UNKNOWN_BASIS))
            continue
        if pos == p["position"] and basis is None:
            continue                                            # a sourced SF: the row was right
        _date_correction(root, p)
        changed.append((p["registry_id"], p["name"], p["position"], pos, src))
        p["position"], p["position_basis"] = pos, src
    return changed


def _date_correction(root, p):
    """Keep the value a correction replaces, dated by the career clock (`position_on`): earlier decisions read it."""
    if "position_corrected_on" in p:
        return
    try:
        day = clock(root)
    except ValueError:                                  # a root with no career state (a fixture): nothing to date against
        return
    p["position_before"], p["position_basis_before"] = p.get("position"), p.get("position_basis")
    p["position_corrected_on"] = day


def move_registry_rows(root, moves):
    """Move each registry id's row between position groups on every league statistics page: {registry_id: (from, to)}.
    The row keeps every value but its Pos cell, which takes the new position; it joins the end of the new group's table,
    where `scripts/format_league_reports.py` places a new row. Returns the pages rewritten."""
    if not moves:
        return []
    group_re = re.compile(r"(<details>\n<summary>(PG|SG|SF|F|PF|C) ·[^\n]*</summary>\n)(.*?)(</details>)", re.S)
    link = re.compile(r"\((?:\.\./)*Players/([^)/]+)\.md\)")
    written = []
    for page in sorted((Path(root) / PLAYER_DIR / "Stats_and_Awards/League").rglob("League_Stats.md")):
        text = page.read_text(encoding="utf-8")
        bodies = {m.group(2): m.group(3) for m in group_re.finditer(text)}
        arriving = {pos: [] for pos in bodies}
        for pos, body in list(bodies.items()):
            lines = body.split("\n")
            header = next((ln for ln in lines if ln.startswith("| Player |")), None)
            if header is None:
                continue
            col = [c.strip() for c in header.split("|")].index("Pos")
            kept = []
            for ln in lines:
                m = link.search(ln) if ln.startswith("| [") else None
                if m and m.group(1) in moves and moves[m.group(1)][0] == pos and moves[m.group(1)][1] in bodies:
                    cells = ln.split("|")
                    cells[col] = f" {moves[m.group(1)][1]} "
                    arriving[moves[m.group(1)][1]].append("|".join(cells))
                    continue
                kept.append(ln)
            bodies[pos] = "\n".join(kept)
        if not any(arriving.values()):
            continue
        for pos, rows in arriving.items():
            if rows:
                lines = bodies[pos].split("\n")
                last = max(i for i, ln in enumerate(lines) if ln.startswith("|"))
                bodies[pos] = "\n".join(lines[:last + 1] + rows + lines[last + 1:])
        text = group_re.sub(lambda m: m.group(1) + bodies[m.group(2)] + m.group(4), text)
        page.write_text(text, encoding="utf-8")
        written.append(page)
    return written


def repair_registry(root=ROOT, write=True):
    """Fill a dated registry addition's missing bbr_id and birth date from the identity sources (never changing a
    recorded value, never touching the original 407), then a placeholder position from the position sources
    (`repair_positions`). Derived identity, so `scripts/reconcile.py` keeps it current. Returns the registry ids
    repaired."""
    path = Path(root) / PLAYER_DIR / "Stats_and_Awards/League/player_registry.json"
    reg = read_json(path)
    names, births = identity_sources(root)
    taken = {p["bbr_id"] for p in reg["players"] if p.get("bbr_id")}
    known = {_key(p["name"]) for p in reg["players"] if p.get("bbr_id")}
    repaired, duplicates = [], []
    for p in reg["players"]:
        if p.get("cohort") != APPEARANCE_COHORT:
            continue
        changed = False
        if not p.get("bbr_id"):
            b = p["name"] if p["name"] in taken else names.get(_key(p["name"]))
            if (b and b in taken) or _key(p["name"]) in known:
                duplicates.append(p)          # the same player registered twice (an accented name, or his id as a name)
                continue
            if b:
                p["bbr_id"], changed = b, True
                taken.add(b)
        if not p.get("birth_date") and births.get(p.get("bbr_id")):
            p["birth_date"], changed = births[p["bbr_id"]], True
        if changed:
            repaired.append(p["registry_id"])
    if duplicates:
        reg["players"] = [p for p in reg["players"] if p not in duplicates]
        reg["player_count"] = len(reg["players"])
        counts = reg.setdefault("coverage", {}).setdefault("source_counts", {})
        counts[APPEARANCE_COHORT] = sum(1 for p in reg["players"] if p.get("cohort") == APPEARANCE_COHORT)
        repaired += [p["registry_id"] for p in duplicates]
        if write:                             # a removed duplicate's generated card pages and page rows go with it
            drop_registry_rows(root, [p["registry_id"] for p in duplicates])
            for p in duplicates:
                for folder in ("Stats_and_Awards/League/Players", "Contracts/players"):
                    for ext in (".md", ".html"):
                        page = Path(root) / PLAYER_DIR / folder / f"{p['registry_id']}{ext}"
                        if page.is_file():
                            page.unlink()
    positions = _fill_positions(root, reg)
    repaired += [rid for rid, *_ in positions if rid not in repaired]
    if positions and write:
        _write_positions(root, path, reg, positions)
    elif repaired and write:
        path.write_text(json.dumps(reg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return repaired


def drop_registry_rows(root, registry_ids):
    """Remove the table rows of registry ids no longer in the registry from every league statistics page."""
    pattern = re.compile(r"\((?:\.\./)*Players/(" + "|".join(re.escape(i) for i in registry_ids) + r")\.md\)")
    for page in (Path(root) / PLAYER_DIR / "Stats_and_Awards/League").rglob("League_Stats.md"):
        text = page.read_text(encoding="utf-8")
        kept = [line for line in text.split("\n") if not (line.startswith("|") and pattern.search(line))]
        if len(kept) != text.count("\n") + 1:
            page.write_text("\n".join(kept), encoding="utf-8")


def registry_additions(root=ROOT, season=None, now=None):
    """Players in closed results who are not in the registry, as dated registry entries (cohort APPEARANCE_COHORT):
    identity from the season's rosters, Miami's register and the dated identity records; club and date of his first
    closed appearance; position and its basis from `position_sources` (by bbr_id, else by club and name), never a
    placeholder: a player no source records takes UNKNOWN_SLOT marked UNKNOWN_BASIS. A result that keys a player by his
    NBA id (a summer market record named a few rookies by id, so their books and box scores did too) registers him under
    his name from the careers table or the researched births file (`id_names`), never the id. The 407 original entries
    are never changed."""
    from .league_cards import club_code
    season = season or _active_season(root)
    reg = registry(root)
    by_bbr = {p["bbr_id"] for p in reg["players"] if p.get("bbr_id")}
    by_name = {_key(p["name"]) for p in reg["players"]}
    named = id_names(root)
    from .seasons import path as season_path
    conf_path = Path(root) / season_path(season, "conferences")
    conference = {t: c for c, ts in read_json(conf_path)["conferences"].items() for t in ts} if conf_path.is_file() else {}
    lookup = bbr_lookup(root, season)
    births = {}
    # Players a club signed in the symmetric market or as a disturbed-club replacement are on no real roster:
    # their identity is the dated move that put them there (their position is not: see `position_sources`).
    for rel, kind in (("League/league_moves.json", "moves"), ("League/club_replacements.json", "replacements")):
        path = Path(root) / season_base(season) / rel
        if path.is_file():
            for e in read_json(path)["entries"]:
                club = e.get("to") or e.get("club")
                if club and e.get("bbr_id"):
                    lookup.setdefault((club, _key(e["player"])), e["bbr_id"])
    roster = Path(root) / season_base(season) / "00_Team/Team/Roster/roster.json"
    if roster.is_file():
        for p in read_json(roster)["players"]:
            if p.get("bbr_id"):
                births[p["bbr_id"]] = p.get("date_of_birth")
    for path in sorted(Path(root).glob("library/*/league/nba_*_end_of_season.json")) + sorted(Path(root).glob("library/*/league/nba_*_draft_class.json")):
        for club in (read_json(path).get("clubs") or {}).values():
            for p in club["players"]:
                if p.get("bbr_id") and p.get("birth_date"):
                    births.setdefault(p["bbr_id"], p["birth_date"])
    for unattached in sorted(Path(root).glob("library/*/league/nba_*_unattached_identities.json")):
        for p in read_json(unattached)["players"]:
            births.setdefault(p["bbr_id"], p.get("birth_date"))
    unique_names, more_births = identity_sources(root)
    for b, d in more_births.items():
        births.setdefault(b, d)
    sources = None                                       # read once, and only when a player is added
    added = {}
    for row in closed_results(root, season, now):
        for side, pid, bbr, record in game_records(row, root, season):
            club = row["result"][side]
            bbr = bbr or lookup.get((club, _key(pid))) or (pid if pid in by_bbr else None) or unique_names.get(_key(pid))
            if (bbr and bbr in by_bbr) or _key(pid) in by_name:
                continue
            key = bbr or _key(pid)
            if key in added:
                continue
            sources = position_sources(root, season) if sources is None else sources
            pos, basis = registry_position(sources, bbr, pid, club)
            added[key] = {"name": named.get(pid, pid),        # an NBA id is a careers key; a name never is
                          "position": pos or UNKNOWN_SLOT, "position_basis": basis or UNKNOWN_BASIS,
                          "team_name": club, "team_code": club_code(club),
                          "conference": conference.get(club), "cohort": APPEARANCE_COHORT, "bbr_id": bbr, "espn_id": None,
                          "birth_date": births.get(bbr), "registry_id": bbr or _key(pid).replace(" ", "_"),
                          "added_on": row["result"]["game_date"],
                          "added_basis": f"first closed {season} appearance, {club}, {row['result']['event_id']}"}
    return sorted(added.values(), key=lambda p: (p["added_on"], p["name"]))


def extend_registry(root=ROOT, season=None, write=True):
    """Add every unregistered player from closed results to the registry. Returns the added entries."""
    season = season or _active_season(root)
    repair_registry(root, write)
    new = registry_additions(root, season)
    if new and write:
        path = Path(root) / PLAYER_DIR / "Stats_and_Awards/League/player_registry.json"
        reg = read_json(path)
        reg["players"] = reg["players"] + new
        reg["player_count"] = len(reg["players"])
        counts = reg.setdefault("coverage", {}).setdefault("source_counts", {})
        counts[APPEARANCE_COHORT] = sum(1 for p in reg["players"] if p.get("cohort") == APPEARANCE_COHORT)
        reg["coverage"]["population_policy"] = ("Retain all 407 original registry entries; add every player who appears in a "
                                                 "closed result, dated by his first appearance (write_back.extend_registry).")
        path.write_text(json.dumps(reg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return new


def week_span(note_path):
    """(first, last) ISO dates of a regular-season week note from its folders and `days` (1-7, 8-14, 15-21, 22-end)."""
    import calendar
    month_dir, week = note_path.parent.parent.name, int(note_path.parent.name.split("_")[1])
    month = int(month_dir.split("_")[0])
    start = int(note_path.parents[3].name[:4])                      # the season folder, e.g. 2003-04
    year = start if month >= 7 else start + 1
    last_day = calendar.monthrange(year, month)[1]
    first, last = {1: (1, 7), 2: (8, 14), 3: (15, 21), 4: (22, last_day)}[week]
    return f"{year}-{month:02d}-{first:02d}", f"{year}-{month:02d}-{last:02d}"


CLOSED_BY_OPENING = ("01_Free_Agency", "02_Summer_League", "04_Training_Camp")


def expected_statuses(root=ROOT, season=None):
    """{note path: status} for the season's preseason and regular-season week notes on the career clock:
    complete once the period has passed, active while the clock is inside it, not_started before it. Phase notes close
    with their phase (the audit of June 2006 found eight left open): the summer market, summer league and training camp
    by opening night; the draft's once its draft record is in the folder (`runtime/draft.py` writes the event); and every
    phase note of an earlier season, closed by the rollover. The 03_Offseason note owns the summer after its season: it
    is active from the day after Miami's last game (`expected_place`) and closes with the season."""
    season = season or _active_season(root)
    root = Path(root)
    now = clock(root)
    base = root / season_base(season)
    out = {}
    for note in sorted((base / "06_Regular_Season").glob("*/Week_*/note.md")):
        first, last = week_span(note)
        out[note] = "complete" if last < now else "active" if first <= now else "not_started"
    from .seasons import dates, live_seasons
    pre, phases = base / "05_Preseason/note.md", []
    if pre.is_file() or any((base / folder / "note.md").is_file() for folder in CLOSED_BY_OPENING):
        gates = dates(season, root)
        opening, preseason = gates["opening_night"], gates["preseason"] or gates["opening_night"]
        if pre.is_file():
            out[pre] = "complete" if now >= opening else "active" if now >= preseason else "not_started"
        if now >= opening:
            phases += [base / folder / "note.md" for folder in CLOSED_BY_OPENING]
    end_year = int(season[:4]) + 1
    if (base / f"09_Draft/draft_{end_year}.json").is_file():
        phases.append(base / "09_Draft/note.md")
    closed = _closed(root, season)
    for earlier in (s for s in live_seasons(root) if s < season or (s == season and closed)):
        phases += sorted((root / season_base(earlier)).glob("[0-9][0-9]_*/note.md"))
    for note in phases:
        if note.is_file() and re.search(r"^type: phase$", note.read_text(encoding="utf-8"), re.M):
            out[note] = "complete"
    if not closed and (expected_place(root, season) or ("",))[0] == "03_Offseason":
        out[base / OFFSEASON_NOTE] = "active"           # from the day after Miami's last game until the rollover
    return out


def _closed(root, season):
    """The rollover closed the season (`current_state.closed`): its phase notes are complete and its place is its last
    day's, whichever season a caller passes (the suite pins 2003-04 as its live season on the real repository)."""
    path = Path(root) / season_base(season) / "current_state.json"
    return path.is_file() and bool(read_json(path).get("closed"))


def current_week_note(root=ROOT, season=None):
    """The week note (relative to the season folder) containing the career clock, or None outside the season."""
    season = season or _active_season(root)
    base, now = Path(root) / season_base(season), clock(root)
    for note in sorted((base / "06_Regular_Season").glob("*/Week_*/note.md")):
        first, last = week_span(note)
        if first <= now <= last:
            return note.relative_to(base).as_posix()
    return None


OFFSEASON_NOTE = "03_Offseason/note.md"


def expected_place(root=ROOT, season=None):
    """(current_area, current_note) owning the career clock in the live season, or None before opening night (training
    camp and the preseason set their own); a note of None keeps the recorded one:
    - from opening night through the regular season: `06_Regular_Season` and the clock's week note;
    - after the regular season, while Miami plays: `08_Playoffs` and its latest playoff round's note (before the bracket
      or the round's first game the recorded note stands);
    - from the day after Miami's last game (eliminated, champion, or out of a bracket that is set): `03_Offseason` and
      its note, which owns the summer after its season (the June 29 extension day, summer trades) until the rollover;
    - a season the rollover closed keeps that place.
    Reads the clock, the schedule and the playoff record with its closed results only. current_note feeds no game input
    and no decision, only the writers of dated phase-note lines (`signing.phase_note_for`, `extensions._miami_note`)."""
    season = season or _active_season(root)
    base = Path(root) / season_base(season)
    if _closed(root, season):
        return ("03_Offseason", OFFSEASON_NOTE) if (base / OFFSEASON_NOTE).is_file() else None
    from .seasons import dates
    now, gates = clock(root), dates(season, root)
    if now < gates["opening_night"]:
        return None
    if now <= gates["regular_season_end"]:
        return "06_Regular_Season", current_week_note(root, season)
    from copy import deepcopy
    from . import playoffs
    record = playoffs.read(root, season)
    if record is None:
        return "08_Playoffs", None
    record = playoffs.apply_results(deepcopy(record), root, season)       # the closed results, not the day's stored copy
    order = [key for key, _, _ in playoffs.ROUNDS]
    mine = sorted((s for s in record["series"] if playoffs.MIAMI in s["clubs"]), key=lambda s: order.index(s["round"]))
    if mine:
        last = mine[-1]
        over = last["winner"] is not None and (last["winner"] != playoffs.MIAMI or last["round"] == "finals")
        if not over or now <= last["clinched_on"]:
            started = [s for s in mine if min(g["date"] for g in s["games"]) <= now] or mine[:1]
            note = next((rel for rel in (f"08_Playoffs/{playoffs.FOLDERS[s['round']]}/note.md" for s in reversed(started))
                         if (base / rel).is_file()), None)
            return "08_Playoffs", note
    return ("03_Offseason", OFFSEASON_NOTE) if (base / OFFSEASON_NOTE).is_file() else ("08_Playoffs", None)


def sync_note_statuses(root=ROOT, season=None, write=True):
    """Set each period and phase note's status, and current_state's area and current_note, to the clock
    (`expected_place`): from opening night the regular season's week note, after it the playoff round note while Miami
    plays, then the season's offseason note. A closed season keeps the place of its last live day, its offseason note
    (the rollover leaves the closed state as it was). Returns the changed paths."""
    season = season or _active_season(root)
    import re
    changed = []
    for note, status in expected_statuses(root, season).items():
        text = note.read_text(encoding="utf-8")
        new = re.sub(r"^status: \S+$", f"status: {status}", text, count=1, flags=re.M)
        if new != text:
            changed.append(note)
            if write:
                note.write_text(new, encoding="utf-8")
    from .seasons import live_seasons
    places = {season: expected_place(root, season)}
    for earlier in (s for s in live_seasons(root) if s < season):
        if (Path(root) / season_base(earlier) / OFFSEASON_NOTE).is_file():
            places[earlier] = ("03_Offseason", OFFSEASON_NOTE)
    for each, place in places.items():
        state_path = Path(root) / season_base(each) / "current_state.json"
        if place is None or not state_path.is_file():
            continue
        state = read_json(state_path)
        before = dict(state)
        state["current_area"] = place[0]
        if place[1]:
            state["current_note"] = place[1]
        if state != before:
            changed.append(state_path)
            if write:
                state_path.write_text(json.dumps(state, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return changed


def closed_lines(root=ROOT, season=None, now=None):
    """Closed regular-season records per registry player: ({registry_id: [records]}, unmatched labels)."""
    season = season or _active_season(root)
    reg = registry(root)
    by_bbr = {p["bbr_id"]: p for p in reg["players"] if p.get("bbr_id")}
    by_name = {}
    for p in reg["players"]:
        by_name.setdefault(_key(p["name"]), p)
    lookup = bbr_lookup(root, season)
    unique_names, _ = identity_sources(root)
    lines, unmatched = {}, set()
    for row in closed_results(root, season, now):
        for side, pid, bbr, record in game_records(row, root, season):
            club = row["result"][side]
            bbr = bbr or lookup.get((club, _key(pid))) or (pid if pid in by_bbr else None) or unique_names.get(_key(pid))
            player = by_bbr.get(bbr) if bbr else None
            if player is None:
                player = by_name.get(_key(pid))
            if player is None:
                unmatched.add(f"{pid} ({club})")
                continue
            lines.setdefault(player["registry_id"], []).append(record)
    return lines, sorted(unmatched)


def miami_lines(root=ROOT, season=None, now=None):
    """Closed regular-season records of Miami's games per Miami player name, plus the team results."""
    season = season or _active_season(root)
    lines, games = {}, []
    for row in closed_results(root, season, now):
        if row["source"] != "miami":
            continue
        side = miami_side(row["result"])
        games.append(row["result"])
        for s, pid, _, record in game_records(row, root, season):
            if s == side:
                lines.setdefault(pid, []).append(record)
    return lines, games


# -- statistics pages ------------------------------------------------------------------------------
def _in(record, scope):
    return scope["start"] <= record["date"] <= scope["end"]


def stat_cells(summary):
    """The 26 per-game cells after Pos, in the repository's column order."""
    a, pg, rates = summary, summary["pg"], summary["rates"]
    return [_n(a["gp"], 0), _n(a["gs"], 0), _n(pg["minutes"]), _n(pg["fgm"]), _n(pg["fga"]), _ratio(rates["fg_pct"]),
            _n(pg["tpm"]), _n(pg["tpa"]), _ratio(rates["three_pct"]), _n(pg["two_pm"]), _n(pg["two_pa"]), _ratio(rates["two_pct"]),
            _ratio(rates["efg_pct"]), _n(pg["ftm"]), _n(pg["fta"]), _ratio(rates["ft_pct"]),
            *(_n(pg[k]) for k in ("orb", "drb", "reb", "ast", "stl", "blk", "tov", "pf", "pts")), _ratio(rates["ts_pct"])]


def _cell_name(cell):
    m = re.match(r"^\[([^\]]+)\]\(", cell.strip())
    return m.group(1) if m else cell.strip()


def name_order(name):
    """The alphabetical sort key of a player's name on the league pages: accents folded and case ignored (Šarūnas
    Jasikevičius sorts with the S names), the name itself breaking a tie."""
    import unicodedata
    folded = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode("ascii").casefold()
    return folded, str(name)


def _table(headers, rows, aligns=None):
    """A pipe table; `aligns` right-aligns the columns it marks True (the team pages' convention)."""
    body = "".join("| " + " | ".join(str(v) for v in row) + " |\n" for row in rows)
    marks = ["---:" if aligns and aligns[i] else "---" for i in range(len(headers))]
    return "| " + " | ".join(headers) + " |\n| " + " | ".join(marks) + " |\n" + body


def _rows(block):
    """Rows of a pipe table block as lists of cells (header and separator excluded)."""
    rows = []
    for line in block.strip("\n").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        rows.append(cells)
    return rows[0], rows[2:]


TABLE = re.compile(r"(?:^\|[^\n]*\|\n)+", re.M)


def _replace_tables(text, replacer):
    """Rewrite every pipe table through `replacer(headers, rows) -> new text or None` (None keeps it)."""
    def sub(match):
        headers, rows = _rows(match.group(0))
        new = replacer(headers, rows)
        return match.group(0) if new is None else new
    return TABLE.sub(sub, text)


def period_rows(text, page, now, games_in):
    """Rewrite a 'By month' / 'By week' table: closed games and status per linked period."""
    def replacer(headers, rows):
        if headers[:3] != ["Period", "Calendar dates", "Closed games"]:
            return None
        out = []
        for row in rows:
            m = re.match(r"^\[[^\]]+\]\(([^)]+)\)$", row[0])
            target = (page.parent / m.group(1)).resolve() if m else page
            scope = scope_for(target, [], now)
            n = games_in(scope)
            # An ended period with no closed game is complete, not "not started" (the audit of 2006-06-20).
            status = ("Complete" if scope["end"] < now else f"Through {long_date(now)}") if n else \
                ("No games" if scope["end"] < now else "Not started")
            out.append([row[0], row[1], str(n), status])
        return _table(headers, out, aligns=[False, False, True, False])
    return _replace_tables(text, replacer)


def leaders_text(summaries, scope):
    """Period leaders among registry players with an appearance: top three per category with G."""
    played = [(name, s) for name, s in summaries.items() if s["gp"]]
    if not played:
        return NO_LEADERS
    rows = []
    for label, key in LEADER_CATEGORIES:
        top = sorted(played, key=lambda item: (-item[1]["pg"][key], item[0]))[:3]
        rows.append([label, *(f"{name} {s['pg'][key]:.1f} (G {s['gp']})" for name, s in top), *[""] * (3 - len(top))])
    return ("Period comparison among registry players with at least one appearance in this scope; G is shown with each value. "
            "These are not official season leaders: the season's qualification rules are not applied.\n\n"
            + _table(["Category", "1", "2", "3"], rows).rstrip("\n"))


def club_cell(player, records, scope, on, signed=None, root=ROOT, sources=None):
    """The Club / rights and Lg cells of one League_Stats row (a dated club, the user's design change of October 2026;
    before it the cell kept the registry's 2002-03 source label): the club or clubs he appeared for in the period's
    closed results, in stint order and joined with "/"; without an appearance, his club on the page's label date `on`
    (`league_cards.dated_label`: "<code> rights" only while a club holds his unsigned draft rights, "FA" for no club, no
    club and no league before he reached the NBA). `records` are his closed records of the season."""
    from .league_cards import period_label
    return period_label(player, records, scope["start"], scope["end"], on, root=root, signed=signed, **(sources or {}))


def league_caption(on):
    """The caption over a League_Stats page's position tables, dated by the page's label date `on`."""
    from .league_cards import NOT_IN_LEAGUE
    return ("Open a position to see every tracked player, listed alphabetically. G and GS are counts; MP and counting statistics "
            "are per appearance. Shooting uses .500 = 50.0%. Scroll horizontally for all columns. "
            f"Age is each player's age on {on}, the period's end (the career date while the period runs); birth dates and "
            "identity references are in the linked player registry. Each player name opens his league card. "
            "Club / rights names the club or clubs he played for in the period's closed results, in stint order; a player "
            f"without an appearance shows his club on {on} (FA when no club holds him, \"rights\" while a club holds only his "
            f"unsigned draft rights, {NOT_IN_LEAGUE} with no league before he reached the NBA). It is not proof of an "
            "active roster spot. Unrecorded starts, attempts, splits and fouls stay N/A; they cannot be reconstructed from "
            "rounded averages.")


CAPTION = re.compile(r"^Open a position to see every tracked player[^\n]*$", re.M)
CARD_LINK = re.compile(r"^\[[^\]]*\]\((?:[^)]*/)?Players/([^/)]+)\.md\)$")


def league_page(text, page, lines, now, results, signed=None, players=None, root=ROOT, sources=None, live=True):
    """One League_Stats.md page rebuilt from the closed results: header, leaders, position tables, period table.

    Each row is the registry player its card link names (`players` and `lines` are keyed by registry id; a row without a
    link is read by name), shown under his registry name and listed alphabetically in its group. Its Age cell is his age
    on the page's label date (the period's end, or the career date while it runs) from his registry birth date (without
    one the cell keeps what it carried); its Club / rights and Lg cells are `club_cell`'s. The tracked-player count and
    each group's count are the rows' own, and the caption states the label date. A closed season's page (`live` False)
    keeps the dated "Through" line it was closed with."""
    from .league_cards import age_on
    scope = scope_for(page, [], now)
    label_on = min(scope["end"], now)
    players = players or {}
    by_name = {p["name"]: rid for rid, p in players.items()}
    def games_in(sc):
        return sum(1 for r in results if sc["start"] <= r["game_date"] <= sc["end"])
    summaries = {}
    for rid, records in lines.items():
        name = players[rid]["name"] if rid in players else rid
        summaries[name] = aggregate([r for r in records if _in(r, scope)])
    empty = aggregate([])
    n = games_in(scope)
    if n and live:   # a period with no closed game keeps its dated "not started" line
        text = re.sub(r"^(\d+) tracked players · \d+ closed games? in this record · [^\n]*$",
                      lambda m: f"{m.group(1)} tracked players · {_plural(n, 'closed game')} in this record · Through {long_date(now)}.",
                      text, count=1, flags=re.M)
    text = re.sub(r"(## Leaders\n\n).*?(\n\n## Players by position)", lambda m: m.group(1) + leaders_text(summaries, scope) + m.group(2), text, count=1, flags=re.S)
    tracked = []

    def position(match):
        head, body, tail = match.groups()
        listed = []
        def replacer(headers, rows):
            if headers != LEAGUE_COLUMNS:
                raise ValueError(f"{page}: league table columns are not the shared layout")
            out = []
            for row in rows:
                link = CARD_LINK.match(row[0])
                rid = link.group(1) if link and link.group(1) in players else by_name.get(_cell_name(row[0]))
                player = players.get(rid) or {"name": _cell_name(row[0])}
                cell = re.sub(r"^\[[^\]]*\]", lambda _: f"[{player['name']}]", row[0]) if link else player["name"]
                records = lines.get(rid, ())
                club, league = club_cell(player, records, scope, label_on, signed, root, sources)
                age = age_on(player.get("birth_date"), label_on)
                out.append([cell, str(age) if age is not None else row[1], club, league, row[4],
                            *stat_cells(summaries.get(player["name"], empty))])
            out.sort(key=lambda r: name_order(_cell_name(r[0])))
            listed.extend(out)
            return _table(headers, out)
        body = _replace_tables(body, replacer)
        tracked.append(len(listed))
        return re.sub(r" · \d+ players</summary>", f" · {len(listed)} players</summary>", head, count=1) + body + tail
    text = re.sub(r"(<details>\n<summary>(?:PG|SG|SF|F|PF|C) ·[^\n]*</summary>\n)(.*?)(</details>)", position, text, flags=re.S)
    text = re.sub(r"^\d+ tracked players · ", f"{sum(tracked)} tracked players · ", text, count=1, flags=re.M)
    text = CAPTION.sub(lambda _: league_caption(label_on), text, count=1)
    return period_rows(text, page, now, games_in)


def team_record(games, scope):
    rows = [g for g in games if scope["start"] <= g["game_date"] <= scope["end"]]
    if not rows:
        return ["0", "0", "0", "N/A", "N/A", "N/A", "N/A"]
    wins = sum(1 for g in rows if g["final_score"][miami_side(g)] > g["final_score"]["away" if miami_side(g) == "home" else "home"])
    pts = sum(g["final_score"][miami_side(g)] for g in rows)
    opp = sum(g["final_score"]["away" if miami_side(g) == "home" else "home"] for g in rows)
    n = len(rows)
    return [str(n), str(wins), str(n - wins), _ratio(wins / n), _n(pts / n), _n(opp / n), f"{(pts - opp) / n:+.1f}"]


# Register statuses of players who are no longer Miami's: they leave the not-started pages (completed
# pages keep them for the games they played).
REGISTER_GONE = ("signed_elsewhere", "traded", "waived", "released", "renounced", "option_declined", "cut", "voided")


def register_names(players):
    """The control register's current Miami players under contract, in register order (rights holders excluded)."""
    return [p["name"] for p in players if not any(word in (p.get("status") or "") for word in REGISTER_GONE)
            and p.get("status") not in RIGHTS_ONLY]


def register_rights(players):
    """[(name, label)] of the register's rights held without a contract, in register order."""
    return [(p["name"], p["status"].replace("_", " ")) for p in players if p.get("status") in RIGHTS_ONLY]


def contract_holdings(players, holdings):
    """{name: [(from, until)]} of the holdings (`Roster/holdings.json`) in which Miami held a player under contract:
    a voided camp contract (never Miami's), unsigned draft rights and draft rights never signed (a renounced or
    released pick, a rights holder) are not one. Wade's draft-rights entry runs on into his contract."""
    status = {p["name"]: p.get("status") or "" for p in players}
    out = {}
    for e in holdings:
        basis = e.get("basis") or ""
        never_signed = basis.startswith("draft rights") and (
            status.get(e["player"]) in RIGHTS_ONLY or any(w in status.get(e["player"], "") for w in ("renounced", "rights_released")))
        if e.get("void") or "unsigned" in basis or never_signed:
            continue
        out.setdefault(e["player"], []).append((e["from"], e.get("until")))
    return out


def team_page(text, page, lines, games, positions, now, register=None, held=None, rights=()):
    """One Team_Stats.md page rebuilt from Miami's closed results.

    A period that has not started lists the players under contract on the control register as it stands on the
    career date, so signings, camp invites and departures reach every future page; rights Miami holds without a
    contract (`rights`: [(name, label)]) are named in its status line, never as player rows. An ended period with no
    Miami game is complete and lists the players Miami held under contract in it (`held`: `contract_holdings`). A
    period with games lists the players who appeared plus the rows it already carried of players Miami held under
    contract in the period: a free agent whose rights Miami kept or an unsigned pick never was (the audit of
    2006-06-20)."""
    scope = scope_for(page, [], now)
    summaries = {name: aggregate([r for r in records if _in(r, scope)]) for name, records in lines.items()}
    present = sorted(name for name, s in summaries.items() if s["closed"])
    n = len([g for g in games if scope["start"] <= g["game_date"] <= scope["end"]])
    ended = scope["end"] < now
    emptied = not n and ended and held is not None   # the period is over and Miami played no game in it
    future = not n and register is not None and not emptied   # no closed Miami game in the period yet

    # A holding counts from the season's own league year (July 1): a previous year's contract that ran into June is not
    # one (Malik Allen's 2002-03 contract on the 2003-04 season page). `until` is the day he left, as in every holdings
    # reader.
    held_from = max(scope["start"], f"{scope['season'][:4]}-07-01") if scope.get("season") else scope["start"]

    def in_period(name):
        return held is None or any(f <= scope["end"] and (u is None or u > held_from) for f, u in held.get(name, []))
    if n:
        status = f"As of {long_date(now)}: {_plural(n, 'closed Miami game')} in this period. Rows cover Miami's closed games only."
        text = re.sub(r"^As of [^\n]*$", lambda _: status, text, count=1, flags=re.M)
    elif emptied:
        status = (f"As of {long_date(now)}: complete; no Miami game in this period. Rows list the players Miami held under "
                  "contract in it.")
        text = re.sub(r"^As of [^\n]*$", lambda _: status, text, count=1, flags=re.M)
    elif future:
        k = len(register)
        named = "; ".join(f"{name} ({label})" for name, label in rights)
        status = (f"As of {long_date(now)}: not started. The {k} players under contract on the control register are listed "
                  f"(contracts, options and camp contracts); it is not a {k}-player active roster."
                  + (f" Rights held without a contract, not listed: {named}." if named else ""))
        text = re.sub(r"^As of [^\n]*$", lambda _: status, text, count=1, flags=re.M)
    empty = aggregate([])

    def listed(rows):
        if future:
            return list(register)
        if emptied:
            return [name for name in held if in_period(name)]
        carried = [r[0] for r in rows if r[0] in present or in_period(r[0])]
        return carried + [p for p in present if p not in carried]

    def replacer(headers, rows):
        if headers == TEAM_RECORD:
            return _table(headers, [team_record(games, scope)], aligns=[True] * 7)
        if headers == TEAM_PRODUCTION:
            names = listed(rows)
            pos = {r[0]: r[1] for r in rows}
            out = []
            for name in names:
                s = summaries.get(name, empty)
                out.append([name, positions.get(name) or pos.get(name) or "N/A", _n(s["gp"], 0), _n(s["pg"]["minutes"]),
                            *(_n(s["pg"][k]) for k in ("pts", "reb", "ast", "stl", "blk", "tov"))])
            return _table(headers, out, aligns=[False, False] + [True] * 8)
        if headers == TEAM_SHOOTING:
            names = listed(rows)
            out = []
            for name in names:
                s = summaries.get(name, empty)
                t, rates = s["totals"], s["rates"]
                mk = lambda m, a: f"{t[m] or 0}/{t[a] or 0}"
                out.append([name, _n(s["gs"], 0), mk("fgm", "fga"), _ratio(rates["fg_pct"]), mk("tpm", "tpa"), _ratio(rates["three_pct"]),
                            mk("ftm", "fta"), _ratio(rates["ft_pct"]), str(t["orb"] or 0), str(t["drb"] or 0)])
            return _table(headers, out, aligns=[False] + [True] * 9)
        return None
    text = _replace_tables(text, replacer)
    return period_rows(text, page, now, lambda sc: sum(1 for g in games if sc["start"] <= g["game_date"] <= sc["end"]))


def league_pages(root=ROOT, season=None, live=True):
    """Every League_Stats.md page of the season rebuilt from closed results: {path: text}. A closed season's pages
    (`live` False) follow the registry (names, counts, the dated club rule) and keep the dated line they closed with."""
    season = season or _active_season(root)
    root = Path(root)
    now = clock(root)
    players = {p["registry_id"]: p for p in registry(root)["players"]}
    lines, _ = closed_lines(root, season, now)
    results = [row["result"] for row in closed_results(root, season, now)]
    league = root / PLAYER_DIR / "Stats_and_Awards/League" / season
    from .league_cards import FIRST_SEASON, TRANSACTIONS, departures_path, holdings_path, signings
    signed = signings(root)
    sources = {}
    if season == FIRST_SEASON:              # the 2003-04 dated club reads these on every label date: read them once
        for key, rel in (("holdings", holdings_path(season)), ("departures", departures_path(season)), ("transactions", TRANSACTIONS)):
            sources[key] = read_json(root / rel) if (root / rel).is_file() else ({} if key == "transactions" else {"entries": []})
    from .league_cards import roster_cache
    with roster_cache():
        return {page: league_page(page.read_text(encoding="utf-8"), page, lines, now, results, signed, players, root, sources, live)
                for page in sorted(league.rglob("League_Stats.md"))}


def closed_league_pages(root=ROOT):
    """The League_Stats.md pages of every season before the live one (`league_pages` with `live` False)."""
    from .seasons import live_seasons
    season = _active_season(root)
    out = {}
    for closed in live_seasons(root):
        if closed < season:
            out.update(league_pages(root, closed, live=False))
    return out


def statistics_pages(root=ROOT, season=None):
    """Every League_Stats.md and Team_Stats.md page of the season rebuilt from closed results: {path: text}."""
    season = season or _active_season(root)
    root = Path(root)
    now = clock(root)
    outputs = league_pages(root, season)
    outputs.update(team_pages(root, season, now))
    return outputs


def team_pages(root, season, now):
    """{path: text} for every Team_Stats.md page of the season rebuilt as of `now` (`team_page`): Miami's closed lines,
    the register's positions on `now` (a dated correction counts from its date, `miami_register.positions_on`), then the
    positions the played requests carried, the contract holdings and the rights held without a contract."""
    from .miami_register import positions_on
    root = Path(root)
    team_lines, games = miami_lines(root, season, now)
    roster = root / season_base(season) / "00_Team/Team/Roster/roster.json"
    players = read_json(roster)["players"] if roster.is_file() else []
    positions = {p["name"]: "/".join(positions_on(p, now)) for p in players}
    holdings = roster.with_name("holdings.json")
    held = contract_holdings(players, read_json(holdings)["entries"]) if holdings.is_file() else None
    for row in closed_results(root, season, now):
        if row["request"]:
            side = row["request"].get("home") if row["request"]["home"].get("team") == MIAMI else row["request"].get("away")
            for p in side.get("players", []):
                positions.setdefault(p["player_id"], p.get("position", "N/A"))
    outputs = {}
    for page in sorted((root / PLAYER_DIR / "Stats_and_Awards/Team" / season).rglob("Team_Stats.md")):
        outputs[page] = team_page(page.read_text(encoding="utf-8"), page, team_lines, games, positions, now, register_names(players),
                                  held, register_rights(players))
    return outputs


def closed_team_pages(root=ROOT):
    """{path: text} for the Team_Stats.md pages of every closed season, rebuilt by the live season's rules (`team_page`)
    as of the date the season page states: a closed season's pages stand as of their last rebuild, so only what the
    rules list changes (a rights holder's row, an ended period with no game; the audit of 2006-06-20)."""
    from .seasons import live_seasons
    root = Path(root)
    live, outputs = _active_season(root), {}
    for season in live_seasons(root):
        base = root / PLAYER_DIR / "Stats_and_Awards/Team" / season
        if season >= live or not (base / "Team_Stats.md").is_file():
            continue
        m = re.search(r"^As of ([A-Z][a-z]+ \d{1,2}, \d{4}):", (base / "Team_Stats.md").read_text(encoding="utf-8"), re.M)
        if not m:
            continue
        from datetime import datetime
        outputs.update(team_pages(root, season, datetime.strptime(m.group(1), "%B %d, %Y").date().isoformat()))
    return outputs


def write_statistics_pages(root=ROOT, season=None):
    season = season or _active_season(root)
    changed = 0
    for page, text in statistics_pages(root, season).items():
        if page.read_text(encoding="utf-8") != text:
            page.write_text(text, encoding="utf-8")
            changed += 1
    return changed


def league_records(root=ROOT, with_hub=True):
    """{path: text} of the league records that follow the registry and the season list across seasons: every closed
    season's League_Stats pages (`closed_league_pages`), every season's bracket page (`playoffs.bracket_pages`), and
    with `with_hub` the league hub's navigation and counts (`season_pages.hub`; like the award pages it is checked by
    the script's --check only, since a checkpoint copy keeps the repository's hub)."""
    from .playoffs import bracket_pages
    out = closed_league_pages(root)
    out.update(bracket_pages(root))
    if with_hub:
        from .season_pages import hub
        out.update(hub(root))
    return out


def write_league_records(root=ROOT):
    changed = 0
    for page, text in league_records(root).items():
        if page.read_text(encoding="utf-8") != text:
            page.write_text(text, encoding="utf-8")
            changed += 1
    return changed


# -- the run and the checks ------------------------------------------------------------------------
def run(root=ROOT, season=None, write=False, pages=True):
    """The write-back. With write=False nothing is touched; the report says what a run would do."""
    season = season or _active_season(root)
    root = Path(root)
    report = dict(written=[], waiting=[], problems=[], unmatched=[], pages=0, reports=0, cards=0)
    ready, waiting = pending_notes(root, season)
    report["waiting"] = [f"{i['note'].relative_to(root)}: result dated {i['meta'].get('date')} is after the career clock {clock(root)}" for i in waiting]
    for info in ready:
        result = read_json(info["result_path"])
        if not result.get("terminated") or result.get("event_id") != info["meta"].get("event_id"):
            report["problems"].append(f"{info['result_path'].relative_to(root)}: unfinished or not this note's event")
            continue
        if result.get("game_date") != info["meta"].get("date"):
            report["problems"].append(f"{info['result_path'].relative_to(root)}: dated {result.get('game_date')}, the note {info['meta'].get('date')}")
            continue
        report["problems"].extend(write_note(info, result, root, season, write=write))
        report["written"].append(f"{info['note'].relative_to(root)}: {MIAMI} {result_label(result, miami_side(result))} ({info['kind']})")
    if write:
        report["registered"] = extend_registry(root, season)
        if report["registered"]:
            from scripts.format_league_reports import format_all
            format_all(root)                     # newly registered players get their rows on every league page
        report["notes"] = sync_note_statuses(root, season)
        from .miami_cards import refresh as refresh_miami_cards, sync_register_roles
        report["roles"] = sync_register_roles(root)      # register labels follow the staff's dated rotation
        report["miami_cards"] = refresh_miami_cards(root)
        from .team_status import refresh as refresh_team_status
        report["team_status"] = refresh_team_status(root)
        # The season award hubs and month status lines, every season on file, in light runs too: the day's
        # `decide_awards.py` rewrites the week pages and the month pages' week rows, so the day's commit restates the
        # month lines and the hub's counts with them (`runtime/award_pages.py`; records only read, a few files).
        from .award_pages import write_pages as write_award_pages
        report["pages"] += len(write_award_pages(root))
    _, report["unmatched"] = closed_lines(root, season)
    if write and pages:                     # light runs (scripts/advance.py, daily) leave the page rebuild to the checkpoint
        from .season_games import refresh_reports
        report["reports"] = refresh_reports(root)
        report["pages"] += write_statistics_pages(root, season)
        for page, text in closed_team_pages(root).items():     # closed seasons' Team pages, as of their own date
            if page.read_text(encoding="utf-8") != text:
                page.write_text(text, encoding="utf-8")
                report["pages"] += 1
        report["pages"] += write_league_records(root)
        from .playoff_stats import write_pages as write_playoff_pages
        report["pages"] += write_playoff_pages(root, season)
        from .seasons import live_seasons
        for closed in live_seasons(root):             # closed seasons' playoff pages follow the registry's names
            if closed != season and (root / PLAYER_DIR / closed / "season_close.json").is_file():
                report["pages"] += write_playoff_pages(root, closed)
        from .league_cards import write_cards
        report["cards"] = sum(1 for p in write_cards(root) if p.suffix == ".md" and p.name != "README.md")
    return report


def write_back_errors(root=ROOT, season=None, cards=False):
    """Validation: no unwritten result, every played note reflects its result, injuries and events logged,
    statistics pages fresh; with `cards`, the league cards and the award pages too (the script's --check; both also
    move with the clock, so repository validation leaves the cards to `build_league_cards.py --check` and checks the
    award pages' facts with `award_pages.page_errors`). The reporter's own freshness check is separate."""
    season = season or _active_season(root)
    root = Path(root)
    errors = []
    try:
        now = clock(root)
    except (OSError, ValueError, KeyError) as exc:
        return [f"write-back: cannot read the career clock: {exc}"]
    card_paths = miami_card_paths(root, season)
    for info in miami_notes(root, season):
        rel = info["note"].relative_to(root)
        meta, status = info["meta"], info["meta"].get("status")
        exists = bool(info["result_path"]) and info["result_path"].is_file()
        if status == "scheduled" and exists and meta.get("date", "") <= now:
            errors.append(f"{rel}: unwritten result {info['result_path'].name}; run scripts/write_back_results.py --write")
            continue
        if status != "played":
            continue
        if not exists:
            errors.append(f"{rel}: played note without its result file")
            continue
        result = read_json(info["result_path"])
        side = miami_side(result)
        if side is None:
            errors.append(f"{rel}: result does not involve {MIAMI}")
            continue
        label = result_label(result, side)
        if meta.get("result") != label:
            errors.append(f"{rel}: result {meta.get('result')!r} does not match the result file ({label})")
        text = info["note"].read_text(encoding="utf-8")
        if RESULT_START not in text or f"**{score_line(result)}**" not in text:
            errors.append(f"{rel}: the result block (score and box score) is not written into the note")
        if info["phase_note"].is_file():
            if result["event_id"] not in info["phase_note"].read_text(encoding="utf-8"):
                errors.append(f"{info['phase_note'].relative_to(root)}: game {result['event_id']} is not logged in its events")
        for injury in miami_injuries(result):
            if result["event_id"] not in text:
                errors.append(f"{rel}: injury of {injury['player_id']} not in the note")
            card = card_paths.get(_key(injury["player_id"]))
            if card is not None and card.is_file() and result["event_id"] not in card.read_text(encoding="utf-8"):
                errors.append(f"{card.relative_to(root)}: injury from {result['event_id']} ({_plural(injury['games_out'])} out) is not recorded")
    try:
        for page, text in statistics_pages(root, season).items():
            if page.read_text(encoding="utf-8") != text:
                errors.append(f"{page.relative_to(root)}: stale statistics page; run scripts/write_back_results.py --write")
        for page, text in closed_team_pages(root).items():
            if page.read_text(encoding="utf-8") != text:
                errors.append(f"{page.relative_to(root)}: stale closed-season Team page; run scripts/write_back_results.py --write")
        for page, text in league_records(root, with_hub=cards).items():
            if page.read_text(encoding="utf-8") != text:
                errors.append(f"{page.relative_to(root)}: stale league page; run scripts/write_back_results.py --write")
    except (OSError, ValueError, KeyError) as exc:
        errors.append(f"write-back: cannot aggregate the statistics pages: {exc}")
    if not cards:
        return errors
    from .league_cards import check_cards
    try:
        stale = check_cards(root)
    except (OSError, ValueError, KeyError) as exc:
        stale, errors = [], errors + [f"write-back: cannot build the league cards: {exc}"]
    if stale:
        errors.append(f"{len(stale)} league card file(s) differ from the closed results, for example {stale[0].relative_to(root)}; run scripts/build_league_cards.py --write")
    # The award hubs and month status lines this write-back owns, compared whole (their 'As of' date too); repository
    # validation checks what they show against the records instead (`award_pages.page_errors`).
    from .award_pages import write_pages as write_award_pages
    try:
        errors += [f"{page.relative_to(root)}: stale award page; run scripts/write_back_results.py --write"
                   for page in write_award_pages(root, write=False)]
    except (OSError, ValueError, KeyError) as exc:
        errors.append(f"write-back: cannot build the award pages: {exc}")
    return errors


def identity_warnings(root=ROOT):
    """Registry players without a birth date: their age reads N/A until one is added to
    `library/careers/nba_player_births.json`. Reported by `scripts/reconcile.py`; never a stop (it changes no result)."""
    return [f"registry {p.get('registry_id')} ({p['name']}): no birth date; age shows N/A (add it to library/careers/nba_player_births.json)"
            for p in registry(root)["players"] if not p.get("birth_date")]


def identity_errors(root=ROOT, on=None):
    """League identity checks (the user's request, November 2004 on the career clock: a player on a club must never
    read as a free agent). Every registry player has a bbr_id and a birth date and appears once (accents folded), and
    each card's club on the career date is the club the simulated league has him with (`options.holders_on`,
    Miami's register for Miami): a mismatch names the player and both clubs."""
    from .league_cards import club_on
    from .options import holders_on
    from .rotations import miami_holds
    root = Path(root)
    reg = registry(root)["players"]
    errors = []
    seen_bbr, seen_name = {}, {}
    for p in reg:
        label = f"registry {p.get('registry_id')} ({p['name']})"
        if not p.get("bbr_id"):
            errors.append(f"{label}: no bbr_id (python scripts/reconcile.py repairs it from the identity sources)")
        elif p["bbr_id"] in seen_bbr:
            errors.append(f"{label}: the same player as registry {seen_bbr[p['bbr_id']]}")
        seen_bbr.setdefault(p.get("bbr_id"), p.get("registry_id"))
        k = _key(p["name"])
        if k in seen_name and p.get("bbr_id") == seen_name[k][1]:
            errors.append(f"{label}: registered twice under one name")
        seen_name.setdefault(k, (p.get("registry_id"), p.get("bbr_id")))
    on = on or clock(root)
    season = _active_season(root)
    from .league_book import active
    if season == "2003-04" or on < f"{season[:4]}-10-01" or not active(on):
        return errors                                    # the club check reads the symmetric league from 2004-05
    from .availability import status
    from .league_moves import club_of
    from .player_stats import alias
    holders = holders_on(on, root)
    miami = set(miami_holds(season, on, root))
    for p in reg:
        b = p.get("bbr_id")
        if not b:
            continue
        if b in miami or alias(p["name"]) in miami:
            actual = "Miami Heat"
        elif status(b, season, root) == "unavailable":
            actual = club_of(b, on, season, root)          # out for the season (injury): his contract's club holds him
        else:
            actual = holders.get(b)
        try:
            shown = (club_on(p, on, root=root) or {}).get("club")
        except Exception as exc:                          # a player the dated rules cannot place
            errors.append(f"registry {p['registry_id']} ({p['name']}): no club can be placed on {on} ({exc})")
            continue
        if actual != shown:
            errors.append(f"registry {p['registry_id']} ({p['name']}): card shows {shown or 'free agent'} on {on}, "
                          f"the league has him with {actual or 'no club (free agent)'}")
    return errors
