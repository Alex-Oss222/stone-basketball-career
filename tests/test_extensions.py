"""Contract extensions for every club (runtime/extensions.py): the agreement's terms, eligibility, the club's call and
the player's draw, the two-phase packet then apply flow, the ledger carried by the rollover, the next summer's pool,
Wade's offer and reply, validation, and the gate that leaves every earlier season unchanged.

Scenario tests build a small scratch career (ledgers, option records, Miami's sheet) and patch only the heavy evidence
(`extensions.evidence_for`) and the start-of-day holders (`extensions.holders`); the live repository is read, never
written.
"""
from contextlib import nullcontext, redirect_stdout
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from runtime import extensions as ext
from tests import live_season

ROOT = Path(__file__).resolve().parents[1]
P = "career/Dwyane_Wade"
NOTE = "---\ntype: phase\nstatus: active\n---\n\n# Training camp\n\n## Player decisions\n\n## Events\n\n## Consequences\n"


def put(root, rel, data):
    path = Path(root) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data if isinstance(data, str) else json.dumps(data, indent=1), encoding="utf-8")


def read(root, rel):
    return json.loads((Path(root) / rel).read_text(encoding="utf-8"))


class FakeEvidence:
    """The interface `extensions.decide` reads, with fixed numbers."""

    def __init__(self, players, planning="2005-06", mid_level=5_000_000, tax=61_700_000, wins=None, gone=()):
        self.players, self.planning, self.mid_level, self.tax = players, planning, mid_level, tax
        self.win, self.gone = wins or {}, set(gone)

    def value(self, b):
        return (self.players.get(b) or {}).get("value")

    def market_price(self, value, b):
        return self.players[b]["price"]

    def age(self, b):
        return self.players[b].get("age", 27)

    def mpg(self, b):
        return self.players[b].get("mpg", 30.0)

    def line(self, b):
        return "82 games, 30.0 minutes (test line)"

    def service_first(self, b):
        return self.players[b].get("service", 4)

    def tier_maximum(self, service):
        return 12_000_000 if (service or 0) <= 6 else 14_400_000 if service <= 9 else 16_800_000

    def minimum(self, service):
        return 641_748

    def wins(self, club):
        return self.win.get(club, 41)

    def contender(self, club):
        return self.win.get(club, 41) >= 50

    def retired(self, b, season):
        return b in self.gone


def scratch():
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    rules = root / "library/2005/league/nba_2005_cba_rules.json"
    rules.parent.mkdir(parents=True)
    shutil.copy(ROOT / "library/2005/league/nba_2005_cba_rules.json", rules)
    return tmp, root


def option(bbr, player, club, season, deadline, decision="exercise"):
    return {"id": f"{season}-option-{bbr}-team_option", "club": club, "player": player, "bbr_id": bbr, "option_season": season,
            "kind": "team_option", "salary": 1, "deadline": deadline, "decision": decision, "applied": deadline}


def league_2005(root):
    """A 2005-06 career on October 31, 2005: a rookie-scale class, veterans and Miami's sheet."""
    put(root, f"{P}/2004-05/current_state.json", {"season": "2004-05", "current_date": "2005-10-01", "closed": True})
    put(root, f"{P}/2005-06/current_state.json", {"season": "2005-06", "current_date": "2005-10-31",
                                                 "current_note": "04_Training_Camp/note.md", "pending_player_decisions": []})
    put(root, f"{P}/2005-06/04_Training_Camp/note.md", NOTE)
    put(root, f"{P}/2004-05/League/option_decisions.json", {"decisions": [
        option("stoudam01", "Amar'e Stoudemire", "Phoenix Suns", "2005-06", "2004-10-31"),
        option("butleca01", "Caron Butler", "Miami Heat", "2005-06", "2004-10-31")]})
    put(root, f"{P}/2005-06/League/option_decisions.json", {"decisions": [
        option("milicda01", "Darko Milicic", "Detroit Pistons", "2006-07", "2005-10-31", "decline")]})
    put(root, "library/2003/league/nba_2003_contracts.json", {"clubs": {
        "Detroit Pistons": {"players": [{"player": "Ben Wallace", "bbr_id": "wallabe01", "status": "under_contract",
                                         "signed_date": "2000-08-03", "original_term_seasons": 6, "contract_text": "Signed a six-year contract."}]},
        "Houston Rockets": {"players": [{"player": "Cuttino Mobley", "bbr_id": "moblecu01", "status": "under_contract",
                                         "signed_date": "2000-08-02", "original_term_seasons": 6}]},
        "Los Angeles Lakers": {"players": [{"player": "Shaquille O'Neal", "bbr_id": "onealsh01", "status": "under_contract",
                                            "signed_date": "2000-10-13", "original_term_seasons": 3,
                                            "contract_text": "Signed a three-year extension with L.A. Lakers."}]},
        "Boston Celtics": {"players": [{"player": "Young Six", "bbr_id": "youngsi01", "status": "under_contract",
                                        "signed_date": "2002-08-01", "original_term_seasons": 6},
                                       {"player": "Short Deal", "bbr_id": "shortde01", "status": "under_contract",
                                        "signed_date": "2001-07-20", "original_term_seasons": 3}]}}})
    inv = "library/2003/league/nba_2003_contracts.json"
    put(root, f"{P}/2004-05/League/contracts.json", {"contracts": [
        {"player": "Ben Wallace", "bbr_id": "wallabe01", "club": "Detroit Pistons", "kind": "existing", "route": "existing",
         "schedule": {"2004-05": 6200000, "2005-06": 6700000}, "source": inv},
        {"player": "Cuttino Mobley", "bbr_id": "moblecu01", "club": "Houston Rockets", "kind": "existing", "route": "existing",
         "schedule": {"2004-05": 5884500, "2005-06": 6374875}, "source": inv},
        {"player": "Shaquille O'Neal", "bbr_id": "onealsh01", "club": "Los Angeles Lakers", "kind": "existing", "route": "existing",
         "schedule": {"2004-05": 27696430, "2005-06": 30642861}, "source": inv},
        {"player": "Young Six", "bbr_id": "youngsi01", "club": "Boston Celtics", "kind": "existing", "route": "existing",
         "schedule": {"2004-05": 3000000, "2005-06": 3200000}, "source": inv},
        {"player": "Short Deal", "bbr_id": "shortde01", "club": "Boston Celtics", "kind": "existing", "route": "existing",
         "schedule": {"2004-05": 2000000, "2005-06": 2100000}, "source": inv},
        {"player": "No Date", "bbr_id": "nodate01", "club": "Boston Celtics", "kind": "existing", "route": "existing",
         "schedule": {"2004-05": 2000000, "2005-06": 2200000},
         "source": "library/2004/league/nba_2004_05_salaries.json (reconstructed: no 2004 offseason move)"}]})
    carried = "league contract ledger 2004-05 (existing)"
    put(root, f"{P}/2005-06/League/contracts.json", {"contracts": [
        {"player": "Amar'e Stoudemire", "bbr_id": "stoudam01", "club": "Phoenix Suns", "kind": "existing", "route": "existing",
         "schedule": {"2005-06": 2589023}, "source": carried, "rookie_scale": True},
        {"player": "Darko Milicic", "bbr_id": "milicda01", "club": "Detroit Pistons", "kind": "existing", "route": "existing",
         "schedule": {"2005-06": 4135200}, "source": carried, "rookie_scale": True},
        {"player": "Ben Wallace", "bbr_id": "wallabe01", "club": "Detroit Pistons", "kind": "existing", "route": "existing",
         "schedule": {"2005-06": 6700000}, "source": carried},
        {"player": "Cuttino Mobley", "bbr_id": "moblecu01", "club": "Houston Rockets", "kind": "existing", "route": "existing",
         "schedule": {"2005-06": 6374875}, "source": carried},
        {"player": "Shaquille O'Neal", "bbr_id": "onealsh01", "club": "Los Angeles Lakers", "kind": "existing", "route": "existing",
         "schedule": {"2005-06": 30642861}, "source": carried},
        {"player": "Young Six", "bbr_id": "youngsi01", "club": "Boston Celtics", "kind": "existing", "route": "existing",
         "schedule": {"2005-06": 3200000}, "source": carried},
        {"player": "Short Deal", "bbr_id": "shortde01", "club": "Boston Celtics", "kind": "existing", "route": "existing",
         "schedule": {"2005-06": 2100000}, "source": carried},
        {"player": "No Date", "bbr_id": "nodate01", "club": "Boston Celtics", "kind": "existing", "route": "existing",
         "schedule": {"2005-06": 2200000}, "source": carried},
        {"player": "Long Deal", "bbr_id": "longde01", "club": "Boston Celtics", "kind": "existing", "route": "existing",
         "schedule": {"2005-06": 5000000, "2006-07": 5400000}, "source": carried},
        {"player": "Caron Butler", "bbr_id": "butleca01", "club": "Miami Heat", "kind": "existing", "route": "existing",
         "schedule": {"2005-06": 2461617}, "source": "Miami contract_schedules.json", "rookie_scale": True},
        {"player": "Mike James", "bbr_id": "jamesmi01", "club": "Miami Heat", "kind": "existing", "route": "existing",
         "schedule": {"2005-06": 3812749}, "source": "Miami contract_schedules.json"}]})
    put(root, f"{P}/2005-06/00_Team/Finances/contract_schedules.json", {"as_of": "2005-10-31", "team": "Miami Heat", "projection": [], "players": [
        {"player": "Caron Butler", "bbr_id": "butleca01", "status": "under_rookie_contract",
         "schedule": {"2003-04": 1804680, "2004-05": 1930680, "2005-06": 2461617},
         "amount_kind": {"2003-04": "contract_salary", "2004-05": "contract_salary", "2005-06": "contract_salary"},
         "signed_date": "2002-07-02", "original_term_seasons": 4},
        {"player": "Mike James", "bbr_id": "jamesmi01", "status": "under_contract",
         "schedule": {"2003-04": 3050199, "2004-05": 3431474, "2005-06": 3812749},
         "signed_date": "2003-07-17", "original_term_seasons": 3, "route": "early_bird"}]})
    put(root, f"{P}/2005-06/00_Team/Team/Roster/roster.json", {"players": [
        {"id": "caron_butler", "name": "Caron Butler", "bbr_id": "butleca01", "status": "under_contract"},
        {"id": "mike_james", "name": "Mike James", "bbr_id": "jamesmi01", "status": "under_contract"}]})


ROSTERS_2005 = {"stoudam01": "Phoenix Suns", "milicda01": "Detroit Pistons", "wallabe01": "Detroit Pistons",
                "moblecu01": "Houston Rockets", "onealsh01": "Los Angeles Lakers", "youngsi01": "Boston Celtics",
                "shortde01": "Boston Celtics", "nodate01": "Boston Celtics", "longde01": "Boston Celtics"}
EVIDENCE_2005 = {"stoudam01": {"value": 25, "price": 11_945_223, "age": 22},
                 "wallabe01": {"value": 18, "price": 8_004_556, "age": 31, "service": 10},
                 "moblecu01": {"value": 12, "price": 4_999_811, "age": 30, "service": 9},
                 "onealsh01": {"value": 20, "price": 13_835_054, "age": 33, "service": 14},
                 "butleca01": {"value": 10, "price": 3_037_758, "age": 25}}


def patched(held, ev):
    return (mock.patch.object(ext, "holders", return_value=held), mock.patch.object(ext, "evidence_for", return_value=ev),
            mock.patch("runtime.club_truth.holder", return_value=(None, "unsigned in the test")))


class Scenario(unittest.TestCase):
    held = (ROSTERS_2005, {"butleca01", "jamesmi01"})
    evidence = EVIDENCE_2005

    def setUp(self):
        self.tmp, self.root = scratch()
        league_2005(self.root)
        self.ev = FakeEvidence(dict(self.evidence), wins={"Phoenix Suns": 60})
        for p in patched(self.held, self.ev):
            p.start()
            self.addCleanup(p.stop)
        ext.clear_cache()
        ext._REPLAY.clear()

    def tearDown(self):
        self.tmp.cleanup()

    def record(self, season="2005-06"):
        return read(self.root, f"{P}/{season}/League/extension_decisions.json")

    def decision(self, bbr, season="2005-06"):
        return next(d for d in self.record(season)["decisions"] if d["bbr_id"] == bbr)

    def draw(self, bbr, outcome, season="2005-06"):
        packet = self.root / self.decision(bbr, season)["packet"]
        data = json.loads(packet.read_text())
        put(self.root, packet.with_name(packet.name.replace(".decision.json", ".decision.result.json")).relative_to(self.root),
            dict(data, kind="decision", outcome=outcome))

    def ledger(self, season="2005-06"):
        return {c["bbr_id"]: c for c in read(self.root, f"{P}/{season}/League/contracts.json")["contracts"]}


