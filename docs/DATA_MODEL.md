# Stone Basketball GM — Milestone 1 Data Model

## Goals

The Milestone 1 model must be:

- strict TypeScript with runtime validation at every untrusted boundary;
- independent of React and browser UI concerns;
- deterministic for all simulation-relevant state;
- explicit about stable identity and ownership;
- able to reproduce box scores, standings, and season totals;
- locally persistable, versioned, migratable, and non-destructive; and
- limited to one deterministically generated eight-team, 96-player regular season.

TypeScript types improve authoring but do not validate JSON. Every imported save and every value read from browser storage enters the program as `unknown` and must pass runtime validation before use.

Every TypeScript configuration must explicitly set `"strict": true`; strictness must not depend on compiler defaults or inheritance that is absent from a referenced configuration.

## Proposed folder structure

```text
src/
  app/
    commands/                 # use cases: create season, set rotation, advance day
    selectors/                # view-ready derived data
    state/                    # in-memory session coordination
  data/
    fictional/
      cityParts.ts            # bundled fictional placeholder components
      teamNameParts.ts
      playerNameParts.ts
      colorPalettes.ts
  generation/
    generateLeague.ts         # seeded eight-team/96-player generator
    generatePlayer.ts
    generateRotation.ts       # deterministic CPU defaults
  domain/
    ids.ts                    # branded ID types and parsers
    ratings.ts                # canonical stored ratings and derived grades
    league.ts                 # team/player entity types
    rotation.ts               # depth-chart types and validation
    schedule.ts               # schedule and game-status types
    boxScore.ts               # game result and stat-line types
    season.ts                 # season aggregate state
    standings.ts              # pure standings derivation
    seasonStats.ts            # pure season-stat derivation
    validation.ts             # shared validation primitives
  random/
    randomSource.ts           # shared injected RNG interface
    xoshiro128ss.ts           # versioned implementation
    seed.ts                   # seed normalization and stream derivation
  simulation/
    game/
      simulateGame.ts         # top-level pure game command
      possession.ts           # possession state machine
      lineups.ts              # substitution and eligibility logic
      fatigue.ts
      boxScoreBuilder.ts
    schedule/
      generateSchedule.ts
    rules/
      leagueRules.ts          # immutable Milestone 1 rule constants
    index.ts                  # React-free public simulation API
  persistence/
    indexedDbSaveStore.ts     # browser adapter
    saveEnvelope.ts
    saveValidation.ts
    migrations/
      index.ts
      v1.ts
    jsonTransfer.ts           # import/export adapter
  ui/
    components/
    pages/
    routes/
  App.tsx
  main.tsx
tests/
  data/
  domain/
  simulation/
  persistence/
  fixtures/
tsconfig.app.json
tsconfig.node.json
tsconfig.test.json            # proposed if tests live outside src
```

Import direction is one way:

```text
ui -> app -> domain
          -> generation -> data
                       -> domain
                       -> random
          -> simulation -> domain
                        -> random
          -> persistence -> domain
```

`domain/`, `generation/`, `random/`, and `simulation/` never import React, UI modules, DOM APIs, or persistence adapters. Generation and simulation receive injected random sources. Persistence stores domain snapshots but never generates league data or performs simulation.

## Identity policy

IDs are opaque branded strings in TypeScript and validated strings at runtime.

```ts
declare const idBrand: unique symbol

type Id<Value extends string> = string & {
  readonly [idBrand]: Value
}

type TeamId = Id<'TeamId'>
type PlayerId = Id<'PlayerId'>
type SeasonId = Id<'SeasonId'>
type SeasonCalendarId = Id<'SeasonCalendarId'>
type TeamSeasonId = Id<'TeamSeasonId'>
type ScheduleId = Id<'ScheduleId'>
type GameId = Id<'GameId'>
type GameDayId = Id<'GameDayId'>
type CalendarEventId = Id<'CalendarEventId'>
type ScheduleRuleSetId = Id<'ScheduleRuleSetId'>
type SaveId = Id<'SaveId'>
type SnapshotId = Id<'SnapshotId'>
```

