#!/usr/bin/env python3
"""Miami's trades with real clubs (docs/front_office.md, trades).

  python scripts/run_trade.py --search 2003-07-20          rank the proposals Miami's front office would make; writes nothing
  python scripts/run_trade.py --propose 2003-07-20         write the top-ranked proposal and its acceptance draw
  python scripts/run_trade.py --write 2003-07-22           apply drawn answers: an accepted trade enters every record
  python scripts/run_trade.py --shop 2003-07-17            the front office shops its agreed own free agents as sign-and-trades

The front office chooses the proposal; the user only triggers the step (AGENTS.md: trades are
club decisions). A proposal is a record under `00_Team/Transactions/Trades/` with a decision
packet beside it; the engine draws the real club's answer, `scripts/collect_results.py` writes
the result, and `--write` applies it on or after the date. Wade's requests (`trade_target`,
`trade_opposed`) in the phase folder's `wade_requests.json` weigh on the ranking by his computed
standing (runtime/standing.py). At `franchise` standing the front office asks Wade before it
trades for another star (runtime/consultations.py): `--propose` writes the consultation instead
of the proposal and makes no other proposal that day; while any consultation is unanswered,
whatever day it was asked, `--propose` and `--shop` write nothing and report it (one question at
a time, never asked twice; a re-run of the same date finds the same ids). `--shop` takes no
player: the front office picks which agreed own free agent, if any, it signs and trades in one
transaction (runtime/gm.py RESIGN_AND_TRADE_FIT) and writes at most one proposal; a player Miami
has already re-signed is a signed player under the newly-signed restriction and is not shopped.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from runtime import consultations, signing              # noqa: E402
from runtime.gm import FrontOffice                      # noqa: E402
from runtime.market import Market                       # noqa: E402
from runtime.standing import standing_on                # noqa: E402
from runtime.trades import TradeDesk                    # noqa: E402
from runtime.valuation import read                      # noqa: E402

SEASON = "2003-04"
TRADES = signing.TRADES


def requests(root=ROOT):
    state = read(signing.STATE, root)
    folder = Path(f"career/Dwyane_Wade/{SEASON}") / Path(state.get("current_note", "01_Free_Agency/note.md")).parent
    path = Path(root) / folder / "wade_requests.json"
    return read(path, root)["requests"] if path.exists() else []


def standing(root=ROOT):
    """Wade's computed standing on the career date (runtime/standing.py)."""
    state = read(signing.STATE, root)
    return standing_on(root, state["current_date"])


def search(day, root=ROOT, limit=10):
    desk = TradeDesk(day, FrontOffice(day, Market(day, root), root), root)
    snap = standing(root)
    return desk, desk.search(requests(root), snap["standing"], limit=limit, consultations=consultations.answers(root, SEASON, day))


def close_answered(day, root=ROOT):
    """Close the consultations Wade has answered since the last run (their pending entries leave the state)."""
    writer = signing.Writer(root)
    state = writer.load(signing.STATE)
    closed = consultations.close_answered(root, state, SEASON)
    for r in closed:
        signing.note_event(writer, signing.phase_note_for(state), r["answered"] or day,
                           f"Wade {'approves' if r['answer'] == 'approve' else 'objects to'} the front office adding {r['player']} ({r['kind']}).")
    if closed:
        writer.commit()
    return closed


def awaiting(day, root=ROOT):
    """The unanswered consultations the front office waits on (after closing the answered ones): nothing is
    proposed, shopped or asked while one is open."""
    close_answered(day, root)
    waiting = consultations.unanswered(root, SEASON, day)
    if waiting:
        print("awaiting Wade's answer: " + ", ".join(waiting))
    return waiting


