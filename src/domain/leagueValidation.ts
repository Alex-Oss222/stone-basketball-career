import { isLeagueId, isPlayerId, isTeamId } from './ids'
import {
  JERSEY_NUMBER_MAX,
  JERSEY_NUMBER_MIN,
  LEAGUE_PLAYER_COUNT,
  LEAGUE_TEAM_COUNT,
  PLAYER_AGE_MAX,
  PLAYER_AGE_MIN,
  PLAYERS_PER_TEAM,
  isPosition,
} from './league'
import type { League, PlayerTendencies, TeamColors } from './league'
import {
  RATING_GENERATION_VERSION,
  RATING_KEYS,
  STORED_RATING_MAX,
  STORED_RATING_MIN,
  isRatingKey,
  isStoredRating,
} from './ratings'

export interface LeagueValidationIssue {
  readonly code: string
  readonly path: string
  readonly message: string
}

export class InvalidLeagueError extends Error {
  readonly issues: readonly LeagueValidationIssue[]

  constructor(issues: readonly LeagueValidationIssue[]) {
    super(`League validation failed with ${issues.length} issue(s)`)
    this.name = 'InvalidLeagueError'
    this.issues = issues
  }
}

/**
 * Checks semantic invariants on an already typed League. This is not a parser
 * for unknown save data; persistence must perform structural validation first.
 */
