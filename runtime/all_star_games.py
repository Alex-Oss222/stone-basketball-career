"""All-Star weekend games played by the engine (roadmap 15b): the Rookie Challenge and the All-Star Game of each season.

The rosters are the season's recorded All-Star selections (`all_star.json`, `runtime/all_star.py`); nothing here
re-decides them. Each game is locked, requested, played by the engine and decided in this order, one record per season
(`Stats_and_Awards/League/<season>/all_star_games.json`), every step from evidence dated before the game and the same
rule for every player, Wade included:

* Lock (on the game's date, results through the day before; `lock`), every selection as the career knew it on the lock
  date (`award_corrections.as_of`):
  - All-Star Game: the twelve a side after the Commissioner's replacements (`all_star.rosters`, as `game_rosters`), its
    recorded five starters;
  - Rookie Challenge: the panel's nine a side as recorded (a corrected roster as corrected). The Commissioner's test
    of the All-Star Game applies: a player who played in none of his club's last two games is out, and the panel's next
    available player of his side and position group takes his place. The panel's order is recomputed by
    `all_star.rookie_challenge_order` on the step's own date (under its correction's context for a corrected roster,
    `award_corrections.replaying`), and the lock refuses when the recomputed nine differ from the recorded nine;
  - ranking, within the starters and within the reserves (all nine for the Rookie Challenge, whose top five start):
    closed regular-season Game Score per game, then points per game, then the recorded selection order;
  - minutes: the coaches' minutes by rank from the real editions before the game (`library/all_star/engine`); a roster
    that is not twelve (or nine) uses the first slots, rescaled to the game;
  - position: the one the engine used for the player in the last frozen game input of the season before the date;
  - the engine file's sha256 (`engine_sha256`): the request is frozen against that file and the engine replays the
    game from it, so validation refuses a change and `scripts/build_all_star_engine.py` never rewrites it.
* Request: Wade's games beside his note (`<season>/11_All_Star/<game>/Game_1.md`), every other game in the league's
  `All_Star/Games` folder, both with frozen inputs (`game_requests.freeze`). Each side is a neutral-court team of its
  locked players with their exhibition profiles (`all_star_engine`), rest 2, pace 1, no injury draws.
* After the game (`after`): Wade's note gets its result; the MVP is decided from the closed box by a media panel of
  MVP_PANEL voters (the Finals MVP panel's size; the award's own is unverified), lens 0.30 to 0.60, one vote each:
  production (mean z of Game Score and points among everyone who played) against the winning side (z of 1 or 0).
  Equal ballots name co-MVPs in the All-Star Game (the 2000 precedent, Duncan and O'Neal) and go to an engine draw in
  the Rookie Challenge (never shared 2000-2005). Wade's MVP is added to `awards.json` under the exhibition competition,
  so no standing, valuation, incentive or national-team rule reads it.

The results are a separate statistical record: no closed-results reader (standings, awards, rotation reviews, the
protagonist and trajectory updates, standing or valuation) reads the `11_All_Star` or `All_Star/Games` folders.

Retroactive weekends. The 2004, 2005 and 2006 weekends passed before this was built; they were locked and requested on
RETROACTIVE_ON from evidence dated before each game and carry `recorded_on`, as the 2004 All-Star selections do (the
games read no closed record of the season after their date, and nothing recorded since reads them). From the 2006-07
season the driver plays each game on its date (`scripts/all_star_day.py`).

Validation recomputes each lock from the records (`errors`). A correction of a selection step dated after the lock
(`award_corrections`) changes what the current code decides, not what the lock read: that lock stands as recorded.
"""
from __future__ import annotations

from datetime import date, timedelta
import hashlib
import json
import os
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
PLAYER = Path("career/Dwyane_Wade")
LEAGUE = PLAYER / "Stats_and_Awards/League"
WADE = "Dwyane Wade"
GAME_TYPES = ("rookie_challenge", "all_star")
NAMES = {"rookie_challenge": "Rookie Challenge", "all_star": "All-Star Game"}
FOLDERS = {"rookie_challenge": "Rookie_Challenge", "all_star": "All_Star_Game"}
SLUGS = {"rookie_challenge": "rookie-challenge", "all_star": "all-star-game"}
SIDES = {"all_star": ("East", "West"), "rookie_challenge": ("Rookies", "Sophomores")}    # (home, away) on a neutral court
FOLDER = "11_All_Star"
RECORD, PAGE = "all_star_games.json", "All_Star_Games.md"
RETROACTIVE_ON = "2006-04-19"          # the career date the 2004-2006 weekends were locked and requested
STEPS_READ = {"all_star": ("starters", "reserves", "replacements"), "rookie_challenge": ("rookie_challenge",)}
MVP_PANEL, MVP_LENS_OF = 9, "finals_mvp"           # the Finals MVP panel's size and lens (0.30 to 0.60)
MVP_NAMES = {"all_star": ("All-Star Game MVP", "ASG MVP"), "rookie_challenge": ("Rookie Challenge / Rising Stars MVP",
                                                                               "Rising Stars MVP")}


