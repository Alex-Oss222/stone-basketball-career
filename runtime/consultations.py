"""The franchise consultation gate (the user's premise; docs/front_office.md, "Franchise consultation").

Once Wade's computed standing is `franchise` (runtime/standing.py), Miami must ask him before it
signs or trades for another star player: the move cannot proceed without his answer and his
objection stops it. A star is a player whose 2002-03 production value (`Valuation.value`) reaches
STAR_PRODUCTION_VALUE; a player without 2002-03 evidence is never a star under this rule. The gate
covers acquisitions only (a free-agent target, the player Miami trades for, the player of a
sign-and-trade acquisition and every player arriving in an own sign-and-trade-out); re-signing
Miami's own player is keeping, not adding, and players Miami sends out are never gated.

A consultation is Wade's own decision, never a draw: its record is a plain JSON file under the
season's `Wade_Consultations/` folder with a milestone page beside it, not a `*.decision.json`.
The career clock stops on the asking day until he answers: while any consultation is unanswered
the front office asks nothing else and makes no move (the drivers check `unanswered` before they
act), so one question is never asked twice. An objection is kind-agnostic and season-wide (no
pursuit of that player until Wade files a new dated record); an approval covers its kind and
player for the season. Only an answered record is an answer (`answer_of`). Closed records are
never edited; Wade changes an answer only by a new dated record.
"""
import json
from pathlib import Path
import re

from .valuation import read

ROOT = Path(__file__).resolve().parents[1]
PLAYER = Path("career/Dwyane_Wade")
STAR_PRODUCTION_VALUE = 20.0     # judgement: 2002-03 production value (Valuation.value); met by 13 inventory players in 2002-03 (about one per two clubs); 15.0 would catch 46
CONSULTATION_STANDING = "franchise"
KINDS = ("free_agent", "trade", "sign_and_trade")     # acquisitions only: re-signing Miami's own player is keeping, not adding (the premise says "another")
ANSWERS = (None, "approve", "object")
FOLDER = "Wade_Consultations"                          # career/Dwyane_Wade/<season>/Wade_Consultations/ (player-owned, season-wide)
PENDING_PREFIX = "star_consultation:"
STATUSES = ("asked", "closed")
RULE = f"2002-03 production value >= {STAR_PRODUCTION_VALUE} (runtime/consultations.py)"


def slug(name):
    return re.sub(r"[^a-z0-9]+", "_", name.lower().replace("'", "")).strip("_")


def is_star(value):
    return value is not None and value >= STAR_PRODUCTION_VALUE


def consultation_required(standing, value):
    return standing == CONSULTATION_STANDING and is_star(value)


def folder(root, season):
    return Path(root) / PLAYER / season / FOLDER


def consultation_id(day, kind, player):
    return f"{day}-{slug(player)}-{kind}"


def records(root, season):
    """Every consultation record of the season, oldest first."""
    f = folder(root, season)
    if not f.exists():
        return []
    out = []
    for path in sorted(f.glob("*.json")):
        out.append(json.loads(path.read_text(encoding="utf-8")))
    return sorted(out, key=lambda r: (r["date"], r["id"]))


def answer_of(root, season, player, on, kind=None):
    """The latest answered record for the player dated on or before `on` (any kind, or one kind), or None.
    An unanswered record is a question, not an answer, so it never hides an earlier answer."""
    rows = [r for r in records(root, season)
            if r["player"] == player and r["date"] <= on and r["answer"] is not None and (kind is None or r["kind"] == kind)]
    return rows[-1] if rows else None


def open_record(root, season, player, kind):
    """The unanswered record for the player and kind, whatever its date, or None (asked once, answered once)."""
    rows = [r for r in records(root, season) if r["player"] == player and r["kind"] == kind and r["answer"] is None]
    return rows[-1] if rows else None


def objected(root, season, player, on):
    r = answer_of(root, season, player, on)
    return bool(r) and r["answer"] == "object"


def approved(root, season, kind, player, on):
    r = answer_of(root, season, player, on, kind)
    return bool(r) and r["answer"] == "approve"


def answers(root, season, on):
    """A callable `(kind, player) -> "approve" | "object" | None` for the desk and the plan."""
    def answer(kind, player):
        if objected(root, season, player, on):
            return "object"
        if approved(root, season, kind, player, on):
            return "approve"
        return None
    return answer


