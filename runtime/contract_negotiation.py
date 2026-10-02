"""Pure, evidence-gated negotiation workflow for the 1999 CBA era.

This module does not generate offers, verify legal source documents, authenticate
callers, advance the career clock, or execute contracts. The trusted application
adapter must do those jobs. It returns immutable snapshots and an audit trail.
"""
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta
from hashlib import sha256
import json
import re
from zoneinfo import ZoneInfo


class NegotiationError(ValueError):
    pass


def _require(condition, message):
    if not condition:
        raise NegotiationError(message)


def _time(value):
    try:
        result = datetime.fromisoformat(value)
        _require(result.tzinfo is not None and result.utcoffset() is not None,
                 "timestamp must include an explicit UTC offset")
        return result
    except (TypeError, ValueError) as exc:
        raise NegotiationError(f"invalid timestamp: {value!r}") from exc


def fingerprint(payload):
    """Bind an external attestation to the exact JSON input it reviewed."""
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"),
                             allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class Terms:
    """An immutable principal-terms snapshot; .data returns an independent copy."""
    encoded: str

    @classmethod
    def from_dict(cls, data):
        _require(isinstance(data, dict), "principal terms must be an object")
        result = cls(json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False))
        result.validate()
        return result

    @property
    def data(self):
        return json.loads(self.encoded)

    @property
    def digest(self):
        return fingerprint(self.data)

    def validate(self):
        data = self.data
        _require(isinstance(data, dict), "principal terms must be an object")
        schedule = data.get("salary_schedule")
        _require(isinstance(schedule, list) and schedule, "salary_schedule is required")
        previous = None
        for index, row in enumerate(schedule):
            _require(isinstance(row, dict), "salary row must be an object")
            season = row.get("season", "")
            _require(isinstance(season, str) and re.fullmatch(r"\d{4}-\d{2}", season),
                     "season must use YYYY-YY")
            start = int(season[:4])
            _require(season[-2:] == f"{(start + 1) % 100:02d}" and
                     (previous is None or start == previous + 1), "seasons must be consecutive")
            previous = start
            salary, guaranteed = row.get("salary"), row.get("guaranteed")
            _require(type(salary) is int and salary > 0, "salary must be positive integer dollars")
            _require(type(guaranteed) is int and 0 <= guaranteed <= salary,
                     "guaranteed salary must be an integer between zero and salary")
            option = row.get("option", "none")
            _require(option in {"none", "team", "player"}, "unknown option type")
            _require(option == "none" or index == len(schedule) - 1,
                     "only the last scheduled season may be an option")


@dataclass(frozen=True)
class Actor:
    kind: str  # player, club, authority
    identity: str


@dataclass(frozen=True)
class Attestation:
    """External verification, not a self-issued claim that the engine verified law.

    The adapter authenticates issuer and resolves sources before constructing this.
    scope and subject_digest must bind the complete payload of the transition.
    """
    issuer: str
    source_refs: tuple[str, ...]
    verified_at: str
    valid_until: str
    scope: str
    subject_digest: str


@dataclass(frozen=True)
class Market:
    status: str  # UFA or RFA, externally established, not merely RFA-eligible
    contract_state: str  # expired or released; waiver clearance is externally checked
    negotiation_opens: str
    negotiation_closes: str  # exclusive
    signing_opens: str
    signing_closes: str  # exclusive
    rights_ref: str  # includes qualifying-offer/rights verification for an RFA


@dataclass(frozen=True)
class Offer:
    offer_id: str
    version: int
    team: str
    terms: Terms
    issued_at: str
    expires_at: str  # exclusive, as documented by the issuer
    status: str = "open"


@dataclass(frozen=True)
class CounterRequest:
    offer_id: str
    version: int
    terms: Terms
    requested_at: str
    decision_ref: str


@dataclass(frozen=True)
class Sheet:
    offer_id: str
    version: int
    team: str
    terms: Terms
    signed_at: str
    signature_ref: str
    received_at: str | None = None
    deadline: str | None = None
    deadline_timezone: str | None = None
    deadline_rule_ref: str | None = None
    deadline_calendar_adjustment_ref: str | None = None


@dataclass(frozen=True)
class Resolution:
    outcome: str  # matched, match_declined, deadline_elapsed, agreement
    team: str
    offer_id: str
    version: int
    terms: Terms
    resolved_at: str
    slot: int | None  # exactly 5 for a match; never a competing club bid


@dataclass(frozen=True)
class Event:
    action: str
    actor: Actor
    at: str
    source_refs: tuple[str, ...]
    subject_digest: str
    attestation: Attestation | None = None


