"""Dated, sourced professional honors for player banners and period rows."""
from __future__ import annotations

from collections import Counter
from datetime import date
import json
from pathlib import Path

from .career_stats import NATIONAL_TYPES, PHASES
from .season_rules import statistics_bucket


def load_awards(player: Path, as_of: str) -> list[dict]:
    path = player / "awards.json"
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or not isinstance(data.get("awards"), list):
        raise ValueError("awards.json: expected schema version 1 and an awards list")
    seen, events = set(), set()
    for award in data["awards"]:
        for key in ("id", "name", "short_name", "competition", "season", "awarded_on", "period_start", "period_end", "source"):
            if not isinstance(award.get(key), str) or not award[key].strip():
                raise ValueError(f"award requires {key}")
        if award.get("status") != "earned":
            raise ValueError("only earned honors belong in the player award register; nominations stay in voting records")
        if award["competition"] not in set(PHASES.values()) | NATIONAL_TYPES | {"career"}:
            raise ValueError("award has an unsupported competition")
        start, end, announced = (date.fromisoformat(award[k]) for k in ("period_start", "period_end", "awarded_on"))
        if start > end or end > announced or announced > date.fromisoformat(as_of):
            raise ValueError("award period/announcement dates are invalid or after the career cutoff")
        if award["competition"] in PHASES.values():
            statistics_bucket(award["competition"], award["season"])
        source = (player / award["source"].split("#", 1)[0]).resolve()
        if not source.is_relative_to(player.resolve()) or not source.is_file():
            raise ValueError("award source must be an existing decision record inside the player career")
        event = (award["name"], award["competition"], award["season"], award["period_start"], award["period_end"])
        if award["id"] in seen or event in events:
            raise ValueError("duplicate player honor")
        seen.add(award["id"])
        events.add(event)
    return sorted(data["awards"], key=lambda a: (a["awarded_on"], a["id"]))


def honors_in_scope(awards, *, known_on, competition=None, season=None, start=None, end=None):
    """File an honor by period end, but never show it before its announcement."""
    return [a for a in awards if a["awarded_on"] <= known_on
            and (competition is None or a["competition"] == competition)
            and (season is None or a["season"] == season)
            and (start is None or a["period_end"] >= start)
            and (end is None or a["period_end"] <= end)]


def badge_labels(awards, as_of):
    counts = Counter(a["name"] for a in awards if a["awarded_on"] <= as_of)
    return [f"{n}× {name}" if n > 1 else name for name, n in counts.items()]
