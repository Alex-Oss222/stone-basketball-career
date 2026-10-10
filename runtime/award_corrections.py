"""Dated corrections of recorded award results: the award audit's findings the user approved correcting (October 2026).

The audit found four recorded results decided with a faulty rookie pool or placeholder registry positions. The code is
fixed (`award_decisions.rookies` and `first_season_ids`, the registry position repair with its dated corrections and
`write_back.position_on`, the Rookie Challenge bbr_id rule gated by `all_star.BBR_ROOKIES_FROM`); `CORRECTED` names,
item by item, the results the user approved re-deciding with it, and nothing else may be corrected:
1. the 2003-04 All-Rookie teams (`season_awards.json`), re-decided by `season_awards.decide_one`: two Second Team places
   change. The Rookie of the Year vote, decided on the same pool, is not part of the approval and stands as recorded
   (`decide_one` decides the two awards independently);
2. the 2003-04 All-Star Rookie Challenge Rookies (`all_star.json`, step rookie_challenge), by
   `all_star.rookie_challenge`;
3. the 2004-05 Rookie Challenge Rookies likewise, with the registry positions as corrected;
4. the 2003-04 West Rookie of the Month shortlists the fixed pool re-ranks (`award_decisions.json`), by
   `award_decisions.rank`: the No. 3 place of the October-November, December and January decisions, and in April the
   No. 2 and No. 3 places (Raül López enters at No. 2 above Leandro Barbosa, so the No. 3 place cannot move alone).
None of these games was played (the All-Star records hold selections and game rosters only), so a roster can change
without contradicting a result. No winner changes and Wade is in none of the changed places: his awards.json stands.
Each approved item also pins the fingerprint of its audited original and corrected values (`fingerprint`), so a
correction can neither supersede values other than the recorded ones nor write values other than the audited ones.

A re-decision reads the world as it stood on the correction date (`replaying`): the live season pinned to the corrected
season (`season_awards.C` and the rookie pool read `seasons.active`), every registry position as it stood on that date
(`write_back.position_on`: after the 2005-12-31 repair, the sourced positions), and the Rookies pool as fixed
(`all_star.BBR_ROOKIES_FROM` lifted for the season: every first-season bbr_id and record name). It writes nothing.

A corrected item keeps its key and its place in its record. Each field the re-decision gives differently takes the new
value in place, and the item gains `correction`: {corrected_on (the career clock when applied, never earlier than
`APPROVED_FROM`), reason (the audit finding and the user's approval), superseded (the exact original value of every
replaced field)}. `apply` is idempotent: an item already corrected is left alone, and one that would now re-decide
differently is refused rather than corrected twice.

`as_of(item, on)` is the one dated reader: on a date before `corrected_on` it returns the item as recorded then (the
superseded values, no correction block), so a reader replaying a decision dated before the correction (a valuation's
honors in a 2004 summer market, a dated card or page) reads what that decision read; on or after it, the corrected
item. Pages and cards show the corrected result with `note` (the correction date and the superseded names).

Validation (`correction_errors`): every correction block on file belongs to an approved item, is dated from
`APPROVED_FROM` to the clock, carries the item's reason, supersedes exactly the approved original values with exactly
the approved corrected ones, changes no winner and nothing of Wade's, and its corrected values equal what the current
code re-decides (read-only), so every correction is reproducible.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PLAYER = Path("career/Dwyane_Wade")
LEAGUE = PLAYER / "Stats_and_Awards/League"
WADE = "Dwyane Wade"
RECORDS = {"season_awards": "season_awards.json", "all_star": "all_star.json", "award_decisions": "award_decisions.json"}
ITEMS = {"season_awards": "decisions", "all_star": "steps", "award_decisions": "decisions"}
APPROVED_FROM = "2006-01-01"      # the career clock of the audited records: no correction is dated earlier, so every
                                  # decision replayed before it (a 2004 or 2005 market, a dated card) reads the original
CORRECTED = {   # item id: (record, season, award or step, fingerprint of the original values superseded, of the corrected)
    "2003-04-all_rookie": ("season_awards", "2003-04", "all_rookie", "92aa398d71258875", "d711e493016429b0"),
    "2003-04-all-star-rookie_challenge": ("all_star", "2003-04", "rookie_challenge",
                                          "b75d5167e2ba9d6d", "546089f196e1743f"),
    "2004-05-all-star-rookie_challenge": ("all_star", "2004-05", "rookie_challenge",
                                          "75727bdb9b76b652", "bab9a3f4d087893c"),
    "2003-04-rookie_of_month-2003-10-28-west": ("award_decisions", "2003-04", "rookie_of_month",
                                                "29ad1b38070e52ed", "7f99f4e637eb7d99"),
    "2003-04-rookie_of_month-2003-12-01-west": ("award_decisions", "2003-04", "rookie_of_month",
                                                "f79cc613b747deae", "d45f6fd8589983be"),
    "2003-04-rookie_of_month-2004-01-01-west": ("award_decisions", "2003-04", "rookie_of_month",
                                                "2632533162a3b657", "7b567b91b804f0cf"),
    "2003-04-rookie_of_month-2004-04-01-west": ("award_decisions", "2003-04", "rookie_of_month",
                                                "36364c923df6989f", "7a5083f2665b0ec5"),
}
APPROVAL = "The user approved correcting the recorded result (October 2026)."
REASONS = {     # (record, season, award or step): the reason each corrected item carries
    ("season_awards", "2003-04", "all_rookie"): (
        "Award audit (October 2026): the 2003-04 rookie pool was read from the registry's 2003 draft-rights cohort and "
        "the unattached identities only, so the first-season players only the 2004 service file names (24, among them "
        "Marquis Daniels, undrafted, and Raül López, drafted in 2001) were not eligible. Re-decided by "
        "season_awards.decide_one with the fixed pool (award_decisions.rookies and first_season_ids): two Second Team "
        "places change (Marquis Daniels and Raül López for T.J. Ford and Keith Bogans) and the points of the players "
        "outside the teams are re-counted; the First Team players are unchanged. " + APPROVAL),
    ("all_star", "2003-04", "rookie_challenge"): (
        "Award audit (October 2026): the 2003-04 Rookie Challenge pool compared the panel's record names with real-roster "
        "spellings, so six first-season players whose spelling differs (Darko Milicic, Michael Sweetney, Mickael Pietrus, "
        "Sasha Pavlovic, Zarko Cabarkapa, Zoran Planinic) were not eligible; with them the panel's ballots move. "
        "Re-decided by all_star.rookie_challenge with the fixed pool (every first-season bbr_id and record name): "
        "Jarvis Hayes for T.J. Ford on the Rookies; the Sophomores are unchanged. " + APPROVAL),
    ("all_star", "2004-05", "rookie_challenge"): (
        "Award audit (October 2026): the 2004-05 Rookie Challenge read the placeholder SF of the season's registry "
        "additions (Ben Gordon SG, Josh Childress SG, Andre Iguodala SG, David Harrison C, Emeka Okafor PF, Nenad "
        "Krstić PF), so the panel's guard, forward and center slots were filled on placeholders. Re-decided by "
        "all_star.rookie_challenge with the registry positions as corrected (write_back.position_on, repair dated "
        "2005-12-31) and the fixed pool: Andrés Nocioni, David Harrison and Josh Smith for Maurice Baker, Carlos "
        "Delfino and Mario Kasun on the Rookies, with the sourced positions; the Sophomores are unchanged. " + APPROVAL),
    ("award_decisions", "2003-04", "rookie_of_month"): (
        "Award audit (October 2026): the 2003-04 Rookie of the Month pool was read from the registry's 2003 draft-rights "
        "cohort and the unattached identities only, so the first-season players only the 2004 service file names "
        "(Marquis Daniels and Raül López among them) were not ranked. Re-ranked by award_decisions.rank with the fixed "
        "pool; every winner is unchanged. The West No. 3 place of the October-November, December and January decisions "
        "moves (Marquis Daniels); in April Raül López enters at No. 2, Leandro Barbosa moves from No. 2 to No. 3 and "
        "Chris Kaman leaves the shortlist. " + APPROVAL),
}


class CorrectionRefused(ValueError):
    """A correction that may not be made: an item or a date outside the user's approval (`CORRECTED`,
    `APPROVED_FROM`), recorded or re-decided values other than the approved ones, a changed winner or anything of
    Wade's, or an item already corrected that would now re-decide differently. Reported, never written."""


