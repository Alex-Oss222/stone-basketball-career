"""Sign-and-trade under the 1999 rules (runtime/trades.py, runtime/cba.py, runtime/signing.py, the drivers)."""
import json
import shutil
import tempfile
import unittest

from tests import checkpoint
from pathlib import Path
from unittest import mock

from runtime import gm, signing, trades
from runtime.cba import terms_errors
from runtime.decisions import decision_errors
from runtime.gm import FrontOffice
from runtime.market import Market
from runtime.negotiation import FOLDER, Negotiation, negotiation_errors
from runtime.private_service import Store
from runtime.rotations import holdings_errors, miami_departed, miami_departures
from runtime.signing import ledger_errors, trade_record_errors
from runtime.trades import SIGN_AND_TRADE_RIGHTS, TradeDesk
from runtime.valuation import read
from scripts import run_trade
from scripts.run_free_agency import WINDOW, Run, local_draw

ROOT = Path(__file__).resolve().parents[1]
SEASON_DIR = Path("career/Dwyane_Wade/2003-04")
TRADES = SEASON_DIR / "00_Team/Transactions/Trades"
DAY = "2003-07-20"


def copy_repo(open_market=True):
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    shutil.copytree(ROOT / "library", root / "library")
    shutil.copytree(ROOT / "career", root / "career")
    checkpoint.pin(root)                      # tests simulate from the June 26 checkpoint, not the live clock
    if open_market:
        writer = signing.Writer(root)
        signing.open_market(writer, "2003-07-01")
        writer.commit()
    return tmp, root


def agreed(player, bbr, club, open_day, answer_day, route, root):
    """A negotiation agreed on the desk without the engine: the test applies the player's acceptance itself."""
    market = Market(open_day, root)
    fo = FrontOffice(open_day, market, root)
    if club == "Miami Heat":
        position = fo._positions().get(bbr, "SF")
        ask = market.asking(bbr, open_day)
        entry = {"bbr_id": bbr, "player": player, "club": club, "position": position, "valuation": fo.valuation_of(bbr), "ask": ask["first_year"],
                 "years_asked": ask["years"], "route": route, "rfa": False, "score": None}
    else:
        entry = dict(next(t for t in fo.targets([], limit=80) if t["player"] == player), route=route)
    n = Negotiation.open(player, bbr, club, open_day, entry, restricted=False, root=root)
    n.record["priorities"] = {"trait": "money", "weights": market.priorities("money")}
    terms = fo.offer_terms(entry, 1, route=route)
    p = market.players[bbr]
    n.make_offer(terms, open_day, route, p.get("nba_seasons_before_2003_04"), p.get("prior_salary_2002_03"))
    n.apply_answer("accept", answer_day, f"{WINDOW}-{bbr}-offer-1", ask=entry["ask"])
    n.save()
    return n, entry, terms


def driver(root, day):
    run = Run(root)
    run.market = Market(day, root)
    run.fo = FrontOffice(day, run.market, root)
    run.standing = "unsigned_rookie"
    return run


def all_errors(root):
    return negotiation_errors(root) + ledger_errors(root) + holdings_errors(root) + trade_record_errors(root)


class LegalityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp, cls.root = copy_repo()                    # the desk on the June 26 checkpoint, not the live clock
        cls.desk = TradeDesk(DAY, FrontOffice(DAY, Market(DAY, cls.root), cls.root), cls.root)

        cls.market = cls.desk.market

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def contract(self, first, years, raise_share=trades.BIRD_RAISE):
        schedule = [int(round(first * (1 + raise_share * i))) for i in range(years)]
        return {"schedule": schedule, "guaranteed": sum(schedule), "non_option_seasons": years}

    def legal(self, terms, **kw):
        return terms_errors(terms, route="sign_and_trade", years_of_service=5, prior_salary=4000000, cap_rules=self.desk.cap_rules, cba=self.desk.cba, **kw)

    def test_contract_shape(self):
        self.assertEqual(self.legal(self.contract(5000000, 7)), [])                      # Bird length and Bird raises
        self.assertTrue(any("three non-option seasons" in e and "sourced" in e for e in self.legal(self.contract(5000000, 2))))
        self.assertTrue(any("8 seasons exceeds the 7" in e for e in self.legal(self.contract(5000000, 8))))
        self.assertTrue(any("12.5% of the first-year salary" in e for e in self.legal(self.contract(5000000, 4, raise_share=0.2))))
        self.assertEqual(self.legal(dict(self.contract(5000000, 4), guaranteed=self.contract(5000000, 3)["guaranteed"])), [])   # no first-season guarantee rule

    def williams(self, years=3, agreement_date="2003-07-02", first=None):
        """Denver's full-Bird, unrestricted free agent Shammond Williams on his ask."""
        row = self.market.players["willish01"]
        ask = self.market.asking("willish01", agreement_date)
        first = first or ask["first_year"]
        schedule = [int(round(first * (1 + trades.BIRD_RAISE * i))) for i in range(years)]
        terms = {"first_year": first, "years": years, "schedule": schedule, "guaranteed": sum(schedule)}
        st = self.desk.synthetic_from_terms(row["player"], "willish01", row["club"], terms, "sign_and_trade", agreement_date)
        return st

    def test_acquisition_passes_and_names_its_rules(self):
        st = self.williams()
        trade = {"partner": "Denver Nuggets", "miami_out": ["LaPhonso Ellis"], "miami_in": ["Shammond Williams"], "picks_out": [], "picks_in": [],
                 "kind": "sign_and_trade", "sign_and_trade_in": st}
        self.assertEqual(self.desk.errors(trade), [])
        self.assertFalse(st["base_year_compensation"]["applies"])                   # Denver signs him into room: no base-year compensation
        short = dict(trade, sign_and_trade_in=self.williams(years=2))
        self.assertTrue(any("three non-option seasons" in e and "sourced" in e for e in self.desk.errors(short)))
        newble = next(b for b, p in self.market.players.items() if p["player"] == "Ira Newble")      # Atlanta's Early Bird free agent
        early = dict(trade, sign_and_trade_in=dict(st, bbr_id=newble, player="Ira Newble"), miami_in=["Ira Newble"], partner="Atlanta Hawks")
        text = " ".join(self.desk.errors(early))
        self.assertIn(str(SIGN_AND_TRADE_RIGHTS), text)
        self.assertIn("early_bird", text)
        early_desk = TradeDesk("2003-07-10", FrontOffice("2003-07-10", Market("2003-07-10", self.root), self.root), self.root)
        self.assertTrue(any("moratorium" in e for e in early_desk.errors(trade)))
        self.assertTrue(any("115%" in e for e in self.desk.errors(dict(trade, miami_out=["Caron Butler"]))))
        both = dict(trade, sign_and_trade_out=st)
        self.assertTrue(any("exactly one" in e for e in self.desk.errors(both)))
        unlisted = dict(trade, miami_in=[])
        self.assertTrue(any("must be listed in miami_in" in e for e in self.desk.errors(unlisted)))
        free_agent = {"partner": "Denver Nuggets", "miami_out": ["LaPhonso Ellis"], "miami_in": ["Shammond Williams"]}
        self.assertTrue(any("not under contract" in e for e in self.desk.errors(free_agent)))

    def test_incumbent_under_the_cap_absorbs_without_matching(self):
        st = self.williams()
        trade = {"partner": "Denver Nuggets", "miami_out": ["Brian Grant"], "miami_in": ["Shammond Williams"], "picks_out": [], "picks_in": [],
                 "kind": "sign_and_trade", "sign_and_trade_in": st}
        totals = self.desk.totals(trade)
        payroll = self.desk.assets.payroll("Denver Nuggets")
        self.assertEqual(totals["partner_after"], payroll + totals["out_full"])          # his salary was never on Denver's payroll
        self.assertEqual(totals["in_contracted"], 0)
        self.assertLessEqual(totals["partner_after"], self.desk.cap)
        self.assertGreater(totals["out_full"], 1.15 * totals["in_match"] + 100000)        # would fail the 115% test over the cap
        self.assertEqual(self.desk.errors(trade), [])
        with_other = dict(trade, miami_in=["Shammond Williams", "Nene Hilario"])
        t2 = self.desk.totals(with_other)
        nene = self.desk.assets.salary(self.desk.partner_player("Denver Nuggets", "Nene Hilario"))
        self.assertEqual(t2["partner_after"], payroll + t2["out_full"] - nene)
        self.assertEqual(t2["in_full"], totals["in_full"] + nene)

    def test_availability_is_judged_on_the_agreement_date(self):
        kidd = self.market.players["kiddja01"]
        ask = self.market.asking("kiddja01", "2003-07-02")
        schedule = [int(round(ask["first_year"] * (1 + trades.BIRD_RAISE * i))) for i in range(3)]
        terms = {"first_year": ask["first_year"], "years": 3, "schedule": schedule, "guaranteed": sum(schedule)}
        before = self.desk.synthetic_from_terms("Jason Kidd", "kiddja01", kidd["club"], terms, "sign_and_trade", "2003-07-02")
        self.assertFalse(any("no longer unsigned" in e for e in self.desk.acquisition_errors(before, kidd["club"])))
        late = dict(before, agreement_date=DAY)                                             # his real re-signing is July 16
        self.assertTrue(any("no longer unsigned" in e for e in self.desk.acquisition_errors(late, kidd["club"])))

    def test_ids_packets_and_the_rights_share(self):
        st = self.williams()
        # A rebuilding Denver takes Ellis's salary only with a first-round pick (club objectives; it refuses him alone).
        first = [{"year": 2005, "round": 1}]
        alone = {"partner": "Denver Nuggets", "miami_out": ["LaPhonso Ellis"], "miami_in": ["Shammond Williams"], "picks_out": [], "picks_in": [],
                 "kind": "sign_and_trade", "sign_and_trade_in": st}
        self.assertIsNone(self.desk.acceptance_packet(alone)[0])
        trade = dict(alone, picks_out=first)
        plain = {"partner": "Denver Nuggets", "miami_out": ["LaPhonso Ellis"], "miami_in": ["Shammond Williams"], "picks_out": first, "picks_in": []}
        self.assertNotEqual(self.desk.trade_id(trade), self.desk.trade_id(plain))                                   # kind and contract
        self.assertNotEqual(self.desk.trade_id(trade), self.desk.trade_id(dict(trade, sign_and_trade_in=self.williams(years=4))))
        packet, valuation = self.desk.acceptance_packet(trade)
        self.assertEqual(decision_errors(packet), [])
        self.assertEqual(packet["event_id"], f"trade-{self.desk.trade_id(trade)}")
        self.assertIn("sign-and-trade", packet["question"])
        self.assertIn("SIGN_AND_TRADE_RIGHTS_SHARE", packet["basis"])
        self.assertEqual(self.desk.acceptance_packet(trade)[0], packet)
        self.assertEqual(valuation["miami_in"][0]["partner_share"], trades.SIGN_AND_TRADE_RIGHTS_SHARE)
        with mock.patch.object(trades, "SIGN_AND_TRADE_RIGHTS_SHARE", 1.0):
            full = self.desk.valuation(trade)
        self.assertGreater(valuation["partner_gain"], full["partner_gain"])     # the incumbent gives up less than a player under contract

    def test_search_never_offers_a_free_agent_and_feasibility_is_two_sided(self):
        found = self.desk.search(requests=[{"subject": "trade_target", "player": "Latrell Sprewell"}], limit=10)
        self.assertTrue(found)
        for f in found:
            for name in f["trade"]["miami_in"]:
                self.assertIn(self.desk.partner_player(f["trade"]["partner"], name)["status"], trades.UNDER_CONTRACT)
            self.assertNotIn("sign_and_trade_in", f["trade"])
        fo = self.desk.fo
        targets = fo.targets([], limit=80)
        miller = next(t for t in targets if t["player"] == "Brad Miller")           # $9.5M ask on a $4.8M prior: Indiana over the cap
        ok, why = self.desk.sign_and_trade_feasible(miller)
        self.assertFalse(ok)
        self.assertIn("Indiana Pacers over the cap", why)
        july_2 = TradeDesk("2003-07-02", FrontOffice("2003-07-02", Market("2003-07-02", self.root), self.root), self.root)     # Kidd is unsigned until July 16
        kidd = next(t for t in july_2.fo.targets([], limit=80) if t["player"] == "Jason Kidd")   # a raise inside 20%: no base-year compensation
        self.assertEqual(july_2.sign_and_trade_feasible(kidd), (True, None))
        self.assertEqual(fo.route_ceiling("sign_and_trade", "kiddja01"), fo.valuation.maximum(self.market.players["kiddja01"].get("nba_seasons_before_2003_04"),
                                                                                              self.market.players["kiddja01"].get("prior_salary_2002_03")))
        terms = fo.offer_terms(dict(kidd, years_asked=1), 1, route="sign_and_trade")
        self.assertEqual(terms["years"], 3)
        self.assertEqual(terms["raise_percent"], 12.5)

    def test_rules_file_marks_every_item(self):
        rule = read("library/2003/league/nba_1999_cba_rules.json", ROOT)["trades"]
        st = rule["sign_and_trade"]
        self.assertEqual(st["min_non_option_seasons"], 3)
        self.assertNotIn("sign_and_trade_min_seasons", rule)
        for key, value in st.items():
            if key.endswith("_status"):
                self.assertTrue(value.startswith("inferred") or value.startswith("sourced"), key)
        self.assertTrue(rule["matching_under_cap"]["status"].startswith("inferred"))
        self.assertTrue(rule["moratorium_trade_ban"]["status"].startswith("inferred"))
        self.assertEqual(rule["base_year_compensation"]["attached_at"].split(":")[0], "signing")
        calendar = read("library/2003/league/nba_2003_04_calendar.json", ROOT)
        start = next(e for e in calendar["events"] if e["id"] == "moratorium_start")
        self.assertIn("moratorium_trade_ban", start["trades"])


