"""Roadmap 17: Miami's 2004 draft on draft-night evidence; other clubs follow history; the conflict rule."""
from pathlib import Path
import unittest

from runtime import draft as D

ROOT = Path(__file__).resolve().parents[1]


class DraftTests(unittest.TestCase):
    def test_miami_slots_include_only_picks_it_owned(self):
        self.assertEqual(D.miami_slots(ROOT), [19, 47, 53])           # own 1st and 2nd; Dallas's 2nd from 2001

    def test_real_miami_draft_night_trade_is_skipped(self):
        names = D.club_names(ROOT)
        p39 = next(p for p in D.picks(ROOT) if p["overall"] == 39)
        self.assertEqual(D.real_holder(p39, names), "Toronto Raptors")  # Miralles stays with Toronto

    def test_choices_are_available_and_distinct(self):
        choices, displaced = D.decide(ROOT)
        real = {p["bbr_id"]: p["overall"] for p in D.picks(ROOT)}
        slots = D.miami_slots(ROOT)
        ids = [c["bbr_id"] for c in choices]
        self.assertEqual(len(ids), len(set(ids)))
        for c in choices:
            k = real.get(c["bbr_id"])
            self.assertTrue(k is None or k >= c["slot"] or k in slots, c)   # never a player taken before Miami's slot
        for bbr, club in displaced.items():
            self.assertNotIn(bbr, ids)                                     # a displaced player is not also Miami's
            self.assertNotEqual(club, D.MIAMI)

    def test_evidence_is_dated_before_the_draft(self):
        import json
        data = json.loads((ROOT / D.EVIDENCE).read_text(encoding="utf-8"))
        for source in data["ranking_sources"]:
            if source.get("published"):
                self.assertLessEqual(source["published"], D.DRAFT_DATE)


if __name__ == "__main__":
    unittest.main()
