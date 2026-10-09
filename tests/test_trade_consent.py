"""The one-year-contract trade consent rule (2005 agreement; cbafaq05 Q83, Q88, Q26; runtime/trades.py ConsentBook).

A player under a one-year contract (any option year excluded) whose club will hold his Larry Bird or Early Bird rights at
its end cannot be traded without his consent; consenting, he loses those rights and is a Non-Bird free agent of his new
club. The rule's tests run on a small stand-in record set in a temporary root (no live record is read or written), except
the read-only checks of the live records: Trevor Ariza's status, Miami's players and the replay of every trade recorded
before the gate.
"""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from runtime import free_agency_2004 as fa
from runtime import league_trades, trades
from runtime.decisions import decision_errors

ROOT = Path(__file__).resolve().parents[1]
LAKERS, DETROIT, BOSTON, MIAMI = "Los Angeles Lakers", "Detroit Pistons", "Boston Celtics", "Miami Heat"
DAY = "2005-12-20"                        # after CONSENT_FROM


def _write(root, rel, data):
    path = Path(root) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1), encoding="utf-8")


def ledger_row(b, club, kind, route, schedule, **extra):
    return dict({"player": b.upper(), "bbr_id": b, "club": club, "kind": kind, "route": route, "schedule": schedule,
                 "source": "test"}, **extra)


def stand_in(root):
    """Two seasons of records: the 2004-05 and 2005-06 ledgers, the 2004 and 2005 summer markets, the league's moves,
    the 2005 draft and Miami's sheets and holdings."""
    rules = Path(root) / trades.CBA_2005_PATH                       # the Bird clock's seasons come from the rules file
    rules.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / trades.CBA_2005_PATH, rules)
    one = {"2005-06": 800_000}
    _write(root, "career/Dwyane_Wade/2005-06/League/contracts.json", {"contracts": [
        ledger_row("eb01", LAKERS, "new", "qualifying_offer", one),         # Early Bird: Detroit 2004, traded, QO 2005
        ledger_row("new01", LAKERS, "new", "minimum", one),                  # signed from another club this summer
        ledger_row("multi01", LAKERS, "new", "bird", {"2005-06": 2_000_000, "2006-07": 2_100_000, "2007-08": 2_200_000}),
        ledger_row("opt01", LAKERS, "new", "bird", {"2005-06": 1_000_000, "2006-07": 1_080_000}, options={"2006-07": "player_option"}),
        ledger_row("opt02", LAKERS, "new", "bird", {"2005-06": 1_000_000, "2006-07": 1_080_000}),   # the option exercised: two seasons
        ledger_row("unk01", LAKERS, "new", "minimum", one),                  # no market event: unknown history
        ledger_row("pick01", LAKERS, "new", "minimum", one),                 # a 2005 pick's first contract (matched sheet)
        ledger_row("bird01", LAKERS, "new", "bird", one),                    # re-signed after a carried contract: three seasons
        ledger_row("ten01", LAKERS, "new", "minimum", one),                  # ended 2004-05 on a ten-day: one season
        ledger_row("claim01", LAKERS, "new", "qualifying_offer", one),       # claimed off waivers in December
    ]})
    _write(root, "career/Dwyane_Wade/2004-05/League/contracts.json", {"contracts": [
        ledger_row("eb01", LAKERS, "new", "minimum", {"2004-05": 400_000}, signed_club=DETROIT),
        ledger_row("opt01", LAKERS, "existing", "existing", {"2004-05": 900_000}),
        ledger_row("bird01", LAKERS, "existing", "existing", {"2004-05": 900_000}),
        ledger_row("ten01", LAKERS, "new", "minimum", {"2004-05": 400_000}),
        ledger_row("claim01", LAKERS, "new", "minimum", {"2004-05": 400_000}),
    ]})
    ev = lambda kind, b, club, frm=None, day="2005-08-02": {"date": day, "kind": kind, "player": b.upper(), "bbr_id": b, "club": club, "from": frm}
    _write(root, fa.record_path(2005), {"events": [
        ev("qualifying_offer_accepted", "eb01", LAKERS, day="2005-09-30"), ev("signing", "new01", LAKERS, "Chicago Bulls"),
        ev("re_sign", "multi01", LAKERS, LAKERS), ev("re_sign", "opt01", LAKERS, LAKERS), ev("re_sign", "opt02", LAKERS, LAKERS),
        ev("offer_sheet_matched", "pick01", LAKERS, "Utah Jazz"), ev("re_sign", "bird01", LAKERS, LAKERS),
        ev("re_sign", "ten01", LAKERS, LAKERS), ev("qualifying_offer_accepted", "claim01", LAKERS, day="2005-09-30"),
        ev("re_sign", "mia01", MIAMI, MIAMI)], "clubs": {}, "unsigned_pool": []})
    _write(root, fa.record_path(2004), {"events": [
        ev("signing", "eb01", DETROIT, day="2004-07-14"), ev("signing", "ten01", LAKERS, "Denver Nuggets", day="2004-07-20"),
        ev("re_sign", "claim01", LAKERS, LAKERS, day="2004-07-20"), ev("signing", "mia01", MIAMI, day="2004-08-01")],
        "clubs": {}, "unsigned_pool": []})
    _write(root, "career/Dwyane_Wade/2004-05/League/league_moves.json", {"entries": [
        {"deal": "d1", "date": "2005-01-03", "kind": "trade", "player": "EB01", "bbr_id": "eb01", "from": DETROIT, "to": LAKERS},
        {"id": "w", "date": "2005-02-20", "kind": "waive", "player": "TEN01", "bbr_id": "ten01", "from": LAKERS, "to": None},
        {"id": "t", "date": "2005-03-01", "kind": "ten_day", "player": "TEN01", "bbr_id": "ten01", "from": None, "to": LAKERS}]})
    _write(root, "career/Dwyane_Wade/2005-06/League/league_moves.json", {"entries": [
        {"id": "c", "date": "2005-12-05", "kind": "claim", "player": "CLAIM01", "bbr_id": "claim01", "from": None, "to": BOSTON}]})
    _write(root, "career/Dwyane_Wade/2004-05/09_Draft/draft_2005.json", {"picks": [
        {"pick": 40, "round": 2, "club": LAKERS, "player": "PICK01", "bbr_id": "pick01"}]})
    for season, signed in (("2005-06", "2005-08-02"), ("2004-05", "2004-08-01")):
        _write(root, f"career/Dwyane_Wade/{season}/00_Team/Finances/contract_schedules.json", {"players": [
            {"player": "MIA01", "bbr_id": "mia01", "status": "under_contract", "route": "minimum", "signed_date": signed,
             "schedule": {season: 700_000}, "amount_kind": {season: "contract_salary"}}]})
        _write(root, f"career/Dwyane_Wade/{season}/00_Team/Team/Roster/roster.json", {"players": [{"name": "MIA01", "bbr_id": "mia01"}]})
    _write(root, "career/Dwyane_Wade/2004-05/00_Team/Team/Roster/holdings.json",
           {"kind": "miami_holdings", "owner": "ai_gm", "entries": [{"player": "MIA01", "bbr_id": "mia01", "from": "2004-08-01", "until": None}]})


