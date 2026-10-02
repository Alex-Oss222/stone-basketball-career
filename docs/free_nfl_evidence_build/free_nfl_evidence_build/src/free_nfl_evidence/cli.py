from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .build import build_evidence
from .guards import assert_allowed_seasons, slice_as_of
from .sources import fetch_public_data, source_specs


def parse_seasons(value: str) -> tuple[int, ...]:
    value = value.strip()
    if ":" in value:
        a, b = value.split(":", 1)
        return assert_allowed_seasons(range(int(a), int(b) + 1))
    return assert_allowed_seasons(int(x.strip()) for x in value.split(",") if x.strip())


def cmd_urls(args: argparse.Namespace) -> None:
    seasons = parse_seasons(args.seasons)
    for spec in source_specs(seasons):
        print(f"{spec.dataset}\t{spec.season or 'global'}\t{spec.candidates[0]}")


def cmd_fetch(args: argparse.Namespace) -> None:
    seasons = parse_seasons(args.seasons)
    manifest = fetch_public_data(Path(args.workspace), seasons, overwrite=args.overwrite)
    print(json.dumps({"downloaded_or_present": len(manifest), "workspace": str(Path(args.workspace).resolve())}, indent=2))


def cmd_build(args: argparse.Namespace) -> None:
    seasons = parse_seasons(args.seasons)
    paths = build_evidence(Path(args.workspace), seasons)
    print(json.dumps(paths, indent=2))


def cmd_as_of(args: argparse.Namespace) -> None:
    src = Path(args.input)
    dst = Path(args.output)
    df = pd.read_csv(src, low_memory=False)
    gated = slice_as_of(df, int(args.season))
    dst.parent.mkdir(parents=True, exist_ok=True)
    gated.to_csv(dst, index=False)
    print(f"wrote {len(gated)} rows to {dst}")


def main() -> None:
    p = argparse.ArgumentParser(description="Build isolated 2010-2014 real public NFL evidence without touching simulation data.")
    sub = p.add_subparsers(dest="command", required=True)

    urls = sub.add_parser("urls", help="Print public source URLs without downloading anything")
    urls.add_argument("--seasons", default="2010:2014")
    urls.set_defaults(func=cmd_urls)

    fetch = sub.add_parser("fetch", help="Download public source files into an isolated workspace")
    fetch.add_argument("--workspace", required=True)
    fetch.add_argument("--seasons", default="2010:2014")
    fetch.add_argument("--overwrite", action="store_true")
    fetch.set_defaults(func=cmd_fetch)

    build = sub.add_parser("build", help="Create derived evidence CSVs from downloaded raw files")
    build.add_argument("--workspace", required=True)
    build.add_argument("--seasons", default="2010:2014")
    build.set_defaults(func=cmd_build)

    asof = sub.add_parser("as-of", help="Apply the no-hindsight season gate to a derived CSV")
    asof.add_argument("--input", required=True)
    asof.add_argument("--output", required=True)
    asof.add_argument("--season", required=True, type=int)
    asof.set_defaults(func=cmd_as_of)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
