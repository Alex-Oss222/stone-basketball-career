"""The 2004 offseason market for all thirty clubs, fully simulated (the user's decision, October 2026).

Real 2004 signings, options and qualifying offers are never consulted: a player's 2004-05 club comes from this market.
Existing 2004-05 contracts (`runtime/contract_terms.py`), the expansion draft and the draft are the starting book.
Evidence is the simulated 2003-04 season (closed results) and the honors announced on or before the date.

Calendar (`library/2004/league/nba_2004_offseason_calendar.json`): options and qualifying offers on June 30; the
market opens July 1; agreements made during the moratorium are signed July 14, when the $43,870,000 cap (Charlotte
$29,250,000) becomes known; before then clubs plan on the 2003-04 cap. Rounds run weekly to September 29; on
September 30 a club still short of thirteen signs the best unsigned players at the minimum, each with the club that
needs him most while it has fewer than thirteen; the rest stay in the unsigned pool, which the in-season market
draws on (career continuity). Players without a real 2004-05 role leave the league as history has them.

Club decisions are judgement rules with no chance element; a player's answers are engine draws:
- Value: NBA efficiency per game in the simulated 2003-04 season, shrunk toward replacement by minutes, times the age
  factor (`runtime/valuation.py`). Price: the salary at the same rank among existing 2004-05 contracts (veterans
  with 500 or more simulated minutes) as his value, times the honor factor, inside the minimum and maximum.
- June 30: a club exercises a team option when the market price is at least TEAM_OPTION_SHARE of the option salary.
  A player or early-termination option is the player's draw: P(opt out) rises with his price over the option salary.
  A club tenders a qualifying offer (the larger of 125% of the prior salary and the minimum plus $175,000) when his
  price is at least the offer and 1.5 times his minimum; the player is then restricted. An offer sheet is matched
  when the holder values him at the offer (price x need) and can pay it.
- First-round picks sign on July 1 at 120% of the 2004 rookie scale (era practice). Second-round and undrafted
  prospects enter the pool at the minimum; their drafting club holds their rights like a restricted player.
- Each round a club ranks the unsigned players it can pay (Bird rights for its own free agents, cap room, the
  mid-level exception once, the minimum) by value x positional need and offers the best one a contract at the
  smaller of his ask and its own price, for the years he wants; it adds minimum offers while it is short of
  ROSTER_TARGET. A club stops paying above the minimum at the payroll ceiling (the tax line; contenders may go
  CONTENDER_TAX_ROOM over it with Bird rights).
- A player with offers answers in one engine draw: accept one club (softmax over money, role and winning, with a
  loyalty weight to his own club) or wait; his willingness to accept rises as the ask meets the offer and as the
  summer passes. An offer sheet to a restricted player is matched when his club values him at the offer and can pay.
- Miami is one of the thirty clubs, run by the same AI/GM rules. Once Wade's standing is `franchise`, Miami asks him
  before offering to a star (`runtime/consultations.py`); the market waits for his answer.
The record is `10_Free_Agency/free_agency_2004.json`, rebuilt by replaying every round from its recorded draws.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
import json
import math
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]
SEASON, NEW = "2003-04", "2004-05"
FOLDER = Path(f"career/Dwyane_Wade/{SEASON}/10_Free_Agency")
RECORD = FOLDER / "free_agency_2004.json"
DRAWS = FOLDER / "Free_Agency_Draws"
CALENDAR = Path("library/2004/league/nba_2004_offseason_calendar.json")
CAREERS = Path("library/careers/nba_player_careers.json")
SERVICE = Path("library/2004/league/nba_2004_service_years.json")
MIAMI, CHARLOTTE = "Miami Heat", "Charlotte Bobcats"
OPTIONS_DATE, OPEN, SIGN_FROM, LAST_ROUND, PLACEMENT = "2004-06-30", "2004-07-01", "2004-07-14", "2004-09-29", "2004-09-30"
PRIOR_CAP = 43_840_000                  # 2003-04 cap: the planning figure until the 2004-05 cap is announced
CAP_KNOWN = "2004-07-13"

# Judgement constants, named so they can be revisited.
TEAM_OPTION_SHARE = 0.85
QO_SHARE = 1.0
QO_MIN_PRICE = 1.5                      # and only a player priced at 1.5x his minimum or more
COMPARABLE_MINUTES = 500
QO_MINIMUM_PLUS = 175_000
OPT_OUT_SLOPE, OPT_OUT_LIMITS = 5.0, (0.03, 0.97)
ROOKIE_SCALE_SHARE = 1.20
ROSTER_TARGET, ROSTER_MAX = 13, 15
CONTENDER_TAX_ROOM = 0.10
STAR_PRICE_MLES, STAR_TAX_ROOM = 2.0, 0.35  # a club pays well into the tax to keep a player priced at two mid-levels
ASK_DECAY_PER_WEEK = 0.05
ASK_FLOOR_SHARE = 0.55                  # the ask never falls below this share of the price
INSULT_SHARE = 0.70                     # a club does not offer below this share of the ask
ACCEPT_SLOPE = 8.0                      # logistic slope on (offer / ask - 1)
ACCEPT_BASE, ACCEPT_WEEKLY = 0.35, 0.06 # P(accept an offer at the ask) in round 1 and its weekly rise
TEMPERATURE = 0.15
WEIGHTS = {"money": 0.60, "role": 0.20, "winning": 0.20}
WINNING_FROM_AGE = 30                   # at 30 and older winning weighs WEIGHTS_VETERAN
WEIGHTS_VETERAN = {"money": 0.50, "role": 0.15, "winning": 0.35}
LOYALTY = 0.05                          # added utility for the club that holds his rights
HOLD_SHARE = 1.5                        # cap hold: 150% of the prior salary
NEED_FLOOR = 0.6                        # a club with no positional need still values talent at this share
YEARS_WANTED = ((26, 5), (29, 4), (32, 3), (34, 2), (99, 1))
GROUP = {"PG": "G", "SG": "G", "G": "G", "SF": "F", "PF": "F", "F": "F", "C": "C", "G-F": "G", "F-C": "F", "F-G": "F", "C-F": "C"}
TARGET_MINUTES = {"G": 96, "F": 96, "C": 48}


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def rounds():
    out, d = [], date.fromisoformat(OPEN)
    while d.isoformat() <= LAST_ROUND:
        out.append(d.isoformat())
        d += timedelta(days=7)
    return out


def calendar(root=ROOT):
    c = _read(Path(root) / CALENDAR)
    return {"cap": c["salary_cap_2004_05"]["value"], "tax": c["luxury_tax_threshold_2004_05"]["value"],
            "mle": c["mid_level_exception_2004_05"]["value"], "charlotte_cap": c["charlotte_cap_and_floor_2004_05"]["value"]["cap"],
            "minimum": {int(k.rstrip("+")): v for k, v in c["minimum_salary_scale_2004_05"]["value"].items()},
            "scale": {r["pick"]: r for r in c["rookie_scale_2004_first_round"]["value"]}}


def minimum(service, cal):
    return cal["minimum"][min(10, max(0, service or 0))]


def maximum(service, cap):
    """1999 agreement: 25%, 30% or 35% of the cap by years of service (the 105% of prior salary rule is applied by the caller)."""
    share = 0.25 if (service or 0) <= 6 else 0.30 if service <= 9 else 0.35
    return int(round(cap * share))


# ---------------------------------------------------------------- evidence

def season_evidence(root=ROOT):
    """{bbr_id: {"games", "minutes", "eff", "mpg"}} over the closed 2003-04 regular season."""
    from .season_awards import identities
    from .write_back import closed_results
    root = Path(root)
    ids = identities(root)
    out = defaultdict(lambda: defaultdict(float))
    for row in closed_results(root, SEASON, "2004-04-14"):
        r = row["result"]
        for side in ("home", "away"):
            for p in r["player_stats"][side]:
                if not p.get("minutes", 0) > 0:
                    continue
                bbr = ids.get(p["player_id"], (None, None, None))[1] or ("dwyane_wade" if p["player_id"] == "Dwyane Wade" else None)
                if not bbr:
                    continue
                t = out[bbr]
                t["games"] += 1
                t["minutes"] += p["minutes"]
                t["eff"] += (p["pts"] + p["orb"] + p["drb"] + p["ast"] + p["stl"] + p["blk"]
                             - (p["fga"] - p["fgm"]) - (p["fta"] - p["ftm"]) - p["tov"])
    return {b: {"games": int(t["games"]), "minutes": round(t["minutes"], 1), "eff": t["eff"], "mpg": t["minutes"] / t["games"]}
            for b, t in out.items()}


def identity(root=ROOT):
    """{bbr_id: {"name", "birth_date", "position", "service"}} from the registry, rosters and careers."""
    from .rotations import load_rosters
    root = Path(root)
    out = {}
    registry = _read(root / "career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json")
    for p in registry["players"] if isinstance(registry, dict) else registry:
        if p.get("bbr_id"):
            out[p["bbr_id"]] = {"name": p["name"], "birth_date": p.get("birth_date"), "position": p.get("position")}
    for season in (SEASON, NEW):
        for club in load_rosters(season, root).values():
            for p in club["players"]:
                if p.get("bbr_id"):
                    e = out.setdefault(p["bbr_id"], {"name": p["player_id"], "birth_date": p.get("birth_date"), "position": p.get("position")})
                    e["birth_date"] = e.get("birth_date") or p.get("birth_date")
                    e["position"] = e.get("position") or p.get("position")
    careers = _read(root / CAREERS)["players"]
    sourced = {}
    for fa in (fa for c in _read(root / "library/2003/league/nba_2003_free_agent_rights.json")["clubs"].values() for fa in c["free_agents"]):
        if fa.get("bbr_id") and fa.get("nba_seasons_before_2003_04") is not None:
            sourced[fa["bbr_id"]] = fa["nba_seasons_before_2003_04"] + 1
    for fa in (fa for c in _read(root / "library/2004/league/nba_2004_free_agent_rights.json")["clubs"].values() for fa in c["free_agents"]):
        if fa.get("bbr_id") and fa.get("nba_seasons_before_2004_05") is not None:
            sourced[fa["bbr_id"]] = fa["nba_seasons_before_2004_05"]
    debut = _read(root / SERVICE)["players"]
    for b, e in out.items():
        if b in sourced:
            e["service"] = sourced[b]
        elif b in debut:
            e["service"] = debut[b]["seasons_through_2003_04"]
        else:
            e["service"] = sum(1 for s in (careers.get(b) or {}).get("seasons", {}) if s < NEW)
    return out


def age(birth, on=OPEN):
    if not birth:
        return None
    b, d = date.fromisoformat(birth), date.fromisoformat(on)
    return d.year - b.year - ((d.month, d.day) < (b.month, b.day))


class Pricing:
    """Value and price on the 2004 market: simulated 2003-04 production, existing contracts as comparables."""

    def __init__(self, root=ROOT, evidence=None, ident=None, terms=None):
        from .valuation import Valuation, age_factor, PRIOR_MINUTES, REPLACEMENT_EFF_PER_GAME
        self.root = Path(root)
        self.evidence = season_evidence(root) if evidence is None else evidence
        self.ident = identity(root) if ident is None else ident
        self._age_factor, self._prior, self._repl = age_factor, PRIOR_MINUTES, REPLACEMENT_EFF_PER_GAME
        self.honors = Valuation(OPEN, root)
        terms = terms if terms is not None else __import__("runtime.contract_terms", fromlist=["x"]).existing_terms(root)
        values, salaries = [], []
        for b, t in terms.items():
            e = self.evidence.get(b)
            if (t["kind"] == "contract" and e and e["minutes"] >= COMPARABLE_MINUTES and t["salary"] > 1_100_000
                    and "rookie" not in t["source"]):
                values.append(self.value(b))
                salaries.append(t["salary"])
        self.values, self.salaries = sorted(values), sorted(salaries)
        self.fit = {"method": "quantile match of value to salary over existing 2004-05 contracts", "n": len(values)}

    def comparables_price(self, v):
        """The salary at the same rank among the comparables as this value (linear between ranks)."""
        import bisect
        n = len(self.values)
        i = bisect.bisect_left(self.values, v)
        if i <= 0:
            return self.salaries[0] * max(0.0, v / self.values[0]) if self.values[0] > 0 else self.salaries[0]
        if i >= n:
            return self.salaries[-1] * v / self.values[-1]
        lo, hi = self.values[i - 1], self.values[i]
        f = (v - lo) / (hi - lo) if hi > lo else 0.0
        q = (i - 1 + f) / (n - 1)
        x = q * (n - 1)
        j = min(n - 2, int(x))
        return self.salaries[j] + (self.salaries[j + 1] - self.salaries[j]) * (x - j)

    def age(self, b):
        return age((self.ident.get(b) or {}).get("birth_date"))

    def value(self, b):
        e = self.evidence.get(b)
        a = self._age_factor(self.age(b))
        if not e or e["games"] <= 0:
            return self._repl * a
        w = e["minutes"] / (e["minutes"] + self._prior)
        return (w * e["eff"] / e["games"] + (1 - w) * self._repl) * a

    def price(self, b, cal, prior=None):
        service = (self.ident.get(b) or {}).get("service", 0)
        top = max(maximum(service, cal["cap"]), int(round((prior or 0) * 1.05)))
        raw = self.comparables_price(self.value(b)) * self.honors.honor_factor(b)
        if b not in self.evidence:
            raw = minimum(service, cal)
        return int(round(min(top, max(minimum(service, cal), raw))))


def years_wanted(a):
    return next(y for limit, y in YEARS_WANTED if (a or 27) <= limit)


# ---------------------------------------------------------------- draws

def _draw(root, packet):
    path = Path(root) / DRAWS / f"{packet['event_id']}.decision.json"
    result = path.with_name(path.name.replace(".decision.json", ".decision.result.json"))
    if result.is_file():
        return _read(result)["outcome"]
    if not path.is_file():
        total = sum(packet["options"].values())
        probs = {k: round(v / total, 6) for k, v in packet["options"].items()}
        top = max(probs, key=probs.get)
        probs[top] = round(probs[top] + 1 - sum(probs.values()), 6)
        _write(path, dict(packet, options=probs))
    return None


def _slug(name):
    import re
    return re.sub(r"[^a-z0-9]+", "-", name.lower().replace("'", "")).strip("-")


# ---------------------------------------------------------------- the book

def starting_book(root=ROOT):
    """Clubs' 2004-05 contracts before June 30, and the market's rights: {"contracts": {bbr: {...}}, "rights": {bbr: club}}."""
    from .contract_terms import existing_terms
    from .draft import drafted_clubs
    from .expansion import charlotte_players
    from .offseason import simulated_clubs, miami_players
    root = Path(root)
    sim = simulated_clubs(root)
    held = miami_players(root)
    for b in held:
        sim[b] = MIAMI
    contracts, options = {}, {}
    for b, t in existing_terms(root).items():
        club = sim.get(b) or t["club"]                    # a player who missed 2003-04 stays with his contract's club
        if not club or club == MIAMI or b in held:
            continue
        row = {"club": club, "salary": t["salary"], "years": max(1, len(t["schedule"])), "source": t["source"]}
        (options if t["kind"] == "option" else contracts)[b] = dict(row, option_kind=t["option_kind"])
    for b, t in miami_contracts(root).items():
        contracts[b] = t
    for b, club in charlotte_players(root).items():
        if b in contracts:
            contracts[b]["club"] = CHARLOTTE
            contracts[b]["source"] += "; expansion draft"
    rights = {b: c for b, c in sim.items() if b not in contracts and b not in options}
    drafted = {b: c for b, c in drafted_clubs(root).items()}
    return {"contracts": contracts, "options": options, "rights": rights, "drafted": drafted}


def miami_contracts(root=ROOT):
    """Miami's 2004-05 contracts from its own ledger (AI/GM records)."""
    sheet = _read(Path(root) / f"career/Dwyane_Wade/{SEASON}/00_Team/Finances/contract_schedules.json")
    roster = {p["name"]: p.get("bbr_id") for p in _read(Path(root) / f"career/Dwyane_Wade/{SEASON}/00_Team/Team/Roster/roster.json")["players"]}
    out = {}
    for p in sheet["players"]:
        s = p.get("schedule") or {}
        if s.get(NEW) and p.get("status") in ("under_contract", "under_rookie_contract", "re_signed"):
            b = roster.get(p["player"]) or ("dwyane_wade" if p["player"] == "Dwyane Wade" else None)
            if b:
                out[b] = {"club": MIAMI, "salary": int(s[NEW]), "years": sum(1 for k, v in s.items() if k >= NEW and v),
                          "source": "Miami contract_schedules.json", "option_kind": None}
    return out


