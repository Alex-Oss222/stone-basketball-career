"""The 2004 playoffs: seeding, tiebreakers, the bracket and each series' calendar (roadmap item 14).

Everything is decided from closed simulated regular-season results only, by the researched 2003-04 rules
(`library/2003/league/nba_2003_04_playoff_rules.json`); real 2004 seeds, matchups and results are never read.

- Seeding: in each conference the two division winners take seeds 1 and 2 by record; seeds 3 to 8 are the next six
  records. Ties go through the tiebreak procedure in the rules file (two-team and multi-team lists, restarting once
  a team is separated); a tie the procedure cannot break is an engine decision draw (`Playoff_Draws/`), never chosen.
- Bracket: 1-8, 4-5, 3-6, 2-7 in each conference, fixed, no reseeding; best of seven.
- Home court: the better regular-season record (equal records by the tiebreak procedure); 2-2-1-1-1 in the
  conference rounds, 2-3-2 in the Finals.
- Calendar: each round's opening days and the gap template from the rules file. A game is listed when its series
  needs it; games 5 to 7 only while the series is undecided.

The record is `Stats_and_Awards/League/<season>/playoffs.json`; its page is `Playoffs.md` beside the standings.
"""
from datetime import date, timedelta
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEASON = "2003-04"
RULES = Path("library/2003/league/nba_2003_04_playoff_rules.json")
LEAGUE = Path(f"career/Dwyane_Wade/Stats_and_Awards/League/{SEASON}")
RECORD = LEAGUE / "playoffs.json"
PAGE = LEAGUE / "Playoffs.md"
DRAWS = LEAGUE / "Playoff_Draws"
ROUNDS = (("first_round", "First round", "First_Round"), ("conference_semifinals", "Conference semifinals", "Conference_Semifinals"),
          ("conference_finals", "Conference finals", "Conference_Finals"), ("finals", "NBA Finals", "Finals"))


def rules(root=ROOT):
    return json.loads((Path(root) / RULES).read_text(encoding="utf-8"))


def divisions(root=ROOT):
    """{club: (conference, division)}."""
    out = {}
    for conf, divs in rules(root)["divisions"].items():
        if conf in ("East", "West"):
            for div, clubs in divs.items():
                for c in clubs:
                    out[c] = (conf, div)
    return out


# -- the regular-season table ---------------------------------------------------------------------
class Table:
    """Every club's closed regular-season results: record, head-to-head, division and conference records, points."""

    def __init__(self, root=ROOT, season=SEASON, through=None):
        from .write_back import closed_results
        self.root = Path(root)
        self.where = divisions(root)
        self.games = []
        for row in closed_results(root, season, through):
            r = row["result"]
            home_won = r["final_score"]["home"] > r["final_score"]["away"]
            self.games.append((r["home"], r["away"], r["home"] if home_won else r["away"],
                               r["final_score"]["home"] - r["final_score"]["away"]))
        self.clubs = sorted(self.where)

    def record(self, club, against=None):
        """(wins, losses) for `club`, over all games or only those against clubs in `against`."""
        w = l = 0
        for home, away, winner, _ in self.games:
            if club not in (home, away):
                continue
            other = away if club == home else home
            if against is not None and other not in against:
                continue
            w, l = (w + 1, l) if winner == club else (w, l + 1)
        return w, l

    def pct(self, club, against=None):
        w, l = self.record(club, against)
        return w / (w + l) if w + l else 0.0

    def differential(self, club):
        return sum((d if club == home else -d) for home, away, _, d in self.games if club in (home, away))

    def conference(self, club):
        return [c for c in self.clubs if self.where[c][0] == self.where[club][0]]

    def division(self, club):
        return [c for c in self.clubs if self.where[c] == self.where[club]]


