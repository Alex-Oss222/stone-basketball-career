"""Wade's ability from one season to the next.

Wade's career is alternate history, so no real trajectory applies to him. His
next-season expected rates combine:

1. his previous expected rates, used as the prior;
2. his simulated season, read from closed game results (box-score lines), with
   the same sample priors the veteran estimates use, so a short season moves
   him less than a full one;
3. an age step for the age he reaches in the new season.

The engine then draws the new season's swing around that expectation
(`runtime/trajectories.py`). Only simulated evidence enters; the historical
Wade's statistics never do.

The age steps are provisional judgement constants describing a typical
development curve. They are not fitted, and must never be tuned toward the
historical Wade's career.
"""
from datetime import date

from .player_stats import PRIOR_ATTEMPTS, PRIOR_MINUTES, RATE_KEYS

PROTAGONIST_BIRTH_DATE = date(1984, 1, 17)
BOX_KEYS = ("seconds", "fgm", "fga", "tpm", "tpa", "ftm", "fta", "orb", "drb", "ast", "stl", "blk", "tov", "pf")
ACCURACY = ("two_point_pct", "three_point_pct", "free_throw_pct")
PRODUCTION = ("usage_pct", "assist_pct", "offensive_rebound_pct", "defensive_rebound_pct", "steal_pct", "block_pct")
INVERSE = ("turnovers_per_fga", "fouls_per_minute")   # lower is better; development reduces them
# (maximum age, production multiplier, accuracy multiplier). Age is taken on February 1 of the season.
AGE_STEPS = ((21, 1.05, 1.015), (24, 1.03, 1.01), (27, 1.01, 1.005), (30, 1.00, 1.000),
             (33, 0.97, 0.995), (99, 0.94, 0.990))


def season_age(season, birth=PROTAGONIST_BIRTH_DATE):
    feb1 = date(int(season[:4]) + 1, 2, 1)
    return feb1.year - birth.year - ((feb1.month, feb1.day) < (birth.month, birth.day))


def age_step(age):
    return next((prod, acc) for limit, prod, acc in AGE_STEPS if age <= limit)


def season_totals(lines):
    """Sum box-score lines (the `player_stats` rows of closed game results)."""
    return {k: sum(line[k] for line in lines) for k in BOX_KEYS}


def observed_rates(t, baselines, per_minute):
    """Season rates comparable to the engine's. Production rates are relative per-minute output
    times the league baseline, the same translation the rookie model uses, with no level factor."""
    minutes = t["seconds"] / 60
    if minutes <= 0:
        return {k: None for k in RATE_KEYS}, {}
    two_a = t["fga"] - t["tpa"]
    usage = (t["fga"] + .44 * t["fta"] + t["tov"]) / minutes
    ratio = lambda num, den: num / den if den else None
    rates = {
        "two_point_pct": ratio(t["fgm"] - t["tpm"], two_a),
        "three_point_pct": ratio(t["tpm"], t["tpa"]),
        "free_throw_pct": ratio(t["ftm"], t["fta"]),
        "three_point_attempt_rate": ratio(t["tpa"], t["fga"]),
        "free_throw_attempt_rate": ratio(t["fta"], t["fga"]),
        "turnovers_per_fga": ratio(t["tov"], t["fga"]),
        "usage_pct": baselines["usage_pct"] * usage / per_minute["usage"],
        "assist_pct": baselines["assist_pct"] * t["ast"] / minutes / per_minute["assists"],
        "offensive_rebound_pct": baselines["offensive_rebound_pct"] * t["orb"] / minutes / per_minute["offensive_rebounds"],
        "defensive_rebound_pct": baselines["defensive_rebound_pct"] * t["drb"] / minutes / per_minute["defensive_rebounds"],
        "steal_pct": baselines["steal_pct"] * t["stl"] / minutes / per_minute["steals"],
        "block_pct": baselines["block_pct"] * t["blk"] / minutes / per_minute["blocks"],
        "fouls_per_minute": t["pf"] / minutes,
    }
    samples = {"two_point_pct": two_a, "three_point_pct": t["tpa"], "free_throw_pct": t["fta"],
               "three_point_attempt_rate": t["fga"], "free_throw_attempt_rate": t["fga"], "turnovers_per_fga": t["fga"]}
    return rates, {k: samples.get(k, minutes) for k in RATE_KEYS}


