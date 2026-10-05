"""Import and isolated kernel fixtures; these never create career game requests."""
from copy import deepcopy
from dataclasses import replace
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from runtime.era import environment_for, rules_for
from runtime.game_requests import _club
from runtime.game_runner import build_game_packet
from runtime.kernel import calibrate, PlayerInput, TeamInput, resolve_game, validate_result
from runtime.league import baseline_team, load_clubs
from runtime.player_stats import (CUTOFF, MODEL_VERSION, RATINGS_PATH, RATE_KEYS, ROOT, STATS_PATH,
                                 RatingIndex, build_ratings, data_errors, load_rating_index,
                                 read_json, repository_rating_errors, sha256)
from scripts.import_veteran_stats import outputs, card_outputs


class ImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = read_json(ROOT / STATS_PATH)
        cls.ratings = read_json(ROOT / RATINGS_PATH)
        cls.index = RatingIndex(cls.ratings)

    def test_complete_unique_source_and_reproducible_outputs(self):
        self.assertEqual(len(self.data["records"]), 428)
        self.assertEqual(data_errors(self.data), [])
        self.assertEqual(repository_rating_errors(), [])
        generated, data, ratings, report = outputs()
        clock = read_json(ROOT / "career/Dwyane_Wade/2003-04/current_state.json")["current_date"]
        if clock == "2003-06-26":                         # opening cards are imported only at the checkpoint
            generated.update(card_outputs(data, ratings, report))
        for path, content in generated.items():
            with self.subTest(file=str(path)):
                self.assertEqual((ROOT/path).read_text(encoding="utf-8"), content)
        self.assertEqual(report["under_100_minutes"], 46)
        self.assertEqual(report["combined_traded_player_rows"], 27)
        self.assertGreaterEqual(len(report["miami_card_matches"]), 14)   # the 14 opening veterans plus later arrivals with a 2002-03 line

    def test_bad_counts_percent_units_future_and_duplicate_refused(self):
        mutations = [lambda d: d["records"].append(deepcopy(d["records"][0])),
                     lambda d: d["records"][0].update(season_end_year=2004),
                     lambda d: d["records"][0]["totals"].update(points=99999),
                     lambda d: d["records"][0]["advanced"].update(usage_pct=20),
                     lambda d: d["records"][0]["advanced"].update(true_shooting_pct=.8),
                     lambda d: d["records"][0].update(team_codes=[{}])]
        for mutation in mutations:
            data = deepcopy(self.data)
            mutation(data)
            with self.assertRaises(ValueError):
                build_ratings(data, "fixture")

    def test_missing_is_not_zero_and_small_sample_is_shrunk(self):
        rucker = self.index.lookup("Guy Rucker")
        self.assertIsNone(rucker["observed"]["true_shooting_pct"])
        self.assertIsNone(rucker["grades"]["two_point_pct"])
        mean = self.ratings["rate_baselines"]
        self.assertEqual(rucker["estimated"]["two_point_pct"], mean["two_point_pct"])
        self.assertLess(abs(rucker["estimated"]["assist_pct"]-mean["assist_pct"]), .003)
        for p in self.ratings["players"].values():
            for key, value in p["observed"].items():
                if value is not None:
                    estimate = p["estimated"][key]
                    self.assertGreaterEqual(estimate + 1e-12, min(value, mean[key]))
                    self.assertLessEqual(estimate - 1e-12, max(value, mean[key]))

    def test_identity_and_exclusions(self):
        self.assertEqual(self.index.lookup("eddie_jones")["bbr_id"], "jonesed02")
        self.assertEqual(self.index.lookup("jonesed02")["player_name"], "Eddie Jones")
        self.assertEqual(self.index.lookup("roster_alias", "allenra02")["player_name"], "Ray Allen")
        with self.assertRaisesRegex(ValueError, "conflicts"):
            self.index.lookup("Eddie Jones", "jordanmi01")
        self.assertEqual(self.index.engine_profile("Dwyane Wade", "wadedw01"), {})
        self.assertEqual(self.index.engine_profile("Alonzo Mourning"), {})

    def test_date_and_source_gates(self):
        with self.assertRaisesRegex(ValueError, "not available"):
            load_rating_index("2003-06-25", "2003-04")
        self.assertIsNone(load_rating_index("2005-10-28", "2005-06"))      # no baseline encoded yet
        with self.assertRaisesRegex(ValueError, "not available"):
            load_rating_index("2004-04-14", "2004-05")                       # 2003-04 totals known from April 15
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/STATS_PATH).parent.mkdir(parents=True)
            (root/STATS_PATH).write_bytes((ROOT/STATS_PATH).read_bytes() + b"\n")
            (root/RATINGS_PATH).write_bytes((ROOT/RATINGS_PATH).read_bytes())
            with self.assertRaisesRegex(ValueError, "stale"):
                load_rating_index("2003-10-28", "2003-04", root)

    def test_all_baseline_clubs_use_verified_profiles(self):
        clubs = load_clubs(ROOT / "library/2003/league/nba_2003_end_of_season.json")
        for name, club in clubs.items():
            team = baseline_team(name, club, 12, self.index)
            for p in team.players:
                self.assertTrue(p.stat_profile, (name, p.player_id))
            self.assertEqual(len({p.stat_profile["bbr_id"] for p in team.players}), len(team.players))
        explicit = _club({"team": "fixture", "players": [
            {"player_id": "eddie_jones", "bbr_id": "jonesed02", "position": "SG", "minutes": 34}]}, 12, ROOT, self.index)
        self.assertEqual(explicit.players[0].stat_profile["bbr_id"], "jonesed02")

    def test_packet_freezes_rates_environment_and_refuses_override(self):
        # Veteran path only: build packets against a library without the careers file (option C off).
        import shutil
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        shutil.copytree(ROOT / "library", root / "library", ignore=shutil.ignore_patterns("careers"))
        clubs = load_clubs(ROOT / "library/2003/league/nba_2003_end_of_season.json")
        home = baseline_team("Miami Heat", clubs["Miami Heat"], 12, self.index)
        away = baseline_team("Orlando Magic", clubs["Orlando Magic"], 12, self.index)
        packet, _, env = build_game_packet(home, away, event_id="fixture", game_date="2003-10-28", root=root)
        self.assertEqual(packet["environment"], env)
        self.assertEqual(packet["home"]["players"][0]["stat_profile"]["source_sha256"], sha256(ROOT/STATS_PATH))
        profile = deepcopy(home.players[0].stat_profile)
        profile["rates"]["free_throw_pct"] = 1
        edited = replace(home, players=(replace(home.players[0], stat_profile=profile),)+home.players[1:])
        with self.assertRaisesRegex(ValueError, "differs"):
            build_game_packet(edited, away, event_id="fixture", game_date="2003-10-28", root=root)
        overlap = replace(home, players=(replace(home.players[0], ratings={"usage": 80}),)+home.players[1:])
        with self.assertRaisesRegex(ValueError, "overlapping"):
            build_game_packet(overlap, away, event_id="fixture", game_date="2003-10-28", root=root)
        duplicate = replace(home, players=(home.players[0], replace(home.players[1], stat_profile=home.players[0].stat_profile))+home.players[2:])
        with self.assertRaisesRegex(ValueError, "duplicate Basketball-Reference"):
            build_game_packet(duplicate, away, event_id="fixture", game_date="2003-10-28", root=root)


