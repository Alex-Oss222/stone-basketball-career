"""Validate prospective engine shot events and aggregate explicitly tracked games.

This module never draws locations. Old box scores remain locationless; new
coordinates are evidence of the simulation, not historical tracking data.
"""
from __future__ import annotations

from collections import Counter
from datetime import date
import hashlib
import json
import math
import re

from .career_stats import aggregate
from .shot_chart import GEOMETRIES, aggregate_shots, classify_zone


ENGINE_SHOT_LABEL = "Simulated engine shot locations"
TRACKING_KEYS = {"schema_version", "model_version", "coordinate_system", "source_type", "prior_sha256", "coverage"}
SHOT_KEYS = {"shot_id", "player_id", "side", "period", "clock_seconds", "x", "y", "zone", "value", "made", "transition"}


def _spatial_kernel(kernel):
    match = re.fullmatch(r"(\d+)\.(\d+)", str(kernel))
    return bool(match and tuple(map(int, match.groups())) >= (2003, 7))


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def spatial_result_errors(result):
    """Return feed errors, accepting legacy results with neither tracking field.

The kernel calls this before its runner adds the kernel/date envelope. A reader
additionally requires that envelope in ``engine_result_shots``.
    """
    if not isinstance(result, dict):
        return ["shot result must be an object"]
    present = "shot_tracking" in result or "shots" in result
    if not present:
        return ["spatial kernel result is missing shot tracking"] if _spatial_kernel(result.get("kernel")) else []
    errors = []
    if "kernel" in result and not _spatial_kernel(result["kernel"]):
        errors.append("shot tracking cannot be appended to a legacy kernel result")
    tracking = result.get("shot_tracking")
    if (not isinstance(tracking, dict) or set(tracking) != TRACKING_KEYS
            or type(tracking.get("schema_version")) is not int or tracking["schema_version"] != 1
            or tracking.get("model_version") != "spatial-2003.1"
            or tracking.get("coordinate_system") not in GEOMETRIES
            or tracking.get("source_type") != "engine_generated"
            or tracking.get("coverage") != "complete"
            or not isinstance(tracking.get("prior_sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", tracking["prior_sha256"])):
        errors.append("shot tracking requires complete versioned engine-generated provenance")
    shots = result.get("shots")
    if not isinstance(shots, list):
        return errors + ["shot events must be a list"]
    event_id = result.get("event_id")
    if not isinstance(event_id, str) or not event_id.strip():
        errors.append("shot result requires an event ID")
    periods = result.get("periods")
    if type(periods) is not int or periods < 4:
        errors.append("shot result requires a completed regulation game")
        periods = 0
    scores = result.get("period_scores", {})
    if not isinstance(scores, dict) or any(not isinstance(scores.get(side), list) or len(scores[side]) != periods for side in ("home", "away")):
        errors.append("shot periods disagree with the period scores")
    rows, expected = {}, {}
    stats = result.get("player_stats", {})
    for side in ("home", "away"):
        boxes = stats.get(side) if isinstance(stats, dict) else None
        if not isinstance(boxes, list):
            errors.append(f"{side}: shot result needs player boxes")
            continue
        for box in boxes:
            pid = box.get("player_id") if isinstance(box, dict) else None
            if not isinstance(pid, str) or not pid.strip() or (side, pid) in rows:
                errors.append(f"{side}: invalid or duplicate shot player identity")
                continue
            rows[side, pid] = box
            keys = ("fgm", "fga", "tpm", "tpa")
            if any(type(box.get(k)) is not int or box[k] < 0 for k in keys):
                errors.append(f"{side}/{pid}: invalid shooting totals")
                continue
            fgm, fga, tpm, tpa = (box[k] for k in keys)
            counts = {(2, True): fgm - tpm, (2, False): fga - tpa - fgm + tpm,
                      (3, True): tpm, (3, False): tpa - tpm}
            if min(counts.values()) < 0:
                errors.append(f"{side}/{pid}: impossible shooting totals")
            expected[side, pid] = counts
    observed, transition = {}, {side: Counter() for side in ("home", "away")}
    period_points = {side: Counter() for side in ("home", "away")}
    previous, ids = (0, 0), set()
    # Imported lazily: spatial_shots is the model, this module only validates it.
    from .spatial_shots import classify_spatial_zone
    for index, shot in enumerate(shots, 1):
        prefix = f"shot {index}"
        if not isinstance(shot, dict) or set(shot) != SHOT_KEYS:
            errors.append(f"{prefix}: invalid event fields")
            continue
        sid = shot["shot_id"]
        if not isinstance(sid, str) or sid in ids or sid != f"{event_id}:shot:{index:06d}":
            errors.append(f"{prefix}: invalid, duplicate or out-of-order shot ID")
        if isinstance(sid, str):
            ids.add(sid)
        side, pid = shot["side"], shot["player_id"]
        valid_player = isinstance(side, str) and isinstance(pid, str) and (side, pid) in rows
        if not valid_player:
            errors.append(f"{prefix}: shooter is absent from that side's player boxes")
        elif not _number(rows[side, pid].get("seconds")) or rows[side, pid]["seconds"] <= 0:
            errors.append(f"{prefix}: a shot requires positive recorded player court time")
        p, clock = shot["period"], shot["clock_seconds"]
        if type(p) is not int or not 1 <= p <= periods or not _number(clock) or not 0 <= clock <= (720 if p <= 4 else 300):
            errors.append(f"{prefix}: invalid period or game clock")
        else:
            order = (p, -clock)
            if order < previous:
                errors.append(f"{prefix}: events are not in game-clock order")
            previous = order
        x, y, value, made = (shot[k] for k in ("x", "y", "value", "made"))
        valid_outcome = type(value) is int and value in (2, 3) and type(made) is bool
        if not valid_outcome or type(shot["transition"]) is not bool:
            errors.append(f"{prefix}: invalid value, make or transition flag")
        if not _number(x) or not _number(y):
            errors.append(f"{prefix}: coordinates must be finite numeric feet")
        else:
            court = GEOMETRIES.get((tracking or {}).get("coordinate_system") if isinstance(tracking, dict) else None)
            chart_zone = classify_zone(x, y, court)
            native_zone = classify_spatial_zone(x, y, court)
            if chart_zone is None or native_zone is None or shot["zone"] != native_zone:
                errors.append(f"{prefix}: location disagrees with its spatial zone")
            if valid_outcome and ((chart_zone == "three") != (value == 3)):
                errors.append(f"{prefix}: location disagrees with its shot value")
        if valid_player and valid_outcome:
            observed.setdefault((side, pid), Counter())[value, made] += 1
            if type(p) is int and 1 <= p <= periods:
                period_points[side][p] += value * int(made)
            if shot["transition"] is True:
                transition[side]["fga"] += 1
                transition[side]["fgm"] += int(made)
    for identity, counts in expected.items():
        actual = observed.get(identity, Counter())
        if any(actual[bucket] != count for bucket, count in counts.items()):
            errors.append(f"{'/'.join(identity)}: shot events do not reconcile with made/missed twos and threes")
    teams = result.get("team_stats", {})
    for side in ("home", "away"):
        team = teams.get(side, {}) if isinstance(teams, dict) else {}
        if not isinstance(team, dict):
            errors.append(f"{side}: invalid shot team totals")
            team = {}
        for key in ("fgm", "fga", "tpm", "tpa"):
            total = sum(row.get(key, 0) for (s, _), row in rows.items() if s == side and type(row.get(key)) is int)
            if type(team.get(key)) is not int or team[key] != total:
                errors.append(f"{side}: shot player totals disagree with team {key}")
        recorded_scores = scores.get(side) if isinstance(scores, dict) else None
        if isinstance(recorded_scores, list):
            for p, score in enumerate(recorded_scores, 1):
                if type(score) is not int or score < period_points[side][p]:
                    errors.append(f"{side}: shot field-goal points exceed recorded period {p} score")
        if "transition_stats" in result:
            counters = result["transition_stats"]
            counters = counters.get(side, {}) if isinstance(counters, dict) else {}
            if not isinstance(counters, dict) or any(counters.get(k) != transition[side][k] for k in ("fgm", "fga")):
                errors.append(f"{side}: shot transition flags disagree with transition totals")
    return errors


validate_shot_events = spatial_result_errors


def engine_result_shots(result, *, source_ref):
    """Normalize a trusted closed result's events, preserving engine provenance.

Callers must establish that this is the result belonging to a closed canonical
game. Source digests bind displayed events to the complete immutable response.
    """
    errors = spatial_result_errors(result)
    if errors:
        raise ValueError("; ".join(errors))
    if "shot_tracking" not in result:
        return []
    if (not _spatial_kernel(result.get("kernel")) or result.get("terminated") is not True
            or not isinstance(result.get("game_date"), str)
            or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", result["game_date"])
            or not isinstance(source_ref, str) or not source_ref.strip()):
        raise ValueError("engine locations require a closed, versioned result with a dated source")
    date.fromisoformat(result["game_date"])
    digest = hashlib.sha256(json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    return [{**shot, "game_id": result["event_id"], "date": result["game_date"],
             "source_ref": source_ref, "source_digest": digest, "source_type": "engine_generated"}
            for shot in result["shots"]]


def shot_source_type(shots, source_games=()):
    types = {"engine_generated" if s.get("source_type") == "engine_generated" else "recorded" for s in shots}
    types.update("engine_generated" if s["shot_source_type"] == "engine_generated" else "recorded"
                 for s in source_games if s.get("shot_source_type") not in (None, "unavailable"))
    return next(iter(types)) if len(types) == 1 else "mixed" if types else "unavailable"


def build_tracking_cohort(records, shots, *, tracked_game_ids, source_games=()):
    """Build separate complete-game aggregates; never erase missing coverage.

Explicit source IDs are required even for zero-attempt/DNP games so old blank
boxes do not silently become spatially tracked games.
    """
    closed = [r for r in records if r.get("status") == "played"]
    by_game = {}
    for shot in shots:
        by_game.setdefault(shot["game_id"], []).append(shot)
    selected = [r for r in closed if r.get("event_id") and r["event_id"] in tracked_game_ids
                and aggregate_shots([r], by_game.get(r["event_id"], []))["coverage"]["status"] == "complete"]
    whole, summary = aggregate(closed), aggregate(selected)
    dates = sorted(r["date"] for r in selected)
    cohort = dict(games=len(selected), appearances=summary["gp"], total_games=len(closed),
                  total_appearances=whole["gp"], start=dates[0] if dates else None,
                  end=dates[-1] if dates else None, excluded_games=len(closed) - len(selected))
    if not selected:
        return dict(tracked=None, tracking_cohort=cohort)
    ids = {r["event_id"] for r in selected}
    included = [s for s in shots if s["game_id"] in ids]
    included_sources = [s for s in source_games if s["id"] in ids]
    kind = shot_source_type(included, included_sources)
    source_note = (ENGINE_SHOT_LABEL + ". " if kind == "engine_generated" else
                   "Simulated engine and separately recorded shot locations. " if kind == "mixed" else "Recorded shot locations. ")
    source_note += "Tracked games only: complete location coverage in the listed source games; older untracked games remain excluded."
    tracked = dict(games=summary["closed"], appearances=summary["gp"], dnp=summary["dnp"],
                   box=summary["totals"], rates=summary["rates"], pg=summary["pg"], per36=summary["per36"],
                   shots=included, shooting=aggregate_shots(selected, included),
                   source_games=included_sources, source_note=source_note,
                   shot_source_type=kind, start=dates[0], end=dates[-1], cutoff=dates[-1],
                   label=f"Tracked games only · {dates[0]} to {dates[-1]}")
    return dict(tracked=tracked, tracking_cohort=cohort)