Milestone 1 IDs use lowercase ASCII, digits, and underscores and are never display labels.

- Team IDs are deterministically derived from the league seed fingerprint and a stable ordinal, such as `team_a1b2c3d4_01`.
- Player IDs are deterministically derived from that fingerprint, team ordinal, and roster ordinal, such as `player_a1b2c3d4_01_01`.
- The initial season ID is deterministically derived from the league ID and starting year in a versioned identity namespace; schedule seed and dates are excluded.
- The initial season-calendar ID depends only on its season ID, and each team-season ID depends only on its season ID and team ID.
- A generated regular-season game ID depends on the season ID, rule-set identity/version, canonical schedule seed, canonical opponent pair, and semantic cycle slot; it excludes array position and scheduled date.
- Simulation entity IDs never come from `Math.random`, timestamps, array indexes that may be reordered, or display names.
- Save IDs are storage identities, not simulation inputs. They may be created with the browser's local `crypto.randomUUID()` outside simulation code; copying or importing a save never changes season, team, player, or game IDs.

Once shipped, IDs cannot be reused for a different entity. Renames change display fields only.

## Core TypeScript entities

The following interfaces show the proposed persisted/domain shapes. Readonly fields discourage accidental mutation; commands return new state.

### League and player data

```ts
type Position = 'PG' | 'SG' | 'SF' | 'PF' | 'C'

interface TeamColors {
  readonly primary: string
  readonly secondary: string
  readonly accent: string
}

interface TeamMark {
  readonly kind: 'initials'
  readonly text: string
}

interface Team {
  readonly id: TeamId
  readonly city: string
  readonly nickname: string
  readonly abbreviation: string
  readonly colors: TeamColors
  readonly mark: TeamMark
}

const RATING_KEYS = [
  'insideScoring',
  'midRangeShooting',
  'threePointShooting',
  'freeThrowShooting',
  'passing',
  'ballHandling',
  'offensiveRebounding',
  'defensiveRebounding',
  'perimeterDefense',
  'interiorDefense',
  'stealing',
  'blocking',
  'speed',
  'strength',
  'endurance',
  'basketballIQ',
] as const

type RatingKey = (typeof RATING_KEYS)[number]
type PlayerRatings = Readonly<Record<RatingKey, number>>

interface PlayerTendencies {
  readonly usage: number
  readonly rim: number
  readonly midrange: number
  readonly threePoint: number
  readonly pass: number
  readonly drawFoul: number
}

interface Player {
  readonly id: PlayerId
  readonly teamId: TeamId
  readonly firstName: string
  readonly lastName: string
  readonly age: number
  readonly jerseyNumber: number
  readonly primaryPosition: Position
  readonly secondaryPosition: Position | null
  readonly ratingGenerationVersion: 1
  readonly ratings: PlayerRatings
  readonly tendencies: PlayerTendencies
}
```

`Player.teamId` is the canonical ownership link. A team roster is derived by grouping players on `teamId`; a duplicate team-level list is not persisted. This prevents two competing ownership sources.

### Deterministic league generation

League generation is a pure function of the normalized league seed, `leagueGeneratorVersion`, bundled fictional component data, and an injected RNG:

```ts
interface GeneratedLeague {
  readonly generatorVersion: 1
  readonly seedFingerprint: string
  readonly teams: readonly Team[]
  readonly players: readonly Player[]
  readonly defaultRotationsByTeamId: Readonly<Record<TeamId, RotationPlan>>
}
```

Generation uses a dedicated `derive(rootSeed, "league/v1")` stream so schedule or game changes cannot shift initial league data. IDs come from stable ordinals rather than random-call position. Each stored player rating uses its own fresh random source derived from the full league seed and the label `player-rating/v{ratingGenerationVersion}/{playerId}/{ratingKey}`. Rating fields never consume the shared league stream, so adding another canonical rating cannot shift any existing rating value. The generator:

1. creates eight unique fictional city/name combinations and non-conflicting color palettes;
2. creates a short initials mark for each team;
3. creates 12 players per team with a position-balanced roster;
4. creates unique fictional names from bundled components;
5. assigns integer ages from 19 through 36;
6. generates all 16 canonical ratings through versioned field-specific streams and generates tendencies within their validated ranges;
7. assigns unique jersey numbers within each team; and
8. creates five starters and a valid 240-minute default rotation.

Team generation must avoid real professional team identities. The component lists are local fictional placeholders, not scraped or runtime-fetched data. Generated teams and players are persisted in full in `SeasonStateV1`; loading a save validates and uses that snapshot instead of rerunning the generator.

### Rating and tendency ranges

Every stored rating is a finite integer from 0 through 100 inclusive. A valid `PlayerRatings` object has exactly the 16 keys in `RATING_KEYS`; missing keys, additional keys, non-numbers, `NaN`, infinity, decimals, and out-of-range values are invalid and are never coerced or clamped.

Letter grades are derived rather than stored: A+ begins at 95, then each boundary descends in five-point steps through D- at 40; values below 40 are F. Derived category values may contain decimals, but grade inputs must remain finite and inside 0 through 100.

No persisted “overall” rating drives simulation. If displayed, overall is a versioned, position-weighted selector derived from component ratings. This keeps simulation decisions traceable to individual skills.

Tendencies are finite integers from 0 through 100. `rim + midrange + threePoint` must be greater than zero but does not need to equal 100; the simulation normalizes the weights after contextual modifiers. `usage` must be 1–100. Other tendency values may be zero.

Generated-league validation requires:

- exactly eight unique teams;
- exactly 96 unique players;
- exactly 12 players owned by each team;
- every age to be an integer from 19 through 36;
- every player to carry the supported rating-generation version and exactly the canonical ratings;
- unique jersey numbers within a team;
- every position and numeric field in range;
- every team mark to contain only its saved text initials;
- every generated team identity to pass the fictional professional-identity audit; and
- no player or team reference outside the persisted generated league.

### Rotation

```ts
type FivePlayerLineup = readonly [
  PlayerId,
  PlayerId,
  PlayerId,
  PlayerId,
  PlayerId,
]

interface RotationPlan {
  readonly teamId: TeamId
  readonly starters: FivePlayerLineup
  readonly minutesByPlayerId: Readonly<Record<PlayerId, number>>
  readonly benchPriority: readonly PlayerId[]
}
```

A valid regulation plan has:

- five distinct starters owned by the team;
- one entry for each of the team's 12 players and no others;
- finite integer minutes from 0 through 48;
- exactly 240 total minutes;
- at least one planned minute for each starter; and
- each team player exactly once in `benchPriority`.

`benchPriority` breaks otherwise equal lineup choices. The engine may depart from individual targets because of dead-ball timing, fatigue, or foul-outs, but the actual team total remains exact.

### Schedule and results

The authoritative generic season, event-calendar, opponent-requirement, and
schedule-placement model is defined in `SEASON_AND_SCHEDULING.md`. It replaces
the earlier result-oriented scheduled-game sketch with separate versioned
`Season`, `SeasonCalendar`, `TeamSeason`, `ScheduleRuleSet`,
`OpponentRequirement`, `LeagueSchedule`, `GameDay`, and `ScheduledGame`
records. The box-score shapes below remain planned simulation outputs; they are
not part of the scheduling implementation.

The pure application command `createSeasonFoundation` composes an already
validated generated `League` into the initial `Season`, `SeasonCalendar`, one
`TeamSeason` per league team, and `LeagueSchedule`. It performs no persistence
or UI work and returns the package only after component and cross-object
validation succeeds.

