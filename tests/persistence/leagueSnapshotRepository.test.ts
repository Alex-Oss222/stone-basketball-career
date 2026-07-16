import { describe, expect, it } from 'vitest'
import { parseLeagueId } from '../../src/domain/ids'
import type { LeagueId } from '../../src/domain/ids'
import { RATING_KEYS } from '../../src/domain/ratings'
import { generateLeague } from '../../src/generation/generateLeague'
import {
  InvalidLeagueSnapshotError,
  createLeagueSnapshot,
} from '../../src/persistence/leagueSnapshot'
import {
  LeagueSnapshotConflictError,
  createLeagueSnapshotRepository,
} from '../../src/persistence/leagueSnapshotRepository'
import type { LeagueSnapshotStorage } from '../../src/persistence/leagueSnapshotRepository'

const ROOT_SEED = 'snapshot-repository-fixture'
const league = generateLeague(ROOT_SEED)
const initialSnapshot = createLeagueSnapshot(ROOT_SEED, league, null)

describe('league snapshot repository', () => {
  it('creates and restores a detached validated snapshot', async () => {
    const storage = new CloningMemoryLeagueSnapshotStorage()
    const repository = createLeagueSnapshotRepository(storage)

    await repository.create(initialSnapshot)
    const restored = await repository.restore()

    expect(restored).toEqual(initialSnapshot)
    expect(restored).not.toBe(initialSnapshot)
    expect(restored?.league).not.toBe(initialSnapshot.league)

    const firstRawRestore = record(await storage.restore())
    firstRawRestore.rootSeed = 'mutated-read-copy'
    expect(record(await storage.restore()).rootSeed).toBe(ROOT_SEED)
  })

  it('updates and restores the selected managed team', async () => {
    const storage = new CloningMemoryLeagueSnapshotStorage()
    const repository = createLeagueSnapshotRepository(storage)
    await repository.create(initialSnapshot)

    const selectedTeamId = league.teams[5].id
    const selectedSnapshot = createLeagueSnapshot(
      ROOT_SEED,
      league,
      selectedTeamId,
    )
    await repository.update(selectedSnapshot, league.id)

    expect((await repository.restore())?.managedTeamId).toBe(selectedTeamId)
  })

  it('rejects invalid restored raw data without changing it', async () => {
    const invalidRaw = clone(initialSnapshot)
    firstRatings(invalidRaw).grade = 'A'
    const storage = new CloningMemoryLeagueSnapshotStorage(
      invalidRaw,
      league.id,
    )
    const repository = createLeagueSnapshotRepository(storage)
    const before = await storage.restore()

    await expect(repository.restore()).rejects.toBeInstanceOf(
      InvalidLeagueSnapshotError,
    )

    expect(await storage.restore()).toEqual(before)
  })

  it('clears the active snapshot', async () => {
    const storage = new CloningMemoryLeagueSnapshotStorage()
    const repository = createLeagueSnapshotRepository(storage)
    await repository.create(initialSnapshot)

    await repository.clear(league.id)

    await expect(repository.restore()).resolves.toBeNull()
  })

  it('protects an existing snapshot from create conflicts', async () => {
    const storage = new CloningMemoryLeagueSnapshotStorage()
    const repository = createLeagueSnapshotRepository(storage)
    await repository.create(initialSnapshot)

    const conflictingSnapshot = createLeagueSnapshot(
      ROOT_SEED,
      league,
      league.teams[1].id,
    )
    await expect(repository.create(conflictingSnapshot)).rejects.toBeInstanceOf(
      LeagueSnapshotConflictError,
    )

    expect(await repository.restore()).toEqual(initialSnapshot)
  })

  it('protects an existing snapshot from stale updates and clears', async () => {
    const storage = new CloningMemoryLeagueSnapshotStorage()
    const repository = createLeagueSnapshotRepository(storage)
    await repository.create(initialSnapshot)
    const before = await storage.restore()
    const selectedSnapshot = createLeagueSnapshot(
      ROOT_SEED,
      league,
      league.teams[2].id,
    )
    const staleLeagueId = parseLeagueId('league_stale')

    await expect(
      repository.update(selectedSnapshot, staleLeagueId),
    ).rejects.toBeInstanceOf(LeagueSnapshotConflictError)
    await expect(repository.clear(staleLeagueId)).rejects.toBeInstanceOf(
      LeagueSnapshotConflictError,
    )

    expect(await storage.restore()).toEqual(before)
  })

  it('does not allow an update to replace the active league identity', async () => {
    const storage = new CloningMemoryLeagueSnapshotStorage()
    const repository = createLeagueSnapshotRepository(storage)
    await repository.create(initialSnapshot)
    const differentLeague = generateLeague('different-active-league')
    const replacement = createLeagueSnapshot(
      'different-active-league',
      differentLeague,
      differentLeague.teams[0].id,
    )

    await expect(
      repository.update(replacement, league.id),
    ).rejects.toBeInstanceOf(LeagueSnapshotConflictError)

    expect(await repository.restore()).toEqual(initialSnapshot)
  })

  it('stores only canonical numeric ratings and never derived grades', async () => {
    const storage = new CloningMemoryLeagueSnapshotStorage()
    const repository = createLeagueSnapshotRepository(storage)
    await repository.create(
      createLeagueSnapshot(ROOT_SEED, league, league.teams[0].id),
    )

    const raw = record(await storage.restore())
    const ratings = firstRatings(raw)

    expect(Object.keys(ratings)).toEqual(RATING_KEYS)
    expect(collectPropertyNames(raw)).not.toContain('grade')
    expect(collectPropertyNames(raw)).not.toContain('letterGrade')
  })
})