def _read(path):
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def _write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def _plus(day, n):
    return (date.fromisoformat(day) + timedelta(days=n)).isoformat()


def _long(day):
    d = date.fromisoformat(day)
    return f"{d:%B} {d.day}, {d.year}"


def event_id(game_type, day):
    """The game's only event id: validation refuses any other, so a game cannot be drawn again under a new id."""
    return f"{day}-{SLUGS[game_type]}"


def record_path(season):
    return LEAGUE / season / RECORD


def page_path(season):
    return LEAGUE / season / PAGE


def read_record(root=ROOT, season=None):
    data = _read(Path(root) / record_path(season))
    return data or {"schema_version": 1, "season": season, "kind": "all_star_games",
                    "rule": "runtime/all_star_games.py; runtime/all_star_engine.py", "games": {}}


def game_days(season, root=ROOT):
    """{game type: date} from the season's All-Star calendar, or {} for a season without one."""
    from .all_star import ctx
    c = ctx(root, season)
    if c.data is None:
        return {}
    d = c.data["dates"]
    return {"rookie_challenge": d["rookie_challenge"]["value"], "all_star": d["all_star_game"]["value"]}


def seasons_on_file(root=ROOT):
    """Seasons with an All-Star record (`all_star.json`), oldest first."""
    return sorted(p.parent.name for p in (Path(root) / LEAGUE).glob("*/all_star.json"))


def plays(game, name=WADE):
    return any(p["player"] == name for t in game["teams"].values() for p in t["players"])


def paths(season, game_type, wade, day):
    """(note or None, request, result) for a game: Wade's beside his note, any other in the league's folder."""
    if wade:
        base = PLAYER / season / FOLDER / FOLDERS[game_type]
        return base / "Game_1.md", base / "Game_1.request.json", base / "Game_1.result.json"
    base = LEAGUE / season / "All_Star" / "Games"
    eid = event_id(game_type, day)
    return None, base / f"{eid}.request.json", base / f"{eid}.result.json"


def result_of(game, root=ROOT):
    """The game's closed result, or None."""
    return _read(Path(root) / game["result"]) if game.get("result") else None


def engine_digest(root, game):
    """sha256 of the game's engine file (None without one): a locked game keeps the file its request was frozen against."""
    path = Path(root) / game["engine"]
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


# -- evidence -------------------------------------------------------------------------------------------------------
def season_rows(root, season):
    from .seasons import dates
    from .write_back import closed_results
    return closed_results(root, season, dates(season, root)["regular_season_end"])


def frozen_positions(root, season, day, wanted):
    """{bbr_id: position} the engine used for each wanted player in the last frozen game input of the season dated
    before `day` (regular-season requests, Miami's and the league slate's, latest first)."""
    root = Path(root)
    candidates = []
    for path in (root / PLAYER / season / "06_Regular_Season").rglob("Game_*.request.json"):
        data = _read(path)
        candidates.append((data["game_date"], data["event_id"], path, data))
    slate = root / LEAGUE / season / "Games"
    for path in slate.glob("*.request.json") if slate.is_dir() else []:
        candidates.append((path.name[:10], path.name, path, None))     # slate files are named by their date
    found = {}
    for day_, _, path, data in sorted(candidates, key=lambda c: (c[0], c[1]), reverse=True):
        if day_ >= day:
            continue
        data = data or _read(path)
        if "frozen" not in data or data.get("game_type") != "regular" or data["game_date"] >= day:
            continue
        for side in ("home", "away"):
            for p in data["frozen"][side]["players"]:
                bbr = (p.get("stat_profile") or {}).get("bbr_id")
                if bbr in wanted and bbr not in found:
                    found[bbr] = p["position"]
        if set(wanted) <= set(found):
            break
    return found


def rank(players, evidence):
    """Players best first: Game Score per game, then points per game, then the recorded selection order."""
    def key(item):
        i, p = item
        e = evidence.get(p["player"]) or {}
        return (-(e.get("game_score") or 0.0), -(e.get("pts") or 0.0), i)
    return [p for _, p in sorted(enumerate(players), key=key)]


def template(engine, starters, reserves):
    """Minutes for `starters` and `reserves` players: the engine file's slots by rank, the first ones used and rescaled
    (largest remainders) when a roster is not the template's size."""
    m = engine["minutes"]
    if starters > len(m["starters"]) or reserves > len(m["reserves"]):
        raise ValueError(f"a {starters}+{reserves} roster is larger than the {len(m['starters'])}+{len(m['reserves'])} minutes template")
    slots = m["starters"][:starters] + m["reserves"][:reserves]
    total = m["team_minutes"]
    if sum(slots) == total:
        return slots
    scaled = [x * total / sum(slots) for x in slots]
    whole = [int(x) for x in scaled]
    for i in sorted(range(len(scaled)), key=lambda i: (-(scaled[i] - whole[i]), i))[:total - sum(whole)]:
        whole[i] += 1
    return whole


