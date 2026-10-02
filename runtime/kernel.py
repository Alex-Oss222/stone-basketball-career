"""Possession-level basketball kernel calibrated to a league environment.

The kernel is deterministic given its entropy bytes. Production callers never
supply those bytes: `game_runner.run_game` derives them from the private
engine-state service after the game packet is journaled.

Calibration: per-play probabilities (turnover, free-throw trip, field-goal
attempt, three-point share, make rates, offensive-rebound rate, assist, steal,
block and foul shares) are derived from the league environment's per-game
averages, so a game between two neutral clubs reproduces that era's pace and
scoring. Player ratings, when present, tilt those rates around the era mean.
"""
from dataclasses import asdict, dataclass, field
import hashlib
import math
import random

from .packets import canonical
from .player_stats import MODEL_VERSION, RATE_KEYS
from .prospects import ROOKIE_MODEL_VERSION

POSITIONS = ("PG", "SG", "SF", "PF", "C")
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
RATING_SLOPE = 0.0025
ORB_CONTINUATION_SECONDS = 7.0  # probability shift per rating point away from the mean


@dataclass(frozen=True)
class PlayerInput:
    player_id: str
    position: str
    minutes: float
    ratings: dict = field(default_factory=dict)
    stat_profile: dict = field(default_factory=dict)


@dataclass(frozen=True)
class TeamInput:
    team_id: str
    players: tuple


def team_errors(team, rules):
    errors = []
    players = list(team.players)
    ids = [p.player_id for p in players]
    if len(ids) != len(set(ids)):
        errors.append("duplicate player ids")
    if len(players) < rules["players_on_floor"]:
        errors.append("fewer than five available players")
    if len(players) > rules["game_day_actives"]:
        errors.append(f"{len(players)} actives exceeds the {rules['season']} limit of {rules['game_day_actives']}")
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
            if (set(profile) != {"bbr_id", "model_version", "as_of", "season_end_year", "source_sha256", "rates"}
                    or profile.get("model_version") not in (MODEL_VERSION, ROOKIE_MODEL_VERSION)
                    or profile.get("season_end_year") != 2003):
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
    if abs(total - regulation) > 1:
        errors.append(f"minutes targets sum to {total}, expected {regulation}")
    return errors


def team_packet(team):
    data = asdict(team)
    data["players"] = [dict(p, ratings=dict(sorted(p["ratings"].items()))) for p in data["players"]]
    return data


def calibrate(environment):
    a = environment["averages"]
    assumptions = environment["engine_assumptions"]
    fgm = a["fga"] * a["fg_pct"]
    three_m = a["three_pa"] * a["three_pct"]
    two_a = a["fga"] - a["three_pa"]
    and_one_fta = a["fta"] * assumptions["and_one_share_of_fta"]
    trips = (a["fta"] - and_one_fta) / 2
    plays = a["fga"] + a["tov"] + trips
    team_tov = environment.get("team_turnovers_per_game", 0)
    player_tov = a["tov"] - team_tov
    misses = a["fga"] - fgm
    box_possessions = plays - a["orb"]
    return {
        # The clock is calibrated so the box-score totals (FGA, TOV, FTA, ORB)
        # land on the era averages. Possessions counted from those totals run a
        # little above the published pace, whose estimator differs; the box
        # totals are what a game record shows, so they take priority.
        "possession_seconds": 2880 / (2 * box_possessions) - ORB_CONTINUATION_SECONDS * a["orb"] / box_possessions,
        "p_team_tov": team_tov / plays,
        "p_tov": player_tov / (plays - team_tov),
        "p_trip": trips / (plays - team_tov),
        "three_share": a["three_pa"] / a["fga"],
        "p_two": (fgm - three_m) / two_a,
        "p_three": a["three_pct"],
        "p_ft": a["ft_pct"],
        "p_and_one": and_one_fta / fgm,
        "p_orb": a["orb"] / misses,
        "p_player_drb": min(1.0, a["drb"] / (misses - a["orb"])),
        "p_ast": a["ast"] / fgm,
        "p_stl": a["stl"] / player_tov,
        "p_blk": a["blk"] / misses,
        "p_extra_foul": max(0.0, a["pf"] - trips - and_one_fta) / (a["pace"]),
        "home_edge": assumptions["home_edge_points_per_game"] / (2 * 2.2 * a["fga"]),
        "and_one_share_of_fta": assumptions["and_one_share_of_fta"],
        "rate_baselines": environment.get("player_rate_baselines", {}),
    }


