"""Wade's request that Miami keep its draft picks, and the trade request it promises (the user's words, 2006-04-19).

The request. A `keep_picks` row (`requested: keep`, `if_ignored: trade_request`, his words in `words`) in any season
folder's `*/wade_requests.json`, dated on or before the day, stands until a later `keep_picks` row with another verb
(`withdraw`) withdraws it: the latest row stands (`standing_request`; on one date the later row of one file, and
validation refuses a keep and a withdrawal of one date filed in different files, whose order would be the paths', not
the filing order). It is read across every season folder of the career, so the rollover, draft night, the summer
market and every later season find it where it was filed; nothing copies it. Before its date nothing reads it, so every
recorded trade, offer, packet and draft replays unchanged.

The front office's rule (one judgement wherever Miami could send a pick away; docs/front_office.md, Wade's requests). A
request never forces a decision. While the request stands, a package that sends one of Miami's picks is scored as an
opposed departure, the scale every request of his has (`scored`, `TradeDesk.scored_gain`): the gain x (1 - w) when it
is positive, x (1 + w) when it is negative, w being Wade's standing weight on the date (`standing.STANDING_WEIGHT`). At
franchise standing (w 0.8) a pick package needs five times the threshold before the request is weighed (0.50 for the
in-season 0.10): the recorded 2006-01-16 trade of Miami's 2006 first (0.492) would have fallen just short. On
draft night the on-clock answer is an even-chance draw, a call right on the line, so the request takes w of Miami's
acceptance away (`draft.keep_down`, `front_office.request_override` at margin 0). The trade request he stated is his own
decision, which the user confirms or withdraws when it is written; the front office does not price it in, which would
turn the request into a veto at a high standing. Wade's own package request dated on or after the keep_picks request
that names a pick is his newer wish for that pick: neither the score nor the consequence applies to it
(`run_trade.answer_requests`, the ranking's `keep_picks_exempt`).

The consequence. If Miami completes a trade that sends one of its picks while the request stands, Wade's trade request
is written the same day (`trade_request`): a `trade_request` row in the phase folder's `wade_requests.json` citing the
keep_picks row (path and index) and the trade, with his stated words, its milestone page beside it and
`wade_trade_request:<id>` in `current_state.pending_player_decisions`, so the driver stops ("WADE TRADE REQUEST",
`scripts/advance.py`) until the user confirms or withdraws it (`scripts/player_milestone.py --reply`, kind
`trade_request`). What follows a confirmed request (Miami answering it, trading Wade, another club becoming the
simulated club) is not modelled (docs/ROADMAP.md F1), so a confirmed request keeps the driver stopped (`confirmed`)
until it is; a withdrawn one lets the career go on.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAYER = Path("career/Dwyane_Wade")
REQUESTS_FILE = "wade_requests.json"
SUBJECT = "keep_picks"
KEEP = "keep"                                   # a later keep_picks row with another verb ("withdraw") withdraws it
CONSEQUENCE = "trade_request"                   # the request's `if_ignored`
TRADE_REQUEST = "trade_request"                 # the subject of the row the consequence writes
PENDING_PREFIX = "wade_trade_request:"
ANSWERS = {"confirm": "confirmed", "withdraw": "withdrawn"}
AWAITING = "awaiting_confirmation"
WADE, WADE_BBR = "Dwyane Wade", "wadedw01"


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _rel(path):
    """A request file's repository path from its last three parts (season, phase folder, file)."""
    return (PLAYER / Path(*Path(path).parts[-3:])).as_posix()


def rows(root=ROOT):
    """(repository path, index, row) of every row of every season folder's wade_requests.json, in path order."""
    for path in sorted((Path(root) / PLAYER).glob(f"????-??/*/{REQUESTS_FILE}")):
        for i, row in enumerate(_read(path).get("requests", [])):
            yield _rel(path), i, row


def keep_rows(root=ROOT):
    """((date, repository path, index), row) of every dated keep_picks row, in standing order (latest last)."""
    return sorted((((row["date"], rel, i), row) for rel, i, row in rows(root) if row.get("subject") == SUBJECT and row.get("date")),
                  key=lambda x: x[0])


