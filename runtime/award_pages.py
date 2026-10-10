"""The NBA award hubs: each season's `Stats_and_Awards/League/<season>/League_Awards.md` and the status line of its
month pages, rebuilt from the source records only (AGENTS.md, Stats and awards; Derived records).

Sources, all read and never written here: the weekly and monthly decisions (`award_decisions.json`,
`runtime/award_decisions.py`), the season awards (`season_awards.json`, `runtime/season_awards.py`) with the season's
researched award calendar (`library/<year>/league/nba_<season>_season_awards.json`), the All-Star selections
(`all_star.json`, `runtime/all_star.py`) with their calendar, and the playoff record (`playoffs.json`,
`runtime/playoffs.py`) for the champion. The Finals MVP is a season-award decision.

The season page carries its own season in the title and coverage line and is dated by the career clock; a closed
season's page is dated at the end of its league year (`season_close_window_end`, June 30), after which none of its
records can close, so a closed season's pages stop moving with the clock. Its sections keep the layout the rollover
template had (`runtime/season_pages.py`): individual awards with the top three of each closed vote and **WINNER** on
the first row only once the award's announcement date has passed (an open award keeps empty rank slots with its close
date), the All-NBA, All-Defensive and All-Rookie teams, the voting procedure from the season's calendar, the All-Star
selections, the champion and the Finals MVP under Other honors, and the weekly and monthly decisions counted by month on
the page each is filed on (`award_decisions.filed_page`, the month's week pages included). Nothing reads a previous
season's page. Each month page's 'As of' line is restated from the same records: its own month decisions in the words
`award_decisions.render_pages` uses, and the Player of the Week decisions filed on its week pages.

`write_pages` runs in every write-back (`write_back.run`), the driver's daily light run included, so a decision day's
commit carries the week rows `award_decisions.render_pages` writes and the month line and hub counts restated with
them; the write-back's --check reports a page that differs (`write_back_errors` with cards). `page_errors` is the
validation: every season page and month status line agrees with the records it shows (titles, counts by month, closed
counts, winners and selections), its 'As of' date aside.
"""
from __future__ import annotations

from calendar import monthrange
from collections import Counter, defaultdict
from datetime import date
import json
from pathlib import Path
import re
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
LEAGUE = Path("career/Dwyane_Wade/Stats_and_Awards/League")
PAGE = "League_Awards.md"
INDIVIDUAL = (("mvp", "Most Valuable Player"), ("roy", "Rookie of the Year"), ("dpoy", "Defensive Player of the Year"),
              ("smoy", "Sixth Man of the Year"), ("mip", "Most Improved Player"), ("coy", "Coach of the Year"))
TEAM_AWARDS = (("all_nba", "All-NBA teams", "All-NBA Teams", 3), ("all_defensive", "All-Defensive teams", "All-Defensive Teams", 2),
               ("all_rookie", "All-Rookie teams", "All-Rookie Teams", 2))
TEAM_LABELS = ("First", "Second", "Third")
SLOT_NAMES = {"G": "Guard", "F": "Forward", "C": "Center"}
ROLES = {"starter": "Starter", "reserve": "Reserve", "injury replacement": "Injury replacement"}
NO_DECISIONS = "no award decisions closed."
FIX = "python scripts/write_back_results.py --write"


def _long(day):
    d = date.fromisoformat(day)
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def _read(path):
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def _clock(root):
    from .write_back import clock
    return clock(root)


def _anchor(name):
    return name.lower().replace(" ", "-")


def _join(dates_):
    return ", ".join(_long(d) for d in dates_)


def seasons_on_file(root=ROOT):
    """Seasons with a season award page, oldest first."""
    base = Path(root) / LEAGUE
    return sorted(p.parent.name for p in base.glob(f"*/{PAGE}") if re.fullmatch(r"\d{4}-\d{2}", p.parent.name))


