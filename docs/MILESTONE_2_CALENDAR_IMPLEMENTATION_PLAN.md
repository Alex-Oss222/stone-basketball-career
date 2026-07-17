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

## M2.4 normalized CalendarEntry read model

M2.4 defines one immutable `CalendarEntryViewModel` projection for every
authoritative `ScheduledGame` and `SeasonCalendar` event. The model preserves
namespaced entry identity, exact source identity, source kind, status-aware
placement date, original/current/actual date history, competition stage,
GameDay or calendar-event metadata, real team associations, complete labels,
managed-team context, and a deterministic sort key.

Source mapping is explicit:

- a game becomes `kind: game`, retains its GameId, GameDayId, home/away
  TeamIds, and schedule stage, and uses an `away at home` title plus
  `AWAY @ HOME` abbreviations;
- a league-scoped event becomes `kind: league_event` with no team association;
  and
- a team-scoped event becomes `kind: team_event` with exactly its stored
  TeamId.

Game entry IDs use `game:<GameId>` and event entry IDs use
`calendar-event:<CalendarEventId>`, so equal serialized source text cannot
collide across kinds. Stored event titles are preserved without truncation.
Managed-team markers are true only when a non-null managed TeamId appears in
the authoritative entry team IDs; inspected-team filtering does not change
them.

Placement is status-aware:

- scheduled games use `currentScheduledDate`;
- completed games use `actualDate`;
- postponed games use a replacement/current date or remain undated;
- cancelled games use a retained current date or fall back to their required
  original date;
- estimated, announced, and scheduled events use `scheduledDate`;
- completed events use `actualDate`;
- postponed events use a replacement/current date or remain undated;
- TBA events remain undated; and
- cancelled events use a retained scheduled date, then an authoritative
  original date, or remain undated.

No placement rule overwrites the separately retained original, current
scheduled, or actual dates. Status is mapped exhaustively from the source and
is never inferred from date presence.

The deterministic order is dated before undated, then canonical LocalDate,
then league event, managed-team game, other game, managed-team team event,
other team event, and finally namespaced entry ID. The final unique tie-breaker
means ordering never depends on input indexes or sort stability.

Pure selectors partition dated and undated entries; select by LocalDate,
YearMonth, or TeamId; select managed-team entries; group dated entries by
LocalDate; and create an ordered day agenda. All return new frozen
collections. Undated entries are never assigned to a placeholder date.

CalendarEntry data is derived application data. It is not part of
`LeagueSnapshotV2`, does not increment league revision, and imports no React,
persistence, generation, browser, or random source.

## M2.5 enriched calendar-grid and selected-day agenda models

M2.5 combines the twelve structural month grids with normalized calendar
entries and explicit transient presentation inputs. The enriched immutable
day, week, month, and league-year models preserve every M2.3 date and weekday
while attaching entries only by their M2.4 placement `LocalDate`.

Calendar scope is closed to `managed_team` and `all_teams`. `all_teams`
retains every normalized entry. `managed_team` retains managed-team entries
and league-wide events while excluding unrelated games and team events; it is
rejected when no managed-team context exists and never falls back to
`all_teams`.

Every enriched day compares its real date with the supplied authoritative
`currentDate`, so exactly one of current, past, or future is true without
consulting the system clock. A nullable explicit `selectedDate` controls the
single owning-month selected cell and its full selected-day agenda; the
builder never selects the current date implicitly.

An explicit positive safe-integer visible-entry limit splits each day's
ordered entries into a visible prefix and an exact overflow remainder. The two
frozen collections partition the full day without loss, duplication, or
truncation. Month summaries count only entries on cells belonging to that
displayed month, so adjacent-month padding cannot inflate either month.

Undated entries remain in a separate honest model with game, league-event,
team-event, and managed-team projections; no synthetic date is assigned.
Dated entries outside the July-through-June display range remain in a
separate immutable out-of-range collection. An exact-date padding cell may
show such an entry for continuity, but authoritative completeness counts come
from the disjoint in-range, undated, and out-of-range collections rather than
from repeated padding cells.

All enriched records, tuples, collections, agenda partitions, and entry
projections are frozen. They are derived application data, are never stored in
`LeagueSnapshotV2`, and do not change league revision or authoritative source
entities.

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

