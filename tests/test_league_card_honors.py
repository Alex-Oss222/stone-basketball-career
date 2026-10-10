"""League player cards' honors: All-Star selections from `all_star.json` (on the card from the selection date, matched
by NBA id, else by name) and season awards over the decision's own period (the Finals MVP's starts with the Finals).

The live checks build the card context read-only (`CardContext` and `awards_lines` write nothing)."""
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

from runtime.league_cards import (CardContext, LEAGUE_DIR, PLAYER_DIR, all_star_honors, award_notice, awards_lines,
                                  card_data, html_card, markdown_card, _key)

ROOT = Path(__file__).resolve().parents[1]

RECORD = {"season": "2004-05", "all_stars": [
    {"player": "Chris Bosh", "bbr_id": "boshch01", "team": "Toronto Raptors", "conference": "East", "role": "reserve",
     "selected_on": "2005-02-08"},
    {"player": "Tracy McGrady", "bbr_id": "mcgratr01", "team": "Houston Rockets", "conference": "West", "role": "starter",
     "selected_on": "2005-02-03"},
    {"player": "Nene", "bbr_id": "hilarne01", "team": "Denver Nuggets", "conference": "West", "role": "reserve",
     "selected_on": "2005-02-08"},
    {"player": "Jamal Crawford", "bbr_id": None, "team": "Chicago Bulls", "conference": "East", "role": "injury replacement",
     "selected_on": "2005-02-18", "replacing": "Jason Kidd"},
    {"player": "Chris Bosh", "bbr_id": "untracked01", "team": "Nowhere", "conference": "East", "role": "reserve",
     "selected_on": "2005-02-08"},
]}
PLAYERS = [{"name": "Chris Bosh", "bbr_id": "boshch01"}, {"name": "Tracy McGrady", "bbr_id": "mcgratr01"},
           {"name": "Nenê", "bbr_id": "hilarne01"}, {"name": "Jamal Crawford", "bbr_id": "crawfja01"}]
OPENING = "2004-11-02"


class AllStarHonorTests(unittest.TestCase):
    def test_on_the_card_from_the_selection_date_only(self):
        self.assertEqual(all_star_honors(PLAYERS, RECORD, "2005-02-02", OPENING), {})
        early = all_star_honors(PLAYERS, RECORD, "2005-02-07", OPENING)
        self.assertEqual(list(early), [_key("Tracy McGrady")])            # the starters' day; reserves come on 02-08
        self.assertEqual(early[_key("Tracy McGrady")][0]["announced_on"], "2005-02-03")
        later = all_star_honors(PLAYERS, RECORD, "2005-02-08", OPENING)
        self.assertEqual(sorted(later), sorted(_key(n) for n in ("Tracy McGrady", "Chris Bosh", "Nenê")))
        self.assertNotIn(_key("Jamal Crawford"), later)
        self.assertIn(_key("Jamal Crawford"), all_star_honors(PLAYERS, RECORD, "2005-02-18", OPENING))

    def test_matched_by_nba_id_else_by_name(self):
        honors = all_star_honors(PLAYERS, RECORD, "2005-12-01", OPENING)
        self.assertEqual(len(honors[_key("Chris Bosh")]), 1)              # an untracked id never lands on a namesake
        self.assertIn(_key("Nenê"), honors)                               # the registry's name, by id
        self.assertEqual(honors[_key("Jamal Crawford")][0]["replacing"], "Jason Kidd")   # no id: by name

    def test_card_row_and_notice(self):
        ctx = SimpleNamespace(honors=all_star_honors(PLAYERS, RECORD, "2005-12-01", OPENING), on="2005-12-01", root=ROOT)
        text = "\n".join(awards_lines(ctx, {"name": "Chris Bosh"}))
        self.assertIn("| East All-Star (reserve) | 2004-11-02 to 2005-02-08 | 2005-02-08 | **Selected** | "
                      "[Decision](../2004-05/All_Star.md#all-stars) |", text)
        self.assertIn("(1 won)", text)
        self.assertIn("Season honors: East All-Star (reserve).", award_notice(ctx, {"name": "Chris Bosh"}))
        crawford = "\n".join(awards_lines(ctx, {"name": "Jamal Crawford"}))
        self.assertIn("| East All-Star (injury replacement) | 2004-11-02 to 2005-02-18 | 2005-02-18 | "
                      "**Selected**, replacing Jason Kidd |", crawford)


class LiveCardHonorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ctx = CardContext(ROOT)
        cls.players = {p["registry_id"]: p for p in cls.ctx.registry["players"]}

    def section(self, pid):
        return "\n".join(awards_lines(self.ctx, self.players[pid]))

    def test_every_recorded_all_star_is_on_his_card(self):
        names = {p["bbr_id"]: p for p in self.ctx.registry["players"]}
        seen = 0
        for season in self.ctx.seasons:
            path = ROOT / LEAGUE_DIR / season / "all_star.json"
            if not path.is_file():
                continue
            for a in json.loads(path.read_text(encoding="utf-8")).get("all_stars", []):
                if a["selected_on"] > self.ctx.on or a.get("bbr_id") not in names:
                    continue
                with self.subTest(season=season, player=a["player"]):
                    self.assertIn(f"| {a['conference']} All-Star ({a['role']}) |", self.section(a["bbr_id"]))
                    self.assertIn(f"| {a['selected_on']} | **Selected**", self.section(a["bbr_id"]))
                    self.assertIn(f"[Decision](../{season}/All_Star.md#all-stars)", self.section(a["bbr_id"]))
                seen += 1
        self.assertGreaterEqual(seen, 49)                                 # 24 in 2003-04 and 25 in 2004-05

    def test_wade_card_lists_his_all_star_selections_and_agrees_with_awards_json(self):
        awards = json.loads((ROOT / PLAYER_DIR / "awards.json").read_text(encoding="utf-8"))["awards"]
        stars = [a for a in awards if a["name"] == "All-Star" and a["awarded_on"] <= self.ctx.on]
        self.assertGreaterEqual(len(stars), 2)
        data = card_data(self.ctx, self.players["wadedw01"])
        md, html = markdown_card(self.ctx, data), html_card(self.ctx, data)
        for a in stars:
            with self.subTest(award=a["id"]):
                self.assertIn(f"| East All-Star ({a['role']}) | {a['period_start']} to {a['period_end']} | {a['awarded_on']} | "
                              f"**Selected** | [Decision](../{a['season']}/All_Star.md#all-stars) |", md)
        nba = [a for a in awards if a.get("competition") in ("regular", "playoff") and a["awarded_on"] <= self.ctx.on]
        self.assertIn(f"from closed award decisions ({len(nba)} won)", md)
        self.assertEqual(md.count("All-Star ("), len(stars))
        self.assertIn("Season honors: East All-Star (", html)

    def test_season_awards_use_the_decisions_own_period(self):
        checked = 0
        for season in self.ctx.seasons:
            path = ROOT / LEAGUE_DIR / season / "season_awards.json"
            if not path.is_file():
                continue
            for d in json.loads(path.read_text(encoding="utf-8"))["decisions"]:
                if not d.get("period_start") or d["announced_on"] > self.ctx.on:
                    continue
                for winner in d.get("winners") or []:
                    pid = next((p["registry_id"] for p in self.ctx.registry["players"] if _key(p["name"]) == _key(winner)), None)
                    if pid is None:
                        continue
                    with self.subTest(award=d["id"], winner=winner):
                        self.assertIn(f"| {d['name']} | {d['period_start']} to {d['evidence_through']} | {d['announced_on']} | "
                                      "**Winner** |", self.section(pid))
                    checked += 1
        self.assertGreaterEqual(checked, 2)                               # the 2003-04 and 2004-05 Finals MVPs
        self.assertIn("| Finals MVP | 2004-06-06 to 2004-06-20 | 2004-06-20 | **Winner** |", self.section("garneke01"))
        self.assertIn("| Finals MVP | 2005-06-09 to 2005-06-16 | 2005-06-16 | **Winner** |", self.section("bibbymi01"))
        self.assertIn("| Most Valuable Player | 2003-10-28 to 2004-04-14 |", self.section("garneke01"))   # opening night

    def test_followed_bosh_pages_show_the_same_all_star_selection(self):
        from runtime.followed_players import honors
        bosh = [h for h in honors(ROOT, "Chris Bosh", "2004-05", self.ctx.on) if h[1].startswith("All-Star")]
        self.assertEqual(bosh, [("2005-02-08", "All-Star (East, reserve)")])
        self.assertIn("| East All-Star (reserve) | 2004-11-02 to 2005-02-08 | 2005-02-08 | **Selected** |", self.section("boshch01"))


if __name__ == "__main__":
    unittest.main()
