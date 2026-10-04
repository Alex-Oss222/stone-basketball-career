"""Rookie estimates: translate pre-draft statistics into NBA engine rates.

Only evidence available on draft night is used. A draftee without a pre-draft
record gets no profile and plays on the engine's neutral fallback, which is not
a claim that he is an average player.

Method (model rookie-2003.2), per rate:

1. Combine the player's pre-draft seasons with recency weights.
2. Translate to an NBA-equivalent rate: shooting percentages and attempt
   tendencies are the observed rate times a level factor; production rates
   (usage, assists, rebounds, steals, blocks) are the NBA rate baseline times
   the player's per-minute production relative to the NBA per-minute average,
   times a level factor.
3. Shrink toward the NBA baseline with the veteran priors, counting each
   pre-draft attempt or minute as EVIDENCE_WEIGHT of an NBA one.

Every constant below is a provisional judgement, not a fitted estimate. They are
kept in one place so a later calibration against historical rookie seasons can
replace them.
"""
from pathlib import Path

from .player_stats import (PRIOR_ATTEMPTS, PRIOR_MINUTES, RATE_KEYS, ROOT, STATS_PATH, read_json, sha256)
from .prospect_scouting import (PAINT_FTR_FACTOR, POSITION_PATH, SCOUTING_PATH,
                                position_rebound_priors, style_for, trait_value, validate_scouting)

ROOKIE_MODEL_VERSION = "rookie-2003.3"
ARCHIVED_ROOKIE_MODEL_VERSION = "rookie-2003.2"
LEGACY_ROOKIE_MODEL_VERSION = "rookie-2003.1"
SCOUTED_MODEL_VERSIONS = (ARCHIVED_ROOKIE_MODEL_VERSION, ROOKIE_MODEL_VERSION)
# Model adoption, not a change in the player's talent or a new scouting date.
# Games before SCOUTING_EFFECTIVE_FROM keep rookie-2003.1; games from it until STYLE_EFFECTIVE_FROM keep the
# archived rookie-2003.2 (first scouting); games from STYLE_EFFECTIVE_FROM use rookie-2003.3 (shot-making
# traits expressed, Wade's revised scoring canon; the user's premise of December 2003).
SCOUTING_EFFECTIVE_FROM = "2003-11-12"
STYLE_EFFECTIVE_FROM = "2003-12-03"
ARCHIVED_ROOKIE_PATH = Path("library/2003/league/nba_2003_rookie_estimates_2003_2.json")
# The archive is immutable closed-game evidence: its bytes are pinned, not rebuilt from today's sources.
ARCHIVED_ROOKIE_SHA256 = "1d2d2d9cfc88fd97b3a54a70e0508a3903640cc78950d2fb4cd31495c63a1dd1"
PROSPECTS_PATH = Path("library/2003/league/nba_2003_prospect_stats.json")
LEGACY_PROSPECTS_PATH = Path("library/2003/league/nba_2003_prospect_stats_2003_1.json")
ROOKIE_PATH = Path("library/2003/league/nba_2003_rookie_estimates.json")
LEGACY_ROOKIE_PATH = Path("library/2003/league/nba_2003_rookie_estimates_2003_1.json")
VETERAN_PATH = Path("library/2003/league/nba_2003_veteran_ratings.json")

RECENCY_WEIGHTS = (3, 2, 1)       # most recent season first
EVIDENCE_WEIGHT = {"ncaa": 0.5}   # levels without a factor table are refused
LEVEL_FACTORS = {
    "ncaa": {
        "two_point_pct": 0.92,             # longer, faster interior defense
        "three_point_pct": 0.90,           # 19'9" college line vs 22'-23'9" NBA line
        "free_throw_pct": 1.00,            # same distance and conditions
        "three_point_attempt_rate": 0.75,  # fewer threes at the longer line
        "free_throw_attempt_rate": 0.85,
        "turnovers_per_fga": 1.15,         # more pressure and length
        "usage_pct": 0.85, "assist_pct": 0.85,
        "offensive_rebound_pct": 0.85, "defensive_rebound_pct": 0.85,
        "steal_pct": 0.80, "block_pct": 0.80,
    },
}
COUNT_KEYS = ("games", "minutes", "points", "field_goals_made", "field_goals_attempted",
              "three_pointers_made", "three_pointers_attempted", "free_throws_made",
              "free_throws_attempted", "rebounds", "assists", "steals", "blocks", "turnovers")


