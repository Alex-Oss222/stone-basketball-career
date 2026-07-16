import { isLeagueId } from '../domain/ids'
import type { LeagueId } from '../domain/ids'
import {
  LeagueSnapshotConflictError,
  LeagueSnapshotQuotaError,
  LeagueSnapshotStorageError,
  createLeagueSnapshotRepository,
} from './leagueSnapshotRepository'
import type {
  LeagueSnapshotRepository,
  LeagueSnapshotStorage,
} from './leagueSnapshotRepository'
import { InvalidLeagueSnapshotError } from './leagueSnapshot'

export {
  LeagueSnapshotConflictError,
  LeagueSnapshotQuotaError,
  LeagueSnapshotStorageError,
} from './leagueSnapshotRepository'

export const LEAGUE_SNAPSHOT_DATABASE_NAME = 'stone-basketball-gm'
export const LEAGUE_SNAPSHOT_DATABASE_VERSION = 1
export const LEAGUE_SNAPSHOT_OBJECT_STORE_NAME = 'activeLeague'
export const ACTIVE_LEAGUE_SNAPSHOT_KEY = 'current'

interface StoredLeagueSnapshotRecord {
  readonly leagueId: LeagueId
  readonly snapshot: unknown
}

type AbortWrite = (error: unknown) => void
type RememberWriteError = (error: unknown) => void
type ScheduleWrite = (
  store: IDBObjectStore,
  abort: AbortWrite,
  rememberError: RememberWriteError,
) => void

/** Native IndexedDB storage for the single active league snapshot. */
export class IndexedDbLeagueSnapshotStorage
  implements LeagueSnapshotStorage
{
  private readonly indexedDb: IDBFactory | undefined

  constructor(indexedDb: IDBFactory | undefined = globalThis.indexedDB) {
    this.indexedDb = indexedDb
  }

  async restore(): Promise<unknown | null> {
    return this.withDatabase((database) => readCurrentSnapshot(database))
  }

  async create(snapshot: unknown, leagueId: LeagueId): Promise<void> {
    await this.withDatabase((database) =>
      executeWrite(database, (store, _abort, rememberError) => {
        const request = store.add(
          createStoredRecord(snapshot, leagueId),
          ACTIVE_LEAGUE_SNAPSHOT_KEY,
        )
        request.onerror = () => {
          rememberError(
            request.error?.name === 'ConstraintError'
              ? new LeagueSnapshotConflictError(
                  'An active league snapshot already exists',
                  request.error,
                )
              : request.error,
          )
        }
      }),
    )
  }

  async update(
    snapshot: unknown,
    expectedLeagueId: LeagueId,
    nextLeagueId: LeagueId,
  ): Promise<void> {
    await this.withDatabase((database) =>
      executeWrite(database, (store, abort, rememberError) => {
        const readRequest = store.get(ACTIVE_LEAGUE_SNAPSHOT_KEY)

        readRequest.onerror = () => {
          rememberError(readRequest.error)
        }
        readRequest.onsuccess = () => {
          if (readRequest.result === undefined) {
            abort(
              new LeagueSnapshotConflictError(
                'The active league snapshot no longer exists',
              ),
            )
            return
          }

          let currentRecord: StoredLeagueSnapshotRecord
          try {
            currentRecord = parseStoredRecord(readRequest.result)
          } catch (error) {
            abort(error)
            return
          }

          if (currentRecord.leagueId !== expectedLeagueId) {
            abort(
              new LeagueSnapshotConflictError(
                'The active league snapshot changed before it could be updated',
              ),
            )
            return
          }

          let writeRequest: IDBRequest<IDBValidKey>
          try {
            writeRequest = store.put(
              createStoredRecord(snapshot, nextLeagueId),
              ACTIVE_LEAGUE_SNAPSHOT_KEY,
            )
          } catch (error) {
            abort(error)
            return
          }
          writeRequest.onerror = () => {
            rememberError(writeRequest.error)
          }
        }
      }),
    )
  }

  async clear(expectedLeagueId?: LeagueId): Promise<void> {
    await this.withDatabase((database) =>
      executeWrite(database, (store, abort, rememberError) => {
        if (expectedLeagueId === undefined) {
          const deleteRequest = store.delete(ACTIVE_LEAGUE_SNAPSHOT_KEY)
          deleteRequest.onerror = () => {
            rememberError(deleteRequest.error)
          }
          return
        }

        const readRequest = store.get(ACTIVE_LEAGUE_SNAPSHOT_KEY)
        readRequest.onerror = () => {
          rememberError(readRequest.error)
        }
        readRequest.onsuccess = () => {
          if (readRequest.result === undefined) {
            abort(
              new LeagueSnapshotConflictError(
                'The active league snapshot no longer exists',
              ),
            )
            return
          }

          let currentRecord: StoredLeagueSnapshotRecord
          try {
            currentRecord = parseStoredRecord(readRequest.result)
          } catch (error) {
            abort(error)
            return
          }

          if (currentRecord.leagueId !== expectedLeagueId) {
            abort(
              new LeagueSnapshotConflictError(
                'The active league snapshot changed before it could be cleared',
              ),
            )
            return
          }

          let deleteRequest: IDBRequest<undefined>
          try {
            deleteRequest = store.delete(ACTIVE_LEAGUE_SNAPSHOT_KEY)
          } catch (error) {
            abort(error)
            return
          }
          deleteRequest.onerror = () => {
            rememberError(deleteRequest.error)
          }
        }
      }),
    )
  }

  private async withDatabase<Result>(
    operation: (database: IDBDatabase) => Promise<Result>,
  ): Promise<Result> {
    if (this.indexedDb === undefined) {
      throw new LeagueSnapshotStorageError(
        'IndexedDB is unavailable in this browser',
      )
    }

    const database = await openDatabase(this.indexedDb)
    try {
      return await operation(database)
    } catch (error) {
      throw normalizeStorageError(error)
    } finally {
      database.close()
    }
  }
}

