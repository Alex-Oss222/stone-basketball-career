"""Read-only player status and first-year market estimate for milestone screens.

Scenario selection never establishes live rights. A price estimate never
establishes a club's spending authority or a legal contract. See
docs/player_market_profile.md for the input contract and model limitations.
"""
from datetime import date
import json
import math
from pathlib import Path
import statistics

from .valuation import age_on, production_value

ROOT = Path(__file__).resolve().parents[1]
MINIMUMS = "library/2003/league/nba_1999_cba_minimum_salary_scale.json"
CAP_RULES = "library/2003/league/nba_2003_04_cap_rules.json"
STATS = "library/2003/league/nba_2002_03_player_stats.json"
CONTRACTS = "library/2003/league/nba_2003_contracts.json"
BASELINE = "library/2003/league/nba_2003_end_of_season.json"
MIN_COMPARABLES = 5
MIN_COMPARABLE_MINUTES = 500
MIN_LOG_BAND = math.log(1.25)
TOTAL_FIELDS = ("games", "minutes", "points", "offensive_rebounds",
                "defensive_rebounds", "assists", "steals", "blocks",
                "field_goals_attempted", "field_goals_made",
                "free_throws_attempted", "free_throws_made", "turnovers")


def _day(value):
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError("dates must use YYYY-MM-DD")
    return date.fromisoformat(value)


def _available(evidence, on):
    """Evidence is caller-authenticated; this only checks date and reference shape."""
    if (not isinstance(evidence, dict) or not isinstance(evidence.get("source_ref"), str)
            or not evidence["source_ref"].strip()):
        return False
    try:
        return _day(evidence.get("as_of")) <= _day(on)
    except (TypeError, ValueError):
        return False


def _positive(value):
    return type(value) in (int, float) and math.isfinite(value) and value > 0


def _totals_ok(totals):
    if not isinstance(totals, dict):
        return False
    if any(type(totals.get(k)) not in (int, float) or
           not math.isfinite(totals[k]) or totals[k] < 0 for k in TOTAL_FIELDS):
        return False
    return (totals["games"] > 0 and totals["minutes"] > 0 and
            totals["field_goals_made"] <= totals["field_goals_attempted"] and
            totals["free_throws_made"] <= totals["free_throws_attempted"])


def _age_ok(age):
    return age is None or (type(age) is int and 0 <= age <= 99)


def select_status(*, on, mode="live", selected_status=None, control=None):
    """Derive status from an evidenced control snapshot; optionally overlay a scenario.

    RFA eligibility alone is insufficient. QO must be timely, valid, and preserve
    matching rights. Withdrawal and no-tender outcomes need final verified facts.
    """
    _day(on)
    if mode not in {"live", "scenario"}:
        raise ValueError("mode must be live or scenario")
    if selected_status not in {None, "UFA", "RFA"}:
        raise ValueError("scenario selection must be UFA or RFA")
    if mode == "live" and selected_status is not None:
        raise ValueError("live status cannot be selected; use scenario mode")
    if mode == "scenario" and selected_status is None:
        raise ValueError("scenario mode requires a selected status")
    blockers, refs = [], []
    live = "unknown"
    if not _available(control, on):
        blockers.append("Dated control evidence is missing or not yet available.")
    else:
        refs.append(control["source_ref"])
        state = control.get("state")
        if state in {"draft_rights", "under_contract", "option_pending"}:
            live = state
        elif state not in {"expired", "released"}:
            blockers.append("Contract expiry or release is not established.")
        elif not control.get("effective_on") or _day(control["effective_on"]) > _day(on):
            blockers.append("Contract expiry or release has not taken effect.")
        elif state == "released" and control.get("waivers_cleared") is not True:
            live = "waivers_pending"
            blockers.append("Waiver clearance is not established.")
        elif control.get("rfa_eligible") is False:
            live = "UFA"
        elif control.get("rfa_eligible") is not True:
            blockers.append("Restricted-free-agency eligibility is unresolved.")
        else:
            qo = control.get("qualifying_offer")
            if not _available(qo, on):
                blockers.append("A qualifying-offer outcome is missing or future-dated.")
            else:
                refs.append(qo["source_ref"])
                if (qo.get("status") == "active" and qo.get("timely") is True and
                        qo.get("valid") is True and qo.get("rights_preserved") is True):
                    live = "RFA"
                elif qo.get("status") == "withdrawn" and qo.get("valid_withdrawal") is True:
                    live = "UFA"
                elif (qo.get("status") == "not_tendered" and qo.get("final") is True and
                      qo.get("deadline") and _day(qo["deadline"]) < _day(on)):
                    live = "UFA"
                else:
                    blockers.append("Timely valid tender, rights preservation, or final loss of rights is unverified.")
    effective = selected_status if mode == "scenario" else live
    return {"mode": mode, "live_status": live, "selected_status": selected_status,
            "effective_status": effective, "is_hypothetical": mode == "scenario",
            "blockers": blockers, "evidence_refs": refs,
            "scenario_note": ("Assumes an expired/cleared contract and, for RFA, a valid qualifying offer with retained rights."
                              if mode == "scenario" else None)}