def propose(day, root=ROOT):
    """Write the front office's top-ranked proposal and its acceptance packet; returns the record, or None
    when nothing is worth proposing, a consultation is still unanswered, or the top choice waits for Wade's
    answer (the stall is deliberate)."""
    if awaiting(day, root):
        return None
    desk, found = search(day, root, limit=1)
    snap = standing(root)
    candidates = found + desk.needing_consultation
    if not candidates:
        return None
    top = max(candidates, key=lambda f: f["score"])
    trade = top["trade"]
    name = trade["miami_in"][0]
    if top.get("consultation") == "required":
        p = desk.partner_player(trade["partner"], name)
        fo = desk.fo
        room = fo.cap_room()
        pos = desk.assets.positions.get(p.get("bbr_id"), (None, "SF", 9))[1].split("-")[0]
        evidence = {"value": top.get("star_value"), "line": None, "salary": f"${desk.assets.salary(p):,} in 2003-04",
                    "cap_position": f"room ${room['room']:,} on the {'published' if room['cap_known'] else 'planning'} cap ${room['cap']:,}",
                    "fit": f"{pos}: fit {fo.fit(pos, fo.needs())}",
                    "reason": f"top-ranked proposal on {day}: {', '.join(trade['miami_out'])} for {name} (score {top['score']}, acceptance {top['accept']})"}
        writer = signing.Writer(root)
        state = writer.load(signing.STATE)
        record = consultations.ask(root, state, day, "trade", name, p.get("bbr_id"), trade["partner"], terms=None, trade_id=None,
                                   basis=evidence["reason"], evidence=evidence, season=SEASON, standing=snap)
        signing.note_event(writer, signing.phase_note_for(state), day,
                           f"Franchise consultation: the front office asks Wade before it trades for {name}. Record: `Wade_Consultations/{record['id']}.json`.")
        writer.commit()
        print(f"awaiting Wade's answer: {record['id']}")
        return None
    consultation = None
    if top.get("consultation") == "approved":
        consultation = consultations.answer_of(root, SEASON, name, day, "trade")["id"]
    return signing.write_proposal(root, desk, trade, top, day, kind="trade", standing=snap, consultation=consultation)


def write(day, root=ROOT):
    """Apply drawn answers to proposals dated on or before the day (sign-and-trades are applied by the free-agency driver)."""
    folder = Path(root) / TRADES
    applied, pending = [], []
    if not folder.exists():
        return applied, pending
    for path in sorted(folder.glob("*.json")):
        if path.name.endswith(".decision.json") or path.name.endswith(".result.json"):
            continue
        record = json.loads(path.read_text(encoding="utf-8"))
        if record["status"] != "proposed" or record["date"] > day or record.get("kind") == "sign_and_trade":
            continue
        result = folder / f"{record['decision_event']}.decision.result.json"
        if not result.exists():
            pending.append(record["decision_event"])
            continue
        outcome = json.loads(result.read_text(encoding="utf-8"))["outcome"]
        writer = signing.Writer(root)
        record["answer"] = {"outcome": outcome, "date": day}
        if outcome == "accept":
            desk = TradeDesk(day, FrontOffice(day, Market(day, root), root), root)
            errors = desk.errors(record["trade"])
            if errors:
                record["status"] = "void"
                record["void_reason"] = errors
                state = writer.load(signing.STATE)
                signing.note_event(writer, signing.phase_note_for(state), day, f"{record['trade']['partner']} accepted, but the trade is no longer legal on {day}: {'; '.join(errors)}.")
            else:
                signing.apply_trade(writer, record, day)
                record["status"], record["applied"] = "completed", day
                writer.commit()
                signing.refresh_finance(writer, FrontOffice(day, Market(day, root), root), day)
        else:
            record["status"] = "declined"
            state = writer.load(signing.STATE)
            signing.note_event(writer, signing.phase_note_for(state), day, f"{record['trade']['partner']} declines Miami's proposal ({record['trade_id']}).")
        path.write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
        writer.commit()
        applied.append((record["trade_id"], record["status"]))
    return applied, pending