/** Creates the browser-backed repository used by the application layer. */
export function createIndexedDbLeagueSnapshotRepository(
  indexedDb: IDBFactory | undefined = globalThis.indexedDB,
): LeagueSnapshotRepository {
  return createLeagueSnapshotRepository(
    new IndexedDbLeagueSnapshotStorage(indexedDb),
  )
}

function openDatabase(indexedDb: IDBFactory): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    let request: IDBOpenDBRequest
    let rejectedAsBlocked = false

    try {
      request = indexedDb.open(
        LEAGUE_SNAPSHOT_DATABASE_NAME,
        LEAGUE_SNAPSHOT_DATABASE_VERSION,
      )
    } catch (error) {
      reject(normalizeStorageError(error))
      return
    }

    request.onupgradeneeded = () => {
      try {
        if (
          !request.result.objectStoreNames.contains(
            LEAGUE_SNAPSHOT_OBJECT_STORE_NAME,
          )
        ) {
          request.result.createObjectStore(
            LEAGUE_SNAPSHOT_OBJECT_STORE_NAME,
          )
        }
      } catch (error) {
        request.transaction?.abort()
        reject(normalizeStorageError(error))
      }
    }
    request.onerror = () => {
      reject(normalizeStorageError(request.error))
    }
    request.onblocked = () => {
      rejectedAsBlocked = true
      reject(
        new LeagueSnapshotStorageError(
          'IndexedDB is blocked by another open application tab',
        ),
      )
    }
    request.onsuccess = () => {
      const database = request.result
      if (rejectedAsBlocked) {
        database.close()
        return
      }
      if (
        !database.objectStoreNames.contains(
          LEAGUE_SNAPSHOT_OBJECT_STORE_NAME,
        )
      ) {
        database.close()
        reject(
          new LeagueSnapshotStorageError(
            'The IndexedDB league snapshot store is missing',
          ),
        )
        return
      }

      database.onversionchange = () => {
        database.close()
      }
      resolve(database)
    }
  })
}

function readCurrentSnapshot(database: IDBDatabase): Promise<unknown | null> {
  return new Promise((resolve, reject) => {
    let transaction: IDBTransaction
    let request: IDBRequest<unknown>
    let restoredSnapshot: unknown | null = null
    let failure: unknown

    try {
      transaction = database.transaction(
        LEAGUE_SNAPSHOT_OBJECT_STORE_NAME,
        'readonly',
      )
      request = transaction
        .objectStore(LEAGUE_SNAPSHOT_OBJECT_STORE_NAME)
        .get(ACTIVE_LEAGUE_SNAPSHOT_KEY)
    } catch (error) {
      reject(normalizeStorageError(error))
      return
    }

    request.onsuccess = () => {
      if (request.result === undefined) return

      try {
        restoredSnapshot = parseStoredRecord(request.result).snapshot
      } catch (error) {
        failure = error
        transaction.abort()
      }
    }
    request.onerror = () => {
      failure = request.error
    }
    transaction.onerror = () => {
      failure ??= transaction.error
    }
    transaction.onabort = () => {
      reject(normalizeStorageError(failure ?? transaction.error))
    }
    transaction.oncomplete = () => {
      resolve(restoredSnapshot)
    }
  })
}

