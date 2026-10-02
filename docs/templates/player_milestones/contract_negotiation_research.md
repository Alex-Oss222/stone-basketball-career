# Contract negotiation and free agency: research and implementation design

Reviewed October 2, 2026. Target: the `milestone-1` player-career project, whose live checkpoint is June 26, 2003. The July 16 examples are independent fictional demonstrations, not decisions in Wade's career.

[Contract example](../../examples/player_milestones/contract_negotiation.md) · [Free-agency example](../../examples/player_milestones/free_agency.md) · [Interactive demonstration](../../examples/player_milestones/contract_negotiation_preview.html) · [Reusable contract template](contract_negotiation.md) · [Workflow engine](../../contract_negotiation_engine.md)

## Assessment of the existing page

The original page does three things correctly: it separates $12.3 million of protected salary from $18.9 million of scheduled salary, identifies the club's control over the last year, and leaves the player's instruction open. It also correctly treats the coach's role description as an intention.

Its limitation is depth and connection. One proposal and four reply examples cannot show a real market decision. There is no common view of alternative offers, no durable link between a counter and a club revision, and no visible route from an incumbent offer into unrestricted or restricted free agency. A fixed red banner cannot identify several offering clubs.

The proposed solution is one contract workspace shared by negotiations and free agency. Four ordinary comparison positions hold proposals. A fifth, permanently reserved position records an incumbent match of an outside restricted-free-agent sheet. That fifth position is a contractual outcome, not an additional discretionary bid.

## Historical research and confidence

The controlling edition matters more than the research date. The NBPA's current agreement page identifies the modern agreement; it does not make modern limits valid in 2003. [S3]

Compact historical findings from the original agreement [S1]: ordinary maximum terms were six seasons, seven using full Bird rights; annual increases were generally 10%, or 12.5% with Bird/Early Bird rights, measured from first-year salary. Restricted offer sheets needed three non-option seasons. The incumbent had 15 days from receipt to match principal terms. Only one signed sheet could be outstanding. A valid match determined the incumbent destination; non-match determined the offering-team destination. Non-cash terms were not principal terms. Time-computation provisions adjusted certain weekend/holiday endpoints. Sign-and-trades also required three non-option seasons. Rookie scale used three seasons plus a fourth-year team option.

Contemporaneous checks: the reported 2003-04 cap was $43.84 million and the mid-level exception $4.917 million. A $6 million starting salary therefore needs a different valid route. [S2] Miami's 2003 Odom release corroborates the historical 15-day matching period. [S4]

These findings are not a complete eligibility opinion for the fictional offers. No verified prior salary, service record, qualifying offer, club payroll, retained rights, roster place or executed document has been supplied. Historical amendments and the transition to the 2005 agreement need checking at the actual event date.

### Original agreement source locator

Use these exact sections when an implementation needs a rule. This is an index, not a substitute for the operative text.

| Question | S1 location |
| --- | --- |
| Definitions of rights and compensation | Article I |
| Permitted terms, protection, minimum and maximum salary | Article II §§3–7 |
| Salary, bonus allocation and cap accounting | Article VII §§3–4 |
| Increases, decreases, incentives and exceptions | Article VII §§5–6 |
| Extensions and renegotiation | Article VII §7 |
| Sign-and-trade | Article VII §8(e) |
| Rookie scale / contract length | Articles VIII–IX |
| Restricted free agency and matching | Article XI §6 |
| Options | Article XII |
| Trade clauses | Article XXIV |
| Contract approval | Article XXXVI |
| Time computation | Article XLII §2 |
| Sheet / matching notice forms | Exhibits G–H |

### Two existing inconsistencies to keep visible

1. The old roadmap called July 15 the start of 2003 signings. Historical calendar retrieval places the first signing day on July 16. The roadmap now defers to a verified season calendar rather than embedding an unsupported date. The examples deliberately do not activate a live calendar. [S5]
2. `runtime/rookie_contract.py` publishes a 2004 fourth-year option deadline, while the existing historical evidence describes a deadline after the second season. The current workflow already flags this. Keep the discrepancy and the subsequent agreement transition open for a focused rules correction; this feature does not silently change Wade's rookie terms.