# -- the agreement's terms and the days --------------------------------------------------------------------------------------
class RuleTests(unittest.TestCase):
    def test_terms_match_the_sourced_file(self):
        r = ext.rules("2005-06", ROOT)
        self.assertEqual((r["rookie_new_seasons"], r["rookie_raise_pct"], r["veteran_total_seasons"]), (5, 10.5, 5))
        self.assertEqual((r["veteran_first_year_pct"], r["veteran_raise_pct"], r["free_agent_max_pct"]), (110.5, 10.5, 105))
        self.assertEqual((r["min_length"], r["years_after"], r["long_years_after"], r["after_extension"]), (4, 3, 4, 3))
        self.assertEqual((r["long_min_length"], r["long_signed_before"]), (6, "2005-07-01"))
        source = json.loads((ROOT / "library/2005/league/nba_2005_cba_rules.json").read_text())["extensions"]
        self.assertEqual(source["terms"]["source"], "cbafaq05")
        self.assertIn("Q52", source["terms"]["source_ref"])
        self.assertIsNone(ext.rules("2004-05", ROOT))                 # the 1999 agreement: no extension day falls there
        clause = source["option_clause"]                              # Q51: one option season, the last
        self.assertEqual((clause["status"], clause["source"], clause["source_ref"]), ("sourced", "cbafaq05", "Q51"))
        self.assertEqual((r["max_option_seasons"], r["option_season"]), (1, "last"))

    def test_days_start_on_the_gate(self):
        self.assertEqual(ext.day_kinds("2005-10-31"), {"rookie_scale", "veteran"})
        self.assertEqual(ext.day_kinds("2006-06-29"), {"veteran"})
        for day in ("2003-10-31", "2004-06-29", "2004-10-31", "2005-06-29", "2005-10-30", "2006-07-01"):
            self.assertEqual(ext.day_kinds(day), set(), day)
        self.assertEqual(ext.decision_days("2005-10-30"), [])
        self.assertEqual(ext.decision_days("2006-10-31"), ["2005-10-31", "2006-06-29", "2006-10-31"])

    def test_exact_limits_never_round_over(self):
        self.assertEqual(ext._pct(6_700_000, 110.5), 7_403_500)
        self.assertEqual(ext._pct(1_000_001, 10.5), 105_000)          # floor: never a dollar over the limit


class TermsTests(unittest.TestCase):
    rule = ext.rules("2005-06", ROOT)

    def test_rookie_scale_terms(self):
        n, first, step, sched = ext.terms_for("rookie_scale", 11_945_223, 2_589_023, 12_000_000, 641_748, 22, "2006-07", self.rule)
        self.assertEqual((n, first, step), (5, 11_945_223, 1_254_248))
        self.assertEqual(list(sched), ["2006-07", "2007-08", "2008-09", "2009-10", "2010-11"])
        self.assertEqual(sched["2010-11"], first + 4 * step)

    def test_veteran_terms_hold_to_110_5_percent_and_four_new_seasons(self):
        n, first, step, sched = ext.terms_for("veteran", 8_004_556, 6_700_000, 16_800_000, 1_138_500, 31, "2006-07", self.rule)
        self.assertEqual((n, first, step), (3, 7_403_500, 703_500))
        n, *_ = ext.terms_for("veteran", 8_004_556, 6_700_000, 16_800_000, 1_138_500, 22, "2006-07", self.rule)
        self.assertEqual(n, 4)                                        # five in all, the final season counted
        _, first, step, _ = ext.terms_for("veteran", 9_000_000, 20_000_000, 21_000_000, 1_138_500, 33, "2006-07", self.rule)
        self.assertEqual((first, step), (9_000_000, 945_000))         # a cut: raises on the smaller first year
        self.assertIsNone(ext.terms_for("veteran", 900_000, 500_000, 12_000_000, 641_748, 30, "2006-07", self.rule))


class DecideTests(unittest.TestCase):
    def cand(self, kind="rookie_scale", club="Phoenix Suns", wade=False, last=2_589_023):
        return {"bbr_id": "x01", "ledger_key": "x01", "player": "Player X", "club": club, "wade": wade, "kind": kind,
                "final_season": "2005-06", "last_salary": last, "eligibility": "test"}

    def run_decide(self, price, age=27, committed=0, spent=None, cand=None, gone=()):
        ev = FakeEvidence({"x01": {"value": 10, "price": price, "age": age}}, gone=gone)
        ev.committed = lambda club: committed
        cand = cand or self.cand()
        app = ext.appraise("2005-10-31", cand, ev, ROOT)
        return ext.decide("2005-10-31", cand, app, ev, {} if spent is None else spent, ROOT)

    def test_a_clear_offer_is_the_player_s_draw_only(self):
        d, packet = self.run_decide(7_000_000)
        self.assertEqual(d["club_call"]["decision"], "offer")
        self.assertEqual(set(packet["options"]), {"signed", "declined"})
        from runtime.decisions import decision_errors
        self.assertEqual(decision_errors(packet), [])

    def test_a_clear_no_offer_needs_no_draw(self):
        d, packet = self.run_decide(3_500_000)
        self.assertEqual((d["outcome"], packet, d["offer"]), ("no_offer", None, None))

    def test_a_close_call_is_one_joint_packet(self):
        d, packet = self.run_decide(5_000_000)
        self.assertEqual(d["club_call"]["decision"], "draw")
        self.assertAlmostEqual(d["club_call"]["p_offer"], 0.5)
        self.assertEqual(set(packet["options"]), {"signed", "declined", "no_offer"})
        self.assertAlmostEqual(packet["options"]["no_offer"], 0.5)
        self.assertAlmostEqual(sum(packet["options"].values()), 1.0, places=9)

    def test_payroll_blocks_and_earlier_offers_count(self):
        d, packet = self.run_decide(7_000_000, committed=58_000_000)
        self.assertEqual((d["club_call"]["blocked"], packet), ("payroll", None))
        spent = {"Phoenix Suns": 6_000_000}
        d, _ = self.run_decide(7_000_000, committed=50_000_000, spent=spent)
        self.assertEqual(d["club_call"]["blocked"], "payroll")
        d, _ = self.run_decide(7_000_000, committed=50_000_000, spent={})
        self.assertEqual(d["payroll"]["after"], 57_000_000)

    def test_a_player_whose_career_ends_gets_no_offer(self):
        d, packet = self.run_decide(9_000_000, gone={"x01"})
        self.assertEqual((d["club_call"]["blocked"], packet), ("retired", None))

    def test_wade_close_call_is_miami_s_draw_like_every_club_s(self):
        cand = self.cand(club="Miami Heat", wade=True)
        for price, p_offer in ((4_500_000, 0.25), (5_200_000, 0.6)):    # ratios 0.9 and 1.04: inside the band
            d, packet = self.run_decide(price, cand=cand)
            self.assertEqual((d["club_call"]["decision"], d["club_call"]["p_offer"], d["outcome"]), ("draw", p_offer, None))
            self.assertEqual(packet["options"], {"offer": p_offer, "no_offer": round(1 - p_offer, 6)})   # the club's call alone
            self.assertEqual((d["answer"]["offer_record"], d["answer"]["decider"]), (None, "Dwyane Wade (the user)"))
            from runtime.decisions import decision_errors
            self.assertEqual(decision_errors(packet), [])
        d, packet = self.run_decide(7_000_000, cand=cand)                # clear: an offer with no draw, his answer his own
        self.assertEqual((d["club_call"]["decision"], packet), ("offer", None))
        with self.assertRaises(ValueError):
            ev = FakeEvidence({})
            ext.appraise("2005-10-31", cand, ev, ROOT)                   # no valuation for Wade is an error


class AcceptTests(unittest.TestCase):
    def test_bounds_and_monotonicity(self):
        sched = {"2006-07": 8_000_000, "2007-08": 8_840_000, "2008-09": 9_680_000}
        chances = [ext.accept_chance(8_000_000, 3, sched, 28, 30.0, "Phoenix Suns", w, "2006-07", ROOT)[0] for w in (20, 41, 60)]
        self.assertEqual(chances, sorted(chances))                       # a stronger club is easier to stay with
        self.assertTrue(all(0.02 <= p <= 0.95 for p in chances))
        short = ext.accept_chance(8_000_000, 1, {"2006-07": 8_000_000}, 28, 30.0, "Phoenix Suns", 41, "2006-07", ROOT)[0]
        self.assertLess(short, chances[1])                               # fewer years than he wants: less security


# -- eligibility -------------------------------------------------------------------------------------------------------------
class EligibilityTests(Scenario):
    def test_rookie_scale_and_veteran_rules(self):
        eligible, skipped = ext.eligibility("2005-10-31", self.root)
        kinds = {c["bbr_id"]: c["kind"] for c in eligible}
        self.assertEqual(kinds, {"stoudam01": "rookie_scale", "butleca01": "rookie_scale", "wallabe01": "veteran",
                                 "moblecu01": "veteran", "onealsh01": "veteran"})
        reasons = {p: r for p, _, r in skipped}
        self.assertIn("under 4 seasons", reasons["Short Deal"])
        self.assertIn("3-season", reasons["Mike James"])
        self.assertIn("not recorded", reasons["No Date"])
        self.assertIn("4 required", reasons["Young Six"])              # six seasons signed before July 2005: four years
        self.assertIn("declined", reasons["Darko Milicic"])
        self.assertNotIn("Long Deal", reasons)                         # a contract running past 2005-06 is not considered
        shaq = next(c for c in eligible if c["bbr_id"] == "onealsh01")
        self.assertIn("extended contract", shaq["eligibility"])        # Q52: three years after the extension

    def test_a_veteran_day_has_no_rookie_window(self):
        put(self.root, f"{P}/2005-06/current_state.json", {"season": "2005-06", "current_date": "2006-06-29"})
        kinds = {c["bbr_id"]: c["kind"] for c in ext.eligibility("2006-06-29", self.root)[0]}
        self.assertNotIn("stoudam01", kinds)                           # rookie scale: October 31 only
        self.assertEqual(kinds.get("wallabe01"), "veteran")


