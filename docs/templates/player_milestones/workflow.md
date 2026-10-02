# Using a milestone page

[Templates](README.md) · [Filled previews](../../examples/player_milestones/README.md) · [Research](research.md)

## Open the relevant page when its event exists

Read the current date, professional identity, contract, availability and owning phase note. Select the page for the actual event. A possible future event belongs in the calendar, not in the pending player-decision list. An offer expiry, option date or meeting time needs a recorded source.

Use the blank template to make a short page in the owning phase, named `Milestone_YYYY-MM-DD_<subject>.md`. Fill it from evidence available on that date; replace relative template links with links appropriate to its new location. Keep a source reference to the original template. This document is not a game note or an engine request.

| Event | Suggested owning location | Evidence to read |
| --- | --- | --- |
| Rookie offer, free-agent offer or summer option decision | `01_Free_Agency/` | Dated offer, signed terms, rights, applicable rule and cap records |
| In-season extension or trade | The actual regular-season month/week | Contract/transaction source and its effective date |
| Summer trade | Current summer phase | Confirmed transaction, applicable consent rights and reporting instructions |
| Training block | `03_Offseason/` or the phase where it actually occurs | Player preference, staff plan, availability, completed-session evidence |
| Exit meeting | The phase/week containing the team's actual last game | Closed season reports and communicated staff feedback |
| Camp review | `04_Training_Camp/` | Staff observations, current role and scheduled evaluation |

Offseason work can start before August, and contract talks can overlap workouts. Existing folder names organize records; they do not create mandatory dates or mean an event occurred.

## Present the decision in one pass

1. Lead with the new fact, what is available to the player, and the next real deadline.
2. Show the decision-relevant table, with a compact identity line. Link the full stats, contract or medical record rather than reproducing unrelated details.
3. End with one concrete question or short reply prompt. Allow a free-form player response; the examples are not mandatory scripts.
4. Record the player's exact choice and date. A counteroffer, role request, workout preference or objection is a request until its actual consequence is known.
5. Show who acts next and the next review date or event. Close the page only when the event and required conditions have resolved.

Waiting for the user's contract choice is appropriate because it is a player decision. Waiting for the user to approve an ordinary AI/GM trade or lineup is not: show the verified outcome and the player's available response. A verified trade-consent right creates a genuine player decision and must never be waived automatically.

## Keep state and authority clear

Use readable states such as **Awaiting your response**, **Awaiting club response**, **Pending execution**, **Awaiting approval**, or **Closed**. Include the event ID, career date, source record and decision owner in a short record block if needed. Do not imply that an unsigned offer, rumor, planned workout or preliminary role assessment is final.

After a closed event, update only the records its outcome actually changes. A signing may affect the contract, roster, holdings, finances and dated identity. A trade preserves earlier team stints and follows the existing new-club career-folder rule. A workout creates a session/review record; it does not add NBA games. The current state's pending decisions list contains live player decisions only.

The user determines Wade's choices. The AI/GM determines club offers and transactions, coaches determine assignments, qualified staff determine clearance, and the league/contract process determines whether transaction conditions have been satisfied.

## What is implemented versus presented

These pages are reusable presentation and recording templates. The existing rookie negotiation log can support a live rookie offer when its date and terms are verified. The [contract/free-agency workflow module](../../contract_negotiation_engine.md) adds isolated, tested transitions for supplied offers and evidence, including the reserved fifth RFA matching record. Its [interactive demonstration](../../examples/player_milestones/contract_negotiation_preview.html) is a separate local preview, not a connection to live career state. Market generation, complete cap/eligibility validation, automatic deadlines, exceptional RFA resolution, trade completion, new-contract write-back and training-driven ability changes still need their supported integration paths. Missing mechanics stay unresolved instead of being improvised as guaranteed results.

Contract and free-agency pages share offer IDs, versions and a history. Declining an incumbent proposal does not create market eligibility. Four comparison slots contain ordinary proposals; the fifth records only the incumbent's matching outcome for the exact signed outside sheet. See the [detailed research and interaction specification](contract_negotiation_research.md).

The [build roadmap](../../ROADMAP.md) retains ownership of unfinished mechanics. No template here advances the clock, runs a draw, creates an offer or signs a deal.

### One rule inconsistency to resolve before using a deadline

The current `runtime/rookie_contract.py` returns a fourth-year option deadline of `2004-10-31`. The repository's 1999 FAQ extract describes October 31 after the player's second season, which appears inconsistent for a 2003 entrant. This template collection deliberately does not choose or publish a live deadline from those conflicting records. Verify the exact applicable rule before an option deadline is activated; this template change does not amend the contract engine.