## The complete player journey

### Incumbent offer before free agency

Show whether the club is proposing an extension of an active contract, a new agreement after expiration, or a rookie-scale deal. These are different routes.

The player can request clarification, counter, request time, decline, or proceed when the terms and route are verified. Declining one proposal does not erase the existing deal. “Test free agency” records the player's intention until the contract status and calendar permit a market to open.

The agent should ask what matters first: protected money, shorter commitment, control over an option, immediate salary, basketball responsibility, team situation or location. The game should not assign the player's priorities for them.

### Eligible unrestricted market

Once the supplied status evidence says UFA and negotiations are permitted, incumbent and outside clubs can submit dated proposals. A club contact with no terms remains “interest,” not an offer with estimated money.

Every offer has a unique ID and immutable versions. The player may compare, counter or decline several available proposals. A revision gets a new version with a visible delta. The original stays in history. A player counter is not displayed as an offer from the club.

Proceeding on one available version locks the selection for the execution handoff. Show outstanding documents and administrative conditions. Other proposals become closed or unavailable only through a recorded event; do not silently label every club as having withdrawn.

### Eligible restricted market

The rights panel comes before the offers: incumbent, basis of restriction, qualifying-offer record and status, negotiation availability, applicable agreement and deadlines. A home-team re-signing proposal and a qualifying offer are separately identified routes.

Unsigned discussions can coexist. Before the player authorizes an outside sheet, display the material consequence: its matched principal terms may bind the player to the incumbent. The player is choosing terms with that possibility understood.

After a signed sheet exists, lock incompatible negotiation actions. Track signature and actual service separately. Only a documented receipt starts the recorded response workflow. The match decision belongs to the incumbent, not to the player.

When the incumbent matches, position five fills with its identity, the source sheet/version, matched terms, notice evidence, destination and remaining administrative conditions. When the response period resolves without a match, the outside destination is recorded; position five says “Not matched.” Do not invent another accept button after either binding resolution.

A disputed deadline, physical condition, three-party withdrawal or defective notice needs a supported exceptional path. It must not be approximated by “try again.”

## Four proposals plus the fifth matching record

The limit of four is a comparison limit, not a fictional rule that only four clubs may contact the player. Keep all contacts and prior proposals in history.

An incumbent's initial offer can occupy position one, with three outside proposals in positions two through four. If that proposal is declined, preserve it in history and allow another real proposal to be pinned to the freed comparison position. Until that happens, show its declined status or an empty slot. Do not generate a replacement.

The fifth position is reserved even when there are fewer than four ordinary proposals. For a UFA it says no matching right. For an RFA it changes from waiting for a sheet, to waiting for receipt, to response pending, then to the recorded outcome.

The matched record stores the incumbent as destination and the outside sheet as source. Money, payment dates, protection and other matched principal terms come from the frozen sheet. The original outside coach's role pitch is not copied as an incumbent promise. The incumbent's original offer remains a separate historical record.

## Money: what the user must be able to distinguish

All example amounts are gross, fictional proposal terms. None are currently owed.

| Measure | Calculation / meaning | Display rule |
| --- | --- | --- |
| Scheduled base | Sum of each proposed season's base, including option years | Label options explicitly |
| Protected non-option base | Protection supported by the proposed wording, excluding unresolved option exercise | State the protection scope |
| Player-controlled amount | Salary reachable through the player's own option election, subject to written conditions | Separate from employer-controlled money |
| Team-controlled amount | Salary dependent on a team election | Never merge into unconditional security |
| Potential incentives | Separate sum of bonus opportunities | Exclude from base; list each condition |
| Cap charge | Amount calculated under the applicable accounting rules | Do not substitute annual cash or average value |
| Cash timing | Actual proposed payment dates and installments | Distinguish from season attribution |
| Net income | Gross less verified fees, deductions and taxes | Do not invent residence, withholding or a universal tax rate |

A signing bonus needs a dedicated field explaining whether it is already included in the displayed compensation total. Otherwise the desk can double-count it. A partial guarantee needs amount, covered termination reasons, vesting trigger and trigger date, not merely a “guaranteed” badge.

