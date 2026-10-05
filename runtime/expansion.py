"""The 2004 Charlotte Bobcats expansion draft, simulated (June 22, 2004; the user's decision for a fully simulated
offseason). The real selections are never consulted.

Rules (`library/2004/league/nba_2004_expansion_draft.json`, sourced): each of the 29 clubs protects up to eight
players; Charlotte takes from 14 to 29 players, at most one from any club; a club that loses a player gets a trade
exception equal to his salary.

Decisions (AI front offices, judgement, no chance element):
- Pool: every player with an existing contract or team option for 2004-05 (`runtime/contract_terms.py`) on the club
  the symmetric league holds him with at the end of 2003-04.
- Protection: each club protects its eight most valuable players under contract for 2004-05, valued on evidence of the
  date (simulated 2003-04 Game Score per game x minutes per game, youth weighted: x1.1 at 24 or younger, x0.85 at 32+).
- Charlotte (rebuilding, cap $29.25M for 2004-05): for each club, its best exposed player by value per million of
  2004-05 salary (expiring and cheap contracts preferred); Charlotte takes them best first until it has 14, then
  keeps taking while a player's value per million is at least MIN_VALUE_PER_MILLION and its payroll stays under the cap.
The result is `09_Draft/expansion_2004.json`; the selected players are Charlotte's in the 2004-05 opening book.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEASON = "2003-04"
DATE = "2004-06-22"
RECORD = Path(f"career/Dwyane_Wade/{SEASON}/09_Draft/expansion_2004.json")
RULES = Path("library/2004/league/nba_2004_expansion_draft.json")
CHARLOTTE, MIAMI = "Charlotte Bobcats", "Miami Heat"
PROTECT, MIN_PICKS, MAX_PICKS = 8, 14, 29
CHARLOTTE_CAP = 29_250_000
MIN_VALUE_PER_MILLION = 2.0


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _value(form, name, age):
    f = form.get(name)
    if not f:
        return 0.0
    youth = 1.1 if age and age <= 24 else 0.85 if age and age >= 32 else 1.0
    return max(0.0, f["game_score"]) * f["mpg"] / 30 * youth


def club_lists(root=ROOT):
    """{club: [{"name", "bbr_id", "salary", "value"}]} of players under contract for 2004-05 on the date."""
    from .contract_terms import existing_terms
    from .offseason import simulated_clubs
    from .season_awards import candidates
    from .valuation import Valuation
    from .write_back import closed_results
    root = Path(root)
    val = Valuation(DATE, root)
    form, _ = candidates(root, closed_results(root, SEASON, "2004-04-14"))
    registry = _read(root / "career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json")
    registry = registry["players"] if isinstance(registry, dict) else registry
    names = {p["bbr_id"]: p["name"] for p in registry if p.get("bbr_id")}
    clubs = simulated_clubs(root)
    out = {}
    for b, t in sorted(existing_terms(root).items()):
        club = clubs.get(b) or t["club"]                  # a player who missed 2003-04 stays with his contract's club
        # A player or early-termination option is the player's to decide on June 30, after the draft: not exposable.
        if not club or club == MIAMI or t["option_kind"] in ("player_option", "early_termination_option"):
            continue
        name = names.get(b, b)
        out.setdefault(club, []).append({"name": name, "bbr_id": b, "salary": t["salary"], "years_left": len(t["schedule"]),
                                         "value": round(_value(form, name, val.age(b)), 3)})
    sheet = _read(root / f"career/Dwyane_Wade/{SEASON}/00_Team/Finances/contract_schedules.json")
    roster = {p["name"]: p for p in _read(root / f"career/Dwyane_Wade/{SEASON}/00_Team/Team/Roster/roster.json")["players"]}
    out[MIAMI] = [{"name": p["player"], "bbr_id": (roster.get(p["player"]) or {}).get("bbr_id") or names_by_name(registry).get(p["player"]),
                   "salary": int(p["schedule"]["2004-05"]),
                   "years_left": sum(1 for s, x in p["schedule"].items() if s >= "2004-05" and x),
                   "value": round(_value(form, p["player"], None), 3)}
                  for p in sheet["players"] if (p.get("schedule") or {}).get("2004-05")
                  and p.get("status") not in ("renounced", "released", "traded", "signed_elsewhere", "voided", "waived")]
    return out


def names_by_name(registry):
    return {p["name"]: p.get("bbr_id") for p in registry}


def decide(root=ROOT, lists=None):
    lists = club_lists(root) if lists is None else lists
    protected, exposed = {}, {}
    for club, rows in lists.items():
        ranked = sorted(rows, key=lambda r: (-r["value"], r["name"]))
        protected[club] = [r["name"] for r in ranked[:PROTECT]]
        exposed[club] = ranked[PROTECT:]
    offers = []
    for club, rows in exposed.items():
        if not rows:
            continue
        best = max(rows, key=lambda r: (r["value"] / (r["salary"] / 1e6 * max(1, r["years_left"])), -r["salary"], r["name"]))
        offers.append(dict(best, club=club, per_million=round(best["value"] / (best["salary"] / 1e6 * max(1, best["years_left"])), 3)))
    offers.sort(key=lambda r: (-r["per_million"], r["name"]))
    picks, payroll = [], 0
    for r in offers:
        if len(picks) >= MAX_PICKS:
            break
        if len(picks) >= MIN_PICKS and (r["per_million"] < MIN_VALUE_PER_MILLION or payroll + r["salary"] > CHARLOTTE_CAP):
            continue
        picks.append(r)
        payroll += r["salary"]
    if any(r["club"] == MIAMI for r in picks):
        raise NotImplementedError("Charlotte selected a Miami player: Miami's ledger move is not built")
    return {"schema_version": 1, "kind": "expansion_draft", "club": CHARLOTTE, "date": DATE,
            "rule": __doc__.split("\n\n", 1)[1].strip(), "protected": protected,
            "selections": [{"player": r["name"], "bbr_id": r["bbr_id"], "from": r["club"], "salary_2004_05": r["salary"],
                            "years_left": r["years_left"], "value": r["value"], "trade_exception": r["salary"]} for r in picks],
            "payroll_2004_05": payroll}


def run(root=ROOT, clock=None):
    from .write_back import clock as career_clock
    root = Path(root)
    if (clock or career_clock(root)) < DATE or (root / RECORD).is_file():
        return None
    record = decide(root)
    (root / RECORD).parent.mkdir(parents=True, exist_ok=True)
    (root / RECORD).write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return record


def charlotte_players(root=ROOT):
    """{bbr_id: from club} for Charlotte's expansion selections (empty before the draft)."""
    path = Path(root) / RECORD
    return {s["bbr_id"]: s["from"] for s in _read(path)["selections"] if s.get("bbr_id")} if path.is_file() else {}
