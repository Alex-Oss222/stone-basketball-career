import {
  deriveSeasonFoundationCalendarEventId,
  deriveSeasonFoundationCalendarId,
  deriveSeasonFoundationSeasonId,
  deriveSeasonFoundationTeamSeasonId,
} from '../domain/seasonFoundation'
import type {
  CalendarEventId,
  LeagueId,
  ScheduleId,
  SeasonCalendarId,
  SeasonId,
  TeamId,
  TeamSeasonId,
} from '../domain/ids'
import type { League } from '../domain/league'
import {
  compareLocalDates,
  formatSeasonLabel,
} from '../domain/localDate'
import type { LocalDate } from '../domain/localDate'
import type {
  LeagueSchedule,
  ScheduleStage,
} from '../domain/schedule'
import { validateLeagueSchedule } from '../domain/scheduleValidation'
import type { SeasonCalendar } from '../domain/seasonCalendar'
import type { Season } from '../domain/season'
import type { TeamSeason } from '../domain/teamSeason'
import {
  InvalidLeagueSnapshotError,
} from './leagueSnapshotTypes'
import type {
  LeagueSnapshotCreationMetadata,
  LeagueSnapshotValidationIssue,
} from './leagueSnapshotTypes'
import type { SupportedScheduleRuleSetRegistration } from './supportedScheduleRuleSets'

export function validateSnapshotCrossObjectConsistency(
  league: League,
  season: Season,
  calendar: SeasonCalendar,
  teamSeasons: readonly TeamSeason[],
  schedule: LeagueSchedule,
  metadata: LeagueSnapshotCreationMetadata,
  registration: SupportedScheduleRuleSetRegistration,
): void {
  const issues: LeagueSnapshotValidationIssue[] = []
  const addIssue = (code: string, path: string, message: string): void => {
    issues.push({ code, path, message })
  }
  const leagueTeamIds = league.teams.map(({ id }) => id)
  const leagueTeamIdSet = new Set(leagueTeamIds)

  let expectedSeasonId: SeasonId | null = null
  try {
    expectedSeasonId = deriveSeasonFoundationSeasonId(
      league.id,
      metadata.startingYear,
    )
  } catch (error) {
    addIssue(
      'league_snapshot.identity.season.unavailable',
      '$.season.id',
      errorMessage(error, 'Season identity could not be derived'),
    )
  }
  if (expectedSeasonId !== null && season.id !== expectedSeasonId) {
    addIssue(
      'league_snapshot.identity.season.mismatch',
      '$.season.id',
      'SeasonId does not match the stored league and starting year',
    )
  }
  if (season.leagueId !== league.id) {
    addIssue(
      'league_snapshot.season.league_id.mismatch',
      '$.season.leagueId',
      'Season must reference the stored league',
    )
  }
  if (season.startingYear !== metadata.startingYear) {
    addIssue(
      'league_snapshot.metadata.starting_year.mismatch',
      '$.creationMetadata.startingYear',
      'Creation starting year must equal the stored season starting year',
    )
  }
  const expectedEndingYear = metadata.startingYear + 1
  if (season.endingYear !== expectedEndingYear) {
    addIssue(
      'league_snapshot.season.ending_year.mismatch',
      '$.season.endingYear',
      'Season ending year must be exactly one year after its starting year',
    )
  }
  let expectedDisplayLabel: string | null = null
  try {
    expectedDisplayLabel = formatSeasonLabel(
      metadata.startingYear,
      expectedEndingYear,
    )
  } catch (error) {
    addIssue(
      'league_snapshot.season.display_label.invalid',
      '$.season.displayLabel',
      errorMessage(error, 'Season display label could not be derived'),
    )
  }
  if (
    expectedDisplayLabel !== null &&
    season.displayLabel !== expectedDisplayLabel
  ) {
    addIssue(
      'league_snapshot.season.display_label.mismatch',
      '$.season.displayLabel',
      'Season display label does not match its stored years',
    )
  }
  if (season.rulesVersion !== metadata.scheduleRuleSetVersion) {
    addIssue(
      'league_snapshot.rule_set.season_version.mismatch',
      '$.season.rulesVersion',
      'Season rules version must match creation metadata',
    )
  }
  if (season.rulesVersion !== registration.ruleSet.version) {
    addIssue(
      'league_snapshot.rule_set.registry_version.mismatch',
      '$.season.rulesVersion',
      'Season rules version must match the resolved supported rule set',
    )
  }

  validateCalendarConsistency(
    calendar,
    season,
    schedule,
    metadata,
    registration.ruleSet.stage,
    leagueTeamIdSet,
    addIssue,
  )
  validateTeamSeasonConsistency(
    teamSeasons,
    season,
    leagueTeamIds,
    leagueTeamIdSet,
    addIssue,
  )
  validateScheduleConsistency(
    schedule,
    season,
    league.id,
    leagueTeamIds,
    metadata,
    registration,
    addIssue,
  )

  if (issues.length > 0) {
    throw new InvalidLeagueSnapshotError(issues)
  }
}