class AcquisitionFlowTests(unittest.TestCase):
    def test_kidd_is_signed_and_traded_or_the_talks_end(self):
        tmp, root = copy_repo()
        self.addCleanup(tmp.cleanup)
        store = Store(root / "data/e.sqlite3")
        store.initialize()
        n, entry, terms = agreed("Jason Kidd", "kiddja01", "New Jersey Nets", "2003-07-01", "2003-07-02", "sign_and_trade", root)
        self.assertEqual(n.record["agreement"]["route"], "sign_and_trade")
        day = "2003-07-16"
        run = driver(root, day)
        self.assertIsNone(run.sign_and_trade(n, day))
        n.save()
        run.writer.commit()
        self.assertEqual(n.record["status"], "trade_pending")
        trade = n.record["trade"]
        self.assertEqual(trade["kind"], "sign_and_trade_in")
        record = json.loads((root / TRADES / f"{trade['trade_id']}.json").read_text())
        self.assertEqual((record["status"], record["kind"], record["negotiation"]), ("proposed", "sign_and_trade", str(FOLDER / "jason_kidd.json")))
        st = record["trade"]["sign_and_trade_in"]
        self.assertEqual((st["route"], st["signing_club"], st["agreement_date"]), ("sign_and_trade", "New Jersey Nets", "2003-07-02"))
        self.assertIn("base_year_compensation", st)
        self.assertTrue((root / TRADES / f"{record['decision_event']}.decision.json").exists())
        self.assertEqual(run.pending, [record["decision_event"]])
        self.assertEqual(run_trade.write(day, root), ([], []))                  # the trade driver leaves a sign-and-trade alone
        self.assertEqual(all_errors(root), [])
        # the same day again writes nothing new, and the real news never ends a trade_pending negotiation
        before = sorted(p.name for p in (root / "career").rglob("*.decision.json"))
        run = driver(root, day)
        self.assertIsNone(run.sign_and_trade(Negotiation.load(root / FOLDER / "jason_kidd.json", root), day))
        self.assertEqual(sorted(p.name for p in (root / "career").rglob("*.decision.json")), before)
        run.state["news_through"] = "2003-07-01"
        run.news("2003-07-17")
        self.assertEqual(Negotiation.load(root / FOLDER / "jason_kidd.json", root).status, "trade_pending")
        local_draw(store, root)
        run = driver(root, day)
        n = Negotiation.load(root / FOLDER / "jason_kidd.json", root)
        record = run.sign_and_trade(n, day)
        n.save()
        run.writer.commit()
        self.assertIn(record["status"], ("completed", "declined"))
        self.assertEqual(record["answer"]["date"], day)
        sheet = json.loads((root / SEASON_DIR / "00_Team/Finances/contract_schedules.json").read_text())
        kidd = next((p for p in sheet["players"] if p["player"] == "Jason Kidd"), None)
        roster = json.loads((root / SEASON_DIR / "00_Team/Team/Roster/roster.json").read_text())
        statuses = {p["name"]: p["status"] for p in roster["players"]}
        if record["status"] == "completed":
            self.assertEqual(n.status, "signed")
            self.assertEqual(record["applied"], day)
            self.assertEqual((kidd["route"], kidd["status"], kidd["acquired"]["how"], kidd["acquired"]["from"]),
                             ("sign_and_trade", "signed_free_agent", "sign_and_trade", "New Jersey Nets"))
            self.assertEqual(kidd["schedule"], st["schedule"])
            self.assertIn(statuses["Jason Kidd"], signing.ACTIVE_STATUSES)
            self.assertTrue((root / SEASON_DIR / "00_Team/Team/Player_Cards/jason_kidd.md").exists())
            holdings = json.loads((root / SEASON_DIR / "00_Team/Team/Roster/holdings.json").read_text())
            self.assertTrue(any(e["player"] == "Jason Kidd" and e["from"] == day and e["until"] is None for e in holdings["entries"]))
            for name in record["trade"]["miami_out"]:
                self.assertEqual(statuses[name], "traded")
            self.assertIn("sign-and-trade", (root / SEASON_DIR / "01_Free_Agency/note.md").read_text())
        else:
            self.assertEqual(n.status, "ended")
            self.assertIsNone(kidd)
            self.assertNotIn("Jason Kidd", statuses)
        self.assertNotIn("trade_pending", [Negotiation.load(p, root).status for p in (root / FOLDER).glob("*.json") if ".decision" not in p.name])
        self.assertEqual(all_errors(root), [])
        self.assertEqual(run_trade.write("2003-07-22", root), ([], []))


