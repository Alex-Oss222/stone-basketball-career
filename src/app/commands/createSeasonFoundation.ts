import {
  isLeagueId,
  isSeasonId,
  isTeamId,
  parseCalendarEventId,
  parseSeasonCalendarId,
  parseSeasonId,
  parseTeamSeasonId,
} from '../../domain/ids'
import type {
  CalendarEventId,
  GameDayId,
  GameId,
  SeasonCalendarId,
  SeasonId,
  TeamId,
  TeamSeasonId,
} from '../../domain/ids'
import type { League, Team } from '../../domain/league'
import {
  assertValidLeague,
  validateLeague,
} from '../../domain/leagueValidation'
import {
  compareLocalDates,
  formatSeasonLabel,
  getCalendarYear,
  isLocalDate,
  parseLocalDate,
} from '../../domain/localDate'
import type { LocalDate } from '../../domain/localDate'
import {
  MILESTONE_1_REGULAR_SEASON_RULE_SET,
} from '../../domain/schedule'
import type { LeagueSchedule } from '../../domain/schedule'
import { validateLeagueSchedule } from '../../domain/scheduleValidation'
import {
  CALENDAR_EVENT_VERSION,
  SEASON_CALENDAR_VERSION,
  createCalendarEvent,
  createSeasonCalendar,
  validateSeasonCalendar,
} from '../../domain/seasonCalendar'
import type {
  CalendarEvent,
  CalendarEventKind,
  SeasonCalendar,
} from '../../domain/seasonCalendar'
import { createSeason, validateSeason } from '../../domain/season'
import type { Season } from '../../domain/season'
import {
  TEAM_SEASON_VERSION,
  createTeamSeason,
  validateTeamSeason,
} from '../../domain/teamSeason'
import type { TeamSeason } from '../../domain/teamSeason'
import {
  SCHEDULE_GENERATION_VERSION,
  deriveStableScheduleId,
  generateRegularSeasonSchedule,
} from '../../generation/generateSchedule'
import { deriveSeed, normalizeSeed } from '../../random/seed'

export const SEASON_FOUNDATION_IDENTITY_VERSION = 1 as const

const IDENTITY_NAMESPACE =
  `season_foundation_identity/v${SEASON_FOUNDATION_IDENTITY_VERSION}` as const
const ID_FINGERPRINT_LENGTH = 24
const SEASON_NUMBER = 1

const FOUNDATION_CALENDAR_EVENT_KINDS = [
  'regular_season_opening',
  'regular_season_conclusion',
] as const satisfies readonly CalendarEventKind[]

type FoundationCalendarEventKind =
  (typeof FOUNDATION_CALENDAR_EVENT_KINDS)[number]

export interface CreateSeasonFoundationInput {
  readonly league: League
  readonly startingYear: number
  readonly regularSeasonStartDate: LocalDate
  readonly calendarDaySpacing: number
  readonly scheduleSeed: string
}

export type SeasonFoundationConfigurationInput = Omit<
  CreateSeasonFoundationInput,
  'league'
>

export interface SeasonFoundationConfiguration {
  readonly startingYear: number
  readonly regularSeasonStartDate: LocalDate
  readonly calendarDaySpacing: number
  readonly scheduleSeed: string
}

export interface SeasonFoundation {
  readonly season: Season
  readonly calendar: SeasonCalendar
  readonly teamSeasons: readonly TeamSeason[]
  readonly schedule: LeagueSchedule
}

export interface ValidateSeasonFoundationInput
  extends CreateSeasonFoundationInput {
  readonly foundation: SeasonFoundation
}

export type SeasonFoundationValidationSource =
  | 'league'
  | 'season'
  | 'calendar'
  | 'team_season'
  | 'schedule'
  | 'foundation'

export interface SeasonFoundationValidationIssue {
  readonly source: SeasonFoundationValidationSource
  readonly code: string
  readonly path: string
  readonly message: string
  readonly teamId?: TeamId
  readonly gameId?: GameId
  readonly gameDayId?: GameDayId
  readonly date?: LocalDate
}

export class InvalidSeasonFoundationError extends Error {
  readonly issues: readonly SeasonFoundationValidationIssue[]

