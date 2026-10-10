"""Tie draw packets share one rule (`runtime/decisions.equal_shares`): equal chances that sum to exactly 1, so a three-way
tie writes a packet the engine accepts, while every recorded tie packet rebuilds byte for byte."""
import json
from pathlib import Path
import re
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from runtime.decisions import decision_errors, equal_shares

ROOT = Path(__file__).resolve().parents[1]
# Each tie packet writer's decider: award_decisions, season_awards (Finals MVP), all_star_games (Rookie Challenge
# MVP), all_star (game coaches), national (FIBA group ties) and playoffs (tiebreak drawing).
TIE_DECIDERS = {"NBA league office (engine draw between equal evidence)",
                "Finals MVP media panel (engine draw between equal ballots)",
                "Rookie Challenge MVP media panel (engine draw between equal ballots)",
                "All-Star tie (engine draw between equal records)",
                "NBA drawing (engine draw)"}


def packet(options):
    return {"event_id": "tie", "date": "2006-08-20", "question": "Who?", "decider": "test", "options": options,
            "basis": "test"}


def tmp_root(test):
    root = Path(tempfile.mkdtemp(prefix="tie-draw-"))
    test.addCleanup(shutil.rmtree, root, True)
    return root


class EqualSharesTests(unittest.TestCase):
    def test_every_tie_size_is_a_valid_draw(self):
        for n in range(2, 721):                     # up to a six-team FIBA block's 720 orders
            with self.subTest(n=n):
                options = equal_shares(f"P{i}" for i in range(n))
                self.assertEqual(len(options), n)
                self.assertEqual(decision_errors(packet(options)), [])

    def test_a_size_the_old_rounding_accepted_keeps_its_exact_shares(self):
        self.assertTrue(decision_errors(packet({n: round(1 / 3, 6) for n in "ABC"})))     # the refused packet
        kept = 0
        for n in range(2, 721):
            old = {f"P{i}": round(1 / n, 6) for i in range(n)}
            if not decision_errors(packet(old)):
                kept += 1
                self.assertEqual(json.dumps(equal_shares(old)), json.dumps(old), n)
        self.assertGreater(kept, 5)                 # 2, 4, 5, 8, 10, ...

    def test_no_share_is_more_than_a_millionth_from_equal(self):
        for n in (6, 24, 120, 720, 5040):           # three- to seven-team FIBA blocks
            with self.subTest(n=n):
                options = equal_shares(f"P{i}" for i in range(n))
                self.assertEqual(decision_errors(packet(options)), [])
                self.assertLessEqual(max(options.values()) - min(options.values()), 1e-6 + 1e-12)

    def test_three_way_shares_and_order(self):
        self.assertEqual(equal_shares(["B", "A", "C"]), {"B": 0.333333, "A": 0.333333, "C": 0.333334})