def estimate_market(*, on, production, comparables, cap):
    """Fit log salary/cap against dated production; return an uncapped salary band.

    No team demand, market exits, later contracts, career trajectories or hidden
    engine ratings enter this estimate. The spread is a judgment range, not a
    statistical confidence interval or a probability of receiving an offer.
    """
    _day(on)
    empty = {"status": "unavailable", "low": None, "target": None, "high": None,
             "cap_share_low": None, "cap_share_target": None, "cap_share_high": None,
             "confidence": "unavailable", "drivers": [], "evidence_refs": [],
             "comparable_count": 0, "comparables": [], "excluded_count": 0}
    if not _available(production, on) or not _totals_ok(production.get("totals")):
        return dict(empty, drivers=["Dated, nonzero NBA production evidence is required; unknown is not minimum-salary value."])
    if not _age_ok(production.get("age")):
        raise ValueError("age must be an integer from 0 to 99, or None")
    if not _available(cap, on) or not _positive(cap.get("amount")):
        return dict(empty, drivers=["A dated published cap or explicitly labeled prior-season planning cap is required."])
    if cap.get("basis") not in {"published", "prior_season_planning", "scenario"}:
        return dict(empty, drivers=["The cap basis is not established."])
    target = production_value(production["totals"], production.get("age"))
    rows, excluded, seen = [], 0, set()
    for row in comparables:
        if not isinstance(row, dict):
            excluded += 1
            continue
        usable = (_available(row, on) and row.get("id") and row.get("id") not in seen and
                  row.get("salary_kind") == "veteran_contract" and _positive(row.get("salary")) and
                  _positive(row.get("cap")) and _totals_ok(row.get("totals")) and
                  row["totals"]["minutes"] >= MIN_COMPARABLE_MINUTES and
                  _age_ok(row.get("age")))
        try:
            usable = usable and _day(row.get("cap_known_on")) <= _day(on)
            if row.get("signed_date") is not None:
                usable = usable and _day(row["signed_date"]) <= _day(row["as_of"])
        except (TypeError, ValueError):
            usable = False
        if not usable:
            excluded += 1
            continue
        seen.add(row["id"])
        value = production_value(row["totals"], row.get("age"))
        rows.append({"id": row["id"], "label": row.get("label", row["id"]),
                     "value": value, "cap_share": row["salary"] / row["cap"],
                     "salary": row["salary"], "source_ref": row["source_ref"],
                     "basis": row.get("basis", "scheduled_salary_proxy"),
                     "salary_season": row.get("salary_season"),
                     "signed_date": row.get("signed_date"), "age": row.get("age"),
                     "normalization_cap": row["cap"], "cap_known_on": row["cap_known_on"]})
    empty.update(comparable_count=len(rows), excluded_count=excluded)
    if len(rows) < MIN_COMPARABLES:
        return dict(empty, drivers=[f"At least {MIN_COMPARABLES} dated veteran comparables with 500 minutes are required."])
    xs, ys = [r["value"] for r in rows], [math.log(r["cap_share"]) for r in rows]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    variance = sum((x - mx) ** 2 for x in xs)
    if variance <= 1e-12:
        return dict(empty, drivers=["Comparable production does not vary enough to fit a price relationship."])
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / variance
    if slope <= 0:
        return dict(empty, drivers=["The supplied comparables do not support a positive production-price relationship."])
    intercept = my - slope * mx
    residuals = [y - (intercept + slope * x) for x, y in zip(xs, ys)]
    center = statistics.median(residuals)
    spread = max(MIN_LOG_BAND, 1.4826 * statistics.median(abs(r - center) for r in residuals))
    minutes = production["totals"]["minutes"]
    spread += 0.20 * 500 / (minutes + 500)
    extrapolated = not min(xs) <= target <= max(xs)
    if extrapolated:
        spread += 0.25
    log_price = intercept + slope * target
    if not -50 < log_price - spread < log_price + spread < 50:
        return dict(empty, drivers=["Inputs produce an unstable estimate outside the supported numeric range."])
    shares = [math.exp(log_price - spread), math.exp(log_price), math.exp(log_price + spread)]
    nearest = sorted(rows, key=lambda r: (abs(r["value"] - target), r["id"]))[:5]
    drivers = [f"{len(rows)} existing veteran scheduled salaries; production uses box-score efficiency, a 500-minute shrinkage prior, and age.",
               "Salary-season cap shares are a scheduled-salary proxy, not signing-year or first-year new-contract comparables.",
               "Existing contracts reflect past bargaining and can overpay or underpay; no held-out new-signing calibration supports predictive confidence.",
               "Band is uncapped first-year market worth; legal limits and a club's available route are separate.",
               "No extra premium is added for points, awards, wins, or potential already represented in production."]
    if production.get("age") is None:
        drivers.append("Age is unknown; neutral age factor applied and confidence reduced.")
    if cap["basis"] != "published":
        drivers.append("Dollars use a planning/scenario cap; the new-season legal maximum is not established by this estimate.")
    if extrapolated:
        drivers.append("Player is outside the comparable production range; extrapolation widens the band.")
    coverage = "moderate" if len(rows) >= 20 and minutes >= 1500 and not extrapolated and production.get("age") is not None else "low"
    return {"status": "estimated", "low": round(shares[0] * cap["amount"]),
            "target": round(shares[1] * cap["amount"]), "high": round(shares[2] * cap["amount"]),
            "cap_share_low": shares[0], "cap_share_target": shares[1], "cap_share_high": shares[2],
            "confidence": "low", "evidence_coverage": coverage,
            "drivers": drivers, "evidence_refs": sorted(set(
                [production["source_ref"], cap["source_ref"]] + [r["source_ref"] for r in rows])),
            "comparable_count": len(rows), "excluded_count": excluded,
            "comparables": [{**r, "value": round(r["value"], 3)} for r in nearest],
            "production_value": round(target, 3), "cap_basis": cap["basis"],
            "model": {"name": "dated-veteran-cap-share-v1", "intercept": intercept,
                      "slope": slope, "log_band": spread, "extrapolated": extrapolated,
                      "comparable_basis": "scheduled_salary_proxy",
                      "calibration": "heuristic; not validated against new signings"}}


