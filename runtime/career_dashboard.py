"""GitHub-compatible career overview SVG, drawn from the same report totals."""
from __future__ import annotations

from datetime import date
from html import escape
import textwrap

from .career_stats import identity_at


def season_highs(records: list[dict], season: str, competition: str = "regular") -> list[tuple]:
    """[(label, value, 'date vs/at opponent')] for the season's closed appearances; ties list the earliest game."""
    played = [r for r in records if r.get("season") == season and r.get("competition") == competition
              and r.get("status") == "played" and r.get("line") and r["line"].get("appeared")]
    out = []
    for key, label in (("pts", "Points"), ("reb", "Rebounds"), ("ast", "Assists"), ("stl", "Steals"), ("blk", "Blocks"),
                       ("fgm", "Field goals"), ("tpm", "Threes"), ("ftm", "Free throws"), ("seconds", "Minutes")):
        value = lambda r: r["line"].get(key) if key != "reb" else (r["line"].get("reb") if r["line"].get("reb") is not None
                                                                   else (r["line"].get("orb") or 0) + (r["line"].get("drb") or 0))
        rows = [r for r in played if value(r) is not None]
        if not rows:
            continue
        best = max(value(r) for r in rows)
        games = sorted((r for r in rows if value(r) == best), key=lambda r: r["date"])
        first = games[0]
        where = f'{"at" if first.get("venue") == "away" else "vs"} {first.get("opponent")}'
        when = date.fromisoformat(first["date"]).strftime("%b %d")
        shown = f"{best / 60:.0f}" if key == "seconds" else str(best)
        out.append((label, shown, f"{when} {where}" + (f" (+{len(games) - 1})" if len(games) > 1 else "")))
    return out