def ask(root, state, day, kind, player, bbr_id, club, *, terms=None, trade_id=None, basis, evidence, season="2003-04", standing=None):
    """Write the consultation record and its page once; add the pending entry to the state. Returns the record
    (the existing one when the same ask was already written, or the still-unanswered record of the same
    player and kind from an earlier day: a question is asked once and waits for its answer)."""
    if kind not in KINDS:
        raise ValueError(f"unknown consultation kind {kind!r}")
    f = folder(root, season)
    cid = consultation_id(day, kind, player)
    path = f / f"{cid}.json"
    pending_record = open_record(root, season, player, kind)
    if path.exists():
        record = json.loads(path.read_text(encoding="utf-8"))
    elif pending_record is not None:
        record, cid = pending_record, pending_record["id"]
    else:
        f.mkdir(parents=True, exist_ok=True)
        standing = standing or {"standing": CONSULTATION_STANDING, "as_of": None}
        record = {"schema_version": 1, "id": cid, "date": day, "kind": kind, "player": player, "bbr_id": bbr_id, "club": club,
                  "terms": terms, "trade_id": trade_id, "standing": {"standing": standing["standing"], "as_of": standing.get("as_of")},
                  "star_basis": {"value": evidence.get("value"), "rule": RULE}, "basis": basis, "status": "asked",
                  "answer": None, "answered": None, "note": None}
        path.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        (f / page_name(record)).write_text(page(record, evidence), encoding="utf-8")
    pending = state.setdefault("pending_player_decisions", [])
    if PENDING_PREFIX + cid not in pending:
        pending.append(PENDING_PREFIX + cid)
    return record


def close(root, state, cid):
    """Remove the pending entry once Wade has answered (the record itself is Wade's)."""
    state["pending_player_decisions"] = [d for d in state.get("pending_player_decisions", []) if d != PENDING_PREFIX + cid]


def close_answered(root, state, season):
    """Close every answered record still pending in the state; returns the records closed, oldest first."""
    closed = []
    for r in records(root, season):
        if r["answer"] is not None and PENDING_PREFIX + r["id"] in state.get("pending_player_decisions", []):
            close(root, state, r["id"])
            closed.append(r)
    return closed


def unanswered(root, season, on):
    """Ids of the consultations asked on or before the date that Wade has not answered: the clock waits for them,
    and the front office asks nothing else and makes no move until they are answered."""
    return [r["id"] for r in records(root, season) if r["answer"] is None and r["date"] <= on]


def page_name(record):
    return f"Milestone_{record['date']}_consultation_{slug(record['player'])}.md"


def page(record, evidence):
    """The player-facing page (docs/templates/player_milestones/workflow.md): the identity line, the actual
    proposed move, the decision-relevant evidence, the available responses and the next checkpoint."""
    kind_text = {"free_agent": "sign as a free agent", "trade": "acquire by trade", "sign_and_trade": "acquire by sign-and-trade"}[record["kind"]]
    line = evidence.get("line") or "no 2002-03 line recorded"
    rows = [("Proposed move", f"Miami wants to {kind_text} **{record['player']}** ({record['club']})"),
            ("2002-03 line", line),
            ("Production value", f"{evidence.get('value')} (star line {STAR_PRODUCTION_VALUE}; {RULE})"),
            ("Salary or ask", evidence.get("salary", "Not recorded")),
            ("Miami's cap position", evidence.get("cap_position", "Not recorded")),
            ("Fit", evidence.get("fit", "Not recorded")),
            ("Front office's reason", evidence.get("reason", "Not recorded")),
            ("Trade record", record["trade_id"] or "none yet (the proposal waits for your answer)")]
    table = "\n".join(f"| {k} | {v} |" for k, v in rows)
    return f"""---
type: milestone
kind: franchise_consultation
status: open
date: {record['date']}
record: {record['id']}.json
---

# Consultation: {record['player']} ({record['date']})

**Dwyane Wade** · Miami Heat · standing **{record['standing']['standing']}** (as of {record['standing']['as_of'] or 'default'}) · career date {record['date']}

**State: Awaiting your response.** The front office does not make this move, or any other move that day, until you answer.

## The proposed move

| Item | Value |
| --- | --- |
{table}

Evidence is what Miami's front office knows on {record['date']}: 2002-03 statistics and the June 26, 2003 contract inventory. This page is a consultation under the career's premise (once your standing is franchise, Miami must ask before it adds another star); it is not a contract right.

## Your response

Write one of these into `{record['id']}.json`, with the date you answer (`answered`, on or after {record['date']}, never after the career date):

- **Approve**: set `"answer": "approve"`. The front office may pursue him this way this season.
- **Object**: set `"answer": "object"`. Miami drops the pursuit of this player for the season, by any route, until you file a new dated record.

Set `"status": "closed"` with your answer; a note is optional. Closed records are never edited.

## Next checkpoint

The front office resumes on the next run after your answer (`scripts/run_free_agency.py --write <date>` or `scripts/run_trade.py --propose <date>`), on the same career date.
"""


