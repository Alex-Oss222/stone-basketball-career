"""National-team tournaments under FIBA rules: selection, rosters, every game, standings, bracket, awards.

The user's premises (December 31, 2004 on the career clock; `career/Dwyane_Wade/National_Team/wade_standing_rule.json`):

* USA Basketball's roster is chosen by a simulated committee: the USA-eligible NBA players ranked by their closed
  simulated season, with positional needs, the same rule for every player (`committee`). Each invitee's answer is an
  engine decision draw; Wade's is his own standing rule (accept unless injured), so no invitation stops the clock.
* Every other team plays its real roster for the edition (world data, like the real NBA clubs' rosters).
* The engine plays every game of the tournament: groups, knockout bracket and classification games.

Nothing reads the event's own real results. A tournament's pipeline record (`FIBA/<family>/<edition>/tournament.json`)
holds the dated selections, the locked rosters, each game's resolved teams and event id, and the engine draws that
settled ties; results come only from the engine's closed games. Days run in order through `day(date)`
(`scripts/national_day.py`, called by `scripts/advance.py`): selection on the committee's date, rosters locked the day
before the first game, then each game day's requests once both teams are known.
"""
from collections import defaultdict
from datetime import date, timedelta
import json
from pathlib import Path

from .fiba_tournament import apply_draws, group_table, resolve_slot

ROOT = Path(__file__).resolve().parents[1]
PLAYER = Path("career/Dwyane_Wade")
WORLD = PLAYER / "FIBA"                       # every tournament's own records (all teams, all games)
WADE = "Dwyane Wade"
WADE_BBR = "wadedw01"
USA = "United States"

# The coach's minutes by rank in his twelve (40-minute games; 200 minutes), a FIBA rotation's usual shape (judgement).
MINUTES_BY_RANK = (32, 30, 28, 26, 24, 20, 16, 10, 6, 4, 2, 2)
# USA committee (judgement, recorded with every selection): positional needs of a twelve, evidence weights.
QUOTAS = {"G": 4, "F": 4, "C": 2}                # at least this many by group; the rest go to the best available
HONOR_BONUS = {"Most Valuable Player": 4.0, "All-NBA First Team": 3.0, "All-NBA Second Team": 2.0,
               "All-NBA Third Team": 1.5, "All-Star": 1.0}
ACCEPT_CHANCE = 0.7                              # an invitee's chance to accept (engine draw; judgement)
FULL_GAMES = 70                                  # games for full weight of a season's per-game production
DEFAULT_SELECTION_LEAD_DAYS = 30                 # selection date when the edition gives none
GROUP_OF = {"PG": "G", "SG": "G", "G": "G", "G-F": "G", "SF": "F", "PF": "F", "F": "F", "F-G": "F", "F-C": "F",
            "C": "C", "C-F": "C"}


# -- editions -------------------------------------------------------------------------------------------------------
def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def _v(x):
    """A sourced value's value ({"value", "status", "source"} or a bare value)."""
    return x.get("value") if isinstance(x, dict) and "value" in x else x


def editions(root=ROOT):
    """{edition id: normalized edition} for every engine-ready edition (`library/fiba/engine/<id>.json` built by
    scripts/build_fiba_engine.py, which normalizes the researched files)."""
    folder = Path(root) / "library/fiba/engine"
    out = {}
    for path in sorted(folder.glob("*.json")) if folder.is_dir() else []:
        data = _read(path)
        out[data["edition_id"]] = data
    return out


def edition_for(day, root=ROOT):
    """The edition whose pipeline window (selection to last game) contains the day, or None."""
    for e in editions(root).values():
        if selection_date(e) <= day <= e["last_game"]:
            return e
    return None


def selection_date(e):
    return e.get("usa", {}).get("selection_date") or (
        date.fromisoformat(e["first_game"]) - timedelta(days=DEFAULT_SELECTION_LEAD_DAYS)).isoformat()


def folder(e):
    return WORLD / e["family"] / e["edition"]


def record_path(e):
    return folder(e) / "tournament.json"


def read_record(e, root=ROOT):
    path = Path(root) / record_path(e)
    return _read(path) if path.is_file() else None


def new_record(e):
    return {"schema_version": 1, "kind": "fiba_tournament_record", "edition_id": e["edition_id"],
            "family": e["family"], "edition": e["edition"], "name": e["name"], "game_type": e["game_type"],
            "rules": "runtime/national.py; runtime/fiba_tournament.py; runtime/national_engine.py",
            "selection": None, "rosters": None, "games": {}, "draws": {}, "awards": None, "closed": False}


