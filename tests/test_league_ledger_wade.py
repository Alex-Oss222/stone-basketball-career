"""Wade's row in the league contract ledger (runtime/league_contracts.py, the 2005-10-31 repair).

The summer market names Wade by his register key (dwyane_wade) and Miami's sheet and register carry no bbr_id for him,
so the 2004-05 build missed his sheet row and priced his rookie-scale contract as a new one (2,361,800 raised 10%:
2,597,980 and 2,834,160), which the 2005-06 build carried. These scenarios hold the fix: the ledger keys him by his NBA
id (wadedw01) with Miami's sheet schedule, option seasons and rookie-scale flag; the repair rewrites recorded rows once;
every Miami row is held to Miami's sheet; each reader (options, extensions, club truth, the rollover, continuity) finds
him by wadedw01; and the gates keep every recorded season's valuations and markets as they were. Scratch careers only:
the live repository is read, never written.
"""
from contextlib import nullcontext
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from runtime import league_contracts as lc

ROOT = Path(__file__).resolve().parents[1]
P = "career/Dwyane_Wade"
SOURCE = "Miami contract_schedules.json"
SHEET = {"2003-04": 2197000, "2004-05": 2361800, "2005-06": 2526600, "2006-07": 3201202}
STALE_0405 = {"2004-05": 2361800, "2005-06": 2597980, "2006-07": 2834160}
STALE_0506 = {"2005-06": 2597980, "2006-07": 2834160}
EXERCISE = {"id": "2006-07-option-wadedw01-team_option", "club": "Miami Heat", "player": "Dwyane Wade", "bbr_id": "wadedw01",
            "option_season": "2006-07", "kind": "team_option", "salary": 3201202, "deadline": "2005-10-31",
            "worth": 32453356, "age": 21, "ratio": 10.138, "decider": "Miami Heat", "decision": "exercise",
            "how": "clear: ratio 10.14 at or above 1.2", "recorded_on": "2005-10-31", "applied": "2005-10-31"}


def put(root, rel, data):
    path = Path(root) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data if isinstance(data, str) else json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def read(root, rel):
    return json.loads((Path(root) / rel).read_text(encoding="utf-8"))


def wade_sheet_row(option_open):
    """Wade's cap-sheet row as Miami's records hold it: no bbr_id, the 2006-07 option open or exercised."""
    kinds = {s: "contract_salary" for s in SHEET}
    if option_open:
        kinds["2006-07"] = "team_option"
    return {"player": "Dwyane Wade", "status": "under_contract", "route": "rookie_scale", "signed_date": "2003-07-21",
            "schedule": dict(SHEET), "amount_kind": kinds}


GRANT = {"player": "Brian Grant", "bbr_id": "grantbr01", "status": "under_contract", "route": "existing",
         "schedule": {"2004-05": 13233434, "2005-06": 14336220, "2006-07": 15439006},
         "amount_kind": {"2004-05": "contract_salary", "2005-06": "contract_salary", "2006-07": "early_termination_option"}}
REGISTER = {"players": [{"id": "dwyane_wade", "name": "Dwyane Wade", "bbr_id": None},
                        {"id": "brian_grant", "name": "Brian Grant", "bbr_id": "grantbr01"}]}
NASH = {"player": "Steve Nash", "bbr_id": "nashst01", "club": "Phoenix Suns", "route": "existing", "kind": "existing",
        "schedule": {"2005-06": 9375000, "2006-07": 10500000}, "source": "test"}


def ledger(season, *rows):
    return {"schema_version": 1, "season": season, "kind": "league_contracts", "rule": "test",
            "contracts": sorted(rows, key=lambda c: c["bbr_id"])}


