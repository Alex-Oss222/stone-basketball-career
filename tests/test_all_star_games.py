"""All-Star weekend games (`runtime/all_star_games.py`) end to end in a scratch copy of the career: the three past weekends
locked retroactively, each game resolved by the kernel with test entropy (a stand-in for the engine, which the production
runner never allows), then written back, the MVPs decided and the records validated. Nothing is written to the
repository. The committed locks and requests must be exactly what the builder writes."""
from collections import Counter
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
PLAYER = "career/Dwyane_Wade"
SEASONS = ("2003-04", "2004-05", "2005-06")
LEAGUE = f"{PLAYER}/Stats_and_Awards/League"
ENGINE_COPY = "2005-06-all_star.json"          # a real copy in the scratch root, so a test may change it


def _farm(src, dst, keep_real):
    """dst mirrors src with symlinks, except the children named in `keep_real` ({name: None (absent) | dict (recurse)})."""
    dst.mkdir(parents=True, exist_ok=True)
    for entry in src.iterdir():
        if entry.name in keep_real:
            sub = keep_real[entry.name]
            if isinstance(sub, dict):
                _farm(entry, dst / entry.name, sub)
            elif sub == "copy":
                shutil.copy(entry, dst / entry.name)
            continue
        os.symlink(entry, dst / entry.name)


def scratch_root():
    """A temporary root: every repository entry linked, except what the All-Star pipeline writes."""
    tmp = Path(tempfile.mkdtemp(prefix="all-star-"))
    season_dirs = {s: {"11_All_Star": None} for s in SEASONS}
    league = {s: {"all_star_games.json": None, "All_Star_Games.md": None, "All_Star": None, "Award_Draws": {}}
              for s in SEASONS}
    _farm(ROOT, tmp, {".git": None, "career": {"Dwyane_Wade": {
        **season_dirs, "awards.json": "copy", "Stats_and_Awards": {"League": league}}},
        "library": {"all_star": {"engine": {ENGINE_COPY: "copy"}}}})
    # The copied awards file as it stood before any weekend game was played: the pipeline writes its exhibition honors.
    awards = tmp / "career/Dwyane_Wade/awards.json"
    data = json.loads(awards.read_text(encoding="utf-8"))
    data["awards"] = [a for a in data["awards"] if a.get("competition") not in ("all_star", "rookie_challenge")]
    awards.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return tmp


