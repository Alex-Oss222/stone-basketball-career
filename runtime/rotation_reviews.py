"""Fortnightly staff decisions from dated, closed Miami regular-season evidence.

The camp assessment is a fixed prior worth 300 minutes. Each review adds every
closed regular-season minute before that day, never another review's score.
Close starting battles are ordinary engine decision packets. This module does
not draw them, play games, change the clock, or rewrite existing game inputs.
"""
from datetime import date, timedelta
import hashlib
import json
import math
from pathlib import Path

from . import camp
from .career_stats import normalize_line
from .decisions import decision_errors
from .season_games import (MIAMI, ROOT, check_date, read_json,
                           season_base, season_games, written_notes, note_meta)

REVIEW_DAYS = 14
PRIOR_MINUTES = 300.0
SCORE_MINUTES = 30.0
CLOSE_BATTLE = camp.CLOSE_BATTLE



def _active_season(root=None):
    """The career's live season (runtime/seasons.py), read from the repository a call works on."""
    from .seasons import active
    return active(root or ROOT)

def depth_dir(root=ROOT, season=None):
    season = season or _active_season(root)
    return Path(root) / season_base(season) / "00_Team/Team/Depth_Chart"


def review_dir(on, root=ROOT, season=None):
    season = season or _active_season(root)
    return depth_dir(root, season) / "Reviews" / check_date(on)


def assessment_date(root=ROOT, season=None):
    """Camp's assessment fixes the cadence; a later roster correction does not reset it."""
    season = season or _active_season(root)
    camp_path = Path(root) / season_base(season) / "04_Training_Camp/camp_roster.json"
    assessed = read_json(camp_path) if camp_path.exists() else {}
    return check_date(assessed.get("evaluated") or read_json(depth_dir(root, season) / "rotation.json")["as_of"])


def review_dates(until, root=ROOT, season=None):
    """Every review due, on the camp decision's fixed fourteen-day cadence."""
    season = season or _active_season(root)
    check_date(until)
    baseline = depth_dir(root, season) / "rotation.json"
    if not baseline.exists():
        return []
    last_game = max((g["date"] for g in season_games(season, root)
                     if MIAMI in (g["home"], g["away"])), default=until)
    cutoff = min(until, last_game)
    day = date.fromisoformat(assessment_date(root, season)) + timedelta(days=REVIEW_DAYS)
    out = []
    while day.isoformat() <= cutoff:
        out.append(day.isoformat())
        day += timedelta(days=REVIEW_DAYS)
    return out


def pending_reviews(until, root=ROOT, season=None):
    season = season or _active_season(root)
    return [on for on in review_dates(until, root, season)
            if not all((review_dir(on, root, season) / name).exists()
                       for name in ("review.json", "depth_chart.json", "rotation.json"))]


def rotation_in_force(on, root=ROOT, season=None, require_review=True):
    """The dated rotation and depth chart, without changing the camp baseline."""
    season = season or _active_season(root)
    folder = depth_dir(root, season)
    baseline = folder / "rotation.json"
    if not baseline.exists():
        raise ValueError("no rotation: the camp decision (rotation.json) has not been written")
    rotation = read_json(baseline)
    if rotation["as_of"] > on:
        raise ValueError(f"rotation.json is dated {rotation['as_of']}, after the game on {on}")
    if require_review:
        pending = pending_reviews(on, root, season)
        if pending:
            raise ValueError(f"staff rotation review due {pending[0]}; run scripts/review_rotation.py --write {pending[0]} and collect any engine battle draws before building this game")
    depth = read_json(folder / "depth_chart.json")
    selected_review = None
    for path in sorted((folder / "Reviews").glob("*/rotation.json")):
        if path.parent.name > on:
            continue
        candidate = read_json(path)
        if candidate.get("as_of") != path.parent.name:
            raise ValueError(f"{path}: rotation date differs from its dated folder")
        if candidate["as_of"] >= rotation["as_of"]:
            rotation = candidate
            depth = read_json(path.with_name("depth_chart.json"))
            selected_review = path
    if depth.get("as_of", "") > on:
        raise ValueError("no historical depth chart for this game; the available chart is dated after it")
    if selected_review is not None:
        errors = review_errors(root, season, until=on)
        if errors:
            raise ValueError("; ".join(errors))
    return rotation, depth


