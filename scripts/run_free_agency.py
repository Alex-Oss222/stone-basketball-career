#!/usr/bin/env python3
"""Advance Miami's 2003 offseason day by day: June 30 decisions, the free-agency plan, offers,
the players' drawn answers, signings, sign-and-trades and Wade's rookie offer (docs/front_office.md).
Wade's standing is read from `career/Dwyane_Wade/standing.json` (runtime/standing.py); at `franchise`
standing the front office asks him before it adds another star and the day stops until he answers
(runtime/consultations.py).

  python scripts/run_free_agency.py --plan 2003-07-16      print Miami's plan on a date; writes nothing
  python scripts/run_free_agency.py --write 2003-07-20     advance the career clock to the date

The clock moves one day at a time from `current_state.json`. Every chance event (a player's
priorities, his answer to an offer, a real club's match) is a `*.decision.json` the engine draws;
the run stops on the day a draw is pending and continues, after `scripts/collect_results.py` has
written the `*.decision.result.json`, from the same day. Nothing here draws chance itself.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from runtime import consultations, signing, standing         # noqa: E402
from runtime.decisions import decision_errors                # noqa: E402
from runtime.front_office import rookie_offer                # noqa: E402
from runtime.rookie_contract import layered_errors, layered_terms   # noqa: E402
from runtime.gm import MAX_ROUNDS, FrontOffice               # noqa: E402
from runtime.market import PATIENCE_ROUNDS, Market           # noqa: E402
from runtime.negotiation import FOLDER, Negotiation, slug    # noqa: E402
from runtime.trades import PARTNER_LOCATION, TradeDesk       # noqa: E402
from runtime.valuation import read                           # noqa: E402
from scripts import run_june30                               # noqa: E402
from scripts.refresh_career_views import refresh_career_views # noqa: E402

SEASON = "2003-04"
PHASE = Path(f"career/Dwyane_Wade/{SEASON}/01_Free_Agency")
STATE_FILE = PHASE / "free_agency_state.json"
WINDOW = "2003-fa"
JUNE_30, OPENS, CAP_DAY, SIGNING = "2003-06-30", "2003-07-01", "2003-07-15", "2003-07-16"
PLAN_DAYS = (OPENS, SIGNING)                    # Miami plans when the market opens and again when the cap is published
MAX_ROSTER = 15
RE_SIGN_TO = 13                                 # re-sign own free agents, best first, until the roster reaches this
MORATORIUM_MIN_SCORE = 20.0                     # before the cap is published Miami opens talks only with targets this strong
TRADES = signing.TRADES
ALTERNATIVE_CONTEXT = {}   # the market fills the alternative club's 2002-03 wins and the player's own 2002-03 minutes


def day_after(day):
    from datetime import date, timedelta
    return (date.fromisoformat(day) + timedelta(days=1)).isoformat()


class Run:
    def __init__(self, root=ROOT):
        self.root = Path(root)
        self.writer = signing.Writer(root)
        self.state = read(STATE_FILE, root) if (self.root / STATE_FILE).exists() else {
            "window": WINDOW, "june30_applied": False, "news_through": "2003-06-26", "plans": [], "wade_offer_date": None,
            "standing": None, "standing_as_of": None, "stopped": None}
        self.career = read(signing.STATE, root)
        self.pending, self.awaiting, self.log = [], [], []
        self.standing, self.wade_signed = "unsigned_rookie", None

    # -- records -------------------------------------------------------------------------------
    def negotiations(self):
        folder = self.root / FOLDER
        if not folder.exists():
            return []
        return [Negotiation.load(p, self.root) for p in sorted(folder.glob("*.json"))
                if not (p.name.endswith(".decision.json") or p.name.endswith(".result.json"))]

    def decision(self, packet, folder=FOLDER):
        """Write a decision request once; return its drawn outcome or None (then the run stops on this day)."""
        errors = decision_errors(packet)
        if errors:
            raise ValueError(f"{packet['event_id']}: " + "; ".join(errors))
        folder = self.root / folder
        folder.mkdir(parents=True, exist_ok=True)
        request, result = folder / f"{packet['event_id']}.decision.json", folder / f"{packet['event_id']}.decision.result.json"
        if not request.exists():
            request.write_text(json.dumps(packet, indent=1) + "\n", encoding="utf-8")
        if result.exists():
            return json.loads(result.read_text(encoding="utf-8"))["outcome"]
        self.pending.append(packet["event_id"])
        return None

    def requests(self):
        path = self.root / PHASE / "wade_requests.json"
        return read(path, self.root)["requests"] if path.exists() else []

    def save(self, day, stopped=None):
        self.state["stopped"] = stopped
        self.writer.files[STATE_FILE] = self.state
        signing.set_state(self.writer, day)
        if day >= OPENS:
            self.writer.files[signing.STATE]["contract_status"] = self.writer.files[signing.STATE].get("contract_status", "draft_rights_unsigned")
        written = self.writer.commit()
        if self.wade_signed == day:
            # The sheet's signed_date is on disk first; the snapshot replays from it (runtime/standing.py).
            standing.record(self.root, day, "signing", f"{SEASON}/01_Free_Agency/Wade_Rookie_Contract/negotiation_log.json")
            self.wade_signed = None
        return written

    # -- days ------------------------------------------------------------------------------------
    def advance(self, until):
        day = self.career["current_date"]
        if day < JUNE_30:
            day = JUNE_30
        while day <= until:
            self.pending = []
            stop = self.process(day)
            written = self.save(day, stop)
            self.log.append({"date": day, "pending": list(self.pending), "written": len(written), "stopped": stop})
            if stop:
                return {"date": day, "stopped": stop, "pending": self.pending, "log": self.log}
            day = day_after(day)
        return {"date": until, "stopped": None, "pending": [], "log": self.log}

    def process(self, day):
        if day == JUNE_30 or (day > JUNE_30 and not self.state["june30_applied"]):
            if not self.june30(day):
                return "awaiting the engine's June 30 draws"
        if day < OPENS:
            return None
        snap = standing.standing_on(self.root, day)
        self.standing, self.state["standing"], self.state["standing_as_of"] = snap["standing"], snap["standing"], snap["as_of"]
        self.close_answered_consultations(day)
        self.market = Market(day, self.root)
        self.fo = FrontOffice(day, self.market, self.root)
        if day == OPENS:
            signing.open_market(self.writer, day)
            self.writer.commit()
            self.fo = FrontOffice(day, self.market, self.root)
        self.news(day)
        # A consultation Wade has not answered (asked by this driver or by scripts/run_trade.py) stops the clock:
        # a re-run of the same day finds the same ids, the plan is not made and no other negotiation, draw or
        # signing moves until he answers; nothing asks him a second question meanwhile.
        for cid in consultations.unanswered(self.root, SEASON, day):
            if cid not in self.awaiting:
                self.awaiting.append(cid)
        if not self.awaiting and day in PLAN_DAYS and day not in self.state["plans"]:
            self.plan(day)
        if not self.awaiting:
            for n in self.negotiations():
                self.work(n, day)
        stop = None
        if self.awaiting or self.pending:
            # The clock stops for the whole day loop: every other Miami negotiation, draw and signing waits with it.
            parts = []
            if self.awaiting:
                parts.append("awaiting Wade's answer on: " + ", ".join(self.awaiting))
            if self.pending:
                parts.append("awaiting engine draws: " + ", ".join(self.pending))
            stop = "; ".join(parts)
        elif day >= SIGNING and not self.state["wade_offer_date"] and not any(n.status in ("open", "agreed", "sheet_pending", "trade_pending") for n in self.negotiations()):
            self.wade_offer(day)
            stop = "awaiting Wade's answer to Miami's rookie offer"
        elif self.state["wade_offer_date"]:
            stop = self.wade_answer(day)
        self.refresh_ledger(day)
        return stop

    def refresh_ledger(self, day):
        """Recompute the finance summary and cap sheet whenever the ledger moved since the last summary."""
        finance = self.writer.load(signing.TEAM / "Finances/finance.json")
        moved = max(self.writer.load(signing.TEAM / rel)["as_of"] for rel in ("Finances/contract_schedules.json", "Finances/free_agent_rights.json", "Team/Roster/roster.json"))
        if finance["as_of"] < moved or finance["as_of"] < OPENS <= day:
            self.writer.commit()             # the front office reads the records from disk
            signing.refresh_finance(self.writer, FrontOffice(day, self.market, self.root), day)

    # -- June 30 ---------------------------------------------------------------------------------
    def june30(self, day):
        folder = self.root / PHASE / "June_30"
        package_path = folder / "front_office_decisions.json"
        if not package_path.exists():
            package, draws = run_june30.build(self.root)
            folder.mkdir(parents=True, exist_ok=True)
            package_path.write_text(json.dumps(package, indent=1) + "\n", encoding="utf-8")
            for d in draws:
                (folder / f"{d['event_id']}.decision.json").write_text(json.dumps(d, indent=1) + "\n", encoding="utf-8")
        package = json.loads(package_path.read_text(encoding="utf-8"))
        outcomes = {}
        for request in sorted(folder.glob("*.decision.json")):
            result = request.with_name(request.name.replace(".decision.json", ".decision.result.json"))
            event = json.loads(request.read_text(encoding="utf-8"))["event_id"]
            if result.exists():
                outcomes[event] = json.loads(result.read_text(encoding="utf-8"))["outcome"]
            else:
                self.pending.append(event)
        if self.pending:
            return False
        if not self.state["june30_applied"]:
            signing.apply_june30(self.writer, package, outcomes, JUNE_30)
            self.writer.files[PHASE / "June_30/front_office_decisions.json"] = package
            self.state["june30_applied"] = True
        return True

    # -- the market -------------------------------------------------------------------------------
    def news(self, day):
        """Real moves since the last processed day: close talks with players who signed elsewhere."""
        since = self.state["news_through"]
        if since >= day:
            return
        names = {n.record["bbr_id"]: n for n in self.negotiations()}
        own = {p.get("bbr_id"): p for p in self.fo.rights["players"]}
        for row in self.market.news(since, day):
            n = names.get(row["bbr_id"])
            if n and n.status in ("open",):
                n.end(f"{row['kind'].replace('_', ' ')} with {row['to']} on {row['date']} (real move; Miami had no agreement)", row["date"])
                n.save()
                signing.note_event(self.writer, PHASE / "note.md", row["date"], f"{row['player']} agrees with {row['to']}; Miami's talks end.")
            if row["bbr_id"] in own and row["kind"] in ("signing", "sign_and_trade", "offer_sheet", "match_declined") and not (n and n.status in ("agreed", "sheet_pending", "trade_pending", "signed")):
                signing.depart(self.writer, row["player"], row["date"], "signed_elsewhere", f"signs with {row['to']} ({row['kind'].replace('_', ' ')}, real move); his hold and rights leave Miami's books")
        self.state["news_through"] = day

    def plan(self, day):
        plan = self.fo.plan(self.requests(), self.standing)
        plan["standing"] = {"standing": self.standing, "as_of": self.state["standing_as_of"]}
        folder = self.root / PHASE / "Plans"
        folder.mkdir(parents=True, exist_ok=True)
        self.state["plans"].append(day)
        targets = ", ".join(f"{t['player']} ({t['route']}, ask ${t['ask']:,})" for t in plan["targets"]) or "none"
        signing.note_event(self.writer, PHASE / "note.md", day,
                           f"Front-office plan ({'cap published' if plan['cap_room']['cap_known'] else 'prior cap, projected'}): room ${plan['cap_room']['room']:,} "
                           f"after renouncing when needed {', '.join(r['player'] for r in plan['renounce_when_needed']) or 'nobody'}; targets {targets}. Record: `Plans/plan_{day}.json`.")
        open_names = {n.record["player"] for n in self.negotiations()}
        for t in plan["targets"]:
            if t["player"] in open_names:
                continue
            if day < CAP_DAY and t["score"] < MORATORIUM_MIN_SCORE:
                t["deferred_until_cap_published"] = True
                continue
            kind = "sign_and_trade" if t["route"] == "sign_and_trade" else "free_agent"
            if consultations.consultation_required(self.standing, t["value"]):
                if consultations.objected(self.root, SEASON, t["player"], day):
                    t["consultation"] = "objected"
                    signing.note_event(self.writer, PHASE / "note.md", day, f"{t['player']}: Wade objected to adding him this season; the front office does not pursue him.")
                    continue
                if not consultations.approved(self.root, SEASON, kind, t["player"], day):
                    record = self.ask_consultation(day, kind, t, plan)
                    self.awaiting.append(record["id"])
                    t["consultation"] = "asked"
                    continue
                t["consultation"] = "approved"
            n = Negotiation.open(t["player"], t["bbr_id"], t["club"], day, t, restricted=t["rfa"], root=self.root)
            n.save()
        if day >= SIGNING:
            self.open_re_signings(plan, day, open_names)
        for r in plan["wade_requests"]:
            if r["outcome"] != "pursued":
                signing.note_event(self.writer, PHASE / "note.md", day, f"Wade's request to pursue {r['player']}: {r['outcome']} ({r['reason']}).")
        (folder / f"plan_{day}.json").write_text(json.dumps(plan, indent=1) + "\n", encoding="utf-8")

    def open_re_signings(self, plan, day, open_names):
        """Re-sign talks with own free agents Miami kept rights to, best first, down to a roster of RE_SIGN_TO."""
        active = sum(1 for p in self.fo.roster["players"] if p["status"] in signing.ACTIVE_STATUSES or "draft_rights" in p["status"])
        live = sum(1 for n in self.negotiations() if n.status in ("open", "agreed", "sheet_pending", "trade_pending"))
        spots = RE_SIGN_TO - active - live
        for r in sorted(plan["re_sign_candidates"], key=lambda r: -(r["valuation"] or 0)):
            if spots <= 0:
                break
            bbr = r["bbr_id"]
            if r["player"] in open_names or bbr not in self.market.players:
                continue
            ask = self.market.asking(bbr, day)
            own = self.fo.valuation_of(bbr)
            position = self.fo._positions().get(bbr, "SF")
            role_cap = self.fo.role_ceiling(position)
            if own is None or ask["first_year"] > own * 1.25 or (role_cap is not None and ask["first_year"] > role_cap * 1.1):
                continue
            route = {"larry_bird": "bird"}.get(r["route"], r["route"])
            route_cap = self.fo.route_ceiling(route, bbr)
            if route_cap is not None and ask["first_year"] > route_cap * 1.25:
                continue                     # the route cannot reach his ask; Miami does not open talks it cannot close
            entry = {"bbr_id": bbr, "player": r["player"], "club": "Miami Heat", "position": position,
                     "valuation": own, "ask": ask["first_year"], "years_asked": ask["years"], "route": route, "rfa": False, "score": None}
            Negotiation.open(r["player"], bbr, "Miami Heat", day, entry, restricted=False, root=self.root).save()
            spots -= 1

    # -- one negotiation ------------------------------------------------------------------------
    def work(self, n, day):
        rec, bbr = n.record, n.record["bbr_id"]
        if n.status in ("ended", "signed", "matched"):
            return
        if bbr not in self.market.players:
            n.end("no market record for the player", day)
            n.save()
            return
        if n.status == "open" and not self.market.available(bbr, day) and not rec["agreement"]:
            e = self.market.exit(bbr)
            n.end(f"{e[2]['kind'].replace('_', ' ')} with {e[1]} on {e[0]} (real move)", day)
            n.save()
            return
        if rec["priorities"] is None:
            outcome = self.decision(self.market.trait_packet(bbr, WINDOW))
            if outcome is None:
                return
            rec["priorities"] = {"trait": outcome, "weights": self.market.priorities(outcome)}
        if n.status == "open":
            self.negotiate(n, day)
        if n.status in ("agreed", "trade_pending") and day >= SIGNING:
            self.execute(n, day)
        if n.status == "sheet_pending":
            self.match(n, day)
        n.save()

    def negotiate(self, n, day):
        rec, target, bbr = n.record, n.record["plan"], n.record["bbr_id"]
        last = n.last_round()
        if last and last["answer"] is None:
            outcome = self.decision_for_round(n, last, day)
            if outcome is None or day <= last["date"]:
                return                      # the player answers the day after the offer at the earliest
            if outcome == "walk":                 # a dealbreaker: he ends the talks without a draw
                n.apply_answer("reject", day, f"dealbreaker:{last['decision_event']}")
                n.end(f"walked away: {last['dealbreaker']}", day)
                return
            focus = last.get("counter_focus") or {}
            premium = 0.0 if focus.get("factor") in (None, "money", "security") else focus.get("weighted_deficit", 0) / 100
            n.apply_answer(outcome, day, last["decision_event"], ask=target["ask"], premium=premium)
            last = n.last_round()
            if outcome == "accept":
                return
        round_no = n.round_number()
        counter = last["counter"] if last else None
        if last and last["answer"] == "reject" and round_no > PATIENCE_ROUNDS:
            n.end("rejected Miami's final offer", day)
            return
        if last and last["answer"] == "counter" and round_no > MAX_ROUNDS:
            n.end("no agreement after the last round", day)
            return
        terms = self.fo.offer_terms(dict(target, last_offer=last["terms"]["first_year"] if last else None), round_no, counter,
                                    route=target["route"], restricted=bool(rec["restricted"] and n.outside()))
        if terms is None:
            n.end(f"Miami walks away: the counter of ${counter:,} is above its ceiling" if counter else "Miami walks away", day)
            return
        if last and last["answer"] == "reject" and terms["first_year"] <= last["terms"]["first_year"]:
            n.end("rejected; Miami has nothing more to offer", day)
            return
        p = self.market.players[bbr]
        rnd = n.make_offer(terms, day, target["route"], p.get("nba_seasons_before_2003_04"), p.get("prior_salary_2002_03"))
        rnd["decision_event"] = f"{WINDOW}-{bbr}-offer-{rnd['round']}"
        self.decision_for_round(n, rnd, day)

    def decision_for_round(self, n, rnd, day):
        rec, target, bbr = n.record, n.record["plan"], n.record["bbr_id"]
        offer = {"first_year": rnd["terms"]["first_year"], "years": rnd["terms"]["years"], "guaranteed": rnd["terms"]["guaranteed"]}
        found = self.market.assess(bbr, offer, self.fo.context_for(target), self.market.alternative(bbr, day),
                                   dict(ALTERNATIVE_CONTEXT, ask=target["ask"]), rec["priorities"], WINDOW, rnd["round"])
        rnd["assessment"] = found["analysis"]
        if found["dealbreaker"]:
            rnd["dealbreaker"] = found["dealbreaker"]
            return "walk"
        rnd["counter_focus"] = found["counter_focus"]
        packet = found["packet"]
        packet["event_id"] = rnd["decision_event"]
        packet["date"] = rnd["date"]
        return self.decision(packet)

    def execute(self, n, day):
        rec, target = n.record, n.record["plan"]
        if rec["restricted"] and n.outside():
            if rec["sheet"] is None:
                n.sign_sheet(day)
                signing.note_event(self.writer, PHASE / "note.md", day,
                                   f"{rec['player']} signs Miami's offer sheet; {rec['incumbent']} has until {rec['sheet']['deadline']} to match.")
            return
        if not n.outside() and self.shops(n):
            self.shop_own(n, day)
            return
        if target.get("route") == "sign_and_trade" or rec.get("trade"):
            self.sign_and_trade(n, day)
            return
        if not self.make_room(n, day):
            return
        n.execute_agreement(day)
        signing.sign(self.writer, n, day, cap=self.market.planning_cap(day))

    # -- sign-and-trade ---------------------------------------------------------------------------
    def shops(self, n):
        """Whether the front office shops Miami's own agreed free agent as a sign-and-trade instead of simply
        re-signing him: a proposal already stands, or his rights are full Bird, the route is Bird and his position
        fit is below RESIGN_AND_TRADE_FIT (runtime/gm.py). The front office picks; the user only triggers the day."""
        rec = n.record
        if rec.get("trade") is not None:
            return True
        if rec["status"] != "agreed" or (rec.get("agreement") or {}).get("route") != "bird":
            return False
        rights = next((p for p in self.fo.rights["players"] if p["player"] == rec["player"]), {})
        if rights.get("bird_status") != "larry_bird":
            return False
        position = rec["plan"].get("position") or self.fo._positions().get(rec["bbr_id"], "SF")
        return self.fo.resign_and_trade(rec["bbr_id"], position)

    def shop_own(self, n, day):
        """Miami's own agreed free agent shopped as a sign-and-trade: the proposal, the two draws, and, when no
        partner takes him or either draw declines, his ordinary re-signing on the agreed terms the same day.
        Returns the trade record, or None while the draws or Wade's answer are awaited."""
        record = self.sign_and_trade(n, day)
        if n.status == "agreed" and not self.awaiting:
            if not self.make_room(n, day):
                return record
            n.execute_agreement(day)
            signing.sign(self.writer, n, day, cap=self.market.planning_cap(day))
        return record

    def sign_and_trade(self, n, day):
        """Execute an agreed sign-and-trade: the acquisition of a real club's free agent (the incumbent signs
        and trades him), or Miami's own agreed free agent whom Miami signs and trades in the same transaction
        (`shop_own`; also `scripts/run_trade.py --shop`).

        The packet's basis is built from committed records; the proposal is written once and re-read on a
        re-run; the player's consent (own out only) and the club's answer are engine draws read from their
        result files; both accepting signs the player and applies the trade in one commit, so the player is
        never Miami's signed player before the trade. A decline ends an acquisition's talks and leaves an own
        agreement standing (the negotiation returns to `agreed` for the ordinary re-signing)."""
        rec = n.record
        self.writer.commit()
        fo = FrontOffice(day, self.market, self.root)
        desk = TradeDesk(day, fo, self.root)
        own = not n.outside()
        if rec.get("trade") is None:
            answers = consultations.answers(self.root, SEASON, day)
            proposal, reasons = desk.sign_and_trade_proposal(rec, direction="out" if own else "in", standing=self.standing, consultations=answers)
            if proposal is None:
                if own:
                    signing.note_event(self.writer, PHASE / "note.md", day,
                                       f"The front office shopped {rec['player']} as a sign-and-trade and found no partner ({reasons[0] if reasons else 'no package'}); it re-signs him on the agreed terms.")
                    return None
                n.end("no legal sign-and-trade package: " + "; ".join(reasons[:3]), day)
                return None
            if own and proposal.get("consultation") == "required":
                for name in proposal["consultation_players"]:
                    p = desk.partner_player(proposal["trade"]["partner"], name)
                    record = self.ask_consultation(day, "trade", {"player": name, "bbr_id": p.get("bbr_id"), "club": proposal["trade"]["partner"],
                                                                 "value": desk.assets.valuation.value(p.get("bbr_id")), "ask": desk.assets.salary(p),
                                                                 "position": desk.assets.positions.get(p.get("bbr_id"), (None, "SF", 9))[1].split("-")[0]},
                                                   None, reason=f"arrives in the sign-and-trade of {rec['player']} to {proposal['trade']['partner']}")
                    self.awaiting.append(record["id"])
                return None
            trade_id = desk.trade_id(proposal["trade"])
            rec["trade"] = {"trade_id": trade_id, "decision_event": f"trade-{trade_id}", "kind": "sign_and_trade_out" if own else "sign_and_trade_in",
                            "player_consent_event": f"{WINDOW}-{rec['bbr_id']}-sign-and-trade-{trade_id}" if own else None}
            rec["status"] = "trade_pending"
            n.save()
            consultation = None
            if not own:
                r = consultations.answer_of(self.root, SEASON, rec["player"], day, "sign_and_trade")
                consultation = r["id"] if r else None
            signing.write_proposal(self.root, desk, proposal["trade"], proposal["ranking"], day, kind="sign_and_trade",
                                   negotiation=str(FOLDER / f"{slug(rec['player'])}.json"), standing={"standing": self.standing, "as_of": self.state["standing_as_of"]},
                                   consultation=consultation)
        trade_id = rec["trade"]["trade_id"]
        path = self.root / TRADES / f"{trade_id}.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        if record["status"] != "proposed" or day < record["date"]:
            return record
        if own:
            consent = self.decision(self.consent_packet(n, record, desk, fo, day))
            if consent is None:
                return None
            if consent != "accept":
                return self.close_sign_and_trade(n, record, path, day, "declined", f"{rec['player']} declines the move to {record['trade']['partner']}; Miami re-signs him on the agreed terms")
        result = self.root / TRADES / f"{record['decision_event']}.decision.result.json"
        if not result.exists():
            self.pending.append(record["decision_event"])
            return None
        outcome = json.loads(result.read_text(encoding="utf-8"))["outcome"]
        record["answer"] = {"outcome": outcome, "date": day}
        if outcome != "accept":
            text = (f"{record['trade']['partner']} declines the sign-and-trade of {rec['player']}; Miami re-signs him on the agreed terms" if own
                    else f"{record['trade']['partner']} declines to sign and trade {rec['player']}; Miami's talks end")
            return self.close_sign_and_trade(n, record, path, day, "declined", text)
        n.execute_agreement(day)
        signing.sign(self.writer, n, day, via_trade=record)      # the signing is part of the trade on both sides
        signing.apply_trade(self.writer, record, day)
        record["status"], record["applied"] = "completed", day
        rec["trade"]["outcome"] = "completed"
        path.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        n.save()
        self.writer.commit()
        signing.refresh_finance(self.writer, FrontOffice(day, self.market, self.root), day)
        return record

    def close_sign_and_trade(self, n, record, path, day, status, text):
        rec = n.record
        record["status"] = status
        rec["trade"]["outcome"] = status
        if n.outside():
            n.end(text, day)                       # the acquisition cannot happen without the sign-and-trade
        else:
            rec["status"] = "agreed"               # the own agreement stands: the ordinary re-signing follows (shop_own)
        path.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        signing.note_event(self.writer, PHASE / "note.md", day, text + f" ({record['trade_id']}).")
        return record

    def consent_packet(self, n, record, desk, fo, day):
        """The own sign-and-trade player's consent as a decision packet: his agreed terms at the partner against
        the same terms at Miami (role minutes from the partner's depth at his position, its 2002-03 wins,
        PARTNER_LOCATION), through the market's answer rule; collapsed to accept/reject."""
        rec, target = n.record, n.record["plan"]
        terms = rec["agreement"]["terms"]
        offer = {"first_year": terms["first_year"], "years": terms["years"], "guaranteed": terms["guaranteed"]}
        club, bbr = record["trade"]["partner"], rec["bbr_id"]
        position = desk.assets.positions.get(bbr, (None, target.get("position", "SF"), 9))[1].split("-")[0]
        depth = sum(1 for b, (c, pos, d) in desk.assets.positions.items() if c == club and pos.split("-")[0] == position and d <= 2)
        role_minutes = 32 if depth <= 1 else 20 if depth <= 3 else 12      # the partner's depth at his position (judgement)
        context = {"club": club, "role_minutes": role_minutes, "strength": desk.assets.standings.get(club, {}).get("wins", 41), "location": PARTNER_LOCATION,
                   "ask": terms["first_year"]}
        alternative = {"guaranteed": terms["guaranteed"], "years": terms["years"], "club": "Miami Heat", "basis": "the agreed Miami contract"}
        alt_context = dict(fo.context_for(target), ask=terms["first_year"])
        found = self.market.assess(bbr, offer, context, alternative, alt_context, rec["priorities"], WINDOW, PATIENCE_ROUNDS)
        packet = found["packet"] or {"options": {}, "decider": f"{rec['player']} (simulated player)", "basis": f"dealbreaker at {club}: {found['dealbreaker']}"}
        accept = packet["options"].get("accept", 0.02)
        accept = round(min(0.95, max(0.05, accept)), 3)
        packet.update(event_id=record["player_consent_event"], date=day, options={"accept": accept, "reject": round(1 - accept, 3)},
                      question=f"Does {rec['player']} consent to the sign-and-trade of his Miami contract to {club} ({record['trade_id']})?")
        packet["basis"] = (f"The same agreed contract at {club} (role about {role_minutes} minutes from its depth at {position}, "
                           f"{context['strength']} wins in 2002-03, location {PARTNER_LOCATION}) against it at Miami; " + packet["basis"])
        return packet

    # -- consultations (the user's premise; runtime/consultations.py) ---------------------------------------
    def ask_consultation(self, day, kind, t, plan, reason=None):
        stats = {r["bbr_id"]: r for r in read("library/2003/league/nba_2002_03_player_stats.json", self.root)["records"]}
        line = "no 2002-03 line recorded"
        tot = (stats.get(t.get("bbr_id")) or {}).get("totals")
        if tot and tot.get("games"):
            g = tot["games"]
            line = (f"{g} games, {tot['minutes'] / g:.1f} minutes, {tot['points'] / g:.1f} points, "
                    f"{(tot['offensive_rebounds'] + tot['defensive_rebounds']) / g:.1f} rebounds, {tot['assists'] / g:.1f} assists a game")
        room = self.fo.cap_room()
        evidence = {"value": t.get("value"), "line": line, "salary": f"${t.get('ask', 0):,} (ask or 2003-04 salary)",
                    "cap_position": f"room ${room['room']:,} on the {'published' if room['cap_known'] else 'planning'} cap ${room['cap']:,}",
                    "fit": f"{t.get('position', 'N/A')}: fit {self.fo.fit(t.get('position', 'SF'), self.fo.needs())}",
                    "reason": reason or f"in the front office's plan on {day} (route {t.get('route', kind)}, score {t.get('score', 'N/A')})"}
        state = self.writer.load(signing.STATE)
        record = consultations.ask(self.root, state, day, kind, t["player"], t.get("bbr_id"), t.get("club"), terms=None, trade_id=None,
                                   basis=evidence["reason"], evidence=evidence, season=SEASON,
                                   standing={"standing": self.standing, "as_of": self.state["standing_as_of"]})
        signing.note_event(self.writer, PHASE / "note.md", day,
                           f"Franchise consultation: the front office asks Wade before it adds {t['player']} ({kind}). Record: `Wade_Consultations/{record['id']}.json`.")
        return record

    def close_answered_consultations(self, day):
        """Close answered consultations and resume the plan's targets that waited for them."""
        state = self.writer.load(signing.STATE)
        answered = consultations.close_answered(self.root, state, SEASON)
        for r in answered:
            signing.note_event(self.writer, PHASE / "note.md", r["answered"] or day,
                               f"Wade {'approves' if r['answer'] == 'approve' else 'objects to'} the front office adding {r['player']} ({r['kind']}).")
        if not answered or not self.state["plans"]:
            return
        plan_path = self.root / PHASE / f"Plans/plan_{self.state['plans'][-1]}.json"
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        open_names = {n.record["player"] for n in self.negotiations()}
        changed = False
        for t in plan["targets"]:
            if t.get("consultation") != "asked":
                continue
            kind = "sign_and_trade" if t["route"] == "sign_and_trade" else "free_agent"
            if consultations.objected(self.root, SEASON, t["player"], day):
                t["consultation"], changed = "objected", True
                signing.note_event(self.writer, PHASE / "note.md", day, f"{t['player']}: Wade objected to adding him this season; the front office does not pursue him.")
            elif consultations.approved(self.root, SEASON, kind, t["player"], day):
                t["consultation"], changed = "approved", True
                if t["player"] not in open_names:
                    Negotiation.open(t["player"], t["bbr_id"], t["club"], day, t, restricted=t["rfa"], root=self.root).save()
        if changed:
            plan_path.write_text(json.dumps(plan, indent=1) + "\n", encoding="utf-8")

    def match(self, n, day):
        rec, target = n.record, n.record["plan"]
        if day > rec["sheet"]["deadline"]:
            outcome = "deadline_elapsed"     # no answer inside the window: the sheet stands
        else:
            outcome = self.decision(self.fo.match_packet(target, rec["agreement"]["terms"], WINDOW))
            if outcome is None or day <= rec["sheet"]["signed"]:
                return                      # the incumbent answers the day after service at the earliest
        n.resolve_sheet(outcome, day, f"{WINDOW}-{rec['bbr_id']}-match")
        if outcome == "matched":
            signing.world_effect(self.writer, n, day, outcome)
            n.record["status"] = "matched"
            return
        if self.make_room(n, day):
            signing.sign(self.writer, n, day, cap=self.market.planning_cap(day))
            signing.world_effect(self.writer, n, day, outcome)

    def make_room(self, n, day):
        """Renounce holds the plan allows until the first-year salary fits the route; end the talks if it cannot."""
        rec, target = n.record, n.record["plan"]
        first = rec["agreement"]["terms"]["first_year"]
        fo = FrontOffice(day, self.market, self.root)
        roster_count = sum(1 for p in fo.roster["players"] if p["status"] in signing.ACTIVE_STATUSES or "draft_rights" in p["status"])
        if roster_count >= MAX_ROSTER:
            n.end("no roster spot", day)
            return False
        if target["route"] != "room":
            return True
        plan = read(PHASE / f"Plans/plan_{self.state['plans'][-1]}.json", self.root)
        allowed = [r["player"] for r in plan["renounce_when_needed"]]
        current = fo.cap_room()
        if current["room"] >= first:
            return True
        renounce = []
        for name, hold, _ in fo.holds()[1]:
            if name in allowed and name != rec["player"]:
                renounce.append(name)
                if fo.cap_room(renounce=tuple(renounce))["room"] >= first:
                    break
        if fo.cap_room(renounce=tuple(renounce))["room"] < first:
            n.end(f"no cap room for ${first:,} in 2003-04 (room ${current['room']:,} after allowed renouncements ${fo.cap_room(renounce=tuple(renounce))['room']:,})", day)
            return False
        signing.renounce(self.writer, renounce, day, f"to clear room for {rec['player']}")
        self.writer.commit()
        return True

    # -- Wade ---------------------------------------------------------------------------------
    def wade_offer(self, day):
        log = self.root / PHASE / "Wade_Rookie_Contract/negotiation_log.json"
        if log.exists():
            self.state["wade_offer_date"] = day
            return
        offer = rookie_offer(5)
        roles = [self.fo.role_for(pos) for pos in ("SG", "PG")]
        role = max(roles + [{"role": "rotation", "minutes_per_game": 20}], key=lambda r: r["minutes_per_game"])   # a top-ten pick is promised a rotation role at least
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(json.dumps({
            "player": "Dwyane Wade", "team": "Miami Heat", "pick": 5,
            "agreement": "1999 CBA rookie scale (library/2003/league/nba_1999_cba_rules.json)",
            "entries": [{"date": day, "party": "miami", "action": "offer", "terms": offer["terms"], "promise": role,
                         "note": f"{offer['reason']}. Offered after Miami's July free-agent moves; the role promise is the better of his two positions on the depth chart on {day}, and at least a rotation role for a top-ten pick."}],
        }, indent=1) + "\n", encoding="utf-8")
        self.state["wade_offer_date"] = day
        self.submit_standing_counter(json.loads(log.read_text(encoding="utf-8")), day)
        signing.note_event(self.writer, PHASE / "note.md", day,
                           f"Miami offers Wade his rookie-scale contract at {offer['terms']['percent_of_scale']}% of scale with a promised role of "
                           f"{role['role']} ({role['minutes_per_game']} minutes). Wade answers in `Wade_Rookie_Contract/negotiation_log.json`. "
                           "[Open the detailed negotiation](../../Milestones/index.html#contract_negotiation).")
        state = self.writer.load(signing.STATE)
        state["pending_player_decisions"] = ["rookie_contract_offer"]

    def standing_instruction(self):
        path = self.root / PHASE / "Wade_Rookie_Contract/standing_instruction.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def submit_standing_counter(self, log, day):
        """Wade's pre-registered counter (the user's standing instruction) goes in the day Miami offers."""
        inst = self.standing_instruction()
        if not inst or not inst.get("counter"):
            return False
        c = inst["counter"]
        terms = layered_terms(c["pick"], c["protected_percent"], c["incentives"], self.root)
        log["entries"].append({"date": day, "party": "wade", "action": "counter", "terms": terms,
                               "note": c.get("note", "standing instruction"), "source": "Wade_Rookie_Contract/standing_instruction.json"})
        log_path = self.root / PHASE / "Wade_Rookie_Contract/negotiation_log.json"
        log_path.write_text(json.dumps(log, indent=1) + "\n", encoding="utf-8")
        return True

    def first_signing_day(self):
        return next(e["date"] for e in read("library/2003/league/nba_2003_04_calendar.json", self.root)["events"] if e["id"] == "first_signing_day")

    def wade_answer(self, day):
        """Read Wade's answer in the rookie log: an acceptance is signed the next legal day; a counter gets Miami's answer."""
        log_path = self.root / PHASE / "Wade_Rookie_Contract/negotiation_log.json"
        log = json.loads(log_path.read_text(encoding="utf-8"))
        entries = log["entries"]
        last = entries[-1]
        if last["action"] == "sign":
            return None
        if last["party"] == "miami" and last["action"] == "answer" and last.get("agreed"):
            inst = self.standing_instruction()
            if inst and inst.get("on_agreement") == "accept" and last["date"] <= day:
                entries.append({"date": day, "party": "wade", "action": "accept", "terms": last["terms"],
                                "note": "Accepts Miami's agreement to the counter (standing instruction).", "source": "Wade_Rookie_Contract/standing_instruction.json"})
                log_path.write_text(json.dumps(log, indent=1) + "\n", encoding="utf-8")
                last = entries[-1]
            else:
                return "awaiting Wade's acceptance of the agreed rookie terms"
        if last["party"] == "miami":
            return "awaiting Wade's answer to Miami's rookie offer"
        if last["date"] >= day:
            return "awaiting Wade's answer to Miami's rookie offer" if last["date"] > day else None
        if last["action"] == "accept":
            if day < self.first_signing_day():
                return f"rookie contract agreed; execution waits for the first legal signing day {self.first_signing_day()} (calendar)"
            terms = last.get("terms") or next(e["terms"] for e in reversed(entries) if e["party"] == "miami" and e.get("terms"))
            signing.sign_rookie(self.writer, log, terms, day)
            self.writer.files[PHASE / "Wade_Rookie_Contract/negotiation_log.json"] = log
            self.wade_signed = day
            return None
        if last["action"] == "counter" and last["terms"].get("structure") == "layered":
            # Miami's rule: a legal counter whose ceiling is within its offer and whose protected floor is lower is accepted.
            errors = layered_errors(last["terms"], self.root)
            offered = next(e["terms"]["percent_of_scale"] for e in reversed(entries) if e["party"] == "miami" and e.get("terms") and "percent_of_scale" in e["terms"])
            if not errors and last["terms"]["total_percent"] <= offered:
                entries.append({"date": day, "party": "miami", "action": "answer", "terms": last["terms"], "agreed": True,
                                "note": (f"Agreed: {last['terms']['protected_percent']}% protected with incentives to {last['terms']['total_percent']}% is legal "
                                         f"and within the {offered}% Miami offered; the counted Salary is protected cash plus included incentives. "
                                         "Miami's stated role remains a basketball representation, not a contract term.")})
                inst = self.standing_instruction()
                if inst and inst.get("on_agreement") == "accept":
                    entries.append({"date": day, "party": "wade", "action": "accept", "terms": last["terms"],
                                    "note": "Accepts Miami's agreement to the counter (standing instruction).", "source": "Wade_Rookie_Contract/standing_instruction.json"})
                    self.writer.files[PHASE / "Wade_Rookie_Contract/negotiation_log.json"] = log
                    return None                     # the contract executes on the next legal day
            else:
                entries.append({"date": day, "party": "miami", "action": "answer", "terms": rookie_offer(5)["terms"],
                                "note": "Declined: " + ("; ".join(errors) if errors else f"ceiling above the {offered}% offered") + "; the 120% offer stands."})
            self.writer.files[PHASE / "Wade_Rookie_Contract/negotiation_log.json"] = log
            return "awaiting Wade's answer to Miami's rookie offer"
        if last["action"] == "counter":
            wanted = last["terms"]["percent_of_scale"]
            offered = next(e["terms"]["percent_of_scale"] for e in reversed(entries) if e["party"] == "miami" and e.get("terms") and "percent_of_scale" in e["terms"])
            if wanted <= offered:
                entries.append({"date": day, "party": "miami", "action": "answer", "terms": last["terms"],
                                "note": "Accepted: the counter is inside what Miami offered."})
            else:
                entries.append({"date": day, "party": "miami", "action": "answer", "terms": rookie_offer(5)["terms"],
                                "note": f"Declined: {wanted}% of scale is above the 120% ceiling the rules allow; the 120% offer stands."})
            self.writer.files[PHASE / "Wade_Rookie_Contract/negotiation_log.json"] = log
            return "awaiting Wade's answer to Miami's rookie offer"
        if last["action"] in ("decline", "request"):
            return "awaiting Wade: " + last.get("note", last["action"])
        return None


