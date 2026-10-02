#!/usr/bin/env python3
"""Build static, accessible red-and-black headers for milestone templates."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.stat_layout import RED, rect, svg_start, svg_text

HEADERS = {
    "contract": ("CONTRACT", "Your next agreement", "Salary · protection · options · your response"),
    "market": ("FREE AGENCY", "Your market", "Priorities · written offers · club conversations"),
    "training": ("DEVELOPMENT", "Your offseason work", "Choose a focus · agree the work · review the evidence"),
    "trade": ("TRADE UPDATE", "Your situation has changed", "Verified status · player rights · reporting and role"),
    "exit": ("SEASON REVIEW", "What you take into summer", "Closed results · staff feedback · your priorities"),
    "camp": ("TRAINING CAMP", "Your role and next opportunity", "Communicated assignment · evidence · player response"),
}


def header(label, title, subtitle):
    parts = svg_start(title, 148, subtitle)
    parts += [rect(20, 20, 322, 108, RED),
              svg_text(42, 54, "PLAYER MILESTONE", 14, "#f4ccd3", 700),
              svg_text(42, 99, label, 28, weight=700),
              svg_text(372, 69, title, 31, weight=700),
              svg_text(372, 108, subtitle, 21, "#c5c7cb")]
    return "\n".join([*parts, "</svg>"]) + "\n"


def main():
    folder = ROOT / "docs/templates/player_milestones/assets"
    folder.mkdir(parents=True, exist_ok=True)
    for name, fields in HEADERS.items():
        (folder / f"{name}.svg").write_text(header(*fields), encoding="utf-8")
    print(f"Built {len(HEADERS)} milestone headers; no career state changed.")


if __name__ == "__main__":
    main()
