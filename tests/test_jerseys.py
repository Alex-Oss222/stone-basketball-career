"""Uniform numbers: real 2003-04 numbers by club, one holder per number, and Wade's number only from his request."""
from pathlib import Path
import unittest

from runtime import jerseys as J

ROOT = Path(__file__).resolve().parents[1]


class JerseyTests(unittest.TestCase):
    def test_real_numbers_come_from_the_season_file(self):
        self.assertEqual(J.number_for("nowitdi01", "Dallas Mavericks", ROOT), "41")

    def test_the_real_wade_number_is_not_in_the_library(self):
        self.assertEqual(J.candidates("wadedw01", "Miami Heat", ROOT), [])

    def test_a_number_is_held_once_and_a_later_arrival_takes_the_lowest_free(self):
        fake = [("A", None, "Club"), ("B", None, "Club"), ("C", None, "Club")]
        out = J.assign(fake, ROOT, fixed={"A": "0"})
        self.assertEqual(out, {"A": "0", "B": "1", "C": "2"})
        self.assertEqual(len(set(out.values())), 3)

    def test_wade_has_no_number_until_a_request_is_accepted(self):
        number, source = J.wade_number(ROOT)
        decided = sorted((ROOT / J.WADE_REQUESTS).glob("*.decision.result.json"))
        if not any('"accept"' in p.read_text(encoding="utf-8") for p in decided):
            self.assertIsNone(number)
        numbers = J.miami_numbers(ROOT)
        held = [n for n in numbers.values() if n]
        self.assertEqual(len(held), len(set(held)))

    def test_request_packet_is_a_two_way_draw(self):
        packet = J.request_packet("3", "Someone", "2004-04-14", "rookie")
        self.assertAlmostEqual(sum(packet["options"].values()), 1.0)
        self.assertEqual(packet["event_id"], "2003-04-wade-jersey-request-3")


if __name__ == "__main__":
    unittest.main()