  constructor(issues: readonly SeasonFoundationValidationIssue[]) {
    super(`Season foundation validation failed with ${issues.length} issue(s)`)
    this.name = 'InvalidSeasonFoundationError'
    this.issues = Object.freeze([...issues])
  }
}

/**
 * Coordinates existing pure domain constructors into one Milestone 1 regular
 * season package. No supplied league object or nested collection is changed.
 */
export function createSeasonFoundation(
  input: CreateSeasonFoundationInput,
): SeasonFoundation {
  const configuration = parseSeasonFoundationConfiguration(input)
  assertValidLeague(input.league)

  const seasonId = deriveSeasonFoundationSeasonId(
    input.league.id,
    configuration.startingYear,
  )
  const canonicalTeams = getCanonicalLeagueTeams(input.league)
  const schedule = generateRegularSeasonSchedule({
    leagueId: input.league.id,
    seasonId,
    teams: canonicalTeams,
    scheduleSeed: configuration.scheduleSeed,
    regularSeasonStartDate: configuration.regularSeasonStartDate,
    calendarDaySpacing: configuration.calendarDaySpacing,
    ruleSet: MILESTONE_1_REGULAR_SEASON_RULE_SET,
  })
  const latestGameDate = getLatestGeneratedGameDate(schedule)
  const endingYear = configuration.startingYear + 1

  const season = createSeason({
    id: seasonId,
    leagueId: input.league.id,
    seasonNumber: SEASON_NUMBER,
    startingYear: configuration.startingYear,
    endingYear,
    rulesVersion: MILESTONE_1_REGULAR_SEASON_RULE_SET.version,
    currentDate: configuration.regularSeasonStartDate,
    currentPhase: 'regular_season',
    scheduleId: schedule.id,
    status: 'schedule_ready',
  })
  const teamSeasons = Object.freeze(
    canonicalTeams.map(({ id: teamId }) =>
      createTeamSeason({
        id: deriveSeasonFoundationTeamSeasonId(seasonId, teamId),
        version: TEAM_SEASON_VERSION,
        seasonId,
        teamId,
        competitiveStatus: 'active',
        eliminationDate: null,
        teamOffseasonStartDate: null,
        postseasonSeed: null,
      }),
    ),
  )
  const calendar = createFoundationCalendar(
    seasonId,
    configuration.regularSeasonStartDate,
    latestGameDate,
  )
  const foundation: SeasonFoundation = Object.freeze({
    season,
    calendar,
    teamSeasons,
    schedule,
  })

  assertValidSeasonFoundation({
    ...input,
    ...configuration,
    foundation,
  })
  return foundation
}

/** Season identity depends only on league identity, starting year, and formula version. */
export function deriveSeasonFoundationSeasonId(
  leagueId: League['id'],
  startingYear: number,
): SeasonId {
  if (!isLeagueId(leagueId)) {
    throw new TypeError('Season identity requires a valid LeagueId')
  }
  const endingYear = startingYear + 1
  formatSeasonLabel(startingYear, endingYear)
  return parseSeasonId(
    `season_${deriveIdentityFingerprint(
      leagueId,
      `${IDENTITY_NAMESPACE}/season/starting_year_${startingYear}`,
    )}`,
  )
}

/** Calendar identity deliberately excludes schedule seed and event dates. */
export function deriveSeasonFoundationCalendarId(
  seasonId: SeasonId,
): SeasonCalendarId {
  if (!isSeasonId(seasonId)) {
    throw new TypeError('Season calendar identity requires a valid SeasonId')
  }
  return parseSeasonCalendarId(
    `season_calendar_${deriveIdentityFingerprint(
      seasonId,
      `${IDENTITY_NAMESPACE}/calendar`,
    )}`,
  )
}

/** Team-season identity deliberately excludes schedule seed and lifecycle state. */
export function deriveSeasonFoundationTeamSeasonId(
  seasonId: SeasonId,
  teamId: TeamId,
): TeamSeasonId {
  if (!isSeasonId(seasonId) || !isTeamId(teamId)) {
    throw new TypeError(
      'Team-season identity requires valid SeasonId and TeamId values',
    )
  }
  return parseTeamSeasonId(
    `team_season_${deriveIdentityFingerprint(
      seasonId,
      `${IDENTITY_NAMESPACE}/team_season/${teamId.length}:${teamId}`,
    )}`,
  )
}

