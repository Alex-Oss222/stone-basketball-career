"""Symmetric league, phase 3: trades between two real clubs (docs/symmetric_league_design.md).

Only while `league_book.active(date)`. Once a week (Mondays) up to the deadline, every pair of real clubs is
searched for deals of up to three rotation players for up to two (MAX_PLAYERS) that both clubs gain from on their own objectives:
- values: `trades.Assets.player_value` split into this season and the future, weighted by each club's stance
  (`STANCE_WEIGHTS`), times its skill fit for the arriving player (`skill_fit.py`, the club's own needs);
- legality: the season's agreement's salary rule (`agreement.terms`: incoming at most 115% of outgoing plus $100,000
  under the 1999 agreement, 125% under the 2005 agreement from 2005-06; deals before AGREEMENT_MATCH_FROM used 115% in
  every season), unless the club is under the cap after the trade; untouchables stay unless the club gains
  UNTOUCHABLE_MARGIN; the deadline;
- acceptance: each club's chance is `trades.acceptance` of its own gain; a deal is proposed only when both
  clear SEARCH_MIN_ACCEPT, and the best mutual gain league-wide is offered first.
At most MAX_PER_WEEK deals a week are put to the engine, one decision packet per deal (accept with the
product of the two chances); a drawn acceptance is written to `league_moves.json`. Same evidence for every
club, no hindsight: values read only last season's production (2002-03 in the first season, then the previous simulated
season), this season's closed games and dated contracts.

Trade consent (2005 agreement, deals decided from `trades.CONSENT_FROM`, 2005-12-01; cbafaq05 Q83): a player under a
one-year contract whose club will hold his Larry Bird or Early Bird rights at its end (`trades.ConsentBook`) cannot be
traded without his consent. The rule is Miami's: a deal is proposed only when each holder would plausibly consent
(`trades.consent_chance` at SEARCH_MIN_ACCEPT, as each club's own chance), and his answer is folded into the deal's one
packet (`trades.consent_options`: asked only once both clubs agree; a refusal, REFUSED + his id, voids the deal and
nothing moves). The proposal carries the holders (`consent`); an executed deal marks each holder's move with his
consent and the rights he lost (`consent.rights_lost`), which the next summer market reads (`trades.lost_bird_rights`).
From the same date (NEWLY_SIGNED_FROM) a deal never moves a player signed in the league year before he may be traded
(cbafaq05 Q88: three months or December 15, whichever is later, after signing as a free agent in the summer market or
to a rest-of-season contract; 30 days for a signed first-round pick), the rule Miami's desk applies to a partner's
player (`trades.signing_block`).
"""
from datetime import date, timedelta
import json
from pathlib import Path

from .league_book import LeagueBook, active
from .league_moves import effective_roster, ledger_path, read as read_moves
from .trades import (ACCEPT_FLOOR, CBA_PATH, CONSENT_FROM, MIAMI, SEARCH_MIN_ACCEPT, SEASON_LABELS_FROM, STANCE_WEIGHTS,
                     UNDER_CONTRACT, UNTOUCHABLE_MARGIN, Assets, ConsentBook, acceptance, consent_basis, consent_chance, consent_options,
                     consent_question, in_season_signings, market_signings, read_json, signing_block)

ROOT = Path(__file__).resolve().parents[1]


def deadline(day, root=ROOT):
    """The trade deadline of the season `day` belongs to (runtime/seasons.py)."""
    from .seasons import dates, season_of_date
    return dates(season_of_date(day), root)["trade_deadline"]


def draws_dir(season):
    return Path(f"career/Dwyane_Wade/{season}/League/Trade_Draws")
MAX_PER_WEEK = 2                     # calibrated against 16 real trades from December 3 to the deadline (rules file)
ROTATION_CANDIDATES = 9
TRIPLE_CANDIDATES = 7               # judgement: a three-player package comes from a club's top seven by minutes
MAX_PLAYERS = 5                     # up to three for two (the user's request, October 2026; was two for one)
MATCH_PERCENT, MATCH_PLUS = 1.15, 100000           # the 1999 rule every deal before AGREEMENT_MATCH_FROM used
AGREEMENT_MATCH_FROM = SEASON_LABELS_FROM          # from this date the season's agreement's rule (`agreement.terms`, 125% from
                                                   # 2005-06, as Miami's desk and the summer market read it); forward-only