```ts
interface PlayerBoxScore {
  readonly playerId: PlayerId
  readonly teamId: TeamId
  readonly started: boolean
  readonly regulationSeconds: number
  readonly overtimeSeconds: number
  readonly fieldGoalsMade: number
  readonly fieldGoalsAttempted: number
  readonly threePointersMade: number
  readonly threePointersAttempted: number
  readonly freeThrowsMade: number
  readonly freeThrowsAttempted: number
  readonly offensiveRebounds: number
  readonly defensiveRebounds: number
  readonly assists: number
  readonly steals: number
  readonly blocks: number
  readonly turnovers: number
  readonly personalFouls: number
  readonly points: number
}

interface TeamBoxScore {
  readonly teamId: TeamId
  readonly periodPoints: readonly number[]
  readonly playerLines: readonly PlayerBoxScore[]
}

interface GameResult {
  readonly gameId: GameId
  readonly simulationVersion: 1
  readonly rngVersion: 'xoshiro128ss-v1'
  readonly inputFingerprint: string
  readonly home: TeamBoxScore
  readonly away: TeamBoxScore
  readonly overtimePeriods: number
  readonly completed: true
}
```

All box-score counting fields and seconds are non-negative safe integers. Team totals are calculated from player lines. A stored team summary may be included for quick display, but validation must prove it equals that calculation.

For each player:

```text
points = 2 × (fieldGoalsMade - threePointersMade)
       + 3 × threePointersMade
       + freeThrowsMade
```

Total rebounds are derived as offensive plus defensive rebounds and need not be stored.

### Season state

```ts
interface LeagueRulesV1 {
  readonly version: 1
  readonly regulationPeriods: 4
  readonly regulationPeriodSeconds: 720
  readonly overtimePeriodSeconds: 300
  readonly playersOnCourt: 5
  readonly foulOutLimit: 6
  readonly shotClockSeconds: 24
  readonly offensiveReboundClockSeconds: 14
}

interface SeasonStateV1 {
  readonly id: SeasonId
  readonly leagueDataVersion: 1
  readonly leagueGeneratorVersion: 1
  readonly rootSeed: string
  readonly userTeamId: TeamId
  readonly currentGameDay: number
  readonly rules: LeagueRulesV1
  readonly teams: readonly Team[]
  readonly players: readonly Player[]
  readonly rotationsByTeamId: Readonly<Record<TeamId, RotationPlan>>
  readonly schedule: readonly ScheduledGame[]
  readonly resultsByGameId: Readonly<Partial<Record<GameId, GameResult>>>
}
```

This combined simulation persistence shape is still a future Milestone 1
target. The narrower active-league snapshot now has a version-2 serialization
and migration boundary for the existing season foundation, described below.
The active-league repository and React state now use the complete V2 value;
this remains distinct from the future autosave-history envelope.

Generated team names, cities, colors, marks, player names, IDs, ratings, ages, positions, assignments, tendencies, rules, and rotations are snapshotted into a new season. A later application or generator update cannot silently change the competitive inputs of an existing save.

Simulation of a game is atomic in Milestone 1, so no in-progress possession or evolving global RNG state is saved. The root seed plus labeled per-game derivation reproduces a game's random stream. A completed result also stores its engine/RNG versions and input fingerprint.

## Derived models

### Standings

```ts
interface StandingsRow {
  readonly teamId: TeamId
  readonly gamesPlayed: number
  readonly wins: number
  readonly losses: number
  readonly pointsFor: number
  readonly pointsAgainst: number
  readonly pointDifferential: number
}
```

Standings are rebuilt from completed results. Winning percentage is a selector: `wins / gamesPlayed`, or zero for sorting and an em dash for display when no games are complete.

Proposed deterministic ordering:

1. higher winning percentage;
2. higher head-to-head winning percentage among tied teams;
3. higher point differential;
4. higher points for;
5. ascending stable team ID.

The final team-ID rule guarantees a stable order without consuming randomness. With the proposed schedule, all teams finish with equal games played, but the derivation remains valid midseason.

### Season player statistics

```ts
interface PlayerSeasonTotals {
  readonly playerId: PlayerId
  readonly teamId: TeamId
  readonly gamesPlayed: number
  readonly gamesStarted: number
  readonly regulationSeconds: number
  readonly overtimeSeconds: number
  readonly fieldGoalsMade: number
  readonly fieldGoalsAttempted: number
  readonly threePointersMade: number
  readonly threePointersAttempted: number
  readonly freeThrowsMade: number
  readonly freeThrowsAttempted: number
  readonly offensiveRebounds: number
  readonly defensiveRebounds: number
  readonly assists: number
  readonly steals: number
  readonly blocks: number
  readonly turnovers: number
  readonly personalFouls: number
  readonly points: number
}
```