def as_of(season, clock, root=ROOT):
    """The date a season's pages are stated at: the career clock, at most the end of the season's league year."""
    from .seasons import dates
    end = dates(season, root).get("season_close_window_end") or f"{int(season[:4]) + 1}-06-30"
    return min(clock, end)


def _month_folder(rel):
    return next(part for part in Path(rel).parts if re.fullmatch(r"\d\d_[A-Za-z]+", part))


# -- the records ---------------------------------------------------------------------------------------------------
def model(season, root=ROOT, clock=None):
    """Everything a season's award pages show, from the source records closed on or before the clock."""
    from .award_decisions import conference_names, filed_page, periods, read_decisions
    from .playoffs import read as read_playoffs
    from .seasons import dates, exists, month_weeks, read
    root = Path(root)
    clock = clock or _clock(root)
    league = root / LEAGUE / season
    weekly = [d for d in read_decisions(root, season)["decisions"] if d["announced_on"] <= clock]
    filed = Counter(_month_folder(d["filed_on"]) for d in weekly)
    expected, month_awards = Counter(), {}
    confs = conference_names(season, root)
    for award, start, end, announced in periods(season, root):
        rel = filed_page(award, end, season)
        expected[_month_folder(rel)] += len(confs)
        if award != "player_of_week":
            month_awards[_month_folder(rel)] = announced
    months = []
    for name, m, y, folder, weeks in month_weeks(season, root):
        n, due = filed.get(folder, 0), expected.get(folder, 0)
        status = "No award filed" if not n else ("Decided" if n >= due else "In progress")
        months.append(SimpleNamespace(label=f"{name} {y}", folder=folder, dates=f"{name} 1-{monthrange(y, m)[1]}, {y}",
                                      count=n, status=status))
    calendar = {a["id"]: a for a in read(season, "season_awards", root)["awards"]} if exists(season, "season_awards", root) else {}
    record = _read(league / "season_awards.json") or {"decisions": []}
    decided = {d["award"]: d for d in record["decisions"] if d["announced_on"] <= clock}
    star = _read(league / "all_star.json") or {"steps": [], "all_stars": []}
    steps = {s["step"]: s for s in star.get("steps", []) if s["announced_on"] <= clock}
    stars = [a for a in star.get("all_stars", []) if a["selected_on"] <= clock]
    if not stars and "starters" in steps:              # starters announced, the reserves not yet: the list is the starters
        stars = [{"player": p["player"], "team": p["team"], "conference": conf, "role": "starter",
                  "selected_on": steps["starters"]["announced_on"]}
                 for conf, sides in steps["starters"]["conferences"].items() for p in sides["starters"]]
    from .all_star import ctx
    star_calendar = {k: v["value"] for k, v in (ctx(root, season).data or {}).get("dates", {}).items()}
    playoffs = read_playoffs(root, season) or {}
    finals = next((s for s in playoffs.get("series", []) if s["round"] == "finals"), None)
    champion = finals if finals and finals.get("winner") and (finals.get("clinched_on") or clock) <= clock else None
    return SimpleNamespace(season=season, clock=clock, as_of=as_of(season, clock, root), weekly=weekly, months=months,
                           month_awards=month_awards, calendar=calendar, decided=decided, all_stars=stars, steps=steps,
                           star_calendar=star_calendar, champion=champion, playoffs_start=dates(season, root).get("playoffs_start"),
                           calendar_path=_calendar_path(season), links={name: (league / name).is_file()
                                                                         for name in ("Season_Awards.md", "All_Star.md", "Playoffs.md")})


def _calendar_path(season):
    from .seasons import path
    return path(season, "season_awards").as_posix()


def _close(m, award):
    """The announcement (close) date of a season award as the page states it."""
    a = m.calendar.get(award)
    if a is None:
        return _long(m.decided[award]["announced_on"]) if award in m.decided else "date not recorded"
    return "the night the Finals are clinched" if a["announced"] == "finals_clinch" else _long(a["announced"])


