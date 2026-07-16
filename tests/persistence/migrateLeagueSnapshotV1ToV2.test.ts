import { describe, expect, it, vi } from 'vitest'
import {
  createSeasonFoundation,
} from '../../src/app/commands/createSeasonFoundation'
import type {
  SeasonFoundationConfiguration,
  SeasonFoundationConfigurationInput,
} from '../../src/app/commands/createSeasonFoundation'
import { parseLocalDate } from '../../src/domain/localDate'
import {
  InvalidLeagueSnapshotError,
  parseLeagueSnapshot,
} from '../../src/persistence/leagueSnapshot'
import {
  InvalidLeagueSnapshotV2Error,
  parseLeagueSnapshotV2,
  serializeLeagueSnapshotV2,
} from '../../src/persistence/leagueSnapshotV2'
import type { LeagueSnapshotV2 } from '../../src/persistence/leagueSnapshotV2'
import {
  LeagueSnapshotV1ToV2MigrationError,
  migrateLeagueSnapshotV1ToV2,
} from '../../src/persistence/migrations/migrateLeagueSnapshotV1ToV2'
import {
  V2_FIXTURE_CREATION_INPUTS,
  createLeagueSnapshotV1Fixture,
} from './leagueSnapshotV2.fixture'

describe('pure LeagueSnapshot V1-to-V2 migration', () => {
  it('creates revision 1 deterministically while preserving the V1 league and managed team', () => {
    const firstV1 = createLeagueSnapshotV1Fixture()
    const secondV1 = createLeagueSnapshotV1Fixture()

    const first = migrateLeagueSnapshotV1ToV2(
      firstV1,
      V2_FIXTURE_CREATION_INPUTS,
    )
    const second = migrateLeagueSnapshotV1ToV2(
      secondV1,
      V2_FIXTURE_CREATION_INPUTS,
    )

    expect(first).toEqual(second)
    expect(first).not.toBe(second)
    expect(first.snapshotVersion).toBe(2)
    expect(first.revision).toBe(1)
    expect(first.rootSeed).toBe(firstV1.rootSeed)
    expect(first.managedTeamId).toBe(firstV1.managedTeamId)
    expect(first.league).toEqual(firstV1.league)
    expect(first.league).not.toBe(firstV1.league)
  })

  it('matches a direct coordinator call and V2 serialization exactly', () => {
    const v1 = createLeagueSnapshotV1Fixture()
    const { foundation, expectedSnapshot } = createDirectExpectedSnapshot(
      v1,
      V2_FIXTURE_CREATION_INPUTS,
    )

    const migrated = migrateLeagueSnapshotV1ToV2(
      v1,
      V2_FIXTURE_CREATION_INPUTS,
    )

    expect(migrated).toEqual(expectedSnapshot)
    expect(migrated.season).toEqual(foundation.season)
    expect(migrated.teamSeasons).toEqual(foundation.teamSeasons)
    expect(migrated.seasonCalendar.events.map(({ id }) => id)).toEqual(
      foundation.calendar.events.map(({ id }) => id),
    )
    expect(migrated.leagueSchedule.games.map(({ id }) => id)).toEqual(
      foundation.schedule.games.map(({ id }) => id),
    )
    expect(migrated.leagueSchedule.opponentRequirements).toEqual(
      expectedSnapshot.leagueSchedule.opponentRequirements,
    )
  })

  it.each([
    {
      name: 'schedule seed',
      inputs: {
        ...V2_FIXTURE_CREATION_INPUTS,
        scheduleSeed: 'league-snapshot-v2-alternate-schedule',
      },
    },
    {
      name: 'regular-season start date',
      inputs: {
        ...V2_FIXTURE_CREATION_INPUTS,
        regularSeasonStartDate: parseLocalDate('2026-10-12'),
      },
    },
    {
      name: 'game-day spacing',
      inputs: {
        ...V2_FIXTURE_CREATION_INPUTS,
        calendarDaySpacing: 4,
      },
    },
    {
      name: 'starting year',
      inputs: {
        ...V2_FIXTURE_CREATION_INPUTS,
        startingYear: 2027,
        regularSeasonStartDate: parseLocalDate('2027-10-05'),
      },
    },
  ] satisfies readonly {
    readonly name: string
    readonly inputs: SeasonFoundationConfiguration
  }[])('follows coordinator identity and schedule behavior when changing $name', ({ inputs }) => {
    const v1 = createLeagueSnapshotV1Fixture()
    const v1Before = structuredClone(v1)
    const inputsBefore = structuredClone(inputs)
    const { expectedSnapshot } = createDirectExpectedSnapshot(v1, inputs)

    const migrated = migrateLeagueSnapshotV1ToV2(v1, inputs)

    expect(migrated).toEqual(expectedSnapshot)
    expect(migrated.league).toEqual(v1.league)
    expect(migrated.managedTeamId).toBe(v1.managedTeamId)
    expect(migrated.leagueSchedule.opponentRequirements).toEqual(
      expectedSnapshot.leagueSchedule.opponentRequirements,
    )
    expect(v1).toEqual(v1Before)
    expect(inputs).toEqual(inputsBefore)
  })

  it('stores the actual coordinator rule metadata and initial revision', () => {
    const v1 = createLeagueSnapshotV1Fixture()
    const foundation = createSeasonFoundation({
      league: v1.league,
      ...V2_FIXTURE_CREATION_INPUTS,
    })

    const migrated = migrateLeagueSnapshotV1ToV2(
      v1,
      V2_FIXTURE_CREATION_INPUTS,
    )

    expect(migrated.revision).toBe(1)
    expect(migrated.creationMetadata).toEqual({
      startingYear: V2_FIXTURE_CREATION_INPUTS.startingYear,
      regularSeasonStartDate:
        V2_FIXTURE_CREATION_INPUTS.regularSeasonStartDate,
      gameDaySpacing: V2_FIXTURE_CREATION_INPUTS.calendarDaySpacing,
      scheduleSeed: V2_FIXTURE_CREATION_INPUTS.scheduleSeed,
      scheduleRuleSetId: foundation.schedule.ruleSetId,
      scheduleRuleSetVersion: foundation.season.rulesVersion,
    })
    expect(migrated.creationMetadata.scheduleRuleSetId).toBe(
      migrated.leagueSchedule.ruleSetId,
    )
    expect(migrated.creationMetadata.scheduleRuleSetVersion).toBe(
      migrated.season.rulesVersion,
    )
  })

  it('preserves the complete migrated schedule through JSON serialization and restoration', () => {
    const migrated = migrateLeagueSnapshotV1ToV2(
      createLeagueSnapshotV1Fixture(),
      V2_FIXTURE_CREATION_INPUTS,
    )

    const restored = parseLeagueSnapshotV2(
      JSON.parse(JSON.stringify(migrated)) as unknown,
    )

    expect(restored).toEqual(migrated)
    expect(restored.leagueSchedule).toEqual(migrated.leagueSchedule)
    expect(restored.leagueSchedule.games.map(({ id }) => id)).toEqual(
      migrated.leagueSchedule.games.map(({ id }) => id),
    )
    expect(
      restored.leagueSchedule.games.map(
        ({ originalScheduledDate }) => originalScheduledDate,
      ),
    ).toEqual(
      migrated.leagueSchedule.games.map(
        ({ originalScheduledDate }) => originalScheduledDate,
      ),
    )
    expect(
      restored.leagueSchedule.games.map(
        ({ currentScheduledDate }) => currentScheduledDate,
      ),
    ).toEqual(
      migrated.leagueSchedule.games.map(
        ({ currentScheduledDate }) => currentScheduledDate,
      ),
    )
    expect(restored.seasonCalendar.events).toEqual(
      migrated.seasonCalendar.events,
    )
    expect(restored.teamSeasons).toEqual(migrated.teamSeasons)
  })

  it('keeps V1 and V2 independently discriminated', () => {
    const v1 = createLeagueSnapshotV1Fixture()
    const v2 = migrateLeagueSnapshotV1ToV2(v1, V2_FIXTURE_CREATION_INPUTS)

    expect(parseLeagueSnapshot(v1)).toEqual(v1)
    expect(() => parseLeagueSnapshot(v2)).toThrow(InvalidLeagueSnapshotError)
    expect(() => parseLeagueSnapshotV2(v1)).toThrow(
      InvalidLeagueSnapshotV2Error,
    )

    const error = captureMigrationError(() =>
      migrateLeagueSnapshotV1ToV2(v2, V2_FIXTURE_CREATION_INPUTS),
    )
    expect(error.stage).toBe('parse-v1')
    expect(error.code).toBe(
      'league_snapshot_migration.v1_to_v2.parse_v1_failed',
    )
  })
})