/** Event identity uses semantic kind, never title, array position, or date. */
export function deriveSeasonFoundationCalendarEventId(
  seasonId: SeasonId,
  kind: FoundationCalendarEventKind,
): CalendarEventId {
  if (!isSeasonId(seasonId)) {
    throw new TypeError('Calendar-event identity requires a valid SeasonId')
  }
  if (!FOUNDATION_CALENDAR_EVENT_KINDS.includes(kind)) {
    throw new TypeError('Calendar-event kind is not part of this foundation')
  }
  return parseCalendarEventId(
    `calendar_event_${deriveIdentityFingerprint(
      seasonId,
      `${IDENTITY_NAMESPACE}/calendar_event/${kind}`,
    )}`,
  )
}

/**
 * Validates a pristine creation-time package against its exact deterministic
 * inputs. It is not a validator for later published, postponed, or completed
 * season state.
 */
export function validateSeasonFoundation(
  input: ValidateSeasonFoundationInput,
): readonly SeasonFoundationValidationIssue[] {
  const issues: SeasonFoundationValidationIssue[] = []
  try {
    collectSeasonFoundationValidationIssues(input, issues)
  } catch (error) {
    addIssue(
      issues,
      'foundation',
      'foundation.structure.invalid',
      '$',
      errorMessage(error),
    )
  }
  return Object.freeze(issues)
}

function collectSeasonFoundationValidationIssues(
  input: ValidateSeasonFoundationInput,
  issues: SeasonFoundationValidationIssue[],
): void {
  const { foundation, league } = input

  try {
    parseSeasonFoundationConfiguration(input)
  } catch (error) {
    addIssue(
      issues,
      'foundation',
      'foundation.configuration.invalid',
      '$',
      errorMessage(error),
    )
  }

  adaptEntityIssues(issues, 'league', '$.league', validateLeague(league))
  adaptEntityIssues(
    issues,
    'season',
    '$.season',
    validateSeason(foundation.season),
  )
  adaptEntityIssues(
    issues,
    'calendar',
    '$.calendar',
    validateSeasonCalendar(foundation.calendar),
  )
  foundation.teamSeasons.forEach((teamSeason, index) => {
    adaptEntityIssues(
      issues,
      'team_season',
      `$.teamSeasons[${index}]`,
      validateTeamSeason(teamSeason),
    )
  })

  const scheduleReport = validateLeagueSchedule({
    schedule: foundation.schedule,
    leagueId: league.id,
    seasonId: foundation.season.id,
    teams: getCanonicalLeagueTeams(league),
    ruleSet: MILESTONE_1_REGULAR_SEASON_RULE_SET,
    regularSeasonStartDate: input.regularSeasonStartDate,
    calendarDaySpacing: input.calendarDaySpacing,
  })
  for (const violation of scheduleReport.hardViolations) {
    addIssue(
      issues,
      'schedule',
      violation.code,
      '$.schedule',
      violation.message,
      {
        ...(violation.teamId === undefined
          ? {}
          : { teamId: violation.teamId }),
        ...(violation.date === undefined ? {} : { date: violation.date }),
        ...(violation.gameId === undefined
          ? {}
          : { gameId: violation.gameId }),
        ...(violation.gameDayId === undefined
          ? {}
          : { gameDayId: violation.gameDayId }),
      },
    )
  }

  validateExpectedSeasonIdentity(input, issues)
  validateSeasonReferences(input, issues)
  validateTeamSeasonCoverage(input, issues)
  validateScheduleIdentity(input, issues)
  validateCanonicalScheduleOutput(input, issues)
  validateCalendarContract(input, issues)
}

export function assertValidSeasonFoundation(
  input: ValidateSeasonFoundationInput,
): void {
  const issues = validateSeasonFoundation(input)
  if (issues.length > 0) {
    throw new InvalidSeasonFoundationError(issues)
  }
}

/**
 * Parses the coordinator's authoritative primitive configuration without
 * creating a league, schedule, or season. Persistence migration reuses this
 * boundary rather than restating its normalization and range rules.
 */
