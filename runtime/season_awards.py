"""End-of-season NBA awards for 2003-04, decided on their real announcement dates from closed simulated results.

The calendar, electorates and ballot scoring are researched (`library/2003/league/nba_2003_04_season_awards.json`);
no real 2004 winner, vote or ballot is read. Each award closes on its announcement date. Its ballots use only closed
regular-season results (`write_back.closed_results`, through April 14), standings from those results, the 2002-03
season as the prior-year baseline (Most Improved, Coach of the Year), and the season's head coaches.

Voters (design choice, documented here and in `docs/player_statistics.md`): every voter in the real electorate files a
ballot. Voters differ only in how much they weigh two published criteria, spread evenly across a fixed range, so the
electorate is a deterministic panel: no chance enters a vote and nothing is re-rolled. Each criterion is a z-score
among the eligible candidates; a voter ranks candidates by (1 - t) x first criterion + t x second, t his lens.

  Award        first criterion                                  second criterion           lens t       eligible
  MVP          production x durability                          club win share             0.20-0.50    55+ games
  ROY          production x durability                          club win share             0.00-0.25    first-season player, 41+ games
  DPOY         defensive box stocks per 36 x minutes factor     club defensive rating      0.30-0.60    55+ games, 24+ minutes
  6MOY         production                                       club win share             0.10-0.30    55+ games, more off the bench than started
  MIP          rise in Game Score per game over 2002-03         Game Score per game        0.10-0.40    55+ games, 25+ games in 2002-03, not a rookie
  COY          club win share above its 2002-03 expectation      club win share             0.20-0.50    head coach for at least half the season and at its end
  All-NBA      the MVP score, by position (2 G, 2 F, 1 C a team)                           MVP lens     55+ games
  All-Defense  the DPOY score, by position; a coach never votes for his own players         DPOY lens    55+ games, 24+ minutes
  All-Rookie   the ROY score, five a team regardless of position; not his own players       ROY lens     first-season player, 30+ games

Production = the mean of the z-scores of Game Score per game and points per game (voters weigh scoring);
durability = min(1, games / 70); minutes factor = min(1, minutes per game / 32); defensive box stocks = steals + blocks
+ 0.3 x defensive rebounds; club defensive rating = points allowed per 100 opponent possessions (lower is better);
2002-03 expectation = 0.5 + 0.6 x (2002-03 win share - 0.5). Positions are the registry's primary positions
(PG/SG -> G, SF/PF/F -> F, C -> C).

Ballots score as published (5-3-1, 10-7-5-3-1, or team points 5/3/1 and 2/1). The highest total wins; first-place
votes break a points tie; a tie that remains names co-winners, as the NBA did (1994-95 and 1999-2000 Rookie of the
Year). A team spot tied at the cut names both players, as the league did when ballots tied. Every rule applies to
every player alike; Wade gets no bonus. Decisions are recorded once in `season_awards.json` and never recomputed;
a Wade honor is added to `awards.json`.
"""
from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
from statistics import mean, pstdev

ROOT = Path(__file__).resolve().parents[1]
SEASON = "2003-04"
SEASON_END = "2004-04-14"
CALENDAR = Path("library/2003/league/nba_2003_04_season_awards.json")
CONFERENCES = Path("library/2003/league/nba_2003_04_conferences.json")
STAFFS = Path("library/2003/league/nba_2003_04_staffs.json")
PRIOR_STATS = Path("library/2003/league/nba_2002_03_player_stats.json")
PRIOR_STANDINGS = Path("library/2003/league/nba_2002_03_standings.json")
LEAGUE = Path(f"career/Dwyane_Wade/Stats_and_Awards/League/{SEASON}")
RECORD = LEAGUE / "season_awards.json"
PAGE = LEAGUE / "Season_Awards.md"
PLAYER = Path("career/Dwyane_Wade")
WADE = "Dwyane Wade"
GROUP = {"PG": "G", "SG": "G", "G": "G", "SF": "F", "PF": "F", "F": "F", "C": "C"}
LENS = {"mvp": (0.20, 0.50), "roy": (0.0, 0.25), "dpoy": (0.30, 0.60), "smoy": (0.10, 0.30), "mip": (0.10, 0.40),
        "coy": (0.20, 0.50), "all_nba": (0.20, 0.50), "all_defensive": (0.30, 0.60), "all_rookie": (0.0, 0.25)}
