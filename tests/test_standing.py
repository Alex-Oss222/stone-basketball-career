"""Wade's standing (runtime/standing.py): the pure rule, the dated computation, the snapshot file and its validation."""
import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from runtime import front_office, gm, signing, standing
from runtime.career_stats import COUNTS, normalize_line
from runtime.front_office import rookie_offer
from scripts import update_standing

ROOT = Path(__file__).resolve().parents[1]
PLAYER = Path("career/Dwyane_Wade")
SEASON_DIR = PLAYER / "2003-04"
SIGN_DAY = "2003-07-20"


def copy_repo():
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    shutil.copytree(ROOT / "library", root / "library")
    shutil.copytree(ROOT / "career", root / "career")
    return tmp, root


def season(name, gp, gs, scheduled=82, minutes=30.0, complete=True):
    return {"season": name, "gp": gp, "gs": gs, "scheduled": scheduled, "minutes_per_game": minutes, "complete": complete}


def honor(name, season_name, number=1):
    return {"id": f"honor-{number}", "name": name, "season": season_name}


def sign_wade(root, day=SIGN_DAY):
    """Wade signs his rookie-scale contract on a copy (the sheet's signed_date is what the rule reads)."""
    writer = signing.Writer(root)
    signing.sign_rookie(writer, {"entries": []}, rookie_offer(5)["terms"], day)
    writer.commit()


def set_state(root, **fields):
    path = root / SEASON_DIR / "current_state.json"
    state = json.loads(path.read_text())
    state.update(fields)
    path.write_text(json.dumps(state, indent=1) + "\n")


def played_game(root, relative="2003-04/06_Regular_Season/11_November/Week_1/Game_1.md", day="2003-11-01", started=True):
    """One closed regular-season game with Wade's box (the fixture of tests/test_career_stats.py)."""
    note = root / PLAYER / relative
    note.parent.mkdir(parents=True, exist_ok=True)
    meta = dict(type="game", status="played", date=day, opponent="Opponent", venue="home", competition="regular",
                result="W 100-90", result_file=note.stem + ".result.json")
    note.write_text("---\n" + "".join(f"{k}: {v}\n" for k, v in meta.items()) + "---\n\n# Game\n")
    row = dict.fromkeys(COUNTS, 0)
    row.update(seconds=1800, fgm=5, fga=10, ftm=2, fta=2, pts=12, ast=4, drb=3, tov=1, started=started)
    raw = dict(event_id=f"event-{note.stem}", game_date=day, season=relative.split("/")[0], edition=None, game_type="regular",
               terminated=True, home="Miami Heat", away="Opponent", venue="home", game_seconds=2880,
               final_score={"home": 100, "away": 90}, player_stats={"home": [{"player_id": "dwyane_wade", **normalize_line(row)}], "away": []},
               inactive={"home": [], "away": []})
    (note.parent / (note.stem + ".result.json")).write_text(json.dumps(raw))
    return note


def close_season(root, close_date="2004-04-15", scheduled=82):
    path = root / SEASON_DIR / "season_close.json"
    path.write_text(json.dumps({"schema_version": 1, "season": "2003-04", "close_date": close_date, "last_game": "2004-04-14",
                                "competitions_closed": ["regular"], "regular_season_games_scheduled": scheduled,
                                "source": "README.md"}, indent=1) + "\n")
    return path


