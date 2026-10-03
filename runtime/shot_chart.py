"""Read-only half-court shooting geometry and aggregation from recorded attempts.

Coordinates are feet from the center of the basket: x is lateral, y points
toward half court, and the near baseline is y=-5.25. This module never infers
live coordinates from a box score. Its explicitly named illustrative helper
accepts only example records and exists solely for the offline preview.

Input games use career_stats records: event_id, date, status, coverage, line.
Each shot is {shot_id, game_id, date, x, y, made, value, source_ref}. x/y may
be null; made is boolean and value is 2 or 3. An adapter must authenticate the
source and supply only closed games, not fabricate an event from this view.
"""
from __future__ import annotations

from datetime import date
import math

GEOMETRY_EPSILON = 1e-9  # feet, numerical roundoff only, not measurement tolerance

NBA_GEOMETRY = {
    "units": "feet", "origin": "basket_center", "x_min": -25.0, "x_max": 25.0,
    "baseline_y": -5.25, "half_court_y": 41.75,
    "paint_half_width": 8.0, "paint_top_y": 13.75,
    "three_point_radius": 23.75, "corner_three_x": 22.0,
    "three_point_join_y": math.sqrt(23.75 ** 2 - 22.0 ** 2),
    "under_12_radius": 12.0, "midrange_radius": 18.0,
    "line_policy": "A coordinate on the three-point line is inside the two-point region.",
}
ZONES = (
    {"id": "paint", "label": "Paint"},
    {"id": "under_12", "label": "Outside paint, under 12 ft"},
    {"id": "12_to_18", "label": "Outside paint, 12 to under 18 ft"},
    {"id": "18_to_3pt", "label": "18 ft to the three-point line"},
    {"id": "three", "label": "Three-point range"},
)


def _day(value):
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError("dates must use YYYY-MM-DD")
    return date.fromisoformat(value)


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _on_line(value, boundary):
    return math.isclose(value, boundary, rel_tol=0, abs_tol=GEOMETRY_EPSILON)


def classify_zone(x, y):
    """Return one non-overlapping zone, or None for missing/out-of-view points.

    Use modern NBA geometry, also applicable to the repository's 2003 NBA
    setting. Other courts/eras need a different verified geometry adapter.
    Three-point range takes precedence, followed by paint, then distance bands.
    An exact 12-foot boundary enters 12_to_18; exact 18 enters 18_to_3pt.
    """
    if x is None or y is None:
        if (x is not None and not _number(x)) or (y is not None and not _number(y)):
            raise ValueError("coordinates must be finite numeric feet or null")
        return None
    if not _number(x) or not _number(y):
        raise ValueError("coordinates must be finite numeric feet or null")
    g = NBA_GEOMETRY
    if not g["x_min"] <= x <= g["x_max"] or not g["baseline_y"] <= y <= g["half_court_y"]:
        return None
    distance = math.hypot(x, y)
    three = ((abs(x) > g["corner_three_x"] and not _on_line(abs(x), g["corner_three_x"]))
             if y <= g["three_point_join_y"] else
             (distance > g["three_point_radius"] and not _on_line(distance, g["three_point_radius"])))
    if three:
        return "three"
    if abs(x) <= g["paint_half_width"] and y <= g["paint_top_y"]:
        return "paint"
    if distance < 12 and not _on_line(distance, 12):
        return "under_12"
    if distance < 18 and not _on_line(distance, 18):
        return "12_to_18"
    return "18_to_3pt"


def _box(line):
    """Validate the shooting subset without requiring unrelated box columns."""
    if not isinstance(line, dict):
        raise ValueError("a covered player appearance requires its recorded box")
    required = ("fgm", "fga", "tpm", "tpa")
    if any(type(line.get(k)) is not int or line[k] < 0 for k in required):
        raise ValueError("recorded shooting totals must be nonnegative integers")
    fgm, fga, tpm, tpa = (line[k] for k in required)
    if (fgm > fga or tpm > tpa or tpm > fgm or tpa > fga or
            fgm - tpm > fga - tpa):
        raise ValueError("impossible field-goal and three-point totals")
    if "pts" in line:
        ft_points = line.get("ft_points", line.get("ftm"))
        if (type(ft_points) is not int or ft_points < 0 or type(line["pts"]) is not int or
                line["pts"] != 2 * fgm + tpm + ft_points):
            raise ValueError("box points must reconcile with field goals and recorded free-throw points")
    if "appeared" in line and type(line["appeared"]) is not bool:
        raise ValueError("appeared must be an observed boolean")
    return {k: line[k] for k in required}


