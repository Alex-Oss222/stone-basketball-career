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


class TradedInContractTests(unittest.TestCase):
    """A contract Miami acquires by summer trade is the existing agreement, assigned: it keeps its original signing date
    and is held from the trade date (the 2005 rollover once dated Telfair's and Stevenson's contracts at the trade)."""

    def setUp(self):
        import json
        import tempfile
        from runtime.rollover import Rollover
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        def put(rel, data):
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data), encoding="utf-8")
        put("career/Dwyane_Wade/2003-04/10_Free_Agency/free_agency_2004.json", {"events": [
            {"date": "2004-07-01", "kind": "rookie_scale_signing", "bbr_id": "telfase01", "club": "Detroit Pistons"},
            {"date": "2004-09-23", "kind": "offer_sheet", "bbr_id": "stevede01", "club": "Cleveland Cavaliers"},
            {"date": "2004-09-23", "kind": "offer_sheet_matched", "bbr_id": "stevede01", "club": "Utah Jazz"}]})
        put("career/Dwyane_Wade/2004-05/League/contracts.json", {"contracts": [
            {"bbr_id": "telfase01", "route": "rookie_scale", "kind": "rookie_scale", "team_option": "2007-08",
             "schedule": {"2004-05": 939480, "2005-06": 1010040, "2006-07": 1080480}},
            {"bbr_id": "stevede01", "route": "bird", "kind": "new", "schedule": {"2004-05": 2657306, "2005-06": 2989469}},
            {"bbr_id": "nodate01", "route": "existing", "kind": "existing", "schedule": {"2004-05": 1, "2005-06": 2}}]})
        r = Rollover.__new__(Rollover)
        r.root, r.old, r.new, r.year, r.day = root, "2004-05", "2005-06", 2005, "2005-10-01"
        r.record_path = root / "career/Dwyane_Wade/2004-05/10_Free_Agency/free_agency_2005.json"
        self.r = r

    def tearDown(self):
        self.tmp.cleanup()

    def entry(self, key, date="2005-08-05"):
        event = {"date": date, "kind": "trade", "bbr_id": key, "club": "Miami Heat", "from": "Utah Jazz", "deal": "d1"}
        row = {"bbr_id": key, "route": "existing", "salary": 1}
        return self.r.traded_in(key, key, row, event, {}, {"2005-06": 1010040, "2006-07": 1080480})

    def test_rookie_scale_contract_keeps_its_signing_and_option(self):
        e = self.entry("telfase01")
        self.assertEqual((e["signed_date"], e["status"], e["team_option_season"]),
                         ("2004-07-01", "under_rookie_contract", "2007-08"))
        self.assertEqual((e["acquired_by"], e["acquired_date"], e["route"]), ("trade", "2005-08-05", "existing"))

    def test_matched_offer_sheet_dates_the_contract(self):
        self.assertEqual(self.entry("stevede01", "2005-09-02")["signed_date"], "2004-09-23")

    def test_an_unrecorded_signing_stays_unknown(self):
        e = self.entry("nodate01")
        self.assertNotIn("signed_date", e)
        self.assertIn("not recorded", e["notes"])


class ReturnedDepartureTests(unittest.TestCase):
    def test_a_player_miami_holds_again_leaves_his_other_club(self):
        import json
        import tempfile
        from runtime.rollover import close_returned_departures
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "departures.json"
            path.write_text(json.dumps({"entries": [
                {"player": "Eddie Jones", "bbr_id": "jonesed02", "club": "Utah Jazz", "from": "2005-01-24", "until": None},
                {"player": "Dorell Wright", "bbr_id": "wrighdo01", "club": "Utah Jazz", "from": "2005-08-05", "until": None}]}))
            held = [{"bbr_id": "jonesed02", "from": "2005-08-05", "until": None}]
            self.assertEqual(close_returned_departures(path, held), ["Eddie Jones"])
            entries = json.loads(path.read_text())["entries"]
            self.assertEqual([e["until"] for e in entries], ["2005-08-05", None])
            self.assertEqual(close_returned_departures(path, held), [])           # once

    def test_the_summer_market_ends_the_other_stints(self):
        import json
        import tempfile
        from runtime.rollover import close_returned_departures
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "departures.json"
            path.write_text(json.dumps({"entries": [
                {"player": "Kendall Gill", "bbr_id": "gillke01", "club": "Utah Jazz", "from": "2005-01-24", "until": None},
                {"player": "Scott Padgett", "bbr_id": "padgesc01", "club": "Toronto Raptors", "from": "2004-12-20", "until": None},
                {"player": "Mover", "bbr_id": "mover01", "club": "Utah Jazz", "from": "2005-01-24", "until": None}]}))
            record = {"clubs": {"Toronto Raptors": [{"bbr_id": "padgesc01"}], "Boston Celtics": [{"bbr_id": "mover01"}]},
                      "events": [{"date": "2005-08-10", "kind": "signing", "bbr_id": "mover01", "club": "Boston Celtics"}]}
            self.assertEqual(sorted(close_returned_departures(path, [], record, 2005)), ["Kendall Gill", "Mover"])
            ends = {e["player"]: e["until"] for e in json.loads(path.read_text())["entries"]}
            self.assertEqual(ends, {"Kendall Gill": "2005-07-01", "Scott Padgett": None, "Mover": "2005-08-10"})


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