@dataclass(frozen=True)
class Negotiation:
    player: str
    incumbent: str
    trusted_issuers: tuple[str, ...]
    last_at: str
    cba: str = "1999"
    phase: str = "incumbent_negotiation"
    market: Market | None = None
    offers: tuple[Offer, ...] = ()
    slots: tuple[str | None, ...] = (None, None, None, None)
    requests: tuple[CounterRequest, ...] = ()
    sheet: Sheet | None = None
    resolution: Resolution | None = None
    events: tuple[Event, ...] = ()


def start(player, incumbent, at, *, trusted_issuers, cba="1999"):
    _time(at)
    _require(player and incumbent and trusted_issuers, "identity and trusted issuers are required")
    _require(cba == "1999", "only the researched 1999 CBA workflow is supported")
    return Negotiation(player, incumbent, tuple(trusted_issuers), at, cba)


def _actor(actor, kind, identity):
    _require(actor == Actor(kind, identity), f"action requires {kind} {identity}")


def _at(state, at):
    _require(_time(at) >= _time(state.last_at), "events cannot go backwards")


def _evidence(state, evidence, scope, payload, at):
    _require(isinstance(evidence, Attestation), "external verification is required")
    _require(evidence.issuer in state.trusted_issuers, "untrusted verification issuer")
    _require(type(evidence.source_refs) is tuple and evidence.source_refs and
             all(isinstance(ref, str) and ref.strip() for ref in evidence.source_refs),
             "verification needs immutable source references")
    _require(evidence.scope == scope and evidence.subject_digest == fingerprint(payload),
             "verification does not cover these exact inputs")
    _require(_time(evidence.verified_at) <= _time(at) < _time(evidence.valid_until),
             "verification is unavailable or expired at this event")


def _finish(state, actor, at, action, payload, *, evidence=None, decision_ref=None, **changes):
    _at(state, at)
    if evidence is not None:
        _evidence(state, evidence, action, payload, at)
        refs = evidence.source_refs
    else:
        _require(isinstance(decision_ref, str) and decision_ref.strip(), "dated decision reference required")
        refs = (decision_ref,)
    event = Event(action, actor, at, refs, fingerprint(payload), evidence)
    return replace(state, last_at=at, events=state.events + (event,), **changes)


def _negotiable(state, at):
    _at(state, at)
    _require(state.phase in {"incumbent_negotiation", "market"}, "negotiations are locked")
    if state.market:
        _require(_time(state.market.negotiation_opens) <= _time(at) <
                 _time(state.market.negotiation_closes), "negotiation window is closed")


def latest_offer(state, offer_id):
    versions = [offer for offer in state.offers if offer.offer_id == offer_id]
    _require(bool(versions), "unknown offer")
    return versions[-1]


def _live_offer(state, offer_id, version, at):
    _at(state, at)
    offer = latest_offer(state, offer_id)
    _require(offer.version == version, "stale offer version")
    _require(offer.status == "open" and _time(at) < _time(offer.expires_at), "offer is not live")
    return offer


def _status(state, offer, status):
    return tuple(replace(row, status=status) if row == offer else row for row in state.offers)


def _close_others(state, selected, selected_status):
    return tuple(replace(row, status=selected_status if row == selected else "closed")
                 if row.status in {"open", "signed_sheet"} else row for row in state.offers)


def offer_payload(state, offer, slot):
    return {"player": state.player, "incumbent": state.incumbent, "cba": state.cba,
            "offer": asdict(offer), "slot": slot}


def submit_offer(state, actor, at, offer, slot, *, evidence):
    """Only an issuing club can submit/revise an externally legal offer."""
    _negotiable(state, at)
    _actor(actor, "club", offer.team)
    _require(offer.team == state.incumbent or state.phase == "market", "outside market is not open")
    _require(type(slot) is int and 1 <= slot <= 4, "ordinary offers use slots 1 through 4")
    _require(offer.offer_id and type(offer.version) is int and offer.version > 0, "invalid offer identity")
    _require(offer.status == "open" and _time(offer.issued_at) == _time(at) and
             _time(offer.expires_at) > _time(at), "invalid issue or expiry time")
    offer.terms.validate()
    previous = [row for row in state.offers if row.offer_id == offer.offer_id]
    offers = state.offers
    if previous:
        old = _live_offer(state, offer.offer_id, offer.version - 1, at)
        _require(old.team == offer.team and state.slots[slot - 1] == offer.offer_id,
                 "revision must keep its issuing team and comparison slot")
        offers = _status(state, old, "superseded")
    else:
        _require(offer.version == 1, "new offers begin at version 1")
        occupied = state.slots[slot - 1]
        if occupied:
            old = latest_offer(state, occupied)
            _require(old.status != "open" or _time(at) >= _time(old.expires_at),
                     "comparison slot is occupied by a live offer")
            if old.status == "open":
                offers = _status(state, old, "expired")
    _require(not any(row.status == "open" and row.team == offer.team and
                     row.offer_id != offer.offer_id and _time(at) < _time(row.expires_at)
                     for row in offers), "a club already has a live offer")
    slots = list(state.slots)
    slots[slot - 1] = offer.offer_id
    return _finish(state, actor, at, "club_offer", offer_payload(state, offer, slot),
                   evidence=evidence, offers=offers + (offer,), slots=tuple(slots))


