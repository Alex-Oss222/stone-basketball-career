# Stone Basketball GM — Season and Scheduling Architecture

## Scope

This document defines the generic season, calendar, and scheduling foundation
and the single active Milestone 1 regular-season rule pack. The architecture
can describe future rule packs and calendar events, but it does not implement
their basketball behavior. In particular, it does not add postseason
qualification, Cup play, Play-In games, venue operations, travel, television,
standings, results, or calendar advancement.

No rule, event date, team identity, or formula is taken from a real
professional league. A future NBA-style or custom rule pack would be a new,
explicitly versioned input rather than a special case embedded in the generic
entities.

## Separated domain layers

The foundation keeps seven concerns independent:

1. `Season` owns stable season identity, lifecycle status, broad phase, year
   metadata, current local date, rules version, and schedule identity.
2. `SeasonCalendar` owns detailed dated or TBA league events. Broad season
   phase is not used as a substitute for those events.
3. `TeamSeason` owns a team's competitive lifecycle. Team elimination and team
   offseason dates do not redefine the league-wide season lifecycle.
4. `ScheduleRuleSet` describes versioned structural expectations without
   assuming that every competition is an equal round robin.
5. `OpponentRequirement` records the intended canonical team-pair inventory
   before any dates or game days are assigned.
6. `LeagueSchedule`, `GameDay`, and `ScheduledGame` record the placed schedule.
7. Constraints and validation diagnostics form an optimization boundary. The
   current generator is deterministic and constructive; it is not an arena,
   travel, or broadcast optimizer.

All of these objects are immutable pure TypeScript values. They do not import
React, the DOM, IndexedDB, persistence adapters, wall-clock time, or locale
services.

## Local calendar dates and date certainty

`LocalDate` is a branded canonical `YYYY-MM-DD` value. It has no time or time
zone. Parsing validates the actual Gregorian calendar date, comparisons use
canonical calendar order, and calendar-day arithmetic never exposes a mutable
`Date` object or performs a time-zone conversion.

Season start and end years remain separate integers. A display label may
abbreviate a same-century ending year, so 2026 through 2027 is `2026–27`.
Century crossings remain explicit, so 2099 through 2100 is `2099–2100`.

Calendar events distinguish:

- the original announced or scheduled date;
- the current scheduled date, which may change or return to TBA;
- the actual completion date; and
- a date-status discriminator describing TBA, estimated, announced,
  scheduled, completed, postponed, or cancelled state.

A postponement therefore never overwrites its original date, and an actual
date never silently replaces a scheduled date. Completed events require an
actual date. Scheduled events require a current scheduled date. TBA events may
have none.

The event-kind vocabulary can describe schedule release, training camp,
preseason boundaries, regular-season boundaries, trade deadline, All-Star
break, Cup events, Play-In events, playoff and finals boundaries, team
elimination, team and league offseason starts, draft, and free-agency events.
Most are deliberately absent or TBA in Milestone 1. Their presence in the
vocabulary does not implement the associated system.

## Season and team-season lifecycle

Season broad phases are `offseason`, `training_camp`, `preseason`,
`regular_season`, `postseason`, and `complete`. Lifecycle status is recorded
separately as `planned`, `schedule_ready`, `in_progress`, or `completed`.
Detailed milestones remain calendar events rather than proliferating broad
phases.

A `TeamSeason` is versioned independently and records only team identity,
competitive status (`active`, `eliminated`, or `season_complete`), optional
elimination and team-offseason dates, and an optional future postseason seed.
It does not contain wins, losses, statistics, payroll, qualification state, or
financial data. A team's offseason may begin before the league-wide offseason
event without changing another team's state.

## Initial regular-season composition

The pure application command `createSeasonFoundation` accepts an existing
validated generated league plus an explicit starting year, regular-season
starting `LocalDate`, positive game-day spacing, and canonical schedule seed.
It returns one validated package containing the season, calendar, one active
team-season record per league team, and the generated league schedule. The
command performs no I/O, persistence, clock access, UI work, or league-data
mutation.

