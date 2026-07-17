# ADR 0005: ScheduledGame versus GameResult

- Status: Accepted
- Date: 2026-07-16

## Context

The current schedule stores lifecycle and date history but intentionally has
no score, winner, or box score. Treating `status: completed` as a result would
fabricate information and blur schedule placement with simulation output.

## Decision

`ScheduledGame` continues to own:

- stable GameId and season/GameDay references;
- stage, participants, and opponent-pair meeting number;
- original and current scheduled dates;
- optional actual date; and
- scheduled, postponed, completed, or cancelled status.

A future immutable `GameResult` is a separate aggregate linked to exactly one
`GameId`. It owns score, winner, period totals, player and team box scores,
simulation/RNG versions, derived game seed, and input fingerprint. Outcome
fields are never embedded in `ScheduledGame`, and a UI never infers them from
schedule status.

Future result commitment should atomically validate and store one immutable
result with the corresponding schedule lifecycle update. That behavior is not
implemented by this task.

## Compatibility and consequences

- Current schedule entities and V2 date-history fields remain authoritative.
- Read-only details show schedule facts and an honest absence of a result.
- The exact closed `LeagueSnapshotV2` cannot store results. A future V3 or
  full-season envelope and migration are required before results persist.
- Existing game identity remains the link; no result-specific replacement ID
  is created for the scheduled game.

## Non-goals

This ADR does not implement simulation, result commitment, scores, standings,
statistics, or resimulation.
