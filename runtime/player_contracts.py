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
          "expiring_contract", "signed_elsewhere", "renounced", "voided", "waived"}
CLOSED = {"team_option_declined", "player_option_declined", "released", "expired",
          "retired_salary_on_books", "signed_elsewhere", "renounced", "voided", "waived"}
NON_SALARY = {"draft_hold", "unsigned_rights"}
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
    return bool(shared) and all(old["schedule"][s] == new["schedule"][s] for s in shared)


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
    options = deepcopy(entry.get("options", []))
    for season, kind in entry.get("amount_kind", {}).items():
        if kind not in ("team_option", "player_option", "early_termination_option") or any(o.get("season") == season for o in options):
            continue
        option = {"season": season, "type": kind, "amount": _number(schedule.get(season)),
                  "deadline": entry.get("fourth_year_option_deadline") if kind == "team_option" else None,
                  "outcome": None, "outcome_date": None}
        if entry.get("status") in (f"{kind}_exercised", f"{kind}_declined"):
            option.update(outcome=entry["status"].split("_")[-1],
                          outcome_date=entry.get("option_decision_date"), evidence_as_of=entry.get("_as_of"))
        options.append(option)
    for option in options:
        if option.get("outcome") is not None and option.get("outcome_date") and not _known(option["outcome_date"], cutoff):
            option.update(outcome=None, outcome_date=None)
    total = entry.get("reported_total")
    total = deepcopy(total) if isinstance(total, dict) else {"amount": _number(total), "precision": None}
    scheduled = [r["salary"] for r in rows if r["amount_kind"] != "prior_season_salary_reference"]
    complete = bool(entry.get("full_original_schedule") is True and scheduled and all(v is not None for v in scheduled))
    if complete and total.get("amount") is None:
        total = {"amount": sum(scheduled), "precision": "complete recorded schedule; includes conditional option years"}
    term = entry.get("original_term_seasons")
    original_aav = (total.get("amount") / term if complete and type(term) is int and term == len(scheduled) and term > 0
                    and total.get("amount") is not None else None)
    expiry = entry.get("expiry_date")
    if not expiry and isinstance(entry.get("end_season"), str) and re.fullmatch(r"\d{4}-\d{2}", entry["end_season"]):
        expiry = f"{int(entry['end_season'][:4]) + 1}-06-30"
    return {"id": _contract_key(player_id, entry), "status": entry.get("status"),
        "team": entry.get("_team"), "signing_team": entry.get("signing_team"),
        "signed_on": entry.get("signed_date"), "start_season": entry.get("start_season"),
        "end_season": entry.get("end_season"), "expiry_date": expiry,
        "type": entry.get("route") or entry.get("basis") or "Existing contract record",
        "original_term_seasons": term, "reported_total": total, "original_aav": original_aav,
        "scheduled_subtotal": sum(v for v in scheduled if v is not None) if scheduled else None,
        "scheduled_unknown_count": sum(v is None for v in scheduled), "full_original_schedule": complete,
        "salary_rows": rows, "options": options, "guarantee": deepcopy(entry.get("guarantee")),
        "terms": {key: deepcopy(entry.get(key)) for key in TERM_FIELDS},
        "notes": entry.get("notes"), "contract_text": entry.get("contract_text"),
        "assignment_history": deepcopy(entry.get("_assignments", [])),
        "sources": deepcopy(entry.get("_sources", [])), "record_as_of": entry.get("_as_of")}


from .league_book import SYMMETRIC_FROM                                       # noqa: E402  (real moves stop applying)
MARKET_SIGNINGS = ("signing", "re_sign", "offer_sheet_matched", "qualifying_offer_accepted", "camp_signing", "rookie_scale_signing")


