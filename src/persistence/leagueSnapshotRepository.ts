import { parseLeagueId, parseTeamId } from '../domain/ids'
import type { LeagueId, TeamId } from '../domain/ids'
import type { SeasonFoundationConfigurationInput } from '../app/commands/createSeasonFoundation'
import {
  InvalidLeagueSnapshotError,
  LEAGUE_SNAPSHOT_VERSION,
  parseLeagueSnapshot,
} from './leagueSnapshot'
import type { LeagueSnapshotV1 } from './leagueSnapshot'
import {
  InvalidLeagueSnapshotV2Error,
  LEAGUE_SNAPSHOT_V2_VERSION,
  parseLeagueSnapshotV2,
} from './leagueSnapshotV2'
import type { LeagueSnapshotV2 } from './leagueSnapshotV2'
import {
  LeagueSnapshotV1ToV2MigrationError,
  migrateLeagueSnapshotV1ToV2,
} from './migrations/migrateLeagueSnapshotV1ToV2'

export interface VersionedLeagueSnapshotStorageSlot {
  readonly present: boolean
  readonly value: unknown
}

export interface VersionedLeagueSnapshotStorageState {
  /** Raw structured-cloned record stored at the authoritative V1 location. */
  readonly v1: VersionedLeagueSnapshotStorageSlot
  /** Raw structured-cloned record stored at the authoritative V2 location. */
  readonly v2: VersionedLeagueSnapshotStorageSlot
}

export type LeagueSnapshotStorageMutation =
  | {
      readonly kind: 'write-v2'
      readonly mode: 'add' | 'put'
      readonly record: unknown
    }
  | {
      readonly kind: 'clear-both'
    }

export interface LeagueSnapshotStorageTransactionPlan<Result> {
  readonly mutation: LeagueSnapshotStorageMutation
  /** Runs against values re-read after the staged mutation and before commit. */
  readonly verify: (state: VersionedLeagueSnapshotStorageState) => Result
}

/**
 * Browser-independent transaction boundary. A storage implementation must
 * publish no mutation unless prepare, mutation, re-read, verify, and commit all
 * succeed.
 */
export interface LeagueSnapshotStorage {
  read(): Promise<VersionedLeagueSnapshotStorageState>
  transact<Result>(
    prepare: (
      state: VersionedLeagueSnapshotStorageState,
    ) => LeagueSnapshotStorageTransactionPlan<Result>,
  ): Promise<Result>
}

