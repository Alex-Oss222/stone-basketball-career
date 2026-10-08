"""Wade's pursue requests in the summer market from the 2006 summer (runtime/free_agency_2004.py, docs/front_office.md,
Wade's requests): Miami renounces lesser cap holds to reach a free agent Wade asked it to pursue, and his own request
answers the franchise consultation for that player. The 2004 and 2005 recorded markets replay unchanged.

The flow tests run on a small stand-in market (no live records are read or written): a temporary root holds the
request file, the consultation folder and the season state, and Wade's standing is patched to `franchise`.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from runtime import consultations as C
from runtime import free_agency_2004 as fa

ROOT = Path(__file__).resolve().parents[1]
MIAMI, SEATTLE = fa.MIAMI, "Seattle SuperSonics"
DAY = "2005-08-05"                       # on or after the 2005 context's CAP_KNOWN: the market plans on the stand-in cap
CAP, MINIMUM = 50_000_000, 1_000_000
FRANCHISE = {"standing": "franchise", "as_of": "2006-06-20"}
WORDS = "Bring Ray Star to Miami on a multi-year plan."
NAMES = {"star01": "Ray Star", "other01": "Second Star", "low01": "Low Hold", "mid01": "Mid Hold", "upp01": "Upper Hold",
         "top01": "Top Hold", "big01": "Big Hold", **{f"m{i}": f"Miami Player {i}" for i in range(1, 6)}}
VALUES = {"star01": 25.0, "other01": 24.0, "low01": 6.0, "mid01": 8.0, "upp01": 10.0, "top01": 11.0, "big01": 30.0,
          **{f"m{i}": 9.0 for i in range(1, 6)}}
PRICES = {"star01": 12_000_000, "other01": 11_000_000, "low01": 3_000_000, "mid01": 4_000_000, "upp01": 5_000_000,
          "top01": 2_500_000, "big01": 15_000_000}
PRIOR = {"low01": 2_000_000, "mid01": 3_000_000, "upp01": 4_000_000, "top01": 1_000_000, "big01": 4_000_000}
HOLDS = {b: int(round(PRIOR[b] * fa.HOLD_SHARE)) for b in PRIOR}   # low 3.0M, mid 4.5M, upp 6.0M, top 1.5M, big 6.0M


class Pricing:
    evidence = {}

    def value(self, b):
        return VALUES[b]

    def age(self, b):
        return 28


def market(root, pool=("star01", "low01", "mid01", "upp01", "top01", "big01")):
    """A stand-in summer: Miami pays $30M to five players against a $50M cap and holds its own five free agents
    ($21M of holds, room -$1M); Ray Star (value 25, price $12M) is Seattle's free agent."""
    m = object.__new__(fa.Market)
    m.root = Path(root)
    m.cal = {"cap": CAP, "tax": 70_000_000, "mle": 5_000_000, "charlotte_cap": CAP,
             "minimum": {s: MINIMUM for s in range(11)}, "scale": {}}
    m.ident = {b: {"name": n, "position": "SG", "service": 5} for b, n in NAMES.items()}
    m.pricing = Pricing()
    m.prior = dict(PRIOR)
    m.contracts = {f"m{i}": {"club": MIAMI, "salary": 6_000_000, "years": 2, "route": "existing", "source": "test"} for i in range(1, 6)}
    m.contracts["other01"] = {"club": SEATTLE, "salary": 11_000_000, "years": 2, "route": "existing", "source": "test"}
    m.pool = sorted(pool)
    m.price = {b: PRICES[b] for b in pool}
    m.rights = {b: MIAMI for b in pool if b in PRIOR}
    m.rights["star01"] = SEATTLE
    m.qualifying, m.renounced, m.mle_used = {}, {}, set()
    m.events, m.pending = [], False
    m.standings, m.june_payroll, m.trait = {}, {MIAMI: 30_000_000}, {}
    return m


def write_requests(root, *rows):
    path = Path(root) / fa.REQUESTS
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"requests": list(rows)}), encoding="utf-8")


def pursue(bbr_id="star01", date="2005-06-16", **extra):
    return dict({"date": date, "subject": "free_agent_target", "player": NAMES[bbr_id], "bbr_id": bbr_id,
                 "requested": "pursue", "term": "multi_year", "words": WORDS}, **extra)


