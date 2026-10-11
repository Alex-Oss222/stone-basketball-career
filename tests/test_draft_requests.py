"""Wade's draft_prospect scouting requests (`runtime/draft.py` rule 7), forward only from the 2006 draft.

Synthetic classes, clubs and orders in a temporary root, so each rule is seen apart from the 2006 class data
(`tests/test_offseason_2006_data.py` reads that). Every pick is answered by a stand-in for the engine that records the
packet and returns the likeliest option (or a scripted answer), so the packets Miami's draw would send can be compared
with and without Wade's requests.
"""
import copy
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from runtime import draft as D

ROOT = Path(__file__).resolve().parents[1]
POSITION = {"G": "PG", "F": "SF", "C": "C"}


def prospect(name, bbr_id, group, consensus, age=21):
    median = D.MEDIAN_TOP * math.exp(-D.MEDIAN_DECAY * (consensus - 1))
    spread = D.SPREAD_BASE * median * (1 + (23 - age) / 4)
    return {"player": name, "bbr_id": bbr_id, "position": POSITION[group], "group": group, "second_position": False,
            "age": age, "consensus": consensus, "median": round(median, 4), "floor": round(max(D.FLOOR_MIN, median - spread), 4),
            "ceiling": round(median + 1.6 * spread, 4)}


def pool_of(*rows):
    return {D._key(r[0]): prospect(*r) for r in rows}


def context():
    return {"stance": "middle", "record": "41-41", "need": {"G": 0.2, "F": 0.2, "C": 0.2},
            "cornerstone": {"G": False, "F": False, "C": False}}


def request(player, bbr_id=None, date="2005-10-31", draft_year=2006, requested="evaluate", **extra):
    row = {"date": date, "subject": "draft_prospect", "player": player, "college": "College", "position": "G",
           "draft_year": draft_year, "requested": requested, "words": "Keep him under consideration.",
           "note": "Scouting recommendation.", "source_ref": "test"}
    if bbr_id:
        row["bbr_id"] = bbr_id
    row.update(extra)
    return row


LOWRY = ("Kyle Lowry", "lowryky01")
TUCKER = ("P.J. Tucker", "tuckepj01")


class Engine:
    """Stands in for the engine: records each packet and answers it (scripted, else the likeliest option; trades declined)."""

    def __init__(self, answers=None):
        self.packets, self.answers = {}, dict(answers or {})

    def __call__(self, root, packet):
        self.packets[packet["event_id"]] = packet
        if packet["event_id"] in self.answers:
            return self.answers[packet["event_id"]]
        if "accept" in packet["options"]:
            return "decline"
        return max(packet["options"], key=lambda k: (packet["options"][k], k))


class Draft:
    """A synthetic draft night in a temporary root under a year's module globals."""

    def __init__(self, testcase, year=2006, standing="franchise"):
        self.t, self.year = testcase, year
        tmp = tempfile.TemporaryDirectory()
        testcase.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        season = f"{year - 1}-{str(year)[-2:]}"
        self.folder = Path(f"career/Dwyane_Wade/{season}/09_Draft")
        self.date = f"{year}-06-28"
        self.globals = {"YEAR": year, "SEASON": season, "DRAFT_DATE": self.date, "FOLDER": self.folder,
                        "RECORD": self.folder / f"draft_{year}.json", "DRAWS": self.folder / "Draft_Draws", "MAX_TRADES": 0}
        (self.root / self.folder).mkdir(parents=True)
        snapshots = [{"as_of": f"{year - 1}-06-16", "standing": standing, "trigger": "season_close", "basis": {}, "source": "test"}]
        (self.root / "career/Dwyane_Wade/standing.json").write_text(json.dumps({"schema_version": 1, "snapshots": snapshots}))

    def order(self, *clubs):
        rows = [{"pick": i, "round": 1 if i <= 30 else 2, "owner_club": c} for i, c in enumerate(clubs, 1)]
        (self.root / self.folder / f"draft_order_{self.year}.json").write_text(json.dumps({"picks": rows}))
        return self

    def requests(self, *rows):
        (self.root / self.folder / D.REQUESTS_FILE).write_text(json.dumps({"requests": list(rows)}))
        return self

    def run(self, pool, engine=None):
        engine = engine or Engine()
        clubs = {c: context() for c in ("Miami Heat", "Alpha", "Beta", "Gamma")}
        with mock.patch.multiple(D, **self.globals, prospects=lambda root=None: copy.deepcopy(pool),
                                 club_contexts=lambda root=None: copy.deepcopy(clubs),
                                 _miami_pick_ledger=lambda root, trades: None, _draw=engine):
            record = D.run(self.root, self.date)
            watched = D.watch_list(self.root)
            asked = D.wade_requests(self.root)
        return record, engine.packets, watched, asked


