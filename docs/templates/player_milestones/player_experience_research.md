# Player milestone experience: research and design rationale

Reviewed October 2, 2026. Career knowledge remains June 26, 2003. This is a design reference, not a played event, contract decision or future schedule publication.

[Reusable templates](README.md) · [Filled examples](../../examples/player_milestones/README.md) · [Contract research and detailed legal locator](contract_negotiation_research.md)

## Evidence, limits and what changes the design

The user's core requirement is a player career with meaningful things to do as the calendar moves. A deep screen should answer an immediate personal question and expose the detail behind it. It should not require acting as the general manager, or repeating the same accept/decline form at every milestone.

Two primary player-perspective sources help distinguish the experiences:

- Jamal Crawford identifies family location, roster fit and money as decision factors; he describes both player-led and team-guided summer work. [P2]
- NBA player interviews describe sudden trade notification, family disruption and adjustment to different team terminology. [P3]

These are later accounts used to inform interface design, not evidence of what a particular player knew or chose in 2003. They do not establish a universal player preference, a medical regimen or a rule for the historical career.

The original 1999 agreement supplies important historical distinctions: ordinary assignment does not require player approval. Negotiated no-trade eligibility requires eight NBA years and four with the signing team. A matched RFA has one year of consent protection and cannot reach the matching offer's club during that year. Certain one-year Bird/Early Bird contracts cannot be traded under that edition. Reporting is generally within 48 hours in-season or one week between seasons, unless notice allows longer; the destination pays reasonable player/family moving expenses. [P1]

For historical free agency, the original matching period is 15 days after receipt. Rookie-scale contracts use three seasons plus a fourth-year team option. [P1] The 2003 signing period began July 16. [P4] Actual notices, amendments and season calendars still control exact dates.

## Make the screens different by making their jobs different

The recommendations below are original product design proposals. They are not claims that the NBA supplies these screens or follows this information architecture.

| Milestone | The player's immediate question | Primary working surface | The meaningful response | What closes the page |
| --- | --- | --- | --- | --- |
| Trade update | Where am I going, when must I report, and what happens to my job? | Before/after transition dossier with a reporting checklist | Acknowledge verified information; ask role or transition questions; decide consent only when a real right exists | Transaction outcome and the next arrival or role meeting |
| Free agency | Which destinations can actually sign me, and which fit what I want? | Market board with contact stages, rights state and shortlist | Set priorities, authorize eligible meetings, pursue terms or wait | A specific next negotiation, signed sheet or executed contract |
| Contract negotiation | What am I being offered, what is secure, and what should I change? | Versioned term sheet and counter comparison | Counter exact terms, request time, decline a proposal or proceed on verified terms | Club response, expiry or execution handoff |
| Offseason training | What am I working on this block, and how will we know it helped? | Two-week training block, dated sessions and repeatable review | Choose focus and constraints, agree workload, report results | A review with evidence and a revised next block |
| Exit meeting | What did this season establish, and what needs attention? | Evidence-backed review with separate player and staff views | State priorities, disagree with an assessment, ask for an explanation | Agreed actions and unresolved items assigned a next meeting |
| Training camp | What is my current role, how can I earn more, and when will it be reviewed? | Role brief, competition, practice tasks and review criteria | Ask for specific reps, feedback or clarity | Coach's dated review or a new assignment |

Each screen has three reading layers: the event and next action at the top, the working evidence in the middle, and the full dossier beneath. Depth comes from inspectable records and precise differences, not a longer introduction.

## Trade: keep the transition useful even without a veto

Lead with the actual status: rumor, club-confirmed agreement, pending conditions, completed, rescinded, or blocked. A reported deal should not rewrite identity. Every confirmation carries its source and time. If a trade failed, preserve the failed event and identify which earlier state remains current.

The transition dossier should contain:

1. **The move:** previous and destination clubs, effective time, player or rights being moved, and the relevant terms of the whole transaction. Teammates, picks and cash belong in a secondary transaction panel rather than burying the player's destination.
2. **My contract:** remaining annual salary, protection, options, known assignment-bonus treatment, current rights and any unresolved effect. Show old and new values side by side. A blank means unknown, not unchanged.
3. **My role:** what the destination coach actually said, who said it, when, position, offensive tasks, defensive responsibilities, relevant competition and next review. Mark a reported expectation separately from an assigned role. Never turn a pitch into guaranteed minutes.
4. **My arrival:** reporting notice, due time with timezone, contact person, meeting place, travel status, physical appointment, temporary accommodation and expense contact. Use actual notice details; do not invent a flight or medical clearance.
5. **My response:** questions for the agent, role meeting request, family/relocation needs, personal reaction and any verified consent decision. Acknowledging receipt is not consenting to a transaction.

Give unfinished tasks owners. “Housing unresolved; destination operations contact to respond by [time]” is more useful than a generic welcoming paragraph. Family fields are optional and user-supplied, not inferred biography.

For trade rumors, the player's available work is limited: ask the representative for confirmation, express a preference and continue the existing schedule. Do not create a destination's playbook or a final relocation task list before there is a destination.

## Free agency: separate opportunity from choice

A free-agency board is a relationship and availability record. It should not fabricate four competitive offers simply because the layout has four columns.

Use contact stages such as unverified report, confirmed interest, meeting requested, meeting held, terms discussed, written proposal, unavailable and signed outcome. Every stage names its source and date. The player's shortlist is separate from club interest: wanting a team is not evidence that the team wants the player.

Before comparing money, state the route: unsigned draft rights, active contract, eligible extension discussion, UFA, RFA or unresolved status. A hypothetical setup can choose UFA or RFA to explore the screen. A live career displays the status established by its dated records. Explain why with the shortest useful evidence trail.

Player priorities should be editable, retain their date, and remain optional. Useful dimensions are protected money, next opportunity to choose a team, intended role, developmental support, roster fit, location and tolerance for uncertainty. Avoid a hidden weighted score that announces a best choice on the player's behalf.

After a meeting, the screen should preserve unanswered questions. Examples: Who handles the ball late in possessions? What role survives if another guard signs? Which year can I control? Has the actual funding route been checked? What happens if the incumbent matches? A follow-up deadline belongs beside each answer request.

## Negotiation: show a credible worth range without pretending it is destiny

Use three distinct concepts throughout:

- **Market estimate:** a reasoned interval based on available comparable contracts and the player's current evidence.
- **Legal boundary:** what this player and club can sign under the dated rules and funding route.
- **Actual proposal:** what an identified club has offered in a recorded version.

For a reusable demonstration, a user-entered theoretical value is a scenario assumption. In a live negotiation it is an aspiration until supported by evidence. Neither should silently overwrite a club's budget or the player's eligibility.

The valuation dossier should expose the comparison set: player, signing date, service, role, age at signing, relevant preceding performance, first-year salary, signing-season cap, term, protection and option owner. Normalize first-year salary by that comparable's cap, then explain any proposed differences. Comparables from after the career cutoff are excluded. A thin or unavailable set produces a wider interval or no estimate, rather than false precision.

The screen can explain upward and downward considerations separately: larger sustained responsibility, a scarce useful skill, limited evidence, role dependence, known availability concerns or a small pool of funded destinations. These are simulation judgments with named evidence, not automatic dollar bonuses for reaching one scoring threshold.

Keep the counter small enough to understand. Identify the current version, fields changed, requested version, money difference and reason. Asking for a player option is different from asking for more salary. The club can accept, reject, revise or leave the request unanswered. No invented response timer should become a league rule.

## Offseason: make training a sequence of work and review

Open the first block from an actual exit meeting or player instruction. Record its starting point before prescribing its target: current phase, known restrictions, workload already scheduled, skill evidence and available staff. A recovery constraint is an input from the appropriate source; the template is not a medical assessment.