def _vote_line(m, award, open_word="Vote closes"):
    """The award's line above its table: announced (with its electorate, ballot and tally link) or still open."""
    a, d = m.calendar.get(award), m.decided.get(award)
    src = d or a
    voters = f" · {src['electorate']} {src['voters']} · ballot {'-'.join(map(str, src['ballot']))}" if src else ""
    if d:
        tally = f" · [tally](Season_Awards.md#{_anchor(d['name'])})" if m.links["Season_Awards.md"] else ""
        draw = (f" Equal votes at the top; the winner was drawn by the engine (`{Path(d['tie_draw']).name}`)."
                if d.get("tie_draw") else "")
        return f"Announced {_long(d['announced_on'])}{voters}{tally}.{draw}"
    return f"{open_word} {_close(m, award)}{voters}."


# -- the season page -------------------------------------------------------------------------------------------------
def _table(headers, rows, right=()):
    align = ["---:" if i in right else "---" for i in range(len(headers))]
    return ["| " + " | ".join(headers) + " |", "| " + " | ".join(align) + " |"] + \
           ["| " + " | ".join(str(x) for x in r) + " |" for r in rows]


def _rank_rows(m, award):
    """The top three of a closed vote, winners first with **WINNER** (or **CO-WINNER**); empty slots while open."""
    d = m.decided.get(award)
    if d is None:
        return [[i, "Pending", "N/A", "N/A", "N/A", f"Awaiting vote (closes {_close(m, award)})"] for i in (1, 2, 3)]
    key = "coach" if award == "coy" else "player"
    winners = d.get("winners") or []
    label = "**WINNER**" if len(winners) == 1 else "**CO-WINNER**"
    tally = sorted(d.get("tally", []), key=lambda v: v[key] not in winners)[:3]       # a drawn winner first, order kept
    place = {1: "First", 2: "Runner-up", 3: "Third"}
    rows = [[i, v[key], v["team"], v["first_place"], v["points"], label if v[key] in winners else place[i]]
            for i, v in enumerate(tally, 1)]
    return rows + [[i, "No further vote-getter", "N/A", "N/A", "N/A", "N/A"] for i in range(len(rows) + 1, 4)]


def _slots(m, award):
    """[(position group or None, column label)]: the era's positional slots, or five a team regardless of position."""
    a = m.calendar.get(award) or {}
    if award == "all_rookie":
        return [(None, f"Player {i}") for i in range(1, a.get("picks_per_team", 5) + 1)]
    shape = a.get("by_position") or {"G": 2, "F": 2, "C": 1}
    return [(g, SLOT_NAMES.get(g, g)) for g in ("G", "F", "C") for _ in range(shape.get(g, 0))]


def _team_cells(players, slots):
    """One cell per slot: by position where the award has positional slots; a tie at the cut shares the last slot."""
    names = [f"{p['player']} ({p['team']})" for p in players]
    cells, groups = [None] * len(slots), {g for g, _ in slots if g}
    for g in sorted(groups, key=[s for s, _ in slots].index):
        idx = [i for i, (s, _) in enumerate(slots) if s == g]
        group = [n for n, p in zip(names, players) if p.get("position") == g]
        if len(group) > len(idx):
            group = group[:len(idx) - 1] + [" / ".join(group[len(idx) - 1:])]
        for i, n in zip(idx, group):
            cells[i] = n
    left = [n for n, p in zip(names, players) if p.get("position") not in groups]      # no slot of his own: the next free one
    for i in range(len(cells)):
        if cells[i] is None and left:
            cells[i] = left.pop(0)
    if left:
        cells[-1] = " / ".join([cells[-1]] + left)
    return [c or "Not selected" for c in cells]


def _team_rows(m, award, teams):
    d, slots = m.decided.get(award), _slots(m, award)
    if d is None:
        return slots, [[TEAM_LABELS[i]] + ["Not selected"] * len(slots) for i in range(teams)]
    return slots, [[t["team"].split()[0]] + _team_cells(t["players"], slots) for t in d["teams"]]