MIN_GAMES, MIN_ROOKIE_GAMES, MIN_ALL_ROOKIE_GAMES, MIN_PRIOR_GAMES = 55, 41, 30, 25
DEF_MINUTES, FULL_MINUTES, FULL_GAMES = 24.0, 32.0, 70
TEAM_NAMES = {1: "First Team", 2: "Second Team", 3: "Third Team"}


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def calendar(root=ROOT):
    return _read(Path(root) / CALENDAR)


def game_score(p):
    return (p["pts"] + 0.4 * p["fgm"] - 0.7 * p["fga"] - 0.4 * (p["fta"] - p["ftm"]) + 0.7 * p["orb"]
            + 0.3 * p["drb"] + p["stl"] + 0.7 * p["ast"] + 0.7 * p["blk"] - 0.4 * p["pf"] - p["tov"])


# -- evidence ------------------------------------------------------------------------------------------------
def identities(root):
    """{name as results key him: (dated record name, bbr_id, position group)}."""
    from .award_decisions import registry_names
    from .rotations import load_rosters
    root = Path(root)
    registry = _read(root / "career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json")
    registry = registry["players"] if isinstance(registry, dict) else registry
    by_bbr = {p["bbr_id"]: p for p in registry if p.get("bbr_id")}
    by_name = {p["name"]: p for p in registry}
    names = registry_names(root)
    out = {}
    pairs = [(p["player_id"], p.get("bbr_id")) for club in load_rosters(SEASON, root).values() for p in club["players"]]
    roster = _read(root / f"career/Dwyane_Wade/{SEASON}/00_Team/Team/Roster/roster.json")
    pairs += [(p["name"], p.get("bbr_id")) for p in roster["players"]]
    for name, bbr in pairs:
        entry = by_bbr.get(bbr) or by_name.get(names.get(name, name)) or {}
        out[name] = (names.get(name, name), bbr or entry.get("bbr_id"), GROUP.get(entry.get("position") or "", None))
    for name, entry in by_name.items():
        out.setdefault(name, (name, entry.get("bbr_id"), GROUP.get(entry.get("position") or "", None)))
    return out


def season_lines(rows):
    """Per player and per club, totals over the closed regular season."""
    players = defaultdict(lambda: defaultdict(float))       # "_club" holds a name
    clubs = defaultdict(lambda: defaultdict(float))
    for row in rows:
        r = row["result"]
        if r["game_date"] > SEASON_END:
            continue
        for side, other in (("home", "away"), ("away", "home")):
            team = r[side]
            won = r["final_score"][side] > r["final_score"][other]
            c = clubs[team]
            c["games"] += 1
            c["wins"] += won
            c["allowed"] += r["final_score"][other]
            c["opp_poss"] += r["team_stats"][other]["possessions"]
            for p in r["player_stats"][side]:
                if not p.get("minutes", 0) > 0:
                    continue
                t = players[p["player_id"]]
                t["games"] += 1
                t["starts"] += bool(p.get("started"))
                t["wins"] += won
                t["gmsc"] += game_score(p)
                for k in ("minutes", "pts", "orb", "drb", "ast", "stl", "blk"):
                    t[k] += p[k]
                t["_club"] = team                                   # rows run in date order: his club at the end
    return players, clubs


