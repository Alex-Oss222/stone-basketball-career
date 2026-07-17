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
  LEAGUE_SNAPSHOT_VERSION,
  parseLeagueSnapshot,
} from '../../src/persistence/leagueSnapshot'
import type { LeagueSnapshot } from '../../src/persistence/leagueSnapshot'
import {
  createLeagueSnapshotFixture,
  createLegacyVersionSnapshotFixture,
} from './leagueSnapshot.fixture'
import {
  TransactionalMemoryLeagueSnapshotStorage,
  absentStorageSlot,
  presentStorageSlot,
} from './helpers/transactionalMemoryLeagueSnapshotStorage'
import type { TransactionalMemoryStorageOptions } from './helpers/transactionalMemoryLeagueSnapshotStorage'

describe('LeagueSnapshot repository restoration', () => {
  it('returns explicit empty and restored states', async () => {
    const empty = createRepository()
    await expect(empty.repository.restore()).resolves.toEqual({ kind: 'empty' })

    const snapshot = createLeagueSnapshotFixture()
    const populated = createRepository(presentStorageSlot(stored(snapshot)))
    const restored = await populated.repository.restore()
    expect(restored).toEqual({ kind: 'restored', snapshot })
    if (restored.kind !== 'restored') {
      throw new Error('Expected a restored snapshot')
    }
    expect(restored.snapshot).not.toBe(snapshot)
    expect(restored.snapshot.leagueSchedule).not.toBe(snapshot.leagueSchedule)
  })

  it('refuses a stored snapshot from a past monotonic version and never mutates it', async () => {
    const legacyRecord = stored2(createLegacyVersionSnapshotFixture(2))
    const initialSlot = presentStorageSlot(legacyRecord)
    const { repository, storage } = createRepository(initialSlot)

    await expect(repository.restore()).resolves.toEqual({
      kind: 'version-mismatch',
      storedVersion: 2,
      supportedVersion: LEAGUE_SNAPSHOT_VERSION,
    })
    expect(storage.inspect()).toEqual(initialSlot)
    expect(storage.operations).not.toContain('clear')
    expect(storage.operations).not.toContain('write:add')
    expect(storage.operations).not.toContain('write:put')
  })

  it('refuses a version-1 record for the same reason', async () => {
    const { repository } = createRepository(
      presentStorageSlot(stored2(createLegacyVersionSnapshotFixture(1))),
    )

    await expect(repository.restore()).resolves.toMatchObject({
      kind: 'version-mismatch',
      storedVersion: 1,
    })
  })

  it('returns recovery-required for an invalid current-version snapshot', async () => {
    const invalid = record(stored(createLeagueSnapshotFixture()))
    delete record(invalid.snapshot).season
    const { repository } = createRepository(presentStorageSlot(invalid))

    const result = await repository.restore()
    expect(result).toMatchObject({
      kind: 'recovery-required',
      source: 'snapshot',
    })
    expect(result).not.toHaveProperty('snapshot')
  })

  it('treats a present slot containing null as corruption rather than empty', async () => {
    const { repository } = createRepository(presentStorageSlot(null))

    await expect(repository.restore()).resolves.toMatchObject({
      kind: 'recovery-required',
      source: 'snapshot',
    })
  })

  it('classifies unsupported rule-set versions for recovery', async () => {
    const unsupportedRuleSet = record(stored(createLeagueSnapshotFixture()))
    record(record(unsupportedRuleSet.snapshot).creationMetadata)
      .scheduleRuleSetVersion = 99
    const { repository } = createRepository(
      presentStorageSlot(unsupportedRuleSet),
    )

    await expect(repository.restore()).resolves.toMatchObject({
      kind: 'recovery-required',
      source: 'snapshot',
      reason: 'unsupported-rule-set-version',
    })
  })

  it('classifies an unknown rule-set ID as rule-set incompatibility', async () => {
    const unknownRuleSet = record(stored(createLeagueSnapshotFixture()))
    record(record(unknownRuleSet.snapshot).creationMetadata)
      .scheduleRuleSetId = 'schedule_rules_unknown_repository_test'
    const { repository } = createRepository(presentStorageSlot(unknownRuleSet))

    await expect(repository.restore()).resolves.toMatchObject({
      kind: 'recovery-required',
      source: 'snapshot',
      reason: 'unsupported-rule-set-version',
    })
  })

  it('returns a structured storage recovery state when the read fails', async () => {
    const { repository } = createRepository(undefined, { failPhase: 'read' })

    await expect(repository.restore()).resolves.toMatchObject({
      kind: 'recovery-required',
      source: 'storage',
      reason: 'storage-failure',
    })
  })
})

