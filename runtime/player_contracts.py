"""Dated, read-only contract dossiers. Missing compensation is never zero.

Only reached canonical sources are read. Offers, draft rights and cap holds do
not create contracts. Assignments do not create another signing.
"""
from copy import deepcopy
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import re

SIGNED = {"under_contract", "under_rookie_contract", "under_contract_guarantee_amended",
          "signed_free_agent", "re_signed", "team_option_pending", "player_option_pending",
          "team_option_exercised", "player_option_exercised", "free_agent_expiring",
          "team_option_declined", "player_option_declined", "traded", "released",
          "retired_salary_on_books", "signed", "expired", "camp_contract",
          "expiring_contract", "signed_elsewhere", "renounced", "voided", "waived", "retired"}
CLOSED = {"team_option_declined", "player_option_declined", "released", "expired",
          "retired_salary_on_books", "signed_elsewhere", "renounced", "voided", "waived", "retired"}
DECLINED = {"team_option_declined", "player_option_declined"}    # closed only from the declined season on
# A status that says a contract is in force, and the control statuses that claim one: shown only while an agreement is.
IN_FORCE = SIGNED - CLOSED - {"traded", "signed"}
CLAIMS = IN_FORCE | {"traded", "signed", "under_contract_unverified", "minimum_contract_unverified"}
NON_SALARY = {"draft_hold", "unsigned_rights"}
OPTION_KINDS = ("team_option", "player_option", "early_termination_option")
# A dated league move (`<season>/League/league_moves.json`): an assignment, a new agreement or the agreement's end.
MOVE_ASSIGN, MOVE_SIGN, MOVE_CLOSE = ("trade", "claim"), ("ten_day", "rest_of_season"), {
    "waive": "waived", "clear": "waived", "expire": "expired", "retire": "retired"}
MONEY_FIELDS = ("base_salary", "cap_hit", "guaranteed", "likely_incentives",
                "unlikely_incentives", "signing_bonus", "dead_cap", "buyout")
TERM_FIELDS = ("trade_clauses", "trade_kicker", "no_trade_clause", "trade_consent",
               "trade_restrictions", "base_year_compensation", "bird_rights", "free_agency",
               "payment_schedule", "bonus_terms", "guarantee_triggers", "waiver_deadline",
               "buyout_terms", "promise", "percent_of_scale", "guarantee_date")


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8")) if Path(path).is_file() else {}


def _day(value):
    try:
        return date.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        return None


def _known(value, cutoff):
    return _day(value) is not None and value <= cutoff


def _snapshot(value, cutoff):
    return (isinstance(value, dict) and _known(value.get("as_of"), cutoff)
            and not any(_day(value.get(k)) and value[k] > cutoff for k in ("updated", "updated_at")))


def _number(value):
    return value if type(value) in (int, float) and value >= 0 else None


def _money(value):
    return f"$ {value:,.0f}".replace("$ ", "$") if _number(value) is not None else "Not recorded"


def _text(value):
    if value is None or value == "":
        return "Not recorded"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, dict):
        return "; ".join(f"{k.replace('_', ' ')}: {_text(v)}" for k, v in value.items()) or "Not recorded"
    if isinstance(value, list):
        return "; ".join(_text(v) for v in value) or "Not recorded"
    return str(value)


def _slug(value):
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def register_contract_id(row):
    """The contract page id of a Miami register row whose name the league registry does not carry. The catalog and the
    personnel cards' contract links (runtime/contract_navigation.py) both name it this way."""
    return row.get("bbr_id") or row.get("registry_id") or row.get("id") or _slug(row["name"])


def _source(path, root, label=None):
    path = Path(path).resolve()
    return {"label": label or path.name, "path": path.relative_to(root).as_posix()}


def _sources(entry, source, season, root):
    result = [source]
    for value in entry.get("sources", []):
        if not isinstance(value, str):
            continue
        if value.startswith(("https://", "http://")):
            item = {"label": "Contract source document", "href": value}
        else:
            raw = value.split("#", 1)[0]
            candidates = [root / raw, season / raw, (root / source["path"]).parent / raw]
            target = next((p.resolve() for p in candidates if p.is_file() and root in p.resolve().parents), None)
            if target is None:
                continue
            item = _source(target, root, "Signing / contract source")
        if item not in result:
            result.append(item)
    return result


def _contract_key(player_id, entry):
    if entry.get("contract_id"):
        return str(entry["contract_id"])
    if entry.get("signed_date"):
        return f"{player_id}-{entry['signed_date']}"
    material = json.dumps({"schedule": entry.get("schedule"), "prior": entry.get("prior_season_salary")}, sort_keys=True)
    return f"{player_id}-existing-{hashlib.sha256(material.encode()).hexdigest()[:12]}"


def _merge(old, new):
    result = deepcopy(old)
    for key, value in new.items():
        if key == "_sources":
            result[key] = old.get(key, []) + [v for v in value if v not in old.get(key, [])]
        elif isinstance(value, dict) and key in ("schedule", "amount_kind", "amount_precision", *MONEY_FIELDS):
            result[key] = {**old.get(key, {}), **value}
        else:
            result[key] = deepcopy(value)
    return result


def _same_contract(old, new):
    if old.get("contract_id") and new.get("contract_id"):
        return old["contract_id"] == new["contract_id"]
    if old.get("signed_date") and new.get("signed_date"):
        return old["signed_date"] == new["signed_date"]
    if old.get("status") not in SIGNED or new.get("status") not in SIGNED:
        return False
    shared = set(old.get("schedule", {})) & set(new.get("schedule", {}))
    # An unrecorded amount is unknown, not a different salary: only two recorded amounts can disagree. Without one
    # recorded on both sides the seasons prove nothing, unless the two records name the agreement in the two ways that
    # cannot be compared (one by its signing date only, the other by its contract id only: a reported signing and the
    # sheet row a trade brought in under its baseline id).
    known = [s for s in shared if old["schedule"][s] is not None and new["schedule"][s] is not None]
    if known:
        return all(old["schedule"][s] == new["schedule"][s] for s in known)
    named = lambda e: (bool(e.get("signed_date")), bool(e.get("contract_id")))
    return bool(shared) and {named(old), named(new)} == {(True, False), (False, True)}


def _season_before(season):
    return f"{int(season[:4]) - 1}-{season[2:4]}"


def _season_after(season):
    return f"{int(season[:4]) + 1}-{str(int(season[:4]) + 2)[-2:]}"


def _june_30(season):
    return f"{int(season[:4]) + 1}-06-30"


def _outcome(kind, decision):
    """An applied option decision (`runtime/options.py`: exercise/decline, stay/leave) as the option's outcome, and
    whether it removes the season (a declined option, an opt-out, an exercised early termination)."""
    if kind == "early_termination_option":
        return ("exercised", True) if decision == "leave" else ("not exercised", False)
    return ("exercised", False) if decision in ("exercise", "stay") else ("declined", True)


def _option_rows(entry):
    """The agreement's options: recorded option lists, option amount kinds, the sheet's `team_option_season`, each with
    its applied decision (`League/option_decisions.json`) laid over it."""
    schedule = entry.get("schedule", {})
    options = deepcopy(entry.get("options", [])) if isinstance(entry.get("options"), list) else []
    kinds = dict(entry.get("amount_kind", {}))
    if entry.get("team_option_season") and not kinds.get(entry["team_option_season"]) in OPTION_KINDS:
        kinds[entry["team_option_season"]] = "team_option"      # an exercised option's season reads contract_salary
    for season, kind in sorted(kinds.items()):
        if kind not in OPTION_KINDS or any(o.get("season") == season for o in options):
            continue
        # a rookie-scale fourth-year option names its deadline; so does an extension's option (runtime/extensions.py)
        option = {"season": season, "type": kind, "amount": _number(schedule.get(season)),
                  "deadline": (entry.get("option_deadline") or entry.get("fourth_year_option_deadline")) if kind == "team_option" else None,
                  "outcome": None, "outcome_date": None}
        if entry.get("status") in (f"{kind}_exercised", f"{kind}_declined"):
            option.update(outcome=entry["status"].split("_")[-1],
                          outcome_date=entry.get("option_decision_date"), evidence_as_of=entry.get("_as_of"))
        options.append(option)
    for d in entry.get("_option_decisions", []):
        option = next((o for o in options if o.get("season") == d["option_season"] and o.get("type") == d["kind"]), None)
        if option is None:
            option = {"season": d["option_season"], "type": d["kind"], "amount": None, "deadline": None}
            options.append(option)
        outcome, removes = _outcome(d["kind"], d["decision"])
        option.update(amount=option.get("amount") if option.get("amount") is not None else _number(d.get("salary")),
                      deadline=option.get("deadline") or d.get("deadline"), outcome=outcome,
                      outcome_date=d.get("applied") or d.get("recorded_on"), decided_by=d.get("decider"),
                      removes_season=removes)
    return sorted(options, key=lambda o: o.get("season") or "")


