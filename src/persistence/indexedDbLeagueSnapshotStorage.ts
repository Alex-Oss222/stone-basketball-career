import {
  LeagueSnapshotConflictError,
  LeagueSnapshotQuotaError,
  LeagueSnapshotStorageError,
  createLeagueSnapshotRepository,
} from './leagueSnapshotRepository'
import type {
  LeagueSnapshotRepository,
  LeagueSnapshotStorage,
  LeagueSnapshotStoragePhase,
  LeagueSnapshotStorageSlot,
  LeagueSnapshotStorageTransactionPlan,
} from './leagueSnapshotRepository'

export {
  LeagueSnapshotConflictError,
  LeagueSnapshotQuotaError,
  LeagueSnapshotStorageError,
} from './leagueSnapshotRepository'

export const LEAGUE_SNAPSHOT_DATABASE_NAME = 'stone-basketball-gm'
export const LEAGUE_SNAPSHOT_DATABASE_VERSION = 1
export const LEAGUE_SNAPSHOT_OBJECT_STORE_NAME = 'activeLeague'

/** The one active-league location. Current-version snapshots live here. */
export const ACTIVE_LEAGUE_SNAPSHOT_KEY = 'current'
/**
 * The pre-collapse V2 location. Never written anymore, but still read so a
 * record left by an older build surfaces as a version mismatch instead of
 * silently looking like an empty save, and still cleared so it can never
 * resurface after the player starts over.
 */
export const ACTIVE_LEAGUE_SNAPSHOT_LEGACY_V2_KEY = 'current-v2'

type PrepareTransaction<Result> = (
  slot: LeagueSnapshotStorageSlot,
) => LeagueSnapshotStorageTransactionPlan<Result>

/** Native IndexedDB storage for the single active-league slot. */
export class IndexedDbLeagueSnapshotStorage implements LeagueSnapshotStorage {
  private readonly indexedDb: IDBFactory | undefined

  constructor(indexedDb: IDBFactory | undefined = globalThis.indexedDB) {
    this.indexedDb = indexedDb
  }

  async read(): Promise<LeagueSnapshotStorageSlot> {
    return this.withDatabase((database) => readActiveSlot(database))
  }

  async transact<Result>(
    prepare: PrepareTransaction<Result>,
  ): Promise<Result> {
    return this.withDatabase((database) =>
      executeSlotTransaction(database, prepare),
    )
  }

