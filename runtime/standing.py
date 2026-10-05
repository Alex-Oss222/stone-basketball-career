"""Wade's standing with Miami's front office, computed from closed simulated results and recorded honors.

Standing is the weight the front office gives Wade's requests (`STANDING_WEIGHT`, read by
`runtime/front_office.py`, `runtime/gm.py` and `runtime/trades.py`) and, at `franchise`, the
premise that Miami must ask him before it adds another star (`runtime/consultations.py`).

`compute(root, on)` is a pure function of the records on a date: whether Wade's contract on
Miami's sheet is signed on that date, every season closed on or before it
(`career/Dwyane_Wade/<season>/season_close.json`), his regular-season line in those seasons from
closed game results, and the earned honors known on the date (`awards.json`). The historical
Wade never enters. Snapshots are appended to `career/Dwyane_Wade/standing.json` at a signing, a
season close or a recorded honor; a snapshot only dates a computation, it cannot choose a value,
and validation replays every snapshot and refuses a stale file.

Every constant here is a judgement constant, named so it can be revisited.
"""
from datetime import date
import json
from pathlib import Path
import re

from .award_records import honors_in_scope, load_awards
from .career_stats import aggregate, collect_games, select
from .schedule import schedule_path, season_of_date
from .valuation import read

ROOT = Path(__file__).resolve().parents[1]
PLAYER = Path("career/Dwyane_Wade")
PROTAGONIST = "Dwyane Wade"
STANDING_PATH = PLAYER / "standing.json"
SEASON_RE = re.compile(r"^\d{4}-\d{2}$")

CATEGORIES = ("unsigned_rookie", "rookie", "starter", "all_star", "franchise")
EVIDENCE_WINDOW_SEASONS = 2          # judgement: the two most recent closed seasons count; standing can fall
STARTER_GAMES_SHARE = 0.5            # judgement: appearances >= share x Miami's scheduled regular-season games
STARTER_START_SHARE = 0.5            # judgement: starts / appearances when every start is observed
STARTER_MINUTES = 28.0               # judgement: minutes per appearance when starts are unobserved (gs is None)
HONOR_ALL_STAR = ("All-Star",)                                    # exact awards.json `name` strings (docs/player_statistics.md)
HONOR_ALL_NBA_FIRST_SECOND = ("All-NBA First Team", "All-NBA Second Team")
HONOR_ALL_NBA_THIRD = ("All-NBA Third Team",)
HONOR_ALL_NBA = HONOR_ALL_NBA_FIRST_SECOND + HONOR_ALL_NBA_THIRD
HONOR_MVP = ("Most Valuable Player",)
HONOR_FINALS_MVP = ("Finals MVP",)
HONOR_NAMES = HONOR_ALL_STAR + HONOR_ALL_NBA + HONOR_MVP + HONOR_FINALS_MVP
HONOR_COMPETITIONS = ("regular", "playoff")                       # an All-Star selection is filed as `regular`
TRIGGERS = ("signing", "season_close", "honor_recorded", "manual") # honor_recorded: runtime/season_awards.py
STANDING_WEIGHT = {"unsigned_rookie": 0.15, "rookie": 0.2, "starter": 0.35, "all_star": 0.6, "franchise": 0.8}
DEFAULT = {"standing": "unsigned_rookie", "as_of": None, "basis": {"default": "no snapshot"}}
PURPOSE = ("Dated snapshots of Wade's standing with Miami's front office (runtime/standing.py): each is the rule's "
           "computation on its date from closed simulated results and recorded honors, never the historical Wade. "
           "Append-only; validation replays every snapshot and refuses a stale file.")


# -- records -----------------------------------------------------------------------------------
def season_folder(root, on):
    """The season folder that holds the records on a date: the date's season, or the latest earlier one."""
    root = Path(root)
    wanted = season_of_date(date.fromisoformat(on))
    folders = live_folders(root)
    if wanted in folders:
        return wanted
    if not folders:
        raise ValueError("no season folder under career/Dwyane_Wade")
    earlier = [f for f in folders if f <= wanted]
    return earlier[-1] if earlier else folders[0]      # the clock sits in the offseason before the first season


