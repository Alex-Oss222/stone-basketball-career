import { describe, expect, it } from 'vitest'
import {
  ACTIVE_LEAGUE_SNAPSHOT_KEY,
  ACTIVE_LEAGUE_SNAPSHOT_V1_KEY,
  ACTIVE_LEAGUE_SNAPSHOT_V2_KEY,
  IndexedDbLeagueSnapshotStorage,
  LEAGUE_SNAPSHOT_DATABASE_NAME,
  LEAGUE_SNAPSHOT_DATABASE_VERSION,
  LEAGUE_SNAPSHOT_OBJECT_STORE_NAME,
} from '../../src/persistence/indexedDbLeagueSnapshotStorage'

describe('IndexedDbLeagueSnapshotStorage versioned locations', () => {
  it('keeps V1 at the shipped key and V2 at a distinct key in the existing store', () => {
    expect(LEAGUE_SNAPSHOT_DATABASE_NAME).toBe('stone-basketball-gm')
    expect(LEAGUE_SNAPSHOT_DATABASE_VERSION).toBe(1)
    expect(LEAGUE_SNAPSHOT_OBJECT_STORE_NAME).toBe('activeLeague')
    expect(ACTIVE_LEAGUE_SNAPSHOT_V1_KEY).toBe('current')
    expect(ACTIVE_LEAGUE_SNAPSHOT_KEY).toBe(ACTIVE_LEAGUE_SNAPSHOT_V1_KEY)
    expect(ACTIVE_LEAGUE_SNAPSHOT_V2_KEY).toBe('current-v2')
    expect(ACTIVE_LEAGUE_SNAPSHOT_V2_KEY).not.toBe(
      ACTIVE_LEAGUE_SNAPSHOT_V1_KEY,
    )
  })

  it('dual-reads presence separately from null and undefined values', async () => {
    const factory = new MemoryIdbFactory()
    factory.seed(ACTIVE_LEAGUE_SNAPSHOT_V1_KEY, null)
    factory.seed(ACTIVE_LEAGUE_SNAPSHOT_V2_KEY, undefined)
    const storage = createStorage(factory)

    await expect(storage.read()).resolves.toEqual({
      v1: { present: true, value: null },
      v2: { present: true, value: undefined },
    })
  })

  it('adds and replaces only the complete V2 location', async () => {
    const factory = new MemoryIdbFactory()
    const storage = createStorage(factory)

    const added = await storage.transact((state) => {
      expect(state.v1.present).toBe(false)
      expect(state.v2.present).toBe(false)
      return {
        mutation: {
          kind: 'write-v2',
          mode: 'add',
          record: { revision: 1 },
        },
        verify: (reread) => reread,
      }
    })

    expect(added).toEqual({
      v1: { present: false, value: undefined },
      v2: { present: true, value: { revision: 1 } },
    })
    expect(factory.has(ACTIVE_LEAGUE_SNAPSHOT_V1_KEY)).toBe(false)
    expect(factory.inspect(ACTIVE_LEAGUE_SNAPSHOT_V2_KEY)).toEqual({
      revision: 1,
    })

    await storage.transact((state) => ({
      mutation: {
        kind: 'write-v2',
        mode: 'put',
        record: { revision: 2 },
      },
      verify: (reread) => {
        expect(state.v2.value).toEqual({ revision: 1 })
        expect(reread.v2.value).toEqual({ revision: 2 })
      },
    }))

    expect(factory.has(ACTIVE_LEAGUE_SNAPSHOT_V1_KEY)).toBe(false)
    expect(factory.inspect(ACTIVE_LEAGUE_SNAPSHOT_V2_KEY)).toEqual({
      revision: 2,
    })
  })

  it('clears V1 and V2 together and verifies before commit', async () => {
    const events: string[] = []
    const factory = new MemoryIdbFactory(events)
    factory.seed(ACTIVE_LEAGUE_SNAPSHOT_V1_KEY, { version: 1 })
    factory.seed(ACTIVE_LEAGUE_SNAPSHOT_V2_KEY, { version: 2 })
    const storage = createStorage(factory)

    await storage.transact((state) => {
      expect(state.v1.present).toBe(true)
      expect(state.v2.present).toBe(true)
      return {
        mutation: { kind: 'clear-both' },
        verify: (reread) => {
          events.push('verify')
          expect(reread.v1.present).toBe(false)
          expect(reread.v2.present).toBe(false)
        },
      }
    })

    expect(events).toEqual(['verify', 'commit'])
    expect(factory.has(ACTIVE_LEAGUE_SNAPSHOT_V1_KEY)).toBe(false)
    expect(factory.has(ACTIVE_LEAGUE_SNAPSHOT_V2_KEY)).toBe(false)
  })

  it('aborts and rolls back a staged V2 write when verification fails', async () => {
    const events: string[] = []
    const factory = new MemoryIdbFactory(events)
    factory.seed(ACTIVE_LEAGUE_SNAPSHOT_V2_KEY, { revision: 1 })
    const storage = createStorage(factory)
    const verificationFailure = new Error('deliberate verification failure')

    await expect(
      storage.transact(() => ({
        mutation: {
          kind: 'write-v2',
          mode: 'put',
          record: { revision: 2 },
        },
        verify: (reread) => {
          events.push('verify')
          expect(reread.v2.value).toEqual({ revision: 2 })
          throw verificationFailure
        },
      })),
    ).rejects.toBe(verificationFailure)

    expect(events).toEqual(['verify', 'abort'])
    expect(factory.inspect(ACTIVE_LEAGUE_SNAPSHOT_V2_KEY)).toEqual({
      revision: 1,
    })
  })
})

