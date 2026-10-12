"""Final audit, group 4 (R3): the team desk labels the contracts that ended on June 30 through the summer to the rollover.

The record tests read the repository's committed records (read-only); the summer-outcome test puts a small market record
in a temporary folder. Each fails on the code and records before the fix.
"""
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
CAREER = ROOT / "career/Dwyane_Wade"
FIVE = {"Mike James", "Caron Butler", "Eddie Gill", "Mike Wilks", "Matt Carroll"}
PENDING = "recorded when the summer market closes (2006-09-30)"


def block(season, on, page):
    from runtime import team_status
    return next(v for k, v in team_status.blocks(ROOT, on, season).items() if k.as_posix().endswith(f"{season}/00_Team/{page}"))


def rows(text):
    out = {}
    for line in text.splitlines():
        if line.startswith("| ["):
            cells = [c.strip() for c in line.strip("|").split("|")]
            out[cells[0][1:cells[0].index("]")]] = cells
    return out


class EndedContracts(unittest.TestCase):
    def test_june_30_still_reads_expiring(self):
        from runtime import team_status
        ending = team_status.expiring(ROOT, "2006-06-30", "2005-06")
        self.assertEqual(set(ending), FIVE)
        self.assertTrue(all(v.startswith("expiring June 30, 2006") for v in ending.values()))
        self.assertIn("qualifying-offer decision is due by June 30, 2006", ending["Caron Butler"])
        self.assertEqual(team_status.ended(ROOT, "2006-06-30", "2005-06"), set())
        self.assertIn("15 under contract (12 active, 3 on the injured list)", block("2005-06", "2006-06-30", "Team/README.md"))
        self.assertIn("5 of the contracts end on June 30, 2006", block("2005-06", "2006-06-30", "README.md"))

    def test_from_july_1_the_contracts_have_ended_until_the_rollover(self):
        from runtime import team_status
        for on in ("2006-07-01", "2006-09-30"):
            ending = team_status.expiring(ROOT, on, "2005-06")
            self.assertEqual(set(ending), FIVE, on)
            for name, label in ending.items():
                self.assertTrue(label.startswith("contract ended June 30, 2006; free agent; "), (on, label))
                self.assertIn(PENDING, label)                    # no 2006 market record yet: never a replay
            self.assertIn("qualifying-offer decision", ending["Caron Butler"])
            self.assertEqual(team_status.ended(ROOT, on, "2005-06"), FIVE)
            reg = {p["name"]: (p, a, role) for p, a, role in team_status.register(ROOT, on, "2005-06")}
            for name in FIVE:
                self.assertEqual(reg[name][1:], ("Contract ended June 30, 2006", "N/A"), name)
                self.assertEqual(reg[name][0]["status"], "under_contract")          # the register's status is unchanged
            team = block("2005-06", on, "Team/README.md")
            self.assertIn("10 under contract (9 active, 1 on the injured list)", team)
            self.assertIn("5 contracts ended on June 30, 2006; they are not counted", team)
            self.assertIn("10 players under contract, 1 on the injured list.", block("2005-06", on, "README.md"))
            table = rows(block("2005-06", on, "Team/Roster/README.md"))
            self.assertEqual(table["Matt Carroll"][2:], [ending["Matt Carroll"], "Contract ended June 30, 2006", "N/A"])
            self.assertNotIn("Injured list", table["Eddie Gill"][3])
        stored = json.loads((CAREER / "2005-06/00_Team/Team/Roster/roster.json").read_text(encoding="utf-8"))
        self.assertTrue(all(p["status"] == "under_contract" for p in stored["players"] if p["name"] in FIVE))

    def test_the_summer_outcome_comes_from_the_closed_market_record(self):
        from runtime import free_agency_2004, team_status
        events = [
            {"date": "2006-06-30", "kind": "qualifying_offer", "player": "Caron Butler", "bbr_id": "butleca01",
             "club": "Miami Heat", "amount": 3077021, "price": 8608511},
            {"date": "2006-07-14", "kind": "offer_sheet", "player": "Caron Butler", "bbr_id": "butleca01",
             "club": "Denver Nuggets", "from": "Miami Heat", "salary": 8000000, "years": 5},
            {"date": "2006-07-14", "kind": "offer_sheet_matched", "player": "Caron Butler", "bbr_id": "butleca01",
             "club": "Miami Heat", "from": "Denver Nuggets", "salary": 8000000, "years": 5, "route": "bird"},
            {"date": "2006-07-21", "kind": "signing", "player": "Mike James", "bbr_id": "jamesmi01", "club": "Toronto Raptors",
             "from": "Miami Heat", "salary": 5500000, "years": 4, "route": "mid_level", "agreed": "2006-07-21"},
            {"date": "2006-08-04", "kind": "re_sign", "player": "Matt Carroll", "bbr_id": "carroma01", "club": "Miami Heat",
             "from": "Miami Heat", "salary": 900000, "years": 1, "route": "minimum", "agreed": "2006-08-04"}]
        record = {"to": "2006-09-30", "events": events,
                  "unsigned_pool": [{"player": "Eddie Gill", "bbr_id": "gilled01", "price": 800000, "rights": "Miami Heat"}],
                  "left_the_league": [{"player": "Mike Wilks", "bbr_id": "wilksmi01", "basis": "no real 2006-07 role"}]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "free_agency_2006.json"
            path.write_text(json.dumps(record), encoding="utf-8")
            with mock.patch.object(free_agency_2004, "record_for", lambda season: path):
                early = team_status.expiring(ROOT, "2006-09-29", "2005-06")      # the record's close not reached
                ending = team_status.expiring(ROOT, "2006-09-30", "2005-06")
                record["events"] = [e for e in events if e["kind"] != "qualifying_offer"]
                path.write_text(json.dumps(record), encoding="utf-8")
                untendered = team_status.expiring(ROOT, "2006-09-30", "2005-06")["Caron Butler"]
        self.assertTrue(all(PENDING in v for v in early.values()))
        self.assertEqual(ending["Caron Butler"], "contract ended June 30, 2006; free agent; Miami Heat tendered a $3,077,021 "
                         "qualifying offer on 2006-06-30 (restricted free agent); signed an offer sheet with Denver Nuggets on "
                         "2006-07-14 ($8,000,000 x 5 seasons); Miami Heat matched it")
        self.assertEqual(ending["Mike James"], "contract ended June 30, 2006; free agent; signed with Toronto Raptors on "
                         "2006-07-21 ($5,500,000 x 4 seasons, mid-level exception)")
        self.assertIn("re-signed with Miami Heat on 2006-08-04 ($900,000 x 1 season, minimum)", ending["Matt Carroll"])
        self.assertIn("unsigned when the market closed on 2006-09-30; Miami Heat holds his rights", ending["Eddie Gill"])
        self.assertIn("left the league (no real 2006-07 role)", ending["Mike Wilks"])
        self.assertIn("rookie scale: Miami made no qualifying offer (unrestricted); signed an offer sheet", untendered)


class ClosedSeasonBlocks(unittest.TestCase):
    """2004-05's register blocks froze on 2005-09-30 counting eight ended contracts; they were regenerated once."""

    def test_2004_05_blocks_regenerated_as_of_september_30(self):
        from runtime import team_status
        self.assertEqual(team_status.regenerate_closed(ROOT, "2004-05", "2005-09-30", write=False), [])
        team = CAREER / "2004-05/00_Team"
        readme = (team / "README.md").read_text(encoding="utf-8")
        self.assertIn("**Status on 2005-09-30**", readme)
        self.assertIn("7 players under contract, 0 on the injured list. 8 contracts ended on June 30, 2005; they are not "
                      "counted", readme)
        self.assertIn("7 under contract (7 active, 0 on the injured list)", (team / "Team/README.md").read_text(encoding="utf-8"))
        table = rows((team / "Team/Roster/README.md").read_text(encoding="utf-8"))
        self.assertEqual(sum(r[3] == "Contract ended June 30, 2005" for r in table.values()), 8)
        self.assertIn("re-signed with Miami Heat on 2005-08-19 ($7,954,111 x 4 seasons, Bird rights)", table["Matt Harpring"][2])
        self.assertIn("left the league (no real 2005-06 role)", table["Maurice Baker"][2])
        self.assertEqual(table["John Thomas"][3:], ["Contract ended June 30, 2005", "N/A"])   # was on the injured list
        self.assertEqual(table["Brian Grant"][2:4], ["under contract", "Available"])


if __name__ == "__main__":
    unittest.main()
