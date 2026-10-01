"""Authenticated private engine-state service (deployed on Railway).

The service holds the career seed and a journal of closed game packets on a
persistent volume. It never sees packet contents: a caller posts the event id
and the SHA-256 of the canonical packet, the service journals that identity
before deriving anything, and returns an opaque reference that the local
kernel turns into game entropy. The same event and packet always return the
same reference; the same event with a different packet is refused, so a game
cannot be re-rolled by editing its inputs.

Endpoints:
  GET  /health                     unauthenticated identity (service, schema, kernel)
  GET  /ready                      authenticated readiness and bound snapshot
  POST /admin/probe                idempotent administrative canary
  POST /events/close?event_id=&packet_sha256=
  POST /admin/snapshot/advance?previous_snapshot=&next_snapshot=&checkpoint=
  POST /corrections?event_id=&reason=
"""
from contextlib import closing
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
import hashlib
import hmac
import json
import secrets
import sqlite3
import threading
import time

from . import KERNEL_VERSION, SCHEMA_VERSION
from .packets import canonical

SERVICE = "basketball-engine-state"


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        with closing(self.connect()) as c, c:
            c.executescript("""PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value BLOB NOT NULL);
            CREATE TABLE IF NOT EXISTS events(event_id TEXT PRIMARY KEY, packet_hash TEXT NOT NULL,
                result TEXT, created INTEGER NOT NULL, closed INTEGER);
            CREATE TABLE IF NOT EXISTS corrections(id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL, reason TEXT NOT NULL, created INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS admin_probes(probe_id TEXT PRIMARY KEY, created INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS snapshot_transitions(id INTEGER PRIMARY KEY AUTOINCREMENT,
                previous_snapshot TEXT NOT NULL, next_snapshot TEXT NOT NULL,
                checkpoint TEXT NOT NULL, created INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS kernel_transitions(id INTEGER PRIMARY KEY AUTOINCREMENT,
                previous_kernel TEXT NOT NULL, next_kernel TEXT NOT NULL,
                snapshot TEXT NOT NULL, created INTEGER NOT NULL);""")

    def connect(self):
        return sqlite3.connect(self.path)

    def initialize(self, snapshot):
        """Seed once, bind the snapshot once, record kernel changes append-only.

        Returns True when the stored snapshot differs from the image's: the
        service then starts locked (no event closure) until the ordinary
        compare-and-swap advance catches the store up. The stored snapshot is
        never overwritten at startup.
        """
        with self.lock, closing(self.connect()) as c, c:
            c.execute("BEGIN IMMEDIATE")
            if not c.execute("SELECT 1 FROM meta WHERE key='seed'").fetchone():
                c.execute("INSERT INTO meta VALUES('seed', ?)", (secrets.token_bytes(32),))
            old = c.execute("SELECT value FROM meta WHERE key='snapshot'").fetchone()
            c.execute("INSERT OR IGNORE INTO meta VALUES('snapshot', ?)", (snapshot.encode(),))
            stored_kernel = c.execute("SELECT value FROM meta WHERE key='kernel'").fetchone()
            if stored_kernel and stored_kernel[0].decode() != KERNEL_VERSION:
                bound = old[0].decode() if old else snapshot
                c.execute("INSERT INTO kernel_transitions(previous_kernel, next_kernel, snapshot, created) "
                          "VALUES(?,?,?,?)", (stored_kernel[0].decode(), KERNEL_VERSION, bound, int(time.time())))
            c.execute("INSERT OR REPLACE INTO meta VALUES('kernel', ?)", (KERNEL_VERSION.encode(),))
            c.execute("INSERT OR REPLACE INTO meta VALUES('schema', ?)", (SCHEMA_VERSION.encode(),))
            return bool(old and old[0].decode() != snapshot)

    def _meta(self, c, key):
        row = c.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        if not row:
            raise ValueError(f"store is not initialized ({key})")
        return row[0]

    def current_snapshot(self):
        with closing(self.connect()) as c:
            return self._meta(c, "snapshot").decode()

    def kernel_history(self):
        with closing(self.connect()) as c:
            return c.execute("SELECT previous_kernel, next_kernel, snapshot FROM kernel_transitions ORDER BY id").fetchall()

    def ready(self):
        """Verify the store survives a backup round trip with its identity intact."""
        with closing(self.connect()) as c:
            seed = self._meta(c, "seed")
            snapshot = self._meta(c, "snapshot").decode()
            kernel = self._meta(c, "kernel").decode()
            schema = self._meta(c, "schema").decode()
            backup_path = self.path.with_name(self.path.stem + ".backup.sqlite3")
            with closing(sqlite3.connect(backup_path)) as backup:
                c.backup(backup)
        with closing(sqlite3.connect(f"file:{backup_path}?mode=ro", uri=True)) as recovered:
            if recovered.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                return False
            row = recovered.execute("SELECT value FROM meta WHERE key='snapshot'").fetchone()
            if not row or row[0].decode() != snapshot:
                return False
        return len(seed) >= 32 and kernel == KERNEL_VERSION and schema == SCHEMA_VERSION

    def advance_snapshot(self, previous_snapshot, next_snapshot, checkpoint):
        for value in (previous_snapshot, next_snapshot, checkpoint):
            if not isinstance(value, str) or not value.strip():
                raise ValueError("snapshot transition fields must be nonempty strings")
        if previous_snapshot == next_snapshot:
            raise ValueError("snapshot transition must change the snapshot")
        with self.lock, closing(self.connect()) as c, c:
            c.execute("BEGIN IMMEDIATE")
            current = self._meta(c, "snapshot").decode()
            if current == next_snapshot:
                # Idempotent replay of the exact transition already applied.
                if c.execute("SELECT 1 FROM snapshot_transitions WHERE previous_snapshot=? AND "
                             "next_snapshot=? AND checkpoint=?",
                             (previous_snapshot, next_snapshot, checkpoint)).fetchone():
                    return current
                raise ValueError("conflicting snapshot transition refused")
            if current != previous_snapshot:
                raise ValueError("previous snapshot does not match current snapshot")
            c.execute("INSERT INTO snapshot_transitions(previous_snapshot, next_snapshot, checkpoint, created) "
                      "VALUES(?,?,?,?)", (previous_snapshot, next_snapshot, checkpoint, int(time.time())))
            c.execute("UPDATE meta SET value=? WHERE key='snapshot'", (next_snapshot.encode(),))
            return next_snapshot

    def probe(self):
        with self.lock, closing(self.connect()) as c, c:
            snapshot = self._meta(c, "snapshot").decode()
            probe_id = hashlib.sha256(f"{snapshot}:{KERNEL_VERSION}".encode()).hexdigest()
            c.execute("INSERT OR IGNORE INTO admin_probes VALUES(?, ?)", (probe_id, int(time.time())))
            created = c.execute("SELECT created FROM admin_probes WHERE probe_id=?", (probe_id,)).fetchone()[0]
            seed = self._meta(c, "seed")
            fingerprint = hmac.new(seed, f"{probe_id}:{created}".encode(), hashlib.sha256).hexdigest()
            return {"idempotent": True, "journal_fingerprint": fingerprint}

    def close_event(self, event_id, packet_hash):
        if not isinstance(event_id, str) or not event_id.strip():
            raise ValueError("event_id must be a nonempty string")
        if not isinstance(packet_hash, str) or len(packet_hash) != 64:
            raise ValueError("packet_sha256 must be a 64-character hex digest")
        try:
            bytes.fromhex(packet_hash)
        except ValueError as exc:
            raise ValueError("packet_sha256 must be hexadecimal") from exc
        with self.lock, closing(self.connect()) as c, c:
            c.execute("BEGIN IMMEDIATE")
            row = c.execute("SELECT packet_hash, result FROM events WHERE event_id=?", (event_id,)).fetchone()
            if row:
                if row[0] != packet_hash:
                    raise ValueError("altered packet refused")
                return row[1]
            # Journal the immutable identity before deriving any entropy.
            c.execute("INSERT INTO events VALUES(?, ?, NULL, ?, NULL)", (event_id, packet_hash, int(time.time())))
            seed = self._meta(c, "seed")
            context = canonical(["event-close-v1", event_id, packet_hash])
            result = hashlib.sha256(hmac.new(seed, context, hashlib.sha256).digest()).hexdigest()
            c.execute("UPDATE events SET result=?, closed=? WHERE event_id=?", (result, int(time.time()), event_id))
            return result

    def correct(self, event_id, reason):
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("correction reason required")
        with self.lock, closing(self.connect()) as c, c:
            if not c.execute("SELECT 1 FROM events WHERE event_id=?", (event_id,)).fetchone():
                raise ValueError("unknown event")
            if not c.execute("SELECT 1 FROM corrections WHERE event_id=? AND reason=?",
                             (event_id, reason.strip())).fetchone():
                c.execute("INSERT INTO corrections(event_id, reason, created) VALUES(?,?,?)",
                          (event_id, reason.strip(), int(time.time())))


