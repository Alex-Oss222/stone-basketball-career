"""The engine's All-Star weekend inputs: the exhibition rules, the exhibition environment and every player's profile.

The Rookie Challenge and the All-Star Game (`runtime/era.EXHIBITION_GAME_TYPES`) are played by the same kernel as an NBA
game, as the FIBA games are (`runtime/national_engine.py`); only their inputs differ, and each is fixed before the game
from dated sources, never from the game itself:

* Rules: `era.exhibition_rules(game_type, game_date)`: the All-Star Game is a standard NBA game; the Rookie Challenge
  two 20-minute halves with 2-minute overtimes, fouls counted but no foul-outs.
* Environment: the real editions of the same game published before it (the five most recent All-Star Games, 1999 had
  none; the Rookies-versus-Sophomores games from 2001, up to five), their team totals per 48 or per 40 minutes, built
  into `library/all_star/engine/<season>-<game_type>.json` by `scripts/build_all_star_engine.py`. Team turnovers are
  0 (the published team totals equal the players' sums). The environment's `defense_intensity` is 0: the translation is
  fitted on real exhibition games and already contains the defense actually played in them, so the five defenders'
  individual values (`kernel.calibrate`) would count it twice.
* Players: each player reads exactly the profile an NBA game on that date reads (`player_stats.load_rating_index`:
  Wade's rookie estimate in 2003-04 and his protagonist profile after it, a real player's trajectory with feedback, an
  alternate-history player's own expectation), translated into exhibition terms by shifts fitted on the real editions'
  players against their own seasons (anchors): a logit shift for two-point, three-point and free-throw percentages, a
  ratio for every other rate. He keeps the season's journaled development swing (`trajectories.development_refs`
  returns the season's existing event), so no new swing is drawn.

The engine validates every exhibition profile in a packet against `expected_profile`, so a packet built from anything
else is refused, as for NBA and FIBA games.
"""
import json
import math
from functools import lru_cache
from pathlib import Path

from .era import EXHIBITION_GAME_TYPES, exhibition_rules, season_for_date   # noqa: F401  (re-exported)

ROOT = Path(__file__).resolve().parents[1]
ENGINE_DIR = Path("library/all_star/engine")
MODEL_VERSION = "all-star-2006.1"
SHIFT_KEYS = ("two_point_pct", "three_point_pct", "free_throw_pct")    # logit shifts
RATIO_KEYS = ("three_point_attempt_rate", "free_throw_attempt_rate", "turnovers_per_fga", "fouls_per_minute",
              "usage_pct", "assist_pct", "offensive_rebound_pct", "defensive_rebound_pct", "steal_pct", "block_pct")
THREE_RATE_CAP = 0.9                   # as the FIBA translation (`national_engine.translate`)


def is_exhibition(game_type):
    return game_type in EXHIBITION_GAME_TYPES


@lru_cache(maxsize=32)
def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def engine_path(season, game_type):
    return ENGINE_DIR / f"{season}-{game_type}.json"


def edition(game_type, game_date, root=ROOT):
    """The built engine file of the game on the date (`scripts/build_all_star_engine.py`); fails closed without one."""
    season = season_for_date(game_date)
    path = Path(root) / engine_path(season, game_type)
    if not path.is_file():
        raise ValueError(f"no {game_type} engine file for {season} (scripts/build_all_star_engine.py)")
    data = _read(str(path))
    if data["game_type"] != game_type or data["game_date"] != game_date:
        raise ValueError(f"{path.name} is built for {data['game_type']} on {data['game_date']}, not {game_type} on {game_date}")
    return data


def exhibition_environment(game_type, game_date, root=ROOT):
    """The engine environment for the game: the real earlier editions' averages, gated by publication."""
    env = edition(game_type, game_date, root)["environment"]
    if env["published_after"] > game_date:
        raise ValueError(f"{env['season']} averages are not published as of {game_date}")
    return env


def exhibition_spatial(game_date, root=ROOT):
    """Shot locations: the NBA distance-band shape of the season, on the NBA court."""
    from .spatial_shots import load_spatial_environment
    return load_spatial_environment(season_for_date(game_date), game_date, root)


def _logit(p):
    p = min(1 - 1e-6, max(1e-6, p))
    return math.log(p / (1 - p))


def _inv(x):
    return 1 / (1 + math.exp(-x))


def translate(profile, translation):
    """An NBA profile in exhibition terms: shooting percentages moved by a logit shift, the other rates by a ratio
    (`translation`, fitted on anchors by scripts/build_all_star_engine.py). Defense and identity fields are kept."""
    if not profile:
        return {}
    rates = dict(profile["rates"])
    for k in SHIFT_KEYS:
        rates[k] = _inv(_logit(rates[k]) + translation["shift"][k])
    for k in RATIO_KEYS:
        rates[k] = rates[k] * translation["ratio"][k]
    rates["three_point_attempt_rate"] = min(THREE_RATE_CAP, rates["three_point_attempt_rate"])
    return dict(profile, rates={k: round(v, 6) for k, v in rates.items()}, exhibition_model=translation["model_version"])


def nba_profile(bbr_id, game_date, root=ROOT):
    """The player's NBA profile on the date, as an NBA game that day reads it ({} when there is none)."""
    from .player_stats import load_rating_index
    index = load_rating_index(game_date, season_for_date(game_date), root)
    return index.engine_profile(bbr_id, bbr_id) if index is not None else {}


def expected_profile(profile, game_type, game_date, root=ROOT):
    """The profile an exhibition packet must carry for this player (before his journaled development swing)."""
    base = nba_profile(profile.get("bbr_id"), game_date, root)
    if not base:
        raise ValueError(f"{profile.get('bbr_id')}: no NBA profile on {game_date}; an exhibition needs every player's")
    return translate(base, edition(game_type, game_date, root)["translation"])
