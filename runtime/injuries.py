"""Fatigue and injuries (engine problem E7, roadmap item 12).

The 28 real clubs miss games at their real season rates through availability
(`runtime/rotations.py`). The simulated club (Miami) gets its injuries from the
engine: after each of its games, every player who played may be hurt, with a
risk that rises with minutes, age and the second night of a back-to-back
(`runtime/kernel.py`). The draw uses the game's journaled entropy, so it can
never be chosen or re-rolled, and is reported in the result's `injuries`.

An injury keeps a player out of his club's next `games_out` games. Miami's game
builder leaves him out of those requests (`injured_out`), and the write-back
records the injury in the game note (roadmap items 10 and 13). Real injury
histories are never used (AGENTS.md); Wade's are engine draws like everyone's.

Every club's rest comes from the schedule: days off since its previous regular-
season game, 0 for the second night of a back-to-back, at most 3.
"""
from datetime import date
import json
from pathlib import Path

from .player_stats import alias
from .rosters import SIMULATED_CLUB

ROOT = Path(__file__).resolve().parents[1]
MAX_REST = 3
# The user's premise (December 31, 2004 on the career clock): every injured player is healed and the engine draws no
# injuries or one-game absences for Miami from INJURY_PAUSE[0] until the injury pipeline is finished and switched back on
# (INJURY_PAUSE[1], None = still paused). Games before the pause keep their recorded inputs and results; nothing is
# re-rolled. A player on the injured list still serves the list's minimum games (a league rule, not an injury).
INJURY_PAUSE = ("2005-01-01", None)


def paused(game_date):
    """Whether the injury model is switched off for a game on `game_date`."""
    start, end = INJURY_PAUSE
    return bool(game_date) and start <= game_date and (end is None or game_date < end)


def rest_days(season, team, game_date, root=ROOT):
    from .schedule import schedule_path
    path = schedule_path(season, root)
    if not path.exists():
        return 2
    day = date.fromisoformat(game_date)
    before = [date.fromisoformat(g["date"]) for g in json.loads(path.read_text(encoding="utf-8"))["games"]
              if team in (g["home"], g["away"]) and g["date"] < game_date]
    from . import playoffs
    before += [date.fromisoformat(d) for d in playoffs.club_dates(playoffs.read(root, season), team) if d < game_date]
    return MAX_REST if not before else max(0, min(MAX_REST, (day - max(before)).days - 1))


def age_on(birth_date, game_date):
    b, d = date.fromisoformat(birth_date), date.fromisoformat(game_date)
    return d.year - b.year - ((d.month, d.day) < (b.month, b.day))


def simulated_ages(season, game_date, root=ROOT):
    """Name key -> age on the game date for the simulated club's register.

    A birth date recorded later (`date_of_birth_from`) is used only for games from that date, so a
    played game's inputs never change when the register gains an identity fact."""
    path = Path(root) / f"career/Dwyane_Wade/{season}/00_Team/Team/Roster/roster.json"
    if not path.exists():
        return {}
    return {alias(p["name"]): age_on(p["date_of_birth"], game_date)
            for p in json.loads(path.read_text(encoding="utf-8"))["players"]
            if p.get("date_of_birth") and p.get("date_of_birth_from", game_date) <= game_date}


def injured_out(results, team=SIMULATED_CLUB, start=None):
    """Player -> games still to miss after the last of `results` (the club's closed results, in order).

    `start`: games still to miss when the first of `results` begins (an injury carried in from the
    previous season, `carried_in`)."""
    out = dict(start or {})
    for result in results:
        side = "home" if result["home"] == team else "away" if result["away"] == team else None
        if side is None:
            continue
        out = {pid: n - 1 for pid, n in out.items() if n - 1 > 0}
        for injury in result.get("injuries", []):
            if injury["side"] == side:
                out[injury["player_id"]] = max(out.get(injury["player_id"], 0), injury["games_out"])
    return out


DAYS_PER_GAME = 170 / 82        # a regular season's days per game: an injury's games become days of recovery


def previous_season(season):
    start = int(season[:4]) - 1
    return f"{start}-{str(start + 1)[-2:]}"


def carried_in(season, root=ROOT, team=SIMULATED_CLUB):
    """Games a player still misses at the start of `season` from an injury drawn in the previous one.

    The games left after the club's last game (regular season, Play-In or playoffs) become days at the
    regular season's pace; the offseason's days until the club's first game of the new season count as
    recovery (judgement). An injury that heals in the summer carries nothing."""
    from .season_games import miami_game_dates, miami_results
    before = previous_season(season)
    results = miami_results(root, before) if (Path(root) / f"career/Dwyane_Wade/{before}").is_dir() else []
    if not results:
        return {}
    left = injured_out(results, team)
    dates = miami_game_dates(root, season)
    if not left or not dates:
        return {}
    gap = (date.fromisoformat(dates[0]) - date.fromisoformat(results[-1]["game_date"])).days
    out = {}
    for pid, games in left.items():
        days = games * DAYS_PER_GAME - gap
        if days > 0:
            out[pid] = max(1, round(days / DAYS_PER_GAME))
    return out


LONG_INJURY_GAMES = 8           # an injury this long brings a ramp-up and a re-injury window on return
RETURN_WINDOW = 10              # games back that carry the higher risk (kernel REINJURY_GAMES)
RETURN_MINUTES = (0.7, 0.8, 0.9)   # the staff's minutes restriction for the first three games back (judgement)


def returning_from(results, team=SIMULATED_CLUB, start=None):
    """Player -> which game back the next one is (1 = first game back) after an injury of
    LONG_INJURY_GAMES or more, within RETURN_WINDOW games; from the club's closed results in order."""
    out, long_, back = dict(start or {}), {pid: True for pid in (start or {})}, {}
    for result in results:
        side = "home" if result["home"] == team else "away" if result["away"] == team else None
        if side is None:
            continue
        missed = {pid for pid, n in out.items() if n > 0}
        for pid in back:
            if pid not in missed:
                back[pid] += 1
        out = {pid: n - 1 for pid, n in out.items() if n - 1 > 0}
        for pid in missed:
            if pid not in out and long_.get(pid):
                back[pid] = 0
        for injury in result.get("injuries", []):
            if injury["side"] == side:
                pid = injury["player_id"]
                out[pid] = max(out.get(pid, 0), injury["games_out"])
                long_[pid] = out[pid] >= LONG_INJURY_GAMES
                back.pop(pid, None)
    return {pid: n + 1 for pid, n in back.items() if n < RETURN_WINDOW and pid not in out}

