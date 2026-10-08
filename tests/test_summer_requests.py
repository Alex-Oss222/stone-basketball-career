"""Wade's free-agent requests with a contract-length preference, and multi-season minimum schedules."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from runtime import free_agency_2004 as fa
from runtime.cba import minimum_salary
from runtime.league_contracts import minimum_steps, schedule_for

ROOT = Path(__file__).resolve().parents[1]


class MinimumScheduleTests(unittest.TestCase):
    def test_two_season_minimum_steps_with_service(self):
        # two years of service in 2005-06, three in 2006-07 (cbafaq05 Q11)
        self.assertEqual(schedule_for(minimum_salary(2, "2005-06", ROOT), 2, "2005-06", "minimum"),
                         {"2005-06": 719373, "2006-07": 771331})

    def test_ten_year_veteran_stays_on_the_top_row(self):
        self.assertEqual(minimum_steps(1138500, 2, "2005-06"), {"2005-06": 1138500, "2006-07": 1178348})

    def test_crossing_agreements(self):
        # a 2004-05 two-year minimum: the 1999 scale, then the 2005 scale's next row
        first = minimum_salary(1, "2004-05", ROOT)
        self.assertEqual(schedule_for(first, 2, "2004-05", "minimum"),
                         {"2004-05": first, "2005-06": minimum_salary(2, "2005-06", ROOT)})

    def test_non_scale_amount_and_one_season_unchanged(self):
        self.assertEqual(schedule_for(700000, 2, "2005-06", "minimum"), {"2005-06": 700000, "2006-07": 700000})
        self.assertEqual(schedule_for(719373, 1, "2005-06", "minimum"), {"2005-06": 719373})
        self.assertEqual(schedule_for(1000000, 2, "2005-06", "mid_level"), {"2005-06": 1000000, "2006-07": 1080000})


class RequestedTermsTests(unittest.TestCase):
    def test_term_preference_read_by_date(self):
        with tempfile.TemporaryDirectory() as tmp, fa.year_context(2005, ROOT):
            path = Path(tmp) / fa.REQUESTS
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({"requests": [
                {"date": "2005-06-16", "subject": "free_agent_target", "bbr_id": "hasleud01", "requested": "pursue",
                 "term": "multi_year"},
                {"date": "2005-07-20", "subject": "free_agent_target", "bbr_id": "later01", "requested": "pursue",
                 "term": "multi_year"},
                {"date": "2005-06-16", "subject": "free_agent_target", "bbr_id": "plain01", "requested": "pursue"}]}))
            market = SimpleNamespace(root=Path(tmp))
            self.assertEqual(fa.Market.requested_terms(market, "2005-07-01"), {"hasleud01": "multi_year"})

    def test_live_request_is_recorded(self):
        with fa.year_context(2005, ROOT):
            requests = json.loads((ROOT / fa.REQUESTS).read_text())["requests"]
        haslem = next(r for r in requests if r["bbr_id"] == "hasleud01")
        self.assertEqual((haslem["date"], haslem["requested"], haslem["term"]), ("2005-06-16", "pursue", "multi_year"))
        self.assertEqual(fa.MINIMUM_EXCEPTION_YEARS, 2)


if __name__ == "__main__":
    unittest.main()
