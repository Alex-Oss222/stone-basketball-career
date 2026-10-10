"""All-Star weekend engine inputs (`runtime/all_star_engine.py`, `scripts/build_all_star_engine.py`): the exhibition rules,
the kernel additions that act only when their key is present, the built environment and translation, the profile check,
and the calibration probe. Replay safety comes first: a synthetic NBA game of each era and a FIBA game, resolved with fixed
test entropy, keep the digests they had on the base commit, and two committed requests keep their input fingerprints."""
import hashlib
import json
from pathlib import Path
import unittest
from unittest import mock

from runtime.kernel import PlayerInput, TeamInput, calibrate, resolve_game, validate_result
from runtime.packets import canonical
from runtime.player_stats import RATE_KEYS
from runtime.trajectories import TRAJECTORY_MODEL_VERSION

ROOT = Path(__file__).resolve().parents[1]
POSITIONS = ("PG", "SG", "SF", "PF", "C")
MINUTES = (36, 34, 32, 30, 28, 24, 20, 16, 12, 8)
# Computed on the base commit (5ae4368534) before any All-Star change; the same code must reproduce them exactly.
PINNED = {"nba_2004_05": "f49bd91972b8ec92a563747233c2d0020342d1bff4563b273d09937388ebbb6c",
          "nba_2003_04": "ceb1068dbeb62716005a3c4aec533a42c6e69d623d783871060a6651290f123c",
          "fiba": "53dd25fed8d7cc6a13ab5abee48f8b86b6763327f92f1153547baebd629cb0cf"}
FINGERPRINTS = {
    "career/Dwyane_Wade/2003-04/06_Regular_Season/02_February/Week_2/Game_1.request.json":
        "612968513491b1393c497c184423e86194bd0064dac4de851066fb21c796e238",
    "career/Dwyane_Wade/FIBA/Continental_Cups/2005/Games/fiba-amc05-g02.request.json":
        "ee3d5582eace42d54e80b0775424ae453677d27978873d9ba466bc3b5a203583",
}


def synthetic_team(tag, baselines, season_end_year, full=48, extra=None):
    """Ten players with fixed rates around the environment's baselines and fixed defensive values."""
    players = []
    scale = full / 48
    total = sum(MINUTES)
    for i, minutes in enumerate(MINUTES):
        tilt = 1 + 0.04 * ((i % 5) - 2)
        rates = {k: round(min(baselines[k] * tilt, 0.95 if k.endswith("_pct") else 10), 6) for k in RATE_KEYS}
        profile = {"bbr_id": f"{tag.lower()}{i:02d}", "model_version": TRAJECTORY_MODEL_VERSION, "as_of": "2004-10-01",
                   "season_end_year": season_end_year, "source_sha256": "0" * 64, "rates": rates,
                   "defense": round(1.5 - 0.3 * i, 2), **(extra or {})}
        players.append(PlayerInput(f"{tag} {i}", POSITIONS[i % 5], minutes * 240 * scale / total, {}, profile))
    return TeamInput(tag, tuple(players), starters=tuple(p.player_id for p in players[:5]))


def digest(result):
    return hashlib.sha256(canonical(result)).hexdigest()


