import json
import shutil
import tempfile
import unittest

from tests import checkpoint
from pathlib import Path

from runtime import camp, season_games
from runtime.game_requests import find_requests, load_request, request_errors
from runtime.player_reports import report_errors
from runtime.private_service import Store, play_requests

ROOT = Path(__file__).resolve().parents[1]
TEAM = Path("career/Dwyane_Wade/2003-04/00_Team/Team")


def copy_repo():
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    for folder in ("library", "career", "foundation", "docs"):
        shutil.copytree(ROOT / folder, root / folder)
    checkpoint.pin(root)                      # tests simulate from the June 26 checkpoint, not the live clock
    return tmp, root


def write_minimal_rotation(root, grade_from="2003-10-24"):
    """A camp decision for the checkpoint register: the depth chart's order with Wade at SG, the season minutes."""
    roster = json.loads((root / TEAM / "Roster/roster.json").read_text())
    depth = json.loads((root / TEAM / "Depth_Chart/depth_chart.json").read_text())
    depth["positions"]["SG"].insert(1, "Dwyane Wade")
    names = [n for group in depth["positions"].values() for n in group]
    players = [{"player": p["name"], "bbr_id": p.get("bbr_id"), "positions": p["positions"], "status": "roster", "injured_through": None}
               for p in roster["players"] if p["name"] in names]
    # This fixture models a completed camp: players in its rotation are signed,
    # rather than retaining June's pending-option/draft-rights register labels.
    for player in roster["players"]:
        if player["name"] in names:
            player["status"] = "under_contract"
    roster["as_of"] = "2003-10-24"
    values = {n: len(names) - i for i, n in enumerate(names)}
    rotation = camp.season_rotation({"players": players}, depth, values, "2003-10-24", {"Dwyane Wade": 45})
    # A camp decision implies the players are under Miami's control: the holdings record (rule 2) says so, as the
    # free-agency and camp drivers would have written it, so no real club also dresses them.
    holdings_path = root / TEAM / "Roster/holdings.json"
    holdings = json.loads(holdings_path.read_text())
    for e in holdings["entries"]:
        if e["player"] in names:
            e["until"] = None
    held_names = {e["player"] for e in holdings["entries"] if e["from"] <= roster["as_of"] and
                  (e["until"] is None or roster["as_of"] < e["until"])}
    for player in roster["players"]:
        if player["name"] not in held_names:
            # Keep former-player rows for the zero-appearance report, while
            # reflecting that June-only holdings have expired by this camp.
            player["status"] = "free_agent"
    (root / TEAM / "Roster/roster.json").write_text(json.dumps(roster, indent=1) + "\n")
    holdings_path.write_text(json.dumps(holdings, indent=1) + "\n")
    # ...and that they are signed: only players under a signed contract dress (camp.playable).
    # The cut to fifteen this fixture skips: the rotation plus the next men on the depth chart stay signed.
    dressed = [p["player_id"] for p in rotation["players"]]
    keep = set((dressed + [n for n in names if n not in dressed])[:camp.ROSTER_MAX])
    for p in roster["players"]:
        if p["name"] in keep and not camp.playable(p.get("status")):
            p["status"] = "under_contract"
        elif p["name"] not in keep and camp.playable(p.get("status")):
            p["status"] = "released"
    (root / TEAM / "Roster/roster.json").write_text(json.dumps(roster, indent=1) + "\n")
    (root / TEAM / "Depth_Chart/depth_chart.json").write_text(json.dumps(depth, indent=1) + "\n")
    (root / TEAM / "Depth_Chart/rotation.json").write_text(json.dumps(rotation, indent=1) + "\n")
    if (root / "library").is_dir():
        from runtime.write_back import write_statistics_pages
        write_statistics_pages(root)          # the not-started team pages follow the register
    grade = camp.wade_grade({})
    (root / TEAM / "defensive_grades.json").write_text(json.dumps(camp.grades_record([grade], grade_from), indent=1) + "\n")
    return rotation


def play_local(store, root):
    status = play_requests(store, root)
    for path in find_requests(root):
        result = path.with_name(path.name.replace(".request.json", ".result.json"))
        event = json.loads(path.read_text())["event_id"]
        if not result.exists() and store.result(event) is not None:
            result.write_text(json.dumps(store.result(event)) + "\n")
    return status


