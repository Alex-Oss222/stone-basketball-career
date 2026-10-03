"""Contract reporting must preserve executed evidence and knowledge boundaries."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from runtime.player_contracts import build_contract_catalog, contract_payload

ROOT = Path(__file__).resolve().parents[1]


class ContractCatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.player = self.root / "career/Dwyane_Wade"
        self.season = "career/Dwyane_Wade/2003-04"
        self.sheet = self.season + "/00_Team/Finances/contract_schedules.json"
        self.archive = "career/Dwyane_Wade/Contracts/contract_records.json"
        self.write(self.season + "/current_state.json", {"current_date": "2003-06-26"})
        self.write("career/Dwyane_Wade/professional_identity.json", {
            "display_name": "Dwyane Wade", "player_id": "dwyane_wade", "aliases": ["wadedw01"]})
        self.write("career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json", {
            "as_of": "2003-06-26", "players": [
                {"name": "Dwyane Wade", "registry_id": "wadedw01", "bbr_id": "wadedw01", "team_name": "Miami Heat"},
                {"name": "Veteran Player", "registry_id": "vet01", "bbr_id": "vet01", "team_name": "Other Club"},
                {"name": "Unknown Player", "registry_id": "unknown01", "team_name": "Other Club"}]})
        self.vet = {"player": "Veteran Player", "bbr_id": "vet01", "status": "under_contract",
                    "signed_date": "2001-07-20", "original_term_seasons": 5,
                    "schedule": {"2003-04": 3000000, "2004-05": None, "2005-06": 4000000},
                    "amount_kind": {"2003-04": "contract_salary", "2004-05": "contract_salary", "2005-06": "team_option"},
                    "reported_total": {"amount": 14000000, "precision": "reported"}}
        self.league([self.vet])
        self.write(self.sheet, {"as_of": "2003-06-26", "team": "Miami Heat", "players": [{
            "player": "Dwyane Wade", "status": "unsigned_first_round_draft_rights",
            "current_cap_hold": 2197000, "schedule": {"2003-04": 2197000},
            "amount_kind": {"2003-04": "draft_hold"}}]})

    def write(self, path, value):
        file = self.root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(json.dumps(value), encoding="utf-8")

    def league(self, entries, as_of="2003-06-26"):
        self.write("library/2003/league/nba_2003_contracts.json",
                   {"as_of": as_of, "clubs": {"Other Club": {"players": entries}}})

    def clock(self, value):
        self.write(self.season + "/current_state.json", {"current_date": value})

    def catalog(self):
        return build_contract_catalog(self.root, self.player)

    def profile(self, name="Veteran Player"):
        return next(p for p in self.catalog()["players"] if p["name"] == name)

    def test_draft_hold_not_salary_or_contract(self):
        p = self.profile("Dwyane Wade")
        self.assertIsNone(p["current"])
        self.assertEqual([], p["history"])
        self.assertEqual(2197000, p["control"]["current_cap_hold"])

    def test_partial_schedule_not_original_total_or_aav(self):
        c = self.profile()["current"]
        self.assertEqual(7000000, c["scheduled_subtotal"])
        self.assertEqual(1, c["scheduled_unknown_count"])
        self.assertEqual(14000000, c["reported_total"]["amount"])
        self.assertIsNone(c["original_aav"])
        self.assertIsNone(c["end_season"])

    def test_missing_terms_are_not_zero_or_false(self):
        c = self.profile()["current"]
        self.assertIsNone(c["salary_rows"][0]["cap_hit"])
        self.assertIsNone(c["salary_rows"][0]["guaranteed"])
        self.assertIsNone(c["terms"]["no_trade_clause"])

    def test_explicit_zero_guarantee_retained(self):
        self.vet["guaranteed"] = {"2003-04": 0}
        self.league([self.vet])
        self.assertEqual(0, self.profile()["current"]["salary_rows"][0]["guaranteed"])

    def test_unverified_salary_is_not_current_signed_contract(self):
        self.vet["status"] = "under_contract_unverified"
        self.league([self.vet])
        p = self.profile()
        self.assertIsNone(p["current"])
        self.assertEqual([], p["history"])
        self.assertEqual(3000000, p["control"]["schedule"]["2003-04"])

    def test_future_signing_and_future_snapshot_excluded(self):
        self.vet["signed_date"] = "2003-07-02"
        self.league([self.vet])
        self.assertIsNone(self.profile()["current"])
        self.vet["signed_date"] = "2001-07-20"
        self.league([self.vet], as_of="2003-07-02")
        self.assertIsNone(self.profile()["current"])

    def test_historical_protagonist_contract_never_loaded(self):
        historical = deepcopy(self.vet)
        historical.update(player="Dwyane Wade", bbr_id="wadedw01", signed_date="2002-07-20")
        self.league([historical])
        self.assertEqual([], self.profile("Dwyane Wade")["history"])

    def test_cap_gate_and_cap_hit_distinct_from_salary(self):
        self.write(self.season + "/00_Team/Finances/league_cap_history.json", {"seasons": [
            {"season": "2003-04", "salary_cap": 43840000, "published_date": "2003-07-15"},
            {"season": "2004-05", "salary_cap": 43870000, "published_date": None}]})
        self.vet["cap_hit"] = {"2003-04": 2000000}
        self.league([self.vet])
        self.assertIsNone(self.profile()["current"]["salary_rows"][0]["salary_cap"])
        self.clock("2003-07-15")
        row = self.profile()["current"]["salary_rows"][0]
        self.assertEqual(43840000, row["salary_cap"])
        self.assertAlmostEqual(4.562, row["cap_percent"], places=3)
        self.assertNotEqual(row["salary_cap_percent"], row["cap_percent"])
        self.assertIsNone(self.profile()["current"]["salary_rows"][1]["salary_cap"])

    def test_option_outcome_dated_separately_from_deadline(self):
        self.vet["options"] = [{"season": "2005-06", "type": "team_option", "amount": 4000000,
            "deadline": "2004-10-31", "outcome": "exercised", "outcome_date": "2004-10-20"}]
        self.league([self.vet])
        option = self.profile()["current"]["options"][0]
        self.assertEqual("2004-10-31", option["deadline"])
        self.assertIsNone(option["outcome"])

    def test_offer_and_acceptance_not_signing(self):
        log = self.season + "/01_Free_Agency/Wade_Rookie_Contract/negotiation_log.json"
        self.write(log, {"entries": [{"date": "2003-06-26", "action": "offer", "party": "miami"},
                                   {"date": "2003-06-26", "action": "accept", "party": "wade"}]})
        p = self.profile("Dwyane Wade")
        self.assertIsNone(p["current"])
        self.assertEqual(2, len(p["control"]["unsigned_responses"]))

    def test_actual_rookie_signing_does_not_infer_guarantees(self):
        self.clock("2003-07-20")
        self.write(self.season + "/01_Free_Agency/Wade_Rookie_Contract/negotiation_log.json", {
            "entries": [{"date": "2003-07-20", "action": "sign", "terms": {
                "schedule": {"2003-04": 2636400}, "amount_kind": {"2003-04": "contract_salary"}}}]})
        c = self.profile("Dwyane Wade")["current"]
        self.assertEqual(2636400, c["salary_rows"][0]["salary"])
        self.assertIsNone(c["salary_rows"][0]["guaranteed"])

    def test_trade_changes_holder_not_contract_count_or_sign_date(self):
        self.clock("2003-07-20")
        incoming = {k: deepcopy(self.vet[k]) for k in ("player", "bbr_id", "schedule", "amount_kind")}
        incoming.update(status="under_contract", acquired={"date": "2003-07-20", "from": "Other Club"})
        self.write(self.sheet, {"as_of": "2003-07-20", "team": "Miami Heat", "players": [incoming]})
        self.write(self.season + "/00_Team/Transactions/Trades/trade1.json", {
            "trade_id": "trade1", "status": "completed", "applied": "2003-07-20",
            "trade": {"partner": "Other Club", "miami_in": ["Veteran Player"], "miami_out": []}})
        p = self.profile()
        self.assertEqual(1, len(p["history"]))
        self.assertEqual("2001-07-20", p["current"]["signed_on"])
        self.assertEqual("Miami Heat", p["current"]["team"])
        self.assertEqual(1, len(p["current"]["assignment_history"]))

    def test_declined_or_future_trade_does_not_assign(self):
        for status, applied in [("declined", None), ("completed", "2003-07-20")]:
            self.write(self.season + "/00_Team/Transactions/Trades/trade1.json", {
                "trade_id": "trade1", "status": status, "applied": applied,
                "trade": {"partner": "Other Club", "miami_in": ["Veteran Player"]}})
            self.assertEqual([], self.profile()["current"]["assignment_history"])
            self.assertEqual("Other Club", self.profile()["team"])

    def test_archive_preserves_two_actual_signings_when_active_row_replaced(self):
        self.clock("2004-07-20")
        new = deepcopy(self.vet)
        new.update(signed_date="2004-07-20", schedule={"2004-05": 8000000},
                   amount_kind={"2004-05": "contract_salary"}, status="signed", full_original_schedule=True,
                   original_term_seasons=1, reported_total={"amount": 8000000})
        self.write(self.sheet, {"as_of": "2004-07-20", "team": "Miami Heat", "players": [new]})
        self.write(self.archive, {"schema_version": 1, "records": [
            {"record_id": "old", "recorded_on": "2004-07-20", "player_id": "vet01",
             "contract_id": "vet01-2001-07-20", "event": "signed", "contract": self.vet},
            {"record_id": "new", "recorded_on": "2004-07-20", "player_id": "vet01",
             "contract_id": "vet01-2004-07-20", "event": "signed", "contract": new}]})
        p = self.profile()
        self.assertEqual(2, len(p["history"]))
        self.assertEqual("2004-07-20", p["current"]["signed_on"])
        self.assertEqual(8000000, p["current"]["original_aav"])

    def test_future_archive_and_orphan_amendment_ignored(self):
        new = deepcopy(self.vet)
        new.update(player="Unknown Player", signed_date="2003-06-01")
        self.write(self.archive, {"records": [
            {"record_id": "future", "recorded_on": "2003-07-20", "player_id": "unknown01",
             "contract_id": "future", "event": "signed", "contract": new},
            {"record_id": "orphan", "recorded_on": "2003-06-26", "player_id": "unknown01",
             "contract_id": "orphan", "event": "amended", "contract": new}]})
        self.assertEqual([], self.profile("Unknown Player")["history"])

    def test_alias_resolves_alternate_protagonist_once(self):
        row = {"signed_date": "2003-06-26", "schedule": {"2003-04": 2000000},
               "amount_kind": {"2003-04": "contract_salary"}}
        self.write(self.archive, {"records": [{"record_id": "signed", "recorded_on": "2003-06-26",
            "player_id": "dwyane_wade", "contract_id": "wade1", "event": "signed", "contract": row}]})
        p = self.profile("Dwyane Wade")
        self.assertEqual("wadedw01", p["id"])
        self.assertEqual(1, len(p["history"]))

    def test_payload_sources_are_page_relative_and_serializable(self):
        p = self.profile()
        payload = contract_payload(p, page=self.player / "Contracts/players/vet01.html", root=self.root)
        json.dumps(payload)
        for source in payload["sources"]:
            if not source["href"].startswith("http"):
                self.assertTrue((self.player / "Contracts/players" / source["href"]).resolve().is_file())
        self.assertIn("Not recorded", json.dumps(payload))

    def test_clock_cannot_advance(self):
        with self.assertRaises(ValueError):
            build_contract_catalog(self.root, self.player, "2003-07-20")

    def test_old_sign_archive_does_not_restore_released_contract(self):
        self.clock("2003-08-01")
        latest = deepcopy(self.vet)
        latest.update(status="released", guaranteed={"2003-04": 1000000})
        self.write(self.sheet, {"as_of": "2003-08-01", "team": "Miami Heat", "players": [latest]})
        self.write(self.archive, {"records": [{"record_id": "old", "recorded_on": "2003-07-20",
            "player_id": "vet01", "contract_id": "vet01-2001-07-20", "event": "signed", "contract": self.vet}]})
        p = self.profile()
        self.assertIsNone(p["current"])
        self.assertEqual("released", p["status"])
        self.assertEqual(1000000, p["history"][0]["salary_rows"][0]["guaranteed"])

    def test_future_extension_does_not_replace_active_contract(self):
        self.clock("2003-08-01")
        extension = deepcopy(self.vet)
        extension.update(signed_date="2003-07-20", start_season="2006-07", schedule={"2006-07": 10000000})
        self.write(self.archive, {"records": [{"record_id": "extension", "recorded_on": "2003-07-20",
            "player_id": "vet01", "contract_id": "extension1", "event": "signed", "contract": extension}]})
        p = self.profile()
        self.assertEqual(2, len(p["history"]))
        self.assertEqual("2001-07-20", p["current"]["signed_on"])

    def test_declined_future_option_keeps_active_base_season(self):
        self.clock("2004-10-20")
        self.vet.update(status="team_option_declined", option_decision_date="2004-10-20")
        self.write(self.sheet, {"as_of": "2004-10-20", "team": "Miami Heat", "players": [self.vet]})
        p = self.profile()
        self.assertIsNotNone(p["current"])
        self.assertEqual("declined", p["current"]["options"][0]["outcome"])
        self.assertEqual("2004-10-20", p["current"]["options"][0]["outcome_date"])

    def test_option_outcome_date_not_inferred_from_snapshot(self):
        self.vet["status"] = "team_option_exercised"
        self.league([self.vet])
        option = self.profile()["current"]["options"][0]
        self.assertEqual("exercised", option["outcome"])
        self.assertIsNone(option["outcome_date"])
        self.assertEqual("2003-06-26", option["evidence_as_of"])

    def test_future_cycle_expiry_uses_own_season(self):
        self.clock("2005-06-26")
        self.vet.update(status="free_agent_expiring", prior_season_salary={"season": "2004-05", "amount": 3000000})
        self.league([self.vet], as_of="2005-06-26")
        c = self.profile()["current"]
        self.assertIsNotNone(c)
        self.assertEqual("2005-06-30", c["expiry_date"])
        self.clock("2005-07-01")
        self.assertIsNone(self.profile()["current"])

    def test_archive_assignment_self_sufficient_and_deduped_with_trade(self):
        self.clock("2003-07-20")
        self.write(self.archive, {"records": [{"record_id": "assignment", "recorded_on": "2003-07-20",
            "player_id": "vet01", "contract_id": "vet01-2001-07-20", "event": "assigned", "contract": self.vet,
            "assignment": {"date": "2003-07-20", "from_team": "Other Club", "to_team": "Miami Heat"}}]})
        p = self.profile()
        self.assertEqual(1, len(p["history"]))
        self.assertEqual("Miami Heat", p["team"])
        self.assertEqual(1, len(p["current"]["assignment_history"]))
        self.write(self.season + "/00_Team/Transactions/Trades/trade1.json", {
            "trade_id": "trade1", "status": "completed", "applied": "2003-07-20",
            "trade": {"partner": "Other Club", "miami_in": ["Veteran Player"]}})
        self.assertEqual(1, len(self.profile()["current"]["assignment_history"]))

    def test_unknown_signing_date_existing_snapshot_preserves_amendment(self):
        self.vet.pop("signed_date")
        self.league([self.vet])
        snapshot = deepcopy(self.vet)
        snapshot["guaranteed"] = {"2003-04": 500000}
        self.write(self.archive, {"records": [{"record_id": "existing", "recorded_on": "2003-06-26",
            "player_id": "vet01", "contract_id": "vet01-baseline-2003-06-26",
            "event": "recorded_existing", "contract": snapshot}]})
        p = self.profile()
        self.assertEqual(1, len(p["history"]))
        self.assertIsNone(p["current"]["signed_on"])
        self.assertEqual(500000, p["current"]["salary_rows"][0]["guaranteed"])

    def test_executed_camp_contract_is_recorded_without_assumed_guarantee(self):
        self.clock("2003-10-01")
        camp = {"player": "Unknown Player", "status": "camp_contract", "signed_date": "2003-10-01",
                "schedule": {"2003-04": 366931}, "amount_kind": {"2003-04": "contract_salary"},
                "guaranteed": {"2003-04": 0}, "guarantee_date": "2004-01-10"}
        self.write(self.archive, {"records": [{"record_id": "camp", "recorded_on": "2003-10-01",
            "player_id": "unknown01", "contract_id": "camp1", "event": "signed", "contract": camp}]})
        c = self.profile("Unknown Player")["current"]
        self.assertIsNotNone(c)
        self.assertEqual(0, c["salary_rows"][0]["guaranteed"])
        self.assertEqual("2004-01-10", c["terms"]["guarantee_date"])

    def test_older_trade_does_not_override_later_signing_club(self):
        self.clock("2004-07-20")
        new = deepcopy(self.vet)
        new.update(signed_date="2004-07-20", signing_team="New Club",
                   schedule={"2004-05": 8000000}, amount_kind={"2004-05": "contract_salary"})
        self.write(self.archive, {"records": [{"record_id": "new", "recorded_on": "2004-07-20",
            "player_id": "vet01", "contract_id": "new1", "event": "signed", "contract": new}]})
        self.write(self.season + "/00_Team/Transactions/Trades/trade1.json", {
            "trade_id": "trade1", "status": "completed", "applied": "2003-07-20",
            "trade": {"partner": "Other Club", "miami_in": ["Veteran Player"]}})
        p = self.profile()
        self.assertEqual("New Club", p["team"])
        self.assertEqual("New Club", p["current"]["team"])
        self.assertEqual(1, len(p["history"][1]["assignment_history"]))


class LiveContractCatalogTests(unittest.TestCase):
    def test_all_registry_and_personnel_players_with_no_career_writes(self):
        player = ROOT / "career/Dwyane_Wade"
        before = {p: p.read_bytes() for p in player.rglob("*.json")}
        catalog = build_contract_catalog(ROOT, player)
        self.assertEqual(410, len(catalog["players"]))
        self.assertEqual("wadedw01", catalog["default_player_id"])
        wade = next(p for p in catalog["players"] if p["id"] == "wadedw01")
        log = player / "2003-04/01_Free_Agency/Wade_Rookie_Contract/negotiation_log.json"
        signed = log.is_file() and any(e["action"] == "sign" for e in json.loads(log.read_text())["entries"])
        if signed:                                       # the live clock is past his signing: one executed agreement
            self.assertEqual(1, len(wade["history"]))
            self.assertEqual("rookie_scale", wade["current"]["type"])
        else:
            self.assertEqual([], wade["history"])
            self.assertIsNone(wade["current"])
        for p in catalog["players"]:
            json.dumps(contract_payload(p, root=ROOT, page=player / "Contracts/players" / (p["id"] + ".html")))
        self.assertEqual(before, {p: p.read_bytes() for p in player.rglob("*.json")})


if __name__ == "__main__":
    unittest.main()
