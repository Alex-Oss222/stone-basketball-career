import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from runtime.game_requests import load_request
from runtime.game_runner import run_game
from runtime.player_stats import RATE_KEYS, read_json
from runtime.protagonist import age_step, next_season_rates, season_age
from runtime.trajectories import development_seasons

ROOT = Path(__file__).resolve().parents[1]
VET = read_json(ROOT / "library/2003/league/nba_2003_veteran_ratings.json")
WADE = read_json(ROOT / "library/2003/league/nba_2003_rookie_estimates.json")["players"]["wadedw01"]["estimated"]


class Journal:
    def __init__(self):
        self.closed = {}

    def close_event(self, packet):
        ref = hashlib.sha256(json.dumps(packet, sort_keys=True).encode()).hexdigest()
        self.closed[packet["event_id"]] = ref
        return ref


def wade_game(event_id, journal):
    miami = [("Travis Best", "PG", 30), ("Dwyane Wade", "SG", 34), ("Caron Butler", "SF", 34),
             ("Malik Allen", "PF", 30), ("Brian Grant", "C", 32), ("Rasual Butler", "SG", 20),
             ("Eddie House", "PG", 18), ("Sean Lampley", "SF", 12), ("LaPhonso Ellis", "PF", 14),
             ("Vladimir Stepania", "C", 16)]
    request = {"event_id": event_id, "game_date": "2003-11-05", "game_type": "regular", "venue": "home",
               "home": {"team": "Miami Heat", "players": [{"player_id": n, "position": p, "minutes": m}
                                                          for n, p, m in miami]},
               "away": {"team": "Orlando Magic", "baseline": "library/2003/league/nba_2003_end_of_season.json"}}
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "Game_1.request.json"
        path.write_text(json.dumps(request))
        home, away, kwargs = load_request(path, ROOT)
    return run_game(home, away, journal=journal, **kwargs)


class WadeDevelopmentTests(unittest.TestCase):
    def test_rookie_season_gets_one_journaled_swing(self):
        journal = Journal()
        result = wade_game("t-swing", journal)
        wade = [k for k in journal.closed if k.startswith("development:") and k.endswith(":wadedw01")]
        self.assertEqual(wade, ["development:2003-04:wadedw01"])
        self.assertEqual(development_seasons("wadedw01", "2006-07"), ["2006-07"])
        self.assertTrue(result["terminated"])

    def test_age_on_february_first(self):
        self.assertEqual(season_age("2003-04"), 20)
        self.assertEqual(season_age("2004-05"), 21)
        self.assertEqual(age_step(21), (1.05, 1.015))
        self.assertEqual(age_step(35), (0.94, 0.99))

    def test_next_season_moves_toward_simulated_play_and_ages(self):
        journal = Journal()
        lines = [next(r for r in wade_game(f"t-season-{i}", journal)["player_stats"]["home"]
                      if r["player_id"] == "Dwyane Wade") for i in range(40)]
        nxt = next_season_rates(WADE, lines, "2004-05", VET["rate_baselines"], VET["source_totals"])
        self.assertEqual(set(nxt), set(RATE_KEYS))
        self.assertGreater(nxt["usage_pct"], 0)
        # No simulated evidence: only the age step applies.
        aged = next_season_rates(WADE, [], "2004-05", VET["rate_baselines"], VET["source_totals"])
        self.assertAlmostEqual(aged["assist_pct"], WADE["assist_pct"] * 1.05)
        self.assertAlmostEqual(aged["free_throw_pct"], min(WADE["free_throw_pct"] * 1.015, 0.99))
        self.assertAlmostEqual(aged["turnovers_per_fga"], WADE["turnovers_per_fga"] / 1.05)


if __name__ == "__main__":
    unittest.main()
