"""The free-agent market on a career date (docs/front_office_design.md, sections 3 and 4).

What exists on a date: the pool of unsigned free agents, each with his rights,
his asking price and the priorities that decide how he answers an offer. Real
history enters only through exits: a free agent whom Miami has not signed joins
his real club on his real date (world data, option D). Miami's front office
never reads a transaction before its date.

Every constant below is a judgement constant, named so it can be revisited.
Chance enters only through decision packets (`runtime/decisions.py`): a player's
trait draw and his answer to each offer are drawn by the engine, never here.
"""
from datetime import date
import json
import math
from pathlib import Path

from .player_stats import alias
from .valuation import Valuation, read

ROOT = Path(__file__).resolve().parents[1]
RIGHTS_PATH = Path("library/2003/league/nba_2003_free_agent_rights.json")
TRANSACTIONS_PATH = Path("library/2003/league/nba_2003_offseason_transactions.json")
CALENDAR_PATH = Path("library/2003/league/nba_2003_04_calendar.json")
CONTRACTS_PATH = Path("library/2003/league/nba_2003_contracts.json")
MIAMI = "Miami Heat"
PRIOR_CAP = 40271000                     # 2002-03 cap: the planning figure before July 15, 2003

# Market pressure (judgement): buyers (clubs that can pay more than the mid-level on the date, after
# their own free-agent holds) raise every ask; supply lowers it below the top tier, where few players exist.
PRESSURE_BASE, PRESSURE_PER_CLUB, PRESSURE_LIMITS = 0.60, 0.07, (0.75, 1.2)
TIER_SUPPLY = ((15.0, 1.0), (10.0, 0.85), (0.0, 0.75))   # (production value at least, supply factor)
ASK_DECAY_PER_WEEK = 0.05                # the ask falls while a player stays unsigned after the first signing day
INSULT_SHARE, INSULT_PAUSE_DAYS = 0.70, 7  # an offer under this share of the ask stops talks for a week
PATIENCE_ROUNDS = 3                      # offers a player hears from one club in one window
NO_EVIDENCE_PREMIUM = 0.35               # a player with no 2002-03 minutes: his agent argues from the prior salary; clubs discount the risk
# Trait draw by age bracket: (max age, {trait: probability}); each trait sets a priority vector.
TRAIT_ODDS = ((25, {"money": 0.30, "fame": 0.20, "loyalty": 0.20, "winning": 0.30}),
              (30, {"money": 0.35, "fame": 0.15, "loyalty": 0.25, "winning": 0.25}),
              (99, {"money": 0.30, "fame": 0.05, "loyalty": 0.25, "winning": 0.40}))
PRIORITIES = {  # weights over log guaranteed money, years, role, club strength, location
    "money":   {"money": 0.55, "years": 0.15, "role": 0.10, "winning": 0.10, "location": 0.10},
    "fame":    {"money": 0.35, "years": 0.10, "role": 0.25, "winning": 0.10, "location": 0.20},
    "loyalty": {"money": 0.35, "years": 0.20, "role": 0.15, "winning": 0.10, "location": 0.20},
    "winning": {"money": 0.30, "years": 0.10, "role": 0.15, "winning": 0.40, "location": 0.05},
}
ACCEPT_SLOPE, ACCEPT_LIMITS = 6.0, (0.02, 0.95)   # logistic slope on the utility gap; chance kept inside the limits
YEARS_WANTED = ((26, 5), (29, 4), (32, 3), (34, 2), (99, 1))   # (max age, seasons a player asks for)


def days_between(a, b):
    return (date.fromisoformat(b) - date.fromisoformat(a)).days