export function parseSeasonFoundationConfiguration(
  input: SeasonFoundationConfigurationInput,
): SeasonFoundationConfiguration {
  const endingYear = input.startingYear + 1
  formatSeasonLabel(input.startingYear, endingYear)
  const regularSeasonStartDate = parseLocalDate(
    input.regularSeasonStartDate,
  )
  if (getCalendarYear(regularSeasonStartDate) !== input.startingYear) {
    throw new RangeError(
      'Regular-season start date must fall in the supplied starting year',
    )
  }
  if (
    !Number.isSafeInteger(input.calendarDaySpacing) ||
    input.calendarDaySpacing <= 0
  ) {
    throw new RangeError(
      'Calendar-day spacing must be a positive safe integer',
    )
  }

  const scheduleSeed = normalizeSeed(input.scheduleSeed)
  if (scheduleSeed !== input.scheduleSeed) {
    throw new RangeError(
      'Schedule seed must already be canonical, trimmed, and NFC-normalized',
    )
  }

  return {
    startingYear: input.startingYear,
    regularSeasonStartDate,
    calendarDaySpacing: input.calendarDaySpacing,
    scheduleSeed,
  }
}

function getCanonicalLeagueTeams(league: League): readonly Team[] {
  return [...league.teams].sort((left, right) =>
    left.id < right.id ? -1 : left.id > right.id ? 1 : 0,
  )
}

function createFoundationCalendar(
  seasonId: SeasonId,
  openingDate: LocalDate,
  conclusionDate: LocalDate,
): SeasonCalendar {
  const events = [
    createBoundaryEvent(
      seasonId,
      'regular_season_opening',
      'Regular-season opening',
      openingDate,
    ),
    createBoundaryEvent(
      seasonId,
      'regular_season_conclusion',
      'Regular-season conclusion',
      conclusionDate,
    ),
  ].sort(compareCalendarEvents)

  return createSeasonCalendar({
    id: deriveSeasonFoundationCalendarId(seasonId),
    version: SEASON_CALENDAR_VERSION,
    seasonId,
    events,
  })
}

function createBoundaryEvent(
  seasonId: SeasonId,
  kind: FoundationCalendarEventKind,
  title: string,
  date: LocalDate,
): CalendarEvent {
  return createCalendarEvent({
    id: deriveSeasonFoundationCalendarEventId(seasonId, kind),
    version: CALENDAR_EVENT_VERSION,
    seasonId,
    kind,
    scope: 'league',
    title,
    originalScheduledDate: date,
    scheduledDate: date,
    actualDate: null,
    dateStatus: 'scheduled',
    completionStatus: 'pending',
  })
}

function getLatestGeneratedGameDate(schedule: LeagueSchedule): LocalDate {
  if (schedule.games.length === 0) {
    throw new InvalidSeasonFoundationError([
      Object.freeze({
        source: 'schedule',
        code: 'foundation.schedule.games.missing',
        path: '$.schedule.games',
        message: 'Generated schedule must contain regular-season games',
      }),
    ])
  }

  return schedule.games.reduce(
    (latest, game) =>
      compareLocalDates(game.originalScheduledDate, latest) > 0
        ? game.originalScheduledDate
        : latest,
    schedule.games[0].originalScheduledDate,
  )
}

function validateExpectedSeasonIdentity(
  input: ValidateSeasonFoundationInput,
  issues: SeasonFoundationValidationIssue[],
): void {
  let expectedSeasonId: SeasonId | null = null
  try {
    expectedSeasonId = deriveSeasonFoundationSeasonId(
      input.league.id,
      input.startingYear,
    )
  } catch (error) {
    addIssue(
      issues,
      'foundation',
      'foundation.season.identity_input.invalid',
      '$.season.id',
      errorMessage(error),
    )
  }

  if (
    expectedSeasonId !== null &&
    input.foundation.season.id !== expectedSeasonId
  ) {
    addIssue(
      issues,
      'foundation',
      'foundation.season.id_mismatch',
      '$.season.id',
      'SeasonId does not match league identity and starting year',
    )
  }

  const expectedEndingYear = input.startingYear + 1
  const season = input.foundation.season
  if (
    season.seasonNumber !== SEASON_NUMBER ||
    season.startingYear !== input.startingYear ||
    season.endingYear !== expectedEndingYear ||
    season.currentDate !== input.regularSeasonStartDate ||
    season.currentPhase !== 'regular_season' ||
    season.status !== 'schedule_ready' ||
    season.rulesVersion !== MILESTONE_1_REGULAR_SEASON_RULE_SET.version
  ) {
    addIssue(
      issues,
      'foundation',
      'foundation.season.configuration_mismatch',
      '$.season',
      'Season lifecycle or year configuration does not match creation inputs',
    )
  }
}

