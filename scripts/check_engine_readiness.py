#!/usr/bin/env python3
"""Fail-closed check that the deployed engine matches this checkout."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.game_runner import architecture_errors
from runtime.private_client import Client, EngineUnavailable

errors = architecture_errors()
if errors:
    raise SystemExit("architecture: " + "; ".join(errors))
try:
    print(Client().readiness())
except EngineUnavailable as exc:
    raise SystemExit(f"engine not ready: {exc}")
