#!/usr/bin/env python3
"""Advance Miami's 2003 offseason day by day: June 30 decisions, the free-agency plan, offers,
the players' drawn answers, signings, and Wade's rookie offer (docs/front_office.md).

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
from runtime import signing                                  # noqa: E402
from runtime.decisions import decision_errors                # noqa: E402
from runtime.front_office import rookie_offer                # noqa: E402
from runtime.gm import MAX_ROUNDS, FrontOffice               # noqa: E402
from runtime.market import PATIENCE_ROUNDS, Market           # noqa: E402
from runtime.negotiation import FOLDER, Negotiation, slug    # noqa: E402
from runtime.valuation import read                           # noqa: E402
from scripts import run_june30                               # noqa: E402

SEASON = "2003-04"
PHASE = Path(f"career/Dwyane_Wade/{SEASON}/01_Free_Agency")
STATE_FILE = PHASE / "free_agency_state.json"
WINDOW = "2003-fa"
JUNE_30, OPENS, CAP_DAY, SIGNING = "2003-06-30", "2003-07-01", "2003-07-15", "2003-07-16"
PLAN_DAYS = (OPENS, SIGNING)                    # Miami plans when the market opens and again when the cap is published
MAX_ROSTER = 15
RE_SIGN_TO = 13                                 # re-sign own free agents, best first, until the roster reaches this
MORATORIUM_MIN_SCORE = 20.0                     # before the cap is published Miami opens talks only with targets this strong
STANDING = "unsigned_rookie"
ALTERNATIVE_CONTEXT = {"role_minutes": 28, "strength": 41, "location": 0.5}   # judgement: an average situation elsewhere


def day_after(day):
    from datetime import date, timedelta
    return (date.fromisoformat(day) + timedelta(days=1)).isoformat()


class Run:
    def __init__(self, root=ROOT):
        self.root = Path(root)
        self.writer = signing.Writer(root)
        self.state = read(STATE_FILE, root) if (self.root / STATE_FILE).exists() else {
            "window": WINDOW, "june30_applied": False, "news_through": "2003-06-26", "plans": [], "wade_offer_date": None,
            "standing": STANDING, "stopped": None}
        self.career = read(signing.STATE, root)
        self.pending, self.log = [], []

    # -- records -------------------------------------------------------------------------------
    def negotiations(self):
        folder = self.root / FOLDER
        if not folder.exists():
            return []
        return [Negotiation.load(p, self.root) for p in sorted(folder.glob("*.json"))
                if not (p.name.endswith(".decision.json") or p.name.endswith(".result.json"))]

    def decision(self, packet):
        """Write a decision request once; return its drawn outcome or None (then the run stops on this day)."""
        errors = decision_errors(packet)
        if errors:
            raise ValueError(f"{packet['event_id']}: " + "; ".join(errors))
        folder = self.root / FOLDER
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
        return self.writer.commit()

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
        self.market = Market(day, self.root)
        self.fo = FrontOffice(day, self.market, self.root)
        if day == OPENS:
            signing.open_market(self.writer, day)
            self.writer.commit()
            self.fo = FrontOffice(day, self.market, self.root)
        self.news(day)
        if day in PLAN_DAYS and day not in self.state["plans"]:
            self.plan(day)
        for n in self.negotiations():
            self.work(n, day)
        stop = None
        if self.pending:
            stop = "awaiting engine draws: " + ", ".join(self.pending)
        elif day >= SIGNING and not self.state["wade_offer_date"] and not any(n.status in ("open", "agreed", "sheet_pending") for n in self.negotiations()):
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
            if row["bbr_id"] in own and row["kind"] in ("signing", "sign_and_trade", "offer_sheet", "match_declined") and not (n and n.status in ("agreed", "sheet_pending", "signed")):
                signing.depart(self.writer, row["player"], row["date"], "signed_elsewhere", f"signs with {row['to']} ({row['kind'].replace('_', ' ')}, real move); his hold and rights leave Miami's books")
        self.state["news_through"] = day

    def plan(self, day):
        plan = self.fo.plan(self.requests(), self.state["standing"])
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
        live = sum(1 for n in self.negotiations() if n.status in ("open", "agreed", "sheet_pending"))
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
        if n.status == "agreed" and day >= SIGNING:
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
            n.apply_answer(outcome, day, last["decision_event"], ask=target["ask"])
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
        packet = self.market.answer_packet(bbr, offer, self.fo.context_for(target), self.market.alternative(bbr, day),
                                           dict(ALTERNATIVE_CONTEXT, ask=target["ask"]), rec["priorities"]["weights"], WINDOW, rnd["round"])
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
        if not self.make_room(n, day):
            return
        n.execute_agreement(day)
        signing.sign(self.writer, n, day)

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
            signing.sign(self.writer, n, day)
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
        signing.note_event(self.writer, PHASE / "note.md", day,
                           f"Miami offers Wade his rookie-scale contract at {offer['terms']['percent_of_scale']}% of scale with a promised role of "
                           f"{role['role']} ({role['minutes_per_game']} minutes). Wade answers in `Wade_Rookie_Contract/negotiation_log.json`.")
        state = self.writer.load(signing.STATE)
        state["pending_player_decisions"] = ["rookie_contract_offer"]

    def wade_answer(self, day):
        """Read Wade's answer in the rookie log: an acceptance is signed the next day; a counter gets Miami's answer."""
        log_path = self.root / PHASE / "Wade_Rookie_Contract/negotiation_log.json"
        log = json.loads(log_path.read_text(encoding="utf-8"))
        entries = log["entries"]
        last = entries[-1]
        if last["action"] == "sign":
            return None
        if last["party"] == "miami":
            return "awaiting Wade's answer to Miami's rookie offer"
        if last["date"] >= day:
            return "awaiting Wade's answer to Miami's rookie offer" if last["date"] > day else None
        if last["action"] == "accept":
            terms = last.get("terms") or next(e["terms"] for e in reversed(entries) if e["party"] == "miami" and e.get("terms"))
            signing.sign_rookie(self.writer, log, terms, day)
            self.writer.files[PHASE / "Wade_Rookie_Contract/negotiation_log.json"] = log
            return None
        if last["action"] == "counter":
            wanted = last["terms"]["percent_of_scale"]
            offered = next(e["terms"]["percent_of_scale"] for e in reversed(entries) if e["party"] == "miami" and e.get("terms"))
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
        print(json.dumps(fo.plan(requests, STANDING), indent=1))
        return
    report = Run().advance(day)
    for row in report["log"]:
        print(f"{row['date']}: {row['written']} files written" + (f"; pending {row['pending']}" if row["pending"] else "") + (f"; stopped: {row['stopped']}" if row["stopped"] else ""))
    if report["stopped"]:
        print(f"Stopped on {report['date']}: {report['stopped']}")


if __name__ == "__main__":
    main(sys.argv)