function validateSeasonReferences(
  input: ValidateSeasonFoundationInput,
  issues: SeasonFoundationValidationIssue[],
): void {
  const { foundation, league } = input
  const seasonId = foundation.season.id

  if (foundation.season.leagueId !== league.id) {
    addIssue(
      issues,
      'foundation',
      'foundation.season.league_id_mismatch',
      '$.season.leagueId',
      'Season must reference the supplied league',
    )
  }
  if (foundation.schedule.leagueId !== league.id) {
    addIssue(
      issues,
      'foundation',
      'foundation.schedule.league_id_mismatch',
      '$.schedule.leagueId',
      'Schedule must reference the supplied league',
    )
  }
  if (foundation.season.scheduleId !== foundation.schedule.id) {
    addIssue(
      issues,
      'foundation',
      'foundation.season.schedule_id_mismatch',
      '$.season.scheduleId',
      'Season ScheduleId must match the generated schedule',
    )
  }
  if (
    foundation.schedule.seasonId !== seasonId ||
    foundation.calendar.seasonId !== seasonId
  ) {
    addIssue(
      issues,
      'foundation',
      'foundation.season_reference.mismatch',
      '$',
      'Schedule and calendar must reference the generated season',
    )
  }

  for (const gameDay of foundation.schedule.gameDays) {
    if (gameDay.seasonId !== seasonId) {
      addIssue(
        issues,
        'foundation',
        'foundation.game_day.season_id_mismatch',
        '$.schedule.gameDays',
        'Every game day must reference the generated season',
      )
    }
  }
  for (const game of foundation.schedule.games) {
    if (game.seasonId !== seasonId) {
      addIssue(
        issues,
        'foundation',
        'foundation.game.season_id_mismatch',
        '$.schedule.games',
        'Every scheduled game must reference the generated season',
      )
    }
  }
  for (const event of foundation.calendar.events) {
    if (event.seasonId !== seasonId) {
      addIssue(
        issues,
        'foundation',
        'foundation.calendar_event.season_id_mismatch',
        '$.calendar.events',
        'Every calendar event must reference the generated season',
      )
    }
    if (
      event.scope === 'team' &&
      !league.teams.some(({ id }) => id === event.teamId)
    ) {
      addIssue(
        issues,
        'foundation',
        'foundation.calendar_event.team_id_unknown',
        '$.calendar.events',
        'Team-scoped calendar event references a foreign team',
        { teamId: event.teamId },
      )
    }
  }
}

