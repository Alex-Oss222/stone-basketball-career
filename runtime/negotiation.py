"""Miami's negotiations on the contract desk (docs/front_office_design.md, sections 5.5 and 6).

One record per player under `01_Free_Agency/Negotiations/<slug>.json`: the desk
state (`runtime/contract_negotiation.py`, with every offer version), Miami's
plan entry for him, the player's drawn priorities, each round's offer, decision
and outcome, and the agreement when one is reached. Miami's offers are checked
against the 1999 rules (`cba.terms_errors`) before the desk accepts them; the
attestation records that check. The player's answers and a real incumbent's
match are engine draws (`*.decision.json` beside the record); applying a drawn
answer is the only way a round moves, and every desk event that follows a draw
cites the decision's event id.
"""
from dataclasses import asdict
from datetime import datetime, timedelta
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from . import contract_negotiation as desk
from .cba import rules as cba_rules, terms_errors
from .valuation import read

ROOT = Path(__file__).resolve().parents[1]
SEASON = "2003-04"
MIAMI = "Miami Heat"
FOLDER = Path(f"career/Dwyane_Wade/{SEASON}/01_Free_Agency/Negotiations")
CAP_RULES_PATH = Path("library/2003/league/nba_2003_04_cap_rules.json")
CBA_PATH = "library/2003/league/nba_1999_cba_rules.json"
RIGHTS_REF = "library/2003/league/nba_2003_free_agent_rights.json"
ISSUER = "miami_cap_adapter"
ZONE = ZoneInfo("America/New_York")
OFFER_DAYS = 3                      # an offer stays open this long
# Hours of a day on the desk, in order: an answer (9), a re-issue or acceptance (10, 11), an offer (12),
# a sheet signature and its receipt (13, 14, 15). Every event on one day keeps this order.
HOURS = {"answer": 9, "reissue": 10, "accept": 11, "offer": 12, "sheet_reissue": 13, "sheet": 14, "receipt": 15}
MATCH_DAYS = 15                     # 1999 rules: the incumbent's matching period after service of the sheet
MARKET_OPENS, SIGNING_OPENS, MARKET_CLOSES = "2003-07-01", "2003-07-16", "2004-06-30"
STATUSES = ("open", "agreed", "sheet_pending", "trade_pending", "signed", "matched", "ended")


def slug(name):
    return name.lower().replace("'", "").replace(".", "").replace(" ", "_")


def stamp(day, hour=12):
    return datetime.fromisoformat(day).replace(hour=hour, tzinfo=ZONE).isoformat()


def shift(day, days):
    return (datetime.fromisoformat(day) + timedelta(days=days)).date().isoformat()


def seasons(first, years):
    start = int(first[:4])
    return [f"{start + i}-{str(start + i + 1)[-2:]}" for i in range(years)]


def salary_schedule(terms, first_season=SEASON):
    rows = []
    for season, salary in zip(seasons(first_season, terms["years"]), terms["schedule"]):
        rows.append({"season": season, "salary": int(salary), "guaranteed": int(salary), "option": "none"})
    if not terms.get("last_year_guaranteed", True) and len(rows) > 1:
        rows[-1]["guaranteed"] = 0
    return rows


def attestation(action, payload, at, source_refs):
    return desk.Attestation(ISSUER, tuple(source_refs), at,
                            (datetime.fromisoformat(at) + timedelta(days=1)).isoformat(), action, desk.fingerprint(payload))


COUNTER_PREMIUM_LIMIT = 0.15    # most an agent adds to the money for a factor money cannot fix (judgement)


def counter_amount(offer_first_year, ask, premium=0.0):
    """The player's counter when the draw says he counters: the split between the offer and his ask,
    never below an 8% lift on the offer and never above the ask (judgement, deterministic given the draw).

    `premium` (0 to COUNTER_PREMIUM_LIMIT) is the agent's price for a weakness money cannot fix, such as a
    weaker club or a smaller role (runtime/player_utility.py, counter focus): it lifts both the counter and its cap."""
    premium = max(0.0, min(COUNTER_PREMIUM_LIMIT, premium))
    top = ask * (1 + premium)
    return int(round(min(top, max(offer_first_year * 1.08, (offer_first_year + ask) / 2 * (1 + premium)))))


