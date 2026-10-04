"""Disturbed clubs replace what simulated Miami takes (option D hybrid; docs/front_office.md, Disturbed clubs).

Real clubs follow history. From REPLACEMENT_FROM, when Miami takes a player who was in a real club's
rotation (one of its ROTATION_DEPTH largest minutes on the day before), that club signs a replacement
the same day from the dated in-season free-agent pool, using the exception it actually has:

- the pool: players on the July 1, 2003 expiring list whom no real club carried in 2003-04 and whose researched
  status on the date is a healthy unsigned free agent (`nba_2003_04_unsigned_status.json`; retired, abroad and
  injured players are never signed), minus players Miami holds and earlier replacements;
- the choice: 2002-03 production value x skill fit for the club's own needs (`runtime/skill_fit.py`),
  x SAME_POSITION_BONUS at the departing player's position; the same rule for every club;
- the terms: under the cap, a room signing at his comparables price up to the room; otherwise the
  minimum exception for his years of service (1999 CBA); a club always has the minimum;
- the effect: he joins that club from the date with his 2002-03 minutes per game and games share, his previous
  minute share (rule 3 arrival).

Undisturbed clubs keep following history. Records: `career/Dwyane_Wade/<season>/League/club_replacements.json`.
"""
import json
from pathlib import Path

from .rotations import ROTATION_DEPTH, holdings_path, load_rosters, season_fraction
from .player_stats import alias

ROOT = Path(__file__).resolve().parents[1]
SEASON = "2003-04"
REPLACEMENT_FROM = "2003-12-01"
SAME_POSITION_BONUS = 1.25
DEFAULT_SERVICE_YEARS = 2


def path_for(season):
    return Path(f"career/Dwyane_Wade/{season}/League/club_replacements.json")


def read(season=SEASON, root=ROOT):
    path = Path(root) / path_for(season)
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"schema_version": 1, "kind": "club_replacements", "season": season,
            "rule": __doc__.split("\n\n", 1)[1].split("\n\nUndisturbed")[0].strip(), "entries": []}


def _present(stint, fraction):
    lo, hi = stint.get("window") or [0.0, 1.0]
    return lo <= fraction and (fraction < hi or hi >= 1.0)


def _day_before(day):
    from datetime import date, timedelta
    return (date.fromisoformat(day) - timedelta(days=1)).isoformat()


def disturbed(season=SEASON, root=ROOT):
    """Miami acquisitions from REPLACEMENT_FROM that took a player out of a real club's rotation:
    [(holding entry, club, his stint)]."""
    holdings = json.loads((Path(root) / holdings_path(season)).read_text(encoding="utf-8"))["entries"]
    rosters = load_rosters(season, root)
    out = []
    for e in holdings:
        if e["from"] < REPLACEMENT_FROM or e.get("void"):
            continue
        fraction = season_fraction(season, _day_before(e["from"]), root)
        for club, entry in rosters.items():
            present = [p for p in entry["players"] if _present(p, fraction)]
            mine = next((p for p in present if (e.get("bbr_id") and p["bbr_id"] == e["bbr_id"]) or alias(p["player_id"]) == alias(e["player"])), None)
            if mine is None:
                continue
            ranked = sorted(present, key=lambda p: -(p["minutes"] / max(1, p["games"])))[:ROTATION_DEPTH]
            if mine in ranked:
                out.append((e, club, mine))
    return out


STATUS_PATH = Path("library/2003/league/nba_2003_04_unsigned_status.json")
EXPIRING_PATH = Path("library/2003/league/nba_2003_expiring_contracts.json")
STATS_PATH = Path("library/2003/league/nba_2002_03_player_stats.json")
STATUS_FRESH_DAYS = 30               # a status snapshot is read for this long after its date (players move abroad, retire)


def pool(day, season=SEASON, root=ROOT):
    """Healthy unsigned free agents on `day`: players on the July 1, 2003 expiring list whom no real club
    carries and whose researched status on the date is unsigned_available (`nba_2003_04_unsigned_status.json`;
    retired, abroad, injured or unknown players are never signed), minus Miami's and earlier replacements.
    {bbr_id: {player_id, bbr_id, position, games, minutes (2002-03: his previous minute share)}}."""
    from .rotations import miami_holds
    root = Path(root)
    status_file = root / STATUS_PATH
    if not status_file.is_file():
        return {}
    from datetime import date, timedelta
    snapshot = json.loads(status_file.read_text(encoding="utf-8"))
    if date.fromisoformat(day) > date.fromisoformat(snapshot["as_of"]) + timedelta(days=STATUS_FRESH_DAYS):
        raise ValueError(f"the unsigned-player statuses are dated {snapshot['as_of']}; research a snapshot within "
                         f"{STATUS_FRESH_DAYS} days of {day} before a club signs from the pool")
    status = snapshot["players"]
    expiring = {p["bbr_id"]: p for p in json.loads((root / EXPIRING_PATH).read_text(encoding="utf-8"))["players"] if p.get("bbr_id")}
    stats = {r["bbr_id"]: r for r in json.loads((root / STATS_PATH).read_text(encoding="utf-8"))["records"]}
    rosters = load_rosters(season, root)
    carried = {p["bbr_id"] for entry in rosters.values() for p in entry["players"]}
    taken = set(miami_holds(season, day, root)) | {e["bbr_id"] for e in read(season, root)["entries"]}
    out = {}
    for bbr, st in status.items():
        since = st.get("since") or ""
        if st["status"] != "unsigned_available" or since[:len(day)] > day or bbr in carried or bbr in taken:
            continue
        totals = (stats.get(bbr) or {}).get("totals") or {}
        games, minutes = totals.get("games") or totals.get("g") or 0, totals.get("minutes") or totals.get("mp") or 0
        if not games or not minutes or bbr not in expiring:
            continue
        out[bbr] = {"player_id": st["player"], "bbr_id": bbr, "position": expiring[bbr].get("position") or "SF",
                    "games": int(games), "minutes": int(minutes), "club": expiring[bbr].get("former_club")}
    return out