class ReplaySafetyTests(unittest.TestCase):
    def nba(self, season, day, end_year, label):
        from runtime.era import environment_for, rules_for
        from runtime.spatial_shots import load_spatial_environment
        env = environment_for(season, day, ROOT)
        home = synthetic_team("Home", env["player_rate_baselines"], end_year)
        away = synthetic_team("Away", env["player_rate_baselines"], end_year)
        return resolve_game(home, away, entropy=hashlib.sha256(label.encode()).digest(), event_id=label,
                            rules=rules_for(season), environment=env, venue="home",
                            spatial_environment=load_spatial_environment(season, day, ROOT))

    def test_nba_games_keep_their_base_commit_digests(self):
        self.assertEqual(digest(self.nba("2004-05", "2005-01-15", 2005, "pinned-nba")), PINNED["nba_2004_05"])
        self.assertEqual(digest(self.nba("2003-04", "2004-01-15", 2004, "pinned-nba-2004")), PINNED["nba_2003_04"])

    def test_a_fiba_game_keeps_its_base_commit_digest(self):
        from runtime.era import national_rules
        from runtime.national_engine import national_environment, national_spatial
        day = "2005-08-31"
        env = national_environment(day, ROOT)
        home = synthetic_team("Home", env["player_rate_baselines"], 2005, 40, {"fiba_model": "fiba-2006.1"})
        away = synthetic_team("Away", env["player_rate_baselines"], 2005, 40, {"fiba_model": "fiba-2006.1"})
        r = resolve_game(home, away, entropy=hashlib.sha256(b"pinned-fiba").digest(), event_id="pinned-fiba",
                         rules=national_rules(day), environment=env, game_type="continental_qualifier", venue="neutral",
                         spatial_environment=national_spatial(day, ROOT))
        self.assertEqual(digest(r), PINNED["fiba"])

    def test_committed_requests_keep_their_input_fingerprints(self):
        from runtime.game_requests import input_fingerprint
        for rel, want in FINGERPRINTS.items():
            with self.subTest(request=rel):
                self.assertEqual(input_fingerprint(ROOT / rel, ROOT), want)

    def test_nba_and_fiba_rules_are_untouched(self):
        from runtime.era import national_rules, rules_for
        self.assertEqual(rules_for("2004-05")["foul_out_limit"], 6)
        self.assertNotIn("competition", rules_for("2005-06"))
        self.assertEqual(national_rules("2005-08-31")["competition"], "FIBA")

    def test_calibrate_is_unchanged_without_a_defense_intensity(self):
        from runtime.era import environment_for
        env = environment_for("2005-06", "2006-01-15", ROOT)
        self.assertNotIn("defense_intensity", env["engine_assumptions"])
        base = calibrate(env)
        off = calibrate(dict(env, engine_assumptions=dict(env["engine_assumptions"], defense_intensity=0.0)))
        self.assertEqual(off["make_per_defense"], 0.0)
        self.assertEqual(off["tov_per_defense"], 0.0)
        self.assertEqual({k: v for k, v in off.items() if not k.endswith("_per_defense")},
                         {k: v for k, v in base.items() if not k.endswith("_per_defense")})

    def test_the_clock_factor_scales_only_the_half_court_possession(self):
        from runtime.era import environment_for
        from runtime.national_engine import national_environment
        env = environment_for("2005-06", "2006-01-15", ROOT)
        for e in (env, national_environment("2005-08-31", ROOT)):
            self.assertNotIn("possession_seconds_factor", e["engine_assumptions"])
        base = calibrate(env)
        fast = calibrate(dict(env, engine_assumptions=dict(env["engine_assumptions"], possession_seconds_factor=0.97)))
        self.assertAlmostEqual(fast["possession_seconds"], base["possession_seconds"] * 0.97, places=12)
        self.assertEqual({k: v for k, v in fast.items() if k != "possession_seconds"},
                         {k: v for k, v in base.items() if k != "possession_seconds"})