class Negotiation:
    """Miami against one free agent. `record` is the JSON kept in the career folder."""

    def __init__(self, record, root=ROOT):
        self.record, self.root = record, Path(root)

    @classmethod
    def open(cls, player, bbr_id, club, on, plan_entry, restricted=False, root=ROOT):
        state = desk.start(player, club, stamp(on), trusted_issuers=(ISSUER,))
        record = {"player": player, "bbr_id": bbr_id, "incumbent": club, "restricted": bool(restricted), "opened": on,
                  "status": "open", "plan": plan_entry, "priorities": None, "rounds": [], "agreement": None,
                  "sheet": None, "signing": None, "ended": None, "trade": None, "state": serialize(state)}
        return cls(record, root)

    @classmethod
    def load(cls, path, root=ROOT):
        return cls(json.loads(Path(path).read_text(encoding="utf-8")), root)

    def path(self, folder=None):
        return Path(folder or self.root / FOLDER) / f"{slug(self.record['player'])}.json"

    def save(self, folder=None):
        path = self.path(folder)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        return path

    @property
    def state(self):
        return deserialize(self.record["state"])

    @property
    def status(self):
        return self.record["status"]

    def outside(self):
        return self.record["incumbent"] != MIAMI

    def round_number(self):
        return len(self.record["rounds"]) + 1

    def last_round(self):
        return self.record["rounds"][-1] if self.record["rounds"] else None

    # -- Miami's side ----------------------------------------------------------------------------
    def make_offer(self, terms, on, route, years_of_service, prior_salary):
        """Check legality, submit the offer on the desk, and open a round. Returns the round."""
        restricted = self.record["restricted"] and self.outside()
        cap_rules, cba = read(CAP_RULES_PATH, self.root), cba_rules(self.root)
        errors = terms_errors({"schedule": terms["schedule"], "guaranteed": terms["guaranteed"]}, route=route,
                              years_of_service=years_of_service, prior_salary=prior_salary, cap_rules=cap_rules,
                              cba=cba, restricted_offer_sheet=restricted)
        if errors:
            raise ValueError(f"illegal offer to {self.record['player']}: " + "; ".join(errors))
        state, at = self.state, stamp(on, HOURS["offer"])
        number = self.round_number()
        offer_id, version = f"MIA-{slug(self.record['player'])}-{number}", 1
        last = self.last_round()
        if last:
            previous = desk.latest_offer(state, last["offer_id"])
            if previous.status == "open" and at < previous.expires_at:
                offer_id, version = previous.offer_id, previous.version + 1     # Miami revises its live offer
        offer = desk.Offer(offer_id, version, MIAMI, desk.Terms.from_dict({"salary_schedule": salary_schedule(terms), "route": route,
                                                                           "promise": terms.get("promise")}),
                           at, stamp(shift(on, OFFER_DAYS)))
        refs = (str(CAP_RULES_PATH), CBA_PATH, f"career/Dwyane_Wade/{SEASON}/00_Team/Finances/contract_schedules.json")
        if state.phase == "incumbent_negotiation" and self.outside():
            market = desk.Market("RFA" if restricted else "UFA", "expired", stamp(MARKET_OPENS, 0), stamp(MARKET_CLOSES),
                                 stamp(SIGNING_OPENS, 0), stamp(MARKET_CLOSES), RIGHTS_REF)
            state = desk.open_market(state, desk.Actor("player", self.record["player"]), at, market,
                                     evidence=attestation("open_market", desk.market_payload(state, market), at, refs))
        state = desk.submit_offer(state, desk.Actor("club", MIAMI), at, offer, 1,
                                  evidence=attestation("club_offer", desk.offer_payload(state, offer, 1), at, refs))
        self.record["state"] = serialize(state)
        rnd = {"round": number, "date": on, "offer_id": offer_id, "version": version, "route": route, "terms": terms,
               "legality": {"checked_by": ISSUER, "rules": refs, "errors": []},
               "decision_event": None, "answer": None, "answered": None, "counter": None}
        self.record["rounds"].append(rnd)
        return rnd

    # -- the player's side (drawn) --------------------------------------------------------------
    def apply_answer(self, outcome, on, decision_ref, ask=None, premium=0.0):
        """Apply the engine's drawn answer to the latest round; `decision_ref` is the decision event id."""
        rnd = self.last_round()
        if rnd["answer"] is not None:
            raise ValueError("the round is already answered")
        rnd["answer"], rnd["answered"], rnd["decision_event"] = outcome, on, decision_ref
        state, at = self.state, stamp(on, HOURS["answer"])
        offer = desk.latest_offer(state, rnd["offer_id"])
        actor = desk.Actor("player", self.record["player"])
        if outcome == "accept":
            self.record["agreement"] = {"date": on, "terms": rnd["terms"], "route": rnd["route"], "offer_id": rnd["offer_id"],
                                        "decision_event": decision_ref, "basis": "agreement in principle; executed on the signing date"}
            self.record["status"] = "agreed"
            # The desk records the acceptance (or the signed sheet) on the signing date: execute_agreement / sign_sheet.
        elif outcome == "counter":
            rnd["counter"] = counter_amount(rnd["terms"]["first_year"], ask or rnd["terms"]["first_year"], premium)
            raise_share = rnd["terms"]["raise_percent"] / 100
            schedule = [int(round(rnd["counter"] * (1 + raise_share * i))) for i in range(rnd["terms"]["years"])]
            terms = desk.Terms.from_dict({"salary_schedule": salary_schedule(dict(rnd["terms"], schedule=schedule, last_year_guaranteed=True))})
            state = desk.request_counter(state, actor, at, rnd["offer_id"], offer.version, terms, decision_ref=decision_ref)
        elif outcome == "reject":
            state = desk.reject_offer(state, actor, at, rnd["offer_id"], offer.version, decision_ref=decision_ref)
        else:
            raise ValueError(f"unknown answer {outcome!r}")
        self.record["state"] = serialize(state)
        return rnd

    def _live_agreed_offer(self, state, on, hour):
        """The agreed offer, re-issued on the desk with the same terms when the agreement outlived its validity."""
        rnd = self.last_round()
        at = stamp(on, hour)
        offer = desk.latest_offer(state, rnd["offer_id"])
        if offer.status != "open" or at >= offer.expires_at:
            self.record["rounds"].append(dict(rnd, round=self.round_number(), date=on, answer="accept", answered=on, counter=None,
                                              offer_id=f"MIA-{slug(self.record['player'])}-{self.round_number()}",
                                              legality=dict(rnd["legality"], note="re-issued agreed terms on the signing date")))
            rnd = self.last_round()
            offer = desk.Offer(rnd["offer_id"], 1, MIAMI, offer.terms, at, stamp(shift(on, OFFER_DAYS)))
            state = desk.submit_offer(state, desk.Actor("club", MIAMI), at, offer, 1,
                                      evidence=attestation("club_offer", desk.offer_payload(state, offer, 1), at, (str(CAP_RULES_PATH), CBA_PATH)))
        return state, rnd, offer

    def execute_agreement(self, on):
        """An agreed unrestricted free agent (or Miami's own) accepts on the desk on the signing date."""
        if self.record["status"] not in ("agreed", "trade_pending") or (self.record["restricted"] and self.outside()):
            raise ValueError("execute_agreement is for an agreed player who is not another club's restricted free agent")
        state, rnd, offer = self._live_agreed_offer(self.state, on, HOURS["reissue"])
        at = stamp(on, HOURS["accept"])
        payload = desk.selection_payload(state, rnd["offer_id"], offer.version)
        state = desk.accept_offer(state, desk.Actor("player", self.record["player"]), at, rnd["offer_id"], offer.version,
                                  evidence=attestation("agreement", payload, at, (rnd["decision_event"],)))
        self.record["state"] = serialize(state)
        self.record["agreement"]["executed"] = on
        return rnd

    def sign_sheet(self, on):
        """An agreed RFA signs Miami's offer sheet on the signing date; the incumbent's clock starts."""
        if self.record["status"] != "agreed" or not (self.record["restricted"] and self.outside()):
            raise ValueError("only an agreed restricted free agent of another club signs a sheet")
        state, rnd, offer = self._live_agreed_offer(self.state, on, HOURS["sheet_reissue"])
        at = stamp(on, HOURS["sheet"])
        actor = desk.Actor("player", self.record["player"])
        payload = desk.selection_payload(state, rnd["offer_id"], offer.version)
        state = desk.sign_offer_sheet(state, actor, at, rnd["offer_id"], offer.version,
                                      evidence=attestation("sign_offer_sheet", payload, at, (rnd["decision_event"],)))
        received, deadline = stamp(on, HOURS["receipt"]), stamp(shift(on, MATCH_DAYS), HOURS["receipt"])
        rule_ref = f"{CBA_PATH}#restricted_free_agency.match_window_days"
        payload = desk.receipt_payload(state, received, deadline, "America/New_York", rule_ref)
        state = desk.record_receipt(state, desk.Actor("authority", ISSUER), received, received, deadline, "America/New_York",
                                    rule_ref, evidence=attestation("record_receipt", payload, received, (rule_ref,)))
        self.record["state"] = serialize(state)
        self.record["status"] = "sheet_pending"
        self.record["sheet"] = {"signed": on, "deadline": shift(on, MATCH_DAYS), "offer_id": rnd["offer_id"], "resolution": None}
        return self.record["sheet"]

    def resolve_sheet(self, outcome, on, decision_ref):
        """The incumbent's drawn answer to the sheet (matched, match_declined), or deadline_elapsed by the authority."""
        if self.record["status"] != "sheet_pending":
            raise ValueError("no sheet is pending")
        state, at = self.state, stamp(on, HOURS["accept"])
        actor = desk.Actor("authority", ISSUER) if outcome == "deadline_elapsed" else desk.Actor("club", self.record["incumbent"])
        state = desk.resolve_sheet(state, actor, at, outcome,
                                   evidence=attestation(outcome, desk.resolution_payload(state, outcome), at, (decision_ref,)))
        self.record["state"] = serialize(state)
        self.record["sheet"]["resolution"] = {"outcome": outcome, "date": on, "decision_event": decision_ref}
        self.record["status"] = "matched" if outcome == "matched" else "agreed"
        return self.record["sheet"]

    def mark_signed(self, on, contract_ref):
        self.record["status"] = "signed"
        self.record["signing"] = {"date": on, "record": contract_ref}

    def end(self, reason, on):
        self.record["status"] = "ended"
        self.record["ended"] = {"date": on, "reason": reason}


