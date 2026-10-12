"""Uniform numbers on a date, club by club (identity data, never a game input).

- Real players wear their real number for the season with that club (`library/<year>/league/nba_<season>_jerseys.json`,
  Basketball-Reference team rosters). A player the simulation put on a different club keeps his number for the season
  from another club, then his numbers from earlier seasons, newest first, then his 2002-03 number
  (`nba_2003_end_of_season.json`), when it is free there.
- Within a club a number is held once: the player already there keeps it; a later arrival whose numbers are all
  taken takes the lowest number from 0 to 55 not in use (the equipment manager's choice; judgement, documented).
  Another club's numbers are assigned over its effective roster on the date (`league_moves.effective_roster`) in
  tenure order: on the club since the season's opening book first, then each arrival by the date he joined; among
  players there equally long, one whose real number for the season is with this club goes first (the audit of June
  2006: 38 numbers were shown twice at 24 clubs when every card took its first preference). The players a club holds
  off its roster (out for the season under contract, `club_truth.holder`) follow, in registry order. A card's lookup
  (`number_for`) only reads these numbers; they are memoized per process while the roster records are unchanged.
- A Miami player who was on Miami's register the season before keeps his Miami number from that season before any
  real-club number (numbers carry across seasons, AGENTS.md); the continuing players are seated first.
- The simulated Wade has no real number: his is set by his own request and, when another player holds it, that
  player's answer, an engine decision draw (`Wade_Jersey/`). After a decline Wade may choose to wait for the number
  (`Wade_Jersey/wade_choice.json`): he takes it the first date no other Miami player holds it. Until a number is
  settled he is "not assigned". A settled number stays his in later seasons: the choice settles in the first season,
  from its own on, whose register has no other holder, and is never re-checked after (the audit of June 2006: Caron
  Butler's real 2005-06 Washington #3 had displaced it). His requests and choice are searched from the live season back.
"""
from functools import lru_cache
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = Path("library/2003/league/nba_2003_end_of_season.json")
REGISTRY = Path("career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json")
MIAMI = "Miami Heat"
WADE = "Dwyane Wade"
GONE = ("released", "traded", "signed_elsewhere", "voided", "waived", "renounced", "declined")


def _read(path, root):
    path = Path(root) / path
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def _season(root=None):
    from .seasons import active
    return active(root or ROOT)


def register_path(root=ROOT, season=None):
    return Path(f"career/Dwyane_Wade/{season or _season(root)}/00_Team/Team/Roster/roster.json")


def request_dirs(root=ROOT, season=None):
    """Wade's jersey folders, the live season (or `season`) first, then earlier seasons."""
    from .seasons import live_seasons
    live = season or _season(root)
    seasons = [s for s in reversed(live_seasons(root) if (Path(root) / "career/Dwyane_Wade").is_dir() else []) if s <= live] or [live]
    return [Path(f"career/Dwyane_Wade/{s}/00_Team/Team/Roster/Wade_Jersey") for s in seasons]


def _jersey_files(root, season=None):
    """The live season's (or `season`'s) jersey file, then earlier seasons', newest first."""
    from .seasons import path, previous_season
    season, out = season or _season(root), []
    while int(season[:4]) >= 2003:
        out.append(path(season, "jerseys"))
        season = previous_season(season)
    return out


def candidates(bbr, club, root=ROOT, season=None):
    """His numbers in order of preference for this club."""
    files = [_read(f, root).get("players", {}).get(bbr, []) for f in _jersey_files(root, season)]
    real = files[0] if files else []
    out = [r["number"].split(",")[-1].strip() for r in real if r["club"] == club]
    out += [r["number"].split(",")[-1].strip() for r in real if r["club"] != club]
    for older in files[1:]:
        out += [r["number"].split(",")[-1].strip() for r in older]
    for c in _read(BASELINE, root).get("clubs", {}).values():
        for p in c["players"]:
            if p.get("bbr_id") == bbr and p.get("jersey"):
                out.append(str(p["jersey"]))
    seen = []
    for n in out:
        if n not in seen:
            seen.append(n)
    return seen


