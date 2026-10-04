"""Symmetric league, phase 3: trades between two real clubs (docs/symmetric_league_design.md).

Only while `league_book.active(date)`. Once a week (Mondays) up to the deadline, every pair of real clubs is
searched for one-for-one swaps of rotation players that both clubs gain from on their own objectives:
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
SEASON = "2003-04"
DEADLINE = "2004-02-19"
DRAWS = Path(f"career/Dwyane_Wade/{SEASON}/League/Trade_Draws")
MAX_PER_WEEK = 1                     # judgement; calibrate in phase 5 against 2003-04 in-season trade volume
ROTATION_CANDIDATES = 9
MATCH_PERCENT, MATCH_PLUS = 1.15, 100000
MIN_MUTUAL_GAIN = 0.10              # a club changes its roster only for a clear gain on its own objective
STATUS_QUO = 1.15                   # judgement: a club values the player it has this much more than an equal arrival


def scan_days(start, until=DEADLINE):
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
        self.on, self.root = on, Path(root)
        self.assets = Assets(on, market, root)
        self.book = LeagueBook(on, market, root)
        from .skill_fit import SkillFit
        self.skills = SkillFit(root)
        self.contracts = {p["bbr_id"]: p for entry in self.assets.contracts.values() for p in entry.get("players", []) if p.get("bbr_id")}
        self.rosters = {c: sorted(effective_roster(c, on, SEASON, root), key=lambda p: -(p["minutes"] / max(1, p["games"])))
                        for c in self.assets.contracts if c != MIAMI}
        self.payroll = {c: self.book.club(c)["payroll"] for c in self.rosters}

    def _needs(self, club, without=None, adding=None):
        held = [(p["bbr_id"], max(1.0, self.assets.valuation.value(p["bbr_id"]) or 1.0))
                for p in self.rosters[club] if p["bbr_id"] != without]
        return self.skills.needs(held)

    def value_to(self, club, bbr, own):
        """The player's value to the club: stance-weighted now and future, times his skill fit for the club's
        needs without him (the same test for the player it has and the one it would get), and the status quo."""
        entry = self.contracts.get(bbr)
        if entry is None or entry.get("status") not in UNDER_CONTRACT:
            return None
        v = self.assets.player_value(entry, for_club=club)
        # The whole contract: salary over his worth in every remaining season, not only the three the shared value
        # counts, weighted by the club's cash weight (a rebuilder guards its flexibility).
        worth = self.assets.valuation.comparables_price(self.assets.form_value(bbr)) if self.assets.form_value(bbr) is not None \
            else self.assets.valuation.minimum(0)
        seasons = [int(x) for season_, x in entry["schedule"].items() if season_ >= SEASON and x]
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
        clubs = sorted(self.rosters)
        found = []
        for i, a in enumerate(clubs):
            for b in clubs[i + 1:]:
                for pa in self.rosters[a][:ROTATION_CANDIDATES]:
                    for pb in self.rosters[b][:ROTATION_CANDIDATES]:
                        row = self.evaluate(a, pa["bbr_id"], b, pb["bbr_id"])
                        if row:
                            found.append(row)
        found.sort(key=lambda r: (-min(r["gain"].values()), r["id"]))
        return found

    def evaluate(self, a, a_bbr, b, b_bbr):
        ca, cb = self.contracts.get(a_bbr), self.contracts.get(b_bbr)
        if not ca or not cb:
            return None
        sa, sb = int(ca["schedule"].get(SEASON) or 0), int(cb["schedule"].get(SEASON) or 0)
        if not sa or not sb or not self.legal(a, sa, sb) or not self.legal(b, sb, sa):
            return None
        a_out, a_in = self.value_to(a, a_bbr, own=True), self.value_to(a, b_bbr, own=False)
        b_out, b_in = self.value_to(b, b_bbr, own=True), self.value_to(b, a_bbr, own=False)
        if None in (a_out, a_in, b_out, b_in):
            return None
        rel = lambda after, before: (after - before) / max(abs(after), abs(before), 1.0)
        gain = {a: round(rel(a_in, a_out), 3), b: round(rel(b_in, b_out), 3)}
        if min(gain.values()) < max(ACCEPT_FLOOR, MIN_MUTUAL_GAIN):
            return None
        untouchable = {a: self.assets.untouchable(a, ca), b: self.assets.untouchable(b, cb)}
        chances = {}
        for club in (a, b):
            p = acceptance({"objective_gain": gain[club], "untouchable": [("x", untouchable[club])] if untouchable[club] else []})
            if p is None or p < SEARCH_MIN_ACCEPT:
                return None
            chances[club] = p
        return {"id": f"{SEASON}-league-trade-{self.on}-{a_bbr}-{b_bbr}", "date": self.on,
                "clubs": [a, b], "a": {"club": a, "sends": ca["player"], "bbr_id": a_bbr, "salary": sa},
                "b": {"club": b, "sends": cb["player"], "bbr_id": b_bbr, "salary": sb},
                "gain": gain, "accept": chances, "both": round(chances[a] * chances[b], 6)}

    def packet(self, row):
        return {"event_id": row["id"], "date": row["date"],
                "question": f"Do {row['a']['club']} and {row['b']['club']} trade {row['a']['sends']} for {row['b']['sends']}?",
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
    draws = root / DRAWS
    draws.mkdir(parents=True, exist_ok=True)
    existing = sorted(draws.glob(f"*{day}*.decision.json"))
    written = []
    if not existing:
        for row in desk.proposals()[:MAX_PER_WEEK]:
            (draws / f"{row['id']}.decision.json").write_text(json.dumps(desk.packet(row), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
            (draws / f"{row['id']}.proposal.json").write_text(json.dumps(row, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
            written.append(row["id"])
    moves = read_moves(SEASON, root)
    done = {e["deal"] for e in moves["entries"]}
    executed = []
    for result in sorted(draws.glob("*.decision.result.json")):
        deal = result.name.replace(".decision.result.json", "")
        if deal in done or json.loads(result.read_text(encoding="utf-8"))["outcome"] != "accept":
            continue
        row = json.loads((draws / f"{deal}.proposal.json").read_text(encoding="utf-8"))
        for side, other in (("a", "b"), ("b", "a")):
            moves["entries"].append({"deal": deal, "date": row["date"], "kind": "trade", "player": row[side]["sends"],
                                     "bbr_id": row[side]["bbr_id"], "from": row[side]["club"], "to": row[other]["club"],
                                     "salary_2003_04": row[side]["salary"]})
        executed.append(deal)
    if executed:
        path = root / ledger_path(SEASON)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(moves, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return written, executed
