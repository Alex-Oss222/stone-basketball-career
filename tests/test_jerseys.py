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
        decided = sorted((ROOT / J.request_dirs(ROOT)[0]).glob("*.decision.result.json"))
        if not any('"accept"' in p.read_text(encoding="utf-8") for p in decided):
            self.assertIsNone(number)
        numbers = J.miami_numbers(ROOT)
        held = [n for n in numbers.values() if n]
        self.assertEqual(len(held), len(set(held)))

    def test_wade_takes_the_number_he_waits_for_once_it_is_free(self):
        import json, shutil, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            from runtime.seasons import path as season_path
            register, requests = J.register_path(ROOT), J.request_dirs(ROOT)[0]
            for rel in (register, season_path("2003-04", "jerseys"), J.BASELINE):
                (tmp / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(ROOT / rel, tmp / rel)
            shutil.copytree(ROOT / requests, tmp / requests)
            self.assertEqual(J.wade_number(tmp), (None, None))          # LaPhonso Ellis still wears #3
            data = json.loads((tmp / register).read_text(encoding="utf-8"))
            for p in data["players"]:
                if p["name"] == "LaPhonso Ellis":
                    p["status"] = "contract_expired_released"
            (tmp / register).write_text(json.dumps(data), encoding="utf-8")
            self.assertEqual(J.wade_number(tmp)[0], "3")

    def test_request_packet_is_a_two_way_draw(self):
        packet = J.request_packet("3", "Someone", "2004-04-14", "rookie")
        self.assertAlmostEqual(sum(packet["options"].values()), 1.0)
        self.assertEqual(packet["event_id"], "2003-04-wade-jersey-request-3")


if __name__ == "__main__":
    unittest.main()
