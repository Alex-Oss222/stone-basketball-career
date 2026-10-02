"""Synthetic workflow fixtures, never canonical career offers or transactions."""
from dataclasses import FrozenInstanceError, replace
import unittest

from runtime.contract_negotiation import (
    Actor, Attestation, Market, NegotiationError, Offer, Terms, accept_offer,
    comparison_slots, fingerprint, latest_offer, market_payload, offer_payload,
    open_market, receipt_payload, record_receipt, reject_offer, request_counter,
    resolution_payload, resolve_sheet, selection_payload, sign_offer_sheet, start,
    submit_offer, withdraw_offer,
)


AT = "2003-07-16T12:00:00-04:00"
LATER = "2003-07-17T12:00:00-04:00"
EXPIRES = "2003-07-20T12:00:00-04:00"
DEADLINE = "2003-07-31T23:59:59-04:00"
PLAYER = Actor("player", "test-player")
HOME = Actor("club", "HOME")
AWAY = Actor("club", "AWAY")
AUTHORITY = Actor("authority", "test-verifier")


def terms(years=3, option=False, salary=1000000):
    return Terms.from_dict({
        "salary_schedule": [
            {"season": f"{2003 + i}-{(2004 + i) % 100:02d}", "salary": salary,
             "guaranteed": salary, "option": "player" if option and i == years - 1 else "none"}
            for i in range(years)],
        "payment_schedule": "externally reviewed schedule",
        "principal_incentives": [],
    })


def evidence(action, payload, **changes):
    fields = dict(issuer="test-verifier", source_refs=("test:legal-record", "test:decision-record"),
                  verified_at=AT, valid_until="2003-09-01T00:00:00-04:00",
                  scope=action, subject_digest=fingerprint(payload))
    fields.update(changes)
    return Attestation(**fields)


def initial():
    return start(PLAYER.identity, HOME.identity, AT, trusted_issuers=(AUTHORITY.identity,))


def market_state(status="RFA", **changes):
    state = initial()
    market = replace(Market(status, "expired", "2003-07-01T00:00:00-04:00",
                           "2003-08-31T00:00:00-04:00", "2003-07-16T00:00:00-04:00",
                           "2003-08-31T00:00:00-04:00", "test:verified-rights"), **changes)
    return open_market(state, PLAYER, AT, market,
                       evidence=evidence("open_market", market_payload(state, market)))


def offered(state=None, club=AWAY, offer_id="outside", slot=1, version=1, value=None, at=AT):
    state = market_state() if state is None else state
    offer = Offer(offer_id, version, club.identity, value or terms(), at, EXPIRES)
    return submit_offer(state, club, at, offer, slot,
                        evidence=evidence("club_offer", offer_payload(state, offer, slot)))


def signed(state=None):
    state = offered() if state is None else state
    return sign_offer_sheet(state, PLAYER, AT, "outside", 1,
                            evidence=evidence("sign_offer_sheet", selection_payload(state, "outside", 1)))


def served(state=None, deadline=DEADLINE, **changes):
    state = signed() if state is None else state
    payload = receipt_payload(state, AT, deadline, "America/New_York", "test:1999-XI-6-and-9", **changes)
    return record_receipt(state, AUTHORITY, AT, AT, deadline, "America/New_York",
                          "test:1999-XI-6-and-9", evidence=evidence("record_receipt", payload), **changes)


def resolved(state=None, outcome="matched", at=LATER, actor=HOME):
    state = served() if state is None else state
    return resolve_sheet(state, actor, at, outcome,
                         evidence=evidence(outcome, resolution_payload(state, outcome)))


