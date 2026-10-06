"""The season-change audit (December 2004 on the career clock): every rule that changes between seasons reads the
season it applies to, and the 2003-04 and 2004-05 values replay unchanged."""
from pathlib import Path
import unittest

from runtime import agreement, seasons
from runtime.cba import minimum_cap_amount, minimum_salary
from runtime.era import rules_for

ROOT = Path(__file__).resolve().parents[1]


class AgreementTests(unittest.TestCase):
    def test_1999_terms_through_2004_05(self):
        t = agreement.terms("2004-05", ROOT)
        self.assertEqual((t["raise_bird"], t["raise_other"], t["max_years_bird"], t["trade_match"]), (0.125, 0.10, 7, 1.15))
        self.assertEqual(agreement.raise_share("bird", "2004-05", ROOT), 0.125)

    def test_2005_terms_from_2005_06(self):
        t = agreement.terms("2005-06", ROOT)
        self.assertEqual((t["raise_bird"], t["raise_other"]), (0.105, 0.08))
        self.assertEqual((t["max_years_bird"], t["max_years_other"]), (6, 5))
        self.assertEqual(t["rookie_option_years"], (3, 4))
        self.assertEqual(t["trade_match"], 1.25)
        self.assertEqual(agreement.max_years("other", "2005-06", ROOT), 5)

    def test_rookie_contract_shape(self):
        from runtime.league_contracts import rookie_options
        self.assertEqual(rookie_options("2005-06"), {"2007-08": "team_option", "2008-09": "team_option"})

    def test_trade_desk_matching_follows_league_year(self):
        from runtime.trades import TradeDesk
        rules = {"matching_over_cap": {"incoming_max_percent_of_outgoing": 115, "plus_dollars": 100_000}}
        desk = TradeDesk.__new__(TradeDesk)
        desk.root = ROOT
        desk.on = "2005-02-01"
        self.assertEqual(desk._matching(rules), (1.15, 100_000))
        self.assertEqual(desk._bird_raise(), 0.125)
        desk.on = "2005-08-10"
        self.assertEqual(desk._matching(rules), (1.25, 100_000))
        self.assertEqual(desk._bird_raise(), 0.105)

    def test_minimum_cap_treatment_2005(self):
        """2005 FAQ Q11: a 3+ year veteran's one-year minimum counts the 2-year minimum; 1999: 5+ years."""
        two = minimum_salary(2, "2005-06", ROOT)
        self.assertEqual(minimum_cap_amount(10, minimum_salary(10, "2005-06", ROOT), 1, "2005-06", ROOT), two)
        self.assertEqual(minimum_cap_amount(3, minimum_salary(3, "2005-06", ROOT), 1, "2005-06", ROOT), two)
        self.assertEqual(minimum_cap_amount(10, minimum_salary(10, "2005-06", ROOT), 2, "2005-06", ROOT),
                         minimum_salary(10, "2005-06", ROOT))


class CalendarTests(unittest.TestCase):
    def test_club_renames(self):
        self.assertEqual(seasons.club_name("New Orleans Hornets", "2004-05"), "New Orleans Hornets")
        self.assertEqual(seasons.club_name("New Orleans Hornets", "2005-06"), "New Orleans/Oklahoma City Hornets")
        self.assertEqual(seasons.club_name("Seattle SuperSonics", "2008-09"), "Oklahoma City Thunder")
        self.assertEqual(seasons.club_aliases("2005-06")["New Orleans Hornets"], "New Orleans/Oklahoma City Hornets")

    def test_summer_belongs_to_the_closed_season(self):
        """Until the next season's current state exists, a July date's records are the closed season's."""
        self.assertEqual(seasons.live_season_on("2004-07-15", ROOT), "2004-05")      # its rollover has run
        if not (ROOT / "career/Dwyane_Wade/2005-06/current_state.json").is_file():
            self.assertEqual(seasons.live_season_on("2005-07-15", ROOT), "2004-05")

    def test_era_rules_2005(self):
        r = rules_for("2005-06")
        self.assertEqual((r["roster_minimum"], r["roster_maximum"], r["reserve_list_minimum_games"]), (13, 15, 0))
        from runtime.league_market import _rules
        self.assertEqual(_rules(ROOT, "2004-05")["min"], 12)

    def test_injured_list_minimum_games(self):
        from runtime.roster_moves import min_games
        self.assertEqual(min_games("2005-02-01"), 5)
        self.assertEqual(min_games("2005-11-10"), 0)

    def test_market_signing_week(self):
        from runtime import free_agency_2004 as F
        self.assertEqual(F.signing_week(), 2)                       # 2004 replays: decay after July 15
        with F.year_context(2005, ROOT):
            self.assertEqual(F.rounds()[F.signing_week()], "2005-08-05")


class AllStarTests(unittest.TestCase):
    def test_riley_rule_bars_the_careers_own_coaches(self):
        from runtime.all_star import ctx, previous_coaches
        record = ROOT / "career/Dwyane_Wade/Stats_and_Awards/League/2003-04/all_star.json"
        if not record.is_file():
            self.skipTest("no 2004 All-Star record")
        import json
        step = next(s for s in json.loads(record.read_text(encoding="utf-8"))["steps"] if s["step"] == "coaches")
        self.assertEqual(previous_coaches(ctx(ROOT, "2004-05"), ROOT), {r["coach"] for r in step["conferences"].values()})


if __name__ == "__main__":
    unittest.main()
