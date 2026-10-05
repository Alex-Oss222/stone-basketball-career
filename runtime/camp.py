"""Training camp and preseason (docs/front_office_design.md, section 8; roadmap items 9 and 10 in part).

Camp invites fill the roster to twenty from the unsigned pool on non-guaranteed
minimums; every participant gets one camp injury draw; the seven preseason
games are played by the engine from Miami's camp rotation; the staff's depth
chart, Miami's 240-minute rotation and Wade's perimeter-defense grade are
written from the preseason box scores, with one journaled evaluation draw per
close battle; the roster is cut to fifteen by lowest value and fit; promised
roles are checked against the rotation. Chance enters only through decision
packets and game results the engine draws. Everything here reads evidence
dated on or before the career date.
"""
from datetime import date
import json
from pathlib import Path

from .kernel import POSITIONS
from .valuation import REPLACEMENT_EFF_PER_GAME, age_on, read

ROOT = Path(__file__).resolve().parents[1]
from .seasons import active as _live_season, dates as _season_dates, path as _season_path
SEASON = _live_season(ROOT)          # the live season (runtime/seasons.py): camp writes into its folder
FIRST = SEASON == "2003-04"
MIAMI = "Miami Heat"
BASE = Path(f"career/Dwyane_Wade/{SEASON}")
TEAM = BASE / "00_Team"
CAMP = BASE / "04_Training_Camp"
PRESEASON = BASE / "05_Preseason"
CAMP_ROSTER = CAMP / "camp_roster.json"
ROTATION = TEAM / "Team/Depth_Chart/rotation.json"
GRADES = TEAM / "Team/defensive_grades.json"
PROMISES = CAMP / "promise_log.json"
PRESEASON_SCHEDULE = _season_path(SEASON, "preseason_schedule")
STATS_PATH = Path("library/2003/league/nba_2002_03_player_stats.json")     # positions of last resort (first season)

# Judgement constants, named so they can be revisited.
CAMP_MAX, ROSTER_MAX = 20, 15
CUT_DAY_FALLBACK = "2003-10-27" if FIRST else _season_dates(SEASON, ROOT)["roster_cut"]   # the 2003 cut date; later seasons read the calendar
INVITE_MIN_VALUE = REPLACEMENT_EFF_PER_GAME + 1.0      # production value worth a camp look
INVITE_YOUNG_AGE = 25                                   # a young player is worth a look at replacement value
CAMP_INJURY_BASE, CAMP_INJURY_PER_YEAR_OVER_30 = 0.03, 0.005
PRESEASON_MINUTES = (26, 26, 26, 26, 26, 18, 16, 14, 12, 10, 8, 6)   # twelve actives, scaled to 240
CORE_SIZE = 8                                           # starters and the first three reserves dress every preseason game
GAME_DAY_ACTIVES = 12
SEASON_MINUTES = (34, 34, 34, 34, 34, 20, 16, 12, 10, 8, 4)                                 # scaled to 240
PRIOR_WEIGHT, CAMP_WEIGHT = 0.6, 0.4                    # the staff's score: prior value against preseason production
ROOKIE_PRIOR = {"top_ten": 9.0, "first_round": 7.0, "second_round": 5.5}   # a rookie's prior value by draft slot, before any NBA minutes (league average is about 9)
CLOSE_BATTLE = 0.10                                     # top two within this share of each other: an evaluation draw
WADE_GRADE_BASE, WADE_GRADE_LIMITS = 45, (35, 60)      # profile sections 6 and 14: tools and weak-side plays against positioning lapses
DEFENSE_POINTS_PER_TEN_GRADE = 1.0                      # grade 60 plays as +1.0 point per 100 possessions, 40 as -1.0
GUARANTEE_DATE = _season_dates(SEASON, ROOT)["guarantee"]   # a camp contract left on the roster becomes guaranteed (1999-era practice, judgement)
CAMP_WINDOW = f"{SEASON[:4]}-camp"                      # decision ids: one camp per season


def slug(name):
    return name.lower().replace("'", "").replace(".", "").replace(" ", "_")


def efficiency(line):
    return (line["pts"] + line["orb"] + line["drb"] + line["ast"] + line["stl"] + line["blk"]
            - (line["fga"] - line["fgm"]) - (line["fta"] - line["ftm"]) - line["tov"])


