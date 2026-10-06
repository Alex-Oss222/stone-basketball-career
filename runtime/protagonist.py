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


# Role growth (the user's request, November 2004 on the career clock), from the 2005-06 expectation on: a player whose
# closed season scored well above the league's true shooting at his usage is given more of the offense the next season,
# and a clearly inefficient one less. Excess true shooting over the league's (the expectation's baseline season), shrunk
# by his scoring attempts against ROLE_PRIOR_ATTEMPTS, clipped to ROLE_EXCESS_LIMITS, times ROLE_SLOPE is the relative
# change in usage (0.08 above the league: +20%), bounded by USAGE_BOUNDS. More shots cost accuracy (the usage-efficiency
# trade-off): two- and three-point accuracy fall by EFFICIENCY_COST per usage point gained. Judgement constants describing
# how coaches redistribute shots; never fitted to the historical Wade. Applied to every model-built (alternate-history)
# player the same way; real players' roles already follow their real careers (talent-trajectory exception).
ROLE_GROWTH_FROM = "2005-06"
ROLE_PRIOR_ATTEMPTS = 400.0
ROLE_EXCESS_LIMITS = (-0.06, 0.08)
ROLE_SLOPE = 2.5
USAGE_BOUNDS = (0.10, 0.34)
EFFICIENCY_COST = 0.004


def league_true_shooting(source_totals):
    t = source_totals
    return t["points"] / (2 * (t["field_goals_attempted"] + .44 * t["free_throws_attempted"]))


def role_growth(rates, totals, source_totals, to_season):
    """Apply role growth to next-season `rates` in place from his closed season `totals`; returns the basis or None."""
    if to_season < ROLE_GROWTH_FROM or not totals.get("fga"):
        return None
    attempts = totals["fga"] + .44 * totals["fta"]
    pts = 2 * (totals["fgm"] - totals["tpm"]) + 3 * totals["tpm"] + totals["ftm"]
    league = league_true_shooting(source_totals)
    excess = pts / (2 * attempts) - league
    shrunk = excess * attempts / (attempts + ROLE_PRIOR_ATTEMPTS)
    clipped = min(max(shrunk, ROLE_EXCESS_LIMITS[0]), ROLE_EXCESS_LIMITS[1])
    before = rates["usage_pct"]
    after = min(max(before * (1 + ROLE_SLOPE * clipped), USAGE_BOUNDS[0]), max(USAGE_BOUNDS[1], before))
    rates["usage_pct"] = after
    gained = max(0.0, after - before) * 100
    for key in ("two_point_pct", "three_point_pct"):
        if rates.get(key) is not None:
            rates[key] *= 1 - EFFICIENCY_COST * gained
    return {"true_shooting": round(pts / (2 * attempts), 4), "league_true_shooting": round(league, 4),
            "excess_shrunk": round(shrunk, 4), "usage_before": round(before, 4), "usage_after": round(after, 4),
            "accuracy_factor": round(1 - EFFICIENCY_COST * gained, 4)}


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
    from .seasons import dates
    last_day = {"2003-04": "2004-04-14"}.get(from_season) or dates(from_season, root)["regular_season_end"]
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
    growth = role_growth(rates, season_totals(lines), ratings["source_totals"], to_season)
    payload = {"prior": prior["rates"], "games": len(lines), "to_season": to_season}
    player = {"player_name": "Dwyane Wade", "bbr_id": "wadedw01", "season_end_year": int(to_season[:4]) + 1,
              "sample": {"games": len(lines), "minutes": round(sum(p["seconds"] for p in lines) / 60, 1)},
              "estimated": rates, "basis": "runtime/protagonist.py: previous expectation + closed simulated season + age step"
              + (" + role growth" if growth else "")}
    if growth:
        player["role_growth"] = growth
    for key in ("scouting", "style"):
        if key in prior:
            player[key] = prior[key]
    out = {"schema_version": 1, "model_version": PROFILE_MODEL, "as_of": on, "season": to_season,
           "source_sha256": hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(),
           "players": {"wadedw01": player}}
    if "scouting_sources" in prior:
        out["scouting_sources"] = prior["scouting_sources"]
    return out


# -- other alternate-history players (the user's premises; trajectories.ALTERNATE_FROM) ------------------------------
ALTERNATE_PROFILE_PATH = "career/{folder}/{season}/expected_profile.json"
ALTERNATE_PLAYERS = {"boshch01": {"name": "Chris Bosh", "folder": "Chris_Bosh", "birth": date(1984, 3, 24)}}
PROFILE_WEIGHT = 1.0     # judgement (the user's premise): the user's development profile counts as one prior's weight


