import {
  parseLeagueId,
  parsePlayerId,
  parseTeamId,
} from '../domain/ids'
import type { TeamId } from '../domain/ids'
import {
  LEAGUE_PLAYER_COUNT,
  LEAGUE_TEAM_COUNT,
  isPosition,
} from '../domain/league'
import type {
  League,
  Player,
  PlayerTendencies,
  Position,
  Team,
  TeamColors,
  TeamMark,
} from '../domain/league'
import {
  InvalidLeagueError,
  assertValidLeague,
} from '../domain/leagueValidation'
import {
  RATING_GENERATION_VERSION,
  RATING_KEYS,
  parsePlayerRatings,
} from '../domain/ratings'
import { normalizeSeed } from '../random/seed'

export const LEAGUE_SNAPSHOT_KIND =
  'stone-basketball-gm-league-snapshot' as const
export const LEAGUE_SNAPSHOT_VERSION = 1 as const

export interface LeagueSnapshotV1 {
  readonly kind: typeof LEAGUE_SNAPSHOT_KIND
  readonly snapshotVersion: typeof LEAGUE_SNAPSHOT_VERSION
  readonly rootSeed: string
  readonly league: League
  readonly managedTeamId: TeamId | null
}

export class InvalidLeagueSnapshotError extends Error {
  readonly path: string

  constructor(path: string, message: string, cause?: unknown) {
    super(`${path}: ${message}`, cause === undefined ? undefined : { cause })
    this.name = 'InvalidLeagueSnapshotError'
    this.path = path
  }
}

const SNAPSHOT_KEYS = [
  'kind',
  'snapshotVersion',
  'rootSeed',
  'league',
  'managedTeamId',
] as const

const LEAGUE_KEYS = [
  'id',
  'generatorVersion',
  'seedFingerprint',
  'teams',
  'players',
] as const

const TEAM_KEYS = [
  'id',
  'city',
  'nickname',
  'abbreviation',
  'colors',
  'mark',
] as const

const TEAM_COLOR_KEYS = ['primary', 'secondary', 'accent'] as const
const TEAM_MARK_KEYS = ['kind', 'text'] as const

const PLAYER_KEYS = [
  'id',
  'teamId',
  'firstName',
  'lastName',
  'age',
  'jerseyNumber',
  'primaryPosition',
  'secondaryPosition',
  'ratingGenerationVersion',
  'ratings',
  'tendencies',
] as const

const TENDENCY_KEYS = [
  'usage',
  'rim',
  'midrange',
  'threePoint',
  'pass',
  'drawFoul',
] as const

type UnknownRecord = Record<string, unknown>

/**
 * Creates a validated, detached snapshot. The visible seed is normalized once
 * at this trusted write boundary; stored snapshots must already be canonical.
 */
export function createLeagueSnapshot(
  rootSeed: string,
  league: League,
  managedTeamId: TeamId | null,
): LeagueSnapshotV1 {
  const normalizedRootSeed = parseAndNormalizeRootSeed(rootSeed, '$.rootSeed')

  return parseLeagueSnapshot({
    kind: LEAGUE_SNAPSHOT_KIND,
    snapshotVersion: LEAGUE_SNAPSHOT_VERSION,
    rootSeed: normalizedRootSeed,
    league,
    managedTeamId,
  })
}

/**
 * Strictly parses an untrusted V1 snapshot without coercing, repairing,
 * regenerating, or dropping data.
 */
export function parseLeagueSnapshot(value: unknown): LeagueSnapshotV1 {
  const source = expectExactRecord(value, SNAPSHOT_KEYS, '$')

  expectLiteral(source.kind, LEAGUE_SNAPSHOT_KIND, '$.kind')
  expectLiteral(
    source.snapshotVersion,
    LEAGUE_SNAPSHOT_VERSION,
    '$.snapshotVersion',
  )

  const rootSeed = parseCanonicalRootSeed(source.rootSeed, '$.rootSeed')
  const league = parseLeague(source.league, '$.league')
  assertLeagueIsValid(league, '$.league')
  const managedTeamId = parseManagedTeamId(
    source.managedTeamId,
    league,
    '$.managedTeamId',
  )

  return {
    kind: LEAGUE_SNAPSHOT_KIND,
    snapshotVersion: LEAGUE_SNAPSHOT_VERSION,
    rootSeed,
    league,
    managedTeamId,
  }
}

function parseLeague(value: unknown, path: string): League {
  const source = expectExactRecord(value, LEAGUE_KEYS, path)

  expectLiteral(source.generatorVersion, 1, `${path}.generatorVersion`)

  return {
    id: parseAtPath(`${path}.id`, () => parseLeagueId(source.id)),
    generatorVersion: 1,
    seedFingerprint: expectString(
      source.seedFingerprint,
      `${path}.seedFingerprint`,
    ),
    teams: parseExactArray(
      source.teams,
      LEAGUE_TEAM_COUNT,
      `${path}.teams`,
      parseTeam,
    ),
    players: parseExactArray(
      source.players,
      LEAGUE_PLAYER_COUNT,
      `${path}.players`,
      parsePlayer,
    ),
  }
}

