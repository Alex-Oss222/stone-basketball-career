import { parseLeagueId, parseTeamId } from '../domain/ids'
import type { LeagueId, TeamId } from '../domain/ids'
import {
  InvalidLeagueSnapshotError,
  LEAGUE_SNAPSHOT_VERSION,
  parseLeagueSnapshot,
} from './leagueSnapshot'
import type { LeagueSnapshot } from './leagueSnapshot'

export interface LeagueSnapshotStorageSlot {
  readonly present: boolean
  readonly value: unknown
}

export type LeagueSnapshotStorageMutation =
  | {
      readonly kind: 'write'
      readonly mode: 'add' | 'put'
      readonly record: unknown
    }
  | {
      readonly kind: 'clear'
    }

export interface LeagueSnapshotStorageTransactionPlan<Result> {
  readonly mutation: LeagueSnapshotStorageMutation
  /** Runs against the slot re-read after the staged mutation, before commit. */
  readonly verify: (slot: LeagueSnapshotStorageSlot) => Result
}

/**
 * Browser-independent transaction boundary over the one active-league slot.
 * A storage implementation must publish no mutation unless prepare, mutation,
 * re-read, verify, and commit all succeed.
 */
export interface LeagueSnapshotStorage {
  read(): Promise<LeagueSnapshotStorageSlot>
  transact<Result>(
    prepare: (
      slot: LeagueSnapshotStorageSlot,
    ) => LeagueSnapshotStorageTransactionPlan<Result>,
  ): Promise<Result>
}

export const LEAGUE_SNAPSHOT_STORAGE_PHASES = [
  'open',
  'read',
  'write',
  'clear',
  'reread',
  'commit',
] as const

export type LeagueSnapshotStoragePhase =
  (typeof LEAGUE_SNAPSHOT_STORAGE_PHASES)[number]

export class LeagueSnapshotStorageError extends Error {
  readonly phase: LeagueSnapshotStoragePhase | null

  constructor(
    message: string,
    cause?: unknown,
    phase: LeagueSnapshotStoragePhase | null = null,
  ) {
    super(message, cause === undefined ? undefined : { cause })
    this.name = 'LeagueSnapshotStorageError'
    this.phase = phase
  }
}

export class LeagueSnapshotConflictError extends LeagueSnapshotStorageError {
  constructor(
    message: string,
    cause?: unknown,
    phase: LeagueSnapshotStoragePhase | null = null,
  ) {
    super(message, cause, phase)
    this.name = 'LeagueSnapshotConflictError'
  }
}

export class LeagueSnapshotQuotaError extends LeagueSnapshotStorageError {
  constructor(
    message: string,
    cause?: unknown,
    phase: LeagueSnapshotStoragePhase | null = null,
  ) {
    super(message, cause, phase)
    this.name = 'LeagueSnapshotQuotaError'
  }
}

export type LeagueSnapshotStaleOperation = 'update' | 'clear'

export class LeagueSnapshotStaleWriteError extends LeagueSnapshotConflictError {
  readonly operation: LeagueSnapshotStaleOperation
  readonly expectedRevision: number | null
  readonly currentRevision: number | null

  constructor(
    operation: LeagueSnapshotStaleOperation,
    expectedRevision: number | null,
    currentRevision: number | null,
    message: string,
  ) {
    super(message)
    this.name = 'LeagueSnapshotStaleWriteError'
    this.operation = operation
    this.expectedRevision = expectedRevision
    this.currentRevision = currentRevision
  }
}

export class LeagueSnapshotRevisionError extends LeagueSnapshotConflictError {
  constructor(message: string, cause?: unknown) {
    super(message, cause)
    this.name = 'LeagueSnapshotRevisionError'
  }
}

export const LEAGUE_SNAPSHOT_RECOVERY_REASONS = [
  'storage-failure',
  'parsing-failure',
  'validation-failure',
  'unsupported-rule-set-version',
] as const

export type LeagueSnapshotRecoveryReason =
  (typeof LEAGUE_SNAPSHOT_RECOVERY_REASONS)[number]

