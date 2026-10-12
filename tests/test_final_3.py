"""Final audit of 2006-06-20, group 3 (positions): R2, R6 and X-5 of the integration review.

From 2006-06-21 a writer that records a Miami player's position stops when no source gives one (`required_position`),
so every player the 2006 summer can place, and every player Miami can trade for, needs a position in each reader that
records one; and a registry row whose position no source records reads as none in every reader after the same date.
The record tests read the repository's committed records (read-only); every recorded decision reads as it did.
"""
from functools import lru_cache
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest import mock

from tests import live_season

ROOT = Path(__file__).resolve().parents[1]
CAREER = ROOT / "career/Dwyane_Wade"
UNATTACHED = ROOT / "library/2006/league/nba_2006_unattached_identities.json"
THREE = {"barroea01": "C", "hitero01": "SG", "quinnch01": "PG"}      # Earl Barron, Robert Hite, Chris Quinn
UNSOURCED = ("fitchge01", "walshma01")                                 # Gerald Fitch, Matt Walsh: registry slot only
AFTER = "2006-10-02"                                                   # a 2006-07 day, after the rollover


def pinned(season):
    """The live season pinned to `season` (`seasons.active`), as it stands once that season's rollover has run."""
    return mock.patch.dict(os.environ, {"CAREER_TEST_SEASON": season})