def odds(p):
    return p / (1 - p)


class GateTests(unittest.TestCase):
    def test_requests_apply_from_the_2006_draft(self):
        self.assertEqual(D.REQUESTS_FROM, 2006)

    def test_a_2005_context_ignores_requests(self):
        """The same class, order and request file under 2005's globals: the packets and the record are the ones a
        draft without any request file writes, with no request keys."""
        pool = pool_of(("Alpha One", "a1", "G", 1), ("Beta Two", "b2", "F", 2), ("Gamma Three", "g3", "C", 3),
                       ("Kyle Lowry", "lowryky01", "G", 4))
        plain = Draft(self, year=2005).order("Miami Heat", "Alpha")
        asked = Draft(self, year=2005).order("Miami Heat", "Alpha").requests(request(*LOWRY, date="2005-01-15", draft_year=2005))
        record0, packets0, _, _ = plain.run(pool)
        record1, packets1, watched, rows = asked.run(pool)
        self.assertEqual(rows, [])
        with mock.patch.multiple(D, **asked.globals, REQUESTS_FROM=2005):              # only the gate keeps it out
            self.assertEqual([r["bbr_id"] for r in D.wade_requests(asked.root)], ["lowryky01"])
        self.assertEqual(packets1, packets0)
        self.assertEqual(record1, record0)
        self.assertNotIn("wade_requests", record1)
        self.assertNotIn("scouting_watch_list", record1)
        self.assertEqual(watched, [])
        self.assertNotIn("Wade", packets1["2005-draft-pick-1"]["basis"])

    def test_the_recorded_drafts_read_no_requests(self):
        """The real 2004 and 2005 draft contexts read no request, whatever their folders hold."""
        for year in (2004, 2005):
            with self.subTest(year=year), D.year_context(year, ROOT):
                self.assertEqual(D.wade_requests(ROOT), [])

    def test_without_requests_a_2006_draft_is_the_old_rule(self):
        pool = pool_of(("Alpha One", "a1", "G", 1), ("Beta Two", "b2", "F", 2), ("Gamma Three", "g3", "C", 3))
        record, packets, _, _ = Draft(self).order("Miami Heat").run(pool)
        self.assertNotIn("wade_requests", record)
        top3 = {pool[k]["player"]: v for k, v in D._options({k: D.utility(pool[k], context()) for k in pool}).items()}
        self.assertEqual(packets["2006-draft-pick-1"]["options"], top3)


