"""Player value and price for the front office (docs/front_office_design.md, sections 4.1 and 4.2).

Everything here reads evidence dated on or before the career date: 2002-03
statistics and the June 26, 2003 contract inventory. Real later contracts and
real-career trajectories never enter.

Production value: NBA efficiency (points + rebounds + assists + steals + blocks
- missed field goals - missed free throws - turnovers) per game of the prior
season, shrunk toward a replacement level by minutes, times an age factor.
It is a judgement model for pricing, as agents and clubs of the era priced on
box-score production; it is not the engine's rating.

Price: a comparables rate fitted on the inventory (first-year 2003-04 salary of
players under contract against their production value), applied inside the
minimum and maximum for the player's years of service.
"""
from datetime import date
import json
import math
from pathlib import Path
import statistics

from .cba import minimum_salary

ROOT = Path(__file__).resolve().parents[1]
STATS_PATH = Path("library/2003/league/nba_2002_03_player_stats.json")
CONTRACTS_PATH = Path("library/2003/league/nba_2003_contracts.json")
RIGHTS_PATH = Path("library/2003/league/nba_2003_free_agent_rights.json")
END_OF_SEASON_PATH = Path("library/2003/league/nba_2003_end_of_season.json")
REGISTRY_PATH = Path("career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json")
MIAMI_REGISTER_PATH = Path("career/Dwyane_Wade/2003-04/00_Team/Team/Roster/roster.json")
CAP_RULES_PATH = Path("library/2003/league/nba_2003_04_cap_rules.json")

# Judgement constants, named so they can be revisited.
REPLACEMENT_EFF_PER_GAME = 5.0      # a minimum-salary player's production
PRIOR_MINUTES = 500                 # minutes at which half the shrinkage toward replacement is gone
AGE_FACTOR = ((24, 1.08), (26, 1.04), (28, 1.00), (30, 0.96), (32, 0.90), (34, 0.82), (36, 0.72), (99, 0.60))
MIN_FIT_MINUTES = 500               # comparables: players with at least this many 2002-03 minutes
# Honors move a player's market (roadmap 15a; judgement, documented in docs/front_office_design.md): a premium on the
# comparables price for each honor announced on or before the date in the most recent season. The largest premium
# counts in full, every other at a quarter, capped; the 1999 maximum still bounds the price. Weekly and monthly awards
# carry none. Every player alike, from the simulated award records only.
HONOR_PREMIUM = {"Most Valuable Player": 0.30, "Finals MVP": 0.15, "All-NBA First Team": 0.25, "All-NBA Second Team": 0.15,
                 "All-NBA Third Team": 0.10, "Defensive Player of the Year": 0.10, "All-Defensive First Team": 0.05,
                 "All-Defensive Second Team": 0.03, "Rookie of the Year": 0.05, "Sixth Man of the Year": 0.05,
                 "Most Improved Player": 0.05, "All-Rookie First Team": 0.02, "All-Rookie Second Team": 0.01,
                 "All-Star": 0.08}
HONOR_CAP = 0.35
SEASON_AWARDS_PATH = Path("career/Dwyane_Wade/Stats_and_Awards/League/2003-04/season_awards.json")


def read(path, root=ROOT):
    return json.loads((Path(root) / path).read_text(encoding="utf-8"))


def age_on(birth_date, on):
    b, d = date.fromisoformat(birth_date), date.fromisoformat(on)
    return d.year - b.year - ((d.month, d.day) < (b.month, b.day))


def age_factor(age):
    if age is None:
        return 1.0
    return next(f for limit, f in AGE_FACTOR if age <= limit)


def efficiency(t):
    """NBA efficiency total from season totals."""
    return (t["points"] + t["offensive_rebounds"] + t["defensive_rebounds"] + t["assists"] + t["steals"]
            + t["blocks"] - (t["field_goals_attempted"] - t["field_goals_made"])
            - (t["free_throws_attempted"] - t["free_throws_made"]) - t["turnovers"])