def consultation_errors(root=ROOT):
    """Every consultation record is well formed, dated on or before the career clock, matches its file and page,
    agrees with the pending list, and no player has two unanswered questions."""
    errors = []
    root = Path(root)
    for season_dir in sorted((root / PLAYER).glob("*/")):
        if not re.fullmatch(r"\d{4}-\d{2}", season_dir.name):
            continue
        f = season_dir / FOLDER
        state_path = season_dir / "current_state.json"
        state = read(state_path, root) if state_path.exists() else {}
        pending = [d for d in state.get("pending_player_decisions", []) if d.startswith(PENDING_PREFIX)]
        ids = set()
        open_players = {}
        if f.exists():
            for path in sorted(f.glob("*.json")):
                rel = path.relative_to(root)
                try:
                    r = json.loads(path.read_text(encoding="utf-8"))
                except ValueError as exc:
                    errors.append(f"{rel}: invalid JSON: {exc}")
                    continue
                needed = {"schema_version", "id", "date", "kind", "player", "bbr_id", "club", "terms", "trade_id", "standing",
                          "star_basis", "basis", "status", "answer", "answered", "note"}
                if not isinstance(r, dict) or not needed <= set(r):
                    errors.append(f"{rel}: missing fields {sorted(needed - set(r or {}))}")
                    continue
                ids.add(r["id"])
                if r["kind"] not in KINDS:
                    errors.append(f"{rel}: unknown kind {r['kind']!r}")
                if r["answer"] not in ANSWERS:
                    errors.append(f"{rel}: unknown answer {r['answer']!r}")
                if r["id"] != path.stem or r["id"] != consultation_id(r["date"], r["kind"], r["player"]):
                    errors.append(f"{rel}: id must be the file stem and <date>-<player>-<kind>")
                if (r["answer"] is None) != (r["answered"] is None):
                    errors.append(f"{rel}: answered is set exactly when answer is")
                if state.get("current_date") and r["date"] > state["current_date"]:
                    errors.append(f"{rel}: asked on {r['date']}, after the career date {state['current_date']}")
                if r["answered"] is not None and not (r["date"] <= r["answered"] <= state.get("current_date", r["answered"])):
                    errors.append(f"{rel}: answered must lie between the asking date and the career date")
                if r["answer"] is None:
                    if r["player"] in open_players:
                        errors.append(f"{rel}: {r['player']} already has the unanswered consultation {open_players[r['player']]}; one question at a time")
                    else:
                        open_players[r["player"]] = r["id"]
                if r["status"] != ("closed" if r["answer"] else "asked"):
                    errors.append(f"{rel}: status must be asked while unanswered and closed once answered")
                if not isinstance(r["standing"], dict) or r["standing"].get("standing") != CONSULTATION_STANDING:
                    errors.append(f"{rel}: a consultation is asked only at {CONSULTATION_STANDING} standing")
                if not isinstance(r["star_basis"], dict) or not is_star(r["star_basis"].get("value")):
                    errors.append(f"{rel}: star_basis.value must reach {STAR_PRODUCTION_VALUE}")
                if not (f / page_name(r)).exists():
                    errors.append(f"{rel}: missing page {page_name(r)}")
                entry = PENDING_PREFIX + r["id"]
                if r["answer"] is None and entry not in pending:
                    errors.append(f"{rel}: unanswered but not in pending_player_decisions")
                if r["answer"] is not None and entry in pending:
                    errors.append(f"{rel}: answered but still in pending_player_decisions")
        for d in pending:
            if d[len(PENDING_PREFIX):] not in ids:
                errors.append(f"{season_dir.relative_to(root)}/current_state.json: pending {d} has no consultation record")
    return errors
