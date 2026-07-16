import { describe, expect, it } from 'vitest'
import { parseLeagueId, parseTeamId } from '../../src/domain/ids'
import {
  LeagueSnapshotConflictError,
  LeagueSnapshotRevisionError,
  LeagueSnapshotStaleWriteError,
  LeagueSnapshotStorageError,
  createLeagueSnapshotRepository,
  createStoredLeagueSnapshotRecord,
} from '../../src/persistence/leagueSnapshotRepository'
import {
  parseLeagueSnapshotV2,
} from '../../src/persistence/leagueSnapshotV2'
import type { LeagueSnapshotV2 } from '../../src/persistence/leagueSnapshotV2'
import {
  LeagueSnapshotRepositoryMigrationError,
} from '../../src/persistence/leagueSnapshotRepository'
import {
  V2_FIXTURE_CREATION_INPUTS,
  createLeagueSnapshotV1Fixture,
  createLeagueSnapshotV2Fixture,
} from './leagueSnapshotV2.fixture'
import {
  TransactionalMemoryLeagueSnapshotStorage,
  absentStorageSlot,
  presentStorageSlot,
} from './helpers/transactionalMemoryLeagueSnapshotStorage'
import type { TransactionalMemoryStorageOptions } from './helpers/transactionalMemoryLeagueSnapshotStorage'