class RulesTests(unittest.TestCase):
    def test_the_all_star_game_is_a_standard_nba_game(self):
        from runtime.era import exhibition_rules
        r = exhibition_rules("all_star", "2004-02-15")
        self.assertEqual((r["quarters"], r["quarter_minutes"], r["overtime_minutes"], r["foul_out_limit"],
                          r["game_day_actives"], r["season"]), (4, 12, 5, 6, 12, "2003-04"))
        self.assertEqual(r["competition"], "NBA All-Star Weekend")

    def test_the_rookie_challenge_has_two_halves_and_no_foul_outs(self):
        from runtime.era import exhibition_rules
        r = exhibition_rules("rookie_challenge", "2006-02-17")
        self.assertEqual((r["quarters"], r["quarter_minutes"], r["overtime_minutes"], r["foul_out_limit"],
                          r["game_day_actives"], r["season"]), (2, 20, 2, None, 9, "2005-06"))

    def test_a_date_outside_the_rows_fails_closed(self):
        from runtime.era import exhibition_rules
        for game_type, day in (("all_star", "2007-02-18"), ("rookie_challenge", "2003-02-08"), ("summer", "2004-02-13")):
            with self.subTest(game=game_type, day=day), self.assertRaises(ValueError):
                exhibition_rules(game_type, day)

    def test_nobody_fouls_out_or_sits_with_fouls_in_the_rookie_challenge(self):
        from runtime.all_star_engine import exhibition_environment, exhibition_spatial
        from runtime.era import exhibition_rules
        day = "2005-02-18"
        rules, env = exhibition_rules("rookie_challenge", day), exhibition_environment("rookie_challenge", day, ROOT)
        base = env["player_rate_baselines"]
        foulers = {"fouls_per_minute": 0.6}                       # a foul every two minutes on the floor
        def team(tag):
            players = []
            for i, m in enumerate((40, 40, 40, 40, 20, 20)):
                rates = dict({k: base[k] for k in RATE_KEYS}, **foulers)
                profile = {"bbr_id": f"{tag}{i}", "model_version": TRAJECTORY_MODEL_VERSION, "as_of": day,
                           "season_end_year": 2005, "source_sha256": "0" * 64, "rates": rates}
                players.append(PlayerInput(f"{tag} {i}", POSITIONS[i % 5], float(m), {}, profile))
            return TeamInput(tag, tuple(players))
        env = dict(env, averages=dict(env["averages"], pf=40.0))
        seen = 0
        for i in range(10):
            r = resolve_game(team("A"), team("B"), entropy=hashlib.sha256(f"no-foul-outs:{i}".encode()).digest(),
                             event_id=f"no-foul-outs-{i}", rules=rules, environment=env, game_type="rookie_challenge",
                             venue="neutral", spatial_environment=exhibition_spatial(day, ROOT))
            self.assertEqual(validate_result(r), [])          # its 20-minute halves pass the shot-clock checks
            rows = [p for side in ("home", "away") for p in r["player_stats"][side]]
            self.assertFalse(any(p["fouled_out"] for p in rows))
            seen = max(seen, max(p["pf"] for p in rows))
            for side in ("home", "away"):
                starters = [p for p in r["player_stats"][side] if p["minutes"] >= 38]
                self.assertGreaterEqual(len(starters), 3)        # 40-minute players play through their fouls
        self.assertGreaterEqual(seen, 6)


class EngineFileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import scripts.build_all_star_engine as B
        cls.B = B

    def test_the_built_files_are_current(self):
        """A locked game's file is the one its lock recorded; an unlocked game's is a fresh build."""
        from runtime.all_star_engine import engine_path
        from runtime.all_star_games import engine_digest, read_record
        for season, game_type in self.B.CONFIG:
            with self.subTest(season=season, game=game_type):
                game = read_record(ROOT, season)["games"].get(game_type)
                if game is not None:
                    self.assertEqual(game["engine"], engine_path(season, game_type).as_posix())
                    self.assertEqual(engine_digest(ROOT, game), game["engine_sha256"])
                    continue
                built = json.loads(json.dumps(self.B.build(season, game_type), sort_keys=True))
                self.assertEqual(json.loads((ROOT / engine_path(season, game_type)).read_text(encoding="utf-8")), built)

    def test_a_locked_games_file_is_never_rewritten(self):
        real = self.B.build

        def corrected(season, game_type, root=ROOT):                # a later research or builder change
            out = real(season, game_type, root)
            out["environment"]["purpose"] += " (corrected)"
            return out
        with mock.patch.object(self.B, "build", corrected):
            stale, kept = self.B.refresh(ROOT, write=False)
            self.assertEqual(stale, [])
            self.assertEqual(kept, [f"{s}-{g}" for s, g in self.B.CONFIG])
            with mock.patch.object(self.B, "locked", lambda *a, **k: False):
                self.assertEqual(self.B.refresh(ROOT, write=False)[0], [f"{s}-{g}" for s, g in self.B.CONFIG])

    def test_a_later_game_needs_the_previous_years_research(self):
        for game_type, day in (("all_star", "2007-02-18"), ("rookie_challenge", "2007-02-16")):
            with self.subTest(game=game_type), self.assertRaisesRegex(ValueError, "2006 .* is not researched"):
                self.B.baseline(game_type, day)
        self.assertEqual([g["year"] for g in self.B.baseline("all_star", "2000-02-13")], [1998])   # 1999: the lockout

    def test_a_missing_anchor_season_is_refused(self):
        games = self.B.baseline("all_star", "2006-02-19")
        line = next(p for t in games[-1]["teams"].values() for p in t["players"] if self.B._usable(p))
        real = self.B._read

        def thinner(path, root=ROOT):
            data = real(path, root)
            if path == self.B.ANCHORS:                       # his 2004-05 season unresearched, his others kept
                data = dict(data, players=dict(data["players"], **{line["bbr_id"]: {
                    k: v for k, v in data["players"][line["bbr_id"]].items() if k != games[-1]["season"]}}))
            return data
        with mock.patch.object(self.B, "_read", thinner), self.assertRaisesRegex(ValueError, "no 2004-05 season"):
            self.B.anchors(games)

    def test_every_baseline_is_published_before_the_game(self):
        from runtime.all_star_engine import engine_path
        want = {("2003-04", "all_star"): [1998, 2000, 2001, 2002, 2003], ("2004-05", "all_star"): [2000, 2001, 2002, 2003, 2004],
                ("2005-06", "all_star"): [2001, 2002, 2003, 2004, 2005], ("2003-04", "rookie_challenge"): [2001, 2002, 2003],
                ("2004-05", "rookie_challenge"): [2001, 2002, 2003, 2004],
                ("2005-06", "rookie_challenge"): [2001, 2002, 2003, 2004, 2005]}
        for (season, game_type), years in want.items():
            e = json.loads((ROOT / engine_path(season, game_type)).read_text(encoding="utf-8"))
            self.assertEqual(e["environment"]["baseline"], [f"{y}-{game_type}" for y in years])
            self.assertLess(e["environment"]["published_after"], e["game_date"])
            self.assertLess(e["translation"]["published_after"], e["game_date"])
            self.assertEqual(e["environment"]["engine_assumptions"]["defense_intensity"], 0.0)
            self.assertEqual(e["environment"]["engine_assumptions"]["possession_seconds_factor"], self.B.CLOCK_FACTOR)

    def test_the_real_wade_is_never_an_anchor_and_2000_is_never_a_baseline(self):
        games = self.B.baseline("rookie_challenge", "2006-02-17")
        self.assertNotIn(2000, [g["year"] for g in games])
        for season, game_type in self.B.CONFIG:
            pairs = self.B.anchors(self.B.baseline(game_type, self.B.game_date(season, game_type)))
            self.assertFalse([p for p, *_ in pairs if p.get("bbr_id") == "wadedw01" or p.get("protagonist_real_history")])
        flagged = [p for g in self.B.editions().values() for t in g["teams"].values() for p in t["players"]
                   if p.get("bbr_id") == "wadedw01"]
        self.assertEqual(len(flagged), 3)                           # 2004 and 2005 Rookie Challenges, 2005 All-Star Game
        self.assertTrue(all(p["protagonist_real_history"] for p in flagged))

    def test_the_minutes_templates(self):
        from runtime.all_star_engine import engine_path
        want = {("2003-04", "all_star"): ([30, 28, 26, 23, 19], [23, 20, 18, 17, 14, 13, 9]),
                ("2004-05", "all_star"): ([31, 28, 26, 23, 19], [24, 21, 17, 16, 14, 12, 9]),
                ("2005-06", "all_star"): ([30, 28, 25, 22, 18], [24, 21, 18, 17, 14, 13, 10]),
                ("2003-04", "rookie_challenge"): ([28, 26, 25, 23, 23], [22, 19, 17, 17]),
                ("2004-05", "rookie_challenge"): ([29, 27, 25, 24, 23], [21, 19, 17, 15]),
                ("2005-06", "rookie_challenge"): ([29, 27, 25, 24, 23], [21, 19, 17, 15])}
        for (season, game_type), (starters, reserves) in want.items():
            m = json.loads((ROOT / engine_path(season, game_type)).read_text(encoding="utf-8"))["minutes"]
            self.assertEqual((m["starters"], m["reserves"]), (starters, reserves))
            self.assertEqual(sum(starters + reserves), m["team_minutes"])

    def test_the_fitted_values(self):
        from runtime.all_star_engine import engine_path
        t = json.loads((ROOT / engine_path("2003-04", "all_star")).read_text(encoding="utf-8"))["translation"]
        self.assertEqual(t["anchors"], 119)
        self.assertAlmostEqual(t["shift"]["two_point_pct"], 0.088, places=3)       # unshrunk
        self.assertAlmostEqual(t["raw"]["three_point_pct"], -0.102, places=3)
        self.assertLess(abs(t["shift"]["three_point_pct"]), abs(t["raw"]["three_point_pct"]))   # shrunk
        self.assertAlmostEqual(t["ratio"]["free_throw_attempt_rate"], 0.432, places=3)
        self.assertAlmostEqual(t["ratio"]["turnovers_per_fga"], 1.104, places=3)
        rc = json.loads((ROOT / engine_path("2003-04", "rookie_challenge")).read_text(encoding="utf-8"))
        self.assertEqual(rc["translation"]["anchors"], 54)
        self.assertAlmostEqual(rc["environment"]["averages"]["points"], 113.0, places=3)
        self.assertAlmostEqual(rc["environment"]["averages"]["fga"], 93.667, places=3)


