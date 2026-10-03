"""Detailed live milestone views from dated canonical career records.

Pure reporting: no clock advancement, offer generation, decisions, randomness,
simulation or career writes. Inactive pages explain their activation trigger.
The same payload supplies the live HTML and detailed Markdown fallbacks.
"""
from __future__ import annotations

from datetime import date
import json
import os
from pathlib import Path
import re

from .career_stats import aggregate, identity_at
from .rookie_contract import rookie_terms

GENERATED = "<!-- Generated live career view; edit canonical event records and rebuild. -->\n"
TEMPLATE = Path(__file__).parent / "assets/career_milestones.html"
SCREEN_IDS = ("calendar", "contract_checkpoint", "contract_negotiation", "free_agency",
              "offseason_training", "trade_update", "exit_meeting", "training_camp", "stats_review")


def _money(value):
    return "$" + format(value, ",.0f") if type(value) in (int, float) else "Not recorded"


def _text(value, unknown="Not recorded"):
    if value is None or value == "":
        return unknown
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, list):
        return "; ".join(_text(v) for v in value) or unknown
    if isinstance(value, dict):
        return "; ".join(f"{k.replace('_', ' ')}: {_text(v)}" for k, v in value.items()) or unknown
    return str(value)


def _date(value):
    try:
        return date.fromisoformat(value[:10]) if isinstance(value, str) else None
    except ValueError:
        return None


def _table(title, columns, rows, **extra):
    return {"title": title, "columns": columns, "rows": rows, **extra}


class _Context:
    def __init__(self, player, identity, records, root):
        self.player = Path(player).resolve()
        self.root = Path(root).resolve() if root else self.player.parents[1]
        self.output = self.player / "Milestones"
        states = []
        for folder in self.player.iterdir():
            if re.fullmatch(r"\d{4}-\d{2}", folder.name) and (folder / "current_state.json").is_file():
                value = self.read(folder / "current_state.json")
                if _date(value.get("current_date")):
                    states.append((value["current_date"], folder, value))
        if not states:
            raise ValueError("live milestones require an authoritative dated current_state.json")
        self.on, self.season, self.state = max(states, key=lambda r: (r[0], r[1].name))
        self.cutoff = _date(self.on)
        self.identity = identity_at(identity, self.on)
        self.name = self.identity.get("display_name", self.identity.get("full_name", self.player.name))
        self.records = [r for r in records if r.get("season") == self.season.name and
                        r.get("status") == "played" and _date(r.get("date")) and _date(r["date"]) <= self.cutoff]
        self.team = self.season / "00_Team"
        self.sources = {}
        self.scale_reference = None

    @staticmethod
    def read(path):
        path = Path(path)
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}

    def known(self, value):
        d = _date(value)
        return d is not None and d <= self.cutoff

    def snapshot(self, path, keys=("as_of", "date", "opened")):
        value = self.read(path)
        if not value or not any(self.known(value.get(k)) for k in keys):
            return {}
        if any(_date(value.get(k)) and not self.known(value[k]) for k in
               ("as_of", "date", "opened", "updated", "updated_at", "evaluated", "cut_done", "injuries_drawn")):
            return {}
        return value

    def href(self, path):
        path = Path(path).resolve()
        if path != self.root and self.root not in path.parents:
            raise ValueError("milestone sources must stay inside the repository")
        return Path(os.path.relpath(path, self.output)).as_posix()

    def source(self, path, label):
        if not Path(path).is_file():
            return None
        ref = {"label": label, "href": self.href(path)}
        self.sources[ref["href"]] = ref
        return ref

    def link(self, path, label):
        return self.source(path, label) or {"label": label + " (not recorded)", "href": None}

    def action(self, path, label, description):
        return {"label": label, "href": self.href(path), "description": description} if Path(path).is_file() else None

    def phase(self, area):
        path = self.season / area / "note.md"
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        front = text.split("---", 2)[1] if text.startswith("---") else ""
        meta = dict((k.strip(), v.strip()) for k, v in re.findall(r"^([^:\n]+):([^\n]*)$", front, re.M))
        rows = [[day, body] for day, body in re.findall(r"^[-*] (\d{4}-\d{2}-\d{2}):\s*(.+)$", text, re.M) if self.known(day)]
        through = meta.get("through")
        status = meta.get("status", "not_recorded") if not through or self.known(through) else "not_available"
        return {"path": path, "status": status, "through": through if self.known(through) else None, "rows": rows}

    def files(self, folder, date_keys=("date", "opened", "as_of")):
        out = []
        for path in sorted(Path(folder).glob("*.json")):
            if path.name.endswith((".decision.json", ".result.json")):
                continue
            value = self.snapshot(path, date_keys)
            if value:
                out.append((path, value))
        return out

    def view(self, screen_id, title, status, trigger, summary, sections, actions=(), next_checkpoint=""):
        return {"id": screen_id, "title": title, "status": status, "trigger": trigger,
                "summary": summary, "sections": sections, "actions": [a for a in actions if a],
                "sources": [], "next_checkpoint": next_checkpoint,
                "metrics": [{"label": "Career date", "value": self.on},
                            {"label": "Team", "value": self.state.get("team", self.identity.get("team"))},
                            {"label": "Season", "value": self.season.name}]}


def _request_rows(c):
    rows = []
    for path in sorted(c.season.glob("*/wade_requests.json")):
        for row in c.read(path).get("requests", []):
            if c.known(row.get("date")):
                rows.append([row["date"], _text(row.get("subject")), _text(row.get("player")),
                             _text(row.get("requested")), _text(row.get("note")), c.link(path, "Recorded request")])
    return rows


