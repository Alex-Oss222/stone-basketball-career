import {
  deriveSeasonFoundationCalendarEventId,
  deriveSeasonFoundationCalendarId,
  deriveSeasonFoundationSeasonId,
  deriveSeasonFoundationTeamSeasonId,
  parseSeasonFoundationConfiguration,
} from '../app/commands/createSeasonFoundation'
import type {
  SeasonFoundation,
  SeasonFoundationConfiguration,
} from '../app/commands/createSeasonFoundation'
import {
  parseCalendarEventId,
  parseGameDayId,
  parseGameId,
  parseLeagueId,
  parseScheduleId,
  parseScheduleRuleSetId,
  parseSeasonCalendarId,
  parseSeasonId,
  parseTeamId,
  parseTeamSeasonId,
} from '../domain/ids'
import type {
  CalendarEventId,
  GameDayId,
  GameId,
  LeagueId,
  PlayerId,
  ScheduleId,
  ScheduleRuleSetId,
  SeasonCalendarId,
  SeasonId,
  TeamId,
  TeamSeasonId,
} from '../domain/ids'
import type {
  League,
  PlayerTendencies,
  Position,
  TeamColors,
  TeamMark,
} from '../domain/league'
import {
  compareLocalDates,
  formatSeasonLabel,
  parseLocalDate,
} from '../domain/localDate'
import type { LocalDate } from '../domain/localDate'
import type { PlayerRatings } from '../domain/ratings'
import {
  SCHEDULED_GAME_STATUSES,
  SCHEDULE_PUBLICATION_STATUSES,
  SCHEDULE_STAGES,
} from '../domain/schedule'
import type {
  GameDay,
  LeagueSchedule,
  OpponentRequirement,
  SchedulePublicationStatus,
  ScheduleStage,
  ScheduledGame,
  ScheduledGameStatus,
} from '../domain/schedule'
import { validateLeagueSchedule } from '../domain/scheduleValidation'
import {
  CALENDAR_COMPLETION_STATUSES,
  CALENDAR_DATE_STATUSES,
  CALENDAR_EVENT_KINDS,
  CALENDAR_EVENT_SCOPES,
  parseCalendarEvent,
  parseSeasonCalendar,
} from '../domain/seasonCalendar'
import type {
  CalendarCompletionStatus,
  CalendarDateStatus,
  CalendarEvent,
  CalendarEventKind,
  CalendarEventScope,
  SeasonCalendar,
} from '../domain/seasonCalendar'
import {
  SEASON_PHASES,
  SEASON_STATUSES,
  parseSeason,
} from '../domain/season'
import type { Season, SeasonPhase, SeasonStatus } from '../domain/season'
import {
  TEAM_COMPETITIVE_STATUSES,
  parseTeamSeason,
} from '../domain/teamSeason'
import type {
  TeamCompetitiveStatus,
  TeamSeason,
} from '../domain/teamSeason'
import { normalizeSeed } from '../random/seed'
import {
  InvalidLeagueSnapshotError,
  LEAGUE_SNAPSHOT_KIND,
  LEAGUE_SNAPSHOT_VERSION,
  parseLeagueSnapshot,
} from './leagueSnapshot'
import type { LeagueSnapshotV1 } from './leagueSnapshot'
import {
  findSupportedScheduleRuleSet,
  hasRegisteredScheduleRuleSetId,
} from './supportedScheduleRuleSets'
import type { SupportedScheduleRuleSetRegistration } from './supportedScheduleRuleSets'
import {
  assertJsonSafeValue,
  expectExactRecord,
  expectLiteral,
  expectOneOf,
  expectPositiveSafeInteger,
  expectSafeInteger,
  expectString,
  parseDenseArray,
} from './strictSerializedValue'
import type {
  RejectSerializedValue,
  SerializedRecord,
} from './strictSerializedValue'

export const LEAGUE_SNAPSHOT_V2_VERSION = 2 as const

export interface LeagueSnapshotV2TeamDto {
  readonly id: TeamId
  readonly city: string
  readonly nickname: string
  readonly abbreviation: string
  readonly colors: TeamColors
  readonly mark: TeamMark
}

export interface LeagueSnapshotV2PlayerDto {
  readonly id: PlayerId
  readonly teamId: TeamId
  readonly firstName: string
  readonly lastName: string
  readonly age: number
  readonly jerseyNumber: number
  readonly primaryPosition: Position
  readonly secondaryPosition: Position | null
  readonly ratingGenerationVersion: 1
  readonly ratings: PlayerRatings
  readonly tendencies: PlayerTendencies
}

export interface LeagueSnapshotV2LeagueDto {
  readonly id: LeagueId
  readonly generatorVersion: 1
  readonly seedFingerprint: string
  readonly teams: readonly LeagueSnapshotV2TeamDto[]
  readonly players: readonly LeagueSnapshotV2PlayerDto[]
}