def recorded_career(root):
    """The career as recorded on 2005-10-31 before the repair: both ledgers key Wade by his register key, stale figures."""
    put(root, f"{P}/2004-05/00_Team/Finances/contract_schedules.json", {"players": [wade_sheet_row(True), GRANT]})
    put(root, f"{P}/2004-05/00_Team/Team/Roster/roster.json", REGISTER)
    put(root, f"{P}/2005-06/00_Team/Finances/contract_schedules.json",
        {"players": [wade_sheet_row(False), dict(GRANT, schedule={k: v for k, v in GRANT["schedule"].items() if k != "2004-05"})]})
    put(root, f"{P}/2005-06/00_Team/Team/Roster/roster.json", REGISTER)
    grant = {"player": "Brian Grant", "bbr_id": "grantbr01", "club": "Miami Heat", "route": "existing", "kind": "existing",
             "schedule": dict(GRANT["schedule"]), "source": SOURCE, "options": {"2006-07": "early_termination_option"}}
    put(root, lc.ledger_path("2004-05"), ledger("2004-05", grant, dict(NASH, schedule={"2004-05": 8250000, **NASH["schedule"]}),
        {"player": "dwyane_wade", "bbr_id": "dwyane_wade", "club": "Miami Heat", "route": "existing", "kind": "new",
         "schedule": dict(STALE_0405), "source": SOURCE}))
    put(root, lc.ledger_path("2005-06"), ledger("2005-06", dict(grant, schedule={k: v for k, v in GRANT["schedule"].items() if k != "2004-05"}),
        NASH, {"player": "dwyane_wade", "bbr_id": "dwyane_wade", "club": "Miami Heat", "route": "existing", "kind": "existing",
               "schedule": dict(STALE_0506), "source": SOURCE}))
    put(root, f"{P}/2005-06/League/option_decisions.json", {"decisions": [EXERCISE]})


def market(*miami):
    return {"clubs": {"Miami Heat": list(miami),
                      "Phoenix Suns": [{"player": "Steve Nash", "bbr_id": "nashst01", "salary": 9375000, "years": 2,
                                        "route": "existing", "source": "test"}]}}


def wade_market_row(salary, years):
    """The summer market's row for Wade (`free_agency_2004.miami_contracts`): his register key."""
    return {"player": "dwyane_wade", "bbr_id": "dwyane_wade", "salary": salary, "years": years, "route": "existing", "source": SOURCE}


def build(season, root, record):
    with mock.patch("runtime.free_agency_2004.year_context", lambda year, root: nullcontext()), \
            mock.patch("runtime.free_agency_2004.calendar", return_value={"scale": {}}):
        return lc.build(season, root, record)


class Scratch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        recorded_career(self.root)


class BuildTests(Scratch):
    def test_the_build_keys_wade_by_his_nba_id_with_miami_s_sheet(self):
        built = build("2005-06", self.root, market(wade_market_row(2526600, 2),
                                                   {"player": "Brian Grant", "bbr_id": "grantbr01", "salary": 14336220,
                                                    "years": 2, "route": "existing", "source": SOURCE}))
        self.assertNotIn("dwyane_wade", built)
        wade = built["wadedw01"]
        self.assertEqual((wade["player"], wade["bbr_id"], wade["kind"], wade["club"]), ("Dwyane Wade", "wadedw01", "existing", "Miami Heat"))
        self.assertEqual(wade["schedule"], {"2005-06": 2526600, "2006-07": 3201202})       # the sheet, never 2,597,980 / 2,834,160
        self.assertEqual((wade["options"], wade["rookie_scale"]), ({"2006-07": "team_option"}, True))
        # every other row reads as before: Miami's sheet for Grant, the carried ledger for Nash
        self.assertEqual(built["grantbr01"]["schedule"], {"2005-06": 14336220, "2006-07": 15439006})
        self.assertEqual(built["grantbr01"]["options"], {"2006-07": "early_termination_option"})
        self.assertNotIn("rookie_scale", built["grantbr01"])
        self.assertEqual(built["nashst01"]["schedule"], NASH["schedule"])

    def test_the_next_season_carries_the_nba_id_row(self):
        lc.repair_wade_rows(self.root)
        built = build("2006-07", self.root, market(wade_market_row(3201202, 1)))
        self.assertEqual(built["wadedw01"]["schedule"], {"2006-07": 3201202})
        self.assertTrue(built["wadedw01"]["rookie_scale"])
        self.assertNotIn("options", built["wadedw01"])                                    # exercised on 2005-10-31
        carried = lc.carried("2006-07", self.root)
        self.assertEqual((carried["wadedw01"]["salary"], carried["wadedw01"]["rookie_scale"]), (3201202, True))
        self.assertNotIn("dwyane_wade", carried)

    def test_an_extension_ends_the_rookie_scale_flag(self):
        row = dict(wade_sheet_row(False), extension={"id": "x", "first_season": "2007-08"})
        self.assertTrue(lc.sheet_terms(row, "2006-07")[2])
        self.assertFalse(lc.sheet_terms(row, "2007-08")[2])

    def test_keys(self):
        self.assertEqual(lc.ledger_key("dwyane_wade"), "wadedw01")
        self.assertEqual(lc.ledger_key(None, "Dwyane Wade"), "wadedw01")
        self.assertEqual(lc.ledger_key("nashst01", "Steve Nash"), "nashst01")
        self.assertEqual(lc.sheet_key(wade_sheet_row(False), {"Dwyane Wade": None}), "wadedw01")
        self.assertEqual(lc.wade_key({"dwyane_wade": {}}), "dwyane_wade")                # a ledger written before the repair
        self.assertEqual(lc.wade_key({"wadedw01": {}, "dwyane_wade": {}}), "wadedw01")
        self.assertEqual(lc.find({"dwyane_wade": {"x": 1}}, "wadedw01"), {"x": 1})


