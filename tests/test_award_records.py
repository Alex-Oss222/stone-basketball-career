"""Award record fixes from the 2005-12 award audit.

1. All-Star recording dates (`runtime/all_star.py`): a later step's rebuild of `all_stars` never re-dates an entry (the
   2004-05 replacements step on 2005-02-18 had stamped all 24 starters and reserves); each entry carries its own step's
   closing date only when that step closed after its date, as Wade's entry in `awards.json` does; `repair_recorded_on`
   restores records written before the rule.
2. Registry positions (`runtime/write_back.py`): a new registry row takes its position from the season's roster, the
   opening book, Miami's register, a draft class or an expiring-contracts list, never the old "SF" placeholder; a row no
   source records keeps a page slot marked unknown; `repair_positions` fills the placeholders and moves each changed row
   between position groups on the league statistics pages; the All-Star pool gives an unknown position only the
   any-position slots.
3. Player report pages (`runtime/player_reports.py`) keep no hand-written awards section: the 2003-04 pages' "No NBA
   awards recorded for this period" and all-"Not awarded" register contradicted `awards.json`.

Live checks read the repository and change nothing.
"""
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from runtime import all_star as A
from runtime import write_back as W

ROOT = Path(__file__).resolve().parents[1]
PLAYER = ROOT / "career/Dwyane_Wade"
LEAGUE = PLAYER / "Stats_and_Awards/League"


def put(root, rel, data):
    path = Path(root) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data if isinstance(data, str) else json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


# -- 1. All-Star recording dates ---------------------------------------------------------------------------------
def row(player, team="Club", pos="G"):
    return {"player": player, "bbr_id": player.lower()[:7] + "01", "team": team, "position": pos, "games": 40, "club_games": 45,
            "pts": 20.0, "reb": 5.0, "ast": 5.0, "game_score": 15.0, "club_pct": 0.6, "ballots": 10}


DATES = {"starters_announced": "2005-02-03", "coach_record_through": "2005-02-06", "reserves_announced": "2005-02-08",
         "rookie_challenge_announced": "2005-01-27", "replacements_named": "2005-02-18"}


def steps_stub():
    """The step functions replaced by fixed outcomes: the record logic is what is tested, not the ballots."""
    def starters(root, c, day, rows):
        return {"step": "starters", "announced_on": day, "conferences": {
            "East": {"starters": [row("Kidd East"), row("Star East")]}, "West": {"starters": [row("Star West")]}}}

    def coaches(root, c, day, rows):
        return {"step": "coaches", "announced_on": day, "conferences": {}}, None

    def reserves(root, c, day, rows, record):
        order = [{"player": "Spare East", "position": "G", "team": "Club", "ballots": 3}]
        return {"step": "reserves", "announced_on": day, "conferences": {
            "East": {"reserves": [row("Dwyane Wade", "Miami Heat")], "coach_order": order},
            "West": {"reserves": [row("Bench West")], "coach_order": []}}}

    def rookie_challenge(root, c, day, rows):
        return {"step": "rookie_challenge", "announced_on": day, "teams": {}}

    def replacements(root, c, day, rows, record):
        return {"step": "replacements", "announced_on": day, "evidence_through": day, "conferences": {"East": [
            {"out": "Kidd East", "out_team": "Club", "role": "starter", "reason": "injured", "replacement": "Spare East",
             "replacement_team": "Club", "position": "G"}], "West": []}}
    return dict(starters=starters, game_coaches=coaches, reserves=reserves, rookie_challenge=rookie_challenge,
                replacements=replacements)