def _consultations(c):
    rows, actions = [], []
    for path, row in c.files(c.season / "Wade_Consultations"):
        answered = c.known(row.get("answered"))
        rows.append([row["date"], _text(row.get("kind")), _text(row.get("player")),
                     _text(row.get("answer")) if answered else "Awaiting your answer",
                     _text(row.get("basis")), c.link(path, "Consultation record")])
        slug = re.sub(r"[^a-z0-9]+", "_", row.get("player", "").lower().replace("'", "")).strip("_")
        page = path.parent / f"Milestone_{row['date']}_consultation_{slug}.md"
        if not answered:
            actions.append(c.action(page if page.is_file() else path, "Answer the recorded consultation",
                                    "Approve or object to this actual star acquisition under the career's franchise-consultation premise."))
    return rows, actions


def _contract_views(c):
    sheet_path = c.team / "Finances/contract_schedules.json"
    sheet = c.snapshot(sheet_path)
    player = next((p for p in sheet.get("players", []) if p.get("player") == c.name), {})
    if ((player.get("signed_date") and not c.known(player["signed_date"])) or
            ((player.get("acquired") or {}).get("date") and not c.known(player["acquired"]["date"]))):
        player = {}
    if sheet:
        c.source(sheet_path, "Current contract and cap-control record")
    contract_status = c.state.get("contract_status", "Not recorded")
    draft_rights = "draft" in contract_status or "unsigned_first_round" in player.get("status", "")
    signed = bool(player and not draft_rights and c.known(player.get("signed_date")))
    schedule = [[season, _money(amount), _text(player.get("amount_kind", {}).get(season))]
                for season, amount in player.get("schedule", {}).items()]
    control_rows = [["Live control", contract_status.replace("_", " ")],
                    ["Signed professional contract", "Recorded" if signed else "Not confirmed in the current control record"],
                    ["Current cap hold", _money(player.get("current_cap_hold"))],
                    ["Cap hold meaning", "Team accounting charge; not player earnings or an accepted offer"],
                    ["Free-agent classification", "Not a free agent: unsigned draft rights" if draft_rights else "Requires dated expiry, option and rights review"],
                    ["Actual signing date", player.get("signed_date") if signed else "Not recorded"],
                    ["Source snapshot", sheet.get("as_of", "Not recorded")]]
    log_path = c.season / "01_Free_Agency/Wade_Rookie_Contract/negotiation_log.json"
    entries = [e for e in c.read(log_path).get("entries", []) if c.known(e.get("date"))]
    actual_offers = [e for e in entries if e.get("party") == "miami" and e.get("action") in {"offer", "counter"} and e.get("terms")]
    signed_entries = [e for e in entries if e.get("action") == "sign"]
    last_offer = actual_offers[-1] if actual_offers else None
    last_action = entries[-1] if entries else {}
    proposal_state = ("recorded" if signed_entries else
                      "awaiting_execution" if last_action.get("party") == "wade" and last_action.get("action") == "accept" else
                      "awaiting_club" if last_action.get("party") == "wade" and last_action.get("action") in {"counter", "request", "decline"} else
                      "awaiting_response" if last_offer else "inactive")
    next_response = {
        "recorded": "Verify registration and the authoritative contract record; no second player acceptance is requested.",
        "awaiting_execution": "The player's acceptance is recorded. The next step is verified signing and registration.",
        "awaiting_club": "The player's response is recorded. Miami must answer before a new player response is due.",
        "awaiting_response": "Your dated response to the actual proposal, then Miami's answer or verified execution.",
        "inactive": "Miami records its actual first offer; the player then chooses a response.",
    }[proposal_state]
    if entries:
        c.source(log_path, "Dated rookie-contract negotiation log")
    offer_schedule = [[year, _money(value), _text(last_offer["terms"].get("amount_kind", {}).get(year))]
                      for year, value in (last_offer or {}).get("terms", {}).get("schedule", {}).items()]
    reference = []
    pick = c.state.get("draft", {}).get("overall")
    scale_path = c.root / "library/2003/league/nba_2003_04_cap_rules.json"
    if draft_rights and c.season.name == "2003-04" and type(pick) is int and scale_path.is_file():
        terms = {p: rookie_terms(pick, p, c.root) for p in (80, 100, 120)}
        for year in terms[100]["schedule"]:
            reference.append([year, *[_money(terms[p]["schedule"][year]) for p in (80, 100, 120)],
                              "Team option, not exercised" if terms[100]["amount_kind"][year] == "team_option" else "Rookie-scale reference"])
        c.scale_reference = {
            "schema_version": 1, "reference_only": True, "as_of": c.on,
            "player": c.name, "draft_year": 2003, "pick": pick,
            "basis": "Fixed 1999-agreement rookie scale; no offer or option decision implied.",
            "terms_by_scale_percent": {str(p): terms[p] for p in (80, 100, 120)},
            "source": c.href(sheet_path) if sheet_path.is_file() else None,
        }
        # The combined league file also contains a cap published after draft
        # night. Link the dated player-scale projection on the canonical sheet,
        # not that mixed-date source, from the current player-facing view.
        c.source(sheet_path, "Dated contract control and fixed rookie-scale reference")
        c.sources["rookie_scale_reference.json"] = {
            "label": "Rookie-scale-only reference: no unpublished cap data",
            "href": "rookie_scale_reference.json",
        }
    checkpoint = c.view("contract_checkpoint", "Contract checkpoint", "active",
        "A dated contract, option, expiry or draft-rights change.",
        "Your current control status and next contract gate are drawn from the career records.", [
            _table("Your contract position", ["Item", "Recorded position"], control_rows),
            _table("Existing amounts on the club's record", ["Season", "Amount", "Nature"], schedule,
                   notice="A draft hold and an unexercised option are not signed guaranteed salary."),
            _table("Upcoming decision ownership", ["Decision", "Owner", "Current gate"], [
                ["Respond to a written contract proposal", "You", "Offer recorded" if last_offer else "No actual offer recorded"],
                ["Issue or revise a club offer", "Miami front office", "Club-owned decision"],
                ["Exercise a team option", "Club", "No current player-controlled team-option decision"],
                ["Verify UFA/RFA status", "Contract/rights review", "Draft rights are neither UFA nor RFA" if draft_rights else "Use dated contract and qualifying-offer evidence"],
                ["Register a signed contract", "Verified execution workflow", "No change occurs from reading this page"]]),
            _table("Evidence required before signing", ["Check", "Current result"], [
                ["Actual written offer and version", "Recorded in negotiation log" if last_offer else "Missing"],
                ["Player's actual response", "See dated log" if entries else "Not recorded"],
                ["Terms, guarantees and option treatment", "Review actual proposal; scale references are not guarantees"],
                ["Signing window and registration", "Must be verified on the event date"],
                ["Replacement contract", "Never generated by an expiry or an empty calendar page"]])],
        [c.action(sheet_path, "Review current contract record", "Inspect the recorded obligations and their amount types.")],
        "A real club offer, contract event or verified option/expiry deadline.")
    negotiation = c.view("contract_negotiation", "Contract negotiation", proposal_state,
        "A dated, actual offer opens the response desk; unsigned draft rights alone do not create one.",
        f"Miami's latest recorded offer is dated {last_offer['date']}." if last_offer else
        "No written rookie-contract offer is recorded at this checkpoint. Your scale reference is available for preparation.", [
            _table("Live eligibility and proposal", ["Item", "Position"], [
                ["Player status", contract_status.replace("_", " ")],
                ["Current proposal", last_offer["date"] if last_offer else "None recorded"],
                ["Whose response is next", next_response],
                ["Negotiation participants", "You and Miami; draft rights remain with Miami" if draft_rights else "As identified in the actual dated offer"],
                ["Market-worth estimate", "Rookie-scale signing; NBA-market value does not set this salary" if draft_rights else "No verified live market valuation supplied"],
                ["Player status selector", "Live eligibility follows records; UFA/RFA cannot be selected here"]]),
            _table("Actual latest club proposal", ["Season", "Salary", "Protection / option classification"], offer_schedule,
                   notice="No rows means no actual club offer. A player counter does not rewrite the club's proposal."),
            _table(f"Fixed No. {pick} rookie-scale reference" if pick else "Fixed rookie-scale reference",
                   ["Season", "80% of scale", "100% of scale", "120% of scale", "Nature"], reference,
                   notice="Legal scale reference only: not offers, signed salary or a future option decision."),
            _table("Dated negotiation history", ["Date", "Party", "Action", "Scale percentage", "Recorded note"], [
                [e["date"], _text(e.get("party")), _text(e.get("action")),
                 (e.get("terms") or {}).get("percent_of_scale"), _text(e.get("note"))] for e in entries]),
            _table("Your response and the separate club decision", ["Response", "Available when", "Consequence"], [
                ["Accept the actual proposal", "A live offer is recorded and timing/terms are verified", "Your decision; execution requires its proper workflow"],
                ["Counter within the applicable scale", "A live offer is recorded", "Your proposal; Miami must separately answer"],
                ["Ask about timing, role or protection", "The negotiation is open", "An attributed request, not a guaranteed assignment"],
                ["Decline or continue discussions", "An actual proposal is open", "Does not turn draft rights into free agency"]]),
            {"title": "Terms to inspect together", "items": [
                "Exact salary for every year; guaranteed and conditional amounts separately.",
                "Option holder, exercise deadline and actual option decision.",
                "Signing date, registration and any verified conditions.",
                "Basketball role discussions remain separate from salary and legal principal terms."]}],
        [c.action(log_path, "Open the actual negotiation record",
                  "Review the recorded proposal and the party whose response is due; no duplicate acceptance is requested.") if entries else None,
         c.action(c.root / "docs/front_office.md", "Review the rookie-contract workflow", "Explains the existing club-offer and player-response process.")],
        next_response)
    if signed_entries and draft_rights:
        negotiation["sections"].append({"title": "Registration check", "notice":
            "A signing entry exists, but the authoritative state still shows draft rights. Resolve this discrepancy before treating the contract as registered."})
    return checkpoint, negotiation, player, draft_rights


