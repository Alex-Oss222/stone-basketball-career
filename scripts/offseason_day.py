#!/usr/bin/env python3
"""Run the dated offseason events due on a day: the draft lottery (runtime/lottery.py), the 2004 expansion draft
(runtime/expansion.py), the draft (runtime/draft.py) and the summer market from June 30 (runtime/free_agency_2004.py)
for every club. The year is the date's: each module runs in its year context (R5); expansion happened only in 2004.
Miami's draft-rights records follow (runtime/draft_rights.py): from the draft, the rights of an earlier pick still
unsigned end on the live register (`end_rights`); once the market record is closed, the year's routine Required
Tenders are entered on their deadlines (`record_tenders`).

    python scripts/offseason_day.py --write DATE

Each event writes engine decision packets one at a time (a lottery draw, a pick, a trade answer) and is completed by
running this again after `python scripts/draw_decisions.py`; `scripts/advance.py` loops until nothing is pending.
Idempotent: a recorded event is never decided again. Nothing here plays a game or signs a contract.

Every summer-market event dated the day that changes Miami's roster prints one line (`miami_news`), read from the
market's dated events (the replay's own while the summer runs, the written record's once it closes), never
recomputed: a trade in the in-season format, starting "MIAMI TRADE", so the driver stops on it or reports it exactly
as it does an in-season trade (`scripts/advance.py`, `--through-trades`); a signing or re-signing "MIAMI SIGNING"; an
offer sheet Miami made, or one it answered for its own restricted player, "MIAMI OFFER SHEET"; a player Miami
renounced or lost "MIAMI LOSES". Draft night is announced the same way from the year's draft record on every run of
the draft date (`draft_news`): each Miami pick "MIAMI DRAFT", each draft-night trade with Miami on either side
"MIAMI TRADE", so the driver stops on it too.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime import draft, draft_rights, expansion, free_agency_2004, lottery                        # noqa: E402


MIAMI = "Miami Heat"
NEWS = ("MIAMI TRADE", "MIAMI SIGNING", "MIAMI OFFER SHEET", "MIAMI LOSES", "MIAMI DRAFT")    # the driver reads these prefixes
SIGNINGS = ("signing", "re_sign", "rookie_scale_signing", "camp_signing", "qualifying_offer_accepted")


def draft_night(day):
    """The draft record of the year context in force (`draft.year_context`) when `day` is its draft date, else None.
    Every run of draft day reads it, so the day's last run, the one the driver reports, carries the news, not only the
    run that completed the draft (the driver's draw loop runs and discards those)."""
    path = ROOT / draft.RECORD
    if day != draft.DRAFT_DATE or not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def draft_news(record, year):
    """Miami's draft night, read from the year's draft record (`runtime/draft.py`), never recomputed, in slot order (a
    trade before the pick it moved):
    - each Miami pick: "MIAMI DRAFT: Miami selects <player> (<position>) at No. <pick>";
    - each draft-night trade with Miami on either side, in the in-season format and named by its engine draw
      (`<year>-draft-pick-<slot>-trade-down`): Miami moving up, the on-clock club's drawn answer,
      "MIAMI TRADE: <club> accepts: Miami sends No. <later>, <Miami's second-rounder> for No. <slot>"; Miami trading
      down, its own drawn answer to the offer, "MIAMI TRADE: <club> offered and Miami accepts: Miami sends No. <slot>
      for No. <later>, <the club's second-rounder>" (the incoming-offer line of `scripts/run_trade.season_day`)."""
    if not record:
        return []
    rows = []
    for t in record.get("trades", []):
        trade_id = f"{year}-draft-pick-{t['slot']}-trade-down"
        if t["to"] == MIAMI:
            rows.append((t["slot"], 0, f"MIAMI TRADE: {t['from']} accepts: Miami sends No. {t['for_slot']}, {t['plus']} "
                                       f"for No. {t['slot']} ({trade_id})"))
        elif t["from"] == MIAMI:
            rows.append((t["slot"], 0, f"MIAMI TRADE: {t['to']} offered and Miami accepts: Miami sends No. {t['slot']} "
                                       f"for No. {t['for_slot']}, {t['plus']} ({trade_id})"))
    for p in record.get("picks", []):
        if p["club"] == MIAMI:
            rows.append((p["pick"], 1, f"MIAMI DRAFT: Miami selects {p['player']} ({p['position']}) at No. {p['pick']}"))
    return [line for _, _, line in sorted(rows)]


def summer_market(day, year):
    """`runtime/free_agency_2004.run` for the day, step for step (one replay from the recorded draws; the record written
    when the market closes), returning (the record when this run closed the market, else None; the summer's dated
    events). The events are the replay's own (`Market.events`) while the summer runs, since the market writes its record
    only when it closes, and the written record's once it exists. Nothing is recomputed for the announcement."""
    with free_agency_2004.year_context(year, ROOT):
        path = ROOT / free_agency_2004.RECORD
        if path.is_file():
            return None, json.loads(path.read_text(encoding="utf-8"))["events"]
        if day < free_agency_2004.OPTIONS_DATE:
            return None, []
        market = free_agency_2004.Market(ROOT, day)
        record = market.run()
        if record:
            free_agency_2004._write(path, record)
        return record, list(market.events)


def _money(e):
    years = e.get("years")
    return f"${e['salary']:,}" + (f" for {years} year{'s' if years != 1 else ''}" if years else "")


def _route(e):
    return f", {e['route'].replace('_', ' ')}" if e.get("route") else ""


def miami_news(events, day):
    """One line for each summer-market event dated `day` that changes Miami's roster, read from the market's dated events
    (`summer_market`), in the record's order (date, kind, player):
    - a trade with Miami on either side, one line a deal, in the in-season format (`scripts/run_trade.season_day`):
      "MIAMI TRADE: <partner> accepts: Miami sends <players> for <players> (<deal id>)";
    - Miami's signing, re-signing, rookie-scale signing, camp signing or accepted qualifying offer: "MIAMI SIGNING";
    - an offer sheet Miami made, matched or not, or another club's sheet to Miami's restricted player that Miami
      matched: "MIAMI OFFER SHEET" (the sheet and its answer in one line, the signing that follows an unmatched sheet
      folded in);
    - a hold Miami renounced, a player whose rights Miami held signing elsewhere, or a sheet Miami did not match:
      "MIAMI LOSES".
    Qualifying offers tendered and the June options change no roster on the day and print nothing here."""
    today = sorted((e for e in events if e.get("date") == day), key=lambda e: (e["date"], e["kind"], e["player"]))
    by_player = {}
    for e in today:
        by_player.setdefault((e.get("bbr_id") or e["player"], e["kind"]), e)
    lines, deals, folded = [], {}, set()
    for e in today:
        if e["kind"] == "trade" and MIAMI in (e.get("club"), e.get("from")):
            deals.setdefault(e["deal"], []).append(e)
    for e in today:
        kind, club, key = e["kind"], e.get("club"), e.get("bbr_id") or e["player"]
        if kind == "trade" and e.get("deal") in deals:
            rows = deals.pop(e["deal"])
            partner = next(r["club"] if r["from"] == MIAMI else r["from"] for r in rows)
            outs = ", ".join(r["player"] for r in rows if r["from"] == MIAMI) or "nothing"
            ins = ", ".join(r["player"] for r in rows if r["club"] == MIAMI) or "nothing"
            lines.append(f"MIAMI TRADE: {partner} accepts: Miami sends {outs} for {ins} ({e['deal']})")
        elif kind == "offer_sheet" and MIAMI in (club, e.get("from")):
            matched = by_player.get((key, "offer_sheet_matched"))
            unmatched = by_player.get((key, "offer_sheet_not_matched"))
            joined = by_player.get((key, "signing")) or by_player.get((key, "re_sign"))
            holder, offering = e["from"], club
            terms = _money(e)
            if offering == MIAMI and matched:
                lines.append(f"MIAMI OFFER SHEET: {holder} matches Miami's offer sheet to {e['player']} ({terms}); he stays with {holder}")
            elif offering == MIAMI and unmatched:
                folded.add(key)
                lines.append(f"MIAMI OFFER SHEET: {holder} does not match Miami's offer sheet to {e['player']}: he signs with "
                             f"Miami, {_money(joined or e)}{_route(joined or {})}")
            elif offering == MIAMI:
                lines.append(f"MIAMI OFFER SHEET: Miami signs {e['player']}, {holder}'s restricted free agent, to an offer sheet ({terms})")
            elif matched:
                lines.append(f"MIAMI OFFER SHEET: Miami matches the {offering} offer sheet to {e['player']} ({terms}{_route(matched)}); "
                             "he stays with Miami")
            elif unmatched:
                folded.add(key)
                lines.append(f"MIAMI LOSES: Miami does not match the {offering} offer sheet to {e['player']} ({terms}); "
                             f"he signs with {offering}")
        elif kind in SIGNINGS and key not in folded:
            if club == MIAMI:
                what = {"signing": f"Miami signs {e['player']}" + (f" (from {e['from']})" if e.get("from") else ""),
                        "re_sign": f"Miami re-signs {e['player']}",
                        "rookie_scale_signing": f"Miami signs first-round pick {e['player']} to the rookie scale",
                        "camp_signing": f"Miami signs {e['player']} to reach its camp roster",
                        "qualifying_offer_accepted": f"{e['player']} accepts Miami's qualifying offer"}[kind]
                agreed = f", agreed {e['agreed']}" if e.get("agreed") and e["agreed"] != e["date"] else ""
                options = e.get("team_options") or ([e["team_option"]] if e.get("team_option") else [])
                option = f", team option {' and '.join(options)}" if options else ""
                lines.append(f"MIAMI SIGNING: {what}, {_money(e)}{_route(e)}{option}{agreed}")
            elif e.get("from") == MIAMI:
                lines.append(f"MIAMI LOSES: {e['player']}, Miami's free agent, signs with {club}, {_money(e)}{_route(e)}")
        elif kind == "renounce" and club == MIAMI:
            withdrawn = (f"; its ${e['qualifying_offer_withdrawn']:,} qualifying offer is withdrawn"
                         if e.get("qualifying_offer_withdrawn") else "")
            lines.append(f"MIAMI LOSES: Miami renounces {e['player']}'s ${e['hold']:,} cap hold for its ${e['offer']:,} offer to "
                         f"{e['for']}{withdrawn}")
    return lines


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--write", metavar="DATE", required=True)
    args = parser.parse_args()
    year = int(args.write[:4])
    calendar = ROOT / f"library/{year}/league/nba_{year}_offseason_calendar.json"
    if not calendar.is_file():
        if args.write < f"{year}-05-15":                # no offseason event before mid-May
            print("offseason events checked for", args.write)
            return 0
        # stop the clock rather than let it pass an unbuilt offseason
        print(f"no {year} offseason library data ({calendar.relative_to(ROOT)}): the {year} lottery, draft and market "
              "cannot run (docs/ROADMAP.md, R5)", file=sys.stderr)
        return 2
    order = lottery.run(ROOT, args.write, year=year)
    if order:
        print(f"{year} draft lottery: " + ", ".join(f"No. {i + 1} {c}" for i, c in enumerate(order["lottery_winners"])))
    if year == 2004:
        taken = expansion.run(ROOT, args.write)
        if taken:
            print(f"2004 expansion draft: Charlotte selects {len(taken['selections'])} players")
    with draft.year_context(year, ROOT):
        made = draft.run(ROOT, args.write)
        night = made or draft_night(args.write)
    for line in draft_news(night, year):
        print(line)
    if made:
        print(f"{year} draft complete: {len(made['picks'])} picks, {len(made['trades'])} draft-night trade(s)")
    for e in draft_rights.end_rights(ROOT, args.write):
        print(f"{e['player']}: Miami's rights to the No. {e['pick']} pick of the {e['draft_year']} draft ended {e['date']}")
    market, events = summer_market(args.write, year)
    for line in miami_news(events, args.write):
        print(line)
    if market:
        miami = market["clubs"].get(draft.MIAMI, [])
        print(f"{year} free agency complete: {sum(len(v) for v in market['clubs'].values())} contracts; Miami {len(miami)} players, "
              f"payroll ${market['payroll'].get(draft.MIAMI, 0):,}")
    for t in draft_rights.record_tenders(ROOT, year, args.write):
        print(f"Required Tender to {t['player']} (No. {t['pick']}, round {t['round']}) entered on {t['date']}")
    print("offseason events checked for", args.write)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
