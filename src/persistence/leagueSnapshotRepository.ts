import { parseLeagueId } from '../domain/ids'
import type { LeagueId } from '../domain/ids'
import { parseLeagueSnapshot } from './leagueSnapshot'
import type { LeagueSnapshotV1 } from './leagueSnapshot'

/**
 * The browser-specific storage boundary. Values restored from browser storage
 * remain unknown until the repository validates them.
 */
export interface LeagueSnapshotStorage {
  restore(): Promise<unknown | null>
  create(snapshot: unknown, leagueId: LeagueId): Promise<void>
  update(
    snapshot: unknown,
    expectedLeagueId: LeagueId,
    nextLeagueId: LeagueId,
  ): Promise<void>
  clear(expectedLeagueId?: LeagueId): Promise<void>
}

/** Application-facing access to the one active league snapshot. */
export interface LeagueSnapshotRepository {
  restore(): Promise<LeagueSnapshotV1 | null>
  create(snapshot: LeagueSnapshotV1): Promise<void>
  update(
    snapshot: LeagueSnapshotV1,
    expectedLeagueId: LeagueId,
  ): Promise<void>
  clear(expectedLeagueId?: LeagueId): Promise<void>
}

export class LeagueSnapshotStorageError extends Error {
  constructor(message: string, cause?: unknown) {
    super(message, cause === undefined ? undefined : { cause })
    this.name = 'LeagueSnapshotStorageError'
  }
}

export class LeagueSnapshotConflictError extends LeagueSnapshotStorageError {
  constructor(message: string, cause?: unknown) {
    super(message, cause)
    this.name = 'LeagueSnapshotConflictError'
  }
}

export class LeagueSnapshotQuotaError extends LeagueSnapshotStorageError {
  constructor(message: string, cause?: unknown) {
    super(message, cause)
    this.name = 'LeagueSnapshotQuotaError'
  }
}

/**
 * Adds validation to an injected storage adapter. In particular, restoring a
 * snapshot never regenerates league data and never trusts a browser value by
 * assertion alone.
 */
export function createLeagueSnapshotRepository(
  storage: LeagueSnapshotStorage,
): LeagueSnapshotRepository {
  return {
    async restore() {
      const storedSnapshot = await storage.restore()
      return storedSnapshot === null
        ? null
        : parseLeagueSnapshot(storedSnapshot)
    },

    async create(snapshot) {
      const parsedSnapshot = parseLeagueSnapshot(snapshot)
      await storage.create(parsedSnapshot, parsedSnapshot.league.id)
    },

    async update(snapshot, expectedLeagueId) {
      const parsedSnapshot = parseLeagueSnapshot(snapshot)
      const parsedExpectedLeagueId = parseLeagueId(expectedLeagueId)

      if (parsedSnapshot.league.id !== parsedExpectedLeagueId) {
        throw new LeagueSnapshotConflictError(
          'An active league update cannot replace a different league',
        )
      }

      await storage.update(
        parsedSnapshot,
        parsedExpectedLeagueId,
        parsedSnapshot.league.id,
      )
    },

    async clear(expectedLeagueId) {
      await storage.clear(
        expectedLeagueId === undefined
          ? undefined
          : parseLeagueId(expectedLeagueId),
      )
    },
  }
}
