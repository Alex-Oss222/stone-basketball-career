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


def rest_days(season, team, game_date, root=ROOT):
    from .schedule import schedule_path
    path = schedule_path(season, root)
    if not path.exists():
        return 2
    day = date.fromisoformat(game_date)
    before = [date.fromisoformat(g["date"]) for g in json.loads(path.read_text(encoding="utf-8"))["games"]
              if team in (g["home"], g["away"]) and g["date"] < game_date]
    return MAX_REST if not before else max(0, min(MAX_REST, (day - max(before)).days - 1))


def age_on(birth_date, game_date):
    b, d = date.fromisoformat(birth_date), date.fromisoformat(game_date)
    return d.year - b.year - ((d.month, d.day) < (b.month, b.day))


def simulated_ages(season, game_date, root=ROOT):
    """Name key -> age on the game date for the simulated club's register."""
    path = Path(root) / f"career/Dwyane_Wade/{season}/00_Team/Team/Roster/roster.json"
    if not path.exists():
        return {}
    return {alias(p["name"]): age_on(p["date_of_birth"], game_date)
            for p in json.loads(path.read_text(encoding="utf-8"))["players"] if p.get("date_of_birth")}


def injured_out(results, team=SIMULATED_CLUB):
    """Player -> games still to miss after the last of `results` (the club's closed results, in order)."""
    out = {}
    for result in results:
        side = "home" if result["home"] == team else "away" if result["away"] == team else None
        if side is None:
            continue
        out = {pid: n - 1 for pid, n in out.items() if n - 1 > 0}
        for injury in result.get("injuries", []):
            if injury["side"] == side:
                out[injury["player_id"]] = max(out.get(injury["player_id"], 0), injury["games_out"])
    return out
