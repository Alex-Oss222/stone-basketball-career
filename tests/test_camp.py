import json
import shutil
import tempfile
import unittest
from pathlib import Path

from runtime import camp, signing
from runtime.decisions import decision_errors
from runtime.gm import FrontOffice
from runtime.market import Market
from runtime.private_service import Store, play_requests
from runtime.rookie_contract import rookie_terms
from runtime.rotations import holdings_errors
from runtime.signing import ledger_errors
from scripts.run_camp import CampRun
from scripts.run_free_agency import local_draw

ROOT = Path(__file__).resolve().parents[1]


def copy_repo():
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    shutil.copytree(ROOT / "library", root / "library")
    shutil.copytree(ROOT / "career", root / "career")
    return tmp, root


def play_local(store, root):
    """Test helper: play requests and draw decisions with a local store, writing result files like the collector."""
    status = play_requests(store, root)
    for path in sorted((root / "career").rglob("*.request.json")):
        result = path.with_name(path.name.replace(".request.json", ".result.json"))
        event = json.loads(path.read_text(encoding="utf-8"))["event_id"]
        if not result.exists() and store.result(event) is not None:
            result.write_text(json.dumps(store.result(event)) + "\n", encoding="utf-8")
    local_draw(store, root)
    return status


class CampUnitTests(unittest.TestCase):
    def test_injury_and_battle_packets_are_valid(self):
        packet = camp.injury_packet({"player": "Test Player", "bbr_id": "testpl01"}, 34)
        self.assertEqual(decision_errors(packet), [])
        self.assertAlmostEqual(packet["options"]["injured"], 0.05)
        roster = {"players": [{"player": "A", "positions": ["PG"], "status": "roster"}, {"player": "B", "positions": ["PG"], "status": "roster"},
                              {"player": "C", "positions": ["SG"], "status": "roster"}]}
        packets = camp.battle_packets(roster, {"A": 10.0, "B": 9.5, "C": 8.0}, "2003-10-24")
        self.assertEqual([p["event_id"] for p in packets], ["2003-camp-pg-starter"])
        self.assertEqual(decision_errors(packets[0]), [])
        self.assertEqual(camp.battle_packets(roster, {"A": 10.0, "B": 8.0, "C": 8.0}, "2003-10-24"), [])

    def test_rotation_dresses_twelve_for_240_minutes(self):
        players = [{"player": f"P{i}", "bbr_id": None, "positions": [camp.POSITIONS[i % 5]], "status": "roster", "injured_through": None} for i in range(18)]
        data = {"players": players}
        depth = {"positions": {pos: [f"P{i}" for i in range(18) if i % 5 == camp.POSITIONS.index(pos)] for pos in camp.POSITIONS}}
        values = {f"P{i}": 18 - i for i in range(18)}
        first = camp.rotation_players(data, depth, values, "2003-10-07", camp.PRESEASON_MINUTES, game_index=0)
        second = camp.rotation_players(data, depth, values, "2003-10-10", camp.PRESEASON_MINUTES, game_index=1)
        self.assertEqual(len(first), 12)
        self.assertAlmostEqual(sum(p["minutes"] for p in first), 240)
        self.assertEqual([p["player_id"] for p in first[:camp.CORE_SIZE]], [p["player_id"] for p in second[:camp.CORE_SIZE]])
        self.assertNotEqual([p["player_id"] for p in first], [p["player_id"] for p in second])
        self.assertEqual(camp.rotation_players(data, depth, values, "2003-10-07", camp.PRESEASON_MINUTES, {"P0": 55})[0]["ratings"], {"perimeter_defense": 55})

    def test_wade_grade_stays_inside_its_limits(self):
        quiet = camp.wade_grade({})
        self.assertEqual(quiet["grade"], camp.WADE_GRADE_BASE)
        busy = camp.wade_grade({"Dwyane Wade": {"minutes": 120.0, "games": 5, "efficiency": 60, "stl": 12, "blk": 4}})
        self.assertEqual(busy["grade"], camp.WADE_GRADE_BASE + camp.WADE_GRADE_CAMP_SWING)
        self.assertAlmostEqual(busy["defense"], (busy["grade"] - 50) / 10)
        for g in (quiet, busy):
            self.assertTrue(camp.WADE_GRADE_LIMITS[0] <= g["grade"] <= camp.WADE_GRADE_LIMITS[1])