# -- the field ------------------------------------------------------------------------------------------------------
def final_ranking(e, rec, root=ROOT):
    """A closed edition's final places, best first: the medal and classification games, then a second group round's
    table, then the remaining teams by their group place and record (ties of the last places: alphabetical)."""
    closed = results(e, rec, root)
    placed = []
    def outcome(stage):
        g = next((x for x in rec["games"].values() if x["stage"] == stage), None)
        if not g or int(g["number"]) not in closed:
            return []
        r = closed[int(g["number"])]
        won = r["home"] if r["home_score"] > r["away_score"] else r["away"]
        return [won, r["away"] if won == r["home"] else r["home"]]
    for stage in ("final", "third_place", "fifth_place", "seventh_place"):
        placed += [t for t in outcome(stage) if t not in placed]
    states, done = group_states(e, rec, closed)
    for group in reversed(list(rec["groups"])):           # later group rounds first
        for row in done.get(group) or []:
            if row["team"] not in placed:
                placed.append(row["team"])
    rest = sorted({t for g in rec["games"].values() for t in (g.get("home"), g.get("away")) if t} - set(placed))
    return placed + rest


def resolve_field(e, rec, root=ROOT):
    """Fill places earned in earlier simulated editions (`e["qualification"]`): each source edition's final ranking,
    less excluded teams, gives its places in order; the k-th simulated qualifier takes the k-th real slot's group place
    (the real team is only a slot label). A wildcard stays with its real recipient unless he qualified on court, when it
    passes to the best-placed team of the same source that did not. Teams without a real roster for this edition play
    their latest real roster from an earlier edition."""
    rec["groups"] = {k: dict(v, teams=list(v["teams"])) for k, v in e["groups"].items()}
    rec["games"] = {str(g["number"]): dict(g) for g in e["games"]}
    replaced = {}
    for q in e.get("qualification", []):
        source = editions(root)[q["source"]]
        srec = read_record(source, root)
        if not srec or not srec.get("closed"):
            raise ValueError(f"{e['edition_id']}: {q['source']} must close before its places are filled")
        ranking = [t for t in final_ranking(source, srec, root) if t not in q.get("exclude", [])]
        ranks = q.get("ranks") or list(range(1, len(q["slots"]) + 1))
        qualified = [ranking[r - 1] for r in ranks]
        for slot, team in zip(q["slots"], qualified):
            replaced[slot] = team
        for wild in q.get("wildcards", []):
            if wild in qualified:
                replaced[wild] = next(t for t in ranking if t not in qualified and t not in replaced.values())
    def sub(team):
        return replaced.get(team, team)
    for grp in rec["groups"].values():
        grp["teams"] = [sub(t) for t in grp["teams"]]
    for g in rec["games"].values():
        for side in ("home", "away"):
            if g.get(side):
                g[side] = sub(g[side])
    rec["field"] = {"replaced": {k: v for k, v in replaced.items() if k != v},
                    "rule": "runtime/national.resolve_field: simulated qualifiers take the real slots in order"}
    rec["roster_sources"] = {}
    for team in sorted({t for grp in rec["groups"].values() for t in grp["teams"] if t in e["rosters"] or t}):
        if (team in e["rosters"] and e["rosters"][team]["players"]) or not team or team[-1:].isdigit():
            continue
        if team == USA and e["usa"]["selection"] == "committee":
            continue                                   # the committee picks the USA's twelve
        rec["roster_sources"][team] = latest_roster(team, e, root)


def latest_roster(team, e, root=ROOT):
    """The team's real roster from the latest earlier edition that has one (a simulated qualifier the real event
    did not include)."""
    best = None
    for other in editions(root).values():
        if other["last_game"] < e["first_game"] and team in other["rosters"] and other["rosters"][team]["players"]:
            if best is None or other["last_game"] > best["last_game"]:
                best = other
    if best is None:
        raise ValueError(f"{team} has no real roster for {e['name']} or any earlier edition")
    return best["edition_id"]


# -- USA committee --------------------------------------------------------------------------------------------------
def non_usa(root=ROOT):
    """bbr ids of NBA players who are not eligible for the USA (`library/fiba/nba_player_nationality.json`)."""
    path = Path(root) / "library/fiba/nba_player_nationality.json"
    if not path.is_file():
        raise ValueError("library/fiba/nba_player_nationality.json is missing; the committee cannot tell who is eligible")
    data = _read(path)
    players = data.get("players", data)
    out = {k for k in players if k not in ("schema_version", "kind", "special_cases", "research", "sources")}
    for k in (data.get("special_cases") or {}):
        case = data["special_cases"][k]
        if (_v(case.get("national_team")) or USA) != USA:
            out.add(k)
    return out


def _honors(root, season):
    """{record name: bonus} from the closed season's award records (season awards and All-Star selections)."""
    from .season_awards import honors
    out = defaultdict(float)
    league = Path(root) / PLAYER / "Stats_and_Awards/League" / season
    awards = league / "season_awards.json"
    if awards.is_file():
        for decision in _read(awards).get("decisions", []):
            for player, name, _ in honors(decision):
                out[player] += HONOR_BONUS.get(name, 0.0)
    star = league / "all_star.json"
    if star.is_file():
        for row in _read(star).get("all_stars", []):
            out[row.get("player")] += HONOR_BONUS["All-Star"]
    return out


