"""Draft rights by draft year: Required Tenders and how long a club keeps its pick's exclusive rights.

A team keeps the exclusive right to sign its pick until the next draft only if it makes a Required
Tender: a First Round Pick's by July 15 after the draft (a rookie-scale offer at 80% or more of scale),
a Second Round Pick's in the two weeks before September 5 (one season at the minimum). Without one, a
first-round pick becomes a rookie free agent on July 16 and a second-round pick on September 6. A
tendered pick who has not signed by the next draft leaves the team's exclusive rights and may be
drafted again (1999 CBA Article X, Section 3 and Article I (vv); 1999 FAQ Q40; 2005 FAQ Q43).

Season-aware (roadmap S1, October 2026). A pick's rules are those of the agreement in force for the
league year his contract belongs to (`runtime/agreement.terms`): the 2003 and 2004 drafts under the
1999 agreement, the 2005 draft on under the 2005 agreement. Each agreement's rules are data, the
`required_tenders` section of its library rules file (`library/2003/league/nba_1999_cba_rules.json`,
`library/2005/league/nba_2005_cba_rules.json`), every value with its source and status. The 2005 FAQ
gives the same deadlines (Q102) and the same end of rights (Q43); it does not give the start of the
second-round window, so the 1999 start is kept there as a documented assumption. A draft's date comes
from the year's offseason calendar (`draft`), the calendar of the season it closes (`draft_<year>`) or
the year's draft class (`date`); a date the check needs and the library lacks is an error, never a guess.

A pick's draft year, round and number come from his register entry (`draft_year`, `draft_round`,
`draft_pick`), else Miami's pick in a simulated draft record (`<season>/09_Draft/draft_<year>.json`),
else the season's contract sheet (`draft_round`, `draft_pick`), else his tender; the year last falls
back to the register's own season (a pick joins the register of the season after his draft: the opening
checkpoint for 2003, the rollover later).

`required_tenders.json` (00_Team/Transactions of any season folder through the one checked) holds
Miami's tenders with their dates. Validation checks every season's register at that season's own date,
through the live season (`runtime/seasons.active`, so the regression suite's pinned 2003-04 replays as
before): it refuses an unsigned pick without a tender once his window has closed, a tender outside its
window or recorded for the wrong round, and a pick still held on or after the next draft. A pick whose
window is still open is held on the draft alone (the first version refused him from the day after the
draft; no record or test depended on that, and the agreement only takes the rights away at the deadline).
A tender is matched to the pick's own draft year only; another draft's tender to the same player is never
checked against this draft's window. Held rights are an explicit set of register statuses (`HELD`); a
status naming the end of the rights (`ENDED_WORDS`) is not held, and any other draft-rights spelling is
refused rather than read either way.

The writers keep those records without a hand edit (`scripts/offseason_day.py`, every summer day):
- `record_tenders`: once a summer's market record is closed, Miami's routine Required Tender to each of
  its picks of that draft that has no signing dated by his deadline, entered on the deadline with the
  rule's terms and marked `reconstructed` (the November 11, 2003 precedent: the tender is a routine filing,
  and the market itself holds every unsigned pick under his drafting club's rights through the summer).
  It is filed in the summer's own folder (the closed season's, `free_agency_2004.record_path`), so the
  rollover that carries the pick finds it.
- `end_rights`: on and after a pick's next draft (or the end of a recorded retained basis), his rights end
  on the live register (`seasons.live_season_on`): status `ENDED` with a dated control line, his holding
  closed on that date (world rule 2 ends with it), the contract-sheet row and any unassigned-rights row of
  the depth chart, and a dated `rights_ended` entry in that season's `required_tenders.json`.

Section 4 (a pick under contract with a non-NBA team keeps the team's rights until one year after that
obligation ends) and the college rule are not modelled: no pipeline decides that a pick is abroad. A
register entry that records such a basis is handled explicitly, checked against its own record instead of
the tender and the next draft (`retained_basis`): `draft_rights_retained` = {"rule": "non_nba_contract" |
"college", "until": the date the rights end or null while it is not known, "source": its evidence}. It is
refused for a rule the agreement does not provide, a record without a source, or an `until` that has
passed. A status that marks him abroad (`unsigned_draft_rights_abroad`) is no record: without a
`draft_rights_retained` entry it is refused and the pick is checked like any other.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAYER = Path("career/Dwyane_Wade")
MIAMI = "Miami Heat"
RULES = {"1999": Path("library/2003/league/nba_1999_cba_rules.json"),
         "2005": Path("library/2005/league/nba_2005_cba_rules.json")}
# The 2005 agreement's article numbers are not in the repository's sources: its rule is cited by the FAQ question.
CITE = {"1999": "1999 CBA Art. X §3", "2005": "2005 CBA, FAQ Q102"}
RETAINED_RULES = ("non_nba_contract", "college")
# Register statuses that mean Miami holds a pick's unsigned rights (the opening checkpoint's, the contract ledger's,
# the rollover's and the abroad mark); a status naming one of ENDED_WORDS is a pick whose rights ended.
HELD = ("unsigned_draft_rights", "unsigned_first_round_draft_rights", "unsigned_second_round_draft_rights",
        "draft_rights_unsigned", "unsigned_draft_rights_abroad")
ENDED_WORDS = ("released", "renounced", "expired", "ended", "lapsed")
# The status `end_rights` writes: 'released' is the departure word every register reader already knows (miami_cards,
# team_status, jerseys, continuity, rotations, write_back, camp, club_strength), and it carries no 'draft_rights', which
# roster_moves, gm and the 2003 market driver read as rights still held. The control line says why they ended.
ENDED = "rights_released"
# Market events that put a pick under contract (runtime/free_agency_2004.py).
SIGN_KINDS = ("signing", "re_sign", "rookie_scale_signing", "camp_signing", "qualifying_offer_accepted", "offer_sheet_matched")

# The opening season's records (the first version of this module was written for them; tests read them).
SEASON = "2003-04"
TEAM = PLAYER / SEASON / "00_Team"
TENDERS = TEAM / "Transactions/required_tenders.json"


def read(rel, root=ROOT):
    path = Path(root) / rel
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def _library(rel, root=ROOT):
    """World data from the given repository, or from this one when a scratch copy lacks it (read-only, the same for
    every copy, as `runtime/seasons._read`)."""
    found = read(rel, root)
    return found if found is not None else read(rel, ROOT)


def _value(entry):
    return entry.get("value") if isinstance(entry, dict) else entry


def season_label(year):
    return f"{year}-{str(year + 1)[-2:]}"


def agreement_for(year):
    """'1999' or '2005': the agreement for a pick of the `year` draft, by the league year his contract belongs to."""
    from .agreement import terms
    return terms(season_label(int(year)))["agreement"]


def tender_rules(year, root=ROOT):
    """The agreement's `required_tenders` section for the `year` draft."""
    agreement = agreement_for(year)
    data = _library(RULES[agreement], root) or {}
    rules = data.get("required_tenders")
    if not rules:
        raise KeyError(f"{RULES[agreement]} has no required_tenders section (the {year} draft's Required Tender rules)")
    return agreement, rules


