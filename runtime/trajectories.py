"""Hybrid talent trajectories (option C).

A real player's ability in a season follows his real career: his real rates for
that season, shrunk toward the league baseline by minutes, are the *expected*
path. Around it the engine draws a development swing per player and season.
Swings persist from year to year (a breakout or a slump carries partly into the
next season), so the simulated league tracks history without copying it.

Scope of the hindsight exception (see AGENTS.md): only ability rates enter.
Results, standings, awards, injuries, transactions and team decisions from
real history never do, and nothing here is shown to the front office or on
player cards. The protagonist is fictional and never has a trajectory.

The swing draws come from the private engine journal (one event per player and
season), exactly like game draws, so they cannot be chosen or re-rolled.

Defense: the real season's Defensive Box Plus/Minus (DBPM, points per 100
possessions against a league-average defender), shrunk toward average by
minutes, is the expected defensive value; the swing moves it additively.

Feedback: from the second simulated season on, a real player's expected rates
may carry 20% of his last simulated season's surprise (simulated rates against
that season's expected rates), shrunk by sample size and capped at one season's
swing spread. Each season's adjustment replaces the last one, so it cannot
accumulate. It reads only closed simulated results.
"""
import hashlib
import math
from pathlib import Path

from .player_stats import PRIOR_ATTEMPTS, PRIOR_MINUTES, RATE_KEYS, ROOT, read_json, sha256

TRAJECTORY_MODEL_VERSION = "trajectory-hybrid.1"
CAREERS_PATH = Path("library/careers/nba_player_careers.json")
PROTAGONIST_IDS = {"wadedw01"}   # the career's Wade is alternate history
FIRST_SEASON = "2003-04"
PERSISTENCE = 0.5                # share of last season's swing that carries over
# Log-scale spread of a season's swing around the real path. Judgement constants:
# shooting accuracy moves less than volume and production rates.
SPREAD = {
    "two_point_pct": 0.03, "three_point_pct": 0.05, "free_throw_pct": 0.02,
    "three_point_attempt_rate": 0.10, "free_throw_attempt_rate": 0.10, "turnovers_per_fga": 0.08,
    "usage_pct": 0.06, "assist_pct": 0.08, "offensive_rebound_pct": 0.08, "defensive_rebound_pct": 0.06,
    "steal_pct": 0.10, "block_pct": 0.12, "fouls_per_minute": 0.08,
}
CAPS = {"free_throw_attempt_rate": 10, "turnovers_per_fga": 10, "fouls_per_minute": 10}
# Defense (DBPM scale): additive swing in points per 100 possessions, a judgement constant.
DEFENSE_SPREAD = 0.5
DBPM_LIMIT = 50                  # raw DBPM of tiny samples can reach about +-30
FEEDBACK_SHARE = 0.2             # share of last simulated season's surprise carried into the next
FEEDBACK_KIND = "trajectory_feedback"


def season_list(first, last):
    out, year = [], int(first[:4])
    while year <= int(last[:4]):
        out.append(f"{year}-{str(year + 1)[-2:]}")
        year += 1
    return out


def careers_errors(data):
    errors = []
    if data.get("kind") != "player_career_rates" or not isinstance(data.get("players"), dict):
        return ["careers file must have kind player_career_rates and a players object"]
    for bbr_id, player in data["players"].items():
        if bbr_id in PROTAGONIST_IDS:
            errors.append(f"{bbr_id}: the protagonist is alternate history and cannot have a real trajectory")
        for season, row in player.get("seasons", {}).items():
            if set(row) != {"minutes", "rates", "dbpm"} or set(row["rates"]) != set(RATE_KEYS):
                errors.append(f"{bbr_id} {season}: needs minutes, dbpm and exactly the engine rate keys")
                continue
            dbpm = row["dbpm"]
            if dbpm is not None and (isinstance(dbpm, bool) or not isinstance(dbpm, (int, float))
                                     or not math.isfinite(dbpm) or abs(dbpm) > DBPM_LIMIT):
                errors.append(f"{bbr_id} {season}: invalid dbpm")
            for key, value in row["rates"].items():
                if value is not None and not (isinstance(value, (int, float)) and 0 <= value <= CAPS.get(key, 1)):
                    errors.append(f"{bbr_id} {season}: invalid {key}")
            if row["minutes"] is None or row["minutes"] < 0:
                errors.append(f"{bbr_id} {season}: invalid minutes")
    return errors


def expected_rates(row, baselines):
    """Real season rates shrunk toward the baseline by minutes; missing rates use the baseline."""
    minutes = row["minutes"]
    return {key: (baselines[key] if value is None else
                  (value * minutes + baselines[key] * PRIOR_MINUTES) / (minutes + PRIOR_MINUTES))
            for key, value in row["rates"].items()}


