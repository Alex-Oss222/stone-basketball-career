# Contract negotiation workflow

`runtime/contract_negotiation.py` is an isolated, deterministic state machine for the 1999 CBA workflow. It creates no offers and writes no career, roster, cap, finance, or clock records. Test fixtures are fictional and remain in the test suite. The current June 26, 2003 unsigned draft-rights checkpoint does not become free agency by using this module.

The historical rules and their primary-source references are in [the contract research guide](templates/player_milestones/contract_negotiation_research.md). This module supports the 1999 agreement only. A later career date requires an appropriate independently verified rules implementation before this workflow can be used for that era.

## Implemented behavior

| Action | Required actor and evidence | Result |
| --- | --- | --- |
| Submit or revise a club offer | Issuing club; external legality attestation bound to complete offer, player, incumbent, era and slot | Immutable version; a revision supersedes the previous version |
| Request different terms | Player; dated player-decision reference | Separate counter request; the club offer remains unchanged |
| Reject an offer | Player; dated player-decision reference | Offer rejected; contract and free-agent status remain unchanged |
| Withdraw an ordinary offer | Issuing club; dated club-decision reference | Offer withdrawn; signed sheets cannot use this route |
| Open a market | Player; externally verified UFA/RFA status, expired/released contract, rights reference and negotiation/signing windows | Outside clubs may submit independently issued offers |
| Accept an ordinary offer | Player; exact selection/legality attestation; valid signing window when a market is open | `execution_pending`; other live proposals close |
| Sign an outside RFA sheet | Player; externally verified legal, signed sheet with at least three non-option seasons | `sheet_pending`; all negotiations lock and the exact terms freeze |
| Record delivery | Trusted authority; actual incumbent receipt, exact verified deadline, IANA timezone and rule reference | Receipt-based match period recorded |
| Match | Incumbent club; verified timely matching notice | `binding_resolution_pending_registration`; a matching resolution appears in slot 5 |
| Decline matching | Incumbent club; verified timely notice | Binding resolution for the outside team; no fifth competing offer |
| Record deadline elapsed | Trusted authority; verified no timely valid matching notice or unresolved dispute | Binding resolution for the outside team |

A match or nonmatch resolves a previously signed offer sheet. It does not ask the player for a second acceptance. `binding_resolution_pending_registration` acknowledges the binding resolution while leaving legal conditions, physical requirements, registration and transaction accounting to the execution adapter. It does not assert that every condition has been satisfied.

## Offer comparison and immutability

There are four ordinary comparison slots. An incumbent's voluntary proposal uses one of those four slots. Only an actual incumbent matching resolution occupies slot 5. It copies the signed outside offer's principal-terms snapshot and preserves its offer ID and version. No API accepts replacement matching terms or an ordinary bid for slot 5.

All prior offer versions remain in `Negotiation.offers`. Rejected, withdrawn or expired slots can be reused by a new offer ID without removing their history. Each club may have one live offer. This first implementation supports four simultaneous live proposals; an unlimited market registry with a separately selected four-card view remains an integration extension. It does not create extra teams or proposals to fill empty cards.

`comparison_slots(state, at)` returns exactly five positions with `None` for unused positions. It derives expiry without changing the stored snapshot or audit journal. An expired ordinary offer cannot be accepted, rejected, withdrawn or revised as if it were live. A signed offer sheet continues through its legal matching process even if the original proposal's acceptance deadline subsequently passes.

`Terms.from_dict` makes an immutable canonical JSON snapshot; `.data` returns a fresh copy. Required `salary_schedule` rows contain consecutive `season` values in `YYYY-YY` format, positive integer-dollar `salary`, integer-dollar `guaranteed`, and `option` set to `none`, `player` or `team`. An option can occur only in the final row and is excluded from the three-season offer-sheet minimum. Additional fields represent externally verified principal terms, including payment schedules and those incentives that legally belong in principal terms. Coaching pitches, expected minutes, housing, noncash benefits and other non-principal material belong in separate presentation/application records, not in this matching snapshot.

## External verification boundary

An `Attestation` records a trusted issuer, immutable source references, the verification timestamp, an exclusive validity endpoint, action scope and SHA-256 digest of the exact action payload. Public payload helpers make the binding reproducible. The state machine rejects absent, expired, future-dated, wrong-scope, wrong-input or untrusted attestations.

