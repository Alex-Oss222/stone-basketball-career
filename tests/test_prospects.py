import copy
import hashlib
import json
import re
import tempfile
import unittest
from pathlib import Path

from runtime.game_requests import load_request
from runtime.game_runner import run_game
from runtime.player_stats import RATE_KEYS, load_rating_index, read_json
from runtime.prospects import (PROSPECTS_PATH, ROOKIE_MODEL_VERSION, VETERAN_PATH, build_rookie_estimates,
                               COUNT_KEYS, LEGACY_PROSPECTS_PATH, LEGACY_ROOKIE_MODEL_VERSION, rookie_errors)

ROOT = Path(__file__).resolve().parents[1]


class Journal:
    def close_event(self, packet):
        return hashlib.sha256(json.dumps(packet, sort_keys=True).encode()).hexdigest()


class RookieEstimateTests(unittest.TestCase):
    def setUp(self):
        self.prospects = read_json(ROOT / PROSPECTS_PATH)
        self.veterans = read_json(ROOT / VETERAN_PATH)
        self.profile = (ROOT / "career/Dwyane_Wade/Dwyane_Wade_Player_Profile.md").read_text(encoding="utf-8")
        self.college = self.profile.split("### University of Connecticut\n", 1)[1].split("## 14.", 1)[0]

    def test_generated_file_is_current(self):
        self.assertEqual(rookie_errors(ROOT), [])

    def test_wade_record_matches_profile_totals(self):
        """The prospect record must follow the career profile whenever the profile is revised."""
        profile = self.profile
        line = re.search(r"College totals: ([\d,]+) points, ([\d,]+) rebounds, ([\d,]+) assists, ([\d,]+) steals, "
                         r"([\d,]+) blocks and ([\d,]+) turnovers.*?plays ([\d,]+) minutes", profile)
        stated = dict(zip(("points", "rebounds", "assists", "steals", "blocks", "turnovers", "minutes"),
                          (int(x.replace(",", "")) for x in line.groups())))
        seasons = self.prospects["records"][0]["seasons"]
        self.assertEqual({k: sum(s[k] for s in seasons) for k in stated}, stated)
        for season in seasons:
            row = re.search(rf"\| {season['season']} \| (\d+)/(\d+) \| [\d.]+ \| (\d+)/(\d+) \| [\d.]+ \| (\d+)/(\d+) \| [\d.]+ \| (\d+) \|", profile)
            self.assertEqual([int(x) for x in row.groups()],
                             [season[k] for k in ("field_goals_made", "field_goals_attempted", "three_pointers_made",
                                                  "three_pointers_attempted", "free_throws_made",
                                                  "free_throws_attempted", "points")])

    def test_college_targets_and_all_displayed_rows_reconcile_from_integers(self):
        seasons = self.prospects["records"][0]["seasons"]
        total = {key: sum(season[key] for season in seasons) for key in COUNT_KEYS}
        self.assertEqual(total["games"], 98)
        self.assertEqual(total["points"], 2078)
        self.assertEqual(f"{total['points'] / total['games']:.1f}", "21.2")
        shots = (("field_goals", "54.7"), ("three_pointers", "44.2"), ("free_throws", "93.3"))
        for stem, target in shots:
            self.assertEqual(f"{100 * total[stem + '_made'] / total[stem + '_attempted']:.1f}", target)
        for row in [*seasons, dict(total, season="Career")]:
            with self.subTest(season=row["season"]):
                self.assertTrue(all(type(row[key]) is int and row[key] >= 0 for key in COUNT_KEYS))
                self.assertEqual(row["points"], 2 * row["field_goals_made"]
                                 + row["three_pointers_made"] + row["free_throws_made"])
                cells = []
                for stem, _ in shots:
                    made, attempted = row[stem + "_made"], row[stem + "_attempted"]
                    self.assertLessEqual(made, attempted)
                    cells.extend((f"{made}/{attempted}", f"{100 * made / attempted:.1f}"))
                two_m = row["field_goals_made"] - row["three_pointers_made"]
                two_a = row["field_goals_attempted"] - row["three_pointers_attempted"]
                self.assertGreaterEqual(two_m, 0)
                self.assertLessEqual(two_m, two_a)
                self.assertIn("| " + " | ".join([row["season"], *cells, str(row["points"])]) + " |", self.college)
                per_game = re.search(rf"\| {row['season']} \| \d+-\d+ \| (\d+) \| ([\d.]+) \| ([\d.]+) \|", self.college)
                self.assertIsNotNone(per_game)
                self.assertEqual(per_game.groups(), (str(row["games"]), f"{row['minutes'] / row['games']:.1f}",
                                                     f"{row['points'] / row['games']:.1f}"))

    def test_college_revision_preserves_non_scoring_totals_and_tournament_subset(self):
        seasons = self.prospects["records"][0]["seasons"]
        old = read_json(ROOT / LEGACY_PROSPECTS_PATH)["records"][0]["seasons"]
        revised = {"points", "field_goals_made", "field_goals_attempted", "three_pointers_made",
                   "three_pointers_attempted", "free_throws_made", "free_throws_attempted"}
        for before, after in zip(old, seasons):
            self.assertEqual({k: v for k, v in before.items() if k not in revised},
                             {k: v for k, v in after.items() if k not in revised})
        # The recorded NCAA games remain a feasible subset of the junior season.
        tournament = dict(zip(("field_goals_made", "field_goals_attempted", "three_pointers_made",
                               "three_pointers_attempted", "free_throws_made", "free_throws_attempted"),
                              (34, 71, 9, 26, 27, 31)))
        self.assertIn("34-for-71 from the field, 9-for-26 from three and 27-for-31 at the line", self.college)
        remaining = {key: seasons[-1][key] - count for key, count in tournament.items()}
        for stem in ("field_goals", "three_pointers", "free_throws"):
            self.assertGreaterEqual(remaining[stem + "_made"], 0)
            self.assertLessEqual(remaining[stem + "_made"], remaining[stem + "_attempted"])
        self.assertEqual(2 * remaining["field_goals_made"] + remaining["three_pointers_made"]
                         + remaining["free_throws_made"], seasons[-1]["points"] - 4 * 26)

    def test_junior_efficiency_narrative_uses_the_revised_shot_totals(self):
        junior = self.prospects["records"][0]["seasons"][-1]
        fg, fga, three, three_a, fta = (junior[key] for key in (
            "field_goals_made", "field_goals_attempted", "three_pointers_made", "three_pointers_attempted",
            "free_throws_attempted"))
        self.assertIn(f"His {fg} field goals include {fg - three} two-pointers on {fga - three_a} attempts, "
                      f"or {100 * (fg - three) / (fga - three_a):.1f} percent", self.college)
        self.assertIn(f"He takes {three_a / junior['games']:.1f} threes and {fta / junior['games']:.1f} free throws per game", self.college)
        self.assertIn(f"Three-point attempts account for {100 * three_a / fga:.1f} percent", self.college)
        self.assertIn(f"free-throw attempt rate is {fta / fga:.3f}", self.college)
        self.assertIn(f"effective field-goal percentage is {100 * (fg + .5 * three) / fga:.1f} "
                      f"and estimated true shooting is {100 * junior['points'] / (2 * (fga + .44 * fta)):.1f}", self.college)

    def test_estimates_sit_between_translation_and_baseline(self):
        wade = build_rookie_estimates(self.prospects, "x", self.veterans)["players"]["wadedw01"]
        base = self.veterans["rate_baselines"]
        for key in RATE_KEYS:
            t, e = wade["translated"][key], wade["estimated"][key]
            if t is None:
                self.assertEqual(e, base[key])
            else:
                self.assertLessEqual(min(t, base[key]) - 1e-12, e)
                self.assertLessEqual(e, max(t, base[key]) + 1e-12)

    def test_unknown_level_and_existing_nba_record_are_refused(self):
        bad = copy.deepcopy(self.prospects)
        bad["records"][0]["level"] = "high_school"
        with self.assertRaises(ValueError):
            build_rookie_estimates(bad, "x", self.veterans)
        bad = copy.deepcopy(self.prospects)
        bad["records"][0]["bbr_id"] = next(iter(self.veterans["players"]))
        with self.assertRaises(ValueError):
            build_rookie_estimates(bad, "x", self.veterans)

    def test_index_returns_rookie_profile(self):
        profile = load_rating_index("2003-10-28", "2003-04", ROOT).engine_profile("Dwyane Wade")
        self.assertEqual(profile["model_version"], LEGACY_ROOKIE_MODEL_VERSION)
        self.assertEqual(set(profile["rates"]), set(RATE_KEYS))

    def test_wade_plays_on_his_estimate(self):
        miami = [("Travis Best", "PG", 30), ("Dwyane Wade", "SG", 34), ("Caron Butler", "SF", 34),
                 ("Malik Allen", "PF", 30), ("Brian Grant", "C", 32), ("Rasual Butler", "SG", 20),
                 ("Eddie House", "PG", 18), ("Sean Lampley", "SF", 12), ("LaPhonso Ellis", "PF", 14),
                 ("Vladimir Stepania", "C", 16)]
        request = {"event_id": "test-wade", "game_date": "2003-10-28", "game_type": "regular", "venue": "home",
                   "home": {"team": "Miami Heat", "players": [{"player_id": n, "position": p, "minutes": m}
                                                              for n, p, m in miami]},
                   "away": {"team": "Philadelphia 76ers", "baseline": "library/2003/league/nba_2003_end_of_season.json"}}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "Game_1.request.json"
            path.write_text(json.dumps(request))
            home, away, kwargs = load_request(path, ROOT)
        wade = next(p for p in home.players if p.player_id == "Dwyane Wade")
        self.assertEqual(wade.stat_profile["model_version"], LEGACY_ROOKIE_MODEL_VERSION)
        result = run_game(home, away, journal=Journal(), **kwargs)
        self.assertTrue(result["terminated"])


if __name__ == "__main__":
    unittest.main()