def prior_rates(root):
    """{bbr_id: (games, Game Score per game)} for 2002-03, from the library's real totals."""
    out = {}
    for rec in _read(Path(root) / PRIOR_STATS)["records"]:
        t = rec["totals"]
        if not t.get("games"):
            continue
        gs = (t["points"] + 0.4 * t["field_goals_made"] - 0.7 * t["field_goals_attempted"]
              - 0.4 * (t["free_throws_attempted"] - t["free_throws_made"]) + 0.7 * t["offensive_rebounds"]
              + 0.3 * t["defensive_rebounds"] + t["steals"] + 0.7 * t["assists"] + 0.7 * t["blocks"]
              - 0.4 * t["personal_fouls"] - t["turnovers"])
        if rec["bbr_id"] not in out or t["games"] > out[rec["bbr_id"]][0]:
            out[rec["bbr_id"]] = (t["games"], gs / t["games"])
    return out


def candidates(root, rows):
    """Every player's season evidence, keyed by the dated record name."""
    from .award_decisions import rookies
    players, clubs = season_lines(rows)
    ids, first, prior = identities(root), rookies(root), prior_rates(root)
    out = {}
    for name, t in players.items():
        record_name, bbr, group = ids.get(name, (name, None, None))
        g = t["games"]
        club = clubs[t["_club"]]
        mpg = t["minutes"] / g
        prior_g, prior_gs = prior.get(bbr, (0, None))
        out[record_name] = {
            "player": record_name, "team": t["_club"], "position": group, "rookie": name in first or record_name in first,
            "games": int(g), "starts": int(t["starts"]), "mpg": round(mpg, 1),
            "pts": round(t["pts"] / g, 1), "reb": round((t["orb"] + t["drb"]) / g, 1), "ast": round(t["ast"] / g, 1),
            "stl": round(t["stl"] / g, 1), "blk": round(t["blk"] / g, 1),
            "game_score": round(t["gmsc"] / g, 2),
            "durable_gmsc": t["gmsc"] / g * min(1.0, g / FULL_GAMES),
            "durable_pts": t["pts"] / g * min(1.0, g / FULL_GAMES),
            "def_stocks": (t["stl"] + t["blk"] + 0.3 * t["drb"]) / max(t["minutes"], 1) * 36 * min(1.0, mpg / FULL_MINUTES),
            "club_pct": round(club["wins"] / club["games"], 3),
            "club_drtg": round(club["allowed"] / max(club["opp_poss"], 1) * 100, 1),
            "prior_games": prior_g, "prior_game_score": None if prior_gs is None else round(prior_gs, 2),
        }
    return out, clubs


def eligible(award, c):
    if award in ("mvp", "all_nba"):
        return c["games"] >= MIN_GAMES
    if award in ("dpoy", "all_defensive"):
        return c["games"] >= MIN_GAMES and c["mpg"] >= DEF_MINUTES
    if award == "roy":
        return c["rookie"] and c["games"] >= MIN_ROOKIE_GAMES
    if award == "all_rookie":
        return c["rookie"] and c["games"] >= MIN_ALL_ROOKIE_GAMES
    if award == "smoy":
        return c["games"] >= MIN_GAMES and c["starts"] < c["games"] - c["starts"]
    if award == "mip":
        return (c["games"] >= MIN_GAMES and not c["rookie"] and c["prior_games"] >= MIN_PRIOR_GAMES
                and c["prior_game_score"] is not None)
    return False


CRITERIA = {      # (first, second); a list is the mean of its z-scores
    "mvp": ([lambda c: c["durable_gmsc"], lambda c: c["durable_pts"]], lambda c: c["club_pct"]),
    "roy": ([lambda c: c["durable_gmsc"], lambda c: c["durable_pts"]], lambda c: c["club_pct"]),
    "dpoy": (lambda c: c["def_stocks"], lambda c: -c["club_drtg"]),
    "smoy": ([lambda c: c["game_score"], lambda c: c["pts"]], lambda c: c["club_pct"]),
    "mip": (lambda c: c["game_score"] - c["prior_game_score"], lambda c: c["game_score"]),
}
BASE = {"all_nba": "mvp", "all_defensive": "dpoy", "all_rookie": "roy"}


def _z(values):
    m, s = mean(values), pstdev(values) or 1.0
    return [(v - m) / s for v in values]