def committee_board(e, root=ROOT):
    """The committee's ranked board on the selection date: every USA-eligible player of the ability season, with his
    closed-season evidence. Score: durable Game Score per game (per game, scaled by games up to FULL_GAMES) plus an
    honors bonus (MVP, All-NBA, All-Star)."""
    from .era import ability_season
    from .season_awards import identities, season_lines
    from .seasons import dates
    from .write_back import closed_results
    season = ability_season(selection_date(e))
    end = dates(season, root)["regular_season_end"]
    players, _ = season_lines(closed_results(root, season, end), end)
    ids = identities(root, season)
    barred = non_usa(root) | other_rosters(e)
    honors = _honors(root, season)
    board = []
    for name, t in players.items():
        record_name, bbr, group = ids.get(name, (name, None, None))
        if name == WADE or record_name == WADE:
            bbr = WADE_BBR
        if not bbr or bbr in barred or not t["games"]:
            continue
        g = t["games"]
        score = t["gmsc"] / g * min(1.0, g / FULL_GAMES) + honors.get(record_name, 0.0)
        board.append({"player": record_name, "bbr_id": bbr, "group": group or "F", "games": int(g),
                      "game_score": round(t["gmsc"] / g, 2), "honors": honors.get(record_name, 0.0),
                      "score": round(score, 3), "club": t["_club"]})
    board.sort(key=lambda r: (-r["score"], r["player"]))
    return board, season


def other_rosters(e):
    """bbr ids on any other team's real roster for the edition (a player who represents another country)."""
    return {p.get("bbr_id") for team, roster in e["rosters"].items() if team != USA for p in roster["players"]
            if p.get("bbr_id")}


def wade_available(day, root=ROOT):
    """Wade's standing rule: he accepts unless injured on the day (Miami's injured list, `runtime/roster_moves.py`)."""
    rule = Path(root) / PLAYER / "National_Team/wade_standing_rule.json"
    if not rule.is_file():
        return None                              # no rule: the invitation would need his answer
    if _read(rule)["rule"] != "accept_unless_injured":
        return False
    try:
        from .injuries import paused
        if paused(day):
            return True                          # the injury pause: every player healed (the user's premise)
        from .roster_moves import ledger, list_on
        return all(e.get("player") != WADE or e.get("reason", "").startswith("reserve")      # a healthy reserve is not hurt
                   for e in list_on(ledger(root), day))
    except (ImportError, OSError, KeyError):
        return True


def invite_order(board):
    """Invitation order: the best player in each positional need first until each quota is met, then the best left."""
    order, need = [], dict(QUOTAS)
    for row in board:
        if need.get(row["group"], 0) > 0:
            order.append(row)
            need[row["group"]] -= 1
    order += [r for r in board if r not in order]
    return order


def select_usa(e, day, rec, root=ROOT):
    """Run the committee on its date: invitations in order, each answered by an engine draw (Wade by his standing rule),
    until twelve accept. Returns the packets still waiting to be drawn."""
    sel = rec.get("selection") or {}
    if sel.get("final"):
        return []
    if not sel:
        board, season = committee_board(e, root)
        sel = {"announced_on": day, "ability_season": season, "rule": {
            "score": "closed-season Game Score per game x min(1, games/70) + honors bonus " + json.dumps(HONOR_BONUS),
            "quotas": QUOTAS, "accept_chance": ACCEPT_CHANCE, "wade": "standing rule: accept unless injured",
            "eligibility": "library/fiba/nba_player_nationality.json; players on another country's real roster excluded"},
            "board": board[:40], "invitations": [], "final": None}
        rec["selection"] = sel
    pending = []
    accepted = [i for i in sel["invitations"] if i["answer"] == "accept"]
    asked = {i["bbr_id"] for i in sel["invitations"]}
    for row in invite_order(sel["board"]):
        if len(accepted) >= 12:
            break
        if row["bbr_id"] in asked:
            continue
        if row["bbr_id"] == WADE_BBR:
            ok = wade_available(day, root)
            if ok is None:
                raise ValueError("Wade has no standing rule for national-team invitations")
            answer = "accept" if ok else "decline"
            inv = dict(row, answer=answer, basis="Wade's standing rule (career/Dwyane_Wade/National_Team/wade_standing_rule.json)")
        else:
            event_id = f"fiba-{e['slug']}-invite-{row['bbr_id']}"
            packet, outcome = _draw(root, e, event_id, day, f"Does {row['player']} accept USA Basketball's invitation "
                                    f"for {e['name']}?", {"accept": ACCEPT_CHANCE, "decline": round(1 - ACCEPT_CHANCE, 6)})
            if outcome is None:
                pending.append(packet)
                break                                 # one answer at a time: the next invitation waits for it
            inv = dict(row, answer=outcome, draw=str(packet.relative_to(root)))
        sel["invitations"].append(inv)
        asked.add(row["bbr_id"])
        if inv["answer"] == "accept":
            accepted.append(inv)
    if len(accepted) >= 12 or (not pending and len(asked) >= len(sel["board"])):
        sel["final"] = [{"player": i["player"], "bbr_id": i["bbr_id"], "group": i["group"]} for i in accepted[:12]]
    return pending


