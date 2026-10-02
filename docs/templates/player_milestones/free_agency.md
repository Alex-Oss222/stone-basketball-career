# Your market | {{player}}

![Free-agency market](assets/market.svg)

<!-- On a filled page, replace the neutral banner with the original team's dated identity/theme. Each offer card uses its own team's accessible colors and written team label. The fifth matching-result card always uses the original team's theme. Color must never be the only status indicator. -->

[Template collection](README.md) · [Filled example](../../examples/player_milestones/free_agency.md) · [Contract desk](contract_negotiation.md) · [Research and implementation requirements](contract_negotiation_research.md) · [Interactive preview](../../examples/player_milestones/contract_negotiation_preview.html)

| Player / age | Position | Original club | Verified rights / status | As of |
| --- | --- | --- | --- | --- |
| {{name; age}} | {{position}} | {{club}} | {{UFA / RFA / draft rights / under contract; evidence}} | {{career date and source cutoff}} |

**Your next move:** {{only available player choices, based on verified rights and current written offers}}

**Negotiations open:** {{verified date and rule source}} · **Signing permitted:** {{verified date and any applicable exception}} · **Next deadline:** {{exact event, timestamp, timezone and source, or unknown}}

Do not produce a countdown from an assumed time. A deadline without reliable receipt or calendar evidence stays unresolved.

## Can you enter this market?

| Required fact | Dated evidence | Effect on available actions |
| --- | --- | --- |
| Existing contract | {{term, end date, active obligation and source}} | {{eligible now / future eligibility / blocked}} |
| Outstanding option | {{owner, deadline, actual exercise decision and source}} | {{effect on contract status, without assuming the decision}} |
| Player service / contract class | {{verified service, prior contract and applicable era}} | {{applicable free-agent or draft-rights rules}} |
| Qualifying offer / rights | {{if relevant, exact qualifying-offer status and source}} | {{UFA / RFA / unresolved}} |
| Calendar | {{dated negotiating and execution gates}} | {{which actions may occur today}} |
| Trigger | {{dated career event that opened this page}} | {{owning event note and next checkpoint}} |

Rejecting a current-team extension or proposal does not itself end an existing contract, waive draft rights or make an RFA unrestricted. Show the actual eligibility transition before opening outside signing choices. A fictional preview is never that transition.

## Scenario setup and live rights

**Template/demo selector:** {{UFA / RFA}}. This lets the user explore either market. **Live derived status:** {{status; controlling evidence}}. A live player cannot elect to remove a club's matching rights by changing the selector.

| Status | What the screen opens | What remains unavailable |
| --- | --- | --- |
| UFA | Eligible club negotiations and direct signing route | RFA matching controls |
| RFA with maintained rights | Incumbent negotiation, available QO, eligible outside sheet and matching timeline | Guaranteed choice of the outside destination after a sheet |
| Draft rights / active contract / unresolved option | Appropriate rookie, extension or checkpoint screen | Open-market signing without the required status transition |
| Rights evidence missing | Questions, records review and existing proposal inspection | Claims of verified eligibility or signing readiness |

The [market profile baseline](../../player_market_profile.md) supplies this separation and an explainable first-year salary range. It does not turn a hypothetical status into a real contract action.

## What are you worth in this market?

**First-year estimate:** {{low / working target / high}} · **Cap share:** {{percentages}} · **Evidence as of:** {{date}} · **Confidence:** {{label and reason}}.

| Value dossier | Evidence to show | Why it matters |
| --- | --- | --- |
| Career production | {{sourced closed totals; minutes and sample}} | Keeps the valuation connected to this simulated player |
| Comparable contracts | {{players, signing date, age, role, first salary, contemporaneous cap}} | Explains the market anchor and era normalization |
| Missing information | {{defense/medical/tracking or weak comparable coverage}} | Keeps the range from implying precision the evidence cannot support |
| Negotiating rights | {{verified status and incumbent rights}} | Determines your alternatives; not an automatic fixed RFA discount |
| Legal bounds | {{verified minimum, maximum and rule source}} | Separates allowable salary from market judgment |
| Each bidder's route | {{dated ledger and cap/exception/rights route}} | Shows whether the specific proposed salary can be supported |

If there is no adequate evidence, display **Estimate unavailable**, identify the missing inputs, and keep the actual offers visible. Never fill a gap using historical Wade's future production or contracts. Prefer a range to a false precise prediction. All example numbers must identify whether they are sourced or synthetic.

## Start with your team's proposal

| Proposal | Your available response | Team response still required |
| --- | --- | --- |
| {{original-team offer ID and version, or no offer}} | {{review / counter / reject / proceed if signing-ready}} | {{revision, acceptance of counter, availability confirmation or execution}} |

