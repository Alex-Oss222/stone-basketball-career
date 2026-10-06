"""All-Star selections for the live season, decided on their real dates from closed simulated results.

The calendar, roster shape and electorates are researched per season (`library/<year>/league/nba_<season>_all_star.json`,
read through `runtime/seasons.py`); no real selection, vote count or roster is read. Every step uses only results closed
by its date and applies the same rule to every player; Wade gets no bonus.

Starters (fan ballot, closes on the ballot date, announced on the starters date). Fans vote two guards, two forwards
and one center in each conference. The fan electorate is a deterministic panel, like the season-award voters
(`runtime/season_awards.py`): fans differ only in how much they weigh two criteria, spread evenly over a fixed range,
so no vote is chance. Criteria, each a z-score among the conference's eligible players:
  production = mean z of Game Score per game and points per game, each times availability (games / club games);
  reputation = mean z of past All-Star selections (each counted at 0.8 to the power of its age in seasons, from
               `nba_all_star_history_1985_2003.json`, then simulated seasons' selections) and the prior season's Game
               Score per game (real before the career began, simulated after; none counts as zero).
  fan lens t (weight on reputation): 0.30 to 0.70. Fans reward names, so reputation carries as much as form; a rookie
  has none (judgement, documented in docs/player_statistics.md).
Eligible: on a club in the conference on the ballot date, with games in at least a third of his club's games.
The most ballots win at each position; summed fan score breaks a ballot tie.

Reserves (the conference's head coaches, announced on the reserves date, results through the day before). Seven per
conference: two guards, two forwards, one center and two at any position, never the elected starters. A coach never
votes for his own players. Criteria as the MVP vote: production (above) and club win share; coach lens 0.20 to 0.50.
A coach's ballot is his seven best by his lens in the shape; the most ballots win, summed coach score breaking ties,
positions filled first, then the two wild cards.

Injury replacements (the Commissioner, on the replacements date, results through the day before). A selected player
who played in none of his club's last two games is unavailable; the Commissioner names the coaches' next player in
his conference at his position (any position when none is left there). A replaced starter's place in the opening five
goes to the selected reserve with the most coach ballots at his position (the coach's choice; the 2004 practice is
unverified).

Game coaches: the head coach of each conference's best winning percentage through the coach-record date, unless he
coached the previous All-Star Game (the Riley Rule), then the next. An exact tie in percentage goes to more wins, then
to an engine draw.

Rookie Challenge (announced on its date, results through the day before): nine first-season players against nine
second-season players, picked by a broadcaster panel. The panel is modelled as the ROY score (production and club
win share, lens 0.0 to 0.25, eleven panelists) in the reserves' shape: two guards, two forwards, one center, then the
best four at any position. Eligible: games in at least a third of his club's games.

The record is written once to `Stats_and_Awards/League/<season>/all_star.json` and never recomputed. An All-Star
selection for Wade is added to `awards.json` as "All-Star", the exact name `runtime/standing.py` reads.
"""
from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
PLAYER = Path("career/Dwyane_Wade")
WADE = "Dwyane Wade"
FAN_LENS, COACH_LENS, PANEL_LENS = (0.30, 0.70), (0.20, 0.50), (0.0, 0.25)
FAN_PANEL, PANEL_SIZE = 101, 11
RECENCY = 0.8
MIN_SHARE = 1 / 3
HISTORY = Path("library/2003/league/nba_all_star_history_1985_2003.json")
STEPS = ("starters", "coaches", "reserves", "rookie_challenge", "replacements")


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def ctx(root=ROOT, season=None):
    from types import SimpleNamespace
    from . import seasons
    root = Path(root)
    season = season or seasons.active(root)
    league = PLAYER / "Stats_and_Awards/League" / season
    rel = seasons.path(season, "all_star")
    data = _read(root / rel) if (root / rel).is_file() else (_read(seasons.ROOT / rel) if (seasons.ROOT / rel).is_file() else None)
    return SimpleNamespace(season=season, calendar=rel, data=data, record=league / "all_star.json",
                           page=league / "All_Star.md", draws=league / "Award_Draws")


