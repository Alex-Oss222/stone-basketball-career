#!/usr/bin/env python3
"""Build a season's player-rating baseline and complete its league environment (roadmap 18).

    python scripts/build_season_baseline.py --season 2004-05 --write

From the completed previous season's real totals (`player_stats.SEASON_SOURCES`): the veteran ratings file and,
in the league-environment file, the rating model label, the rate baselines, and the team/player turnover split
(published team turnovers minus summed player turnovers over the season's club games). No game is created or run.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from runtime.era import environment_path                                 # noqa: E402
from runtime.player_stats import SEASON_SOURCES, build_ratings, read_json, sha256   # noqa: E402
CLUBS = {"2003-04": 29}


def outputs(season, root=ROOT):
    src = SEASON_SOURCES[season]
    data = read_json(root / src["stats"])
    ratings = build_ratings(data, sha256(root / src["stats"]), season)
    env_path = environment_path(season, root)
    env = read_json(env_path)
    games = CLUBS[src["baseline"]] * 82
    player_tov = ratings["source_totals"]["turnovers"] / games
    residual = env["averages"]["tov"] - player_tov
    if not 0 <= residual < 1.5:
        raise ValueError(f"team/player turnover gap {residual:.2f} needs review")
    env.update(team_turnovers_per_game=residual, player_turnovers_per_game=player_tov,
               team_turnover_note="Inferred residual: published team TOV minus summed individual TOV / (clubs x 82).",
               player_rating_model=src["model"], player_rate_baselines=ratings["rate_baselines"])
    env.pop("omitted_keys", None)
    return {root / src["ratings"]: ratings, env_path: env}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--season", required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    for path, data in outputs(args.season).items():
        text = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        stale = not path.exists() or path.read_text(encoding="utf-8") != text
        print(f"{path.relative_to(ROOT)}: {'stale' if stale else 'current'}")
        if args.write and stale:
            path.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