class RepairTests(Scratch):
    def test_the_repair_rewrites_both_rows_to_the_sheet_once(self):
        before = lc.sheet_errors(self.root)
        self.assertEqual(len(before), 2)
        self.assertTrue(all("dwyane_wade" in e for e in before))
        changes = lc.repair_wade_rows(self.root)
        self.assertEqual([c["season"] for c in changes], ["2004-05", "2005-06"])
        now = {c["bbr_id"]: c for c in read(self.root, lc.ledger_path("2005-06"))["contracts"]}
        self.assertNotIn("dwyane_wade", now)
        self.assertEqual(now["wadedw01"], {
            "player": "Dwyane Wade", "bbr_id": "wadedw01", "club": "Miami Heat", "route": "existing", "kind": "existing",
            "schedule": {"2005-06": 2526600, "2006-07": 3201202}, "source": SOURCE, "rookie_scale": True,
            "option_history": ["2006-07 team option: exercise (2005-10-31; clear: ratio 10.14 at or above 1.2; "
                               "runtime/options.py, League/option_decisions.json)"]})
        ids = [c["bbr_id"] for c in read(self.root, lc.ledger_path("2005-06"))["contracts"]]
        self.assertEqual(ids, sorted(ids))
        closed = {c["bbr_id"]: c for c in read(self.root, lc.ledger_path("2004-05"))["contracts"]}
        self.assertNotIn("wadedw01", closed)                       # the closed ledger keeps the key its readers used
        self.assertEqual(closed["dwyane_wade"]["schedule"], {"2004-05": 2361800, "2005-06": 2526600, "2006-07": 3201202})
        self.assertEqual(closed["dwyane_wade"]["options"], {"2006-07": "team_option"})
        self.assertEqual(lc.sheet_errors(self.root), [])
        files = [(self.root / lc.ledger_path(s)).read_bytes() for s in ("2004-05", "2005-06")]
        self.assertEqual(lc.repair_wade_rows(self.root), [])                               # idempotent
        self.assertEqual([(self.root / lc.ledger_path(s)).read_bytes() for s in ("2004-05", "2005-06")], files)

    def test_a_dry_run_writes_nothing_and_one_season_can_be_named(self):
        files = [(self.root / lc.ledger_path(s)).read_bytes() for s in ("2004-05", "2005-06")]
        self.assertEqual(len(lc.repair_wade_rows(self.root, write=False)), 2)
        self.assertEqual([(self.root / lc.ledger_path(s)).read_bytes() for s in ("2004-05", "2005-06")], files)
        self.assertEqual([c["season"] for c in lc.repair_wade_rows(self.root, seasons=["2005-06"])], ["2005-06"])

    def test_two_rows_for_wade_become_one(self):
        data = read(self.root, lc.ledger_path("2005-06"))
        data["contracts"].append({"player": "Dwyane Wade", "bbr_id": "wadedw01", "club": "Miami Heat", "route": "existing",
                                  "kind": "existing", "schedule": {"2005-06": 1}, "source": SOURCE})
        put(self.root, lc.ledger_path("2005-06"), data)
        from runtime.continuity import ledger_errors
        self.assertTrue(any("appears twice" in e for e in ledger_errors(self.root, "2005-06")))
        lc.repair_wade_rows(self.root)
        keys = [c["bbr_id"] for c in read(self.root, lc.ledger_path("2005-06"))["contracts"]]
        self.assertEqual((keys.count("wadedw01"), keys.count("dwyane_wade")), (1, 0))
        self.assertEqual(ledger_errors(self.root, "2005-06"), [])