class OwnOutFlowTests(unittest.TestCase):
    def own_out_patches(self):
        """The fit threshold raised and the value floors relaxed so 2003's inventories yield a partner for House."""
        patches = (mock.patch.object(gm, "RESIGN_AND_TRADE_FIT", 2.0), mock.patch.object(trades, "SEARCH_MIN_GAIN", -1.0),
                   mock.patch.object(trades, "OWN_OUT_ACCEPT_MARGIN", 0.0))
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def test_house_is_signed_and_traded_in_one_transaction_or_re_signed(self):
        tmp, root = copy_repo()
        self.addCleanup(tmp.cleanup)
        store = Store(root / "data/e.sqlite3")
        store.initialize()
        n, entry, terms = agreed("Eddie House", "houseed01", "Miami Heat", "2003-07-16", "2003-07-17", "bird", root)
        day = "2003-07-17"
        desk = TradeDesk(day, FrontOffice(day, Market(day, root), root), root)
        # the proposal's contract: Miami's base-year flag attached from its ledger on the date, before any signing
        st = desk.synthetic_from_terms("Eddie House", "houseed01", "Miami Heat", terms, "bird", day)
        self.assertEqual((st["route"], st["signing_club"], st["prior_season_salary"]["amount"]), ("bird", "Miami Heat", 637435))
        self.assertTrue(st["base_year_compensation"]["applies"])                     # a raise over 20% while Miami is over the cap
        self.assertIn("attached at the signing", st["base_year_compensation"]["status"])
        matched, note = desk.matching_salary(desk._synthetic(st), True)
        self.assertEqual(matched, max(st["schedule"]["2003-04"] * 0.5, 637435))
        # four totals: the partner's test runs on his full salary, Miami's on the base-year value; his salary never reaches Miami's payroll
        dump = {"partner": "New York Knicks", "miami_out": ["Eddie House"], "miami_in": [], "picks_out": [], "picks_in": [],
                "kind": "sign_and_trade", "sign_and_trade_out": st}
        totals = desk.totals(dump)
        self.assertEqual((totals["out_full"], totals["out_match"], totals["out_contracted"]), (st["schedule"]["2003-04"], matched, 0))
        errors = desk.errors(dump)
        self.assertTrue(any("New York Knicks over the cap" in e and f"${st['schedule']['2003-04']:,}" in e for e in errors), errors)
        self.assertFalse(any("Miami over the cap" in e or "already re-signed" in e or "newly signed" in e for e in errors))
        self.assertEqual(desk.errors(dict(dump, miami_out=[])), ["Eddie House: the sign-and-trade player must be listed in miami_out"])
        self.assertEqual(all_errors(root), [])
        sheet = json.loads((root / SEASON_DIR / "00_Team/Finances/contract_schedules.json").read_text())
        self.assertNotIn("re_signed", {p["status"] for p in sheet["players"] if p["player"] == "Eddie House"})
        # the front office shops him at the agreed stage: the proposal and both packets, the player still unsigned
        self.own_out_patches()
        record, considered = run_trade.shop(day, root)
        self.assertIsNotNone(record, considered)
        self.assertEqual([c["outcome"] for c in considered], ["proposal"])
        self.assertEqual((record["status"], record["kind"]), ("proposed", "sign_and_trade"))
        self.assertEqual(record["trade"]["miami_out"], ["Eddie House"])
        self.assertEqual(record["trade"]["sign_and_trade_out"]["base_year_compensation"], st["base_year_compensation"])
        self.assertEqual(record["player_consent_event"], f"2003-fa-houseed01-sign-and-trade-{record['trade_id']}")
        self.assertIn("same transaction", record["basis"])
        n = Negotiation.load(root / FOLDER / "eddie_house.json", root)
        self.assertEqual(n.status, "trade_pending")                                     # unsigned until the trade executes
        self.assertEqual(n.record["trade"]["kind"], "sign_and_trade_out")
        roster = json.loads((root / SEASON_DIR / "00_Team/Team/Roster/roster.json").read_text())
        self.assertEqual(next(p["status"] for p in roster["players"] if p["name"] == "Eddie House"), "free_agent_rights_held")
        sheet = json.loads((root / SEASON_DIR / "00_Team/Finances/contract_schedules.json").read_text())
        self.assertFalse(any(p["player"] == "Eddie House" and p.get("signed_date") for p in sheet["players"]))
        consent = root / FOLDER / f"{record['player_consent_event']}.decision.json"
        self.assertTrue(consent.exists())
        packet = json.loads(consent.read_text())
        self.assertEqual(decision_errors(packet), [])
        self.assertEqual(set(packet["options"]), {"accept", "reject"})
        self.assertIn(record["trade"]["partner"], packet["question"])
        self.assertTrue((root / TRADES / f"{record['decision_event']}.decision.json").exists())
        self.assertEqual(all_errors(root), [])
        before = sorted(p.name for p in (root / "career").rglob("*.decision.json"))
        again, considered = run_trade.shop(day, root)
        self.assertEqual(again["trade_id"], record["trade_id"])
        self.assertEqual([c["outcome"] for c in considered], ["proposal"])
        self.assertEqual(sorted(p.name for p in (root / "career").rglob("*.decision.json")), before)
        self.assertEqual(run_trade.write(day, root), ([], []))                           # the trade driver leaves a sign-and-trade alone
        local_draw(store, root)
        final, considered = run_trade.shop(day, root)
        self.assertIn(final["status"], ("completed", "declined"))
        self.assertEqual(sorted(p.name for p in (root / "career").rglob("*.decision.json")), before)
        rights = json.loads((root / SEASON_DIR / "00_Team/Finances/free_agent_rights.json").read_text())
        house_rights = next(p for p in rights["players"] if p["player"] == "Eddie House")
        roster = json.loads((root / SEASON_DIR / "00_Team/Team/Roster/roster.json").read_text())
        sheet = json.loads((root / SEASON_DIR / "00_Team/Finances/contract_schedules.json").read_text())
        house = next(p for p in sheet["players"] if p["player"] == "Eddie House")
        status = next(p["status"] for p in roster["players"] if p["name"] == "Eddie House")
        holdings = json.loads((root / SEASON_DIR / "00_Team/Team/Roster/holdings.json").read_text())
        n = Negotiation.load(root / FOLDER / "eddie_house.json", root)
        self.assertEqual(n.status, "signed")                                            # either way he is signed on the agreed terms that day
        self.assertEqual((house["signed_date"], house["route"], house["schedule"]), (day, "bird", st["schedule"]))
        self.assertEqual(house["base_year_compensation"], st["base_year_compensation"])   # attached once, never re-derived
        self.assertTrue(house_rights.get("re_signed"))
        partner = final["trade"]["partner"]
        if final["status"] == "completed":
            self.assertEqual([c["outcome"] for c in considered], ["completed"])
            self.assertTrue(house_rights.get("traded"))
            self.assertEqual((status, house["status"], final["applied"]), ("traded", "traded", day))
            self.assertIn("same transaction", house["notes"])
            self.assertFalse(any(e["player"] == "Eddie House" and e["from"] == day for e in holdings["entries"]))   # never held by Miami
            departures = json.loads((root / SEASON_DIR / "00_Team/Team/Roster/departures.json").read_text())
            self.assertTrue(any(e["player"] == "Eddie House" and e["club"] == partner for e in departures["entries"]))
            self.assertIn("houseed01", miami_departed("2003-04", "2003-11-15", root))
            self.assertIn("houseed01", {a["bbr_id"] for a in miami_departures("2003-04", partner, "2003-11-15", root)})
            other = "Denver Nuggets" if partner != "Denver Nuggets" else "Utah Jazz"
            self.assertNotIn("houseed01", {a["bbr_id"] for a in miami_departures("2003-04", other, "2003-11-15", root)})
            for name in final["trade"]["miami_in"]:
                self.assertEqual(next(p["status"] for p in roster["players"] if p["name"] == name), "under_contract")
        else:
            self.assertEqual([c["outcome"] for c in considered], ["declined; re-signed on the agreed terms"])
            self.assertEqual((status, house["status"]), ("re_signed", "re_signed"))      # the agreement stands: an ordinary re-signing
            self.assertIsNone(house_rights.get("traded"))
            self.assertTrue(any(e["player"] == "Eddie House" and e["from"] == day and e["until"] is None for e in holdings["entries"]))
            self.assertEqual(miami_departed("2003-04", "2003-11-15", root), frozenset())
            self.assertIn("re-signs him on the agreed terms", (root / SEASON_DIR / "01_Free_Agency/note.md").read_text())
        self.assertEqual(n.record["trade"]["outcome"], final["status"])
        self.assertEqual(all_errors(root), [])
        self.assertEqual(run_trade.write("2003-07-22", root), ([], []))
        self.assertEqual(run_trade.shop("2003-07-18", root), (None, []))                 # a signed player is nothing to shop

    def test_a_re_signed_player_is_a_signed_player_whatever_the_label(self):
        """A completed Bird re-signing traded on a later day is an ordinary trade of a newly signed player: the
        `sign_and_trade_out` wrapper does not lift the restriction (the rules file's sourced simultaneity item)."""
        tmp, root = copy_repo()
        self.addCleanup(tmp.cleanup)
        n, entry, terms = agreed("Eddie House", "houseed01", "Miami Heat", "2003-07-16", "2003-07-17", "bird", root)
        n.execute_agreement("2003-07-17")
        writer = signing.Writer(root)
        signing.sign(writer, n, "2003-07-17", cap=Market("2003-07-17", root).planning_cap("2003-07-17"))
        n.save()
        writer.commit()
        self.own_out_patches()
        for day in ("2003-07-17", "2003-07-18", "2003-10-01", "2003-12-01"):
            desk = TradeDesk(day, FrontOffice(day, Market(day, root), root), root)
            house = desk.miami_player("Eddie House")[0]
            self.assertEqual(desk.blocked(house), "newly signed: not tradable until 2003-12-15 (inferred for 1999 (modern rule believed unchanged))")
            plain = {"partner": "New York Knicks", "miami_out": ["Eddie House"], "miami_in": ["Frank Williams"], "picks_out": [], "picks_in": []}
            self.assertIn("Eddie House: newly signed: not tradable until 2003-12-15 (inferred for 1999 (modern rule believed unchanged))", desk.errors(plain))
            st = desk.synthetic_from_terms("Eddie House", "houseed01", "Miami Heat", terms, "bird", "2003-07-17")
            wrapped = dict(plain, kind="sign_and_trade", sign_and_trade_out=st)
            errors = desk.errors(wrapped)
            self.assertTrue(any("already re-signed on 2003-07-17" in e and "one transaction" in e and "sourced" in e for e in errors), (day, errors))
            self.assertIn("Eddie House: newly signed: not tradable until 2003-12-15 (inferred for 1999 (modern rule believed unchanged))", errors)
            if day >= "2003-07-18":
                self.assertEqual(run_trade.shop(day, root), (None, []))                 # nothing agreed and unsigned to shop
        after = TradeDesk("2003-12-15", FrontOffice("2003-12-15", Market("2003-12-15", root), root), root)
        self.assertIsNone(after.blocked(after.miami_player("Eddie House")[0]))          # from then on an ordinary trade
        self.assertFalse(any("newly signed" in e for e in after.errors(plain)))