class ContractNegotiationTests(unittest.TestCase):
    def test_rejection_never_establishes_free_agency(self):
        state = offered(initial(), HOME, "home")
        declined = reject_offer(state, PLAYER, AT, "home", 1, decision_ref="test:player-rejects")
        self.assertEqual(declined.phase, "incumbent_negotiation")
        self.assertIsNone(declined.market)
        self.assertEqual(latest_offer(state, "home").status, "open")
        self.assertEqual(latest_offer(declined, "home").status, "rejected")
        with self.assertRaisesRegex(NegotiationError, "market is not open"):
            offered(declined)

    def test_rejected_incumbent_can_be_followed_by_verified_market(self):
        state = reject_offer(offered(initial(), HOME, "home"), PLAYER, AT, "home", 1,
                             decision_ref="test:reject")
        market = market_state("UFA").market
        state = open_market(state, PLAYER, AT, market,
                            evidence=evidence("open_market", market_payload(state, market)))
        state = offered(state)
        self.assertEqual(latest_offer(state, "outside").team, "AWAY")
        self.assertEqual(latest_offer(state, "home").status, "rejected")

    def test_market_blocks_unresolved_contract_or_eligibility_only(self):
        for changes in ({"contract_state": "under_contract"}, {"status": "rfa_eligible"},
                        {"rights_ref": ""}, {"negotiation_opens": LATER}):
            with self.subTest(changes=changes), self.assertRaises(NegotiationError):
                market_state(**changes)

    def test_verification_is_bound_to_input_and_time(self):
        state = initial()
        offer = Offer("home", 1, "HOME", terms(), AT, EXPIRES)
        payload = offer_payload(state, offer, 1)
        for changes in ({"issuer": "unknown"}, {"source_refs": ()},
                        {"source_refs": ["mutable"]}, {"scope": "wrong"},
                        {"subject_digest": fingerprint({})}, {"verified_at": LATER},
                        {"valid_until": AT}):
            with self.subTest(changes=changes), self.assertRaises(NegotiationError):
                submit_offer(state, HOME, AT, offer, 1, evidence=evidence("club_offer", payload, **changes))

    def test_player_cannot_issue_club_offer_or_club_reject_for_player(self):
        state = offered()
        with self.assertRaises(NegotiationError):
            reject_offer(state, HOME, AT, "outside", 1, decision_ref="test:wrong-actor")
        with self.assertRaises(NegotiationError):
            withdraw_offer(state, HOME, AT, "outside", 1, decision_ref="test:wrong-club")
        offer = Offer("home", 1, "HOME", terms(), AT, EXPIRES)
        with self.assertRaises(NegotiationError):
            submit_offer(state, PLAYER, AT, offer, 2,
                         evidence=evidence("club_offer", offer_payload(state, offer, 2)))

    def test_four_ordinary_slots_and_reserved_fifth(self):
        state = market_state()
        for slot in range(1, 5):
            state = offered(state, Actor("club", f"CLUB-{slot}"), f"offer-{slot}", slot)
        self.assertEqual(len(comparison_slots(state, AT)), 5)
        self.assertTrue(all(comparison_slots(state, AT)[:4]))
        self.assertIsNone(comparison_slots(state, AT)[4])
        with self.assertRaisesRegex(NegotiationError, "slots 1 through 4"):
            offered(state, AWAY, "fifth", 5)
        with self.assertRaisesRegex(NegotiationError, "occupied"):
            offered(state, AWAY, "overwrite", 1)

    def test_closed_slot_can_be_reused_without_erasing_history(self):
        state = reject_offer(offered(), PLAYER, AT, "outside", 1, decision_ref="test:reject")
        state = offered(state, Actor("club", "OTHER"), "replacement")
        self.assertEqual(latest_offer(state, "outside").status, "rejected")
        self.assertEqual(comparison_slots(state, AT)[0].offer_id, "replacement")

    def test_counter_is_a_request_and_requires_club_revision(self):
        state = offered()
        requested = request_counter(state, PLAYER, AT, "outside", 1, terms(salary=2000000),
                                    decision_ref="test:counter-request")
        self.assertEqual(requested.offers, state.offers)
        self.assertEqual(len(requested.requests), 1)
        revised = offered(requested, version=2, value=terms(salary=1500000))
        self.assertEqual(revised.offers[0].status, "superseded")
        self.assertEqual(latest_offer(revised, "outside").version, 2)
        self.assertEqual(latest_offer(state, "outside").version, 1)
        with self.assertRaisesRegex(NegotiationError, "stale"):
            reject_offer(revised, PLAYER, AT, "outside", 1, decision_ref="test:stale")

    def test_expired_or_withdrawn_offer_cannot_be_accepted(self):
        state = offered(market_state("UFA"))
        for closed, at in ((state, EXPIRES),
                           (withdraw_offer(state, AWAY, AT, "outside", 1, decision_ref="test:withdraw"), AT)):
            with self.subTest(at=at), self.assertRaisesRegex(NegotiationError, "not live"):
                accept_offer(closed, PLAYER, at, "outside", 1,
                             evidence=evidence("agreement", selection_payload(closed, "outside", 1)))
        self.assertEqual(comparison_slots(state, EXPIRES)[0].status, "expired")
        self.assertEqual(latest_offer(state, "outside").status, "open")

    def test_ufa_agreement_stops_at_execution_handoff_and_closes_other_bids(self):
        state = offered(offered(market_state("UFA")), HOME, "home", 2)
        state = accept_offer(state, PLAYER, AT, "outside", 1,
                             evidence=evidence("agreement", selection_payload(state, "outside", 1)))
        self.assertEqual(state.phase, "execution_pending")
        self.assertEqual(state.resolution.team, "AWAY")
        self.assertEqual(latest_offer(state, "home").status, "closed")
        self.assertIsNone(comparison_slots(state, AT)[4])

    def test_rfa_can_re_sign_with_incumbent_without_matching(self):
        state = offered(market_state(), HOME, "home")
        state = accept_offer(state, PLAYER, AT, "home", 1,
                             evidence=evidence("agreement", selection_payload(state, "home", 1)))
        self.assertEqual(state.resolution.team, "HOME")
        self.assertIsNone(state.sheet)

    def test_rfa_outside_offer_cannot_bypass_offer_sheet(self):
        state = offered()
        with self.assertRaisesRegex(NegotiationError, "offer-sheet"):
            accept_offer(state, PLAYER, AT, "outside", 1,
                         evidence=evidence("agreement", selection_payload(state, "outside", 1)))

    def test_ufa_or_unsigned_offer_cannot_trigger_match(self):
        for state in (offered(market_state("UFA")), offered(), signed()):
            with self.subTest(phase=state.phase), self.assertRaisesRegex(NegotiationError, "served RFA"):
                resolved(state)
        with self.assertRaises(NegotiationError):
            signed(offered(market_state("UFA")))

    def test_offer_sheet_minimum_three_nonoption_seasons(self):
        for value in (terms(1), terms(2), terms(3, option=True)):
            with self.subTest(value=value), self.assertRaisesRegex(NegotiationError, "3 seasons"):
                signed(offered(value=value))
        self.assertEqual(signed(offered(value=terms(4, option=True))).phase, "sheet_pending")

    def test_offer_sheet_locks_all_other_negotiations(self):
        state = signed()
        actions = (
            lambda: request_counter(state, PLAYER, AT, "outside", 1, terms(), decision_ref="test:counter"),
            lambda: reject_offer(state, PLAYER, AT, "outside", 1, decision_ref="test:reject"),
            lambda: withdraw_offer(state, AWAY, AT, "outside", 1, decision_ref="test:withdraw"),
            lambda: offered(state, HOME, "home", 2),
            lambda: signed(state),
        )
        for action in actions:
            with self.assertRaisesRegex(NegotiationError, "locked"):
                action()

    def test_receipt_deadline_cannot_use_modern_period_or_missing_timezone(self):
        for deadline in ("2003-07-18T23:59:59-04:00", "2003-07-23T23:59:59-04:00",
                         "2003-07-31T23:59:59", "2003-07-31T23:59:59+00:00",
                         "2003-08-01T23:59:59-04:00"):
            with self.subTest(deadline=deadline), self.assertRaises(NegotiationError):
                served(deadline=deadline)

    def test_external_calendar_adjustment_requires_bound_source(self):
        result = served(deadline="2003-08-01T23:59:59-04:00",
                        deadline_calendar_adjustment_ref="test:verified-calendar-adjustment")
        self.assertEqual(result.sheet.deadline_calendar_adjustment_ref, "test:verified-calendar-adjustment")

    def test_matching_period_starts_at_receipt_not_signature(self):
        state = signed()
        deadline = "2003-08-01T23:59:59-04:00"
        payload = receipt_payload(state, LATER, deadline, "America/New_York", "test:receipt-rule")
        state = record_receipt(state, AUTHORITY, LATER, LATER, deadline, "America/New_York",
                               "test:receipt-rule", evidence=evidence("record_receipt", payload))
        self.assertEqual(state.sheet.signed_at, AT)
        self.assertEqual(state.sheet.received_at, LATER)

    def test_fifth_slot_clones_signed_principal_terms_and_exact_version(self):
        state = served()
        result = resolved(state)
        match = comparison_slots(result, LATER)[4]
        self.assertEqual(match.team, "HOME")
        self.assertEqual(match.slot, 5)
        self.assertEqual((match.offer_id, match.version), (state.sheet.offer_id, state.sheet.version))
        self.assertEqual(match.terms, state.sheet.terms)
        self.assertEqual(result.phase, "binding_resolution_pending_registration")
        self.assertEqual(state.phase, "sheet_pending")
        with self.assertRaises(FrozenInstanceError):
            match.team = "OTHER"
        copied = match.terms.data
        copied["salary_schedule"][0]["salary"] = 1
        self.assertEqual(match.terms.data["salary_schedule"][0]["salary"], 1000000)
        self.assertEqual(state.sheet.terms.data["salary_schedule"][0]["salary"], 1000000)

    def test_only_incumbent_can_match_and_no_repeat_acceptance_follows(self):
        with self.assertRaisesRegex(NegotiationError, "club HOME"):
            resolved(actor=AWAY)
        with self.assertRaisesRegex(NegotiationError, "club HOME"):
            resolved(actor=PLAYER)
        state = resolved()
        with self.assertRaisesRegex(NegotiationError, "locked"):
            accept_offer(state, PLAYER, LATER, "outside", 1,
                         evidence=evidence("agreement", selection_payload(state, "outside", 1)))
        with self.assertRaises(NegotiationError):
            resolved(state)

    def test_valid_sheet_survives_original_offer_expiry(self):
        state = resolved(at="2003-07-25T12:00:00-04:00")
        self.assertEqual(state.resolution.outcome, "matched")

    def test_timed_match_and_verified_nonmatch_resolutions(self):
        self.assertEqual(resolved(at=DEADLINE).resolution.outcome, "matched")
        self.assertEqual(resolved(outcome="match_declined").resolution.team, "AWAY")
        with self.assertRaisesRegex(NegotiationError, "deadline has elapsed"):
            resolved(at="2003-08-01T00:00:00-04:00")
        with self.assertRaisesRegex(NegotiationError, "has not elapsed"):
            resolved(outcome="deadline_elapsed", at=DEADLINE, actor=AUTHORITY)
        result = resolved(outcome="deadline_elapsed", at="2003-08-01T00:00:00-04:00", actor=AUTHORITY)
        self.assertEqual(result.resolution.team, "AWAY")
        self.assertEqual(result.phase, "binding_resolution_pending_registration")
        self.assertIsNone(comparison_slots(result, result.last_at)[4])

    def test_signing_moratorium_and_backdated_action_are_blocked(self):
        state = offered(market_state("UFA", signing_opens=LATER))
        with self.assertRaisesRegex(NegotiationError, "signing window"):
            accept_offer(state, PLAYER, AT, "outside", 1,
                         evidence=evidence("agreement", selection_payload(state, "outside", 1)))
        with self.assertRaisesRegex(NegotiationError, "go backwards"):
            reject_offer(state, PLAYER, "2003-07-15T12:00:00-04:00", "outside", 1,
                         decision_ref="test:backdate")

    def test_terms_input_is_copied_and_invalid_schedules_fail(self):
        original = terms().data
        snapshot = Terms.from_dict(original)
        original["salary_schedule"][0]["salary"] = 1
        self.assertEqual(snapshot.data["salary_schedule"][0]["salary"], 1000000)
        for field, value in (("salary", -1), ("salary", True), ("guaranteed", 2000000),
                             ("season", "2003-07"), ("option", "unknown")):
            data = terms().data
            data["salary_schedule"][0][field] = value
            with self.subTest(field=field), self.assertRaises(NegotiationError):
                Terms.from_dict(data)

    def test_unsupported_era_is_blocked(self):
        with self.assertRaisesRegex(NegotiationError, "1999"):
            start("test-player", "HOME", AT, trusted_issuers=(AUTHORITY.identity,), cba="2023")


if __name__ == "__main__":
    unittest.main()