def _draw(root, e, event_id, day, question, options):
    packet = Path(root) / folder(e) / "Draws" / f"{event_id}.decision.json"
    result = packet.with_name(packet.name.replace(".decision.json", ".decision.result.json"))
    if not packet.is_file():
        _write(packet, {"event_id": event_id, "date": day, "question": question, "options": options,
                        "decider": "engine draw (runtime/national.py)", "basis": "runtime/national.py"})
    if not result.is_file():
        return packet, None
    return packet, _read(result)["outcome"]


# -- rosters and team inputs ----------------------------------------------------------------------------------------
def lock_rosters(e, rec, day, root=ROOT):
    """The day before the first game: every team's twelve with each player's identity, profile key and the coach's
    trust (expected minutes on a 40-minute scale: an NBA player's minutes per game in his closed simulated season,
    a FIBA player's minutes per game in the tournaments behind his profile; 5 for a player with neither)."""
    if rec.get("rosters"):
        return
    from .era import ability_season
    from .national_engine import edition_on
    trust_fiba = edition_on(e["first_game"], root).get("minutes", {})
    nba_minutes = _nba_minutes(ability_season(e["first_game"]), root)
    rosters = {}
    field = sorted({t for grp in rec["groups"].values() for t in grp["teams"] if not (len(t) <= 3 and t[-1:].isdigit())})
    for team in field:
        source = rec.get("roster_sources", {}).get(team)
        roster = editions(root)[source]["rosters"][team] if source else e["rosters"].get(team, {"coach": None, "players": []})
        if team == USA and e["usa"]["selection"] == "committee" and (rec.get("selection") or {}).get("final"):
            players = [{"player": p["player"], "bbr_id": p["bbr_id"], "position": _position(p["bbr_id"], p.get("group"), root)}
                       for p in rec["selection"]["final"]]
        else:
            from .national_engine import nba_profile
            players = []
            for p in roster["players"]:
                # An NBA player of the ability season plays on his translated NBA profile; anyone else (an NBA id
                # without an NBA season behind it included) on his FIBA profile.
                nba = bool(p.get("bbr_id")) and bool(nba_profile(p["name"], p["bbr_id"], e["first_game"], root))
                players.append({"player": p["name"], "bbr_id": p["bbr_id"] if nba else None,
                                "fiba_key": None if nba else p["fiba_key"], "position": _fiba_position(p.get("position"))})
        for p in players:
            if p.get("bbr_id"):
                p["trust"] = round(nba_minutes.get(p["bbr_id"], 5.0 * 48 / 40) * 40 / 48, 1)
            else:
                p["trust"] = round(trust_fiba.get(p["fiba_key"], 5.0), 1)
        rosters[team] = {"coach": roster.get("coach"), "players": players}
    rec["rosters"] = rosters
    rec["rosters_locked_on"] = day


def _nba_minutes(season, root):
    """{bbr_id: minutes per game} in the season's closed simulated regular season."""
    from .season_awards import identities, season_lines
    from .seasons import dates
    from .write_back import closed_results
    end = dates(season, root)["regular_season_end"]
    players, _ = season_lines(closed_results(root, season, end), end)
    ids = identities(root, season)
    out = {}
    for name, t in players.items():
        bbr = WADE_BBR if name == WADE else ids.get(name, (name, None, None))[1]
        if bbr and t["games"]:
            out[bbr] = t["minutes"] / t["games"]
    return out


def _fiba_position(text):
    """A roster's position text to the engine's five positions (G, F, C families; judgement where FIBA lists only G/F/C)."""
    t = (text or "F").upper().replace(" ", "")
    return {"PG": "PG", "SG": "SG", "G": "SG", "SF": "SF", "F": "SF", "PF": "PF", "C": "C", "G/F": "SF", "F/G": "SF",
            "F/C": "PF", "C/F": "C", "GF": "SF", "FC": "PF"}.get(t.split("-")[0], "SF")


def _position(bbr, group, root):
    registry = _read(Path(root) / PLAYER / "Stats_and_Awards/League/player_registry.json")
    rows = registry["players"] if isinstance(registry, dict) else registry
    pos = next((r.get("position") for r in rows if r.get("bbr_id") == bbr), None)
    if bbr == WADE_BBR:
        pos = "SG"
    first = (pos or "").split("-")[0]
    return first if first in ("PG", "SG", "SF", "PF", "C") else {"G": "SG", "F": "SF", "C": "C"}.get(group or "F", "SF")


def rotation(players):
    """The coach's twelve in rank order of his trust (locked with the rosters), with MINUTES_BY_RANK."""
    ranked = sorted(players, key=lambda p: (-p["trust"], p["player"]))[:len(MINUTES_BY_RANK)]
    minutes = list(MINUTES_BY_RANK[:len(ranked)])
    short = sum(MINUTES_BY_RANK) - sum(minutes)          # a team with fewer than twelve spreads the rest, at most 40 each
    while short > 1e-9:
        room = [i for i, m in enumerate(minutes) if m < 40]
        if not room:
            break
        give = short / len(room)
        for i in room:
            add = min(give, 40 - minutes[i])
            minutes[i] += add
            short -= add
    return [dict(p, minutes=round(m, 4)) for p, m in zip(ranked, minutes)]