def dates(c):
    return {k: v["value"] for k, v in c.data["dates"].items()}


def _plus(day, n):
    from datetime import date, timedelta
    return (date.fromisoformat(day) + timedelta(days=n)).isoformat()


def _z(values):
    from statistics import pstdev
    m, s = mean(values), pstdev(values) or 1.0
    return [(v - m) / s for v in values]


def lenses(lo_hi, n):
    lo, hi = lo_hi
    return [lo + (hi - lo) * (i + 0.5) / n for i in range(n)]


# -- evidence ---------------------------------------------------------------------------------------------------
def pool(root, season, through, rows=None):
    """{record name: evidence} for every player with a closed game through the date."""
    from .season_awards import identities, season_lines
    from .seasons import conference_of
    from .write_back import closed_results
    rows = closed_results(root, season, through) if rows is None else rows
    players, clubs = season_lines(rows, through)
    ids = identities(root, season)
    out = {}
    for name, t in players.items():
        record_name, bbr, group = ids.get(name, (name, None, None))
        club = clubs[t["_club"]]
        g, cg = t["games"], club["games"]
        avail = min(1.0, g / cg)
        out[record_name] = {"player": record_name, "bbr_id": bbr, "position": group or "F", "team": t["_club"],
                            "conference": conference_of(season, t["_club"], root), "games": int(g), "club_games": int(cg),
                            "pts": round(t["pts"] / g, 1), "reb": round((t["orb"] + t["drb"]) / g, 1),
                            "ast": round(t["ast"] / g, 1), "game_score": round(t["gmsc"] / g, 2),
                            "avail_gmsc": t["gmsc"] / g * avail, "avail_pts": t["pts"] / g * avail,
                            "club_pct": round(club["wins"] / cg, 3), "eligible": g >= cg * MIN_SHARE}
    return out


def _last_games(rows, through):
    """{club: [the dates of its games through the date]} and {(club, date): players who appeared}."""
    games, appeared = defaultdict(list), defaultdict(set)
    for row in rows:
        r = row["result"]
        if r["game_date"] > through:
            continue
        for side in ("home", "away"):
            games[r[side]].append(r["game_date"])
            appeared[(r[side], r["game_date"])] |= {p["player_id"] for p in r["player_stats"][side] if p.get("minutes", 0) > 0}
    return games, appeared


def reputation(root, season, players):
    """{record name: (weighted past selections, prior Game Score per game)} known before the season."""
    from .season_awards import prior_rates, C
    from .seasons import start_year
    start = start_year(season)
    weighted = defaultdict(float)
    hist = Path(root) / HISTORY if (Path(root) / HISTORY).is_file() else ROOT / HISTORY
    for p in _read(hist)["players"]:
        weighted[p["bbr_id"]] += sum(RECENCY ** (start - y) for y in p["years"] if y <= start)
    base = Path(root) / PLAYER / "Stats_and_Awards/League"
    for rec in sorted(base.glob("*/all_star.json")):                  # the career's own earlier seasons
        s = rec.parent.name
        if s >= season:
            continue
        y = start_year(s) + 1
        for name in _read(rec).get("all_stars", []):
            weighted[name["bbr_id"] or name["player"]] += RECENCY ** (start - y)
    prior = prior_rates(root) if C(root).season == season else {}
    out = {}
    for name, e in players.items():
        key = e["bbr_id"] or name
        out[name] = (weighted.get(key, 0.0), (prior.get(e["bbr_id"]) or (0, 0.0))[1])
    return out


# -- ballots ----------------------------------------------------------------------------------------------------
def _scores(names, first, second):
    """[(name, first z, second z)]; a list in `first` is the mean of its z-scores."""
    parts = [_z(v) for v in first]
    a = [mean(x) for x in zip(*parts)]
    return list(zip(names, a, _z(second)))


