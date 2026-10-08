#!/usr/bin/env python3
"""Save a dated working event or an explicitly authorized player reply.

  python scripts/player_milestone.py --version
  python scripts/player_milestone.py --record-event event.json --expected-version TOKEN
  python scripts/player_milestone.py --reply reply.json --expected-version TOKEN

Read docs/live_player_milestones.md for the record formats. This command never
runs the engine, advances the clock, signs a contract or applies training gains.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from runtime import consultations
from runtime.milestone_records import PLAYER, load_registry, read, source_path, version
from scripts.refresh_career_views import refresh_career_views as refresh
from runtime.rookie_contract import log_errors, rookie_terms


def dump(path, record):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def context(root, season):
    if not isinstance(season, str) or not re.fullmatch(r"\d{4}-\d{2}", season):
        raise ValueError("season must be YYYY-YY")
    player = root / PLAYER
    state_path = player / season / "current_state.json"
    state = read(state_path)
    if not state:
        raise ValueError("season is not initialized")
    active = max(player.glob("*/current_state.json"), key=lambda p: (read(p)["current_date"], p.parent.name))
    if state_path != active:
        raise ValueError("new events and replies must belong to the active career season, not an archived checkpoint")
    return player, state_path, state


def expect(path, token):
    if not path.is_file() or not token or token != version(path):
        raise ValueError("record changed or is unavailable; reopen the live page and use its current version")


def record_event(root, event, token):
    root = Path(root)
    player, _, state = context(root, event.get("season"))
    path = player / "milestones.json"
    expect(path, token)
    registry = load_registry(root, player)
    if event.get("recorded_on") != state["current_date"]:
        raise ValueError("record the event on the current career date")
    if any(e["id"] == event.get("id") for e in registry["events"]):
        raise ValueError("event ID already recorded; preserve it and use a new follow-up event")
    if event.get("responses"):
        raise ValueError("record a player's reply separately with its own source and version")
    candidate = deepcopy(registry)
    candidate["events"].append(event)
    # Validate the exact candidate before any canonical write.
    load_registry(root, player, data=candidate)
    dump(path, candidate)
    refresh(root)
    return path


def reply(root, response, token):
    root = Path(root)
    player, state_path, state = context(root, response.get("season"))
    if response.get("date") != state["current_date"]:
        raise ValueError("reply must use the current career date")
    source_path(root, response.get("source_ref"))
    if not isinstance(response.get("text"), str) or not response["text"].strip():
        raise ValueError("record the player's actual words or authorized instruction")
    kind, action = response.get("kind"), response.get("action")
    if kind == "rookie_contract":
        if response["season"] != "2003-04":
            raise ValueError("the rookie execution adapter supports the 2003-04 opening only")
        path = player / response["season"] / "01_Free_Agency/Wade_Rookie_Contract/negotiation_log.json"
        expect(path, token)
        log = read(path)
        if log_errors(log, root):
            raise ValueError("invalid existing negotiation log")
        entries = log["entries"]
        if not entries or entries[-1]["party"] != "miami" or any(e["action"] == "sign" or e["date"] > response["date"] for e in entries):
            raise ValueError("no current unanswered club offer")
        if action not in {"accept", "counter", "decline", "request"}:
            raise ValueError("rookie reply must accept, counter, decline or request")
        current = next((e["terms"] for e in reversed(entries) if e["party"] == "miami" and e.get("terms")), None)
        if not current:
            raise ValueError("no dated club terms to answer")
        entry = {"date": response["date"], "party": "wade", "action": action, "note": response["text"], "source_ref": response["source_ref"], "reply_to_version": token}
        if action == "accept":
            entry["terms"] = current
        elif action == "counter":
            percent = response.get("percent_of_scale")
            if type(percent) not in (int, float) or not math.isfinite(percent):
                raise ValueError("a counter needs a finite percent_of_scale")
            entry["terms"] = rookie_terms(log["pick"], percent, root)
        log["entries"].append(entry)
        errors = log_errors(log, root)
        if errors:
            raise ValueError("; ".join(errors))
        dump(path, log)
    elif kind == "consultation":
        cid = response.get("event_id")
        matches = [r for r in consultations.records(root, response["season"]) if r["id"] == cid]
        if len(matches) != 1:
            raise ValueError("consultation ID not found")
        record = matches[0]
        path = consultations.folder(root, response["season"]) / (cid + ".json")
        expect(path, token)
        if record["answer"] is not None or record["date"] > response["date"] or record.get("status") != "asked":
            raise ValueError("consultation is not awaiting an answer")
        if consultations.PENDING_PREFIX + cid not in state.get("pending_player_decisions", []):
            raise ValueError("consultation is not in the live pending list")
        if action not in {"approve", "object"}:
            raise ValueError("consultation reply must approve or object")
        record.update(answer=action, answered=response["date"], status="closed", note=response["text"], source_ref=response["source_ref"], reply_to_version=token)
        consultations.close(root, state, cid)
        dump(path, record)
        dump(state_path, state)
        page = path.parent / consultations.page_name(record)
        with page.open("a", encoding="utf-8") as f:
            f.write(f"\n## Recorded player answer\n\n{response['date']}: **{action}** — {response['text']}\n")
    elif kind == "extension":
        # Wade's answer to a contract extension offer (runtime/extensions.py). It never signs anything: the next run of
        # scripts/extension_day.py applies the answer (accept: the extension is signed; decline: no contract changes).
        from runtime import extensions
        oid = response.get("event_id")
        if not isinstance(oid, str) or not oid:
            raise ValueError("extension offer ID not found")
        path = extensions.offer_path(root, response["season"], oid)
        expect(path, token)
        record = read(path)
        if not record or record.get("id") != oid:
            raise ValueError("extension offer ID not found")
        if record.get("status") != "offered" or record.get("answer") is not None or record["date"] > response["date"]:
            raise ValueError("extension offer is not awaiting an answer")
        if extensions.PENDING_PREFIX + oid not in state.get("pending_player_decisions", []):
            raise ValueError("extension offer is not in the live pending list")
        if action not in {"accept", "decline"}:
            raise ValueError("extension reply must accept or decline")
        record.update(answer=action, answered=response["date"], status="closed", note=response["text"], source_ref=response["source_ref"], reply_to_version=token)
        extensions.close(state, oid)
        dump(path, record)
        dump(state_path, state)
        page = path.parent / extensions.page_name(record)
        with page.open("a", encoding="utf-8") as f:
            f.write(f"\n## Recorded player answer\n\n{response['date']}: **{action}**: {response['text']}\n\n"
                    f"The extension step applies it on its next run (`scripts/extension_day.py --write {response['date']}`).\n")
    elif kind == "working_record":
        path = player / "milestones.json"
        expect(path, token)
        registry = load_registry(root, player)
        event = next((e for e in registry["events"] if e["id"] == response.get("event_id") and e["season"] == response["season"]), None)
        if not event or event["status"] == "closed" or event["owner"] != "player" or not event["needs_response"] or event.get("responses"):
            raise ValueError("working record is not awaiting a player reply; open a new follow-up for a later review")
        if any(e.get("supersedes") == event["id"] for e in registry["events"]):
            raise ValueError("working record has a newer follow-up; answer that event instead")
        if action != "record":
            raise ValueError("a working-record reply records a preference; it cannot execute a transaction or staff decision")
        event.setdefault("responses", []).append({"date": response["date"], "text": response["text"], "source_ref": response["source_ref"], "reply_to_version": token})
        dump(path, registry)
    else:
        raise ValueError("unknown reply kind")
    refresh(root)
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--version", action="store_true", help="print the working registry version")
    group.add_argument("--record-event", type=Path)
    group.add_argument("--reply", type=Path)
    parser.add_argument("--expected-version")
    args = parser.parse_args(argv)
    try:
        if args.version:
            print(version(ROOT / PLAYER / "milestones.json"))
            return 0
        source = args.record_event or args.reply
        record = json.loads(source.read_text(encoding="utf-8"))
        result = record_event(ROOT, record, args.expected_version) if args.record_event else reply(ROOT, record, args.expected_version)
        print(f"Saved {result.relative_to(ROOT)}; live pages refreshed. Career date unchanged.")
        return 0
    except (ValueError, KeyError, TypeError, OSError) as exc:
        parser.exit(1, f"Milestone command failed: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
