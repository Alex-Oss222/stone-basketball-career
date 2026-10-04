"""Symmetric league phase 1: the dated cap book of every real club, read-only and switched off by default."""
import unittest

from runtime import league_book
from runtime.league_book import LeagueBook, owner_ceiling
from runtime.market import Market


class LeagueBookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.book = LeagueBook("2003-12-01", Market("2003-12-01"))
        cls.clubs = cls.book.all()

    def test_every_real_club_has_a_book_and_miami_keeps_its_own_ledger(self):
        self.assertEqual(len(self.clubs), 28)
        self.assertNotIn("Miami Heat", self.clubs)
        with self.assertRaises(ValueError):
            self.book.club("Miami Heat")
        for row in self.clubs.values():
            self.assertEqual(row["cap_room"], max(0, self.book.cap - row["payroll"]))
            self.assertGreaterEqual(row["owner_ceiling"], self.book.tax_line)
            self.assertFalse(row["mid_level_open"] and row["cap_room"] > 0)    # the MLE is for clubs over the cap

    def test_owner_ceiling_and_the_switch(self):
        self.assertEqual(owner_ceiling(40000000, 57000000), 57000000)
        self.assertEqual(owner_ceiling(80000000, 57000000), 81600000)
        self.assertEqual(league_book.SYMMETRIC_FROM, "2003-12-03")             # the user's activation date
        self.assertFalse(league_book.active("2003-12-02"))                      # option D before it
        self.assertTrue(league_book.active("2003-12-03"))


if __name__ == "__main__":
    unittest.main()