class SheetCheckTests(Scratch):
    def setUp(self):
        super().setUp()
        lc.repair_wade_rows(self.root)

    def edit(self, season, fn):
        data = read(self.root, lc.ledger_path(season))
        fn({c["bbr_id"]: c for c in data["contracts"]})
        put(self.root, lc.ledger_path(season), data)
        return lc.miami_sheet_errors(season, self.root)

    def test_a_miami_row_off_the_sheet_is_refused(self):
        errors = self.edit("2005-06", lambda c: c["grantbr01"]["schedule"].update({"2006-07": 1}))
        self.assertEqual(len(errors), 1)
        self.assertIn("Brian Grant (grantbr01)", errors[0])

    def test_a_season_the_sheet_keeps_and_the_ledger_drops_is_refused_and_other_clubs_are_not_compared(self):
        errors = self.edit("2005-06", lambda c: c["grantbr01"]["schedule"].pop("2006-07"))   # an option the sheet kept
        self.assertEqual(len(errors), 1)
        self.assertIn("Brian Grant (grantbr01)", errors[0])
        self.edit("2005-06", lambda c: c["grantbr01"]["schedule"].update({"2006-07": 15439006}))
        errors = self.edit("2005-06", lambda c: c["wadedw01"]["schedule"].update({"2007-08": 4000000}))   # a season the sheet never held
        self.assertEqual(len(errors), 1)
        self.assertIn("Dwyane Wade (wadedw01)", errors[0])
        self.edit("2005-06", lambda c: c["wadedw01"]["schedule"].pop("2007-08"))
        self.assertEqual(self.edit("2005-06", lambda c: c["nashst01"]["schedule"].update({"2006-07": 1})), [])

    def test_a_miami_row_without_a_sheet_row_is_refused(self):
        def add(c):
            c["nashst01"]["club"] = "Miami Heat"
        errors = self.edit("2005-06", add)
        self.assertEqual(len(errors), 1)
        self.assertIn("no row on Miami's 2005-06 cap sheet", errors[0])

    def test_any_row_of_his_may_carry_the_ledger_s_contract(self):
        rel = f"{P}/2005-06/00_Team/Finances/contract_schedules.json"
        sheet = read(self.root, rel)
        for p in sheet["players"]:
            if p["player"] == "Brian Grant":
                p["status"] = "waived"                             # still owed: his ledger row stays the contract
        sheet["players"].append(dict(GRANT, schedule={"2005-06": 1, "2006-07": 2}))   # a later deal of his
        put(self.root, rel, sheet)
        self.assertEqual(lc.miami_sheet_errors("2005-06", self.root), [])
        sheet["players"] = [p for p in sheet["players"] if p["status"] != "waived"]
        put(self.root, rel, sheet)                                 # no row of his carries the ledger's contract
        self.assertEqual(len(lc.miami_sheet_errors("2005-06", self.root)), 1)

    def test_continuity_holds_the_live_ledger_to_the_sheet(self):
        from runtime.continuity import ledger_errors
        self.assertEqual(ledger_errors(self.root, "2005-06"), [])
        errors = self.edit("2005-06", lambda c: c["wadedw01"]["schedule"].update({"2006-07": 2834160}))
        self.assertEqual(ledger_errors(self.root, "2005-06"), errors)


