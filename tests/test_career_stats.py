import copy
import json
import tempfile
import unittest
from pathlib import Path

from runtime.career_stats import COUNTS, aggregate, collect_games, identity_at, normalize_line, select
from runtime.player_reports import build_reports, report_errors
from runtime.season_rules import area_available, month_markers, nba_cup_available, play_in_format, statistics_bucket
from scripts.create_game_note import season_dir
from scripts.build_player_preview import build_preview

ROOT = Path(__file__).resolve().parents[1]
PLAYER = ROOT / "career/Dwyane_Wade"
IDENTITY = json.loads((PLAYER / "professional_identity.json").read_text())


def line(**changes):
    row = dict.fromkeys(COUNTS, 0)
    row.update(seconds=1200, fgm=2, fga=4, ftm=2, fta=2, pts=6, ast=3, drb=2, tov=1)
    row.update(changes)
    return normalize_line(row)


def record(box=None, **changes):
    r = dict(status="played", event_id="one", competition="regular", coverage="complete",
             line=box or line(), appearance="Played", date="2003-11-01", season="2003-04")
    r.update(changes)
    return r


class AggregationTests(unittest.TestCase):
    def test_pooled_shooting_and_exact_minutes(self):
        rows = [record(line(fgm=1, fga=2, pts=4, seconds=600.5)),
                record(line(fgm=4, fga=10, pts=10, seconds=1800.5), event_id="two")]
        a = aggregate(rows)
        self.assertEqual(a["gp"], 2)
        self.assertEqual(a["totals"]["pts"], 14)
        self.assertAlmostEqual(a["rates"]["fg_pct"], 5/12)
        self.assertNotAlmostEqual(a["rates"]["fg_pct"], (.5 + .4)/2)
        self.assertAlmostEqual(a["minutes"], 2401/60)
        self.assertAlmostEqual(a["per36"]["pts"], 14 * 36 / (2401/60))

    def test_dnp_and_future_fixture_do_not_dilute_average(self):
        rows = [record(), record(event_id="dnp", line=None, appearance="DNP: inactive"),
                record(event_id=None, status="scheduled", coverage="not_played", line=None)]
        a = aggregate(rows)
        self.assertEqual((a["gp"], a["closed"], a["dnp"], a["pg"]["pts"]), (1, 2, 1, 6))

    def test_empty_and_unknown_are_different(self):
        empty = aggregate([])
        self.assertEqual(empty["gp"], 0)
        self.assertEqual(empty["totals"]["pts"], 0)
        self.assertIsNone(empty["rates"]["fg_pct"])
        a = aggregate([record(), record(event_id="missing", coverage="missing_box", line=None)])
        self.assertIsNone(a["gp"])
        self.assertIsNone(a["totals"]["pts"])
        self.assertIsNone(a["pg"]["pts"])

    def test_optional_fields_and_zero_denominators(self):
        a = aggregate([record(line(tov=0, fgm=0, fga=0, pts=2))])
        self.assertIsNone(a["gs"])
        self.assertIsNone(a["plus_minus"])
        self.assertIsNone(a["rates"]["fg_pct"])
        self.assertIsNone(a["rates"]["ast_to"])
        observed = aggregate([record(line(started=True, plus_minus=-4))])
        self.assertEqual((observed["gs"], observed["plus_minus"]), (1, -4))

    def test_weighted_free_throws_disable_conventional_ts(self):
        raw = dict.fromkeys(COUNTS, 0)
        raw.update(seconds=60, ftm=1, fta=1, ft_points=3, pts=3)
        a = aggregate([record(normalize_line(raw, weighted_free_throws=True))])
        self.assertEqual(a["totals"]["ft_points"], 3)
        self.assertIsNone(a["rates"]["ts_pct"])
        with self.assertRaises(ValueError):
            normalize_line(raw)

    def test_duplicates_and_mixed_competitions_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            aggregate([record(), record()])
        with self.assertRaisesRegex(ValueError, "different competitions"):
            aggregate([record(), record(event_id="two", competition="playoff")])

    def test_invalid_boxes_fail_closed(self):
        for changes in ({"pts": 99}, {"fgm": 5}, {"seconds": float("nan")}, {"ast": -1},
                        {"appeared": False}, {"started": "yes"}, {"tpm": 3, "tpa": 3}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                line(**changes)

    def test_month_to_date_excludes_later_week(self):
        a = record(date="2003-11-07")
        b = record(date="2003-11-08", event_id="two")
        self.assertEqual(aggregate(select([a, b], end="2003-11-07"))["gp"], 1)


class SeasonRulesTests(unittest.TestCase):
    def test_cup_first_season_and_single_bucket(self):
        self.assertFalse(nba_cup_available("2022-23"))
        self.assertTrue(nba_cup_available("2023-24"))
        for stage in ("group", "quarterfinal", "semifinal"):
            self.assertEqual(statistics_bucket("regular", "2023-24", stage), "regular")
            with self.assertRaises(ValueError):
                statistics_bucket("regular", "2003-04", stage)
        self.assertEqual(statistics_bucket("nba_cup_championship", "2023-24", "championship"), "nba_cup_championship")
        with self.assertRaises(ValueError):
            statistics_bucket("regular", "2023-24", "championship")

    def test_configuration_resolves_cup_by_year(self):
        config = json.loads((ROOT / "foundation/season_structure.json").read_text())
        cup = next(a for a in config["areas"] if a["folder"] == "10_NBA_Cup")
        self.assertFalse(area_available(cup, "2003-04"))
        self.assertTrue(area_available(cup, "2023-24"))
        for month in ("November", "December"):
            self.assertFalse(any("NBA Cup" in s for s in month_markers(config, month, "2022-23")))
            self.assertTrue(any("NBA Cup" in s for s in month_markers(config, month, "2023-24")))

    def test_play_in_historical_formats(self):
        self.assertIsNone(play_in_format("2003-04"))
        self.assertEqual(play_in_format("2019-20"), "2020_restart")
        self.assertEqual(play_in_format("2020-21"), "seventh_through_tenth")
        with self.assertRaises(ValueError):
            statistics_bucket("play_in", "2003-04")

    def test_game_creator_ignores_statistics_and_national_directories(self):
        self.assertEqual(season_dir().name, "2003-04")


class CanonicalSourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.player = self.root / "career/Dwyane_Wade"
        self.player.mkdir(parents=True)

    def game(self, relative="2003-04/06_Regular_Season/11_November/Week_1/Game_1.md", **changes):
        note = self.player / relative
        note.parent.mkdir(parents=True, exist_ok=True)
        meta = dict(type="game", status="played", date="2003-11-01", opponent="Opponent", venue="home",
                    competition="regular", result="W 100-90", result_file=note.stem + ".result.json")
        meta.update(changes)
        note.write_text("---\n" + "".join(f"{k}: {v}\n" for k, v in meta.items()) + "---\n\n# Game\n")
        raw = dict(event_id="event-one", game_date=meta["date"], season=relative.split("/")[0],
                   edition=meta.get("edition"), game_type=meta["competition"], terminated=True,
                   home="Miami Heat", away="Opponent", venue="home", game_seconds=2880,
                   final_score={"home": 100, "away": 90}, player_stats={"home": [{"player_id": "dwyane_wade", **line()}], "away": []},
                   inactive={"home": [], "away": []})
        source = note.parent / (note.stem + ".result.json")
        source.write_text(json.dumps(raw))
        return note, source, raw

    def test_only_declared_played_result_counts(self):
        note, source, raw = self.game()
        self.assertEqual(aggregate(collect_games(self.player, IDENTITY, "2003-11-01"))["gp"], 1)
        note.write_text(note.read_text().replace("result_file: Game_1.result.json", "result_file:"))
        self.assertIsNone(aggregate(collect_games(self.player, IDENTITY, "2003-11-01"))["gp"])

    def test_future_game_cannot_be_closed(self):
        self.game()
        with self.assertRaisesRegex(ValueError, "cutoff"):
            collect_games(self.player, IDENTITY, "2003-06-26")

    def test_wrong_month_wrong_season_duplicate_id(self):
        note, source, raw = self.game(date="2003-11-08")
        with self.assertRaisesRegex(ValueError, "month/week"):
            collect_games(self.player, IDENTITY, "2003-11-10")
        note.unlink()
        note, source, raw = self.game()
        raw["season"] = "2004-05"
        source.write_text(json.dumps(raw))
        with self.assertRaisesRegex(ValueError, "season"):
            collect_games(self.player, IDENTITY, "2003-11-10")
        raw["season"] = "2003-04"
        source.write_text(json.dumps(raw))
        self.game("2003-04/06_Regular_Season/11_November/Week_1/Game_2.md")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            collect_games(self.player, IDENTITY, "2003-11-10")

    def test_unfinished_impossible_and_mismatched_scores_rejected(self):
        note, source, raw = self.game()
        for field, value, message in (("terminated", False, "unfinished"),
                                      ("final_score", {"home": 101, "away": 90}, "score/venue"),
                                      ("game_seconds", 1, "minutes")):
            changed = {**raw, field: value}
            source.write_text(json.dumps(changed))
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, message):
                collect_games(self.player, IDENTITY, "2003-11-10")

    def test_absent_player_is_not_automatically_a_dnp(self):
        _, source, raw = self.game()
        raw["player_stats"]["home"] = []
        source.write_text(json.dumps(raw))
        self.assertIsNone(aggregate(collect_games(self.player, IDENTITY, "2003-11-01"))["gp"])
        raw["inactive"]["home"] = ["dwyane_wade"]
        source.write_text(json.dumps(raw))
        a = aggregate(collect_games(self.player, IDENTITY, "2003-11-01"))
        self.assertEqual((a["gp"], a["dnp"]), (0, 1))

    def test_cup_view_references_regular_game_and_is_not_created_in_2003(self):
        self.assertFalse(any("10_NBA_Cup" in p.parts for p in build_reports(ROOT, PLAYER)))
        folder = self.player / "2023-24"
        folder.mkdir()
        (folder / "current_state.json").write_text(json.dumps({"current_date": "2023-11-10"}))
        (self.player / "professional_identity.json").write_text(json.dumps(IDENTITY))
        (self.root / "foundation").mkdir()
        (self.root / "foundation/season_structure.json").write_text((ROOT / "foundation/season_structure.json").read_text())
        note, _, _ = self.game("2023-24/06_Regular_Season/11_November/Week_1/Game_1.md", date="2023-11-01", cup_stage="group")
        records = collect_games(self.player, IDENTITY, "2023-11-10")
        self.assertEqual(aggregate(select(records, competition="regular"))["gp"], 1)
        reports = build_reports(self.root, self.player)
        cup = folder / "10_NBA_Cup/README.md"
        self.assertIn("../06_Regular_Season/11_November/Week_1/Game_1.md", reports[cup])
        self.assertEqual(sum(p.name.startswith("Game_") for p in reports), 1)

    def test_national_stage_cannot_masquerade_as_nba_or_other_edition(self):
        note, source, raw = self.game("National_Team/World_Cup/2006/Final_Tournament/Group_A/Game_1.md",
            date="2006-08-20", competition="world_cup_finals", edition="2006", player_team="Example Country")
        raw["home"] = "Example Country"
        raw["game_seconds"] = 2400
        source.write_text(json.dumps(raw))
        records = collect_games(self.player, IDENTITY, "2006-08-20")
        self.assertEqual(aggregate(select(records, competition="world_cup_finals"))["gp"], 1)
        self.assertEqual(aggregate(select(records, competition="regular"))["gp"], 0)
        note.write_text(note.read_text().replace("edition: 2006", "edition: 2010"))
        with self.assertRaisesRegex(ValueError, "edition/competition"):
            collect_games(self.player, IDENTITY, "2006-08-20")