def _shot_counts(shots):
    made = sum(s["made"] for s in shots)
    threes = [s for s in shots if s["value"] == 3]
    tpm = sum(s["made"] for s in threes)
    return {"fgm": made, "fga": len(shots), "tpm": tpm, "tpa": len(threes),
            "fg_points": 2 * made + tpm}


def _verify_subset(observed, box):
    """A partial event feed must fit every made/missed 2- and 3-point bucket."""
    parts = lambda c: (c["tpm"], c["tpa"] - c["tpm"], c["fgm"] - c["tpm"],
                       c["fga"] - c["tpa"] - c["fgm"] + c["tpm"])
    if any(a > b for a, b in zip(parts(observed), parts(box))):
        raise ValueError("shot attempts/outcomes do not reconcile with the game's recorded box")


def _metrics(counts, games):
    return {**counts,
            "fg_pct": counts["fgm"] / counts["fga"] if counts["fga"] else None,
            "fg_ppg": counts["fg_points"] / games if games else None,
            "fga_per_game": counts["fga"] / games if games else None}


def aggregate_shots(records, shots, *, start=None, end=None, bin_size=3.0):
    """Aggregate one player's one-competition period without writes or mutation.

    Pass the full record/shot collection and optional inclusive date bounds, or
    already matching subsets. Orphan/duplicate/mismatched shots are errors.
    DNPs are excluded from G; every recorded appearance is included, even one
    with zero FGA. Unknown player boxes make full-period G unknown.

    Partial tracking exposes observed raw counts, but zone totals, zone rates
    and bin per-game rates remain unavailable. Dot area_weight is FGA/G only
    when the selected period has full box and location coverage. It uses the
    same scale across periods and never assigns fictitious points to the court.
    """
    if not _number(bin_size) or not 0 < bin_size <= 10:
        raise ValueError("bin_size must be positive and at most ten feet")
    lower, upper = _day(start) if start else None, _day(end) if end else None
    if lower and upper and lower > upper:
        raise ValueError("period start must not follow period end")
    all_games, selected, missing_boxes = {}, {}, []
    appearances, dnp = [], []
    for record_index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError("game records must be objects")
        if record.get("status") != "played":
            continue
        game_id = record.get("event_id")
        if game_id is None and record.get("coverage") != "complete":
            # A closed note can lack a result file and therefore a canonical
            # event ID. This is only a coverage-row label, never a shot source.
            game_id = f"__missing_box_row__:{record_index}"
        if not isinstance(game_id, str) or not game_id or game_id in all_games:
            raise ValueError("played games need unique nonempty event IDs")
        when = _day(record.get("date"))
        all_games[game_id] = record
        if (lower and when < lower) or (upper and when > upper):
            continue
        selected[game_id] = record
        if record.get("coverage") != "complete":
            missing_boxes.append(game_id)
            continue
        line = record.get("line")
        explicit_dnp = (line is None and str(record.get("appearance", "")).startswith("DNP"))
        if line is not None and line.get("appeared") is False:
            box = _box(line)
            if any(box.values()) or line.get("pts", 0) or line.get("seconds", 0):
                raise ValueError("DNP cannot contain attempts, points or playing time")
            explicit_dnp = True
        if explicit_dnp:
            dnp.append(game_id)
        else:
            _box(line)
            appearances.append(game_id)
    competitions = {r.get("competition") for r in selected.values()}
    if len(competitions) > 1:
        raise ValueError("different competitions must have separate shot charts")
    season_values = {r.get("season") for r in selected.values()}
    if len(season_values) > 1:
        raise ValueError("different seasons must have separate shot charts")
    by_game = {key: [] for key in selected}
    seen = set()
    for shot in shots:
        if not isinstance(shot, dict):
            raise ValueError("shots must be objects")
        shot_id = shot.get("shot_id")
        if not isinstance(shot_id, str) or not shot_id or shot_id in seen:
            raise ValueError("shots need unique nonempty shot IDs")
        seen.add(shot_id)
        game_id = shot.get("game_id")
        if game_id not in all_games:
            raise ValueError("shot refers to an unknown or unplayed game")
        _day(shot.get("date"))
        if shot["date"] != all_games[game_id]["date"]:
            raise ValueError("shot date disagrees with its game")
        if type(shot.get("made")) is not bool or type(shot.get("value")) is not int or shot["value"] not in (2, 3):
            raise ValueError("shot needs a boolean made outcome and a 2- or 3-point value")
        if not isinstance(shot.get("source_ref"), str) or not shot["source_ref"].strip():
            raise ValueError("shot needs a recorded source reference")
        zone = classify_zone(shot.get("x"), shot.get("y"))
        if zone is not None and (3 if zone == "three" else 2) != shot["value"]:
            raise ValueError("recorded shot value disagrees with its coordinate zone; review the source")
        if game_id not in selected:
            continue
        if game_id in dnp:
            raise ValueError("DNP cannot have field-goal attempts")
        if game_id in missing_boxes:
            raise ValueError("shot outcomes require a matching closed player box before aggregation")
        status = "located" if zone else "unlocated" if shot.get("x") is None or shot.get("y") is None else "outside_view"
        by_game[game_id].append({**shot, "zone": zone, "location_status": status})
    observed_shots = [s for group in by_game.values() for s in group]
    totals = {k: 0 for k in ("fgm", "fga", "tpm", "tpa", "fg_points")}
    missing_attempts, missing_shot_games = 0, []
    for game_id in appearances:
        box = _box(selected[game_id]["line"])
        observed = _shot_counts(by_game[game_id])
        _verify_subset(observed, box)
        missing = box["fga"] - observed["fga"]
        missing_attempts += missing
        if missing:
            missing_shot_games.append(game_id)
        for key, value in box.items():
            totals[key] += value
        totals["fg_points"] += 2 * box["fgm"] + box["tpm"]
    located = [s for s in observed_shots if s["zone"]]
    unlocated = sum(s["location_status"] == "unlocated" for s in observed_shots)
    outside = sum(s["location_status"] == "outside_view" for s in observed_shots)
    complete = not (missing_boxes or missing_attempts or unlocated or outside)
    coverage_status = "complete" if complete else "partial" if located else "unavailable"
    games = None if missing_boxes else len(appearances)
    zones = []
    for definition in ZONES:
        counts = _shot_counts([s for s in located if s["zone"] == definition["id"]])
        values = _metrics(counts, games) if complete else {k: None for k in (*counts, "fg_pct", "fg_ppg", "fga_per_game")}
        zones.append({**definition, **values, "coverage": coverage_status,
                      "observed_fgm": counts["fgm"], "observed_fga": counts["fga"],
                      "observed_fg_points": counts["fg_points"]})
    cells = {}
    for shot in located:
        # A zone is part of the bin key, so a cell can never mix paint and threes.
        key = (shot["zone"], math.floor(shot["x"] / bin_size), math.floor(shot["y"] / bin_size))
        cells.setdefault(key, []).append(shot)
    bins = []
    for (zone, bx, by), group in sorted(cells.items()):
        counts = _shot_counts(group)
        metrics = _metrics(counts, games if complete else None)
        # Use an observed medoid, not an invented location or a centroid that
        # might cross the non-convex edge between the paint and another zone.
        mx, my = sum(s["x"] for s in group) / len(group), sum(s["y"] for s in group) / len(group)
        representative = min(group, key=lambda s: ((s["x"] - mx) ** 2 + (s["y"] - my) ** 2, s["shot_id"]))
        bins.append({"id": f"{zone}:{bx}:{by}", "zone": zone,
                     "x": representative["x"], "y": representative["y"], **metrics,
                     "area_weight": metrics["fga_per_game"], "area_unit": "attempts_per_appearance",
                     "coverage": coverage_status, "location_method": "observed_medoid",
                     "shot_ids": sorted(s["shot_id"] for s in group)})
    observed_counts = _shot_counts(observed_shots)
    box_metrics = _metrics(totals, games) if not missing_boxes else {key: None for key in (*totals, "fg_pct", "fg_ppg", "fga_per_game")}
    return {"schema_version": 1, "scope": {"start": start, "end": end},
            "geometry": dict(NBA_GEOMETRY), "games": games, "recorded_appearances": len(appearances),
            "dnp": len(dnp), "closed_games": len(selected), "totals": box_metrics,
            "observed": observed_counts, "zones": zones, "bins": bins,
            "coverage": {"status": coverage_status, "located_attempts": len(located),
                         "unlocated_attempts": unlocated, "outside_view_attempts": outside,
                         "missing_attempts": None if missing_boxes else missing_attempts,
                         "known_missing_attempts": missing_attempts,
                         "recorded_attempts": len(observed_shots),
                         "box_fga": None if missing_boxes else totals["fga"],
                         "missing_box_games": missing_boxes, "missing_shot_games": missing_shot_games,
                         "location_fraction": len(located) / totals["fga"] if totals["fga"] and not missing_boxes else None},
            "source_refs": sorted({s["source_ref"] for s in observed_shots}),
            "notes": ["Zone points count made field goals only; free throws are excluded.",
                      "All recorded appearances in the selected period are in the denominator; DNPs are excluded.",
                      "Incomplete tracking leaves full-period zone and bin per-game rates unavailable.",
                      "Bin area is proportional to attempts per appearance using a fixed display scale, not its radius."]}