def _basketball_views(c, contract):
    depth_path = c.team / "Team/Depth_Chart/depth_chart.json"
    depth = c.snapshot(depth_path)
    rotation_path = depth_path.with_name("rotation.json")
    rotation = c.snapshot(rotation_path)
    reviewed = False
    if rotation and any(c.known(p.parent.name) for p in depth_path.parent.glob("Reviews/*/rotation.json")):
        from .rotation_reviews import rotation_in_force
        # Reporting keeps the last completed assignment while the next review
        # awaits a draw. The game builder independently enforces the due gate.
        rotation, depth = rotation_in_force(c.on, c.root, c.season.name, require_review=False)
        if rotation.get("review"):
            reviewed = True
            folder = depth_path.parent / "Reviews" / rotation["as_of"]
            depth_path, rotation_path = folder / "depth_chart.json", folder / "rotation.json"
            c.source(folder / "review.json", "Dated staff rotation review")
    if depth:
        c.source(depth_path, "Current dated staff depth chart")
    role_rows = [[position, ", ".join(_text(n) for n in names), "Staff ordering; not a future minutes promise"]
                 for position, names in depth.get("positions", {}).items()]
    unassigned = [p for p in depth.get("unassigned_draft_rights", []) + depth.get("unassigned_arrivals", [])
                  if p.get("name", p.get("player")) == c.name]
    role = "Unassigned rookie; staff role decision pending" if unassigned else _text(c.identity.get("role"))
    if reviewed:
        minutes = next((p.get("minutes", 0) for p in rotation["players"] if p["player_id"] == c.name), 0)
        positions = [pos for pos, name in rotation.get("starters", {}).items() if name == c.name]
        assignment = "Starting " + "/".join(positions) if positions else "Rotation" if minutes else "Outside current rotation"
        role = f"{assignment}; staff plan {minutes:g} minutes"
    offseason, camp_phase = c.phase("03_Offseason"), c.phase("04_Training_Camp")
    c.source(offseason["path"], "Offseason player decisions and events")
    c.source(camp_phase["path"], "Training-camp events and player response")
    training_path = c.season / "03_Offseason/training_plan.json"
    training = c.snapshot(training_path)
    if training:
        c.source(training_path, "Dated staff/player training plan")
    blocks = [b for b in training.get("blocks", []) if c.known(b.get("date", b.get("as_of")))]
    training_view = c.view("offseason_training", "Offseason training",
        "active" if training or offseason["rows"] else "inactive",
        "A dated player priority and staff-supported development block.",
        "Recorded goals, assigned work and measured results remain separate. No ability gain is awarded by a planning page.", [
            _table("Starting point", ["Item", "Recorded evidence"], [
                ["Current role", role], ["Availability", _text(c.identity.get("availability"))],
                ["Chosen focus", _text(training.get("focus"))], ["Baseline measurement", _text(training.get("baseline"))],
                ["Qualified staff restrictions", _text(training.get("restrictions"), "No current training-specific assessment recorded")],
                ["Agreed review", _text(training.get("review_date"), "No review scheduled")]]),
            _table("Dated development blocks", ["Date", "Focus", "Work / dose", "Owner", "Evidence", "Result"], [
                [b.get("date", b.get("as_of")), _text(b.get("focus")), _text(b.get("work")),
                 _text(b.get("owner")), _text(b.get("evidence")), _text(b.get("result"))] for b in blocks]),
            _table("Planning conversation still to record", ["Item", "Who supplies it", "Current position"], [
                ["Main skill priority and why", "Player", _text(training.get("goal"))],
                ["Representative possession or drill", "Player and staff", _text(training.get("test"))],
                ["Workload and recovery limits", "Qualified staff", _text(training.get("load_plan"))],
                ["Facilities, travel and protected time", "Player and staff", _text(training.get("logistics"))],
                ["Success criterion and sample", "Staff and player", _text(training.get("success_criteria"))],
                ["What receives less time", "Player", _text(training.get("tradeoff"))]]),
            _table("Recorded offseason discussion", ["Date", "Event / player decision"], offseason["rows"]),
            {"title": "Your legitimate response", "items": [
                "Choose a focus and explain the basketball problem you want to solve.",
                "Report availability and request a staff-supported plan.",
                "Return with recorded drill/game evidence at the agreed review.",
                "A preference does not assign staff, prescribe an unsourced workload or change engine ability."]}],
        [c.action(training_path if training else offseason["path"], "Open your recorded development work",
                  "Record a real dated priority or review in the owning offseason record.")],
        _text(training.get("review_date"), "The player and staff agree a dated first block and review criteria."))
    camp_path = c.season / "04_Training_Camp/camp_roster.json"
    camp = c.snapshot(camp_path, ("opened", "as_of"))
    p_rows = [p for p in camp.get("players", []) if p.get("player") == c.name]
    minutes = next((p.get("minutes") for p in rotation.get("players", [])
                    if p.get("player_id") in {c.name, c.identity.get("player_id")}), None)
    if camp:
        c.source(camp_path, "Recorded camp roster")
    if rotation:
        c.source(rotation_path, "Dated staff rotation")
    promises = c.snapshot(c.season / "04_Training_Camp/promise_log.json")
    promise_rows = [r for r in promises.get("promises", promises.get("players", [])) if r.get("player") == c.name]
    preseason = [r for r in c.records if r.get("competition") == "preseason"]
    camp_view = c.view("training_camp", "Training camp", "active" if camp else "inactive",
        "The club opens camp and records participation, evaluation or an actual role decision.",
        "Staff ordering is visible; camp attendance, minutes and grades require their own dated records.", [
            _table("Your camp position", ["Item", "Recorded position"], [
                ["Camp opened", camp.get("opened", "Not recorded")],
                ["Participation", _text(p_rows[0].get("status")) if p_rows else "No camp participation record"],
                ["Current role", role], ["Staff rotation minutes", minutes],
                ["Closed preseason games", len(preseason)],
                ["Camp availability", _text(p_rows[0].get("injured_through"), "No camp injury restriction recorded") if p_rows else "No camp assessment recorded"]]),
            _table("Current depth chart", ["Position", "Staff ordering", "Interpretation"], role_rows,
                   notice=f"Snapshot: {depth.get('as_of', 'not recorded')}. Draft rights and unassigned arrivals are not assigned minutes."),
            _table("Role and promise review", ["Item", "Evidence needed", "Current position"], [
                ["Expected role", "Attributed coach statement", role],
                ["Actual use", "Closed preseason boxes", f"{len(preseason)} closed games"],
                ["Promised minutes", "Written promise and date", _text(contract.get("promise"))],
                ["Promise review", "Dated review against rotation", _text(promise_rows)],
                ["Defensive evaluation", "Dated staff assessment", "Steals and blocks alone do not establish overall defense"]]),
            _table("Recorded camp discussion", ["Date", "Event / decision"], camp_phase["rows"]),
            {"title": "Your response to the staff", "items": [
                "Ask which assignment you are being evaluated for and which evidence matters.",
                "State the role you want and request a review of the actual sample.",
                "Report availability to qualified staff.",
                "The coach owns depth-chart position and rotation minutes; a request is not an assignment."]}],
        [c.action(c.season / "04_Training_Camp/Wade_Camp_Review.md", "Answer your camp review", "Respond to the actual staff review.") if c.known(camp.get("evaluated")) else None,
         c.action(camp_phase["path"], "Open camp events and discussion", "Inspect the dated camp record.")],
        "A verified camp-opening record, then actual preseason evidence and the coach's role review.")
    exit_path = c.season / "03_Offseason/exit_meeting.json"
    meeting = c.snapshot(exit_path)
    if meeting:
        c.source(exit_path, "Dated season exit meeting")
    exit_view = c.view("exit_meeting", "Season exit meeting", "active" if meeting else "inactive",
        "The player's season closes and a dated exit meeting is recorded.",
        "No completed NBA season is implied by a calendar container. The review starts from closed simulated games and actual staff discussion.", [
            _table("Meeting status", ["Item", "Recorded position"], [
                ["Meeting date", meeting.get("date", meeting.get("as_of", "Not recorded"))],
                ["Participants", _text(meeting.get("participants"))], ["Player's main goal", _text(meeting.get("goal"))],
                ["Season conclusion", _text(meeting.get("season_outcome"))],
                ["Staff observation", _text(meeting.get("staff_observation"))],
                ["Unresolved disagreement", _text(meeting.get("unresolved"))]]),
            _table("Basketball and contract discussion", ["Discussion", "Current evidence", "Needed before a conclusion"], [
                ["Strength and limiting possession", _text(meeting.get("basketball_review")), "Specific game or film references"],
                ["Communicated role and actual use", role, "Dated statements and closed minutes"],
                ["Availability and recovery", _text(c.identity.get("availability")), "Current qualified assessment"],
                ["Contract outlook", c.state.get("contract_status", "Not recorded"), "Actual terms, options and next verified gate"],
                ["Summer priorities", _text(meeting.get("priorities")), "Player selection and staff-supported plan"]]),
            _table("Follow-up ownership", ["Deliverable", "Owner", "Current response"], [
                ["Development block", "Player and development staff", _text(meeting.get("training_handoff"))],
                ["Role-evaluation criteria", "Coach", _text(meeting.get("role_handoff"))],
                ["Contract review", "Player and representative", _text(meeting.get("contract_handoff"))],
                ["Team-direction request", "Front office", _text(meeting.get("club_response"))]]),
            {"title": "Your response when the meeting opens", "items": [
                "Name the main basketball goal and two offseason priorities.",
                "Ask about a recorded promise, role change or unanswered request.",
                "Leave disagreements visible until someone actually answers.",
                "Agreement is not prefilled and priorities do not produce automatic improvement."]}],
        [c.action(exit_path if meeting else offseason["path"], "Open the owning offseason record",
                  "Use a dated meeting and closed-season evidence when the review occurs.")],
        _text(meeting.get("next_checkpoint"), "The actual season close and an agreed exit-meeting date."))
    return training_view, camp_view, exit_view


