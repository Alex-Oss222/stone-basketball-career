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

This combined persistence shape is still a future Milestone 1 target. The
generic season and schedule foundation is deliberately not wired into the
current league snapshot or IndexedDB schema yet.

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

### Version 1 envelope

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

### Import and export

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

## Versioning and migrations

`saveVersion`, `simulationVersion`, `rngVersion`, `leagueDataVersion`, `leagueGeneratorVersion`, and `ratingGenerationVersion` serve different purposes:

- `saveVersion` describes envelope and payload shape.
- `simulationVersion` describes game-resolution behavior.
- `rngVersion` identifies exact seed and random-number behavior.
- `leagueDataVersion` identifies the bundled fictional generation components.
- `leagueGeneratorVersion` identifies the exact initial team/player generation behavior.
- `ratingGenerationVersion` identifies the stored-rating formula, position biases, field-seed label, and rating RNG behavior used for each player.

Future migrations are named, pure functions such as `migrateV1ToV2(input: SaveEnvelopeV1): SaveEnvelopeV2`. They:

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

A handwritten narrow validator is proposed for version 1, avoiding a new production dependency. If the schema becomes too complex, a production validation package requires a written rationale before it is added.

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