export interface LeagueSnapshotV2SeasonDto {
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

export interface LeagueSnapshotV2CalendarEventDto {
  readonly id: CalendarEventId
  readonly version: 1
  readonly seasonId: SeasonId
  readonly kind: CalendarEventKind
  readonly scope: CalendarEventScope
  /** Null represents the absence of a TeamId for a league-scoped event. */
  readonly teamId: TeamId | null
  readonly title: string
  readonly originalScheduledDate: LocalDate | null
  readonly scheduledDate: LocalDate | null
  readonly actualDate: LocalDate | null
  readonly dateStatus: CalendarDateStatus
  readonly completionStatus: CalendarCompletionStatus
}

export interface LeagueSnapshotV2SeasonCalendarDto {
  readonly id: SeasonCalendarId
  readonly version: 1
  readonly seasonId: SeasonId
  readonly events: readonly LeagueSnapshotV2CalendarEventDto[]
}

export interface LeagueSnapshotV2TeamSeasonDto {
  readonly id: TeamSeasonId
  readonly version: 1
  readonly seasonId: SeasonId
  readonly teamId: TeamId
  readonly competitiveStatus: TeamCompetitiveStatus
  readonly eliminationDate: LocalDate | null
  readonly teamOffseasonStartDate: LocalDate | null
  readonly postseasonSeed: number | null
}

export interface LeagueSnapshotV2OpponentRequirementDto {
  readonly firstTeamId: TeamId
  readonly secondTeamId: TeamId
  readonly totalMeetings: number
  readonly homeGamesForFirstTeam: number
  readonly homeGamesForSecondTeam: number
  readonly stage: ScheduleStage
  readonly sourceTag: string | null
}

export interface LeagueSnapshotV2GameDayDto {
  readonly id: GameDayId
  readonly seasonId: SeasonId
  readonly sequenceNumber: number
  readonly scheduledDate: LocalDate
  readonly gameIds: readonly GameId[]
}

export interface LeagueSnapshotV2ScheduledGameDto {
  readonly id: GameId
  readonly seasonId: SeasonId
  readonly gameDayId: GameDayId
  readonly stage: ScheduleStage
  readonly homeTeamId: TeamId
  readonly awayTeamId: TeamId
  readonly originalScheduledDate: LocalDate
  readonly currentScheduledDate: LocalDate | null
  readonly actualDate: LocalDate | null
  readonly status: ScheduledGameStatus
  readonly meetingNumber: number
}

export interface LeagueSnapshotV2LeagueScheduleDto {
  readonly id: ScheduleId
  readonly leagueId: LeagueId
  readonly seasonId: SeasonId
  readonly ruleSetId: ScheduleRuleSetId
  readonly generationVersion: number
  readonly scheduleSeed: string
  readonly calendarDaySpacing: number
  readonly publicationStatus: SchedulePublicationStatus
  readonly opponentRequirements: readonly LeagueSnapshotV2OpponentRequirementDto[]
  readonly gameDays: readonly LeagueSnapshotV2GameDayDto[]
  readonly games: readonly LeagueSnapshotV2ScheduledGameDto[]
}

export interface LeagueSnapshotV2CreationMetadata {
  readonly startingYear: number
  readonly regularSeasonStartDate: LocalDate
  readonly gameDaySpacing: number
  readonly scheduleSeed: string
  readonly scheduleRuleSetId: ScheduleRuleSetId
  readonly scheduleRuleSetVersion: number
}

export interface LeagueSnapshotV2 {
  readonly kind: typeof LEAGUE_SNAPSHOT_KIND
  readonly snapshotVersion: typeof LEAGUE_SNAPSHOT_V2_VERSION
  readonly revision: number
  readonly rootSeed: string
  readonly managedTeamId: TeamId | null
  readonly league: LeagueSnapshotV2LeagueDto
  readonly season: LeagueSnapshotV2SeasonDto
  readonly seasonCalendar: LeagueSnapshotV2SeasonCalendarDto
  readonly teamSeasons: readonly LeagueSnapshotV2TeamSeasonDto[]
  readonly leagueSchedule: LeagueSnapshotV2LeagueScheduleDto
  readonly creationMetadata: LeagueSnapshotV2CreationMetadata
}

export interface LeagueSnapshotV2ValidationIssue {
  readonly code: string
  readonly path: string
  readonly message: string
}

export class InvalidLeagueSnapshotV2Error extends InvalidLeagueSnapshotError {
  readonly issues: readonly LeagueSnapshotV2ValidationIssue[]