def _read(path):
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def _write(path, data):
    Path(path).write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def record_path(kind, season):
    return LEAGUE / season / RECORDS[kind]


def _long(day):
    d = date.fromisoformat(day)
    return f"{d.strftime('%B')} {d.day}, {d.year}"


# -- the dated reader -------------------------------------------------------------------------------------------------
def as_of(item, on):
    """The item as the career knew it on `on`: before its correction date, the values recorded then (the superseded
    fields restored in place, no correction block); on or after it, or with no date, the item as it stands."""
    c = (item or {}).get("correction")
    if not c or on is None or on >= c["corrected_on"]:
        return item
    out = {k: v for k, v in item.items() if k != "correction"}
    out.update(c["superseded"])
    return out


def superseded(item):
    """The item as recorded before its correction (the item itself when it carries none)."""
    c = (item or {}).get("correction")
    return as_of(item, _day_before(c["corrected_on"])) if c else item


def _day_before(day):
    return date.fromordinal(date.fromisoformat(day).toordinal() - 1).isoformat()


# -- what a correction changed ----------------------------------------------------------------------------------------
def _join(names):
    names = list(names)
    return " and ".join(names) if len(names) < 3 else ", ".join(names[:-1]) + " and " + names[-1]


def _players(rows):
    return [p["player"] for p in rows]


