"""Fail-closed client for the private engine-state service.

Configuration comes from the environment and never from Git:
  ENGINE_RUNTIME_URL  the Railway public URL of the service
  ENGINE_API_TOKEN    the bearer token set on the Railway service
"""
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import hashlib
import json
import os

from . import KERNEL_VERSION, SCHEMA_VERSION
from .packets import canonical
from .snapshot import current_snapshot

DEFAULT_URL = "http://127.0.0.1:8765"


class EngineUnavailable(RuntimeError):
    pass


class Client:
    def __init__(self, url=None, token=None, snapshot=None, timeout=15):
        self.url = (url or os.getenv("ENGINE_RUNTIME_URL") or DEFAULT_URL).rstrip("/")
        self.token = token if token is not None else os.getenv("ENGINE_API_TOKEN", "")
        self.snapshot = snapshot or current_snapshot()
        self.timeout = timeout

    def _request(self, path, method="GET", auth=True):
        headers = {}
        if auth:
            if not self.token:
                raise EngineUnavailable("ENGINE_API_TOKEN is not set")
            headers["Authorization"] = f"Bearer {self.token}"
        request = Request(self.url + path, headers=headers, method=method, data=b"" if method == "POST" else None)
        route = path.split("?", 1)[0]
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.load(response)
        except HTTPError as exc:
            try:
                detail = json.loads(exc.read().decode()).get("error", "")
            except (OSError, ValueError, AttributeError):
                detail = ""
            raise EngineUnavailable(f"engine {route} failed (HTTP {exc.code}{': ' + detail if detail else ''})") from exc
        except (OSError, URLError, ValueError) as exc:
            raise EngineUnavailable(f"engine {route} unreachable") from exc

    def readiness(self):
        health = self._request("/health", auth=False)
        if health.get("schema") != SCHEMA_VERSION or health.get("kernel") != KERNEL_VERSION:
            raise EngineUnavailable(f"engine identity mismatch: deployed kernel {health.get('kernel')}, local {KERNEL_VERSION}")
        data = self._request("/ready")
        if data.get("snapshot_advance_pending"):
            raise EngineUnavailable("engine is locked: run scripts/advance_engine_snapshot.py from merged main")
        if data.get("snapshot") != self.snapshot:
            raise EngineUnavailable("engine snapshot differs from this checkout's current_state.json")
        if not data.get("ready"):
            raise EngineUnavailable("engine store failed its readiness check")
        first = self._request("/admin/probe", "POST")
        second = self._request("/admin/probe", "POST")
        if not first.get("journal_fingerprint") or first != second:
            raise EngineUnavailable("engine administrative probe is not idempotent")
        canary = {"event_id": "__readiness__:" + hashlib.sha256(canonical([self.snapshot, KERNEL_VERSION])).hexdigest(),
                  "kernel": KERNEL_VERSION, "snapshot": self.snapshot, "type": "readiness-canary"}
        if self.close_event(canary) != self.close_event(canary):
            raise EngineUnavailable("engine event closure is not idempotent")
        return {"ready": True, "kernel": KERNEL_VERSION, "schema": SCHEMA_VERSION, "snapshot": self.snapshot}

    def close_event(self, packet):
        event_id = packet.get("event_id") if isinstance(packet, dict) else None
        if not isinstance(event_id, str) or not event_id.strip():
            raise ValueError("packet event_id must be a nonempty string")
        query = urlencode({"event_id": event_id, "packet_sha256": hashlib.sha256(canonical(packet)).hexdigest()})
        result_ref = self._request("/events/close?" + query, "POST").get("result_ref")
        if not isinstance(result_ref, str) or len(result_ref) != 64:
            raise EngineUnavailable("engine returned an invalid event reference")
        return result_ref

    def current_snapshot(self):
        return self._request("/ready")["snapshot"]

    def advance_snapshot(self, previous_snapshot, next_snapshot, checkpoint):
        query = urlencode({"previous_snapshot": previous_snapshot, "next_snapshot": next_snapshot,
                           "checkpoint": checkpoint})
        return self._request("/admin/snapshot/advance?" + query, "POST")["snapshot"]

    def record_correction(self, event_id, reason):
        query = urlencode({"event_id": event_id, "reason": reason})
        return self._request("/corrections?" + query, "POST").get("recorded") is True