function validateTeamSeasonCoverage(
  input: ValidateSeasonFoundationInput,
  issues: SeasonFoundationValidationIssue[],
): void {
  const expectedTeamIds = getCanonicalLeagueTeams(input.league).map(
    ({ id }) => id,
  )
  const expectedTeamIdSet = new Set(expectedTeamIds)
  const seenTeamIds = new Set<TeamId>()
  const teamSeasons = input.foundation.teamSeasons

  if (teamSeasons.length !== expectedTeamIds.length) {
    addIssue(
      issues,
      'foundation',
      'foundation.team_season.count_mismatch',
      '$.teamSeasons',
      'Team-season count must equal the supplied league team count',
    )
  }

  teamSeasons.forEach((teamSeason, index) => {
    if (teamSeason.seasonId !== input.foundation.season.id) {
      addIssue(
        issues,
        'foundation',
        'foundation.team_season.season_id_mismatch',
        `$.teamSeasons[${index}].seasonId`,
        'Team-season must reference the generated season',
      )
    }
    if (!expectedTeamIdSet.has(teamSeason.teamId)) {
      addIssue(
        issues,
        'foundation',
        'foundation.team_season.team_id_unknown',
        `$.teamSeasons[${index}].teamId`,
        'Team-season references a foreign team',
        { teamId: teamSeason.teamId },
      )
    }
    if (seenTeamIds.has(teamSeason.teamId)) {
      addIssue(
        issues,
        'foundation',
        'foundation.team_season.team_id_duplicate',
        `$.teamSeasons[${index}].teamId`,
        'Team-season team references must be unique',
        { teamId: teamSeason.teamId },
      )
    }
    seenTeamIds.add(teamSeason.teamId)

    if (expectedTeamIds[index] !== teamSeason.teamId) {
      addIssue(
        issues,
        'foundation',
        'foundation.team_season.order_mismatch',
        `$.teamSeasons[${index}].teamId`,
        'Team seasons must preserve canonical league-team order',
        { teamId: teamSeason.teamId },
      )
    }

    let expectedId: TeamSeasonId | null = null
    try {
      expectedId = deriveSeasonFoundationTeamSeasonId(
        input.foundation.season.id,
        teamSeason.teamId,
      )
    } catch {
      // The entity validator already reports malformed IDs.
    }
    if (expectedId !== null && teamSeason.id !== expectedId) {
      addIssue(
        issues,
        'foundation',
        'foundation.team_season.id_mismatch',
        `$.teamSeasons[${index}].id`,
        'Team-season ID does not match its SeasonId and TeamId',
        { teamId: teamSeason.teamId },
      )
    }
    if (
      teamSeason.competitiveStatus !== 'active' ||
      teamSeason.eliminationDate !== null ||
      teamSeason.teamOffseasonStartDate !== null ||
      teamSeason.postseasonSeed !== null
    ) {
      addIssue(
        issues,
        'foundation',
        'foundation.team_season.initial_state.invalid',
        `$.teamSeasons[${index}]`,
        'Initial team-season state must be active without postseason data',
      )
    }
  })

  for (const teamId of expectedTeamIds) {
    if (!seenTeamIds.has(teamId)) {
      addIssue(
        issues,
        'foundation',
        'foundation.team_season.team_id_missing',
        '$.teamSeasons',
        `League team ${teamId} is missing its team-season record`,
        { teamId },
      )
    }
  }
}

function validateScheduleIdentity(
  input: ValidateSeasonFoundationInput,
  issues: SeasonFoundationValidationIssue[],
): void {
  let expectedScheduleId: LeagueSchedule['id'] | null = null
  try {
    const canonicalSeed = normalizeSeed(input.scheduleSeed)
    if (canonicalSeed !== input.scheduleSeed) {
      throw new RangeError('Schedule seed is not canonical')
    }
    expectedScheduleId = deriveStableScheduleId({
      seasonId: input.foundation.season.id,
      teams: getCanonicalLeagueTeams(input.league),
      scheduleSeed: canonicalSeed,
      ruleSet: MILESTONE_1_REGULAR_SEASON_RULE_SET,
    })
  } catch (error) {
    addIssue(
      issues,
      'foundation',
      'foundation.schedule.identity_input.invalid',
      '$.schedule.id',
      errorMessage(error),
    )
  }

  if (
    expectedScheduleId !== null &&
    input.foundation.schedule.id !== expectedScheduleId
  ) {
    addIssue(
      issues,
      'foundation',
      'foundation.schedule.id_mismatch',
      '$.schedule.id',
      'ScheduleId does not match the generator identity inputs',
    )
  }
  if (
    input.foundation.schedule.scheduleSeed !== input.scheduleSeed ||
    input.foundation.schedule.calendarDaySpacing !== input.calendarDaySpacing ||
    input.foundation.schedule.ruleSetId !==
      MILESTONE_1_REGULAR_SEASON_RULE_SET.id ||
    input.foundation.schedule.generationVersion !== SCHEDULE_GENERATION_VERSION
  ) {
    addIssue(
      issues,
      'foundation',
      'foundation.schedule.configuration_mismatch',
      '$.schedule',
      'Schedule configuration does not match the creation inputs',
    )
  }
}

