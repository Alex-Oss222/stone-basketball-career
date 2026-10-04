"""The only production game entry point, for Wade's games and background games alike."""
import hashlib
import inspect

from . import KERNEL_VERSION
from .era import allowed_game_types, environment_for, rules_for, season_for_date
from .kernel import resolve_game, team_errors, team_packet, validate_result
from .player_stats import ROOT, MODEL_VERSION, load_rating_index
from .trajectories import develop_profile, development_refs, development_seasons, needs_development
from dataclasses import replace

ENTROPY_DOMAIN = b"stone-basketball-career/event-entropy/v1\0"
VENUES = ("home", "neutral")


def build_game_packet(home, away, *, event_id, game_date, game_type="regular", venue="home", root=ROOT,
                      kernel_version=None, validation_only=False):
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
            expected = index.engine_profile(profile["bbr_id"]) if index is not None else None
            if expected and "development" in profile:
                # A developed trajectory must equal the expected path moved by its journaled draws.
                refs = profile["development"]
                if sorted(refs) != development_seasons(profile["bbr_id"], season):
                    raise ValueError("profile lacks its journaled development draws")
                expected = develop_profile(expected, refs)
            if profile != expected:
                raise ValueError("statistical profile differs from the dated, generated source")
        if environment.get("player_rating_model") != MODEL_VERSION or environment.get("player_rate_baselines") != index.data["rate_baselines"]:
            raise ValueError("league environment and player rating model do not match")
    # Request parsing checks common dated inputs without requiring a future
    # kernel's spatial source to replay an older, already closed game.
    if validation_only:
        return None, rules, environment
    procedure = kernel_version or KERNEL_VERSION
    packet = {
        "procedure": procedure, "event_id": event_id,
        "season": season, "game_date": game_date, "game_type": game_type, "venue": venue,
        "baseline_season": environment["season"],
        "environment": environment,
        "home": team_packet(home), "away": team_packet(away),
    }
    if spatial_kernel(procedure):
        from .spatial_shots import load_spatial_environment
        packet["spatial_environment"] = load_spatial_environment(season, game_date, root)
    return packet, rules, environment


def spatial_kernel(version):
    """Only new kernels journal spatial inputs; legacy packets retain their shape."""
    try:
        parts = tuple(int(part) for part in version.split("."))
    except (AttributeError, ValueError) as exc:
        raise ValueError("invalid kernel version") from exc
    if len(parts) != 2:
        raise ValueError("invalid kernel version")
    return parts >= (2003, 7)


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
    home, away, packet, rules, environment = freeze_inputs(
        home, away, journal, event_id=event_id, game_date=game_date, game_type=game_type, venue=venue, root=root)
    if any(needs_development(p.stat_profile) and "development" not in p.stat_profile
           for team in (home, away) for p in team.players):
        raise RuntimeError("a developing player reached the journal without a development draw")
    result_ref = journal.close_event(packet)  # durable closure precedes the draw
    result = resolve_game(home, away, entropy=entropy_from_ref(result_ref), event_id=event_id,
                          rules=rules, environment=environment, game_type=game_type, venue=venue,
                          spatial_environment=packet.get("spatial_environment"))
    errors = validate_result(result)
    if errors:
        raise RuntimeError("kernel invariant failure: " + "; ".join(errors))
    result["game_date"] = game_date
    result["kernel"] = KERNEL_VERSION
    return result


def freeze_inputs(home, away, journal, **kwargs):
    """Apply journaled development draws, then build the packet exactly as it is journaled.

    Shared by run_game and the service's replay check, so a redeploy recomputes
    the same packet digest for a game that is already played.
    """
    season = season_for_date(kwargs["game_date"])
    # Real-career players (option C) and Wade get this season's journaled swing before inputs freeze.
    home, away = (_developed(team, season, journal) for team in (home, away))
    # Real clubs' absences as journaled spells from November 12, 2003 (`absence_spells`); earlier games unchanged.
    from .absence_spells import apply_spells
    home, away = (apply_spells(team, season, kwargs["game_date"], journal, kwargs.get("root", ROOT)) for team in (home, away))
    packet, rules, environment = build_game_packet(home, away, **kwargs)
    return home, away, packet, rules, environment


def replay_packet(home, away, journal, result, **kwargs):
    """Reconstruct an already played game's packet without running an old kernel.

    The store serves its first result verbatim across engine upgrades. All dated
    inputs must still hash to the original journal entry, but the procedure is
    the version that actually played the game, not the newly deployed version.
    This is only for checking a stored result; unfinished events go through the
    current runner and fail closed if their original packet no longer matches.
    """
    if result.get("event_id") != kwargs["event_id"]:
        raise ValueError("stored result does not match the game event")
    kernel = result.get("kernel")
    if not isinstance(kernel, str) or not kernel.strip():
        raise ValueError("stored game result has no kernel version")
    # Select the original input schema before loading additional data. Changing
    # or adding a spatial prior must never modify a pre-tracking packet hash.
    return freeze_inputs(home, away, journal, kernel_version=kernel, **kwargs)[2]


def _developed(team, season, journal):
    players = []
    for p in team.players:
        profile = p.stat_profile
        if needs_development(profile) and "development" not in profile:
            refs = development_refs(journal, profile["bbr_id"], season)
            profile = develop_profile(profile, refs)
            p = replace(p, stat_profile=profile)
        players.append(p)
    return replace(team, players=tuple(players))


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