MIN_MUTUAL_GAIN = 0.06              # a club changes its roster only for a clear gain on its own objective (calibrated)
STATUS_QUO = 1.15                   # judgement: a club values the player it has this much more than an equal arrival
NEWLY_SIGNED_FROM = CONSENT_FROM    # from this date a deal never moves a player signed in the league year before he is tradable
                                    # (cbafaq05 Q88, `trades.signing_block`); forward-only: every deal before it replays unchanged


def salary_rule(on, season, root=ROOT):
    """(agreement, percent, plus) of the salary rule a deal on the date is searched under: the 1999 rule before
    AGREEMENT_MATCH_FROM, then the season's agreement's (`agreement.terms`)."""
    if on < AGREEMENT_MATCH_FROM:
        return "1999", MATCH_PERCENT, MATCH_PLUS
    from .agreement import terms
    t = terms(season, root)
    return t["agreement"], t["trade_match"], t["trade_plus"]


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
        self.consent = ConsentBook(on, root) if on >= CONSENT_FROM else None      # forward-only: earlier deals replay unchanged
        self.signings = {}                                  # the newly signed restriction, from NEWLY_SIGNED_FROM (Miami's desk's rule)
        if on >= NEWLY_SIGNED_FROM:
            self.cba = read_json(CBA_PATH, root)
            self.signings = dict(market_signings(self.season, on, root, exclude=MIAMI), **in_season_signings(self.season, on, root, MIAMI))

    def blocked(self, bbr):
        """Why the player cannot be traded on the date (newly signed or a signed first-round pick: `trades.signing_block`,
        as Miami's desk reads a partner's player), or None; always None before NEWLY_SIGNED_FROM."""
        row = self.signings.get(bbr)
        return signing_block(row, self.on, self.season, self.cba) if row else None

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
        if not hasattr(self, "_caps"):
            from .league_book import club_cap
            self._caps = {c: club_cap(c, self.book.season, self.book.cap, self.book.root) for c in self.rosters}
        if self.payroll[club] - out_salary + in_salary <= self._caps[club]:
            return True
        _, percent, plus = salary_rule(self.on, self.season, self.root)
        return in_salary <= out_salary * percent + plus

    def _packages(self, club):
        """(players, salary) a club can offer: one or two of its rotation, and three from its top TRIPLE_CANDIDATES."""
        from itertools import combinations
        ids = [p["bbr_id"] for p in self.rosters[club][:ROTATION_CANDIDATES]]
        pay = {x: int((self.contracts.get(x) or {}).get("schedule", {}).get(self.season) or 0) for x in ids}
        ids = [x for x in ids if pay[x] and not self.blocked(x)]   # a player without a salary this season, or newly signed, is not tradable here
        groups = [list(c) for n in (1, 2) for c in combinations(ids, n)]
        groups += [list(c) for c in combinations(ids[:TRIPLE_CANDIDATES], 3)]
        return [(g, sum(pay[x] for x in g)) for g in groups]

    def proposals(self):
        """Every legal deal of up to three rotation players for up to two (MAX_PLAYERS moved in all), both clubs clearing
        MIN_MUTUAL_GAIN, best first. The salary rule and roster limits are checked on salaries alone first."""
        clubs = sorted(self.rosters)
        packages = {c: self._packages(c) for c in clubs}
        found = []
        for i, a in enumerate(clubs):
            for b in clubs[i + 1:]:
                for pa, sa in packages[a]:
                    for pb, sb in packages[b]:
                        if len(pa) + len(pb) > MAX_PLAYERS or (len(pa) == 3 and len(pb) == 3):
                            continue
                        if not (self.legal(a, sa, sb) and self.legal(b, sb, sa)):
                            continue
                        if (len(self.rosters[a]) - len(pa) + len(pb) > 15 or len(self.rosters[b]) - len(pb) + len(pa) > 15):
                            continue
                        row = self.evaluate(a, pa, b, pb)
                        if row:
                            found.append(row)
        found.sort(key=lambda r: (-min(r["gain"].values()), r["id"]))
        return found

    def evaluate(self, a, a_out, b, b_out):
        a_out, b_out = list(a_out) if isinstance(a_out, (list, tuple)) else [a_out], list(b_out) if isinstance(b_out, (list, tuple)) else [b_out]
        ca, cb = [self.contracts.get(x) for x in a_out], [self.contracts.get(x) for x in b_out]
        if not all(ca) or not all(cb) or any(self.blocked(x) for x in a_out + b_out):
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
        consent = self.consent_rows(a, a_out, b, b_out)
        if any(r["p"] < SEARCH_MIN_ACCEPT for r in consent):
            return None                                    # a club does not propose what a holder would plausibly refuse
        tag = "-".join(sorted(a_out + b_out))
        row = {"id": f"{self.season}-league-trade-{self.on}-{tag}", "date": self.on, "clubs": [a, b],
               "a": {"club": a, "sends": [c["player"] for c in ca], "bbr_ids": a_out, "salary": sa},
               "b": {"club": b, "sends": [c["player"] for c in cb], "bbr_ids": b_out, "salary": sb},
               "gain": gain, "accept": chances, "both": round(chances[a] * chances[b], 6)}
        if consent:
            row["consent"] = consent
        return row

    def consent_rows(self, a, a_out, b, b_out):
        """The players the deal moves whose consent it needs, each with his chance (`trades.consent_chance` on the two
        clubs' rosters before and after the deal); empty before CONSENT_FROM."""
        if self.consent is None:
            return []
        rows = []
        for club, out, other, inc in ((a, a_out, b, b_out), (b, b_out, a, a_out)):
            for x in out:
                entry = self.contracts.get(x) or {}
                status = self.consent.status(x, club, entry.get("player"))
                if not status["holds"]:
                    continue
                stay = [p["bbr_id"] for p in self.rosters[club]]
                new = [p["bbr_id"] for p in self.rosters[other] if p["bbr_id"] not in inc] + list(out)
                p, detail = consent_chance(self.assets, status, dict(entry, bbr_id=x), club, other, stay, new, self.root)
                rows.append(dict(detail, player=entry.get("player"), bbr_id=x, held_by=club, to=other,
                                 rights=status["rights"], seasons=status["seasons"], status_basis=status["basis"], p=p))
        return rows

    def packet(self, row):
        from .seasons import season_of_date
        packet = {"event_id": row["id"], "date": row["date"],
                  "question": f"Do {row['a']['club']} and {row['b']['club']} trade {' and '.join(row['a']['sends'])} for {' and '.join(row['b']['sends'])}?",
                  "decider": f"{row['a']['club']} and {row['b']['club']} front offices (engine draw)",
                  "options": {"accept": row["both"], "decline": round(1 - row["both"], 6)},
                  "basis": (f"gains on own objectives {row['gain']}; acceptance {row['accept']}; {salary_rule(row['date'], season_of_date(row['date']))[0]} salary rule met; "
                            "symmetric league phase 3 (runtime/league_trades.py)")}
        rows = row.get("consent") or []
        if rows:
            packet.update(options=consent_options(row["both"], rows), question=packet["question"] + consent_question(rows),
                          decider=packet["decider"] + f"; {', '.join(r['player'] for r in rows)} (consent, simulated player)",
                          basis=packet["basis"] + "." + consent_basis(rows))
        return packet


def weekly(root=ROOT, day=None, market=None):
    """Write the week's packet(s) and execute drawn acceptances. Returns (packets_written, moves_written)."""
    from .season_market import for_date as Market   # the season's own market (2003 Market in 2003-04)
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
        consented = {r["bbr_id"]: r for r in row.get("consent") or []}      # an accepted deal: every holder consented
        for side, other in (("a", "b"), ("b", "a")):
            for name, bbr in zip(row[side]["sends"], row[side]["bbr_ids"]):
                entry = {"deal": deal, "date": row["date"], "kind": "trade", "player": name, "bbr_id": bbr,
                         "from": row[side]["club"], "to": row[other]["club"]}
                if bbr in consented:
                    entry["consent"] = {"answer": "consented", "rights_lost": consented[bbr]["rights"], "seasons": consented[bbr]["seasons"],
                                        "p": consented[bbr]["p"], "rule": "trade_consent_one_year_contract (cbafaq05 Q83): "
                                        "a Non-Bird free agent of his new club"}
                moves["entries"].append(entry)
        executed.append(deal)
    if executed:
        path = root / ledger_path(SEASON)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(moves, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return written, executed