describe('LeagueSnapshot V2 repository restoration precedence', () => {
  it('returns explicit empty, migration-required, and restored-v2 states', async () => {
    const empty = createRepository()
    await expect(empty.repository.restore()).resolves.toEqual({ kind: 'empty' })

    const v1 = createLeagueSnapshotV1Fixture()
    const v1Only = createRepository({
      v1: presentStorageSlot(stored(v1)),
      v2: absentStorageSlot(),
    })
    const migrationRequired = await v1Only.repository.restore()
    expect(migrationRequired).toEqual({
      kind: 'migration-required',
      snapshotVersion: 1,
      leagueId: v1.league.id,
    })
    expect(migrationRequired).not.toHaveProperty('snapshot')
    expect(migrationRequired).not.toHaveProperty('league')

    const v2 = createLeagueSnapshotV2Fixture()
    const v2Only = createRepository({
      v1: absentStorageSlot(),
      v2: presentStorageSlot(stored(v2)),
    })
    const restored = await v2Only.repository.restore()
    expect(restored).toEqual({ kind: 'restored-v2', snapshot: v2 })
    if (restored.kind !== 'restored-v2') {
      throw new Error('Expected a restored V2 snapshot')
    }
    expect(restored.snapshot).not.toBe(v2)
    expect(restored.snapshot.leagueSchedule).not.toBe(v2.leagueSchedule)
  })

  it('prefers a valid V2 whenever both versioned locations are populated', async () => {
    const v1 = createLeagueSnapshotV1Fixture()
    const v2 = createLeagueSnapshotV2Fixture()
    const { repository } = createRepository({
      v1: presentStorageSlot(stored(v1)),
      v2: presentStorageSlot(stored(v2)),
    })

    await expect(repository.restore()).resolves.toEqual({
      kind: 'restored-v2',
      snapshot: v2,
    })
  })

  it('does not inspect or reject an older invalid V1 when V2 is valid', async () => {
    const invalidV1 = record(stored(createLeagueSnapshotV1Fixture()))
    delete record(invalidV1.snapshot).rootSeed
    const v2 = createLeagueSnapshotV2Fixture()
    const { repository } = createRepository({
      v1: presentStorageSlot(invalidV1),
      v2: presentStorageSlot(stored(v2)),
    })

    await expect(repository.restore()).resolves.toEqual({
      kind: 'restored-v2',
      snapshot: v2,
    })
  })

  it('returns recovery-required for invalid V1 when no V2 exists', async () => {
    const invalidV1 = record(stored(createLeagueSnapshotV1Fixture()))
    delete record(invalidV1.snapshot).rootSeed
    const { repository } = createRepository({
      v1: presentStorageSlot(invalidV1),
      v2: absentStorageSlot(),
    })

    const result = await repository.restore()
    expect(result).toMatchObject({
      kind: 'recovery-required',
      source: 'v1',
      v1Present: true,
      v2Present: false,
      v1FallbackBlocked: false,
    })
    expect(result).not.toHaveProperty('snapshot')
  })

  it('never falls back to valid V1 when authoritative V2 is invalid', async () => {
    const invalidV2 = record(stored(createLeagueSnapshotV2Fixture()))
    delete record(invalidV2.snapshot).season
    const { repository } = createRepository({
      v1: presentStorageSlot(stored(createLeagueSnapshotV1Fixture())),
      v2: presentStorageSlot(invalidV2),
    })

    const result = await repository.restore()
    expect(result).toMatchObject({
      kind: 'recovery-required',
      source: 'v2',
      v1Present: true,
      v2Present: true,
      v1FallbackBlocked: true,
    })
    expect(result).not.toHaveProperty('snapshot')
  })

  it.each([null, undefined])(
    'treats a present V2 key containing %s as corruption and blocks V1 fallback',
    async (invalidStoredValue) => {
      const { repository } = createRepository({
        v1: presentStorageSlot(stored(createLeagueSnapshotV1Fixture())),
        v2: presentStorageSlot(invalidStoredValue),
      })

      await expect(repository.restore()).resolves.toMatchObject({
        kind: 'recovery-required',
        source: 'v2',
        v1Present: true,
        v2Present: true,
        v1FallbackBlocked: true,
      })
    },
  )

  it('treats a present V1 key containing null as corruption rather than empty', async () => {
    const { repository } = createRepository({
      v1: presentStorageSlot(null),
      v2: absentStorageSlot(),
    })

    await expect(repository.restore()).resolves.toMatchObject({
      kind: 'recovery-required',
      source: 'v1',
      v1Present: true,
      v2Present: false,
      v1FallbackBlocked: false,
    })
  })

  it('classifies unsupported V2 snapshot and rule-set versions for recovery', async () => {
    const unsupportedSnapshot = record(stored(createLeagueSnapshotV2Fixture()))
    record(unsupportedSnapshot.snapshot).snapshotVersion = 3
    const snapshotRepository = createRepository({
      v1: presentStorageSlot(stored(createLeagueSnapshotV1Fixture())),
      v2: presentStorageSlot(unsupportedSnapshot),
    }).repository
    await expect(snapshotRepository.restore()).resolves.toMatchObject({
      kind: 'recovery-required',
      source: 'v2',
      reason: 'unsupported-snapshot-version',
      v1FallbackBlocked: true,
    })

    const unsupportedRuleSet = record(stored(createLeagueSnapshotV2Fixture()))
    record(record(unsupportedRuleSet.snapshot).creationMetadata)
      .scheduleRuleSetVersion = 99
    const ruleRepository = createRepository({
      v1: absentStorageSlot(),
      v2: presentStorageSlot(unsupportedRuleSet),
    }).repository
    await expect(ruleRepository.restore()).resolves.toMatchObject({
      kind: 'recovery-required',
      source: 'v2',
      reason: 'unsupported-rule-set-version',
    })
  })

  it('classifies an unknown rule-set ID as rule-set incompatibility', async () => {
    const unknownRuleSet = record(stored(createLeagueSnapshotV2Fixture()))
    record(record(unknownRuleSet.snapshot).creationMetadata)
      .scheduleRuleSetId = 'schedule_rules_unknown_repository_test'
    const { repository } = createRepository({
      v1: absentStorageSlot(),
      v2: presentStorageSlot(unknownRuleSet),
    })

    await expect(repository.restore()).resolves.toMatchObject({
      kind: 'recovery-required',
      source: 'v2',
      reason: 'unsupported-rule-set-version',
    })
  })

  it('returns a structured storage recovery state when the versioned read fails', async () => {
    const { repository } = createRepository(undefined, { failPhase: 'read' })

    await expect(repository.restore()).resolves.toMatchObject({
      kind: 'recovery-required',
      source: 'storage',
      reason: 'storage-failure',
      v1Present: false,
      v2Present: false,
      v1FallbackBlocked: false,
    })
  })
})