class StatisticalKernelTests(unittest.TestCase):
    env = environment_for("2003-04", "2003-10-28")
    rules = rules_for("2003-04")

    def team(self, side, **rate_changes):
        # Artificial equal-rate clubs, not real teams or production profiles.
        rates = {k:self.env["player_rate_baselines"][k] for k in RATE_KEYS}
        rates.update(rate_changes)
        minutes = [34, 34, 34, 34, 34, 18, 16, 12, 12, 8, 4, 0]
        positions = ["PG", "SG", "SF", "PF", "C", "PG", "SG", "SF", "PF", "C", "SF", "C"]
        return TeamInput(side, tuple(PlayerInput(f"{side}_{i}", positions[i], m, stat_profile={
            "bbr_id": f"fixture{side}{chr(97+i)}01", "model_version": MODEL_VERSION,
            "as_of": CUTOFF, "season_end_year": 2003, "source_sha256": "0"*64, "rates": dict(rates)})
            for i,m in enumerate(minutes)))

    def sample(self, home, away=None, n=100):
        totals, rows = {}, {}
        for i in range(n):
            result = resolve_game(home, away or self.team("A"), entropy=hashlib.sha256(f"stat-fixture-{i}".encode()).digest(),
                                  event_id="stat-fixture", rules=self.rules, environment=self.env, venue="neutral")
            self.assertEqual(validate_result(result), [])
            for key, value in result["team_stats"]["home"].items():
                totals[key] = totals.get(key, 0) + value
            for row in result["player_stats"]["home"]:
                target = rows.setdefault(row["player_id"], {k:0 for k in ("orb", "drb", "seconds")})
                for key in target:
                    target[key] += row[key]
        return totals, rows

    def test_statistical_neutral_clubs_reproduce_environment(self):
        n = 200
        t, _ = self.sample(self.team("H"), n=n)
        for stat, target in (("pts", "points"), ("fga", "fga"), ("tpa", "three_pa"), ("fta", "fta"),
                             ("orb", "orb"), ("drb", "drb"), ("ast", "ast"), ("stl", "stl"), ("blk", "blk"), ("tov", "tov")):
            with self.subTest(stat=stat):
                self.assertAlmostEqual(t[stat]/n/self.env["averages"][target], 1, delta=.07)
        self.assertAlmostEqual(t["team_turnovers"]/n, self.env["team_turnovers_per_game"], delta=.15)

    def test_shooting_frequency_and_accuracy_are_independent(self):
        # Regular possessions use the rate less the late-game threes the late-game logic adds back.
        regular = calibrate(self.env)["regular_three_share"]
        for share in (.05, .65):
            t, _ = self.sample(self.team("H", three_point_attempt_rate=share, three_point_pct=.4))
            self.assertAlmostEqual(t["tpa"]/t["fga"], share * regular, delta=.02)
            self.assertAlmostEqual(t["tpm"]/t["tpa"], .4, delta=.065)
        for accuracy in (.15, .55):
            t, _ = self.sample(self.team("H", three_point_attempt_rate=.35, three_point_pct=accuracy))
            self.assertAlmostEqual(t["tpa"]/t["fga"], .35, delta=.02)
            self.assertAlmostEqual(t["tpm"]/t["tpa"], accuracy, delta=.03)

    def test_free_throw_drawing_and_accuracy_are_independent(self):
        observed = {}
        # Isolate ordinary foul drawing from the score-dependent intentional
        # fouls. Their calibration deduction must also be disabled: an extreme
        # FTR=.7 club often wins comfortably and never receives the late fouls
        # that restore the league-average deduction (ordinary FTR is then .660).
        # A fixed 500-game sample supplies roughly 35,000+ FGA and 8,000+ FTA
        # per condition. The tolerances are about four sampling standard errors
        # at the least precise condition, with direct independence checks below.
        with patch("runtime.kernel.FOUL_WINDOWS", ()), patch("runtime.kernel.LATE_FOUL_FTA", 0):
            for ftr in (.2, .7):
                for accuracy in (.52, .9):
                    with self.subTest(ftr=ftr, accuracy=accuracy):
                        t, _ = self.sample(self.team("H", free_throw_attempt_rate=ftr,
                                                   free_throw_pct=accuracy), n=500)
                        drawing, shooting = t["fta"] / t["fga"], t["ftm"] / t["fta"]
                        observed[ftr, accuracy] = drawing, shooting
                        self.assertAlmostEqual(drawing, ftr, delta=.03)
                        self.assertAlmostEqual(shooting, accuracy, delta=.025)
        for ftr in (.2, .7):
            self.assertAlmostEqual(observed[ftr, .52][0], observed[ftr, .9][0], delta=.04)
        for accuracy in (.52, .9):
            self.assertAlmostEqual(observed[.2, accuracy][1], observed[.7, accuracy][1], delta=.03)

    def test_offensive_and_defensive_rebound_allocations_differ(self):
        team = self.team("H")
        players = list(team.players)
        for i, orb, drb in ((3, .2, .05), (4, .02, .35)):
            profile = deepcopy(players[i].stat_profile)
            profile["rates"].update(offensive_rebound_pct=orb, defensive_rebound_pct=drb)
            players[i] = replace(players[i], stat_profile=profile)
        _, rows = self.sample(replace(team, players=tuple(players)), n=60)
        self.assertGreater(rows["H_3"]["orb"], 3*rows["H_4"]["orb"])
        self.assertGreater(rows["H_4"]["drb"], 3*rows["H_3"]["drb"])


if __name__ == "__main__":
    unittest.main()
