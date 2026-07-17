import { describe, expect, it } from 'vitest'
import {
  ACTIVE_LEAGUE_SNAPSHOT_KEY,
  ACTIVE_LEAGUE_SNAPSHOT_LEGACY_V2_KEY,
  IndexedDbLeagueSnapshotStorage,
  LEAGUE_SNAPSHOT_DATABASE_NAME,
  LEAGUE_SNAPSHOT_DATABASE_VERSION,
  LEAGUE_SNAPSHOT_OBJECT_STORE_NAME,
  createIndexedDbLeagueSnapshotRepository,
} from '../../src/persistence/indexedDbLeagueSnapshotStorage'
import { LEAGUE_SNAPSHOT_VERSION } from '../../src/persistence/leagueSnapshot'
import { createLegacyVersionSnapshotFixture } from './leagueSnapshot.fixture'

describe('IndexedDbLeagueSnapshotStorage single active-league slot', () => {
  it('keeps the active key and reads the legacy V2 key in the existing store', () => {
    expect(LEAGUE_SNAPSHOT_DATABASE_NAME).toBe('stone-basketball-gm')
    expect(LEAGUE_SNAPSHOT_DATABASE_VERSION).toBe(1)
    expect(LEAGUE_SNAPSHOT_OBJECT_STORE_NAME).toBe('activeLeague')
    expect(ACTIVE_LEAGUE_SNAPSHOT_KEY).toBe('current')
    expect(ACTIVE_LEAGUE_SNAPSHOT_LEGACY_V2_KEY).toBe('current-v2')
    expect(ACTIVE_LEAGUE_SNAPSHOT_LEGACY_V2_KEY).not.toBe(
      ACTIVE_LEAGUE_SNAPSHOT_KEY,
    )
  })

  it('reads the active key as one present slot, distinguishing null from absence', async () => {
    const present = new MemoryIdbFactory()
    present.seed(ACTIVE_LEAGUE_SNAPSHOT_KEY, null)
    await expect(createStorage(present).read()).resolves.toEqual({
      present: true,
      value: null,
    })

    const absent = new MemoryIdbFactory()
    absent.createStore(LEAGUE_SNAPSHOT_OBJECT_STORE_NAME)
    await expect(createStorage(absent).read()).resolves.toEqual({
      present: false,
      value: undefined,
    })
  })

  it('falls back to the legacy V2 key only when the active key is empty', async () => {
    const legacyOnly = new MemoryIdbFactory()
    legacyOnly.seed(ACTIVE_LEAGUE_SNAPSHOT_LEGACY_V2_KEY, { version: 2 })
    await expect(createStorage(legacyOnly).read()).resolves.toEqual({
      present: true,
      value: { version: 2 },
    })

    const both = new MemoryIdbFactory()
    both.seed(ACTIVE_LEAGUE_SNAPSHOT_KEY, { version: 'current' })
    both.seed(ACTIVE_LEAGUE_SNAPSHOT_LEGACY_V2_KEY, { version: 2 })
    await expect(createStorage(both).read()).resolves.toEqual({
      present: true,
      value: { version: 'current' },
    })
  })

  it('adds and replaces only the active key', async () => {
    const factory = new MemoryIdbFactory()
    const storage = createStorage(factory)

    const added = await storage.transact((slot) => {
      expect(slot.present).toBe(false)
      return {
        mutation: { kind: 'write', mode: 'add', record: { revision: 1 } },
        verify: (reread) => reread,
      }
    })

    expect(added).toEqual({ present: true, value: { revision: 1 } })
    expect(factory.has(ACTIVE_LEAGUE_SNAPSHOT_LEGACY_V2_KEY)).toBe(false)
    expect(factory.inspect(ACTIVE_LEAGUE_SNAPSHOT_KEY)).toEqual({ revision: 1 })

    await storage.transact((slot) => ({
      mutation: { kind: 'write', mode: 'put', record: { revision: 2 } },
      verify: (reread) => {
        expect(slot.value).toEqual({ revision: 1 })
        expect(reread.value).toEqual({ revision: 2 })
      },
    }))

    expect(factory.inspect(ACTIVE_LEAGUE_SNAPSHOT_KEY)).toEqual({ revision: 2 })
  })

  it('clears the active and legacy keys together and verifies before commit', async () => {
    const events: string[] = []
    const factory = new MemoryIdbFactory(events)
    factory.seed(ACTIVE_LEAGUE_SNAPSHOT_KEY, { version: 'current' })
    factory.seed(ACTIVE_LEAGUE_SNAPSHOT_LEGACY_V2_KEY, { version: 2 })
    const storage = createStorage(factory)

    await storage.transact((slot) => {
      expect(slot.present).toBe(true)
      return {
        mutation: { kind: 'clear' },
        verify: (reread) => {
          events.push('verify')
          expect(reread.present).toBe(false)
        },
      }
    })

    expect(events).toEqual(['verify', 'commit'])
    expect(factory.has(ACTIVE_LEAGUE_SNAPSHOT_KEY)).toBe(false)
    expect(factory.has(ACTIVE_LEAGUE_SNAPSHOT_LEGACY_V2_KEY)).toBe(false)
  })

  it('aborts and rolls back a staged write when verification fails', async () => {
    const events: string[] = []
    const factory = new MemoryIdbFactory(events)
    factory.seed(ACTIVE_LEAGUE_SNAPSHOT_KEY, { revision: 1 })
    const storage = createStorage(factory)
    const verificationFailure = new Error('deliberate verification failure')

    await expect(
      storage.transact(() => ({
        mutation: { kind: 'write', mode: 'put', record: { revision: 2 } },
        verify: (reread) => {
          events.push('verify')
          expect(reread.value).toEqual({ revision: 2 })
          throw verificationFailure
        },
      })),
    ).rejects.toBe(verificationFailure)

    expect(events).toEqual(['verify', 'abort'])
    expect(factory.inspect(ACTIVE_LEAGUE_SNAPSHOT_KEY)).toEqual({ revision: 1 })
  })

  it('surfaces a legacy V2 record left under current-v2 as a version mismatch', async () => {
    const legacyDto = createLegacyVersionSnapshotFixture(2) as {
      readonly league: { readonly id: unknown }
    }
    const factory = new MemoryIdbFactory()
    factory.seed(ACTIVE_LEAGUE_SNAPSHOT_LEGACY_V2_KEY, {
      leagueId: legacyDto.league.id,
      snapshot: legacyDto,
    })
    const repository = createIndexedDbLeagueSnapshotRepository(
      factory.asIdbFactory(),
    )

    await expect(repository.restore()).resolves.toEqual({
      kind: 'version-mismatch',
      storedVersion: 2,
      supportedVersion: LEAGUE_SNAPSHOT_VERSION,
    })
    expect(factory.has(ACTIVE_LEAGUE_SNAPSHOT_LEGACY_V2_KEY)).toBe(true)
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