describe('migration failure stages and immutability', () => {
  it('reports parse-v1 failures with safe underlying validation issues', () => {
    const invalidV1 = structuredClone(
      createLeagueSnapshotV1Fixture(),
    ) as unknown as MutableRecord
    invalidV1.snapshotVersion = 2
    const before = structuredClone(invalidV1)
    deepFreeze(invalidV1)

    const error = captureMigrationError(() =>
      migrateLeagueSnapshotV1ToV2(
        invalidV1,
        V2_FIXTURE_CREATION_INPUTS,
      ),
    )

    expect(error.stage).toBe('parse-v1')
    expect(error.code).toBe(
      'league_snapshot_migration.v1_to_v2.parse_v1_failed',
    )
    expect(error.issues).toEqual([
      expect.objectContaining({
        code: 'league_snapshot_v1.invalid',
        path: '$.snapshotVersion',
      }),
    ])
    expect(invalidV1).toEqual(before)
  })

  it('reports validate-inputs failures without changing either input', () => {
    const v1 = deepFreeze(createLeagueSnapshotV1Fixture())
    const invalidInputs = deepFreeze({
      ...V2_FIXTURE_CREATION_INPUTS,
      calendarDaySpacing: 0,
    })
    const v1Before = structuredClone(v1)
    const inputsBefore = structuredClone(invalidInputs)

    const error = captureMigrationError(() =>
      migrateLeagueSnapshotV1ToV2(v1, invalidInputs),
    )

    expect(error.stage).toBe('validate-inputs')
    expect(error.code).toBe(
      'league_snapshot_migration.v1_to_v2.invalid_season_inputs',
    )
    expect(v1).toEqual(v1Before)
    expect(invalidInputs).toEqual(inputsBefore)
  })

  it.each([
    {
      name: 'blank schedule seed',
      inputs: { ...V2_FIXTURE_CREATION_INPUTS, scheduleSeed: '   ' },
    },
    {
      name: 'noncanonical schedule seed',
      inputs: {
        ...V2_FIXTURE_CREATION_INPUTS,
        scheduleSeed: ' schedule-seed',
      },
    },
    {
      name: 'malformed LocalDate',
      inputs: {
        ...V2_FIXTURE_CREATION_INPUTS,
        regularSeasonStartDate: '2026-02-30',
      },
    },
    {
      name: 'fractional game-day spacing',
      inputs: { ...V2_FIXTURE_CREATION_INPUTS, calendarDaySpacing: 1.5 },
    },
    {
      name: 'additional input field',
      inputs: { ...V2_FIXTURE_CREATION_INPUTS, unexpected: true },
    },
  ])('rejects $name during the validate-inputs stage', ({ inputs }) => {
    const error = captureMigrationError(() =>
      migrateLeagueSnapshotV1ToV2(
        createLeagueSnapshotV1Fixture(),
        inputs as unknown as SeasonFoundationConfigurationInput,
      ),
    )

    expect(error.stage).toBe('validate-inputs')
    expect(error.issues.length).toBeGreaterThan(0)
  })

  it('reports coordinator creation failures without changing valid supplied values', () => {
    const v1 = deepFreeze(createLeagueSnapshotV1Fixture())
    const inputs = deepFreeze({
      startingYear: 2026,
      regularSeasonStartDate: parseLocalDate('2026-12-31'),
      calendarDaySpacing: 30,
      scheduleSeed: 'migration-outside-season-window',
    })
    const v1Before = structuredClone(v1)
    const inputsBefore = structuredClone(inputs)

    const error = captureMigrationError(() =>
      migrateLeagueSnapshotV1ToV2(v1, inputs),
    )

    expect(error.stage).toBe('create-season-foundation')
    expect(error.code).toBe(
      'league_snapshot_migration.v1_to_v2.season_foundation_failed',
    )
    expect(error.issues).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          code: 'foundation.schedule.conclusion_outside_season',
        }),
      ]),
    )
    expect(v1).toEqual(v1Before)
    expect(inputs).toEqual(inputsBefore)
  })

  it('reports a JSON serialization failure at serialize-round-trip', () => {
    const stringify = vi
      .spyOn(JSON, 'stringify')
      .mockImplementationOnce(() => {
        throw new TypeError('deliberate serialization failure')
      })

    try {
      const error = captureMigrationError(() =>
        migrateLeagueSnapshotV1ToV2(
          createLeagueSnapshotV1Fixture(),
          V2_FIXTURE_CREATION_INPUTS,
        ),
      )

      expect(error.stage).toBe('serialize-round-trip')
      expect(error.code).toBe(
        'league_snapshot_migration.v1_to_v2.serialize_round_trip_failed',
      )
    } finally {
      stringify.mockRestore()
    }
  })

  it('does not mutate deeply frozen supplied values on successful migration', () => {
    const v1 = deepFreeze(createLeagueSnapshotV1Fixture())
    const inputs = deepFreeze(structuredClone(V2_FIXTURE_CREATION_INPUTS))
    const v1Before = structuredClone(v1)
    const inputsBefore = structuredClone(inputs)

    const migrated = migrateLeagueSnapshotV1ToV2(v1, inputs)

    expect(migrated.league).toEqual(v1.league)
    expect(v1).toEqual(v1Before)
    expect(inputs).toEqual(inputsBefore)
  })
})

