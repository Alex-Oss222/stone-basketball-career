"""Engine service deployed on Railway.

On every start (that is, every push to the branch Railway tracks) the service
plays any game request in the repository it has not played yet, keeps the
result, and serves it. The career seed lives only on the Railway volume. Before
a game is drawn, its event id and the SHA-256 of its canonical packet are
journaled; the same event with the same packet replays identically, and the
same event with changed inputs is refused, so a result cannot be re-rolled.

Public (results are not secret; only the seed is):
  GET /career                     detailed canonical milestone screens
  GET /cards                      canonical Shooting, Contract and Awards
  GET /contracts                  every tracked player's contract page
  GET /career/status              current screen cutoff and deployed revision
  GET /health
  GET /games                       every request and its status
  GET /games/<event_id>            result JSON
  GET /games/<event_id>/box        plain-text box score
  GET /decisions/<event_id>        an engine-drawn decision (same store as games)
Authenticated with ENGINE_API_TOKEN:
  GET  /ready
  POST /corrections?event_id=&reason=
"""
from contextlib import closing
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit
import hashlib
import hmac
import json
import secrets
import sqlite3
import threading
import time

from . import KERNEL_VERSION, SCHEMA_VERSION
from .packets import canonical

SERVICE = "basketball-engine"


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
            CREATE TABLE IF NOT EXISTS results(event_id TEXT PRIMARY KEY, packet_hash TEXT NOT NULL,
                body TEXT NOT NULL, created INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS corrections(id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL, reason TEXT NOT NULL, created INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS kernel_transitions(id INTEGER PRIMARY KEY AUTOINCREMENT,
                previous_kernel TEXT NOT NULL, next_kernel TEXT NOT NULL, created INTEGER NOT NULL);""")

    def connect(self):
        return sqlite3.connect(self.path)

    def initialize(self):
        """Create the seed once; record kernel version changes append-only."""
        with self.lock, closing(self.connect()) as c, c:
            c.execute("BEGIN IMMEDIATE")
            if not c.execute("SELECT 1 FROM meta WHERE key='seed'").fetchone():
                c.execute("INSERT INTO meta VALUES('seed', ?)", (secrets.token_bytes(32),))
            stored = c.execute("SELECT value FROM meta WHERE key='kernel'").fetchone()
            if stored and stored[0].decode() != KERNEL_VERSION:
                # A store created by the first engine version has a required `snapshot` column here.
                columns = {row[1] for row in c.execute("PRAGMA table_info(kernel_transitions)")}
                if "snapshot" in columns:
                    c.execute("INSERT INTO kernel_transitions(previous_kernel, next_kernel, snapshot, created) "
                              "VALUES(?,?,?,?)", (stored[0].decode(), KERNEL_VERSION, "", int(time.time())))
                else:
                    c.execute("INSERT INTO kernel_transitions(previous_kernel, next_kernel, created) VALUES(?,?,?)",
                              (stored[0].decode(), KERNEL_VERSION, int(time.time())))
            c.execute("INSERT OR REPLACE INTO meta VALUES('kernel', ?)", (KERNEL_VERSION.encode(),))
            c.execute("INSERT OR REPLACE INTO meta VALUES('schema', ?)", (SCHEMA_VERSION.encode(),))

    def _meta(self, c, key):
        row = c.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        if not row:
            raise ValueError(f"store is not initialized ({key})")
        return row[0]

    def kernel_history(self):
        with closing(self.connect()) as c:
            return c.execute("SELECT previous_kernel, next_kernel FROM kernel_transitions ORDER BY id").fetchall()

    def ready(self):
        """Verify the store survives a backup round trip with its seed intact."""
        with closing(self.connect()) as c:
            seed = self._meta(c, "seed")
            backup_path = self.path.with_name(self.path.stem + ".backup.sqlite3")
            with closing(sqlite3.connect(backup_path)) as backup:
                c.backup(backup)
        with closing(sqlite3.connect(f"file:{backup_path}?mode=ro", uri=True)) as recovered:
            if recovered.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                return False
            row = recovered.execute("SELECT value FROM meta WHERE key='seed'").fetchone()
        return bool(row) and row[0] == seed and len(seed) >= 32

    def close_digest(self, event_id, packet_hash):
        if not isinstance(event_id, str) or not event_id.strip():
            raise ValueError("event_id must be a nonempty string")
        if not isinstance(packet_hash, str) or len(packet_hash) != 64:
            raise ValueError("packet hash must be a 64-character hex digest")
        bytes.fromhex(packet_hash)
        with self.lock, closing(self.connect()) as c, c:
            c.execute("BEGIN IMMEDIATE")
            row = c.execute("SELECT packet_hash, result FROM events WHERE event_id=?", (event_id,)).fetchone()
            if row:
                if row[0] != packet_hash:
                    raise ValueError("altered packet refused: this game was already played with different inputs")
                return row[1]
            # Journal the immutable identity before deriving any entropy.
            c.execute("INSERT INTO events VALUES(?, ?, NULL, ?, NULL)", (event_id, packet_hash, int(time.time())))
            seed = self._meta(c, "seed")
            context = canonical(["event-close-v1", event_id, packet_hash])
            result = hashlib.sha256(hmac.new(seed, context, hashlib.sha256).digest()).hexdigest()
            c.execute("UPDATE events SET result=?, closed=? WHERE event_id=?", (result, int(time.time()), event_id))
            return result

    def close_event(self, packet):
        """Journal interface used by `game_runner.run_game`."""
        return self.close_digest(packet["event_id"], hashlib.sha256(canonical(packet)).hexdigest())

    def save_result(self, event_id, packet_hash, result):
        with self.lock, closing(self.connect()) as c, c:
            c.execute("INSERT OR IGNORE INTO results VALUES(?, ?, ?, ?)",
                      (event_id, packet_hash, json.dumps(result, sort_keys=True), int(time.time())))

    def result(self, event_id):
        with closing(self.connect()) as c:
            row = c.execute("SELECT body FROM results WHERE event_id=?", (event_id,)).fetchone()
            return json.loads(row[0]) if row else None

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


def play_requests(store, root):
    """Play every game request in the repository. Returns {event_id or path: status}."""
    from .game_requests import find_requests, load_request
    from .game_runner import freeze_inputs, replay_packet, run_game

    status = {}
    for path in find_requests(root):
        rel = str(path.relative_to(root))
        try:
            home, away, kwargs = load_request(path, root)
            event_id = kwargs["event_id"]
            existing = store.result(event_id)
            if existing is None:
                packet = freeze_inputs(home, away, store, **kwargs)[2]
                packet_hash = hashlib.sha256(canonical(packet)).hexdigest()
                result = run_game(home, away, journal=store, **kwargs)
                store.save_result(event_id, packet_hash, result)
                state = "played"
            else:
                packet = replay_packet(home, away, store, existing, **kwargs)
                packet_hash = hashlib.sha256(canonical(packet)).hexdigest()
                store.close_digest(event_id, packet_hash)  # refuses edited inputs
                state = "already_played"
            status[event_id] = {"status": state, "request": rel}
        except Exception as exc:  # one bad request must not stop the others or the service
            status[rel] = {"status": "error", "request": rel, "error": str(exc)}
    from .decisions import find_decisions, load_decision
    for path in find_decisions(root):
        rel = str(path.relative_to(root))
        try:
            data = load_decision(path)
            state, _ = play_decision(store, data)
            status[data["event_id"]] = {"status": state, "request": rel}
        except Exception as exc:
            status[rel] = {"status": "error", "request": rel, "error": str(exc)}
    return status


MAX_DECISION_BYTES = 65536


def play_decision(store, data):
    """Draw one decision packet once, or return the stored draw for the identical packet.

    The single path for both the boot scan of committed `*.decision.json` files and the authenticated
    `POST /decisions` route: the engine journals the packet before drawing, keeps the first result for
    ever, and refuses a packet that differs from the one already drawn under the same event id.
    Returns (status, result) with status "decided" or "already_decided".
    """
    from .decisions import decision_errors, draw, packet
    errors = decision_errors(data)
    if errors:
        raise ValueError("; ".join(errors))
    packet_hash = hashlib.sha256(canonical(packet(data))).hexdigest()
    existing = store.result(data["event_id"])
    if existing is not None:
        store.close_digest(data["event_id"], packet_hash)      # refuses an edited request
        return "already_decided", existing
    result = {"event_id": data["event_id"], "kind": "decision", "date": data["date"], "question": data["question"],
              "decider": data["decider"], "options": data["options"], "outcome": draw(data, store)}
    store.save_result(data["event_id"], packet_hash, result)
    return "decided", store.result(data["event_id"])


def handler(store, token, games, career_site=None):
    if not token or len(token) < 32:
        raise ValueError("ENGINE_API_TOKEN must be at least 32 characters")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def send(self, status, body, content_type="application/json"):
            raw = body if isinstance(body, bytes) else body.encode() if isinstance(body, str) else json.dumps(body, indent=1).encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type + "; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-cache")
            if content_type == "text/html":
                self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            self.end_headers()
            self.wfile.write(raw)

        def authorized(self):
            supplied = self.headers.get("Authorization", "").removeprefix("Bearer ")
            if not hmac.compare_digest(supplied.encode(), token.encode()):
                self.send(401, {"error": "unauthorized"})
                return False
            return True

        def do_GET(self):
            path = urlsplit(self.path).path.rstrip("/") or "/"
            if path == "/health":
                return self.send(200, {"service": SERVICE, "schema": SCHEMA_VERSION, "kernel": KERNEL_VERSION})
            if career_site is not None:
                if path in ("/", "/career", "/player", "/cards", "/contracts"):
                    self.send_response(302)
                    self.send_header("Location", career_site.contracts if path == "/contracts" else
                                     career_site.cards if path in ("/player", "/cards") else career_site.home)
                    self.send_header("Cache-Control", "no-cache")
                    self.end_headers()
                    return
                if path == "/career/status":
                    return self.send(200, career_site.status)
                resource = career_site.resource(path)
                if resource is not None:
                    return self.send(200, resource[0], resource[1])
            if path in ("/", "/games"):
                return self.send(200, {"kernel": KERNEL_VERSION, "games": games})
            if path.startswith("/decisions/"):
                result = store.result(unquote(path[len("/decisions/"):]))
                if result is None or result.get("kind") != "decision":
                    return self.send(404, {"error": "no drawn decision with that id"})
                return self.send(200, result)
            if path.startswith("/games/"):
                parts = path[len("/games/"):].split("/")
                event_id = unquote(parts[0])
                result = store.result(event_id)
                if result is None:
                    return self.send(404, {"error": f"no played game {event_id!r}"})
                if parts[1:] == ["box"]:
                    from .boxscore import render
                    return self.send(200, render(result), "text/plain")
                if len(parts) == 1:
                    return self.send(200, result)
            if path == "/ready":
                if not self.authorized():
                    return
                return self.send(200, {"ready": store.ready(), "kernel": KERNEL_VERSION, "schema": SCHEMA_VERSION})
            self.send(404, {"error": "not found"})

        def do_POST(self):
            if not self.authorized():
                return
            parsed = urlsplit(self.path)
            query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
            try:
                if parsed.path == "/corrections":
                    store.correct(query["event_id"], query["reason"])
                    return self.send(201, {"recorded": True})
                if parsed.path.rstrip("/") == "/decisions":
                    # A decision drawn on demand: the same packet, journal and no-re-roll rule as a deploy scan.
                    length = int(self.headers.get("Content-Length") or 0)
                    if length <= 0 or length > MAX_DECISION_BYTES:
                        return self.send(413 if length > 0 else 400, {"error": "a decision body of 1 to 65536 bytes is required"})
                    try:
                        data = json.loads(self.rfile.read(length).decode("utf-8"))
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        return self.send(400, {"error": "the body must be a JSON decision packet"})
                    state, result = play_decision(store, data)
                    games[data["event_id"]] = {"status": state, "request": "POST /decisions"}
                    return self.send(201 if state == "decided" else 200, dict(result, status=state))
                self.send(404, {"error": "not found"})
            except (KeyError, ValueError) as exc:
                self.send(409, {"error": str(exc)})

    return Handler