def lens_scores(award, pool):
    """[(name, first z, second z)] for the eligible pool."""
    first, second = CRITERIA[BASE.get(award, award)]
    names = sorted(pool)
    parts = [_z([f(pool[n]) for n in names]) for f in (first if isinstance(first, list) else [first])]
    a, b = [mean(v) for v in zip(*parts)], _z([second(pool[n]) for n in names])
    return list(zip(names, a, b))


def lenses(award, electorate):
    lo, hi = LENS[award]
    return [lo + (hi - lo) * (i + 0.5) / electorate for i in range(electorate)]


def _ordered(scored, t):
    return [n for _, n in sorted(((-(1 - t) * a - t * b), n) for n, a, b in scored)]


# -- coaches ---------------------------------------------------------------------------------------------------
def coaches(root):
    """{club: coach at the season's end who coached at least half of it}; Miami's from its simulated team config."""
    root = Path(root)
    out = {}
    for club, info in _read(root / STAFFS)["clubs"].items():
        last = info["head_coaches"][-1]
        if last["window"][1] >= 1.0 and last["window"][1] - last["window"][0] >= 0.5:
            out[club] = last["name"]
    team = _read(root / f"career/Dwyane_Wade/{SEASON}/00_Team/team_config.json")
    out["Miami Heat"] = team["head_coach"]
    return out


def coach_pool(root, clubs):
    prior = _read(Path(root) / PRIOR_STANDINGS)["clubs"]
    out = {}
    for club, coach in coaches(root).items():
        c = clubs.get(club)
        if not c or club not in prior:
            continue
        p = prior[club]
        expected = 0.5 + 0.6 * (p["wins"] / (p["wins"] + p["losses"]) - 0.5)
        pct = c["wins"] / c["games"]
        out[coach] = {"coach": coach, "team": club, "wins": int(c["wins"]), "losses": int(c["games"] - c["wins"]),
                      "pct": round(pct, 3), "prior": f"{p['wins']}-{p['losses']}", "expected_pct": round(expected, 3),
                      "above_expected": round(pct - expected, 3)}
    return out


# -- tallies ---------------------------------------------------------------------------------------------------
def _ballot_groups(scored, t):
    """A voter's order as groups of equal score (a voter cannot separate identical evidence)."""
    groups, last = [], None
    for score, name in sorted((round(-(1 - t) * a - t * b, 9), n) for n, a, b in scored):
        if score == last:
            groups[-1].append(name)
        else:
            groups.append([name])
        last = score
    return groups


def tally_single(award, scored, electorate, points):
    """Equal scores on one ballot share the places they cover: the mean of those places' points, and a first-place
    vote is split. Nothing is ordered by name."""
    totals, firsts, places = defaultdict(float), defaultdict(float), defaultdict(lambda: [0.0] * len(points))
    for t in lenses(award, electorate):
        place = 0
        for group in _ballot_groups(scored, t):
            if place >= len(points):
                break
            covered = list(range(place, place + len(group)))
            share = sum(points[i] for i in covered if i < len(points)) / len(group)
            for name in group:
                totals[name] += share
                firsts[name] += (0 in covered) / len(group)
                for i in covered:
                    if i < len(points):
                        places[name][i] += 1 / len(group)
            place += len(group)
    num = lambda x: int(x) if float(x).is_integer() else round(x, 2)
    rows = sorted(totals, key=lambda n: (-round(totals[n], 6), -round(firsts[n], 6), n))
    return [{"player": n, "points": num(totals[n]), "first_place": num(firsts[n]),
             "votes_by_place": [num(x) for x in places[n]]} for n in rows]


def winners(votes):
    """The top of the tally; equal points and first-place votes name co-winners."""
    key = lambda v: (round(v["points"], 6), round(v["first_place"], 6))
    return [v["player"] for v in votes if votes and key(v) == key(votes[0])]


