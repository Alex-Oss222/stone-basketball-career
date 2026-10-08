"""The 2004 offseason market for all thirty clubs, fully simulated (the user's decision, October 2026).

Real 2004 signings, options and qualifying offers are never consulted: a player's 2004-05 club comes from this market.
Existing 2004-05 contracts (`runtime/contract_terms.py`), the expansion draft and the draft are the starting book.
Evidence is the simulated 2003-04 season (closed results) and the honors announced on or before the date.

Calendar (`library/2004/league/nba_2004_offseason_calendar.json`): options and qualifying offers on June 30; the
market opens July 1; agreements made during the moratorium are signed July 14, when the $43,870,000 cap (Charlotte
$29,250,000) becomes known; before then clubs plan on the 2003-04 cap. Rounds run weekly to September 29; on
September 30 a club still short of thirteen signs the best unsigned players (at what it can still pay, from the
minimum up to its room or mid-level), each with the club that needs him most while it has fewer than thirteen; the rest stay in the unsigned pool, which the in-season market
draws on (career continuity). Players without a real 2004-05 role leave the league as history has them.

Club decisions are judgement rules with no chance element; a player's answers are engine draws:
- Value: NBA efficiency per game in the simulated 2003-04 season, shrunk toward replacement by minutes, times the age
  factor (`runtime/valuation.py`). Price: the salary at the same rank among existing 2004-05 contracts (veterans
  with 500 or more simulated minutes) as his value, times the honor factor, inside the minimum and maximum; a player
  with fewer than 250 simulated minutes is priced at his minimum.
- June 30: a club exercises a team option when the market price is at least TEAM_OPTION_SHARE of the option salary.
  A player or early-termination option is the player's draw: P(opt out) rises with his price over the option salary.
  A club tenders a qualifying offer (the larger of 125% of the prior salary and the minimum plus $175,000) when his
  price is at least the offer and 1.5 times his minimum; the player is then restricted. When Wade has asked Miami to
  keep a player the rule would let go, the tender is an engine draw at his standing weight x (1 - the rule's margin). An offer sheet is matched
  when the holder values him at the offer (price x need) and can pay it.
- First-round picks sign on July 1 at 120% of the 2004 rookie scale (era practice). Second-round and undrafted
  prospects enter the pool at the minimum; their drafting club holds their rights like a restricted player.
- Each round a club ranks the unsigned players it can pay (Bird rights for its own free agents, cap room, the
  mid-level exception once, the minimum) by value x positional need and offers the best one a contract at the
  smaller of his ask and its own price, for the years he wants; it adds minimum offers while it is short of
  ROSTER_TARGET. A club stops paying above the minimum at the payroll ceiling (the tax line; contenders may go
  CONTENDER_TAX_ROOM over it with Bird rights).
- Every free agent's priority is drawn once on July 1 (money, fame, loyalty or winning, with the 2003 odds by age;
  `runtime/market.py`). A player with offers answers in one engine draw: accept one club or wait. Each club's share
  comes from the 2003 factor model (`runtime/player_utility.py`): money and security against his ask and the years
  he wants, net income by state tax, his role (minutes by rank in his position group), contention (projected wins),
  loyalty to the club holding his rights and market size, weighted by his career stage and tilted by his drawn
  priority; a prime starter offered a bench role walks from that club. His willingness to accept at all rises as
  the ask meets the best offer and as the summer passes.
- From July 14 the clubs trade, one search a round: one or two contracted players for one, both clubs gaining on
  their own objective (stance from the simulated record: contenders value the present, rebuilders youth and cash;
  positional fit; salary against worth; a status-quo premium on players they hold), legal under the 1999 salary
  rule, each deal an engine draw on both clubs' acceptance (`runtime/trades.acceptance`). Players signed this summer
  are not tradable; a first-round pick is after 30 days. Miami's trades for a star wait for Wade's consultation. An offer sheet to a restricted player is matched when his club values him at the offer and can pay.
- Miami is one of the thirty clubs, run by the same AI/GM rules. Wade's free-agent requests (`10_Free_Agency/
  wade_requests.json`) move a requested player up Miami's list by his standing weight and let Miami pay up to 110% of
  its own valuation, and a requested minimum player may take a roster spot up to the fifteenth; the front office still
  decides and the player still answers. Once Wade's standing is `franchise`, Miami asks him before offering to a star
  (`runtime/consultations.py`); the market waits for his answer.
- From the 2006 summer (RENOUNCE_FOR_REQUEST_FROM): when Miami's offer to a free agent Wade asked it to pursue cannot
  be paid because of its cap holds, but would be without some of them, Miami plans to renounce its own unsigned free
  agents valued below him, lowest value first, only as many as the offer needs (never one Wade asked it to keep, and it
  offers none of them a contract that round). The plan is carried out only when he accepts that offer, before any
  signing that day; if he waits or goes elsewhere Miami keeps every hold. Each renouncement is a dated `renounce` event
  and ends Miami's Bird rights (and any qualifying offer) for that player. From the same summer
  (REQUEST_ANSWERS_CONSULTATION_FROM) Wade's own pursue request answers the franchise consultation for that player:
  the record is written answered `approve` from the request on the asking day and the market does not stop.
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
MIN_EVIDENCE_MINUTES = 250              # below this many simulated 2003-04 minutes a player is priced at his minimum
QO_MINIMUM_PLUS = 175_000
OPT_OUT_SLOPE, OPT_OUT_LIMITS = 5.0, (0.03, 0.97)
ROOKIE_SCALE_SHARE = 1.20
ROSTER_TARGET, ROSTER_MAX = 13, 15
CONTENDER_TAX_ROOM = 0.10
STAR_PRICE_MLES, STAR_TAX_ROOM = 2.0, 0.35  # a club pays well into the tax to keep a player priced at two mid-levels
ASK_DECAY_PER_WEEK = 0.05
ASK_FLOOR_SHARE = 0.55                  # the ask never falls below this share of the price before September
LATE_WEEK, LATE_DECAY = 9, 0.15         # from the tenth round (September) the floor falls this much a week toward the minimum
INSULT_SHARE = 0.70                     # a club does not offer below this share of the ask
ACCEPT_SLOPE = 8.0                      # logistic slope on (offer / ask - 1)
ACCEPT_BASE, ACCEPT_WEEKLY = 0.35, 0.06 # P(accept an offer at the ask) in round 1 and its weekly rise
CHOICE_TEMPERATURE = 4.0               # utility points (0-100 scale, runtime/player_utility.py) per e-fold in a club's share
ROLE_LADDER = {"G": (34, 30, 22, 14, 8), "F": (34, 30, 22, 14, 8), "C": (32, 20, 12, 6)}   # minutes by rank in his group
CHARLOTTE_WINS = 20                     # an expansion club's projected wins (judgement)
# Summer trades (from the first signing day): one search a round on the market's own values.
TRADE_FROM = SIGN_FROM
TRADE_CANDIDATES = 8                    # a club's most valuable tradable contracts
MAX_TRADES_PER_ROUND = 2                # proposals a round; about half pass the two clubs' draws
STAR_EXPONENT = 1.6                     # trade worth grows faster than production above replacement (a star is scarce)
PACKAGE_WEIGHTS = (1.0, 0.45)           # a second player in a package counts at this share (roster spots, consolidation)
SALARY_POINTS_PER_MILLION = 0.35        # trade worth points one million dollars of salary costs, times the stance's cash weight
TRADE_MATCH, TRADE_PLUS = 1.15, 100_000 # 1999 agreement: incoming salary at most 115% of outgoing plus $100,000 over the cap
MIN_MUTUAL_GAIN = 0.10
STATUS_QUO = 1.15
ROOKIE_TRADE_DAYS = 30                  # a first-round pick can be traded 30 days after he signs
NEW_SIGNING_TRADABLE = "2004-12-15"     # a free agent signed this summer cannot be traded before December 15
REQUEST_PRICE_CEILING = 1.10           # Miami pays a player Wade asked for up to this share of its own valuation (docs/front_office.md)
RENOUNCE_FOR_REQUEST_FROM = 2006        # from this summer Miami renounces lesser holds to reach a free agent Wade asked it to pursue
REQUEST_ANSWERS_CONSULTATION_FROM = 2006  # from this summer Wade's own pursue request answers the franchise consultation for that player
REQUESTS = FOLDER / "wade_requests.json"
UNTOUCHABLE = {"dwyane_wade"}           # Miami's AI/GM keeps its franchise cornerstone off the market (judgement)
HOLD_SHARE = 1.5                        # cap hold: 150% of the prior salary
NEED_FLOOR = 0.6                        # a club with no positional need still values talent at this share
YEARS_WANTED = ((26, 5), (29, 4), (32, 3), (34, 2), (99, 1))
GROUP = {"PG": "G", "SG": "G", "G": "G", "SF": "F", "PF": "F", "F": "F", "C": "C", "G-F": "G", "F-C": "F", "F-G": "F", "C-F": "C"}
TARGET_MINUTES = {"G": 96, "F": 96, "C": 48}


YEAR, SEASON_END = 2004, "2004-04-14"


class year_context:
    """Run the market for a later summer (R5, October 2026): the closed season, the new one, its calendar, folder and
    dates. Contracts come from the league ledger (options already decided by `runtime/options.py` on June 29), rights
    from each club's roster at the season's end, prior salaries and rookie-scale flags from the ledger. 2004 keeps its
    constants and replays unchanged."""

    NAMES = ("YEAR", "SEASON", "NEW", "FOLDER", "RECORD", "DRAWS", "CALENDAR", "SERVICE", "OPTIONS_DATE", "OPEN", "SIGN_FROM",
             "LAST_ROUND", "PLACEMENT", "PRIOR_CAP", "CAP_KNOWN", "NEW_SIGNING_TRADABLE", "TRADE_FROM", "REQUESTS", "SEASON_END")

    def __init__(self, year, root=ROOT):
        self.year, self.root = int(year), Path(root)

    def __enter__(self):
        g = globals()
        self.saved = {k: g[k] for k in self.NAMES}
        _IN_CONTEXT.append(self.year)
        if self.year == 2004:
            return self
        from .seasons import dates, path as season_path
        y = self.year
        season, new = f"{y - 1}-{str(y)[-2:]}", f"{y}-{str(y + 1)[-2:]}"
        folder = Path(f"career/Dwyane_Wade/{season}/10_Free_Agency")
        cal = _read(self.root / f"library/{y}/league/nba_{y}_offseason_calendar.json")
        get = lambda *keys: next(v for v in (_date_of(cal, k) for k in keys) if v)
        sign_from = get("first_signing_and_trade_date", "first_signing_day", "moratorium_end_signing", "signing_opens")
        g.update(YEAR=y, SEASON=season, NEW=new, FOLDER=folder, RECORD=folder / f"free_agency_{y}.json",
                 DRAWS=folder / "Free_Agency_Draws", CALENDAR=Path(f"library/{y}/league/nba_{y}_offseason_calendar.json"),
                 SERVICE=Path(f"library/{y}/league/nba_{y}_service_years.json"), OPTIONS_DATE=f"{y}-06-30", OPEN=f"{y}-07-01",
                 SIGN_FROM=sign_from, LAST_ROUND=f"{y}-09-29", PLACEMENT=f"{y}-09-30",
                 PRIOR_CAP=_read(self.root / season_path(season, "cap_rules"))["salary_cap"],
                 CAP_KNOWN=(date.fromisoformat(sign_from) - timedelta(days=1)).isoformat(),
                 NEW_SIGNING_TRADABLE=f"{y}-12-15", TRADE_FROM=sign_from, REQUESTS=folder / "wade_requests.json",
                 SEASON_END=dates(season, self.root)["regular_season_end"])
        return self

    def __exit__(self, *exc):
        globals().update(self.saved)
        _IN_CONTEXT.pop()
        return False


def _date_of(cal, key):
    v = cal.get(key)
    if isinstance(v, dict):
        v = v.get("value") or v.get("date")
    return v[:10] if isinstance(v, str) and len(v) >= 10 and v[4] == "-" else None


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


def signing_week():
    """The first round on or after the moratorium's end (2004: July 15, round 2; 2005: August 5, round 5)."""
    return next(i for i, d in enumerate(rounds()) if d >= SIGN_FROM)


