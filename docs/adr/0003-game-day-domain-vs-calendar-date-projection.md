# ADR 0003: GameDay ownership versus calendar-date projection

- Status: Accepted
- Date: 2026-07-16

## Context

`GameDay` is a stable schedule-generation grouping and validation reference.
The current rule pack happens to place four games on each of 28 GameDays.
Future postponements or rule packs may place games from multiple GameDays on
one visible date or leave a date with any number of games.

## Decision

Keep `GameDay` responsible for generation grouping, sequence, stable identity,
original placement date, and its ordered game-ID references. Do not change its
identity or its relationship to `ScheduledGame`.

Presentation normalizes authoritative records and groups them by a concrete
`LocalDate`, not by `GameDay`. For schedule views, a game's presentation date
is its non-null `currentScheduledDate`. This wording does not mean the separate
`actualDate`, which remains preserved for future historical and result views.
A calendar event uses its current `scheduledDate`.

Entries on the same date are merged into one date slate even when they came
from different GameDays. No presentation selector may assume four games on a
date. Undated entries remain in a separate TBA collection and are never given
a placeholder date.

## Compatibility and consequences

- Current generator and validator invariants of four games per GameDay remain
  valid for the Milestone 1 rule pack.
- Existing stable GameDay IDs, game references, stored order, and date history
  are unchanged.
- `groupGamesByGameDay` remains useful for placement inspection and reference
  validation, but it no longer drives the month calendar.
- The current GameDay-section calendar must be replaced at presentation level;
  domain generation and persistence are not redesigned.

## Non-goals

This ADR does not reschedule postponed games, change game status, or reinterpret
an actual completion date as a scheduled date.