def league_per_minute(source_totals):
    m, t = source_totals["minutes"], source_totals
    return {"usage": (t["field_goals_attempted"] + .44 * t["free_throws_attempted"] + t["turnovers"]) / m,
            "assists": t["assists"] / m, "offensive_rebounds": t["offensive_rebounds"] / m,
            "defensive_rebounds": t["defensive_rebounds"] / m, "steals": t["steals"] / m, "blocks": t["blocks"] / m}


def next_season_rates(prior_rates, lines, next_season, baselines, source_totals):
    """Expected rates for `next_season` from last season's expectation and simulated play."""
    observed, samples = observed_rates(season_totals(lines), baselines, league_per_minute(source_totals))
    production, accuracy = age_step(season_age(next_season))
    out = {}
    for key in RATE_KEYS:
        prior = prior_rates[key]
        value = observed[key]
        if value is not None:
            weight = PRIOR_ATTEMPTS.get(key, PRIOR_MINUTES)
            prior = (value * samples[key] + prior * weight) / (samples[key] + weight)
        if key in ACCURACY:
            prior *= accuracy
        elif key in PRODUCTION:
            prior *= production
        elif key in INVERSE:
            prior /= production
        out[key] = min(prior, 0.99) if key in ACCURACY else prior
    return out


from .prospects import PROTAGONIST_MODEL_VERSION as PROFILE_MODEL


def build_profile(root, from_season="2003-04", to_season="2004-05", on=None):
    """Wade's expected profile for `to_season` (roadmap 18): his `from_season` expectation, his closed simulated
    regular-season box lines, and the generic age step; written beside the season as a one-player rookie-shaped file
    that `player_stats.load_rating_index` reads. The engine then draws the season's development swing."""
    import hashlib
    import json
    from pathlib import Path
    from .player_stats import SEASON_SOURCES, load_rating_index, read_json
    from .write_back import closed_results
    root = Path(root)
    src = SEASON_SOURCES[from_season]
    # The expectation in force at the season's last regular-season game: for 2003-04 the rookie-2003.3 estimate built
    # from the Player Profile (its scouting traits and shot style carry forward unchanged; only rates are updated).
    last_day = {"2003-04": "2004-04-14"}[from_season]
    index = load_rating_index(last_day, from_season, root)
    prior = index.engine_profile("Dwyane Wade", "wadedw01")
    ratings = read_json(root / src["ratings"])
    lines = []
    for row in closed_results(root, from_season, on):
        r = row["result"]
        for side in ("home", "away"):
            if r[side] == "Miami Heat":
                lines += [p for p in r["player_stats"][side] if p["player_id"] == "Dwyane Wade" and p.get("seconds")]
    rates = next_season_rates(prior["rates"], lines, to_season, ratings["rate_baselines"], ratings["source_totals"])
    payload = {"prior": prior["rates"], "games": len(lines), "to_season": to_season}
    player = {"player_name": "Dwyane Wade", "bbr_id": "wadedw01", "season_end_year": int(to_season[:4]) + 1,
              "sample": {"games": len(lines), "minutes": round(sum(p["seconds"] for p in lines) / 60, 1)},
              "estimated": rates, "basis": "runtime/protagonist.py: previous expectation + closed simulated season + age step"}
    for key in ("scouting", "style"):
        if key in prior:
            player[key] = prior[key]
    out = {"schema_version": 1, "model_version": PROFILE_MODEL, "as_of": on, "season": to_season,
           "source_sha256": hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(),
           "players": {"wadedw01": player}}
    if "scouting_sources" in prior:
        out["scouting_sources"] = prior["scouting_sources"]
    return out
