# Stone Basketball GM — Milestone 2 Calendar Implementation Plan

## Scope

Milestone 2 turns the authoritative stored season and schedule into a
continuous league-year calendar, selected-day agenda, month-grouped team
schedule, and shared schedule-only game details. It remains read-only.

The frozen implementation baseline is recorded in the
[M2.1 Calendar contract audit](CALENDAR_CONTRACT_AUDIT.md).

The governing decisions are:

- [ADR 0001](adr/0001-league-year-display-range.md)
- [ADR 0002](adr/0002-calendar-accessibility-semantics.md)
- [ADR 0003](adr/0003-game-day-domain-vs-calendar-date-projection.md)
- [ADR 0004](adr/0004-league-truth-vs-ui-preferences.md)
- [ADR 0005](adr/0005-scheduled-game-vs-game-result.md)
- [ADR 0006](adr/0006-future-uncertain-schedule-slots.md)

This plan does not implement season advancement, schedule editing,
postponement rescheduling, simulation, results, scores, standings, statistics,
postseason, or a V2 schema/repository migration.

## Current contracts to preserve

- `LocalDate` remains timezone-free and no calendar code uses JavaScript
  `Date`.
- Season, calendar, team-season, schedule, GameDay, and game IDs and their
  derivation inputs remain unchanged.
- The current rule still has 8 teams, 28 games per team, 28 GameDays, and 112
  games, but presentation selectors do not generalize the four-games-per-day
  coincidence.
- Original, current scheduled, and actual dates stay separate.
- `LeagueSnapshotV2` remains exact and authoritative; read-only presentation
  never regenerates or persists league data.
- Stable page IDs `schedule-calendar`, `schedule-team-schedule`, and
  `league-overview` remain unchanged.

## M2.2 YearMonth foundation

M2.2 defines a branded, immutable `YearMonth` string in exact `YYYY-MM`
format. Its supported range is `0000-01` through `9999-12`, matching
`LocalDate` years. Parsing never trims, pads, clamps, or corrects input.

Pure month arithmetic accepts only safe integer offsets, supports movement in
either direction, and rejects any result before `0000-01` or after
`9999-12`. Month lengths and boundary dates remain governed by the existing
proleptic-Gregorian `LocalDate` rules, including leap year `0000`.

Weekday indexes use the fixed Sunday-first convention: Sunday is `0`, Monday
is `1`, through Saturday as `6`. The calculation is independent of JavaScript
`Date`, timestamps, locale, timezone, and the system clock.

## M2.3 League-year range and structural month grids

M2.3 consumes the YearMonth primitives in two pure application read-model
modules:

- `LeagueYearDisplayRange` derives the authoritative Season's July 1 through
  June 30 display boundary and all twelve ordered months.
- `CalendarMonthGridModel` supplies complete Sunday-first week rows with seven
  real `LocalDate` cells each, including leading and trailing adjacent-month
  dates.

The earliest supported complete league year is July 0000 through June 0001.
The latest is July 9998 through June 9999. A grid can be requested only for a
month contained in its supplied valid league-year range; this keeps complete
Sunday-through-Saturday padding inside the existing `LocalDate` bounds.

Month grids contain four, five, or six weeks as required by the first weekday
and month length. `belongsToMonth` means the cell's actual `YearMonth` equals
the grid's requested month. Independently, `isWithinLeagueYear` means the
cell's date lies inclusively between the range's July 1 and June 30 dates.
Consequently, an adjacent-month padding cell may be inside the league year
without belonging to the displayed month.

All range, month, week, tuple, and cell records and collections are frozen.
The full range always retains all twelve months, including months with no
future games or events. These derived structures are not stored in
`LeagueSnapshotV2`.

## Ordered implementation steps

### 1. YearMonth arithmetic (M2.2)

The pure `src/domain/yearMonth.ts` module and
`tests/domain/yearMonth.test.ts` implement the contract above: strict parsing,
month derivation and comparison, bounded whole-month addition, first/last
`LocalDate`, month length, Sunday-first weekday index, and inclusive month
enumeration. They cover leap years, year and century crossings, supported
bounds, invalid offsets, deterministic behavior, and the absence of
JavaScript `Date` or locale APIs.

### 2. Explicit LeagueYearDisplayRange and month-grid models (M2.3)

The pure `src/app/leagueYearDisplayRange.ts` projection derives July 1 through
June 30 solely from the validated Season years and preserves the Season's
authoritative label. It requires adjacent years, enumerates exactly twelve
months, supports league years `0000–01` through `9998–99`, freezes its output,
and remains independent from games, events, schedule seed, and schedule
endpoints.

The pure `src/app/calendarMonthGrid.ts` module builds Sunday-first structural
month grids. Every week contains exactly seven increasing real dates; every
in-month date appears once; leading and trailing cells retain their actual
adjacent `YearMonth`; and the separate `belongsToMonth` and
`isWithinLeagueYear` flags describe month membership and inclusive range
membership. Grids contain four, five, or six weeks, and the full builder
returns all twelve July-through-June grids even when they contain no entries.
No calendar entry, schedule, persistence, browser, or React concern is part of
these models.