class RotationUnitTests(unittest.TestCase):
    def rotation(self):
        return {"players": [{"player_id": f"P{i}", "position": "SG", "minutes": m, "ratings": {}}
                            for i, m in enumerate(camp.SEASON_MINUTES)]}

    def test_full_rotation_keeps_240_and_only_grades_in_force(self):
        out = season_games.rotation_for(self.rotation(), {}, {"P0": 45})
        self.assertEqual([p["player_id"] for p in out], [f"P{i}" for i in range(11)])
        self.assertAlmostEqual(sum(p["minutes"] for p in out), 240)
        self.assertEqual(out[0]["ratings"], {"perimeter_defense": 45})
        self.assertEqual(out[1]["ratings"], {})

    def test_injured_player_leaves_and_the_next_man_takes_the_last_slot(self):
        bench = [{"name": "Sub A", "positions": ["PF"], "bbr_id": "subaaa01", "depth_position": "PF"}, {"name": "Sub B", "positions": ["C"]}]
        out = season_games.rotation_for(self.rotation(), {"P0": 2, "Sub A": 1}, {}, bench)
        names = [p["player_id"] for p in out]
        self.assertNotIn("P0", names)
        self.assertNotIn("Sub A", names)
        self.assertEqual(names[-1], "Sub B")
        self.assertEqual(len(out), 11)
        self.assertAlmostEqual(sum(p["minutes"] for p in out), 240)
        self.assertTrue(all(0 < p["minutes"] <= 48 for p in out))
        # Without a next man the minutes are re-scaled over the rest.
        short = season_games.rotation_for(self.rotation(), {"P0": 2}, {})
        self.assertEqual(len(short), 10)
        self.assertAlmostEqual(sum(p["minutes"] for p in short), 240)
        with self.assertRaises(ValueError):
            season_games.rotation_for(self.rotation(), {f"P{i}": 1 for i in range(11)}, {})

    def test_week_folders_and_slate_paths(self):
        self.assertEqual(season_games.week_dir("2003-10-28").name, "Week_4")
        self.assertEqual(season_games.week_dir("2003-10-28").parent.name, "10_October")
        self.assertEqual(season_games.week_dir("2004-01-03").parent.name, "01_January")
        with self.assertRaises(ValueError):
            season_games.week_dir("2003-08-01")
        self.assertTrue(season_games.is_league_slate(ROOT / season_games.slate_dir() / "x.request.json"))
        self.assertFalse(season_games.is_league_slate(ROOT / "career/Dwyane_Wade/2003-04/06_Regular_Season/10_October/Week_4/Game_1.request.json"))
        self.assertEqual(season_games.club_name_errors(ROOT), [])