def team_changes(item):
    """[(team or side, added, removed)] between a corrected item's superseded and current team rosters."""
    old = ((item or {}).get("correction") or {}).get("superseded", {})
    if "teams" not in old:
        return []
    before, after = old["teams"], item["teams"]
    if isinstance(after, dict):                                  # an All-Star step: {side: [players]}
        pairs = [(side, _players(before.get(side, [])), _players(rows)) for side, rows in after.items()]
    else:                                                        # a season award: [{"team", "players"}]
        was = {t["team"]: _players(t["players"]) for t in before}
        pairs = [(t["team"], was.get(t["team"], []), _players(t["players"])) for t in after]
    out = []
    for label, b, a in pairs:
        added, removed = [n for n in a if n not in b], [n for n in b if n not in a]
        if added or removed:
            out.append((label, added, removed))
    return out


def summary(item):
    """Short statements of what the item's correction changed: team places and re-ranked shortlists."""
    c = (item or {}).get("correction")
    if not c:
        return []
    old, out = c["superseded"], []
    for label, added, removed in team_changes(item):
        verb = "replaces" if len(added) == 1 else "replace"
        out.append(f"{label}: {_join(added) or 'no one'} {verb} {_join(removed) or 'no one'}")
    if "shortlist" in old:
        out.append(f"shortlist {', '.join(_players(item['shortlist']))} (was {', '.join(_players(old['shortlist']))})")
    if out and not ({"winners", "winner"} & set(old)) and ("winners" in item or "winner" in item):
        out[-1] += "; the winner is unchanged"
    return out


def note(item, fmt=_long):
    """A page's line for a corrected item: the correction date and what it superseded; None for an uncorrected one."""
    c = (item or {}).get("correction")
    if not c:
        return None
    return (f"Corrected on {fmt(c['corrected_on'])} (award audit, approved by the user): {'; '.join(summary(item))}. "
            "The superseded values are kept in the record (`correction`).")


# -- re-deciding with the current code --------------------------------------------------------------------------------
@contextmanager
def replaying(season, on=None):
    """The world a re-decision reads, restored afterwards: the live season pinned to `season` (`seasons.active`, read
    by `season_awards.C` and the rookie pool), every registry position as it stood on `on` (`write_back.position_on`
    with its basis: a reader that selects by position reads `known_position`), and the Rookie Challenge's Rookies pool
    as fixed for the season (`all_star.BBR_ROOKIES_FROM`). Nothing is written."""
    from . import all_star, seasons, write_back
    saved = seasons.active, write_back.known_position, all_star.BBR_ROOKIES_FROM
    known = write_back.known_position

    def dated(entry):
        if on and entry.get("position_corrected_on") and on < entry["position_corrected_on"]:
            return None if entry.get("position_basis_before") == write_back.UNKNOWN_BASIS else entry.get("position_before")
        return known(entry)

    seasons.active = lambda root=None: season
    write_back.known_position = dated
    all_star.BBR_ROOKIES_FROM = min(saved[2], season)
    try:
        yield
    finally:
        seasons.active, write_back.known_position, all_star.BBR_ROOKIES_FROM = saved


