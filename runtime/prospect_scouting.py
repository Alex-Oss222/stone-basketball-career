"""Dated qualitative prospect evidence, separate from statistical ability.

The mappings are bounded modeling assumptions, not measured tracking or fitted
NCAA translations. No player name or historical career selects a modifier.
"""
from datetime import date
import math
from pathlib import Path

from .player_stats import CUTOFF, MIN_COHORT_MINUTES, sha256

SCOUTING_PATH = Path("library/2003/league/nba_2003_prospect_scouting.json")
POSITION_PATH = Path("library/2003/league/nba_2003_end_of_season.json")
SCOUTING_MODEL_VERSION = "prospect-scouting-2003.1"
POSITIONS = ("PG", "SG", "SF", "PF", "C")
TRAIT_VALUES = {
    "paint_pressure": ("neutral", "plus"),
    "contact_finishing": ("neutral", "plus"),
    "secondary_creation": ("neutral", "plus"),
    "pressure_decisions": ("neutral", "concern"),
    "set_perimeter_shooting": ("neutral", "plus"),
    "off_dribble_three": ("neutral", "limited"),
    "midrange_pull_up": ("neutral", "plus"),
    "guard_rebounding": ("neutral", "plus"),
    "transition_push": ("neutral", "plus"),
    "screen_navigation": ("neutral", "concern"),
    "help_discipline": ("neutral", "concern"),
    "weak_side_event_defense": ("neutral", "plus"),
}
STYLE_ZONES = ("distance_0_3", "distance_3_10", "distance_10_16", "distance_16_three",
               "corner_three", "arc_three")
PAINT_FTR_FACTOR = 1.15
PRESSURE_SENSITIVITY = 1.5
REBOUND_TRANSITION_FACTOR = 1.25
PAINT_WEIGHTS = {"distance_0_3": 1.30, "distance_3_10": 1.10}
PULL_UP_WEIGHTS = {"distance_10_16": 1.10, "distance_16_three": 1.05}


def validate_scouting(data, prospects, root=None):
    """Fail closed on unsupported, untraceable or post-draft evidence."""
    if (not isinstance(data, dict) or set(data) != {"schema_version", "model_version", "as_of", "players"}
            or type(data["schema_version"]) is not int or data["schema_version"] != 1
            or data["model_version"] != SCOUTING_MODEL_VERSION):
        raise ValueError("unsupported prospect scouting schema or model")
    cutoff = min(date.fromisoformat(CUTOFF), date.fromisoformat(prospects["as_of"]))
    as_of = date.fromisoformat(data["as_of"])
    if as_of > cutoff:
        raise ValueError("prospect scouting contains future evidence")
    known = {p["bbr_id"] for p in prospects["records"]}
    if not isinstance(data["players"], dict) or set(data["players"]) - known:
        raise ValueError("scouting requires a matching pre-draft statistical record")
    for pid, entry in data["players"].items():
        if (not isinstance(entry, dict) or set(entry) != {
                "as_of", "source_file", "source_sha256", "position", "traits"}
                or entry["position"] not in POSITIONS):
            raise ValueError(f"{pid}: invalid scouting record or position")
        if date.fromisoformat(entry["as_of"]) > as_of:
            raise ValueError(f"{pid}: future scouting record")
        source = Path(entry["source_file"])
        if source.is_absolute() or ".." in source.parts or source.suffix != ".md":
            raise ValueError(f"{pid}: scouting source must be a repository Markdown file")
        digest = entry["source_sha256"]
        if (not isinstance(digest, str) or len(digest) != 64
                or any(c not in "0123456789abcdef" for c in digest)):
            raise ValueError(f"{pid}: invalid scouting source hash")
        source_text = None
        if root is not None:
            path = Path(root) / source
            if sha256(path) != digest:
                raise ValueError(f"{pid}: scouting source changed; review its traits before rebuilding")
            source_text = path.read_text(encoding="utf-8")
        if not isinstance(entry["traits"], dict):
            raise ValueError(f"{pid}: scouting traits must be an object")
        for trait, evidence in entry["traits"].items():
            if trait not in TRAIT_VALUES or not isinstance(evidence, dict) or set(evidence) != {"value", "as_of", "sections"}:
                raise ValueError(f"{pid}: unsupported scouting trait {trait}")
            if evidence["value"] not in TRAIT_VALUES[trait]:
                raise ValueError(f"{pid}: unsupported {trait} classification")
            if date.fromisoformat(evidence["as_of"]) > date.fromisoformat(entry["as_of"]):
                raise ValueError(f"{pid}: future {trait} evidence")
            sections = evidence["sections"]
            if (not isinstance(sections, list) or not sections
                    or any(not isinstance(s, str) or not s.strip() for s in sections)):
                raise ValueError(f"{pid}: {trait} needs source sections")
            if source_text is not None and any(f"## {s}\n" not in source_text for s in sections):
                raise ValueError(f"{pid}: {trait} source section not found")


