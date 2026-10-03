"""Write-back of Miami's transactions into the canonical records (docs/front_office_design.md 5.6).

One adapter writes each signing, renouncement, option outcome and arrival
exactly once: the contract on `contract_schedules.json`, the holding on
`holdings.json` (conflict rule 2), the register and a player card, the finance
summary and cap sheet, the depth chart as an unassigned arrival, the phase note
and `current_state.json`. Everything is computed first and written last, so a
failed write leaves the records untouched. Nothing here draws chance or decides
anything; it records what the front office and the engine already decided.
"""
from datetime import date
from copy import deepcopy
import json
from pathlib import Path

from .valuation import read
from .contract_archive import archive_contract, archive_previous_contract

ROOT = Path(__file__).resolve().parents[1]
SEASON = "2003-04"
TEAM = Path(f"career/Dwyane_Wade/{SEASON}/00_Team")
PHASE = Path(f"career/Dwyane_Wade/{SEASON}/01_Free_Agency")
STATE = Path(f"career/Dwyane_Wade/{SEASON}/current_state.json")
HORIZON = ["2003-04", "2004-05", "2005-06", "2006-07", "2007-08", "2008-09", "2009-10", "2010-11"]
ACTIVE_STATUSES = ("under_contract", "under_contract_guarantee_amended", "team_option_exercised", "player_option_exercised",
                   "signed_free_agent", "re_signed")
CLOSED_STATUSES = ("team_option_declined", "player_option_declined", "renounced", "released", "traded", "signed_elsewhere")


def slug(name):
    return name.lower().replace("'", "").replace(".", "").replace(" ", "_")


def long_date(day):
    d = date.fromisoformat(day)
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def dump(path, data):
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


