"""scripts/advance.py: the day loop stops whenever Wade has a decision to make, and `--until-champion` stops the day the
NBA Finals are decided."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

from runtime import playoffs
import scripts.advance as A


class AdvanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = Path(self.tmp.name) / "current_state.json"
        self.addCleanup(self.tmp.cleanup)

    def test_a_pending_decision_or_consultation_stops_the_clock(self):
        self.state.write_text(json.dumps({"current_date": "2004-01-22", "pending_player_decisions": ["consultation:x"]}))
        with mock.patch.object(A, "state_file", lambda: self.state), self.assertRaises(A.Stop) as stop:
            A.wade_waits()
        self.assertIn("consultation:x", str(stop.exception))
        self.state.write_text(json.dumps({"current_date": "2004-01-22", "pending_player_decisions": []}))
        with mock.patch.object(A, "state_file", lambda: self.state):
            A.wade_waits()                                       # nothing pending: the day goes on

    def test_the_driver_never_passes_a_seed_or_chooses_an_outcome(self):
        text = Path(A.__file__).read_text()
        body = text.split('"""', 2)[2]
        for name in ("seed_playoffs", "playoffs seeded", "cannot be seeded"):     # playoff seeding (the bracket), not a random seed
            body = body.replace(name, "")
        for word in ("seed", "random", "outcome ="):
            self.assertNotIn(word, body)
        self.assertIn("pending_player_decisions", text)


def series(sid, rnd, clubs, wins=None, clinched_on=None):
    """A bracket series as `runtime/playoffs.py` records it: `wins` by club, the winner once a club has four."""
    wins = dict(zip(clubs, wins or (0, 0)))
    winner = next((c for c, w in wins.items() if w == 4), None)
    return {"id": sid, "round": rnd, "conference": "Finals" if rnd == "finals" else "East", "clubs": list(clubs), "wins": wins,
            "winner": winner, **({"clinched_on": clinched_on} if winner else {})}


def bracket(day, finals_clubs=("Miami Heat", "Dallas Mavericks"), finals_wins=(4, 2)):
    """The 2005-06 record as it stands after `day`: Miami's conference final decided on 2006-06-13 and the Finals on
    2006-06-15 (`finals_clubs` and `finals_wins` in their order)."""
    east = ("Miami Heat", "Detroit Pistons")
    rows = [series("east-final", "conference_finals", east, (4, 2) if day >= "2006-06-13" else (3, 2),
                   "2006-06-13" if day >= "2006-06-13" else None)]
    if day >= "2006-06-13":
        rows.append(series("finals", "finals", finals_clubs, finals_wins if day >= "2006-06-15" else (2, 2),
                           "2006-06-15" if day >= "2006-06-15" else None))
    return {"season": "2005-06", "series": rows, "champion": rows[-1]["winner"] if len(rows) > 1 else None}