def standing_request(day, root=ROOT):
    """The keep_picks request standing on `day`: the latest `keep_picks` row dated on or before it, when its verb is
    `keep`, as {"path", "index", "date", "requested", "if_ignored", "words", "source_ref"}; None before any, or after a
    withdrawal."""
    found = None
    for key, row in keep_rows(root):
        if key[0] <= day:
            found = (key, row)
    if found is None or found[1].get("requested") != KEEP:
        return None
    (date, rel, i), row = found
    return {"path": rel, "index": i, "date": date, "requested": KEEP, "if_ignored": row.get("if_ignored"),
            "words": row.get("words"), "source_ref": row.get("source_ref")}


def exempt(keep, requested_on):
    """Whether a package Wade asked for himself on `requested_on` is his newer wish for the picks it names: dated on or
    after the keep_picks request."""
    return bool(keep) and bool(requested_on) and requested_on >= keep["date"]


def scored(gain, weight):
    """A gain with the keep_picks request weighed: an opposed departure at the standing weight."""
    return gain * (1 - weight) if gain > 0 else gain * (1 + weight)


def basis(keep, weight, standing, before, after):
    """The sentence a ranking or record gives for the weighing."""
    return (f"Wade's keep_picks request of {keep['date']} ({keep['path']}) stands: standing {standing}, weight {weight}; "
            f"the pick is an opposed departure: gain {before:+.3f} -> {after:+.3f} (runtime/keep_picks.py).")


def picks_text(picks):
    return ", ".join(p.get("label") or f"{p['year']} round {p['round']} pick" for p in picks) or "a pick"


def request_id(day, trade_id):
    return f"{day}-{trade_id}"


def page_name(row):
    """One page per trade request: two trades on one date (two draft-night moves) write two pages."""
    return f"Milestone_{row['date']}_trade_request_{(row.get('cites') or {}).get('trade_id')}.md"


def trade_request(keep, day, trade_id, trade_record, picks, partner, standing):
    """Wade's trade request when Miami sent picks away while `keep` stood: (the `trade_request` row, its page)."""
    rid = request_id(day, trade_id)
    sent = picks_text(picks)
    row = {"date": day, "subject": TRADE_REQUEST, "id": rid, "player": WADE, "bbr_id": WADE_BBR, "requested": "trade",
           "words": keep["words"],
           "cites": {"keep_picks": {"path": keep["path"], "index": keep["index"], "date": keep["date"],
                                    "if_ignored": keep.get("if_ignored")},
                     "trade_id": trade_id, "trade_record": trade_record, "partner": partner, "picks": picks},
           "standing": {"standing": (standing or {}).get("standing"), "as_of": (standing or {}).get("as_of")},
           "note": (f"Wade asks Miami's front office to trade him. On {day} Miami sent {sent} to {partner} ({trade_id}) while "
                    f"his keep_picks request of {keep['date']} stood, and that request named this consequence in his own "
                    "words. Recorded the same day; it waits for the user to confirm or withdraw it. What follows a confirmed "
                    "request (Miami answering it, trading Wade, another club becoming the simulated club) is not modelled "
                    "(docs/ROADMAP.md F1), so a confirmed request keeps the career clock stopped until it is "
                    "(runtime/keep_picks.py)."),
           "source_ref": trade_record, "status": AWAITING, "answer": None, "answered": None, "reply": None}
    return row, page(row)