def register(season):
    return json.loads((CAREER / season / "00_Team/Team/Roster/roster.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def summer():
    """The 2006 summer pool as the market builds it on 2006-06-30 (stopped before its first draw), the market's group
    for the three, the coming rollover's identities and the 2006-07 real rosters' players."""
    from runtime import free_agency_2004 as fa
    from runtime.rollover import Rollover
    with live_season():
        with fa.year_context(2006, ROOT):
            market = fa.Market(ROOT, "2006-06-30")
            pool = sorted(b for b in market.roles if b not in market.book["contracts"] and b != "dwyane_wade")
            groups = {b: market.group(b) for b in THREE}
        coming = Rollover(ROOT)                          # the 2006 rollover, whatever season the career has reached
        coming.old, coming.new, coming.year = "2005-06", "2006-07", 2006
        coming.old_dir = CAREER / "2005-06"
        coming.old_team = coming.old_dir / "00_Team"
        rollover = coming.identities()
    rosters = json.loads((ROOT / "library/2006/league/nba_2006_07_team_rosters.json").read_text(encoding="utf-8"))
    rostered = sorted({p["bbr_id"] for c in rosters["clubs"].values() for p in c["players"] if p.get("bbr_id")})
    return SimpleNamespace(pool=pool, groups=groups, rollover=rollover, rostered=rostered)


class SummerPool(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        found = summer()
        cls.pool, cls.groups, cls.rollover, cls.rostered = found.pool, found.groups, found.rollover, found.rostered


class UnattachedIdentities2006(SummerPool):
    """R2: Barron, Hite and Quinn are in the 2006 pool with no registry row, no prospect evidence and no roster file that
    lists them (rule 1 strips real Miami's players), so no reader had a position for them."""

    def test_the_library_file_records_each_with_its_source(self):
        data = json.loads(UNATTACHED.read_text(encoding="utf-8"))
        births = json.loads((ROOT / "library/careers/nba_player_births.json").read_text(encoding="utf-8"))["players"]
        rows = {p["bbr_id"]: p for p in data["players"]}
        self.assertEqual({b: p["position"] for b, p in rows.items()}, THREE)
        for b, p in rows.items():
            self.assertEqual(p["birth_date"], births[b]["birth_date"])
            self.assertEqual(p["page_url"], births[b]["source"])
            self.assertEqual((p["player_id"], p["name"]), (births[b]["name"], births[b]["name"]))
            self.assertEqual(p["position_status"], "verified")
        self.assertEqual({b: p["nba_seasons_before_2006_07"] for b, p in rows.items()}, {"barroea01": 1, "hitero01": 0, "quinnch01": 0})

    def test_the_2006_market_reads_it_and_the_recorded_summers_do_not(self):
        from runtime import free_agency_2004 as fa
        ident = fa.identity(ROOT, 2006)
        self.assertEqual({b: ident[b]["position"] for b in THREE}, THREE)
        self.assertEqual(ident["barroea01"]["service"], 1)                       # the 2006 service file, as every pool player
        self.assertEqual(self.groups, {"barroea01": "C", "hitero01": "G", "quinnch01": "G"})    # was "F" for all three
        for year, on in ((2004, "2004-07-01"), (2005, "2005-07-01"), (2005, "2005-09-30"), (2005, None)):
            self.assertFalse(set(THREE) & set(fa.identity(ROOT, year, on=on)), (year, on))   # the 2005 market priced Barron as F

    def test_league_identity_reads_every_summers_unattached_identities(self):
        from runtime.signing import league_identity
        for b, pos in THREE.items():
            found = league_identity(ROOT, b)
            self.assertEqual((found["position"], found["club"]), (pos, None))
        self.assertEqual(league_identity(ROOT, "hasleud01")["position"], "PF")    # the 2003 file as before

    def test_the_rollover_positions_every_pool_player(self):
        self.assertEqual({b: self.rollover[b]["position"] for b in THREE}, THREE)
        self.assertEqual([b for b in self.pool if not (self.rollover.get(b) or {}).get("position")], [])


class SourcedPositions(SummerPool):
    """R6: from 2006-06-21 a writer needs a position; the league identity falls back to the live season's sources."""

    def test_every_real_roster_and_pool_player_has_a_position(self):
        from runtime.signing import league_identity
        with pinned("2006-07"):
            missing = [b for b in sorted(set(self.rostered) | set(self.pool))
                       if not league_identity(ROOT, b, on=AFTER).get("position")]
        self.assertEqual(missing, [])
        self.assertEqual([b for b in self.rostered if not (self.rollover.get(b) or {}).get("position")], [])

    def test_through_the_clock_the_recorded_answer_stands(self):
        """Kelenna Azubuike's only source is the 2006-07 roster: every earlier writer read no position (the "SF" guess)."""
        from runtime.miami_register import required_position
        from runtime.signing import league_identity
        with pinned("2006-07"):
            self.assertIsNone(league_identity(ROOT, "azubuke01", on="2006-06-20").get("position"))
            self.assertEqual(required_position(league_identity(ROOT, "azubuke01", on="2006-06-20").get("position"),
                                               "2006-06-20", "Kelenna Azubuike"), "SF")
            self.assertEqual(league_identity(ROOT, "azubuke01", on=AFTER)["position"], "SG")

    def test_only_a_player_no_source_records_stops_a_writer(self):
        from runtime.miami_register import required_position
        from runtime.signing import league_identity
        with pinned("2006-07"):
            for b in UNSOURCED:
                with self.assertRaises(ValueError):
                    required_position(league_identity(ROOT, b, on=AFTER).get("position"), AFTER, b)

    def test_a_departure_reads_his_register_row_first(self):
        from runtime.signing import departure_position
        roster = register("2005-06")
        telfair = next(p for p in roster["players"] if p["name"] == "Sebastian Telfair")
        self.assertEqual(departure_position(ROOT, roster, telfair["name"], telfair["bbr_id"], "2006-04-01"), "SF")
        self.assertEqual(departure_position(ROOT, roster, telfair["name"], telfair["bbr_id"], AFTER), "PG")   # his dated correction

    def test_every_recorded_trade_departure_reads_as_written(self):
        from runtime.signing import departure_position
        seen = 0
        for season in ("2004-05", "2005-06"):
            roster = register(season)
            ledger = json.loads((CAREER / season / "00_Team/Team/Roster/departures.json").read_text(encoding="utf-8"))
            for e in ledger["entries"]:
                if e["basis"].startswith("traded"):
                    seen += 1
                    self.assertEqual(departure_position(ROOT, roster, e["player"], e["bbr_id"], e["from"]), e["position"], e)
        self.assertEqual(seen, 6)


class UnsourcedRegistryRows(unittest.TestCase):
    """X-5: the summer market's identity read a registry row with no sourced position as its page slot ("SF") after
    the clock, and camp invites put that slot back where the front office's table had dropped it."""

    def test_market_identity_reads_no_position_after_the_clock(self):
        from runtime import free_agency_2004 as fa
        for b in UNSOURCED:
            self.assertEqual(fa.identity(ROOT, 2005, on="2005-12-31")[b]["position"], "SF")     # the recorded summers
            self.assertEqual(fa.identity(ROOT, 2006, on="2006-06-20")[b]["position"], "SF")
            self.assertIsNone(fa.identity(ROOT, 2006, on="2006-06-21")[b]["position"])
        with mock.patch("runtime.write_back.clock", return_value="2006-09-01"):                 # no date: the career clock
            self.assertIsNone(fa.identity(ROOT, 2006)["fitchge01"]["position"])

    def test_the_reading_date_and_a_root_without_season_state(self):
        import tempfile
        from runtime.miami_register import guess_in_force
        self.assertTrue(guess_in_force(ROOT, "2006-06-20"))
        self.assertFalse(guess_in_force(ROOT, "2006-06-21"))
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(guess_in_force(tmp))                   # a test scaffold reads as every such reader did

    def test_camp_leaves_an_unsourced_row_unranked(self):
        from runtime import camp
        players = {"fitchge01": "Gerald Fitch", "walshma01": "Matt Walsh", "jamesle01": "LeBron James"}
        market = SimpleNamespace(
            pool=lambda on: {b: {"player": n, "bbr_id": b, "club": None, "nba_seasons_before_2003_04": 2} for b, n in players.items()},
            restricted=lambda b: False,
            valuation=SimpleNamespace(value=lambda b: 12.0, age=lambda b: 24, signing_minimum=lambda years: 641748))
        office = SimpleNamespace(roster={"players": []}, needs=lambda: {}, _positions=lambda: {}, fit=lambda pos, needs: 1.0)

        def invited(day):
            with pinned("2006-07"), mock.patch.object(camp, "FIRST", False), \
                    mock.patch("runtime.write_back.clock", return_value=day):
                return {r["bbr_id"]: r["position"] for r in camp.invite(day, office, market, ROOT)}

        self.assertEqual(invited("2006-09-01"), {"jamesle01": "SF"})
        self.assertEqual(invited("2006-06-20"), {"jamesle01": "SF", "fitchge01": "SF", "walshma01": "SF"})   # as recorded


if __name__ == "__main__":
    unittest.main()
