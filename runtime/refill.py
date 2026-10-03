"""Filling open roster spots after camp: who is truly available, and how Wade's request is weighed.

The front office fills each open spot (fifteen signed players, `camp.ROSTER_MAX`) at the minimum on
a non-guaranteed contract, the same terms as a camp contract. Candidates are the free agents the
market shows unsigned on the date who are not restricted (`Market.restricted`: a minimum contract is
not an offer sheet), plus *unattached* players: men with no previous NBA club whose real 2003 club was
Miami, so the user's conflict rule 1 leaves them free agents unless simulated Miami signs them
(Udonis Haslem, undrafted in 2002 and in France in 2002-03).

The rule ranks candidates by 2002-03 production value times positional fit. A player with no NBA line
is valued at replacement level, which says nothing is known, not that he is poor. Wade's request for a
candidate the rule does not pick is weighed like every other request
(`front_office.request_override`): the chance it changes the decision is his standing weight times one
minus the rule's margin. The engine draws it, and then the player's own answer.
"""
from __future__ import annotations

import json
from pathlib import Path

from .camp import ROSTER_MAX, playable
from .front_office import request_override
from .player_stats import alias
from .valuation import REPLACEMENT_EFF_PER_GAME, read

ROOT = Path(__file__).resolve().parents[1]
TRANSACTIONS = Path("library/2003/league/nba_2003_offseason_transactions.json")
STATS = Path("library/2003/league/nba_2002_03_player_stats.json")
CAREERS = Path("library/careers/nba_player_careers.json")
PROTAGONIST_IDS = {"wadedw01"}
IDENTITIES = Path("library/2003/league/nba_2003_unattached_identities.json")
MIAMI = "Miami Heat"
UNATTACHED_ACCEPT = 0.90   # an undrafted player with no NBA club offered an NBA roster spot (judgement)
VETERAN_ACCEPT = 0.75      # a veteran still unsigned at the end of October offered a non-guaranteed minimum (judgement)


def unattached(on, root=ROOT):
    """Players with no previous NBA club whose only real 2003 signing was with Miami (rule 1 skips it)."""
    stats = {r["bbr_id"] for r in read(STATS, root)["records"]}
    careers = read(CAREERS, root).get("players", {})
    ident = Path(root) / IDENTITIES
    identities = {p["bbr_id"]: p for p in json.loads(ident.read_text(encoding="utf-8"))["players"]} if ident.is_file() else {}
    out = {}
    for row in read(TRANSACTIONS, root)["signings"]:
        key = row.get("bbr_id")
        if not key or key in PROTAGONIST_IDS:
            continue
        earlier = [s for s in (careers.get(key) or {}).get("seasons", {}) if s < "2003-04"] or identities.get(key, {}).get("nba_history")
        if row.get("to") == MIAMI and not row.get("from") and key not in stats:
            out[key] = {"player": row["player"], "bbr_id": row.get("bbr_id"), "club": None, "unattached": not earlier,
                        "nba_seasons_before_2003_04": 0, "basis": f"real signing with Miami on {row['date']} skipped (rule 1); no previous NBA club"}
    return out


def open_spots(roster):
    return max(0, ROSTER_MAX - sum(1 for p in roster["players"] if playable(p.get("status"))))


def candidates(on, front_office, market, positions, root=ROOT, requested=()):
    """Available, unrestricted free agents not on Miami's books, ranked by value times fit.

    Equal scores are broken by Wade's requests first (the front office is indifferent between them, so the
    request decides), then by the player's name for a stable order."""
    held = {p.get("bbr_id") for p in front_office.roster["players"]} | {p["name"] for p in front_office.roster["players"]}
    needs = front_office.needs()
    pool = {b: p for b, p in market.pool(on).items() if not market.restricted(b) and p.get("club") != MIAMI}
    pool.update({b: p for b, p in unattached(on, root).items() if b not in pool})
    rows = []
    for bbr, p in pool.items():
        if bbr in held or p["player"] in held:
            continue
        value = market.valuation.value(bbr)
        known = value is not None
        value = value if known else REPLACEMENT_EFF_PER_GAME
        pos = positions.get(bbr, "SF")
        fit = front_office.fit(pos, needs)
        rows.append({"player": p["player"], "bbr_id": bbr, "position": pos, "value": round(value, 2), "value_known": known,
                     "fit": fit, "score": round(value * fit, 3), "unattached": bool(p.get("unattached")),
                     "salary": market.valuation.minimum(p.get("nba_seasons_before_2003_04"))})
    for r in rows:
        r["wade_request"] = r["player"] in requested
    rows.sort(key=lambda r: (-r["score"], not r["wade_request"], r["player"]))
    return rows


def request_packet(on, request, row, last_pick, standing):
    """Wade's request for a candidate the rule did not pick: may it take the last open spot?"""
    margin = 0.0 if not last_pick or last_pick["score"] <= 0 else max(0.0, min(1.0, (last_pick["score"] - row["score"]) / last_pick["score"]))
    p = request_override("pass", "sign", margin, standing)
    return {"event_id": f"{on}-refill-request-{row['bbr_id']}", "date": on,
            "question": f"Does Miami give its last open roster spot to {row['player']}, as Wade asked, instead of {last_pick['player'] if last_pick else 'leaving it open'}?",
            "decider": "Miami Heat front office (simulated)",
            "options": {"sign": max(0.001, p), "pass": round(1 - max(0.001, p), 3)},
            "basis": (f"Rule ranking by 2002-03 production value x positional fit: {row['player']} {row['score']} "
                      f"({'no NBA line, valued at replacement level' if not row['value_known'] else 'from his 2002-03 line'}) against the last pick "
                      f"{last_pick['player'] if last_pick else 'none'} {last_pick['score'] if last_pick else 0}; margin {margin:.2f}. Wade's request "
                      f"({request['date']}) is weighed at his standing '{standing}': chance = standing weight x (1 - margin) "
                      f"(front_office.request_override). The request does not force the decision.")}


def answer_packet(on, row):
    p = UNATTACHED_ACCEPT if row["unattached"] else VETERAN_ACCEPT
    return {"event_id": f"{on}-refill-answer-{row['bbr_id']}", "date": on,
            "question": f"Does {row['player']} accept Miami's non-guaranteed minimum contract (${row['salary']:,}, 2003-04)?",
            "decider": f"{row['player']} (simulated player)", "options": {"accept": p, "decline": round(1 - p, 3)},
            "basis": ("An undrafted player with no NBA club offered an NBA roster spot" if row["unattached"] else
                      "A veteran still unsigned at the end of October offered a non-guaranteed minimum")
                     + f" (judgement {p}); guaranteed if he is still on the roster on January 10, 2004."}
