"""The 2006 offseason library data (roadmap R5, F1): the 2005 files' schema, every date inside its publication gate,
the class the draft reads (P.J. Tucker, a declared early entrant, treated like every other prospect; SI.com's stated
omissions; InsideHoops' unordered second-round groups), a draft order that honours Miami's simulated trade of its 2006
first-round pick and the seconds given on the simulated 2005 draft night, and the published 2006-07 maximums."""
import json
import os
from pathlib import Path
import statistics
import tempfile
import unittest
from unittest import mock

from runtime import draft as D
from runtime import draft_rights, lottery
from runtime import free_agency_2004 as F
from runtime.cba import minimum_salary

ROOT = Path(__file__).resolve().parents[1]
DRAFT_DATE = "2006-06-28"
TUCKER = "tuckepj01"
SI = "si_com_2006_06_14"
# The 2006 seconds given on the simulated 2005 draft night (draft_2005.json `trades`): {(round, original): receiver}.
SECONDS = {(2, "DET"): "POR", (2, "SAC"): "PHO", (2, "BOS"): "MIN", (2, "UTA"): "LAL", (2, "LAL"): "DET", (2, "DAL"): "MIN"}
DRAFT_2005 = "career/Dwyane_Wade/2004-05/09_Draft/draft_2005.json"


def lib(year, kind):
    return json.loads((ROOT / f"library/{year}/league/nba_{year}_{kind}.json").read_text(encoding="utf-8"))


def value(entry):
    return entry["value"] if isinstance(entry, dict) else entry


class SchemaTests(unittest.TestCase):
    def test_every_2005_key_is_kept(self):
        """Each 2006 file has its 2005 counterpart's kind, schema version and top-level keys (the calendar's keys
        with the year renamed; its 2005 agreement events, the agreement in principle and ratification, are 2005's)."""
        for kind in ("lottery_rules", "pick_ownership", "draft_class", "prospect_evidence", "predraft_boards",
                     "service_years", "offseason_calendar"):
            with self.subTest(kind=kind):
                old, new = lib(2005, kind), lib(2006, kind)
                self.assertEqual((new["schema_version"], new["kind"]), (old["schema_version"], old["kind"]))
                keys = {k.replace("2005_06", "2006_07").replace("2005", "2006") for k in old}
                if kind == "offseason_calendar":
                    keys -= {"cba_agreement_in_principle", "cba_ratified"}
                self.assertEqual(keys - set(new), set())

    def test_the_calendar_carries_what_the_readers_take(self):
        cal = lib(2006, "offseason_calendar")
        self.assertEqual(value(cal["draft"]), DRAFT_DATE)
        self.assertEqual(value(cal["salary_cap_2006_07"]), 53_135_000)
        self.assertEqual(value(cal["luxury_tax_threshold_2006_07"]), 65_420_000)
        self.assertEqual(value(cal["salary_floor_2006_07"]), round(0.75 * 53_135_000))
        self.assertEqual(value(cal["charlotte_cap_and_floor_2006_07"]), {"cap": 53_135_000, "floor": 39_851_250})
        scale = value(cal["minimum_salary_scale_2006_07"])
        for years in range(11):                     # the 2005 agreement's scale file gives the same 2006-07 figures
            self.assertEqual(scale["10+" if years == 10 else str(years)], minimum_salary(years, "2006-07", ROOT))
        rookie = value(cal["rookie_scale_2006_first_round"])
        self.assertEqual([r["pick"] for r in rookie], list(range(1, 31)))
        self.assertEqual(rookie[0]["year1"], 3_751_000)                          # cbafaq05, pick 1
        self.assertEqual(sorted((r["year1"] for r in rookie), reverse=True), [r["year1"] for r in rookie])
        self.assertIsNone(value(cal["expansion_draft"]))

    def test_the_offseason_readers_take_the_2006_files(self):
        y = lottery.Year(2006, ROOT)
        self.assertEqual((y.lottery_date, y.season, y.next_season), ("2006-05-23", "2005-06", "2006-07"))
        for rel in (y.rules_path, y.ownership_path, y.rosters_path):
            self.assertTrue((ROOT / rel).is_file(), rel)
        with D.year_context(2006, ROOT):
            self.assertEqual((D.YEAR, D.SEASON, D.DRAFT_DATE), (2006, "2005-06", DRAFT_DATE))
            self.assertEqual(D.BOARDS.as_posix(), "library/2006/league/nba_2006_predraft_boards.json")
            self.assertEqual(set(D.RESEARCH_MOCKS), {"nbadraft_net_2006_06_10", "si_com_2006_06_14",
                                                     "espn_ford_top45_2006_06_15", "draftexpress_2006_06_27"})
        self.assertEqual((D.YEAR, D.DRAFT_DATE), (2004, "2004-06-24"))            # 2004 replays with its constants
        with F.year_context(2006, ROOT):
            self.assertEqual((F.OPTIONS_DATE, F.OPEN, F.SIGN_FROM, F.CAP_KNOWN), ("2006-06-30", "2006-07-01", "2006-07-12", "2006-07-11"))
            self.assertEqual(F.SERVICE.as_posix(), "library/2006/league/nba_2006_service_years.json")
            self.assertEqual(F.rounds()[F.signing_week()], "2006-07-15")
            cal = F.calendar(ROOT)
            self.assertEqual((cal["cap"], cal["tax"], cal["mle"], cal["charlotte_cap"]), (53_135_000, 65_420_000, 5_215_000, 53_135_000))
            self.assertEqual((cal["minimum"][0], cal["minimum"][10], len(cal["scale"])), (412_718, 1_178_348, 30))
        self.assertEqual(draft_rights.draft_date(2006, ROOT), DRAFT_DATE)

    def test_service_years_add_the_closed_season(self):
        old, new = lib(2005, "service_years")["players"], lib(2006, "service_years")["players"]
        for b, row in old.items():
            self.assertEqual(new[b], {"first_season": row["first_season"], "seasons_through_2005_06": row["seasons_through_2004_05"] + 1})
        self.assertEqual({r["first_season"] for b, r in new.items() if b not in old}, {"2005-06"})
        self.assertNotIn(TUCKER, new)                                             # debuted 2006-07: not listed
        self.assertEqual(new["wadedw01"]["seasons_through_2005_06"], 3)