def _available(club, aliases, games, appeared):
    """(available, reason): the Commissioner's test, a player who played in none of his club's last two games is out."""
    last = sorted(set(games.get(club, [])))[-2:]
    if last and not any(aliases & appeared[(club, d)] for d in last):
        return False, f"played in none of {club}'s last two games ({', '.join(last)})"
    return True, None


def _aliases(root, season):
    from collections import defaultdict
    from .season_awards import identities
    by_record = defaultdict(set)
    for raw, (rec, _, _) in identities(root, season).items():
        by_record[rec].add(raw)
    return by_record


def dated_steps(root, season, on):
    """The season's All-Star selection steps as the career knew them on `on` (`award_corrections.as_of`)."""
    from . import all_star
    from .award_corrections import as_of
    return [as_of(s, on) for s in all_star.read_record(root, season)["steps"]]


def corrected_since(root, season, game_type, on):
    """The steps a game's lock reads whose correction is dated after `on`: the lock read the superseded selection."""
    from . import all_star
    return [s["step"] for s in all_star.read_record(root, season)["steps"]
            if s["step"] in STEPS_READ[game_type] and (s.get("correction") or {}).get("corrected_on", "") > on]


def rookie_rosters(root, season, day, rows, evidence, known_on):
    """{side: [nine roster rows]} after the Commissioner's test, and the changes, from the step as known on `known_on`.
    Refuses when the panel's recomputed nine differ from the recorded nine."""
    from . import all_star
    from .award_corrections import replaying
    step = next(s for s in dated_steps(root, season, known_on) if s["step"] == "rookie_challenge")
    on = (step.get("correction") or {}).get("corrected_on") or step["announced_on"]
    with replaying(season, on):
        order = all_star.rookie_challenge_order(root, all_star.ctx(root, season), step["announced_on"], rows)
    games, appeared = all_star._last_games(rows, _plus(day, -1))
    by_record = _aliases(root, season)
    out, changes = {}, []
    for side, recorded in step["teams"].items():
        nine, ranked = order[side]
        names = [p["player"] for p in recorded]
        if nine != names:
            raise ValueError(f"{season} Rookie Challenge {side}: the panel's recomputed nine {nine} differ from the "
                             f"recorded {names}")
        roster, taken = [], set(names)
        for p in recorded:
            club = (evidence.get(p["player"]) or p)["team"]
            ok, reason = _available(club, by_record.get(p["player"], set()) | {p["player"]}, games, appeared)
            if ok:
                roster.append(p)
                continue
            def fits(o, same):
                if o["player"] in taken:
                    return False
                if same and p["position"] in ("G", "F", "C") and o["position"] != p["position"]:
                    return False
                club_o = (evidence.get(o["player"]) or o)["team"]
                return _available(club_o, by_record.get(o["player"], set()) | {o["player"]}, games, appeared)[0]
            pick = next((o for o in ranked if fits(o, True)), None) or next((o for o in ranked if fits(o, False)), None)
            if pick is None:
                raise ValueError(f"{season} Rookie Challenge {side}: no available replacement for {p['player']}")
            taken.add(pick["player"])
            roster.append(pick)
            changes.append({"side": side, "out": p["player"], "out_team": club, "reason": reason,
                            "replacement": pick["player"], "replacement_team": pick["team"], "position": pick["position"],
                            "panel_rank": ranked.index(pick) + 1, "ballots": pick["ballots"]})
        out[side] = roster
    return out, changes


def lock_game(root, season, game_type, on, rows=None):
    """The game's locked rotation (see the module docstring); nothing is written. `rows`: the season's closed results
    (`season_rows`), when the caller already holds them."""
    from . import all_star
    from .all_star_engine import edition, engine_path
    root = Path(root)
    day = game_days(season, root)[game_type]
    through = _plus(day, -1)
    engine = edition(game_type, day, root)
    rows = season_rows(root, season) if rows is None else rows
    evidence = all_star.pool(root, season, through, rows)
    record = all_star.read_record(root, season)
    steps = dated_steps(root, season, on)
    changes = []
    if game_type == "all_star":
        if not {"starters", "reserves", "replacements"} <= {s["step"] for s in steps}:
            raise ValueError(f"{season}: the All-Star rosters are not complete (all_star.json steps)")
        rosters = all_star.rosters({"steps": steps})
        bbr = {a["player"]: a.get("bbr_id") for a in record["all_stars"]}
        teams = {}
        for side in SIDES[game_type]:
            r = rosters[side]
            teams[side] = ([{"player": n, "bbr_id": bbr.get(n), "starter": True} for n in r["starters"]],
                           [{"player": n, "bbr_id": bbr.get(n), "starter": False} for n in r["reserves"]])
    else:
        nine, changes = rookie_rosters(root, season, day, rows, evidence, on)
        teams = {}
        for side in SIDES[game_type]:
            ordered = rank([{"player": p["player"], "bbr_id": p["bbr_id"]} for p in nine[side]], evidence)
            teams[side] = ([dict(p, starter=True) for p in ordered[:5]], [dict(p, starter=False) for p in ordered[5:]])
    positions = frozen_positions(root, season, day, {p["bbr_id"] for s, r in teams.values() for p in s + r})
    out = {}
    for side, (starters, reserves) in teams.items():
        selection = {p["player"]: i + 1 for i, p in enumerate(starters + reserves)}
        if game_type == "rookie_challenge":
            selection = {p["player"]: i + 1 for i, p in enumerate(nine[side])}
        ranked = rank(starters, evidence) + rank(reserves, evidence) if game_type == "all_star" else starters + reserves
        minutes = template(engine, len(starters), len(reserves))
        players = []
        for p, m in zip(ranked, minutes):
            e = evidence.get(p["player"]) or {}
            if not p.get("bbr_id"):
                raise ValueError(f"{season} {NAMES[game_type]}: {p['player']} has no NBA id; his profile cannot be read")
            position = positions.get(p["bbr_id"])
            if position is None:
                raise ValueError(f"{season} {NAMES[game_type]}: {p['player']} is in no frozen game input before {day}")
            players.append({"player": p["player"], "bbr_id": p["bbr_id"], "club": e.get("team"), "position": position,
                            "starter": p["starter"], "minutes": m, "games": e.get("games"),
                            "game_score": e.get("game_score"), "pts": e.get("pts"), "selection": selection[p["player"]]})
        out[side] = {"players": players}
    game = {"game_type": game_type, "name": NAMES[game_type], "date": day, "event_id": event_id(game_type, day),
            "home": SIDES[game_type][0], "away": SIDES[game_type][1], "venue": "neutral",
            "engine": engine_path(season, game_type).as_posix(), "locked_on": on, "evidence_through": through,
            "teams": out}
    if game_type == "rookie_challenge":
        game["availability"] = changes
    if on > day:
        game["recorded_on"] = on
    return game


