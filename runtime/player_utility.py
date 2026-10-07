"""A free agent's view of one contract at one club: factor scores, weights and the answer odds.

Model `utility-2003.2` (docs/front_office_design.md 4.3a). It adapts a twelve-factor negotiation
framework the user supplied, keeping only the factors this repository has dated evidence for:

    money        guaranteed salary against what he asks for the years he wants
    security     seasons offered against seasons wanted, last season guaranteed or not
    net_income   state or provincial income tax tier where the club plays
    role         minutes he would get at the club (Miami: its depth-chart promise; elsewhere: his value
                 rank in his position group on the club's roster on the date) against his 2002-03 minutes
    contention   the club's projected wins with him on its roster on the date (runtime/club_strength.py),
                 so every signing changes what the next free agent sees
    loyalty      the club he played for in 2002-03
    market       the club's media-market tier

Factors without dated evidence are excluded and named on every packet, never filled with a guess:
scheme fit (Miami's staff has not set a scheme), organisational stability, coach relationship,
locker-room ties, medical staff and family. Era rules are not a preference: the contract desk
refuses an illegal offer before any answer is drawn.

A player scores every factor 0-100 for Miami's offer and for his best alternative. Weights come from
his career stage (age) tilted by his drawn trait (money, fame, loyalty, winning). The gap between the
two utilities sets the odds of accept, counter and reject through an ordered logistic, and the engine
draws the answer. A role far below an established starter's is a dealbreaker: he walks without a draw.
Every constant is a named judgement constant.
"""
from __future__ import annotations

import math

MODEL = "utility-2003.2"

# Career stage (age at the date): category weights (the supplied framework's table; health is excluded
# because no medical evidence exists, and the rest is renormalised).
# The user asked that the rosters a player leaves and joins weigh heavily, so contention carries more
# than the supplied table at the early and prime stages, taken from the financial share.
STAGES = ((24, "early", {"financial": 0.35, "role": 0.30, "contention": 0.15, "personal": 0.15}),
          (29, "prime", {"financial": 0.30, "role": 0.25, "contention": 0.25, "personal": 0.15}),
          (99, "veteran", {"financial": 0.20, "role": 0.15, "contention": 0.35, "personal": 0.25}))
CATEGORY = {"money": ("financial", 0.65), "security": ("financial", 0.20), "net_income": ("financial", 0.15),
            "role": ("role", 1.0), "contention": ("contention", 1.0),
            "loyalty": ("personal", 0.60), "market": ("personal", 0.40)}
# The drawn trait tilts the stage weights (judgement): multiplier per factor before renormalising.
TRAIT_TILT = {"money": {"money": 1.6, "security": 1.6, "net_income": 1.6},
              "winning": {"contention": 1.6},
              "fame": {"role": 1.3, "market": 2.0},
              "loyalty": {"loyalty": 2.5}}
EXCLUDED = ("scheme fit: Miami's staff has not set an offensive or defensive scheme (team_config.json)",
            "organisational stability, coach relationship and locker-room ties: no dated evidence",
            "medical and training staff: no dated evidence",
            "family and personal circumstances: no sourced evidence; never invented for a real person")

# Income tax tiers in 2003 (judgement tiers from each jurisdiction's general rate level, not a payroll
# calculation): no state wage tax in Florida, Texas, Washington and Tennessee; the highest top rates in
# California, New York City and Ontario (with Canadian federal tax). Everyone else is standard.
NO_TAX = {"Miami Heat", "Orlando Magic", "Dallas Mavericks", "Houston Rockets", "San Antonio Spurs",
          "Seattle SuperSonics", "Memphis Grizzlies"}
HIGH_TAX = {"Los Angeles Lakers", "Los Angeles Clippers", "Golden State Warriors", "Sacramento Kings",
            "New York Knicks", "Toronto Raptors"}
TAX_SCORE = {"none": 100, "standard": 60, "high": 30}
# Media-market tiers (judgement): the three largest markets, and the smallest.
LARGE_MARKETS = {"New York Knicks", "Los Angeles Lakers", "Los Angeles Clippers", "Chicago Bulls"}
SMALL_MARKETS = {"Memphis Grizzlies", "Milwaukee Bucks", "Utah Jazz", "San Antonio Spurs", "New Orleans Hornets"}
MARKET_SCORE = {"large": 100, "mid": 60, "small": 35}

MONEY_CENTER, MONEY_SPAN = 60, 100       # money score at the ask, and points per unit of log(guaranteed / ask total)
ASK_RAISE = 0.10                          # the ask's yearly raise when pricing the seasons he wants (1999 non-Bird raise;
                                          # a later summer passes its agreement's rate as player["ask_raise"], see ask_raise)
