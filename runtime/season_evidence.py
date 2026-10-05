"""The prior season's player statistics a season's front offices may read, from one place.

Before the career began the evidence is the library's real season totals (`nba_<prev>_player_stats.json`). Once the
career has played a season, its closed simulated results are the evidence for the next one, never the real season
(the world drifted from history). The totals keep the library's record shape, so every model reads both alike:
{bbr_id: {"bbr_id", "player_name", "team_codes", "totals": {...}}}.

The simulated totals are written once when a season closes (`Stats_and_Awards/League/<season>/season_totals.json`)
and recomputed from closed results when that file is absent.
"""
from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAYER = Path("career/Dwyane_Wade")
KEYS = {"games": None, "games_started": None, "minutes": "minutes", "points": "pts", "field_goals_made": "fgm",
        "field_goals_attempted": "fga", "three_point_field_goals_made": "tpm", "three_point_field_goals_attempted": "tpa",
        "free_throws_made": "ftm", "free_throws_attempted": "fta", "offensive_rebounds": "orb", "defensive_rebounds": "drb",
        "assists": "ast", "steals": "stl", "blocks": "blk", "turnovers": "tov", "personal_fouls": "pf"}


def totals_path(season):
    return PLAYER / "Stats_and_Awards/League" / season / "season_totals.json"


def simulated(season, root=ROOT):
    """True once the career has closed this season (its season close is recorded)."""
    return (Path(root) / PLAYER / season / "season_close.json").is_file()


def compute_totals(season, root=ROOT):
    """{bbr_id: record} over the season's closed regular-season results."""
    from .seasons import dates
    from .season_awards import identities
    from .write_back import closed_results
    root = Path(root)
    end = dates(season, root)["regular_season_end"]
    ids = identities(root, season)
    sums = defaultdict(lambda: defaultdict(float))
    clubs = defaultdict(list)
    for row in closed_results(root, season, end):
        r = row["result"]
        for side in ("home", "away"):
            for p in r["player_stats"][side]:
                if not p.get("minutes", 0) > 0:
                    continue
                bbr = ids.get(p["player_id"], (None, None, None))[1] or ("dwyane_wade" if p["player_id"] == "Dwyane Wade" else None)
                if not bbr:
                    continue
                t = sums[bbr]
                t["games"] += 1
                t["games_started"] += bool(p.get("started"))
                for key, src in KEYS.items():
                    if src:
                        t[key] += p.get(src) or 0
                if not clubs[bbr] or clubs[bbr][-1] != r[side]:
                    clubs[bbr].append(r[side])
                t["_name"] = p["player_id"]
    out = {}
    for bbr, t in sums.items():
        name = t.pop("_name")
        out[bbr] = {"bbr_id": bbr, "player_name": name, "team_codes": clubs[bbr],
                    "totals": {k: (int(v) if k != "minutes" else round(v, 1)) for k, v in t.items()}}
    return out


def write_totals(season, root=ROOT):
    path = Path(root) / totals_path(season)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"schema_version": 1, "season": season, "kind": "simulated_season_totals",
            "rule": __doc__.split("\n\n", 1)[0], "records": sorted(compute_totals(season, root).values(), key=lambda r: r["bbr_id"])}
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def season_records(season, root=ROOT):
    """{bbr_id: record} for a played season: the closed simulated totals, or the library's real ones."""
    root = Path(root)
    if simulated(season, root):
        path = root / totals_path(season)
        if path.is_file():
            return {r["bbr_id"]: r for r in json.loads(path.read_text(encoding="utf-8"))["records"]}
        return compute_totals(season, root)
    from .seasons import library, next_season, tag
    path = root / library(next_season(season)) / f"nba_{tag(season)}_player_stats.json"
    if not path.is_file():
        from .seasons import ROOT as REPO
        path = REPO / library(next_season(season)) / f"nba_{tag(season)}_player_stats.json"
    return {r["bbr_id"]: r for r in json.loads(path.read_text(encoding="utf-8"))["records"]}


def prior_records(season, root=ROOT):
    """The evidence a season's front offices read: the season before it."""
    from .seasons import previous_season
    return season_records(previous_season(season), root)


def market_season(on):
    """The season a front-office date prices for: from June 1 the coming season (the draft and free agency serve it),
    else the season in progress."""
    from .seasons import label
    y, m = int(on[:4]), int(on[5:7])
    return label(y if m >= 6 else y - 1)