def window(round_, year=2003, root=ROOT):
    """(first day or None, last day) of a Required Tender to a pick of `round_` in the `year` draft. The first-round
    window opens at the draft itself (None, as the first version printed it)."""
    year = int(year)
    _, rules = tender_rules(year, root)
    if round_ == 1:
        return None, f"{year}-{_value(rules['first_round']['tender_by'])}"
    second = rules["second_round"]
    return f"{year}-{_value(second['window_from'])}", f"{year}-{_value(second['tender_by'])}"


def _calendar_draft(calendar):
    """The draft's date from an offseason calendar: `draft` as a plain date or {"value": date}."""
    v = _value(calendar.get("draft")) if isinstance(calendar, dict) else None
    return v[:10] if isinstance(v, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}.*", v) else None


def draft_date(year, root=ROOT):
    """The date of the `year` draft from researched data, or None when the library does not record it."""
    year = int(year)
    lib = Path(f"library/{year}/league")
    found = _calendar_draft(_library(lib / f"nba_{year}_offseason_calendar.json", root) or {})
    if found:
        return found
    from .seasons import calendar, exists
    closing = season_label(year - 1)
    if exists(closing, "calendar", root) and calendar(closing, root).get(f"draft_{year}"):
        return calendar(closing, root)[f"draft_{year}"]
    v = _value((_library(lib / f"nba_{year}_draft_class.json", root) or {}).get("date"))
    return v if isinstance(v, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", v) else None


def _seasons_through(root, through):
    """Season folders with a current state, oldest first, through `through` (default: the live season)."""
    from .seasons import active, live_seasons
    if not (Path(root) / PLAYER).is_dir():
        return []
    last = through or active(root)
    return [s for s in live_seasons(root) if s <= last]


def _keys(row, name_key="name"):
    return [k for k in (row.get("bbr_id"), row.get(name_key), row.get("player")) if k]


def miami_picks(root, through):
    """{bbr_id or name: {"year", "round", "pick", "source"}}: Miami's picks in every simulated draft record of the
    seasons through `through`."""
    out = {}
    for season in _seasons_through(root, through) or [through]:
        folder = Path(root) / PLAYER / season / "09_Draft"
        for path in sorted(folder.glob("draft_*.json")) if folder.is_dir() else []:
            m = re.fullmatch(r"draft_(\d{4})\.json", path.name)
            if not m:
                continue
            for p in json.loads(path.read_text(encoding="utf-8")).get("picks", []):
                if p.get("club") == MIAMI:
                    row = {"year": int(m.group(1)), "round": p.get("round"), "pick": p.get("pick"),
                           "source": path.relative_to(root).as_posix()}
                    for k in _keys(p):
                        out[k] = row
    return out


def tender_book(root, through):
    """[tender]: every recorded Required Tender in the season folders through `through`, each with its draft year
    (`draft_year`, else the year of its date: a tender falls in its draft's summer) and its file."""
    out = []
    for season in _seasons_through(root, through) or [through]:
        rel = PLAYER / season / "00_Team/Transactions/required_tenders.json"
        for t in (read(rel, root) or {}).get("tenders", []):
            out.append(dict(t, draft_year=int(t.get("draft_year") or t["date"][:4]), file=rel.as_posix()))
    return out


def _tender_for(player, year, book):
    """The pick's latest recorded tender for the `year` draft, or None. With `year` None, his latest of any draft: read
    only to infer an unrecorded draft year (`pick_of`), never checked against a window."""
    names = set(_keys(player))
    mine = [t for t in book if t.get("player") in names or (t.get("bbr_id") and t["bbr_id"] in names)]
    if year is not None:
        mine = [t for t in mine if t["draft_year"] == int(year)]
    return mine[-1] if mine else None


def _round_from_status(status):
    return 1 if "first_round" in status else 2 if "second_round" in status else None


def pick_of(player, season, root, picks, sheet, tender):
    """(year, round, pick, basis) for an unsigned pick on `season`'s register."""
    found = next((picks[k] for k in _keys(player) if k in picks), None)
    row = next((sheet[k] for k in _keys(player) if k in sheet), {})
    year = player.get("draft_year") or (found or {}).get("year") or (tender or {}).get("draft_year") or int(season[:4])
    round_ = (player.get("draft_round") or (found or {}).get("round") or row.get("draft_round")
              or _round_from_status(player.get("status") or ""))
    number = player.get("draft_pick") or (found or {}).get("pick") or row.get("draft_pick") or (tender or {}).get("pick")
    basis = "register" if player.get("draft_year") else (found or {}).get("source") or ("tender" if tender else f"{season} register")
    return int(year), round_, number, basis


def retained_basis(player):
    """The register's own record (`draft_rights_retained`) that a pick's rights outlast the Required Tender and the next
    draft, or None. A status that marks him abroad is not such a record: it names no evidence and no end."""
    return player.get("draft_rights_retained")


def _status_error(name, status):
    """None for a held status or one naming the end of the rights; an error for any other draft-rights spelling."""
    if status in HELD or "draft_rights" not in status or any(w in status for w in ENDED_WORDS):
        return None
    return (f"{name}: register status {status!r} is not a known draft-rights status (held: {', '.join(HELD)}; "
            f"ended: one naming {', '.join(ENDED_WORDS)})")


def _retained_errors(player, keep, today, rules):
    name = player["name"]
    if not isinstance(keep, dict):
        return [f"{name}: draft_rights_retained must be a record (rule, until, source), not {keep!r}"]
    known = _value(rules.get("retained_beyond_next_draft")) or {}
    errors = []
    if keep.get("rule") not in RETAINED_RULES or keep.get("rule") not in known:
        errors.append(f"{name}: draft_rights_retained rule {keep.get('rule')!r} is not one the agreement provides ({', '.join(sorted(known))})")
    if not keep.get("source"):
        errors.append(f"{name}: draft_rights_retained has no source for the {keep.get('rule')} basis")
    if keep.get("until") and today >= keep["until"]:
        errors.append(f"{name}: rights retained under the {keep.get('rule')} rule ended on {keep['until']}; he cannot stay on the register unsigned")
    return errors


def season_errors(season, root=ROOT, today=None):
    """Errors in `season`'s register at its own date (or `today`)."""
    root = Path(root)
    state = read(PLAYER / season / "current_state.json", root) or {}
    today = today or state.get("current_date", "")
    roster = read(PLAYER / season / "00_Team/Team/Roster/roster.json", root)
    if not today or not roster:
        return []
    picks, book = miami_picks(root, season), tender_book(root, season)
    sheet_rows = (read(PLAYER / season / "00_Team/Finances/contract_schedules.json", root) or {}).get("players", [])
    sheet = {k: r for r in sheet_rows for k in _keys(r, "player")}
    errors = []
    for p in roster["players"]:
        status = p.get("status") or ""
        name = p["name"]
        if status not in HELD:
            wrong = _status_error(name, status)
            errors.extend([wrong] if wrong else [])
            continue
        year, round_, number, basis = pick_of(p, season, root, picks, sheet, _tender_for(p, None, book))
        tender = _tender_for(p, year, book)
        agreement, rules = tender_rules(year, root)
        keep = retained_basis(p)
        if keep is not None:
            errors.extend(_retained_errors(p, keep, today, rules))
            continue
        if "abroad" in status:
            errors.append(f"{name}: status {status} marks him abroad, but no draft_rights_retained record (rule, until, source) "
                          "dates his non-NBA contract; a status alone keeps no rights beyond the tender and the next draft")
        what = (f"{f'No. {number} ' if number else ''}{f'round-{round_}' if round_ else 'round not recorded'} "
                f"pick of the {year} draft")
        if tender is None:
            start, end = window(int(round_ or 1), year, root)     # an unknown round: the earlier, first-round deadline
            if today > end:
                errors.append(f"{name}: unsigned draft rights without a Required Tender ({CITE[agreement]}; required_tenders.json): "
                              f"{what} ({basis}); his window closed {end}, so he became a rookie free agent the next day")
        elif not (round_ or tender.get("round")):
            errors.append(f"{name}: Required Tender of {tender['date']} names no round, and no draft record gives one ({tender['file']})")
        else:
            if round_ and tender.get("round") and int(tender["round"]) != int(round_):
                errors.append(f"{name}: Required Tender recorded for round {tender['round']} but he was a {what} ({basis})")
            start, end = window(int(round_ or tender["round"]), year, root)
            opens = start or draft_date(year, root)                # a first-round tender cannot precede the draft
            if tender["date"] > end or (opens and tender["date"] < opens):
                errors.append(f"{name}: Required Tender dated {tender['date']} is outside its window ({start or 'draft'} to {end})")
        following = draft_date(year + 1, root)
        if following is None:
            errors.append(f"{name}: his rights end at the {year + 1} draft, whose date is not in the library "
                          f"(library/{year + 1}/league/nba_{year + 1}_offseason_calendar.json `draft` or the {season_label(year)} calendar `draft_{year + 1}`)")
        elif today >= following:
            errors.append(f"{name}: exclusive rights ended at the {following} draft; he cannot stay on the register unsigned")
    return errors


def draft_rights_errors(root=ROOT, through=None):
    """Every season's register through the live season (or `through`), each at its own date."""
    errors = []
    for season in _seasons_through(root, through):
        errors.extend(season_errors(season, root))
    return errors


# -- writers (scripts/offseason_day.py) ---------------------------------------------------------------------------------

def _long(day):
    from datetime import date
    d = date.fromisoformat(day)
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def _dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def _book(season, root):
    rel = PLAYER / season / "00_Team/Transactions/required_tenders.json"
    return rel, read(rel, root) or {
        "schema_version": 1, "owner": "ai_gm", "kind": "required_tenders", "season": season,
        "rule": "Required Tenders and the end of draft rights by draft year (1999 CBA Art. X §3 and Art. I (vv); 2005 FAQ "
                "Q43 and Q102): see runtime/draft_rights.py.", "tenders": []}


def _conduct(market, b, signed):
    """What the closed market record shows of Miami's holding of an unsigned pick (the tender's evidence)."""
    pool = next((r for r in market.get("unsigned_pool", []) if b and r.get("bbr_id") == b), None)
    left = next((r for r in market.get("left_the_league", []) if b and r.get("bbr_id") == b), None)
    if b in signed:
        return f"he signed on {signed[b]}, the market having held him under his drafting club's draft rights until then"
    if pool and pool.get("rights") == MIAMI:
        return "the market kept him in its unsigned pool under Miami's rights"
    if left:
        return (f"the market lists him out of the league ({left.get('basis', 'no role')}), and the rollover carries every "
                "Miami pick left unsigned as Miami's draft rights")
    return "the market holds every unsigned pick under his drafting club's draft rights"


def record_tenders(root=ROOT, year=None, day=None, write=True):
    """[tender]: Miami's routine Required Tenders for the `year` draft, entered once that summer's market record is closed.

    Each of Miami's picks of the year (`<season>/09_Draft/draft_<year>.json`) with no signing (any club) and no trade of
    his rights out of Miami dated on or before his round's deadline gets a tender dated on the deadline, with the
    agreement's terms, marked `reconstructed` with the day it is recorded and its basis. The rule is the AI/GM's routine
    filing (the 2003 tenders, recorded November 11, 2003) and the market's own conduct, which holds every unsigned pick
    under his drafting club's rights through the summer (`free_agency_2004`, `draft_rights` qualifying); nothing is
    drawn or chosen. A pick already tendered for this draft is skipped, so a rerun writes nothing. The tenders are filed
    in the summer's folder (the market record's season), where `tender_book` finds them for every later register."""
    from .free_agency_2004 import record_path
    root, year = Path(root), int(year)
    rel_market = record_path(year)
    market = read(rel_market, root)
    season = rel_market.parts[2]
    draft = read(PLAYER / season / f"09_Draft/draft_{year}.json", root)
    if not market or not draft:
        return []
    day = day or market.get("to")
    closed = market.get("to") or day
    signed, traded = {}, {}
    for e in market.get("events", []):
        b = e.get("bbr_id")
        if b and e.get("kind") in SIGN_KINDS:
            signed[b] = min(signed.get(b, e["date"]), e["date"])
        if b and e.get("kind") == "trade" and e.get("from") == MIAMI:
            traded[b] = min(traded.get(b, e["date"]), e["date"])
    from .seasons import live_seasons
    book = tender_book(root, max([season] + live_seasons(root)))      # every folder's tenders, the summer's and later
    agreement, rules = tender_rules(year, root)
    rel, data = _book(season, root)
    new = []
    for p in draft.get("picks", []):
        if p.get("club") != MIAMI or p.get("round") not in (1, 2):
            continue
        _, end = window(p["round"], year, root)
        b = p.get("bbr_id")
        if end > closed or end > day or (b and min(signed.get(b, "9999"), traded.get(b, "9999")) <= end):
            continue
        if _tender_for(p, year, book + new):
            continue
        terms = _value(rules["first_round" if p["round"] == 1 else "second_round"]["terms"])
        new.append({"player": p["player"], "bbr_id": b, "pick": p.get("pick"), "round": p["round"], "draft_year": year,
                    "date": end, "reconstructed": True, "recorded": day, "terms": terms,
                    "basis": (f"Miami's routine Required Tender to each pick it still holds unsigned on his deadline "
                              f"({CITE[agreement]}): no signing and no trade of his rights by {end} in the closed {year} summer "
                              f"market record ({rel_market.as_posix()}); {_conduct(market, b, signed)}; recorded {day} by "
                              f"runtime/draft_rights.record_tenders")})
    if new and write:
        data.setdefault("tenders", []).extend(new)
        _dump(root / rel, data)
    return new


def _cite(agreement, rule):
    """'1999 CBA Art. X §3(a); 1999 FAQ Q40' or '2005 FAQ Q43': a rule's source as the records cite it."""
    ref = rule.get("source_ref") or ""
    if ref.startswith(("1999", "2005")):
        return ref
    return f"1999 CBA {ref}" if agreement == "1999" else f"2005 FAQ {ref}"


def end_rights(root=ROOT, day=None, season=None, write=True):
    """[ended]: Miami's unsigned picks whose exclusive rights have ended by `day`, written on the live register.

    A held pick (`HELD`) without a retained basis loses his rights on the date of the draft after his own (1999 FAQ
    Q40; 2005 FAQ Q43); one with a sourced `draft_rights_retained` record keeps them until its `until`, and one whose
    record is malformed is left for validation to refuse. The register of the season that governs the day
    (`seasons.live_season_on`, the closed season's folder through the summer) gets status `ENDED` and a dated control
    line; his holding (`holdings.json`) closes on that date, so he plays for no club on Miami's rights after it; his
    contract-sheet row takes the same status; an unassigned-rights row of the depth chart moves to `departed`; and that
    season's `required_tenders.json` keeps the dated `rights_ended` entry. Nothing is decided: the date is the
    agreement's. A rerun finds no held pick left and writes nothing."""
    from .seasons import live_season_on
    root = Path(root)
    season = season or live_season_on(day, root)
    team = PLAYER / season / "00_Team"
    roster = read(team / "Team/Roster/roster.json", root)
    if not roster:
        return []
    picks, book = miami_picks(root, season), tender_book(root, season)
    sheet_doc = read(team / "Finances/contract_schedules.json", root) or {"players": []}
    sheet = {k: r for r in sheet_doc.get("players", []) for k in _keys(r, "player")}
    ended = []
    for p in roster["players"]:
        if p.get("status") not in HELD:
            continue
        year, round_, number, _ = pick_of(p, season, root, picks, sheet, _tender_for(p, None, book))
        agreement, rules = tender_rules(year, root)
        keep = retained_basis(p)
        if keep is not None:
            if not (isinstance(keep, dict) and keep.get("source") and keep.get("rule") in RETAINED_RULES
                    and keep.get("until") and day >= keep["until"]):
                continue
            on, why = keep["until"], f"Miami's draft rights retained under the {keep['rule']} rule ended"
            cite = f"{keep['source']}; {_cite(agreement, rules['retained_beyond_next_draft'])}"
        else:
            on = draft_date(year + 1, root)
            if on is None or day < on:
                continue
            why, cite = f"Miami's exclusive rights ended unsigned at the {year + 1} draft", _cite(agreement, rules["rights_until"])
        ended.append({"player": p["name"], "bbr_id": p.get("bbr_id"), "draft_year": year, "pick": number, "round": round_,
                      "date": on, "recorded": day, "status": ENDED,
                      "basis": f"{why} ({cite}); runtime/draft_rights.end_rights",
                      "control": f"{_long(on)}: {why} ({cite}). He is no longer under Miami's control."})
    if not ended or not write:
        return ended
    gone = {e["player"]: e for e in ended}
    for p in roster["players"]:
        if p["name"] in gone:
            p["status"], p["control"] = ENDED, gone[p["name"]]["control"]
    roster["as_of"] = max(roster.get("as_of") or day, day)
    _dump(root / team / "Team/Roster/roster.json", roster)
    by_id = {e["bbr_id"]: e for e in ended if e["bbr_id"]}
    holdings = read(team / "Team/Roster/holdings.json", root)
    if holdings:
        for h in holdings.get("entries", []):
            e = by_id.get(h.get("bbr_id")) or (gone.get(h.get("player")) if not h.get("bbr_id") else None)
            if e and h.get("until") is None and not h.get("void"):
                h["until"] = e["date"]
                h["basis"] = (h.get("basis", "") + f"; {e['basis']}").lstrip("; ")
        _dump(root / team / "Team/Roster/holdings.json", holdings)
    changed = False
    for r in sheet_doc.get("players", []):
        if r.get("player") in gone and r.get("status") in HELD:
            r["status"], changed = ENDED, True
    if changed:
        _dump(root / team / "Finances/contract_schedules.json", sheet_doc)
    depth = read(team / "Team/Depth_Chart/depth_chart.json", root)
    if depth and any((u.get("name") if isinstance(u, dict) else u) in gone for u in depth.get("unassigned_draft_rights", [])):
        depth["unassigned_draft_rights"] = [u for u in depth["unassigned_draft_rights"] if (u.get("name") if isinstance(u, dict) else u) not in gone]
        depth.setdefault("departed", []).extend({"name": e["player"], "date": e["date"], "status": ENDED} for e in ended)
        _dump(root / team / "Team/Depth_Chart/depth_chart.json", depth)
    rel, data = _book(season, root)
    data.setdefault("rights_ended", []).extend({k: v for k, v in e.items() if k != "control"} for e in ended)
    _dump(root / rel, data)
    return ended


# The 2003 draft's deadlines and the next draft, from the data (the first version's constants).
FIRST_ROUND_BY = window(1, 2003)[1]
SECOND_ROUND_WINDOW = window(2, 2003)
NEXT_DRAFT = draft_date(2004)