def _extend(root, rel, key, *items):
    """Append rows to a list in a stand-in record."""
    path = Path(root) / rel
    data = json.loads(path.read_text(encoding="utf-8"))
    data[key].extend(items)
    path.write_text(json.dumps(data, indent=1), encoding="utf-8")


def re_signings(root):
    """Re-signings by the club holding the rights, for every club alike: ros01 (Lakers, 2004-05 carried, left in the 2005
    pool with the Lakers' rights, signed by them to a rest-of-season contract), rosm01 (the same facts for Miami: its
    sheet and holdings), ros02 (same pool rights, signed by Boston), ros03 (a ten-day with Boston, then the Lakers), ren01
    (renounced by the Lakers in the 2005 market, then signed back by them), ren02 (renounced by the Lakers, signed by
    Boston, waived and signed by the Lakers for the rest of the season: he changed teams) and renm01 (renounced by
    Miami, then a Miami camp signing)."""
    carried = {"2004-05": 900_000}
    for b in ("ros01", "ros02", "ros03", "ren01", "ren02"):
        _extend(root, "career/Dwyane_Wade/2004-05/League/contracts.json", "contracts", ledger_row(b, LAKERS, "existing", "existing", carried))
    _extend(root, "career/Dwyane_Wade/2005-06/League/contracts.json", "contracts", ledger_row("ren01", LAKERS, "new", "cap_room", {"2005-06": 800_000}))
    _extend(root, fa.record_path(2005), "unsigned_pool", *[{"player": b.upper(), "bbr_id": b, "price": 1, "rights": c}
                                                            for b, c in (("ros01", LAKERS), ("ros02", LAKERS), ("ros03", LAKERS),
                                                                         ("rosm01", MIAMI), ("renm01", None))])
    _extend(root, fa.record_path(2005), "events",
            {"date": "2005-07-20", "kind": "renounce", "player": "REN01", "bbr_id": "ren01", "club": LAKERS},
            {"date": "2005-08-02", "kind": "signing", "player": "REN01", "bbr_id": "ren01", "club": LAKERS, "from": LAKERS},
            {"date": "2005-07-20", "kind": "renounce", "player": "RENM01", "bbr_id": "renm01", "club": MIAMI},
            {"date": "2005-07-20", "kind": "renounce", "player": "REN02", "bbr_id": "ren02", "club": LAKERS},
            {"date": "2005-08-02", "kind": "signing", "player": "REN02", "bbr_id": "ren02", "club": BOSTON, "from": LAKERS})
    _extend(root, "career/Dwyane_Wade/2005-06/League/contracts.json", "contracts", ledger_row("ren02", BOSTON, "new", "minimum", {"2005-06": 800_000}))
    move = lambda b, kind, to, day: {"id": f"{b}-{kind}", "date": day, "kind": kind, "player": b.upper(), "bbr_id": b, "from": None, "to": to}
    _extend(root, "career/Dwyane_Wade/2005-06/League/league_moves.json", "entries",
            move("ros01", "rest_of_season", LAKERS, "2005-11-15"), move("ros02", "rest_of_season", BOSTON, "2005-11-15"),
            move("ros03", "ten_day", BOSTON, "2005-11-10"), move("ros03", "rest_of_season", LAKERS, "2005-11-25"),
            dict(move("ren02", "waive", None, "2005-11-05"), **{"from": BOSTON}), move("ren02", "rest_of_season", LAKERS, "2005-11-20"))
    sheet = lambda b, season, signed, route: {"player": b.upper(), "bbr_id": b, "status": "under_contract", "route": route,
                                               "signed_date": signed, "schedule": {season: 700_000}, "amount_kind": {season: "contract_salary"}}
    _extend(root, "career/Dwyane_Wade/2005-06/00_Team/Finances/contract_schedules.json", "players",
            sheet("rosm01", "2005-06", "2005-11-15", "minimum"), sheet("renm01", "2005-06", "2005-09-30", "minimum"))
    _extend(root, "career/Dwyane_Wade/2004-05/00_Team/Finances/contract_schedules.json", "players",
            sheet("rosm01", "2004-05", "2003-07-20", "existing"), sheet("renm01", "2004-05", "2003-07-20", "existing"))
    _extend(root, "career/Dwyane_Wade/2004-05/00_Team/Team/Roster/holdings.json", "entries",
            *[{"player": b.upper(), "bbr_id": b, "from": "2004-07-01", "until": None} for b in ("rosm01", "renm01")])


