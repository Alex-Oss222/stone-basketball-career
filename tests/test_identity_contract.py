"""Wade's identity contract line per season (runtime/identity_contract.py, the user's report of April 2006).

Every 2005-06 stat page named his 2004-05 salary: the 2004-10-01 snapshot wrote the season's salary into its contract
text and the 2005-10-26 camp snapshot copied it. These scenarios hold the fix: a page of 2005-06 names that season's
salary from Miami's cap sheet and the 2006-07 team option's status on its own cutoff (open until the option record
applied the exercise on 2005-10-31), a career page reads the season the rollover had opened, and every page of an earlier
season reads the line its snapshot recorded without another season's salary (the 2003-04 season pages, dated on the
2004-05 rollover day, drop its 2004-05 note). An extension's option reaches the line only from its signing date. The live
repository is read, never written.
"""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from runtime import identity_contract as ic
from runtime.career_stats import identity_at
from runtime.extensions import _extend
from runtime.player_reports import identity_block

ROOT = Path(__file__).resolve().parents[1]
PLAYER = ROOT / "career/Dwyane_Wade"
RAW = json.loads((PLAYER / "professional_identity.json").read_text(encoding="utf-8"))
AGREEMENT = "Rookie scale signed 2003-07-21: three seasons plus a 2006-07 team option"
OPEN = f"{AGREEMENT} (2005-06: $2,526,600; 2006-07 team option at $3,201,202, to be decided by 2005-10-31)"
EXERCISED = f"{AGREEMENT} (2005-06: $2,526,600; 2006-07 team option exercised 2005-10-31 at $3,201,202)"
LINE_0405 = f"{AGREEMENT} (2004-05: $2,361,800)"


def put(root, rel, data):
    path = Path(root) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")


def page_line(rel):
    return next(line for line in (PLAYER / rel).read_text(encoding="utf-8").splitlines() if line.startswith("| Contract |"))


class LiveSeasonLine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.identity = ic.attach(RAW, ROOT, PLAYER)

    def test_terms_come_from_the_season_sheet_and_option_record(self):
        sheet = json.loads((PLAYER / "2005-06/00_Team/Finances/contract_schedules.json").read_text(encoding="utf-8"))
        row = next(p for p in sheet["players"] if p["player"] == "Dwyane Wade")
        option = next(d for d in json.loads((PLAYER / "2005-06/League/option_decisions.json").read_text(encoding="utf-8"))
                      ["decisions"] if d["player"] == "Dwyane Wade")
        terms = self.identity["contract_terms"]["2005-06"]
        self.assertEqual(terms["salary"], row["schedule"]["2005-06"])
        self.assertEqual(terms["options"]["2006-07"], {"kind": "team_option", "salary": option["salary"],
                                                       "due": "2005-10-31", "outcome": "exercise", "on": option["applied"],
                                                       "signed": row["signed_date"]})
        self.assertNotIn("2004-05", self.identity["contract_terms"])          # earlier seasons keep their snapshots

    def test_a_season_page_names_its_salary_and_the_option_status_on_its_cutoff(self):
        self.assertEqual(identity_at(self.identity, "2005-10-10", "2005-06")["contract"], OPEN)
        self.assertEqual(identity_at(self.identity, "2005-10-30", "2005-06")["contract"], OPEN)
        self.assertEqual(identity_at(self.identity, "2005-10-31", "2005-06")["contract"], EXERCISED)
        self.assertEqual(identity_at(self.identity, "2006-04-19", "2005-06")["contract"], EXERCISED)
        # a career page reads the season the rollover had opened by its cutoff
        self.assertEqual(identity_at(self.identity, "2006-04-19")["contract"], EXERCISED)
        self.assertEqual(identity_at(self.identity, "2005-10-01")["contract"], OPEN)
        self.assertEqual(identity_at(self.identity, "2005-08-15")["contract"], LINE_0405)

    def test_earlier_seasons_read_the_line_their_snapshots_recorded(self):
        cutoffs = [(s["as_of"], season) for s in RAW["snapshots"] if s["as_of"] < "2005-10-01"
                   for season in ("2003-04", "2004-05", None)]
        cutoffs += [("2004-10-01", "2003-04"), ("2005-10-01", "2004-05"), ("2005-09-30", None)]
        for day, season in cutoffs:
            with self.subTest(day=day, season=season):
                stored = identity_at(RAW, day, season)["contract"]
                if season == "2003-04" and stored and "(2004-05:" in stored:
                    stored = AGREEMENT                       # a 2003-04 page never names the 2004-05 salary
                self.assertEqual(identity_at(self.identity, day, season)["contract"], stored)
        # the 2003-04 season pages are dated on the 2004-05 rollover day and read the agreement, as its game notes do
        self.assertEqual(identity_at(self.identity, "2004-10-01", "2003-04")["contract"], AGREEMENT)
        self.assertEqual(identity_at(self.identity, "2004-10-01")["contract"], LINE_0405)    # a career page: 2004-05
        # the 2004-05 season pages are dated on the 2005-06 rollover day and keep the 2004-05 salary
        page = PLAYER / "Stats_and_Awards/2004-05/README.md"
        self.assertEqual(identity_block(self.identity, "2005-10-01", full=True, page=page),
                         identity_block(RAW, "2005-10-01", full=True, page=page))
        self.assertEqual(identity_at(self.identity, "2005-10-01", "2004-05")["contract"], LINE_0405)

    def test_rebuilt_pages(self):
        self.assertEqual(page_line("Stats_and_Awards/2005-06/README.md"), f"| Contract | {EXERCISED} |")
        self.assertEqual(page_line("Stats_and_Awards/README.md"), f"| Contract | {EXERCISED} |")
        self.assertEqual(page_line("2005-06/05_Preseason/Game_1.md"), f"| Contract | {OPEN} |")
        self.assertEqual(page_line("Stats_and_Awards/2004-05/README.md"), f"| Contract | {LINE_0405} |")
        self.assertEqual(page_line("Stats_and_Awards/2003-04/README.md"), f"| Contract | {AGREEMENT} |")
        self.assertEqual(page_line("2003-04/08_Playoffs/README.md"), f"| Contract | {AGREEMENT} |")
        self.assertEqual(page_line("2003-04/06_Regular_Season/11_November/Week_1/Game_1.md"), f"| Contract | {AGREEMENT} |")

    def test_the_live_identity_carries_the_agreement_only(self):
        self.assertEqual(ic.errors(ROOT), [])


