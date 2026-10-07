"""2004 playoffs: seeding by the 2003-04 rules, tiebreakers, home court and the first-round calendar."""
import json
from pathlib import Path
import tempfile
import unittest

from runtime import playoffs as P

ROOT = Path(__file__).resolve().parents[1]


def table(results):
    """A Table from (home, away, winner) tuples; one-point margins."""
    t = object.__new__(P.Table)
    t.root, t.where = ROOT, P.divisions(ROOT)
    t.games = [(h, a, w, 1 if w == h else -1) for h, a, w in results]
    t.clubs = sorted(t.where)
    return t


class PlayoffRuleTests(unittest.TestCase):
    def test_rules_file_holds_the_2003_04_structure(self):
        cfg = P.rules(ROOT)
        self.assertEqual(sum(len(c) for conf in ("East", "West") for c in cfg["divisions"][conf].values()), 29)
        self.assertEqual(cfg["bracket"]["first_round"], [[1, 8], [4, 5], [3, 6], [2, 7]])
        self.assertEqual(cfg["home_court"]["conference_rounds"]["home_team_games"], [1, 2, 5, 7])
        self.assertEqual(cfg["calendar"]["finals"]["game_1"], "2004-06-06")

    def test_head_to_head_breaks_a_two_team_tie(self):
        t = table([("Boston Celtics", "Miami Heat", "Miami Heat"), ("Miami Heat", "Atlanta Hawks", "Atlanta Hawks"),
                   ("Boston Celtics", "Chicago Bulls", "Boston Celtics")])     # both 1-1; Miami beat Boston
        self.assertEqual(P.Ranker(t, ROOT).order(["Boston Celtics", "Miami Heat"]), ["Miami Heat", "Boston Celtics"])

    def test_division_winner_breaks_a_tie_only_after_head_to_head(self):
        t = table([("Boston Celtics", "Miami Heat", "Miami Heat"), ("Miami Heat", "Boston Celtics", "Boston Celtics")])
        ranker = P.Ranker(t, ROOT, winners=["Boston Celtics"])
        self.assertEqual(ranker.order(["Miami Heat", "Boston Celtics"]), ["Boston Celtics", "Miami Heat"])

    def test_an_unbreakable_tie_is_an_engine_drawing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / P.rules_path('2003-04')).parent.mkdir(parents=True)
            (root / P.rules_path('2003-04')).write_text((ROOT / P.rules_path('2003-04')).read_text())
            t = table([])
            ranker = P.Ranker(t, root)
            ranker.order(["Boston Celtics", "Miami Heat"])
            self.assertEqual(len(ranker.pending), 1)
            packet = json.loads(next((root / P.draws_dir('2003-04')).glob("*.decision.json")).read_text())
            self.assertAlmostEqual(sum(packet["options"].values()), 1.0)

    def test_the_seeded_record_shape_and_calendar(self):
        record, pending = P.build(ROOT, write=False)
        if pending:
            self.skipTest("a live tiebreak drawing is pending")
        for conf in ("East", "West"):
            rows = record["seeds"][conf]
            self.assertEqual([r["seed"] for r in rows], list(range(1, 9)))
            self.assertTrue(rows[0]["division_winner"] and rows[1]["division_winner"])
            self.assertFalse(any(r["division_winner"] for r in rows[2:]))
        for s in record["series"]:
            self.assertEqual(len(s["games"]), 7)
            hosts = [g["home"] for g in s["games"]]
            self.assertEqual([i + 1 for i, h in enumerate(hosts) if h == s["home_court"]], [1, 2, 5, 7])
            self.assertEqual([g["conditional"] for g in s["games"]], [False] * 4 + [True] * 3)
            self.assertIn(s["games"][0]["date"], ("2004-04-17", "2004-04-18"))
            days = [g["date"] for g in s["games"]]
            self.assertEqual(days, sorted(days))



class BuildWritesTests(unittest.TestCase):
    def test_build_with_write_saves_through_the_module_writer(self):
        """Regression (April 2005): `build(write=True)` called its own boolean flag instead of the writer."""
        from unittest import mock
        from runtime import playoffs
        bracket = {"seeded": {"East": [], "West": []}, "series": []}
        saved = []
        with mock.patch.object(playoffs, "first_round", return_value=(bracket, [])), \
                mock.patch.object(playoffs, "rules", return_value={"calendar": {"regular_season_last_day": "2005-04-20"}}), \
                mock.patch.object(playoffs, "_write_record", side_effect=lambda record, root: saved.append(record)), \
                mock.patch.object(playoffs, "league_dir", return_value=__import__("pathlib").Path("nowhere/x")):
            record, pending = playoffs.build("/nonexistent-root", "2004-05", write=True)
        self.assertEqual(pending, [])
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["seeded_on"], "2005-04-20")


if __name__ == "__main__":
    unittest.main()
