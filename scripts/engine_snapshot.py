#!/usr/bin/env python3
"""Print (or write) the digest of the live current_state.json the engine binds to."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.snapshot import current_snapshot

digest = current_snapshot()
if len(sys.argv) > 2 and sys.argv[1] == "--write":
    Path(sys.argv[2]).write_text(digest + "\n")
print(digest)