def _ballot(scored, t, shape, positions, exclude=()):
    """One voter's picks in a shape {"G": n, "F": n, "C": n, "any": n}, best first by (1 - t) a + t b."""
    order = [n for _, n in sorted((-((1 - t) * a + t * b), n) for n, a, b in scored if n not in exclude)]
    picks, left = [], dict(shape)
    for n in order:
        g = positions[n]
        if left.get(g, 0) > 0:
            picks.append(n)
            left[g] -= 1
    for n in order:
        if left.get("any", 0) > 0 and n not in picks:
            picks.append(n)
            left["any"] -= 1
    return picks


def tally(scored, voters, shape, positions, exclude_for=None, exclude=()):
    """Ballots and summed score per player over the voters [(voter, lens)]."""
    votes, total = defaultdict(int), defaultdict(float)
    by = {n: (a, b) for n, a, b in scored}
    for voter, t in voters:
        skip = set(exclude) | set((exclude_for or {}).get(voter, ()))
        for n in _ballot(scored, t, shape, positions, skip):
            votes[n] += 1
        for n, (a, b) in by.items():
            total[n] += (1 - t) * a + t * b
    return votes, total


def elect(votes, total, shape, positions, exclude=()):
    """Fill the shape by ballots (summed score breaks ties): positions first, then any position."""
    order = sorted((n for n in votes if n not in exclude), key=lambda n: (-votes[n], -total[n], n))
    chosen, left = [], dict(shape)
    for n in order:
        if left.get(positions[n], 0) > 0:
            chosen.append(n)
            left[positions[n]] -= 1
    for n in order:
        if left.get("any", 0) > 0 and n not in chosen:
            chosen.append(n)
            left["any"] -= 1
    return chosen


def _row(e, **extra):
    keep = ("player", "bbr_id", "team", "position", "games", "club_games", "pts", "reb", "ast", "game_score", "club_pct")
    return dict({k: e[k] for k in keep}, **extra)


# -- steps ------------------------------------------------------------------------------------------------------
def starters(root, c, day, rows):
    through = dates(c)["fan_ballot_close"]
    players = pool(root, c.season, through, rows)
    rep = reputation(root, c.season, players)
    out = {}
    for conf in ("East", "West"):
        names = sorted(n for n, e in players.items() if e["conference"] == conf and e["eligible"])
        e = players
        scored = _scores(names, [[e[n]["avail_gmsc"] for n in names], [e[n]["avail_pts"] for n in names]],
                         [mean(z) for z in zip(_z([rep[n][0] for n in names]), _z([rep[n][1] for n in names]))])
        positions = {n: e[n]["position"] for n in names}
        voters = [(f"fan-{i}", t) for i, t in enumerate(lenses(FAN_LENS, FAN_PANEL))]
        votes, total = tally(scored, voters, c.data["shape"]["starters"], positions)
        chosen = elect(votes, total, c.data["shape"]["starters"], positions)
        top = sorted(votes, key=lambda n: (-votes[n], -total[n], n))[:15]
        out[conf] = {"starters": [_row(e[n], ballots=votes[n], past_all_star_weight=round(rep[n][0], 2),
                                       prior_game_score=round(rep[n][1], 2)) for n in chosen],
                     "leading_vote_getters": [{"player": n, "position": positions[n], "team": e[n]["team"], "ballots": votes[n]} for n in top]}
    return {"step": "starters", "announced_on": day, "evidence_through": through, "electorate": c.data["electorates"]["starters"],
            "panel": FAN_PANEL, "lens": list(FAN_LENS), "conferences": out}


