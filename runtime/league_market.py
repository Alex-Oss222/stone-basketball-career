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
Choices are by value (2002-03 production blended with closed 2003-04 games) times skill fit for the club's needs.
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
SEASON = "2003-04"
RULES = Path("library/2003/league/nba_1999_in_season_rules.json")
STATUS_DEC = Path("library/2003/league/nba_2003_04_unsigned_status.json")
STATUS_MONTHLY = Path("library/2003/league/nba_2003_04_unsigned_status_monthly.json")
STATS_PATH = Path("library/2003/league/nba_2002_03_player_stats.json")
EXPIRING_PATH = Path("library/2003/league/nba_2003_expiring_contracts.json")
SEASON_END = "2004-04-14"
TEN_DAY_DAYS = 10
# Judgement constants, calibrated against the 2003-04 volume in the rules file (docs/symmetric_league_design.md).
INJURED_FOR_TEN_DAY = 1
UPGRADE_MARGIN = 1.2
GUARANTEE_CUT_DAY = "2004-01-07"     # the last day a 48-hour waiver clears before the January 10 guarantee
GUARANTEE_CUT_KEEP = 13              # outside its top thirteen by value, an unprotected player can be let go
GUARANTEE_CUT_MARGIN = 1.25          # ... when a free agent is this much more valuable
CLAIM_MARGIN = 1.2
SNAPSHOT_FRESH_DAYS = 31


def _rules(root):
    data = json.loads((Path(root) / RULES).read_text(encoding="utf-8"))["rules"]
    roster, ten = data["roster"], data["ten_day"]
    first = ten.get("first_signing_date_2003_04", {})
    return {"min": roster["minimum_players_under_contract_regular_season"]["value"],
            "max": roster["maximum_players_under_contract_regular_season"]["value"],
            "ten_day_from": first.get("value", first) if isinstance(first, dict) else first or "2004-01-05",
            "ten_day_per_club": 2,
            "guarantee": data["waivers"]["contract_guarantee_date"].get("date_2003_04", "2004-01-10")}


def _status_on(day, root):
    """The newest researched snapshot dated on or before `day` and within SNAPSHOT_FRESH_DAYS: {bbr: status}."""
    root = Path(root)
    snaps = {}
    if (root / STATUS_DEC).is_file():
        d = json.loads((root / STATUS_DEC).read_text(encoding="utf-8"))
        snaps[d["as_of"]] = d["players"]
    if (root / STATUS_MONTHLY).is_file():
        snaps.update(json.loads((root / STATUS_MONTHLY).read_text(encoding="utf-8"))["snapshots"])
    dated = [k for k in snaps if k <= day]
    if not dated:
        return {}
    newest = max(dated)
    if date.fromisoformat(day) > date.fromisoformat(newest) + timedelta(days=SNAPSHOT_FRESH_DAYS):
        raise ValueError(f"no researched unsigned-player snapshot within {SNAPSHOT_FRESH_DAYS} days of {day}")
    return snaps[newest]