# -- engine inputs ---------------------------------------------------------------------------------------------------
def team_inputs(data, root=ROOT):
    """Both teams' engine inputs for an All-Star weekend request (`game_requests.computed_inputs`)."""
    from .all_star_engine import edition, nba_profile, translate
    from .kernel import PlayerInput, TeamInput
    season, game_type = data["home"]["all_star"], data["game_type"]
    game = read_record(root, season)["games"].get(game_type)
    if game is None:
        raise ValueError(f"{season} {NAMES[game_type]}: not locked")
    translation = edition(game_type, data["game_date"], root)["translation"]
    teams = []
    for side in ("home", "away"):
        name = data[side]["team"]
        players = []
        for p in game["teams"][name]["players"]:
            profile = translate(nba_profile(p["bbr_id"], data["game_date"], root), translation)
            if not profile:
                raise ValueError(f"{p['player']}: no NBA profile on {data['game_date']}")
            players.append(PlayerInput(p["player"], p["position"], float(p["minutes"]), {}, profile))
        starters = tuple(p["player"] for p in game["teams"][name]["players"] if p["starter"])
        teams.append(TeamInput(name, tuple(players), starters=starters))
    return teams[0], teams[1]


def request_data(season, game):
    return {"event_id": game["event_id"], "game_date": game["date"], "game_type": game["game_type"], "venue": "neutral",
            "home": {"team": game["home"], "all_star": season}, "away": {"team": game["away"], "all_star": season}}


# -- the day ---------------------------------------------------------------------------------------------------------
def due(root, day, retroactive=False):
    """[(season, game type, date)] to lock on the day: the games dated on it; with `retroactive` (only on
    RETROACTIVE_ON), every earlier game of the seasons on file not locked yet."""
    out = []
    for season in seasons_on_file(root):
        record = read_record(root, season)
        for game_type, when in game_days(season, root).items():
            if game_type in record["games"]:
                continue
            if when == day or (retroactive and when < day):
                out.append((season, game_type, when))
    return sorted(out, key=lambda x: (x[2], GAME_TYPES.index(x[1])))


def missed(root, day):
    """Games dated before the day that were never locked (refused unless locked retroactively on RETROACTIVE_ON)."""
    return [(s, g, d) for s, g, d in due(root, day, retroactive=True) if d < day]


def lock(root, day, retroactive=False, write=True):
    """Lock and request the games due on the day. Returns summary lines."""
    from .game_requests import freeze
    root = Path(root)
    if retroactive and day != RETROACTIVE_ON:
        raise ValueError(f"the retroactive lock belongs to {RETROACTIVE_ON} only")
    late = missed(root, day)
    if late and not retroactive:
        raise ValueError("All-Star weekend games passed without a lock: " + ", ".join(f"{s} {NAMES[g]} ({d})" for s, g, d in late))
    lines, seasons = [], set()
    for season, game_type, when in due(root, day, retroactive):
        record = read_record(root, season)
        game = lock_game(root, season, game_type, day)
        note, request, result = paths(season, game_type, plays(game), when)
        game.update(request=request.as_posix(), result=result.as_posix(), note=note.as_posix() if note else None,
                    engine_sha256=engine_digest(root, game))
        record["games"][game_type] = game
        seasons.add(season)
        if write:
            _write(root / record_path(season), record)
            data = freeze(request_data(season, game), root)
            _write(root / request, data)
            if note is not None:
                write_note(root, season, game)
        changes = "; ".join(f"{c['out']} out, {c['replacement']} in" for c in game.get("availability", []))
        lines.append(f"{season} {NAMES[game_type]} ({when}) locked and requested"
                     + (f" ({changes})" if changes else "") + (" [Wade plays]" if note else ""))
    if write:
        for season in sorted(seasons):
            write_page(root, season)
    return lines