def career_overview(identity: dict, as_of: str, regular: dict, playoffs: dict, highs: list | None = None,
                    highs_title: str = "Season highs", season: str | None = None, palette: dict | None = None) -> str:
    """The career overview card, or with `season` the same card for one season (its own totals and highs)."""
    scope = season or "Career"
    p = identity_at(identity, as_of)
    red, dark, white, muted = "#a71930", "#222326", "#ffffff", "#d0d1d4"
    light = "#f6c7cf"                      # Miami's tint; another club's card passes its own colours (`palette`)
    if palette:
        red, light = palette["primary"], palette.get("light", "#e6dcf5")
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="{1110 if highs else 820}" viewBox="0 0 1280 {1110 if highs else 820}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{escape(p.get("display_name", p["full_name"]))} {escape(scope.lower() if not season else season)} overview</title>',
        f'<desc id="desc">Simulation career as of {escape(as_of)}. Professional identity, NBA regular-season and playoff statistics. N/A means no qualifying denominator or missing data. An accessible text version follows this image in the README.</desc>',
        f'<rect width="1280" height="{1110 if highs else 820}" rx="28" fill="#141517"/>',
        '<g>',
    ]

    def rect(x, y, width, height, fill, radius=24):
        parts.append(f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="{radius}" fill="{fill}"/>')

    def text(x, y, value, size=20, color=white, weight=400, anchor="start"):
        parts.append(f'<text x="{x}" y="{y}" font-family="sans-serif" fill="{color}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}">{escape(str(value))}</text>')

    def line(x1, y1, x2, y2, color="#ffffff", opacity="0.18"):
        parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-opacity="{opacity}"/>')

    def wrapped(x, y, value, *, width=48, size=20, color=white, weight=400, leading=25):
        rows = textwrap.wrap(str(value), width=width) or [""]
        for i, row in enumerate(rows):
            text(x, y + i * leading, row, size, color, weight)
        return y + (len(rows) - 1) * leading

    def number(value):
        return "N/A" if value is None else f"{value:.1f}"

    def percent(value):
        return "N/A" if value is None else f"{100 * value:.1f}"

    def stats_card(x, y, title, a, fill):
        rect(x, y, 610, 270, fill)
        text(x + 24, y + 38, title, 24, weight=700)
        text(x + 584, y + 38, f'{a["gp"] if a["gp"] is not None else "N/A"} G', 19, muted, 700, "end")
        line(x + 24, y + 57, x + 586, y + 57)
        fields = [("PPG", number(a["pg"]["pts"])), ("RPG", number(a["pg"]["reb"])),
                  ("APG", number(a["pg"]["ast"])), ("SPG", number(a["pg"]["stl"])),
                  ("BPG", number(a["pg"]["blk"])), ("MPG", number(a["pg"]["minutes"])),
                  ("FG%", percent(a["rates"]["fg_pct"])), ("3P%", percent(a["rates"]["three_pct"])),
                  ("FT%", percent(a["rates"]["ft_pct"])), ("TS% (est.)", percent(a["rates"]["ts_pct"]))]
        for i, (label, value) in enumerate(fields):
            cx = x + 70 + (i % 5) * 117.5
            cy = y + 103 + (i // 5) * 88
            text(cx, cy, value, 28, weight=600, anchor="middle")
            text(cx, cy + 27, label, 17, muted, anchor="middle")
        status = "No appearances recorded" if a["gp"] == 0 else f'Player box coverage: {a["covered"]}/{a["closed"]} closed games'
        if not a["complete"]:
            status = f'Incomplete player coverage: {a["covered"]}/{a["closed"]} closed games'
        text(x + 24, y + 250, status, 16, muted)

    rect(20, 20, 1240, 170, red)
    text(52, 57, "PLAYER CAREER" if not season else f"PLAYER SEASON · {season}", 16, light, 700)
    text(52, 110, p.get("display_name", p["full_name"]), 46, weight=700)
    text(52, 152, f'{p["team"]}  ·  {p["league"]}  ·  {" / ".join(p["positions"])}', 23)
    text(1228, 58, "SIMULATION RECORD", 16, light, 700, "end")
    text(1228, 90, date.fromisoformat(as_of).strftime("%B %d, %Y"), 22, white, 500, "end")
    text(1228, 150, "Career overview" if not season else f"{season} overview", 20, light, 500, "end")

    rect(20, 210, 610, 270, red)
    text(44, 248, "Professional identity", 24, weight=700)
    line(44, 267, 606, 267)
    height = p["height_in_shoes"].replace(" ft ", "′ ").replace(" in", "″")
    fields = [
        ("Position", " / ".join(p["positions"])),
        ("Number", f'#{p["jersey"]}' if p["jersey"] is not None else "Unassigned"),
        ("Birthdate", date.fromisoformat(p["date_of_birth"]).strftime("%b %d, %Y")),
        ("Height (in shoes)", height), ("Weight", f'{p["weight_lb"]} lb'),
        ("Age at checkpoint", str(p["age"])),
    ]
    for i, (label, value) in enumerate(fields):
        cx = 123 + (i % 3) * 195
        cy = 308 + (i // 3) * 84
        text(cx, cy, value, 23 if i != 2 else 21, weight=600, anchor="middle")
        text(cx, cy + 27, label, 17, light, anchor="middle")
    text(44, 460, f'Measurements recorded {p["physical_profile_as_of"]}', 16, light)

    stats_card(650, 210, f"{scope} playoffs", playoffs, dark)
    stats_card(20, 500, f"{scope} regular season", regular, red)

    rect(650, 500, 610, 270, dark)
    text(674, 538, "Professional status", 24, weight=700)
    line(674, 557, 1236, 557)
    text(674, 588, "NBA ENTRY", 14, muted, 700)
    last = wrapped(674, 616, p["entry"], width=52, size=20, weight=500, leading=24)
    text(674, last + 35, "ROSTER STATUS", 14, muted, 700)
    text(674, last + 61, p["roster_status"], 21, weight=500)
    text(674, 741, p["prior_program"], 18, muted)

    footer = 801
    if highs:
        rect(20, 790, 1240, 280, dark)
        text(44, 828, highs_title, 24, weight=700)
        text(1236, 828, "first game listed; (+n) more games at the same high", 15, muted, anchor="end")
        line(44, 847, 1236, 847)
        for i, (label, value, game) in enumerate(highs[:9]):
            cx, cy = 44 + (i % 3) * 400, 898 + (i // 3) * 68         # three columns of three
            text(cx + 52, cy, value, 32, weight=700, anchor="end")
            text(cx + 66, cy - 13, label.upper(), 14, muted, 700)
            text(cx + 66, cy + 9, game, 16, white)
        footer = 1091
    text(32, footer, "NBA regular season and playoffs are separate records. N/A = no denominator or unavailable data.", 16, "#aeb0b5")
    parts.extend(["</g>", "</svg>"])
    return "\n".join(parts) + "\n"