# -- the two-phase flow --------------------------------------------------------------------------------------------------------
class FlowTests(Scenario):
    def test_packets_then_apply_then_carry(self):
        decided, written, applied, waiting = ext.run("2005-10-31", self.root)
        self.assertEqual({d["bbr_id"] for d in decided}, {"stoudam01", "butleca01", "wallabe01", "moblecu01", "onealsh01"})
        self.assertEqual(set(written), {"2005-10-31-extension-stoudam01", "2005-10-31-extension-wallabe01",
                                        "2005-10-31-extension-moblecu01", "2005-10-31-extension-onealsh01"})
        self.assertEqual((applied, waiting), (["2005-10-31-extension-butleca01"], []))   # Butler: a clear no, applied at once
        self.assertEqual(self.decision("moblecu01")["club_call"]["decision"], "draw")
        self.assertIn("Caron Butler", (self.root / f"{P}/2005-06/04_Training_Camp/note.md").read_text())
        from runtime.decisions import decision_errors
        for path in (self.root / f"{P}/2005-06/League/Extension_Draws").glob("*.decision.json"):
            self.assertEqual(decision_errors(json.loads(path.read_text())), [], path.name)
        self.assertEqual(ext.pending(self.root)["draws"].__len__(), 4)
        self.assertNotIn("extension", self.ledger()["stoudam01"])     # nothing signed before the draw
        self.assertEqual(ext.extension_errors(self.root), [])
        before = (self.root / f"{P}/2005-06/League/extension_decisions.json").read_text()
        self.assertEqual(ext.run("2005-10-31", self.root)[:3], ([], [], []))      # idempotent
        self.assertEqual((self.root / f"{P}/2005-06/League/extension_decisions.json").read_text(), before)

        self.draw("stoudam01", "signed")
        self.draw("wallabe01", "declined")
        self.draw("moblecu01", "no_offer")
        self.draw("onealsh01", "signed")
        _, _, applied, _ = ext.run("2005-10-31", self.root)
        self.assertEqual(len(applied), 4)
        amare = self.ledger()["stoudam01"]
        offer = self.decision("stoudam01")["offer"]
        self.assertEqual(amare["extension"]["id"], "2005-10-31-extension-stoudam01")
        self.assertEqual(amare["schedule"], {"2005-06": 2589023, **offer["schedule"]})
        self.assertEqual(ext.base_schedule(amare), {"2005-06": 2589023})
        self.assertNotIn("extension", self.ledger()["wallabe01"])
        self.assertEqual(ext.pending(self.root), {"draws": [], "wade": []})
        self.assertEqual(ext.extension_errors(self.root), [])
        # the day's eligibility replays unchanged after the schedule grew
        self.assertIn("stoudam01", {c["bbr_id"] for c in ext.eligibility("2005-10-31", self.root)[0]})

        # the rollover carries it: the next season's existing contracts and its rebuilt ledger
        from runtime import league_contracts
        carried = league_contracts.carried("2006-07", self.root)["stoudam01"]
        self.assertEqual(carried["schedule"], offer["schedule"])
        self.assertFalse(carried["rookie_scale"])                      # a veteran contract from its first extension season
        self.assertEqual(carried["extension"]["id"], amare["extension"]["id"])
        market = {"clubs": {"Phoenix Suns": [{"player": "Amar'e Stoudemire", "bbr_id": "stoudam01", "route": "existing",
                                              "salary": offer["first_salary"], "source": "league contract ledger 2005-06 (existing)"}]}}
        with mock.patch("runtime.free_agency_2004.calendar", return_value={"scale": {}}), \
                mock.patch("runtime.free_agency_2004.year_context", lambda *a, **k: nullcontext()):
            built = league_contracts.build("2006-07", self.root, market)["stoudam01"]
        self.assertEqual(built["schedule"], offer["schedule"])
        self.assertEqual(built["extension"]["id"], amare["extension"]["id"])
        self.assertTrue(built["source"].endswith("; extended 2005-10-31"))
        self.assertNotIn("rookie_scale", built)

    def test_the_extended_player_is_not_in_next_summer_s_pool(self):
        ext.run("2005-10-31", self.root)
        for b, outcome in (("stoudam01", "signed"), ("wallabe01", "declined"), ("moblecu01", "no_offer"), ("onealsh01", "declined")):
            self.draw(b, outcome)
        ext.run("2005-10-31", self.root)
        from runtime import free_agency_2004 as fa
        rosters = {"Phoenix Suns": [{"bbr_id": "stoudam01"}], "Detroit Pistons": [{"bbr_id": "wallabe01"}]}
        with mock.patch.multiple(fa, SEASON="2005-06", NEW="2006-07", SEASON_END="2006-04-19", YEAR=2006), \
                mock.patch("runtime.seasons.clubs", return_value=sorted(rosters)), \
                mock.patch("runtime.league_moves.effective_roster", side_effect=lambda club, *a, **k: rosters.get(club, [])), \
                mock.patch("runtime.rotations.miami_holds", return_value=frozenset()), \
                mock.patch("runtime.draft.drafted_clubs", return_value={}), \
                mock.patch("runtime.draft.year_context", lambda *a, **k: nullcontext()):
            book = fa._ledger_book(self.root)
        self.assertIn("stoudam01", book["contracts"])
        self.assertEqual(book["contracts"]["stoudam01"]["years"], len(self.decision("stoudam01")["offer"]["schedule"]))
        self.assertNotIn("stoudam01", book["rights"])
        self.assertEqual(book["rights"].get("wallabe01"), "Detroit Pistons")   # declined: a free agent next summer
        # validation: a market that treated the extended contract as expiring is refused
        market = f"{P}/2005-06/10_Free_Agency/free_agency_2006.json"
        put(self.root, market, {"events": [], "unsigned_pool": [{"bbr_id": "wallabe01", "rights": "Detroit Pistons"}]})
        self.assertEqual(ext.extension_errors(self.root), [])
        put(self.root, market, {"events": [{"date": "2006-06-30", "kind": "qualifying_offer", "bbr_id": "stoudam01"}],
                                "unsigned_pool": [{"bbr_id": "stoudam01", "rights": "Phoenix Suns"}]})
        self.assertTrue(any("treats his contract as expiring" in e for e in ext.extension_errors(self.root)))

    def test_tampering_is_refused(self):
        ext.run("2005-10-31", self.root)
        self.draw("stoudam01", "signed")
        for b, outcome in (("wallabe01", "declined"), ("moblecu01", "no_offer"), ("onealsh01", "declined")):
            self.draw(b, outcome)
        ext.run("2005-10-31", self.root)
        path = self.root / f"{P}/2005-06/League/extension_decisions.json"
        good = path.read_text()

        def errors_with(change):
            data = json.loads(good)
            change(data)
            path.write_text(json.dumps(data))
            ext._REPLAY.clear()
            out = ext.extension_errors(self.root)
            path.write_text(good)
            return out

        def over_limit(data):
            o = next(d for d in data["decisions"] if d["bbr_id"] == "wallabe01")["offer"]
            o["first_salary"] += 1_000_000
        self.assertTrue(any("first-year" in e or "flat raises" in e for e in errors_with(over_limit)))

        def changed_outcome(data):
            next(d for d in data["decisions"] if d["bbr_id"] == "wallabe01")["outcome"] = "signed"
        self.assertTrue(any("differs from the drawn" in e or "lacks the signed" in e for e in errors_with(changed_outcome)))

        def clear_drawn(data):
            d = next(d for d in data["decisions"] if d["bbr_id"] == "stoudam01")
            d["club_call"]["decision"] = "draw"
        self.assertTrue(errors_with(clear_drawn))

        def dropped(data):
            data["decisions"] = [d for d in data["decisions"] if d["bbr_id"] != "onealsh01"]
        self.assertTrue(any("not decided" in e for e in errors_with(dropped)))

        def late(data):
            data["days"][0]["recorded_on"] = "2005-11-02"
        self.assertTrue(any("on its own date" in e for e in errors_with(late)))

        ledger = self.root / f"{P}/2005-06/League/contracts.json"
        saved = ledger.read_text()
        data = json.loads(saved)
        for c in data["contracts"]:
            c.pop("extension", None)
        ledger.write_text(json.dumps(data))
        self.assertTrue(any("lacks the signed extension" in e for e in ext.extension_errors(self.root)))
        ledger.write_text(saved)

    def test_an_undecided_day_before_the_clock_is_refused(self):
        put(self.root, f"{P}/2005-06/current_state.json", {"season": "2005-06", "current_date": "2005-11-01"})
        self.assertTrue(any("2005-10-31 was missed" in e for e in ext.extension_errors(self.root)))
        self.assertTrue(any("was missed" in b and "--write" not in b for b in ext.rollover_blockers("2005-06", "2006-10-01", self.root)))
        self.assertEqual(ext.rollover_blockers("2004-05", "2005-10-01", self.root), [])


# -- a day is decided on its own date, in order, never late ----------------------------------------------------------------------
class GateTests(Scenario):
    def clock(self, day):
        put(self.root, f"{P}/2005-06/current_state.json", {"season": "2005-06", "current_date": day,
                                                           "current_note": "04_Training_Camp/note.md", "pending_player_decisions": []})

    def test_a_missed_day_is_refused_never_caught_up(self):
        # the reviewer's case: the clock in the 2006 summer, both 2005-06 days undecided; nothing is decided or written
        self.clock("2006-07-10")
        with self.assertRaises(ext.ExtensionError) as e:
            ext.run("2006-07-10", self.root)
        self.assertIn("2005-10-31 was missed", str(e.exception))
        self.assertFalse((self.root / ext.record_path("2005-06")).exists())
        self.assertFalse((self.root / ext.draws_dir("2005-06")).exists())
        from scripts import extension_day
        with mock.patch.object(extension_day, "ROOT", self.root), mock.patch("builtins.print") as shown, \
                self.assertRaises(SystemExit) as code:
            extension_day.main(["extension_day.py", "--write", "2006-07-10"])
        self.assertEqual(code.exception.code, 1)
        self.assertTrue(shown.call_args[0][0].startswith("extensions refused: extension day 2005-10-31 was missed"))

    def test_a_day_ahead_of_the_clock_is_refused(self):
        self.clock("2005-10-30")
        with self.assertRaises(ext.ExtensionError) as e:
            ext.run("2005-10-31", self.root)
        self.assertIn("ahead of the career clock", str(e.exception))

    def test_a_day_waits_for_every_earlier_decision(self):
        ext.run("2005-10-31", self.root)                                   # four packets, not drawn
        self.clock("2006-06-29")
        with self.assertRaises(ext.ExtensionError) as e:
            ext.run("2006-06-29", self.root)
        self.assertIn("unresolved", str(e.exception))
        self.assertIn("2005-10-31-extension-wallabe01", str(e.exception))
        self.assertNotIn("2006-06-29", {x["day"] for x in self.record()["days"]})
        for b, outcome in (("stoudam01", "declined"), ("wallabe01", "declined"), ("moblecu01", "no_offer"), ("onealsh01", "declined")):
            self.draw(b, outcome)
        decided, *_ = ext.run("2006-06-29", self.root)                       # applied first, then the June day is decided
        self.assertIn("2006-06-29", {x["day"] for x in self.record()["days"]})
        self.assertTrue(all(d["applied"] for d in self.record()["decisions"] if d["day"] == "2005-10-31"))
        self.assertTrue(all(d["recorded_on"] == d["day"] for d in self.record()["decisions"]))

    def test_a_day_whose_league_year_is_not_live_is_refused(self):
        self.clock("2006-10-31")
        closed_days(self.root, "2005-06", "2005-10-31", "2006-06-29")
        with self.assertRaises(ext.ExtensionError) as e:
            ext.run("2006-10-31", self.root)
        self.assertIn("not live", str(e.exception))

    def test_the_rollover_stops_with_unsettled_extensions_once_it_is_due(self):
        from runtime.rollover import Rollover
        r = Rollover.__new__(Rollover)
        r.root, r.old, r.new, r.year, r.day = self.root, "2005-06", "2006-07", 2006, "2006-10-01"
        r.old_dir, r.new_dir = self.root / P / "2005-06", self.root / P / "2006-07"
        r.record_path, r.record = self.root / f"{P}/2005-06/10_Free_Agency/free_agency_2006.json", {"events": []}
        put(self.root, f"{P}/2005-06/season_close.json", {})
        with mock.patch("runtime.seasons.supported", return_value=[]):
            waiting = r.blockers("2006-09-15")                              # not due: listed with the other gates
            self.assertTrue(any("not settled" not in b and "was missed" in b for b in waiting))
            self.assertTrue(any("the clock is 2006-09-15" in b for b in waiting))
            with self.assertRaises(ext.ExtensionError) as e:                # due: raised, never a silent wait
                r.blockers("2006-10-01")
            self.assertIn("2005-10-31 was missed", str(e.exception))
            closed_days(self.root, "2005-06", "2005-10-31", "2006-06-29")
            self.assertEqual(r.blockers("2006-10-01"), [])


# -- waived contracts and the payroll --------------------------------------------------------------------------------------------
def moves(root, season, *entries):
    put(root, f"{P}/{season}/League/league_moves.json", {"kind": "league_moves", "season": season, "entries": [
        {"id": f"{season}-market-{d}-{k}-{b}", "date": d, "kind": k, "bbr_id": b, "player": b, "from": f, "to": t,
         **({"waiver": w} if w else {})} for d, k, b, f, t, w in entries]})