export interface LeagueSnapshotRepositoryIssue {
  readonly code: string
  readonly path: string
  readonly message: string
}

export type LeagueSnapshotRestorationResult =
  | {
      readonly kind: 'empty'
    }
  | {
      readonly kind: 'restored'
      readonly snapshot: LeagueSnapshot
    }
  | {
      /**
       * The stored record declares a numeric snapshot version other than the
       * one this build supports. There are no migrations before 1.0: the
       * record is refused untouched and the player starts a new league.
       */
      readonly kind: 'version-mismatch'
      readonly storedVersion: number
      readonly supportedVersion: typeof LEAGUE_SNAPSHOT_VERSION
    }
  | {
      readonly kind: 'recovery-required'
      readonly source: 'storage' | 'snapshot'
      readonly reason: LeagueSnapshotRecoveryReason
      readonly code: string
      readonly message: string
      readonly issues: readonly LeagueSnapshotRepositoryIssue[]
    }

export interface UpdateManagedTeamInput {
  readonly expectedLeagueId: LeagueId
  readonly expectedRevision: number
  readonly managedTeamId: TeamId | null
}

export type ClearActiveLeagueExpectation =
  | {
      readonly kind: 'snapshot'
      readonly expectedLeagueId: LeagueId
      readonly expectedRevision: number
    }
  | {
      /**
       * Clears a refused older-version record without ever parsing it. The
       * expected stored version guards against deleting a record that another
       * tab replaced with a valid current-version snapshot in the meantime.
       */
      readonly kind: 'version-mismatch'
      readonly expectedStoredVersion: number
    }

/** Application-facing access to the one atomic active-league snapshot. */
export interface LeagueSnapshotRepository {
  restore(): Promise<LeagueSnapshotRestorationResult>
  create(snapshot: LeagueSnapshot): Promise<LeagueSnapshot>
  updateManagedTeam(
    input: UpdateManagedTeamInput,
  ): Promise<LeagueSnapshot>
  clear(expectation: ClearActiveLeagueExpectation): Promise<void>
  /**
   * Explicit destructive recovery for storage that cannot be parsed well
   * enough to use the normal identity/revision-guarded clear operation.
   */
  purgeCorruptLeagueStorage(): Promise<void>
}

interface StoredLeagueSnapshotRecord {
  readonly leagueId: LeagueId
  readonly snapshot: unknown
}

/**
 * Adds validation, revisions, and rollback-safe decisions to an injected
 * transaction-capable storage adapter.
 */
