"""Contract extensions for every club (the user's request, October 2026: the career had no contract extensions, so
players history kept off the market, such as Allen Iverson and Andrei Kirilenko, reached free agency).

Gate. Extension days start on FIRST_DAY (2005-10-31, the 2002 draft class's rookie-scale deadline). The days that had
already passed (2003-10-31, 2004-06-29, 2004-10-31, 2005-06-29) belong to markets, options and trades that are recorded
and replay unchanged: they are never decided. A contract without an `extension` key reads exactly as before.

Rules: the agreement in force for the decision day's league year (`agreement.terms`; the 2005 agreement's extension
terms in `library/2005/league/nba_2005_cba_rules.json` "extensions", cbafaq05 Q52, the 105% free-agent maximum Q11):
- rookie scale: a first-round pick whose club picked up the option on his last scale season may be extended to October
  31 before that season, up to five more seasons, the first at any amount up to his maximum, raises up to 10.5% of the
  first extension year;
- veteran: a contract of four or more seasons, three years after it was signed (four for a six- or seven-season contract
  signed before July 1, 2005; three after an earlier extension), to June 30 before free agency, five seasons at most
  including the season remaining (four new), the first at most 110.5% of the last salary and at most his free-agent
  maximum (the tier maximum or 105% of the last salary, the greater), raises up to 10.5% of the last salary.

Eligibility (repository records only; an unknown signing date or length is never eligible, never guessed). On a decision
day D in league year S (F = the season after it), a player is considered when his contract in force ends with S (no
later season, no option for F) and a club holds him at the start of D (the end of the day before: a trade dated D never
precedes the decision, so a replay finds the same holder). A contract his club waived is not the one in force: a waiver
(`League/league_moves.json`) after its signing that no claim took up ends it, and the contract he plays on with a later
club is a new one (cbafaq05 Q52 extends the contract a club holds). Rookie scale (October 31 only): the team option for
S, the last scale season, was exercised on the October 31 a year earlier (`League/option_decisions.json`) and the
contract in force is still that rookie-scale contract. Veteran: no option decision for F cut the contract short, it is
not a rookie-scale contract, and its signing date and length are recorded: the latest extension, else the summer market
record that signed it (a `new` or `rookie_scale` ledger entry, traced back season by season), else the June 2003
inventory or the real 2003 summer signing a 2004-05 ledger entry was built from; Miami's own sheet for a contract Miami
signed. A 2004-05 contract rebuilt from the salary list has no recorded length.

Days: October 31 every year from 2005 (rookie scale on its deadline, veterans in a pre-season review) and June 29 from
2006 (veterans: the last day before free agency, the same day as `options.VETERAN_DEADLINE`; from June 1 the valuation
reads the season just closed, the only other date with new evidence). Each day is decided once, on its own date (the
career clock on it), with evidence and holders dated on it, and before the day's other club steps (the market day, the
trade scan and the option step): the driver's extension step (`extension_day` in `scripts/advance.py`) must run
`scripts/extension_day.py --write DATE` every day for this. A day is never decided late or ahead of the clock (`run`
refuses, `ExtensionError`): later systems have used the contracts by then, so a missed day is reported by validation
and the rollover and needs a decision, never a catch-up. A day is decided only once every earlier decision is applied.

Club decision (one rule for every club, Miami's AI/GM included; judgement constants named below):
- price: the market price of his closed-season production (`Valuation.market_price`, the honor factor included) inside
  the minimum and his free-agent maximum for his service in F, under the cap rules published by D (the planning season:
  never a cap figure before its publication date); worth: the price, x YOUTH_PREMIUM at 24 or younger (`options`);
- core ratio r = worth / (CORE_MLES x the mid-level): a player worth the mid-level or more costs that much to replace over
  the cap. r >= HIGH: the club offers; r <= LOW: it does not; in between the engine draws the call, P(offer) =
  (r - LOW) / (HIGH - LOW) (the option rule's band, `options.LOW` and `options.HIGH`);
- no offer, before any call, when his real career has no season F (`availability`), there is no valuation, no legal first
  salary exists, or F's committed payroll plus the club's earlier offers that day plus this one passes the summer
  market's ceiling (the tax line; 10% over it for a contender; for a player priced at two mid-levels the greater of 35%
  over it and 17.5% over the committed payroll). Candidates are taken by worth, highest first.
- terms: the years he wants by age (`free_agency_2004.YEARS_WANTED`) within the agreement's limit; first year: the price
  (rookie scale) or the price held to 110.5% of the last salary (veteran); flat raises at the agreement's limit (10.5% of
  the first year, rookie scale; 10.5% of the smaller of the first year and the last salary, veteran).

Player's answer (an engine draw for every player but Wade): the 2003 factor model (`runtime/player_utility.py`, no drawn
priority: it is drawn only when he reaches free agency) scores the extension at his club against free agency next summer
at his price with a league-average club (loyalty, contention, tax and market, money and security against the years he
wants); P(sign) = the model's accept odds on the utility gap, the counter share folded into a decline (take it or leave
it). A clear offer is one packet (signed or declined); a close call is one packet with the club's call and his answer
together (signed, declined, no_offer), so the step never waits twice. Packets are `League/Extension_Draws/<id>`, written
once and never re-rolled.

Wade: Miami's AI/GM calls by the same rule as every club, a close call included: inside the band the engine draws the
club's call alone (`offer` or `no_offer`, P(offer) as above), since his answer is his own. An offer, clear or drawn, is a
player decision: a record and a milestone page under `01_Free_Agency/Wade_Extension/`, a pending entry
`wade_extension:<id>` that stops the clock, and his answer through `scripts/player_milestone.py --reply` (kind
`extension`, accept or decline). The next run applies it.

Records: `<season>/League/extension_decisions.json` (days and decisions). A signed extension is written into the league
ledger (`extension`, the schedule gains its seasons) and, for Miami, its cap sheet, the contract archive and the phase
note; a later rebuild re-applies it (`reapply`) and the rollover carries it (`league_contracts.carried`).
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
from fractions import Fraction
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAYER = Path("career/Dwyane_Wade")
MIAMI = "Miami Heat"
WADE, WADE_BBR, WADE_KEY = "Dwyane Wade", "wadedw01", "dwyane_wade"
FIRST_DAY = "2005-10-31"
ROOKIE_DAY = "10-31"                   # the rookie-scale deadline (cbafaq05 Q52; the weekend rule is not modelled)
VETERAN_DAY = "06-29"                  # the day before free agency (options.VETERAN_DEADLINE)
PENDING_PREFIX = "wade_extension:"
KINDS = ("rookie_scale", "veteran")
OUTCOMES = ("signed", "declined", "no_offer")
ROUTES = {"rookie_scale": "rookie_scale_extension", "veteran": "veteran_extension"}
CORE_MLES = 1.0                        # judgement: a core player costs the mid-level or more to replace over the cap
NEUTRAL_WINS = 41                      # judgement: the league-average club a free agent would sign with next summer
CLUB_CALLS = ("offer", "no_offer")     # the outcomes of Miami's drawn close call on Wade (his answer is his own)
EXTENSION_FIELDS = ("extension", "earlier_extensions", "extended_on", "extension_history")
SIGN_EVENTS = ("signing", "re_sign", "offer_sheet_matched", "offer_sheet_not_matched", "rookie_scale_signing",
               "camp_signing", "qualifying_offer_accepted")
INVENTORY = Path("library/2003/league/nba_2003_contracts.json")
SIGNINGS_2003 = Path("library/2003/league/nba_2003_offseason_transactions.json")
SHEET = "00_Team/Finances/contract_schedules.json"
REGISTER = "00_Team/Team/Roster/roster.json"


class ExtensionError(ValueError):
    """An extension day that cannot be decided as the rule requires: missed, ahead of the clock, not live, or behind an
    earlier decision still unresolved. Never repaired by a late run; it needs a decision."""


# -- files ---------------------------------------------------------------------------------------------------------------
def _read(path, default=None):
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else default


def _dump(path, data):
    """Write JSON keeping the file's existing indentation (one space for a new file), so records diff by content."""
    path = Path(path)
    indent = 1
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines()[1:3]:
            lead = len(line) - len(line.lstrip(" "))
            if lead:
                indent = lead
                break
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=indent, ensure_ascii=False) + "\n", encoding="utf-8")


def record_path(season):
    return PLAYER / season / "League/extension_decisions.json"


def draws_dir(season):
    return PLAYER / season / "League/Extension_Draws"


def offer_folder(root, season):
    return Path(root) / PLAYER / season / "01_Free_Agency/Wade_Extension"


def offer_id(day):
    return f"{day}-{WADE_KEY}-extension"


def offer_path(root, season, oid):
    return offer_folder(root, season) / f"{oid}.json"


def page_name(record):
    return f"Milestone_{record['date']}_extension_offer.md"


def read_record(season, root=ROOT):
    return _read(Path(root) / record_path(season)) or {
        "schema_version": 1, "kind": "extension_decisions", "season": season,
        "rule": __doc__.split("\n\n", 1)[1].strip(), "days": [], "decisions": []}


# -- the agreement's terms -----------------------------------------------------------------------------------------------
def rules(season, root=ROOT):
    """The extension terms of the agreement in force for a league year (`agreement.terms`), or None under the 1999
    agreement (no extension day falls in it)."""
    from .agreement import CBA_2005, terms
    if terms(season, root)["agreement"] == "1999":
        return None
    t = _read(Path(root) / CBA_2005)["extensions"]["terms"]["value"]
    long = t["long_contract"]
    return {"rookie_new_seasons": t["rookie_scale_additional_seasons"],
            "rookie_raise_pct": t["rookie_scale_raise_pct_of_first_year"],
            "veteran_total_seasons": t["veteran_total_seasons_including_remaining"],
            "veteran_first_year_pct": t["veteran_first_year_pct_of_last_salary"],
            "veteran_raise_pct": t["veteran_raise_pct_of_last_salary"],
            "free_agent_max_pct": t["free_agent_maximum_pct_of_last_salary"],
            "min_length": t["minimum_contract_seasons"], "years_after": t["years_after_signing"],
            "long_min_length": long["min_seasons"], "long_signed_before": long["signed_before"],
            "long_years_after": long["years_after_signing"], "after_extension": t["years_after_extension"],
            "rookie_deadline": t["rookie_scale_deadline_month_day"], "veteran_deadline": t["veteran_deadline_month_day"]}


def _pct(amount, pct):
    """floor(amount x pct / 100) in exact arithmetic (a limit is never passed by a rounding)."""
    return int(Fraction(int(amount)) * Fraction(str(pct)) / 100)


# -- days ----------------------------------------------------------------------------------------------------------------
def day_kinds(day):
    """{"rookie_scale", "veteran"} on October 31, {"veteran"} on June 29, from FIRST_DAY; else empty."""
    if day < FIRST_DAY:
        return set()
    md = day[5:]
    return {"rookie_scale", "veteran"} if md == ROOKIE_DAY else {"veteran"} if md == VETERAN_DAY else set()