def team_inputs(data, root=ROOT):
    """Both teams' engine inputs for a national request (`game_requests.computed_inputs`)."""
    from .kernel import PlayerInput, TeamInput
    from .national_engine import expected_profile
    e = editions(root)[data["home"]["national"]]
    rec = read_record(e, root)
    if rec is None or not rec.get("rosters"):
        raise ValueError(f"{e['edition_id']}: rosters are not locked")
    teams = []
    for side in ("home", "away"):
        name = data[side]["team"]
        roster = rec["rosters"][name]["players"]
        rotation_rows = rotation(roster)
        players = []
        for p in rotation_rows:
            stub = {"bbr_id": p["bbr_id"]} if p.get("bbr_id") else {"fiba_key": p["fiba_key"]}
            profile = expected_profile(p["player"], stub, data["game_date"], root)
            players.append(PlayerInput(p["player"], p["position"], float(p["minutes"]), {}, profile))
        teams.append(TeamInput(name, tuple(players), rest_days=_rest(e, rec, name, data["game_date"])))
    return teams[0], teams[1]


def _rest(e, rec, team, day):
    """Days off before this game (the kernel's back-to-back fatigue), from the team's previous tournament game."""
    before = [g["date"] for g in rec["games"].values() if team in (g.get("home"), g.get("away")) and g["date"] < day]
    if not before:
        return 2
    return min(10, (date.fromisoformat(day) - date.fromisoformat(max(before))).days - 1)


# -- games, standings and bracket ------------------------------------------------------------------------------------
def event_id(e, number):
    return f"fiba-{e['slug']}-g{int(number):02d}"


def wade_plays(rec):
    return any(p.get("bbr_id") == WADE_BBR for p in ((rec.get("rosters") or {}).get(USA, {}).get("players") or []))


def game_paths(e, rec, g, root=ROOT):
    """(note or None, request, result) for a game: Wade's games beside his note in the National_Team record, every
    other game in the tournament's Games folder."""
    eid = event_id(e, g["number"])
    if wade_plays(rec) and USA in (g.get("home"), g.get("away")):
        n = 1 + sorted(x["number"] for x in rec["games"].values() if USA in (x.get("home"), x.get("away"))).index(g["number"])
        base = Path(root) / PLAYER / "National_Team" / e["family"] / e["edition"] / e["stage"] / _round_folder(g["stage"])
        return base / f"Game_{n}.md", base / f"Game_{n}.request.json", base / f"Game_{n}.result.json"
    base = Path(root) / folder(e) / "Games"
    return None, base / f"{eid}.request.json", base / f"{eid}.result.json"


def _round_folder(stage):
    return {"round_of_16": "Round_of_16", "quarterfinal": "Quarterfinals", "semifinal": "Semifinals",
            "final": "Final", "third_place": "Third_Place"}.get(stage, "Group_Phase" if stage.startswith("group")
                                                                  else "Classification")


def results(e, rec, root=ROOT):
    """{game number: closed result summary} for every played game."""
    out = {}
    for number, g in rec["games"].items():
        if not g.get("home") or not g.get("away"):
            continue
        _, _, result = game_paths(e, rec, g, root)
        if result.is_file():
            r = _read(result)
            out[int(number)] = {"home": r["home"], "away": r["away"], "home_score": r["final_score"]["home"],
                                "away_score": r["final_score"]["away"], "stage": g["stage"], "date": g["date"],
                                "event_id": r["event_id"], "result": str(result.relative_to(root))}
    return out


def _group_teams(e, group, done):
    """A group's teams: named teams, or slots ("A1") resolved from earlier completed tables; None until all known."""
    teams = []
    for slot in e["_groups"][group]["teams"]:
        if not (len(slot) <= 3 and slot[-1:].isdigit()):
            teams.append(slot)
            continue
        team = resolve_slot(slot, done, {}, {})
        if team is None:
            return None
        teams.append(team)
    return teams


def _group_games(e, group, teams, closed):
    """The group's own closed games, plus results carried over from earlier groups between teams now in it."""
    g = e["_groups"][group]
    own = [r for r in closed.values() if r["stage"] == g["stage"]]
    carried = [r for r in closed.values() for src in g.get("carry_from", ())
               if r["stage"] == e["_groups"][src]["stage"] and r["home"] in teams and r["away"] in teams]
    return own, carried


def group_states(e, rec, closed):
    """{group: (teams or None, all games counted, complete?)} in the edition's group order."""
    e = dict(e, _groups=rec.get("groups") or e["groups"])
    done, states = {}, {}
    for group, g in e["_groups"].items():
        teams = _group_teams(e, group, done)
        if teams is None:
            states[group] = (None, [], False)
            continue
        own, carried = _group_games(e, group, teams, closed)
        expected = sum(1 for x in rec["games"].values() if x["stage"] == g["stage"])
        complete = len(own) == expected
        states[group] = (teams, own + carried, complete)
        if complete:
            drawn = {tuple(k.split("|")): v for k, v in rec["draws"].items() if set(k.split("|")) <= set(teams)}
            final = apply_draws(group_table(teams, own + carried, e.get("tiebreak", "fiba_2004")), drawn)
            if final is not None:
                done[group] = final
    return states, done


