#!/usr/bin/env python3
"""Audit the engine's published journal against the committed career (roadmap 18b).

    python scripts/audit_journal.py            check; exit 1 on any problem
    python scripts/audit_journal.py --publish  also record the engine's seed hash the first time (foundation/engine_seed.json)

Checks:
- every journaled event has a committed request: a game `*.request.json` or a decision `*.decision.json` with that
  event id, or an engine-internal draw (development swings, absence spells) whose id the engine derives itself;
- the engine's career-seed SHA-256 equals the hash committed in `foundation/engine_seed.json` once published, so the
  seed cannot be swapped to re-roll later events (the protection runs from the day the hash is published).
Reads the public `GET /journal` route; no token is needed and none is printed.
"""
import argparse
import json
from pathlib import Path
import sys
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.collect_results import URL                                  # noqa: E402
SEED_RECORD = ROOT / "foundation/engine_seed.json"
INTERNAL = ("development:", "absence-spells:")


def committed_ids(root=ROOT):
    ids = set()
    for path in (Path(root) / "career").rglob("*.request.json"):
        ids.add(json.loads(path.read_text(encoding="utf-8")).get("event_id"))
    for path in (Path(root) / "career").rglob("*.decision.json"):
        ids.add(json.loads(path.read_text(encoding="utf-8")).get("event_id"))
    return ids


def audit(journal, root=ROOT):
    problems = []
    ids = committed_ids(root)
    for e in journal["events"]:
        if e["event_id"] not in ids and not e["event_id"].startswith(INTERNAL):
            problems.append(f"journaled event {e['event_id']} has no committed request (abandoned or uncommitted draw)")
    if SEED_RECORD.is_file():
        published = json.loads(SEED_RECORD.read_text(encoding="utf-8"))["seed_sha256"]
        if published != journal["seed_sha256"]:
            problems.append("the engine's career seed differs from the published hash")
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--url", default=URL)
    args = parser.parse_args()
    with urlopen(f"{args.url}/journal", timeout=60) as response:
        journal = json.loads(response.read().decode("utf-8"))
    if args.publish and not SEED_RECORD.is_file():
        from datetime import date
        SEED_RECORD.write_text(json.dumps({"schema_version": 1, "seed_sha256": journal["seed_sha256"],
                                           "published_on": date.today().isoformat(),
                                           "purpose": "SHA-256 of the engine's career seed (roadmap 18b). Every later game and "
                                                      "draw must come from this seed; scripts/audit_journal.py compares it."},
                                          indent=1) + "\n", encoding="utf-8")
        print(f"published the seed hash {journal['seed_sha256'][:12]}...")
    problems = audit(journal)
    print(f"{len(journal['events'])} journaled events; " + ("no problems" if not problems else f"{len(problems)} problem(s)"))
    for p in problems[:20]:
        print("  " + p)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