class AllStarRecordingTests(unittest.TestCase):
    def run_decide(self, root, clocks):
        c = SimpleNamespace(season="2004-05", calendar=Path("cal.json"), data={"dates": {k: {"value": v} for k, v in DATES.items()}},
                              record=A.PLAYER / "Stats_and_Awards/League/2004-05/all_star.json",
                              page=A.PLAYER / "Stats_and_Awards/League/2004-05/All_Star.md", draws=Path("draws"))
        put(root, A.PLAYER / "awards.json", {"schema_version": 1, "awards": []})
        stubs = {k: mock.patch.object(A, k, v) for k, v in steps_stub().items()}
        with mock.patch.object(A, "ctx", lambda root=None, season=None: c), \
                mock.patch.object(A, "page", lambda record, clock, c: ""), \
                mock.patch.object(A, "pool", lambda *a, **k: {}), \
                mock.patch("runtime.write_back.closed_results", lambda *a, **k: []), \
                mock.patch("runtime.seasons.dates", lambda *a, **k: {"regular_season_end": "2005-04-20", "opening_night": "2004-11-02"}), \
                mock.patch("runtime.standing.record", lambda *a, **k: None):
            for s in stubs.values():
                s.start()
            try:
                for clock in clocks:
                    A.decide(root, clock)
            finally:
                for s in stubs.values():
                    s.stop()
        return (json.loads((Path(root) / c.record).read_text()),
                json.loads((Path(root) / A.PLAYER / "awards.json").read_text())["awards"])

    def test_steps_closed_on_their_dates_leave_no_recording_date(self):
        with tempfile.TemporaryDirectory() as root:
            record, awards = self.run_decide(root, ["2005-01-27", "2005-02-03", "2005-02-07", "2005-02-08", "2005-02-18"])
        self.assertEqual(len(record["all_stars"]), 6)                     # 3 starters, 2 reserves, 1 replacement
        self.assertFalse([a for a in record["all_stars"] if "recorded_on" in a])
        self.assertFalse([s for s in record["steps"] if "recorded_on" in s])
        self.assertEqual(A.recorded_on_errors(record), [])
        wade = next(a for a in awards if a["id"] == "2004-05-all-star")
        self.assertNotIn("recorded_on", wade)

    def test_a_later_step_never_redates_an_earlier_entry(self):
        with tempfile.TemporaryDirectory() as root:
            # The starters closed late on the reserves' day: they carry it; the replacements' day touches no one.
            record, _ = self.run_decide(root, ["2005-01-27", "2005-02-08", "2005-02-18"])
        by = {a["player"]: a for a in record["all_stars"]}
        self.assertEqual(by["Star East"]["recorded_on"], "2005-02-08")
        self.assertNotIn("recorded_on", by["Dwyane Wade"])                # the reserves closed on their own date
        self.assertNotIn("recorded_on", by["Spare East"])
        steps = {s["step"]: s for s in record["steps"]}
        self.assertEqual((steps["starters"]["recorded_on"], steps["coaches"]["recorded_on"]), ("2005-02-08", "2005-02-08"))
        self.assertNotIn("recorded_on", steps["replacements"])
        self.assertEqual(A.recorded_on_errors(record), [])

    def test_a_late_last_step_never_reads_as_a_record_closed_late_in_one_run(self):
        # Under the rule a late step's date on its own entries is no legacy mark: the steps closed on time stay undated,
        # validation passes and the repair changes nothing (review: the inference had re-dated them to the late day).
        for clocks, late_role, day in ((["2005-01-27", "2005-02-03", "2005-02-07", "2005-02-10"], "reserve", "2005-02-10"),
                                       (["2005-01-27", "2005-02-03", "2005-02-07", "2005-02-08", "2005-02-20"],
                                        "injury replacement", "2005-02-20")):
            with self.subTest(late=late_role), tempfile.TemporaryDirectory() as root:
                record, awards = self.run_decide(root, clocks)
                self.assertEqual({a["player"]: a.get("recorded_on") for a in record["all_stars"] if a.get("recorded_on")},
                                 {a["player"]: day for a in record["all_stars"] if a["role"] == late_role})
                closed = A.decision_dates(record)
                self.assertEqual(closed["starters"], "2005-02-03")
                self.assertEqual(closed[A.ROLE_STEP[late_role]], day)
                self.assertEqual(A.recorded_on_errors(record), [])
                self.assertEqual(A.repair_recorded_on(root, write=False), [])
                wade = next(a for a in awards if a["id"] == "2004-05-all-star")
                self.assertEqual(wade.get("recorded_on"), day if late_role == "reserve" else None)

    def test_a_season_decided_after_the_fact_carries_the_day_it_was_closed(self):
        with tempfile.TemporaryDirectory() as root:
            record, awards = self.run_decide(root, ["2005-06-24"])
        self.assertEqual({a.get("recorded_on") for a in record["all_stars"]}, {"2005-06-24"})
        self.assertEqual({s.get("recorded_on") for s in record["steps"]}, {"2005-06-24"})
        self.assertEqual(next(a for a in awards if a["id"] == "2004-05-all-star")["recorded_on"], "2005-06-24")

    def test_keep_recorded_keeps_the_recorded_entry(self):
        old = [{"player": "P", "bbr_id": None, "team": "Old", "conference": "East", "role": "starter", "selected_on": "2005-02-03"}]
        built = [dict(old[0], team="New", bbr_id="pp01"),
                 {"player": "Q", "bbr_id": None, "team": "T", "conference": "East", "role": "injury replacement",
                  "selected_on": "2005-02-18", "replacing": "P"}]
        steps = {"starters": {"announced_on": "2005-02-03"}, "replacements": {"announced_on": "2005-02-18", "recorded_on": "2005-03-01"}}
        kept = A.keep_recorded(old, built, steps)
        self.assertIs(kept[0], old[0])
        self.assertEqual(kept[1]["recorded_on"], "2005-03-01")

    def test_decision_dates_read_a_record_written_before_the_rule(self):
        steps = [{"step": s, "announced_on": d} for s, d in (("starters", "2005-02-03"), ("reserves", "2005-02-08"),
                                                             ("replacements", "2005-02-18"))]
        entry = lambda role, day, mark=None: dict({"player": role + day, "conference": "East", "role": role, "selected_on": day},
                                                  **({"recorded_on": mark} if mark else {}))
        overwritten = {"steps": steps, "all_stars": [entry("starter", "2005-02-03", "2005-02-18"),
                                                     entry("reserve", "2005-02-08", "2005-02-18"), entry("injury replacement", "2005-02-18")]}
        self.assertEqual(A.decision_dates(overwritten), {"starters": "2005-02-03", "reserves": "2005-02-08", "replacements": "2005-02-18"})
        self.assertEqual(len(A.recorded_on_errors(overwritten)), 2)
        late = {"steps": steps, "all_stars": [entry("starter", "2005-02-03", "2005-06-24"), entry("reserve", "2005-02-08", "2005-06-24")]}
        self.assertEqual(set(A.decision_dates(late).values()), {"2005-06-24"})
        self.assertEqual(A.recorded_on_errors(late), [])
        self.assertEqual(A.decision_dates(overwritten, {"starters": "2005-02-05"})["starters"], "2005-02-05")

    def test_repair_restores_each_entry_to_its_own_step(self):
        steps = [{"step": s, "announced_on": d} for s, d in (("starters", "2005-02-03"), ("reserves", "2005-02-08"),
                                                             ("replacements", "2005-02-18"))]
        overwritten = {"steps": steps, "all_stars": [
            {"player": "S", "conference": "East", "role": "starter", "selected_on": "2005-02-03", "recorded_on": "2005-02-18"},
            {"player": "R", "conference": "West", "role": "reserve", "selected_on": "2005-02-08", "recorded_on": "2005-02-18"},
            {"player": "I", "conference": "East", "role": "injury replacement", "selected_on": "2005-02-18", "replacing": "S"}]}
        late = {"steps": [dict(s, announced_on=s["announced_on"].replace("2005", "2004")) for s in steps], "all_stars": [
            {"player": "S", "conference": "East", "role": "starter", "selected_on": "2004-02-03", "recorded_on": "2004-06-24"}]}
        with tempfile.TemporaryDirectory() as root:
            put(root, A.PLAYER / "Stats_and_Awards/League/2004-05/all_star.json", overwritten)
            put(root, A.PLAYER / "Stats_and_Awards/League/2003-04/all_star.json", late)
            dry = A.repair_recorded_on(root, write=False)
            self.assertEqual(json.loads((Path(root) / A.PLAYER / "Stats_and_Awards/League/2004-05/all_star.json").read_text()), overwritten)
            self.assertEqual(A.repair_recorded_on(root), dry)
            self.assertEqual(dry, [("2004-05", "S", "starter", "2005-02-18", None), ("2004-05", "R", "reserve", "2005-02-18", None)])
            fixed = json.loads((Path(root) / A.PLAYER / "Stats_and_Awards/League/2004-05/all_star.json").read_text())
            self.assertEqual(fixed["steps"], steps)                         # metadata of the entries only
            self.assertEqual([a.get("recorded_on") for a in fixed["all_stars"]], [None, None, None])
            self.assertEqual(json.loads((Path(root) / A.PLAYER / "Stats_and_Awards/League/2003-04/all_star.json").read_text()), late)
            self.assertEqual(A.repair_recorded_on(root), [])

    def test_live_records_agree_with_awards_json_once_repaired(self):
        awards = {a["id"]: a for a in json.loads((PLAYER / "awards.json").read_text())["awards"]}
        for path in sorted(LEAGUE.glob("*/all_star.json")):
            record = json.loads(path.read_text())
            closed = A.decision_dates(record)
            for a in record.get("all_stars", []):                        # the repair, in memory
                a.pop("recorded_on", None)
                if A._wanted(a, closed):
                    a["recorded_on"] = A._wanted(a, closed)
            self.assertEqual(A.recorded_on_errors(record), [], path)
            for a in record.get("all_stars", []):
                if a["player"] == A.WADE:
                    self.assertEqual(a.get("recorded_on"), awards[f"{path.parent.name}-all-star"].get("recorded_on"), path)
            if path.parent.name == "2003-04":                             # decided after the fact on 2004-06-24
                self.assertEqual({a.get("recorded_on") for a in record["all_stars"]}, {"2004-06-24"})
            if path.parent.name == "2004-05":                             # each step closed on its own date
                self.assertEqual({a.get("recorded_on") for a in record["all_stars"]}, {None})

    def test_an_unknown_position_fills_only_the_any_slots(self):
        scored = [("x", 3, 0), ("g1", 2, 0), ("g2", 1, 0)]
        positions = {"x": A.UNKNOWN, "g1": "G", "g2": "G"}
        self.assertEqual(A._ballot(scored, 0.0, {"G": 1, "any": 1}, positions), ["g1", "x"])
        self.assertEqual(A._ballot(scored, 0.0, {"G": 1, "F": 1}, positions), ["g1"])