class MiamiBuilderTests(unittest.TestCase):
    def test_games_on_their_dates_injuries_out_and_idempotent(self):
        tmp, root = copy_repo()
        self.addCleanup(tmp.cleanup)
        with self.assertRaises(ValueError):                     # no camp decision, no request
            season_games.build_miami("2003-10-28", root, write=True)
        write_minimal_rotation(root, grade_from="2003-10-29")
        self.assertEqual(season_games.build_miami("2003-10-27", root, write=True), [])   # nothing due before opening night
        week4 = root / "career/Dwyane_Wade/2003-04/06_Regular_Season/10_October/Week_4"
        plan = season_games.build_miami("2003-10-28", root, write=True)
        self.assertEqual([r["number"] for r in plan], [1])
        self.assertTrue((week4 / "Game_1.md").exists() and (week4 / "Game_1.request.json").exists())
        meta = season_games.note_meta(week4 / "Game_1.md")
        self.assertEqual((meta["status"], meta["competition"], meta["venue"], meta["opponent"], meta["result_file"]),
                         ("scheduled", "regular", "away", "Philadelphia 76ers", "Game_1.result.json"))
        self.assertEqual(meta["event_id"], "2003-10-28-miami-heat-at-philadelphia-76ers")
        first = json.loads((week4 / "Game_1.request.json").read_text())
        self.assertEqual(first["away"]["team"], "Miami Heat")
        self.assertEqual(first["home"], {"team": "Philadelphia 76ers", "rotation": "real"})
        self.assertAlmostEqual(sum(p["minutes"] for p in first["away"]["players"]), 240)
        wade = next(p for p in first["away"]["players"] if p["player_id"] == "Dwyane Wade")
        self.assertEqual(wade["ratings"], {})                     # the grade dates from October 29
        load_request(week4 / "Game_1.request.json", root)
        # Idempotent: a second run writes nothing and changes nothing.
        before = (week4 / "Game_1.request.json").read_bytes()
        self.assertEqual(season_games.build_miami("2003-10-28", root, write=True), [])
        self.assertEqual((week4 / "Game_1.request.json").read_bytes(), before)
        self.assertEqual(season_games.miami_check("2003-10-28", root), [])
        self.assertEqual(len(season_games.miami_check("2003-10-29", root)), 1)
        # The engine plays game 1; its result (with an injury added here) keeps a starter out of the next two games.
        store = Store(root / "data/e.sqlite3")
        store.initialize()
        status = play_local(store, root)
        self.assertEqual({v["status"] for v in status.values() if "decision" not in v.get("request", "")}, {"played"})
        result_path = week4 / "Game_1.result.json"
        result = json.loads(result_path.read_text())
        starter = first["away"]["players"][0]["player_id"]
        result["injuries"] = [{"side": "away", "player_id": starter, "kind": "test", "games_out": 2}]
        result_path.write_text(json.dumps(result) + "\n")
        plan = season_games.build_miami("2003-11-03", root, write=True)
        self.assertEqual([(r["number"], r["folder"].name) for r in plan], [(2, "Week_4"), (3, "Week_4"), (1, "Week_1")])
        for row in plan[:2]:
            request = json.loads(row["request_path"].read_text())
            side = request["home"] if request["home"]["team"] == "Miami Heat" else request["away"]
            names = [p["player_id"] for p in side["players"]]
            self.assertNotIn(starter, names)
            self.assertEqual(len(names), 11)                       # the next man up dresses
            self.assertAlmostEqual(sum(p["minutes"] for p in side["players"]), 240)
            self.assertEqual(next(p for p in side["players"] if p["player_id"] == "Dwyane Wade")["ratings"], {"perimeter_defense": 45})
            self.assertEqual(row["injured_out"], {starter: 2} if row["number"] == 2 else {starter: 1})
        back = json.loads(plan[2]["request_path"].read_text())
        self.assertIn(starter, [p["player_id"] for p in back["away"]["players"]])
        self.assertEqual(plan[2]["injured_out"], {})
        self.assertEqual(season_games.note_meta(plan[2]["note_path"])["venue"], "away")
        self.assertIn("November Week 1 Game 1", plan[2]["note_path"].read_text())
        self.assertEqual(request_errors(root), [])
        season_games.refresh_reports(root)
        self.assertEqual(report_errors(root, root / "career/Dwyane_Wade"), [])


class LeagueSlateTests(unittest.TestCase):
    def test_slate_is_written_on_its_dates_and_validated(self):
        tmp, root = copy_repo()
        self.addCleanup(tmp.cleanup)
        due, _ = season_games.build_slate("2003-10-29", root)
        self.assertEqual(len(due), 12)
        self.assertEqual(season_games.build_slate("2003-10-27", root, write=True)[0], [])
        written, errors = season_games.build_slate("2003-10-29", root, write=True, every=1)   # every request through the engine
        self.assertEqual((len(written), errors), (12, []))
        folder = root / season_games.slate_dir()
        self.assertTrue((folder / "README.md").exists())
        self.assertTrue((folder / "2003-10-28-dallas-mavericks-at-los-angeles-lakers.request.json").exists())
        self.assertFalse(any("miami" in p.name for p in folder.glob("*.request.json")))
        data = json.loads(written[0].read_text())
        self.assertEqual((data["game_type"], data["venue"], data["home"]["rotation"], data["away"]["rotation"]), ("regular", "home", "real", "real"))
        # Idempotent, and the check passes on what was written.
        self.assertEqual(season_games.build_slate("2003-10-29", root, write=True)[0], [])
        self.assertEqual(season_games.slate_check("2003-10-29", root), [])
        self.assertEqual(len(season_games.slate_check("2003-10-30", root)), 4)
        self.assertEqual(len(season_games.slate_sample(written, 5)), 4)
        self.assertEqual(request_errors(root), [])
        # A tampered request fails the structural check without the engine.
        data["venue"] = "neutral"
        written[0].write_text(json.dumps(data) + "\n")
        self.assertTrue(any("differs from the schedule" in e for e in season_games.slate_errors(written, root, every=len(written))))


if __name__ == "__main__":
    unittest.main()