class LeagueMarket:
    def __init__(self, day, market, root=ROOT):
        if not active(day):
            raise ValueError("the symmetric league is not active on this date")
        self.day, self.root = day, Path(root)
        self.rules = _rules(root)
        self.assets = Assets(day, market, root)
        self.book = LeagueBook(day, market, root)
        from .skill_fit import SkillFit
        self.skills = SkillFit(root)
        self.moves = read_moves(SEASON, root)
        self.clubs = sorted(c for c in self.book.inventory if c != MIAMI)
        self.rosters = {c: effective_roster(c, day, SEASON, root) for c in self.clubs}
        from .league_moves import _protected_contracts
        self.protected = _protected_contracts(root)
        from .standings import worst_first
        self.order = worst_first(day, root, SEASON, self.clubs)

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
        held = set(miami_holds(SEASON, self.day, self.root))
        out = {}
        for e in activation_free_agents(SEASON, self.root):
            out[e["bbr_id"]] = {k: e[k] for k in ("player_id", "bbr_id", "position", "games", "minutes")}
        for bbr, st in _status_on(self.day, self.root).items():
            if st["status"] == "unsigned_available":
                out.setdefault(bbr, self._role_from_stats(bbr, st["player"]))
        for e in self.moves["entries"]:
            if e.get("to") is None and e.get("role") and e["date"] <= self.day:
                out.setdefault(e["bbr_id"], e["role"])         # cleared waivers, ended 10-day contracts
        return {b: r for b, r in out.items() if b not in on_a_club and b not in held}

    def fit_value(self, club, bbr, without=None):
        held = [(p["bbr_id"], max(1.0, self.value(p["bbr_id"]))) for p in self.rosters[club] if p["bbr_id"] != without]
        return self.value(bbr) * self.skills.fit(bbr, self.skills.needs(held))

    def injured_regulars(self, club):
        return sum(1 for p in self.rosters[club] if self.assets.injured(p["player_id"], club))

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
        entry = {"id": f"{SEASON}-market-{self.day}-{kind}-{bbr}", "date": self.day, "kind": kind,
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
        until = (date.fromisoformat(self.day) + timedelta(days=TEN_DAY_DAYS)).isoformat() if kind == "ten_day" else SEASON_END
        return self._add(kind, bbr, role, None, club, {"type": kind, "until": min(until, SEASON_END), "salary": "pro-rated minimum"},
                         note=f"value {round(self.fit_value(club, bbr), 2)} x fit")

    def _weakest(self, club):
        cands = [p for p in self.rosters[club] if p["bbr_id"] not in self.protected]
        return min(cands, key=lambda p: (self.value(p["bbr_id"]), p["bbr_id"])) if cands else None

    def _waive(self, club, player, pool):
        role = {k: player[k] for k in ("player_id", "bbr_id", "position", "games", "minutes")}
        self._add("waive", player["bbr_id"], role, club, None, note="48-hour waivers")
        for other in self.order:
            if other == club or len(self.rosters[other]) >= self.rules["max"]:
                continue
            weakest = self._weakest(other)
            legal = self.book.club(other)["cap_room"] > 0 or player["bbr_id"] not in self.protected
            if legal and (weakest is None or self.value(player["bbr_id"]) > CLAIM_MARGIN * self.value(weakest["bbr_id"])):
                return self._add("claim", player["bbr_id"], role, None, other, {"type": "claimed contract", "until": SEASON_END},
                                 note=f"claimed off waivers from {club} (worst record first)")
        pool[player["bbr_id"]] = role                               # cleared: a free agent
        return None

    def run(self):
        """Make today's moves. Returns the new entries."""
        start = len(self.moves["entries"])
        pool = self.pool()
        ten_open = self.day >= self.rules["ten_day_from"]
        for club in self.clubs:
            # 1. expiring 10-day contracts
            for p in list(self.rosters[club]):
                c = self.contract_of(p["bbr_id"], club)
                if not c or c["kind"] != "ten_day" or c["contract"]["until"] > self.day:
                    continue
                role = c["role"]
                if self.ten_days_with(p["bbr_id"], club) < self.rules["ten_day_per_club"] and self.injured_regulars(club) >= INJURED_FOR_TEN_DAY:
                    self._add("ten_day", p["bbr_id"], role, club, club,
                              {"type": "ten_day", "until": min((date.fromisoformat(self.day) + timedelta(days=TEN_DAY_DAYS)).isoformat(), SEASON_END),
                               "salary": "pro-rated minimum"}, note="second 10-day contract")
                    continue
                ranked = sorted((self.value(q["bbr_id"]) for q in self.rosters[club]), reverse=True)
                if len(ranked) >= self.rules["min"] and self.value(p["bbr_id"]) < ranked[self.rules["min"] - 1]:
                    self._add("expire", p["bbr_id"], role, club, None, note="10-day contract ended")
                    pool[p["bbr_id"]] = role
                else:
                    self._add("rest_of_season", p["bbr_id"], role, club, club, {"type": "rest_of_season", "until": SEASON_END,
                                                                               "salary": "pro-rated minimum"})
            # 2. the twelve-man minimum
            while len(self.rosters[club]) < self.rules["min"] and pool:
                self._sign(club, pool, "ten_day" if ten_open else "rest_of_season")
            # 3. injury depth
            if ten_open and self.injured_regulars(club) >= INJURED_FOR_TEN_DAY and len(self.rosters[club]) < self.rules["max"] and pool:
                self._sign(club, pool, "ten_day")
            # 4. the guarantee cut: before contracts become guaranteed, a club lets go of non-guaranteed depth it can better
            if self.day == GUARANTEE_CUT_DAY:
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
        if new:
            path = self.root / ledger_path(SEASON)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(self.moves, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        return new