class Market:
    def __init__(self, on, root=ROOT):
        self.on, self.root = on, Path(root)
        self.valuation = Valuation(on, root)
        self.calendar = {e["id"]: e for e in read(CALENDAR_PATH, root)["events"]}
        self.transactions = read(TRANSACTIONS_PATH, root)
        self.players = {}
        for club, entry in read(RIGHTS_PATH, root)["clubs"].items():
            for p in entry["free_agents"]:
                self.players[p["bbr_id"]] = dict(p, club=club)
        self.exits = self._exits()

    # -- world data: exits ---------------------------------------------------------------
    def _exits(self):
        """bbr_id -> (date, destination, row) of the first real move that takes him off the market."""
        out = {}
        for row in sorted(self.transactions["signings"], key=lambda r: r["date"]):
            if row["kind"] not in ("signing", "re_sign", "sign_and_trade", "match", "match_declined"):
                continue
            key = row["bbr_id"] or alias(row["player"])
            if key in out:
                continue
            destination = row["to"]
            if destination == MIAMI:
                # Rule 1: a real Miami signing is skipped; he stays with the club that had him.
                destination = row["from"] or self.players.get(key, {}).get("club")
            out[key] = (row["date"], destination, row)
        return out

    def exit(self, bbr_id):
        return self.exits.get(bbr_id)

    def available(self, bbr_id, on=None):
        """Still unsigned on the date: no real exit on or before it."""
        on = on or self.on
        e = self.exits.get(bbr_id)
        return e is None or e[0] > on

    def pool(self, on=None):
        on = on or self.on
        return {b: p for b, p in self.players.items() if self.available(b, on)}

    def news(self, since, until):
        """Real moves dated after `since` and on or before `until`: what the front office reads as news."""
        return [row for row in self.transactions["signings"] if since < row["date"] <= until
                and not (row["to"] == MIAMI or row["kind"] == "rookie_signing")]

    # -- prices ------------------------------------------------------------------------------
    def cap_known(self, on=None):
        return (on or self.on) >= self.calendar["cap_published"]["date"]

    def planning_cap(self, on=None):
        return 43840000 if self.cap_known(on) else PRIOR_CAP

    def clubs_with_room(self, on=None):
        """Clubs whose June 26 ledger, less their own free-agent holds, leaves more than the mid-level
        under the planning cap (on-date evidence). Miami is counted like any other club."""
        from .contracts import club_ledger
        cap, mid = self.planning_cap(on), self.valuation.mid_level
        holds = {club: entry.get("total_cap_holds") or 0 for club, entry in read(RIGHTS_PATH, self.root)["clubs"].items()}
        out = []
        for club in read(CONTRACTS_PATH, self.root)["clubs"]:
            ledger = club_ledger(club, "2003-04", self.root)
            if cap - ledger["known_total"] - min(holds.get(club, 0), cap) > mid or cap - ledger["known_total"] > 2 * mid + holds.get(club, 0) * 0:
                out.append(club)
        return sorted(set(out))

    def buyers(self, on=None):
        """Clubs with room before holds: a club can renounce its free agents to use the room, so holds
        do not remove it from the market, but they make it a weaker buyer."""
        from .contracts import club_ledger
        cap, mid = self.planning_cap(on), self.valuation.mid_level
        return sorted(club for club in read(CONTRACTS_PATH, self.root)["clubs"]
                      if cap - club_ledger(club, "2003-04", self.root)["known_total"] > mid)

    def pressure(self, on=None, value=None):
        n = len(self.buyers(on))
        buyers = max(PRESSURE_LIMITS[0], min(PRESSURE_LIMITS[1], PRESSURE_BASE + PRESSURE_PER_CLUB * n))
        supply = next(f for floor, f in TIER_SUPPLY if (value or 0) >= floor)
        return buyers * supply

    def decay(self, on=None):
        on = on or self.on
        first = self.calendar["first_signing_day"]["date"]
        weeks = max(0, days_between(first, on)) / 7
        return (1 - ASK_DECAY_PER_WEEK) ** weeks

    def years_wanted(self, bbr_id):
        age = self.valuation.age(bbr_id) or 27
        return next(y for limit, y in YEARS_WANTED if age <= limit)

    def asking(self, bbr_id, on=None, mood=1.0):
        """First-year asking salary and years on the date: comparables price x pressure x decay x mood."""
        on = on or self.on
        p = self.players[bbr_id]
        service, prior = p.get("nba_seasons_before_2003_04"), p.get("prior_salary_2002_03")
        price = self.valuation.price(bbr_id, service, prior)
        evidence = "2002-03 production"
        if price is None:
            # No 2002-03 minutes (Mourning): the agent argues from the prior salary; clubs discount the risk.
            base = (prior or self.valuation.minimum(service)) * NO_EVIDENCE_PREMIUM
            price = int(round(min(self.valuation.maximum(service, prior), max(self.valuation.minimum(service), base))))
            evidence = "prior salary only; no 2002-03 minutes"
        pressure = self.pressure(on, self.valuation.value(bbr_id))
        ask = price * pressure * self.decay(on) * mood
        floor, ceiling = self.valuation.minimum(service), self.valuation.maximum(service, prior)
        return {"first_year": int(round(min(ceiling, max(floor, ask)))), "years": self.years_wanted(bbr_id),
                "comparables_price": price, "pressure": round(pressure, 3), "decay": round(self.decay(on), 3),
                "mood": mood, "minimum": floor, "maximum": ceiling, "evidence": evidence}

    # -- priorities and answers ---------------------------------------------------------------
    def trait_packet(self, bbr_id, window):
        age = self.valuation.age(bbr_id) or 27
        odds = next(o for limit, o in TRAIT_ODDS if age <= limit)
        p = self.players[bbr_id]
        return {"event_id": f"{window}-{bbr_id}-priorities", "date": self.on,
                "question": f"What does {p['player']} weigh most in choosing his next contract?",
                "decider": f"{p['player']} (simulated player)", "options": dict(odds),
                "basis": f"Trait odds by age ({age}): money, fame, loyalty, winning (docs/front_office_design.md 4.3). Drawn once per market window."}

    @staticmethod
    def priorities(trait):
        return dict(PRIORITIES[trait])

    @staticmethod
    def utility(terms, context, priorities):
        """Priority-weighted score of a contract at a club.

        terms: guaranteed (total guaranteed salary), years; context: role_minutes (expected per game),
        strength (projected wins, 0-82), location (0-1 preference), ask (first-year asking salary).
        """
        money = math.log(max(terms["guaranteed"], 1) / max(context["ask"], 1))        # 0 at the ask
        years = (terms["years"] - 1) / 6
        role = min(1.0, context.get("role_minutes", 20) / 32)
        winning = min(1.0, max(0.0, (context.get("strength", 41) - 20) / 40))
        return (priorities["money"] * money + priorities["years"] * years + priorities["role"] * role
                + priorities["winning"] * winning + priorities["location"] * context.get("location", 0.5))

    @staticmethod
    def acceptance_probability(u_offer, u_alternative):
        p = 1 / (1 + math.exp(-ACCEPT_SLOPE * (u_offer - u_alternative)))
        return round(min(ACCEPT_LIMITS[1], max(ACCEPT_LIMITS[0], p)), 3)

    def alternative(self, bbr_id, on=None):
        """The player's best alternative: his real contract where the world has it, else the tier price."""
        e = self.exits.get(bbr_id)
        ask = self.asking(bbr_id, on)
        if e and e[2].get("total") and e[2].get("years"):
            return {"guaranteed": e[2]["total"], "years": e[2]["years"], "club": e[1], "basis": "real contract (world data)"}
        years = ask["years"]
        total = int(round(sum(ask["comparables_price"] * (1 + 0.1 * i) for i in range(years))))
        return {"guaranteed": total, "years": years, "club": e[1] if e else None, "basis": "tier price (no reported terms)"}

    def answer_packet(self, bbr_id, offer, context, alternative, alt_context, priorities, window, round_no):
        """Decision packet for a player's answer to an offer: accept, counter or reject."""
        p = self.players[bbr_id]
        u_offer = self.utility(offer, context, priorities)
        u_alt = self.utility(alternative, alt_context, priorities)
        accept = self.acceptance_probability(u_offer, u_alt)
        if offer["first_year"] < INSULT_SHARE * context["ask"]:
            accept = ACCEPT_LIMITS[0]
        remaining = max(0.0, 1 - accept)
        counter = round(remaining * (0.7 if round_no < PATIENCE_ROUNDS else 0.0), 3)
        reject = round(1 - accept - counter, 3)
        options = {k: v for k, v in (("accept", accept), ("counter", counter), ("reject", reject)) if v > 0}
        if len(options) == 1:
            options = {"accept": min(0.95, accept), "reject": round(1 - min(0.95, accept), 3)}
        return {"event_id": f"{window}-{bbr_id}-offer-{round_no}", "date": self.on,
                "question": f"Does {p['player']} accept Miami's offer ({offer['years']} years, ${offer['guaranteed']:,} guaranteed)?",
                "decider": f"{p['player']} (simulated player)", "options": options,
                "basis": (f"Utility of Miami's offer {u_offer:.3f} against his alternative {u_alt:.3f} "
                          f"({alternative['basis']}: {alternative['years']} years, ${alternative['guaranteed']:,} at {alternative.get('club')}); "
                          f"priorities {priorities}; logistic slope {ACCEPT_SLOPE}, kept inside {ACCEPT_LIMITS}; round {round_no} of {PATIENCE_ROUNDS}.")}
