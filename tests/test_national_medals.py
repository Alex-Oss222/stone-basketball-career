"""FIBA team medals (runtime/national_medals.py): the register's rule on a small closed record, its validation, its
readers and where it shows (league cards, followed players). Wade's own awards.json medal stays as before. Scratch
folders only; nothing is written to the repository. The full 2005 tournament run is in tests/test_national_pipeline.py."""
import json
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]

EDITION = {"edition_id": "test_cup_2005", "family": "Continental_Cups", "edition": "2005", "name": "2005 Test Cup",
           "game_type": "continental_qualifier", "first_game": "2005-08-24", "last_game": "2005-09-04", "rosters": {}}


NO_ROOT = ROOT / "tests" / "no-such-medal-root"          # a root with no registry: identities from the locked roster


def record(frozen=False):
    """A closed record: four teams, three locked players each; Spain's third man (Spain Gamma) never played. `frozen`:
    with the medal teams' identities frozen on the close, as `national.after_games` writes them."""
    rosters = {team: {"coach": None, "players": [
        {"player": f"{team} {n}", "bbr_id": None, "fiba_key": f"fiba:{team[:3].lower()}:{team.lower()}-{n.lower()}:1980-01-0{i}"}
        for i, n in enumerate(("Alpha", "Beta", "Gamma"), start=1)]} for team in ("Spain", "Greece", "United States", "Lithuania")}
    rosters["United States"]["players"][0] = {"player": "Dwyane Wade", "bbr_id": "wadedw01", "fiba_key": None}
    rec = {"closed": True, "closed_on": "2005-09-04", "ranking": ["United States", "Spain", "Greece", "Lithuania"],
           "rosters": rosters, "games": {}, "awards": {
               "champion": "United States", "runner_up": "Spain", "third": "Greece", "mvp": None, "all_tournament": []}}
    if frozen:
        from runtime.national_medals import freeze
        rec["medal_identities"] = freeze(EDITION, rec, NO_ROOT)
    return rec


def played(rec):
    return {(team, p["player"]): 7 for team, r in rec["rosters"].items() for p in r["players"] if p["player"] != "Spain Gamma"}


def sources():
    return {1: "career/Dwyane_Wade/FIBA/Continental_Cups/2005/Games/final.result.json",
            2: "career/Dwyane_Wade/FIBA/Continental_Cups/2005/Games/final.result.json",
            3: "career/Dwyane_Wade/FIBA/Continental_Cups/2005/Games/third.result.json"}