# -- camp roster ---------------------------------------------------------------------------------
def active_players(roster):
    return [p for p in roster["players"] if not any(w in p["status"] for w in
            ("free_agent", "renounced", "released", "traded", "signed_elsewhere", "declined", "pending", "camp", "voided", "waived", "unsigned"))]


def invite(on, front_office, market, root=ROOT):
    """Camp invitees from the unsigned pool, best fit first, to a camp of CAMP_MAX."""
    roster = front_office.roster
    active = active_players(roster)
    spots = CAMP_MAX - len(active)
    needs = front_office.needs()
    positions = front_office._positions()
    if FIRST:
        for r in read(STATS_PATH, root)["records"]:      # last resort for a player without a club listing
            if r.get("position"):
                positions.setdefault(r["bbr_id"], str(r["position"]).split("-")[0])
    else:
        from .free_agency_2004 import identity
        for b, e in identity(root).items():
            if e.get("position"):
                positions.setdefault(b, str(e["position"]).split("-")[0])
    rows = []
    for bbr, p in market.pool(on).items():
        if p["club"] == MIAMI or any(r.get("bbr_id") == bbr for r in roster["players"]):
            continue
        if market.restricted(bbr):
            continue          # a camp contract is not an offer sheet: his club's right to match would be bypassed
        if p.get("nba_seasons_before_2003_04") is None and p.get("nba_history", True):
            continue          # no recorded service: Miami cannot set the legal minimum (cba.minimum_salary)
        value, age = market.valuation.value(bbr), market.valuation.age(bbr)
        if value is None:
            continue
        if value < INVITE_MIN_VALUE and not (age is not None and age <= INVITE_YOUNG_AGE and value >= REPLACEMENT_EFF_PER_GAME):
            continue
        pos = positions.get(bbr, "SF")
        rows.append({"player": p["player"], "bbr_id": bbr, "position": pos, "age": age, "value": round(value, 2),
                     "fit": front_office.fit(pos, needs), "score": round(value * front_office.fit(pos, needs), 3),
                     "salary": market.valuation.signing_minimum(p.get("nba_seasons_before_2003_04")),
                     "years_of_service": p.get("nba_seasons_before_2003_04")})
    rows.sort(key=lambda r: -r["score"])
    return rows[:max(0, spots)]


def camp_roster(on, front_office, invitees):
    """The camp roster record: the active register plus invitees on non-guaranteed minimums."""
    players = []
    for p in active_players(front_office.roster):
        players.append({"player": p["name"], "bbr_id": p.get("bbr_id"), "positions": p["positions"], "status": p["status"],
                        "kind": "roster", "injured_through": None})
    for r in invitees:
        players.append({"player": r["player"], "bbr_id": r["bbr_id"], "positions": [r["position"]], "status": "camp_contract",
                        "kind": "invite", "contract": {"salary": r["salary"], "guaranteed": 0, "guarantee_date": GUARANTEE_DATE},
                        "value": r["value"], "fit": r["fit"], "injured_through": None})
    return {"schema_version": 1, "owner": "ai_gm", "season": SEASON, "opened": on, "status": "open",
            "purpose": "Miami's training-camp roster: the register plus invitees on non-guaranteed minimum contracts, camp injuries, and the cut.",
            "players": players, "cuts": []}


def injury_packet(player, age, window=None, day=None):
    window = window or CAMP_WINDOW
    p = CAMP_INJURY_BASE + max(0, (age or 27) - 30) * CAMP_INJURY_PER_YEAR_OVER_30
    p = round(min(0.5, p), 3)
    key = player.get("bbr_id") or slug(player["player"])
    return {"event_id": f"{window}-{key}-injury", "date": day or ("2003-09-30" if FIRST else _season_dates(SEASON, ROOT)["training_camp_opens"]),
            "question": f"Is {player['player']} hurt in training camp?", "decider": "engine (camp injury draw)",
            "options": {"healthy": round(1 - p, 3), "injured": p},
            "basis": f"Camp injury chance {CAMP_INJURY_BASE} plus {CAMP_INJURY_PER_YEAR_OVER_30} a year over 30 (age {age}); an injured player misses the preseason (judgement, docs/front_office_design.md 8)."}


