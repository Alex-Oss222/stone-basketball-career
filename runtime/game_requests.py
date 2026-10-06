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
from .rotations import club_pace, load_rosters, miami_departed, miami_departures, miami_holds, real_rotation, rotation_model, season_fraction
from .schedule import games_per_team

ROOT = Path(__file__).resolve().parents[1]
FIELDS = {"event_id", "game_date", "game_type", "venue", "home", "away"}
# From this date each request also carries both clubs' engine inputs as the builder computed them from the dated
# records (rosters, minutes, availability, ratings, ages, rest, pace), frozen before the engine's own draws
# (development swings and absence spells stay in the engine). The engine then needs no deployed copy of the
# changing career records to play a game, so a roster move no longer forces a redeploy. Validation recomputes the
# frozen inputs from the committed records and refuses any difference.
FROZEN_FROM = "2004-01-22"


def team_from_packet(data):
    """A TeamInput from its `kernel.team_packet` form (the inverse of team_packet)."""
    players = tuple(PlayerInput(**p) for p in data["players"])
    return TeamInput(data["team_id"], players, pace=data["pace"], rest_days=data["rest_days"], injuries=data["injuries"],
                     starters=tuple(data.get("starters", ())), season_roster=data.get("season_roster", False))


def computed_inputs(data, root=ROOT):
    """Both clubs' engine inputs computed from the request's club specs and the dated records."""
    season = season_for_date(data["game_date"])
    actives = rules_for(season)["game_day_actives"]
    index = load_rating_index(data["game_date"], season, root)
    home = _club(data["home"], actives, root, index, season, data["game_date"])
    away = _club(data["away"], actives, root, index, season, data["game_date"])
    if data.get("game_type") == "playoff":
        # A real club's season share of missed games describes the regular season; in the playoffs every real player is
        # available (design choice, docs/front_office.md). Miami's players carry their own engine-drawn injuries.
        home, away = (replace(t, players=tuple(replace(p, availability=1.0) for p in t.players), season_roster=True)
                      if "rotation" in spec else t          # the engine dresses twelve and allocates the minutes
                      for t, spec in ((home, data["home"]), (away, data["away"])))
    return home, away


def freeze(data, root=ROOT):
    """The request with its clubs' inputs frozen, for a game on or after FROZEN_FROM; otherwise unchanged."""
    if data["game_date"] < FROZEN_FROM:
        return data
    from .kernel import team_packet
    home, away = computed_inputs(data, root)
    frozen = json.loads(json.dumps({"home": team_packet(home), "away": team_packet(away)}))
    return {**{k: v for k, v in data.items() if k != "frozen"}, "frozen": frozen}


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
        # A disturbed club's replacement (runtime/club_replacements.py) arrives there and leaves his later real club.
        from .club_replacements import arrivals as replacement_arrivals, held as replacements_held
        # Symmetric league (docs/symmetric_league_design.md): the club's simulated roster, only once switched on.
        from .league_book import active as symmetric_active
        if symmetric_active(game_date):
            from .league_moves import simulated_club
            club_entry = simulated_club(spec["team"], game_date, season, root)
        else:
            club_entry = rosters[spec["team"]]
        team = real_rotation(spec["team"], club_entry, games_per_team(season, spec["team"]), rating_index,
                             fraction=season_fraction(season, game_date, root),
                             exclude=(miami_holds(season, game_date, root) | miami_departed(season, game_date, root)
                                      | replacements_held(season, game_date, root)),
                             arrivals=(miami_departures(season, spec["team"], game_date, root)
                                       + replacement_arrivals(season, spec["team"], game_date, root)),
                             pace=club_pace(season, spec["team"], root), model=rotation_model(game_date))
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
        unknown = set(p) - {"player_id", "bbr_id", "position", "minutes", "ratings", "starter", "returning"}
        if unknown:
            raise ValueError(f"{spec['team']}: unknown player fields {sorted(unknown)}")
        profile = rating_index.engine_profile(p["player_id"], p.get("bbr_id")) if rating_index else {}
        players.append(PlayerInput(p["player_id"], p["position"], p["minutes"], dict(p.get("ratings", {})), profile,
                                   age=ages.get(alias(p["player_id"])), returning=p.get("returning", 0)))
    starters = tuple(p["player_id"] for p in spec["players"] if p.get("starter") is True)
    if explicit_starters and len(starters) != 5:
        raise ValueError(f"{spec['team']}: exactly five players must be marked starter")
    from .injuries import paused
    # The injury model is off while paused (the user's premise, runtime/injuries.INJURY_PAUSE); earlier games unchanged.
    return TeamInput(spec["team"], tuple(players), rest_days=rest, injuries=simulated and not paused(game_date),
                     starters=starters)


