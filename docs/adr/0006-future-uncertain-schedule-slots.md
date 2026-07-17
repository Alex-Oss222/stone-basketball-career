# ADR 0006: Future uncertain schedule slots

- Status: Accepted
- Date: 2026-07-16

## Context

The current rule pack requires two known teams, a generated GameDay date, and
no TBD opponents. Future competition formats may contain TBA dates or
opponents, date windows, or neutral sites. Adding speculative persistence
fields now would weaken the exact V2 contract without an authoritative domain
model to validate them.

## Decision

Do not migrate current schedule entities or `LeagueSnapshotV2`. Define the
normalized presentation boundary as a discriminated, future-tolerant
`CalendarEntry`. It can express:

- a known `LocalDate` or undated/TBA state;
- known or TBD participants;
- an optional earliest/latest date window; and
- ordinary home/away or neutral-site context.

The current V2 adapter emits only shapes supported by today's authoritative
data. It does not manufacture uncertain slots. Selectors collect undated
entries instead of throwing or assigning a fake day, label unknown opponents
as TBA, and avoid home/away claims for a neutral site. Stable source IDs remain
the identity; dates and array indexes do not become substitute IDs.

## Compatibility and consequences

- Today's `GameDay` date, required TeamIds, no-TBD rule, generator, validator,
  and V2 schema remain unchanged.
- `SeasonCalendar` already demonstrates a valid undated TBA event and can be
  normalized without inventing a date.
- Presentation types will not block a future versioned adapter, but they do not
  claim current persistence supports uncertain games.
- Authoritative TBD opponents, date windows, or neutral sites later require
  explicit domain, rule-set, persistence, and validation versions.

## Non-goals

This ADR does not add placeholder teams, venues, migration fields, or a
schedule optimizer.
