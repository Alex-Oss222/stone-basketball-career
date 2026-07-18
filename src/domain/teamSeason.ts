import {
  isSeasonId,
  isTeamId,
  isTeamSeasonId,
  parseSeasonId,
  parseTeamId,
  parseTeamSeasonId,
} from './ids'
import type { SeasonId, TeamId, TeamSeasonId } from './ids'
import {
  compareLocalDates,
  isLocalDate,
  parseLocalDate,
} from './localDate'
import type { LocalDate } from './localDate'
import {
  addIssue,
  isPositiveSafeInteger,
  isRecord,
  validateNullableLocalDate,
} from './validationIssue'
import type { ValidationIssue } from './validationIssue'

export const TEAM_SEASON_VERSION = 1 as const

export const TEAM_COMPETITIVE_STATUSES = [
  'active',
  'eliminated',
  'season_complete',
] as const
export type TeamCompetitiveStatus =
  (typeof TEAM_COMPETITIVE_STATUSES)[number]

export interface TeamSeason {
  readonly id: TeamSeasonId
  readonly version: typeof TEAM_SEASON_VERSION
  readonly seasonId: SeasonId
  readonly teamId: TeamId
  readonly competitiveStatus: TeamCompetitiveStatus
  readonly eliminationDate: LocalDate | null
  readonly teamOffseasonStartDate: LocalDate | null
  readonly postseasonSeed: number | null
}

export type TeamSeasonValidationIssue = ValidationIssue

export class InvalidTeamSeasonError extends Error {
  readonly issues: readonly TeamSeasonValidationIssue[]

  constructor(issues: readonly TeamSeasonValidationIssue[]) {
    super(`Team-season validation failed with ${issues.length} issue(s)`)
    this.name = 'InvalidTeamSeasonError'
    this.issues = issues
  }
}

export function isTeamCompetitiveStatus(
  value: unknown,
): value is TeamCompetitiveStatus {
  return TEAM_COMPETITIVE_STATUSES.some((status) => status === value)
}

export function createTeamSeason(value: TeamSeason): TeamSeason {
  return parseTeamSeason(value)
}

export function validateTeamSeason(
  value: unknown,
): readonly TeamSeasonValidationIssue[] {
  const issues: TeamSeasonValidationIssue[] = []
  if (!isRecord(value)) {
    addIssue(issues, 'team_season.invalid', '$', 'Team season must be an object')
    return issues
  }

  if (!isTeamSeasonId(value.id)) {
    addIssue(
      issues,
      'team_season.id.invalid',
      '$.id',
      'Team-season ID is invalid',
    )
  }
  if (value.version !== TEAM_SEASON_VERSION) {
    addIssue(
      issues,
      'team_season.version.invalid',
      '$.version',
      `Team-season version must equal ${TEAM_SEASON_VERSION}`,
    )
  }
  if (!isSeasonId(value.seasonId)) {
    addIssue(
      issues,
      'team_season.season_id.invalid',
      '$.seasonId',
      'Team-season SeasonId is invalid',
    )
  }
  if (!isTeamId(value.teamId)) {
    addIssue(
      issues,
      'team_season.team_id.invalid',
      '$.teamId',
      'Team-season TeamId is invalid',
    )
  }
  if (!isTeamCompetitiveStatus(value.competitiveStatus)) {
    addIssue(
      issues,
      'team_season.status.invalid',
      '$.competitiveStatus',
      'Competitive status is invalid',
    )
  }

  validateNullableDate(value.eliminationDate, '$.eliminationDate', issues)
  validateNullableDate(
    value.teamOffseasonStartDate,
    '$.teamOffseasonStartDate',
    issues,
  )

  if (
    value.postseasonSeed !== null &&
    !isPositiveSafeInteger(value.postseasonSeed)
  ) {
    addIssue(
      issues,
      'team_season.postseason_seed.invalid',
      '$.postseasonSeed',
      'Postseason seed must be a positive safe integer or null',
    )
  }

  if (
    value.competitiveStatus === 'active' &&
    (value.eliminationDate !== null || value.teamOffseasonStartDate !== null)
  ) {
    addIssue(
      issues,
      'team_season.active_dates.invalid',
      '$.competitiveStatus',
      'An active team cannot have elimination or offseason-start dates',
    )
  }

  if (
    isLocalDate(value.eliminationDate) &&
    isLocalDate(value.teamOffseasonStartDate) &&
    compareLocalDates(value.teamOffseasonStartDate, value.eliminationDate) < 0
  ) {
    addIssue(
      issues,
      'team_season.offseason_date.invalid',
      '$.teamOffseasonStartDate',
      'Team offseason cannot start before the team elimination date',
    )
  }

  return issues
}

export function parseTeamSeason(value: unknown): TeamSeason {
  const issues = validateTeamSeason(value)
  if (issues.length > 0) {
    throw new InvalidTeamSeasonError(issues)
  }

  const source = value as Record<string, unknown>
  return Object.freeze({
    id: parseTeamSeasonId(source.id),
    version: TEAM_SEASON_VERSION,
    seasonId: parseSeasonId(source.seasonId),
    teamId: parseTeamId(source.teamId),
    competitiveStatus: source.competitiveStatus as TeamCompetitiveStatus,
    eliminationDate:
      source.eliminationDate === null
        ? null
        : parseLocalDate(source.eliminationDate),
    teamOffseasonStartDate:
      source.teamOffseasonStartDate === null
        ? null
        : parseLocalDate(source.teamOffseasonStartDate),
    postseasonSeed: source.postseasonSeed as number | null,
  })
}

function validateNullableDate(
  value: unknown,
  path: string,
  issues: TeamSeasonValidationIssue[],
): void {
  validateNullableLocalDate(
    value,
    path,
    issues,
    'team_season.date.invalid',
    'Team-season date must be a valid LocalDate or null',
  )
}