def build_milestone_payload(player: Path, identity: dict, records: list, *, root: Path | None = None) -> dict:
    """Build nine live views, preserving unknowns and omitting future evidence."""
    c = _Context(player, identity, records, root)
    c.source(c.season / "current_state.json", "Authoritative career checkpoint")
    c.source(c.player / "professional_identity.json", "Dated professional identity")
    c.source(c.player / identity.get("source_profile", "Dwyane_Wade_Player_Profile.md"), "Established player profile")
    phase_path = c.season / c.state.get("current_note", "note.md")
    c.source(phase_path, "Current owning event")
    checkpoint, negotiation, contract, draft_rights = _contract_views(c)
    requests = _request_rows(c)
    consultation_rows, consultation_actions = _consultations(c)
    training, camp, exit_view = _basketball_views(c, contract)
    pending = c.state.get("pending_player_decisions", [])
    calendar_rows = [[c.on, "Current checkpoint", c.state.get("last_closed_event", "Recorded current state"),
                      "Recorded", c.link(phase_path, "Owning event")]]
    if c.season.name == "2003-04" and c.on <= "2003-07-01":
        calendar_rows.extend([
            ["2003-06-30", "Option and qualifying-offer decisions", "Owner depends on the actual contract",
             "Scheduled gate; no outcome imported", c.link(c.root / "docs/front_office.md", "Workflow")],
            ["2003-07-01", "Free-agent negotiation window", "Miami's roster work; Wade's own status follows his control record",
             "Window does not create an offer", c.link(c.season / "01_Free_Agency/note.md", "Free-agency record")]])
    offer_date = next((r[1] for r in negotiation["sections"][0]["rows"] if r[0] == "Current proposal"), None)
    camp_date = next((r[1] for r in camp["sections"][0]["rows"] if r[0] == "Camp opened"), None)
    exit_date = next((r[1] for r in exit_view["sections"][0]["rows"] if r[0] == "Meeting date"), None)
    calendar_rows.extend([
        [offer_date if c.known(offer_date) else "Not yet recorded",
         "Rookie-contract proposal" if draft_rights else "Next contract review",
         "Player responds to an actual eligible proposal", negotiation["status"].replace("_", " "),
         {"label": "Contract desk", "href": "#contract_negotiation"}],
        [camp_date if c.known(camp_date) else "Not yet verified", "Camp reporting",
         "Club records the date", camp["status"].replace("_", " "),
         {"label": "Training camp", "href": "#training_camp"}],
        [exit_date if c.known(exit_date) else "After the actual final game", "Season exit meeting",
         "Player and staff review the closed season", exit_view["status"].replace("_", " "),
         {"label": "Exit meeting", "href": "#exit_meeting"}]])
    calendar = c.view("calendar", "Your career calendar", "awaiting_response" if pending or consultation_actions else "active",
        "The authoritative current date and recorded event determine what is open.",
        f"{c.name} is at {c.state.get('current_area', 'the current phase').replace('_', ' ')}. All milestone pages remain accessible; inactive pages explain their opening event.", [
            _table("What is happening now", ["Item", "Current record"], [
                ["Career date", c.on], ["Team", c.state.get("team")],
                ["Contract status", c.state.get("contract_status", "Not recorded")],
                ["Roster status", c.state.get("roster_status", "Not recorded")],
                ["Last closed event", c.state.get("last_closed_event", "Not recorded")],
                ["Pending player decisions", _text(pending, "None recorded")]]),
            _table("Milestone calendar", ["Date / gate", "Milestone", "Who acts", "Current meaning", "Open record"], calendar_rows),
            _table("Your recorded requests", ["Date", "Subject", "Player / target", "Request", "Explanation", "Source"], requests),
            _table("Franchise consultations", ["Asked", "Move", "Target", "Response", "Basis", "Source"], consultation_rows),
            {"title": "What opens the other pages", "items": [
                "Contract: an actual offer, option, signing or verified expiry event.",
                "Trade: a dated proposal or completed transaction; ordinary trades are club decisions.",
                "Training and camp: a player/staff plan or actual club evaluation.",
                "Stats: declared, closed game results, never future or historical Wade results.",
                "Exit meeting: the actual season close and a recorded meeting."]}],
        consultation_actions + [c.action(phase_path, "Open the current event",
            "Read the owning career note and record the player's actual response when one is due.")],
        "Answer the recorded consultation." if consultation_actions else
        "The next actual dated career event; viewing these pages does not advance time.")
    fa_phase = c.phase("01_Free_Agency")
    club_talks = []
    for path, row in c.files(c.season / "01_Free_Agency/Negotiations"):
        if row.get("player") == c.name:
            continue
        rounds = [r for r in row.get("rounds", []) if c.known(r.get("date"))]
        signing = row.get("signing") or {}
        club_talks.append([row.get("player"), row.get("opened"), len(rounds),
                          "Signed" if c.known(signing.get("date")) else "Dated negotiation; no signing confirmed",
                          c.link(path, "Negotiation source")])
    freeagency = c.view("free_agency", "Free agency", "inactive" if draft_rights else "needs_evidence",
        "A verified player market window or actual dated Miami roster-market event.",
        "Wade is not on the free-agent market while Miami holds his unsigned draft rights." if draft_rights else
        "Player eligibility requires actual contract, option and qualifying-offer records; team recruitment is separate.", [
            _table("Your market position", ["Item", "Current evidence"], [
                ["Control", c.state.get("contract_status", "Not recorded")],
                ["UFA / RFA", "Neither: unsigned draft rights" if draft_rights else "Not established by a calendar date alone"],
                ["Qualifying offer", "Not applicable to this unsigned draft checkpoint" if draft_rights else "Requires actual tender and rights evidence"],
                ["Outside written offers", "None established by the current player control record"],
                ["Market value", "Rookie scale governs the first contract" if draft_rights else "No verified estimate supplied to this live view"]]),
            _table("Your team-direction requests", ["Date", "Subject", "Target", "Request", "Explanation", "Source"], requests),
            _table("Miami's actual negotiation records", ["Player", "Opened", "Dated rounds", "Known position", "Source"], club_talks,
                   notice="These are Miami's roster negotiations, not offers to Wade."),
            _table("Recorded market events", ["Date", "Event / player discussion"], fa_phase["rows"]),
            _table("Decision authority", ["Item", "Who decides", "Player response"], [
                ["Targets, offers and roster construction", "AI/GM", "State a preference and ask for an answer"],
                ["Wade's actual eligible contract offer", "Wade", "Accept, counter or decline through the actual desk"],
                ["Adding another star at franchise standing", "Recorded consultation premise", "Answer the actual approve/object question"],
                ["RFA matching", "Incumbent under verified rules", "A valid offer sheet starts its binding workflow"]])],
        consultation_actions + [c.action(fa_phase["path"], "Open market events and your requests", "Review the actual dated roster-market discussion.")],
        "Miami's next recorded market action or an actual proposal in Wade's own contract desk.")
    trades, player_trades = [], []
    for path, row in c.files(c.team / "Transactions/Trades"):
        trade = row.get("trade", {})
        completed = row.get("status") == "completed" and c.known(row.get("applied"))
        answered = c.known((row.get("answer") or {}).get("date"))
        known_status = ("Completed" if completed else
                        row["status"].replace("_", " ").capitalize() if answered and row.get("status") in {"declined", "void"} else
                        "Proposal; completion not recorded by this date")
        if c.name in trade.get("miami_out", []) or c.name in trade.get("miami_in", []):
            player_trades.append(f"{row.get('date')}: {known_status.lower()} with {trade.get('partner', 'unrecorded partner')}")
        trades.append([row.get("date"), known_status,
                       trade.get("partner", "Not recorded"), _text(trade.get("miami_out"), "None listed"),
                       _text(trade.get("miami_in"), "None listed"), row.get("applied") if completed else "Not recorded",
                       _text(row.get("void_reason") or (row.get("answer") or {}).get("outcome")) if answered else "No dated answer recorded",
                       c.link(path, "Transaction record")])
    trade_view = c.view("trade_update", "Trade update", "active" if trades else "inactive",
        "An actual dated proposal, consultation or executed transaction.",
        "No trade update is recorded at this checkpoint." if not trades else "Proposals and completed transactions are distinguished below.", [
            _table("Actual transaction register", ["Proposed", "Known status", "Partner", "Miami sends", "Miami receives", "Applied", "Outcome / reason", "Source"], trades),
            _table("What this changes for you", ["Item", "Current evidence"], [
                ["Current club", c.state.get("team")], ["Trade involving Wade", _text(player_trades, "Not established by a transaction record")],
                ["Staff role after a move", _text(c.identity.get("role"))],
                ["Report / travel deadline", "No actual assignment notice supplied"],
                ["Physical or reporting requirements", "Use the dated notice; no timer invented"],
                ["Contract or guarantees", "Inspect executed transaction and contract records; no automatic rewrite"]]),
            _table("Consent and consultation", ["Decision", "Authority", "Availability"], [
                ["Ordinary club trade", "AI/GM and league process", "No universal player veto"],
                ["Actual contractual/CBA consent right", "Verified source and exact transaction", "Not assumed"],
                ["Franchise star-acquisition consultation", "Career premise", "Only an actual recorded question"],
                ["Player reaction or preference", "Player", "Request an explanation or role discussion"]]),
            _table("Recorded franchise consultations", ["Asked", "Move", "Target", "Response", "Basis", "Source"], consultation_rows),
            {"title": "Your response when an update arrives", "items": [
                "Ask what changed, which obligations carry over and whom to contact.",
                "State your view of the move or request a basketball discussion.",
                "Exercise only an independently verified applicable consent right.",
                "An ordinary trade is not paused for a fictional approve/reject button."]}],
        consultation_actions + [c.action(phase_path, "Open the current event discussion", "Record a dated reaction to an actual transaction.")],
        "An actual transaction update with its source and applicable player rights.")
    stats_rows, shooting_rows, game_rows = [], [], []
    competitions = sorted({r.get("competition") for r in c.records if r.get("competition")} | {"regular"})
    for competition in competitions:
        a = aggregate([r for r in c.records if r.get("competition") == competition])
        stats_rows.append([competition.replace("_", " "), a["gp"], a["pg"]["minutes"], a["pg"]["pts"],
                          a["pg"]["reb"], a["pg"]["ast"], a["pg"]["tov"], "Complete" if a["complete"] else "Missing source coverage"])
        shooting_rows.append([competition.replace("_", " "), a["totals"]["fgm"], a["totals"]["fga"],
                              a["rates"]["fg_pct"], a["totals"]["tpm"], a["totals"]["tpa"], a["rates"]["three_pct"]])
    for r in sorted(c.records, key=lambda r: (r["date"], r.get("event_id") or "")):
        game_rows.append([r["date"], _text(r.get("competition")), _text(r.get("opponent")), _text(r.get("appearance")),
                          c.link(r["note"], "Closed game") if r.get("note") else "No source link supplied"])
    stats = c.view("stats_review", "Stats review", "active" if c.records else "inactive",
        "A declared, closed game result supplies observed participation and the player box.",
        f"{len(c.records)} closed game records in {c.season.name} through {c.on}. Competitions remain separate.", [
            _table("Production by competition", ["Competition", "G", "MPG", "PPG", "RPG", "APG", "TOV/G", "Coverage"], stats_rows),
            _table("Pooled shooting", ["Competition", "FGM", "FGA", "FG ratio", "3PM", "3PA", "3P ratio"], shooting_rows,
                   notice="Ratios are pooled makes divided by attempts; missing and zero-attempt percentages are N/A."),
            _table("Closed source games", ["Date", "Competition", "Opponent", "Participation", "Source"], game_rows),
            _table("Evidence available for decisions", ["Question", "Required evidence", "Current treatment"], [
                ["Period production", "Closed simulated boxes", "Summed and divided by recorded appearances"],
                ["Shot locations", "Actual coordinates and outcomes", "Never invented from a box score"],
                ["Defense or role improvement", "Assignment, film and representative sample", "Box-score events alone do not settle it"],
                ["Training effects", "Dated plan and repeated comparable evidence", "No automatic ability gain"]]),
            {"title": "Your next useful question", "items": [
                "Choose a completed period and name the basketball question you want reviewed.",
                "Compare the same competition and keep sample size visible.",
                "Respond through training and role conversations; do not import historical Wade results."]}],
        [c.action(c.player / "Stats_and_Awards/README.md", "Open your complete statistics", "Follow season, month, week and source-game reports."),
         {"label": "Open shooting and player cards", "href": "../Stats_and_Awards/player_cards.html", "description": "The live card dashboard uses the same canonical source records."}],
        "The next declared, closed game result or a chosen completed-period review.")
    screens = {s["id"]: s for s in (calendar, checkpoint, negotiation, freeagency, training, trade_view, exit_view, camp, stats)}
    from .milestone_records import augment_live_screens
    augment_live_screens(c, screens)
    for screen in screens.values():
        screen["sources"] = list(c.sources.values())
    return {"schema_version": 1, "mode": "live", "as_of": c.on, "season": c.season.name,
            "identity": {"name": c.name, "team": c.state.get("team", c.identity.get("team")),
                         "position": " / ".join(c.identity.get("positions", [])), "age": c.identity.get("age"),
                         "contract_status": c.state.get("contract_status", "Not recorded")},
            "current_event": c.state.get("last_closed_event", "Not recorded"), "current_screen": "calendar",
            "screens": [screens[key] for key in SCREEN_IDS], "read_only": True, "execution_enabled": False,
            "rookie_scale_reference": c.scale_reference,
            "source_policy": "Canonical dated career records only. Reading a view creates no offer, decision, trade, workout result or future event."}


