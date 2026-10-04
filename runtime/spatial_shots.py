"""Prospective NBA shot locations from a dated league distance-band prior.

The prior describes attempt shares and make rates, not individual tracking.
Coordinates within each band are explicit geometric model assumptions. Optional
scouting style weights change conditional geography, never aggregate accuracy.
"""
from datetime import date
import hashlib
import json
import math
from pathlib import Path

from .packets import canonical
from .shot_chart import NBA_GEOMETRY, classify_zone

ROOT = Path(__file__).resolve().parents[1]
SPATIAL_MODEL_VERSION = "spatial-2003.1"
SPATIAL_ZONES = ("distance_0_3", "distance_3_10", "distance_10_16", "distance_16_three", "corner_three", "arc_three")
ZONE_VALUES = {zone: 2 if i < 4 else 3 for i, zone in enumerate(SPATIAL_ZONES)}


def spatial_environment_errors(environment, season=None, game_date=None):
    errors = []
    if not isinstance(environment, dict):
        return ["spatial environment must be an object"]
    if (environment.get("schema_version") != 1 or environment.get("kind") != "league_shot_environment"
            or environment.get("league") != "NBA" or environment.get("model_version") != SPATIAL_MODEL_VERSION):
        errors.append("unsupported spatial environment schema or model")
    if season is not None:
        start = int(season[:4])
        previous = f"{start - 1}-{str(start)[-2:]}"
        if environment.get("season") != previous:
            errors.append("spatial environment must describe the previous season")
    try:
        published = date.fromisoformat(environment["published_after"])
        if game_date is not None and published > date.fromisoformat(game_date):
            errors.append("spatial environment was not available on the game date")
    except (KeyError, TypeError, ValueError):
        errors.append("spatial environment requires a valid publication gate")
    zones = environment.get("zones")
    if (not isinstance(zones, list) or len(zones) != len(SPATIAL_ZONES)
            or any(not isinstance(zone, dict) for zone in zones)
            or any(not isinstance(zone.get("id"), str) for zone in zones)
            or {zone.get("id") for zone in zones} != set(SPATIAL_ZONES)):
        return errors + ["spatial environment requires the six sourced distance bands"]
    for zone in zones:
        if zone.get("shot_value") != ZONE_VALUES[zone["id"]]:
            errors.append(f"{zone['id']}: wrong shot value")
        for key in ("attempt_share_within_value", "fg_pct"):
            number = zone.get(key)
            if (type(number) not in (int, float) or not math.isfinite(number)
                    or not 0 <= number <= 1 or (key == "attempt_share_within_value" and number == 0)):
                errors.append(f"{zone['id']}: invalid {key}")
    if not errors:
        for value in (2, 3):
            total = sum(zone["attempt_share_within_value"] for zone in zones if zone["shot_value"] == value)
            if not math.isclose(total, 1, abs_tol=1e-8):
                errors.append(f"{value}-point spatial attempt shares must sum to one")
    return errors


def load_spatial_environment(season, game_date=None, root=ROOT):
    """Load only this season's completed prior-season NBA spatial environment."""
    start = int(season[:4])
    path = Path(root) / "library" / str(start) / "league" / f"nba_{start - 1}_{str(start)[-2:]}_shot_environment.json"
    try:
        environment = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"no verified prior-season shot environment for {season}") from exc
    errors = spatial_environment_errors(environment, season, game_date)
    if errors:
        raise ValueError("; ".join(errors))
    return environment


def tracking_metadata(environment):
    return {"schema_version": 1, "model_version": SPATIAL_MODEL_VERSION,
            "coordinate_system": "nba_feet_from_basket", "source_type": "engine_generated",
            "prior_sha256": hashlib.sha256(canonical(environment)).hexdigest(), "coverage": "complete"}


def classify_spatial_zone(x, y):
    """Source distance bands, separate from the chart's custom paint regions."""
    try:
        display_zone = classify_zone(x, y)
    except ValueError:
        return None
    if display_zone is None:
        return None
    if display_zone == "three":
        return "corner_three" if y <= NBA_GEOMETRY["three_point_join_y"] else "arc_three"
    radius = math.hypot(x, y)
    for limit, zone in ((3, "distance_0_3"), (10, "distance_3_10"), (16, "distance_10_16")):
        if radius < limit:
            return zone
    return "distance_16_three"