describe('LeagueSnapshot V1-to-V2 repository migration', () => {
  it('atomically writes revision 1 to V2 while preserving the V1 record', async () => {
    const v1 = createLeagueSnapshotV1Fixture()
    const originalV1Record = stored(v1)
    const { repository, storage } = createRepository({
      v1: presentStorageSlot(originalV1Record),
      v2: absentStorageSlot(),
    })

    const migrated = await repository.migrateV1ToV2({
      expectedV1LeagueId: v1.league.id,
      seasonCreationInputs: V2_FIXTURE_CREATION_INPUTS,
    })

    expect(migrated).toEqual(createLeagueSnapshotV2Fixture())
    expect(migrated.revision).toBe(1)
    expect(storage.inspect().v1).toEqual(
      presentStorageSlot(originalV1Record),
    )
    expect(storedSnapshot(storage.inspect().v2.value)).toEqual(migrated)
    expect(storage.operations).toContain('write-v2:add')
    expect(storage.operations).not.toContain('clear-v1')
    expect(storage.operations).not.toContain('clear-v2')
    await expect(repository.restore()).resolves.toEqual({
      kind: 'restored-v2',
      snapshot: migrated,
    })
  })

  it('leaves V1 authoritative when pure migration rejects explicit inputs', async () => {
    const v1 = createLeagueSnapshotV1Fixture()
    const before = stored(v1)
    const { repository, storage } = createRepository({
      v1: presentStorageSlot(before),
      v2: absentStorageSlot(),
    })

    await expect(
      repository.migrateV1ToV2({
        expectedV1LeagueId: v1.league.id,
        seasonCreationInputs: {
          ...V2_FIXTURE_CREATION_INPUTS,
          calendarDaySpacing: 0,
        },
      }),
    ).rejects.toMatchObject({
      name: 'LeagueSnapshotRepositoryMigrationError',
      stage: 'pure-migration',
    })

    expect(storage.inspect()).toEqual({
      v1: presentStorageSlot(before),
      v2: absentStorageSlot(),
    })
    await expect(repository.restore()).resolves.toMatchObject({
      kind: 'migration-required',
      leagueId: v1.league.id,
    })
  })

  it('rejects a changed V1 identity and leaves migration retryable', async () => {
    const v1 = createLeagueSnapshotV1Fixture()
    const initialState = {
      v1: presentStorageSlot(stored(v1)),
      v2: absentStorageSlot(),
    }
    const { repository, storage } = createRepository(initialState)

    await expect(
      repository.migrateV1ToV2({
        expectedV1LeagueId: parseLeagueId('league_stale_migration'),
        seasonCreationInputs: V2_FIXTURE_CREATION_INPUTS,
      }),
    ).rejects.toMatchObject({
      name: 'LeagueSnapshotRepositoryMigrationError',
      stage: 'parse-v1',
      code: 'league_snapshot_repository.migration.v1_identity_changed',
    })

    expect(storage.inspect()).toEqual(initialState)
    await expect(repository.restore()).resolves.toMatchObject({
      kind: 'migration-required',
      leagueId: v1.league.id,
    })
  })

  it('wraps an invalid expected V1 identity as a structured migration error', async () => {
    const v1 = createLeagueSnapshotV1Fixture()
    const initialState = {
      v1: presentStorageSlot(stored(v1)),
      v2: absentStorageSlot(),
    }
    const { repository, storage } = createRepository(initialState)

    await expect(
      repository.migrateV1ToV2({
        expectedV1LeagueId: '' as ReturnType<typeof parseLeagueId>,
        seasonCreationInputs: V2_FIXTURE_CREATION_INPUTS,
      }),
    ).rejects.toMatchObject({
      name: 'LeagueSnapshotRepositoryMigrationError',
      stage: 'parse-v1',
      code: 'league_snapshot_repository.migration.v1_identity_invalid',
    })
    expect(storage.inspect()).toEqual(initialState)
  })

  it('never replaces an already authoritative V2 during migration', async () => {
    const v1 = createLeagueSnapshotV1Fixture()
    const v2 = createLeagueSnapshotV2Fixture()
    const initialState = {
      v1: presentStorageSlot(stored(v1)),
      v2: presentStorageSlot(stored(v2)),
    }
    const { repository, storage } = createRepository(initialState)

    await expect(
      repository.migrateV1ToV2({
        expectedV1LeagueId: v1.league.id,
        seasonCreationInputs: V2_FIXTURE_CREATION_INPUTS,
      }),
    ).rejects.toMatchObject({
      name: 'LeagueSnapshotRepositoryMigrationError',
      stage: 'read-v1-storage',
      code: 'league_snapshot_repository.migration.v2_exists',
    })
    expect(storage.inspect()).toEqual(initialState)
  })

  it.each([
    ['write-v2', 'write-v2'],
    ['reread', 'reread-v2'],
    ['commit', 'commit-transaction'],
  ] as const)(
    'rolls back V2 when the storage %s phase fails',
    async (failurePhase, expectedStage) => {
      const v1 = createLeagueSnapshotV1Fixture()
      const before = stored(v1)
      const { repository, storage } = createRepository(
        {
          v1: presentStorageSlot(before),
          v2: absentStorageSlot(),
        },
        { failPhase: failurePhase },
      )

      await expect(
        repository.migrateV1ToV2({
          expectedV1LeagueId: v1.league.id,
          seasonCreationInputs: V2_FIXTURE_CREATION_INPUTS,
        }),
      ).rejects.toMatchObject({
        name: 'LeagueSnapshotRepositoryMigrationError',
        stage: expectedStage,
      })

      expect(storage.inspect()).toEqual({
        v1: presentStorageSlot(before),
        v2: absentStorageSlot(),
      })
    },
  )

  it('rolls back when the re-read V2 fails validation', async () => {
    const v1 = createLeagueSnapshotV1Fixture()
    const before = stored(v1)
    const { repository, storage } = createRepository(
      {
        v1: presentStorageSlot(before),
        v2: absentStorageSlot(),
      },
      {
        transformReread: (state) => {
          const transformed = clone(state)
          delete record(record(transformed.v2.value).snapshot).season
          return transformed
        },
      },
    )

    await expect(
      repository.migrateV1ToV2({
        expectedV1LeagueId: v1.league.id,
        seasonCreationInputs: V2_FIXTURE_CREATION_INPUTS,
      }),
    ).rejects.toMatchObject({
      name: 'LeagueSnapshotRepositoryMigrationError',
      stage: 'revalidate-v2',
    })
    expect(storage.inspect()).toEqual({
      v1: presentStorageSlot(before),
      v2: absentStorageSlot(),
    })
  })

  it('rolls back when a valid re-read V2 differs from the value written', async () => {
    const v1 = createLeagueSnapshotV1Fixture()
    const before = stored(v1)
    const { repository, storage } = createRepository(
      {
        v1: presentStorageSlot(before),
        v2: absentStorageSlot(),
      },
      {
        transformReread: (state) => {
          const transformed = clone(state)
          record(record(transformed.v2.value).snapshot).revision = 2
          return transformed
        },
      },
    )

    await expect(
      repository.migrateV1ToV2({
        expectedV1LeagueId: v1.league.id,
        seasonCreationInputs: V2_FIXTURE_CREATION_INPUTS,
      }),
    ).rejects.toMatchObject({
      name: 'LeagueSnapshotRepositoryMigrationError',
      stage: 'compare-v2',
    })
    expect(storage.inspect()).toEqual({
      v1: presentStorageSlot(before),
      v2: absentStorageSlot(),
    })
  })
})

