"""Wade's career statistical milestones: round career totals and career firsts, each with the closed game that
reached it and his age on that date (the user's request, October 2026).

Evidence is the closed game records only (`career_stats.collect_games`): a played game with a box line. The NBA
counts career milestones in the regular season; playoff totals are kept as their own milestones and never mixed
in. Preseason games never count. A milestone is reached in the game whose running total first meets the threshold;
the age is years and days from the date of birth in his professional identity (the alternate-history profile).
"""
from datetime import date

STATS = (  # (key in the box line, label, thresholds)
    ("pts", "points", (1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000, 12500, 15000, 17500, 20000,
                       22500, 25000, 27500, 30000)),
    ("reb", "rebounds", (250, 500, 1000, 1500, 2000, 2500, 3000, 4000, 5000, 6000, 7000, 8000, 10000)),
    ("ast", "assists", (250, 500, 1000, 1500, 2000, 2500, 3000, 4000, 5000, 6000, 7000, 8000, 10000)),
    ("stl", "steals", (100, 250, 500, 750, 1000, 1250, 1500, 2000)),
    ("blk", "blocks", (100, 250, 500, 750, 1000, 1500)),
    ("tpm", "three-pointers made", (100, 250, 500, 750, 1000, 1500, 2000)),
    ("ftm", "free throws made", (500, 1000, 2000, 3000, 4000, 5000, 6000, 7000)),
    ("games", "games played", (100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200)),
)
PLAYOFF_STATS = (
    ("pts", "playoff points", (100, 250, 500, 1000, 1500, 2000, 2500, 3000, 3500, 4000, 5000)),
    ("reb", "playoff rebounds", (100, 250, 500, 750, 1000)),
    ("ast", "playoff assists", (100, 250, 500, 750, 1000)),
    ("games", "playoff games", (10, 25, 50, 75, 100, 125, 150, 175, 200)),
)
FIRSTS = (  # (label, test on the box line)
    ("NBA regular-season debut", lambda l: True),
    ("First 20-point game", lambda l: l["pts"] >= 20),
    ("First 30-point game", lambda l: l["pts"] >= 30),
    ("First 40-point game", lambda l: l["pts"] >= 40),
    ("First 50-point game", lambda l: l["pts"] >= 50),
    ("First double-double", lambda l: _doubles(l) >= 2),
    ("First triple-double", lambda l: _doubles(l) >= 3),
    ("First 10-assist game", lambda l: l["ast"] >= 10),
    ("First 15-rebound game", lambda l: l["reb"] >= 15),
    ("First 5-steal game", lambda l: l["stl"] >= 5),
    ("First 5-block game", lambda l: l["blk"] >= 5),
)


def _doubles(line):
    return sum(1 for k in ("pts", "reb", "ast", "stl", "blk") if (line.get(k) or 0) >= 10)


def age_on(birth, day):
    """(years, days) from the date of birth to `day`."""
    b, d = date.fromisoformat(birth), date.fromisoformat(day)
    years = d.year - b.year - ((d.month, d.day) < (b.month, b.day))
    try:
        last = b.replace(year=b.year + years)
    except ValueError:                       # a February 29 birthday
        last = date(b.year + years, 3, 1)
    return years, (d - last).days


def age_text(birth, day):
    if not birth:
        return "Not recorded"
    y, d = age_on(birth, day)
    return f"{y} years, {d} day{'s' if d != 1 else ''}"


def _played(records, competition):
    games = [r for r in records if r.get("competition") == competition and r.get("status") == "played"
             and isinstance(r.get("line"), dict) and r["line"].get("appeared")]
    return sorted(games, key=lambda r: (r["date"], r.get("event_id") or ""))


