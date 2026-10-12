"""Evaluate a signed contract's incentive clauses for one season against the dated career record (roadmap 15a, 18).

Each clause is judged only from evidence the career records hold on or after the season's last regular-season day:
- `performance` clauses with a minutes benchmark: closed regular-season minutes (career_stats, Wade's game records);
- `performance` clauses with a scoring benchmark ("At least X points per game while appearing in at least N games"):
  closed regular-season points and games from the same records;
- `performance` clauses naming an honor (All-Rookie, All-NBA, All-Star, MVP...): earned honors in `awards.json` for that
  season, announced on or before the evaluation date (`season_awards.py` writes them);
- `conditioning_program` and `physical_condition` clauses: a recorded camp review or reply that states the condition;
  without one the clause is `unrecorded`, never assumed.
A clause is `met`, `not_met` or `unrecorded`, with its evidence path. Nothing here pays, signs or edits a contract.

The season close writes each season's evaluation once (`season_close.json` incentive_evaluation). A clause the evaluator
of its date could not read is corrected by a dated record beside it (`season_close_corrections.json`: the corrected and
the superseded values, in force from CORRECTED_FROM), never by rewriting the close: the 2004-05 and 2005-06 scoring
clauses, closed as `unrecorded` before the scoring benchmark was read, were both met (21.29 points in 76 games, 27.56 in
82). `season_evaluation` reads a season's evaluation on a date with the corrections then in force. The rollover writes
`bonus_evaluation` (every closed season of the contract: each clause, the Unlikely bonuses earned and the included
amounts) on Wade's new contract-sheet row, and the earned Unlikely bonuses of the season it closes on that season's
finance summary (`earned_unlikely_bonuses`): an Unlikely bonus counts in Team Salary only once earned, at its season's
end. Classifications already recorded and the cap decisions taken on them stand.

Where an earned bonus flows, from BONUS_FLOW_FROM (the day the corrections take effect; every record written before
stands, and the 2004 and 2005 rollovers replay unchanged): the live season's finance summary and cap sheet
(`finance_bonuses`, written by `signing.refresh_finance` and checked by `signing.ledger_errors`, so
`scripts/reconcile.py` rebuilds a summary that lacks them), and the rollover (`Rollover.bonus_records`). It never
enters the counted salary the cap room, the payrolls and the trade rules read: those count a season's Salary while it
is played, and an earned bonus belongs to the closed season's end. No decision reads it: Wade's 2006-07 option year
carries no incentives, so no later Likely/Unlikely classification depends on it, and the career keeps no record of
cash paid (Wade's earnings).
"""
from __future__ import annotations

import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PLAYER = Path("career/Dwyane_Wade")
SCORING = re.compile(r"At least ([\d.]+) points per game while appearing in at least (\d+) games")
CORRECTED_FROM = "2006-06-21"      # the audit's corrections of closed evaluations take effect the day after the clock
CORRECTION_REASON = ("audit (October 2026): the season close's evaluator did not read a scoring benchmark and closed the "
                     "clause unrecorded; the closed regular-season results decide it")
BONUS_FLOW_FROM = CORRECTED_FROM   # the normal writers carry earned bonuses from this date (finance summary, rollover)
HONOR_WORDS = (("All-Rookie", "All-Rookie"), ("All-NBA", "All-NBA"), ("All-Star", "All-Star"),
               ("Most Valuable Player", "Most Valuable Player"), ("Rookie of the Year", "Rookie of the Year"))


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def regular_line(season, on, root=ROOT):
    """Wade's closed regular-season (minutes, games, points) for the season, from his game records."""
    from .career_stats import aggregate, collect_games, select
    root = Path(root)
    identity = _read(root / PLAYER / "professional_identity.json")
    records = collect_games(root / PLAYER, identity, on)
    a = aggregate(select(records, competition="regular", season=season, end=on))
    if not a["gp"]:
        return 0.0, 0, 0
    return (a["totals"]["seconds"] or 0) / 60.0, a["gp"], a["totals"]["pts"] or 0


def regular_minutes(season, on, root=ROOT):
    """Wade's closed regular-season minutes and games for the season, from his game records."""
    minutes, games, _ = regular_line(season, on, root)
    return minutes, games


def earned_honors(season, on, root=ROOT):
    """The season's earned honors announced by the date. An All-Star weekend game's MVP is an exhibition honor
    (`runtime/all_star_games.py`): no clause reads it, though its name contains "All-Star"."""
    from .era import EXHIBITION_GAME_TYPES
    data = _read(Path(root) / PLAYER / "awards.json")
    return [a for a in data["awards"] if a["season"] == season and a["status"] == "earned" and a["awarded_on"] <= on
            and a["competition"] not in EXHIBITION_GAME_TYPES]


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
        m = SCORING.search(benchmark)
        if m:
            need, least = float(m.group(1)), int(m.group(2))
            _, games, points = regular_line(season, on, root)
            ppg = points / games if games else 0.0
            return dict(out, status="met" if games >= least and ppg >= need else "not_met",
                        evidence=(f"{points:,} closed regular-season points in {games} games, {ppg:.2f} per game "
                                  f"(career_stats, through {on})"))
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


# -- closed evaluations, their dated corrections and the bonus record ----------------------------------------------
def close_path(season):
    return PLAYER / season / "season_close.json"


def corrections_path(season):
    return PLAYER / season / "season_close_corrections.json"


