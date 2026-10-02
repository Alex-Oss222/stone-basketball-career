#!/usr/bin/env python3
"""Create clearly fictional report examples outside the canonical career tree."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.career_stats import normalize_line, select
from runtime.player_reports import report, identity_block
from runtime.stat_layout import ReportStyle
from runtime.career_stats import aggregate

NOTICE = "> **ILLUSTRATIVE TEMPLATE ONLY.** All games, teams, dates and performance figures below are invented for layout testing. They are not Wade's career results or a simulated future outcome.\n\n"


def build_preview(root=ROOT):
    folder = root / "docs/examples"
    identity = copy.deepcopy(json.loads((root / "career/Dwyane_Wade/professional_identity.json").read_text()))
    identity.update(full_name="Example Player", display_name="Example Player", player_id="example_player", date_of_birth="1984-01-17", record_type="illustrative")
    identity["snapshots"] = [{**identity["snapshots"][0], "as_of": "2003-10-01", "team": "Example Club",
        "jersey": 7, "roster_status": "Active (fictional example)", "contract": "Example contract",
        "role": "Starting guard (example)", "entry": "Example draft entry: round 1, pick 5", "prior_program": "Example University"}]
    # PTS, REB and percentages are derived, never typed into the rendered tables.
    data = [
        ("2003-10-30", "Club A", "home", True, 34, 8, 17, 1, 3, 5, 6, 1, 4, 6, 2, 1, 3, 2, 8),
        ("2003-11-01", "Club B", "away", False, 36, 9, 20, 2, 5, 4, 5, 2, 5, 7, 1, 0, 4, 3, -4),
        ("2003-11-03", "Club C", "home", True, 32, 7, 13, 0, 1, 6, 7, 1, 3, 10, 3, 1, 2, 2, 12),
        ("2003-11-05", "Club D", "away", True, 38, 11, 21, 2, 4, 7, 8, 3, 7, 8, 2, 2, 3, 4, 9),
        ("2003-11-09", "Club A", "home", False, 33, 6, 15, 1, 4, 5, 6, 0, 4, 5, 1, 0, 5, 3, -7),
        ("2003-11-12", "Club B", "away", True, 35, 10, 18, 1, 2, 3, 4, 2, 4, 9, 2, 1, 2, 2, 6),
    ]
    records = []
    for i, row in enumerate(data, 1):
        day, opp, venue, win, minutes, fgm, fga, tpm, tpa, ftm, fta, orb, drb, ast, stl, blk, tov, pf, pm = row
        line = normalize_line(dict(seconds=minutes*60, pts=2*fgm+tpm+ftm, fgm=fgm, fga=fga, tpm=tpm, tpa=tpa,
            ftm=ftm, fta=fta, orb=orb, drb=drb, ast=ast, stl=stl, blk=blk, tov=tov, pf=pf, started=True, plus_minus=pm))
        records.append(dict(date=day, opponent=opp, venue=venue, result="W 102-96" if win else "L 94-100",
            win=win, line=line, event_id=f"illustrative-{i}", competition="regular", season="2003-04",
            status="played", coverage="complete", appearance="Played", team="Example Club", note=folder / f"sample_game_{i}.md"))
    records.append(dict(date="2003-11-07", opponent="Club E", venue="home", result="W 90-85", win=True,
        line=None, event_id="illustrative-dnp", competition="regular", season="2003-04", status="played",
        coverage="complete", appearance="DNP: inactive (example)", team="Example Club", note=folder / "sample_dnp.md"))
    records.sort(key=lambda r: r["date"])
    month = select(records, start="2003-11-01")
    week = select(month, end="2003-11-07")
    index = folder / "player_stats_preview.md"
    nav = [("Preview index", index)]
    outputs = {}
    awards = [
        dict(id="example-rookie-month", name="Rookie of the Month", short_name="ROTM", competition="regular", season="2003-04",
             period_start="2003-10-01", period_end="2003-10-31", awarded_on="2003-11-01", status="earned"),
        dict(id="example-player-week", name="Player of the Week", short_name="POTW", competition="regular", season="2003-04",
             period_start="2003-11-01", period_end="2003-11-07", awarded_on="2003-11-08", status="earned"),
    ]
    style = ReportStyle(identity, awards, "2003-11-12", outputs, folder / "assets")
    scopes = [("Season", records, "sample_season.md", "2003-11-12"),
              ("November", month, "sample_month.md", "2003-11-12"),
              ("November Week 1 (days 1-7)", week, "sample_week.md", "2003-11-07")]
    for label, rows, filename, cutoff in scopes:
        page = folder / filename
        scope = {"competition": "regular", "season": "2003-04", "start": "2003-06-01" if filename == "sample_season.md" else "2003-11-01", "end": cutoff}
        groups = []
        if filename == "sample_season.md":
            groups = [("October", select(records, end="2003-10-31"), None, {"start": "2003-10-01", "end": "2003-10-31"}),
                      ("November", month, folder / "sample_month.md", {"start": "2003-11-01", "end": "2003-11-30"})]
        elif filename == "sample_month.md":
            groups = [("Week 1: November 1-7", week, folder / "sample_week.md", {"start": "2003-11-01", "end": "2003-11-07"}),
                      ("Week 2: November 8-14 (through Nov 12)", select(month, start="2003-11-08"), None, {"start": "2003-11-08", "end": "2003-11-14"})]
        comparison = [("This week", week, None, {"start": "2003-11-01", "end": "2003-11-07"}),
                      ("Month through Nov 7", select(month, end="2003-11-07"), None, {"start": "2003-11-01", "end": "2003-11-07"}),
                      ("Season through Nov 7", select(records, end="2003-11-07"), None, {"start": "2003-06-01", "end": "2003-11-07"})] if filename == "sample_week.md" else []
        outputs[page] = NOTICE + report(page, f"Example Player | {label}", identity, cutoff, rows,
            navigation=nav, groups=groups, comparison=comparison, detail=folder / filename.replace(".md", "_detail.md"), style=style, scope=scope)
        detail = folder / filename.replace(".md", "_detail.md")
        outputs[detail] = NOTICE + report(detail, f"Example Player | {label} detail", identity, cutoff, rows,
                                          navigation=[("Summary", page), *nav], full=True, style=style, scope=scope)
    for r in records:
        outputs[r["note"]] = NOTICE + report(r["note"], f"Example Player | {r['date']} vs {r['opponent']}",
            identity, r["date"], [r], navigation=nav, full=True, style=style,
            scope={"competition": "regular", "season": "2003-04", "start": r["date"], "end": r["date"], "honors": False})
    outputs[index] = "# Player statistics | Filled preview\n\n" + NOTICE
    outputs[index] += "These examples use the same calculations and presentation as the career reports. Start with the season and follow its month, week and game links.\n\n"
    outputs[index] += "| Level | Preview | What changes at this level |\n| --- | --- | --- |\n"
    outputs[index] += "| Season | [Season summary](sample_season.md) · [Full detail](sample_season_detail.md) | Season totals, monthly comparison, splits and highs |\n"
    outputs[index] += "| Month | [November](sample_month.md) · [Full detail](sample_month_detail.md) | Monthly production and week-by-week rollup |\n"
    outputs[index] += "| Week | [November 1-7](sample_week.md) · [Full detail](sample_week_detail.md) | Week, month-to-date, season-to-date and game log |\n"
    outputs[index] += "| Game | [One game](sample_game_4.md) · [DNP example](sample_dnp.md) | Actual box totals, shooting and participation |\n\n"
    outputs[index] += identity_block(identity, "2003-11-12", style=style, page=index)
    outputs[index] += "## Statistics\n\nSix illustrative appearances, plus one recorded DNP, through November 12. All honors here are fictional layout examples.\n\n"
    outputs[index] += style.per_game(index, [("Example season", records, folder / "sample_season.md", {"start": "2003-06-01", "end": "2003-11-12"})])
    outputs[index] += "[Full statistics definitions](../player_statistics.md) · [Current canonical career](../../career/Dwyane_Wade/README.md)\n"
    return {path: ("<!-- ILLUSTRATIVE TEMPLATE ONLY -->\n" + text if path.suffix == ".svg" else text) for path, text in outputs.items()}


if __name__ == "__main__":
    for path, text in build_preview().items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    print("Built illustrative reports in docs/examples; no career results written.")
