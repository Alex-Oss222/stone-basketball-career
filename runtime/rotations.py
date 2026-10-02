"""Rotations for real clubs (roadmap item 8, world model D).

A real club's game input is its real season roster
(`library/<year>/league/nba_<season>_team_rosters.json`) on the game's date.
Each player brings his minutes per game played and his availability, the share
of the club's games he played while with it. A traded player is with each club
only for his stint's part of the season (`window`), so he is never on two clubs
at once; this uses season totals and the order of his stints, never dates or
results from history. The engine draws who is available for a given game,
dresses the top of the rotation and fills the 240 minutes in rotation order
(`runtime/kernel.py`). Season-share minutes would give a star who missed half
the season half his minutes every night; this gives him his real minutes on
the nights he plays.

Conflict rules (AGENTS.md, option D):
1. A real Miami transaction is skipped at import (`scripts/import_careers.py`):
   a stint it began is folded into the player's previous club, and a player
   real Miami brought in between seasons is back on the club that had him
   (`returned`), with his previous season's minutes and games played.
2. Players simulated Miami holds on the game date are taken out of every real
   club (`miami_holds`, from the dated holdings record next to the register),
   so a later roster move never changes a game already played.
3. Departing players' minutes go to arrivals (and returned players) up to
   their own previous share; the rest raises the staying rotation in
   proportion to real minutes. When the arrivals' shares are larger than the
   departing minutes, the difference comes out of the staying rotation in
   the same proportion.
Miami's own rotation comes from its depth chart, never from this module.
"""
from datetime import date
import json
from pathlib import Path

from .kernel import POSITIONS, PlayerInput, TeamInput
from .player_stats import alias

ROOT = Path(__file__).resolve().parents[1]
MAX_MINUTES_PER_GAME = 44.0     # input sanity bound; the kernel's caps decide game minutes
NOT_HELD = ("free_agent", "released", "waived", "renounced", "traded", "retired")


def rosters_path(season):
    start = int(season[:4])
    return Path(f"library/{start}/league/nba_{start}_{str(start + 1)[-2:]}_team_rosters.json")


def load_rosters(season, root=ROOT):
    return json.loads((Path(root) / rosters_path(season)).read_text(encoding="utf-8"))["clubs"]


PACE_LIMITS = (0.85, 1.15)      # relative club pace; real clubs of this era sit well inside it


def pace_path(season):
    start = int(season[:4])
    return Path(f"library/{start}/league/nba_{start}_{str(start + 1)[-2:]}_team_pace.json")


def club_pace(season, club_name, root=ROOT):
    """A real club's pace relative to the league, from the season before (1.0 without a pace file)."""
    path = Path(root) / pace_path(season)
    if not path.exists():
        return 1.0
    return json.loads(path.read_text(encoding="utf-8"))["clubs"][club_name]["relative_pace"]


def pace_errors(root=ROOT):
    errors = []
    for path in sorted((Path(root) / "library").glob("*/league/nba_*_team_pace.json")):
        rel = path.relative_to(root)
        data = json.loads(path.read_text(encoding="utf-8"))
        season = data.get("season", "")
        try:
            clubs = set(load_rosters(season, root))
        except (OSError, ValueError):
            errors.append(f"{rel}: no real rosters for {season!r}")
            continue
        if data.get("kind") != "team_pace" or set(data.get("clubs", {})) != clubs:
            errors.append(f"{rel}: must be kind team_pace and cover exactly the season's real clubs")
            continue
        if int(data["source_season"][:4]) != int(season[:4]) - 1:
            errors.append(f"{rel}: pace must come from the season before")
        for club, entry in data["clubs"].items():
            value = entry.get("relative_pace")
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not PACE_LIMITS[0] <= value <= PACE_LIMITS[1]:
                errors.append(f"{rel}: {club}: relative pace out of range")
    return errors


def season_fraction(season, game_date, root=ROOT):
    """Where a date falls in the regular season, 0 at the first game and 1 at the last."""
    from .schedule import schedule_path
    games = json.loads(schedule_path(season, root).read_text(encoding="utf-8"))["games"]
    first, last = (date.fromisoformat(d) for d in (min(g["date"] for g in games), max(g["date"] for g in games)))
    day = date.fromisoformat(game_date)
    return min(1.0, max(0.0, (day - first).days / max(1, (last - first).days)))


def holdings_path(season):
    return Path(f"career/Dwyane_Wade/{season}/00_Team/Team/Roster/holdings.json")


def miami_holds(season, game_date, root=ROOT):
    """Players simulated Miami holds on `game_date` (rule 2), from its dated holdings record.

    Returns Basketball-Reference IDs, plus name keys only for entries without an ID, so a
    namesake on a real club is never taken for a Miami player."""
    path = Path(root) / holdings_path(season)
    if not path.exists():
        return frozenset()
    held = set()
    for e in json.loads(path.read_text(encoding="utf-8"))["entries"]:
        if e["from"] <= game_date and (e["until"] is None or game_date < e["until"]):
            held.add(e["bbr_id"] or alias(e["player"]))
    return frozenset(held)