The pure `src/app/calendarViewModel.ts` module normalizes validated live-domain
League, LeagueSchedule, and SeasonCalendar entities without losing source
identity, original/current/actual date history, status, scope, participants,
calendar-event kind, or GameDay metadata. It exposes the frozen entry builder,
dated/undated, date, month, team, and managed-team selectors, chronological
date grouping, and day-agenda selection described above.

Cross-reference checks reject foreign teams, wrong league or season
references, self-matchups, duplicate source IDs, invalid GameDay membership,
and merged entry-ID collisions. Current sources never manufacture TBD
opponents, date windows, or neutral-site claims. Normalization and selection
do not import or rerun generation.

### 4. Enriched month-grid read models (M2.5)

The pure enriched models implement the M2.5 contract above without mutating
the range, structural grids, or normalized entries. They preserve all twelve
months, zero or variable entries per date, multiple GameDays on one date,
event/game coexistence, selected-day completeness, explicit overflow, and
honest undated and out-of-range entries without a four-game assumption.

M2.5 remains application-only: no React rendering, routing, persistence,
schedule generation, results, or simulation.

### 5. Team Schedule and game-details read models (M2.6)

Implement only pure Team Schedule month-grouping and shared game-details read
models. Introduce explicit inspected-team context that remains distinct from
the managed team, preserve normalized entry identity, ordering, status, and
date history, and derive schedule-only details without scores or results.
M2.6 remains React-free and does not add routing, persistence, simulation, or
authoritative schedule changes.

### 6. Continuous month-grid Calendar

Refactor `ScheduleCalendarContent`, optionally behind a re-export from the
existing schedule-pages module. Render every July-through-June month, including
empty months, as the semantic sections and tables required by ADR 0002. Date
buttons show concise authoritative entry counts and accessible managed-team
markers. TBA entries are not forced into a date cell. Keep the existing page
ID and do not display results.

### 7. Selected-day Agenda using the slate

Add Calendar/Agenda presentation using the same selected date and complete
`CalendarDaySlate`. Initialize selection explicitly from stored
`Season.currentDate` when it is in range, otherwise from the range start.
Render all events and games for that date, or honest empty-day copy. Date
selection is UI state only and never advances the stored season. Test native
button selection, accessible selected-state text, full and empty slates, TBA
handling, managed-team markers, and event/game coexistence.

### 8. Month-grouped Team Schedule

Refactor `TeamScheduleContent` to consume the shared normalized entries and
display range. Preserve all/home/away filters and current 28/14/14 totals while
grouping visible games by month. Omit empty month tables on the team page; keep
them on the continuous league calendar. Put future undated team games in an
explicit TBA section. Preserve stable order, status, and date history.

### 9. Shared game-details surface

Add one schedule-only details component used by both the Agenda and Team
Schedule, with its pure selector in the calendar view model. Show GameId,
participants and location, season/GameDay context, meeting and status, and
separate original/current/actual dates with honest null/TBA labels. Show no
score, winner, or box score. Choose and test an accessible inline region or a
complete dialog focus model; do not add partial dialog semantics.

### 10. UI-preference separation

Define a pure UI state type/reducer, preferably in
`src/ui/scheduleUiState.ts`, for Calendar/Agenda mode, scope, density, selected
date, inspected team, opened game, and filters. Prove reducer changes do not
mutate the snapshot. Do not add DTO fields, repository calls, revision changes,
or preference persistence. Keep inspected and managed team identities
distinct.

### 11. Accessibility and responsive verification

Automate checks for headings, captions, scoped headers, native controls,
selected/current date labels, visible non-color markers, TBA and empty states,
focus styles, and the absence of unsupported `role="grid"`. Verify
keyboard-only selection and details focus behavior manually. Test narrow
windows, zoom/reflow, high contrast, reduced motion, and table overflow or
semantic narrow-screen alternatives. Add no dependency unless separately
approved.

### 12. Definition of Done

Milestone 2 calendar work is complete only when:

- the explicit July 1–June 30 range is independent of schedule endpoints;
- all twelve current-season months render continuously;
- date slates use the documented status-aware placement `LocalDate`, never
  GameDay grouping, and never assume four games;
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
