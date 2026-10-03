"""Reference-style player headers, earned-honor badges and complete per-game rows."""
from __future__ import annotations

import calendar
from datetime import date
from html import escape
import os
from pathlib import Path
import re
import textwrap

from .award_records import badge_labels, honors_in_scope
from .career_stats import aggregate, identity_at, NATIONAL_PATHS, NATIONAL_TYPES, PHASES

RED = "#a71930"
BLACK = "#141517"
CARD = "#222326"
GOLD = "#efbf58"


def svg_text(x, y, value, size=20, color="#ffffff", weight=400, anchor="start"):
    return f'<text x="{x}" y="{y}" font-family="sans-serif" font-size="{size}" fill="{color}" font-weight="{weight}" text-anchor="{anchor}">{escape(str(value))}</text>'


def rect(x, y, w, h, fill, radius=16):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}"/>'


def svg_start(title, height, desc=""):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="{height}" viewBox="0 0 1280 {height}" role="img" aria-labelledby="title desc">',
            f'<title id="title">{escape(title)}</title><desc id="desc">{escape(desc)}</desc>', rect(0, 0, 1280, height, BLACK, 24)]


def badges(parts, labels, x, y, width, columns):
    if not labels:
        parts.append(rect(x, y, width, 62, "#34363a", 10))
        parts.append(svg_text(x + width / 2, y + 37, "No earned professional honors", 18, "#d0d1d4", anchor="middle"))
        return
    gap = 10
    cell_width = (width - (columns - 1) * gap) / columns
    for i, label in enumerate(labels):
        cx = x + (i % columns) * (cell_width + gap)
        cy = y + (i // columns) * 72
        parts.append(rect(cx, cy, cell_width, 62, GOLD, 9))
        lines = textwrap.wrap(label, width=max(15, int(cell_width / 9)))
        # A long official award name grows its label font down to fit without truncation.
        size = min(18, 48 / max(1, len(lines)))
        for j, row in enumerate(lines):
            baseline = cy + 31 - (len(lines) - 1) * (size + 2) / 2 + j * (size + 2) + size / 3
            parts.append(svg_text(cx + cell_width / 2, baseline, row, size, "#221709", 700, "middle"))


def honors_banner(awards, as_of):
    labels = badge_labels(awards, as_of)
    rows = max(1, (len(labels) + 3) // 4)
    height = 82 + rows * 72
    parts = svg_start("Earned professional honors", height, f"Confirmed career honors through {as_of}.")
    parts += [rect(20, 18, 1240, 42, RED, 10), svg_text(40, 46, "EARNED PROFESSIONAL HONORS", 19, weight=700),
              svg_text(1240, 46, f"Through {as_of}", 17, "#f4ccd3", anchor="end")]
    badges(parts, labels, 20, 76, 1240, 4)
    return "\n".join([*parts, "</svg>"]) + "\n"


def personal_header(identity, as_of, awards):
    p = identity_at(identity, as_of)
    labels = badge_labels(awards, as_of)
    badge_rows = max(1, (len(labels) + 1) // 2)
    body_height = max(250, 76 + badge_rows * 72)
    height = 142 + body_height + 20
    parts = svg_start(f'{p.get("display_name", p["full_name"])} personal information and honors', height,
                      f"Simulation identity and earned honors through {as_of}; the text equivalent follows this image.")
    parts += [rect(20, 20, 1240, 106, RED),
              svg_text(46, 66, p.get("display_name", p["full_name"]), 36, weight=700),
              svg_text(46, 101, p["full_name"] + (" · ILLUSTRATIVE TEMPLATE ONLY" if p.get("record_type") == "illustrative" else ""), 20, "#f5d0d6"),
              svg_text(1234, 60, p["team"] + " · " + p["league"], 22, weight=600, anchor="end"),
              svg_text(1234, 99, "Identity / honors through " + as_of, 18, "#f5d0d6", anchor="end"),
              rect(20, 142, 780, body_height, CARD), rect(816, 142, 444, body_height, CARD)]
    fields = [
        ("POSITION / SHOOTS", " / ".join(p["positions"]) + " · " + p["shooting_hand"]),
        ("HEIGHT / WEIGHT", p["height_in_shoes"] + " (in shoes) · " + str(p["weight_lb"]) + " lb"),
        ("BIRTH / AGE", date.fromisoformat(p["date_of_birth"]).strftime("%b %d, %Y") + f' · Age {p["age"]}'),
        ("PRIOR PROGRAM", p["prior_program"]),
        ("JERSEY / STATUS", (f'#{p["jersey"]}' if p["jersey"] is not None else "Unassigned") + " · " + p["roster_status"]),
        ("NBA ENTRY", p["entry"]),
    ]
    for i, (label, value) in enumerate(fields):
        y = 177 + i * 37
        parts.append(svg_text(40, y, label, 13, "#bdc0c5", 700))
        parts.append(svg_text(200, y, value, 17 if i == 5 else 18, weight=500))
    parts.append(svg_text(838, 177, "EARNED CAREER HONORS", 17, weight=700))
    badges(parts, labels, 838, 196, 400, 2)
    return "\n".join([*parts, "</svg>"]) + "\n"


def per_game_strip():
    parts = svg_start("Per-game statistics", 64, "Complete player box-score columns; averages per appearance.")
    parts += [rect(0, 0, 230, 64, RED, 12), svg_text(25, 41, "PER GAME", 27, weight=700),
              svg_text(254, 39, "Production · Shooting · Rebounding · Playmaking · Defense · Honors", 20, "#d0d1d4")]
    return "\n".join([*parts, "</svg>"]) + "\n"


def link(page, target, label):
    return f'[{label}]({Path(os.path.relpath(target, page.parent)).as_posix()})'


def markdown_table(headers, rows):
    def safe(value):
        return str(value).replace("|", "&#124;").replace("\n", " ")
    return "| " + " | ".join(headers) + " |\n| " + " | ".join("---" for _ in headers) + " |\n" + "".join(
        "| " + " | ".join(safe(v) for v in row) + " |\n" for row in rows) + "\n"


def scope_for(path, records, clock, *, heading="", explicit=None):
    """Describe a row's calendar scope, including empty future containers."""
    parts = path.parts
    season = next((part for part in parts if re.fullmatch(r"\d{4}-\d{2}", part)), None)
    competition = next((PHASES[p] for p in parts if p in PHASES), None)
    if "Stats_and_Awards" in parts and season:
        competition = "regular"
    if "National_Team" in parts:
        index = parts.index("National_Team")
        tail = parts[index + 1:]
        if len(tail) >= 3:
            competition = NATIONAL_PATHS.get((tail[0], tail[2]))
            season = tail[1]
    kinds = {r["competition"] for r in records}
    if len(kinds) == 1:
        competition = next(iter(kinds))
    if competition is None:
        competition = "playoff" if "playoff" in heading.lower() else ("regular" if "regular" in heading.lower() else None)
    start = end = None
    if season and re.fullmatch(r"\d{4}-\d{2}", season):
        start, end = f"{season[:4]}-06-01", f"{int(season[:4])+1}-06-30"
        month = next((part for part in parts if re.fullmatch(r"\d{2}_[A-Za-z]+", part) and part[:2] in {"01", "02", "03", "04", "10", "11", "12"}), None)
        if month:
            num = int(month[:2])
            year = int(season[:4]) + (num < 7)
            last = calendar.monthrange(year, num)[1]
            start, end = f"{year}-{num:02d}-01", f"{year}-{num:02d}-{last:02d}"
            week = next((int(part[5:]) for part in parts if re.fullmatch(r"Week_[1-4]", part)), None)
            if week:
                start = f"{year}-{num:02d}-{1+(week-1)*7:02d}"
                end = f"{year}-{num:02d}-{min(week*7,last) if week<4 else last:02d}"
    if re.fullmatch(r"Game_\d+\.md", path.name) and len(records) == 1 and records[0]["date"]:
        start = end = records[0]["date"]
    scope = dict(season=season, competition=competition, start=start, end=end)
    if re.fullmatch(r"Game_\d+\.md", path.name):
        scope["honors"] = False
    is_round = "08_Playoffs" in parts and parts.index("08_Playoffs") + 2 < len(parts)
    if "National_Team" in parts:
        is_round = is_round or len(parts[parts.index("National_Team") + 1:]) > 4
    if is_round:
        dates = [r["date"] for r in records if r["date"] and r["status"] == "played"]
        if dates:
            scope.update(start=min(dates), end=max(dates))
        else:
            scope["honors"] = False
    scope.update(explicit or {})
    scope["identity_date"] = min(clock, scope.get("identity_date") or scope.get("end") or clock)
    return scope


PER_GAME_COLUMNS = ["Scope", "Age", "Team", "Lg", "Pos", "G", "GS", "MP", "FG", "FGA", "FG%", "3P", "3PA", "3P%",
                    "2P", "2PA", "2P%", "eFG%", "FT", "FTA", "FT%", "ORB", "DRB", "TRB", "AST", "STL", "BLK", "TOV", "PF", "PTS", "TS% (est.)", "Awards"]


class ReportStyle:
    def __init__(self, identity, awards, clock, outputs, asset_dir, player=None, *, cards_root=None,
                 card_periods=(), default_card_period=None, detailed=False):
        self.identity, self.awards, self.clock = identity, awards, clock
        self.outputs, self.asset_dir, self.player = outputs, asset_dir, player
        self.cards_root, self.card_periods = cards_root, set(card_periods)
        self.default_card_period, self.detailed = default_card_period, detailed

    def award_terms(self, text):
        if self.cards_root is None:
            return text
        return text.replace("Awards and honors", "Awards").replace("HONORS", "AWARDS").replace("Honors", "Awards").replace("honors", "awards").replace("| Honor |", "| Award |")

    def cards_navigation(self, page, groups=(), heading="", cutoff=None):
        if self.cards_root is None:
            return ""
        from .player_cards import period_for_scope
        records = groups[0][1] if groups else []
        explicit = groups[0][3] if groups and len(groups[0]) > 3 else None
        scope = scope_for(page, records, cutoff or self.clock, heading=heading, explicit=explicit)
        pid = period_for_scope(scope, records, page, self.player)
        if pid not in self.card_periods:
            pid = self.default_card_period
        shooting_image = "!" + link(page, self.cards_root / "assets/shooting_link.svg", "Shooting")
        awards_image = "!" + link(page, self.cards_root / "assets/awards_link.svg", "Awards")
        shooting_path = Path(os.path.relpath(self.cards_root / "Shooting.md", page.parent)).as_posix()
        awards_path = Path(os.path.relpath(self.cards_root / "Awards.md", page.parent)).as_posix()
        html = Path(os.path.relpath(self.cards_root / "player_cards.html", page.parent)).as_posix()
        return (f"[{shooting_image}]({html}?period={pid}#shooting) [{awards_image}]({html}#awards)\n\n"
                f"[Shooting detail]({shooting_path}) · [Annual award record]({awards_path})\n\n")

    def header(self, page, cutoff):
        asset = self.asset_dir / f"personal_{cutoff}.svg"
        self.outputs[asset] = self.award_terms(personal_header(self.identity, cutoff, self.awards))
        return self.award_terms("!" + link(page, asset, f"Player personal information and earned career honors through {cutoff}") + "\n\n")

    def banner(self, page, cutoff):
        asset = self.asset_dir / f"awards_{cutoff}.svg"
        self.outputs[asset] = self.award_terms(honors_banner(self.awards, cutoff))
        return self.award_terms("!" + link(page, asset, f"Earned professional honors through {cutoff}") + "\n\n")

    def award_text(self, page, awards):
        if not awards:
            return "—"
        labels = []
        for a in awards:
            if self.player:
                source, _, anchor = a["source"].partition("#")
                url = Path(os.path.relpath(self.player / source, page.parent)).as_posix() + ("#" + anchor if anchor else "")
                labels.append(f'[{a["short_name"]}]({url})')
            else:
                labels.append(a["short_name"] + " (example)")
        return ", ".join(labels)

    def row(self, page, group, heading, cutoff=None):
        label, records, target, *extra = group
        scope = scope_for(target or page, records, cutoff or self.clock, heading=heading, explicit=extra[0] if extra else None)
        p = identity_at(self.identity, scope["identity_date"])
        a = aggregate(records)
        national = scope["competition"] in NATIONAL_TYPES
        teams = sorted({r["team"] for r in records if r["status"] == "played"})
        team = " / ".join(teams) if teams else ("Not selected" if national else p["team"])
        pos = sorted({" / ".join(identity_at(self.identity, r["date"])["positions"]) for r in records if r["status"] == "played"})
        awards = [] if heading in {"Splits", "Individual game boxes"} or not scope.get("honors", True) else honors_in_scope(
            self.awards, known_on=self.clock, **{k: scope[k] for k in ("season", "competition", "start", "end")})
        def n(value, places=1):
            return "N/A" if value is None else f"{value:.{places}f}"
        def shooting(key):
            value = a["rates"][key]
            return "N/A" if value is None else f"{value:.3f}".removeprefix("0")
        pg = a["pg"]
        return [link(page, target, label) if target else label, p["age"], team, "FIBA" if national else p["league"],
                "; ".join(pos) if pos else " / ".join(p["positions"]), n(a["gp"], 0), n(a["gs"], 0), n(pg["minutes"]),
                n(pg["fgm"]), n(pg["fga"]), shooting("fg_pct"), n(pg["tpm"]), n(pg["tpa"]), shooting("three_pct"),
                n(pg["two_pm"]), n(pg["two_pa"]), shooting("two_pct"), shooting("efg_pct"), n(pg["ftm"]), n(pg["fta"]), shooting("ft_pct"),
                *(n(pg[k]) for k in ("orb", "drb", "reb", "ast", "stl", "blk", "tov", "pf", "pts")), shooting("ts_pct"), self.award_text(page, awards)]

    def per_game(self, page, groups, heading="Per game", *, decorate=True, as_of=None):
        asset = self.asset_dir / "per_game.svg"
        self.outputs[asset] = per_game_strip() if self.cards_root is None else self.award_terms(
            per_game_strip().replace("Production · Shooting · Rebounding · Playmaking · Defense · Honors", "Complete recorded box-score statistics"))
        text = f"### {heading}\n\n"
        if decorate:
            text += self.cards_navigation(page, groups, heading, as_of) if self.cards_root else "!" + link(page, asset, "Per-game player statistics") + "\n\n"
        text += markdown_table(PER_GAME_COLUMNS, [self.row(page, group, heading, as_of) for group in groups])
        text += "G and GS are counts; MP and counting statistics are **per appearance**. Shooting uses **.500 = 50.0%**. Age is at the row's cutoff. Scroll horizontally for every column.\n\n"
        if self.awards:
            text += f"Awards are confirmed through {self.clock}, filed by the honor's period-end date; the banner shows career honors known at the page's identity cutoff.\n\n"
        return self.award_terms(text)