class ProfileTests(unittest.TestCase):
    def test_translate_moves_percentages_by_logit_and_rates_by_ratio(self):
        from runtime.all_star_engine import translate
        profile = {"bbr_id": "x", "rates": {k: 0.5 if k.endswith("_pct") else 0.2 for k in RATE_KEYS}, "defense": 1.0}
        tr = {"model_version": "m", "shift": {"two_point_pct": 0.4, "three_point_pct": 0.0, "free_throw_pct": -0.4},
              "ratio": {k: 2.0 for k in ("three_point_attempt_rate", "free_throw_attempt_rate", "turnovers_per_fga",
                                          "fouls_per_minute", "usage_pct", "assist_pct", "offensive_rebound_pct",
                                          "defensive_rebound_pct", "steal_pct", "block_pct")}}
        out = translate(profile, tr)
        self.assertAlmostEqual(out["rates"]["two_point_pct"], 0.598688, places=5)
        self.assertEqual(out["rates"]["three_point_pct"], 0.5)
        self.assertAlmostEqual(out["rates"]["free_throw_pct"], 0.401312, places=5)
        self.assertEqual(out["rates"]["turnovers_per_fga"], 0.4)
        self.assertEqual(out["exhibition_model"], "m")
        self.assertEqual(out["defense"], 1.0)
        self.assertEqual(translate({}, tr), {})

    def test_the_exhibition_packet_checks_every_profile(self):
        from runtime.game_requests import load_request
        from runtime.game_runner import build_game_packet
        from dataclasses import replace
        path = ROOT / "career/Dwyane_Wade/Stats_and_Awards/League/2005-06/All_Star/Games/2006-02-17-rookie-challenge.request.json"
        home, away, kw = load_request(path, ROOT)
        bent = replace(home, players=(replace(home.players[0], stat_profile=dict(
            home.players[0].stat_profile, rates=dict(home.players[0].stat_profile["rates"], two_point_pct=0.9))),)
            + home.players[1:])
        with self.assertRaisesRegex(ValueError, "exhibition profile differs"):
            build_game_packet(bent, away, validation_only=True, **kw)
        bare = replace(home, players=(replace(home.players[0], stat_profile={}),) + home.players[1:])
        with self.assertRaisesRegex(ValueError, "needs every player's profile"):
            build_game_packet(bare, away, validation_only=True, **kw)
        with self.assertRaisesRegex(ValueError, "neutral court"):
            build_game_packet(home, away, validation_only=True, **dict(kw, venue="home"))

    def test_a_profile_is_the_nba_profile_of_the_date(self):
        from runtime.all_star_engine import nba_profile
        from runtime.game_requests import load_request
        miami = json.loads((ROOT / "career/Dwyane_Wade/2005-06/06_Regular_Season/02_February/Week_3/Game_1.request.json")
                           .read_text(encoding="utf-8"))
        side = "home" if miami["home"]["team"] == "Miami Heat" else "away"
        frozen = next(p for p in miami["frozen"][side]["players"] if p["player_id"] == "Dwyane Wade")["stat_profile"]
        self.assertEqual(nba_profile("wadedw01", "2006-02-19", ROOT), frozen)
        home, _, _ = load_request(ROOT / "career/Dwyane_Wade/2005-06/11_All_Star/All_Star_Game/Game_1.request.json", ROOT)
        wade = next(p for p in home.players if p.player_id == "Dwyane Wade").stat_profile
        self.assertEqual(wade["exhibition_model"], "all-star-2006.1")
        self.assertEqual({k: wade[k] for k in ("bbr_id", "model_version", "as_of", "season_end_year")},
                         {k: frozen[k] for k in ("bbr_id", "model_version", "as_of", "season_end_year")})