class GateTests(Scratch):
    def test_the_2005_06_valuation_fit_never_counts_wade(self):
        before = lc.under_contract("2005-06", self.root)
        self.assertIn("dwyane_wade", before)                       # recorded: a key no evidence record carries
        lc.repair_wade_rows(self.root)
        after = lc.under_contract("2005-06", self.root)
        self.assertNotIn("wadedw01", after)
        self.assertEqual(set(after) - {"dwyane_wade"}, set(before) - {"dwyane_wade"})
        self.assertEqual(lc.under_contract("2004-05", self.root)["dwyane_wade"]["salary"], 2361800)

    def test_from_2006_07_his_row_counts_like_every_contract(self):
        lc.repair_wade_rows(self.root)
        self.assertEqual(lc.under_contract("2006-07", self.root)["wadedw01"]["salary"], 3201202)   # carried, before the rollover
        put(self.root, lc.ledger_path("2006-07"), ledger("2006-07", {
            "player": "Dwyane Wade", "bbr_id": "wadedw01", "club": "Miami Heat", "route": "existing", "kind": "existing",
            "schedule": {"2006-07": 3201202}, "source": SOURCE, "rookie_scale": True}))
        self.assertEqual(lc.under_contract("2006-07", self.root)["wadedw01"]["salary"], 3201202)


class ReaderTests(Scratch):
    def test_an_option_decision_reaches_his_nba_id_row(self):
        from runtime import options
        lc.repair_wade_rows(self.root)
        data = read(self.root, lc.ledger_path("2005-06"))
        for c in data["contracts"]:
            if c["bbr_id"] == "wadedw01":
                c["options"] = {"2006-07": "team_option"}
        put(self.root, lc.ledger_path("2005-06"), data)
        decline = dict(EXERCISE, id="t", decision="decline", how="test")
        decline.pop("applied")
        self.assertEqual(options.apply({"decisions": [decline]}, "2005-06", self.root, "2005-10-31"), ["t"])
        wade = lc.read("2005-06", self.root)["wadedw01"]
        self.assertEqual((wade["schedule"], wade["options"]), ({"2005-06": 2526600}, {}))
        self.assertEqual(read(self.root, f"{P}/2005-06/00_Team/Finances/contract_schedules.json")["players"][0]["schedule"],
                         {"2003-04": 2197000, "2004-05": 2361800, "2005-06": 2526600})
        self.assertEqual(lc.miami_sheet_errors("2005-06", self.root), [])

    def test_a_rookie_option_never_reaches_a_register_key_row(self):
        from runtime import options
        decline = dict(EXERCISE, id="t", decision="decline", how="test")
        decline.pop("applied")
        options.apply({"decisions": [decline]}, "2005-06", self.root, "2005-10-31")
        self.assertEqual(lc.read("2005-06", self.root)["dwyane_wade"]["schedule"], STALE_0506)   # the fallback is extension-only

    def test_open_options_name_him_by_his_nba_id(self):
        from runtime import options
        rows = [r for r in options.open_options("2004-05", self.root) if r[2] == "Dwyane Wade"]
        self.assertEqual(rows, [("Miami Heat", "wadedw01", "Dwyane Wade", "2006-07", "team_option", 3201202, True)])

    def test_club_truth_reads_his_nba_id_as_his_holding(self):
        from runtime import club_truth
        with mock.patch("runtime.club_truth._season", return_value="2005-06"), \
                mock.patch("runtime.rotations.miami_holds", return_value=frozenset({"dwyane_wade"})):
            self.assertEqual(club_truth.holder("wadedw01", None, "2005-11-01", self.root)[0], "Miami Heat")
            self.assertEqual(club_truth.holder("wadedw01", "Dwyane Wade", "2005-11-01", self.root)[0], "Miami Heat")

    def test_the_rollover_s_lookup_finds_his_row_under_either_key(self):
        """The rollover keys Miami's market rows by the register (`rollover.WADE_ID`); `find` reads the ledger's key."""
        from runtime.rollover import WADE_ID
        lc.repair_wade_rows(self.root)
        self.assertEqual(lc.find(lc.read("2005-06", self.root), WADE_ID)["bbr_id"], "wadedw01")
        self.assertEqual(lc.find(lc.read("2004-05", self.root), "wadedw01")["bbr_id"], "dwyane_wade")
        self.assertEqual(lc.find(lc.read("2005-06", self.root), "nashst01")["player"], "Steve Nash")


