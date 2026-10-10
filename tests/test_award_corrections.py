"""Dated corrections of recorded award results (`runtime/award_corrections.py`, the award audit the user approved).

On a scratch copy of the three affected records (as recorded before any correction) and their pages, `apply` re-decides
the approved items with the repository's own evidence and current code: exactly the expected places change, the Rookie
of the Year vote (outside the approval) stands, every winner and every honor of Wade's stands, and a second run changes
nothing. A reader dated before the correction reads the original result, one dated on or after it the corrected one;
the pages, the season hub and the cards name the correction date and the superseded players; validation passes after
`apply` and refuses a corrected value edited by hand, a correction on an item outside the approval, a superseded winner,
a backdated correction or another reason, and `plan`/`apply` refuse an unapproved target or date.
"""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

from runtime import award_corrections as AC

ROOT = Path(__file__).resolve().parents[1]
LEAGUE = Path("career/Dwyane_Wade/Stats_and_Awards/League")
DAY = "2006-01-01"
KINDS = [("season_awards", "2003-04"), ("all_star", "2003-04"), ("all_star", "2004-05"), ("award_decisions", "2003-04")]
RECORDS = [AC.record_path(k, s) for k, s in KINDS]
PAGES = [LEAGUE / p for p in ("2003-04/Season_Awards.md", "2003-04/All_Star.md", "2004-05/All_Star.md",
                              "2003-04/11_November/League_Awards.md", "2003-04/12_December/League_Awards.md",
                              "2003-04/01_January/League_Awards.md", "2003-04/04_April/League_Awards.md")]
ROM = ["2003-04-rookie_of_month-2003-10-28-west", "2003-04-rookie_of_month-2003-12-01-west",
       "2003-04-rookie_of_month-2004-01-01-west", "2003-04-rookie_of_month-2004-04-01-west"]


def read(root, rel):
    return json.loads((Path(root) / rel).read_text(encoding="utf-8"))


def write(root, rel, record):
    path = Path(root) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def as_recorded(record):
    """The record as it stood before any correction (the repository's own may already be corrected)."""
    for key in ("decisions", "steps"):
        if key in record:
            record[key] = [AC.superseded(i) for i in record[key]]
    return record


def scratch(tmp):
    for rel in RECORDS:
        write(tmp, rel, as_recorded(read(ROOT, rel)))
    for rel in PAGES + [LEAGUE / "player_registry.json"]:
        if (ROOT / rel).is_file():
            (Path(tmp) / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / rel, Path(tmp) / rel)


def item(root, kind, season, key):
    record = read(root, AC.record_path(kind, season))
    return next(i for i in record[AC.ITEMS[kind]] if AC._key(kind, i) == key or i.get("id") == key)


def names(rows):
    return [p["player"] for p in rows]


class CorrectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        scratch(cls.tmp)
        cls.before = {rel: read(cls.tmp, rel) for rel in RECORDS}
        cls.report = AC.apply(cls.tmp, DAY, world=ROOT)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def errors_for(self, rel, edit, keep=None, clock=DAY):
        """correction_errors over a copy of one corrected record, its items cut to the ids in `keep`, edited by `edit`."""
        kind, season = KINDS[RECORDS.index(rel)]
        record = read(self.tmp, rel)
        key = AC.ITEMS[kind]
        if keep:
            record[key] = [i for i in record[key] if AC._item_id(kind, season, i) in keep]
        edit(record[key])
        with tempfile.TemporaryDirectory() as other:
            write(other, rel, record)
            return AC.correction_errors(other, clock=clock, world=ROOT)

    def test_apply_gives_exactly_the_expected_changes(self):
        self.assertEqual([e["item"] for e in self.report["items"]],
                         ["2003-04-all_rookie", "2003-04-all-star-rookie_challenge", "2004-05-all-star-rookie_challenge"] + ROM)
        self.assertEqual([e["item"] for e in self.report["items"]], list(AC.CORRECTED))
        rookie = item(self.tmp, "season_awards", "2003-04", "all_rookie")
        first, second = rookie["teams"]
        self.assertEqual(names(second["players"]), ["Josh Howard", "Boris Diaw", "Jarvis Hayes", "Marquis Daniels", "Raül López"])
        self.assertEqual(AC.team_changes(rookie), [("Second Team", ["Marquis Daniels", "Raül López"], ["T.J. Ford", "Keith Bogans"])])
        self.assertIn("Dwyane Wade", names(first["players"]))
        self.assertEqual(set(rookie["correction"]["superseded"]), {"teams", "others"})
        roy = item(self.tmp, "season_awards", "2003-04", "roy")              # outside the approval: as recorded
        self.assertNotIn("correction", roy)
        self.assertEqual([(v["player"], v["points"]) for v in roy["tally"][:3]],
                         [("Dwyane Wade", 590), ("Carmelo Anthony", 250), ("LeBron James", 222)])
        rc03 = item(self.tmp, "all_star", "2003-04", "rookie_challenge")
        self.assertEqual(AC.team_changes(rc03), [("Rookies", ["Jarvis Hayes"], ["T.J. Ford"])])
        self.assertIn("hayesja01", [p["bbr_id"] for p in rc03["teams"]["Rookies"]])
        rc04 = item(self.tmp, "all_star", "2004-05", "rookie_challenge")
        (side, added, removed), = AC.team_changes(rc04)
        self.assertEqual((side, set(added), set(removed)), ("Rookies", {"Andrés Nocioni", "David Harrison", "Josh Smith"},
                                                            {"Maurice Baker", "Carlos Delfino", "Mario Kasun"}))
        positions = {p["player"]: p["position"] for p in rc04["teams"]["Rookies"]}
        self.assertEqual((positions["David Harrison"], positions["Ben Gordon"]), ("C", "G"))   # positions as corrected
        third = {d["id"]: (d["winner"], names(d["shortlist"])) for d in read(self.tmp, RECORDS[3])["decisions"] if d.get("correction")}
        self.assertEqual(third, {ROM[0]: ("Carmelo Anthony", ["Carmelo Anthony", "Josh Howard", "Marquis Daniels"]),
                                 ROM[1]: ("Carmelo Anthony", ["Carmelo Anthony", "Josh Howard", "Marquis Daniels"]),
                                 ROM[2]: ("Carmelo Anthony", ["Carmelo Anthony", "Josh Howard", "Marquis Daniels"]),
                                 ROM[3]: ("Carmelo Anthony", ["Carmelo Anthony", "Raül López", "Leandro Barbosa"])})
        # Every other item is untouched and every corrected one keeps its other fields; the block is dated and sourced.
        for (kind, season), rel in zip(KINDS, RECORDS):
            after = read(self.tmp, rel)
            key = AC.ITEMS[kind]
            for old, new in zip(self.before[rel][key], after[key]):
                if not new.get("correction"):
                    self.assertEqual(old, new)
                    continue
                c = new["correction"]
                self.assertEqual(c["corrected_on"], DAY)
                self.assertEqual(c["reason"], AC.REASONS[(kind, season, AC._key(kind, new))])
                self.assertIn("approved", c["reason"])
                self.assertEqual(AC.as_of(new, "2005-01-01"), old)
                self.assertEqual(list(new)[:-1], list(old))             # the keys keep their places
            self.assertEqual({k: v for k, v in after.items() if k != key}, {k: v for k, v in self.before[rel].items() if k != key})

    def test_wades_honors_stand(self):
        from runtime.season_awards import honors
        for rel in RECORDS[:1]:
            old = sorted(h for d in self.before[rel]["decisions"] for h in honors(d) if h[0] == "Dwyane Wade")
            new = sorted(h for d in read(self.tmp, rel)["decisions"] for h in honors(d) if h[0] == "Dwyane Wade")
            self.assertEqual(old, new)
        wins = lambda rel: [d["id"] for d in rel["decisions"] if d["winner"] == "Dwyane Wade"]
        self.assertEqual(wins(self.before[RECORDS[3]]), wins(read(self.tmp, RECORDS[3])))

    def test_a_second_run_changes_nothing(self):
        files = {rel: (Path(self.tmp) / rel).read_bytes() for rel in RECORDS + PAGES if (Path(self.tmp) / rel).is_file()}
        self.assertEqual(AC.apply(self.tmp, DAY, world=ROOT), {"items": [], "pages": []})
        self.assertEqual(files, {rel: (Path(self.tmp) / rel).read_bytes() for rel in files})

    def test_a_reader_dated_before_the_correction_reads_the_original(self):
        rookie = item(self.tmp, "season_awards", "2003-04", "all_rookie")
        original = next(d for d in self.before[RECORDS[0]]["decisions"] if d["award"] == "all_rookie")
        self.assertEqual(AC.as_of(rookie, "2004-07-01"), original)
        self.assertEqual(AC.as_of(rookie, DAY), rookie)
        self.assertEqual(AC.as_of(rookie, None), rookie)
        from runtime import followed_players
        self.assertIn(("2004-04-27", "All-Rookie Team: Second Team"), followed_players.honors(self.tmp, "T.J. Ford", "2003-04", "2005-06-30"))
        self.assertEqual(followed_players.honors(self.tmp, "T.J. Ford", "2003-04", DAY), [])
        self.assertIn(("2004-04-27", "All-Rookie Team: Second Team"), followed_players.honors(self.tmp, "Marquis Daniels", "2003-04", DAY))
        # The front office's honor premium (valuation): the 2004 summer market priced the honors as recorded.
        from runtime.valuation import Valuation
        v = object.__new__(Valuation)
        v.root, v.first, v.season = Path(self.tmp), False, "2004-05"
        for on, has, lacks in (("2004-07-01", "fordtj01", "daniema01"), (DAY, "daniema01", "fordtj01")):
            v.on = on
            honors = v._honors()
            self.assertIn("All-Rookie Second Team", honors.get(has, []), on)
            self.assertNotIn("All-Rookie Second Team", honors.get(lacks, []), on)

    def test_pages_and_cards_name_the_correction(self):
        page = lambda rel: (Path(self.tmp) / LEAGUE / rel).read_text(encoding="utf-8")
        text = page("2003-04/Season_Awards.md")
        self.assertIn("Corrected on 2006-01-01", text)
        self.assertIn("Second Team: Marquis Daniels and Raül López replace T.J. Ford and Keith Bogans", text)
        self.assertEqual(text.count("Corrected on"), 1)                  # the Rookie of the Year vote carries no note
        self.assertIn("Through 2004-06-20.", text)                     # the page keeps its own evidence date
        self.assertIn("Corrected on January 1, 2006 (award audit, approved by the user): Rookies: Jarvis Hayes replaces T.J. Ford",
                      page("2003-04/All_Star.md"))
        self.assertIn("Rookies: David Harrison, Andrés Nocioni and Josh Smith replace Maurice Baker, Carlos Delfino and Mario Kasun",
                      page("2004-05/All_Star.md"))
        april = page("2003-04/04_April/League_Awards.md")
        self.assertIn("| West | 2 | Raül López |", april)
        self.assertIn("(was Carmelo Anthony, Leandro Barbosa, Chris Kaman); the winner is unchanged", april)
        self.assertTrue(april.splitlines()[6].startswith("As of June 30, 2004"))   # the month line is the hub's
        # The league cards (league_cards.corrected_rows).
        rookie = item(self.tmp, "season_awards", "2003-04", "all_rookie")
        from runtime.league_cards import corrected_rows
        from runtime.season_awards import honors
        rows_of = lambda d: [(p, {"name": n, "rank": 1}) for p, n, _ in honors(d)]
        rows = {p: r for p, r in corrected_rows(rookie, DAY, rows_of)}
        self.assertEqual(rows["Marquis Daniels"]["corrected"], "corrected on 2006-01-01, superseding T.J. Ford, Keith Bogans")
        self.assertIsNone(rows["T.J. Ford"]["rank"])
        self.assertIn("Superseded by the correction of 2006-01-01", rows["T.J. Ford"]["superseded"])
        self.assertNotIn("corrected", rows["Josh Howard"])
        self.assertEqual({p for p, _ in corrected_rows(rookie, "2004-07-01", rows_of)},
                         {p for p, _ in rows_of(AC.superseded(rookie))})     # a card dated before reads the original

    def test_the_season_hub_shows_the_corrected_result(self):
        # The hub (award_pages) built from the repository with the corrected season records read in: the corrected
        # All-Rookie Second Team and its note on the clock, the facts its validation compares, the original before.
        from runtime import award_pages
        real = award_pages._read
        swap = {(ROOT / rel).resolve(): Path(self.tmp) / rel for rel in RECORDS[:2]}
        with mock.patch.object(award_pages, "_read", lambda path: real(swap.get(Path(path).resolve(), path))):
            m = award_pages.model("2003-04", ROOT, DAY)
            text = award_pages.season_page("2003-04", ROOT, DAY, m)
            earlier = award_pages.model("2003-04", ROOT, "2005-12-31")
        self.assertIn("Corrected on January 1, 2006 (award audit, approved by the user): Second Team: Marquis Daniels and Raül "
                      "López replace T.J. Ford and Keith Bogans", text)
        self.assertEqual(text.count("Corrected on"), 1)
        hub = award_pages.page_facts(text)
        self.assertEqual(award_pages.facts(m), hub)
        second = hub["All-Rookie teams"]["Second"]
        self.assertLessEqual({"Marquis Daniels", "Raül López"}, set(second))
        self.assertTrue({"T.J. Ford", "Keith Bogans"}.isdisjoint(second))
        self.assertNotIn("correction", earlier.decided["all_rookie"])         # the clock before reads the original
        self.assertIn("T.J. Ford", names(earlier.decided["all_rookie"]["teams"][1]["players"]))

    def test_validation_passes_after_apply_and_refuses_a_hand_edit(self):
        self.assertEqual(AC.correction_errors(self.tmp, clock=DAY, world=ROOT), [])

        def edit(items):
            rookie = next(d for d in items if d["award"] == "all_rookie")
            rookie["teams"][1]["players"][3]["points"] = 30                # a corrected value edited by hand
        errors = self.errors_for(RECORDS[0], edit, keep={"2003-04-all_rookie"})
        self.assertEqual(len(errors), 2, errors)
        self.assertIn("2003-04-all_rookie: the corrected values (teams, others) are not the ones the user approved", errors[0])
        self.assertIn("2003-04-all_rookie: corrected teams differ from what the current code re-decides", errors[1])
        late = self.errors_for(RECORDS[3], lambda items: None, keep=ROM[:1], clock="2005-12-31")
        self.assertTrue(any("after the career clock" in e for e in late), late)

    def test_a_correction_outside_the_approval_is_refused(self):
        # A correction block on an item the user never approved (the MVP), with made-up superseded values.
        def edit(items):
            items[0]["correction"] = {"corrected_on": DAY, "reason": "made up", "superseded": {"winners": ["Somebody Else"]}}
        errors = self.errors_for(RECORDS[0], edit, keep={"2003-04-mvp"})
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("2003-04-mvp: carries a correction the user did not approve", errors[0])

    def test_a_superseded_winner_is_refused(self):
        # A hand-added superseded winner on a corrected Rookie of the Month decision: a reader dated before would see it.
        def edit(items):
            items[0]["correction"]["superseded"]["winner"] = "Somebody Else"
        errors = self.errors_for(RECORDS[3], edit, keep=ROM[:1])
        self.assertTrue(any("are not the ones the user approved correcting" in e for e in errors), errors)
        self.assertTrue(any("the re-decided winner would be Carmelo Anthony, not the recorded Somebody Else" in e
                            for e in errors), errors)

    def test_a_backdated_correction_or_another_reason_is_refused(self):
        def edit(items):
            items[0]["correction"].update(corrected_on="2004-05-01", reason="another reason")
        errors = self.errors_for(RECORDS[0], edit, keep={"2003-04-all_rookie"})
        self.assertTrue(any("correction dated 2004-05-01, before 2006-01-01" in e for e in errors), errors)
        self.assertTrue(any("not the approved one" in e for e in errors), errors)

    def test_a_block_without_reason_or_superseded_values_is_refused(self):
        def edit(items):
            items[0]["correction"] = {"corrected_on": DAY, "reason": " ", "superseded": {}}
        errors = self.errors_for(RECORDS[3], edit, keep=ROM[:1])
        self.assertTrue(any("not the approved one" in e for e in errors), errors)
        self.assertTrue(any("keeps no superseded values" in e for e in errors), errors)

    def test_plan_and_apply_refuse_what_the_user_did_not_approve(self):
        with self.assertRaisesRegex(AC.CorrectionRefused, "2003-04-roy: not a correction the user approved"):
            AC.plan(self.tmp, DAY, ROOT, targets=["2003-04-roy"])
        with self.assertRaisesRegex(AC.CorrectionRefused, "before 2006-01-01"):
            AC.plan(self.tmp, "2004-05-01", ROOT)
        from runtime.write_back import clock
        other = "2006-01-02" if clock(ROOT) == "2005-12-31" else "2005-12-31"
        with self.assertRaisesRegex(AC.CorrectionRefused, "not dated by the career clock"):
            AC.apply(ROOT, other, write=False)                           # refused before any re-decision or write

    def test_a_changed_monthly_winner_is_refused(self):
        d = {"id": "x", "winner": "Somebody Else"}
        with self.assertRaises(AC.CorrectionRefused):
            AC._guard("award_decisions", "2003-04", d, {"winner": "Carmelo Anthony", "shortlist": []})


