# ADR 0001: League-year display range

- Status: Accepted
- Date: 2026-07-16

## Context

The stored season has authoritative starting and ending years, while the
current regular-season games occupy only part of that cross-year period. A
calendar derived from its first and last game would hide empty offseason
months and would change shape when schedule placement changes.

## Decision

Define a derived `LeagueYearDisplayRange` whose inclusive bounds are:

- July 1 of `Season.startingYear`; and
- June 30 of `Season.endingYear`.

The current season foundation always has adjacent years, so its display range
contains twelve continuous months. The range depends only on authoritative
season-year fields. It never depends on a game, `GameDay`, calendar event,
schedule seed, current date, or result.

A future versioned league rule may provide an authoritative equivalent display
range. Only such an explicit rule contract may override the July-through-June
default. Schedule contents and UI heuristics may not.

`LeagueYearDisplayRange` is an in-memory projection made from `LocalDate`
values. It is not added to `Season`, stable-ID derivation, creation metadata,
or `LeagueSnapshotV2`.

## Compatibility and consequences

- Existing season identity, year values, label, and V2 validation are
  unchanged.
- Empty months remain visible and schedule changes cannot resize the calendar.
- Month enumeration must use pure calendar arithmetic without JavaScript
  `Date`, UTC, locale, or timezone conversion.
- Invalid or unsupported season-year combinations are rejected rather than
  clamped or repaired.

## Non-goals

This decision does not define offseason behavior, advance `Season.currentDate`,
or assign dates to unknown events.
