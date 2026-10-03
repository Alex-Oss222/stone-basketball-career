"""Executed contract evidence survives active-ledger replacement and trades."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from tests import checkpoint

from runtime.contract_archive import ARCHIVE, archive_contract, archive_previous_contract
from runtime import signing
from runtime.rookie_contract import rookie_terms

ROOT = Path(__file__).resolve().parents[1]


class ContractArchiveTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.writer = signing.Writer(self.root)
        self.entry = {"player": "Example Player", "bbr_id": "exampl01", "signed_date": "2003-07-20",
                      "status": "under_contract", "schedule": {"2003-04": 1000000},
                      "guaranteed": {"2003-04": 1000000}, "amount_kind": {"2003-04": "contract_salary"}}

    def archive(self, entry=None, day="2003-07-20", **kwargs):
        return archive_contract(self.writer, entry or self.entry, day, event="signed", source="career/decision.json", **kwargs)

    def test_prior_terms_survive_replacement_without_sharing_mutable_data(self):
        first = self.archive(signing_team="Miami Heat")
        self.writer.commit()
        replacement = deepcopy(self.entry)
        replacement.update(signed_date="2004-07-20", schedule={"2004-05": 2000000})
        archive_previous_contract(self.writer, self.entry, "2004-07-20", source="career/active_contracts.json")
        self.archive(replacement, day="2004-07-20", signing_team="Miami Heat")
        replacement["schedule"]["2004-05"] = 1
        self.entry["schedule"]["2003-04"] = 2
        self.writer.commit()
        records = json.loads((self.root / ARCHIVE).read_text())["records"]
        self.assertEqual(len(records), 3)
        self.assertEqual(records[0]["recorded_on"], "2003-07-20")
        self.assertEqual(records[0]["contract"]["schedule"], {"2003-04": 1000000})
        self.assertEqual(records[1]["event"], "recorded_existing")
        self.assertEqual(records[2]["contract"]["schedule"], {"2004-05": 2000000})
        self.assertNotEqual(records[0]["contract_id"], records[2]["contract_id"])
        self.assertEqual(first["contract"]["schedule"], {"2003-04": 1000000})

    def test_duplicate_execution_does_not_duplicate_or_change_signed_terms(self):
        first = self.archive()
        self.assertIs(self.archive(), first)
        self.assertEqual(len(self.writer.files[ARCHIVE]["records"]), 1)
        changed = deepcopy(self.entry)
        changed["schedule"]["2003-04"] += 1
        with self.assertRaisesRegex(ValueError, "different contract terms"):
            self.archive(changed)
        guarantee = deepcopy(self.entry)
        guarantee["guaranteed"]["2003-04"] = 0
        with self.assertRaisesRegex(ValueError, "different contract terms"):
            self.archive(guarantee)

    def test_offer_unsigned_and_unreached_signing_cannot_become_signed_history(self):
        with self.assertRaisesRegex(ValueError, "before its signing"):
            self.archive(day="2003-07-19")
        unsigned = {"player": "Unsigned Rookie", "status": "draft_rights_unsigned", "schedule": {"2003-04": 2197000}}
        self.assertIsNone(archive_previous_contract(self.writer, unsigned, "2003-06-26", source="career/draft.json"))
        with self.assertRaisesRegex(ValueError, "actual signing date"):
            self.archive(unsigned)
        with self.assertRaisesRegex(ValueError, "executed signings"):
            archive_contract(self.writer, self.entry, "2003-07-20", event="offered", source="career/offer.json")
        self.assertNotIn(ARCHIVE, self.writer.files)

    def test_assignment_preserves_unknown_signing_date_and_original_details(self):
        entry = deepcopy(self.entry)
        entry.pop("signed_date")
        entry["conditions"] = {"2004-05": "Team option; unresolved"}
        entry["amount_precision"] = {"2003-04": "exact"}
        record = archive_contract(self.writer, entry, "2003-08-01", event="assigned", source="career/trade.json",
                                  assignment={"date": "2003-08-01", "from_team": "Example Club", "to_team": "Miami Heat", "source": "career/trade.json"})
        self.assertEqual(record["event"], "assigned")
        self.assertNotIn("signed_date", record["contract"])
        self.assertNotIn("signing_team", record["contract"])
        self.assertEqual(record["contract"]["conditions"], entry["conditions"])
        self.assertEqual(record["contract_id"], "exampl01-baseline-2003-06-26")

    def test_unknown_date_previous_guarantee_amendment_is_preserved(self):
        entry = deepcopy(self.entry)
        entry.pop("signed_date")
        entry["guaranteed"]["2003-04"] = 0
        earlier = archive_previous_contract(self.writer, entry, "2003-07-20", source="career/active_contracts.json")
        amended = deepcopy(entry)
        amended["status"] = "under_contract_guarantee_amended"
        amended["guaranteed"]["2003-04"] = 1000000
        later = archive_previous_contract(self.writer, amended, "2003-07-21", source="career/active_contracts.json")
        self.assertEqual(earlier["contract_id"], later["contract_id"])
        self.assertNotEqual(earlier["record_id"], later["record_id"])
        self.assertEqual(later["event"], "recorded_existing")
        self.assertNotIn("signed_date", later["contract"])
        self.assertEqual(later["contract"]["guaranteed"]["2003-04"], 1000000)
        self.assertEqual(earlier["contract"]["guaranteed"]["2003-04"], 0)

    def test_partial_existing_statuses_remain_available_for_history(self):
        for status in ("free_agent_expiring", "signed", "expired", "retired_salary_on_books"):
            with self.subTest(status=status):
                entry = deepcopy(self.entry)
                entry.pop("signed_date")
                entry["status"] = status
                record = archive_previous_contract(self.writer, entry, "2003-07-21", source="career/active_contracts.json")
                self.assertIsNotNone(record)
                self.assertEqual(record["event"], "recorded_existing")
                self.assertEqual(record["contract"]["status"], status)
                self.assertNotIn("signed_date", record["contract"])

    def copy_career(self, library=False):
        shutil.copytree(ROOT / "career", self.root / "career")
        checkpoint.pin(self.root)                        # signings are exercised from the June 26 checkpoint
        if library:
            shutil.copytree(ROOT / "library", self.root / "library")

    def test_rookie_execution_writes_one_immutable_contract_record(self):
        self.copy_career()
        terms = rookie_terms(5, 120)
        signing.sign_rookie(self.writer, {"entries": []}, terms, "2003-07-20")
        self.writer.commit()
        records = json.loads((self.root / ARCHIVE).read_text())["records"]
        wade = [r for r in records if r["player_id"] == "wadedw01"]
        self.assertEqual(len(wade), 1)
        self.assertEqual(wade[0]["event"], "signed")
        self.assertEqual(wade[0]["contract"]["schedule"], terms["schedule"])
        self.assertEqual(wade[0]["contract"]["signing_team"], "Miami Heat")
        self.assertEqual(wade[0]["contract"]["executed_terms"], terms)

    def test_trade_archives_original_metadata_as_assignment_not_new_signing(self):
        self.copy_career(library=True)
        record = {"trade_id": "archive-fixture", "decision_event": "accepted-archive-fixture",
                  "trade": {"partner": "Denver Nuggets", "miami_out": ["Caron Butler"], "miami_in": ["Nene Hilario"]}}
        source = json.loads((self.root / "library/2003/league/nba_2003_contracts.json").read_text())
        original = next(p for p in source["clubs"]["Denver Nuggets"]["players"] if p["player"] == "Nene Hilario")
        signing.apply_trade(self.writer, record, "2003-07-22")
        self.writer.commit()
        records = json.loads((self.root / ARCHIVE).read_text())["records"]
        self.assertEqual({r["event"] for r in records}, {"assigned"})
        incoming = next(r for r in records if r["player_id"] == "hilarne01")
        self.assertEqual(incoming["contract"]["signed_date"], original["signed_date"])
        self.assertEqual(incoming["contract"]["conditions"], original["conditions"])
        self.assertEqual(incoming["contract"]["amount_precision"], original["amount_precision"])
        self.assertEqual(incoming["contract"]["reported_total"], original["reported_total"])
        self.assertEqual(incoming["assignment"]["to_team"], "Miami Heat")
        outgoing = next(r for r in records if r["player_id"] == "butleca01")
        self.assertEqual(outgoing["assignment"]["to_team"], "Denver Nuggets")
        # A later trade carries the same agreement, without substituting its
        # acquisition date for its original signing date or inventing a new ID.
        second = {"trade_id": "archive-return-fixture", "decision_event": "accepted-archive-return-fixture",
                  "trade": {"partner": "Denver Nuggets", "miami_out": ["Nene Hilario"], "miami_in": []}}
        later_writer = signing.Writer(self.root)
        signing.apply_trade(later_writer, second, "2003-07-23")
        later_writer.commit()
        nene = [r for r in json.loads((self.root / ARCHIVE).read_text())["records"] if r["player_id"] == "hilarne01"]
        self.assertEqual(len(nene), 2)
        self.assertEqual(nene[0]["contract_id"], nene[1]["contract_id"])
        self.assertEqual(nene[1]["contract"]["signed_date"], original["signed_date"])


if __name__ == "__main__":
    unittest.main()