def decision_days(through):
    """Every extension day from FIRST_DAY to `through`, oldest first."""
    out = []
    for year in range(int(FIRST_DAY[:4]), int(through[:4]) + 1):
        for d in (f"{year}-{VETERAN_DAY}", f"{year}-{ROOKIE_DAY}"):
            if FIRST_DAY <= d <= through:
                out.append(d)
    return out


def _day_before(day):
    return (date.fromisoformat(day) - timedelta(days=1)).isoformat()


def _full_years(since, day):
    a, b = date.fromisoformat(since), date.fromisoformat(day)
    return b.year - a.year - ((b.month, b.day) < (a.month, a.day))


def _season_after(season, n):
    from .seasons import label
    return label(int(season[:4]) + n)


# -- schedules -----------------------------------------------------------------------------------------------------------
def extensions_of(entry):
    """Every extension recorded on a contract entry, oldest first."""
    out = list(entry.get("earlier_extensions") or [])
    if entry.get("extension"):
        out.append(entry["extension"])
    return out


def base_schedule(entry, day=None):
    """The schedule without the seasons of the extensions signed on or after `day` (every extension when None): the
    contract in force before them."""
    drop = {s for ext in extensions_of(entry) if day is None or ext["signed_date"] >= day for s in ext["schedule"]}
    return {s: v for s, v in (entry.get("schedule") or {}).items() if s not in drop}


def without_extension(row):
    """A contract row without its extensions' seasons (the agreement it extends keeps its own term on contract pages)."""
    out = deepcopy(row)
    drop = {s for ext in extensions_of(row) for s in ext["schedule"]}
    if not drop:
        return out
    for field in ("schedule", "amount_kind", "guaranteed", "cap_amount", "amount_precision", "conditions"):
        if isinstance(out.get(field), dict):
            out[field] = {s: v for s, v in out[field].items() if s not in drop}
    for field in ("extension", "earlier_extensions", "extended_on"):
        out.pop(field, None)
    return out


def carry_fields(entry, source):
    """Copy a contract's extension record (EXTENSION_FIELDS) from the entry it is built from, in place: a trade assigns
    the extended agreement whole (`rollover.traded_in`; an in-season trade's partner asset row, `runtime/trades.py`)."""
    for field in EXTENSION_FIELDS:
        if (source or {}).get(field) is not None:
            entry[field] = deepcopy(source[field])
    return entry


def signed_extensions(root=ROOT):
    """{ledger key: [the sub-record of each signed and applied extension, oldest first]} over every season's record."""
    out = {}
    for path in sorted((Path(root) / PLAYER).glob("*/League/extension_decisions.json")):
        season = path.parts[-3]
        for d in sorted(_read(path)["decisions"], key=lambda d: d["day"]):
            if d.get("outcome") == "signed" and d.get("applied"):
                out.setdefault(d["ledger_key"], []).append(_sub_record(d, season))
    return out


def with_recorded(row, root=ROOT, key=None, known=None):
    """A contract row carrying its signed extensions. A row copied from a ledger entry without the extension fields (an
    in-season trade's asset row) gains every signed extension of the player whose seasons it schedules at the same
    amounts, so its pages, origin and carry-over see the extension; a row naming its extensions, or a player with none
    signed, is returned as it is. A copy, never the row itself, when anything is added. `known` is `signed_extensions`
    when the caller already read it."""
    key = key or row.get("bbr_id")
    if extensions_of(row) or not key:
        return row
    sched = row.get("schedule") or {}
    if not sched:
        return row
    start = min(sched)
    subs = [s for s in (signed_extensions(root) if known is None else known).get(key, [])
            if any(k in sched for k in s["schedule"]) and all(sched.get(k) == v for k, v in s["schedule"].items() if k >= start)]
    if not subs:
        return row
    out = deepcopy(row)
    if len(subs) > 1:
        out["earlier_extensions"] = subs[:-1]
    out["extension"], out["extended_on"] = subs[-1], subs[-1]["signed_date"]
    return out


def _ends_with(schedule, season):
    return bool(schedule.get(season)) and not any(s > season for s in schedule)


def _latest_extension(entry, day):
    found = [e for e in extensions_of(entry) if e["signed_date"] < day]
    return found[-1] if found else None


# -- origin of a contract --------------------------------------------------------------------------------------------------
_CACHE = {}


def _cached(key, fn):
    if key not in _CACHE:
        _CACHE[key] = fn()
    return _CACHE[key]


def clear_cache():
    _CACHE.clear()


def _ledger(season, root):
    from .league_contracts import read
    return read(season, root) or {}


def _market_events(season, root):
    """{bbr_id: [events]} of the summer market that opened `season`."""
    from .free_agency_2004 import record_for
    def load():
        out = {}
        for e in (_read(Path(root) / record_for(season)) or {}).get("events", []):
            out.setdefault(e.get("bbr_id"), []).append(e)
        return out
    return _cached(("market", str(Path(root).resolve()), season), load)


def _market_signing(b, season, root, signed=None):
    """The event that signed a player's contract in the summer market that opened `season` (the latest signing; an
    offer sheet that was not matched dates from the sheet his new club signed), or None."""
    events = _market_events(season, root).get(b, [])
    found = [e for e in events if e["kind"] in SIGN_EVENTS and (signed is None or e["date"] == signed)]
    if not found:
        return None
    e = max(found, key=lambda e: e["date"])
    if e["kind"] == "offer_sheet_not_matched":
        sheet = [x for x in events if x["kind"] == "offer_sheet" and x.get("club") == e.get("to")]
        return max(sheet, key=lambda x: x["date"]) if sheet else None
    return e


def _inventory(root):
    def load():
        out = {}
        for club in (_read(Path(root) / INVENTORY) or {"clubs": {}})["clubs"].values():
            for p in club["players"]:
                if p.get("bbr_id"):
                    out[p["bbr_id"]] = p
        return out
    return _cached(("inventory", str(Path(root).resolve())), load)


def _signing_2003(b, root):
    """The real 2003 summer signing a 2004-05 contract was built from (`contract_terms.existing_terms`: the first row
    not involving Miami with years and a total, of two or more seasons)."""
    for row in (_read(Path(root) / SIGNINGS_2003) or {"signings": []})["signings"]:
        if row.get("bbr_id") == b and not row.get("involves_miami") and row.get("years") and row.get("total") and row["years"] >= 2:
            return row
    return None


def _miami_sheet(season, root):
    return (_read(Path(root) / PLAYER / season / SHEET) or {"players": []})["players"]


def _register_ids(season, root):
    return {p["name"]: p.get("bbr_id") for p in (_read(Path(root) / PLAYER / season / REGISTER) or {"players": []})["players"]}


def _sheet_key(p, ids):
    return p.get("bbr_id") or ids.get(p["player"]) or (WADE_BBR if p["player"] == WADE else None)


def _found(signed, length, basis, source, rookie=False, extended=False):
    if not signed or not length:
        return None
    return {"signed_date": signed, "length": int(length), "basis": basis, "source": source, "rookie_scale": bool(rookie),
            "extended": bool(extended)}


def _extension_origin(ext):
    return _found(ext["signed_date"], ext["years"] + 1, f"{ext['route'].replace('_', ' ')} signed {ext['signed_date']}",
                  ext.get("record"), False, True)


def miami_origin(entry, b, season, root=ROOT, day=None):
    """Signing date and length of a Miami sheet contract: the latest extension; else the sheet's signing date with the
    market event's years, else the June 2003 inventory's term, else the sheet's term for a contract Miami signed itself
    (a traded-in entry's term counts only the seasons left, `rollover.traded_in`)."""
    entry = with_recorded(entry, root, b)
    ext = _latest_extension(entry, day or "9999-12-31")
    if ext:
        return _extension_origin(ext)
    signed = entry.get("signed_date")
    rookie = (entry.get("route") == "rookie_scale" or "rookie" in (entry.get("status") or "")
              or "rookie-scale" in (entry.get("notes") or ""))
    if not signed:
        return None
    from .seasons import next_season, season_of_date
    event = None
    if b:
        for s in sorted({next_season(season_of_date(signed)), season_of_date(signed), season}):
            event = event or _market_signing(b, s, root, signed)
    if event and event.get("years"):
        return _found(signed, event["years"], f"{event['kind'].replace('_', ' ')} {signed} (summer market record)",
                      "free_agency record", rookie or event["kind"] == "rookie_scale_signing")
    inv = _inventory(root).get(b) or {}
    if inv.get("signed_date") == signed and inv.get("original_term_seasons"):
        return _inventory_origin(inv, rookie)
    if entry.get("acquired_by") != "trade" and entry.get("original_term_seasons"):
        return _found(signed, entry["original_term_seasons"], f"signed {signed} by Miami (its cap sheet)", SHEET, rookie)
    return None


def _inventory_origin(p, rookie=False):
    """A June 2003 inventory contract: its signing date and term; one its contract history records as an extension is an
    extended contract (cbafaq05 Q52: extendable three years after the extension)."""
    extended = "extension" in (p.get("contract_text") or "").lower()
    return _found(p.get("signed_date"), p.get("original_term_seasons"),
                  f"{'extension' if extended else 'contract'} signed {p.get('signed_date')} (June 2003 contract inventory)",
                  INVENTORY.as_posix(), rookie or p.get("status") == "under_rookie_contract", extended)


def origin(bbr_id, season, root=ROOT, day=None):
    """{"signed_date", "length", "basis", "source", "rookie_scale", "extended"} of the league contract in force for
    `season`, or None when the records do not date it. Traced back season by season through the ledgers: an extension
    signed before `day`; a `new` or `rookie_scale` entry's summer market signing; a 2004-05 entry's source (the June 2003
    inventory or the real 2003 summer signing; the salary-list reconstruction has no recorded length); a Miami contract's
    cap sheet."""
    from .seasons import previous_season
    root = Path(root)
    day = day or "9999-12-31"
    t = season
    while True:
        c = _ledger(t, root).get(bbr_id)
        if c is None:
            return None
        ext = _latest_extension(c, day)
        if ext:
            return _extension_origin(ext)
        source = c.get("source") or ""
        if source.startswith("Miami contract_schedules.json"):
            ids = _register_ids(t, root)
            entry = next((p for p in _miami_sheet(t, root) if _sheet_key(p, ids) == bbr_id), None)
            return miami_origin(entry, bbr_id, t, root, day) if entry else None
        if c.get("kind") in ("new", "rookie_scale"):
            e = _market_signing(bbr_id, t, root)
            if not e:
                return None
            return _found(e["date"], e.get("years"), f"{e['kind'].replace('_', ' ')} {e['date']} ({t[:4]} summer market record)",
                          f"free_agency_{t[:4]}.json", c.get("kind") == "rookie_scale" or e["kind"] == "rookie_scale_signing")
        if t <= "2004-05":
            if source.startswith(INVENTORY.as_posix()):
                return _inventory_origin(_inventory(root).get(bbr_id) or {}, "rookie" in source)
            if source.startswith(SIGNINGS_2003.as_posix()):
                row = _signing_2003(bbr_id, root) or {}
                return _found(row.get("date"), row.get("years"),
                              f"{(row.get('kind') or 'signing').replace('_', ' ')} {row.get('date')} (real 2003 summer)",
                              SIGNINGS_2003.as_posix())
            return None
        t = previous_season(t)