class MiamiPickTests(unittest.TestCase):
    TIER_ONE = (("Alpha One", "a1", "G", 1), ("Beta Two", "b2", "F", 1.5), ("Gamma Three", "g3", "C", 2),
                ("Delta Four", "d4", "F", 2.5))

    def test_a_requested_prospect_in_the_best_tier_gains_his_standing_weight(self):
        pool = pool_of(*self.TIER_ONE[:2], ("Kyle Lowry", "lowryky01", "G", 1.8), self.TIER_ONE[2])
        self.assertEqual(len(set(D.tiers(pool).values())), 1)
        plain, _, _, _ = Draft(self).order("Miami Heat").run(pool)
        record, packets, _, _ = Draft(self).order("Miami Heat").requests(request(*LOWRY)).run(pool)
        packet = packets["2006-draft-pick-1"]
        p1 = packet["options"]["Kyle Lowry"]
        self.assertEqual(set(packet["options"]), {"Alpha One", "Beta Two", "Kyle Lowry"})   # the club's own top three
        base = D._options({k: D.utility(pool[k], context()) for k in pool if pool[k]["player"] in packet["options"]})
        p0 = base[D._key("Kyle Lowry")]
        self.assertGreater(p1, p0)
        self.assertAlmostEqual(odds(p1) / odds(p0), 1.8, places=3)        # franchise standing: x (1 + 0.8)
        self.assertAlmostEqual(sum(packet["options"].values()), 1.0, places=9)
        self.assertIn("Kyle Lowry tier 1, in the best available tier; draw weight x1.80", packet["basis"])
        self.assertIn("standing franchise", packet["basis"])
        note = record["wade_requests"]["picks"][0]
        self.assertEqual((note["pick"], note["club"], note["event_id"]), (1, "Miami Heat", "2006-draft-pick-1"))
        row = note["requests"][0]
        self.assertEqual((row["status"], row["weight"], row["added_to_candidates"]), ("weighed", 0.8, False))
        self.assertEqual((row["probability"], row["probability_without_request"]), (p1, p0))
        self.assertEqual(record["wade_requests"]["weight"], 0.8)
        self.assertNotIn("wade_requests", plain)

    def test_the_weight_follows_standing(self):
        pool = pool_of(*self.TIER_ONE[:2], ("Kyle Lowry", "lowryky01", "G", 1.8))
        _, packets, _, _ = Draft(self, standing="rookie").order("Miami Heat").requests(request(*LOWRY)).run(pool)
        base = D._options({k: D.utility(pool[k], context()) for k in pool})
        p0, p1 = base[D._key("Kyle Lowry")], packets["2006-draft-pick-1"]["options"]["Kyle Lowry"]
        self.assertAlmostEqual(odds(p1) / odds(p0), 1.2, places=3)

    def test_a_requested_tier_prospect_outside_the_top_three_joins_the_draw(self):
        pool = pool_of(*self.TIER_ONE, ("Kyle Lowry", "lowryky01", "G", 3))
        tiers = D.tiers(pool)
        self.assertEqual(tiers[D._key("Kyle Lowry")], 1)
        _, plain, _, _ = Draft(self).order("Miami Heat").run(pool)
        record, packets, _, _ = Draft(self).order("Miami Heat").requests(request(*LOWRY)).run(pool)
        self.assertNotIn("Kyle Lowry", plain["2006-draft-pick-1"]["options"])
        options = packets["2006-draft-pick-1"]["options"]
        self.assertEqual(list(options)[:3], list(plain["2006-draft-pick-1"]["options"]))   # the club's own three stay
        self.assertIn("Kyle Lowry", options)
        self.assertGreater(options["Kyle Lowry"], 0)
        row = record["wade_requests"]["picks"][0]["requests"][0]
        self.assertTrue(row["added_to_candidates"])
        self.assertEqual(row["probability_without_request"], 0.0)
        self.assertIn("added to the club's top three by utility", packets["2006-draft-pick-1"]["basis"])

    def test_a_requested_prospect_outside_the_best_tier_changes_nothing(self):
        pool = pool_of(*self.TIER_ONE, ("Kyle Lowry", "lowryky01", "G", 30))
        tiers = D.tiers(pool)
        self.assertGreater(tiers[D._key("Kyle Lowry")], tiers[D._key("Alpha One")])
        record0, plain, _, _ = Draft(self).order("Miami Heat").run(pool)
        record, packets, _, _ = Draft(self).order("Miami Heat").requests(request(*LOWRY)).run(pool)
        self.assertEqual(packets["2006-draft-pick-1"]["options"], plain["2006-draft-pick-1"]["options"])
        self.assertEqual(record["picks"], record0["picks"])
        row = record["wade_requests"]["picks"][0]["requests"][0]
        self.assertEqual(row["status"], "outside_tier")
        self.assertNotIn("probability", row)
        self.assertIn("outside the best available tier", packets["2006-draft-pick-1"]["basis"])

    def test_another_clubs_pick_is_unaffected(self):
        """Alpha picks first with the requested prospect in its tier: its packet is the same with or without Wade's
        request, and only Miami's pick carries an account of the request."""
        pool = pool_of(*self.TIER_ONE, ("Kyle Lowry", "lowryky01", "G", 1.2))
        record0, plain, _, _ = Draft(self).order("Alpha", "Miami Heat", "Beta").run(pool)
        record, packets, _, _ = Draft(self).order("Alpha", "Miami Heat", "Beta").requests(request(*LOWRY)).run(pool)
        self.assertEqual(packets["2006-draft-pick-1"], plain["2006-draft-pick-1"])
        self.assertEqual([n["pick"] for n in record["wade_requests"]["picks"]], [2])
        self.assertIn("Kyle Lowry", packets["2006-draft-pick-2"]["options"])
        self.assertIn("Wade's scouting requests", packets["2006-draft-pick-2"]["basis"])
        self.assertEqual(record["picks"][1]["player"], record0["picks"][1]["player"])    # Miami took the same player
        self.assertEqual(packets["2006-draft-pick-3"], plain["2006-draft-pick-3"])     # so Beta's pick is the same
        self.assertNotIn("Wade", packets["2006-draft-pick-3"]["basis"])

    def test_a_prospect_taken_earlier_is_not_weighed(self):
        pool = pool_of(*self.TIER_ONE, ("Kyle Lowry", "lowryky01", "G", 1.2))
        engine = Engine({"2006-draft-pick-1": "Kyle Lowry"})
        record, packets, watched, _ = Draft(self).order("Alpha", "Miami Heat").requests(request(*LOWRY)).run(pool, engine)
        row = record["wade_requests"]["picks"][0]["requests"][0]
        self.assertEqual((row["status"], row["taken"]), ("taken", {"pick": 1, "club": "Alpha"}))
        self.assertNotIn("Kyle Lowry", packets["2006-draft-pick-2"]["options"])
        self.assertIn("Kyle Lowry taken No. 1 by Alpha; not weighed", packets["2006-draft-pick-2"]["basis"])
        self.assertEqual(watched[0]["outcome"], "drafted")
        self.assertEqual((watched[0]["pick"], watched[0]["club"], watched[0]["by_miami"]), (1, "Alpha", False))
        self.assertEqual(watched[0]["weighed_at_miami_picks"], [])

    def test_the_only_player_left_in_the_tier_needs_no_draw(self):
        pool = pool_of(("Kyle Lowry", "lowryky01", "G", 1), ("Beta Two", "b2", "F", 20))
        record, packets, watched, _ = Draft(self).order("Miami Heat").requests(request(*LOWRY)).run(pool)
        self.assertEqual(packets, {})
        note = record["wade_requests"]["picks"][0]
        self.assertEqual((note["event_id"], note["selected"], note["requests"][0]["status"]), (None, "Kyle Lowry", "only_candidate"))
        self.assertEqual(watched[0]["weighed_at_miami_picks"], [1])

    def test_a_request_dated_after_the_draft_or_for_another_draft_is_ignored(self):
        pool = pool_of(*self.TIER_ONE[:2], ("Kyle Lowry", "lowryky01", "G", 1.8))
        draft = Draft(self).order("Miami Heat").requests(request(*LOWRY, date="2006-06-29"),
                                                         request(*TUCKER, draft_year=2007))
        record, packets, _, rows = draft.run(pool)
        self.assertEqual(rows, [])
        self.assertNotIn("wade_requests", record)

    def test_a_later_row_withdraws_the_recommendation(self):
        pool = pool_of(*self.TIER_ONE[:2], ("Kyle Lowry", "lowryky01", "G", 1.8))
        draft = Draft(self).order("Miami Heat").requests(request(*LOWRY), request(*LOWRY, date="2006-05-01", requested="withdraw"))
        record, _, _, rows = draft.run(pool)
        self.assertEqual(rows, [])
        self.assertNotIn("wade_requests", record)

    def test_a_later_name_only_row_withdraws_a_request_that_gave_the_bbr_id(self):
        """The withdrawal names the prospect without his bbr_id: it is the same prospect, so the request is withdrawn
        and Miami's packet is the one a draft without requests sends."""
        pool = pool_of(*self.TIER_ONE[:2], ("Kyle Lowry", "lowryky01", "G", 1.8))
        _, plain, _, _ = Draft(self).order("Miami Heat").run(pool)
        for withdrawal in (request("Kyle Lowry", date="2006-05-01", requested="withdraw"),
                           request("Kyle  Lowry.", date="2006-05-01", requested="withdraw")):
            with self.subTest(player=withdrawal["player"]):
                record, packets, watched, rows = Draft(self).order("Miami Heat").requests(request(*LOWRY), withdrawal).run(pool)
                self.assertEqual(rows, [])
                self.assertNotIn("wade_requests", record)
                self.assertEqual(watched, [])
                self.assertEqual(packets, plain)
                self.assertNotIn("Wade", packets["2006-draft-pick-1"]["basis"])

    def test_a_later_row_with_the_bbr_id_withdraws_a_name_only_request(self):
        """The two rows spell him differently and only the later gives his bbr_id: both resolve to the class's P.J.
        Tucker, so draft night reads one prospect and the withdrawal stands."""
        pool = pool_of(*self.TIER_ONE[:2], ("P.J. Tucker", "tuckepj01", "F", 1.8))
        draft = Draft(self).order("Miami Heat").requests(
            request("PJ Tucker"), request("Pat Tucker", "tuckepj01", date="2006-05-01", requested="withdraw"))
        record, _, _, rows = draft.run(pool)
        self.assertEqual([r["player"] for r in rows], ["PJ Tucker"])     # without the class the two names differ
        with mock.patch.multiple(D, **draft.globals):
            self.assertEqual(D.wade_requests(draft.root, pool), [])
        self.assertNotIn("wade_requests", record)

    def test_a_repeated_request_is_weighed_once(self):
        """The same prospect asked for twice, once with his bbr_id and once by name only: one request, the latest row,
        one account in the packet basis and one Miami pick in the watch list."""
        pool = pool_of(*self.TIER_ONE[:2], ("Kyle Lowry", "lowryky01", "G", 1.8))
        once, packets0, _, _ = Draft(self).order("Miami Heat").requests(request(*LOWRY)).run(pool)
        record, packets, watched, rows = Draft(self).order("Miami Heat").requests(
            request(*LOWRY), request("Kyle Lowry", date="2006-05-01")).run(pool)
        self.assertEqual([(r.get("bbr_id"), r["date"]) for r in rows], [(None, "2006-05-01")])
        self.assertEqual(packets["2006-draft-pick-1"]["options"], packets0["2006-draft-pick-1"]["options"])
        self.assertEqual(packets["2006-draft-pick-1"]["basis"].count("Kyle Lowry tier 1"), 1)
        self.assertEqual(len(record["wade_requests"]["requests"]), 1)
        self.assertEqual(len(record["wade_requests"]["picks"][0]["requests"]), 1)
        self.assertEqual([w["weighed_at_miami_picks"] for w in watched], [[1]])
        self.assertEqual(record["picks"], once["picks"])

    def test_two_prospects_of_one_name_stay_two_requests(self):
        """Different bbr_ids are different prospects, whatever their names; a name-only row is the latest of its name."""
        pool = pool_of(*self.TIER_ONE[:2], ("Kyle Lowry", "lowryky01", "G", 1.8))
        draft = Draft(self).order("Miami Heat").requests(request("John Smith", "smithjo01"), request("John Smith", "smithjo02"))
        _, _, watched, rows = draft.run(pool)
        self.assertEqual([r["bbr_id"] for r in rows], ["smithjo01", "smithjo02"])
        self.assertEqual([w["outcome"] for w in watched], ["not_in_class", "not_in_class"])
        self.assertTrue(D._same_prospect({"player": "John Smith"}, {"player": "John Smith", "bbr_id": "smithjo02"}))
        self.assertFalse(D._same_prospect({"player": "John Smith", "bbr_id": "smithjo01"},
                                          {"player": "John Smith", "bbr_id": "smithjo02"}))


