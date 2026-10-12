"""Audit group A (career date 2006-06-20): the contract catalog follows the dated option decisions, league moves and
Miami's sheet, and its status never claims a contract that is not in force."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from runtime.contract_archive import signed_record
from runtime.contract_navigation import END, START, build_contract_navigation
from runtime.contract_pages import orphan_pages, prune_orphan_pages
from runtime.player_contracts import build_contract_catalog

ROOT = Path(__file__).resolve().parents[1]
PLAYER = ROOT / "career/Dwyane_Wade"


class CatalogFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.player = self.root / "career/Dwyane_Wade"
        self.write("career/Dwyane_Wade/2003-04/current_state.json", {"current_date": "2004-10-01"})
        self.write("career/Dwyane_Wade/2004-05/current_state.json", {"current_date": "2005-10-01"})
        self.clock("2006-06-20")
        self.write("career/Dwyane_Wade/professional_identity.json", {
            "display_name": "Dwyane Wade", "player_id": "dwyane_wade", "aliases": ["wadedw01"]})
        self.write("career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json", {
            "as_of": "2003-06-26", "players": [
                {"name": "Dwyane Wade", "registry_id": "wadedw01", "bbr_id": "wadedw01", "team_name": "Miami Heat"},
                {"name": "Veteran Player", "registry_id": "vet01", "bbr_id": "vet01", "team_name": "Other Club"},
                {"name": "Bench Player", "registry_id": "bench01", "bbr_id": "bench01", "team_name": "Other Club"},
                {"name": "Draft Pick", "registry_id": "pick01", "bbr_id": "pick01", "team_name": "Other Club"}]})
        self.vet = {"player": "Veteran Player", "bbr_id": "vet01", "status": "under_contract", "signed_date": "2001-07-20",
                    "schedule": {"2003-04": 3000000, "2004-05": 3200000, "2005-06": 3400000},
                    "amount_kind": {"2003-04": "contract_salary", "2004-05": "contract_salary", "2005-06": "team_option"}}
        self.bench = {"player": "Bench Player", "bbr_id": "bench01", "status": "under_contract",
                      "schedule": {"2003-04": 1000000, "2004-05": 1100000, "2005-06": 1200000},
                      "amount_kind": {"2003-04": "contract_salary", "2004-05": "contract_salary", "2005-06": "contract_salary"}}
        self.write("library/2003/league/nba_2003_contracts.json",
                   {"as_of": "2003-06-26", "clubs": {"Other Club": {"players": [self.vet, self.bench]}}})

    def write(self, path, value):
        file = self.root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(json.dumps(value), encoding="utf-8")

    def clock(self, value):
        self.write("career/Dwyane_Wade/2005-06/current_state.json", {"current_date": value})

    def profile(self, name):
        return next(p for p in build_contract_catalog(self.root, self.player)["players"] if p["name"] == name)

    def decision(self, player, bbr, club, season, kind, decision, deadline, applied, salary):
        return {"id": f"{season}-option-{bbr}-{kind}", "club": club, "player": player, "bbr_id": bbr,
                "option_season": season, "kind": kind, "salary": salary, "deadline": deadline, "decision": decision,
                "decider": club, "recorded_on": applied, "applied": applied}

    def moves(self, season, entries):
        self.write(f"career/Dwyane_Wade/{season}/League/league_moves.json",
                   {"schema_version": 1, "kind": "league_moves", "season": season, "entries": entries})


class OptionDecisionTests(CatalogFixture):
    def test_exercised_option_on_the_sheet_keeps_its_outcome_and_date(self):
        # Miami's sheet turns an exercised option into contract salary and keeps team_option_season (Wade, 2006-07)
        row = {"player": "Veteran Player", "bbr_id": "vet01", "status": "under_contract", "signed_date": "2003-07-21",
               "schedule": {"2003-04": 1, "2004-05": 2, "2005-06": 3, "2006-07": 3201202},
               "amount_kind": {s: "contract_salary" for s in ("2003-04", "2004-05", "2005-06", "2006-07")},
               "team_option_season": "2006-07", "fourth_year_option_deadline": "2005-10-31"}
        self.write("career/Dwyane_Wade/2005-06/00_Team/Finances/contract_schedules.json",
                   {"as_of": "2005-11-01", "team": "Miami Heat", "players": [row]})
        self.write("career/Dwyane_Wade/2005-06/League/option_decisions.json", {"decisions": [
            self.decision("Veteran Player", "vet01", "Miami Heat", "2006-07", "team_option", "exercise",
                          "2005-10-31", "2005-10-31", 3201202)]})
        current = self.profile("Veteran Player")["current"]
        self.assertEqual("2003-07-21", current["signed_on"])
        self.assertEqual([("2006-07", "team_option", 3201202, "2005-10-31", "exercised", "2005-10-31")],
                         [(o["season"], o["type"], o["amount"], o["deadline"], o["outcome"], o["outcome_date"])
                          for o in current["options"]])

    def test_declined_option_shows_its_outcome_and_closes_the_season(self):
        self.write("career/Dwyane_Wade/2004-05/League/option_decisions.json", {"decisions": [
            self.decision("Veteran Player", "vet01", "Other Club", "2005-06", "team_option", "decline",
                          "2004-10-31", "2004-11-23", 3400000)]})
        p = self.profile("Veteran Player")
        agreement = p["history"][0]
        option = agreement["options"][0]
        self.assertEqual(("declined", "2004-11-23", "2004-10-31"), (option["outcome"], option["outcome_date"], option["deadline"]))
        self.assertEqual("2004-05", agreement["end_season"])
        self.assertEqual("2005-06-30", agreement["expiry_date"])
        self.assertIsNone(p["current"])                       # no "under contract" status without a contract in force
        self.assertNotIn(p["status"], ("under_contract", "team_option_pending"))

    def test_the_salary_row_keeps_its_evidence_and_states_the_outcome(self):
        self.vet["conditions"] = {"2005-06": "Team option; no decision recorded on or before 2003-06-26."}
        self.write("library/2003/league/nba_2003_contracts.json",
                   {"as_of": "2003-06-26", "clubs": {"Other Club": {"players": [self.vet, self.bench]}}})
        self.write("career/Dwyane_Wade/2004-05/League/option_decisions.json", {"decisions": [
            self.decision("Veteran Player", "vet01", "Other Club", "2005-06", "team_option", "decline",
                          "2004-10-31", "2004-11-23", 3400000)]})
        rows = {r["season"]: r["condition"] for r in self.profile("Veteran Player")["history"][0]["salary_rows"]}
        self.assertEqual("Team option; no decision recorded on or before 2003-06-26. "
                         "Team option declined 2004-11-23; not part of the contract.", rows["2005-06"])
        self.assertIsNone(rows["2004-05"])
        before = build_contract_catalog(self.root, self.player, "2004-11-22")["players"]    # the day before the decision
        rows = {r["season"]: r["condition"] for r in next(p for p in before if p["id"] == "vet01")["history"][0]["salary_rows"]}
        self.assertEqual("Team option; no decision recorded on or before 2003-06-26.", rows["2005-06"])

    def test_draft_pick_contract_from_the_ledger_carries_its_option_decision(self):
        self.write("career/Dwyane_Wade/2004-05/League/contracts.json", {"contracts": [
            {"player": "Draft Pick", "bbr_id": "pick01", "club": "Other Club", "kind": "existing", "route": "existing",
             "schedule": {"2004-05": 3000000, "2005-06": 3300000, "2006-07": 4200000},
             "options": {"2006-07": "team_option"}, "rookie_scale": True, "source": "fixture"}]})
        self.write("career/Dwyane_Wade/2005-06/League/option_decisions.json", {"decisions": [
            self.decision("Draft Pick", "pick01", "Other Club", "2006-07", "team_option", "exercise",
                          "2005-10-31", "2005-10-31", 4200000)]})
        current = self.profile("Draft Pick")["current"]
        self.assertIsNotNone(current)
        self.assertEqual("Other Club", current["team"])
        self.assertEqual([("2006-07", "exercised", "2005-10-31")],
                         [(o["season"], o["outcome"], o["outcome_date"]) for o in current["options"]])


class LeagueMoveTests(CatalogFixture):
    def test_waiver_closes_and_claim_reassigns_the_agreement(self):
        self.moves("2004-05", [
            {"id": "w1", "date": "2004-11-02", "kind": "waive", "player": "Bench Player", "bbr_id": "bench01",
             "from": "Other Club", "to": None},
            {"id": "c1", "date": "2004-11-04", "kind": "claim", "player": "Bench Player", "bbr_id": "bench01",
             "from": None, "to": "Claim Club", "waiver": "w1", "contract": {"type": "claimed contract", "until": "2005-04-20"}}])
        self.clock("2005-06-01")
        current = self.profile("Bench Player")["current"]
        self.assertEqual("Claim Club", current["team"])
        self.assertEqual([("2004-11-04", "Other Club", "Claim Club")],
                         [(a["date"], a["from"], a["to"]) for a in current["assignment_history"]])

    def test_cleared_waiver_ends_the_agreement_on_the_waiver_date(self):
        self.moves("2005-06", [
            {"id": "w1", "date": "2005-11-01", "kind": "waive", "player": "Bench Player", "bbr_id": "bench01",
             "from": "Other Club", "to": None},
            {"id": "x1", "date": "2005-11-03", "kind": "clear", "player": "Bench Player", "bbr_id": "bench01",
             "from": None, "to": None, "waiver": "w1"}])
        p = self.profile("Bench Player")
        self.assertIsNone(p["current"])
        self.assertEqual(("waived", "2005-11-01"), (p["history"][0]["status"], p["history"][0]["ended_on"]))
        self.assertNotIn("under", p["status"])

    def test_ten_day_and_rest_of_season_are_new_agreements_and_trades_assign(self):
        self.moves("2005-06", [
            {"id": "w1", "date": "2005-11-01", "kind": "waive", "player": "Bench Player", "bbr_id": "bench01",
             "from": "Other Club", "to": None},
            {"id": "x1", "date": "2005-11-03", "kind": "clear", "player": "Bench Player", "bbr_id": "bench01", "waiver": "w1"},
            {"id": "t1", "date": "2006-01-07", "kind": "ten_day", "player": "Bench Player", "bbr_id": "bench01",
             "from": None, "to": "Ten Club", "contract": {"type": "ten_day", "until": "2006-01-17", "salary": "pro-rated minimum"}},
            {"id": "r1", "date": "2006-01-17", "kind": "rest_of_season", "player": "Bench Player", "bbr_id": "bench01",
             "from": "Ten Club", "to": "Ten Club",
             "contract": {"type": "rest_of_season", "until": "2006-04-19", "salary": "pro-rated minimum"}},
            {"deal": "d1", "date": "2006-02-01", "kind": "trade", "player": "Bench Player", "bbr_id": "bench01",
             "from": "Ten Club", "to": "Trade Club"}])
        p = self.profile("Bench Player")
        current = p["current"]
        self.assertEqual(("rest-of-season contract", "2006-01-17", "Ten Club", "Trade Club", "2006-06-30"),
                         (current["type"], current["signed_on"], current["signing_team"], current["team"], current["expiry_date"]))
        ten_day = next(c for c in p["history"] if c["type"] == "10-day contract")
        self.assertEqual(("expired", "2006-01-17"), (ten_day["status"], ten_day["expiry_date"]))
        self.assertEqual("under_contract", p["status"])


class AgreementTests(CatalogFixture):
    def test_assigned_club_is_the_latest_assignment_whatever_the_source_order(self):
        # Miami's own trade of 2005-01-24 is applied after the 2005 summer trade back to Miami: the later one names the club
        self.write("career/Dwyane_Wade/2004-05/00_Team/Transactions/Trades/t1.json", {
            "trade_id": "t1", "status": "completed", "applied": "2005-01-24",
            "trade": {"partner": "Other Club", "miami_in": ["Veteran Player"], "miami_out": []}})
        self.write("career/Dwyane_Wade/2005-06/00_Team/Transactions/Trades/t2.json", {
            "trade_id": "t2", "status": "completed", "applied": "2005-01-10",
            "trade": {"partner": "Third Club", "miami_in": [], "miami_out": ["Veteran Player"]}})
        self.write("career/Dwyane_Wade/2004-05/10_Free_Agency/free_agency_2005.json", {"events": [
            {"date": "2005-08-05", "kind": "trade", "player": "Veteran Player", "bbr_id": "vet01", "club": "Summer Club",
             "from": "Miami Heat", "deal": "s1"}]})
        self.write("career/Dwyane_Wade/2005-06/League/contracts.json", {"contracts": []})
        self.vet["schedule"]["2005-06"] = 3400000
        self.vet["amount_kind"]["2005-06"] = "contract_salary"
        self.write("library/2003/league/nba_2003_contracts.json",
                   {"as_of": "2003-06-26", "clubs": {"Other Club": {"players": [self.vet, self.bench]}}})
        self.clock("2005-09-01")
        current = self.profile("Veteran Player")["current"]
        self.assertEqual(["2005-01-10", "2005-01-24", "2005-08-05"], [a["date"] for a in current["assignment_history"]])
        self.assertEqual("Summer Club", current["team"])

    def test_unrecorded_amounts_do_not_split_one_agreement(self):
        # a reported re-signing without amounts and the sheet row a trade brought in under its baseline id (P.J. Brown)
        self.write("library/2003/league/nba_2003_offseason_transactions.json", {"season": "2003-04", "signings": [
            {"kind": "re_sign", "player": "Veteran Player", "bbr_id": "vet01", "to": "Other Club", "date": "2003-07-16",
             "years": 4}]})
        self.write("career/Dwyane_Wade/2005-06/00_Team/Finances/contract_schedules.json", {"as_of": "2006-01-16",
            "team": "Miami Heat", "players": [{"player": "Veteran Player", "bbr_id": "vet01", "status": "under_contract",
            "contract_id": "vet01-baseline-2003-06-26", "schedule": {"2005-06": 8500000, "2006-07": 8500000},
            "amount_kind": {"2005-06": "contract_salary", "2006-07": "contract_salary"}}]})
        p = self.profile("Veteran Player")
        current = p["current"]
        self.assertEqual("vet01-baseline-2003-06-26", current["id"])
        self.assertEqual({"2005-06": 8500000, "2006-07": 8500000},
                         {r["season"]: r["salary"] for r in current["salary_rows"] if r["season"] >= "2005-06"})
        self.assertEqual(1, sum(1 for c in p["history"] if "2006-07" in {r["season"] for r in c["salary_rows"]}))

    def test_miami_sheet_agreement_ends_with_its_last_scheduled_season(self):
        self.write("career/Dwyane_Wade/2003-04/00_Team/Finances/contract_schedules.json", {"as_of": "2003-10-01",
            "team": "Miami Heat", "players": [{"player": "Bench Player", "bbr_id": "bench01", "status": "camp_contract",
            "signed_date": "2003-09-30", "schedule": {"2003-04": 600000}, "amount_kind": {"2003-04": "contract_salary"}}]})
        p = self.profile("Bench Player")
        camp = next(c for c in p["history"] if c["signed_on"] == "2003-09-30")
        self.assertEqual(("2003-04", "2004-06-30"), (camp["end_season"], camp["expiry_date"]))
        self.assertNotEqual("2003-09-30", (p["current"] or {}).get("signed_on"))


class LedgerTests(CatalogFixture):
    """The league contract ledger and later agreements settle where an agreement whose end its record leaves open ends."""

    def ledger(self, season, contracts):
        self.write(f"career/Dwyane_Wade/{season}/League/contracts.json", {"season": season, "contracts": contracts})

    def test_a_ledger_agreement_the_next_ledger_does_not_carry_ends(self):
        # T.J. Ford: carried as a Milwaukee scale contract in 2004-05, a new minimum elsewhere in the 2005-06 ledger
        self.ledger("2004-05", [{"player": "Draft Pick", "bbr_id": "pick01", "club": "Other Club", "kind": "existing",
                                 "schedule": {"2004-05": 2000000, "2005-06": 2100000, "2006-07": 2700000},
                                 "options": {"2006-07": "team_option"}, "rookie_scale": True, "source": "fixture"}])
        self.ledger("2005-06", [{"player": "Draft Pick", "bbr_id": "pick01", "club": "New Club", "kind": "new",
                                 "schedule": {"2005-06": 700000}, "source": "fixture"}])
        p = self.profile("Draft Pick")
        agreement = p["history"][0]
        self.assertEqual(("2004-05", "2005-06-30", "expired"), (agreement["end_season"], agreement["expiry_date"], agreement["status"]))
        rows = {r["season"]: r["condition"] for r in agreement["salary_rows"]}
        self.assertIsNone(rows["2004-05"])
        for season in ("2005-06", "2006-07"):
            self.assertEqual("Not carried by the 2005-06 league contract ledger; not part of the contract.", rows[season])
        self.assertIsNone(p["current"])
        # carried on as an existing contract (any club: a trade assigns it), the agreement runs on
        self.ledger("2005-06", [{"player": "Draft Pick", "bbr_id": "pick01", "club": "New Club", "kind": "existing",
                                 "schedule": {"2005-06": 2100000, "2006-07": 2700000}, "source": "fixture"}])
        self.assertEqual("2006-07", self.profile("Draft Pick")["history"][0]["end_season"])

    def test_the_ledger_continues_an_open_fragment_at_the_same_club(self):
        self.bench["schedule"] = {"2002-03": 900000, "2003-04": 1000000}
        self.bench["amount_kind"] = {"2002-03": "contract_salary", "2003-04": "contract_salary"}
        self.write("library/2003/league/nba_2003_contracts.json",
                   {"as_of": "2003-06-26", "clubs": {"Other Club": {"players": [self.vet, self.bench]}}})
        fragment = self.profile("Bench Player")["history"][0]["id"]
        self.ledger("2004-05", [{"player": "Bench Player", "bbr_id": "bench01", "club": "Other Club", "kind": "existing",
                                 "schedule": {"2004-05": 1100000, "2005-06": 1200000}, "source": "fixture"}])
        history = self.profile("Bench Player")["history"]
        self.assertEqual([fragment], [c["id"] for c in history])          # one agreement, its id kept
        self.assertEqual({"2002-03": 900000, "2003-04": 1000000, "2004-05": 1100000, "2005-06": 1200000},
                         {r["season"]: r["salary"] for r in history[0]["salary_rows"]})
        self.assertEqual("2005-06", history[0]["end_season"])
        # at another club the ledger's contract is its own agreement, and the fragment ends with its last recorded season
        self.ledger("2004-05", [{"player": "Bench Player", "bbr_id": "bench01", "club": "Third Club", "kind": "existing",
                                 "schedule": {"2004-05": 1100000, "2005-06": 1200000}, "source": "fixture"}])
        history = {c["id"]: c for c in self.profile("Bench Player")["history"]}
        self.assertEqual(2, len(history))
        self.assertEqual(("2003-04", "2004-06-30"), (history[fragment]["end_season"], history[fragment]["expiry_date"]))

    def test_a_later_agreement_ends_an_open_fragment(self):
        self.moves("2004-05", [
            {"id": "t1", "date": "2005-01-10", "kind": "ten_day", "player": "Veteran Player", "bbr_id": "vet01",
             "from": None, "to": "Ten Club", "contract": {"type": "ten_day", "until": "2005-01-20", "salary": "pro-rated minimum"}}])
        p = self.profile("Veteran Player")
        old = next(c for c in p["history"] if c["signed_on"] == "2001-07-20")
        self.assertEqual(("2003-04", "2004-06-30", "expired"), (old["end_season"], old["expiry_date"], old["status"]))
        rows = {r["season"]: r["condition"] for r in old["salary_rows"]}
        self.assertEqual("A later agreement began in 2004-05; not part of this contract.", rows["2004-05"])
        self.assertTrue(rows["2005-06"].endswith("A later agreement began in 2004-05; not part of this contract."))
        ten_day = next(c for c in p["history"] if c["type"] == "10-day contract")
        self.assertIsNone(ten_day["scheduled_subtotal"])                 # no amount recorded: not $0
        self.assertEqual(1, ten_day["scheduled_unknown_count"])


class ArchiveAndPageTests(unittest.TestCase):
    def test_release_names_the_agreement_with_the_entry_signing_date(self):
        records = [{"player": "Jumaine Jones", "event": "signed", "contract_id": "jonesju01-2003-09-30",
                    "recorded_on": "2003-09-30", "contract": {"signed_date": "2003-09-30"}},
                   {"player": "Jumaine Jones", "event": "voided", "contract_id": "jonesju01-2003-09-30",
                    "recorded_on": "2003-10-27", "contract": {"signed_date": "2003-09-30"}},
                   {"player": "Jumaine Jones", "event": "signed", "contract_id": "jonesju01-2005-10-04",
                    "recorded_on": "2005-10-04", "contract": {"signed_date": "2005-10-04"}}]
        self.assertEqual("jonesju01-2005-10-04", signed_record(records, "Jumaine Jones", "2005-10-04")["contract_id"])
        self.assertEqual("jonesju01-2003-09-30", signed_record(records, "Jumaine Jones", "2003-09-30")["contract_id"])
        self.assertEqual("jonesju01-2005-10-04", signed_record(records, "Jumaine Jones")["contract_id"])
        self.assertIsNone(signed_record(records, "Nobody"))

    def test_orphan_contract_pages_are_found(self):
        with tempfile.TemporaryDirectory() as temp:
            player = Path(temp) / "career/Dwyane_Wade"
            folder = player / "Contracts/players"
            folder.mkdir(parents=True)
            for name in ("kept01.md", "kept01.html", "gone01.md", "gone01.html"):
                (folder / name).write_text("x", encoding="utf-8")
            outputs = {folder / "kept01.md": "x", folder / "kept01.html": "x", player / "README.md": "x"}
            self.assertEqual(["gone01.html", "gone01.md"], [p.name for p in orphan_pages(player, outputs)])
            self.assertEqual(["gone01.html", "gone01.md"], [p.name for p in prune_orphan_pages(player, outputs)])
            self.assertEqual(["kept01.html", "kept01.md"], sorted(p.name for p in folder.iterdir()))
            self.assertEqual([], prune_orphan_pages(player, outputs))

    def test_every_page_refresher_prunes_through_the_shared_helper(self):
        for path in ("scripts/refresh_career_views.py", "runtime/season_games.py"):
            self.assertIn("prune_orphan_pages(", (ROOT / path).read_text(encoding="utf-8"), path)


class NavigationTests(unittest.TestCase):
    """A Miami personnel card links the contract page the catalog writes for its player, or carries no contract links."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.player = self.root / "career/Dwyane_Wade"
        team = self.player / "2003-04/00_Team/Team"
        for path, value in (
                ("2003-04/current_state.json", {"current_date": "2003-06-26"}),
                ("professional_identity.json", {"display_name": "Dwyane Wade", "player_id": "dwyane_wade"}),
                ("Stats_and_Awards/League/player_registry.json", {"as_of": "2003-06-26", "players": [
                    {"name": "Dwyane Wade", "registry_id": "wadedw01", "bbr_id": "wadedw01"}]}),
                ("2003-04/00_Team/Team/Roster/roster.json", {"as_of": "2003-06-26", "team": "Miami Heat", "players": [
                    {"name": "Dwyane Wade", "id": "dwyane_wade", "positions": ["SG"]},
                    {"name": "Register Only", "id": "register_only", "bbr_id": None, "positions": ["C"]},
                    {"name": "Bbr Only", "id": "bbr_only", "bbr_id": "bbronly01", "positions": ["PF"]}]})):
            (self.player / path).parent.mkdir(parents=True, exist_ok=True)
            (self.player / path).write_text(json.dumps(value), encoding="utf-8")
        self.cards = {}
        for name, stem in (("Register Only", "register_only"), ("Bbr Only", "bbr_only")):
            card = team / f"Player_Cards/{stem}.md"
            card.parent.mkdir(parents=True, exist_ok=True)
            card.write_text(f"# {name} | Miami Heat Player Profile\n\n**Contract/control:** Unsigned.\n\n## Scouting report\nUnassessed.\n",
                            encoding="utf-8")
            self.cards[name] = card

    def links(self, text):
        import re
        return {Path(href.split("#")[0]).stem for href in re.findall(r"\]\(([^)\s]+)\)", text) if "Contracts/players/" in href}

    def test_register_only_cards_link_the_catalog_id(self):
        ids = {p["id"] for p in build_contract_catalog(self.root, self.player)["players"]}
        outputs = build_contract_navigation(self.root, self.player, pages=ids)
        self.assertEqual({"register_only"}, self.links(outputs[self.cards["Register Only"]]))
        self.assertEqual({"bbronly01"}, self.links(outputs[self.cards["Bbr Only"]]))
        self.assertLessEqual({"register_only", "bbronly01"}, ids)

    def test_a_card_without_a_catalog_page_drops_its_links(self):
        first = build_contract_navigation(self.root, self.player, pages={"register_only", "bbronly01"})
        for card, text in first.items():
            card.write_text(text, encoding="utf-8")
        # a roster snapshot dated after the clock is not on the catalog: the card loses its links, not a link to nothing
        roster = self.player / "2003-04/00_Team/Team/Roster/roster.json"
        data = json.loads(roster.read_text())
        data["as_of"] = "2003-10-24"
        roster.write_text(json.dumps(data), encoding="utf-8")
        ids = {p["id"] for p in build_contract_catalog(self.root, self.player)["players"]}
        self.assertNotIn("register_only", ids)
        text = build_contract_navigation(self.root, self.player, pages=ids)[self.cards["Register Only"]]
        self.assertNotIn(START, text)
        self.assertNotIn(END, text)
        self.assertEqual(self.cards["Register Only"].read_text().split(START)[0].rstrip("\n") +
                         self.cards["Register Only"].read_text().split(END)[1], text)