def target_rates(targets, prior, totals_per_minute, baselines, per_minute, observed):
    """Engine rates implied by a user target line (per game and percentages). Rates the line does not name are absent.

    Accuracy is read directly (two-point accuracy from FG% and his expected three-point share); production rates use
    the same per-minute translation as `observed_rates`; usage scales his observed usage by the target points per
    minute over his observed points per minute, divided by the ratio of target to observed true shooting (more
    efficient scoring needs fewer possessions). Approximations, documented, applied the same way for every season."""
    out = {}
    mpg = targets.get("mpg")
    if targets.get("ft_pct") is not None:
        out["free_throw_pct"] = targets["ft_pct"]
    if targets.get("three_pct") is not None:
        out["three_point_pct"] = targets["three_pct"]
    if targets.get("fg_pct") is not None and targets.get("three_pct") is not None:
        r = prior["three_point_attempt_rate"]
        out["two_point_pct"] = (targets["fg_pct"] - r * targets["three_pct"]) / (1 - r) if r < 1 else prior["two_point_pct"]
    if not mpg:
        return out
    for key, stat, rate in (("assist_pct", "ast", "assists"), ("steal_pct", "stl", "steals"), ("block_pct", "blk", "blocks")):
        if targets.get(stat) is not None:
            out[key] = baselines[key] * targets[stat] / mpg / per_minute[rate]
    if targets.get("reb") is not None and totals_per_minute.get("reb"):
        share = totals_per_minute["orb"] / totals_per_minute["reb"]
        out["offensive_rebound_pct"] = baselines["offensive_rebound_pct"] * targets["reb"] * share / mpg / per_minute["offensive_rebounds"]
        out["defensive_rebound_pct"] = baselines["defensive_rebound_pct"] * targets["reb"] * (1 - share) / mpg / per_minute["defensive_rebounds"]
    if targets.get("pts") is not None and totals_per_minute.get("pts") and observed.get("usage_pct"):
        ts_ratio = (targets["ts_pct"] / totals_per_minute["ts"]) if targets.get("ts_pct") and totals_per_minute.get("ts") else 1.0
        out["usage_pct"] = observed["usage_pct"] * (targets["pts"] / mpg) / totals_per_minute["pts"] / ts_ratio
    return out


def build_alternate_profile(root, bbr_id, from_season, to_season, on=None, targets=None):
    """An alternate-history player's expected profile for `to_season`: his `from_season` expectation (his real path while
    that season was real for him), his closed simulated box lines, the generic age step, and the user's target line
    for `to_season` (`targets`) at PROFILE_WEIGHT. The engine then draws the season's swing (trajectories.alternate)."""
    import hashlib
    import json
    from pathlib import Path
    from .player_stats import SEASON_SOURCES, load_rating_index, read_json
    from .seasons import dates
    from .write_back import closed_results
    meta = ALTERNATE_PLAYERS[bbr_id]
    root = Path(root)
    src = SEASON_SOURCES[from_season]
    last_day = dates(from_season, root)["regular_season_end"]
    prior_profile = load_rating_index(last_day, from_season, root).engine_profile(meta["name"], bbr_id)
    prior = prior_profile["rates"]
    ratings = read_json(root / src["ratings"])
    lines = []
    for row in closed_results(root, from_season, on):
        r = row["result"]
        for side in ("home", "away"):
            lines += [p for p in r["player_stats"][side] if p["player_id"] == meta["name"] and p.get("seconds")]
    age = season_age(to_season, meta["birth"])
    production, accuracy = age_step(age)
    t = season_totals(lines)
    per_minute = league_per_minute(ratings["source_totals"])
    observed, samples = observed_rates(t, ratings["rate_baselines"], per_minute)
    out = {}
    for key in RATE_KEYS:                     # next_season_rates with his own birth date
        value, p = observed[key], prior[key]
        if value is not None:
            weight = PRIOR_ATTEMPTS.get(key, PRIOR_MINUTES)
            p = (value * samples[key] + p * weight) / (samples[key] + weight)
        p = p * accuracy if key in ACCURACY else p * production if key in PRODUCTION else p / production if key in INVERSE else p
        out[key] = min(p, 0.99) if key in ACCURACY else p
    growth = role_growth(out, t, ratings["source_totals"], to_season)
    minutes = t["seconds"] / 60
    pts = 2 * (t["fgm"] - t["tpm"]) + 3 * t["tpm"] + t["ftm"]
    reb = t["orb"] + t["drb"]
    totals_pm = {"reb": reb, "orb": t["orb"], "pts": pts / minutes if minutes else None,
                 "ts": pts / (2 * (t["fga"] + .44 * t["fta"])) if t["fga"] else None}
    pulled = {}
    if targets:
        pulled = target_rates(targets, out, totals_pm, ratings["rate_baselines"], per_minute, observed)
        for key, target in pulled.items():
            out[key] = (out[key] + PROFILE_WEIGHT * target) / (1 + PROFILE_WEIGHT)
            if key in ACCURACY:
                out[key] = min(out[key], 0.99)
    payload = {"prior": prior, "games": len(lines), "to_season": to_season, "targets": targets}
    player = {"player_name": meta["name"], "bbr_id": bbr_id, "season_end_year": int(to_season[:4]) + 1,
              "sample": {"games": len(lines), "minutes": round(minutes, 1)}, "estimated": out,
              "target_rates": pulled, "profile_weight": PROFILE_WEIGHT,
              "basis": ("runtime/protagonist.py build_alternate_profile: previous expectation + closed simulated season + "
                        "age step + the user's development profile target line at PROFILE_WEIGHT")}
    if growth:
        player["role_growth"] = growth
    if "defense" in prior_profile:
        player["defense"] = prior_profile["defense"]
    return {"schema_version": 1, "model_version": PROFILE_MODEL, "as_of": on, "season": to_season,
            "source_sha256": hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(),
            "players": {bbr_id: player}}
