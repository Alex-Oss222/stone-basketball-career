"""Possession-level basketball kernel calibrated to a league environment.

The kernel is deterministic given its entropy bytes. Production callers never
supply those bytes: `game_runner.run_game` derives them from the private
engine-state service after the game packet is journaled.

Calibration: per-play probabilities (turnover, free-throw trip, field-goal
attempt, three-point share, make rates, offensive-rebound rate, assist, steal,
block and foul shares) are derived from the league environment's per-game
averages, so a game between two neutral clubs reproduces that era's pace and
scoring. Player ratings, when present, tilt those rates around the era mean.

On top of the per-play rates (docs/engine_model.md):
* Defense: the five defenders' summed defensive value (DBPM scale, points per
  100 possessions) lowers the opponent's make probability and raises its
  turnovers, two thirds through shooting and one third through turnovers.
  Blocks/steals allocate that shooting budget between two- and three-point
  shots; they do not create defensive value for an ungraded player.
* Shot creation: usage above a player's own expected share lowers efficiency;
  teammates' passing improves it. Live steals and defensive rebounds can start
  shorter, easier transition plays, centered on the era's existing rates.
* Spatial shots: each field-goal attempt selects a modeled location from the
  prior season's league distance bands before its make/miss draw. Zone make
  rates retain that attempt's mean two-/three-point efficiency after clipping.
* Rotation: each player brings minutes per game and an availability; the engine
  draws who is available, dresses the top of the rotation and fills 240 minutes
  in rotation order, raising the rest within caps when short-handed.
* Late game: trailing teams foul and hurry, leading teams run the clock, every
  period ends on a held last shot, close games finish with the closing lineup
  and blowouts with the bench.
* Foul trouble: a player sits at 2 fouls in the 1st quarter, 3 in the 2nd, 4 in
  the 3rd and 5 in the 4th (until the last five minutes), and returns later.
* Score effect: a team ahead of the margin the two rosters should produce
  (estimated before the tip from the same rates) relaxes, one behind presses.
"""
from dataclasses import asdict, dataclass, field
import hashlib
import math
import random

from .packets import canonical
from .player_stats import MODEL_VERSION, RATE_KEYS
from .prospects import LEGACY_ROOKIE_MODEL_VERSION, ROOKIE_MODEL_VERSION
from .prospect_scouting import style_errors
from .shot_events import spatial_result_errors
from .spatial_shots import (draw_spatial_shot, load_spatial_environment,
                            spatial_environment_errors, tracking_metadata)
from .trajectories import TRAJECTORY_MODEL_VERSION, needs_development

POSITIONS = ("PG", "SG", "SF", "PF", "C")
GUARDS, BIGS = ("PG", "SG"), ("PF", "C")
RATING_KEYS = (
    "three_point_shooting", "mid_range_shooting", "rim_finishing", "free_throws",
    "ball_handling", "passing", "rebounding", "perimeter_defense", "interior_defense",
    "usage",
)
RATING_MIN, RATING_MAX, RATING_MEAN = 20, 80, 50

# Structural assumptions (provisional, not sourced league data): how the
# league's shot, rebound, assist and defensive events distribute by position
# in a mid-2000s offense. Team totals are always rescaled to the environment.
POSITION_PROFILE = {
    #        usage  three  reb   ast   stl   blk   foul
    "PG": (1.00, 1.35, 0.55, 2.40, 1.35, 0.30, 0.85),
    "SG": (1.15, 1.45, 0.65, 1.10, 1.20, 0.45, 0.90),
    "SF": (1.05, 1.05, 0.95, 0.85, 1.00, 0.75, 1.00),
    "PF": (0.95, 0.35, 1.40, 0.65, 0.80, 1.40, 1.15),
    "C":  (0.85, 0.05, 1.55, 0.55, 0.65, 2.10, 1.25),
}
RATING_SLOPE = 0.0025           # probability shift per rating point away from the mean
ORB_CONTINUATION_SECONDS = 7.0

# Judgement constants (provisional, documented in docs/engine_model.md).
DEFENSE_SHOT_SHARE = 2 / 3      # the rest of a defense's effect goes through turnovers
DEFENSE_LIMIT = 25              # bound on one player's defensive value, points per 100
MAX_ROSTER_INPUT = 30           # a season roster with availabilities, before dressing
MIN_DRESSED = 8                 # hardship: fewer available players than this are filled back
MINUTES_CAP = 42.0              # short-handed raises stop here (or at a player's own average if higher)
SHORT_HANDED_RAISE = 8.0        # and at most this far above his average
SUB_SECONDS = 180
CLOSING_SECONDS, CLOSING_MARGIN = 300, 10       # 4th quarter: closing lineup in the last 5:00 of a 10-point game
GARBAGE_MARGIN, GARBAGE_PER_MINUTE = 20, 1.0    # 4th quarter: bench when the lead reaches 20 + 1 per minute left (kernel 2003.9; was 15)
FOUL_WINDOWS = ((3, 24), (6, 45), (10, 75))     # trailing by at most N: foul with at most S seconds left
LATE_SECONDS = 150              # leaders run the clock and trailers hurry inside the last 2:30
HEAVE_SECONDS = 3.0             # a possession with less time than this gets a shot off only in proportion
LEAD_EFFECT, LEAD_CAP = 0.0022, 25   # make probability lost per point ahead of par (gained when behind), up to 25 points
EXPECTED_MARGIN_SCALE = 1.0     # par margin per unit of the analytic estimate (checked against played margins)
THREE_FLOOR = (0.6, 0.95)       # trailing by 3+ in the last minute: least three-point share (exactly 3 down, shot clock off)
# League averages already contain late-game fouls and threes; the regular rates leave out what this
# engine's own late-game logic adds back (measured on 2003-04 rosters, per team per game).
LATE_FOUL_FTA, LATE_FOUL_PF, LATE_THREE_PA = 1.4, 0.7, 0.5
LAST_SHOT = 0.7                # make probability factor on a period's final, fully defended possession
# Fatigue and injuries (problem E7, roadmap item 12).
BACK_TO_BACK_POINTS = 1.5       # a club on the second night of a back-to-back plays this much worse
INJURY_PER_36 = 0.016           # chance of an injury per 36 minutes played
# A one-game absence (illness, personal) for the simulated club, drawn before the game (kernel 2003.9).
# Its injuries already match 2002-03 regulars' missed games at 30+ minutes; 25-30 minute regulars missed
# about 1.3 more of 82 than the injury model loses, so 1.5% a game (judgement; docs/engine_model.md).
ABSENCE_PER_GAME = 0.015
INJURY_AGE = ((25, 0.85), (29, 1.0), (32, 1.2), (99, 1.45))     # (up to age, risk factor)
BACK_TO_BACK_INJURY = 1.2       # risk factor on the second night of a back-to-back
REINJURY_FACTOR, REINJURY_GAMES = 1.5, 10   # first ten games back from an 8+ game injury carry more risk (judgement)
# (share of injuries, fewest and most games missed): day-to-day up to season-ending.
INJURY_LENGTHS = ((0.55, 1, 2, "day-to-day"), (0.25, 3, 7, "short"), (0.13, 8, 20, "medium"),
                  (0.06, 21, 50, "long"), (0.01, 51, 82, "season"))
CAREFUL = 0.25                  # foul weight of a player one foul from disqualification
# Shot creation: structural assumptions, not fits to any player's career.
USAGE_MAKE_SLOPE, USAGE_MAKE_LIMIT = 0.30, 0.06
PASSING_MAKE_SLOPE, PASSING_MAKE_LIMIT = 0.018, 0.035
TRANSITION_AFTER_STEAL, TRANSITION_AFTER_REBOUND = 0.70, 0.22
TRANSITION_SECONDS = 7.0
TRANSITION_TWO_BONUS, TRANSITION_THREE_BONUS = 0.08, 0.02
# Source percentages include final-clock/forced attempts. The kernel applies
# those penalties explicitly; aggregate prior-environment validation measured
# a residual 1.4 percentage-point loss on threes before this correction.
THREE_MAKE_CALIBRATION = 0.014