class PinnedCheckpointNavigationTests(unittest.TestCase):
    def test_every_miami_card_contract_link_opens_a_catalog_page(self):
        import re
        import shutil
        from tests import checkpoint
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for folder in ("library", "career", "foundation", "docs"):
                shutil.copytree(ROOT / folder, root / folder)
            checkpoint.pin(root)
            player = root / "career/Dwyane_Wade"
            roster = player / "2003-04/00_Team/Team/Roster/roster.json"
            for as_of in (None, "2003-10-24"):       # as pinned; then a camp register dated after the pinned clock
                if as_of:
                    data = json.loads(roster.read_text())
                    data["as_of"] = as_of
                    roster.write_text(json.dumps(data), encoding="utf-8")
                ids = {p["id"] for p in build_contract_catalog(root, player)["players"]}
                outputs = build_contract_navigation(root, player, pages=ids)
                cards = [page for page in outputs if page.parent.name == "Player_Cards" and page.name != "README.md"]
                self.assertTrue(cards)
                for page in cards:
                    for href in re.findall(r"\]\(([^)\s]+)\)", outputs[page]):
                        if "Contracts/players/" in href:
                            self.assertTrue(Path(href.split("#")[0]).stem in ids, (as_of, page.name, href))


class LiveCareerTests(unittest.TestCase):
    """The recorded career on 2006-06-20 (the audit's cases)."""

    @classmethod
    def setUpClass(cls):
        state = json.loads((PLAYER / "2005-06/current_state.json").read_text())
        if state.get("current_date", "") < "2006-06-20":
            raise unittest.SkipTest("the career has not reached the audit date")
        cls.catalog = build_contract_catalog(ROOT, PLAYER, "2006-06-20")
        cls.by_id = {p["id"]: p for p in cls.catalog["players"]}

    def test_wade_option_exercised_on_his_agreement(self):
        options = self.by_id["wadedw01"]["current"]["options"]
        self.assertIn(("2006-07", "team_option", 3201202, "2005-10-31", "exercised", "2005-10-31"),
                      [(o["season"], o["type"], o["amount"], o["deadline"], o["outcome"], o["outcome_date"]) for o in options])

    def test_every_applied_option_decision_is_shown(self):
        by_bbr = {(p.get("identity") or {}).get("bbr_id") or p["id"]: p for p in self.catalog["players"]}
        for path in sorted(PLAYER.glob("*/League/option_decisions.json")):
            for d in json.loads(path.read_text())["decisions"]:
                if not d.get("applied") or d["applied"] > "2006-06-20":
                    continue
                p = by_bbr[d["bbr_id"]]
                shown = [o for c in p["history"] for o in c["options"]
                         if o["season"] == d["option_season"] and o["type"] == d["kind"] and o["outcome_date"] == d["applied"]]
                self.assertTrue(shown, d["id"])

    def test_current_agreement_and_status_follow_the_dated_club(self):
        from runtime.club_truth import holder
        from runtime.league_cards import club_on
        registry = json.loads((PLAYER / "Stats_and_Awards/League/player_registry.json").read_text())["players"]
        for row in registry:
            p = self.by_id[row["registry_id"]]
            if row.get("cohort") and p["name"] != "Dwyane Wade":
                self.assertEqual(club_on(row, "2006-06-20", root=ROOT)["club"] or "Free agent", p["team"], p["id"])
            club = holder(row.get("bbr_id"), row["name"], "2006-06-20", ROOT)[0]
            if p["current"] and club:
                self.assertEqual(club, p["current"]["team"], p["id"])
            if not p["current"]:
                self.assertNotIn(p["status"], ("under_contract", "under_rookie_contract", "under_contract_unverified",
                                               "minimum_contract_unverified", "camp_contract"), p["id"])

    def test_audit_cases(self):
        jones = self.by_id["jonesju01"]
        self.assertEqual(("Boston Celtics", "rest-of-season contract"), (jones["current"]["team"], jones["current"]["type"]))
        camp = next(c for c in jones["history"] if c["id"] == "jonesju01-2003-09-30")
        self.assertEqual(("voided", ["2003-04"]), (camp["status"], [r["season"] for r in camp["salary_rows"]]))
        self.assertEqual("Miami Heat", self.by_id["jonesed02"]["current"]["team"])
        self.assertEqual("Utah Jazz", self.by_id["murrala01"]["current"]["team"])
        brown = self.by_id["brownpj01"]["current"]
        self.assertEqual({"2005-06": 8500000, "2006-07": 8500000},
                         {r["season"]: r["salary"] for r in brown["salary_rows"] if r["season"] >= "2005-06"})
        for pid in ("kempsh01", "alstora01", "bellra01", "wallajo01", "ellisla01", "lamplse01"):
            current = self.by_id[pid]["current"]
            self.assertFalse(current and current["team"] == "Miami Heat", pid)
        records = json.loads((PLAYER / "Contracts/contract_records.json").read_text())["records"]
        release = next(r for r in records if r["player"] == "Jumaine Jones" and r["event"] == "released")
        self.assertEqual("jonesju01-2005-10-04", release["contract_id"])


if __name__ == "__main__":
    unittest.main()
