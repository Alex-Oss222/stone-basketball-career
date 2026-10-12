"""The June 2006 audit of Wade's records (group D): the card's live season, the identity's role and availability, the
win/loss classification of a game without a box row, the inactive label, phase and draft notes, the current note,
uniform numbers and a followed player's row ages."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from tests import live_season
from runtime import jerseys
from runtime.career_stats import aggregate, attach_status, collect_games, identity_at, select

ROOT = Path(__file__).resolve().parents[1]
PLAYER = ROOT / "career/Dwyane_Wade"
IDENTITY = json.loads((PLAYER / "professional_identity.json").read_text(encoding="utf-8"))


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text if isinstance(text, str) else json.dumps(text), encoding="utf-8")
    return path


def front_matter(path):
    head = path.read_text(encoding="utf-8").split("---\n", 2)[1]
    return dict(line.split(": ", 1) for line in head.splitlines() if ": " in line)


class CardSeasonTests(unittest.TestCase):
    def test_a_season_folder_without_a_current_state_is_not_a_card_season(self):
        from runtime.player_cards import player_cards_data
        with tempfile.TemporaryDirectory() as tmp:
            player = Path(tmp) / "career/Dwyane_Wade"
            write(player / "2003-04/current_state.json", {"current_date": "2004-06-20"})
            write(player / "2004-05/wade_expected_profile.json", {})      # the season close writes the next folder early
            data = player_cards_data(player, deepcopy(IDENTITY), [], [], "2004-06-20")
        self.assertEqual(data["default_period"], "regular-2003-04-season")
        self.assertEqual(data["awards"]["default_scenario"], "2003-04")
        self.assertEqual({p["season"] for p in data["periods"]}, {"2003-04"})


class IdentityTests(unittest.TestCase):
    identity = attach_status(deepcopy(IDENTITY), PLAYER)

    def role(self, day):
        return identity_at(self.identity, day)["role"]

    def test_the_role_follows_the_staff_review_in_force(self):
        self.assertEqual(self.role("2004-11-24"), "Starting SG; staff plan 34 minutes")
        self.assertEqual(self.role("2004-11-25"), "Starting SG; staff plan 38.76 minutes")
        self.assertEqual(self.role("2005-07-01"), "Starting SG; staff plan 39.04 minutes")    # the 2005 summer
        self.assertEqual(self.role("2005-11-09"), "Starting SG; staff plan 40 minutes")
        self.assertEqual(self.role("2006-06-20"), "Starting SG; staff plan 40 minutes")

    def test_a_snapshot_that_sets_a_role_stands_until_the_next_review(self):
        self.assertEqual(self.role("2003-11-06"), "Rotation; staff plan 20 minutes")         # camp
        self.assertEqual(self.role("2004-10-01"), self.identity["snapshots"][6]["role"])     # the rollover's carried-over role
        self.assertEqual(self.role("2005-10-27"), "Starting SG; staff plan 34 minutes")      # the 2005-06 camp
        self.assertEqual(self.role("2003-12-02"), "Starting SG; staff plan 34 minutes")      # a copied snapshot sets nothing

    def test_without_derived_records_the_snapshot_stands(self):
        self.assertEqual(identity_at(IDENTITY, "2005-11-09")["role"], "Starting SG; staff plan 34 minutes")

    def test_the_trade_update_reads_the_staff_role_in_force(self):
        from runtime.player_milestones import build_milestone_payload
        with live_season():
            payload = build_milestone_payload(PLAYER, deepcopy(IDENTITY), collect_games(PLAYER, IDENTITY, "2006-06-20"), root=ROOT)
        screens = {s["id"]: s for s in payload["screens"]}
        rows = next(s for s in screens["trade_update"]["sections"] if s["title"] == "What this changes for you")["rows"]
        self.assertEqual(dict((r[0], r[1]) for r in rows)["Staff role after a move"], "Starting SG; staff plan 40 minutes")

    def test_availability_reads_the_dated_injured_list(self):
        on_list = identity_at(self.identity, "2004-12-25")["availability"]
        self.assertTrue(on_list.startswith("Injured list since 2004-12-23: Fractured tibia"), on_list)
        self.assertIn("since 2004-02-23", identity_at(self.identity, "2004-03-05")["availability"])
        self.assertEqual(identity_at(self.identity, "2004-03-06")["availability"], IDENTITY["snapshots"][-1]["availability"])
        self.assertNotIn("Injured", identity_at(self.identity, "2006-06-20")["availability"])


class GameRecordTests(unittest.TestCase):
    records = collect_games(PLAYER, IDENTITY, "2006-06-20")

    def test_a_game_without_his_box_row_is_still_a_win_or_a_loss(self):
        missing = [r for r in self.records if r["coverage"] == "missing_box"]
        self.assertEqual(len(missing), 5)
        self.assertTrue(all(r["win"] is False for r in missing))
        losses = [r for r in select(self.records, competition="preseason", season="2003-04") if r.get("win") is False]
        self.assertIsNone(aggregate(losses)["gp"])                  # the Losses split reads N/A, never G = 0

    def test_an_inactive_game_names_the_results_absence_kind(self):
        game = next(r for r in self.records if r["date"] == "2004-11-23")
        self.assertEqual(game["appearance"], "DNP: inactive (illness or personal)")


class NoteTests(unittest.TestCase):
    def test_the_draft_closes_its_phase_note(self):
        from runtime.draft import phase_note
        record = json.loads((PLAYER / "2004-05/09_Draft/draft_2005.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            note = write(Path(tmp) / "09_Draft/note.md", "---\ntype: phase\nstatus: not_started\nthrough: 2003-06-26\n---\n\n"
                                                         "# Draft\n\n## Player decisions\n\nNone.\n\n## Consequences\n")
            phase_note(tmp, record, Path("09_Draft"), "draft_2005.json")
            phase_note(tmp, record, Path("09_Draft"), "draft_2005.json")
            text, meta = note.read_text(encoding="utf-8"), front_matter(note)
        self.assertEqual((meta["status"], meta["through"]), ("complete", "2005-06-28"))
        self.assertEqual(text.count("- 2005-06-28: The 2005 NBA Draft was held"), 1)
        self.assertIn("## Events\n- 2005-06-28:", text)
        self.assertIn("Miami selected Uroš Slokar (F) at No. 58 (round 2).", text)

    def test_the_recorded_drafts_and_closed_phases(self):
        for season in ("2003-04", "2004-05"):
            for folder in ("01_Free_Agency", "02_Summer_League", "03_Offseason", "04_Training_Camp", "05_Preseason", "09_Draft"):
                self.assertEqual(front_matter(PLAYER / season / folder / "note.md")["status"], "complete", f"{season}/{folder}")
        self.assertEqual(front_matter(PLAYER / "2005-06/04_Training_Camp/note.md")["status"], "complete")
        self.assertIn("Dorell Wright (SF) at No. 23", (PLAYER / "2003-04/09_Draft/note.md").read_text(encoding="utf-8"))
        self.assertIn("Uroš Slokar (F) at No. 58", (PLAYER / "2004-05/09_Draft/note.md").read_text(encoding="utf-8"))
        for season in ("2004-05", "2005-06"):
            state = json.loads((PLAYER / season / "current_state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["current_note"], "06_Regular_Season/04_April/Week_3/note.md")

    def test_opening_night_moves_the_area_and_the_note_and_closes_the_phases(self):
        from runtime.seasons import path as season_path
        from runtime.write_back import sync_note_statuses
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            player = root / "career/Dwyane_Wade"
            write(root / season_path("2005-06", "schedule"), {"games": [{"date": "2005-11-01"}, {"date": "2006-04-19"}]})
            write(player / "2004-05/current_state.json", {"current_date": "2005-10-01"})
            old = write(player / "2004-05/04_Training_Camp/note.md", "---\ntype: phase\nstatus: active\n---\n\n# Camp\n")
            write(player / "2005-06/current_state.json", {"current_date": "2005-11-03", "current_area": "04_Training_Camp",
                                                          "current_note": "04_Training_Camp/note.md"})
            camp = write(player / "2005-06/04_Training_Camp/note.md", "---\ntype: phase\nstatus: active\n---\n\n# Camp\n")
            draft = write(player / "2005-06/09_Draft/note.md", "---\ntype: phase\nstatus: not_started\n---\n\n# Draft\n")
            week = write(player / "2005-06/06_Regular_Season/11_November/Week_1/note.md",
                         "---\ntype: regular_season_week\nstatus: not_started\n---\n\n# Week\n")
            sync_note_statuses(root, "2005-06")
            state = json.loads((player / "2005-06/current_state.json").read_text(encoding="utf-8"))
            self.assertEqual((state["current_area"], state["current_note"]),
                             ("06_Regular_Season", "06_Regular_Season/11_November/Week_1/note.md"))
            self.assertEqual([front_matter(p)["status"] for p in (week, camp, old, draft)],
                             ["active", "complete", "complete", "not_started"])
            self.assertEqual(sync_note_statuses(root, "2005-06", write=False), [])


class JerseyTests(unittest.TestCase):
    def test_wades_settled_number_stays_his(self):
        self.assertEqual(jerseys.wade_number(ROOT, "2005-06"), ("3", jerseys.CHOICE_NAME))
        numbers = jerseys.miami_numbers(ROOT, "2005-06")
        self.assertEqual(numbers["Dwyane Wade"], "3")
        held = [n for n in numbers.values() if n]
        self.assertEqual(len(held), len(set(held)))

    def test_a_continuing_player_keeps_his_miami_number(self):
        before, after = jerseys.miami_numbers(ROOT, "2004-05"), jerseys.miami_numbers(ROOT, "2005-06")
        for name in ("Caron Butler", "Donyell Marshall", "Mike James"):
            self.assertEqual(after[name], before[name], name)
        self.assertEqual(before["Brian Grant"], jerseys.miami_numbers(ROOT, "2003-04")["Brian Grant"])

    def test_continuity_flags_a_register_without_wades_number(self):
        from runtime.continuity import number_errors
        with mock.patch("runtime.jerseys.miami_numbers", return_value={"Dwyane Wade": None, "Caron Butler": "3"}):
            errors = number_errors(ROOT, "2005-06", "2006-06-20")
        self.assertTrue(any("Wade has no number" in e for e in errors), errors)
        with live_season():
            self.assertEqual(number_errors(ROOT, "2005-06", "2006-06-20"), [])

    def test_no_club_shows_a_number_twice(self):
        from runtime.club_truth import rosters_on
        with live_season():
            clubs = sorted(set(rosters_on("2006-06-20", ROOT).values()))
            for club in clubs:
                numbers = jerseys.club_numbers(club, "2006-06-20", ROOT)
                self.assertEqual(len(set(numbers.values())), len(numbers), club)
            self.assertEqual(jerseys.number_for("jamesle01", "Cleveland Cavaliers", ROOT), "23")
            self.assertNotEqual(jerseys.number_for("milesda01", "Cleveland Cavaliers", ROOT), "23")
            # a registry id that is not the NBA id reads the NBA id's number
            self.assertEqual(jerseys.number_for("sebastiantelfair", "Miami Heat", ROOT), jerseys.miami_numbers(ROOT)["Sebastian Telfair"])
            self.assertEqual(jerseys.number_for("andreiguodala", "New York Knicks", ROOT), jerseys.number_for("iguodan01", "New York Knicks", ROOT))
            # held off the roster (out for the season under contract): a number still free at his club
            self.assertNotEqual(jerseys.number_for("jacobca01", "Phoenix Suns", ROOT), jerseys.number_for("stoudam01", "Phoenix Suns", ROOT))


class FollowedAgeTests(unittest.TestCase):
    def test_bosh_rows_use_their_own_cutoff_ages(self):
        from runtime.followed_players import build
        with live_season():
            text = build(ROOT, "2006-06-20")[ROOT / "career/Chris_Bosh/README.md"]
        rows = [line.split(" | ")[:2] for line in text.splitlines() if line.startswith(("| [200", "| 200"))][:6]
        self.assertEqual([r[1] for r in rows], ["20", "21", "22", "20", "21", "22"])


if __name__ == "__main__":
    unittest.main()
