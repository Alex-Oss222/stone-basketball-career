"""The only production game entry point, for Wade's games and background games alike."""
import hashlib
import inspect

from . import KERNEL_VERSION
from .era import allowed_game_types, environment_for, rules_for, season_for_date
from .kernel import resolve_game, team_errors, team_packet, validate_result

ENTROPY_DOMAIN = b"stone-basketball-career/event-entropy/v1\0"
VENUES = ("home", "neutral")


def build_game_packet(home, away, *, event_id, game_date, game_type="regular", venue="home"):
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
    environment = environment_for(season, game_date)
    packet = {
        "procedure": KERNEL_VERSION, "event_id": event_id,
        "season": season, "game_date": game_date, "game_type": game_type, "venue": venue,
        "baseline_season": environment["season"],
        "home": team_packet(home), "away": team_packet(away),
    }
    return packet, rules, environment


def entropy_from_ref(result_ref):
    if not isinstance(result_ref, str) or len(result_ref) != 64:
        raise ValueError("invalid opaque event reference")
    return hashlib.sha256(ENTROPY_DOMAIN + bytes.fromhex(result_ref)).digest()


def run_game(home, away, *, event_id, game_date, journal, game_type="regular", venue="home"):
    """Journal the packet in the engine store, then and only then resolve the game.

    There is deliberately no seed parameter. The same event with the same
    inputs reproduces the same game; the same event with changed inputs is
    refused by the journal.
    """
    packet, rules, environment = build_game_packet(
        home, away, event_id=event_id, game_date=game_date, game_type=game_type, venue=venue)
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