ROLE_FLOOR_MINUTES = 12                   # a player with almost no 2002-03 minutes compares against this
DEFAULT_MINUTES = 24                      # no 2002-03 minutes recorded
DEALBREAKER = {"minutes": 30, "start_share": 0.75, "ages": (25, 31), "offered_below": 20}
# Ordered logistic on the utility gap (Miami minus alternative, points): accept above ACCEPT_AT,
# reject below REJECT_AT, counter between; SCALE sets how much chance blurs the bands.
ACCEPT_AT, REJECT_AT, SCALE = 4.0, -10.0, 4.0
ACCEPT_LIMITS = (0.02, 0.95)


def tax_tier(club):
    return "none" if club in NO_TAX else "high" if club in HIGH_TAX else "standard"


def market_tier(club):
    return "large" if club in LARGE_MARKETS else "small" if club in SMALL_MARKETS else "mid"


def stage(age):
    return next((name, weights) for limit, name, weights in STAGES if (age or 27) <= limit)


def weights(age, trait):
    """Factor weights summing to 1: the stage's category weights split over factors, tilted by the trait."""
    _, cats = stage(age)
    raw = {f: cats[c] * share * TRAIT_TILT.get(trait, {}).get(f, 1.0) for f, (c, share) in CATEGORY.items()}
    total = sum(raw.values())
    return {f: round(v / total, 4) for f, v in raw.items()}


def ask_raise(season, root=None):
    """The yearly raise a player prices his ask with in a season: the agreement's non-Bird raise
    (`runtime/agreement.py`: 10% under the 1999 agreement, 8% from 2005-06)."""
    from . import agreement
    return agreement.raise_share("other", season, *([root] if root else []))


def clip(x, lo=0.0, hi=100.0):
    return max(lo, min(hi, x))


def scores(terms, situation, player):
    """0-100 score per factor for one contract at one club.

    terms: guaranteed, years, last_year_guaranteed (optional).
    situation: club, role_minutes, strength (wins).
    player: ask (first-year asking salary), years_wanted, prior_minutes, prior_club.
    """
    wanted = max(1, player["years_wanted"])
    rate = player.get("ask_raise", ASK_RAISE)
    ask_total = sum(player["ask"] * (1 + rate * i) for i in range(wanted))
    money = clip(MONEY_CENTER + MONEY_SPAN * math.log(max(terms["guaranteed"], 1) / max(ask_total, 1)))
    years = min(terms["years"], wanted) - (0.5 if terms.get("last_year_guaranteed") is False else 0)
    security = clip(100 * years / wanted)
    baseline = max(ROLE_FLOOR_MINUTES, player.get("prior_minutes") or DEFAULT_MINUTES)
    role = clip(100 * situation.get("role_minutes", DEFAULT_MINUTES) / baseline)
    contention = clip(100 * (situation.get("strength", 41) - 20) / 40)
    club = situation.get("club")
    return {"money": round(money, 1), "security": round(security, 1),
            "net_income": TAX_SCORE[tax_tier(club)], "role": round(role, 1), "contention": round(contention, 1),
            "loyalty": 100 if club and club == player.get("prior_club") else 50,
            "market": MARKET_SCORE[market_tier(club)]}


def utility(score, weight):
    return round(sum(weight[f] * score[f] for f in weight), 2)


def dealbreaker(situation, player):
    """An established starter in his prime offered a bench role walks (the framework's role disrespect)."""
    d = DEALBREAKER
    age = player.get("age") or 0
    if ((player.get("prior_minutes") or 0) >= d["minutes"] and (player.get("start_share") or 0) >= d["start_share"]
            and d["ages"][0] <= age <= d["ages"][1] and situation.get("role_minutes", 99) < d["offered_below"]):
        return (f"role disrespect: {player.get('prior_minutes'):.1f} minutes and {player['start_share']:.0%} starts in 2002-03 "
                f"at age {age}, offered about {situation['role_minutes']} minutes")
    return None


def odds(gap, round_no, patience):
    """Accept, counter and reject odds from the utility gap; no counter after the last round he hears."""
    def sigma(x):
        return 1 / (1 + math.exp(-x))
    accept = clip(sigma((gap - ACCEPT_AT) / SCALE), *ACCEPT_LIMITS)
    reject = sigma((REJECT_AT - gap) / SCALE)
    counter = max(0.0, 1 - accept - reject)
    if round_no >= patience:
        reject, counter = reject + counter, 0.0
    accept = round(accept, 3)
    counter = round(counter, 3)
    reject = round(1 - accept - counter, 3)
    return {k: v for k, v in (("accept", accept), ("counter", counter), ("reject", reject)) if v > 0}


def counter_focus(miami, alternative, weight):
    """The factor where Miami's offer loses most weighted ground to the alternative: what the agent pushes on."""
    deficits = {f: weight[f] * (alternative[f] - miami[f]) for f in weight}
    factor = max(deficits, key=deficits.get)
    return factor, round(deficits[factor], 2)