def _status(m):
    n, k = len(m.weekly), len(m.decided)
    total = len(set(m.calendar) | set(m.decided))
    if not n and not k:
        return f"As of {_long(m.as_of)}: {NO_DECISIONS}"
    season = f"; {k} of {total} season awards decided" if total else ""
    return f"As of {_long(m.as_of)}: {n} weekly and monthly award decision(s) closed{season}."


def _all_star_lines(m):
    link = " [All-Star selections](All_Star.md#all-stars)" if m.links["All_Star.md"] else ""
    c = m.star_calendar
    if not m.all_stars:
        if c.get("starters_announced"):
            return [f"No All-Star selection announced yet: starters {_long(c['starters_announced'])} (fan ballot), reserves "
                    f"{_long(c['reserves_announced'])} (head coaches).{link}", ""]
        return [f"No All-Star selection recorded; the season's All-Star calendar is not on file.{link}", ""]
    steps = [f"{word} announced {_long(m.steps[s]['announced_on'])} ({who})" for s, word, who in
             (("starters", "starters", "fan ballot"), ("reserves", "reserves", "head coaches")) if s in m.steps]
    if "replacements" in m.steps:                      # the Commissioner's step, worded by what it records
        s = m.steps["replacements"]
        n = sum(len(v) for v in (s.get("conferences") or {}).values())
        steps.append(f"{n} injury replacement{'s' if n != 1 else ''} named {_long(s['announced_on'])} (the Commissioner)" if n
                     else f"no injury replacement named by the Commissioner ({_long(s['announced_on'])})")
    rows = [[a["conference"], ROLES.get(a["role"], a["role"].capitalize()) + (f" for {a['replacing']}" if a.get("replacing") else ""),
             a["player"], a["team"], _long(a["selected_on"])] for a in m.all_stars]
    return [f"{len(m.all_stars)} All-Stars: {', '.join(steps)}.{link}", ""] + _table(
        ["Conference", "Role", "Player", "Team", "Selected"], rows) + [""]


def _champion_lines(m):
    link = " [Playoffs](Playoffs.md)" if m.links["Playoffs.md"] else ""
    f = m.champion
    if f is None:
        when = f" The playoffs open {_long(m.playoffs_start)}." if m.playoffs_start and m.playoffs_start > m.clock else ""
        return [f"Not decided yet.{when}{link}", ""]
    loser = next((c for c in f["clubs"] if c != f["winner"]), "N/A")
    wins = f.get("wins", {})
    score = f", {wins.get(f['winner'])}-{wins.get(loser)}" if wins else ""
    clinched = f", Finals clinched {_long(f['clinched_on'])}" if f.get("clinched_on") else ""
    return [f"**{f['winner']}**{clinched} over the {loser}{score}.{link}", ""]