describe('LeagueSnapshot creation and revision protection', () => {
  it('creates directly at the active location at revision 1', async () => {
    const snapshot = createLeagueSnapshotFixture(null)
    const { repository, storage } = createRepository()

    const created = await repository.create(snapshot)

    expect(created).toEqual(snapshot)
    expect(created.revision).toBe(1)
    expect(storedSnapshot(storage.inspect().value)).toEqual(snapshot)
    expect(storage.operations).toContain('write:add')
  })

  it('rejects a noninitial creation revision without writing', async () => {
    const snapshot = { ...createLeagueSnapshotFixture(), revision: 2 }
    const { repository, storage } = createRepository()

    await expect(repository.create(snapshot)).rejects.toBeInstanceOf(
      LeagueSnapshotRevisionError,
    )
    expect(storage.inspect()).toEqual(absentStorageSlot())
  })

  it('does not overwrite an existing record with a fresh creation', async () => {
    const initialSlot = presentStorageSlot(stored(createLeagueSnapshotFixture()))
    const { repository, storage } = createRepository(initialSlot)

    await expect(
      repository.create(createLeagueSnapshotFixture()),
    ).rejects.toBeInstanceOf(LeagueSnapshotConflictError)
    expect(storage.inspect()).toEqual(initialSlot)
  })

  it('rolls back creation when the commit fails', async () => {
    const { repository, storage } = createRepository(undefined, {
      failPhase: 'commit',
    })

    await expect(
      repository.create(createLeagueSnapshotFixture()),
    ).rejects.toBeInstanceOf(LeagueSnapshotStorageError)
    expect(storage.inspect()).toEqual(absentStorageSlot())
  })

  it('increments exactly once per managed-team update and preserves all other data', async () => {
    const initial = createLeagueSnapshotFixture(null)
    const { repository, storage } = createRepository(
      presentStorageSlot(stored(initial)),
    )
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
    expect(storedSnapshot(storage.inspect().value)).toEqual(third)
    expect(storage.operations.filter((item) => item === 'write:put')).toHaveLength(2)
  })

  it('rejects a stale update without mutation or revision increment', async () => {
    const initial = createLeagueSnapshotFixture()
    const { repository, storage } = createRepository(
      presentStorageSlot(stored(initial)),
    )
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
    expect(storedSnapshot(storage.inspect().value)).toEqual(current)
  })

  it('rejects revision overflow without writing', async () => {
    const maximumRevisionSnapshot = parseLeagueSnapshot({
      ...createLeagueSnapshotFixture(),
      revision: Number.MAX_SAFE_INTEGER,
    })
    const initialSlot = presentStorageSlot(stored(maximumRevisionSnapshot))
    const { repository, storage } = createRepository(initialSlot)

    await expect(
      repository.updateManagedTeam({
        expectedLeagueId: maximumRevisionSnapshot.league.id,
        expectedRevision: Number.MAX_SAFE_INTEGER,
        managedTeamId: maximumRevisionSnapshot.league.teams[0].id,
      }),
    ).rejects.toBeInstanceOf(LeagueSnapshotRevisionError)
    expect(storage.inspect()).toEqual(initialSlot)
  })

  it('rolls back an update when persistence cannot commit', async () => {
    const initial = createLeagueSnapshotFixture()
    const { repository, storage } = createRepository(
      presentStorageSlot(stored(initial)),
    )
    storage.setFailure('commit')

    await expect(
      repository.updateManagedTeam({
        expectedLeagueId: initial.league.id,
        expectedRevision: 1,
        managedTeamId: initial.league.teams[1].id,
      }),
    ).rejects.toBeInstanceOf(LeagueSnapshotStorageError)
    expect(storedSnapshot(storage.inspect().value)).toEqual(initial)
  })

  it('rejects foreign managed teams without writing', async () => {
    const initial = createLeagueSnapshotFixture()
    const { repository, storage } = createRepository(
      presentStorageSlot(stored(initial)),
    )
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
    const snapshot = createLeagueSnapshotFixture()
    const { repository, storage } = createRepository()
    await repository.create(snapshot)

    const propertyNames = collectPropertyNames(storage.inspect().value)
    expect(propertyNames).not.toContain('timestamp')
    expect(propertyNames).not.toContain('createdAt')
    expect(propertyNames).not.toContain('updatedAt')
    expect(propertyNames.filter((name) => name === 'revision')).toHaveLength(1)
  })
})