export function validateLeague(league: League): readonly LeagueValidationIssue[] {
  const issues: LeagueValidationIssue[] = []
  const allIds = new Set<string>()
  const teamIdCounts = new Map<string, number>()
  const rosterCounts = new Map<string, number>()
  const jerseyNumbersByTeam = new Map<string, Set<number>>()
  const teamIdentities = new Set<string>()
  const abbreviations = new Set<string>()
  const palettes = new Set<string>()
  const playerNames = new Set<string>()

  if (!isLeagueId(league.id)) {
    addIssue(issues, 'league.id.invalid', '$.id', 'League ID is invalid')
  } else {
    registerId(league.id, '$.id', issues, allIds)
  }

  if (league.generatorVersion !== 1) {
    addIssue(
      issues,
      'league.generator_version.invalid',
      '$.generatorVersion',
      'Generator version must equal 1',
    )
  }

  if (!isSeedFingerprint(league.seedFingerprint)) {
    addIssue(
      issues,
      'league.seed_fingerprint.invalid',
      '$.seedFingerprint',
      'Seed fingerprint must be eight lowercase hexadecimal characters',
    )
  }

  if (league.teams.length !== LEAGUE_TEAM_COUNT) {
    addIssue(
      issues,
      'league.team_count.invalid',
      '$.teams',
      `League must contain exactly ${LEAGUE_TEAM_COUNT} teams`,
    )
  }

  for (let index = 0; index < league.teams.length; index += 1) {
    const team = league.teams[index]
    const path = `$.teams[${index}]`

    if (!isTeamId(team.id)) {
      addIssue(issues, 'team.id.invalid', `${path}.id`, 'Team ID is invalid')
    } else {
      registerId(team.id, `${path}.id`, issues, allIds)
      teamIdCounts.set(team.id, (teamIdCounts.get(team.id) ?? 0) + 1)
      rosterCounts.set(team.id, rosterCounts.get(team.id) ?? 0)
    }

    if (!isNonEmptyString(team.city)) {
      addIssue(issues, 'team.city.invalid', `${path}.city`, 'City must not be empty')
    }
    if (!isNonEmptyString(team.nickname)) {
      addIssue(
        issues,
        'team.nickname.invalid',
        `${path}.nickname`,
        'Nickname must not be empty',
      )
    }
    if (!isAbbreviation(team.abbreviation)) {
      addIssue(
        issues,
        'team.abbreviation.invalid',
        `${path}.abbreviation`,
        'Abbreviation must contain two to four uppercase ASCII letters',
      )
    }

    registerUniqueValue(
      `${team.city}\u0000${team.nickname}`,
      `${path}.nickname`,
      'team.identity.duplicate',
      'Team city and nickname combination must be unique',
      teamIdentities,
      issues,
    )
    registerUniqueValue(
      team.abbreviation,
      `${path}.abbreviation`,
      'team.abbreviation.duplicate',
      'Team abbreviation must be unique',
      abbreviations,
      issues,
    )

    validateColors(team.colors, `${path}.colors`, issues)
    registerUniqueValue(
      paletteSignature(team.colors),
      `${path}.colors`,
      'team.colors.duplicate',
      'Team color palette must be unique',
      palettes,
      issues,
    )

    if (team.mark.kind !== 'initials' || team.mark.text !== team.abbreviation) {
      addIssue(
        issues,
        'team.mark.invalid',
        `${path}.mark`,
        'Team mark must contain the saved abbreviation as initials',
      )
    }
  }

  if (league.players.length !== LEAGUE_PLAYER_COUNT) {
    addIssue(
      issues,
      'league.player_count.invalid',
      '$.players',
      `League must contain exactly ${LEAGUE_PLAYER_COUNT} players`,
    )
  }

  for (let index = 0; index < league.players.length; index += 1) {
    const player = league.players[index]
    const path = `$.players[${index}]`

    if (!isPlayerId(player.id)) {
      addIssue(issues, 'player.id.invalid', `${path}.id`, 'Player ID is invalid')
    } else {
      registerId(player.id, `${path}.id`, issues, allIds)
    }

    if (!isTeamId(player.teamId)) {
      addIssue(
        issues,
        'player.team_id.invalid',
        `${path}.teamId`,
        'Player team ID is invalid',
      )
    } else if (teamIdCounts.get(player.teamId) !== 1) {
      addIssue(
        issues,
        'player.team_ownership.invalid',
        `${path}.teamId`,
        'Player must reference exactly one league team',
      )
    } else {
      rosterCounts.set(player.teamId, (rosterCounts.get(player.teamId) ?? 0) + 1)
    }

    if (!isNonEmptyString(player.firstName)) {
      addIssue(
        issues,
        'player.first_name.invalid',
        `${path}.firstName`,
        'First name must not be empty',
      )
    }
    if (!isNonEmptyString(player.lastName)) {
      addIssue(
        issues,
        'player.last_name.invalid',
        `${path}.lastName`,
        'Last name must not be empty',
      )
    }

    registerUniqueValue(
      `${player.firstName}\u0000${player.lastName}`,
      `${path}.firstName`,
      'player.name.duplicate',
      'Generated player full name must be unique',
      playerNames,
      issues,
    )

    if (!isIntegerInRange(player.age, PLAYER_AGE_MIN, PLAYER_AGE_MAX)) {
      addIssue(
        issues,
        'player.age.invalid',
        `${path}.age`,
        `Age must be an integer from ${PLAYER_AGE_MIN} through ${PLAYER_AGE_MAX}`,
      )
    }

    if (
      !isIntegerInRange(
        player.jerseyNumber,
        JERSEY_NUMBER_MIN,
        JERSEY_NUMBER_MAX,
      )
    ) {
      addIssue(
        issues,
        'player.jersey_number.invalid',
        `${path}.jerseyNumber`,
        `Jersey number must be an integer from ${JERSEY_NUMBER_MIN} through ${JERSEY_NUMBER_MAX}`,
      )
    } else if (isTeamId(player.teamId)) {
      const jerseyNumbers = jerseyNumbersByTeam.get(player.teamId) ?? new Set()
      if (jerseyNumbers.has(player.jerseyNumber)) {
        addIssue(
          issues,
          'player.jersey_number.duplicate',
          `${path}.jerseyNumber`,
          'Jersey number must be unique within a team',
        )
      }
      jerseyNumbers.add(player.jerseyNumber)
      jerseyNumbersByTeam.set(player.teamId, jerseyNumbers)
    }

    if (!isPosition(player.primaryPosition)) {
      addIssue(
        issues,
        'player.primary_position.invalid',
        `${path}.primaryPosition`,
        'Primary position is invalid',
      )
    }
    if (
      player.secondaryPosition !== null &&
      !isPosition(player.secondaryPosition)
    ) {
      addIssue(
        issues,
        'player.secondary_position.invalid',
        `${path}.secondaryPosition`,
        'Secondary position is invalid',
      )
    }

    if (player.ratingGenerationVersion !== RATING_GENERATION_VERSION) {
      addIssue(
        issues,
        'player.rating_generation_version.invalid',
        `${path}.ratingGenerationVersion`,
        `Rating generation version must equal ${RATING_GENERATION_VERSION}`,
      )
    }

    validateRatings(player.ratings, `${path}.ratings`, issues)

    validateTendencies(player.tendencies, `${path}.tendencies`, issues)
  }

  for (const [teamId, teamCount] of teamIdCounts) {
    if (teamCount === 1 && rosterCounts.get(teamId) !== PLAYERS_PER_TEAM) {
      addIssue(
        issues,
        'team.roster_size.invalid',
        '$.players',
        `Team ${teamId} must own exactly ${PLAYERS_PER_TEAM} players`,
      )
    }
  }

  return issues
}

