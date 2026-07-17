# M2.1 Calendar Contract Audit and Characterization

- Status: Complete
- Audit date: 2026-07-16
- Scope: authoritative contracts and read-only presentation behavior only

## Audit result

The current persistence, identity, `LocalDate`, season, schedule, and
no-regeneration contracts are compatible with the proposed Calendar work and
must not be weakened. The future Calendar can be built as a pure projection of
the restored `LeagueSnapshotV2`.

There are, however, presentation gaps that later M2 tasks must address:

1. The page called Calendar currently renders one slate per stored `GameDay`.
   It does not render `SeasonCalendar.events` and does not group games by their
   current scheduled `LocalDate`.
2. There is no shared normalized calendar-entry or date-slate selector.
3. There is no explicit league-year display range.
4. The application has a persisted managed team but no separate inspected-team
   UI state.
5. Navigation uses stable typed IDs but has no URL parser, serializer, browser
   history integration, or direct-link restoration.

These are acknowledged implementation gaps, not reasons to alter V2 or the
domain. M2.1 makes no production behavior or validator change.

## Authoritative contract inventory

### 1. LeagueSnapshotV2 and strict parsing

- `src/persistence/leagueSnapshotV2.ts` owns every explicit serialized V2 DTO,
  the exact top-level and nested key sets, `serializeLeagueSnapshotV2`, and
  `parseLeagueSnapshotV2`.
- `src/persistence/strictSerializedValue.ts` owns the JSON-safe boundary. It
  rejects non-plain records, accessors, sparse or augmented arrays,
  `undefined`, functions, symbols, `Date`, `Map`, `Set`, non-finite numbers,
  negative zero, and other values that cannot round-trip as exact JSON data.
- `src/persistence/supportedScheduleRuleSets.ts` resolves the stored
  `(ScheduleRuleSetId, version)` pair. Restoration does not substitute a newer
  rule set.
- V2 parsing reconstructs and validates league, season, calendar,
  team-season, opponent-requirement, GameDay, and game values; then checks
  cross-object IDs, team ownership, rule metadata, schedule invariants, date
  spacing, and opening/conclusion events. It returns a detached DTO and does
  not repair, normalize, reorder, or regenerate stored schedule data.
- V2 is closed. Navigation, filters, selected date, inspected team, view
  density, results, scores, grades, and other derived view models are not part
  of it.

`leagueSnapshotV2.ts` imports stable identity derivation and configuration
parsing from `createSeasonFoundation`, but its normal parser does not call the
coordinator or any generator. Existing no-regeneration tests freeze that
distinction.

### 2. IndexedDB repository and restoration

- `src/persistence/leagueSnapshotRepository.ts` owns the browser-independent
  storage transaction interface, V2-over-V1 precedence, restoration result
  union, revision checks, update/clear behavior, migration composition, and
  structured recovery errors.
- `src/persistence/indexedDbLeagueSnapshotStorage.ts` is the native IndexedDB
  adapter. It uses database `stone-basketball-gm`, version `1`, object store
  `activeLeague`, V1 key `current`, and authoritative V2 key `current-v2`.
  Both records are read together; writes and clears use one read-write
  prepare/mutate/reread/verify/commit transaction.
- A present valid V2 restores as `restored-v2`. An invalid authoritative V2
  produces `recovery-required` and never falls back to V1. V1 is considered
  only when V2 is absent and yields `migration-required`; neither version
  yields `empty`.
- `src/App.tsx` creates one repository, starts restoration in
  `restoreInitialSnapshot`, and installs a successful V2 as one atomic
  `snapshot` state value. Rendering receives that same object; schedule parts
  are not loaded independently.
- Returning to the main menu changes only `activePageId` and `setupView`.
  It does not clear, revise, or replace the restored snapshot.

### 3. LocalDate parsing and arithmetic

`src/domain/localDate.ts` owns the branded timezone-free `LocalDate` contract:

- exact `YYYY-MM-DD` parsing for proleptic Gregorian years `0000`–`9999`;
- rejection of malformed and impossible dates;
- deterministic lexical comparison after validation;
- whole-day `addDays` using ordinal calendar arithmetic, without JavaScript
  `Date`, timestamps, UTC, locale, or timezone conversion;
- calendar-year extraction; and
- the cross-year season display-label rule.

It currently has no calendar-month value, month enumeration, or weekday-offset
API. Those are the exact subject of M2.2.

### 4. Season and schedule domain

- `src/domain/season.ts` owns broad season phase/status vocabulary, season
  year and label consistency, current `LocalDate`, and the linked `ScheduleId`.
- `src/domain/seasonCalendar.ts` owns versioned `SeasonCalendar` and
  `CalendarEvent` records, event kinds, league/team scope, completion state,
  and distinct original/current scheduled/actual dates. A TBA event can remain
  undated; a date is never silently invented.
- `src/domain/teamSeason.ts` owns one team's competitive state for one season.
  It keeps elimination and team-offseason dates separate from league-wide
  calendar events.