def write_note(root, season, game, result=None):
    """Wade's game note (the statistics contract's metadata: competition, player team, neutral venue)."""
    root = Path(root)
    side = next(s for s, t in game["teams"].items() if any(p["player"] == WADE for p in t["players"]))
    opponent = next(s for s in game["teams"] if s != side)
    request = Path(game["request"])
    meta = {"type": "game", "status": "played" if result else "scheduled", "date": game["date"], "opponent": opponent,
            "venue": "neutral", "competition": game["game_type"], "player_team": side, "event_id": game["event_id"],
            "request_file": request.name}
    if result:
        own = "home" if result["home"] == side else "away"
        other = "away" if own == "home" else "home"
        won = result["final_score"][own] > result["final_score"][other]
        meta["result"] = f"{'W' if won else 'L'} {result['final_score'][own]}-{result['final_score'][other]}"
        meta["result_file"] = Path(game["result"]).name
    front = "\n".join(f"{k}: {v}" for k, v in meta.items())
    page = Path(os.path.relpath(root / page_path(season), (root / game["request"]).parent)).as_posix()
    late = (f" Locked and requested on {_long(game['recorded_on'])}, after the weekend, from evidence dated before it."
            if game.get("recorded_on") else "")
    body = (f"# {season} {game['name']}: {side} vs {opponent}\n\n{_long(game['date'])}; {side} ({WADE}).\n\n"
            f"Played by the engine as an All-Star weekend exhibition ({'result in the adjacent result file' if result else 'scheduled'}); "
            f"a separate statistical record, never in NBA totals.{late} [Box score, rotation lock and MVP]({page})\n")
    note = root / game["note"]
    old = note.read_text(encoding="utf-8") if note.is_file() else ""
    block = ""
    if "<!-- player-report:start -->" in old:
        block = "\n" + old[old.index("<!-- player-report:start -->"):]
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text(f"---\n{front}\n---\n\n{body}{block}", encoding="utf-8")



def known(root, season, on):
    """The season's games as the career knew them on `on` (a retroactive game from its `recorded_on`): [{game type,
    name, date, result (home, home score, away, away score, overtimes) or None, MVP winners or None}]."""
    root = Path(root)
    record = read_record(root, season)
    out = []
    for game_type in GAME_TYPES:
        game = record["games"].get(game_type)
        if game is None:
            continue
        result = result_of(game, root) if max(game["date"], game.get("recorded_on") or "") <= on else None
        mvp = game.get("mvp")
        seen = mvp and result and max(game["date"], mvp.get("recorded_on") or "") <= on
        out.append({"game_type": game_type, "name": game["name"], "date": game["date"],
                    "result": (result["home"], result["final_score"]["home"], result["away"], result["final_score"]["away"],
                               result["overtimes"]) if result else None,
                    "mvp": list(mvp["winners"]) if seen else None})
    return out


# -- after the game --------------------------------------------------------------------------------------------------
def box_lines(result):
    """[(side name, player row)] of everyone who played."""
    return [(result[side], p) for side in ("home", "away") for p in result["player_stats"][side] if p["seconds"] > 0]


def mvp_tally(result):
    """(winners, tally rows) of the media panel from the closed box (see the module docstring)."""
    from .all_star import _z
    from .season_awards import game_score, tally_single, winners
    lines = box_lines(result)
    won = result["home"] if result["final_score"]["home"] > result["final_score"]["away"] else result["away"]
    names = [p["player_id"] for _, p in lines]
    gmsc = [game_score(p) for _, p in lines]
    production = [mean(z) for z in zip(_z(gmsc), _z([p["pts"] for _, p in lines]))]
    scored = list(zip(names, production, _z([1.0 if team == won else 0.0 for team, _ in lines])))
    votes = tally_single(MVP_LENS_OF, scored, MVP_PANEL, [1])
    by = {p["player_id"]: (team, p, g) for (team, p), g in zip(lines, gmsc)}
    rows = []
    for v in votes:
        team, p, g = by[v["player"]]
        rows.append({"player": v["player"], "team": team, "minutes": p["minutes"], "pts": p["pts"],
                     "reb": p["orb"] + p["drb"], "ast": p["ast"], "game_score": round(g, 2), "won": team == won,
                     "points": v["points"]})
    return winners(votes), rows


