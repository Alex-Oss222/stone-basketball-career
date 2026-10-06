"""The collective bargaining agreement's contract terms for a season, in one place (the season-change audit, December 2004
on the career clock: the 2005 market would otherwise price on a mix of 2005 and 1999 terms).

Through 2004-05 the 1999 agreement's terms, exactly as the code used them (so every recorded summer and trade replays
unchanged). From 2005-06 the 2005 agreement (`library/2005/league/nba_2005_cba_rules.json`, sourced from the 2005 Salary
Cap FAQ): maximum salaries (the hard 2005-06 figures, then the agreement's formula), raises, contract lengths, the rookie
scale's structure and traded-salary matching. Every reader asks `terms(season)`; nothing hard-codes an agreement.
"""
import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CBA_2005 = Path("library/2005/league/nba_2005_cba_rules.json")
FIRST_2005_SEASON = "2005-06"

TERMS_1999 = {
    "agreement": "1999",
    "max_share": {"0_to_6_years": 0.25, "7_to_9_years": 0.30, "10_plus_years": 0.35},
    "max_floor": {},
    "max_fixed": {},
    "raise_bird": 0.125, "raise_other": 0.10,
    "max_years_bird": 7, "max_years_other": 6,
    "rookie_guaranteed_years": 3, "rookie_option_years": (4,),
    "trade_match": 1.15, "trade_plus": 100_000,
}


@lru_cache(maxsize=8)
def _cba_2005(root):
    return json.loads((Path(root) / CBA_2005).read_text(encoding="utf-8"))


def terms(season, root=ROOT):
    """The agreement's contract terms in force for `season`."""
    if season < FIRST_2005_SEASON:
        return dict(TERMS_1999)
    d = _cba_2005(str(Path(root).resolve()))
    raises = d["annual_raises"]
    length = d["contract_length"]
    fixed = d["maximum_salary"].get(season.replace("-", "_"), {}).get("value", {})
    return {
        "agreement": "2005",
        "max_share": {"0_to_6_years": 0.25, "7_to_9_years": 0.30, "10_plus_years": 0.35},
        "max_floor": {"0_to_6_years": 9_000_000, "7_to_9_years": 11_000_000, "10_plus_years": 14_000_000},
        "max_fixed": fixed,
        "raise_bird": raises["larry_bird_pct"]["value"] / 100,
        "raise_other": raises["non_bird_pct"]["value"] / 100,
        "max_years_bird": length["bird_rights_re_signing_max_years"]["value"],
        "max_years_other": length["other_free_agents_max_years"]["value"],
        "rookie_guaranteed_years": 2, "rookie_option_years": (3, 4),
        "trade_match": 1.25, "trade_plus": 100_000,
    }


def tier(service):
    s = service or 0
    return "0_to_6_years" if s <= 6 else "7_to_9_years" if s <= 9 else "10_plus_years"


def maximum(service, cap, season, root=ROOT):
    """The maximum first-year salary for a player's years of service: the season's fixed figure where the agreement sets
    one, else the greater of the floor and the share of the cap (the 105% of prior salary rule is the caller's)."""
    t = terms(season, root)
    k = tier(service)
    if t["max_fixed"].get(k):
        return int(t["max_fixed"][k])
    return max(int(t["max_floor"].get(k, 0)), int(round(cap * t["max_share"][k])))


def raise_share(route, season, root=ROOT):
    """The annual raise for a new contract by its route (minimum and qualifying offer: none)."""
    if route in ("minimum", "qualifying_offer"):
        return 0.0
    t = terms(season, root)
    return t["raise_bird"] if route in ("bird", "early_bird") else t["raise_other"]


def max_years(route, season, root=ROOT):
    t = terms(season, root)
    return t["max_years_bird"] if route == "bird" else t["max_years_other"]
