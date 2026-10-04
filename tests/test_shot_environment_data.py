import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import import_shot_environment as importer


ROOT = Path(__file__).resolve().parents[1]


class ShotEnvironmentDataTests(unittest.TestCase):
    def test_prior_is_reproducible_offline_from_verified_sources(self):
        with patch.object(importer, "urlopen", side_effect=AssertionError("offline build made a network request")):
            expected = importer.rendered(ROOT)
        self.assertEqual((ROOT / importer.OUTPUT).read_text(encoding="utf-8"), expected)
        data = json.loads(expected)
        self.assertEqual(data["season"], "2002-03")
        self.assertEqual(data["published_after"], "2003-04-16")
        self.assertEqual(data["coverage"]["unique_full_season_players"], 428)
        self.assertEqual(data["coverage"]["aggregated_trade_rows_used"], 27)
        # Independently recorded season totals catch counting traded stints twice.
        self.assertEqual(data["league_totals"], {
            "fga": 192109, "fg": 84937, "x2pa": 157197, "x2p": 72737,
            "x3pa": 34912, "x3p": 12200,
        })

    def test_conditional_priors_preserve_two_and_three_point_baselines(self):
        data = importer.build_environment(ROOT)
        for value, baseline in ((2, "two_point_fg_pct"), (3, "three_point_fg_pct")):
            group = [zone for zone in data["zones"] if zone["shot_value"] == value]
            self.assertAlmostEqual(sum(zone["attempt_share_within_value"] for zone in group), 1.0)
            self.assertAlmostEqual(sum(zone["attempt_share_within_value"] * zone["fg_pct"] for zone in group),
                                   data[baseline])
            for zone in group:
                self.assertGreater(zone["estimated_attempts"], 0)
                self.assertGreaterEqual(zone["fg_pct"], 0)
                self.assertLessEqual(zone["fg_pct"], 1)
        # Rounded source shares cannot truthfully be reported as exact observed counts.
        self.assertAlmostEqual(data["coverage"]["two_point_attempt_rounding_residual"], 8.512)
        self.assertIn("estimates", data["count_kind"])
        self.assertNotIn("restricted_area", {zone["id"] for zone in data["zones"]})

    def test_snapshots_exclude_later_seasons_and_historical_wade_nba_rows(self):
        for rows in importer.read_sources(ROOT).values():
            self.assertEqual({row["season"] for row in rows}, {"2003"})
            self.assertEqual({row["lg"] for row in rows}, {"NBA"})
            self.assertNotIn("Dwyane Wade", {row["player"] for row in rows})
        source = ("season,lg,player\n2003,NBA,Prior Veteran\n"
                  "2004,NBA,Dwyane Wade\n2003,OTHER,Other League\n").encode()
        filtered = list(csv.DictReader(io.StringIO(importer.season_snapshot(source).decode())))
        self.assertEqual(filtered, [{"season": "2003", "lg": "NBA", "player": "Prior Veteran"}])

    def test_traded_player_total_replaces_stints_without_hiding_ambiguity(self):
        rows = [{"player_id": "1", "tm": "AAA"}, {"player_id": "1", "tm": "BBB"},
                {"player_id": "1", "tm": "TOT"}, {"player_id": "2", "tm": "AAA"}]
        self.assertEqual({key: row["tm"] for key, row in importer.full_season_rows(rows).items()},
                         {"1": "TOT", "2": "AAA"})
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            importer.full_season_rows(rows[:2])

    def test_source_tampering_fails_before_calibration(self):
        with tempfile.TemporaryDirectory() as folder:
            for spec in importer.SOURCES.values():
                target = Path(folder) / spec["snapshot_file"]
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((ROOT / spec["snapshot_file"]).read_bytes())
            target = Path(folder) / importer.SOURCES["shooting"]["snapshot_file"]
            target.write_bytes(target.read_bytes() + b"\n")
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                importer.build_environment(folder)


if __name__ == "__main__":
    unittest.main()
