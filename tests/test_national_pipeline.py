"""The national pipeline end to end on the 2005 FIBA Americas Championship, in a scratch copy of the career: every day
from the record's opening to the final, each game resolved by the kernel with test entropy (a stand-in for the engine,
which the production runner never allows). Nothing is written to the repository."""
from datetime import date, timedelta
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
EDITION = "continental_qualifier_2005"


def scratch_root():
    """A temporary root: every repository entry linked, except the folders the pipeline writes."""
    tmp = Path(tempfile.mkdtemp(prefix="national-"))
    for entry in ROOT.iterdir():
        if entry.name not in ("career", ".git"):
            os.symlink(entry, tmp / entry.name)
    player = tmp / "career/Dwyane_Wade"
    player.mkdir(parents=True)
    for entry in (ROOT / "career").iterdir():
        if entry.name != "Dwyane_Wade":
            os.symlink(entry, tmp / "career" / entry.name)          # followed players (Chris Bosh's profiles)
    for entry in (ROOT / "career/Dwyane_Wade").iterdir():
        if entry.name not in ("FIBA", "National_Team"):
            os.symlink(entry, player / entry.name)
    (player / "National_Team").mkdir()
    shutil.copy(ROOT / "career/Dwyane_Wade/National_Team/wade_standing_rule.json", player / "National_Team")
    return tmp


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from runtime import national
        from runtime.era import national_rules
        from runtime.game_requests import load_request
        from runtime.kernel import resolve_game
        from runtime.national_engine import national_environment, national_spatial
        cls.root = scratch_root()
        cls.e = national.editions(cls.root)[EDITION]
        day = date.fromisoformat(national.selection_date(cls.e))
        while day.isoformat() <= cls.e["last_game"]:
            d = day.isoformat()
            lines, pending = national.day(d, cls.root)
            assert not pending, pending
            rec = national.read_record(cls.e, cls.root)
            for g in rec["games"].values():
                if g["date"] != d or not g.get("home"):
                    continue
                _, request, result = national.game_paths(cls.e, rec, g, cls.root)
                home, away, kw = load_request(request, cls.root)
                r = resolve_game(home, away, entropy=hashlib.sha256(f"test:{kw['event_id']}".encode()).digest(),
                                 event_id=kw["event_id"], rules=national_rules(d), environment=national_environment(d, cls.root),
                                 game_type=kw["game_type"], venue=kw["venue"], spatial_environment=national_spatial(d, cls.root))
                r["game_date"] = d
                result.write_text(json.dumps(r))
            national.after_games(d, cls.root)
            day += timedelta(days=1)
        cls.rec = national.read_record(cls.e, cls.root)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root, ignore_errors=True)

    def test_every_game_is_played_and_the_tournament_closes(self):
        from runtime import national
        self.assertEqual(len(national.results(self.e, self.rec, self.root)), 40)
        self.assertTrue(self.rec["closed"])
        self.assertEqual(len(self.rec["ranking"]), 10)
        self.assertEqual(self.rec["ranking"][0], self.rec["awards"]["champion"])
        self.assertEqual(len(self.rec["awards"]["all_tournament"]), 5)

    def test_second_round_carries_first_round_results(self):
        table = self.rec["tables"]["R"]
        self.assertEqual(len(table), 8)
        self.assertTrue(all(r["w"] + r["l"] == 7 for r in table))     # four new games and three carried

    def test_bracket_follows_the_tables(self):
        from runtime import national
        final_r = national.tables(self.e, self.rec, national.results(self.e, self.rec, self.root))["R"]
        semis = [g for g in self.rec["games"].values() if g["stage"] == "semifinal"]
        top4 = {r["team"] for r in final_r if r["position"] <= 4}
        self.assertEqual({t for g in semis for t in (g["home"], g["away"])}, top4)

    def test_usa_plays_its_real_2005_roster(self):
        usa = self.rec["rosters"]["United States"]["players"]
        self.assertEqual(len(usa), 12)
        self.assertNotIn("wadedw01", {p.get("bbr_id") for p in usa})
        self.assertIsNone(self.rec["selection"])

    def test_pages_are_written(self):
        page = (self.root / "career/Dwyane_Wade/FIBA/Continental_Cups/2005/README.md").read_text(encoding="utf-8")
        self.assertIn("Final placings and honors", page)
        self.assertIn("Second round", page)
        self.assertTrue((self.root / "career/Dwyane_Wade/FIBA/README.md").is_file())


if __name__ == "__main__":
    unittest.main()