def _md_cell(value):
    if isinstance(value, dict) and "label" in value:
        label = str(value["label"]).replace("[", "\\[").replace("]", "\\]")
        href = value.get("href")
        if href and href.startswith("#"):
            href = "index.html" + href
        return f"[{label}]({href})" if href else label
    if isinstance(value, float):
        value = f"{value:.3f}" if 0 < value < 1 else f"{value:.1f}"
    return _text(value, "N/A").replace("|", "&#124;").replace("\n", " ")


def milestone_markdown(payload, screen):
    """Render the same detailed data without JavaScript or hidden sections."""
    text = GENERATED + f"\n# {screen['title']} | {payload['identity']['name']}\n\n"
    text += f"Career date: {payload['as_of']} · {payload['identity']['team']} · {screen['status'].replace('_', ' ')}\n\n"
    text += "[Live milestone desk](index.html#" + screen["id"] + ") · [All milestones](README.md)\n\n"
    text += screen["summary"] + "\n\nActivation: " + screen["trigger"] + "\n\n"
    for section in screen["sections"]:
        text += f"## {section['title']}\n\n"
        for key in ("description", "body", "notice"):
            if section.get(key):
                text += _text(section[key]) + "\n\n"
        if section.get("columns"):
            columns = section["columns"]
            text += "| " + " | ".join(columns) + " |\n| " + " | ".join("---" for _ in columns) + " |\n"
            for row in section.get("rows", []):
                text += "| " + " | ".join(_md_cell(value) for value in row) + " |\n"
            if not section.get("rows"):
                text += "| " + " | ".join(["No dated record"] + ["N/A"] * (len(columns) - 1)) + " |\n"
            text += "\n"
        if section.get("items"):
            text += "".join("- " + _text(item) + "\n" for item in section["items"]) + "\n"
    text += "## Available response paths\n\n"
    text += "".join(f"- [{a['label']}]({a['href']}): {a['description']}\n" for a in screen["actions"]) or "No player response is currently due.\n"
    text += "\n## Next checkpoint\n\n" + screen["next_checkpoint"] + "\n\n## Evidence\n\n"
    text += "".join(f"- [{s['label']}]({s['href']})\n" for s in screen["sources"])
    return text


