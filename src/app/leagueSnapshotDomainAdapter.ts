import {
  parseGameDayId,
  parseGameId,
  parseLeagueId,
  parsePlayerId,
  parseScheduleId,
  parseScheduleRuleSetId,
  parseSeasonId,
  parseTeamId,
} from '../domain/ids'
import type { TeamId } from '../domain/ids'
import type {
  League,
  Player,
  Team,
} from '../domain/league'
import { assertValidLeague } from '../domain/leagueValidation'
import { parseLocalDate } from '../domain/localDate'
import type {
  GameDay,
  LeagueSchedule,
  OpponentRequirement,
  ScheduledGame,
} from '../domain/schedule'
import { parseSeason } from '../domain/season'
import type { Season } from '../domain/season'
import { parseSeasonCalendar } from '../domain/seasonCalendar'
import type {
  CalendarEvent,
  SeasonCalendar,
} from '../domain/seasonCalendar'
import type { CalendarEntryViewModel } from './calendarViewModel'
import { createCalendarEntries } from './calendarViewModel'
import type {
  LeagueSnapshotV2,
  LeagueSnapshotV2CalendarEventDto,
  LeagueSnapshotV2GameDayDto,
  LeagueSnapshotV2LeagueDto,
  LeagueSnapshotV2LeagueScheduleDto,
  LeagueSnapshotV2OpponentRequirementDto,
  LeagueSnapshotV2PlayerDto,
  LeagueSnapshotV2ScheduledGameDto,
  LeagueSnapshotV2TeamDto,
} from '../persistence/leagueSnapshotV2'

/**
 * Validated live-domain values projected from one authoritative V2 snapshot.
 * This is the only DTO-to-domain hydration seam used by Milestone 2 UI.
 */
export interface LeagueSnapshotDomainProjection {
  readonly league: League
  readonly season: Season
  readonly seasonCalendar: SeasonCalendar
  readonly schedule: LeagueSchedule
  readonly managedTeamId: TeamId | null
}

/**
 * Snapshot-stable presentation foundation. Preference-specific selectors may
 * derive from these entries, but must never rebuild them.
 */
export interface LeaguePresentationBundle
  extends LeagueSnapshotDomainProjection {
  readonly calendarEntries: readonly CalendarEntryViewModel[]
}

export function adaptLeagueSnapshotV2ToDomain(
  snapshot: LeagueSnapshotV2,
): LeagueSnapshotDomainProjection {
  const league = adaptLeague(snapshot.league)
  const season = parseSeason(snapshot.season)
  const seasonCalendar = parseSeasonCalendar({
    id: snapshot.seasonCalendar.id,
    version: snapshot.seasonCalendar.version,
    seasonId: snapshot.seasonCalendar.seasonId,
    events: snapshot.seasonCalendar.events.map(adaptCalendarEvent),
  })
  const schedule = adaptLeagueSchedule(snapshot.leagueSchedule)
  const managedTeamId =
    snapshot.managedTeamId === null
      ? null
      : parseManagedTeamId(snapshot.managedTeamId, league)

  if (
    season.leagueId !== league.id ||
    schedule.leagueId !== league.id ||
    schedule.seasonId !== season.id ||
    seasonCalendar.seasonId !== season.id ||
    season.scheduleId !== schedule.id
  ) {
    throw new RangeError(
      'The hydrated league, season, calendar, and schedule references do not agree',
    )
  }

  return Object.freeze({
    league,
    season,
    seasonCalendar,
    schedule,
    managedTeamId,
  })
}

export function createLeaguePresentationBundle(
  snapshot: LeagueSnapshotV2,
): LeaguePresentationBundle {
  const domain = adaptLeagueSnapshotV2ToDomain(snapshot)
  const calendarEntries = createCalendarEntries({
    league: domain.league,
    schedule: domain.schedule,
    seasonCalendar: domain.seasonCalendar,
    managedTeamId: domain.managedTeamId,
  })

  return Object.freeze({
    ...domain,
    calendarEntries,
  })
}

function adaptLeague(source: LeagueSnapshotV2LeagueDto): League {
  const league = Object.freeze({
    id: parseLeagueId(source.id),
    generatorVersion: source.generatorVersion,
    seedFingerprint: source.seedFingerprint,
    teams: Object.freeze(source.teams.map(adaptTeam)),
    players: Object.freeze(source.players.map(adaptPlayer)),
  }) satisfies League

  assertValidLeague(league)
  return league
}

function adaptTeam(source: LeagueSnapshotV2TeamDto): Team {
  return Object.freeze({
    id: parseTeamId(source.id),
    city: source.city,
    nickname: source.nickname,
    abbreviation: source.abbreviation,
    colors: Object.freeze({ ...source.colors }),
    mark: Object.freeze({ ...source.mark }),
  })
}