These are adapter assertions, not cryptographic credentials. The module does not open the referenced documents, determine whether a string names a real source, authenticate an actor, or prove that a verifier reached a correct legal conclusion. A trusted adapter must authenticate the person or AI/GM issuing each action, verify source contents, associate player actions with the user's actual decision, and prevent a client from minting attestations. Do not expose these Python constructors as a public unauthenticated action API.

Before a live action, that adapter must independently validate, as applicable:

- The actual career date, applicable CBA, player identity, incumbent rights, contract expiry/release and waiver clearance.
- A qualifying offer and preserved rights establishing actual restricted status. Merely meeting RFA eligibility criteria is insufficient.
- Negotiating and signing windows, moratoria, minimum and maximum salary, maximum term, raises, options, guarantees, incentives, bonuses, offer-sheet contents and cap/exception authority.
- The validity and delivery of the player-signed offer sheet and notices. For elapsed-deadline resolution, the absence of a timely matching notice, including one deemed sent under the governing rule, and any unresolved dispute.
- The applicable definition of principal terms under Article XI, Section 6(c), including which cash incentives qualify. Similar economic totals alone do not establish a valid match.
- Physical or other legal conditions, NBA registration, the appropriate transaction/contract documents and postmatch restrictions, including applicable trade-consent and offering-team trade restrictions.

The clock guard checks nondecreasing, timezone-aware event timestamps. It never advances the canonical career clock. The calling application must reject events beyond its independently established career date and persist the returned snapshot and journal atomically with an optimistic version check. That persistence adapter is not implemented here.

## Matching deadline

The supported historical period is 15 days from actual incumbent receipt, not from the player's signature. `record_receipt` requires the exact externally verified deadline and a supplied source. It does not choose an hour of day. Both timestamps must carry the supplied IANA timezone's actual UTC offset.

The ordinary date guard requires the fifteenth calendar date after receipt. A later deadline is accepted only with an additional `deadline_calendar_adjustment_ref` bound into the trusted attestation, for an independently checked Article XLII weekend/federal-holiday rollover. The engine does not compute or validate the holiday calendar or the adjustment's legal correctness. A supplied earlier deadline is always rejected. The verified deadline is inclusive for the recorded matching-notice action; an elapsed-deadline event must occur strictly later. The authority must verify notice timing under the actual deemed-sent rule before recording either action.

Receipt and resolution must be recorded in chronological order. Backdated notice ingestion, disputed notice timing, jointly agreed three-party sheet withdrawal, revised eligibility after opening, and special-case adjustments require a separate verified workflow. Unsupported actions fail closed rather than silently changing the signed sheet.

## Integration still required

The isolated `contract_negotiation.py` state machine does not itself supply a live player dashboard, a persistence store, club demand, cap authority or a complete league contract validator. The wider repository already has a 2003 Miami pathway: `runtime/market.py` and `runtime/gm.py` construct front-office market judgments and proposals; `runtime/negotiation.py` persists negotiation records and applies independently drawn responses; `runtime/signing.py` writes supported transactions into career, control and finance records. Trade and camp adapters also exist. Those modules are distinct from this isolated workflow and are not automatically a complete, authenticated player-facing action layer.

The new read-only [`player_market_profile.py`](player_market_profile.md) supplies a selectable UFA/RFA scenario, separately derived live status, an explainable scheduled-salary-proxy valuation and distinct player/route salary bounds. It creates no club offer or legal attestation and does not execute a career action. Unknown rights, missing cap publication and missing route authority remain visible. Its checked-in examples are synthetic scenarios, not career events.

Remaining player-dashboard integration must authenticate the actor, use the authoritative date and current records, bind exact offer versions, verify every applicable legal/timing condition, and hand off accepted actions to the correct supported persistence/execution adapter. This state machine also does not implement a separate qualifying-offer tender/withdrawal state machine. A valid incumbent qualifying offer may be represented as an independently verified club offer, but its special legal consequences must be validated outside this module.

Use the presentation templates to explain choices. Use authenticated, dated application actions to call the workflow. Only a separate verified execution adapter may update the canonical player contract, team control, cap holds, salary commitments, roster, destination career folder and postmatch restrictions. Do not mark those integration tasks complete because these tests pass.

Run `python -m unittest tests.test_contract_negotiation` to check the synthetic actor, eligibility, version, expiry, four-plus-one comparison and restricted-matching flows.
