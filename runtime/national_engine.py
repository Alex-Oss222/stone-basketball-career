"""The engine's national-team inputs: FIBA rules, the FIBA environment and every player's FIBA profile.

A national game (FIBA rules, `runtime/era.NATIONAL_GAME_TYPES`) is played by the same kernel as an NBA game; only its
inputs differ, and each is fixed before the event from dated sources, never from the event itself:

* Rules: `era.national_rules(game_date)`: four ten-minute quarters, five fouls, the FIBA three-point line of the date.
* Environment: the previous senior FIBA tournament's real per-game averages (the repository's policy: a competition is
  calibrated on the real averages of the one before it), published before the game date. Built into
  `library/fiba/engine/<edition>.json` by `scripts/build_fiba_engine.py`, with the translation below.
* Players:
  - an NBA player (or Wade) reads his expected profile for the ability season (`era.ability_season`: the season just
    closed for a summer event), exactly as the NBA engine would, then translated into FIBA terms by shifts fitted on
    the players who played both an NBA season and the FIBA tournaments that followed it (anchors), and gets his
    journaled development swing for that season like any NBA game;
  - any other player reads his FIBA profile from his real statistics in the senior FIBA tournaments he played before
    the event, shrunk toward a replacement prior by minutes; a player with no record plays at that prior.
  Defense: an NBA player's DBPM as in the NBA; any other player a share of his national team's defensive margin in
  those tournaments (team points allowed per 100 possessions against the tournament average, over five).

The engine validates every national profile in a packet against `expected_profile`, so a packet built from anything
else is refused, as for NBA games.
"""
import json
import math
from functools import lru_cache
from pathlib import Path

from .era import NATIONAL_GAME_TYPES, ability_season, national_rules   # noqa: F401  (re-exported)

ROOT = Path(__file__).resolve().parents[1]
ENGINE_DIR = Path("library/fiba/engine")
from .kernel import FIBA_MODEL_VERSION                                  # noqa: E402
PCT_KEYS = ("two_point_pct", "three_point_pct", "free_throw_pct")
SHIFT_KEYS = ("two_point_pct", "three_point_pct")            # logit shifts (free-throw distance is the same)
RATIO_KEYS = ("three_point_attempt_rate", "free_throw_attempt_rate", "turnovers_per_fga", "usage_pct", "assist_pct",
              "offensive_rebound_pct", "defensive_rebound_pct", "steal_pct", "block_pct", "fouls_per_minute")


def is_national(game_type):
    return game_type in NATIONAL_GAME_TYPES


@lru_cache(maxsize=32)
def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def editions(root=ROOT):
    """Every built edition: {edition id: engine file data}."""
    folder = Path(root) / ENGINE_DIR
    return {p.stem: _read(str(p)) for p in sorted(folder.glob("*.json"))} if folder.is_dir() else {}


def edition_on(game_date, root=ROOT):
    """The built edition whose dates contain the game date."""
    hits = [e for e in editions(root).values() if e["first_game"] <= game_date <= e["last_game"]]
    if len(hits) != 1:
        raise ValueError(f"no single FIBA edition is built for {game_date} (scripts/build_fiba_engine.py)")
    return hits[0]


def national_environment(game_date, root=ROOT):
    """The engine environment for a national game: the previous tournament's averages, gated by publication."""
    e = edition_on(game_date, root)
    env = e["environment"]
    if env["published_after"] > game_date:
        raise ValueError(f"{env['baseline']} averages are not published as of {game_date}")
    return env


def national_spatial(game_date, root=ROOT):
    """Shot locations: the NBA distance-band shape used for the ability season's games, drawn on the FIBA court."""
    from .spatial_shots import load_spatial_environment
    rules = national_rules(game_date)
    nba = load_spatial_environment(rules["season"], None, root)
    return dict(nba, league="FIBA", coordinate_system=rules["coordinate_system"],
                purpose=f"{nba['purpose']} Drawn on the FIBA court ({rules['three_point_m']} m line) for national games.")


def _logit(p):
    p = min(1 - 1e-6, max(1e-6, p))
    return math.log(p / (1 - p))


def _inv(x):
    return 1 / (1 + math.exp(-x))


def translate(profile, translation):
    """An NBA profile in FIBA terms: shooting percentages moved by a logit shift, the other rates by a ratio
    (`translation`, fitted on anchors by scripts/build_fiba_engine.py). Defense and identity fields are kept."""
    if not profile:
        return {}
    rates = dict(profile["rates"])
    for k in SHIFT_KEYS:
        rates[k] = _inv(_logit(rates[k]) + translation["shift"][k])
    for k in RATIO_KEYS:
        if k in rates:
            rates[k] = rates[k] * translation["ratio"][k]
    rates["three_point_attempt_rate"] = min(0.9, rates["three_point_attempt_rate"])
    return dict(profile, rates={k: round(v, 6) for k, v in rates.items()}, fiba_model=translation["model_version"])


def nba_profile(player_id, bbr_id, game_date, root=ROOT):
    """The player's NBA expectation for the ability season, as an NBA game on that season's last day would read it:
    only a season profile (a real career's trajectory or an alternate-history player's expectation). A player whose
    only NBA record is older (a veteran rating without a season in the ability year) is not an NBA player here."""
    from .player_stats import load_rating_index
    from .prospects import PROTAGONIST_MODEL_VERSION
    from .trajectories import TRAJECTORY_MODEL_VERSION
    season = ability_season(game_date)
    index = load_rating_index(game_date, season, root)
    if index is None:
        return {}
    try:
        profile = index.engine_profile(player_id, bbr_id)
    except ValueError:
        profile = index.engine_profile(bbr_id, bbr_id) if bbr_id in index.players else {}
    return profile if profile.get("model_version") in (TRAJECTORY_MODEL_VERSION, PROTAGONIST_MODEL_VERSION) else {}


def fiba_profile(fiba_key, game_date, root=ROOT):
    """A non-NBA player's FIBA profile for the edition (his past tournaments, or the replacement prior)."""
    e = edition_on(game_date, root)
    if fiba_key not in e["fiba_profiles"]:
        raise ValueError(f"{fiba_key} has no FIBA profile for {e['edition']}")
    return e["fiba_profiles"][fiba_key]


def expected_profile(player_id, profile, game_date, root=ROOT):
    """The profile a national packet must carry for this player (before his journaled development swing)."""
    if profile.get("fiba_key"):
        return fiba_profile(profile["fiba_key"], game_date, root)
    base = nba_profile(player_id, profile.get("bbr_id"), game_date, root)
    return translate(base, edition_on(game_date, root)["translation"])
