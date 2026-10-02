#!/usr/bin/env python3
"""Railway entry point: play any new game requests, then serve results.

  ENGINE_API_TOKEN       bearer token for the authenticated endpoints (>= 32 characters)
  ENGINE_DATABASE_PATH   SQLite file on the Railway volume (default /data/engine.sqlite3)
  PORT                   provided by Railway
"""
from http.server import ThreadingHTTPServer
from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.private_service import Store, handler, play_requests

store = Store(os.getenv("ENGINE_DATABASE_PATH", "/data/engine.sqlite3"))
store.initialize()
games = play_requests(store, ROOT)
for key, entry in games.items():
    print(f"{entry['status']:>14}  {key}" + (f"  ({entry['error']})" if "error" in entry else ""), flush=True)
port = int(os.getenv("PORT", "8765"))
print(f"basketball engine listening on {port}; {len(games)} game request(s)", flush=True)
ThreadingHTTPServer((os.getenv("ENGINE_BIND_HOST", "0.0.0.0"), port),
                    handler(store, os.environ["ENGINE_API_TOKEN"], games)).serve_forever()
