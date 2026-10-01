"""Season-gated rules and league environment.

Two kinds of era knowledge feed the engine:

* Rules: what the game legally looks like in a season (period length, foul-out
  limit, game-day actives, which postseason formats exist). These are known
  before the season starts, so a season reads its own row.
* Environment: league-wide scoring/pace averages. A season is calibrated on the
  last *completed* season, read from `library/<year>/league/`, and only once
  that season's averages were published relative to the game date. A season's
  own final averages are hindsight and are never used to simulate it.

Seasons without an encoded row fail closed rather than borrowing another era.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Facts that hold across every supported season.
BASE_RULES = {
    "quarters": 4,
    "quarter_minutes": 12,
    "overtime_minutes": 5,
    "shot_clock_seconds": 24,
    "foul_out_limit": 6,
    "players_on_floor": 5,
}

# Per-season rule rows. Only seasons the career can reach soon are encoded;
# add a row (with its basis) before the career clock enters a new season.
SEASON_RULES = {
    "2003-04": {
        "game_day_actives": 12,
        "roster_maximum": 15,
        "reserve_list": "injured_list",
        "zone_defense_legal": True,          # since 2001-02, with defensive three seconds
        "defensive_three_seconds": True,
        "hand_check_emphasis": False,         # perimeter hand-check crackdown begins 2004-05
        "play_in_tournament": False,          # the play-in format begins 2020-21
        "first_round_best_of": 7,             # first round became best-of-seven in 2003
        "playoff_teams_per_conference": 8,
    },
}

GAME_TYPES = ("preseason", "regular", "play_in", "playoff")


def season_of(year_start):
    return f"{year_start}-{str(year_start + 1)[-2:]}"


def previous_season(season):
    start = int(season[:4])
    return season_of(start - 1)


def rules_for(season):
    if season not in SEASON_RULES:
        raise ValueError(f"no era rules encoded for {season}; add a SEASON_RULES row before simulating it")
    return {**BASE_RULES, **SEASON_RULES[season], "season": season}


def allowed_game_types(season):
    rules = rules_for(season)
    return tuple(t for t in GAME_TYPES if t != "play_in" or rules["play_in_tournament"])


def environment_path(season, root=ROOT):
    baseline = previous_season(season)
    year_end = int(baseline[:4]) + 1
    return Path(root) / "library" / str(year_end) / "league" / f"nba_{baseline.replace('-', '_')}_league_environment.json"


def environment_for(season, as_of, root=ROOT):
    """Return the calibration environment for a season, gated by publication date."""
    path = environment_path(season, root)
    if not path.is_file():
        raise ValueError(f"no league environment for {previous_season(season)} (needed to simulate {season})")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("season") != previous_season(season):
        raise ValueError(f"{path.name}: season label mismatch")
    if not isinstance(as_of, str) or len(as_of) != 10:
        raise ValueError("as_of must be an ISO date")
    if data["published_after"] > as_of:
        raise ValueError(f"{data['season']} environment is not published as of {as_of}")
    return data


def season_for_date(date):
    """NBA seasons run across the calendar year; July 1 starts the new league year."""
    year, month = int(date[:4]), int(date[5:7])
    return season_of(year if month >= 7 else year - 1)