describe('LeagueSnapshot repository clear semantics', () => {
  it('clears the active record at the current revision', async () => {
    const snapshot = createLeagueSnapshotFixture()
    const { repository, storage } = createRepository(
      presentStorageSlot(stored(snapshot)),
    )

    await repository.clear({
      kind: 'snapshot',
      expectedLeagueId: snapshot.league.id,
      expectedRevision: 1,
    })

    expect(storage.inspect()).toEqual(absentStorageSlot())
    expect(storage.operations).toContain('clear')
    await expect(repository.restore()).resolves.toEqual({ kind: 'empty' })
  })

  it('supports the full new-league flow after clear: create then restore', async () => {
    const first = createLeagueSnapshotFixture()
    const { repository, storage } = createRepository(
      presentStorageSlot(stored(first)),
    )

    await repository.clear({
      kind: 'snapshot',
      expectedLeagueId: first.league.id,
      expectedRevision: 1,
    })
    expect(storage.inspect()).toEqual(absentStorageSlot())

    const created = await repository.create(createLeagueSnapshotFixture(null))
    await expect(repository.restore()).resolves.toEqual({
      kind: 'restored',
      snapshot: created,
    })
  })

  it('rejects a stale snapshot clear and preserves the record', async () => {
    const initialSlot = presentStorageSlot(stored(createLeagueSnapshotFixture()))
    const { repository, storage } = createRepository(initialSlot)

    await expect(
      repository.clear({
        kind: 'snapshot',
        expectedLeagueId: createLeagueSnapshotFixture().league.id,
        expectedRevision: 2,
      }),
    ).rejects.toBeInstanceOf(LeagueSnapshotStaleWriteError)
    expect(storage.inspect()).toEqual(initialSlot)
  })

  it('clears a refused older-version record only through the version-mismatch expectation', async () => {
    const legacyRecord = stored2(createLegacyVersionSnapshotFixture(2))
    const { repository, storage } = createRepository(
      presentStorageSlot(legacyRecord),
    )

    await repository.clear({
      kind: 'version-mismatch',
      expectedStoredVersion: 2,
    })

    expect(storage.inspect()).toEqual(absentStorageSlot())
    await expect(repository.restore()).resolves.toEqual({ kind: 'empty' })
  })

  it('rejects a version-mismatch clear whose expected stored version has changed', async () => {
    const legacyRecord = stored2(createLegacyVersionSnapshotFixture(2))
    const initialSlot = presentStorageSlot(legacyRecord)
    const { repository, storage } = createRepository(initialSlot)

    await expect(
      repository.clear({
        kind: 'version-mismatch',
        expectedStoredVersion: 1,
      }),
    ).rejects.toBeInstanceOf(LeagueSnapshotConflictError)
    expect(storage.inspect()).toEqual(initialSlot)
  })

  it('does not let a version-mismatch clear delete a valid current-version record', async () => {
    const snapshot = createLeagueSnapshotFixture()
    const initialSlot = presentStorageSlot(stored(snapshot))
    const { repository, storage } = createRepository(initialSlot)

    await expect(
      repository.clear({
        kind: 'version-mismatch',
        expectedStoredVersion: 2,
      }),
    ).rejects.toBeInstanceOf(LeagueSnapshotConflictError)
    expect(storage.inspect()).toEqual(initialSlot)
  })

  it('rolls back the delete when clear cannot commit', async () => {
    const snapshot = createLeagueSnapshotFixture()
    const initialSlot = presentStorageSlot(stored(snapshot))
    const { repository, storage } = createRepository(initialSlot, {
      failPhase: 'commit',
    })

    await expect(
      repository.clear({
        kind: 'snapshot',
        expectedLeagueId: snapshot.league.id,
        expectedRevision: snapshot.revision,
      }),
    ).rejects.toBeInstanceOf(LeagueSnapshotStorageError)
    expect(storage.inspect()).toEqual(initialSlot)
    await expect(repository.restore()).resolves.toMatchObject({
      kind: 'restored',
      snapshot,
    })
  })
})