def tables(e, rec, closed):
    """Final group tables (engine-drawn orders applied) for every completed group; the live tables in the record."""
    states, done = group_states(e, rec, closed)
    rec["tables"] = {group: group_table(teams, games, e.get("tiebreak", "fiba_2004")) for group, (teams, games, _) in states.items() if teams}
    return done


def settle_ties(e, rec, closed, day, root=ROOT):
    """An engine draw for every completed group tie the FIBA procedure cannot break. Returns pending packets."""
    from itertools import permutations
    pending = []
    states, _ = group_states(e, rec, closed)
    for group, (teams, games, complete) in states.items():
        if not complete:
            continue
        for row in group_table(teams, games, e.get("tiebreak", "fiba_2004")):
            if not row["tied_with"]:
                continue
            block = tuple(sorted([row["team"], *row["tied_with"]]))
            key = "|".join(block)
            if key in rec["draws"]:
                continue
            orders = ["|".join(o) for o in permutations(block)]
            packet, outcome = _draw(root, e, f"fiba-{e['slug']}-tie-{group.lower()}-" + "-".join(_short(t) for t in block),
                                    day, f"Group {group}: order of {', '.join(block)} (level after every FIBA criterion)",
                                    {o: round(1 / len(orders), 6) for o in orders})
            if outcome is None:
                pending.append(packet)
            else:
                rec["draws"][key] = outcome.split("|")
    return pending


def _short(team):
    return "".join(ch for ch in team.lower() if ch.isalnum())[:6]


def resolve(e, rec, closed):
    """Fill each game's teams from its slots once they are decided."""
    final_tables = tables(e, rec, closed)
    winners, losers = {}, {}
    for number, r in closed.items():
        won = r["home"] if r["home_score"] > r["away_score"] else r["away"]
        winners[str(number)] = won
        losers[str(number)] = r["away"] if won == r["home"] else r["home"]
    for number, g in rec["games"].items():
        for side in ("home", "away"):
            if g.get(side) is None and g.get(f"{side}_slot"):
                g[side] = resolve_slot(g[f"{side}_slot"], final_tables, winners, losers)


def build_requests(e, rec, day, root=ROOT):
    """Requests for the day's games whose teams are known (frozen inputs, as every request from 2004-01-22)."""
    from .game_requests import freeze
    written = []
    for number, g in sorted(rec["games"].items(), key=lambda x: int(x[0])):
        if g["date"] != day or not g.get("home") or not g.get("away"):
            continue
        note, request, result = game_paths(e, rec, g, root)
        if request.exists() or result.exists():
            continue
        venue = "home" if e.get("host") in (g["home"], g["away"]) else "neutral"
        home, away = g["home"], g["away"]
        if venue == "home" and away == e.get("host"):
            home, away = away, home                       # the host is the home side
        data = {"event_id": event_id(e, number), "game_date": day, "game_type": e["game_type"], "venue": venue,
                "home": {"team": home, "national": e["edition_id"]}, "away": {"team": away, "national": e["edition_id"]}}
        _write(request, freeze(data, root))
        if note is not None:
            write_note(e, g, note, request, home, away, root)
        written.append(request)
    return written


def write_note(e, g, note, request, home, away, root=ROOT, result=None):
    """Wade's national game note (the statistics contract's metadata: competition, edition, player_team)."""
    opponent = away if home == USA else home
    venue = "neutral" if e.get("host") not in (home, away) else ("home" if home == USA else "away")
    meta = {"type": "game", "status": "played" if result else "scheduled", "date": g["date"], "opponent": opponent,
            "venue": venue, "competition": e["game_type"], "edition": e["edition"], "player_team": USA,
            "stage": g["stage"], "game_number": g["number"], "request_file": request.name}
    if result:
        own = "home" if result["home"] == USA else "away"
        other = "away" if own == "home" else "home"
        won = result["final_score"][own] > result["final_score"][other]
        meta["result"] = f"{'W' if won else 'L'} {result['final_score'][own]}-{result['final_score'][other]}"
        meta["result_file"] = request.name.replace(".request.json", ".result.json")
    front = "\n".join(f"{k}: {json.dumps(v) if not isinstance(v, str) else v}" for k, v in meta.items())
    body = (f"# {e['name']}: USA vs {opponent}\n\n{g['date']}, {g.get('venue') or 'venue as scheduled'}; "
            f"{g['stage'].replace('_', ' ')} (game {g['number']}).\n\nPlayed by the engine under FIBA rules "
            f"({'result in the adjacent result file' if result else 'scheduled'}).\n")
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text(f"---\n{front}\n---\n\n{body}", encoding="utf-8")