def trait_value(entry, trait):
    return (entry or {}).get("traits", {}).get(trait, {}).get("value", "neutral")


def style_for(entry):
    """Evidence-only traits stay in the source until the engine can express them."""
    if not entry:
        return {}
    style = {}
    if trait_value(entry, "pressure_decisions") == "concern":
        style["pressure_turnover_sensitivity"] = PRESSURE_SENSITIVITY
    if trait_value(entry, "transition_push") == "plus":
        style["rebound_transition_multiplier"] = REBOUND_TRANSITION_FACTOR
    weights = {zone: 1.0 for zone in STYLE_ZONES}
    for trait, modifiers in (("paint_pressure", PAINT_WEIGHTS), ("midrange_pull_up", PULL_UP_WEIGHTS)):
        if trait_value(entry, trait) == "plus":
            for zone, multiplier in modifiers.items():
                weights[zone] *= multiplier
    if any(value != 1 for value in weights.values()):
        style["spatial_weights"] = weights
    return style


def style_errors(style):
    if not isinstance(style, dict) or set(style) - {
            "pressure_turnover_sensitivity", "rebound_transition_multiplier", "spatial_weights"}:
        return ["unsupported player style"]
    errors = []
    for key in ("pressure_turnover_sensitivity", "rebound_transition_multiplier"):
        number = style.get(key, 1.0)
        if type(number) not in (int, float) or not math.isfinite(number) or not 1 <= number <= 2:
            errors.append(f"invalid {key}")
    if "spatial_weights" in style:
        weights = style["spatial_weights"]
        if (not isinstance(weights, dict) or set(weights) != set(STYLE_ZONES)
                or any(type(w) not in (int, float) or not math.isfinite(w) or not .5 <= w <= 2
                       for w in weights.values())):
            errors.append("spatial weights require six finite multipliers between 0.5 and 2")
    return errors


def position_rebound_priors(stats, roster):
    """Pooled ORB / total rebounds for dated NBA position cohorts, once per ID.

    These are split priors only, not invented individual college ORB/DRB data.
    """
    if (date.fromisoformat(stats["as_of_date"]) > date.fromisoformat(CUTOFF)
            or roster["season"] != 2003
            or roster["as_of"] != "end of 2002-03 season (each club's final game)"):
        raise ValueError("rebound prior contains future evidence")
    positions = {}
    for club in roster["clubs"].values():
        for player in club["players"]:
            pid, position = player.get("bbr_id"), player["position"]
            if pid and position in POSITIONS:
                positions.setdefault(pid, set()).add(position)
    totals = {pos: [0, 0, 0] for pos in POSITIONS}
    for record in stats["records"]:
        t = record["totals"]
        candidates = positions.get(record["bbr_id"], set())
        if len(candidates) != 1 or t["minutes"] < MIN_COHORT_MINUTES:
            continue
        if record["season_end_year"] != 2003:
            raise ValueError("rebound prior requires the completed 2002-03 NBA season")
        row = totals[next(iter(candidates))]
        row[0] += t["offensive_rebounds"]
        row[1] += t["defensive_rebounds"]
        row[2] += 1
    return {pos: {"offensive_share": orb / (orb + drb), "players": count,
                  "offensive_rebounds": orb, "defensive_rebounds": drb}
            for pos, (orb, drb, count) in totals.items() if orb + drb > 0}