def load_request(path, root=ROOT):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or set(data) not in (FIELDS, FIELDS | {"frozen"}):
        raise ValueError(f"request fields must be exactly {sorted(FIELDS)} (plus frozen from {FROZEN_FROM})")
    if "frozen" in data:
        if data["game_date"] < FROZEN_FROM:
            raise ValueError(f"frozen inputs start with games on {FROZEN_FROM}")
        frozen = data["frozen"]
        if not isinstance(frozen, dict) or set(frozen) != {"home", "away"}:
            raise ValueError("frozen must hold exactly the home and away inputs")
        home, away = team_from_packet(frozen["home"]), team_from_packet(frozen["away"])
        if (home.team_id, away.team_id) != (data["home"]["team"], data["away"]["team"]):
            raise ValueError("frozen inputs name different clubs from the request")
    else:
        if data["game_date"] >= FROZEN_FROM:
            raise ValueError(f"a game on or after {FROZEN_FROM} carries its frozen inputs")
        home, away = computed_inputs(data, root)
    kwargs = {k: data[k] for k in ("event_id", "game_date", "game_type", "venue")}
    kwargs["root"] = root
    build_game_packet(home, away, validation_only=True, **kwargs)  # common inputs only; runner freezes the selected kernel's sources
    return home, away, kwargs


def input_fingerprint(path, root=ROOT):
    """SHA-256 of everything a game reads from the repository before the engine journal: both clubs' inputs
    (rosters, rotations, ratings, ages, rest, pace), the request's fields, the league environment and the
    spatial environment. The direct game route (`POST /games`) refuses a game whose fingerprint on the
    engine's deployed copy differs from the caller's, so a game played there replays identically at the
    next boot."""
    import hashlib
    from .era import environment_for, season_for_date
    from .kernel import team_packet
    from .packets import canonical
    from .spatial_shots import load_spatial_environment
    home, away, kwargs = load_request(path, root)
    season = season_for_date(kwargs["game_date"])
    material = {"home": team_packet(home), "away": team_packet(away),
                "fields": {k: kwargs[k] for k in ("event_id", "game_date", "game_type", "venue")},
                "environment": environment_for(season, kwargs["game_date"], root),
                "spatial": load_spatial_environment(season, kwargs["game_date"], root)}
    return hashlib.sha256(canonical(material)).hexdigest()


def frozen_errors(root=ROOT, recent_days=3, every=25):
    """Frozen inputs that differ from what the committed records give for the same request: every request not yet
    played, every one dated within `recent_days` of the career clock, and every `every`th of the rest."""
    from datetime import date, timedelta
    from .kernel import team_packet
    state = json.loads((Path(root) / "career/Dwyane_Wade/2003-04/current_state.json").read_text(encoding="utf-8"))
    since = (date.fromisoformat(state["current_date"]) - timedelta(days=recent_days)).isoformat()
    errors, k = [], 0
    for path in find_requests(root):
        data = json.loads(path.read_text(encoding="utf-8"))
        if "frozen" not in data:
            continue
        k += 1
        played = path.with_name(path.name.replace(".request.json", ".result.json")).exists()
        if played and data["game_date"] < since and k % every:
            continue
        try:
            home, away = computed_inputs(data, root)
            if json.loads(json.dumps({"home": team_packet(home), "away": team_packet(away)})) != data["frozen"]:
                errors.append(f"{path.relative_to(root)}: frozen inputs differ from the committed records")
        except (OSError, KeyError, TypeError, ValueError) as exc:
            errors.append(f"{path.relative_to(root)}: cannot recompute frozen inputs: {exc}")
    return errors


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


HARDEN_SEASON = "2004-05"


def schedule_id_errors(root=ROOT):
    """Roadmap 18b: from 2004-05 every game request's event id is a scheduled game's id (regular season or preseason
    schedule, or a game the playoff bracket created), so a game cannot be re-drawn under a new id."""
    from .era import season_for_date
    root = Path(root)
    errors, known = [], {}
    for path in find_requests(root):
        data = json.loads(path.read_text(encoding="utf-8"))
        day = data.get("game_date")
        if not isinstance(day, str):
            continue
        season = season_for_date(day)
        if season < HARDEN_SEASON:
            continue
        if season not in known:
            ids = set()
            start = int(season[:4])
            for name in (f"nba_{start}_{str(start + 1)[-2:]}_schedule.json", f"nba_{start}_{str(start + 1)[-2:]}_preseason_schedule.json"):
                f = root / "library" / str(start) / "league" / name
                if f.is_file():
                    ids |= {g.get("game_id") for g in json.loads(f.read_text(encoding="utf-8"))["games"]}
            bracket = root / f"career/Dwyane_Wade/Stats_and_Awards/League/{season}/playoffs.json"
            if bracket.is_file():
                ids |= {g.get("event_id") for s in json.loads(bracket.read_text(encoding="utf-8"))["series"] for g in s["games"]}
            known[season] = ids
        if data.get("event_id") not in known[season]:
            errors.append(f"{path.relative_to(root)}: event id {data.get('event_id')} is not a scheduled {season} game")
    return errors
