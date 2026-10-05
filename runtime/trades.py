"""Trades between simulated Miami and a real club (docs/front_office_design.md, section 7).

Legality follows the 1999 rules as recorded in `nba_1999_cba_rules.json` (the module
names the rule it used, inferred ones included). Values follow the design: a
player's production value above replacement with a contract term, picks from a
1999-era chart placed by the owning club's last record, a star premium before
summing. A real club's answer is a logistic draw of its value change under its
posture, written as a decision packet the engine draws; the same proposal on
the same date gives the same packet. Nothing here writes career records.

Sign-and-trade (design 7.1, `trades.sign_and_trade` in the rules file): a trade whose
`sign_and_trade_in` (Miami acquires a real club's free agent whom the incumbent signs
with full Bird rights and trades at once) or `sign_and_trade_out` (Miami's own free agent,
agreed on the desk, whom Miami signs with his full Bird rights and trades in the same
transaction) names the player, his contract and the base-year compensation attached at
the signing. The signing is part of the trade on both sides: the player is unsigned until
the trade executes, so the newly-signed restriction (which starts at a signing) never
arises for it, while a player Miami has already re-signed is an ordinary signed player
whom that restriction binds, whatever label the proposal carries. The player appears in
`miami_in` or `miami_out` like any other and `resolve` gives him a synthetic contract entry.
"""
from datetime import date, timedelta
import hashlib
import json
import math
from pathlib import Path

from .camp import playable
from .contracts import club_ledger
from .market import UNDATED_EXIT
from .valuation import read

ROOT = Path(__file__).resolve().parents[1]
SEASON = "2003-04"
MIAMI = "Miami Heat"
TEAM = Path(f"career/Dwyane_Wade/{SEASON}/00_Team")
CBA_PATH = Path("library/2003/league/nba_1999_cba_rules.json")
CAP_RULES_PATH = Path("library/2003/league/nba_2003_04_cap_rules.json")
STANDINGS_PATH = Path("library/2003/league/nba_2002_03_standings.json")
CONTRACTS_PATH = Path("library/2003/league/nba_2003_contracts.json")
END_OF_SEASON_PATH = Path("library/2003/league/nba_2003_end_of_season.json")
TRANSACTIONS_PATH = Path("library/2003/league/nba_2003_offseason_transactions.json")
PICKS_PATH = TEAM / "Finances/draft_picks.json"
MORATORIUM = ("2003-07-01", "2003-07-15")
SIGNING_OPENS = "2003-07-16"
PROTAGONIST = "Dwyane Wade"
UNDER_CONTRACT = ("under_contract", "under_rookie_contract", "under_contract_unverified", "minimum_contract_unverified")
NOT_TRADEABLE_WORDS = ("free_agent", "declined", "pending", "renounced", "traded", "signed_elsewhere", "unsigned", "draft")

# Judgement constants (design 7.2 to 7.4), named so they can be revisited.
REPLACEMENT_VALUE = 5.0                  # efficiency per game of a minimum player (valuation.py)
POINTS_PER_EFFICIENCY = 0.25             # value points per efficiency point above replacement (a 25-a-game star is 5)
CONTRACT_YEARS_COUNTED = 3               # seasons of surplus or burden counted
CONTRACT_TERM_LIMITS = (-2.0, 2.0)       # value points
EXPIRING_RELIEF_PER_5M = 0.3             # for a club over the tax projection
NEGATIVE_SHARE = 0.05                    # a negative asset counts at a twentieth
STAR_EXPONENT = 7                        # Basketball GM: assets above 1 are raised to this before summing
TOP_PICK_VALUE, PICK_DECAY = 4.0, 0.0555  # chart: value(slot) = TOP x exp(-decay x (slot - 1)); 1st pick about 5x the 30th
SECOND_ROUND_VALUE = 0.1
FUTURE_PICK_REGRESSION = 0.5             # slots regress halfway to the middle each year further out
MIAMI_PICK_PESSIMISM = 4                 # Miami's own picks are placed this many slots later than its record says
POSTURE = {"contending": {"players": 1.15, "picks": 0.7, "old_players": 1.0}, "middle": {"players": 1.0, "picks": 1.0, "old_players": 1.0},
           "rebuilding": {"players": 0.9, "picks": 1.3, "old_players": 0.7}}
POSTURE_ORDER = ("contending", "middle", "rebuilding")   # partners asked first in an own sign-and-trade-out
CONTENDING_WINS, REBUILDING_WINS, OLD_AGE = 50, 30, 30
ACCEPT_SLOPE, ACCEPT_LIMITS = 6.0, (0.02, 0.90)   # legacy curve (closed decisions only); see the club objectives below
# Club objectives (design 7.5, November 2003). A real club answers on its own objective, not on a league-wide
# talent score: this season's production, future surplus and picks, weighted by its stance. Judgement constants.
STANCE_WEIGHTS = {"contending": {"now": 1.0, "future": 0.35, "picks": 0.6, "cash": 0.2},
                  "middle": {"now": 0.7, "future": 0.7, "picks": 1.0, "cash": 0.5},
                  "rebuilding": {"now": 0.35, "future": 1.0, "picks": 1.4, "cash": 1.0}}
MIAMI_WEIGHTS = {"now": 1.0, "future": 0.6, "picks": 0.8, "cash": 0.3}   # trying to win around a rookie Wade: now dominates
STANCE_YOUNG_AGE = 25.5                  # a middle club whose top eight average this young or less is building
AGE_FACTOR = ((23, 1.15), (28, 1.0), (30, 0.9), (32, 0.75), (99, 0.55))   # expected production ahead, by age
WALK_YEAR_DISCOUNT = {"contending": 0.9, "middle": 0.75, "rebuilding": 0.65}  # a seller's own expiring veteran (28+): he walks in July
TOP_PICK_ROOKIE_SALARY = 1800000         # rookie-scale 2003-04 salary at or above this stands for a top-ten pick
UNTOUCHABLE_MARGIN = 0.20                # a club parts with an untouchable only for this much more on its own objective
ACCEPT_FLOOR = -0.03                     # below this on the partner's objective: a flat no (no draw)
ACCEPT_HURDLE, ACCEPT_STEEPNESS = 0.06, 25.0   # a flat deal is usually passed; 50% at +6%, about 90% at +15%
ACCEPT_BOUNDS = (0.02, 0.95)
DUMP_VALUE_PER_5M = 0.25                 # value points per $5M of a season's salary a club sheds on purpose
SEARCH_MIN_ACCEPT = 0.40                 # Miami proposes only what the partner would plausibly take
MAX_OUT, MAX_IN = 2, 2                   # players a search proposal moves each way
# Distressed assets (design 7.5 item 6): an injured player's current-season production counts at this share to the
# club that would take him on (judgement, within the 15-40% discount). Evidence on the date only: Miami's injured
# list with an injury reason, or a real player who missed all of his club's last INJURY_GAMES closed games.
INJURY_DISCOUNT = 0.75
INJURY_GAMES = 3
INJURY_FROM = "2003-12-01" 
# Current form and control (from FORM_FROM; judgement): a club values a player on his closed 2003-04 production
# as well as 2002-03, the new season counting as its games against FORM_PRIOR_GAMES of last season's; and a young
# player's future runs past his contract through restricted free agency or Bird rights (CONTROL_AFTER_CONTRACT).
FORM_FROM = "2003-12-01"
FORM_PRIOR_GAMES = 20
CONTROL_AFTER_CONTRACT = ((25, 2), (29, 1), (99, 0))   # by age: extra seasons a club expects to keep him               # earlier trade decisions keep the values they were drawn with
SEARCH_SKILL_FIT = 1.10                  # a candidate this good a fit is searched even where Miami has the minutes
SEARCH_MIN_GAIN = 0.05                   # Miami's value gain for a proposal to be worth making
# Sign-and-trade (design 7.1 and 7.4)
SIGN_AND_TRADE_RIGHTS = ("bird",)        # both directions; inferred (one 2003 observation: Miller, full Bird, 7 years); Early Bird / Non-Bird / room not found
SIGN_AND_TRADE_RIGHTS_SHARE = 0.25       # judgement: the incumbent values the player it would otherwise lose for nothing at a quarter of his value (club-objective model; real sign-and-trade returns were small, e.g. Boston for Walker in 2005)
PARTNER_LOCATION = 0.5                   # judgement: a partner club's location appeal in the player's consent draw
OWN_OUT_ACCEPT_MARGIN = 0.1              # judgement: an own sign-and-trade-out goes to the first partner whose acceptance clears the floor by this
BIRD_RAISE = 0.125