def closed_evidence(on, root=ROOT, season=None):
    """Require the earlier schedule closed; only played notes own result evidence."""
    season = season or _active_season(root)
    notes = written_notes(root, season)
    results, sources, pending = [], [], []
    for game in season_games(season, root):
        if MIAMI not in (game["home"], game["away"]) or game["date"] >= on:
            continue
        note_row = notes.get(game["game_id"])
        if note_row is None:
            pending.append(game["game_id"])
            continue
        path = note_row[0]
        meta = note_meta(path)
        if meta.get("status") == "not_played" and meta.get("reason"):
            continue
        declared = meta.get("result_file")
        if meta.get("status") != "played" or not declared:
            pending.append(game["game_id"])
            continue
        result_path = path.parent / declared
        if result_path.parent != path.parent or not result_path.is_file():
            pending.append(game["game_id"])
            continue
        result = read_json(result_path)
        if not result.get("terminated"):
            pending.append(game["game_id"])
            continue
        expected = {"event_id": game["game_id"], "game_date": game["date"],
                    "game_type": "regular", "home": game["home"], "away": game["away"]}
        if any(result.get(k) != v for k, v in expected.items()) or meta.get("date") != game["date"]:
            raise ValueError(f"{result_path}: closed result disagrees with its scheduled game")
        results.append(result)
        sources.append({"event_id": game["game_id"], "date": game["date"],
                        "result_file": str(result_path.relative_to(root)),
                        "sha256": hashlib.sha256(result_path.read_bytes()).hexdigest()})
    return results, sources, pending


def staff_scores(players, priors, results):
    """Same prior minutes for everyone; no seniority, draft-slot or start bonus."""
    totals = {}
    for result in results:
        side = "home" if result["home"] == MIAMI else "away"
        for row in result["player_stats"][side]:
            line = normalize_line(row, weighted_free_throws=result.get("free_throw_mode") == "weighted")
            if not line["appeared"]:
                continue
            t = totals.setdefault(row["player_id"], {"games": 0, "minutes": 0.0, "efficiency": 0.0})
            t["games"] += 1
            t["minutes"] += line["seconds"] / 60
            t["efficiency"] += camp.efficiency(line)
    scores, evidence = {}, {}
    for p in players:
        name = p["player"]
        if name not in priors:
            raise ValueError(f"no preseason staff estimate for {name}; record a dated estimate in Depth_Chart/preseason_estimates.json")
        value = priors[name]
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
            raise ValueError(f"nonfinite preseason estimate for {name}")
        prior = float(value)
        t = totals.get(name, {"games": 0, "minutes": 0.0, "efficiency": 0.0})
        scores[name] = round((prior * PRIOR_MINUTES + t["efficiency"] * SCORE_MINUTES) /
                             (PRIOR_MINUTES + t["minutes"]), 6)
        evidence[name] = dict(t, preseason_estimate=prior,
                             observed_per_30=(round(t["efficiency"] / t["minutes"] * SCORE_MINUTES, 6) if t["minutes"] else None),
                             observed_weight=round(t["minutes"] / (PRIOR_MINUTES + t["minutes"]), 6),
                             score=scores[name])
    return scores, evidence