  constructor(
    issues: readonly LeagueSnapshotV2ValidationIssue[],
    cause?: unknown,
  ) {
    const firstIssue = issues[0] ?? {
      code: 'league_snapshot_v2.invalid',
      path: '$',
      message: 'League snapshot V2 is invalid',
    }
    super(firstIssue.path, firstIssue.message, cause)
    this.name = 'InvalidLeagueSnapshotV2Error'
    this.issues = Object.freeze(issues.map((issue) => Object.freeze({ ...issue })))
  }
}

export interface SerializeLeagueSnapshotV2Input {
  readonly rootSeed: string
  readonly managedTeamId: TeamId | null
  readonly league: League
  readonly foundation: SeasonFoundation
  readonly creationInputs: SeasonFoundationConfiguration
}

interface ParsedSchedule {
  readonly domain: LeagueSchedule
  readonly dto: LeagueSnapshotV2LeagueScheduleDto
}

const TOP_LEVEL_KEYS = [
  'kind',
  'snapshotVersion',
  'revision',
  'rootSeed',
  'managedTeamId',
  'league',
  'season',
  'seasonCalendar',
  'teamSeasons',
  'leagueSchedule',
  'creationMetadata',
] as const

const SEASON_KEYS = [
  'id',
  'leagueId',
  'seasonNumber',
  'startingYear',
  'endingYear',
  'displayLabel',
  'rulesVersion',
  'currentDate',
  'currentPhase',
  'scheduleId',
  'status',
] as const

const SEASON_CALENDAR_KEYS = ['id', 'version', 'seasonId', 'events'] as const
const CALENDAR_EVENT_KEYS = [
  'id',
  'version',
  'seasonId',
  'kind',
  'scope',
  'teamId',
  'title',
  'originalScheduledDate',
  'scheduledDate',
  'actualDate',
  'dateStatus',
  'completionStatus',
] as const
const TEAM_SEASON_KEYS = [
  'id',
  'version',
  'seasonId',
  'teamId',
  'competitiveStatus',
  'eliminationDate',
  'teamOffseasonStartDate',
  'postseasonSeed',
] as const
const SCHEDULE_KEYS = [
  'id',
  'leagueId',
  'seasonId',
  'ruleSetId',
  'generationVersion',
  'scheduleSeed',
  'calendarDaySpacing',
  'publicationStatus',
  'opponentRequirements',
  'gameDays',
  'games',
] as const
const OPPONENT_REQUIREMENT_KEYS = [
  'firstTeamId',
  'secondTeamId',
  'totalMeetings',
  'homeGamesForFirstTeam',
  'homeGamesForSecondTeam',
  'stage',
  'sourceTag',
] as const
const GAME_DAY_KEYS = [
  'id',
  'seasonId',
  'sequenceNumber',
  'scheduledDate',
  'gameIds',
] as const
const SCHEDULED_GAME_KEYS = [
  'id',
  'seasonId',
  'gameDayId',
  'stage',
  'homeTeamId',
  'awayTeamId',
  'originalScheduledDate',
  'currentScheduledDate',
  'actualDate',
  'status',
  'meetingNumber',
] as const
const CREATION_METADATA_KEYS = [
  'startingYear',
  'regularSeasonStartDate',
  'gameDaySpacing',
  'scheduleSeed',
  'scheduleRuleSetId',
  'scheduleRuleSetVersion',
] as const

const rejectStructure: RejectSerializedValue = (path, message) => {
  throw invalid('league_snapshot_v2.structure.invalid', path, message)
}

/**
 * Strictly parses and cross-validates a detached JSON-safe V2 DTO. This normal
 * restoration path never calls league, season, calendar, team-season,
 * opponent, or schedule generation.
 */
export function parseLeagueSnapshotV2(value: unknown): LeagueSnapshotV2 {
  try {
    assertJsonSafeValue(value, '$', rejectStructure)
  } catch (error) {
    if (error instanceof InvalidLeagueSnapshotV2Error) throw error
    throw invalid(
      'league_snapshot_v2.structure.invalid',
      '$',
      errorMessage(error, 'Snapshot is not JSON-safe'),
      error,
    )
  }

  const source = expectExactRecord(value, TOP_LEVEL_KEYS, '$', rejectStructure)
  expectLiteral(source.kind, LEAGUE_SNAPSHOT_KIND, '$.kind', rejectStructure)
  expectLiteral(
    source.snapshotVersion,
    LEAGUE_SNAPSHOT_V2_VERSION,
    '$.snapshotVersion',
    rejectStructure,
  )
  const revision = expectPositiveSafeInteger(
    source.revision,
    '$.revision',
    rejectStructure,
  )

  const v1 = parseLeagueFieldsThroughV1(source)
  const season = parseSeasonDto(source.season, '$.season')
  const seasonCalendar = parseSeasonCalendarDto(
    source.seasonCalendar,
    '$.seasonCalendar',
  )
  const teamSeasons = parseDenseArray(
    source.teamSeasons,
    '$.teamSeasons',
    parseTeamSeasonDto,
    rejectStructure,
  )
  const parsedSchedule = parseLeagueScheduleDto(
    source.leagueSchedule,
    '$.leagueSchedule',
  )
  const creationMetadata = parseCreationMetadata(
    source.creationMetadata,
    '$.creationMetadata',
  )
  const registration = resolveRuleSet(creationMetadata)

  validateSnapshotCrossObjectConsistency(
    v1,
    season,
    seasonCalendar,
    teamSeasons,
    parsedSchedule.domain,
    creationMetadata,
    registration,
  )

  return {
    kind: LEAGUE_SNAPSHOT_KIND,
    snapshotVersion: LEAGUE_SNAPSHOT_V2_VERSION,
    revision,
    rootSeed: v1.rootSeed,
    managedTeamId: v1.managedTeamId,
    league: serializeLeague(v1.league),
    season: serializeSeason(season),
    seasonCalendar: serializeSeasonCalendar(seasonCalendar),
    teamSeasons: teamSeasons.map(serializeTeamSeason),
    leagueSchedule: parsedSchedule.dto,
    creationMetadata,
  }
}

/**
 * Serializes already-created domain values into the exact V2 DTO shape. The
 * caller must pass the result through parseLeagueSnapshotV2 before trusting or
 * storing it.
 */
export function serializeLeagueSnapshotV2(
  input: SerializeLeagueSnapshotV2Input,
): LeagueSnapshotV2 {
  const { foundation } = input
  return {
    kind: LEAGUE_SNAPSHOT_KIND,
    snapshotVersion: LEAGUE_SNAPSHOT_V2_VERSION,
    revision: 1,
    rootSeed: input.rootSeed,
    managedTeamId: input.managedTeamId,
    league: serializeLeague(input.league),
    season: serializeSeason(foundation.season),
    seasonCalendar: serializeSeasonCalendar(foundation.calendar),
    teamSeasons: foundation.teamSeasons.map(serializeTeamSeason),
    leagueSchedule: serializeLeagueSchedule(foundation.schedule),
    creationMetadata: {
      startingYear: input.creationInputs.startingYear,
      regularSeasonStartDate:
        input.creationInputs.regularSeasonStartDate,
      gameDaySpacing: input.creationInputs.calendarDaySpacing,
      scheduleSeed: input.creationInputs.scheduleSeed,
      scheduleRuleSetId: foundation.schedule.ruleSetId,
      scheduleRuleSetVersion: foundation.season.rulesVersion,
    },
  }
}

function parseLeagueFieldsThroughV1(source: SerializedRecord): LeagueSnapshotV1 {
  try {
    return parseLeagueSnapshot({
      kind: LEAGUE_SNAPSHOT_KIND,
      snapshotVersion: LEAGUE_SNAPSHOT_VERSION,
      rootSeed: source.rootSeed,
      league: source.league,
      managedTeamId: source.managedTeamId,
    })
  } catch (error) {
    if (error instanceof InvalidLeagueSnapshotError) {
      throw invalid(
        'league_snapshot_v2.league.invalid',
        error.path,
        stripErrorPath(error.message, error.path),
        error,
      )
    }
    throw invalid(
      'league_snapshot_v2.league.invalid',
      '$.league',
      errorMessage(error, 'League data is invalid'),
      error,
    )
  }
}

function parseSeasonDto(value: unknown, path: string): Season {
  const source = expectExactRecord(value, SEASON_KEYS, path, rejectStructure)
  const parsed = {
    id: parseAtPath(`${path}.id`, source.id, parseSeasonId),
    leagueId: parseAtPath(`${path}.leagueId`, source.leagueId, parseLeagueId),
    seasonNumber: expectPositiveSafeInteger(
      source.seasonNumber,
      `${path}.seasonNumber`,
      rejectStructure,
    ),
    startingYear: expectSafeInteger(
      source.startingYear,
      `${path}.startingYear`,
      rejectStructure,
    ),
    endingYear: expectSafeInteger(
      source.endingYear,
      `${path}.endingYear`,
      rejectStructure,
    ),
    displayLabel: expectString(
      source.displayLabel,
      `${path}.displayLabel`,
      rejectStructure,
    ),
    rulesVersion: expectPositiveSafeInteger(
      source.rulesVersion,
      `${path}.rulesVersion`,
      rejectStructure,
    ),
    currentDate: parseAtPath(
      `${path}.currentDate`,
      source.currentDate,
      parseLocalDate,
    ),
    currentPhase: expectOneOf(
      source.currentPhase,
      SEASON_PHASES,
      `${path}.currentPhase`,
      rejectStructure,
    ),
    scheduleId: parseAtPath(
      `${path}.scheduleId`,
      source.scheduleId,
      parseScheduleId,
    ),
    status: expectOneOf(
      source.status,
      SEASON_STATUSES,
      `${path}.status`,
      rejectStructure,
    ),
  }
  return parseDomainAtPath(
    'league_snapshot_v2.season.invalid',
    path,
    () => parseSeason(parsed),
  )
}

function parseSeasonCalendarDto(
  value: unknown,
  path: string,
): SeasonCalendar {
  const source = expectExactRecord(
    value,
    SEASON_CALENDAR_KEYS,
    path,
    rejectStructure,
  )
  const events = parseDenseArray(
    source.events,
    `${path}.events`,
    parseCalendarEventDto,
    rejectStructure,
  )
  const parsed = {
    id: parseAtPath(`${path}.id`, source.id, parseSeasonCalendarId),
    version: expectLiteral(
      source.version,
      1,
      `${path}.version`,
      rejectStructure,
    ),
    seasonId: parseAtPath(
      `${path}.seasonId`,
      source.seasonId,
      parseSeasonId,
    ),
    events,
  }
  return parseDomainAtPath(
    'league_snapshot_v2.calendar.invalid',
    path,
    () => parseSeasonCalendar(parsed),
  )
}

function parseCalendarEventDto(
  value: unknown,
  path: string,
): CalendarEvent {
  const source = expectExactRecord(
    value,
    CALENDAR_EVENT_KEYS,
    path,
    rejectStructure,
  )
  const scope = expectOneOf(
    source.scope,
    CALENDAR_EVENT_SCOPES,
    `${path}.scope`,
    rejectStructure,
  )
  const teamId =
    source.teamId === null
      ? null
      : parseAtPath(`${path}.teamId`, source.teamId, parseTeamId)
  if (scope === 'team' && teamId === null) {
    throw invalid(
      'league_snapshot_v2.calendar.team_id.required',
      `${path}.teamId`,
      'A team-scoped event requires a TeamId',
    )
  }
  if (scope === 'league' && teamId !== null) {
    throw invalid(
      'league_snapshot_v2.calendar.team_id.forbidden',
      `${path}.teamId`,
      'A league-scoped event must store a null TeamId',
    )
  }

  const base = {
    id: parseAtPath(`${path}.id`, source.id, parseCalendarEventId),
    version: expectLiteral(
      source.version,
      1,
      `${path}.version`,
      rejectStructure,
    ),
    seasonId: parseAtPath(
      `${path}.seasonId`,
      source.seasonId,
      parseSeasonId,
    ),
    kind: expectOneOf(
      source.kind,
      CALENDAR_EVENT_KINDS,
      `${path}.kind`,
      rejectStructure,
    ),
    title: expectString(source.title, `${path}.title`, rejectStructure),
    originalScheduledDate: parseNullableLocalDate(
      source.originalScheduledDate,
      `${path}.originalScheduledDate`,
    ),
    scheduledDate: parseNullableLocalDate(
      source.scheduledDate,
      `${path}.scheduledDate`,
    ),
    actualDate: parseNullableLocalDate(
      source.actualDate,
      `${path}.actualDate`,
    ),
    dateStatus: expectOneOf(
      source.dateStatus,
      CALENDAR_DATE_STATUSES,
      `${path}.dateStatus`,
      rejectStructure,
    ),
    completionStatus: expectOneOf(
      source.completionStatus,
      CALENDAR_COMPLETION_STATUSES,
      `${path}.completionStatus`,
      rejectStructure,
    ),
  }
  const parsed =
    scope === 'team'
      ? { ...base, scope, teamId: teamId as TeamId }
      : { ...base, scope }
  return parseDomainAtPath(
    'league_snapshot_v2.calendar_event.invalid',
    path,
    () => parseCalendarEvent(parsed),
  )
}

function parseTeamSeasonDto(value: unknown, path: string): TeamSeason {
  const source = expectExactRecord(
    value,
    TEAM_SEASON_KEYS,
    path,
    rejectStructure,
  )
  const parsed = {
    id: parseAtPath(`${path}.id`, source.id, parseTeamSeasonId),
    version: expectLiteral(
      source.version,
      1,
      `${path}.version`,
      rejectStructure,
    ),
    seasonId: parseAtPath(
      `${path}.seasonId`,
      source.seasonId,
      parseSeasonId,
    ),
    teamId: parseAtPath(`${path}.teamId`, source.teamId, parseTeamId),
    competitiveStatus: expectOneOf(
      source.competitiveStatus,
      TEAM_COMPETITIVE_STATUSES,
      `${path}.competitiveStatus`,
      rejectStructure,
    ),
    eliminationDate: parseNullableLocalDate(
      source.eliminationDate,
      `${path}.eliminationDate`,
    ),
    teamOffseasonStartDate: parseNullableLocalDate(
      source.teamOffseasonStartDate,
      `${path}.teamOffseasonStartDate`,
    ),
    postseasonSeed: parseNullablePositiveSafeInteger(
      source.postseasonSeed,
      `${path}.postseasonSeed`,
    ),
  }
  return parseDomainAtPath(
    'league_snapshot_v2.team_season.invalid',
    path,
    () => parseTeamSeason(parsed),
  )
}

function parseLeagueScheduleDto(value: unknown, path: string): ParsedSchedule {
  const source = expectExactRecord(value, SCHEDULE_KEYS, path, rejectStructure)
  const opponentRequirements = parseDenseArray(
    source.opponentRequirements,
    `${path}.opponentRequirements`,
    parseOpponentRequirementDto,
    rejectStructure,
  )
  const gameDays = parseDenseArray(
    source.gameDays,
    `${path}.gameDays`,
    parseGameDayDto,
    rejectStructure,
  )
  const games = parseDenseArray(
    source.games,
    `${path}.games`,
    parseScheduledGameDto,
    rejectStructure,
  )
  const scheduleSeed = parseCanonicalSeed(
    source.scheduleSeed,
    `${path}.scheduleSeed`,
  )
  const domain: LeagueSchedule = {
    id: parseAtPath(`${path}.id`, source.id, parseScheduleId),
    leagueId: parseAtPath(
      `${path}.leagueId`,
      source.leagueId,
      parseLeagueId,
    ),
    seasonId: parseAtPath(
      `${path}.seasonId`,
      source.seasonId,
      parseSeasonId,
    ),
    ruleSetId: parseAtPath(
      `${path}.ruleSetId`,
      source.ruleSetId,
      parseScheduleRuleSetId,
    ),
    generationVersion: expectPositiveSafeInteger(
      source.generationVersion,
      `${path}.generationVersion`,
      rejectStructure,
    ),
    scheduleSeed,
    calendarDaySpacing: expectPositiveSafeInteger(
      source.calendarDaySpacing,
      `${path}.calendarDaySpacing`,
      rejectStructure,
    ),
    publicationStatus: expectOneOf(
      source.publicationStatus,
      SCHEDULE_PUBLICATION_STATUSES,
      `${path}.publicationStatus`,
      rejectStructure,
    ),
    opponentRequirements,
    gameDays,
    games,
  }
  return { domain, dto: serializeLeagueSchedule(domain) }
}

function parseOpponentRequirementDto(
  value: unknown,
  path: string,
): OpponentRequirement {
  const source = expectExactRecord(
    value,
    OPPONENT_REQUIREMENT_KEYS,
    path,
    rejectStructure,
  )
  const totalMeetings = expectSafeInteger(
    source.totalMeetings,
    `${path}.totalMeetings`,
    rejectStructure,
  )
  const homeGamesForFirstTeam = expectSafeInteger(
    source.homeGamesForFirstTeam,
    `${path}.homeGamesForFirstTeam`,
    rejectStructure,
  )
  const homeGamesForSecondTeam = expectSafeInteger(
    source.homeGamesForSecondTeam,
    `${path}.homeGamesForSecondTeam`,
    rejectStructure,
  )
  if (
    totalMeetings < 0 ||
    homeGamesForFirstTeam < 0 ||
    homeGamesForSecondTeam < 0
  ) {
    throw invalid(
      'league_snapshot_v2.schedule.requirement_numeric.invalid',
      path,
      'Opponent requirement counts must be non-negative safe integers',
    )
  }
  const sourceTag =
    source.sourceTag === null
      ? null
      : expectString(source.sourceTag, `${path}.sourceTag`, rejectStructure)
  return {
    firstTeamId: parseAtPath(
      `${path}.firstTeamId`,
      source.firstTeamId,
      parseTeamId,
    ),
    secondTeamId: parseAtPath(
      `${path}.secondTeamId`,
      source.secondTeamId,
      parseTeamId,
    ),
    totalMeetings,
    homeGamesForFirstTeam,
    homeGamesForSecondTeam,
    stage: expectOneOf(
      source.stage,
      SCHEDULE_STAGES,
      `${path}.stage`,
      rejectStructure,
    ),
    ...(sourceTag === null ? {} : { sourceTag }),
  }
}

function parseGameDayDto(value: unknown, path: string): GameDay {
  const source = expectExactRecord(value, GAME_DAY_KEYS, path, rejectStructure)
  return {
    id: parseAtPath(`${path}.id`, source.id, parseGameDayId),
    seasonId: parseAtPath(
      `${path}.seasonId`,
      source.seasonId,
      parseSeasonId,
    ),
    sequenceNumber: expectPositiveSafeInteger(
      source.sequenceNumber,
      `${path}.sequenceNumber`,
      rejectStructure,
    ),
    scheduledDate: parseAtPath(
      `${path}.scheduledDate`,
      source.scheduledDate,
      parseLocalDate,
    ),
    gameIds: parseDenseArray(
      source.gameIds,
      `${path}.gameIds`,
      (gameId, gameIdPath) => parseAtPath(gameIdPath, gameId, parseGameId),
      rejectStructure,
    ),
  }
}

function parseScheduledGameDto(
  value: unknown,
  path: string,
): ScheduledGame {
  const source = expectExactRecord(
    value,
    SCHEDULED_GAME_KEYS,
    path,
    rejectStructure,
  )
  const actualDate = parseNullableLocalDate(
    source.actualDate,
    `${path}.actualDate`,
  )
  return {
    id: parseAtPath(`${path}.id`, source.id, parseGameId),
    seasonId: parseAtPath(
      `${path}.seasonId`,
      source.seasonId,
      parseSeasonId,
    ),
    gameDayId: parseAtPath(
      `${path}.gameDayId`,
      source.gameDayId,
      parseGameDayId,
    ),
    stage: expectOneOf(
      source.stage,
      SCHEDULE_STAGES,
      `${path}.stage`,
      rejectStructure,
    ),
    homeTeamId: parseAtPath(
      `${path}.homeTeamId`,
      source.homeTeamId,
      parseTeamId,
    ),
    awayTeamId: parseAtPath(
      `${path}.awayTeamId`,
      source.awayTeamId,
      parseTeamId,
    ),
    originalScheduledDate: parseAtPath(
      `${path}.originalScheduledDate`,
      source.originalScheduledDate,
      parseLocalDate,
    ),
    currentScheduledDate: parseNullableLocalDate(
      source.currentScheduledDate,
      `${path}.currentScheduledDate`,
    ),
    ...(actualDate === null ? {} : { actualDate }),
    status: expectOneOf(
      source.status,
      SCHEDULED_GAME_STATUSES,
      `${path}.status`,
      rejectStructure,
    ),
    meetingNumber: expectPositiveSafeInteger(
      source.meetingNumber,
      `${path}.meetingNumber`,
      rejectStructure,
    ),
  }
}

function parseCreationMetadata(
  value: unknown,
  path: string,
): LeagueSnapshotV2CreationMetadata {
  const source = expectExactRecord(
    value,
    CREATION_METADATA_KEYS,
    path,
    rejectStructure,
  )
  const configuration = parseDomainAtPath(
    'league_snapshot_v2.creation_metadata.invalid',
    path,
    () =>
      parseSeasonFoundationConfiguration({
        startingYear: expectSafeInteger(
          source.startingYear,
          `${path}.startingYear`,
          rejectStructure,
        ),
        regularSeasonStartDate: parseAtPath(
          `${path}.regularSeasonStartDate`,
          source.regularSeasonStartDate,
          parseLocalDate,
        ),
        calendarDaySpacing: expectPositiveSafeInteger(
          source.gameDaySpacing,
          `${path}.gameDaySpacing`,
          rejectStructure,
        ),
        scheduleSeed: parseCanonicalSeed(
          source.scheduleSeed,
          `${path}.scheduleSeed`,
        ),
      }),
  )
  return {
    startingYear: configuration.startingYear,
    regularSeasonStartDate: configuration.regularSeasonStartDate,
    gameDaySpacing: configuration.calendarDaySpacing,
    scheduleSeed: configuration.scheduleSeed,
    scheduleRuleSetId: parseAtPath(
      `${path}.scheduleRuleSetId`,
      source.scheduleRuleSetId,
      parseScheduleRuleSetId,
    ),
    scheduleRuleSetVersion: expectPositiveSafeInteger(
      source.scheduleRuleSetVersion,
      `${path}.scheduleRuleSetVersion`,
      rejectStructure,
    ),
  }
}

function resolveRuleSet(
  metadata: LeagueSnapshotV2CreationMetadata,
): SupportedScheduleRuleSetRegistration {
  const registration = findSupportedScheduleRuleSet(
    metadata.scheduleRuleSetId,
    metadata.scheduleRuleSetVersion,
  )
  if (registration !== null) return registration

  if (hasRegisteredScheduleRuleSetId(metadata.scheduleRuleSetId)) {
    throw invalid(
      'league_snapshot_v2.rule_set.unsupported_version',
      '$.creationMetadata.scheduleRuleSetVersion',
      `Schedule rule set ${metadata.scheduleRuleSetId} version ${metadata.scheduleRuleSetVersion} is not supported by this application version`,
    )
  }
  throw invalid(
    'league_snapshot_v2.rule_set.unknown_id',
    '$.creationMetadata.scheduleRuleSetId',
    `Schedule rule set ${metadata.scheduleRuleSetId} is unknown to this application version`,
  )
}

function validateSnapshotCrossObjectConsistency(
  v1: LeagueSnapshotV1,
  season: Season,
  calendar: SeasonCalendar,
  teamSeasons: readonly TeamSeason[],
  schedule: LeagueSchedule,
  metadata: LeagueSnapshotV2CreationMetadata,
  registration: SupportedScheduleRuleSetRegistration,
): void {
  const issues: LeagueSnapshotV2ValidationIssue[] = []
  const addIssue = (code: string, path: string, message: string): void => {
    issues.push({ code, path, message })
  }
  const leagueTeamIds = v1.league.teams.map(({ id }) => id)
  const leagueTeamIdSet = new Set(leagueTeamIds)

  let expectedSeasonId: SeasonId | null = null
  try {
    expectedSeasonId = deriveSeasonFoundationSeasonId(
      v1.league.id,
      metadata.startingYear,
    )
  } catch (error) {
    addIssue(
      'league_snapshot_v2.identity.season.unavailable',
      '$.season.id',
      errorMessage(error, 'Season identity could not be derived'),
    )
  }
  if (expectedSeasonId !== null && season.id !== expectedSeasonId) {
    addIssue(
      'league_snapshot_v2.identity.season.mismatch',
      '$.season.id',
      'SeasonId does not match the stored league and starting year',
    )
  }
  if (season.leagueId !== v1.league.id) {
    addIssue(
      'league_snapshot_v2.season.league_id.mismatch',
      '$.season.leagueId',
      'Season must reference the stored league',
    )
  }
  if (season.startingYear !== metadata.startingYear) {
    addIssue(
      'league_snapshot_v2.metadata.starting_year.mismatch',
      '$.creationMetadata.startingYear',
      'Creation starting year must equal the stored season starting year',
    )
  }
  const expectedEndingYear = metadata.startingYear + 1
  if (season.endingYear !== expectedEndingYear) {
    addIssue(
      'league_snapshot_v2.season.ending_year.mismatch',
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
      'league_snapshot_v2.season.display_label.invalid',
      '$.season.displayLabel',
      errorMessage(error, 'Season display label could not be derived'),
    )
  }
  if (
    expectedDisplayLabel !== null &&
    season.displayLabel !== expectedDisplayLabel
  ) {
    addIssue(
      'league_snapshot_v2.season.display_label.mismatch',
      '$.season.displayLabel',
      'Season display label does not match its stored years',
    )
  }
  if (season.rulesVersion !== metadata.scheduleRuleSetVersion) {
    addIssue(
      'league_snapshot_v2.rule_set.season_version.mismatch',
      '$.season.rulesVersion',
      'Season rules version must match creation metadata',
    )
  }
  if (season.rulesVersion !== registration.ruleSet.version) {
    addIssue(
      'league_snapshot_v2.rule_set.registry_version.mismatch',
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
    v1.league.id,
    leagueTeamIds,
    metadata,
    registration,
    addIssue,
  )

  if (issues.length > 0) {
    throw new InvalidLeagueSnapshotV2Error(issues)
  }
}

type AddCrossIssue = (code: string, path: string, message: string) => void

function validateCalendarConsistency(
  calendar: SeasonCalendar,
  season: Season,
  schedule: LeagueSchedule,
  metadata: LeagueSnapshotV2CreationMetadata,
  ruleSetStage: ScheduleStage,
  leagueTeamIds: ReadonlySet<TeamId>,
  addIssue: AddCrossIssue,
): void {
  if (calendar.seasonId !== season.id) {
    addIssue(
      'league_snapshot_v2.calendar.season_id.mismatch',
      '$.seasonCalendar.seasonId',
      'Season calendar must reference the stored season',
    )
  }
  let expectedCalendarId: SeasonCalendarId | null = null
  try {
    expectedCalendarId = deriveSeasonFoundationCalendarId(season.id)
  } catch (error) {
    addIssue(
      'league_snapshot_v2.identity.calendar.unavailable',
      '$.seasonCalendar.id',
      errorMessage(error, 'Calendar identity could not be derived'),
    )
  }
  if (expectedCalendarId !== null && calendar.id !== expectedCalendarId) {
    addIssue(
      'league_snapshot_v2.identity.calendar.mismatch',
      '$.seasonCalendar.id',
      'SeasonCalendarId does not match the stored SeasonId',
    )
  }

  for (let index = 0; index < calendar.events.length; index += 1) {
    const event = calendar.events[index]
    const path = `$.seasonCalendar.events[${index}]`
    if (event.seasonId !== season.id) {
      addIssue(
        'league_snapshot_v2.calendar.event_season_id.mismatch',
        `${path}.seasonId`,
        'Calendar event must reference the stored season',
      )
    }
    if (
      event.scope === 'team' &&
      !leagueTeamIds.has(event.teamId)
    ) {
      addIssue(
        'league_snapshot_v2.calendar.team_id.foreign',
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
          'league_snapshot_v2.calendar.boundary_scope.invalid',
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
          'league_snapshot_v2.identity.calendar_event.unavailable',
          `${path}.id`,
          errorMessage(error, 'Calendar event identity could not be derived'),
        )
      }
      if (expectedEventId !== null && event.id !== expectedEventId) {
        addIssue(
          'league_snapshot_v2.identity.calendar_event.mismatch',
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
        'league_snapshot_v2.calendar.future_event.unsupported_state',
        path,
        'This V2 foundation may preserve future calendar events only as undated pending TBA records',
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
      'league_snapshot_v2.calendar.opening.count',
      '$.seasonCalendar.events',
      'Season calendar must contain exactly one regular-season opening event',
    )
  }
  if (conclusions.length !== 1) {
    addIssue(
      'league_snapshot_v2.calendar.conclusion.count',
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
        'league_snapshot_v2.calendar.opening_date.mismatch',
        '$.seasonCalendar.events',
        'Regular-season opening must preserve the metadata and earliest original game date',
      )
    }
    if (opening.scheduledDate !== firstCurrentDate) {
      addIssue(
        'league_snapshot_v2.calendar.opening_current_date.mismatch',
        '$.seasonCalendar.events',
        'Regular-season opening current date must match the earliest currently scheduled game date',
      )
    }
    if (
      opening.actualDate !== null &&
      opening.actualDate !== firstActualDate
    ) {
      addIssue(
        'league_snapshot_v2.calendar.opening_actual_date.mismatch',
        '$.seasonCalendar.events',
        'A completed regular-season opening must match the earliest actual game date',
      )
    }
  }
  const conclusion = conclusions[0]
  if (conclusion !== undefined) {
    if (conclusion.originalScheduledDate !== latestOriginalDate) {
      addIssue(
        'league_snapshot_v2.calendar.conclusion_date.mismatch',
        '$.seasonCalendar.events',
        'Regular-season conclusion must preserve the latest original game date',
      )
    }
    if (conclusion.scheduledDate !== latestCurrentDate) {
      addIssue(
        'league_snapshot_v2.calendar.conclusion_current_date.mismatch',
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
          'league_snapshot_v2.calendar.conclusion_actual_date.mismatch',
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
      'league_snapshot_v2.team_seasons.count',
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
        'league_snapshot_v2.team_season.season_id.mismatch',
        `${path}.seasonId`,
        'Team-season record must reference the stored season',
      )
    }
    if (!leagueTeamIdSet.has(teamSeason.teamId)) {
      addIssue(
        'league_snapshot_v2.team_season.team_id.foreign',
        `${path}.teamId`,
        'Team-season record references a team outside the stored league',
      )
    }
    if (seenTeamIds.has(teamSeason.teamId)) {
      addIssue(
        'league_snapshot_v2.team_season.team_id.duplicate',
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
        'league_snapshot_v2.identity.team_season.unavailable',
        `${path}.id`,
        errorMessage(error, 'Team-season identity could not be derived'),
      )
    }
    if (expectedId !== null && teamSeason.id !== expectedId) {
      addIssue(
        'league_snapshot_v2.identity.team_season.mismatch',
        `${path}.id`,
        'TeamSeasonId does not match its SeasonId and TeamId',
      )
    }
  }
  for (const teamId of leagueTeamIds) {
    if (!seenTeamIds.has(teamId)) {
      addIssue(
        'league_snapshot_v2.team_season.team_id.missing',
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
  metadata: LeagueSnapshotV2CreationMetadata,
  registration: SupportedScheduleRuleSetRegistration,
  addIssue: AddCrossIssue,
): void {
  if (schedule.leagueId !== leagueId) {
    addIssue(
      'league_snapshot_v2.schedule.league_id.mismatch',
      '$.leagueSchedule.leagueId',
      'Schedule must reference the stored league',
    )
  }
  if (schedule.seasonId !== season.id) {
    addIssue(
      'league_snapshot_v2.schedule.season_id.mismatch',
      '$.leagueSchedule.seasonId',
      'Schedule must reference the stored season',
    )
  }
  if (season.scheduleId !== schedule.id) {
    addIssue(
      'league_snapshot_v2.schedule.id.season_mismatch',
      '$.season.scheduleId',
      'Season ScheduleId must match the stored schedule',
    )
  }
  if (
    schedule.ruleSetId !== metadata.scheduleRuleSetId ||
    schedule.ruleSetId !== registration.ruleSet.id
  ) {
    addIssue(
      'league_snapshot_v2.rule_set.id.mismatch',
      '$.leagueSchedule.ruleSetId',
      'Stored schedule and creation metadata must reference the resolved rule set',
    )
  }
  if (schedule.scheduleSeed !== metadata.scheduleSeed) {
    addIssue(
      'league_snapshot_v2.metadata.schedule_seed.mismatch',
      '$.creationMetadata.scheduleSeed',
      'Creation schedule seed must equal the stored schedule seed',
    )
  }
  if (schedule.calendarDaySpacing !== metadata.gameDaySpacing) {
    addIssue(
      'league_snapshot_v2.metadata.game_day_spacing.mismatch',
      '$.creationMetadata.gameDaySpacing',
      'Creation game-day spacing must equal the stored schedule spacing',
    )
  }
  if (
    schedule.generationVersion !== registration.scheduleGenerationVersion
  ) {
    addIssue(
      'league_snapshot_v2.schedule.generation_version.unsupported',
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
      'league_snapshot_v2.identity.schedule.unavailable',
      '$.leagueSchedule.id',
      errorMessage(error, 'Schedule identity could not be derived'),
    )
  }
  if (expectedScheduleId !== null && schedule.id !== expectedScheduleId) {
    addIssue(
      'league_snapshot_v2.identity.schedule.mismatch',
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
      `league_snapshot_v2.schedule.${violation.code}`,
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

function serializeLeague(league: League): LeagueSnapshotV2LeagueDto {
  return {
    id: league.id,
    generatorVersion: league.generatorVersion,
    seedFingerprint: league.seedFingerprint,
    teams: league.teams.map((team) => ({
      id: team.id,
      city: team.city,
      nickname: team.nickname,
      abbreviation: team.abbreviation,
      colors: {
        primary: team.colors.primary,
        secondary: team.colors.secondary,
        accent: team.colors.accent,
      },
      mark: { kind: team.mark.kind, text: team.mark.text },
    })),
    players: league.players.map((player) => ({
      id: player.id,
      teamId: player.teamId,
      firstName: player.firstName,
      lastName: player.lastName,
      age: player.age,
      jerseyNumber: player.jerseyNumber,
      primaryPosition: player.primaryPosition,
      secondaryPosition: player.secondaryPosition,
      ratingGenerationVersion: player.ratingGenerationVersion,
      ratings: { ...player.ratings },
      tendencies: { ...player.tendencies },
    })),
  }
}

function serializeSeason(season: Season): LeagueSnapshotV2SeasonDto {
  return {
    id: season.id,
    leagueId: season.leagueId,
    seasonNumber: season.seasonNumber,
    startingYear: season.startingYear,
    endingYear: season.endingYear,
    displayLabel: season.displayLabel,
    rulesVersion: season.rulesVersion,
    currentDate: season.currentDate,
    currentPhase: season.currentPhase,
    scheduleId: season.scheduleId,
    status: season.status,
  }
}

function serializeSeasonCalendar(
  calendar: SeasonCalendar,
): LeagueSnapshotV2SeasonCalendarDto {
  return {
    id: calendar.id,
    version: calendar.version,
    seasonId: calendar.seasonId,
    events: calendar.events.map((event) => ({
      id: event.id,
      version: event.version,
      seasonId: event.seasonId,
      kind: event.kind,
      scope: event.scope,
      teamId: event.scope === 'team' ? event.teamId : null,
      title: event.title,
      originalScheduledDate: event.originalScheduledDate,
      scheduledDate: event.scheduledDate,
      actualDate: event.actualDate,
      dateStatus: event.dateStatus,
      completionStatus: event.completionStatus,
    })),
  }
}

function serializeTeamSeason(
  teamSeason: TeamSeason,
): LeagueSnapshotV2TeamSeasonDto {
  return {
    id: teamSeason.id,
    version: teamSeason.version,
    seasonId: teamSeason.seasonId,
    teamId: teamSeason.teamId,
    competitiveStatus: teamSeason.competitiveStatus,
    eliminationDate: teamSeason.eliminationDate,
    teamOffseasonStartDate: teamSeason.teamOffseasonStartDate,
    postseasonSeed: teamSeason.postseasonSeed,
  }
}

function serializeLeagueSchedule(
  schedule: LeagueSchedule,
): LeagueSnapshotV2LeagueScheduleDto {
  return {
    id: schedule.id,
    leagueId: schedule.leagueId,
    seasonId: schedule.seasonId,
    ruleSetId: schedule.ruleSetId,
    generationVersion: schedule.generationVersion,
    scheduleSeed: schedule.scheduleSeed,
    calendarDaySpacing: schedule.calendarDaySpacing,
    publicationStatus: schedule.publicationStatus,
    opponentRequirements: schedule.opponentRequirements.map((requirement) => ({
      firstTeamId: requirement.firstTeamId,
      secondTeamId: requirement.secondTeamId,
      totalMeetings: requirement.totalMeetings,
      homeGamesForFirstTeam: requirement.homeGamesForFirstTeam,
      homeGamesForSecondTeam: requirement.homeGamesForSecondTeam,
      stage: requirement.stage,
      sourceTag: requirement.sourceTag ?? null,
    })),
    gameDays: schedule.gameDays.map((gameDay) => ({
      id: gameDay.id,
      seasonId: gameDay.seasonId,
      sequenceNumber: gameDay.sequenceNumber,
      scheduledDate: gameDay.scheduledDate,
      gameIds: [...gameDay.gameIds],
    })),
    games: schedule.games.map((game) => ({
      id: game.id,
      seasonId: game.seasonId,
      gameDayId: game.gameDayId,
      stage: game.stage,
      homeTeamId: game.homeTeamId,
      awayTeamId: game.awayTeamId,
      originalScheduledDate: game.originalScheduledDate,
      currentScheduledDate: game.currentScheduledDate,
      actualDate: game.actualDate ?? null,
      status: game.status,
      meetingNumber: game.meetingNumber,
    })),
  }
}

function parseCanonicalSeed(value: unknown, path: string): string {
  const seed = expectString(value, path, rejectStructure)
  return parseAtPath(path, seed, () => {
    const normalized = normalizeSeed(seed)
    if (normalized !== seed) {
      throw new RangeError(
        'Seed must already be canonical, trimmed, and NFC-normalized',
      )
    }
    return seed
  })
}

function parseNullableLocalDate(
  value: unknown,
  path: string,
): LocalDate | null {
  return value === null ? null : parseAtPath(path, value, parseLocalDate)
}

function parseNullablePositiveSafeInteger(
  value: unknown,
  path: string,
): number | null {
  return value === null
    ? null
    : expectPositiveSafeInteger(value, path, rejectStructure)
}

function parseAtPath<T>(
  path: string,
  value: unknown,
  parse: (value: unknown) => T,
): T {
  try {
    return parse(value)
  } catch (error) {
    if (error instanceof InvalidLeagueSnapshotV2Error) throw error
    throw invalid(
      'league_snapshot_v2.value.invalid',
      path,
      errorMessage(error, 'Value is invalid'),
      error,
    )
  }
}

function parseDomainAtPath<T>(
  code: string,
  path: string,
  parse: () => T,
): T {
  try {
    return parse()
  } catch (error) {
    if (error instanceof InvalidLeagueSnapshotV2Error) throw error
    const nestedIssues = getValidationIssues(error)
    if (nestedIssues.length > 0) {
      throw new InvalidLeagueSnapshotV2Error(
        nestedIssues.map((issue) => ({
          code: `${code}.${issue.code}`,
          path: prefixIssuePath(path, issue.path),
          message: issue.message,
        })),
        error,
      )
    }
    throw invalid(
      code,
      path,
      errorMessage(error, 'Domain value is invalid'),
      error,
    )
  }
}

function getValidationIssues(
  error: unknown,
): readonly LeagueSnapshotV2ValidationIssue[] {
  if (
    error === null ||
    typeof error !== 'object' ||
    !('issues' in error) ||
    !Array.isArray(error.issues)
  ) {
    return []
  }
  return error.issues.flatMap((issue) => {
    if (
      issue !== null &&
      typeof issue === 'object' &&
      'code' in issue &&
      typeof issue.code === 'string' &&
      'path' in issue &&
      typeof issue.path === 'string' &&
      'message' in issue &&
      typeof issue.message === 'string'
    ) {
      return [{ code: issue.code, path: issue.path, message: issue.message }]
    }
    return []
  })
}

function prefixIssuePath(prefix: string, issuePath: string): string {
  return issuePath === '$' ? prefix : `${prefix}${issuePath.slice(1)}`
}

function stripErrorPath(message: string, path: string): string {
  const prefix = `${path}: `
  return message.startsWith(prefix) ? message.slice(prefix.length) : message
}

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback
}

function invalid(
  code: string,
  path: string,
  message: string,
  cause?: unknown,
): InvalidLeagueSnapshotV2Error {
  return new InvalidLeagueSnapshotV2Error([{ code, path, message }], cause)
}
