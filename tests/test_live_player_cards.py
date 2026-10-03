"""Live cards authenticate career sources, preserve missing evidence and stay read-only."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from runtime.career_stats import COUNTS, collect_games, normalize_line
from runtime.player_cards import (
    award_scope, build_player_cards, earned_annual_awards, load_recorded_shots,
    period_id, player_cards_data,
)
from runtime.stat_layout import PER_GAME_COLUMNS, ReportStyle


ROOT = Path(__file__).resolve().parents[1]
PLAYER = ROOT / "career/Dwyane_Wade"
IDENTITY = json.loads((PLAYER / "professional_identity.json").read_text())


def box(**changes):
    row = dict.fromkeys(COUNTS, 0)
    row.update(seconds=1200, fgm=1, fga=2, tpm=0, tpa=1, ftm=2, fta=2,
               pts=4, ast=3, drb=2, tov=1)
    row.update(changes)
    return normalize_line(row)


def annual(award_id="roy", **changes):
    row = dict(id=award_id, name="NBA Rookie of the Year", short_name="ROY",
               competition="regular", season="2003-04", status="earned",
               period_start="2003-10-28", period_end="2004-04-14",
               awarded_on="2004-04-30", source="2003-04/09_Offseason/Decision.md#award")
    row.update(changes)
    return row


class LiveCardFixtures(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.player = self.root / "career/Dwyane_Wade"
        (self.player / "2003-04").mkdir(parents=True)
        self.identity = deepcopy(IDENTITY)

    def game(self, name="Game_1", day="2003-11-01", *, line=None,
             competition="regular", season="2003-04"):
        # Like test_career_stats fixtures, a declared, terminated result owns
        # player evidence. Tests never run the engine or use real Wade results.
        week = min((int(day[-2:]) - 1) // 7 + 1, 4)
        phase = {"regular": f"06_Regular_Season/{day[5:7]}_November/Week_{week}",
                 "preseason": "05_Preseason", "playoff": "08_Playoffs/Round_1",
                 "summer_league": "02_Summer_League"}.get(competition, "Other")
        if competition == "world_cup_finals":
            folder = self.player / "National_Team/World_Cup/2006/Final_Tournament/Group_A"
        else:
            folder = self.player / season / phase
        folder.mkdir(parents=True, exist_ok=True)
        note = folder / f"{name}.md"
        event = name + "-" + competition + "-" + day
        meta = dict(type="game", status="played", date=day, opponent="Opponent", venue="home",
                    competition=competition, result="W 100-90", result_file=f"{name}.result.json")
        if competition == "world_cup_finals":
            meta.update(edition=season, player_team="Recorded National Team")
        note.write_text("---\n" + "".join(f"{k}: {v}\n" for k, v in meta.items()) + "---\n\n# Recorded game\n")
        source = folder / f"{name}.result.json"
        raw = dict(event_id=event, game_date=day, season=season, edition=season,
                   game_type=competition, terminated=True, home=meta.get("player_team", "Miami Heat"),
                   away="Opponent", venue="home", game_seconds=2880,
                   final_score={"home": 100, "away": 90},
                   player_stats={"home": [{"player_id": "dwyane_wade", **(line or box())}], "away": []},
                   inactive={"home": [], "away": []})
        source.write_text(json.dumps(raw))
        return note, source, raw

    def feed(self, note, raw, **changes):
        path = note.with_suffix(".shots.json")
        if "shot_file:" not in note.read_text():
            note.write_text(note.read_text().replace("type: game\n", "type: game\nshot_file: " + path.name + "\n"))
        envelope = dict(schema_version=1, record_type="recorded_player_shots",
                        player_id="dwyane_wade", event_id=raw["event_id"], date=raw["game_date"],
                        season=raw["season"], competition=raw["game_type"], recorded_on=raw["game_date"],
                        coordinate_system="nba_feet_from_basket", source_type="recorded_manual_tracking",
                        source_label="Recorded fixture tracking", shots=[
                            dict(shot_id=raw["event_id"] + ":1", x=1.125, y=2.25, made=True, value=2),
                            dict(shot_id=raw["event_id"] + ":2", x=23.25, y=1.75, made=False, value=3)])
        envelope.update(changes)
        path.write_text(json.dumps(envelope))
        return path, envelope

    def records(self, clock="2003-11-30"):
        return collect_games(self.player, self.identity, clock)

    def data(self, clock="2003-11-30", awards=()):
        return player_cards_data(self.player, self.identity, self.records(clock), awards, clock)

    def season(self, data, competition="regular", season="2003-04"):
        return next(p for p in data["periods"] if p["kind"] == "season"
                    and p["competition"] == competition and p["season"] == season)


class LiveRenderTests(LiveCardFixtures):
    def test_draft_checkpoint_has_actual_identity_empty_games_and_no_annual_awards(self):
        clock = "2003-06-26"
        # The draft checkpoint has no game notes; later notes belong to dates the card at this clock cannot see.
        records = [r for r in collect_games(PLAYER, IDENTITY, "9999-12-31") if r["date"] <= clock] if any(
            (PLAYER / "2003-04").rglob("Game_*.result.json")) else collect_games(PLAYER, IDENTITY, clock)
        before = json.dumps(IDENTITY, sort_keys=True)
        with patch("runtime.shot_chart.make_illustrative_shots", side_effect=AssertionError("synthetic feed called")):
            outputs = build_player_cards(ROOT, PLAYER, IDENTITY, records, [], clock)
        data = json.loads(outputs[PLAYER / "Stats_and_Awards/player_cards_data.json"])
        self.assertEqual(data["mode"], "live")
        self.assertEqual((data["identity"]["name"], data["identity"]["age"], data["identity"]["team"]),
                         ("Dwyane Wade", 19, "Miami Heat"))
        self.assertEqual(data["identity"]["status"], "Draft rights; unsigned")
        self.assertEqual(len(data["periods"]), 1)
        self.assertEqual((data["periods"][0]["appearances"], data["periods"][0]["games"]), (0, 0))
        self.assertEqual(data["periods"][0]["shots"], [])
        self.assertIsNone(data["periods"][0]["rates"]["fg_pct"])
        self.assertEqual(data["awards"]["scenarios"][0]["records"], [])
        self.assertNotIn("Example Player", json.dumps(data))
        self.assertNotIn("docs/examples", json.dumps(data))
        self.assertEqual(json.dumps(IDENTITY, sort_keys=True), before)
        self.assertNotIn("__PLAYER_CARD_DATA__", outputs[PLAYER / "Stats_and_Awards/player_cards.html"])

    def test_closed_box_without_declared_shots_keeps_locations_unavailable(self):
        note, _, raw = self.game()
        # An undeclared adjacent feed must never be discovered automatically.
        note.with_suffix(".shots.json").write_text(json.dumps({"shots": [{"x": 1, "y": 2}]}))
        data = self.data()
        period = self.season(data)
        self.assertEqual((period["box"]["fgm"], period["box"]["fga"]), (1, 2))
        self.assertEqual(period["shooting"]["coverage"]["status"], "unavailable")
        self.assertEqual(period["shots"], [])
        self.assertEqual(period["shooting"]["bins"], [])
        self.assertTrue(all(z["fga"] is None for z in period["shooting"]["zones"]))
        self.assertNotIn("shot_href", period["source_games"][0])
        self.assertEqual(period["source_games"][0]["id"], raw["event_id"])

    def test_missing_box_is_unknown_while_explicit_dnp_is_zero_appearances(self):
        note, source, raw = self.game()
        raw["player_stats"]["home"] = []
        source.write_text(json.dumps(raw))
        period = self.season(self.data())
        self.assertIsNone(period["appearances"])
        self.assertIsNone(period["box"]["fga"])
        self.assertEqual(period["dnp"], 0)
        raw["inactive"]["home"] = ["dwyane_wade"]
        source.write_text(json.dumps(raw))
        period = self.season(self.data())
        self.assertEqual((period["appearances"], period["dnp"], period["box"]["fga"]), (0, 1, 0))
        self.assertIsNone(period["rates"]["fg_pct"])
        note.write_text(note.read_text().replace("result_file: Game_1.result.json", "result_file:"))
        period = self.season(self.data())
        self.assertIsNone(period["appearances"])
        self.assertEqual(period["dnp"], 0)

    def test_render_returns_artifacts_without_writing_or_mutating_sources(self):
        note, _, raw = self.game()
        self.feed(note, raw)
        records = self.records()
        before_records = deepcopy(records)
        before_files = {p: p.read_bytes() for p in self.player.rglob("*") if p.is_file()}
        outputs = build_player_cards(self.root, self.player, self.identity, records, [], "2003-11-30")
        self.assertEqual(records, before_records)
        self.assertEqual({p: p.read_bytes() for p in self.player.rglob("*") if p.is_file()}, before_files)
        self.assertTrue(all(not p.exists() for p in outputs))
        self.assertIn(self.player / "Stats_and_Awards/Shooting.md", outputs)
        self.assertIn("Recorded shots", outputs[self.player / "Stats_and_Awards/Shooting.md"])

    def test_recorded_feeds_preserve_raw_coordinates_and_pool_period_totals(self):
        note, _, raw = self.game()
        self.feed(note, raw)
        note2, _, raw2 = self.game("Game_2", "2003-11-08", line=box(fgm=3, fga=4, tpm=1, tpa=2, pts=9))
        _, envelope = self.feed(note2, raw2, shots=[
            dict(shot_id="g2:1", x=-1.125, y=1.125, made=True, value=2),
            dict(shot_id="g2:2", x=3.125, y=8.125, made=True, value=2),
            dict(shot_id="g2:3", x=-23.125, y=1.125, made=True, value=3),
            dict(shot_id="g2:4", x=-23.375, y=1.375, made=False, value=3)])
        data = self.data()
        season = self.season(data)
        self.assertEqual((season["box"]["fgm"], season["box"]["fga"], season["appearances"]), (4, 6, 2))
        self.assertAlmostEqual(season["rates"]["fg_pct"], 4 / 6)
        self.assertEqual(season["shooting"]["coverage"]["status"], "complete")
        self.assertEqual(len(season["shots"]), 6)
        self.assertEqual((season["shots"][0]["x"], season["shots"][0]["y"]), (1.125, 2.25))
        self.assertEqual([(s["x"], s["y"]) for s in season["shots"][2:]],
                         [(s["x"], s["y"]) for s in envelope["shots"]])
        self.assertEqual(sum(z["fg_points"] for z in season["shooting"]["zones"]), 9)
        self.assertEqual(sum(z["fga_per_game"] for z in season["shooting"]["zones"]), 3)
        self.assertEqual({p["kind"] for p in data["periods"]}, {"season", "month", "week", "game"})
        self.assertEqual(len([p for p in data["periods"] if p["kind"] == "week"]), 2)
        for source in season["source_games"]:
            page = self.player / "Stats_and_Awards/player_cards.html"
            self.assertTrue((page.parent / source["href"]).resolve().is_file())
            self.assertTrue((page.parent / source["result_href"]).resolve().is_file())
            self.assertTrue((page.parent / source["shot_href"]).resolve().is_file())

    def test_missing_beginning_of_month_and_last_week_use_calendar_bounds(self):
        self.game(day="2003-11-25")
        note, _, _ = self.game("Game_2", "2003-11-30")
        note.write_text(note.read_text().replace("status: played", "status: scheduled").replace("result: W 100-90\n", ""))
        data = self.data("2003-11-26")
        month = next(p for p in data["periods"] if p["kind"] == "month")
        week = next(p for p in data["periods"] if p["kind"] == "week")
        self.assertEqual((month["start"], month["end"]), ("2003-11-01", "2003-11-26"))
        self.assertEqual((week["start"], week["end"]), ("2003-11-22", "2003-11-26"))
        self.assertIn("2003-11-22 to 2003-11-26", week["label"])
        self.assertTrue(all(g["date"] <= "2003-11-26" for p in data["periods"] for g in p["source_games"]))
        self.assertEqual(self.season(data)["games"], 1)

    def test_competitions_and_national_geometry_remain_separate(self):
        self.game()
        self.game("Game_2", "2003-11-02", competition="preseason")
        self.game("Game_3", "2006-08-20", competition="world_cup_finals", season="2006")
        data = self.data("2006-08-20")
        regular = self.season(data)
        preseason = self.season(data, "preseason")
        national = self.season(data, "world_cup_finals", "2006")
        self.assertEqual((regular["games"], preseason["games"], national["games"]), (1, 1, 1))
        self.assertTrue(regular["geometry_supported"])
        self.assertFalse(national["geometry_supported"])
        self.assertEqual(national["shots"], [])
        self.assertEqual(national["shooting"]["bins"], [])
        self.assertIn("no verified court-geometry adapter", national["source_note"])


class RecordedShotAdapterTests(LiveCardFixtures):
    def test_feed_requires_matching_recorded_envelope(self):
        note, _, raw = self.game()
        path, valid = self.feed(note, raw)
        records = self.records()
        invalid = [
            ("player_id", "different_player"), ("event_id", "different_event"),
            ("date", "2003-11-02"), ("season", "2004-05"), ("competition", "playoff"),
            ("schema_version", 2), ("record_type", "illustrative_synthetic_locations"),
            ("coordinate_system", "fiba_metres"), ("source_type", "synthetic"),
            ("source_label", " "), ("recorded_on", "2003-10-31"),
            ("recorded_on", "2003-12-01"), ("recorded_on", "invalid"), ("shots", {})]
        for key, value in invalid:
            with self.subTest(key=key, value=value):
                path.write_text(json.dumps({**valid, key: value}))
                with self.assertRaises(ValueError):
                    load_recorded_shots(self.player, self.identity, records, "2003-11-30")
        path.write_text(json.dumps({**valid, "source_type": "recorded_event_feed"}))
        shots, sources = load_recorded_shots(self.player, self.identity, records, "2003-11-30")
        self.assertEqual(len(shots), 2)
        self.assertEqual(sources[raw["event_id"]]["path"], path)

    def test_declaration_must_be_existing_adjacent_json_inside_career(self):
        note, _, raw = self.game()
        path, _ = self.feed(note, raw)
        valid_note = note.read_text()
        elsewhere = note.parent.parent / path.name
        elsewhere.write_bytes(path.read_bytes())
        text_path = path.with_suffix(".txt")
        text_path.write_bytes(path.read_bytes())
        for declaration in ("../" + path.name, "missing.json", text_path.name):
            with self.subTest(declaration=declaration):
                note.write_text(valid_note.replace(path.name, declaration))
                with self.assertRaisesRegex(ValueError, "existing adjacent JSON"):
                    load_recorded_shots(self.player, self.identity, self.records(), "2003-11-30")
        outside = self.root / "outside.json"
        outside.write_bytes(path.read_bytes())
        link = note.parent / "linked.json"
        link.symlink_to(outside)
        note.write_text(valid_note.replace(path.name, link.name))
        with self.assertRaisesRegex(ValueError, "existing adjacent JSON"):
            load_recorded_shots(self.player, self.identity, self.records(), "2003-11-30")

    def test_future_game_and_unplayed_shot_feeds_cannot_enter_adapter(self):
        note, _, raw = self.game()
        self.feed(note, raw)
        rows = self.records()
        with self.assertRaisesRegex(ValueError, "career cutoff"):
            load_recorded_shots(self.player, self.identity, rows, "2003-10-31")
        rows[0]["status"] = "scheduled"
        self.assertEqual(load_recorded_shots(self.player, self.identity, rows, "2003-11-30"), ([], {}))

    def test_shot_event_date_geometry_and_outcomes_are_checked(self):
        note, _, raw = self.game()
        path, valid = self.feed(note, raw)
        for changes in ({"game_id": "orphan"}, {"date": "2003-11-02"}, {"value": 3},
                        {"made": "yes"}, {"x": True}, {"shot_id": ""}):
            with self.subTest(changes=changes):
                bad = deepcopy(valid)
                bad["shots"][0].update(changes)
                path.write_text(json.dumps(bad))
                with self.assertRaises(ValueError):
                    load_recorded_shots(self.player, self.identity, self.records(), "2003-11-30")
        bad = deepcopy(valid)
        bad["shots"][1]["made"] = True
        path.write_text(json.dumps(bad))
        with self.assertRaisesRegex(ValueError, "outcomes do not reconcile"):
            load_recorded_shots(self.player, self.identity, self.records(), "2003-11-30")

    def test_dnp_and_unknown_player_boxes_cannot_supply_shots(self):
        note, source, raw = self.game()
        self.feed(note, raw)
        raw["player_stats"]["home"] = []
        source.write_text(json.dumps(raw))
        with self.assertRaisesRegex(ValueError, "matching closed player box"):
            load_recorded_shots(self.player, self.identity, self.records(), "2003-11-30")
        raw["inactive"]["home"] = ["dwyane_wade"]
        source.write_text(json.dumps(raw))
        with self.assertRaisesRegex(ValueError, "DNP cannot"):
            load_recorded_shots(self.player, self.identity, self.records(), "2003-11-30")

    def test_duplicate_shot_ids_across_games_are_rejected(self):
        note, _, raw = self.game()
        _, first = self.feed(note, raw)
        note2, _, raw2 = self.game("Game_2", "2003-11-02")
        self.feed(note2, raw2, shots=first["shots"])
        with self.assertRaisesRegex(ValueError, "unique across source games"):
            load_recorded_shots(self.player, self.identity, self.records(), "2003-11-30")

    def test_illustrative_shots_cannot_be_relabelled_as_recorded_evidence(self):
        note, _, raw = self.game()
        path, valid = self.feed(note, raw)
        for marker in ({"example_only": True}, {"synthetic": True},
                       {"source_ref": "example:fictional-locations/illustrative-1"}):
            with self.subTest(marker=marker):
                bad = deepcopy(valid)
                bad["shots"][0].update(marker)
                path.write_text(json.dumps(bad))
                with self.assertRaises(ValueError):
                    load_recorded_shots(self.player, self.identity, self.records(), "2003-11-30")

    def test_partial_declared_feed_keeps_observed_counts_and_withholds_period_rates(self):
        note, _, raw = self.game()
        _, feed = self.feed(note, raw)
        self.feed(note, raw, shots=feed["shots"][:1])
        season = self.season(self.data())
        self.assertEqual(season["shooting"]["coverage"]["status"], "partial")
        self.assertEqual(season["shooting"]["observed"]["fga"], 1)
        self.assertEqual(season["shooting"]["coverage"]["missing_attempts"], 1)
        self.assertTrue(all(z["fga_per_game"] is None for z in season["shooting"]["zones"]))
        self.assertTrue(all(b["area_weight"] is None for b in season["shooting"]["bins"]))

    def test_national_feed_needs_separate_verified_geometry_adapter(self):
        note, _, raw = self.game(day="2006-08-20", competition="world_cup_finals", season="2006")
        self.feed(note, raw)
        with self.assertRaisesRegex(ValueError, "separately verified shot geometry"):
            load_recorded_shots(self.player, self.identity, self.records("2006-08-20"), "2006-08-20")


class AnnualAwardTests(LiveCardFixtures):
    def test_scope_is_optional_but_only_recognized_legacy_types_are_annual(self):
        for name in ("NBA Most Valuable Player", "NBA Rookie of the Year", "NBA Defensive Player of the Year",
                     "NBA Most Improved Player", "NBA Sixth Man of the Year", "All-NBA First Team",
                     "All-Defensive Second Team", "All-Rookie First Team", "NBA Champion", "NBA Finals MVP",
                     "NBA All-Star", "NBA All-Star selection"):
            with self.subTest(name=name):
                self.assertEqual(award_scope(annual(name=name)), "annual")
        self.assertEqual(award_scope(annual(name="NBA All-Star Game MVP")), "event")
        self.assertEqual(award_scope(annual(name="NBA All-Star selection", scope="event")), "event")
        self.assertEqual(award_scope(annual(name="Community recognition")), "unclassified")
        self.assertEqual(award_scope(annual(name="National MVP", competition="world_cup_finals")), "unclassified")
        self.assertEqual(award_scope(annual(name="Custom verified award", scope="annual")), "annual")
        with self.assertRaisesRegex(ValueError, "award scope"):
            award_scope(annual(scope="unknown"))

    def test_weekly_monthly_pending_future_and_other_season_awards_are_excluded(self):
        awards = [annual(), annual("week", name="Eastern Conference Player of the Week", scope="annual"),
                  annual("month", name="Eastern Conference Rookie of the Month", scope="annual"),
                  annual("pending", status="pending"), annual("nominated", status="nominated"),
                  annual("future", awarded_on="2004-05-01"), annual("undated", awarded_on=None),
                  annual("other", season="2004-05"), annual("event", scope="event")]
        self.assertEqual([a["id"] for a in earned_annual_awards(awards, "2003-04", "2004-04-30")], ["roy"])
        self.assertEqual(earned_annual_awards(awards, "2003-04", "2004-04-29"), [])

    def test_annual_sources_preserve_anchors_and_markdown_has_only_earned_badges(self):
        source = self.player / "2003-04/09_Offseason/Decision.md"
        source.parent.mkdir(parents=True)
        source.write_text("# Decision\n\n## Award\nEarned award fixture.\n")
        awards = [annual(), annual("allstar", name="NBA All-Star selection", awarded_on="2004-02-01"),
                  annual("weekly", name="Player of the Week", scope="weekly")]
        outputs = build_player_cards(self.root, self.player, self.identity, [], awards, "2004-04-30")
        data = json.loads(outputs[self.player / "Stats_and_Awards/player_cards_data.json"])
        record = data["awards"]["scenarios"][0]["records"][0]
        self.assertEqual(record["source_href"], "../2003-04/09_Offseason/Decision.md#award")
        markdown = outputs[self.player / "Stats_and_Awards/Awards.md"]
        self.assertIn(record["source_href"], markdown)
        self.assertIn("NBA Rookie of the Year", markdown)
        self.assertIn("NBA All-Star selection", markdown)
        self.assertNotIn("Player of the Week", markdown)
        self.assertEqual(len([p for p in outputs if p.name.startswith("annual_")]), 2)


class LiveNavigationTests(LiveCardFixtures):
    def test_cards_navigation_is_opt_in_and_keeps_complete_stat_columns(self):
        note, _, _ = self.game()
        records = self.records()
        page = self.player / "Stats_and_Awards/2003-04/11_November/Week_1/README.md"
        assets = self.player / "assets/stat_reports"
        legacy = ReportStyle(self.identity, [], "2003-11-30", {}, assets, self.player)
        self.assertEqual(legacy.cards_navigation(page), "")
        data = self.data()
        style = ReportStyle(self.identity, [], "2003-11-30", {}, assets, self.player,
                            cards_root=self.player / "Stats_and_Awards",
                            card_periods=[p["id"] for p in data["periods"]],
                            default_card_period=data["default_period"], detailed=True)
        rendered = style.per_game(page, [("Week 1", records, page)])
        for column in PER_GAME_COLUMNS:
            self.assertIn("| " + column + " ", rendered)
        self.assertIn("[![Shooting]", rendered)
        self.assertIn("[![Awards]", rendered)
        week_id = period_id("regular", "2003-04", "week", "2003-11-01")
        self.assertIn("[![Shooting](../../../assets/shooting_link.svg)](../../../player_cards.html?period="
                      + week_id + "#shooting)", rendered)
        self.assertIn("[![Awards](../../../assets/awards_link.svg)](../../../player_cards.html#awards)", rendered)
        self.assertIn("[Shooting detail](../../../Shooting.md)", rendered)
        self.assertIn("[Annual award record](../../../Awards.md)", rendered)
        game_navigation = style.cards_navigation(note, [("Game", records, note)])
        self.assertIn("?period=" + period_id("regular", "2003-04", "game", event_id=records[0]["event_id"]), game_navigation)
        future_page = self.player / "Stats_and_Awards/2003-04/12_December/Week_1/README.md"
        self.assertIn("?period=" + data["default_period"], style.cards_navigation(future_page))

    def test_missing_result_game_has_stable_relative_period_id_and_direct_navigation(self):
        note, _, _ = self.game()
        note.write_text(note.read_text().replace("result_file: Game_1.result.json", "result_file:"))
        records = self.records()
        data = self.data()
        game = next(p for p in data["periods"] if p["kind"] == "game")
        expected = period_id("regular", "2003-04", "game", event_id=note.relative_to(self.player).as_posix())
        self.assertEqual(game["id"], expected)
        self.assertIsNone(game["appearances"])
        style = ReportStyle(self.identity, [], "2003-11-30", {}, self.player / "assets/stat_reports", self.player,
                            cards_root=self.player / "Stats_and_Awards",
                            card_periods=[p["id"] for p in data["periods"]],
                            default_card_period=data["default_period"], detailed=True)
        navigation = style.cards_navigation(note, [("Missing player box", records, note)])
        self.assertIn("?period=" + expected + "#shooting", navigation)


if __name__ == "__main__":
    unittest.main()