class PublicationGateTests(unittest.TestCase):
    def test_calendar_dates_fall_in_order(self):
        cal = lib(2006, "offseason_calendar")
        order = [value(cal[k]) for k in ("early_entry_application_deadline", "draft_lottery", "predraft_camp")]
        order += [cal["predraft_camp"]["end"]]
        order += [value(cal[k]) for k in ("early_entry_withdrawal_deadline", "early_entry_final_list", "draft",
                                          "options_and_qualifying_offers_deadline", "free_agency_negotiation_opens",
                                          "cap_published", "first_signing_and_trade_date", "regular_season_2006_07_opens")]
        self.assertEqual(order, sorted(order))
        self.assertEqual(lib(2006, "lottery_rules")["lottery_date"], value(cal["draft_lottery"]))

    def test_the_cap_is_live_only_from_its_publication(self):
        cal = lib(2006, "offseason_calendar")
        with F.year_context(2006, ROOT):
            self.assertEqual(F.CAP_KNOWN, value(cal["cap_published"]))
        history = json.loads((ROOT / "career/Dwyane_Wade/2005-06/00_Team/Finances/league_cap_history.json").read_text(encoding="utf-8"))
        row = next(r for r in history["seasons"] if r["season"] == "2006-07")
        self.assertEqual((row["published_date"], row["salary_cap"]), (value(cal["cap_published"]), value(cal["salary_cap_2006_07"])))

    def test_draft_evidence_was_published_before_the_draft(self):
        evidence, boards = lib(2006, "prospect_evidence"), lib(2006, "predraft_boards")
        for data in (evidence, boards):
            self.assertTrue(data["evidence_cutoff"].startswith(DRAFT_DATE))
        register = json.loads((ROOT / "library/2006/league/sources/nba_2006_draft_research_sources.json").read_text(encoding="utf-8"))
        published = [s["published"] for s in evidence["ranking_sources"]] + [b["published"] for b in boards["boards"].values()]
        published += [s["published"] for s in register["pre_draft_evidence"] if s.get("published")]
        self.assertTrue(published and all(p <= DRAFT_DATE for p in published), published)
        self.assertLessEqual(lib(2006, "offseason_calendar")["predraft_camp"]["end"], DRAFT_DATE)
        rows = evidence["players_drafted"] + evidence["undrafted_candidates"]["players"]
        self.assertEqual({r["last_pre_draft_season"]["season"] for r in rows}, {"2005-06"})
        self.assertEqual(lib(2006, "draft_class")["available_from"], DRAFT_DATE)

    def test_the_board_reads_pre_draft_evidence_only(self):
        """The board is the same from the evidence alone with every real-draft field taken out (the actual pick, the
        draft status, the stored consensus) and the drafted and undrafted rows merged in another order: nothing in it
        reads the real picks, the lottery or who was drafted."""
        with D.year_context(2006, ROOT):
            expected = D.prospects(ROOT)
            ev = lib(2006, "prospect_evidence")
            rows = ev["players_drafted"] + ev["undrafted_candidates"]["players"]
            for r in rows:
                r.pop("world_data_not_pre_draft", None)
                r.pop("draft_status", None)
                for k in ("consensus_mock_mean_slot", "consensus_rank", "consensus_status"):
                    r["pre_draft_rankings"].pop(k)
            ev["players_drafted"] = rows[1::2][::-1] + rows[::2]
            ev["undrafted_candidates"]["players"] = []
            with tempfile.TemporaryDirectory() as tmp:
                (Path(tmp) / D.EVIDENCE).parent.mkdir(parents=True)
                (Path(tmp) / D.EVIDENCE).write_text(json.dumps(ev), encoding="utf-8")
                os.symlink(ROOT / D.BOARDS, Path(tmp) / D.BOARDS)
                stripped = D.prospects(tmp)
            self.assertEqual(stripped, expected)
            self.assertEqual(D.tiers(stripped), D.tiers(expected))


class ClassTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(D.year_context(2006, ROOT))
        self.pool = D.prospects(ROOT)
        self.evidence = lib(2006, "prospect_evidence")

    def test_the_class_and_its_tiers(self):
        rows = self.evidence["players_drafted"] + self.evidence["undrafted_candidates"]["players"]
        self.assertEqual(len(self.pool), len(rows))
        tiers = D.tiers(self.pool)
        self.assertEqual(min(tiers.values()), 1)
        self.assertTrue(all(1 <= p["consensus"] <= 61 for p in self.pool.values()))
        withdrawn = {D._key(p["player_id"]) for p in self.evidence["withdrawn_before_draft"]["players"]}
        self.assertTrue(withdrawn)
        self.assertFalse(withdrawn & set(self.pool))

    def test_tucker_is_a_declared_entrant_like_any_other(self):
        """He stayed in the draft (the NBA's June 19, 2006 list of remaining early entrants), so he is in the pool
        with his 2005-06 Texas line and the consensus every prospect gets: the mean of the eight sources' slots, an
        absent player taking each source's unlisted rank."""
        [key] = [k for k, p in self.pool.items() if p["bbr_id"] == TUCKER]
        withdrawn = {p["player_id"] for p in self.evidence["withdrawn_before_draft"]["players"]}
        self.assertNotIn("P.J. Tucker", withdrawn)
        row = next(r for r in self.evidence["players_drafted"] + self.evidence["undrafted_candidates"]["players"]
                   if r.get("bbr_id") == TUCKER)
        self.assertEqual((row["college_class"], row["last_pre_draft_season"]["team"], row["last_pre_draft_season"]["games"]),
                         ("JR", "Texas", 37))
        ranks = row["pre_draft_rankings"]
        slots = [ranks[k] if isinstance(ranks.get(k), int) else miss for k, miss in D.RESEARCH_MOCKS.items()]
        slots += [b["rank_by_player"].get("P.J. Tucker", 31) for b in lib(2006, "predraft_boards")["boards"].values()]
        self.assertEqual(len(slots), 8)
        self.assertEqual(self.pool[key]["consensus"], round(statistics.mean(slots), 2))
        self.assertEqual(self.pool[key]["stats"]["games"], 37)

    def test_the_stored_consensus_is_the_drafts_own(self):
        """The evidence file's consensus slot and rank are what runtime/draft.py computes (ties by the DraftExpress
        June 27 slot, then by name)."""
        rows = self.evidence["players_drafted"] + self.evidence["undrafted_candidates"]["players"]
        dx = lambda r: r["pre_draft_rankings"]["draftexpress_2006_06_27"] or 61
        order = sorted(rows, key=lambda r: (self.pool[D._key(r["player_id"])]["consensus"], dx(r), r["player_id"]))
        for rank, r in enumerate(order, 1):
            rk = r["pre_draft_rankings"]
            self.assertEqual((rk["consensus_mock_mean_slot"], rk["consensus_rank"]),
                             (self.pool[D._key(r["player_id"])]["consensus"], rank), r["player_id"])

    def test_si_omissions_are_not_rankings(self):
        """SI.com's last mock before the withdrawal deadline left out early entrants it expected to withdraw (Lowry and
        Gibson by name, the international candidates as a group): for the seven still in the draft its absence is left
        out of the mean instead of counting 61. Every other absence, the four unnamed college early entrants included,
        keeps the unlisted slot."""
        rows = self.evidence["players_drafted"] + self.evidence["undrafted_candidates"]["players"]
        marked = {r["player_id"]: r["pre_draft_rankings"][D.OMISSIONS] for r in rows if r["pre_draft_rankings"].get(D.OMISSIONS)}
        self.assertEqual(set(marked), {"Kyle Lowry", "Daniel Gibson", "Joel Freeland", "Kosta Perović", "Lior Eliyahu",
                                       "Ejike Ugboaja", "Damir Markota"})
        boards = lib(2006, "predraft_boards")["boards"].values()
        for r in rows:
            ranks = r["pre_draft_rankings"]
            skip = set(ranks.get(D.OMISSIONS) or {})
            self.assertEqual(skip, {SI} if r["player_id"] in marked else set())
            self.assertTrue(all(ranks[k] is None for k in skip))            # an omission, never a listed slot
            slots = [ranks[k] if isinstance(ranks[k], int) else miss for k, miss in D.RESEARCH_MOCKS.items() if k not in skip]
            slots += [b["rank_by_player"].get(D._board_name(b, r), 31) for b in boards]
            self.assertEqual(self.pool[D._key(r["player_id"])]["consensus"], round(statistics.mean(slots), 2), r["player_id"])
        self.assertEqual(self.pool[D._key("Kyle Lowry")]["consensus"], 22.71)
        for name in ("Will Blalock", "Thomas Gardner", "Paul Millsap", "J.R. Pinnock"):
            self.assertNotIn(name, marked)
        with D.year_context(2005, ROOT):                                      # no rule before OMISSIONS_FROM
            self.assertLess(D.YEAR, D.OMISSIONS_FROM)

    def test_every_name_in_the_unordered_groups_is_in_the_class_or_withdrew(self):
        """InsideHoops' two unordered second-round groups project the players they name: each is in the pool or listed
        as withdrawn (Afflalo, Bobby Brown and Newley withdrew; Horton, Adeleke, Grunfeld and Di Pacce Dos Santos were
        eligible and are undrafted candidates, unlisted by every source's slots)."""
        src = next(s for s in self.evidence["ranking_sources"] if s["id"] == "insidehoops_2006_06_14")
        groups = src["unordered_second_round_groups"]
        printed = {"Louis Amundson": "Lou Amundson", "Kevin Pittsnoogle": "Kevin Pittsnogle", "PJ Tucker": "P.J. Tucker",
                   "Leonardo Di Pacce Santos": "Leonardo Di Pacce Dos Santos", "Jose Juan Barea": "J.J. Barea",
                   "Danny Grunfeld": "Dan Grunfeld"}
        withdrawn = {D._key(p["player_id"]) for p in self.evidence["withdrawn_before_draft"]["players"]}
        for name in groups["upper_second_round"] + groups["rest_of_second_round"]:
            key = D._key(printed.get(name, name))
            self.assertTrue(key in self.pool or key in withdrawn, name)
        for name in ("Arron Afflalo", "Bobby Brown", "Brad Newley"):
            self.assertIn(D._key(name), withdrawn)
        for name in ("Daniel Horton", "Kenny Adeleke", "Dan Grunfeld", "Leonardo Di Pacce Dos Santos"):
            self.assertEqual(self.pool[D._key(name)]["consensus"], 44.12)

    def test_wades_requests_name_class_players(self):
        rows = D.wade_requests(ROOT, self.pool)
        self.assertEqual({(r["bbr_id"], r["requested"]) for r in rows}, {("lowryky01", "evaluate"), (TUCKER, "draft")})
        self.assertTrue(all(D.match_prospect(r, self.pool) for r in rows))


