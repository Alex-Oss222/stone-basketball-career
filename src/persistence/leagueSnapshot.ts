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
  parsePlayerId,
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
import { assertValidLeague } from '../domain/leagueValidation'
import {
  compareLocalDates,
  formatSeasonLabel,
  parseLocalDate,
} from '../domain/localDate'
import type { LocalDate } from '../domain/localDate'
import {
  RATING_GENERATION_VERSION,
  RATING_KEYS,
  parsePlayerRatings,
} from '../domain/ratings'
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

export const LEAGUE_SNAPSHOT_KIND =
  'stone-basketball-gm-league-snapshot' as const

/**
 * The one current snapshot version. Deliberately monotonic — versions 1 and 2
 * shipped to local browser storage during development and must be refused,
 * never mis-parsed, so this constant never resets.
 */
export const LEAGUE_SNAPSHOT_VERSION = 3 as const

export interface LeagueSnapshotTeamDto {
  readonly id: TeamId
  readonly city: string
  readonly nickname: string
  readonly abbreviation: string
  readonly colors: TeamColors
  readonly mark: TeamMark
}

export interface LeagueSnapshotPlayerDto {
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

export interface LeagueSnapshotLeagueDto {
  readonly id: LeagueId
  readonly generatorVersion: 1
  readonly seedFingerprint: string
  readonly teams: readonly LeagueSnapshotTeamDto[]
  readonly players: readonly LeagueSnapshotPlayerDto[]
}

export interface LeagueSnapshotSeasonDto {
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

export interface LeagueSnapshotCalendarEventDto {
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

export interface LeagueSnapshotSeasonCalendarDto {
  readonly id: SeasonCalendarId
  readonly version: 1
  readonly seasonId: SeasonId
  readonly events: readonly LeagueSnapshotCalendarEventDto[]
}

export interface LeagueSnapshotTeamSeasonDto {
  readonly id: TeamSeasonId
  readonly version: 1
  readonly seasonId: SeasonId
  readonly teamId: TeamId
  readonly competitiveStatus: TeamCompetitiveStatus
  readonly eliminationDate: LocalDate | null
  readonly teamOffseasonStartDate: LocalDate | null
  readonly postseasonSeed: number | null
}

export interface LeagueSnapshotOpponentRequirementDto {
  readonly firstTeamId: TeamId
  readonly secondTeamId: TeamId
  readonly totalMeetings: number
  readonly homeGamesForFirstTeam: number
  readonly homeGamesForSecondTeam: number
  readonly stage: ScheduleStage
  readonly sourceTag: string | null
}

export interface LeagueSnapshotGameDayDto {
  readonly id: GameDayId
  readonly seasonId: SeasonId
  readonly sequenceNumber: number
  readonly scheduledDate: LocalDate
  readonly gameIds: readonly GameId[]
}

export interface LeagueSnapshotScheduledGameDto {
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

export interface LeagueSnapshotLeagueScheduleDto {
  readonly id: ScheduleId
  readonly leagueId: LeagueId
  readonly seasonId: SeasonId
  readonly ruleSetId: ScheduleRuleSetId
  readonly generationVersion: number
  readonly scheduleSeed: string
  readonly calendarDaySpacing: number
  readonly publicationStatus: SchedulePublicationStatus
  readonly opponentRequirements: readonly LeagueSnapshotOpponentRequirementDto[]
  readonly gameDays: readonly LeagueSnapshotGameDayDto[]
  readonly games: readonly LeagueSnapshotScheduledGameDto[]
}

export interface LeagueSnapshotCreationMetadata {
  readonly startingYear: number
  readonly regularSeasonStartDate: LocalDate
  readonly gameDaySpacing: number
  readonly scheduleSeed: string
  readonly scheduleRuleSetId: ScheduleRuleSetId
  readonly scheduleRuleSetVersion: number
}

export interface LeagueSnapshot {
  readonly kind: typeof LEAGUE_SNAPSHOT_KIND
  readonly snapshotVersion: typeof LEAGUE_SNAPSHOT_VERSION
  readonly revision: number
  readonly rootSeed: string
  readonly managedTeamId: TeamId | null
  readonly league: LeagueSnapshotLeagueDto
  readonly season: LeagueSnapshotSeasonDto
  readonly seasonCalendar: LeagueSnapshotSeasonCalendarDto
  readonly teamSeasons: readonly LeagueSnapshotTeamSeasonDto[]
  readonly leagueSchedule: LeagueSnapshotLeagueScheduleDto
  readonly creationMetadata: LeagueSnapshotCreationMetadata
}

export interface LeagueSnapshotValidationIssue {
  readonly code: string
  readonly path: string
  readonly message: string
}

export class InvalidLeagueSnapshotError extends Error {
  readonly path: string
  readonly issues: readonly LeagueSnapshotValidationIssue[]

