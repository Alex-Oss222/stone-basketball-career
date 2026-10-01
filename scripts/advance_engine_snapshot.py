#!/usr/bin/env python3
"""Compare-and-swap the engine's bound snapshot to this checkout's current_state.json.

Run only from a merged main checkout, after the state change is merged.
Usage: python scripts/advance_engine_snapshot.py "<checkpoint label>"
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.private_client import Client

if len(sys.argv) != 2 or not sys.argv[1].strip():
    raise SystemExit(__doc__)
client = Client()
previous = client.current_snapshot()
if previous == client.snapshot:
    print(f"engine already bound to {client.snapshot}")
else:
    print(f"advanced {previous} -> {client.advance_snapshot(previous, client.snapshot, sys.argv[1])}")
print(client.readiness())
