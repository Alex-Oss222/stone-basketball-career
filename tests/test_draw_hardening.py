"""Roadmap 18b: semantic decision keys, the published journal, the seed hash and schedule-bound event ids."""
from pathlib import Path
import tempfile
import unittest

from runtime import decisions
from runtime.private_service import Store, play_decision
from scripts import audit_journal

ROOT = Path(__file__).resolve().parents[1]


def packet(event_id, question="Does X accept?", date="2004-07-02"):
    return {"event_id": event_id, "date": date, "question": question, "decider": "X", "options": {"yes": 0.5, "no": 0.5},
            "basis": "test"}


class HardeningTests(unittest.TestCase):
    def setUp(self):
        self.store = Store(Path(tempfile.mkdtemp()) / "e.sqlite3")
        self.store.initialize()

    def test_same_question_cannot_be_redrawn_under_a_new_id(self):
        play_decision(self.store, packet("a"))
        with self.assertRaises(ValueError):
            play_decision(self.store, packet("b"))
        self.assertEqual(play_decision(self.store, packet("a"))[0], "already_decided")

    def test_keys_apply_only_from_the_hardening_date(self):
        play_decision(self.store, packet("c", date="2004-04-01"))
        play_decision(self.store, packet("d", date="2004-04-01"))          # before HARDEN_FROM: not keyed
        self.assertNotEqual(decisions.semantic_key(packet("x", "Q one")), decisions.semantic_key(packet("x", "Q two")))
        self.assertEqual(decisions.semantic_key(packet("x", "Does  X accept?")), decisions.semantic_key(packet("y", "does x accept?")))

    def test_journal_and_seed_hash(self):
        play_decision(self.store, packet("e"))
        journal = {"seed_sha256": self.store.seed_sha256(), "events": self.store.journal()}
        self.assertEqual(len(journal["seed_sha256"]), 64)
        self.assertEqual([e["event_id"] for e in journal["events"]], ["e"])
        problems = audit_journal.audit(journal, ROOT)
        self.assertTrue(any("e has no committed request" in p for p in problems))

    def test_committed_records_pass(self):
        self.assertEqual(decisions.key_errors(ROOT), [])
        from runtime.game_requests import schedule_id_errors
        self.assertEqual(schedule_id_errors(ROOT), [])


if __name__ == "__main__":
    unittest.main()