def expected_defense(row):
    """Real DBPM shrunk toward league average (0) by minutes; a missing value is average."""
    if row.get("dbpm") is None:
        return 0.0
    return row["dbpm"] * row["minutes"] / (row["minutes"] + PRIOR_MINUTES)


def _normals(ref, count):
    """Deterministic standard normals from an opaque 64-hex event reference (Box-Muller)."""
    out, counter = [], 0
    while len(out) < count:
        block = hashlib.sha256(bytes.fromhex(ref) + counter.to_bytes(4, "big")).digest()
        for i in range(0, 32, 16):
            u1 = (int.from_bytes(block[i:i + 8], "big") + 1) / (2 ** 64 + 1)
            u2 = int.from_bytes(block[i + 8:i + 16], "big") / 2 ** 64
            radius = math.sqrt(-2 * math.log(u1))
            out += [radius * math.cos(2 * math.pi * u2), radius * math.sin(2 * math.pi * u2)]
        counter += 1
    return out[:count]


def development_packet(bbr_id, season):
    return {"event_id": f"development:{season}:{bbr_id}", "procedure": TRAJECTORY_MODEL_VERSION,
            "bbr_id": bbr_id, "season": season}


def needs_development(profile):
    """Real-career players and the protagonist both get an engine-drawn swing each season."""
    return profile.get("model_version") == TRAJECTORY_MODEL_VERSION or profile.get("bbr_id") in PROTAGONIST_IDS


def development_seasons(bbr_id, season):
    """Real players' swings persist, so their chain starts at FIRST_SEASON. The protagonist's
    simulated seasons already carry last year's swing into his next estimate, so he gets only
    the current season's draw; chaining it again would count it twice."""
    return [season] if bbr_id in PROTAGONIST_IDS else season_list(FIRST_SEASON, season)


def development_refs(journal, bbr_id, season):
    """Journal (idempotently) one development event per required season."""
    return {s: journal.close_event(development_packet(bbr_id, s)) for s in development_seasons(bbr_id, season)}


SWING_KEYS = RATE_KEYS + ("defense",)   # appended last, so the rate draws are unchanged


def swings(refs):
    """Persistent standard-normal swing per rate (and defense) for the latest season in `refs`."""
    z = None
    for season in sorted(refs):
        draw = _normals(refs[season], len(SWING_KEYS))
        # Stationary AR(1): full spread in the first season, PERSISTENCE carry-over afterwards.
        z = draw if z is None else [PERSISTENCE * old + math.sqrt(1 - PERSISTENCE ** 2) * new
                                    for old, new in zip(z, draw)]
    return dict(zip(SWING_KEYS, z))


def develop(rates, refs):
    z = swings(refs)
    out = {}
    for key, value in rates.items():
        moved = value * math.exp(SPREAD[key] * z[key])
        out[key] = min(moved, 0.99 if CAPS.get(key, 1) == 1 else CAPS[key])
    return out


def develop_profile(profile, refs):
    """The profile moved by its journaled swings: rates multiplicatively, defense additively."""
    out = dict(profile, rates=develop(profile["rates"], refs), development=refs)
    if "defense" in profile:
        out["defense"] = profile["defense"] + DEFENSE_SPREAD * swings(refs)["defense"]
    return out


def _shrunk(observed, expected, sample, prior):
    return (observed * sample + expected * prior) / (sample + prior)


def feedback_adjustments(expected, observed, samples):
    """Log-scale shift per rate for a real player's next season.

    `expected` are the rates the engine expected for the simulated season (before
    its swing), `observed` his simulated rates from closed results, `samples` their
    sample sizes. The observed rate is first shrunk toward the expectation with
    the veteran-model priors, so a short season moves him little; 20% of the
    remaining log surprise is kept, capped at one season's swing spread.
    """
    out = {}
    for key in RATE_KEYS:
        value, base = observed.get(key), expected[key]
        if value is None or base <= 0 or not samples.get(key):
            out[key] = 0.0
            continue
        shrunk = _shrunk(value, base, samples[key], PRIOR_ATTEMPTS.get(key, PRIOR_MINUTES))
        shift = FEEDBACK_SHARE * math.log(max(shrunk, 1e-9) / base)
        out[key] = max(-SPREAD[key], min(SPREAD[key], shift))
    return out


def apply_feedback(rates, adjustments):
    return {key: min(value * math.exp(adjustments.get(key, 0.0)), 0.99 if CAPS.get(key, 1) == 1 else CAPS[key])
            for key, value in rates.items()}