def season_page(season, root=ROOT, clock=None, m=None):
    """The season award hub's text from the records closed on or before the clock."""
    m = m or model(season, root, clock)
    s = season
    nav = [f"[Stats hub](../../README.md)", f"[Wade](../../{s}/README.md)", f"[Miami](../../Team/{s}/Team_Stats.md)",
           "[NBA players](League_Stats.md)"]
    nav += [f"[{label}]({name})" for name, label in (("Season_Awards.md", "Season awards"), ("All_Star.md", "All-Star"),
                                                     ("Playoffs.md", "Playoffs")) if m.links[name]]
    tally = "[Season awards](Season_Awards.md) (`season_awards.json`)" if m.links["Season_Awards.md"] else "`season_awards.json`, once the first vote closes"
    lines = [f"# NBA awards | {s}", "", " · ".join(nav), "", f"{s} · Calendar coverage: {s}", "", _status(m), "",
             "## Individual awards", "",
             "Each award shows its top three once its vote has closed on the real announcement date, the first-place result "
             "labelled **WINNER**; an award still open keeps empty rank slots with its close date. Ballots and complete "
             f"tallies: {tally}.", ""]
    for award, name in INDIVIDUAL:
        who = "Coach" if award == "coy" else "Player"
        lines += [f"### {name}", "", _vote_line(m, award), ""] + _table(
            ["Rank slot", who, "Team", "1st votes", "Points", "Status"], _rank_rows(m, award), right=(0, 3, 4)) + [""]
    for award, heading, _, teams in TEAM_AWARDS:
        teams = (m.calendar.get(award) or {}).get("teams", teams)
        slots, rows = _team_rows(m, award, teams)
        lines += [f"## {heading}", "", _vote_line(m, award, "Selection closes"), ""] + _table(
            ["Team"] + [label for _, label in slots], rows) + [""]
    lines += ["<details>", "<summary>Voting procedure and eligibility</summary>", ""]
    if m.calendar:
        lines += [f"Electorates, ballots and announcement dates are researched for the season (`{m.calendar_path}`); every "
                  "ballot is filed by the rule in `runtime/season_awards.py`.", ""] + _table(
            ["Award", "Announced", "Voters", "Ballot"],
            [[a["name"], _close(m, a["id"]), f"{a['electorate']} {a['voters']}", "-".join(map(str, a["ballot"]))]
             for a in m.calendar.values()]) + [""]
    else:
        lines += ["The season's award calendar (electorates, ballots and announcement dates) is not on file yet.", ""]
    lines += ["Every voter in the real electorate files a ballot from closed simulated results; voters differ only in how much "
              "they weigh the award's two published criteria, so no vote is chance and nothing is re-rolled. All-NBA and "
              "All-Defensive teams keep the era's positional slots (two guards, two forwards, one center); All-Rookie teams "
              "take five players regardless of position, and a coach never votes for his own players. Every ballot or the "
              "complete tally stays in the owning award record; this page shows three finishers.", "", "</details>", "",
              "## Other honors", "",
              "These are separate decisions, not consequences of the regular-season award vote.", "",
              "### All-Star selections", ""] + _all_star_lines(m)
    lines += ["### NBA champion", ""] + _champion_lines(m)
    lines += ["### Finals MVP", "", _vote_line(m, "finals_mvp"), ""] + _table(
        ["Rank slot", "Player", "Team", "1st votes", "Points", "Status"], _rank_rows(m, "finals_mvp"), right=(0, 3, 4)) + [""]
    lines += ["## By month", "",
              "Weekly and monthly award decisions, each counted on the page it is filed on (the calendar bucket holding its "
              "period's end: a week page for Player of the Week, the month page for Player and Rookie of the Month), the "
              "month's week pages included.", ""] + _table(
        ["Period", "Calendar dates", "Closed decisions", "Status"],
        [[f"[{x.label}]({x.folder}/{PAGE})", x.dates, x.count, x.status] for x in m.months], right=(2,)) + [""]
    lines += ["[Awards procedure and research](../README.md) · [Player evidence for this calendar period](League_Stats.md)"]
    return "\n".join(lines) + "\n"


# -- the month pages' status line ------------------------------------------------------------------------------------
def month_status(m, folder):
    """A month page's 'As of' line: its own month decisions (the words `award_decisions.render_pages` uses) and the
    Player of the Week decisions filed on its week pages."""
    prefix = f"{(LEAGUE / m.season / folder).as_posix()}/"
    own = sorted(d["announced_on"] for d in m.weekly if d["filed_on"] == prefix + PAGE)
    weeks = sorted(d["announced_on"] for d in m.weekly if d["filed_on"].startswith(prefix + "Week_"))
    head = f"As of {_long(m.as_of)}: "
    if own:
        line = head + f"{len(own)} award decision(s) closed, announced {_join(sorted(set(own)))}"
        return line + (f"; {len(weeks)} Player of the Week decision(s) closed on this month's week pages." if weeks else ".")
    if weeks:
        due = m.month_awards.get(folder)
        when = f" (Player and Rookie of the Month announced {_long(due)})" if due else ""
        return (head + f"no month award decision closed{when}; {len(weeks)} Player of the Week decision(s) closed on this "
                f"month's week pages, announced {_join(sorted(set(weeks)))}.")
    return head + NO_DECISIONS


