"""Standing roster and payroll rules: the cut, who may dress, and later-season payrolls."""
import json
import unittest
from unittest import mock

from runtime import camp
from runtime.season_games import depth_order, rotation_for


class FakeOffice:
    def needs(self):
        return {}

    def fit(self, position, needs):
        return 1.0


def player(name, kind="invite", status="camp_contract", pos="SG"):
    return {"player": name, "kind": kind, "status": status, "positions": [pos]}


class CutTests(unittest.TestCase):
    def setUp(self):
        self.data = {"players": [player(f"R{i}", "roster", "under_contract") for i in range(10)]
                     + [player(f"I{i}") for i in range(9)]
                     + [player("Rights", "roster", "draft_rights_unsigned", "PF")]}
        self.scores = {p["player"]: float(i) for i, p in enumerate(self.data["players"])}

    def test_unsigned_rights_do_not_count_and_are_never_released(self):
        names = camp.cut_list(self.data, self.scores, FakeOffice())
        self.assertEqual(len(names), 19 - camp.ROSTER_MAX)          # 19 signed players, not 20
        self.assertNotIn("Rights", names)

    def test_rotation_players_are_released_last(self):
        lowest = min((p for p in self.data["players"] if p["kind"] == "invite"), key=lambda p: self.scores[p["player"]])["player"]
        self.assertIn(lowest, camp.cut_list(self.data, self.scores, FakeOffice()))
        self.assertNotIn(lowest, camp.cut_list(self.data, self.scores, FakeOffice(), protected=[lowest]))

    def test_playable_statuses(self):
        for status in ("under_contract", "camp_contract", "re_signed", "team_option_exercised", "under_rookie_contract"):
            self.assertTrue(camp.playable(status), status)
        for status in (None, "released", "draft_rights_unsigned", "free_agent_rights_held", "signed_elsewhere", "traded"):
            self.assertFalse(camp.playable(status), status)


class DressingTests(unittest.TestCase):
    def test_a_released_rotation_player_is_replaced_by_the_next_playable_man(self):
        rotation = {"players": [{"player_id": n, "position": "SG", "minutes": m, "ratings": {}}
                                for n, m in (("A", 40), ("B", 40), ("C", 40), ("D", 40), ("E", 40), ("Cut", 40))]}
        roster = {"players": [{"name": n, "positions": ["SG"], "status": st} for n, st in
                              (("A", "under_contract"), ("B", "under_contract"), ("C", "under_contract"), ("D", "under_contract"),
                               ("E", "under_contract"), ("Cut", "released"), ("Rights", "draft_rights_unsigned"), ("Next", "camp_contract"))]}
        depth = {"positions": {"SG": ["A", "B", "C", "D", "E", "Cut", "Rights", "Next"]}}
        order = depth_order(depth, roster)
        self.assertNotIn("Cut", [e["name"] for e in order])
        self.assertNotIn("Rights", [e["name"] for e in order])
        players = rotation_for(rotation, {"Cut": 10 ** 6}, {}, order)
        names = [p["player_id"] for p in players]
        self.assertNotIn("Cut", names)
        self.assertIn("Next", names)
        self.assertAlmostEqual(sum(p["minutes"] for p in players), 240)


class FuturePayrollTests(unittest.TestCase):
    def office(self, committed):
        from runtime.gm import FrontOffice
        fo = FrontOffice.__new__(FrontOffice)
        fo.budget = {"payroll_ceiling": 57000000}
        fo.committed_in = lambda season: committed.get(season, 0)
        return fo

    def test_later_seasons_must_fit_under_the_ceiling(self):
        fo = self.office({"2004-05": 40000000, "2005-06": 52000000})
        self.assertEqual(fo.future_fit([5000000, 6000000, 6500000, 7000000]), 2)     # 2005-06 would reach $58.5M
        self.assertEqual(self.office({"2005-06": 50000000}).future_fit([5000000, 6000000, 6500000, 7000000]), 4)   # $56.5M fits
        self.assertEqual(self.office({}).future_fit([5000000, 6000000, 6500000]), 3)
        self.assertEqual(self.office({"2004-05": 56000000}).future_fit([5000000, 6000000]), 1)


class ValidatorTests(unittest.TestCase):
    def test_a_scheduled_request_with_a_released_player_is_an_error(self):
        import tempfile
        from pathlib import Path
        from scripts.validate_repository import miami_roster_errors
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            season = root / "career/Dwyane_Wade/2003-04"
            (season / "00_Team/Team/Roster").mkdir(parents=True)
            (season / "06_Regular_Season/10_October/Week_4").mkdir(parents=True)
            (season / "current_state.json").write_text(json.dumps({"current_date": "2003-10-28"}))
            names = [f"P{i}" for i in range(16)]
            (season / "00_Team/Team/Roster/roster.json").write_text(json.dumps({"players":
                [{"name": n, "status": "under_contract"} for n in names] + [{"name": "Gone", "status": "released"}]}))
            (season / "06_Regular_Season/10_October/Week_4/Game_1.request.json").write_text(json.dumps(
                {"home": {"team": "Miami Heat", "players": [{"player_id": "Gone"}, {"player_id": "P1"}]}, "away": {"team": "X"}}))
            errors = miami_roster_errors(root)
            self.assertTrue(any("Gone is not a signed Miami player" in e for e in errors), errors)
            self.assertTrue(any("16 signed players" in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main()