class RegisterTests(unittest.TestCase):
    def setUp(self):
        from runtime.national_medals import assemble
        self.rec = record()
        self.reg = assemble(EDITION, self.rec, sources(), played(self.rec))

    def test_top_three_win_gold_silver_bronze_for_every_locked_player(self):
        by_team = {}
        for m in self.reg["medals"]:
            by_team.setdefault(m["country"], set()).add((m["player"], m["medal"], m["place"]))
        self.assertEqual(by_team["United States"], {("Dwyane Wade", "gold", 1), ("United States Beta", "gold", 1),
                                                    ("United States Gamma", "gold", 1)})
        self.assertEqual({x[1] for x in by_team["Spain"]}, {"silver"})
        self.assertEqual({x[1] for x in by_team["Greece"]}, {"bronze"})
        self.assertNotIn("Lithuania", by_team)                                       # fourth: no medal
        self.assertEqual(len(self.reg["medals"]), 9)

    def test_a_player_who_never_played_still_receives_the_medal(self):
        m = next(x for x in self.reg["medals"] if x["player"] == "Spain Gamma")
        self.assertEqual((m["medal"], m["games_played"]), ("silver", 0))

    def test_each_medal_names_its_player_country_tournament_place_date_and_source(self):
        m = next(x for x in self.reg["medals"] if x["player"] == "Greece Alpha")
        self.assertEqual(m["id"], "test_cup_2005-greece-greece-alpha-1980-01-01-bronze")
        self.assertEqual((m["country"], m["tournament"], m["edition"], m["place"], m["awarded_on"]),
                         ("Greece", "2005 Test Cup", "2005", 3, "2005-09-04"))
        self.assertTrue(m["source_result"].endswith("third.result.json"))
        wade = next(x for x in self.reg["medals"] if x["player"] == "Dwyane Wade")
        self.assertEqual(wade["id"], "test_cup_2005-united-states-wadedw01-gold")

    def test_a_rebuild_is_identical_and_ids_are_unique(self):
        from runtime.national_medals import _key, assemble
        again = assemble(EDITION, record(), sources(), played(record()))
        self.assertEqual(again, self.reg)
        ids = [m["id"] for m in self.reg["medals"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(ids, [m["id"] for m in sorted(self.reg["medals"], key=lambda m: (m["place"], _key(m["player"]), m["id"]))])

    def test_a_place_no_game_decided_cites_the_ranking(self):
        from runtime.national_medals import assemble
        reg = assemble(EDITION, record(), {1: "a.json", 2: "a.json"}, {})
        self.assertTrue(reg["teams"][2]["source_result"].endswith("tournament.json#ranking"))


class ValidationTests(unittest.TestCase):
    def setUp(self):
        from runtime.national_medals import assemble
        self.rec = record(frozen=True)
        self.fresh = assemble(EDITION, self.rec, sources(), played(self.rec))

    def errors(self, have, rec=None, clock="2005-09-30", wade=("test_cup_2005-gold",)):
        from runtime.national_medals import edition_errors
        return edition_errors(EDITION, rec or self.rec, have, self.fresh, clock, set(wade))

    def test_a_matching_register_passes(self):
        self.assertEqual(self.errors(json.loads(json.dumps(self.fresh))), [])

    def test_a_closed_edition_needs_its_register(self):
        self.assertTrue(any("has no medal register" in e for e in self.errors(None)))

    def test_no_medal_before_the_close(self):
        from runtime.national_medals import edition_errors
        rec = dict(record(), closed=False)
        self.assertTrue(any("before the tournament closed" in e for e in edition_errors(EDITION, rec, self.fresh, None)))
        self.assertEqual(edition_errors(EDITION, rec, None, None), [])
        self.assertTrue(any("after the career date" in e for e in self.errors(self.fresh, clock="2005-09-03")))
        early = json.loads(json.dumps(self.fresh))
        early["medals"][0]["awarded_on"] = "2005-09-03"
        self.assertTrue(any("before the tournament closed" in e for e in self.errors(early)))

    def test_a_missing_medal_is_caught(self):
        have = json.loads(json.dumps(self.fresh))
        dropped = have["medals"].pop(4)
        self.assertTrue(any(f"lacks {dropped['id']}" in e for e in self.errors(have)))

    def test_an_extra_medal_is_caught(self):
        have = json.loads(json.dumps(self.fresh))
        have["medals"].append(dict(have["medals"][0], id="test_cup_2005-lithuania-x-bronze", player="Lithuania Alpha",
                                   country="Lithuania"))
        self.assertTrue(any("is not the medal Lithuania's final place earns" in e for e in self.errors(have)))
        have["medals"].append(dict(have["medals"][0], id="test_cup_2005-united-states-y-gold", player="Never Selected"))
        self.assertTrue(any("not on United States's locked roster" in e for e in self.errors(have)))
        have = json.loads(json.dumps(self.fresh))
        have["medals"].append(dict(have["medals"][0]))
        self.assertTrue(any("recorded twice" in e for e in self.errors(have)))

    def test_wade_medal_must_also_be_in_awards_json(self):
        self.assertTrue(any("not in awards.json" in e for e in self.errors(self.fresh, wade=())))

    def test_an_awards_json_medal_the_register_does_not_back_is_caught(self):
        from runtime.national_medals import assemble, edition_errors, freeze
        wrong = self.errors(self.fresh, wade=("test_cup_2005-gold", "test_cup_2005-silver"))
        self.assertIn("test_cup_2005: awards.json has Wade's silver medal but the medal register does not", wrong)
        self.assertFalse(any("gold medal but" in e for e in wrong))
        rec = record(frozen=True)
        rec["ranking"] = ["Spain", "Greece", "Lithuania", "United States"]                 # the USA 4th: no medal
        rec["medal_identities"] = freeze(EDITION, rec, NO_ROOT)
        fresh = assemble(EDITION, rec, sources(), played(rec))
        self.assertIn("test_cup_2005: awards.json has Wade's gold medal but the medal register does not",
                      edition_errors(EDITION, rec, fresh, fresh, "2005-09-30", {"test_cup_2005-gold"}))
        early = dict(record(), closed=False)
        self.assertIn("test_cup_2005: awards.json has Wade's gold medal but the tournament has not closed",
                      edition_errors(EDITION, early, None, None, "2005-09-30", {"test_cup_2005-gold"}))
        self.assertEqual(edition_errors(EDITION, early, None, None, "2005-09-30", {"test_cup_2005-mvp"}), [])

    def test_identities_must_be_frozen_at_the_close_and_follow_the_locked_roster(self):
        from runtime.national_medals import identity_errors
        self.assertEqual(identity_errors(EDITION, self.rec), [])
        self.assertTrue(any("not frozen at the close" in e for e in identity_errors(EDITION, record())))
        self.assertTrue(any("not frozen at the close" in e for e in self.errors(self.fresh, rec=record())))
        early = dict(self.rec, closed=False)
        self.assertEqual(identity_errors(EDITION, early), ["test_cup_2005: medal identities frozen before the tournament closed"])
        bad = json.loads(json.dumps(self.rec))
        bad["medal_identities"]["Spain"].reverse()
        self.assertIn("test_cup_2005: Spain's frozen medal identities do not follow its locked roster", identity_errors(EDITION, bad))
        bad = json.loads(json.dumps(self.rec))
        bad["medal_identities"]["United States"][0]["bbr_id"] = "someone01"
        self.assertTrue(any("Dwyane Wade's frozen medal bbr_id someone01" in e for e in identity_errors(EDITION, bad)))
        bad = json.loads(json.dumps(self.rec))
        bad["medal_identities"]["Lithuania"] = []
        self.assertTrue(any("not the medal teams" in e for e in identity_errors(EDITION, bad)))


def registry_row(name, bbr_id, birth_date, added_on=None):
    row = {"name": name, "bbr_id": bbr_id, "birth_date": birth_date}
    if added_on:
        row["added_on"] = added_on
    return row


class IdentityTests(unittest.TestCase):
    """Identity as the league knew it on the close: the locked id first; a researched id only when the registry tracked
    him on or before the close; the registry's one same-name, same-birth player; else his FIBA identity. Frozen into the
    record, so a later registry row or repair never renames a medal."""

    PLAYERS = [("Locked Star", "lockst01", None), ("Tracked Early", "earlytr01", "1980-02-02"),
               ("Added Before", "beforad01", "1981-03-03"), ("Debut Later", "laterde01", "1982-04-04"),
               ("Birth Match", None, "1984-06-06"), ("Twin Name", None, "1983-05-05"), ("Late Birth", None, "1985-07-07"),
               ("Never Tracked", "nevertr01", "1986-08-08"), ("Repaired Later", None, "1987-09-09")]

    def setUp(self):
        from runtime.national_medals import REGISTRY
        self.root = Path(tempfile.mkdtemp(prefix="medals-"))
        self.registry = self.root / REGISTRY
        self.write_registry([
            registry_row("Tracked Early", "earlytr01", "1980-02-02"),                       # an original row
            registry_row("Added Before", "beforad01", "1981-03-03", "2005-08-30"),
            registry_row("Debut Later", "laterde01", "1982-04-04", "2005-11-02"),           # his NBA debut after the close
            registry_row("Birth Match", "birthma01", "1984-06-06"),
            registry_row("Twin Name", "twinna01", "1983-05-05"), registry_row("Twin Name", "twinna02", "1983-05-05"),
            registry_row("Late Birth", "latebi01", "1985-07-07", "2005-10-01"),
            registry_row("Repaired Later", None, None, "2005-08-28")])      # registered before the close, no id yet
        researched = [{"name": n, "bbr_id": b, "birth_date": d,
                       "fiba_key": None if n == "Locked Star" else f"fiba:esp:{n.lower().replace(' ', '-')}:{d}"}
                      for n, b, d in self.PLAYERS]
        self.e = dict(EDITION, rosters={"Spain": {"coach": None, "players": researched}})
        locked = [{"player": x["name"], "bbr_id": "lockst01" if x["name"] == "Locked Star" else None, "fiba_key": x["fiba_key"]}
                  for x in researched]
        self.rec = record()
        self.rec["rosters"]["Spain"]["players"] = locked
        self.rec["ranking"] = ["Spain", "Greece", "Lithuania", "United States"]

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def write_registry(self, rows):
        self.registry.parent.mkdir(parents=True, exist_ok=True)
        self.registry.write_text(json.dumps({"players": rows}), encoding="utf-8")

    def ids(self, on=None):
        from runtime.national_medals import Identity
        ident = Identity(self.e, self.rec, self.root, on)
        return {p["player"]: ident("Spain", p)[0] for p in self.rec["rosters"]["Spain"]["players"]}

    def test_each_tier_as_the_league_knew_it_on_the_close(self):
        from runtime.national_medals import FIBA_ONLY, LOCKED, Identity
        self.assertEqual(self.ids(), {"Locked Star": "lockst01", "Tracked Early": "earlytr01", "Added Before": "beforad01",
                                      "Debut Later": None, "Birth Match": "birthma01", "Twin Name": None,
                                      "Late Birth": None, "Never Tracked": None, "Repaired Later": None})
        ident = Identity(self.e, self.rec, self.root)
        roster = {p["player"]: p for p in self.rec["rosters"]["Spain"]["players"]}
        self.assertEqual(ident("Spain", roster["Locked Star"]), ("lockst01", None, LOCKED))
        self.assertEqual(ident("Spain", roster["Debut Later"]), (None, "fiba:esp:debut-later:1982-04-04", FIBA_ONLY))
        self.assertIn("registry", ident("Spain", roster["Tracked Early"])[2])
        self.assertIn("same name and birth date", ident("Spain", roster["Birth Match"])[2])
        later = self.ids(on="2005-12-01")                          # only the date kept the later rows out
        self.assertEqual((later["Debut Later"], later["Late Birth"]), ("laterde01", "latebi01"))

    def test_a_registry_row_added_or_repaired_after_the_close_never_renames_a_medal(self):
        from runtime.national_medals import build, edition_errors, freeze
        self.rec["medal_identities"] = freeze(self.e, self.rec, self.root)
        before = build(self.e, self.rec, self.root)
        spain = {m["player"]: m for m in before["medals"] if m["country"] == "Spain"}
        self.assertEqual(spain["Debut Later"]["id"], "test_cup_2005-spain-debut-later-1982-04-04-gold")
        self.assertEqual(spain["Birth Match"]["id"], "test_cup_2005-spain-birthma01-gold")
        self.assertEqual(spain["Repaired Later"]["id"], "test_cup_2005-spain-repaired-later-1987-09-09-gold")
        rows = json.loads(self.registry.read_text(encoding="utf-8"))["players"]
        rows.append(registry_row("Never Tracked", "nevertr01", "1986-08-08", "2005-11-02"))      # a later NBA debut
        rows.append(registry_row("Debut Later", "laterde02", "1982-04-04", "2005-11-03"))
        rows[-3].update(bbr_id="repaila01", birth_date="1987-09-09")      # repair_registry fills his id after the close
        self.write_registry(rows)
        self.assertEqual(build(self.e, self.rec, self.root), before)
        self.assertEqual(edition_errors(self.e, self.rec, json.loads(json.dumps(before)), build(self.e, self.rec, self.root),
                                        "2005-12-01", set()), [])
        again = freeze(self.e, self.rec, self.root)                      # the date guard alone keeps the later rows out,
        changed = [x["player"] for x, y in zip(again["Spain"], self.rec["medal_identities"]["Spain"]) if x != y]
        self.assertEqual(changed, ["Repaired Later"])                    # but not a repair: hence the frozen identities


class WadeAwardsTests(unittest.TestCase):
    """record_wade_honors keeps writing awards.json exactly as before; the register never touches it."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="medals-"))
        player = self.root / "career/Dwyane_Wade"
        player.mkdir(parents=True)
        shutil.copy(ROOT / "career/Dwyane_Wade/awards.json", player / "awards.json")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_awards_json_gets_the_same_medal_entry_once(self):
        from runtime import national
        from runtime.national_medals import assemble, register_path
        path = self.root / "career/Dwyane_Wade/awards.json"
        before = json.loads(path.read_text(encoding="utf-8"))["awards"]
        rec = record()
        self.assertEqual(national.record_wade_honors(EDITION, rec, self.root), ["2005 Test Cup gold medal"])
        after = json.loads(path.read_text(encoding="utf-8"))["awards"]
        self.assertEqual(after[:-1], before)
        self.assertEqual(after[-1], {"id": "test_cup_2005-gold", "name": "2005 Test Cup gold medal", "short_name": "Gold Medal",
                                     "status": "earned", "competition": "continental_qualifier", "season": "2005",
                                     "period_start": "2005-08-24", "period_end": "2005-09-04", "awarded_on": "2005-09-04",
                                     "source": "FIBA/Continental_Cups/2005/README.md#final-placings-and-honors"})
        text = path.read_text(encoding="utf-8")
        national._write(self.root / register_path(EDITION), assemble(EDITION, rec, sources(), played(rec)))
        self.assertEqual(national.record_wade_honors(EDITION, rec, self.root), [])     # no duplicate
        self.assertEqual(path.read_text(encoding="utf-8"), text)


class ReaderTests(unittest.TestCase):
    def setUp(self):
        from runtime import national
        from runtime.national_medals import assemble, register_path
        self.root = Path(tempfile.mkdtemp(prefix="medals-"))
        rec = record()
        rec["rosters"]["Spain"]["players"][0]["bbr_id"] = "boshch01"      # a stand-in NBA id for the readers
        rec["rosters"]["Spain"]["players"][0]["player"] = "Chris Bosh"
        self.reg = assemble(EDITION, rec, sources(), played(rec))
        national._write(self.root / register_path(EDITION), self.reg)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_medals_appear_only_from_the_close(self):
        from runtime.national_medals import medals_for, register_medals
        self.assertEqual(medals_for(bbr_id="boshch01", on="2005-09-03", root=self.root), [])
        got = medals_for(bbr_id="boshch01", on="2005-09-04", root=self.root)
        self.assertEqual([(m["medal"], m["country"]) for m in got], [("silver", "Spain")])
        self.assertEqual(len(register_medals(self.root, "2005-09-04")), 9)
        self.assertEqual(register_medals(self.root, "2005-09-03"), [])

    def test_by_name_when_the_medal_has_no_nba_id(self):
        from runtime.national_medals import medals_for
        self.assertEqual(len(medals_for(name="Greece Beta", on="2005-12-01", root=self.root)), 1)
        self.assertEqual(medals_for(bbr_id="someone01", name="Chris Bosh", on="2005-12-01", root=self.root), [])

    def test_league_card_awards_section(self):
        from runtime.league_cards import awards_lines, award_notice, medal_honors
        from runtime.national_medals import register_medals
        players = [{"name": "Chris Bosh", "bbr_id": "boshch01"}, {"name": "Greece Alpha", "bbr_id": "nobody01"}]
        honors = medal_honors(players, register_medals(self.root, "2005-09-04"))
        self.assertEqual(list(honors), ["chrisbosh"])                    # a medal without an NBA id stays off the cards
        ctx = SimpleNamespace(honors=honors, on="2005-09-04", root=self.root)
        text = "\n".join(awards_lines(ctx, {"name": "Chris Bosh"}))
        self.assertIn("2005 Test Cup silver medal", text)
        self.assertIn("**Silver medal** (Spain, place 2)", text)
        self.assertIn("(0 won), and 1 FIBA team medal", text)
        self.assertIn("FIBA/Continental_Cups/2005/README.md#medals", text)
        self.assertIn("FIBA team medals: 2005 Test Cup silver medal (Spain).", award_notice(ctx, {"name": "Chris Bosh"}))
        empty = SimpleNamespace(honors={}, on="2005-09-04", root=self.root)
        self.assertEqual(awards_lines(empty, {"name": "Chris Bosh"})[1].split(".")[0],
                         "No simulated honor has been recorded for this player through 2005-09-04")
        self.assertNotIn("FIBA", award_notice(empty, {"name": "Chris Bosh"}))

    def test_followed_player_honor_rows(self):
        from runtime.followed_players import medal_honor_rows
        rows = medal_honor_rows(self.root, "boshch01", "2005-09-04", self.root / "career/Chris_Bosh")
        self.assertEqual(rows, [["2005 FIBA", "2005-09-04", "[2005 Test Cup: silver medal (Spain, 2nd)]"
                                 "(../Dwyane_Wade/FIBA/Continental_Cups/2005/README.md#medals)"]])
        self.assertEqual(medal_honor_rows(self.root, "boshch01", "2005-09-03", self.root / "career/Chris_Bosh"), [])


if __name__ == "__main__":
    unittest.main()