class DraftVerbTests(unittest.TestCase):
    """`requested: draft` (rule 7): an engine-drawn decision before the pick's own draw, at standing weight x closeness."""
    TIER_ONE = MiamiPickTests.TIER_ONE

    def tucker(self, **extra):
        return request(*TUCKER, date="2006-04-19", requested="draft", **extra)

    def test_in_the_best_tier_the_request_is_drawn_first_at_weight_times_closeness(self):
        pool = pool_of(*self.TIER_ONE[:2], ("P.J. Tucker", "tuckepj01", "F", 1.8))
        record, packets, watched, _ = Draft(self).order("Miami Heat").requests(self.tucker()).run(pool)
        scores = {k: D.utility(pool[k], context()) for k in pool}
        close = math.exp((scores[D._key("P.J. Tucker")] - max(scores.values())) / D.TEMPERATURE)
        chance = round(0.8 * close, 3)
        ask = packets["2006-draft-pick-1-wade-request"]
        self.assertEqual(ask["options"], {"P.J. Tucker": chance, "rule": round(1 - chance, 6)})
        self.assertIn("Wade asks Miami to draft P.J. Tucker", ask["basis"])
        self.assertEqual(ask["decider"], "Miami Heat front office (engine draw on Wade's request)")
        # The stand-in answered the likelier "rule": the pick's own draw follows, with the evaluate lift.
        base = D._options(scores)
        lifted = packets["2006-draft-pick-1"]["options"]["P.J. Tucker"]
        self.assertAlmostEqual(odds(lifted) / odds(base[D._key("P.J. Tucker")]), 1.8, places=3)
        total = chance + (1 - chance) * lifted
        self.assertGreater(total, lifted)                        # at least the evaluate lift
        self.assertLess(total, 1.0)                              # never a certainty
        row = record["wade_requests"]["picks"][0]["requests"][0]
        self.assertEqual((row["status"], row["requested"]), ("weighed", "draft"))
        self.assertEqual((row["request_draw"]["chance"], row["request_draw"]["outcome"]), (chance, "rule"))
        self.assertAlmostEqual(row["request_draw"]["closeness"], round(close, 4))
        self.assertIn("left the pick to the rule's own draw", packets["2006-draft-pick-1"]["basis"])
        self.assertEqual(watched[0]["weighed_at_miami_picks"], [1])
        self.assertIn("A request to draft him also opposes the rule's call", record["wade_requests"]["rule"])

    def test_the_request_draw_can_take_him(self):
        pool = pool_of(*self.TIER_ONE[:2], ("P.J. Tucker", "tuckepj01", "F", 1.8))
        engine = Engine({"2006-draft-pick-1-wade-request": "P.J. Tucker"})
        record, packets, watched, _ = Draft(self).order("Miami Heat").requests(self.tucker()).run(pool, engine)
        self.assertNotIn("2006-draft-pick-1", packets)            # no draw of the club's own
        self.assertEqual(record["picks"][0]["player"], "P.J. Tucker")
        note = record["wade_requests"]["picks"][0]
        self.assertEqual((note["event_id"], note["request_event_id"], note["request_outcome"]),
                         (None, "2006-draft-pick-1-wade-request", "P.J. Tucker"))
        self.assertIsNone(note["requests"][0]["probability"])
        self.assertEqual((watched[0]["outcome"], watched[0]["by_miami"]), ("drafted", True))

    def test_outside_the_tier_the_chance_is_weight_times_closeness_to_the_line(self):
        pool = pool_of(*self.TIER_ONE, ("P.J. Tucker", "tuckepj01", "F", 9))
        tiers = D.tiers(pool)
        k = D._key("P.J. Tucker")
        self.assertEqual(tiers[k], 2)
        head = max(D.board_score(p) for key, p in pool.items() if tiers[key] == 1)
        close = 1 - ((1 - D.TIER_BREAK) * head - D.board_score(pool[k])) / (D.TIER_BREAK * head)
        engine = Engine({"2006-draft-pick-1-wade-request": "rule"})
        record, packets, _, _ = Draft(self).order("Miami Heat").requests(self.tucker()).run(pool, engine)
        chance = round(0.8 * close, 3)
        self.assertTrue(0 < close < 1)
        self.assertEqual(packets["2006-draft-pick-1-wade-request"]["options"], {"P.J. Tucker": chance, "rule": round(1 - chance, 6)})
        plain = Draft(self).order("Miami Heat").run(pool)[1]
        self.assertEqual(packets["2006-draft-pick-1"]["options"], plain["2006-draft-pick-1"]["options"])   # no reach in the rule's draw
        row = record["wade_requests"]["picks"][0]["requests"][0]
        self.assertEqual(row["status"], "outside_tier")
        self.assertIn("the rule does not reach across tiers", row["reason"])

    def test_a_request_drawn_from_a_lower_tier_records_his_own_tier(self):
        pool = pool_of(*self.TIER_ONE, ("P.J. Tucker", "tuckepj01", "F", 9))
        engine = Engine({"2006-draft-pick-1-wade-request": "P.J. Tucker"})
        record, _, watched, _ = Draft(self).order("Miami Heat").requests(self.tucker()).run(pool, engine)
        pick = record["picks"][0]
        self.assertEqual((pick["player"], pick["tier"]), ("P.J. Tucker", 2))
        self.assertEqual(pick["tier"], next(b["tier"] for b in record["board"] if b["player"] == "P.J. Tucker"))
        self.assertEqual((watched[0]["outcome"], watched[0]["board_tier"]), ("drafted", 2))

    def test_a_whole_tier_below_the_line_is_clear_cut(self):
        pool = pool_of(*self.TIER_ONE, ("P.J. Tucker", "tuckepj01", "F", 40))
        record, packets, _, _ = Draft(self).order("Miami Heat").requests(self.tucker()).run(pool)
        self.assertNotIn("2006-draft-pick-1-wade-request", packets)
        self.assertIn("a clear-cut call (closeness 0), not drawn", record["wade_requests"]["picks"][0]["requests"][0]["reason"])

    def test_another_clubs_pick_and_an_evaluation_request_draw_nothing_more(self):
        pool = pool_of(*self.TIER_ONE, ("P.J. Tucker", "tuckepj01", "F", 1.2))
        _, plain, _, _ = Draft(self).order("Alpha", "Miami Heat").run(pool)
        _, packets, _, _ = Draft(self).order("Alpha", "Miami Heat").requests(self.tucker()).run(pool)
        self.assertEqual(packets["2006-draft-pick-1"], plain["2006-draft-pick-1"])
        self.assertEqual([e for e in packets if e.endswith("wade-request")], ["2006-draft-pick-2-wade-request"])
        _, evaluated, _, _ = Draft(self).order("Miami Heat").requests(request(*TUCKER)).run(pool)
        self.assertFalse([e for e in evaluated if e.endswith("wade-request")])

    def test_two_draft_requests_share_one_packet_in_request_order(self):
        pool = pool_of(*self.TIER_ONE[:2], ("Kyle Lowry", "lowryky01", "G", 1.6), ("P.J. Tucker", "tuckepj01", "F", 1.8))
        draft = Draft(self).order("Miami Heat").requests(request(*LOWRY, date="2006-04-01", requested="draft"), self.tucker())
        _, packets, _, _ = draft.run(pool)
        options = packets["2006-draft-pick-1-wade-request"]["options"]
        self.assertEqual(list(options), ["Kyle Lowry", "P.J. Tucker", "rule"])
        self.assertAlmostEqual(sum(options.values()), 1.0, places=9)
        self.assertTrue(all(0 < v < 1 for v in options.values()))

    def test_the_live_tucker_request_asks_to_draft_him(self):
        with mock.patch.multiple(D, YEAR=2006, SEASON="2005-06", DRAFT_DATE="2006-06-28",
                                 FOLDER=Path("career/Dwyane_Wade/2005-06/09_Draft")):
            rows = {r["bbr_id"]: r for r in D.wade_requests(ROOT)}
        self.assertEqual((rows["tuckepj01"]["requested"], rows["tuckepj01"]["date"]), ("draft", "2006-04-19"))
        self.assertEqual(rows["tuckepj01"]["words"], "also tell them they better draft pj tucker")
        self.assertEqual(rows["lowryky01"]["requested"], "evaluate")