def tally_teams(award, scored, electorate, team_points, per_team, groups=None, exclude=None):
    """Team ballots. `per_team` slots by position group (or a count regardless of position); `exclude(voter)` names
    a club whose players that voter may not choose."""
    totals, firsts = defaultdict(int), defaultdict(int)
    for i, t in enumerate(lenses(award, electorate)):
        barred = exclude(i) if exclude else None
        order = [n for n in _ordered(scored, t) if not barred or groups["team"][n] != barred]
        for team_no, pts in enumerate(team_points):
            for n in _pick(order, per_team, groups):
                order.remove(n)
                totals[n] += pts
                firsts[n] += team_no == 0
    return sorted(totals, key=lambda n: (-totals[n], -firsts[n], n)), totals, firsts


def _pick(order, per_team, groups):
    if isinstance(per_team, int):
        return order[:per_team]
    need, out = dict(per_team), []
    for n in order:
        g = groups["position"].get(n)
        if need.get(g, 0) > 0:
            out.append(n)
            need[g] -= 1
        if not any(need.values()):
            break
    return out


def select_teams(ranked, totals, firsts, teams, per_team, positions):
    """Fill the teams in order of points; a tie at a team's last spot names both players."""
    left, out = list(ranked), []
    for _ in range(teams):
        chosen = []
        slots = {"all": per_team} if isinstance(per_team, int) else dict(per_team)
        for n in list(left):
            g = "all" if isinstance(per_team, int) else positions.get(n)
            if slots.get(g, 0) > 0:
                chosen.append(n)
                slots[g] -= 1
            elif g in slots and chosen and any(c for c in chosen if ("all" if isinstance(per_team, int) else positions.get(c)) == g
                                               and (totals[c], firsts[c]) == (totals[n], firsts[n])):
                chosen.append(n)                            # tied with the last player chosen at his position
            if not any(slots.values()) and not _tied_next(left, n, chosen, totals, firsts):
                break
        for n in chosen:
            left.remove(n)
        out.append(chosen)
    return out


def _tied_next(left, n, chosen, totals, firsts):
    i = left.index(n)
    return i + 1 < len(left) and (totals[left[i + 1]], firsts[left[i + 1]]) == (totals[n], firsts[n])


# -- decisions -------------------------------------------------------------------------------------------------
def _player_row(c, extra=None):
    row = {k: c[k] for k in ("player", "team", "games", "mpg", "pts", "reb", "ast", "stl", "blk", "game_score")}
    row.update(extra or {})
    return row


def decide_one(award, rows, root):
    pool_all, clubs = candidates(root, rows)
    a_id, n, ballot = award["id"], award["electorate"], award["ballot"]
    base = {"id": f"{SEASON}-{a_id}", "award": a_id, "name": award["name"], "announced_on": award["announced"],
            "electorate": n, "voters": award["voters"], "ballot": ballot, "lens": list(LENS[a_id]),
            "evidence_through": SEASON_END}
    if a_id == "coy":
        pool = coach_pool(root, clubs)
        scored = list(zip(sorted(pool), _z([pool[c]["above_expected"] for c in sorted(pool)]),
                          _z([pool[c]["pct"] for c in sorted(pool)])))
        votes = tally_single(a_id, scored, n, ballot)
        return dict(base, winners=winners(votes),
                    tally=[dict(pool[v["player"]], points=v["points"], first_place=v["first_place"],
                                votes_by_place=v["votes_by_place"]) for v in votes])
    pool = {k: c for k, c in pool_all.items() if eligible(a_id, c)}
    scored = lens_scores(a_id, pool)
    if "teams" not in award:
        votes = tally_single(a_id, scored, n, ballot)
        extra = (lambda c: {"prior_game_score": c["prior_game_score"]}) if a_id == "mip" else \
                (lambda c: {"starts": c["starts"]}) if a_id == "smoy" else \
                (lambda c: {"club_drtg": c["club_drtg"]}) if a_id == "dpoy" else (lambda c: {"club_pct": c["club_pct"]})
        return dict(base, winners=winners(votes),
                    tally=[_player_row(pool[v["player"]], dict(extra(pool[v["player"]]), points=v["points"],
                                                              first_place=v["first_place"], votes_by_place=v["votes_by_place"]))
                           for v in votes])
    per_team = award.get("by_position") or award["picks_per_team"]
    groups = {"position": {k: c["position"] for k, c in pool.items()}, "team": {k: c["team"] for k, c in pool.items()}}
    exclude = None
    if "own players" in award["voters"]:
        clubs_sorted = sorted(c for cs in _read(Path(root) / CONFERENCES)["conferences"].values() for c in cs)[:n]
        exclude = lambda i: clubs_sorted[i]
    if not isinstance(per_team, int):
        scored = [s for s in scored if groups["position"].get(s[0])]
    ranked, totals, firsts = tally_teams(a_id, scored, n, ballot, per_team, groups, exclude)
    teams = select_teams(ranked, totals, firsts, award["teams"], per_team, groups["position"])
    return dict(base, teams=[{"team": TEAM_NAMES[i + 1], "players": [
        _player_row(pool[p], {"position": pool[p]["position"], "points": totals[p], "first_team_votes": firsts[p]})
        for p in t]} for i, t in enumerate(teams)],
        others=[{"player": p, "team": pool[p]["team"], "points": totals[p]} for p in ranked
                if not any(p in t for t in teams)][:10])


