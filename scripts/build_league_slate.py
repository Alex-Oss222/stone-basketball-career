#!/usr/bin/env python3
"""The league slate: a request for every non-Miami regular-season game, on its date (roadmap item 11).

  python scripts/build_league_slate.py --write 2003-10-31       write every game due by October 31
  python scripts/build_league_slate.py --check 2003-10-31       report what is due and unwritten; write nothing
  python scripts/build_league_slate.py --write 2004-04-14 --validate-all

Requests go under `career/Dwyane_Wade/Stats_and_Awards/League/2003-04/Games/<game_id>.request.json`
(both clubs `"rotation": "real"`, game_type regular, venue home) with a README; Railway plays them and
`scripts/collect_results.py` writes `<game_id>.result.json` beside each. Every written request is
checked structurally (fields, clubs against the roster file, agreement with the schedule); the
engine's full `load_request` runs on a deterministic sample (the first, the last and every 25th), since
it costs about 0.2 s a request and the whole 1,189-game slate would take minutes. `--validate-all`
runs it on every request written. A request is never written before its date or rewritten.
"""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from runtime import season_games  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", metavar="DATE", help="write every league game due on or before DATE")
    group.add_argument("--check", metavar="DATE", help="verify without writing")
    parser.add_argument("--validate-all", action="store_true", help="run the engine's load_request on every request, not a sample")
    args = parser.parse_args()
    every = 1 if args.validate_all else season_games.SLATE_SAMPLE_EVERY
    names = season_games.club_name_errors(ROOT)
    if names:
        print("\n".join(f"- {n}" for n in names))
        return 1
    if args.check:
        problems = season_games.slate_check(args.check, ROOT, every=every)
        for p in problems:
            print(f"- {p}")
        print(f"league slate complete through {args.check}" if not problems else f"{len(problems)} problem(s)")
        return 1 if problems else 0
    written, _ = season_games.build_slate(args.write, ROOT, write=True, every=every)
    for path in written:
        print(path.relative_to(ROOT))
    sample = len(season_games.slate_sample(written, every)) if written else 0
    print(f"{len(written)} request(s) written; {sample} checked with load_request, all checked structurally")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
