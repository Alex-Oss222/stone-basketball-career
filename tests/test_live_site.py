import hashlib
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from runtime.live_site import CareerSite, source_page
from runtime.private_service import Store, handler

ROOT = Path(__file__).resolve().parents[1]
TOKEN = "live-site-test-token-32-characters-long"


class LiveCareerSiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.site = CareerSite(ROOT, revision="test-revision")

    def test_live_pages_are_canonical_and_detailed_without_writing_career(self):
        source = ROOT / "career/Dwyane_Wade/2003-04/current_state.json"
        before = hashlib.sha256(source.read_bytes()).hexdigest()
        self.assertEqual(self.site.status["as_of"], json.loads(source.read_text())["current_date"])   # the live clock
        self.assertEqual(self.site.status["detail"], "full")
        self.assertEqual(self.site.status["mode"], "canonical")
        for path in (self.site.home, self.site.cards):
            page, kind = self.site.resource(path)
            self.assertEqual(kind, "text/html")
            self.assertIn("Dwyane", page)
            self.assertNotIn('"name": "Example Player"', page)
            self.assertNotIn("illustrative-1", page)
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), before)

    def test_source_routes_are_bounded_and_examples_are_not_live_apps(self):
        for path in ("/career/../runtime/private_service.py", "/career/%2e%2e/.env",
                     "/career/Dwyane_Wade/%2e%2e/%2e%2e/AGENTS.md", "/data/engine.sqlite3",
                     "/docs/examples/player_cards_preview.html", "/library/../../etc/passwd",
                     "/library/careers/nba_player_careers.json", "/library/2013/league/nba_2013_14_team_rosters.json"):
            self.assertIsNone(self.site.resource(path), path)
        page, kind = self.site.resource("/career/Dwyane_Wade/2003-04/current_state.json")
        self.assertEqual(kind, "application/json")
        live = json.loads((ROOT / "career/Dwyane_Wade/2003-04/current_state.json").read_text(encoding="utf-8"))
        self.assertEqual(json.loads(page)["contract_status"], live["contract_status"])      # served as recorded, whatever the date

    def test_record_pages_keep_full_tables_and_escape_embedded_html(self):
        page = source_page("# Record\n\n| A | B |\n| --- | --- |\n| 2 | 3 |\n\n<script>alert(1)</script>\n[Bad](javascript:alert)\n", "Record")
        self.assertIn("<table>", page)
        self.assertIn("<td>3</td>", page)
        self.assertIn("&lt;script&gt;", page)
        self.assertNotIn("<script>", page)
        self.assertIn('href="#"', page)
        banner = source_page("[![Shooting](assets/shooting.svg)](Shooting.md)", "Cards")
        self.assertIn('<a href="Shooting.md"><img src="assets/shooting.svg"', banner)
        self.assertNotIn("\x00", banner)

    def test_http_routes_preserve_engine_auth_and_expose_live_screens(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / "engine.sqlite3")
            store.initialize()
            server = ThreadingHTTPServer(("127.0.0.1", 0), handler(store, TOKEN, {}, career_site=self.site))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}"
            try:
                with urlopen(base + "/career") as response:
                    self.assertTrue(response.url.endswith(self.site.home))
                    self.assertIn("text/html", response.headers["Content-Type"])
                    self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
                with urlopen(base + "/cards") as response:
                    self.assertTrue(response.url.endswith(self.site.cards))
                with urlopen(base + "/contracts") as response:
                    self.assertTrue(response.url.endswith(self.site.contracts))
                    self.assertIn("Player contracts", response.read().decode())
                with urlopen(base + "/career/Dwyane_Wade/Contracts/assets/player_cards.js") as response:
                    self.assertIn("text/javascript", response.headers["Content-Type"])
                    self.assertIn("JSON.parse", response.read().decode())
                with urlopen(base + "/career/Dwyane_Wade/Contracts/assets/player_cards.css") as response:
                    self.assertIn("text/css", response.headers["Content-Type"])
                with urlopen(base + "/career/status") as response:
                    self.assertEqual(json.load(response)["revision"], "test-revision")
                with urlopen(base + "/games") as response:
                    self.assertEqual(json.load(response)["games"], {})
                with self.assertRaises(HTTPError) as error:
                    urlopen(base + "/ready")
                self.assertEqual(error.exception.code, 401)
                with self.assertRaises(HTTPError) as error:
                    urlopen(Request(base + "/corrections?event_id=fake&reason=test", data=b""))
                self.assertEqual(error.exception.code, 401)
                with self.assertRaises(HTTPError) as error:
                    urlopen(base + "/data/engine.sqlite3")
                self.assertEqual(error.exception.code, 404)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