class MatchingTests(unittest.TestCase):
    def test_match_by_bbr_id_else_folded_name(self):
        pool = pool_of(("P.J. Tucker", "tuckepj01", "F", 20), ("Kyle Lowry", None, "G", 15), ("Other Player", "other01", "F", 10))
        self.assertEqual(D.match_prospect({"player": "Pat Tucker", "bbr_id": "tuckepj01"}, pool), D._key("P.J. Tucker"))
        self.assertEqual(D.match_prospect({"player": "PJ Tucker"}, pool), D._key("P.J. Tucker"))
        self.assertEqual(D.match_prospect({"player": "Kyle Lowry", "bbr_id": "lowryky01"}, pool), D._key("Kyle Lowry"))
        self.assertIsNone(D.match_prospect({"player": "Other Player", "bbr_id": "someone02"}, pool))   # same name, another id
        self.assertIsNone(D.match_prospect({"player": "Not In Class"}, pool))

    def test_a_name_only_request_is_weighed(self):
        pool = pool_of(("Alpha One", "a1", "G", 1), ("Beta Two", "b2", "F", 1.5), ("P.J. Tucker", "tuckepj01", "F", 1.8))
        record, packets, _, _ = Draft(self).order("Miami Heat").requests(request("PJ Tucker")).run(pool)
        row = record["wade_requests"]["picks"][0]["requests"][0]
        self.assertEqual(row["status"], "weighed")
        self.assertEqual(record["wade_requests"]["requests"][0]["class_player"], "P.J. Tucker")
        base = D._options({k: D.utility(pool[k], context()) for k in pool})
        self.assertAlmostEqual(odds(packets["2006-draft-pick-1"]["options"]["P.J. Tucker"]) / odds(base[D._key("P.J. Tucker")]), 1.8, places=3)

    def test_the_live_2006_requests_parse(self):
        path = ROOT / "career/Dwyane_Wade/2005-06/09_Draft" / D.REQUESTS_FILE
        if not path.is_file():
            self.skipTest("Wade's 2006 scouting requests are not recorded")
        with mock.patch.multiple(D, YEAR=2006, SEASON="2005-06", DRAFT_DATE="2006-06-28",
                                 FOLDER=Path("career/Dwyane_Wade/2005-06/09_Draft")):
            rows = D.wade_requests(ROOT)
        self.assertEqual({r["bbr_id"] for r in rows}, {"lowryky01", "tuckepj01"})