def read_record(root=ROOT):
    path = Path(root) / RECORD
    if path.is_file():
        return _read(path)
    return {"schema_version": 1, "season": SEASON, "kind": "season_awards",
            "rule": __doc__.split("\n\n", 1)[1].strip(), "calendar": CALENDAR.as_posix(), "decisions": []}


def due(root, clock):
    return [a for a in calendar(root)["awards"] if a["announced"] <= clock]


def decide(root=ROOT, clock=None):
    """Close every season award announced on or before the clock. Returns the new decisions."""
    from .write_back import clock as career_clock, closed_results
    root = Path(root)
    clock = clock or career_clock(root)
    record = read_record(root)
    done = {d["award"] for d in record["decisions"]}
    pending = [a for a in due(root, clock) if a["id"] not in done]
    if not pending:
        return []
    rows = closed_results(root, SEASON, SEASON_END)
    new = [decide_one(a, rows, root) for a in pending]
    record["decisions"] += new
    record["decisions"].sort(key=lambda d: d["announced_on"])
    (root / RECORD).write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    if _record_wade(root, record):
        from . import standing
        standing.record(root, clock, "honor_recorded", PAGE.as_posix())
    (root / PAGE).write_text(page(record, clock, root), encoding="utf-8")
    return new


def honors(decision):
    """[(player, honor name, id suffix)] named by a decision."""
    if "teams" in decision:
        label = {"all_nba": "All-NBA", "all_defensive": "All-Defensive", "all_rookie": "All-Rookie"}[decision["award"]]
        return [(p["player"], f"{label} {t['team']}", t["team"].split()[0].lower())
                for t in decision["teams"] for p in t["players"]]
    return [(w, decision["name"], "") for w in decision["winners"]]


SHORT = {"Most Valuable Player": "MVP", "Rookie of the Year": "ROY", "Defensive Player of the Year": "DPOY",
         "Sixth Man of the Year": "6MOY", "Most Improved Player": "MIP", "Coach of the Year": "COY"}


def short_name(name):
    if name in SHORT:
        return SHORT[name]
    label, team = name.rsplit(" ", 2)[0], name.split()[-2]
    return f"{label} {dict(First='1st', Second='2nd', Third='3rd')[team]}"


def _record_wade(root, record):
    path = root / PLAYER / "awards.json"
    data = _read(path) if path.is_file() else {"schema_version": 1, "awards": []}
    have = {a["id"] for a in data["awards"]}
    added = 0
    for d in record["decisions"]:
        for player, name, suffix in honors(d):
            award_id = d["id"] + (f"-{suffix}" if suffix else "")
            if player != WADE or award_id in have:
                continue
            data["awards"].append({"id": award_id, "name": name, "short_name": short_name(name), "status": "earned",
                                   "competition": "regular", "season": SEASON, "period_start": "2003-10-28",
                                   "period_end": SEASON_END, "awarded_on": d["announced_on"],
                                   "source": PAGE.relative_to(PLAYER).as_posix() + "#" + d["name"].lower().replace(" ", "-")})
            added += 1
    data["awards"].sort(key=lambda a: (a["awarded_on"], a["id"]))
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return added