def _last_season(entry):
    """The agreement's final season when its own record establishes it: a recorded end, the last season of a schedule
    that is the whole agreement (Miami's authoritative sheet and archive, an executed signing, the league contract
    ledger, a league move), cut short by an option that removed its season. None for a partial salary fragment."""
    schedule = entry.get("schedule", {})
    seasons = sorted(s for s in schedule if entry.get("amount_kind", {}).get(s) not in NON_SALARY)
    end = entry.get("end_season") if isinstance(entry.get("end_season"), str) else None
    if end is None and seasons and (entry.get("_whole_schedule") or entry.get("full_original_schedule") is True):
        end = seasons[-1]
    end = end or entry.get("_ledger_end") or entry.get("_superseded_end")
    removed = [o["season"] for o in _option_rows(entry) if o.get("removes_season")
               or (o.get("outcome") == "declined" and o.get("type") != "early_termination_option")]
    if entry.get("_ledger_cut"):
        removed.append(entry["_ledger_cut"])      # the next league contract ledger does not carry the agreement
    if removed:
        cut = _season_before(min(removed))
        end = min(end, cut) if end else cut
    return end


def _salary_seasons(entry):
    return sorted(s for s in entry.get("schedule") or {} if entry.get("amount_kind", {}).get(s) not in NON_SALARY)


def _open_fragment(entry):
    """A salary fragment whose end its own record leaves open: no final season, expiry or dated closing."""
    return bool(_salary_seasons(entry) and not entry.get("_league_move") and not entry.get("expiry_date")
                and not entry.get("_ended_on") and entry.get("status") not in CLOSED and _last_season(entry) is None)


def _season_of(day):
    year = int(day[:4]) - (day[5:7] < "07")
    return f"{year}-{str(year + 1)[-2:]}"


def _expiry(entry):
    expiry = entry.get("expiry_date")
    end = _last_season(entry)
    if end and re.fullmatch(r"\d{4}-\d{2}", end):
        expiry = min(expiry, _june_30(end)) if expiry else _june_30(end)
    return expiry


def _started(entry, day):
    if entry.get("signed_date") and entry["signed_date"] > day:
        return False
    first = entry.get("start_season")
    return not first or first[:4] + "-07-01" <= day


def _ended(entry, day):
    """True once the agreement is no longer in force on `day`: closed by a dated event, a closing status without a
    date, or past its expiry."""
    if entry.get("_ended_on"):
        if entry["_ended_on"] <= day:
            return True
    elif entry.get("status") in CLOSED - DECLINED:
        return True
    elif entry.get("status") in DECLINED and not any(o.get("outcome") == "declined" for o in _option_rows(entry)):
        return True
    expiry = _expiry(entry)
    return bool(expiry and expiry < day)


def _start_key(entry):
    first = entry.get("start_season") or min(entry.get("schedule") or {"": None})
    return entry.get("signed_date") or (first[:4] + "-07-01" if first else "")


def _holding(entries, day):
    """The agreements a holder change on `day` moves: the newest agreement in force, with every agreement signed by then
    that has not begun (an extension travels with the contract it extends)."""
    live = [e for e in entries if _started(e, day) and not _ended(e, day)]
    newest = max(live, key=lambda e: (_start_key(e), e.get("_as_of") or ""), default=None)
    future = [e for e in entries if e.get("signed_date") and e["signed_date"] <= day and not _started(e, day)
              and not _ended(e, day)]
    return ([newest] if newest else []) + future


def _normal_contract(player_id, entry, cutoff, caps):
    schedule = entry.get("schedule", {})
    rows = []
    prior = entry.get("prior_season_salary")
    if isinstance(prior, dict) and prior.get("season") and prior["season"] not in schedule:
        rows.append({"season": prior["season"], "salary": _number(prior.get("amount")),
                     "amount_kind": "prior_season_salary_reference", "precision": "recorded prior-season reference",
                     **{k: None for k in MONEY_FIELDS}, "salary_cap": None, "cap_percent": None,
                     "salary_cap_percent": None,
                     "condition": "Prior salary evidence; not automatically part of the full original term."})
    for season, value in sorted(schedule.items()):
        kind = entry.get("amount_kind", {}).get(season)
        if kind in NON_SALARY:
            continue
        row = {"season": season, "salary": _number(value), "amount_kind": kind,
               "precision": entry.get("amount_precision", {}).get(season),
               "condition": entry.get("conditions", {}).get(season)}
        for field in MONEY_FIELDS:
            mapping = entry.get(field, {})
            row[field] = _number(mapping.get(season)) if isinstance(mapping, dict) else None
        if row["guaranteed"] is None and isinstance(entry.get("guarantee"), dict):
            row["guaranteed"] = _number(entry["guarantee"].get("protected_amount_" + season.replace("-", "_")))
        cap = caps.get(season)
        row["salary_cap"] = cap
        row["cap_percent"] = round(100 * row["cap_hit"] / cap, 4) if cap and row["cap_hit"] is not None else None
        row["salary_cap_percent"] = round(100 * row["salary"] / cap, 4) if cap and row["salary"] is not None else None
        rows.append(row)
    after = [(entry["_ledger_cut"], f"Not carried by the {entry['_ledger_cut']} league contract ledger; not part of the contract.")
             ] if entry.get("_ledger_cut") else []
    if entry.get("_superseded_end"):
        after.append((_season_after(entry["_superseded_end"]),
                      f"A later agreement began in {entry['_superseded_by']}; not part of this contract."))
    for first, outcome in after:          # recorded seasons the agreement did not reach keep their row, so marked
        for row in rows:
            if row["season"] >= first and row["amount_kind"] != "prior_season_salary_reference":
                row["condition"] = f"{row['condition'].rstrip()} {outcome}" if row["condition"] else outcome
    options = _option_rows(entry)
    for option in options:
        if option.get("outcome") is not None and option.get("outcome_date") and not _known(option["outcome_date"], cutoff):
            option.update(outcome=None, outcome_date=None, removes_season=False)
        row = next((r for r in rows if r["season"] == option.get("season") and r["amount_kind"] != "prior_season_salary_reference"), None)
        if row is not None and option.get("outcome"):
            # the season's own condition is dated evidence (often "no decision recorded on or before ..."): the outcome
            # follows it, and a season the decision removed says so
            removes = option.get("removes_season") or (option["outcome"] == "declined" and option.get("type") != "early_termination_option")
            outcome = (" ".join(filter(None, [option["type"].replace("_", " ").capitalize(), option["outcome"], option.get("outcome_date")]))
                       + ("; not part of the contract." if removes else "."))
            if outcome not in (row["condition"] or ""):
                row["condition"] = f"{row['condition'].rstrip()} {outcome}" if row["condition"] else outcome
    total = entry.get("reported_total")
    total = deepcopy(total) if isinstance(total, dict) else {"amount": _number(total), "precision": None}
    scheduled = [r["salary"] for r in rows if r["amount_kind"] != "prior_season_salary_reference"]
    complete = bool(entry.get("full_original_schedule") is True and scheduled and all(v is not None for v in scheduled))
    if complete and total.get("amount") is None:
        total = {"amount": sum(scheduled), "precision": "complete recorded schedule; includes conditional option years"}
    term = entry.get("original_term_seasons")
    original_aav = (total.get("amount") / term if complete and type(term) is int and term == len(scheduled) and term > 0
                    and total.get("amount") is not None else None)
    # a dated closing (a waiver, an expired ten-day, a Miami release or void) ends the agreement on its date; one past
    # its own expiry reads expired, never under contract
    ended = entry.get("_ended_on") if _known(entry.get("_ended_on"), cutoff) else None
    status, expiry = entry.get("_close_status") if ended and entry.get("_close_status") else entry.get("status"), _expiry(entry)
    if cutoff and not ended and status in IN_FORCE and expiry and expiry < cutoff:
        status = "expired"
    return {"id": _contract_key(player_id, entry), "status": status,
        "team": entry.get("_team"), "signing_team": entry.get("signing_team"),
        "signed_on": entry.get("signed_date"), "start_season": entry.get("start_season"),
        "end_season": _last_season(entry), "expiry_date": expiry, "ended_on": ended,
        "type": entry.get("route") or entry.get("basis") or "Existing contract record",
        "original_term_seasons": term, "reported_total": total, "original_aav": original_aav,
        "scheduled_subtotal": sum(v for v in scheduled if v is not None) if any(v is not None for v in scheduled) else None,
        "scheduled_unknown_count": sum(v is None for v in scheduled), "full_original_schedule": complete,
        "salary_rows": rows, "options": options, "guarantee": deepcopy(entry.get("guarantee")),
        "terms": {key: deepcopy(entry.get(key)) for key in TERM_FIELDS},
        "notes": entry.get("notes"), "contract_text": entry.get("contract_text"),
        "assignment_history": sorted(deepcopy(entry.get("_assignments", [])), key=lambda a: a["date"]),
        "sources": deepcopy(entry.get("_sources", [])), "record_as_of": entry.get("_as_of")}