  constructor(
    issues: readonly LeagueSnapshotValidationIssue[],
    cause?: unknown,
  ) {
    const firstIssue = issues[0] ?? {
      code: 'league_snapshot.invalid',
      path: '$',
      message: 'League snapshot is invalid',
    }
    super(
      `${firstIssue.path}: ${firstIssue.message}`,
      cause === undefined ? undefined : { cause },
    )
    this.name = 'InvalidLeagueSnapshotError'
    this.path = firstIssue.path
    this.issues = Object.freeze(issues.map((issue) => Object.freeze({ ...issue })))
  }
}

export interface SerializeLeagueSnapshotInput {
  readonly rootSeed: string
  readonly managedTeamId: TeamId | null
  readonly league: League
  readonly foundation: SeasonFoundation
  readonly creationInputs: SeasonFoundationConfiguration
}

interface ParsedSchedule {
  readonly domain: LeagueSchedule
  readonly dto: LeagueSnapshotLeagueScheduleDto
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
  throw invalid('league_snapshot.structure.invalid', path, message)
}

/**
 * Strictly parses and cross-validates a detached JSON-safe snapshot DTO. This
 * normal restoration path never calls league, season, calendar, team-season,
 * opponent, or schedule generation.
 */
export function parseLeagueSnapshot(value: unknown): LeagueSnapshot {
  try {
    assertJsonSafeValue(value, '$', rejectStructure)
  } catch (error) {
    if (error instanceof InvalidLeagueSnapshotError) throw error
    throw invalid(
      'league_snapshot.structure.invalid',
      '$',
      errorMessage(error, 'Snapshot is not JSON-safe'),
      error,
    )
  }

  const source = expectExactRecord(value, TOP_LEVEL_KEYS, '$', rejectStructure)
  expectLiteral(source.kind, LEAGUE_SNAPSHOT_KIND, '$.kind', rejectStructure)
  expectLiteral(
    source.snapshotVersion,
    LEAGUE_SNAPSHOT_VERSION,
    '$.snapshotVersion',
    rejectStructure,
  )
  const revision = expectPositiveSafeInteger(
    source.revision,
    '$.revision',
    rejectStructure,
  )

  const leagueFields = parseLeagueFields(source)
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
    leagueFields,
    season,
    seasonCalendar,
    teamSeasons,
    parsedSchedule.domain,
    creationMetadata,
    registration,
  )

