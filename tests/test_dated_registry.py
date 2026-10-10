"""The summer market and the valuations read the league player registry as it stood on their own date: a row added
later (`added_on`, a debut written by a later game) was unknown then, so replaying a closed summer reads what the summer
read (runtime/free_agency_2004.identity, runtime/valuation.Valuation.registry)."""
import unittest
from pathlib import Path
from unittest import mock

from runtime import free_agency_2004 as fa
from runtime import valuation as V

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = {"players": [
    {"name": "Known Player", "bbr_id": "known01", "birth_date": "1980-01-01", "position": "SF"},
    {"name": "Debut Player", "bbr_id": "debut01", "birth_date": "1986-10-26", "position": "PF", "added_on": "2005-11-02"},
]}


class DatedRegistryTests(unittest.TestCase):
    def test_valuation_reads_the_registry_as_of_its_date(self):
        v = V.Valuation.__new__(V.Valuation)
        v.root = ROOT
        with mock.patch.object(V, "read", return_value=REGISTRY):
            v.on = "2005-09-30"
            self.assertEqual([p["bbr_id"] for p in v.registry()], ["known01"])
            v.on = "2005-11-02"
            self.assertEqual([p["bbr_id"] for p in v.registry()], ["known01", "debut01"])

    def test_market_identity_reads_the_registry_as_of_its_day(self):
        real = fa._read

        def read(path, *args, **kwargs):
            return REGISTRY if "player_registry" in str(path) else real(path, *args, **kwargs)

        with mock.patch.object(fa, "_read", read), mock.patch("runtime.rotations.load_rosters", return_value={}):
            summer = fa.identity(ROOT, year=2005, on="2005-09-30")
            later = fa.identity(ROOT, year=2005, on="2005-11-02")
            undated = fa.identity(ROOT, year=2005)
        self.assertIn("known01", summer)
        self.assertNotIn("debut01", summer)
        self.assertIn("debut01", later)
        self.assertIn("debut01", undated)                  # no date: every row on file, as before



class DatedPositionTests(unittest.TestCase):
    """A corrected registry position reads as it stood before its correction date (runtime/write_back.position_on), so a
    closed summer or a recorded trade replays with the position it read."""

    def test_position_reads_by_date(self):
        from runtime.write_back import position_on
        row = {"position": "SG", "position_before": "SF", "position_corrected_on": "2005-12-31"}
        self.assertEqual(position_on(row, "2005-07-01"), "SF")
        self.assertEqual(position_on(row, "2005-12-31"), "SG")
        self.assertEqual(position_on(row), "SG")
        self.assertEqual(position_on({"position": "PF"}, "2004-01-01"), "PF")

    def test_live_registry_corrections_are_dated(self):
        import json
        rows = json.loads((ROOT / "career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json").read_text())["players"]
        corrected = [r for r in rows if r.get("position_corrected_on")]
        self.assertTrue(corrected)
        for r in corrected:
            self.assertIn("position_before", r)
            self.assertLessEqual(r["position_corrected_on"], json.loads((ROOT / "career/Dwyane_Wade/2005-06/current_state.json").read_text())["current_date"])


if __name__ == "__main__":
    unittest.main()