def season_feedback(lines_by_player, expected_by_player, baselines, from_season, applies_to):
    """Feedback file content from a closed simulated season (run at rollover, roadmap item 18).

    `lines_by_player`: bbr_id -> that player's box-score lines from every closed game.
    `expected_by_player`: bbr_id -> the rates the engine expected for him that season before
    its swing, i.e. `expected_profile(...)["rates"]` including that season's own feedback.
    League per-minute rates come from the same simulated games.
    """
    from .protagonist import BOX_KEYS, observed_rates, season_totals
    every = [line for lines in lines_by_player.values() for line in lines]
    league = {k: sum(line[k] for line in every) for k in BOX_KEYS}
    minutes = league["seconds"] / 60
    per_minute = {"usage": (league["fga"] + .44 * league["fta"] + league["tov"]) / minutes,
                  "assists": league["ast"] / minutes, "offensive_rebounds": league["orb"] / minutes,
                  "defensive_rebounds": league["drb"] / minutes, "steals": league["stl"] / minutes,
                  "blocks": league["blk"] / minutes}
    players = {}
    for bbr_id, lines in sorted(lines_by_player.items()):
        if bbr_id in PROTAGONIST_IDS or bbr_id not in expected_by_player:
            continue
        totals = season_totals(lines)
        observed, samples = observed_rates(totals, baselines, per_minute)
        players[bbr_id] = {"minutes": round(totals["seconds"] / 60, 1),
                           "adjust": feedback_adjustments(expected_by_player[bbr_id], observed, samples)}
    return {"schema_version": 1, "kind": FEEDBACK_KIND, "from_season": from_season, "applies_to": applies_to,
            "share": FEEDBACK_SHARE, "source": "closed simulated game results of the from_season",
            "players": players}


def feedback_errors(data):
    if data.get("kind") != FEEDBACK_KIND or data.get("share") != FEEDBACK_SHARE or not isinstance(data.get("players"), dict):
        return ["feedback file must have kind trajectory_feedback, the current share and a players object"]
    errors = []
    for bbr_id, entry in data["players"].items():
        if bbr_id in PROTAGONIST_IDS:
            errors.append(f"{bbr_id}: the protagonist has his own season update, not real-player feedback")
        adjust = entry.get("adjust", {})
        if set(adjust) != set(RATE_KEYS) or any(
                isinstance(v, bool) or not isinstance(v, (int, float)) or abs(v) > SPREAD[k] + 1e-12
                for k, v in adjust.items()):
            errors.append(f"{bbr_id}: adjustments must cover every rate and stay within the cap")
    return errors


class Trajectories:
    def __init__(self, data, data_hash, feedback=None, feedback_hash=None):
        self.data, self.hash = data, data_hash
        self.feedback, self.feedback_hash = feedback, feedback_hash

    def has(self, bbr_id, season):
        return season in self.data["players"].get(bbr_id, {}).get("seasons", {})

    def expected_profile(self, bbr_id, season, baselines):
        row = self.data["players"][bbr_id]["seasons"][season]
        profile = {"bbr_id": bbr_id, "model_version": TRAJECTORY_MODEL_VERSION, "as_of": season,
                   "season_end_year": int(season[:4]) + 1, "source_sha256": self.hash,
                   "rates": expected_rates(row, baselines), "defense": expected_defense(row)}
        entry = (self.feedback or {}).get("players", {}).get(bbr_id)
        if entry and self.feedback.get("applies_to") == season:
            profile["rates"] = apply_feedback(profile["rates"], entry["adjust"])
            profile["feedback_sha256"] = self.feedback_hash
        return profile


def feedback_path(season):
    """Feedback for `season`, written at rollover from the season before (simulation-owned)."""
    return Path(f"career/Dwyane_Wade/{season}/trajectory_feedback.json")


def load_trajectories(root=ROOT, season=None):
    path = Path(root) / CAREERS_PATH
    if not path.exists():
        return None
    data = read_json(path)
    errors = careers_errors(data)
    if errors:
        raise ValueError("; ".join(errors[:5]))
    feedback = feedback_hash = None
    if season is not None and (Path(root) / feedback_path(season)).exists():
        feedback = read_json(Path(root) / feedback_path(season))
        errors = feedback_errors(feedback)
        if errors or feedback.get("applies_to") != season or season_list(FIRST_SEASON, season)[-2:-1] != [feedback.get("from_season")]:
            raise ValueError(f"{feedback_path(season)}: " + "; ".join(errors or ["wrong seasons"]))
        feedback_hash = sha256(Path(root) / feedback_path(season))
    return Trajectories(data, sha256(path), feedback, feedback_hash)


def trajectory_errors(root=ROOT):
    path = Path(root) / CAREERS_PATH
    if not path.exists():
        return []
    try:
        return [f"{CAREERS_PATH}: {e}" for e in careers_errors(read_json(path))]
    except (OSError, ValueError) as exc:
        return [f"{CAREERS_PATH}: {exc}"]