def _rating(player, key):
    return player.ratings.get(key, RATING_MEAN) - RATING_MEAN


def _clamp(p, low=0.01, high=0.99):
    return min(high, max(low, p))


def _blank_line():
    return {k: 0 for k in ("seconds", "pts", "fgm", "fga", "tpm", "tpa", "ftm", "fta",
                           "orb", "drb", "ast", "stl", "blk", "tov", "pf")}


class _Club:
    def __init__(self, team, side):
        self.team = team
        self.side = side
        self.players = {p.player_id: p for p in team.players}
        self.order = [p.player_id for p in team.players]
        self.lines = {pid: _blank_line() for pid in self.order}
        self.on_floor = []
        self.fouled_out = set()
        self.points = 0
        self.period_points = []
        self.team_turnovers = 0


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


def _choose_lineup(club, elapsed, game_seconds):
    """Pick the five whose played time lags their target share the most."""
    candidates = [pid for pid in club.order if pid not in club.fouled_out]
    def deficit(pid):
        target = club.players[pid].minutes * 60 * (game_seconds / 2880)
        expected = target * min(1.0, (elapsed + 180) / game_seconds)
        return expected - club.lines[pid]["seconds"]
    ranked = sorted(candidates, key=lambda pid: (-deficit(pid), club.order.index(pid)))
    lineup = ranked[:5]
    # Keep one guard and one big on the floor when the bench allows it.
    for group in (("PG", "SG"), ("PF", "C")):
        if not any(club.players[pid].position in group for pid in lineup):
            replacement = next((pid for pid in ranked[5:] if club.players[pid].position in group), None)
            if replacement:
                lineup[-1] = replacement
    return lineup