Totals are rebuilt by folding completed player box scores in stable `gameDay, gameId` order. Per-game values and percentages are derived, not persisted. A zero-attempt percentage is `null`, never zero-by-accident or `NaN`.

Derived standings and season totals may be memoized in memory. If cached in a save later, they are disposable and must be recomputed and compared during validation.

## Save format and local storage

### Current active-league snapshot DTOs

The active-league snapshot and the planned full-season save envelope are
different versioned contracts. The current `LeagueSnapshotV1` remains the
independently parseable league-only format:

```ts
interface LeagueSnapshotV1 {
  readonly kind: 'stone-basketball-gm-league-snapshot'
  readonly snapshotVersion: 1
  readonly rootSeed: string
  readonly league: League
  readonly managedTeamId: TeamId | null
}
```

`LeagueSnapshotV2` is the serialized regular-season-foundation DTO. Its top
level is closed and contains exactly:

```ts
interface LeagueSnapshotV2 {
  readonly kind: 'stone-basketball-gm-league-snapshot'
  readonly snapshotVersion: 2
  readonly revision: number
  readonly rootSeed: string
  readonly managedTeamId: TeamId | null
  readonly league: LeagueSnapshotV2LeagueDto
  readonly season: LeagueSnapshotV2SeasonDto
  readonly seasonCalendar: LeagueSnapshotV2SeasonCalendarDto
  readonly teamSeasons: readonly LeagueSnapshotV2TeamSeasonDto[]
  readonly leagueSchedule: LeagueSnapshotV2LeagueScheduleDto
  readonly creationMetadata: LeagueSnapshotV2CreationMetadata
}

interface LeagueSnapshotV2CreationMetadata {
  readonly startingYear: number
  readonly regularSeasonStartDate: LocalDate
  readonly gameDaySpacing: number
  readonly scheduleSeed: string
  readonly scheduleRuleSetId: ScheduleRuleSetId
  readonly scheduleRuleSetVersion: number
}
```

A newly serialized or migrated V2 snapshot starts at revision 1. Revision is a
positive safe integer and is the only DTO revision field; it is not a timestamp.
Every successful repository update increments it by exactly one. Callers must
supply the revision they observed; a mismatch is a structured stale-write
failure and cannot overwrite the current value.

V2 stores the complete authoritative generated league, season, calendar event
records, one team-season record per league team, opponent requirements, game
days, and scheduled games. Stable identifiers, every original/current/actual
date, statuses, meeting numbers, and public array order are serialized. Optional
serialized values use explicit `null`: for example a league-scoped calendar
event has `teamId: null`, an uncompleted scheduled game has `actualDate: null`,
and an absent opponent-requirement source tag is `null`. Domain unions may omit
those properties after the DTO has been parsed and validated.

Letter grades, dashboard or navigation state, view models, derived summaries,
standings, records, scores, winners, statistics, and unknown event dates are not
serialized. Numeric ratings remain authoritative, and grades continue to be
derived. The rule-set definition itself is also not copied into the snapshot;
the snapshot stores its exact ID and version and resolves that pair through the
supported rule-set registry.

### DTO and live-domain boundary

A persistence DTO is not assumed to be a live domain object. It contains only
JSON primitives, dense arrays, plain records, canonical serialized identifier
strings, canonical `LocalDate` strings, and explicit nulls. It cannot contain
`Date`, `Map`, `Set`, functions, symbols, `undefined`, accessors, sparse arrays,
array custom properties, class instances, non-finite numbers, negative zero, or
other values that change under a JSON round trip.

`parseLeagueSnapshotV2` accepts `unknown`, verifies every exact record key set
and property descriptor before reading it, parses every nested primitive and
branded value, reconstructs detached live domain values for semantic
validation, and returns a detached validated DTO. Missing and additional fields
are errors; the parser never clamps, trims, drops, repairs, or regenerates
stored data.

