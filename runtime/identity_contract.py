"""The contract line on Wade's dated identity: the season's terms come from that season's contract record.

The user's report (April 2006 on the career clock): every 2005-06 stat page still named his 2004-05 salary. The 2004-10-01
snapshot wrote the season's salary into its `contract` text by hand, and each later snapshot (camp roles, numbers)
copied the text forward, so nothing changed it when the season did. From FROM on the season's part is derived, so it can
never go stale:

- a status snapshot's `contract` names the agreement (written by the signing, extension or other contract event); a
  season note left in it by an earlier snapshot ("(2004-05: $2,361,800)") is not the agreement and is dropped;
- the page's season adds its terms from Miami's cap sheet of that season (`contract_schedules.json`, Wade's row): the
  season's salary and every later option season, decided only once the season's option record
  (`League/option_decisions.json`, `runtime/options.py`) applied the decision on or before the page's cutoff, open
  with its deadline before then;
- an option an extension added is shown only from the extension's signing date: the extension writes its seasons into
  the same row of the sheet, and a page dated before it must not know them;
- a page inside a season's folders reads that season; a career page reads the season the rollover had opened by its
  cutoff (`rolled_over_on`), and the stored line before any.

Seasons before FROM keep the line their snapshots recorded (a 2004-05 page keeps its 2004-05 salary, even the season
pages dated on the 2005-06 rollover day), except that a season page never names another season's salary: the 2003-04
season pages, dated on the 2004-05 rollover day, drop the 2004-05 note and read the agreement, as the 2003-04 game notes
do. Read-only: it writes no record.
"""
import json
import re
from pathlib import Path

from .extensions import extensions_of
from .options import deadline, record_path as option_record, sheet_options

FROM = "2005-06"
PLAYER = "career/Dwyane_Wade"
SHEET = "00_Team/Finances/contract_schedules.json"
SEASON_NOTE = re.compile(r"\s*\(\d{4}-\d{2}: \$[\d,]+\)")
OUTCOMES = {("team_option", "exercise"): "exercised", ("team_option", "decline"): "declined",
            ("player_option", "stay"): "exercised", ("player_option", "leave"): "declined",
            ("early_termination_option", "stay"): "not exercised", ("early_termination_option", "leave"): "exercised"}


def _read(path):
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def season_terms(root, player, season, name):
    """{"from", "salary", "options"} for the player's row on Miami's cap sheet of `season`, or None without a salary
    for the season there. A traded contract keeps its row and schedule, and the option record is league-wide. Each
    option carries the date its agreement was signed: an extension's own date for its seasons, the row's otherwise."""
    folder = Path(player) / season
    sheet = _read(folder / SHEET) or {"players": []}
    row = next((p for p in sheet["players"] if p["player"] == name), None)
    if not row or not (row.get("schedule") or {}).get(season):
        return None
    signed = {s: e["signed_date"] for e in extensions_of(row) for s in e["schedule"]}
    options = {s: {"kind": kind, "salary": salary, "due": deadline(kind, s, rookie), "outcome": None, "on": None,
                   "signed": signed.get(s, row.get("signed_date"))}
               for s, kind, salary, rookie in sheet_options(row, season)}
    for d in (_read(Path(root) / option_record(season)) or {"decisions": []})["decisions"]:
        if d["player"] == name and d["option_season"] > season and d.get("applied"):
            options[d["option_season"]] = {"kind": d["kind"], "salary": d["salary"], "due": d["deadline"],
                                           "outcome": d["decision"], "on": d["applied"],
                                           "signed": signed.get(d["option_season"], row.get("signed_date"))}
    state = _read(folder / "current_state.json") or {}
    return {"from": state.get("rolled_over_on"), "salary": int(row["schedule"][season]),
            "options": dict(sorted(options.items()))}


def attach(identity, root, player):
    """A copy of the identity carrying each live season's contract terms from FROM on (`contract_terms`), which
    `career_stats.identity_at` reads."""
    name = identity.get("display_name") or identity["full_name"]
    seasons = sorted(p.name for p in Path(player).iterdir() if p.is_dir() and re.fullmatch(r"\d{4}-\d{2}", p.name)
                     and (p / "current_state.json").is_file() and p.name >= FROM)
    terms = {s: season_terms(root, player, s, name) for s in seasons}
    return {**identity, "contract_terms": {s: t for s, t in terms.items() if t}}


def line(terms, stored, as_of, season=None):
    """The contract line on `as_of` for a page of `season` (None: a career page)."""
    page = season
    if season is None:
        season = max((s for s, t in terms.items() if t["from"] and t["from"] <= as_of), default=None)
    t = terms.get(season)
    if not stored:
        return stored
    if t is None:
        # a season page keeps its snapshot's line but never another season's salary note
        note = SEASON_NOTE.search(stored)
        return SEASON_NOTE.sub("", stored) if page and note and not note.group().strip().startswith(f"({page}:") else stored
    parts = [f"{season}: ${t['salary']:,}"]
    for s, o in t["options"].items():
        if o.get("signed") and o["signed"] > as_of:
            continue                         # an extension signed after the page's cutoff
        label = o["kind"].replace("_", " ")
        if o["on"] and o["on"] <= as_of:
            kept = o["outcome"] in ("exercise", "stay")
            parts.append(f"{s} {label} {OUTCOMES.get((o['kind'], o['outcome']), o['outcome'])} {o['on']}"
                         + (f" at ${o['salary']:,}" if kept else ""))
        else:
            parts.append(f"{s} {label} at ${o['salary']:,}, to be decided by {o['due']}")
    return f"{SEASON_NOTE.sub('', stored)} ({'; '.join(parts)})"


def errors(root, player=None):
    """A snapshot dated from FROM's rollover on names the agreement only: its season's terms are derived."""
    player = Path(player or Path(root) / PLAYER)
    identity = _read(Path(player) / "professional_identity.json") or {}
    state = _read(Path(player) / FROM / "current_state.json") or {}
    start = state.get("rolled_over_on")
    if not start:
        return []
    rel = Path(player).relative_to(root) / "professional_identity.json"
    return [f"{rel.as_posix()}: the {s['as_of']} snapshot writes a season's salary into its contract line "
            f"({SEASON_NOTE.search(s['contract']).group().strip()}); from {FROM} the season's terms come from the "
            "contract record (runtime/identity_contract.py)"
            for s in identity.get("snapshots", []) if s["as_of"] >= start and SEASON_NOTE.search(s.get("contract") or "")]
