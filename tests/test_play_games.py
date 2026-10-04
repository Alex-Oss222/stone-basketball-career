"""The authenticated POST /games route: play from the deployed copy only when its inputs match the caller's."""
import json
from pathlib import Path
import shutil
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from runtime.game_requests import find_requests, input_fingerprint
from runtime.private_service import Store, handler
from scripts.collect_results import result_errors

ROOT = Path(__file__).resolve().parents[1]
TOKEN = "g" * 40


def a_pending_request():
    for path in find_requests(ROOT):
        if "Stats_and_Awards" in str(path) and not path.with_name(path.name.replace(".request.json", ".result.json")).exists():
            return path
    for path in find_requests(ROOT):
        if "Stats_and_Awards" in str(path):
            return path                     # a played one: the route returns its stored result
    return None


class PlayGamesRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.deployed = Path(cls.tmp.name) / "deployed"
        for folder in ("library", "career", "foundation", "runtime"):
            shutil.copytree(ROOT / folder, cls.deployed / folder, ignore=shutil.ignore_patterns("__pycache__"))
        cls.path = a_pending_request()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.store = Store(Path(self.tmp.name) / f"engine-{self.id()}.sqlite3")
        self.store.initialize()
        self.games = {}
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler(self.store, TOKEN, self.games, root=self.deployed))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.url = f"http://127.0.0.1:{server.server_address[1]}"
        self.rel = self.path.relative_to(ROOT).as_posix()
        (self.deployed / self.rel).unlink(missing_ok=True)       # the deploy predates the request
        self.data = json.loads(self.path.read_text())

    def send(self, body, token=TOKEN):
        try:
            with urlopen(Request(f"{self.url}/games", data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}), timeout=120) as r:
                return r.status, json.loads(r.read())
        except HTTPError as exc:
            return exc.code, json.loads(exc.read())

    def test_a_matching_game_is_played_once_and_kept(self):
        body = {"path": self.rel, "request": self.data, "fingerprint": input_fingerprint(self.path, ROOT)}
        status, first = self.send(body)
        self.assertEqual((status, first.pop("status")), (201, "played"))
        self.assertEqual(result_errors(self.data, first, "game"), [])
        status, again = self.send(body)
        self.assertEqual((status, again.pop("status")), (200, "already_played"))
        self.assertEqual(again["final_score"], first["final_score"])
        self.assertEqual(self.games[self.data["event_id"]]["status"], "already_played")

    def test_changed_inputs_wrong_paths_and_no_token_are_refused(self):
        status, body = self.send({"path": self.rel, "request": self.data, "fingerprint": "0" * 64})
        self.assertEqual(status, 409)
        self.assertIn("deployed inputs differ", body["error"])
        self.assertFalse((self.deployed / self.rel).exists())       # the deployed copy is left as it was
        status, _ = self.send({"path": "../etc/x.request.json", "request": self.data, "fingerprint": "0" * 64})
        self.assertEqual(status, 409)
        status, _ = self.send({"path": self.rel, "request": self.data, "fingerprint": "0" * 64}, token="x" * 40)
        self.assertEqual(status, 401)



class PendingRequestsFreezeTests(unittest.TestCase):
    def test_every_pending_request_freezes_to_a_valid_packet(self):
        """Repository validation checks requests before the engine's freeze step; this runs the step itself."""
        from runtime.game_requests import load_request
        from runtime.game_runner import freeze_inputs
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "freeze.sqlite3")
            store.initialize()
            for path in find_requests(ROOT):
                if path.with_name(path.name.replace(".request.json", ".result.json")).exists():
                    continue
                with self.subTest(request=path.name):
                    home, away, kwargs = load_request(path, ROOT)
                    freeze_inputs(home, away, store, **kwargs)


if __name__ == "__main__":
    unittest.main()