def _weighted(seasons):
    ordered = sorted(seasons, key=lambda s: s["season"], reverse=True)
    if len(ordered) > len(RECENCY_WEIGHTS):
        raise ValueError("more pre-draft seasons than recency weights")
    weights = RECENCY_WEIGHTS[:len(ordered)]
    totals = {k: sum(w * s[k] for w, s in zip(weights, ordered)) for k in COUNT_KEYS}
    raw = {k: sum(s[k] for s in ordered) for k in COUNT_KEYS}
    return totals, raw


def _nba_per_minute(source_totals):
    m = source_totals["minutes"]
    t = source_totals
    return {
        "usage": (t["field_goals_attempted"] + .44 * t["free_throws_attempted"] + t["turnovers"]) / m,
        "assists": t["assists"] / m,
        "rebounds": (t["offensive_rebounds"] + t["defensive_rebounds"]) / m,
        "steals": t["steals"] / m, "blocks": t["blocks"] / m,
    }


def translate(record, baselines, source_totals, scouting=None, rebound_priors=None):
    level = record["level"]
    if level not in LEVEL_FACTORS:
        raise ValueError(f"{record['player_id']}: no translation factors for level {level!r}")
    f, evidence = LEVEL_FACTORS[level], EVIDENCE_WEIGHT[level]
    w, raw = _weighted(record["seasons"])
    nba = _nba_per_minute(source_totals)
    two_a, two_m = w["field_goals_attempted"] - w["three_pointers_attempted"], w["field_goals_made"] - w["three_pointers_made"]
    per_min = lambda key: w[key] / w["minutes"]
    usage = (w["field_goals_attempted"] + .44 * w["free_throws_attempted"] + w["turnovers"]) / w["minutes"]
    translated = {
        "two_point_pct": two_m / two_a * f["two_point_pct"],
        "three_point_pct": w["three_pointers_made"] / w["three_pointers_attempted"] * f["three_point_pct"],
        "free_throw_pct": w["free_throws_made"] / w["free_throws_attempted"] * f["free_throw_pct"],
        "three_point_attempt_rate": w["three_pointers_attempted"] / w["field_goals_attempted"] * f["three_point_attempt_rate"],
        "free_throw_attempt_rate": w["free_throws_attempted"] / w["field_goals_attempted"] * f["free_throw_attempt_rate"],
        "turnovers_per_fga": w["turnovers"] / w["field_goals_attempted"] * f["turnovers_per_fga"],
        "usage_pct": baselines["usage_pct"] * usage / nba["usage"] * f["usage_pct"],
        "assist_pct": baselines["assist_pct"] * per_min("assists") / nba["assists"] * f["assist_pct"],
        # Pre-draft records give total rebounds only; both sides use the same relative rate.
        "offensive_rebound_pct": baselines["offensive_rebound_pct"] * per_min("rebounds") / nba["rebounds"] * f["offensive_rebound_pct"],
        "defensive_rebound_pct": baselines["defensive_rebound_pct"] * per_min("rebounds") / nba["rebounds"] * f["defensive_rebound_pct"],
        "steal_pct": baselines["steal_pct"] * per_min("steals") / nba["steals"] * f["steal_pct"],
        "block_pct": baselines["block_pct"] * per_min("blocks") / nba["blocks"] * f["block_pct"],
        "fouls_per_minute": None,  # not recorded before the draft
    }
    if trait_value(scouting, "paint_pressure") == "plus":
        translated["free_throw_attempt_rate"] *= PAINT_FTR_FACTOR
    if scouting:
        prior = (rebound_priors or {}).get(scouting["position"])
        if prior is None:
            raise ValueError(f"{record['player_id']}: missing dated position rebound prior")
        # Redistribute translated total rebounds, preserving the implied total
        # per-minute production. No second rebounding bonus from a plus trait.
        league_orb_share = source_totals["offensive_rebounds"] / (
            source_totals["offensive_rebounds"] + source_totals["defensive_rebounds"])
        translated["offensive_rebound_pct"] *= prior["offensive_share"] / league_orb_share
        translated["defensive_rebound_pct"] *= (1 - prior["offensive_share"]) / (1 - league_orb_share)
    samples = {
        "two_point_pct": raw["field_goals_attempted"] - raw["three_pointers_attempted"],
        "three_point_pct": raw["three_pointers_attempted"], "free_throw_pct": raw["free_throws_attempted"],
        "three_point_attempt_rate": raw["field_goals_attempted"], "free_throw_attempt_rate": raw["field_goals_attempted"],
        "turnovers_per_fga": raw["field_goals_attempted"],
    }
    estimated = {}
    for key in RATE_KEYS:
        value = translated[key]
        if value is None:
            estimated[key] = baselines[key]
            continue
        sample = samples.get(key, raw["minutes"]) * evidence
        prior = PRIOR_ATTEMPTS.get(key, PRIOR_MINUTES)
        estimated[key] = (value * sample + baselines[key] * prior) / (sample + prior)
    return translated, estimated, raw


