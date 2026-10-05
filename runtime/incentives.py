"""Evaluate a signed contract's incentive clauses for one season against the dated career record (roadmap 15a, 18).

Each clause is judged only from evidence the career records hold on or after the season's last regular-season day:
- `performance` clauses with a minutes benchmark: closed regular-season minutes (career_stats, Wade's game records);
- `performance` clauses naming an honor (All-Rookie, All-NBA, All-Star, MVP...): earned honors in `awards.json` for that
  season, announced on or before the evaluation date (`season_awards.py` writes them);
- `conditioning_program` and `physical_condition` clauses: a recorded camp review or reply that states the condition;
  without one the clause is `unrecorded`, never assumed.
A clause is `met`, `not_met` or `unrecorded`, with its evidence path. Nothing here pays, signs or edits a contract: the
season rollover records the evaluation beside the contract (`contract_schedules.json` bonus_evaluation) and the cap
accounting reads it.
"""
from __future__ import annotations

import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PLAYER = Path("career/Dwyane_Wade")
HONOR_WORDS = (("All-Rookie", "All-Rookie"), ("All-NBA", "All-NBA"), ("All-Star", "All-Star"),
               ("Most Valuable Player", "Most Valuable Player"), ("Rookie of the Year", "Rookie of the Year"))


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def regular_minutes(season, on, root=ROOT):
    """Wade's closed regular-season minutes for the season, from his game records."""
    from .career_stats import aggregate, collect_games, select
    root = Path(root)
    identity = _read(root / PLAYER / "professional_identity.json")
    records = collect_games(root / PLAYER, identity, on)
    a = aggregate(select(records, competition="regular", season=season, end=on))
    return (a["totals"]["seconds"] or 0) / 60.0 if a["gp"] else 0.0, a["gp"]


def earned_honors(season, on, root=ROOT):
    data = _read(Path(root) / PLAYER / "awards.json")
    return [a for a in data["awards"] if a["season"] == season and a["status"] == "earned" and a["awarded_on"] <= on]


def evaluate_clause(clause, season, on, root=ROOT):
    root = Path(root)
    benchmark = clause["benchmarks"].get(season, "")
    out = {"id": clause["id"], "kind": clause["kind"], "classification": clause["classification"],
           "benchmark": benchmark, "amount": clause.get("amounts", {}).get(season)}
    if clause["kind"] == "performance":
        m = re.search(r"([\d,]+) regular-season minutes", benchmark)
        if m:
            need = int(m.group(1).replace(",", ""))
            minutes, games = regular_minutes(season, on, root)
            return dict(out, status="met" if minutes >= need else "not_met",
                        evidence=f"{minutes:,.0f} closed regular-season minutes in {games} games (career_stats, through {on})")
        for word, label in HONOR_WORDS:
            if word in benchmark:
                hits = [a for a in earned_honors(season, on, root) if label in a["name"]]
                return dict(out, status="met" if hits else "not_met",
                            evidence=("; ".join(f"{a['name']} ({a['awarded_on']}, {a['source']})" for a in hits)
                                      or f"no {label} honor in awards.json for {season} through {on}"))
        return dict(out, status="unrecorded", evidence="benchmark not machine-readable; needs a recorded evaluation")
    camp = root / PLAYER / season / "04_Training_Camp"
    review = camp / "Wade_Camp_Review.md"
    reply = camp / "wade_reply.json"
    if clause["kind"] == "physical_condition" and review.is_file():
        row = next((l for l in review.read_text(encoding="utf-8").splitlines() if l.startswith("| Conditioning")), None)
        if row and "cleared" in row:
            return dict(out, status="met", evidence=f"{review.relative_to(root / PLAYER).as_posix()}: {row.strip()}")
    if clause["kind"] == "conditioning_program" and reply.is_file() and review.is_file():
        text = _read(reply).get("reply", "")
        if "conditioning program" in text and "cleared" in review.read_text(encoding="utf-8"):
            return dict(out, status="met", evidence=(f"{reply.relative_to(root / PLAYER).as_posix()} (Wade took Miami's "
                                                     f"designated program) and {review.relative_to(root / PLAYER).as_posix()} (cleared)"))
    return dict(out, status="unrecorded", evidence="no recorded camp evaluation states this condition")


def evaluate(contract, season, on, root=ROOT):
    """[clause evaluations] for the contract's incentives in the season."""
    return [evaluate_clause(c, season, on, root) for c in contract.get("incentives", [])]
