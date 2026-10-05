"""Symmetric league, phase 3: trades between two real clubs (docs/symmetric_league_design.md).

Only while `league_book.active(date)`. Once a week (Mondays) up to the deadline, every pair of real clubs is
searched for deals of one or two rotation players for one that both clubs gain from on their own objectives:
- values: `trades.Assets.player_value` split into this season and the future, weighted by each club's stance
  (`STANCE_WEIGHTS`), times its skill fit for the arriving player (`skill_fit.py`, the club's own needs);
- legality: the 1999 salary rule (incoming at most 115% of outgoing plus $100,000, unless the club is under
  the cap after the trade); untouchables stay unless the club gains UNTOUCHABLE_MARGIN; the deadline;
- acceptance: each club's chance is `trades.acceptance` of its own gain; a deal is proposed only when both
  clear SEARCH_MIN_ACCEPT, and the best mutual gain league-wide is offered first.
At most MAX_PER_WEEK deals a week are put to the engine, one decision packet per deal (accept with the
product of the two chances); a drawn acceptance is written to `league_moves.json`. Same evidence for every
club, no hindsight: values read only 2002-03 production and dated contracts.
"""
from datetime import date, timedelta
import json
from pathlib import Path

from .league_book import LeagueBook, active
from .league_moves import effective_roster, ledger_path, read as read_moves
from .trades import (ACCEPT_FLOOR, MIAMI, SEARCH_MIN_ACCEPT, STANCE_WEIGHTS, UNDER_CONTRACT, UNTOUCHABLE_MARGIN,
                     Assets, acceptance)

ROOT = Path(__file__).resolve().parents[1]


def deadline(day, root=ROOT):
    """The trade deadline of the season `day` belongs to (runtime/seasons.py)."""
    from .seasons import dates, season_of_date
    return dates(season_of_date(day), root)["trade_deadline"]


def draws_dir(season):
    return Path(f"career/Dwyane_Wade/{season}/League/Trade_Draws")
MAX_PER_WEEK = 2                     # calibrated against 16 real trades from December 3 to the deadline (rules file)
ROTATION_CANDIDATES = 9
MATCH_PERCENT, MATCH_PLUS = 1.15, 100000
MIN_MUTUAL_GAIN = 0.06              # a club changes its roster only for a clear gain on its own objective (calibrated)
STATUS_QUO = 1.15                   # judgement: a club values the player it has this much more than an equal arrival


def scan_days(start, until=None):
    until = until or deadline(start)
    d = date.fromisoformat(start)
    d += timedelta(days=(7 - d.weekday()) % 7)
    out = []
    while d.isoformat() <= until:
        out.append(d.isoformat())
        d += timedelta(days=7)
    return out