def make_illustrative_shots(records, *, example_only=False):
    """Invent explicitly fictional locations solely for existing illustrative boxes.

    This is not a live box-to-location estimator. Requiring both the explicit
    opt-in and illustrative event IDs prevents an accidental canonical adapter
    call. Synthetic makes, misses and values reconcile exactly to each box.
    """
    if example_only is not True:
        raise ValueError("fictional locations require explicit example_only=True")
    records = list(records)
    if any(not str(r.get("event_id", "")).startswith("illustrative-") for r in records if r.get("status") == "played"):
        raise ValueError("fictional locations are restricted to illustrative event IDs")
    two_locations = ((-3.0, 2.0), (3.0, 3.0), (-2.0, 7.0), (4.0, 10.0),
                     (-10.0, 3.0), (10.0, 4.0), (-12.0, 8.0), (11.0, 10.0),
                     (-15.0, 12.0), (14.0, 15.0), (2.0, 20.0))
    three_locations = ((-23.0, 2.0), (23.0, 3.0), (-19.0, 17.0),
                       (18.0, 18.0), (-3.0, 25.0), (5.0, 25.0))
    shots = []
    for gi, record in enumerate(records):
        if record.get("status") != "played" or record.get("line") is None:
            continue
        line = record["line"]
        if line.get("appeared") is False:
            continue
        box = _box(line)
        game_id = record["event_id"]
        for value, attempts, makes, positions in (
                (2, box["fga"] - box["tpa"], box["fgm"] - box["tpm"], two_locations),
                (3, box["tpa"], box["tpm"], three_locations)):
            for i in range(attempts):
                # Rotate a predetermined location list across games. The made
                # flag distributes exact box totals and is fictional, too.
                x, y = positions[(i + gi * 3) % len(positions)]
                made = ((i + gi) % attempts) < makes
                shots.append({"shot_id": f"{game_id}:{value}:{i + 1}", "game_id": game_id,
                              "date": record["date"], "x": x, "y": y,
                              "made": made, "value": value,
                              "source_ref": f"example:fictional-locations/{game_id}",
                              "example_only": True})
    return shots