from .league_book import SYMMETRIC_FROM                                       # noqa: E402  (real moves stop applying)
MARKET_SIGNINGS = ("signing", "re_sign", "offer_sheet_matched", "qualifying_offer_accepted", "camp_signing", "rookie_scale_signing")


def _market_contracts(root, player, cutoff, add, match, protagonist, moves):
    """Every completed summer market's contracts (2004 onward), oldest first; its trades join `moves`."""
    for path in sorted(Path(root).glob("career/Dwyane_Wade/????-??/10_Free_Agency/free_agency_????.json")):
        year = int(path.stem[-4:])
        _market_year_contracts(root, player, cutoff, add, match, protagonist, path, f"{year}-{str(year + 1)[-2:]}", moves)


def _market_year_contracts(root, player, cutoff, add, match, protagonist, path, NEW, moves):
    from .extensions import base_schedule
    from .league_contracts import read as read_ledger, schedule_for
    from .seasons import dates
    record = _read(path)
    ledger = read_ledger(NEW, root) or {}
    guarantee = dates(NEW, root)["guarantee"]
    source = _source(path, root, "Simulated summer market (every club)")
    for e in sorted(record["events"], key=lambda e: e["date"]):
        if not _known(e["date"], cutoff) or e.get("player") == protagonist:
            continue
        if e["kind"] in MARKET_SIGNINGS:
            salary = e.get("salary") or e.get("amount")
            years = e.get("years") or 1
            route = e.get("route") or ("rookie_scale" if e["kind"] == "rookie_scale_signing" else
                                       "qualifying_offer" if e["kind"] == "qualifying_offer_accepted" else "signing")
            lg = ledger.get(e["bbr_id"]) or {}
            # a later extension's seasons are its own agreement (runtime/extensions.py), never this signing's
            schedule = base_schedule(lg) if lg.get("schedule") and lg.get("club") else schedule_for(salary, years, NEW, route)
            seasons = sorted(schedule)
            camp = e["kind"] == "camp_signing"
            entry = {"player": e["player"], "bbr_id": e["bbr_id"], "status": "under_contract", "signed_date": e["date"],
                     "signing_team": e["club"], "route": route.replace("_", " "), "original_term_seasons": len(seasons),
                     "start_season": seasons[0], "end_season": seasons[-1], "schedule": schedule,
                     "amount_kind": {k: ("team_option" if lg.get("team_option") == k else "contract_salary") for k in seasons},
                     "guaranteed": {k: (0 if camp and k == NEW else v) for k, v in schedule.items()},
                     "notes": (f"Simulated {NEW[:4]} summer market: {e['kind'].replace('_', ' ')} on {e['date']}"
                               + (f", from {e['from']}" if e.get("from") and e["from"] != e["club"] else "")
                               + (f"; non-guaranteed until {guarantee}" if camp else "")
                               + ". Later years follow the agreement's raise rule for the route (runtime/league_contracts.py).")}
            add(entry, e["club"], source, e["date"], path.parent, False)
        elif e["kind"] == "trade":
            key = match({"player": e["player"], "bbr_id": e["bbr_id"]})
            if key:
                moves.append({"date": e["date"], "key": key, "kind": "trade", "from": e.get("from"), "to": e["club"],
                              "id": e.get("deal"), "source": source, "order": (0, path.as_posix(), 0)})


def _ledger_contracts(root, player, cutoff, add, match, profiles, protagonist):
    """The league contract ledger's carried contracts (`<season>/League/contracts.json`, `runtime/league_contracts.py`)
    that no dated record shows for the ledger's season: a 2003 first-round scale contract, or a contract the first ledger
    reconstructed from the season's salaries. Each is an agreement from the ledger, known from the rollover that wrote
    it, with the remaining seasons and option seasons the ledger carries; its option decision and later moves land on it.
    Miami's rows stay its own sheet's, and a new summer-market contract is already its own agreement."""
    from .extensions import without_extension
    from .seasons import club_name
    for season, path, ledger, as_of in _ledgers(player, cutoff):
        source = _source(path, root, "League contract ledger (simulated league)")
        for c in ledger["contracts"]:
            if c.get("club") in (None, "Miami Heat") or c.get("kind") != "existing" or not c.get("schedule"):
                continue
            key = match({"player": c.get("player"), "bbr_id": c.get("bbr_id")})
            if not key or profiles[key]["name"] == protagonist:
                continue
            if any(season in (e.get("schedule") or {}) for e in profiles[key]["_entries"]):
                continue
            schedule = without_extension(c)["schedule"]      # an extension's seasons are its own agreement
            options = c.get("options") or {}
            kinds = {s: options.get(s) if options.get(s) in OPTION_KINDS else "contract_salary" for s in schedule}
            carried = f"Carried by the {season} league contract ledger ({c.get('source') or 'source not recorded'}): the seasons from {season} on."
            same_club = lambda e: club_name(e.get("_team") or "", season) == club_name(c["club"], season)
            fragment = max((e for e in profiles[key]["_entries"] if _open_fragment(e) and same_club(e)
                            and _salary_seasons(e)[-1] == _season_before(season)), key=_start_key, default=None)
            if fragment is not None:
                # the ledger carries on the contract an open fragment at the same club records up to the season before:
                # its later seasons, not another signing (the agreement keeps the fragment's id)
                fragment["contract_id"] = _contract_key(key, fragment)
                fragment["schedule"] = {**fragment.get("schedule", {}), **schedule}
                fragment["amount_kind"] = {**fragment.get("amount_kind", {}), **kinds}
                fragment.update(_whole_schedule=True, _ledger_season=season,
                                notes=f"{fragment['notes']} {carried}" if fragment.get("notes") else carried)
                if source not in fragment["_sources"]:
                    fragment["_sources"].append(source)
                continue
            rookie = bool(c.get("rookie_scale"))
            row = {"player": c["player"], "bbr_id": c["bbr_id"], "status": "under_rookie_contract" if rookie else "under_contract",
                   "route": ("rookie scale" if rookie else "existing contract") + " (league contract ledger)",
                   "schedule": dict(schedule), "_whole_schedule": True, "_ledger_season": season, "amount_kind": kinds,
                   "notes": carried + " Its signing date and earlier seasons are not in the dated records."}
            add(row, c["club"], source, as_of, path.parent.parent, False)


def _ledgers(player, cutoff):
    """[(season, path, ledger, as_of)] for each league contract ledger known on the cutoff: the rollover writes it on
    the closed season's last career date (that season's state stops there)."""
    out = []
    for folder in sorted(player.glob("????-??")):
        path = folder / "League/contracts.json"
        ledger = _read(path)
        as_of = _read(player / _season_before(folder.name) / "current_state.json").get("current_date") or f"{folder.name[:4]}-10-01"
        if ledger.get("contracts") and _known(as_of, cutoff):
            out.append((folder.name, path, ledger, as_of))
    return out


def _ledger_ends(player, cutoff, profiles):
    """A salary fragment's final season when the league contract ledger settles it: an agreement whose end its own record
    leaves open, and which the first ledger after its last recorded season does not carry (the player has no contract
    in that ledger, Miami's sheet included), ended with that recorded season. An agreement a ledger carries ends with
    that ledger's season when the next ledger carries no existing contract for the player (a new signing, or none)."""
    ledgers = _ledgers(player, cutoff)
    carried = {season: {c.get("bbr_id") for c in ledger["contracts"]} for season, _, ledger, _ in ledgers}
    existing = {season: {c.get("bbr_id") for c in ledger["contracts"] if c.get("kind") == "existing"}
                for season, _, ledger, _ in ledgers}
    for profile in profiles.values():
        bbr = (profile.get("identity") or {}).get("bbr_id")
        for entry in profile["_entries"]:
            following = entry.get("_ledger_season") and _season_after(entry["_ledger_season"])
            if bbr and following in existing and bbr not in existing[following]:
                entry["_ledger_cut"] = following
            seasons = _salary_seasons(entry)
            if not bbr or not seasons or entry.get("_league_move") or _last_season(entry) or entry.get("expiry_date"):
                continue
            after = _season_after(seasons[-1])
            if after in carried and bbr not in carried[after]:
                entry["_ledger_end"] = seasons[-1]