def calendar(root=ROOT):
    c = _read(Path(root) / CALENDAR)
    sfx = NEW.replace("-", "_")
    charlotte = c.get(f"charlotte_cap_and_floor_{sfx}")
    return {"cap": c[f"salary_cap_{sfx}"]["value"], "tax": c[f"luxury_tax_threshold_{sfx}"]["value"],
            "mle": c[f"mid_level_exception_{sfx}"]["value"],
            "charlotte_cap": charlotte["value"]["cap"] if charlotte else c[f"salary_cap_{sfx}"]["value"],
            "minimum": {int(k.rstrip("+")): v for k, v in c[f"minimum_salary_scale_{sfx}"]["value"].items()},
            "scale": {r["pick"]: r for r in c[f"rookie_scale_{YEAR}_first_round"]["value"]}}


def minimum(service, cal):
    return cal["minimum"][min(10, max(0, service or 0))]


def maximum(service, cap):
    """The maximum by years of service under the agreement in force for the market's new season (`runtime/agreement.py`:
    1999's 25/30/35% of the cap through 2004; the 2005 agreement's fixed 2005-06 figures after). The 105% of prior salary
    rule is applied by the caller."""
    from .agreement import maximum as agreement_maximum
    return agreement_maximum(service, cap, NEW)


# ---------------------------------------------------------------- evidence

def season_evidence(root=ROOT):
    """{bbr_id: {"games", "minutes", "eff", "mpg"}} over the closed 2003-04 regular season."""
    from .season_awards import identities
    from .write_back import closed_results
    root = Path(root)
    ids = identities(root)
    out = defaultdict(lambda: defaultdict(float))
    for row in closed_results(root, SEASON, SEASON_END):
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
                t["starts"] += bool(p.get("started"))
                t["minutes"] += p["minutes"]
                t["eff"] += (p["pts"] + p["orb"] + p["drb"] + p["ast"] + p["stl"] + p["blk"]
                             - (p["fga"] - p["fgm"]) - (p["fta"] - p["ftm"]) - p["tov"])
    return {b: {"games": int(t["games"]), "starts": int(t["starts"]), "minutes": round(t["minutes"], 1), "eff": t["eff"],
                "mpg": t["minutes"] / t["games"]}
            for b, t in out.items()}


_IN_CONTEXT = []                           # year_context depth: inside a market year, identity() uses that year