export function createLeagueSnapshotRepository(
  storage: LeagueSnapshotStorage,
): LeagueSnapshotRepository {
  return {
    async restore() {
      let slot: LeagueSnapshotStorageSlot
      try {
        slot = await storage.read()
      } catch (error) {
        return createStorageRecoveryResult(error)
      }

      if (!slot.present) {
        return { kind: 'empty' }
      }

      const storedVersion = readStoredSnapshotVersion(slot.value)
      if (
        storedVersion !== null &&
        storedVersion !== LEAGUE_SNAPSHOT_VERSION
      ) {
        return {
          kind: 'version-mismatch',
          storedVersion,
          supportedVersion: LEAGUE_SNAPSHOT_VERSION,
        }
      }

      try {
        const record = parseStoredRecord(slot.value)
        return {
          kind: 'restored',
          snapshot: parseLeagueSnapshot(record.snapshot),
        }
      } catch (error) {
        return createSnapshotRecoveryResult(error)
      }
    },

    async create(snapshot) {
      const parsedSnapshot = parseLeagueSnapshot(snapshot)
      if (parsedSnapshot.revision !== 1) {
        throw new LeagueSnapshotRevisionError(
          'A newly created snapshot must start at revision 1',
        )
      }
      const record = createStoredRecord(parsedSnapshot)

      return storage.transact((slot) => {
        if (slot.present) {
          throw new LeagueSnapshotConflictError(
            'An active league snapshot already exists',
          )
        }
        return {
          mutation: { kind: 'write', mode: 'add', record },
          verify: (reread) => verifyStoredWrite(parsedSnapshot, reread),
        }
      })
    },

    async updateManagedTeam(input) {
      const expectedLeagueId = parseLeagueId(input.expectedLeagueId)
      const expectedRevision = parseExpectedRevision(input.expectedRevision)
      const managedTeamId =
        input.managedTeamId === null
          ? null
          : parseTeamId(input.managedTeamId)

      return storage.transact((slot) => {
        if (!slot.present) {
          throw new LeagueSnapshotStaleWriteError(
            'update',
            expectedRevision,
            null,
            'The active league snapshot no longer exists',
          )
        }
        const currentRecord = parseStoredRecord(slot.value)
        const current = parseLeagueSnapshot(currentRecord.snapshot)
        if (current.league.id !== expectedLeagueId) {
          throw new LeagueSnapshotConflictError(
            'A managed-team update cannot replace a different league',
          )
        }
        if (current.revision !== expectedRevision) {
          throw new LeagueSnapshotStaleWriteError(
            'update',
            expectedRevision,
            current.revision,
            'The active league changed before the managed team could be updated',
          )
        }
        if (current.revision === Number.MAX_SAFE_INTEGER) {
          throw new LeagueSnapshotRevisionError(
            'The active league revision cannot be incremented safely',
          )
        }

        const next = parseLeagueSnapshot({
          ...current,
          revision: current.revision + 1,
          managedTeamId,
        })
        return {
          mutation: {
            kind: 'write',
            mode: 'put',
            record: createStoredRecord(next),
          },
          verify: (reread) => verifyStoredWrite(next, reread),
        }
      })
    },

    async clear(expectation) {
      const parsedExpectation = parseClearExpectation(expectation)
      await storage.transact((slot) => {
        if (!slot.present) {
          throw new LeagueSnapshotConflictError(
            'The active league snapshot no longer exists',
          )
        }

        const storedVersion = readStoredSnapshotVersion(slot.value)
        if (parsedExpectation.kind === 'version-mismatch') {
          if (
            storedVersion === null ||
            storedVersion === LEAGUE_SNAPSHOT_VERSION
          ) {
            throw new LeagueSnapshotConflictError(
              'The stored league record is no longer a refused older-version snapshot',
            )
          }
          if (storedVersion !== parsedExpectation.expectedStoredVersion) {
            throw new LeagueSnapshotConflictError(
              'The stored league record changed before it could be cleared',
            )
          }
        } else {
          if (
            storedVersion !== null &&
            storedVersion !== LEAGUE_SNAPSHOT_VERSION
          ) {
            throw new LeagueSnapshotStaleWriteError(
              'clear',
              parsedExpectation.expectedRevision,
              null,
              'The expected active league snapshot no longer exists',
            )
          }
          const currentRecord = parseStoredRecord(slot.value)
          const current = parseLeagueSnapshot(currentRecord.snapshot)
          if (current.league.id !== parsedExpectation.expectedLeagueId) {
            throw new LeagueSnapshotConflictError(
              'The active league changed before it could be cleared',
            )
          }
          if (current.revision !== parsedExpectation.expectedRevision) {
            throw new LeagueSnapshotStaleWriteError(
              'clear',
              parsedExpectation.expectedRevision,
              current.revision,
              'The active league revision changed before it could be cleared',
            )
          }
        }

        return {
          mutation: { kind: 'clear' },
          verify: (reread) => {
            if (reread.present) {
              throw new LeagueSnapshotStorageError(
                'The active league records remained after clear verification',
                undefined,
                'reread',
              )
            }
          },
        }
      })
    },

    async purgeCorruptLeagueStorage() {
      await storage.transact(() => ({
        mutation: { kind: 'clear' },
        verify: (reread) => {
          if (reread.present) {
            throw new LeagueSnapshotStorageError(
              'The corrupt active league records remained after recovery purge verification',
              undefined,
              'reread',
            )
          }
        },
      }))
    },
  }
}

