"""Season awards: the researched calendar, the deterministic voter panel, team selection and Wade's honor names."""
import json
from pathlib import Path
import unittest

from runtime import season_awards as S

ROOT = Path(__file__).resolve().parents[1]


class SeasonAwardTests(unittest.TestCase):
    def test_calendar_holds_the_researched_dates_and_electorates(self):
        cal = {a["id"]: a for a in S.calendar(ROOT)["awards"]}
        self.assertEqual(cal["mvp"]["announced"], "2004-05-03")
        self.assertEqual(cal["mvp"]["ballot"], [10, 7, 5, 3, 1])
        self.assertEqual(cal["roy"]["announced"], "2004-04-20")
        self.assertEqual(cal["all_defensive"]["electorate"], 29)
        self.assertTrue(all(a["announced"] > S.C(ROOT).end for a in cal.values()))
        self.assertEqual(set(cal), set(S.LENS))

    def test_voters_spread_evenly_and_never_draw(self):
        lens = S.lenses("mvp", 4)
        self.assertEqual([round(x, 4) for x in lens], [0.2375, 0.3125, 0.3875, 0.4625])
        scored = [("A", 2.0, -1.0), ("B", 0.0, 2.0), ("C", 1.0, 0.0)]
        first = S.tally_single("mvp", scored, 123, [10, 7, 5, 3, 1])
        again = S.tally_single("mvp", scored, 123, [10, 7, 5, 3, 1])
        self.assertEqual(first, again)
        self.assertEqual(sum(v["points"] for v in first), 123 * (10 + 7 + 5))

    def test_a_points_tie_breaks_on_first_place_votes_else_co_winners(self):
        tally = S.tally_single("roy", [("A", 1.0, 1.0), ("B", 1.0, 1.0), ("C", 0.0, 0.0)], 10, [5, 3, 1])
        self.assertEqual([v["points"] for v in tally], [40, 40, 10])       # identical evidence shares places 1 and 2
        self.assertEqual(S.winners(tally), ["A", "B"])
        votes = [{"player": "A", "points": 9, "first_place": 2}, {"player": "B", "points": 9, "first_place": 1}]
        self.assertEqual(S.winners(votes), ["A"])

    def test_teams_respect_positions_and_coaches_skip_their_own_players(self):
        pos = {"G1": "G", "G2": "G", "G3": "G", "F1": "F", "F2": "F", "C1": "C", "C2": "C"}
        team = {n: ("Club X" if n == "G1" else "Club Y") for n in pos}
        scored = [(n, 3.0 - i * 0.4, 0.0) for i, n in enumerate(pos)]
        groups = {"position": pos, "team": team}
        ranked, totals, firsts = S.tally_teams("all_defensive", scored, 2, [2, 1], {"G": 2, "F": 2, "C": 1}, groups,
                                               exclude=lambda i: "Club X" if i == 0 else None)
        self.assertEqual(totals["G1"], 2)                    # one voter is Club X's coach
        teams = S.select_teams(ranked, totals, firsts, 2, {"G": 2, "F": 2, "C": 1}, pos)
        self.assertEqual(sorted(pos[n] for n in teams[0]), ["C", "F", "F", "G", "G"])

    def test_a_tie_at_the_last_spot_names_both(self):
        totals = {"A": 10, "B": 8, "C": 8, "D": 1}
        firsts = {"A": 2, "B": 0, "C": 0, "D": 0}
        teams = S.select_teams(["A", "B", "C", "D"], totals, firsts, 2, 2, {})
        self.assertEqual(teams[0], ["A", "B", "C"])
        self.assertEqual(teams[1], ["D"])

    def test_eligibility_rules(self):
        base = {"games": 60, "mpg": 30.0, "rookie": False, "starts": 10, "prior_games": 40, "prior_game_score": 8.0}
        self.assertTrue(S.eligible("mvp", base))
        self.assertTrue(S.eligible("smoy", base))
        self.assertFalse(S.eligible("smoy", dict(base, starts=31)))
        self.assertFalse(S.eligible("roy", base))
        self.assertTrue(S.eligible("roy", dict(base, rookie=True, games=41)))
        self.assertFalse(S.eligible("mip", dict(base, prior_games=10)))
        self.assertFalse(S.eligible("dpoy", dict(base, mpg=20.0)))

    def test_honor_names_match_what_standing_reads(self):
        from runtime.standing import HONOR_NAMES
        decision = {"id": "x", "award": "all_nba", "name": "All-NBA Teams",
                    "teams": [{"team": t, "players": [{"player": "P"}]} for t in ("First Team", "Second Team", "Third Team")]}
        for _, name, _ in S.honors(decision):
            self.assertIn(name, HONOR_NAMES)
        self.assertEqual(S.short_name("All-Rookie First Team"), "All-Rookie 1st")
        self.assertEqual(S.short_name("Rookie of the Year"), "ROY")

    def test_every_club_coach_votes_on_coaches_ballots(self):
        confs = json.loads((ROOT / S.C(ROOT).conferences).read_text(encoding="utf-8"))["conferences"]
        self.assertEqual(sum(len(c) for c in confs.values()), 29)
        self.assertEqual(S.coaches(ROOT)["Miami Heat"], "Erik Spoelstra")


if __name__ == "__main__":
    unittest.main()