def live_folders(root):
    """Season folders with a current state, oldest first. The next season's folder can exist before the rollover
    (the season close writes its expectations there) and is not live until its state is written."""
    return sorted(p.name for p in (Path(root) / PLAYER).iterdir()
                  if p.is_dir() and SEASON_RE.match(p.name) and (p / "current_state.json").is_file())


def current_date(root):
    return read(PLAYER / live_folders(root)[-1] / "current_state.json", root)["current_date"]


def signed_on(root, on, folder):
    """(signed, signed_date) from Wade's entries on the season's contract sheet: signed iff an entry has a
    `signed_date` on or before the date and its schedule covers the date's season."""
    season = max(season_of_date(date.fromisoformat(on)), folder)   # a June date belongs to the folder's coming season
    sheet = read(PLAYER / folder / "00_Team/Finances/contract_schedules.json", root)
    for p in sheet["players"]:
        if p["player"] != PROTAGONIST:
            continue
        signed = p.get("signed_date")
        if signed and signed <= on and p.get("schedule", {}).get(season) is not None:
            return True, signed
    return False, None


def closed_seasons(root, on):
    """Season-close records dated on or before the date, newest first."""
    out = []
    for path in sorted((Path(root) / PLAYER).glob("*/season_close.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("close_date") and data["close_date"] <= on:
            out.append(data)
    return sorted(out, key=lambda d: d["season"], reverse=True)


def season_line(records, season, scheduled, on):
    """Wade's regular-season line for a closed season from closed game results dated on or before `on`."""
    a = aggregate(select(records, competition="regular", season=season, end=on))
    return {"season": season, "gp": a["gp"], "gs": a["gs"], "scheduled": scheduled,
            "minutes_per_game": (round(a["pg"]["minutes"], 2) if a["complete"] and a["gp"] else None),
            "complete": bool(a["complete"])}


# -- the rule --------------------------------------------------------------------------------------
def starter_line(line):
    """Whether a season line meets the starter line; a season without complete evidence never does."""
    if not line["complete"] or not line["gp"]:
        return False
    if line["gp"] < STARTER_GAMES_SHARE * line["scheduled"]:
        return False
    if line["gs"] is not None:
        return line["gs"] / line["gp"] >= STARTER_START_SHARE
    return (line["minutes_per_game"] or 0) >= STARTER_MINUTES


def classify(signed, seasons, honors):
    """The pure rule. `seasons`: closed-season lines newest first ({season, gp, gs, scheduled, minutes_per_game,
    complete}); `honors`: earned honors ({id, name, season}) in scope. Returns (standing, basis)."""
    basis = {"closed_seasons": [s["season"] for s in seasons], "window": [], "starter_lines": {},
             "honors": [], "conflicts": [], "ignored_honors": [], "rule": None}
    if not signed:
        if seasons:
            raise ValueError("closed season without a contract")
        basis["rule"] = "not signed"
        return "unsigned_rookie", basis
    if not seasons:
        basis["rule"] = "no closed season"
        return "rookie", basis
    window = seasons[:EVIDENCE_WINDOW_SEASONS]
    basis["window"] = [s["season"] for s in window]
    met = {s["season"]: starter_line(s) for s in window}
    basis["starter_lines"] = {s["season"]: dict(s, met=met[s["season"]]) for s in window}
    counted = []
    for h in honors:
        if h["name"] not in HONOR_NAMES:
            basis["ignored_honors"].append(h["id"])
        elif h["season"] not in met:
            continue
        elif not met[h["season"]]:
            basis["conflicts"].append({"honor": h["id"], "season": h["season"], "reason": "starter line not met"})
        else:
            counted.append(h)
    basis["honors"] = sorted(h["id"] for h in counted)
    newest = window[0]["season"]
    names_by_season = {}
    for h in counted:
        names_by_season.setdefault(h["season"], set()).add(h["name"])
    if any(h["name"] in HONOR_MVP + HONOR_FINALS_MVP for h in counted):
        basis["rule"] = "MVP or Finals MVP in the window"
        return "franchise", basis
    if names_by_season.get(newest, set()) & set(HONOR_ALL_NBA_FIRST_SECOND):
        basis["rule"] = "All-NBA First or Second Team in the most recent closed season"
        return "franchise", basis
    if len(window) == EVIDENCE_WINDOW_SEASONS and all(names_by_season.get(s["season"], set()) & set(HONOR_ALL_NBA) for s in window):
        basis["rule"] = "All-NBA in every season of the window"
        return "franchise", basis
    if any(h["name"] in HONOR_ALL_STAR + HONOR_ALL_NBA for h in counted):
        basis["rule"] = "All-Star or All-NBA honor in the window with the starter line met"
        return "all_star", basis
    if met[newest]:
        basis["rule"] = "starter line met in the most recent closed season"
        return "starter", basis
    basis["rule"] = "signed; below the starter line"
    return "rookie", basis


def compute(root=ROOT, on=None):
    """Wade's standing on a date from the records as they stand: a pure function of (root, on)."""
    root = Path(root)
    on = on or current_date(root)
    folder = season_folder(root, on)
    signed, signed_date = signed_on(root, on, folder)
    now = current_date(root)
    if on == now:
        state = read(PLAYER / folder / "current_state.json", root)
        if signed != (state.get("contract_status") != "draft_rights_unsigned"):
            raise ValueError("contract_status disagrees with the contract sheet")
    seasons = closed_seasons(root, on)
    player = root / PLAYER
    lines = []
    if seasons:
        identity = json.loads((player / "professional_identity.json").read_text(encoding="utf-8"))
        records = collect_games(player, identity, now)
        lines = [season_line(records, s["season"], s["regular_season_games_scheduled"], on) for s in seasons]
    window_seasons = {s["season"] for s in seasons[:EVIDENCE_WINDOW_SEASONS]}
    honors = [{"id": a["id"], "name": a["name"], "season": a["season"]}
              for a in honors_in_scope(load_awards(player, now), known_on=on)
              if a["competition"] in HONOR_COMPETITIONS and a["season"] in window_seasons]
    standing, basis = classify(signed, lines, honors)
    basis = dict(basis, signed_date=signed_date, season_folder=folder, statistics={l["season"]: l for l in lines})
    return {"standing": standing, "as_of": on, "basis": basis}


# -- snapshots -------------------------------------------------------------------------------------
def load(root=ROOT):
    path = Path(root) / STANDING_PATH
    if not path.exists():
        return {"schema_version": 1, "purpose": PURPOSE, "snapshots": []}
    return json.loads(path.read_text(encoding="utf-8"))


def standing_on(root=ROOT, on=None):
    """The latest snapshot dated on or before the date, else the default (unsigned rookie)."""
    on = on or current_date(root)
    snaps = [s for s in load(root)["snapshots"] if s["as_of"] <= on]
    return dict(snaps[-1]) if snaps else dict(DEFAULT)


def record(root=ROOT, on=None, trigger="manual", source=None):
    """Compute the standing on the date and append a snapshot; returns it, or None when nothing changed."""
    root = Path(root)
    on = on or current_date(root)
    if trigger not in TRIGGERS:
        raise ValueError(f"unknown trigger {trigger!r}")
    now = current_date(root)
    if on > now:
        raise ValueError(f"{on} is after the career clock ({now})")
    data = load(root)
    last = data["snapshots"][-1] if data["snapshots"] else None
    if last and on < last["as_of"]:
        raise ValueError(f"{on} is before the last snapshot ({last['as_of']})")
    result = compute(root, on)
    if last and last["as_of"] == on and last["standing"] == result["standing"]:
        return None
    snap = {"as_of": on, "standing": result["standing"], "trigger": trigger, "basis": result["basis"],
            "source": source or "standing.json (manual snapshot; the value is the rule's)"}
    data["snapshots"].append(snap)
    path = root / STANDING_PATH
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return snap


# -- validation ------------------------------------------------------------------------------------
def standing_errors(root=ROOT):
    """The snapshot file replays, stays in order, and is current with the records on the career date."""
    errors = []
    root = Path(root)
    rel = str(STANDING_PATH)
    try:
        now = current_date(root)
        live = compute(root, now)
    except Exception as exc:  # a broken record is a validation failure, not a crash
        return [f"{rel}: cannot compute the standing on the career date: {exc}"]
    path = root / STANDING_PATH
    if not path.exists():
        if live["standing"] != "unsigned_rookie":
            errors.append(f"{rel}: missing while the computed standing is {live['standing']}: run scripts/update_standing.py --write {now}")
        return errors
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return [f"{rel}: invalid JSON: {exc}"]
    if data.get("schema_version") != 1 or not isinstance(data.get("snapshots"), list):
        return [f"{rel}: needs schema_version 1 and a snapshots list"]
    previous = None
    for i, s in enumerate(data["snapshots"]):
        if not isinstance(s, dict) or not {"as_of", "standing", "trigger", "basis", "source"} <= set(s):
            errors.append(f"{rel}: snapshot {i} needs as_of, standing, trigger, basis and source")
            continue
        if s["standing"] not in CATEGORIES:
            errors.append(f"{rel}: snapshot {i}: unknown standing {s['standing']!r}")
        if s["trigger"] not in TRIGGERS:
            errors.append(f"{rel}: snapshot {i}: unknown trigger {s['trigger']!r}")
        if previous and s["as_of"] < previous:
            errors.append(f"{rel}: snapshot {i}: as_of {s['as_of']} is before the previous snapshot")
        previous = s["as_of"]
        if s["as_of"] > now:
            errors.append(f"{rel}: snapshot {i}: as_of {s['as_of']} is after the career clock")
            continue
        source_ok = isinstance(s["source"], str) and (s["source"].startswith("standing.json")
                                                      or (root / PLAYER / s["source"].split("#", 1)[0]).exists())
        if not source_ok:
            errors.append(f"{rel}: snapshot {i}: source must exist under career/Dwyane_Wade")
        try:
            replay = compute(root, s["as_of"])
        except Exception as exc:
            errors.append(f"{rel}: snapshot {i}: cannot replay on {s['as_of']}: {exc}")
            continue
        if replay["standing"] != s["standing"]:
            errors.append(f"{rel}: snapshot {i}: {s['standing']} does not replay on {s['as_of']} (rule gives {replay['standing']})")
        basis = s.get("basis") or {}
        for key in ("honors", "closed_seasons"):
            if basis.get(key) != replay["basis"].get(key):
                errors.append(f"{rel}: snapshot {i}: cited {key} differ from the replay on {s['as_of']}")
    if not errors and live["standing"] != standing_on(root, now)["standing"]:
        errors.append(f"{rel} is stale: run scripts/update_standing.py --write {now}")
    return errors


def season_close_errors(root=ROOT):
    """Every season-close record agrees with the played games, the clock and the schedule."""
    errors = []
    root = Path(root)
    try:
        now = current_date(root)
    except Exception as exc:
        return [f"cannot read the career clock: {exc}"]
    for path in sorted((root / PLAYER).glob("*/season_close.json")):
        rel = path.relative_to(root)
        season = path.parent.name
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as exc:
            errors.append(f"{rel}: invalid JSON: {exc}")
            continue
        if data.get("schema_version") != 1 or data.get("season") != season:
            errors.append(f"{rel}: needs schema_version 1 and season {season}")
            continue
        close = data.get("close_date")
        if not isinstance(close, str) or close > now:
            errors.append(f"{rel}: close_date must be on or before the career clock")
            continue
        if "regular" not in (data.get("competitions_closed") or []):
            errors.append(f"{rel}: competitions_closed must include regular")
        played = []
        for note in path.parent.rglob("Game_*.md"):
            text = note.read_text(encoding="utf-8")
            if re.search(r"^status: played$", text, re.M):
                m = re.search(r"^date: (\S+)$", text, re.M)
                played.append(m.group(1) if m else "9999-99-99")
        if any(d > close for d in played):
            errors.append(f"{rel}: a played game is dated after close_date")
        try:
            games = json.loads(schedule_path(season, root).read_text(encoding="utf-8"))["games"]
            miami = sum(1 for g in games if "Miami Heat" in (g["home"], g["away"]))
            if data.get("regular_season_games_scheduled") != miami:
                errors.append(f"{rel}: regular_season_games_scheduled must equal Miami's {miami} scheduled games")
        except OSError:
            errors.append(f"{rel}: no schedule file for {season}")
        source = data.get("source")
        if not isinstance(source, str) or not (path.parent / source.split("#", 1)[0]).exists():
            errors.append(f"{rel}: source must exist under the season folder")
    return errors