describe('LeagueSnapshot V2 creation and revision protection', () => {
  it('creates directly at the V2 location at revision 1', async () => {
    const snapshot = createLeagueSnapshotV2Fixture(null)
    const { repository, storage } = createRepository()

    const created = await repository.createV2(snapshot)

    expect(created).toEqual(snapshot)
    expect(created.revision).toBe(1)
    expect(storage.inspect().v1).toEqual(absentStorageSlot())
    expect(storedSnapshot(storage.inspect().v2.value)).toEqual(snapshot)
    expect(storage.operations).toContain('write-v2:add')
    expect(storage.operations).not.toContain('clear-v1')
  })

  it('rejects a noninitial creation revision without writing', async () => {
    const snapshot = { ...createLeagueSnapshotV2Fixture(), revision: 2 }
    const { repository, storage } = createRepository()

    await expect(repository.createV2(snapshot)).rejects.toBeInstanceOf(
      LeagueSnapshotRevisionError,
    )
    expect(storage.inspect()).toEqual({
      v1: absentStorageSlot(),
      v2: absentStorageSlot(),
    })
  })

  it('does not hide an existing V1 record with direct V2 creation', async () => {
    const v1 = createLeagueSnapshotV1Fixture()
    const initialState = {
      v1: presentStorageSlot(stored(v1)),
      v2: absentStorageSlot(),
    }
    const { repository, storage } = createRepository(initialState)

    await expect(
      repository.createV2(createLeagueSnapshotV2Fixture()),
    ).rejects.toBeInstanceOf(LeagueSnapshotConflictError)
    expect(storage.inspect()).toEqual(initialState)
  })

  it('rolls back direct V2 creation when the commit fails', async () => {
    const { repository, storage } = createRepository(undefined, {
      failPhase: 'commit',
    })

    await expect(
      repository.createV2(createLeagueSnapshotV2Fixture()),
    ).rejects.toBeInstanceOf(LeagueSnapshotStorageError)
    expect(storage.inspect()).toEqual({
      v1: absentStorageSlot(),
      v2: absentStorageSlot(),
    })
  })

  it('increments exactly once for each managed-team update and preserves all other data', async () => {
    const initial = createLeagueSnapshotV2Fixture(null)
    const { repository, storage } = createRepository({
      v1: absentStorageSlot(),
      v2: presentStorageSlot(stored(initial)),
    })
    const selectedTeamId = initial.league.teams[3].id

    const second = await repository.updateManagedTeam({
      expectedLeagueId: initial.league.id,
      expectedRevision: 1,
      managedTeamId: selectedTeamId,
    })
    const third = await repository.updateManagedTeam({
      expectedLeagueId: initial.league.id,
      expectedRevision: 2,
      managedTeamId: null,
    })

    expect(second.revision).toBe(2)
    expect(second.managedTeamId).toBe(selectedTeamId)
    expect(third.revision).toBe(3)
    expect(third.managedTeamId).toBeNull()
    expect(withoutMutableRepositoryFields(second)).toEqual(
      withoutMutableRepositoryFields(initial),
    )
    expect(withoutMutableRepositoryFields(third)).toEqual(
      withoutMutableRepositoryFields(initial),
    )
    expect(storedSnapshot(storage.inspect().v2.value)).toEqual(third)
    expect(storage.operations.filter((item) => item === 'write-v2:put')).toHaveLength(2)
  })

  it('rejects a stale update without mutation or revision increment', async () => {
    const initial = createLeagueSnapshotV2Fixture()
    const { repository, storage } = createRepository({
      v1: absentStorageSlot(),
      v2: presentStorageSlot(stored(initial)),
    })
    const current = await repository.updateManagedTeam({
      expectedLeagueId: initial.league.id,
      expectedRevision: 1,
      managedTeamId: initial.league.teams[2].id,
    })
    const beforeStaleAttempt = storage.inspect()

    await expect(
      repository.updateManagedTeam({
        expectedLeagueId: initial.league.id,
        expectedRevision: 1,
        managedTeamId: initial.league.teams[4].id,
      }),
    ).rejects.toMatchObject({
      name: 'LeagueSnapshotStaleWriteError',
      operation: 'update',
      expectedRevision: 1,
      currentRevision: 2,
    })

    expect(storage.inspect()).toEqual(beforeStaleAttempt)
    expect(storedSnapshot(storage.inspect().v2.value)).toEqual(current)
  })

  it('rejects revision overflow without writing', async () => {
    const maximumRevisionSnapshot = parseLeagueSnapshotV2({
      ...createLeagueSnapshotV2Fixture(),
      revision: Number.MAX_SAFE_INTEGER,
    })
    const initialState = {
      v1: absentStorageSlot(),
      v2: presentStorageSlot(stored(maximumRevisionSnapshot)),
    }
    const { repository, storage } = createRepository(initialState)

    await expect(
      repository.updateManagedTeam({
        expectedLeagueId: maximumRevisionSnapshot.league.id,
        expectedRevision: Number.MAX_SAFE_INTEGER,
        managedTeamId: maximumRevisionSnapshot.league.teams[0].id,
      }),
    ).rejects.toBeInstanceOf(LeagueSnapshotRevisionError)
    expect(storage.inspect()).toEqual(initialState)
  })

  it('rolls back an update when persistence cannot commit', async () => {
    const initial = createLeagueSnapshotV2Fixture()
    const { repository, storage } = createRepository({
      v1: absentStorageSlot(),
      v2: presentStorageSlot(stored(initial)),
    })
    storage.setFailure('commit')

    await expect(
      repository.updateManagedTeam({
        expectedLeagueId: initial.league.id,
        expectedRevision: 1,
        managedTeamId: initial.league.teams[1].id,
      }),
    ).rejects.toBeInstanceOf(LeagueSnapshotStorageError)
    expect(storedSnapshot(storage.inspect().v2.value)).toEqual(initial)
  })

  it('rejects foreign managed teams without writing', async () => {
    const initial = createLeagueSnapshotV2Fixture()
    const { repository, storage } = createRepository({
      v1: absentStorageSlot(),
      v2: presentStorageSlot(stored(initial)),
    })
    const before = storage.inspect()

    await expect(
      repository.updateManagedTeam({
        expectedLeagueId: initial.league.id,
        expectedRevision: 1,
        managedTeamId: parseTeamId('team_foreign_repository_test'),
      }),
    ).rejects.toThrow(/managed team/i)
    expect(storage.inspect()).toEqual(before)
  })

  it('uses only the numeric revision and stores no timestamp metadata', async () => {
    const snapshot = createLeagueSnapshotV2Fixture()
    const { repository, storage } = createRepository()
    await repository.createV2(snapshot)

    const propertyNames = collectPropertyNames(storage.inspect().v2.value)
    expect(propertyNames).not.toContain('timestamp')
    expect(propertyNames).not.toContain('createdAt')
    expect(propertyNames).not.toContain('updatedAt')
    expect(propertyNames.filter((name) => name === 'revision')).toHaveLength(1)
  })
})