class StandIn(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        stand_in(cls.root)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def status(self, b, club=LAKERS, on=DAY):
        return trades.ConsentBook(on, self.root).status(b, club, b.upper() if b else None)


class WhoHoldsItTests(StandIn):
    def test_one_year_with_early_bird_rights_holds_it(self):
        s = self.status("eb01")
        self.assertEqual((s["holds"], s["rights"], s["seasons"]), (True, "early_bird", 2))
        self.assertIn("qualifying offer accepted", s["basis"])
        self.assertIn("signing with Detroit Pistons", s["basis"])     # traded to the Lakers: the trade did not reset the clock
        self.assertEqual(s["rule"], trades.CONSENT_RULE)

    def test_three_seasons_give_larry_bird_rights(self):
        s = self.status("bird01")
        self.assertEqual((s["holds"], s["rights"], s["seasons"]), (True, "larry_bird", 3))

    def test_one_year_without_the_seasons_does_not(self):
        for b, why in (("new01", "one season"), ("pick01", "one season"), ("ten01", "one season")):
            with self.subTest(player=b):
                s = self.status(b)
                self.assertFalse(s["holds"])
                self.assertIn(why, s["basis"])
        self.assertIn("first NBA contract", self.status("pick01")["basis"])  # a pick's first contract starts his clock

    def test_a_multi_year_contract_does_not(self):
        s = self.status("multi01")
        self.assertFalse(s["holds"])
        self.assertIn("not a one-year contract", s["basis"])

    def test_an_option_year_is_excluded_until_exercised(self):
        s = self.status("opt01")                                         # one season plus a player option: one-year
        self.assertEqual((s["holds"], s["rights"]), (True, "larry_bird"))
        self.assertFalse(self.status("opt02")["holds"])                 # the option exercised: two seasons

    def test_unknown_history_gives_no_right(self):
        s = self.status("unk01")
        self.assertFalse(s["holds"])
        self.assertIn("unknown", s["basis"])
        self.assertFalse(self.status(None)["holds"])

    def test_a_waiver_claim_starts_a_new_clock(self):
        self.assertTrue(self.status("claim01", on="2005-12-01")["holds"])
        s = self.status("claim01", club=BOSTON, on="2005-12-10")
        self.assertFalse(s["holds"])
        self.assertIn("claim", s["basis"])

    def test_miami_reads_its_own_sheet_and_holdings(self):
        s = self.status("mia01", club=MIAMI)
        self.assertEqual((s["holds"], s["rights"], s["seasons"]), (True, "early_bird", 2))
        self.assertIn("Miami contract", s["basis"])
        self.assertFalse(trades.ConsentBook(DAY, self.root).status(None, MIAMI, trades.PROTAGONIST)["holds"])   # never Wade

    def test_a_player_who_consented_once_is_a_non_bird_free_agent_already(self):
        moves = self.root / "career/Dwyane_Wade/2005-06/League/league_moves.json"
        before = moves.read_text(encoding="utf-8")
        data = json.loads(before)
        data["entries"].append({"deal": "x", "date": "2005-12-15", "kind": "trade", "player": "BIRD01", "bbr_id": "bird01",
                                "from": LAKERS, "to": BOSTON, "consent": {"answer": "consented", "rights_lost": "larry_bird"}})
        moves.write_text(json.dumps(data), encoding="utf-8")
        try:
            self.assertTrue(self.status("bird01", on="2005-12-14")["holds"])
            later = self.status("bird01", club=BOSTON, on="2005-12-16")
            self.assertFalse(later["holds"])
            self.assertIn("Non-Bird free agent already", later["basis"])
            self.assertEqual(trades.lost_bird_rights("2005-06", self.root)["bird01"]["club"], BOSTON)
        finally:
            moves.write_text(before, encoding="utf-8")


class ReSigningTests(StandIn):
    """cbafaq05 Q26 resets the clock only when he changes teams by signing as a free agent; Q34 makes a renounced player
    who re-signs with his prior club a Bird free agent again. The same facts give the same answer for Miami and any other
    club."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        re_signings(cls.root)

    def test_a_rest_of_season_re_signing_by_the_rights_club_continues_the_clock(self):
        s = self.status("ros01")
        self.assertEqual((s["holds"], s["rights"], s["seasons"]), (True, "larry_bird", 3))
        self.assertIn("re-signed by the club that kept his rights", s["basis"])
        self.assertFalse(self.status("ros01", on="2005-11-14")["holds"])     # not yet signed: no contract

    def test_miami_and_another_club_get_the_same_answer(self):
        lakers, miami = self.status("ros01"), self.status("rosm01", club=MIAMI)
        self.assertEqual((miami["holds"], miami["rights"], miami["seasons"]), (lakers["holds"], lakers["rights"], lakers["seasons"]))

    def test_a_signing_by_another_club_starts_a_clock(self):
        s = self.status("ros02", club=BOSTON)
        self.assertEqual((s["holds"], s["seasons"]), (False, 1))
        s = self.status("ros03")                                            # a ten-day with Boston first: he changed teams
        self.assertEqual((s["holds"], s["seasons"]), (False, 1))
        s = self.status("ren02")                                            # renounced, signed by Boston, waived, back: a new clock
        self.assertEqual((s["holds"], s["seasons"]), (False, 1))

    def test_a_renounced_players_return_continues_the_clock(self):
        s = self.status("ren01")
        self.assertEqual((s["holds"], s["rights"], s["seasons"]), (True, "larry_bird", 3))
        self.assertIn("Q34", s["basis"])
        m = self.status("renm01", club=MIAMI)
        self.assertEqual((m["holds"], m["rights"], m["seasons"]), (True, "larry_bird", 3))
        self.assertIn("renouncement", m["basis"])


class FakeValuation:
    """The valuation fields the consent model reads: service, the minimum scale, the comparables price, the maximum and
    the mid-level, age and last season's evidence."""
    mid_level = 5_000_000

    def __init__(self, service, prices):
        self.service, self.prices, self.stats = service, prices, {}

    def minimum(self, n):
        return 400_000 + 50_000 * (n or 0)

    def price(self, b, service=None, salary=None):
        return self.prices.get(b)

    def maximum(self, service, salary=None):
        return 12_000_000

    def age(self, b):
        return 24


class FakeAssets:
    season, on = "2005-06", DAY

    def __init__(self, root, forms, positions, wins, service=None, prices=None, contracts=None):
        self.root, self._forms, self.positions = Path(root), forms, positions
        self.valuation = FakeValuation(service or {}, prices or {})
        self._consent_tables = ({c: {"wins": w, "losses": 82 - w} for c, w in wins.items()}, {})
        self._season_totals = {}
        self.contracts = contracts or {}
        self.standings = {}

    def form_value(self, b):
        return self._forms.get(b)


GUARDS = {"hol01": 10.0, "lak01": 15.0, "lak02": 12.0, "atl01": 20.0, "atl02": 18.0, "atl03": 16.0, "atl04": 14.0}
WINS = {LAKERS: 30, MIAMI: 60, "Atlanta Hawks": 20}


class ChanceTests(unittest.TestCase):
    """`consent_chance`, `bird_rights_cost` and `non_bird_reach` on stand-in assets (no record is read)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.assets = FakeAssets(self.tmp.name, GUARDS, {b: (None, "SG", 9) for b in GUARDS}, WINS,
                                 service={"hol01": 1, "vet01": 5}, prices={"hol01": 8_000_000, "vet01": 8_000_000})
        self.status = {"holds": True, "rights": "early_bird", "seasons": 2, "basis": "stand-in holder"}
        self.player = {"player": "HOL01", "bbr_id": "hol01", "schedule": {"2005-06": 1_000_000}}

    def chance(self, new, new_roster, rights="early_bird"):
        return trades.consent_chance(self.assets, dict(self.status, rights=rights), self.player, LAKERS, new,
                                     ["hol01", "lak01", "lak02"], new_roster, self.tmp.name)

    def test_a_bigger_role_on_a_stronger_club_raises_his_chance_inside_the_limits(self):
        good, gd = self.chance(MIAMI, ["hol01"])
        bad, bd = self.chance("Atlanta Hawks", ["hol01", "atl01", "atl02", "atl03", "atl04"])
        self.assertGreater(good, bad)
        for p in (good, bad):
            self.assertTrue(trades.CONSENT_LIMITS[0] <= p <= trades.CONSENT_LIMITS[1])
        self.assertEqual((gd["stay"]["club"], gd["stay"]["role_minutes"], gd["stay"]["strength"]), (LAKERS, 22, 30.0))
        self.assertEqual((gd["move"]["club"], gd["move"]["role_minutes"], gd["move"]["strength"]), (MIAMI, 34, 60.0))
        self.assertEqual((bd["move"]["role_minutes"], bd["move"]["strength"]), (8, 20.0))
        self.assertAlmostEqual(gd["gap"], round(gd["move"]["utility"] - gd["stay"]["utility"] - gd["rights_cost"], 2), places=1)
        self.assertGreater(gd["rights_cost"], 0)                       # the rights he gives up count against the move

    def test_larry_bird_rights_cost_more_than_early_bird_rights(self):
        from runtime.player_utility import weights
        w = weights(24, None)
        early, _ = trades.bird_rights_cost(self.assets, "vet01", 1_000_000, "early_bird", w)
        larry, basis = trades.bird_rights_cost(self.assets, "vet01", 1_000_000, "larry_bird", w)
        self.assertGreater(larry, early)
        self.assertGreater(early, 0)
        self.assertIn("120% of his salary", basis)
        _, gd = self.chance(MIAMI, ["hol01"])
        _, ld = self.chance(MIAMI, ["hol01"], rights="larry_bird")
        self.assertGreater(ld["rights_cost"], gd["rights_cost"])

    def test_the_non_bird_limit_counts_the_qualifying_offer_of_a_restricted_free_agent(self):
        amount, name = trades.non_bird_reach(self.assets, "hol01", 1_000_000)      # one season of service: restricted next summer
        self.assertEqual((amount, name), (1_250_000, "his qualifying offer (a restricted free agent)"))
        self.assertEqual(amount, fa.qualifying_amount(1_000_000, 2, {"minimum": {n: self.assets.valuation.minimum(n) for n in range(11)}}))
        amount, name = trades.non_bird_reach(self.assets, "vet01", 1_000_000)      # five seasons: unrestricted
        self.assertEqual((amount, name), (1_200_000, "120% of his salary"))
        amount, name = trades.non_bird_reach(self.assets, "vet01", 100_000)
        self.assertEqual((amount, name), (1.2 * self.assets.valuation.minimum(6), "120% of his minimum"))


class RecordingChance:
    """Stands in for `trades.consent_chance`, recording the clubs and rosters it is asked about."""

    def __init__(self):
        self.calls = []

    def __call__(self, assets, status, player, stay, new, stay_roster, new_roster, root=None):
        self.calls.append({"bbr": player["bbr_id"], "stay": stay, "new": new, "stay_roster": list(stay_roster), "new_roster": list(new_roster)})
        return 0.5, {"basis": "recorded"}


class HolderBook:
    """A ConsentBook stand-in: eb01 holds Early Bird rights with the Lakers, mia02 with Miami."""

    def status(self, b, club, name=None):
        holder = {"eb01": LAKERS, "mia02": MIAMI}.get(b)
        if holder != club:
            return {"holds": False}
        return {"holds": True, "rights": "early_bird", "seasons": 2, "basis": "stand-in holder"}


class DeskRowsTests(unittest.TestCase):
    """The real row builders after CONSENT_FROM: each holder is asked about the club he leaves (its roster before the
    trade) and the club he joins (its roster after it)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        lakers = [{"player": "EB01", "bbr_id": "eb01", "schedule": {"2005-06": 800_000}},
                  {"player": "LAK02", "bbr_id": "lak02", "schedule": {"2005-06": 900_000}}]
        forms = {"eb01": 10.0, "lak02": 12.0, "mia02": 9.0, trades.WADE_BBR: 20.0}
        self.assets = FakeAssets(self.tmp.name, forms, {b: (None, "SG", 9) for b in forms}, {LAKERS: 30, MIAMI: 50},
                                 service={"eb01": 2, "mia02": 2}, prices={"eb01": 3_000_000, "mia02": 3_000_000},
                                 contracts={LAKERS: {"players": lakers}})
        d = trades.TradeDesk.__new__(trades.TradeDesk)
        d.on, d.root, d.season, d.assets = DAY, Path(self.tmp.name), "2005-06", self.assets
        d.fo = mock.Mock(roster={"players": [{"name": trades.PROTAGONIST, "status": "under_rookie_contract"},
                                             {"name": "MIA02", "bbr_id": "mia02", "status": "under_contract"}]},
                         sheet={"players": [{"player": "MIA02", "bbr_id": "mia02", "status": "under_contract",
                                             "schedule": {"2005-06": 700_000}}]})
        d._consent_book = HolderBook()
        self.desk = d
        self.trade = {"partner": LAKERS, "miami_out": ["MIA02"], "miami_in": ["EB01"], "picks_out": [], "picks_in": []}

    def test_the_miami_desk_asks_each_holder_about_the_right_rosters(self):
        rec = RecordingChance()
        with mock.patch.object(trades, "consent_chance", rec):
            rows = self.desk.consent_rows(self.trade)
        by = {r["bbr_id"]: r for r in rows}
        self.assertEqual((by["eb01"]["held_by"], by["eb01"]["to"]), (LAKERS, MIAMI))
        self.assertEqual((by["mia02"]["held_by"], by["mia02"]["to"]), (MIAMI, LAKERS))
        calls = {c["bbr"]: c for c in rec.calls}
        self.assertEqual((calls["eb01"]["stay"], calls["eb01"]["new"]), (LAKERS, MIAMI))
        self.assertEqual(sorted(calls["eb01"]["stay_roster"]), ["eb01", "lak02"])                     # the Lakers before
        self.assertEqual(sorted(calls["eb01"]["new_roster"]), sorted(["eb01", trades.WADE_BBR]))      # Miami after
        self.assertEqual(sorted(calls["mia02"]["stay_roster"]), sorted(["mia02", trades.WADE_BBR]))   # Miami before
        self.assertEqual(sorted(calls["mia02"]["new_roster"]), ["lak02", "mia02"])                    # the Lakers after

    def test_the_miami_desk_runs_the_real_chance(self):
        rows = self.desk.consent_rows(self.trade)
        for r in rows:
            self.assertTrue(trades.CONSENT_LIMITS[0] <= r["p"] <= trades.CONSENT_LIMITS[1])
            self.assertEqual(r["stay"]["club"], r["held_by"])
            self.assertEqual(r["move"]["club"], r["to"])
            self.assertIn("P(consent)", r["basis"])

    def test_the_league_desk_asks_each_holder_about_the_right_rosters(self):
        d = league_trades.LeagueTradeDesk.__new__(league_trades.LeagueTradeDesk)
        d.root, d.assets, d.consent = Path(self.tmp.name), self.assets, HolderBook()
        d.contracts = {"eb01": {"player": "EB01", "schedule": {"2005-06": 800_000}}, "bos01": {"player": "BOS01", "schedule": {"2005-06": 800_000}}}
        d.rosters = {LAKERS: [{"bbr_id": "eb01"}, {"bbr_id": "lak02"}], BOSTON: [{"bbr_id": "bos01"}, {"bbr_id": "bos02"}]}
        rec = RecordingChance()
        with mock.patch.object(league_trades, "consent_chance", rec):
            rows = d.consent_rows(LAKERS, ["eb01"], BOSTON, ["bos01"])
        self.assertEqual([(r["bbr_id"], r["held_by"], r["to"], r["p"]) for r in rows], [("eb01", LAKERS, BOSTON, 0.5)])
        self.assertEqual(sorted(rec.calls[0]["stay_roster"]), ["eb01", "lak02"])
        self.assertEqual(sorted(rec.calls[0]["new_roster"]), ["bos02", "eb01"])


class NewlySignedTests(StandIn):
    """cbafaq05 Q88: no club trades a player signed in the league year before three months or December 15, whichever is
    later (30 days for a signed first-round pick), so consent is never asked of a player who may not be traded at all."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        re_signings(cls.root)

    def test_a_rest_of_season_signing_is_newly_signed(self):
        rows = trades.in_season_signings("2005-06", "2005-11-30", self.root, MIAMI)
        self.assertEqual({b: r["date"] for b, r in rows.items()},
                         {"ros01": "2005-11-15", "ros02": "2005-11-15", "ros03": "2005-11-25", "ren02": "2005-11-20"})
        self.assertNotIn("ros03", trades.in_season_signings("2005-06", "2005-11-20", self.root, MIAMI))
        cba = trades.read_json(trades.CBA_PATH, ROOT)
        self.assertIn("2006-02-15", trades.signing_block(rows["ros01"], "2006-02-14", "2005-06", cba))
        self.assertIsNone(trades.signing_block(rows["ros01"], "2006-02-15", "2005-06", cba))
        self.assertEqual(trades.IN_SEASON_SIGNED_FROM, trades.CONSENT_FROM)

    def test_the_league_desk_never_moves_a_newly_signed_player(self):
        d = league_trades.LeagueTradeDesk.__new__(league_trades.LeagueTradeDesk)
        d.on, d.season = "2005-12-20", "2005-06"
        d.cba = {"trades": {"signed_first_round_pick_restriction_days": {"days": 30}}}
        d.signings = {"new01": {"date": "2005-09-30", "kind": "signing"}, "rk01": {"date": "2005-07-20", "kind": "rookie_signing"}}
        self.assertIn("not tradable until", d.blocked("new01"))
        self.assertIsNone(d.blocked("rk01"))                          # a signed pick waits 30 days only
        self.assertIsNone(d.blocked("old01"))
        d.contracts = {b: {"player": b.upper(), "schedule": {"2005-06": 1_000_000}} for b in ("new01", "old01", "old02")}
        self.assertIsNone(d.evaluate(LAKERS, ["new01"], BOSTON, ["old02"]))
        d.rosters = {LAKERS: [{"bbr_id": b, "minutes": 100, "games": 10} for b in ("new01", "old01")]}
        self.assertEqual([g for g, _ in d._packages(LAKERS)], [["old01"]])
        d.on = "2005-12-30"
        self.assertIsNone(d.blocked("new01"))
        self.assertEqual(league_trades.NEWLY_SIGNED_FROM, trades.CONSENT_FROM)

    def test_the_live_holders_are_newly_signed_until_late_december(self):
        signed = trades.market_signings("2005-06", "2005-11-07", ROOT, exclude=MIAMI)
        cba = trades.read_json(trades.CBA_PATH, ROOT)
        for b in ("arizatr01", "elyme01", "collini01"):
            with self.subTest(player=b):
                self.assertEqual(signed[b]["date"], "2005-09-30")
                self.assertIn("not tradable until 2005-12", trades.signing_block(signed[b], "2005-11-07", "2005-06", cba))


def holder_row(b="eb01", p=0.6, rights="early_bird", to=MIAMI):
    return {"player": b.upper(), "bbr_id": b, "held_by": LAKERS, "to": to, "rights": rights, "seasons": 2, "p": p,
            "basis": f"{b.upper()}: test basis"}


class PacketTests(unittest.TestCase):
    def test_options_fold_each_consent_after_the_clubs_agree(self):
        opts = trades.consent_options(0.7, [holder_row("a01", 0.6), holder_row("b01", 0.9)])
        self.assertAlmostEqual(sum(opts.values()), 1.0, places=12)
        self.assertAlmostEqual(opts["decline"], 0.3)
        self.assertAlmostEqual(opts["accept"], 0.7 * 0.6 * 0.9, places=6)
        self.assertAlmostEqual(opts[trades.REFUSED + "a01"], 0.7 * 0.4, places=6)
        self.assertAlmostEqual(opts[trades.REFUSED + "b01"], 0.7 * 0.6 * 0.1, places=6)
        self.assertEqual(trades.refused_by(trades.REFUSED + "b01"), "b01")
        self.assertIsNone(trades.refused_by("decline"))

    def desk(self, on, rows=None):
        d = trades.TradeDesk.__new__(trades.TradeDesk)
        d.on, d.root, d.season = on, ROOT, "2005-06"
        d.errors = lambda trade, ignore_timing=False: []
        d.fits_partner = lambda trade: True
        d.valuation = lambda trade: {"partner": LAKERS, "posture": "middle", "objective_gain": 0.2, "miami_gain": 0.1,
                                     "partner_gain": 0.2, "dump": False, "shed": 0, "untouchable": []}
        d.trade_id = lambda trade: f"{on}-test"
        if rows is not None:
            d.consent_rows = lambda trade: rows
        return d

    def test_the_trade_packet_carries_the_consent_and_names_the_rule(self):
        trade = {"partner": LAKERS, "miami_out": ["MIA02"], "miami_in": ["EB01"], "picks_out": [], "picks_in": []}
        packet, v = self.desk(DAY, [holder_row(p=0.5)]).acceptance_packet(trade)
        self.assertEqual(decision_errors(packet), [])
        p = trades.acceptance({"objective_gain": 0.2})
        self.assertAlmostEqual(packet["options"]["accept"], round(p * 0.5, 6), places=5)
        self.assertIn(trades.REFUSED + "eb01", packet["options"])
        self.assertIn("must consent", packet["question"])
        self.assertIn("trade_consent_one_year_contract", packet["basis"])
        self.assertIn("cbafaq05 Q83", packet["basis"])
        self.assertEqual((v["club_accept"], v["consent"][0]["bbr_id"]), (p, "eb01"))
        self.assertFalse(trades.plausible(packet, dict(v, consent=[holder_row(p=0.3)])))   # a holder who would refuse: not proposed
        self.assertTrue(trades.plausible(packet, v))

    def test_before_the_gate_no_consent_is_asked(self):
        trade = {"partner": LAKERS, "miami_out": ["MIA02"], "miami_in": ["EB01"], "picks_out": [], "picks_in": []}
        d = self.desk("2005-10-31")                                     # the real consent_rows: no book before CONSENT_FROM
        self.assertIsNone(d.consent_book())
        packet, v = d.acceptance_packet(trade)
        self.assertEqual(set(packet["options"]), {"accept", "decline"})
        self.assertNotIn("consent", v)
        self.assertNotIn("consent", packet["question"])

    def test_an_offer_completed_at_once_never_moves_a_holder(self):
        class Book:
            def status(self, b, club, name=None):
                return {"holds": b == "eb01"}
        d = self.desk(DAY)
        d._consent_book = Book()
        d.resolve = lambda name, trade: {"bbr_id": name.lower()}
        self.assertTrue(d.needs_consent({"partner": LAKERS, "miami_out": ["MIA02"], "miami_in": ["EB01"]}))
        self.assertFalse(d.needs_consent({"partner": LAKERS, "miami_out": ["MIA02"], "miami_in": ["NEW01"]}))


class MiamiFlowTests(unittest.TestCase):
    """`run_trade.py`: a drawn refusal leaves the trade declined and prints on the trade's own line; a drawn acceptance
    completes it and marks the rights lost for the next summer."""

    def setUp(self):
        from scripts import run_trade
        self.rt = run_trade
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.folder = self.root / run_trade.TRADES
        self.folder.mkdir(parents=True)
        self.notes = []
        patches = [mock.patch.object(run_trade.signing, "Writer"), mock.patch.object(run_trade.signing, "phase_note_for"),
                   mock.patch.object(run_trade.signing, "note_event", side_effect=lambda w, rel, day, text, *a, **k: self.notes.append(text)),
                   mock.patch.object(run_trade.signing, "apply_trade"), mock.patch.object(run_trade.signing, "refresh_finance"),
                   mock.patch.object(run_trade, "FrontOffice"), mock.patch.object(run_trade, "Market"),
                   mock.patch.object(run_trade, "TradeDesk"), mock.patch.object(run_trade, "scan_due", return_value=None)]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        run_trade.TradeDesk.return_value.errors.return_value = []

    def tearDown(self):
        self.tmp.cleanup()

    def proposal(self, outcome):
        record = {"trade_id": f"{DAY}-test", "date": DAY, "status": "proposed", "kind": "trade",
                  "trade": {"partner": LAKERS, "miami_out": ["MIA02"], "miami_in": ["EB01"], "picks_out": [], "picks_in": []},
                  "valuation": {"club_accept": 0.6, "consent": [holder_row()]}, "decision_event": f"trade-{DAY}-test",
                  "answer": None, "applied": None}
        (self.folder / f"{record['trade_id']}.json").write_text(json.dumps(record), encoding="utf-8")
        (self.folder / f"trade-{DAY}-test.decision.result.json").write_text(json.dumps({"outcome": outcome}), encoding="utf-8")
        return record

    def test_a_refusal_voids_the_trade_and_prints_on_its_line(self):
        self.proposal(trades.REFUSED + "eb01")
        lines = self.rt.season_day(DAY, self.root)
        record = json.loads((self.folder / f"{DAY}-test.json").read_text(encoding="utf-8"))
        self.assertEqual((record["status"], record["answer"]["outcome"]), ("declined", trades.REFUSED + "eb01"))
        self.assertTrue(lines[0].startswith("Miami trade declined"))
        self.assertIn("EB01 refuses his consent", lines[0])
        self.assertIn("refuses his consent", self.notes[-1])
        self.rt.signing.apply_trade.assert_not_called()
        self.assertEqual(trades.lost_bird_rights(self.rt.SEASON, self.root), {})

    def test_consent_executes_and_marks_the_rights_lost(self):
        self.proposal("accept")
        lines = self.rt.season_day(DAY, self.root)
        record = json.loads((self.folder / f"{DAY}-test.json").read_text(encoding="utf-8"))
        self.assertEqual(record["status"], "completed")
        self.rt.signing.apply_trade.assert_called_once()
        self.assertTrue(lines[0].startswith("MIAMI TRADE"))
        self.assertIn("consents and loses his early bird rights", lines[0])
        lost = trades.lost_bird_rights(self.rt.SEASON, self.root)
        self.assertEqual((lost["eb01"]["club"], lost["eb01"]["rights"]), (MIAMI, "early_bird"))
        self.assertEqual(trades.lost_bird_rights(self.rt.SEASON, self.root, before=DAY), {})   # only trades before a date


    def test_a_voided_trade_reports_no_rights_lost(self):
        self.rt.TradeDesk.return_value.errors.return_value = ["no longer legal"]
        self.proposal("accept")
        lines = self.rt.season_day(DAY, self.root)
        record = json.loads((self.folder / f"{DAY}-test.json").read_text(encoding="utf-8"))
        self.assertEqual(record["status"], "void")
        self.assertNotIn("loses his", lines[0])
        self.assertIn("no rights were lost", lines[0])
        self.assertEqual(trades.lost_bird_rights(self.rt.SEASON, self.root), {})


class LeagueFlowTests(unittest.TestCase):
    """`league_trades.weekly`: the deal's one packet carries the consent; a refusal moves nobody; an accepted deal marks
    the holder's move with the rights he lost."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        packet = league_trades.LeagueTradeDesk.packet
        rows = [self.row("deal-a", BOSTON, ["aaa01"], "Utah Jazz", ["bbb01"], holder=True),
                self.row("deal-b", "Chicago Bulls", ["ccc01"], "Denver Nuggets", ["ddd01"], holder=True)]

        class Desk:
            season = "2005-06"

            def __init__(self, *a, **k):
                pass

            def proposals(self):
                return rows

            def packet(self, row):
                return packet(self, row)
        p = mock.patch.object(league_trades, "LeagueTradeDesk", Desk)
        p.start()
        self.addCleanup(p.stop)
        self.draws = self.root / league_trades.draws_dir("2005-06")

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def row(deal, a, a_ids, b, b_ids, holder=False):
        row = {"id": deal, "date": DAY, "clubs": [a, b], "a": {"club": a, "sends": [x.upper() for x in a_ids], "bbr_ids": a_ids, "salary": 1},
               "b": {"club": b, "sends": [x.upper() for x in b_ids], "bbr_ids": b_ids, "salary": 1},
               "gain": {a: 0.1, b: 0.1}, "accept": {a: 0.7, b: 0.7}, "both": 0.49}
        if holder:
            row["consent"] = [dict(holder_row(a_ids[0], 0.8), held_by=a, to=b)]
        return row

    def test_refusal_voids_and_consent_marks_the_rights_lost(self):
        written, executed = league_trades.weekly(self.root, DAY, market=object())
        self.assertEqual((written, executed), (["deal-a", "deal-b"], []))
        packet = json.loads((self.draws / "deal-a.decision.json").read_text(encoding="utf-8"))
        self.assertEqual(decision_errors(packet), [])
        self.assertEqual(set(packet["options"]), {"accept", "decline", trades.REFUSED + "aaa01"})
        self.assertIn("must consent", packet["question"])
        self.assertIn("cbafaq05 Q83", packet["basis"])
        (self.draws / "deal-a.decision.result.json").write_text(json.dumps({"outcome": trades.REFUSED + "aaa01"}))
        (self.draws / "deal-b.decision.result.json").write_text(json.dumps({"outcome": "accept"}))
        _, executed = league_trades.weekly(self.root, DAY, market=object())
        self.assertEqual(executed, ["deal-b"])                          # the refused deal moves nobody
        moves = json.loads((self.root / league_trades.ledger_path("2005-06")).read_text(encoding="utf-8"))["entries"]
        self.assertEqual({m["deal"] for m in moves}, {"deal-b"})
        marked = {m["bbr_id"]: m.get("consent") for m in moves}
        self.assertEqual(marked["ccc01"]["rights_lost"], "early_bird")
        self.assertIsNone(marked["ddd01"])
        lost = trades.lost_bird_rights("2005-06", self.root)
        self.assertEqual(set(lost), {"ccc01"})
        self.assertEqual(lost["ccc01"]["club"], "Denver Nuggets")

    def test_a_deal_without_a_holder_keeps_the_old_packet(self):
        row = self.row("deal-c", BOSTON, ["aaa01"], "Utah Jazz", ["bbb01"])
        packet = league_trades.LeagueTradeDesk.packet(None, row)
        self.assertEqual(packet["options"], {"accept": 0.49, "decline": 0.51})


class SummerMarketTests(unittest.TestCase):
    """The next summer market reads the lost rights: a Non-Bird free agent of his club, room or the mid-level above it."""

    def test_the_market_pays_him_as_a_non_bird_free_agent(self):
        from tests.test_free_agency_requests import DAY as MARKET_DAY, PRICES, market
        with tempfile.TemporaryDirectory() as tmp:
            m = market(tmp)
            self.assertEqual(m.means(MIAMI, "low01", MARKET_DAY, PRICES["low01"]), "bird")
            m.lost_bird = {"low01": {"club": MIAMI, "rights": "early_bird"}}
            limit = m.non_bird_limit("low01")
            self.assertEqual(limit, int(1.2 * 2_000_000))                 # 120% of his prior salary
            self.assertEqual(m.means(MIAMI, "low01", MARKET_DAY, limit), "non_bird")
            self.assertNotIn(m.means(MIAMI, "low01", MARKET_DAY, PRICES["low01"]), ("bird", "non_bird"))
            self.assertEqual(m.means(MIAMI, "mid01", MARKET_DAY, PRICES["mid01"]), "bird")   # the others keep theirs

    def test_his_own_hold_is_not_taken_from_the_room_that_pays_him(self):
        from tests.test_free_agency_requests import DAY as MARKET_DAY, HOLDS, market
        with tempfile.TemporaryDirectory() as tmp:
            m = market(tmp, pool=("star01", "low01"))                   # Miami: $30M payroll, low01's $3M hold, $50M cap
            self.assertEqual(m.holds(MIAMI, MARKET_DAY), HOLDS["low01"])
            m.lost_bird = {"low01": {"club": MIAMI, "rights": "early_bird"}}
            self.assertEqual(m.means(MIAMI, "low01", MARKET_DAY, 18_000_000), "cap_room")   # $20M of room once his hold goes
            self.assertEqual(m.most_affordable(MIAMI, "low01", MARKET_DAY, own=True), (20_000_000, "cap_room"))
            self.assertEqual(m.most_affordable(MIAMI, "star01", MARKET_DAY), (17_000_000, "cap_room"))   # another player: the hold stays
            m.lost_bird = {}
            self.assertEqual(m.means(MIAMI, "low01", MARKET_DAY, 18_000_000), "bird")

    def test_the_summer_market_never_trades_a_holder(self):
        m = object.__new__(fa.Market)
        m.traded = set()
        before = (fa.date.fromisoformat(fa.NEW_SIGNING_TRADABLE) - fa.timedelta(days=1)).isoformat()
        for route in ("minimum", "bird", "qualifying_offer", "mid_level", "cap_room"):   # this summer's one-year contracts
            self.assertFalse(m.tradable("x01", {"route": route, "date": fa.SIGN_FROM}, before))

    def test_the_flag_is_read_from_the_2006_summer_only(self):
        self.assertEqual(fa.LOST_BIRD_FROM, 2006)
        self.assertGreater(trades.CONSENT_FROM, "2005-07-01")         # no trade before the 2005 summer can carry a consent


class GateTests(unittest.TestCase):
    """Forward-only: every trade recorded before CONSENT_FROM replays unchanged."""

    def test_recorded_league_packets_rebuild_unchanged(self):
        n = 0
        for season in ("2003-04", "2004-05", "2005-06"):
            folder = ROOT / league_trades.draws_dir(season)
            for prop in sorted(folder.glob("*.proposal.json")) if folder.is_dir() else []:
                row = json.loads(prop.read_text(encoding="utf-8"))
                if row["date"] >= trades.CONSENT_FROM:
                    continue
                recorded = json.loads(prop.with_name(prop.name.replace(".proposal.json", ".decision.json")).read_text(encoding="utf-8"))
                self.assertEqual(league_trades.LeagueTradeDesk.packet(None, row), recorded, prop.name)
                n += 1
        self.assertGreater(n, 0)

    def test_recorded_miami_packets_rebuild_unchanged(self):
        """Each recorded Miami trade packet rebuilds byte-identical from its record's valuation through the real
        `acceptance_packet` and `consent_rows` on its date (no consent book before the gate)."""
        n = 0
        for path in sorted((ROOT / "career/Dwyane_Wade").glob("*/00_Team/Transactions/Trades/*.json")):
            if path.name.endswith((".decision.json", ".result.json")):
                continue
            record = json.loads(path.read_text(encoding="utf-8"))
            decision = path.with_name(f"{record.get('decision_event')}.decision.json")
            if record["date"] >= trades.CONSENT_FROM or not decision.is_file():
                continue
            d = trades.TradeDesk.__new__(trades.TradeDesk)
            d.on, d.root, d.season = record["date"], ROOT, path.parts[-5]
            d.errors = lambda trade, ignore_timing=False: []
            d.fits_partner = lambda trade: True
            d.valuation = lambda trade, v=record["valuation"]: v
            d.trade_id = lambda trade, i=record["trade_id"]: i
            self.assertIsNone(d.consent_book())
            packet, _ = d.acceptance_packet(record["trade"])
            self.assertEqual(packet, json.loads(decision.read_text(encoding="utf-8")), path.name)
            n += 1
        self.assertGreater(n, 0)
        for season in ("2004-05", "2005-06"):
            self.assertEqual(trades.lost_bird_rights(season, ROOT, before=trades.CONSENT_FROM), {})

    def test_the_league_desk_asks_no_consent_before_the_gate(self):
        d = league_trades.LeagueTradeDesk.__new__(league_trades.LeagueTradeDesk)
        d.consent = None
        self.assertEqual(d.consent_rows("A", ["x"], "B", ["y"]), [])


class LiveStatusTests(unittest.TestCase):
    """Read-only: the live records on November 1, 2005."""

    @classmethod
    def setUpClass(cls):
        cls.book = trades.ConsentBook(trades.CONSENT_FROM, ROOT)

    def test_trevor_ariza_holds_it_with_early_bird_rights(self):
        s = self.book.status("arizatr01", LAKERS, "Trevor Ariza")
        self.assertEqual((s["holds"], s["rights"], s["seasons"]), (True, "early_bird", 2))
        self.assertIn("qualifying offer accepted with Los Angeles Lakers on 2005-09-30", s["basis"])
        self.assertIn("signing with Detroit Pistons on 2004-07-14", s["basis"])

    def test_no_miami_player_holds_it(self):
        held = [p["player"] for b, p in self.book.sheet("2005-06").items() if self.book.status(b, MIAMI, p["player"])["holds"]]
        self.assertEqual(held, [])


if __name__ == "__main__":
    unittest.main()