def reject_offer(state, actor, at, offer_id, version, *, decision_ref):
    _negotiable(state, at)
    _actor(actor, "player", state.player)
    offer = _live_offer(state, offer_id, version, at)
    return _finish(state, actor, at, "reject_offer", {"offer_id": offer_id, "version": version},
                   decision_ref=decision_ref, offers=_status(state, offer, "rejected"))


def withdraw_offer(state, actor, at, offer_id, version, *, decision_ref):
    _negotiable(state, at)
    offer = _live_offer(state, offer_id, version, at)
    _actor(actor, "club", offer.team)
    return _finish(state, actor, at, "withdraw_offer", {"offer_id": offer_id, "version": version},
                   decision_ref=decision_ref, offers=_status(state, offer, "withdrawn"))


def request_counter(state, actor, at, offer_id, version, terms, *, decision_ref):
    """A player proposal never overwrites the club's actual offer."""
    _negotiable(state, at)
    _actor(actor, "player", state.player)
    _live_offer(state, offer_id, version, at)
    terms.validate()
    request = CounterRequest(offer_id, version, terms, at, decision_ref)
    return _finish(state, actor, at, "counter_request", asdict(request), decision_ref=decision_ref,
                   requests=state.requests + (request,))


def market_payload(state, market):
    return {"player": state.player, "incumbent": state.incumbent, "cba": state.cba,
            "market": asdict(market)}


def open_market(state, actor, at, market, *, evidence):
    _negotiable(state, at)
    _actor(actor, "player", state.player)
    _require(state.market is None, "market eligibility is already recorded")
    _require(market.status in {"UFA", "RFA"} and market.contract_state in {"expired", "released"},
             "verified free-agent status and an expired/released contract are required")
    _require(bool(market.rights_ref), "rights verification reference required")
    _require(_time(market.negotiation_opens) <= _time(at) < _time(market.negotiation_closes),
             "negotiation window is closed")
    _require(_time(market.negotiation_opens) <= _time(market.signing_opens) <
             _time(market.signing_closes) <= _time(market.negotiation_closes), "invalid signing window")
    return _finish(state, actor, at, "open_market", market_payload(state, market),
                   evidence=evidence, market=market, phase="market")


def selection_payload(state, offer_id, version):
    offer = latest_offer(state, offer_id)
    _require(offer.version == version, "stale offer version")
    return {"player": state.player, "incumbent": state.incumbent, "cba": state.cba,
            "offer": asdict(offer)}


def _select(state, actor, at, offer_id, version):
    _negotiable(state, at)
    _actor(actor, "player", state.player)
    offer = _live_offer(state, offer_id, version, at)
    if state.market:
        _require(_time(state.market.signing_opens) <= _time(at) < _time(state.market.signing_closes),
                 "signing window is closed")
    return offer


def accept_offer(state, actor, at, offer_id, version, *, evidence):
    """Record an agreement and execution handoff, never a cap/roster transaction."""
    offer = _select(state, actor, at, offer_id, version)
    _require(not (state.market and state.market.status == "RFA" and offer.team != state.incumbent),
             "an RFA outside offer must use the signed offer-sheet workflow")
    result = Resolution("agreement", offer.team, offer_id, version, offer.terms, at, None)
    return _finish(state, actor, at, "agreement", selection_payload(state, offer_id, version),
                   evidence=evidence, phase="execution_pending", resolution=result,
                   offers=_close_others(state, offer, "accepted"))


def sign_offer_sheet(state, actor, at, offer_id, version, *, evidence):
    offer = _select(state, actor, at, offer_id, version)
    _require(state.market is not None and state.market.status == "RFA" and
             offer.team != state.incumbent, "outside RFA offer sheet required")
    non_option = [row for row in offer.terms.data["salary_schedule"] if row.get("option", "none") == "none"]
    _require(len(non_option) >= 3, "1999 offer sheets require at least 3 seasons excluding an option year")
    sheet = Sheet(offer_id, version, offer.team, offer.terms, at, evidence.source_refs[0]
                  if isinstance(evidence, Attestation) and evidence.source_refs else "")
    return _finish(state, actor, at, "sign_offer_sheet", selection_payload(state, offer_id, version),
                   evidence=evidence, phase="sheet_pending", sheet=sheet,
                   offers=_close_others(state, offer, "signed_sheet"))


