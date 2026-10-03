"""Preserve executed contract evidence when the active ledger changes.

These records describe signings and assignments that the transaction writer has
already executed. They never represent an offer or authorize a transaction.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import hashlib
import json
from pathlib import Path
import re

ARCHIVE = Path("career/Dwyane_Wade/Contracts/contract_records.json")
REGISTRY = Path("career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json")


def _player_id(writer, entry, player_id=None):
    identity = None
    if (writer.root / REGISTRY).is_file():
        registry = json.loads((writer.root / REGISTRY).read_text(encoding="utf-8"))
        identity = next((p["registry_id"] for p in registry["players"] if p["name"] == entry["player"]), None)
    if not identity:
        for path in sorted((writer.root / "career/Dwyane_Wade").glob("*/00_Team/Team/Roster/roster.json")):
            roster = writer.files.get(path.relative_to(writer.root)) or json.loads(path.read_text(encoding="utf-8"))
            row = next((p for p in roster["players"] if p["name"] == entry["player"]), None)
            if row:
                identity = row.get("bbr_id") or row.get("registry_id") or row.get("id")
                if identity:
                    break
    identity = identity or player_id or entry.get("bbr_id") or entry.get("registry_id")
    if not identity:
        identity = re.sub(r"[^a-z0-9]+", "_", entry["player"].lower()).strip("_")
    return identity


def archive_contract(writer, entry, day, *, event, source, player_id=None,
                     signing_team=None, assignment=None, executed_terms=None):
    """Append a dated deep snapshot, retaining the original contract on a trade.

    Unknown signing dates remain unknown. An ``assigned`` record only describes
    a holder change; the catalog must match it to existing contract evidence.
    Duplicate execution of the same event does not duplicate its history row.
    """
    date.fromisoformat(day)
    if event not in {"signed", "assigned", "recorded_existing"}:
        raise ValueError("The transaction archive accepts executed signings, assignments and existing contract snapshots only")
    signed = entry.get("signed_date")
    if signed:
        date.fromisoformat(signed)
        if signed > day:
            raise ValueError("A contract cannot be archived before its signing date")
    if event == "signed" and not signed:
        raise ValueError("A signed contract archive requires its actual signing date")
    if not source or not isinstance(entry.get("schedule"), dict):
        raise ValueError("Contract archive requires a source and the recorded schedule")
    if event == "assigned" and (not assignment or assignment.get("date") != day):
        raise ValueError("An assignment requires its reached date and holder change")
    identity = _player_id(writer, entry, player_id)
    contract_id = entry.get("contract_id") or f"{identity}-{signed or 'baseline-2003-06-26'}"
    if ARCHIVE in writer.files:
        archive = writer.files[ARCHIVE]
    elif (writer.root / ARCHIVE).is_file():
        archive = writer.load(ARCHIVE)
    else:
        archive = {"schema_version": 1, "records": []}
        writer.files[ARCHIVE] = archive
    contract = deepcopy(entry)
    if signing_team:
        contract["signing_team"] = signing_team
    if executed_terms is not None:
        contract["executed_terms"] = deepcopy(executed_terms)
    if event == "signed":
        suffix = "signed"
    elif event == "assigned":
        suffix = f"assigned-{day}-{hashlib.sha256(source.encode()).hexdigest()[:12]}"
    else:
        fingerprint = hashlib.sha256(json.dumps(contract, sort_keys=True).encode()).hexdigest()[:12]
        suffix = f"recorded-existing-{day}-{fingerprint}"
    record_id = f"{contract_id}-{suffix}"
    existing = next((record for record in archive["records"] if record["record_id"] == record_id), None)
    if existing:
        if existing["contract"] != contract:
            raise ValueError("An executed archive event already exists with different contract terms")
        return existing
    record = {"record_id": record_id, "recorded_on": day, "player_id": identity, "player": entry["player"],
              "contract_id": contract_id, "event": event, "source": source, "contract": contract}
    if assignment:
        record["assignment"] = deepcopy(assignment)
    archive["records"].append(record)
    return record


def archive_previous_contract(writer, entry, day, *, source, player_id=None):
    """Preserve an established executed entry before its active row is replaced."""
    if not entry or "draft" in entry.get("status", ""):
        return None
    kinds = set(entry.get("amount_kind", {}).values())
    if kinds and kinds <= {"draft_hold", "unsigned_rights"}:
        return None
    if not entry.get("signed_date") and entry.get("status") not in {
            "under_contract", "under_contract_guarantee_amended", "under_rookie_contract", "camp_contract",
            "team_option_pending", "player_option_pending", "team_option_exercised", "player_option_exercised",
            "team_option_declined", "player_option_declined", "expiring_contract", "re_signed", "signed_free_agent",
            "free_agent_expiring", "signed", "expired", "retired_salary_on_books",
            "traded", "released", "signed_elsewhere", "renounced"}:
        return None
    return archive_contract(writer, entry, day, event="recorded_existing", source=source, player_id=player_id,
                            signing_team=entry.get("signing_team"))
