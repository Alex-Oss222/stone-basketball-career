import {
  isLeagueId,
  isScheduleId,
  isSeasonId,
  parseLeagueId,
  parseScheduleId,
  parseSeasonId,
} from './ids'
import type { LeagueId, ScheduleId, SeasonId } from './ids'
import {
  formatSeasonLabel,
  isLocalDate,
  parseLocalDate,
} from './localDate'
import type { LocalDate } from './localDate'
import { addIssue, isPositiveSafeInteger, isRecord } from './validationIssue'
import type { ValidationIssue } from './validationIssue'

export const SEASON_PHASES = [
  'offseason',
  'training_camp',
  'preseason',
  'regular_season',
  'postseason',
  'complete',
] as const
export type SeasonPhase = (typeof SEASON_PHASES)[number]

export const SEASON_STATUSES = [
  'planned',
  'schedule_ready',
  'in_progress',
  'completed',
] as const
export type SeasonStatus = (typeof SEASON_STATUSES)[number]

export interface Season {
  readonly id: SeasonId
  readonly leagueId: LeagueId
  readonly seasonNumber: number
  readonly startingYear: number
  readonly endingYear: number
  readonly displayLabel: string
  readonly rulesVersion: number
  readonly currentDate: LocalDate
  readonly currentPhase: SeasonPhase
  readonly scheduleId: ScheduleId
  readonly status: SeasonStatus
}

export type CreateSeasonInput = Omit<Season, 'displayLabel'>

export type SeasonValidationIssue = ValidationIssue

export class InvalidSeasonError extends Error {
  readonly issues: readonly SeasonValidationIssue[]

  constructor(issues: readonly SeasonValidationIssue[]) {
    super(`Season validation failed with ${issues.length} issue(s)`)
    this.name = 'InvalidSeasonError'
    this.issues = issues
  }
}

export function isSeasonPhase(value: unknown): value is SeasonPhase {
  return SEASON_PHASES.some((phase) => phase === value)
}

export function isSeasonStatus(value: unknown): value is SeasonStatus {
  return SEASON_STATUSES.some((status) => status === value)
}

export function createSeason(input: CreateSeasonInput): Season {
  return parseSeason({
    ...input,
    displayLabel: formatSeasonLabel(input.startingYear, input.endingYear),
  })
}

export function validateSeason(value: unknown): readonly SeasonValidationIssue[] {
  const issues: SeasonValidationIssue[] = []
  if (!isRecord(value)) {
    addIssue(issues, 'season.invalid', '$', 'Season must be an object')
    return issues
  }

  if (!isSeasonId(value.id)) {
    addIssue(issues, 'season.id.invalid', '$.id', 'Season ID is invalid')
  }
  if (!isLeagueId(value.leagueId)) {
    addIssue(issues, 'season.league_id.invalid', '$.leagueId', 'League ID is invalid')
  }
  if (!isPositiveSafeInteger(value.seasonNumber)) {
    addIssue(
      issues,
      'season.number.invalid',
      '$.seasonNumber',
      'Season number must be a positive safe integer',
    )
  }

  const validStartingYear = isCalendarYear(value.startingYear)
  const validEndingYear = isCalendarYear(value.endingYear)
  if (!validStartingYear) {
    addIssue(
      issues,
      'season.starting_year.invalid',
      '$.startingYear',
      'Starting year must be an integer from 0 through 9999',
    )
  }
  if (!validEndingYear) {
    addIssue(
      issues,
      'season.ending_year.invalid',
      '$.endingYear',
      'Ending year must be an integer from 0 through 9999',
    )
  }
  if (
    validStartingYear &&
    validEndingYear &&
    (value.endingYear as number) <= (value.startingYear as number)
  ) {
    addIssue(
      issues,
      'season.year_order.invalid',
      '$.endingYear',
      'Ending year must be later than starting year',
    )
  }

  if (typeof value.displayLabel !== 'string') {
    addIssue(
      issues,
      'season.display_label.invalid',
      '$.displayLabel',
      'Season display label must be a string',
    )
  } else if (
    validStartingYear &&
    validEndingYear &&
    (value.endingYear as number) > (value.startingYear as number) &&
    value.displayLabel !==
      formatSeasonLabel(value.startingYear as number, value.endingYear as number)
  ) {
    addIssue(
      issues,
      'season.display_label.mismatch',
      '$.displayLabel',
      'Season display label must match the stored starting and ending years',
    )
  }

  if (!isPositiveSafeInteger(value.rulesVersion)) {
    addIssue(
      issues,
      'season.rules_version.invalid',
      '$.rulesVersion',
      'Rules version must be a positive safe integer',
    )
  }
  if (!isLocalDate(value.currentDate)) {
    addIssue(
      issues,
      'season.current_date.invalid',
      '$.currentDate',
      'Current date must be a valid LocalDate',
    )
  }
  if (!isSeasonPhase(value.currentPhase)) {
    addIssue(
      issues,
      'season.phase.invalid',
      '$.currentPhase',
      'Current phase is invalid',
    )
  }
  if (!isScheduleId(value.scheduleId)) {
    addIssue(
      issues,
      'season.schedule_id.invalid',
      '$.scheduleId',
      'Schedule ID is invalid',
    )
  }
  if (!isSeasonStatus(value.status)) {
    addIssue(issues, 'season.status.invalid', '$.status', 'Season status is invalid')
  }

  return issues
}

export function parseSeason(value: unknown): Season {
  const issues = validateSeason(value)
  if (issues.length > 0) {
    throw new InvalidSeasonError(issues)
  }

  const source = value as Record<string, unknown>
  return Object.freeze({
    id: parseSeasonId(source.id),
    leagueId: parseLeagueId(source.leagueId),
    seasonNumber: source.seasonNumber as number,
    startingYear: source.startingYear as number,
    endingYear: source.endingYear as number,
    displayLabel: source.displayLabel as string,
    rulesVersion: source.rulesVersion as number,
    currentDate: parseLocalDate(source.currentDate),
    currentPhase: source.currentPhase as SeasonPhase,
    scheduleId: parseScheduleId(source.scheduleId),
    status: source.status as SeasonStatus,
  })
}

function isCalendarYear(value: unknown): value is number {
  return Number.isSafeInteger(value) && (value as number) >= 0 && (value as number) <= 9999
}
