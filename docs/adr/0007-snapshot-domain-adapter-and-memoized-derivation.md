# ADR 0007: Snapshot-to-domain adapter and memoized presentation derivation

- Status: Accepted
- Date: 2026-07-17

## Context

`LeagueSnapshotV2` is the restored persistence contract held in React state.
Its content is a tree of DTOs (`LeagueSnapshotV2LeagueDto`,
`LeagueSnapshotV2LeagueScheduleDto`, `LeagueSnapshotV2ScheduledGameDto`, and so
on). The Milestone 2 read models that the calendar UI consumes are split
across two incompatible conventions:

- `scheduleViewModel` accepts DTO types directly.
- `calendarViewModel` and `teamScheduleViewModel` accept domain types
  (`League`, `LeagueSchedule`, `SeasonCalendar`, `ScheduledGame`) and run
  domain validation such as `assertValidLeague` and `parseSeasonCalendar`.

The two representations are not identical. Domain `ScheduledGame.actualDate` is
optional (`LocalDate | undefined`) while the DTO field is `LocalDate | null`,
and DTOs carry closed persistence fields (`version`, `generatorVersion`) that
domain entities do not. The mapping is therefore a real transform, not a cast.

Separately, the calendar selectors (`createCalendarEntries`,
`getCalendarEntriesForMonth`, `groupCalendarEntriesByDate`, and the rest) each
return a freshly filtered, sorted, and frozen array. `createCalendarEntries`
also performs full validation. Called inline during render — once per month,
per scope, per re-render — this repeats validation and produces new array
identities every time, which defeats `React.memo` and effect-dependency
comparisons even though every call is pure and correct.

Both questions must be answered before any Milestone 2 component is written,
because otherwise the mapping and the derivation leak into the components.

## Decision

### 1. Domain is the read-model currency; one named adapter is the seam

Application read models operate on domain types, not DTOs. A single pure
adapter is the only place a `LeagueSnapshotV2` becomes domain data — the
projected `League`, `LeagueSchedule`, `SeasonCalendar`, `Season`, and
`managedTeamId` needed to build presentation. All DTO-to-domain concerns live
there: `null`/`undefined` normalization (for example `actualDate`), dropping
closed persistence fields, and running the domain validators
(`assertValidLeague`, `parseSeasonCalendar`) exactly once at the boundary.

Components never hand a DTO to a read model. Even where a mapping is currently
close to structural, it passes through the named adapter so that future V2
additions (authoritative results per ADR 0005, uncertain slots per ADR 0006)
and every existing optionality gap have exactly one home. `scheduleViewModel`
is the existing DTO-typed outlier; it is realigned to consume domain types over
time and is not a blocker for this decision.

The adapter validates; it never regenerates, persists, or writes a revision,
consistent with the read-only Milestone 2 scope.

### 2. Derive presentation once per snapshot; select cheaply per preference

Presentation data is derived once per snapshot and passed down, not computed
inline in render. Because `installSnapshot` replaces the snapshot by reference,
the snapshot reference is the natural memo key.

A single derivation point (an `App`-level `useMemo`, or a `useLeagueCalendar`
hook it owns) keyed on the snapshot reference produces, in order: the domain
projection from decision 1, then `createCalendarEntries`, then the derived
display range, twelve month groupings, and day slates. This bundle holds stable
references, so page components may be wrapped in `React.memo` and only re-render
when the snapshot actually changes.

UI-preference changes — selected date, scope, density, inspected team, opened
game, filters, all outside league truth per ADR 0004 — never rebuild or
re-validate this bundle. They re-select from the already-built entries through
cheap memos keyed on `(entries, preference)`. Validation and entry construction
run once per snapshot, never per selector call and never per re-render.

## Compatibility and consequences

- The closed V2 parser, restoration flow, and revision semantics are unchanged;
  the adapter is a read-only projection over an already-validated snapshot.
- Selectors keep returning new frozen collections; stability comes from calling
  them once inside the memoized bundle, not from mutating them to cache.
- `scheduleViewModel` continues to work during the transition; its realignment
  to domain types is incremental and separately committed.
- A domain projection that fails validation surfaces through the workspace error
  boundary rather than blanking the app.
- No memoization library is introduced; React `useMemo` and `React.memo` are
  sufficient at the current 8-team, 112-game scale.

## Non-goals

This ADR does not add cross-snapshot caching, persisted UI preferences, a data
layer, or any change to the V2 schema, and it does not itself implement the
calendar or agenda components — it fixes the boundary they will sit on.