class ReaderTests(unittest.TestCase):
    def test_as_of_without_a_correction_is_the_item(self):
        d = {"id": "x", "winners": ["A"]}
        self.assertIs(AC.as_of(d, "2004-01-01"), d)
        self.assertIs(AC.superseded(d), d)
        self.assertIsNone(AC.note(d))

    def test_as_of_restores_the_superseded_fields_in_place(self):
        d = {"id": "x", "shortlist": [{"player": "B"}], "winner": "A",
             "correction": {"corrected_on": "2006-01-01", "reason": "r", "superseded": {"shortlist": [{"player": "C"}]}}}
        before = AC.as_of(d, "2005-12-31")
        self.assertEqual(before, {"id": "x", "shortlist": [{"player": "C"}], "winner": "A"})
        self.assertEqual(list(before), ["id", "shortlist", "winner"])
        self.assertIs(AC.as_of(d, "2006-01-01"), d)
        self.assertEqual(AC.summary(d), ["shortlist B (was C); the winner is unchanged"])

    def test_every_approved_item_has_its_reason_and_the_rookie_of_the_year_is_not_one(self):
        self.assertEqual({tuple(v[:3]) for v in AC.CORRECTED.values()}, set(AC.REASONS))
        self.assertNotIn("2003-04-roy", AC.CORRECTED)


if __name__ == "__main__":
    unittest.main()
