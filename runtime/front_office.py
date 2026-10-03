"""Miami's simulated front office: June 30, 2003 decisions (roadmap item 4).

The front office sees only evidence available on its date: 2002-03 statistics
(veteran ratings), contracts, the 1999 rules and Wade's logged requests. It
never reads real-career trajectories or real rosters (AGENTS.md).

Rules are provisional judgement constants, documented here and in
docs/front_office.md:

* Team option at a near-minimum salary: exercise if the player logged at least
  400 minutes in 2002-03 or is 24 or younger; otherwise decline.
* Qualifying offer to a restricted-eligible player: tender if he logged at
  least 500 minutes or is 24 or younger.
* A simulated player's player option: he opts in with a probability that rises
  as the option salary exceeds his estimated market value; the engine draws it.
* Renouncing free agents to create cap room is a free-agency decision (item 6),
  not a June 30 one.

Wade's requests (AGENTS.md, "Wade's voice"): a request that opposes a
rule-based decision becomes an engine-drawn decision when the rule's margin is
small. The chance it changes the outcome is Wade's standing weight times how
close the call was.
"""
from datetime import date

OPTION_MINUTES, OPTION_MAX_AGE = 400, 24
QO_MINUTES, QO_MAX_AGE = 500, 24
from .standing import STANDING_WEIGHT   # noqa: E402  (one object, computed standing: runtime/standing.py)


def age_on(birth_date, on):
    b, d = date.fromisoformat(birth_date), date.fromisoformat(on)
    return d.year - b.year - ((d.month, d.day) < (b.month, b.day))


def rule_margin(minutes, minutes_line, age, age_line):
    """How clearly the rule decided: 1 = far from the deciding line, 0 = right on it."""
    by_minutes = min(1.0, abs(minutes - minutes_line) / minutes_line)
    by_age = min(1.0, abs(age - age_line) / 4)
    met = [d for d, ok in ((by_minutes, minutes >= minutes_line), (by_age, age <= age_line)) if ok]
    # Passed: the strongest satisfied criterion decides. Failed: the nearer miss decides.
    return max(met) if met else min(by_minutes, by_age)


def team_option(player, minutes, age):
    keep = minutes >= OPTION_MINUTES or age <= OPTION_MAX_AGE
    return {"player": player, "decision": "exercise" if keep else "decline",
            "margin": rule_margin(minutes, OPTION_MINUTES, age, OPTION_MAX_AGE),
            "reason": f"{minutes} minutes in 2002-03, age {age}: rule is {OPTION_MINUTES}+ minutes or age {OPTION_MAX_AGE} or younger"}


def qualifying_offer(player, minutes, age, amount):
    tender = minutes >= QO_MINUTES or age <= QO_MAX_AGE
    return {"player": player, "decision": "tender" if tender else "do_not_tender", "amount": amount,
            "margin": rule_margin(minutes, QO_MINUTES, age, QO_MAX_AGE),
            "reason": f"{minutes} minutes in 2002-03, age {age}: rule is {QO_MINUTES}+ minutes or age {QO_MAX_AGE} or younger"}


def estimated_market_value(minutes, minimum, mid_level):
    """Provisional: the minimum plus a share of the mid-level proportional to 2002-03 minutes (capped at 2,000)."""
    return minimum + (mid_level - minimum) * min(1.0, minutes / 2000)


def player_option_probability(option_salary, market_value):
    gap = max(-1.0, min(1.0, (option_salary - market_value) / option_salary))
    return round(min(0.95, max(0.05, 0.5 + 0.4 * gap)), 3)


def request_override(rule_decision, requested, margin, standing):
    """Probability that Wade's opposing request changes a rule-based decision (0 when he agrees)."""
    if requested is None or requested == rule_decision:
        return 0.0
    return round(STANDING_WEIGHT[standing] * (1 - margin), 3)


def rookie_offer(pick):
    """Miami's opening rookie-scale offer: 120% of scale, the usual practice for first-round picks
    under the 1999 agreement. Timing: Miami signs him once its July free-agency plans are set,
    because until he signs he counts at 100% of scale rather than the higher signed salary."""
    from .rookie_contract import rookie_terms
    return {"terms": rookie_terms(pick, 120),
            "timing": "after Miami's free-agency signings, once the 2003-04 cap is published (July 15, 2003)",
            "reason": "120% is the customary first-round signing level; signing later keeps the lower 100% hold during free agency"}