def battle_packets(players, scores, on, season=None):
    season = season or _active_season()
    packets = []
    for pos in camp.POSITIONS:
        names = sorted((p["player"] for p in players if p["positions"][0] == pos),
                       key=lambda n: (-scores[n], n))
        if len(names) < 2:
            continue
        a, b = names[:2]
        gap = (scores[a] - scores[b]) / max(abs(scores[a]), abs(scores[b]), 1.0)
        if gap > CLOSE_BATTLE:
            continue
        probability = round(0.5 + 0.25 * gap / CLOSE_BATTLE, 6)
        packet = {"event_id": f"{season}-rotation-{on}-{pos.lower()}-starter", "date": on,
                  "question": f"Who starts at {pos}: {a} or {b}?",
                  "decider": "Miami coaching staff (engine evaluation draw)",
                  "options": {a: probability, b: round(1 - probability, 6)},
                  "basis": f"Dated staff scores {scores[a]} and {scores[b]} within {CLOSE_BATTLE:.0%}; closed production per {SCORE_MINUTES:g} minutes blended with {PRIOR_MINUTES:g} preseason prior minutes. No seniority, draft-slot or incumbent bonus."}
        errors = decision_errors(packet)
        if errors:
            raise ValueError("; ".join(errors))
        packets.append(packet)
    return packets


def preseason_priors(on, root=ROOT, season=None):
    """Dated staff estimates, preserving the first frozen prior for each player.

    Camp evaluation scores lead. Players signed in a later camp refill retain
    the recorded basketball value on that signing decision, before fit or a
    Wade request affects recruitment. No later season ability is consulted.
    """
    season = season or _active_season(root)
    base = Path(root) / season_base(season)
    camp_path = base / "04_Training_Camp/camp_roster.json"
    assessed = read_json(camp_path) if camp_path.exists() else {}
    if assessed.get("evaluated", "") > on:
        raise ValueError("preseason assessment is dated after this review")
    # The first frozen estimate remains the prior at every later review,
    # including camp players who were not on the first review's active roster.
    priors = {}
    for path in sorted((depth_dir(root, season) / "Reviews").glob("*/review.json")):
        if path.parent.name < on:
            for name, value in read_json(path)["prior_scores"].items():
                priors.setdefault(name, value)
    for name, value in assessed.get("staff_scores", {}).items():
        priors.setdefault(name, value)
    correction_path = base / "04_Training_Camp/signing_corrections.json"
    if correction_path.exists():
        correction = read_json(correction_path)
        if correction.get("date", "") and correction["date"] <= on and correction.get("rotation_written", "") and correction["rotation_written"] <= on:
            for row in correction.get("refill", {}).get("picks", []):
                priors.setdefault(row["player"], row["value"])
    estimates = depth_dir(root, season) / "preseason_estimates.json"
    if estimates.exists():
        for row in read_json(estimates).get("players", []):
            if row["as_of"] <= on:
                priors.setdefault(row["player"], row["score"])
    return priors


def review_input(on, root=ROOT, season=None):
    """Freeze basketball evidence before any engine battle draw is requested."""
    season = season or _active_season(root)
    base = Path(root) / season_base(season)
    roster = read_json(base / "00_Team/Team/Roster/roster.json")
    if roster.get("as_of", "") > on:
        raise ValueError("cannot reconstruct a past staff review from a later roster")
    players = [{"player": p["name"], "positions": p["positions"], "bbr_id": p.get("bbr_id"), "status": "roster"}
               for p in roster["players"] if camp.playable(p.get("status"))]
    players.sort(key=lambda p: p["player"])
    if len(players) < 5:
        raise ValueError("staff review needs at least five contracted players")
    priors = preseason_priors(on, root, season)
    results, sources, pending = closed_evidence(on, root, season)
    if pending:
        raise ValueError("awaiting closed Miami results before " + on + ": " + ", ".join(pending))
    scores, evidence = staff_scores(players, priors, results)
    return {"schema_version": 1, "owner": "ai_gm", "season": season, "as_of": on,
            "assessment_date": assessment_date(root, season),
            "prior_minutes": PRIOR_MINUTES, "score_minutes": SCORE_MINUTES,
            "prior_scores": priors,
            "evidence_cutoff": "game_date strictly before review date", "sources": sources,
            "players": players, "scores": scores, "evidence": evidence,
            "battles": battle_packets(players, scores, on, season)}


