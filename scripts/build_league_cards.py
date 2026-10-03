#!/usr/bin/env python3
"""Build one dated league player card (Markdown and interactive HTML) per registry player.

`--write` regenerates every card from the dated records; `--check` verifies the cards on disk
match a fresh build without writing. The builder reads closed results only through the
repository's records; it never runs the engine, advances the clock or imports real results.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.league_cards import CARDS_DIR, check_cards, write_cards


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true", help="regenerate every league card")
    group.add_argument("--check", action="store_true", help="verify the cards on disk without writing")
    args = parser.parse_args(argv)
    if args.check:
        stale = check_cards(ROOT)
        if stale:
            print(f"{len(stale)} league card file(s) differ from a fresh build, for example {stale[0].relative_to(ROOT)}; run --write.")
            return 1
        print("League cards match the dated records.")
        return 0
    outputs = write_cards(ROOT)
    cards = sum(1 for path in outputs if path.suffix == ".md" and path.name != "README.md")
    print(f"Wrote {cards} league player cards under {CARDS_DIR} ({len(outputs)} files). No results, roster decisions or awards changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
