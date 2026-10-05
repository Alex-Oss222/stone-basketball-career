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
    """File an honor by period end, but never show it before its announcement, nor before the career recorded it
    (`recorded_on`, set only when an honor was decided after its date: the 2004 All-Star selections)."""
    return [a for a in awards if max(a["awarded_on"], a.get("recorded_on") or "") <= known_on
            and (competition is None or a["competition"] == competition)
            and (season is None or a["season"] == season)
            and (start is None or a["period_end"] >= start)
            and (end is None or a["period_end"] <= end)]


def badge_labels(awards, as_of):
    counts = Counter(a["name"] for a in awards if a["awarded_on"] <= as_of)
    return [f"{n}× {name}" if n > 1 else name for name, n in counts.items()]


# -- the era-gated catalogue (library/2003/league/nba_awards_catalog.json, docs/awards_catalog.md) ------------
ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "library/2003/league/nba_awards_catalog.json"
SCOPES = ("season", "monthly", "weekly", "playoff", "all-star", "cup")
FACT_STATUSES = ("sourced", "derived", "unverified")


def season_start(season: str) -> int:
    """'2003-04' -> 2003; the catalogue compares seasons by their starting year."""
    if not isinstance(season, str) or len(season) != 7 or season[4] != "-" or not season[:4].isdigit() \
            or not season[5:].isdigit() or int(season[5:]) != (int(season[:4]) + 1) % 100:
        raise ValueError(f"season must look like 2003-04, got {season!r}")
    return int(season[:4])


def load_catalog(path: Path | None = None) -> dict:
    data = json.loads(Path(path or CATALOG_PATH).read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or not isinstance(data.get("awards"), list) or not isinstance(data.get("rules"), list):
        raise ValueError("awards catalogue: expected schema version 1 with awards and rules lists")
    return data


def _in_force(entry: dict, start: int) -> bool:
    first = entry["first_season"]
    first = first["value"] if isinstance(first, dict) else first
    last = entry.get("last_season")
    last = last["value"] if isinstance(last, dict) else last
    return season_start(first) <= start and (last is None or start <= season_start(last))


def awards_in_force(season: str, catalog: dict | None = None) -> list[dict]:
    """Awards that may be decided for `season`: first season on or before it, not yet discontinued.

    Later rules never apply retroactively; `rules_in_force` gives the ones that do. Entries come back in
    catalogue order and unchanged, so a caller still reads each fact's `status` before using it in a vote.
    """
    start = season_start(season)
    catalog = catalog or load_catalog()
    return [a for a in catalog["awards"] if _in_force(a, start)]


def rules_in_force(season: str, catalog: dict | None = None) -> list[dict]:
    """Catalogue rules whose first season is on or before `season` (the 65-game rule is not one in 2003-04)."""
    start = season_start(season)
    catalog = catalog or load_catalog()
    return [r for r in catalog["rules"] if _in_force(r, start)]
