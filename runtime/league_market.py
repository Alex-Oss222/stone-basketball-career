"""Symmetric league, phase 2: the in-season market for every real club (docs/symmetric_league_design.md).

Only while `league_book.active(date)`. Rules from `library/2003/league/nba_1999_in_season_rules.json` (1999 CBA,
researched with sources): twelve the minimum and fifteen the maximum under contract, 48-hour waivers claimed by the
worst record, a claim needs cap room for the salary or a minimum contract, 10-day contracts from January 5, 2004 (two
per player with one club, then a rest-of-season contract or release), all contracts guaranteed January 10.

Each market day, in this order, for each real club (alphabetical, so the order is fixed):
1. a 10-day contract that has run out (ten days, `TEN_DAY_DAYS`) is renewed once if the club still needs him, then
   converted to the rest of the season if he is worth a place in its top twelve by value, else he leaves;
2. a club under twelve signs from the pool (a rest-of-season minimum before January 5, a 10-day after);
3. from January 5, a club with INJURED_FOR_TEN_DAY or more injured regulars and a spare place signs a 10-day;
4. on January 7, the last day a waiver clears before the January 10 guarantee, a club lets go of an unprotected player
   outside its top thirteen when a free agent is GUARANTEE_CUT_MARGIN more valuable (12 of 2003-04's 55 waivers came
   January 5-7);
5. a club at fifteen whose best available free agent beats its weakest unprotected player by UPGRADE_MARGIN waives
   him and signs the free agent; the waived player goes through waivers (worst record first, a club claims him when
   he beats its own weakest by CLAIM_MARGIN and the claim is legal), or clears into the pool.
The pool: researched unsigned players fit to sign on the date (December 1 and monthly snapshots), the players left
off rosters at activation, and players who cleared waivers or whose 10-day ran out, minus Miami's and anyone signed.
Choices are by value (`trades.Assets.form_value`: last season's production, 2002-03 in the first season and then the
previous simulated season, blended with this season's closed games) times skill fit for the club's needs.
Every move is written to `league_moves.json` with its contract. Nothing here is a chance draw: these are routine
front-office decisions, like Miami's own roster moves, on evidence known on the date.
"""
from datetime import date, timedelta
import json
from pathlib import Path

from .league_book import LeagueBook, active
from .league_moves import activation_free_agents, effective_roster, ledger_path, read as read_moves
from .trades import Assets, MIAMI

ROOT = Path(__file__).resolve().parents[1]
RULES = Path("library/2003/league/nba_1999_in_season_rules.json")
STATS_PATH = Path("library/2003/league/nba_2002_03_player_stats.json")
EXPIRING_PATH = Path("library/2003/league/nba_2003_expiring_contracts.json")
TEN_DAY_DAYS = 10
# Judgement constants, calibrated against the 2003-04 volume in the rules file (docs/symmetric_league_design.md).
INJURED_FOR_TEN_DAY = 1             # before NEED_RULE_FROM: one injured regular was enough (2.5x the real 10-day rate)
NEED_RULE_FROM = "2004-01-20"       # from this date a 10-day is an emergency fill: healthy players under contract below 12
CONTRIBUTOR_MINUTES = 10.0          # judgement: a 10-day player averaging this many minutes a club game is kept
UPGRADE_MARGIN = 1.2
WAIVER_DAYS = 2                      # 48-hour waivers (1999 CBA, nba_1999_in_season_rules.json)
GUARANTEE_CUT_KEEP = 13              # outside its top thirteen by value, an unprotected player can be let go
GUARANTEE_CUT_MARGIN = 1.25          # ... when a free agent is this much more valuable
CLAIM_MARGIN = 1.2
SNAPSHOT_FRESH_DAYS = 31


