"""Deterministic reporting calendar and season-specific competition rules.

Competition availability does not enable the game engine for a new era. That
still requires an independently verified row in runtime.era.SEASON_RULES.
"""
import re


def season_start(season: str) -> int:
    if not isinstance(season, str) or not re.fullmatch(r"\d{4}-\d{2}", season):
        raise ValueError("season must use YYYY-YY")
    year = int(season[:4])
    if int(season[-2:]) != (year + 1) % 100:
        raise ValueError("season must name consecutive years")
    return year


def nba_cup_available(season: str) -> bool:
    """The inaugural tournament belongs to 2023-24, never to earlier years."""
    return season_start(season) >= 2023


def play_in_format(season: str):
    year = season_start(season)
    if year < 2019:
        return None
    return "2020_restart" if year == 2019 else "seventh_through_tenth"


def area_available(area: dict, season: str) -> bool:
    first = area.get("first_season")
    return first is None or season_start(season) >= season_start(first)


def month_markers(config: dict, month: str, season: str) -> list[str]:
    """Resolve dated structural markers without leaking modern events backward."""
    spec = config["regular_season"][month]
    markers = list(spec.get("markers", []))
    for marker in spec.get("conditional_markers", []):
        if season_start(season) >= season_start(marker["first_season"]):
            markers.append(marker["label"])
    return markers


def statistics_bucket(game_type: str, season: str, cup_stage: str | None = None) -> str:
    """One additive bucket per game; Cup stage is an overlapping filter only."""
    season_start(season)
    if cup_stage not in (None, "group", "quarterfinal", "semifinal", "championship"):
        raise ValueError("unknown NBA Cup stage")
    if cup_stage is not None or game_type == "nba_cup_championship":
        if not nba_cup_available(season):
            raise ValueError(f"NBA Cup does not exist in {season}")
        if game_type == "nba_cup_championship":
            if cup_stage not in (None, "championship"):
                raise ValueError("championship must use the championship stage")
            return "nba_cup_championship"
        if game_type != "regular" or cup_stage == "championship":
            raise ValueError("non-championship Cup games must be regular-season games")
    if game_type == "play_in" and play_in_format(season) is None:
        raise ValueError(f"Play-In does not exist in {season}")
    if game_type not in {"summer_league", "preseason", "regular", "play_in", "playoff"}:
        raise ValueError(f"unsupported NBA report game type: {game_type}")
    return game_type


def month_week(day: int) -> int:
    if isinstance(day, bool) or not isinstance(day, int):
        raise TypeError("day must be an integer")
    if day < 1 or day > 31:
        raise ValueError("day must be between 1 and 31")
    if day <= 7:
        return 1
    if day <= 14:
        return 2
    if day <= 21:
        return 3
    return 4


def series_over(player_team_wins: int, opponent_wins: int) -> bool:
    for value in (player_team_wins, opponent_wins):
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError("series wins must be integers")
        if value < 0 or value > 4:
            raise ValueError("series wins must be between 0 and 4")
    return player_team_wins == 4 or opponent_wins == 4


def next_series_game_number(player_team_wins: int, opponent_wins: int):
    if series_over(player_team_wins, opponent_wins):
        return None
    game_number = player_team_wins + opponent_wins + 1
    if game_number > 7:
        raise ValueError("invalid best-of-seven state")
    return game_number