class WaiverTests(Scenario):
    held = (dict(ROSTERS_2005, moblecu01="Boston Celtics", stoudam01="Boston Celtics", wallabe01="Boston Celtics",
                 longde01="Phoenix Suns"), {"butleca01", "jamesmi01"})

    def setUp(self):
        super().setUp()
        moves(self.root, "2004-05",
              ("2005-01-10", "waive", "moblecu01", "Houston Rockets", None, None),
              ("2005-01-12", "clear", "moblecu01", None, None, None),
              ("2005-02-01", "rest_of_season", "moblecu01", None, "Boston Celtics", None),
              ("2005-03-01", "waive", "stoudam01", "Phoenix Suns", None, None),
              ("2005-03-03", "clear", "stoudam01", None, None, None),
              ("2005-03-10", "ten_day", "stoudam01", None, "Boston Celtics", None),
              ("2005-01-20", "waive", "wallabe01", "Detroit Pistons", None, None),
              ("2005-01-22", "claim", "wallabe01", None, "Boston Celtics", "2004-05-market-2005-01-20-waive-wallabe01"),
              ("2005-02-01", "waive", "longde01", "Boston Celtics", None, None),
              ("2005-02-03", "clear", "longde01", None, None, None),
              ("2005-02-10", "rest_of_season", "longde01", None, "Phoenix Suns", None))

    def test_a_waived_contract_is_not_the_new_club_s_to_extend(self):
        eligible, skipped = ext.eligibility("2005-10-31", self.root)
        kinds = {c["bbr_id"]: (c["kind"], c["club"]) for c in eligible}
        reasons = {p: r for p, _, r in skipped}
        self.assertNotIn("moblecu01", kinds)                               # a waived veteran
        self.assertIn("waived by Houston Rockets on 2005-01-10", reasons["Cuttino Mobley"])
        self.assertNotIn("stoudam01", kinds)                               # a waived rookie-scale player, option exercised
        self.assertIn("waived by Phoenix Suns", reasons["Amar'e Stoudemire"])
        self.assertEqual(kinds["wallabe01"], ("veteran", "Boston Celtics"))  # claimed: the contract travelled with him

    def test_the_waiving_club_keeps_the_waived_salary(self):
        committed = ext.payrolls("2005-10-31", self.root)
        self.assertEqual(committed.get("Boston Celtics"), 5_400_000)       # Long Deal's 2006-07, owed by Boston
        self.assertNotIn("Phoenix Suns", committed)

    def test_an_exercised_option_on_a_contract_no_longer_in_force(self):
        # a rookie whose option was exercised, then signed a new one-season contract in the summer market
        opts = read(self.root, f"{P}/2004-05/League/option_decisions.json")
        opts["decisions"].append(option("rooknew01", "Rookie New", "Denver Nuggets", "2005-06", "2004-10-31"))
        put(self.root, f"{P}/2004-05/League/option_decisions.json", opts)
        ledger = read(self.root, f"{P}/2005-06/League/contracts.json")
        ledger["contracts"].append({"player": "Rookie New", "bbr_id": "rooknew01", "club": "Denver Nuggets", "kind": "new",
                                    "route": "minimum", "schedule": {"2005-06": 1_000_000}, "rookie_scale": True,
                                    "source": "2005 simulated free agency"})
        put(self.root, f"{P}/2005-06/League/contracts.json", ledger)
        put(self.root, f"{P}/2004-05/10_Free_Agency/free_agency_2005.json", {"events": [
            {"date": "2005-07-20", "kind": "signing", "bbr_id": "rooknew01", "club": "Denver Nuggets", "years": 1}]})
        held = (dict(self.held[0], rooknew01="Denver Nuggets"), self.held[1])
        eligible, skipped = ext.eligibility("2005-10-31", self.root, held)
        self.assertNotIn("rooknew01", {c["bbr_id"] for c in eligible})
        self.assertIn("1-season contract", {p: r for p, _, r in skipped}["Rookie New"])


class PayrollTests(Scenario):
    def test_miami_counts_the_players_it_holds_at_the_start_of_the_day(self):
        sheet = read(self.root, f"{P}/2005-06/00_Team/Finances/contract_schedules.json")
        sheet["players"] += [
            {"player": "Later Traded", "bbr_id": "latertr01", "status": "traded", "signed_date": "2004-07-15",
             "schedule": {"2005-06": 2_000_000, "2006-07": 2_200_000}},          # traded after the day: still Miami's then
            {"player": "Gone Before", "bbr_id": "gonebe01", "status": "under_contract", "signed_date": "2004-07-15",
             "schedule": {"2005-06": 1_000_000, "2006-07": 1_100_000}},          # not Miami's at the start of the day
            {"player": "Signed Later", "bbr_id": "signla01", "status": "under_contract", "signed_date": "2005-11-05",
             "schedule": {"2005-06": 1_000_000, "2006-07": 1_300_000}}]
        put(self.root, f"{P}/2005-06/00_Team/Finances/contract_schedules.json", sheet)
        held = (ROSTERS_2005, {"butleca01", "jamesmi01", "latertr01", "signla01"})
        self.assertEqual(ext.payrolls("2005-10-31", self.root, held).get("Miami Heat"), 2_200_000)


# -- an extended contract traded to Miami keeps its extension ---------------------------------------------------------------------
class TradedInTests(Scenario):
    def signed_amare(self):
        ext.run("2005-10-31", self.root)
        for b, outcome in (("stoudam01", "signed"), ("wallabe01", "declined"), ("moblecu01", "no_offer"), ("onealsh01", "declined")):
            self.draw(b, outcome)
        ext.run("2005-10-31", self.root)
        return self.ledger()["stoudam01"], self.decision("stoudam01")["offer"]

    def test_a_row_copied_without_the_extension_record_gains_it(self):
        amare, offer = self.signed_amare()
        row = {"player": "Amar'e Stoudemire", "bbr_id": "stoudam01", "status": "under_rookie_contract", "acquired_by": "trade",
               "schedule": dict(amare["schedule"]), "amount_kind": {s: "contract_salary" for s in amare["schedule"]}}
        full = ext.with_recorded(row, self.root)
        self.assertEqual(full["extension"]["id"], "2005-10-31-extension-stoudam01")
        self.assertNotIn("extension", row)                                 # a copy
        self.assertEqual(set(ext.without_extension(full)["schedule"]), {"2005-06"})   # no season on both agreements
        self.assertEqual(ext.miami_origin(row, "stoudam01", "2005-06", self.root)["signed_date"], "2005-10-31")
        other = dict(row, schedule={"2005-06": 2589023, "2006-07": 1})      # different amounts: not this extension
        self.assertIs(ext.with_recorded(other, self.root), other)

    def test_a_summer_trade_assigns_the_extended_agreement(self):
        amare, offer = self.signed_amare()
        from runtime.rollover import Rollover
        r = Rollover.__new__(Rollover)
        r.root, r.old, r.new, r.year, r.day = self.root, "2005-06", "2006-07", 2006, "2006-10-01"
        r.record_path = self.root / f"{P}/2005-06/10_Free_Agency/free_agency_2006.json"
        lg = {k: v for k, v in amare.items()}
        lg["schedule"] = dict(offer["schedule"])
        event = {"date": "2006-07-20", "from": "Phoenix Suns", "deal": "test", "kind": "trade"}
        with mock.patch.object(Rollover, "original_signing", return_value=None):
            entry = r.traded_in("stoudam01", "Amar'e Stoudemire", {"route": "existing"}, event, lg, dict(offer["schedule"]))
        self.assertEqual(entry["extension"]["id"], "2005-10-31-extension-stoudam01")
        self.assertEqual((entry["status"], entry["original_term_seasons"]), ("under_contract", 1))
        self.assertEqual(ext.without_extension(entry)["schedule"], {})      # every 2006-07 season is the extension's


class MiamiTests(Scenario):
    evidence = dict(EVIDENCE_2005, butleca01={"value": 14, "price": 6_000_000, "age": 25})

    def test_a_miami_extension_reaches_the_sheet_archive_and_carries(self):
        ext.run("2005-10-31", self.root)
        for b, outcome in (("butleca01", "signed"), ("stoudam01", "declined"), ("wallabe01", "declined"),
                           ("moblecu01", "no_offer"), ("onealsh01", "declined")):
            self.draw(b, outcome)
        _, _, applied, _ = ext.run("2005-10-31", self.root)
        self.assertIn("2005-10-31-extension-butleca01", applied)
        sheet = read(self.root, f"{P}/2005-06/00_Team/Finances/contract_schedules.json")
        butler = next(p for p in sheet["players"] if p["player"] == "Caron Butler")
        offer = self.decision("butleca01")["offer"]
        self.assertEqual({s: butler["schedule"][s] for s in offer["schedule"]}, offer["schedule"])
        self.assertEqual(butler["status"], "under_rookie_contract")    # the agreement in force is unchanged until 2006-07
        self.assertEqual(butler["signed_date"], "2002-07-02")
        self.assertEqual(sheet["known_baseline"]["2006-07"], offer["first_salary"])
        archive = read(self.root, f"{P}/Contracts/contract_records.json")
        self.assertIn("butleca01-2005-10-31", {r["contract_id"] for r in archive["records"]})
        self.assertEqual(self.ledger()["butleca01"]["extension"]["id"], "2005-10-31-extension-butleca01")
        self.assertEqual(ext.extension_errors(self.root), [])
        # contract pages: the sheet row keeps the term it extends
        self.assertEqual(set(ext.without_extension(butler)["schedule"]), {"2003-04", "2004-05", "2005-06"})

        # the rollover carries the entry; continuity accepts it and the status follows the extension
        from runtime.continuity import contract_errors
        from runtime.rollover import Rollover
        r = Rollover.__new__(Rollover)
        r.root, r.old, r.new, r.year, r.day = self.root, "2005-06", "2006-07", 2006, "2006-10-01"
        r.old_dir, r.new_dir = self.root / P / "2005-06", self.root / P / "2006-07"
        r.old_team, r.team = r.old_dir / "00_Team", r.new_dir / "00_Team"
        r.record_path = self.root / f"{P}/2005-06/10_Free_Agency/free_agency_2006.json"
        row = {"bbr_id": "butleca01", "player": "Caron Butler", "route": "existing", "salary": offer["first_salary"]}
        with mock.patch.object(Rollover, "miami", return_value=[("butleca01", row, {"name": "Caron Butler"}, None)]), \
                mock.patch("runtime.seasons.dates", return_value={"guarantee": "2007-01-10"}):
            entries = r.contract_entries({})
        self.assertEqual(entries[0]["status"], "under_contract")
        self.assertEqual(entries[0]["extension"]["id"], "2005-10-31-extension-butleca01")
        put(self.root, f"{P}/2006-07/00_Team/Finances/contract_schedules.json", {"players": entries})
        put(self.root, f"{P}/2006-07/00_Team/Team/Roster/roster.json",
            {"players": [{"id": "caron_butler", "name": "Caron Butler", "bbr_id": "butleca01"}]})
        self.assertEqual(contract_errors(self.root, "2005-06", "2006-07"), [])

    def test_continuity_accepts_an_extension_signed_in_the_new_year_and_refuses_unrecorded_growth(self):
        from runtime.continuity import contract_errors
        old = {"player": "X", "bbr_id": "x01", "status": "under_contract", "schedule": {"2005-06": 1, "2006-07": 2}}
        sub = {"id": "2006-10-31-extension-x01", "signed_date": "2006-10-31", "schedule": {"2007-08": 3}}
        for season, players in (("2005-06", [old]),
                                ("2006-07", [dict(old, schedule={"2006-07": 2, "2007-08": 3}, extension=sub)])):
            put(self.root, f"{P}/{season}/00_Team/Finances/contract_schedules.json", {"players": players})
            put(self.root, f"{P}/{season}/00_Team/Team/Roster/roster.json", {"players": [{"name": "X", "bbr_id": "x01"}]})
        self.assertEqual(contract_errors(self.root, "2005-06", "2006-07"), [])
        put(self.root, f"{P}/2006-07/00_Team/Finances/contract_schedules.json",
            {"players": [dict(old, schedule={"2006-07": 2, "2007-08": 3})]})
        self.assertTrue(contract_errors(self.root, "2005-06", "2006-07"))


