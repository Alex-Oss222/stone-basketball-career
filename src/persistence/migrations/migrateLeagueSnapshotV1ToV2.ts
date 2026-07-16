import {
  InvalidSeasonFoundationError,
  createSeasonFoundation,
  parseSeasonFoundationConfiguration,
} from '../../app/commands/createSeasonFoundation'
import type {
  SeasonFoundationConfigurationInput,
} from '../../app/commands/createSeasonFoundation'
import {
  InvalidLeagueSnapshotError,
  parseLeagueSnapshot,
} from '../leagueSnapshot'
import {
  InvalidLeagueSnapshotV2Error,
  parseLeagueSnapshotV2,
  serializeLeagueSnapshotV2,
} from '../leagueSnapshotV2'
import type { LeagueSnapshotV2 } from '../leagueSnapshotV2'
import {
  assertJsonSafeValue,
  expectExactRecord,
} from '../strictSerializedValue'
import type { RejectSerializedValue } from '../strictSerializedValue'

export type LeagueSnapshotV1ToV2SeasonCreationInputs =
  SeasonFoundationConfigurationInput

export const LEAGUE_SNAPSHOT_V1_TO_V2_MIGRATION_STAGES = [
  'parse-v1',
  'validate-inputs',
  'create-season-foundation',
  'construct-v2',
  'validate-v2',
  'serialize-round-trip',
] as const

export type LeagueSnapshotV1ToV2MigrationStage =
  (typeof LEAGUE_SNAPSHOT_V1_TO_V2_MIGRATION_STAGES)[number]

export type LeagueSnapshotMigrationStage =
  LeagueSnapshotV1ToV2MigrationStage

export interface LeagueSnapshotMigrationIssue {
  readonly code: string
  readonly path: string
  readonly message: string
}

export class LeagueSnapshotV1ToV2MigrationError extends Error {
  readonly stage: LeagueSnapshotV1ToV2MigrationStage
  readonly code: string
  readonly issues: readonly LeagueSnapshotMigrationIssue[]

  constructor(
    stage: LeagueSnapshotV1ToV2MigrationStage,
    code: string,
    message: string,
    issues: readonly LeagueSnapshotMigrationIssue[] = [],
    cause?: unknown,
  ) {
    super(message, cause === undefined ? undefined : { cause })
    this.name = 'LeagueSnapshotV1ToV2MigrationError'
    this.stage = stage
    this.code = code
    this.issues = Object.freeze(
      issues.map((issue) => Object.freeze({ ...issue })),
    )
  }
}

export {
  LeagueSnapshotV1ToV2MigrationError as LeagueSnapshotMigrationError,
}

/**
 * Purely migrates one validated V1 league snapshot into the serialized V2
 * season-foundation DTO. Storage and application state remain outside this
 * boundary, and the supplied snapshot and configuration are never changed.
 */
export function migrateLeagueSnapshotV1ToV2(
  snapshotV1: unknown,
  explicitSeasonCreationInputs: LeagueSnapshotV1ToV2SeasonCreationInputs,
): LeagueSnapshotV2 {
  const parsedV1 = runMigrationStage(
    'parse-v1',
    'league_snapshot_migration.v1_to_v2.parse_v1_failed',
    'The V1 league snapshot could not be parsed',
    () => parseLeagueSnapshot(snapshotV1),
  )

  const creationInputs = runMigrationStage(
    'validate-inputs',
    'league_snapshot_migration.v1_to_v2.invalid_season_inputs',
    'The explicit season-creation inputs are invalid',
    () => parseExplicitSeasonCreationInputs(explicitSeasonCreationInputs),
  )

  const foundation = runMigrationStage(
    'create-season-foundation',
    'league_snapshot_migration.v1_to_v2.season_foundation_failed',
    'The season foundation could not be created',
    () =>
      createSeasonFoundation({
        league: parsedV1.league,
        ...creationInputs,
      }),
  )

  const candidateV2 = runMigrationStage(
    'construct-v2',
    'league_snapshot_migration.v1_to_v2.construct_v2_failed',
    'The serialized V2 snapshot could not be constructed',
    () =>
      serializeLeagueSnapshotV2({
        rootSeed: parsedV1.rootSeed,
        managedTeamId: parsedV1.managedTeamId,
        league: parsedV1.league,
        foundation,
        creationInputs,
      }),
  )

  const validatedV2 = runMigrationStage(
    'validate-v2',
    'league_snapshot_migration.v1_to_v2.validate_v2_failed',
    'The constructed V2 snapshot is invalid',
    () => parseLeagueSnapshotV2(candidateV2),
  )

  return runMigrationStage(
    'serialize-round-trip',
    'league_snapshot_migration.v1_to_v2.serialize_round_trip_failed',
    'The V2 snapshot did not survive its required JSON round trip',
    () => verifyJsonRoundTrip(validatedV2),
  )
}