function parseTeam(value: unknown, path: string): Team {
  const source = expectExactRecord(value, TEAM_KEYS, path)

  return {
    id: parseAtPath(`${path}.id`, () => parseTeamId(source.id)),
    city: expectString(source.city, `${path}.city`),
    nickname: expectString(source.nickname, `${path}.nickname`),
    abbreviation: expectString(
      source.abbreviation,
      `${path}.abbreviation`,
    ),
    colors: parseTeamColors(source.colors, `${path}.colors`),
    mark: parseTeamMark(source.mark, `${path}.mark`),
  }
}

function parseTeamColors(value: unknown, path: string): TeamColors {
  const source = expectExactRecord(value, TEAM_COLOR_KEYS, path)

  return {
    primary: expectString(source.primary, `${path}.primary`),
    secondary: expectString(source.secondary, `${path}.secondary`),
    accent: expectString(source.accent, `${path}.accent`),
  }
}

function parseTeamMark(value: unknown, path: string): TeamMark {
  const source = expectExactRecord(value, TEAM_MARK_KEYS, path)
  expectLiteral(source.kind, 'initials', `${path}.kind`)

  return {
    kind: 'initials',
    text: expectString(source.text, `${path}.text`),
  }
}

function parsePlayer(value: unknown, path: string): Player {
  const source = expectExactRecord(value, PLAYER_KEYS, path)
  expectLiteral(
    source.ratingGenerationVersion,
    RATING_GENERATION_VERSION,
    `${path}.ratingGenerationVersion`,
  )

  return {
    id: parseAtPath(`${path}.id`, () => parsePlayerId(source.id)),
    teamId: parseAtPath(`${path}.teamId`, () => parseTeamId(source.teamId)),
    firstName: expectString(source.firstName, `${path}.firstName`),
    lastName: expectString(source.lastName, `${path}.lastName`),
    age: expectSafeInteger(source.age, `${path}.age`),
    jerseyNumber: expectSafeInteger(
      source.jerseyNumber,
      `${path}.jerseyNumber`,
    ),
    primaryPosition: parsePosition(
      source.primaryPosition,
      `${path}.primaryPosition`,
    ),
    secondaryPosition: parseSecondaryPosition(
      source.secondaryPosition,
      `${path}.secondaryPosition`,
    ),
    ratingGenerationVersion: RATING_GENERATION_VERSION,
    ratings: parseRatings(source.ratings, `${path}.ratings`),
    tendencies: parseTendencies(source.tendencies, `${path}.tendencies`),
  }
}

function parseRatings(value: unknown, path: string): Player['ratings'] {
  expectExactRecord(value, RATING_KEYS, path)
  return parseAtPath(path, () => parsePlayerRatings(value))
}

function parseTendencies(value: unknown, path: string): PlayerTendencies {
  const source = expectExactRecord(value, TENDENCY_KEYS, path)

  return {
    usage: expectSafeInteger(source.usage, `${path}.usage`),
    rim: expectSafeInteger(source.rim, `${path}.rim`),
    midrange: expectSafeInteger(source.midrange, `${path}.midrange`),
    threePoint: expectSafeInteger(source.threePoint, `${path}.threePoint`),
    pass: expectSafeInteger(source.pass, `${path}.pass`),
    drawFoul: expectSafeInteger(source.drawFoul, `${path}.drawFoul`),
  }
}

function parsePosition(value: unknown, path: string): Position {
  if (!isPosition(value)) {
    throw invalid(path, 'Position must be PG, SG, SF, PF, or C')
  }
  return value
}

function parseSecondaryPosition(
  value: unknown,
  path: string,
): Position | null {
  return value === null ? null : parsePosition(value, path)
}

function parseManagedTeamId(
  value: unknown,
  league: League,
  path: string,
): TeamId | null {
  if (value === null) return null

  const teamId = parseAtPath(path, () => parseTeamId(value))
  const matchingTeams = league.teams.filter((team) => team.id === teamId)
  if (matchingTeams.length !== 1) {
    throw invalid(path, 'Managed team ID must reference one league team')
  }
  return teamId
}

function parseCanonicalRootSeed(value: unknown, path: string): string {
  const rootSeed = expectString(value, path)
  const normalized = parseAndNormalizeRootSeed(rootSeed, path)

  if (normalized !== rootSeed) {
    throw invalid(path, 'Root seed must already be normalized')
  }
  return rootSeed
}

function parseAndNormalizeRootSeed(value: unknown, path: string): string {
  const rootSeed = expectString(value, path)
  return parseAtPath(path, () => normalizeSeed(rootSeed))
}

