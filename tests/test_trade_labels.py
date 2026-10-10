"""Trade valuation labels and the pick horizon (runtime/trades.py, SEASON_LABELS_FROM; a dated fix).

From the second season a player's production prior is the previous simulated season and club records are its final
simulated standings, but the basis text kept naming 2002-03 and 2003-04, the season's own June first was regressed a year
as if it were next season's, and a renamed club found no row in standings keyed by its old name. From SEASON_LABELS_FROM
the text names the seasons actually read, a renamed club keeps its record and the season's own pick is unregressed; before
it every string and value is the recorded one. The rule's tests run on stand-in assets in a temporary root; the replay
tests read the live trade records (read-only) and rebuild every one, whatever its date, so a gate placed on or before a
recorded trade fails them.
"""
from datetime import date, timedelta
import json
import math
from pathlib import Path
import re
import tempfile
import unittest

from runtime import trades

ROOT = Path(__file__).resolve().parents[1]
GATE = trades.SEASON_LABELS_FROM
BEFORE = (date.fromisoformat(GATE) - timedelta(days=1)).isoformat()
MIAMI, ATLANTA, CHARLOTTE = "Miami Heat", "Atlanta Hawks", "Charlotte Bobcats"
OLD_NAME, RENAMED = "New Orleans Hornets", "New Orleans/Oklahoma City Hornets"   # seasons.CLUB_RENAMES, 2005-06
STANDINGS = {MIAMI: {"wins": 56, "losses": 26}, ATLANTA: {"wins": 20, "losses": 62},
             "Detroit Pistons": {"wins": 60, "losses": 22}}   # Miami's raw slot: 2 (one worse record)
PICK_2006, PICK_2007 = {"year": 2006, "round": 1}, {"year": 2007, "round": 1}


def totals(games, per_game_points):
    """Closed-game totals in the shape `Assets._closed_totals` builds."""
    t = {k: 0 for k in ("offensive_rebounds", "defensive_rebounds", "assists", "steals", "blocks", "field_goals_attempted",
                        "field_goals_made", "free_throws_attempted", "free_throws_made", "turnovers")}
    return dict(t, games=games, minutes=30.0 * games, points=per_game_points * games)


class FakeValuation:
    mid_level = 5_000_000

    def __init__(self, season, priors):
        self.season, self._priors = season, priors

    def value(self, bbr):
        return self._priors.get(bbr)

    def age(self, bbr):
        return 27

    def market_price(self, value, bbr):
        return 2_000_000

    def minimum(self, service):
        return 800_000


def assets(on, season, root, priors=None, closed=None, valuation_season=None, standings=STANDINGS):
    a = trades.Assets.__new__(trades.Assets)
    a.on, a.season, a.root = on, season, Path(root)
    a.valuation = FakeValuation(valuation_season or season, priors or {})
    a.standings = dict(standings) if season == trades.SEASON else a.under_season_names(dict(standings))   # as __init__
    a._season_totals = closed or {}
    a._stance = {}
    return a


def player(bbr, season="2005-06"):
    return {"player": bbr.upper(), "bbr_id": bbr, "status": "under_contract", "schedule": {season: 1_000_000},
            "amount_kind": {season: "contract_salary"}}


