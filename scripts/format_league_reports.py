#!/usr/bin/env python3
"""Apply the shared per-game layout while preserving recorded league values.

This is a presentation migration, not a result importer or league simulation.
"""
from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.stat_layout import RED, PER_GAME_COLUMNS, link, markdown_table, rect, scope_for, svg_start, svg_text
from runtime.contract_navigation import contract_player_link, plain_player_name

COLUMNS = ["Player", "Age", "Club / rights", "Lg", *PER_GAME_COLUMNS[4:-1]]
LINK = re.compile(r"^\[([^\]]+)\]\([^)]+\)$")


def player_name(cell):
    """The player's name from a Player cell, whether or not it is already a card link."""
    match = LINK.match(cell.strip())
    return match.group(1) if match else cell.strip()


def card_link(page, registry_player, league_dir):
    """Markdown link to the player's league card, relative to the page; plain text without a registry id."""
    card_id = registry_player.get("registry_id")
    if not card_id:
        return registry_player["name"]
    return link(page, league_dir / "Players" / f"{card_id}.md", registry_player["name"])
ALIASES = {"MP": "MPG", "PTS": "PPG", "TRB": "RPG", "AST": "APG", "STL": "SPG", "BLK": "BPG", "TOV": "TOV/G"}


def header_svg():
    parts = svg_start("NBA player statistics", 116, "League player statistics, grouped by position, for the dates shown on the page.")
    parts += [rect(20, 20, 284, 76, RED, 12), svg_text(42, 66, "NBA / PER GAME", 26, weight=700),
              svg_text(334, 51, "LEAGUE PLAYER STATISTICS", 24, weight=700),
              svg_text(334, 83, "Identity · Shooting · Rebounding · Playmaking · Defense", 21, "#c5c7cb")]
    return "\n".join([*parts, "</svg>"]) + "\n"


def read_tables(text):
    for block in re.findall(r"(?:^\|.*\|\n)+", text, re.M):
        lines = [line.strip().strip("|").split("|") for line in block.splitlines()]
        cells = [[cell.strip() for cell in line] for line in lines]
        if len(cells) < 2 or cells[0][0] != "Player":
            continue
        if any(len(row) != len(cells[0]) for row in cells[2:]):
            raise ValueError("league table has mismatched columns")
        yield cells[0], [dict(zip(cells[0], row)) for row in cells[2:]]


def ratio(value, *, maximum=1.0):
    if value == "N/A":
        return value
    number = float(value.removesuffix("%"))
    if value.endswith("%"):
        number /= 100
    elif number > maximum:
        raise ValueError(f"league shooting rate needs an explicit percent sign or a 0-{maximum:g} ratio")
    return f"{number:.3f}".removeprefix("0")


def format_page(text, page, registry, as_of, asset, league_dir=None):
    """Rewrite one page's position tables; `league_dir` is the League folder the Players cards live in."""
    cutoff = scope_for(page, [], as_of)["identity_date"]
    league_dir = league_dir or asset.parent.parent
    players = {p["name"]: p for p in registry["players"]}
    def position(match):
        pos, summary, body = match.groups()
        production, shooting = {}, {}
        for headers, rows in read_tables(body):
            target = production if "PPG" in headers or "PTS" in headers else shooting
            for row in rows:
                name = row["Player"] = player_name(row["Player"])
                if name in target:
                    raise ValueError(f"{page}: duplicate {name} row")
                target[name] = row
        expected = {p["name"] for p in registry["players"] if p["position"] == pos}
        if set(production) != expected:
            raise ValueError(f"{page}: {pos} membership differs from the registry")
        if shooting and set(shooting) != expected:
            raise ValueError(f"{page}: {pos} shooting coverage differs from production")
        rows = []
        for name, old in production.items():
            old = {**shooting.get(name, {}), **old}
            p = players[name]
            birth, on = date.fromisoformat(p["birth_date"]), date.fromisoformat(cutoff)
            age = on.year - birth.year - ((on.month, on.day) < (birth.month, birth.day))
            values = {key: old.get(key, old.get(ALIASES.get(key, ""), "N/A")) for key in COLUMNS}
            values.update(Player=card_link(page, p, league_dir), Age=old.get("Age", str(age)), Lg=old.get("Lg", "NBA"), Pos=old.get("Pos", pos))
            # The club/rights cell is an existing dated label, never a new roster decision.
            values["Club / rights"] = old["Club / rights"]
            for key in ("FG%", "3P%", "2P%", "eFG%", "FT%", "TS% (est.)"):
                # Three-point value makes eFG and true shooting exceed 100% in
                # small samples; ordinary make/attempt percentages cannot.
                values[key] = ratio(values[key], maximum=1.5 if key in ("eFG%", "TS% (est.)") else 1.0)
            rows.append([values[key] for key in COLUMNS])
        return f"<details>\n<summary>{pos} ·{summary}</summary>\n\n### {pos}: per game\n\n" + markdown_table(COLUMNS, rows).rstrip() + "\n\n</details>"
    text, count = re.subn(r"<details>\n<summary>(PG|SG|SF|F|PF|C) ·(.*?)</summary>(.*?)</details>", position, text, flags=re.S)
    if count != len(registry["positions"]):
        raise ValueError(f"{page}: expected every position group")
    old_caption = "Open a position to see every tracked player. Production is per appearance; the shooting table keeps GS and percentages separate. Team labels show the source club or draft rights, not a finalized opening-night roster."
    caption = (f"Open a position to see every tracked player. G and GS are counts; MP and counting statistics are per appearance. "
               f"Shooting uses .500 = 50.0%. Scroll horizontally for all columns. Age is recorded at the period's identity cutoff ({cutoff}); "
               "birth dates and identity references are in the linked player registry. Each player name opens his league card. Club / rights is the recorded source label, not proof of an active roster spot. "
               "Unrecorded starts, attempts, splits and fouls stay N/A; they cannot be reconstructed from rounded averages.")
    previous_caption = caption.replace("Each player name opens his league card. ", "")
    for old in (old_caption, previous_caption):
        if old in text:
            text = text.replace(old, caption)
    image = "!" + link(page, asset, "NBA per-game statistics: identity, shooting, rebounding, playmaking and defense") + "\n\n"
    if image not in text:
        text = text.replace("## Players by position\n\n", "## Players by position\n\n" + image)
    return text


def main():
    outputs = {}
    for player in (ROOT / "career").iterdir():
        league = player / "Stats_and_Awards/League"
        if not (league / "player_registry.json").is_file():
            continue
        registry = json.loads((league / "player_registry.json").read_text())
        as_of = max(json.loads(path.read_text())["current_date"] for path in player.glob("*/current_state.json"))
        asset = league / "assets/per_game.svg"
        outputs[asset] = header_svg()
        for page in league.rglob("League_Stats.md"):
            outputs[page] = format_page(page.read_text(), page, registry, as_of, asset, league)
    for page, text in outputs.items():
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(text, encoding="utf-8")
    print(f"Formatted {len(outputs)-1} league period pages. No results, roster decisions or award winners changed.")


if __name__ == "__main__":
    main()
