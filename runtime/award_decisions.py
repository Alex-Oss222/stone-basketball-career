"""Weekly and monthly NBA awards for 2003-04: Player of the Week, Player of the Month, Rookie of the Month.

Each award is split East and West (from 2001-02, `nba_awards_catalog.json`). An award closes on its
announcement date and only from closed regular-season results dated inside its period
(`write_back.closed_results`), so no later game, real winner or historical vote enters it.

Periods (judgement, from the NBA's calendar of the era):
- Player of the Week: Monday to Sunday (the opening week runs from opening night, October 28), announced
  the Monday after; the final week ends on the last regular-season day.
- Player and Rookie of the Month: calendar months, October folded into November because the season opened
  October 28; announced two days after the month ends. The exact announcement day is an assumption.

Selection: the league office named the winners without a published ballot, so the branch ranks the
evidence. Each game is scored with Hollinger's Game Score (PTS + 0.4 FGM - 0.7 FGA - 0.4 missed FT
+ 0.7 ORB + 0.3 DRB + STL + 0.7 AST + 0.7 BLK - 0.4 PF - TOV), and winning counts:
- Player of the Week: at least two games; total Game Score + 3 per club win in his games.
- Player of the Month: at least 60% of his club's games in the period; Game Score per game + 12 x his club's
  win share in his games.
- Rookie of the Month: first-season players (the registry's 2003 draft class and sourced identities with no earlier
  NBA season); at least
  half his club's games; Game Score per game + 4 x win share.
The highest score wins; the next two are the published shortlist. Decisions are appended once to
`award_decisions.json` and never recomputed. A Wade win is added to his `awards.json` with the page as its
source. Rules apply to every player alike: no seniority, reputation or market bonus.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEASON = "2003-04"
SEASON_START, SEASON_END = "2003-10-28", "2004-04-14"
LEAGUE = Path(f"career/Dwyane_Wade/Stats_and_Awards/League/{SEASON}")
DECISIONS = LEAGUE / "award_decisions.json"
DRAWS = LEAGUE / "Award_Draws"
CONFERENCES = Path("library/2003/league/nba_2003_04_conferences.json")
PLAYER = Path("career/Dwyane_Wade")
WADE = "Dwyane Wade"
MONTH_DIRS = {10: "10_October", 11: "11_November", 12: "12_December", 1: "01_January", 2: "02_February",
              3: "03_March", 4: "04_April"}
MONTH_NAMES = {10: "October", 11: "November", 12: "December", 1: "January", 2: "February", 3: "March", 4: "April"}
AWARDS = {"player_of_week": "Player of the Week", "player_of_month": "Player of the Month",
          "rookie_of_month": "Rookie of the Month"}
SHORT = {"player_of_week": "POW", "player_of_month": "POM", "rookie_of_month": "ROM"}
WEEK_WIN_BONUS, MONTH_WIN_WEIGHT, ROOKIE_WIN_WEIGHT = 3.0, 12.0, 4.0
WEEK_MIN_GAMES, MONTH_SHARE, ROOKIE_SHARE = 2, 0.6, 0.5
MONTH_ANNOUNCE_DAYS = 2


def game_score(p):
    return (p["pts"] + 0.4 * p["fgm"] - 0.7 * p["fga"] - 0.4 * (p["fta"] - p["ftm"]) + 0.7 * p["orb"]
            + 0.3 * p["drb"] + p["stl"] + 0.7 * p["ast"] + 0.7 * p["blk"] - 0.4 * p["pf"] - p["tov"])


def _d(text):
    return date.fromisoformat(text)


def periods():
    """Every award period of the season: (award, start, end, announced_on)."""
    out = []
    start, last = _d(SEASON_START), _d(SEASON_END)
    while start <= last:
        end = min(start + timedelta(days=6 - start.weekday()), last)
        out.append(("player_of_week", start.isoformat(), end.isoformat(), (end + timedelta(days=1)).isoformat()))
        start = end + timedelta(days=1)
    for first in ("2003-10-28", "2003-12-01", "2004-01-01", "2004-02-01", "2004-03-01", "2004-04-01"):
        f = _d(first)
        nxt = date(f.year + (f.month == 12), f.month % 12 + 1, 1) if f.month != 10 else date(2003, 12, 1)
        end = min(nxt - timedelta(days=1), last)
        announced = (end + timedelta(days=MONTH_ANNOUNCE_DAYS)).isoformat()
        for award in ("player_of_month", "rookie_of_month"):
            out.append((award, first, end.isoformat(), announced))
    return sorted(out, key=lambda p: (p[3], p[0]))


def conferences(root=ROOT):
    data = json.loads((Path(root) / CONFERENCES).read_text(encoding="utf-8"))["conferences"]
    return {team: conf for conf, teams in data.items() for team in teams}


def rookies(root=ROOT):
    """First-season players by name, from sourced identity records only: the registry's 2003 draft-rights
    cohort, unattached identities with no NBA season before 2003-04 (Haslem), and Wade. An undrafted rookie
    on a real club without such a record is not yet recognised (a known gap, not a judgement)."""
    root = Path(root)
    registry = json.loads((root / "career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json").read_text(encoding="utf-8"))
    registry = registry["players"] if isinstance(registry, dict) else registry
    bbrs = {p["bbr_id"] for p in registry if p.get("cohort") == "2003_draft_rights" and p.get("bbr_id")}
    unattached = json.loads((root / "library/2003/league/nba_2003_unattached_identities.json").read_text(encoding="utf-8"))
    bbrs |= {p["bbr_id"] for p in unattached["players"] if p.get("service_basis", "").startswith("No NBA season before")}
    names = {WADE}
    from .rotations import load_rosters
    for club in load_rosters(SEASON, root).values():
        names |= {p["player_id"] for p in club["players"] if p.get("bbr_id") in bbrs}
    roster = json.loads((root / f"career/Dwyane_Wade/{SEASON}/00_Team/Team/Roster/roster.json").read_text(encoding="utf-8"))
    names |= {p["name"] for p in roster["players"] if p.get("bbr_id") in bbrs}
    return names


def _lines(rows, start, end):
    """Per player: his games in the period, with club, Game Score and whether the club won."""
    out, club_games = defaultdict(list), defaultdict(int)
    for row in rows:
        r = row["result"]
        if not start <= r["game_date"] <= end:
            continue
        for side, other in (("home", "away"), ("away", "home")):
            team = r[side]
            club_games[team] += 1
            won = r["final_score"][side] > r["final_score"][other]
            for p in r["player_stats"][side]:
                if p.get("seconds", p.get("minutes", 0)) and p["minutes"] > 0:
                    out[p["player_id"]].append({"team": team, "won": won, "gmsc": game_score(p), "pts": p["pts"],
                                                "reb": p["orb"] + p["drb"], "ast": p["ast"], "date": r["game_date"]})
    return out, club_games


def registry_names(root=ROOT):
    """{name in the season's real roster file: the registry's name for the same bbr_id} where they differ. The roster
    file keys a few players by a later name (Metta World Peace for the 2003-04 Ron Artest); records use the dated one."""
    from .rotations import load_rosters
    root = Path(root)
    registry = json.loads((root / "career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json").read_text(encoding="utf-8"))
    by_bbr = {p["bbr_id"]: p["name"] for p in (registry["players"] if isinstance(registry, dict) else registry) if p.get("bbr_id")}
    out = {}
    for club in load_rosters(SEASON, root).values():
        for p in club["players"]:
            name = by_bbr.get(p.get("bbr_id"))
            if name and name != p["player_id"]:
                out[p["player_id"]] = name
    return out


def rank(award, start, end, rows, conf, first_years, names=None):
    lines, club_games = _lines(rows, start, end)
    names = names or {}
    table = defaultdict(list)
    for player, games in lines.items():
        team = sorted(games, key=lambda g: g["date"])[-1]["team"]       # his club at the period's end
        n, wins = len(games), sum(g["won"] for g in games)
        total = sum(g["gmsc"] for g in games)
        if award == "player_of_week":
            if n < WEEK_MIN_GAMES:
                continue
            score = total + WEEK_WIN_BONUS * wins
        else:
            if award == "rookie_of_month" and player not in first_years:
                continue
            share = MONTH_SHARE if award == "player_of_month" else ROOKIE_SHARE
            if n < share * club_games[team]:
                continue
            weight = MONTH_WIN_WEIGHT if award == "player_of_month" else ROOKIE_WIN_WEIGHT
            score = total / n + weight * wins / n
        table[conf[team]].append({
            "player": names.get(player, player), "team": team, "games": n, "wins": wins, "losses": n - wins,
            "pts": round(sum(g["pts"] for g in games) / n, 1), "reb": round(sum(g["reb"] for g in games) / n, 1),
            "ast": round(sum(g["ast"] for g in games) / n, 1), "game_score": round(total / n, 2), "score": round(score, 3)})
    # Scores compare at two decimals; a tie at the top is drawn by the engine, never by name or float noise.
    return {c: sorted(rows_, key=lambda x: (-round(x["score"], 2), x["player"]))[:3] for c, rows_ in sorted(table.items())}


def filed_page(award, end):
    """The calendar bucket containing the period's end date: its week page for a weekly award, else its month page."""
    d = _d(end)
    month = MONTH_DIRS[d.month]
    if award != "player_of_week":
        return LEAGUE / month / "League_Awards.md"
    week = 1 if d.day <= 7 else 2 if d.day <= 14 else 3 if d.day <= 21 else 4
    return LEAGUE / month / f"Week_{week}" / "League_Awards.md"