# -- Wade ----------------------------------------------------------------------------------------------------------------------
def wade_2006(root):
    put(root, f"{P}/2005-06/current_state.json", {"season": "2005-06", "current_date": "2006-10-01", "closed": True})
    put(root, f"{P}/2006-07/current_state.json", {"season": "2006-07", "current_date": "2006-10-31", "team": "Miami Heat",
                                                 "current_note": "04_Training_Camp/note.md", "pending_player_decisions": [],
                                                 "contract_status": "rookie_scale_contract"})
    put(root, f"{P}/2006-07/04_Training_Camp/note.md", NOTE)
    put(root, f"{P}/2005-06/League/option_decisions.json", {"decisions": [
        option("wadedw01", "Dwyane Wade", "Miami Heat", "2006-07", "2005-10-31")]})
    put(root, f"{P}/2006-07/League/contracts.json", {"contracts": [
        {"player": "dwyane_wade", "bbr_id": "dwyane_wade", "club": "Miami Heat", "route": "existing", "kind": "existing",
         "schedule": {"2006-07": 3201202}, "source": "Miami contract_schedules.json"}]})
    put(root, f"{P}/2006-07/00_Team/Finances/contract_schedules.json", {"as_of": "2006-10-31", "team": "Miami Heat", "projection": [], "players": [
        {"player": "Dwyane Wade", "status": "under_contract", "route": "rookie_scale", "signed_date": "2003-07-21",
         "original_term_seasons": 3, "contract_id": "wadedw01-2003-07-21",
         "schedule": {"2003-04": 2197000, "2004-05": 2361800, "2005-06": 2526600, "2006-07": 3201202},
         "amount_kind": {"2003-04": "contract_salary", "2004-05": "contract_salary", "2005-06": "contract_salary", "2006-07": "contract_salary"}}]})
    put(root, f"{P}/2006-07/00_Team/Team/Roster/roster.json", {"players": [{"id": "dwyane_wade", "name": "Dwyane Wade", "status": "under_contract"}]})
    put(root, f"{P}/professional_identity.json", {"snapshots": [{"as_of": "2006-10-01", "team": "Miami Heat", "positions": ["SG"],
                                                                "jersey": "3", "contract": "Rookie scale signed 2003-07-21"}]})
    closed_days(root, "2005-06", "2005-10-31", "2006-06-29")       # the 2005-06 days were decided on their own dates


def closed_days(root, season, *days):
    """An extension record whose days were decided on their own dates with nobody eligible."""
    put(root, f"{P}/{season}/League/extension_decisions.json", {
        "schema_version": 1, "kind": "extension_decisions", "season": season, "rule": "test", "decisions": [],
        "days": [{"day": d, "kinds": sorted(ext.day_kinds(d)), "eligible": 0, "recorded_on": d} for d in days]})


class WadeTests(unittest.TestCase):
    def setUp(self):
        self.tmp, self.root = scratch()
        wade_2006(self.root)
        ev = self.ev = FakeEvidence({"wadedw01": {"value": 30, "price": 12_455_000, "age": 22}}, planning="2006-07",
                                    mid_level=5_215_000, tax=65_420_000)
        for p in patched(({}, {"dwyane_wade"}), ev):
            p.start()
            self.addCleanup(p.stop)
        ext.clear_cache()
        ext._REPLAY.clear()
        self.oid = ext.offer_id("2006-10-31")
        self.state = f"{P}/2006-07/current_state.json"

    def tearDown(self):
        self.tmp.cleanup()

    def answer(self, action):
        from runtime.milestone_records import version
        from scripts.player_milestone import reply
        path = ext.offer_path(self.root, "2006-07", self.oid)
        response = {"kind": "extension", "season": "2006-07", "event_id": self.oid, "action": action, "date": "2006-10-31",
                    "text": f"I {action} the extension.", "source_ref": self.state}
        with mock.patch("scripts.player_milestone.refresh"):
            reply(self.root, response, version(path))

    def test_offer_waits_then_accept_signs(self):
        decided, written, applied, waiting = ext.run("2006-10-31", self.root)
        self.assertEqual((written, applied, waiting), ([], [], [self.oid]))
        d = decided[0]
        self.assertEqual((d["kind"], d["outcome"], d["packet"]), ("rookie_scale", None, None))
        self.assertEqual(read(self.root, self.state)["pending_player_decisions"], [ext.PENDING_PREFIX + self.oid])
        offer = ext.offer_path(self.root, "2006-07", self.oid)
        self.assertTrue(offer.with_name(ext.page_name({"date": "2006-10-31"})).is_file())
        self.assertEqual(ext.pending(self.root)["wade"], [self.oid])
        self.assertEqual(ext.extension_errors(self.root), [])
        with self.assertRaises(ValueError):                             # a reply needs accept or decline
            self.answer("counter")
        self.answer("accept")
        self.assertEqual(read(self.root, self.state)["pending_player_decisions"], [])
        self.assertEqual(json.loads(offer.read_text())["answer"], "accept")
        _, _, applied, waiting = ext.run("2006-10-31", self.root)
        self.assertEqual((applied, waiting), ([d["id"]], []))
        sheet = read(self.root, f"{P}/2006-07/00_Team/Finances/contract_schedules.json")["players"][0]
        schedule = d["offer"]["schedule"]
        self.assertEqual({s: sheet["schedule"][s] for s in schedule}, schedule)
        self.assertEqual(list(schedule)[0], "2007-08")
        ledger = read(self.root, f"{P}/2006-07/League/contracts.json")["contracts"][0]
        self.assertEqual(ledger["extension"]["id"], d["id"])
        self.assertEqual(read(self.root, self.state)["contract_status"], "rookie_scale_contract_extended")
        identity = read(self.root, f"{P}/professional_identity.json")["snapshots"][-1]
        self.assertEqual(identity["as_of"], "2006-10-31")
        self.assertIn("extension signed 2006-10-31", identity["contract"])
        self.assertEqual(ext.extension_errors(self.root), [])

    def test_miami_s_close_call_on_wade_is_drawn_then_he_answers(self):
        self.ev.players["wadedw01"]["price"] = 4_500_000                  # worth 5,625,000: ratio 1.0786, P(offer) 0.697
        decided, written, applied, waiting = ext.run("2006-10-31", self.root)
        d = decided[0]
        self.assertEqual((d["club_call"]["decision"], d["club_call"]["p_offer"]), ("draw", 0.697))
        self.assertEqual((written, applied, waiting), ([d["id"]], [], []))      # no offer before the club's draw
        self.assertFalse(ext.offer_path(self.root, "2006-07", self.oid).exists())
        self.assertEqual(read(self.root, self.state)["pending_player_decisions"], [])
        self.assertEqual(ext.pending(self.root), {"draws": [d["packet"]], "wade": []})
        self.assertEqual(ext.extension_errors(self.root), [])
        packet = self.root / d["packet"]
        put(self.root, packet.with_name(packet.name.replace(".decision.json", ".decision.result.json")).relative_to(self.root),
            dict(json.loads(packet.read_text()), kind="decision", outcome="offer"))
        _, _, applied, waiting = ext.run("2006-10-31", self.root)                # the drawn offer opens: his to answer
        self.assertEqual((applied, waiting), ([], [self.oid]))
        self.assertEqual(read(self.root, self.state)["pending_player_decisions"], [ext.PENDING_PREFIX + self.oid])
        self.assertIn("the engine drew the offer", json.loads(ext.offer_path(self.root, "2006-07", self.oid).read_text())["evidence"]["basis"])
        self.assertEqual(ext.extension_errors(self.root), [])
        self.answer("accept")
        _, _, applied, _ = ext.run("2006-10-31", self.root)
        self.assertEqual(applied, [d["id"]])
        self.assertEqual(read(self.root, f"{P}/2006-07/League/contracts.json")["contracts"][0]["extension"]["id"], d["id"])
        self.assertEqual(ext.extension_errors(self.root), [])

    def test_miami_s_drawn_no_offer_closes_without_a_question(self):
        self.ev.players["wadedw01"]["price"] = 4_500_000
        decided, *_ = ext.run("2006-10-31", self.root)
        packet = self.root / decided[0]["packet"]
        put(self.root, packet.with_name(packet.name.replace(".decision.json", ".decision.result.json")).relative_to(self.root),
            dict(json.loads(packet.read_text()), kind="decision", outcome="no_offer"))
        _, _, applied, waiting = ext.run("2006-10-31", self.root)
        self.assertEqual((applied, waiting), ([decided[0]["id"]], []))
        rec = read(self.root, f"{P}/2006-07/League/extension_decisions.json")["decisions"][0]
        self.assertEqual((rec["outcome"], rec["answer"]["offer_record"]), ("no_offer", None))
        self.assertFalse(ext.offer_path(self.root, "2006-07", self.oid).exists())
        self.assertIn("Miami makes no offer after the draw", (self.root / f"{P}/2006-07/04_Training_Camp/note.md").read_text())
        self.assertEqual(ext.extension_errors(self.root), [])

    def test_decline_leaves_the_contract_unchanged(self):
        ext.run("2006-10-31", self.root)
        sheet_before = read(self.root, f"{P}/2006-07/00_Team/Finances/contract_schedules.json")["players"][0]["schedule"]
        self.answer("decline")
        _, _, applied, _ = ext.run("2006-10-31", self.root)
        self.assertEqual(len(applied), 1)
        self.assertEqual(read(self.root, f"{P}/2006-07/00_Team/Finances/contract_schedules.json")["players"][0]["schedule"], sheet_before)
        self.assertNotIn("extension", read(self.root, f"{P}/2006-07/League/contracts.json")["contracts"][0])
        self.assertEqual(read(self.root, self.state)["contract_status"], "rookie_scale_contract")
        self.assertEqual(ext.extension_errors(self.root), [])


# -- Wade's own extension terms (filed 2005-10-31, read on his first extension day) ------------------------------------------------
TERMS = {"discount_from_market": 0.20, "additional_seasons": 5, "guaranteed_seasons": 4, "team_option_final_season": True,
         "raise": "maximum", "no_trade_clause": False}
WORDS = "My preferred starting point is 20% below my established fair market value (test words)."
REQUESTS = f"{P}/2005-06/04_Training_Camp/wade_requests.json"


def terms_row(date="2005-10-31", terms=None, **extra):
    return {"date": date, "subject": "extension_terms", "player": "Dwyane Wade", "bbr_id": "wadedw01", "requested": "propose",
            "terms": dict(TERMS if terms is None else terms), "if_not_offered": "play out the rookie contract", "words": WORDS,
            "note": "test", "source_ref": f"{P}/2005-06/04_Training_Camp/Wade_Extension_Outlook_2005-10-31.md", **extra}


def file_terms(root, *rows, rel=REQUESTS):
    put(root, rel, {"requests": list(rows) or [terms_row()]})


def wade_cand():
    return {"bbr_id": "wadedw01", "ledger_key": "dwyane_wade", "player": "Dwyane Wade", "club": "Miami Heat", "wade": True,
            "kind": "rookie_scale", "final_season": "2006-07", "last_salary": 3_201_202, "eligibility": "test"}


def request(terms):
    return {"path": REQUESTS, "index": 0, "date": "2005-10-31", "subject": "extension_terms", "terms": dict(terms),
            "words": WORDS, "if_not_offered": None, "source_ref": None}


class TermsReaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp, self.root = scratch()
        self.addCleanup(self.tmp.cleanup)

    def test_none_without_his_terms(self):
        self.assertIsNone(ext.terms_request("2006-10-31", self.root))
        file_terms(self.root, {"date": "2005-10-31", "subject": "draft_prospect", "player": "Kyle Lowry", "bbr_id": "lowryky01"})
        self.assertIsNone(ext.terms_request("2006-10-31", self.root))

    def test_the_latest_on_or_before_the_day_from_any_season_folder(self):
        file_terms(self.root, {"date": "2005-10-31", "subject": "draft_prospect", "player": "Kyle Lowry"}, terms_row())
        r = ext.terms_request("2006-10-31", self.root)
        self.assertEqual((r["path"], r["index"], r["date"], r["terms"], r["words"]), (REQUESTS, 1, "2005-10-31", TERMS, WORDS))
        self.assertEqual(r["if_not_offered"], "play out the rookie contract")
        self.assertIsNone(ext.terms_request("2005-10-30", self.root))             # filed after the day: not yet his terms
        later = f"{P}/2006-07/03_Offseason/wade_requests.json"
        file_terms(self.root, terms_row("2006-09-15", dict(TERMS, discount_from_market=0.10)),
                   terms_row("2006-11-01", dict(TERMS, discount_from_market=0.30)),
                   dict(terms_row("2006-10-01"), player="Udonis Haslem", bbr_id="hasleud01"), rel=later)
        r = ext.terms_request("2006-10-31", self.root)
        self.assertEqual((r["path"], r["date"], r["terms"]["discount_from_market"]), (later, "2006-09-15", 0.10))
        self.assertEqual(ext.terms_request("2006-11-01", self.root)["terms"]["discount_from_market"], 0.30)

    def test_terms_are_spent_by_the_negotiation_they_shaped(self):
        file_terms(self.root)
        put(self.root, f"{P}/2006-07/League/extension_decisions.json", {"kind": "extension_decisions", "season": "2006-07", "days": [],
            "decisions": [{"id": "2006-10-31-extension-wadedw01", "day": "2006-10-31", "wade": True}]})
        self.assertEqual(ext.terms_request("2006-10-31", self.root)["date"], "2005-10-31")    # the day it shapes
        self.assertIsNone(ext.terms_request("2010-06-29", self.root))      # never a later veteran extension's terms
        file_terms(self.root, terms_row("2009-07-01"), rel=f"{P}/2008-09/10_Free_Agency/wade_requests.json")
        self.assertEqual(ext.terms_request("2010-06-29", self.root)["date"], "2009-07-01")