class WatchListTests(unittest.TestCase):
    def test_the_watch_list_follows_each_requested_prospect(self):
        pool = pool_of(("Alpha One", "a1", "G", 1), ("Beta Two", "b2", "F", 1.5), ("Kyle Lowry", "lowryky01", "G", 1.8),
                       ("Gamma Three", "g3", "C", 25), ("P.J. Tucker", "tuckepj01", "F", 40))
        engine = Engine({"2006-draft-pick-1": "Kyle Lowry"})
        record, _, watched, _ = Draft(self).order("Miami Heat", "Alpha", "Beta").requests(
            request(*LOWRY), request(*TUCKER), request("Nobody Here", "nobodhe01")).run(pool, engine)
        self.assertEqual(watched, record["scouting_watch_list"])
        lowry, tucker, nobody = watched
        board = {b["player"]: b for b in record["board"]}
        self.assertEqual((lowry["outcome"], lowry["pick"], lowry["round"], lowry["club"], lowry["by_miami"]),
                         ("drafted", 1, 1, "Miami Heat", True))
        self.assertEqual((lowry["board_tier"], lowry["consensus_slot"]), (board["Kyle Lowry"]["tier"], 1.8))
        self.assertEqual(lowry["weighed_at_miami_picks"], [1])
        self.assertEqual(lowry["summary"], "drafted No. 1 (round 1) by Miami Heat")
        self.assertEqual((tucker["outcome"], tucker["board_tier"], tucker["consensus_slot"]),
                         ("undrafted", board["P.J. Tucker"]["tier"], 40))
        self.assertIn("P.J. Tucker", record["undrafted"])
        self.assertEqual((nobody["outcome"], nobody["in_class"], nobody["board_tier"]), ("not_in_class", False, None))
        miami = record["wade_requests"]["picks"][0]["requests"]
        self.assertEqual([n["status"] for n in miami], ["weighed", "outside_tier", "not_in_class"])

    def test_the_watch_list_reads_the_record_not_the_board_rule(self):
        """A hand-made record: the list repeats its picks, board and undrafted list, whatever a recomputation would say."""
        record = {"draft": "2006 NBA Draft", "picks": [{"pick": 35, "round": 2, "club": "Beta", "player": "P.J. Tucker",
                                                        "bbr_id": "tuckepj01"}],
                  "undrafted": ["Kyle Lowry"],
                  "board": [{"player": "Kyle Lowry", "tier": 4, "consensus_slot": 27.5},
                            {"player": "P.J. Tucker", "tier": 5, "consensus_slot": 38.25}],
                  "wade_requests": {"requests": [{"player": "Kyle Lowry", "bbr_id": "lowryky01", "class_player": "Kyle Lowry"},
                                                 {"player": "PJ Tucker", "bbr_id": "tuckepj01", "class_player": "P.J. Tucker"}],
                                    "picks": [{"pick": 20, "requests": [{"player": "Kyle Lowry", "status": "outside_tier"},
                                                                        {"player": "PJ Tucker", "status": "weighed"}]}]}}
        lowry, tucker = D.scouting_watch_list(record)
        self.assertEqual((lowry["outcome"], lowry["board_tier"], lowry["consensus_slot"], lowry["weighed_at_miami_picks"]),
                         ("undrafted", 4, 27.5, []))
        self.assertEqual((tucker["outcome"], tucker["pick"], tucker["club"], tucker["board_tier"], tucker["weighed_at_miami_picks"]),
                         ("drafted", 35, "Beta", 5, [20]))
        self.assertEqual(D.scouting_watch_list({"picks": [], "board": []}), [])


if __name__ == "__main__":
    unittest.main()