def receipt_payload(state, received_at, deadline, deadline_timezone, deadline_rule_ref,
                    deadline_calendar_adjustment_ref=None):
    return {"player": state.player, "incumbent": state.incumbent, "sheet": asdict(state.sheet),
            "received_at": received_at, "deadline": deadline, "deadline_timezone": deadline_timezone,
            "deadline_rule_ref": deadline_rule_ref,
            "deadline_calendar_adjustment_ref": deadline_calendar_adjustment_ref}


def record_receipt(state, actor, at, received_at, deadline, deadline_timezone, deadline_rule_ref, *,
                   evidence, deadline_calendar_adjustment_ref=None):
    """Record externally verified service and exact deadline; never guess its time of day."""
    _require(state.phase == "sheet_pending" and state.sheet is not None and
             state.sheet.received_at is None, "receipt requires an unserved signed sheet")
    _require(actor.kind == "authority" and actor.identity in state.trusted_issuers,
             "receipt requires a trusted authority")
    received, due = _time(received_at), _time(deadline)
    _require(_time(state.sheet.signed_at) <= received <= _time(at) and due > received,
             "invalid receipt/deadline ordering")
    try:
        zone = ZoneInfo(deadline_timezone)
    except (KeyError, ValueError, TypeError) as exc:
        raise NegotiationError("explicit IANA deadline timezone required") from exc
    _require(received.utcoffset() == received.astimezone(zone).utcoffset() and
             due.utcoffset() == due.astimezone(zone).utcoffset(), "timestamps must use the deadline timezone")
    unadjusted = received.astimezone(zone).date() + timedelta(days=15)
    supplied_date = due.astimezone(zone).date()
    _require(supplied_date >= unadjusted and (supplied_date == unadjusted or
             (isinstance(deadline_calendar_adjustment_ref, str) and
              deadline_calendar_adjustment_ref.strip())),
             "1999 15-day period needs separate evidence for a calendar-adjusted deadline")
    _require(isinstance(deadline_rule_ref, str) and deadline_rule_ref.strip(), "deadline source required")
    sheet = replace(state.sheet, received_at=received_at, deadline=deadline,
                    deadline_timezone=deadline_timezone, deadline_rule_ref=deadline_rule_ref,
                    deadline_calendar_adjustment_ref=deadline_calendar_adjustment_ref)
    return _finish(state, actor, at, "record_receipt",
                   receipt_payload(state, received_at, deadline, deadline_timezone, deadline_rule_ref,
                                   deadline_calendar_adjustment_ref),
                   evidence=evidence, sheet=sheet)


def resolution_payload(state, outcome):
    return {"player": state.player, "incumbent": state.incumbent,
            "sheet": asdict(state.sheet) if state.sheet else None, "outcome": outcome}


def resolve_sheet(state, actor, at, outcome, *, evidence):
    """An incumbent match copies the signed principal terms into reserved slot 5."""
    _at(state, at)
    _require(state.phase == "sheet_pending" and state.sheet is not None and
             state.sheet.deadline is not None, "a served RFA offer sheet is required")
    _require(outcome in {"matched", "match_declined", "deadline_elapsed"}, "unknown matching resolution")
    sheet = state.sheet
    if outcome == "deadline_elapsed":
        _require(actor.kind == "authority" and actor.identity in state.trusted_issuers,
                 "elapsed deadline requires a trusted authority")
        _require(_time(at) > _time(sheet.deadline), "matching deadline has not elapsed")
    else:
        _actor(actor, "club", state.incumbent)
        _require(_time(at) <= _time(sheet.deadline), "matching deadline has elapsed")
    result = Resolution(outcome, state.incumbent if outcome == "matched" else sheet.team,
                        sheet.offer_id, sheet.version, sheet.terms, at, 5 if outcome == "matched" else None)
    source = latest_offer(state, sheet.offer_id)
    return _finish(state, actor, at, outcome, resolution_payload(state, outcome), evidence=evidence,
                   resolution=result, phase="binding_resolution_pending_registration",
                   offers=_status(state, source, "matched" if outcome == "matched" else "accepted"))


def comparison_slots(state, at):
    """Exactly four ordinary cards plus the optional fifth matching resolution.

    Expiry is a derived view status. Viewing never modifies the event journal.
    """
    _at(state, at)
    cards = []
    for offer_id in state.slots:
        offer = latest_offer(state, offer_id) if offer_id else None
        if offer and offer.status == "open" and _time(at) >= _time(offer.expires_at):
            offer = replace(offer, status="expired")
        cards.append(offer)
    cards.append(state.resolution if state.resolution and state.resolution.slot == 5 else None)
    return tuple(cards)