def read_json(path, root=ROOT):
    return read(path, root)


def seasons_from(first, years):
    start = int(first[:4])
    return [f"{start + i}-{str(start + i + 1)[-2:]}" for i in range(years)]


# -- assets ------------------------------------------------------------------------------------
def dated_inventory(on, valuation, root=ROOT):
    """Each real club's contract inventory as its roster stands on `on`.

    The June 26, 2003 inventory is the source of the terms; who holds each contract on the date comes from
    the world's dated moves (`club_strength.League`: real signings, trades and waivers to the date, rule 1
    skipping any involving Miami, rule 2 removing the players Miami holds). A traded contract travels with
    its player. A player who joined by signing has no terms in the inventory, so he is listed with his old
    entry's free-agent status and is never a trade candidate. Miami's own entry is never used here."""
    from .club_strength import League
    june = read_json(CONTRACTS_PATH, root)["clubs"]
    league = League(on, valuation.value, root)
    rosters = league.rosters
    on_date = {b: club for club, members in rosters.items() for b in members}
    from .league_book import active
    if active(on):
        # Symmetric league: who holds each contract is the simulated league on the date (real moves after the
        # activation date are not applied; docs/symmetric_league_design.md).
        from .league_moves import effective_roster
        on_date = {p["bbr_id"]: club for club in june if club != MIAMI for p in effective_roster(club, on, SEASON, root)}
    in_baseline = set().union(*league.baseline.values())
    # Terms of the summer's signings: reported years and total spread flat over the seasons, or, unreported,
    # the minimum for the player's service (an estimate, labelled so). Rule 1 skips moves involving Miami.
    signed = {}
    for row in read_json(TRANSACTIONS_PATH, root)["signings"]:
        if (row.get("kind") in ("signing", "re_sign", "sign_and_trade", "match", "match_declined", "offer_sheet", "rookie_signing") and row.get("bbr_id")
                and not row.get("involves_miami") and row.get("to") != MIAMI and (row.get("date") or UNDATED_EXIT) <= on):
            signed[row["bbr_id"]] = row
    service = valuation.service

    def signed_entry(p, holder):
        row = signed.get(p["bbr_id"])
        if row is None or row.get("to") != holder:
            return None
        start = int(SEASON[:4])
        if row.get("years") and row.get("total"):
            per = int(round(row["total"] / row["years"]))
            seasons = [f"{start + i}-{str(start + i + 1)[-2:]}" for i in range(row["years"])]
            return dict(p, status="under_contract", schedule={s_: per for s_ in seasons},
                        amount_kind={s_: "contract_salary" for s_ in seasons}, terms_source="reported total, spread flat",
                        signed_date=row.get("date"))
        return dict(p, status="under_contract", schedule={SEASON: valuation.minimum(service.get(p["bbr_id"]))},
                    amount_kind={SEASON: "contract_salary"}, terms_source="unreported: minimum for his service (estimate)",
                    signed_date=row.get("date"))

    placed = {club: [] for club in june}
    for club, entry in june.items():
        for p in entry["players"]:
            b = p.get("bbr_id")
            if not b:
                placed[club].append(p)            # unidentified rows stay where June had them
                continue
            if b in on_date:
                holder = on_date[b]
            elif b in in_baseline:
                continue                          # waived, or held by Miami: on no real club's roster
            else:
                holder = club                     # under contract but off the end-of-season list (injured all year)
            if holder != MIAMI and holder in placed:
                placed[holder].append(signed_entry(p, holder) or dict(p, held_on=on))
    return {club: (entry if club == MIAMI else dict(entry, players=placed[club], as_of=on)) for club, entry in june.items()}