def _crossings(games, stats, birth):
    reached, upcoming = [], []
    totals = {key: 0 for key, _, _ in stats}
    pending = {key: list(thresholds) for key, _, thresholds in stats}
    labels = {key: label for key, label, _ in stats}
    for n, g in enumerate(games, start=1):
        for key in totals:
            totals[key] = n if key == "games" else totals[key] + int(g["line"].get(key) or 0)
            while pending[key] and totals[key] >= pending[key][0]:
                mark = pending[key].pop(0)
                reached.append({"milestone": f"{mark:,} career {labels[key]}", "stat": key, "threshold": mark, "date": g["date"],
                                "season": g.get("season"), "opponent": g.get("opponent"), "game_number": n,
                                "total_after": totals[key], "age": age_text(birth, g["date"]), "note": g.get("note")})
    for key, label, _ in stats:
        if pending[key]:
            upcoming.append({"milestone": f"{pending[key][0]:,} career {label}", "current": totals[key],
                             "needed": pending[key][0] - totals[key]})
    return reached, upcoming


def career_milestones(records, birth):
    """{"regular": reached, "regular_next": upcoming, "playoff": ..., "firsts": [...]} from closed records."""
    regular, playoff = _played(records, "regular"), _played(records, "playoff")
    reg, reg_next = _crossings(regular, STATS, birth)
    po, po_next = _crossings(playoff, PLAYOFF_STATS, birth)
    firsts = []
    for label, test in FIRSTS:
        g = next((g for g in regular if test(g["line"])), None)
        if g:
            firsts.append({"milestone": label, "date": g["date"], "season": g.get("season"), "opponent": g.get("opponent"),
                           "line": f"{g['line']['pts']} pts, {g['line']['reb']} reb, {g['line']['ast']} ast",
                           "age": age_text(birth, g["date"]), "note": g.get("note")})
    firsts.sort(key=lambda r: r["date"])
    return {"regular": reg, "regular_next": reg_next, "playoff": po, "playoff_next": po_next, "firsts": firsts,
            "regular_games": len(regular), "playoff_games": len(playoff)}


def markdown(name, birth, as_of, data, link):
    """The career milestones page; `link(note)` gives a relative link to a closed game note."""
    def game(row):
        return f"[{row['opponent'] or 'game'}]({link(row['note'])})" if row.get("note") else (row.get("opponent") or "N/A")
    text = (f"# {name} | Career milestones\n\nCareer date: {as_of}. Born {birth or 'not recorded'}. "
            f"{data['regular_games']} regular-season and {data['playoff_games']} playoff games closed.\n\n"
            "Milestones count closed regular-season games (the NBA convention); playoff milestones are their own record and "
            "preseason never counts. Each is dated by the game that reached it, with his age on that day. "
            "[Season tracker](calendar.md) · [All milestones](README.md)\n\n")
    sections = (("Career firsts", ["Milestone", "Date", "Age", "Season", "Opponent", "Line"], data["firsts"],
                 lambda r: [r["milestone"], r["date"], r["age"], r["season"], game(r), r["line"]]),
                ("Regular-season milestones reached", ["Milestone", "Date", "Age", "Season", "Game no.", "Opponent", "Total after"], data["regular"],
                 lambda r: [r["milestone"], r["date"], r["age"], r["season"], r["game_number"], game(r), f"{r['total_after']:,}"]),
                ("Next regular-season milestones", ["Milestone", "Current", "Still needed"], data["regular_next"],
                 lambda r: [r["milestone"], f"{r['current']:,}", f"{r['needed']:,}"]),
                ("Playoff milestones reached", ["Milestone", "Date", "Age", "Season", "Game no.", "Opponent", "Total after"], data["playoff"],
                 lambda r: [r["milestone"], r["date"], r["age"], r["season"], r["game_number"], game(r), f"{r['total_after']:,}"]),
                ("Next playoff milestones", ["Milestone", "Current", "Still needed"], data["playoff_next"],
                 lambda r: [r["milestone"], f"{r['current']:,}", f"{r['needed']:,}"]))
    for title, cols, rows, fmt in sections:
        text += f"## {title}\n\n| " + " | ".join(cols) + " |\n| " + " | ".join("---" for _ in cols) + " |\n"
        text += "".join("| " + " | ".join(str(x) for x in fmt(r)) + " |\n" for r in rows) or ("| None yet |" + " |" * (len(cols) - 1) + "\n")
        text += "\n"
    return text
