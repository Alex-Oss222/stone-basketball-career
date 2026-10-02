import json
import shutil
import tempfile
import unittest
from pathlib import Path

from runtime.decisions import decision_errors
from runtime.gm import FrontOffice
from runtime.market import Market
from runtime.private_service import Store
from runtime.rotations import holdings_errors, miami_departures, real_rotation, load_rosters
from runtime.signing import ledger_errors
from runtime.trades import Assets, TradeDesk
from scripts import run_trade
from scripts.run_free_agency import local_draw

ROOT = Path(__file__).resolve().parents[1]
DAY = "2003-07-20"


def copy_repo():
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    shutil.copytree(ROOT / "library", root / "library")
    shutil.copytree(ROOT / "career", root / "career")
    return tmp, root


class TradeDeskTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.desk = TradeDesk(DAY, FrontOffice(DAY, Market(DAY)))

    def test_legality_names_its_rules(self):
        errors = self.desk.errors({"partner": "Los Angeles Lakers", "miami_out": ["Dwyane Wade", "Eddie Jones"], "miami_in": ["Kobe Bryant"],
                                   "picks_out": [{"year": 2004, "round": 1}, {"year": 2005, "round": 1}], "picks_in": [], "cash_out": 5000000})
        text = " ".join(errors)
        self.assertIn("Dwyane Wade", text)
        self.assertIn("cash above $3,000,000", text)
        self.assertIn("Stepien", text)
        self.assertIn("after the 2004-02-19 trade deadline", " ".join(TradeDesk("2004-02-20", FrontOffice("2004-02-20", Market("2004-02-20"))).errors(
            {"partner": "Denver Nuggets", "miami_out": ["Eddie Jones"], "miami_in": ["Nene Hilario"]})))
        self.assertIn("moratorium", " ".join(TradeDesk("2003-07-05", FrontOffice("2003-07-05", Market("2003-07-05"))).errors(
            {"partner": "Denver Nuggets", "miami_out": ["Eddie Jones"], "miami_in": ["Nene Hilario"]})))
        self.assertEqual(self.desk.errors({"partner": "Denver Nuggets", "miami_out": ["Eddie Jones"], "miami_in": ["Nene Hilario"]}), [])

    def test_salary_matching_over_the_cap(self):
        # Caron Butler's rookie salary cannot bring back a $5M+ player while Miami stays over the cap.
        errors = self.desk.errors({"partner": "Orlando Magic", "miami_out": ["Caron Butler"], "miami_in": ["Grant Hill"]})
        self.assertTrue(any("115%" in e for e in errors), errors)

    def test_values_and_packet(self):
        jones = self.desk.assets.player_value(self.desk.miami_player("Eddie Jones")[0])
        self.assertGreater(jones["production"], 0)
        self.assertLess(jones["contract_term"], 0)                     # paid above the comparables price
        self.assertEqual(Assets.premium([0.5, 2.0]), 0.5 + 2.0 ** 7)
        pick = self.desk.assets.pick_value({"year": 2004, "round": 1}, "Miami Heat", miami_own=True)
        self.assertGreater(pick["value"], self.desk.assets.pick_value({"year": 2004, "round": 1}, "San Antonio Spurs")["value"])
        packet, valuation = self.desk.acceptance_packet({"partner": "Denver Nuggets", "miami_out": ["Eddie Jones"], "miami_in": ["Nene Hilario"]})
        self.assertEqual(decision_errors(packet), [])
        self.assertEqual(valuation["posture"], "rebuilding")
        self.assertTrue(-1 <= valuation["partner_gain"] <= 1)
        again, _ = self.desk.acceptance_packet({"partner": "Denver Nuggets", "miami_out": ["Eddie Jones"], "miami_in": ["Nene Hilario"]})
        self.assertEqual(packet, again)                                  # same proposal, same date, same packet

    def test_search_ranks_legal_proposals(self):
        found = self.desk.search(requests=[{"subject": "trade_target", "player": "Latrell Sprewell"}], limit=5)
        self.assertTrue(found)
        for f in found:
            self.assertEqual(self.desk.errors(f["trade"]), [])
            self.assertGreater(f["miami_gain"], 0)
            self.assertTrue(0.02 <= f["accept"] <= 0.9)


class TradeWriteBackTests(unittest.TestCase):
    def test_proposal_draw_and_write_back(self):
        tmp, root = copy_repo()
        self.addCleanup(tmp.cleanup)
        store = Store(root / "data/e.sqlite3")
        store.initialize()
        writer = run_trade.signing.Writer(root)          # the register as free agency leaves it on July 1
        run_trade.signing.open_market(writer, "2003-07-01")
        writer.commit()
        record = run_trade.propose(DAY, root)
        self.assertIsNotNone(record)
        folder = root / "career/Dwyane_Wade/2003-04/00_Team/Transactions/Trades"
        self.assertTrue((folder / f"{record['decision_event']}.decision.json").exists())
        applied, pending = run_trade.write(DAY, root)
        self.assertEqual(applied, [])
        self.assertEqual(pending, [record["decision_event"]])
        local_draw(store, root)
        applied, pending = run_trade.write("2003-07-22", root)
        self.assertEqual(pending, [])
        self.assertEqual(len(applied), 1)
        trade_id, status = applied[0]
        self.assertIn(status, ("completed", "declined"))
        saved = json.loads((folder / f"{trade_id}.json").read_text())
        self.assertEqual(saved["status"], status)
        if status == "completed":
            trade = saved["trade"]
            roster = json.loads((root / "career/Dwyane_Wade/2003-04/00_Team/Team/Roster/roster.json").read_text())
            statuses = {p["name"]: p["status"] for p in roster["players"]}
            for name in trade["miami_out"]:
                self.assertEqual(statuses[name], "traded")
            for name in trade["miami_in"]:
                self.assertEqual(statuses[name], "under_contract")
                self.assertTrue((root / "career/Dwyane_Wade/2003-04/00_Team/Team/Player_Cards" / f"{run_trade.signing.slug(name)}.md").exists())
            departures = json.loads((root / "career/Dwyane_Wade/2003-04/00_Team/Team/Roster/departures.json").read_text())
            self.assertEqual({e["player"] for e in departures["entries"]}, set(trade["miami_out"]))
            arrivals = miami_departures("2003-04", trade["partner"], "2003-11-15", root)
            self.assertEqual({a["player_id"] for a in arrivals}, set(trade["miami_out"]))
            rosters = load_rosters("2003-04", root)
            team = real_rotation(trade["partner"], rosters[trade["partner"]], 82, None, fraction=0.2, arrivals=arrivals)
            self.assertTrue(set(trade["miami_out"]) <= {p.player_id for p in team.players})
            self.assertEqual(holdings_errors(root), [])
            self.assertEqual(ledger_errors(root), [])


if __name__ == "__main__":
    unittest.main()