class OwnershipTests(unittest.TestCase):
    def setUp(self):
        self.y = lottery.Year(2006, ROOT)
        self.code = lottery.codes(ROOT, self.y)
        self.table = lottery.records(ROOT, self.y)

    def test_miamis_first_goes_to_the_hornets_by_its_ledger(self):
        """The activation-dated ownership file keeps Miami's own picks; Miami's ledger records the 2006-01-16 trade."""
        own = lib(2006, "pick_ownership")
        self.assertEqual((own["round_1"]["MIA"]["owner"], own["round_2"]["MIA"]["owner"], own["as_of"]), ("MIA", "MIA", "2003-12-03"))
        self.assertEqual(lottery.miami_pick_trades(ROOT, "2005-06", 2006, self.code), {(1, "MIA"): "NOK"})

    def order(self, washington_drawn):
        """The 2006 order with a stand-in field (the sixteen best records) and stand-in draws: Washington wins No. 1,
        or the three picks go to the next clubs by seed so Washington falls to No. 4."""
        field = set(sorted(self.table, key=lambda c: -self.table[c]["pct"])[:16])
        self.assertNotIn("Washington Wizards", field)

        def draw(root, packet, y=None):
            options = sorted(packet["options"], key=lambda c: (-packet["options"][c], c))
            if "lottery-pick" in packet["event_id"]:
                others = [c for c in options if c != "Washington Wizards"]
                return "Washington Wizards" if washington_drawn and "Washington Wizards" in options else others[0]
            return options[0]

        with mock.patch.object(lottery, "playoff_clubs", lambda root=None, y=None: field), mock.patch.object(lottery, "_draw", draw):
            return lottery.build(ROOT, 2006)

    def test_the_order_conveys_each_pick_to_its_holder(self):
        for drawn in (True, False):
            with self.subTest(washington_drawn=drawn):
                record = self.order(drawn)
                picks = {(p["round"], p["original"]): p for p in record["picks"]}
                self.assertEqual((len(record["picks"]), sum(p["round"] == 1 for p in record["picks"])), (60, 30))
                self.assertEqual(picks[(1, "MIA")]["owner"], "NOK")           # the simulated 2006-01-16 trade
                self.assertEqual(picks[(2, "MIA")]["owner"], "MIA")
                self.assertEqual(picks[(1, "LAC")]["owner"], "DEN")           # unprotected in 2006
                self.assertEqual(picks[(2, "CHI")]["owner"], "UTA")
                was = picks[(1, "WAS")]                                       # protected 1-3 in 2006
                self.assertEqual((was["pick"], was["owner"]), (1, "WAS") if drawn else (4, "ORL"))
                moved = {k: p["owner"] for k, p in picks.items() if p["owner"] != p["original"]}
                self.assertEqual(moved, {(1, "MIA"): "NOK", (1, "LAC"): "DEN", (2, "CHI"): "UTA", **SECONDS,
                                         **({} if drawn else {(1, "WAS"): "ORL"})})
                self.assertEqual({(2, s["original"]): s["owner"] for s in record["draft_night_seconds"]}, SECONDS)
                self.assertEqual({s["source"] for s in record["draft_night_seconds"]}, {DRAFT_2005})

    def test_the_seconds_are_the_2005_draft_nights(self):
        """Each conveyed second is one the moving-up club added in a recorded 2005 trade, given to the club moving down;
        none of the six had left its club by a real trade before activation. Before 2006 nothing is conveyed."""
        trades = json.loads((ROOT / DRAFT_2005).read_text(encoding="utf-8"))["trades"]
        self.assertEqual({(2, self.code[t["to"]]): self.code[t["from"]] for t in trades}, SECONDS)
        self.assertTrue(all(t["plus"] == f"{t['to']} 2006 second-round pick" for t in trades))
        own = lib(2006, "pick_ownership")["round_2"]
        self.assertTrue(all(own.get(c, {}).get("owner", c) == c for _, c in SECONDS))
        self.assertEqual({k: v[0] for k, v in lottery.draft_night_seconds(ROOT, 2006, self.code).items()}, SECONDS)
        self.assertEqual(lottery.draft_night_seconds(ROOT, 2005, self.code), {})

    def test_an_order_written_before_the_rule_gains_the_seconds_before_the_draft(self):
        """The live driver may write the order on 2006-05-23 before this rule reaches it: the next offseason day gives it
        the seconds (once), and never after the draft's first draw."""
        full = self.order(False)
        names = lottery._names(ROOT, self.y)
        bare = json.loads(json.dumps(full))
        del bare["draft_night_seconds"]
        for s in bare["picks"]:
            if (s["round"], s["original"]) in SECONDS:
                s["owner"], s["owner_club"] = s["original"], names[s["original"]]
        with tempfile.TemporaryDirectory() as tmp:
            for rel in (self.y.rosters_path, Path(DRAFT_2005)):
                (Path(tmp) / rel).parent.mkdir(parents=True, exist_ok=True)
                os.symlink(ROOT / rel, Path(tmp) / rel)
            written = Path(tmp) / self.y.record
            written.parent.mkdir(parents=True, exist_ok=True)
            written.write_text(json.dumps(bare), encoding="utf-8")
            with mock.patch.object(lottery, "Year", lambda year, root=None: self.y):
                self.assertIsNone(lottery.run(tmp, "2006-06-01", 2006))
            self.assertEqual(json.loads(written.read_text(encoding="utf-8")), full)
            self.assertEqual(lottery._convey_written(tmp, self.y), [])                     # once
            written.write_text(json.dumps(bare), encoding="utf-8")
            draws = Path(tmp) / self.y.folder / "Draft_Draws"
            draws.mkdir()
            (draws / "2006-draft-pick-1.decision.json").write_text("{}", encoding="utf-8")
            self.assertEqual(lottery._convey_written(tmp, self.y), [])                     # the draft has begun
            self.assertEqual(json.loads(written.read_text(encoding="utf-8")), bare)
            self.assertEqual(lottery._convey_written(tmp, lottery.Year(2005, ROOT)), [])   # 2005 stands as recorded