class ShapeTests(unittest.TestCase):
    """Miami adopts a term that is legal and at least as favourable to it as its rule's term, and records every reason."""
    rule = ext.rules("2006-07", ROOT)

    def decide(self, terms, price=12_455_000, committed=0):
        ev = FakeEvidence({"wadedw01": {"value": 30, "price": price, "age": 22}}, planning="2006-07", mid_level=5_215_000,
                          tax=65_420_000)
        ev.committed = lambda club: committed
        app = ext.appraise("2006-10-31", wade_cand(), ev, ROOT)
        return ext.decide("2006-10-31", wade_cand(), app, ev, {}, ROOT, request=None if terms is None else request(terms))

    def test_his_terms_are_adopted(self):
        d, packet = self.decide(TERMS)
        o = d["offer"]
        self.assertEqual((d["club_call"]["decision"], packet), ("offer", None))
        # the benchmark is his price: the 12,455,000 market price held to his 12,000,000 maximum
        self.assertEqual(o["first_salary"], ext.discounted(12_000_000, 0.2))
        self.assertEqual(o["first_salary"], 9_600_000)                          # 20% under the benchmark
        self.assertEqual((o["years"], list(o["schedule"])), (5, ["2007-08", "2008-09", "2009-10", "2010-11", "2011-12"]))
        self.assertEqual(o["raise"], ext._pct(9_600_000, 10.5))                 # the maximum, on the offered first year
        self.assertLessEqual(o["raise"], o["limits"]["raise_limit"])
        self.assertEqual((o["options"], o["guaranteed_seasons"], o["team_option_season"]), ({"2011-12": "team_option"}, 4, "2011-12"))
        basis = o["terms_basis"]
        self.assertEqual((basis["benchmark"], basis["discount"]), (12_000_000, 0.2))
        self.assertEqual(basis["rule_terms"], {"years": 5, "first_salary": 12_000_000, "raise": ext._pct(12_000_000, 10.5)})
        self.assertEqual({x["term"] for x in basis["elements"]}, set(TERMS))
        self.assertTrue(all(x["adopted"] for x in basis["elements"]), basis["elements"])
        self.assertEqual((d["request"]["path"], d["request"]["words"]), (REQUESTS, WORDS))
        self.assertEqual(ext._offer_errors(d, "test"), [])
        # the call is the rule's on his full worth, as without his terms
        plain, _ = self.decide(None)
        self.assertEqual((d["club_call"], d["evidence"]), (plain["club_call"], plain["evidence"]))
        self.assertEqual(plain["offer"]["first_salary"], 12_000_000)
        self.assertNotIn("options", plain["offer"])

    def test_the_payroll_test_counts_the_offered_first_year(self):
        # price 8,000,000 (not a star's): the ceiling is the 65,420,000 tax line; 58,000,000 committed
        plain, _ = self.decide(None, price=8_000_000, committed=58_000_000)
        self.assertEqual(plain["club_call"]["blocked"], "payroll")              # 58,000,000 + 8,000,000 passes it
        d, _ = self.decide(TERMS, price=8_000_000, committed=58_000_000)
        self.assertEqual((d["club_call"]["decision"], d["payroll"]["offer"], d["payroll"]["after"]), ("offer", 6_400_000, 64_400_000))

    def test_his_discount_leaves_room_for_a_later_miami_offer_that_day(self):
        # Wade first by worth (a star's ceiling), then a Miami rookie-scale player priced at 7,000,000 under the tax line:
        # the day's running total counts Wade's offered first year, so his discount is room for the later offer
        ev = FakeEvidence({"wadedw01": {"value": 30, "price": 12_455_000, "age": 22},
                           "x02": {"value": 12, "price": 7_000_000, "age": 25}}, planning="2006-07", mid_level=5_215_000,
                          tax=65_420_000)
        ev.committed = lambda club: 48_000_000
        other = dict(wade_cand(), bbr_id="x02", ledger_key="x02", player="Player X", wade=False, last_salary=2_500_000)

        def day(terms):
            spent = {}
            wade, _ = ext.decide("2006-10-31", wade_cand(), ext.appraise("2006-10-31", wade_cand(), ev, ROOT), ev, spent,
                                 ROOT, request=None if terms is None else request(terms))
            return wade, ext.decide("2006-10-31", other, ext.appraise("2006-10-31", other, ev, ROOT), ev, spent, ROOT)

        wade, (later, packet) = day(None)
        self.assertEqual(wade["offer"]["first_salary"], 12_000_000)
        self.assertEqual((later["club_call"]["blocked"], later["payroll"]["after"], packet), ("payroll", 67_000_000, None))
        wade, (later, packet) = day(TERMS)
        self.assertEqual(wade["offer"]["first_salary"], 9_600_000)
        self.assertEqual((later["club_call"]["decision"], later["payroll"]["earlier_offers"], later["payroll"]["after"]),
                         ("offer", 9_600_000, 64_600_000))
        self.assertNotIn("request", later)
        # the later decision reads the room, never his terms: it is the plain rule's with 9,600,000 offered earlier
        plain = ext.decide("2006-10-31", other, ext.appraise("2006-10-31", other, ev, ROOT), ev, {"Miami Heat": 9_600_000}, ROOT)
        self.assertEqual((later, packet), plain)

    def test_terms_less_favourable_to_miami_are_not_adopted(self):
        terms = {"discount_from_market": -0.10, "additional_seasons": 6, "raise": 0.12, "player_option_final_season": True,
                 "no_trade_clause": True, "guaranteed_seasons": 5, "team_option_final_season": True, "signing_bonus": 1_000_000}
        d, _ = self.decide(terms)
        o = d["offer"]
        self.assertEqual((o["first_salary"], o["years"], o["raise"]), (12_000_000, 5, ext._pct(12_000_000, 10.5)))   # the rule's
        self.assertEqual((o["options"], o["guaranteed_seasons"]), ({"2011-12": "team_option"}, 4))
        by = {x["term"]: x for x in o["terms_basis"]["elements"]}
        self.assertEqual({t for t, x in by.items() if x["adopted"]}, {"team_option_final_season"})
        for term in ("discount_from_market", "player_option_final_season", "no_trade_clause"):
            self.assertIn("less favourable to Miami", by[term]["reason"], term)
        self.assertIn("cbafaq05 Q52", by["additional_seasons"]["reason"])
        self.assertIn("10.5%", by["raise"]["reason"])
        self.assertIn("not modelled", by["guaranteed_seasons"]["reason"])
        self.assertIn("not a term", by["signing_bonus"]["reason"])
        self.assertIsNone(o["terms_basis"]["discount"])
        self.assertEqual(ext._offer_errors(d, "test"), [])

    def test_limits_hold_the_adopted_terms(self):
        offer = (5, 1_000_000, 105_000, {})
        app = {"price": 1_000_000, "minimum": 641_748, "maximum": 12_000_000}
        n, f1, step, sched, opts, basis = ext.shape("rookie_scale", offer, app, 900_000, "2007-08", self.rule,
                                                    {"terms": {"discount_from_market": 0.5, "raise": 0.05}})
        self.assertEqual((f1, step), (641_748, ext._pct(641_748, 5)))           # held to his minimum; a lower raise adopted
        self.assertIn("held to his $641,748 minimum", basis["elements"][0]["reason"])
        vet = ext.terms_for("veteran", 9_000_000, 6_700_000, 16_800_000, 1_138_500, 31, "2006-07", self.rule)
        n, f1, *_ , basis = ext.shape("veteran", vet, {"price": 9_000_000, "minimum": 1_138_500, "maximum": 16_800_000},
                                      6_700_000, "2006-07", self.rule, {"terms": {"discount_from_market": 0.1}})
        self.assertEqual(f1, 7_403_500)                                         # 8,100,000 passes 110.5% of his last salary
        self.assertFalse(basis["elements"][0]["adopted"])
        unrecorded = dict(self.rule, max_option_seasons=None)
        *_, opts, basis = ext.shape("rookie_scale", (5, 9_000_000, 945_000, {}), app, 900_000, "2007-08", unrecorded,
                                    {"terms": {"team_option_final_season": True}})
        self.assertEqual((opts, basis["elements"][0]["adopted"]), ({}, False))  # no recorded option clause: no option

    def test_any_other_player_ignores_the_terms(self):
        ev = FakeEvidence({"x01": {"value": 10, "price": 7_000_000, "age": 27}})
        ev.committed = lambda club: 0
        cand = {"bbr_id": "x01", "ledger_key": "x01", "player": "Player X", "club": "Miami Heat", "wade": False,
                "kind": "rookie_scale", "final_season": "2005-06", "last_salary": 2_589_023, "eligibility": "test"}
        app = ext.appraise("2005-10-31", cand, ev, ROOT)
        plain = ext.decide("2005-10-31", cand, app, ev, {}, ROOT)
        asked = ext.decide("2005-10-31", cand, app, ev, {}, ROOT, request=request(TERMS))
        self.assertEqual(plain, asked)
        self.assertNotIn("request", asked[0])


