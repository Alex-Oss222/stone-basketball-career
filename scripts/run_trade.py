#!/usr/bin/env python3
"""Miami's trades with real clubs (docs/front_office.md, trades).

  python scripts/run_trade.py --search 2003-07-20          rank the proposals Miami's front office would make; writes nothing
  python scripts/run_trade.py --propose 2003-07-20         write the top-ranked proposal and its acceptance draw
  python scripts/run_trade.py --write 2003-07-22           apply drawn answers: an accepted trade enters every record

The front office chooses the proposal; the user only triggers the step (AGENTS.md: trades are
club decisions). A proposal is a record under `00_Team/Transactions/Trades/` with a decision
packet beside it; the engine draws the real club's answer, `scripts/collect_results.py` writes
the result, and `--write` applies it on or after the date. Wade's requests (`trade_target`,
`trade_opposed`) in the phase folder's `wade_requests.json` weigh on the ranking by his standing.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from runtime import signing                        # noqa: E402
from runtime.decisions import decision_errors      # noqa: E402
from runtime.gm import FrontOffice                 # noqa: E402
from runtime.market import Market                  # noqa: E402
from runtime.trades import TradeDesk               # noqa: E402
from runtime.valuation import read                 # noqa: E402

SEASON = "2003-04"
TRADES = signing.TRADES
STANDING = "unsigned_rookie"


def requests(root=ROOT):
    state = read(signing.STATE, root)
    folder = Path(f"career/Dwyane_Wade/{SEASON}") / Path(state.get("current_note", "01_Free_Agency/note.md")).parent
    path = Path(root) / folder / "wade_requests.json"
    return read(path, root)["requests"] if path.exists() else []


def standing(root=ROOT):
    state = read(signing.STATE, root)
    return "rookie" if state.get("contract_status") == "rookie_scale_contract" else STANDING


def search(day, root=ROOT, limit=10):
    desk = TradeDesk(day, FrontOffice(day, Market(day, root), root), root)
    return desk, desk.search(requests(root), standing(root), limit=limit)


def propose(day, root=ROOT):
    """Write the front office's top-ranked proposal and its acceptance packet; returns the record or None."""
    desk, found = search(day, root, limit=1)
    if not found:
        return None
    trade = found[0]["trade"]
    packet, valuation = desk.acceptance_packet(trade)
    errors = decision_errors(packet)
    if errors:
        raise ValueError("; ".join(errors))
    folder = Path(root) / TRADES
    folder.mkdir(parents=True, exist_ok=True)
    trade_id = desk.trade_id(trade)
    record = {"trade_id": trade_id, "date": day, "status": "proposed", "trade": trade, "valuation": valuation,
              "ranking": found[0], "decision_event": packet["event_id"], "answer": None, "applied": None,
              "basis": "Chosen by Miami's front office as the top-ranked legal proposal on the date (runtime/trades.py search)."}
    (folder / f"{trade_id}.json").write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
    request = folder / f"{packet['event_id']}.decision.json"
    if not request.exists():
        request.write_text(json.dumps(packet, indent=1) + "\n", encoding="utf-8")
    writer = signing.Writer(root)
    state = writer.load(signing.STATE)
    outs = ", ".join(trade["miami_out"]) or "nothing"
    signing.note_event(writer, signing.phase_note_for(state), day,
                       f"Miami proposes to {trade['partner']}: {outs} for {', '.join(trade['miami_in']) or 'nothing'} "
                       f"(acceptance drawn by the engine, {packet['event_id']}). Record: `00_Team/Transactions/Trades/{trade_id}.json`.")
    writer.commit()
    return record


def write(day, root=ROOT):
    """Apply drawn answers to proposals dated on or before the day."""
    folder = Path(root) / TRADES
    applied, pending = [], []
    if not folder.exists():
        return applied, pending
    for path in sorted(folder.glob("*.json")):
        if path.name.endswith(".decision.json") or path.name.endswith(".result.json"):
            continue
        record = json.loads(path.read_text(encoding="utf-8"))
        if record["status"] != "proposed" or record["date"] > day:
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


def main(argv):
    if len(argv) != 3 or argv[1] not in ("--search", "--propose", "--write"):
        raise SystemExit(__doc__)
    day = argv[2]
    if argv[1] == "--search":
        desk, found = search(day)
        for f in found:
            t = f["trade"]
            print(f"{f['score']:6.3f}  gain {f['miami_gain']:+.3f}  partner {f['partner_gain']:+.3f}  accept {f['accept']:.2f}  "
                  f"{t['partner']}: {', '.join(t['miami_out'])} -> {', '.join(t['miami_in'])}" + ("  [Wade's request]" if f["wade_request"] else ""))
        if not found:
            print("no proposal worth making on this date")
    elif argv[1] == "--propose":
        record = propose(day)
        print(f"proposed {record['trade_id']}: {record['trade']}" if record else "no proposal worth making on this date")
    else:
        applied, pending = write(day)
        for trade_id, status in applied:
            print(f"{trade_id}: {status}")
        if pending:
            print("pending draws: " + ", ".join(pending))


if __name__ == "__main__":
    main(sys.argv)
