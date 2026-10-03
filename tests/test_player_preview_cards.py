import json
import unittest
from pathlib import Path
from xml.etree import ElementTree

from runtime.stat_layout import PER_GAME_COLUMNS
from scripts.build_player_preview import annual_awards, build_preview
from scripts.validate_repository import markdown_tables


ROOT = Path(__file__).resolve().parents[1]


class PlayerPreviewCardsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outputs = build_preview(ROOT)
        cls.folder = ROOT / "docs/examples"
        cls.data = json.loads(cls.outputs[cls.folder / "player_cards_data.json"])

    def test_clickable_markdown_banners_preserve_every_statistics_column(self):
        page = self.outputs[self.folder / "sample_week.md"]
        self.assertIn("[![Shooting:", page)
        self.assertIn("](sample_shooting.md#week)", page)
        self.assertIn("[![Awards:", page)
        self.assertIn("](sample_awards.md)", page)
        self.assertIn("player_cards_preview.html?period=week#shooting", page)
        self.assertNotIn("![Per-game player statistics]", page)
        table = next(headers for headers, _ in markdown_tables(page) if headers[0] == "Scope")
        self.assertEqual(table, PER_GAME_COLUMNS)
        strip = self.outputs[self.folder / "assets/per_game.svg"]
        self.assertNotIn("Production", strip)
        self.assertNotIn("Honors", strip)
        header = self.outputs[self.folder / "assets/personal_2003-11-12.svg"]
        self.assertIn("EARNED CAREER AWARDS", header)

    def test_period_shots_reconcile_with_the_existing_boxes(self):
        periods = {p["id"]: p for p in self.data["periods"]}
        self.assertEqual(len(periods), 10)
        for pid, expected in (("season", (51, 104, 7, 19, 6)),
                              ("month", (43, 87, 6, 16, 5)),
                              ("week", (27, 54, 4, 10, 3))):
            p = periods[pid]
            self.assertEqual(tuple(p["box"][k] for k in ("fgm", "fga", "tpm", "tpa")) + (p["appearances"],), expected)
            self.assertEqual(len(p["shots"]), p["box"]["fga"])
            self.assertEqual(sum(s["made"] for s in p["shots"]), p["box"]["fgm"])
            self.assertEqual(sum(z["fga"] for z in p["shooting"]["zones"]), p["box"]["fga"])
            self.assertEqual(sum(z["fg_points"] for z in p["shooting"]["zones"]), 2 * p["box"]["fgm"] + p["box"]["tpm"])
        dnp = periods["dnp"]
        self.assertEqual((dnp["appearances"], dnp["shots"], dnp["shooting"]["bins"]), (0, [], []))
        self.assertIsNone(dnp["shooting"]["totals"]["fg_pct"])
        self.assertIsNone(dnp["shooting"]["totals"]["fga_per_game"])

    def test_annual_awards_require_scope_season_earned_state_and_cutoff(self):
        current, demo = self.data["awards"]["scenarios"]
        self.assertEqual(annual_awards(current["records"], current["season"], current["cutoff"]), [])
        self.assertEqual(len(annual_awards(demo["records"], demo["season"], demo["cutoff"])), 2)
        self.assertEqual(annual_awards(demo["records"], "2003-04", "2005-06-30"), [])
        self.assertEqual(annual_awards(demo["records"], "2004-05", "2005-05-19"), [])
        known = annual_awards(demo["records"], "2004-05", "2005-05-22")
        self.assertEqual([a["short_name"] for a in known], ["ALL-NBA 3RD"])
        self.assertNotIn("MIP", [a["short_name"] for a in annual_awards(demo["records"], demo["season"], demo["cutoff"])])

    def test_generated_artifacts_are_offline_and_outside_canonical_career(self):
        for path, text in self.outputs.items():
            self.assertTrue(path.is_relative_to(self.folder), path)
            if path.suffix == ".svg":
                ElementTree.fromstring(text)
                self.assertIn("ILLUSTRATIVE TEMPLATE ONLY", text)
        html = self.outputs[self.folder / "player_cards_preview.html"]
        self.assertNotIn("__PLAYER_CARD_DATA__", html)
        self.assertNotIn('<script src="http', html)
        self.assertIn('"photo_url": null', html)
        shots = json.loads(self.outputs[self.folder / "illustrative_shots.json"])
        self.assertEqual(shots["record_type"], "illustrative_synthetic_locations")
        self.assertEqual(len(shots["shots"]), 104)


if __name__ == "__main__":
    unittest.main()
