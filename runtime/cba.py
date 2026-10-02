"""1999 collective bargaining agreement: free-agent rights, cap holds and qualifying offers.

Rules come from `library/2003/league/nba_1999_cba_rules.json`, extracted from Larry
Coon's 1999 Salary Cap FAQ (question numbers recorded per rule). Every result
carries the rule it used and any open question, so an unverified input is never
silently treated as settled.
"""
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RULES_PATH = Path("library/2003/league/nba_1999_cba_rules.json")


def rules(root=ROOT):
    return json.loads((Path(root) / RULES_PATH).read_text(encoding="utf-8"))


def bird_status(seasons_with_team):
    """Seasons with the club since he last joined it, counted without a waiver or a free-agent change."""
    if seasons_with_team >= 3:
        return "larry_bird"
    if seasons_with_team == 2:
        return "early_bird"
    return "non_bird"


def first_season_with_team(join_date):
    """A player who joins from May onward (draft night, summer signings) first plays that autumn."""
    d = date.fromisoformat(join_date)
    return d.year if d.month >= 5 else d.year - 1


def bird_seasons(join_date, last_season="2002-03"):
    first = first_season_with_team(join_date)
    return int(last_season[:4]) - first + 1


def cap_hold(prior_salary, status, *, rookie_scale, above_average, max_salary, cba):
    """Free-agent amount (FAQ Q28). Returns (amount, percent, notes)."""
    holds = cba["cap_holds_percent"]
    if status == "larry_bird":
        key = ("bird_rookie_scale" if rookie_scale else "bird") + ("_above_average" if above_average else "_below_average")
        percent = holds[key]
    else:
        percent = holds[status]
    amount = round(prior_salary * percent / 100)
    notes = []
    if amount > max_salary:
        amount, notes = max_salary, [f"capped at the player's maximum salary ({max_salary})"]
    return amount, percent, notes


def qualifying_offer(prior_salary, minimum_salary, cba):
    """Non-rookie-scale qualifying offer (FAQ Q34): greater of 125% of prior salary or minimum + $150,000."""
    rule = cba["qualifying_offer"]
    if minimum_salary is None:
        return None, "unresolved: minimum salary for the player's years of service is not recorded"
    by_salary = round(prior_salary * rule["percent_of_previous_salary"] / 100)
    by_minimum = minimum_salary + rule["minimum_salary_plus"]
    return max(by_salary, by_minimum), ("125% of previous salary" if by_salary >= by_minimum else "minimum salary plus $150,000")


def rfa_eligible(entered_season, nba_seasons, cba):
    """Veteran restricted free agency (FAQ Q34): entered 1998-99 or later with three or fewer seasons."""
    rule = cba["restricted_free_agency"]["veterans"]
    return int(entered_season[:4]) >= int(rule["entered_from_season"][:4]) and nba_seasons <= rule["max_seasons"]