const SEASON_CREATION_INPUT_KEYS = [
  'startingYear',
  'regularSeasonStartDate',
  'calendarDaySpacing',
  'scheduleSeed',
] as const

function parseExplicitSeasonCreationInputs(
  value: unknown,
): ReturnType<typeof parseSeasonFoundationConfiguration> {
  const reject: RejectSerializedValue = (path, message) => {
    throw new InvalidMigrationInputError([
      {
        code: 'league_snapshot_migration.season_inputs.structure.invalid',
        path,
        message,
      },
    ])
  }
  assertJsonSafeValue(value, '$', reject)
  const source = expectExactRecord(
    value,
    SEASON_CREATION_INPUT_KEYS,
    '$',
    reject,
  )
  try {
    return parseSeasonFoundationConfiguration(
      source as unknown as SeasonFoundationConfigurationInput,
    )
  } catch (error) {
    throw new InvalidMigrationInputError(
      [
        {
          code: 'league_snapshot_migration.season_inputs.invalid',
          path: '$',
          message: errorMessage(error),
        },
      ],
      error,
    )
  }
}

class InvalidMigrationInputError extends Error {
  readonly issues: readonly LeagueSnapshotMigrationIssue[]

  constructor(
    issues: readonly LeagueSnapshotMigrationIssue[],
    cause?: unknown,
  ) {
    super(
      issues[0]?.message ?? 'Migration season inputs are invalid',
      cause === undefined ? undefined : { cause },
    )
    this.name = 'InvalidMigrationInputError'
    this.issues = Object.freeze(
      issues.map((issue) => Object.freeze({ ...issue })),
    )
  }
}

function runMigrationStage<Result>(
  stage: LeagueSnapshotV1ToV2MigrationStage,
  code: string,
  message: string,
  operation: () => Result,
): Result {
  try {
    return operation()
  } catch (error) {
    if (error instanceof LeagueSnapshotV1ToV2MigrationError) {
      throw error
    }

    throw new LeagueSnapshotV1ToV2MigrationError(
      stage,
      code,
      `${message}: ${errorMessage(error)}`,
      extractValidationIssues(error),
      error,
    )
  }
}

function verifyJsonRoundTrip(snapshot: LeagueSnapshotV2): LeagueSnapshotV2 {
  const serialized = JSON.stringify(snapshot)
  if (typeof serialized !== 'string') {
    throw new TypeError('JSON serialization did not produce text')
  }

  const restored = parseLeagueSnapshotV2(JSON.parse(serialized) as unknown)
  if (!areStructurallyEqual(restored, snapshot)) {
    throw new Error('Validated snapshot data changed during JSON serialization')
  }
  return restored
}

function extractValidationIssues(
  error: unknown,
): readonly LeagueSnapshotMigrationIssue[] {
  if (error instanceof InvalidLeagueSnapshotV2Error) {
    return error.issues
  }

  if (error instanceof InvalidSeasonFoundationError) {
    return error.issues.map(({ code, path, message }) => ({
      code,
      path,
      message,
    }))
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

  if (error instanceof InvalidMigrationInputError) {
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

function stripLeadingPath(message: string, path: string): string {
  const prefix = `${path}: `
  return message.startsWith(prefix) ? message.slice(prefix.length) : message
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Unknown migration failure'
}
