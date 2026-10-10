"""Wade's keep_picks request and the trade request it promises (runtime/keep_picks.py; the user's words, 2006-04-19).

The rule's tests run on stand-in desks, synthetic draft nights (the harness of `tests/test_draft_requests.py`) and
temporary roots. The replay tests read the live records (read-only): every recorded trade, offer and draft is dated
before the request and nothing reads it there; the desk's hook adds nothing to the one recorded pick trade's score.
"""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from runtime import draft as D, keep_picks as K, signing, trades
from tests.test_draft_requests import Draft, Engine, pool_of

ROOT = Path(__file__).resolve().parents[1]
REQUEST_DATE = "2006-04-19"
WORDS = "if they trade one more pick i am asking for a trade keep the fucking picks mfers"
LIVE = "career/Dwyane_Wade/2005-06/04_Training_Camp/wade_requests.json"


def keep_row(date=REQUEST_DATE, requested="keep", **extra):
    return dict({"date": date, "subject": "keep_picks", "player": "Dwyane Wade", "bbr_id": "wadedw01", "requested": requested,
                 "if_ignored": "trade_request", "words": WORDS, "note": "test", "source_ref": "test"}, **extra)


class Root:
    """A temporary career with request files, a season state and notes."""

    def __init__(self, testcase, season="2005-06", clock="2006-12-18"):
        tmp = tempfile.TemporaryDirectory()
        testcase.addCleanup(tmp.cleanup)
        self.root, self.season = Path(tmp.name), season
        self.write(f"career/Dwyane_Wade/{season}/current_state.json",
                   {"season": season, "current_date": clock, "current_note": "04_Training_Camp/note.md", "pending_player_decisions": []})
        for phase in ("04_Training_Camp", "09_Draft"):
            note = self.root / f"career/Dwyane_Wade/{season}/{phase}/note.md"
            note.parent.mkdir(parents=True, exist_ok=True)
            note.write_text("---\ntype: phase\nstatus: active\n---\n\n# Phase\n\n## Events\n\n## Consequences\n", encoding="utf-8")

    def write(self, rel, data):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=1), encoding="utf-8")
        return path

    def requests(self, rel, *rows):
        return self.write(rel, {"requests": list(rows)})

    def state(self):
        return json.loads((self.root / f"career/Dwyane_Wade/{self.season}/current_state.json").read_text())


class StandingRequestTests(unittest.TestCase):
    def test_nothing_stands_before_the_request_date(self):
        self.assertIsNone(K.standing_request("2006-04-18", ROOT))
        live = K.standing_request(REQUEST_DATE, ROOT)
        self.assertEqual((live["path"], live["date"], live["words"], live["if_ignored"]), (LIVE, REQUEST_DATE, WORDS, "trade_request"))

    def test_it_stands_in_later_seasons_from_where_it_was_filed(self):
        r = Root(self)
        r.requests(LIVE, keep_row())
        r.requests("career/Dwyane_Wade/2006-07/04_Training_Camp/wade_requests.json",
                   {"date": "2006-10-31", "subject": "trade_target", "player": "Someone", "requested": "pursue"})
        for day in ("2006-06-28", "2006-12-18", "2010-02-01"):
            self.assertEqual(K.standing_request(day, r.root)["path"], LIVE, day)

    def test_a_later_row_withdraws_it_and_a_later_keep_restores_it(self):
        r = Root(self)
        r.requests(LIVE, keep_row())
        r.requests("career/Dwyane_Wade/2006-07/03_Offseason/wade_requests.json", keep_row("2006-08-01", "withdraw"),
                   keep_row("2007-01-05"))
        self.assertIsNotNone(K.standing_request("2006-07-31", r.root))
        self.assertIsNone(K.standing_request("2006-08-01", r.root))
        self.assertIsNone(K.standing_request("2007-01-04", r.root))
        self.assertEqual(K.standing_request("2007-01-05", r.root)["date"], "2007-01-05")

    def test_the_live_request_validates(self):
        self.assertEqual(K.request_errors(ROOT), [])