def _key(kind, item):
    return item["award"] if kind != "all_star" else item["step"]


def _item_id(kind, season, item):
    return item.get("id") or f"{season}-all-star-{item['step']}"


class _Evidence:
    """Closed results read once per season for every re-decision of a run (read-only)."""

    def __init__(self, world):
        self.world, self.rows = Path(world), {}

    def season_rows(self, season):
        if season not in self.rows:
            from .seasons import dates
            from .write_back import closed_results
            self.rows[season] = closed_results(self.world, season, dates(season, self.world)["regular_season_end"])
        return self.rows[season]


def redecide(kind, season, item, world=ROOT, on=None, evidence=None):
    """{field: value} the current code decides for a recorded item (its superseded values ignored), read-only:
    - a season award: `season_awards.decide_one` (the Finals MVP is not re-decided here);
    - an All-Star Rookie Challenge step: `all_star.rookie_challenge` on the step's own date;
    - a weekly or monthly award: `award_decisions.rank` over the period, the recorded engine draw deciding a tie at the
      top as `award_decisions.decide` does (a tie with no recorded draw cannot be re-decided).
    `on` dates the registry positions read (the correction date)."""
    world = Path(world)
    evidence = evidence or _Evidence(world)
    with replaying(season, on):
        rows = evidence.season_rows(season)
        if kind == "season_awards":
            from . import season_awards
            if item["award"] == "finals_mvp":
                raise CorrectionRefused(f"{season} {item['name']}: the Finals MVP is not re-decided by this module")
            award = next(a for a in season_awards.calendar(world)["awards"] if a["id"] == item["award"])
            out = season_awards.decide_one(dict(award, announced=item["announced_on"]), rows, world)
        elif kind == "all_star":
            from . import all_star
            if item["step"] != "rookie_challenge":
                raise CorrectionRefused(f"{season} All-Star {item['step']}: only the Rookie Challenge is re-decided here")
            out = all_star.rookie_challenge(world, all_star.ctx(world, season), item["announced_on"], rows)
        elif kind == "award_decisions":
            out = _rerank(world, season, item, rows)
        else:
            raise ValueError(f"unknown award record {kind}")
    return out


def _rerank(world, season, d, rows):
    from . import award_decisions as A
    conf, first, names = A.conferences(world, season), A.rookies(world, season), A.registry_names(world, season)
    listed = A.rank(d["award"], d["period_start"], d["period_end"], rows, conf, first, names).get(d["conference"], [])
    winner = listed[0]["player"] if listed else None
    tied = [x["player"] for x in listed if round(x["score"], 2) == round(listed[0]["score"], 2)] if listed else []
    if len(tied) > 1:
        draw = d.get("tie_draw")
        result = world / draw if draw else None
        if not result or not result.is_file():
            raise CorrectionRefused(f"{d['id']}: equal scores at the top and no recorded engine draw to decide them")
        winner = _read(result)["outcome"]
        listed = sorted(listed, key=lambda x: x["player"] != winner)
    return {"shortlist": [dict(x, rank=i + 1) for i, x in enumerate(listed)], "winner": winner}


def _wade_honors(kind, item):
    """What an item gives Wade: his season honors (awards.json), his Rookie Challenge side, a weekly or monthly win."""
    if kind == "season_awards":
        from .season_awards import honors
        return sorted(h for h in honors(item) if h[0] == WADE)
    if kind == "all_star":
        return sorted(side for side, rows in (item.get("teams") or {}).items() if WADE in _players(rows))
    return [WADE] if item.get("winner") == WADE else []


def _guard(kind, season, item, fresh):
    """Refuse a re-decision that changes a winner (no approved correction changes one) or anything of Wade's."""
    label = _item_id(kind, season, item)
    for k in ("winner", "winners"):
        if k in fresh and fresh[k] != item.get(k):
            raise CorrectionRefused(f"{label}: the re-decided {k} would be {fresh[k]}, not the recorded {item.get(k)}; "
                                    "a changed winner is not corrected here")
    if _wade_honors(kind, item) != _wade_honors(kind, dict(item, **fresh)):
        raise CorrectionRefused(f"{label}: the re-decision changes an honor or a place of Wade's")