def choose(club, departing, day, season=SEASON, root=ROOT):
    """The replacement a disturbed club signs and his terms, or None when the pool is empty."""
    from .market import Market
    from .skill_fit import SkillFit
    from .trades import Assets
    from .cba import minimum_salary
    candidates = pool(day, season, root)
    if not candidates:
        return None
    market = Market(day, root)
    assets = Assets(day, market, root)
    skills = SkillFit(root)
    rosters = load_rosters(season, root)
    fraction = season_fraction(season, day, root)
    held = [(p["bbr_id"], max(1.0, market.valuation.value(p["bbr_id"]) or 1.0))
            for p in rosters[club]["players"] if _present(p, fraction) and p["bbr_id"] != departing["bbr_id"]]
    needs = skills.needs(held)
    want = departing["position"].split("-")[0]

    def score(bbr, p):
        value = market.valuation.value(bbr) or 0.0
        same = SAME_POSITION_BONUS if p["position"].split("-")[0] == want else 1.0
        return value * skills.fit(bbr, needs) * same

    bbr, p = max(candidates.items(), key=lambda kv: (score(*kv), kv[0]))
    service = (market.players.get(bbr) or {}).get("nba_seasons_before_2003_04")
    minimum = minimum_salary(service if service is not None else DEFAULT_SERVICE_YEARS, season, root)
    payroll = assets.payroll(club) or 0
    cap = assets.cap_rules.get("salary_cap", 43840000)
    value = market.valuation.value(bbr)
    price = market.valuation.comparables_price(value) if value is not None else minimum
    if payroll < cap and cap - payroll > minimum:
        route, salary = "cap room", int(max(minimum, min(price, cap - payroll)))
    else:
        route, salary = "minimum exception", int(minimum)
    return {"club": club, "player": p["player_id"], "bbr_id": bbr, "position": p["position"], "from": day, "until": None,
            "replaces": departing["player_id"], "replaces_bbr": departing["bbr_id"],
            "terms": {"route": route, "salary_2003_04": salary, "years": 1},
            "games": p["games"], "minutes": p["minutes"], "former_club": p["club"],
            "basis": (f"best of {len(candidates)} unsigned players by 2002-03 production x skill fit "
                      f"(score {round(score(bbr, p), 3)}); payroll {payroll:,} against a {cap:,} cap")}


def replace(root=ROOT, season=SEASON, write=True):
    """Make every replacement due. Returns the new entries."""
    record = read(season, root)
    done = {e["replaces_bbr"] for e in record["entries"]}
    new = []
    for holding, club, stint in disturbed(season, root):
        if stint["bbr_id"] in done:
            continue
        entry = choose(club, stint, holding["from"], season, root)
        if entry:
            record["entries"].append(entry)
            new.append(entry)
    if new and write:
        path = Path(root) / path_for(season)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return new


def held(season, game_date, root=ROOT):
    """Replacement players on their new club on the date: excluded from every real roster (they arrive below)."""
    return frozenset(e["bbr_id"] for e in read(season, root)["entries"]
                     if e["from"] <= game_date and (e["until"] is None or game_date < e["until"]))


def arrivals(season, club, game_date, root=ROOT):
    """Roster-shaped arrivals at a disturbed club on the date (rule 3), as `real_rotation` takes them."""
    out = []
    for e in read(season, root)["entries"]:
        if e["club"] == club and e["from"] <= game_date and (e["until"] is None or game_date < e["until"]):
            start = season_fraction(season, e["from"], root)
            out.append({"player_id": e["player"], "bbr_id": e["bbr_id"], "position": e["position"], "games": e["games"],
                        "minutes": e["minutes"], "span": [0.0, 1.0], "window": [start, 1.0]})
    return tuple(out)


def replacement_errors(root=ROOT, season=SEASON):
    """A disturbed club without its replacement (python scripts/club_replacements.py --write)."""
    root = Path(root)
    if not (root / holdings_path(season)).is_file():
        return []
    try:
        done = {e["replaces_bbr"] for e in read(season, root)["entries"]}
        return [f"{club} lost {stint['player_id']} to Miami on {h['from']} and has not replaced him "
                f"(python scripts/club_replacements.py --write)" for h, club, stint in disturbed(season, root)
                if stint["bbr_id"] not in done and pool(h["from"], season, root)]
    except (OSError, KeyError, ValueError) as exc:
        return [f"cannot check club replacements: {exc}"]
