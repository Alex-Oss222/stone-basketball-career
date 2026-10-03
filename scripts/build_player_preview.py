#!/usr/bin/env python3
"""Create clearly fictional report examples outside the canonical career tree."""
from __future__ import annotations

import copy
import json
import math
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.career_stats import normalize_line, select
from runtime.player_reports import report, identity_block
from runtime.stat_layout import ReportStyle
from runtime.career_stats import aggregate
from runtime.shot_chart import NBA_GEOMETRY, ZONES, aggregate_shots, make_illustrative_shots

NOTICE = "> **ILLUSTRATIVE TEMPLATE ONLY.** All games, teams, dates and performance figures below are invented for layout testing. They are not Wade's career results or a simulated future outcome.\n\n"


def preview_terms(text):
    """Sample-only vocabulary; do not rewrite canonical award records or reports."""
    return text.replace("HONORS", "AWARDS").replace("Honors", "Awards").replace("honors", "awards").replace("| Honor |", "| Award |")


def navigation_badge(label, subtitle, color):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="620" height="92" viewBox="0 0 620 92" role="img" aria-label="{escape(label)}">
<rect width="620" height="92" rx="12" fill="#141517"/>
<rect width="8" height="92" rx="4" fill="{color}"/>
<text x="28" y="40" fill="{color}" font-family="sans-serif" font-size="27" font-weight="700">{escape(label)}</text>
<text x="28" y="69" fill="#cbd0d7" font-family="sans-serif" font-size="16">{escape(subtitle)}</text>
<text x="580" y="56" fill="{color}" font-family="sans-serif" font-size="29">›</text>
</svg>\n'''


class PreviewStyle(ReportStyle):
    """Opt-in sample navigation, retaining the shared complete statistics table."""

    def per_game(self, page, groups, heading="Per game", *, decorate=True, as_of=None):
        text = super().per_game(page, groups, heading, decorate=False, as_of=as_of)
        # This old asset is retained as a plain heading for existing external links.
        # Navigation uses linked Markdown images, never SVG-internal hotspots.
        self.outputs[self.asset_dir / "per_game.svg"] = navigation_badge(
            "PER GAME", "Complete box-score columns below", "#e03a55")
        if decorate:
            prefix = f"### {heading}\n\n"
            text = text.replace(prefix, prefix + card_navigation(period_for_page(page)), 1)
        return preview_terms(text)


def period_for_page(page):
    stem = page.stem.removesuffix("_detail")
    return {"sample_season": "season", "sample_month": "month", "sample_week": "week",
            "sample_dnp": "dnp", **{f"sample_game_{i}": f"game-{i}" for i in range(1, 7)}}.get(stem, "season")


def card_navigation(period="season"):
    return (f"[![Shooting: open the shot-chart page](assets/shooting_link.svg)](sample_shooting.md#{period}) "
            "[![Awards: open the annual-awards page](assets/awards_link.svg)](sample_awards.md)\n\n"
            f"[Interactive Shooting](player_cards_preview.html?period={period}#shooting) · "
            "[Interactive Awards](player_cards_preview.html#awards) · "
            "[Shooting text version](sample_shooting.md) · [Awards text version](sample_awards.md)\n\n")


def annual_awards(records, season, cutoff):
    """Only earned annual records known at the selected scenario cutoff."""
    return [a for a in records if a.get("scope") == "annual" and a.get("season") == season
            and a.get("status") == "earned" and a.get("awarded_on") and a["awarded_on"] <= cutoff]


def cards_payload(identity, records, awards):
    shots = make_illustrative_shots(records, example_only=True)
    periods = []
    selections = [("season", "2003-04 season through November 12", "season", "2003-06-01", "2003-11-12"),
                  ("month", "November through November 12", "month", "2003-11-01", "2003-11-12"),
                  ("week", "November 1 to 7", "week", "2003-11-01", "2003-11-07")]
    for r in records:
        pid = "dnp" if r["line"] is None else "game-" + r["event_id"].rsplit("-", 1)[-1]
        selections.append((pid, f'{r["date"]} vs {r["opponent"]}' + (" · DNP" if pid == "dnp" else ""),
                           "game", r["date"], r["date"]))
    for pid, label, kind, start, end in selections:
        selected = select(records, start=start, end=end)
        ids = {r["event_id"] for r in selected}
        selected_shots = [s for s in shots if s["game_id"] in ids]
        summary = aggregate(selected)
        periods.append(dict(id=pid, label=label, kind=kind, season="2003-04", start=start, end=end, cutoff=end,
            games=summary["closed"], appearances=summary["gp"], dnp=summary["dnp"],
            source_games=[dict(id=r["event_id"], date=r["date"], opponent=r["opponent"], status=r["status"],
                               appearance=r["appearance"], href=r["note"].name) for r in selected],
            box=summary["totals"], rates=summary["rates"], shots=selected_shots,
            shooting=aggregate_shots(selected, selected_shots)))
    current_awards = [{**a, "scope": "monthly" if a["id"] == "example-rookie-month" else "weekly",
                       "source_label": "Existing fictional layout fixture"} for a in awards]
    annual_demo = [
        dict(id="annual-demo-all-nba", name="All-NBA Third Team", short_name="ALL-NBA 3RD", scope="annual",
             season="2004-05", awarded_on="2005-05-20", status="earned", source_label="Independent fictional annual-award design fixture",
             description="Hypothetical earned team selection used only to demonstrate the annual-awards layout."),
        dict(id="annual-demo-defense", name="All-Defensive Second Team", short_name="ALL-DEF 2ND", scope="annual",
             season="2004-05", awarded_on="2005-05-25", status="earned", source_label="Independent fictional annual-award design fixture",
             description="Hypothetical earned defensive-team selection, separate from the November 2003 sample."),
        dict(id="annual-demo-nominee", name="Most Improved Player", short_name="MIP", scope="annual",
             season="2004-05", awarded_on="2005-05-10", status="nominated", source_label="Independent fictional exclusion fixture",
             description="Nomination is not an earned award and must not render as a badge."),
    ]
    snap = identity["snapshots"][0]
    return dict(schema_version=1, identity=dict(name=identity["display_name"], team=snap["team"], jersey=snap["jersey"],
        position=" / ".join(snap["positions"]), age=19, height=identity["height_in_shoes"],
        weight=f'{identity["weight_lb"]} lb', shoots=identity["shooting_hand"], entry=snap["entry"],
        photo_url=None, initials="EP"),
        notice="ILLUSTRATIVE TEMPLATE ONLY. Fictional box scores and synthetic shot locations for layout testing only. No real tracking or career results.",
        geometry=NBA_GEOMETRY, zones=ZONES, default_period="season", periods=periods,
        awards=dict(default_scenario="current", scenarios=[
            dict(id="current", label="2003-04 current sample", season="2003-04", cutoff="2003-11-12",
                 notice="No annual award has been earned by this sample's November 12, 2003 cutoff. Weekly and monthly awards remain separate.", records=current_awards),
            dict(id="annual-demo", label="Annual award design sample: 2004-05", season="2004-05", cutoff="2005-06-30",
                 notice="Independent hypothetical full-year design scenario. Not the 2003 sample, a future career result, or an award known in November 2003.", records=annual_demo)]))


def fg_color(rate):
    if rate is None:
        return "#747c8b"
    # Match the offline interactive screen's fixed 0-100% color scale.
    stops = [(0, (40, 125, 196)), (.25, (124, 172, 205)), (.5, (237, 229, 207)),
             (.75, (219, 116, 126)), (1, (196, 33, 64))]
    value = min(1, max(0, rate))
    low, high = next((a, b) for a, b in zip(stops, stops[1:]) if value <= b[0])
    weight = (value - low[0]) / (high[0] - low[0])
    rgb = [math.floor(a + (b - a) * weight + .5) for a, b in zip(low[1], high[1])]
    return "rgb(" + ",".join(map(str, rgb)) + ")"


def shot_chart_svg(period):
    """Exact court geometry, fixed per-game area scale and absolute FG% colors."""
    g = NBA_GEOMETRY
    sx = lambda x: 320 + x * 10
    sy = lambda y: 82 + (g["half_court_y"] - y) * 10
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="640" height="700" viewBox="0 0 640 700" role="img" aria-labelledby="title desc">',
             f'<title id="title">Synthetic shooting map: {escape(period["label"])}</title>',
             '<desc id="desc">Illustrative locations only. Circle area is attempts per appearance on one fixed scale; color is observed field-goal percentage. No league comparison.</desc>',
             '<rect width="640" height="700" rx="18" fill="#141517"/>',
             f'<text x="28" y="35" fill="#fff" font-family="sans-serif" font-size="20" font-weight="700">{escape(period["label"])}</text>',
             '<text x="28" y="61" fill="#c7cdd6" font-family="sans-serif" font-size="13">SYNTHETIC LOCATIONS · FIELD GOALS ONLY</text>',
             f'<rect x="{sx(g["x_min"])}" y="{sy(g["half_court_y"])}" width="500" height="470" fill="#1f242b" stroke="#a1a9b4"/>',
             f'<rect x="{sx(-g["paint_half_width"])}" y="{sy(g["paint_top_y"])}" width="160" height="190" fill="#282b32" stroke="#a1a9b4"/>',
             f'<circle cx="320" cy="{sy(g["paint_top_y"])}" r="60" fill="none" stroke="#78828f"/>',
             f'<path d="M {sx(-22)} {sy(g["baseline_y"])} L {sx(-22)} {sy(g["three_point_join_y"])} A 237.5 237.5 0 0 1 {sx(22)} {sy(g["three_point_join_y"])} L {sx(22)} {sy(g["baseline_y"])}" fill="none" stroke="#d3d8df" stroke-width="2"/>',
             f'<path d="M {sx(-4)} {sy(0)} A 40 40 0 0 1 {sx(4)} {sy(0)}" fill="none" stroke="#78828f"/>',
             f'<line x1="{sx(-3)}" y1="{sy(-1.25)}" x2="{sx(3)}" y2="{sy(-1.25)}" stroke="#d3d8df" stroke-width="3"/>',
             f'<circle cx="320" cy="{sy(0)}" r="7.5" fill="none" stroke="#f2a251" stroke-width="2"/>']
    shooting = period["shooting"]
    for b in shooting["bins"]:
        area = b["area_weight"]
        if area is None or area <= 0:
            continue
        radius = 16 * math.sqrt(area)
        title = f'{b["fgm"]}/{b["fga"]} FG; {b["fg_pct"]:.1%}; {area:.2f} FGA per appearance'
        parts.append(f'<circle cx="{sx(b["x"]):.3f}" cy="{sy(b["y"]):.3f}" r="{radius:.3f}" fill="{fg_color(b["fg_pct"])}" fill-opacity=".8" stroke="#f1f3f6" stroke-width="1"><title>{escape(title)}</title></circle>')
    if not shooting["bins"]:
        message = "No appearance: no shot sample" if period["appearances"] == 0 else "No located shot sample"
        parts.append(f'<text x="320" y="274" fill="#e2e6ed" font-family="sans-serif" font-size="20" text-anchor="middle">{message}</text>')
    parts.append('<text x="28" y="582" fill="#fff" font-family="sans-serif" font-size="14">FG% color, absolute observed accuracy</text>')
    for i, rate in enumerate((0, .25, .5, .75, 1)):
        label, color = f"{rate:.0%}", fg_color(rate)
        x = 28 + i * 122
        parts.append(f'<rect x="{x}" y="596" width="18" height="18" rx="3" fill="{color}"/><text x="{x + 25}" y="610" fill="#cbd0d7" font-family="sans-serif" font-size="12">{label}</text>')
    parts += ['<text x="28" y="645" fill="#cbd0d7" font-family="sans-serif" font-size="13">Area: fixed scale, 16 px radius = 1 FGA per appearance</text>',
              '<text x="28" y="674" fill="#cbd0d7" font-family="sans-serif" font-size="13">Full percentages, attempts, zones and source games follow in text.</text>', '</svg>']
    return "\n".join(parts) + "\n"


def display(value, kind="number"):
    if value is None:
        return "N/A"
    return f"{value:.1%}" if kind == "percent" else f"{value:.2f}" if kind == "rate" else str(value)


def card_fallbacks(folder, payload):
    """Readable repository pages back every clickable image banner."""
    outputs = {}
    shooting = "# Shooting | Example Player\n\n" + NOTICE
    shooting += "[Open interactive Shooting](player_cards_preview.html#shooting) · [Statistics index](player_stats_preview.md) · [Awards](sample_awards.md)\n\n"
    shooting += "Shot coordinates are **synthetic design fixtures**, explicitly generated to reconcile with the six existing fictional game boxes. They are not inferred real locations or canonical tracking. Free throws contribute to PTS but never appear as field-goal dots.\n\n"
    shooting += "**Read the map:** circle area represents field-goal attempts per appearance, using one fixed scale across periods. Color represents absolute observed FG%, with no invented league benchmark. Hover inspection and selectors are in the interactive version; the complete values remain below.\n\n"
    shooting += " · ".join(f'[{p["id"].replace("-", " ").title()}](#{p["id"]})' for p in payload["periods"]) + "\n\n"
    for p in payload["periods"]:
        pid, s = p["id"], p["shooting"]
        shooting += f'## {pid.replace("-", " ").title()}\n\n**{p["label"]}** · {p["appearances"]} appearances · {p["dnp"]} DNP · Cutoff {p["cutoff"]}.\n\n'
        shooting += f'[Open this period interactively](player_cards_preview.html?period={pid}#shooting)\n\n'
        shooting += f'![Synthetic shooting map, {p["label"]}](assets/shooting_{pid}.svg)\n\n'
        outputs[folder / f"assets/shooting_{pid}.svg"] = shot_chart_svg(p)
        shooting += "| Zone | FGM | FGA | FG% | FG points / game | FGA / game |\n| --- | ---: | ---: | ---: | ---: | ---: |\n"
        for z in [*s["zones"], dict(id="total", label="All field goals", **s["totals"])]:
            shooting += f'| {z["label"]} | {display(z["fgm"])} | {display(z["fga"])} | {display(z["fg_pct"], "percent")} | {display(z["fg_ppg"], "rate")} | {display(z["fga_per_game"], "rate")} |\n'
        coverage = s["coverage"]
        shooting += f'\nCoverage: **{coverage["status"]}**; {coverage["located_attempts"]} located attempts, {coverage["unlocated_attempts"]} unlocated, {coverage["outside_view_attempts"]} outside this view, {display(coverage["missing_attempts"])} missing.\n\n'
        if p["appearances"] == 0:
            shooting += "A DNP has no appearance and no shooting-percentage sample. Zero attempts do not mean 0.0% shooting.\n\n"
        shooting += "Source games: " + " · ".join(f'[{r["date"]} vs {r["opponent"]}]({r["href"]})' for r in p["source_games"]) + ".\n\n"
    shooting += "Zones are non-overlapping: three-point range first, then the paint, then outside-paint distance bands. A coordinate on the three-point line remains a two-point shot. Percentages are pooled makes divided by pooled attempts, never averages of game percentages.\n\n"
    shooting += "[Raw synthetic shot fixture](illustrative_shots.json) · [Period payload](player_cards_data.json) · [Definitions and implementation boundaries](../shooting_and_awards_design.md)\n"
    outputs[folder / "sample_shooting.md"] = shooting
    awards = "# Awards | Example Player\n\n" + NOTICE
    awards += "[Open interactive Awards](player_cards_preview.html#awards) · [Statistics index](player_stats_preview.md) · [Shooting](sample_shooting.md)\n\n"
    awards += "This page presents **annual awards by season**. Only records explicitly marked earned, scoped to that season, and announced on or before that scenario's cutoff receive a badge. Nominees and pending decisions are excluded.\n\n"
    for scenario in payload["awards"]["scenarios"]:
        earned = annual_awards(scenario["records"], scenario["season"], scenario["cutoff"])
        awards += f'## {scenario["label"]}\n\n{scenario["notice"]}\n\n**Season:** {scenario["season"]}. **Known through:** {scenario["cutoff"]}. **Earned annual awards:** {len(earned)}.\n\n'
        if not earned:
            awards += "No earned annual awards at this cutoff. The existing fictional Rookie of the Month and Player of the Week badges remain period awards on the sample reports; they do not become annual awards.\n\n"
        for a in earned:
            asset = f'assets/{a["id"]}.svg'
            outputs[folder / asset] = navigation_badge(a["name"], f'{a["season"]} · Earned {a["awarded_on"]} · Independent fictional scenario', "#efbf58")
            awards += f'![{a["name"]}, fictional annual-award design scenario]({asset})\n\n'
        if earned:
            awards += "| Earned award | Season | Announced | Evidence |\n| --- | --- | --- | --- |\n"
            for a in earned:
                awards += f'| {a["name"]} | {a["season"]} | {a["awarded_on"]} | {a["source_label"]} |\n'
            awards += "\nThe nominated Most Improved Player record is deliberately excluded from earned badges. This design scenario never joins the November 2003 identity, totals or current-award count.\n\n"
    awards += "[Structured fixture](player_cards_data.json) · [Award scope and cutoff rules](../shooting_and_awards_design.md)\n"
    outputs[folder / "sample_awards.md"] = awards
    return outputs


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
    style = PreviewStyle(identity, awards, "2003-11-12", outputs, folder / "assets")
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
    outputs[index] += "[Open interactive Shooting and Awards cards](player_cards_preview.html) · [Shooting page](sample_shooting.md) · [Annual Awards page](sample_awards.md)\n\n"
    outputs[index] += "The two image banners are ordinary Markdown links and work in repository views. Open the HTML preview in a browser for period selectors and shot inspection. Synthetic locations illustrate the layout; they are not real tracking.\n\n"
    outputs[index] += "| Level | Preview | What changes at this level |\n| --- | --- | --- |\n"
    outputs[index] += "| Season | [Season summary](sample_season.md) · [Full detail](sample_season_detail.md) | Season totals, monthly comparison, splits and highs |\n"
    outputs[index] += "| Month | [November](sample_month.md) · [Full detail](sample_month_detail.md) | Monthly production and week-by-week rollup |\n"
    outputs[index] += "| Week | [November 1-7](sample_week.md) · [Full detail](sample_week_detail.md) | Week, month-to-date, season-to-date and game log |\n"
    outputs[index] += "| Game | [One game](sample_game_4.md) · [DNP example](sample_dnp.md) | Actual box totals, shooting and participation |\n\n"
    outputs[index] += identity_block(identity, "2003-11-12", style=style, page=index)
    outputs[index] += "## Statistics\n\nSix illustrative appearances, plus one recorded DNP, through November 12. All honors here are fictional layout examples.\n\n"
    outputs[index] += style.per_game(index, [("Example season", records, folder / "sample_season.md", {"start": "2003-06-01", "end": "2003-11-12"})])
    outputs[index] += "[Full statistics definitions](../player_statistics.md) · [Current canonical career](../../career/Dwyane_Wade/README.md)\n"
    payload = cards_payload(identity, records, awards)
    outputs[folder / "assets/shooting_link.svg"] = navigation_badge("Shooting", "Court map · attempt frequency · accuracy · period selector", "#e34e67")
    outputs[folder / "assets/awards_link.svg"] = navigation_badge("Awards", "Earned annual awards · season selector · dated record", "#efbf58")
    outputs[folder / "player_cards_data.json"] = json.dumps(payload, indent=2) + "\n"
    outputs[folder / "illustrative_shots.json"] = json.dumps(dict(schema_version=1, record_type="illustrative_synthetic_locations",
        notice=payload["notice"], coordinate_system="Feet from basket: x lateral; y toward half court; baseline y=-5.25",
        shots=payload["periods"][0]["shots"]), indent=2) + "\n"
    outputs.update(card_fallbacks(folder, payload))
    template = (Path(__file__).resolve().parents[1] / "runtime/assets/player_cards.html").read_text()
    if template.count("__PLAYER_CARD_DATA__") != 1:
        raise ValueError("player-card HTML template must contain exactly one __PLAYER_CARD_DATA__ token")
    # Escape HTML-significant characters while retaining valid JSON for inline data.
    encoded = json.dumps(payload).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    outputs[folder / "player_cards_preview.html"] = template.replace("__PLAYER_CARD_DATA__", encoded)
    return {path: ("<!-- ILLUSTRATIVE TEMPLATE ONLY -->\n" + preview_terms(text) if path.suffix == ".svg"
                   else preview_terms(text) if path.suffix == ".md" else text) for path, text in outputs.items()}


if __name__ == "__main__":
    for path, text in build_preview().items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    print("Built illustrative reports in docs/examples; no career results written.")