@dataclass(frozen=True)
class PlayerInput:
    player_id: str
    position: str
    minutes: float                  # minutes per game when he plays
    ratings: dict = field(default_factory=dict)
    stat_profile: dict = field(default_factory=dict)
    availability: float = 1.0       # chance he is available for this game; the engine draws it
    age: int = None                 # age on the game date; sets injury risk where injuries are drawn
    returning: int = 0              # games back from an injury of 8+ games (1-10); raises his injury risk (2003.10)


@dataclass(frozen=True)
class TeamInput:
    team_id: str
    players: tuple
    pace: float = 1.0               # the club's pace relative to the league (problem E6)
    rest_days: int = 2              # days off before this game; 0 is the second night of a back-to-back
    injuries: bool = False          # draw injuries for this club's players (the simulated club; E7)
    starters: tuple = ()            # dated staff choice; availability may require replacements
    season_roster: bool = False     # dressed by the engine even when every availability is 0 or 1 (absence spells)


def team_errors(team, rules):
    errors = []
    players = list(team.players)
    if isinstance(team.pace, bool) or not isinstance(team.pace, (int, float)) or not 0.85 <= team.pace <= 1.15:
        errors.append("club pace must be between 0.85 and 1.15 of the league's")
    if isinstance(team.rest_days, bool) or not isinstance(team.rest_days, int) or not 0 <= team.rest_days <= 10:
        errors.append("rest days must be a whole number from 0 to 10")
    if not isinstance(team.injuries, bool):
        errors.append("injuries must be true or false")
    if not isinstance(team.season_roster, bool):
        errors.append("season_roster must be true or false")
    for p in team.players:
        if type(p.returning) is not int or not 0 <= p.returning <= REINJURY_GAMES:
            errors.append(f"{p.player_id}: returning must be a whole number of games from 0 to {REINJURY_GAMES}")
    for p in players:
        if p.age is not None and (isinstance(p.age, bool) or not isinstance(p.age, int) or not 15 <= p.age <= 50):
            errors.append(f"{p.player_id}: age must be a whole number from 15 to 50")
    ids = [p.player_id for p in players]
    if len(ids) != len(set(ids)):
        errors.append("duplicate player ids")
    if team.starters and (len(team.starters) != 5 or len(set(team.starters)) != 5
                          or any(pid not in ids for pid in team.starters)):
        errors.append("starters must name five different roster players")
    if len(players) < rules["players_on_floor"]:
        errors.append("fewer than five available players")
    availability = [p.availability for p in players]
    # A spell-flagged season roster may mark a player out for this game (availability 0).
    floor_ok = (lambda a: 0 <= a <= 1) if team.season_roster is True else (lambda a: 0 < a <= 1)
    if any(isinstance(a, bool) or not isinstance(a, (int, float)) or not math.isfinite(a) or not floor_ok(a)
           for a in availability):
        errors.append("availability must be greater than 0 and at most 1")
        season_roster = False
    else:
        season_roster = team.season_roster is True or any(a < 1 for a in availability)
    # A game-day list dresses everyone; a season roster with availabilities is dressed by the engine.
    limit = MAX_ROSTER_INPUT if season_roster else rules["game_day_actives"]
    if len(players) > limit:
        errors.append(f"{len(players)} players exceeds the {rules['season']} limit of {limit}")
    for p in players:
        if p.position not in POSITIONS:
            errors.append(f"{p.player_id}: unknown position {p.position!r}")
        if isinstance(p.minutes, bool) or not isinstance(p.minutes, (int, float)) or not math.isfinite(p.minutes) or p.minutes < 0 or p.minutes > 48:
            errors.append(f"{p.player_id}: minutes target must be 0-48")
        for key, value in p.ratings.items():
            if key not in RATING_KEYS:
                errors.append(f"{p.player_id}: unknown rating {key!r}")
            elif isinstance(value, bool) or not isinstance(value, int) or not RATING_MIN <= value <= RATING_MAX:
                errors.append(f"{p.player_id}: rating {key} must be an integer {RATING_MIN}-{RATING_MAX}")
        if p.stat_profile:
            profile = p.stat_profile
            base_keys = {"bbr_id", "model_version", "as_of", "season_end_year", "source_sha256", "rates"}
            trajectory = profile.get("model_version") == TRAJECTORY_MODEL_VERSION
            defense = profile.get("defense", 0.0)
            if (isinstance(defense, bool) or not isinstance(defense, (int, float)) or not math.isfinite(defense)
                    or abs(defense) > DEFENSE_LIMIT):
                errors.append(f"{p.player_id}: invalid defensive value")
            if ("feedback_sha256" in profile and (not trajectory or not isinstance(profile["feedback_sha256"], str)
                                                  or len(profile["feedback_sha256"]) != 64)):
                errors.append(f"{p.player_id}: feedback applies only to real-career profiles")
            scouting_keys = {"scouting", "style", "scouting_sources"}
            if set(profile) & scouting_keys:
                if profile.get("model_version") != ROOKIE_MODEL_VERSION or not scouting_keys <= set(profile):
                    errors.append(f"{p.player_id}: scouting requires a complete current rookie profile")
                errors.extend(f"{p.player_id}: {e}" for e in style_errors(profile.get("style")))
            if (set(profile) - {"development", "defense", "feedback_sha256"} - scouting_keys != base_keys
                    or ("development" in profile and not needs_development(profile))
                    or profile.get("model_version") not in (MODEL_VERSION, LEGACY_ROOKIE_MODEL_VERSION,
                                                             ROOKIE_MODEL_VERSION, TRAJECTORY_MODEL_VERSION)
                    or (not trajectory and profile.get("season_end_year") != 2003)
                    or (trajectory and profile.get("season_end_year") != int(rules["season"][:4]) + 1)):
                errors.append(f"{p.player_id}: invalid statistical profile metadata")
            rates = profile.get("rates", {})
            if not isinstance(rates, dict) or set(rates) != set(RATE_KEYS):
                errors.append(f"{p.player_id}: incomplete statistical rates")
            else:
                for key, value in rates.items():
                    limit = 10 if key in ("free_throw_attempt_rate", "turnovers_per_fga", "fouls_per_minute") else 1
                    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= limit:
                        errors.append(f"{p.player_id}: invalid rate {key}")
            # Avoid silently ignoring a supplied grade or double-counting a rate.
            if set(p.ratings) - {"perimeter_defense", "interior_defense"}:
                errors.append(f"{p.player_id}: statistical rates replace overlapping legacy ratings")
    total = sum(p.minutes for p in players if isinstance(p.minutes, (int, float)))
    regulation = rules["players_on_floor"] * rules["quarters"] * rules["quarter_minutes"]
    if season_roster and total < regulation - 1:
        errors.append(f"minutes per game sum to {total}, fewer than the {regulation} a full roster must cover")
    if not season_roster and abs(total - regulation) > 1:
        errors.append(f"minutes targets sum to {total}, expected {regulation}")
    return errors


def team_packet(team):
    data = asdict(team)
    if not team.starters:
        # Preserve the shape (and journal digest) of historical input packets.
        data.pop("starters")
    if not team.season_roster:
        data.pop("season_roster")       # historical packets have no such field
    data["players"] = [dict(p, ratings=dict(sorted(p["ratings"].items()))) for p in data["players"]]
    for p in data["players"]:
        if not p.get("returning"):
            p.pop("returning", None)        # historical packets have no such field
    return data


