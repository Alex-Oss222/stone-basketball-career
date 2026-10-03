#!/usr/bin/env python3
"""Collect played games and drawn decisions from the Railway engine into the repository.

Run by the results workflow after every push to the branch Railway tracks, and on
a schedule. For every `*.request.json` (Miami's `Game_N.request.json` next to its
game note, and the league slate's `<game_id>.request.json` under
`Stats_and_Awards/League/<season>/Games/`) and every `*.decision.json` that has
no result file yet, it asks the public engine endpoints and writes:

  <name>.result.json            next to the request (the full result JSON)
  <name>.decision.result.json   next to the decision request

A result file is the engine's answer as served; writing it into the game note
or the phase note is still the canonical step (AGENTS.md, Game engine). The
collector never edits a request and never writes a result the engine has not
served. It waits for the engine to report the new kernel after a deploy, then
polls until every pending event is served or the time limit passes.

  ENGINE_URL     public base URL of the engine (default: the Railway domain)
  COLLECT_WAIT   seconds to keep polling for pending events (default 900)
"""
import json
import os
from pathlib import Path
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from runtime import KERNEL_VERSION
from runtime.decisions import find_decisions
from runtime.game_requests import find_requests
from scripts.refresh_career_views import refresh_career_views

URL = os.getenv("ENGINE_URL", "https://stone-basketball-career-production.up.railway.app").rstrip("/")


def fetch(path):
    try:
        with urlopen(f"{URL}{path}", timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code == 404:
            return None
        raise
    except (URLError, TimeoutError, ValueError):
        return None


def pending():
    games = [(p, p.with_name(p.name.replace(".request.json", ".result.json")),
              json.loads(p.read_text(encoding="utf-8"))["event_id"], "game") for p in find_requests(ROOT)]
    decisions = [(p, p.with_name(p.name.replace(".decision.json", ".decision.result.json")),
                  json.loads(p.read_text(encoding="utf-8"))["event_id"], "decision") for p in find_decisions(ROOT)]
    return [row for row in games + decisions if not row[1].exists()]


def main():
    todo = pending()
    if not todo:
        print("nothing pending")
        return
    deadline = time.time() + int(os.getenv("COLLECT_WAIT", "900"))
    written = []
    while todo and time.time() < deadline:
        health = fetch("/health")
        if not health or health.get("kernel") != KERNEL_VERSION:
            print(f"engine not ready (kernel {health and health.get('kernel')!r}, want {KERNEL_VERSION!r}); waiting")
            time.sleep(30)
            continue
        listing = fetch("/games") or {}
        statuses = listing.get("games", {})
        remaining = []
        for request, out, event_id, kind in todo:
            entry = statuses.get(event_id)
            if entry and entry.get("status") == "error":
                print(f"ERROR  {event_id}: {entry.get('error')}")
                continue
            result = fetch(f"/decisions/{event_id}" if kind == "decision" else f"/games/{event_id}")
            if result is None:
                remaining.append((request, out, event_id, kind))
                continue
            out.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8")
            written.append(out.relative_to(ROOT))
            print(f"{kind:<8} {event_id} -> {out.relative_to(ROOT)}")
        todo = remaining
        if todo:
            time.sleep(30)
    for request, out, event_id, kind in todo:
        print(f"PENDING {event_id} (not served yet)")
    print(f"{len(written)} result file(s) written; {len(todo)} still pending")
    if written:
        refreshed = refresh_career_views(ROOT)
        print(f"Updated {len(refreshed)} detailed career views from closed career evidence. Raw sidecars remain unclosed until their owning notes are updated.")


if __name__ == "__main__":
    main()
