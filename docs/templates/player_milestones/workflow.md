# Using a milestone page

[Templates](README.md) · [Filled previews](../../examples/player_milestones/README.md) · [Research](research.md)

## Open the relevant page when its event exists

Read the current date, professional identity, contract, availability and owning phase note. Select the page for the actual event. A possible future event belongs in the calendar, not in the pending player-decision list. An offer expiry, option date or meeting time needs a recorded source.

Use the blank template to make a page in the owning phase, named `Milestone_YYYY-MM-DD_<subject>.md`. Keep its immediate action compact and retain the detailed working records below it. Fill it from evidence available on that date; replace relative template links with links appropriate to its new location. Keep a source reference to the original template. This document is not a game note or an engine request.

| Event | Suggested owning location | Evidence to read |
| --- | --- | --- |
| Rookie offer, free-agent offer or summer option decision | `01_Free_Agency/` | Dated offer, signed terms, rights, applicable rule and cap records |
| In-season extension or trade | The actual regular-season month/week | Contract/transaction source and its effective date |
| Summer trade | Current summer phase | Confirmed transaction, applicable consent rights and reporting instructions |
| Training block | `03_Offseason/` or the phase where it actually occurs | Player preference, staff plan, availability, completed-session evidence |
| Exit meeting | The phase/week containing the team's actual last game | Closed season reports and communicated staff feedback |
| Camp review | `04_Training_Camp/` | Staff observations, current role and scheduled evaluation |
| Contract checkpoint | Phase containing the actual option/QO/expiry event | Existing terms, notice, holder, applicable rules and rights outcome |
| Stats review | Owning reporting period or meeting note | Source-linked closed reports, coverage and dated role evidence |
| Calendar view | Current phase index | Actual milestone IDs, commitments, dependencies and sourced deadlines |

Offseason work can start before August, and contract talks can overlap workouts. Existing folder names organize records; they do not create mandatory dates or mean an event occurred.

## Present the decision in one pass

1. Lead with the new fact, what is available to the player, and the next real deadline.
2. Show the decision-relevant table, with a compact identity line. Link the full stats, contract or medical record rather than reproducing unrelated details.
3. End with one concrete question or short reply prompt. Allow a free-form player response; the examples are not mandatory scripts.
4. Record the player's exact choice and date. A counteroffer, role request, workout preference or objection is a request until its actual consequence is known.
5. Show who acts next and the next review date or event. Close the page only when the event and required conditions have resolved.

Waiting for the user's contract choice is appropriate because it is a player decision. Waiting for the user to approve an ordinary AI/GM trade or lineup is not, below franchise standing: show the verified outcome and the player's available response. At franchise standing the consultation gate (`docs/front_office.md`, Franchise consultation) is a genuine player decision: the front office asks before it adds another star, the career clock waits for the answer, and the consultation page under `Wade_Consultations/` follows this workflow. A verified trade-consent right creates a genuine player decision and must never be waived automatically.

## Keep state and authority clear

Use readable states such as **Awaiting your response**, **Awaiting club response**, **Pending execution**, **Awaiting approval**, or **Closed**. Include the event ID, career date, source record and decision owner in a short record block if needed. Do not imply that an unsigned offer, rumor, planned workout or preliminary role assessment is final.

After a closed event, update only the records its outcome actually changes. A signing may affect the contract, roster, holdings, finances and dated identity. A trade preserves earlier team stints and follows the existing new-club career-folder rule. A workout creates a session/review record; it does not add NBA games. The current state's pending decisions list contains live player decisions only.

The user determines Wade's choices. The AI/GM determines club offers and transactions, coaches determine assignments, qualified staff determine clearance, and the league/contract process determines whether transaction conditions have been satisfied.

## What is implemented versus presented

These pages are reusable presentation and recording templates. The rookie negotiation log supports dated rookie offers. The [contract/free-agency workflow module](../../contract_negotiation_engine.md) supplies isolated transitions for offers and evidence, including the reserved fifth RFA matching record. Existing 2003 front-office adapters in `runtime/market.py`, `runtime/gm.py`, `runtime/negotiation.py` and `runtime/signing.py` support their documented market and transaction paths; `runtime/trades.py` and `runtime/camp.py` support their own documented workflows. A template never bypasses those paths or broadens their era/transaction coverage.

The [screen gallery](../../examples/player_milestones/career_milestones_preview.html) and [detailed contract demonstration](../../examples/player_milestones/contract_negotiation_preview.html) are local previews. The [market profile](../../player_market_profile.md) adds read-only status derivation, scenario selection and an evidence-backed salary range. It does not authenticate sources, approve a contract or write to the career. Live player-dashboard action integration, unsupported legal exceptions and any training-driven ability mechanism still require their own supported implementation. Missing mechanics stay unresolved.

Contract and free-agency pages share offer IDs, versions and a history. Declining an incumbent proposal does not create market eligibility. Four comparison slots contain ordinary proposals; the fifth records only the incumbent's matching outcome for the exact signed outside sheet. See the [detailed research and interaction specification](contract_negotiation_research.md).

The [build roadmap](../../ROADMAP.md) retains ownership of unfinished mechanics. No template here advances the clock, runs a draw, creates an offer or signs a deal.

## Keep depth useful

Use three levels: the event and next decision, the main working surface, then supporting records. Trade shows a transition dossier; free agency shows rights, contacts and bids; negotiation shows versioned cash and control; training shows planned work, completed work and review. Do not replace all of them with the same generic choice card.

For live screens, remove inapplicable branches while preserving material unknowns. The UFA/RFA selector belongs to hypothetical setup; the career's status comes from dated records. Acknowledging a trade notice is distinct from exercising a real consent right. A new contract needs an executed source agreement, its own schedule and the supported write-back. Contract expiry alone is not that agreement.

Keep unresolved questions with their owners and next checkpoints. Calendar conflicts can reschedule proposed sessions after confirmation; they cannot silently move a sourced legal deadline. Periodic statistics reviews use the existing report hierarchy and never duplicate game ownership.

### One rule inconsistency to resolve before using a deadline

Resolved October 2, 2026: `runtime/rookie_contract.py` now returns `2005-10-31`, October 31 after Wade's second season (1999 FAQ Q38), recorded in `library/2003/league/nba_2003_04_calendar.json`.