def calibrate(environment):
    a = environment["averages"]
    assumptions = environment["engine_assumptions"]
    fgm = a["fga"] * a["fg_pct"]
    three_m = a["three_pa"] * a["three_pct"]
    two_a = a["fga"] - a["three_pa"]
    and_one_fta = a["fta"] * assumptions["and_one_share_of_fta"]
    trips = (a["fta"] - and_one_fta - LATE_FOUL_FTA) / 2
    plays = a["fga"] + a["tov"] + trips
    team_tov = environment.get("team_turnovers_per_game", 0)
    player_tov = a["tov"] - team_tov
    misses = a["fga"] - fgm
    box_possessions = plays - a["orb"]
    # One point of defense (per 100 possessions) as a change in make probability and in
    # turnover probability. A make is worth its points and and-one free throws, less the
    # offensive-rebound continuation a miss would have had (worth a possession's points). A
    # defensive turnover takes the place of a shot, so it costs a shot's full value.
    per_possession = a["points"] / box_possessions
    shot_points = 2 * fgm + three_m + and_one_fta * a["ft_pct"]
    make_value = shot_points / fgm - a["orb"] / misses * per_possession
    shot_value = a["fga"] / box_possessions * make_value
    turnover_value = plays / box_possessions * (shot_points + a["orb"] * per_possession) / a["fga"]
    p_extra_foul = max(0.0, a["pf"] - LATE_FOUL_PF - trips - and_one_fta) / box_possessions
    transition_share = ((a["stl"] * TRANSITION_AFTER_STEAL + a["drb"] * TRANSITION_AFTER_REBOUND)
                        / box_possessions * (1 - p_extra_foul))
    mean_seconds = 2880 / (2 * box_possessions) - ORB_CONTINUATION_SECONDS * a["orb"] / box_possessions
    continuation_value = a["orb"] / misses * per_possession
    and_one_value = and_one_fta / fgm * a["ft_pct"]
    two_value, three_value = 2 + and_one_value - continuation_value, 3 + and_one_value - continuation_value
    return {
        # The clock is calibrated so the box-score totals (FGA, TOV, FTA, ORB)
        # land on the era averages. Possessions counted from those totals run a
        # little above the published pace, whose estimator differs; the box
        # totals are what a game record shows, so they take priority.
        "possession_seconds": (mean_seconds - transition_share * TRANSITION_SECONDS) / (1 - transition_share),
        "transition_share": transition_share,
        # Offensive rebounds create additional half-court plays, diluting transition shots.
        "transition_play_share": transition_share * box_possessions / plays,
        "defense_three_share": a["three_pa"] * three_value / (two_a * two_value + a["three_pa"] * three_value),
        "p_team_tov": team_tov / plays,
        "p_tov": player_tov / (plays - team_tov),
        "p_trip": trips / (plays - team_tov),
        # A player's real free-throw rate also contains late-game fouls; his regular trips leave them out.
        "regular_trip_share": trips / (trips + LATE_FOUL_FTA / 2),
        "three_share": (a["three_pa"] - LATE_THREE_PA) / a["fga"],
        # A player's real three-point rate also contains late-game threes, which the late-game
        # logic adds back; his regular share leaves them out.
        "regular_three_share": (a["three_pa"] - LATE_THREE_PA) / a["three_pa"],
        "p_two": (fgm - three_m) / two_a,
        "p_three": a["three_pct"],
        "p_ft": a["ft_pct"],
        "p_and_one": and_one_fta / fgm,
        "p_orb": a["orb"] / misses,
        "p_player_drb": min(1.0, a["drb"] / (misses - a["orb"])),
        "p_ast": a["ast"] / fgm,
        "p_stl": a["stl"] / player_tov,
        "p_blk": a["blk"] / misses,
        # Drawn once per engine possession, which follow the box totals rather than the published pace.
        "p_extra_foul": p_extra_foul,
        "home_edge": assumptions["home_edge_points_per_game"] / (2 * a["fga"] * make_value),
        "home_points": assumptions["home_edge_points_per_game"],
        "edge_per_point": 1 / (a["fga"] * make_value),     # make-probability shift worth one point a game
        "box_possessions": box_possessions,
        "and_one_share_of_fta": assumptions["and_one_share_of_fta"],
        "rate_baselines": environment.get("player_rate_baselines", {}),
        "make_per_defense": DEFENSE_SHOT_SHARE / 100 / shot_value,
        "tov_per_defense": (1 - DEFENSE_SHOT_SHARE) / 100 / turnover_value,
    }


def _rating(player, key):
    return player.ratings.get(key, RATING_MEAN) - RATING_MEAN


def _rate_weight(player, key, position_index, cal, legacy_key=None):
    if player.stat_profile:
        return player.stat_profile["rates"][key] / cal["rate_baselines"][key]
    return POSITION_PROFILE[player.position][position_index] * (1 + 0.02 * _rating(player, legacy_key))


def _usage_adjustment(player, total_weight, cal):
    """Extra load relative to this player's own expected usage costs shot quality.

    Five league-average usage weights sum to five. Normalizing the player's
    estimate onto that scale keeps a neutral lineup neutral in every era.
    """
    weight = _rate_weight(player, "usage_pct", 0, cal, "usage")
    extra_share = weight / max(.01, total_weight) - weight / 5
    return _clamp(-USAGE_MAKE_SLOPE * extra_share, -USAGE_MAKE_LIMIT, USAGE_MAKE_LIMIT)


def _passing_weight(player, cal):
    weight = _rate_weight(player, "assist_pct", 3, cal, "passing")
    if not player.stat_profile:
        weight /= sum(profile[3] for profile in POSITION_PROFILE.values()) / 5
    return weight


def _passing_adjustment(teammates, cal):
    """Mean teammate passing quality; (player, presence) pairs exclude the shooter."""
    weight = sum(presence for _, presence in teammates)
    quality = sum(presence * _passing_weight(player, cal) for player, presence in teammates) / max(.01, weight)
    return _clamp(PASSING_MAKE_SLOPE * (quality - 1), -PASSING_MAKE_LIMIT, PASSING_MAKE_LIMIT)


def _defensive_split(player, cal):
    """Allocate existing DBPM, never infer defensive ability from blocks or steals.

    The two-point side remains an interior proxy: player ability inputs contain
    no individual rim/midrange splits. A one-baseline-event prior in each channel shrinks specialization.
    League shot values normalize the split to the original shooting budget.
    """
    value = _defense(player)
    if not value:
        return 0.0, 0.0
    blocks = _rate_weight(player, "block_pct", 5, cal, "interior_defense")
    steals = _rate_weight(player, "steal_pct", 4, cal, "perimeter_defense")
    tilt = (blocks - steals) / (blocks + steals + 2)
    two, three = 1 + tilt, 1 - tilt
    share = cal["defense_three_share"]
    normalizer = (1 - share) * two + share * three
    return value * two / normalizer, value * three / normalizer


def _transition_adjustment(is_three, transition, cal):
    bonus = TRANSITION_THREE_BONUS if is_three else TRANSITION_TWO_BONUS
    # Real season make rates already include fast breaks; remove the expected
    # contribution from every shot before adding it to actual transition shots.
    return bonus * (int(transition) - cal["transition_play_share"])


def _pressure_turnover_adjustment(player, team_defense, cal):
    """Pressure concerns amplify only the positive defense term, not base TOV.

    Team defensive value is a coarse proxy until actual trap/coverage events
    exist. Weak defense gives no extra ball-security reward for the concern.
    """
    sensitivity = player.stat_profile.get("style", {}).get("pressure_turnover_sensitivity", 1.0)
    return cal["tov_per_defense"] * team_defense * (sensitivity if team_defense > 0 else 1.0)


def _rebound_transition_chance(player):
    multiplier = player.stat_profile.get("style", {}).get("rebound_transition_multiplier", 1.0)
    return min(1.0, TRANSITION_AFTER_REBOUND * multiplier)