def _with_status(text, line):
    return re.sub(r"^As of [^\n]*$", lambda _: line, text, count=1, flags=re.M)


def outputs(root=ROOT, clock=None):
    """{path: text} for every season award page on file and every month page of those seasons."""
    root = Path(root)
    on_file = seasons_on_file(root)
    if not on_file:                                    # a scratch copy without award pages
        return {}
    clock = clock or _clock(root)
    out = {}
    for season in on_file:
        m = model(season, root, clock)
        league = root / LEAGUE / season
        out[league / PAGE] = season_page(season, root, clock, m)
        for x in m.months:
            page = league / x.folder / PAGE
            if page.is_file():
                out[page] = _with_status(page.read_text(encoding="utf-8"), month_status(m, x.folder))
    return out


def write_pages(root=ROOT, clock=None, write=True):
    """Rebuild the season award pages and the month status lines; returns the paths that changed."""
    changed = []
    for path, text in outputs(root, clock).items():
        if path.read_text(encoding="utf-8") != text:
            if write:
                path.write_text(text, encoding="utf-8")
            changed.append(path)
    return changed


# -- validation ------------------------------------------------------------------------------------------------------
def facts(m):
    """What a season page must show, from the records: title, coverage, closed counts, counts by month, the winners
    of every closed vote (none while open), the team selections, the All-Stars and the champion."""
    out = {"title": f"# NBA awards | {m.season}", "coverage": f"{m.season} · Calendar coverage: {m.season}",
           "closed decisions": (len(m.weekly), len(m.decided)),
           "decisions by month": {x.label: x.count for x in m.months}}
    for award, name in INDIVIDUAL + (("finals_mvp", "Finals MVP"),):
        d = m.decided.get(award)
        out[f"{name} winner"] = sorted(d.get("winners") or []) if d else []
    for award, heading, _, teams in TEAM_AWARDS:
        d = m.decided.get(award)
        out[heading] = {t["team"].split()[0]: sorted(p["player"] for p in t["players"]) for t in d["teams"]} if d else {}
    out["All-Star selections"] = sorted((a["conference"], a["player"]) for a in m.all_stars)
    out["champion"] = m.champion["winner"] if m.champion else None
    return out


def _closed_counts(body):
    if body.startswith("no award decisions closed"):
        return (0, 0)
    n = re.search(r"(\d+) weekly and monthly award decision\(s\) closed", body)
    k = re.search(r"(\d+) of \d+ season awards decided", body)
    return (int(n.group(1)) if n else None, int(k.group(1)) if k else 0)


def _player(cell):
    return re.sub(r" \([^()]*\)$", "", cell.strip())


def page_facts(text):
    """The same facts read back from a season page's text."""
    lines = text.splitlines()
    status = re.search(r"^As of [^:\n]+: (.*)$", text, re.M)
    out = {"title": lines[0] if lines else "", "coverage": next((l for l in lines if "Calendar coverage:" in l), None),
           "closed decisions": _closed_counts(status.group(1)) if status else None}
    rows, prose, h2, h3 = defaultdict(list), defaultdict(list), None, None
    for line in lines:
        if line.startswith("## "):
            h2, h3 = line[3:].strip(), None
        elif line.startswith("<details>"):                 # the procedure block belongs to no award section
            h2, h3 = "<details>", None
        elif line.startswith("### "):
            h3 = line[4:].strip()
        elif line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if not all(re.fullmatch(r":?-+:?", c) for c in cells) and cells[0] not in ("Rank slot", "Team", "Period", "Conference", "Award"):
                rows[(h2, h3)].append(cells)
        else:
            prose[(h2, h3)].append(line)
    out["decisions by month"] = {re.sub(r"^\[([^\]]+)\].*$", r"\1", r[0]): int(r[2]) if r[2].isdigit() else r[2]
                                 for r in rows[("By month", None)]}
    for award, name in INDIVIDUAL + (("finals_mvp", "Finals MVP"),):
        section = rows[("Other honors", name)] if award == "finals_mvp" else rows[("Individual awards", name)]
        out[f"{name} winner"] = sorted(r[1] for r in section if len(r) > 5 and "WINNER" in r[5])
    for _, heading, _, _ in TEAM_AWARDS:
        out[heading] = {r[0]: sorted(_player(n) for c in r[1:] if c != "Not selected" for n in c.split(" / "))
                        for r in rows[(heading, None)] if any(c != "Not selected" for c in r[1:])}
    out["All-Star selections"] = sorted((r[0], r[2]) for r in rows[("Other honors", "All-Star selections")] if len(r) > 2)
    champion = re.search(r"\*\*(.+?)\*\*", "\n".join(prose[("Other honors", "NBA champion")]))
    out["champion"] = champion.group(1) if champion else None
    return out