CHOICE_NAME = "wade_choice.json"


def _active(register):
    return [p for p in register if not any(w in (p.get("status") or "") for w in GONE)]


def _seasons_from(first, season):
    """The seasons from `first` to `season`, oldest first."""
    from .seasons import previous_season
    out = [season]
    while out[-1] > first:
        out.append(previous_season(out[-1]))
    return out[::-1]


def _preferences(p, root, season, previous):
    """A Miami player's numbers in order: his number on Miami's register the season before, when he was on it, then
    his candidates for the season."""
    kept = [previous[p["name"]]] if previous.get(p["name"]) else []
    return kept + [n for n in candidates(p.get("bbr_id"), MIAMI, root, season) if n not in kept]


def _previous_numbers(root, season):
    """Miami's numbers on the previous season's register ({} for the first season or without that register)."""
    from .seasons import previous_season
    prev = previous_season(season)
    if int(prev[:4]) < 2003 or not (Path(root) / register_path(root, prev)).is_file():
        return {}
    return miami_numbers(root, prev)


def _stamp(root, season):
    """The modification times of the Miami records the numbers of a season read (every register and jersey folder up
    to it), so a memoized answer is reused only while they are unchanged."""
    out = []
    for s in _seasons_from("2003-04", season):
        register = Path(root) / register_path(root, s)
        out.append(register.stat().st_mtime_ns if register.is_file() else None)
        folder = Path(root) / f"career/Dwyane_Wade/{s}/00_Team/Team/Roster/Wade_Jersey"
        out += [(f.name, f.stat().st_mtime_ns) for f in sorted(folder.iterdir())] if folder.is_dir() else []
    return tuple(out)


_MEMO = {}


def _memo(kind, compute, root, season):
    """One answer per process for a season's Miami numbers or Wade's number, while the records they read are unchanged
    (each recursed through every earlier season: a card build asks for them once per Miami player)."""
    key = (kind, str(Path(root).resolve()), season, _stamp(root, season))
    if key not in _MEMO:
        _MEMO[key] = compute(root, season)
    return _MEMO[key]


def wade_number(root=ROOT, season=None):
    """(number or None, the decision that settled it or None): an accepted request, else Wade's recorded choice to wait
    for a number, settled in the first season from the choice's own whose register has no other player holding it
    (first preference) and his in every later season."""
    season = season or _season(root)
    return _memo("wade", _wade_number, root, season)


def _wade_number(root, season):
    number, source = _requested_number(root, season)
    if number:
        return number, source
    for folder in request_dirs(root, season):
        choice = _read(folder / CHOICE_NAME, root)
        if choice.get("number"):
            for s in _seasons_from(folder.parts[2], season):
                if not (Path(root) / register_path(root, s)).is_file():
                    continue
                register = _read(register_path(root, s), root).get("players", [])
                previous = _previous_numbers(root, s)
                holders = [p for p in _active(register) if p["name"] != WADE
                           and choice["number"] in _preferences(p, root, s, previous)[:1]]
                if not holders:
                    return choice["number"], CHOICE_NAME
            return None, None
    return None, None


def _requested_number(root=ROOT, season=None):
    for rel in request_dirs(root, season):
        number, source = _requested_in(Path(root) / rel)
        if number:
            return number, source
    return None, None


def _requested_in(folder):
    for packet in sorted(folder.glob("*.decision.json")) if folder.is_dir() else []:
        result = packet.with_name(packet.name.replace(".decision.json", ".decision.result.json"))
        if not result.is_file():
            return None, None
        data = json.loads(packet.read_text(encoding="utf-8"))
        if json.loads(result.read_text(encoding="utf-8"))["outcome"] == "accept":
            return data["event_id"].rsplit("-", 1)[-1], data["event_id"]
    return None, None