def _expected_play_rates(club, opponent, cal, transition_share=None):
    """Minute-weighted points, misses, rebounds and steals for one play."""
    presence = {pid: club.targets[pid] / 48 for pid in club.order}
    against = {pid: opponent.targets[pid] / 48 for pid in opponent.order}
    team_defense = sum(against[pid] * _defense(opponent.players[pid]) for pid in opponent.order)
    defense_two = sum(against[pid] * _defensive_split(opponent.players[pid], cal)[0] for pid in opponent.order)
    defense_three = sum(against[pid] * _defensive_split(opponent.players[pid], cal)[1] for pid in opponent.order)
    perimeter = sum(against[pid] * _rating(opponent.players[pid], "perimeter_defense") for pid in opponent.order) / 5
    interior = sum(against[pid] * _rating(opponent.players[pid], "interior_defense") for pid in opponent.order) / 5
    usage = {pid: presence[pid] * _rate_weight(club.players[pid], "usage_pct", 0, cal, "usage") for pid in club.order}
    total = sum(usage.values()) or 1.0
    mean_three = sum(u * POSITION_PROFILE[club.players[pid].position][1] for pid, u in usage.items()) / total
    value = misses = turnovers = 0.0
    for pid in club.order:
        player = club.players[pid]
        rates = player.stat_profile.get("rates")
        if rates:
            trips_per_fga = (rates["free_throw_attempt_rate"] * (1 - cal["and_one_share_of_fta"]) / 2
                             * cal["regular_trip_share"])
            plays_per_fga = 1 + rates["turnovers_per_fga"] + trips_per_fga
            p_tov, p_trip = rates["turnovers_per_fga"] / plays_per_fga, trips_per_fga / plays_per_fga
            fg_pct = (rates["three_point_attempt_rate"] * rates["three_point_pct"]
                      + (1 - rates["three_point_attempt_rate"]) * rates["two_point_pct"])
            p_and_one = _clamp(rates["free_throw_attempt_rate"] * cal["and_one_share_of_fta"] / max(.01, fg_pct), 0, 1)
            three = rates["three_point_attempt_rate"] * cal["regular_three_share"]
            p2, p3, ft = rates["two_point_pct"], rates["three_point_pct"], rates["free_throw_pct"]
        else:
            p_tov = _clamp(cal["p_tov"] - RATING_SLOPE * _rating(player, "ball_handling"), 0.03, 0.4)
            p_trip, p_and_one = cal["p_trip"], cal["p_and_one"]
            three = _clamp(cal["three_share"] * POSITION_PROFILE[player.position][1]
                           * (1 + 0.02 * _rating(player, "three_point_shooting")) / max(.01, mean_three), 0.0, 0.8)
            p2 = cal["p_two"] + RATING_SLOPE * (_rating(player, "rim_finishing") + _rating(player, "mid_range_shooting")) / 2
            p3 = cal["p_three"] + RATING_SLOPE * _rating(player, "three_point_shooting")
            ft = _clamp(cal["p_ft"] + RATING_SLOPE * _rating(player, "free_throws"), 0.3, 0.97)
        p_tov = _clamp(p_tov + _pressure_turnover_adjustment(player, team_defense, cal), 0.005, 0.6)
        creation = _usage_adjustment(player, total, cal) + _passing_adjustment(
            [(club.players[mate], presence[mate]) for mate in club.order if mate != pid], cal)
        transition_delta = (transition_share - cal["transition_play_share"]) if transition_share is not None else 0.0
        p2 = _clamp(p2 + creation + transition_delta * TRANSITION_TWO_BONUS
                    - RATING_SLOPE * interior - cal["make_per_defense"] * defense_two, 0.0, 1.0)
        p3 = _clamp(p3 + THREE_MAKE_CALIBRATION + creation + transition_delta * TRANSITION_THREE_BONUS
                    - RATING_SLOPE * perimeter - cal["make_per_defense"] * defense_three, 0.0, 1.0)
        shot = max(0.0, 1 - p_tov - p_trip)
        make = three * p3 + (1 - three) * p2
        share = usage[pid] / total
        value += share * (p_trip * 2 * ft + shot * (three * p3 * 3 + (1 - three) * p2 * 2 + make * p_and_one * ft))
        misses += share * shot * (1 - make)
        turnovers += share * p_tov
    o_reb = sum(presence[pid] * _rate_weight(club.players[pid], "offensive_rebound_pct", 2, cal, "rebounding") for pid in club.order)
    d_reb = sum(against[pid] * _rate_weight(opponent.players[pid], "defensive_rebound_pct", 2, cal, "rebounding") for pid in opponent.order)
    p_orb = _clamp(cal["p_orb"] * (o_reb / max(.01, d_reb)) ** 0.5, 0.05, 0.6)
    kept = 1 - cal["p_team_tov"]
    steal_weight = sum(against[pid] * _rate_weight(opponent.players[pid], "steal_pct", 4, cal, "perimeter_defense")
                       for pid in opponent.order) / 5
    p_stl = cal["p_stl"] * (steal_weight if any(opponent.players[pid].stat_profile for pid in opponent.order) else 1)
    return kept * value, kept * misses, p_orb, kept * turnovers * _clamp(p_stl, 0, .98)


def _expected_points(club, opponent, cal):
    """Expected points per possession before home edge and score effects.

    The same creation and defensive terms as live play set the par margin.
    Opponent misses and turnovers also predict this club's transition chances;
    a turnover-producing defense therefore retains its fast-break benefit.
    """
    value, misses, p_orb, _ = _expected_play_rates(club, opponent, cal)
    _, other_misses, other_orb, steals = _expected_play_rates(opponent, club, cal)
    other_continuation = 1 - other_misses * other_orb
    steals /= other_continuation
    drb = other_misses * (1 - other_orb) * cal["p_player_drb"] / other_continuation
    rebound_chance = TRANSITION_AFTER_REBOUND
    if any(p.stat_profile.get("style", {}).get("rebound_transition_multiplier", 1) != 1
           for p in club.players.values()):
        weights = {pid: club.targets[pid] / 48 * _rate_weight(
            club.players[pid], "defensive_rebound_pct", 2, cal, "rebounding") for pid in club.order}
        total = sum(weights.values())
        if total:
            rebound_chance = sum(w * _rebound_transition_chance(club.players[pid])
                                 for pid, w in weights.items()) / total
    transitions = (steals * TRANSITION_AFTER_STEAL + drb * rebound_chance)
    transitions *= 1 - cal["p_extra_foul"]       # common fouls stop the break
    transition_share = transitions * (1 - misses * p_orb)
    value, misses, p_orb, _ = _expected_play_rates(club, opponent, cal, transition_share)
    return value / (1 - misses * p_orb)


def _clamp(p, low=0.01, high=0.99):
    return min(high, max(low, p))


def _blank_line():
    return {k: 0 for k in ("seconds", "pts", "fgm", "fga", "tpm", "tpa", "ftm", "fta",
                           "orb", "drb", "ast", "stl", "blk", "tov", "pf")}


def _defense(player):
    return player.stat_profile.get("defense", 0.0) if player.stat_profile else 0.0


def _allocate(players, total):
    """Minutes targets for the dressed players: each player's average in rotation order until the
    game is full; when short-handed, the shortfall is spread in proportion to the averages, first
    within the realistic caps and only then up to 48."""
    targets, left = {}, total
    for p in players:
        targets[p.player_id] = min(p.minutes, left)
        left -= targets[p.player_id]
    for cap in (lambda p: max(p.minutes, min(MINUTES_CAP, p.minutes + SHORT_HANDED_RAISE)), lambda p: 48.0):
        while left > 1e-9:
            room = {p.player_id: cap(p) - targets[p.player_id] for p in players if cap(p) - targets[p.player_id] > 1e-9}
            if not room:
                break
            weights = {p.player_id: max(p.minutes, 1.0) for p in players if p.player_id in room}
            share, given = left / sum(weights.values()), 0.0
            for pid, weight in weights.items():
                give = min(room[pid], share * weight)
                targets[pid] += give
                given += give
            left -= given
    return targets


