# ADR 0004: League truth versus UI preferences

- Status: Accepted
- Date: 2026-07-16

## Context

`LeagueSnapshotV2` is an exact, validated persistence contract. Calendar
navigation and presentation choices do not change the basketball league and
must not create save revisions.

## Decision

League truth consists of the validated league, season, season calendar,
team-season records, schedule, opponent requirements, GameDays, games, and
their stored identities, dates, and statuses.

The following are UI preferences outside league truth:

- Calendar or Agenda view;
- league, managed-team, or inspected-team scope;
- compact or comfortable density;
- selected date;
- inspected team and opened game; and
- display filters such as all, home, or away.

These values live in React/component or pure UI-reducer state. They are not
added to domain objects, creation metadata, `LeagueSnapshotV2`, or repository
mutation inputs. Changing them does not call IndexedDB, increment `revision`,
autosave, change `managedTeamId`, or advance `Season.currentDate`.

An inspected team is presentation context and is distinct from the controlled
team. A selected date may initially derive from the stored current date, but
subsequent selection remains a preference.

## Compatibility and consequences

- The closed V2 parser and current restoration flow remain unchanged.
- Preferences may reset on reload in this task.
- Any later preference persistence requires a separate versioned storage
  contract whose failure cannot block or mutate league restoration.
- Returning to the main menu continues to affect navigation only.

## Non-goals

This ADR does not add routing persistence, multiple users, or a second source
of league state.
