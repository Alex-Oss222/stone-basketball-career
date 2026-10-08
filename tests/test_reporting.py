"""Reporting: Miami's summer-market news (`scripts/offseason_day.py`) and the driver (`scripts/advance.py`) treating a
summer MIAMI TRADE like an in-season one; a failing step's own output printed before the stop."""
import contextlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import scripts.advance as A
import scripts.offseason_day as O
from runtime import free_agency_2004 as fa

ROOT = Path(__file__).resolve().parents[1]
DAY = "2006-07-14"
TRADE_ID = f"2006-summer-trade-{DAY}-jonesed02-smithjr01-wrighdo01"

# A fixture market record: the day's events as `runtime/free_agency_2004.Market` writes them, plus events of another
# day and of other clubs that must print nothing.
EVENTS = [
    {"date": DAY, "kind": "trade", "player": "Dorell Wright", "bbr_id": "wrighdo01", "club": "Utah Jazz", "from": "Miami Heat",
     "salary": 1052040, "deal": TRADE_ID},
    {"date": DAY, "kind": "trade", "player": "Eddie Jones", "bbr_id": "jonesed02", "club": "Miami Heat", "from": "Utah Jazz",
     "salary": 14576250, "deal": TRADE_ID},
    {"date": DAY, "kind": "trade", "player": "J.R. Smith", "bbr_id": "smithjr01", "club": "Miami Heat", "from": "Utah Jazz",
     "salary": 1500000, "deal": TRADE_ID},
    {"date": DAY, "kind": "trade", "player": "Other One", "bbr_id": "otherx01", "club": "Boston Celtics", "from": "Utah Jazz",
     "salary": 1, "deal": f"2006-summer-trade-{DAY}-otherx01-othery01"},
    {"date": DAY, "kind": "trade", "player": "Other Two", "bbr_id": "othery01", "club": "Utah Jazz", "from": "Boston Celtics",
     "salary": 1, "deal": f"2006-summer-trade-{DAY}-otherx01-othery01"},
    # Miami's offer sheet, matched by the holder
    {"date": DAY, "kind": "offer_sheet", "player": "Salim Stoudamire", "bbr_id": "stoudsa01", "club": "Miami Heat",
     "from": "New York Knicks", "salary": 398762, "years": 1},
    {"date": DAY, "kind": "offer_sheet_matched", "player": "Salim Stoudamire", "bbr_id": "stoudsa01", "club": "New York Knicks",
     "from": "Miami Heat", "salary": 398762, "years": 1, "route": "minimum"},
    # Miami's offer sheet, not matched: the signing that follows is folded into the offer-sheet line
    {"date": DAY, "kind": "offer_sheet", "player": "Mehmet Okur", "bbr_id": "okurme01", "club": "Miami Heat",
     "from": "Detroit Pistons", "salary": 2827619, "years": 5},
    {"date": DAY, "kind": "offer_sheet_not_matched", "player": "Mehmet Okur", "bbr_id": "okurme01", "club": "Detroit Pistons",
     "to": "Miami Heat"},
    {"date": DAY, "kind": "signing", "player": "Mehmet Okur", "bbr_id": "okurme01", "club": "Miami Heat", "from": "Detroit Pistons",
     "salary": 2827619, "years": 5, "route": "mid_level", "agreed": DAY},
    # another club's sheet to Miami's restricted player: Miami matches one and lets one go
    {"date": DAY, "kind": "offer_sheet", "player": "Udonis Haslem", "bbr_id": "hasleud01", "club": "Toronto Raptors",
     "from": "Miami Heat", "salary": 5000000, "years": 5},
    {"date": DAY, "kind": "offer_sheet_matched", "player": "Udonis Haslem", "bbr_id": "hasleud01", "club": "Miami Heat",
     "from": "Toronto Raptors", "salary": 5000000, "years": 5, "route": "bird"},
    {"date": DAY, "kind": "offer_sheet", "player": "Wayne Simien", "bbr_id": "simiewa01", "club": "Atlanta Hawks",
     "from": "Miami Heat", "salary": 1200000, "years": 3},
    {"date": DAY, "kind": "offer_sheet_not_matched", "player": "Wayne Simien", "bbr_id": "simiewa01", "club": "Miami Heat",
     "to": "Atlanta Hawks"},
    {"date": DAY, "kind": "signing", "player": "Wayne Simien", "bbr_id": "simiewa01", "club": "Atlanta Hawks", "from": "Miami Heat",
     "salary": 1200000, "years": 3, "route": "cap_room", "agreed": DAY},
    # signings, a loss and a renunciation
    {"date": DAY, "kind": "signing", "player": "Matt Carroll", "bbr_id": "carroma01", "club": "Miami Heat", "from": "Chicago Bulls",
     "salary": 719373, "years": 1, "route": "minimum", "agreed": "2006-07-01"},
    {"date": DAY, "kind": "re_sign", "player": "Matt Harpring", "bbr_id": "harprma01", "club": "Miami Heat", "from": "Miami Heat",
     "salary": 7954111, "years": 4, "route": "bird", "agreed": DAY},
    {"date": DAY, "kind": "signing", "player": "Maurice Evans", "bbr_id": "evansma01", "club": "Golden State Warriors",
     "from": "Miami Heat", "salary": 771123, "years": 1, "route": "minimum", "agreed": DAY},
    {"date": DAY, "kind": "renounce", "player": "John Thomas", "bbr_id": "thomajo02", "club": "Miami Heat", "hold": 1500000,
     "value": 3.2, "for": "Andrei Kirilenko", "for_bbr_id": "kirilan01", "offer": 9000000, "qualifying_offer_withdrawn": 900000},
    # no roster change on the day, or not the day, or not Miami
    {"date": DAY, "kind": "qualifying_offer", "player": "Udonis Haslem", "bbr_id": "hasleud01", "club": "Miami Heat",
     "amount": 795046, "price": 620046},
    {"date": "2006-07-07", "kind": "signing", "player": "Eddie Gill", "bbr_id": "gilled01", "club": "Miami Heat", "from": None,
     "salary": 835810, "years": 1, "route": "minimum", "agreed": "2006-07-07"},
    {"date": DAY, "kind": "signing", "player": "Nobody Else", "bbr_id": "nobodx01", "club": "Boston Celtics", "from": "Utah Jazz",
     "salary": 1, "years": 1, "route": "minimum", "agreed": DAY},
]

