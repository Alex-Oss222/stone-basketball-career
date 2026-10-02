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

A club is either an explicit `players` list (minutes summing to 240) or a
`baseline` library file, from which `runtime.league.baseline_team` builds the
default rotation for a background club.
"""
import json
from pathlib import Path

from .era import rules_for, season_for_date
from .game_runner import build_game_packet
from .kernel import PlayerInput, TeamInput
from .league import baseline_team, load_clubs

ROOT = Path(__file__).resolve().parents[1]
FIELDS = {"event_id", "game_date", "game_type", "venue", "home", "away"}


def find_requests(root=ROOT):
    return sorted((Path(root) / "career").rglob("*.request.json"))


def _club(spec, actives, root):
    if not isinstance(spec, dict) or not isinstance(spec.get("team"), str):
        raise ValueError("each club needs a team name")
    if ("players" in spec) == ("baseline" in spec):
        raise ValueError(f"{spec['team']}: give exactly one of players or baseline")
    if "baseline" in spec:
        clubs = load_clubs(Path(root) / spec["baseline"])
        if spec["team"] not in clubs:
            raise ValueError(f"{spec['team']} is not in {spec['baseline']}")
        return baseline_team(spec["team"], clubs[spec["team"]], actives)
    players = []
    for p in spec["players"]:
        unknown = set(p) - {"player_id", "position", "minutes", "ratings"}
        if unknown:
            raise ValueError(f"{spec['team']}: unknown player fields {sorted(unknown)}")
        players.append(PlayerInput(p["player_id"], p["position"], p["minutes"], dict(p.get("ratings", {}))))
    return TeamInput(spec["team"], tuple(players))


def load_request(path, root=ROOT):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or set(data) != FIELDS:
        raise ValueError(f"request fields must be exactly {sorted(FIELDS)}")
    actives = rules_for(season_for_date(data["game_date"]))["game_day_actives"]
    home = _club(data["home"], actives, root)
    away = _club(data["away"], actives, root)
    kwargs = {k: data[k] for k in ("event_id", "game_date", "game_type", "venue")}
    build_game_packet(home, away, **kwargs)  # full validation, nothing journaled
    return home, away, kwargs


def request_errors(root=ROOT):
    errors, seen = [], {}
    for path in find_requests(root):
        rel = path.relative_to(root)
        try:
            _, _, kwargs = load_request(path, root)
        except (OSError, KeyError, TypeError, ValueError) as exc:
            errors.append(f"{rel}: {exc}")
            continue
        if kwargs["event_id"] in seen:
            errors.append(f"{rel}: event_id also used by {seen[kwargs['event_id']]}")
        seen[kwargs["event_id"]] = rel
    return errors
