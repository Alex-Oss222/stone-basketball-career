"""Canonical result write-back (roadmap item 13): notes, Wade's pages, Miami and league pages, cards."""
import hashlib
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

from runtime import camp, season_games, write_back
from runtime.game_requests import find_requests, request_errors
from runtime.league_cards import check_cards
from runtime.player_reports import report_errors
from runtime.private_service import Store, play_requests
from scripts.validate_repository import markdown_tables
from tests import checkpoint
from tests.test_season_games import copy_repo, write_minimal_rotation

ROOT = Path(__file__).resolve().parents[1]
PLAYER = Path("career/Dwyane_Wade")
SEASON = PLAYER / "2003-04"
STATS = PLAYER / "Stats_and_Awards"
MIAMI = "Miami Heat"


def play_local(store, root):
    """Play every request locally and write the result files as the collector does (test only)."""
    status = play_requests(store, root)
    for path in find_requests(root):
        result = path.with_name(path.name.replace(".request.json", ".result.json"))
        event = json.loads(path.read_text())["event_id"]
        if not result.exists() and store.result(event) is not None:
            result.write_text(json.dumps(store.result(event), indent=1, sort_keys=True) + "\n")
    return status


def rows_by_first_cell(text, header_start):
    """{first cell: row} over every table whose header begins with `header_start`."""
    out = {}
    for headers, rows in markdown_tables(text):
        if headers[:len(header_start)] == header_start:
            for row in rows:
                out[re.sub(r"^\[([^\]]+)\]\(.*\)$", r"\1", row[0])] = dict(zip(headers, row))
    return out


def ratio(made, att):
    return "N/A" if not att else f"{made / att:.3f}".removeprefix("0")


class WriteBackUnitTests(unittest.TestCase):
    def test_section_and_card_rows_are_idempotent(self):
        text = "---\ntype: phase\n---\n\n# Preseason\n\n## Events\n\n## Consequences\n"
        once = write_back.add_section_line(text, "## Events", "- game one (`e1`)", "e1")
        self.assertIn("## Events\n\n- game one (`e1`)\n\n## Consequences", once)
        self.assertEqual(write_back.add_section_line(once, "## Events", "- game one again (`e1`)", "e1"), once)
        twice = write_back.add_section_line(once, "## Events", "- game two (`e2`)", "e2")
        self.assertIn("- game one (`e1`)\n- game two (`e2`)\n\n## Consequences", twice)
        with self.assertRaises(ValueError):
            write_back.add_section_line(text, "## Missing", "x", "x")
        card = "# Card\n\n## Changes and coaching notes\n\n| Date | Finding | Evidence |\n| --- | --- | --- |\n| June 26, 2003 | Opened. | x |\n\n## Sources\n"
        added = write_back.add_card_row(card, "| October 28, 2003 | Injured in `e1`. | [Game](g.md) |", "e1")
        self.assertIn("| June 26, 2003 | Opened. | x |\n| October 28, 2003 | Injured in `e1`. | [Game](g.md) |\n\n## Sources", added)
        self.assertEqual(write_back.add_card_row(added, "| again | `e1` | y |", "e1"), added)

    def test_zero_results_leave_the_statistics_pages_unchanged(self):
        tmp, root = copy_repo()
        self.addCleanup(tmp.cleanup)
        write_back.write_statistics_pages(root)
        self.assertEqual(write_back.closed_results(root), [])
        for page, text in write_back.statistics_pages(root).items():
            self.assertEqual(page.read_text(encoding="utf-8"), text, page)

    def test_checkpoint_clears_future_game_logs_in_any_week_and_preseason(self):
        tmp, root = copy_repo()
        self.addCleanup(tmp.cleanup)
        week = root / SEASON / "06_Regular_Season/11_November/Week_1/note.md"
        preseason = root / SEASON / "05_Preseason/note.md"
        for note in (week, preseason):
            note.write_text(note.read_text().replace("status: not_started", "status: active")
                            + "\n- Future fixture result (`future-game-log`)\n")
        checkpoint.pin(root)
        for note in (week, preseason):
            self.assertNotIn("future-game-log", note.read_text())
            self.assertIn("status: not_started", note.read_text())
        self.assertIn("month: November\nweek: 1\ndays: 1-7", week.read_text())
        self.assertIn("## Games and events", week.read_text())
        self.assertIn("## Events", preseason.read_text())