class Writer:
    """Collects file writes and applies them together."""

    def __init__(self, root=ROOT):
        self.root, self.files, self.texts = Path(root), {}, {}

    def load(self, rel):
        rel = Path(rel)
        if rel not in self.files:
            self.files[rel] = read(rel, self.root)
        return self.files[rel]

    def text(self, rel, content):
        self.texts[Path(rel)] = content

    def commit(self):
        for rel, data in self.files.items():
            (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
            dump(self.root / rel, data)
        for rel, content in self.texts.items():
            (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.root / rel).write_text(content, encoding="utf-8")
        written = sorted(str(p) for p in list(self.files) + list(self.texts))
        self.files, self.texts = {}, {}
        return written


# -- building blocks -------------------------------------------------------------------------------
def note_event(writer, rel, day, text, status="in_progress"):
    """Append a dated line under '## Events' of a phase note and move its status."""
    path = writer.root / rel
    content = writer.texts.get(Path(rel)) or path.read_text(encoding="utf-8")
    content = content.replace("status: not_started", f"status: {status}", 1)
    head, _, tail = content.partition("## Consequences")
    if not head.rstrip().endswith("## Events") and not head.rstrip().endswith("."):
        head = head.rstrip() + "\n"
    line = f"- {day}: {text}\n"
    if line in head:
        return
    head = head.rstrip() + "\n" + line + "\n"
    writer.text(rel, head + "## Consequences" + tail)


def set_state(writer, day, area="01_Free_Agency", note="01_Free_Agency/note.md", last_event=None, **fields):
    state = writer.load(STATE)
    state.update(current_date=day, current_area=area, current_note=note, **fields)
    if last_event:
        state["last_closed_event"] = last_event
    return state


def league_identity(root, bbr_id):
    """Identity from the league baseline (position, birth date, jersey, photo) for a new Miami player."""
    for club, entry in read("library/2003/league/nba_2003_end_of_season.json", root)["clubs"].items():
        for p in entry["players"]:
            if p.get("bbr_id") == bbr_id:
                return dict(p, club=club)
    for p in read("career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json", root)["players"]:
        if p.get("bbr_id") == bbr_id:
            return {"player_id": p["name"], "position": p.get("position"), "birth_date": p.get("birth_date"), "club": p.get("team_name")}
    return {}


def player_card(name, identity, day, control, source_rel, prior_stats=None):
    """A new Miami player card in the template's section order; grades stay unassessed until evidence exists."""
    pos = (identity.get("position") or "N/A").replace("-", " / ")
    born = identity.get("birth_date")
    age = (date.fromisoformat(day).year - int(born[:4]) - ((date.fromisoformat(day).month, date.fromisoformat(day).day) < (int(born[5:7]), int(born[8:10])))) if born else "N/A"
    photo = ""
    if identity.get("headshot_url"):
        photo = (f"<!-- photo -->\n<img src=\"{identity['headshot_url']}\" alt=\"{name}\" width=\"160\">\n\n"
                 f"*Photo: {identity.get('headshot_credit', 'see source')}, {identity.get('headshot_license', 'license on file')}.*\n<!-- /photo -->\n\n")
    stats = ""
    if prior_stats:
        t = prior_stats["totals"]
        g = max(t["games"], 1)
        fg = f"{t['field_goals_made'] / t['field_goals_attempted']:.3f}" if t["field_goals_attempted"] else "N/A"
        tp = f"{t['three_pointers_made'] / t['three_pointers_attempted']:.3f}" if t.get("three_pointers_attempted") else "N/A"
        ft = f"{t['free_throws_made'] / t['free_throws_attempted']:.3f}" if t["free_throws_attempted"] else "N/A"
        stats = (f"| 2002-03 | {prior_stats.get('team', identity.get('club', 'N/A'))} | {t['games']} | N/A | {t['minutes'] / g:.1f} | {t['points'] / g:.1f} | "
                 f"{(t['offensive_rebounds'] + t['defensive_rebounds']) / g:.1f} | {t['assists'] / g:.1f} | {t['steals'] / g:.1f} | {t['blocks'] / g:.1f} | "
                 f"{t['turnovers'] / g:.1f} | {fg} | {tp} | {ft} |\n")
    return f"""{photo}# {name} | {SEASON} Player Profile

**Team:** Miami Heat · **League:** NBA · **Position:** {pos}  
**Age at assessment:** {age} · **Height:** N/A · **Weight:** N/A  
**Opening assessment:** {long_date(day)} · **Statistics through:** {long_date(day)}

**Contract/control:** {control} [Finance record](../../Finances/cap_sheet.md).

## Scouting report

**Role:** Arrival on {long_date(day)}; Miami's coaching staff has not assigned a role. The depth chart lists him as an unassigned arrival.

**Offense:** Unassessed by Miami's staff; prior production is in the statistics below.

**Defense:** Unassessed.

## Player grades

Unassessed. Statistical estimates can be generated from his 2002-03 record with `scripts/import_veteran_stats.py` once the card is included in the import.

## Changes and coaching notes

| Date | Finding and effect on role or grade | Evidence |
| --- | --- | --- |
| {long_date(day)} | Joined Miami. Card opened from the league baseline and the signing record; no role assigned. | [Signing record]({source_rel}) |

## Sources and uncertainty

- **Assessment evidence:** [League baseline](../../../../../../library/2003/league/nba_2003_end_of_season.json), [signing record]({source_rel}).
- **Not yet established:** height, weight, role, staff grades.

<!-- yearly-statistics:start -->

## Regular-season statistics by year

G and GS are counts. MIN and all other counting statistics are per game. Percentages use total makes divided by total attempts.

**Coverage:** {'2002-03 from the league record; ' if stats else ''}2003-04 not started.

| Season | Team(s) | G | GS | MIN | PTS | REB | AST | STL | BLK | TOV | FG% | 3P% | FT% |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{stats}| {SEASON} | Miami Heat | 0 | 0 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |

Source: [2002-03 league record](../../../../../../library/2003/league/nba_2002_03_player_stats.json); 2003-04 from closed Miami game results.

## Playoff statistics by year

**Coverage:** No playoff appearances recorded for Miami.

<!-- yearly-statistics:end -->

## Awards and honors

| Season / year | Award or honor | Source |
| --- | --- | --- |
| — | No verified awards or honors recorded on this card. | — |
"""


# -- transactions -------------------------------------------------------------------------------------
def apply_june30(writer, package, outcomes, day="2003-06-30"):
    """Record the June 30 option and qualifying-offer outcomes. `outcomes` maps event_id to the drawn option."""
    sheet, roster, rights = writer.load(TEAM / "Finances/contract_schedules.json"), writer.load(TEAM / "Team/Roster/roster.json"), writer.load(TEAM / "Finances/free_agent_rights.json")
    holdings = writer.load(TEAM / "Team/Roster/holdings.json")
    lines = []
    for d in package["decisions"]:
        final = d["decision"]
        if d["status"] == "pending_engine_draw":
            event = f"{day}-{slug(d['player'])}-{d['kind'].replace('_', '-')}-wade-request"
            if event not in outcomes:
                raise ValueError(f"{event}: not drawn yet")
            final = outcomes[event]
        d["final"] = final
        if d["kind"] == "team_option":
            status = "team_option_exercised" if final == "exercise" else "team_option_declined"
            _set_status(sheet, roster, d["player"], status, f"Team option {final}d on June 30, 2003 (front office rule; see June_30/front_office_decisions.json).")
            if final == "decline":
                _close_holding(holdings, d["player"], "2003-07-01")
            lines.append(f"{d['player']}: team option {final}d")
        elif d["kind"] == "qualifying_offer":
            r = next(p for p in rights["players"] if p["player"] == d["player"])
            r["qualifying_offer_tendered"] = final == "tender"
            r["qualifying_offer_date"] = day if final == "tender" else None
            if final != "tender":
                r["restricted_free_agency_eligible"] = False
            lines.append(f"{d['player']}: qualifying offer {'tendered' if final == 'tender' else 'not tendered'}")
    for p in sheet["players"]:
        if p["status"] == "player_option_pending":
            event = f"{day}-{slug(p['player'])}-player-option"
            if event not in outcomes:
                raise ValueError(f"{event}: not drawn yet")
            final = outcomes[event]
            status = "player_option_exercised" if final == "exercise" else "player_option_declined"
            _set_status(sheet, roster, p["player"], status, f"Player option {final}d on June 30, 2003 (engine draw {event}).")
            if final == "decline":
                _close_holding(holdings, p["player"], "2003-07-01")
            lines.append(f"{p['player']}: player option {final}d (his decision, drawn)")
    sheet["as_of"] = roster["as_of"] = day
    note_event(writer, PHASE / "note.md", day, "June 30 decisions: " + "; ".join(lines) + ". Record: `June_30/front_office_decisions.json`.")
    set_state(writer, day, last_event=f"{day}-miami-option-and-qualifying-offer-decisions")
    return lines


def _set_status(sheet, roster, name, status, control):
    p = next(p for p in sheet["players"] if p["player"] == name)
    p["status"] = status
    r = next(p for p in roster["players"] if p["name"] == name)
    r["status"], r["control"] = status, control


def _close_holding(holdings, name, until):
    for e in holdings["entries"]:
        if e["player"] == name and e["until"] is None:
            e["until"] = until


def renounce(writer, names, day, reason):
    """Renounce free agents: their holds and Bird rights go until the next June 30."""
    rights = writer.load(TEAM / "Finances/free_agent_rights.json")
    done = []
    for p in rights["players"]:
        if p["player"] in names and not p.get("renounced"):
            p["renounced_reason"] = reason
            depart(writer, p["player"], day, "renounced", f"renounced: hold and Bird rights released until the next June 30 ({reason})")
            done.append(p["player"])
    return done


def league_prior_salary(root, bbr_id):
    """A free agent's 2002-03 salary from the league rights file (the inventory's prior-salary evidence)."""
    for club in read("library/2003/league/nba_2003_free_agent_rights.json", root)["clubs"].values():
        for p in club["free_agents"]:
            if p.get("bbr_id") == bbr_id:
                return p.get("prior_salary_2002_03")
    return None


def planning_cap(root, day):
    from .market import Market
    return Market(day, root).planning_cap(day)


def base_year_compensation(sheet, rights, name, route, first_year, prior, cap, day):
    """The base-year flag attached at a Miami signing (trades.base_year_compensation): a Bird or Early Bird
    re-signing at a raise over 20% while Miami is over the cap once the new contract is counted (holds
    without the player's own hold). Never re-derived in a later trade."""
    if route not in ("bird", "early_bird"):
        return {"applies": False, "status": f"not a Bird or Early Bird re-signing ({route}); base-year compensation does not apply"}
    committed = counted_salary(sheet["players"], day)
    holds = sum(p.get("cap_hold") or 0 for p in rights["players"]
                if p["player"] != name and not (p.get("renounced") or p.get("signed_elsewhere") or p.get("re_signed")))
    over = committed + holds + first_year > cap
    raise_over = bool(prior) and first_year > prior * 1.2
    applies = over and raise_over
    return {"applies": applies, "status": ("inferred for 1999: re-signed with Bird or Early Bird rights at a raise over 20% by a club over the cap "
                                           f"(raise {'over' if raise_over else 'within'} 20% of ${prior or 0:,}; Miami ${committed + holds + first_year:,} "
                                           f"against the ${cap:,} cap with the contract counted); attached at the signing")}


def sign(writer, negotiation, day, *, via_trade=None, cap=None):
    """Write a contract agreed on the desk into every canonical record.

    `via_trade` is the accepted sign-and-trade record. For an acquisition the incumbent signed the
    player on the agreed terms and traded him, so his entry carries route `sign_and_trade`, the
    acquisition and the base-year compensation the incumbent's cap position attached. For Miami's own
    sign-and-trade-out Miami signs him with his Bird rights and trades him in the same transaction
    (`apply_trade` departs him in the same commit): the entry carries the base-year flag the proposal
    attached from Miami's ledger and no Miami holding opens, because he never plays for Miami."""
    rec = negotiation.record
    terms, route = rec["agreement"]["terms"], rec["agreement"]["route"]
    name, bbr = rec["player"], rec["bbr_id"]
    schedule = {s: int(v) for s, v in zip(_seasons(terms["years"]), terms["schedule"])}
    kinds = {s: "contract_salary" for s in schedule}
    guaranteed = {s: (0 if (i == terms["years"] - 1 and not terms.get("last_year_guaranteed", True)) else v) for i, (s, v) in enumerate(schedule.items())}
    own = not negotiation.outside()
    sheet, roster, rights = writer.load(TEAM / "Finances/contract_schedules.json"), writer.load(TEAM / "Team/Roster/roster.json"), writer.load(TEAM / "Finances/free_agent_rights.json")
    holdings, depth = writer.load(TEAM / "Team/Roster/holdings.json"), writer.load(TEAM / "Team/Depth_Chart/depth_chart.json")
    source_rel = f"../../../01_Free_Agency/Negotiations/{slug(name)}.json"
    right = next((p for p in rights["players"] if p["player"] == name), None)
    prior = (right or {}).get("previous_salary") if own else league_prior_salary(writer.root, bbr)
    acquired = via_trade["trade"].get("sign_and_trade_in") if via_trade else None
    sent = via_trade["trade"].get("sign_and_trade_out") if via_trade else None
    if acquired:
        route = "sign_and_trade"
        byc = acquired.get("base_year_compensation") or {"applies": False, "status": "not recorded by the incumbent"}
    elif sent and sent.get("base_year_compensation") is not None:
        byc = sent["base_year_compensation"]           # attached once, by the proposal, from Miami's ledger on its date
    else:
        byc = base_year_compensation(sheet, rights, name, route, terms["first_year"], prior, cap or planning_cap(writer.root, day), day)
    entry = {"player": name, "bbr_id": bbr, "status": "re_signed" if own else "signed_free_agent", "schedule": schedule, "amount_kind": kinds,
             "guaranteed": guaranteed, "signed_date": day, "original_term_seasons": terms["years"], "route": route,
             "promise": terms.get("promise"), "base_year_compensation": byc,
             "notes": f"Signed {long_date(day)} by simulated Miami via {route}; agreed {rec['agreement']['date']} (engine decision {rec['agreement']['decision_event']}).",
             "sources": [f"career/Dwyane_Wade/{SEASON}/01_Free_Agency/Negotiations/{slug(name)}.json"]}
    if prior:
        entry["prior_season_salary"] = {"season": "2002-03", "amount": prior}
    if acquired:
        record_rel = f"00_Team/Transactions/Trades/{via_trade['trade_id']}.json"
        entry["acquired"] = {"how": "sign_and_trade", "date": day, "from": via_trade["trade"]["partner"], "record": record_rel}
        entry["notes"] = (f"Signed {long_date(day)} by {via_trade['trade']['partner']} with his Bird rights on Miami's agreed terms and traded to Miami "
                          f"at once (sign-and-trade {via_trade['trade_id']}); agreed {rec['agreement']['date']} (engine decision {rec['agreement']['decision_event']}).")
        entry["sources"].append(f"career/Dwyane_Wade/{SEASON}/{record_rel}")
    if sent:
        record_rel = f"00_Team/Transactions/Trades/{via_trade['trade_id']}.json"
        entry["notes"] = (f"Signed {long_date(day)} by simulated Miami via {route} and traded to {via_trade['trade']['partner']} in the same transaction "
                          f"(sign-and-trade {via_trade['trade_id']}); agreed {rec['agreement']['date']} (engine decision {rec['agreement']['decision_event']}).")
        entry["sources"].append(f"career/Dwyane_Wade/{SEASON}/{record_rel}")
    previous = next((p for p in sheet["players"] if p["player"] == name), None)
    archive_previous_contract(writer, previous, day, source=str(TEAM / "Finances/contract_schedules.json"), player_id=bbr)
    archived = archive_contract(writer, entry, day, event="signed", source=entry["sources"][0], player_id=bbr,
                                signing_team=via_trade["trade"]["partner"] if acquired else "Miami Heat", executed_terms=terms)
    entry["contract_id"] = archived["contract_id"]
    if acquired:
        archive_contract(writer, entry, day, event="assigned", source=f"career/Dwyane_Wade/{SEASON}/{record_rel}", player_id=bbr,
                         signing_team=via_trade["trade"]["partner"], assignment={"date": day, "from_team": via_trade["trade"]["partner"],
                         "to_team": "Miami Heat", "source": f"career/Dwyane_Wade/{SEASON}/{record_rel}"})
    sheet["players"] = [p for p in sheet["players"] if p["player"] != name] + [entry]
    sheet["as_of"] = roster["as_of"] = day
    control = f"Signed {long_date(day)}: {terms['years']} seasons, ${sum(terms['schedule']):,} (${terms['first_year']:,} in 2003-04), ${terms['guaranteed']:,} guaranteed; route {route}."
    if acquired:
        control = f"Acquired by sign-and-trade from {via_trade['trade']['partner']} on {long_date(day)}: " + control[len("Signed "):]
    identity = league_identity(writer.root, bbr)
    existing = next((p for p in roster["players"] if p["name"] == name), None)
    if existing:
        existing.update(status="re_signed", control=control)
    else:
        roster["players"].append({"id": slug(name), "name": name, "positions": [x for x in (identity.get("position") or "SF").replace("/", "-").split("-")],
                                 "date_of_birth": identity.get("birth_date"), "status": "signed_free_agent", "control": control,
                                 "working_role": "Unassigned arrival", "player_card": f"../Player_Cards/{slug(name)}.md", "bbr_id": bbr})
        stats = next((r for r in read("library/2003/league/nba_2002_03_player_stats.json", writer.root)["records"] if r["bbr_id"] == bbr), None)
        writer.text(TEAM / f"Team/Player_Cards/{slug(name)}.md", player_card(name, identity, day, control, source_rel, stats))
        depth.setdefault("unassigned_arrivals", []).append({"name": name, "positions": roster["players"][-1]["positions"], "status": "signed_free_agent", "date": day})
    for p in rights["players"]:
        if p["player"] == name:
            p["re_signed"], p["re_signed_date"] = True, day
    if not sent:
        holdings["entries"].append({"player": name, "bbr_id": bbr, "from": day, "until": None,
                                    "basis": f"signed {day} ({route}); negotiation record Negotiations/{slug(name)}.json"})
    kind = "re-signs" if own else "signs"
    how = f"route {route}"
    if acquired:
        kind, how = "acquires by sign-and-trade from " + via_trade["trade"]["partner"], f"contract signed by the incumbent with his Bird rights ({via_trade['trade_id']})"
    if sent:
        kind, how = f"signs and trades to {via_trade['trade']['partner']} in one transaction", f"route {route}, sign-and-trade {via_trade['trade_id']}"
    note_event(writer, PHASE / "note.md", day, f"Miami {kind} {name}: {terms['years']} seasons, ${sum(terms['schedule']):,} "
               f"(${terms['guaranteed']:,} guaranteed), {how}; promised role {promise_text(terms.get('promise'))}. Record: `Negotiations/{slug(name)}.json`.")
    set_state(writer, day, last_event=f"{day}-miami-signs-{slug(name)}")
    negotiation.mark_signed(day, f"00_Team/Finances/contract_schedules.json#{name}")
    return entry


def world_effect(writer, negotiation, day, outcome):
    """A real club's answer changed the world: record it where rotations and later phases can read it."""
    rec = negotiation.record
    effects = writer.load(PHASE / "world_effects.json") if (writer.root / PHASE / "world_effects.json").exists() else None
    if effects is None:
        effects = {"schema_version": 1, "owner": "ai_gm", "purpose": ("Real-club outcomes caused by simulated Miami's offers (option D, rule 2). "
                   "A matched sheet keeps the player with his real club in place of his real move; a declined one is a Miami signing. "
                   "Rotations read this file for the 2003-04 roster import."), "effects": []}
        writer.files[PHASE / "world_effects.json"] = effects
    effects["effects"].append({"date": day, "player": rec["player"], "bbr_id": rec["bbr_id"], "club": rec["incumbent"], "outcome": outcome,
                               "terms": rec["agreement"]["terms"] if outcome == "matched" else None,
                               "decision_event": rec["sheet"]["resolution"]["decision_event"]})
    note_event(writer, PHASE / "note.md", day, f"{rec['incumbent']} {'matches' if outcome == 'matched' else 'declines to match'} Miami's offer sheet for {rec['player']}.")


def promise_text(promise):
    return f"{promise['role']}, {promise['minutes_per_game']} minutes a game" if promise else "none"


def _seasons(years, first=SEASON):
    start = int(first[:4])
    return [f"{start + i}-{str(start + i + 1)[-2:]}" for i in range(years)]


# -- finance summary ---------------------------------------------------------------------------------
def refresh_finance(writer, front_office, day):
    """Recompute the finance summary and cap sheet from the ledger on the date."""
    finance = writer.load(TEAM / "Finances/finance.json")
    room = front_office.cap_room()
    finance.update(as_of=day, cap_status="free_agency" if day >= "2003-07-01" else "pre_free_agency",
                   live_official_salary_cap=room["cap"] if room["cap_known"] else None, planning_cap=room["cap"],
                   known_counted_salary=room["committed"], free_agent_holds=room["holds"], roster_charge=room["roster_charge"],
                   cap_room=room["room"] if room["cap_known"] else None, projected_cap_room=room["room"],
                   cap_room_reason=[("Cap published July 15, 2003." if room["cap_known"] else "Cap not yet published; room is projected on the prior cap."),
                                    "Committed salary, unrenounced holds and the roster charge for empty spots are deducted (docs/front_office_design.md 5.1)."])
    sheet = writer.load(TEAM / "Finances/contract_schedules.json")
    writer.text(TEAM / "Finances/cap_sheet.md", cap_sheet_text(sheet, writer.load(TEAM / "Finances/free_agent_rights.json"), room, day))


def cap_sheet_text(sheet, rights, room, day):
    rows = []
    totals = {s: 0 for s in HORIZON}
    for p in sorted(sheet["players"], key=lambda p: -(p["schedule"].get(SEASON) or 0)):
        if p["status"] in CLOSED_STATUSES:
            continue
        cells = []
        for s in HORIZON:
            v = p["schedule"].get(s)
            kind = p.get("amount_kind", {}).get(s, "")
            tag = {"team_option": "TO", "player_option": "PO", "early_termination_option": "ETO", "draft_hold": "H"}.get(kind, "")
            cells.append("—" if v is None else f"{v:,}" + (f"<sup>{tag}</sup>" if tag else ""))
            if v and kind in ("contract_salary", "draft_hold", "team_option", "player_option", "early_termination_option") and "pending" not in p["status"]:
                totals[s] += v
        rows.append(f"| [{p['player']}](../Team/Player_Cards/{slug(p['player'])}.md) | " + " | ".join(cells) + " |")
    holds = [f"| {p['player']} | {p['cap_hold']:,} | {p['bird_status']} |" for p in rights["players"]
             if p.get("cap_hold") and not (p.get("renounced") or p.get("re_signed") or p.get("signed_elsewhere"))]
    return f"""# Miami Heat | Cap sheet

{long_date(day)} · 2003-04 through 2010-11 · USD

[Finance guide](README.md) · [Roster and control](../Team/Roster/roster.json) · [Contract detail](contract_schedules.json)

## Current cap position

| Cap ({'published' if room['cap_known'] else 'planning, prior season'}) | Committed salary | Free-agent holds | Roster charge | Room |
| ---: | ---: | ---: | ---: | ---: |
| {room['cap']:,} | {room['committed']:,} | {room['holds']:,} | {room['roster_charge']:,} | {room['room']:,} |

Committed salary counts contracts, exercised options and the unsigned first-round hold on {long_date(day)}. Holds are the unrenounced free agents' cap holds; the roster charge is the minimum salary for each spot under twelve.

## Eight-season commitments

| Player | {' | '.join(HORIZON)} |
| --- | {' | '.join('---:' for _ in HORIZON)} |
{chr(10).join(rows)}
| Counted | {' | '.join(f'{totals[s]:,}' for s in HORIZON)} |

## Free-agent holds

| Player | Hold | Rights |
| --- | ---: | --- |
{chr(10).join(holds) if holds else '| — | — | no unrenounced free agents |'}

## Payroll notes

Signings and renouncements are dated in the free-agency note (`../../01_Free_Agency/note.md`) and the negotiation records. Renounced players keep no hold or Bird rights until the next June 30.

## Cap reconciliation

Figures are recomputed from `contract_schedules.json` and `free_agent_rights.json` by `runtime/signing.py` on every transaction; `finance.json` carries the same totals for the date.
"""


# -- validation ------------------------------------------------------------------------------------
def counted_salary(sheet_players, on, season=SEASON):
    """2003-04 salary counted on a date: contracts, exercised options and holds; pending options only before July 1."""
    total = 0
    for p in sheet_players:
        amount, status = p["schedule"].get(season), p["status"]
        if amount is None or status in CLOSED_STATUSES:
            continue
        if status in ("team_option_pending", "player_option_pending") and on >= "2003-07-01":
            continue
        total += amount
    return total


def ledger_errors(root=ROOT):
    """Once the clock has left June 26: the finance summary, register, holdings, cards and records agree."""
    errors = []
    root = Path(root)
    state = read(STATE, root)
    if state["current_date"] <= "2003-06-26":
        return errors
    sheet, roster, finance = read(TEAM / "Finances/contract_schedules.json", root), read(TEAM / "Team/Roster/roster.json", root), read(TEAM / "Finances/finance.json", root)
    holdings = read(TEAM / "Team/Roster/holdings.json", root)
    if not finance["as_of"] <= state["current_date"]:
        errors.append("finance.json is dated after the career clock")
    if finance["as_of"] > "2003-06-26" and finance.get("known_counted_salary") != counted_salary(sheet["players"], finance["as_of"]):
        errors.append("finance.json: known_counted_salary does not reconcile to contract_schedules.json on its date")
    by_name = {p["player"]: p for p in sheet["players"]}
    for p in roster["players"]:
        if p["status"] not in ("signed_free_agent", "re_signed"):
            continue
        entry = by_name.get(p["name"])
        card = root / TEAM / "Team/Player_Cards" / f"{p['id']}.md"
        record = root / PHASE / "Negotiations" / f"{slug(p['name'])}.json"
        if not entry or entry["status"] != p["status"]:
            errors.append(f"{p['name']}: register and contract sheet disagree")
        if not card.exists():
            errors.append(f"{p['name']}: signed player without a card")
        if not record.exists() or json.loads(record.read_text(encoding="utf-8"))["status"] != "signed":
            errors.append(f"{p['name']}: signed player without a signed negotiation record")
        if entry and not any(e["player"] == p["name"] and e["from"] == entry.get("signed_date") and e["until"] is None for e in holdings["entries"]):
            errors.append(f"{p['name']}: no open holding from his signing date")
        acquired = (entry or {}).get("acquired") or {}
        if acquired.get("how") == "sign_and_trade":
            trade_path = root / f"career/Dwyane_Wade/{SEASON}" / acquired.get("record", "")
            if not trade_path.is_file() or json.loads(trade_path.read_text(encoding="utf-8")).get("status") != "completed":
                errors.append(f"{p['name']}: acquired by sign-and-trade without a completed trade record")
    return errors


# -- July 1: the register's free agents; departures; Wade's rookie contract -----------------------------
def open_market(writer, day="2003-07-01"):
    """On July 1 the expiring contracts are free agents whose rights Miami holds; a declined player option too."""
    roster, rights, sheet = writer.load(TEAM / "Team/Roster/roster.json"), writer.load(TEAM / "Finances/free_agent_rights.json"), writer.load(TEAM / "Finances/contract_schedules.json")
    cba = read("library/2003/league/nba_1999_cba_rules.json", writer.root)
    rules = read("library/2003/league/nba_2003_04_cap_rules.json", writer.root)
    known = {p["player"] for p in rights["players"]}
    changed = []
    for p in roster["players"]:
        if "expiring" in p["status"] or p["status"] == "player_option_declined":
            if p["status"] == "player_option_declined" and p["name"] not in known:
                entry = next(s for s in sheet["players"] if s["player"] == p["name"])
                prior = entry.get("prior_season_salary", {}).get("amount") or entry["schedule"].get("2002-03") or entry["schedule"].get(SEASON)
                seasons = entry.get("seasons_with_club_for_bird") or entry.get("years_of_service") or 0
                status = "larry_bird" if seasons >= 3 else "early_bird" if seasons == 2 else "non_bird"
                above = prior >= rights["average_salary_threshold"]
                percent = {"larry_bird": 150 if above else 200, "early_bird": 130, "non_bird": 120}[status]
                service = entry.get("years_of_service") or 0
                tier = "0_to_6_years" if service <= 6 else "7_to_9_years" if service <= 9 else "10_plus_years"
                hold = min(int(round(prior * percent / 100)), rules["maximum_salary"][tier])
                rights["players"].append({"player": p["name"], "bbr_id": p.get("bbr_id"), "previous_salary": prior,
                                          "seasons_with_miami_for_bird": seasons, "nba_seasons_before_2003_04": service,
                                          "bird_status": status, "cap_hold": hold, "cap_hold_percent": percent,
                                          "above_league_average_salary": above, "restricted_free_agency_eligible": False,
                                          "qualifying_offer": None, "qualifying_offer_basis": "not eligible for restricted free agency",
                                          "notes": [f"Added {day}: declined his {SEASON} player option on June 30 (engine draw); hold at {percent}% of ${prior:,} "
                                                    f"({cba['cap_holds_percent']['source']}), capped at his maximum."]})
            p["status"] = "free_agent_rights_held"
            p["control"] = f"Free agent from July 1, 2003; Miami holds his rights and cap hold until he re-signs, signs elsewhere or is renounced (Finances/free_agent_rights.json)."
            changed.append(p["name"])
        elif p["status"] == "team_option_declined":
            p["status"] = "free_agent_option_declined"
            p["control"] = "Free agent from July 1, 2003 after Miami declined his team option on June 30; no cap hold is carried."
            changed.append(p["name"])
    roster["as_of"] = rights["as_of"] = day
    if changed:
        note_event(writer, PHASE / "note.md", day, "Free agency opens; Miami's free agents on the register: " + ", ".join(changed) + ".")
    return changed


def depart(writer, name, day, status, reason):
    """A player leaves Miami's books: register, rights, cap sheet and depth chart, with the reason."""
    roster, rights, sheet = writer.load(TEAM / "Team/Roster/roster.json"), writer.load(TEAM / "Finances/free_agent_rights.json"), writer.load(TEAM / "Finances/contract_schedules.json")
    depth = writer.load(TEAM / "Team/Depth_Chart/depth_chart.json")
    found = False
    for p in roster["players"]:
        if p["name"] == name and "elsewhere" not in p["status"] and p["status"] != "renounced":
            p["status"], p["control"] = status, f"{long_date(day)}: {reason}."
            found = True
    if not found:
        return False
    for p in rights["players"]:
        if p["player"] == name:
            p[status], p[f"{status}_date"] = True, day
    for s in sheet["players"]:
        if s["player"] == name:
            s["status"] = status
    for pos, names in depth["positions"].items():
        if name in names:
            names.remove(name)
    depth["unavailable"] = [u for u in depth.get("unavailable", []) if u["name"] != name]
    depth.setdefault("departed", []).append({"name": name, "date": day, "status": status})
    depth["as_of"] = roster["as_of"] = day
    note_event(writer, PHASE / "note.md", day, f"{name} {reason}.")
    return True


def player_status_snapshot(writer, day, source_event, **fields):
    """Keep the public identity dated when an executed event changes Wade's status."""
    identity_rel = Path("career/Dwyane_Wade/professional_identity.json")
    if not (writer.root / identity_rel).is_file():
        return
    identity = writer.load(identity_rel)
    snapshot = dict(max((s for s in identity["snapshots"] if s["as_of"] <= day), key=lambda s: s["as_of"]))
    snapshot.update(as_of=day, source_state=f"{SEASON}/current_state.json", source_event=source_event, **fields)
    identity["snapshots"] = sorted([s for s in identity["snapshots"] if s["as_of"] != day] + [snapshot], key=lambda s: s["as_of"])


def sign_rookie(writer, log, terms, day):
    """Wade signs his rookie-scale contract: the cap sheet, register, depth chart, state and the log's signing entry."""
    sheet, roster, depth = writer.load(TEAM / "Finances/contract_schedules.json"), writer.load(TEAM / "Team/Roster/roster.json"), writer.load(TEAM / "Team/Depth_Chart/depth_chart.json")
    entry = next(p for p in sheet["players"] if p["player"] == "Dwyane Wade")
    archive_previous_contract(writer, entry, day, source=str(TEAM / "Finances/contract_schedules.json"), player_id="wadedw01")
    layered = terms.get("structure") == "layered"
    percent = terms["total_percent"] if layered else terms["percent_of_scale"]
    entry.update(status="under_contract", schedule=dict(terms["schedule"]), amount_kind=dict(terms["amount_kind"]), signed_date=day,
                 original_term_seasons=3, team_option_season="2006-07", fourth_year_option_deadline=terms["fourth_year_option_deadline"],
                 percent_of_scale=percent, route="rookie_scale",
                 notes=(f"Rookie-scale contract signed {long_date(day)}: {terms['protected_percent']}% of the No. 5 scale as protected Current Cash "
                        f"Compensation plus incentives to {percent}%; the scheduled amounts are the counted Salary (protected cash, included "
                        f"incentives and bonuses classified Likely); Unlikely bonuses count only when earned. Three seasons plus a team option for "
                        f"2006-07 at the third season's Salary raised 26.7%, to be exercised by {terms['fourth_year_option_deadline']}. The draft hold ends with the signing."
                        if layered else
                        f"Rookie-scale contract signed {long_date(day)} at {percent}% of the No. 5 scale: three seasons plus a team option for 2006-07, to be exercised by {terms['fourth_year_option_deadline']}. The draft hold ends with the signing."))
    if layered:
        entry["protected_schedule"], entry["maximum_schedule"], entry["incentives"] = dict(terms["protected_schedule"]), dict(terms["maximum_schedule"]), [dict(l) for l in terms["incentives"]]
        entry["bonus_evaluation"] = "each season's incentives are evaluated against closed results at the season rollover (docs/ROADMAP.md item 18)"
    entry.pop("current_cap_hold", None)
    entry["sources"] = ["01_Free_Agency/Wade_Rookie_Contract/negotiation_log.json"] + [s for s in entry.get("sources", []) if "negotiation_log" not in s]
    archived = archive_contract(writer, entry, day, event="signed", source=str(PHASE / "Wade_Rookie_Contract/negotiation_log.json"),
                                player_id="wadedw01", signing_team="Miami Heat", executed_terms=terms)
    entry["contract_id"] = archived["contract_id"]
    first = terms["schedule"]["2003-04"]
    for p in roster["players"]:
        if p["name"] == "Dwyane Wade":
            p["status"] = "under_contract"
            p["control"] = f"Rookie-scale contract signed {long_date(day)}: ${first:,} counted in 2003-04, three seasons plus a 2006-07 team option; {percent}% of scale" + (" at the maximum, 80% protected" if layered else "") + "."
    for u in depth.get("unassigned_draft_rights", []):
        if u["name"] == "Dwyane Wade":
            u["status"] = "under_contract"
    sheet["as_of"] = roster["as_of"] = depth["as_of"] = day
    log["entries"].append({"date": day, "party": "miami", "action": "sign", "terms": terms,
                           "note": f"Contract executed {long_date(day)}; recorded on contract_schedules.json and the register."})
    note_event(writer, PHASE / "note.md", day, f"Wade signs his rookie-scale contract ({'80% protected plus incentives to ' if layered else ''}{percent}% of scale): "
               f"${first:,} counted in 2003-04, three seasons plus a 2006-07 team option. Record: `Wade_Rookie_Contract/negotiation_log.json`.")
    state = writer.load(STATE)
    pending = [d for d in state.get("pending_player_decisions", []) if d != "rookie_contract_offer"]
    set_state(writer, day, last_event=f"{day}-wade-signs-rookie-contract", contract_status="rookie_scale_contract", roster_status="under_contract",
              pending_player_decisions=pending)
    player_status_snapshot(writer, day, f"{SEASON}/01_Free_Agency/Wade_Rookie_Contract/negotiation_log.json",
                           roster_status="Under contract", contract=f"Rookie scale signed {day}: three seasons plus a 2006-07 team option")
    return entry


# -- trades ---------------------------------------------------------------------------------------
TRADES = TEAM / "Transactions/Trades"
DEPARTURES = TEAM / "Team/Roster/departures.json"


def phase_note_for(state):
    return Path(f"career/Dwyane_Wade/{SEASON}") / state.get("current_note", "01_Free_Agency/note.md")


def apply_trade(writer, record, day):
    """Write an accepted trade: Miami's side into every record, the partner's side into the departures ledger."""
    trade = record["trade"]
    club = trade["partner"]
    sheet, roster, holdings = writer.load(TEAM / "Finances/contract_schedules.json"), writer.load(TEAM / "Team/Roster/roster.json"), writer.load(TEAM / "Team/Roster/holdings.json")
    depth, picks = writer.load(TEAM / "Team/Depth_Chart/depth_chart.json"), writer.load(TEAM / "Finances/draft_picks.json")
    departures = writer.load(DEPARTURES) if (writer.root / DEPARTURES).exists() else None
    if departures is None:
        departures = {"schema_version": 1, "owner": "ai_gm", "kind": "miami_departures", "season": SEASON,
                      "purpose": ("Players simulated Miami sent to real clubs (conflict rule 3): the club, the dates and the previous minute "
                                  "share (last real season) rule 3 lets him keep up to the departing minutes. Read by runtime/rotations.py."),
                      "entries": []}
        writer.files[DEPARTURES] = departures
    stats = {r["bbr_id"]: r for r in read("library/2003/league/nba_2002_03_player_stats.json", writer.root)["records"]}
    inventory = read("library/2003/league/nba_2003_contracts.json", writer.root)["clubs"][club]
    record_rel = f"00_Team/Transactions/Trades/{record['trade_id']}.json"
    # Miami's outgoing players
    for name in trade.get("miami_out", []):
        entry = next(p for p in sheet["players"] if p["player"] == name)
        bbr = entry.get("bbr_id") or next((r.get("bbr_id") for r in roster["players"] if r["name"] == name), None)
        archive_contract(writer, entry, day, event="assigned", source=f"career/Dwyane_Wade/{SEASON}/{record_rel}", player_id=bbr,
                         assignment={"date": day, "from_team": "Miami Heat", "to_team": club,
                                     "source": f"career/Dwyane_Wade/{SEASON}/{record_rel}"})
        depart(writer, name, day, "traded", f"traded to {club} ({record['trade_id']})")
        for e in holdings["entries"]:
            if e["player"] == name and e["until"] is None:
                e["until"] = day
        prior = stats.get(bbr, {}).get("totals", {})
        identity = league_identity(writer.root, bbr)
        departures["entries"].append({"player": name, "bbr_id": bbr, "club": club, "from": day, "until": None,
                                      "position": (identity.get("position") or "SF").split("-")[0],
                                      "games": prior.get("games", 0), "minutes": prior.get("minutes", 0),
                                      "basis": f"traded {day} ({record['trade_id']}); previous share from 2002-03 totals"})
    # Miami's incoming players (a sign-and-trade acquisition was written by `sign` from the agreed terms)
    acquired = trade.get("sign_and_trade_in")
    for name in trade.get("miami_in", []):
        if acquired and acquired["player"] == name:
            continue
        p = next(p for p in inventory["players"] if p["player"] == name)
        bbr = p.get("bbr_id")
        entry = {"player": name, "bbr_id": bbr, "status": "under_contract", "schedule": dict(p["schedule"]), "amount_kind": dict(p.get("amount_kind", {})),
                 "acquired": {"how": "trade", "date": day, "from": club, "record": record_rel},
                 "notes": f"Acquired from {club} on {long_date(day)} by trade ({record['trade_id']}); contract carried as the inventory records it ({p['status']}).",
                 "sources": [record_rel] + list(p.get("sources", []))}
        if p.get("prior_season_salary"):
            entry["prior_season_salary"] = p["prior_season_salary"]
        previous = next((old for old in sheet["players"] if old["player"] == name), None)
        archive_previous_contract(writer, previous, day, source=str(TEAM / "Finances/contract_schedules.json"), player_id=bbr)
        # The presentation archive retains all sourced original terms, including
        # options and guarantees. It does not alter the engine's salary ledger.
        assigned = {**deepcopy(p), "acquired": deepcopy(entry["acquired"])}
        archived = archive_contract(writer, assigned, day, event="assigned", source=f"career/Dwyane_Wade/{SEASON}/{record_rel}", player_id=bbr,
                                    assignment={"date": day, "from_team": club, "to_team": "Miami Heat",
                                                "source": f"career/Dwyane_Wade/{SEASON}/{record_rel}"})
        entry["contract_id"] = archived["contract_id"]
        for field in ("signed_date", "signing_team"):
            if p.get(field):
                entry[field] = p[field]
        sheet["players"] = [x for x in sheet["players"] if x["player"] != name] + [entry]
        identity = league_identity(writer.root, bbr)
        salary = p["schedule"].get(SEASON) or 0
        control = f"Acquired by trade from {club} on {long_date(day)}: ${salary:,} in 2003-04; contract through {max(s for s, v in p['schedule'].items() if v)}."
        roster["players"].append({"id": slug(name), "name": name, "positions": [x for x in (identity.get("position") or "SF").replace("/", "-").split("-")],
                                 "date_of_birth": identity.get("birth_date"), "status": "under_contract", "control": control,
                                 "working_role": "Unassigned arrival", "player_card": f"../Player_Cards/{slug(name)}.md", "bbr_id": bbr})
        writer.text(TEAM / f"Team/Player_Cards/{slug(name)}.md", player_card(name, identity, day, control, f"../../../{record_rel}", stats.get(bbr)))
        depth.setdefault("unassigned_arrivals", []).append({"name": name, "positions": roster["players"][-1]["positions"], "status": "under_contract", "date": day})
        holdings["entries"].append({"player": name, "bbr_id": bbr, "from": day, "until": None, "basis": f"acquired by trade from {club} ({record['trade_id']})"})
    # Picks
    for pick in trade.get("picks_out", []):
        for own in picks["picks"]:
            if own["year"] == pick["year"] and own["round"] == pick["round"] and own["owned"]:
                own["owned"] = False
                own["history"].append({"date": day, "to": club, "trade": record["trade_id"]})
    for pick in trade.get("picks_in", []):
        picks["picks"].append({"year": pick["year"], "round": pick["round"], "owned": True, "original_club": club,
                               "history": [{"date": day, "from": club, "trade": record["trade_id"]}]})
    sheet["as_of"] = roster["as_of"] = depth["as_of"] = picks["as_of"] = day
    outs = ", ".join(trade.get("miami_out", []) + [f"{x['year']} round {x['round']} pick" for x in trade.get("picks_out", [])]) or "nothing"
    ins = ", ".join(trade.get("miami_in", []) + [f"{x['year']} round {x['round']} pick" for x in trade.get("picks_in", [])]) or "nothing"
    state = writer.load(STATE)
    own = trade.get("sign_and_trade_out")
    if acquired or own:
        st = acquired or own
        who = (f"{club} signs {st['player']} with his Bird rights and trades him to Miami" if acquired
               else f"Miami signs {st['player']} with his Bird rights and trades him to {club} in the same transaction")
        text = f"Sign-and-trade with {club}: Miami sends {outs} for {ins}; {who} (accepted by engine draw {record['decision_event']}). Record: `{record_rel}`."
        event = f"{day}-sign-and-trade-{record['trade_id']}"
    else:
        text = f"Trade with {club}: Miami sends {outs} for {ins} (accepted by engine draw {record['decision_event']}). Record: `{record_rel}`."
        event = f"{day}-trade-{record['trade_id']}"
    note_event(writer, phase_note_for(state), day, text)
    set_state(writer, day, area=state.get("current_area", "01_Free_Agency"), note=state.get("current_note", "01_Free_Agency/note.md"),
              last_event=event)
    return record_rel


def write_proposal(root, desk, trade, ranking, day, *, kind="trade", negotiation=None, standing=None, consultation=None):
    """Write a proposal record and its acceptance packet once (the one proposal writer): the record under
    `00_Team/Transactions/Trades/<trade_id>.json`, `trade-<trade_id>.decision.json` beside it and the phase-note line."""
    from .decisions import decision_errors
    packet, valuation = desk.acceptance_packet(trade)
    if packet is None:
        raise ValueError("; ".join(valuation))
    errors = decision_errors(packet)
    if errors:
        raise ValueError("; ".join(errors))
    root = Path(root)
    folder = root / TRADES
    folder.mkdir(parents=True, exist_ok=True)
    trade_id = desk.trade_id(trade)
    path = folder / f"{trade_id}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    st = trade.get("sign_and_trade_in") or trade.get("sign_and_trade_out")
    basis = ("Chosen by Miami's front office as the top-ranked legal proposal on the date (runtime/trades.py search)." if kind == "trade" else
             ("The incumbent signs the agreed player with his Bird rights and trades him; Miami offers the legal package that costs it the least value "
              "(runtime/trades.py sign_and_trade_proposal)." if trade.get("sign_and_trade_in") else
              "Miami signs its own agreed free agent with his Bird rights and trades him in the same transaction to the first partner whose "
              "arriving package is worth Miami's while; his consent is a separate draw (runtime/trades.py sign_and_trade_proposal). "
              "A decline on either draw leaves the agreement standing: Miami re-signs him on the agreed terms."))
    record = {"trade_id": trade_id, "date": day, "status": "proposed", "kind": kind, "trade": trade, "valuation": valuation,
              "ranking": ranking, "decision_event": packet["event_id"], "negotiation": negotiation, "standing": standing,
              "consultation": consultation, "answer": None, "applied": None, "basis": basis}
    if trade.get("sign_and_trade_out"):
        record["player_consent_event"] = f"2003-fa-{st['bbr_id']}-sign-and-trade-{trade_id}"
    path.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    request = folder / f"{packet['event_id']}.decision.json"
    if not request.exists():
        request.write_text(json.dumps(packet, indent=1) + "\n", encoding="utf-8")
    writer = Writer(root)
    state = writer.load(STATE)
    outs = ", ".join(trade.get("miami_out", [])) or "nothing"
    ins = ", ".join(trade.get("miami_in", [])) or "nothing"
    label = "proposes a sign-and-trade to" if kind == "sign_and_trade" else "proposes to"
    note_event(writer, phase_note_for(state), day,
               f"Miami {label} {trade['partner']}: {outs} for {ins} (acceptance drawn by the engine, {packet['event_id']}). "
               f"Record: `00_Team/Transactions/Trades/{trade_id}.json`.")
    writer.commit()
    return record


TRADE_STATUSES = ("proposed", "completed", "declined", "void")


def trade_record_errors(root=ROOT):
    """Every trade record is well formed, has its packet, and a completed sign-and-trade links back to its signing."""
    errors = []
    root = Path(root)
    folder = root / TRADES
    if not folder.exists():
        return errors
    season_dir = root / f"career/Dwyane_Wade/{SEASON}"
    for path in sorted(folder.glob("*.json")):
        if path.name.endswith(".decision.json") or path.name.endswith(".result.json"):
            continue
        rel = path.relative_to(root)
        try:
            r = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as exc:
            errors.append(f"{rel}: invalid JSON: {exc}")
            continue
        if r.get("trade_id") != path.stem:
            errors.append(f"{rel}: trade_id must be the file stem")
        if r.get("status") not in TRADE_STATUSES:
            errors.append(f"{rel}: unknown status {r.get('status')!r}")
        if not r.get("decision_event") or not (folder / f"{r['decision_event']}.decision.json").exists():
            errors.append(f"{rel}: missing decision packet {r.get('decision_event')}.decision.json")
        if r.get("status") == "completed" and not r.get("applied"):
            errors.append(f"{rel}: completed without an applied date")
        trade = r.get("trade") or {}
        kind = r.get("kind", "trade")
        if kind == "sign_and_trade" or trade.get("sign_and_trade_in") or trade.get("sign_and_trade_out"):
            if bool(trade.get("sign_and_trade_in")) == bool(trade.get("sign_and_trade_out")):
                errors.append(f"{rel}: a sign-and-trade names exactly one of sign_and_trade_in and sign_and_trade_out")
            neg = r.get("negotiation")
            if not neg or not (root / neg).exists():
                errors.append(f"{rel}: a sign-and-trade needs its negotiation record")
            elif r.get("status") == "completed" and json.loads((root / neg).read_text(encoding="utf-8")).get("status") != "signed":
                errors.append(f"{rel}: a completed sign-and-trade needs a signed negotiation")
        if r.get("consultation") and not (season_dir / "Wade_Consultations" / f"{r['consultation']}.json").exists():
            errors.append(f"{rel}: consultation {r['consultation']} has no record")
    return errors
