"""Game requests: the files that tell the Railway engine which games to play.

A request lives next to its game note as `Game_N.request.json` and names the
two clubs and the game. When the branch Railway tracks is pushed, Railway
rebuilds, the engine plays every request it has not played yet, and the result
appears at `/games/<event_id>`. A request that is already played is replayed
identically; a request whose inputs were edited after it was played is refused.

    {
      "event_id": "2003-10-28-orl-at-mia",
      "game_date": "2003-10-28",
      "game_type": "regular",
      "venue": "home",
      "home": {"team": "Miami Heat", "players": [
          {"player_id": "Dwyane Wade", "position": "SG", "minutes": 34, "ratings": {}}, ...]},
      "away": {"team": "Orlando Magic", "baseline": "library/2003/league/nba_2003_end_of_season.json"}
    }

A club is one of:
* an explicit `players` list (minutes summing to 240), which is how Miami's
  AI/GM states its rotation from the depth chart;
* `"rotation": "real"`: a real club's real roster on the game's date, with
  minutes per game and availability, less any player simulated Miami holds
  (`runtime/rotations.py`, world model D);
* a `baseline` library file, from which `runtime.league.baseline_team` builds a
  conventional rotation (the older end-of-2002-03 default).

An explicit rotation may give every player a `starter` boolean, with five
true values. These are the staff's starters for this game, including injury
replacements. The engine records the actual opening five in its closed box;
historical requests without these flags keep their original lineup policy.
"""
import json
from pathlib import Path

from .era import rules_for, season_for_date
from .game_runner import build_game_packet
from .kernel import PlayerInput, TeamInput
from .league import baseline_team, load_clubs
from .player_stats import load_rating_index
from dataclasses import replace

from .injuries import rest_days, simulated_ages
from .player_stats import alias
from .rosters import SIMULATED_CLUB
from .rotations import club_pace, load_rosters, miami_departed, miami_departures, miami_holds, real_rotation, season_fraction
from .schedule import games_per_team

ROOT = Path(__file__).resolve().parents[1]
FIELDS = {"event_id", "game_date", "game_type", "venue", "home", "away"}


def find_requests(root=ROOT):
    return sorted((Path(root) / "career").rglob("*.request.json"))


def _club(spec, actives, root, rating_index, season=None, game_date=None):
    if not isinstance(spec, dict) or not isinstance(spec.get("team"), str):
        raise ValueError("each club needs a team name")
    if sum(key in spec for key in ("players", "baseline", "rotation")) != 1:
        raise ValueError(f"{spec['team']}: give exactly one of players, baseline or rotation")
    rest = rest_days(season, spec["team"], game_date, root) if season and game_date else 2
    if "rotation" in spec:
        if spec["rotation"] != "real" or set(spec) != {"team", "rotation"}:
            raise ValueError(f"{spec['team']}: the only rotation is \"real\"")
        rosters = load_rosters(season, root)
        if spec["team"] not in rosters:
            raise ValueError(f"{spec['team']} has no real {season} roster (Miami is simulated)")
        # Rule 2: players simulated Miami holds are not with their real club; rule 3: players Miami sent arrive at the
        # partner only (`arrivals` re-adds them there), never also at the club history gave them.
        team = real_rotation(spec["team"], rosters[spec["team"]], games_per_team(season, spec["team"]), rating_index,
                             fraction=season_fraction(season, game_date, root),
                             exclude=miami_holds(season, game_date, root) | miami_departed(season, game_date, root),
                             arrivals=miami_departures(season, spec["team"], game_date, root),
                             pace=club_pace(season, spec["team"], root))
        return replace(team, rest_days=rest)
    if "baseline" in spec:
        clubs = load_clubs(Path(root) / spec["baseline"])
        if spec["team"] not in clubs:
            raise ValueError(f"{spec['team']} is not in {spec['baseline']}")
        return replace(baseline_team(spec["team"], clubs[spec["team"]], actives, rating_index), rest_days=rest)
    # The simulated club's players are exposed to the engine's injury draws, with their ages.
    simulated = spec["team"] == SIMULATED_CLUB
    ages = simulated_ages(season, game_date, root) if simulated and season and game_date else {}
    players = []
    starter_flags = [p.get("starter") for p in spec["players"]]
    explicit_starters = any("starter" in p for p in spec["players"])
    if explicit_starters and any(type(flag) is not bool for flag in starter_flags):
        raise ValueError(f"{spec['team']}: starter must be a boolean for every player when supplied")
    for p in spec["players"]:
        unknown = set(p) - {"player_id", "bbr_id", "position", "minutes", "ratings", "starter"}
        if unknown:
            raise ValueError(f"{spec['team']}: unknown player fields {sorted(unknown)}")
        profile = rating_index.engine_profile(p["player_id"], p.get("bbr_id")) if rating_index else {}
        players.append(PlayerInput(p["player_id"], p["position"], p["minutes"], dict(p.get("ratings", {})), profile,
                                   age=ages.get(alias(p["player_id"]))))
    starters = tuple(p["player_id"] for p in spec["players"] if p.get("starter") is True)
    if explicit_starters and len(starters) != 5:
        raise ValueError(f"{spec['team']}: exactly five players must be marked starter")
    return TeamInput(spec["team"], tuple(players), rest_days=rest, injuries=simulated, starters=starters)


def load_request(path, root=ROOT):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or set(data) != FIELDS:
        raise ValueError(f"request fields must be exactly {sorted(FIELDS)}")
    season = season_for_date(data["game_date"])
    actives = rules_for(season)["game_day_actives"]
    index = load_rating_index(data["game_date"], season, root)
    home = _club(data["home"], actives, root, index, season, data["game_date"])
    away = _club(data["away"], actives, root, index, season, data["game_date"])
    kwargs = {k: data[k] for k in ("event_id", "game_date", "game_type", "venue")}
    kwargs["root"] = root
    build_game_packet(home, away, validation_only=True, **kwargs)  # common inputs only; runner freezes the selected kernel's sources
    return home, away, kwargs


def request_errors(root=ROOT):
    """Every request in the repository: the engine's full check for Miami's game requests (each has a
    game note), structural checks for all of the league slate plus the engine's check on a sample
    (`runtime/season_games.py`, since the slate has 1,189 requests), and unique event ids throughout."""
    from .season_games import is_league_slate, slate_errors
    errors, seen, slate = [], {}, []
    for path in find_requests(root):
        rel = path.relative_to(root)
        if is_league_slate(path):
            slate.append(path)
            try:
                event_id = json.loads(path.read_text(encoding="utf-8"))["event_id"]
            except (OSError, KeyError, TypeError, ValueError) as exc:
                errors.append(f"{rel}: {exc}")
                continue
        else:
            try:
                _, _, kwargs = load_request(path, root)
            except (OSError, KeyError, TypeError, ValueError) as exc:
                errors.append(f"{rel}: {exc}")
                continue
            event_id = kwargs["event_id"]
        if event_id in seen:
            errors.append(f"{rel}: event_id also used by {seen[event_id]}")
        seen[event_id] = rel
    errors.extend(slate_errors(slate, root))
    return errors
