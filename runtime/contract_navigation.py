"""Link existing personnel and league records to dated contract projections.

Only presentation text changes here. Identity, salary, offer and transaction
records remain owned by their existing canonical workflows.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re

START = "<!-- contract-navigation:start -->"
END = "<!-- contract-navigation:end -->"


def plain_player_name(value: str) -> str:
    """Read a table's identity label whether its cell is linked or plain text."""
    value = value.strip()
    match = re.fullmatch(r"\[([^\]\n]+)\]\([^\n]+\)", value)
    return match.group(1) if match else value


def contract_page(player: Path, registry_id: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", registry_id):
        raise ValueError(f"Invalid contract navigation registry ID: {registry_id!r}")
    return player / "Contracts" / "players" / f"{registry_id}.html"


def relative_link(page: Path, target: Path, label: str, section: str = "") -> str:
    path = Path(os.path.relpath(target, page.parent)).as_posix()
    return f"[{label}]({path}{'#' + section if section else ''})"


def contract_player_link(page: Path, player: Path, registry_entry: dict) -> str:
    """Return a stable link; limited legacy formatter fixtures may have no ID."""
    if not registry_entry.get("registry_id"):
        return registry_entry["name"]
    target = contract_page(player, registry_entry["registry_id"])
    return relative_link(page, target, registry_entry["name"], "contract")


def league_player_links(text: str, page: Path, player: Path, registry: dict) -> str:
    """Link only recognized name cells, retaining every statistic byte-for-byte."""
    names = {entry["name"]: entry for entry in registry["players"]}

    def replace(match):
        prefix, cell, suffix = match.groups()
        name = plain_player_name(cell)
        if name not in names:
            return match.group(0)
        return prefix + contract_player_link(page, player, names[name]) + suffix

    return re.sub(r"^(\|[ \t]*)([^|\n]*?)([ \t]*\|[^\n]*)$", replace, text, flags=re.M)


def navigation_block(text: str, body: str, *, after: str) -> str:
    block = f"{START}\n{body}\n{END}"
    if START in text or END in text:
        pattern = re.escape(START) + r".*?" + re.escape(END)
        if text.count(START) != 1 or text.count(END) != 1 or not re.search(pattern, text, re.S):
            raise ValueError("Malformed contract navigation block")
        return re.sub(pattern, lambda _: block, text, count=1, flags=re.S)
    text, count = re.subn(after, lambda m: m.group(0) + "\n\n" + block, text, count=1, flags=re.M)
    if count != 1:
        raise ValueError("Contract navigation has no recognized insertion point")
    return text


def build_contract_navigation(root: Path, player: Path) -> dict[Path, str]:
    """Build link updates for every known personnel card and league period.

    The contract catalog supplies one page per registry ID, including unsigned
    players and records with incomplete terms. Historical personnel cards keep
    their original assessments; their links explicitly open the current record.
    """
    player = Path(player)
    registry_path = player / "Stats_and_Awards/League/player_registry.json"
    if not registry_path.is_file():
        return {}
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    names = {entry["name"]: entry for entry in registry["players"]}
    if len(names) != len(registry["players"]):
        raise ValueError("Contract navigation requires unambiguous registry names")
    # The league tracking pool omits a few members of Miami's control register.
    # Their personnel cards still need the same catalog destination.
    for roster_path in sorted(player.glob("*/00_Team/Team/Roster/roster.json")):
        roster = json.loads(roster_path.read_text(encoding="utf-8"))
        for entry in roster["players"]:
            if entry["name"] not in names:
                identity = entry.get("bbr_id") or entry.get("registry_id") or entry.get("id")
                if identity:
                    names[entry["name"]] = {"name": entry["name"], "registry_id": identity}
    for entry in names.values():
        contract_page(player, entry["registry_id"])
    outputs = {}
    for page in sorted(player.glob("*/00_Team/Team/Player_Cards/*.md")):
        text = page.read_text(encoding="utf-8")
        heading = re.search(r"^# (.*?) \| .* Player Profile$", text, re.M)
        if not heading or heading.group(1) not in names:
            continue
        target = contract_page(player, names[heading.group(1)]["registry_id"])
        body = (relative_link(page, target, "Current contract", "contract") + " · " +
                relative_link(page, target, "Contract history", "contract-history") + " · " +
                relative_link(page, player / "Contracts/index.html", "All tracked players") +
                "\n\nContract pages follow the current career date; this personnel assessment retains its stated date.")
        outputs[page] = navigation_block(text, body, after=r"^\*\*Contract/control:\*\*[^\n]*$")
    league = registry_path.parent
    for page in sorted(league.rglob("League_Stats.md")):
        outputs[page] = league_player_links(page.read_text(encoding="utf-8"), page, player, registry)
    index_pages = [league / "README.md", *sorted(player.glob("*/00_Team/Team/Player_Cards/README.md"))]
    for page in index_pages:
        if page.is_file():
            body = relative_link(page, player / "Contracts/index.html", "Current contracts and contract history for every tracked player")
            outputs[page] = navigation_block(page.read_text(encoding="utf-8"), body, after=r"^# [^\n]+$")
    return outputs