type AddCrossIssue = (code: string, path: string, message: string) => void

function validateCalendarConsistency(
  calendar: SeasonCalendar,
  season: Season,
  schedule: LeagueSchedule,
  metadata: LeagueSnapshotCreationMetadata,
  ruleSetStage: ScheduleStage,
  leagueTeamIds: ReadonlySet<TeamId>,
  addIssue: AddCrossIssue,
): void {
  if (calendar.seasonId !== season.id) {
    addIssue(
      'league_snapshot.calendar.season_id.mismatch',
      '$.seasonCalendar.seasonId',
      'Season calendar must reference the stored season',
    )
  }
  let expectedCalendarId: SeasonCalendarId | null = null
  try {
    expectedCalendarId = deriveSeasonFoundationCalendarId(season.id)
  } catch (error) {
    addIssue(
      'league_snapshot.identity.calendar.unavailable',
      '$.seasonCalendar.id',
      errorMessage(error, 'Calendar identity could not be derived'),
    )
  }
  if (expectedCalendarId !== null && calendar.id !== expectedCalendarId) {
    addIssue(
      'league_snapshot.identity.calendar.mismatch',
      '$.seasonCalendar.id',
      'SeasonCalendarId does not match the stored SeasonId',
    )
  }

  for (let index = 0; index < calendar.events.length; index += 1) {
    const event = calendar.events[index]
    const path = `$.seasonCalendar.events[${index}]`
    if (event.seasonId !== season.id) {
      addIssue(
        'league_snapshot.calendar.event_season_id.mismatch',
        `${path}.seasonId`,
        'Calendar event must reference the stored season',
      )
    }
    if (
      event.scope === 'team' &&
      !leagueTeamIds.has(event.teamId)
    ) {
      addIssue(
        'league_snapshot.calendar.team_id.foreign',
        `${path}.teamId`,
        'Team-scoped calendar event references a team outside the stored league',
      )
    }
    if (
      event.kind === 'regular_season_opening' ||
      event.kind === 'regular_season_conclusion'
    ) {
      if (event.scope !== 'league') {
        addIssue(
          'league_snapshot.calendar.boundary_scope.invalid',
          `${path}.scope`,
          'Regular-season boundary events must be league-scoped',
        )
      }
      let expectedEventId: CalendarEventId | null = null
      try {
        expectedEventId = deriveSeasonFoundationCalendarEventId(
          season.id,
          event.kind,
        )
      } catch (error) {
        addIssue(
          'league_snapshot.identity.calendar_event.unavailable',
          `${path}.id`,
          errorMessage(error, 'Calendar event identity could not be derived'),
        )
      }
      if (expectedEventId !== null && event.id !== expectedEventId) {
        addIssue(
          'league_snapshot.identity.calendar_event.mismatch',
          `${path}.id`,
          'Boundary CalendarEventId does not match its SeasonId and event kind',
        )
      }
    } else if (
      event.originalScheduledDate !== null ||
      event.scheduledDate !== null ||
      event.actualDate !== null ||
      event.dateStatus !== 'tba' ||
      event.completionStatus !== 'pending'
    ) {
      addIssue(
        'league_snapshot.calendar.future_event.unsupported_state',
        path,
        'This foundation may preserve future calendar events only as undated pending TBA records',
      )
    }
  }

  const openings = calendar.events.filter(
    ({ kind }) => kind === 'regular_season_opening',
  )
  const conclusions = calendar.events.filter(
    ({ kind }) => kind === 'regular_season_conclusion',
  )
  if (openings.length !== 1) {
    addIssue(
      'league_snapshot.calendar.opening.count',
      '$.seasonCalendar.events',
      'Season calendar must contain exactly one regular-season opening event',
    )
  }
  if (conclusions.length !== 1) {
    addIssue(
      'league_snapshot.calendar.conclusion.count',
      '$.seasonCalendar.events',
      'Season calendar must contain exactly one regular-season conclusion event',
    )
  }

  const regularSeasonGames = schedule.games.filter(
    ({ stage }) => stage === ruleSetStage,
  )
  const originalDates = regularSeasonGames.map(
    ({ originalScheduledDate }) => originalScheduledDate,
  )
  const nonCancelledGames = regularSeasonGames.filter(
    ({ status }) => status !== 'cancelled',
  )
  const currentDates = nonCancelledGames.flatMap(
    ({ currentScheduledDate }) =>
      currentScheduledDate === null ? [] : [currentScheduledDate],
  )
  const actualDates = regularSeasonGames.flatMap(({ actualDate }) =>
    actualDate === undefined ? [] : [actualDate],
  )
  const hasUnknownCurrentDate = nonCancelledGames.some(
    ({ currentScheduledDate }) => currentScheduledDate === null,
  )
  const firstOriginalDate = minimumLocalDate(originalDates)
  const latestOriginalDate = maximumLocalDate(originalDates)
  const firstCurrentDate = minimumLocalDate(currentDates)
  const latestCurrentDate = hasUnknownCurrentDate
    ? null
    : maximumLocalDate(currentDates)
  const firstActualDate = minimumLocalDate(actualDates)
  const latestActualDate = maximumLocalDate(actualDates)

  const opening = openings[0]
  if (opening !== undefined) {
    if (
      opening.originalScheduledDate !== metadata.regularSeasonStartDate ||
      opening.originalScheduledDate !== firstOriginalDate
    ) {
      addIssue(
        'league_snapshot.calendar.opening_date.mismatch',
        '$.seasonCalendar.events',
        'Regular-season opening must preserve the metadata and earliest original game date',
      )
    }
    if (opening.scheduledDate !== firstCurrentDate) {
      addIssue(
        'league_snapshot.calendar.opening_current_date.mismatch',
        '$.seasonCalendar.events',
        'Regular-season opening current date must match the earliest currently scheduled game date',
      )
    }
    if (
      opening.actualDate !== null &&
      opening.actualDate !== firstActualDate
    ) {
      addIssue(
        'league_snapshot.calendar.opening_actual_date.mismatch',
        '$.seasonCalendar.events',
        'A completed regular-season opening must match the earliest actual game date',
      )
    }
  }
  const conclusion = conclusions[0]
  if (conclusion !== undefined) {
    if (conclusion.originalScheduledDate !== latestOriginalDate) {
      addIssue(
        'league_snapshot.calendar.conclusion_date.mismatch',
        '$.seasonCalendar.events',
        'Regular-season conclusion must preserve the latest original game date',
      )
    }
    if (conclusion.scheduledDate !== latestCurrentDate) {
      addIssue(
        'league_snapshot.calendar.conclusion_current_date.mismatch',
        '$.seasonCalendar.events',
        'Regular-season conclusion current date must match the latest currently scheduled game date',
      )
    }
    if (conclusion.actualDate !== null) {
      const hasUnfinishedGame = regularSeasonGames.some(
        ({ status }) => status === 'scheduled' || status === 'postponed',
      )
      if (
        hasUnfinishedGame ||
        conclusion.actualDate !== latestActualDate
      ) {
        addIssue(
          'league_snapshot.calendar.conclusion_actual_date.mismatch',
          '$.seasonCalendar.events',
          'A completed regular-season conclusion requires all non-cancelled games to be complete and must match the latest actual game date',
        )
      }
    }
  }
}