def miami_prior_salaries(root=ROOT):
    sheet = _read(Path(root) / f"career/Dwyane_Wade/{SEASON}/00_Team/Finances/contract_schedules.json")
    roster = {p["name"]: p.get("bbr_id") for p in _read(Path(root) / f"career/Dwyane_Wade/{SEASON}/00_Team/Team/Roster/roster.json")["players"]}
    return {roster[p["player"]]: (p.get("schedule") or {}).get(SEASON) for p in sheet["players"] if roster.get(p["player"])}


def prior_salaries(root=ROOT):
    """{bbr_id: 2003-04 salary} from the 2003 inventory, the 2003-04 salary list where held, and Miami's ledger."""
    out = {}
    for club, e in _read(Path(root) / "library/2003/league/nba_2003_contracts.json")["clubs"].items():
        for p in e["players"]:
            if p.get("bbr_id") and (p.get("schedule") or {}).get(SEASON):
                out[p["bbr_id"]] = p["schedule"][SEASON]
    rights = _read(Path(root) / "library/2004/league/nba_2004_free_agent_rights.json")
    for c in rights["clubs"].values():
        for fa in c["free_agents"]:
            if fa.get("bbr_id") and fa.get("prior_salary_2003_04"):
                out.setdefault(fa["bbr_id"], fa["prior_salary_2003_04"])
    out.update({b: s for b, s in miami_prior_salaries(root).items() if s})
    return out