describe('LeagueSnapshot repository clear semantics', () => {
  it('clears V1 and V2 together at the current revision so V1 cannot reappear', async () => {
    const v1 = createLeagueSnapshotV1Fixture()
    const v2 = createLeagueSnapshotV2Fixture()
    const { repository, storage } = createRepository({
      v1: presentStorageSlot(stored(v1)),
      v2: presentStorageSlot(stored(v2)),
    })

    await repository.clear({
      kind: 'v2',
      expectedLeagueId: v2.league.id,
      expectedRevision: 1,
    })

    expect(storage.inspect()).toEqual({
      v1: absentStorageSlot(),
      v2: absentStorageSlot(),
    })
    expect(storage.operations).toContain('clear-v1')
    expect(storage.operations).toContain('clear-v2')
    await expect(repository.restore()).resolves.toEqual({ kind: 'empty' })
  })

  it('rejects a stale V2 clear and preserves both records', async () => {
    const initialState = {
      v1: presentStorageSlot(stored(createLeagueSnapshotV1Fixture())),
      v2: presentStorageSlot(stored(createLeagueSnapshotV2Fixture())),
    }
    const { repository, storage } = createRepository(initialState)

    await expect(
      repository.clear({
        kind: 'v2',
        expectedLeagueId: createLeagueSnapshotV2Fixture().league.id,
        expectedRevision: 2,
      }),
    ).rejects.toBeInstanceOf(LeagueSnapshotStaleWriteError)
    expect(storage.inspect()).toEqual(initialState)
  })

  it('clears a V1-only record using its explicit league identity', async () => {
    const v1 = createLeagueSnapshotV1Fixture()
    const { repository, storage } = createRepository({
      v1: presentStorageSlot(stored(v1)),
      v2: absentStorageSlot(),
    })

    await repository.clear({ kind: 'v1', expectedLeagueId: v1.league.id })

    expect(storage.inspect()).toEqual({
      v1: absentStorageSlot(),
      v2: absentStorageSlot(),
    })
  })

  it('rejects a stale V1 clear identity without deleting either location', async () => {
    const v1 = createLeagueSnapshotV1Fixture()
    const initialState = {
      v1: presentStorageSlot(stored(v1)),
      v2: absentStorageSlot(),
    }
    const { repository, storage } = createRepository(initialState)

    await expect(
      repository.clear({
        kind: 'v1',
        expectedLeagueId: parseLeagueId('league_stale_clear'),
      }),
    ).rejects.toBeInstanceOf(LeagueSnapshotConflictError)
    expect(storage.inspect()).toEqual(initialState)
  })

  it('rolls back both deletes when clear cannot commit', async () => {
    const initialState = {
      v1: presentStorageSlot(stored(createLeagueSnapshotV1Fixture())),
      v2: presentStorageSlot(stored(createLeagueSnapshotV2Fixture())),
    }
    const { repository, storage } = createRepository(initialState, {
      failPhase: 'commit',
    })
    const v2 = createLeagueSnapshotV2Fixture()

    await expect(
      repository.clear({
        kind: 'v2',
        expectedLeagueId: v2.league.id,
        expectedRevision: v2.revision,
      }),
    ).rejects.toBeInstanceOf(LeagueSnapshotStorageError)
    expect(storage.inspect()).toEqual(initialState)
    await expect(repository.restore()).resolves.toMatchObject({
      kind: 'restored-v2',
      snapshot: v2,
    })
  })
})