export function createStoredLeagueSnapshotRecord(
  snapshot: LeagueSnapshot,
): unknown {
  return createStoredRecord(snapshot)
}

function createStoredRecord(
  snapshot: LeagueSnapshot,
): StoredLeagueSnapshotRecord {
  return { leagueId: snapshot.league.id, snapshot }
}

function parseStoredRecord(value: unknown): StoredLeagueSnapshotRecord {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    throw invalidStoredRecord()
  }
  const prototype = Object.getPrototypeOf(value)
  const keys = Reflect.ownKeys(value)
  if (
    (prototype !== Object.prototype && prototype !== null) ||
    keys.length !== 2 ||
    !Object.prototype.hasOwnProperty.call(value, 'leagueId') ||
    !Object.prototype.hasOwnProperty.call(value, 'snapshot')
  ) {
    throw invalidStoredRecord()
  }
  for (const key of keys) {
    if (typeof key !== 'string' || (key !== 'leagueId' && key !== 'snapshot')) {
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

  const source = value as Record<string, unknown>
  const leagueId = parseLeagueId(source.leagueId)
  if (!hasMatchingSnapshotLeagueId(source.snapshot, leagueId)) {
    throw invalidStoredRecord()
  }
  return { leagueId, snapshot: source.snapshot }
}

function hasMatchingSnapshotLeagueId(
  snapshot: unknown,
  leagueId: LeagueId,
): boolean {
  if (
    snapshot === null ||
    typeof snapshot !== 'object' ||
    Array.isArray(snapshot)
  ) {
    return false
  }
  const leagueDescriptor = Object.getOwnPropertyDescriptor(snapshot, 'league')
  if (
    leagueDescriptor === undefined ||
    !Object.prototype.hasOwnProperty.call(leagueDescriptor, 'value') ||
    leagueDescriptor.value === null ||
    typeof leagueDescriptor.value !== 'object' ||
    Array.isArray(leagueDescriptor.value)
  ) {
    return false
  }
  const idDescriptor = Object.getOwnPropertyDescriptor(
    leagueDescriptor.value,
    'id',
  )
  return (
    idDescriptor !== undefined &&
    Object.prototype.hasOwnProperty.call(idDescriptor, 'value') &&
    idDescriptor.value === leagueId
  )
}

function verifyStoredWrite(
  expected: LeagueSnapshot,
  reread: LeagueSnapshotStorageSlot,
): LeagueSnapshot {
  if (!reread.present) {
    throw new LeagueSnapshotStorageError(
      'The written snapshot could not be re-read',
      undefined,
      'reread',
    )
  }
  const record = parseStoredRecord(reread.value)
  const restored = parseLeagueSnapshot(record.snapshot)
  if (!areStructurallyEqual(expected, restored)) {
    throw new LeagueSnapshotStorageError(
      'The re-read snapshot differs from the value written',
      undefined,
      'reread',
    )
  }
  return restored
}

function parseExpectedRevision(value: number): number {
  if (!Number.isSafeInteger(value) || value <= 0) {
    throw new LeagueSnapshotRevisionError(
      'Expected revision must be a positive safe integer',
    )
  }
  return value
}

function parseClearExpectation(
  expectation: ClearActiveLeagueExpectation,
): ClearActiveLeagueExpectation {
  if (expectation.kind === 'version-mismatch') {
    const { expectedStoredVersion } = expectation
    if (
      !Number.isSafeInteger(expectedStoredVersion) ||
      expectedStoredVersion === LEAGUE_SNAPSHOT_VERSION
    ) {
      throw new LeagueSnapshotConflictError(
        'A version-mismatch clear requires the refused stored snapshot version',
      )
    }
    return { kind: 'version-mismatch', expectedStoredVersion }
  }
  return {
    kind: 'snapshot',
    expectedLeagueId: parseLeagueId(expectation.expectedLeagueId),
    expectedRevision: parseExpectedRevision(expectation.expectedRevision),
  }
}

function createStorageRecoveryResult(
  error: unknown,
): Extract<LeagueSnapshotRestorationResult, { kind: 'recovery-required' }> {
  return {
    kind: 'recovery-required',
    source: 'storage',
    reason: 'storage-failure',
    code: 'league_snapshot_repository.storage_failed',
    message:
      error instanceof Error
        ? error.message
        : 'Local league storage could not be read',
    issues: [],
  }
}

function createSnapshotRecoveryResult(
  error: unknown,
): Extract<LeagueSnapshotRestorationResult, { kind: 'recovery-required' }> {
  const issues = extractIssues(error)
  const unsupportedRuleSet = issues.some(({ code }) =>
    code.includes('rule_set.unsupported_version') ||
    code.includes('rule_set.unknown_id'),
  )
  const reason: LeagueSnapshotRecoveryReason = unsupportedRuleSet
    ? 'unsupported-rule-set-version'
    : isParsingFailure(error, issues)
      ? 'parsing-failure'
      : 'validation-failure'

  return {
    kind: 'recovery-required',
    source: 'snapshot',
    reason,
    code:
      issues[0]?.code ??
      `league_snapshot_repository.snapshot_${reason.replaceAll('-', '_')}`,
    message:
      'The stored league snapshot is invalid or unsupported and was left unchanged.',
    issues,
  }
}

function readStoredSnapshotVersion(record: unknown): number | null {
  if (record === null || typeof record !== 'object' || Array.isArray(record)) {
    return null
  }
  const snapshotDescriptor = Object.getOwnPropertyDescriptor(record, 'snapshot')
  if (
    snapshotDescriptor === undefined ||
    !Object.prototype.hasOwnProperty.call(snapshotDescriptor, 'value') ||
    snapshotDescriptor.value === null ||
    typeof snapshotDescriptor.value !== 'object' ||
    Array.isArray(snapshotDescriptor.value)
  ) {
    return null
  }
  const versionDescriptor = Object.getOwnPropertyDescriptor(
    snapshotDescriptor.value,
    'snapshotVersion',
  )
  return versionDescriptor !== undefined &&
    Object.prototype.hasOwnProperty.call(versionDescriptor, 'value') &&
    typeof versionDescriptor.value === 'number' &&
    Number.isSafeInteger(versionDescriptor.value)
    ? versionDescriptor.value
    : null
}

function isParsingFailure(
  error: unknown,
  issues: readonly LeagueSnapshotRepositoryIssue[],
): boolean {
  if (issues.some(({ code }) => code.includes('structure.invalid'))) {
    return true
  }
  return (
    error instanceof InvalidLeagueSnapshotError &&
    /expected|missing|unexpected|property|array|object/i.test(error.message)
  )
}

function extractIssues(
  error: unknown,
): readonly LeagueSnapshotRepositoryIssue[] {
  if (error instanceof InvalidLeagueSnapshotError) {
    return error.issues
  }
  return []
}

function areStructurallyEqual(left: unknown, right: unknown): boolean {
  if (Object.is(left, right)) return true
  if (Array.isArray(left) || Array.isArray(right)) {
    return (
      Array.isArray(left) &&
      Array.isArray(right) &&
      left.length === right.length &&
      left.every((item, index) => areStructurallyEqual(item, right[index]))
    )
  }
  if (!isRecord(left) || !isRecord(right)) return false
  const leftKeys = Object.keys(left).sort()
  const rightKeys = Object.keys(right).sort()
  return (
    leftKeys.length === rightKeys.length &&
    leftKeys.every(
      (key, index) =>
        key === rightKeys[index] &&
        areStructurallyEqual(left[key], right[key]),
    )
  )
}

function isRecord(value: unknown): value is Readonly<Record<string, unknown>> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function invalidStoredRecord(): InvalidLeagueSnapshotError {
  return new InvalidLeagueSnapshotError([
    {
      code: 'league_snapshot_repository.stored_record.invalid',
      path: '$',
      message: 'The stored active-league record is invalid',
    },
  ])
}