def build_rookie_estimates(prospects, prospects_hash, veterans, *, scouting=None,
                           rebound_priors=None, source_hashes=None, legacy=False):
    if scouting is not None:
        validate_scouting(scouting, prospects)
    if legacy and scouting is not None:
        raise ValueError("legacy rookie estimates cannot consume scouting")
    baselines, totals = veterans["rate_baselines"], veterans["source_totals"]
    players = {}
    for record in prospects["records"]:
        if record["bbr_id"] in veterans["players"]:
            raise ValueError(f"{record['player_id']} already has an NBA record")
        entry = (scouting or {}).get("players", {}).get(record["bbr_id"])
        translated, estimated, raw = translate(record, baselines, totals, entry, rebound_priors)
        players[record["bbr_id"]] = {
            "player_name": record["player_id"], "bbr_id": record["bbr_id"], "level": record["level"],
            "school": record.get("school"), "season_end_year": 2003,
            "sample": {"games": raw["games"], "minutes": raw["minutes"], "seasons": len(record["seasons"])},
            "translated": translated, "estimated": estimated,
            "status": "estimate from pre-draft statistics; not NBA evidence",
        }
        if entry:
            players[record["bbr_id"]]["scouting"] = entry
            players[record["bbr_id"]]["style"] = style_for(entry)
    data = {
        "schema_version": 1, "model_version": LEGACY_ROOKIE_MODEL_VERSION if legacy else ROOKIE_MODEL_VERSION,
        "as_of": prospects["as_of"],
        "baseline_season": veterans["baseline_season"], "source_file": str(PROSPECTS_PATH),
        "source_sha256": prospects_hash, "veteran_model_version": veterans["model_version"],
        "method": {"recency_weights": list(RECENCY_WEIGHTS), "evidence_weight": EVIDENCE_WEIGHT,
                   "level_factors": LEVEL_FACTORS, "prior_minutes": PRIOR_MINUTES, "prior_attempts": PRIOR_ATTEMPTS,
                   "status": "provisional judgement constants; see docs/statistical_ratings.md"},
        "players": players,
    }
    if not legacy:
        data["effective_from"] = STYLE_EFFECTIVE_FROM
        data["scouting_sources"] = source_hashes or {}
        data["method"]["position_rebound_priors"] = rebound_priors or {}
        data["method"]["paint_pressure_ftr_factor"] = PAINT_FTR_FACTOR
        data["method"]["scouting_status"] = "dated qualitative priors; bounded assumptions, not fitted translations or measured tracking"
    return data


def expected_rookie_estimates(root=ROOT, *, legacy=False):
    root = Path(root)
    source_path = LEGACY_PROSPECTS_PATH if legacy else PROSPECTS_PATH
    prospects, veterans = read_json(root / source_path), read_json(root / VETERAN_PATH)
    if legacy:
        # Keep the original logical source_file and hash in the archived artifact
        # and closed packets; resolve those bytes from the immutable source copy.
        return build_rookie_estimates(prospects, sha256(root / source_path), veterans, legacy=True)
    scouting = read_json(root / SCOUTING_PATH)
    validate_scouting(scouting, prospects, root)
    priors = position_rebound_priors(read_json(root / STATS_PATH), read_json(root / POSITION_PATH))
    hashes = {str(path): sha256(root / path) for path in (SCOUTING_PATH, STATS_PATH, POSITION_PATH)}
    hashes.update({entry["source_file"]: entry["source_sha256"] for entry in scouting["players"].values()})
    return build_rookie_estimates(prospects, sha256(root / PROSPECTS_PATH), veterans,
                                  scouting=scouting, rebound_priors=priors, source_hashes=hashes)


def rookie_errors(root=ROOT):
    try:
        if read_json(Path(root) / ROOKIE_PATH) != expected_rookie_estimates(root):
            return ["generated rookie estimates are stale; run scripts/import_prospect_stats.py"]
        if read_json(Path(root) / LEGACY_ROOKIE_PATH) != expected_rookie_estimates(root, legacy=True):
            return ["archived rookie-2003.1 inputs changed; preserve closed-game evidence"]
        if sha256(Path(root) / ARCHIVED_ROOKIE_PATH) != ARCHIVED_ROOKIE_SHA256:
            return ["archived rookie-2003.2 estimates changed; preserve closed-game evidence"]
        return []
    except (OSError, ValueError, KeyError, TypeError, ZeroDivisionError) as exc:
        return [f"cannot validate rookie estimates: {exc}"]