class WadeTermsTests(WadeTests):
    """Wade's own terms on file (filed 2005-10-31): the WadeTests flows run again with them, and the shaped offer reaches
    his page, the ledger, Miami's sheet, the options step, the archive, the contract pages, the rollover and continuity."""

    def setUp(self):
        super().setUp()
        file_terms(self.root)
        sheet = read(self.root, f"{P}/2006-07/00_Team/Finances/contract_schedules.json")
        sheet["players"][0]["guaranteed"] = dict(sheet["players"][0]["schedule"])
        put(self.root, f"{P}/2006-07/00_Team/Finances/contract_schedules.json", sheet)

    def signed(self):
        decided, *_ = ext.run("2006-10-31", self.root)
        self.answer("accept")
        _, _, applied, _ = ext.run("2006-10-31", self.root)
        self.assertEqual(applied, [decided[0]["id"]])
        return decided[0]

    def test_the_offer_and_its_page_follow_his_terms(self):
        decided, written, applied, waiting = ext.run("2006-10-31", self.root)
        d = decided[0]
        self.assertEqual((written, waiting), ([], [self.oid]))
        o = d["offer"]
        self.assertEqual((o["first_salary"], o["years"], o["options"]), (9_600_000, 5, {"2011-12": "team_option"}))
        self.assertEqual((d["payroll"]["offer"], d["request"]["path"]), (9_600_000, REQUESTS))
        record = read(self.root, ext.offer_path(self.root, "2006-07", self.oid).relative_to(self.root))
        self.assertEqual(record["request"], d["request"])
        self.assertEqual((record["evidence"]["benchmark"], record["evidence"]["discount"]), (12_000_000, 0.2))
        self.assertEqual((record["offer"]["guaranteed_seasons"], record["offer"]["team_option_season"]), (4, "2011-12"))
        page = ext.offer_path(self.root, "2006-07", self.oid).with_name(ext.page_name(record)).read_text()
        for text in ("## Your terms", WORDS, "your discount of 20% makes the first year $9,600,000", "Market benchmark $12,000,000",
                     "| 2011-12 | $13,632,000 | Team option: Miami exercises or declines it by 2011-06-29",
                     "| 2007-08 | $9,600,000 | Fully guaranteed |", "Guaranteed seasons: 4 (2007-08 to 2010-11",
                     "through 2010-11 guaranteed", "**Accept**", "**Decline**", "../../../2005-06/04_Training_Camp/wade_requests.json"):
            self.assertIn(text, page)
        self.assertNotIn("Not adopted", page)
        note = (self.root / f"{P}/2006-07/04_Training_Camp/note.md").read_text()
        self.assertIn("2011-12 a Miami team option; shaped by Wade's terms of 2005-10-31", note)
        self.assertEqual(ext.extension_errors(self.root), [])
        self.assertEqual(read(self.root, self.state)["contract_status"], "rookie_scale_contract")   # nothing accepted for him

    def test_the_accepted_option_reaches_the_ledger_sheet_and_the_options_step(self):
        d = self.signed()
        o = d["offer"]
        ledger = read(self.root, f"{P}/2006-07/League/contracts.json")["contracts"][0]
        self.assertEqual((ledger["options"], ledger["schedule"]["2011-12"]), ({"2011-12": "team_option"}, o["schedule"]["2011-12"]))
        row = read(self.root, f"{P}/2006-07/00_Team/Finances/contract_schedules.json")["players"][0]
        self.assertEqual((row["amount_kind"]["2011-12"], row["amount_kind"]["2010-11"]), ("team_option", "contract_salary"))
        self.assertEqual(sorted(s for s in row["guaranteed"] if s >= "2007-08"), ["2007-08", "2008-09", "2009-10", "2010-11"])
        from runtime import options
        due = [r for r in options.open_options("2006-07", self.root) if r[3] == "2011-12"]
        self.assertEqual(due, [("Miami Heat", "wadedw01", "Dwyane Wade", "2011-12", "team_option", o["schedule"]["2011-12"], False)])
        self.assertEqual(options.deadline("team_option", "2011-12", due[0][6]), "2011-06-29")   # the veteran deadline
        archive = read(self.root, f"{P}/Contracts/contract_records.json")["records"][-1]["contract"]
        self.assertEqual((archive["amount_kind"]["2011-12"], archive["guaranteed"]["2011-12"], archive["option_deadline"]),
                         ("team_option", 0, "2011-06-29"))
        self.assertEqual(archive["guaranteed"]["2010-11"], o["schedule"]["2010-11"])
        (row, club, _, _), = ext.catalog_rows(self.root)
        self.assertEqual((club, row["guaranteed_seasons"], row["options"][0]["deadline"], row["options"][0]["outcome"]),
                         ("Miami Heat", 4, "2011-06-29", None))
        from runtime.player_contracts import _normal_contract
        page = _normal_contract("wadedw01", archive, None, {})
        self.assertEqual([(x["season"], x["type"], x["deadline"]) for x in page["options"]], [("2011-12", "team_option", "2011-06-29")])
        self.assertEqual({r["season"]: r["guaranteed"] for r in page["salary_rows"]}["2011-12"], 0)
        self.assertIn("2011-12 a team option", read(self.root, f"{P}/professional_identity.json")["snapshots"][-1]["contract"])
        self.assertEqual(ext.extension_errors(self.root), [])

    def test_the_rollover_carries_the_option_and_continuity_accepts_it(self):
        d = self.signed()
        from runtime import league_contracts, options
        from runtime.continuity import contract_errors
        from runtime.rollover import Rollover
        self.assertEqual(league_contracts.carried("2007-08", self.root)["dwyane_wade"]["options"], {"2011-12": "team_option"})
        r = Rollover.__new__(Rollover)
        r.root, r.old, r.new, r.year, r.day = self.root, "2006-07", "2007-08", 2007, "2007-10-01"
        r.old_dir, r.new_dir = self.root / P / "2006-07", self.root / P / "2007-08"
        r.old_team, r.team = r.old_dir / "00_Team", r.new_dir / "00_Team"
        r.record_path = self.root / f"{P}/2006-07/10_Free_Agency/free_agency_2007.json"
        row = {"bbr_id": "dwyane_wade", "player": "Dwyane Wade", "route": "existing", "salary": d["offer"]["first_salary"]}
        with mock.patch.object(Rollover, "miami", return_value=[("dwyane_wade", row, {"name": "Dwyane Wade"}, None)]), \
                mock.patch("runtime.seasons.dates", return_value={"guarantee": "2008-01-10"}):
            entries = r.contract_entries({})
        self.assertEqual((entries[0]["status"], entries[0]["amount_kind"]["2011-12"]), ("under_contract", "team_option"))
        put(self.root, f"{P}/2007-08/00_Team/Finances/contract_schedules.json", {"players": entries})
        put(self.root, f"{P}/2007-08/00_Team/Team/Roster/roster.json", {"players": [{"id": "dwyane_wade", "name": "Dwyane Wade"}]})
        self.assertEqual(contract_errors(self.root, "2006-07", "2007-08"), [])
        self.assertEqual([x[3:] for x in options.open_options("2007-08", self.root)],
                         [("2011-12", "team_option", d["offer"]["schedule"]["2011-12"], False)])

    def test_a_declined_option_ends_the_contract_and_the_extension_stays_valid(self):
        d = self.signed()
        from runtime import options
        decision = {"id": "2011-12-option-wadedw01-team_option", "club": "Miami Heat", "player": "Dwyane Wade", "bbr_id": "wadedw01",
                    "option_season": "2011-12", "kind": "team_option", "salary": d["offer"]["schedule"]["2011-12"],
                    "deadline": "2011-06-29", "decision": "decline", "how": "test"}
        record = {"decisions": [decision]}
        self.assertEqual(options.apply(record, "2006-07", self.root, "2011-06-29"), [decision["id"]])
        put(self.root, f"{P}/2006-07/League/option_decisions.json", record)
        ledger = read(self.root, f"{P}/2006-07/League/contracts.json")["contracts"][0]
        row = read(self.root, f"{P}/2006-07/00_Team/Finances/contract_schedules.json")["players"][0]
        self.assertEqual((max(ledger["schedule"]), max(row["schedule"]), ledger.get("options")), ("2010-11", "2010-11", {}))
        (catalog, *_), = ext.catalog_rows(self.root)
        self.assertEqual((catalog["options"][0]["outcome"], catalog["options"][0]["outcome_date"]), ("declined", "2011-06-29"))
        bare = {k: v for k, v in row.items() if k not in ext.EXTENSION_FIELDS}       # a copy without the extension record
        self.assertEqual(ext.with_recorded(bare, self.root, "dwyane_wade")["extension"]["id"], d["id"])
        self.assertEqual(ext.extension_errors(self.root), [])

    def test_the_option_season_leaves_a_schedule_only_by_its_applied_decline(self):
        d = self.signed()
        ledger_rel = f"{P}/2006-07/League/contracts.json"
        ledger = read(self.root, ledger_rel)
        c = ledger["contracts"][0]
        c["schedule"].pop("2011-12")
        c["options"].pop("2011-12")
        put(self.root, ledger_rel, ledger)                  # the option season dropped with no decision of runtime/options.py
        lacks = f"lacks the signed extension {d['id']}"
        bare = {k: v for k, v in c.items() if k not in ext.EXTENSION_FIELDS}
        self.assertIn(lacks, "\n".join(ext.extension_errors(self.root)))
        self.assertNotIn("extension", ext.with_recorded(bare, self.root, "dwyane_wade"))
        rel = f"{P}/2006-07/League/option_decisions.json"
        decision = {"id": "2011-12-option-wadedw01-team_option", "club": "Miami Heat", "player": "Dwyane Wade",
                    "bbr_id": "wadedw01", "option_season": "2011-12", "kind": "team_option", "salary": 1,
                    "deadline": "2011-06-29", "how": "test"}
        for decided in (dict(decision, decision="decline"),                                   # not applied yet
                        dict(decision, decision="exercise", applied="2011-06-29")):           # kept: the season stays
            put(self.root, rel, {"decisions": [decided]})
            self.assertIn(lacks, "\n".join(ext.extension_errors(self.root)), decided)
            self.assertNotIn("extension", ext.with_recorded(bare, self.root, "dwyane_wade"))
        put(self.root, rel, {"decisions": [dict(decision, decision="decline", applied="2011-06-29")]})
        self.assertEqual(ext.extension_errors(self.root), [])
        self.assertEqual(ext.with_recorded(bare, self.root, "dwyane_wade")["extension"]["id"], d["id"])
        self.assertEqual(ext.option_declines(self.root, {"dwyane_wade"}), set())               # matched by his own keys
        self.assertEqual(ext.option_declines(self.root, {"wadedw01"}), {"2011-12"})

    def refused(self, rel, edit, *expected):
        """extension_errors after one edit of a record (restored afterwards); every expected message among them."""
        path = self.root / rel
        before = path.read_text()
        data = json.loads(before)
        edit(data)
        path.write_text(json.dumps(data, indent=1))
        try:
            errors = ext.extension_errors(self.root, replay=False)
        finally:
            path.write_text(before)
        self.assertTrue(errors, expected)
        for text in expected:
            self.assertTrue(any(text in e for e in errors), (text, errors))

    def test_tampering_with_his_terms_or_the_shaped_offer_is_refused(self):
        decided, *_ = ext.run("2006-10-31", self.root)
        self.assertEqual(ext.extension_errors(self.root), [])
        record = f"{P}/2006-07/League/extension_decisions.json"
        offer = ext.offer_path(self.root, "2006-07", self.oid).relative_to(self.root)
        on_file, shape = "differ from Wade's terms on file for 2006-10-31", "not Miami's answer to Wade's recorded terms"
        last = "one team option season, the last"

        def decision(edit):
            return lambda data: edit(data["decisions"][0])

        def offered(edit):
            return decision(lambda d: edit(d["offer"]))

        def shift(o, by):
            o["first_salary"] += by
            o["schedule"] = {s: v + by for s, v in o["schedule"].items()}
            o["total"] = sum(o["schedule"].values())

        def strip(o):
            for k in ext.SHAPED_FIELDS:
                o.pop(k)

        # the shaped offer: an option on a non-last season, two options, the guaranteed count, the first year, the basis
        self.refused(record, offered(lambda o: o.update(options={"2010-11": "team_option"}, team_option_season="2010-11")),
                     last, f"{shape} (`shape`): options differ", "the offer record and")
        self.refused(record, offered(lambda o: o.update(options={"2010-11": "team_option", "2011-12": "team_option"})), last)
        self.refused(record, offered(lambda o: o.update(options={"2011-12": "player_option"})), last)
        self.refused(record, offered(lambda o: o.update(guaranteed_seasons=5)),
                     "the guaranteed seasons and the team option season must follow")
        self.refused(record, offered(lambda o: shift(o, -100_000)),
                     "the first year does not follow the benchmark and the adopted discount", "first_salary, schedule differ")
        self.refused(record, offered(lambda o: o["terms_basis"].update(benchmark=12_455_000)),
                     "the benchmark must be his price", "terms_basis differ")
        self.refused(record, offered(lambda o: o["terms_basis"]["elements"][0].update(reason="edited")), "terms_basis differ")
        self.refused(record, offered(strip), "options, terms_basis differ")             # his terms on file, the rule's form
        # the decision's request: edited, removed, or none recorded while his terms were on file
        smaller = dict(TERMS, discount_from_market=0.10, additional_seasons=3, team_option_final_season=False)
        self.refused(record, decision(lambda d: d["request"].update(terms=smaller)), on_file, shape)
        self.refused(record, decision(lambda d: d.pop("request")), "records the extension terms on file for its day")
        self.refused(record, decision(lambda d: d.update(request=None)), on_file, "only Wade's own recorded terms shape an offer")
        # his request file: the row edited or removed after the decision, or a row filed for the day afterwards
        self.refused(REQUESTS, lambda r: r["requests"][0]["terms"].update(discount_from_market=0.25), on_file)
        self.refused(REQUESTS, lambda r: r["requests"][0].update(words="other words"), on_file)
        self.refused(REQUESTS, lambda r: r["requests"].pop(0), f"{on_file} (none)")
        self.refused(REQUESTS, lambda r: r["requests"].append(terms_row("2006-10-01", dict(TERMS, discount_from_market=0.10))),
                     f"{on_file} ({REQUESTS} row 1 of 2006-10-01)")
        # Wade's offer record: it must repeat the decision's offer and terms
        self.refused(offer, lambda r: r["offer"].update(options={}), "the offer record and")
        self.refused(offer, lambda r: r["request"].update(words="other words"), "the offer record and")
        # only Wade's own terms shape an offer
        other = dict(decided[0], wade=False)
        other.pop("request")
        self.assertIn("only Wade's own recorded terms shape an offer", "\n".join(ext._offer_errors(other, "test")))
        # a later filing (after the day) is the next negotiation's, never this one's: nothing refused
        file_terms(self.root, terms_row(), terms_row("2006-11-01", dict(TERMS, discount_from_market=0.30)))
        self.assertEqual(ext.extension_errors(self.root), [])