# -- rotation and preseason requests ------------------------------------------------------------------
def ordered_players(camp, depth, values, on):
    """Players in rotation order: the depth chart's first at each position, then by the staff's value."""
    available = [p for p in camp["players"] if not (p.get("injured_through") and on <= p["injured_through"]) and p["status"] != "released"]
    by_name = {p["player"]: p for p in available}
    starters = []
    for pos in POSITIONS:
        for name in depth["positions"].get(pos, []):
            if name in by_name and name not in starters:
                starters.append(name)
                break
    rest = sorted((n for n in by_name if n not in starters), key=lambda n: -values.get(n, 0))
    return [by_name[n] for n in starters + rest]


def rotation_players(camp, depth, values, on, template, grades=None, game_index=0):
    """Miami's explicit `players` list for a game request: twelve actives, minutes summing to 240.

    The core (starters and the first reserves) and every signed roster player dress every game, so a
    rookie without a 2002-03 line is never rotated out by his missing production value; the remaining
    spots rotate through the camp invitees by game, so every invitee is seen in the preseason."""
    order = ordered_players(camp, depth, values, on)
    core = order[:CORE_SIZE] + [p for p in order[CORE_SIZE:] if p.get("kind") != "invite"]
    tail = [p for p in order[CORE_SIZE:] if p.get("kind") == "invite"]
    if tail:
        shift = game_index % len(tail)
        tail = tail[shift:] + tail[:shift]
    order = (core + tail)[:min(len(template), GAME_DAY_ACTIVES)]
    weights = list(template[:len(order)])
    scale = 240 / sum(weights)
    minutes = [round(w * scale, 2) for w in weights]
    minutes[0] = round(minutes[0] + 240 - sum(minutes), 2)
    out = []
    for p, m in zip(order, minutes):
        entry = {"player_id": p["player"], "position": p["positions"][0], "minutes": m, "ratings": {}}
        if p.get("bbr_id"):
            entry["bbr_id"] = p["bbr_id"]
        grade = (grades or {}).get(p["player"])
        if grade is not None:
            entry["ratings"] = {"perimeter_defense": grade}
        out.append(entry)
    return out


def miami_preseason_games(root=ROOT):
    games = read(PRESEASON_SCHEDULE, root)["games"]
    return [g for g in games if MIAMI in (g["home"], g["away"])]


def preseason_note(number, game, venue):
    from datetime import date as calendar_date
    return f"""---
type: game
status: scheduled
date: {game['date']}
opponent: {game['away'] if venue == 'home' else game['home']}
venue: {venue}
competition: preseason
cup_stage:
player_team: Miami Heat
result:
reason:
simulation_source: Railway engine (runtime/private_service.py)
event_id: {game['game_id']}
result_file: Game_{number}.result.json
---

# Preseason Game {number}

Player identity and statistics are generated here by `python scripts/update_player_reports.py`.
Decisions remain in the owning phase/week note. A scheduled game has no statistical result.
"""


def preseason_requests(camp, depth, values, root=ROOT, grades=None):
    """Write the seven preseason game notes and requests (only those not yet written)."""
    written = []
    for number, game in enumerate(miami_preseason_games(root), start=1):
        venue = "home" if game["home"] == MIAMI else "away"
        note, request = Path(root) / PRESEASON / f"Game_{number}.md", Path(root) / PRESEASON / f"Game_{number}.request.json"
        if request.exists():
            continue
        players = rotation_players(camp, depth, values, game["date"], PRESEASON_MINUTES, grades, game_index=number - 1)
        miami = {"team": MIAMI, "players": players}
        other = {"team": game["away"] if venue == "home" else game["home"], "rotation": "real"}
        # The request's venue is the home club's: "home" for an arena game (neutral sites are not in the source).
        data = {"event_id": game["game_id"], "game_date": game["date"], "game_type": "preseason", "venue": "home",
                "home": miami if venue == "home" else other, "away": other if venue == "home" else miami}
        from .game_requests import freeze, load_request
        data = freeze(data, root)                          # inputs frozen at build from the dated records (game_requests)
        request.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
        try:
            load_request(request, root)
        except Exception:
            request.unlink()
            raise
        if not note.exists():
            note.write_text(preseason_note(number, game, venue), encoding="utf-8")
        written.append(request.relative_to(root))
    return written


def preseason_results(root=ROOT):
    out = []
    for path in sorted((Path(root) / PRESEASON).glob("Game_*.result.json")):
        out.append(json.loads(path.read_text(encoding="utf-8")))
    return out


