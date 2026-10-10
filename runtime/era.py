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
    "2004-05": {
        # 30 clubs in six divisions (Charlotte joins); hand-checking crackdown recorded as a rule flag only, with no
        # engine effect (the user's decision: sizing it from 2004-05 results would be hindsight). Roster limits and the
        # injured list are unchanged until 2005-06 (inactive list). Sources: library/2004/league/nba_2004_offseason_calendar.json,
        # library/2005/league/nba_2005_cba_rules.json game_rules.
        "game_day_actives": 12,
        "roster_maximum": 15,
        "reserve_list": "injured_list",
        "zone_defense_legal": True,
        "defensive_three_seconds": True,
        "hand_check_emphasis": True,
        "play_in_tournament": False,
        "first_round_best_of": 7,
        "playoff_teams_per_conference": 8,
        "clubs": 30,
    },
    "2005-06": {
        # The 2005 agreement (library/2005/league/nba_2005_cba_rules.json `roster`, sourced): the injured list becomes
        # an inactive list set game by game with no minimum stay, at most three inactive; 13 to 15 players under
        # contract; twelve dress. Playing rules as 2004-05 (hand-check emphasis continues; no 2005-06 rule change is
        # recorded in `game_rules`). Added in the season-change audit, December 2004 on the career clock.
        "game_day_actives": 12,
        "roster_minimum": 13,
        "roster_maximum": 15,
        "reserve_list": "inactive_list",
        "reserve_list_maximum": 3,
        "reserve_list_minimum_games": 0,
        "zone_defense_legal": True,
        "defensive_three_seconds": True,
        "hand_check_emphasis": True,
        "play_in_tournament": False,
        "first_round_best_of": 7,
        "playoff_teams_per_conference": 8,
        "clubs": 30,
    },
}

GAME_TYPES = ("preseason", "regular", "play_in", "playoff")

# National-team competitions (FIBA rules; `runtime/national_engine.py`), the same buckets as the statistics contract
# (`runtime/career_stats.NATIONAL_TYPES`).
NATIONAL_GAME_TYPES = ("world_cup_qualifier", "world_cup_finals", "olympic_qualifier", "olympic_finals",
                       "continental_qualifier", "continental_finals", "national_friendly")

# FIBA playing rules by period (library/fiba/fiba_rules.json, FIBA Official Basketball Rules). Four ten-minute
# quarters, five-minute overtimes, a 24-second clock, five fouls, twelve dressed. The three-point line moved from
# 6.25 m to 6.75 m on October 1, 2010, with the no-charge semicircle and the rectangular lane.
FIBA_RULE_PERIODS = (
    ("2004-09-01", "2010-09-30", {"coordinate_system": "fiba_2006_feet_from_basket", "three_point_m": 6.25,
                                  "lane": "trapezoid", "no_charge_semicircle": False}),
    ("2010-10-01", "2017-12-31", {"coordinate_system": "fiba_2010_feet_from_basket", "three_point_m": 6.75,
                                  "lane": "rectangle", "no_charge_semicircle": True}),
)
FIBA_BASE_RULES = {
    "quarters": 4,
    "quarter_minutes": 10,
    "overtime_minutes": 5,
    "shot_clock_seconds": 24,
    "foul_out_limit": 5,
    "players_on_floor": 5,
    "game_day_actives": 12,
    "roster_maximum": 12,
    "zone_defense_legal": True,
    "defensive_three_seconds": False,
    "competition": "FIBA",
}


# All-Star weekend exhibitions (`runtime/all_star_engine.py`, `runtime/all_star_games.py`): the Rookie Challenge and the
# All-Star Game, played by the same kernel under their own rules, dated like the FIBA rows. Researched in each season's
# All-Star calendar (library/<year>/league/nba_<season>_all_star.json, `research`):
# * All-Star Game: standard NBA rules, four 12-minute quarters, 5-minute overtimes, six fouls, twelve dressed (every
#   1997-2005 box totals 240 team minutes, 2003's two overtimes 290; no 2004-2006 source states a deviation).
# * Rookie Challenge: two 20-minute halves (the kernel's `quarters` are its periods), 2-minute overtimes, nine a side,
#   fouls counted but nobody fouls out (`foul_out_limit` None: no disqualification and no foul-trouble sitting; sourced
#   for 2004, unverified for 2005 and 2006, where the 2005 box fits it). Not modelled: the team-foul penalty after ten,
#   the 20-second timeouts and the clock stopping after made baskets.
EXHIBITION_GAME_TYPES = ("rookie_challenge", "all_star")
EXHIBITION_COMPETITION = "NBA All-Star Weekend"
EXHIBITION_BASE_RULES = {
    "shot_clock_seconds": 24,
    "players_on_floor": 5,
    "zone_defense_legal": True,
    "defensive_three_seconds": True,
    "competition": EXHIBITION_COMPETITION,
}
EXHIBITION_RULE_PERIODS = {
    "all_star": (("2004-02-15", "2006-02-19", {"quarters": 4, "quarter_minutes": 12, "overtime_minutes": 5,
                                                "foul_out_limit": 6, "game_day_actives": 12, "roster_maximum": 12}),),
    "rookie_challenge": (("2004-02-13", "2006-02-17", {"quarters": 2, "quarter_minutes": 20, "overtime_minutes": 2,
                                                        "foul_out_limit": None, "game_day_actives": 9,
                                                        "roster_maximum": 9}),),
}


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


def ability_season(game_date):
    """The NBA season whose ability a national game reads: a summer game (June to September) the season just closed,
    otherwise the season under way (a qualifying window in November or February)."""
    month = int(game_date[5:7])
    season = season_for_date(game_date)
    return previous_season(season) if 6 <= month <= 9 else season


def national_rules(game_date):
    """FIBA's rules on the game's date, labelled with the ability season (the kernel checks profiles against it)."""
    for first, last, row in FIBA_RULE_PERIODS:
        if first <= game_date <= last:
            return {**FIBA_BASE_RULES, **row, "season": ability_season(game_date)}
    raise ValueError(f"no FIBA rules encoded for {game_date}; add a FIBA_RULE_PERIODS row before simulating it")


def exhibition_layout(game_type, season):
    """(regulation periods, period seconds, overtime seconds) of an All-Star weekend game in the season, or None for any
    other game type; read by the result checks (`shot_events.spatial_result_errors`), which carry no date."""
    for first, last, row in EXHIBITION_RULE_PERIODS.get(game_type, ()):
        if season_for_date(first) <= (season or "") <= season_for_date(last):
            return row["quarters"], row["quarter_minutes"] * 60, row["overtime_minutes"] * 60
    return None


def exhibition_rules(game_type, game_date):
    """An All-Star weekend game's rules on its date, labelled with the NBA season it belongs to (the kernel checks
    profiles against it). A date outside an encoded row fails closed: add the row before the weekend is played."""
    for first, last, row in EXHIBITION_RULE_PERIODS.get(game_type, ()):
        if first <= game_date <= last:
            return {**EXHIBITION_BASE_RULES, **row, "season": season_for_date(game_date)}
    raise ValueError(f"no {game_type} rules encoded for {game_date}; add an EXHIBITION_RULE_PERIODS row before simulating it")