def _market_contracts(root, player, cutoff, add, profiles, match, protagonist):
    from .free_agency_2004 import NEW, RECORD
    from .league_contracts import read as read_ledger, schedule_for
    from .seasons import dates
    path = Path(root) / RECORD
    if not path.is_file():
        return
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
            schedule = dict(lg["schedule"]) if lg.get("schedule") and lg.get("club") else schedule_for(salary, years, NEW, route)
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
            if not key:
                continue
            profile = profiles[key]
            eligible = [x for x in profile["_entries"] if not x.get("signed_date") or x["signed_date"] <= e["date"]]
            if eligible:
                entry = max(eligible, key=lambda x: (x.get("signed_date") or "", x.get("_as_of") or ""))
                entry.setdefault("_assignments", []).append({"date": e["date"], "from": e.get("from"), "to": e["club"],
                                                             "kind": "trade", "transaction_id": e.get("deal"), "source": source})
                entry["_team"] = e["club"]
                entry["_sources"].append(source)
            if e["date"] >= profile["_team_date"]:
                profile["team"], profile["_team_date"] = e["club"], e["date"]


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
                    players.append({"registry_id": row.get("bbr_id") or row.get("id") or _slug(row["name"]),
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
            for row in data.get("players", []):
                add(row, data.get("team"), _source(path, root, "Authoritative club contract schedule"), data["as_of"], season, True)
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
    # contract to its new club. These are simulated contracts, labelled so; Miami's own sheet stays authoritative.
    _market_contracts(root, player, cutoff, add, profiles, match, protagonist)
    trades = [(path, _read(path)) for path in player.glob("????-??/00_Team/Transactions/Trades/*.json")]
    for path, rec in sorted(trades, key=lambda pair: (str(pair[1].get("applied") or ""), pair[0].name)):
        applied = rec.get("applied")
        if rec.get("status") != "completed" or not _known(applied, cutoff):
            continue
        trade = rec.get("trade", {})
        for side, destination, origin in (("miami_out", trade.get("partner"), "Miami Heat"),
                                           ("miami_in", "Miami Heat", trade.get("partner"))):
            for name in trade.get(side, []):
                key = by_name.get(name)
                if not key:
                    continue
                profile = profiles[key]
                eligible = [e for e in profile["_entries"] if not e.get("signed_date") or e["signed_date"] <= applied]
                if eligible:
                    entry = max(eligible, key=lambda e: (e.get("signed_date") or "", e.get("_as_of") or ""))
                    assignment = {"date": applied, "from": origin, "to": destination,
                                  "kind": rec.get("kind", "trade"), "transaction_id": rec.get("trade_id"),
                                  "source": _source(path, root, "Completed contract assignment")}
                    # Prefer the transaction document to an archive of the same assignment.
                    entry["_assignments"] = [a for a in entry.get("_assignments", []) if
                        (a["date"], a["from"], a["to"]) != (applied, origin, destination)]
                    entry["_assignments"].append(assignment)
                    entry["_team"] = destination
                    entry["_sources"].append(assignment["source"])
                if applied >= profile["_team_date"]:
                    profile["team"] = destination
                    profile["_team_date"] = applied
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
    # club, and one whose rights Miami keeps is an unsigned free agent with Miami's rights noted.
    for path in sorted(player.glob("????-??/00_Team/Team/Roster/roster.json")):
        roster = _read(path)
        if not _snapshot(roster, cutoff):
            continue
        for row in roster.get("players", []):
            key = by_bbr.get(row.get("bbr_id")) or by_name.get(row["name"])
            if not key or row["name"] == protagonist:
                continue
            profile = profiles[key]
            control = profile.get("_control") or {}
            if row.get("status") == "signed_elsewhere":
                found = re.search(r"signs with ([A-Z][A-Za-z0-9 .'-]+?) \(", row.get("control", ""))
                if found:
                    profile["team"] = found.group(1)
                    if control.get("status") in ("free_agent_expiring", "expiring_contract", None) or "Miami" in str(control.get("status")):
                        control["status"] = "signed elsewhere; contract terms not in the dated records"
                        profile["_control"] = control or {"status": control.get("status")}
            elif row.get("status") == "free_agent_rights_held":
                profile["team"] = "Free agent"
                control["status"] = "unsigned free agent; Miami holds his rights"
                profile["_control"] = control
    output = []
    for profile in profiles.values():
        entries = profile.pop("_entries")
        control = profile.pop("_control") or {}
        profile["status"] = control.get("status", profile["status"])
        profile["control"] = {k: deepcopy(control.get(k)) for k in ("status", "current_cap_hold", "rookie_scale_reference",
                              "schedule", "amount_kind", "notes", "candidate_2003_04")}
        profile["control"]["rights"] = profile.pop("_rights")
        profile["control"]["unsigned_responses"] = profile.pop("_offers")
        profile["sources"] = profile.pop("_sources")
        profile.pop("_team_date")
        contracts = [_normal_contract(profile["id"], e, cutoff, caps) for e in entries]
        contracts.sort(key=lambda c: (c["signed_on"] or "", c["record_as_of"] or "", c["id"]), reverse=True)
        profile["history"] = contracts
        # A signed future extension does not replace the agreement still in force.
        commenced = [c for c in contracts if not c["start_season"] or c["start_season"][:4] + "-07-01" <= cutoff]
        current = commenced[0] if commenced else None
        if current and current["status"] in ("team_option_declined", "player_option_declined"):
            declined = [o["season"] for o in current["options"] if o.get("outcome") == "declined"]
            # Declining a later option leaves earlier base seasons in force.
            if declined and cutoff <= min(declined)[:4] + "-06-30":
                pass
            else:
                current = None
        elif current and (current["status"] in CLOSED or (current["expiry_date"] and current["expiry_date"] < cutoff)):
            current = None
        profile["current"] = current
        profile["coverage"] = {"history_complete": False, "recorded_contract_count": len(contracts),
            "current_contract_verified": profile["current"] is not None, "as_of": cutoff,
            "note": "Only dated recorded contracts are shown. Earlier contracts, missing amounts, riders and unrecorded league transactions are not reconstructed."}
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
                ["Status", _text(c["status"])], ["Contract wording", _text(c["contract_text"])]]),
            _table("Salary by season", ["Season", "Recorded salary", "Base salary", "Cap hit", "Guaranteed",
                "Likely incentives", "Unlikely incentives", "Published season cap", "Cap hit / cap", "Amount kind", "Precision", "Condition"],
                financial, notice="Recorded salary is not automatically base salary, cap hit, cash paid or guaranteed compensation. Missing values are unknown. Only the same season's published and activated cap is displayed."),
            _table("Options and decision deadlines", ["Season", "Option", "Amount", "Decision deadline", "Outcome", "Outcome date"],
                [[_money(o.get(k)) if k == "amount" else _text(o.get(k)) for k in ("season", "type", "amount", "deadline", "outcome", "outcome_date")] for o in c["options"]],
                notice="An option amount is conditional. No exercise or decline is assumed."),
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