describe('LeagueSnapshot corrupt-storage recovery purge', () => {
  it('does not let the normal guarded clear bypass an unreadable authoritative V2', async () => {
    const v1 = createLeagueSnapshotV1Fixture()
    const initialState = {
      v1: presentStorageSlot(stored(v1)),
      v2: presentStorageSlot(null),
    }
    const { repository, storage } = createRepository(initialState)

    await expect(repository.restore()).resolves.toMatchObject({
      kind: 'recovery-required',
      source: 'v2',
      v1Present: true,
      v2Present: true,
      v1FallbackBlocked: true,
    })

    await expect(
      repository.clear({
        kind: 'v1',
        expectedLeagueId: v1.league.id,
      }),
    ).rejects.toThrow()
    await expect(
      repository.clear({
        kind: 'v2',
        expectedLeagueId: v1.league.id,
        expectedRevision: 1,
      }),
    ).rejects.toThrow()

    expect(storage.inspect()).toEqual(initialState)
    expect(storage.operations).not.toContain('clear-v1')
    expect(storage.operations).not.toContain('clear-v2')
  })

  it('atomically purges unreadable V2 and retained V1 records without resurrecting V1', async () => {
    const initialState = {
      v1: presentStorageSlot(stored(createLeagueSnapshotV1Fixture())),
      v2: presentStorageSlot(null),
    }
    const { repository, storage } = createRepository(initialState)

    await repository.purgeCorruptLeagueStorage()

    expect(storage.inspect()).toEqual({
      v1: absentStorageSlot(),
      v2: absentStorageSlot(),
    })
    expect(storage.operations).toContain('clear-v1')
    expect(storage.operations).toContain('clear-v2')
    expect(storage.operations).toContain('commit')
    await expect(repository.restore()).resolves.toEqual({ kind: 'empty' })
    await expect(repository.restore()).resolves.toEqual({ kind: 'empty' })
  })

  it('reports a structured failed purge, preserves both records, and permits a successful retry', async () => {
    const initialState = {
      v1: presentStorageSlot(stored(createLeagueSnapshotV1Fixture())),
      v2: presentStorageSlot(null),
    }
    const { repository, storage } = createRepository(initialState, {
      failPhase: 'commit',
    })

    await expect(repository.purgeCorruptLeagueStorage()).rejects.toMatchObject({
      name: 'LeagueSnapshotStorageError',
      phase: 'commit',
    })
    expect(storage.inspect()).toEqual(initialState)
    await expect(repository.restore()).resolves.toMatchObject({
      kind: 'recovery-required',
      source: 'v2',
      v1Present: true,
      v2Present: true,
      v1FallbackBlocked: true,
    })

    storage.setFailure(undefined)
    await repository.purgeCorruptLeagueStorage()

    expect(storage.inspect()).toEqual({
      v1: absentStorageSlot(),
      v2: absentStorageSlot(),
    })
    await expect(repository.restore()).resolves.toEqual({ kind: 'empty' })
  })
})

