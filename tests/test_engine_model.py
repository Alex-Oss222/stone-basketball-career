"""Engine model: defense (E1), rotations and availability (E3, item 8), late game (E4), foul trouble (E5)."""
import hashlib
import json
import statistics
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from runtime.era import environment_for, rules_for
from runtime.game_requests import load_request
from runtime.kernel import (MINUTES_CAP, SHORT_HANDED_RAISE, PlayerInput, TeamInput, _allocate, _choose_lineup,
                            _Club, _expected_points, calibrate, resolve_game, team_errors, validate_result)
from runtime.player_stats import CUTOFF, MODEL_VERSION, RATE_KEYS
from runtime.rotations import load_rosters, miami_holds, primary_position, real_rotation, season_fraction
from runtime.schedule import schedule_path

ROOT = Path(__file__).resolve().parents[1]
GAME_DATE = "2003-10-28"
ENV = environment_for("2003-04", GAME_DATE)
RULES = rules_for("2003-04")


def team(side, defense=None, minutes=(34, 34, 34, 34, 34, 18, 16, 12, 12, 8, 4, 0), availability=None):
    """Artificial equal-rate club (not a real team or a production profile)."""
    rates = {k: ENV["player_rate_baselines"][k] for k in RATE_KEYS}
    positions = ["PG", "SG", "SF", "PF", "C", "PG", "SG", "SF", "PF", "C", "SF", "C"] * 2
    players = []
    for i, m in enumerate(minutes):
        profile = {"bbr_id": f"fixture{side.lower()}{chr(97 + i)}01", "model_version": MODEL_VERSION, "as_of": CUTOFF,
                   "season_end_year": 2003, "source_sha256": "0" * 64, "rates": dict(rates)}
        if defense is not None:
            profile["defense"] = defense
        players.append(PlayerInput(f"{side}_{i}", positions[i], m, stat_profile=profile,
                                   availability=1.0 if availability is None else availability[i]))
    return TeamInput(side, tuple(players))


def games(home, away, n, venue="neutral", tag="m"):
    for i in range(n):
        result = resolve_game(home, away, entropy=hashlib.sha256(f"{tag}{i}".encode()).digest(), event_id=f"{tag}{i}",
                              rules=RULES, environment=ENV, venue=venue)
        assert validate_result(result) == [], validate_result(result)
        yield result


class ExpectedMarginTests(unittest.TestCase):
    def test_equal_clubs_have_no_edge_and_defense_creates_one(self):
        import random
        cal = calibrate(ENV)
        make = lambda t: _Club(t, "home", random.Random(0), RULES)
        a, b = make(team("A")), make(team("B"))
        self.assertAlmostEqual(_expected_points(a, b, cal), _expected_points(b, a, cal))
        good = make(team("G", defense=2.0))
        self.assertLess(_expected_points(a, good, cal), _expected_points(a, b, cal) - 0.05)


class DefenseTests(unittest.TestCase):
    def test_calibration_is_points_per_100(self):
        cal = calibrate(ENV)
        self.assertGreater(cal["make_per_defense"], 0.002)
        self.assertLess(cal["make_per_defense"], 0.008)
        self.assertGreater(cal["tov_per_defense"], 0.001)

    def test_five_good_defenders_allow_fewer_points_and_force_turnovers(self):
        base, good = team("A"), team("A", defense=2.0)   # +10 on the floor
        allowed = {}
        for label, defense in (("base", base), ("good", good)):
            pts = tov = poss = 0
            for g in games(team("H"), defense, 150, tag="def"):
                pts += g["final_score"]["home"]
                tov += g["team_stats"]["home"]["tov"]
                poss += g["team_stats"]["home"]["possessions"]
            allowed[label] = (100 * pts / poss, tov / 150)
        self.assertLess(allowed["good"][0], allowed["base"][0] - 6)       # about -10 per 100
        self.assertGreater(allowed["good"][1], allowed["base"][1] + 0.5)

    def test_defensive_value_is_bounded(self):
        bad = team("A", defense=40.0)
        self.assertTrue(any("defensive value" in e for e in team_errors(bad, RULES)))


