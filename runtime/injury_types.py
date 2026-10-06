"""What the injury was: a type for every injury and absence the engine draws for Miami (the user's request, December
2004 on the career clock: "where an injury happens we assign what type of injury").

The engine draws an injury's length (kernel `INJURY_LENGTHS`: day-to-day to season-ending) and a one-game absence
(`ABSENCE_PER_GAME`, illness or personal). It never named the injury. The researched sheet
`library/injuries/nba_injury_types_2003_2014.json` (56 types from 5,402 absences of NBA rotation players, 2003-04 to
2013-14) records how often each type happened and how many games it kept a player out. For each Miami injury or absence
in a closed result, from INJURY_TYPES_FROM, this module writes one engine decision packet: the types of that kind
(injuries for an injury, illnesses for an absence), each weighted by its real frequency times how well its recorded
length fits the games the engine drew (inside its middle half: 1; inside its 10th-90th percentile range: 0.4; inside its
recorded extremes: 0.1; outside: 0). The engine draws the type once, journaled, never re-rolled (AGENTS.md: where an
answer depends on chance, the engine draws it). The drawn type is recorded in `00_Team/Transactions/injury_types.json`
and on the injured list. The length stays the engine's; the type only names it.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHEET = Path("library/injuries/nba_injury_types_2003_2014.json")
MIAMI = "Miami Heat"
INJURY_TYPES_FROM = "2004-10-01"          # the 2004-05 season on (the user's request); earlier injuries stand unnamed
FIT = ((1.0, "p25", "p75"), (0.4, "min", "max"), (0.1, "fastest_recorded", "slowest_recorded"))
MIN_SHARE = 0.002                          # options below this share are dropped (the packet stays readable)


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def sheet(root=ROOT):
    return _read(Path(root) / SHEET)["injuries"]


def fit(games, g):
    """How well a type's recorded length fits `games` (FIT), 0 when outside every recorded range."""
    for weight, lo_key, hi_key in FIT:
        lo, hi = g.get(lo_key), g.get(hi_key)
        if lo is None:
            continue
        if hi is None:                         # still out when the season ended: no recorded upper bound
            hi = max(g.get("slowest_recorded") or 0, 82)
        if lo <= games <= hi:
            return weight
    return 0.0


def options(games, kind, root=ROOT):
    """{type id: probability} for an engine injury (kind 'injury') or absence (kind 'illness') of `games` games."""
    rows = [t for t in sheet(root) if t["kind"] == kind]
    weights = {t["id"]: t["cases"] * fit(games, t["games_out"]) for t in rows}
    total = sum(weights.values())
    if total <= 0:                             # nothing recorded this long: the longest types of the kind, by frequency
        longest = sorted(rows, key=lambda t: -(t["games_out"].get("slowest_recorded") or 0))[:5]
        weights = {t["id"]: t["cases"] for t in longest}
        total = sum(weights.values())
    shares = {k: v / total for k, v in weights.items() if v / total >= MIN_SHARE}
    if len(shares) < 2:                        # a decision needs two options: add the next most likely type
        extra = max((k for k in weights if k not in shares), key=lambda k: weights[k], default=None)
        if extra:
            shares[extra] = max(weights[extra] / total, MIN_SHARE)
    norm = sum(shares.values())
    out = {k: round(v / norm, 6) for k, v in sorted(shares.items())}
    last = sorted(out)[-1]
    out[last] = round(1 - sum(v for k, v in out.items() if k != last), 6)
    return out


def events(root=ROOT, season=None):
    """[(game result, entry, kind)] for every Miami injury and absence in the season's closed results."""
    from .seasons import active
    from .write_back import closed_results
    season = season or active(root)
    out = []
    for row in closed_results(Path(root), season):
        r = row["result"]
        if r.get("game_date", "") < INJURY_TYPES_FROM:
            continue
        for e in r.get("injuries") or []:
            if r.get(e.get("side")) == MIAMI:
                out.append((r, e, "injury"))
        for e in r.get("absences") or []:
            if r.get(e.get("side")) == MIAMI:
                out.append((r, e, "illness"))
    return out


def folder(season):
    return Path(f"career/Dwyane_Wade/{season}/00_Team/Transactions/Injury_Draws")


def ledger_path(season):
    return Path(f"career/Dwyane_Wade/{season}/00_Team/Transactions/injury_types.json")


