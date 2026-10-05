"""Uniform numbers on a date, club by club (identity data, never a game input).

- Real players wear their real 2003-04 number with that club (`library/2003/league/nba_2003_04_jerseys.json`,
  Basketball-Reference team rosters). A player the simulation put on a different club keeps his 2003-04 number from
  another club, then his 2002-03 number (`nba_2003_end_of_season.json`), when it is free there.
- Within a club a number is held once: the player already there keeps it; a later arrival whose numbers are all
  taken takes the lowest number from 0 to 55 not in use (the equipment manager's choice; judgement, documented).
- The simulated Wade has no real number: his is set by his own request and, when another player holds it, that
  player's answer, an engine decision draw (`Wade_Jersey/`). Until a number is settled he is "not assigned".
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEASON = "2003-04"
REAL = Path("library/2003/league/nba_2003_04_jerseys.json")
BASELINE = Path("library/2003/league/nba_2003_end_of_season.json")
REGISTER = Path(f"career/Dwyane_Wade/{SEASON}/00_Team/Team/Roster/roster.json")
WADE_REQUESTS = Path(f"career/Dwyane_Wade/{SEASON}/00_Team/Team/Roster/Wade_Jersey")
MIAMI = "Miami Heat"
WADE = "Dwyane Wade"
GONE = ("released", "traded", "signed_elsewhere", "voided", "waived", "renounced", "declined")


def _read(path, root):
    path = Path(root) / path
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def candidates(bbr, club, root=ROOT):
    """His numbers in order of preference for this club."""
    real = _read(REAL, root).get("players", {}).get(bbr, [])
    out = [r["number"].split(",")[-1].strip() for r in real if r["club"] == club]
    out += [r["number"].split(",")[-1].strip() for r in real if r["club"] != club]
    for c in _read(BASELINE, root).get("clubs", {}).values():
        for p in c["players"]:
            if p.get("bbr_id") == bbr and p.get("jersey"):
                out.append(str(p["jersey"]))
    seen = []
    for n in out:
        if n not in seen:
            seen.append(n)
    return seen


def wade_number(root=ROOT):
    """(number or None, the decision that settled it or None)."""
    folder = Path(root) / WADE_REQUESTS
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
    register = _read(REGISTER, root).get("players", [])
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
        register = {p.get("bbr_id"): p["name"] for p in _read(REGISTER, root).get("players", [])}
        return miami_numbers(root).get(register.get(bbr))
    pref = candidates(bbr, club, root)
    return pref[0] if pref else None


def request_packet(number, holder, date, standing):
    """Wade's request for a number another player holds: the holder's answer is an engine draw."""
    accept = 0.6
    return {"event_id": f"{SEASON}-wade-jersey-request-{number}", "date": date,
            "question": f"Does {holder} give jersey #{number} to Dwyane Wade?",
            "decider": f"{holder} (simulated player)",
            "options": {"accept": accept, "decline": round(1 - accept, 6)},
            "basis": (f"Wade's request for #{number} (the user's decision for Wade); {holder} wears it. Judgement: a veteran "
                      f"reserve usually obliges a starting teammate who asks, often for a gift (0.6); Wade's standing on the date: {standing}. "
                      "runtime/jerseys.py")}
