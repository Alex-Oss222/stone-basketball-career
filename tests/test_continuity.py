"""Cross-season continuity: a carried contract keeps its schedule, players their identity, numbers are unique."""
import json
from pathlib import Path
import tempfile
import unittest

from runtime import continuity


def write(root, rel, data):
    path = Path(root) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = self.tmp.name
        team = "career/Dwyane_Wade/{}/00_Team"
        for season in ("2004-05", "2005-06"):
            write(self.root, f"{team.format(season)}/Team/Roster/roster.json",
                  {"players": [{"name": "A", "bbr_id": "a01", "date_of_birth": "1975-01-01", "status": "under_contract"}]})
        write(self.root, f"{team.format('2004-05')}/Finances/contract_schedules.json",
              {"players": [{"player": "A", "status": "under_contract", "schedule": {"2004-05": 10, "2005-06": 11, "2006-07": 12}}]})
        self.new = f"{team.format('2005-06')}/Finances/contract_schedules.json"

    def errors(self, entry):
        write(self.root, self.new, {"players": [entry]})
        return continuity.contract_errors(self.root, "2004-05", "2005-06")

    def test_a_carried_contract_keeps_every_remaining_season(self):
        self.assertEqual(self.errors({"player": "A", "bbr_id": "a01", "route": "existing", "status": "under_contract",
                                      "schedule": {"2005-06": 11, "2006-07": 12}}), [])
        problems = self.errors({"player": "A", "bbr_id": "a01", "route": "existing", "status": "under_contract", "schedule": {"2005-06": 11}})
        self.assertTrue(any("lost or changed" in p for p in problems))

    def test_a_carried_contract_is_never_dated_inside_the_new_league_year(self):
        problems = self.errors({"player": "A", "bbr_id": "a01", "route": "existing", "signed_date": "2005-10-01",
                                "status": "under_contract", "schedule": {"2005-06": 11, "2006-07": 12}})
        self.assertTrue(any("dated as signed" in p for p in problems))

    def test_a_new_contract_in_the_new_league_year_may_replace_it(self):
        self.assertEqual(self.errors({"player": "A", "bbr_id": "a01", "route": "bird", "signed_date": "2005-07-20",
                                      "status": "under_contract", "schedule": {"2005-06": 15}}), [])

    def test_a_player_under_contract_cannot_vanish(self):
        write(self.root, self.new, {"players": []})
        self.assertTrue(any("on no record" in p for p in continuity.contract_errors(self.root, "2004-05", "2005-06")))

    def test_identity_is_kept(self):
        write(self.root, "career/Dwyane_Wade/2005-06/00_Team/Team/Roster/roster.json",
              {"players": [{"name": "A", "bbr_id": "a02", "date_of_birth": "1975-01-01"}]})
        self.assertTrue(continuity.player_errors(self.root, "2004-05", "2005-06"))


class LiveTests(unittest.TestCase):
    def test_the_live_records_carry_over_intact(self):
        from tests import live_season
        with live_season():
            self.assertEqual(continuity.errors(clubs=False), [])


if __name__ == "__main__":
    unittest.main()