function createStorage(
  factory: MemoryIdbFactory,
): IndexedDbLeagueSnapshotStorage {
  return new IndexedDbLeagueSnapshotStorage(factory.asIdbFactory())
}

class MemoryIdbFactory {
  readonly events: string[]

  private records = new Map<IDBValidKey, unknown>()
  private storeCreated = false

  constructor(events: string[] = []) {
    this.events = events
  }

  asIdbFactory(): IDBFactory {
    return this as unknown as IDBFactory
  }

  open(_name: string, _version?: number): IDBOpenDBRequest {
    const request = new MemoryOpenRequest()
    queueMicrotask(() => {
      const database = new MemoryDatabase(this)
      request.result = database.asIdbDatabase()
      if (!this.storeCreated) {
        let aborted = false
        request.transaction = {
          abort: () => {
            aborted = true
          },
        } as IDBTransaction
        request.onupgradeneeded?.call(
          request.asOpenRequest(),
          new Event('upgradeneeded') as IDBVersionChangeEvent,
        )
        if (aborted) {
          request.error = namedError('AbortError')
          request.onerror?.call(request.asOpenRequest(), new Event('error'))
          return
        }
      }
      request.onsuccess?.call(request.asOpenRequest(), new Event('success'))
    })
    return request.asOpenRequest()
  }

  seed(key: IDBValidKey, value: unknown): void {
    this.storeCreated = true
    this.records.set(key, clone(value))
  }

  has(key: IDBValidKey): boolean {
    return this.records.has(key)
  }

  inspect(key: IDBValidKey): unknown {
    return clone(this.records.get(key))
  }

  containsStore(name: string): boolean {
    return this.storeCreated && name === LEAGUE_SNAPSHOT_OBJECT_STORE_NAME
  }

  createStore(name: string): void {
    if (name !== LEAGUE_SNAPSHOT_OBJECT_STORE_NAME) {
      throw new Error(`Unexpected object store ${name}`)
    }
    this.storeCreated = true
  }

  createTransaction(mode: IDBTransactionMode): MemoryTransaction {
    if (!this.storeCreated) {
      throw namedError('NotFoundError')
    }
    return new MemoryTransaction(this, mode, this.records)
  }

  commit(records: Map<IDBValidKey, unknown>): void {
    this.records = cloneMap(records)
    this.events.push('commit')
  }
}

class MemoryOpenRequest {
  result!: IDBDatabase
  error: DOMException | null = null
  transaction: IDBTransaction | null = null
  onupgradeneeded: IDBOpenDBRequest['onupgradeneeded'] = null
  onerror: IDBOpenDBRequest['onerror'] = null
  onblocked: IDBOpenDBRequest['onblocked'] = null
  onsuccess: IDBOpenDBRequest['onsuccess'] = null

  asOpenRequest(): IDBOpenDBRequest {
    return this as unknown as IDBOpenDBRequest
  }
}

class MemoryDatabase {
  onversionchange: IDBDatabase['onversionchange'] = null
  private readonly factory: MemoryIdbFactory

  constructor(factory: MemoryIdbFactory) {
    this.factory = factory
  }

  readonly objectStoreNames = {
    contains: (name: string) => this.factory.containsStore(name),
  } as DOMStringList

  asIdbDatabase(): IDBDatabase {
    return this as unknown as IDBDatabase
  }

  createObjectStore(name: string): IDBObjectStore {
    this.factory.createStore(name)
    return {} as IDBObjectStore
  }

  transaction(
    _storeName: string,
    mode: IDBTransactionMode = 'readonly',
  ): IDBTransaction {
    return this.factory.createTransaction(mode).asIdbTransaction()
  }

  close(): void {}
}

class MemoryTransaction {
  error: DOMException | null = null
  onerror: IDBTransaction['onerror'] = null
  onabort: IDBTransaction['onabort'] = null
  oncomplete: IDBTransaction['oncomplete'] = null

