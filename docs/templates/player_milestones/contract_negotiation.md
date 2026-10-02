# Contract desk | {{player}}

![Contract desk: use the current team's verified banner when instantiating this template](assets/contract.svg)

[Templates](README.md) · [Four-offer example](../../examples/player_milestones/contract_negotiation.md) · [Free agency](free_agency.md) · [Research and detailed design](contract_negotiation_research.md)

| Player / age | Position / incumbent | Career date / agreement | Verified status |
| --- | --- | --- | --- |
| {{name; age today}} | {{position; club or rights holder}} | {{date; governing CBA}} | {{under contract / draft rights / UFA / RFA; source}} |

**Now:** {{dated event that opened this desk}}.

**Your decision:** {{specific action the player can take now}}.

**Next deadline:** {{date, time, timezone, event, source; or no firm deadline communicated}}.

**Waiting on:** {{player / representative / offering club / incumbent / registration}}.

**Market eligibility:** {{negotiations open? signing permitted? existing contract ended? valid RFA rights?}}. Declining a proposal does not terminate an existing contract, release draft rights, erase restrictions, or advance the calendar.

## Four ordinary offers, one reserved matching position

Display up to four actual written proposals together. An open incumbent proposal uses one ordinary slot. Empty slots read **No written offer**. Keep additional proposals in the offer register and let the player select the four compared here. Interest, meetings and estimates belong in a separate contact log.

| Decision factor | 1 · {{club / offer ID}} | 2 · {{club / offer ID}} | 3 · {{club / offer ID}} | 4 · {{club / offer ID}} |
| --- | --- | --- | --- | --- |
| Version / received | {{version; timestamp}} | {{version; timestamp}} | {{version; timestamp}} | {{version; timestamp}} |
| Availability | {{open/declined/withdrawn/expired/superseded}} | {{state}} | {{state}} | {{state}} |
| Protected base under offered terms | {{amount; protection scope}} | {{amount}} | {{amount}} | {{amount}} |
| Player-controlled option money | {{amount; conditions}} | {{amount}} | {{amount}} | {{amount}} |
| Team-controlled option money | {{amount}} | {{amount}} | {{amount}} | {{amount}} |
| Maximum scheduled base | {{includes options; excludes incentives}} | {{amount}} | {{amount}} | {{amount}} |
| Incentives | {{none / possible amount and conditions}} | {{terms}} | {{terms}} | {{terms}} |
| Length / control | {{firm years; option type/year}} | {{terms}} | {{terms}} | {{terms}} |
| Next possible market | {{date and controlling condition}} | {{condition}} | {{condition}} | {{condition}} |
| First-year cap route | {{room / rights / named exception; verification}} | {{route}} | {{route}} | {{route}} |
| Trade consent | {{actual clause/right or none verified}} | {{basis}} | {{basis}} | {{basis}} |
| Basketball plan | {{speaker, date, intended role; non-contractual}} | {{plan}} | {{plan}} | {{plan}} |
| Expiry / signing readiness | {{real deadline; missing checks}} | {{state}} | {{state}} | {{state}} |

### 5 · {{incumbent}} matched offer

**State:** {{inactive for UFA / no sheet signed / awaiting receipt / match pending / matched / not matched}}.

**Matched source:** {{outside offer ID + immutable version + signed sheet reference}}.

**Principal terms:** {{exact matched salary schedule, payment dates, protection, applicable options and eligible incentives}}.

Use the incumbent's identity. Keep the source team's non-contractual role pitch separate. This position never contains an unrelated fifth bid or a second accept/decline menu after a valid match. Show outstanding administrative conditions even when the contractual destination is determined.

**Service and response evidence:** {{actual receipt; verified deadline; notice and dispatch evidence; applicable rule; outstanding physical/registration conditions}}. Unknown receipt means no invented countdown. A display clock is not evidence of non-match.

## Salary, security and cash timing

Repeat per offer, or align all schedules in one table. Store integer dollars. A shorter deal's later seasons say **No contracted salary; future earnings unknown**, rather than projecting zero career income.

| Offer / season | Base | Protected under offered terms | Conditional amount | Controller / trigger | Payment / decision date |
| --- | ---: | ---: | ---: | --- | --- |
| {{ID; season}} | {{amount}} | {{amount; protection scope}} | {{amount}} | {{option owner; vesting condition}} | {{source-backed date or unknown}} |
| **Offer totals** | {{scheduled base}} | {{protected base}} | {{separate option/vesting subtotals}} | {{incentives excluded}} | {{next checkpoint}} |

Compare the first season, first two seasons and all contracted years. Average annual value is descriptive, not an automatic ranking. Extension schedules separate existing years from added years.

<details>
<summary>Detailed term sheet for {{selected offer/version}}</summary>

| Term | Written proposal | Requested change | Evidence / consequence |
| --- | --- | --- | --- |
| Contract type / start | {{new agreement / extension / rookie scale}} | {{request}} | {{eligibility; existing deal separate}} |
| Salary progression | {{each season; dollar changes}} | {{request}} | {{route-specific limits}} |
| Protection | {{amount, termination reasons covered, exclusions}} | {{request}} | {{clause; partial guarantees and vesting dates}} |
| Options / termination | {{owner, season, amount, notice method}} | {{request}} | {{structure; deadline and default verified}} |
| Signing bonus | {{amount, installments, inclusion in total}} | {{request}} | {{allocation/limit review; no double counting}} |
| Incentives | {{each amount, objective target, season, payment trigger}} | {{request}} | {{likely/unlikely classification and cap review separately}} |
| Trade terms | {{consent basis; assignment bonus if any}} | {{eligible request}} | {{no fictional blanket veto}} |
| Payment timing | {{gross installments; deferral if any}} | {{request}} | {{cash timing distinct from cap charge}} |
| Physical / execution | {{conditions; required documents}} | {{clarification}} | {{responsible party and next action}} |
| Fees / deductions | {{verified representation and escrow terms}} | {{clarification}} | {{gross is not take-home; unknown taxes stay unknown}} |
| Role / development | {{coach's words/date; competition}} | {{player goals}} | {{basketball discussion, not guaranteed minutes}} |
| Team situation | {{known roster, coach and competitive plan}} | {{questions}} | {{evidence available at cutoff}} |

</details>

## Your instruction and the club's reply

| Action | Player instruction | What changes |
| --- | --- | --- |
| Counter | “On {{offer/version}}, request {{specific changes}}.” | Append a player request; original club terms remain intact until a club revision |
| Clarify | “Confirm {{protection, role, route, deadline}}.” | Open a question with an owner; unknowns remain visible |
| Request time | “Request until {{date}}.” | Expiry changes only if the offering club grants it |
| Decline | “Decline {{offer/version}}.” | That version becomes unavailable; other offers and rights retain their recorded status |
| Explore market | “Seek other offers when I am eligible.” | Open the free-agency path; no automatic release or fabricated offers |
| Proceed on UFA terms | “Proceed with {{available verified version}}.” | Record instruction/agreement; list execution and registration separately |
| Choose RFA sheet | “Authorize this eligible outside sheet.” | Explain possible incumbent destination before signature; follow receipt/matching process |
| Re-sign / choose qualifying offer | “Proceed on {{verified incumbent terms}}.” | Use the distinct eligible route; no fabricated outside matching event |

**Your reply:** {{exact instruction; nothing preselected}}.

**Priority order:** {{player-ranked security, immediate salary, flexibility, role, team situation, location}}.

**Counter version:** {{source offer; requested delta; proposed schedule; status; not a club offer}}.

**Next checkpoint:** {{club reply, actual receipt, verified deadline or registration}}.

## History and final handoff

| Time / timezone | Actor | Event | Offer / version | Changed terms | Result / evidence |
| --- | --- | --- | --- | --- | --- |
| {{timestamp}} | {{player/representative/club/league}} | {{offer/counter/decline/revision/sheet/receipt/match}} | {{immutable reference}} | {{before → after}} | {{source and status}} |

Superseded terms stay accessible, but unavailable. Declined, withdrawn and expired mean different things. No player counter unilaterally reopens a signed sheet.

**Final terms:** {{exact record and rule checks}}. **Destination:** {{determined/pending}}. **Execution:** {{unsigned/signed/matching resolution}}. **Registration:** {{pending/completed}}. **Career write-back:** {{not performed/owning event}}.

A live outcome must reconcile contract schedule, roster/holdings, cap/rights, professional identity and owning event through a supported transaction path. Templates and the demonstration do not perform that write-back.

### Route-specific substitutions

- Rookie scale: verified scale band and mandatory term, not arbitrary competing UFA contracts for a draft-rights player.
- Extension: remaining old money separate from added years; verify eligibility window.
- Option-only event: holder, amount, notice and consequence. A team option is the club's decision. Remove the new-offer menu if no new offer exists.
- Team styling: current-club banner, each offering club's own header, selected-offer accent, incumbent-colored fifth match. Status always has readable text. See the [theme specification](contract_negotiation_research.md#team-colors-and-page-layout).