def read_decisions(root=ROOT):
    path = Path(root) / DECISIONS
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"schema_version": 1, "season": SEASON, "kind": "award_decisions",
            "rule": __doc__.split("\n\n", 1)[1].strip(), "decisions": []}


def due(clock):
    return [p for p in periods() if p[3] <= clock]


def tie_packet(award_id, award, conference, start, end, announced, tied):
    return {"event_id": award_id, "date": announced,
            "question": f"Who is the {conference} {AWARDS[award]} for {start} to {end}: " + " or ".join(tied) + "?",
            "decider": "NBA league office (engine draw between equal evidence)",
            "options": {name: round(1 / len(tied), 6) for name in tied},
            "basis": "Equal award scores at two decimals under runtime/award_decisions.py; no name, reputation or market tiebreak."}


def decide(root=ROOT, clock=None):
    """Close every award announced on or before the clock. Returns the new decisions.

    A tie at the top writes an engine decision packet (`Award_Draws/`) and waits for its drawn result
    (`python scripts/draw_decisions.py`); the other awards close meanwhile."""
    from .write_back import clock as career_clock, closed_results
    root = Path(root)
    clock = clock or career_clock(root)
    record = read_decisions(root)
    done = {(d["award"], d["period_start"], d["conference"]) for d in record["decisions"]}
    pending = [p for p in due(clock) if any((p[0], p[1], c) not in done for c in ("East", "West"))]
    if not pending:
        return []
    rows = closed_results(root, SEASON, clock)
    conf, first, names = conferences(root), rookies(root), registry_names(root)
    new = []
    for award, start, end, announced in pending:
        shortlist = rank(award, start, end, rows, conf, first, names)
        for c in ("East", "West"):
            if (award, start, c) in done:
                continue
            listed = shortlist.get(c, [])
            award_id = f"{SEASON}-{award}-{start}-{c.lower()}"
            winner, draw = (listed[0]["player"] if listed else None), None
            tied = [x["player"] for x in listed if listed and round(x["score"], 2) == round(listed[0]["score"], 2)]
            if len(tied) > 1:
                packet_path = root / DRAWS / f"{award_id}.decision.json"
                result_path = packet_path.with_name(f"{award_id}.decision.result.json")
                if not packet_path.is_file():
                    packet_path.parent.mkdir(parents=True, exist_ok=True)
                    packet_path.write_text(json.dumps(tie_packet(award_id, award, c, start, end, announced, tied), indent=1,
                                                      ensure_ascii=False) + "\n", encoding="utf-8")
                if not result_path.is_file():
                    continue                                   # waits for the engine's draw
                winner = json.loads(result_path.read_text(encoding="utf-8"))["outcome"]
                draw = (DRAWS / result_path.name).as_posix()
                listed = sorted(listed, key=lambda x: x["player"] != winner)        # the drawn winner first, order kept
            entry = {"id": award_id, "award": award, "name": AWARDS[award],
                     "conference": c, "period_start": start, "period_end": end, "announced_on": announced,
                     "filed_on": filed_page(award, end).as_posix(),
                     "shortlist": [dict(x, rank=i + 1) for i, x in enumerate(listed)], "winner": winner}
            if draw:
                entry["tie_draw"] = draw
            new.append(entry)
    if not new:
        return []
    record["decisions"] += new
    record["decisions"].sort(key=lambda d: (d["announced_on"], d["award"], d["conference"]))
    (root / DECISIONS).write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    _record_wade(root, record)
    render_pages(root, record, clock)
    return new