class RotationTests(unittest.TestCase):
    def test_full_roster_fills_in_rotation_order(self):
        players = [PlayerInput(f"p{i}", "SF", m) for i, m in enumerate((38, 36, 34, 32, 30, 24, 20, 16, 12, 8))]
        targets = _allocate(players, 240)
        self.assertAlmostEqual(sum(targets.values()), 240)
        self.assertEqual(targets["p0"], 38)
        self.assertEqual(targets["p9"], 0)          # deep bench sits when everyone is available

    def test_short_handed_raise_is_capped(self):
        players = [PlayerInput(f"p{i}", "SF", m) for i, m in enumerate((39, 32, 30, 28, 26, 22, 18, 14))]
        targets = _allocate(players, 240)
        self.assertAlmostEqual(sum(targets.values()), 240)
        self.assertLessEqual(targets["p0"], MINUTES_CAP + 1e-9)
        self.assertLessEqual(targets["p7"], 14 + SHORT_HANDED_RAISE + 1e-9)
        self.assertGreater(targets["p7"], 14)

    def test_seven_players_still_cover_the_game(self):
        players = [PlayerInput(f"p{i}", "SF", m) for i, m in enumerate((39, 30, 28, 26, 24, 20, 16))]
        targets = _allocate(players, 240)
        self.assertAlmostEqual(sum(targets.values()), 240)      # the caps give way only when they must
        self.assertTrue(all(t <= 48 for t in targets.values()))

    def test_availability_is_drawn_and_inactives_listed(self):
        # Rotation order (most minutes first); the 0.5 players are spread through it.
        minutes = (36, 35, 34, 33, 32, 30, 28, 25, 22, 20, 18, 15, 12, 10, 8, 6, 5, 4)
        availability = [1.0, 1.0, 1.0, 1.0, 1.0, 0.5, 0.5, 1.0, 1.0, 0.5, 1.0, 1.0, 1.0, 0.5, 1.0, 0.5, 0.5, 1.0]
        roster = team("H", minutes=minutes, availability=availability)
        self.assertEqual(team_errors(roster, RULES), [])
        dressed = []
        for g in games(roster, team("A"), 80, tag="avail"):
            rows = g["player_stats"]["home"]
            self.assertLessEqual(len(rows), RULES["game_day_actives"])
            self.assertEqual(len(rows) + len(g["inactive"]["home"]), 18)
            dressed.append(any(r["player_id"] == "H_5" for r in rows))
        self.assertGreater(sum(dressed), 25)       # a 50% player dresses in about half the games
        self.assertLess(sum(dressed), 55)

    def test_game_day_list_and_season_roster_limits(self):
        explicit = team("H", minutes=(20,) * 12 + (0,))
        self.assertTrue(any("exceeds" in e for e in team_errors(explicit, RULES)))
        thin = team("H", minutes=(15,) * 13, availability=[0.9] * 13)
        self.assertTrue(any("fewer than" in e for e in team_errors(thin, RULES)))
        invalid = team("H", availability=[1.2] + [1.0] * 11)
        self.assertTrue(any("availability" in e for e in team_errors(invalid, RULES)))

    def test_real_rotation_uses_minutes_per_game_and_games_played(self):
        rosters = load_rosters("2003-04")
        cle = real_rotation("Cleveland Cavaliers", rosters["Cleveland Cavaliers"], 82, fraction=0.5)
        lebron = next(p for p in cle.players if p.player_id == "LeBron James")
        self.assertAlmostEqual(lebron.minutes, 3122 / 79, places=1)
        self.assertAlmostEqual(lebron.availability, 79 / 82, places=3)
        per_game = [p.minutes for p in cle.players]
        self.assertEqual(per_game, sorted(per_game, reverse=True))
        self.assertEqual(primary_position("SG-SF"), "SG")

    def test_traded_players_are_with_one_club_on_every_scheduled_date(self):
        rosters = load_rosters("2003-04")
        games = json.loads(schedule_path("2003-04").read_text())["games"]
        held = miami_holds("2003-04")
        for g in games:
            if "Miami Heat" in (g["home"], g["away"]):
                continue
            fraction = season_fraction("2003-04", g["date"])
            ids = [{p.stat_profile.get("bbr_id") or p.player_id for p in real_rotation(
                       name, rosters[name], 82, fraction=fraction, exclude=held).players}
                   for name in (g["home"], g["away"])]
            self.assertFalse(ids[0] & ids[1], g)
        def wallace(club, day):
            players = real_rotation(club, rosters[club], 82, fraction=season_fraction("2003-04", day)).players
            return any(p.player_id == "Rasheed Wallace" for p in players)
        self.assertTrue(wallace("Portland Trail Blazers", "2003-11-05"))
        self.assertFalse(wallace("Detroit Pistons", "2003-11-05"))
        self.assertTrue(wallace("Detroit Pistons", "2004-04-01"))

    def test_miami_register_players_leave_their_real_club(self):
        held = miami_holds("2003-04")
        self.assertIn("cartean01", held)                       # player option pending on June 26
        rosters = load_rosters("2003-04")
        spurs = real_rotation("San Antonio Spurs", rosters["San Antonio Spurs"], 82, fraction=0.05, exclude=held)
        self.assertNotIn("Anthony Carter", {p.player_id for p in spurs.players})
        nets = real_rotation("New Jersey Nets", rosters["New Jersey Nets"], 82, fraction=0.05, exclude=held)
        self.assertNotIn("Alonzo Mourning", {p.player_id for p in nets.players})   # matched by name

    def test_conflict_rule_three_spreads_departed_minutes(self):
        row = lambda pid, minutes: {"player_id": pid, "bbr_id": f"{pid.lower() * 5}01", "position": "PG",
                                    "games": 82, "games_started": 82, "minutes": minutes}
        club = {"players": [row("A", 2952), row("B", 2460), row("C", 1640)]}
        moved = real_rotation("X", club, 82, fraction=0.5, exclude={"aaaaa01"}, arrivals=[row("D", 1640)])
        minutes = {p.player_id: p.minutes for p in moved.players}
        self.assertEqual(minutes["D"], 20.0)                   # the arrival brings his own share
        # The other 16 minutes of A's 36 are spread over B and C in proportion to their minutes.
        self.assertAlmostEqual(minutes["B"] + minutes["C"], 30 + 20 + 16, places=1)
        self.assertAlmostEqual(minutes["B"] / minutes["C"], 30 / 20, places=3)
        # An arrival who needs more than the departing minutes still plays his share; the
        # difference comes out of the staying rotation in proportion to real minutes.
        small = {"players": [row("A", 492), row("B", 2460), row("C", 1640)]}
        moved = real_rotation("X", small, 82, fraction=0.5, exclude={"aaaaa01"}, arrivals=[row("D", 2460)])
        minutes = {p.player_id: p.minutes for p in moved.players}
        self.assertEqual(minutes["D"], 30.0)
        self.assertAlmostEqual(minutes["B"] + minutes["C"], 50 - 24, places=1)
        self.assertAlmostEqual(minutes["B"] / minutes["C"], 30 / 20, places=3)

    def test_real_miami_signings_return_to_their_previous_club(self):
        rosters = load_rosters("2003-04")
        returned = {p["player_id"]: club for club, entry in rosters.items() for p in entry["players"] if "returned" in p}
        self.assertEqual(returned.get("Lamar Odom"), "Los Angeles Clippers")
        self.assertEqual(returned.get("Rafer Alston"), "Toronto Raptors")
        self.assertNotIn("Udonis Haslem", returned)                  # no previous NBA club
        raptors = real_rotation("Toronto Raptors", rosters["Toronto Raptors"], 82, fraction=0.5)
        alston = next(p for p in raptors.players if p.player_id == "Rafer Alston")
        self.assertAlmostEqual(alston.minutes, 980 / 47, places=1)    # his 2002-03 share
        signed = real_rotation("Toronto Raptors", rosters["Toronto Raptors"], 82, fraction=0.5, exclude={"alstora01"})
        self.assertNotIn("Rafer Alston", {p.player_id for p in signed.players})   # if simulated Miami signs him

    def test_hardship_does_not_override_availability(self):
        import random
        players = [PlayerInput("star", "PF", 42, availability=1 / 82)] + [
            PlayerInput(f"p{i}", "SG", 30 - i, availability=0.55) for i in range(12)]
        rng, dressed = random.Random(3), 0
        for _ in range(3000):
            dressed += "star" in _Club(TeamInput("X", tuple(players)), "home", rng, RULES).order
        self.assertLess(dressed / 3000, 0.05)

    def test_lineup_keeps_a_guard_and_a_big(self):
        positions = ["SF", "SF", "SF", "SF", "PG", "C", "SG", "PF", "C", "SG"]
        players = tuple(PlayerInput(f"p{i}", pos, m) for i, (pos, m) in enumerate(zip(positions, (38, 36, 34, 32, 30, 20, 18, 14, 10, 8))))
        import random
        club = _Club(TeamInput("X", players), "home", random.Random(1), RULES)
        for mode in ("normal", "closing"):
            lineup = _choose_lineup(club, 0, 2880, mode)
            kinds = {club.players[pid].position for pid in lineup}
            self.assertTrue(kinds & {"PG", "SG"} and kinds & {"PF", "C"}, (mode, lineup))


