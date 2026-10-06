#!/usr/bin/env python3
"""Miami's trades with real clubs (docs/front_office.md, trades).

  python scripts/run_trade.py --search 2003-07-20          rank the proposals Miami's front office would make; writes nothing
  python scripts/run_trade.py --propose 2003-07-20         write the top-ranked proposal and its acceptance draw
  python scripts/run_trade.py --write 2003-07-22           apply drawn answers: an accepted trade enters every record
  python scripts/run_trade.py --shop 2003-07-17            the front office shops its agreed own free agents as sign-and-trades
  python scripts/run_trade.py --season-day 2005-01-03      the driver's daily step: apply drawn answers, then a due in-season scan

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
from scripts.refresh_career_views import refresh_career_views # noqa: E402

SEASON = signing.SEASON          # the live season (runtime/seasons.py)
TRADES = signing.TRADES


def requests(root=ROOT):
    """Wade's requests logged in the season's phase folders (the current one and every earlier one this season)."""
    out = []
    for path in sorted((Path(root) / f"career/Dwyane_Wade/{SEASON}").glob("*/wade_requests.json")):
        out += read(path, root)["requests"]
    return out


def standing(root=ROOT):
    """Wade's computed standing on the career date (runtime/standing.py)."""
    state = read(signing.STATE, root)
    return standing_on(root, state["current_date"])


def season_records(root=ROOT):
    """This season's trade records (proposals with their answers), oldest first."""
    folder = Path(root) / TRADES
    out = []
    for path in sorted(folder.glob("*.json")) if folder.exists() else []:
        if not path.name.endswith((".decision.json", ".result.json")):
            out.append(json.loads(path.read_text(encoding="utf-8")))
    return sorted(out, key=lambda r: (r["date"], r["trade_id"]))


def in_season(day, root=ROOT):
    """From opening night to the trade deadline: the in-season rules of `scan_due` apply."""
    from runtime.seasons import dates
    gates = dates(SEASON, root)
    return gates["opening_night"] <= day <= gates["trade_deadline"]


def scan_due(day, root=ROOT):
    """Whether the front office looks for a trade on `day` during the season (None outside it, else (due, why)).

    Judgement (docs/front_office.md, In-season trades): Mondays from SCAN_FROM (December 15, when the summer's
    signings become tradable league-wide) to the deadline; no new proposal while one awaits its answer; none for
    TRADE_COOLDOWN_DAYS after a completed trade; at most MAX_IN_SEASON_TRADES completed trades a season."""
    from datetime import date, timedelta
    from runtime.seasons import dates
    from runtime.trades import MAX_IN_SEASON_TRADES, TRADE_COOLDOWN_DAYS
    if not in_season(day, root):
        return None
    first = f"{SEASON[:4]}-12-15"
    if day < first or date.fromisoformat(day).weekday() != 0:
        return False, f"scans run on Mondays from {first}"
    records = [r for r in season_records(root) if r.get("kind", "trade") == "trade" and r["date"] >= dates(SEASON, root)["opening_night"]]
    if any(r["status"] == "proposed" for r in records):
        return False, "a proposal awaits its answer"
    done = [r for r in records if r["status"] == "completed"]
    if len(done) >= MAX_IN_SEASON_TRADES:
        return False, f"{len(done)} in-season trades made (at most {MAX_IN_SEASON_TRADES})"
    if done and day < (date.fromisoformat(done[-1]["applied"]) + timedelta(days=TRADE_COOLDOWN_DAYS)).isoformat():
        return False, f"the roster settles after the {done[-1]['applied']} trade"
    return True, "scan"


def search(day, root=ROOT, limit=10):
    from runtime.trades import IN_SEASON_MIN_GAIN, SEARCH_MIN_GAIN, package_key
    desk = TradeDesk(day, FrontOffice(day, Market(day, root), root), root)
    snap = standing(root)
    declined = {package_key(r["trade"]) for r in season_records(root) if r["status"] in ("declined", "void")}
    return desk, desk.search(requests(root), snap["standing"], limit=limit, consultations=consultations.answers(root, SEASON, day),
                             min_gain=IN_SEASON_MIN_GAIN if in_season(day, root) else SEARCH_MIN_GAIN, exclude=declined)


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
    due = scan_due(day, root)
    if due is not None and not due[0]:
        print(f"no in-season scan on {day}: {due[1]}")
        return None
    desk, found = search(day, root, limit=1)
    snap = standing(root)
    candidates = found + desk.needing_consultation
    if not candidates:
        return None
    top = max(candidates, key=lambda f: f["score"])
    trade = top["trade"]
    name = top.get("consultation_player") or trade["miami_in"][0]
    if top.get("consultation") == "required":
        p = desk.partner_player(trade["partner"], name)
        fo = desk.fo
        room = fo.cap_room()
        pos = desk.assets.positions.get(p.get("bbr_id"), (None, "SF", 9))[1].split("-")[0]
        evidence = {"value": top.get("star_value"), "line": None, "salary": f"${desk.assets.salary(p):,} in {SEASON}",
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
                signing.apply_trade(writer, record, day, desk=desk)
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


def season_day(day, root=ROOT):
    """The driver's in-season step (scripts/advance.py): apply answers drawn for earlier proposals, then, when a scan
    is due, the front office's proposal. Returns the lines to report; a completed trade starts with "MIAMI TRADE"."""
    lines = []
    applied, pending = write(day, root)
    for trade_id, status in applied:
        record = json.loads((Path(root) / TRADES / f"{trade_id}.json").read_text(encoding="utf-8"))
        t = record["trade"]
        outs = ", ".join(t.get("miami_out", []) + [f"{x['year']} round {x['round']} pick" for x in t.get("picks_out", [])]) or "nothing"
        ins = ", ".join(t.get("miami_in", []) + [f"{x['year']} round {x['round']} pick" for x in t.get("picks_in", [])]) or "nothing"
        head = "MIAMI TRADE" if status == "completed" else f"Miami trade {status}"
        lines.append(f"{head}: {t['partner']} {'accepts' if status == 'completed' else 'answers'}: Miami sends {outs} for {ins} ({trade_id})")
    if pending:
        return lines + ["awaiting the draw: " + ", ".join(pending)]
    due = scan_due(day, root)
    if due and due[0]:
        record = propose(day, root)
        if record:
            t = record["trade"]
            lines.append(f"Miami proposes to {t['partner']}: {', '.join(t['miami_out'])}"
                         + "".join(f" + {x['year']} round {x['round']} pick" for x in t.get("picks_out", []))
                         + f" for {', '.join(t['miami_in'])} (acceptance {record['ranking']['accept']:.2f}, engine draw)")
        else:
            lines.append("trade scan: no proposal worth making")
    return lines


def main(argv):
    if len(argv) != 3 or argv[1] not in ("--search", "--propose", "--write", "--shop", "--season-day"):
        raise SystemExit(__doc__)
    day = argv[2]
    if argv[1] == "--season-day":
        lines = season_day(day)
        print("\n".join(lines))
        if any(not l.startswith("trade scan") for l in lines):
            refresh_career_views(ROOT)
        return
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
    if argv[1] != "--search":
        refreshed = refresh_career_views(ROOT)
        print(f"Updated {len(refreshed)} detailed career views; open career/Dwyane_Wade/Milestones/index.html#trade_update.")


if __name__ == "__main__":
    main(sys.argv)