# -- eligibility ---------------------------------------------------------------------------------------------------------
def holders(day, root=ROOT):
    """({bbr_id: club} for every club but Miami, Miami's held keys) at the start of `day`, the end of the day before
    (`club_truth.rosters_on`, `rotations.miami_holds`)."""
    from .club_truth import rosters_on
    from .rotations import miami_holds
    from .seasons import live_season_on
    start = _day_before(day)
    return dict(rosters_on(start, root)), set(miami_holds(live_season_on(start, root), start, root))


def _exercised(day, root):
    """{bbr_id: decision} of the rookie-scale team options on the decision season exercised on the October 31 a year
    before (`runtime/options.py`): the window Q52 opens only after the option is picked up."""
    from .options import read_record
    from .seasons import live_season_on, season_of_date
    deadline = f"{int(day[:4]) - 1}-{ROOKIE_DAY}"
    season = season_of_date(day)
    return {d["bbr_id"]: d for d in read_record(live_season_on(deadline, root), root)["decisions"]
            if d["kind"] == "team_option" and d["option_season"] == season and d["deadline"] == deadline
            and d["decision"] == "exercise"}


def _cut_short(season, first, root):
    """bbr_ids whose option on the first extension season was declined or opted out (`runtime/options.py`)."""
    from .options import read_record
    from .seasons import previous_season
    out = set()
    for s in (previous_season(season), season):
        for d in read_record(s, root)["decisions"]:
            if d["option_season"] == first and d["decision"] in ("decline", "leave"):
                out.add(d["bbr_id"])
    return out


def _moves(root):
    """{bbr_id: [the league's dated moves of him, oldest first]} over every season's `League/league_moves.json`."""
    def load():
        out = {}
        for path in sorted((Path(root) / PLAYER).glob("*/League/league_moves.json")):
            for e in (_read(path) or {}).get("entries", []):
                if e.get("bbr_id"):
                    out.setdefault(e["bbr_id"], []).append(e)
        for moves in out.values():
            moves.sort(key=lambda e: e["date"])
        return out
    return _cached(("moves", str(Path(root).resolve())), load)


def _contract_start(b, season, root, ledgers=None):
    """The earliest date the contract a season's ledger holds for a player can have been signed: June 30 of the summer
    market that made it (the first ledger season in which it is a `new` or `rookie_scale` entry, traced back through the
    `existing` ones), or "" for a contract older than the ledgers. `ledgers` memoizes the files read."""
    from .seasons import previous_season
    ledgers = {} if ledgers is None else ledgers
    t = season
    while True:
        if t not in ledgers:
            ledgers[t] = _ledger(t, root)
        c = ledgers[t].get(b)
        if c is None:
            return ""
        if c.get("kind") in ("new", "rookie_scale"):
            return f"{t[:4]}-06-30"
        t = previous_season(t)


def waiver(b, since, day, root=ROOT):
    """The waiver that ended a contract signed on `since` ("" when older than the records), or None: the first `waive` of
    the player dated from `since` to the day before `day` in the league's dated moves that no `claim` took up before the
    day (a claim assigns the contract, as a trade does; a later waiver by the claiming club ends it). The waiving club
    still owes the contract, and the deal he plays on with a later club (a ten-day, rest-of-season or market contract) is a
    new one: {"date", "club", "move"}."""
    moves = [e for e in _moves(root).get(b, []) if e["date"] < day]
    claimed = {e.get("waiver") for e in moves if e["kind"] == "claim"}
    for e in moves:
        if e["kind"] == "waive" and e["date"] >= (since or "") and e["id"] not in claimed:
            return {"date": e["date"], "club": e.get("from"), "move": e["id"]}
    return None


def eligibility(day, root=ROOT, held=None):
    """(eligible, skipped) on a decision day: eligible is [{kind, bbr_id, ledger_key, player, club, wade, final_season,
    last_salary, signed_date, length, origin, eligibility}] by club and player; skipped is [(player, club, reason)] for
    the other final-season contracts. Read-only."""
    from .club_truth import holder
    from .player_stats import alias
    from .seasons import next_season, season_of_date
    root = Path(root)
    kinds = day_kinds(day)
    season = season_of_date(day)
    rule = rules(season, root) if kinds else None
    if not kinds or rule is None:
        return [], []
    first = next_season(season)
    rosters, miami = held if held is not None else holders(day, root)
    exercised = _exercised(day, root) if "rookie_scale" in kinds else {}
    cut = _cut_short(season, first, root)
    eligible, skipped = [], []

    def consider(cand, o, rookie_contract, waived):
        b = cand["bbr_id"]
        if b in cut:
            skipped.append((cand["player"], cand["club"], f"his {first} option was declined or opted out"))
            return
        if waived:
            skipped.append((cand["player"], cand["club"],
                            f"waived by {waived['club']} on {waived['date']} ({waived['move']}): that club still owes the "
                            f"contract, and his deal with {cand['club']} is a new one, not this contract"))
            return
        if b in exercised and rookie_contract:
            d = exercised[b]
            cand.update(kind="rookie_scale", signed_date=(o or {}).get("signed_date"), length=(o or {}).get("length"),
                        origin=(o or {}).get("basis") or "rookie-scale contract",
                        eligibility=(f"rookie scale: the {season} team option exercised on {d['deadline']} by {d['club']} "
                                     f"(runtime/options.py); the window runs to {day} (cbafaq05 Q52)"))
            eligible.append(cand)
            return
        # an exercised option on a rookie-scale deal no longer in force: the contract he holds is judged as a veteran's
        if "veteran" not in kinds:
            return
        if o is None:
            skipped.append((cand["player"], cand["club"], "signing date or length not recorded"))
        elif o["rookie_scale"]:
            skipped.append((cand["player"], cand["club"], "rookie-scale contract outside its extension window"))
        elif o["length"] < rule["min_length"] and not o["extended"]:
            skipped.append((cand["player"], cand["club"], f"{o['length']}-season contract: under {rule['min_length']} "
                                                          "seasons may not be extended"))
        else:
            # Q52: an extended contract three years after the extension (its length is the extended agreement's, at least
            # the four seasons that made it extendable); six or seven seasons signed before July 1, 2005 four years.
            need = (rule["after_extension"] if o["extended"] else rule["long_years_after"]
                    if o["length"] >= rule["long_min_length"] and o["signed_date"] < rule["long_signed_before"] else rule["years_after"])
            have = _full_years(o["signed_date"], day)
            if have < need:
                skipped.append((cand["player"], cand["club"], f"signed {o['signed_date']}: {have} full year(s), {need} required"))
                return
            what = "an extended contract" if o["extended"] else f"a {o['length']}-season contract"
            cand.update(kind="veteran", signed_date=o["signed_date"], length=o["length"], origin=o["basis"],
                        eligibility=(f"veteran: {what} ({o['basis']}); {have} full years since {o['signed_date']} by {day}, "
                                     f"{need} required (cbafaq05 Q52)"))
            eligible.append(cand)

    ids = _register_ids(season, root)
    taken = set()
    for p in _miami_sheet(season, root):
        key = _sheet_key(p, ids)
        if not key or not (key in miami or alias(p["player"]) in miami) or p.get("status") == "unsigned_draft_rights":
            continue
        p = with_recorded(p, root, None if key == WADE_BBR else key)
        sched = base_schedule(p, day)
        if not _ends_with(sched, season):
            continue
        wade = key == WADE_BBR
        lkey = WADE_KEY if wade else key
        taken |= {key, lkey}
        cand = {"bbr_id": key, "ledger_key": lkey, "player": p["player"], "club": MIAMI, "wade": wade,
                "final_season": season, "last_salary": int(sched[season])}
        o = miami_origin(p, None if wade else key, season, root, day)
        # Miami's own sheet row is the contract Miami holds (a player it signed after another club's waiver has a new row)
        rookie = o["rookie_scale"] if o else (p.get("status") == "under_rookie_contract" or p.get("route") == "rookie_scale")
        consider(cand, o, rookie, None)
    ledgers = {}
    for b, c in sorted(_ledger(season, root).items()):
        if b in taken or b in miami or b == WADE_KEY:
            continue
        sched = base_schedule(c, day)
        if not _ends_with(sched, season):
            continue
        club = rosters.get(b)
        if club is None:
            club, _ = holder(b, c.get("player"), _day_before(day), root)
        if club is None or club == MIAMI:
            if club is None:
                skipped.append((c.get("player"), c.get("club"), "no club holds him"))
            continue
        cand = {"bbr_id": b, "ledger_key": b, "player": c.get("player"), "club": club, "wade": False,
                "final_season": season, "last_salary": int(sched[season])}
        o = origin(b, season, root, day)
        # the ledger's rookie flag only when no record dates the contract (it can outlive the rookie-scale deal)
        rookie = o["rookie_scale"] if o else bool(c.get("rookie_scale"))
        since = o["signed_date"] if o else _contract_start(b, season, root, ledgers)
        consider(cand, o, rookie, waiver(b, since, day, root))
    eligible.sort(key=lambda c: (c["club"], c["player"] or "", c["bbr_id"]))
    return eligible, skipped


def eligible(day, root=ROOT):
    """The players eligible for an extension on a decision day (read-only)."""
    return eligibility(day, root)[0]


# -- evidence ------------------------------------------------------------------------------------------------------------
def planning_season(day, root=ROOT):
    """The latest season whose cap figures were published by `day` (`league_cap_history.json`): never a later one."""
    from .seasons import live_season_on
    root = Path(root)
    history = None
    for season in (live_season_on(day, root), "2003-04"):
        history = _read(root / PLAYER / season / "00_Team/Finances/league_cap_history.json")
        if history:
            break
    rows = [r for r in (history or {}).get("seasons", []) if r.get("published_date") and r["published_date"] <= day]
    if not rows:
        raise ValueError(f"{day}: no published cap season in league_cap_history.json")
    return max(r["season"] for r in rows)


