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
   bbr_id, then by name; a player in a result who is not in the registry is reported,
   never added.
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


def _researched_births(root):
    """Birth dates researched for registry players no other source dates (`library/careers/nba_player_births.json`)."""
    path = Path(root) / "library/careers/nba_player_births.json"
    return {b: e["birth_date"] for b, e in read_json(path)["players"].items() if e.get("birth_date")} if path.is_file() else {}


def repair_registry(root=ROOT, write=True):
    """Fill a dated registry addition's missing bbr_id and birth date from the identity sources (never changing a
    recorded value, never touching the original 407). Derived identity, so `scripts/reconcile.py` keeps it current.
    Returns the registry ids repaired."""
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
    if repaired and write:
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
    closed appearance. The 407 original entries are never changed."""
    season = season or _active_season(root)
    from .rotations import primary_position
    reg = registry(root)
    by_bbr = {p["bbr_id"] for p in reg["players"] if p.get("bbr_id")}
    by_name = {_key(p["name"]) for p in reg["players"]}
    codes = {p["team_name"]: p["team_code"] for p in reg["players"] if p.get("team_code")}
    codes.setdefault(MIAMI, "MIA")
    from .seasons import path as season_path
    conf_path = Path(root) / season_path(season, "conferences")
    conference = {t: c for c, ts in read_json(conf_path)["conferences"].items() for t in ts} if conf_path.is_file() else {}
    lookup = bbr_lookup(root, season)
    positions, births = {}, {}
    # Players a club signed in the symmetric market or as a disturbed-club replacement are on no real roster:
    # their identity is the dated move that put them there.
    for rel, kind in (("League/league_moves.json", "moves"), ("League/club_replacements.json", "replacements")):
        path = Path(root) / season_base(season) / rel
        if path.is_file():
            for e in read_json(path)["entries"]:
                club = e.get("to") or e.get("club")
                if club and e.get("bbr_id"):
                    lookup.setdefault((club, _key(e["player"])), e["bbr_id"])
                    positions.setdefault(e["bbr_id"], (e.get("role") or {}).get("position") or e.get("position"))
    try:
        for club, data in load_rosters(season, root).items():
            for p in data["players"]:
                positions.setdefault(p["bbr_id"], p.get("position"))
    except OSError:
        pass
    roster = Path(root) / season_base(season) / "00_Team/Team/Roster/roster.json"
    if roster.is_file():
        for p in read_json(roster)["players"]:
            if p.get("bbr_id"):
                positions.setdefault(p["bbr_id"], (p.get("positions") or [None])[0])
                births[p["bbr_id"]] = p.get("date_of_birth")
    for path in sorted(Path(root).glob("library/*/league/nba_*_end_of_season.json")) + sorted(Path(root).glob("library/*/league/nba_*_draft_class.json")):
        for club in (read_json(path).get("clubs") or {}).values():
            for p in club["players"]:
                if p.get("bbr_id") and p.get("birth_date"):
                    births.setdefault(p["bbr_id"], p["birth_date"])
    for unattached in sorted(Path(root).glob("library/*/league/nba_*_unattached_identities.json")):
        for p in read_json(unattached)["players"]:
            births.setdefault(p["bbr_id"], p.get("birth_date"))
            positions.setdefault(p["bbr_id"], p.get("position"))
    unique_names, more_births = identity_sources(root)
    for b, d in more_births.items():
        births.setdefault(b, d)
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
            pos = primary_position(positions.get(bbr) or "SF") if positions.get(bbr) else "SF"
            added[key] = {"name": pid, "position": pos, "team_name": club, "team_code": codes.get(club),
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


def expected_statuses(root=ROOT, season=None):
    """{note path: status} for the season's preseason and regular-season week notes on the career clock:
    complete once the period has passed, active while the clock is inside it, not_started before it."""
    season = season or _active_season(root)
    root = Path(root)
    now = clock(root)
    base = root / season_base(season)
    out = {}
    for note in sorted((base / "06_Regular_Season").glob("*/Week_*/note.md")):
        first, last = week_span(note)
        out[note] = "complete" if last < now else "active" if first <= now else "not_started"
    pre = base / "05_Preseason/note.md"
    if pre.is_file():
        from .seasons import dates
        gates = dates(season, root)
        opening, preseason = gates["opening_night"], gates["preseason"] or gates["opening_night"]
        out[pre] = "complete" if now >= opening else "active" if now >= preseason else "not_started"
    return out


def current_week_note(root=ROOT, season=None):
    """The week note (relative to the season folder) containing the career clock, or None outside the season."""
    season = season or _active_season(root)
    for note, status in expected_statuses(root, season).items():
        if status == "active" and note.parent.name.startswith("Week_"):
            return note.relative_to(Path(root) / season_base(season)).as_posix()
    return None


def sync_note_statuses(root=ROOT, season=None, write=True):
    """Set each period note's status and current_state.current_note to the clock. Returns the changed paths."""
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
    current = current_week_note(root, season)
    state_path = Path(root) / season_base(season) / "current_state.json"
    if current and state_path.is_file():
        state = read_json(state_path)
        if state.get("current_area") == "06_Regular_Season" and state.get("current_note") != current:
            state["current_note"] = current
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
            status = "Not started" if not n else ("Complete" if scope["end"] < now else f"Through {long_date(now)}")
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


def club_cell(cell, name, records, on, signed):
    """The Club / rights cell on `on`: a 2003 pick's "rights" label ends once he is under contract."""
    from .league_cards import signed_evidence
    if cell.endswith(" rights") and signed_evidence(name, on, records, signed):
        return cell[:-len(" rights")]
    return cell