def decide_mvp(root, season, game, day):
    """The game's MVP decision, or (None, packet) while a Rookie Challenge tie waits for its engine draw."""
    from .decisions import equal_shares                 # the shares sum to exactly 1 (three or more)
    from .season_awards import LENS
    root = Path(root)
    result = result_of(game, root)
    top, rows = mvp_tally(result)
    name, short = MVP_NAMES[game["game_type"]]
    base = {"award": f"{game['game_type']}_mvp", "name": name, "short_name": short, "decided_on": day,
            "electorate": f"media panel of {MVP_PANEL} (the Finals MVP panel's size; the award's own is unverified)",
            "lens": list(LENS[MVP_LENS_OF]), "ballot": [1],
            "rule": "production (mean z of Game Score and points among everyone who played) against the winning side; "
                    "equal ballots: co-MVPs in the All-Star Game, an engine draw in the Rookie Challenge"}
    if day > game["date"]:
        base["recorded_on"] = day
    if len(top) > 1 and game["game_type"] == "rookie_challenge":
        eid = f"{season}-rookie-challenge-mvp"
        packet = root / LEAGUE / season / "Award_Draws" / f"{eid}.decision.json"
        drawn = packet.with_name(packet.name.replace(".decision.json", ".decision.result.json"))
        if not packet.is_file():
            _write(packet, {"event_id": eid, "date": day, "question": f"Who is the {season} Rookie Challenge MVP: "
                            + " or ".join(top) + "?", "decider": "Rookie Challenge MVP media panel (engine draw between equal ballots)",
                            "options": equal_shares(top),
                            "basis": "Equal ballots under runtime/all_star_games.py; the award was never shared 2000-2005."})
        if not drawn.is_file():
            return None, packet
        top = [_read(drawn)["outcome"]]
        base["tie_draw"] = drawn.relative_to(root).as_posix()
    return dict(base, winners=top, tally=rows[:10]), None


def record_wade(root, season, game):
    """Wade's MVP in his award register (earned honors only), dated on the game and recorded when it was decided."""
    mvp = game.get("mvp") or {}
    if WADE not in mvp.get("winners", []):
        return False
    path = Path(root) / PLAYER / "awards.json"
    data = _read(path)
    aid = f"{season}-{SLUGS[game['game_type']]}-mvp"
    if any(a["id"] == aid for a in data["awards"]):
        return False
    anchor = "all-star-game-mvp" if game["game_type"] == "all_star" else "rookie-challenge-mvp"
    data["awards"].append({"id": aid, "name": mvp["name"], "short_name": mvp["short_name"], "status": "earned",
                           "competition": game["game_type"], "season": season, "period_start": game["date"],
                           "period_end": game["date"], "awarded_on": game["date"],
                           **({"recorded_on": mvp["recorded_on"]} if mvp.get("recorded_on") else {}),
                           "source": page_path(season).relative_to(PLAYER).as_posix() + f"#{anchor}"})
    data["awards"].sort(key=lambda a: (a["awarded_on"], a["id"]))
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return True


def after(root, day):
    """After the day's games: Wade's notes get their results, each played game's MVP is decided (a Rookie Challenge
    tie waits for its engine draw), Wade's MVP is recorded, the pages are rebuilt. Returns (summary lines, pending)."""
    root = Path(root)
    lines, pending = [], []
    for season in seasons_on_file(root):
        record = read_record(root, season)
        touched = False
        for game_type in GAME_TYPES:
            game = record["games"].get(game_type)
            if not game or game["date"] > day:
                continue
            result = result_of(game, root)
            if result is None:
                continue
            if game.get("note") and "result: " not in (root / game["note"]).read_text(encoding="utf-8").split("---")[1]:
                write_note(root, season, game, result)
                score = f"{result['home']} {result['final_score']['home']}, {result['away']} {result['final_score']['away']}"
                lines.append(f"{season} {game['name']}: {score}")
            if "mvp" not in game:
                mvp, packet = decide_mvp(root, season, game, day)
                if mvp is None:
                    pending.append(packet)
                    continue
                game["mvp"] = mvp
                touched = True
                lines.append(f"{season} {game['name']} MVP: {' and '.join(mvp['winners'])}")
                if record_wade(root, season, game):
                    lines.append(f"WADE HONOR: {season} {mvp['name']}")
        if touched:
            _write(root / record_path(season), record)
        if record["games"]:
            write_page(root, season)
    return lines, pending


# -- page ------------------------------------------------------------------------------------------------------------
def _table(headers, rows):
    return ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)] + ["| " + " | ".join(str(x) for x in r) + " |" for r in rows]


def _box(result, side):
    from .season_awards import game_score
    key = "home" if result["home"] == side else "away"
    rows = []
    for p in result["player_stats"][key]:
        if p["seconds"] <= 0:
            rows.append([p["player_id"], "DNP"] + [""] * 12)
            continue
        rows.append([p["player_id"], "Yes" if p.get("started") else "", f"{p['minutes']:.1f}", p["pts"], p["orb"] + p["drb"],
                     p["ast"], p["stl"], p["blk"], p["tov"], p["pf"], f"{p['fgm']}-{p['fga']}", f"{p['tpm']}-{p['tpa']}",
                     f"{p['ftm']}-{p['fta']}", f"{game_score(p):.1f}"])
    t = result["team_stats"][key]
    rows.append(["Team", "", f"{result['game_seconds'] * 5 / 60:.0f}", t["pts"], t["orb"] + t["drb"], t["ast"], t["stl"],
                 t["blk"], t["tov"], t["pf"], f"{t['fgm']}-{t['fga']}", f"{t['tpm']}-{t['tpa']}", f"{t['ftm']}-{t['fta']}", ""])
    return _table(["Player", "Start", "MIN", "PTS", "REB", "AST", "STL", "BLK", "TOV", "PF", "FG", "3P", "FT", "GmSc"], rows)


