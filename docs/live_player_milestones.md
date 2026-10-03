# Live player milestones

[Open Wade's career desk](../career/Dwyane_Wade/Milestones/README.md) · [Calendar](../career/Dwyane_Wade/Milestones/calendar.md) · [Full working templates](templates/player_milestones/README.md)

The nine detailed screens live inside the career and feed the browser's `/career` view. Visit the season, Free Agency, Offseason, Training Camp, Draft or Team folder to find the relevant pages. Statistics and milestones share the canonical player record and red-and-black styling. Working records and replies appear in both the interactive screens and their complete Markdown versions.

At the June 26, 2003 checkpoint the pages are available, but Wade is still unsigned, with no offer, training block, camp assessment or closed NBA game. A future calendar reference is not a live offer or appointment.

## What is connected

| Page | Live evidence | What refreshes it |
| --- | --- | --- |
| Calendar | Current date, pending decisions, consultations, working events and season calendar | Every rebuild or supported event boundary |
| Contract checkpoint | Contract/control ledger; separate draft holds, signed salary and conditional options | Actual signing / contract record changes |
| Contract desk | Rookie negotiation log, communicated terms and player replies | Offer opener, free-agency driver and player replies |
| Free-agency board | Actual control, dated requests and market working records | Dated eligibility, contact and offer records |
| Training plan | Player focus, staff plan, sessions and reviews | Working event and reply commands |
| Trade updates | Completed transactions and franchise consultations | Trade CLI, free-agency driver and consultation replies |
| Exit meeting | Season-close record, separate season statistics and meeting | Season closure and dated meeting record |
| Camp / role review | Actual Wade assessment and dated staff rotation | Camp driver and later role conversations |
| Stats review | Canonical closed games, coverage and all period reports | Player report rebuild; declared canonical results only |

`python scripts/update_player_reports.py` rebuilds both statistics and milestone views. `--check` checks both without writes. Repository validation checks source validity, freshness and live-page links. GitHub's results-collection workflow also rebuilds the pages. Raw collected results do not become played games just because the reports refresh.

The free-agency, camp, trade, June 30 and offer-opening CLIs refresh the desk after their completed writes; player replies do too. The hooks never initiate a run or change its stopping rules. Direct low-level Python writes, standalone standing updates and manual edits must finish with the report rebuild. Working records extend the detailed screens; they never replace existing training-plan, camp, trade or contract evidence.

## Using a page during play

1. Read the current desk and owning event. Present its actual choice and next checkpoint.
2. Record the user's authorized words in the owning career note, dated on the career clock. That file is the reply's evidence.
3. Use the reply command with the version of the offer, consultation or registry that was actually read.
4. Show the updated page. The supported club/engine workflow still owns execution: an answer alone never creates a signing, trade, assignment or ability gain.

No player decision was entered by activating these screens. The player can answer in ordinary conversation; the agent records it through this path. This repository view is not an authenticated web form.

## Record a working event

Use an event for an actual development block, exit meeting, market meeting, role review, contract-status appointment or period review. The full template remains linked on every live page. File the completed document or session evidence in the owning phase/week, then reference it here. Keep practice protocols and staff observations in that source; the screen summarizes the useful fields.

`career/Dwyane_Wade/milestones.json` holds append-only events. IDs are unique; a later review is a new event linked to the earlier source. Club/engine source files retain their authority. Never copy illustrative examples into this register.

For an agreed plan, completed block, revised appointment or later review, append a new dated event with `supersedes` set to the previous event ID in the same area and season. Use its actual new status and owner. The old record remains history, stops asking for a response and no longer creates a calendar conflict; its successor becomes the current working record. Close a block with a sourced successor whose status is `closed` and `needs_response` is false.

Input format below uses documentation placeholders and is not a recorded event:

```json
{
  "id": "unique-dated-slug",
  "season": "2003-04",
  "kind": "training",
  "title": "Actual block or appointment title",
  "recorded_on": "CURRENT_CAREER_DATE",
  "status": "planned",
  "owner": "player",
  "needs_response": true,
  "source_ref": "career/Dwyane_Wade/2003-04/03_Offseason/ACTUAL_RECORD.md",
  "prompt": "Which primary basketball focus do you want?",
  "details": {
    "Player focus": "Awaiting your choice",
    "Staff plan and availability": "What staff actually communicated",
    "Baseline and protocol": "Recorded measure, sample and source",
    "Planned / completed sessions": "Keep planned and completed work separate"
  },
  "next_checkpoint": {"date": null, "trigger": "Staff confirm the focus and review appointment"}
}
```

`kind`: `calendar`, `checkpoint`, `contract`, `market`, `training`, `trade`, `exit`, `camp` or `stats`. `status`: `planned`, `active`, `review` or `closed`. `owner`: `player`, `club`, `staff` or `none`. Only an open player-owned event can require a reply. Optional `starts_on` and `ends_on` dates describe actual planned commitments; future dates are allowed. The recording date cannot exceed the career clock. Overlapping commitments appear on the calendar; nothing silently reschedules them.

```sh
python scripts/player_milestone.py --version
python scripts/player_milestone.py --record-event /path/to/event.json --expected-version TOKEN
```

The whole candidate is validated before saving. The command refreshes the pages; it does not run training. A player's reply cannot assign a coaching role, grant medical clearance or establish contract legality. Recording a preference does not automatically close its staff follow-up or unblock an unrelated engine decision.

## Record the player's reply

Build this input from the user's actual instruction:

```json
{
  "season": "2003-04",
  "date": "CURRENT_CAREER_DATE",
  "kind": "working_record",
  "event_id": "EXACT_EVENT_ID",
  "action": "record",
  "text": "The player's actual authorized reply",
  "source_ref": "career/Dwyane_Wade/2003-04/03_Offseason/ACTUAL_DECISION_NOTE.md"
}
```

```sh
python scripts/player_milestone.py --reply /path/to/reply.json --expected-version CURRENT_TOKEN
```

| Kind | Actions | Version to use | Consequence |
| --- | --- | --- | --- |
| `rookie_contract` | `accept`, `counter`, `decline`, `request` | Contract desk token | Appends Wade's entry to the rookie log. Counter needs numeric `percent_of_scale` within 80–120; accept uses exactly the latest club terms |
| `consultation` | `approve`, `object` | Token beside the exact consultation ID | Records the answer, clears that pending consultation and lets the existing franchise rule consume it |
| `working_record` | `record` | Registry `--version` | Saves the preference and shows the next staff/club follow-up |

Replies refuse an old version, wrong clock date, missing career evidence, closed record or repeated answer. A new review needs its own event. Demo state and browser-local choices are never evidence.

The rookie adapter covers the 2003 opening. Later veteran negotiations, extensions, options and RFA execution require their supported era-specific path and authenticated evidence in [the contract engine guide](contract_negotiation_engine.md). Live pages can hold dated working records without claiming unfinished execution paths are available. Training records work and review; training-driven ability changes remain unfinished. See [the roadmap](ROADMAP.md).