function validateCanonicalScheduleOutput(
  input: ValidateSeasonFoundationInput,
  issues: SeasonFoundationValidationIssue[],
): void {
  let expectedSchedule: LeagueSchedule
  try {
    const configuration = parseSeasonFoundationConfiguration(input)
    expectedSchedule = generateRegularSeasonSchedule({
      leagueId: input.league.id,
      seasonId: input.foundation.season.id,
      teams: getCanonicalLeagueTeams(input.league),
      scheduleSeed: configuration.scheduleSeed,
      regularSeasonStartDate: configuration.regularSeasonStartDate,
      calendarDaySpacing: configuration.calendarDaySpacing,
      ruleSet: MILESTONE_1_REGULAR_SEASON_RULE_SET,
    })
  } catch (error) {
    addIssue(
      issues,
      'foundation',
      'foundation.schedule.canonical_generation_failed',
      '$.schedule',
      errorMessage(error),
    )
    return
  }

  if (!areStructurallyEqual(input.foundation.schedule, expectedSchedule)) {
    addIssue(
      issues,
      'foundation',
      'foundation.schedule.not_canonical',
      '$.schedule',
      'Schedule must exactly match the existing deterministic generator output',
    )
  }
}

function validateCalendarContract(
  input: ValidateSeasonFoundationInput,
  issues: SeasonFoundationValidationIssue[],
): void {
  const { calendar, schedule, season } = input.foundation
  let expectedCalendarId: SeasonCalendarId | null = null
  try {
    expectedCalendarId = deriveSeasonFoundationCalendarId(season.id)
  } catch (error) {
    addIssue(
      issues,
      'foundation',
      'foundation.calendar.identity_input.invalid',
      '$.calendar.id',
      errorMessage(error),
    )
  }
  if (expectedCalendarId !== null && calendar.id !== expectedCalendarId) {
    addIssue(
      issues,
      'foundation',
      'foundation.calendar.id_mismatch',
      '$.calendar.id',
      'SeasonCalendarId does not match its SeasonId',
    )
  }

  let latestGameDate: LocalDate | null = null
  try {
    latestGameDate = getLatestGeneratedGameDate(schedule)
  } catch (error) {
    addIssue(
      issues,
      'foundation',
      'foundation.calendar.conclusion_date.unavailable',
      '$.calendar.events',
      errorMessage(error),
    )
  }

  const expectedKinds = new Set<CalendarEventKind>(
    FOUNDATION_CALENDAR_EVENT_KINDS,
  )
  const eventsByKind = new Map<CalendarEventKind, CalendarEvent[]>()
  for (const event of calendar.events) {
    const sameKind = eventsByKind.get(event.kind) ?? []
    sameKind.push(event)
    eventsByKind.set(event.kind, sameKind)

    if (!expectedKinds.has(event.kind)) {
      addIssue(
        issues,
        'foundation',
        'foundation.calendar.event_kind.unsupported',
        '$.calendar.events',
        `Calendar event ${event.kind} is not part of the regular-season foundation`,
      )
    }
    if (expectedKinds.has(event.kind) && isSeasonId(season.id)) {
      const expectedEventId = deriveSeasonFoundationCalendarEventId(
        season.id,
        event.kind as FoundationCalendarEventKind,
      )
      if (event.id !== expectedEventId) {
        addIssue(
          issues,
          'foundation',
          'foundation.calendar_event.id_mismatch',
          '$.calendar.events',
          'CalendarEventId does not match SeasonId and event kind',
        )
      }
    }
  }

  if (calendar.events.length !== FOUNDATION_CALENDAR_EVENT_KINDS.length) {
    addIssue(
      issues,
      'foundation',
      'foundation.calendar.event_count_mismatch',
      '$.calendar.events',
      'Calendar must contain exactly the two known regular-season boundaries',
    )
  }

  validateBoundaryEvent(
    eventsByKind.get('regular_season_opening') ?? [],
    input.regularSeasonStartDate,
    'regular_season_opening',
    issues,
  )
  if (latestGameDate !== null) {
    validateBoundaryEvent(
      eventsByKind.get('regular_season_conclusion') ?? [],
      latestGameDate,
      'regular_season_conclusion',
      issues,
    )
    if (getCalendarYear(latestGameDate) > season.endingYear) {
      addIssue(
        issues,
        'foundation',
        'foundation.schedule.conclusion_outside_season',
        '$.schedule.games',
        'Latest generated game date falls after the season ending year',
        { date: latestGameDate },
      )
    }
  }

  const canonicallyOrdered = [...calendar.events].sort(compareCalendarEvents)
  if (
    canonicallyOrdered.some(
      (event, index) => event.id !== calendar.events[index]?.id,
    )
  ) {
    addIssue(
      issues,
      'foundation',
      'foundation.calendar.order.invalid',
      '$.calendar.events',
      'Calendar events must use canonical date and event-kind order',
    )
  }
}