def page(root, season, record):
    """The season's All-Star weekend games page: results, box scores, the rotation locks, the basis and the MVPs."""
    from .all_star_engine import edition
    root = Path(root)
    lines = [f"# {season} All-Star weekend games", "",
             "[All-Star selections](All_Star.md) · [NBA awards](League_Awards.md)", "",
             "Played by the engine as exhibitions (`runtime/all_star_games.py`, `runtime/all_star_engine.py`): the "
             "season's recorded selections, each player's NBA profile on the game date translated into exhibition terms, "
             "an environment from the real editions published before the game. A separate statistical record: no NBA "
             "total, standing, award or rating reads these games.", ""]
    for game_type in GAME_TYPES:
        game = record["games"].get(game_type)
        if game is None:
            continue
        name = game["name"]
        result = result_of(game, root)
        lines += [f"## {name}", ""]
        late = f"; locked and requested {_long(game['recorded_on'])}, after the weekend" if game.get("recorded_on") else ""
        lines += [f"{_long(game['date'])} · event `{game['event_id']}` · evidence through {_long(game['evidence_through'])}{late}.", ""]
        if result is None:
            lines += [f"Not played yet: the request is `{game['request']}`.", ""]
        else:
            h, a = result["home"], result["away"]
            ot = f" ({result['overtimes']} OT)" if result["overtimes"] else ""
            lines += [f"**{h} {result['final_score']['home']}, {a} {result['final_score']['away']}**{ot}.", ""]
            for side in (h, a):
                lines += [f"### {side} box score", ""] + _box(result, side) + [""]
        ranked = ("The recorded starters, then the reserves, each ranked" if game_type == "all_star" else
                  "The nine ranked (the top five start)")
        lines += [f"### {name} rotation lock", "",
                  f"{ranked} by closed regular-season Game Score per game, then points per game, then the recorded "
                  "selection order; minutes by rank from the real editions; the position the engine used in the player's "
                  "last frozen game input before the date.", ""]
        for side, team in game["teams"].items():
            lines += [f"#### {side}", ""] + _table(
                ["Player", "Club", "Pos", "Role", "Minutes", "G", "GmSc/G", "PTS/G", "Selection"],
                [[p["player"], p["club"] or "N/A", p["position"], "Starter" if p["starter"] else "Reserve", p["minutes"],
                  p["games"] if p["games"] is not None else "N/A", p["game_score"] if p["game_score"] is not None else "N/A",
                  p["pts"] if p["pts"] is not None else "N/A", p["selection"]] for p in team["players"]]) + [""]
        if game_type == "rookie_challenge":
            changes = game.get("availability", [])
            lines += [f"### {name} availability", "",
                      "The Commissioner's test: a player who played in none of his club's last two games is out; the panel's "
                      "next available player of his side and position group takes his place.", ""]
            lines += (_table(["Side", "Out", "Reason", "Replacement", "Club", "Pos", "Panel rank"],
                             [[c["side"], c["out"], c["reason"], c["replacement"], c["replacement_team"], c["position"],
                               c["panel_rank"]] for c in changes]) if changes else ["None."]) + [""]
        engine = edition(game_type, game["date"], root)
        env, tr = engine["environment"], engine["translation"]
        av = env["averages"]
        lines += [f"### {name} environment", "",
                  f"Real editions: {', '.join(env['baseline'])} ({env['unit']}): {av['points']:.1f} points, {av['fga']:.1f} FGA, "
                  f"{av['three_pa']:.1f} 3PA, {av['fta']:.1f} FTA, {av['tov']:.1f} turnovers, {av['pace']:.1f} possessions. "
                  f"Translation from {tr['anchors']} anchor lines: two-point shift {tr['shift']['two_point_pct']:+.3f}, "
                  f"three-point {tr['shift']['three_point_pct']:+.3f}, free throws {tr['shift']['free_throw_pct']:+.3f} (logit); "
                  f"three-point attempts x{tr['ratio']['three_point_attempt_rate']:.3f}, free-throw attempts "
                  f"x{tr['ratio']['free_throw_attempt_rate']:.3f}, turnovers x{tr['ratio']['turnovers_per_fga']:.3f}. "
                  f"Individual defense off (intensity {env['engine_assumptions']['defense_intensity']}); half-court "
                  f"possession seconds x{env['engine_assumptions']['possession_seconds_factor']:.2f}. Source: `{game['engine']}`.", ""]
        mvp = game.get("mvp")
        lines += [f"### {name} MVP", ""]
        if not mvp:
            lines += ["Not decided yet.", ""]
        else:
            late = f", recorded {_long(mvp['recorded_on'])}" if mvp.get("recorded_on") else ""
            draw = f" An engine draw settled equal ballots (`{mvp['tie_draw']}`)." if mvp.get("tie_draw") else ""
            lines += [f"**{' and '.join(mvp['winners'])}** ({mvp['electorate']}, lens {mvp['lens'][0]:.2f} to "
                      f"{mvp['lens'][1]:.2f}; decided {_long(mvp['decided_on'])}{late}).{draw}", ""]
            lines += _table(["Player", "Team", "MIN", "PTS", "REB", "AST", "GmSc", "Won", "Votes"],
                            [[r["player"], r["team"], f"{r['minutes']:.1f}", r["pts"], r["reb"], r["ast"], r["game_score"],
                              "Yes" if r["won"] else "", r["points"]] for r in mvp["tally"]]) + [""]
    lines += ["Rules and method: `runtime/all_star_games.py`; engine inputs `runtime/all_star_engine.py`; research "
              "`library/all_star/`.", ""]
    return "\n".join(lines)


