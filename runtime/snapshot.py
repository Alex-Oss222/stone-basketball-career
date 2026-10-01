"""Locate the live career state and compute the snapshot digest the engine binds to."""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def current_state_path(root=ROOT):
    career = Path(root) / "career"
    players = [p for p in career.iterdir() if p.is_dir()]
    if len(players) != 1:
        raise ValueError("career must contain exactly one player directory")
    seasons = [p for p in players[0].iterdir() if p.is_dir()]
    if len(seasons) != 1:
        raise ValueError("player directory must contain exactly one active season directory")
    path = seasons[0] / "current_state.json"
    if not path.is_file():
        raise ValueError(f"missing {path.relative_to(root)}")
    return path


def current_snapshot(root=ROOT):
    return hashlib.sha256(current_state_path(root).read_bytes()).hexdigest()
