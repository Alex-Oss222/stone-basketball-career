"""Wade's rookie-scale contract and its negotiation log (roadmap item 5).

1999 agreement (FAQ Q38, Q41): first-round picks sign for 80-120% of the scale
for their pick; three seasons plus a team option for a fourth, exercised by
October 31 after the second season (October 31, 2005 for a 2003 draftee); the
scale fixes the raises. Until he signs, an
unsigned first-round pick counts at 100% of scale.

The log records every offer, counter, request and answer with its date and
party. Wade's entries are the user's decisions; Miami's are the AI/GM's.
Nothing in the log changes the cap sheet until a signing entry is closed.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARTIES = {"miami", "wade"}
ACTIONS = {"offer", "counter", "accept", "decline", "request", "answer", "sign"}


def scale_row(pick, root=ROOT):
    rules = json.loads((Path(root) / "library/2003/league/nba_2003_04_cap_rules.json").read_text())
    return next(r for r in rules["rookie_scale"]["picks"] if r["pick"] == pick), rules["rookie_scale"]


def rookie_terms(pick, percent, root=ROOT):
    """Salary schedule for a rookie-scale contract at `percent` of scale (80-120)."""
    row, scale = scale_row(pick, root)
    low, high = scale["allowed_signing_percent_of_scale"]["min"], scale["allowed_signing_percent_of_scale"]["max"]
    if not low <= percent <= high:
        raise ValueError(f"rookie-scale signing must be {low}-{high}% of scale")
    years = [round(row[f"year_{i}"] * percent / 100) for i in (1, 2, 3)]
    for a, b in zip(years, years[1:]):
        if b > a * 1.10:
            raise ValueError("raise exceeds the 10% rookie-scale limit")
    option = round(years[2] * (1 + row["fourth_year_option_increase_percent"] / 100))
    return {"pick": pick, "percent_of_scale": percent,
            "schedule": {"2003-04": years[0], "2004-05": years[1], "2005-06": years[2], "2006-07": option},
            "amount_kind": {"2003-04": "contract_salary", "2004-05": "contract_salary",
                            "2005-06": "contract_salary", "2006-07": "team_option"},
            "fourth_year_option_deadline": "2005-10-31",   # October 31 after his second season (FAQ Q38)
            "qualifying_offer_increase_percent_after_fourth_year": row["qualifying_offer_increase_percent"]}


def log_errors(log, root=ROOT):
    errors, last_date, signed = [], "", False
    for i, entry in enumerate(log.get("entries", [])):
        where = f"entry {i + 1}"
        if entry.get("party") not in PARTIES or entry.get("action") not in ACTIONS:
            errors.append(f"{where}: unknown party or action")
        if not isinstance(entry.get("date"), str) or entry["date"] < last_date:
            errors.append(f"{where}: dates must not go backwards")
        last_date = entry.get("date", last_date)
        if signed:
            errors.append(f"{where}: nothing may follow the signing")
        terms = entry.get("terms")
        if terms is not None:
            errors.extend(f"{where}: {e}" for e in terms_errors_any(terms, root))
        if entry.get("action") == "sign":
            signed = True
            if terms is None:
                errors.append(f"{where}: a signing needs terms")
    return errors


# -- layered rookie contract (Wade's counter framework, user premise) ----------------------------------------
# 1999 rules as recorded in library/2003/league/nba_1999_cba_rules.json and docs/research/cba_1999_rules.md:
# at least 80% of scale must be Current Cash Compensation (protected salary, no incentives); the total may not
# exceed 120%; Unlikely Bonuses may not exceed 25% of Regular Salary; incentives for physical condition and for
# an offseason skill-and-conditioning program count as Salary (included); no signing bonus on a rookie-scale deal;
# the fourth-year option is the third-year Salary raised by the pick's percentage; a promised role is not a
# permitted amendment of the Uniform Player Contract.
PROTECTED_MIN_PERCENT, TOTAL_MAX_PERCENT = 80, 120
UNLIKELY_MAX_SHARE_OF_REGULAR_SALARY = 0.25
INCLUDED_KINDS = ("conditioning_program", "physical_condition", "academic")   # incentive kinds the 1999 rules count as Salary
SEASONS = ("2003-04", "2004-05", "2005-06")


def layered_terms(pick, protected_percent, incentives, root=ROOT):
    """A rookie-scale contract as protected cash plus incentives, each a percent of scale per season.

    `incentives`: list of {id, label, kind (included kind or "performance"), percent, benchmarks {season: text},
    classification ("included" for included kinds; "likely" or "unlikely" for performance)}. The counted Salary of a
    season is protected cash plus included incentives plus performance bonuses classified likely; the fourth-year
    option is the third season's counted Salary raised by the pick's percentage (Article XI carries the third year's
    terms into the option year, except the raise).
    """
    row, scale = scale_row(pick, root)
    base = {s: row[f"year_{i}"] for i, s in enumerate(SEASONS, start=1)}
    amounts = lambda pct: {s: round(base[s] * pct / 100) for s in SEASONS}
    protected = amounts(protected_percent)
    layers = []
    for inc in incentives:
        kind = inc["kind"]
        classification = "included" if kind in INCLUDED_KINDS else inc.get("classification", "unlikely")
        layers.append({"id": inc["id"], "label": inc["label"], "kind": kind, "percent": inc["percent"],
                       "classification": classification,
                       "classified_by": ("1999 rules: physical-condition, academic and designated program incentives are Salary"
                                         if classification == "included" else
                                         "league determination (NBA/NBPA; an expert if they disagree): a rookie's performance bonus is "
                                         "Unlikely unless the prior season's record would have earned it"),
                       "benchmarks": dict(inc.get("benchmarks", {})), "amounts": amounts(inc["percent"])})
    counted = {s: protected[s] + sum(l["amounts"][s] for l in layers if l["classification"] in ("included", "likely")) for s in SEASONS}
    maximum = {s: protected[s] + sum(l["amounts"][s] for l in layers) for s in SEASONS}
    option = round(counted["2005-06"] * (1 + row["fourth_year_option_increase_percent"] / 100))
    return {"pick": pick, "structure": "layered", "protected_percent": protected_percent,
            "total_percent": protected_percent + sum(l["percent"] for l in layers),
            "protected_schedule": protected, "incentives": layers, "maximum_schedule": maximum,
            "schedule": {**counted, "2006-07": option},
            "amount_kind": {"2003-04": "contract_salary", "2004-05": "contract_salary", "2005-06": "contract_salary", "2006-07": "team_option"},
            "signing_bonus": 0, "promised_role_contractual": False,
            "fourth_year_option_deadline": "2005-10-31",
            "fourth_year_option_basis": f"third-season counted Salary raised {row['fourth_year_option_increase_percent']}% (pick {pick})",
            "qualifying_offer_increase_percent_after_fourth_year": row["qualifying_offer_increase_percent"]}


def layered_errors(terms, root=ROOT):
    """Why a layered rookie contract breaks the 1999 rules, with the rule named."""
    errors = []
    try:
        expected = layered_terms(terms["pick"], terms["protected_percent"],
                                 [{k: l[k] for k in ("id", "label", "kind", "percent", "benchmarks", "classification") if k in l} for l in terms["incentives"]], root)
    except (KeyError, TypeError, ValueError, StopIteration) as exc:
        return [f"layered terms cannot be rebuilt: {exc}"]
    if {k: v for k, v in terms.items() if k != "note"} != expected:
        errors.append("layered terms do not match their percentages and the scale")
    if terms["protected_percent"] < PROTECTED_MIN_PERCENT:
        errors.append(f"protected Current Cash Compensation under {PROTECTED_MIN_PERCENT}% of scale (1999 rookie-scale rule)")
    if terms["total_percent"] > TOTAL_MAX_PERCENT:
        errors.append(f"maximum compensation over {TOTAL_MAX_PERCENT}% of scale (1999 rookie-scale rule)")
    unlikely = sum(l["percent"] for l in terms["incentives"] if l["classification"] == "unlikely")
    if unlikely > terms["protected_percent"] * UNLIKELY_MAX_SHARE_OF_REGULAR_SALARY + 1e-9:
        errors.append(f"Unlikely Bonuses exceed {UNLIKELY_MAX_SHARE_OF_REGULAR_SALARY:.0%} of Regular Salary (1999 rules)")
    if terms.get("signing_bonus"):
        errors.append("no signing bonus on a rookie-scale contract (1999 rules)")
    if terms.get("promised_role_contractual"):
        errors.append("a promised role is not a permitted amendment of the Uniform Player Contract")
    for l in terms["incentives"]:
        if l["kind"] == "performance" and any(not b for b in l["benchmarks"].values()):
            errors.append(f"{l['id']}: a performance bonus needs a positive, numerical or recognized-honor benchmark for each season")
    return errors


def terms_errors_any(terms, root=ROOT):
    """Errors for either shape of rookie terms: a plain percent of scale, or the layered structure."""
    if isinstance(terms, dict) and terms.get("structure") == "layered":
        return layered_errors(terms, root)
    try:
        expected = rookie_terms(terms["pick"], terms["percent_of_scale"], root)
    except (KeyError, TypeError, ValueError, StopIteration) as exc:
        return [str(exc)]
    return [] if terms == expected else ["terms do not match the rookie scale"]
