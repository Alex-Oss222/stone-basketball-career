"""Generated player reports do not depend on how they are run (the user's choice A, October 2026).

The suite pins the active season (`tests/__init__.py`) and checks report freshness (`report_errors`) under that pin;
the checkpoint and validation build the same reports without it. A report builder that reads "the active season"
instead of the season it is given renders differently in the two contexts, and the committed page then looks stale to
the one that did not build it (the 2004-11-02 milestone calendar). Every player report must be byte-identical with and
without the pin. League cards and league statistics pages are built for the active season on purpose and are checked
for freshness only without the pin, so they are outside this guard."""
import unittest
from pathlib import Path

from tests import live_season
from runtime.player_reports import build_reports

ROOT = Path(__file__).resolve().parents[1]
PLAYER = ROOT / "career/Dwyane_Wade"


class IndependenceTests(unittest.TestCase):
    def test_player_reports_are_the_same_with_and_without_the_season_pin(self):
        pinned = build_reports(ROOT, PLAYER)
        with live_season():
            live = build_reports(ROOT, PLAYER)
        self.assertEqual(sorted(map(str, pinned)), sorted(map(str, live)), "the two contexts build different report sets")
        differing = sorted(str(Path(p).relative_to(ROOT)) for p in pinned if pinned[p] != live[p])
        self.assertEqual(differing, [], "these reports render differently under the test season pin; pass the season explicitly")


if __name__ == "__main__":
    unittest.main()