describe('LeagueSnapshot corrupt-storage recovery purge', () => {
  it('does not let the normal guarded clear bypass an unreadable record', async () => {
    const initialSlot = presentStorageSlot(null)
    const { repository, storage } = createRepository(initialSlot)

    await expect(repository.restore()).resolves.toMatchObject({
      kind: 'recovery-required',
      source: 'snapshot',
    })

    await expect(
      repository.clear({
        kind: 'snapshot',
        expectedLeagueId: parseLeagueId('league_corrupt_recovery_test'),
        expectedRevision: 1,
      }),
    ).rejects.toThrow()

    expect(storage.inspect()).toEqual(initialSlot)
    expect(storage.operations).not.toContain('clear')
  })

  it('atomically purges an unreadable record', async () => {
    const initialSlot = presentStorageSlot(null)
    const { repository, storage } = createRepository(initialSlot)

    await repository.purgeCorruptLeagueStorage()

    expect(storage.inspect()).toEqual(absentStorageSlot())
    expect(storage.operations).toContain('clear')
    expect(storage.operations).toContain('commit')
    await expect(repository.restore()).resolves.toEqual({ kind: 'empty' })
  })

  it('reports a structured failed purge, preserves the record, and permits a successful retry', async () => {
    const initialSlot = presentStorageSlot(null)
    const { repository, storage } = createRepository(initialSlot, {
      failPhase: 'commit',
    })

    await expect(repository.purgeCorruptLeagueStorage()).rejects.toMatchObject({
      name: 'LeagueSnapshotStorageError',
      phase: 'commit',
    })
    expect(storage.inspect()).toEqual(initialSlot)

    storage.setFailure(undefined)
    await repository.purgeCorruptLeagueStorage()

    expect(storage.inspect()).toEqual(absentStorageSlot())
    await expect(repository.restore()).resolves.toEqual({ kind: 'empty' })
  })
})

function createRepository(
  initial: { readonly present: boolean; readonly value: unknown } =
    absentStorageSlot(),
  options: TransactionalMemoryStorageOptions = {},
) {
  const storage = new TransactionalMemoryLeagueSnapshotStorage(initial, options)
  return { storage, repository: createLeagueSnapshotRepository(storage) }
}

function stored(snapshot: LeagueSnapshot): unknown {
  return clone(createStoredLeagueSnapshotRecord(snapshot))
}

/** Wraps an untyped legacy DTO in the stored-record envelope. */
function stored2(snapshot: unknown): unknown {
  const dto = record(structuredClone(snapshot))
  return { leagueId: record(dto.league).id, snapshot: dto }
}

function storedSnapshot(value: unknown): LeagueSnapshot {
  return parseLeagueSnapshot(record(value).snapshot)
}

function withoutMutableRepositoryFields(snapshot: LeagueSnapshot) {
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