class Evidence:
    """What a front office knows on a decision day: the valuation dated on it (`runtime/valuation.py`: the closed season's
    production and honors announced by then), the cap rules of the planning season, service from the summer's identity,
    the closed season's standings and the availability of his real career."""

    def __init__(self, day, root=ROOT):
        from .free_agency_2004 import identity, market_year
        from .season_evidence import market_season
        from .seasons import path as season_path, previous_season, season_of_date
        from .valuation import Valuation
        self.day, self.root = day, Path(root)
        self.season = season_of_date(day)
        self.valuation = Valuation(day, self.root)
        self.closed = previous_season(market_season(day))
        self.planning = planning_season(day, self.root)
        self.rules = _read(self.root / season_path(self.planning, "cap_rules"))
        self.mid_level = int(self.rules["exceptions"]["mid_level"])
        self.tax = int(self.rules["luxury_tax_line"])
        self.cap = int(self.rules["salary_cap"])
        self.ident = identity(self.root, market_year(self.season))
        self._wins = self._standings()

    def _standings(self):
        from .seasons import club_name, dates
        from .standings import standings_on
        table = standings_on(dates(self.closed, self.root)["regular_season_end"], self.root, self.closed)
        return {club_name(c, self.season): r["pct"] for c, r in table.items()}

    def value(self, b):
        return self.valuation.value(b)

    def market_price(self, value, b):
        return self.valuation.market_price(value, b)

    def age(self, b):
        return self.valuation.age(b)

    def _totals(self, b):
        return ((getattr(self.valuation, "stats", {}) or {}).get(b) or {}).get("totals")

    def mpg(self, b):
        t = self._totals(b)
        return round(t["minutes"] / t["games"], 1) if t and t.get("games") else None

    def line(self, b):
        from .valuation import efficiency
        t = self._totals(b)
        if not t or not t.get("games"):
            return f"no {self.closed} line"
        return (f"{t['games']} games, {t['minutes'] / t['games']:.1f} minutes, {t['points'] / t['games']:.1f} points, "
                f"efficiency {efficiency(t) / t['games']:.1f} a game (simulated {self.closed})")

    def service_first(self, b):
        s = (self.ident.get(b) or {}).get("service")
        return None if s is None else s + 1

    def tier_maximum(self, service):
        from .agreement import maximum, tier
        top = (self.rules.get("maximum_salary") or {}).get(tier(service))
        return int(top) if top else maximum(service, self.cap, self.planning, self.root)

    def minimum(self, service):
        from .cba import minimum_salary
        return minimum_salary(service or 0, self.planning, root=self.root)

    def wins(self, club):
        pct = self._wins.get(club)
        return round(82 * pct, 1) if pct is not None else NEUTRAL_WINS

    def contender(self, club):
        return self._wins.get(club, 0.5) >= 50 / 82

    def retired(self, b, season):
        from .availability import status
        return status(b, season, self.root) in ("retired", "unknown")


def evidence_for(day, root=ROOT):
    return Evidence(day, root)


def payrolls(day, root=ROOT, held=None):
    """{club: committed salary for the first extension season} at the start of `day`: the league ledger's schedules
    (extensions signed on or after the day left out) by the club holding each player, Miami's counted amounts on its
    sheet for the players it holds at the start of the day (its dated holdings, never a row's later status; the latest
    contract signed by the day when a player has two rows). A contract no club holds stays with the club that owes it,
    and a waived contract (`waiver`) with the club that waived him, whoever he plays for since."""
    from .contracts import counted_amount
    from .player_stats import alias
    from .seasons import next_season, season_of_date
    root = Path(root)
    season = season_of_date(day)
    first = next_season(season)
    rosters, miami = held if held is not None else holders(day, root)
    out, ledgers = {}, {}
    for b, c in _ledger(season, root).items():
        if b in miami or b == WADE_KEY or c.get("club") == MIAMI and b not in rosters:
            continue
        amount = base_schedule(c, day).get(first)
        if amount:
            waived = (waiver(b, _contract_start(b, season, root, ledgers), day, root)
                      if any(e["kind"] == "waive" for e in _moves(root).get(b, [])) else None)
            club = (waived or {}).get("club") or rosters.get(b) or c.get("club")
            out[club] = out.get(club, 0) + int(amount)
    ids = _register_ids(season, root)
    rows = {}
    for p in _miami_sheet(season, root):
        key = _sheet_key(p, ids)
        if not key or not (key in miami or alias(p["player"]) in miami) or (p.get("signed_date") or "") > day:
            continue
        if key not in rows or (p.get("signed_date") or "") >= (rows[key].get("signed_date") or ""):
            rows[key] = p
    for key, p in rows.items():
        p = with_recorded(p, root, None if key == WADE_BBR else key)
        row = dict(p, schedule=base_schedule(p, day))
        amount = counted_amount(row, first) if first in row["schedule"] else None
        if amount:
            out[MIAMI] = out.get(MIAMI, 0) + int(amount)
    return out


# -- the decision --------------------------------------------------------------------------------------------------------
def _years_wanted(age):
    from .free_agency_2004 import YEARS_WANTED
    return next(y for limit, y in YEARS_WANTED if (age or 27) <= limit)


def ceiling(ev, club, price, committed):
    """The summer market's payroll ceiling for a club keeping its own player (`free_agency_2004.Market.ceiling` with Bird
    rights): the tax line; CONTENDER_TAX_ROOM over it for a contender; a player priced at STAR_PRICE_MLES mid-levels or
    more is kept up to STAR_TAX_ROOM over it, or half that share over the committed payroll."""
    from .free_agency_2004 import CONTENDER_TAX_ROOM, STAR_PRICE_MLES, STAR_TAX_ROOM
    if price >= STAR_PRICE_MLES * ev.mid_level:
        return int(max(ev.tax * (1 + STAR_TAX_ROOM), committed * (1 + STAR_TAX_ROOM / 2))), \
            f"a player priced at {STAR_PRICE_MLES:g} mid-levels or more: {STAR_TAX_ROOM:.0%} over the tax line or {STAR_TAX_ROOM / 2:.1%} over the committed payroll"
    if ev.contender(club):
        return int(ev.tax * (1 + CONTENDER_TAX_ROOM)), f"a contender: {CONTENDER_TAX_ROOM:.0%} over the tax line"
    return int(ev.tax), "the tax line"


def accept_chance(price, years, schedule, age, mpg, club, wins, first_season, root=ROOT):
    """(P(sign), utility gap) for an extension against free agency next summer (`runtime/player_utility.py`, no trait)."""
    from . import player_utility as pu
    wanted = _years_wanted(age)
    rate = pu.ask_raise(first_season, root)
    player = {"ask": price, "years_wanted": wanted, "prior_minutes": mpg, "prior_club": club, "age": age, "ask_raise": rate}
    role = mpg or pu.DEFAULT_MINUTES
    ext = pu.scores({"guaranteed": sum(schedule.values()), "years": years}, {"club": club, "role_minutes": role, "strength": wins}, player)
    alt = pu.scores({"guaranteed": price * sum(1 + rate * i for i in range(wanted)), "years": wanted},
                    {"club": None, "role_minutes": role, "strength": NEUTRAL_WINS}, player)
    weight = pu.weights(age, None)
    gap = round(pu.utility(ext, weight) - pu.utility(alt, weight), 2)
    return pu.odds(gap, 1, 1)["accept"], gap


def terms_for(kind, price, last, maximum, minimum, age, first_season, rule):
    """The offer: (years, first-year salary, flat raise, schedule) or None when no legal first-year salary exists."""
    if kind == "rookie_scale":
        n = min(_years_wanted(age), rule["rookie_new_seasons"])
        first = price
        step = _pct(first, rule["rookie_raise_pct"])
    else:
        n = min(_years_wanted(age), rule["veteran_total_seasons"] - 1)
        first = min(price, _pct(last, rule["veteran_first_year_pct"]), maximum)
        if first < minimum:
            return None
        step = _pct(min(first, last), rule["veteran_raise_pct"])
    schedule = {_season_after(first_season, i): first + step * i for i in range(n)}
    return n, first, step, schedule


def _normalise(options):
    probs = {k: round(v, 6) for k, v in options.items()}
    top = max(probs, key=probs.get)
    probs[top] = round(probs[top] + 1 - sum(probs.values()), 6)
    return probs


def _band(ratio):
    from .options import HIGH, LOW
    return "offer" if ratio >= HIGH else "no_offer" if ratio <= LOW else "close"


def appraise(day, cand, ev, root=ROOT):
    """The club's numbers for one eligible player on the day: {value, market_price, price, worth, age, service_first,
    mid_level, core_ratio, planning_season, maximum, minimum, line, mpg}, or {"blocked", "how"} when no call is made (his
    real career has no season after this one, or no valuation exists; Wade's missing valuation is an error)."""
    from .options import YOUNG_AGE, YOUTH_PREMIUM
    from .seasons import next_season
    rule = rules(cand["final_season"], root)
    b, last = cand["bbr_id"], cand["last_salary"]
    first = next_season(cand["final_season"])
    if ev.retired(b, first):
        return {"blocked": "retired", "how": f"his real career has no {first} season (runtime/availability.py)"}
    value = ev.value(b)
    if value is None:
        if cand["wade"]:
            raise ValueError(f"Dwyane Wade: no valuation on {day}; the extension cannot be decided")
        return {"blocked": "no_valuation", "how": f"no valuation on {day}: no closed-season evidence (never guessed)"}
    service = ev.service_first(b)
    market = ev.market_price(value, b)
    maximum = max(int(ev.tier_maximum(service)), _pct(last, rule["free_agent_max_pct"]))
    minimum = int(ev.minimum(service))
    price = int(round(min(maximum, max(minimum, market))))
    age = ev.age(b)
    young = age is not None and age <= YOUNG_AGE
    worth = int(round(price * (YOUTH_PREMIUM if young else 1.0)))
    return {"value": round(value, 3), "market_price": int(round(market)), "price": price, "worth": worth, "age": age,
            "young": young, "service_first": service, "mid_level": int(ev.mid_level),
            "core_ratio": round(worth / (CORE_MLES * ev.mid_level), 4), "planning_season": ev.planning,
            "maximum": maximum, "minimum": minimum, "line": ev.line(b), "mpg": ev.mpg(b)}