def zone_probabilities(environment, value, target, spatial_weights=None, zone_accuracy=None):
    """Zone make probabilities whose attempt-weighted mean is exactly target.

    A common shift preserves sourced efficiency differences. At the bounds,
    water filling reallocates the clipped mass among remaining zones, so even
    extreme shooting grades cannot silently increase or decrease mean scoring.
    """
    if value not in (2, 3) or type(target) not in (int, float) or not math.isfinite(target) or not 0 <= target <= 1:
        raise ValueError("shot value and target make probability are invalid")
    rows = [zone for zone in environment["zones"] if zone["shot_value"] == value]
    if spatial_weights is not None:
        from .prospect_scouting import style_errors
        errors = style_errors({"spatial_weights": spatial_weights})
        if errors:
            raise ValueError("; ".join(errors))
        weights = [row["attempt_share_within_value"] * spatial_weights[row["id"]] for row in rows]
        total = sum(weights)
        rows = [dict(row, attempt_share_within_value=weight / total) for row, weight in zip(rows, weights)]
    if zone_accuracy is not None:
        # A player's relative accuracy by zone (an elite catch-and-shoot corner, say): added before the common
        # shift, so his mean make probability for the shot value is still exactly the target.
        from .prospect_scouting import style_errors
        errors = style_errors({"zone_accuracy": zone_accuracy})
        if errors:
            raise ValueError("; ".join(errors))
        rows = [dict(row, fg_pct=row["fg_pct"] + zone_accuracy.get(row["id"], 0.0)) for row in rows]
    active = list(range(len(rows)))
    probabilities = [None] * len(rows)
    remaining = target
    while active:
        weight = sum(rows[i]["attempt_share_within_value"] for i in active)
        mean = sum(rows[i]["attempt_share_within_value"] * rows[i]["fg_pct"] for i in active)
        shift = (remaining - mean) / weight
        clipped = []
        for i in active:
            probability = rows[i]["fg_pct"] + shift
            if probability < 0 or probability > 1:
                probabilities[i] = min(1.0, max(0.0, probability))
                remaining -= rows[i]["attempt_share_within_value"] * probabilities[i]
                clipped.append(i)
        if not clipped:
            for i in active:
                probabilities[i] = min(1.0, max(0.0, rows[i]["fg_pct"] + shift))
            break
        active = [i for i in active if i not in clipped]
    return [(row["id"], row["attempt_share_within_value"], probability)
            for row, probability in zip(rows, probabilities)]


def draw_location(rng, zone):
    """Choose a legal modeled point within a band, before drawing its outcome.

    Two-point distances are area-uniform, with a uniform angle in front of the
    basket; corners use uniform legal strips. Arc threes extend to 28 feet.
    These within-band distributions are assumptions, not measured tracking.
    """
    bounds = {"distance_0_3": (0, 3), "distance_3_10": (3, 10),
              "distance_10_16": (10, 16), "distance_16_three": (16, 23.75), "arc_three": (23.75, 28)}
    if zone not in SPATIAL_ZONES:
        raise ValueError("unsupported spatial zone")
    for _ in range(1000):
        if zone == "corner_three":
            x = rng.uniform(22.0001, 24.9999) * (-1 if rng.random() < .5 else 1)
            y = rng.uniform(NBA_GEOMETRY["baseline_y"] + .0001, NBA_GEOMETRY["three_point_join_y"] - .0001)
        else:
            low, high = bounds[zone]
            radius = math.sqrt(rng.uniform(low * low, high * high))
            angle = rng.uniform(-math.pi / 2, math.pi / 2)
            x, y = radius * math.sin(angle), radius * math.cos(angle)
        x, y = round(x, 6), round(y, 6)
        if classify_spatial_zone(x, y) == zone:
            return x, y
    raise RuntimeError("could not sample a point inside its spatial zone")


def draw_spatial_shot(rng, environment, value, target, spatial_weights=None, zone_accuracy=None):
    """Return zone, x, y and its calibrated make probability; no outcome draw."""
    probabilities = zone_probabilities(environment, value, target, spatial_weights, zone_accuracy)
    draw = rng.random()
    chosen = probabilities[-1]
    for zone in probabilities:
        draw -= zone[1]
        if draw < 0:
            chosen = zone
            break
    zone, _, probability = chosen
    x, y = draw_location(rng, zone)
    return zone, x, y, probability