def _coaches_on(root, season, day, rows):
    """{club: head coach on the date}, from the staffs file's windows (season fraction by games played)."""
    from .seasons import path
    games, _ = _last_games(rows, day)
    staffs = _read(Path(root) / path(season, "staffs")) if (Path(root) / path(season, "staffs")).is_file() else _read(ROOT / path(season, "staffs"))
    out = {}
    for club, info in staffs["clubs"].items():
        frac = len(games.get(club, [])) / 82
        out[club] = next((h["name"] for h in info["head_coaches"] if h["window"][0] <= frac <= h["window"][1]), info["head_coaches"][-1]["name"])
    team = _read(Path(root) / PLAYER / season / "00_Team/team_config.json")
    out["Miami Heat"] = team["head_coach"]
    return out


def reserves(root, c, day, rows, record):
    through = _plus(day, -1)
    players = pool(root, c.season, through, rows)
    coaches = _coaches_on(root, c.season, through, rows)
    from .seasons import conference_of
    out = {}
    for conf in ("East", "West"):
        elected = {s["player"] for s in record["conferences"][conf]["starters"]}
        names = sorted(n for n, e in players.items() if e["conference"] == conf and e["eligible"])
        e = players
        scored = _scores(names, [[e[n]["avail_gmsc"] for n in names], [e[n]["avail_pts"] for n in names]],
                         [e[n]["club_pct"] for n in names])
        positions = {n: e[n]["position"] for n in names}
        staff = sorted((coach, club) for club, coach in coaches.items() if conference_of(c.season, club, root) == conf)
        ts = lenses(COACH_LENS, len(staff))
        voters = [(coach, t) for (coach, _), t in zip(staff, ts)]
        own = {coach: {n for n in names if e[n]["team"] == club} for coach, club in staff}
        votes, total = tally(scored, voters, c.data["shape"]["reserves"], positions, own, elected)
        chosen = elect(votes, total, c.data["shape"]["reserves"], positions, elected)
        order = sorted((n for n in votes if n not in elected), key=lambda n: (-votes[n], -total[n], n))
        out[conf] = {"reserves": [_row(e[n], ballots=votes[n]) for n in chosen],
                     "coach_order": [{"player": n, "position": positions[n], "team": e[n]["team"], "ballots": votes[n]} for n in order[:20]],
                     "voters": [{"coach": coach, "team": club} for coach, club in staff]}
    return {"step": "reserves", "announced_on": day, "evidence_through": through, "electorate": c.data["electorates"]["reserves"],
            "lens": list(COACH_LENS), "conferences": out}


def previous_coaches(c, root=ROOT):
    """The Riley rule's barred coaches: the career's own previous All-Star Game where the career played one (a
    simulated game's coaches, not history's), else the researched real previous game (the career's first season)."""
    from .seasons import previous_season
    earlier = Path(root) / c.record.parent.parent / previous_season(c.season) / "all_star.json"
    if earlier.is_file():
        step = next((s for s in json.loads(earlier.read_text(encoding="utf-8"))["steps"] if s["step"] == "coaches"), None)
        if step:
            return {r["coach"] for r in step["conferences"].values()}
    barred = c.data["previous_game_coaches"]["value"]
    return set(barred.values()) if isinstance(barred, dict) else set(barred)