class StandIn(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        close = self.root / "career/Dwyane_Wade/2004-05/season_close.json"    # 2004-05 closed: its totals are simulated
        close.parent.mkdir(parents=True)
        close.write_text("{}", encoding="utf-8")
        self.priors = {"both01": 12.0, "prior01": 9.0}
        self.closed = {"both01": totals(30, 15.0), "new01": totals(10, 8.0)}

    def later(self, on, **kw):
        return assets(on, "2005-06", self.root, self.priors, self.closed, **kw)

    def basis(self, a, bbr):
        return a.player_value(player(bbr, a.season))["basis"]


class BeforeTheGateTests(StandIn):
    """Every string and value is the recorded one, in every season."""

    def test_a_later_season_keeps_the_recorded_production_words(self):
        a = self.later(BEFORE)
        value = a.form_value("both01")
        self.assertEqual(self.basis(a, "both01"), f"production value {value:.1f} (2002-03 blended with closed 2003-04 games)")
        self.assertEqual(self.basis(a, "prior01"), "production value 9.0 (2002-03 blended with closed 2003-04 games)")
        self.assertEqual(self.basis(a, "none01"), "no 2002-03 evidence: production counted at replacement")

    def test_the_first_season_before_form_keeps_its_words(self):
        a = assets("2003-11-01", "2003-04", self.root, {"x01": 9.0})
        self.assertEqual(self.basis(a, "x01"), "2002-03 production value 9.0")

    def test_the_season_s_own_pick_is_regressed_a_year_as_recorded(self):
        got = self.later(BEFORE).pick_value(PICK_2006, MIAMI, miami_own=True)
        self.assertEqual(got, {"value": round(trades.TOP_PICK_VALUE * math.exp(-trades.PICK_DECAY * 11.5), 3),
                               "slot": 12.5, "basis": "Miami Heat 56 wins in 2002-03; 2006 first regressed 1 year(s)"})
        self.assertIn("2005 first regressed 1 year(s)", assets("2005-01-24", "2004-05", self.root).pick_value(
            {"year": 2005, "round": 1}, MIAMI)["basis"])                      # 2004-05 as recorded
        self.assertIn("2004 first regressed 0 year(s)", assets("2004-01-10", "2003-04", self.root).pick_value(
            {"year": 2004, "round": 1}, MIAMI)["basis"])                      # 2003-04 was already right

    def test_a_club_without_a_row_keeps_the_recorded_words(self):
        self.assertEqual(self.later(BEFORE).pick_value(PICK_2006, CHARLOTTE)["basis"],
                         "Charlotte Bobcats 41 wins in 2002-03; 2006 first regressed 1 year(s)")

    def test_a_renamed_club_finds_no_row_as_recorded(self):
        a = self.later(BEFORE, standings=dict(STANDINGS, **{OLD_NAME: {"wins": 55, "losses": 27}}))
        self.assertEqual((OLD_NAME in a.standings, RENAMED in a.standings), (True, False))
        self.assertEqual(a.posture(RENAMED), "rebuilding")                  # the expansion branch, as recorded
        self.assertEqual(a.pick_value(PICK_2006, RENAMED)["basis"], f"{RENAMED} 41 wins in 2002-03; 2006 first regressed 1 year(s)")


class FromTheGateTests(StandIn):
    """The text names the seasons read; the season's own pick is unregressed."""

    def test_the_production_basis_names_the_seasons_read(self):
        a = self.later(GATE)
        value = a.form_value("both01")
        self.assertEqual(self.basis(a, "both01"),
                         f"production value {value:.1f} (2004-05 simulated season blended with closed 2005-06 games)")
        self.assertEqual(self.basis(a, "prior01"), "2004-05 simulated season production value 9.0")   # no closed game yet
        new = a.form_value("new01")
        self.assertEqual(self.basis(a, "new01"), f"production value {new:.1f} (closed 2005-06 games; no 2004-05 simulated season evidence)")
        self.assertEqual(self.basis(a, "none01"),
                         "no 2004-05 simulated season or closed 2005-06 evidence: production counted at replacement")

    def test_a_prior_season_not_closed_by_the_career_is_named_plainly(self):
        a = assets(GATE, "2005-06", self.root / "elsewhere", self.priors, self.closed)
        self.assertEqual(a.evidence_season(), ("2004-05", False))
        self.assertIn("(2004-05 blended with closed 2005-06 games)", self.basis(a, "both01"))

    def test_the_prior_follows_the_valuation_s_season(self):
        """In June the valuation prices the coming season, so its prior is the season just closed."""
        close = self.root / "career/Dwyane_Wade/2005-06/season_close.json"
        close.parent.mkdir(parents=True)
        close.write_text("{}", encoding="utf-8")
        a = self.later(GATE, valuation_season="2006-07")
        self.assertIn("(2005-06 simulated season blended with closed 2005-06 games)", self.basis(a, "both01"))

    def test_the_first_season_still_reads_2002_03(self):
        a = assets(GATE, "2003-04", self.root, {"x01": 9.0}, {"x01": totals(20, 12.0)})
        self.assertEqual((a.evidence_season(), a.record_season()), (("2002-03", False), ("2002-03", False)))
        value = a.form_value("x01")
        self.assertEqual(self.basis(a, "x01"), f"production value {value:.1f} (2002-03 blended with closed 2003-04 games)")
        self.assertEqual(a.pick_value({"year": 2004, "round": 1}, MIAMI)["basis"], "Miami Heat 56 wins in 2002-03; 2004 first regressed 0 year(s)")

    def test_the_season_s_own_pick_is_unregressed_and_next_season_s_regressed_one_year(self):
        a = self.later(GATE)
        own, after = a.pick_value(PICK_2006, MIAMI, miami_own=True), a.pick_value(PICK_2007, MIAMI, miami_own=True)
        self.assertEqual(own["basis"], "Miami Heat 56 wins in 2004-05 (simulated); 2006 first regressed 0 year(s)")
        self.assertEqual(own["slot"], 2 + trades.MIAMI_PICK_PESSIMISM)
        self.assertEqual(after["basis"], "Miami Heat 56 wins in 2004-05 (simulated); 2007 first regressed 1 year(s)")
        self.assertEqual(after["slot"], 12.5)
        self.assertIn("2005 first regressed 0 year(s)", a.pick_value({"year": 2005, "round": 1}, MIAMI)["basis"])   # a past year

    def test_a_club_without_a_row_says_so(self):
        self.assertEqual(self.later(GATE).pick_value(PICK_2006, CHARLOTTE)["basis"],
                         "Charlotte Bobcats no 2004-05 record (placed at 41 wins); 2006 first regressed 0 year(s)")
        self.assertEqual(self.later(GATE).stance_basis(CHARLOTTE), "no 2004-05 record: a club without a previous season builds")

    def test_a_renamed_club_keeps_its_record(self):
        row = {"wins": 55, "losses": 27}
        a = self.later(GATE, standings=dict(STANDINGS, **{OLD_NAME: row}))
        self.assertEqual((a.standings.get(RENAMED), OLD_NAME in a.standings), (row, False))
        self.assertEqual(a.posture(RENAMED), "contending")
        got = a.pick_value(PICK_2006, RENAMED)
        self.assertEqual(got["basis"], f"{RENAMED} 55 wins in 2004-05 (simulated); 2006 first regressed 0 year(s)")
        self.assertEqual(got["slot"], 2)                                     # one worse record (Atlanta's 20)
        self.assertEqual(a.stance_basis(RENAMED), "2004-05 simulated record and the age of its core")
        back = assets("2007-11-01", "2007-08", self.root, standings={RENAMED: row})   # renamed back in 2007-08
        self.assertEqual(back.standings, {OLD_NAME: row})

    def test_a_real_desk_finds_the_renamed_hornets(self):
        """Read-only: a real `Assets` on the gate reads the Hornets' 2004-05 row under their 2005-06 name."""
        from runtime.season_market import for_date
        from runtime.seasons import dates, season_of_date
        from runtime.standings import standings_on
        if season_of_date(GATE) != "2005-06":
            self.skipTest("the rename falls in 2005-06 only")
        row = standings_on(dates("2004-05", ROOT)["regular_season_end"], ROOT, "2004-05")[OLD_NAME]
        a = trades.Assets(GATE, for_date(GATE, ROOT), ROOT)
        self.assertEqual((a.standings.get(RENAMED), OLD_NAME in a.standings), (row, False))
        self.assertEqual(a.pick_value(PICK_2006, RENAMED)["basis"],
                         f"{RENAMED} {row['wins']} wins in 2004-05 (simulated); 2006 first regressed 0 year(s)")


class StanceBasisTests(StandIn):
    """The partner's stance words in Miami's acceptance packet."""

    def packet(self, on, partner=ATLANTA, with_assets=True):
        d = trades.TradeDesk.__new__(trades.TradeDesk)
        d.on, d.root, d.season = on, self.root, "2005-06"
        d._consent_book = None
        d.errors = lambda trade, ignore_timing=False: []
        d.fits_partner = lambda trade: True
        d.valuation = lambda trade: {"posture": "rebuilding", "objective_gain": 0.1, "untouchable": [], "dump": False,
                                     "miami_gain": 0.2}
        d.trade_id = lambda trade: f"{on}-0000000000"
        if with_assets:
            d.assets = self.later(on)
        packet, _ = d.acceptance_packet({"partner": partner, "miami_out": ["X"], "miami_in": ["Y"], "picks_out": [], "picks_in": []})
        return packet["basis"]

    def test_before_the_gate_the_recorded_words_without_reading_assets(self):
        self.assertIn("Atlanta Hawks stance rebuilding (2002-03 record and the age of its core);", self.packet(BEFORE, with_assets=False))

    def test_from_the_gate_the_standings_season_read(self):
        self.assertIn("Atlanta Hawks stance rebuilding (2004-05 simulated record and the age of its core);", self.packet(GATE))
        self.assertIn(f"{CHARLOTTE} stance rebuilding (no 2004-05 record: a club without a previous season builds);",
                      self.packet(GATE, partner=CHARLOTTE))


OLD_WORDS = ("wins in 2002-03", "(2002-03 blended with closed 2003-04 games)", "2002-03 production value",
             "no 2002-03 evidence", "(2002-03 record and the age of its core)")


def recorded_trades():
    """(path, record) of every Miami trade record, whatever its date."""
    for path in sorted((ROOT / "career/Dwyane_Wade").glob("*/00_Team/Transactions/Trades/*.json")):
        if path.name.endswith((".decision.json", ".result.json")):
            continue
        yield path, json.loads(path.read_text(encoding="utf-8"))


def real_assets(on):
    from runtime.season_market import for_date
    return trades.Assets(on, for_date(on, ROOT), ROOT)


class ReplayTests(unittest.TestCase):
    """Read-only: every recorded Miami trade rebuilds its recorded words and values, before the gate and after it."""

    def test_recorded_packets_rebuild_unchanged(self):
        """Before the gate the desk writes the recorded stance words without reading Assets (no `assets` here); from it
        through a real `Assets` on the record's date."""
        n = 0
        for path, record in recorded_trades():
            decision = path.with_name(f"{record.get('decision_event')}.decision.json")
            if not decision.is_file():
                continue
            d = trades.TradeDesk.__new__(trades.TradeDesk)
            d.on, d.root, d.season = record["date"], ROOT, path.parts[-5]
            if record["date"] >= GATE:
                d.assets = real_assets(record["date"])
            d.errors = lambda trade, ignore_timing=False: []
            d.fits_partner = lambda trade: True
            d.valuation = lambda trade, v=record["valuation"]: v
            d.trade_id = lambda trade, i=record["trade_id"]: i
            d.consent_rows = lambda trade, rows=record["valuation"].get("consent") or []: rows
            packet, _ = d.acceptance_packet(record["trade"])
            self.assertEqual(packet, json.loads(decision.read_text(encoding="utf-8")), path.name)
            n += 1
        self.assertGreater(n, 0)

    def test_recorded_player_labels_rebuild_unchanged(self):
        """The label only: the value is read back from the recorded text, since recomputing it on a past date can
        differ by a tenth (closed results dated on the trade day count; a known drift outside this fix). A record from
        the gate on, after the first season, carries none of the words recorded before it."""
        n = 0
        for path, record in recorded_trades():
            rows = (record.get("valuation") or {}).get("miami_out", []) + (record.get("valuation") or {}).get("miami_in", [])
            if record["date"] >= GATE:
                if path.parts[-5] != trades.SEASON:
                    for row in rows:
                        self.assertFalse([w for w in OLD_WORDS if w in row["basis"]], path.name)
                        n += 1
                continue
            a = assets(record["date"], path.parts[-5], ROOT)
            for row in rows:
                found = re.search(r"production value (\d+\.\d)", row["basis"])
                self.assertEqual(a.form_basis(row["bbr_id"], float(found.group(1)) if found else None), row["basis"], path.name)
                n += 1
        self.assertGreater(n, 0)

    def test_recorded_picks_rebuild_unchanged(self):
        """Each recorded pick's value, slot and words through a real `Assets` on its date."""
        n = 0
        for path, record in recorded_trades():
            v = record.get("valuation") or {}
            rows = [(p, MIAMI, True) for p in v.get("picks_out", [])] + [(p, v.get("partner"), False) for p in v.get("picks_in", [])]
            if not rows:
                continue
            a = real_assets(record["date"])
            for row, club, own in rows:
                self.assertEqual(dict(a.pick_value(row["pick"], club, miami_own=own), pick=row["pick"]), row, path.name)
                n += 1
        self.assertGreater(n, 0)


class LeagueMatchTests(unittest.TestCase):
    """League trades read the season's agreement's salary rule from the gate (`league_trades.AGREEMENT_MATCH_FROM`):
    125% under the 2005 agreement in 2005-06, as Miami's desk and the summer market already read it; every deal before
    it was searched and recorded under the 1999 rule's 115%."""

    def desk(self, on, season="2005-06"):
        from runtime.league_trades import LeagueTradeDesk
        d = LeagueTradeDesk.__new__(LeagueTradeDesk)
        d.on, d.season, d.root = on, season, ROOT
        d.payroll, d._caps = {ATLANTA: 70_000_000}, {ATLANTA: 49_500_000}       # over the cap: the matching rule applies
        return d

    def test_the_1999_rule_before_the_gate(self):
        from runtime.league_trades import salary_rule
        d = self.desk(BEFORE)
        self.assertEqual(salary_rule(BEFORE, "2005-06"), ("1999", 1.15, 100000))
        self.assertFalse(d.legal(ATLANTA, 10_000_000, 12_000_000))           # 120% plus nothing: over 115% + $100,000
        self.assertTrue(d.legal(ATLANTA, 10_000_000, 11_600_000))

    def test_the_seasons_agreement_from_the_gate(self):
        from runtime.league_trades import salary_rule
        d = self.desk(GATE)
        self.assertEqual(salary_rule(GATE, "2005-06"), ("2005", 1.25, 100000))
        self.assertTrue(d.legal(ATLANTA, 10_000_000, 12_600_000))
        self.assertFalse(d.legal(ATLANTA, 10_000_000, 12_700_000))
        self.assertEqual(salary_rule(GATE, "2004-05"), ("1999", 1.15, 100000))      # a 1999-agreement season keeps 115%
        self.assertFalse(self.desk(GATE, "2004-05").legal(ATLANTA, 10_000_000, 12_000_000))

    def test_the_packet_names_the_rule_it_applied(self):
        row = {"id": "x", "date": BEFORE, "a": {"club": ATLANTA, "sends": ["A"]}, "b": {"club": MIAMI, "sends": ["B"]},
               "both": 0.5, "gain": {}, "accept": {}}
        from runtime.league_trades import LeagueTradeDesk
        self.assertIn("; 1999 salary rule met; ", LeagueTradeDesk.packet(None, row)["basis"])
        self.assertIn("; 2005 salary rule met; ", LeagueTradeDesk.packet(None, dict(row, date=GATE))["basis"])

    def test_recorded_league_trades_before_the_gate_name_the_1999_rule(self):
        n = 0
        for path in sorted(ROOT.glob("career/Dwyane_Wade/*/League/Trade_Draws/*league-trade-*.decision.json")):
            packet = json.loads(path.read_text(encoding="utf-8"))
            if packet["date"] < GATE:
                self.assertIn("1999 salary rule met", packet["basis"], path.name)
                n += 1
        self.assertGreater(n, 0)


if __name__ == "__main__":
    unittest.main()
