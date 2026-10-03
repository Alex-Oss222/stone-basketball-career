"""Frozen June 26, 2003 checkpoint for tests.

The live career clock moves on with every run of the free-agency driver, so tests that exercise
checkpoint rules (June 30 package, draft-day finance projection, market opening, standing on the
draft date) pin a repository copy back to the checkpoint. `tests/fixtures/checkpoint_2003-06-26/`
holds the team-control, finance and phase files exactly as they stood on that date; `pin()` lays
them over a copy of the repository and removes every record the clock produced after it.
"""
from pathlib import Path
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT = "2003-06-26"
FIXTURE = ROOT / "tests/fixtures/checkpoint_2003-06-26"
SEASON = "career/Dwyane_Wade/2003-04"
AFTER_CHECKPOINT = (                       # records the clock writes after June 26; absent at the checkpoint
    f"{SEASON}/01_Free_Agency/June_30",
    f"{SEASON}/01_Free_Agency/Negotiations",
    f"{SEASON}/01_Free_Agency/Plans",
    f"{SEASON}/Wade_Consultations",
    f"{SEASON}/00_Team/Transactions",
    f"{SEASON}/04_Training_Camp/camp_roster.json",
    "career/Dwyane_Wade/standing.json",
)


def pin(root):
    """Return `root` with its career records restored to the June 26 checkpoint."""
    root = Path(root)
    for path in sorted(p for p in FIXTURE.rglob("*") if p.is_file()):
        target = root / path.relative_to(FIXTURE)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(path, target)
    for rel in AFTER_CHECKPOINT:
        target = root / rel
        if target.is_dir():
            shutil.rmtree(target)
        elif target.is_file():
            target.unlink()
    state_path = root / SEASON / "current_state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["current_date"] == CHECKPOINT, state["current_date"]
    return root


def read(rel):
    """Read one checkpoint fixture file (JSON by extension, else text)."""
    path = FIXTURE / rel
    text = path.read_text(encoding="utf-8")
    return json.loads(text) if path.suffix == ".json" else text