def serialize(state):
    return json.loads(json.dumps(asdict(state), default=str))


def deserialize(data):
    def terms(t):
        return desk.Terms(t["encoded"])
    offers = tuple(desk.Offer(o["offer_id"], o["version"], o["team"], terms(o["terms"]), o["issued_at"], o["expires_at"], o["status"])
                   for o in data["offers"])
    requests = tuple(desk.CounterRequest(r["offer_id"], r["version"], terms(r["terms"]), r["requested_at"], r["decision_ref"])
                     for r in data["requests"])
    market = desk.Market(**data["market"]) if data.get("market") else None
    sheet = desk.Sheet(**dict(data["sheet"], terms=terms(data["sheet"]["terms"]))) if data.get("sheet") else None
    resolution = desk.Resolution(**dict(data["resolution"], terms=terms(data["resolution"]["terms"]))) if data.get("resolution") else None
    events = tuple(desk.Event(e["action"], desk.Actor(**e["actor"]), e["at"], tuple(e["source_refs"]), e["subject_digest"],
                              desk.Attestation(**dict(e["attestation"], source_refs=tuple(e["attestation"]["source_refs"]))) if e.get("attestation") else None)
                   for e in data["events"])
    return desk.Negotiation(data["player"], data["incumbent"], tuple(data["trusted_issuers"]), data["last_at"], data["cba"],
                            data["phase"], market, offers, tuple(data["slots"]), requests, sheet, resolution, events)