def _rules(root, season):
    """The agreement's in-season rules (roster limits) with the season's dates (runtime/seasons.py)."""
    from .seasons import dates
    data = json.loads((Path(root) / RULES).read_text(encoding="utf-8"))["rules"]
    roster = data["roster"]
    gates = dates(season, root)
    if season >= "2005-06":               # the 2005 agreement's limits (runtime/era.py: 13 to 15)
        from .era import rules_for
        era = rules_for(season)
        lo, hi = era["roster_minimum"], era["roster_maximum"]
    else:
        lo = roster["minimum_players_under_contract_regular_season"]["value"]
        hi = roster["maximum_players_under_contract_regular_season"]["value"]
    return {"min": lo, "max": hi,
            "ten_day_from": gates["ten_day_contracts_from"], "ten_day_per_club": 2, "guarantee": gates["guarantee"],
            "cut_day": gates["waive_by"], "season_end": gates["regular_season_end"]}


def _status_on(day, root):
    """The newest researched snapshot of unsigned players dated on or before `day` and within SNAPSHOT_FRESH_DAYS:
    {bbr: status}. A season without researched snapshots has none (its pool is the league's own free agents)."""
    from .seasons import path as season_path, season_of_date
    root = Path(root)
    season = season_of_date(day)
    status_dec, status_monthly = season_path(season, "unsigned_status"), season_path(season, "unsigned_status_monthly")
    snaps = {}
    if (root / status_dec).is_file():
        d = json.loads((root / status_dec).read_text(encoding="utf-8"))
        snaps[d["as_of"]] = d["players"]
    if (root / status_monthly).is_file():
        snaps.update(json.loads((root / status_monthly).read_text(encoding="utf-8"))["snapshots"])
    dated = [k for k in snaps if k <= day]
    if not dated:
        return {}
    newest = max(dated)
    if date.fromisoformat(day) > date.fromisoformat(newest) + timedelta(days=SNAPSHOT_FRESH_DAYS):
        raise ValueError(f"no researched unsigned-player snapshot within {SNAPSHOT_FRESH_DAYS} days of {day}")
    return snaps[newest]


RETIREMENT_FROM = "2004-11-24"     # the user's request (October 2026); earlier market days stand as run