- `src/domain/schedule.ts` owns generic rule sets, canonical opponent
  requirements, `LeagueSchedule`, `GameDay`, `ScheduledGame`, lifecycle
  statuses, supported constraint shapes, and diagnostic types.
- `src/domain/scheduleValidation.ts` aggregates reference, count, balance,
  identity, ordering, spacing, and lifecycle violations. The current rule pack
  validly enforces 28 GameDays with four games per GameDay; that generator rule
  is not a generic presentation assumption.
- `src/generation/generateSchedule.ts` owns deterministic placement and stable
  Game/GameDay identity. It is not a presentation dependency.

`GameDay.scheduledDate` is the original generation-group date. A
`ScheduledGame` separately retains `originalScheduledDate`, nullable
`currentScheduledDate`, and nullable/optional `actualDate`. Future Calendar
grouping must use a concrete current scheduled date, not the GameDay date or
the actual completion date.

### 5. Existing selectors and view-model helpers

`src/app/scheduleViewModel.ts` is pure and operates on validated serialized V2
DTOs. It owns:

- team games in stored game-array order;
- opponent and home/away resolution;
- next and upcoming scheduled games using `LocalDate` comparison;
- GameDay grouping in stored GameDay and `gameIds` order;
- managed-team matchup identification;
- home/away totals and the all/home/away filter; and
- deterministic fixed-English LocalDate and phase labels.

The helpers return new arrays or projections and do not sort or mutate the
snapshot. There is no current helper that combines schedule games with
`SeasonCalendar.events`, groups entries by date/month, or models uncertain
future schedule slots.

### 6. Current Team Schedule page

`TeamScheduleContent` in `src/ui/schedulePages.tsx` reads only the restored
snapshot's `managedTeamId`, league, season label, and schedule. It renders the
managed team's stored games in one table with GameDay sequence, current date
or honest TBA, location, real opponent, and schedule status. Its all/home/away
filter is component-local `useState`; it is not persisted and resets when the
component is remounted. A postponed TBA game retains its original date as
additional accessible context.

### 7. Current Calendar/GameDay page

`ScheduleCalendarContent` in `src/ui/schedulePages.tsx` uses
`groupGamesByGameDay` and renders one semantic section/table for each stored
GameDay. It currently shows all four current-rule-pack matchups and explicitly
marks the managed team's game.

It is a GameDay slate, not yet a league-year Calendar:

- it uses `GameDay.scheduledDate` for the section date;
- it does not display or select months or dates;
- it does not include `SeasonCalendar.events`; and
- a future postponed game moved to another current scheduled date would still
  appear under its original GameDay section.

This page is the later presentation replacement point. Its source entities,
stable IDs, date history, generator, and V2 storage remain unchanged.

### 8. Navigation and URL state

`src/app/navigation.ts` is the single typed registry for stable section/page
IDs and availability. `schedule-team-schedule` and `schedule-calendar` are
available; `schedule-results` and `schedule-postseason` remain planned with
honest dependency explanations.

`src/ui/dashboardShell.tsx` renders primary and secondary navigation as native
buttons with `aria-current`. `src/App.tsx` stores `activePageId` in React state
and switches pages through callbacks.

There is no URL-state implementation: no route parser/serializer,
`window.location`, History API, `popstate`, hash handling, or page links.
The navigation test description “URL-stable” currently characterizes only
unique canonical kebab-case IDs, not addressable URLs, refresh persistence, or
back/forward behavior.

### 9. UI-only filters and preferences

Current transient UI state includes:

- `activePageId`, `setupView`, and selected roster player in `src/App.tsx`;
- the Team Schedule all/home/away filter in `src/ui/schedulePages.tsx`; and
- League Players name/position filters in `src/ui/dashboardPages.tsx`.

Calendar/Agenda mode, selected Calendar date, density, inspected team, and
Calendar scope do not exist yet. When introduced, they remain UI preferences
under ADR 0004. The only team selection in V2 is authoritative
`managedTeamId`; changing it is a validated repository update that increments
the league revision.

### 10. Rendering and generation call paths

Normal restored presentation is generation-free:

- `src/app/scheduleViewModel.ts`, `src/ui/schedulePages.tsx`,
  `src/ui/dashboardPages.tsx`, and `src/ui/dashboardShell.tsx` import no league
  or schedule generator;
- V2 parser and repository restoration validate stored entities in place; and
- existing architectural tests replace foundation, league, schedule,
  opponent-matrix, and RNG modules with throwing mocks while rendering the
  schedule surfaces.

Generation is reachable only through explicit creation/migration workflows:

- `src/app/commands/createNewLeagueSnapshotV2.ts` calls league generation and
  `createSeasonFoundation` for a new league;
- `src/persistence/migrations/migrateLeagueSnapshotV1ToV2.ts` calls the
  coordinator only for explicit V1 migration; and
- `src/app/commands/createSeasonFoundation.ts` calls schedule generation while
  constructing and validating a new foundation.

`src/App.tsx` statically imports the creation command because creation and
restoration currently share one module. Importing the whole App therefore
loads that dependency graph, but the `restored-v2` branch does not call it.
The leaf presentation modules are independently proven generation-free.