function validateTeamSeasonConsistency(
  teamSeasons: readonly TeamSeason[],
  season: Season,
  leagueTeamIds: readonly TeamId[],
  leagueTeamIdSet: ReadonlySet<TeamId>,
  addIssue: AddCrossIssue,
): void {
  if (teamSeasons.length !== leagueTeamIds.length) {
    addIssue(
      'league_snapshot.team_seasons.count',
      '$.teamSeasons',
      'Team-season collection must contain exactly one record per league team',
    )
  }
  const seenTeamIds = new Set<TeamId>()
  for (let index = 0; index < teamSeasons.length; index += 1) {
    const teamSeason = teamSeasons[index]
    const path = `$.teamSeasons[${index}]`
    if (teamSeason.seasonId !== season.id) {
      addIssue(
        'league_snapshot.team_season.season_id.mismatch',
        `${path}.seasonId`,
        'Team-season record must reference the stored season',
      )
    }
    if (!leagueTeamIdSet.has(teamSeason.teamId)) {
      addIssue(
        'league_snapshot.team_season.team_id.foreign',
        `${path}.teamId`,
        'Team-season record references a team outside the stored league',
      )
    }
    if (seenTeamIds.has(teamSeason.teamId)) {
      addIssue(
        'league_snapshot.team_season.team_id.duplicate',
        `${path}.teamId`,
        'Team-season records must not repeat a TeamId',
      )
    }
    seenTeamIds.add(teamSeason.teamId)

    let expectedId: TeamSeasonId | null = null
    try {
      expectedId = deriveSeasonFoundationTeamSeasonId(
        season.id,
        teamSeason.teamId,
      )
    } catch (error) {
      addIssue(
        'league_snapshot.identity.team_season.unavailable',
        `${path}.id`,
        errorMessage(error, 'Team-season identity could not be derived'),
      )
    }
    if (expectedId !== null && teamSeason.id !== expectedId) {
      addIssue(
        'league_snapshot.identity.team_season.mismatch',
        `${path}.id`,
        'TeamSeasonId does not match its SeasonId and TeamId',
      )
    }
  }
  for (const teamId of leagueTeamIds) {
    if (!seenTeamIds.has(teamId)) {
      addIssue(
        'league_snapshot.team_season.team_id.missing',
        '$.teamSeasons',
        `League team ${teamId} has no team-season record`,
      )
    }
  }
}

