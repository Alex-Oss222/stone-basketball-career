import json
import unittest
from pathlib import Path

from runtime.season_rules import month_week, next_series_game_number, series_over

ROOT=Path(__file__).resolve().parents[1]
PLAYER=ROOT/"career/Dwyane_Wade"
SEASON=PLAYER/"2003-04"
TEAM=SEASON/"00_Team"


class CalendarWeekTests(unittest.TestCase):
    def test_week_boundaries(self):
        expected={1:1,7:1,8:2,14:2,15:3,21:3,22:4,28:4,29:4,30:4,31:4}
        for day,week in expected.items():
            with self.subTest(day=day):
                self.assertEqual(month_week(day),week)


class BestOfSevenTests(unittest.TestCase):
    def test_series_rules(self):
        self.assertTrue(series_over(4,0))
        self.assertFalse(series_over(3,3))
        self.assertEqual(next_series_game_number(2,2),5)
        self.assertEqual(next_series_game_number(3,2),6)
        self.assertEqual(next_series_game_number(3,3),7)
        self.assertIsNone(next_series_game_number(4,2))


class InitializedCareerTests(unittest.TestCase):
    def test_player_and_team(self):
        self.assertTrue((PLAYER/"Dwyane Wade: Player Profile.md").is_file())
        state=json.loads((SEASON/"current_state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["team"],"Miami Heat")
        self.assertEqual(state["draft"]["overall"],5)

    def test_organization_files(self):
        for name in ("Micky_Arison","Pat_Riley","Randy_Pfund","Andy_Elisburg","Chet_Kammerer"):
            self.assertTrue((TEAM/"Organization"/f"{name}.md").is_file())

    def test_every_roster_player_has_card(self):
        roster=json.loads((TEAM/"Team/Roster/roster.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(roster["players"]),17)
        for player in roster["players"]:
            self.assertTrue((TEAM/"Team/Player_Cards"/f"{player['id']}.md").is_file())

    def test_depth_chart_is_holding_chart(self):
        depth=json.loads((TEAM/"Team/Depth_Chart/depth_chart.json").read_text(encoding="utf-8"))
        self.assertFalse(depth["game_ready"])
        names={p["name"] for p in depth["unassigned_draft_rights"]}
        self.assertEqual(names,{"Dwyane Wade","Jerome Beasley"})

    def test_cap_room_stays_unresolved_on_draft_day(self):
        finance=json.loads((TEAM/"Finances/finance.json").read_text(encoding="utf-8"))
        self.assertIsNone(finance["cap_room"])
        carter=next(x for x in finance["pending_control_items"] if x["player"]=="Anthony Carter")
        self.assertEqual(carter["status"],"pending")
        self.assertEqual(carter["deadline"],"2003-06-30")

    def test_no_empty_postseason_placeholders(self):
        self.assertFalse(any((SEASON/"07_Play_In_Tournament").glob("Game_*.md")))
        for folder in ("First_Round","Conference_Semifinals","Conference_Finals","Finals"):
            self.assertFalse(any((SEASON/"08_Playoffs"/folder).glob("Game_*.md")))


if __name__=="__main__":
    unittest.main()