export const LEAGUE_SNAPSHOT_STORAGE_PHASES = [
  'open',
  'read',
  'write-v2',
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

export const LEAGUE_SNAPSHOT_REPOSITORY_MIGRATION_STAGES = [
  'read-v1-storage',
  'parse-v1',
  'pure-migration',
  'validate-v2',
  'write-v2',
  'reread-v2',
  'revalidate-v2',
  'compare-v2',
  'commit-transaction',
] as const

export type LeagueSnapshotRepositoryMigrationStage =
  (typeof LEAGUE_SNAPSHOT_REPOSITORY_MIGRATION_STAGES)[number]

export interface LeagueSnapshotRepositoryIssue {
  readonly code: string
  readonly path: string
  readonly message: string
}

export class LeagueSnapshotRepositoryMigrationError extends LeagueSnapshotStorageError {
  readonly stage: LeagueSnapshotRepositoryMigrationStage
  readonly code: string
  readonly issues: readonly LeagueSnapshotRepositoryIssue[]

  constructor(
    stage: LeagueSnapshotRepositoryMigrationStage,
    code: string,
    message: string,
    issues: readonly LeagueSnapshotRepositoryIssue[] = [],
    cause?: unknown,
  ) {
    super(message, cause)
    this.name = 'LeagueSnapshotRepositoryMigrationError'
    this.stage = stage
    this.code = code
    this.issues = Object.freeze(
      issues.map((issue) => Object.freeze({ ...issue })),
    )
  }
}

export const LEAGUE_SNAPSHOT_RECOVERY_REASONS = [
  'storage-failure',
  'parsing-failure',
  'validation-failure',
  'unsupported-snapshot-version',
  'unsupported-rule-set-version',
] as const

export type LeagueSnapshotRecoveryReason =
  (typeof LEAGUE_SNAPSHOT_RECOVERY_REASONS)[number]

export type LeagueSnapshotRestorationResult =
  | {
      readonly kind: 'empty'
    }
  | {
      readonly kind: 'restored-v2'
      readonly snapshot: LeagueSnapshotV2
    }
  | {
      readonly kind: 'migration-required'
      readonly snapshotVersion: typeof LEAGUE_SNAPSHOT_VERSION
      readonly leagueId: LeagueId
    }
  | {
      readonly kind: 'recovery-required'
      readonly source: 'storage' | 'v1' | 'v2'
      readonly reason: LeagueSnapshotRecoveryReason
      readonly code: string
      readonly message: string
      readonly issues: readonly LeagueSnapshotRepositoryIssue[]
      readonly v1Present: boolean
      readonly v2Present: boolean
      /** True means an invalid authoritative V2 prevented V1 fallback. */
      readonly v1FallbackBlocked: boolean
    }

export interface MigrateStoredLeagueSnapshotInput {
  readonly expectedV1LeagueId: LeagueId
  readonly seasonCreationInputs: SeasonFoundationConfigurationInput
}

export interface UpdateManagedTeamInput {
  readonly expectedLeagueId: LeagueId
  readonly expectedRevision: number
  readonly managedTeamId: TeamId | null
}

export type ClearActiveLeagueExpectation =
  | {
      readonly kind: 'v2'
      readonly expectedLeagueId: LeagueId
      readonly expectedRevision: number
    }
  | {
      readonly kind: 'v1'
      readonly expectedLeagueId: LeagueId
    }

/** Application-facing access to the one atomic active-league snapshot. */
export interface LeagueSnapshotRepository {
  restore(): Promise<LeagueSnapshotRestorationResult>
  createV2(snapshot: LeagueSnapshotV2): Promise<LeagueSnapshotV2>
  migrateV1ToV2(
    input: MigrateStoredLeagueSnapshotInput,
  ): Promise<LeagueSnapshotV2>
  updateManagedTeam(
    input: UpdateManagedTeamInput,
  ): Promise<LeagueSnapshotV2>
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
 * Adds validation, precedence, revisions, and rollback-safe decisions to an
 * injected transaction-capable storage adapter.
 */
export function createLeagueSnapshotRepository(
  storage: LeagueSnapshotStorage,
): LeagueSnapshotRepository {
  return {
    async restore() {
      let state: VersionedLeagueSnapshotStorageState
      try {
        state = await storage.read()
      } catch (error) {
        return createStorageRecoveryResult(error)
      }

      if (state.v2.present) {
        try {
          const record = parseStoredRecord(state.v2.value, 'v2')
          return {
            kind: 'restored-v2',
            snapshot: parseLeagueSnapshotV2(record.snapshot),
          }
        } catch (error) {
          return createSnapshotRecoveryResult('v2', error, state)
        }
      }

      if (state.v1.present) {
        try {
          const record = parseStoredRecord(state.v1.value, 'v1')
          const snapshot = parseLeagueSnapshot(record.snapshot)
          return {
            kind: 'migration-required',
            snapshotVersion: LEAGUE_SNAPSHOT_VERSION,
            leagueId: snapshot.league.id,
          }
        } catch (error) {
          return createSnapshotRecoveryResult('v1', error, state)
        }
      }

      return { kind: 'empty' }
    },

    async createV2(snapshot) {
      const parsedSnapshot = parseLeagueSnapshotV2(snapshot)
      if (parsedSnapshot.revision !== 1) {
        throw new LeagueSnapshotRevisionError(
          'A newly created V2 snapshot must start at revision 1',
        )
      }
      const record = createStoredRecord(parsedSnapshot)

      return storage.transact((state) => {
        if (state.v1.present || state.v2.present) {
          throw new LeagueSnapshotConflictError(
            'An active league snapshot already exists',
          )
        }
        return {
          mutation: { kind: 'write-v2', mode: 'add', record },
          verify: (reread) =>
            verifyStoredV2Write(parsedSnapshot, state.v1, reread),
        }
      })
    },

    async migrateV1ToV2(input) {
      let expectedLeagueId: LeagueId
      try {
        expectedLeagueId = parseLeagueId(input.expectedV1LeagueId)
      } catch (error) {
        throw migrationErrorFrom(
          'parse-v1',
          'league_snapshot_repository.migration.v1_identity_invalid',
          'The expected V1 league identity is invalid',
          error,
        )
      }
      try {
        return await storage.transact((state) => {
          if (state.v2.present) {
            throw migrationError(
              'read-v1-storage',
              'league_snapshot_repository.migration.v2_exists',
              'Migration cannot replace an existing authoritative V2 snapshot',
            )
          }
          if (!state.v1.present) {
            throw migrationError(
              'read-v1-storage',
              'league_snapshot_repository.migration.v1_missing',
              'The stored V1 snapshot no longer exists',
            )
          }

          const originalV1Record = state.v1.value
          let v1Snapshot: LeagueSnapshotV1
          try {
            const record = parseStoredRecord(originalV1Record, 'v1')
            v1Snapshot = parseLeagueSnapshot(record.snapshot)
          } catch (error) {
            throw migrationErrorFrom(
              'parse-v1',
              'league_snapshot_repository.migration.v1_invalid',
              'The stored V1 snapshot is invalid',
              error,
            )
          }
          if (v1Snapshot.league.id !== expectedLeagueId) {
            throw migrationError(
              'parse-v1',
              'league_snapshot_repository.migration.v1_identity_changed',
              'The stored V1 league changed before migration began',
            )
          }

          let migrated: LeagueSnapshotV2
          try {
            migrated = migrateLeagueSnapshotV1ToV2(
              v1Snapshot,
              input.seasonCreationInputs,
            )
          } catch (error) {
            throw migrationErrorFrom(
              'pure-migration',
              'league_snapshot_repository.migration.pure_failed',
              'The pure V1-to-V2 migration failed',
              error,
            )
          }

          let validatedV2: LeagueSnapshotV2
          try {
            validatedV2 = parseLeagueSnapshotV2(migrated)
          } catch (error) {
            throw migrationErrorFrom(
              'validate-v2',
              'league_snapshot_repository.migration.v2_invalid',
              'The migrated V2 snapshot failed validation',
              error,
            )
          }

          return {
            mutation: {
              kind: 'write-v2',
              mode: 'add',
              record: createStoredRecord(validatedV2),
            },
            verify: (reread) => {
              if (!reread.v1.present) {
                throw migrationError(
                  'compare-v2',
                  'league_snapshot_repository.migration.v1_removed',
                  'The original V1 record was not preserved',
                )
              }
              if (!areStructurallyEqual(originalV1Record, reread.v1.value)) {
                throw migrationError(
                  'compare-v2',
                  'league_snapshot_repository.migration.v1_changed',
                  'The original V1 record changed during migration',
                )
              }
              if (!reread.v2.present) {
                throw migrationError(
                  'reread-v2',
                  'league_snapshot_repository.migration.v2_missing',
                  'The written V2 record could not be re-read',
                )
              }

              let restored: LeagueSnapshotV2
              try {
                const rereadRecord = parseStoredRecord(reread.v2.value, 'v2')
                restored = parseLeagueSnapshotV2(rereadRecord.snapshot)
              } catch (error) {
                throw migrationErrorFrom(
                  'revalidate-v2',
                  'league_snapshot_repository.migration.v2_reread_invalid',
                  'The re-read V2 snapshot failed validation',
                  error,
                )
              }
              if (!areStructurallyEqual(validatedV2, restored)) {
                throw migrationError(
                  'compare-v2',
                  'league_snapshot_repository.migration.v2_changed',
                  'The re-read V2 snapshot differs from the validated value written',
                )
              }
              return restored
            },
          }
        })
      } catch (error) {
        if (error instanceof LeagueSnapshotRepositoryMigrationError) {
          throw error
        }
        throw mapStorageMigrationError(error)
      }
    },

    async updateManagedTeam(input) {
      const expectedLeagueId = parseLeagueId(input.expectedLeagueId)
      const expectedRevision = parseExpectedRevision(input.expectedRevision)
      const managedTeamId =
        input.managedTeamId === null
          ? null
          : parseTeamId(input.managedTeamId)

      return storage.transact((state) => {
        if (!state.v2.present) {
          throw new LeagueSnapshotStaleWriteError(
            'update',
            expectedRevision,
            null,
            'The authoritative V2 snapshot no longer exists',
          )
        }
        const currentRecord = parseStoredRecord(state.v2.value, 'v2')
        const current = parseLeagueSnapshotV2(currentRecord.snapshot)
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

        const next = parseLeagueSnapshotV2({
          ...current,
          revision: current.revision + 1,
          managedTeamId,
        })
        return {
          mutation: {
            kind: 'write-v2',
            mode: 'put',
            record: createStoredRecord(next),
          },
          verify: (reread) =>
            verifyStoredV2Write(next, state.v1, reread),
        }
      })
    },

    async clear(expectation) {
      const parsedExpectation = parseClearExpectation(expectation)
      await storage.transact((state) => {
        if (state.v2.present) {
          const currentRecord = parseStoredRecord(state.v2.value, 'v2')
          const current = parseLeagueSnapshotV2(currentRecord.snapshot)
          if (parsedExpectation.kind !== 'v2') {
            throw new LeagueSnapshotStaleWriteError(
              'clear',
              null,
              current.revision,
              'A V1 clear request cannot remove an authoritative V2 snapshot',
            )
          }
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
        } else if (state.v1.present) {
          if (parsedExpectation.kind !== 'v1') {
            throw new LeagueSnapshotStaleWriteError(
              'clear',
              parsedExpectation.expectedRevision,
              null,
              'The expected V2 snapshot no longer exists',
            )
          }
          const currentRecord = parseStoredRecord(state.v1.value, 'v1')
          const current = parseLeagueSnapshot(currentRecord.snapshot)
          if (current.league.id !== parsedExpectation.expectedLeagueId) {
            throw new LeagueSnapshotConflictError(
              'The stored V1 league changed before it could be cleared',
            )
          }
        } else {
          throw new LeagueSnapshotConflictError(
            'The active league snapshot no longer exists',
          )
        }

        return {
          mutation: { kind: 'clear-both' },
          verify: (reread) => {
            if (reread.v1.present || reread.v2.present) {
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
        mutation: { kind: 'clear-both' },
        verify: (reread) => {
          if (reread.v1.present || reread.v2.present) {
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
  snapshot: LeagueSnapshotV1 | LeagueSnapshotV2,
): unknown {
  return createStoredRecord(snapshot)
}

function createStoredRecord(
  snapshot: LeagueSnapshotV1 | LeagueSnapshotV2,
): StoredLeagueSnapshotRecord {
  return { leagueId: snapshot.league.id, snapshot }
}

function parseStoredRecord(
  value: unknown,
  version: 'v1' | 'v2',
): StoredLeagueSnapshotRecord {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    throw invalidStoredRecord(version)
  }
  const prototype = Object.getPrototypeOf(value)
  const keys = Reflect.ownKeys(value)
  if (
    (prototype !== Object.prototype && prototype !== null) ||
    keys.length !== 2 ||
    !Object.prototype.hasOwnProperty.call(value, 'leagueId') ||
    !Object.prototype.hasOwnProperty.call(value, 'snapshot')
  ) {
    throw invalidStoredRecord(version)
  }
  for (const key of keys) {
    if (typeof key !== 'string' || (key !== 'leagueId' && key !== 'snapshot')) {
      throw invalidStoredRecord(version)
    }
    const descriptor = Object.getOwnPropertyDescriptor(value, key)
    if (
      descriptor === undefined ||
      !descriptor.enumerable ||
      !Object.prototype.hasOwnProperty.call(descriptor, 'value')
    ) {
      throw invalidStoredRecord(version)
    }
  }

  const source = value as Record<string, unknown>
  const leagueId = parseLeagueId(source.leagueId)
  if (!hasMatchingSnapshotLeagueId(source.snapshot, leagueId)) {
    throw invalidStoredRecord(version)
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

function verifyStoredV2Write(
  expected: LeagueSnapshotV2,
  expectedV1: VersionedLeagueSnapshotStorageSlot,
  reread: VersionedLeagueSnapshotStorageState,
): LeagueSnapshotV2 {
  if (
    expectedV1.present !== reread.v1.present ||
    !areStructurallyEqual(expectedV1.value, reread.v1.value)
  ) {
    throw new LeagueSnapshotStorageError(
      'The V1 storage location changed during the V2 write',
      undefined,
      'reread',
    )
  }
  if (!reread.v2.present) {
    throw new LeagueSnapshotStorageError(
      'The written V2 snapshot could not be re-read',
      undefined,
      'reread',
    )
  }
  const record = parseStoredRecord(reread.v2.value, 'v2')
  const restored = parseLeagueSnapshotV2(record.snapshot)
  if (!areStructurallyEqual(expected, restored)) {
    throw new LeagueSnapshotStorageError(
      'The re-read V2 snapshot differs from the value written',
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
  if (expectation.kind === 'v1') {
    return {
      kind: 'v1',
      expectedLeagueId: parseLeagueId(expectation.expectedLeagueId),
    }
  }
  return {
    kind: 'v2',
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
    v1Present: false,
    v2Present: false,
    v1FallbackBlocked: false,
  }
}

function createSnapshotRecoveryResult(
  source: 'v1' | 'v2',
  error: unknown,
  state: VersionedLeagueSnapshotStorageState,
): Extract<LeagueSnapshotRestorationResult, { kind: 'recovery-required' }> {
  const issues = extractIssues(error)
  const rawRecord = source === 'v2' ? state.v2.value : state.v1.value
  const expectedVersion =
    source === 'v2' ? LEAGUE_SNAPSHOT_V2_VERSION : LEAGUE_SNAPSHOT_VERSION
  const storedVersion = readStoredSnapshotVersion(rawRecord)
  const unsupportedVersion =
    storedVersion !== null && storedVersion !== expectedVersion
  const unsupportedRuleSet = issues.some(({ code }) =>
    code.includes('rule_set.unsupported_version') ||
    code.includes('rule_set.unknown_id'),
  )
  const reason: LeagueSnapshotRecoveryReason = unsupportedVersion
    ? 'unsupported-snapshot-version'
    : unsupportedRuleSet
      ? 'unsupported-rule-set-version'
      : isParsingFailure(error, issues)
        ? 'parsing-failure'
        : 'validation-failure'

  return {
    kind: 'recovery-required',
    source,
    reason,
    code:
      issues[0]?.code ??
      `league_snapshot_repository.${source}_${reason.replaceAll('-', '_')}`,
    message:
      source === 'v2'
        ? 'The authoritative V2 league snapshot is invalid or unsupported; no V1 fallback was attempted.'
        : 'The stored V1 league snapshot is invalid or unsupported.',
    issues,
    v1Present: state.v1.present,
    v2Present: state.v2.present,
    v1FallbackBlocked: source === 'v2' && state.v1.present,
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
  if (error instanceof InvalidLeagueSnapshotV2Error) {
    return error.issues
  }
  if (error instanceof InvalidLeagueSnapshotError) {
    return [
      {
        code: 'league_snapshot_v1.invalid',
        path: error.path,
        message: stripLeadingPath(error.message, error.path),
      },
    ]
  }
  if (error instanceof LeagueSnapshotV1ToV2MigrationError) {
    return error.issues
  }
  return []
}

function migrationError(
  stage: LeagueSnapshotRepositoryMigrationStage,
  code: string,
  message: string,
): LeagueSnapshotRepositoryMigrationError {
  return new LeagueSnapshotRepositoryMigrationError(stage, code, message)
}

function migrationErrorFrom(
  stage: LeagueSnapshotRepositoryMigrationStage,
  code: string,
  message: string,
  cause: unknown,
): LeagueSnapshotRepositoryMigrationError {
  return new LeagueSnapshotRepositoryMigrationError(
    stage,
    code,
    `${message}: ${errorMessage(cause)}`,
    extractIssues(cause),
    cause,
  )
}

function mapStorageMigrationError(
  error: unknown,
): LeagueSnapshotRepositoryMigrationError {
  const phase =
    error instanceof LeagueSnapshotStorageError ? error.phase : null
  const stage: LeagueSnapshotRepositoryMigrationStage =
    phase === 'write-v2'
      ? 'write-v2'
      : phase === 'reread'
        ? 'reread-v2'
        : phase === 'commit'
          ? 'commit-transaction'
          : 'read-v1-storage'
  return migrationErrorFrom(
    stage,
    `league_snapshot_repository.migration.${stage.replaceAll('-', '_')}_failed`,
    `Stored migration failed during ${stage}`,
    error,
  )
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

function invalidStoredRecord(version: 'v1' | 'v2'): InvalidLeagueSnapshotError {
  return new InvalidLeagueSnapshotError(
    '$',
    `The stored ${version.toUpperCase()} active-league record is invalid`,
  )
}

function stripLeadingPath(message: string, path: string): string {
  const prefix = `${path}: `
  return message.startsWith(prefix) ? message.slice(prefix.length) : message
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Unknown persistence failure'
}