def game_coaches(root, c, day, rows):
    """(decision, pending packet or None)."""
    from .seasons import conference_of
    through = dates(c)["coach_record_through"]
    games, _ = _last_games(rows, through)
    wins = defaultdict(int)
    for row in rows:
        r = row["result"]
        if r["game_date"] > through:
            continue
        w = r["home"] if r["final_score"]["home"] > r["final_score"]["away"] else r["away"]
        wins[w] += 1
    coaches = _coaches_on(root, c.season, through, rows)
    barred = previous_coaches(c, root)
    out, pending = {}, None
    for conf in ("East", "West"):
        table = sorted(((wins[cl] / len(games[cl]), wins[cl], cl) for cl in games if conference_of(c.season, cl, root) == conf), reverse=True)
        rows_ = [{"team": cl, "coach": coaches[cl], "wins": w, "losses": len(games[cl]) - w, "pct": round(p, 3),
                  "barred": coaches[cl] in barred} for p, w, cl in table]
        open_ = [r for r in rows_ if not r["barred"]]
        best = [r for r in open_ if (r["pct"], r["wins"]) == (open_[0]["pct"], open_[0]["wins"])]
        pick = best[0]
        if len(best) > 1:
            packet, outcome = _draw(root, c, f"{c.season}-all-star-coach-{conf.lower()}", day,
                                    f"Who coaches the {conf}: " + " or ".join(r["coach"] for r in best) + "?",
                                    {r["coach"]: round(1 / len(best), 6) for r in best})
            if outcome is None:
                pending = packet
                continue
            pick = next(r for r in best if r["coach"] == outcome)
        out[conf] = {"coach": pick["coach"], "team": pick["team"], "record": f"{pick['wins']}-{pick['losses']}", "standings": rows_[:5]}
    return {"step": "coaches", "announced_on": day, "evidence_through": through, "riley_rule_barred": sorted(barred),
            "conferences": out}, pending