class TermsReplayTests(Scenario):
    """Wade's terms on file change no other player's decision: the 2005-10-31 day decides the same with them."""

    def test_the_day_replays_unchanged_with_his_terms_on_file(self):
        ext.run("2005-10-31", self.root)
        baseline = self.record()
        packets = {p.name: p.read_text() for p in (self.root / ext.draws_dir("2005-06")).glob("*.json")}
        tmp, root = scratch()
        self.addCleanup(tmp.cleanup)
        league_2005(root)
        file_terms(root)
        ext.clear_cache()
        ext._REPLAY.clear()
        self.assertIsNotNone(ext.terms_request("2005-10-31", root))
        ext.run("2005-10-31", root)
        again = read(root, f"{P}/2005-06/League/extension_decisions.json")
        self.assertEqual((again["days"], again["decisions"]), (baseline["days"], baseline["decisions"]))
        self.assertEqual({p.name: p.read_text() for p in (root / ext.draws_dir("2005-06")).glob("*.json")}, packets)
        self.assertFalse(any("request" in d or "terms_basis" in (d.get("offer") or {}) for d in again["decisions"]))
        self.assertEqual(ext.extension_errors(root), [])


# -- the live repository (read-only) and the gate --------------------------------------------------------------------------------
class LiveTests(unittest.TestCase):
    def test_origin_of_live_contracts(self):
        # pinned to the first extension day: an extension signed on or after it never changes the contract in force then
        day = "2005-10-31"
        o = ext.origin("wallabe01", "2005-06", ROOT, day=day)
        self.assertEqual((o["signed_date"], o["length"], o["extended"]), ("2000-08-03", 6, False))
        o = ext.origin("harrial01", "2005-06", ROOT, day=day)
        self.assertEqual((o["signed_date"], o["length"], o["extended"]), ("2001-11-01", 4, True))
        o = ext.origin("brownpj01", "2005-06", ROOT, day=day)
        self.assertEqual((o["signed_date"], o["length"]), ("2003-07-16", 4))
        o = ext.origin("thomaet01", "2005-06", ROOT, day=day)
        self.assertEqual((o["signed_date"], o["length"]), ("2004-07-14", 4))
        self.assertIsNone(ext.origin("houstal01", "2005-06", ROOT, day=day))  # a salary-pattern inventory row: no term recorded

    def test_live_eligible_set_on_2005_10_31(self):
        with live_season():
            eligible = ext.eligible("2005-10-31", ROOT)
        rookies = {c["player"] for c in eligible if c["kind"] == "rookie_scale"}
        veterans = {c["player"] for c in eligible if c["kind"] == "veteran"}
        self.assertEqual(len(rookies), 18)
        self.assertTrue({"Yao Ming", "Amar'e Stoudemire", "Caron Butler", "Tayshaun Prince"} <= rookies)
        self.assertEqual(veterans, {"Ben Wallace", "Cuttino Mobley", "Tony Delk", "Tony Battie", "Al Harrington", "Shaquille O'Neal"})
        names = rookies | veterans
        for out in ("Jason Terry", "Darko Milicic", "Allen Iverson", "Mike James", "Dwyane Wade", "Allan Houston"):
            self.assertNotIn(out, names)

    def test_the_recorded_day_is_untouched_by_wade_s_terms(self):
        # Wade was not eligible on 2005-10-31 (his option ran to 2006-07): no decision of that day reads his terms
        record = json.loads((ROOT / ext.record_path("2005-06")).read_text())
        day = [d for d in record["decisions"] if d["day"] == "2005-10-31"]
        self.assertEqual(len(day), 24)
        for d in day:
            self.assertFalse(d["wade"])
            self.assertNotIn("request", d)
            self.assertFalse(set(ext.SHAPED_FIELDS) & set(d.get("offer") or {}), d["id"])
            if d.get("offer"):
                self.assertEqual(ext._offer_errors(d, "live"), [])
        filed = ext.terms_request("2006-10-31", ROOT)                 # his terms, when filed, are read on his own day
        if filed is not None:
            self.assertEqual((filed["subject"], filed["path"].endswith("wade_requests.json")), ("extension_terms", True))
            self.assertLessEqual(filed["date"], "2006-10-31")

    def test_earlier_seasons_are_unchanged(self):
        from runtime.league_contracts import read as read_ledger
        for season in ("2003-04", "2004-05"):
            for c in (read_ledger(season, ROOT) or {}).values():
                self.assertNotIn("extension", c)
        for path in (ROOT / P).glob("*/League/contracts.json"):
            for c in json.loads(path.read_text())["contracts"]:
                self.assertTrue(all(e["signed_date"] >= ext.FIRST_DAY for e in ext.extensions_of(c)))
        for season in ("2003-04", "2004-05"):
            self.assertFalse((ROOT / ext.record_path(season)).exists())

    def test_a_contract_without_an_extension_reads_as_before(self):
        tmp, root = scratch()
        self.addCleanup(tmp.cleanup)
        put(root, f"{P}/2005-06/League/contracts.json", {"contracts": [
            {"player": "A", "bbr_id": "a01", "club": "Boston Celtics", "kind": "existing", "schedule": {"2005-06": 1, "2006-07": 2},
             "rookie_scale": True, "options": {"2006-07": "team_option"}}]})
        from runtime.league_contracts import carried
        self.assertEqual(carried("2006-07", root), {"a01": {
            "club": "Boston Celtics", "salary": 2, "kind": "contract", "option_kind": None, "schedule": {"2006-07": 2},
            "options": {"2006-07": "team_option"}, "rookie_scale": True, "source": f"{P}/2005-06/League/contracts.json (existing)"}})
        row = {"player": "A", "schedule": {"2005-06": 1}, "status": "under_contract"}
        self.assertEqual(ext.without_extension(row), row)
        self.assertEqual(ext.base_schedule(row), {"2005-06": 1})

    def test_no_day_before_the_gate_is_decided(self):
        tmp, root = scratch()
        self.addCleanup(tmp.cleanup)
        put(root, f"{P}/2005-06/current_state.json", {"season": "2005-06", "current_date": "2005-10-30"})
        self.assertEqual(ext.run("2005-10-30", root), ([], [], [], []))
        self.assertFalse((root / ext.record_path("2005-06")).exists())
        self.assertFalse((root / ext.record_path("2004-05")).exists())


if __name__ == "__main__":
    unittest.main()


class DriverTests(unittest.TestCase):
    """`scripts/advance.py` runs the extension step on every day before the options and the market, and turns the
    rollover's refusal for a missed or unresolved extension day into a stop."""

    def setUp(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("advance_for_extensions", ROOT / "scripts/advance.py")
        self.A = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.A)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = Path(self.tmp.name) / "current_state.json"
        self.state.write_text(json.dumps({"current_date": "2006-10-31", "pending_player_decisions": []}))

    def order(self, step):
        calls = []

        def fake_run(*args, ok=(0,), show=True):
            calls.append(args[0])
            if args[0] == "scripts/extension_day.py":
                return "EXTENSION Houston Rockets: Yao Ming 5 seasons from 2006-07 ($70,000,000)\nextensions: 1 decided, 0 draw packet(s) written, 1 applied, 0 waiting on Wade"
            if args[0] == "scripts/review_rotation.py":
                return "no review due"
            return "x"
        A = self.A
        out = io.StringIO()
        moves = mock.Mock(waive_by="2007-01-07", guarantee="2007-01-10")
        with mock.patch.object(A, "state_file", lambda: self.state), mock.patch.object(A, "run", fake_run), \
                mock.patch.object(A, "draws_pending", return_value=False), \
                mock.patch.multiple(A, draw=mock.DEFAULT, seed_playoffs=mock.DEFAULT, national_day=mock.DEFAULT,
                                    wade_waits=mock.DEFAULT, play=mock.DEFAULT, frozen_check=mock.DEFAULT,
                                    miami_trade_day=mock.DEFAULT, summary=mock.DEFAULT, close_day=mock.DEFAULT,
                                    checkpoint=mock.DEFAULT, commit=mock.DEFAULT, rollover_day=mock.DEFAULT), \
                mock.patch.object(A, "git", side_effect=AssertionError("the test must not run git")), \
                mock.patch("runtime.roster_moves.ctx", return_value=moves), redirect_stdout(out):
            try:
                step("2006-10-31")
            except AssertionError:
                raise
            except Exception:                            # later steps of a real day are outside this test
                pass
        return calls, out.getvalue()

    def test_every_day_type_runs_extensions_before_the_options_and_the_market(self):
        A = self.A
        for step in (A.camp_day, A.playoff_day):
            calls, out = self.order(step)
            self.assertIn("scripts/extension_day.py", calls, step.__name__)
            self.assertLess(calls.index("scripts/extension_day.py"), calls.index("scripts/option_day.py"), step.__name__)
            self.assertIn("    EXTENSION Houston Rockets: Yao Ming", out)
        with mock.patch.object(A, "season_dates", return_value={"regular_season_end": "2007-04-18", "opening_night": "2006-10-31",
                                                                  "training_camp_opens": "2006-10-03"}):
            calls, _ = self.order(A.advance_day)
        self.assertLess(calls.index("scripts/extension_day.py"), calls.index("scripts/league_day.py"))

    def test_a_refused_rollover_stops_the_run(self):
        A = self.A
        with mock.patch("runtime.rollover.Rollover.blockers", side_effect=ext.ExtensionError("extension day 2006-06-29 was missed")), \
                mock.patch.object(A, "run", side_effect=AssertionError("the test must not run a step")):
            with self.assertRaises(A.Stop) as stop:
                A.rollover_day("2006-09-30")
        self.assertIn("2006-06-29 was missed", str(stop.exception))


class MilestoneScreenTests(unittest.TestCase):
    """Wade's extension offer is listed on the Milestones contract screen with its reply version, from its date only."""

    def test_offer_listed_with_its_version_from_its_date(self):
        from types import SimpleNamespace
        from runtime import milestone_records as mr
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            season = root / P / "2006-07"
            record = {"id": "2006-10-31-wadedw01-extension", "date": "2006-10-31", "season": "2006-07", "club": "Miami Heat",
                      "offer": {"years": 5, "first_season": "2007-08", "first_salary": 9_600_000, "raise": 1_008_000,
                                "total": 58_080_000, "team_option_season": "2011-12"}, "answer": None, "answered": None}
            put(root, ext.offer_path(root, "2006-07", record["id"]).relative_to(root), record)

            def screens():
                return {k: {"sections": [], "actions": [], "status": "idle"}
                        for k in ("calendar", "contract_negotiation", "trade_update")}

            def context(on):
                return SimpleNamespace(root=root, player=root / P, season=season, state={},
                                       known=lambda d: bool(d) and d <= on, source=lambda *a: None, action=lambda *a: None,
                                       link=lambda path, label: {"label": label, "href": str(path)})
            with mock.patch.object(mr, "load_registry", return_value={"events": []}):
                before, after = screens(), screens()
                mr.augment_live_screens(context("2006-10-30"), before)
                mr.augment_live_screens(context("2006-10-31"), after)
            expected = mr.version(ext.offer_path(root, "2006-07", record["id"]))
        self.assertEqual(before["contract_negotiation"]["sections"], [])
        (section,) = after["contract_negotiation"]["sections"]
        row = section["rows"][0]
        self.assertEqual(row[0]["label"], record["id"])
        self.assertEqual(row[3], "5 seasons from 2007-08, $9,600,000 rising $1,008,000 ($58,080,000; 2011-12 a Miami team option)")
        self.assertEqual(row[4], "Awaiting your answer")
        self.assertEqual(row[5], expected)
        self.assertEqual(after["contract_negotiation"]["status"], "awaiting_response")