  return {
    kind: LEAGUE_SNAPSHOT_KIND,
    snapshotVersion: LEAGUE_SNAPSHOT_VERSION,
    revision,
    rootSeed: leagueFields.rootSeed,
    managedTeamId: leagueFields.managedTeamId,
    league: serializeLeague(leagueFields.league),
    season: serializeSeason(season),
    seasonCalendar: serializeSeasonCalendar(seasonCalendar),
    teamSeasons: teamSeasons.map(serializeTeamSeason),
    leagueSchedule: parsedSchedule.dto,
    creationMetadata,
  }
}

/**
 * Serializes already-created domain values into the exact snapshot DTO shape.
 * The caller must pass the result through parseLeagueSnapshot before trusting
 * or storing it.
 */
export function serializeLeagueSnapshot(
  input: SerializeLeagueSnapshotInput,
): LeagueSnapshot {
  const { foundation } = input
  return {
    kind: LEAGUE_SNAPSHOT_KIND,
    snapshotVersion: LEAGUE_SNAPSHOT_VERSION,
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

interface ParsedLeagueFields {
  readonly rootSeed: string
  readonly league: League
  readonly managedTeamId: TeamId | null
}

function parseLeagueFields(source: SerializedRecord): ParsedLeagueFields {
  const rootSeed = parseCanonicalSeed(source.rootSeed, '$.rootSeed')
  const league = parseLeagueDto(source.league, '$.league')
  const managedTeamId = parseManagedTeamId(
    source.managedTeamId,
    league,
    '$.managedTeamId',
  )
  return { rootSeed, league, managedTeamId }
}

function parseLeagueDto(value: unknown, path: string): League {
  const source = expectExactRecord(value, LEAGUE_KEYS, path, rejectStructure)
  expectLiteral(
    source.generatorVersion,
    1,
    `${path}.generatorVersion`,
    rejectStructure,
  )
  const league: League = {
    id: parseAtPath(`${path}.id`, source.id, parseLeagueId),
    generatorVersion: 1,
    seedFingerprint: expectString(
      source.seedFingerprint,
      `${path}.seedFingerprint`,
      rejectStructure,
    ),
    teams: parseExactCountArray(
      source.teams,
      LEAGUE_TEAM_COUNT,
      `${path}.teams`,
      parseTeamDto,
    ),
    players: parseExactCountArray(
      source.players,
      LEAGUE_PLAYER_COUNT,
      `${path}.players`,
      parsePlayerDto,
    ),
  }
  return parseDomainAtPath('league_snapshot.league.invalid', path, () => {
    assertValidLeague(league)
    return league
  })
}

function parseTeamDto(value: unknown, path: string): Team {
  const source = expectExactRecord(value, TEAM_KEYS, path, rejectStructure)
  return {
    id: parseAtPath(`${path}.id`, source.id, parseTeamId),
    city: expectString(source.city, `${path}.city`, rejectStructure),
    nickname: expectString(
      source.nickname,
      `${path}.nickname`,
      rejectStructure,
    ),
    abbreviation: expectString(
      source.abbreviation,
      `${path}.abbreviation`,
      rejectStructure,
    ),
    colors: parseTeamColorsDto(source.colors, `${path}.colors`),
    mark: parseTeamMarkDto(source.mark, `${path}.mark`),
  }
}

function parseTeamColorsDto(value: unknown, path: string): TeamColors {
  const source = expectExactRecord(
    value,
    TEAM_COLOR_KEYS,
    path,
    rejectStructure,
  )
  return {
    primary: expectString(source.primary, `${path}.primary`, rejectStructure),
    secondary: expectString(
      source.secondary,
      `${path}.secondary`,
      rejectStructure,
    ),
    accent: expectString(source.accent, `${path}.accent`, rejectStructure),
  }
}

function parseTeamMarkDto(value: unknown, path: string): TeamMark {
  const source = expectExactRecord(value, TEAM_MARK_KEYS, path, rejectStructure)
  expectLiteral(source.kind, 'initials', `${path}.kind`, rejectStructure)
  return {
    kind: 'initials',
    text: expectString(source.text, `${path}.text`, rejectStructure),
  }
}

function parsePlayerDto(value: unknown, path: string): Player {
  const source = expectExactRecord(value, PLAYER_KEYS, path, rejectStructure)
  expectLiteral(
    source.ratingGenerationVersion,
    RATING_GENERATION_VERSION,
    `${path}.ratingGenerationVersion`,
    rejectStructure,
  )
  return {
    id: parseAtPath(`${path}.id`, source.id, parsePlayerId),
    teamId: parseAtPath(`${path}.teamId`, source.teamId, parseTeamId),
    firstName: expectString(
      source.firstName,
      `${path}.firstName`,
      rejectStructure,
    ),
    lastName: expectString(
      source.lastName,
      `${path}.lastName`,
      rejectStructure,
    ),
    age: expectSafeInteger(source.age, `${path}.age`, rejectStructure),
    jerseyNumber: expectSafeInteger(
      source.jerseyNumber,
      `${path}.jerseyNumber`,
      rejectStructure,
    ),
    primaryPosition: parsePositionDto(
      source.primaryPosition,
      `${path}.primaryPosition`,
    ),
    secondaryPosition:
      source.secondaryPosition === null
        ? null
        : parsePositionDto(
            source.secondaryPosition,
            `${path}.secondaryPosition`,
          ),
    ratingGenerationVersion: RATING_GENERATION_VERSION,
    ratings: parseRatingsDto(source.ratings, `${path}.ratings`),
    tendencies: parseTendenciesDto(source.tendencies, `${path}.tendencies`),
  }
}

function parseRatingsDto(value: unknown, path: string): PlayerRatings {
  expectExactRecord(value, RATING_KEYS, path, rejectStructure)
  return parseAtPath(path, value, parsePlayerRatings)
}

function parseTendenciesDto(value: unknown, path: string): PlayerTendencies {
  const source = expectExactRecord(value, TENDENCY_KEYS, path, rejectStructure)
  return {
    usage: expectSafeInteger(source.usage, `${path}.usage`, rejectStructure),
    rim: expectSafeInteger(source.rim, `${path}.rim`, rejectStructure),
    midrange: expectSafeInteger(
      source.midrange,
      `${path}.midrange`,
      rejectStructure,
    ),
    threePoint: expectSafeInteger(
      source.threePoint,
      `${path}.threePoint`,
      rejectStructure,
    ),
    pass: expectSafeInteger(source.pass, `${path}.pass`, rejectStructure),
    drawFoul: expectSafeInteger(
      source.drawFoul,
      `${path}.drawFoul`,
      rejectStructure,
    ),
  }
}

function parsePositionDto(value: unknown, path: string): Position {
  if (!isPosition(value)) {
    throw invalid(
      'league_snapshot.structure.invalid',
      path,
      'Position must be PG, SG, SF, PF, or C',
    )
  }
  return value
}

function parseManagedTeamId(
  value: unknown,
  league: League,
  path: string,
): TeamId | null {
  if (value === null) return null

  const teamId = parseAtPath(path, value, parseTeamId)
  const matchingTeams = league.teams.filter((team) => team.id === teamId)
  if (matchingTeams.length !== 1) {
    throw invalid(
      'league_snapshot.league.invalid',
      path,
      'Managed team ID must reference one league team',
    )
  }
  return teamId
}

function parseExactCountArray<T>(
  value: unknown,
  expectedLength: number,
  path: string,
  parseItem: (item: unknown, itemPath: string) => T,
): readonly T[] {
  if (Array.isArray(value) && value.length !== expectedLength) {
    throw invalid(
      'league_snapshot.structure.invalid',
      path,
      `Array must contain exactly ${expectedLength} items`,
    )
  }
  return parseDenseArray(value, path, parseItem, rejectStructure)
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
    'league_snapshot.season.invalid',
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
    'league_snapshot.calendar.invalid',
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
      'league_snapshot.calendar.team_id.required',
      `${path}.teamId`,
      'A team-scoped event requires a TeamId',
    )
  }
  if (scope === 'league' && teamId !== null) {
    throw invalid(
      'league_snapshot.calendar.team_id.forbidden',
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
    'league_snapshot.calendar_event.invalid',
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
    'league_snapshot.team_season.invalid',
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
      'league_snapshot.schedule.requirement_numeric.invalid',
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
): LeagueSnapshotCreationMetadata {
  const source = expectExactRecord(
    value,
    CREATION_METADATA_KEYS,
    path,
    rejectStructure,
  )
  const configuration = parseDomainAtPath(
    'league_snapshot.creation_metadata.invalid',
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
  metadata: LeagueSnapshotCreationMetadata,
): SupportedScheduleRuleSetRegistration {
  const registration = findSupportedScheduleRuleSet(
    metadata.scheduleRuleSetId,
    metadata.scheduleRuleSetVersion,
  )
  if (registration !== null) return registration

  if (hasRegisteredScheduleRuleSetId(metadata.scheduleRuleSetId)) {
    throw invalid(
      'league_snapshot.rule_set.unsupported_version',
      '$.creationMetadata.scheduleRuleSetVersion',
      `Schedule rule set ${metadata.scheduleRuleSetId} version ${metadata.scheduleRuleSetVersion} is not supported by this application version`,
    )
  }
  throw invalid(
    'league_snapshot.rule_set.unknown_id',
    '$.creationMetadata.scheduleRuleSetId',
    `Schedule rule set ${metadata.scheduleRuleSetId} is unknown to this application version`,
  )
}

function validateSnapshotCrossObjectConsistency(
  leagueFields: ParsedLeagueFields,
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
  const leagueTeamIds = leagueFields.league.teams.map(({ id }) => id)
  const leagueTeamIdSet = new Set(leagueTeamIds)

  let expectedSeasonId: SeasonId | null = null
  try {
    expectedSeasonId = deriveSeasonFoundationSeasonId(
      leagueFields.league.id,
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
  if (season.leagueId !== leagueFields.league.id) {
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
    leagueFields.league.id,
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

function serializeLeague(league: League): LeagueSnapshotLeagueDto {
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

function serializeSeason(season: Season): LeagueSnapshotSeasonDto {
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
): LeagueSnapshotSeasonCalendarDto {
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
): LeagueSnapshotTeamSeasonDto {
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
): LeagueSnapshotLeagueScheduleDto {
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
    if (error instanceof InvalidLeagueSnapshotError) throw error
    throw invalid(
      'league_snapshot.value.invalid',
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
    if (error instanceof InvalidLeagueSnapshotError) throw error
    const nestedIssues = getValidationIssues(error)
    if (nestedIssues.length > 0) {
      throw new InvalidLeagueSnapshotError(
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
): readonly LeagueSnapshotValidationIssue[] {
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

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback
}

function invalid(
  code: string,
  path: string,
  message: string,
  cause?: unknown,
): InvalidLeagueSnapshotError {
  return new InvalidLeagueSnapshotError([{ code, path, message }], cause)
}