def _record_wade(root, record):
    path = root / PLAYER / "awards.json"
    data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"schema_version": 1, "awards": []}
    have = {a["id"] for a in data["awards"]}
    for d in record["decisions"]:
        if d["winner"] != WADE or d["id"] in have:
            continue
        source = Path(d["filed_on"]).relative_to(PLAYER).as_posix() + "#" + d["name"].lower().replace(" ", "-")
        data["awards"].append({"id": d["id"], "name": f"{d['conference']}ern Conference {d['name']}",
                               "short_name": f"{d['conference']} {SHORT[d['award']]}", "status": "earned",
                               "competition": "regular", "season": SEASON, "period_start": d["period_start"],
                               "period_end": d["period_end"], "awarded_on": d["announced_on"], "source": source})
    data["awards"].sort(key=lambda a: (a["awarded_on"], a["id"]))
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# -- pages -------------------------------------------------------------------------------------------------
def _long(d):
    x = _d(d)
    return f"{x.strftime('%B')} {x.day}, {x.year}"


def _section(name, decisions, clock):
    """One shortlist table per award period, three slots per conference (padded when fewer were eligible)."""
    header = ["| Conference | Rank slot | Player | Team | Evidence | Result |", "| --- | ---: | --- | --- | --- | --- |"]
    if not decisions:
        return [f"## {name}", ""] + header + [f"| {c} | {i} | Not shortlisted | N/A | No closed period | Pending |"
                                             for c in ("East", "West") for i in (1, 2, 3)] + [""]
    out = [f"## {name}", ""]
    for start in sorted({d["period_start"] for d in decisions}):
        period = [d for d in decisions if d["period_start"] == start]
        label = f"{_long(period[0]['period_start'])} to {_long(period[0]['period_end'])}"
        out += [f"### {label} (announced {_long(period[0]['announced_on'])})", ""] + header
        for c in ("East", "West"):
            d = next((d for d in period if d["conference"] == c), None)
            listed = d["shortlist"] if d else []
            for x in listed:
                result = "**WINNER**" if x["rank"] == 1 else "Shortlist"
                evidence = (f"{x['games']} G, {x['wins']}-{x['losses']} in his games, {x['pts']} PTS, {x['reb']} REB, "
                            f"{x['ast']} AST, Game Score {x['game_score']} a game; score {x['score']}")
                out.append(f"| {c} | {x['rank']} | {x['player']} | {x['team']} | {evidence} | {result} |")
            for i in range(len(listed) + 1, 4):
                why = "Awaiting the engine's tie draw" if d is None else "No further eligible player"
                out.append(f"| {c} | {i} | Not shortlisted | N/A | {why} | {'Pending' if d is None else 'N/A'} |")
        out.append("")
    return out