def save_once(path, data):
    """Refuse changed evidence, requests, or completed decisions under one date."""
    if path.exists():
        if read_json(path) != data:
            raise ValueError(f"{path}: immutable staff record differs; it cannot be rewritten")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def decision_outcome(packet, path):
    result = read_json(path)
    if (result.get("kind") != "decision" or
            any(result.get(k) != packet[k] for k in ("event_id", "date", "question", "decider", "options")) or
            result.get("outcome") not in packet["options"]):
        raise ValueError(f"{path}: engine result does not answer the unchanged staff battle packet")
    return result["outcome"]


def validate_evidence(snapshot, root=ROOT, season=None):
    """Replay frozen scores and require their canonical evidence still unchanged."""
    season = season or _active_season(root)
    if snapshot.get("prior_minutes") != PRIOR_MINUTES or snapshot.get("score_minutes") != SCORE_MINUTES:
        raise ValueError("saved scoring rule differs from the staff rule")
    for value in snapshot["prior_scores"].values():
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
            raise ValueError("preseason estimates must be finite numbers")
    results, sources, pending = closed_evidence(snapshot["as_of"], root, season)
    if pending or sources != snapshot["sources"]:
        raise ValueError("closed evidence differs from the frozen staff review")
    scores, evidence = staff_scores(snapshot["players"], snapshot["prior_scores"], results)
    if scores != snapshot["scores"] or evidence != snapshot["evidence"]:
        raise ValueError("staff scores differ from the closed production and preseason estimates")


def review_rotation(snapshot, winners):
    on = snapshot["as_of"]
    roster = {"players": snapshot["players"]}
    depth = camp.depth_chart_from(roster, snapshot["scores"], winners, on)
    depth.update(status="staff_review", basis=f"Fortnightly staff review {on}; fixed preseason estimate plus closed production per minute")
    rotation = camp.season_rotation(roster, depth, snapshot["scores"], on)
    starters = {pos: names[0] for pos, names in depth["positions"].items() if names}
    # A short positional group uses the best remaining player; no size model is implied.
    selected = set(starters.values())
    for pos in camp.POSITIONS:
        if pos not in starters:
            replacement = next(p["player_id"] for p in rotation["players"] if p["player_id"] not in selected)
            starters[pos] = replacement
            selected.add(replacement)
    rotation.update(starters=starters, review="review.json")
    for player in rotation["players"]:
        player["starter"] = player["player_id"] in selected
    return depth, rotation


def write_review(on, root=ROOT, season=None):
    """Write a due review, or its battle requests and pending IDs. Never draws."""
    season = season or _active_season(root)
    if on not in review_dates(on, root, season):
        raise ValueError(f"{on} is not a fortnightly staff review date")
    earlier = [day for day in pending_reviews(on, root, season) if day < on]
    if earlier:
        raise ValueError(f"complete earlier staff review {earlier[0]} first")
    folder = review_dir(on, root, season)
    if (folder / "rotation.json").exists():
        errors = review_errors(root, season, until=on)
        if errors:
            raise ValueError("; ".join(errors))
        return []
    snapshot_path = folder / "review.json"
    if snapshot_path.exists():
        # A draw resumes its frozen review even if the roster has since changed.
        snapshot = read_json(snapshot_path)
        validate_evidence(snapshot, root, season)
        if snapshot.get("as_of") != on or snapshot["battles"] != battle_packets(snapshot["players"], snapshot["scores"], on, season):
            raise ValueError("frozen review date or battle packets differ from the staff evidence")
    else:
        errors = review_errors(root, season, until=on)
        if errors:
            raise ValueError("; ".join(errors))
        snapshot = review_input(on, root, season)
        validate_evidence(snapshot, root, season)
        save_once(snapshot_path, snapshot)
    winners, pending = {}, []
    for packet in snapshot["battles"]:
        request = folder / f"{packet['event_id']}.decision.json"
        result = folder / f"{packet['event_id']}.decision.result.json"
        save_once(request, packet)
        if result.exists():
            winners[packet["event_id"].split("-")[-2].upper()] = decision_outcome(packet, result)
        else:
            pending.append(packet["event_id"])
    if pending:
        return pending
    depth, rotation = review_rotation(snapshot, winners)
    save_once(folder / "depth_chart.json", depth)
    save_once(folder / "rotation.json", rotation)
    return []


