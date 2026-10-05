"""Uniform numbers on a date, club by club (identity data, never a game input).

- Real players wear their real number for the season with that club (`library/<year>/league/nba_<season>_jerseys.json`,
  Basketball-Reference team rosters). A player the simulation put on a different club keeps his number for the season
  from another club, then his numbers from earlier seasons, newest first, then his 2002-03 number
  (`nba_2003_end_of_season.json`), when it is free there.
- Within a club a number is held once: the player already there keeps it; a later arrival whose numbers are all
  taken takes the lowest number from 0 to 55 not in use (the equipment manager's choice; judgement, documented).
- The simulated Wade has no real number: his is set by his own request and, when another player holds it, that
  player's answer, an engine decision draw (`Wade_Jersey/`). After a decline Wade may choose to wait for the number
  (`Wade_Jersey/wade_choice.json`): he takes it the first date no other Miami player holds it. Until a number is
  settled he is "not assigned". A settled number stays his in later seasons; his requests and choice are searched
  from the live season back.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = Path("library/2003/league/nba_2003_end_of_season.json")
MIAMI = "Miami Heat"
WADE = "Dwyane Wade"
GONE = ("released", "traded", "signed_elsewhere", "voided", "waived", "renounced", "declined")


def _read(path, root):
    path = Path(root) / path
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def _season(root=None):
    from .seasons import active
    return active(root or ROOT)


def register_path(root=ROOT):
    return Path(f"career/Dwyane_Wade/{_season(root)}/00_Team/Team/Roster/roster.json")


def request_dirs(root=ROOT):
    """Wade's jersey folders, the live season first, then earlier seasons."""
    from .seasons import live_seasons
    live = _season(root)
    seasons = [s for s in reversed(live_seasons(root) if (Path(root) / "career/Dwyane_Wade").is_dir() else []) if s <= live] or [live]
    return [Path(f"career/Dwyane_Wade/{s}/00_Team/Team/Roster/Wade_Jersey") for s in seasons]


def _jersey_files(root):
    """The live season's jersey file, then earlier seasons', newest first."""
    from .seasons import path, previous_season
    season, out = _season(root), []
    while int(season[:4]) >= 2003:
        out.append(path(season, "jerseys"))
        season = previous_season(season)
    return out


def candidates(bbr, club, root=ROOT):
    """His numbers in order of preference for this club."""
    files = [_read(f, root).get("players", {}).get(bbr, []) for f in _jersey_files(root)]
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


def wade_number(root=ROOT):
    """(number or None, the decision that settled it or None): an accepted request, else Wade's recorded choice to wait
    for a number, once no other player on Miami's register holds it."""
    number, source = _requested_number(root)
    if number:
        return number, source
    for folder in request_dirs(root):
        choice = _read(folder / CHOICE_NAME, root)
        if choice.get("number"):
            register = _read(register_path(root), root).get("players", [])
            holders = [p for p in register if p["name"] != WADE and not any(w in (p.get("status") or "") for w in GONE)
                       and choice["number"] in candidates(p.get("bbr_id"), MIAMI, root)[:1]]
            if not holders:
                return choice["number"], CHOICE_NAME
            return None, None
    return None, None


def _requested_number(root=ROOT):
    for rel in request_dirs(root):
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


def assign(players, root=ROOT, fixed=None):
    """{key: number or None} for a club's players in tenure order: [(key, bbr, club)]. `fixed` pre-assigns keys."""
    fixed = dict(fixed or {})
    taken = {n for n in fixed.values() if n}
    out = dict(fixed)
    for key, bbr, club in players:
        if key in out:
            continue
        number = next((n for n in candidates(bbr, club, root) if n not in taken), None) if bbr else None
        if number is None:
            number = next(str(n) for n in range(0, 56) if str(n) not in taken)
        out[key] = number
        taken.add(number)
    return out


def miami_numbers(root=ROOT):
    """Miami's register on the career date: {name: number or None}; Wade only from his settled request."""
    register = _read(register_path(root), root).get("players", [])
    active = [p for p in register if not any(w in (p.get("status") or "") for w in GONE)]
    wade, _ = wade_number(root)
    fixed = {WADE: wade}
    if wade:
        holder = next((p["name"] for p in active if p["name"] != WADE and wade in candidates(p.get("bbr_id"), MIAMI, root)[:1]), None)
        if holder:
            fixed[holder] = None                                        # he gave it up: a new number below
    order = [(p["name"], p.get("bbr_id"), MIAMI) for p in active if p["name"] != WADE]
    numbers = assign([x for x in order if x[0] not in fixed or fixed[x[0]] is not None], root,
                     {k: v for k, v in fixed.items() if v})
    if wade:
        for name, value in fixed.items():
            if value is None and name != WADE:
                bbr = next(p.get("bbr_id") for p in active if p["name"] == name)
                taken = {v for v in numbers.values() if v}
                numbers[name] = next((n for n in candidates(bbr, MIAMI, root) if n not in taken and n != wade),
                                     next(str(n) for n in range(0, 56) if str(n) not in taken))
    numbers.setdefault(WADE, wade)
    return numbers


def number_for(bbr, club, root=ROOT):
    """A league card's number: Miami's from its register, others' first preference (their real club's number)."""
    if club == MIAMI:
        register = {p.get("bbr_id"): p["name"] for p in _read(register_path(root), root).get("players", [])}
        return miami_numbers(root).get(register.get(bbr))
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