def assign(players, root=ROOT, fixed=None, season=None, prefer=None):
    """{key: number or None} for a club's players in tenure order: [(key, bbr, club)]. `fixed` pre-assigns keys;
    `prefer` gives a key's own preference list in place of his candidates."""
    fixed = dict(fixed or {})
    taken = {n for n in fixed.values() if n}
    out = dict(fixed)
    for key, bbr, club in players:
        if key in out:
            continue
        own = (prefer or {}).get(key)
        if own is None:
            own = candidates(bbr, club, root, season) if bbr else []
        number = next((n for n in own if n not in taken), None)
        if number is None:
            number = next(str(n) for n in range(0, 56) if str(n) not in taken)
        out[key] = number
        taken.add(number)
    return out


def miami_numbers(root=ROOT, season=None):
    """Miami's register on the career date (or `season`'s register): {name: number or None}; Wade only from his
    settled request. Continuing players are seated first with their previous Miami number."""
    season = season or _season(root)
    return dict(_memo("miami", _miami_numbers, root, season))


def _miami_numbers(root, season):
    register = _read(register_path(root, season), root).get("players", [])
    active = _active(register)
    previous = _previous_numbers(root, season)
    prefer = {p["name"]: _preferences(p, root, season, previous) for p in active if p["name"] != WADE}
    wade, _ = wade_number(root, season)
    fixed = {WADE: wade}
    if wade:
        holder = next((p["name"] for p in active if p["name"] != WADE and wade in prefer[p["name"]][:1]), None)
        if holder:
            fixed[holder] = None                                        # he gave it up: a new number below
    order = [(p["name"], p.get("bbr_id"), MIAMI) for p in active if p["name"] != WADE]
    order.sort(key=lambda x: x[0] not in previous)                      # stable: the continuing players are there first
    numbers = assign([x for x in order if x[0] not in fixed or fixed[x[0]] is not None], root,
                     {k: v for k, v in fixed.items() if v}, season, prefer)
    if wade:
        for name, value in fixed.items():
            if value is None and name != WADE:
                taken = {v for v in numbers.values() if v}
                numbers[name] = next((n for n in prefer[name] if n not in taken and n != wade),
                                     next(str(n) for n in range(0, 56) if str(n) not in taken))
    numbers.setdefault(WADE, wade)
    return numbers


_CLUBS = {}


def club_numbers(club, on=None, root=ROOT):
    """{bbr_id: number} for a club other than Miami on the date (default the career date), from its effective roster
    in tenure order (`assign`): the season's opening book first, then each arrival by the date he joined (a league move,
    a Miami departure or a disturbed club's replacement); among players there equally long, one with a real number for
    the season with this club first, then the roster's order. None before the symmetric league, whose rosters are the
    real ones."""
    from .league_book import active as league_active
    from .seasons import state
    season = _season(root)
    try:
        on = on or state(season, root)["current_date"]
    except OSError:                                         # a scaffold without the season's state
        return None
    if not league_active(on):
        return None
    key = (str(Path(root).resolve()), club, on, _roster_stamp(root, season))
    if key not in _CLUBS:
        from .club_replacements import read as replacements
        from .league_moves import effective_roster, read as moves
        from .rotations import departures_path
        joined = {}
        for e in _read(departures_path(season), root).get("entries", []) + replacements(season, root)["entries"]:
            if e["club"] == club and e["from"] <= on:
                joined[e["bbr_id"]] = max(joined.get(e["bbr_id"], ""), e["from"])
        for e in moves(season, root)["entries"]:
            if e.get("to") == club and e["date"] <= on:
                joined[e["bbr_id"]] = max(joined.get(e["bbr_id"], ""), e["date"])
        real = _read(_jersey_files(root, season)[0], root).get("players", {})
        roster = [p for p in effective_roster(club, on, season, root) if p.get("bbr_id")]
        order = sorted(range(len(roster)), key=lambda i: (joined.get(roster[i]["bbr_id"], ""),
                                                          not any(r["club"] == club for r in real.get(roster[i]["bbr_id"], [])), i))
        on_roster = {p["bbr_id"] for p in roster}
        players = [(roster[i]["bbr_id"], roster[i]["bbr_id"], club) for i in order]
        players += [(b, b, club) for b in _held_off_roster(club, on, season, on_roster, root)]
        _CLUBS[key] = assign(players, root, season=season)
    return dict(_CLUBS[key])


