"""Who can play in a season: retirements and unavailable seasons from real careers (the user's request, October 2026:
no retired player comes back, and a player who retired in history retires in the simulation).

Career continuity (AGENTS.md) keeps every real player on his real career path. `library/careers/nba_player_careers.json`
lists each real player's NBA seasons from 2003-04 (seasons with minutes). For a season S:
- retired: his real seasons stop before S (and not at the file's last season, where the data simply ends). He never
  signs again and, if a club holds him when S opens, he retires that day;
- unavailable: no real NBA season S but later ones (injured all year, abroad): no club signs him during S;
- available: a real NBA season S, or S after the file's last season while his career ran to that last season.
A player absent from the file never played an NBA minute from 2003-04 on: no club signs him from the free-agent pool.
Alternate-history players (trajectories.ALTERNATE_FROM) follow their own model, not this file, from their first season.
The rule reads world data only, the same evidence the engine's ability model already uses; it decides availability,
never a result.
"""
import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAREERS = Path("library/careers/nba_player_careers.json")


@lru_cache(maxsize=4)
def _careers(root):
    path = Path(root) / CAREERS
    data = json.loads(path.read_text(encoding="utf-8"))["players"] if path.is_file() else {}
    seasons = {b: sorted(s for s, row in p.get("seasons", {}).items() if (row.get("minutes") or 0) > 0) for b, p in data.items()}
    last = max((s[-1] for s in seasons.values() if s), default=None)
    return seasons, last


def status(bbr_id, season, root=ROOT):
    """'available', 'unavailable' (sits this season out), 'retired' or 'unknown' (never an NBA minute from 2003-04)."""
    from .trajectories import alternate
    if alternate(bbr_id, season):
        return "available"
    seasons, last = _careers(str(Path(root).resolve()))
    real = seasons.get(bbr_id)
    if not real:
        return "unknown"
    if season in real or (last and season > last and real[-1] == last):
        return "available"
    if real[-1] < season:
        return "retired"
    return "unavailable"


def signable(bbr_id, season, root=ROOT):
    """A free agent a club may sign during the season."""
    return status(bbr_id, season, root) == "available"