def packet_for(r, e, kind, root=ROOT):
    games = e.get("games_out") or 1
    event_id = f"{r['season']}-injury-type-{r['event_id']}-{_slug(e['player_id'])}"
    opts = options(games, kind, root)
    names = {t["id"]: t["injury"] for t in sheet(root)}
    return {"event_id": event_id, "date": r["game_date"],
            "question": f"What was {e['player_id']}'s {'injury' if kind == 'injury' else 'absence'} in {r['event_id']} "
                        f"({e.get('kind')}, {games} game(s) out on the engine's draw)?",
            "decider": "engine (injury type)",
            "options": opts,
            "basis": (f"Types of kind '{kind}' from {SHEET.as_posix()}, each weighted by its real frequency (cases) times "
                      f"how well its recorded length fits {games} game(s): middle half 1, 10th-90th percentile 0.4, "
                      f"recorded extremes 0.1 (runtime/injury_types.py). Most likely: "
                      + ", ".join(f"{names.get(k, k)} {v:.0%}" for k, v in sorted(opts.items(), key=lambda x: -x[1])[:4]) + ".")}


def run(root=ROOT, season=None, write=True):
    """Write a packet for every Miami injury or absence without one; record drawn types in the ledger and on the
    injured list. Returns (packets written, types recorded)."""
    from .decisions import decision_errors
    from .seasons import active
    root = Path(root)
    season = season or active(root)
    names = {t["id"]: t for t in sheet(root)}
    written, recorded = [], []
    led_path = root / ledger_path(season)
    ledger = _read(led_path) if led_path.is_file() else {
        "schema_version": 1, "kind": "miami_injury_types", "season": season,
        "rule": __doc__.split("\n\n")[1].replace("\n", " "), "entries": []}
    known = {x["event_id"] for x in ledger["entries"]}
    for r, e, kind in events(root, season):
        p = packet_for(r, e, kind, root)
        errors = decision_errors(p)
        if errors:
            raise ValueError(f"{p['event_id']}: {'; '.join(errors)}")
        path = root / folder(season) / f"{p['event_id']}.decision.json"
        result = path.with_name(path.name.replace(".decision.json", ".decision.result.json"))
        if not path.exists():
            if write:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(p, indent=1) + "\n", encoding="utf-8")
            written.append(p["event_id"])
            continue
        if p["event_id"] in known or not result.exists():
            continue
        outcome = _read(result)["outcome"]
        t = names[outcome]
        entry = {"event_id": p["event_id"], "game": r["event_id"], "date": r["game_date"], "player": e["player_id"],
                 "engine_kind": e.get("kind"), "games_out": e.get("games_out") or 1, "type": outcome,
                 "injury": t["injury"], "body_area": t.get("body_area"), "decision": path.relative_to(root).as_posix()}
        ledger["entries"].append(entry)
        recorded.append(entry)
    if recorded and write:
        ledger["entries"].sort(key=lambda x: (x["date"], x["event_id"]))
        led_path.parent.mkdir(parents=True, exist_ok=True)
        led_path.write_text(json.dumps(ledger, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        _label_injured_list(root, season, ledger)
    return written, recorded


def _label_injured_list(root, season, ledger):
    """Name the injury on the injured-list placement it caused (the first missed game after the injury's game)."""
    path = root / f"career/Dwyane_Wade/{season}/00_Team/Transactions/injured_list.json"
    if not path.is_file():
        return
    data = _read(path)
    changed = False
    for x in ledger["entries"]:
        if x["engine_kind"] in (None, "illness or personal"):
            continue
        for p in data.get("entries", []):
            if p["player"] == x["player"] and p.get("placed", "") >= x["date"] and not p.get("injury"):
                p["injury"], p["body_area"], p["injury_type_source"] = x["injury"], x["body_area"], x["decision"]
                changed = True
                break
    if changed:
        path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def errors(root=ROOT, season=None):
    """Every Miami injury or absence from INJURY_TYPES_FROM has its packet (a type is never skipped)."""
    from .seasons import active
    root = Path(root)
    season = season or active(root)
    out = []
    for r, e, kind in events(root, season):
        p = packet_for(r, e, kind, root)
        if not (root / folder(season) / f"{p['event_id']}.decision.json").exists():
            out.append(f"{r['event_id']}: {e['player_id']}'s {kind} has no type draw "
                       f"(python scripts/injury_types.py --write)")
    return out