class ThreeWayTiePacketTests(unittest.TestCase):
    def test_award_decisions(self):
        from runtime.award_decisions import tie_packet
        data = tie_packet("2006-07-player_of_week-2006-11-06-east", "player_of_week", "East", "2006-11-06",
                          "2006-11-12", "2006-11-13", ["A", "B", "C"])
        self.assertEqual(decision_errors(data), [])
        self.assertEqual(list(data["options"]), ["A", "B", "C"])

    def test_season_awards_finals_mvp(self):
        from runtime.season_awards import finals_tie_packet
        data = finals_tie_packet("2005-06-finals_mvp", "2006-06-20", ["A", "B", "C"])
        self.assertEqual(decision_errors(data), [])
        self.assertEqual(finals_tie_packet("x", "2006-06-20", ["A", "B"])["options"], {"A": 0.5, "B": 0.5})

    def test_all_star_game_coaches(self):
        from runtime import all_star
        root = tmp_root(self)
        c = SimpleNamespace(season="2006-07", draws=Path("Award_Draws"))
        rows = [{"result": {"game_date": "2007-02-01", "home": f"E{i}", "away": f"W{i}",
                            "final_score": {"home": 100, "away": 90}, "player_stats": {"home": [], "away": []}}}
                for i in range(3)]                  # three East clubs 1-0 and three West clubs 0-1: both level
        with mock.patch.object(all_star, "dates", lambda c: {"coach_record_through": "2007-02-04"}), \
                mock.patch.object(all_star, "_coaches_on", lambda *a: {f"{s}{i}": f"Coach {s}{i}" for s in "EW" for i in range(3)}), \
                mock.patch.object(all_star, "previous_coaches", lambda *a: set()), \
                mock.patch("runtime.seasons.conference_of", lambda season, club, root=None: "East" if club[0] == "E" else "West"):
            decision, pending = all_star.game_coaches(root, c, "2007-02-05", rows)
        self.assertIsNotNone(pending)
        packets = sorted((root / "Award_Draws").glob("*.decision.json"))
        self.assertEqual([p.name for p in packets], ["2006-07-all-star-coach-east.decision.json",
                                                      "2006-07-all-star-coach-west.decision.json"])
        for path in packets:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(len(data["options"]), 3)
            self.assertEqual(decision_errors(data), [], path.name)

    def test_national_group_tie(self):
        from runtime import national
        root = tmp_root(self)
        games = [{"home": "A", "away": "B", "home_score": 80, "away_score": 70, "stage": "group_a"},
                 {"home": "B", "away": "C", "home_score": 80, "away_score": 70, "stage": "group_a"},
                 {"home": "C", "away": "A", "home_score": 80, "away_score": 70, "stage": "group_a"}]
        e = {"slug": "test06", "family": "World_Cup", "edition": "2099", "tiebreak": "fiba_2004"}
        rec = {"draws": {}}
        with mock.patch.object(national, "group_states", lambda e, rec, closed: ({"A": (["A", "B", "C"], games, True)}, {})):
            pending = national.settle_ties(e, rec, {}, "2099-08-25", root)
        self.assertEqual(len(pending), 1)                               # one packet for the block, listed once
        data = json.loads(pending[0].read_text(encoding="utf-8"))
        self.assertEqual(len(data["options"]), 6)                     # every order of the three
        self.assertEqual(decision_errors(data), [])

    def test_playoff_tiebreak_drawing(self):
        from runtime import playoffs as P
        root = tmp_root(self)
        (root / P.rules_path("2003-04")).parent.mkdir(parents=True)
        (root / P.rules_path("2003-04")).write_text((ROOT / P.rules_path("2003-04")).read_text(encoding="utf-8"))
        t = object.__new__(P.Table)
        t.root, t.where, t.games = ROOT, P.divisions(ROOT), []
        t.clubs = sorted(t.where)
        ranker = P.Ranker(t, root)
        ranker.order(["Atlanta Hawks", "Boston Celtics", "Miami Heat"])  # load_decision refuses an invalid packet
        data = json.loads(next((root / P.draws_dir("2003-04")).glob("*.decision.json")).read_text(encoding="utf-8"))
        self.assertEqual(len(data["options"]), 3)
        self.assertEqual(decision_errors(data), [])


class RecordedTiePacketTests(unittest.TestCase):
    def recorded(self):
        out = []
        for path in sorted((ROOT / "career").rglob("*.decision.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            national_tie = data.get("decider") == "engine draw (runtime/national.py)" and "-tie-" in data["event_id"]
            if data.get("decider") in TIE_DECIDERS or national_tie:
                out.append((path, data))
        return out

    def test_every_recorded_tie_packet_keeps_its_shares(self):
        rows = self.recorded()
        self.assertGreaterEqual(len(rows), 2)        # the 2003-04 and 2004-05 Player of the Week draws at least
        for path, data in rows:
            with self.subTest(packet=path.name):
                self.assertEqual(json.dumps(equal_shares(data["options"])), json.dumps(data["options"]))

    def test_recorded_award_tie_packets_rebuild_byte_for_byte(self):
        from runtime.award_decisions import AWARDS, tie_packet
        labels = {v: k for k, v in AWARDS.items()}
        rows = [(p, d) for p, d in self.recorded() if d["decider"] == "NBA league office (engine draw between equal evidence)"]
        self.assertGreaterEqual(len(rows), 2)
        for path, data in rows:
            with self.subTest(packet=path.name):
                m = re.fullmatch(r"Who is the (\w+) (.+) for (\S+) to (\S+): (.+)\?", data["question"])
                conference, label, start, end, names = m.groups()
                rebuilt = tie_packet(data["event_id"], labels[label], conference, start, end, data["date"], names.split(" or "))
                self.assertEqual(json.dumps(rebuilt, indent=1, ensure_ascii=False) + "\n", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