# -- evaluation ---------------------------------------------------------------------------------
def rookie_prior(player, root=ROOT):
    """A rookie's prior by his draft slot: the June 26, 2003 contract inventory's draft rights in the first season,
    the season's simulated draft after it."""
    if not FIRST:
        draft = Path(root) / f"career/Dwyane_Wade/2003-04/09_Draft/draft_{SEASON[:4]}.json"
        picks = read(draft.relative_to(root), root)["picks"] if draft.is_file() else []
        pick = next((p for p in picks if p["player"] == player), None)
        if pick is None:
            return ROOKIE_PRIOR["second_round"]
        return ROOKIE_PRIOR["top_ten" if pick["round"] == 1 and pick["pick"] <= 10 else "first_round" if pick["round"] == 1 else "second_round"]
    for club in read("library/2003/league/nba_2003_contracts.json", root)["clubs"].values():
        for pick in club.get("draft_rights", []):
            if pick.get("player") == player:
                first = pick.get("status", "").startswith("unsigned_first_round") or pick.get("status") == "under_rookie_contract"
                overall = pick.get("pick") or 99
                return ROOKIE_PRIOR["top_ten" if first and overall <= 10 else "first_round" if first else "second_round"]
    return ROOKIE_PRIOR["second_round"]


def prior_values(camp, valuation, root=ROOT):
    out = {}
    for p in camp["players"]:
        # Wade's record key is his career id (alternate history: no real Basketball-Reference id).
        key = p.get("bbr_id") or ("dwyane_wade" if p["player"] == "Dwyane Wade" else None)
        v = valuation.value(key) if key else None
        if v is None:
            v = rookie_prior(p["player"], root) if ("draft" in p["status"] or not p.get("bbr_id")) else REPLACEMENT_EFF_PER_GAME
        out[p["player"]] = v
    return out


def preseason_lines(results):
    """Per Miami player: minutes, games, efficiency, steals and blocks over the preseason."""
    totals = {}
    for r in results:
        side = "home" if r["home"] == MIAMI else "away"
        for line in r["player_stats"][side]:
            if line["seconds"] <= 0:
                continue
            t = totals.setdefault(line["player_id"], {"minutes": 0.0, "games": 0, "efficiency": 0.0, "stl": 0, "blk": 0})
            t["minutes"] += line["seconds"] / 60
            t["games"] += 1
            t["efficiency"] += efficiency(line)
            t["stl"] += line["stl"]
            t["blk"] += line["blk"]
    return totals


def staff_scores(camp, valuation, results):
    """The staff's score per player: prior value against preseason efficiency per 36 minutes (as a per-game value)."""
    priors, lines = prior_values(camp, valuation), preseason_lines(results)
    scores = {}
    for p in camp["players"]:
        name = p["player"]
        t = lines.get(name)
        if t and t["minutes"] >= 20:
            camp_value = t["efficiency"] / t["minutes"] * 30        # per 30 minutes, the scale of a starter's game
            scores[name] = round(PRIOR_WEIGHT * priors[name] + CAMP_WEIGHT * camp_value, 3)
        else:
            scores[name] = round(priors[name], 3)
    return scores, lines


def battle_packets(camp, scores, on):
    """One evaluation draw per close battle for a starting spot."""
    packets = []
    for pos in POSITIONS:
        group = sorted((p for p in camp["players"] if p["positions"][0] == pos and p["status"] != "released"), key=lambda p: -scores[p["player"]])
        if len(group) < 2:
            continue
        a, b = group[0], group[1]
        sa, sb = scores[a["player"]], scores[b["player"]]
        if sa <= 0 or (sa - sb) / sa > CLOSE_BATTLE:
            continue
        pa = round(0.5 + 0.5 * (sa - sb) / (sa * CLOSE_BATTLE) * 0.5, 3)
        packets.append({"event_id": f"{CAMP_WINDOW}-{pos.lower()}-starter", "date": on,
                        "question": f"Who starts at {pos}: {a['player']} or {b['player']}?",
                        "decider": "Miami coaching staff (evaluation draw)",
                        "options": {a["player"]: pa, b["player"]: round(1 - pa, 3)},
                        "basis": f"Staff scores {sa} and {sb} within {CLOSE_BATTLE:.0%}: the leader's edge over half the margin, drawn once (docs/front_office_design.md 8)."})
    return packets


