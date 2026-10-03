# Your next career decisions | {{player}}

[Templates](README.md) · [Filled calendar](../../examples/player_milestones/career_calendar.md) · [Screen gallery](../../examples/player_milestones/career_milestones_preview.html)

**Career date:** {{date and timezone}} · **Season / phase:** {{season; current phase}} · **Club / status:** {{club; active contract or rights}}.

**Today:** {{one action that genuinely needs the player's response, or no player decision due}}.

**Next real deadline:** {{event, holder, exact timestamp and source, or not yet established}}.

## Act now

Show only live decisions. A calendar milestone can exist without requiring the player to approve it.

| Priority | Decision / event | Who acts | Available response | Due / next update | Open screen |
| --- | --- | --- | --- | --- | --- |
| {{time-sensitive / scheduled / informational}} | {{specific dated event}} | {{player / club / staff}} | {{precise action or informational status}} | {{verified time or event}} | {{owning milestone}} |

**If nothing needs your response:** “No player decision is due. Your next recorded commitment is {{commitment}}.” Do not create a meeting, contract, workout or club offer to fill an empty calendar.

## Across the season

This is a reusable event map. Instantiate only events that exist in the current career. Dates are supplied by the active era, contract and season, not copied from another year's schedule.

| Moment | Event that opens it | Screen and player work | Completion evidence | Next return |
| --- | --- | --- | --- | --- |
| Final team game | Closed result and actual season elimination/end | [Exit meeting](exit_meeting.md): review role, results and summer requests | Dated meeting record; unresolved requests carried forward | Agreed follow-up |
| Contract review | Eligible extension window or actual offer | [Contract desk](contract_negotiation.md): security, salary, control and counter | Exact offer version and response; signing separately tracked | Club reply or real deadline |
| Option / QO date | Sourced contract or agreement deadline | [Contract checkpoint](contract_checkpoint.md): identify whose decision it is | Valid notice or unresolved record | Resulting contract/right status |
| Contract end | Recorded expiry, release or option outcome | [Free agency](free_agency.md): establish UFA/RFA/other status | Dated eligibility determination | Market opening, meeting or bid |
| Free-agent market | Eligible talks or receipt of written terms | Rank priorities, review value, compare current offers | Contact/offer history and exact instruction | Response, execution or RFA receipt |
| Development block | Agreed start date | [Summer work](offseason_training.md): focus, schedule, completion and review | Completed-session record and comparable observations | Block review |
| Trade | Verified report, agreement, consent request or completion | [Trade update](trade_update.md): rights, terms, practical transition and role questions | Actual transaction stage and reporting/meeting record | Condition cleared or staff follow-up |
| Camp / role review | Actual camp opening or scheduled feedback | [Camp review](training_camp.md): assignment, reps, evidence and requests | Dated coaching decision and player response | Next evaluation |
| Monthly check-in | Closed reporting period | [Stats review](stats_review.md): evidence, context and one basketball question | Source-linked aggregates and meeting note | Next closed period |

## Upcoming, with the uncertainty visible

| When | Item | Confidence in date | Dependency | What to prepare | Who confirms |
| --- | --- | --- | --- | --- | --- |
| {{date / date range / event-based}} | {{item}} | {{confirmed / proposed / unresolved}} | {{prerequisite}} | {{specific materials or question}} | {{owner}} |

Unverified dates cannot be used as countdowns or automatic default decisions. A proposed training review can be rescheduled; a legal deadline may require a different process. Display the distinction next to the date.

## Conflicts and carry-forward

| Conflict / open issue | Commitments affected | Player request | Responsible reply | Status / next check |
| --- | --- | --- | --- | --- |
| {{travel vs workout; agent call vs film session; pending physical}} | {{source event IDs}} | {{requested change}} | {{staff/agent/club}} | {{pending/confirmed; checkpoint}} |

Keep contractual deadlines fixed unless an authorized change is documented. Move the negotiable appointment only after its owner agrees. Preserve the original session as rescheduled instead of marking it completed.

**Your reply:** “For {{event}}, I want {{instruction}}. Please clarify {{open issue}}.”

**Next screen:** {{event and trigger}}. **Unresolved items carried forward:** {{IDs or none}}.

<details>
<summary>Instantiation record</summary>

`event_id`, `as_of`, `season`, `phase`, `trigger_ref`, `decision_owner`, `state`, `deadline_at`, `deadline_timezone`, `deadline_ref`, `dependencies`, `next_checkpoint`, `owning_note`, `source_template`. Use `null` for unverified times; never use zero or midnight as a placeholder. Opening this view never advances time.

</details>