Validation proceeds through four layers:

1. JSON-safe primitive, record, descriptor, and dense-array shape;
2. league, season, calendar, team-season, and schedule entity rules;
3. cross-object identity, ownership, season, schedule, team, event, and date
   references; and
4. creation-metadata, stored opponent-matrix, game-day spacing, boundary-event,
   and supported-rule-set consistency.

The stored `managedTeamId` is always present and is either null or resolves to
exactly one stored team. Season years and label must agree with creation
metadata; season and schedule IDs must agree; each league team must have exactly
one correctly identified team-season record; and calendar opening/conclusion
dates must agree with the stored schedule and creation inputs. Schedule seed,
spacing, rule-set ID, and rule-set version are duplicated audit facts and must
agree with the stored entities rather than being trusted or repaired.

In this V2 foundation, opening and conclusion are league-scoped and are the only
events whose dates are currently supported. Other recognized future event kinds
may be retained only as pending TBA records with null dates. A postponed game
with no current date keeps the conclusion unknown rather than moving it earlier;
cancelled games do not extend the current conclusion date.

Normal V2 restoration never calls league generation,
`createSeasonFoundation`, schedule generation, opponent-requirement generation,
or seeded randomization. The stored opponent matrix is validated in place and
the stored games, IDs, dates, and ordering remain authoritative. A rule set is
restorable only when its exact `(ScheduleRuleSetId, version)` registration is
available. An unknown ID or unsupported version produces a structured recovery
error; restoration never substitutes the newest rule version or reinterprets a
schedule using a different pack.

A valid DTO guarantees this round trip without losing, regenerating,
reordering, or changing an authoritative field:

```ts
const serialized = JSON.stringify(snapshotV2)
const restored = parseLeagueSnapshotV2(JSON.parse(serialized))
```

### Pure V1-to-V2 migration

`migrateLeagueSnapshotV1ToV2(snapshotV1, explicitSeasonCreationInputs)` is the
only Task A path that creates the missing season foundation. It first parses V1
without modifying it, requires an explicit starting year, regular-season start
`LocalDate`, positive game-day spacing, and canonical schedule seed, and then
calls the authoritative `createSeasonFoundation` coordinator. It does not choose
defaults or accept caller-provided rule-set metadata.

The pure in-memory migration stages are `parse-v1`, `validate-inputs`,
`create-season-foundation`, `construct-v2`, `validate-v2`, and
`serialize-round-trip`. Failures identify the stage, a stable code, a readable
message, and safe nested validation issues. Success preserves the V1 league and
managed team, stores the actual rule-set identity used by the coordinator, sets
revision 1, validates the completed V2 DTO, and verifies its JSON round trip.
For the same explicit inputs, migrated season entities must equal a direct
coordinator result; persistence does not introduce separate identity rules.

Migration performs no storage reads, writes, deletes, repository selection, or
React-state updates and mutates neither input. V1 remains parseable on its own,
and neither parser accepts the other version. The repository composes this pure
operation with its storage transaction; the migration function itself remains
independent of IndexedDB.

### Active-league IndexedDB repository

The current single-active-league bridge retains database version 1 and the
existing `activeLeague` object store. Versioned records occupy separate keys in
that one store:

- `current` is the shipped V1 location and is never renamed or rewritten by a
  migration; and
- `current-v2` stores one complete V2 DTO and is authoritative whenever it
  exists.

Each value is one structured-cloned `{ leagueId, snapshot }` record. Version is
not duplicated in the wrapper: the key is the storage-location discriminator
and the DTO's exact `snapshotVersion` remains the data discriminator. Both raw
locations are read in one readonly transaction before parsing. Restoration has
four explicit results: `empty`, `restored-v2`, `migration-required`, and
`recovery-required`. A valid V2 wins even if a retained V1 is invalid. An
invalid or unsupported V2 produces recovery instead of falling back to V1,
because fallback could silently resurrect stale state. A V1 is parsed only
when no V2 record exists, and it is never installed as partial active React
state. Storage tracks key presence separately from its raw value, so a corrupt
record containing literal `null` or `undefined` is rejected as present data and
cannot masquerade as an absent version.