class ScratchCareer(unittest.TestCase):
    """A declined option and the validation guard, on a scratch career."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.player = self.root / "career/Dwyane_Wade"
        put(self.root, "career/Dwyane_Wade/2005-06/current_state.json", {"current_date": "2006-01-10", "rolled_over_on": "2005-10-01"})
        put(self.root, "career/Dwyane_Wade/2005-06/00_Team/Finances/contract_schedules.json", {"players": [
            {"player": "Dwyane Wade", "status": "under_contract", "route": "rookie_scale",
             "schedule": {"2005-06": 2526600}, "amount_kind": {"2005-06": "contract_salary"}}]})
        put(self.root, "career/Dwyane_Wade/2005-06/League/option_decisions.json", {"decisions": [
            {"player": "Dwyane Wade", "club": "Miami Heat", "option_season": "2006-07", "kind": "team_option",
             "salary": 3201202, "deadline": "2005-10-31", "decision": "decline", "applied": "2005-10-31"}]})
        self.raw = copy.deepcopy(RAW)
        self.raw["snapshots"] = [s for s in self.raw["snapshots"] if s["as_of"] <= "2005-10-26"]
        put(self.root, "career/Dwyane_Wade/professional_identity.json", self.raw)

    def tearDown(self):
        self.tmp.cleanup()

    def test_a_declined_option_reads_declined_from_its_date(self):
        identity = ic.attach(self.raw, self.root, self.player)
        self.assertEqual(identity_at(identity, "2005-10-20", "2005-06")["contract"],
                         f"{AGREEMENT} (2005-06: $2,526,600; 2006-07 team option at $3,201,202, to be decided by 2005-10-31)")
        self.assertEqual(identity_at(identity, "2005-11-02", "2005-06")["contract"],
                         f"{AGREEMENT} (2005-06: $2,526,600; 2006-07 team option declined 2005-10-31)")

    def test_validation_refuses_a_season_salary_written_into_a_later_snapshot(self):
        self.assertEqual(ic.errors(self.root), [])
        self.raw["snapshots"].append({**self.raw["snapshots"][-1], "as_of": "2005-12-01",
                                      "contract": f"{AGREEMENT} (2005-06: $2,526,600)"})
        put(self.root, "career/Dwyane_Wade/professional_identity.json", self.raw)
        problems = ic.errors(self.root)
        self.assertEqual(len(problems), 1)
        self.assertIn("2005-12-01 snapshot", problems[0])
        # a stored season note never doubles the line: the page season's terms replace it
        identity = ic.attach(self.raw, self.root, self.player)
        self.assertEqual(identity_at(identity, "2005-12-02", "2005-06")["contract"],
                         f"{AGREEMENT} (2005-06: $2,526,600; 2006-07 team option declined 2005-10-31)")

    def test_an_extension_option_reaches_the_line_only_from_its_signing_date(self):
        # 2006-07 opens on 2006-10-01 with the exercised option season; the extension Wade asked for (five seasons from
        # 2007-08, the fifth a Miami team option) is signed on 2006-10-31 and written into the same row of the sheet
        put(self.root, "career/Dwyane_Wade/2006-07/current_state.json", {"current_date": "2006-11-10", "rolled_over_on": "2006-10-01"})
        row = {"player": "Dwyane Wade", "status": "under_contract", "route": "rookie_scale", "signed_date": "2003-07-21",
               "schedule": {"2005-06": 2526600, "2006-07": 3201202},
               "amount_kind": {"2005-06": "contract_salary", "2006-07": "contract_salary"}}
        sub = {"id": "2006-10-31-extension-wadedw01", "route": "rookie_scale_extension", "club": "Miami Heat",
               "signed_date": "2006-10-31", "first_season": "2007-08", "years": 5, "total": 60000000, "record": "x",
               "schedule": {"2007-08": 10000000, "2008-09": 11000000, "2009-10": 12000000, "2010-11": 13000000,
                            "2011-12": 14000000},
               "options": {"2011-12": "team_option"}}
        self.assertTrue(_extend(row, sub, "2006-07", sheet=True))
        put(self.root, "career/Dwyane_Wade/2006-07/00_Team/Finances/contract_schedules.json", {"players": [row]})
        identity = ic.attach(self.raw, self.root, self.player)
        self.assertEqual(identity["contract_terms"]["2006-07"]["options"]["2011-12"]["signed"], "2006-10-31")
        before = f"{AGREEMENT} (2006-07: $3,201,202)"
        self.assertEqual(identity_at(identity, "2006-10-05", "2006-07")["contract"], before)
        self.assertEqual(identity_at(identity, "2006-10-30", "2006-07")["contract"], before)
        self.assertEqual(identity_at(identity, "2006-10-30")["contract"], before)
        self.assertEqual(identity_at(identity, "2006-10-31", "2006-07")["contract"],
                         f"{AGREEMENT} (2006-07: $3,201,202; 2011-12 team option at $14,000,000, to be decided by 2011-06-29)")


if __name__ == "__main__":
    unittest.main()