def resolve(root, request):
    """The game as the engine would play it, with test entropy (never the production runner)."""
    from runtime.all_star_engine import exhibition_environment, exhibition_spatial
    from runtime.era import exhibition_rules
    from runtime.game_requests import load_request
    from runtime.kernel import resolve_game, validate_result
    from scripts.collect_results import result_errors
    home, away, kw = load_request(root / request, root)
    r = resolve_game(home, away, entropy=hashlib.sha256(f"test:{kw['event_id']}".encode()).digest(),
                     event_id=kw["event_id"], rules=exhibition_rules(kw["game_type"], kw["game_date"]),
                     environment=exhibition_environment(kw["game_type"], kw["game_date"], root),
                     game_type=kw["game_type"], venue=kw["venue"], spatial_environment=exhibition_spatial(kw["game_date"], root))
    assert validate_result(r) == [], validate_result(r)             # the engine's own invariant check
    r = dict(r, game_date=kw["game_date"], kernel="2003.11")
    data = json.loads((root / request).read_text(encoding="utf-8"))
    assert result_errors(data, r, "game") == [], result_errors(data, r, "game")   # the collector's check
    return r


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from runtime import all_star_games as G
        cls.G = G
        cls.root = scratch_root()
        cls.refusals = []
        for day, retro in (("2006-04-19", False), ("2006-04-18", True)):
            try:
                G.lock(cls.root, day, retroactive=retro)
            except ValueError as exc:
                cls.refusals.append(str(exc))
        cls.lines = G.lock(cls.root, "2006-04-19", retroactive=True)
        cls.records = {s: G.read_record(cls.root, s) for s in SEASONS}
        cls.played = {}
        for s in SEASONS:
            for game in cls.records[s]["games"].values():
                result = resolve(cls.root, game["request"])
                (cls.root / game["result"]).write_text(json.dumps(result), encoding="utf-8")
                cls.played[game["event_id"]] = result
        cls.after_lines, cls.pending = G.after(cls.root, "2006-04-19")
        cls.records = {s: G.read_record(cls.root, s) for s in SEASONS}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root, ignore_errors=True)

    def games(self):
        return [g for s in SEASONS for g in self.records[s]["games"].values()]

    def test_a_missed_lock_is_refused_and_the_retroactive_lock_belongs_to_one_date(self):
        self.assertEqual(len(self.refusals), 2)
        self.assertIn("passed without a lock", self.refusals[0])
        self.assertIn("2006-04-19 only", self.refusals[1])

    def test_six_games_at_their_only_event_ids_and_paths(self):
        ids = sorted(g["event_id"] for g in self.games())
        self.assertEqual(ids, ["2004-02-13-rookie-challenge", "2004-02-15-all-star-game", "2005-02-18-rookie-challenge",
                               "2005-02-20-all-star-game", "2006-02-17-rookie-challenge", "2006-02-19-all-star-game"])
        for g in self.games():
            wade = self.G.plays(g)
            self.assertEqual(g["note"] is not None, wade)
            self.assertEqual("11_All_Star" in g["request"], wade)
            self.assertEqual(g["recorded_on"], "2006-04-19")
        rc06 = self.records["2005-06"]["games"]["rookie_challenge"]
        self.assertFalse(self.G.plays(rc06))
        self.assertTrue(rc06["request"].endswith("League/2005-06/All_Star/Games/2006-02-17-rookie-challenge.request.json"))

    def test_the_committed_locks_and_requests_are_what_the_builder_writes(self):
        for s in SEASONS:
            committed = json.loads((ROOT / self.G.record_path(s)).read_text(encoding="utf-8"))
            for game_type, game in self.records[s]["games"].items():
                lock = {k: v for k, v in game.items() if k != "mvp"}
                self.assertEqual({k: v for k, v in committed["games"][game_type].items() if k != "mvp"}, lock)
                self.assertEqual((ROOT / game["request"]).read_bytes(), (self.root / game["request"]).read_bytes())

    def test_the_commissioner_test_replaces_six_rookie_challenge_players(self):
        out = {s: [(c["side"], c["out"], c["replacement"]) for c in self.records[s]["games"]["rookie_challenge"]["availability"]]
               for s in SEASONS}
        self.assertEqual(sorted(o for _, o, _ in out["2003-04"]), ["Amar'e Stoudemire", "Manu Ginobili", "Marquis Daniels",
                                                                   "Mike Dunleavy"])
        self.assertEqual(sorted(o for _, o, _ in out["2004-05"]), ["David Harrison", "Kirk Hinrich"])
        self.assertEqual(out["2005-06"], [])
        for s in SEASONS:
            game = self.records[s]["games"]["rookie_challenge"]
            for c in game["availability"]:
                names = [p["player"] for p in game["teams"][c["side"]]["players"]]
                self.assertIn(c["replacement"], names)
                self.assertNotIn(c["out"], names)

    def test_the_lock_refuses_when_the_panel_no_longer_gives_the_recorded_nine(self):
        from runtime import all_star
        real = all_star.rookie_challenge_order

        def shuffled(*args, **kwargs):
            out = real(*args, **kwargs)
            nine, ranked = out["Rookies"]
            out["Rookies"] = (list(reversed(nine)), ranked)
            return out
        with mock.patch.object(all_star, "rookie_challenge_order", shuffled), self.assertRaisesRegex(ValueError, "recomputed nine"):
            self.G.lock_game(self.root, "2005-06", "rookie_challenge", "2006-04-19")

    def test_ranking_minutes_and_starters(self):
        from runtime.all_star_engine import edition
        for g in self.games():
            m = edition(g["game_type"], g["date"], self.root)["minutes"]
            for side, team in g["teams"].items():
                players = team["players"]
                self.assertEqual([p["minutes"] for p in players], m["starters"] + m["reserves"][:len(players) - 5])
                self.assertEqual(sum(p["starter"] for p in players), 5)
                self.assertEqual(sum(p["minutes"] for p in players), m["team_minutes"])
                for group in ([p for p in players if p["starter"]], [p for p in players if not p["starter"]]):
                    keys = [(-(p["game_score"] or 0), -(p["pts"] or 0), p["selection"]) for p in group]
                    self.assertEqual(keys, sorted(keys))
        east = self.records["2003-04"]["games"]["all_star"]["teams"]["East"]["players"]
        recorded = json.loads((ROOT / LEAGUE / "2003-04/all_star.json").read_text(encoding="utf-8"))["game_rosters"]["East"]
        self.assertEqual({p["player"] for p in east if p["starter"]}, set(recorded["starters"]))

    def test_positions_are_the_engines_own(self):
        wade = [p for g in self.games() for t in g["teams"].values() for p in t["players"] if p["player"] == "Dwyane Wade"]
        self.assertEqual(len(wade), 5)
        self.assertTrue(all(p["position"] in ("PG", "SG") for p in wade))
        self.assertTrue(all(p["position"] in ("PG", "SG", "SF", "PF", "C") for g in self.games()
                            for t in g["teams"].values() for p in t["players"]))

    def test_every_game_is_decided_and_wades_notes_are_written(self):
        self.assertEqual(self.pending, [])
        for g in self.games():
            self.assertIn("mvp", g)
            self.assertEqual(g["mvp"]["recorded_on"], "2006-04-19")
            self.assertTrue(g["mvp"]["winners"])
            if g["note"]:
                text = (self.root / g["note"]).read_text(encoding="utf-8")
                self.assertIn("status: played", text)
                self.assertIn("result_file: Game_1.result.json", text)

    def test_wades_games_are_their_own_records(self):
        from runtime.career_stats import aggregate, collect_games, select
        player = self.root / PLAYER                    # the scratch copy's own folders (its links are not walked)
        identity = json.loads((player / "professional_identity.json").read_text(encoding="utf-8"))
        records = collect_games(player, identity, "2006-04-19")
        kinds = Counter(r["competition"] for r in records)
        self.assertEqual(kinds, Counter({"all_star": 3, "rookie_challenge": 2}))
        for kind in ("all_star", "rookie_challenge"):
            a = aggregate(select(records, competition=kind))
            self.assertTrue(a["complete"])
            self.assertEqual(a["gp"], kinds[kind])
            self.assertEqual(len({r["season"] for r in select(records, competition=kind)}), kinds[kind])
        with self.assertRaisesRegex(ValueError, "different competitions"):
            aggregate(records)                         # never one total with another competition
        teams = {r["team"] for r in records}
        self.assertLessEqual(teams, {"East", "Rookies", "Sophomores"})

    def test_no_reader_of_nba_results_reads_them(self):
        from runtime.write_back import closed_results
        ids = set(self.played)
        for s in SEASONS:
            rows = closed_results(self.root, s, "2006-04-19")
            self.assertFalse(ids & {r["result"]["event_id"] for r in rows})
            self.assertEqual(len(rows), len(closed_results(ROOT, s, "2006-04-19")))

    def test_wades_mvp_is_an_exhibition_honor(self):
        from runtime import incentives, standing
        awards = json.loads((self.root / PLAYER / "awards.json").read_text(encoding="utf-8"))["awards"]
        won = [g for g in self.games() if "Dwyane Wade" in g["mvp"]["winners"]]
        mine = [a for a in awards if a["competition"] in ("all_star", "rookie_challenge")]
        self.assertEqual(len(mine), len(won))
        for a in mine:
            self.assertTrue((self.root / PLAYER / a["source"].split("#")[0]).is_file())
            self.assertEqual(a["recorded_on"], "2006-04-19")
            self.assertNotIn(a["name"], standing.HONOR_NAMES)
        fake = dict(id="2004-05-all-star-game-mvp", name="All-Star Game MVP", short_name="ASG MVP", status="earned",
                    competition="all_star", season="2004-05", period_start="2005-02-20", period_end="2005-02-20",
                    awarded_on="2005-02-20", source="Stats_and_Awards/League/2004-05/All_Star_Games.md")
        path = self.root / PLAYER / "awards.json"
        saved = path.read_text(encoding="utf-8")
        try:
            data = json.loads(saved)
            data["awards"] = [a for a in data["awards"] if a["id"] != fake["id"]] + [fake]
            path.write_text(json.dumps(data), encoding="utf-8")
            names = [a["name"] for a in incentives.earned_honors("2004-05", "2005-06-30", self.root)]
            self.assertIn("All-Star", names)
            self.assertNotIn("All-Star Game MVP", names)
        finally:
            path.write_text(saved, encoding="utf-8")

    def test_the_mvps_reach_the_award_hub_league_cards_and_followed_pages(self):
        from runtime import award_pages, followed_players
        from runtime.league_cards import weekend_mvp_honors
        registry = json.loads((ROOT / LEAGUE / "player_registry.json").read_text(encoding="utf-8"))["players"]
        for s in SEASONS:
            m = award_pages.model(s, self.root, "2006-04-19")
            want = sorted((g["name"], n) for g in self.records[s]["games"].values() for n in g["mvp"]["winners"])
            self.assertEqual(award_pages.facts(m)["All-Star weekend MVPs"], want)
            self.assertEqual(award_pages.page_facts(award_pages.season_page(s, self.root, "2006-04-19", m))["All-Star weekend MVPs"], want)
            self.assertEqual(award_pages.facts(award_pages.model(s, self.root, "2006-04-18"))["All-Star weekend MVPs"], [])
            rows = weekend_mvp_honors(registry, self.records[s], "2006-04-19")
            self.assertEqual(sum(len(v) for v in rows.values()), len(want))
            self.assertEqual(weekend_mvp_honors(registry, self.records[s], "2006-04-18"), {})
            for g in self.records[s]["games"].values():
                for n in g["mvp"]["winners"]:
                    honors = [h for _, h in followed_players.honors(self.root, n, s, "2006-04-19")]
                    self.assertIn(g["mvp"]["name"], honors)

    def test_a_changed_engine_file_of_a_locked_game_is_refused(self):
        from runtime import all_star_engine
        game = self.records["2005-06"]["games"]["all_star"]
        path = self.root / game["engine"]
        self.assertEqual(path.name, ENGINE_COPY)
        self.assertFalse(path.is_symlink())
        saved = path.read_text(encoding="utf-8")
        try:
            data = json.loads(saved)
            data["environment"]["purpose"] += " (a typo fixed)"        # prose only: the replay would still be refused
            path.write_text(json.dumps(data, indent=1, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
            self.assertTrue(any("not the engine file the 2005-06 All-Star Game was locked with" in e
                                for e in self.G.errors(self.root)))
        finally:
            path.write_text(saved, encoding="utf-8")
            all_star_engine._read.cache_clear()
        self.assertEqual(self.G.engine_digest(self.root, game), game["engine_sha256"])

    def test_a_correction_after_the_lock_leaves_the_lock_standing(self):
        from runtime import all_star
        real_read, real_order = all_star.read_record, all_star.rookie_challenge_order

        def corrected(root, season):                 # a step corrected after the lock, as award_corrections records one
            rec = copy.deepcopy(real_read(root, season))
            if season == "2005-06":
                step = next(s for s in rec["steps"] if s["step"] == "rookie_challenge")
                old = copy.deepcopy(step["teams"])
                step["teams"]["Rookies"][-1] = dict(step["teams"]["Rookies"][-1], player="Later Pick")
                step["correction"] = {"corrected_on": "2006-05-01", "superseded": {"teams": old}}
            return rec

        def redecided(root, c, day, rows):           # the code behind the correction decides the corrected nine
            out = real_order(root, c, day, rows)
            if c.season == "2005-06":
                nine, ranked = out["Rookies"]
                out["Rookies"] = (nine[:-1] + ["Later Pick"], ranked)
            return out
        with mock.patch.object(all_star, "read_record", corrected), \
                mock.patch.object(all_star, "rookie_challenge_order", redecided):
            self.assertEqual(self.G.corrected_since(self.root, "2005-06", "rookie_challenge", "2006-04-19"),
                             ["rookie_challenge"])
            self.assertEqual(self.G.corrected_since(self.root, "2005-06", "all_star", "2006-04-19"), [])
            with self.assertRaisesRegex(ValueError, "recomputed nine"):    # the lock read the nine known on its date
                self.G.lock_game(self.root, "2005-06", "rookie_challenge", "2006-04-19")
            self.assertEqual([e for e in self.G.errors(self.root) if "rookie_challenge lock" in e], [])

    def test_validation_passes_and_refuses_a_stray_request(self):
        self.assertEqual(self.G.errors(self.root), [])
        stray = self.root / LEAGUE / "2005-06/All_Star/Games/2006-02-17-rookie-challenge-2.request.json"
        data = json.loads((self.root / self.records["2005-06"]["games"]["rookie_challenge"]["request"]).read_text(encoding="utf-8"))
        stray.write_text(json.dumps(dict(data, event_id="2006-02-17-rookie-challenge-2")), encoding="utf-8")
        try:
            self.assertTrue(any("no locked game names" in e for e in self.G.errors(self.root)))
        finally:
            stray.unlink()


class MvpTests(unittest.TestCase):
    def edition_result(self, g):
        sides = list(g["teams"])
        return {"home": sides[0], "away": sides[1], "final_score": {"home": g["final"][sides[0]], "away": g["final"][sides[1]]},
                "player_stats": {side: [dict(p, player_id=p["player"], seconds=p["minutes"] * 60, minutes=p["minutes"])
                                        for p in g["teams"][team]["players"] if p["minutes"] > 0]
                                 for side, team in (("home", sides[0]), ("away", sides[1]))}}

    def test_the_rule_names_the_real_mvp_in_ten_of_the_thirteen_editions(self):
        from runtime.all_star_games import mvp_tally
        hits = 0
        for path in sorted((ROOT / "library/all_star/games").glob("*.json")):
            g = json.loads(path.read_text(encoding="utf-8"))
            winners, _ = mvp_tally(self.edition_result(g))
            hits += bool(set(winners) & {m["player"] for m in g["mvp"]})
        self.assertEqual(hits, 10)

    def tie(self):
        line = dict(pts=20, fgm=8, fga=15, tpm=1, tpa=3, ftm=3, fta=4, orb=1, drb=5, ast=4, stl=1, blk=0, tov=2, pf=2,
                    seconds=1500.0, minutes=25.0)
        other = dict(line, pts=6, fgm=3, fga=10, tpm=0, ftm=0, fta=0)
        home = [dict(line, player_id="A"), dict(line, player_id="B")] + [dict(other, player_id=f"H{i}") for i in range(3)]
        away = [dict(other, player_id=f"W{i}") for i in range(5)]
        return {"home": "East", "away": "West", "final_score": {"home": 70, "away": 30}, "home_stats": None,
                "player_stats": {"home": home, "away": away}}

    def test_a_three_way_rookie_challenge_tie_is_one_valid_draw(self):
        from runtime import all_star_games as G
        from runtime.decisions import decision_errors
        tie = self.tie()
        tie["player_stats"]["home"][2] = dict(tie["player_stats"]["home"][0], player_id="C")
        tmp = Path(tempfile.mkdtemp(prefix="all-star-mvp-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        (tmp / "r.json").write_text(json.dumps(tie), encoding="utf-8")
        game = {"game_type": "rookie_challenge", "date": "2007-02-16", "result": "r.json"}
        mvp, packet = G.decide_mvp(tmp, "2006-07", game, "2007-02-16")
        self.assertIsNone(mvp)
        data = json.loads(packet.read_text(encoding="utf-8"))
        self.assertEqual(sorted(data["options"]), ["A", "B", "C"])
        self.assertEqual(decision_errors(data), [])

    def test_equal_ballots_name_co_mvps_in_the_all_star_game(self):
        from runtime.all_star_games import mvp_tally
        winners, rows = mvp_tally(self.tie())
        self.assertEqual(sorted(winners), ["A", "B"])
        self.assertEqual(rows[0]["points"], rows[1]["points"])

    def test_a_rookie_challenge_tie_waits_for_one_engine_draw(self):
        from runtime import all_star_games as G
        tmp = Path(tempfile.mkdtemp(prefix="all-star-mvp-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        (tmp / "r.json").write_text(json.dumps(self.tie()), encoding="utf-8")
        game = {"game_type": "rookie_challenge", "date": "2007-02-16", "result": "r.json"}
        mvp, packet = G.decide_mvp(tmp, "2006-07", game, "2007-02-16")
        self.assertIsNone(mvp)
        data = json.loads(packet.read_text(encoding="utf-8"))
        from runtime.decisions import decision_errors
        self.assertEqual(decision_errors(data), [])
        self.assertEqual(sorted(data["options"]), ["A", "B"])
        packet.with_name(packet.name.replace(".decision.json", ".decision.result.json")).write_text(
            json.dumps({"outcome": "B"}), encoding="utf-8")
        mvp, _ = G.decide_mvp(tmp, "2006-07", game, "2007-02-16")
        self.assertEqual(mvp["winners"], ["B"])
        self.assertNotIn("recorded_on", mvp)
        self.assertTrue(mvp["tie_draw"].endswith("2006-07-rookie-challenge-mvp.decision.result.json"))


if __name__ == "__main__":
    unittest.main()