def decide(day, cand, app, ev, spent, root=ROOT):
    """(decision, packet or None) for one eligible player from his appraisal; `spent` is {club: offers made earlier that
    day} and is updated with this offer."""
    from .options import HIGH, LOW, YOUNG_AGE, YOUTH_PREMIUM
    from .seasons import next_season
    season, first = cand["final_season"], next_season(cand["final_season"])
    rule = rules(season, root)
    b, club, kind, last = cand["bbr_id"], cand["club"], cand["kind"], cand["last_salary"]
    decision = {"id": f"{day}-extension-{b}", "day": day, "kind": kind, "club": club, "player": cand["player"], "bbr_id": b,
                "ledger_key": cand["ledger_key"], "wade": cand["wade"],
                "contract": {"final_season": season, "last_salary": last, "signed_date": cand.get("signed_date"),
                             "length": cand.get("length"), "origin": cand.get("origin"), "eligibility": cand["eligibility"]},
                "evidence": None, "payroll": None, "club_call": None, "offer": None, "answer": None, "packet": None,
                "outcome": None}

    def no_offer(blocked, how):
        decision.update(club_call={"decision": "no_offer", "how": how, "p_offer": None, "blocked": blocked}, outcome="no_offer")
        return decision, None

    if app.get("blocked"):
        return no_offer(app["blocked"], app["how"])
    decision["evidence"] = {k: v for k, v in app.items() if k != "young"}
    price, worth, ratio, maximum, minimum = app["price"], app["worth"], app["core_ratio"], app["maximum"], app["minimum"]
    offer = terms_for(kind, price, last, maximum, minimum, app["age"], first, rule)
    if offer is None:
        return no_offer("minimum", f"110.5% of his ${last:,} salary is under his ${minimum:,} minimum: no legal first year")
    n, f1, step, schedule = offer
    band = _band(ratio)
    youth = f", x{YOUTH_PREMIUM} for a player {YOUNG_AGE} or younger" if app["young"] else ""
    reason = (f"worth ${worth:,} (price ${price:,}: market price ${app['market_price']:,} for his production, inside the "
              f"minimum ${minimum:,} and his maximum ${maximum:,} with {app['service_first']} years of service in {first} under "
              f"the {app['planning_season']} cap rules{youth}) against {CORE_MLES:g} x the ${app['mid_level']:,} mid-level: "
              f"ratio {ratio}")
    p_offer = None
    if band == "offer":
        call, how = "offer", f"clear: {reason}, at or above {HIGH}"
    elif band == "no_offer":
        call, how = "no_offer", f"clear: {reason}, at or below {LOW}"
    else:                                       # the close band: an engine draw for every club, Miami's call on Wade too
        p_offer = round((ratio - LOW) / (HIGH - LOW), 3)
        call, how = "draw", f"close call drawn by the engine: {reason}, inside {LOW}-{HIGH}, P(offer) {p_offer}"
        if not 0 < p_offer < 1:
            call, p_offer = ("no_offer" if p_offer <= 0 else "offer"), None
    if call == "no_offer":
        decision["club_call"] = {"decision": "no_offer", "how": how, "p_offer": None, "blocked": None}
        decision["outcome"] = "no_offer"
        return decision, None
    committed = int(ev.committed(club))
    top, top_rule = ceiling(ev, club, price, committed)
    earlier = spent.get(club, 0)
    after = committed + earlier + f1
    decision["payroll"] = {"first_season": first, "committed": committed, "earlier_offers": earlier, "offer": f1,
                           "after": after, "ceiling": top, "tax_line": ev.tax, "rule": top_rule}
    if after > top:
        return no_offer("payroll", f"{first} payroll ${committed:,} + earlier offers ${earlier:,} + ${f1:,} = ${after:,} passes "
                                   f"${top:,} ({top_rule})")
    spent[club] = earlier + f1
    decision["club_call"] = {"decision": call, "how": how, "p_offer": p_offer, "blocked": None}
    decision["offer"] = {"first_season": first, "years": n, "first_salary": f1, "raise": step, "schedule": schedule,
                         "total": sum(schedule.values()), "route": ROUTES[kind],
                         "limits": {"max_new_seasons": rule["rookie_new_seasons"] if kind == "rookie_scale" else rule["veteran_total_seasons"] - 1,
                                    "maximum": maximum, "minimum": minimum,
                                    "first_year_limit": maximum if kind == "rookie_scale" else min(maximum, _pct(last, rule["veteran_first_year_pct"])),
                                    "raise_limit": _pct(f1 if kind == "rookie_scale" else last,
                                                        rule["rookie_raise_pct"] if kind == "rookie_scale" else rule["veteran_raise_pct"])}}
    kind_text = "rookie-scale extension" if kind == "rookie_scale" else "veteran extension"
    terms_text = f"{n}-season {kind_text} from {first} (${f1:,} in {first}, raises of ${step:,} a season, ${sum(schedule.values()):,} in all)"
    if cand["wade"]:
        # his answer is his own: a clear offer opens at once, a close call is the club's draw alone (offer or no_offer)
        decision["answer"] = {"decider": "Dwyane Wade (the user)", "offer_record": None}
        if call == "offer":
            return decision, None
        packet = {"event_id": decision["id"], "date": day, "question": f"Does {club} offer {cand['player']} a {terms_text}?",
                  "decider": f"{club}'s AI/GM (drawn by rule)", "options": _normalise({"offer": p_offer, "no_offer": 1 - p_offer}),
                  "basis": (f"Club: {how}; {first} payroll ${after:,} with this offer, within ${top:,} ({top_rule}). The "
                            f"same close-band rule as every club's call (runtime/extensions.py); an offer goes to Wade, whose "
                            f"answer is his own. Eligibility: {cand['eligibility']}.")}
        return decision, packet
    p, gap = accept_chance(price, n, schedule, app["age"], app["mpg"], club, ev.wins(club), first, root)
    decision["answer"] = {"decider": f"{cand['player']} (simulated player, engine draw)", "p_accept": p, "gap": gap,
                          "years_wanted": _years_wanted(app["age"]), "wins": ev.wins(club)}
    if call == "offer":
        options = {"signed": p, "declined": 1 - p}
        question = f"Does {cand['player']} sign {club}'s {terms_text}?"
        decider = f"{cand['player']} (simulated player, engine draw)"
    else:
        options = {"signed": p_offer * p, "declined": p_offer * (1 - p), "no_offer": 1 - p_offer}
        question = f"Does {club} offer {cand['player']} a {terms_text}, and does he sign it?"
        decider = f"{club} (drawn by rule) and {cand['player']} (simulated player)"
    packet = {"event_id": decision["id"], "date": day, "question": question, "decider": decider, "options": _normalise(options),
              "basis": (f"Club: {how}; {first} payroll ${after:,} with this offer, within ${top:,} ({top_rule}). Player: "
                        f"utility gap {gap:+.2f} (this extension at {club} against free agency next summer at his price with a "
                        f"league-average club, runtime/player_utility.py, no drawn priority) gives P(sign) {p}. "
                        f"Eligibility: {cand['eligibility']} (runtime/extensions.py).")}
    return decision, packet


# -- Wade's offer --------------------------------------------------------------------------------------------------------
def _open_offer(root, season, decision):
    """Write Wade's offer record and page once and add the pending entry to the season's state: on the decision day for
    a clear offer, on the run that reads the engine's `offer` for a close call."""
    root = Path(root)
    oid = offer_id(decision["day"])
    path = offer_path(root, season, oid)
    if not path.is_file():
        e, o, pay = decision["evidence"], decision["offer"], decision["payroll"]
        basis = decision["club_call"]["how"] + (f"; the engine drew the offer ({decision['packet']})" if decision.get("packet") else "")
        record = {"schema_version": 1, "id": oid, "date": decision["day"], "season": season, "club": decision["club"],
                  "kind": decision["kind"], "decision": decision["id"],
                  "offer": {k: o[k] for k in ("first_season", "years", "first_salary", "raise", "schedule", "total", "route", "limits")},
                  "evidence": {"line": e.get("line"), "value": e["value"], "price": e["price"], "worth": e["worth"],
                               "maximum": e["maximum"], "core_ratio": e["core_ratio"], "payroll": pay["after"],
                               "ceiling": pay["ceiling"], "basis": basis},
                  "contract": decision["contract"], "status": "offered", "answer": None, "answered": None, "note": None,
                  "source_ref": None, "reply_to_version": None}
        _dump(path, record)
        (path.parent / page_name(record)).write_text(page(record, root), encoding="utf-8")
    state_path = root / PLAYER / season / "current_state.json"
    state = _read(state_path)
    if state is not None:
        pending = state.setdefault("pending_player_decisions", [])
        if PENDING_PREFIX + oid not in pending and (_read(path) or {}).get("answer") is None:
            pending.append(PENDING_PREFIX + oid)
            _dump(state_path, state)
    return path.relative_to(root).as_posix()


def close(state, oid):
    """Remove the pending entry once Wade has answered (the record itself is his)."""
    state["pending_player_decisions"] = [d for d in state.get("pending_player_decisions", []) if d != PENDING_PREFIX + oid]


def page(record, root=ROOT):
    """Wade's milestone page for an extension offer (docs/templates/player_milestones/workflow.md): identity, the actual
    offer, the evidence, the available responses and the next checkpoint."""
    o, e, c = record["offer"], record["evidence"], record["contract"]
    identity = _read(Path(root) / PLAYER / "professional_identity.json") or {}
    snaps = [s for s in identity.get("snapshots", []) if s.get("as_of", "") <= record["date"]]
    snap = max(snaps, key=lambda s: s["as_of"]) if snaps else {}
    positions = "/".join(snap.get("positions") or []) or "SG"
    rows = "\n".join(f"| {s} | ${v:,} |" for s, v in o["schedule"].items())
    kind = "rookie-scale" if record["kind"] == "rookie_scale" else "veteran"
    last_season = max(o["schedule"])
    free_year = int(c["final_season"][:4]) + 1
    after = ("restricted free agency if Miami tenders a qualifying offer, unrestricted otherwise" if record["kind"] == "rookie_scale"
             else "unrestricted free agency")
    return f"""---
type: milestone
kind: contract_extension_offer
status: open
date: {record['date']}
record: {record['id']}.json
---

# Contract extension offer: {record['club']} ({record['date']})

**{WADE}** · {record['club']} · {positions} · #{snap.get('jersey', 'N/A')} · career date {record['date']}

**State: Awaiting your response.** The career clock stops on {record['date']} until you answer (`wade_extension:{record['id']}` in `current_state.json`).

## The offer

{record['club']}'s front office offers a {o['years']}-season {kind} extension from {o['first_season']}, after the {c['final_season']} season that ends your current contract (${c['last_salary']:,} in {c['final_season']}).

| Season | Salary |
| --- | --- |
{rows}
| **Total** | **${o['total']:,}** |

First-year salary ${o['first_salary']:,}; raises of ${o['raise']:,} a season (the agreement allows ${o['limits']['raise_limit']:,}); the first year is limited to ${o['limits']['first_year_limit']:,} (cbafaq05 Q52).

## Evidence

| Item | Value |
| --- | --- |
| Current contract | {c.get('origin') or 'Not recorded'}; final season {c['final_season']} |
| Eligibility | {c['eligibility']} |
| Closed-season line | {e.get('line') or 'Not recorded'} |
| Price | ${e['price']:,}: your market price within the minimum and your maximum ${e['maximum']:,} (worth to Miami ${e['worth']:,}) |
| Front office's reason | {e['basis']} |
| Miami's {o['first_season']} payroll with the offer | ${e['payroll']:,} (ceiling ${e['ceiling']:,}) |

The evidence is what Miami's front office knows on {record['date']}: closed simulated results, honors announced by then and the published cap figures. This page is a dated offer; it is not a signed contract.

## Your response

- **Accept**: the extension is signed on the next run of the extension step (`scripts/extension_day.py --write <career date>`): your contract runs through {last_season} and you do not reach free agency in {free_year}.
- **Decline**: no contract changes. You play out {c['final_season']}; in {free_year} you go to {after}.

Record the answer with `python scripts/player_milestone.py --reply reply.json --expected-version <version of {record['id']}.json>`, where `reply.json` holds `{{"kind": "extension", "season": "{record['season']}", "event_id": "{record['id']}", "action": "accept" or "decline", "date": <career date>, "text": <your words>, "source_ref": <career file with your words>}}`.

## Next checkpoint

The extension step runs again on the same career date after your answer, applies it, and the season continues.
"""