class WriteBackRunTests(unittest.TestCase):
    def digest(self, root):
        out = {}
        for path in sorted((root / "career").rglob("*")):
            if path.is_file():
                out[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
        return out

    def test_results_flow_into_every_record_once(self):
        tmp, root = copy_repo()
        self.addCleanup(tmp.cleanup)
        write_minimal_rotation(root, grade_from="2003-10-24")
        roster = json.loads((root / SEASON / "00_Team/Team/Roster/roster.json").read_text())
        self.assertEqual(next(p["status"] for p in roster["players"] if p["name"] == "Alonzo Mourning"), "released")
        # Miami's regular-season opener from the builder, a preseason game from the camp note format, one league game.
        plan = season_games.build_miami("2003-10-28", root, write=True)
        self.assertEqual(len(plan), 1)
        regular_note, regular_request = plan[0]["note_path"], plan[0]["request_path"]
        regular = json.loads(regular_request.read_text())
        miami_side = "home" if regular["home"]["team"] == MIAMI else "away"
        players = [dict(p, ratings={}) for p in regular[miami_side]["players"]]
        pre_game = camp.miami_preseason_games(root)[0]
        pre_dir = root / SEASON / "05_Preseason"
        pre_note, pre_request = pre_dir / "Game_1.md", pre_dir / "Game_1.request.json"
        venue = "home" if pre_game["home"] == MIAMI else "away"
        pre_note.write_text(camp.preseason_note(1, pre_game, venue))
        other = {"team": pre_game["away"] if venue == "home" else pre_game["home"], "rotation": "real"}
        miami = {"team": MIAMI, "players": players}
        pre_request.write_text(json.dumps({"event_id": pre_game["game_id"], "game_date": pre_game["date"], "game_type": "preseason",
                                           "venue": "home", "home": miami if venue == "home" else other,
                                           "away": other if venue == "home" else miami}, indent=1) + "\n")
        slate_game = next(g for g in season_games.season_games("2003-04", root)
                          if g["date"] == "2003-10-28" and MIAMI not in (g["home"], g["away"]))
        slate = root / season_games.slate_dir()
        slate.mkdir(parents=True, exist_ok=True)
        (slate / f"{slate_game['game_id']}.request.json").write_text(json.dumps(season_games.slate_request(slate_game), indent=1) + "\n")
        self.assertEqual(request_errors(root), [])
        store = Store(root / "data/e.sqlite3")
        store.initialize()
        status = play_local(store, root)
        self.assertEqual({v["status"] for k, v in status.items() if "-at-" in k}, {"played"})
        for path in (regular_note, pre_note):
            self.assertTrue(path.with_name(path.stem + ".result.json").exists())
        # A result dated after the clock waits; the career clock is not moved by the write-back.
        self.assertEqual(write_back.pending_notes(root)[0], [])
        self.assertEqual(len(write_back.pending_notes(root)[1]), 2)
        errors_before = write_back.write_back_errors(root)
        self.assertEqual(errors_before, [])                     # nothing is due before the clock reaches the games
        state_path = root / SEASON / "current_state.json"
        state = json.loads(state_path.read_text())
        state.update(current_date="2003-10-28", current_area="06_Regular_Season", current_note="06_Regular_Season/10_October/Week_4/note.md")
        state_path.write_text(json.dumps(state, indent=1) + "\n")
        self.assertTrue(any("unwritten result" in e for e in write_back.write_back_errors(root)))
        # Add an injury to the preseason result the way the engine reports one (a draw the test fixes).
        pre_result_path = pre_dir / "Game_1.result.json"
        pre_result = json.loads(pre_result_path.read_text())
        pre_side = "home" if pre_result["home"] == MIAMI else "away"
        hurt = next(r["player_id"] for r in pre_result["player_stats"][pre_side] if r["seconds"] > 0 and r["player_id"] != "Dwyane Wade")
        pre_result["injuries"] = [{"side": pre_side, "player_id": hurt, "kind": "ankle sprain", "games_out": 2}]
        pre_result_path.write_text(json.dumps(pre_result, indent=1, sort_keys=True) + "\n")
        request_bytes = {p: p.read_bytes() for p in find_requests(root)}
        result_bytes = {p: p.read_bytes() for p in root.rglob("*.result.json")}

        report = write_back.run(root, write=True)
        self.assertEqual(report["problems"], [])
        self.assertEqual(len(report["written"]), 2)
        self.assertEqual(report["waiting"], [])
        self.assertEqual({p: p.read_bytes() for p in find_requests(root)}, request_bytes)      # never edited
        self.assertEqual({p: p.read_bytes() for p in root.rglob("*.result.json")}, result_bytes)
        self.assertEqual(json.loads(state_path.read_text())["current_date"], "2003-10-28")

        # 1. The notes: played, the score, the box score, the injuries; the phase notes log the games.
        result = json.loads(regular_note.with_name("Game_1.result.json").read_text())
        scores = result["final_score"]
        other_side = "away" if miami_side == "home" else "home"
        label = f"{'W' if scores[miami_side] > scores[other_side] else 'L'} {scores[miami_side]}-{scores[other_side]}"
        meta = season_games.note_meta(regular_note)
        self.assertEqual((meta["status"], meta["result"], meta["event_id"], meta["result_file"]), ("played", label, result["event_id"], "Game_1.result.json"))
        self.assertEqual(meta["simulation_source"], season_games.SIMULATION_SOURCE)
        text = regular_note.read_text()
        self.assertIn(f"**{result['away']} {scores['away']} at {result['home']} {scores['home']}", text)
        self.assertIn("### Box score\n\n```text\n", text)
        self.assertIn("TEAM", text)
        self.assertLess(text.index("<!-- game-result:start -->"), text.index("<!-- player-report:start -->"))
        pre_text = pre_note.read_text()
        pre_meta = season_games.note_meta(pre_note)
        self.assertEqual(pre_meta["status"], "played")
        self.assertIn("Preseason result: evidence for the preseason record", pre_text)
        self.assertIn(f"| {hurt} | ankle sprain | 2 |", pre_text)
        week_note = (regular_note.parent / "note.md").read_text()
        self.assertIn(f"event `{result['event_id']}`", week_note)
        self.assertIn(f"{MIAMI} {label}", week_note)
        phase_note = (pre_dir / "note.md").read_text()
        self.assertIn(f"event `{pre_result['event_id']}`", phase_note)
        self.assertIn(f"injuries: {hurt} (ankle sprain, out 2 games)", phase_note)
        roster = json.loads((root / SEASON / "00_Team/Team/Roster/roster.json").read_text())
        card = root / SEASON / "00_Team/Team/Player_Cards" / f"{next(p['id'] for p in roster['players'] if p['name'] == hurt)}.md"
        card_text = card.read_text()
        self.assertIn(f"| October 7, 2003 | Injured (ankle sprain) in event `{pre_result['event_id']}`: out 2 games;", card_text)
        self.assertIn("[Game 1 result](../../../05_Preseason/Game_1.md)", card_text)
        self.assertLess(card_text.index("## Changes and coaching notes"), card_text.index("October 7, 2003 | Injured"))
        self.assertLess(card_text.index("October 7, 2003 | Injured"), card_text.index("## Sources and uncertainty"))

        # 2. Wade's line on the game page, the week, month and season pages, with pooled percentages.
        wade = next(r for r in result["player_stats"][miami_side] if r["player_id"] == "Dwyane Wade")
        self.assertGreater(wade["seconds"], 0)
        game_row = rows_by_first_cell(text, ["Scope"])["This game"]
        self.assertEqual((game_row["G"], game_row["PTS"], game_row["FG%"]), ("1", f"{wade['pts']:.1f}", ratio(wade["fgm"], wade["fga"])))
        self.assertEqual(game_row["GS"], str(int(wade["started"])))
        for page in (STATS / "2003-04/10_October/Week_4/README.md", STATS / "2003-04/10_October/README.md", STATS / "2003-04/README.md",
                     SEASON / "06_Regular_Season/10_October/Week_4/README.md"):
            row = rows_by_first_cell((root / page).read_text(), ["Scope"])["This scope"]
            self.assertEqual(row["G"], "1", page)
            self.assertEqual(row["GS"], str(int(wade["started"])), page)
            self.assertEqual(row["PTS"], f"{wade['pts']:.1f}", page)
            self.assertEqual(row["TRB"], f"{wade['orb'] + wade['drb']:.1f}", page)
            self.assertEqual(row["MP"], f"{wade['seconds'] / 60:.1f}", page)
            self.assertEqual(row["FG%"], ratio(wade["fgm"], wade["fga"]), page)
            self.assertEqual(row["FT%"], ratio(wade["ftm"], wade["fta"]), page)
            self.assertEqual(row["3P%"], ratio(wade["tpm"], wade["tpa"]), page)
        pre_wade = next(r for r in pre_result["player_stats"][pre_side] if r["player_id"] == "Dwyane Wade")
        pre_row = rows_by_first_cell((root / SEASON / "05_Preseason/README.md").read_text(), ["Scope"])["This scope"]
        self.assertEqual((pre_row["G"], pre_row["PTS"]), ("1", f"{pre_wade['pts']:.1f}"))   # preseason: its own record, not the season's
        self.assertEqual(rows_by_first_cell((root / STATS / "2003-04/11_November/Week_1/README.md").read_text(), ["Scope"])["This scope"]["G"], "0")

        # 3. Miami's team page and the league pages, aggregated from the closed results.
        team_page = (root / STATS / "Team/2003-04/10_October/Week_4/Team_Stats.md").read_text()
        self.assertIn("As of October 28, 2003: 1 closed Miami game in this period.", team_page)
        record = next(rows for headers, rows in markdown_tables(team_page) if headers == write_back.TEAM_RECORD)[0]
        self.assertEqual(record[:3], ["1", "1" if label.startswith("W") else "0", "0" if label.startswith("W") else "1"])
        self.assertEqual(record[4], f"{scores[miami_side]:.1f}")
        self.assertEqual(record[6], f"{scores[miami_side] - scores[other_side]:+.1f}")
        production = rows_by_first_cell(team_page, ["Player", "Pos", "G"])
        self.assertEqual((production["Dwyane Wade"]["G"], production["Dwyane Wade"]["PPG"]), ("1", f"{wade['pts']:.1f}"))
        idle = next(n for n, row in production.items() if row["G"] == "0")    # on the register, no appearance
        self.assertEqual(production[idle]["G"], "0")
        self.assertNotIn("Alonzo Mourning", production)                     # released before the period: not a Miami row
        shooting = rows_by_first_cell(team_page, ["Player", "GS"])
        self.assertEqual(shooting["Dwyane Wade"]["GS"], str(int(wade["started"])))
        self.assertEqual((shooting["Dwyane Wade"]["FG"], shooting["Dwyane Wade"]["FG%"]), (f"{wade['fgm']}/{wade['fga']}", ratio(wade["fgm"], wade["fga"])))
        season_team = (root / STATS / "Team/2003-04/Team_Stats.md").read_text()
        self.assertIn("| [October 2003](10_October/Team_Stats.md) | October 1-31, 2003 | 1 | Through October 28, 2003 |", season_team)
        self.assertEqual(rows_by_first_cell(season_team, ["Player", "Pos", "G"])["Dwyane Wade"]["G"], "1")
        self.assertEqual(rows_by_first_cell((root / STATS / "Team/2003-04/11_November/Week_1/Team_Stats.md").read_text(), ["Player", "Pos", "G"])["Dwyane Wade"]["G"], "0")
        registry = json.loads((root / STATS / "League/player_registry.json").read_text())
        names = {p["name"] for p in registry["players"]}
        slate_result = json.loads((slate / f"{slate_game['game_id']}.result.json").read_text())
        appeared = {}
        for res in (result, slate_result):
            for side in ("home", "away"):
                for r in res["player_stats"][side]:
                    if r["seconds"] > 0 and r["player_id"] in names:
                        appeared[r["player_id"]] = (res[side], r)
        self.assertGreaterEqual(len({club for club, _ in appeared.values()}), 4)   # both clubs of both games reach the pages
        for page in (STATS / "League/2003-04/10_October/Week_4/League_Stats.md", STATS / "League/2003-04/10_October/League_Stats.md",
                     STATS / "League/2003-04/League_Stats.md"):
            league = (root / page).read_text()
            self.assertIn("2 closed games in this record · Through October 28, 2003.", league)
            rows = rows_by_first_cell(league, ["Player", "Age", "Club / rights"])
            registered = json.loads((root / STATS / "League/player_registry.json").read_text())["players"]
            self.assertEqual({p["name"] for p in registered} - set(rows), set(), page)  # every registered player, additions included
            self.assertGreater(len(registered), 407)                           # first appearances were registered
            for name, (club, r) in appeared.items():
                row = rows[name]
                self.assertEqual(row["G"], "1", (page, name))
                self.assertEqual(row["PTS"], f"{r['pts']:.1f}", (page, name))
                self.assertEqual(row["FG%"], ratio(r["fgm"], r["fga"]), (page, name))
                self.assertEqual(row["eFG%"], ratio(r["fgm"] + .5 * r["tpm"], r["fga"]), (page, name))
                self.assertEqual(row["GS"], str(int(r["started"])))
            self.assertEqual(rows["Alvin Williams"]["G"], "0")
            self.assertEqual(set(list(rows["Alvin Williams"].values())[5:]) - {"0"}, {"N/A"})
            self.assertIn("| Category | 1 | 2 | 3 |", league)
        self.assertIn("No eligible results yet.", (root / STATS / "League/2003-04/11_November/Week_1/League_Stats.md").read_text())
        self.assertEqual(rows_by_first_cell((root / STATS / "League/2003-04/11_November/Week_1/League_Stats.md").read_text(),
                                            ["Player", "Age", "Club / rights"])["Dwyane Wade"]["G"], "0")

        # 4. The league cards carry the closed results; a card for an unused player keeps N/A.
        wade_card = (root / STATS / "League/Players/wadedw01.md").read_text()
        season_row = rows_by_first_cell(wade_card, ["Scope"])["2003-04 regular season"]
        self.assertEqual((season_row["G"], season_row["PTS"]), ("1", f"{wade['pts']:.1f}"))
        self.assertEqual(season_row["GS"], str(int(wade["started"])))
        self.assertIn("1 closed games feed this card", wade_card)
        payload = json.loads(re.search(r'type="application/json">(.*?)</script>', (root / STATS / "League/Players/wadedw01.html").read_text(), re.S).group(1)
                             .replace("\\u003c", "<").replace("\\u003e", ">").replace("\\u0026", "&"))
        season_period = next(p for p in payload["periods"] if p["id"] == "season")
        # New-kernel locations survive collection/write-back unchanged and cover
        # precisely Wade's regular-season attempts, excluding preseason/others.
        chart = season_period["shooting"]
        self.assertEqual((season_period["games"], season_period["box"]["pts"], chart["coverage"]["status"]),
                         (1, wade["pts"], "complete"))
        self.assertEqual(season_period["shot_source_type"], "engine_generated")
        source_shots = [s for s in result["shots"] if s["side"] == miami_side and s["player_id"] == wade["player_id"]]
        displayed = {s["shot_id"]: s for s in season_period["shots"]}
        self.assertEqual(set(displayed), {s["shot_id"] for s in source_shots})
        for shot in source_shots:
            self.assertEqual({key: displayed[shot["shot_id"]][key] for key in shot}, shot)
            self.assertEqual(displayed[shot["shot_id"]]["game_id"], result["event_id"])
        for key in ("fgm", "fga", "tpm", "tpa"):
            self.assertEqual(chart["totals"][key], wade[key])
            self.assertEqual(sum(z[key] for z in chart["zones"]), wade[key])
            self.assertEqual(sum(b[key] for b in chart["bins"]), wade[key])
        self.assertEqual(chart["totals"]["fg_points"], 2 * wade["fgm"] + wade["tpm"])
        self.assertEqual((chart["coverage"]["located_attempts"], chart["coverage"]["missing_attempts"]), (wade["fga"], 0))
        self.assertEqual(season_period["tracked"]["appearances"], 1)
        self.assertEqual(season_period["tracked"]["box"]["fga"], wade["fga"])
        idle = rows_by_first_cell((root / STATS / "League/Players/willial02.md").read_text(), ["Scope"])
        self.assertEqual(idle["2003-04 regular season"]["G"], "0")
        self.assertEqual(check_cards(root), [])

        # 5. Idempotent, the checks are clean, and the game builder now keeps the injured player out.
        before = self.digest(root)
        again = write_back.run(root, write=True)
        self.assertEqual((again["written"], again["problems"], again["pages"], again["reports"]), ([], [], 0, 0))
        self.assertEqual(self.digest(root), before)
        self.assertEqual(write_back.write_back_errors(root, cards=True), [])
        self.assertEqual(report_errors(root, root / PLAYER), [])
        self.assertEqual(request_errors(root), [])
        self.assertEqual(season_games.miami_check("2003-10-28", root), [])
        self.assertEqual(write_back.closed_lines(root)[1], write_back.run(root)["unmatched"])
        # Repository validation on the written-back copy (the validator reads its module ROOT).
        for extra in ("README.md", "AGENTS.md", "runtime/README.md"):
            (root / extra).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / extra, root / extra)
        import scripts.validate_repository as validator
        original = validator.ROOT
        validator.ROOT = root
        try:
            self.assertEqual(validator.validate(), [])
        finally:
            validator.ROOT = original
        # A played note whose result label is edited is caught; so is a result removed from beside its note.
        regular_note.write_text(regular_note.read_text().replace(f"result: {label}", "result: W 1-0"))
        self.assertTrue(any("does not match the result file" in e for e in write_back.write_back_errors(root)))


if __name__ == "__main__":
    unittest.main()