class ExtensionTests(unittest.TestCase):
    """Wade's extension day on a ledger keyed by his NBA id: his decision names that key, the signed extension reaches the
    row, his row is never another club's payroll, and the offer is the one the register-key ledger gave."""

    def run_day(self, nba_key):
        from tests import test_extensions as te
        ext = te.ext
        tmp, root = te.scratch()
        self.addCleanup(tmp.cleanup)
        te.wade_2006(root)
        if nba_key:
            rel = f"{P}/2006-07/League/contracts.json"
            data = read(root, rel)
            data["contracts"][0].update(player="Dwyane Wade", bbr_id="wadedw01")
            put(root, rel, data)
        ev = te.FakeEvidence({"wadedw01": {"value": 30, "price": 12_455_000, "age": 22}}, planning="2006-07",
                             mid_level=5_215_000, tax=65_420_000)
        patches = te.patched(({}, {"dwyane_wade"}), ev)
        for p in patches:
            p.start()
        try:
            ext.clear_cache()
            ext._REPLAY.clear()
            decided, *_ = ext.run("2006-10-31", root)
            from runtime.milestone_records import version
            from scripts.player_milestone import reply
            oid = ext.offer_id("2006-10-31")
            path = ext.offer_path(root, "2006-07", oid)
            with mock.patch("scripts.player_milestone.refresh"):
                reply(root, {"kind": "extension", "season": "2006-07", "event_id": oid, "action": "accept", "date": "2006-10-31",
                             "text": "I accept the extension.", "source_ref": f"{P}/2006-07/current_state.json"}, version(path))
            _, _, applied, _ = ext.run("2006-10-31", root)
            errors = ext.extension_errors(root)
            payroll = ext.payrolls("2006-10-31", root)
        finally:
            for p in patches:
                p.stop()
        return root, decided[0], applied, errors, payroll

    def test_his_decision_and_extension_follow_the_nba_id(self):
        root, d, applied, errors, payroll = self.run_day(True)
        self.assertEqual((d["bbr_id"], d["ledger_key"], applied), ("wadedw01", "wadedw01", [d["id"]]))
        row = read(root, f"{P}/2006-07/League/contracts.json")["contracts"][0]
        self.assertEqual((row["bbr_id"], row["extension"]["id"]), ("wadedw01", d["id"]))
        self.assertEqual(errors, [])
        _, old, _, old_errors, old_payroll = self.run_day(False)
        self.assertEqual(old["ledger_key"], "dwyane_wade")       # a ledger written before the repair: the key it carries
        self.assertEqual((old["offer"], old["payroll"], old_errors), (d["offer"], d["payroll"], []))
        self.assertEqual(old_payroll, payroll)                    # his row is Miami's sheet, never a second payroll


class LiveRecordTests(unittest.TestCase):
    def test_the_recorded_rows_come_from_the_2004_05_build(self):
        """The stale figures are the 2004-05 build's raise on the market's first-year salary: 2,361,800 x (1 + 10% x n)."""
        self.assertEqual(lc.schedule_for(2361800, 3, "2004-05", "existing"), STALE_0405)

    def test_the_repair_on_a_copy_of_the_live_ledgers(self):
        """The live ledgers (read only) repaired in a scratch copy: Miami's rows all agree with its sheets."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        seasons = [p.parts[-3] for p in sorted((ROOT / P).glob("*/League/contracts.json"))]
        if not seasons:
            self.skipTest("no league ledger in this checkout")
        for s in seasons:
            for rel in (lc.ledger_path(s), Path(P) / s / "League/option_decisions.json",
                        Path(P) / s / "00_Team/Finances/contract_schedules.json", Path(P) / s / "00_Team/Team/Roster/roster.json"):
                if (ROOT / rel).is_file():
                    (root / rel).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy(ROOT / rel, root / rel)
        lc.repair_wade_rows(root)
        self.assertEqual(lc.sheet_errors(root), [])
        self.assertEqual(lc.repair_wade_rows(root), [])
        for s in seasons:
            entries = lc.read(s, root)
            key = "wadedw01" if s >= lc.NBA_KEY_FROM else lc.wade_key(entries)
            if key in entries:
                self.assertEqual(entries[key]["player"], "Dwyane Wade")
                if s <= "2006-07":                                  # his rookie-scale contract's seasons
                    self.assertTrue(entries[key].get("rookie_scale"))


if __name__ == "__main__":
    unittest.main()