def _draw(root, c, event_id, day, question, options):
    packet = Path(root) / c.draws / f"{event_id}.decision.json"
    result = packet.with_name(packet.name.replace(".decision.json", ".decision.result.json"))
    if not packet.is_file():
        packet.parent.mkdir(parents=True, exist_ok=True)
        packet.write_text(json.dumps({"event_id": event_id, "date": day, "question": question,
                                      "decider": "All-Star tie (engine draw between equal records)", "options": options,
                                      "basis": "runtime/all_star.py"}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    if not result.is_file():
        return packet, None
    return packet, _read(result)["outcome"]


def rookie_challenge(root, c, day, rows):
    from .award_decisions import rookies
    through = _plus(day, -1)
    players = pool(root, c.season, through, rows)
    first = rookies(root, c.season)
    from .seasons import previous_season
    year = int(c.season[:4])                                    # the season's own service file (players before it)
    service_path = Path(root) / f"library/{year}/league/nba_{year}_service_years.json"
    if not service_path.is_file():
        service_path = Path(root) / "library/2004/league/nba_2004_service_years.json"
    service = _read(service_path)["players"]
    second_bbr = {b for b, s in service.items() if s.get("first_season") == previous_season(c.season)}
    shape = {"G": 2, "F": 2, "C": 1, "any": c.data["shape"]["rookie_challenge_roster"] - 5}
    out = {}
    for side, keep in (("Rookies", lambda n, e: n in first), ("Sophomores", lambda n, e: e["bbr_id"] in second_bbr)):
        names = sorted(n for n, e in players.items() if keep(n, e) and e["eligible"])
        e = players
        scored = _scores(names, [[e[n]["avail_gmsc"] for n in names], [e[n]["avail_pts"] for n in names]], [e[n]["club_pct"] for n in names])
        positions = {n: e[n]["position"] for n in names}
        voters = [(f"panelist-{i}", t) for i, t in enumerate(lenses(PANEL_LENS, PANEL_SIZE))]
        votes, total = tally(scored, voters, shape, positions)
        chosen = elect(votes, total, shape, positions)
        out[side] = [_row(e[n], ballots=votes[n]) for n in chosen]
    return {"step": "rookie_challenge", "announced_on": day, "evidence_through": through,
            "electorate": c.data["electorates"]["rookie_challenge"], "panel": PANEL_SIZE, "lens": list(PANEL_LENS),
            "game_date": dates(c)["rookie_challenge"], "teams": out}


def replacements(root, c, day, rows, record):
    through = _plus(day, -1)
    games, appeared = _last_games(rows, through)
    players = pool(root, c.season, through, rows)
    from .season_awards import identities
    ids = identities(root, c.season)
    by_record = defaultdict(set)
    for raw, (rec, _, _) in ids.items():
        by_record[rec].add(raw)
    out = {}
    for conf in ("East", "West"):
        steps = {s["step"]: s for s in record["steps"]}
        named = [dict(p, role="starter") for p in steps["starters"]["conferences"][conf]["starters"]]
        named += [dict(p, role="reserve") for p in steps["reserves"]["conferences"][conf]["reserves"]]
        order = steps["reserves"]["conferences"][conf]["coach_order"]
        taken = {p["player"] for p in named}
        changes = []
        for p in named:
            club = (players.get(p["player"]) or p)["team"]
            last = sorted(set(games.get(club, [])))[-2:]
            aliases = by_record.get(p["player"], set()) | {p["player"]}
            if last and not any(aliases & appeared[(club, d)] for d in last):
                pick = next((o for o in order if o["player"] not in taken and o["position"] == p["position"]), None) \
                    or next((o for o in order if o["player"] not in taken), None)
                if pick is None:
                    continue
                taken.add(pick["player"])
                changes.append({"out": p["player"], "out_team": club, "role": p["role"], "reason": f"played in none of {club}'s last two games ({', '.join(last)})",
                                "replacement": pick["player"], "replacement_team": pick["team"], "position": pick["position"]})
        out[conf] = changes
    return {"step": "replacements", "announced_on": day, "evidence_through": through,
            "electorate": c.data["electorates"]["replacements"], "conferences": out}


def rosters(record):
    """{conference: {"starters": [...], "reserves": [...], "out": [...]}} after replacements (and the opening five)."""
    steps = {s["step"]: s for s in record["steps"]}
    out = {}
    for conf in ("East", "West"):
        start = [p["player"] for p in steps["starters"]["conferences"][conf]["starters"]]
        res = [p["player"] for p in steps["reserves"]["conferences"][conf]["reserves"]]
        gone = []
        if "replacements" in steps:
            ballots = {o["player"]: (o["ballots"], o["position"]) for o in steps["reserves"]["conferences"][conf]["coach_order"]}
            pos = {p["player"]: p["position"] for s in ("starters",) for p in steps[s]["conferences"][conf]["starters"]}
            for ch in steps["replacements"]["conferences"][conf]:
                gone.append(ch["out"])
                if ch["out"] in start:
                    start.remove(ch["out"])
                    cands = sorted((p for p in res if ballots.get(p, (0, ""))[1] == pos[ch["out"]]), key=lambda p: -ballots[p][0]) or \
                        sorted(res, key=lambda p: -ballots.get(p, (0, ""))[0])
                    start.append(cands[0])
                    res.remove(cands[0])
                else:
                    res.remove(ch["out"])
                res.append(ch["replacement"])
        out[conf] = {"starters": start, "reserves": res, "out": gone}
    return out


# -- the record -------------------------------------------------------------------------------------------------
def read_record(root=ROOT, season=None):
    c = ctx(root, season)
    path = Path(root) / c.record
    if path.is_file():
        return _read(path)
    return {"schema_version": 1, "season": c.season, "kind": "all_star", "rule": __doc__.split("\n\n", 1)[1].strip(),
            "calendar": c.calendar.as_posix(), "steps": [], "all_stars": []}


def due(c, clock):
    d = dates(c)
    when = {"starters": d["starters_announced"], "coaches": _plus(d["coach_record_through"], 1), "reserves": d["reserves_announced"],
            "rookie_challenge": d["rookie_challenge_announced"], "replacements": d["replacements_named"]}
    return [(s, when[s]) for s in STEPS if when[s] <= clock]


def decide(root=ROOT, clock=None):
    """Close every All-Star step dated on or before the clock. Returns the new steps."""
    from .write_back import clock as career_clock, closed_results
    from .seasons import dates as season_dates
    root = Path(root)
    c = ctx(root)
    if c.data is None:
        return []
    clock = clock or career_clock(root)
    record = read_record(root)
    done = {s["step"] for s in record["steps"]}
    pending = [(s, d) for s, d in due(c, clock) if s not in done]
    if not pending:
        return []
    rows = closed_results(root, c.season, season_dates(c.season, root)["regular_season_end"])
    new = []
    for step, day in pending:
        if step == "starters":
            out = starters(root, c, day, rows)
        elif step == "coaches":
            out, waiting = game_coaches(root, c, day, rows)
            if waiting:
                break
        elif step == "reserves":
            out = reserves(root, c, day, rows, {"conferences": {k: v for k, v in next(s for s in record["steps"] if s["step"] == "starters")["conferences"].items()}})
        elif step == "rookie_challenge":
            out = rookie_challenge(root, c, day, rows)
        else:
            out = replacements(root, c, day, rows, record)
        record["steps"].append(out)
        new.append(out)
    if not new:
        return []
    record["steps"].sort(key=lambda s: (s["announced_on"], STEPS.index(s["step"])))
    if {"starters", "reserves"} <= {s["step"] for s in record["steps"]}:
        steps = {s["step"]: s for s in record["steps"]}
        record["all_stars"] = [{"player": p["player"], "bbr_id": p["bbr_id"], "team": p["team"], "conference": conf, "role": role,
                                "selected_on": steps[step]["announced_on"]}
                               for conf in ("East", "West")
                               for step, key, role in (("starters", "starters", "starter"), ("reserves", "reserves", "reserve"))
                               for p in steps[step]["conferences"][conf][key]]
        if "replacements" in steps:
            for conf, changes in steps["replacements"]["conferences"].items():
                for ch in changes:
                    rep = next(o for o in steps["reserves"]["conferences"][conf]["coach_order"] if o["player"] == ch["replacement"])
                    bbr = next((p.get("bbr_id") for p in pool(root, c.season, steps["replacements"]["evidence_through"], rows).values()
                                if p["player"] == ch["replacement"]), None)
                    record["all_stars"].append({"player": ch["replacement"], "bbr_id": bbr, "team": rep["team"], "conference": conf,
                                                "role": "injury replacement", "selected_on": steps["replacements"]["announced_on"],
                                                "replacing": ch["out"]})
            record["game_rosters"] = rosters(record)
    for a in record.get("all_stars", []):
        if clock > a["selected_on"]:                     # decided after its date: known to the career from the clock
            a.setdefault("recorded_on", clock)
    path = root / c.record
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (root / c.page).write_text(page(record, clock, c), encoding="utf-8")
    if _record_wade(root, record, c, clock):
        from . import standing
        standing.record(root, clock, "honor_recorded", c.page.relative_to(PLAYER).as_posix())
    return new


def _record_wade(root, record, c, clock=None):
    path = root / PLAYER / "awards.json"
    data = _read(path) if path.is_file() else {"schema_version": 1, "awards": []}
    have = {a["id"] for a in data["awards"]}
    added = 0
    from .seasons import dates as season_dates
    opening = season_dates(c.season, root)["opening_night"]
    for a in record.get("all_stars", []):
        award_id = f"{c.season}-all-star"
        if a["player"] != WADE or award_id in have:
            continue
        data["awards"].append({"id": award_id, "name": "All-Star", "short_name": "All-Star", "status": "earned",
                               "competition": "regular", "season": c.season, "period_start": opening,
                               "period_end": a["selected_on"], "awarded_on": a["selected_on"], "role": a["role"],
                               **({"recorded_on": clock} if clock and clock > a["selected_on"] else {}),
                               "source": c.page.relative_to(PLAYER).as_posix() + "#all-stars"})
        added += 1
    if added:
        data["awards"].sort(key=lambda a: (a["awarded_on"], a["id"]))
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return added


# -- page -------------------------------------------------------------------------------------------------------
def _table(headers, rows):
    return ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)] + ["| " + " | ".join(str(x) for x in r) + " |" for r in rows]