class UntilChampionTests(unittest.TestCase):
    """`--until-champion`: main() over stand-in days (no step, commit or push runs; `checkpoint` is recorded)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = Path(self.tmp.name) / "current_state.json"
        self.state.write_text(json.dumps({"current_date": "2006-06-12", "pending_player_decisions": []}))
        A.TRADES_TODAY.clear()
        A.WADE_LONG.clear()

    def drive(self, *flags, finals=None, stop_on=None):
        """main() from the clock's day; the bracket is `bracket(day)` for the day just played (or `finals` built from it)."""
        days, checkpoints, played = [], [], {"day": "2006-06-11"}

        def advance_day(day):
            days.append(day)
            played["day"] = day
            data = json.loads(self.state.read_text())
            data["current_date"] = max(day, data["current_date"])
            self.state.write_text(json.dumps(data))
            if day == stop_on:
                raise A.Stop("Wade has a decision to make: extension:x")

        def read(root=None, season=None):
            return (finals or bracket)(played["day"])
        out = io.StringIO()
        with mock.patch.object(A, "state_file", lambda: self.state), mock.patch.object(A, "advance_day", advance_day), \
                mock.patch.object(A, "checkpoint", lambda day, push=True: checkpoints.append((day, push))), \
                mock.patch.object(playoffs, "read", read), mock.patch.object(sys, "argv", ["advance.py", *flags]), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = A.main()
        return code, days, checkpoints, out.getvalue().splitlines()

    def test_it_runs_past_a_miami_series_and_stops_the_day_the_finals_are_decided(self):
        code, days, checkpoints, lines = self.drive("--until-champion")
        self.assertEqual(code, 0)
        self.assertEqual(days, ["2006-06-12", "2006-06-13", "2006-06-14", "2006-06-15"])     # not stopped on 06-13
        self.assertEqual(checkpoints, [("2006-06-15", True)])                                  # checkpointed and pushed
        self.assertEqual(lines[-1], "DONE: Miami Heat won the 2005-06 NBA championship 4-2 over Dallas Mavericks")

    def test_the_series_end_flag_still_stops_on_the_miami_series(self):
        code, days, checkpoints, lines = self.drive("--series-end", "--to", "2006-06-16")
        self.assertEqual((code, days[-1], checkpoints), (0, "2006-06-13", [("2006-06-13", True)]))
        self.assertTrue(lines[-1].startswith("DONE: conference_finals: Miami Heat won the series 4-2"))

    def test_a_finals_without_miami_stops_too(self):
        code, days, _, lines = self.drive("--until-champion", finals=lambda day: bracket(
            day, ("Detroit Pistons", "San Antonio Spurs"), (3, 4)))
        self.assertEqual((code, days[-1]), (0, "2006-06-15"))
        self.assertEqual(lines[-1], "DONE: San Antonio Spurs won the 2005-06 NBA championship 4-3 over Detroit Pistons")

    def test_to_bounds_the_run_before_the_finals(self):
        code, days, checkpoints, lines = self.drive("--until-champion", "--to", "2006-06-14")
        self.assertEqual((code, days[-1], checkpoints[-1]), (0, "2006-06-14", ("2006-06-14", True)))
        self.assertEqual(lines[-1], "DONE through 2006-06-14")

    def test_a_pending_decision_still_stops_the_run(self):
        code, days, checkpoints, lines = self.drive("--until-champion", stop_on="2006-06-14")
        self.assertEqual((code, days[-1], checkpoints), (1, "2006-06-14", []))
        self.assertEqual(lines[-1], "STOPPED on 2006-06-14: Wade has a decision to make: extension:x")

    def test_finals_decided_before_the_start_stop_at_once(self):
        self.state.write_text(json.dumps({"current_date": "2006-06-16", "pending_player_decisions": []}))
        code, days, checkpoints, lines = self.drive("--until-champion", finals=lambda day: bracket("2006-06-16"))
        self.assertEqual((code, days, checkpoints), (1, [], []))
        self.assertEqual(lines[-1], "STOPPED on 2006-06-16: the Finals were already decided on 2006-06-15: "
                                    "Miami Heat won the 2005-06 NBA championship 4-2 over Dallas Mavericks")

    def test_a_season_change_before_the_finals_stops_the_run(self):
        """A bracket that never names its Finals cannot carry the run into the next season unbounded."""
        seasons = iter(["2005-06", "2005-06", "2005-06", "2006-07"])            # the start, then each day played
        with mock.patch.object(A, "live", lambda: next(seasons, "2006-07")):
            code, days, checkpoints, lines = self.drive("--until-champion", finals=lambda day: bracket("2006-06-12"))
        self.assertEqual((code, days, checkpoints), (1, ["2006-06-12", "2006-06-13", "2006-06-14"], []))
        self.assertEqual(lines[-1], "STOPPED on 2006-06-14: the live season changed from 2005-06 to 2006-07 before its "
                                    "NBA Finals were decided")

    def test_an_unreadable_bracket_at_the_start_is_a_stop(self):
        def broken(day):
            raise ValueError("bad playoffs record")
        code, days, _, lines = self.drive("--until-champion", finals=broken)
        self.assertEqual((code, days), (1, []))
        self.assertEqual(lines[-1], "STOPPED on 2006-06-12: ValueError: bad playoffs record")

    def test_the_flags_exclude_each_other_and_to_is_needed_without_it(self):
        for flags in (("--until-champion", "--series-end"), ()):
            with self.subTest(flags=flags), self.assertRaises(SystemExit) as exit_:
                self.drive(*flags)
            self.assertEqual(exit_.exception.code, 2)

    def test_the_recorded_finals_read_as_the_driver_prints_them(self):
        """The real records name the Finals round `finals` (runtime/playoffs.ROUNDS)."""
        for season, day, line in (("2003-04", "2004-06-20", "Minnesota Timberwolves won the 2003-04 NBA championship 4-3 over New Jersey Nets"),
                                  ("2004-05", "2005-06-16", "Sacramento Kings won the 2004-05 NBA championship 4-0 over Toronto Raptors")):
            record = playoffs.read(A.ROOT, season)
            with self.subTest(season=season), mock.patch.object(playoffs, "read", lambda root=None, season=None: record):
                self.assertEqual(A.champion_decided(day), line)
                self.assertIsNone(A.champion_decided("2004-06-19"))
                self.assertIsNone(A.miami_series_decided(day))


if __name__ == "__main__":
    unittest.main()