def identity(root=ROOT, year=None, on=None):
    """{bbr_id: {"name", "birth_date", "position", "service"}} from the registry, rosters and careers.

    The year's identity (service through the season before its summer): `year`, else the market year in force (inside
    `year_context`), else the summer that opened the career's live season (the season-change audit: outside a context
    this used the 2004 rules in every later season, one season of service short and without the new draftees).
    With `on`, the registry is read as it stood that day: a row added later (`added_on`, a debut written by the season's
    games) was unknown then, so a replay of a closed summer reads the inputs the summer itself read."""
    root = Path(root)
    if year is None and not _IN_CONTEXT:
        from .seasons import active
        year = max(2004, market_year(active(root)))     # 2003-04 had no simulated summer market: 2004 is the first
    if year is not None and int(year) != YEAR:
        with year_context(int(year), root):
            return identity(root, on=on)
    from .rotations import load_rosters
    out = {}
    registry = _read(root / "career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json")
    for p in registry["players"] if isinstance(registry, dict) else registry:
        if on is not None and (p.get("added_on") or "") > on:
            continue
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
    if YEAR != 2004:                       # a later summer: the year's service file, else the real seasons played before
        debut = _read(root / SERVICE)["players"] if (root / SERVICE).is_file() else {}
        for b, e in out.items():
            row = debut.get(b) or {}
            e["service"] = next((v for k, v in row.items() if k.startswith("seasons") and isinstance(v, int)), None)
            if e["service"] is None:
                e["service"] = sum(1 for s in (careers.get(b) or {}).get("seasons", {}) if s < NEW)
        return out
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


def age(birth, on=None):
    if not birth:
        return None
    b, d = date.fromisoformat(birth), date.fromisoformat(on or OPEN)       # the market year's July 1 in force
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
        if terms is None:                  # the summer's existing contracts: 2004's inventory, later the closed season's ledger
            if YEAR == 2004:
                from .contract_terms import existing_terms
                terms = existing_terms(root)
            else:
                from .league_contracts import carried
                terms = carried(NEW, root)
        values, salaries = [], []
        for b, t in terms.items():
            e = self.evidence.get(b)
            if (t["kind"] == "contract" and e and e["minutes"] >= COMPARABLE_MINUTES
                    and "rookie" not in t["source"] and not t.get("rookie_scale")):
                values.append(self.value(b))
                salaries.append(t["salary"])
        self.values, self.salaries = sorted(values), sorted(salaries)
        self.fit = {"method": f"quantile match of value to salary over existing {NEW} contracts", "n": len(values)}

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
        if (self.evidence.get(b) or {}).get("minutes", 0) < MIN_EVIDENCE_MINUTES:
            raw = minimum(service, cal)                 # too little simulated evidence to price above the minimum
        return int(round(min(top, max(minimum(service, cal), raw))))


# The minimum player exception signs a contract of at most two seasons (1999 FAQ Q19; cbafaq05 Q19, recorded in
# library/2005/league/nba_2005_cba_rules.json exceptions.minimum.max_years).
MINIMUM_EXCEPTION_YEARS = 2


def years_wanted(a):
    """Years a player of age `a` asks for, within the agreement's longest non-Bird contract (5 from the 2005 agreement)."""
    from .agreement import max_years
    return min(next(y for limit, y in YEARS_WANTED if (a or 27) <= limit), max_years("other", NEW))


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
    if YEAR != 2004:
        return _ledger_book(root)
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


def _ledger_book(root=ROOT):
    """A later summer's starting book from the closed season's contract ledger (options decided on June 29 by
    `runtime/options.py`) and each club's roster on the season's last day: a contract running into the new season stays
    with the club holding him; a player whose contract ended is a free agent whose rights his club holds; Miami's
    contracts are its own cap sheet's; the year's draft picks go to the clubs that drafted them."""
    from .draft import drafted_clubs, year_context as draft_year
    from .league_contracts import read as read_ledger
    from .league_moves import effective_roster
    from .rotations import miami_holds
    from .seasons import clubs as season_clubs
    root = Path(root)
    ledger = read_ledger(SEASON, root) or {}
    holder = {}
    for club in season_clubs(SEASON, root):
        if club == MIAMI:
            continue
        for p in effective_roster(club, SEASON_END, SEASON, root):
            holder[p["bbr_id"]] = club
    for b in miami_holds(SEASON, SEASON_END, root):
        holder[b] = MIAMI
    contracts, rights = {}, {}
    for b, club in holder.items():
        c = ledger.get(b)
        if club == MIAMI:
            continue
        if c and c["schedule"].get(NEW):
            years = sum(1 for k, v in c["schedule"].items() if k >= NEW and v)
            contracts[b] = {"club": club, "salary": int(c["schedule"][NEW]), "years": years, "option_kind": None,
                            "source": f"league contract ledger {SEASON} ({c.get('kind')})"}
        else:
            rights[b] = club
    for b, t in miami_contracts(root).items():
        contracts[b] = t
    sheet = _read(root / f"career/Dwyane_Wade/{SEASON}/00_Team/Finances/contract_schedules.json")
    ids = {p["name"]: p.get("bbr_id") for p in _read(root / f"career/Dwyane_Wade/{SEASON}/00_Team/Team/Roster/roster.json")["players"]}
    for p in sheet["players"]:
        b = p.get("bbr_id") or ids.get(p["player"])
        if b and b not in contracts and (p.get("schedule") or {}).get(SEASON) and p.get("status") in ("under_contract", "under_rookie_contract"):
            rights[b] = MIAMI                                   # Miami's own expiring contracts: its rights
    with draft_year(YEAR, root):
        drafted = dict(drafted_clubs(root))
    return {"contracts": contracts, "options": {}, "rights": rights, "drafted": drafted}


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
    if YEAR != 2004:                       # a later summer: the closed season's ledger salaries, then Miami's sheet
        from .league_contracts import read as read_ledger
        out = {b: int(c["schedule"][SEASON]) for b, c in (read_ledger(SEASON, root) or {}).items() if c["schedule"].get(SEASON)}
        out.update({b: s for b, s in miami_prior_salaries(root).items() if s})
        return out
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
    from .availability import status
    from .offseason import real_clubs
    from .rotations import rosters_path
    careers = _read(Path(root) / CAREERS)["players"]
    out = set(real_clubs(NEW, root)) if (Path(root) / rosters_path(NEW)).is_file() else set()
    # Past the careers table's last season, a player whose career ran to it stays available (runtime/availability.py).
    out |= {b for b in careers if status(b, NEW, root) == "available"}
    return out


def rfa_eligible(b, ident, rookie_scale):
    """1999 agreement: three or fewer years of service, or a first-round pick finishing his rookie-scale contract."""
    service = (ident.get(b) or {}).get("service", 0)
    return service <= 3 or (b in rookie_scale and service <= 4)


def rookie_scale_players(root=ROOT):
    if YEAR != 2004:
        from .league_contracts import read as read_ledger
        return {b for b, c in (read_ledger(SEASON, root) or {}).items() if c.get("rookie_scale") or c.get("kind") == "rookie_scale"}
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


def _request_answer_page(record, evidence):
    """The milestone page of a franchise consultation answered by Wade's own request (`Market.answered_by_request`):
    the consultation page's identity line, proposed move and evidence (`runtime/consultations.page`), with the answer,
    its date and the request's words in place of the open question."""
    from .consultations import RULE, STAR_PRODUCTION_VALUE
    kind_text = {"free_agent": "sign as a free agent", "trade": "acquire by trade", "sign_and_trade": "acquire by sign-and-trade"}[record["kind"]]
    asked = record["answered_by_request"]
    rows = [("Proposed move", f"Miami wants to {kind_text} **{record['player']}** ({record['club']})"),
            ("Simulated line", evidence.get("line") or "no line recorded"),
            ("Production value", f"{evidence.get('value')} (star line {STAR_PRODUCTION_VALUE}; {RULE})"),
            ("Salary or ask", evidence.get("salary", "Not recorded")),
            ("Miami's cap position", evidence.get("cap_position", "Not recorded")),
            ("Fit", evidence.get("fit", "Not recorded")),
            ("Front office's reason", evidence.get("reason", "Not recorded")),
            ("Trade record", record["trade_id"] or "none")]
    table = "\n".join(f"| {k} | {v} |" for k, v in rows)
    return f"""---
type: milestone
kind: franchise_consultation
status: closed
date: {record['date']}
record: {record['id']}.json
---

# Consultation: {record['player']} ({record['date']})

**Dwyane Wade** · Miami Heat · standing **{record['standing']['standing']}** (as of {record['standing']['as_of'] or 'default'}) · career date {record['date']}

**State: Answered by your request.** You asked Miami to pursue {record['player']} on {asked['date']}, so the front office did not stop to ask: your request is recorded as your approval of this move.

## The proposed move

| Item | Value |
| --- | --- |
{table}

## Your answer

- **Answer**: approve, recorded {record['answered']}
- **Source**: your request of {asked['date']} (`{asked['source']}`, subject `{asked['subject']}`)
- **Your words**: "{asked['words']}"

The approval covers this kind of move for {record['player']} this season. An objection still needs a new dated consultation record; closed records are never edited.

## Next checkpoint

The summer market goes on the same day: Miami makes the move it planned, and the other side still answers by its own engine draw.
"""