class ScoreTests(unittest.TestCase):
    def test_at_franchise_standing_a_pick_needs_five_times_the_threshold(self):
        self.assertAlmostEqual(K.scored(0.5, 0.8), trades.IN_SEASON_MIN_GAIN)
        self.assertLess(K.scored(0.49, 0.8), trades.IN_SEASON_MIN_GAIN)
        self.assertGreater(K.scored(0.8, 0.8), trades.IN_SEASON_MIN_GAIN)        # weighed, never a veto
        self.assertAlmostEqual(K.scored(-0.2, 0.8), -0.2 * 1.8)

    def test_at_a_low_standing_a_smaller_gain_still_clears(self):
        self.assertAlmostEqual(K.scored(0.125, 0.2), trades.IN_SEASON_MIN_GAIN)
        self.assertLess(K.scored(0.12, 0.2), trades.IN_SEASON_MIN_GAIN)

    def test_no_standing_makes_it_a_veto(self):
        from runtime.standing import STANDING_WEIGHT
        for standing, w in STANDING_WEIGHT.items():
            self.assertGreaterEqual(K.scored(trades.IN_SEASON_MIN_GAIN / (1 - w) + 1e-9, w), trades.IN_SEASON_MIN_GAIN, standing)

    def test_his_own_later_package_is_exempt(self):
        keep = {"date": REQUEST_DATE}
        self.assertTrue(K.exempt(keep, "2006-11-01"))
        self.assertTrue(K.exempt(keep, REQUEST_DATE))
        self.assertFalse(K.exempt(keep, "2006-01-10"))
        self.assertFalse(K.exempt(None, "2006-11-01"))


class DeskTests(unittest.TestCase):
    """`TradeDesk.scored_gain` on a stand-in desk."""

    def desk(self, on, root=ROOT, flex=0.0):
        d = trades.TradeDesk.__new__(trades.TradeDesk)
        d.on, d.root = on, Path(root)
        d.flexibility = lambda outs, ins, club: flex
        return d

    def v(self, gain, picks=True):
        return {"miami_gain": gain, "picks_out": [{"pick": {"year": 2007, "round": 1}, "value": 1.0}] if picks else []}

    def test_before_the_request_a_pick_package_scores_as_before(self):
        d = self.desk("2006-04-18")
        self.assertAlmostEqual(d.scored_gain(self.v(0.4), ["A"], ["B"], "P", standing="franchise"), 0.4)
        self.assertIsNone(d.last_keep_picks)

    def test_while_it_stands_a_pick_package_is_weighed(self):
        d = self.desk("2006-12-18")
        got = d.scored_gain(self.v(0.4), ["A"], ["B"], "P", standing="franchise")
        self.assertAlmostEqual(got, 0.4 * 0.2)
        self.assertEqual((d.last_keep_picks["request"], d.last_keep_picks["weight"], d.last_keep_picks["before"]), (LIVE, 0.8, 0.4))
        self.assertIn("keep_picks request of 2006-04-19", d.last_keep_picks["basis"])
        self.assertGreaterEqual(d.scored_gain(self.v(0.6), ["A"], ["B"], "P", standing="franchise"), trades.IN_SEASON_MIN_GAIN)
        low = d.scored_gain(self.v(0.5), ["A"], ["B"], "P", standing="rookie")
        self.assertAlmostEqual(low, 0.5 * 0.8)

    def test_the_pick_weighs_like_an_opposed_departure(self):
        d = self.desk("2006-12-18")
        opposed = d.scored_gain(self.v(0.4, picks=False), ["A"], ["B"], "P", opposed={"A"}, standing="all_star")
        self.assertAlmostEqual(d.scored_gain(self.v(0.4), ["A"], ["B"], "P", standing="all_star"), opposed)
        both = d.scored_gain(self.v(-0.1), ["A"], ["B"], "P", opposed={"A"}, standing="all_star")
        self.assertAlmostEqual(both, -0.1 * 1.6 * 1.6)                  # an opposed player and a pick: each weighed

    def test_players_only_and_his_own_package_are_unchanged(self):
        d = self.desk("2006-12-18")
        self.assertAlmostEqual(d.scored_gain(self.v(0.4, picks=False), ["A"], ["B"], "P", standing="franchise"), 0.4)
        self.assertAlmostEqual(d.scored_gain(self.v(0.4), ["A"], ["B"], "P", standing="franchise", keep_exempt=True), 0.4)
        self.assertIsNone(d.last_keep_picks)


