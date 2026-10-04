"""Frozen game inputs (from 2004-01-22): a request carries both clubs' engine inputs, computed by the builder from the
dated records and frozen before the engine's own draws, so the engine needs no deployed copy of the career records."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from runtime import game_requests as G
from runtime.kernel import team_packet
from runtime.season_games import season_games, slate_request

ROOT = Path(__file__).resolve().parents[1]


def slate_game(day):
    return next(g for g in season_games() if g["date"] == day and "Miami Heat" not in (g["home"], g["away"]))


class FrozenInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls.tmp.name)
        cls.plain = slate_request(slate_game(G.FROZEN_FROM))
        cls.frozen = G.freeze(cls.plain)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def write(self, name, data):
        path = self.dir / name
        path.write_text(json.dumps(data))
        return path

    def test_the_engine_gets_exactly_the_inputs_the_records_give(self):
        home, away = G.computed_inputs(self.plain)
        loaded_home, loaded_away, _ = G.load_request(self.write("a.request.json", self.frozen))
        self.assertEqual(team_packet(loaded_home), team_packet(home))
        self.assertEqual(team_packet(loaded_away), team_packet(away))
        for side in (home, away):                                   # the round trip is exact
            self.assertEqual(team_packet(G.team_from_packet(json.loads(json.dumps(team_packet(side))))), team_packet(side))

    def test_the_engines_own_draws_are_not_frozen(self):
        for side in ("home", "away"):
            for p in self.frozen["frozen"][side]["players"]:
                self.assertNotIn("development", p["stat_profile"])   # swings are drawn in the engine journal
                self.assertIn(p["availability"], [p["availability"]])
        self.assertFalse(self.frozen["frozen"]["home"].get("season_roster", False))   # absence spells come in the engine

    def test_the_date_decides_the_form(self):
        early = slate_request(slate_game("2004-01-21"))
        self.assertIs(G.freeze(early), early)                      # earlier games keep their committed shape
        with self.assertRaises(ValueError):
            G.load_request(self.write("b.request.json", {**early, "frozen": self.frozen["frozen"]}))
        with self.assertRaises(ValueError):
            G.load_request(self.write("c.request.json", self.plain))  # from FROZEN_FROM the inputs must be frozen
        swapped = {**self.frozen, "frozen": {"home": self.frozen["frozen"]["away"], "away": self.frozen["frozen"]["home"]}}
        with self.assertRaises(ValueError):
            G.load_request(self.write("d.request.json", swapped))

    def test_the_fingerprint_reads_the_frozen_inputs(self):
        path = self.write("e.request.json", self.frozen)
        self.assertEqual(G.input_fingerprint(path), G.input_fingerprint(path))
        changed = json.loads(json.dumps(self.frozen))
        changed["frozen"]["home"]["players"][0]["minutes"] += 1
        self.assertNotEqual(G.input_fingerprint(self.write("f.request.json", changed)), G.input_fingerprint(path))


class FrozenValidationTests(unittest.TestCase):
    def test_validation_refuses_frozen_inputs_the_records_do_not_give(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for folder in ("library", "career", "foundation"):
                shutil.copytree(ROOT / folder, root / folder, ignore=shutil.ignore_patterns("*.html", "Players"))
            game = slate_game(G.FROZEN_FROM)
            path = root / "career/Dwyane_Wade/Stats_and_Awards/League/2003-04/Games" / f"{game['game_id']}.request.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            result = path.with_name(path.name.replace(".request.json", ".result.json"))
            if result.exists():
                result.unlink()
            good = G.freeze(slate_request(game), root)
            path.write_text(json.dumps(good, indent=1) + "\n")
            self.assertEqual([e for e in G.frozen_errors(root) if game["game_id"] in e], [])
            bad = json.loads(json.dumps(good))
            bad["frozen"]["away"]["players"][0]["minutes"] += 5
            path.write_text(json.dumps(bad, indent=1) + "\n")
            self.assertTrue([e for e in G.frozen_errors(root) if game["game_id"] in e and "differ" in e])


if __name__ == "__main__":
    unittest.main()