def real_roles(root=ROOT):
    """Players with a real 2004-05 role: minutes in the real careers table, which (unlike the club rosters) keeps real
    Miami's players (career continuity; the club itself is never read)."""
    from .offseason import real_clubs
    careers = _read(Path(root) / CAREERS)["players"]
    out = set(real_clubs(NEW, root))
    out |= {b for b, e in careers.items() if (e.get("seasons", {}).get(NEW) or {}).get("minutes", 0) > 0}
    return out


def rfa_eligible(b, ident, rookie_scale):
    """1999 agreement: three or fewer years of service, or a first-round pick finishing his rookie-scale contract."""
    service = (ident.get(b) or {}).get("service", 0)
    return service <= 3 or (b in rookie_scale and service <= 4)


def rookie_scale_players(root=ROOT):
    out = set()
    for e in _read(Path(root) / "library/2003/league/nba_2003_contracts.json")["clubs"].values():
        for p in e["players"]:
            if p.get("bbr_id") and p.get("status") == "under_rookie_contract":
                out.add(p["bbr_id"])
    return out


def qualifying_amount(prior, service, cal):
    return int(max(round((prior or 0) * 1.25), minimum(service, cal) + QO_MINIMUM_PLUS))


def _sigmoid(x):
    return 1 / (1 + math.exp(-x))