def shop(day, root=ROOT):
    """The front office shops its own agreed free agents (full Bird rights, route Bird, position fit below
    RESIGN_AND_TRADE_FIT) as sign-and-trades signed and traded in one transaction, through the free-agency
    driver's `Run.shop_own`: at most one proposal a day, the draws of a pending one read first, and a player
    no partner takes or whose draws declined is re-signed on the agreed terms. Returns (record or None, the
    candidates considered)."""
    from scripts.run_free_agency import Run, SIGNING
    root = Path(root)
    if awaiting(day, root):
        return None, []
    if day < SIGNING:
        print(f"no contract may be signed before {SIGNING}")
        return None, []
    market = Market(day, root)
    fo = FrontOffice(day, market, root)
    snap = standing(root)
    run = Run(root)
    run.market, run.fo = market, fo
    run.standing, run.state["standing"], run.state["standing_as_of"] = snap["standing"], snap["standing"], snap["as_of"]
    considered, candidates = [], []
    positions = fo._positions()
    for n in run.negotiations():
        rec = n.record
        if n.outside() or n.status not in ("agreed", "trade_pending"):
            continue
        rights = next((p for p in fo.rights["players"] if p["player"] == rec["player"]), {})
        row = {"player": rec["player"], "bbr_id": rec["bbr_id"], "position": rec["plan"].get("position") or positions.get(rec["bbr_id"], "SF"),
               "bird_status": rights.get("bird_status"), "route": rec["agreement"]["route"], "agreed": rec["agreement"]["date"]}
        trade = rec.get("trade")
        if trade:
            considered.append(dict(row, outcome="proposal pending" if not trade.get("outcome") else f"{trade['outcome']}; re-signing on the agreed terms"))
            candidates.append((float("inf"), n))        # a standing proposal (its draws, or the re-signing after a decline) comes before any new one
        elif run.shops(n):
            considered.append(dict(row, outcome="shopped"))
            candidates.append((0.0, n))
        else:
            considered.append(dict(row, outcome="kept"))
    if not candidates:
        return None, considered
    candidates.sort(key=lambda x: -x[0])
    n = candidates[0][1]
    record = run.shop_own(n, day)
    n.save()
    run.writer.commit()
    trade = n.record.get("trade")
    if record is None and trade:
        record = json.loads((root / TRADES / f"{trade['trade_id']}.json").read_text(encoding="utf-8"))
    if run.awaiting:
        outcome = "awaiting Wade's answer"
    elif trade:
        outcome = trade.get("outcome") or "proposal"
        if trade.get("outcome") == "declined" and n.status == "signed":
            outcome = "declined; re-signed on the agreed terms"
    else:
        outcome = "re-signed: no partner"
    for row in considered:
        if row["player"] == n.record["player"]:
            row["outcome"] = outcome
    return record, considered


def main(argv):
    if len(argv) != 3 or argv[1] not in ("--search", "--propose", "--write", "--shop"):
        raise SystemExit(__doc__)
    day = argv[2]
    if argv[1] == "--search":
        desk, found = search(day)
        for f in found:
            t = f["trade"]
            print(f"{f['score']:6.3f}  gain {f['miami_gain']:+.3f}  partner {f['partner_gain']:+.3f}  accept {f['accept']:.2f}  "
                  f"{t['partner']}: {', '.join(t['miami_out'])} -> {', '.join(t['miami_in'])}" + ("  [Wade's request]" if f["wade_request"] else ""))
        for f in desk.needing_consultation:
            t = f["trade"]
            print(f"{f['score']:6.3f}  {t['partner']}: {', '.join(t['miami_out'])} -> {', '.join(t['miami_in'])}  [needs Wade's answer: franchise consultation]")
        if not found and not desk.needing_consultation:
            print("no proposal worth making on this date")
    elif argv[1] == "--propose":
        record = propose(day)
        print(f"proposed {record['trade_id']}: {record['trade']}" if record else "no proposal written on this date")
    elif argv[1] == "--shop":
        record, considered = shop(day)
        for row in considered:
            print(f"{row['player']}: {row['outcome']}")
        print(f"sign-and-trade {record['trade_id']}: {record['status']}" if record else "no re-signed player shopped on this date")
    else:
        applied, pending = write(day)
        for trade_id, status in applied:
            print(f"{trade_id}: {status}")
        if pending:
            print("pending draws: " + ", ".join(pending))


if __name__ == "__main__":
    main(sys.argv)