def _superseded_ends(profiles, cutoff):
    """An open salary fragment ends once a later agreement has begun (the player cannot be under both): with its last
    recorded season, or the season before the later agreement's first when that comes sooner, never before its own
    first season or the season of its latest dated assignment (which shows it still in force then)."""
    for profile in profiles.values():
        entries = profile["_entries"]
        for entry in [e for e in entries if _open_fragment(e)]:
            seasons = _salary_seasons(entry)
            later = [e.get("start_season") or (_salary_seasons(e) or [""])[0] for e in entries
                     if e is not entry and _started(e, cutoff) and _start_key(e) > _start_key(entry)]
            later = [season for season in later if season]
            if later:
                held = [_season_of(a["date"]) for a in entry.get("_assignments", [])]
                entry["_superseded_end"] = max([min(seasons[-1], _season_before(min(later))), seasons[0], *held])
                entry["_superseded_by"] = min(later)


def _attach_option_decisions(player, cutoff, match, profiles):
    """Every applied option decision (`<season>/League/option_decisions.json`, `runtime/options.py`) on each agreement
    whose option it decides: the one naming that option season (amount kind, option list or the sheet's
    `team_option_season`), else the earlier agreement whose schedule holds the season (Miami's sheet turns an exercised
    option into contract salary). `_option_rows` lays the outcome and its date over the option."""
    for path in sorted(player.glob("????-??/League/option_decisions.json")):
        for d in _read(path).get("decisions", []):
            day = d.get("applied")
            if not d.get("decision") or not _known(day, cutoff):
                continue
            key = match({"player_id": d.get("bbr_id"), "player": d.get("player"), "bbr_id": d.get("bbr_id")})
            if not key:
                continue
            entries = profiles[key]["_entries"]
            s, kind = d["option_season"], d["kind"]
            marked = [e for e in entries if any(o.get("season") == s and o.get("type") == kind for o in _option_rows(e))]
            if not marked:
                marked = [e for e in entries if s in (e.get("schedule") or {}) and _start_key(e) < s[:4] + "-07-01"
                          and (not e.get("signed_date") or e["signed_date"] <= day)]
            for e in marked:
                if all(x.get("id") != d.get("id") for x in e.get("_option_decisions", [])):
                    e.setdefault("_option_decisions", []).append(d)


def _league_moves(player, cutoff, match, profiles, protagonist, root, moves):
    """Every dated league move (`<season>/League/league_moves.json`) as a holder event; Miami's own moves are its records'.
    A trade or claim of a player the engine pins to his club on its date (`league_moves.pinned`: Miami sent him there, or
    a disturbed club's replacement) was never applied and assigns nothing (Eddie Jones in the 2005-01-31 Utah-Houston
    trade); a move that ends an agreement is never skipped."""
    from .league_moves import pinned
    for path in sorted(player.glob("????-??/League/league_moves.json")):
        record = _read(path)
        source = _source(path, root, "Dated league move")
        season = record.get("season") or path.parts[-3]
        for i, m in enumerate(record.get("entries", [])):
            if not _known(m.get("date"), cutoff) or "Miami Heat" in (m.get("from"), m.get("to")):
                continue
            if m.get("kind") in MOVE_ASSIGN and m.get("bbr_id") and m["bbr_id"] in pinned(season, m["date"], root):
                continue
            key = match({"player": m.get("player"), "bbr_id": m.get("bbr_id")})
            if key and profiles[key]["name"] != protagonist:
                moves.append(dict(m, key=key, season=season, source=source,
                                  id=m.get("id") or m.get("deal"), order=(1, path.as_posix(), i)))


def _world_moves(root, cutoff, match, profiles, protagonist, moves):
    """The real league's dated trades and waivers before the symmetric league (rule 1 skips any involving Miami), the
    moves `league_cards.world_moves` gives a registry player's club: draft rights, picks and a sign-and-trade's signing
    (its own agreement, above) are not contract assignments."""
    for path in sorted((root / "library").glob("*/league/nba_*_offseason_transactions.json")):
        data = _read(path)
        source = _source(path, root, "Dated real transaction (before the symmetric league)")
        for i, t in enumerate(data.get("trades", [])):
            if t.get("involves_miami") or not _known(t.get("date"), cutoff) or t["date"] >= SYMMETRIC_FROM:
                continue
            for club, sides in t.get("clubs", {}).items():
                for item in sides.get("in", []):
                    key = None if "(" in item else match({"player": item})
                    if not key or profiles[key]["name"] == protagonist:
                        continue
                    origin = next((c for c, s in t["clubs"].items() if c != club and item in s.get("out", [])), None)
                    moves.append({"date": t["date"], "key": key, "kind": "trade", "from": origin, "to": club,
                                  "id": None, "source": source, "order": (-1, path.as_posix(), i)})
        for i, w in enumerate(data.get("waivers", [])):
            if (w.get("involves_miami") or w.get("club") == "Miami Heat" or not _known(w.get("date"), cutoff)
                    or w["date"] >= SYMMETRIC_FROM):
                continue
            key = match({"player": w.get("player"), "bbr_id": w.get("bbr_id")})
            if key and profiles[key]["name"] != protagonist:
                moves.append({"date": w["date"], "key": key, "kind": "waive", "from": w.get("club"), "to": None,
                              "id": f"{path.stem}-waiver-{i}", "source": source, "order": (-1, path.as_posix(), 100 + i)})


def _expansion_moves(player, cutoff, match, profiles, protagonist, root, moves):
    """Each expansion-draft selection (`<season>/09_Draft/expansion_<year>.json`): the contract assigned to the new club."""
    for path in sorted(player.glob("????-??/09_Draft/expansion_????.json")):
        record = _read(path)
        if not _known(record.get("date"), cutoff):
            continue
        source = _source(path, root, "Expansion draft")
        for i, s in enumerate(record.get("selections", [])):
            key = match({"player": s.get("player"), "bbr_id": s.get("bbr_id")})
            if key and profiles[key]["name"] != protagonist:
                moves.append({"date": record["date"], "key": key, "kind": "trade", "from": s.get("from"),
                              "to": record["club"], "id": None, "label": "expansion draft", "source": source,
                              "order": (0, path.as_posix(), i)})


def _apply_moves(moves, profiles, add, player):
    """Holder changes in date order. A trade or waiver claim assigns the agreement in force (an extension signed and not
    begun travels with it); a 10-day or rest-of-season contract is a new agreement; a waiver, an expired 10-day contract
    or a retirement closes the agreement in force on its date, and a claim reopens the agreement its waiver closed."""
    waivers = {m["id"]: m for m in moves if m["kind"] == "waive"}
    for m in sorted(moves, key=lambda m: (m["date"], m["order"])):
        profile, day, kind = profiles[m["key"]], m["date"], m["kind"]
        entries = profile["_entries"]

        def assign(targets, origin, label):
            for entry in targets:
                # one assignment per holder change: the transaction document replaces an archive of the same change
                entry["_assignments"] = [a for a in entry.get("_assignments", [])
                                         if (a["date"], a["from"], a["to"]) != (day, origin, m["to"])]
                entry["_assignments"].append({"date": day, "from": origin, "to": m["to"], "kind": label,
                                              "transaction_id": m.get("id"), "source": m["source"]})
                if m["source"] not in entry["_sources"]:
                    entry["_sources"].append(m["source"])
        if kind == "trade":
            targets = _holding(entries, day)
            if not targets and m.get("fallback"):
                # Miami's completed trade always moves a contract: the newest begun agreement no dated event closed
                begun = [e for e in entries if _started(e, day) and not (e.get("_ended_on") and e["_ended_on"] <= day)]
                targets = [max(begun, key=lambda e: (_start_key(e), e.get("_as_of") or ""))] if begun else []
            assign(targets, m.get("from"), m.get("label") or "trade")
        elif kind == "claim":
            waived = [e for e in entries if e.get("_closed_by") and e["_closed_by"] == m.get("waiver")]
            for e in waived:
                for field in ("_ended_on", "_close_status", "_closed_by"):
                    e.pop(field, None)
                if e.get("_league_move") and (m.get("contract") or {}).get("until"):
                    e["expiry_date"] = _june_30(m["season"])        # a claimed contract runs the rest of the season
            assign(waived or _holding(entries, day), (waivers.get(m.get("waiver")) or {}).get("from"), "waiver claim")
        elif kind in MOVE_SIGN:
            season, rest = m["season"], kind == "rest_of_season"
            terms = m.get("contract") or {}
            row = {"player": m["player"], "bbr_id": m.get("bbr_id"), "status": "under_contract",
                   "contract_id": f"{m['key']}-{day}-{kind.replace('_', '-')}", "signed_date": day, "signing_team": m["to"],
                   "route": "rest-of-season contract" if rest else "10-day contract", "original_term_seasons": 1,
                   "start_season": season, "end_season": season, "schedule": {season: None},
                   "amount_kind": {season: "contract_salary"},
                   "amount_precision": {season: f"{terms.get('salary') or 'salary'}; amount not recorded"},
                   "expiry_date": _june_30(season) if rest else terms.get("until"), "_league_move": True,
                   "notes": (f"League market {kind.replace('_', '-')} contract with {m['to']} on {day} ({m.get('note') or 'no note'}). "
                             + (f"The move runs it through {terms.get('until')}, the last day of the regular season; a "
                                f"contract for the rest of the season ends with the league year on {_june_30(season)}."
                                if rest else f"It ends on {terms.get('until')}."))}
            add(row, m["to"], m["source"], day, player, False)
        elif kind in MOVE_CLOSE:
            if not (kind == "clear" and any(e.get("_closed_by") == m.get("waiver") for e in entries)):
                # a clear normally finds the agreement its waiver already closed on the waiver's date
                for e in _holding(entries, day):
                    e.update(_ended_on=day, _close_status=MOVE_CLOSE[kind], _closed_by=m.get("id"))
                    if m["source"] not in e["_sources"]:
                        e["_sources"].append(m["source"])
        if kind in MOVE_ASSIGN + MOVE_SIGN and m.get("to") and day >= profile["_team_date"]:
            profile["team"], profile["_team_date"] = m["to"], day