TRADE_LINE = f"MIAMI TRADE: Utah Jazz accepts: Miami sends Dorell Wright for Eddie Jones, J.R. Smith ({TRADE_ID})"
IN_SEASON = re.compile(r"^MIAMI TRADE: (?P<partner>.+) accepts: Miami sends (?P<outs>.+) for (?P<ins>.+) \((?P<id>[^()]+)\)$")


class MarketNewsTests(unittest.TestCase):
    def test_each_miami_roster_change_of_the_day_prints_one_line(self):
        self.assertEqual(O.miami_news(EVENTS, DAY), [
            "MIAMI OFFER SHEET: Detroit Pistons does not match Miami's offer sheet to Mehmet Okur: he signs with Miami, "
            "$2,827,619 for 5 years, mid level",
            "MIAMI OFFER SHEET: New York Knicks matches Miami's offer sheet to Salim Stoudamire ($398,762 for 1 year); "
            "he stays with New York Knicks",
            "MIAMI OFFER SHEET: Miami matches the Toronto Raptors offer sheet to Udonis Haslem ($5,000,000 for 5 years, bird); "
            "he stays with Miami",
            "MIAMI LOSES: Miami does not match the Atlanta Hawks offer sheet to Wayne Simien ($1,200,000 for 3 years); "
            "he signs with Atlanta Hawks",
            "MIAMI SIGNING: Miami re-signs Matt Harpring, $7,954,111 for 4 years, bird",
            "MIAMI LOSES: Miami renounces John Thomas's $1,500,000 cap hold for its $9,000,000 offer to Andrei Kirilenko; "
            "its $900,000 qualifying offer is withdrawn",
            "MIAMI SIGNING: Miami signs Matt Carroll (from Chicago Bulls), $719,373 for 1 year, minimum, agreed 2006-07-01",
            "MIAMI LOSES: Maurice Evans, Miami's free agent, signs with Golden State Warriors, $771,123 for 1 year, minimum",
            TRADE_LINE,
        ])

    def test_a_summer_trade_line_is_the_in_season_format(self):
        trades = [line for line in O.miami_news(EVENTS, DAY) if line.startswith("MIAMI TRADE")]
        self.assertEqual(trades, [TRADE_LINE])                       # one line a deal; the other clubs' deal prints nothing
        m = IN_SEASON.match(trades[0])
        self.assertEqual((m["partner"], m["outs"], m["ins"], m["id"]), ("Utah Jazz", "Dorell Wright", "Eddie Jones, J.R. Smith", TRADE_ID))
        # the same head as scripts/run_trade.season_day's completed trade
        self.assertIn('head = "MIAMI TRADE" if status == "completed"', (ROOT / "scripts/run_trade.py").read_text(encoding="utf-8"))
        self.assertIn("{head}: {t['partner']} {'accepts' if status == 'completed' else 'answers'}: Miami sends {outs} for {ins} ({trade_id})",
                      (ROOT / "scripts/run_trade.py").read_text(encoding="utf-8"))

    def test_only_the_day_and_known_prefixes(self):
        self.assertEqual(O.miami_news(EVENTS, "2006-07-07"), ["MIAMI SIGNING: Miami signs Eddie Gill, $835,810 for 1 year, minimum"])
        self.assertEqual(O.miami_news(EVENTS, "2006-07-21"), [])
        self.assertEqual(A.MARKET_NEWS, O.NEWS)                     # the driver reads what the announcer prints
        self.assertTrue(all(line.startswith(O.NEWS) for line in O.miami_news(EVENTS, DAY)))

    @unittest.skipUnless((ROOT / fa.record_path(2005)).is_file(), "the 2005 market record")
    def test_the_recorded_2005_summer_announces_its_two_miami_trades(self):
        events = json.loads((ROOT / fa.record_path(2005)).read_text(encoding="utf-8"))["events"]
        trades = [line for day in sorted({e["date"] for e in events}) for line in O.miami_news(events, day) if line.startswith("MIAMI TRADE")]
        self.assertEqual(len(trades), 2)
        self.assertTrue(all(IN_SEASON.match(line) for line in trades))

    def test_the_script_prints_the_lines(self):
        out = io.StringIO()
        shifted = [dict(e, date="2005-08-05") if e["date"] == DAY else e for e in EVENTS]
        with mock.patch.object(sys, "argv", ["offseason_day.py", "--write", "2005-08-05"]), \
                mock.patch.object(O.lottery, "run", return_value=None), \
                mock.patch.object(O.draft, "run", return_value=None), \
                mock.patch.object(O.draft_rights, "end_rights", return_value=[]), \
                mock.patch.object(O.draft_rights, "record_tenders", return_value=[]), \
                mock.patch.object(O, "summer_market", return_value=(None, shifted)) as market, \
                contextlib.redirect_stdout(out):
            self.assertEqual(O.main(), 0)
        market.assert_called_once_with("2005-08-05", 2005)
        lines = out.getvalue().splitlines()
        self.assertEqual([line for line in lines if line.startswith(O.NEWS)], O.miami_news(shifted, "2005-08-05"))
        self.assertEqual(len(O.miami_news(shifted, "2005-08-05")), 9)
        self.assertIn(TRADE_LINE, lines)
        self.assertEqual(lines[-1], "offseason events checked for 2005-08-05")