def write_state(root):
    path = Path(root) / f"career/Dwyane_Wade/{fa.SEASON}/current_state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"current_date": DAY, "pending_player_decisions": []}), encoding="utf-8")
    return path


class Summer(unittest.TestCase):
    """Each test runs inside the 2005 market context (its dates and paths); `later` lifts YEAR to 2006 on top."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.enter(fa.year_context(2005, ROOT))
        self.enter(mock.patch("runtime.standing.standing_on", return_value=dict(FRANCHISE)))
        self.state = write_state(self.root)

    def enter(self, cm):
        cm.__enter__()
        self.addCleanup(cm.__exit__, None, None, None)

    def later(self):
        self.enter(mock.patch.object(fa, "YEAR", 2006))


class RenunciationTests(Summer):
    def test_order_and_stop_rule(self):
        self.later()
        write_requests(self.root, pursue())
        m = market(self.root)
        room = CAP - 30_000_000 - sum(HOLDS.values())
        self.assertEqual(room, -1_000_000)
        # lowest value first, only as many as needed: 3.0M + 4.5M + 6.0M covers the $13M gap; Top Hold (11) is kept
        self.assertEqual(m.renunciation(MIAMI, "star01", DAY, 12_000_000), ["low01", "mid01", "upp01"])
        self.assertEqual(m.renunciation(MIAMI, "star01", DAY, 2_000_000), ["low01"])
        # a $4M gap: Low Hold (3.0M) is picked first, Mid Hold (4.5M) completes it and alone covers it, so Low Hold stays
        self.assertEqual(m.renunciation(MIAMI, "star01", DAY, 3_000_000), ["mid01"])
        # every hold below the target (15M) cannot reach a $21M gap; Big Hold (value 30) would, and is never renounced
        self.assertEqual(m.renunciation(MIAMI, "star01", DAY, 20_000_000), [])
        # a player already offered this round, or one Wade asked Miami to keep, is passed over
        self.assertEqual(m.renunciation(MIAMI, "star01", DAY, 10_000_000, {"low01"}), ["mid01", "upp01", "top01"])
        write_requests(self.root, pursue(), {"date": "2005-06-16", "subject": "re_sign", "player": "Mid Hold",
                                             "bbr_id": "mid01", "requested": "keep"})
        self.assertEqual(m.renunciation(MIAMI, "star01", DAY, 9_000_000), ["low01", "upp01", "top01"])
        # room that already pays him renounces nothing
        m.cal["cap"] = 70_000_000
        self.assertEqual(m.renunciation(MIAMI, "star01", DAY, 12_000_000), [])

    def play(self, m, answers, seattle=()):
        """One market round on the stand-in: Miami's real offers, Seattle's given ones (cap room), and each player's
        answer from `answers` (wait when unnamed or when the named club made him no offer)."""
        real = m.offers_for
        m.offers_for = lambda club, week, day, open_players: (
            [{"club": SEATTLE, "bbr_id": b, "salary": s, "years": 2, "route": "cap_room", "ask": m.ask(b, week)} for b, s in seattle]
            if club == SEATTLE else real(club, week, day, open_players))
        m.clubs = [MIAMI, SEATTLE]
        m.assess = lambda b, o, week: (1.0, None)
        packets = {}

        def draw(root, packet):
            b = next(x for x, n in NAMES.items() if packet["event_id"].endswith(fa._slug(n)))
            packets[b] = packet
            answer = answers.get(b, "wait")
            return answer if answer in packet["options"] else "wait"

        with mock.patch.object(fa, "_draw", draw):
            self.assertTrue(m.round(0, DAY))
        return packets

    def test_offer_carries_the_plan_and_renounces_nothing(self):
        self.later()
        write_requests(self.root, pursue())
        m = market(self.root)
        out = m.offers_for(MIAMI, 0, DAY, sorted(m.pool))
        offer = next(o for o in out if o["bbr_id"] == "star01")
        self.assertEqual((offer["salary"], offer["route"], offer["renounce"]), (12_000_000, "cap_room", ["low01", "mid01", "upp01"]))
        self.assertEqual([e for e in m.events if e["kind"] == "renounce"], [])
        self.assertEqual({b for b, c in m.rights.items() if c == MIAMI}, set(PRIOR))

    def test_holds_go_when_he_accepts(self):
        self.later()
        write_requests(self.root, pursue())
        m = market(self.root)
        m.qualifying["mid01"] = {"club": MIAMI, "amount": 3_750_000}
        # Seattle's sheet to Mid Hold, Miami's restricted free agent, is accepted the same day
        packets = self.play(m, {"star01": MIAMI, "mid01": SEATTLE}, seattle=[("mid01", 4_000_000)])
        self.assertEqual(set(packets["star01"]["options"]), {MIAMI, "wait"})
        renounced = [e for e in m.events if e["kind"] == "renounce"]
        self.assertEqual([e["bbr_id"] for e in renounced], ["low01", "mid01", "upp01"])
        self.assertTrue(all(e["date"] == DAY and e["club"] == MIAMI and e["for_bbr_id"] == "star01" and e["offer"] == 12_000_000
                            for e in renounced))
        self.assertEqual([e["hold"] for e in renounced], [HOLDS["low01"], HOLDS["mid01"], HOLDS["upp01"]])
        self.assertEqual(renounced[1]["qualifying_offer_withdrawn"], 3_750_000)
        # the renouncements come before any signing that day: Mid Hold's sheet is no longer Miami's to match
        kinds = [e["kind"] for e in m.events]
        self.assertLess(max(i for i, k in enumerate(kinds) if k == "renounce"), min(i for i, k in enumerate(kinds) if k != "renounce"))
        self.assertFalse([e for e in m.events if e["kind"].startswith("offer_sheet")])
        self.assertEqual((m.contracts["mid01"]["club"], m.contracts["star01"]["club"]), (SEATTLE, MIAMI))
        self.assertEqual(m.contracts["star01"]["route"], "cap_room")
        signed = {e["bbr_id"]: e for e in m.events if e["kind"] == "signing"}
        self.assertEqual((signed["mid01"]["club"], signed["mid01"]["from"]), (SEATTLE, MIAMI))
        self.assertTrue(all("renounce" not in o for o in [m.contracts["star01"], signed["star01"]]))
        # the Bird rights end (he may come back only with room or an exception); the rest keep theirs
        for b in ("low01", "mid01", "upp01"):
            self.assertNotIn(b, m.rights)
            self.assertEqual(m.renounced[b], MIAMI)
        self.assertNotEqual(m.means(MIAMI, "low01", DAY, PRICES["low01"]), "bird")
        self.assertNotIn("mid01", m.qualifying)
        self.assertEqual((m.rights["top01"], m.rights["big01"]), (MIAMI, MIAMI))
        self.assertLessEqual(m.payroll(MIAMI) + m.holds(MIAMI, DAY), CAP)       # the star's salary fits the room made
        self.assertEqual(m.profile("low01", 0)["prior_club"], MIAMI)          # renouncing ends rights, not his ties

    def test_holds_stay_when_he_waits_or_goes_elsewhere(self):
        for answer, seattle in (("wait", ()), (SEATTLE, [("star01", 13_000_000)])):
            with self.subTest(answer=answer):
                self.later()
                write_requests(self.root, pursue())
                m = market(self.root)
                m.qualifying["mid01"] = {"club": MIAMI, "amount": 3_750_000}
                packets = self.play(m, {"star01": answer}, seattle=seattle)
                self.assertIn(MIAMI, packets["star01"]["options"])            # Miami's offer was made
                self.assertEqual([e for e in m.events if e["kind"] == "renounce"], [])
                self.assertEqual({b for b, c in m.rights.items() if c == MIAMI}, set(PRIOR))
                self.assertEqual(m.qualifying["mid01"]["club"], MIAMI)
                self.assertEqual(m.renounced, {})
                self.assertEqual(m.contracts.get("star01", {}).get("club"), None if answer == "wait" else SEATTLE)

    def test_no_offer_that_round_to_a_hold_in_the_plan(self):
        self.later()
        late = {"low01", "top01"}                         # their asks have fallen to the minimum: each would get a minimum offer
        for requested in (False, True):
            with self.subTest(requested=requested):
                write_requests(self.root, *([pursue()] if requested else [pursue("other01")]))
                m = market(self.root)
                m.ask = lambda b, week: MINIMUM if b in late else PRICES[b]
                offers = {o["bbr_id"]: o for o in m.offers_for(MIAMI, 0, DAY, sorted(m.pool))}
                self.assertEqual(offers["top01"]["route"], "minimum")
                if requested:
                    self.assertEqual(offers["star01"]["renounce"], ["low01", "mid01", "upp01"])
                    self.assertNotIn("low01", offers)          # planned: kept off the round's offers
                else:
                    self.assertNotIn("star01", offers)
                    self.assertEqual(offers["low01"]["route"], "minimum")

    def test_no_renunciation_without_a_request(self):
        self.later()
        write_requests(self.root, pursue("other01"))                         # Wade asked for someone else
        m = market(self.root, pool=("star01", "low01", "mid01", "upp01", "top01"))
        self.assertEqual(m.renunciation(MIAMI, "star01", DAY, 12_000_000), [])
        out = m.offers_for(MIAMI, 0, DAY, sorted(m.pool))
        self.assertNotIn("star01", [o["bbr_id"] for o in out])               # the mid-level is below 70% of his ask
        self.assertEqual([e for e in m.events if e["kind"] == "renounce"], [])
        self.assertEqual({b for b, c in m.rights.items() if c == MIAMI}, {"low01", "mid01", "upp01", "top01"})


class GateTests(unittest.TestCase):
    def test_gate_leaves_2004_and_2005_alone(self):
        """The same request and holds in a 2004 or 2005 market context renounce nothing (the recorded summers)."""
        for year in (2004, 2005):
            with self.subTest(year=year), tempfile.TemporaryDirectory() as tmp, fa.year_context(year, ROOT), \
                    mock.patch("runtime.standing.standing_on", return_value=dict(FRANCHISE)):
                self.assertEqual(fa.YEAR, year)
                write_requests(tmp, pursue())
                write_state(tmp)
                m = market(tmp)
                self.assertEqual(m.renunciation(MIAMI, "star01", DAY, 12_000_000), [])
                out = m.offers_for(MIAMI, 0, DAY, sorted(m.pool))
                self.assertNotIn("star01", [o["bbr_id"] for o in out])
                self.assertEqual([e for e in m.events if e["kind"] == "renounce"], [])
                self.assertEqual(m.renounced, {})
                self.assertEqual({b for b, c in m.rights.items() if c == MIAMI}, set(PRIOR))


class ConsultationTests(Summer):
    def record(self, cid):
        return json.loads((C.folder(self.root, fa.SEASON) / f"{cid}.json").read_text(encoding="utf-8"))

    def test_request_answers_the_consultation(self):
        self.later()
        write_requests(self.root, pursue())
        m = market(self.root)
        self.assertTrue(m.consulted(MIAMI, "star01", DAY, 12_000_000))
        self.assertFalse(m.pending)
        r = self.record(C.consultation_id(DAY, "free_agent", "Ray Star"))
        self.assertEqual((r["date"], r["answer"], r["answered"], r["status"]), (DAY, "approve", DAY, "closed"))
        self.assertEqual(r["answered_by_request"]["source"], fa.REQUESTS.as_posix())
        self.assertEqual((r["answered_by_request"]["date"], r["answered_by_request"]["words"]), ("2005-06-16", WORDS))
        self.assertIn(WORDS, r["note"])
        page = (C.folder(self.root, fa.SEASON) / C.page_name(r)).read_text(encoding="utf-8")
        self.assertIn("status: closed", page)
        self.assertEqual(json.loads(self.state.read_text())["pending_player_decisions"], [])
        self.assertEqual(C.consultation_errors(self.root), [])
        self.assertTrue(C.approved(self.root, fa.SEASON, "free_agent", "Ray Star", DAY))
        self.assertTrue(m.consulted(MIAMI, "star01", DAY, 12_000_000))         # a replay finds the answer, writes nothing new
        self.assertEqual(len(C.records(self.root, fa.SEASON)), 1)

    def test_unrequested_star_is_still_asked(self):
        self.later()
        write_requests(self.root, pursue())
        m = market(self.root, pool=("star01", "other01"))
        m.rights["other01"] = SEATTLE
        self.assertFalse(m.consulted(MIAMI, "other01", DAY, 11_000_000))
        self.assertTrue(m.pending)
        r = self.record(C.consultation_id(DAY, "free_agent", "Second Star"))
        self.assertIsNone(r["answer"])
        self.assertIn(C.PENDING_PREFIX + r["id"], json.loads(self.state.read_text())["pending_player_decisions"])

    def test_objection_stands_over_a_request(self):
        self.later()
        write_requests(self.root, pursue())
        folder = C.folder(self.root, fa.SEASON)
        folder.mkdir(parents=True)
        cid = C.consultation_id("2005-07-01", "free_agent", "Ray Star")
        (folder / f"{cid}.json").write_text(json.dumps({"id": cid, "date": "2005-07-01", "kind": "free_agent", "player": "Ray Star",
                                                        "answer": "object", "answered": "2005-07-02"}), encoding="utf-8")
        m = market(self.root)
        self.assertFalse(m.consulted(MIAMI, "star01", DAY, 12_000_000))
        self.assertFalse(m.pending)
        self.assertEqual(len(C.records(self.root, fa.SEASON)), 1)

    def test_2005_request_does_not_answer(self):
        write_requests(self.root, pursue())
        m = market(self.root)
        self.assertFalse(m.consulted(MIAMI, "star01", DAY, 12_000_000))
        self.assertTrue(m.pending)
        self.assertIsNone(self.record(C.consultation_id(DAY, "free_agent", "Ray Star"))["answer"])

    def test_trade_consultation_needs_a_trade_request(self):
        self.later()
        m = market(self.root, pool=("star01",))
        row = {"id": f"2006-summer-trade-{DAY}-m1-other01", "clubs": [MIAMI, SEATTLE],
               "a": {"club": MIAMI, "sends": ["Miami Player 1"], "bbr_ids": ["m1"], "salary": 6_000_000},
               "b": {"club": SEATTLE, "sends": ["Second Star"], "bbr_ids": ["other01"], "salary": 11_000_000}}
        write_requests(self.root, pursue("other01"))                         # a free-agent request covers signings only
        self.assertEqual(m.trade_consulted(row, DAY), "asked")
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.state = write_state(self.root)
        m = market(self.root, pool=("star01",))
        write_requests(self.root, {"date": "2005-07-20", "subject": "trade_target", "player": "Second Star",
                                   "words": "Get Second Star if Seattle will deal him."})
        self.assertEqual(m.trade_consulted(row, DAY), "ok")
        r = self.record(C.consultation_id(DAY, "trade", "Second Star"))
        self.assertEqual((r["answer"], r["trade_id"], r["club"]), ("approve", row["id"], SEATTLE))
        self.assertEqual(C.consultation_errors(self.root), [])


class RecordedSummerReplayTests(unittest.TestCase):
    def test_2005_market_replays_unchanged(self):
        """The recorded 2005 summer, replayed from its recorded draws with every write refused, gives the same record."""
        def recorded(root, packet):
            path = Path(root) / fa.DRAWS / f"{packet['event_id']}.decision.result.json"
            self.assertTrue(path.is_file(), f"no recorded draw {packet['event_id']}")
            return json.loads(path.read_text(encoding="utf-8"))["outcome"]

        def refuse(*args, **kwargs):
            raise AssertionError("the replay tried to write")

        with fa.year_context(2005, ROOT), mock.patch.object(fa, "_draw", recorded), mock.patch.object(fa, "_write", refuse), \
                mock.patch.object(C, "ask", refuse):
            path = ROOT / fa.RECORD
            if not path.is_file():
                self.skipTest("no recorded 2005 market")
            stored = json.loads(path.read_text(encoding="utf-8"))
            replay = fa.Market(ROOT, stored["to"]).run()
        self.assertFalse([e for e in replay["events"] if e["kind"] == "renounce"])
        for key in ("events", "clubs", "payroll", "unsigned_pool", "left_the_league"):
            self.assertEqual(replay[key], stored[key], key)


if __name__ == "__main__":
    unittest.main()
