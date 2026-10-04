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
    f"{SEASON}/00_Team/Finances/minimum_salary_corrections.json",
    f"{SEASON}/04_Training_Camp/camp_roster.json",
    f"{SEASON}/04_Training_Camp/Decisions",
    f"{SEASON}/00_Team/Team/Depth_Chart/rotation.json",
    f"{SEASON}/00_Team/Team/Depth_Chart/Reviews",
    f"{SEASON}/00_Team/Team/defensive_grades.json",
    f"{SEASON}/01_Free_Agency/Wade_Rookie_Contract/negotiation_log.json",
    "career/Dwyane_Wade/standing.json",
    "career/Dwyane_Wade/Contracts/contract_records.json",
    "career/Dwyane_Wade/Stats_and_Awards/League/2003-04/Games",
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
    for pattern in ("05_Preseason/Game_*", "06_Regular_Season/**/Game_*"):   # game notes and requests come after camp
        for path in (root / SEASON).glob(pattern):
            if path.is_file():
                path.unlink()
    # Reset the initial game-log scaffolds too: deleting a result must not leave
    # its event ID in a copied phase/week note, where idempotent write-back would
    # mistake a newly simulated fixture game for the live career's earlier game.
    preseason = root / SEASON / "05_Preseason/note.md"
    if preseason.exists():
        preseason.write_text("---\ntype: phase\nstatus: not_started\n---\n\n# Preseason\n\n"
                             "## Player decisions\n\n## Events\n\n## Consequences\n", encoding="utf-8")
    day_ranges = {1: "1-7", 2: "8-14", 3: "15-21", 4: "22-end"}
    for note in (root / SEASON / "06_Regular_Season").glob("*/Week_*/note.md"):
        month = note.parent.parent.name.split("_", 1)[1]
        week = int(note.parent.name.split("_", 1)[1])
        note.write_text(f"---\ntype: regular_season_week\nstatus: not_started\nmonth: {month}\n"
                        f"week: {week}\ndays: {day_ranges[week]}\n---\n\n# {month} Week {week}\n\n"
                        "## Schedule\n\n## Player decisions\n\n## Games and events\n\n## Consequences\n",
                        encoding="utf-8")
    register = json.loads((root / SEASON / "00_Team/Team/Roster/roster.json").read_text(encoding="utf-8"))
    ids = {p["id"] for p in register["players"]}
    for card in (root / SEASON / "00_Team/Team/Player_Cards").glob("*.md"):
        if card.name not in ("README.md", "TEMPLATE.md") and card.stem not in ids:
            card.unlink()                        # personnel cards of players who joined after the checkpoint
        elif card.name not in ("README.md", "TEMPLATE.md"):
            # A checkpoint player's card keeps no row sourced from a game the fixture removed (an injury, say).
            text = card.read_text(encoding="utf-8")
            kept = [line for line in text.splitlines(keepends=True)
                    if "06_Regular_Season/" not in line and "05_Preseason/Game_" not in line]
            if len(kept) != len(text.splitlines(keepends=True)):
                card.write_text("".join(kept), encoding="utf-8")
    # Dated registry additions (first 2003-04 appearances) come after the checkpoint.
    reg_path = root / "career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json"
    if reg_path.is_file():
        reg = json.loads(reg_path.read_text(encoding="utf-8"))
        kept = [p for p in reg["players"] if p.get("cohort") != "2003_04_appearance"]
        if len(kept) != len(reg["players"]):
            reg["players"], reg["player_count"] = kept, len(kept)
            reg.get("coverage", {}).get("source_counts", {}).pop("2003_04_appearance", None)
            reg_path.write_text(json.dumps(reg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    state_path = root / SEASON / "current_state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["current_date"] == CHECKPOINT, state["current_date"]
    if (root / "library").is_dir():
        from runtime.write_back import write_statistics_pages
        write_statistics_pages(root)             # Miami's not-started pages list the checkpoint register
    return root


def read(rel):
    """Read one checkpoint fixture file (JSON by extension, else text)."""
    path = FIXTURE / rel
    text = path.read_text(encoding="utf-8")
    return json.loads(text) if path.suffix == ".json" else text
