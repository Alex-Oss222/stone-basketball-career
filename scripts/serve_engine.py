#!/usr/bin/env python3
"""Railway entry point for the private engine-state service.

Secrets and storage stay outside the repository:
  ENGINE_API_TOKEN       bearer token (Railway variable, >= 32 characters)
  ENGINE_DATABASE_PATH   SQLite file on the Railway volume (default /data/engine.sqlite3)
  PORT                   provided by Railway
"""
from http.server import ThreadingHTTPServer
from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.private_service import Store, handler

snapshot = os.getenv("ENGINE_SNAPSHOT") or (ROOT / "engine_snapshot.txt").read_text().strip()
store = Store(os.getenv("ENGINE_DATABASE_PATH", "/data/engine.sqlite3"))
locked_until = None
if store.initialize(snapshot):
    locked_until = snapshot
    print("engine started LOCKED: stored snapshot differs from this image; "
          "run scripts/advance_engine_snapshot.py from merged main", flush=True)
port = int(os.getenv("PORT", "8765"))
print(f"basketball engine-state listening on {port}", flush=True)
ThreadingHTTPServer((os.getenv("ENGINE_BIND_HOST", "0.0.0.0"), port),
                    handler(store, os.environ["ENGINE_API_TOKEN"], locked_until)).serve_forever()