function createRepository(
  initial: {
    readonly v1: { readonly present: boolean; readonly value: unknown }
    readonly v2: { readonly present: boolean; readonly value: unknown }
  } = { v1: absentStorageSlot(), v2: absentStorageSlot() },
  options: TransactionalMemoryStorageOptions = {},
) {
  const storage = new TransactionalMemoryLeagueSnapshotStorage(initial, options)
  return { storage, repository: createLeagueSnapshotRepository(storage) }
}

function stored(
  snapshot: Parameters<typeof createStoredLeagueSnapshotRecord>[0],
): unknown {
  return clone(createStoredLeagueSnapshotRecord(snapshot))
}

function storedSnapshot(value: unknown): LeagueSnapshotV2 {
  return parseLeagueSnapshotV2(record(value).snapshot)
}

function withoutMutableRepositoryFields(snapshot: LeagueSnapshotV2) {
  const { revision: _revision, managedTeamId: _managedTeamId, ...rest } = snapshot
  return rest
}

function record(value: unknown): Record<string, unknown> {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    throw new TypeError('Expected a record fixture')
  }
  return value as Record<string, unknown>
}

function clone<Value>(value: Value): Value {
  return structuredClone(value)
}

function collectPropertyNames(value: unknown): readonly string[] {
  if (Array.isArray(value)) return value.flatMap(collectPropertyNames)
  if (value === null || typeof value !== 'object') return []
  return Object.entries(value).flatMap(([key, nested]) => [
    key,
    ...collectPropertyNames(nested),
  ])
}

// Compile-time assertions keep the public structured error contracts covered.
const _migrationError: typeof LeagueSnapshotRepositoryMigrationError =
  LeagueSnapshotRepositoryMigrationError
void _migrationError