function validateBoundaryEvent(
  events: readonly CalendarEvent[],
  expectedDate: LocalDate,
  kind: FoundationCalendarEventKind,
  issues: SeasonFoundationValidationIssue[],
): void {
  if (events.length !== 1) {
    addIssue(
      issues,
      'foundation',
      'foundation.calendar.boundary_event.count_invalid',
      '$.calendar.events',
      `Calendar must contain exactly one ${kind} event`,
    )
    return
  }

  const event = events[0]
  if (
    event.scope !== 'league' ||
    event.originalScheduledDate !== expectedDate ||
    event.scheduledDate !== expectedDate ||
    event.actualDate !== null ||
    event.dateStatus !== 'scheduled' ||
    event.completionStatus !== 'pending'
  ) {
    addIssue(
      issues,
      'foundation',
      'foundation.calendar.boundary_event.invalid',
      '$.calendar.events',
      `${kind} must be a pending league event on its derived date`,
      { date: expectedDate },
    )
  }
}

function compareCalendarEvents(left: CalendarEvent, right: CalendarEvent): number {
  if (isLocalDate(left.scheduledDate) && isLocalDate(right.scheduledDate)) {
    const dateComparison = compareLocalDates(
      left.scheduledDate,
      right.scheduledDate,
    )
    if (dateComparison !== 0) {
      return dateComparison
    }
  } else if (isLocalDate(left.scheduledDate)) {
    return -1
  } else if (isLocalDate(right.scheduledDate)) {
    return 1
  }

  return left.kind < right.kind ? -1 : left.kind > right.kind ? 1 : 0
}

function deriveIdentityFingerprint(root: string, label: string): string {
  const derivedSeed = deriveSeed(root, label)
  const digest = derivedSeed.slice(derivedSeed.lastIndexOf(':') + 1)
  if (digest.length < ID_FINGERPRINT_LENGTH) {
    throw new Error('Derived seed digest is too short for a stable identity')
  }
  return digest.slice(0, ID_FINGERPRINT_LENGTH)
}

function areStructurallyEqual(left: unknown, right: unknown): boolean {
  if (Object.is(left, right)) {
    return true
  }
  if (Array.isArray(left) || Array.isArray(right)) {
    return (
      Array.isArray(left) &&
      Array.isArray(right) &&
      left.length === right.length &&
      left.every((value, index) => areStructurallyEqual(value, right[index]))
    )
  }
  if (!isRecord(left) || !isRecord(right)) {
    return false
  }

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

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function adaptEntityIssues(
  target: SeasonFoundationValidationIssue[],
  source: Exclude<SeasonFoundationValidationSource, 'foundation' | 'schedule'>,
  basePath: string,
  entityIssues: readonly {
    readonly code: string
    readonly path: string
    readonly message: string
  }[],
): void {
  for (const issue of entityIssues) {
    addIssue(
      target,
      source,
      issue.code,
      prefixPath(basePath, issue.path),
      issue.message,
    )
  }
}

function prefixPath(basePath: string, nestedPath: string): string {
  return nestedPath === '$' ? basePath : `${basePath}${nestedPath.slice(1)}`
}

function addIssue(
  issues: SeasonFoundationValidationIssue[],
  source: SeasonFoundationValidationSource,
  code: string,
  path: string,
  message: string,
  association: Pick<
    SeasonFoundationValidationIssue,
    'teamId' | 'gameId' | 'gameDayId' | 'date'
  > = {},
): void {
  issues.push(Object.freeze({ source, code, path, message, ...association }))
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Validation failed'
}