class Market:
    """The whole summer, replayed from its recorded draws. `run()` returns the record, or None while a draw or
    Wade's answer is pending."""

    def __init__(self, root=ROOT, clock=None):
        from .write_back import clock as career_clock
        self.root = Path(root)
        self.clock = clock or career_clock(self.root)
        self.cal = calendar(root)
        self.ident = identity(root)
        self.book = starting_book(root)
        self.pricing = Pricing(root, ident=self.ident)
        self.prior = prior_salaries(root)
        self.roles = real_roles(root)
        self.rookie_scale = rookie_scale_players(root)
        self.clubs = sorted({c["club"] for c in self.book["contracts"].values()} | set(self.book["rights"].values()) | {CHARLOTTE})
        self.events, self.pending = [], False
        self.standings = self._standings()

    # ---- helpers
    def _standings(self):
        from .standings import standings_on
        table = standings_on("2004-04-14", self.root, SEASON)
        rows = table if isinstance(table, list) else [r for conf in table.values() for r in (conf if isinstance(conf, list) else [])]
        out = {}
        for r in rows:
            if isinstance(r, dict) and r.get("club"):
                g = (r.get("wins", 0) + r.get("losses", 0)) or 1
                out[r["club"]] = r.get("wins", 0) / g
        return out

    def name(self, b):
        return (self.ident.get(b) or {}).get("name", b)

    def group(self, b):
        pos = (self.ident.get(b) or {}).get("position") or "F"
        return GROUP.get(pos, GROUP.get(pos.split("-")[0], "F"))

    def service(self, b):
        return (self.ident.get(b) or {}).get("service", 0)

    def mpg(self, b):
        e = self.pricing.evidence.get(b)
        return e["mpg"] if e else 10.0

    def cap(self, club, on):
        if club == CHARLOTTE:
            return self.cal["charlotte_cap"]
        return self.cal["cap"] if on >= CAP_KNOWN else PRIOR_CAP

    def ceiling(self, club, bird=False, b=None):
        """Payroll a club will reach: the tax line; with Bird rights a contender goes CONTENDER_TAX_ROOM over it, and
        any club keeps a player priced at STAR_PRICE_MLES mid-levels or more up to STAR_TAX_ROOM over it."""
        tax = self.cal["tax"]
        if bird and b is not None and self.price.get(b, 0) >= STAR_PRICE_MLES * self.cal["mle"]:
            return tax * (1 + STAR_TAX_ROOM)
        contender = self.standings.get(club, 0.5) >= 50 / 82
        return tax * (1 + CONTENDER_TAX_ROOM) if (bird and contender) else tax

    def need(self, club, g):
        mins = sorted((self.mpg(b) for b, c in self.contracts.items() if c["club"] == club and self.group(b) == g), reverse=True)
        covered = sum(mins[:3 if g != "C" else 2])
        return max(0.0, min(1.0, (TARGET_MINUTES[g] - covered) / TARGET_MINUTES[g]))

    def roster(self, club):
        return sum(1 for c in self.contracts.values() if c["club"] == club)

    def payroll(self, club):
        return sum(c["salary"] for c in self.contracts.values() if c["club"] == club)

    def holds(self, club, on):
        """Cap holds the club keeps: its own unsigned free agents it values above twice the minimum."""
        total = 0
        for b in self.pool:
            if b in self.contracts or self.rights.get(b) != club:
                continue
            if self.price[b] >= 2 * minimum(self.service(b), self.cal):
                total += int(round((self.prior.get(b) or self.price[b]) * HOLD_SHARE))
        return total

    def ask(self, b, week):
        decay = max(ASK_FLOOR_SHARE, 1 - ASK_DECAY_PER_WEEK * max(0, week - 2))      # falls after the moratorium
        return max(minimum(self.service(b), self.cal), int(round(self.price[b] * decay)))

    def draw(self, packet):
        out = _draw(self.root, packet)
        if out is None:
            self.pending = True
        return out

    # ---- June 30
    def june_30(self):
        for b, o in sorted(self.book["options"].items()):
            price = self.price_of(b)
            if o["option_kind"] == "team_option":
                keep = price >= TEAM_OPTION_SHARE * o["salary"]
                self.events.append({"date": OPTIONS_DATE, "kind": "team_option", "player": self.name(b), "bbr_id": b, "club": o["club"],
                                    "decision": "exercised" if keep else "declined", "salary": o["salary"], "price": price})
            else:
                gap = (price - o["salary"]) / o["salary"]
                p_out = min(OPT_OUT_LIMITS[1], max(OPT_OUT_LIMITS[0], _sigmoid(OPT_OUT_SLOPE * gap)))
                answer = self.draw({"event_id": f"2004-06-30-{_slug(self.name(b))}-{o['option_kind'].replace('_', '-')}", "date": OPTIONS_DATE,
                                    "question": f"Does {self.name(b)} exercise his 2004-05 {o['option_kind'].replace('_', ' ')} with {o['club']} (${o['salary']:,})?",
                                    "decider": f"{self.name(b)} (simulated player, engine draw)",
                                    "options": {"exercise": round(1 - p_out, 6), "opt_out": round(p_out, 6)},
                                    "basis": f"Market price ${price:,} from simulated 2003-04 production against the option salary; "
                                             f"P(opt out) = logistic({OPT_OUT_SLOPE} x {gap:+.3f}) (runtime/free_agency_2004.py)."})
                if answer is None:
                    continue
                keep = answer == "exercise"
                self.events.append({"date": OPTIONS_DATE, "kind": o["option_kind"], "player": self.name(b), "bbr_id": b, "club": o["club"],
                                    "decision": "exercised" if keep else "opted_out", "salary": o["salary"], "price": price})
            if keep:
                self.contracts[b] = {"club": o["club"], "salary": o["salary"], "years": 1, "source": o["source"] + "; option exercised 2004-06-30",
                                     "date": OPTIONS_DATE, "route": "option"}
            else:
                self.rights[b] = o["club"]

    def price_of(self, b):
        return self.pricing.price(b, self.cal, self.prior.get(b))

    # ---- the market
    def run(self):
        if self.clock < OPTIONS_DATE:
            return None
        self.contracts = {b: dict(c, route="existing") for b, c in self.book["contracts"].items()}
        self.rights = dict(self.book["rights"])
        self.june_30()
        if self.pending:
            return None
        drafted = self.book["drafted"]
        for b, club in drafted.items():
            self.rights[b] = club
        self.sign_first_round(drafted)
        self.pool = sorted(b for b in set(self.roles) | set(self.rights)
                           if b not in self.contracts and b in self.roles and b != "dwyane_wade")
        self.price = {b: self.price_of(b) for b in self.pool}
        self.qualifying = {}
        for b in self.pool:
            club = self.rights.get(b)
            if club and rfa_eligible(b, self.ident, self.rookie_scale) and b not in drafted:
                qo = qualifying_amount(self.prior.get(b), self.service(b), self.cal)
                if self.price[b] >= QO_SHARE * qo and self.price[b] >= QO_MIN_PRICE * minimum(self.service(b), self.cal):
                    self.qualifying[b] = {"club": club, "amount": qo}
                    self.events.append({"date": OPTIONS_DATE, "kind": "qualifying_offer", "player": self.name(b), "bbr_id": b,
                                        "club": club, "amount": qo, "price": self.price[b]})
        for b in self.pool:
            if b in drafted and b not in self.contracts:
                self.qualifying[b] = {"club": drafted[b], "amount": minimum(0, self.cal), "draft_rights": True}
        self.mle_used = set()
        for week, day in enumerate(rounds()):
            if day > self.clock:
                return None
            if not self.round(week, day):
                return None
        if self.clock < PLACEMENT:
            return None
        self.place()
        return self.record()

    def sign_first_round(self, drafted):
        from .draft import _read as dread, RECORD as DREC
        path = self.root / DREC
        if not path.is_file():
            return
        for p in dread(path)["picks"]:
            if p["round"] != 1 or not p.get("bbr_id"):
                continue
            scale = self.cal["scale"].get(p["pick"]) or self.cal["scale"][max(self.cal["scale"])]
            salary = int(round(scale["year1"] * ROOKIE_SCALE_SHARE))
            self.contracts[p["bbr_id"]] = {"club": p["club"], "salary": salary, "years": 3, "date": OPEN, "route": "rookie_scale",
                                           "source": f"2004 rookie scale No. {p['pick']} at {int(ROOKIE_SCALE_SHARE * 100)}%"}
            self.events.append({"date": OPEN, "kind": "rookie_scale_signing", "player": p["player"], "bbr_id": p["bbr_id"],
                                "club": p["club"], "salary": salary, "years": 3, "team_option": "2007-08"})

    def means(self, club, b, on, amount):
        """The route by which the club can pay `amount` to player b on the date, or None."""
        payroll = self.payroll(club)
        if amount <= minimum(self.service(b), self.cal) and self.roster(club) < ROSTER_MAX:
            return "minimum"
        if self.rights.get(b) == club:
            return "bird" if payroll + amount <= self.ceiling(club, bird=True, b=b) else None
        room = self.cap(club, on) - payroll - self.holds(club, on)
        if amount <= room:
            return "cap_room"
        if club not in self.mle_used and amount <= self.cal["mle"] and payroll + amount <= self.ceiling(club):
            return "mid_level"
        return None

    def offers_for(self, club, week, day, open_players):
        out, short = [], ROSTER_TARGET - self.roster(club)
        if self.roster(club) >= ROSTER_MAX:
            return out
        ranked = sorted(open_players, key=lambda b: (-self.pricing.value(b) * (NEED_FLOOR + (1 - NEED_FLOOR) * self.need(club, self.group(b))), b))
        made_big = False
        for b in ranked:
            ask = self.ask(b, week)
            need = self.need(club, self.group(b))
            willing = int(round(self.price[b] * (0.9 + 0.2 * need)))
            amount = max(minimum(self.service(b), self.cal), min(ask, willing))
            if amount < INSULT_SHARE * ask:
                continue
            minimum_deal = amount <= minimum(self.service(b), self.cal)
            if not minimum_deal and made_big:
                continue
            if minimum_deal and short <= 0:
                continue
            route = self.means(club, b, day, amount)
            if route is None:
                continue
            if not minimum_deal and not self.consulted(club, b, day, amount):
                if self.pending:
                    return out
                continue
            out.append({"club": club, "bbr_id": b, "salary": amount, "years": 1 if minimum_deal else years_wanted(self.pricing.age(b)),
                        "route": route, "ask": ask})
            if minimum_deal:
                short -= 1
            else:
                made_big = True
            if made_big and short <= 0:
                break
        return out

    def consulted(self, club, b, day, amount):
        """Miami asks Wade before adding a star once his standing is franchise (runtime/consultations.py)."""
        if club != MIAMI or self.rights.get(b) == MIAMI:
            return True
        from . import consultations as C
        from .standing import standing_on
        value = self.pricing.value(b)
        standing = standing_on(self.root, day)
        if not C.consultation_required(standing.get("standing"), value):
            return True
        name = self.name(b)
        if C.objected(self.root, SEASON, name, day):
            return False
        if C.approved(self.root, SEASON, "free_agent", name, day):
            return True
        state_path = self.root / f"career/Dwyane_Wade/{SEASON}/current_state.json"
        state = _read(state_path)
        C.ask(self.root, state, day, "free_agent", name, b, club, basis=f"Miami's market plan on {day}: offer ${amount:,} (runtime/free_agency_2004.py)",
              evidence={"value": round(value, 2), "line": self.line(b), "salary": f"${amount:,} offer", "cap_position": f"payroll ${self.payroll(MIAMI):,}",
                        "fit": f"{self.group(b)} need {self.need(MIAMI, self.group(b)):.2f}", "reason": "2004 free agency"},
              season=SEASON, standing=standing)
        _write(state_path, state)
        self.pending = True
        return False

    def line(self, b):
        e = self.pricing.evidence.get(b)
        if not e:
            return "no simulated 2003-04 line"
        return f"{e['games']} games, {e['mpg']:.1f} minutes, efficiency {e['eff'] / e['games']:.1f} a game (simulated 2003-04)"

    def utility(self, b, offer):
        a = self.pricing.age(b) or 27
        w = WEIGHTS_VETERAN if a >= WINNING_FROM_AGE else WEIGHTS
        money = math.log(max(1, offer["salary"] * offer["years"]) / max(1, self.ask(b, 0) * years_wanted(a)))
        better = sum(1 for x, c in self.contracts.items()
                     if c["club"] == offer["club"] and self.group(x) == self.group(b) and self.pricing.value(x) > self.pricing.value(b))
        role = 1 - min(1.0, better / 3)
        win = self.standings.get(offer["club"], 0.3 if offer["club"] == CHARLOTTE else 0.5)
        return w["money"] * money + w["role"] * role + w["winning"] * win + (LOYALTY if self.rights.get(b) == offer["club"] else 0)

    def round(self, week, day):
        open_players = [b for b in self.pool if b not in self.contracts]
        offers = defaultdict(list)
        for club in self.clubs:
            for o in self.offers_for(club, week, day, open_players):
                offers[o["bbr_id"]].append(o)
            if self.pending:
                return False
        accepted = []
        for b in sorted(offers):
            options = offers[b]
            best = max(o["salary"] * o["years"] for o in options)
            ratio = best / max(1, self.ask(b, week) * max(o["years"] for o in options))
            base = min(0.95, ACCEPT_BASE + ACCEPT_WEEKLY * week)
            p_accept = _sigmoid(ACCEPT_SLOPE * (ratio - 1) + math.log(base / (1 - base)))
            p_accept = min(0.97, max(0.03, p_accept))
            us = {o["club"]: self.utility(b, o) for o in options}
            m = max(us.values())
            ex = {c: math.exp((u - m) / TEMPERATURE) for c, u in us.items()}
            z = sum(ex.values())
            probs = {c: p_accept * v / z for c, v in ex.items()}
            probs["wait"] = 1 - p_accept
            answer = self.draw({"event_id": f"2004-fa-{day}-{_slug(self.name(b))}", "date": day,
                                "question": f"2004 free agency, {day}: which offer does {self.name(b)} accept ("
                                            + ", ".join(f"{o['club']} ${o['salary']:,} x {o['years']}" for o in options) + "), or does he wait?",
                                "decider": f"{self.name(b)} (simulated player, engine draw)", "options": probs,
                                "basis": f"Ask ${self.ask(b, week):,}; best offer {ratio:.2f} of the ask in total; accept chance {p_accept:.3f}; "
                                         "club shares by money, role and winning (runtime/free_agency_2004.py)."})
            if answer is None or answer == "wait":
                continue
            accepted.append(next(o for o in options if o["club"] == answer))
        if self.pending:
            return False
        for o in accepted:
            self.sign(o, day)
        return True

    def sign(self, o, day):
        b, club = o["bbr_id"], o["club"]
        when = max(day, SIGN_FROM) if o["route"] != "minimum" or day >= SIGN_FROM else SIGN_FROM
        q = self.qualifying.get(b)
        matched = False
        if q and q["club"] != club:
            holder = q["club"]
            willing = q.get("draft_rights") or o["salary"] <= self.price[b] * (0.9 + 0.2 * self.need(holder, self.group(b)))
            route = self.means(holder, b, day, o["salary"])
            self.events.append({"date": when, "kind": "offer_sheet", "player": self.name(b), "bbr_id": b, "club": club,
                                "from": holder, "salary": o["salary"], "years": o["years"]})
            if willing and route:
                self.events.append({"date": when, "kind": "offer_sheet_matched", "player": self.name(b), "bbr_id": b, "club": holder,
                                    "from": club, "salary": o["salary"], "years": o["years"], "route": route})
                o = dict(o, club=holder, route=route)
                club, matched = holder, True
            else:
                self.events.append({"date": when, "kind": "offer_sheet_not_matched", "player": self.name(b), "bbr_id": b, "club": holder,
                                    "to": club})
        if o["route"] == "mid_level":
            self.mle_used.add(club)
        self.contracts[b] = {"club": club, "salary": o["salary"], "years": o["years"], "date": when, "route": o["route"],
                             "source": "2004 simulated free agency"}
        if matched:
            return
        kind = "re_sign" if self.rights.get(b) == club else "signing"
        self.events.append({"date": when, "kind": kind, "player": self.name(b), "bbr_id": b, "club": club, "from": self.rights.get(b),
                            "salary": o["salary"], "years": o["years"], "route": o["route"], "agreed": day})

    def place(self):
        """A restricted player still unsigned accepts his qualifying offer. Then clubs short of ROSTER_TARGET sign the best remaining players at the minimum; the rest stay unsigned in the
        pool for the in-season market (runtime/league_market.py)."""
        for b, q in sorted(self.qualifying.items()):
            if b in self.contracts or q.get("draft_rights"):
                continue
            self.contracts[b] = {"club": q["club"], "salary": q["amount"], "years": 1, "date": PLACEMENT, "route": "qualifying_offer",
                                 "source": "2004 qualifying offer accepted"}
            self.events.append({"date": PLACEMENT, "kind": "qualifying_offer_accepted", "player": self.name(b), "bbr_id": b,
                                "club": q["club"], "salary": q["amount"], "years": 1})
        left = sorted((b for b in self.pool if b not in self.contracts), key=lambda b: (-self.pricing.value(b), b))
        for b in left:
            short = [c for c in self.clubs if self.roster(c) < ROSTER_TARGET]
            if not short:
                break
            club = min(short, key=lambda c: (-self.need(c, self.group(b)), self.roster(c), c))
            salary = minimum(self.service(b), self.cal)
            self.contracts[b] = {"club": club, "salary": salary, "years": 1, "date": PLACEMENT, "route": "minimum",
                                 "source": "2004 camp signing (roster minimum)"}
            self.events.append({"date": PLACEMENT, "kind": "camp_signing", "player": self.name(b), "bbr_id": b, "club": club,
                                "from": self.rights.get(b), "salary": salary, "years": 1})
        self.unsigned = [b for b in left if b not in self.contracts]

    def record(self):
        clubs = defaultdict(list)
        for b, c in sorted(self.contracts.items()):
            clubs[c["club"]].append({"player": self.name(b), "bbr_id": b, "salary": c["salary"], "years": c["years"],
                                     "route": c.get("route"), "source": c["source"]})
        departed = sorted(b for b in set(self.rights) | set(self.book["options"]) if b not in self.contracts)
        return {"schema_version": 1, "kind": "free_agency", "season": NEW, "from": OPTIONS_DATE, "to": PLACEMENT,
                "rule": __doc__.split("\n\n", 1)[1].strip(), "pricing_fit": self.pricing.fit,
                "events": sorted(self.events, key=lambda e: (e["date"], e["kind"], e["player"])),
                "clubs": {c: sorted(v, key=lambda r: -r["salary"]) for c, v in sorted(clubs.items())},
                "payroll": {c: sum(r["salary"] for r in v) for c, v in sorted(clubs.items())},
                "unsigned_pool": [{"player": self.name(b), "bbr_id": b, "price": self.price[b], "rights": self.rights.get(b)}
                                  for b in self.unsigned],
                "left_the_league": [{"player": self.name(b), "bbr_id": b, "basis": "no real 2004-05 role"} for b in departed if b not in self.roles]}


def run(root=ROOT, clock=None):
    """Replay the summer to the clock. Writes the record when the market is complete; returns it, else None."""
    from .write_back import clock as career_clock
    root = Path(root)
    if (root / RECORD).is_file() or (clock or career_clock(root)) < OPTIONS_DATE:
        return None
    market = Market(root, clock)
    record = market.run()
    if record:
        _write(root / RECORD, record)
    return record


def signed_clubs(root=ROOT):
    """{bbr_id: club} for every 2004-05 contract once the market is complete, else {}."""
    path = Path(root) / RECORD
    if not path.is_file():
        return {}
    return {r["bbr_id"]: club for club, rows in _read(path)["clubs"].items() for r in rows}