function validateScheduleConsistency(
  schedule: LeagueSchedule,
  season: Season,
  leagueId: LeagueId,
  leagueTeamIds: readonly TeamId[],
  metadata: LeagueSnapshotCreationMetadata,
  registration: SupportedScheduleRuleSetRegistration,
  addIssue: AddCrossIssue,
): void {
  if (schedule.leagueId !== leagueId) {
    addIssue(
      'league_snapshot.schedule.league_id.mismatch',
      '$.leagueSchedule.leagueId',
      'Schedule must reference the stored league',
    )
  }
  if (schedule.seasonId !== season.id) {
    addIssue(
      'league_snapshot.schedule.season_id.mismatch',
      '$.leagueSchedule.seasonId',
      'Schedule must reference the stored season',
    )
  }
  if (season.scheduleId !== schedule.id) {
    addIssue(
      'league_snapshot.schedule.id.season_mismatch',
      '$.season.scheduleId',
      'Season ScheduleId must match the stored schedule',
    )
  }
  if (
    schedule.ruleSetId !== metadata.scheduleRuleSetId ||
    schedule.ruleSetId !== registration.ruleSet.id
  ) {
    addIssue(
      'league_snapshot.rule_set.id.mismatch',
      '$.leagueSchedule.ruleSetId',
      'Stored schedule and creation metadata must reference the resolved rule set',
    )
  }
  if (schedule.scheduleSeed !== metadata.scheduleSeed) {
    addIssue(
      'league_snapshot.metadata.schedule_seed.mismatch',
      '$.creationMetadata.scheduleSeed',
      'Creation schedule seed must equal the stored schedule seed',
    )
  }
  if (schedule.calendarDaySpacing !== metadata.gameDaySpacing) {
    addIssue(
      'league_snapshot.metadata.game_day_spacing.mismatch',
      '$.creationMetadata.gameDaySpacing',
      'Creation game-day spacing must equal the stored schedule spacing',
    )
  }
  if (
    schedule.generationVersion !== registration.scheduleGenerationVersion
  ) {
    addIssue(
      'league_snapshot.schedule.generation_version.unsupported',
      '$.leagueSchedule.generationVersion',
      'Stored schedule generation version is not supported by the resolved rule-set registration',
    )
  }

  let expectedScheduleId: ScheduleId | null = null
  try {
    expectedScheduleId = registration.deriveScheduleId({
      seasonId: season.id,
      teams: leagueTeamIds.map((id) => ({ id })),
      scheduleSeed: metadata.scheduleSeed,
    })
  } catch (error) {
    addIssue(
      'league_snapshot.identity.schedule.unavailable',
      '$.leagueSchedule.id',
      errorMessage(error, 'Schedule identity could not be derived'),
    )
  }
  if (expectedScheduleId !== null && schedule.id !== expectedScheduleId) {
    addIssue(
      'league_snapshot.identity.schedule.mismatch',
      '$.leagueSchedule.id',
      'ScheduleId does not match the stored season, teams, seed, and rule set',
    )
  }

  const report = validateLeagueSchedule({
    schedule,
    leagueId,
    seasonId: season.id,
    teams: leagueTeamIds.map((id) => ({ id })),
    ruleSet: registration.ruleSet,
    regularSeasonStartDate: metadata.regularSeasonStartDate,
    calendarDaySpacing: metadata.gameDaySpacing,
    opponentRequirementValidationMode: 'validate_stored',
  })
  for (const violation of report.hardViolations) {
    addIssue(
      `league_snapshot.schedule.${violation.code}`,
      scheduleIssuePath(violation),
      violation.message,
    )
  }
}

function scheduleIssuePath(
  issue: ReturnType<typeof validateLeagueSchedule>['hardViolations'][number],
): string {
  if (issue.gameId !== undefined) return '$.leagueSchedule.games'
  if (issue.gameDayId !== undefined) return '$.leagueSchedule.gameDays'
  if (issue.teamId !== undefined) return '$.leagueSchedule'
  return '$.leagueSchedule'
}

function minimumLocalDate(dates: readonly LocalDate[]): LocalDate | null {
  if (dates.length === 0) return null
  return dates.reduce((minimum, date) =>
    compareLocalDates(date, minimum) < 0 ? date : minimum,
  )
}

function maximumLocalDate(dates: readonly LocalDate[]): LocalDate | null {
  if (dates.length === 0) return null
  return dates.reduce((maximum, date) =>
    compareLocalDates(date, maximum) > 0 ? date : maximum,
  )
}

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback
}