def resolve_game(home, away, *, entropy, event_id, rules, environment, game_type="regular", venue="home"):
    if not isinstance(entropy, bytes) or len(entropy) < 32:
        raise ValueError("engine entropy required")
    for team in (home, away):
        errors = team_errors(team, rules)
        if errors:
            raise ValueError(f"{team.team_id}: " + "; ".join(errors))
    cal = calibrate(environment)
    if any(p.stat_profile for team in (home, away) for p in team.players):
        if any(not isinstance(cal["rate_baselines"].get(k), (int, float)) or
               not math.isfinite(cal["rate_baselines"][k]) or cal["rate_baselines"][k] <= 0
               for k in RATE_KEYS):
            raise ValueError("statistical profiles require a complete positive rate baseline")
    seed_material = entropy + canonical({"event_id": event_id, "home": team_packet(home),
                                         "away": team_packet(away), "game_type": game_type})
    rng = random.Random(int.from_bytes(hashlib.sha256(seed_material).digest(), "big"))

    clubs = {"home": _Club(home, "home"), "away": _Club(away, "away")}
    edge = {"home": cal["home_edge"], "away": -cal["home_edge"]} if venue == "home" else {"home": 0.0, "away": 0.0}
    quarter_seconds = rules["quarter_minutes"] * 60
    ot_seconds = rules["overtime_minutes"] * 60
    regulation_seconds = rules["quarters"] * quarter_seconds
    possessions = {"home": 0, "away": 0}

    def other(side):
        return "away" if side == "home" else "home"

    def credit_seconds(seconds):
        for club in clubs.values():
            for pid in club.on_floor:
                club.lines[pid]["seconds"] += seconds

    def foul(defense, kind):
        club = clubs[defense]
        weights = [rate_weight(club.players[pid], "fouls_per_minute", 6) *
                   (1.25 if not club.players[pid].stat_profile and kind == "shooting" and club.players[pid].position in ("PF", "C") else 1)
                   for pid in club.on_floor]
        pid = _weighted(rng, club.on_floor, weights)
        club.lines[pid]["pf"] += 1
        if club.lines[pid]["pf"] >= rules["foul_out_limit"]:
            club.fouled_out.add(pid)
            return pid
        return None

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
        if player.stat_profile:
            return player.stat_profile["rates"][key] / cal["rate_baselines"][key]
        return POSITION_PROFILE[player.position][position_index] * (1 + 0.02 * _rating(player, legacy_key))

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
        return side == offense

    def play(offense):
        """Resolve one possession; return True when the offense keeps the ball (offensive rebound)."""
        defense = other(offense)
        o, d = clubs[offense], clubs[defense]
        if rng.random() < cal["p_team_tov"]:
            o.team_turnovers += 1
            return False
        handlers = weights_for(o, "usage_pct", 0, "usage")
        shooter = _weighted(rng, o.on_floor, handlers)
        player = o.players[shooter]
        roll = rng.random()
        p_tov = _clamp(cal["p_tov"] - RATING_SLOPE * _rating(player, "ball_handling"), 0.03, 0.4)
        p_trip, p_and_one = cal["p_trip"], cal["p_and_one"]
        rates = player.stat_profile.get("rates")
        if rates:
            trips_per_fga = rates["free_throw_attempt_rate"] * (1-cal["and_one_share_of_fta"]) / 2
            plays_per_fga = 1 + rates["turnovers_per_fga"] + trips_per_fga
            p_tov = rates["turnovers_per_fga"] / plays_per_fga
            p_trip = trips_per_fga / plays_per_fga
            fg_pct = rates["three_point_attempt_rate"]*rates["three_point_pct"] + (1-rates["three_point_attempt_rate"])*rates["two_point_pct"]
            p_and_one = _clamp(rates["free_throw_attempt_rate"] * cal["and_one_share_of_fta"] / max(.01, fg_pct), 0, 1)
        if roll < p_tov:
            o.lines[shooter]["tov"] += 1
            weights = weights_for(d, "steal_pct", 4, "perimeter_defense")
            p_stl = cal["p_stl"] * sum(weights)/5 if any(d.players[pid].stat_profile for pid in d.on_floor) else cal["p_stl"]
            if rng.random() < _clamp(p_stl, 0, .98):
                d.lines[_weighted(rng, d.on_floor, weights)]["stl"] += 1
            return False
        if roll < p_tov + p_trip:
            fouler = foul(defense, "shooting")
            free_throws(offense, shooter, 2)
            if fouler:
                d.on_floor[d.on_floor.index(fouler)] = _replacement(d, fouler)
            return False
        if rates:
            three_share = rates["three_point_attempt_rate"]
        else:
            three_weight = POSITION_PROFILE[player.position][1] * (1 + 0.02 * _rating(player, "three_point_shooting"))
            # Keep the old positional frequency fallback for unrated players.
            mean_three = sum(h * POSITION_PROFILE[o.players[pid].position][1] for pid, h in zip(o.on_floor, handlers)) / max(.01, sum(handlers))
            three_share = _clamp(cal["three_share"] * three_weight / max(.01, mean_three), 0.0, 0.8)
        is_three = rng.random() < three_share
        defense_key = "perimeter_defense" if is_three else "interior_defense"
        def_rating = sum(_rating(d.players[pid], defense_key) for pid in d.on_floor) / 5
        if rates:
            p_make = rates["three_point_pct" if is_three else "two_point_pct"]
        elif is_three:
            p_make = cal["p_three"] + RATING_SLOPE * _rating(player, "three_point_shooting")
        else:
            finish = (_rating(player, "rim_finishing") + _rating(player, "mid_range_shooting")) / 2
            p_make = cal["p_two"] + RATING_SLOPE * finish
        p_make = _clamp(p_make - RATING_SLOPE * def_rating + edge[offense], 0.0, 1.0)
        line = o.lines[shooter]
        line["fga"] += 1
        if is_three:
            line["tpa"] += 1
        if rng.random() < p_make:
            value = 3 if is_three else 2
            line["fgm"] += 1
            line["tpm"] += int(is_three)
            line["pts"] += value
            o.points += value
            mates = [pid for pid in o.on_floor if pid != shooter]
            weights = weights_for(o, "assist_pct", 3, "passing", mates)
            p_ast = cal["p_ast"] * sum(weights)/4 if any(o.players[pid].stat_profile for pid in mates) else cal["p_ast"]
            if rng.random() < _clamp(p_ast, 0, .98):
                o.lines[_weighted(rng, mates, weights)]["ast"] += 1
            if rng.random() < p_and_one:
                fouler = foul(defense, "shooting")
                free_throws(offense, shooter, 1)
                if fouler:
                    d.on_floor[d.on_floor.index(fouler)] = _replacement(d, fouler)
            return False
        weights = weights_for(d, "block_pct", 5, "interior_defense")
        p_blk = cal["p_blk"] * sum(weights)/5 if any(d.players[pid].stat_profile for pid in d.on_floor) else cal["p_blk"]
        if rng.random() < _clamp(p_blk, 0, .98):
            d.lines[_weighted(rng, d.on_floor, weights)]["blk"] += 1
        return rebound(offense, defense)

    def run_period(number, seconds, offense, game_seconds, elapsed_before):
        for club in clubs.values():
            club.on_floor = _choose_lineup(club, elapsed_before, game_seconds)
            club.period_points.append(club.points)
        clock = seconds
        since_sub = 0.0
        while clock > 0:
            if since_sub >= 180:
                for club in clubs.values():
                    club.on_floor = _choose_lineup(club, elapsed_before + seconds - clock, game_seconds)
                since_sub = 0.0
            drawn = max(4.0, min(24.0, rng.gauss(cal["possession_seconds"], 4.5)))
            duration = min(clock, drawn)
            credit_seconds(duration)
            clock -= duration
            since_sub += duration
            # A possession the period clock cuts short only produces a play in
            # proportion to the time it had, so period ends do not inflate pace.
            if duration < drawn and rng.random() >= duration / drawn:
                break
            possessions[offense] += 1
            # Non-shooting defensive fouls (reach-ins, loose balls, illegal screens excluded).
            if rng.random() < cal["p_extra_foul"]:
                fouler = foul(other(offense), "common")
                if fouler:
                    d = clubs[other(offense)]
                    d.on_floor[d.on_floor.index(fouler)] = _replacement(d, fouler)
            kept = play(offense)
            while kept and clock > 0:
                extra = min(clock, max(2.0, rng.gauss(ORB_CONTINUATION_SECONDS, 3.0)))
                credit_seconds(extra)
                clock -= extra
                since_sub += extra
                kept = play(offense)
            offense = other(offense)
        for club in clubs.values():
            club.period_points[-1] = club.points - club.period_points[-1]

    tip_winner = "home" if rng.random() < 0.5 else "away"
    starts = {1: tip_winner, 2: other(tip_winner), 3: other(tip_winner), 4: tip_winner}
    elapsed = 0
    for q in range(1, rules["quarters"] + 1):
        run_period(q, quarter_seconds, starts[q], regulation_seconds, elapsed)
        elapsed += quarter_seconds
    overtimes = 0
    while clubs["home"].points == clubs["away"].points:
        overtimes += 1
        game_seconds = regulation_seconds + overtimes * ot_seconds
        run_period(rules["quarters"] + overtimes, ot_seconds,
                   "home" if rng.random() < 0.5 else "away", game_seconds, elapsed)
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
        "game_seconds": elapsed,
        "terminated": True,
    }


def _replacement(club, fouled_out_pid):
    """Bench player for someone who just fouled out, same position first."""
    bench = [pid for pid in club.order if pid not in club.on_floor and pid not in club.fouled_out]
    if not bench:
        # Every bench player is out: NBA rule lets the last eligible player stay in.
        club.fouled_out.discard(fouled_out_pid)
        return fouled_out_pid
    same = [pid for pid in bench if club.players[pid].position == club.players[fouled_out_pid].position]
    return (same or bench)[0]


def validate_result(result):
    errors = []
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
        for r in rows:
            if r["fgm"] > r["fga"] or r["tpm"] > r["tpa"] or r["ftm"] > r["fta"] or r["tpa"] > r["fga"]:
                errors.append(f"{side}: {r['player_id']} has impossible shooting line")
    return errors
