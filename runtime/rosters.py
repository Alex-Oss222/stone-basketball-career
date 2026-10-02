"""Real club rosters for the world model (option D): every non-Miami club, season by season."""
import json
from pathlib import Path

from .trajectories import PROTAGONIST_IDS

ROOT = Path(__file__).resolve().parents[1]
SIMULATED_CLUB = "Miami Heat"


def roster_errors(root=ROOT):
    errors = []
    for path in sorted((Path(root) / "library").glob("*/league/nba_*_team_rosters.json")):
        rel = path.relative_to(root)
        data = json.loads(path.read_text(encoding="utf-8"))
        schedule_path = path.with_name(path.name.replace("team_rosters", "schedule"))
        if SIMULATED_CLUB in data["clubs"]:
            errors.append(f"{rel}: Miami is simulated and must not have a real roster")
        if any(p["bbr_id"] in PROTAGONIST_IDS for c in data["clubs"].values() for p in c["players"]):
            errors.append(f"{rel}: contains the historical protagonist")
        if schedule_path.exists():
            schedule = json.loads(schedule_path.read_text(encoding="utf-8"))
            names = {t for g in schedule["games"] for t in (g["home"], g["away"])} - {SIMULATED_CLUB}
            if set(data["clubs"]) != names:
                errors.append(f"{rel}: clubs do not match the season schedule")
    return errors
