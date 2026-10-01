"""Small deterministic rules shared by validation and tests."""


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
    games_played = player_team_wins + opponent_wins
    number = games_played + 1
    if number > 7:
        raise ValueError("invalid best-of-seven state")
    return number
