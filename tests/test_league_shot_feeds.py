"""League charts consume closed engine events without borrowing another player's shots."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from runtime.league_cards import (CARDS_DIR, LEAGUE_DIR, PLAYER_DIR, TEMPLATE, card_data,
                                  closed_card_feeds, html_card, html_payload, markdown_card,
                                  period_statistics)
from runtime.shot_events import engine_result_shots
from runtime.spatial_shots import classify_spatial_zone

ROOT = Path(__file__).resolve().parents[1]
PERIOD = dict(id="season", kind="season", label="2003-04 regular season",
              start="2003-10-01", end="2004-04-30", folder="2003-04")


def result_fixture(event_id="tracked", day="2003-11-02", *, tracked=True, zero_attempts=False,
                   home="Home Club", guard="Tracked Guard"):
    """Small complete shooting feed with equal box counts but distinct shooter locations."""
    boxes, shots = {}, []
    for side, players in (("home", [(guard, 0), ("Other Guard", 15)]),
                          ("away", [("Opponent", -15)])):
        boxes[side] = []
        for name, x in players:
            fga = 0 if zero_attempts and name == guard else 2
            fgm = int(bool(fga))
            boxes[side].append(dict(player_id=name, fgm=fgm, fga=fga, tpm=0, tpa=0,
                                    ftm=0, fta=0, pts=2 * fgm, orb=0, drb=1, ast=1,
                                    stl=0, blk=0, tov=0, pf=0, seconds=1200.0, started=True))
            for made in ([True, False] if fga else []):
                index = len(shots) + 1
                shots.append(dict(shot_id=f"{event_id}:shot:{index:06d}", player_id=name,
                                  side=side, period=1, clock_seconds=720 - index * 10,
                                  x=x, y=1, zone=classify_spatial_zone(x, 1), value=2,
                                  made=made, transition=False))
    teams = {side: {key: sum(r[key] for r in rows) for key in ("fgm", "fga", "tpm", "tpa")}
             for side, rows in boxes.items()}
    scores = {side: sum(r["pts"] for r in rows) for side, rows in boxes.items()}
    result = dict(event_id=event_id, game_date=day, game_type="regular", season="2003-04",
                  kernel="2003.7" if tracked else "2003.6", terminated=True, periods=4,
                  period_scores={side: [score, 0, 0, 0] for side, score in scores.items()},
                  home=home, away="Away Club", final_score=scores, player_stats=boxes, team_stats=teams)
    if tracked:
        result.update(shots=shots, shot_tracking=dict(schema_version=1, model_version="spatial-2003.1",
                      coordinate_system="nba_feet_from_basket", source_type="engine_generated",
                      prior_sha256="a" * 64, coverage="complete"))
    return result


def fixture_context(root):
    players = [dict(registry_id=pid, bbr_id=pid, name=name, position="SG", birth_date="1980-01-01",
                    team_name="Home Club", team_code="HOM", cohort="end_2002_03_roster")
               for pid, name in (("tracked01", "Tracked Guard"), ("other01", "Other Guard"),
                                 ("opponent01", "Opponent"))]
    return SimpleNamespace(root=root, on="2003-11-04", season="2003-04", seasons=["2003-04"], history={}, honors={}, registry=dict(players=players), periods=[PERIOD],
                           colors=dict(placeholder=dict(primary="#111111", secondary="#eeeeee"), eras=[]),
                           photos={}, baseline={}, prior={}, rights={}, signed={}, contracts={}, legend={}, miami_cards={},
                           template=(ROOT / TEMPLATE).read_text(),
                           club=lambda player, signed=None: dict(club=player["team_name"], code="HOM", rights=False,
                                                    basis="fixture club record"))


class LeagueShotFeedTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.ctx = fixture_context(self.root)
        self.folder = self.root / LEAGUE_DIR / "2003-04/Games"
        self.folder.mkdir(parents=True)
        lookup_patch = patch("runtime.write_back.bbr_lookup", return_value={})
        self.lookup = lookup_patch.start()
        self.addCleanup(lookup_patch.stop)

    def save(self, result):
        path = self.folder / f'{result["event_id"]}.result.json'
        path.write_text(json.dumps(result))
        return path

    def miami_note(self, result, *, status="scheduled", request=None):
        folder = self.root / PLAYER_DIR / "2003-04" / "06_Regular_Season/11_November/Week_1"
        folder.mkdir(parents=True)
        (folder / "Game_1.result.json").write_text(json.dumps(result))
        (folder / "Game_1.md").write_text(
            f'---\ntype: game\nstatus: {status}\ndate: {result["game_date"]}\n'
            'result_file: Game_1.result.json\n---\n')
        if request is not None:
            (folder / "Game_1.request.json").write_text(json.dumps(request))

    def test_only_closed_dated_results_are_validated_once_and_shots_keep_exact_owner(self):
        self.save(result_fixture("old", "2003-11-01", tracked=False))
        source = self.save(result_fixture())
        future = result_fixture("future", "2003-11-05")
        future["shots"][0]["player_id"] = "Invalid future shooter"
        self.save(future)
        unfinished = result_fixture("unfinished", "2003-11-03")
        unfinished["terminated"] = False
        self.save(unfinished)
        unclosed = result_fixture("unclosed", "2003-11-03", home="Miami Heat")
        unclosed["shots"][0]["player_id"] = "Invalid unclosed shooter"
        self.miami_note(unclosed)
        with patch("runtime.league_cards.engine_result_shots", wraps=engine_result_shots) as adapter:
            records, shots = closed_card_feeds(self.ctx)
        self.assertEqual(adapter.call_count, 2)  # Once per result, not once per registry player.
        self.assertEqual([r["event_id"] for r in records["tracked01"]], ["old", "tracked"])
        self.assertEqual(len(shots["tracked01"]), 2)
        self.assertTrue(all(s["player_id"] == "Tracked Guard" and s["side"] == "home"
                            and s["x"] == 0 for s in shots["tracked01"]))
        self.assertTrue(all(s["x"] == 15 for s in shots["other01"]))
        self.assertTrue(all(s["source_type"] == "engine_generated" and len(s["source_digest"]) == 64
                            for s in shots["tracked01"]))
        self.assertEqual((self.root / CARDS_DIR / shots["tracked01"][0]["source_ref"]).resolve(), source)

    def test_mixed_period_preserves_missing_history_and_tracks_its_own_denominator(self):
        self.save(result_fixture("old", "2003-11-01", tracked=False))
        self.save(result_fixture())
        records, shots = closed_card_feeds(self.ctx)
        stat = period_statistics(records["tracked01"], shots["tracked01"], PERIOD)
        self.assertEqual((stat["summary"]["gp"], stat["summary"]["totals"]["fga"]), (2, 4))
        self.assertEqual(stat["shooting"]["coverage"]["status"], "partial")
        self.assertEqual(stat["shooting"]["coverage"]["missing_attempts"], 2)
        self.assertTrue(all(z["fga_per_game"] is None for z in stat["shooting"]["zones"]))
        tracked = stat["tracked"]
        self.assertEqual((tracked["appearances"], tracked["box"]["fga"]), (1, 2))
        self.assertEqual(tracked["shooting"]["coverage"]["status"], "complete")
        self.assertEqual(tracked["shooting"]["bins"][0]["fga_per_game"], 2)
        self.assertEqual((tracked["start"], tracked["end"]), ("2003-11-02", "2003-11-02"))
        self.assertEqual([s["id"] for s in tracked["source_games"]], ["tracked"])
        self.assertEqual(tracked["source_games"][0]["shot_source_label"], "Simulated engine shot data")
        self.assertEqual(tracked["source_games"][0]["shot_href"], shots["tracked01"][0]["source_ref"])
        self.assertEqual(stat["tracking_cohort"]["excluded_games"], 1)
        data = card_data(self.ctx, self.ctx.registry["players"][0], records["tracked01"], shots["tracked01"])
        payload = html_payload(self.ctx, data)
        period = payload["periods"][0]
        self.assertEqual(period["tracked"]["box"]["fga"], 2)
        self.assertEqual(period["box"]["fga"], 4)
        self.assertEqual(period["cutoff"], self.ctx.on)
        self.assertEqual(payload["mode"], "live")
        self.assertEqual(payload["enabled_tabs"], ["shooting", "awards"])
        self.assertIn("tracked01.html#contract", payload["links"]["contract"])
        html = html_card(self.ctx, data)
        self.assertIn('id="cohort-select"', html)
        self.assertIn("Simulated engine shot locations", html)
        self.assertNotIn("FICTIONAL EXAMPLE", html)
        self.assertIn("1 tracked appearances form the denominator", markdown_card(self.ctx, data))

    def test_zero_attempt_tracked_appearance_keeps_provenance_and_old_feed_unknown(self):
        self.save(result_fixture("old", "2003-11-01", tracked=False))
        self.save(result_fixture(zero_attempts=True))
        records, shots = closed_card_feeds(self.ctx)
        self.assertEqual(shots["tracked01"], [])
        stat = period_statistics(records["tracked01"], [], PERIOD)
        self.assertEqual(stat["shooting"]["coverage"]["status"], "unavailable")
        self.assertEqual(stat["tracked"]["appearances"], 1)
        self.assertEqual(stat["tracked"]["box"]["fga"], 0)
        self.assertEqual(stat["tracked"]["shot_source_type"], "engine_generated")
        self.assertEqual(stat["shot_source_type"], "engine_generated")

    def test_wrong_event_shooter_and_conflicting_request_identity_are_rejected(self):
        result = result_fixture()
        result["shots"][0]["player_id"] = "Someone outside the box"
        path = self.save(result)
        with self.assertRaisesRegex(ValueError, "shooter is absent"):
            closed_card_feeds(self.ctx)
        path.unlink()
        result = result_fixture(home="Miami Heat")
        self.miami_note(result, status="played", request={"home": {"players": [
            {"player_id": "Tracked Guard", "bbr_id": "other01"}]}})
        self.lookup.return_value = {("Miami Heat", "trackedguard"): "tracked01"}
        with self.assertRaisesRegex(ValueError, "player identity disagrees"):
            closed_card_feeds(self.ctx)
        self.lookup.return_value = {}
        with self.assertRaisesRegex(ValueError, "named registry player"):
            closed_card_feeds(self.ctx)

    def test_multiple_result_names_cannot_claim_one_tracked_registry_player(self):
        self.save(result_fixture())
        self.ctx.registry["players"] = self.ctx.registry["players"][:1]
        self.lookup.return_value = {("Home Club", "trackedguard"): "tracked01",
                                    ("Home Club", "otherguard"): "tracked01"}
        with self.assertRaisesRegex(ValueError, "duplicate tracked registry player"):
            closed_card_feeds(self.ctx)

    def test_authoritative_bbr_mapping_preserves_legitimate_name_aliases(self):
        self.ctx.registry["players"][0].update(name="Slava Medvedenko", bbr_id="medvest01", registry_id="medvest01")
        self.save(result_fixture(guard="Stanislav Medvedenko"))
        self.lookup.return_value = {("Home Club", "stanislavmedvedenko"): "medvest01"}
        records, shots = closed_card_feeds(self.ctx)
        self.assertEqual(len(records["medvest01"]), 1)
        self.assertEqual(len(shots["medvest01"]), 2)
        self.assertTrue(all(s["player_id"] == "Stanislav Medvedenko" for s in shots["medvest01"]))


if __name__ == "__main__":
    unittest.main()
