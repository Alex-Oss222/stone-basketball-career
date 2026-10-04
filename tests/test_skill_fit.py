"""Skill fit: standardized dated skills, club needs below league average, crowding a high-usage club."""
import unittest

from runtime.gm import SKILL_FIT_FROM, FrontOffice
from runtime.market import Market
from runtime.skill_fit import FIT_LIMITS, NEEDED, SKILLS, SkillFit


class SkillFitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skills = SkillFit()

    def test_skills_are_standardized_against_the_2002_03_league(self):
        z = self.skills.z("wallabe01")                  # Ben Wallace: a 2002-03 defensive anchor
        self.assertEqual(set(z), set(SKILLS))
        self.assertGreater(z["rim_protection"], 2)
        self.assertGreater(z["defense"], 2)
        self.assertLess(z["creation"], 0)
        self.assertIsNone(self.skills.z("no_such_player"))
        self.assertEqual(self.skills.z("wadedw01")["defense"], 0.0)   # a draftee has no NBA defensive record

    def test_a_club_needs_only_what_it_lacks_and_a_scorer_crowds_a_high_usage_club(self):
        needs = {"need": {s: 0.0 for s in NEEDED}, "creation_load": 0.0}
        self.assertEqual(self.skills.fit("iversal01", needs), 1.0)         # no need, no crowding: neutral
        needs = {"need": dict(needs["need"], rim_protection=1.0), "creation_load": 1.0}
        big, scorer = self.skills.fit("wallabe01", needs), self.skills.fit("iversal01", needs)
        self.assertGreater(big, 1.0)
        self.assertLess(scorer, 1.0)
        self.assertTrue(FIT_LIMITS[0] <= scorer <= big <= FIT_LIMITS[1])
        self.assertEqual(self.skills.fit("no_such_player", needs), 1.0)

    def test_miami_reads_skill_fit_only_from_its_adoption_date(self):
        before = FrontOffice("2003-11-30", Market("2003-11-30"))
        self.assertIsNone(before.skill_needs())
        self.assertEqual(before.skill_fit("wallabe01"), 1.0)
        after = FrontOffice(SKILL_FIT_FROM, Market(SKILL_FIT_FROM))
        needs = after.skill_needs()
        self.assertEqual(set(needs["need"]), set(NEEDED))
        self.assertTrue(all(v >= 0 for v in needs["need"].values()))
        self.assertGreater(after.skill_fit("wallabe01"), after.skill_fit("iversal01"))


if __name__ == "__main__":
    unittest.main()