class CalibrationTests(unittest.TestCase):
    """The acceptance probe: synthetic rosters at the anchors' mean season rates, translated by the built file, at the
    game's template minutes, resolved with test entropy; per-team totals scaled to regulation against the environment."""
    GAMES = 150

    def test_the_environment_is_reproduced(self):
        import scripts.build_all_star_engine as B
        from runtime.all_star_engine import edition, exhibition_environment, exhibition_spatial, translate
        from runtime.era import exhibition_rules
        keys = {"pts": "points", "fga": "fga", "tpa": "three_pa", "fta": "fta", "orb": "orb", "drb": "drb", "ast": "ast",
                "stl": "stl", "tov": "tov", "pf": "pf"}
        seasons = json.loads((ROOT / B.ANCHORS).read_text(encoding="utf-8"))["players"]
        for season, game_type in B.CONFIG:
            day = B.game_date(season, game_type)
            games = B.baseline(game_type, day)
            rows = [seasons[p["bbr_id"]][g["season"]] for g in games for t in g["teams"].values() for p in t["players"]
                    if B._usable(p) and seasons.get(p.get("bbr_id") or "", {}).get(g["season"], {}).get("minutes", 0) >= B.ANCHOR_MINUTES]
            total = lambda k: sum(r[k] for r in rows)
            mean = {"two_point_pct": total("x2p") / total("x2pa"), "three_point_pct": total("x3p") / total("x3pa"),
                    "free_throw_pct": total("ft") / total("fta"), "three_point_attempt_rate": total("x3pa") / total("fga"),
                    "free_throw_attempt_rate": total("fta") / total("fga"), "turnovers_per_fga": total("tov") / total("fga"),
                    "fouls_per_minute": total("pf") / total("minutes")}
            for k in ("usage_pct", "assist_pct", "offensive_rebound_pct", "defensive_rebound_pct", "steal_pct", "block_pct"):
                mean[k] = sum(r[k] * r["minutes"] for r in rows) / total("minutes")
            e = edition(game_type, day, ROOT)
            rules, env, spatial = exhibition_rules(game_type, day), exhibition_environment(game_type, day, ROOT), exhibition_spatial(day, ROOT)
            minutes = e["minutes"]["starters"] + e["minutes"]["reserves"]
            def team(tag):
                players = []
                for i, m in enumerate(minutes):
                    profile = {"bbr_id": f"{tag}{i}", "model_version": TRAJECTORY_MODEL_VERSION, "as_of": day,
                               "season_end_year": int(season[:4]) + 1, "source_sha256": "0" * 64,
                               "rates": {k: mean[k] for k in RATE_KEYS}}
                    players.append(PlayerInput(f"{tag} {i}", POSITIONS[i % 5], float(m), {}, translate(profile, e["translation"])))
                return TeamInput(tag, tuple(players), starters=tuple(p.player_id for p in players[:5]))
            sums = {k: 0.0 for k in keys}
            regulation = rules["quarters"] * rules["quarter_minutes"] * 60
            for i in range(self.GAMES):
                r = resolve_game(team("H"), team("A"), entropy=hashlib.sha256(f"calibration:{season}:{game_type}:{i}".encode()).digest(),
                                 event_id=f"calibration-{i}", rules=rules, environment=env, game_type=game_type,
                                 venue="neutral", spatial_environment=spatial)
                for side in ("home", "away"):
                    for k in keys:
                        sums[k] += r["team_stats"][side][k] * regulation / r["game_seconds"]
            for k, env_key in keys.items():
                sim, target = sums[k] / (2 * self.GAMES), env["averages"][env_key]
                band = 0.03 if k in ("pts", "fga") else 0.10           # the NBA path's 3%; other counts: docs/engine_model.md
                with self.subTest(season=season, game=game_type, count=k):
                    self.assertLess(abs(sim / target - 1), band, f"{sim:.1f} against {target:.1f}")


if __name__ == "__main__":
    unittest.main()