class LeagueMarket:
    def __init__(self, day, market, root=ROOT):
        if not active(day):
            raise ValueError("the symmetric league is not active on this date")
        from .seasons import season_of_date
        self.day, self.root = day, Path(root)
        self.season = season_of_date(day)
        self.rules = _rules(root, self.season)
        self.assets = Assets(day, market, root)
        self.book = LeagueBook(day, market, root)
        from .skill_fit import SkillFit
        self.skills = SkillFit(root)
        self.moves = read_moves(self.season, root)
        self.clubs = sorted(c for c in self.book.inventory if c != MIAMI)
        self.rosters = {c: effective_roster(c, day, self.season, root) for c in self.clubs}
        from .league_moves import _protected_contracts
        self.protected = _protected_contracts(root, self.season)
        from .standings import worst_first
        self.order = worst_first(day, root, self.season, self.clubs)

    # -- evidence --------------------------------------------------------------------------------
    def value(self, bbr):
        v = self.assets.form_value(bbr)
        return v if v is not None else 0.0

    def _role_from_stats(self, bbr, name):
        stats = {r["bbr_id"]: r for r in json.loads((self.root / STATS_PATH).read_text(encoding="utf-8"))["records"]}
        expiring = {p["bbr_id"]: p for p in json.loads((self.root / EXPIRING_PATH).read_text(encoding="utf-8"))["players"] if p.get("bbr_id")}
        t = (stats.get(bbr) or {}).get("totals") or {}
        return {"player_id": name, "bbr_id": bbr, "position": (expiring.get(bbr) or {}).get("position") or "SF",
                "games": int(t.get("games") or 1), "minutes": int(t.get("minutes") or 1)}

    def pool(self):
        """{bbr: role} of players any club may sign today."""
        on_a_club = {p["bbr_id"] for players in self.rosters.values() for p in players}
        from .rotations import miami_holds
        held = set(miami_holds(self.season, self.day, self.root))
        out = {}
        for e in activation_free_agents(self.season, self.root):
            out[e["bbr_id"]] = {k: e[k] for k in ("player_id", "bbr_id", "position", "games", "minutes")}
        for bbr, st in _status_on(self.day, self.root).items():
            if st["status"] == "unsigned_available":
                out.setdefault(bbr, self._role_from_stats(bbr, st["player"]))
        for e in self.moves["entries"]:
            if e.get("to") is None and e.get("role") and e["date"] <= self.day and e["kind"] != "waive":
                out.setdefault(e["bbr_id"], e["role"])         # cleared waivers, ended 10-day contracts
        waiting = {e["bbr_id"] for e in self.on_waivers()}     # on waivers: nobody may sign him yet
        from .availability import signable                     # retired or sitting the season out in history: never signed
        return {b: r for b, r in out.items() if b not in on_a_club and b not in held and b not in waiting
                and signable(b, self.season, self.root)}

    def fit_value(self, club, bbr, without=None):
        held = [(p["bbr_id"], max(1.0, self.value(p["bbr_id"]))) for p in self.rosters[club] if p["bbr_id"] != without]
        return self.value(bbr) * self.skills.fit(bbr, self.skills.needs(held))

    def injured_regulars(self, club):
        return sum(1 for p in self.rosters[club] if self.assets.injured(p["player_id"], club))

    def short_handed(self, club):
        """Fewer than the minimum healthy players under contract: injured regulars do not count."""
        return len(self.rosters[club]) - self.injured_regulars(club) < self.rules["min"]

    def minutes_for(self, name, club, since):
        """His average minutes per club game from `since` through the day before, from closed results only."""
        if not hasattr(self, "_results"):
            from .write_back import closed_results
            prior = (date.fromisoformat(self.day) - timedelta(days=1)).isoformat()
            self._results = [row["result"] for row in closed_results(self.root, self.season, prior)]
        games = minutes = 0
        for r in self._results:
            if r["game_date"] < since:
                continue
            for side in ("home", "away"):
                if r[side] == club:
                    games += 1
                    minutes += sum(p.get("minutes") or 0 for p in r["player_stats"][side] if p["player_id"] == name)
        return minutes / games if games else 0.0

    def contract_of(self, bbr, club):
        """The market contract a club holds on him, if any (10-day or rest-of-season), newest first."""
        for e in reversed(self.moves["entries"]):
            if e["bbr_id"] == bbr and e.get("to") == club and e["kind"] in ("ten_day", "rest_of_season", "signing", "claim"):
                return e
        return None

    def ten_days_with(self, bbr, club):
        return sum(1 for e in self.moves["entries"] if e["bbr_id"] == bbr and e.get("to") == club and e["kind"] == "ten_day")

    # -- moves -----------------------------------------------------------------------------------
    def _add(self, kind, bbr, role, frm, to, contract=None, note=""):
        entry = {"id": f"{self.season}-market-{self.day}-{kind}-{bbr}", "date": self.day, "kind": kind,
                 "player": role["player_id"], "bbr_id": bbr, "from": frm, "to": to, "role": role,
                 "contract": contract, "note": note}
        self.moves["entries"].append(entry)
        if frm:
            self.rosters[frm] = [p for p in self.rosters[frm] if p["bbr_id"] != bbr]
        if to:
            self.rosters[to].append(dict(role))
        return entry

    def _sign(self, club, pool, kind):
        # After two 10-day contracts with a club, that club may keep him only on a rest-of-season contract (1999 CBA).
        eligible = [b for b in pool if kind != "ten_day" or self.ten_days_with(b, club) < self.rules["ten_day_per_club"]]
        if not eligible:
            return None
        bbr = max(eligible, key=lambda b: (self.fit_value(club, b), b))
        role = pool.pop(bbr)
        until = (date.fromisoformat(self.day) + timedelta(days=TEN_DAY_DAYS)).isoformat() if kind == "ten_day" else self.rules["season_end"]
        return self._add(kind, bbr, role, None, club, {"type": kind, "until": min(until, self.rules["season_end"]), "salary": "pro-rated minimum"},
                         note=f"value {round(self.fit_value(club, bbr), 2)} x fit")

    def _weakest(self, club):
        cands = [p for p in self.rosters[club] if p["bbr_id"] not in self.protected]
        return min(cands, key=lambda p: (self.value(p["bbr_id"]), p["bbr_id"])) if cands else None

    def _waive(self, club, player, pool):
        """He goes on 48-hour waivers: off the club, in nobody's pool until the waivers resolve (`_resolve_waivers`)."""
        role = {k: player[k] for k in ("player_id", "bbr_id", "position", "games", "minutes")}
        clears = (date.fromisoformat(self.day) + timedelta(days=WAIVER_DAYS)).isoformat()
        return self._add("waive", player["bbr_id"], role, club, None, note=f"48-hour waivers; resolve {clears}")

    def on_waivers(self):
        """Waive entries not yet resolved by a claim or a clearance."""
        resolved = {e.get("waiver") for e in self.moves["entries"] if e["kind"] in ("claim", "clear")}
        return [e for e in self.moves["entries"] if e["kind"] == "waive" and e["id"] not in resolved]

    def _resolve_waivers(self, pool):
        """Waivers placed WAIVER_DAYS or more ago resolve today: the worst record on today's standings with a roster
        spot claims him when he beats its own weakest by CLAIM_MARGIN and the claim is legal (cap room, or a contract
        that is not a protected one); otherwise he clears into the pool."""
        for w in self.on_waivers():
            if (date.fromisoformat(w["date"]) + timedelta(days=WAIVER_DAYS)).isoformat() > self.day:
                continue
            role, bbr, club = w["role"], w["bbr_id"], w["from"]
            claimed = None
            for other in self.order:
                if other == club or len(self.rosters[other]) >= self.rules["max"]:
                    continue
                weakest = self._weakest(other)
                legal = self.book.club(other)["cap_room"] > 0 or bbr not in self.protected
                if legal and (weakest is None or self.value(bbr) > CLAIM_MARGIN * self.value(weakest["bbr_id"])):
                    claimed = self._add("claim", bbr, role, None, other, {"type": "claimed contract", "until": self.rules["season_end"]},
                                        note=f"claimed off waivers from {club} (worst record first)")
                    break
            if claimed is None:
                claimed = self._add("clear", bbr, role, None, None, note=f"cleared waivers from {club}: a free agent")
                pool[bbr] = role
            claimed["waiver"] = w["id"]

    def run(self):
        """Make today's moves. Returns the new entries."""
        if self.day in self.moves.get("market_days", []) or any(
                e["date"] == self.day and "-market-" in e.get("id", "") for e in self.moves["entries"]):
            return []                                   # the day's market already ran (with or without moves): never twice
        start = len(self.moves["entries"])
        pool = self.pool()
        self._resolve_waivers(pool)
        # 0. retirements (runtime/availability.py, from RETIREMENT_FROM): a player history retired before this season
        #    leaves his club for good; the club fills the spot below like any other vacancy.
        if self.day >= RETIREMENT_FROM:
            from .availability import status
            for club in self.clubs:
                for p in list(self.rosters[club]):
                    if status(p["bbr_id"], self.season, self.root) == "retired":
                        role = {k: p.get(k) for k in ("player_id", "bbr_id", "position", "games", "minutes")}
                        self._add("retire", p["bbr_id"], role, club, None,
                                  note=f"retired: his real career ended before {self.season} (career continuity)")
        ten_open = self.day >= self.rules["ten_day_from"]
        for club in self.clubs:
            # 1. expiring 10-day contracts
            for p in list(self.rosters[club]):
                c = self.contract_of(p["bbr_id"], club)
                if not c or c["kind"] != "ten_day" or c["contract"]["until"] > self.day:
                    continue
                role = c["role"]
                if self.day >= NEED_RULE_FROM:
                    # Kept if he contributed; a second 10-day only while the club is still short; otherwise he goes.
                    first = min(e["date"] for e in self.moves["entries"]
                                if e["bbr_id"] == p["bbr_id"] and e.get("to") == club and e["kind"] == "ten_day")
                    mpg = self.minutes_for(role["player_id"], club, first)
                    if mpg >= CONTRIBUTOR_MINUTES:
                        self._add("rest_of_season", p["bbr_id"], role, club, club,
                                  {"type": "rest_of_season", "until": self.rules["season_end"], "salary": "pro-rated minimum"},
                                  note=f"kept: {mpg:.1f} minutes a game on his 10-day contracts")
                    elif self.ten_days_with(p["bbr_id"], club) < self.rules["ten_day_per_club"] and self.short_handed(club):
                        self._add("ten_day", p["bbr_id"], role, club, club,
                                  {"type": "ten_day", "until": min((date.fromisoformat(self.day) + timedelta(days=TEN_DAY_DAYS)).isoformat(), self.rules["season_end"]),
                                   "salary": "pro-rated minimum"}, note=f"second 10-day contract: still short-handed ({mpg:.1f} minutes a game)")
                    else:
                        self._add("expire", p["bbr_id"], role, club, None, note=f"10-day contract ended ({mpg:.1f} minutes a game)")
                        pool[p["bbr_id"]] = role
                    continue
                if self.ten_days_with(p["bbr_id"], club) < self.rules["ten_day_per_club"] and self.injured_regulars(club) >= INJURED_FOR_TEN_DAY:
                    self._add("ten_day", p["bbr_id"], role, club, club,
                              {"type": "ten_day", "until": min((date.fromisoformat(self.day) + timedelta(days=TEN_DAY_DAYS)).isoformat(), self.rules["season_end"]),
                               "salary": "pro-rated minimum"}, note="second 10-day contract")
                    continue
                ranked = sorted((self.value(q["bbr_id"]) for q in self.rosters[club]), reverse=True)
                if len(ranked) >= self.rules["min"] and self.value(p["bbr_id"]) < ranked[self.rules["min"] - 1]:
                    self._add("expire", p["bbr_id"], role, club, None, note="10-day contract ended")
                    pool[p["bbr_id"]] = role
                else:
                    self._add("rest_of_season", p["bbr_id"], role, club, club, {"type": "rest_of_season", "until": self.rules["season_end"],
                                                                               "salary": "pro-rated minimum"})
            # 2. the twelve-man minimum
            while len(self.rosters[club]) < self.rules["min"] and pool:
                self._sign(club, pool, "ten_day" if ten_open else "rest_of_season")
            # 3. injury depth
            need = self.short_handed(club) if self.day >= NEED_RULE_FROM else self.injured_regulars(club) >= INJURED_FOR_TEN_DAY
            if ten_open and need and len(self.rosters[club]) < self.rules["max"] and pool:
                self._sign(club, pool, "ten_day")
            # 4. the guarantee cut: before contracts become guaranteed, a club lets go of non-guaranteed depth it can better
            if self.day == self.rules["cut_day"]:
                ranked = sorted(self.rosters[club], key=lambda q: (-self.value(q["bbr_id"]), q["bbr_id"]))
                for q in ranked[GUARANTEE_CUT_KEEP:]:
                    if q["bbr_id"] in self.protected or not pool:
                        continue
                    best = max(pool, key=lambda b: (self.fit_value(club, b), b))
                    if self.fit_value(club, best) >= GUARANTEE_CUT_MARGIN * max(0.5, self.value(q["bbr_id"])):
                        self._waive(club, q, pool)
                        self._sign(club, pool, "ten_day" if ten_open else "rest_of_season")
            # 5. an upgrade at fifteen
            if len(self.rosters[club]) >= self.rules["max"] and pool:
                weakest = self._weakest(club)
                best = max(pool, key=lambda b: (self.fit_value(club, b), b))
                if weakest and self.fit_value(club, best) > UPGRADE_MARGIN * max(0.5, self.value(weakest["bbr_id"])):
                    self._waive(club, weakest, pool)
                    self._sign(club, pool, "ten_day" if ten_open else "rest_of_season")
        new = self.moves["entries"][start:]
        self.moves["market_days"] = sorted(set(self.moves.get("market_days", [])) | {self.day})
        path = self.root / ledger_path(self.season)                  # written even without moves: the day is recorded as run,
        path.parent.mkdir(parents=True, exist_ok=True)          # so a rerun of the day cannot act again
        path.write_text(json.dumps(self.moves, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        return new