def _roster_stamp(root, season):
    """The modification times of the dated roster records a club's numbers read (league moves, disturbed clubs'
    replacements, Miami's departures and holdings), so a roster change later in the same process is seen."""
    from .club_replacements import path_for
    from .league_moves import ledger_path
    from .rotations import departures_path, holdings_path
    paths = (Path(root) / rel for rel in (ledger_path(season), path_for(season), departures_path(season), holdings_path(season)))
    return tuple(p.stat().st_mtime_ns if p.is_file() else None for p in paths)


def _held_off_roster(club, on, season, on_roster, root):
    """The players the club holds off its roster on the date (out for the season under contract, `club_truth.holder`),
    in registry order: they take numbers after the roster's players."""
    from .club_truth import holder
    from .league_moves import clubs_at_activation, read as moves
    clubs = dict(clubs_at_activation(season, root))
    for e in sorted(moves(season, root)["entries"], key=lambda e: e["date"]):
        if e["date"] <= on:
            clubs[e["bbr_id"]] = e["to"]
    held = {b for b, c in clubs.items() if c == club and b and b not in on_roster and holder(b, None, on, root)[0] == club}
    rank = {b: i for i, b in enumerate(_registry_ids(str(Path(root).resolve()), _mtime(Path(root) / REGISTRY)).values())}
    return sorted(held, key=lambda b: (rank.get(b, len(rank)), b))


def _mtime(path):
    return path.stat().st_mtime_ns if path.is_file() else None


@lru_cache(maxsize=4)
def _registry_ids(root, mtime):
    """{registry id: NBA id} from the league registry, read once per registry version."""
    return {p["registry_id"]: p.get("bbr_id") for p in _read(REGISTRY, root).get("players", [])}


def _nba_id(key, root):
    """A league registry id's NBA (Basketball-Reference) id: a later registry entry is keyed by name, not by the NBA id."""
    return _registry_ids(str(Path(root).resolve()), _mtime(Path(root) / REGISTRY)).get(key) or key


def number_for(bbr, club, root=ROOT, on=None):
    """A league card's number by the player's NBA id (or registry id): Miami's from its register; another club's from
    its numbers on the date (`club_numbers`, which seats the players a club holds off its roster after the roster's),
    else, before the symmetric league, his first preference (his real club's number). Read-only: it never changes the
    club's numbers."""
    if club == MIAMI:
        # Wade's register entry carries no Basketball-Reference id (alternate history): his card's id is wadedw01.
        register = {p.get("bbr_id") or ("wadedw01" if p["name"] == WADE else None): p["name"]
                    for p in _read(register_path(root), root).get("players", [])}
        return miami_numbers(root).get(register.get(bbr) or register.get(_nba_id(bbr, root)))
    numbers = club_numbers(club, on, root)
    if numbers is not None and bbr:
        if bbr not in numbers:
            bbr = _nba_id(bbr, root)
        if bbr not in numbers:      # on neither list (no holder on the date): his first number free there, nothing kept
            return assign([(bbr, bbr, club)], root, fixed=numbers)[bbr]
        return numbers[bbr]
    pref = candidates(bbr, club, root)
    return pref[0] if pref else None


def request_packet(number, holder, date, standing, season=None):
    """Wade's request for a number another player holds: the holder's answer is an engine draw."""
    accept = 0.6
    season = season or _season()
    return {"event_id": f"{season}-wade-jersey-request-{number}", "date": date,
            "question": f"Does {holder} give jersey #{number} to Dwyane Wade?",
            "decider": f"{holder} (simulated player)",
            "options": {"accept": accept, "decline": round(1 - accept, 6)},
            "basis": (f"Wade's request for #{number} (the user's decision for Wade); {holder} wears it. Judgement: a veteran "
                      f"reserve usually obliges a starting teammate who asks, often for a gift (0.6); Wade's standing on the date: {standing}. "
                      "runtime/jerseys.py")}