class FakeMarket:
    """Stands in for `free_agency_2004.Market`: an event a round, the record at placement."""

    def __init__(self, root, clock):
        self.clock = clock
        self.events = [{"date": d, "kind": "signing", "player": f"P {d}", "club": "Miami Heat"} for d in ("2004-07-14", "2004-07-21")
                       if d <= clock]

    def run(self):
        return {"kind": "free_agency", "events": self.events} if self.clock >= "2004-09-30" else None


class SummerMarketTests(unittest.TestCase):
    """`offseason_day.summer_market` is `free_agency_2004.run` step for step, keeping the replay's dated events."""

    def test_replay_events_before_the_record_then_the_record(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b, mock.patch.object(fa, "Market", FakeMarket):
            with mock.patch.object(O, "ROOT", Path(a)):
                self.assertEqual(O.summer_market("2004-06-29", 2004), (None, []))
                record, events = O.summer_market("2004-07-21", 2004)
                self.assertIsNone(record)
                self.assertEqual([e["date"] for e in events], ["2004-07-14", "2004-07-21"])
                self.assertFalse((Path(a) / fa.RECORD).exists())                       # nothing written mid-summer
                record, events = O.summer_market("2004-09-30", 2004)
                self.assertEqual(record["events"], events)
                again = O.summer_market("2004-10-01", 2004)                              # read from the written record
                self.assertEqual(again, (None, events))
            self.assertIsNone(fa.run(Path(b), "2004-07-21", year=2004))
            self.assertEqual(fa.run(Path(b), "2004-09-30", year=2004), record)
            self.assertEqual((Path(a) / fa.RECORD).read_text(encoding="utf-8"), (Path(b) / fa.RECORD).read_text(encoding="utf-8"))


class DriverTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = Path(self.tmp.name) / "current_state.json"
        self.state.write_text(json.dumps({"current_date": "2006-07-13", "pending_player_decisions": []}))
        A.TRADES_TODAY.clear()
        A.WADE_LONG.clear()
        self.addCleanup(A.TRADES_TODAY.clear)
        self.addCleanup(A.WADE_LONG.clear)

    def offseason_output(self):
        return "\n".join(["offseason events checked for " + DAY] + O.miami_news(EVENTS, DAY))

    def test_playoff_day_reports_the_market_and_takes_its_trade(self):
        def fake_run(*args, ok=(0,), show=True):
            return self.offseason_output() if args[0] == "scripts/offseason_day.py" else ""
        out = io.StringIO()
        with mock.patch.object(A, "state_file", lambda: self.state), mock.patch.object(A, "run", fake_run), \
                mock.patch.multiple(A, option_day=mock.DEFAULT, draw=mock.DEFAULT, seed_playoffs=mock.DEFAULT,
                                    national_day=mock.DEFAULT, wade_waits=mock.DEFAULT, play=mock.DEFAULT), \
                mock.patch.object(A, "draws_pending", return_value=False), contextlib.redirect_stdout(out):
            A.playoff_day(DAY)
        lines = out.getvalue().splitlines()
        self.assertEqual(lines[0], "    offseason events checked for " + DAY)
        self.assertEqual([line.strip() for line in lines[1:]], O.miami_news(EVENTS, DAY))
        self.assertEqual(A.TRADES_TODAY, [TRADE_LINE])

    def test_in_season_and_summer_trades_reach_the_same_list(self):
        with mock.patch.object(A, "run", return_value=TRADE_LINE), mock.patch.object(A, "draws_pending", return_value=False), \
                contextlib.redirect_stdout(io.StringIO()):
            A.miami_trade_day(DAY)
            in_season = list(A.TRADES_TODAY)
            A.TRADES_TODAY.clear()
            A.market_news(self.offseason_output())
        self.assertEqual(A.TRADES_TODAY, in_season)

    def drive(self, *flags, then=None):
        """main() over three days, the middle one a summer day whose market made a Miami trade (`then` raised after it)."""
        days, checkpoints = [], []

        def advance_day(day):
            days.append(day)
            data = json.loads(self.state.read_text())
            data["current_date"] = max(day, data["current_date"])
            self.state.write_text(json.dumps(data))
            if day == DAY:
                A.market_news(self.offseason_output())
                if then:
                    raise then
        out = io.StringIO()
        with mock.patch.object(A, "state_file", lambda: self.state), mock.patch.object(A, "advance_day", advance_day), \
                mock.patch.object(A, "checkpoint", lambda day, push=True: checkpoints.append((day, push))), \
                mock.patch.object(sys, "argv", ["advance.py", "--to", "2006-07-15", *flags]), contextlib.redirect_stdout(out):
            code = A.main()
        return code, days, checkpoints, out.getvalue()

    def test_a_summer_trade_stops_the_run_by_default(self):
        code, days, checkpoints, out = self.drive()
        self.assertEqual((code, days, checkpoints), (0, ["2006-07-13", DAY], [(DAY, True)]))
        self.assertIn("DONE: " + TRADE_LINE, out.splitlines())
        self.assertEqual(json.loads(self.state.read_text())["reported_stop"], {"date": DAY, "lines": [TRADE_LINE]})
        # resuming on the clock's day reports the trade again but does not stop on it a second time
        code, days, checkpoints, out = self.drive()
        self.assertEqual((code, days, checkpoints), (0, [DAY, "2006-07-15"], [("2006-07-15", True)]))
        self.assertIn("    " + TRADE_LINE, out.splitlines())
        self.assertIn("DONE through 2006-07-15", out.splitlines())

    def test_another_stop_that_day_repeats_the_trade_and_the_resumed_day_stops_on_it(self):
        code, days, checkpoints, out = self.drive(then=A.Stop("Wade has a decision to make: consultation:x"))
        lines = out.splitlines()
        self.assertEqual((code, days, checkpoints), (1, ["2006-07-13", DAY], []))
        self.assertEqual(lines[-2:], ["Miami news of the day before the stop: " + TRADE_LINE,
                                      f"STOPPED on {DAY}: Wade has a decision to make: consultation:x"])
        code, days, checkpoints, out = self.drive()                 # Wade answered: the trade's own stop comes now
        self.assertEqual((code, days, checkpoints), (0, [DAY], [(DAY, True)]))
        self.assertIn("DONE: " + TRADE_LINE, out.splitlines())

    def test_through_trades_reports_and_goes_on(self):
        code, days, checkpoints, out = self.drive("--through-trades")
        self.assertEqual((code, days, checkpoints), (0, ["2006-07-13", DAY, "2006-07-15"], [("2006-07-15", True)]))
        self.assertEqual(out.splitlines().count("    " + TRADE_LINE), 1)
        self.assertNotIn("reported_stop", json.loads(self.state.read_text()))
        self.assertIn("DONE through 2006-07-15", out.splitlines())

    def test_an_exception_inside_the_driver_prints_its_whole_traceback(self):
        def boom(day):
            cause = None
            for i in range(15):                                      # a chain far longer than FAIL_TAIL lines, its root on top
                try:
                    raise KeyError(f"cause {i}") from cause
                except KeyError as exc:
                    cause = exc
            raise RuntimeError("continuity: Eddie Jones on two clubs") from cause
        out = io.StringIO()
        with mock.patch.object(A, "state_file", lambda: self.state), mock.patch.object(A, "advance_day", boom), \
                mock.patch.object(sys, "argv", ["advance.py", "--to", "2006-07-15"]), contextlib.redirect_stdout(out):
            self.assertEqual(A.main(), 1)
        lines = out.getvalue().splitlines()
        self.assertGreater(len(lines), A.FAIL_TAIL + 20)
        self.assertEqual(lines[0], "    Traceback (most recent call last):")               # the root cause's own head
        self.assertIn("    KeyError: 'cause 0'", lines)
        self.assertIn("    The above exception was the direct cause of the following exception:", lines)
        self.assertIn("    RuntimeError: continuity: Eddie Jones on two clubs", lines)
        self.assertEqual(lines[-1], "STOPPED on 2006-07-13: RuntimeError: continuity: Eddie Jones on two clubs")


class RunOutputTests(unittest.TestCase):
    STDOUT = "\n".join(f"line {i}" for i in range(60))
    STDERR = "runtime.continuity.ContinuityError: Eddie Jones is on two clubs"

    def call(self, code, **kw):
        done = subprocess.CompletedProcess(["python"], code, stdout=self.STDOUT + "\n", stderr=self.STDERR + "\n")
        out = io.StringIO()
        with mock.patch.object(A.subprocess, "run", return_value=done), contextlib.redirect_stdout(out):
            try:
                result = A.run("scripts/rollover.py", "--write", **kw)
            except A.Stop as stop:
                result = stop
        return result, out.getvalue().splitlines()

    def test_a_failing_step_prints_its_last_lines_shown_or_not(self):
        for show in (True, False):
            stop, lines = self.call(1, show=show)
            self.assertIsInstance(stop, A.Stop)
            self.assertEqual(str(stop), "scripts/rollover.py --write exited 1")
            self.assertEqual(len(lines), A.FAIL_TAIL)
            self.assertEqual(lines[0], "    line 21")
            self.assertEqual(lines[-1], "    " + self.STDERR)

    def test_a_passing_step_keeps_its_twelve_lines(self):
        out, lines = self.call(0)
        self.assertEqual(out, self.STDOUT + "\n" + self.STDERR)
        self.assertEqual(lines, ["    " + line for line in out.splitlines()[-12:]])
        _, lines = self.call(1, ok=(0, 1), show=False)                 # an accepted code is not a failure
        self.assertEqual(lines, [])


GAME = "2005-11-01-miami-heat-memphis-grizzlies"
CRASH = "\n".join(["Traceback (most recent call last):"]
                  + [f'  File "scripts/play_games.py", line {i}, in play_pending' for i in range(50)]
                  + ["KeyError: 'frozen'"])


class PlayTests(unittest.TestCase):
    """`advance.play`: a games step that did not finish is not an engine refusal; it stops at once with its error."""

    def drive(self, stdout, stderr="", code=1):
        calls, checkpoints, sleeps = [], [], []

        def fake(cmd, **kw):
            calls.append(cmd[1])
            if cmd[1] == "scripts/play_games.py":
                return subprocess.CompletedProcess(cmd, code, stdout=stdout, stderr=stderr)
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        out = io.StringIO()
        with mock.patch.object(A.subprocess, "run", fake), mock.patch.object(A, "checkpoint", lambda day: checkpoints.append(day)), \
                mock.patch.object(A.time, "sleep", sleeps.append), contextlib.redirect_stdout(out):
            try:
                result = A.play("2005-11-01")
            except A.Stop as stop:
                result = stop
        return result, out.getvalue().splitlines(), calls, checkpoints, sleeps

    def test_a_crash_stops_at_once_with_its_error_and_no_push(self):
        stop, lines, calls, checkpoints, sleeps = self.drive("", CRASH)
        self.assertEqual(str(stop), "scripts/play_games.py 2005-11-01 did not finish: KeyError: 'frozen'")
        self.assertEqual(len(lines), A.FAIL_TAIL)
        self.assertEqual(lines[-1], "    KeyError: 'frozen'")
        self.assertEqual((calls, checkpoints, sleeps), (["scripts/play_games.py"], [], []))    # no push, no wait

    def test_a_missing_token_stops_at_once(self):
        stop, lines, _, checkpoints, sleeps = self.drive("", "ENGINE_API_TOKEN is not set")
        self.assertIn("did not finish: ENGINE_API_TOKEN is not set", str(stop))
        self.assertEqual((lines, checkpoints, sleeps), (["    ENGINE_API_TOKEN is not set"], [], []))

    def test_a_played_day_reports_its_closing_line_whatever_stderr_adds(self):
        result, lines, _, checkpoints, _ = self.drive(f"played         {GAME}\n1 of 1 game(s) written\n",
                                                      "DeprecationWarning: something old", code=0)
        self.assertIsNone(result)
        self.assertEqual((lines, checkpoints), (["    1 of 1 game(s) written"], []))

    def test_an_engine_refusal_still_pushes_once_then_prints_its_tail(self):
        refusal = f"refused 409: input fingerprint differs {GAME}\n0 of 1 game(s) written\n"
        stop, lines, calls, checkpoints, sleeps = self.drive(refusal)
        self.assertEqual(checkpoints, ["2005-11-01"])                                       # one push so the engine redeploys
        self.assertEqual(calls.count("scripts/write_back_results.py"), 1)
        self.assertEqual(len(sleeps), 40)
        self.assertEqual(str(stop), f"games still refused after the push: refused 409: input fingerprint differs {GAME}")
        self.assertEqual(lines[-2:], [f"    refused 409: input fingerprint differs {GAME}", "    0 of 1 game(s) written"])


class CheckpointOutputTests(unittest.TestCase):
    def test_a_failed_push_prints_the_push_refusal_not_the_quiet_merge(self):
        rejected = "To origin\n ! [rejected]        HEAD -> milestone-1 (fetch first)\nerror: failed to push some refs"

        def fake_git(*args):
            return {"push": (1, rejected), "diff": (0, "")}.get(args[0], (0, ""))       # every merge clean and silent

        def fake_run(*args, ok=(0,), show=True):
            return {"scripts/reconcile.py": "validation passed", "scripts/audit_journal.py": "no problems",
                    "scripts/run_tests.py": "Ran 3 tests\n\nOK", "scripts/validate_repository.py": "validation passed"}[args[0]]
        out = io.StringIO()
        with mock.patch.object(A, "git", fake_git), mock.patch.object(A, "run", fake_run), \
                mock.patch.object(A.time, "sleep", lambda s: None), contextlib.redirect_stdout(out), \
                self.assertRaises(A.Stop) as stop:
            A.checkpoint("2005-11-01")
        self.assertEqual(str(stop.exception), "push failed")
        self.assertEqual(out.getvalue().splitlines()[-3:], ["    " + line for line in rejected.splitlines()])

    def test_frozen_input_differences_print_their_tail(self):
        problems = "\n".join(f"{GAME}-{i}: frozen inputs differ (miami.players)" for i in range(45))
        out = io.StringIO()
        with mock.patch.object(A, "run", return_value=problems), contextlib.redirect_stdout(out), \
                self.assertRaises(A.Stop) as stop:
            A.frozen_check()
        lines = out.getvalue().splitlines()
        self.assertEqual(len(lines), A.FAIL_TAIL)
        self.assertEqual(lines[-1], f"    {GAME}-44: frozen inputs differ (miami.players)")
        self.assertEqual(str(stop.exception), "frozen inputs differ from the records: " + "; ".join(problems.splitlines()[:3]))
        with mock.patch.object(A, "run", return_value=""):
            A.frozen_check()                                                                # nothing differs: the day goes on
        text = Path(A.__file__).read_text(encoding="utf-8")
        self.assertEqual(text.count("import frozen_errors"), 1)                             # one check, called by every day type
        self.assertEqual(text.count("    frozen_check()"), 3)


DRAFT = {"date": "2006-06-28", "picks": [
    {"pick": 9, "round": 1, "club": "Boston Celtics", "player": "Someone Else", "position": "C"},
    {"pick": 12, "round": 1, "club": "Miami Heat", "player": "Rudy Gay", "position": "SF"},
    {"pick": 44, "round": 2, "club": "Miami Heat", "player": "Paul Davis", "position": "C"},
    {"pick": 45, "round": 2, "club": "Utah Jazz", "player": "Third Man", "position": "PG"}],
    "trades": [{"slot": 10, "from": "Golden State Warriors", "to": "Denver Nuggets", "for_slot": 14,
                "plus": "Denver Nuggets 2007 second-round pick"},
               {"slot": 12, "from": "Boston Celtics", "to": "Miami Heat", "for_slot": 15, "plus": "Miami Heat 2007 second-round pick"},
               {"slot": 40, "from": "Miami Heat", "to": "Utah Jazz", "for_slot": 44, "plus": "Utah Jazz 2007 second-round pick"}]}


class DraftNewsTests(unittest.TestCase):
    """Draft night's Miami picks and trades, read from the draft record on every run of the draft date."""

    UP = "MIAMI TRADE: Boston Celtics accepts: Miami sends No. 15, Miami Heat 2007 second-round pick for No. 12 (2006-draft-pick-12-trade-down)"
    DOWN = ("MIAMI TRADE: Utah Jazz offered and Miami accepts: Miami sends No. 40 for No. 44, Utah Jazz 2007 second-round pick "
            "(2006-draft-pick-40-trade-down)")

    def test_miami_picks_and_trades_in_slot_order(self):
        self.assertEqual(O.draft_news(DRAFT, 2006), [self.UP, "MIAMI DRAFT: Miami selects Rudy Gay (SF) at No. 12", self.DOWN,
                                                     "MIAMI DRAFT: Miami selects Paul Davis (C) at No. 44"])
        self.assertTrue(all(IN_SEASON.match(line) for line in (self.UP, self.DOWN)))
        self.assertEqual(O.draft_news(None, 2006), [])
        self.assertIn("MIAMI DRAFT", A.MARKET_NEWS)

    def test_the_record_is_read_on_the_draft_date_only(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(O, "ROOT", Path(tmp)), \
                mock.patch.object(O.draft, "DRAFT_DATE", DRAFT["date"]):
            self.assertIsNone(O.draft_night(DRAFT["date"]))                                # no record yet
            path = Path(tmp) / O.draft.RECORD
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(DRAFT), encoding="utf-8")
            self.assertEqual(O.draft_night(DRAFT["date"]), DRAFT)
            self.assertIsNone(O.draft_night("2006-06-29"))

    def script(self, made, night):
        out = io.StringIO()
        with mock.patch.object(sys, "argv", ["offseason_day.py", "--write", "2005-06-28"]), \
                mock.patch.object(O.lottery, "run", return_value=None), \
                mock.patch.object(O.draft, "run", return_value=made), \
                mock.patch.object(O, "draft_night", return_value=night) as reader, \
                mock.patch.object(O.draft_rights, "end_rights", return_value=[]), \
                mock.patch.object(O.draft_rights, "record_tenders", return_value=[]), \
                mock.patch.object(O, "summer_market", return_value=(None, [])), contextlib.redirect_stdout(out):
            self.assertEqual(O.main(), 0)
        return out.getvalue().splitlines(), reader

    def test_every_run_of_draft_day_prints_the_news(self):
        news = O.draft_news(DRAFT, 2005)
        lines, reader = self.script(None, DRAFT)                                   # a later run: the record already exists
        self.assertEqual(lines, news + ["offseason events checked for 2005-06-28"])
        reader.assert_called_once_with("2005-06-28")
        lines, reader = self.script(DRAFT, None)                                   # the run that completed the draft
        self.assertEqual(lines, news + ["2005 draft complete: 4 picks, 3 draft-night trade(s)", "offseason events checked for 2005-06-28"])
        reader.assert_not_called()

    def test_the_driver_reports_the_picks_and_stops_on_the_trades(self):
        out = "\n".join(O.draft_news(DRAFT, 2006) + ["offseason events checked for 2006-06-28"])
        A.TRADES_TODAY.clear()
        self.addCleanup(A.TRADES_TODAY.clear)
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            A.market_news(out)
        self.assertEqual(A.TRADES_TODAY, [self.UP, self.DOWN])
        self.assertEqual([line.strip() for line in printed.getvalue().splitlines()], O.draft_news(DRAFT, 2006))

    def test_the_recorded_drafts_announce_miami_picks_only(self):
        for year, season in ((2004, "2003-04"), (2005, "2004-05")):
            path = ROOT / f"career/Dwyane_Wade/{season}/09_Draft/draft_{year}.json"
            if not path.is_file():
                continue
            record = json.loads(path.read_text(encoding="utf-8"))
            lines = O.draft_news(record, year)
            self.assertEqual(lines, [f"MIAMI DRAFT: Miami selects {p['player']} ({p['position']}) at No. {p['pick']}"
                                     for p in record["picks"] if p["club"] == "Miami Heat"])
            self.assertFalse(any("Miami Heat" in (t["from"], t["to"]) for t in record["trades"]))   # no Miami trade that night


if __name__ == "__main__":
    unittest.main()