def recorded(pattern):
    for path in sorted((ROOT / "career/Dwyane_Wade").glob(pattern)):
        if not path.name.endswith((".decision.json", ".result.json")):
            yield path, json.loads(path.read_text(encoding="utf-8"))


class ReplayTests(unittest.TestCase):
    """Read-only: nothing recorded is dated on or after the request, so nothing recorded reads it."""

    def test_no_recorded_trade_offer_or_draft_reads_the_request(self):
        n = 0
        for pattern, key in (("*/00_Team/Transactions/Trades/*.json", "date"), ("*/00_Team/Transactions/Trade_Offers/*.json", "date"),
                             ("*/09_Draft/draft_20??.json", "date")):
            for path, record in recorded(pattern):
                self.assertLess(record[key], REQUEST_DATE, path.name)
                self.assertIsNone(K.standing_request(record[key], ROOT), path.name)
                self.assertNotIn("keep_picks", record)
                self.assertNotIn("wade_trade_request", record)
                self.assertNotIn("wade_trade_requests", record)
                n += 1
        self.assertGreater(n, 10)

    def test_the_hook_adds_nothing_to_the_recorded_pick_trade(self):
        """Brian Grant and Miami's 2006 first for P.J. Brown and Chris Mihm (2006-01-16), proposed at franchise standing.
        Not a rebuild: the cap-room term is the one it was ranked with, taken from the recorded score (today's sheet
        already holds the trade, so the 2006-01-16 room cannot be recomputed from it). With the hook in place a desk
        dated before the request returns the recorded score exactly, so the hook adds nothing there; had the request
        stood, the pick would have scored below the in-season threshold."""
        path = ROOT / "career/Dwyane_Wade/2005-06/00_Team/Transactions/Trades/2006-01-16-7a8ce79392.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        v, ranking, t = record["valuation"], record["ranking"], record["trade"]
        self.assertTrue(t["picks_out"])
        flex = (ranking["score"] - v["miami_gain"]) / trades.CAP_FLEXIBILITY_WEIGHT     # the later room it was ranked with
        d = DeskTests().desk(record["date"], flex=flex)
        got = d.scored_gain(v, t["miami_out"], t["miami_in"], t["partner"], standing=record["standing"]["standing"])
        self.assertAlmostEqual(got, ranking["score"], places=6)
        self.assertIsNone(d.last_keep_picks)
        d._keep_picks = K.standing_request(REQUEST_DATE, ROOT)
        weighed = d.scored_gain(v, t["miami_out"], t["miami_in"], t["partner"], standing="franchise")
        self.assertAlmostEqual(weighed, ranking["score"] * 0.2, places=6)
        self.assertLess(weighed, trades.IN_SEASON_MIN_GAIN)

    def test_recorded_offers_carry_no_miami_pick(self):
        for path, log in recorded("*/00_Team/Transactions/Trade_Offers/*.json"):
            for o in log["offers"]:
                self.assertEqual(o["trade"].get("picks_out"), [], path.name)

    def test_recorded_summer_trades_carry_no_pick(self):
        n = 0
        for path in sorted((ROOT / "career/Dwyane_Wade").glob("*/10_Free_Agency/Free_Agency_Draws/*.proposals.json")):
            for deal in json.loads(path.read_text(encoding="utf-8"))["deals"]:
                self.assertEqual(set(deal) & {"picks", "picks_out", "picks_in"}, set(), path.name)
                n += 1
        self.assertGreater(n, 0)