export function assertValidLeague(league: League): void {
  const issues = validateLeague(league)
  if (issues.length > 0) {
    throw new InvalidLeagueError(issues)
  }
}

function validateColors(
  colors: TeamColors,
  path: string,
  issues: LeagueValidationIssue[],
): void {
  for (const key of ['primary', 'secondary', 'accent'] as const) {
    const value = colors[key]
    if (!isHexColor(value)) {
      addIssue(
        issues,
        'team.color.invalid',
        `${path}.${key}`,
        'Team colors must be six-digit hexadecimal values',
      )
    }
  }
}

function validateTendencies(
  tendencies: PlayerTendencies,
  path: string,
  issues: LeagueValidationIssue[],
): void {
  if (!isIntegerInRange(tendencies.usage, 1, 100)) {
    addIssue(
      issues,
      'player.tendency.invalid',
      `${path}.usage`,
      'Usage tendency must be an integer from 1 through 100',
    )
  }

  const otherKeys = ['rim', 'midrange', 'threePoint', 'pass', 'drawFoul'] as const
  for (const key of otherKeys) {
    if (!isIntegerInRange(tendencies[key], 0, 100)) {
      addIssue(
        issues,
        'player.tendency.invalid',
        `${path}.${key}`,
        'Tendency must be an integer from 0 through 100',
      )
    }
  }

  if (tendencies.rim + tendencies.midrange + tendencies.threePoint <= 0) {
    addIssue(
      issues,
      'player.shot_tendencies.invalid',
      path,
      'At least one shot-zone tendency must be positive',
    )
  }
}

function validateRatings(
  ratings: unknown,
  path: string,
  issues: LeagueValidationIssue[],
): void {
  if (ratings === null || typeof ratings !== 'object' || Array.isArray(ratings)) {
    addIssue(
      issues,
      'player.ratings.invalid',
      path,
      'Player ratings must be an object',
    )
    return
  }

  const source = ratings as Record<string, unknown>

  for (const ratingKey of RATING_KEYS) {
    if (!Object.prototype.hasOwnProperty.call(source, ratingKey)) {
      addIssue(
        issues,
        'player.rating.missing',
        `${path}.${ratingKey}`,
        'Canonical player rating is missing',
      )
      continue
    }

    if (!isStoredRating(source[ratingKey])) {
      addIssue(
        issues,
        'player.rating.invalid',
        `${path}.${ratingKey}`,
        `Rating must be a finite integer from ${STORED_RATING_MIN} through ${STORED_RATING_MAX}`,
      )
    }
  }

  for (const key of Reflect.ownKeys(ratings)) {
    if (!isRatingKey(key)) {
      addIssue(
        issues,
        'player.rating.unexpected',
        typeof key === 'string' ? `${path}.${key}` : path,
        'Player ratings must not contain additional keys',
      )
    }
  }
}

function registerId(
  id: string,
  path: string,
  issues: LeagueValidationIssue[],
  allIds: Set<string>,
): void {
  if (allIds.has(id)) {
    addIssue(issues, 'id.duplicate', path, 'All league IDs must be unique')
  }
  allIds.add(id)
}

function registerUniqueValue(
  value: string,
  path: string,
  code: string,
  message: string,
  values: Set<string>,
  issues: LeagueValidationIssue[],
): void {
  if (values.has(value)) {
    addIssue(issues, code, path, message)
  }
  values.add(value)
}

function addIssue(
  issues: LeagueValidationIssue[],
  code: string,
  path: string,
  message: string,
): void {
  issues.push({ code, path, message })
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0
}

function isIntegerInRange(value: number, minimum: number, maximum: number): boolean {
  return Number.isInteger(value) && value >= minimum && value <= maximum
}

function isSeedFingerprint(value: unknown): value is string {
  return (
    typeof value === 'string' &&
    value.length === 8 &&
    !/[^0-9a-f]/.test(value)
  )
}

function isAbbreviation(value: unknown): value is string {
  return (
    typeof value === 'string' &&
    value.length >= 2 &&
    value.length <= 4 &&
    !/[^A-Z]/.test(value)
  )
}

function isHexColor(value: unknown): value is string {
  return (
    typeof value === 'string' &&
    value.length === 7 &&
    value.startsWith('#') &&
    !/[^0-9a-f]/i.test(value.slice(1))
  )
}

function paletteSignature(colors: TeamColors): string {
  return `${colors.primary}\u0000${colors.secondary}\u0000${colors.accent}`
}