class Assets:
    """Values of players and picks on a date, from on-date evidence."""

    def __init__(self, on, market, root=ROOT):
        self.on, self.market, self.root = on, market, Path(root)
        self.valuation = market.valuation
        self.standings = read_json(STANDINGS_PATH, root)["clubs"]
        self.contracts = dated_inventory(on, self.valuation, root)
        self.cap_rules = read_json(CAP_RULES_PATH, root)
        self.tax_line = self.cap_rules.get("luxury_tax_line_projection_july_2003", 57000000)
        self.positions = {}
        self._payroll = {}
        self._stance = {}
        for club, entry in read_json(END_OF_SEASON_PATH, root)["clubs"].items():
            for p in entry["players"]:
                if p.get("bbr_id"):
                    self.positions[p["bbr_id"]] = (club, p.get("position") or "SF", p.get("depth") or 9)

    def posture(self, club):
        """The club's stance on the date: its 2002-03 record, and a middle club whose core is young is building
        (the top eight of its dated roster by production; judgement STANCE_YOUNG_AGE)."""
        if club not in self._stance:
            wins = self.standings.get(club, {}).get("wins", 41)
            stance = "contending" if wins >= CONTENDING_WINS else "rebuilding" if wins <= REBUILDING_WINS else "middle"
            if stance == "middle":
                ages = sorted(((self.valuation.value(p["bbr_id"]) or 0.0, self.valuation.age(p["bbr_id"]))
                               for p in self.contracts.get(club, {}).get("players", []) if p.get("bbr_id")), reverse=True)[:8]
                ages = [a for _, a in ages if a is not None]
                if ages and sum(ages) / len(ages) <= STANCE_YOUNG_AGE and wins < 41:
                    stance = "rebuilding"
            self._stance[club] = stance
        return self._stance[club]

    def payroll(self, club):
        """The club's 2003-04 salary on the date, from its dated inventory (`dated_inventory`), not the June list."""
        if club == MIAMI:
            return None   # Miami's ledger is the front office's
        if club not in self._payroll:
            entry = self.contracts.get(club, {})
            self._payroll[club] = (sum(int(p["schedule"].get(SEASON) or 0) for p in entry.get("players", [])
                                       if p.get("status") in UNDER_CONTRACT or "option_exercised" in (p.get("status") or ""))
                                   # a first-round pick counts at his scale amount, signed or not (1999 CBA cap hold)
                                   + sum(int(d.get("current_cap_hold") or 0) for d in entry.get("draft_rights", [])))
        return self._payroll[club]

    def untouchable(self, club, player):
        """A club's young top pick on his rookie scale, or one of its two most valuable players to itself."""
        if player.get("status") == "under_rookie_contract" and self.salary(player) >= TOP_PICK_ROOKIE_SALARY:
            return "top-ten pick on his rookie scale"
        weights = STANCE_WEIGHTS[self.posture(club)]
        ranked = sorted((self.club_value(self.player_value(p), weights), p.get("bbr_id"))
                        for p in self.contracts.get(club, {}).get("players", []) if p.get("bbr_id") and p.get("status") in UNDER_CONTRACT)
        top = {b for _, b in ranked[-2:]}
        return "one of its two most valuable players" if player.get("bbr_id") in top else None

    @staticmethod
    def club_value(v, weights, walk_discount=1.0):
        """One player's value to a club with these weights: this season's production and the future."""
        total = (weights["now"] * v["now"] + weights["future"] * v["future"]) * walk_discount + weights["cash"] * v["relief"]
        return total if total >= 0 else total * NEGATIVE_SHARE

    def salary(self, player):
        """2003-04 salary of a player entry (Miami sheet or inventory shape)."""
        return int(player["schedule"].get(SEASON) or 0)

    def years_left(self, player):
        return sum(1 for s, v in player["schedule"].items() if s >= SEASON and v and player.get("amount_kind", {}).get(s) == "contract_salary")

    def player_value(self, player, for_club=None):
        """Value points of a player under contract: production above replacement plus his contract term."""
        bbr = player.get("bbr_id")
        value = self.form_value(bbr) if bbr else None
        if value is None:
            production = 0.0
            basis = "no 2002-03 evidence: production counted at replacement"
        else:
            production = max(0.0, value - REPLACEMENT_VALUE) * POINTS_PER_EFFICIENCY
            basis = (f"production value {value:.1f} (2002-03 blended with closed 2003-04 games)" if self.on >= FORM_FROM
                     else f"2002-03 production value {value:.1f}")
        salary, years = self.salary(player), min(CONTRACT_YEARS_COUNTED, max(1, self.years_left(player)))
        worth = self.valuation.market_price(value, bbr) if value is not None else self.valuation.minimum(0)
        term = (worth - salary) * years / self.valuation.mid_level * 0.5 if salary else 0.0
        term = max(CONTRACT_TERM_LIMITS[0], min(CONTRACT_TERM_LIMITS[1], term))
        total = production + term
        age = self.valuation.age(bbr) if bbr else None
        if age is None and player.get("date_of_birth"):
            from .valuation import age_on
            age = age_on(player["date_of_birth"], self.on)
        relief = 0.0
        if for_club and years == 1 and self.payroll(for_club) and self.payroll(for_club) > self.tax_line:
            relief = EXPIRING_RELIEF_PER_5M * salary / 5000000
        total += relief
        if total < 0:
            total *= NEGATIVE_SHARE
        # The club-objective split: this season's production, and the future (production ahead by age over
        # the years of control, plus the contract's surplus or burden).
        factor = next(f for limit, f in AGE_FACTOR if (age or 27) <= limit)
        control = years + (1 if player.get("status") == "under_rookie_contract" else 0)
        if self.on >= FORM_FROM:
            control = max(control, years + next(extra for limit, extra in CONTROL_AFTER_CONTRACT if (age or 27) <= limit))
        future = production * factor * min(CONTRACT_YEARS_COUNTED, control - 1) / 2 + term
        return {"player": player["player"], "bbr_id": bbr, "value": round(total, 3), "production": round(production, 3),
                "contract_term": round(term, 3), "relief": round(relief, 3), "salary": salary, "years": years,
                "age": age, "basis": basis, "now": round(production, 3), "future": round(future, 3),
                "walk_year": years == 1 and (age or 0) >= 28 and player.get("status") != "under_rookie_contract"}

    def injured(self, player_name, club):
        """On-date evidence that a player is hurt: Miami's injured list (an injury, not a reserve listing),
        or a real player absent from all of his club's last INJURY_GAMES closed games while it played."""
        if self.on < INJURY_FROM:
            return False
        if not hasattr(self, "_injured"):
            self._injured = self._injury_evidence()
        return (club, player_name) in self._injured

    def _injury_evidence(self):
        out = set()
        ledger = read_json(TEAM / "Transactions/injured_list.json", self.root) if (self.root / TEAM / "Transactions/injured_list.json").is_file() else {"entries": []}
        for e in ledger["entries"]:
            if e["placed"] <= self.on and (e["activated"] is None or e["activated"] > self.on) and e["reason"].startswith("injury"):
                out.add((MIAMI, e["player"]))
        from .write_back import closed_results
        recent = {}
        for row in closed_results(self.root, SEASON, self.on):
            r = row["result"]
            for side in ("home", "away"):
                recent.setdefault(r[side], []).append({p["player_id"] for p in r["player_stats"][side] if p["minutes"] > 0})
        for club, games in recent.items():
            last = games[-INJURY_GAMES:]
            if club == MIAMI or len(last) < INJURY_GAMES:
                continue
            before = games[:-INJURY_GAMES]
            if len(before) < INJURY_GAMES:
                continue
            seen = set().union(*last)
            # A regular (in at least half his club's earlier games) who then vanished, not a reserve's coach's decision.
            regulars = {n for n in set().union(*before) if sum(n in g for g in before) >= len(before) / 2}
            for name in regulars - seen:
                out.add((club, name))
        return out

    def form_value(self, bbr):
        """Production value on the date: 2002-03, blended with closed 2003-04 games from FORM_FROM."""
        prior = self.valuation.value(bbr)
        if self.on < FORM_FROM or bbr is None:
            return prior
        if not hasattr(self, "_season_totals"):
            self._season_totals = self._closed_totals()
        totals = self._season_totals.get(bbr)
        if not totals or not totals["games"]:
            return prior
        from .valuation import production_value
        current = production_value(totals, self.valuation.age(bbr))
        if prior is None:
            return current
        g = totals["games"]
        return (prior * FORM_PRIOR_GAMES + current * g) / (FORM_PRIOR_GAMES + g)

    def _closed_totals(self):
        from .rotations import load_rosters
        from .write_back import closed_results
        names = {}
        for entry in load_rosters(SEASON, self.root).values():
            for p in entry["players"]:
                names.setdefault(p["player_id"], p["bbr_id"])
        roster = read_json(TEAM / "Team/Roster/roster.json", self.root)
        for p in roster["players"]:
            if p.get("bbr_id"):
                names[p["name"]] = p["bbr_id"]
        keys = {"points": "pts", "offensive_rebounds": "orb", "defensive_rebounds": "drb", "assists": "ast", "steals": "stl",
                "blocks": "blk", "field_goals_attempted": "fga", "field_goals_made": "fgm", "free_throws_attempted": "fta",
                "free_throws_made": "ftm", "turnovers": "tov"}
        out = {}
        for row in closed_results(self.root, SEASON, self.on):
            for side in ("home", "away"):
                for line in row["result"]["player_stats"][side]:
                    bbr = names.get(line["player_id"])
                    if not bbr or line["minutes"] <= 0:
                        continue
                    t = out.setdefault(bbr, dict({k: 0 for k in keys}, games=0, minutes=0.0))
                    t["games"] += 1
                    t["minutes"] += line["minutes"]
                    for k, src in keys.items():
                        t[k] += line[src]
        return out

    def pick_value(self, pick, owner_record_club, miami_own=False):
        """A draft pick from the chart, placed by the owning club's last record and regressed for later years."""
        if pick["round"] == 2:
            return {"value": SECOND_ROUND_VALUE, "slot": None, "basis": "second-round pick"}
        wins = self.standings.get(owner_record_club, {}).get("wins", 41)
        order = sorted(self.standings.values(), key=lambda r: r["wins"])
        slot = 1 + sum(1 for r in order if r["wins"] < wins)      # worst record picks first (lottery ignored)
        years_out = max(0, pick["year"] - 2004)
        slot = 15 + (slot - 15) * FUTURE_PICK_REGRESSION ** years_out
        if miami_own:
            slot += MIAMI_PICK_PESSIMISM
        slot = max(1, min(29, slot))
        value = TOP_PICK_VALUE * math.exp(-PICK_DECAY * (slot - 1))
        return {"value": round(value, 3), "slot": round(slot, 1), "basis": f"{owner_record_club} {wins} wins in 2002-03; {pick['year']} first regressed {years_out} year(s)"}

    @staticmethod
    def premium(values):
        """Sum with the star premium: every asset above 1 is raised to STAR_EXPONENT first."""
        return sum(v ** STAR_EXPONENT if v > 1 else v for v in values)

    @staticmethod
    def effective(values):
        """The premium sum brought back to the scale of one asset (its STAR_EXPONENT-th root), so a
        package is compared as the single player it would be worth: two 2s make about a 2.2, not a 4."""
        total = Assets.premium(values)
        return total ** (1 / STAR_EXPONENT) if total > 1 else total


def acceptance(v):
    """The partner's chance of accepting, from its objective (`TradeDesk.valuation`), or None for a flat no:
    below the floor (a salary dump counted), or an untouchable without UNTOUCHABLE_MARGIN more."""
    gain = v["objective_gain"]
    if v.get("untouchable") and gain < UNTOUCHABLE_MARGIN:
        return None
    if gain < ACCEPT_FLOOR:
        return None
    p = 1 / (1 + math.exp(-ACCEPT_STEEPNESS * (gain - ACCEPT_HURDLE)))
    return round(min(ACCEPT_BOUNDS[1], max(ACCEPT_BOUNDS[0], p)), 3)