def league_page(text, page, lines, now, results, signed=None):
    """One League_Stats.md page rebuilt from the closed results: header, leaders, position tables, period table."""
    scope = scope_for(page, [], now)
    label_on = min(scope["end"], now)
    def games_in(sc):
        return sum(1 for r in results if sc["start"] <= r["game_date"] <= sc["end"])
    summaries = {}
    for name, records in lines.items():
        summaries[name] = aggregate([r for r in records if _in(r, scope)])
    empty = aggregate([])
    n = games_in(scope)
    if n:   # a period with no closed game keeps its dated "not started" line
        text = re.sub(r"^(\d+) tracked players · \d+ closed games? in this record · [^\n]*$",
                      lambda m: f"{m.group(1)} tracked players · {_plural(n, 'closed game')} in this record · Through {long_date(now)}.",
                      text, count=1, flags=re.M)
    text = re.sub(r"(## Leaders\n\n).*?(\n\n## Players by position)", lambda m: m.group(1) + leaders_text(summaries, scope) + m.group(2), text, count=1, flags=re.S)

    def position(match):
        head, body, tail = match.groups()
        def replacer(headers, rows):
            if headers != LEAGUE_COLUMNS:
                raise ValueError(f"{page}: league table columns are not the shared layout")
            out = []
            for row in rows:
                name = _cell_name(row[0])
                club = club_cell(row[2], name, lines.get(name, ()), label_on, signed)
                out.append([*row[:2], club, *row[3:5], *stat_cells(summaries.get(name, empty))])
            return _table(headers, out)
        return head + _replace_tables(body, replacer) + tail
    text = re.sub(r"(<details>\n<summary>(?:PG|SG|SF|F|PF|C) ·[^\n]*</summary>\n)(.*?)(</details>)", position, text, flags=re.S)
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
    """The control register's current Miami players, in register order."""
    return [p["name"] for p in players if not any(word in (p.get("status") or "") for word in REGISTER_GONE)]


def team_page(text, page, lines, games, positions, now, register=None):
    """One Team_Stats.md page rebuilt from Miami's closed results.

    A period that has not started lists the control register as it stands on the career date, so
    signings, camp invites and departures reach every future page; a period with games lists the
    players who appeared plus the rows it already carried."""
    scope = scope_for(page, [], now)
    summaries = {name: aggregate([r for r in records if _in(r, scope)]) for name, records in lines.items()}
    present = sorted(name for name, s in summaries.items() if s["closed"])
    n = len([g for g in games if scope["start"] <= g["game_date"] <= scope["end"]])
    future = not n and register is not None          # no closed Miami game in the period yet
    if n:
        status = f"As of {long_date(now)}: {_plural(n, 'closed Miami game')} in this period. Rows cover Miami's closed games only."
        text = re.sub(r"^As of [^\n]*$", lambda _: status, text, count=1, flags=re.M)
    elif future:
        k = len(register)
        status = (f"As of {long_date(now)}: not started. The {k}-player control register includes contracts, options, "
                  f"camp contracts and unsigned rights; it is not a {k}-player active roster.")
        text = re.sub(r"^As of [^\n]*$", lambda _: status, text, count=1, flags=re.M)
    empty = aggregate([])

    def listed(rows):
        if future:
            return list(register)
        return [r[0] for r in rows] + [p for p in present if p not in {r[0] for r in rows}]

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


def statistics_pages(root=ROOT, season=None):
    """Every League_Stats.md and Team_Stats.md page of the season rebuilt from closed results: {path: text}."""
    season = season or _active_season(root)
    root = Path(root)
    now = clock(root)
    reg = registry(root)
    names = {p["registry_id"]: p["name"] for p in reg["players"]}
    lines, _ = closed_lines(root, season, now)
    by_name = {names[pid]: records for pid, records in lines.items() if pid in names}
    results = [row["result"] for row in closed_results(root, season, now)]
    outputs = {}
    league = root / PLAYER_DIR / "Stats_and_Awards/League" / season
    from .league_cards import signings
    signed = signings(root)
    for page in sorted(league.rglob("League_Stats.md")):
        outputs[page] = league_page(page.read_text(encoding="utf-8"), page, by_name, now, results, signed)
    team_lines, games = miami_lines(root, season, now)
    roster = root / season_base(season) / "00_Team/Team/Roster/roster.json"
    players = read_json(roster)["players"] if roster.is_file() else []
    positions = {p["name"]: "/".join(p["positions"]) for p in players}
    for row in closed_results(root, season, now):
        if row["request"]:
            side = row["request"].get("home") if row["request"]["home"].get("team") == MIAMI else row["request"].get("away")
            for p in side.get("players", []):
                positions.setdefault(p["player_id"], p.get("position", "N/A"))
    team = root / PLAYER_DIR / "Stats_and_Awards/Team" / season
    for page in sorted(team.rglob("Team_Stats.md")):
        outputs[page] = team_page(page.read_text(encoding="utf-8"), page, team_lines, games, positions, now, register_names(players))
    return outputs


def write_statistics_pages(root=ROOT, season=None):
    season = season or _active_season(root)
    changed = 0
    for page, text in statistics_pages(root, season).items():
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
    _, report["unmatched"] = closed_lines(root, season)
    if write and pages:                     # light runs (scripts/advance.py, daily) leave the page rebuild to the checkpoint
        from .season_games import refresh_reports
        report["reports"] = refresh_reports(root)
        report["pages"] = write_statistics_pages(root, season)
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
    statistics pages fresh; with `cards`, the league cards too (the script's --check; the cards also move
    with the clock, so repository validation leaves them to `build_league_cards.py --check`). The
    reporter's own freshness check is separate."""
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
