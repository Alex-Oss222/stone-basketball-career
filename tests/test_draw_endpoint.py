"""The authenticated POST /decisions route, the draw client and the collector's result check."""
import json
from pathlib import Path
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from runtime.private_service import Store, handler, play_requests
from scripts.collect_results import result_errors
from scripts.draw_decisions import draw_pending, post

TOKEN = "t" * 40
PACKET = {"event_id": "2003-fa-test01-offer-1", "date": "2003-07-02", "question": "Does Test Player accept Miami's offer?",
          "decider": "Test Player (simulated player)", "options": {"accept": 0.3, "counter": 0.5, "reject": 0.2},
          "basis": "test packet"}


class DrawEndpointTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.store = Store(self.root / "data/engine.sqlite3")
        self.store.initialize()
        self.games = {}
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler(self.store, TOKEN, self.games))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.url = f"http://127.0.0.1:{server.server_address[1]}"

    def send(self, data, token=TOKEN, raw=None):
        body = raw if raw is not None else json.dumps(data).encode()
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            with urlopen(Request(f"{self.url}/decisions", data=body, method="POST", headers=headers), timeout=10) as r:
                return r.status, json.loads(r.read())
        except HTTPError as exc:
            return exc.code, json.loads(exc.read())

    def test_draw_once_then_the_same_answer_for_ever(self):
        status, first = self.send(PACKET)
        self.assertEqual((status, first["status"]), (201, "decided"))
        self.assertIn(first["outcome"], PACKET["options"])
        status, again = self.send(PACKET)
        self.assertEqual((status, again["status"], again["outcome"]), (200, "already_decided", first["outcome"]))
        with urlopen(f"{self.url}/decisions/{PACKET['event_id']}", timeout=10) as r:
            self.assertEqual(json.loads(r.read())["outcome"], first["outcome"])
        self.assertEqual(self.games[PACKET["event_id"]]["status"], "already_decided")

    def test_changed_packet_unauthorised_and_malformed_requests_are_refused(self):
        self.send(PACKET)
        status, body = self.send(dict(PACKET, options={"accept": 0.9, "reject": 0.1}))
        self.assertEqual(status, 409)
        self.assertIn("altered packet refused", body["error"])
        self.assertEqual(self.send(PACKET, token=None)[0], 401)
        self.assertEqual(self.send(PACKET, token="w" * 40)[0], 401)
        self.assertEqual(self.send(None, raw=b"not json")[0], 400)
        self.assertEqual(self.send(dict(PACKET, extra=1))[0], 409)          # the decision schema is enforced
        self.assertEqual(self.send(dict(PACKET, event_id="other", options={"accept": 1.0}))[0], 409)

    def test_a_posted_draw_is_verified_by_the_next_boot_scan(self):
        _, first = self.send(PACKET)
        folder = self.root / "career/Dwyane_Wade/2003-04/01_Free_Agency/Negotiations"
        folder.mkdir(parents=True)
        (folder / f"{PACKET['event_id']}.decision.json").write_text(json.dumps(PACKET))
        status = play_requests(self.store, self.root)
        self.assertEqual(status[PACKET["event_id"]]["status"], "already_decided")
        self.assertEqual(self.store.result(PACKET["event_id"])["outcome"], first["outcome"])
        (folder / f"{PACKET['event_id']}.decision.json").write_text(json.dumps(dict(PACKET, basis="edited after the draw")))
        self.assertEqual(play_requests(self.store, self.root)[f"career/Dwyane_Wade/2003-04/01_Free_Agency/Negotiations/{PACKET['event_id']}.decision.json"]["status"], "error")

    def test_client_writes_checked_results_and_skips_answered_requests(self):
        folder = self.root / "career/Dwyane_Wade/2003-04/01_Free_Agency/Negotiations"
        folder.mkdir(parents=True)
        (folder / f"{PACKET['event_id']}.decision.json").write_text(json.dumps(PACKET))
        report = draw_pending(self.root, send=lambda data: post(data, TOKEN, url=self.url))
        self.assertEqual(len(report), 1)
        result = json.loads((folder / f"{PACKET['event_id']}.decision.result.json").read_text())
        self.assertNotIn("status", result)
        self.assertEqual(result_errors(PACKET, result, "decision"), [])
        self.assertEqual(draw_pending(self.root, send=lambda data: post(data, TOKEN, url=self.url)), [])

    def test_collector_check_refuses_an_answer_to_a_different_request(self):
        good = {"event_id": PACKET["event_id"], "kind": "decision", "date": PACKET["date"], "question": PACKET["question"],
                "decider": PACKET["decider"], "options": PACKET["options"], "outcome": "counter"}
        self.assertEqual(result_errors(PACKET, good, "decision"), [])
        self.assertTrue(result_errors(PACKET, dict(good, options={"accept": 0.5, "reject": 0.5}), "decision"))
        self.assertTrue(result_errors(PACKET, dict(good, outcome="walk"), "decision"))
        self.assertTrue(result_errors(PACKET, dict(good, event_id="x"), "decision"))
        self.assertEqual(result_errors({"event_id": "g"}, {"event_id": "g"}, "game"), [])


if __name__ == "__main__":
    unittest.main()