def salary_bounds(*, on, season, years_of_service, prior_salary=None, cap=None, route=None, root=ROOT):
    """First-year player limits and a dated route ceiling, never contract approval.

    The 2003-04 maximum is the only published maximum table supported here.
    Unknown service does not silently become zero service; prior salary unknown
    leaves the 105% alternative unresolved. Route capacity must be supplied by
    a separate cap/rights adapter and never inferred from the player valuation.
    """
    _day(on)
    out = {"minimum": None, "maximum": None, "service_tier_maximum": None,
           "route_ceiling": None, "offer_floor": None, "offer_ceiling": None,
           "status": "incomplete", "contract_legality": "not_evaluated",
           "blockers": [], "evidence_refs": []}
    if not date(1999, 1, 20) <= _day(on) <= date(2005, 6, 30):
        out["blockers"].append("The view date is outside the supported 1999-agreement era.")
        return out
    if type(years_of_service) is not int or years_of_service < 0:
        out["blockers"].append("Verified NBA years of service are required for salary limits.")
        return out
    minimum_data = json.loads((Path(root) / MINIMUMS).read_text(encoding="utf-8"))
    if season not in minimum_data["seasons"]:
        out["blockers"].append("The requested season has no supported 1999-agreement minimum table.")
        return out
    key = "10_plus" if years_of_service >= 10 else str(years_of_service)
    out["minimum"] = minimum_data["seasons"][season][key]
    out["evidence_refs"].append(MINIMUMS)
    published = (season == "2003-04" and _day(on) >= date(2003, 7, 15) and
                 _available(cap, on) and cap.get("basis") == "published" and
                 cap.get("season") == season and cap.get("amount") == 43840000)
    if published:
        rules = json.loads((Path(root) / CAP_RULES).read_text(encoding="utf-8"))
        tier = "0_to_6_years" if years_of_service <= 6 else "7_to_9_years" if years_of_service <= 9 else "10_plus_years"
        out["service_tier_maximum"] = rules["maximum_salary"][tier]
        out["evidence_refs"].extend([CAP_RULES, cap["source_ref"]])
        if type(prior_salary) is int and prior_salary >= 0:
            out["maximum"] = max(out["service_tier_maximum"], round(prior_salary * 1.05))
        else:
            out["blockers"].append("Prior salary is unknown; the 105% prior-salary maximum alternative is unresolved.")
    else:
        out["blockers"].append("A supported published season maximum is unavailable on this date; a planning cap cannot replace it.")
    if (not _available(route, on) or route.get("verified") is not True or
            type(route.get("capacity")) is not int or route["capacity"] < 0):
        out["blockers"].append("Team spending route, rights and remaining capacity require separate dated verification.")
    elif route.get("name") not in {"room", "bird", "early_bird", "non_bird", "mid_level", "million", "minimum"}:
        out["blockers"].append("Unsupported spending route; rookie-scale signing uses its own workflow.")
    else:
        out["route_ceiling"] = route["capacity"]
        out["evidence_refs"].append(route["source_ref"])
    if out["maximum"] is not None and out["route_ceiling"] is not None:
        out["offer_floor"] = out["minimum"]
        out["offer_ceiling"] = min(out["maximum"], out["route_ceiling"])
        out["status"] = "first_year_bounds_only"
        if out["offer_ceiling"] < out["offer_floor"]:
            out["status"] = "no_first_year_capacity"
            out["blockers"].append("The verified route cannot fund this player's minimum salary.")
    return out