def _replace_body(text, sections, record_lines, status_line):
    head, _, rest = text.partition("\n## ")
    tail_marker = "\n[Awards procedure and research]"
    tail = text[text.index(tail_marker):] if tail_marker in text else ""
    by_week = ""
    if "\n## By week" in text:
        by_week = text[text.index("\n## By week"):text.index(tail_marker)] if tail else text[text.index("\n## By week"):]
    lines = head.split("\n")
    lines = [status_line if l.startswith("As of ") else l for l in lines]
    body = "\n".join(lines).rstrip() + "\n\n" + "\n".join(sum(sections, [])) + "\n" + "\n".join(record_lines) + "\n"
    return body + by_week.rstrip("\n") + ("\n" if by_week else "") + tail


def render_pages(root, record, clock):
    root = Path(root)
    pages = defaultdict(list)
    for d in record["decisions"]:
        pages[d["filed_on"]].append(d)
    for rel in sorted(pages):
        path = root / rel
        if not path.is_file():
            continue
        decisions = pages[rel]
        names = ["player_of_week"] if "Week_" in rel else ["player_of_month", "rookie_of_month"]
        sections = [_section(AWARDS[a], [d for d in decisions if d["award"] == a], clock) for a in names]
        record_lines = ["## Decision record", ""]
        for d in decisions:
            record_lines.append(f"- {d['conference']} {d['name']}, {_long(d['period_start'])} to {_long(d['period_end'])}, "
                                f"announced {_long(d['announced_on'])}: **{d['winner'] or 'no award'}**. Ranked from closed "
                                f"branch results only (`award_decisions.json`, rule in `runtime/award_decisions.py`)"
                                + (f"; equal scores at the top, winner drawn by the engine (`{Path(d['tie_draw']).name}`)." if d.get("tie_draw") else "."))
        record_lines.append("")
        closed = sorted({d["announced_on"] for d in decisions})
        status = f"As of {_long(clock)}: {len(decisions)} award decision(s) closed, announced {', '.join(_long(c) for c in closed)}."
        text = path.read_text(encoding="utf-8")
        new = _replace_body(text, sections, record_lines, status)
        new = new.replace("Official award window: not recorded. Announcement date: not recorded.",
                          "Official award window and announcement date: listed with each decision below.")
        if new != text:
            path.write_text(new, encoding="utf-8")
    _week_counts(root, record)