class Ranker:
    """Orders clubs by record with the tiebreak procedure; an unbreakable tie becomes an engine draw."""

    def __init__(self, table, root=ROOT, winners=()):
        self.t, self.root, self.winners = table, Path(root), set(winners)
        self.pending = []

    def eligible(self, conference):
        clubs = [c for c in self.t.clubs if self.t.where[c][0] == conference]
        ordered = sorted(clubs, key=lambda c: -self.t.pct(c))
        cut = self.t.pct(ordered[7])
        return {c for c in clubs if self.t.pct(c) >= cut}            # playoff-eligible if the season ended today

    def order(self, clubs):
        groups = {}
        for c in clubs:
            groups.setdefault(round(self.t.pct(c), 9), []).append(c)
        out = []
        for key in sorted(groups, reverse=True):
            out += self.break_tie(groups[key])
        return out

    def break_tie(self, tied):
        if len(tied) == 1:
            return list(tied)
        conf = self.t.where[tied[0]][0]
        own = self.eligible(conf)
        other = self.eligible("West" if conf == "East" else "East")
        same_div = len({self.t.where[c] for c in tied}) == 1
        if len(tied) == 2:
            a, b = tied
            steps = [lambda c: self.t.pct(c, {b if c == a else a}),
                     lambda c: 1 if c in self.winners else 0,
                     (lambda c: self.t.pct(c, set(self.t.division(c)) - {c})) if same_div else None,
                     lambda c: self.t.pct(c, set(self.t.conference(c)) - {c}),
                     lambda c: self.t.pct(c, own - {c}),
                     lambda c: self.t.pct(c, other),
                     lambda c: self.t.differential(c)]
        else:
            group = set(tied)
            steps = [lambda c: 1 if c in self.winners else 0,
                     lambda c: self.t.pct(c, group - {c}),
                     (lambda c: self.t.pct(c, set(self.t.division(c)) - {c})) if same_div else None,
                     lambda c: self.t.pct(c, set(self.t.conference(c)) - {c}),
                     lambda c: self.t.pct(c, own - {c}),
                     lambda c: self.t.differential(c)]
        for step in steps:
            if step is None:
                continue
            values = {c: round(step(c), 9) for c in tied}
            best = max(values.values())
            top = [c for c in tied if values[c] == best]
            if len(top) < len(tied):
                rest = [c for c in tied if c not in top]
                return self.break_tie(top) + self.order(rest)          # restart for those still tied
        return self.drawing(tied)

    def drawing(self, tied):
        """A drawing: an engine decision packet; until it is drawn the order is pending."""
        from .decisions import load_decision
        key = "-".join(sorted(c.lower().replace(" ", "-") for c in tied))
        event = f"{SEASON}-playoff-tiebreak-{key}"
        path = self.root / DRAWS / f"{event}.decision.json"
        result = path.with_name(f"{event}.decision.result.json")
        if result.is_file():
            first = json.loads(result.read_text(encoding="utf-8"))["outcome"]
            return [first] + self.drawing([c for c in tied if c != first]) if len(tied) > 2 else [first, next(c for c in tied if c != first)]
        if not path.is_file():
            path.parent.mkdir(parents=True, exist_ok=True)
            share = round(1 / len(tied), 6)
            options = {c: share for c in sorted(tied)}
            options[sorted(tied)[-1]] = round(1 - share * (len(tied) - 1), 6)
            path.write_text(json.dumps({"event_id": event, "date": rules(self.root)["calendar"]["regular_season_last_day"],
                                        "question": f"Tiebreak drawing: who ranks first among {', '.join(sorted(tied))}?",
                                        "decider": "NBA drawing (engine draw)", "options": options,
                                        "basis": "every tiebreak step in the 2003-04 procedure left them level (runtime/playoffs.py)"},
                                       indent=1) + "\n", encoding="utf-8")
            load_decision(path)
        self.pending.append(event)
        return sorted(tied)


def seeds(root=ROOT, season=SEASON):
    """{conference: [(seed, club, wins, losses, division winner?)]} and the pending tiebreak draws."""
    table = Table(root, season)
    winners = []
    plain = Ranker(table, root)
    for conf, divs in rules(root)["divisions"].items():
        if conf not in ("East", "West"):
            continue
        for div, clubs in divs.items():
            winners.append(plain.order(clubs)[0])
    ranker = Ranker(table, root, winners)
    out = {}
    for conf in ("East", "West"):
        clubs = table.conference(next(c for c in table.clubs if table.where[c][0] == conf))
        div_winners = ranker.order([c for c in clubs if c in winners])
        rest = ranker.order([c for c in clubs if c not in winners])[:6]
        out[conf] = [(i + 1, c, *table.record(c), c in winners) for i, c in enumerate(div_winners + rest)]
    return out, plain.pending + ranker.pending, table, ranker


def home_court(a, b, table, ranker):
    """The club with home court in a series: better record, equal records by the tiebreak procedure."""
    return ranker.order([a, b])[0]


def first_round(root=ROOT, season=SEASON):
    """The bracket's first round with each series' home-court team and its calendar of possible games."""
    seeded, pending, table, ranker = seeds(root, season)
    if pending:
        return None, pending
    cfg = rules(root)
    openers = {}
    for day, pairs in cfg["calendar"]["first_round"]["openers"].items():
        for conf, pair in pairs:
            openers[(conf, tuple(pair))] = day
    gaps = cfg["calendar"]["first_round"]["gaps_days"]
    home_games = cfg["home_court"]["conference_rounds"]["home_team_games"]
    series = []
    for conf in ("East", "West"):
        by_seed = {s: c for s, c, *_ in seeded[conf]}
        for high, low in cfg["bracket"]["first_round"]:
            a, b = by_seed[high], by_seed[low]
            home = home_court(a, b, table, ranker)
            road = b if home == a else a
            day = date.fromisoformat(openers[(conf, (high, low))])
            games = []
            for n in range(1, 8):
                host = home if n in home_games else road
                games.append({"game": n, "date": day.isoformat(), "home": host, "away": road if host == home else home,
                              "conditional": n >= 5})
                if n < 7:
                    day += timedelta(days=gaps[n - 1])
            series.append({"id": f"{conf.lower()}-{high}-{low}", "round": "first_round", "conference": conf,
                           "seeds": [high, low], "clubs": [a, b], "home_court": home, "wins": {a: 0, b: 0},
                           "winner": None, "games": games})
    return {"seeded": seeded, "series": series}, []