function createDirectExpectedSnapshot(
  v1: ReturnType<typeof createLeagueSnapshotV1Fixture>,
  inputs: SeasonFoundationConfiguration,
): {
  readonly foundation: ReturnType<typeof createSeasonFoundation>
  readonly expectedSnapshot: LeagueSnapshotV2
} {
  const foundation = createSeasonFoundation({ league: v1.league, ...inputs })
  const expectedSnapshot = parseLeagueSnapshotV2(
    serializeLeagueSnapshotV2({
      rootSeed: v1.rootSeed,
      managedTeamId: v1.managedTeamId,
      league: v1.league,
      foundation,
      creationInputs: inputs,
    }),
  )
  return { foundation, expectedSnapshot }
}

function captureMigrationError(
  operation: () => unknown,
): LeagueSnapshotV1ToV2MigrationError {
  let caught: unknown
  try {
    operation()
  } catch (error) {
    caught = error
  }

  expect(caught).toBeInstanceOf(LeagueSnapshotV1ToV2MigrationError)
  if (!(caught instanceof LeagueSnapshotV1ToV2MigrationError)) {
    throw new Error('Expected a structured V1-to-V2 migration error')
  }
  return caught
}

function deepFreeze<Value>(value: Value): Value {
  if (value === null || typeof value !== 'object') return value

  for (const key of Reflect.ownKeys(value)) {
    const descriptor = Object.getOwnPropertyDescriptor(value, key)
    if (descriptor !== undefined && 'value' in descriptor) {
      deepFreeze(descriptor.value)
    }
  }
  return Object.freeze(value)
}

type MutableRecord = Record<string, unknown>

// Compile-time coverage keeps the migration boundary aligned with the exported
// coordinator input instead of introducing a parallel configuration shape.
const _configurationTypeCheck: SeasonFoundationConfigurationInput =
  V2_FIXTURE_CREATION_INPUTS
void _configurationTypeCheck
