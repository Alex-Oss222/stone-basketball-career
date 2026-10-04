"""Dated prospect identity, generic modifiers and immutable historical inputs."""
from copy import deepcopy
from dataclasses import replace
import hashlib
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

from runtime.game_requests import load_request
from runtime.game_runner import build_game_packet, freeze_inputs, run_game
from runtime.kernel import (_Club, _expected_points, _pressure_turnover_adjustment,
                            _rebound_transition_chance, calibrate, team_errors, validate_result)
from runtime.packets import canonical
from runtime.player_stats import RATE_KEYS, STATS_PATH, load_rating_index, read_json, sha256
from runtime.prospect_scouting import (POSITION_PATH, SCOUTING_PATH, position_rebound_priors,
                                       style_errors, validate_scouting)
from runtime.prospects import (LEGACY_PROSPECTS_PATH, LEGACY_ROOKIE_MODEL_VERSION, LEGACY_ROOKIE_PATH, PROSPECTS_PATH,
                               ROOKIE_MODEL_VERSION, ROOKIE_PATH, SCOUTING_EFFECTIVE_FROM,
                               VETERAN_PATH, build_rookie_estimates, expected_rookie_estimates)
from runtime.spatial_shots import draw_spatial_shot, load_spatial_environment, zone_probabilities
from runtime.trajectories import develop_profile, development_packet
from tests.test_engine_model import ENV, RULES, games, team

ROOT = Path(__file__).resolve().parents[1]


class Journal:
    def __init__(self):
        self.packets = {}

    def close_event(self, packet):
        if packet["event_id"] in self.packets:
            assert self.packets[packet["event_id"]] == packet
        self.packets[packet["event_id"]] = deepcopy(packet)
        return hashlib.sha256(canonical(packet)).hexdigest()


def styled(roster, style):
    """Synthetic profiles for kernel unit tests, never saved as career inputs."""
    return replace(roster, players=tuple(replace(p, stat_profile=dict(
        p.stat_profile, model_version=ROOKIE_MODEL_VERSION, style=deepcopy(style),
        scouting={}, scouting_sources={})) for p in roster.players))


class ScoutingEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.scouting = read_json(ROOT / SCOUTING_PATH)
        self.prospects = read_json(ROOT / PROSPECTS_PATH)
        self.veterans = read_json(ROOT / VETERAN_PATH)
        self.current = expected_rookie_estimates(ROOT)
        self.legacy = expected_rookie_estimates(ROOT, legacy=True)
        self.generic = build_rookie_estimates(self.prospects, "fixture", self.veterans, legacy=True)

    def test_unscouted_prospect_is_exactly_the_generic_translation(self):
        generic = build_rookie_estimates(self.prospects, "fixture", self.veterans)
        self.assertEqual(generic["players"], self.generic["players"])
        empty = dict(self.scouting, players={})
        self.assertEqual(build_rookie_estimates(self.prospects, "fixture", self.veterans,
                                               scouting=empty)["players"], generic["players"])

    def test_same_evidence_on_a_different_player_gets_the_same_model(self):
        prospects, scouting = deepcopy(self.prospects), deepcopy(self.scouting)
        prospects["records"][0].update(player_id="Test Prospect", bbr_id="prospectxx01")
        scouting["players"]["prospectxx01"] = scouting["players"].pop("wadedw01")
        result = build_rookie_estimates(prospects, "fixture", self.veterans, scouting=scouting,
                                        rebound_priors=self.current["method"]["position_rebound_priors"])
        for key in ("estimated", "style"):
            self.assertEqual(result["players"]["prospectxx01"][key], self.current["players"]["wadedw01"][key])

    def test_scouting_changes_only_supported_rates(self):
        old = self.generic["players"]["wadedw01"]["estimated"]
        new = self.current["players"]["wadedw01"]["estimated"]
        affected = {"free_throw_attempt_rate", "offensive_rebound_pct", "defensive_rebound_pct"}
        for key in set(RATE_KEYS) - affected:
            self.assertEqual(old[key], new[key], key)
        self.assertGreater(new["free_throw_attempt_rate"], old["free_throw_attempt_rate"])
        self.assertGreater(new["free_throw_attempt_rate"], self.veterans["rate_baselines"]["free_throw_attempt_rate"])
        self.assertLess(new["offensive_rebound_pct"], old["offensive_rebound_pct"])
        self.assertGreater(new["defensive_rebound_pct"], old["defensive_rebound_pct"])
        totals, base = self.veterans["source_totals"], self.veterans["rate_baselines"]
        def implied_rebounds(rates):
            return sum(rates[rate] / base[rate] * totals[count] / totals["minutes"] for rate, count in (
                ("offensive_rebound_pct", "offensive_rebounds"), ("defensive_rebound_pct", "defensive_rebounds")))
        self.assertAlmostEqual(implied_rebounds(old), implied_rebounds(new), places=14)

    def test_dates_classifications_and_provenance_fail_closed(self):
        validate_scouting(self.scouting, self.prospects, ROOT)
        for target in ("dataset", "player", "trait"):
            bad = deepcopy(self.scouting)
            entry = bad["players"]["wadedw01"]
            row = bad if target == "dataset" else entry if target == "player" else entry["traits"]["paint_pressure"]
            row["as_of"] = "2003-06-27"
            with self.subTest(target=target), self.assertRaisesRegex(ValueError, "future"):
                validate_scouting(bad, self.prospects, ROOT)
        bad = deepcopy(self.scouting)
        bad["players"]["wadedw01"]["traits"]["paint_pressure"]["value"] = "elite_99"
        with self.assertRaisesRegex(ValueError, "classification"):
            validate_scouting(bad, self.prospects, ROOT)
        bad = deepcopy(self.scouting)
        bad["players"]["wadedw01"]["traits"]["paint_pressure"]["sections"] = ["Imaginary section"]
        with self.assertRaisesRegex(ValueError, "section not found"):
            validate_scouting(bad, self.prospects, ROOT)
        bad = deepcopy(self.scouting)
        bad["players"]["wadedw01"]["source_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "source changed"):
            validate_scouting(bad, self.prospects, ROOT)
        bad = deepcopy(self.scouting)
        bad["players"]["unknownxx01"] = bad["players"].pop("wadedw01")
        with self.assertRaisesRegex(ValueError, "matching"):
            validate_scouting(bad, self.prospects, ROOT)

    def test_position_priors_use_only_the_completed_prior_nba_season(self):
        stats, roster = read_json(ROOT / STATS_PATH), read_json(ROOT / POSITION_PATH)
        priors = position_rebound_priors(stats, roster)
        self.assertEqual(set(priors), {"PG", "SG", "SF", "PF", "C"})
        self.assertLess(priors["SG"]["offensive_share"], priors["C"]["offensive_share"])
        roster["season"] = 2004
        with self.assertRaisesRegex(ValueError, "future"):
            position_rebound_priors(stats, roster)

    def test_new_sources_and_generated_style_are_checked_when_loading(self):
        tampered = deepcopy(self.current)
        tampered["players"]["wadedw01"]["style"]["pressure_turnover_sensitivity"] = 1.9
        def read(path):
            return tampered if Path(path) == ROOT / ROOKIE_PATH else read_json(path)
        with patch("runtime.player_stats.read_json", side_effect=read), self.assertRaisesRegex(ValueError, "stale"):
            load_rating_index(SCOUTING_EFFECTIVE_FROM, "2003-04", ROOT)
        with patch("runtime.prospect_scouting.sha256", return_value="0" * 64), self.assertRaisesRegex(ValueError, "source changed"):
            load_rating_index(SCOUTING_EFFECTIVE_FROM, "2003-04", ROOT)


class ScoutingKernelTests(unittest.TestCase):
    def setUp(self):
        self.profile = load_rating_index(SCOUTING_EFFECTIVE_FROM, "2003-04", ROOT).engine_profile("Dwyane Wade")
        self.style = self.profile["style"]
        self.cal = calibrate(ENV)

    def test_pressure_concern_does_not_change_ordinary_or_weak_defense(self):
        base = team("H").players[0]
        concern = styled(team("H"), {"pressure_turnover_sensitivity": 1.5}).players[0]
        for defense in (0, -5):
            self.assertEqual(_pressure_turnover_adjustment(base, defense, self.cal),
                             _pressure_turnover_adjustment(concern, defense, self.cal))
        self.assertAlmostEqual(_pressure_turnover_adjustment(concern, 5, self.cal),
                               1.5 * _pressure_turnover_adjustment(base, 5, self.cal))
        roster = styled(team("H"), {"pressure_turnover_sensitivity": 1.5})
        ordinary = list(games(roster, team("A"), 3, tag="neutral-style"))
        # Keep identical packet metadata: kernel entropy includes the input
        # profiles, so changing metadata alone would change random draws.
        with patch("runtime.kernel._pressure_turnover_adjustment",
                   side_effect=lambda player, defense, cal: cal["tov_per_defense"] * defense):
            self.assertEqual(ordinary, list(games(roster, team("A"), 3, tag="neutral-style")))

    def test_pressure_concern_increases_live_turnovers_against_strong_defense(self):
        opponent = team("A", defense=2)
        ordinary = sum(g["team_stats"]["home"]["tov"] for g in games(team("H"), opponent, 60, tag="pressure-style"))
        concern = styled(team("H"), {"pressure_turnover_sensitivity": 1.5})
        pressured = sum(g["team_stats"]["home"]["tov"] for g in games(concern, opponent, 60, tag="pressure-style"))
        self.assertGreater(pressured, ordinary)

    def test_spatial_style_changes_geography_not_aggregate_accuracy(self):
        environment = load_spatial_environment("2003-04")
        weights = self.style["spatial_weights"]
        for value in (2, 3):
            for target in (0, 1e-9, .01, .2, .5, .9, .99, 1):
                result = zone_probabilities(environment, value, target, weights)
                self.assertAlmostEqual(sum(share for _, share, _ in result), 1, places=14)
                self.assertAlmostEqual(sum(share * chance for _, share, chance in result), target, places=12)
        generic = zone_probabilities(environment, 2, .5)
        paint = zone_probabilities(environment, 2, .5, weights)
        self.assertGreater(paint[0][1], generic[0][1])
        self.assertEqual(zone_probabilities(environment, 3, .359, weights),
                         zone_probabilities(environment, 3, .359))
        calls = []
        def draw(rng, env, value, target, spatial_weights=None):
            calls.append(spatial_weights)
            return draw_spatial_shot(rng, env, value, target, spatial_weights)
        with patch("runtime.kernel.draw_spatial_shot", side_effect=draw):
            game = next(games(styled(team("H"), {"spatial_weights": weights}), team("A"), 1, tag="style-locations"))
        for shot, supplied in zip(game["shots"], calls):
            self.assertEqual(supplied, weights if shot["side"] == "home" else None)

    def test_rebound_push_uses_the_rebounder_and_expected_margin(self):
        base = team("H")
        pushed = styled(base, {"rebound_transition_multiplier": 1.25})
        self.assertEqual(_rebound_transition_chance(base.players[0]), .22)
        self.assertAlmostEqual(_rebound_transition_chance(pushed.players[0]), .275)
        club = lambda t: _Club(t, "home", random.Random(0), RULES)
        self.assertGreater(_expected_points(club(pushed), club(team("A")), self.cal),
                           _expected_points(club(base), club(team("A")), self.cal))
        rebounders = []
        def chance(player):
            rebounders.append(player.player_id)
            return _rebound_transition_chance(player)
        with patch("runtime.kernel._expected_points", return_value=1), \
                patch("runtime.kernel._rebound_transition_chance", side_effect=chance):
            game = next(games(pushed, team("A"), 1, tag="rebounder-origin"))
        self.assertTrue(rebounders)
        lines = {p["player_id"]: p for rows in game["player_stats"].values() for p in rows}
        self.assertTrue(all(lines[pid]["drb"] > 0 for pid in rebounders))

    def test_malformed_style_is_rejected_before_the_game(self):
        for style in ({"pressure_turnover_sensitivity": float("nan")}, {"rebound_transition_multiplier": True},
                      {"spatial_weights": {"distance_0_3": 1.3}}, {"secret_scoring_bonus": 2}):
            with self.subTest(style=style):
                self.assertTrue(style_errors(style))
                self.assertTrue(team_errors(styled(team("H"), style), RULES))


class ScoutingReplayTests(unittest.TestCase):
    def test_legacy_replay_does_not_require_new_model_files(self):
        old = load_rating_index("2003-11-11", "2003-04", ROOT).engine_profile("Dwyane Wade")
        exists = Path.exists
        current_files = (ROOT / ROOKIE_PATH, ROOT / SCOUTING_PATH, ROOT / PROSPECTS_PATH)
        def without_current(path):
            return False if path in current_files else exists(path)
        def read_legacy(path):
            self.assertNotIn(Path(path), current_files)
            return read_json(path)
        with patch.object(Path, "exists", without_current), patch("runtime.prospects.read_json", side_effect=read_legacy):
            self.assertEqual(load_rating_index("2003-11-11", "2003-04", ROOT).engine_profile("Dwyane Wade"), old)

    def test_legacy_source_is_separate_and_missing_or_changed_archive_fails_closed(self):
        old = read_json(ROOT / LEGACY_ROOKIE_PATH)
        self.assertEqual(old["source_sha256"], sha256(ROOT / LEGACY_PROSPECTS_PATH))
        self.assertNotEqual(old["source_sha256"], sha256(ROOT / PROSPECTS_PATH))
        exists = Path.exists
        def without_archive(path):
            return False if path == ROOT / LEGACY_PROSPECTS_PATH else exists(path)
        with patch.object(Path, "exists", without_archive):
            with self.assertRaisesRegex(ValueError, "missing dated prospect"):
                load_rating_index("2003-11-11", "2003-04", ROOT)
            load_rating_index(SCOUTING_EFFECTIVE_FROM, "2003-04", ROOT)
        def changed_archive(path):
            return "0" * 64 if Path(path) == ROOT / LEGACY_PROSPECTS_PATH else sha256(path)
        with patch("runtime.player_stats.sha256", side_effect=changed_archive):
            with self.assertRaisesRegex(ValueError, "stale"):
                load_rating_index("2003-11-11", "2003-04", ROOT)
            load_rating_index(SCOUTING_EFFECTIVE_FROM, "2003-04", ROOT)

    def test_missing_dated_estimate_cannot_fall_back_to_neutral(self):
        exists = Path.exists
        for date, missing in (("2003-11-11", LEGACY_ROOKIE_PATH), (SCOUTING_EFFECTIVE_FROM, ROOKIE_PATH)):
            with self.subTest(date=date), patch.object(Path, "exists", lambda path: False if path == ROOT / missing else exists(path)):
                with self.assertRaisesRegex(ValueError, "missing dated rookie"):
                    load_rating_index(date, "2003-04", ROOT)

    def test_legacy_archive_and_adoption_gate_preserve_the_same_development_draw(self):
        old = load_rating_index("2003-11-11", "2003-04", ROOT).engine_profile("Dwyane Wade")
        new = load_rating_index(SCOUTING_EFFECTIVE_FROM, "2003-04", ROOT).engine_profile("Dwyane Wade")
        self.assertEqual(old["model_version"], LEGACY_ROOKIE_MODEL_VERSION)
        self.assertEqual(new["model_version"], ROOKIE_MODEL_VERSION)
        self.assertNotIn("style", old)
        self.assertIn("style", new)
        self.assertEqual(read_json(ROOT / LEGACY_ROOKIE_PATH), expected_rookie_estimates(ROOT, legacy=True))
        journal = Journal()
        refs = {"2003-04": journal.close_event(development_packet("wadedw01", "2003-04"))}
        old_base, new_base = old["rates"]["three_point_pct"], new["rates"]["three_point_pct"]
        old, new = develop_profile(old, refs), develop_profile(new, refs)
        self.assertEqual(old["development"], new["development"])
        self.assertGreater(new["rates"]["three_point_pct"], old["rates"]["three_point_pct"])
        self.assertAlmostEqual(old["rates"]["three_point_pct"] / old_base,
                               new["rates"]["three_point_pct"] / new_base, places=14)
        self.assertEqual(len(journal.packets), 1)

    def test_pre_upgrade_wade_packet_hashes_are_unchanged(self):
        # Captured from b36037c before this implementation, using the fixture
        # journal above. These verify input identity, not new game outcomes.
        for suffix, digest in (
            ("05_Preseason/Game_1", "e21681aa1c82070f1517ac0f9444b4ec8914ea05963c309308156a8c6f6872e6"),
            ("06_Regular_Season/11_November/Week_2/Game_2", "27eaeb1c9d849233c80df445bfb6446b935f132e1223471582696724d38cd536"),
        ):
            path = ROOT / f"career/Dwyane_Wade/2003-04/{suffix}.request.json"
            result = read_json(path.with_name(path.name.replace(".request.json", ".result.json")))
            home, away, kwargs = load_request(path, ROOT)
            packet = freeze_inputs(home, away, Journal(), kernel_version=result["kernel"], **kwargs)[2]
            self.assertEqual(hashlib.sha256(canonical(packet)).hexdigest(), digest)

    def test_future_packet_freezes_sources_styles_and_replays(self):
        request = read_json(ROOT / "career/Dwyane_Wade/2003-04/06_Regular_Season/11_November/Week_2/Game_2.request.json")
        request.update(game_date=SCOUTING_EFFECTIVE_FROM, event_id="scouting-fixture-only")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fixture.request.json"
            path.write_bytes(canonical(request))
            home, away, kwargs = load_request(path, ROOT)
        journal = Journal()
        result = run_game(home, away, journal=journal, **kwargs)
        self.assertEqual(validate_result(result), [])
        self.assertEqual(result, run_game(home, away, journal=journal, **kwargs))
        packet = journal.packets[request["event_id"]]
        wade = next(p for side in ("home", "away") for p in packet[side]["players"] if p["player_id"] == "Dwyane Wade")
        self.assertIn(str(SCOUTING_PATH), wade["stat_profile"]["scouting_sources"])
        self.assertEqual(wade["stat_profile"]["style"]["pressure_turnover_sensitivity"], 1.5)
        changed = replace(away, players=tuple(replace(p, stat_profile=dict(p.stat_profile, style={}))
                          if p.player_id == "Dwyane Wade" else p for p in away.players))
        with self.assertRaisesRegex(ValueError, "differs from"):
            build_game_packet(home, changed, **kwargs)


if __name__ == "__main__":
    unittest.main()