class ClassifyTests(unittest.TestCase):
    def test_contract_state_comes_first(self):
        self.assertEqual(standing.classify(False, [], [])[0], "unsigned_rookie")
        with self.assertRaisesRegex(ValueError, "closed season without a contract"):
            standing.classify(False, [season("2003-04", 70, 60)], [])
        self.assertEqual(standing.classify(True, [], [])[0], "rookie")

    def test_starter_line(self):
        self.assertEqual(standing.classify(True, [season("2003-04", 70, 60)], [])[0], "starter")
        self.assertEqual(standing.classify(True, [season("2003-04", 40, 40)], [])[0], "rookie")          # under half the schedule
        self.assertEqual(standing.classify(True, [season("2003-04", 70, 30)], [])[0], "rookie")          # under half the starts
        self.assertEqual(standing.classify(True, [season("2003-04", 70, None, minutes=28.0)], [])[0], "starter")   # starts unobserved
        self.assertEqual(standing.classify(True, [season("2003-04", 70, None, minutes=27.9)], [])[0], "rookie")
        value, basis = standing.classify(True, [season("2003-04", None, None, minutes=None, complete=False)], [])
        self.assertEqual(value, "rookie")                                                              # no evidence, never zero games
        self.assertFalse(basis["starter_lines"]["2003-04"]["met"])
        # standing can fall: the most recent closed season decides the starter line
        self.assertEqual(standing.classify(True, [season("2004-05", 30, 10), season("2003-04", 70, 60)], [])[0], "rookie")

    def test_honors_need_the_starter_line_and_statistics_alone_stay_at_starter(self):
        met, missed = season("2003-04", 70, 60), season("2003-04", 70, 20)
        self.assertEqual(standing.classify(True, [met], [honor("All-Star", "2003-04")])[0], "all_star")
        value, basis = standing.classify(True, [missed], [honor("All-Star", "2003-04")])
        self.assertEqual(value, "rookie")
        self.assertEqual([c["honor"] for c in basis["conflicts"]], ["honor-1"])
        self.assertEqual(standing.classify(True, [season("2003-04", 82, 82, minutes=40.0)], [])[0], "starter")
        value, basis = standing.classify(True, [met], [honor("Rookie of the Month", "2003-04")])
        self.assertEqual((value, basis["ignored_honors"]), ("starter", ["honor-1"]))
        self.assertEqual(standing.classify(True, [met], [honor("All-Star", "2002-03")])[0], "starter")   # outside the window

    def test_franchise_rules(self):
        two = [season("2004-05", 75, 75), season("2003-04", 70, 60)]
        self.assertEqual(standing.classify(True, two, [honor("Most Valuable Player", "2003-04")])[0], "franchise")
        self.assertEqual(standing.classify(True, two, [honor("Finals MVP", "2004-05")])[0], "franchise")
        self.assertEqual(standing.classify(True, two, [honor("All-NBA Second Team", "2004-05")])[0], "franchise")
        self.assertEqual(standing.classify(True, two, [honor("All-NBA First Team", "2003-04")])[0], "all_star")   # older season only
        self.assertEqual(standing.classify(True, two, [honor("All-NBA Third Team", "2004-05")])[0], "all_star")
        self.assertEqual(standing.classify(True, two, [honor("All-NBA Third Team", "2004-05"), honor("All-NBA Third Team", "2003-04", 2)])[0], "franchise")
        self.assertEqual(standing.classify(True, two[:1], [honor("All-NBA Third Team", "2004-05")])[0], "all_star")   # one-season window
        # an All-NBA season below the starter line does not promote
        self.assertEqual(standing.classify(True, [season("2004-05", 70, 20), two[1]], [honor("All-NBA First Team", "2004-05")])[0], "rookie")