The initial calendar contains exactly two events whose dates are known:

- regular-season opening on the supplied start date; and
- regular-season conclusion on the latest date found in the generated games.

Schedule release and every unsupported future milestone remain absent because
their dates are not inputs. The conclusion is read from the generated schedule
rather than reconstructed from a duplicated game-count formula. A derived
conclusion after the season's stored ending year makes the package inconsistent
and is rejected.

The aggregate validator in this command is deliberately creation-time-only: it
requires the pristine deterministic generator output. Later publication,
postponement, completion, and persistence validation belong to lifecycle-aware
validators rather than this initial-package contract.

## Serialized foundation and restoration

`LeagueSnapshotV2` serializes this regular-season foundation as a JSON-safe DTO,
not as an assertion that untrusted records are already live domain entities. It
stores the complete `League`, `Season`, `SeasonCalendar`, ordered
`TeamSeason` collection, `LeagueSchedule`, and the explicit creation metadata:
starting year, regular-season start `LocalDate`, game-day spacing, canonical
schedule seed, rule-set ID, and rule-set version. All schedule IDs, opponent
requirements, game days, games, statuses, meeting numbers, and separate
original/current/actual dates are authoritative stored values.

The DTO boundary uses exact plain records, dense arrays, JSON primitives,
canonical identifier and `LocalDate` strings, and explicit nulls. Parsing first
checks that serialized boundary, then reconstructs detached values through the
existing domain parsers and runs lifecycle-aware component and cross-object
validation. Additional or missing properties, non-plain values, invalid dates,
foreign references, unsupported statuses, and inconsistent audit metadata are
rejected rather than discarded or repaired.

Creation metadata is explanatory but not trusted. Validation proves that its
starting year matches the season; the ending year and display label follow the
existing two-year rules; its opening date matches the calendar; its seed and
spacing match the schedule; its rule identity matches the schedule and season
rules version; each game-day date follows the stored start and spacing; and the
conclusion event matches the latest scheduled regular-season date. It also
rechecks the coordinator-owned season, calendar, team-season, and calendar-event
identity dependencies and the generator-owned schedule identity without
introducing a persistence-specific ID formula.

Regular-season opening and conclusion remain league-scoped. They are the only
dated event kinds supported by this V2 foundation; other recognized future
events may be preserved only as pending, undated TBA records. An unresolved
postponed game therefore keeps the current conclusion date null, while a
cancelled game cannot extend the conclusion.

Normal V2 restoration treats the stored foundation as authoritative. It never
calls `createSeasonFoundation`, the schedule generator, league generation,
opponent-requirement construction, or seeded randomization. The stored opponent
matrix is validated in place against the exact registered rule policy, while
the stored game and game-day arrays retain their order. Therefore later schedule
publication or date-status state is not reset to pristine generator output.

V1-to-V2 migration is deliberately different: V1 has no season foundation, so
the pure migration requires all season-creation inputs explicitly and calls the
existing coordinator once. It stores exactly that result and its actual rule-set
identity, starts at revision 1, validates the V2 DTO, and verifies a
stringify/parse/reparse round trip. It chooses no default season year, date,
spacing, or seed and performs no storage or UI work.

Restoration resolves rule compatibility by exact `(ScheduleRuleSetId, version)`
rather than a “current” alias. Every genuinely registered historical version may
restore with its own immutable rules. Unknown IDs and known IDs with unsupported
versions are structured recovery errors; no schedule is regenerated or
reinterpreted with a newer pack. At present the only registered restoration
rule is the shipped Milestone 1 regular-season rule set version 1.

This serialization and migration boundary does not change IndexedDB keys,
repository read precedence, application state, or React behavior. Those remain
separate integration work.

## Rule sets and opponent requirements

The generic `ScheduleRuleSet` identifies its rule-set ID, version, stage,
supported team-count rule, expected games, home/away totals, game-day shape,
TBD policy, opponent-requirement source, and calendar-spacing bounds. The
opponent source is explicit: a rule pack may use uniform meetings or provide a
non-uniform matrix. Generic schedule entities do not assume equal conferences,
divisions, round robins, or any professional-league formula.