def _display_status(profile, current, contracts, control_status, club_basis):
    """The profile's status on the cutoff, from the agreement in force: never a contract status without one."""
    out = str(club_basis or "").startswith("out of the league")
    if current:
        if out:
            return "out of the league (contract on the books)"     # his real career ended; the club still owes it
        return current["status"] if current["status"] in IN_FORCE else "under_contract"
    # the 2003 expiry rule's "on the 2003-04 roster" holds for that season only
    dated = str(control_status).startswith("on the 2003-04 roster") and profile["as_of"] > "2004-06-30"
    if control_status not in CLAIMS and not dated:
        return control_status
    team = profile.get("team")
    if team and team not in ("Free agent", "Retired", "Abroad"):
        return "rostered; no contract in force in the dated records"
    where = "out of the league" if out else "unsigned free agent"
    last = contracts[0] if contracts else None
    if last and last.get("ended_on"):
        return f"{where} ({str(last['status']).replace('_', ' ')})"      # the agreement's history dates it
    return f"{where} (contract ended)" if last else f"{where} (no contract in force)"


def build_contract_catalog(root, player, clock=None):
    """Build every tracked profile once. clock is an ISO date or state mapping."""
    root = Path(root).resolve()
    player = Path(player)
    player = player.resolve() if player.is_absolute() else (root / player).resolve()
    states = [_read(p) for p in sorted(player.glob("????-??/current_state.json"))]
    states = [s for s in states if _day(s.get("current_date"))]
    state = max(states, key=lambda x: x["current_date"]) if states else {}
    cutoff = clock.get("current_date") if isinstance(clock, dict) else clock
    cutoff = cutoff or state.get("current_date")
    if not _day(cutoff):
        raise ValueError("contract catalog requires an authoritative ISO career date")
    if state.get("current_date") and cutoff > state["current_date"]:
        raise ValueError("contract catalog cannot move beyond the authoritative career date")
    registry = _read(player / "Stats_and_Awards/League/player_registry.json")
    identity = _read(player / "professional_identity.json")
    protagonist = identity.get("display_name", player.name.replace("_", " "))
    players = deepcopy(registry.get("players", [])) if _snapshot(registry, cutoff) else []
    for path in sorted(player.glob("????-??/00_Team/Team/Roster/roster.json")):
        roster = _read(path)
        if _snapshot(roster, cutoff):
            for row in roster.get("players", []):
                if not any(p["name"] == row["name"] for p in players):
                    players.append({"registry_id": register_contract_id(row),
                                    "bbr_id": row.get("bbr_id"), "name": row["name"],
                                    "team_name": roster.get("team"), "position": "/".join(row.get("positions", [])),
                                    "birth_date": row.get("date_of_birth")})
    if not any(p.get("name") == protagonist for p in players):
        players.append({"registry_id": identity.get("player_id", _slug(protagonist)), "name": protagonist})
    profiles, by_name, by_bbr = {}, {}, {}
    for row in players:
        key = row.get("registry_id") or row.get("bbr_id") or _slug(row["name"])
        profiles[key] = {"id": key, "name": row["name"], "team": row.get("team_name"),
                        "as_of": cutoff, "status": "No verified contract record", "identity": deepcopy(row),
                        "_entries": [], "_control": None, "_rights": {}, "_offers": [], "_sources": [],
                        "_team_date": registry.get("as_of", "")}
        by_name[row["name"]] = key
        if row.get("bbr_id"):
            by_bbr[row["bbr_id"]] = key
    def match(row):
        candidate = row.get("player_id")
        if candidate is not None and (candidate in identity.get("aliases", []) or candidate == identity.get("player_id")):
            return by_name.get(protagonist)
        return candidate if candidate in profiles else by_bbr.get(row.get("bbr_id")) or by_name.get(row.get("player") or row.get("name"))
    def add(row, team, source, as_of, season, authoritative=False):
        key = match(row)
        if not key or (_day(row.get("signed_date")) and not _known(row["signed_date"], cutoff)):
            return
        profile = profiles[key]
        entry = deepcopy(row)
        entry.update(_team=team, _as_of=as_of, _sources=_sources(row, source, season, root))
        if authoritative:
            entry["_whole_schedule"] = True     # Miami's sheet and archive carry the agreement's whole schedule
        if row.get("status") == "waived" and _day(row.get("waived_date")):
            entry["_ended_on"] = row["waived_date"]
        previous_control = profile["_control"]
        if (previous_control is None or as_of > previous_control["_as_of"] or
                authoritative and as_of == previous_control["_as_of"]):
            profile["_control"] = entry
            profile["team"] = team
            profile["_team_date"] = as_of
        if row.get("status") in ("free_agent_expiring", "expiring_contract") and not entry.get("expiry_date"):
            prior_season = (row.get("prior_season_salary") or {}).get("season")
            expiry_year = int(prior_season[:4]) + 1 if isinstance(prior_season, str) and re.fullmatch(r"\d{4}-\d{2}", prior_season) else int(as_of[:4]) + (as_of[5:7] > "06")
            entry["expiry_date"] = f"{expiry_year}-06-30"
        profile["_sources"] += [v for v in entry["_sources"] if v not in profile["_sources"]]
        if row.get("status") not in SIGNED:
            return
        if profile["name"] == protagonist and source["path"].startswith("library/"):
            return
        existing = next((e for e in profile["_entries"] if _same_contract(e, entry)), None)
        if existing is None:
            profile["_entries"].append(entry)
        else:
            merged = _merge(entry, existing) if existing["_as_of"] > as_of else _merge(existing, entry)
            profile["_entries"][profile["_entries"].index(existing)] = merged
    for path in sorted((root / "library").glob("*/league/nba_*_contracts.json")):
        data = _read(path)
        if not _snapshot(data, cutoff):
            continue
        for team, club in data.get("clubs", {}).items():
            for row in club.get("players", []):
                if (row.get("player") or row.get("name")) != protagonist:
                    add(row, team, _source(path, root, "Dated league contract inventory"), data["as_of"], path.parent)
    # The summer's dated signings by real clubs (rule 1 skips any involving Miami). Reported total and term are kept;
    # an unreported per-season split stays unknown rather than estimated.
    for path in sorted((root / "library").glob("*/league/nba_*_offseason_transactions.json")):
        data = _read(path)
        for row in data.get("signings", []):
            if (row.get("kind") not in ("signing", "re_sign", "sign_and_trade", "match", "match_declined", "rookie_signing")
                    or row.get("involves_miami") or row.get("to") in (None, "Miami Heat") or not _known(row.get("date"), cutoff)
                    or (row.get("date") or "") >= SYMMETRIC_FROM):
                continue     # from the symmetric league's activation every club signs for itself: real moves never apply
            years = row.get("years") if isinstance(row.get("years"), int) else None
            first = int(str(data.get("season", "2003-04"))[:4]) if str(data.get("season", "")).strip()[:4].isdigit() else 2003
            seasons = [f"{first + i}-{str(first + i + 1)[-2:]}" for i in range(years or 1)]
            entry = {"player": row.get("player"), "bbr_id": row.get("bbr_id"), "status": "under_contract",
                     "signed_date": row["date"], "signing_team": row["to"], "route": row["kind"].replace("_", " "),
                     "original_term_seasons": years, "reported_total": {"amount": row.get("total"), "precision": "reported total"}
                     if row.get("total") else None, "start_season": seasons[0], "end_season": seasons[-1] if years else None,
                     "schedule": {season: None for season in seasons}, "amount_kind": {season: "contract_salary" for season in seasons},
                     "notes": row.get("note")}
            add(entry, row["to"], _source(path, root, "Dated 2003 offseason transaction"), row["date"], path.parent)
    # League rights are evidence of eligibility, not proof of a QO tender.
    for path in sorted((root / "library").glob("*/league/nba_*_free_agent_rights.json")):
        rights = _read(path)
        if _snapshot(rights, cutoff):
            for club in rights.get("clubs", {}).values():
                for row in club.get("free_agents", []):
                    key = match(row)
                    if key and profiles[key]["name"] != protagonist:
                        profiles[key]["_rights"] = deepcopy(row)
                        profiles[key]["_sources"].append(_source(path, root, "Dated league rights evidence"))
    caps = {}
    for season in sorted(player.glob("????-??")):
        for row in _read(season / "00_Team/Finances/league_cap_history.json").get("seasons", []):
            if _known(row.get("published_date"), cutoff) and (not row.get("effective_date") or _known(row["effective_date"], cutoff)):
                if _number(row.get("salary_cap")):
                    caps[row["season"]] = row["salary_cap"]
        path = season / "00_Team/Finances/contract_schedules.json"
        data = _read(path)
        if _snapshot(data, cutoff):
            from .extensions import signed_extensions, with_recorded, without_extension
            known = signed_extensions(root)
            for row in data.get("players", []):
                # an extension's seasons are its own agreement (added below); the row keeps the term it extends, a row an
                # in-season trade copied without its extension record included (`extensions.with_recorded`)
                add(without_extension(with_recorded(row, root, known=known)), data.get("team"),
                    _source(path, root, "Authoritative club contract schedule"), data["as_of"], season, True)
        rights_path = season / "00_Team/Finances/free_agent_rights.json"
        rights = _read(rights_path)
        if _snapshot(rights, cutoff):
            for row in rights.get("players", []):
                key = match(row)
                if key:
                    profiles[key]["_rights"] = deepcopy(row)
                    profiles[key]["_sources"].append(_source(rights_path, root, "Recorded free-agent rights"))
        log_path = season / "01_Free_Agency/Wade_Rookie_Contract/negotiation_log.json"
        for item in _read(log_path).get("entries", []):
            if not _known(item.get("date"), cutoff):
                continue
            key = by_name.get(protagonist)
            if item.get("action") == "sign":
                terms = deepcopy(item.get("terms", {}))
                terms.update(player=protagonist, status="under_contract", signed_date=item["date"],
                             signing_team="Miami Heat", route="rookie_scale", original_term_seasons=3,
                             full_original_schedule=True, start_season=season.name)
                add(terms, "Miami Heat", _source(log_path, root, "Executed rookie signing log"), item["date"], season)
            elif key and item.get("action") in ("offer", "counter", "accept", "decline"):
                profiles[key]["_offers"].append({"date": item["date"], "party": item.get("party"),
                    "action": item["action"], "terms": deepcopy(item.get("terms")),
                    "source": _source(log_path, root, "Unsigned negotiation / player response")})
        for path in sorted((season / "01_Free_Agency/Negotiations").glob("*.json")):
            rec = _read(path)
            signed = (rec.get("signing") or {}).get("date")
            if rec.get("status") != "signed" or not _known(signed, cutoff):
                continue
            terms = (rec.get("agreement") or {}).get("terms", {})
            first = int(season.name[:4])
            schedule = {f"{first+i}-{str(first+i+1)[-2:]}": v for i, v in enumerate(terms.get("schedule", []))}
            row = {"player": rec.get("player"), "bbr_id": rec.get("bbr_id"), "signed_date": signed,
                   "status": "signed_free_agent", "schedule": schedule,
                   "amount_kind": {s: "contract_salary" for s in schedule},
                   "route": (rec.get("agreement") or {}).get("route"), "original_term_seasons": terms.get("years"),
                   "full_original_schedule": True, "start_season": season.name,
                   "guaranteed": {s: (0 if i == len(schedule)-1 and terms.get("last_year_guaranteed") is False else v)
                                  for i, (s, v) in enumerate(schedule.items())}}
            add(row, "Miami Heat", _source(path, root, "Executed free-agent signing"), signed, season)
    supplemental = player / "Contracts/contract_records.json"
    for record in sorted(_read(supplemental).get("records", []), key=lambda r: (r.get("recorded_on", ""), r.get("record_id", ""))):
        row = deepcopy(record.get("contract", {}))
        if not _known(record.get("recorded_on"), cutoff):
            continue
        row.update(player_id=record.get("player_id"), player=record.get("player") or row.get("player"),
                   contract_id=record.get("contract_id") or row.get("contract_id"))
        key = match(row)
        event = record.get("event")
        if event not in ("signed", "amended", "assigned", "recorded_existing", "voided", "released") or not key:
            continue
        existing = next((e for e in profiles[key]["_entries"] if _contract_key(key, e) == row["contract_id"] or _same_contract(e, row)), None)
        if event in ("amended", "assigned", "voided", "released") and existing is None:
            continue
        if event == "assigned" and not _known((record.get("assignment") or {}).get("date"), record["recorded_on"]):
            continue
        if event == "recorded_existing" and row.get("status") not in SIGNED:
            continue
        if event == "signed" and not _known(row.get("signed_date"), cutoff):
            continue
        if event != "signed" and existing is not None:
            row = _merge(existing, row)
        if event in ("voided", "released"):
            row["_ended_on"] = row.get("ended_on") or record["recorded_on"]
        row["sources"] = list(row.get("sources", []))
        if record.get("source"):
            row["sources"].append(record["source"])
        executed = row.get("executed_terms")
        if isinstance(executed, dict):
            row["full_original_schedule"] = True
            row.setdefault("start_season", min(row.get("schedule", {}), default=None))
        assignment = record.get("assignment")
        if event == "assigned" and isinstance(assignment, dict) and _known(assignment.get("date"), cutoff):
            row["current_team"] = assignment.get("to_team")
            row.setdefault("_assignments", []).append({
                "date": assignment["date"], "from": assignment.get("from_team"),
                "to": assignment.get("to_team"), "kind": "trade", "transaction_id": None,
                "source": _source(supplemental, root, "Archived contract assignment")})
        row.setdefault("status", "signed")
        add(row, row.get("current_team") or row.get("signing_team") or (existing or {}).get("_team"),
            _source(supplemental, root, "Dated signed-contract archive"), record["recorded_on"], player, True)
    # The simulated summer market's contracts for every club (`runtime/free_agency_2004.py`), each on its signing date,
    # with the schedule the league contract ledger gives it (raises by route, rookie scale); a summer trade assigns the
    # contract to its new club (below, with every holder change). These are simulated contracts, labelled so; Miami's own
    # sheet stays authoritative.
    moves = []
    _market_contracts(root, player, cutoff, add, match, protagonist, moves)
    # Every signed contract extension (runtime/extensions.py) is its own agreement from its signing date; the agreement
    # it extends stays current until July 1 of the extension's first season (see "current" below).
    from .extensions import catalog_rows
    for row, club, record_path, as_of in catalog_rows(root, cutoff):
        key = match(row)
        if key:
            row["contract_id"] = f"{key}-{row['signed_date']}"
            add(row, club, _source(record_path, root, "Signed contract extension"), as_of, record_path.parent, False)
    _ledger_contracts(root, player, cutoff, add, match, profiles, protagonist)
    _ledger_ends(player, cutoff, profiles)
    _attach_option_decisions(player, cutoff, match, profiles)
    trades = [(path, _read(path)) for path in player.glob("????-??/00_Team/Transactions/Trades/*.json")]
    for path, rec in sorted(trades, key=lambda pair: (str(pair[1].get("applied") or ""), pair[0].name)):
        applied = rec.get("applied")
        if rec.get("status") != "completed" or not _known(applied, cutoff):
            continue
        trade = rec.get("trade", {})
        for side, destination, origin in (("miami_out", trade.get("partner"), "Miami Heat"),
                                           ("miami_in", "Miami Heat", trade.get("partner"))):
            for name in trade.get(side, []):
                if by_name.get(name):
                    moves.append({"date": applied, "key": by_name[name], "kind": "trade", "from": origin, "to": destination,
                                  "id": rec.get("trade_id"), "label": rec.get("kind", "trade"), "fallback": True,
                                  "source": _source(path, root, "Completed contract assignment"), "order": (0, path.name, 0)})
    # The dated league moves of every club (`runtime/league_market.py`, the league's trades), the real league's trades
    # and waivers before the symmetric league and the expansion draft: with the summer and Miami trades above, applied in
    # date order to the agreement in force on each date.
    _league_moves(player, cutoff, match, profiles, protagonist, root, moves)
    _world_moves(root, cutoff, match, profiles, protagonist, moves)
    _expansion_moves(player, cutoff, match, profiles, protagonist, root, moves)
    _apply_moves(moves, profiles, add, player)
    _superseded_ends(profiles, cutoff)
    for profile in profiles.values():
        for entry in profile["_entries"]:
            if entry.get("_assignments"):    # an agreement's club is its latest assignment's, whatever source came last
                entry["_team"] = sorted(entry["_assignments"], key=lambda a: a["date"])[-1]["to"]
    # Each registry player's recorded team is his dated club on the career date (`league_cards.club_on`: real moves to
    # the date, Miami's holdings and departures), the same answer his league card gives.
    from .league_cards import club_on
    for profile in profiles.values():
        ident = profile.get("identity") or {}
        if ident.get("cohort") and profile["name"] != protagonist:
            try:
                on = club_on(ident, cutoff, root=root)
            except (KeyError, ValueError, TypeError):
                continue
            profile["team"] = on.get("club") or "Free agent"
            profile["_club_basis"] = on.get("basis") or ""
    # An expired 2002-03 contract after June 30: researched status first (retired, abroad, unsigned), then the club whose
    # real 2003-04 roster carries him with terms not in the dated records, else a free agent.
    statuses = {}
    if cutoff >= "2003-07-01":
        try:
            from .league_market import _status_on
            statuses = _status_on(cutoff, root)
        except (ValueError, KeyError, OSError):
            statuses = {}
        from .rotations import load_rosters
        try:
            carried = {pl["bbr_id"] for club in load_rosters("2003-04", root).values() for pl in club["players"]}
        except (OSError, KeyError):
            carried = set()
        for profile in profiles.values():
            control = profile.get("_control") or {}
            ident = profile.get("identity") or {}
            if control.get("status") not in ("free_agent_expiring", "expiring_contract") or profile["name"] == protagonist:
                continue
            if any(e.get("status") in SIGNED and (e.get("signed_date") or "") >= "2003-07-01" for e in profile["_entries"]):
                continue
            st = statuses.get(ident.get("bbr_id"))
            if st and st["status"] in ("retired", "abroad", "unsigned_available", "injured_unavailable", "unknown"):
                labels = {"retired": ("Retired", "retired"), "abroad": ("Abroad", "playing outside the NBA"),
                          "unsigned_available": ("Free agent", "unsigned free agent"),
                          "injured_unavailable": (profile.get("team") or "Free agent", "injured, unavailable"),
                          "unknown": ("Free agent", "not with an NBA club (status not established)")}
                profile["team"], label = labels[st["status"]]
                control["status"] = label + f" (researched, {st.get('since') or 'date not recorded'})"
            elif ident.get("bbr_id") in carried:
                control["status"] = "on the 2003-04 roster; contract terms not in the dated records"
            else:
                profile["team"], control["status"] = "Free agent", "unsigned free agent"
    # Miami's register decides its own former and unsigned players: a free agent who signed elsewhere is with that
    # club, and one whose rights Miami keeps is an unsigned free agent with Miami's rights noted. A register snapshot is
    # never newer than the dated club a registry player already has (`club_on` answers on the career date itself), so
    # its "signs with" club names only a player without one; Miami's rights are its latest snapshot's.
    rosters = [(path, _read(path)) for path in sorted(player.glob("????-??/00_Team/Team/Roster/roster.json"))]
    rosters = [(path, roster) for path, roster in rosters if _snapshot(roster, cutoff)]
    for i, (path, roster) in enumerate(rosters):
        for row in roster.get("players", []):
            key = by_bbr.get(row.get("bbr_id")) or by_name.get(row["name"])
            if not key or row["name"] == protagonist:
                continue
            profile = profiles[key]
            control = profile.get("_control") or {}
            dated = "_club_basis" in profile
            if row.get("status") == "signed_elsewhere":
                found = re.search(r"signs with ([A-Z][A-Za-z0-9 .'-]+?) \(", row.get("control", ""))
                if found and not dated:
                    profile["team"] = found.group(1)
                    if control.get("status") in ("free_agent_expiring", "expiring_contract", None) or "Miami" in str(control.get("status")):
                        control["status"] = "signed elsewhere; contract terms not in the dated records"
                        profile["_control"] = control or {"status": control.get("status")}
            elif row.get("status") == "free_agent_rights_held" and (not dated or i == len(rosters) - 1):
                if not dated:
                    profile["team"] = "Free agent"
                control["status"] = "unsigned free agent; Miami holds his rights"
                profile["_control"] = control
    from .seasons import club_name, live_season_on
    live = live_season_on(cutoff, root) if cutoff >= "2003-07-01" else "2003-04"
    output = []
    for profile in profiles.values():
        entries = profile.pop("_entries")
        control = profile.pop("_control") or {}
        club_basis = profile.pop("_club_basis", None)
        profile["control"] = {k: deepcopy(control.get(k)) for k in ("status", "current_cap_hold", "rookie_scale_reference",
                              "schedule", "amount_kind", "notes", "candidate_2003_04")}
        profile["control"]["rights"] = profile.pop("_rights")
        profile["control"]["unsigned_responses"] = profile.pop("_offers")
        profile["sources"] = profile.pop("_sources")
        profile.pop("_team_date")
        # A signed future extension does not replace the agreement still in force; the newest begun agreement is the
        # current one while it is in force (a dated closing, its final season, an option that removed its season).
        live_entries = {id(e) for e in entries if _started(e, cutoff) and not _ended(e, cutoff)}
        contracts = [(_normal_contract(profile["id"], e, cutoff, caps), id(e) in live_entries, _started(e, cutoff)) for e in entries]
        contracts.sort(key=lambda t: (t[0]["signed_on"] or ((t[0]["start_season"] or min([r["season"] for r in t[0]["salary_rows"]] or [""]))[:4] + "-07-01"),
                                      t[0]["record_as_of"] or "", t[0]["id"]), reverse=True)
        commenced = [t for t in contracts if t[2]]
        current = commenced[0][0] if commenced and commenced[0][1] else None
        for c, in_force, _ in contracts:
            if in_force and c["team"]:     # a club renamed since (seasons.club_name) holds the agreement under its name now
                c["team"] = club_name(c["team"], live)
        contracts = [t[0] for t in contracts]
        profile["history"] = contracts
        profile["current"] = current
        profile["status"] = _display_status(profile, current, contracts, control.get("status") or profile["status"], club_basis)
        stale = profile["control"]["status"] in CLAIMS | CLOSED or str(profile["control"]["status"]).startswith("on the 2003-04 roster")
        if stale and profile["status"] != profile["control"]["status"]:
            profile["control"]["status"] = profile["status"]       # the control row reads the cutoff's position too
        profile["coverage"] = {"history_complete": False, "recorded_contract_count": len(contracts),
            "current_contract_verified": profile["current"] is not None, "as_of": cutoff,
            "note": "Only dated recorded contracts are shown. Earlier contracts, missing amounts, riders and league transactions outside the dated records are not reconstructed."}
        output.append(profile)
    return {"schema_version": 1, "as_of": cutoff, "default_player_id": by_name.get(protagonist),
            "players": sorted(output, key=lambda p: (p["name"], p["id"]))}