# -- 2. Registry positions ---------------------------------------------------------------------------------------
REG = W.PLAYER_DIR / "Stats_and_Awards/League/player_registry.json"
COLUMNS = ["Player", "Age", "Club / rights", "Lg", "Pos", "G", "PTS"]


def roster(pid, bbr, pos, minutes=1000):
    return {"player_id": pid, "bbr_id": bbr, "position": pos, "games": 50, "minutes": minutes}


def reg_row(name, bbr, pos="SF", cohort=W.APPEARANCE_COHORT, season="2004-05", rid=None, **extra):
    return dict({"name": name, "position": pos, "team_name": "Chicago Bulls", "team_code": "CHI", "conference": "East",
                 "cohort": cohort, "bbr_id": bbr, "espn_id": None, "birth_date": "1983-01-01",
                 "registry_id": rid or bbr, "added_on": "2004-11-03",
                 "added_basis": f"first closed {season} appearance, Chicago Bulls, test"}, **extra)


def stats_page(groups):
    """A League_Stats.md with one table per position group: {pos: [(registry id, name, pos cell, points)]}."""
    parts = ["# League statistics\n\n## Players by position\n"]
    for pos in W.REGISTRY_POSITIONS:
        parts.append(f"<details>\n<summary>{pos} · group · 0 players</summary>\n\n### {pos}: per game\n\n"
                     "| " + " | ".join(COLUMNS) + " |\n|" + " --- |" * len(COLUMNS) + "\n"
                     + "".join(f"| [{n}](../Players/{rid}.md) | 21 | CHI | NBA | {cell} | 82 | {pts} |\n" for rid, n, cell, pts in groups.get(pos, []))
                     + "\n</details>\n")
    return "\n".join(parts)