# -- the day -------------------------------------------------------------------------------------------------------------
def _decide_day(day, season, record, root, run_day, evidence_day=None):
    held = holders(day, root)
    cands, _ = eligibility(day, root, held)
    decided, written = [], []
    done = {d["id"] for d in record["decisions"]}
    if cands:
        ev = evidence_for(evidence_day or day, root)
        committed = payrolls(day, root, held)
        ev.committed = lambda club, c=committed: c.get(club, 0)
        appraised = [(cand, appraise(day, cand, ev, root)) for cand in cands]
        spent = {}
        folder = Path(root) / draws_dir(season)
        for cand, app in sorted(appraised, key=lambda x: (-(x[1].get("worth") or 0), x[0]["bbr_id"])):
            if f"{day}-extension-{cand['bbr_id']}" in done:
                continue
            decision, packet = decide(day, cand, app, ev, spent, root)
            if packet:
                folder.mkdir(parents=True, exist_ok=True)
                path = folder / f"{packet['event_id']}.decision.json"
                if not path.exists():
                    path.write_text(json.dumps(packet, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
                    written.append(packet["event_id"])
                decision["packet"] = path.relative_to(root).as_posix()
            if cand["wade"] and decision["offer"] and decision["club_call"]["decision"] == "offer":
                decision["answer"]["offer_record"] = _open_offer(root, season, decision)
            record["decisions"].append(dict(decision, recorded_on=run_day, applied=None))
            decided.append(decision)
            done.add(decision["id"])
            if decision["club"] == MIAMI:
                _miami_note(root, season, run_day, _decision_text(decision))
    record["days"].append({"day": day, "kinds": sorted(day_kinds(day)), "eligible": len(cands), "recorded_on": run_day})
    record["days"].sort(key=lambda x: x["day"])
    return decided, written


def _decision_text(d):
    o = d.get("offer")
    head = f"{d['club']}'s {d['kind'].replace('_', '-')} extension decision on {d['player']}"
    if d["outcome"] == "no_offer":
        return f"{head}: no offer ({d['club_call']['how']}; runtime/extensions.py, League/extension_decisions.json)."
    terms = f"{o['years']} seasons from {o['first_season']}, ${o['first_salary']:,} rising ${o['raise']:,} a season (${o['total']:,})"
    if d["wade"] and d["club_call"]["decision"] == "draw":
        return (f"{head}: a close call; Miami's offer of {terms} is an engine draw ({d['packet']}), and Wade answers an "
                "offer himself (01_Free_Agency/Wade_Extension/).")
    if d["wade"]:
        return f"{head}: offer of {terms}, awaiting Wade's answer (01_Free_Agency/Wade_Extension/)."
    if d["club_call"]["decision"] == "draw":
        return f"{head}: a close call; the offer of {terms} and his answer are one engine draw ({d['packet']})."
    return f"{head}: offer of {terms}; his answer is an engine draw ({d['packet']})."


def _miami_note(root, season, day, text):
    """A dated line in Miami's current phase note (`signing.note_event`), when the note exists."""
    from .signing import Writer, note_event
    root = Path(root)
    state = _read(root / PLAYER / season / "current_state.json") or {}
    rel = PLAYER / season / state.get("current_note", "04_Training_Camp/note.md")
    if not (root / rel).is_file():
        return
    writer = Writer(root)
    note_event(writer, rel, day, text)
    writer.commit()


def _drawn(d, root):
    """The engine's result for a decision's packet, or None while it is not drawn (or there is no packet)."""
    if not d.get("packet"):
        return None
    result = Path(root) / d["packet"].replace(".decision.json", ".decision.result.json")
    return _read(result)["outcome"] if result.is_file() else None


def _resolved(d, root):
    """The outcome of a recorded decision once known: the engine's draw; for Wade, the club's drawn call (a drawn
    `no_offer` ends it) and then his own answer to the offer."""
    outcome = _drawn(d, root)
    if d.get("wade"):
        if d.get("packet"):
            if outcome is not None and outcome not in CLUB_CALLS:
                raise ValueError(f"{d['id']}: unknown drawn club call {outcome!r}")
            if outcome != "offer":
                return outcome
        offer = (d.get("answer") or {}).get("offer_record")
        if offer:
            answer = (_read(Path(root) / offer) or {}).get("answer")
            return {"accept": "signed", "decline": "declined"}.get(answer)
        return None
    if outcome is not None and outcome not in OUTCOMES:
        raise ValueError(f"{d['id']}: unknown drawn outcome {outcome!r}")
    return outcome


def _unresolved(root, before):
    """The ids of every recorded decision of a day before `before` not yet applied (a draw or Wade's answer pending)."""
    out = []
    for path in sorted((Path(root) / PLAYER).glob("*/League/extension_decisions.json")):
        out += [x["id"] for x in _read(path)["decisions"] if x["day"] < before and not x.get("applied")]
    return out


def missed(d, clock):
    """The message for an extension day the career clock passed without deciding it."""
    return (f"extension day {d} was missed (the career clock is {clock}): a day is decided only on its own date, with the "
            "holders, evidence and payrolls of that date, and never late, since later systems have used the contracts "
            "since; a missed day needs a decision (runtime/extensions.py)")


def run(day, root=ROOT, evidence_day=None):
    """Decide the extension day the career clock is on, if `day` reaches it and it is not yet closed, write the draw
    packets and Wade's offer, and apply drawn or answered outcomes of every closed day up to `day`. Idempotent. Refuses
    (`ExtensionError`, nothing written for that day) a day the clock has passed or not reached, a day whose league year
    is not live, and a day while a decision of an earlier day is unresolved. Returns (decided now, packet event ids
    written, applied ids, Wade's offer ids waiting)."""
    from .seasons import live_season_on, season_of_date
    root = Path(root)
    decided, written, applied, waiting = [], [], [], []
    days = decision_days(day)
    clock = _clock(root) if days else None
    seasons = []
    for d in days:
        season = season_of_date(d)
        record = read_record(season, root)
        before = json.dumps(record, sort_keys=True)
        if d not in {x["day"] for x in record["days"]}:
            if clock is None or d < clock:
                raise ExtensionError(missed(d, clock))
            if d > clock:
                raise ExtensionError(f"extension day {d} is ahead of the career clock {clock}: a day is decided on its own "
                                     "date, never before it")
            if live_season_on(d, root) != season:
                raise ExtensionError(f"extension day {d}: the {season} records are not live (its rollover has not run)")
            earlier = _unresolved(root, d)
            if earlier:
                raise ExtensionError(f"extension day {d} cannot be decided while earlier extension decisions are "
                                     f"unresolved (a draw or Wade's answer pending): {', '.join(earlier)}")
            new, packets = _decide_day(d, season, record, root, d, evidence_day)
            decided += new
            written += packets
        if season not in seasons:
            seasons.append(season)
        applied += apply(record, season, root, day)
        if json.dumps(record, sort_keys=True) != before or not (root / record_path(season)).is_file():
            _dump(root / record_path(season), record)
    for season in seasons:
        for d in read_record(season, root)["decisions"]:
            if d["outcome"] is None and (d.get("answer") or {}).get("offer_record"):
                waiting.append(Path(d["answer"]["offer_record"]).stem)
    return decided, written, applied, waiting


# -- application ---------------------------------------------------------------------------------------------------------
def _sub_record(d, season):
    o = d["offer"]
    return {"id": d["id"], "kind": d["kind"], "route": o["route"], "signed_date": d["day"], "club": d["club"],
            "first_season": o["first_season"], "years": o["years"], "first_salary": o["first_salary"], "raise": o["raise"],
            "schedule": dict(o["schedule"]), "total": o["total"], "record": record_path(season).as_posix()}


def _extend(entry, sub, from_season, sheet=False):
    """Add an extension to a contract entry, in place, once: its seasons from `from_season` on join the schedule."""
    if any(e["id"] == sub["id"] for e in extensions_of(entry)):
        return False
    if entry.get("extension"):
        entry.setdefault("earlier_extensions", []).append(entry.pop("extension"))
    seasons = {s: v for s, v in sub["schedule"].items() if s >= from_season}
    entry["schedule"] = dict(sorted({**(entry.get("schedule") or {}), **seasons}.items()))
    entry["extension"] = deepcopy(sub)
    entry["extended_on"] = sub["signed_date"]
    note = (f"{sub['route'].replace('_', ' ')} signed {sub['signed_date']} with {sub['club']}: {sub['years']} seasons from "
            f"{sub['first_season']}, ${sub['total']:,} (runtime/extensions.py, {sub['record']})")
    entry.setdefault("extension_history", []).append(note)
    if sheet:
        entry["amount_kind"] = dict(sorted({**(entry.get("amount_kind") or {}), **{s: "contract_salary" for s in seasons}}.items()))
        if isinstance(entry.get("guaranteed"), dict):
            entry["guaranteed"] = dict(sorted({**entry["guaranteed"], **seasons}.items()))
        entry["notes"] = ((entry.get("notes") or "") + f" Extended {sub['signed_date']}: {note}.").strip()
        entry.setdefault("sources", []).append(sub["record"])
    return True


def _later_seasons(season, root):
    from .seasons import live_seasons
    return [s for s in live_seasons(root) if s >= season]


def _write_extension(d, season, root, day):
    """A signed extension into the league ledger of its season and every later one already written, and for Miami into
    its cap sheet(s), the contract archive and the phase note (Wade: his dated identity and state too)."""
    from .contract_archive import _player_id, archive_contract
    from .league_contracts import ledger_path
    from .signing import Writer, refresh_schedule_totals
    root = Path(root)
    sub = _sub_record(d, season)
    for s in _later_seasons(season, root):
        path = root / ledger_path(s)
        data = _read(path)
        if not data:
            continue
        entry = next((c for c in data["contracts"] if c["bbr_id"] == d["ledger_key"]), None)
        if entry and _extend(entry, sub, s):
            _dump(path, data)
    if d["club"] != MIAMI:
        return
    for s in _later_seasons(season, root):
        path = root / PLAYER / s / SHEET
        sheet = _read(path)
        if not sheet:
            continue
        ids = _register_ids(s, root)
        entry = next((p for p in sheet["players"] if _sheet_key(p, ids) == d["bbr_id"] or p["player"] == d["player"]), None)
        if entry and _extend(entry, sub, s, sheet=True):
            refresh_schedule_totals(sheet)
            _dump(path, sheet)
    writer = Writer(root)
    pid = _player_id(writer, {"player": d["player"]}, d["bbr_id"])
    o = d["offer"]
    contract = {"player": d["player"], "bbr_id": None if d["wade"] else d["bbr_id"], "status": "under_contract",
                "schedule": dict(o["schedule"]), "amount_kind": {s: "contract_salary" for s in o["schedule"]},
                "guaranteed": dict(o["schedule"]), "signed_date": d["day"], "route": o["route"],
                "original_term_seasons": o["years"], "start_season": o["first_season"], "end_season": max(o["schedule"]),
                "full_original_schedule": True, "contract_id": f"{pid}-{d['day']}",
                "extends": {"final_season": d["contract"]["final_season"], "signed_date": d["contract"]["signed_date"]},
                "notes": (f"{o['route'].replace('_', ' ').capitalize()} signed {d['day']}: {o['years']} seasons from "
                          f"{o['first_season']}, ${o['first_salary']:,} rising ${o['raise']:,} a season; it follows the agreement "
                          f"ending with {d['contract']['final_season']}."),
                "sources": [record_path(season).as_posix()]}
    archive_contract(writer, contract, day, event="signed", source=record_path(season).as_posix(), player_id=pid,
                     signing_team=MIAMI)
    writer.commit()
    _miami_note(root, season, day, f"{d['player']} signs his {o['route'].replace('_', ' ')}: {o['years']} seasons from "
                                   f"{o['first_season']} (${o['total']:,}); runtime/extensions.py, League/extension_decisions.json.")
    if d["wade"]:
        _wade_status(root, season, day, d)


def _wade_status(root, season, day, d):
    """Wade's dated identity snapshot and live contract status after he signs (as `signing.player_status_snapshot`)."""
    o = d["offer"]
    text = f"{o['route'].replace('_', ' ').capitalize()} signed {d['day']}: {o['years']} seasons from {o['first_season']} (${o['total']:,})"
    path = root / PLAYER / "professional_identity.json"
    identity = _read(path)
    if identity and identity.get("snapshots"):
        snaps = [s for s in identity["snapshots"] if s["as_of"] <= day]
        if snaps:
            snap = dict(max(snaps, key=lambda s: s["as_of"]))
            contract = snap.get("contract") or ""
            if text not in contract:
                contract = f"{contract}; {text}" if contract else text
            snap.update(as_of=day, source_state=f"{season}/current_state.json",
                        source_event=f"{season}/League/extension_decisions.json", contract=contract)
            identity["snapshots"] = sorted([s for s in identity["snapshots"] if s["as_of"] != day] + [snap], key=lambda s: s["as_of"])
            _dump(path, identity)
    state_path = root / PLAYER / season / "current_state.json"
    state = _read(state_path)
    if state is not None:
        state["contract_status"] = ("rookie_scale_contract_extended" if d["kind"] == "rookie_scale" else "under_contract_extended")
        _dump(state_path, state)


def apply(record, season, root=ROOT, day=None):
    """Write every resolved outcome into the records (only a signed extension changes a contract). Idempotent; returns
    the ids applied now."""
    root = Path(root)
    applied = []
    for d in record["decisions"]:
        if d.get("applied"):
            continue
        if d["outcome"] is None and d["wade"] and _drawn(d, root) == "offer" and not (d.get("answer") or {}).get("offer_record"):
            d["answer"]["offer_record"] = _open_offer(root, season, d)      # Miami's drawn offer: now Wade's to answer
        if d["outcome"] is None:
            outcome = _resolved(d, root)
            if outcome is None:
                continue
            d["outcome"] = outcome
        if d["outcome"] == "signed":
            _write_extension(d, season, root, day or d["day"])
        elif d["club"] == MIAMI and d.get("offer"):
            _miami_note(root, season, day or d["day"], f"{d['player']} does not sign "
                        + ("Miami's extension offer" if d["outcome"] == "declined" else "an extension: Miami makes no offer after the draw")
                        + " (runtime/extensions.py).")
        d["applied"] = day or d["day"]
        applied.append(d["id"])
    return applied


def reapply(entries, season, root=ROOT):
    """Apply the season's signed extensions to rebuilt ledger entries (a rebuild never undoes one); in place."""
    for d in read_record(season, root)["decisions"]:
        if d.get("outcome") == "signed" and d.get("applied") and d["ledger_key"] in entries:
            _extend(entries[d["ledger_key"]], _sub_record(d, season), season)
    return entries


# -- driver helpers ------------------------------------------------------------------------------------------------------
def pending(root=ROOT):
    """{"draws": [packets without a result], "wade": [unanswered offer ids]} over every season's record."""
    root = Path(root)
    out = {"draws": [], "wade": []}
    for path in sorted((root / PLAYER).glob("*/League/extension_decisions.json")):
        for d in _read(path)["decisions"]:
            if d["outcome"] is not None:
                continue
            if d.get("packet") and not (root / d["packet"].replace(".decision.json", ".decision.result.json")).is_file():
                out["draws"].append(d["packet"])
            offer = (d.get("answer") or {}).get("offer_record")
            if offer and (_read(root / offer) or {}).get("answer") is None:
                out["wade"].append(Path(offer).stem)
    return out


def rollover_blockers(old, clock, root=ROOT):
    """What stops the rollover out of `old`: an extension day of its league year the clock passed without deciding it
    (missed: it needs a decision, never a late run), or a decision whose outcome is not applied (the next ledger is built
    from this one, so every extension must be in it first). `Rollover.blockers` raises them once the rollover is due."""
    from .seasons import season_of_date
    if old < season_of_date(FIRST_DAY):
        return []
    record = read_record(old, root)
    closed = {x["day"] for x in record["days"]}
    out = [missed(d, clock) for d in decision_days(clock) if season_of_date(d) == old and d not in closed and d < clock]
    out += [f"extension {d['id']} not resolved (a draw or Wade's answer pending)" for d in record["decisions"] if not d.get("applied")]
    return out


def catalog_rows(root=ROOT, cutoff=None):
    """[(row, club, record path, as_of)] for every signed extension known by `cutoff`: its own agreement on the contract
    pages (`player_contracts.build_contract_catalog`)."""
    root = Path(root)
    out = []
    for path in sorted((root / PLAYER).glob("*/League/extension_decisions.json")):
        for d in _read(path)["decisions"]:
            if d.get("outcome") != "signed" or not d.get("applied") or (cutoff and max(d["day"], d["applied"]) > cutoff):
                continue
            o = d["offer"]
            row = {"player": d["player"], "bbr_id": None if d["wade"] else d["bbr_id"], "status": "under_contract",
                   "signed_date": d["day"], "signing_team": d["club"], "route": o["route"].replace("_", " "),
                   "original_term_seasons": o["years"], "start_season": o["first_season"], "end_season": max(o["schedule"]),
                   "schedule": dict(o["schedule"]), "amount_kind": {s: "contract_salary" for s in o["schedule"]},
                   "guaranteed": dict(o["schedule"]), "full_original_schedule": True,
                   "notes": (f"{o['route'].replace('_', ' ').capitalize()} signed {d['day']} with {d['club']}: {o['years']} seasons, "
                             f"${o['first_salary']:,} rising ${o['raise']:,} a season. It follows the agreement ending with "
                             f"{d['contract']['final_season']} ({d['contract'].get('origin') or 'signing not recorded'}), "
                             "which stays in force until then (runtime/extensions.py).")}
            out.append((row, d["club"], path, max(d["day"], d["applied"])))
    return out


# -- validation ----------------------------------------------------------------------------------------------------------
def _clock(root):
    dates = [(_read(p) or {}).get("current_date") for p in (Path(root) / PLAYER).glob("????-??/current_state.json")]
    dates = [d for d in dates if d]
    return max(dates) if dates else None


_REPLAY = {}


def _replayed(day, root):
    key = (str(Path(root).resolve()), day)
    if key not in _REPLAY:
        _REPLAY[key] = {c["bbr_id"] for c in eligibility(day, root)[0]}
    return _REPLAY[key]


def _offer_errors(d, rel):
    from .seasons import next_season
    errors = []
    o, c = d["offer"], d["contract"]
    first = next_season(c["final_season"])
    lim = o.get("limits") or {}
    seasons = sorted(o["schedule"])
    if seasons != [_season_after(first, i) for i in range(len(seasons))] or o["first_season"] != first:
        errors.append(f"{rel}: {d['id']}: the offer's seasons must run on from {first}")
    if len(seasons) != o["years"] or not 1 <= o["years"] <= lim.get("max_new_seasons", 0):
        errors.append(f"{rel}: {d['id']}: {o['years']} seasons outside the agreement's limit")
    if not lim.get("minimum", 0) <= o["first_salary"] <= lim.get("first_year_limit", -1) or o["first_salary"] > lim.get("maximum", -1):
        errors.append(f"{rel}: {d['id']}: first-year salary ${o['first_salary']:,} outside the minimum and the first-year limit")
    if d["kind"] == "veteran" and o["first_salary"] > lim.get("first_year_limit", -1):
        errors.append(f"{rel}: {d['id']}: a veteran's first year passes 110.5% of his last salary")
    if o["raise"] > lim.get("raise_limit", -1) + 1:
        errors.append(f"{rel}: {d['id']}: raise ${o['raise']:,} passes the agreement's ${lim.get('raise_limit'):,}")
    if [o["schedule"][s] for s in seasons] != [o["first_salary"] + o["raise"] * i for i in range(len(seasons))]:
        errors.append(f"{rel}: {d['id']}: the schedule must rise by equal flat raises from the first year")
    if o["total"] != sum(o["schedule"].values()):
        errors.append(f"{rel}: {d['id']}: total does not match the schedule")
    return errors


def extension_errors(root=ROOT, replay=True):
    """Every extension day the clock passed is decided, each on its own date; every record is well formed, decided by
    the rule (a clear call never drawn, a close call always drawn, Miami's on Wade included, packets matching the
    recorded chances), its offer within the agreement's limits, applied into the ledgers (and Miami's sheet and archive)
    exactly when signed, absent from the next summer's pool, and in agreement with Wade's answer and the pending list.
    With `replay`, each closed day's eligible set is recomputed from the start-of-day holders."""
    from .free_agency_2004 import record_for
    from .league_contracts import ledger_path
    from .options import HIGH, LOW
    from .seasons import live_seasons, next_season, season_of_date
    root = Path(root)
    clock = _clock(root)
    errors = []
    if not clock:
        return errors
    seasons = live_seasons(root) if (root / PLAYER).is_dir() else []
    for d in decision_days(clock):
        season = season_of_date(d)
        if d < clock and season in seasons and d not in {x["day"] for x in read_record(season, root)["days"]}:
            errors.append(f"{record_path(season).as_posix()}: {missed(d, clock)}")
    archive = _read(root / PLAYER / "Contracts/contract_records.json") or {"records": []}
    archived = {r["contract_id"] for r in archive["records"] if r.get("event") == "signed"}
    for path in sorted((root / PLAYER).glob("*/League/extension_decisions.json")):
        season = path.parts[-3]
        rel = path.relative_to(root).as_posix()
        record = _read(path)
        if record.get("kind") != "extension_decisions" or record.get("season") != season:
            errors.append(f"{rel}: needs kind extension_decisions and season {season}")
            continue
        state = _read(root / PLAYER / season / "current_state.json") or {}
        wade_pending = [p for p in state.get("pending_player_decisions", []) if p.startswith(PENDING_PREFIX)]
        days = {}
        for x in record["days"]:
            if not day_kinds(x["day"]) or x.get("kinds") != sorted(day_kinds(x["day"])):
                errors.append(f"{rel}: {x['day']} is not an extension day or names the wrong kinds")
            if season_of_date(x["day"]) != season or not (FIRST_DAY <= x["day"] <= clock):
                errors.append(f"{rel}: day {x['day']} outside {season} or after the clock {clock}")
            if x.get("recorded_on") != x["day"]:
                errors.append(f"{rel}: day {x['day']} recorded on {x.get('recorded_on')}: a day is decided on its own date")
            days[x["day"]] = x
        seen, offers = set(), set()
        ledgers = {s: {c["bbr_id"]: c for c in (_read(root / ledger_path(s)) or {"contracts": []})["contracts"]}
                   for s in _later_seasons(season, root)}
        for d in record["decisions"]:
            key = (d["day"], d["bbr_id"])
            if key in seen:
                errors.append(f"{rel}: two decisions for {d['player']} on {d['day']}")
            seen.add(key)
            if d["id"] != f"{d['day']}-extension-{d['bbr_id']}":
                errors.append(f"{rel}: {d['id']}: id must be <day>-extension-<bbr_id>")
            if d["day"] not in days or d["kind"] not in day_kinds(d["day"]):
                errors.append(f"{rel}: {d['id']}: its day is not closed in days or the kind is not decided that day")
            if d.get("recorded_on") != d["day"]:
                errors.append(f"{rel}: {d['id']}: recorded on {d.get('recorded_on')}: a day is decided on its own date")
            if d["outcome"] not in (None,) + OUTCOMES:
                errors.append(f"{rel}: {d['id']}: unknown outcome {d['outcome']!r}")
            call = d.get("club_call") or {}
            e = d.get("evidence") or {}
            if call.get("blocked") in (None, "payroll", "minimum") and e:
                ratio = round(e["worth"] / (CORE_MLES * e["mid_level"]), 4)
                band = _band(ratio)
                if ratio != e.get("core_ratio"):
                    errors.append(f"{rel}: {d['id']}: core ratio does not follow from the recorded worth and mid-level")
                if call.get("blocked") is None:
                    if band != "close" and call.get("decision") != band:
                        errors.append(f"{rel}: {d['id']}: a clear call ({band}) recorded as {call.get('decision')}")
                    if band == "close" and call.get("decision") != "draw" and 0 < round((ratio - LOW) / (HIGH - LOW), 3) < 1:
                        errors.append(f"{rel}: {d['id']}: a close call must be drawn by the engine (Miami's call on Wade too)")
                    if call.get("decision") == "draw" and (band != "close"
                                                           or call.get("p_offer") != round((ratio - LOW) / (HIGH - LOW), 3)):
                        errors.append(f"{rel}: {d['id']}: a drawn club call needs the close band and its recorded chance")
            if (call.get("decision") == "no_offer") != (d["outcome"] == "no_offer" and d.get("offer") is None):
                errors.append(f"{rel}: {d['id']}: the club's call and the outcome disagree")
            if d.get("offer"):
                errors += _offer_errors(d, rel)
                pay = d.get("payroll") or {}
                if pay.get("after") != pay.get("committed", 0) + pay.get("earlier_offers", 0) + d["offer"]["first_salary"] \
                        or pay.get("after", 0) > pay.get("ceiling", -1):
                    errors.append(f"{rel}: {d['id']}: the offer's payroll does not reconcile or passes the ceiling")
            packet = d.get("packet")
            if d["wade"]:
                # Wade's answer is his own; the only packet is Miami's drawn close call (offer or no_offer)
                club_draw = None
                if packet:
                    data = _read(root / packet)
                    po = call.get("p_offer")
                    if call.get("decision") != "draw" or not d.get("offer") or not isinstance(po, (int, float)):
                        errors.append(f"{rel}: {d['id']}: Wade's only packet is Miami's drawn close call")
                    elif not data or data.get("event_id") != d["id"] or \
                            data.get("options") != _normalise({"offer": po, "no_offer": 1 - po}):
                        errors.append(f"{rel}: {d['id']}: packet {packet} missing, misnamed or off the recorded chance")
                    club_draw = _drawn(d, root)
                    if club_draw is None and d["outcome"] is not None:
                        errors.append(f"{rel}: {d['id']}: outcome recorded before Miami's call was drawn")
                    if (club_draw == "no_offer") != (d["outcome"] == "no_offer"):
                        errors.append(f"{rel}: {d['id']}: outcome {d['outcome']} disagrees with Miami's drawn call {club_draw!r}")
                elif call.get("decision") == "draw":
                    errors.append(f"{rel}: {d['id']}: Miami's close call on Wade needs its draw packet")
                made = bool(d.get("offer")) and (call.get("decision") == "offer" or club_draw == "offer")
                if not made and (d.get("answer") or {}).get("offer_record"):
                    errors.append(f"{rel}: {d['id']}: an offer record without Miami's offer")
                if made:
                    offer_rel = (d.get("answer") or {}).get("offer_record")
                    offer = _read(root / offer_rel) if offer_rel else None
                    if not offer:
                        errors.append(f"{rel}: {d['id']}: Wade's offer record is missing (a drawn offer opens on the next "
                                      "run of the extension step that day)")
                    else:
                        offers.add(offer["id"])
                        if not (root / offer_rel).with_name(page_name(offer)).is_file():
                            errors.append(f"{offer_rel}: missing page {page_name(offer)}")
                        expected = {"accept": "signed", "decline": "declined", None: None}.get(offer.get("answer"), "?")
                        if d["outcome"] != expected:
                            errors.append(f"{rel}: {d['id']}: outcome {d['outcome']} disagrees with Wade's answer {offer.get('answer')!r}")
                        if (offer.get("answer") is None) != (offer.get("status") == "offered") or \
                                (offer.get("answer") is None) != (offer.get("answered") is None):
                            errors.append(f"{offer_rel}: status and answered must follow the answer")
                        if offer.get("answered") and not (offer["date"] <= offer["answered"] <= clock):
                            errors.append(f"{offer_rel}: answered outside the offer date and the clock")
                        if (offer.get("answer") is None) != (PENDING_PREFIX + offer["id"] in wade_pending):
                            errors.append(f"{offer_rel}: pending_player_decisions must list it exactly while it is unanswered")
            elif d.get("offer"):
                if not packet:
                    errors.append(f"{rel}: {d['id']}: an offer needs its draw packet")
                else:
                    data = _read(root / packet)
                    if not data or data.get("event_id") != d["id"]:
                        errors.append(f"{rel}: {d['id']}: packet {packet} missing or misnamed")
                    else:
                        p, po = (d.get("answer") or {}).get("p_accept"), call.get("p_offer")
                        want = None
                        if isinstance(p, (int, float)) and call.get("decision") == "offer":
                            want = {"signed": p, "declined": 1 - p}
                        elif isinstance(p, (int, float)) and call.get("decision") == "draw" and isinstance(po, (int, float)):
                            want = {"signed": po * p, "declined": po * (1 - p), "no_offer": 1 - po}
                        if want is None or data["options"] != _normalise(want):
                            errors.append(f"{rel}: {d['id']}: packet chances differ from the recorded call and answer")
                        result = _read(root / packet.replace(".decision.json", ".decision.result.json"))
                        if result is not None and d["outcome"] != result.get("outcome"):
                            errors.append(f"{rel}: {d['id']}: outcome {d['outcome']} differs from the drawn {result.get('outcome')}")
                        if result is None and d["outcome"] is not None:
                            errors.append(f"{rel}: {d['id']}: outcome recorded before the draw")
            elif packet:
                errors.append(f"{rel}: {d['id']}: a packet without an offer")
            if d["outcome"] is None and d.get("applied"):
                errors.append(f"{rel}: {d['id']}: applied without an outcome")
            signed = d["outcome"] == "signed" and d.get("applied")
            for s, ledger in ledgers.items():
                c = ledger.get(d["ledger_key"])
                if c is None:
                    continue
                has = any(x["id"] == d["id"] for x in extensions_of(c))
                if signed and (not has or any(c["schedule"].get(k) != v for k, v in d["offer"]["schedule"].items() if k >= s)):
                    errors.append(f"{ledger_path(s).as_posix()}: {d['player']} lacks the signed extension {d['id']}")
                if not signed and has:
                    errors.append(f"{ledger_path(s).as_posix()}: {d['player']} carries extension {d['id']}, which was not signed")
            if signed and d["club"] == MIAMI:
                sheet = _miami_sheet(season, root)
                ids = _register_ids(season, root)
                entry = next((p for p in sheet if _sheet_key(p, ids) == d["bbr_id"] or p["player"] == d["player"]), None)
                if not entry or not any(x["id"] == d["id"] for x in extensions_of(entry)):
                    errors.append(f"{rel}: {d['id']}: Miami's {season} cap sheet lacks the signed extension")
                from .contract_archive import _player_id
                from .signing import Writer
                if f"{_player_id(Writer(root), {'player': d['player']}, d['bbr_id'])}-{d['day']}" not in archived:
                    errors.append(f"{rel}: {d['id']}: the contract archive lacks the signed extension")
            if signed:
                # The next summer must see a contract, not an expiring one: no qualifying offer or re-signing for him and
                # no pool row with his club's rights (a player waived since is a free agent by his waiver, not by this).
                market = _read(root / record_for(d["offer"]["first_season"]))
                if market:
                    keys = {d["bbr_id"], d["ledger_key"]}
                    if any(e.get("bbr_id") in keys and e["kind"] in ("qualifying_offer", "qualifying_offer_accepted", "re_sign")
                           for e in market.get("events", [])) or \
                            any(p.get("bbr_id") in keys and p.get("rights") for p in market.get("unsigned_pool", [])):
                        errors.append(f"{record_for(d['offer']['first_season']).as_posix()}: {d['player']} was extended "
                                      f"({d['id']}) but the market treats his contract as expiring")
        for p in wade_pending:
            if p[len(PENDING_PREFIX):] not in offers:
                errors.append(f"{PLAYER.as_posix()}/{season}/current_state.json: pending {p} has no extension offer")
        if replay:
            for day in sorted(days):
                recorded = {d["bbr_id"] for d in record["decisions"] if d["day"] == day}
                again = _replayed(day, root)
                if recorded != again:
                    errors.append(f"{rel}: {day}: recorded decisions {sorted(recorded - again)} not eligible on replay, "
                                  f"eligible {sorted(again - recorded)} not decided")
    return errors