class ConsequenceTests(unittest.TestCase):
    """`signing.file_trade_request`: a completed trade sending a Miami pick while the request stands."""

    def setUp(self):
        self.r = Root(self, season=signing.SEASON)
        self.requests_rel = f"career/Dwyane_Wade/{signing.SEASON}/04_Training_Camp/wade_requests.json"
        self.r.requests(self.requests_rel, keep_row())
        self.trade_rel = (signing.TRADES / "2006-12-18-abc.json").as_posix()
        self.r.write(self.trade_rel, {"trade_id": "2006-12-18-abc"})

    def record(self, picks=({"year": 2007, "round": 1},), trade_id="2006-12-18-abc", **extra):
        return dict({"trade_id": trade_id, "standing": {"standing": "rookie", "as_of": "2006-06-01"},
                     "trade": {"partner": "Utah Jazz", "miami_out": ["X"], "miami_in": ["Y"], "picks_out": list(picks), "picks_in": []}},
                    **extra)

    def rows(self):
        return json.loads((self.r.root / self.requests_rel).read_text())["requests"]

    def answer(self, action="withdraw", day="2006-12-18"):
        """The user's answer, as `scripts/player_milestone.py --reply` writes it."""
        data = {"requests": self.rows()}
        data["requests"][-1].update(answer=action, answered=day, status=K.ANSWERS[action])
        self.r.write(self.requests_rel, data)
        state = self.r.state()
        K.close(state, data["requests"][-1]["id"])
        self.r.write(f"career/Dwyane_Wade/{signing.SEASON}/current_state.json", state)

    def file(self, record, day="2006-12-18"):
        writer = signing.Writer(self.r.root)
        state = writer.load(signing.STATE)
        row = signing.file_trade_request(writer, record, day, state)
        writer.commit()
        return row

    def test_a_pick_sent_writes_his_trade_request(self):
        record = self.record()
        row = self.file(record)
        rid = "2006-12-18-2006-12-18-abc"
        self.assertEqual((row["id"], row["subject"], row["words"], row["status"]), (rid, "trade_request", WORDS, K.AWAITING))
        self.assertEqual((row["cites"]["keep_picks"]["date"], row["cites"]["keep_picks"]["index"]), (REQUEST_DATE, 0))
        self.assertEqual(K.page_name(row), "Milestone_2006-12-18_trade_request_2006-12-18-abc.md")
        self.assertEqual((row["cites"]["trade_record"], row["cites"]["picks"]), (self.trade_rel, [{"year": 2007, "round": 1}]))
        self.assertEqual(record["wade_trade_request"], rid)
        self.assertIn(K.PENDING_PREFIX + rid, self.r.state()["pending_player_decisions"])
        folder = self.r.root / f"career/Dwyane_Wade/{signing.SEASON}/04_Training_Camp"
        self.assertTrue((folder / K.page_name(row)).is_file())
        self.assertIn("Wade asks Miami to trade him", (folder / "note.md").read_text())
        self.assertEqual(K.request_errors(self.r.root), [])
        line = K.report_line(row)
        self.assertTrue(line.startswith("WADE TRADE REQUEST: "))
        self.assertIn(WORDS, line)

    def test_two_trades_on_one_date_write_two_pages(self):
        other = (signing.TRADES / "2006-12-18-def.json").as_posix()
        self.r.write(other, {"trade_id": "2006-12-18-def"})
        first, second = self.file(self.record()), self.file(self.record(trade_id="2006-12-18-def"))
        self.assertNotEqual(K.page_name(first), K.page_name(second))
        folder = self.r.root / f"career/Dwyane_Wade/{signing.SEASON}/04_Training_Camp"
        self.assertIn("2006-12-18-def", (folder / K.page_name(second)).read_text())
        self.assertNotIn("2006-12-18-def", (folder / K.page_name(first)).read_text())
        self.assertEqual(K.request_errors(self.r.root), [])

    def test_a_withdrawal_filed_the_day_the_clock_stopped_leaves_the_request_valid(self):
        self.file(self.record())
        self.answer()
        data = {"requests": self.rows() + [keep_row("2006-12-18", "withdraw")]}
        self.r.write(self.requests_rel, data)
        self.assertIsNone(K.standing_request("2006-12-18", self.r.root))
        self.assertEqual(K.request_errors(self.r.root), [])

    def test_a_request_withdrawn_before_the_trade_cannot_be_cited(self):
        self.file(self.record())
        self.answer()
        rows = self.rows()
        self.r.write(self.requests_rel, {"requests": rows + [keep_row("2006-11-01", "withdraw")]})
        self.assertTrue(any("replaced or withdrawn before 2006-12-18" in e for e in K.request_errors(self.r.root)))
        self.r.write(self.requests_rel, {"requests": [{"date": "2006-01-01", "subject": "trade_target"}] + rows})
        self.assertTrue(any("must cite" in e for e in K.request_errors(self.r.root)))     # the cited index names another row

    def test_a_keep_and_a_withdrawal_of_one_date_in_two_files_are_refused(self):
        self.r.requests(f"career/Dwyane_Wade/{signing.SEASON}/01_Free_Agency/wade_requests.json", keep_row(REQUEST_DATE, "withdraw"))
        self.assertTrue(any("belong in one wade_requests.json" in e for e in K.request_errors(self.r.root)))
        self.r.requests(f"career/Dwyane_Wade/{signing.SEASON}/01_Free_Agency/wade_requests.json")
        self.r.requests(self.requests_rel, keep_row(), keep_row(REQUEST_DATE, "withdraw"))   # one file: row order decides
        self.assertEqual(K.request_errors(self.r.root), [])
        self.assertIsNone(K.standing_request(REQUEST_DATE, self.r.root))

    def test_no_pick_no_request_or_his_own_package_writes_nothing(self):
        self.assertIsNone(self.file(self.record(picks=())))
        self.assertIsNone(self.file(self.record(ranking={"keep_picks_exempt": "2006-11-01|key"})))
        self.assertIsNone(self.file(self.record(), day="2006-04-18"))
        self.assertEqual(self.r.state()["pending_player_decisions"], [])

    def test_validation_refuses_a_broken_request(self):
        self.file(self.record())
        path = self.r.root / f"career/Dwyane_Wade/{signing.SEASON}/04_Training_Camp/wade_requests.json"
        data = json.loads(path.read_text())
        broken = copy.deepcopy(data)
        broken["requests"][-1]["words"] = "something else"
        path.write_text(json.dumps(broken))
        self.assertTrue(any("words" in e for e in K.request_errors(self.r.root)))
        path.write_text(json.dumps(data))
        state = self.r.state()
        state["pending_player_decisions"] = []
        self.r.write(f"career/Dwyane_Wade/{signing.SEASON}/current_state.json", state)
        self.assertTrue(any("pending_player_decisions" in e for e in K.request_errors(self.r.root)))