def _long(day):
    from datetime import date
    d = date.fromisoformat(day)
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def page(record, clock, c):
    steps = {s["step"]: s for s in record["steps"]}
    d = dates(c)
    lines = [f"# {c.season} NBA All-Star selections", "",
             f"All-Star Game: {_long(d['all_star_game'])}, {c.data['dates']['all_star_game'].get('venue', '')}. "
             f"Rookie Challenge: {_long(d['rookie_challenge'])}. Decided from closed simulated results on each step's date "
             f"(`runtime/all_star.py`); no real selection is read. Career clock: {_long(clock)}.", ""]
    head = ["Player", "Pos", "Team", "G", "PTS", "REB", "AST", "GmSc", "Ballots"]

    def rows(ps):
        return [[p["player"], p["position"], p["team"], p["games"], p["pts"], p["reb"], p["ast"], p["game_score"], p["ballots"]] for p in ps]

    if "starters" in steps:
        s = steps["starters"]
        lines += [f"## Starters (fan ballot, announced {_long(s['announced_on'])}; results through {_long(s['evidence_through'])})", ""]
        for conf in ("East", "West"):
            lines += [f"### {conf}", ""] + _table(head, rows(s["conferences"][conf]["starters"])) + [""]
    if "coaches" in steps:
        s = steps["coaches"]
        lines += [f"## Coaches (best record through {_long(s['evidence_through'])}; Riley Rule barred {', '.join(s['riley_rule_barred'])})", ""]
        lines += _table(["Conference", "Coach", "Team", "Record"], [[k, v["coach"], v["team"], v["record"]] for k, v in s["conferences"].items()]) + [""]
    if "reserves" in steps:
        s = steps["reserves"]
        lines += [f"## Reserves (head coaches, announced {_long(s['announced_on'])}; results through {_long(s['evidence_through'])})", ""]
        for conf in ("East", "West"):
            lines += [f"### {conf}", ""] + _table(head, rows(s["conferences"][conf]["reserves"])) + [""]
    if "rookie_challenge" in steps:
        s = steps["rookie_challenge"]
        lines += [f"## Rookie Challenge rosters (broadcaster panel, announced {_long(s['announced_on'])})", ""]
        for side, ps in s["teams"].items():
            lines += [f"### {side}", ""] + _table(head, rows(ps)) + [""]
    if "replacements" in steps:
        s = steps["replacements"]
        lines += [f"## Injury replacements (the Commissioner, {_long(s['announced_on'])})", ""]
        changes = [[k, ch["out"], ch["reason"], ch["replacement"], ch["replacement_team"]] for k, v in s["conferences"].items() for ch in v]
        lines += (_table(["Conference", "Out", "Reason", "Replacement", "Team"], changes) if changes else ["None."]) + [""]
    if record.get("all_stars"):
        lines += ["## All-Stars", ""] + _table(["Player", "Team", "Conference", "Role", "Selected"],
                                                 [[a["player"], a["team"], a["conference"], a["role"], a["selected_on"]] for a in record["all_stars"]]) + [""]
    lines += ["Rules: " + c.calendar.as_posix() + "; method in `runtime/all_star.py`.", ""]
    return "\n".join(lines)


def all_star_errors(root=ROOT):
    """A step dated on or before the clock and not decided; a Wade selection missing from awards.json."""
    from .write_back import clock as career_clock
    root = Path(root)
    c = ctx(root)
    if c.data is None:
        return []
    record = read_record(root)
    done = {s["step"] for s in record["steps"]}
    errors = [f"{c.record.as_posix()}: All-Star {s} dated {d} is not decided (python scripts/decide_awards.py --write)"
              for s, d in due(c, career_clock(root)) if s not in done]
    path = root / PLAYER / "awards.json"
    have = {a["id"] for a in _read(path)["awards"]} if path.is_file() else set()
    if any(a["player"] == WADE for a in record.get("all_stars", [])) and f"{c.season}-all-star" not in have:
        errors.append(f"awards.json: Wade's {c.season} All-Star selection is not recorded")
    return errors
