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

ROOT = Path(__file__).resolve().parents[1]
STATS_PATH = Path("library/2003/league/nba_2002_03_player_stats.json")
CONTRACTS_PATH = Path("library/2003/league/nba_2003_contracts.json")
RIGHTS_PATH = Path("library/2003/league/nba_2003_free_agent_rights.json")
END_OF_SEASON_PATH = Path("library/2003/league/nba_2003_end_of_season.json")
REGISTRY_PATH = Path("career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json")
CAP_RULES_PATH = Path("library/2003/league/nba_2003_04_cap_rules.json")

# Judgement constants, named so they can be revisited.
REPLACEMENT_EFF_PER_GAME = 5.0      # a minimum-salary player's production
PRIOR_MINUTES = 500                 # minutes at which half the shrinkage toward replacement is gone
AGE_FACTOR = ((24, 1.08), (26, 1.04), (28, 1.00), (30, 0.96), (32, 0.90), (34, 0.82), (36, 0.72), (99, 0.60))
MIN_FIT_MINUTES = 500               # comparables: players with at least this many 2002-03 minutes


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
        self.on, self.root = on, Path(root)
        self.stats = {r["bbr_id"]: r for r in read(STATS_PATH, root)["records"]}
        self.birth = {}
        for club in read(END_OF_SEASON_PATH, root)["clubs"].values():
            for p in club["players"]:
                if p.get("bbr_id") and p.get("birth_date"):
                    self.birth[p["bbr_id"]] = p["birth_date"]
        for p in read(REGISTRY_PATH, root)["players"]:
            if p.get("bbr_id") and p.get("birth_date"):
                self.birth.setdefault(p["bbr_id"], p["birth_date"])
        rules = read(CAP_RULES_PATH, root)
        self.maximums = rules["maximum_salary"]
        self.minimums = rules["minimum_salary"]
        self.mid_level = rules["exceptions"]["mid_level"]
        self.service = {}
        for club in read(RIGHTS_PATH, root)["clubs"].values():
            for p in club["free_agents"]:
                self.service[p["bbr_id"]] = p.get("nba_seasons_before_2003_04")
        self.fit = self._fit_comparables()

    def age(self, bbr_id):
        birth = self.birth.get(bbr_id)
        return age_on(birth, self.on) if birth else None

    def value(self, bbr_id):
        record = self.stats.get(bbr_id)
        if record is None:
            return None
        return production_value(record["totals"], self.age(bbr_id))

    def _fit_comparables(self):
        """log(2003-04 salary) against production value, on players under contract (median-based fit)."""
        xs, ys = [], []
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
        y = years_of_service or 0
        key = "10_plus_years" if y >= 10 else f"{min(y, 2)}_year{'s' if min(y, 2) != 1 else ''}"
        return self.minimums.get(key) or self.minimums["2_years"]

    def comparables_price(self, value):
        """First-year salary the inventory pays for this production value."""
        return math.exp(self.fit["intercept"] + self.fit["slope"] * value)

    def price(self, bbr_id, years_of_service=None, prior_salary=None):
        """Comparables price inside the player's minimum and maximum. None without 2002-03 evidence."""
        value = self.value(bbr_id)
        if value is None:
            return None
        service = years_of_service if years_of_service is not None else self.service.get(bbr_id)
        raw = self.comparables_price(value)
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