class ReportTests(unittest.TestCase):
    def test_dated_identity_keeps_earlier_status_and_correct_age(self):
        identity = copy.deepcopy(IDENTITY)
        identity["snapshots"].append({**identity["snapshots"][0], "as_of": "2003-07-20", "roster_status": "Signed"})
        self.assertEqual(identity_at(identity, "2003-06-26")["roster_status"], "Draft rights; unsigned")
        self.assertEqual(identity_at(identity, "2003-07-20")["roster_status"], "Signed")
        self.assertEqual(identity_at(identity, "2004-01-16")["age"], 19)
        self.assertEqual(identity_at(identity, "2004-01-17")["age"], 20)

    def test_current_reports_are_idempotent_and_canon_unchanged(self):
        self.assertEqual(report_errors(ROOT, PLAYER), [])
        self.assertEqual(collect_games(PLAYER, IDENTITY, "2003-06-26"), [])
        self.assertEqual(json.loads((PLAYER / "2003-04/current_state.json").read_text())["current_date"], "2003-06-26")

    def test_preview_is_reproducible_and_outside_career(self):
        for path, text in build_preview(ROOT).items():
            self.assertNotIn("career", path.relative_to(ROOT).parts)
            self.assertIn("ILLUSTRATIVE TEMPLATE ONLY", text)
            self.assertEqual(path.read_text(), text)


if __name__ == "__main__":
    unittest.main()
