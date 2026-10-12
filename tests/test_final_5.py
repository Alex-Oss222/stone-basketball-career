"""Final audit fix 5 (the June 2006 integration review, R5): the rookie-scale qualifying offer by draft position.

From the 2006 summer a first-round pick finishing his rookie-scale contract is tendered his fourth-season salary raised
by the scale's percentage for his pick (both agreements' rule: 1999 FAQ Q34, cbafaq05 Q37 and Q42), not 125% of it.
The 2004 and 2005 summers' recorded offers stand."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from runtime import consultations as C
from runtime import free_agency_2004 as F

ROOT = Path(__file__).resolve().parents[1]

# The 2002-03 rookie scale's 120% qualifying offers (SalarySwish, https://www.salaryswish.com/rookie-scale/2003) for the
# 2002 class's restricted free agents of the 2006 market, on their recorded 2005-06 salaries.
SCALE_2006 = {"mingya01": (1, 5_594_906, 7_273_378), "dunlemi02": (3, 4_506_261, 5_912_214),
              "wilcoch01": (8, 2_812_239, 3_790_898), "butleca01": (10, 2_461_617, 3_352_722),
              "jeffrja01": (11, 2_433_824, 3_331_905), "jonesfr01": (14, 2_328_843, 3_239_421),
              "dixonju01": (17, 2_070_835, 2_924_019), "salmojo01": (26, 1_669_001, 2_463_445),
              "dickada01": (28, 1_612_587, 2_402_755)}


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def june_30(year):
    """The market's June 30 as the code runs it now: recorded draws where they exist, any other left pending, every
    write refused. Returns the market."""
    def recorded(root, packet):
        path = Path(root) / F.DRAWS / f"{packet['event_id']}.decision.result.json"
        return json.loads(path.read_text(encoding="utf-8"))["outcome"] if path.is_file() else None

    def refuse(*args, **kwargs):
        raise AssertionError("the market tried to write")

    with F.year_context(year, ROOT), mock.patch.object(F, "_draw", recorded), mock.patch.object(F, "_write", refuse), \
            mock.patch.object(C, "ask", refuse):
        m = F.Market(ROOT, F.OPTIONS_DATE)
        m.store = False
        m.run()
        m.record_path = ROOT / F.RECORD
    return m


class ScaleTableTests(unittest.TestCase):
    def test_2002_first_round_is_recorded_with_the_scale(self):
        picks = F.first_round(2002, ROOT)
        self.assertEqual(picks["butleca01"], {"pick": 10, "qualifying_offer_raise_pct": 36.2})
        self.assertEqual(sorted(p["pick"] for p in picks.values()), list(range(1, 29)))    # No. 29 forfeited (Minnesota)
        old = {r["pick"]: r["qualifying_offer_raise_pct"] for r in read("library/2004/league/nba_2004_offseason_calendar.json")["rookie_scale_2004_first_round"]["value"]}
        new = {r["pick"]: r["qualifying_offer_raise_pct"] for r in read("library/2006/league/nba_2006_offseason_calendar.json")["rookie_scale_2006_first_round"]["value"]}
        for p in picks.values():                     # the 1999 table the class signed under, the same as the 2005 one
            self.assertEqual(p["qualifying_offer_raise_pct"], old[p["pick"]])
            self.assertEqual(p["qualifying_offer_raise_pct"], new[p["pick"]])

    def test_research_record_answers_each_question(self):
        rec = read("library/2006/league/nba_2006_rookie_scale_qualifying_offers.json")
        self.assertEqual([r["pick"] for r in rec["table"]], list(range(1, 31)))
        self.assertEqual((rec["table"][0]["qualifying_offer_raise_pct"], rec["table"][-1]["qualifying_offer_raise_pct"]), (30.0, 50.0))
        for q in rec["questions"].values():
            self.assertTrue(q["status"].startswith("sourced"))
            self.assertTrue(q["evidence"])

    def test_first_round_reads_the_2003_file_and_the_career_drafts(self):
        self.assertEqual(F.first_round(2003, ROOT)["fordtj01"], {"pick": 8, "qualifying_offer_raise_pct": 34.8})
        self.assertEqual(F.first_round(2004, ROOT)["howardw01"], {"pick": 1, "qualifying_offer_raise_pct": 30.0})
        self.assertEqual(len(F.first_round(2005, ROOT)), 30)
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(ValueError):
            F.first_round(2004, tmp)                 # no round recorded: refused, never the general offer


class AmountTests(unittest.TestCase):
    def test_scale_offer_by_pick(self):
        with F.year_context(2006, ROOT):
            cal = F.calendar(ROOT)
            picks = F.first_round(2002, ROOT)
            for b, (pick, prior, amount) in SCALE_2006.items():
                self.assertEqual(picks[b]["pick"], pick)
                self.assertEqual(F.qualifying_amount(prior, 4, cal, picks[b]["qualifying_offer_raise_pct"]), amount, b)
            self.assertEqual(F.qualifying_amount(2_461_617, 4, cal), 3_077_021)            # the general rule is unchanged

    def test_gate_by_summer(self):
        for year in (2004, 2005):
            with F.year_context(year, ROOT):
                self.assertEqual(F.scale_qualifying_picks(ROOT), {}, year)
        with F.year_context(2006, ROOT):
            scale = F.scale_qualifying_picks(ROOT)
        self.assertTrue(set(SCALE_2006) <= set(scale))
        self.assertEqual(scale["butleca01"]["pick"], 10)
        # 2003 picks whose fourth-year option was declined (Milicic, Banks) and rookies on a later contract (Ford, Monia)
        for b in ("milicda01", "banksma01", "fordtj01", "moniase01"):
            self.assertNotIn(b, scale)


class MarketTests(unittest.TestCase):
    def test_2006_june_30_tenders_the_scale_offer(self):
        m = june_30(2006)
        offers = {e["bbr_id"]: e for e in m.events if e["kind"] == "qualifying_offer"}
        self.assertEqual((offers["butleca01"]["amount"], offers["butleca01"]["rookie_scale_pick"]), (3_352_722, 10))
        self.assertEqual(m.qualifying["butleca01"], {"club": "Miami Heat", "amount": 3_352_722})
        for b, (pick, prior, amount) in SCALE_2006.items():
            if b in offers:
                self.assertEqual((offers[b]["amount"], offers[b]["rookie_scale_pick"]), (amount, pick), b)
        self.assertNotIn("dickada01", offers)        # priced below his bar under either offer
        for b, e in offers.items():
            if b not in SCALE_2006:
                self.assertNotIn("rookie_scale_pick", e)

    def test_2005_june_30_offers_are_the_recorded_ones(self):
        m = june_30(2005)
        now = sorted((e for e in m.events if e["kind"] == "qualifying_offer"), key=lambda e: e["bbr_id"])
        was = sorted((e for e in read(m.record_path.relative_to(ROOT))["events"] if e["kind"] == "qualifying_offer"), key=lambda e: e["bbr_id"])
        self.assertEqual(now, was)

    def test_2004_offer_amounts_are_the_recorded_ones(self):
        """The 2004 market no longer replays from today's inputs (docs/ROADMAP.md F1); every offer it recorded keeps
        its amount and gains no scale pick."""
        m = june_30(2004)
        now = {e["bbr_id"]: e for e in m.events if e["kind"] == "qualifying_offer"}
        for e in read(m.record_path.relative_to(ROOT))["events"]:
            if e["kind"] == "qualifying_offer":
                self.assertEqual(now[e["bbr_id"]]["amount"], e["amount"], e["bbr_id"])
                self.assertNotIn("rookie_scale_pick", now[e["bbr_id"]])


if __name__ == "__main__":
    unittest.main()
