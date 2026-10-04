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
MINIMUM_SCALE_PATH = Path("library/2003/league/nba_1999_cba_minimum_salary_scale.json")
MINIMUM_CAP_SERVICE = 5        # FAQ Q9: a one-year minimum for a 5+ year veteran counts the 4-year minimum


def rules(root=ROOT):
    return json.loads((Path(root) / RULES_PATH).read_text(encoding="utf-8"))


def minimum_scale(root=ROOT):
    return json.loads((Path(root) / MINIMUM_SCALE_PATH).read_text(encoding="utf-8"))


def minimum_salary(years_of_service, season="2003-04", root=ROOT):
    """The 1999 CBA minimum salary for a player's years of NBA service before the season (FAQ Q9)."""
    if years_of_service is None:
        raise ValueError("years of service are not recorded; the minimum salary cannot be set")
    row = minimum_scale(root)["seasons"][season]
    return row["10_plus"] if years_of_service >= 10 else row[str(max(0, int(years_of_service)))]


def minimum_cap_amount(years_of_service, salary, seasons, season="2003-04", root=ROOT):
    """Team salary counted for a contract: a one-year minimum for a 5+ year veteran counts the
    4-year minimum (the league reimburses the rest); every other contract counts its salary."""
    if (years_of_service is not None and years_of_service >= MINIMUM_CAP_SERVICE and seasons == 1
            and salary == minimum_salary(years_of_service, season, root)):
        return minimum_scale(root)["cap_treatment"]["amount_counted"][season]
    return salary


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


# -- contract legality (docs/front_office_design.md, section 6; rules file, exceptions and maximum_salary) --

MAX_SIGNING_BONUS_SHARE = 0.20     # of total salary (reported for 1999 offer sheets; docs/research/cba_1999_rules.md)


def terms_errors(terms, *, route, years_of_service, prior_salary, cap_rules, cba, restricted_offer_sheet=False):
    """Why a proposed contract is illegal under the 1999 rules, or [] when it passes.

    terms: {"schedule": [first-year salary, ...], "guaranteed": int, "signing_bonus": int (optional)}.
    route: "room", "bird", "early_bird", "non_bird", "mid_level", "million", "minimum", "rookie_scale", "sign_and_trade"
    (the last is a contract signed by the incumbent with full Bird rights to be traded at once; the desk checks the
    rights class and the clubs' cap positions, this function the contract's shape only).
    """
    errors = []
    schedule = terms.get("schedule") or []
    if not schedule or any(not isinstance(s, int) or s <= 0 for s in schedule):
        return ["a contract needs a positive integer salary for every season"]
    years, first = len(schedule), schedule[0]
    tier = ("0_to_6_years" if (years_of_service or 0) <= 6 else "7_to_9_years" if years_of_service <= 9 else "10_plus_years")
    maximum = cap_rules["maximum_salary"][tier]
    if prior_salary:
        maximum = max(maximum, round(prior_salary * 1.05))
    minimum = minimum_salary(years_of_service or 0)
    if first > maximum:
        errors.append(f"first-year salary {first:,} exceeds the maximum {maximum:,} for {years_of_service} years of service")
    if first < minimum:
        errors.append(f"first-year salary {first:,} is under the minimum {minimum:,}")
    bird = route in ("bird", "early_bird", "sign_and_trade")
    max_years = (cba["exceptions"]["larry_bird"]["max_years"] if route in ("bird", "sign_and_trade")
                 else cba["exceptions"]["early_bird"]["max_years"] if route == "early_bird" else cba["exceptions"]["non_bird"]["max_years"])
    if route == "minimum":
        max_years = cba["exceptions"]["minimum"]["max_years"]
    if years > max_years:
        errors.append(f"{years} seasons exceeds the {max_years} allowed by the {route} route")
    if route == "sign_and_trade":
        # A sign-and-trade contract is signed with full Bird rights (Bird raises and length) and must run at
        # least three non-option seasons; no first-season guarantee is required under the 1999 rules (inferred).
        rule = cba["trades"]["sign_and_trade"]
        non_option = terms.get("non_option_seasons", years)
        if non_option < rule["min_non_option_seasons"]:
            errors.append(f"a sign-and-trade contract needs at least three non-option seasons ({rule['min_non_option_seasons_status']})")
    raise_limit = (cba["exceptions"]["larry_bird"]["raise_percent"] if bird else cba["exceptions"]["non_bird"]["raise_percent"]) / 100
    for i in range(1, years):
        if schedule[i] > schedule[i - 1] + first * raise_limit + 1 or schedule[i] < schedule[i - 1] - first * raise_limit - 1:
            errors.append(f"season {i + 1} changes salary by more than {raise_limit:.1%} of the first-year salary")
            break
    if route == "mid_level" and first > cap_rules["exceptions"]["mid_level"]:
        errors.append(f"mid-level exception allows at most {cap_rules['exceptions']['mid_level']:,} in the first season")
    if route == "million" and (first > cap_rules["exceptions"]["biennial"] or years > 2):
        errors.append("the $1 million exception allows at most its amount for up to two seasons")
    if route == "early_bird":
        floor = max(round((prior_salary or 0) * 1.75), cap_rules["exceptions"]["mid_level"])
        if first > floor and first > maximum:
            errors.append("early bird salary is limited to the greater of 175% of the prior salary and the average salary")
    if route == "non_bird":
        limit = max(round((prior_salary or 0) * 1.2), round(minimum * 1.2))
        if first > limit:
            errors.append(f"non-bird salary is limited to {limit:,} (120% of the prior salary or of the minimum)")
    guaranteed = terms.get("guaranteed", sum(schedule))
    if not 0 <= guaranteed <= sum(schedule):
        errors.append("guaranteed money must be between zero and the scheduled total")
    bonus = terms.get("signing_bonus") or 0
    if bonus > MAX_SIGNING_BONUS_SHARE * sum(schedule):
        errors.append(f"signing bonus exceeds {MAX_SIGNING_BONUS_SHARE:.0%} of total salary")
    if restricted_offer_sheet and years < cba["restricted_free_agency"]["offer_sheet_min_seasons"]:
        errors.append("an offer sheet to a restricted free agent needs at least three seasons")
    return errors