# -- page ------------------------------------------------------------------------------------------------------
def _table(headers, rows):
    return ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"] + \
           ["| " + " | ".join(str(x) for x in r) + " |" for r in rows]


def page(record, clock, root=ROOT):
    cal = {a["id"]: a for a in calendar(root)["awards"]}
    lines = [f"# {SEASON} season awards", "",
             f"Decided on each award's real announcement date from closed simulated results through {SEASON_END} "
             "(`runtime/season_awards.py`); no real 2004 vote is used. Every voter in the real electorate files a ballot; "
             f"voters differ only in how they weigh the award's two criteria. Through {clock}.", ""]
    decided = {d["award"]: d for d in record["decisions"]}
    lines += ["## Calendar", ""] + _table(["Announced", "Award", "Voters", "Ballot", "Status"], [
        [a["announced"], a["name"], f"{a['electorate']} {a['voters']}", "-".join(map(str, a["ballot"])),
         "decided" if a["id"] in decided else "pending"] for a in cal.values()]) + [""]
    for d in record["decisions"]:
        lines += [f"## {d['name']}", "", f"Announced {d['announced_on']}; {d['electorate']} {d['voters']}, "
                  f"ballot {'-'.join(map(str, d['ballot']))}.", ""]
        if "teams" in d:
            for t in d["teams"]:
                lines += [f"### {t['team']}", ""] + _table(
                    ["Player", "Pos", "Club", "G", "MPG", "PTS", "REB", "AST", "STL", "BLK", "GmSc", "Points", "1st-team votes"],
                    [[p["player"], p["position"], p["team"], p["games"], p["mpg"], p["pts"], p["reb"], p["ast"], p["stl"],
                      p["blk"], p["game_score"], p["points"], p["first_team_votes"]] for p in t["players"]]) + [""]
            if d.get("others"):
                lines += ["Also receiving votes: " + ", ".join(f"{o['player']} ({o['team']}) {o['points']}" for o in d["others"]) + ".", ""]
            continue
        label = "WINNER" if len(d["winners"]) == 1 else "CO-WINNER"
        if d["award"] == "coy":
            lines += _table(["#", "Coach", "Club", "Record", "2002-03", "Expected pct", "Points", "1st"],
                            [[label if v["coach"] in d["winners"] else i + 1, v["coach"], v["team"], f"{v['wins']}-{v['losses']}",
                              v["prior"], v["expected_pct"], v["points"], v["first_place"]] for i, v in enumerate(d["tally"][:3])])
        else:
            lines += _table(["#", "Player", "Club", "G", "MPG", "PTS", "REB", "AST", "STL", "BLK", "GmSc", "Points", "1st"],
                            [[label if v["player"] in d["winners"] else i + 1, v["player"], v["team"], v["games"], v["mpg"],
                              v["pts"], v["reb"], v["ast"], v["stl"], v["blk"], v["game_score"], v["points"], v["first_place"]]
                             for i, v in enumerate(d["tally"][:3])])
        lines += ["", f"Complete tally: `season_awards.json` ({len(d['tally'])} receiving votes).", ""]
    return "\n".join(lines).rstrip() + "\n"


def season_award_errors(root=ROOT):
    from .write_back import clock as career_clock
    root = Path(root)
    if not (root / CALENDAR).is_file():
        return []
    clock = career_clock(root)
    done = {d["award"] for d in read_record(root)["decisions"]}
    return [f"{a['name']} was announced {a['announced']} and is not decided (python scripts/decide_awards.py --write)"
            for a in due(root, clock) if a["id"] not in done]