Prefer one primary focus and one maintenance focus. Each work item needs the game situation it is meant to improve, drill or film task, planned dose, staff owner, completion evidence and review method. A plan has a status of planned. Sessions become completed only when there is a record.

Separate three kinds of review:

| Evidence | What it can establish | What it cannot establish by itself |
| --- | --- | --- |
| Completion record | Sessions or reps actually performed | Improvement or readiness |
| Comparable practice test | Change under the stated test conditions | Transfer to NBA competition |
| Later game sample | Performance in actual simulated games | Causality from a single drill without other evidence |

Use makes and attempts, attempt type, drill conditions and fatigue stage when measuring shooting. Use a defined grading rubric and possession count for reads. Compare like conditions and show missing data. A 20-shot practice sample is not a new career shooting percentage.

The review can finish with continue, modify, reduce, pause pending staff input, or switch focus, with a reason. Do not award a predetermined rating gain for clicking “train.” The next block should retain lessons from the review, not reset the same blank table.

## Calendar rhythm and interruption handling

These are trigger designs, not a newly published 2003 calendar. The upcoming-events list should show only dates known at the current checkpoint. Use “date pending” when a club meeting or league calendar has not been supplied.

| Trigger | Screen to open | Due-date source | If another event intervenes |
| --- | --- | --- | --- |
| Team's season closes | Exit meeting | Club appointment | Keep unresolved actions in the summer plan |
| An actual option or eligibility checkpoint approaches | Contract status review | Existing contract and verified era rule | Recalculate only after the decision is recorded |
| Negotiation window opens | Free agency | Verified season calendar | Keep training scheduled unless changed by a real instruction |
| A club issues or revises terms | Negotiation | Dated proposal and stated expiry | Preserve prior versions and explain what superseded them |
| An RFA sheet is served | Matching status | Actual receipt and applicable time rules | Lock incompatible sheet actions; retain player support tasks |
| A training block ends | Training review | Agreed block plan | Record sessions displaced by meetings, travel or medical guidance |
| A trade is confirmed | Trade update | Official event and reporting notice | Reassign staff owners; transfer existing plan without inventing continuity |
| Camp reporting instructions arrive | Camp preparation | Club notice and era requirements | Resolve travel and documentation before role review |
| A coach schedules reassessment | Role review | Dated staff commitment | Use practice/game evidence available by that date |

The calendar should always answer: next action, actor, due date, evidence needed and consequence of waiting. Waiting can be a legitimate choice. It should not manufacture an offer, erase a deadline, skip a physical, or advance the simulation without a recorded event.

## Source ledger

| ID | Source, publication/era and link | Use and limitation |
| --- | --- | --- |
| P1 | NBA/NBPA, 1999 Collective Bargaining Agreement, effective January 20, 1999; [original document hosted by UNH Law](https://ipmall.law.unh.edu/sites/default/files/hosted_resources/SportsEntLaw_Institute/1999NBA_NBPA_CBA.pdf) | Primary agreement. Rule locators: Articles VII §8(b), VIII §1, XI §§5–6, XXIV §2; Exhibit A §10. Check amendments at the event date. |
| P2 | Jamal Crawford, NBA.com, June 28, 2023; [NBA Mailbag](https://www.nba.com/news/nba-mailbag-june-28-2023) | First-person perspective, used only for experience design. Not a 2003 rule source. |
| P3 | Steve Aschburner, NBA.com, February 22, 2017; [trade-deadline player interviews](https://www.nba.com/news/trade-deadline-can-be-roller-coaster-ride-nba-players) | Primary interviews, used only for experience design. Historical reporting periods come from P1. |
| P4 | ESPN, 2003 offseason; [free-agency scoreboard](https://www.espn.com/nba/s/2003/freeagents/scoreboard.html) | Contemporaneous secondary calendar corroboration only. Does not authorize importing later signings into the career. |

All URLs were checked October 2, 2026. The [existing contract research](contract_negotiation_research.md) supplies the broader contract source ledger and unresolved integration requirements. The practical design above intentionally avoids copying future player outcomes into live decisions.
