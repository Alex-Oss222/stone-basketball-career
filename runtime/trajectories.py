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
"""
import hashlib
import math
from pathlib import Path

from .player_stats import PRIOR_MINUTES, RATE_KEYS, ROOT, read_json, sha256

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
            if set(row) != {"minutes", "rates"} or set(row["rates"]) != set(RATE_KEYS):
                errors.append(f"{bbr_id} {season}: needs minutes and exactly the engine rate keys")
                continue
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


def swings(refs):
    """Persistent log-scale swing per rate for the latest season in `refs`."""
    z = None
    for season in sorted(refs):
        draw = _normals(refs[season], len(RATE_KEYS))
        # Stationary AR(1): full spread in the first season, PERSISTENCE carry-over afterwards.
        z = draw if z is None else [PERSISTENCE * old + math.sqrt(1 - PERSISTENCE ** 2) * new
                                    for old, new in zip(z, draw)]
    return dict(zip(RATE_KEYS, z))


def develop(rates, refs):
    z = swings(refs)
    out = {}
    for key, value in rates.items():
        moved = value * math.exp(SPREAD[key] * z[key])
        out[key] = min(moved, 0.99 if CAPS.get(key, 1) == 1 else CAPS[key])
    return out


class Trajectories:
    def __init__(self, data, data_hash):
        self.data, self.hash = data, data_hash

    def has(self, bbr_id, season):
        return season in self.data["players"].get(bbr_id, {}).get("seasons", {})

    def expected_profile(self, bbr_id, season, baselines):
        row = self.data["players"][bbr_id]["seasons"][season]
        return {"bbr_id": bbr_id, "model_version": TRAJECTORY_MODEL_VERSION, "as_of": season,
                "season_end_year": int(season[:4]) + 1, "source_sha256": self.hash,
                "rates": expected_rates(row, baselines)}


def load_trajectories(root=ROOT):
    path = Path(root) / CAREERS_PATH
    if not path.exists():
        return None
    data = read_json(path)
    errors = careers_errors(data)
    if errors:
        raise ValueError("; ".join(errors[:5]))
    return Trajectories(data, sha256(path))


def trajectory_errors(root=ROOT):
    path = Path(root) / CAREERS_PATH
    if not path.exists():
        return []
    try:
        return [f"{CAREERS_PATH}: {e}" for e in careers_errors(read_json(path))]
    except (OSError, ValueError) as exc:
        return [f"{CAREERS_PATH}: {exc}"]
