"""Staff starters survive request loading and actual injury starts feed closed records."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from runtime import season_games, standing
from runtime.career_stats import aggregate, collect_games
from runtime.era import environment_for, rules_for
from runtime.game_requests import _club
from runtime.kernel import PlayerInput, TeamInput, resolve_game, team_packet, validate_result


ROOT = Path(__file__).resolve().parents[1]
GAME_DATE = "2003-11-01"


def rotation():
    names = ["Lead Guard", "Eddie Jones", "Starting Wing", "Starting Forward", "Starting Center",
             "Reserve Guard", "Dwyane Wade", "Reserve Wing", "Reserve Forward", "Reserve Center"]
    positions = ["PG", "SG", "SF", "PF", "C"] * 2
    minutes = [34, 34, 34, 34, 34, 18, 16, 12, 12, 12]
    return {"as_of": "2003-10-27", "players": [
        {"player_id": name, "position": pos, "minutes": mpg, "ratings": {}}
        for name, pos, mpg in zip(names, positions, minutes)
    ]}


def explicit_club(players):
    return _club({"team": "Miami Heat", "players": players}, 12, ROOT, None)


class StarterRequestTests(unittest.TestCase):
    def test_legacy_request_keeps_absent_starter_input(self):
        club = explicit_club(rotation()["players"])
        self.assertEqual(club.starters, ())
        self.assertNotIn("starters", team_packet(club))

    def test_explicit_starters_are_frozen_in_packet(self):
        players = rotation()["players"]
        for i, player in enumerate(players):
            player["starter"] = i < 5
        club = explicit_club(players)
        expected = tuple(p["player_id"] for p in players[:5])
        self.assertEqual(club.starters, expected)
        self.assertEqual(tuple(team_packet(club)["starters"]), expected)

    def test_partial_non_boolean_or_wrong_count_flags_are_rejected(self):
        baseline = rotation()["players"]
        for i, player in enumerate(baseline):
            player["starter"] = i < 5
        for change in ("missing", None, "yes", 1, False):
            players = deepcopy(baseline)
            if change == "missing":
                players[0].pop("starter")
            else:
                players[0]["starter"] = change
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, "starter"):
                explicit_club(players)


class InjuryStartsTests(unittest.TestCase):
    def play(self, injured):
        players = season_games.rotation_for(rotation(), injured, {})
        home = explicit_club(players)
        away = TeamInput("Opponent", tuple(
            PlayerInput("Opponent " + p["player_id"], p["position"], p["minutes"])
            for p in rotation()["players"]))
        result = resolve_game(home, away, entropy=b"injury-start-test" * 2, event_id="test-injury-start",
                              rules=rules_for("2003-04"), environment=environment_for("2003-04", GAME_DATE))
        result["game_date"] = GAME_DATE
        self.assertEqual(validate_result(result), [])
        return home, result

    def test_injury_replacement_starts_even_below_other_bench_minute_targets(self):
        healthy, healthy_result = self.play({})
        self.assertNotIn("Dwyane Wade", healthy.starters)
        self.assertFalse(next(p for p in healthy_result["player_stats"]["home"]
                              if p["player_id"] == "Dwyane Wade")["started"])
        injured, injury_result = self.play({"Eddie Jones": 2})
        self.assertIn("Dwyane Wade", injured.starters)
        self.assertNotIn("Eddie Jones", [p.player_id for p in injured.players])
        targets = {p.player_id: p.minutes for p in injured.players}
        self.assertLess(targets["Dwyane Wade"], targets["Reserve Guard"])
        wade = next(p for p in injury_result["player_stats"]["home"] if p["player_id"] == "Dwyane Wade")
        self.assertTrue(wade["started"])
        for side in ("home", "away"):
            self.assertEqual(sum(p["started"] for p in injury_result["player_stats"][side]), 5)

    def test_closed_injury_start_counts_for_standing_at_season_close_after_rotation_changes(self):
        _, result = self.play({"Eddie Jones": 2})
        with tempfile.TemporaryDirectory() as directory:
            player = Path(directory) / "career/Dwyane_Wade"
            week = player / "2003-04/06_Regular_Season/11_November/Week_1"
            week.mkdir(parents=True)
            source = week / "Game_1.result.json"
            source.write_text(json.dumps(result))
            original = source.read_bytes()
            scores = result["final_score"]
            outcome = "W" if scores["home"] > scores["away"] else "L"
            note = week / "Game_1.md"
            note.write_text(
                "---\ntype: game\nstatus: played\ndate: 2003-11-01\nopponent: Opponent\n"
                "venue: home\ncompetition: regular\nplayer_team: Miami Heat\n"
                f"result: {outcome} {scores['home']}-{scores['away']}\n"
                "event_id: test-injury-start\nresult_file: Game_1.result.json\n---\n\n# Game\n")
            # The current rotation again gives Jones the job. It cannot rewrite who started earlier.
            current = player / "2003-04/00_Team/Team/Depth_Chart/rotation.json"
            current.parent.mkdir(parents=True)
            current.write_text(json.dumps(rotation()))
            identity = json.loads((ROOT / "career/Dwyane_Wade/professional_identity.json").read_text())
            records = collect_games(player, identity, GAME_DATE)
            self.assertEqual((aggregate(records)["gp"], aggregate(records)["gs"]), (1, 1))
            close_date = "2004-04-15"
            (player / "2003-04/season_close.json").write_text(json.dumps({
                "season": "2003-04", "close_date": close_date, "regular_season_games_scheduled": 2}))
            # GS is immediate; standing keeps its established closed-season timing.
            closed_before = standing.closed_seasons(Path(directory), GAME_DATE)
            self.assertEqual(closed_before, [])
            self.assertEqual(standing.classify(True, closed_before, [])[0], "rookie")
            closed = standing.closed_seasons(Path(directory), close_date)
            self.assertEqual(len(closed), 1)
            line = standing.season_line(records, closed[0]["season"],
                                        closed[0]["regular_season_games_scheduled"], close_date)
            self.assertEqual(standing.classify(True, [line], [])[0], "starter")
            self.assertEqual(source.read_bytes(), original)

    def test_historical_result_without_started_remains_unknown(self):
        # No starts are inferred from today's depth chart, minutes or player identity.
        from tests.test_career_stats import line, record
        records = [record(line(started=True)), record(line(), event_id="legacy")]
        self.assertIsNone(aggregate(records)["gs"])


if __name__ == "__main__":
    unittest.main()
