import json
import shutil
import tempfile
import unittest
from pathlib import Path

from runtime import contract_negotiation as desk
from runtime.decisions import decision_errors
from runtime.gm import FrontOffice, MAX_ROUNDS
from runtime.market import Market
from runtime.negotiation import Negotiation, STATUSES, negotiation_errors
from runtime.private_service import Store
from runtime.rotations import holdings_errors
from runtime.signing import ledger_errors, trade_record_errors
from runtime.standing import standing_errors, standing_on
from runtime.valuation import Valuation, age_factor, production_value
from scripts.run_free_agency import Run, local_draw
from scripts.validate_repository import rights_errors

ROOT = Path(__file__).resolve().parents[1]
REQUEST = [{"date": "2003-06-26", "subject": "free_agent_target", "player": "Andre Miller", "requested": "pursue"}]


def copy_repo():
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    shutil.copytree(ROOT / "library", root / "library")
    shutil.copytree(ROOT / "career", root / "career")
    return tmp, root


class ValuationTests(unittest.TestCase):
    def test_price_stays_inside_the_player_bounds(self):
        v = Valuation("2003-07-16")
        for bbr in ("millean02", "mournal01", "alstora01", "paytoga01"):
            price = v.price(bbr)
            if price is not None:
                self.assertGreaterEqual(price, v.minimum(v.service.get(bbr)))
                self.assertLessEqual(price, v.maximum(v.service.get(bbr)))
        self.assertIsNone(v.price("mournal01"))          # no 2002-03 minutes: no production evidence

    def test_age_and_minutes_shape_the_value(self):
        totals = {"games": 80, "minutes": 2800, "points": 1300, "offensive_rebounds": 60, "defensive_rebounds": 200, "assists": 500,
                  "steals": 100, "blocks": 10, "field_goals_attempted": 1000, "field_goals_made": 450, "free_throws_attempted": 400,
                  "free_throws_made": 320, "turnovers": 200}
        self.assertGreater(production_value(totals, 25), production_value(totals, 33))
        fewer = {k: (v // 8 if k != "games" else 10) for k, v in totals.items()}       # the same per-game line in 350 minutes
        self.assertGreater(production_value(totals, 25), production_value(fewer, 25))
        self.assertGreater(age_factor(24), age_factor(36))


class MarketTests(unittest.TestCase):
    def test_real_miami_signings_are_skipped_and_exits_dated(self):
        m = Market("2003-07-01")
        self.assertTrue(m.available("alstora01", "2003-09-03"))          # Alston's real move was to Miami: never applied;
        self.assertEqual(m.exit("alstora01")[:2], ("2003-09-04", "Toronto Raptors"))   # he goes back to his last club that day
        self.assertEqual(m.exit("mournal01")[:2], ("2003-07-16", "New Jersey Nets"))
        self.assertFalse(m.available("mournal01", "2003-07-16"))
        self.assertTrue(m.available("mournal01", "2003-07-15"))

    def test_asking_and_answers(self):
        m = Market("2003-07-16")
        ask = m.asking("millean02")
        self.assertTrue(ask["minimum"] <= ask["first_year"] <= ask["maximum"])
        self.assertEqual(ask["years"], 4)                                     # age 27: four seasons wanted
        priorities = m.priorities("money")
        context = {"role_minutes": 32, "strength": 30, "location": 0.6, "ask": ask["first_year"]}
        alt = m.alternative("millean02")
        packet = m.answer_packet("millean02", {"first_year": ask["first_year"], "years": 4, "guaranteed": ask["first_year"] * 4},
                                 context, alt, dict(context, location=0.5), priorities, "t", 1)
        self.assertEqual(decision_errors(packet), [])
        insult = m.answer_packet("millean02", {"first_year": ask["first_year"] // 2, "years": 1, "guaranteed": ask["first_year"] // 2},
                                 context, alt, dict(context, location=0.5), priorities, "t", 3)
        self.assertEqual(insult["options"]["accept"], 0.02)
        self.assertEqual(decision_errors(m.trait_packet("millean02", "t")), [])


class FrontOfficeTests(unittest.TestCase):
    def setUp(self):
        self.market = Market("2003-07-16")
        self.fo = FrontOffice("2003-07-16", self.market)

    def test_plan_weighs_wade_request_and_keeps_room_nonnegative(self):
        plan = self.fo.plan(REQUEST)
        self.assertGreaterEqual(plan["room_after_targets"], 0)
        miller = next(t for t in self.fo.targets(REQUEST, limit=50) if t["player"] == "Andre Miller")
        self.assertTrue(miller["wade_request"])
        self.assertEqual(plan["wade_requests"][0]["player"], "Andre Miller")
        self.assertIn("Alonzo Mourning", [r["player"] for r in plan["renounce_when_needed"]])
        for t in plan["targets"]:
            self.assertIn(t["route"], ("room", "mid_level", "sign_and_trade"))
            if t["route"] == "sign_and_trade":
                self.assertTrue(t["sign_and_trade_feasible"])
        self.assertIn("sign_and_trade_probes", plan)
        self.assertLessEqual(sum(1 for t in plan["targets"] if t["route"] == "sign_and_trade"), 1)

    def test_offers_follow_the_policy(self):
        t = next(t for t in self.fo.targets(REQUEST, limit=50) if t["player"] == "Andre Miller")
        first = self.fo.offer_terms(t, 1, restricted=True)
        self.assertLessEqual(first["first_year"], t["valuation"])
        self.assertGreaterEqual(first["years"], 3)
        self.assertEqual(len(first["schedule"]), first["years"])
        self.assertIsNone(self.fo.offer_terms(t, 2, counter=int(t["valuation"] * 1.5)))
        self.assertIsNone(self.fo.offer_terms(t, MAX_ROUNDS + 1))
        mle = self.fo.offer_terms(dict(t, ask=9000000, valuation=9000000), 1, route="mid_level")
        self.assertLessEqual(mle["first_year"], self.fo.valuation.mid_level)
        packet = self.fo.match_packet(t, first, "t")
        self.assertEqual(decision_errors(packet), [])


class NegotiationAdapterTests(unittest.TestCase):
    def test_unrestricted_flow_executes_on_the_signing_date(self):
        n = Negotiation.open("Gary Payton", "paytoga01", "Milwaukee Bucks", "2003-07-02", {"ask": 1})
        terms = {"first_year": 4917000, "years": 2, "schedule": [4917000, 5408700], "guaranteed": 10325700, "raise_percent": 10.0,
                 "last_year_guaranteed": True, "round": 1}
        n.make_offer(terms, "2003-07-02", "mid_level", 12, 12000000)
        with self.assertRaises(desk.NegotiationError):
            n.apply_answer("counter", "2003-07-01", "e", ask=5000000)      # before the offer: the desk refuses
        n.record["rounds"][-1].update(answer=None, counter=None)
        n.apply_answer("accept", "2003-07-03", "t-offer-1")
        self.assertEqual(n.status, "agreed")
        n.execute_agreement("2003-07-16")
        self.assertEqual(n.state.phase, "execution_pending")
        self.assertEqual(n.state.resolution.outcome, "agreement")

    def test_restricted_flow_uses_the_sheet_and_slot_five(self):
        n = Negotiation.open("Andre Miller", "millean02", "Los Angeles Clippers", "2003-07-02", {"ask": 5780236}, restricted=True)
        terms = {"first_year": 5800000, "years": 4, "schedule": [5800000, 6380000, 6960000, 7540000], "guaranteed": 26680000,
                 "raise_percent": 10.0, "last_year_guaranteed": True, "round": 1}
        n.make_offer(terms, "2003-07-02", "room", 4, 2460709)
        n.apply_answer("counter", "2003-07-03", "t-offer-1", ask=5780236)
        self.assertIsNotNone(n.last_round()["counter"])
        n.make_offer(dict(terms, round=2), "2003-07-05", "room", 4, 2460709)
        n.apply_answer("accept", "2003-07-06", "t-offer-2")
        n.sign_sheet("2003-07-16")
        self.assertEqual(n.record["sheet"]["deadline"], "2003-07-31")
        n.resolve_sheet("matched", "2003-07-20", "t-match")
        self.assertEqual(n.status, "matched")
        self.assertEqual(n.state.resolution.slot, 5)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = n.save(tmp.name)
        self.assertEqual(Negotiation.load(path).state.phase, n.state.phase)

    def test_illegal_offers_are_refused_before_the_desk(self):
        n = Negotiation.open("Andre Miller", "millean02", "Los Angeles Clippers", "2003-07-02", {"ask": 1}, restricted=True)
        with self.assertRaises(ValueError):
            n.make_offer({"first_year": 5000000, "years": 2, "schedule": [5000000, 5500000], "guaranteed": 10500000,
                          "raise_percent": 10.0, "last_year_guaranteed": True, "round": 1}, "2003-07-02", "room", 4, 2460709)
        self.assertEqual(n.record["rounds"], [])


class DriverTests(unittest.TestCase):
    def test_free_agency_advances_through_drawn_decisions(self):
        tmp, root = copy_repo()
        self.addCleanup(tmp.cleanup)
        store = Store(root / "data/e.sqlite3")
        store.initialize()
        report = Run(root).advance("2003-07-25")
        self.assertEqual(report["date"], "2003-06-30")
        self.assertIn("June 30", report["stopped"])
        self.assertTrue((root / "career/Dwyane_Wade/2003-04/01_Free_Agency/June_30/front_office_decisions.json").exists())
        for _ in range(40):
            local_draw(store, root)
            report = Run(root).advance("2003-07-25")
            if not report["stopped"] or "Wade" in report["stopped"]:
                break
        self.assertTrue(not report["stopped"] or "Wade" in report["stopped"], report)
        state = json.loads((root / "career/Dwyane_Wade/2003-04/01_Free_Agency/free_agency_state.json").read_text())
        self.assertTrue(state["june30_applied"])
        self.assertEqual(state["plans"], ["2003-07-01", "2003-07-16"])
        note = (root / "career/Dwyane_Wade/2003-04/01_Free_Agency/note.md").read_text()
        self.assertIn("Front-office plan", note)
        self.assertIn("Wade's request to pursue Andre Miller", note + "pursued")
        folder = root / "career/Dwyane_Wade/2003-04/01_Free_Agency/Negotiations"
        records = [json.loads(p.read_text()) for p in folder.glob("*.json") if ".decision" not in p.name] if folder.exists() else []
        plan = json.loads((root / "career/Dwyane_Wade/2003-04/01_Free_Agency/Plans/plan_2003-07-16.json").read_text())
        self.assertGreaterEqual(plan["room_after_targets"], min(0, plan["cap_room"]["room"]))
        for t in plan["targets"]:                       # every chosen target was talked to (the draws decide the rest)
            self.assertIn(t["player"], [r["player"] for r in records])
        for r in records:
            self.assertIn(r["status"], STATUSES)
            for rnd in r["rounds"]:
                self.assertEqual(rnd["legality"]["errors"], [])
        self.assertEqual(negotiation_errors(root), [])
        self.assertEqual(ledger_errors(root), [])
        self.assertEqual(holdings_errors(root), [])
        self.assertEqual(trade_record_errors(root), [])
        self.assertEqual(rights_errors(root), [])                    # the rights check tolerates the drivers' state after June 30
        self.assertEqual(standing_errors(root), [])
        self.assertFalse((root / "career/Dwyane_Wade/2003-04/Wade_Consultations").exists())   # no gate below franchise standing
        self.assertEqual(state["standing"], "unsigned_rookie")
        career = json.loads((root / "career/Dwyane_Wade/2003-04/current_state.json").read_text())
        self.assertGreaterEqual(career["current_date"], "2003-07-16")
        # Re-running the same day writes no new decision request: the run is idempotent.
        before = sorted(p.name for p in folder.glob("*.decision.json"))
        Run(root).advance(career["current_date"])
        self.assertEqual(sorted(p.name for p in folder.glob("*.decision.json")), before)
        roster = json.loads((root / "career/Dwyane_Wade/2003-04/00_Team/Team/Roster/roster.json").read_text())
        statuses = {p["name"]: p["status"] for p in roster["players"]}
        self.assertEqual(statuses["Alonzo Mourning"], "signed_elsewhere")      # his real July 16 move to New Jersey
        self.assertNotIn("expiring", " ".join(statuses.values()))
        # Wade accepts: the next day's run signs him and the records agree.
        if "Wade" in (report["stopped"] or ""):
            log_path = root / "career/Dwyane_Wade/2003-04/01_Free_Agency/Wade_Rookie_Contract/negotiation_log.json"
            log = json.loads(log_path.read_text())
            offer = next(e for e in log["entries"] if e["action"] == "offer")
            self.assertIn(offer["promise"]["role"], ("rotation", "starter"))   # never a reserve for a top-ten pick
            self.assertGreaterEqual(offer["promise"]["minutes_per_game"], 20)
            self.assertEqual(log["entries"][-1]["action"], "counter")          # Wade's standing counter goes in the same day
            report = Run(root).advance("2003-07-31")                           # Miami agrees, Wade accepts, the contract executes
            self.assertIsNone(report["stopped"], report)
            log = json.loads(log_path.read_text())
            self.assertEqual([e["action"] for e in log["entries"][-3:]], ["answer", "accept", "sign"])
            sheet = json.loads((root / "career/Dwyane_Wade/2003-04/00_Team/Finances/contract_schedules.json").read_text())
            wade = next(p for p in sheet["players"] if p["player"] == "Dwyane Wade")
            self.assertEqual(wade["status"], "under_contract")
            self.assertEqual(wade["schedule"]["2003-04"], 2197000)              # counted Salary: 80% protected plus 20% included incentives
            state = json.loads((root / "career/Dwyane_Wade/2003-04/current_state.json").read_text())
            self.assertEqual(state["contract_status"], "rookie_scale_contract")
            self.assertEqual(state["pending_player_decisions"], [])
            self.assertEqual(ledger_errors(root), [])
            self.assertEqual(holdings_errors(root), [])
            # the signing dated a standing snapshot from the sheet, and it replays
            snapshots = json.loads((root / "career/Dwyane_Wade/standing.json").read_text())["snapshots"]
            self.assertEqual((snapshots[-1]["standing"], snapshots[-1]["trigger"]), ("rookie", "signing"))
            self.assertEqual(standing_errors(root), [])
            self.assertEqual(standing_on(root, "2003-07-31")["standing"], "rookie")
            self.assertEqual(rights_errors(root), [])
            self.assertEqual(trade_record_errors(root), [])
            self.assertEqual(negotiation_errors(root), [])


if __name__ == "__main__":
    unittest.main()


class RookieCounterTests(unittest.TestCase):
    def test_layered_counter_reproduces_the_user_table_and_passes_the_rules(self):
        from runtime.rookie_contract import layered_errors, layered_terms, log_errors
        inst = json.loads((ROOT / "career/Dwyane_Wade/2003-04/01_Free_Agency/Wade_Rookie_Contract/standing_instruction.json").read_text())
        c = inst["counter"]
        terms = layered_terms(c["pick"], c["protected_percent"], c["incentives"])
        self.assertEqual(terms["protected_schedule"]["2003-04"], 1757600)
        self.assertEqual(terms["schedule"]["2003-04"], 2197000)              # counted: protected plus included incentives
        self.assertEqual(terms["maximum_schedule"]["2003-04"], 2636400)
        self.assertEqual(terms["schedule"]["2006-07"], round(2526600 * 1.267))
        self.assertEqual(layered_errors(terms), [])
        self.assertEqual(log_errors({"entries": [{"date": "2003-07-20", "party": "wade", "action": "counter", "terms": terms}]}), [])
        too_rich = layered_terms(5, 80, c["incentives"] + [{"id": "x", "label": "x", "kind": "performance", "percent": 5, "benchmarks": {s: "y" for s in ("2003-04", "2004-05", "2005-06")}}])
        self.assertTrue(any("Unlikely" in e or "120%" in e for e in layered_errors(too_rich)))
        self.assertTrue(layered_errors(layered_terms(5, 70, c["incentives"][:2])))

    def test_driver_submits_the_counter_agrees_and_signs_on_a_legal_day(self):
        tmp, root = copy_repo()
        self.addCleanup(tmp.cleanup)
        run = Run(root)
        run.market = Market("2003-07-18", root)
        run.fo = FrontOffice("2003-07-18", run.market, root)
        run.wade_offer("2003-07-18")
        run.writer.commit()
        log_path = root / "career/Dwyane_Wade/2003-04/01_Free_Agency/Wade_Rookie_Contract/negotiation_log.json"
        log = json.loads(log_path.read_text())
        self.assertEqual([e["action"] for e in log["entries"]], ["offer", "counter"])
        self.assertEqual(log["entries"][1]["terms"]["structure"], "layered")
        run1 = Run(root)
        run1.wade_answer("2003-07-19")
        run1.writer.commit()
        log = json.loads(log_path.read_text())
        self.assertEqual([e["action"] for e in log["entries"][-2:]], ["answer", "accept"])
        self.assertTrue(log["entries"][-2].get("agreed"))
        run2 = Run(root)
        self.assertIsNone(run2.wade_answer("2003-07-20"))
        run2.writer.commit()
        log = json.loads(log_path.read_text())
        self.assertEqual(log["entries"][-1]["action"], "sign")
        sheet = json.loads((root / "career/Dwyane_Wade/2003-04/00_Team/Finances/contract_schedules.json").read_text())
        wade = next(p for p in sheet["players"] if p["player"] == "Dwyane Wade")
        self.assertEqual(wade["schedule"]["2003-04"], 2197000)
        self.assertEqual(wade["protected_schedule"]["2003-04"], 1757600)
        self.assertEqual(wade["percent_of_scale"], 120)