def build_profile(*, on, mode="live", selected_status=None, control=None, production=None,
                  comparables=(), cap=None, season="2003-04", years_of_service=None,
                  prior_salary=None, route=None, root=ROOT):
    """Return a JSON-safe display profile without writing or executing any action."""
    if not date(1999, 1, 20) <= _day(on) <= date(2005, 6, 30):
        raise ValueError("the profile supports the 1999 agreement only; choose a supported era adapter")
    eligibility = select_status(on=on, mode=mode, selected_status=selected_status, control=control)
    if mode == "live" and cap and cap.get("basis") == "scenario":
        raise ValueError("scenario cap assumptions cannot enter a live profile")
    value = estimate_market(on=on, production=production, comparables=comparables, cap=cap)
    bounds = salary_bounds(on=on, season=season, years_of_service=years_of_service,
                           prior_salary=prior_salary, cap=cap, route=route, root=root)
    if eligibility["effective_status"] == "draft_rights":
        bounds = {key: None for key in ("minimum", "maximum", "service_tier_maximum",
                                      "route_ceiling", "offer_floor", "offer_ceiling")}
        bounds.update(status="rookie_scale_required", contract_legality="not_evaluated",
                      evidence_refs=eligibility["evidence_refs"],
                      blockers=["Unsigned draft rights require their draft-specific signing workflow; veteran free-agent salary bounds do not apply."])
    return {"schema_version": 1, "as_of": on, "season": season, "era": "1999",
            "eligibility": eligibility, "market_value": value, "legal_bounds": bounds,
            "execution_enabled": False,
            "actions": (["compare_terms", "prepare_counter", "review_incumbent_offer", "review_outside_offer_sheet"]
                        if eligibility["effective_status"] == "RFA" else
                        ["compare_terms", "prepare_counter", "review_team_offers"]
                        if eligibility["effective_status"] == "UFA" else
                        ["review_rookie_scale"] if eligibility["effective_status"] == "draft_rights" else
                        ["review_control_record"]),
            "action_note": "Preparation only. Signing, timing, valid rights and complete terms require the negotiation workflow and authenticated verification."}