def run_reviews(until, root=ROOT, season=None):
    """Complete reviews in date order, stopping at the first unresolved draw."""
    season = season or _active_season(root)
    written = []
    for on in pending_reviews(until, root, season):
        pending = write_review(on, root, season)
        if pending:
            return written, pending
        written.append(on)
    return written, []


def review_errors(root=ROOT, season=None, until=None):
    """Replay saved outputs from frozen evidence and checked engine answers."""
    season = season or _active_season(root)
    errors = []
    known_priors = {}
    for path in sorted((depth_dir(root, season) / "Reviews").glob("*/rotation.json")):
        if until is not None and path.parent.name > until:
            continue
        if not path.with_name("review.json").exists():
            errors.append(f"{path.relative_to(root)}: rotation has no frozen staff review")
    for path in sorted((depth_dir(root, season) / "Reviews").glob("*/review.json")):
        if until is not None and path.parent.name > until:
            continue
        try:
            snapshot = read_json(path)
            if snapshot.get("as_of") != path.parent.name:
                raise ValueError("review date differs from its dated folder")
            if snapshot.get("season") != season:
                raise ValueError("review season differs from its season folder")
            if snapshot.get("assessment_date", assessment_date(root, season)) != assessment_date(root, season):
                raise ValueError("review cadence differs from the original camp assessment date")
            if snapshot["as_of"] not in review_dates(snapshot["as_of"], root, season):
                raise ValueError("review is outside the fortnightly cadence")
            earlier = [day for day in pending_reviews(snapshot["as_of"], root, season) if day < snapshot["as_of"]]
            if earlier:
                raise ValueError(f"review cannot precede unresolved earlier staff review {earlier[0]}")
            validate_evidence(snapshot, root, season)
            if any(snapshot["prior_scores"].get(name) != value for name, value in known_priors.items()):
                raise ValueError("preseason prior differs from an earlier frozen staff review")
            known_priors.update(snapshot["prior_scores"])
            winners = {}
            expected = battle_packets(snapshot["players"], snapshot["scores"], snapshot["as_of"], season)
            if snapshot["battles"] != expected:
                raise ValueError("battle packets differ from staff scores")
            for packet in expected:
                request = path.parent / f"{packet['event_id']}.decision.json"
                result = path.parent / f"{packet['event_id']}.decision.result.json"
                if not request.exists() or read_json(request) != packet:
                    raise ValueError("battle request differs from frozen review")
                if result.exists():
                    winners[packet["event_id"].split("-")[-2].upper()] = decision_outcome(packet, result)
            rotation_path = path.with_name("rotation.json")
            if rotation_path.exists():
                if len(winners) != len(expected):
                    raise ValueError("rotation closed before all engine battle draws")
                depth, rotation = review_rotation(snapshot, winners)
                if read_json(rotation_path) != rotation or read_json(path.with_name("depth_chart.json")) != depth:
                    raise ValueError("dated rotation/depth differs from frozen staff evidence and engine draws")
        except (OSError, KeyError, TypeError, ValueError, AttributeError) as exc:
            errors.append(f"{path.relative_to(root)}: {exc}")
    return errors
