"""scripts/reconcile.py: derived records are rebuilt from sources, and a clean repository is unchanged."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import reconcile  # noqa: E402
from runtime.seasons import active  # noqa: E402

SHEET = "career/Dwyane_Wade/{season}/00_Team/Finances/contract_schedules.json"


class ScheduleTotalsTests(unittest.TestCase):
    def copy(self, tmp):
        season = active(ROOT)
        for rel in (SHEET.format(season=season), f"career/Dwyane_Wade/{season}/current_state.json", "foundation/seasons.json"):
            src = ROOT / rel
            if src.is_file():
                (tmp / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(src, tmp / rel)
        return tmp / SHEET.format(season=season)

    def test_committed_totals_are_current(self):
        self.assertEqual(reconcile.schedule_totals(ROOT, False), [])

    def test_stale_totals_are_rebuilt_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            try:
                path = self.copy(tmp)
                active(tmp)
            except Exception as exc:                      # the season registry needs more of the tree
                self.skipTest(f"partial copy: {exc}")
            sheet = json.loads(path.read_text())
            good = dict(sheet["known_baseline"])
            season = sorted(good)[1]
            sheet["known_baseline"][season] += 1          # a writer that forgot the downstream total
            path.write_text(json.dumps(sheet))
            self.assertEqual(reconcile.schedule_totals(tmp, True), [path])
            self.assertEqual(json.loads(path.read_text())["known_baseline"], good)
            self.assertEqual(reconcile.schedule_totals(tmp, True), [])


if __name__ == "__main__":
    unittest.main()