class ReplyTests(unittest.TestCase):
    """`scripts/player_milestone.py --reply`, kind trade_request."""

    def setUp(self):
        ConsequenceTests.setUp(self)
        self.row = ConsequenceTests.file(self, ConsequenceTests.record(self))
        self.path = self.r.root / f"career/Dwyane_Wade/{signing.SEASON}/04_Training_Camp/wade_requests.json"

    def reply(self, action, token=None):
        from runtime.milestone_records import version
        from scripts import player_milestone
        response = {"season": signing.SEASON, "date": "2006-12-18", "kind": "trade_request", "event_id": self.row["id"],
                    "action": action, "text": "I stand by it.", "source_ref": f"career/Dwyane_Wade/{signing.SEASON}/04_Training_Camp/note.md"}
        with mock.patch.object(player_milestone, "refresh", lambda root: []):
            return player_milestone.reply(self.r.root, response, token or version(self.path))

    def test_confirm_records_it_and_clears_the_pending_entry(self):
        self.reply("confirm")
        row = json.loads(self.path.read_text())["requests"][-1]
        self.assertEqual((row["answer"], row["answered"], row["status"]), ("confirm", "2006-12-18", "confirmed"))
        self.assertEqual(self.r.state()["pending_player_decisions"], [])
        self.assertEqual(K.request_errors(self.r.root), [])
        self.assertIsNotNone(K.standing_request("2006-12-18", self.r.root))       # the keep_picks request still stands
        with self.assertRaises(ValueError):
            self.reply("withdraw")                                                   # answered once

    def test_withdraw_and_refusals(self):
        with self.assertRaises(ValueError):
            self.reply("accept")
        with self.assertRaises(ValueError):
            self.reply("withdraw", token="stale")
        self.reply("withdraw")
        self.assertEqual(json.loads(self.path.read_text())["requests"][-1]["status"], "withdrawn")


