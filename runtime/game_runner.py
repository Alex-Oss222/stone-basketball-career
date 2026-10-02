"""The only production game entry point, for Wade's games and background games alike."""
import hashlib
import inspect

from . import KERNEL_VERSION
from .era import allowed_game_types, environment_for, rules_for, season_for_date
from .kernel import resolve_game, team_errors, team_packet, validate_result
from .player_stats import ROOT, MODEL_VERSION, load_rating_index

ENTROPY_DOMAIN = b"stone-basketball-career/event-entropy/v1\0"
VENUES = ("home", "neutral")


def build_game_packet(home, away, *, event_id, game_date, game_type="regular", venue="home", root=ROOT):
    """Validate every input and freeze the canonical packet. Fails before anything is journaled."""
    if not isinstance(event_id, str) or not event_id.strip():
        raise ValueError("event_id required")
    season = season_for_date(game_date)
    rules = rules_for(season)
    if game_type not in allowed_game_types(season):
        raise ValueError(f"{game_type} games do not exist in {season}")
    if venue not in VENUES:
        raise ValueError("venue must be home or neutral")
    if home.team_id == away.team_id:
        raise ValueError("teams must differ")
    for team in (home, away):
        errors = team_errors(team, rules)
        if errors:
            raise ValueError(f"{team.team_id}: " + "; ".join(errors))
    environment = environment_for(season, game_date, root)
    profiles = [p.stat_profile for team in (home, away) for p in team.players if p.stat_profile]
    if profiles:
        ids = [profile["bbr_id"] for profile in profiles]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate Basketball-Reference IDs in game inputs")
        index = load_rating_index(game_date, season, root)
        for profile in profiles:
            if index is None or profile != index.engine_profile(profile["bbr_id"]):
                raise ValueError("statistical profile differs from the dated, generated source")
        if environment.get("player_rating_model") != MODEL_VERSION or environment.get("player_rate_baselines") != index.data["rate_baselines"]:
            raise ValueError("league environment and player rating model do not match")
    packet = {
        "procedure": KERNEL_VERSION, "event_id": event_id,
        "season": season, "game_date": game_date, "game_type": game_type, "venue": venue,
        "baseline_season": environment["season"],
        "environment": environment,
        "home": team_packet(home), "away": team_packet(away),
    }
    return packet, rules, environment


def entropy_from_ref(result_ref):
    if not isinstance(result_ref, str) or len(result_ref) != 64:
        raise ValueError("invalid opaque event reference")
    return hashlib.sha256(ENTROPY_DOMAIN + bytes.fromhex(result_ref)).digest()


def run_game(home, away, *, event_id, game_date, journal, game_type="regular", venue="home", root=ROOT):
    """Journal the packet in the engine store, then and only then resolve the game.

    There is deliberately no seed parameter. The same event with the same
    inputs reproduces the same game; the same event with changed inputs is
    refused by the journal.
    """
    packet, rules, environment = build_game_packet(
        home, away, event_id=event_id, game_date=game_date, game_type=game_type, venue=venue, root=root)
    result_ref = journal.close_event(packet)  # durable closure precedes the draw
    result = resolve_game(home, away, entropy=entropy_from_ref(result_ref), event_id=event_id,
                          rules=rules, environment=environment, game_type=game_type, venue=venue)
    errors = validate_result(result)
    if errors:
        raise RuntimeError("kernel invariant failure: " + "; ".join(errors))
    result["game_date"] = game_date
    result["kernel"] = KERNEL_VERSION
    return result


def architecture_errors():
    errors = []
    params = inspect.signature(run_game).parameters
    if "seed" in params or "entropy" in params:
        errors.append("production runner accepts caller-supplied randomness")
    source = inspect.getsource(run_game)
    if "close_event(" not in source:
        errors.append("production runner does not journal the event")
    elif source.find("close_event(") > source.find("resolve_game("):
        errors.append("kernel can run before event closure")
    return errors