  private readonly draft: Map<IDBValidKey, unknown>
  private pendingRequests = 0
  private completionQueued = false
  private active = true
  private aborted = false
  private readonly factory: MemoryIdbFactory
  private readonly mode: IDBTransactionMode

  constructor(
    factory: MemoryIdbFactory,
    mode: IDBTransactionMode,
    records: Map<IDBValidKey, unknown>,
  ) {
    this.factory = factory
    this.mode = mode
    this.draft = cloneMap(records)
  }

  asIdbTransaction(): IDBTransaction {
    return this as unknown as IDBTransaction
  }

  objectStore(_name: string): IDBObjectStore {
    return new MemoryObjectStore(this).asIdbObjectStore()
  }

  request<Result>(operation: () => Result): IDBRequest<Result> {
    if (!this.active) throw namedError('TransactionInactiveError')
    const request = new MemoryRequest<Result>()
    this.pendingRequests += 1

    queueMicrotask(() => {
      if (this.aborted) return
      try {
        request.result = operation()
        request.onsuccess?.call(request.asIdbRequest(), new Event('success'))
      } catch (error) {
        const requestError = asDomException(error)
        request.error = requestError
        request.onerror?.call(request.asIdbRequest(), new Event('error'))
        this.fail(requestError)
      } finally {
        this.pendingRequests -= 1
        this.queueCompletionIfReady()
      }
    })
    return request.asIdbRequest()
  }

  get records(): Map<IDBValidKey, unknown> {
    return this.draft
  }

  abort(): void {
    if (!this.active) throw namedError('InvalidStateError')
    this.aborted = true
    this.active = false
    queueMicrotask(() => {
      this.factory.events.push('abort')
      this.onabort?.call(this.asIdbTransaction(), new Event('abort'))
    })
  }

  private fail(error: DOMException): void {
    if (!this.active) return
    this.error = error
    this.onerror?.call(this.asIdbTransaction(), new Event('error'))
    this.abort()
  }

  private queueCompletionIfReady(): void {
    if (
      this.pendingRequests !== 0 ||
      this.completionQueued ||
      !this.active
    ) {
      return
    }
    this.completionQueued = true
    queueMicrotask(() => {
      this.completionQueued = false
      if (this.pendingRequests !== 0 || !this.active) return
      this.active = false
      if (this.mode === 'readwrite') this.factory.commit(this.draft)
      this.oncomplete?.call(this.asIdbTransaction(), new Event('complete'))
    })
  }
}

class MemoryObjectStore {
  private readonly transaction: MemoryTransaction

  constructor(transaction: MemoryTransaction) {
    this.transaction = transaction
  }

  asIdbObjectStore(): IDBObjectStore {
    return this as unknown as IDBObjectStore
  }

  get(key: IDBValidKey): IDBRequest<unknown> {
    return this.transaction.request(() =>
      this.transaction.records.has(key)
        ? clone(this.transaction.records.get(key))
        : undefined,
    )
  }

  getKey(key: IDBValidKey): IDBRequest<IDBValidKey | undefined> {
    return this.transaction.request(() =>
      this.transaction.records.has(key) ? key : undefined,
    )
  }

  add(value: unknown, key: IDBValidKey): IDBRequest<IDBValidKey> {
    return this.transaction.request(() => {
      if (this.transaction.records.has(key)) throw namedError('ConstraintError')
      this.transaction.records.set(key, clone(value))
      return key
    })
  }

  put(value: unknown, key: IDBValidKey): IDBRequest<IDBValidKey> {
    return this.transaction.request(() => {
      this.transaction.records.set(key, clone(value))
      return key
    })
  }

  delete(key: IDBValidKey): IDBRequest<undefined> {
    return this.transaction.request(() => {
      this.transaction.records.delete(key)
      return undefined
    })
  }
}

class MemoryRequest<Result> {
  result!: Result
  error: DOMException | null = null
  onsuccess: IDBRequest<Result>['onsuccess'] = null
  onerror: IDBRequest<Result>['onerror'] = null

  asIdbRequest(): IDBRequest<Result> {
    return this as unknown as IDBRequest<Result>
  }
}

function clone<Value>(value: Value): Value {
  return structuredClone(value)
}

function cloneMap(
  source: Map<IDBValidKey, unknown>,
): Map<IDBValidKey, unknown> {
  return new Map(
    [...source].map(([key, value]) => [clone(key), clone(value)]),
  )
}

function namedError(name: string): DOMException {
  return new DOMException(name, name)
}

function asDomException(error: unknown): DOMException {
  return error instanceof DOMException
    ? error
    : new DOMException(
        error instanceof Error ? error.message : 'IndexedDB request failed',
        'UnknownError',
      )
}
