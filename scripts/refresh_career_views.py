"""Refresh detailed player-facing pages after a committed career operation.

Rendering reads canonical evidence only. It never plays a game, advances the
clock, accepts a contract, or turns a fetched result into a closed game note.
"""
from __future__ import annotations

from pathlib import Path

from runtime.league_cards import CARDS_DIR, COLORS_FILE, build_cards
from runtime.player_reports import build_reports


def refresh_career_views(root: Path) -> list[Path]:
    """Build the complete set before writing, then replace only changed pages.

    Called at the successful CLI boundary, after the event driver has committed
    its records. A stopped decision is a successful boundary too: the player
    should immediately see the question on which the career is waiting.
    """
    root = Path(root)
    outputs = {}
    for player in sorted((root / "career").iterdir()):
        if player.is_dir() and (player / "professional_identity.json").is_file():
            outputs.update(build_reports(root, player))
    if (root / CARDS_DIR).is_dir() and (root / COLORS_FILE).is_file():      # a partial test copy has no card sources
        outputs.update(build_cards(root))   # league cards follow dated clubs and contracts, so every boundary rebuilds them
        from runtime.write_back import statistics_pages
        outputs.update(statistics_pages(root))   # not-started Miami pages follow the register; played periods their results
        from runtime.roster_moves import depth_views
        outputs.update(depth_views(root))        # the readable depth chart follows the staff's chart in force
    changed = []
    for page, text in outputs.items():
        if not page.is_file() or page.read_text(encoding="utf-8") != text:
            page.parent.mkdir(parents=True, exist_ok=True)
            page.write_text(text, encoding="utf-8")
            changed.append(page)
    return changed