class _Club:
    def __init__(self, team, side, rng, rules):
        self.team = team
        self.side = side
        self.players = {p.player_id: p for p in team.players}
        # Availability is drawn in roster order before anything else in the game.
        available = [p.player_id for p in team.players if p.availability >= 1 or rng.random() < p.availability]
        self.absences = []
        if team.injuries:
            self.absences = [pid for pid in available if rng.random() < ABSENCE_PER_GAME]
            available = [pid for pid in available if pid not in self.absences]
        need = min(len(team.players), MIN_DRESSED)
        if len(available) < need:
            # Hardship: the missing players most likely to have been available come back first
            # (stable sort, so rotation order breaks ties); a player barely with the club stays out.
            missing = sorted((p for p in team.players if p.player_id not in available), key=lambda p: -p.availability)
            available += [p.player_id for p in missing][:need - len(available)]
            available.sort(key=lambda pid: [p.player_id for p in team.players].index(pid))
        self.order = available[:rules["game_day_actives"]]
        self.inactive = [p.player_id for p in team.players if p.player_id not in self.order]
        regulation = rules["players_on_floor"] * rules["quarters"] * rules["quarter_minutes"]
        self.targets = _allocate([self.players[pid] for pid in self.order], regulation)
        self.lines = {pid: _blank_line() for pid in self.order}
        self.on_floor = []
        self.fouled_out = set()
        self.injured = set()            # hurt during this game: out for the rest of it
        self.points = 0
        self.period_points = []
        self.team_turnovers = 0
        self.started = set()
        self.transition = {key: 0 for key in ("possessions", "after_steal", "after_rebound", "seconds", "fga", "fgm", "points")}


def _weighted(rng, items, weights):
    total = sum(weights)
    if total <= 0:
        return items[0]
    draw = rng.random() * total
    for item, weight in zip(items, weights):
        draw -= weight
        if draw < 0:
            return item
    return items[-1]


def _eligible(club, sitting=frozenset()):
    """Players who may enter: not fouled out and not sitting with foul trouble, unless the bench runs dry."""
    able = [pid for pid in club.order if pid not in club.fouled_out and pid not in club.injured]
    free = [pid for pid in able if pid not in sitting]
    if len(free) < 5:
        free += sorted((pid for pid in able if pid in sitting), key=lambda pid: club.lines[pid]["pf"])[:5 - len(free)]
    if len(free) < 5:
        # Every bench player is out: NBA rule lets the last eligible players stay in.
        free += [pid for pid in club.order if pid not in free and pid not in club.injured][:5 - len(free)]
    if len(free) < 5:
        free += [pid for pid in club.order if pid not in free][:5 - len(free)]   # nobody else left at all
    return free


def _choose_lineup(club, elapsed, game_seconds, mode="normal", sitting=frozenset(), opening=False):
    """Pick the five whose played time lags their target share the most.

    `closing`: the five with the largest targets (the coach's best players).
    `garbage`: the bench first, the five largest targets only if needed.
    """
    candidates = _eligible(club, sitting)
    def deficit(pid):
        target = club.targets[pid] * 60 * (game_seconds / 2880)
        expected = target * min(1.0, (elapsed + SUB_SECONDS) / game_seconds)
        return expected - club.lines[pid]["seconds"]
    if mode == "closing":
        ranked = sorted(candidates, key=lambda pid: (-club.targets[pid], club.order.index(pid)))
    else:
        ranked = sorted(candidates, key=lambda pid: (-deficit(pid), club.order.index(pid)))
        if mode == "garbage":
            starters = set(sorted(club.order, key=lambda pid: (-club.targets[pid], club.order.index(pid)))[:5])
            bench = [pid for pid in ranked if pid not in starters]
            if len(bench) >= 5:
                ranked = bench + [pid for pid in ranked if pid in starters]
    if opening and club.team.starters:
        starters = [pid for pid in club.team.starters if pid in candidates]
        for missing in (pid for pid in club.team.starters if pid not in candidates):
            position = club.players[missing].position
            replacement = next((pid for pid in ranked if pid not in starters and club.players[pid].position == position), None)
            if replacement is None:
                replacement = next(pid for pid in ranked if pid not in starters)
            starters.append(replacement)
        ranked = starters + [pid for pid in ranked if pid not in starters]
        return ranked[:5]       # an explicit staff choice may deliberately be small
    lineup = ranked[:5]
    # Keep one guard and one big on the floor when the bench allows it. The player replaced is the
    # lowest-ranked one who was not just brought in and is not the only guard or big.
    position = lambda pid: club.players[pid].position
    inserted = set()
    for group, other in ((GUARDS, BIGS), (BIGS, GUARDS)):
        if any(position(pid) in group for pid in lineup):
            continue
        replacement = next((pid for pid in ranked[5:] if position(pid) in group), None)
        if replacement is None:
            continue
        for i in range(4, -1, -1):
            pid = lineup[i]
            if pid in inserted or (position(pid) in other and sum(position(q) in other for q in lineup) == 1):
                continue
            lineup[i] = replacement
            inserted.add(replacement)
            break
    return lineup


