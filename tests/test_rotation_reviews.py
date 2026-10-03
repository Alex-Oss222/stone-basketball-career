import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from runtime import camp, rotation_reviews as reviews, season_games
from runtime.private_service import Store, play_decision


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")


def line(name, minutes=30, points=10):
    row = {k: 0 for k in ("pts", "fgm", "fga", "tpm", "tpa", "ftm", "fta", "orb", "drb", "ast", "stl", "blk", "tov", "pf")}
    row.update(player_id=name, seconds=minutes * 60, pts=points, fgm=points // 2,
               fga=points // 2, ftm=points % 2, fta=points % 2)
    return row


class StaffScoreTests(unittest.TestCase):
    def test_minutes_blend_the_fixed_prior_not_games_or_starts(self):
        players = [{"player": "Dwyane Wade"}, {"player": "Eddie Jones"}, {"player": "Unplayed"}]
        priors = {p["player"]: 10 for p in players}
        result = {"home": reviews.MIAMI, "player_stats": {"home": [line("Dwyane Wade", 15, 10), line("Eddie Jones", 30, 20)]}}
        scores, evidence = reviews.staff_scores(players, priors, [result])
        self.assertAlmostEqual(scores["Dwyane Wade"], (10 * 300 + 20 * 15) / 315, places=5)
        self.assertGreater(scores["Eddie Jones"], scores["Dwyane Wade"])
        self.assertEqual(evidence["Dwyane Wade"]["observed_per_30"], evidence["Eddie Jones"]["observed_per_30"])
        self.assertEqual(scores["Unplayed"], 10)
        for _ in range(29):
            result["player_stats"]["home"].append(line("Dwyane Wade", 15, 10))
        sustained, _ = reviews.staff_scores(players, priors, [result])
        self.assertGreater(sustained["Dwyane Wade"], scores["Dwyane Wade"] + 4)
        with self.assertRaisesRegex(ValueError, "preseason staff estimate"):
            reviews.staff_scores(players, {}, [])
        with self.assertRaisesRegex(ValueError, "nonfinite"):
            reviews.staff_scores(players, {**priors, "Dwyane Wade": float("nan")}, [])

    def test_close_battles_ignore_incumbency_draft_slot_and_order(self):
        players = [{"player": "Eddie Jones", "positions": ["SG"], "draft_slot": 10, "starter": True},
                   {"player": "Dwyane Wade", "positions": ["SG"], "draft_slot": 5, "starter": False}]
        for scores in ({"Eddie Jones": 10, "Dwyane Wade": 10}, {"Eddie Jones": -10, "Dwyane Wade": -10.5},
                       {"Eddie Jones": 0, "Dwyane Wade": 0}):
            first = reviews.battle_packets(players, scores, "2003-11-07")
            second = reviews.battle_packets(list(reversed(players)), scores, "2003-11-07")
            self.assertEqual(first, second)
            self.assertEqual(len(first), 1)
            self.assertEqual(sum(first[0]["options"].values()), 1)
        self.assertEqual(reviews.battle_packets(players, {"Eddie Jones": 10, "Dwyane Wade": 15}, "2003-11-07"), [])
        self.assertEqual(reviews.battle_packets(players, {"Eddie Jones": 15, "Dwyane Wade": 10}, "2003-11-07"), [])


class DatedReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.base = self.root / season_games.season_base()
        self.depth = reviews.depth_dir(self.root)
        self.players = [{"player": name, "positions": [pos], "status": "roster"} for name, pos in
                        (("Point Guard", "PG"), ("Eddie Jones", "SG"), ("Caron Butler", "SF"),
                         ("Lamar Odom", "PF"), ("Brian Grant", "C"), ("Dwyane Wade", "SG"), ("Backup Point", "PG"))]
        self.priors = {p["player"]: 10 for p in self.players}
        self.priors["Backup Point"] = 4
        self.priors["Dwyane Wade"] = 8
        depth = camp.depth_chart_from({"players": self.players}, self.priors, {}, "2003-10-24")
        rotation = camp.season_rotation({"players": self.players}, depth, self.priors, "2003-10-24")
        save(self.depth / "rotation.json", rotation)
        save(self.depth / "depth_chart.json", depth)
        save(self.base / "00_Team/Team/Roster/roster.json", {"as_of": "2003-10-24", "players": [
            {"name": p["player"], "positions": p["positions"], "status": "under_contract"} for p in self.players]})
        save(self.base / "04_Training_Camp/camp_roster.json", {"evaluated": "2003-10-24", "staff_scores": self.priors})
        self.games = [{"date": day, "game_id": day + "-game", "home": reviews.MIAMI, "away": "Boston Celtics"}
                      for day in ("2003-10-28", "2003-11-07", "2003-11-20", "2003-11-21", "2003-12-05")]
        save(self.root / "library/2003/league/nba_2003_04_schedule.json", {"games": self.games})
        for game in self.games:
            (self.root / season_games.week_dir(game["date"])).mkdir(parents=True, exist_ok=True)

    def game_record(self, index=0, status="played", points=10, terminated=True):
        game = self.games[index]
        folder = self.root / season_games.week_dir(game["date"])
        path = folder / f"Game_{index + 1}.md"
        text = season_games.game_note(index + 1, game, "home").replace("status: scheduled", "status: " + status)
        if status == "not_played":
            text = text.replace("reason:\n", "reason: canceled\n")
        path.write_text(text, encoding="utf-8")
        result = {"event_id": game["game_id"], "game_date": game["date"], "game_type": "regular",
                  "home": game["home"], "away": game["away"], "terminated": terminated,
                  "player_stats": {"home": [line(p["player"], 30, points if p["player"] == "Dwyane Wade" else 10)
                                             for p in self.players], "away": []}}
        save(path.with_suffix(".result.json"), result)
        return path

    def test_closed_notes_only_exclude_raw_same_day_future_and_canceled_games(self):
        path = self.game_record(status="scheduled")
        self.game_record(1, points=100)
        self.game_record(4, points=100)
        results, _, pending = reviews.closed_evidence("2003-11-07", self.root)
        self.assertEqual(results, [])
        self.assertEqual(pending, [self.games[0]["game_id"]])
        with self.assertRaisesRegex(ValueError, "awaiting closed"):
            reviews.write_review("2003-11-07", self.root)
        self.game_record(status="played", terminated=False)
        self.assertEqual(len(reviews.closed_evidence("2003-11-07", self.root)[2]), 1)
        self.game_record(status="played")
        results, sources, pending = reviews.closed_evidence("2003-11-07", self.root)
        self.assertEqual([r["event_id"] for r in results], [self.games[0]["game_id"]])
        self.assertEqual(len(sources[0]["sha256"]), 64)
        self.assertEqual(pending, [])
        self.game_record(status="not_played")
        self.assertEqual(reviews.closed_evidence("2003-11-07", self.root), ([], [], []))
        path.write_text(path.read_text().replace("reason: canceled", "reason:"))
        self.assertTrue(reviews.closed_evidence("2003-11-07", self.root)[2])

    def test_dated_rotation_clear_winner_and_prior_requests_stay_unchanged(self):
        path = self.game_record(points=90)
        request_path = path.with_suffix(".request.json")
        baseline = (self.depth / "rotation.json").read_bytes()
        old_request = season_games.miami_request(self.games[0], json.loads(baseline)["players"])
        save(request_path, old_request)
        before = request_path.read_bytes()
        with self.assertRaisesRegex(ValueError, "review due 2003-11-07"):
            season_games.miami_side("2003-11-07", self.root)
        self.assertEqual(reviews.write_review("2003-11-07", self.root), [])
        rotation, _ = reviews.rotation_in_force("2003-11-07", self.root)
        self.assertEqual(rotation["starters"]["SG"], "Dwyane Wade")
        self.assertEqual(sum(p["starter"] for p in rotation["players"]), 5)
        self.assertAlmostEqual(sum(p["minutes"] for p in rotation["players"]), 240)
        self.assertEqual(reviews.rotation_in_force("2003-11-06", self.root)[0]["as_of"], "2003-10-24")
        self.assertEqual((self.depth / "rotation.json").read_bytes(), baseline)
        with patch("runtime.game_requests.load_request"):
            season_games.build_miami("2003-11-07", self.root, write=True)
        self.assertEqual(request_path.read_bytes(), before)
        self.assertEqual(reviews.review_errors(self.root), [])
        closed = reviews.review_dir("2003-11-07", self.root) / "rotation.json"
        old_rotation = closed.read_bytes()
        self.assertEqual(reviews.write_review("2003-11-07", self.root), [])
        self.assertEqual(closed.read_bytes(), old_rotation)
        self.assertEqual(reviews.review_dates("2003-12-31", self.root), ["2003-11-07", "2003-11-21", "2003-12-05"])
        # Same-day/newer results do not retroactively enter the frozen decision.
        self.game_record(1, points=100)
        self.assertEqual(reviews.write_review("2003-11-07", self.root), [])
        self.assertEqual(closed.read_bytes(), old_rotation)

    def test_engine_draw_is_required_and_rerun_cannot_change_packet(self):
        self.game_record(points=30)
        pending = reviews.write_review("2003-11-07", self.root)
        self.assertEqual(len(pending), 1)
        folder = reviews.review_dir("2003-11-07", self.root)
        request = folder / f"{pending[0]}.decision.json"
        packet = json.loads(request.read_text())
        self.assertFalse((folder / "rotation.json").exists())
        self.assertEqual(reviews.write_review("2003-11-07", self.root), pending)
        store = Store(self.root / "test-decisions.sqlite3")
        store.initialize()
        status, answer = play_decision(store, packet)
        self.assertEqual(status, "decided")
        self.assertEqual(play_decision(store, packet)[0], "already_decided")
        result_path = request.with_name(request.name.replace(".decision.json", ".decision.result.json"))
        save(result_path, {**answer, "date": "2003-11-08"})
        with self.assertRaisesRegex(ValueError, "unchanged staff battle packet"):
            reviews.write_review("2003-11-07", self.root)
        save(result_path, answer)
        self.assertEqual(reviews.write_review("2003-11-07", self.root), [])
        self.assertEqual(reviews.rotation_in_force("2003-11-07", self.root)[0]["starters"]["SG"], answer["outcome"])
        self.assertEqual(reviews.review_errors(self.root), [])
        # Editing old canonical production cannot reselect a winner.
        self.game_record(points=90)
        self.assertTrue(reviews.review_errors(self.root))
        with self.assertRaisesRegex(ValueError, "closed evidence differs"):
            reviews.write_review("2003-11-07", self.root)

    def test_pending_evidence_and_saved_outputs_are_immutable(self):
        self.game_record(points=30)
        reviews.write_review("2003-11-07", self.root)
        frozen = reviews.review_dir("2003-11-07", self.root) / "review.json"
        before = frozen.read_bytes()
        self.game_record(points=90)
        with self.assertRaisesRegex(ValueError, "closed evidence differs"):
            reviews.write_review("2003-11-07", self.root)
        self.assertEqual(frozen.read_bytes(), before)
        with self.assertRaisesRegex(ValueError, "earlier staff review"):
            reviews.write_review("2003-11-21", self.root)

    def test_prior_is_fixed_across_reviews_and_pending_roster_is_frozen(self):
        self.game_record(points=30)
        pending = reviews.write_review("2003-11-07", self.root)
        folder = reviews.review_dir("2003-11-07", self.root)
        packet_path = folder / f"{pending[0]}.decision.json"
        packet = json.loads(packet_path.read_text())
        camp_path = self.base / "04_Training_Camp/camp_roster.json"
        save(camp_path, {"evaluated": "2003-10-24", "staff_scores": {**self.priors, "Dwyane Wade": 99}})
        roster_path = self.base / "00_Team/Team/Roster/roster.json"
        roster = json.loads(roster_path.read_text())
        roster["as_of"] = "2003-11-08"
        save(roster_path, roster)
        store = Store(self.root / "test-decisions.sqlite3")
        store.initialize()
        _, result = play_decision(store, packet)
        save(packet_path.with_name(packet_path.name.replace(".decision.json", ".decision.result.json")), result)
        self.assertEqual(reviews.write_review("2003-11-07", self.root), [])
        self.game_record(1, points=90)
        self.game_record(2, points=90)
        self.assertEqual(reviews.write_review("2003-11-21", self.root), [])
        snapshot = json.loads((reviews.review_dir("2003-11-21", self.root) / "review.json").read_text())
        self.assertEqual(snapshot["evidence"]["Dwyane Wade"]["preseason_estimate"], 8)
        self.assertEqual(reviews.review_errors(self.root), [])
        latest_path = reviews.review_dir("2003-11-21", self.root) / "review.json"
        changed = {**snapshot, "season": "2099-00"}
        save(latest_path, changed)
        self.assertEqual(reviews.rotation_in_force("2003-11-07", self.root)[0]["as_of"], "2003-11-07")
        self.assertTrue(any("season differs" in error for error in reviews.review_errors(self.root)))
        save(latest_path, snapshot)
        # A later valid rotation cannot hide a changed older battle answer.
        result_path = packet_path.with_name(packet_path.name.replace(".decision.json", ".decision.result.json"))
        result_path.unlink()
        with self.assertRaisesRegex(ValueError, "before all engine battle draws"):
            reviews.rotation_in_force("2003-11-21", self.root)

    def test_departure_between_reviews_promotes_backup_without_inventing_injury(self):
        self.game_record(points=90)
        reviews.write_review("2003-11-07", self.root)
        path = self.base / "00_Team/Team/Roster/roster.json"
        roster = json.loads(path.read_text())
        for player in roster["players"]:
            if player["name"] == "Dwyane Wade":
                player["status"] = "traded"
        roster["as_of"] = "2003-11-08"
        save(path, roster)
        players, injuries = season_games.miami_side("2003-11-20", self.root)
        self.assertNotIn("Dwyane Wade", [p["player_id"] for p in players])
        self.assertTrue(next(p for p in players if p["player_id"] == "Eddie Jones")["starter"])
        self.assertEqual(sum(p["starter"] for p in players), 5)
        self.assertEqual(injuries, {})
        with self.assertRaisesRegex(ValueError, "historical roster"):
            season_games.miami_side("2003-11-07", self.root)

    def test_builder_refuses_orphan_or_missing_played_request(self):
        folder = self.root / season_games.week_dir("2003-10-28")
        path = folder / "Game_1.request.json"
        save(path, {"event_id": "immutable-orphan"})
        before = path.read_bytes()
        with self.assertRaisesRegex(ValueError, "orphan request/result"):
            season_games.build_miami("2003-10-28", self.root, write=True)
        self.assertEqual(path.read_bytes(), before)
        path.unlink()
        self.game_record()
        with self.assertRaisesRegex(ValueError, "cannot reconstruct"):
            season_games.build_miami("2003-10-28", self.root, write=True)

    def test_tampered_completed_scores_and_rotation_are_refused(self):
        self.game_record(points=90)
        reviews.write_review("2003-11-07", self.root)
        folder = reviews.review_dir("2003-11-07", self.root)
        path = folder / "review.json"
        snapshot = json.loads(path.read_text())
        snapshot["scores"]["Dwyane Wade"] = 1000
        save(path, snapshot)
        self.assertTrue(any("staff scores differ" in error for error in reviews.review_errors(self.root)))
        with self.assertRaisesRegex(ValueError, "staff scores differ"):
            reviews.rotation_in_force("2003-11-07", self.root)

    def test_orphan_rotation_cannot_bypass_review_and_future_chart_is_refused(self):
        folder = reviews.review_dir("2003-11-07", self.root)
        save(folder / "rotation.json", json.loads((self.depth / "rotation.json").read_text()))
        self.assertEqual(reviews.pending_reviews("2003-11-07", self.root), ["2003-11-07"])
        self.assertTrue(reviews.review_errors(self.root))
        with self.assertRaisesRegex(ValueError, "review due"):
            reviews.rotation_in_force("2003-11-07", self.root)
        chart = json.loads((self.depth / "depth_chart.json").read_text())
        chart["as_of"] = "2003-11-06"
        save(self.depth / "depth_chart.json", chart)
        with self.assertRaisesRegex(ValueError, "historical depth chart"):
            reviews.rotation_in_force("2003-11-01", self.root)


if __name__ == "__main__":
    unittest.main()
