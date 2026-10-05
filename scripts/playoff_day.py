#!/usr/bin/env python3
"""Build one day's 2004 playoff games, or bring the bracket up to date after they are played (runtime/playoffs.py).

    python scripts/playoff_day.py --build DATE     write the day's requests (Miami's with its game note), frozen
    python scripts/playoff_day.py --refresh        apply closed results, open the next rounds, rewrite the page

Miami's games are built one at a time, so an injury reaches the next game. Nothing here plays a game: the requests
are played by the engine (`python scripts/play_games.py DATE`) like any other.
"""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime import playoffs                                            # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--build", metavar="DATE")
    group.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    if playoffs.read(ROOT) is None:
        print("the playoffs are not seeded (python scripts/seed_playoffs.py --write)")
        return 1
    if args.build:
        built = playoffs.build_games(args.build, ROOT)
        for path in built:
            print(f"built {path.relative_to(ROOT)}")
        print(f"{len(built)} playoff game(s) built for {args.build}")
        return 0
    record = playoffs.refresh(ROOT)
    open_ = [f"{s['id']} " + "-".join(str(s['wins'][c]) for c in s["clubs"]) for s in record["series"] if not s["winner"]]
    print("open series: " + (", ".join(open_) or "none"))
    if record.get("champion"):
        print(f"champion: {record['champion']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