class RealRotationRequestTests(unittest.TestCase):
    def load(self, home, away):
        data = {"event_id": "r", "game_date": "2003-11-05", "game_type": "regular", "venue": "home",
                "home": home, "away": away}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "Game_1.request.json"
            path.write_text(json.dumps(data))
            return load_request(path, ROOT)

    def test_real_rotation_request(self):
        home, away, _ = self.load({"team": "Cleveland Cavaliers", "rotation": "real"},
                                  {"team": "Detroit Pistons", "rotation": "real"})
        self.assertGreater(len(home.players), RULES["game_day_actives"])
        self.assertTrue(all(p.stat_profile for p in home.players))
        self.assertTrue(any(p.availability < 1 for p in away.players))

    def test_miami_and_unknown_rotations_are_refused(self):
        for spec in ({"team": "Miami Heat", "rotation": "real"}, {"team": "Detroit Pistons", "rotation": "fantasy"},
                     {"team": "Detroit Pistons", "rotation": "real", "players": []}):
            with self.assertRaises(ValueError):
                self.load(spec, {"team": "Cleveland Cavaliers", "rotation": "real"})


class LateGameAndFoulTroubleTests(unittest.TestCase):
    """Statistical checks on equal clubs; the 6,000-game check with real rosters is scripts/engine_diagnostics.py."""

    @classmethod
    def setUpClass(cls):
        cls.results = list(games(team("H"), team("A"), 400, venue="home", tag="late"))

    def test_close_games_reach_overtime_and_margins_stay_realistic(self):
        overtime = sum(g["overtimes"] > 0 for g in self.results) / len(self.results)
        margins = [g["final_score"]["home"] - g["final_score"]["away"] for g in self.results]
        self.assertGreater(overtime, 0.03)
        self.assertLess(overtime, 0.12)
        self.assertLess(statistics.pstdev(margins), 14.5)
        self.assertGreater(statistics.mean(margins), 0.5)       # home edge survives the score effect

    def test_foul_trouble_keeps_disqualifications_rare(self):
        foul_outs = sum(r["fouled_out"] for g in self.results for side in ("home", "away")
                        for r in g["player_stats"][side]) / len(self.results)
        self.assertLess(foul_outs, 0.4)

    def test_starters_stay_near_their_targets(self):
        starters = [(r["minutes"], g["overtimes"]) for g in self.results for r in g["player_stats"]["home"]
                    if r["player_id"] == "H_0"]
        self.assertAlmostEqual(statistics.mean(m for m, _ in starters), 34, delta=2.5)
        self.assertLessEqual(max(m for m, ot in starters if not ot), 46)


if __name__ == "__main__":
    unittest.main()