class DriverTests(unittest.TestCase):
    def state(self):
        path = Path(tempfile.mkdtemp()) / "current_state.json"
        self.addCleanup(lambda: path.unlink(missing_ok=True))
        path.write_text(json.dumps({"current_date": "2006-12-18", "pending_player_decisions": []}))
        return path

    def test_the_driver_stops_on_a_trade_request_even_through_trades(self):
        from scripts import advance
        path = self.state()
        self.addCleanup(advance.TRADES_TODAY.clear)
        advance.TRADES_TODAY[:] = ["MIAMI TRADE: x"]
        with mock.patch.object(advance, "state_file", lambda: path):
            advance.trade_request_stop("MIAMI TRADE: x\ntrade scan: no proposal worth making", "2006-12-18")
            self.assertNotIn("reported_stop", json.loads(path.read_text()))
            with self.assertRaises(advance.Stop) as stop:
                advance.trade_request_stop("MIAMI TRADE: x\nWADE TRADE REQUEST: Miami sent its 2007 round 1 pick", "2006-12-18")
            self.assertIn("WADE TRADE REQUEST", str(stop.exception))
            # The day's trade and the request are recorded, so the resumed day reports them without stopping again.
            self.assertEqual(advance.reported("2006-12-18"), {"MIAMI TRADE: x", "WADE TRADE REQUEST: Miami sent its 2007 round 1 pick"})

    def test_a_confirmed_request_keeps_the_driver_stopped(self):
        from scripts import advance
        r = Root(self)
        rel = "career/Dwyane_Wade/2005-06/04_Training_Camp/wade_requests.json"
        row, _ = K.trade_request(dict(K.standing_request(REQUEST_DATE, ROOT), path=rel, index=0), "2006-12-18", "2006-12-18-abc", "x",
                                 [{"year": 2007, "round": 1}], "Utah Jazz", {"standing": "franchise"})
        path = self.state()
        with mock.patch.object(advance, "state_file", lambda: path), mock.patch.object(advance, "ROOT", r.root):
            r.requests(rel, keep_row(), dict(row, answer="withdraw", answered="2006-12-18", status="withdrawn"))
            advance.wade_waits()                                                      # withdrawn: the career goes on
            r.requests(rel, keep_row(), dict(row, answer="confirm", answered="2006-12-18", status="confirmed"))
            with self.assertRaises(advance.Stop) as stop:
                advance.wade_waits()
        self.assertIn("ROADMAP.md F1", str(stop.exception))
        self.assertIn(row["id"], str(stop.exception))

    def test_the_season_day_line_shows_only_while_it_waits(self):
        from scripts import run_trade
        r = Root(self, season=run_trade.SEASON)
        rel = f"career/Dwyane_Wade/{run_trade.SEASON}/04_Training_Camp/wade_requests.json"
        r.requests(rel, keep_row())
        row, _ = K.trade_request(K.standing_request("2006-12-18", r.root), "2006-12-18", "2006-12-18-abc", "x", [{"year": 2007, "round": 1}],
                                 "Utah Jazz", {"standing": "franchise"})
        r.requests(rel, keep_row(), row)
        lines = run_trade.trade_request_lines({"wade_trade_request": row["id"]}, r.root)
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].startswith("WADE TRADE REQUEST"))
        r.requests(rel, keep_row(), dict(row, answer="confirm", answered="2006-12-18", status="confirmed"))
        self.assertEqual(run_trade.trade_request_lines({"wade_trade_request": row["id"]}, r.root), [])
        self.assertEqual(run_trade.trade_request_lines({}, r.root), [])


KEEP_FRANCHISE = {"path": LIVE, "index": 2, "date": REQUEST_DATE, "requested": "keep", "if_ignored": "trade_request", "words": WORDS,
                  "source_ref": "test", "standing": "franchise", "standing_as_of": "2005-06-16", "weight": 0.8}
SPREAD = (("Alpha One", "a1", "G", 1), ("Beta Two", "b2", "F", 5), ("Gamma Three", "g3", "C", 5.5), ("Delta Four", "d4", "F", 6))