## Conflicts and resolutions frozen by M2.1

| Finding | Resolution |
| --- | --- |
| Current Calendar groups by GameDay; M2 requires date/month presentation. | Keep GameDay authoritative for generation; add a derived LocalDate projection later under ADR 0003. |
| Current Calendar omits `SeasonCalendar.events`. | Preserve those events exactly now; normalize them with games only in the later shared `CalendarEntry` task. |
| No authoritative display range is stored. | Derive July 1 of `startingYear` through June 30 of `endingYear` from stored Season years under ADR 0001, never from schedule endpoints. |
| A GameDay has four games today. | Preserve the current rule invariant, but forbid generic UI selectors from assuming four games on a concrete date. |
| Managed team exists; inspected team does not. | Add inspected team only as future UI state. Never reuse the managed-team repository update for inspection. |
| Stable page IDs exist but URLs do not. | Treat current page selection as transient. Any later URL adapter remains outside V2 and league revision state. |
| V2 has known teams/dates while future slots may be uncertain. | Do not migrate V2 now. Use a future-tolerant presentation boundary under ADR 0006. |
| Schedule status can become completed without stored outcome data. | Keep future immutable `GameResult` separate under ADR 0005; never infer scores or winners. |
| Whole-App imports can load creation code. | Freeze the stronger behavioral rule—restored parsing and rendering make no generation calls—and keep leaf presentation imports generation-free. |

No conflict requires a domain, stable-ID, parser, validator, repository, or
snapshot-schema change in M2.1.

## Characterization coverage

### Existing coverage reused

- `tests/persistence/leagueSnapshotV2.noRegeneration.test.ts` proves strict V2
  parsing does not call foundation, schedule, opponent-matrix, league, or RNG
  generation.
- `tests/persistence/leagueSnapshotV2Repository.noRegeneration.test.ts` proves
  authoritative V2 restoration does not migrate, regenerate, or write.
- `tests/ui/schedulePages.noRegeneration.test.tsx` proves schedule/dashboard/
  header presentation imports and rendering are generation-free and that
  restoration preserves SeasonId, ScheduleId, GameIds, GameDayIds, opponent
  requirements, event records, game order, and every stored date field.
- `tests/generation/generateSchedule.test.ts`,
  `tests/domain/scheduleValidation.test.ts`,
  `tests/ui/schedulePages.test.tsx`, and
  `tests/ui/dashboardPages.test.tsx` already prove the authoritative 112-game,
  28-GameDay, four-games-per-GameDay, 28-team-game, and 14/14 home/away shape.
- `tests/domain/seasonCalendar.test.ts` already proves an explicit TBA event
  receives no invented date and that original/current/actual dates remain
  separate.
- `tests/persistence/leagueSnapshotV2.test.ts` already proves exact V2 keys,
  JSON round-trip behavior, event preservation, future pending-TBA handling,
  and rejection of additional UI-like fields.
- `tests/app/navigation.test.ts` already proves central unique stable IDs and
  availability; `tests/ui/dashboardShell.test.tsx` proves native navigation
  and main-menu controls.

### Focused M2.1 coverage added

`tests/app/calendarContract.characterization.test.ts` adds only previously
implicit full-fixture guarantees:

- selecting any inspected team's schedule preserves stored GameId/GameDayId
  order, resolves every opponent, and does not change `managedTeamId`;
- GameDay slate flattening is an exact one-time permutation of all stored
  games and returns their unchanged identity and original/current/actual date
  history;
- the authoritative SeasonCalendar event collection remains complete and
  unchanged beside the current GameDay slate projection; and
- main-menu/page/filter/date/inspection choices remain transient, do not enter
  V2, do not increment revision, and leave all restored schedule identities,
  order, and dates unchanged when the league is reopened.

There is intentionally no test claiming that the current Calendar UI displays
SeasonCalendar events or that an inspected-team UI already exists. Those would
be false. Domain/persistence coverage freezes the event facts now; the shared
entry selector and inspected-team state are later plan steps.

## M2.2 exact proposed scope: pure calendar math

M2.2 should implement only a pure `CalendarMonth`/year-month foundation and
tests, with no React, schedule, persistence, or V2 change. Its exact API scope
is:

1. strict canonical `YYYY-MM` parsing for supported `LocalDate` years;
2. derive a `CalendarMonth` from `LocalDate`;
3. compare two months deterministically;
4. add a safe integer number of whole months with explicit range rejection;
5. obtain the first and last `LocalDate` of a month;
6. obtain month length with Gregorian leap-year behavior;
7. calculate a deterministic Sunday-first weekday-cell offset without
   JavaScript `Date`; and
8. enumerate an inclusive month range in canonical order without mutation.

Tests should cover valid and malformed values, leap years, ordinary and
century year boundaries, `0000`/`9999` bounds, negative and fractional
offsets, deterministic weekday vectors, and no timezone/locale dependence.
`LeagueYearDisplayRange`, normalized `CalendarEntry`, date grouping, UI state,
and Calendar rendering begin only after this foundation.