def write_page(root, season):
    root = Path(root)
    record = read_record(root, season)
    (root / page_path(season)).write_text(page(root, season, record), encoding="utf-8")


# -- validation ------------------------------------------------------------------------------------------------------
def due_on(game_date):
    """The career date by which a game must be locked and requested: its date, or RETROACTIVE_ON for a weekend that
    passed before the engine played them. Past it, the game must also have its result and MVP."""
    return max(game_date, RETROACTIVE_ON)


def errors(root=ROOT):
    """Every game due by the clock is locked and requested at its one event id and path; past its due date it is played
    and decided; its engine file is the one it was locked with; the lock still reproduces from the records (unless a
    correction dated after it changed a step it read); Wade's MVP is in awards.json; the page is current; and no other
    request carries an exhibition game type."""
    from .all_star_engine import is_exhibition
    from .game_requests import find_requests
    from .write_back import clock
    root = Path(root)
    now = clock(root)
    out = []
    known = set()
    for season in seasons_on_file(root):
        record = read_record(root, season)
        rel = record_path(season).as_posix()
        rows = None
        for game_type, day in game_days(season, root).items():
            game = record["games"].get(game_type)
            if game is None:
                if now >= due_on(day):
                    out.append(f"{rel}: the {season} {NAMES[game_type]} ({day}) is not locked (python scripts/all_star_day.py)")
                continue
            if game["event_id"] != event_id(game_type, day) or game["date"] != day:
                out.append(f"{rel}: {game_type} must be event {event_id(game_type, day)} on {day}")
            note, request, result = paths(season, game_type, plays(game), day)
            if game.get("request") != request.as_posix() or game.get("result") != result.as_posix():
                out.append(f"{rel}: {game_type} request or result is not at {request.as_posix()}")
            known.add(request.as_posix())
            if game.get("engine_sha256") != engine_digest(root, game):
                out.append(f"{game['engine']}: not the engine file the {season} {NAMES[game_type]} was locked with "
                           "(its request was frozen against it; scripts/build_all_star_engine.py leaves a locked game's file)")
            if not (root / request).is_file():
                out.append(f"{request.as_posix()}: missing request for the locked {season} {NAMES[game_type]}")
            if note is not None and not (root / note).is_file():
                out.append(f"{note.as_posix()}: missing Wade's game note")
            played = (root / result).is_file()
            if now > due_on(day) and not played:
                out.append(f"{rel}: the {season} {NAMES[game_type]} ({day}) has no result (python scripts/play_games.py)")
            if played and "mvp" not in game:
                out.append(f"{rel}: the {season} {NAMES[game_type]} MVP is not decided (python scripts/all_star_day.py --after)")
            if WADE in (game.get("mvp") or {}).get("winners", []):
                have = {a["id"] for a in _read(root / PLAYER / "awards.json")["awards"]}
                if f"{season}-{SLUGS[game_type]}-mvp" not in have:
                    out.append(f"awards.json: Wade's {season} {NAMES[game_type]} MVP is not recorded")
            if corrected_since(root, season, game_type, game["locked_on"]):
                continue                      # the lock read the selection known on its date; it stands as recorded
            try:
                rows = rows if rows is not None else season_rows(root, season)
                fresh = lock_game(root, season, game_type, game["locked_on"], rows)
                if fresh != {k: game.get(k) for k in fresh}:
                    out.append(f"{rel}: the {game_type} lock no longer reproduces from the records")
            except (OSError, KeyError, ValueError) as exc:
                out.append(f"{rel}: the {game_type} lock cannot be recomputed: {exc}")
        if record["games"]:
            path = root / page_path(season)
            if not path.is_file() or path.read_text(encoding="utf-8") != page(root, season, record):
                out.append(f"{page_path(season).as_posix()}: stale (python scripts/all_star_day.py --after {now})")
    for path in find_requests(root):
        data = _read(path)
        if is_exhibition(data.get("game_type")) and path.relative_to(root).as_posix() not in known:
            out.append(f"{path.relative_to(root)}: an All-Star weekend request that no locked game names")
    return out