Stored V1-to-V2 migration executes in one read-write transaction. It rereads
and validates V1, validates the user's explicit season inputs, invokes the pure
migration, validates the complete revision-1 V2, adds V2 at `current-v2`,
rereads both records, revalidates V2, and compares both reread values before
commit. Success is reported only from transaction completion. Any read,
generation, write, reread, revalidation, comparison, or commit failure aborts
the transaction, leaves no V2, and preserves V1 unchanged.

The only current V2 update changes `managedTeamId`. It validates the complete
stored snapshot inside the transaction, requires the expected league identity
and revision, increments revision once, reparses the complete candidate, then
rereads and compares the stored result before commit. Revision overflow,
foreign teams, stale callers, quota failures, and commit failures publish no
state. Clearing likewise requires the current V2 league identity and revision
(or the known V1 league identity when V1 is the only record), deletes both keys
in one transaction, and verifies both are absent. Deleting only V2 is forbidden
because it would reactivate retained V1.

Normal clearing and corrupt-storage recovery are deliberately separate
operations. Healthy V2 clearing continues to require the observed league
identity and revision, and a stale normal clear publishes no mutation. When a
`recovery-required` record is too malformed to yield a trusted identity or
revision, the application may instead offer the explicitly destructive
`purgeCorruptLeagueStorage` action. It appears only in recovery, requires a
separate permanent-deletion confirmation, parses neither record, and deletes
both `current` and `current-v2` in one read-write transaction. The transaction
rereads both locations and reports success only after both are absent and the
commit completes. A deletion, verification, or commit failure rolls back the
transaction, reports a structured storage error, preserves the prior records,
and never activates V1 as fallback.

New leagues are created directly as complete V2 snapshots from visible,
explicit season inputs. The application generates the league once, calls
`createSeasonFoundation` once, validates the DTO, writes only `current-v2`, and
places it into React state only after the repository confirms commit. Normal V2
restore remains parse-and-validate only and never calls any generator.

### Planned full-season save envelope

```ts
interface SaveEnvelopeV1 {
  readonly kind: 'stone-basketball-gm-save'
  readonly saveVersion: 1
  readonly simulationVersion: 1
  readonly rngVersion: 'xoshiro128ss-v1'
  readonly saveId: SaveId
  readonly snapshotId: SnapshotId
  readonly snapshotKind: 'autosave' | 'manual'
  readonly revision: number
  readonly saveName: string
  readonly createdAt: string
  readonly updatedAt: string
  readonly payload: SeasonStateV1
}
```

Timestamps, save IDs, and snapshot IDs are persistence metadata and are excluded from simulation determinism comparisons. The JSON export is one complete immutable envelope with no functions, class instances, typed arrays, or browser-specific objects. Every named manual save has a unique snapshot ID even when two manual saves share the same display name.

The approved IndexedDB layout is:

- `autosaveRevisions`, keyed by `[saveId, revision]`, containing immutable autosave envelopes;
- `autosaveHeads`, keyed by `saveId`, pointing to the latest confirmed autosave revision; and
- `manualSaves`, keyed by `snapshotId`, containing named immutable manual-save envelopes.

An autosave transaction adds a new immutable revision, advances the head, and deletes only autosave revisions older than the newest 20 for that save ID. Those operations share one transaction: if any operation fails, the transaction rolls back and the prior head/history remain valid. The UI discloses the 20-revision retention policy.

Creating a named manual save always adds a new `manualSaves` record. It never updates a same-name record. Named manual saves are never pruned; deletion requires the user to select a specific manual save and confirm. Storage quota failures leave the prior state intact and produce a clear persistent error with export and explicit save-management options.

### Planned import and export

Export serializes an already validated revision and downloads it locally. Import follows this sequence:

1. enforce a 50 MiB file-size ceiling before parsing;
2. parse JSON as `unknown`;
3. validate the envelope discriminator and integer version;
4. reject unsupported future versions without touching storage;
5. migrate older supported versions sequentially in memory;
6. fully validate structure, references, rules, schedule, results, and invariants;
7. show a preview with save name, team, progress, source ID, and any migration;
8. write only after explicit confirmation; and
9. on ID collision, keep both by assigning new storage IDs unless the user explicitly chooses a different safe action.

Import never changes or deletes the currently loaded revision or a named manual save as a side effect. A confirmed import is retained as a named manual save unless the user explicitly chooses to begin using it as the active season.

## Full-season versioning and migrations

`saveVersion`, `simulationVersion`, `rngVersion`, `leagueDataVersion`, `leagueGeneratorVersion`, and `ratingGenerationVersion` serve different purposes:

- `saveVersion` describes envelope and payload shape.
- `simulationVersion` describes game-resolution behavior.
- `rngVersion` identifies exact seed and random-number behavior.
- `leagueDataVersion` identifies the bundled fictional generation components.
- `leagueGeneratorVersion` identifies the exact initial team/player generation behavior.
- `ratingGenerationVersion` identifies the stored-rating formula, position biases, field-seed label, and rating RNG behavior used for each player.

Future full-season-envelope migrations are named, pure functions such as
`migrateV1ToV2(input: SaveEnvelopeV1): SaveEnvelopeV2`. They:

- never mutate the input;
- never consume randomness;
- never rerun league generation to replace already persisted team or player fields;
- never rewrite completed game outcomes;
- fill new fields with documented deterministic defaults;
- validate their expected input and output;
- are covered by frozen JSON fixtures; and
- retain the original imported file outside app storage and create a new local revision after user confirmation.

A newer unsupported version is rejected clearly. A known older version either migrates completely or leaves storage unchanged. There is no partial recovery that silently discards invalid teams, players, games, or statistics.

## Runtime validation

Validation has four layers:

1. **Primitive:** object/array shape, literal discriminators, finite safe integers, string length and character rules.
2. **Entity:** rating/tendency ranges, unique IDs, valid rotations, legal box-score arithmetic.
3. **Referential:** player ownership, team/game references, result-to-schedule correspondence, unique game IDs.
4. **Whole-season:** schedule shape, chronological completion boundary, standings/stat recomputation, and all statistical invariants.

Validators return structured issues with a stable code and JSON-style path. They do not coerce strings to numbers, clamp bad ratings, drop unknown records, or repair corrupt statistics silently.

The current league snapshot versions use handwritten narrow validators and no
new production dependency. If the future full-season schema becomes too
complex, a production validation package requires a written rationale before
it is added.

## Required statistical invariants

These are checked after every simulated game and during save import:

- each team has exactly 14,400 regulation player-seconds, equivalent to 240 regulation minutes;
- each team has exactly `overtimePeriods × 1,500` overtime player-seconds;
- team points equal the sum of player points;
- player and team point formulas agree with made field goals, made threes, and made free throws;
- made field goals never exceed field-goal attempts;
- made three-pointers never exceed three-point attempts, and three-point attempts never exceed field-goal attempts;
- made free throws never exceed free-throw attempts;
- no statistic is negative, non-finite, fractional where an integer is required, or `NaN`;
- every completed game has exactly one winner;
- standings wins and losses match completed games;
- league wins equal league losses and equal the number of completed games;
- every player belongs to exactly one valid team;
- every team has exactly 12 players;
- every saved player has a stable ID, fictional name, valid age, positions, ratings, and team assignment;
- every scheduled game references two different valid teams;
- every completed result corresponds to exactly one scheduled game;
- no team is scheduled twice on one game day;
- the proposed full schedule gives each team 28 games and each pairing four games; and
- identical league seeds and generator versions produce deeply equal initial teams, players, and rotations; and
- identical validated inputs, simulation version, RNG version, and seeds produce deeply equal results.

Additional consistency checks include `gamesPlayed = wins + losses`, player games played matching box-score appearances, five starters per team, assists not exceeding made field goals, steals not exceeding opponent turnovers, and blocks not exceeding opponent missed field goals.