def handler(store, token, locked_until=None):
    if not token or len(token) < 32:
        raise ValueError("ENGINE_API_TOKEN must be at least 32 characters")

    def pending():
        return locked_until is not None and store.current_snapshot() != locked_until

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def send(self, status, body):
            raw = json.dumps(body, separators=(",", ":")).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def authorized(self):
            supplied = self.headers.get("Authorization", "").removeprefix("Bearer ")
            if not hmac.compare_digest(supplied.encode(), token.encode()):
                self.send(401, {"error": "unauthorized"})
                return False
            return True

        def do_GET(self):
            if self.path == "/health":
                return self.send(200, {"service": SERVICE, "schema": SCHEMA_VERSION, "kernel": KERNEL_VERSION})
            if not self.authorized():
                return
            if self.path == "/ready":
                waiting = pending()
                return self.send(200, {"ready": store.ready() and not waiting,
                                       "snapshot_advance_pending": waiting,
                                       "schema": SCHEMA_VERSION, "kernel": KERNEL_VERSION,
                                       "snapshot": store.current_snapshot()})
            self.send(404, {"error": "not found"})

        def do_POST(self):
            if not self.authorized():
                return
            try:
                parsed = urlsplit(self.path)
                query = {k: v[0] for k, v in parse_qs(parsed.query, keep_blank_values=True).items()}

                def need(*names):
                    missing = [n for n in names if n not in query]
                    if missing:
                        raise ValueError("missing " + ", ".join(missing))
                    return [query[n] for n in names]

                if parsed.path in {"/events/close", "/admin/probe"} and pending():
                    return self.send(409, {"error": "snapshot advance pending; event closure locked"})
                if parsed.path == "/events/close":
                    event_id, packet_hash = need("event_id", "packet_sha256")
                    return self.send(200, {"result_ref": store.close_event(event_id, packet_hash)})
                if parsed.path == "/admin/probe":
                    return self.send(200, store.probe())
                if parsed.path == "/admin/snapshot/advance":
                    current = store.advance_snapshot(*need("previous_snapshot", "next_snapshot", "checkpoint"))
                    return self.send(200, {"advanced": True, "snapshot": current})
                if parsed.path == "/corrections":
                    store.correct(*need("event_id", "reason"))
                    return self.send(201, {"recorded": True})
                self.send(404, {"error": "not found"})
            except ValueError as exc:
                self.send(409, {"error": str(exc)})

    return Handler