### 3. Shared normalized CalendarEntry (M2.4)

Add `src/app/calendarViewModel.ts` and tests. Normalize scheduled games and
season-calendar events into a stable discriminated `CalendarEntry` without
losing source identity, original/current/actual date history, status, scope,
participants, or GameDay metadata. Include future-tolerant uncertain variants
from ADR 0006, while ensuring the current adapter emits only authoritative V2
facts. Add pure selectors that merge authoritative `ScheduledGame` and
`SeasonCalendar` records without React UI, persistence changes, or generation.
Do not duplicate or rerun generation.

### 4. Selectors grouped by date and month

In the calendar view model, add pure selectors that partition dated and TBA
entries, group concrete current scheduled dates, group those date slates by
calendar month, return empty display months, and filter league/managed-team/
inspected-team scopes. Define an explicit deterministic tie order. Test
multiple GameDays on one date, zero or variable games per date, postponement
with original date retained, event/game coexistence, range boundaries,
uncertain entries, non-mutation, and the absence of a four-game assumption.

### 5. Continuous month-grid Calendar

Refactor `ScheduleCalendarContent`, optionally behind a re-export from the
existing schedule-pages module. Render every July-through-June month, including
empty months, as the semantic sections and tables required by ADR 0002. Date
buttons show concise authoritative entry counts and accessible managed-team
markers. TBA entries are not forced into a date cell. Keep the existing page
ID and do not display results.

### 6. Selected-day Agenda using the slate

Add Calendar/Agenda presentation using the same selected date and complete
`CalendarDaySlate`. Initialize selection explicitly from stored
`Season.currentDate` when it is in range, otherwise from the range start.
Render all events and games for that date, or honest empty-day copy. Date
selection is UI state only and never advances the stored season. Test native
button selection, accessible selected-state text, full and empty slates, TBA
handling, managed-team markers, and event/game coexistence.

### 7. Month-grouped Team Schedule

Refactor `TeamScheduleContent` to consume the shared normalized entries and
display range. Preserve all/home/away filters and current 28/14/14 totals while
grouping visible games by month. Omit empty month tables on the team page; keep
them on the continuous league calendar. Put future undated team games in an
explicit TBA section. Preserve stable order, status, and date history.

### 8. Shared game-details surface

Add one schedule-only details component used by both the Agenda and Team
Schedule, with its pure selector in the calendar view model. Show GameId,
participants and location, season/GameDay context, meeting and status, and
separate original/current/actual dates with honest null/TBA labels. Show no
score, winner, or box score. Choose and test an accessible inline region or a
complete dialog focus model; do not add partial dialog semantics.

### 9. UI-preference separation

Define a pure UI state type/reducer, preferably in
`src/ui/scheduleUiState.ts`, for Calendar/Agenda mode, scope, density, selected
date, inspected team, opened game, and filters. Prove reducer changes do not
mutate the snapshot. Do not add DTO fields, repository calls, revision changes,
or preference persistence. Keep inspected and managed team identities
distinct.

### 10. Accessibility and responsive verification

Automate checks for headings, captions, scoped headers, native controls,
selected/current date labels, visible non-color markers, TBA and empty states,
focus styles, and the absence of unsupported `role="grid"`. Verify
keyboard-only selection and details focus behavior manually. Test narrow
windows, zoom/reflow, high contrast, reduced motion, and table overflow or
semantic narrow-screen alternatives. Add no dependency unless separately
approved.

### 11. Definition of Done

Milestone 2 calendar work is complete only when:

- the explicit July 1–June 30 range is independent of schedule endpoints;
- all twelve current-season months render continuously;
- date slates group by current scheduled `LocalDate`, not GameDay or
  `actualDate`, and never assume four games;
- Agenda and Team Schedule share normalized entries and game details;
- the current snapshot still exposes 8 teams, 28 managed-team games split
  14/14, 28 GameDays, and 112 games with identities, order, and date history
  unchanged;
- empty, TBA, and future uncertain projections never fabricate values;
- UI preference changes perform no persistence write or revision update;
- no result, score, standing, simulation, season advancement, schedule
  mutation, V2 migration, or generation call is introduced;
- domain/generation/random remain React- and browser-independent and use no
  `Math.random` or JavaScript `Date`; and
- focused, golden-vector, and no-regeneration tests plus `npm test`,
  `npm run typecheck`, `npm run lint`, `npm run build`, and
  `git diff --check` pass.

## Known integration conflicts

The existing Calendar groups by GameDay and its UI tests assert 28 groups of
four. Milestone 2 replaces those presentation assertions with date/month
slates while preserving generator and domain invariant tests. Existing
`groupGamesByGameDay` remains available for placement/reference work.

Current V2 cannot accept preferences, results, or uncertain schedule fields.
All new ranges, entries, slates, and preferences are derived in memory. A
future authoritative result or uncertain-slot schema requires a separately
versioned persistence task.