function adaptPlayer(source: LeagueSnapshotV2PlayerDto): Player {
  return Object.freeze({
    id: parsePlayerId(source.id),
    teamId: parseTeamId(source.teamId),
    firstName: source.firstName,
    lastName: source.lastName,
    age: source.age,
    jerseyNumber: source.jerseyNumber,
    primaryPosition: source.primaryPosition,
    secondaryPosition: source.secondaryPosition,
    ratingGenerationVersion: source.ratingGenerationVersion,
    ratings: Object.freeze({ ...source.ratings }),
    tendencies: Object.freeze({ ...source.tendencies }),
  })
}

function adaptCalendarEvent(
  source: LeagueSnapshotV2CalendarEventDto,
): CalendarEvent {
  const base = {
    id: source.id,
    version: source.version,
    seasonId: source.seasonId,
    kind: source.kind,
    title: source.title,
    originalScheduledDate: source.originalScheduledDate,
    scheduledDate: source.scheduledDate,
    actualDate: source.actualDate,
    dateStatus: source.dateStatus,
    completionStatus: source.completionStatus,
  } as const

  if (source.scope === 'team') {
    if (source.teamId === null) {
      throw new RangeError(`Team calendar event ${source.id} requires a TeamId`)
    }
    return { ...base, scope: 'team', teamId: parseTeamId(source.teamId) }
  }
  if (source.teamId !== null) {
    throw new RangeError(
      `League calendar event ${source.id} cannot reference a TeamId`,
    )
  }
  return { ...base, scope: 'league' }
}

function adaptLeagueSchedule(
  source: LeagueSnapshotV2LeagueScheduleDto,
): LeagueSchedule {
  return Object.freeze({
    id: parseScheduleId(source.id),
    leagueId: parseLeagueId(source.leagueId),
    seasonId: parseSeasonId(source.seasonId),
    ruleSetId: parseScheduleRuleSetId(source.ruleSetId),
    generationVersion: source.generationVersion,
    scheduleSeed: source.scheduleSeed,
    calendarDaySpacing: source.calendarDaySpacing,
    publicationStatus: source.publicationStatus,
    opponentRequirements: Object.freeze(
      source.opponentRequirements.map(adaptOpponentRequirement),
    ),
    gameDays: Object.freeze(source.gameDays.map(adaptGameDay)),
    games: Object.freeze(source.games.map(adaptScheduledGame)),
  })
}

function adaptOpponentRequirement(
  source: LeagueSnapshotV2OpponentRequirementDto,
): OpponentRequirement {
  return Object.freeze({
    firstTeamId: parseTeamId(source.firstTeamId),
    secondTeamId: parseTeamId(source.secondTeamId),
    totalMeetings: source.totalMeetings,
    homeGamesForFirstTeam: source.homeGamesForFirstTeam,
    homeGamesForSecondTeam: source.homeGamesForSecondTeam,
    stage: source.stage,
    ...(source.sourceTag === null ? {} : { sourceTag: source.sourceTag }),
  })
}

function adaptGameDay(source: LeagueSnapshotV2GameDayDto): GameDay {
  return Object.freeze({
    id: parseGameDayId(source.id),
    seasonId: parseSeasonId(source.seasonId),
    sequenceNumber: source.sequenceNumber,
    scheduledDate: parseLocalDate(source.scheduledDate),
    gameIds: Object.freeze(source.gameIds.map((gameId) => parseGameId(gameId))),
  })
}

function adaptScheduledGame(
  source: LeagueSnapshotV2ScheduledGameDto,
): ScheduledGame {
  return Object.freeze({
    id: parseGameId(source.id),
    seasonId: parseSeasonId(source.seasonId),
    gameDayId: parseGameDayId(source.gameDayId),
    stage: source.stage,
    homeTeamId: parseTeamId(source.homeTeamId),
    awayTeamId: parseTeamId(source.awayTeamId),
    originalScheduledDate: parseLocalDate(source.originalScheduledDate),
    currentScheduledDate:
      source.currentScheduledDate === null
        ? null
        : parseLocalDate(source.currentScheduledDate),
    ...(source.actualDate === null
      ? {}
      : { actualDate: parseLocalDate(source.actualDate) }),
    status: source.status,
    meetingNumber: source.meetingNumber,
  })
}

function parseManagedTeamId(value: TeamId, league: League): TeamId {
  const teamId = parseTeamId(value)
  if (league.teams.filter((team) => team.id === teamId).length !== 1) {
    throw new RangeError(
      `Managed team ${teamId} must reference exactly one hydrated league team`,
    )
  }
  return teamId
}