class Market:
    """The whole summer, replayed from its recorded draws. `run()` returns the record, or None while a draw or
    Wade's answer is pending."""

    def __init__(self, root=ROOT, clock=None):
        from .write_back import clock as career_clock
        self.root = Path(root)
        self.clock = clock or career_clock(self.root)
        self.cal = calendar(root)
        self.ident = identity(root, on=self.clock)          # the registry as the summer knew it on its own day
        self.book = starting_book(root)
        self.pricing = Pricing(root, ident=self.ident)
        self.prior = prior_salaries(root)
        self.roles = real_roles(root)
        self.rookie_scale = rookie_scale_players(root)
        self.clubs = sorted({c["club"] for c in self.book["contracts"].values()} | set(self.book["rights"].values()) | {CHARLOTTE})
        self.events, self.pending = [], False
        self.renounced = {}                             # {bbr_id: club} rights a club renounced this summer (from 2006)
        self.store = True                               # stored trade proposals (False only in tests)
        self.standings = self._standings()

    # ---- helpers
    def _standings(self):
        from .standings import standings_on
        table = standings_on(SEASON_END, self.root, SEASON)
        if YEAR != 2004:                   # {club: {"wins", "losses", "pct"}}; the 2004 summer replays its recorded empty table
            return {club: r["wins"] / ((r["wins"] + r["losses"]) or 1) for club, r in table.items()}
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
        any club keeps a player priced at STAR_PRICE_MLES mid-levels or more up to STAR_TAX_ROOM over it (a club already
        that far over goes half that share over its June 30 payroll)."""
        tax = self.cal["tax"]
        if bird and b is not None and self.price.get(b, 0) >= STAR_PRICE_MLES * self.cal["mle"]:
            return max(tax * (1 + STAR_TAX_ROOM), self.june_payroll.get(club, 0) * (1 + STAR_TAX_ROOM / 2))
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

    def held(self, club):
        """The club's own unsigned free agents that carry a cap hold: those it prices at twice the minimum or more."""
        return [b for b in self.pool if b not in self.contracts and self.rights.get(b) == club
                and self.price[b] >= 2 * minimum(self.service(b), self.cal)]

    def hold(self, b):
        """One player's cap hold: HOLD_SHARE x his prior salary (his price when none is recorded)."""
        return int(round((self.prior.get(b) or self.price[b]) * HOLD_SHARE))

    def holds(self, club, on):
        """Cap holds the club keeps: its own unsigned free agents it values above twice the minimum."""
        return sum(self.hold(b) for b in self.held(club))

    def ask(self, b, week):
        floor = ASK_FLOOR_SHARE - LATE_DECAY * max(0, week - LATE_WEEK + 1)
        decay = max(floor, 1 - ASK_DECAY_PER_WEEK * max(0, week - signing_week()))     # falls after the moratorium
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
                answer = self.draw({"event_id": f"{YEAR}-06-30-{_slug(self.name(b))}-{o['option_kind'].replace('_', '-')}", "date": OPTIONS_DATE,
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
                bar = max(QO_SHARE * qo, QO_MIN_PRICE * minimum(self.service(b), self.cal))
                tender = self.price[b] >= bar
                kept = self.requested(OPTIONS_DATE, ("re_sign",)) if club == MIAMI else {}
                if not tender and b in kept:
                    tender = self.request_draw(b, bar, kept[b])
                    if tender is None:
                        continue
                if tender:
                    self.qualifying[b] = {"club": club, "amount": qo}
                    self.events.append({"date": OPTIONS_DATE, "kind": "qualifying_offer", "player": self.name(b), "bbr_id": b,
                                        "club": club, "amount": qo, "price": self.price[b]})
        if self.pending:
            return None
        for b in self.pool:
            if b in drafted and b not in self.contracts:
                self.qualifying[b] = {"club": drafted[b], "amount": minimum(0, self.cal), "draft_rights": True}
        self.mle_used = set()
        self.traded = set()
        self.june_payroll = {c: self.payroll(c) for c in self.clubs}
        self.draw_priorities()
        if self.pending:
            return None
        for week, day in enumerate(rounds()):
            if day > self.clock:
                return None
            if day >= TRADE_FROM and not self.trade_round(day):
                return None
            if not self.round(week, day):
                return None
        if self.clock < PLACEMENT:
            return None
        self.place()
        return self.record()

    def sign_first_round(self, drafted):
        from .draft import _read as dread, year_context as draft_year
        with draft_year(YEAR, self.root):
            from . import draft as _draft
            path = self.root / _draft.RECORD
        if not path.is_file():
            return
        for p in dread(path)["picks"]:
            if p["round"] != 1 or not p.get("bbr_id"):
                continue
            scale = self.cal["scale"].get(p["pick"]) or self.cal["scale"][max(self.cal["scale"])]
            salary = int(round(scale["year1"] * ROOKIE_SCALE_SHARE))
            from .agreement import terms
            t = terms(NEW)                       # 1999: three guaranteed + a 4th-year option; 2005: two + options on 3 and 4
            years = t["rookie_guaranteed_years"]
            options = [f"{YEAR + n - 1}-{str(YEAR + n)[-2:]}" for n in t["rookie_option_years"]]
            self.contracts[p["bbr_id"]] = {"club": p["club"], "salary": salary, "years": years, "date": OPEN, "route": "rookie_scale",
                                           "source": f"{YEAR} rookie scale No. {p['pick']} at {int(ROOKIE_SCALE_SHARE * 100)}%"}
            event = {"date": OPEN, "kind": "rookie_scale_signing", "player": p["player"], "bbr_id": p["bbr_id"],
                     "club": p["club"], "salary": salary, "years": years, "team_option": options[-1]}
            if len(options) > 1:
                event["team_options"] = options
            self.events.append(event)

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

    def most_affordable(self, club, b, on):
        """The largest first-year salary the club can pay a player who is not its own: cap room, else the mid-level."""
        room = self.cap(club, on) - self.payroll(club) - self.holds(club, on)
        if room > self.cal["mle"]:
            return int(room), "cap_room"
        if club not in self.mle_used and self.payroll(club) + self.cal["mle"] <= self.ceiling(club):
            return self.cal["mle"], "mid_level"
        return 0, None

    def requested(self, day, subjects=("free_agent_target", "re_sign")):
        """{bbr_id: standing weight} for Wade's requests to pursue a free agent or keep Miami's own, dated on or before
        the day (Miami only)."""
        path = self.root / REQUESTS
        if not path.is_file():
            return {}
        from .standing import STANDING_WEIGHT, standing_on
        weight = STANDING_WEIGHT.get(standing_on(self.root, day).get("standing"), 0.0)
        return {r["bbr_id"]: weight for r in _read(path)["requests"]
                if r.get("subject") in subjects and r.get("requested") in ("pursue", "keep") and r["date"] <= day and r.get("bbr_id")}

    def requested_terms(self, day):
        """{bbr_id: term} for Wade's pursue requests that state a contract-length preference (`"term": "multi_year"`),
        dated on or before the day. The preference never sets salary: it makes a minimum offer to that player run the
        minimum exception's longest term (MINIMUM_EXCEPTION_YEARS); a larger offer already runs his wanted years."""
        path = self.root / REQUESTS
        if not path.is_file():
            return {}
        return {r["bbr_id"]: r["term"] for r in _read(path)["requests"]
                if r.get("term") and r.get("requested") in ("pursue", "keep") and r["date"] <= day and r.get("bbr_id")}

    def pursuit_request(self, kind, b, day):
        """Wade's own latest request, dated on or before the day, that Miami pursue player b by this route, or None: a
        `free_agent_target` request that says `pursue` for a free-agent signing, a `trade_target` request for a trade
        (as `runtime/trades.py` reads it). Matched by bbr_id, else by name when the request names no bbr_id."""
        path = self.root / REQUESTS
        if not path.is_file():
            return None
        subject = {"free_agent": "free_agent_target", "trade": "trade_target"}[kind]
        rows = [r for r in _read(path)["requests"]
                if r.get("subject") == subject and r.get("date", "9999") <= day
                and (r["bbr_id"] == b if r.get("bbr_id") else r.get("player") == self.name(b))
                and (kind != "free_agent" or r.get("requested") == "pursue")]
        return max(rows, key=lambda r: r["date"]) if rows else None

    def renunciation(self, club, b, day, amount, offered=()):
        """The holds Miami would renounce so its cap room pays `amount` (the offer its rule would make) to b, a free agent
        Wade asked it to pursue, from the 2006 summer (RENOUNCE_FOR_REQUEST_FROM): its own unsigned free agents valued
        below b, taken lowest value first until their holds cover the gap, then any earlier pick the later ones already
        cover is kept (checked from the most valuable down), so no hold goes that the offer does not need; never a
        player Wade asked it to keep, nor one it has already offered a contract this round. [] when the room already
        pays him, when renouncing every eligible hold would still fall short, or when Wade did not ask for him. Ordered
        lowest value first. A plan only: `round` carries it out when he accepts. A rule, never a draw
        (docs/front_office.md, Wade's requests)."""
        if YEAR < RENOUNCE_FOR_REQUEST_FROM or club != MIAMI or self.rights.get(b) == club:
            return []
        if self.pursuit_request("free_agent", b, day) is None:
            return []
        short = amount - (self.cap(club, day) - self.payroll(club) - self.holds(club, day))
        if short <= 0:
            return []
        kept = self.requested(day, ("re_sign",))
        value = self.pricing.value(b)
        lesser = sorted((x for x in self.held(club) if x not in offered and x not in kept and self.pricing.value(x) < value),
                        key=lambda x: (self.pricing.value(x), x))
        out, freed = [], 0
        for x in lesser:
            out.append(x)
            freed += self.hold(x)
            if freed >= short:
                break
        else:
            return []
        for x in reversed(out[:-1]):                   # the last pick is always needed; drop earlier ones the rest cover
            if freed - self.hold(x) >= short:
                out.remove(x)
                freed -= self.hold(x)
        return out

    def renounce(self, club, players, day, target, amount):
        """Renounce each player's hold, on the day the target accepts the offer it pays for (`round`): a dated `renounce`
        event; the club's Bird rights and any qualifying offer it tendered him end, so he is an unrestricted free agent
        whom the club can sign again only with room or an exception, like any other club."""
        for x in players:
            hold = self.hold(x)
            q = self.qualifying.get(x)
            withdrawn = q if q and q["club"] == club else None
            self.rights.pop(x, None)
            self.renounced[x] = club
            if withdrawn:
                self.qualifying.pop(x)
            event = {"date": day, "kind": "renounce", "player": self.name(x), "bbr_id": x, "club": club, "hold": hold,
                     "value": round(self.pricing.value(x), 2), "for": self.name(target), "for_bbr_id": target, "offer": amount,
                     "basis": f"{club} renounces {self.name(x)}'s ${hold:,} cap hold so its room pays the ${amount:,} offer accepted by "
                              f"{self.name(target)}, whom Wade asked it to pursue ({REQUESTS.as_posix()}): its own free agents "
                              "valued below him, lowest value first, only as many as needed (runtime/free_agency_2004.py "
                              "Market.renunciation)."}
            if withdrawn:
                event["qualifying_offer_withdrawn"] = withdrawn["amount"]
            self.events.append(event)

    def request_draw(self, b, bar, weight):
        """Wade asks Miami to keep a player its June 30 rule would let go (no qualifying offer): an engine draw with
        P(tender) = standing weight x (1 - margin), the margin being how clear-cut the rule's call was
        (`runtime/front_office.request_override`)."""
        from .front_office import request_override
        from .standing import standing_on
        margin = min(1.0, abs(bar - self.price[b]) / bar)
        p = request_override("let_go", "tender", margin, standing_on(self.root, OPTIONS_DATE)["standing"])
        if p <= 0:
            return False
        answer = self.draw({"event_id": f"{YEAR}-06-30-{_slug(self.name(b))}-qualifying-offer-request", "date": OPTIONS_DATE,
                            "question": f"Does Miami tender {self.name(b)} a qualifying offer at Wade's request?",
                            "decider": "Miami front office (engine draw on Wade's request)",
                            "options": {"tender": p, "let_go": round(1 - p, 6)},
                            "basis": f"Rule: no tender (price ${self.price[b]:,} under the bar ${int(bar):,}; margin {margin:.3f}). Wade asked "
                                     f"to keep him (10_Free_Agency/wade_requests.json); standing weight {weight} x (1 - margin) "
                                     "(docs/front_office.md, Wade's requests)."})
        if answer is None:
            return None
        return answer == "tender"

    def offers_for(self, club, week, day, open_players):
        out, short = [], ROSTER_TARGET - self.roster(club)
        if self.roster(club) >= ROSTER_MAX:
            return out
        wanted = self.requested(day) if club == MIAMI else {}
        terms_wanted = self.requested_terms(day) if club == MIAMI else {}
        ranked = sorted(open_players, key=lambda b: (-self.pricing.value(b) * (NEED_FLOOR + (1 - NEED_FLOOR) * self.need(club, self.group(b)))
                                                     * (1 + wanted.get(b, 0.0)), b))
        made_big, planned = False, set()
        for b in ranked:
            if b in planned:
                continue                                   # a hold Miami plans to renounce this round gets no offer
            ask = self.ask(b, week)
            need = self.need(club, self.group(b))
            willing = int(round(self.price[b] * (0.9 + 0.2 * need)))
            if b in wanted:                                # Wade asked: up to 110% of the club's valuation
                willing = max(willing, int(round(self.price[b] * min(REQUEST_PRICE_CEILING, 1 + 0.2 * wanted[b]))))
            amount = max(minimum(self.service(b), self.cal), min(ask, willing))
            if amount < INSULT_SHARE * ask:
                continue
            minimum_deal = amount <= minimum(self.service(b), self.cal)
            if not minimum_deal and made_big:
                continue
            if minimum_deal and short <= 0 and b not in wanted:
                continue                                   # a requested player may take a spot up to the fifteenth
            route = self.means(club, b, day, amount)
            renounce = []
            if route is None and not minimum_deal:         # from 2006: lesser holds give way to a star Wade asked for
                renounce = self.renunciation(club, b, day, amount, {o["bbr_id"] for o in out})
                if renounce:
                    route = "cap_room"
            if route is None and not minimum_deal:
                amount, route = self.most_affordable(club, b, day)
                if route is None or amount < INSULT_SHARE * ask or amount <= minimum(self.service(b), self.cal):
                    continue
            if route is None:
                continue
            if not minimum_deal and not self.consulted(club, b, day, amount):
                if self.pending:
                    return out
                continue
            years = years_wanted(self.pricing.age(b))
            if minimum_deal:                               # a minimum offer runs one season unless Wade asked for more
                years = MINIMUM_EXCEPTION_YEARS if terms_wanted.get(b) == "multi_year" else 1
            out.append({"club": club, "bbr_id": b, "salary": amount, "years": years,
                        "route": route, "ask": ask})
            if renounce:                                   # a plan: `round` renounces only if he accepts this offer
                out[-1]["renounce"] = renounce
                planned |= set(renounce)
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
        basis = f"Miami's market plan on {day}: offer ${amount:,} (runtime/free_agency_2004.py)"
        evidence = {"value": round(value, 2), "line": self.line(b), "salary": f"${amount:,} offer", "cap_position": f"payroll ${self.payroll(MIAMI):,}",
                    "fit": f"{self.group(b)} need {self.need(MIAMI, self.group(b)):.2f}", "reason": f"{YEAR} free agency"}
        if self.answered_by_request("free_agent", b, club, day, basis, evidence, standing):
            return True
        state_path = self.root / f"career/Dwyane_Wade/{SEASON}/current_state.json"
        state = _read(state_path)
        C.ask(self.root, state, day, "free_agent", name, b, club, basis=basis, evidence=evidence, season=SEASON, standing=standing)
        _write(state_path, state)
        self.pending = True
        return False

    def answered_by_request(self, kind, b, club, day, basis, evidence, standing, trade_id=None):
        """From the 2006 summer (REQUEST_ANSWERS_CONSULTATION_FROM) a star Wade himself asked Miami to pursue needs no
        question: his request is the answer. Miami writes the consultation record the ask would write, dated the day it
        would ask, answered `approve` on that day from the request (its file, date and words), with its page, and the
        market goes on. Only his request for that player and route counts (`pursuit_request`: a free-agent `pursue` for
        a signing, a `trade_target` for a trade); the caller checks an objection first and it stands; a question already
        open waits for his own answer; a request whose `consultation` entry gives another answer is not an approval.
        Returns True when the request answered."""
        if YEAR < REQUEST_ANSWERS_CONSULTATION_FROM:
            return False
        from . import consultations as C
        name = self.name(b)
        request = self.pursuit_request(kind, b, day)
        if request is None or (request.get("consultation") or {}).get("standing_answer", "approve") != "approve":
            return False
        if C.open_record(self.root, SEASON, name, kind) is not None:
            return False
        source = REQUESTS.as_posix()
        words = request.get("words") or request.get("note") or ""
        cid = C.consultation_id(day, kind, name)
        record = {"schema_version": 1, "id": cid, "date": day, "kind": kind, "player": name, "bbr_id": b, "club": club,
                  "terms": None, "trade_id": trade_id,
                  "standing": {"standing": standing["standing"], "as_of": standing.get("as_of")},
                  "star_basis": {"value": evidence.get("value"), "rule": C.RULE}, "basis": basis, "status": "closed",
                  "answer": "approve", "answered": day,
                  "note": f"Answered by Wade's own request of {request['date']} that Miami pursue {name} ({source}): \"{words}\"",
                  "answered_by_request": {"source": source, "date": request["date"], "subject": request["subject"],
                                          "requested": request.get("requested"), "words": words}}
        if request.get("consultation"):
            record["answered_by_request"]["consultation"] = request["consultation"]
        folder = C.folder(self.root, SEASON)
        path = folder / f"{cid}.json"
        if not path.exists():
            _write(path, record)
            (folder / C.page_name(record)).write_text(_request_answer_page(record, evidence), encoding="utf-8")
        return True

    def line(self, b):
        e = self.pricing.evidence.get(b)
        if not e:
            return "no simulated 2003-04 line"
        return f"{e['games']} games, {e['mpg']:.1f} minutes, efficiency {e['eff'] / e['games']:.1f} a game (simulated 2003-04)"

    def draw_priorities(self):
        """Each free agent's priority, drawn once on July 1 with the 2003 odds by age (runtime/market.py)."""
        from .market import TRAIT_ODDS
        self.trait = {}
        for b in self.pool:
            a = self.pricing.age(b) or 27
            odds = next(o for limit, o in TRAIT_ODDS if a <= limit)
            t = self.draw({"event_id": f"{YEAR}-07-01-{_slug(self.name(b))}-priorities", "date": OPEN,
                           "question": f"What does {self.name(b)} weigh most in choosing his 2004 contract?",
                           "decider": f"{self.name(b)} (simulated player, engine draw)", "options": dict(odds),
                           "basis": f"Trait odds by age ({a}): money, fame, loyalty, winning (runtime/market.py TRAIT_ODDS; "
                                    "docs/front_office_design.md 4.3). Drawn once for the 2004 market."})
            if t is not None:
                self.trait[b] = t

    def wins(self, club):
        return CHARLOTTE_WINS if (club == CHARLOTTE and YEAR == 2004) else round(82 * self.standings.get(club, 0.5))

    def role_minutes(self, club, b):
        g, v = self.group(b), self.pricing.value(b)
        rank = sum(1 for x, c in self.contracts.items() if c["club"] == club and x != b and self.group(x) == g and self.pricing.value(x) > v)
        ladder = ROLE_LADDER[g]
        return ladder[min(rank, len(ladder) - 1)]

    def profile(self, b, week):
        e = self.pricing.evidence.get(b)
        return {"ask": self.ask(b, week), "years_wanted": years_wanted(self.pricing.age(b)), "age": self.pricing.age(b),
                "prior_minutes": round(e["mpg"], 1) if e else None, "start_share": e["starts"] / e["games"] if e else 0.0,
                "prior_club": self.rights.get(b) or self.renounced.get(b)}     # renouncing ends rights, not his ties

    def assess(self, b, offer, week):
        """(utility points, dealbreaker or None) of an offer, by the 2003 factor model with his drawn priority."""
        from . import player_utility as pu
        rate = pu.ask_raise(NEW, self.root)
        player = dict(self.profile(b, week), ask_raise=rate)
        situation = {"club": offer["club"], "role_minutes": self.role_minutes(offer["club"], b), "strength": self.wins(offer["club"])}
        terms = {"guaranteed": sum(offer["salary"] * (1 + rate * i) for i in range(offer["years"])), "years": offer["years"]}
        score = pu.scores(terms, situation, player)
        return pu.utility(score, pu.weights(player["age"], self.trait.get(b, "money"))), pu.dealbreaker(situation, player)

    # ---- summer trades
    def stance(self, club):
        if club == CHARLOTTE:
            return "rebuilding"
        pct = self.standings.get(club, 0.5)
        return "contending" if pct >= 50 / 82 else "rebuilding" if pct <= 30 / 82 else "middle"

    def tradable(self, b, c, day):
        if b in UNTOUCHABLE or b in self.traded:
            return False                               # a player traded this summer is not moved again before camp
        if c.get("route") in ("existing", "option"):
            return True
        if c.get("route") == "rookie_scale":
            return (date.fromisoformat(day) - date.fromisoformat(c["date"])).days >= ROOKIE_TRADE_DAYS
        return day >= NEW_SIGNING_TRADABLE

    def group_value(self, club, g, without=(), adding=()):
        vals = sorted([self.pricing.value(x) for x, c in self.contracts.items()
                       if c["club"] == club and self.group(x) == g and x not in without] + [self.pricing.value(x) for x in adding if self.group(x) == g],
                      reverse=True)
        return vals

    def worth(self, club, b, own):
        """A contract's trade worth to a club, in production points over this season and up to two more: production
        above replacement raised to STAR_EXPONENT, times the honor factor (defense the box score misses), positional fit and the stance's age weight, less salary at
        the stance's cash weight; a held player carries the status-quo premium."""
        from .trades import STANCE_WEIGHTS
        from .valuation import REPLACEMENT_EFF_PER_GAME
        c = self.contracts[b]
        stance = self.stance(club)
        w = STANCE_WEIGHTS[stance]
        a = self.pricing.age(b) or 27
        age_w = (1.2 if a <= 25 else 0.8 if a >= 31 else 1.0) if stance == "rebuilding" else \
                (0.85 if a <= 23 else 1.0) if stance == "contending" else 1.0
        need = self.need_without(club, self.group(b), b if own else None)
        fit = NEED_FLOOR + (1 - NEED_FLOOR) * need
        talent = max(0.0, self.pricing.value(b) - REPLACEMENT_EFF_PER_GAME) ** STAR_EXPONENT * self.pricing.honors.honor_factor(b)
        seasons = min(3, max(1, c.get("years", 1)))
        per = talent * fit * age_w * (w["now"] + w["future"]) / 2 - c["salary"] / 1e6 * SALARY_POINTS_PER_MILLION * w["cash"]
        value = per * seasons
        return value * STATUS_QUO if own and value > 0 else value

    @staticmethod
    def package(values):
        """A package's worth: its best player in full, the next at PACKAGE_WEIGHTS[1]; negative worth counts in full."""
        pos = sorted((v for v in values if v > 0), reverse=True)
        return sum(v * PACKAGE_WEIGHTS[min(i, len(PACKAGE_WEIGHTS) - 1)] for i, v in enumerate(pos)) + sum(v for v in values if v <= 0)

    def need_without(self, club, g, b):
        key = (club, g, b)
        if key not in self._need_cache:
            mins = sorted((self.mpg(x) for x, c in self.contracts.items() if c["club"] == club and self.group(x) == g and x != b), reverse=True)
            covered = sum(mins[:3 if g != "C" else 2])
            self._need_cache[key] = max(0.0, min(1.0, (TARGET_MINUTES[g] - covered) / TARGET_MINUTES[g]))
        return self._need_cache[key]

    def legal_trade(self, club, out_salary, in_salary, day):
        if self.payroll(club) - out_salary + in_salary <= self.cap(club, day):
            return True
        from .agreement import terms
        t = terms(NEW) if YEAR != 2004 else {"trade_match": TRADE_MATCH, "trade_plus": TRADE_PLUS}
        return in_salary <= out_salary * t["trade_match"] + t["trade_plus"]                 # 125% from the 2005 agreement

    def trade_proposals(self, day):
        from .trades import SEARCH_MIN_ACCEPT, acceptance
        self._need_cache = {}
        cands = {}
        for club in self.clubs:
            own = [b for b, c in self.contracts.items() if c["club"] == club and self.tradable(b, c, day)]
            cands[club] = sorted(own, key=lambda b: (-self.pricing.value(b), b))[:TRADE_CANDIDATES]
        worth = {}
        def wv(club, b, own):
            k = (club, b, own)
            if k not in worth:
                worth[k] = self.worth(club, b, own)
            return worth[k]
        found = []
        clubs = sorted(c for c in self.clubs if cands.get(c))
        for i, a in enumerate(clubs):
            pa_list = [(x,) for x in cands[a]] + [(x, y) for k, x in enumerate(cands[a]) for y in cands[a][k + 1:]]
            for bclub in clubs[i + 1:]:
                pb_list = [(x,) for x in cands[bclub]] + [(x, y) for k, x in enumerate(cands[bclub]) for y in cands[bclub][k + 1:]]
                for pa in pa_list:
                    sa = sum(self.contracts[x]["salary"] for x in pa)
                    for pb in pb_list:
                        if len(pa) + len(pb) > 3:
                            continue
                        sb = sum(self.contracts[x]["salary"] for x in pb)
                        if not self.legal_trade(a, sa, sb, day) or not self.legal_trade(bclub, sb, sa, day):
                            continue
                        if self.roster(a) - len(pa) + len(pb) > ROSTER_MAX and len(pb) > len(pa):
                            continue
                        if self.roster(bclub) - len(pb) + len(pa) > ROSTER_MAX and len(pa) > len(pb):
                            continue
                        gain = {}
                        for club, out, inc in ((a, pa, pb), (bclub, pb, pa)):
                            before = self.package([wv(club, x, True) for x in out])
                            after = self.package([wv(club, x, False) for x in inc])
                            gain[club] = (after - before) / max(abs(after), abs(before), 1.0)
                        if min(gain.values()) < MIN_MUTUAL_GAIN:
                            continue
                        chances = {c: acceptance({"objective_gain": g}) for c, g in gain.items()}
                        if any(p is None or p < SEARCH_MIN_ACCEPT for p in chances.values()):
                            continue
                        found.append({"date": day, "clubs": [a, bclub],
                                      "a": {"club": a, "sends": [self.name(x) for x in pa], "bbr_ids": list(pa), "salary": sa},
                                      "b": {"club": bclub, "sends": [self.name(x) for x in pb], "bbr_ids": list(pb), "salary": sb},
                                      "gain": {c: round(g, 3) for c, g in gain.items()}, "accept": chances,
                                      "both": round(chances[a] * chances[bclub], 6)})
        found.sort(key=lambda r: (-min(r["gain"].values()), r["a"]["bbr_ids"], r["b"]["bbr_ids"]))
        chosen, used = [], set()
        for row in found:
            if len(chosen) >= MAX_TRADES_PER_ROUND:
                break
            keys = set(row["clubs"]) | set(row["a"]["bbr_ids"]) | set(row["b"]["bbr_ids"])
            if used & keys:
                continue
            used |= keys
            row["id"] = f"{YEAR}-summer-trade-{day}-" + "-".join(sorted(row["a"]["bbr_ids"] + row["b"]["bbr_ids"]))
            chosen.append(row)
        return chosen

    def trade_round(self, day):
        """The round's proposals (searched once and stored), each an engine draw; accepted deals move the contracts."""
        path = self.root / DRAWS / f"{YEAR}-summer-trades-{day}.proposals.json"
        if self.store and path.is_file():
            chosen = _read(path)["deals"]
        else:
            chosen = []
            for row in self.trade_proposals(day):
                answer = self.trade_consulted(row, day) if MIAMI in row["clubs"] else "ok"
                if answer == "asked":
                    return False
                if answer == "ok":
                    chosen.append(row)                     # an objection by Wade drops the deal
            if self.store:
                _write(path, {"schema_version": 1, "date": day, "rule": "runtime/free_agency_2004.py Market.trade_proposals", "deals": chosen})
        for row in chosen:
            if any(self.contracts.get(b, {}).get("club") != row[side]["club"] for side in ("a", "b") for b in row[side]["bbr_ids"]):
                raise ValueError(f"{row['id']}: a stored deal no longer matches the contracts it moves")
            answer = self.draw({"event_id": row["id"], "date": day,
                                "question": f"Do {row['a']['club']} and {row['b']['club']} trade {' and '.join(row['a']['sends'])} "
                                            f"for {' and '.join(row['b']['sends'])} on {day}?",
                                "decider": f"{row['a']['club']} and {row['b']['club']} front offices (engine draw)",
                                "options": {"accept": row["both"], "decline": round(1 - row["both"], 6)},
                                "basis": f"Gains on own objectives {row['gain']}; acceptance {row['accept']}; 1999 salary rule met "
                                         "(runtime/free_agency_2004.py summer trades)."})
            if answer != "accept":
                continue
            for side, other in (("a", "b"), ("b", "a")):
                for name, b in zip(row[side]["sends"], row[side]["bbr_ids"]):
                    self.contracts[b] = dict(self.contracts[b], club=row[other]["club"], source=self.contracts[b]["source"] + f"; traded {day}")
                    self.traded.add(b)
                    self.events.append({"date": day, "kind": "trade", "player": name, "bbr_id": b, "club": row[other]["club"],
                                        "from": row[side]["club"], "salary": self.contracts[b]["salary"], "deal": row["id"]})
        return not self.pending

    def trade_consulted(self, row, day):
        side = "b" if row["a"]["club"] == MIAMI else "a"
        for b in row[side]["bbr_ids"]:
            from . import consultations as C
            from .standing import standing_on
            value = self.pricing.value(b)
            standing = standing_on(self.root, day)
            if not C.consultation_required(standing.get("standing"), value):
                continue
            name = self.name(b)
            if C.objected(self.root, SEASON, name, day):
                return "objected"
            if C.approved(self.root, SEASON, "trade", name, day):
                continue
            basis = f"Miami's summer trade search on {day}: {' and '.join(row['a']['sends'])} for {' and '.join(row['b']['sends'])}"
            evidence = {"value": round(value, 2), "line": self.line(b), "salary": f"${self.contracts[b]['salary']:,}",
                        "cap_position": f"payroll ${self.payroll(MIAMI):,}", "fit": self.group(b), "reason": f"{YEAR} summer trade"}
            if self.answered_by_request("trade", b, row[side]["club"], day, basis, evidence, standing, trade_id=row.get("id")):
                continue
            state_path = self.root / f"career/Dwyane_Wade/{SEASON}/current_state.json"
            state = _read(state_path)
            C.ask(self.root, state, day, "trade", name, b, row[side]["club"], basis=basis, evidence=evidence,
                  season=SEASON, standing=standing)
            _write(state_path, state)
            self.pending = True
            return "asked"
        return "ok"

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
            assessed = {o["club"]: self.assess(b, o, week) for o in options}
            us = {c: u for c, (u, walk) in assessed.items() if not walk}
            if not us:
                continue                                   # every offer is a role he will not take: he waits, undrawn
            m = max(us.values())
            ex = {c: math.exp((u - m) / CHOICE_TEMPERATURE) for c, u in us.items()}
            z = sum(ex.values())
            probs = {c: p_accept * v / z for c, v in ex.items()}
            probs["wait"] = 1 - p_accept
            answer = self.draw({"event_id": f"{YEAR}-fa-{day}-{_slug(self.name(b))}", "date": day,
                                "question": f"{YEAR} free agency, {day}: which offer does {self.name(b)} accept ("
                                            + ", ".join(f"{o['club']} ${o['salary']:,} x {o['years']}" for o in options) + "), or does he wait?",
                                "decider": f"{self.name(b)} (simulated player, engine draw)", "options": probs,
                                "basis": f"Ask ${self.ask(b, week):,}; best offer {ratio:.2f} of the ask in total; accept chance {p_accept:.3f}; "
                                         f"priority {self.trait.get(b, 'money')}; utility " + ", ".join(f"{c} {u:.1f}" for c, u in us.items())
                                         + "; " + "; ".join(f"{c} walks: {w}" for c, (_, w) in assessed.items() if w)
                                         + " (runtime/player_utility.py, runtime/free_agency_2004.py)."})
            if answer is None or answer == "wait":
                continue
            accepted.append(dict(next(o for o in options if o["club"] == answer), trait=self.trait.get(b)))
        if self.pending:
            return False
        for o in accepted:                                 # from 2006: the holds go only once the target has said yes,
            plan = o.pop("renounce", None)                 # before any signing, so no renounced player's sheet is matched
            if plan:
                self.renounce(o["club"], [x for x in plan if x not in self.contracts], day, o["bbr_id"], o["salary"])
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
                             "source": f"{YEAR} simulated free agency"}
        if matched:
            return
        kind = "re_sign" if self.rights.get(b) == club else "signing"
        self.events.append({"date": when, "kind": kind, "player": self.name(b), "bbr_id": b, "club": club, "from": self.rights.get(b) or self.renounced.get(b),
                            "salary": o["salary"], "years": o["years"], "route": o["route"], "agreed": day})

    def place(self):
        """A restricted player still unsigned accepts his qualifying offer. Then clubs short of ROSTER_TARGET sign the best remaining players at the minimum; the rest stay unsigned in the
        pool for the in-season market (runtime/league_market.py)."""
        for b, q in sorted(self.qualifying.items()):
            if b in self.contracts or q.get("draft_rights"):
                continue
            self.contracts[b] = {"club": q["club"], "salary": q["amount"], "years": 1, "date": PLACEMENT, "route": "qualifying_offer",
                                 "source": f"{YEAR} qualifying offer accepted"}
            self.events.append({"date": PLACEMENT, "kind": "qualifying_offer_accepted", "player": self.name(b), "bbr_id": b,
                                "club": q["club"], "salary": q["amount"], "years": 1})
        left = sorted((b for b in self.pool if b not in self.contracts), key=lambda b: (-self.pricing.value(b), b))
        for b in left:
            short = [c for c in self.clubs if self.roster(c) < ROSTER_TARGET]
            if not short:
                break
            club = min(short, key=lambda c: (-self.need(c, self.group(b)), self.roster(c), c))
            salary, route = minimum(self.service(b), self.cal), "minimum"
            top, how = self.most_affordable(club, b, PLACEMENT) if self.rights.get(b) != club else (self.price[b], "bird")
            if how and top > salary:
                salary, route = max(salary, min(top, int(round(self.price[b] * ASK_FLOOR_SHARE)))), how
                if route == "mid_level":
                    self.mle_used.add(club)
            self.contracts[b] = {"club": club, "salary": salary, "years": 1, "date": PLACEMENT, "route": route,
                                 "source": f"{YEAR} camp signing (roster minimum)"}
            self.events.append({"date": PLACEMENT, "kind": "camp_signing", "player": self.name(b), "bbr_id": b, "club": club,
                                "from": self.rights.get(b) or self.renounced.get(b), "salary": salary, "years": 1, "route": route})
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
                "left_the_league": [{"player": self.name(b), "bbr_id": b, "basis": f"no real {NEW} role"} for b in departed if b not in self.roles]}