def local_draw(store, root):
    """Test helper only: draw pending decisions with a local Store and write result files the way the collector does."""
    from runtime.private_service import play_requests
    play_requests(store, root)
    for request in sorted((Path(root) / "career").rglob("*.decision.json")):
        result = request.with_name(request.name.replace(".decision.json", ".decision.result.json"))
        event = json.loads(request.read_text(encoding="utf-8"))["event_id"]
        if not result.exists() and store.result(event) is not None:
            result.write_text(json.dumps(store.result(event), indent=1) + "\n", encoding="utf-8")


def main(argv):
    if len(argv) != 3 or argv[1] not in ("--plan", "--write"):
        raise SystemExit(__doc__)
    day = argv[2]
    if argv[1] == "--plan":
        market = Market(day)
        fo = FrontOffice(day, market)
        requests = read(PHASE / "wade_requests.json")["requests"] if (ROOT / PHASE / "wade_requests.json").exists() else []
        print(json.dumps(fo.plan(requests, standing.standing_on(ROOT, day)["standing"]), indent=1))
        return
    report = Run().advance(day)
    refreshed = refresh_career_views(ROOT)
    for row in report["log"]:
        print(f"{row['date']}: {row['written']} files written" + (f"; pending {row['pending']}" if row["pending"] else "") + (f"; stopped: {row['stopped']}" if row["stopped"] else ""))
    if report["stopped"]:
        print(f"Stopped on {report['date']}: {report['stopped']}")
    print(f"Updated {len(refreshed)} detailed career views; open career/Dwyane_Wade/Milestones/index.html.")


if __name__ == "__main__":
    main(sys.argv)
