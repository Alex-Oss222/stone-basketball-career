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
            try:
                expected = rookie_terms(terms["pick"], terms["percent_of_scale"], root)
                if terms != expected:
                    errors.append(f"{where}: terms do not match the rookie scale")
            except (KeyError, ValueError, StopIteration) as exc:
                errors.append(f"{where}: {exc}")
        if entry.get("action") == "sign":
            signed = True
            if terms is None:
                errors.append(f"{where}: a signing needs terms")
    return errors