class ComputeTests(unittest.TestCase):
    def test_june_26_is_an_unsigned_rookie_without_a_snapshot_file(self):
        tmp, root = copy_repo()
        self.addCleanup(tmp.cleanup)
        result = standing.compute(root, "2003-06-26")
        self.assertEqual(result["standing"], "unsigned_rookie")
        self.assertEqual((result["as_of"], result["basis"]["signed_date"], result["basis"]["season_folder"]), ("2003-06-26", None, "2003-04"))
        self.assertEqual(standing.standing_on(root, "2003-06-26")["standing"], "unsigned_rookie")
        self.assertEqual(standing.standing_errors(root), [])            # missing file accepted while unsigned
        self.assertEqual(standing.season_close_errors(root), [])
        self.assertEqual(standing.compute(root, "2004-08-01")["standing"], "unsigned_rookie")   # no 2004-05 folder: the latest one

    def test_signing_reads_the_sheet_and_replays_by_date(self):
        tmp, root = copy_repo()
        self.addCleanup(tmp.cleanup)
        with self.assertRaisesRegex(ValueError, "after the career clock"):
            standing.record(root, "2003-07-01", "manual")
        sign_wade(root)
        snap = standing.record(root, "2003-07-01", "manual")             # dated before the signing: the rule on that date
        self.assertEqual(snap["standing"], "unsigned_rookie")
        self.assertEqual(standing.compute(root, SIGN_DAY)["standing"], "rookie")
        self.assertEqual(standing.compute(root, SIGN_DAY)["basis"]["signed_date"], SIGN_DAY)
        self.assertEqual(standing.compute(root, "2003-07-01")["standing"], "unsigned_rookie")    # pure in the date
        self.assertIn("stale", " ".join(standing.standing_errors(root)))
        self.assertEqual(standing.standing_on(root, SIGN_DAY)["standing"], "unsigned_rookie")    # until a snapshot dates the change
        snap = standing.record(root, SIGN_DAY, "signing", "2003-04/01_Free_Agency/note.md")
        self.assertEqual((snap["standing"], snap["trigger"]), ("rookie", "signing"))
        self.assertEqual(standing.standing_errors(root), [])
        self.assertEqual(standing.standing_on(root, SIGN_DAY)["standing"], "rookie")
        self.assertIsNone(standing.record(root, SIGN_DAY, "manual"))                               # nothing changed: no new snapshot
        with self.assertRaisesRegex(ValueError, "before the last snapshot"):
            standing.record(root, "2003-07-10", "manual")
        with self.assertRaisesRegex(ValueError, "after the career clock"):
            standing.record(root, "2003-12-01", "manual")
        with self.assertRaisesRegex(ValueError, "unknown trigger"):
            standing.record(root, SIGN_DAY, "whim")
        # a manual write only dates a snapshot: its value is the rule's
        snaps = standing.load(root)["snapshots"]
        self.assertEqual([s["standing"] for s in snaps], ["unsigned_rookie", "rookie"])
        # contract_status disagreeing with the sheet on the career date is an error, not a value
        set_state(root, contract_status="draft_rights_unsigned")
        with self.assertRaisesRegex(ValueError, "contract_status disagrees"):
            standing.compute(root, SIGN_DAY)
        self.assertEqual(len(standing.standing_errors(root)), 1)
        self.assertIn("cannot compute", standing.standing_errors(root)[0])

    def test_snapshot_file_rules(self):
        tmp, root = copy_repo()
        self.addCleanup(tmp.cleanup)
        sign_wade(root)
        path = root / standing.STANDING_PATH
        self.assertIn("missing while the computed standing is rookie", " ".join(standing.standing_errors(root)))

        def write(snapshots):
            path.write_text(json.dumps({"schema_version": 1, "purpose": standing.PURPOSE, "snapshots": snapshots}))

        good = {"as_of": SIGN_DAY, "standing": "rookie", "trigger": "signing", "basis": standing.compute(root, SIGN_DAY)["basis"],
                "source": "2003-04/01_Free_Agency/note.md"}
        earlier = {"as_of": "2003-07-01", "standing": "unsigned_rookie", "trigger": "manual", "basis": standing.compute(root, "2003-07-01")["basis"],
                   "source": "standing.json (manual snapshot; the value is the rule's)"}
        write([earlier, good])
        self.assertEqual(standing.standing_errors(root), [])
        write([good, earlier])
        self.assertTrue(any("before the previous snapshot" in e for e in standing.standing_errors(root)))
        write([earlier, dict(good, as_of="2003-12-25")])
        self.assertTrue(any("after the career clock" in e for e in standing.standing_errors(root)))
        write([earlier, dict(good, standing="starter")])
        self.assertTrue(any("does not replay" in e for e in standing.standing_errors(root)))
        write([earlier, dict(good, trigger="rumour")])
        self.assertTrue(any("unknown trigger" in e for e in standing.standing_errors(root)))
        write([earlier, dict(good, source="2003-04/nowhere.json")])
        self.assertTrue(any("source must exist" in e for e in standing.standing_errors(root)))
        write([earlier])
        self.assertTrue(any("stale" in e for e in standing.standing_errors(root)))

    def test_closed_season_counts_closed_results_and_replays(self):
        tmp, root = copy_repo()
        self.addCleanup(tmp.cleanup)
        sign_wade(root)
        standing.record(root, SIGN_DAY, "signing", "2003-04/01_Free_Agency/note.md")
        played_game(root)
        set_state(root, current_date="2004-05-01")
        close_season(root)
        self.assertEqual(standing.season_close_errors(root), [])
        result = standing.compute(root, "2004-05-01")
        self.assertEqual(result["standing"], "rookie")                      # one appearance: below the starter line
        self.assertEqual(result["basis"]["closed_seasons"], ["2003-04"])
        line = result["basis"]["statistics"]["2003-04"]
        self.assertEqual((line["gp"], line["gs"], line["scheduled"], line["complete"]), (1, 1, 82, True))
        self.assertEqual(standing.compute(root, "2004-04-14")["basis"]["closed_seasons"], [])   # before the close date
        snap = standing.record(root, "2004-05-01", "season_close", "2003-04/season_close.json")
        self.assertEqual(snap["standing"], "rookie")
        self.assertEqual(standing.standing_errors(root), [])
        # the season-close record must agree with the games, the clock and the schedule
        close_season(root, close_date="2003-10-15")
        self.assertTrue(any("dated after close_date" in e for e in standing.season_close_errors(root)))
        close_season(root, scheduled=81)
        self.assertTrue(any("82 scheduled games" in e for e in standing.season_close_errors(root)))
        close_season(root, close_date="2004-06-01")
        self.assertTrue(any("on or before the career clock" in e for e in standing.season_close_errors(root)))
        close_season(root)
        # one malformed game note yields one error, not an abort
        note = root / PLAYER / "2003-04/06_Regular_Season/11_November/Week_1/Game_1.md"
        note.write_text(note.read_text().replace("result: W 100-90\n", ""))
        errors = standing.standing_errors(root)
        self.assertEqual(len(errors), 1, errors)

    def test_update_standing_script_is_idempotent(self):
        tmp, root = copy_repo()
        self.addCleanup(tmp.cleanup)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            update_standing.main(["update_standing.py", "--check", "2003-06-26"], root)
        self.assertEqual(json.loads(out.getvalue())["standing"], "unsigned_rookie")
        for _ in range(2):
            with contextlib.redirect_stdout(io.StringIO()):
                update_standing.main(["update_standing.py", "--write", "2003-06-26"], root)
        self.assertEqual(len(standing.load(root)["snapshots"]), 1)
        with self.assertRaises(ValueError):
            with contextlib.redirect_stdout(io.StringIO()):
                update_standing.main(["update_standing.py", "--write", "2003-07-01"], root)   # after the career clock
        self.assertEqual(standing.standing_errors(root), [])

    def test_one_weight_table(self):
        self.assertIs(front_office.STANDING_WEIGHT, standing.STANDING_WEIGHT)
        self.assertIs(gm.STANDING_WEIGHT, standing.STANDING_WEIGHT)
        self.assertEqual(set(standing.STANDING_WEIGHT), set(standing.CATEGORIES))


if __name__ == "__main__":
    unittest.main()