class MaximumTests(unittest.TestCase):
    def test_the_market_prices_at_the_published_maximums(self):
        """From the 2006 summer the market's maximums are the figures published with the 2006-07 cap, not the
        agreement's 25/30/35% of that cap; the 2005 summer keeps the agreement's fixed 2005-06 figures."""
        published = {"0_to_6_years": 12_455_000, "7_to_9_years": 14_946_000, "10_plus_years": 17_437_000}
        rules = json.loads((ROOT / "library/2006/league/nba_2006_07_cap_rules.json").read_text(encoding="utf-8"))
        self.assertEqual(rules["maximum_salary"], published)
        with F.year_context(2006, ROOT):
            cal = F.calendar(ROOT)
            self.assertEqual(cal["maximum"], published)
            self.assertEqual([F.maximum(s, cal["cap"], cal["maximum"]) for s in (3, 8, 12)], [12_455_000, 14_946_000, 17_437_000])
            self.assertEqual(F.maximum(3, cal["cap"]), round(0.25 * 53_135_000))    # the share the market no longer uses
        with F.year_context(2005, ROOT):
            cal = F.calendar(ROOT)
            self.assertNotIn("maximum", cal)
            self.assertEqual([F.maximum(s, cal["cap"], cal.get("maximum")) for s in (3, 8, 12)], [12_000_000, 14_400_000, 16_800_000])


if __name__ == "__main__":
    unittest.main()
