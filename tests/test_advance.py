"""scripts/advance.py: the day loop stops whenever Wade has a decision to make."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import scripts.advance as A


class AdvanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = Path(self.tmp.name) / "current_state.json"
        self.addCleanup(self.tmp.cleanup)

    def test_a_pending_decision_or_consultation_stops_the_clock(self):
        self.state.write_text(json.dumps({"current_date": "2004-01-22", "pending_player_decisions": ["consultation:x"]}))
        with mock.patch.object(A, "state_file", lambda: self.state), self.assertRaises(A.Stop) as stop:
            A.wade_waits()
        self.assertIn("consultation:x", str(stop.exception))
        self.state.write_text(json.dumps({"current_date": "2004-01-22", "pending_player_decisions": []}))
        with mock.patch.object(A, "state_file", lambda: self.state):
            A.wade_waits()                                       # nothing pending: the day goes on

    def test_the_driver_never_passes_a_seed_or_chooses_an_outcome(self):
        text = Path(A.__file__).read_text()
        for word in ("seed", "random", "outcome ="):
            self.assertNotIn(word, text.split('"""', 2)[2])
        self.assertIn("pending_player_decisions", text)


if __name__ == "__main__":
    unittest.main()