class CampRunTests(unittest.TestCase):
    def test_camp_through_the_cut(self):
        tmp, root = copy_repo()
        self.addCleanup(tmp.cleanup)
        store = Store(root / "data/e.sqlite3")
        store.initialize()
        writer = signing.Writer(root)
        signing.open_market(writer, "2003-07-01")                  # the register as free agency leaves it
        signing.sign_rookie(writer, {"entries": []}, rookie_terms(5, 120, root), "2003-07-20")
        writer.commit()
        stops = CampRun(root).write("2003-09-30")
        self.assertTrue(stops and "injury draws" in stops[0])
        data = json.loads((root / camp.CAMP_ROSTER).read_text())
        self.assertLessEqual(len(data["players"]), camp.CAMP_MAX)
        self.assertTrue(all(p["contract"]["guaranteed"] == 0 for p in data["players"] if p["kind"] == "invite"))
        first = play_local(store, root)
        self.assertEqual({v["status"] for v in first.values()}, {"decided"})
        self.assertEqual({v["status"] for v in play_local(store, root).values()}, {"already_decided"})   # a draw is never repeated
        self.assertEqual(CampRun(root).write("2003-10-05"), [])
        requests = sorted((root / camp.PRESEASON).glob("Game_*.request.json"))
        self.assertEqual(len(requests), 7)
        self.assertTrue((root / camp.PRESEASON / "Game_1.md").exists())
        stops = CampRun(root).write("2003-10-24")
        self.assertIn("preseason results", stops[0])
        status = play_local(store, root)
        self.assertEqual({v["status"] for k, v in status.items() if "at-" in k}, {"played"})
        for _ in range(3):
            stops = CampRun(root).write("2003-10-24")
            if not stops:
                break
            play_local(store, root)
        self.assertEqual(stops, [])
        depth = json.loads((root / signing.TEAM / "Team/Depth_Chart/depth_chart.json").read_text())
        self.assertTrue(depth["game_ready"])
        rotation = json.loads((root / camp.ROTATION).read_text())
        self.assertAlmostEqual(sum(p["minutes"] for p in rotation["players"]), 240)
        grades = json.loads((root / camp.GRADES).read_text())
        self.assertEqual(grades["players"][0]["player"], "Dwyane Wade")
        self.assertEqual(grades["players"][0]["from"], "2003-10-24")
        self.assertTrue((root / camp.CAMP / "Wade_Camp_Review.md").exists())
        self.assertEqual(CampRun(root).write("2003-10-27"), [])
        data = json.loads((root / camp.CAMP_ROSTER).read_text())
        self.assertEqual(data["status"], "closed")
        self.assertLessEqual(sum(1 for p in data["players"] if p["status"] != "released"), camp.ROSTER_MAX)
        self.assertTrue((root / camp.PROMISES).exists())
        self.assertEqual(holdings_errors(root), [])
        self.assertEqual(ledger_errors(root), [])
        # A game on or after the grade's date carries Wade's defensive value; one before does not.
        from runtime.player_stats import load_rating_index
        self.assertEqual(load_rating_index("2003-10-28", "2003-04", root).engine_profile("Dwyane Wade").get("defense"), grades["players"][0]["defense"])
        self.assertIsNone(load_rating_index("2003-10-07", "2003-04", root).engine_profile("Dwyane Wade").get("defense"))


if __name__ == "__main__":
    unittest.main()