class LeagueTradeDesk:
    def __init__(self, on, market, root=ROOT):
        if not active(on):
            raise ValueError("the symmetric league is not active on this date")
        from .seasons import season_of_date
        self.on, self.root = on, Path(root)
        self.season = season_of_date(on)
        self.assets = Assets(on, market, root)
        self.book = LeagueBook(on, market, root)
        from .skill_fit import SkillFit
        self.skills = SkillFit(root)
        self.contracts = {p["bbr_id"]: p for entry in self.assets.contracts.values() for p in entry.get("players", []) if p.get("bbr_id")}
        self.rosters = {c: sorted(effective_roster(c, on, self.season, root), key=lambda p: -(p["minutes"] / max(1, p["games"])))
                        for c in self.assets.contracts if c != MIAMI}
        self.payroll = {c: self.book.club(c)["payroll"] for c in self.rosters}
        self._needs_cache, self._value_cache = {}, {}

    def _needs(self, club, without=None, adding=None):
        key = (club, without)
        if key not in self._needs_cache:
            held = [(p["bbr_id"], max(1.0, self.assets.valuation.value(p["bbr_id"]) or 1.0))
                    for p in self.rosters[club] if p["bbr_id"] != without]
            self._needs_cache[key] = self.skills.needs(held)
        return self._needs_cache[key]

    def value_to(self, club, bbr, own):
        key = (club, bbr, own)
        if key not in self._value_cache:
            self._value_cache[key] = self._value_to(club, bbr, own)
        return self._value_cache[key]

    def _value_to(self, club, bbr, own):
        """The player's value to the club: stance-weighted now and future, times his skill fit for the club's
        needs without him (the same test for the player it has and the one it would get), and the status quo."""
        entry = self.contracts.get(bbr)
        if entry is None or entry.get("status") not in UNDER_CONTRACT:
            return None
        v = self.assets.player_value(entry, for_club=club)
        # The whole contract: salary over his worth in every remaining season, not only the three the shared value
        # counts, weighted by the club's cash weight (a rebuilder guards its flexibility).
        worth = self.assets.valuation.market_price(self.assets.form_value(bbr), bbr) if self.assets.form_value(bbr) is not None \
            else self.assets.valuation.minimum(0)
        seasons = [int(x) for season_, x in entry["schedule"].items() if season_ >= self.season and x]
        burden = sum(max(0, x - worth) for x in seasons) / self.assets.valuation.mid_level * 0.5
        counted = max(0.0, -v["contract_term"])
        extra = max(0.0, burden - counted) * STANCE_WEIGHTS[self.assets.posture(club)]["cash"]
        weights = STANCE_WEIGHTS[self.assets.posture(club)]
        base = Assets.club_value(v, weights)
        fit = self.skills.fit(bbr, self._needs(club, without=bbr if own else None))
        return base * fit * (STATUS_QUO if own else 1.0) - extra

    def legal(self, club, out_salary, in_salary):
        if self.payroll[club] - out_salary + in_salary <= self.book.cap:
            return True
        return in_salary <= out_salary * MATCH_PERCENT + MATCH_PLUS

    def proposals(self):
        """Every legal deal of one or two rotation players for one, both clubs clearing MIN_MUTUAL_GAIN, best first."""
        clubs = sorted(self.rosters)
        found = []
        for i, a in enumerate(clubs):
            for b in clubs[i + 1:]:
                ra = [p["bbr_id"] for p in self.rosters[a][:ROTATION_CANDIDATES]]
                rb = [p["bbr_id"] for p in self.rosters[b][:ROTATION_CANDIDATES]]
                packages_a = [[x] for x in ra] + [[x, y] for k, x in enumerate(ra) for y in ra[k + 1:]]
                packages_b = [[x] for x in rb] + [[x, y] for k, x in enumerate(rb) for y in rb[k + 1:]]
                for pa in packages_a:
                    for pb in packages_b:
                        if len(pa) + len(pb) > 3:
                            continue                       # one or two for one
                        row = self.evaluate(a, pa, b, pb)
                        if row:
                            found.append(row)
        found.sort(key=lambda r: (-min(r["gain"].values()), r["id"]))
        return found

    def evaluate(self, a, a_out, b, b_out):
        a_out, b_out = list(a_out) if isinstance(a_out, (list, tuple)) else [a_out], list(b_out) if isinstance(b_out, (list, tuple)) else [b_out]
        ca, cb = [self.contracts.get(x) for x in a_out], [self.contracts.get(x) for x in b_out]
        if not all(ca) or not all(cb):
            return None
        sa = sum(int(c["schedule"].get(self.season) or 0) for c in ca)
        sb = sum(int(c["schedule"].get(self.season) or 0) for c in cb)
        if not all(int(c["schedule"].get(self.season) or 0) for c in ca + cb) or not self.legal(a, sa, sb) or not self.legal(b, sb, sa):
            return None
        if len(self.rosters[a]) - len(a_out) + len(b_out) > 15 or len(self.rosters[b]) - len(b_out) + len(a_out) > 15:
            return None
        vals = {}
        for club, out, inc in ((a, a_out, b_out), (b, b_out, a_out)):
            own = [self.value_to(club, x, own=True) for x in out]
            got = [self.value_to(club, x, own=False) for x in inc]
            if None in own or None in got:
                return None
            vals[club] = (Assets.effective([max(0.0, v) for v in got]) - sum(min(0.0, v) for v in got) * -1,
                          Assets.effective([max(0.0, v) for v in own]) - sum(min(0.0, v) for v in own) * -1)
        rel = lambda after, before: (after - before) / max(abs(after), abs(before), 1.0)
        gain = {club: round(rel(*vals[club]), 3) for club in (a, b)}
        if min(gain.values()) < max(ACCEPT_FLOOR, MIN_MUTUAL_GAIN):
            return None
        chances = {}
        for club, out, cs in ((a, a_out, ca), (b, b_out, cb)):
            held = [why for c in cs for why in [self.assets.untouchable(club, c)] if why]
            p = acceptance({"objective_gain": gain[club], "untouchable": [("x", w) for w in held]})
            if p is None or p < SEARCH_MIN_ACCEPT:
                return None
            chances[club] = p
        tag = "-".join(sorted(a_out + b_out))
        return {"id": f"{self.season}-league-trade-{self.on}-{tag}", "date": self.on, "clubs": [a, b],
                "a": {"club": a, "sends": [c["player"] for c in ca], "bbr_ids": a_out, "salary": sa},
                "b": {"club": b, "sends": [c["player"] for c in cb], "bbr_ids": b_out, "salary": sb},
                "gain": gain, "accept": chances, "both": round(chances[a] * chances[b], 6)}

    def packet(self, row):
        return {"event_id": row["id"], "date": row["date"],
                "question": f"Do {row['a']['club']} and {row['b']['club']} trade {' and '.join(row['a']['sends'])} for {' and '.join(row['b']['sends'])}?",
                "decider": f"{row['a']['club']} and {row['b']['club']} front offices (engine draw)",
                "options": {"accept": row["both"], "decline": round(1 - row["both"], 6)},
                "basis": (f"gains on own objectives {row['gain']}; acceptance {row['accept']}; 1999 salary rule met; "
                          "symmetric league phase 3 (runtime/league_trades.py)")}