def resolve_game(home, away, *, entropy, event_id, rules, environment, game_type="regular", venue="home",
                 spatial_environment=None):
    if not isinstance(entropy, bytes) or len(entropy) < 32:
        raise ValueError("engine entropy required")
    for team in (home, away):
        errors = team_errors(team, rules)
        if errors:
            raise ValueError(f"{team.team_id}: " + "; ".join(errors))
    if spatial_environment is None:
        spatial_environment = load_spatial_environment(rules["season"])
    spatial_errors = spatial_environment_errors(spatial_environment, rules["season"])
    if spatial_errors:
        raise ValueError("; ".join(spatial_errors))
    cal = calibrate(environment)
    if any(p.stat_profile for team in (home, away) for p in team.players):
        if any(not isinstance(cal["rate_baselines"].get(k), (int, float)) or
               not math.isfinite(cal["rate_baselines"][k]) or cal["rate_baselines"][k] <= 0
               for k in RATE_KEYS):
            raise ValueError("statistical profiles require a complete positive rate baseline")
    seed_material = entropy + canonical({"event_id": event_id, "home": team_packet(home),
                                         "away": team_packet(away), "game_type": game_type})
    rng = random.Random(int.from_bytes(hashlib.sha256(seed_material).digest(), "big"))
    # Geometry has its own deterministic stream: extra coordinate samples must
    # not consume availability, clock, injury or shooting-outcome draws.
    spatial_rng = random.Random(int.from_bytes(hashlib.sha256(
        seed_material + b"\0spatial-shots/v1\0" + canonical(spatial_environment)).digest(), "big"))
    shots = []

    clubs = {"home": _Club(home, "home", rng, rules), "away": _Club(away, "away", rng, rules)}
    edge = {"home": cal["home_edge"], "away": -cal["home_edge"]} if venue == "home" else {"home": 0.0, "away": 0.0}
    quarter_seconds = rules["quarter_minutes"] * 60
    ot_seconds = rules["overtime_minutes"] * 60
    regulation_seconds = rules["quarters"] * quarter_seconds
    shot_clock = rules["shot_clock_seconds"]
    possessions = {"home": 0, "away": 0}
    state = {"period": 1, "clock": quarter_seconds, "elapsed": 0.0}
    # The margin these rosters should produce over regulation, home side positive (score effect centre).
    game_pace = (home.pace + away.pace) / 2     # a game is played between the two clubs' paces
    expected_margin = EXPECTED_MARGIN_SCALE * cal["box_possessions"] * game_pace * (
        _expected_points(clubs["home"], clubs["away"], cal) - _expected_points(clubs["away"], clubs["home"], cal))
    if venue == "home":
        expected_margin += cal["home_points"]
    # Fatigue: the second night of a back-to-back costs a club about 1.5 points (E7).
    for side, team in (("home", home), ("away", away)):
        if team.rest_days == 0:
            edge[side] -= cal["edge_per_point"] * BACK_TO_BACK_POINTS
            expected_margin += BACK_TO_BACK_POINTS * (-1 if side == "home" else 1)

    def other(side):
        return "away" if side == "home" else "home"

    def credit_seconds(seconds):
        for club in clubs.values():
            for pid in club.on_floor:
                club.lines[pid]["seconds"] += seconds

    def trouble_limit():
        """Fouls at which a player sits for now (E5)."""
        number, quarters = state["period"], rules["quarters"]
        if number > quarters or (number == quarters and state["clock"] <= CLOSING_SECONDS):
            return rules["foul_out_limit"]
        # With six to foul out: 2 in the 1st quarter, 3 in the 2nd, 4 in the 3rd, 5 in the 4th.
        return rules["foul_out_limit"] - (quarters - number) - 1

    def sitting(club):
        limit = trouble_limit()
        return frozenset(pid for pid in club.order if club.lines[pid]["pf"] >= limit)

    def foul(defense, kind):
        club = clubs[defense]
        if kind == "intentional":
            # The trailing team fouls with someone who can afford it.
            weights = [max(0.1, rules["foul_out_limit"] - 1 - club.lines[pid]["pf"]) for pid in club.on_floor]
        else:
            # A player one foul from disqualification defends carefully.
            weights = [rate_weight(club.players[pid], "fouls_per_minute", 6) *
                       (1.25 if not club.players[pid].stat_profile and kind == "shooting" and club.players[pid].position in ("PF", "C") else 1) *
                       (CAREFUL if club.lines[pid]["pf"] == rules["foul_out_limit"] - 1 else 1)
                       for pid in club.on_floor]
        pid = _weighted(rng, club.on_floor, weights)
        club.lines[pid]["pf"] += 1
        if club.lines[pid]["pf"] >= rules["foul_out_limit"]:
            club.fouled_out.add(pid)
            club.on_floor[club.on_floor.index(pid)] = _replacement(club, pid, sitting(club))
        elif club.lines[pid]["pf"] >= trouble_limit():
            # Foul trouble: he comes out at this dead ball if the bench has someone.
            club.on_floor[club.on_floor.index(pid)] = _replacement(club, pid, sitting(club), stay_if_none=True)

    def free_throws(offense, shooter, attempts):
        club = clubs[offense]
        player = club.players[shooter]
        p = (player.stat_profile["rates"]["free_throw_pct"] if player.stat_profile else
             _clamp(cal["p_ft"] + RATING_SLOPE * _rating(player, "free_throws"), 0.3, 0.97))
        made = 0
        for _ in range(attempts):
            club.lines[shooter]["fta"] += 1
            if rng.random() < p:
                club.lines[shooter]["ftm"] += 1
                club.lines[shooter]["pts"] += 1
                made += 1
        club.points += made
        return made

    def rate_weight(player, key, position_index, legacy_key=None):
        return _rate_weight(player, key, position_index, cal, legacy_key)

    def weights_for(club, key, position_index, legacy_key=None, players=None):
        return [rate_weight(club.players[pid], key, position_index, legacy_key)
                for pid in (club.on_floor if players is None else players)]

    def rebound(offense, defense):
        o, d = clubs[offense], clubs[defense]
        o_weights = weights_for(o, "offensive_rebound_pct", 2, "rebounding")
        d_weights = weights_for(d, "defensive_rebound_pct", 2, "rebounding")
        p = _clamp(cal["p_orb"] * (sum(o_weights) / max(.01, sum(d_weights))) ** 0.5, 0.05, 0.6)
        side = offense if rng.random() < p else defense
        # Not every missed field goal produces an individual rebound (dead ball,
        # out of bounds, etc.). Do not credit those to a made-up player.
        if side == defense and rng.random() >= cal["p_player_drb"]:
            return False
        club = clubs[side]
        weights = o_weights if side == offense else d_weights
        pid = _weighted(rng, club.on_floor, weights)
        club.lines[pid]["orb" if side == offense else "drb"] += 1
        if side == defense:
            state["transition"] = (defense, "rebound", pid)
        return side == offense

    def intentional_foul(offense):
        """Late-game foul by the trailing defense: two free throws to the player with the ball."""
        o = clubs[offense]
        shooter = _weighted(rng, o.on_floor, weights_for(o, "usage_pct", 0, "usage"))
        foul(other(offense), "intentional")
        free_throws(offense, shooter, 2)

    def play(offense, three_floor=None, last=False, transition=False):
        """Resolve one possession; return True when the offense keeps the ball (offensive rebound).
        `last`: the period's final possession, against a set defense that knows it."""
        defense = other(offense)
        o, d = clubs[offense], clubs[defense]
        state.pop("transition", None)
        if rng.random() < cal["p_team_tov"]:
            o.team_turnovers += 1
            return False
        handlers = weights_for(o, "usage_pct", 0, "usage")
        shooter = _weighted(rng, o.on_floor, handlers)
        player = o.players[shooter]
        # The five defenders' combined defensive value, in points per 100 possessions (E1).
        team_defense = sum(_defense(d.players[pid]) for pid in d.on_floor)
        roll = rng.random()
        p_tov = _clamp(cal["p_tov"] - RATING_SLOPE * _rating(player, "ball_handling"), 0.03, 0.4)
        p_trip, p_and_one = cal["p_trip"], cal["p_and_one"]
        rates = player.stat_profile.get("rates")
        if rates:
            trips_per_fga = rates["free_throw_attempt_rate"] * (1-cal["and_one_share_of_fta"]) / 2 * cal["regular_trip_share"]
            plays_per_fga = 1 + rates["turnovers_per_fga"] + trips_per_fga
            p_tov = rates["turnovers_per_fga"] / plays_per_fga
            p_trip = trips_per_fga / plays_per_fga
            fg_pct = rates["three_point_attempt_rate"]*rates["three_point_pct"] + (1-rates["three_point_attempt_rate"])*rates["two_point_pct"]
            p_and_one = _clamp(rates["free_throw_attempt_rate"] * cal["and_one_share_of_fta"] / max(.01, fg_pct), 0, 1)
        p_tov = _clamp(p_tov + _pressure_turnover_adjustment(player, team_defense, cal), 0.005, 0.6)
        if roll < p_tov:
            o.lines[shooter]["tov"] += 1
            weights = weights_for(d, "steal_pct", 4, "perimeter_defense")
            p_stl = cal["p_stl"] * sum(weights)/5 if any(d.players[pid].stat_profile for pid in d.on_floor) else cal["p_stl"]
            if rng.random() < _clamp(p_stl, 0, .98):
                d.lines[_weighted(rng, d.on_floor, weights)]["stl"] += 1
                state["transition"] = (defense, "steal")
            return False
        if roll < p_tov + p_trip:
            foul(defense, "shooting")
            free_throws(offense, shooter, 2)
            return False
        if rates:
            three_share = rates["three_point_attempt_rate"] * cal["regular_three_share"]
        else:
            three_weight = POSITION_PROFILE[player.position][1] * (1 + 0.02 * _rating(player, "three_point_shooting"))
            # Keep the old positional frequency fallback for unrated players.
            mean_three = sum(h * POSITION_PROFILE[o.players[pid].position][1] for pid, h in zip(o.on_floor, handlers)) / max(.01, sum(handlers))
            three_share = _clamp(cal["three_share"] * three_weight / max(.01, mean_three), 0.0, 0.8)
        if three_floor is not None:
            three_share = max(three_share, three_floor)
        is_three = rng.random() < three_share
        defense_key = "perimeter_defense" if is_three else "interior_defense"
        def_rating = sum(_rating(d.players[pid], defense_key) for pid in d.on_floor) / 5
        shot_defense = sum(_defensive_split(d.players[pid], cal)[int(is_three)] for pid in d.on_floor)
        if rates:
            p_make = rates["three_point_pct" if is_three else "two_point_pct"]
        elif is_three:
            p_make = cal["p_three"] + RATING_SLOPE * _rating(player, "three_point_shooting")
        else:
            finish = (_rating(player, "rim_finishing") + _rating(player, "mid_range_shooting")) / 2
            p_make = cal["p_two"] + RATING_SLOPE * finish
        # Score effect: a team ahead of where these rosters should be relaxes, one behind presses.
        par = expected_margin * min(1.0, state["elapsed"] / regulation_seconds) * (1 if offense == "home" else -1)
        lead = max(-LEAD_CAP, min(LEAD_CAP, o.points - d.points - par))
        creation = _usage_adjustment(player, sum(handlers), cal) + _passing_adjustment(
            [(o.players[pid], 1.0) for pid in o.on_floor if pid != shooter], cal)
        p_make = _clamp(p_make + (THREE_MAKE_CALIBRATION if is_three else 0)
                        + creation + _transition_adjustment(is_three, transition, cal)
                        - RATING_SLOPE * def_rating - cal["make_per_defense"] * shot_defense
                        - LEAD_EFFECT * lead + edge[offense], 0.0, 1.0) * (LAST_SHOT if last else 1.0)
        # First select the attempted location, then use that zone's normalized
        # make probability. All zones average back to the existing shot chance,
        # including when one or more zone probabilities hit zero or one.
        value = 3 if is_three else 2
        spatial_weights = player.stat_profile.get("style", {}).get("spatial_weights")
        if spatial_weights is None:
            zone, x, y, p_make = draw_spatial_shot(spatial_rng, spatial_environment, value, p_make)
        else:
            zone, x, y, p_make = draw_spatial_shot(spatial_rng, spatial_environment, value, p_make, spatial_weights)
        line = o.lines[shooter]
        line["fga"] += 1
        if transition:
            o.transition["fga"] += 1
        if is_three:
            line["tpa"] += 1
        made = rng.random() < p_make
        shots.append({"shot_id": f"{event_id}:shot:{len(shots) + 1:06d}", "player_id": shooter,
                      "side": offense, "period": state["period"], "clock_seconds": round(max(0.0, state["clock"]), 6),
                      "x": x, "y": y, "zone": zone, "value": value, "made": made,
                      "transition": bool(transition)})
        if made:
            line["fgm"] += 1
            if transition:
                o.transition["fgm"] += 1
            line["tpm"] += int(is_three)
            line["pts"] += value
            o.points += value
            mates = [pid for pid in o.on_floor if pid != shooter]
            weights = weights_for(o, "assist_pct", 3, "passing", mates)
            p_ast = cal["p_ast"] * sum(weights)/4 if any(o.players[pid].stat_profile for pid in mates) else cal["p_ast"]
            if rng.random() < _clamp(p_ast, 0, .98):
                o.lines[_weighted(rng, mates, weights)]["ast"] += 1
            if rng.random() < p_and_one:
                foul(defense, "shooting")
                free_throws(offense, shooter, 1)
            return False
        weights = weights_for(d, "block_pct", 5, "interior_defense")
        p_blk = cal["p_blk"] * sum(weights)/5 if any(d.players[pid].stat_profile for pid in d.on_floor) else cal["p_blk"]
        if rng.random() < _clamp(p_blk, 0, .98):
            d.lines[_weighted(rng, d.on_floor, weights)]["blk"] += 1
        return rebound(offense, defense)

    def lineup_mode():
        """Rotation mode for both clubs: normal, closing (close late game) or garbage (blowout)."""
        number, clock, quarters = state["period"], state["clock"], rules["quarters"]
        margin = abs(clubs["home"].points - clubs["away"].points)
        if number > quarters:
            return "closing"
        if number < quarters:
            return "normal"
        if margin >= GARBAGE_MARGIN + GARBAGE_PER_MINUTE * clock / 60:
            return "garbage"
        if clock <= CLOSING_SECONDS and margin <= CLOSING_MARGIN:
            return "closing"
        return "normal"

    def foul_window(lead):
        return next((seconds for points, seconds in FOUL_WINDOWS if lead <= points), 0)

    def run_period(number, seconds, offense, game_seconds, elapsed_before):
        state["period"], state["clock"] = number, seconds
        state.pop("transition", None)       # a new period always begins against a set defense
        late = number >= rules["quarters"]

        def substitute(mode):
            for club in clubs.values():
                club.on_floor = _choose_lineup(club, elapsed_before + seconds - state["clock"], game_seconds,
                                               mode, sitting(club), opening=number == 1 and state["clock"] == seconds)

        mode = lineup_mode()
        substitute(mode)
        if number == 1:
            for club in clubs.values():
                club.started = set(club.on_floor)
        for club in clubs.values():
            club.period_points.append(club.points)
        since_sub = 0.0

        def run(duration):
            nonlocal since_sub
            credit_seconds(duration)
            state["clock"] -= duration
            state["elapsed"] += duration
            since_sub += duration

        while state["clock"] > 0:
            clock = state["clock"]
            origin = state.pop("transition", None)
            transition = False
            now = lineup_mode()
            if since_sub >= SUB_SECONDS or now != mode:
                mode = now
                substitute(mode)
                since_sub = 0.0
                origin = None                 # substitution is a dead ball
            lead = clubs[offense].points - clubs[other(offense)].points
            if late and 0 < lead and clock <= foul_window(lead):
                # The trailing defense fouls at once to stop the clock (E4), if it can before the horn.
                foul_time = rng.uniform(1.0, 4.0)
                if foul_time >= clock:
                    run(clock)                   # the leader inbounds and the clock runs out
                    continue
                run(foul_time)
                possessions[offense] += 1
                intentional_foul(offense)
                offense = other(offense)
                continue
            if origin is not None and origin[0] == offense and clock > shot_clock:
                chance = (TRANSITION_AFTER_STEAL if origin[1] == "steal" else
                          _rebound_transition_chance(clubs[offense].players[origin[2]]))
                transition = rng.random() < chance
                if late and lead > 0 and clock <= LATE_SECONDS:
                    transition = False           # protect the lead and use the clock
            common_foul = rng.random() < cal["p_extra_foul"]
            if common_foul:
                transition = False               # dead ball resets shot quality and tempo
            three_floor = None
            if late and lead <= -3 and clock <= 60:
                three_floor = THREE_FLOOR[1] if lead == -3 and clock <= shot_clock else THREE_FLOOR[0]
            if transition:
                drawn = max(3.0, min(float(shot_clock), rng.gauss(TRANSITION_SECONDS / game_pace, 2.0)))
            elif late and lead < 0 and clock <= LATE_SECONDS:
                if lead >= -3 and clock <= shot_clock:
                    drawn = max(1.0, clock - rng.uniform(2.0, 8.0))   # a good shot, leaving a little time
                else:
                    drawn = max(4.0, min(16.0, rng.gauss(9.0, 3.0)))  # hurry for more possessions
            elif clock <= shot_clock:
                drawn = clock                    # hold for the last shot of the period
            elif late and lead > 0 and clock <= LATE_SECONDS:
                drawn = max(14.0, min(float(shot_clock), rng.gauss(20.0, 2.0)))   # run the clock
            else:
                drawn = max(4.0, min(float(shot_clock), rng.gauss(cal["possession_seconds"] / game_pace, 4.5)))
            if clock < HEAVE_SECONDS:
                # A heave with almost no time left gets a shot off only in proportion to the time it had.
                run(clock)
                if rng.random() >= clock / HEAVE_SECONDS:
                    break
            else:
                run(min(clock, drawn))
            possessions[offense] += 1
            # Non-shooting defensive fouls (reach-ins, loose balls, illegal screens excluded).
            if common_foul:
                foul(other(offense), "common")
            before_points = clubs[offense].points
            if transition:
                clubs[offense].transition["possessions"] += 1
                clubs[offense].transition["after_" + origin[1]] += 1
                clubs[offense].transition["seconds"] += min(clock, drawn)
            kept = play(offense, three_floor, last=state["clock"] <= 0, transition=transition)
            if transition:
                clubs[offense].transition["points"] += clubs[offense].points - before_points
            while kept and state["clock"] > 0:
                run(min(state["clock"], max(2.0, rng.gauss(ORB_CONTINUATION_SECONDS, 3.0))))
                kept = play(offense, three_floor)
            offense = other(offense)
        for club in clubs.values():
            club.period_points[-1] = club.points - club.period_points[-1]

    injuries = []

    def injury_draws(number, before):
        """Injuries for the simulated club, drawn at the end of each period on the minutes played in it,
        from the game's entropy (E7). A player hurt in a period sits out the rest of the game."""
        for side, club in clubs.items():
            if not club.team.injuries:
                continue
            for pid in club.order:
                if pid in club.injured:
                    continue
                minutes = (club.lines[pid]["seconds"] - before[side].get(pid, 0.0)) / 60
                if minutes <= 0:
                    continue
                player = club.players[pid]
                risk = INJURY_PER_36 * minutes / 36 * (next(f for limit, f in INJURY_AGE if player.age <= limit) if player.age else 1.0)
                if club.team.rest_days == 0:
                    risk *= BACK_TO_BACK_INJURY
                if 0 < player.returning <= REINJURY_GAMES:
                    risk *= REINJURY_FACTOR
                if rng.random() < risk:
                    share, low, high, kind = _weighted(rng, INJURY_LENGTHS, [length[0] for length in INJURY_LENGTHS])
                    club.injured.add(pid)
                    injuries.append({"side": side, "player_id": pid, "kind": kind, "games_out": rng.randint(low, high),
                                     "period": number})

    def snapshot():
        return {side: {pid: club.lines[pid]["seconds"] for pid in club.order} for side, club in clubs.items()}

    tip_winner = "home" if rng.random() < 0.5 else "away"
    starts = {1: tip_winner, 2: other(tip_winner), 3: other(tip_winner), 4: tip_winner}
    elapsed = 0
    for q in range(1, rules["quarters"] + 1):
        before = snapshot()
        run_period(q, quarter_seconds, starts[q], regulation_seconds, elapsed)
        injury_draws(q, before)
        elapsed += quarter_seconds
    overtimes = 0
    while clubs["home"].points == clubs["away"].points:
        overtimes += 1
        game_seconds = regulation_seconds + overtimes * ot_seconds
        before = snapshot()
        run_period(rules["quarters"] + overtimes, ot_seconds,
                   "home" if rng.random() < 0.5 else "away", game_seconds, elapsed)
        injury_draws(rules["quarters"] + overtimes, before)
        elapsed += ot_seconds

    def team_totals(club):
        totals = _blank_line()
        for line in club.lines.values():
            for key in totals:
                totals[key] += line[key]
        totals["possessions"] = possessions[club.side]
        totals["team_turnovers"] = club.team_turnovers
        totals["tov"] += club.team_turnovers
        return totals

    def box(club):
        rows = []
        for pid in club.order:
            line = dict(club.lines[pid])
            line["seconds"] = round(line["seconds"], 3)
            line["minutes"] = round(line["seconds"] / 60, 1)
            line["fouled_out"] = pid in club.fouled_out
            line["started"] = pid in club.started
            rows.append({"player_id": pid, **line})
        return rows

    return {
        "event_id": event_id,
        "season": rules["season"],
        "game_type": game_type,
        "venue": venue,
        "calibration": {"baseline_season": environment["season"],
                        "status": environment["verification"]["status"]},
        "home": home.team_id,
        "away": away.team_id,
        "final_score": {"home": clubs["home"].points, "away": clubs["away"].points},
        "periods": rules["quarters"] + overtimes,
        "overtimes": overtimes,
        "period_scores": {"home": clubs["home"].period_points, "away": clubs["away"].period_points},
        "team_stats": {side: team_totals(club) for side, club in clubs.items()},
        "player_stats": {side: box(club) for side, club in clubs.items()},
        "inactive": {side: list(club.inactive) for side, club in clubs.items()},
        "transition_stats": {side: {**club.transition, "seconds": round(club.transition["seconds"], 3)}
                             for side, club in clubs.items()},
        "game_seconds": elapsed,
        "injuries": injuries,
        "absences": [{"side": side, "player_id": pid, "kind": "illness or personal", "games_out": 1}
                     for side, club in clubs.items() for pid in club.absences],
        "shot_tracking": tracking_metadata(spatial_environment),
        "shots": shots,
        "terminated": True,
    }