def run(root=ROOT, clock=None, year=2004):
    """Replay the summer to the clock. Writes the record when the market is complete; returns it, else None."""
    from .write_back import clock as career_clock
    root = Path(root)
    with year_context(year, root):
        if (root / RECORD).is_file() or (clock or career_clock(root)) < OPTIONS_DATE:
            return None
        market = Market(root, clock)
        record = market.run()
        if record:
            _write(root / RECORD, record)
        return record


def record_path(year=2004):
    """The summer market record for a year (its season's 10_Free_Agency folder)."""
    y = int(year)
    return Path(f"career/Dwyane_Wade/{y - 1}-{str(y)[-2:]}/10_Free_Agency/free_agency_{y}.json")


def market_year(season):
    """The summer whose market opened a season ("2005-06" opened in 2005)."""
    return int(season[:4])


def record_for(season):
    """The summer market record that opened a season."""
    return record_path(market_year(season))


def signed_clubs(root=ROOT, year=None):
    """{bbr_id: club} for every contract the year's market made once it is complete (default: the current context's
    year, 2004 outside a year_context), else {}."""
    path = Path(root) / (record_path(year) if year else RECORD)
    if not path.is_file():
        return {}
    return {r["bbr_id"]: club for club, rows in _read(path)["clubs"].items() for r in rows}