Each `OpponentRequirement` stores a canonically ordered pair, total meetings,
home games for each side, stage, and optional source tag. Canonical ordering
prevents A/B and B/A from becoming separate requirements. The requirement
matrix is constructed and validated before game dates are assigned. Placed
games are then checked against that intended matrix; the final game array is
not treated as the only source of opponent requirements.

### Milestone 1 regular-season rule set

The active rule pack is explicitly versioned and contains:

- exactly 8 teams;
- 28 games per team and 112 games total;
- four meetings for every unordered pair;
- two home and two away meetings for each side of every pair;
- 14 home and 14 away games per team;
- 28 regular-season game days;
- four games per game day;
- exactly one appearance per team on every game day; and
- no TBD opponent slots.

The resulting matrix has 28 pair requirements, one for every combination of
two teams. It is independent of start date, calendar spacing, round ordering,
and publication state.

## Deterministic placement and stable identity

The current generator first sorts validated team IDs, then uses independent
derived seed labels for team permutation, cycle ordering, per-cycle round
ordering, home/away orientation, and stable game identity. It constructs a
seven-round circle-method cycle and places four copies. Paired cycles reverse
home court so every requirement finishes 2–2. Only after the matchup inventory
exists does the generator assign 28 game-day sequence numbers and `LocalDate`
values using the configured start date and whole-day spacing.

Schedule and game-day IDs bind to the canonically sorted participant set, so a
different set of teams cannot reuse identities for different schedule content.
Game IDs bind to the canonical opponent pair and semantic cycle slot rather
than final array indexes, dates, or round positions. Introducing another
scheduling operation with a new seed label cannot consume a shared random
stream and shift existing identity derivation. Equal validated inputs and seed
deep-compare equal; a different seed may reorder the placed games but cannot
change the opponent requirement totals.

Initial-package identities use a separate versioned namespace. `SeasonId`
depends on league identity and starting year. `SeasonCalendarId` depends only
on `SeasonId`; each `TeamSeasonId` depends only on `SeasonId` and `TeamId`; and
each singleton boundary `CalendarEventId` depends only on `SeasonId` and event
kind. Schedule seed and event dates are deliberately excluded from those
identities. `ScheduleId` remains owned by the schedule generator and depends on
the season, canonical participants, canonical schedule seed, and rule-set
identity/version. `LeagueSchedule` also carries its owning `LeagueId` as an
explicit cross-object reference.

## Constraints, optimization, and diagnostics

Typed constraints can express team or venue unavailability, fixed or preferred
matchups, minimum rest, maximum games in a date window, consecutive home/away
limits, showcase preferences, and travel-region preferences. Every constraint
declares hard or soft severity.

These types are an explicit future optimizer boundary, not an implementation
of venues, travel distance, broadcasts, or showcase selection. The current
constructive generator supports only constraints it declares supported. Any
other supplied constraint is returned or rejected as unsupported; it is never
silently ignored.

Schedule validation returns a complete report rather than stopping at the
first error. Hard violations and soft warnings carry stable invariant codes,
human-readable messages, and associated game, game day, team, or date context
when available. Validation covers identity, references, counts, pair balance,
home/away balance, game-day participation, sequence and date spacing, status
date requirements, original-date preservation, and finite non-negative numeric
values.

## Future rule packs

A future NBA-style, tournament, or custom schedule can add a new rule-set ID
and version, a non-uniform opponent matrix, and an optimizer appropriate to its
constraints. Future event calendars may add arena availability, travel
regions, showcase games, Cup windows, Play-In dates, and playoff stages. Those
changes must remain explicit versioned modules and must not mutate the shipped
Milestone 1 rule pack or existing saved identities.

Real NBA dates and scheduling formulas are intentionally not hard-coded. They
change over time, carry licensing and accuracy concerns, and do not belong in
the generic engine. This project uses only its fictional league's documented
rule pack until another fictional or user-supplied pack is deliberately
implemented and tested.
