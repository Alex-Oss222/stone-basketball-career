"""The season rollover's building blocks: the season's structure, its not-started pages, Miami's summer report."""
from pathlib import Path
import re
import unittest

from runtime import seasons
from runtime.rollover import miami_summer
from runtime.season_pages import Builder, Calendar

ROOT = Path(__file__).resolve().parents[1]


class StructureTests(unittest.TestCase):
    def test_the_first_season_keeps_its_folders(self):
        cfg = seasons.structure("2003-04", ROOT)
        self.assertEqual(cfg["regular_season"]["October"]["weeks"], [3, 4])
        self.assertEqual(cfg["regular_season"]["April"]["weeks"], [1, 2])

    def test_a_later_season_follows_its_own_calendar(self):
        cfg = seasons.structure("2004-05", ROOT)["regular_season"]
        self.assertNotIn("October", cfg)                    # opening night is November 2, 2004
        self.assertEqual(cfg["April"]["weeks"], [1, 2, 3])   # the season ends April 20, 2005
        self.assertEqual([spec["folder"] for spec in cfg.values()],
                         ["11_November", "12_December", "01_January", "02_February", "03_March", "04_April"])


class PageTests(unittest.TestCase):
    def setUp(self):
        self.builder = Builder("2004-05", ROOT)

    def test_week_dates_and_neighbours(self):
        cal = Calendar("2004-05", ROOT)
        nov = cal.months[0]
        self.assertEqual(cal.week_dates(nov, 4), "November 22-30, 2004")
        text = self.builder.league("week", month=nov, week=4)
        self.assertIn("[Next week](../../12_December/Week_1/League_Stats.md)", text)
        self.assertIn("0 closed games in this record · Not started.", text)

    def test_season_page_lists_the_season_months_only(self):
        text = self.builder.team("season")
        periods = re.findall(r"^\| \[(\w+ \d{4})\]\((\d\d_\w+)/Team_Stats\.md\)", text, re.M)
        self.assertEqual([p[1] for p in periods][0], "11_November")
        self.assertEqual(len(periods), 6)
        self.assertNotIn("2003-04/", text)

    def test_award_pages_hold_empty_shortlists(self):
        nov = self.builder.cal.months[0]
        text = self.builder.awards("week", month=nov, week=1, clock="2004-10-01")
        self.assertIn("| Conference | Rank slot | Player | Team | Evidence | Result |", text)
        self.assertIn("\n[Awards procedure and research]", text)


class SummerReportTests(unittest.TestCase):
    def test_departures_are_players_miami_held(self):
        record = {"events": [{"kind": "re_sign", "club": "Miami Heat", "player": "A", "bbr_id": "a", "date": "2004-07-14"}],
                  "clubs": {"Miami Heat": [{"bbr_id": "a"}], "Boston Celtics": [{"bbr_id": "b", "salary": 1}]}}
        register = {"players": [{"name": "A", "bbr_id": "a", "status": "camp_contract"},
                                {"name": "B", "bbr_id": "b", "status": "under_contract"},
                                {"name": "C", "bbr_id": "c", "status": "voided"}]}
        s = miami_summer(record, register)
        self.assertEqual([e["player"] for e in s["re_signed"]], ["A"])
        self.assertEqual([(e["player"], e["to"]) for e in s["left"]], [("B", "Boston Celtics")])


if __name__ == "__main__":
    unittest.main()


class CampPriorTests(unittest.TestCase):
    def test_wade_is_valued_on_his_own_record_not_a_rookie_prior(self):
        from runtime import camp

        class V:
            def value(self, key):
                return 21.4 if key == "wadedw01" else None
        values = camp.prior_values({"players": [{"player": "Dwyane Wade", "bbr_id": None, "status": "under_contract"}]}, V())
        self.assertEqual(values["Dwyane Wade"], 21.4)