def _month_counts(line):
    """(month decisions, week decisions or None) stated by a month page's 'As of' line."""
    body = line.split(": ", 1)[1] if ": " in line else ""
    if body.startswith("no award decisions closed"):
        return 0, 0
    own = re.match(r"(\d+) award decision\(s\) closed", body)
    weeks = re.search(r"(\d+) Player of the Week decision\(s\) closed", body)
    return (int(own.group(1)) if own else 0), (int(weeks.group(1)) if weeks else None)


def _difference(have, want):
    """What a page shows against what its records give, briefly: the differing entries of a table or list."""
    if isinstance(want, dict) and isinstance(have, dict):
        keys = [k for k in dict.fromkeys(list(want) + list(have)) if have.get(k) != want.get(k)]
        return "; ".join(f"{k}: page {have.get(k, 'missing')!r}, records {want.get(k, 'none')!r}" for k in keys[:6])
    if isinstance(want, list) and isinstance(have, list):
        missing, extra = [x for x in want if x not in have], [x for x in have if x not in want]
        parts = ([f"misses {missing[:6]!r}"] if missing else []) + ([f"shows {extra[:6]!r}, not in the records"] if extra else [])
        if parts:
            return "; ".join(parts)
    return f"reads {have!r}, the records give {want!r}"


def page_errors(root=ROOT):
    """Each season award page and month status line against its records (`python scripts/write_back_results.py --write`
    rebuilds them)."""
    root = Path(root)
    on_file = seasons_on_file(root)
    if not on_file:
        return []
    try:
        clock = _clock(root)
    except (OSError, ValueError, KeyError) as exc:
        return [f"award pages: cannot read the career clock: {exc}"]
    errors = []
    for season in on_file:
        m = model(season, root, clock)
        league = root / LEAGUE / season
        rel = (LEAGUE / season / PAGE).as_posix()
        want, have = facts(m), page_facts((league / PAGE).read_text(encoding="utf-8"))
        for key, value in want.items():
            if have.get(key) != value:
                errors.append(f"{rel}: {key} {_difference(have.get(key), value)} ({FIX})")
        for x in m.months:
            page = league / x.folder / PAGE
            if not page.is_file():
                continue
            line = next((l for l in page.read_text(encoding="utf-8").splitlines() if l.startswith("As of ")), "")
            prefix = f"{(LEAGUE / season / x.folder).as_posix()}/"
            own = sum(1 for d in m.weekly if d["filed_on"] == prefix + PAGE)
            weeks = sum(1 for d in m.weekly if d["filed_on"].startswith(prefix + "Week_"))
            stated_own, stated_weeks = _month_counts(line)
            if stated_own != own or (stated_weeks is not None and stated_weeks != weeks) or (not own and weeks and stated_weeks is None):
                errors.append(f"{(LEAGUE / season / x.folder / PAGE).as_posix()}: status {line!r} disagrees with "
                              f"award_decisions.json ({own} month and {weeks} week decision(s) closed) ({FIX})")
    return errors
