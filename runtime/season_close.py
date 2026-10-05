"""Close a season the night its Finals end (roadmap 18): the season-close record, Wade's incentive evaluation and the
`season_close` standing snapshot.

The close date is the clinching date of the Finals in the bracket record (`runtime/playoffs.py`), the league's last
game; Miami's own season may have ended earlier. Nothing is closed before every regular-season and playoff game
scheduled on or before that date is closed. The record `career/Dwyane_Wade/<season>/season_close.json` holds:
- the close date, the competitions closed (regular and playoff), Miami's scheduled regular-season games;
- Wade's closed regular-season and playoff lines (career_stats) and his earned honors for the season;
- the evaluation of each incentive clause in his signed contract for the season (`runtime/incentives.py`), so the
  cap accounting and the contract pages read one dated record. Nothing is paid or re-signed here.
Then `standing.record(..., trigger="season_close")` dates the standing that the closed season and its honors give.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEASON = "2003-04"
PLAYER = Path("career/Dwyane_Wade")


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def path(season=SEASON, root=ROOT):
    return Path(root) / PLAYER / season / "season_close.json"


def close_date(root=ROOT):
    """The Finals' clinching date, or None while the Finals are undecided."""
    from .playoffs import read
    record = read(root) or {}
    finals = next((s for s in record.get("series", []) if s["round"] == "finals"), None)
    return finals.get("clinched_on") if finals and finals.get("winner") else None


def wade_contract(root=ROOT):
    records = _read(Path(root) / PLAYER / "Contracts/contract_records.json")["records"]
    signed = [r for r in records if r.get("contract", {}).get("incentives") is not None]
    return signed[-1]["contract"] if signed else None


def build(season=SEASON, root=ROOT, on=None):
    """The season-close record for `on` (default: the Finals' clinching date), or None if the season is still open."""
    from .career_stats import aggregate, collect_games, select
    from .incentives import evaluate, earned_honors
    from .season_games import season_games
    root = Path(root)
    day = on or close_date(root)
    if not day:
        return None
    identity = _read(root / PLAYER / "professional_identity.json")
    records = collect_games(root / PLAYER, identity, day)
    line = lambda comp: aggregate(select(records, competition=comp, season=season, end=day))
    reg, po = line("regular"), line("playoff")
    games = season_games(season, root)
    miami = sum(1 for g in games if "Miami Heat" in (g["home"], g["away"]))
    contract = wade_contract(root)
    summary = lambda a: {"gp": a["gp"], "gs": a["gs"], "minutes_per_game": round(a["pg"]["minutes"], 2) if a["gp"] else None,
                         "points_per_game": round(a["pg"]["pts"], 2) if a["gp"] else None, "complete": bool(a["complete"])}
    return {
        "schema_version": 1, "season": season, "close_date": day,
        "competitions_closed": ["regular", "playoff"],
        "regular_season_games_scheduled": miami,
        "source": "08_Playoffs/README.md",
        "rule": __doc__.split("\n\n", 1)[0].replace("\n", " "),
        "wade": {"regular": summary(reg), "playoff": summary(po),
                 "honors": [{"name": a["name"], "awarded_on": a["awarded_on"], "id": a["id"]} for a in earned_honors(season, day, root)]},
        "incentive_evaluation": evaluate(contract, season, day, root) if contract else [],
    }


def close(season=SEASON, root=ROOT, write=True):
    """Write the record and the standing snapshot once the Finals are over and the clock has reached them."""
    from .write_back import clock
    from . import standing
    root = Path(root)
    target = path(season, root)
    if target.is_file():
        return None
    day = close_date(root)
    if not day or day > clock(root):
        return None
    record = build(season, root, day)
    if write:
        target.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        standing.record(root, clock(root), "season_close", f"{season}/season_close.json")
        # The next season's expectations (roadmap 18): Wade's own update and real players' capped feedback.
        from .protagonist import build_profile
        from .trajectories import feedback_path
        nxt = root / PLAYER / "2004-05"
        nxt.mkdir(parents=True, exist_ok=True)
        (nxt / "wade_expected_profile.json").write_text(
            json.dumps(build_profile(root, season, "2004-05", day), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        (root / feedback_path("2004-05")).write_text(
            json.dumps(feedback(root, season, "2004-05", day), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return record


def feedback(root=ROOT, season=SEASON, next_season="2004-05", on=None):
    """Real players' capped 20% feedback for the next season (`trajectories.season_feedback`) from every closed
    regular-season result of the season: each player's box lines against the rates the engine expected for him."""
    from .player_stats import SEASON_SOURCES, read_json
    from .trajectories import load_trajectories, season_feedback
    from .write_back import _key, bbr_lookup, closed_results, game_records, registry
    root = Path(root)
    lookup = bbr_lookup(root, season)
    by_name = {}
    for p in registry(root)["players"]:
        if p.get("bbr_id"):
            by_name.setdefault(_key(p["name"]), p["bbr_id"])
    baselines = read_json(root / SEASON_SOURCES[season]["ratings"])["rate_baselines"]
    trajectories = load_trajectories(root, season)
    lines = {}
    for row in closed_results(root, season, on):
        r = row["result"]
        raw = {(side, p["player_id"]): p for side in ("home", "away") for p in r["player_stats"][side]}
        for side, pid, bbr, _record in game_records(row, root, season):
            bbr = bbr or lookup.get((r[side], _key(pid))) or by_name.get(_key(pid))
            line = raw.get((side, pid))
            if bbr and line and line.get("seconds"):
                lines.setdefault(bbr, []).append(line)
    expected = {b: trajectories.expected_profile(b, season, baselines)["rates"] for b in lines if trajectories.has(b, season)}
    return season_feedback(lines, expected, baselines, season, next_season)