class CloningMemoryLeagueSnapshotStorage implements LeagueSnapshotStorage {
  private storedSnapshot: unknown | null
  private storedLeagueId: LeagueId | null

  constructor(
    initialSnapshot: unknown | null = null,
    initialLeagueId: LeagueId | null = null,
  ) {
    if ((initialSnapshot === null) !== (initialLeagueId === null)) {
      throw new TypeError('Initial snapshot and league ID must be supplied together')
    }
    this.storedSnapshot = clone(initialSnapshot)
    this.storedLeagueId = initialLeagueId
  }

  async restore(): Promise<unknown | null> {
    return clone(this.storedSnapshot)
  }

  async create(snapshot: unknown, leagueId: LeagueId): Promise<void> {
    if (this.storedSnapshot !== null) {
      throw new LeagueSnapshotConflictError('A league snapshot already exists')
    }

    this.storedSnapshot = clone(snapshot)
    this.storedLeagueId = leagueId
  }

  async update(
    snapshot: unknown,
    expectedLeagueId: LeagueId,
    nextLeagueId: LeagueId,
  ): Promise<void> {
    this.assertCurrentLeague(expectedLeagueId)
    this.storedSnapshot = clone(snapshot)
    this.storedLeagueId = nextLeagueId
  }

  async clear(expectedLeagueId?: LeagueId): Promise<void> {
    if (expectedLeagueId !== undefined) {
      this.assertCurrentLeague(expectedLeagueId)
    }
    this.storedSnapshot = null
    this.storedLeagueId = null
  }

  private assertCurrentLeague(expectedLeagueId: LeagueId): void {
    if (
      this.storedSnapshot === null ||
      this.storedLeagueId !== expectedLeagueId
    ) {
      throw new LeagueSnapshotConflictError(
        'Stored league changed before the operation completed',
      )
    }
  }
}

type MutableRecord = Record<string, unknown>

function clone<T>(value: T): T {
  return structuredClone(value)
}

function record(value: unknown): MutableRecord {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    throw new TypeError('Test fixture value is not a record')
  }
  return value as MutableRecord
}

function array(value: unknown): unknown[] {
  if (!Array.isArray(value)) {
    throw new TypeError('Test fixture value is not an array')
  }
  return value
}

function firstRatings(snapshot: unknown): MutableRecord {
  const snapshotLeague = record(record(snapshot).league)
  const firstPlayer = record(array(snapshotLeague.players)[0])
  return record(firstPlayer.ratings)
}

function collectPropertyNames(value: unknown): readonly string[] {
  if (Array.isArray(value)) {
    return value.flatMap(collectPropertyNames)
  }
  if (value === null || typeof value !== 'object') {
    return []
  }

  return Object.entries(value).flatMap(([key, nestedValue]) => [
    key,
    ...collectPropertyNames(nestedValue),
  ])
}