def page(row):
    """The player-facing page (docs/templates/player_milestones/workflow.md): identity line, the actual event, the
    evidence, the available responses and the next checkpoint."""
    c = row["cites"]
    items = [("Trade", f"Miami sends {picks_text(c['picks'])} to {c['partner']} (`{c['trade_id']}`)"),
             ("Trade record", f"`{c['trade_record']}`"),
             ("Your standing request", f"keep_picks of {c['keep_picks']['date']} (`{c['keep_picks']['path']}`), "
                                       f"if ignored: {c['keep_picks'].get('if_ignored') or 'not stated'}"),
             ("Your words", f"\"{row['words']}\""),
             ("Standing", f"{row['standing']['standing']} (as of {row['standing']['as_of'] or 'default'})")]
    table = "\n".join(f"| {k} | {v} |" for k, v in items)
    return f"""---
type: milestone
kind: trade_request
status: open
date: {row['date']}
record: {REQUESTS_FILE} ({row['id']})
---

# Trade request ({row['date']})

**Dwyane Wade** · Miami Heat · standing **{row['standing']['standing']}** · career date {row['date']}

**State: Awaiting your confirmation.** Miami traded a pick while your request to keep the picks stood, so your stated consequence is recorded: you ask Miami to trade you. The career clock stops until you confirm or withdraw it.

## What happened

| Item | Record |
| --- | --- |
{table}

The front office weighed your request by your standing (runtime/keep_picks.py; docs/front_office.md, Wade's requests). A request never forces its decision, and this one did not stop the trade.

## Your response

Reply with `scripts/player_milestone.py --reply` (kind `trade_request`, event `{row['id']}`), using the version of `{REQUESTS_FILE}` you read:

- **Confirm**: your trade request stands and is recorded. Miami's answer to it (trading you, which would make another club the simulated club, or keeping you) is not modelled yet (docs/ROADMAP.md F1), so the career clock stays stopped until it is.
- **Withdraw**: the trade request is withdrawn and the career goes on. Your keep_picks request still stands until you withdraw it with a new dated row.

## Next checkpoint

After a withdrawal the career resumes on the same date (`scripts/advance.py`); after a confirmation it waits for Miami's answer to be built.
"""


def report_line(row):
    """The driver's line for a written trade request (scripts/advance.py stops on "WADE TRADE REQUEST")."""
    c = row["cites"]
    return (f"WADE TRADE REQUEST: Miami sent {picks_text(c['picks'])} to {c['partner']} ({c['trade_id']}) while Wade's "
            f"keep_picks request of {c['keep_picks']['date']} stood; Wade asks to be traded (\"{row['words']}\"). Record: "
            f"{row['id']}; confirm or withdraw it with scripts/player_milestone.py --reply (kind trade_request).")


def add_pending(state, rid):
    pending = state.setdefault("pending_player_decisions", [])
    if PENDING_PREFIX + rid not in pending:
        pending.append(PENDING_PREFIX + rid)


def close(state, rid):
    state["pending_player_decisions"] = [d for d in state.get("pending_player_decisions", []) if d != PENDING_PREFIX + rid]


def find(root, season, rid):
    """(file path, index, row) of the trade request `rid` in the season's phase folders, or None."""
    for path in sorted((Path(root) / PLAYER / season).glob(f"*/{REQUESTS_FILE}")):
        for i, row in enumerate(_read(path).get("requests", [])):
            if row.get("subject") == TRADE_REQUEST and row.get("id") == rid:
                return path, i, row
    return None


def trade_requests(root=ROOT, season=None):
    """(repository path, row) of every trade request, oldest first (one season's when `season` is given)."""
    out = [(rel, row) for rel, _, row in rows(root) if row.get("subject") == TRADE_REQUEST
           and (season is None or rel.split("/")[2] == season)]
    return sorted(out, key=lambda x: (x[1].get("date") or "", x[1].get("id") or ""))


def confirmed(root=ROOT):
    """(repository path, row) of every confirmed trade request. Miami's answer to one is not modelled (docs/ROADMAP.md
    F1), so none has been answered and each keeps the driver stopped (`scripts/advance.py wade_waits`)."""
    return [(rel, row) for rel, row in trade_requests(root) if row.get("status") == ANSWERS["confirm"]]


def _cited_errors(root, cited, day):
    """Why a trade request of `day` does not cite the keep_picks request that stood when its trade was made, or None.
    The cited row is read by its path and index, so a withdrawal filed later on the same day (the user's answer while
    the clock is stopped) leaves it valid; any keep_picks row after it dated before `day` replaced or withdrew it."""
    path, index = Path(root) / (cited.get("path") or ""), cited.get("index")
    found = _read(path).get("requests", []) if path.is_file() else []
    row = found[index] if isinstance(index, int) and 0 <= index < len(found) else {}
    if row.get("subject") != SUBJECT or row.get("requested") != KEEP or row.get("date") != cited.get("date") or (row.get("date") or day) > day:
        return None, f"it must cite, by path and index, the keep_picks request standing on {day}"
    key = (row["date"], cited["path"], index)
    if any(k > key and k[0] < day for k, _ in keep_rows(root)):
        return row, f"the cited keep_picks request of {row['date']} was replaced or withdrawn before {day}"
    return row, None


