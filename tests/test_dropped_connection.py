"""A connection the engine drops or cuts off mid-reply is transient for the game and draw clients: they report the event
as unreachable (which `scripts/advance.py` waits out and retries; the engine keeps the first result for ever, so sending
the same request again is safe) instead of crashing the step."""
from http.client import IncompleteRead, RemoteDisconnected
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts import draw_decisions, play_games


class DroppedConnectionTests(unittest.TestCase):
    def test_a_cut_off_game_reply_is_unreachable(self):
        request = {"event_id": "2005-11-25-test-game", "game_date": "2005-11-25"}
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(play_games, "pending", return_value=[(Path(tmp) / "Game_1.request.json", request)]), \
                mock.patch.object(play_games, "input_fingerprint", return_value="f"):
            for error in (IncompleteRead(b"x" * 10, 40), RemoteDisconnected("closed"), ConnectionResetError("reset")):
                def send(body, error=error):
                    raise error
                (event, status), = play_games.play_pending(Path(tmp), token="t", send=send)
                self.assertEqual(event, "2005-11-25-test-game")
                self.assertTrue(status.startswith("unreachable"), status)

    def test_a_cut_off_draw_reply_is_unreachable(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.decision.json"
            path.write_text(json.dumps({"event_id": "draw-1"}), encoding="utf-8")

            def send(data):
                raise IncompleteRead(b"", 10)
            with mock.patch.object(draw_decisions, "find_decisions", return_value=[path]), \
                    mock.patch.object(draw_decisions, "load_decision", return_value={"event_id": "draw-1"}):
                report = draw_decisions.draw_pending(Path(tmp), token="t", send=send)
        self.assertEqual(report[0][0], "draw-1")
        self.assertTrue(report[0][1].startswith("unreachable"), report)


if __name__ == "__main__":
    unittest.main()
