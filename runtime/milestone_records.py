"""Dated milestone working records and guarded reply metadata for the live screens."""
from __future__ import annotations

from datetime import date
import hashlib
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PLAYER = Path("career/Dwyane_Wade")
SCREEN_MAP = {"calendar": "calendar", "checkpoint": "contract_checkpoint", "contract": "contract_negotiation",
              "market": "free_agency", "training": "offseason_training", "trade": "trade_update",
              "exit": "exit_meeting", "camp": "training_camp", "stats": "stats_review"}
SCREENS = SCREEN_MAP
START, END = "<!-- career-desk:start -->", "<!-- career-desk:end -->"


def read(path, default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else default


def version(path):
    """Opaque optimistic-concurrency token; a reply must name exactly what was read."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def source_path(root, reference):
    if not isinstance(reference, str) or not reference:
        raise ValueError("a career source_ref is required")
    path = (root / reference).resolve()
    if not path.is_relative_to((root / "career").resolve()) or not path.is_file():
        raise ValueError(f"source must be an existing career file: {reference}")
    return path


def load_registry(root, player, *, data=None):
    path = player / "milestones.json"
    registry = read(path) if data is None else data
    if registry is None:
        return None
    if registry.get("schema_version") != 1 or registry.get("enabled") is not True:
        raise ValueError("milestones.json requires schema_version 1 and enabled: true")
    if not isinstance(registry.get("events"), list):
        raise ValueError("milestones.json events must be a list")
    ids = set()
    previous = {}
    for e in registry["events"]:
        required = {"id", "season", "kind", "title", "recorded_on", "status", "owner", "needs_response", "source_ref", "details", "next_checkpoint"}
        if not isinstance(e, dict) or not required <= set(e):
            raise ValueError("a milestone event is missing required fields")
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", e["id"]) or e["id"] in ids:
            raise ValueError("milestone IDs must be unique lowercase slugs")
        ids.add(e["id"])
        if not re.fullmatch(r"\d{4}-\d{2}", e["season"]) or e["kind"] not in SCREENS:
            raise ValueError(f"{e['id']}: unknown season or kind")
        state = read(player / e["season"] / "current_state.json")
        if not state or date.fromisoformat(e["recorded_on"]) > date.fromisoformat(state["current_date"]):
            raise ValueError(f"{e['id']}: event cannot be recorded after its career clock")
        if e["status"] not in {"planned", "active", "review", "closed"} or e["owner"] not in {"player", "club", "staff", "none"}:
            raise ValueError(f"{e['id']}: invalid status or owner")
        if type(e["needs_response"]) is not bool or (e["needs_response"] and (e["owner"] != "player" or e["status"] == "closed")):
            raise ValueError(f"{e['id']}: only an open player decision can need a response")
        source_path(root, e["source_ref"])
        if not isinstance(e["details"], dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in e["details"].items()):
            raise ValueError(f"{e['id']}: details must map labels to text")
        checkpoint = e["next_checkpoint"]
        if not isinstance(checkpoint, dict) or not checkpoint.get("trigger"):
            raise ValueError(f"{e['id']}: next checkpoint needs a trigger")
        for field in ("starts_on", "ends_on"):
            if e.get(field):
                date.fromisoformat(e[field])
        if e.get("starts_on") and e.get("ends_on") and e["ends_on"] < e["starts_on"]:
            raise ValueError(f"{e['id']}: end precedes start")
        if checkpoint.get("date"):
            date.fromisoformat(checkpoint["date"])
        if e.get("supersedes"):
            before = previous.get(e["supersedes"])
            if not before or before["season"] != e["season"] or before["kind"] != e["kind"] or before["recorded_on"] > e["recorded_on"]:
                raise ValueError(f"{e['id']}: supersedes must name an earlier record in the same season and area")
            if any(p.get("supersedes") == e["supersedes"] for p in previous.values()):
                raise ValueError(f"{e['id']}: a working record can have only one direct successor")
        previous[e["id"]] = e
        last = e["recorded_on"]
        for r in e.get("responses", []):
            if not last <= r["date"] <= state["current_date"] or not r.get("text"):
                raise ValueError(f"{e['id']}: invalid response date or text")
            source_path(root, r["source_ref"])
            last = r["date"]
    return registry


def event_status(e):
    if e.get("_superseded_by"):
        return "History; followed by " + e["_superseded_by"]
    if e["status"] == "closed":
        return "Closed"
    if e.get("responses"):
        return "Player response recorded; awaiting follow-up"
    if e["needs_response"]:
        return "Awaiting your response"
    return {"planned": "Planned", "active": "Active", "review": "Review due"}[e["status"]]


def managed_navigation(page, block):
    old = page.read_text(encoding="utf-8") if page.is_file() else f"# {page.parent.name.replace('_', ' ')}\n"
    new = START + "\n\n" + block.rstrip() + "\n\n" + END
    if START in old:
        if END not in old:
            raise ValueError(f"{page}: incomplete career desk navigation block")
        return re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: new, old, flags=re.S)
    # Place discoverable links directly below the title, preserving authored content.
    first, sep, rest = old.partition("\n")
    return first + "\n\n" + new + "\n" + ("\n" + rest.lstrip("\n") if sep else "")


def augment_live_screens(context, screens):
    """Add working records and actual reply tokens to the existing detailed UI."""
    c = context
    registry = load_registry(c.root, c.player)
    if registry is None:
        return
    registry_path = c.player / "milestones.json"
    c.source(registry_path, "Dated milestone working records and player replies")
    guide = c.root / "docs/live_player_milestones.md"
    for screen in screens.values():
        action = c.action(guide, "Record your authorized reply", "Use the dated source and current record version; a browser visit does not submit a decision.")
        if action:
            screen["actions"].append(action)
    log_path = c.season / "01_Free_Agency/Wade_Rookie_Contract/negotiation_log.json"
    entries = [e for e in read(log_path, {}).get("entries", []) if c.known(e.get("date"))]
    if entries:
        screens["contract_negotiation"]["sections"].append({"title": "Reply to this version", "columns": ["Record", "Version", "Next step"],
            "rows": [[c.link(log_path, "Rookie negotiation log"), version(log_path), "Use rookie_contract: accept, counter, decline or request; execution remains separate"]]})
        if entries[-1]["party"] == "wade":
            screens["calendar"]["sections"].append({"title": "Waiting on Miami", "items": ["Your rookie-contract reply is recorded. The existing free-agency driver owns the next club response or execution."]})
            if not [p for p in c.state.get("pending_player_decisions", []) if p != "rookie_contract_offer"]:
                screens["calendar"]["status"] = "active"
    from .consultations import folder
    tokens = []
    for path in sorted(folder(c.root, c.season.name).glob("*.json")):
        r = read(path)
        if c.known(r.get("date")):
            tokens.append([r["id"], r["player"], r.get("answer") if c.known(r.get("answered")) else "Awaiting your answer", version(path)])
    if tokens:
        screens["trade_update"]["sections"].append({"title": "Consultation reply versions", "columns": ["Event ID", "Player", "Status", "Version"], "rows": tokens})
    from .extensions import offer_folder, page_name
    offers = []
    for path in sorted(offer_folder(c.root, c.season.name).glob("*.json")):
        r = read(path)
        if c.known(r.get("date")):
            o = r["offer"]
            status = r["answer"] if r.get("answer") and c.known(r.get("answered")) else "Awaiting your answer"
            offers.append([c.link(path.parent / page_name(r), r["id"]), r["date"], r["club"],
                           f"{o['years']} seasons from {o['first_season']}, ${o['total']:,}", status, version(path)])
    if offers:
        screens["contract_negotiation"]["sections"].append({"title": "Contract extension offers",
            "columns": ["Offer", "Date", "Club", "Terms", "Status", "Version"], "rows": offers})
        if any(row[4] == "Awaiting your answer" for row in offers):
            screens["contract_negotiation"]["status"] = "awaiting_response"
    successors = {e["supersedes"]: e["id"] for e in registry["events"] if e.get("supersedes")}
    events = [dict(e, _superseded_by=successors.get(e["id"])) for e in registry["events"] if e["season"] == c.season.name]
    current = [e for e in events if not e["_superseded_by"] and e["status"] != "closed"]
    pending = [e for e in current if e["needs_response"] and not e.get("responses")]
    for e in events:
        screen = screens[SCREEN_MAP[e["kind"]]]
        evidence = c.link(source_path(c.root, e["source_ref"]), "Owning dated record")
        rows = [["Event ID", e["id"]], ["Recorded", e["recorded_on"]], ["Status", event_status(e)], ["Owner", e["owner"]], ["Evidence", evidence],
                ["Reply registry version", version(registry_path)], *[list(item) for item in e["details"].items()]]
        if e.get("prompt"):
            rows.append(["Your response", e["prompt"]])
        for r in e.get("responses", []):
            rows.append(["Your reply on " + r["date"], r["text"]])
            rows.append(["Reply evidence", c.link(source_path(c.root, r["source_ref"]), "Authorized player decision")])
        nxt = e["next_checkpoint"]
        checkpoint = (nxt.get("date") or "Date not set") + ": " + nxt["trigger"]
        rows.append(["Next checkpoint", checkpoint])
        screen["sections"].append({"title": e["title"], "columns": ["Working record", "Dated information"], "rows": rows})
        if not e["_superseded_by"]:
            screen["status"] = "awaiting_response" if e in pending else "awaiting_follow_up" if e.get("responses") else e["status"]
            screen["next_checkpoint"] = checkpoint
    if events:
        screens["calendar"]["sections"].append({"title": "Your working calendar", "columns": ["Event", "Dates", "Status", "Next checkpoint", "Open"],
            "rows": [[e["title"], (e.get("starts_on") or "Not set") + " to " + (e.get("ends_on") or "Not set"), event_status(e),
                      (e["next_checkpoint"].get("date") or "Date not set") + ": " + e["next_checkpoint"]["trigger"],
                      {"label": "Working record", "href": "#" + SCREEN_MAP[e["kind"]]}] for e in events]})
    if pending:
        screens["calendar"]["status"] = "awaiting_response"
        screens["calendar"]["sections"].append({"title": "Waiting on your preferences", "columns": ["Event", "Your response"],
            "rows": [[e["title"], e.get("prompt", "Record your preference")] for e in pending]})
    conflicts = []
    intervals = [e for e in current if e.get("starts_on") and e.get("ends_on")]
    for i, a in enumerate(intervals):
        for b in intervals[i + 1:]:
            if max(a["starts_on"], b["starts_on"]) <= min(a["ends_on"], b["ends_on"]):
                conflicts.append([a["title"], b["title"], "Overlapping dates; confirm timing with the owners"])
    if conflicts:
        screens["calendar"]["sections"].append({"title": "Scheduling conflicts", "columns": ["Commitment", "Overlaps", "Action"], "rows": conflicts})


def build_phase_navigation(root, player):
    """Make the detailed live views discoverable from their actual phase folders."""
    if load_registry(root, player) is None:
        return {}
    def link(page, target, title):
        return f"[{title}]({Path(os.path.relpath(target, page.parent)).as_posix()})"
    outputs = {}
    groups = (("01_Free_Agency", ("contract_checkpoint", "contract_negotiation", "free_agency")),
              ("03_Offseason", ("offseason_training", "exit_meeting", "trade_update")),
              ("04_Training_Camp", ("training_camp", "offseason_training")),
              ("09_Draft", ("contract_checkpoint", "contract_negotiation")), ("00_Team", ("trade_update", "calendar")))
    for season in sorted(player.iterdir()):
        if not re.fullmatch(r"\d{4}-\d{2}", season.name) or not (season / "current_state.json").is_file():
            continue
        for folder, keys in groups:
            page = season / folder / "README.md"
            block = "**Current live player pages:** " + " · ".join(link(page, player / "Milestones" / (k + ".md"), k.replace("_", " ").capitalize()) for k in keys)
            block += " · " + link(page, player / "Milestones/README.md", "Full career desk")
            block += " · " + link(page, player / "Milestones/index.html", "Interactive view")
            outputs[page] = managed_navigation(page, block)
    return outputs