function assertLeagueIsValid(league: League, path: string): void {
  try {
    assertValidLeague(league)
  } catch (error) {
    if (error instanceof InvalidLeagueError && error.issues.length > 0) {
      const firstIssue = error.issues[0]
      throw invalid(
        prefixLeagueIssuePath(path, firstIssue.path),
        firstIssue.message,
        error,
      )
    }
    throw invalid(path, errorMessage(error, 'League is invalid'), error)
  }
}

function expectExactRecord(
  value: unknown,
  expectedKeys: readonly string[],
  path: string,
): UnknownRecord {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    throw invalid(path, 'Expected an object')
  }

  const prototype = Object.getPrototypeOf(value)
  if (prototype !== Object.prototype && prototype !== null) {
    throw invalid(path, 'Expected a plain object')
  }

  const expectedKeySet = new Set(expectedKeys)
  const actualKeys = Reflect.ownKeys(value)

  for (const expectedKey of expectedKeys) {
    if (!Object.prototype.hasOwnProperty.call(value, expectedKey)) {
      throw invalid(`${path}.${expectedKey}`, 'Required property is missing')
    }
  }

  for (const actualKey of actualKeys) {
    if (typeof actualKey !== 'string') {
      throw invalid(path, 'Symbol properties are not allowed')
    }
    if (!expectedKeySet.has(actualKey)) {
      throw invalid(`${path}.${actualKey}`, 'Unexpected property')
    }

    const descriptor = Object.getOwnPropertyDescriptor(value, actualKey)
    if (
      descriptor === undefined ||
      !descriptor.enumerable ||
      !Object.prototype.hasOwnProperty.call(descriptor, 'value')
    ) {
      throw invalid(
        `${path}.${actualKey}`,
        'Properties must be enumerable data values',
      )
    }
  }

  return value as UnknownRecord
}

function parseExactArray<T>(
  value: unknown,
  expectedLength: number,
  path: string,
  parseItem: (item: unknown, itemPath: string) => T,
): readonly T[] {
  if (!Array.isArray(value) || Object.getPrototypeOf(value) !== Array.prototype) {
    throw invalid(path, 'Expected a plain array')
  }
  if (value.length !== expectedLength) {
    throw invalid(path, `Array must contain exactly ${expectedLength} items`)
  }

  const actualKeys = Reflect.ownKeys(value)
  if (actualKeys.length !== expectedLength + 1) {
    throw invalid(path, 'Array must not be sparse or contain custom properties')
  }

  for (const key of actualKeys) {
    if (typeof key !== 'string') {
      throw invalid(path, 'Array symbol properties are not allowed')
    }
    if (key === 'length') continue

    const index = Number(key)
    if (
      !Number.isInteger(index) ||
      index < 0 ||
      index >= expectedLength ||
      String(index) !== key
    ) {
      throw invalid(path, 'Array contains a custom property')
    }
  }

  const result: T[] = []
  for (let index = 0; index < expectedLength; index += 1) {
    if (!Object.prototype.hasOwnProperty.call(value, index)) {
      throw invalid(`${path}[${index}]`, 'Array item is missing')
    }

    const descriptor = Object.getOwnPropertyDescriptor(value, String(index))
    if (
      descriptor === undefined ||
      !descriptor.enumerable ||
      !Object.prototype.hasOwnProperty.call(descriptor, 'value')
    ) {
      throw invalid(
        `${path}[${index}]`,
        'Array items must be enumerable data values',
      )
    }

    result.push(parseItem(value[index], `${path}[${index}]`))
  }
  return result
}

function expectString(value: unknown, path: string): string {
  if (typeof value !== 'string') {
    throw invalid(path, 'Expected a string')
  }
  return value
}

function expectSafeInteger(value: unknown, path: string): number {
  if (typeof value !== 'number' || !Number.isSafeInteger(value)) {
    throw invalid(path, 'Expected a finite safe integer')
  }
  return value
}

function expectLiteral<T extends string | number>(
  value: unknown,
  expected: T,
  path: string,
): asserts value is T {
  if (value !== expected) {
    throw invalid(path, `Expected literal ${JSON.stringify(expected)}`)
  }
}

function parseAtPath<T>(path: string, parse: () => T): T {
  try {
    return parse()
  } catch (error) {
    if (error instanceof InvalidLeagueSnapshotError) throw error
    throw invalid(path, errorMessage(error, 'Value is invalid'), error)
  }
}

function prefixLeagueIssuePath(prefix: string, issuePath: string): string {
  return issuePath === '$' ? prefix : `${prefix}${issuePath.slice(1)}`
}

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback
}

function invalid(
  path: string,
  message: string,
  cause?: unknown,
): InvalidLeagueSnapshotError {
  return new InvalidLeagueSnapshotError(path, message, cause)
}