def correction_record(season, root=ROOT, on=CORRECTED_FROM):
    """The dated correction of a closed season's evaluation, or None: each performance clause the close recorded as
    `unrecorded` that the evaluator now decides from the evidence of the close date (the corrected and the superseded
    values side by side). The close itself is never rewritten."""
    root = Path(root)
    close = _read(root / close_path(season))
    from .season_close import wade_contract
    contract = wade_contract(root) or {}
    clauses = {c["id"]: c for c in contract.get("incentives", [])}
    items = []
    for e in close.get("incentive_evaluation", []):
        if e["status"] != "unrecorded" or e["kind"] != "performance" or e["id"] not in clauses:
            continue
        fresh = evaluate_clause(clauses[e["id"]], season, close["close_date"], root)
        if fresh["status"] == "unrecorded":
            continue
        items.append({"id": e["id"], "status": fresh["status"], "evidence": fresh["evidence"],
                      "superseded": {"status": e["status"], "evidence": e["evidence"]}})
    if not items:
        return None
    return {"schema_version": 1, "season": season, "kind": "season_close_correction", "corrected_on": on,
            "source": close_path(season).relative_to(PLAYER).as_posix(), "reason": CORRECTION_REASON,
            "incentive_evaluation": items}


def season_evaluation(season, on, root=ROOT):
    """A closed season's clause evaluations on a date: the season close's, with each correction in force by then (the
    corrected clause carries `correction` {corrected_on, reason, superseded}). None before the close."""
    root = Path(root)
    path = root / close_path(season)
    if not path.is_file():
        return None
    close = _read(path)
    if close["close_date"] > on:
        return None
    out = [dict(e) for e in close.get("incentive_evaluation", [])]
    corr = root / corrections_path(season)
    if corr.is_file():
        record = _read(corr)
        if record["corrected_on"] <= on:
            fixes = {c["id"]: c for c in record["incentive_evaluation"]}
            for e in out:
                c = fixes.get(e["id"])
                if c:
                    e.update(status=c["status"], evidence=c["evidence"],
                             correction={"corrected_on": record["corrected_on"], "reason": record["reason"], "superseded": c["superseded"]})
    return out


def bonus_evaluation(entry, on, root=ROOT):
    """{season: evaluation} for every season of a contract-sheet entry's incentives closed by the date: each clause's
    status and amount, the Unlikely bonuses earned (they count in Team Salary only once earned) and the included
    amounts (counted as Salary from the signing). Seasons not yet closed are left out."""
    seasons = sorted({s for c in entry.get("incentives", []) for s in c.get("amounts", {})})
    out = {}
    for season in seasons:
        evaluation = season_evaluation(season, on, root)
        if evaluation is None:
            continue
        close = _read(Path(root) / close_path(season))
        clauses = [{"id": e["id"], "classification": e["classification"], "amount": e["amount"], "status": e["status"],
                    **({"corrected_on": e["correction"]["corrected_on"]} if e.get("correction") else {})} for e in evaluation]
        out[season] = {"evaluated_on": close["close_date"], "source": close_path(season).relative_to(PLAYER).as_posix(),
                       "clauses": clauses,
                       "earned_unlikely": sum(c["amount"] or 0 for c in clauses if c["classification"] == "unlikely" and c["status"] == "met"),
                       "earned_likely": sum(c["amount"] or 0 for c in clauses if c["classification"] == "likely" and c["status"] == "met"),
                       "unresolved": [c["id"] for c in clauses if c["status"] == "unrecorded"]}
    return out


def earned_unlikely(entry, season, on, root=ROOT):
    """[{player, season, clause, amount, evaluated_on, source, corrected_on?}] for the Unlikely bonuses an entry earned in
    the season (`corrected_on`: the clause was met by a dated correction of its close)."""
    evaluation = bonus_evaluation(entry, on, root).get(season)
    if not evaluation:
        return []
    return [{"player": entry["player"], "season": season, "clause": c["id"], "amount": c["amount"],
             "evaluated_on": evaluation["evaluated_on"], "source": evaluation["source"],
             **({"corrected_on": c["corrected_on"]} if c.get("corrected_on") else {})}
            for c in evaluation["clauses"] if c["classification"] == "unlikely" and c["status"] == "met"]


def wade_entry(season, root=ROOT):
    """Wade's row with incentive clauses on a season's contract sheet, or None."""
    path = Path(root) / PLAYER / season / "00_Team/Finances/contract_schedules.json"
    if not path.is_file():
        return None
    return next((e for e in _read(path)["players"] if e.get("player") == "Dwyane Wade" and e.get("incentives")), None)


def finance_bonuses(season, on, root=ROOT):
    """The earned Unlikely bonuses a season's finance summary dated `on` carries (`earned_unlikely_bonuses`): Wade's
    bonuses earned in that season as its evaluation stands on the date, corrections in force included; [] before
    BONUS_FLOW_FROM, before the season's close, or for a season with no clause."""
    if on < BONUS_FLOW_FROM:
        return []
    entry = wade_entry(season, root)
    return earned_unlikely(entry, season, on, root) if entry else []


def incentive_errors(root=ROOT):
    """Every correction record supersedes exactly what its season close recorded and states what the evaluator decides
    from the close date's evidence; none is dated before CORRECTED_FROM."""
    root = Path(root)
    errors = []
    for path in sorted((root / PLAYER).glob("*/season_close_corrections.json")):
        season = path.parent.name
        rel = path.relative_to(root).as_posix()
        record = _read(path)
        if not (root / close_path(season)).is_file():
            errors.append(f"{rel}: corrects a season with no season_close.json")
            continue
        if record.get("corrected_on", "") < CORRECTED_FROM:
            errors.append(f"{rel}: a correction takes effect no earlier than {CORRECTED_FROM}")
        expected = correction_record(season, root, record.get("corrected_on"))
        if expected is None or record.get("incentive_evaluation") != expected["incentive_evaluation"]:
            errors.append(f"{rel}: does not match the season close and the evaluator (runtime/incentives.correction_record)")
    return errors