def _week_counts(root, record):
    """Month pages: each week row's closed-decision count and status."""
    import re
    counts = defaultdict(int)
    for d in record["decisions"]:
        counts[d["filed_on"]] += 1
    for month in sorted({str(Path(d["filed_on"]).parent.parent) for d in record["decisions"] if "Week_" in d["filed_on"]}):
        page = root / month / "League_Awards.md"
        if not page.is_file():
            continue
        text = page.read_text(encoding="utf-8")

        def row(m):
            n = counts.get(f"{month}/{m.group(2)}/League_Awards.md", 0)
            return f"| [{m.group(1)}]({m.group(2)}/League_Awards.md) | {m.group(3)} | {n} | {'Decided' if n else 'No award filed'} |"
        new = re.sub(r"^\| \[(Week \d)\]\((Week_\d)/League_Awards\.md\) \| ([^|]+?) \| \d+ \| [^|]+ \|$", row, text, flags=re.M)
        if new != text:
            page.write_text(new, encoding="utf-8")


def award_errors(root=ROOT):
    """An award announced on or before the clock that has no closed decision."""
    from .write_back import clock as career_clock
    clock = career_clock(root)
    done = {(d["award"], d["period_start"], d["conference"]) for d in read_decisions(root)["decisions"]}
    return [f"{c} {AWARDS[a]} for {s} to {e} was announced {n} and is not decided (python scripts/decide_awards.py --write; "
            f"a tie waits for python scripts/draw_decisions.py)"
            for a, s, e, n in due(clock) for c in ("East", "West") if (a, s, c) not in done]
