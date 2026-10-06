"""Career statistical milestones: the game that crosses a total, and his age that day."""
import unittest

from runtime.stat_milestones import age_on, age_text, career_milestones


def game(day, pts, reb=0, ast=0, competition="regular", appeared=True):
    return {"date": day, "competition": competition, "status": "played", "season": "2003-04", "opponent": "X", "note": None,
            "line": {"pts": pts, "reb": reb, "ast": ast, "stl": 0, "blk": 0, "tpm": 0, "ftm": 0, "appeared": appeared}}


class AgeTests(unittest.TestCase):
    def test_years_and_days(self):
        self.assertEqual(age_on("1984-01-17", "2004-03-06"), (20, 49))
        self.assertEqual(age_text("1984-01-17", "2004-01-18"), "20 years, 1 day")
        self.assertEqual(age_text(None, "2004-01-18"), "Not recorded")


class CrossingTests(unittest.TestCase):
    def test_the_game_that_crosses_the_total_reaches_it(self):
        games = [game(f"2004-01-{d:02d}", 400) for d in range(1, 4)]
        data = career_milestones(games, "1984-01-17")
        reached = {r["milestone"]: r["date"] for r in data["regular"]}
        self.assertEqual(reached["1,000 career points"], "2004-01-03")
        self.assertEqual(data["regular_next"][0], {"milestone": "2,000 career points", "current": 1200, "needed": 800})

    def test_preseason_playoffs_and_did_not_play_stay_out(self):
        games = [game("2004-01-01", 900), game("2004-01-02", 200, competition="preseason"),
                 game("2004-01-03", 200, appeared=False), game("2004-04-20", 200, competition="playoff")]
        data = career_milestones(games, "1984-01-17")
        self.assertEqual(data["regular"], [])
        self.assertEqual([r["milestone"] for r in data["playoff"]], ["100 career playoff points"])

    def test_firsts_are_dated_in_order(self):
        data = career_milestones([game("2004-01-01", 12), game("2004-01-02", 31, reb=10)], "1984-01-17")
        firsts = {r["milestone"]: r["date"] for r in data["firsts"]}
        self.assertEqual(firsts["NBA regular-season debut"], "2004-01-01")
        self.assertEqual(firsts["First 30-point game"], "2004-01-02")
        self.assertEqual(firsts["First double-double"], "2004-01-02")


if __name__ == "__main__":
    unittest.main()