def holdings_errors(root=ROOT):
    """Each season's holdings record must be well formed and cover every player the register holds."""
    errors = []
    for register in sorted((Path(root) / "career/Dwyane_Wade").glob("*/00_Team/Team/Roster/roster.json")):
        season = register.parts[-5]
        path = Path(root) / holdings_path(season)
        rel = path.relative_to(root)
        if not path.exists():
            errors.append(f"{rel}: missing; conflict rule 2 needs Miami's dated holdings")
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("kind") != "miami_holdings" or data.get("owner") != "ai_gm" or not isinstance(data.get("entries"), list):
            errors.append(f"{rel}: needs kind miami_holdings, owner ai_gm and an entries list")
            continue
        for e in data["entries"]:
            try:
                start = date.fromisoformat(e["from"])
                end = None if e["until"] is None else date.fromisoformat(e["until"])
                if end is not None and end <= start:
                    errors.append(f"{rel}: {e['player']}: until must be after from")
                if e["bbr_id"] is not None and not isinstance(e["bbr_id"], str):
                    errors.append(f"{rel}: {e['player']}: invalid bbr_id")
            except (KeyError, TypeError, ValueError):
                errors.append(f"{rel}: entries need player, bbr_id, from and until")
        roster = json.loads(register.read_text(encoding="utf-8"))
        as_of = roster["as_of"]
        open_keys = {e.get("bbr_id") or alias(e.get("player", "")) for e in data["entries"]
                     if isinstance(e.get("from"), str) and e["from"] <= as_of and (e.get("until") is None or as_of < e["until"])}
        open_names = {alias(e.get("player", "")) for e in data["entries"]
                      if isinstance(e.get("from"), str) and e["from"] <= as_of and (e.get("until") is None or as_of < e["until"])}
        for p in roster["players"]:
            if any(word in p.get("status", "") for word in NOT_HELD):
                continue
            if p.get("bbr_id") not in open_keys and alias(p["name"]) not in open_names:
                errors.append(f"{rel}: {p['name']} is on the register on {as_of} but not held then")
    return errors


def primary_position(label):
    """Basketball-Reference positions such as 'SG-SF' use their first listed position."""
    position = label.split("-")[0]
    return position if position in POSITIONS else "SF"


def _span(p):
    lo, hi = p.get("span", [0.0, 1.0])
    return max(1e-9, hi - lo)


def _present(p, fraction):
    lo, hi = p.get("window", [0.0, 1.0])
    return p["games"] >= 1 and p["minutes"] > 0 and (lo <= fraction < hi or (fraction >= 1.0 and hi >= 1.0))


def _availability(p, season_games):
    return min(1.0, p["games"] / (season_games * _span(p)))


def _share(p, season_games):
    """Expected minutes per club game while he is with the club."""
    return p["minutes"] / p["games"] * _availability(p, season_games)


def real_rotation(club_name, club, season_games, rating_index=None, *, fraction, exclude=(), arrivals=(), pace=1.0):
    """TeamInput for a real club on the date at `fraction` of the season, rotation order first.

    `club` is the roster file entry; `season_games` the club's regular-season games.
    `exclude`: bbr_ids or names not with this club in the simulation (rule 2).
    `arrivals`: roster entries (same shape) for players who joined in the simulation, such as a
    player simulated Miami trades to this club.
    """
    exclude = set(exclude)
    gone = lambda p: p["bbr_id"] in exclude or alias(p["player_id"]) in exclude
    present = [p for p in club["players"] if _present(p, fraction)]
    staying = [p for p in present if not gone(p) and "returned" not in p]
    incoming = [p for p in present if not gone(p) and "returned" in p] + [
        a for a in arrivals if a["games"] >= 1 and a["minutes"] > 0 and not gone(a)]
    # Rule 3: departing minutes go to the incoming players up to their own previous share and the
    # rest raises the staying rotation; a shortfall comes out of it, both in proportion to real minutes.
    # A returned player Miami holds never played for this club in the real season, so he frees nothing.
    freed = sum(_share(p, season_games) for p in present if gone(p) and "returned" not in p)
    wanted = sum(_share(p, season_games) for p in incoming)
    stay_share = sum(_share(p, season_games) for p in staying)
    factor = max(0.25, 1 + (freed - wanted) / stay_share) if stay_share else 1.0
    players = []
    for p, scale in [(p, factor) for p in staying] + [(p, 1.0) for p in incoming]:
        per_game = min(MAX_MINUTES_PER_GAME, p["minutes"] / p["games"] * scale)
        if per_game <= 0:
            continue
        availability = _availability(p, season_games)
        profile = rating_index.engine_profile(p["player_id"], p["bbr_id"]) if rating_index else {}
        players.append((per_game, availability, PlayerInput(p["player_id"], primary_position(p["position"]),
                                                            round(per_game, 2), {}, profile,
                                                            round(availability, 4))))
    # Rotation order: who plays the most when he plays.
    players.sort(key=lambda item: (-item[0], -item[1], item[2].player_id))
    return TeamInput(club_name, tuple(p for _, _, p in players), pace)