def depth_chart_from(camp, scores, winners, on):
    """The staff's depth chart: at each position by score, the drawn winner first where a battle was drawn."""
    positions = {}
    for pos in POSITIONS:
        group = sorted((p["player"] for p in camp["players"] if p["positions"][0] == pos and p["status"] != "released"), key=lambda n: -scores[n])
        if pos in winners and winners[pos] in group:
            group.remove(winners[pos])
            group.insert(0, winners[pos])
        positions[pos] = group
    return {"schema_version": 1, "owner": "ai_gm", "as_of": on, "team": MIAMI, "status": "camp_decision", "game_ready": True,
            "basis": f"Training-camp decision on {on}: staff scores (prior value {PRIOR_WEIGHT}, preseason production {CAMP_WEIGHT}) with one evaluation draw per close battle",
            "positions": positions, "battles_drawn": winners, "unassigned_draft_rights": [], "unassigned_arrivals": [], "unavailable": [], "departed": []}


def season_rotation(camp, depth, scores, on, grades=None):
    players = rotation_players(camp, depth, scores, on, SEASON_MINUTES, grades)
    return {"schema_version": 1, "owner": "ai_gm", "as_of": on, "team": MIAMI, "total_minutes": 240,
            "purpose": "Miami's rotation for the game builder: minutes per game in rotation order; the engine's injury and foul logic changes a night's minutes.",
            "players": players}


def wade_grade(lines):
    """Keep the scouting baseline until completed defensive assignments exist.

    Stocks cannot establish screen navigation or help discipline. Existing
    dated camp decisions remain historical records and are never rewritten.
    """
    grade = WADE_GRADE_BASE
    return {"player": "Dwyane Wade", "bbr_id": None, "grade": grade, "from": None,
            "defense": round((grade - 50) / 10 * DEFENSE_POINTS_PER_TEN_GRADE, 2),
            "evidence": [f"profile sections 6 and 14: base {WADE_GRADE_BASE} (length and strength for guard matchups, weak-side blocks and deflections; "
                         f"loses cutters, leaves shooters to help, caught on screens)",
                         "No assignment-level defensive evidence; preseason steals and blocks do not change this grade."],
            "basis": f"grade 50 is an average defender; {DEFENSE_POINTS_PER_TEN_GRADE} point per 100 possessions per ten grade points (runtime/camp.py)"}


def grades_record(entries, on):
    for e in entries:
        e["from"] = on
    return {"schema_version": 1, "owner": "ai_gm", "team": MIAMI, "as_of": on,
            "purpose": ("Dated staff grades of defense for players without a DBPM record. The engine reads a grade for games on or after "
                        "its date as the player's defensive value (points per 100 possessions) and as his perimeter_defense rating; "
                        "a played game keeps the inputs it was played with."),
            "players": entries}


# -- cut and promises ------------------------------------------------------------------------------
# Register statuses of players who cannot dress for Miami: not signed, or no longer Miami's.
NOT_PLAYABLE = ("free_agent", "unsigned", "released", "waived", "traded", "renounced", "signed_elsewhere", "declined", "cut", "voided")


def playable(status):
    """A register status that lets a player dress for Miami: a signed contract Miami still holds."""
    return bool(status) and not any(word in status for word in NOT_PLAYABLE)


def cut_list(camp, scores, front_office, protected=()):
    """Players to release until the signed roster is ROSTER_MAX: non-guaranteed first, lowest score and fit first.

    Unsigned draft rights do not count toward the fifteen and are never released here: the rights stay
    Miami's. Players in `protected` (the staff's written rotation) are released last, so a cut never
    removes a player the staff has just given minutes."""
    needs = front_office.needs()
    keep = [p for p in camp["players"] if p["status"] != "released" and playable(p.get("status", "camp_contract"))]
    if len(keep) <= ROSTER_MAX:
        return []
    def rank(p):
        guaranteed = p["kind"] == "roster"
        return (p["player"] in protected, guaranteed, scores[p["player"]] * (0.5 + front_office.fit(p["positions"][0], needs)))
    ordered = sorted(keep, key=rank)
    return [p["player"] for p in ordered[:len(keep) - ROSTER_MAX]]


def promise_check(front_office, rotation, on):
    """Promised roles against the written rotation."""
    minutes = {p["player_id"]: p["minutes"] for p in rotation["players"]}
    rows = []
    for p in front_office.sheet["players"]:
        promise = p.get("promise")
        if not promise:
            continue
        got = minutes.get(p["player"], 0)
        kept = got >= promise["minutes_per_game"] * 0.85
        rows.append({"player": p["player"], "promised": promise, "rotation_minutes": got, "kept": kept, "date": on})
    return rows
