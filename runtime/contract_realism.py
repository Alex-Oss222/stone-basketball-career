"""Contract length and role pricing for summer markets after 2004 (the user's request, October 2026: clubs sign
realistic, sensible contracts).

The 2004 market (`runtime/free_agency_2004.py`) priced on production alone and wanted years by age alone (5 at most).
Its answers were engine draws, so it stands as decided. From the 2005 market on, two corrections apply to every
player alike:

Length. A player's wanted years start from his age at signing and move with his standing in the market: a club
commits longer to a player in the top fifth of the season's free agents by value and shorter to one in the bottom
half. The 1999 agreement caps the term by route (`library/2003/league/nba_1999_cba_rules.json`): seven seasons with
Bird rights, six with Early Bird (at least two) or Non-Bird rights, and six for another club's player (cap room or
the mid-level: the file records no separate mid-level term, so the general limit applies). A minimum contract is one
season, or two (the agreement's most) for a player with less than two seasons of service.

  age at signing   <=25   26-28   29-30   31-32   33-34   35+
  base years         6      5       4       3       2      1
  top fifth of the market by value: +1; bottom half: -1; never below 1.

Role. Box-score production undervalues players whose coaches trust them with minutes for what the box score misses
(defenders, screeners). A player's minutes per game in the prior season raise his production value toward the value
of a player who earns those minutes: value + ROLE_WEIGHT x max(0, minutes_value(mpg) - value), where minutes_value is
the league's median production at that minutes level (judgement: ROLE_WEIGHT 0.35). It never lowers a value.
"""
from __future__ import annotations

ROUTE_MAX_YEARS = {"bird": 7, "early_bird": 6, "non_bird": 6, "cap_room": 6, "mid_level": 6, "minimum": 2,
                   "rookie_scale": 3, "qualifying_offer": 1}
ROUTE_MIN_YEARS = {"early_bird": 2}
BASE_YEARS = ((25, 6), (28, 5), (30, 4), (32, 3), (34, 2), (199, 1))
TOP_SHARE, BOTTOM_SHARE = 0.20, 0.50
ROLE_WEIGHT = 0.35


def contract_years(age, value_rank, route, service=None):
    """Years a player and club settle on: age base, market standing, the agreement's route cap.

    `value_rank` is his place among the season's free agents by value, 0.0 the best and 1.0 the last."""
    if route == "minimum":
        return 2 if (service is not None and service < 2) else 1
    base = next(y for limit, y in BASE_YEARS if (age if age is not None else 27) <= limit)
    if value_rank is not None:
        if value_rank <= TOP_SHARE:
            base += 1
        elif value_rank > BOTTOM_SHARE:
            base -= 1
    return max(ROUTE_MIN_YEARS.get(route, 1), min(base, ROUTE_MAX_YEARS.get(route, 6)))


def minutes_value(mpg, table):
    """The league's median production value at a minutes level: `table` is [(mpg, value)] sorted by mpg (the prior
    season's players with at least 20 games); the median of the players within two minutes either side."""
    near = sorted(v for m, v in table if abs(m - mpg) <= 2.0)
    if not near:
        return None
    mid = len(near) // 2
    return near[mid] if len(near) % 2 else (near[mid - 1] + near[mid]) / 2


def role_value(value, mpg, table):
    """Production value raised toward what his minutes earn (never lowered)."""
    if value is None or mpg is None:
        return value
    earned = minutes_value(mpg, table)
    if earned is None or earned <= value:
        return value
    return value + ROLE_WEIGHT * (earned - value)