def _replacement(club, out_pid, sitting=frozenset(), stay_if_none=False):
    """Bench player for someone who fouled out or is in foul trouble, same position first."""
    bench = [pid for pid in club.order if pid not in club.on_floor and pid not in club.fouled_out]
    rested = [pid for pid in bench if pid not in sitting]
    if not rested and stay_if_none:
        return out_pid                   # nobody left without foul trouble: he stays on
    bench = rested or bench
    if not bench:
        # Every bench player is out: NBA rule lets the last eligible player stay in.
        club.fouled_out.discard(out_pid)
        return out_pid
    same = [pid for pid in bench if club.players[pid].position == club.players[out_pid].position]
    return (same or bench)[0]


def validate_result(result):
    errors = spatial_result_errors(result)
    if result["final_score"]["home"] == result["final_score"]["away"]:
        errors.append("game ended tied")
    for side in ("home", "away"):
        rows = result["player_stats"][side]
        team = result["team_stats"][side]
        if sum(r["pts"] for r in rows) != result["final_score"][side]:
            errors.append(f"{side}: player points do not sum to score")
        if sum(r["tov"] for r in rows) + team.get("team_turnovers", 0) != team["tov"]:
            errors.append(f"{side}: individual and team turnovers do not reconcile")
        if sum(result["period_scores"][side]) != result["final_score"][side]:
            errors.append(f"{side}: period scores do not sum to score")
        if 2 * (team["fgm"] - team["tpm"]) + 3 * team["tpm"] + team["ftm"] != team["pts"]:
            errors.append(f"{side}: points do not reconcile with makes")
        floor_seconds = sum(r["seconds"] for r in rows)
        if abs(floor_seconds - 5 * result["game_seconds"]) > 0.01 * len(rows):
            errors.append(f"{side}: floor time {floor_seconds} != 5 x {result['game_seconds']}")
        if any("started" in row for row in rows):
            if (any(not isinstance(row.get("started"), bool) for row in rows)
                    or sum(row.get("started") is True for row in rows) != 5
                    or any(row.get("started") is True and row["seconds"] <= 0 for row in rows)):
                errors.append(f"{side}: starters must identify the five players who opened the game")
        if "transition_stats" in result:
            transition = result["transition_stats"].get(side, {})
            keys = {"possessions", "after_steal", "after_rebound", "seconds", "fga", "fgm", "points"}
            valid = (set(transition) == keys and all(
                not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v) and v >= 0
                and (key == "seconds" or isinstance(v, int)) for key, v in transition.items()))
            if not valid:
                errors.append(f"{side}: invalid transition counters")
            elif (transition["after_steal"] + transition["after_rebound"] != transition["possessions"]
                  or not transition["fgm"] <= transition["fga"] <= transition["possessions"] <= team["possessions"]
                  or transition["after_steal"] > team["stl"] or transition["after_rebound"] > team["drb"]
                  or transition["points"] > team["pts"] or transition["seconds"] > result["game_seconds"]):
                errors.append(f"{side}: transition counters do not reconcile")
        for r in rows:
            if r["fgm"] > r["fga"] or r["tpm"] > r["tpa"] or r["ftm"] > r["fta"] or r["tpa"] > r["fga"]:
                errors.append(f"{side}: {r['player_id']} has impossible shooting line")
    return errors