def request_errors(root=ROOT):
    """Every keep_picks row is well formed, and a keep and a withdrawal of one date are filed in one file; every trade
    request is well formed, cites the keep_picks request that stood on its date (by path and index) with its words and a
    trade record that exists, has its page, is dated on or before its season's clock, and agrees with the season's
    pending list (listed exactly while unanswered); every pending entry names a request."""
    root = Path(root)
    errors, ids, dated = [], {}, {}
    for rel, i, row in rows(root):
        where = f"{rel} row {i}"
        if row.get("subject") == SUBJECT:
            if row.get("requested") not in (KEEP, "withdraw") or not row.get("date"):
                errors.append(f"{where}: a keep_picks row needs a date and requested keep or withdraw")
            if row.get("requested") == KEEP and (not row.get("words") or row.get("if_ignored") not in (None, CONSEQUENCE)):
                errors.append(f"{where}: a keep request records Wade's words and if_ignored {CONSEQUENCE} or none")
            dated.setdefault(row.get("date"), []).append((rel, row.get("requested")))
            continue
        if row.get("subject") != TRADE_REQUEST:
            continue
        needed = {"date", "id", "player", "requested", "words", "cites", "standing", "note", "source_ref", "status", "answer",
                  "answered", "reply"}
        if not needed <= set(row):
            errors.append(f"{where}: missing fields {sorted(needed - set(row))}")
            continue
        season = rel.split("/")[2]
        state_path = root / PLAYER / season / "current_state.json"
        state = _read(state_path) if state_path.is_file() else {}
        clock = state.get("current_date")
        c = row["cites"] or {}
        if row["id"] != request_id(row["date"], c.get("trade_id")):
            errors.append(f"{where}: id must be <date>-<trade_id>")
        if row["id"] in ids:
            errors.append(f"{where}: id {row['id']} also used by {ids[row['id']]}")
        ids[row["id"]] = where
        if clock and row["date"] > clock:
            errors.append(f"{where}: dated {row['date']}, after the career date {clock}")
        keep, problem = _cited_errors(root, c.get("keep_picks") or {}, row["date"])
        if problem:
            errors.append(f"{where}: {problem}")
        elif row["words"] != keep.get("words"):
            errors.append(f"{where}: the words must be the keep_picks request's own")
        if not c.get("picks") or not c.get("trade_record") or not (root / c["trade_record"]).is_file():
            errors.append(f"{where}: it must name the picks sent and an existing trade record")
        expected = AWAITING if row["answer"] is None else ANSWERS.get(row["answer"])
        if row["status"] != expected or (row["answer"] is None) != (row["answered"] is None):
            errors.append(f"{where}: status {AWAITING} while unanswered, else confirmed or withdrawn with its date")
        if row["answered"] is not None and not (row["date"] <= row["answered"] <= (clock or row["answered"])):
            errors.append(f"{where}: answered must lie between the request date and the career date")
        if not (root / rel).parent.joinpath(page_name(row)).is_file():
            errors.append(f"{where}: missing page {page_name(row)}")
        listed = PENDING_PREFIX + row["id"] in state.get("pending_player_decisions", [])
        if listed != (row["answer"] is None):
            errors.append(f"{where}: pending_player_decisions must list it exactly while it is unanswered")
    for day, found in sorted((d, f) for d, f in dated.items() if d):
        if len({rel for rel, _ in found}) > 1 and len({verb for _, verb in found}) > 1:
            errors.append(f"keep_picks rows of {day} in {sorted({rel for rel, _ in found})}: a keep and a withdrawal of one "
                          "date belong in one wade_requests.json, whose row order is their filing order")
    for state_path in sorted((root / PLAYER).glob("????-??/current_state.json")):
        for d in _read(state_path).get("pending_player_decisions", []):
            if d.startswith(PENDING_PREFIX) and d[len(PENDING_PREFIX):] not in ids:
                errors.append(f"{(PLAYER / state_path.parent.name).as_posix()}/current_state.json: pending {d} has no trade request")
    return errors
