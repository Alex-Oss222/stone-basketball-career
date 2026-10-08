"""The national pipeline end to end on the 2005 FIBA Americas Championship, in a scratch copy of the career: every day
from the record's opening to the final, each game resolved by the kernel with test entropy (a stand-in for the engine,
which the production runner never allows). Nothing is written to the repository."""
from datetime import date, timedelta
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
EDITION = "continental_qualifier_2005"


def scratch_root():
    """A temporary root: every repository entry linked, except the folders the pipeline writes."""
    tmp = Path(tempfile.mkdtemp(prefix="national-"))
    for entry in ROOT.iterdir():
        if entry.name not in ("career", ".git"):
            os.symlink(entry, tmp / entry.name)
    player = tmp / "career/Dwyane_Wade"
    player.mkdir(parents=True)
    for entry in (ROOT / "career").iterdir():
        if entry.name != "Dwyane_Wade":
            os.symlink(entry, tmp / "career" / entry.name)          # followed players (Chris Bosh's profiles)
    for entry in (ROOT / "career/Dwyane_Wade").iterdir():
        if entry.name not in ("FIBA", "National_Team"):
            os.symlink(entry, player / entry.name)
    (player / "National_Team").mkdir()
    shutil.copy(ROOT / "career/Dwyane_Wade/National_Team/wade_standing_rule.json", player / "National_Team")
    return tmp


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from runtime import national
        from runtime.era import national_rules
        from runtime.game_requests import load_request
        from runtime.kernel import resolve_game
        from runtime.national_engine import national_environment, national_spatial
        cls.root = scratch_root()
        cls.e = national.editions(cls.root)[EDITION]
        day = date.fromisoformat(national.selection_date(cls.e))
        while day.isoformat() <= cls.e["last_game"]:
            d = day.isoformat()
            lines, pending = national.day(d, cls.root)
            assert not pending, pending
            rec = national.read_record(cls.e, cls.root)
            for g in rec["games"].values():
                if g["date"] != d or not g.get("home"):
                    continue
                _, request, result = national.game_paths(cls.e, rec, g, cls.root)
                home, away, kw = load_request(request, cls.root)
                r = resolve_game(home, away, entropy=hashlib.sha256(f"test:{kw['event_id']}".encode()).digest(),
                                 event_id=kw["event_id"], rules=national_rules(d), environment=national_environment(d, cls.root),
                                 game_type=kw["game_type"], venue=kw["venue"], spatial_environment=national_spatial(d, cls.root))
                r["game_date"] = d
                result.write_text(json.dumps(r))
            national.after_games(d, cls.root)
            day += timedelta(days=1)
        cls.rec = national.read_record(cls.e, cls.root)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root, ignore_errors=True)

    def test_every_game_is_played_and_the_tournament_closes(self):
        from runtime import national
        self.assertEqual(len(national.results(self.e, self.rec, self.root)), 40)
        self.assertTrue(self.rec["closed"])
        self.assertEqual(len(self.rec["ranking"]), 10)
        self.assertEqual(self.rec["ranking"][0], self.rec["awards"]["champion"])
        self.assertEqual(len(self.rec["awards"]["all_tournament"]), 5)

    def test_second_round_carries_first_round_results(self):
        table = self.rec["tables"]["R"]
        self.assertEqual(len(table), 8)
        self.assertTrue(all(r["w"] + r["l"] == 7 for r in table))     # four new games and three carried

    def test_bracket_follows_the_tables(self):
        from runtime import national
        final_r = national.tables(self.e, self.rec, national.results(self.e, self.rec, self.root))["R"]
        semis = [g for g in self.rec["games"].values() if g["stage"] == "semifinal"]
        top4 = {r["team"] for r in final_r if r["position"] <= 4}
        self.assertEqual({t for g in semis for t in (g["home"], g["away"])}, top4)

    def test_usa_plays_its_real_2005_roster(self):
        usa = self.rec["rosters"]["United States"]["players"]
        self.assertEqual(len(usa), 12)
        self.assertNotIn("wadedw01", {p.get("bbr_id") for p in usa})
        self.assertIsNone(self.rec["selection"])

    def test_every_request_has_its_note_or_is_a_tournament_record(self):
        # repository validation's rule (scripts/validate_repository.py): a request needs a game note beside it unless
        # its result is a league or tournament record; other nations' games and the USA's without Wade have no note
        from runtime import national
        from runtime.game_requests import find_requests
        from runtime.season_games import is_league_record
        requests = [r for r in find_requests(self.root) if "FIBA" in r.parts or "National_Team" in r.parts]
        self.assertEqual(len(requests), 40)
        for request in requests:
            note = request.with_name(request.name.replace(".request.json", ".md"))
            self.assertTrue(note.is_file() or is_league_record(request) or national.is_tournament_record(request),
                            request.relative_to(self.root))

    def test_pages_are_written(self):
        page = (self.root / "career/Dwyane_Wade/FIBA/Continental_Cups/2005/README.md").read_text(encoding="utf-8")
        self.assertIn("Final placings and honors", page)
        self.assertIn("Second round", page)
        self.assertIn("### Final ranking", page)
        self.assertIn("### Medals", page)
        self.assertTrue((self.root / "career/Dwyane_Wade/FIBA/README.md").is_file())

    def test_medals_go_to_every_locked_roster_player_of_the_top_three(self):
        from runtime import national, national_medals
        reg = national_medals.read(self.e, self.root)
        ranking, a = self.rec["ranking"], self.rec["awards"]
        self.assertEqual([(t["place"], t["medal"], t["country"]) for t in reg["teams"]],
                         [(1, "gold", ranking[0]), (2, "silver", ranking[1]), (3, "bronze", ranking[2])])
        self.assertEqual(ranking[:3], [a["champion"], a["runner_up"], a["third"]])
        for place, team in enumerate(ranking, start=1):
            got = sorted(m["player"] for m in reg["medals"] if m["country"] == team)
            locked = sorted(p["player"] for p in self.rec["rosters"][team]["players"])
            self.assertEqual(got, locked if place <= 3 else [], team)          # 4th and below: none
        self.assertEqual(len(reg["medals"]), sum(len(self.rec["rosters"][t]["players"]) for t in ranking[:3]))
        self.assertEqual(len({m["id"] for m in reg["medals"]}), len(reg["medals"]))
        self.assertTrue(all(m["awarded_on"] == self.rec["closed_on"] == self.e["last_game"] for m in reg["medals"]))
        final = next(g for g in self.rec["games"].values() if g["stage"] == "final")
        third = next(g for g in self.rec["games"].values() if g["stage"] == "third_place")
        for m in reg["medals"]:
            game = final if m["place"] < 3 else third
            self.assertTrue(m["source_result"].endswith(national.event_id(self.e, game["number"]) + ".result.json"))

    def test_a_rebuild_does_not_duplicate_medals(self):
        from runtime import national, national_medals
        path = self.root / national_medals.register_path(self.e)
        before = path.read_text(encoding="utf-8")
        national.after_games(self.e["last_game"], self.root)               # a later run on the closed edition
        self.assertEqual(national_medals.write_all(self.root), [path])
        self.assertEqual(path.read_text(encoding="utf-8"), before)

    def test_medal_identities_are_frozen_on_the_close(self):
        """A medal player's later NBA debut (a registry row dated after the close) never renames his medal."""
        from unittest import mock
        from runtime import national_medals
        frozen, medal_teams = self.rec["medal_identities"], self.rec["ranking"][:3]
        self.assertEqual(sorted(frozen), sorted(medal_teams))
        for team in medal_teams:
            self.assertEqual([x["player"] for x in frozen[team]], [p["player"] for p in self.rec["rosters"][team]["players"]])
        register = national_medals.read(self.e, self.root)
        ident = national_medals.Identity(self.e, self.rec, self.root)
        fiba_only = [(t, p) for t in medal_teams for p in self.rec["rosters"][t]["players"] if not p.get("bbr_id")]
        later = []
        for n, (team, p) in enumerate(fiba_only):
            entry = ident.researched(team, p)
            later.append({"name": p["player"], "bbr_id": entry.get("bbr_id") or f"later{n:02d}",
                          "birth_date": entry.get("birth_date"), "added_on": "2005-11-02"})
        rows = json.loads((self.root / national_medals.REGISTRY).read_text(encoding="utf-8"))["players"] + later
        scratch = Path("scratch_player_registry.json")
        (self.root / scratch).write_text(json.dumps({"players": rows}), encoding="utf-8")
        try:
            with mock.patch.object(national_medals, "REGISTRY", scratch):
                debut = national_medals.Identity(self.e, self.rec, self.root, on="2005-12-01")
                self.assertTrue(any(debut(t, p)[0] for t, p in fiba_only))    # read on a later date, they would rename
                self.assertEqual(national_medals.build(self.e, self.rec, self.root), register)
                self.assertEqual(national_medals.freeze(self.e, self.rec, self.root), frozen)
                self.assertEqual(national_medals.medal_errors(self.root, "2005-12-01"), [])
        finally:
            (self.root / scratch).unlink()

    def test_medals_are_read_only_from_the_close(self):
        from runtime import national_medals
        m = national_medals.read(self.e, self.root)["medals"][0]
        ask = {"bbr_id": m["bbr_id"]} if m["bbr_id"] else {"name": m["player"]}
        day_before = (date.fromisoformat(self.e["last_game"]) - timedelta(days=1)).isoformat()
        self.assertIn(m, national_medals.medals_for(**ask, on=self.e["last_game"], root=self.root))
        self.assertEqual(national_medals.medals_for(**ask, on=day_before, root=self.root), [])

    def test_validation_catches_a_missing_or_extra_medal(self):
        from runtime import national_medals
        clock = self.e["last_game"]
        self.assertEqual(national_medals.medal_errors(self.root, clock), [])
        path = self.root / national_medals.register_path(self.e)
        original = path.read_text(encoding="utf-8")
        try:
            data = json.loads(original)
            dropped = data["medals"].pop()
            path.write_text(json.dumps(data), encoding="utf-8")
            self.assertTrue(any(f"lacks {dropped['id']}" in e for e in national_medals.medal_errors(self.root, clock)))
            data = json.loads(original)
            fourth = self.rec["ranking"][3]
            player = self.rec["rosters"][fourth]["players"][0]["player"]
            data["medals"].append(dict(data["medals"][-1], id=f"x-{fourth}-bronze", player=player, country=fourth))
            path.write_text(json.dumps(data), encoding="utf-8")
            self.assertTrue(any(f"is not the medal {fourth}'s final place earns" in e
                                for e in national_medals.medal_errors(self.root, clock)))
            self.assertTrue(any("after the career date" in e for e in national_medals.medal_errors(self.root, "2005-09-03")))
        finally:
            path.write_text(original, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