def library(root):
    put(root, "library/2004/league/nba_2004_05_team_rosters.json", {"season": "2004-05", "clubs": {
        "Chicago Bulls": {"players": [roster("Ben Gordon", "gordobe01", "SG"), roster("Luol Deng", "denglu01", "SF"),
                                      roster("Tyson Chandler", "chandty01", "C")]},
        "Orlando Magic": {"players": [roster("Jackson Vroman", "vromaja01", "PF", 57)]},
        "New Orleans Hornets": {"players": [roster("Jackson Vroman", "vromaja01", "C", 648)]}}})
    put(root, "library/2005/league/nba_2005_06_team_rosters.json", {"season": "2005-06", "clubs": {
        "Chicago Bulls": {"players": [roster("Ben Gordon", "gordobe01", "PG"), roster("Future Rookie", "futurro01", "C")]}}})
    put(root, "library/2004/league/nba_2004_draft_class.json", {"picks": [
        {"player": "Draft Only", "bbr_id": "draftor01", "position": "C/PF"},
        {"player": "Generic Guard", "bbr_id": "genergu01", "position": "G"}]})


class RegistryPositionTests(unittest.TestCase):
    def test_a_source_label_becomes_a_registry_position_or_nothing(self):
        self.assertEqual([W._slot(x) for x in ("SG-SF", "C/PF", "F/C", "pg", "G", "G/F", "", None)],
                         ["SG", "C", "F", "PG", None, None, None, None])

    def test_the_season_roster_answers_first_then_draft_classes_never_a_later_season(self):
        with tempfile.TemporaryDirectory() as root:
            library(root)
            sources = W.position_sources(root, "2004-05", through="2004-05")
            self.assertEqual(sources[0][0], "library/2004/league/nba_2004_05_team_rosters.json")
            self.assertNotIn("library/2005/league/nba_2005_06_team_rosters.json", [s[0] for s in sources])
            self.assertEqual(W.registry_position(sources, "gordobe01", "Ben Gordon", "Chicago Bulls")[0], "SG")
            self.assertEqual(W.registry_position(sources, None, "Ben Gordon", "Chicago Bulls")[0], "SG")   # by name
            self.assertEqual(W.registry_position(sources, "vromaja01", "Jackson Vroman", "Orlando Magic")[0], "PF")
            self.assertEqual(W.registry_position(sources, "vromaja01", "Jackson Vroman", "Milwaukee Bucks")[0], "C")  # longest stint
            self.assertEqual(W.registry_position(sources, "draftor01", "Draft Only", "Chicago Bulls"),
                             ("C", "library/2004/league/nba_2004_draft_class.json"))
            self.assertEqual(W.registry_position(sources, "genergu01", "Generic Guard"), (None, None))
            self.assertEqual(W.registry_position(sources, "futurro01", "Future Rookie"), (None, None))
            later = W.position_sources(root, "2005-06", through="2005-06")
            self.assertEqual(W.registry_position(later, "gordobe01", "Ben Gordon", "Chicago Bulls")[0], "PG")

    def test_a_new_row_takes_a_sourced_position_or_is_marked_unknown(self):
        with tempfile.TemporaryDirectory() as root:
            library(root)
            put(root, REG, {"positions": list(W.REGISTRY_POSITIONS), "players": []})
            result = {"event_id": "g1", "game_date": "2004-11-03", "home": "Chicago Bulls", "away": "Orlando Magic"}
            rows = [{"result": result, "request": None, "note": None}]
            records = [("home", "Ben Gordon", None, {}), ("home", "Nobody Known", None, {})]
            with mock.patch.object(W, "closed_results", lambda *a, **k: rows), \
                    mock.patch.object(W, "game_records", lambda *a, **k: records):
                added = {p["name"]: p for p in W.registry_additions(root, "2004-05")}
        self.assertEqual((added["Ben Gordon"]["position"], added["Ben Gordon"]["position_basis"]),
                         ("SG", "library/2004/league/nba_2004_05_team_rosters.json"))
        self.assertEqual(added["Ben Gordon"]["bbr_id"], "gordobe01")
        self.assertEqual((added["Nobody Known"]["position"], added["Nobody Known"]["position_basis"]), (W.UNKNOWN_SLOT, W.UNKNOWN_BASIS))
        self.assertIsNone(W.known_position(added["Nobody Known"]))
        self.assertEqual(W.known_position(added["Ben Gordon"]), "SG")

    def test_a_market_signing_takes_the_expiring_list_position(self):
        # Review: the expiring-contracts list is the researched position the market reads for an unsigned player
        # (`league_market._role_from_stats`); his registry row takes it, dated 2002-03, behind a nearer season's roster.
        with tempfile.TemporaryDirectory() as root:
            library(root)
            put(root, "library/2003/league/nba_2003_expiring_contracts.json", {"season": "2003", "players": [
                {"player_id": "Free Agent", "bbr_id": "freeag01", "position": "PF", "former_club": "Boston Celtics"},
                {"player_id": "Luol Deng", "bbr_id": "denglu01", "position": "PF", "former_club": "Chicago Bulls"}]})
            put(root, W.season_base("2004-05") / "League/league_moves.json", {"entries": [
                {"to": "Chicago Bulls", "player": "Free Agent", "bbr_id": "freeag01", "role": {"position": "SF"}}]})
            put(root, REG, {"positions": list(W.REGISTRY_POSITIONS), "players": []})
            result = {"event_id": "g1", "game_date": "2004-11-03", "home": "Chicago Bulls", "away": "Orlando Magic"}
            rows = [{"result": result, "request": None, "note": None}]
            with mock.patch.object(W, "closed_results", lambda *a, **k: rows), \
                    mock.patch.object(W, "game_records", lambda *a, **k: [("home", "Free Agent", None, {})]):
                added = W.registry_additions(root, "2004-05")
            later = W.position_sources(root, "2005-06", through="2005-06")
        self.assertEqual([(p["bbr_id"], p["position"], p["position_basis"]) for p in added],
                         [("freeag01", "PF", "library/2003/league/nba_2003_expiring_contracts.json")])
        self.assertEqual(W.registry_position(later, "denglu01", "Luol Deng")[0], "SF")    # 2004-05 roster, nearer

    def test_repair_fills_placeholders_and_moves_their_page_rows(self):
        players = [reg_row("Ben Gordon", "gordobe01", rid="bengordon"), reg_row("Luol Deng", "denglu01", rid="luoldeng"),
                   reg_row("Nobody Known", "nobodkn01"), reg_row("Tyson Chandler", "chandty01", pos="PF"),
                   reg_row("Original Gordon", "gordobe01", cohort="end_2002_03_roster", rid="origgo01")]
        page = stats_page({"SF": [("bengordon", "Ben Gordon", "SF", 1500), ("luoldeng", "Luol Deng", "SF", 900),
                                  ("nobodkn01", "Nobody Known", "SF", 10), ("origgo01", "Original Gordon", "SF", 5)],
                           "SG": [("other01", "Other Guard", "SG", 700)], "PF": [("chandty01", "Tyson Chandler", "PF", 400)]})
        with tempfile.TemporaryDirectory() as root:
            library(root)
            put(root, REG, {"positions": list(W.REGISTRY_POSITIONS), "players": players})
            pages = [put(root, W.PLAYER_DIR / f"Stats_and_Awards/League/{rel}/League_Stats.md", page) for rel in ("2004-05", "2003-04/11_November")]
            self.assertEqual(W.repair_positions(root, write=False)[0][:4], ("bengordon", "Ben Gordon", "SF", "SG"))
            self.assertEqual(pages[0].read_text(), page)
            changed = W.repair_positions(root)
            self.assertEqual(changed, [("bengordon", "Ben Gordon", "SF", "SG", "library/2004/league/nba_2004_05_team_rosters.json"),
                                       ("nobodkn01", "Nobody Known", "SF", "SF", W.UNKNOWN_BASIS)])
            reg = {p["registry_id"]: p for p in json.loads((Path(root) / REG).read_text())["players"]}
            self.assertEqual((reg["bengordon"]["position"], reg["luoldeng"]["position"], reg["chandty01"]["position"],
                              reg["origgo01"]["position"]), ("SG", "SF", "PF", "SF"))
            self.assertNotIn("position_basis", reg["luoldeng"])                  # a sourced SF was right
            self.assertEqual(reg["nobodkn01"]["position_basis"], W.UNKNOWN_BASIS)
            for path in pages:
                text = path.read_text()
                sg = text.split("<summary>SG ·", 1)[1].split("</details>", 1)[0]
                sf = text.split("<summary>SF ·", 1)[1].split("</details>", 1)[0]
                self.assertIn("| [Ben Gordon](../Players/bengordon.md) | 21 | CHI | NBA | SG | 82 | 1500 |", sg)
                self.assertTrue(sg.index("Other Guard") < sg.index("Ben Gordon"))   # joins the end of the group
                self.assertNotIn("Ben Gordon", sf)
                self.assertIn("Nobody Known", sf)
                self.assertEqual(sorted(text.replace("| SG | 82 | 1500", "| SF | 82 | 1500").split("\n")), sorted(page.split("\n")))
            self.assertEqual(W.repair_positions(root), [])                       # idempotent

    def test_repair_registry_includes_the_positions(self):
        with tempfile.TemporaryDirectory() as root:
            library(root)
            put(root, REG, {"positions": list(W.REGISTRY_POSITIONS), "players": [reg_row("Ben Gordon", "gordobe01", rid="bengordon")]})
            put(root, W.PLAYER_DIR / "Stats_and_Awards/League/2004-05/League_Stats.md",
                stats_page({"SF": [("bengordon", "Ben Gordon", "SF", 1500)]}))
            self.assertEqual(W.repair_registry(root), ["bengordon"])
            self.assertEqual(json.loads((Path(root) / REG).read_text())["players"][0]["position"], "SG")

    def test_live_registry_placeholders_resolve_once(self):
        reg = json.loads((ROOT / REG).read_text())
        first = copy.deepcopy(reg)
        W._fill_positions(ROOT, first)
        self.assertEqual(W._fill_positions(ROOT, copy.deepcopy(first)), [])
        by = {p["name"]: p for p in first["players"]}
        expected = {"Ben Gordon": "SG", "J.R. Smith": "SG", "Jameer Nelson": "PG", "David Harrison": "C", "Emeka Okafor": "PF",
                    "Devin Harris": "PG", "Robert Swift": "C", "Shaun Livingston": "PG"}
        for name, pos in expected.items():
            if name in by:
                self.assertEqual(by[name]["position"], pos, name)
        self.assertTrue(all(p["position"] in W.REGISTRY_POSITIONS for p in first["players"]))
        originals = [p for p in first["players"] if p.get("cohort") != W.APPEARANCE_COHORT]
        self.assertEqual(originals, [p for p in reg["players"] if p.get("cohort") != W.APPEARANCE_COHORT])


# -- 3. Player report pages ----------------------------------------------------------------------------------------
class ReportAwardSectionTests(unittest.TestCase):
    def test_no_page_keeps_a_hand_written_awards_section(self):
        from runtime.player_reports import build_reports
        out = build_reports(ROOT, PLAYER)
        stale = [p for p, text in out.items() if p.suffix == ".md"
                 and ("No NBA awards recorded for this period" in text or "Season honor register" in text)]
        self.assertEqual(stale, [])
        season = out[PLAYER / "Stats_and_Awards/2003-04/README.md"]
        awards = json.loads((PLAYER / "awards.json").read_text())["awards"]
        for a in awards:
            if a["season"] == "2003-04" and a["name"] in ("Rookie of the Year", "All-NBA First Team", "All-Rookie First Team", "All-Star"):
                self.assertIn(f"| {a['name']} | {a['period_start']} to {a['period_end']} | {a['awarded_on']} |", season)


if __name__ == "__main__":
    unittest.main()