# -- legality ------------------------------------------------------------------------------------
def months_after(day, months):
    d = date.fromisoformat(day)
    month = d.month - 1 + months
    return date(d.year + month // 12, month % 12 + 1, min(d.day, 28)).isoformat()


def st_in(trade):
    return trade.get("sign_and_trade_in")


def st_out(trade):
    return trade.get("sign_and_trade_out")


def is_sign_and_trade(trade):
    return bool(st_in(trade) or st_out(trade)) or trade.get("kind") == "sign_and_trade"


class TradeDesk:
    """Legality and acceptance of a proposal between Miami and one real club on a date."""

    def __init__(self, on, front_office, root=ROOT):
        self.on, self.fo, self.root = on, front_office, Path(root)
        self.market = front_office.market
        self.assets = Assets(on, self.market, root)
        self.cba = read_json(CBA_PATH, root)
        self.cap_rules = read_json(CAP_RULES_PATH, root)
        self.cap = self.market.planning_cap(on)
        self.signings = {r["bbr_id"]: r for r in read_json(TRANSACTIONS_PATH, root)["signings"]
                         if r.get("bbr_id") and r["kind"] in ("signing", "re_sign", "sign_and_trade", "match", "match_declined", "rookie_signing")
                         and r["to"] != MIAMI and (r["date"] or UNDATED_EXIT) <= on}
        self.picks = read_json(PICKS_PATH, root) if (self.root / PICKS_PATH).exists() else {"picks": []}
        self.needing_consultation = []

    # -- lookups ------------------------------------------------------------------------------
    def miami_player(self, name):
        """Miami's sheet entry (with the register's bbr_id, which the sheet may lack) and register entry."""
        p = next((p for p in self.fo.sheet["players"] if p["player"] == name), None)
        r = next((r for r in self.fo.roster["players"] if r["name"] == name), None)
        if p is not None and r is not None:
            p = dict(p, bbr_id=p.get("bbr_id") or r.get("bbr_id"), date_of_birth=r.get("date_of_birth"))
        return p, r

    def partner_player(self, club, name):
        entry = self.assets.contracts.get(club)
        if not entry:
            return None
        return next((p for p in entry["players"] if p["player"] == name), None)

    def _synthetic(self, st):
        """A contract entry for the sign-and-trade player, shaped like the sheet and the inventory."""
        return {"player": st["player"], "bbr_id": st["bbr_id"], "status": "under_contract", "schedule": dict(st["schedule"]),
                "amount_kind": dict(st["amount_kind"]), "prior_season_salary": st.get("prior_season_salary"), "route": "sign_and_trade",
                "base_year_compensation": st.get("base_year_compensation"), "date_of_birth": self.assets.valuation.birth.get(st["bbr_id"])}

    def resolve(self, name, trade):
        """The contract entry a name in the proposal stands for: the synthetic sign-and-trade entry, Miami's
        sheet entry (outgoing) or the partner's inventory entry (incoming)."""
        for st in (st_in(trade), st_out(trade)):
            if st and st["player"] == name:
                return self._synthetic(st)
        if name in trade.get("miami_out", []):
            return self.miami_player(name)[0]
        return self.partner_player(trade["partner"], name)

    def miami_tradeable(self):
        """Miami players under contract who may be traded on the date, with the rule that blocks the others."""
        out = []
        for entry in self.fo.sheet["players"]:
            p, r = self.miami_player(entry["player"])
            if not r or not p["schedule"].get(SEASON) or p["status"] in ("renounced", "released", "traded", "signed_elsewhere", "voided", "waived"):
                continue
            if any(w in p["status"] for w in NOT_TRADEABLE_WORDS):
                continue
            block = self.blocked(p)
            if not block:
                out.append(p)
        return out

    def blocked(self, player):
        """Why a player cannot be traded on the date (newly signed, signed first-round pick, Wade)."""
        if player["player"] == PROTAGONIST:
            return "Wade's trade would change the simulated club (AGENTS.md); not supported"
        signed = player.get("signed_date")
        if signed and signed >= "2003-07-01":
            rule = self.cba["trades"]
            if player.get("route") == "rookie_scale":
                until = (date.fromisoformat(signed) + timedelta(days=rule["signed_first_round_pick_restriction_days"]["days"])).isoformat()
                if self.on < until:
                    return f"signed first-round pick: not tradable until {until} ({rule['signed_first_round_pick_restriction_days']['status']})"
            else:
                until = max(months_after(signed, 3), "2003-12-15")
                if self.on < until:
                    return f"newly signed: not tradable until {until} ({rule['newly_signed_free_agent_restriction']['status']})"
        return None

    def partner_blocked(self, club, player):
        row = self.signings.get(player.get("bbr_id"))
        if row and row["date"] >= "2003-07-01":
            until = max(months_after(row["date"], 3), "2003-12-15")
            if self.on < until:
                return f"newly signed on {row['date']}: not tradable until {until}"
        return None

    def matching_salary(self, player, outgoing_from_miami):
        """Salary for matching. Base-year compensation is read from the flag the signing attached
        (`base_year_compensation.applies`): the greater of half the new salary and the prior salary. A
        legacy Miami entry without the flag keeps the derivation from its route and prior salary."""
        salary = self.assets.salary(player)
        byc = player.get("base_year_compensation")
        prior = (player.get("prior_season_salary") or {}).get("amount") or player.get("previous_salary")
        if byc is not None:
            if byc.get("applies") and prior:
                return max(salary * 0.5, prior), "base-year compensation (inferred for 1999; attached at the signing)"
            return salary, None
        if outgoing_from_miami and player.get("route") in ("bird", "early_bird"):
            if prior and salary > prior * 1.2:
                return max(salary * 0.5, prior), "base-year compensation (inferred for 1999)"
        return salary, None

    def partner_over_cap_after_signing(self, club, first_year):
        """The incumbent's cap position after signing its own free agent (its ledger carries no other holds; inferred)."""
        return (self.assets.payroll(club) or 0) + first_year > self.cap

    def base_year_compensation(self, club, first_year, prior):
        """The flag attached at a signing by a real club: a raise over 20% while over the cap after the signing."""
        rule = self.cba["trades"]["base_year_compensation"]
        applies = bool(prior) and first_year > prior * 1.2 and self.partner_over_cap_after_signing(club, first_year)
        return {"applies": applies, "status": f"inferred: {rule['applies_when']}; the incumbent's ledger carries no other holds ({rule['attached_at']})"}

    # -- legality ------------------------------------------------------------------------------
    def totals(self, trade):
        """The four salary totals of a proposal and each club's payroll after it.

        Miami's outgoing at full value (`out_full`) and for matching (`out_match`, base-year compensation
        applied); the partner's outgoing at full value (`in_full`) and for matching (`in_match`, base-year
        compensation only for a sign-and-trade player whose signing attached it). A sign-and-trade player's
        salary was never on his signing club's payroll, so each club's post-trade payroll excludes him on
        its own side (`out_contracted`, `in_contracted`)."""
        club = trade["partner"]
        own, acquired = st_out(trade), st_in(trade)
        t = {"out_full": 0.0, "out_match": 0.0, "out_contracted": 0.0, "in_full": 0.0, "in_match": 0.0, "in_contracted": 0.0, "byc_notes": []}
        for name in trade.get("miami_out", []):
            p = self._synthetic(own) if (own and own["player"] == name) else self.miami_player(name)[0]
            if not p:
                continue
            salary, note = self.matching_salary(p, True)
            full = self.assets.salary(p)
            t["out_full"] += full
            t["out_match"] += salary
            if not (own and own["player"] == name):
                t["out_contracted"] += full          # the own sign-and-trade player's salary never reaches Miami's payroll
            if note:
                t["byc_notes"].append(f"{name}: {note}")
        for name in trade.get("miami_in", []):
            if acquired and acquired["player"] == name:
                p = self._synthetic(acquired)
                salary, note = self.matching_salary(p, False)
                t["in_full"] += self.assets.salary(p)
                t["in_match"] += salary
                if note:
                    t["byc_notes"].append(f"{name}: {note}")
                continue
            p = self.partner_player(club, name)
            if not p:
                continue
            full = self.assets.salary(p)
            t["in_full"] += full
            t["in_match"] += full
            t["in_contracted"] += full
        room = self.fo.cap_room(renounce=(own["player"],) if own else ())
        t["miami_after"] = room["committed"] + room["holds"] - t["out_contracted"] + t["in_full"]
        # The player a club signs only to trade to Miami is not also on its payroll under his real contract
        # (the dated inventory may carry the real re-signing that the sign-and-trade replaces).
        real = self.partner_player(club, acquired["player"]) if acquired else None
        t["partner_after"] = ((self.assets.payroll(club) or 0) - (self.assets.salary(real) if real and real.get("terms_source") else 0)
                              + t["out_full"] - t["in_contracted"])
        return t

    def errors(self, trade, ignore_timing=False):
        """Everything that makes the proposal illegal on the date, each naming its rule (totals: `totals`)."""
        errors, rules = [], self.cba["trades"]
        deadline = rules["deadline_2003_04"][:10]
        if self.on > deadline:
            errors.append(f"after the {deadline} trade deadline")
        if not ignore_timing:
            if MORATORIUM[0] <= self.on <= MORATORIUM[1]:
                errors.append(f"no trade during the July moratorium (calendar; {rules['moratorium_trade_ban']['status']})")
            if is_sign_and_trade(trade) and self.on < SIGNING_OPENS:
                errors.append("no contract may be signed before July 16, 2003 (calendar)")
        club = trade["partner"]
        if club == MIAMI or club not in self.assets.contracts:
            errors.append(f"unknown partner club {club!r}")
            return errors
        own, acquired = st_out(trade), st_in(trade)
        if is_sign_and_trade(trade) and bool(own) == bool(acquired):
            errors.append("a sign-and-trade names exactly one of sign_and_trade_in and sign_and_trade_out")
            return errors
        if own and own["player"] not in trade.get("miami_out", []):
            errors.append(f"{own['player']}: the sign-and-trade player must be listed in miami_out")
        if acquired and acquired["player"] not in trade.get("miami_in", []):
            errors.append(f"{acquired['player']}: the sign-and-trade player must be listed in miami_in")
        for name in trade.get("miami_out", []):
            p, r = self.miami_player(name)
            if own and own["player"] == name:
                errors.extend(self.own_out_errors(own, p, r))
                continue
            if not p or not r:
                errors.append(f"{name} is not on Miami's register")
                continue
            if any(w in p["status"] for w in NOT_TRADEABLE_WORDS):
                errors.append(f"{name}: a {p['status']} player cannot be traded outside a sign-and-trade")
                continue
            block = self.blocked(p)
            if block:
                errors.append(f"{name}: {block}")
        for name in trade.get("miami_in", []):
            if acquired and acquired["player"] == name:
                errors.extend(self.acquisition_errors(acquired, club))
                continue
            p = self.partner_player(club, name)
            if not p or p["status"] not in UNDER_CONTRACT:
                errors.append(f"{name} is not under contract with {club} on the inventory")
                continue
            block = self.partner_blocked(club, p)
            if block:
                errors.append(f"{name}: {block}")
        cash_out, cash_in = trade.get("cash_out", 0) or 0, trade.get("cash_in", 0) or 0
        if max(cash_out, cash_in) > rules["cash_per_season_max"]["amount"]:
            errors.append(f"cash above ${rules['cash_per_season_max']['amount']:,} a season ({rules['cash_per_season_max']['status']})")
        # Salary matching for a club over the cap after the trade (115% + $100,000, reported for 1999); a club at or
        # under the cap after the trade absorbs the incoming salary into room (matching_under_cap, inferred).
        pct, plus = rules["matching_over_cap"]["incoming_max_percent_of_outgoing"] / 100, rules["matching_over_cap"]["plus_dollars"]
        t = self.totals(trade)
        byc = f"; {'; '.join(t['byc_notes'])}" if t["byc_notes"] else ""
        if t["miami_after"] > self.cap and t["in_full"] > t["out_match"] * pct + plus:
            errors.append(f"Miami over the cap after the trade: incoming ${t['in_full']:,.0f} exceeds {pct:.0%} of outgoing ${t['out_match']:,.0f} plus ${plus:,} "
                          f"({rules['matching_over_cap']['status']})" + byc)
        if t["partner_after"] > self.cap and t["out_full"] > t["in_match"] * pct + plus:
            errors.append(f"{club} over the cap after the trade: incoming ${t['out_full']:,.0f} exceeds {pct:.0%} of its outgoing ${t['in_match']:,.0f} plus ${plus:,}" + byc)
        # Rosters of at most 15 after the trade (Miami; the partner's count is not on the inventory for the date).
        # The same rule as the cut and the game builder (camp.playable): unsigned draft rights are not a roster spot.
        active = sum(1 for r in self.fo.roster["players"] if playable(r["status"]))
        leaving = [n for n in trade.get("miami_out", []) if not (own and own["player"] == n)]   # the own sign-and-trade player is not on the active register
        if active - len(leaving) + len(trade.get("miami_in", [])) > rules["roster_max_after_trade"]:
            errors.append(f"Miami would carry more than {rules['roster_max_after_trade']} players")
        # Picks: ownership and the Stepien rule.
        owned = {(p["year"], p["round"]) for p in self.picks.get("picks", []) if p.get("owned")}
        for pick in trade.get("picks_out", []):
            if (pick["year"], pick["round"]) not in owned:
                errors.append(f"Miami does not own its {pick['year']} round-{pick['round']} pick on the record (Finances/draft_picks.json)")
        firsts_after = sorted(y for (y, r) in owned if r == 1)
        firsts_after = [y for y in firsts_after if {"year": y, "round": 1} not in trade.get("picks_out", [])]
        years = [p["year"] for p in self.picks.get("picks", []) if p["round"] == 1]
        for y in range(min(years, default=2004), max(years, default=2004)):
            if y not in firsts_after and y + 1 not in firsts_after and (y, 1) in owned | {(p["year"], 1) for p in trade.get("picks_out", [])}:
                errors.append(f"Stepien rule: Miami would lack a first-round pick in {y} and {y + 1} ({rules['stepien_rule']})")
                break
        return errors

    def own_out_errors(self, own, sheet_entry, register_entry):
        """The own sign-and-trade-out player: Miami's unsigned full-Bird free agent, signed on a legal contract and
        traded in the same transaction (`simultaneous_signing_and_trade`, sourced from the Miller example). A player
        Miami has already re-signed is a signed player: the sign-and-trade label does not lift the newly-signed
        restriction from him."""
        errors, rule = [], self.cba["trades"]["sign_and_trade"]
        name = own["player"]
        status = (register_entry or {}).get("status")
        if status == "re_signed" or (sheet_entry or {}).get("status") == "re_signed":
            signed = (sheet_entry or {}).get("signed_date") or (register_entry or {}).get("re_signed_date") or "an earlier day"
            errors.append(f"{name}: already re-signed on {signed}; a sign-and-trade signs and trades in one transaction "
                          f"({rule['simultaneous_status']}), and a signed player is traded as any other")
            block = self.blocked(sheet_entry) if sheet_entry else None
            if block:
                errors.append(f"{name}: {block}")
        elif status != "free_agent_rights_held":
            errors.append(f"{name}: an own sign-and-trade needs an unsigned free agent whose rights Miami holds (register status {status})")
        rights = next((p for p in self.fo.rights["players"] if p["player"] == name), None)
        if not rights or rights.get("bird_status") != "larry_bird" or rights.get("renounced") or rights.get("signed_elsewhere") or rights.get("traded") or rights.get("re_signed"):
            errors.append(f"{name}: an own sign-and-trade needs full Bird rights still held (SIGN_AND_TRADE_RIGHTS {SIGN_AND_TRADE_RIGHTS}; {rule['signing_club_rights_status']})")
        if own.get("non_option_seasons", 0) < rule["min_non_option_seasons"]:
            errors.append(f"{name}: a sign-and-trade contract needs at least three non-option seasons ({rule['min_non_option_seasons_status']})")
        if own.get("route") != "sign_and_trade" and own.get("route") != "bird":
            errors.append(f"{name}: the contract must be a Bird re-signing")
        if (own.get("agreement_date") or self.on) > self.on:
            errors.append(f"{name}: the agreement is dated {own['agreement_date']}, after the trade date")
        return errors

    def acquisition_errors(self, acquired, club):
        """The acquired sign-and-trade player: the partner's unsigned full-Bird free agent on a legal contract."""
        from .cba import terms_errors
        errors, rule = [], self.cba["trades"]["sign_and_trade"]
        name, bbr = acquired["player"], acquired["bbr_id"]
        p = self.market.players.get(bbr)
        if p is None:
            return [f"{name}: not on the league rights file"]
        if p["club"] != club:
            errors.append(f"{name}: his rights belong to {p['club']}, not {club}")
        if p.get("bird_class") not in SIGN_AND_TRADE_RIGHTS:
            errors.append(f"{name}: a sign-and-trade needs full Bird rights (SIGN_AND_TRADE_RIGHTS {SIGN_AND_TRADE_RIGHTS}; his class is {p.get('bird_class')}; {rule['signing_club_rights_status']})")
        if p.get("rfa_eligible"):
            errors.append(f"{name}: a restricted free agent's sign-and-trade is not modeled ({rule['restricted_free_agents']})")
        agreed = acquired.get("agreement_date") or self.on
        if not self.market.available(bbr, agreed):
            e = self.market.exit(bbr)
            errors.append(f"{name}: no longer unsigned on the agreement date {agreed} (real move {e[0]} to {e[1]})")
        if acquired.get("route") != "sign_and_trade":
            errors.append(f"{name}: the contract route must be sign_and_trade")
        terms = acquired.get("terms") or {}
        schedule = [int(acquired["schedule"][s]) for s in seasons_from(SEASON, len(acquired["schedule"]))]
        legal = terms_errors({"schedule": schedule, "guaranteed": acquired.get("guaranteed", sum(schedule)),
                              "non_option_seasons": acquired.get("non_option_seasons", len(schedule))},
                             route="sign_and_trade", years_of_service=p.get("nba_seasons_before_2003_04"),
                             prior_salary=p.get("prior_salary_2002_03"), cap_rules=self.cap_rules, cba=self.cba)
        errors.extend(f"{name}: {e}" for e in legal)
        if terms and terms.get("years") != len(schedule):
            errors.append(f"{name}: the terms and the schedule disagree on the seasons")
        return errors

    # -- values and acceptance ----------------------------------------------------------------
    def valuation(self, trade):
        """Each side's value before and after, with the posture multipliers of the partner. A player the
        incumbent signs only to trade counts for it at SIGN_AND_TRADE_RIGHTS_SHARE of his value."""
        club = trade["partner"]
        posture = self.assets.posture(club)
        weights = STANCE_WEIGHTS[posture]
        acquired = st_in(trade)
        miami_out = [self.assets.player_value(self.resolve(n, trade), for_club=club) for n in trade.get("miami_out", [])]
        miami_in = []
        for n in trade.get("miami_in", []):
            v = self.assets.player_value(self.resolve(n, trade), for_club=MIAMI)
            if acquired and acquired["player"] == n:
                v = dict(v, partner_share=SIGN_AND_TRADE_RIGHTS_SHARE)
            miami_in.append(v)
        picks_out = [dict(self.assets.pick_value(p, MIAMI, miami_own=True), pick=p) for p in trade.get("picks_out", [])]
        picks_in = [dict(self.assets.pick_value(p, club), pick=p) for p in trade.get("picks_in", [])]

        def partner_view(players, picks, own=False):
            """The partner's objective: its stance weights; its own walk-year veterans are worth less to it."""
            vals = []
            for v in players:
                if not own and self.assets.injured(v["player"], MIAMI):
                    v = dict(v, now=v["now"] * INJURY_DISCOUNT)   # it would take on a hurt player
                walk = WALK_YEAR_DISCOUNT[posture] if (own and v.get("walk_year")) else 1.0
                vals.append(Assets.club_value(v, weights, walk) * v.get("partner_share", 1.0))
            vals += [p["value"] * weights["picks"] for p in picks]
            return Assets.effective(vals)

        def miami_view(players, picks):
            """Miami's objective (MIAMI_WEIGHTS: this season first) with its positional fit."""
            needs = self.fo.needs()
            vals = []
            for v in players:
                if self.assets.injured(v["player"], club):
                    v = dict(v, now=v["now"] * INJURY_DISCOUNT)   # Miami would take on a hurt player
                pos = self.assets.positions.get(v["bbr_id"], (None, "SF", 9))[1].split("-")[0]
                fit = self.fo.fit(pos, needs)
                value = Assets.club_value(v, MIAMI_WEIGHTS)
                # Skill fit (spacing, rim protection, rebounding, defense, playmaking; crowding Wade) from SKILL_FIT_FROM.
                vals.append(value * (0.75 + 0.5 * fit) * self.fo.skill_fit(v["bbr_id"]) if value > 0 else value)
            vals += [p["value"] * MIAMI_WEIGHTS["picks"] for p in picks]
            return Assets.effective(vals)

        # Relative change of the effective values, so a star-for-prospects deal and a swap of reserves sit on one scale.
        def relative(after, before):
            return (after - before) / max(after, before, 1.0)

        partner_gain = relative(partner_view(miami_out, picks_out), partner_view(miami_in, picks_in, own=True))
        miami_gain = relative(miami_view(miami_in, picks_in), miami_view(miami_out, picks_out))
        # A salary dump: a club not contending, or over the tax line, sheds real salary on purpose and gets a
        # first-round pick or a prospect (23 or younger with production) back. The salary it sheds is worth
        # something to it (DUMP_VALUE_PER_5M a season, by its cash weight); nothing else lets it take a loss.
        # A sign-and-trade player's salary was never on his signing club's books, so it is not shed.
        shed = (sum(v["salary"] * v["years"] for v in miami_in if not v.get("partner_share"))
                - sum(v["salary"] * v["years"] for v in miami_out))
        sweetener = any(p["pick"]["round"] == 1 for p in picks_out) or any((v["age"] or 99) <= 23 and v["now"] > 0 for v in miami_out)
        payroll = self.assets.payroll(club) or 0
        dump = bool(shed >= 5000000 and sweetener and (posture != "contending" or payroll > self.assets.tax_line))
        dump_value = DUMP_VALUE_PER_5M * shed / 5000000 * weights["cash"] if dump else 0.0
        objective_gain = partner_gain + dump_value / max(1.0, partner_view(miami_in, picks_in, own=True))
        untouchable = [(n, why) for n in trade.get("miami_in", []) if not (acquired and acquired["player"] == n)
                       for why in [self.assets.untouchable(club, self.resolve(n, trade) or {})] if why]
        return {"partner": club, "posture": posture, "miami_out": miami_out, "miami_in": miami_in, "picks_out": picks_out,
                "picks_in": picks_in, "partner_gain": round(partner_gain, 3), "miami_gain": round(miami_gain, 3),
                "miami_out_view": round(miami_view(miami_out, picks_out), 3), "dump": dump, "shed": shed,
                "objective_gain": round(objective_gain, 3), "untouchable": untouchable}

    def fits_partner(self, trade):
        """The partner has minutes for the arriving positions (at most two incumbents at depth 1-2 there)
        and is not left without a depth-1 or depth-2 player at a position it empties."""
        club = trade["partner"]
        acquired = st_in(trade)
        leaving = {self.resolve(n, trade).get("bbr_id") for n in trade.get("miami_in", [])
                   if self.resolve(n, trade) and not (acquired and acquired["player"] == n)}
        arriving_positions = {self.assets.positions.get(self.resolve(n, trade).get("bbr_id"), (None, "SF", 9))[1].split("-")[0]
                              for n in trade.get("miami_out", []) if self.resolve(n, trade)}
        for bbr in leaving:
            c, position, depth = self.assets.positions.get(bbr, (None, "SF", 9))
            pos = position.split("-")[0]
            if depth <= 2 and pos not in arriving_positions:
                left = sum(1 for b, (cc, pp, d) in self.assets.positions.items() if cc == club and pp.split("-")[0] == pos and d <= 2 and b not in leaving)
                if left == 0:
                    return False
        for name in trade.get("miami_out", []):
            p = self.resolve(name, trade)
            if not p:
                continue
            pos = self.assets.positions.get(p.get("bbr_id"), (None, "SF", 9))[1].split("-")[0]
            incumbents = sum(1 for b, (c, position, depth) in self.assets.positions.items()
                             if c == club and position.split("-")[0] == pos and depth <= 2 and b not in leaving)
            if incumbents >= 3:
                return False
        return True

    def trade_id(self, trade):
        key = json.dumps({k: trade.get(k) for k in ("partner", "miami_out", "miami_in", "picks_out", "picks_in", "cash_out", "cash_in",
                                                     "kind", "sign_and_trade_in", "sign_and_trade_out")}, sort_keys=True)
        return f"{self.on}-{hashlib.sha256(key.encode()).hexdigest()[:10]}"

    def acceptance_packet(self, trade):
        """The partner's answer as a decision packet, or None with the reasons when it cannot be asked."""
        errors = self.errors(trade)
        if errors:
            return None, errors
        if not self.fits_partner(trade):
            return None, [f"{trade['partner']} has no minutes at the arriving positions"]
        v = self.valuation(trade)
        p = acceptance(v)
        if p is None:
            why = (f"{trade['partner']} keeps {', '.join(n for n, _ in v['untouchable'])} "
                   f"({'; '.join(w for _, w in v['untouchable'])}): it needs {UNTOUCHABLE_MARGIN:.0%} more on its own objective"
                   if v["untouchable"] and v["objective_gain"] < UNTOUCHABLE_MARGIN else
                   f"{trade['partner']} ({v['posture']}) loses {v['objective_gain']:+.1%} on its own objective, below its floor {ACCEPT_FLOOR:+.0%}")
            return None, [why]
        outs = ", ".join(trade.get("miami_out", []) + [f"{x['year']} round {x['round']}" for x in trade.get("picks_out", [])]) or "nothing"
        ins = ", ".join(trade.get("miami_in", []) + [f"{x['year']} round {x['round']}" for x in trade.get("picks_in", [])]) or "nothing"
        st = st_in(trade) or st_out(trade)
        contract = ""
        if st:
            total = sum(int(x) for x in st["schedule"].values())
            who = "it signs and trades" if st_in(trade) else "Miami re-signed and trades"
            contract = (f" {st['player']} on the contract {who} ({len(st['schedule'])} seasons, ${total:,}; sign-and-trade)")
        question = f"Does {trade['partner']} accept Miami's proposal: {outs} for {ins}?" + (f" The sign-and-trade covers{contract}." if contract else "")
        basis = (f"{trade['partner']} stance {v['posture']} (2002-03 record and the age of its core); its change on its own objective "
                 f"{v['objective_gain']:+.3f} (weights {STANCE_WEIGHTS[v['posture']]}, star premium {STAR_EXPONENT}, pick chart, contract terms"
                 + (f"; a salary dump shedding ${v['shed']:,} with a pick or prospect back" if v["dump"] else "") +
                 f"). Floor {ACCEPT_FLOOR:+.0%}; above it, 50% at {ACCEPT_HURDLE:+.0%} (steepness {ACCEPT_STEEPNESS}) inside {ACCEPT_BOUNDS}. "
                 f"Miami's own gain {v['miami_gain']:+.3f}.")
        if st_in(trade):
            basis += (f" The incumbent counts the player it signs only to trade at {SIGN_AND_TRADE_RIGHTS_SHARE:.0%} of his value "
                      f"(SIGN_AND_TRADE_RIGHTS_SHARE; it would otherwise lose him for nothing).")
        if st_out(trade):
            basis += " The partner receives Miami's re-signed player at his full value; his consent is a separate draw."
        return {"event_id": f"trade-{self.trade_id(trade)}", "date": self.on, "question": question,
                "decider": f"{trade['partner']} (real club, drawn by rule)", "options": {"accept": p, "decline": round(1 - p, 3)},
                "basis": basis}, v

    # -- Miami's search ----------------------------------------------------------------------
    def _combos(self):
        tradeable = [p for p in self.miami_tradeable()]
        return [[p["player"]] for p in tradeable] + [[a["player"], b["player"]] for i, a in enumerate(tradeable) for b in tradeable[i + 1:]]

    def search(self, requests=(), standing="unsigned_rookie", limit=10, consultations=None):
        """Proposals Miami's front office would make: legal, likely to be accepted, and a gain for Miami.

        `consultations(kind, player)` answers "approve", "object" or None for a star the franchise
        consultation gate covers; an objected star is skipped, an unanswered one is evaluated but kept
        aside in `needing_consultation` rather than returned (runtime/consultations.py). Free agents are
        never candidates here; a sign-and-trade is a negotiation's execution, not a search result."""
        from .consultations import consultation_required
        from .standing import STANDING_WEIGHT
        needs = self.fo.needs()
        need_positions = [pos for pos, n in needs.items() if n["minutes_short"] > 0 or n["quality_gap"] >= 0.3]
        wanted = {r["player"] for r in requests if r.get("subject") == "trade_target"}
        opposed = {r["player"] for r in requests if r.get("subject") == "trade_opposed"}
        combos = self._combos()
        found = []
        self.needing_consultation = []
        for club, entry in self.assets.contracts.items():
            if club == MIAMI:
                continue
            candidates = []
            for p in entry["players"]:
                if p["status"] not in ("under_contract", "under_rookie_contract", "under_contract_unverified") or not p.get("bbr_id"):
                    continue
                pos = self.assets.positions.get(p["bbr_id"], (None, "SF", 9))[1].split("-")[0]
                value = self.assets.player_value(p, for_club=MIAMI)
                helps = self.fo.skill_fit(p["bbr_id"]) >= SEARCH_SKILL_FIT     # a skill Miami lacks, at any position
                if ((pos in need_positions or helps) and value["production"] >= 0.5) or p["player"] in wanted:
                    candidates.append(p)
            for p in candidates[:8]:
                name = p["player"]
                star = consultation_required(standing, self.assets.valuation.value(p["bbr_id"]))
                answer = consultations("trade", name) if (star and consultations) else None
                if star and answer == "object":
                    continue
                for outs in combos:
                    trade = {"partner": club, "miami_out": outs, "miami_in": [name], "picks_out": [], "picks_in": []}
                    packet, v = self.acceptance_packet(trade)
                    if packet is None or packet["options"]["accept"] < SEARCH_MIN_ACCEPT:
                        continue                   # only deals the partner would plausibly take
                    gain = v["miami_gain"]
                    if name in wanted:
                        gain *= 1 + STANDING_WEIGHT[standing]
                    if any(o in opposed for o in outs):
                        gain *= 1 - STANDING_WEIGHT[standing]
                    if gain < SEARCH_MIN_GAIN:
                        continue
                    row = {"trade": trade, "miami_gain": round(gain, 3), "partner_gain": v["objective_gain"],
                           "accept": packet["options"]["accept"], "score": round(gain, 3),
                           "wade_request": name in wanted or any(o in opposed for o in outs)}
                    if star and answer != "approve":
                        self.needing_consultation.append(dict(row, consultation="required", star_value=round(self.assets.valuation.value(p["bbr_id"]), 3)))
                    else:
                        found.append(dict(row, consultation="approved" if star else None))
        found.sort(key=lambda f: -f["score"])
        self.needing_consultation.sort(key=lambda f: -f["score"])
        return found[:limit]

    # -- sign-and-trade ------------------------------------------------------------------------
    def synthetic_from_terms(self, player, bbr_id, club, terms, route, agreement_date=None):
        """The sign-and-trade entry for agreed terms: schedule, guarantee, the player's rights and the
        base-year compensation attached at the signing by the signing club's cap position."""
        p = self.market.players.get(bbr_id, {})
        schedule = {s: int(v) for s, v in zip(seasons_from(SEASON, terms["years"]), terms["schedule"])}
        prior = p.get("prior_salary_2002_03")
        if club == MIAMI:
            # Miami's own flag, from its ledger on the date (the same rule signing.sign applies; the record carries it
            # to the sheet entry when the trade executes, so it is attached once and never re-derived).
            from .signing import base_year_compensation
            prior = next((r.get("previous_salary") for r in self.fo.rights["players"] if r["player"] == player), None) or prior
            byc = base_year_compensation(self.fo.sheet, self.fo.rights, player, route, terms["first_year"], prior, self.cap, self.on)
        else:
            byc = self.base_year_compensation(club, terms["first_year"], prior)
        return {"player": player, "bbr_id": bbr_id, "route": route, "signing_club": club, "terms": terms, "schedule": schedule,
                "amount_kind": {s: "contract_salary" for s in schedule}, "guaranteed": terms.get("guaranteed", sum(schedule.values())),
                "prior_season_salary": {"season": "2002-03", "amount": prior} if prior else None,
                "bird_class": p.get("bird_class"), "non_option_seasons": terms["years"], "base_year_compensation": byc,
                "agreement_date": agreement_date or self.on}

    def _packages(self, with_pick=True):
        """Outgoing packages Miami can offer: singles and pairs of tradeable players, then one owned first."""
        combos = self._combos()
        packages = [(outs, []) for outs in combos]
        if with_pick:
            owned = [{"year": p["year"], "round": p["round"]} for p in self.picks.get("picks", []) if p.get("owned") and p["round"] == 1]
            if owned:
                packages += [(outs, [owned[0]]) for outs in combos] + [([], [owned[0]])]
        return packages

    def sign_and_trade_proposal(self, negotiation_record, *, direction, standing="unsigned_rookie", consultations=None):
        """The front office's sign-and-trade proposal for an agreed or signed negotiation, or (None, reasons).

        Acquisition (`direction="in"`): the incumbent signs the player on the agreed terms and trades him;
        Miami offers the package that costs it the least value (singles, pairs, then one first) among the
        legal ones that fit the partner. Own out (`direction="out"`): Miami signs its agreed free agent and
        trades him in the same transaction to the first partner, contending clubs first, whose smallest legal
        arriving package gains Miami at least SEARCH_MIN_GAIN and whose acceptance clears the floor by
        OWN_OUT_ACCEPT_MARGIN."""
        rec = negotiation_record
        terms = rec["agreement"]["terms"]
        if direction == "in":
            st = self.synthetic_from_terms(rec["player"], rec["bbr_id"], rec["incumbent"], terms, "sign_and_trade", rec["agreement"]["date"])
            reasons, legal = [], []
            for outs, picks in self._packages(with_pick=False) or []:
                trade = {"partner": rec["incumbent"], "miami_out": outs, "miami_in": [rec["player"]], "picks_out": picks, "picks_in": [],
                         "kind": "sign_and_trade", "sign_and_trade_in": st}
                errors = self.errors(trade)
                if errors:
                    reasons.append(f"{', '.join(outs) or 'nothing'}: {errors[0]}")
                    continue
                legal.append(trade)
            if not legal:
                for outs, picks in [pk for pk in self._packages(with_pick=True) if pk[1]]:
                    trade = {"partner": rec["incumbent"], "miami_out": outs, "miami_in": [rec["player"]], "picks_out": picks, "picks_in": [],
                             "kind": "sign_and_trade", "sign_and_trade_in": st}
                    if not self.errors(trade):
                        legal.append(trade)
            legal.sort(key=lambda t: self.valuation(t)["miami_out_view"])
            for trade in legal:
                packet, v = self.acceptance_packet(trade)
                if packet is None:
                    continue
                return {"trade": trade, "packet": packet, "valuation": v,
                        "ranking": {"miami_gain": v["miami_gain"], "partner_gain": v["partner_gain"], "accept": packet["options"]["accept"],
                                    "score": round(v["miami_gain"] * packet["options"]["accept"], 3), "packages_considered": len(legal)}}, []
            return None, reasons or ["no legal sign-and-trade package"]
        if direction != "out":
            raise ValueError("direction must be 'in' or 'out'")
        from .consultations import consultation_required
        st = self.synthetic_from_terms(rec["player"], rec["bbr_id"], MIAMI, terms, rec["agreement"]["route"], rec["agreement"]["date"])
        reasons = []
        clubs = sorted((c for c in self.assets.contracts if c != MIAMI), key=lambda c: (POSTURE_ORDER.index(self.assets.posture(c)), c))
        for club in clubs:
            players = [p for p in self.assets.contracts[club]["players"] if p["status"] in UNDER_CONTRACT and p.get("bbr_id")]
            singles = [[p] for p in players]
            pairs = [[a, b] for i, a in enumerate(players) for b in players[i + 1:]]
            for ins in sorted(singles + pairs, key=lambda pk: (len(pk), sum(self.assets.salary(p) for p in pk))):
                names = [p["player"] for p in ins]
                stars = [(p, consultation_required(standing, self.assets.valuation.value(p["bbr_id"]))) for p in ins]
                answers = {p["player"]: (consultations("trade", p["player"]) if consultations else None) for p, s in stars if s}
                if any(a == "object" for a in answers.values()):
                    continue
                trade = {"partner": club, "miami_out": [rec["player"]], "miami_in": names, "picks_out": [], "picks_in": [],
                         "kind": "sign_and_trade", "sign_and_trade_out": st}
                packet, v = self.acceptance_packet(trade)
                if packet is None:
                    reasons.append(f"{club}: {', '.join(names)}: {v[0]}")
                    continue
                if v["miami_gain"] < SEARCH_MIN_GAIN or packet["options"]["accept"] < ACCEPT_LIMITS[0] + OWN_OUT_ACCEPT_MARGIN:
                    continue
                needs = [n for n, a in answers.items() if a != "approve"]
                return {"trade": trade, "packet": packet, "valuation": v,
                        "consultation": "required" if needs else ("approved" if answers else None), "consultation_players": needs,
                        "ranking": {"miami_gain": v["miami_gain"], "partner_gain": v["partner_gain"], "accept": packet["options"]["accept"],
                                    "score": round(v["miami_gain"] * packet["options"]["accept"], 3)}}, []
        return None, reasons[:10] or ["no partner takes the contract on terms worth Miami's while"]

    def sign_and_trade_feasible(self, target):
        """Plan-time probe for a free-agent target Miami could only reach by sign-and-trade: a synthetic
        contract from his ask (Bird raises, at least three seasons, base-year compensation from the
        incumbent's cap position) against every outgoing package Miami could send. Timing rules are
        ignored (the trade executes on the signing day). Returns (feasible, binding_constraint)."""
        years = max(3, int(target.get("years_asked") or 3))
        first = int(target["ask"])
        terms = {"first_year": first, "years": years, "schedule": [int(round(first * (1 + BIRD_RAISE * i))) for i in range(years)]}
        terms["guaranteed"] = sum(terms["schedule"])
        st = self.synthetic_from_terms(target["player"], target["bbr_id"], target["club"], terms, "sign_and_trade", self.on)
        best = None
        for outs, picks in self._packages(with_pick=True):
            trade = {"partner": target["club"], "miami_out": outs, "miami_in": [target["player"]], "picks_out": picks, "picks_in": [],
                     "kind": "sign_and_trade", "sign_and_trade_in": st}
            errors = self.errors(trade, ignore_timing=True)
            if not errors:
                return True, None
            if best is None or len(errors) < len(best):
                best = errors
        return False, (best[0] if best else "no outgoing package")