The comparison should show the same horizon. A one-year deal with $7 million does not create zero earnings in years two and three; it creates unknown future earnings after the contracted year. A projected future deal, if the simulation later supports one, is a separately labeled scenario.

### Worked arithmetic and negotiating leverage

Using the four fictional examples:

- Miami A1: $6m + $6.3m + $6.6m = $18.9m scheduled. The first two years supply $12.3m of assumed protected base. The $6.6m final year is controlled by the team. Each $300,000 step is 5% of the first-year $6m.
- Lakers B1: $5.5m + $5.775m + $6.05m = $17.325m protected over three seasons. That is $5.025m more protected base than A1, although its headline is $1.575m lower.
- Boston C1: $6.4m first year plus a $6.4m player option. The desk separates $6.4m non-option protection from $6.4m of player-controlled continuation. This is not equivalent to Miami's team option.
- New York D1: $7m for one season. It has the largest first-year salary and the shortest contracted horizon.

A useful Miami counter is to preserve the schedule while requesting full final-year protection. Its exact delta is $6.6m of additional protection, with no base-salary increase. A lower salary for more protection is a negotiable fallback, not a mandatory concession and not a predicted club acceptance.

An alternative approach is to negotiate option ownership instead of only price. It changes who decides the next market entry. Its usefulness depends on the player's priorities and whether the requested structure is permitted. No generic “best contract” score captures that tradeoff.

## The minute-detail negotiation dossier

For each selected proposal, provide these records without forcing all of them into the four-card headline:

1. Identity: player, club, representative, agreement edition, career cutoff, status basis and years of service.
2. Provenance: offer ID/version, issuer, issue/receipt times, written source and known expiry.
3. Structure: transaction route, start season, existing money versus new money, term, allowed salary band and annual progression.
4. Security: full/partial protection, covered reasons, excluded conditions, vesting dates and medical contingencies.
5. Control: option owner, amount, exercise method, notice deadline, termination provision if applicable and possible market entry.
6. Incentives: objective target, amount, applicable season, prior evidence, payout date, accounting classification and treatment in any matched sheet.
7. Cash: salary installments, signing bonus, advance/deferral if offered, representation fee basis and separate gross/net display.
8. Mobility: actual trade-consent basis, assignment bonus if offered, post-transaction restrictions and later option/rights effects.
9. Signing feasibility: team cap route, supporting ledger date, holds, necessary prior transactions, roster place, required documents and signing window.
10. Basketball discussion: coach and date, intended position, ball-handling responsibility, rotation competition, development support and review meeting.
11. Player evaluation: priorities, concerns, preferred counter and fallback. These are user decisions, not automated club actions.
12. Completion: exact selected terms, destination outcome, conditions outstanding, registration reference and canonical write-back record.

Use “not offered,” “not applicable” and “not verified” precisely. An empty source should not become a zero, an automatic approval or a hidden default.

## Team colors and page layout

Use a neutral reading surface and club-specific accents. The main career identity remains the current club; the selected proposal can tint the negotiation workspace with an explicit “Reviewing [club] offer” label. This must not imply a team change.

The sample design presets are Miami burgundy/black/gold, Lakers purple/gold, Boston green, and New York blue/orange. These are recognizable illustrative UI presets, not a verified reproduction of each franchise's 2003 brand manual. Production styling should come from a team-and-era theme registry.

| Surface | Identity / behavior |
| --- | --- |
| Career header | Current club and dated player identity |
| Ordinary offer card | Offering club, club name and offer version |
| Selected details / counter | Selected offering club; visible review label |
| Fifth matched record | Incumbent club; source sheet explicitly attributed |
| Validation state | Text and icon/label independent of brand color |

Desktop: four aligned cards, same metric order, followed by the fixed fifth matching panel and detailed schedules. Tablet: two by two. Phone: four sequential cards on the same page. Never shrink four dense columns to unreadable phone text or hide essential terms behind a carousel.

The GitHub Markdown view uses real tables and embedded team assets because arbitrary page CSS cannot be relied upon there. The HTML demonstration shows responsive selection and local interaction. It is a review surface, not a hosted production career app.