def load_2003_comparables(*, on, root=ROOT):
    """June-26 inventory only: exclude rookie, unresolved, option and later contracts.

    Salaries already owed for 2003-04 are normalized by the same dated cap that
    sizes the current estimate. Before publication that is the prior planning
    cap. No free-agent exits, future cap rows or real Wade career data are read.
    """
    _day(on)
    if on < "2003-06-26" or on > "2004-06-30":
        return []
    def read(path):
        return json.loads((Path(root) / path).read_text(encoding="utf-8"))
    stats_data, inventory = read(STATS), read(CONTRACTS)
    try:
        stats_on, contracts_on = stats_data["as_of_date"], inventory["as_of"]
        if any(not _day(d) <= _day(on) or _day(d) > date(2003, 6, 26)
               for d in (stats_on, contracts_on)):
            return []
    except (KeyError, TypeError, ValueError):
        return []
    stats = {r["bbr_id"]: r for r in stats_data["records"]}
    birth = {p["bbr_id"]: p["birth_date"] for c in read(BASELINE)["clubs"].values()
             for p in c["players"] if p.get("bbr_id") and p.get("birth_date")}
    published = on >= "2003-07-15"
    cap, cap_on = (43840000, "2003-07-15") if published else (40271000, contracts_on)
    out = []
    for club in inventory["clubs"].values():
        for p in club["players"]:
            player_id = p.get("bbr_id")
            if (p["status"] != "under_contract" or player_id not in stats or
                    p.get("amount_kind", {}).get("2003-04") != "contract_salary"):
                continue
            signed = p.get("signed_date")
            try:
                if signed is not None and _day(signed) > _day(contracts_on):
                    continue
            except (TypeError, ValueError):
                continue
            salary = p.get("schedule", {}).get("2003-04")
            if not _positive(salary):
                continue
            out.append({"id": player_id, "label": p.get("player", player_id),
                        "as_of": max(contracts_on, stats_on), "source_ref": f"{CONTRACTS}#{player_id};{STATS}#{player_id}",
                        "salary_kind": "veteran_contract", "salary": salary,
                        "basis": "scheduled_salary_proxy", "salary_season": "2003-04", "signed_date": signed,
                        "cap": cap, "cap_known_on": cap_on,
                        "totals": stats[player_id]["totals"],
                        "age": age_on(birth[player_id], on) if player_id in birth else None})
    return out


def demo_profiles(root=ROOT):
    """Explicitly synthetic player/rights scenarios with dated 2003 league comps."""
    on = "2003-07-16"
    cap = {"as_of": "2003-07-15", "source_ref": "library/2003/league/nba_2003_04_calendar.json#cap_published",
           "amount": 43840000, "season": "2003-04", "basis": "published"}
    roles = []
    comps = load_2003_comparables(on=on, root=root)
    for key, label, points, assists, minutes in (
            ("rotation", "Illustrative rotation guard", 650, 180, 1450),
            ("starter", "Illustrative starting guard", 1250, 360, 2250),
            ("star", "Illustrative leading guard", 1900, 570, 2750)):
        totals = {"games": 72, "minutes": minutes, "points": points,
                  "offensive_rebounds": 60, "defensive_rebounds": 250,
                  "assists": assists, "steals": 95, "blocks": 30,
                  "field_goals_attempted": round(points * .75), "field_goals_made": round(points * .35),
                  "free_throws_attempted": round(points * .25), "free_throws_made": round(points * .2),
                  "turnovers": round(assists * .45)}
        production = {"as_of": "2003-06-26", "source_ref": f"example:synthetic-{key}-production",
                      "totals": totals, "age": 25}
        roles.append({"id": key, "label": label, "production": production,
                      "market_value": estimate_market(on=on, production=production, comparables=comps, cap=cap)})
    control = {"as_of": "2003-07-01", "source_ref": "example:synthetic-expired-contract",
               "state": "expired", "effective_on": "2003-07-01", "rfa_eligible": False}
    profiles = {status: build_profile(on=on, mode="scenario", selected_status=status,
                control=control, production=roles[1]["production"], comparables=comps,
                cap=cap, years_of_service=4, prior_salary=2500000, root=root)
                for status in ("UFA", "RFA")}
    checkpoint = build_profile(on="2003-06-26", control={"as_of": "2003-06-26",
        "source_ref": "career/Dwyane_Wade/2003-04/current_state.json", "state": "draft_rights"},
        years_of_service=0, prior_salary=0, root=root)
    return {"schema_version": 1, "example_only": True, "on": on, "cap": cap["amount"],
            "player_label": "Illustrative fourth-year guard", "profiles": profiles,
            "roles": roles, "current_checkpoint": checkpoint,
            "note": "Synthetic production and selectable status; no Wade results, actual offers, or career events."}


if __name__ == "__main__":
    print(json.dumps(demo_profiles(), indent=2, sort_keys=True, allow_nan=False))