# -- the day --------------------------------------------------------------------------------------------------------
def day(today, root=ROOT, write=True):
    """Everything due on the day for the edition in progress. Returns (summary lines, pending draw packets)."""
    e = edition_for(today, root)
    if e is None:
        return [], []
    rec = read_record(e, root)
    if rec is None:
        rec = new_record(e)
        resolve_field(e, rec, root)                   # simulated qualifiers take their places in the field
    lines, pending = [], []
    usa_in = any(USA in grp["teams"] for grp in rec["groups"].values())
    if not usa_in and not rec.get("usa_absent_noted"):
        rec["usa_absent_noted"] = today
        lines.append(f"{e['name']}: the USA is not in the field (no selection)")
    if usa_in and e["usa"]["selection"] == "committee" and today >= selection_date(e) and not (rec.get("selection") or {}).get("final"):
        pending += select_usa(e, today, rec, root)
        sel = rec["selection"]
        if sel.get("final"):
            names = ", ".join(p["player"] for p in sel["final"])
            lines.append(f"USA roster for {e['name']}: {names}")
            if any(p["bbr_id"] == WADE_BBR for p in sel["final"]):
                lines.append(f"WADE SELECTED: {e['name']} (USA Basketball committee, {sel['announced_on']})")
                if write:
                    record_wade_selection(e, rec, root)
    first = date.fromisoformat(e["first_game"])
    ready = not usa_in or e["usa"]["selection"] != "committee" or (rec.get("selection") or {}).get("final")
    if ready and today >= (first - timedelta(days=1)).isoformat():
        lock_rosters(e, rec, today, root)
    if rec.get("rosters"):
        closed = results(e, rec, root)
        pending += settle_ties(e, rec, closed, today, root)
        resolve(e, rec, closed)
        written = build_requests(e, rec, today, root) if write else []
        if written:
            lines.append(f"{e['name']}: {len(written)} game request(s) for {today}")
    if write:
        _write(Path(root) / record_path(e), rec)
        from .national_pages import write as write_page
        write_page(e, rec, root)
    return lines, pending


def after_games(today, root=ROOT):
    """After the day's games are played: Wade's notes get their results, standings refresh, the bracket advances,
    and the tournament closes after its last game (awards). Returns summary lines."""
    e = edition_for(today, root)
    if e is None:
        return []
    rec = read_record(e, root)
    if rec is None or not rec.get("rosters"):
        return []
    lines = []
    for number, g in rec["games"].items():
        note, request, result = game_paths(e, rec, g, root)
        if note is not None and result.is_file() and g["date"] <= today:
            r = _read(result)
            write_note(e, g, note, request, r["home"], r["away"], root, result=r)
            if g["date"] == today:
                own = "home" if r["home"] == USA else "away"
                other = "away" if own == "home" else "home"
                line = next((p for p in r["player_stats"][own] if p["player_id"] == WADE), None)
                score = f"USA {r['final_score'][own]}-{r['final_score'][other]} {r[other]}"
                lines.append(score + (f"; Wade {line['pts']} pts, {line['orb'] + line['drb']} reb, {line['ast']} ast"
                                      if line else ""))
    closed = results(e, rec, root)
    resolve(e, rec, closed)
    if today >= e["last_game"] and len(closed) == len(rec["games"]) and not rec.get("closed"):
        rec["awards"] = decide_awards(e, rec, root)
        rec["closed"] = True
        rec["ranking"] = final_ranking(e, rec, root)
        lines.append(f"{e['name']} closed: champion {rec['awards']['champion']}")
        for name in record_wade_honors(e, rec, root):
            lines.append(f"WADE HONOR: {name}")
    _write(Path(root) / record_path(e), rec)
    from .national_pages import write as write_page
    write_page(e, rec, root)
    return lines


# -- awards ---------------------------------------------------------------------------------------------------------
def decide_awards(e, rec, root=ROOT):
    """Final placings and the tournament's honors from closed results only: MVP and the All-Tournament Team (five)
    ranked by Game Score per game times the team's finish (the same evidence rule as the league's awards)."""
    from .season_awards import game_score
    closed = results(e, rec, root)
    final = next(g for g in rec["games"].values() if g["stage"] == "final")
    last = closed[int(final["number"])]
    champion = last["home"] if last["home_score"] > last["away_score"] else last["away"]
    runner_up = last["away"] if champion == last["home"] else last["home"]
    third = next((g for g in rec["games"].values() if g["stage"] == "third_place"), None)
    bronze = None
    if third:
        t = closed[int(third["number"])]
        bronze = t["home"] if t["home_score"] > t["away_score"] else t["away"]
    finish = {champion: 1.0, runner_up: 0.85}
    if bronze:
        finish[bronze] = 0.75
    lines = defaultdict(lambda: defaultdict(float))
    for r in closed.values():
        res = _read(Path(root) / r["result"])
        for side in ("home", "away"):
            for p in res["player_stats"][side]:
                if p.get("minutes", 0) <= 0:
                    continue
                t = lines[(p["player_id"], res[side])]
                t["games"] += 1
                t["gmsc"] += game_score(p)
                t["pts"] += p["pts"]
    ranked = sorted(((k, v) for k, v in lines.items() if v["games"] >= 3),
                    key=lambda kv: (-kv[1]["gmsc"] / kv[1]["games"] * finish.get(kv[0][1], 0.6), kv[0][0]))
    rows = [{"player": k[0], "team": k[1], "games": int(v["games"]), "game_score": round(v["gmsc"] / v["games"], 2),
             "pts": round(v["pts"] / v["games"], 1)} for k, v in ranked[:10]]
    return {"champion": champion, "runner_up": runner_up, "third": bronze, "mvp": rows[0] if rows else None,
            "all_tournament": rows[:5], "shortlist": rows,
            "rule": "Game Score per game x team finish (champion 1.0, runner-up 0.85, third 0.75, others 0.6); "
                    "at least three games; closed results only"}