  private async withDatabase<Result>(
    operation: (database: IDBDatabase) => Promise<Result>,
  ): Promise<Result> {
    if (this.indexedDb === undefined) {
      throw new LeagueSnapshotStorageError(
        'IndexedDB is unavailable in this browser',
        undefined,
        'open',
      )
    }

    const database = await openDatabase(this.indexedDb)
    try {
      return await operation(database)
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
      reject(normalizeStorageError(error, 'open'))
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
        reject(normalizeStorageError(error, 'open'))
      }
    }
    request.onerror = () => {
      reject(normalizeStorageError(request.error, 'open'))
    }
    request.onblocked = () => {
      rejectedAsBlocked = true
      reject(
        new LeagueSnapshotStorageError(
          'IndexedDB is blocked by another open application tab',
          undefined,
          'open',
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
            undefined,
            'open',
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

function readActiveSlot(
  database: IDBDatabase,
): Promise<LeagueSnapshotStorageSlot> {
  return new Promise((resolve, reject) => {
    let transaction: IDBTransaction
    let store: IDBObjectStore
    let active = absentStorageSlot()
    let legacy = absentStorageSlot()
    let failure: unknown

    try {
      transaction = database.transaction(
        LEAGUE_SNAPSHOT_OBJECT_STORE_NAME,
        'readonly',
      )
      store = transaction.objectStore(LEAGUE_SNAPSHOT_OBJECT_STORE_NAME)
    } catch (error) {
      reject(normalizeStorageError(error, 'read'))
      return
    }

    transaction.onerror = () => {
      failure ??= transaction.error
    }
    transaction.onabort = () => {
      reject(normalizeStorageError(failure ?? transaction.error, 'read'))
    }
    transaction.oncomplete = () => {
      resolve(mergeSlots(active, legacy))
    }

    const rememberReadFailure = (error: unknown): void => {
      failure ??= error
    }
    try {
      requestStorageSlot(
        store,
        ACTIVE_LEAGUE_SNAPSHOT_KEY,
        (slot) => {
          active = slot
        },
        rememberReadFailure,
      )
      requestStorageSlot(
        store,
        ACTIVE_LEAGUE_SNAPSHOT_LEGACY_V2_KEY,
        (slot) => {
          legacy = slot
        },
        rememberReadFailure,
      )
    } catch (error) {
      failure = error
      try {
        transaction.abort()
      } catch (abortError) {
        reject(normalizeStorageError(error ?? abortError, 'read'))
      }
    }
  })
}

function executeSlotTransaction<Result>(
  database: IDBDatabase,
  prepare: PrepareTransaction<Result>,
): Promise<Result> {
  return new Promise((resolve, reject) => {
    let transaction: IDBTransaction
    let store: IDBObjectStore
    let phase: LeagueSnapshotStoragePhase = 'read'
    let failure: unknown
    let preserveFailure = false
    let settled = false
    let verified = false
    let verifiedResult: Result
    let initialActive = absentStorageSlot()
    let initialLegacy = absentStorageSlot()
    let initialReadsRemaining = 2
    let plan: LeagueSnapshotStorageTransactionPlan<Result> | null = null

    const rememberFailure = (
      error: unknown,
      nextPhase: LeagueSnapshotStoragePhase,
      preserve = false,
    ): void => {
      if (failure !== undefined) return
      failure = error
      phase = nextPhase
      preserveFailure = preserve
    }

    const abort = (
      error: unknown,
      nextPhase: LeagueSnapshotStoragePhase,
      preserve = false,
    ): void => {
      rememberFailure(error, nextPhase, preserve)
      try {
        transaction.abort()
      } catch (abortError) {
        if (settled) return
        settled = true
        reject(
          preserveFailure
            ? failure
            : normalizeStorageError(failure ?? abortError, phase),
        )
      }
    }

    const handleRequestError = <Value>(
      request: IDBRequest<Value>,
      nextPhase: LeagueSnapshotStoragePhase,
    ): void => {
      rememberFailure(request.error, nextPhase)
    }

    const verifyReread = (
      active: LeagueSnapshotStorageSlot,
      legacy: LeagueSnapshotStorageSlot,
    ): void => {
      if (plan === null) {
        abort(
          new LeagueSnapshotStorageError(
            'The active league transaction lost its verification plan',
            undefined,
            'reread',
          ),
          'reread',
        )
        return
      }

      try {
        verifiedResult = plan.verify(mergeSlots(active, legacy))
        verified = true
        phase = 'commit'
      } catch (error) {
        abort(withStoragePhase(error, 'reread'), 'reread', true)
      }
    }

    const scheduleReread = (): void => {
      phase = 'reread'
      let active = absentStorageSlot()
      let legacy = absentStorageSlot()
      let readsRemaining = 2

      const completeRead = (): void => {
        readsRemaining -= 1
        if (readsRemaining === 0) {
          verifyReread(active, legacy)
        }
      }

      try {
        requestStorageSlot(
          store,
          ACTIVE_LEAGUE_SNAPSHOT_KEY,
          (slot) => {
            active = slot
            completeRead()
          },
          (error) => {
            rememberFailure(error, 'reread')
          },
        )
        requestStorageSlot(
          store,
          ACTIVE_LEAGUE_SNAPSHOT_LEGACY_V2_KEY,
          (slot) => {
            legacy = slot
            completeRead()
          },
          (error) => {
            rememberFailure(error, 'reread')
          },
        )
      } catch (error) {
        abort(error, 'reread')
      }
    }

    const applyClear = (): void => {
      phase = 'clear'
      let deletesRemaining = 2
      const completeDelete = (): void => {
        deletesRemaining -= 1
        if (deletesRemaining === 0) scheduleReread()
      }

      let activeDelete: IDBRequest<undefined>
      let legacyDelete: IDBRequest<undefined>
      try {
        activeDelete = store.delete(ACTIVE_LEAGUE_SNAPSHOT_KEY)
        legacyDelete = store.delete(ACTIVE_LEAGUE_SNAPSHOT_LEGACY_V2_KEY)
      } catch (error) {
        abort(error, 'clear')
        return
      }

      activeDelete.onsuccess = completeDelete
      legacyDelete.onsuccess = completeDelete
      activeDelete.onerror = () => {
        handleRequestError(activeDelete, 'clear')
      }
      legacyDelete.onerror = () => {
        handleRequestError(legacyDelete, 'clear')
      }
    }

    const applyWrite = (
      mutation: Extract<
        LeagueSnapshotStorageTransactionPlan<Result>['mutation'],
        { kind: 'write' }
      >,
    ): void => {
      phase = 'write'
      let request: IDBRequest<IDBValidKey>
      try {
        request =
          mutation.mode === 'add'
            ? store.add(mutation.record, ACTIVE_LEAGUE_SNAPSHOT_KEY)
            : store.put(mutation.record, ACTIVE_LEAGUE_SNAPSHOT_KEY)
      } catch (error) {
        abort(error, 'write')
        return
      }

      request.onsuccess = scheduleReread
      request.onerror = () => {
        handleRequestError(request, 'write')
      }
    }

    const prepareMutation = (): void => {
      try {
        plan = prepare(mergeSlots(initialActive, initialLegacy))
      } catch (error) {
        abort(error, 'read', true)
        return
      }

      if (plan.mutation.kind === 'write') {
        applyWrite(plan.mutation)
      } else {
        applyClear()
      }
    }

    const completeInitialRead = (): void => {
      initialReadsRemaining -= 1
      if (initialReadsRemaining === 0) prepareMutation()
    }

    try {
      transaction = database.transaction(
        LEAGUE_SNAPSHOT_OBJECT_STORE_NAME,
        'readwrite',
      )
      store = transaction.objectStore(LEAGUE_SNAPSHOT_OBJECT_STORE_NAME)
    } catch (error) {
      reject(normalizeStorageError(error, 'read'))
      return
    }

    transaction.onerror = () => {
      rememberFailure(transaction.error, phase)
    }
    transaction.onabort = () => {
      if (settled) return
      settled = true
      reject(
        preserveFailure
          ? failure
          : normalizeStorageError(failure ?? transaction.error, phase),
      )
    }
    transaction.oncomplete = () => {
      if (settled) return
      settled = true
      if (!verified) {
        reject(
          new LeagueSnapshotStorageError(
            'The active league transaction committed before verification completed',
            undefined,
            'commit',
          ),
        )
        return
      }
      resolve(verifiedResult)
    }

    try {
      requestStorageSlot(
        store,
        ACTIVE_LEAGUE_SNAPSHOT_KEY,
        (slot) => {
          initialActive = slot
          completeInitialRead()
        },
        (error) => {
          rememberFailure(error, 'read')
        },
      )
      requestStorageSlot(
        store,
        ACTIVE_LEAGUE_SNAPSHOT_LEGACY_V2_KEY,
        (slot) => {
          initialLegacy = slot
          completeInitialRead()
        },
        (error) => {
          rememberFailure(error, 'read')
        },
      )
    } catch (error) {
      abort(error, 'read')
    }
  })
}

/** The active key always wins; the legacy key only surfaces when it is alone. */
function mergeSlots(
  active: LeagueSnapshotStorageSlot,
  legacy: LeagueSnapshotStorageSlot,
): LeagueSnapshotStorageSlot {
  return active.present ? active : legacy
}

function absentStorageSlot(): LeagueSnapshotStorageSlot {
  return { present: false, value: undefined }
}

function requestStorageSlot(
  store: IDBObjectStore,
  key: IDBValidKey,
  onSuccess: (slot: LeagueSnapshotStorageSlot) => void,
  onError: (error: unknown) => void,
): void {
  const valueRequest = store.get(key)
  const keyRequest = store.getKey(key)
  let value: unknown
  let storedKey: IDBValidKey | undefined
  let valueReady = false
  let keyReady = false

  const complete = (): void => {
    if (!valueReady || !keyReady) return
    onSuccess({ present: storedKey !== undefined, value })
  }

  valueRequest.onsuccess = () => {
    value = valueRequest.result
    valueReady = true
    complete()
  }
  keyRequest.onsuccess = () => {
    storedKey = keyRequest.result
    keyReady = true
    complete()
  }
  valueRequest.onerror = () => {
    onError(valueRequest.error)
  }
  keyRequest.onerror = () => {
    onError(keyRequest.error)
  }
}

function withStoragePhase(
  error: unknown,
  phase: LeagueSnapshotStoragePhase,
): unknown {
  if (
    !(error instanceof LeagueSnapshotStorageError) ||
    error.phase !== null
  ) {
    return error
  }
  if (Object.getPrototypeOf(error) === LeagueSnapshotQuotaError.prototype) {
    return new LeagueSnapshotQuotaError(error.message, error, phase)
  }
  if (Object.getPrototypeOf(error) === LeagueSnapshotConflictError.prototype) {
    return new LeagueSnapshotConflictError(error.message, error, phase)
  }
  if (Object.getPrototypeOf(error) === LeagueSnapshotStorageError.prototype) {
    return new LeagueSnapshotStorageError(error.message, error, phase)
  }
  return error
}

function normalizeStorageError(
  error: unknown,
  phase: LeagueSnapshotStoragePhase,
): LeagueSnapshotStorageError {
  if (error instanceof LeagueSnapshotStorageError) {
    return error
  }
  if (hasErrorName(error, 'QuotaExceededError')) {
    return new LeagueSnapshotQuotaError(
      'Browser storage is full; the prior league snapshot was preserved',
      error,
      phase,
    )
  }
  if (hasErrorName(error, 'ConstraintError')) {
    return new LeagueSnapshotConflictError(
      'The active league snapshot changed before the operation completed',
      error,
      phase,
    )
  }
  return new LeagueSnapshotStorageError(
    'The active league snapshot could not be accessed',
    error,
    phase,
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
