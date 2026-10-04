"""In-season roster moves: game-day lists, the injured list, waivers and the January 10 guarantee review."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from runtime import roster_moves
from runtime.roster_moves import empty_ledger, game_day, games_missed, record_lists, waived_charge

ROOT = Path(__file__).resolve().parents[1]
DATES = ["2003-11-12", "2003-11-14", "2003-11-16", "2003-11-18", "2003-11-19", "2003-11-21", "2003-11-23"]


def depth(*names):
    return [{"name": n, "positions": ["SF"], "depth_position": "SF"} for n in names]


def rotation(*names):
    return [{"player_id": n, "position": "SF", "minutes": 20} for n in names]


class GameDayTests(unittest.TestCase):
    roster = [f"P{i:02d}" for i in range(1, 16)]          # 15 playable players in depth order

    def test_twelve_dress_and_the_lowest_reserves_fill_the_list(self):
        actives, il, placements, activations = game_day(DATES[0], rotation(*self.roster[:11]), depth(*self.roster), {}, empty_ledger(), DATES)
        self.assertEqual(len(actives), 12)
        self.assertEqual(actives[-1], "P12")                # the twelfth man dresses
        self.assertEqual(il, ["P15", "P14", "P13"])
        self.assertEqual({why for _, why in placements}, {"reserve"})
        self.assertEqual(activations, [])

    def test_an_injured_player_takes_a_place_on_the_list_and_stays_five_games(self):
        data = empty_ledger()
        kept = rotation(*[n for n in self.roster[:11] if n != "P03"])
        actives, il, placements, _ = game_day(DATES[0], kept, depth(*self.roster), {"P03": 2}, data, DATES)
        self.assertIn("P03", il)
        self.assertNotIn("P03", actives)
        record_lists(data, DATES[0], il, placements, [], {"P03": 2}, "g1")
        # Healthy again two games later, he still has to sit out five games on the list.
        self.assertIn("P03", roster_moves.held_on_list(data, DATES[2], DATES))
        self.assertNotIn("P03", roster_moves.held_on_list(data, DATES[5], DATES))
        entry = next(e for e in data["entries"] if e["player"] == "P03")
        self.assertEqual(games_missed(entry, DATES[5], DATES), 5)

    def test_reserves_already_on_the_list_stay_rather_than_churn(self):
        data = empty_ledger()
        record_lists(data, DATES[0], ["P13", "P14", "P15"], [("P13", "reserve"), ("P14", "reserve"), ("P15", "reserve")], [], {}, "g1")
        _, il, placements, activations = game_day(DATES[6], rotation(*self.roster[:11]), depth(*self.roster), {}, data, DATES)
        self.assertEqual(sorted(il), ["P13", "P14", "P15"])
        self.assertEqual((placements, activations), ([], []))


class LiveListTests(unittest.TestCase):
    def test_the_next_game_dresses_at_most_twelve_and_lists_the_rest(self):
        from runtime import season_games
        due = [r for r in season_games.miami_games_due("2004-04-14", ROOT) if r["game"]["date"] >= roster_moves.LISTS_FROM]
        if not due or season_games.miami_requests_without_results(ROOT):
            self.skipTest("no buildable game")
        players, injured, lists = season_games.miami_side(due[0]["game"]["date"], ROOT, with_lists=True)
        names = [p["player_id"] for p in players]
        self.assertLessEqual(len(names), roster_moves.GAME_DAY_ACTIVES)
        self.assertLessEqual(len(lists["injured_list"]), roster_moves.IL_MAX)
        self.assertFalse(set(names) & set(lists["injured_list"]))
        self.assertAlmostEqual(sum(p["minutes"] for p in players), 240)


class WaiverTests(unittest.TestCase):
    def test_a_non_guaranteed_waiver_costs_the_days_on_the_roster(self):
        entry = {"schedule": {"2003-04": 688679}, "guaranteed": {"2003-04": 0}}
        self.assertEqual(waived_charge(entry, "2003-10-28"), 0)
        self.assertTrue(0 < waived_charge(entry, roster_moves.WAIVE_BY) < 688679)
        self.assertEqual(waived_charge({"schedule": {"2003-04": 688679}, "guaranteed": {"2003-04": 688679}}, "2004-02-01"), 688679)


class GuaranteeReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        for folder in ("library", "career", "foundation"):
            shutil.copytree(ROOT / folder, cls.root / folder)
        live = cls.root / roster_moves.GUARANTEES               # the live career's own review is not this test's
        if live.exists():
            live.unlink()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def clock(self, day):
        path = self.root / "career/Dwyane_Wade/2003-04/current_state.json"
        state = json.loads(path.read_text())
        state["current_date"] = day
        path.write_text(json.dumps(state, indent=1))

    def test_the_builder_waits_for_the_review_and_kept_contracts_become_guaranteed(self):
        self.assertIsNone(roster_moves.required_before(roster_moves.WAIVE_BY, self.root))
        self.assertIn("guarantee review", roster_moves.required_before("2004-01-08", self.root))
        from scripts.guarantee_review import review
        self.clock("2004-01-10")
        with unittest.mock.patch("scripts.guarantee_review.refresh_career_views", return_value=[]):
            review(self.root, "2004-01-10")
        record = json.loads((self.root / roster_moves.GUARANTEES).read_text())
        self.assertEqual(record["decided_on"], roster_moves.WAIVE_BY)
        self.assertEqual(record["guaranteed_on"], "2004-01-10")
        self.assertTrue(all(d["decision"] == "keep" for d in record["decisions"]))      # Miami is under its ceiling
        self.assertIn("Udonis Haslem", [g["player"] for g in record["guaranteed"]])
        self.assertIsNone(roster_moves.required_before("2004-01-12", self.root))
        self.assertEqual(roster_moves.guarantee_errors(self.root), [])
        sheet = json.loads((self.root / "career/Dwyane_Wade/2003-04/00_Team/Finances/contract_schedules.json").read_text())
        haslem = next(p for p in sheet["players"] if p["player"] == "Udonis Haslem")
        self.assertEqual(haslem["guaranteed"]["2003-04"], haslem["schedule"]["2003-04"])

    def test_over_the_ceiling_the_lowest_valued_are_waived_and_the_books_keep_their_days(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for folder in ("library", "career", "foundation"):
                shutil.copytree(self.root / folder, root / folder)
            config = root / "career/Dwyane_Wade/2003-04/00_Team/team_config.json"
            data = json.loads(config.read_text())
            data.setdefault("budget", {})["payroll_ceiling"] = 43000000
            config.write_text(json.dumps(data, indent=1))
            state = root / "career/Dwyane_Wade/2003-04/current_state.json"
            s = json.loads(state.read_text()); s["current_date"] = roster_moves.WAIVE_BY; state.write_text(json.dumps(s))
            from scripts.guarantee_review import review
            with unittest.mock.patch("scripts.guarantee_review.refresh_career_views", return_value=[]):
                review(root, roster_moves.WAIVE_BY)
            record = json.loads((root / roster_moves.GUARANTEES).read_text())
            waived = [d for d in record["decisions"] if d["decision"] == "waive"]
            self.assertTrue(waived)
            sheet = json.loads((root / "career/Dwyane_Wade/2003-04/00_Team/Finances/contract_schedules.json").read_text())
            entry = next(p for p in sheet["players"] if p["player"] == waived[0]["player"])
            self.assertEqual(entry["status"], "waived")
            self.assertEqual(entry["cap_amount"]["2003-04"], waived[0]["charge"])
            from runtime.signing import ledger_errors
            self.assertEqual(ledger_errors(root), [])
            roster = json.loads((root / "career/Dwyane_Wade/2003-04/00_Team/Team/Roster/roster.json").read_text())
            self.assertEqual(next(p for p in roster["players"] if p["name"] == entry["player"])["status"], "waived")

    def test_the_review_is_never_written_ahead_of_the_clock(self):
        from scripts.guarantee_review import review
        self.clock("2003-11-11")
        with self.assertRaises(SystemExit):
            review(self.root, roster_moves.WAIVE_BY)


import unittest.mock  # noqa: E402

if __name__ == "__main__":
    unittest.main()