class DraftNightTests(unittest.TestCase):
    """Rule 6 with the request standing: a synthetic night where the second club gains 1.22 by moving up."""

    def night(self, *clubs, keep=None, answers=None):
        draft = Draft(self).order(*clubs)
        draft.globals.update(MAX_TRADES=6, _keep=lambda root: copy.deepcopy(keep))
        (draft.root / f"career/Dwyane_Wade/{draft.globals['SEASON']}/current_state.json").write_text(
            json.dumps({"current_date": draft.date, "pending_player_decisions": []}))
        record, packets, _, _ = draft.run(pool_of(*SPREAD), Engine(answers))
        return draft, record, packets

    def test_the_pool_is_one_tier_with_a_clear_favourite(self):
        pool = pool_of(*SPREAD)
        self.assertEqual(set(D.tiers(pool).values()), {1})

    def test_on_the_clock_miami_answers_a_trade_down_at_a_reduced_chance(self):
        _, plain, packets0 = self.night("Miami Heat", "Alpha")
        self.assertEqual(packets0["2006-draft-pick-1-trade-down"]["options"], {"accept": 0.5, "decline": 0.5})
        self.assertNotIn("keep_picks", plain)
        _, record, packets = self.night("Miami Heat", "Alpha", keep=KEEP_FRANCHISE)
        packet = packets["2006-draft-pick-1-trade-down"]
        self.assertEqual(packet["options"], {"accept": 0.1, "decline": 0.9})          # 0.5 x (1 - 0.8): weighed, still drawn
        self.assertIn("keep_picks request of 2006-04-19", packet["basis"])
        call = record["keep_picks"]["calls"][0]
        self.assertEqual((call["side"], call["slot"], call["for_slot"], call["accept"]), ("down", 1, 2, 0.1))
        self.assertEqual(record["trades"], [])                                          # the stand-in declined

    def test_a_trade_down_taken_anyway_writes_his_trade_request(self):
        draft, record, _ = self.night("Miami Heat", "Alpha", keep=KEEP_FRANCHISE, answers={"2006-draft-pick-1-trade-down": "accept"})
        self.assertEqual(record["trades"][0]["from"], "Miami Heat")
        rid = "2006-06-28-2006-draft-pick-1-trade-down"
        self.assertEqual(record["wade_trade_requests"], [rid])
        rows = json.loads((draft.root / draft.folder / "wade_requests.json").read_text())["requests"]
        row = next(r for r in rows if r.get("id") == rid)
        self.assertEqual([p["label"] for p in row["cites"]["picks"]], ["No. 1 in the 2006 draft"])

    def test_miami_does_not_move_up_at_franchise_standing(self):
        _, plain, packets0 = self.night("Alpha", "Miami Heat")
        self.assertIn("Miami Heat", packets0["2006-draft-pick-1-trade-down"]["question"])
        _, record, packets = self.night("Alpha", "Miami Heat", keep=KEEP_FRANCHISE)
        self.assertNotIn("2006-draft-pick-1-trade-down", packets)
        self.assertEqual([(c["side"], c["declined"]) for c in record["keep_picks"]["calls"]], [("up", True)])

    def test_another_clubs_trade_is_unaffected(self):
        _, _, packets0 = self.night("Alpha", "Beta", "Miami Heat")
        _, record, packets = self.night("Alpha", "Beta", "Miami Heat", keep=KEEP_FRANCHISE)
        self.assertEqual(packets["2006-draft-pick-1-trade-down"], packets0["2006-draft-pick-1-trade-down"])
        self.assertEqual(record["keep_picks"]["calls"], [])

    def test_a_low_standing_can_move_up_and_the_pick_traded_writes_his_trade_request(self):
        low = dict(KEEP_FRANCHISE, standing="unsigned_rookie", weight=0.15)
        draft, record, packets = self.night("Alpha", "Miami Heat", keep=low, answers={"2006-draft-pick-1-trade-down": "accept"})
        self.assertEqual([(c["side"], c["declined"]) for c in record["keep_picks"]["calls"]], [("up", False)])
        self.assertEqual(record["trades"][0]["to"], "Miami Heat")
        rid = "2006-06-28-2006-draft-pick-1-trade-down"
        self.assertEqual(record["wade_trade_requests"], [rid])
        rows = json.loads((draft.root / draft.folder / "wade_requests.json").read_text())["requests"]
        row = next(r for r in rows if r.get("id") == rid)
        self.assertEqual([p["label"] for p in row["cites"]["picks"]], ["No. 2 in the 2006 draft", "its 2007 second-round pick"])
        self.assertEqual(row["cites"]["partner"], "Alpha")
        state = json.loads((draft.root / f"career/Dwyane_Wade/{draft.globals['SEASON']}/current_state.json").read_text())
        self.assertIn(K.PENDING_PREFIX + rid, state["pending_player_decisions"])
        self.assertTrue((draft.root / draft.folder / K.page_name(row)).is_file())

    def test_the_recorded_drafts_had_no_request(self):
        for year in (2004, 2005):
            with self.subTest(year=year), D.year_context(year, ROOT):
                self.assertIsNone(K.standing_request(D.DRAFT_DATE, ROOT))
                self.assertIsNone(D._keep(ROOT))

    def test_the_real_reader_finds_the_live_request_on_a_2006_draft_date(self):
        with mock.patch.multiple(D, YEAR=2006, SEASON="2005-06", DRAFT_DATE="2006-06-28",
                                 FOLDER=Path("career/Dwyane_Wade/2005-06/09_Draft")):
            keep = D._keep(ROOT)
        self.assertEqual((keep["path"], keep["index"], keep["date"], keep["standing"], keep["weight"]),
                         (LIVE, 2, REQUEST_DATE, "franchise", 0.8))
        self.assertEqual(D.keep_down(28, 31, keep)["accept"], 0.1)
        self.assertTrue(D.keep_up(28, 31, 1.22, keep)["declined"])

    def test_a_club_moves_up_once_from_the_2006_draft(self):
        """Its next-year second goes with its first move up; before 2006 the rule could send it twice."""
        eight = (("A1", "a1", "G", 1), ("B2", "b2", "F", 1.1), ("C3", "c3", "C", 5), ("D4", "d4", "F", 5.2), ("E5", "e5", "G", 5.4),
                 ("F6", "f6", "C", 5.6), ("G7", "g7", "F", 5.8), ("H8", "h8", "G", 6.0))
        moves = {}
        for year in (2005, 2006):
            draft = Draft(self, year=year).order("Alpha", "Alpha", "Beta", "Beta", "Alpha", "Alpha")
            draft.globals.update(MAX_TRADES=6)
            answers = {f"{year}-draft-pick-{s}-trade-down": "accept" for s in range(1, 7)}
            record, _, _, _ = draft.run(pool_of(*eight), Engine(answers))
            moves[year] = [t["to"] for t in record["trades"]]
        self.assertEqual(moves, {2005: ["Beta", "Beta"], 2006: ["Beta"]})


class NewsTests(unittest.TestCase):
    def test_draft_news_reports_a_waiting_trade_request(self):
        from scripts import offseason_day
        r = Root(self)
        rel = "career/Dwyane_Wade/2005-06/09_Draft/wade_requests.json"
        row, _ = K.trade_request(dict(KEEP_FRANCHISE, path=rel), "2006-06-28", "2006-draft-pick-30-trade-down", "x",
                                 [{"year": 2006, "round": 1}], "Alpha", {"standing": "rookie"})
        r.requests(rel, keep_row(), row)
        with mock.patch.object(offseason_day, "ROOT", r.root):
            lines = offseason_day.draft_news({"trades": [], "picks": [], "wade_trade_requests": [row["id"]]}, 2006)
            self.assertEqual(len(lines), 1)
            self.assertTrue(lines[0].startswith("WADE TRADE REQUEST"))
            r.requests(rel, keep_row(), dict(row, answer="withdraw", answered="2006-06-28", status="withdrawn"))
            self.assertEqual(offseason_day.draft_news({"trades": [], "picks": [], "wade_trade_requests": [row["id"]]}, 2006), [])


if __name__ == "__main__":
    unittest.main()