function executeWrite(
  database: IDBDatabase,
  scheduleWrite: ScheduleWrite,
): Promise<void> {
  return new Promise((resolve, reject) => {
    let transaction: IDBTransaction
    let failure: unknown

    try {
      transaction = database.transaction(
        LEAGUE_SNAPSHOT_OBJECT_STORE_NAME,
        'readwrite',
      )
    } catch (error) {
      reject(normalizeStorageError(error))
      return
    }

    const rememberError: RememberWriteError = (error) => {
      failure ??= error
    }
    const abort: AbortWrite = (error) => {
      rememberError(error)
      try {
        transaction.abort()
      } catch (abortError) {
        reject(normalizeStorageError(failure ?? abortError))
      }
    }

    transaction.onerror = () => {
      rememberError(transaction.error)
    }
    transaction.onabort = () => {
      reject(normalizeStorageError(failure ?? transaction.error))
    }
    transaction.oncomplete = () => {
      resolve()
    }

    try {
      scheduleWrite(
        transaction.objectStore(LEAGUE_SNAPSHOT_OBJECT_STORE_NAME),
        abort,
        rememberError,
      )
    } catch (error) {
      abort(error)
    }
  })
}

function createStoredRecord(
  snapshot: unknown,
  leagueId: LeagueId,
): StoredLeagueSnapshotRecord {
  return { leagueId, snapshot }
}

function parseStoredRecord(value: unknown): StoredLeagueSnapshotRecord {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    throw invalidStoredRecord()
  }

  const source = value as Record<string, unknown>
  const ownKeys = Reflect.ownKeys(value)
  if (
    (Object.getPrototypeOf(value) !== Object.prototype &&
      Object.getPrototypeOf(value) !== null) ||
    ownKeys.length !== 2 ||
    !Object.prototype.hasOwnProperty.call(source, 'leagueId') ||
    !Object.prototype.hasOwnProperty.call(source, 'snapshot') ||
    !isLeagueId(source.leagueId) ||
    !hasMatchingSnapshotLeagueId(source.snapshot, source.leagueId)
  ) {
    throw invalidStoredRecord()
  }

  for (const key of ownKeys) {
    if (typeof key !== 'string') {
      throw invalidStoredRecord()
    }

    const descriptor = Object.getOwnPropertyDescriptor(value, key)
    if (
      descriptor === undefined ||
      !descriptor.enumerable ||
      !Object.prototype.hasOwnProperty.call(descriptor, 'value')
    ) {
      throw invalidStoredRecord()
    }
  }

  return {
    leagueId: source.leagueId,
    snapshot: source.snapshot,
  }
}

function hasMatchingSnapshotLeagueId(
  snapshot: unknown,
  leagueId: LeagueId,
): boolean {
  if (
    snapshot === null ||
    typeof snapshot !== 'object' ||
    Array.isArray(snapshot) ||
    !Object.prototype.hasOwnProperty.call(snapshot, 'league')
  ) {
    return false
  }

  const snapshotLeague = (snapshot as Record<string, unknown>).league
  return (
    snapshotLeague !== null &&
    typeof snapshotLeague === 'object' &&
    !Array.isArray(snapshotLeague) &&
    Object.prototype.hasOwnProperty.call(snapshotLeague, 'id') &&
    (snapshotLeague as Record<string, unknown>).id === leagueId
  )
}

function invalidStoredRecord(): InvalidLeagueSnapshotError {
  return new InvalidLeagueSnapshotError(
    '$',
    'The stored active league record is invalid',
  )
}

function normalizeStorageError(error: unknown): LeagueSnapshotStorageError {
  if (error instanceof LeagueSnapshotStorageError) {
    return error
  }
  if (hasErrorName(error, 'QuotaExceededError')) {
    return new LeagueSnapshotQuotaError(
      'Browser storage is full; the prior league snapshot was preserved',
      error,
    )
  }
  if (hasErrorName(error, 'ConstraintError')) {
    return new LeagueSnapshotConflictError(
      'The active league snapshot changed before the operation completed',
      error,
    )
  }
  return new LeagueSnapshotStorageError(
    'The active league snapshot could not be accessed',
    error,
  )
}

function hasErrorName(error: unknown, name: string): boolean {
  return (
    error !== null &&
    typeof error === 'object' &&
    'name' in error &&
    error.name === name
  )
}