def _href(source, page, root):
    if source.get("href"):
        return {"label": source["label"], "href": source["href"]}
    target = (root / source["path"]).resolve()
    if root not in target.parents:
        raise ValueError("contract source outside repository")
    return {"label": source["label"], "href": Path(os.path.relpath(target, page.parent)).as_posix()}


def _table(title, columns, rows, **extra):
    return {"title": title, "columns": columns, "rows": rows, **extra}


def contract_payload(profile, *, page, root):
    """Page-aware rich sections for one profile, without re-reading sources."""
    root = Path(root).resolve()
    page = Path(page)
    page = page if page.is_absolute() else root / page
    def sources(items):
        result = []
        for item in items:
            value = _href(item, page, root)
            if value not in result:
                result.append(value)
        return result
    def render(contract):
        c = deepcopy(contract)
        c["title"] = f"{profile['name']} · {c['signed_on'] or 'existing contract; signing date not recorded'}"
        c["summary"] = "Recorded terms only. Unreported amounts and clauses remain unknown; conditional years are identified separately."
        c["metrics"] = [
            {"label": "Signing date", "value": _text(c["signed_on"])},
            {"label": "Original term", "value": f"{c['original_term_seasons']} seasons" if c["original_term_seasons"] else "Not recorded"},
            {"label": "Reported original value", "value": _money(c["reported_total"].get("amount")), "detail": _text(c["reported_total"].get("precision"))},
            {"label": "Original AAV", "value": _money(c["original_aav"]), "detail": "Requires complete original schedule and term."},
            {"label": "Recorded schedule subtotal", "value": _money(c["scheduled_subtotal"]), "detail": "Includes conditional years; excludes prior-salary reference. Not career earnings or original value."},
            {"label": "Missing scheduled amounts", "value": str(c["scheduled_unknown_count"])}]
        financial = [[r["season"], _money(r["salary"]), _money(r["base_salary"]), _money(r["cap_hit"]),
                      _money(r["guaranteed"]), _money(r["likely_incentives"]), _money(r["unlikely_incentives"]),
                      _money(r["salary_cap"]), f"{r['cap_percent']:.2f}%" if r["cap_percent"] is not None else "Not recorded",
                      _text(r["amount_kind"]), _text(r["precision"]), _text(r["condition"])] for r in c["salary_rows"]]
        c["sections"] = [
            _table("Contract identity and execution", ["Field", "Recorded detail"], [
                ["Assigned club", _text(c["team"])], ["Signing club", _text(c["signing_team"])],
                ["Contract ID", c["id"]], ["Signing route / evidence basis", _text(c["type"])],
                ["Signing date", _text(c["signed_on"])], ["Verified first season", _text(c["start_season"])],
                ["Verified final season", _text(c["end_season"])], ["Verified expiry date", _text(c["expiry_date"])],
                ["Ended on (dated event)", _text(c.get("ended_on"))],
                ["Status", _text(c["status"])], ["Contract wording", _text(c["contract_text"])]]),
            _table("Salary by season", ["Season", "Recorded salary", "Base salary", "Cap hit", "Guaranteed",
                "Likely incentives", "Unlikely incentives", "Published season cap", "Cap hit / cap", "Amount kind", "Precision", "Condition"],
                financial, notice="Recorded salary is not automatically base salary, cap hit, cash paid or guaranteed compensation. Missing values are unknown. Only the same season's published and activated cap is displayed."),
            _table("Options and decision deadlines", ["Season", "Option", "Amount", "Decision deadline", "Outcome", "Outcome date"],
                [[_money(o.get(k)) if k == "amount" else _text(o.get(k)) for k in ("season", "type", "amount", "deadline", "outcome", "outcome_date")] for o in c["options"]],
                notice="An option amount is conditional. An outcome appears only from its dated decision (League/option_decisions.json or the club's record); no exercise or decline is assumed."),
            _table("Additional recorded annual compensation", ["Season", "Signing bonus", "Dead cap", "Buyout"],
                [[r["season"], _money(r["signing_bonus"]), _money(r["dead_cap"]), _money(r["buyout"])] for r in c["salary_rows"]],
                notice="Missing bonus, dead-cap and buyout fields do not establish zero liability or payment."),
            _table("Guarantees, incentives and payment terms", ["Term", "Recorded detail"], [
                ["Guarantee rider / amendment", _text(c["guarantee"])]] +
                [[key.replace("_", " ").capitalize(), _text(c["terms"][key])] for key in
                 ("guarantee_triggers", "guarantee_date", "waiver_deadline", "bonus_terms", "payment_schedule", "buyout_terms", "promise", "percent_of_scale")]),
            _table("Free agency, Bird rights and trade terms", ["Term", "Recorded detail"],
                [[key.replace("_", " ").capitalize(), _text(c["terms"][key])] for key in
                 ("free_agency", "bird_rights", "no_trade_clause", "trade_consent", "trade_restrictions", "trade_kicker", "trade_clauses", "base_year_compensation")],
                notice="No clause, consent right, unrestricted/restricted status or future qualifying-offer outcome is inferred from a missing field."),
            _table("Assignment history", ["Date", "From", "To", "Transaction", "Source"],
                [[a["date"], _text(a["from"]), _text(a["to"]), _text(a["transaction_id"]), _href(a["source"], page, root)] for a in c["assignment_history"]],
                notice="A trade assigns this contract; it does not create a duplicate signing."),
            {"title": "Evidence and coverage", "body": [_text(c["notes"]), profile["coverage"]["note"]]}]
        c["sources"] = sources(c["sources"])
        return c
    current = render(profile["current"]) if profile["current"] else None
    control = profile["control"]
    rights = control["rights"]
    sections = [
        _table("Current control and contract coverage", ["Field", "Dated record"], [
            ["Player", profile["name"]], ["Club / rights baseline", _text(profile["team"])],
            ["Control status", _text(control["status"])],
            ["Executed current contract", "Recorded" if current else "No verified current signed contract"],
            ["Recorded cap hold", _money(control["current_cap_hold"])], ["Coverage", profile["coverage"]["note"]]],
            notice="Draft rights and cap holds are not salaries or executed contracts. A roster baseline does not certify an active contract."),
        _table("Unsigned or unresolved salary evidence", ["Season", "Amount", "Record kind"],
            [[s, _money(v), _text((control.get("amount_kind") or {}).get(s))] for s, v in sorted((control.get("schedule") or {}).items())] if not current else [],
            notice=_text(control.get("notes")) if not current else "Current signed salary detail appears in the contract below."),
        _table("Draft-rights scale reference", ["Reference", "Recorded value"],
            [[key.replace("_", " "), _money(value) if re.fullmatch(r"\d{4}-\d{2}", key) else _text(value)]
             for key, value in (control.get("rookie_scale_reference") or {}).items()] if not current else [],
            notice="A scale reference and permitted percentage range are negotiation boundaries, not an offer, signed salary or guarantee."),
        _table("Recorded free-agent rights", ["Field", "Recorded detail"], [
            ["Bird classification", _text(rights.get("bird_status", rights.get("bird_class")))],
            ["Bird classification basis", _text(rights.get("bird_basis"))],
            ["Recorded Bird-clock seasons", _text(rights.get("seasons_with_miami_for_bird", rights.get("bird_clock_seasons")))],
            ["Restricted-free-agency eligibility", _text(rights.get("restricted_free_agency_eligible", rights.get("rfa_eligible")))],
            ["Qualifying-offer reference amount", _money(rights.get("qualifying_offer", rights.get("qualifying_offer_amount")))],
            ["Qualifying-offer basis", _text(rights.get("qualifying_offer_basis"))],
            ["Free-agent cap hold reference", _money(rights.get("cap_hold", rights.get("cap_hold_amount")))],
            ["Qualifying offer actually tendered", _text(rights.get("qualifying_offer_tendered"))],
            ["Tender date", _text(rights.get("qualifying_offer_date"))], ["Renounced", _text(rights.get("renounced"))]],
            notice="Eligibility and a reference amount do not establish a tendered qualifying offer or completed free-agency outcome."),
        _table("Unsigned negotiation and player responses", ["Date", "Party", "Action", "Terms", "Source"],
            [[o["date"], _text(o["party"]), o["action"], _text(o["terms"]), _href(o["source"], page, root)] for o in control["unsigned_responses"]],
            notice="An offer, counteroffer or acceptance is not an executed contract.")]
    return {"as_of": profile["as_of"], "player_id": profile["id"], "status": profile["status"],
            "summary": f"{profile['name']}: {profile['status'].replace('_', ' ')}. Evidence cutoff: {profile['as_of']}.",
            "current": current, "history": [render(c) for c in profile["history"]],
            "metrics": [{"label": "Career date", "value": profile["as_of"]},
                        {"label": "Recorded contracts", "value": str(len(profile["history"])), "detail": "Partial archive; current contract included once."},
                        {"label": "History coverage", "value": "Partial"}],
            "sections": sections, "sources": sources(profile["sources"]), "coverage": deepcopy(profile["coverage"])}