def negotiation_errors(root=ROOT):
    """Every negotiation record must replay on the desk and keep its rounds consistent with the desk events."""
    errors = []
    for path in sorted((Path(root) / "career").glob("*/*/01_Free_Agency/Negotiations/*.json")):
        if path.name.endswith(".decision.json") or path.name.endswith(".result.json"):
            continue                      # decision requests and results live beside the records
        rel = path.relative_to(root)
        try:
            n = Negotiation.load(path, root)
            state = n.state
            if n.record["status"] not in STATUSES:
                errors.append(f"{rel}: unknown status {n.record['status']!r}")
            if n.path().name != path.name:
                errors.append(f"{rel}: file name must be the player's slug")
            for rnd in n.record["rounds"]:
                desk.latest_offer(state, rnd["offer_id"])
                if rnd["answer"] is not None and not rnd.get("decision_event"):
                    errors.append(f"{rel}: round {rnd['round']} answered without a decision event")
            if n.record["status"] in ("signed", "agreed", "sheet_pending", "matched", "trade_pending") and not n.record.get("agreement"):
                errors.append(f"{rel}: status {n.record['status']} needs an agreement")
            if n.record["status"] == "signed" and state.phase not in ("execution_pending", "binding_resolution_pending_registration"):
                errors.append(f"{rel}: signed without a desk agreement or resolution")
            trade = n.record.get("trade")
            if n.record["status"] == "trade_pending" and not trade:
                errors.append(f"{rel}: trade_pending needs the trade reference")
            route = (n.record.get("agreement") or {}).get("route")
            if n.record["status"] == "signed" and (route == "sign_and_trade" or trade):
                record_path = Path(root) / f"career/Dwyane_Wade/{SEASON}/00_Team/Transactions/Trades/{(trade or {}).get('trade_id')}.json"
                if not trade or not record_path.exists():
                    errors.append(f"{rel}: a sign-and-trade signing needs its trade record")
                else:
                    tr = json.loads(record_path.read_text(encoding="utf-8"))
                    back = tr.get("negotiation") == str(rel).replace("\\", "/")
                    if route == "sign_and_trade" and tr.get("status") != "completed":
                        errors.append(f"{rel}: a sign-and-trade acquisition needs a completed trade record")
                    if not back:
                        errors.append(f"{rel}: the trade record {trade.get('trade_id')} does not point back to this negotiation")
        except Exception as exc:  # a corrupt record is a validation failure, not a crash
            errors.append(f"{rel}: {exc}")
    return errors