def build_milestone_pages(player: Path, identity: dict, records: list, *, root: Path | None = None) -> dict[Path, str]:
    """Return artifacts for the normal report build; the caller persists them."""
    payload = build_milestone_payload(player, identity, records, root=root)
    folder = Path(player) / "Milestones"
    encoded = json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False)
    safe = encoded.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    template = TEMPLATE.read_text(encoding="utf-8")
    if template.count("__CAREER_MILESTONES_DATA__") != 1:
        raise ValueError("live milestone template requires exactly one data token")
    outputs = {folder / "index.html": template.replace("__CAREER_MILESTONES_DATA__", safe),
               folder / "data.json": encoded + "\n"}
    if payload["rookie_scale_reference"]:
        outputs[folder / "rookie_scale_reference.json"] = json.dumps(
            payload["rookie_scale_reference"], ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    index = GENERATED + f"\n# {payload['identity']['name']} | Live milestones\n\n"
    index += f"Career date: {payload['as_of']}. [Open the detailed milestone desk](index.html).\n\n"
    index += "These are current career views, with activation gates and actual evidence. An inactive view does not imply its event occurred.\n\n"
    index += "| Milestone | Status | Opens when |\n| --- | --- | --- |\n"
    for screen in payload["screens"]:
        outputs[folder / f"{screen['id']}.md"] = milestone_markdown(payload, screen)
        index += f"| [{screen['title']}]({screen['id']}.md) | {screen['status'].replace('_', ' ')} | {screen['trigger']} |\n"
    outputs[folder / "README.md"] = index
    return outputs