class SigningFlagTests(unittest.TestCase):
    def test_base_year_compensation_is_attached_at_the_signing_only(self):
        tmp, root = copy_repo()
        self.addCleanup(tmp.cleanup)
        market = Market(DAY, root)
        fo = FrontOffice(DAY, market, root)
        cap = market.planning_cap(DAY)
        room = signing.base_year_compensation(fo.sheet, fo.rights, "Anyone", "room", 5000000, 1000000, cap, DAY)
        self.assertFalse(room["applies"])
        bird = signing.base_year_compensation(fo.sheet, fo.rights, "Eddie House", "bird", 1500000, 637435, cap, DAY)
        self.assertTrue(bird["applies"])
        self.assertIn("inferred", bird["status"])
        small = signing.base_year_compensation(fo.sheet, fo.rights, "Eddie House", "bird", 700000, 637435, cap, DAY)
        self.assertFalse(small["applies"])                                                 # a raise inside 20%
        desk = TradeDesk(DAY, fo, root)
        self.assertFalse(desk.base_year_compensation("Denver Nuggets", 5000000, 2000000)["applies"])     # signed into room
        self.assertTrue(desk.base_year_compensation("New York Knicks", 5000000, 2000000)["applies"])


if __name__ == "__main__":
    unittest.main()