def build(root=ROOT, season=SEASON, write=True):
    """Seed the playoffs and write the record and its page once the regular season is complete."""
    root = Path(root)
    bracket, pending = first_round(root, season)
    if bracket is None:
        return None, pending
    cfg = rules(root)
    record = {"schema_version": 1, "kind": "playoffs", "season": season,
              "rules": RULES.as_posix(), "seeded_on": cfg["calendar"]["regular_season_last_day"],
              "seeds": {conf: [{"seed": s, "club": c, "wins": w, "losses": l, "division_winner": d}
                               for s, c, w, l, d in rows] for conf, rows in bracket["seeded"].items()},
              "series": bracket["series"], "champion": None}
    if write:
        (root / RECORD).write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        (root / PAGE).write_text(page(record, root), encoding="utf-8")
        readme = root / LEAGUE.parent / "README.md"                    # the league hub links the bracket once it exists
        text = readme.read_text(encoding="utf-8") if readme.is_file() else ""
        hub = f"[{season} standings]({season}/Standings.md)"
        if hub in text and f"({season}/Playoffs.md)" not in text:
            readme.write_text(text.replace(hub, hub + f" · [2004 playoffs]({season}/Playoffs.md)", 1), encoding="utf-8")
    return record, []


def _d(day):
    d = date.fromisoformat(day)
    return f"{d:%a} {d:%b} {d.day}"


def page(record, root=ROOT):
    lines = [f"# {record['season']} NBA playoffs", "",
             f"Seeded {record['seeded_on']} from closed simulated regular-season results only "
             f"([standings](Standings.md); rules and sources: `{record['rules']}`, `runtime/playoffs.py`). "
             "Real 2004 seeds, matchups and results are never used.", "",
             "Division winners take seeds 1 and 2; seeds 3 to 8 are the next six records. Ties: the 2003-04 tiebreak "
             "procedure, an engine drawing if it cannot separate them. Best of seven; home court to the better record; "
             "2-2-1-1-1 in the conference rounds, 2-3-2 in the Finals. Games 5 to 7 are played only if needed.", ""]
    for conf in ("East", "West"):
        lines += [f"## {conf}ern Conference seeds", "", "| Seed | Club | W | L | Note |", "| ---: | --- | ---: | ---: | --- |"]
        for row in record["seeds"][conf]:
            club = f"**{row['club']}**" if row["club"] == "Miami Heat" else row["club"]
            lines.append(f"| {row['seed']} | {club} | {row['wins']} | {row['losses']} | {'division winner' if row['division_winner'] else ''} |")
        lines.append("")
    lines += ["## Bracket", "", "```"]
    for conf in ("East", "West"):
        lines.append(f"{conf.upper()}")
        firsts = {tuple(s["seeds"]): s for s in record["series"] if s["round"] == "first_round" and s["conference"] == conf}
        for half in (((1, 8), (4, 5)), ((3, 6), (2, 7))):
            for pair in half:
                s = firsts[pair]
                a, b = s["clubs"]
                lines.append(f"  ({pair[0]}) {a:<24} {s['wins'][a]}")
                lines.append(f"  ({pair[1]}) {b:<24} {s['wins'][b]}   {'-> ' + s['winner'] if s['winner'] else ''}")
            lines.append("        conference semifinal: winners meet")
        lines.append("    conference final, then the NBA Finals")
        lines.append("")
    lines += ["```", "", "## First-round schedule", ""]
    for s in (x for x in record["series"] if x["round"] == "first_round"):
        a, b = s["clubs"]
        lines += [f"### {s['conference']} ({s['seeds'][0]}) {a} vs ({s['seeds'][1]}) {b}", "",
                  f"Home court: {s['home_court']}. Series {s['wins'][a]}-{s['wins'][b]}.", "",
                  "| Game | Date | Home | Away | |", "| ---: | --- | --- | --- | --- |"]
        for g in s["games"]:
            lines.append(f"| {g['game']} | {_d(g['date'])} | {g['home']} | {g['away']} | {'if needed' if g['conditional'] else ''} |")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