def fingerprint(fields):
    """A short digest of {field: value}, pinned in `CORRECTED` for an item's audited original and corrected values."""
    text = json.dumps(fields, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _flat(value, path=""):
    if isinstance(value, dict):
        for k, v in value.items():
            yield from _flat(v, f"{path}.{k}" if path else k)
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from _flat(v, f"{path}[{i}]")
    else:
        yield path, value


def field_changes(before, after):
    """[{field, before, after}] for every leaf that differs between two values of the same fields."""
    a, b = dict(_flat(before)), dict(_flat(after))
    return [{"field": k, "before": a.get(k), "after": b.get(k)} for k in dict.fromkeys(list(a) + list(b)) if a.get(k) != b.get(k)]


def _find(record, kind, season, item_id):
    items = (record or {}).get(ITEMS[kind], [])
    return next((i for i in items if _item_id(kind, season, i) == item_id), None)


def _approved(item_id, old, new):
    """Why `old` superseded by `new` is not the change the user approved for the item (None when it is)."""
    *_, before, after = CORRECTED[item_id]
    if fingerprint(old) != before:
        return (f"{item_id}: the recorded values it would supersede ({', '.join(old)}) are not the ones the user "
                "approved correcting")
    if fingerprint(new) != after:
        return f"{item_id}: the corrected values ({', '.join(new)}) are not the ones the user approved"
    return None


def plan(root=ROOT, day=None, world=None, targets=None):
    """The corrections `apply` would write, read-only: [(kind, season, item index, corrected item, report entry)].
    `targets` (item ids, all of `CORRECTED` by default) must be approved items."""
    from .write_back import clock
    root, world = Path(root), Path(world or root)
    day = day or clock(root)
    if day < APPROVED_FROM:
        raise CorrectionRefused(f"a correction dated {day} is before {APPROVED_FROM}, the earliest the approval allows")
    targets = list(dict.fromkeys(CORRECTED if targets is None else targets))
    unknown = [t for t in targets if t not in CORRECTED]
    if unknown:
        raise CorrectionRefused(f"{', '.join(map(str, unknown))}: not a correction the user approved (CORRECTED)")
    evidence, out, records = _Evidence(world), [], {}
    for item_id in targets:
        kind, season, key, *_ = CORRECTED[item_id]
        record = records.setdefault((kind, season), _read(root / record_path(kind, season)))
        item = _find(record, kind, season, item_id)
        if item is None or _key(kind, item) != key:
            raise CorrectionRefused(f"{record_path(kind, season).as_posix()}: no item {item_id} to correct")
        fresh = redecide(kind, season, superseded(item), world, day, evidence)
        current = {k: v for k, v in item.items() if k != "correction"}
        changed = [k for k in fresh if fresh[k] != current.get(k)]
        if item.get("correction"):
            if changed:
                raise CorrectionRefused(f"{item_id} was corrected on {item['correction']['corrected_on']} and now "
                                        f"re-decides differently ({', '.join(changed)}): a second correction needs its "
                                        "own decision")
            continue
        if not changed:
            raise CorrectionRefused(f"{item_id}: the current code re-decides the recorded values, not the change the "
                                    "user approved")
        _guard(kind, season, item, fresh)
        old, new_values = {k: item[k] for k in changed}, {k: fresh[k] for k in changed}
        wrong = _approved(item_id, old, new_values)
        if wrong:
            raise CorrectionRefused(wrong)
        new = dict(item)
        new.update(new_values)                                 # in place: each key keeps its place in the item
        new["correction"] = {"corrected_on": day, "reason": REASONS[(kind, season, key)], "superseded": old}
        index = record[ITEMS[kind]].index(item)
        out.append((kind, season, index, new, {
            "record": record_path(kind, season).as_posix(), "season": season, "item": item_id,
            "name": item.get("name") or "All-Star Rookie Challenge rosters", "corrected_on": day,
            "fields": field_changes(old, new_values), "note": note(new)}))
    return out, records


def apply(root=ROOT, day=None, write=True, world=None, targets=None):
    """Re-decide the approved items (`CORRECTED`, or the approved ids in `targets`) with the current code and write
    each into its record as a correction dated by the career clock, then rebuild the pages that show them
    (`write_pages`). `day` may only restate the clock (a scratch copy of the records alone has none, and takes `day`).
    `world` is the repository the re-decisions read (the records' own by default; a test reads the repository's
    evidence for a scratch copy of the records). Idempotent: a second run changes nothing. Refuses
    (`CorrectionRefused`, before anything is written) anything outside the approval (see the class). Returns
    {"items": [{record, season, item, name, corrected_on, fields: [{field, before, after}], note}], "pages": [paths
    rewritten]}."""
    from .write_back import clock
    root, world = Path(root), Path(world or root)
    try:
        now = clock(root)
    except ValueError:                                         # a scratch copy of the records alone: no clock to check
        now = None
    day = day or now
    if now and day != now:
        raise CorrectionRefused(f"a correction dated {day} is not dated by the career clock {now}")
    targets = list(dict.fromkeys(CORRECTED if targets is None else targets))
    changes, records = plan(root, day, world, targets)
    pages = []
    if write:
        touched = set()
        for kind, season, index, new, _ in changes:
            records[(kind, season)][ITEMS[kind]][index] = new
            touched.add((kind, season))
        for kind, season in sorted(touched):
            _write(root / record_path(kind, season), records[(kind, season)])
        pages = write_pages(root, day, world, sorted({tuple(CORRECTED[t][:2]) for t in targets}))
    return {"items": [entry for *_, entry in changes], "pages": pages}


# -- pages ------------------------------------------------------------------------------------------------------------
def _page_date(text, pattern, parse=lambda s: s):
    m = re.search(pattern, text or "")
    return parse(m.group(1)) if m else None


def _from_long(text):
    return datetime.strptime(text, "%B %d, %Y").date().isoformat()


def write_pages(root=ROOT, day=None, world=None, records=None):
    """Rebuild every page that shows a corrected record and that no daily pipeline rebuilds for a closed season, from
    the records as they stand: the season's `Season_Awards.md` (`season_awards.page`) and `All_Star.md`
    (`all_star.page`), each keeping the date it states (its evidence date, not the correction's), the month pages of
    the corrected weekly and monthly decisions (`award_decisions.render_pages`, the month's 'As of' line kept), and
    the season's award hub (`award_pages.outputs`). Only existing pages are rewritten, and only when they differ.
    Returns the paths rewritten."""
    from .write_back import clock
    root, world = Path(root), Path(world or root)
    day = day or clock(root)
    written = []

    def put(path, text):
        if path.is_file() and path.read_text(encoding="utf-8") != text:
            path.write_text(text, encoding="utf-8")
            written.append(path.relative_to(root).as_posix())

    records = records or sorted({tuple(v[:2]) for v in CORRECTED.values()})
    for kind, season in records:
        record = _read(root / record_path(kind, season))
        if record is None:
            continue
        league = root / LEAGUE / season
        if kind == "season_awards":
            from . import season_awards
            page = league / "Season_Awards.md"
            through = (_page_date(page.read_text(encoding="utf-8") if page.is_file() else "", r"Through (\d{4}-\d{2}-\d{2})\.")
                       or max(d["announced_on"] for d in record["decisions"]))
            with replaying(season):
                put(page, season_awards.page(record, through, world))
        elif kind == "all_star":
            from . import all_star
            page = league / "All_Star.md"
            stated = _page_date(page.read_text(encoding="utf-8") if page.is_file() else "",
                                r"Career clock: ([A-Z][a-z]+ \d{1,2}, \d{4})\.", _from_long)
            put(page, all_star.page(record, stated or max(all_star.decision_dates(record).values()), all_star.ctx(world, season)))
        else:
            from .award_decisions import render_pages
            corrected = {d["filed_on"] for d in record["decisions"] if d.get("correction")}
            if not corrected:
                continue
            before = {rel: (root / rel).read_text(encoding="utf-8") for rel in corrected if (root / rel).is_file()}
            render_pages(root, {"season": season, "decisions": [d for d in record["decisions"] if d["filed_on"] in corrected]}, day)
            for rel, old in before.items():                   # the month's 'As of' line is the hub's (award_pages)
                path = root / rel
                text = _keep_status(path.read_text(encoding="utf-8"), old)
                if text != path.read_text(encoding="utf-8"):
                    path.write_text(text, encoding="utf-8")
                if text != old:
                    written.append(rel)
    seasons = {s for _, s in records}
    try:
        from .award_pages import outputs
        hubs = outputs(root, day)
    except (OSError, KeyError, ValueError):                    # a scratch copy without the hub's records
        hubs = {}
    for path, text in hubs.items():
        if any(Path(path).is_relative_to(root / LEAGUE / s) for s in seasons):
            put(Path(path), text)
    return sorted(set(written))


def _keep_status(text, old):
    """The page text with the 'As of' line it had before the rebuild (restated by `award_pages`, not by the decision)."""
    line = _page_date(old, r"(?m)^(As of [^\n]*)$")
    return re.sub(r"(?m)^As of [^\n]*$", lambda _: line, text, count=1) if line else text


# -- validation -------------------------------------------------------------------------------------------------------
def corrected_items(root=ROOT):
    """[(kind, season, item)] for every item on file that carries a correction block."""
    root, out = Path(root), []
    for kind, name in RECORDS.items():
        for path in sorted((root / LEAGUE).glob(f"*/{name}")):
            record = _read(path) or {}
            out += [(kind, path.parent.name, i) for i in record.get(ITEMS[kind], []) if i.get("correction")]
    return out


def correction_errors(root=ROOT, clock=None, world=None):
    """Every correction block on file: on an approved item (`CORRECTED`), dated from `APPROVED_FROM` to the clock, with
    the item's reason, superseded values that differ from the corrected ones and are exactly the approved originals,
    corrected values exactly the approved ones, no winner and nothing of Wade's changed, and corrected values equal to
    what the current code re-decides (`redecide`, read-only, the world as it stood on the correction date), so the
    correction is reproducible."""
    from .write_back import clock as career_clock
    root, world = Path(root), Path(world or root)
    items = corrected_items(root)
    if not items:
        return []
    clock = clock or career_clock(root)
    evidence, errors = _Evidence(world), []
    for kind, season, item in items:
        item_id = _item_id(kind, season, item)
        label = f"{record_path(kind, season).as_posix()}: {item_id}"
        key = (kind, season, _key(kind, item))
        if tuple(CORRECTED.get(item_id, ())[:3]) != key:
            errors.append(f"{label}: carries a correction the user did not approve (award_corrections.CORRECTED)")
            continue
        c = item["correction"]
        day = c.get("corrected_on") if isinstance(c, dict) else None
        try:
            date.fromisoformat(day or "")
        except (TypeError, ValueError):
            errors.append(f"{label}: correction has no valid date ({day!r})")
            continue
        if day > clock:
            errors.append(f"{label}: correction dated {day}, after the career clock {clock}")
        if day < APPROVED_FROM:
            errors.append(f"{label}: correction dated {day}, before {APPROVED_FROM}, the earliest the approval allows")
        if c.get("reason") != REASONS[key]:
            errors.append(f"{label}: correction gives no reason or not the approved one (award_corrections.REASONS)")
        old = c.get("superseded")
        if not isinstance(old, dict) or not old:
            errors.append(f"{label}: correction keeps no superseded values")
            continue
        unknown = [k for k in old if k not in item or k == "correction"]
        same = [k for k in old if k in item and item[k] == old[k]]
        if unknown or same:
            errors.append(f"{label}: superseded fields {unknown + same} are not fields the correction replaced")
            continue
        current = {k: v for k, v in item.items() if k != "correction"}
        wrong = _approved(item_id, old, {k: item[k] for k in old})
        if wrong:
            errors.append(f"{record_path(kind, season).as_posix()}: {wrong}")
        try:
            _guard(kind, season, superseded(item), current)
        except CorrectionRefused as exc:
            errors.append(f"{record_path(kind, season).as_posix()}: {exc}")
        try:
            fresh = redecide(kind, season, superseded(item), world, day, evidence)
        except (CorrectionRefused, StopIteration, KeyError, ValueError, OSError) as exc:
            errors.append(f"{label}: cannot re-decide the corrected values ({exc})")
            continue
        differ = [k for k in fresh if fresh[k] != item.get(k)]
        if differ:
            errors.append(f"{label}: corrected {', '.join(differ)} differ from what the current code re-decides "
                          "(python -c 'from runtime.award_corrections import apply; print(apply(write=False))')")
        missing = [k for k in old if k not in fresh]
        if missing:
            errors.append(f"{label}: superseded fields {missing} are not fields the re-decision gives")
    return errors