def production_value(totals, age=None):
    """Efficiency per game, shrunk toward replacement by minutes, times the age factor."""
    minutes = totals["minutes"]
    if minutes <= 0 or totals["games"] <= 0:
        return REPLACEMENT_EFF_PER_GAME * age_factor(age)
    per_game = efficiency(totals) / totals["games"]
    weight = minutes / (minutes + PRIOR_MINUTES)
    shrunk = weight * per_game + (1 - weight) * REPLACEMENT_EFF_PER_GAME
    return shrunk * age_factor(age)


class Valuation:
    """Values and prices on a career date, from the dated evidence files."""

    def __init__(self, on, root=ROOT):
        from .season_evidence import market_season, prior_records
        self.on, self.root = on, Path(root)
        self.season = market_season(on) if on >= "2003-06-01" else "2003-04"
        self.first = self.season == "2003-04"            # the June 2003 import's sources; later seasons read the sim
        self.stats = ({r["bbr_id"]: r for r in read(STATS_PATH, root)["records"]} if self.first
                      else prior_records(self.season, root))
        self.birth = {}
        for club in read(END_OF_SEASON_PATH, root)["clubs"].values():
            for p in club["players"]:
                if p.get("bbr_id") and p.get("birth_date"):
                    self.birth[p["bbr_id"]] = p["birth_date"]
        for p in read(REGISTRY_PATH, root)["players"]:
            if p.get("bbr_id") and p.get("birth_date"):
                self.birth.setdefault(p["bbr_id"], p["birth_date"])
        # Miami's register carries sourced birth dates for players the end-of-season baseline lacks (Eddie Jones,
        # Haslem, Parks, Wallace, Marks); a birth date is identity known on every date, so every player is aged alike.
        register = Path(root) / MIAMI_REGISTER_PATH
        if register.is_file():
            for p in read(MIAMI_REGISTER_PATH, root)["players"]:
                if p.get("bbr_id") and p.get("date_of_birth"):
                    self.birth.setdefault(p["bbr_id"], p["date_of_birth"])
        from .seasons import path as season_path
        rules = read(CAP_RULES_PATH if self.first else season_path(self.season, "cap_rules"), root)
        self.maximums = rules["maximum_salary"]
        self.minimums = rules["minimum_salary"]
        self.mid_level = rules["exceptions"]["mid_level"]
        self.service = {}
        if self.first:
            for club in read(RIGHTS_PATH, root)["clubs"].values():
                for p in club["free_agents"]:
                    self.service[p["bbr_id"]] = p.get("nba_seasons_before_2003_04")
        else:
            from .free_agency_2004 import identity
            self.service = {b: e.get("service") for b, e in identity(root).items()}
            for b, e in identity(root).items():
                if e.get("birth_date"):
                    self.birth.setdefault(b, e["birth_date"])
        self.fit = self._fit_comparables()
        self.honors = self._honors()

    def _honors(self):
        """{bbr_id: [honor names]} from the most recent season's awards announced on or before the date."""
        from .seasons import previous_season
        rel = SEASON_AWARDS_PATH if self.first else Path(f"career/Dwyane_Wade/Stats_and_Awards/League/{previous_season(self.season)}/season_awards.json")
        path = self.root / rel
        if not path.is_file():
            return {}
        from .season_awards import honors
        by_name = {p["name"]: p["bbr_id"] for p in read(REGISTRY_PATH, self.root)["players"] if p.get("bbr_id")}
        out = {}
        for d in read(rel, self.root)["decisions"]:
            if d["announced_on"] > self.on:
                continue
            for player, name, _ in honors(d):
                if by_name.get(player):
                    out.setdefault(by_name[player], []).append(name)
        stars = path.with_name("all_star.json")                         # All-Star selections (runtime/all_star.py)
        if stars.is_file():
            for a in read(stars.relative_to(self.root), self.root).get("all_stars", []):
                bbr = a.get("bbr_id") or by_name.get(a["player"])
                if bbr and max(a["selected_on"], a.get("recorded_on") or "") <= self.on:
                    out.setdefault(bbr, []).append("All-Star")
        return out

    def honor_factor(self, bbr_id):
        """1 + the honor premium (HONOR_PREMIUM): the largest in full, the others at a quarter, at most HONOR_CAP."""
        premiums = sorted((HONOR_PREMIUM.get(h, 0.0) for h in self.honors.get(bbr_id, [])), reverse=True)
        if not premiums:
            return 1.0
        return 1.0 + min(HONOR_CAP, premiums[0] + 0.25 * sum(premiums[1:]))

    def market_price(self, value, bbr_id=None):
        """The comparables price for a production value, times the player's honor factor."""
        return self.comparables_price(value) * (self.honor_factor(bbr_id) if bbr_id else 1.0)

    def age(self, bbr_id):
        birth = self.birth.get(bbr_id)
        return age_on(birth, self.on) if birth else None

    def value(self, bbr_id):
        record = self.stats.get(bbr_id)
        if record is None:
            return None
        return production_value(record["totals"], self.age(bbr_id))

    def _fit_comparables(self):
        """log(salary) against production value, on players under contract for the season (median-based fit): the June
        2003 inventory for the first season, the league's contracts for the season after it."""
        xs, ys = [], []
        if not self.first:
            from .league_contracts import under_contract
            for b, c in under_contract(self.season, self.root).items():
                record = self.stats.get(b)
                if not c.get("salary") or record is None or record["totals"]["minutes"] < MIN_FIT_MINUTES:
                    continue
                xs.append(production_value(record["totals"], self.age(b)))
                ys.append(math.log(c["salary"]))
            mx, my = statistics.mean(xs), statistics.mean(ys)
            slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
            return {"intercept": my - slope * mx, "slope": slope, "n": len(xs)}
        for club in read(CONTRACTS_PATH, self.root)["clubs"].values():
            for p in club["players"]:
                salary = p.get("schedule", {}).get("2003-04")
                record = self.stats.get(p.get("bbr_id"))
                if p["status"] not in ("under_contract", "under_contract_unverified") or not salary or record is None:
                    continue
                if record["totals"]["minutes"] < MIN_FIT_MINUTES:
                    continue
                xs.append(production_value(record["totals"], self.age(p["bbr_id"])))
                ys.append(math.log(salary))
        mx, my = statistics.mean(xs), statistics.mean(ys)
        slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
        return {"intercept": my - slope * mx, "slope": slope, "n": len(xs)}

    def maximum(self, years_of_service, prior_salary=None):
        tier = ("0_to_6_years" if (years_of_service or 0) <= 6 else "7_to_9_years" if years_of_service <= 9 else "10_plus_years")
        base = self.maximums[tier]
        return max(base, round(prior_salary * 1.05)) if prior_salary else base

    def minimum(self, years_of_service):
        """The 1999 CBA minimum for the years of service (unknown service prices at the rookie minimum;
        a signing must pass recorded service, see `signing_minimum`)."""
        return minimum_salary(years_of_service or 0, self.season, root=self.root)   # the season's own scale

    def signing_minimum(self, years_of_service, nba_history=True):
        """The minimum Miami must pay to sign him: a veteran without recorded service is refused."""
        if years_of_service is None and nba_history:
            raise ValueError("a veteran's years of NBA service must be recorded before a minimum contract")
        return minimum_salary(years_of_service or 0, self.season, root=self.root)

    def comparables_price(self, value):
        """First-year salary the inventory pays for this production value."""
        return math.exp(self.fit["intercept"] + self.fit["slope"] * value)

    def price(self, bbr_id, years_of_service=None, prior_salary=None):
        """Comparables price inside the player's minimum and maximum. None without 2002-03 evidence."""
        value = self.value(bbr_id)
        if value is None:
            return None
        service = years_of_service if years_of_service is not None else self.service.get(bbr_id)
        raw = self.market_price(value, bbr_id)
        return int(round(min(self.maximum(service, prior_salary), max(self.minimum(service), raw))))

    def tier(self, salary):
        if salary >= self.maximums["0_to_6_years"]:
            return "maximum"
        if salary >= self.mid_level * 1.5:
            return "above_mid_level"
        if salary >= self.mid_level * 0.9:
            return "mid_level"
        if salary >= self.mid_level * 0.4:
            return "rotation"
        return "minimum"