# -- Wade's records -------------------------------------------------------------------------------------------------
MEDALS = {1: "gold medal", 2: "silver medal", 3: "bronze medal"}


def record_wade_selection(e, rec, root=ROOT):
    """A dated identity snapshot when Wade is named to the USA's twelve (his status changes; earlier ones stay)."""
    path = Path(root) / PLAYER / "professional_identity.json"
    data = _read(path)
    day = rec["selection"]["announced_on"]
    label = f"United States ({e['name']})"
    if any(s.get("national_team") == label for s in data["snapshots"]):
        return
    last = sorted(data["snapshots"], key=lambda s: s["as_of"])[-1]
    snap = dict(last, as_of=max(day, last["as_of"]), national_team=label,
                national_team_eligibility="United States (USA Basketball); selected",
                source_event=(folder(e) / "README.md").relative_to(PLAYER).as_posix())
    data["snapshots"].append(snap)
    _write(path, data)


def record_wade_honors(e, rec, root=ROOT):
    """Wade's tournament honors in his award register (MVP, All-Tournament Team, a medal), sourced to the page."""
    if not wade_plays(rec):
        return []
    a = rec["awards"]
    source = (folder(e) / "README.md").relative_to(PLAYER).as_posix() + "#final-placings-and-honors"
    names = []
    if a.get("mvp") and a["mvp"]["player"] == WADE:
        names.append((f"{e['name']} MVP", "MVP", "mvp"))
    if any(r["player"] == WADE for r in a["all_tournament"]):
        names.append((f"{e['name']} All-Tournament Team", "All-Tournament", "all_tournament"))
    place = {a["champion"]: 1, a["runner_up"]: 2, a.get("third"): 3}.get(USA)
    if place:
        names.append((f"{e['name']} {MEDALS[place]}", MEDALS[place].title(), MEDALS[place].split()[0]))
    path = Path(root) / PLAYER / "awards.json"
    data = _read(path)
    have = {x["id"] for x in data["awards"]}
    added = []
    for name, short, key in names:
        aid = f"{e['edition_id']}-{key}"
        if aid in have:
            continue
        data["awards"].append({"id": aid, "name": name, "short_name": short, "status": "earned",
                               "competition": e["game_type"], "season": e["edition"], "period_start": e["first_game"],
                               "period_end": e["last_game"], "awarded_on": e["last_game"], "source": source})
        added.append(name)
    if added:
        _write(path, data)
    return added


# -- validation -----------------------------------------------------------------------------------------------------
def national_errors(root=ROOT):
    """Built editions match a fresh build; nothing hindsight in the researched editions; every tournament game dated
    on or before the clock with both teams known has its request; Wade's selection and honors are recorded."""
    from .seasons import state
    root = Path(root)
    errors = []
    clock = state(None, root)["current_date"]
    for path in sorted(root.glob("library/*/fiba/*.json")):
        if "later_nba" in path.read_text(encoding="utf-8"):
            errors.append(f"{path.relative_to(root)}: carries later NBA identities (hindsight)")
    for e in editions(root).values():
        rec = read_record(e, root)
        if rec is None:
            if selection_date(e) <= clock:
                errors.append(f"{e['edition_id']}: its window opened {selection_date(e)} but it has no record "
                              "(scripts/national_day.py)")
            continue
        for g in rec["games"].values():
            if g["date"] <= clock and g.get("home") and g.get("away") and rec.get("rosters"):
                _, request, result = game_paths(e, rec, g, root)
                if not request.exists():
                    errors.append(f"{e['edition_id']} game {g['number']}: no request on {g['date']}")
                elif g["date"] < clock and not result.exists():
                    errors.append(f"{e['edition_id']} game {g['number']}: played {g['date']} but has no result")
        sel = rec.get("selection") or {}
        if any(p.get("bbr_id") == WADE_BBR for p in sel.get("final") or []):
            ident = _read(root / PLAYER / "professional_identity.json")
            if not any(s.get("national_team") == f"United States ({e['name']})" for s in ident["snapshots"]):
                errors.append(f"{e['edition_id']}: Wade's selection has no identity snapshot")
        if rec.get("closed") and wade_plays(rec):
            have = {a["id"] for a in _read(root / PLAYER / "awards.json")["awards"]}
            a = rec["awards"]
            if (a.get("mvp") or {}).get("player") == WADE and f"{e['edition_id']}-mvp" not in have:
                errors.append(f"{e['edition_id']}: Wade's MVP is not in awards.json")
    return errors