def weekly(root=ROOT, day=None, market=None):
    """Write the week's packet(s) and execute drawn acceptances. Returns (packets_written, moves_written)."""
    from .market import Market
    root = Path(root)
    market = market or Market(day, root)
    desk = LeagueTradeDesk(day, market, root)
    SEASON = desk.season
    draws = root / draws_dir(SEASON)
    draws.mkdir(parents=True, exist_ok=True)
    existing = sorted(draws.glob(f"*{day}*.decision.json"))
    written = []
    if not existing:
        used = set()
        chosen = []
        for row in desk.proposals():
            if len(chosen) >= MAX_PER_WEEK:
                break
            if used & (set(row["clubs"]) | set(row["a"]["bbr_ids"]) | set(row["b"]["bbr_ids"])):
                continue                                   # a club or player is in at most one deal a week
            used |= set(row["clubs"]) | set(row["a"]["bbr_ids"]) | set(row["b"]["bbr_ids"])
            chosen.append(row)
        for row in chosen:
            (draws / f"{row['id']}.decision.json").write_text(json.dumps(desk.packet(row), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
            (draws / f"{row['id']}.proposal.json").write_text(json.dumps(row, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
            written.append(row["id"])
    moves = read_moves(SEASON, root)
    done = {e.get("deal") for e in moves["entries"]}
    executed = []
    for result in sorted(draws.glob("*.decision.result.json")):
        deal = result.name.replace(".decision.result.json", "")
        if deal in done or json.loads(result.read_text(encoding="utf-8"))["outcome"] != "accept":
            continue
        row = json.loads((draws / f"{deal}.proposal.json").read_text(encoding="utf-8"))
        for side, other in (("a", "b"), ("b", "a")):
            for name, bbr in zip(row[side]["sends"], row[side]["bbr_ids"]):
                moves["entries"].append({"deal": deal, "date": row["date"], "kind": "trade", "player": name, "bbr_id": bbr,
                                         "from": row[side]["club"], "to": row[other]["club"]})
        executed.append(deal)
    if executed:
        path = root / ledger_path(SEASON)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(moves, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return written, executed