Maintain readable contrast, visible keyboard focus, labeled native controls and status text that does not rely on red/green. Keep currency values aligned and option explanations adjacent. Long legal details belong in expandable sections; salary, control, expiry and signing blockers stay visible.

## State, authority and integration

The player decides personal instructions. Club actors issue, revise or withdraw proposals. The incumbent supplies the matching response. Trusted adapters supply validated dates, rights and legality evidence. The workflow records these actions; it does not grant the user GM authority.

The Python module supplies isolated negotiation transitions and an audit history. Its trusted input boundary is explicit: a passed source reference is not independent proof that the underlying contract is legal. The live adapter must validate those records before calling it.

The HTML demonstration is an independent, local exploration of the intended interaction. Its hypothetical match/non-match controls preview alternative outcomes; they are not player powers in the simulation. It does not call the Python workflow or persist an actual contract.

Live integration still needs dated offer generation, complete cap/eligibility validation, supported exceptional RFA cases, authenticated actor routing, durable storage, deadline scheduling and atomic transaction write-back. A successful write-back must reconcile contract, rights, cap ledger, roster/holdings, identity and owning event exactly once. A failed write must leave the prior canonical state intact.

No demo fixture should enter those records. An offer from a real NBA team in an example is fictional unless a dated simulation event establishes it.

## Acceptance criteria

- An active contract cannot become a UFA market merely because the player declines an extension.
- An incumbent offer and outside proposals use the same terms model and history.
- Four ordinary proposals can be compared simultaneously; prior proposals remain accessible.
- Player counters never overwrite club terms or renew deadlines.
- Expired, withdrawn, declined and superseded versions cannot be selected as open proposals.
- An RFA cannot bypass its workflow through a UFA acceptance action.
- An ineligible short outside proposal cannot become a signed historical sheet.
- Only one signed sheet is active; incompatible negotiations lock.
- Receipt and response evidence are distinct from signature and display time.
- Position five uses the incumbent's identity and the exact applicable source terms.
- A matching resolution is not presented as a new elective offer.
- Outstanding administrative conditions remain visible.
- Unknown data stays unresolved; examples never alter live career files.

## Sources

**S1. Primary historical agreement.** [1999 NBA–NBPA collective bargaining agreement, UNH Law archive](https://ipmall.law.unh.edu/sites/default/files/hosted_resources/SportsEntLaw_Institute/1999NBA_NBPA_CBA.pdf). Original operative text, with the section index above. Later amendments must be checked for a live event.

**S2. Contemporary cap reporting.** [UPI, July 15, 2003: NBA salary cap rises to $43.8 million](https://www.upi.com/Sports_News/2003/07/15/NBA-salary-cap-rises-to-438-million/70781058319542/). Supports historical cap and exception amounts; it does not establish any sample club's available room.

**S3. Modern agreement boundary.** [NBPA agreement page](https://nbpa.com/cba) and [NBA CBA 101, November 2024](https://cms.nba.com/wp-content/uploads/sites/4/2024/11/2024-25-CBA-101.pdf). Modern reference, not the historical authority for 2003.

**S4. Contemporary club corroboration.** [Miami Heat: Odom offer-sheet announcement](https://www.nba.com/heat/news/heat_sign_odom_offersheet.html). Used only for the historical matching-period check; its later transaction is not imported into the career.

**S5. Historical calendar reference.** [Larry Coon's 1999-agreement FAQ](https://cbafaq.com/salarycap99.htm). Search retrieval was available; direct page retrieval failed during this review. The repository also contains a [limited extract](../../../library/2003/league/cba_1999_salary_cap_faq_extract.txt). Verify the calendar from a complete operative source before live activation.

**Repository evidence.** [Operating rules](../../../AGENTS.md), [existing historical rule inventory](../../../library/2003/league/nba_1999_cba_rules.json), [2003 cap inputs](../../../library/2003/league/nba_2003_04_cap_rules.json), [front-office workflow](../../front_office.md), [milestone workflow](workflow.md), [build roadmap](../../ROADMAP.md). Repository inputs describe the existing implementation; they are not independent proof of historical accuracy.

The financial examples, interaction design, theme presets, negotiation priorities and implementation recommendations are original product-design proposals. They are distinguished throughout from sourced historical rules.