**Explore the market:** {{available if eligible; otherwise name the remaining contract/right/calendar condition}}.

Keep an open original-team proposal in the ordinary comparison while outside conversations occur. If the player rejects it, archive that exact version and free its slot. A later actual proposal may use the empty slot. Never generate a replacement bid merely to fill the layout. A counter records the player's request; it is not automatically a new club offer, and the original version's continued availability must be checked.

## What matters to you?

| Priority | Your ranking | What would satisfy it? |
| --- | ---: | --- |
| Guaranteed money | {{rank}} | {{amount and protection preference}} |
| Role and development | {{rank}} | {{responsibility, coaching support and questions}} |
| Control over your next move | {{rank}} | {{term and option preference within the rules}} |
| Competitive situation | {{rank}} | {{dated evidence available at this checkpoint}} |
| Location / family fit | {{rank or omit}} | {{player's stated preference}} |

## Four ordinary offer slots

Show up to four actual ordinary offers in one comparison. The original team's open bid counts toward four. Use fewer columns when fewer offers exist. In a responsive UI, keep all four on the same page, with a two-by-two or stacked arrangement when needed. Reject, expire, withdraw and supersede actions retain an archive entry and remove signing availability. History does not become an extra active slot.

| Comparison | Slot 1: {{team / version}} | Slot 2: {{team / version}} | Slot 3: {{team / version}} | Slot 4: {{team / version}} |
| --- | --- | --- | --- | --- |
| Team theme | {{club-specific colors and label}} | {{theme}} | {{theme}} | {{theme}} |
| Relationship | {{original / outside}} | {{relationship}} | {{relationship}} | {{relationship}} |
| Source / received at | {{written source, timestamp and timezone}} | {{source / time}} | {{source / time}} | {{source / time}} |
| Version / status | {{ID, open / closed reason}} | {{ID / status}} | {{ID / status}} | {{ID / status}} |
| Annual base salaries | {{one figure per season}} | {{schedule}} | {{schedule}} | {{schedule}} |
| Unconditional guaranteed base | {{amount, exact protection basis}} | {{amount / basis}} | {{amount / basis}} | {{amount / basis}} |
| Potential base total | {{including separately identified option salary}} | {{amount}} | {{amount}} | {{amount}} |
| Term / option owner | {{non-option years; option year, owner and deadline}} | {{term / option}} | {{term / option}} | {{term / option}} |
| Guarantee conditions | {{amount, covered grounds, vesting dates and remaining conditions}} | {{conditions}} | {{conditions}} | {{conditions}} |
| Incentives | {{amounts and conditions; likely/unlikely classification if verified}} | {{incentives}} | {{incentives}} | {{incentives}} |
| Signing / assignment bonus | {{separate cash terms and eligibility}} | {{terms}} | {{terms}} | {{terms}} |
| Payment schedule | {{dated installments / source or unresolved}} | {{schedule}} | {{schedule}} | {{schedule}} |
| Cap/signing mechanism | {{verified route or signing blocked}} | {{route}} | {{route}} | {{route}} |
| Expiration | {{exact timestamp and source / unknown}} | {{expiry}} | {{expiry}} | {{expiry}} |
| Basketball plan | {{speaker, date, projection; no automatic minutes promise}} | {{plan}} | {{plan}} | {{plan}} |
| Main unanswered question | {{decision-relevant issue}} | {{issue}} | {{issue}} | {{issue}} |
| Current action | {{counter / reject / signing-ready choice / blocked with reason}} | {{action}} | {{action}} | {{action}} |

Reconcile every total to the annual schedule. Separate option-dependent salary, guaranteed bonuses and conditional upside. A player option gives the player a choice, but its unexercised salary is not unconditional guaranteed base in this comparison. Do not present an agent's projection as a club offer or invent a net-pay estimate without the assumptions and required information.

### Interest and conversations, outside the money comparison

| Club | Contact stage | Contact source / timestamp | What is actually known | Next inquiry |
| --- | --- | --- | --- | --- |
| {{club or omit if none}} | {{interest / meeting / request for terms}} | {{dated source}} | {{no written salary offer unless supplied}} | {{specific question}} |

## Restricted free agency: rights panel

Remove this panel for a verified UFA. Keep it visible if rights are unresolved, with blocked actions explained. An original-club negotiated offer, its qualifying offer and a matching result are distinct records.

| Rights item | Required record |
| --- | --- |
| Restriction basis | {{player eligibility, era and qualifying-offer evidence}} |
| Qualifying offer | {{amount, tender time, version, withdrawal/expiry status, acceptance deadline and source}} |
| Qualifying-offer route | {{choose only if actually available and lawful; separate rights-panel action}} |
| Original club / matching authority | {{team and verified right of first refusal}} |
| Proposed outside offer sheet | {{exact version; term, cap and other eligibility checks}} |
| Execution | {{player/team execution status and source timestamp}} |
| Actual original-team receipt | {{time, timezone, delivery method and receipt evidence}} |
| Applicable matching period | {{era-specific source and calculated deadline, or unresolved}} |
| Matching notice | {{pending / exercised / not exercised; timestamp and evidence}} |
| Remaining conditions | {{physical, notice, dispute or other relevant conditions, if any}} |

The qualifying offer can be chosen from its rights panel when verified available. It is not an extra fabricated ordinary offer and must not push the match out of position five.

For a 2003 event, use the 1999 CBA rather than a modern deadline. Article XI, Section 6 requires more than two non-option seasons for an outside offer sheet and provides a 15-day matching period from receipt. The [research notes](contract_negotiation_research.md) cover principal terms, conditions and evidence needed for resolution. [Primary source: 1999 NBA/NBPA CBA](https://ipmall.law.unh.edu/sites/default/files/hosted_resources/SportsEntLaw_Institute/1999NBA_NBPA_CBA.pdf).

## Fifth position: {{original team}} matching result

Pin this panel below the four-slot ordinary comparison. Preserve position five even when fewer ordinary offers exist. Before a sheet, show “No offer sheet selected”; after verified service, show “Response pending.” Do not display a fabricated dollar offer while waiting. For a UFA, show “Not applicable, no matching right” or omit the panel.

| Field | Match record |
| --- | --- |
| Team / theme | {{original club's colors, name and status label}} |
| Status | {{no sheet / receipt unverified / response pending / matched / not matched / disputed}} |
| Record identity | {{match ID, separate from the original-team ordinary offer}} |
| Matched source | {{immutable outside offer-sheet ID and version}} |
| Receipt / deadline | {{sourced timestamps or unresolved}} |
| Exercise evidence | {{dated valid notice or verified no-match resolution}} |
| Annual base / total | {{copy matched principal terms exactly; do not negotiate new figures here}} |
| Term / options / protection | {{matched principal terms, with reference to original schedule}} |
| Bonus / payment terms | {{matchable terms as determined under the applicable era}} |
| Basketball plan | {{separate original-club statement, not copied from outside coaching pitch}} |
| Binding destination / outcome | {{original club if matched; outside club if applicable no-match outcome; unresolved otherwise}} |
| Administration | {{registration and career writeback separately tracked}} |
| Player action | {{review/reporting tasks; no second veto of a binding outcome}} |

Do not label a discretionary improved original-club bid as a match. It remains an ordinary proposal. Once a binding offer-sheet outcome exists, pending administration does not reopen the player's destination choice. Preserve any unresolved conditions explicitly rather than claiming an unconditional final result.

## Interaction and record transitions

| Action / event | Required condition | Recorded result |
| --- | --- | --- |
| Request free agency | Actual status and calendar permit entry | Eligible market opens, or precise blocker is shown |
| Reject ordinary offer | Exact open version identified | Version archived; status/rights unchanged unless separately established |
| Counter | Valid contact and clear requested changes | Player request logged; club answer pending |
| Revised club offer | Actual club response | New version, relation to prior version, availability rechecked |
| New outside offer | Dated written terms from a club | Available ordinary slot populated; no fabricated overflow |
| Choose UFA offer | Eligible player, current offer and signing checks passed | Execution process for the exact version |
| Execute RFA offer sheet | Complete era-specific eligibility and terms checks | Freeze signed terms; other signing choices locked |
| Receive offer sheet | Documented actual receipt | Applicable matching clock begins |
| Valid match | Authorized timely notice and required evidence | Fifth result populated; contractual destination recorded |
| No match | Verified applicable period and resolution | Fifth result says not matched; outside outcome recorded |
| Expiry / withdrawal | Sourced event and exact version | Offer unavailable; history preserved |
| Register / write back | Documented binding outcome and remaining conditions resolved | Owning event, career state and affected team records reconciled through supported workflow |

**Implementation boundary:** static Markdown pages describe decisions; they do not perform them. A preview or local negotiation state is not a validated cap engine, a real team bid, a league registration or an automatic career transfer. Use the supported canonical event workflow only when its required evidence exists.

## Your instruction and next checkpoint

**Your reply:** {{precise player instruction identifying offer version or information request}}

**Next checkpoint:** {{club response, calendar gate, receipt, matching deadline or execution/administrative event}}

**Evidence:** {{rights determination, current offers and all versions, contact log, cap basis, calendar authority, applicable CBA rules and event references}}

**History:** {{append timestamps, actor, source, prior state, action and new state; retain rejected/withdrawn/expired/superseded records}}
