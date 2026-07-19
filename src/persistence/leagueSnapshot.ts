import {
  parseSeasonFoundationConfiguration,
} from '../domain/seasonFoundation'
import type {
  SeasonFoundation,
  SeasonFoundationConfiguration,
} from '../domain/seasonFoundation'
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
import type { PlayerId, TeamId } from '../domain/ids'
import {
  LEAGUE_PLAYER_COUNT,
  LEAGUE_TEAM_COUNT,
  isPosition,
} from '../domain/league'
import type {
  League,
  Player,
  PlayerMeasurements,
  PlayerTendencies,
  Position,
  Team,
  TeamColors,
  TeamMark,
} from '../domain/league'
import { assertValidLeague } from '../domain/leagueValidation'
import { parseLocalDate } from '../domain/localDate'
import type { LocalDate } from '../domain/localDate'
import {
  CATEGORY_DEFINITION_VERSION,
  DETAILED_RATING_GENERATION_VERSION,
  DETAILED_RATINGS_SCHEMA_VERSION,
  SUB_RATING_KEYS,
  parseDetailedPlayerRatings,
} from '../domain/detailedRatings'
import type { DetailedPlayerRatings } from '../domain/detailedRatings'
import {
  SCHEDULED_GAME_STATUSES,
  SCHEDULE_PUBLICATION_STATUSES,
  SCHEDULE_STAGES,
} from '../domain/schedule'
import type {
  GameDay,
  LeagueSchedule,
  OpponentRequirement,
  ScheduledGame,
} from '../domain/schedule'
import {
  CALENDAR_COMPLETION_STATUSES,
  CALENDAR_DATE_STATUSES,
  CALENDAR_EVENT_KINDS,
  CALENDAR_EVENT_SCOPES,
  parseCalendarEvent,
  parseSeasonCalendar,
} from '../domain/seasonCalendar'
import type {
  CalendarEvent,
  SeasonCalendar,
} from '../domain/seasonCalendar'
import {
  SEASON_PHASES,
  SEASON_STATUSES,
  parseSeason,
} from '../domain/season'
import type { Season } from '../domain/season'
import {
  TEAM_COMPETITIVE_STATUSES,
  parseTeamSeason,
} from '../domain/teamSeason'
import type { TeamSeason } from '../domain/teamSeason'
import { MILESTONE_1_LEAGUE_RULES } from '../domain/leagueRules'
import {
  ROTATION_GENERATOR_VERSION,
  ROTATION_PLAN_SOURCES,
  ROTATION_REPAIR_REASONS,
  ROTATION_REPAIR_VERSION,
  validateRotationPlan,
} from '../domain/rotationPlan'
import type { RotationPlanV1 } from '../domain/rotationPlan'
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
import {
  validateSnapshotCrossObjectConsistency,
} from './leagueSnapshotConsistency'
import {
  InvalidLeagueSnapshotError,
  LEAGUE_SNAPSHOT_KIND,
  LEAGUE_SNAPSHOT_VERSION,
} from './leagueSnapshotTypes'
import type {
  LeagueSnapshot,
  LeagueSnapshotCreationMetadata,
  LeagueSnapshotLeagueDto,
  LeagueSnapshotLeagueScheduleDto,
  LeagueSnapshotRotationPlanDto,
  LeagueSnapshotSeasonCalendarDto,
  LeagueSnapshotSeasonDto,
  LeagueSnapshotTeamSeasonDto,
  LeagueSnapshotValidationIssue,
} from './leagueSnapshotTypes'

export {
  InvalidLeagueSnapshotError,
  LEAGUE_SNAPSHOT_KIND,
  LEAGUE_SNAPSHOT_VERSION,
} from './leagueSnapshotTypes'
export type {
  LeagueSnapshot,
  LeagueSnapshotCalendarEventDto,
  LeagueSnapshotCreationMetadata,
  LeagueSnapshotGameDayDto,
  LeagueSnapshotLeagueDto,
  LeagueSnapshotLeagueScheduleDto,
  LeagueSnapshotOpponentRequirementDto,
  LeagueSnapshotPlayerDto,
  LeagueSnapshotRotationPlanDto,
  LeagueSnapshotScheduledGameDto,
  LeagueSnapshotSeasonCalendarDto,
  LeagueSnapshotSeasonDto,
  LeagueSnapshotTeamDto,
  LeagueSnapshotTeamSeasonDto,
  LeagueSnapshotValidationIssue,
} from './leagueSnapshotTypes'

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
  'rotationPlans',
] as const

const ROTATION_PLAN_KEYS = [
  'version',
  'teamId',
  'starters',
  'minuteTargetsSeconds',
  'benchOrder',
  'source',
  'generation',
  'autoRepair',
] as const
const ROTATION_GENERATION_KEYS = ['generatorVersion'] as const
const ROTATION_AUTO_REPAIR_KEYS = ['repairVersion', 'reason'] as const

const LEAGUE_KEYS = [
  'id',
  'generatorVersion',
  'detailedRatingsSchemaVersion',
  'categoryDefinitionVersion',
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
  'measurements',
  'tendencies',
] as const
const MEASUREMENT_KEYS = [
  'heightInches',
  'weightPounds',
  'wingspanInches',
  'standingReachInches',
  'handSizeInches',
] as const
const TENDENCY_KEYS = [
  'usage',
  'rim',
  'midrange',
  'threePoint',
  'catchAndShoot',
  'pullUp',
  'movement',
  'drive',
  'shoot',
  'pass',
  'isolation',
  'pickAndRoll',
  'rollPop',
  'postUp',
  'cutRelocate',
  'transition',
  'contactSeeking',
  'offensiveReboundCrash',
  'stealAggression',
  'blockAggression',
  'passingRisk',
  'pacePreference',
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
  const rotationPlans = parseRotationPlansDto(
    source.rotationPlans,
    '$.rotationPlans',
    leagueFields.league,
  )

  validateSnapshotCrossObjectConsistency(
    leagueFields.league,
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
    rotationPlans,
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
    // A new league saves no rotation plans; the editor generates a default on
    // demand and persists only what the user saves.
    rotationPlans: [],
  }
}

/**
 * Converts a domain rotation plan to its stored DTO (optional metadata becomes
 * an explicit null key, since a stored record has an exact key set).
 */
export function rotationPlanToSnapshotDto(
  plan: RotationPlanV1,
): LeagueSnapshotRotationPlanDto {
  return {
    version: 1,
    teamId: plan.teamId,
    starters: [...plan.starters],
    minuteTargetsSeconds: { ...plan.minuteTargetsSeconds },
    benchOrder: [...plan.benchOrder],
    source: plan.source,
    generation:
      plan.generation === undefined
        ? null
        : { generatorVersion: plan.generation.generatorVersion },
    autoRepair:
      plan.autoRepair === undefined
        ? null
        : {
            repairVersion: plan.autoRepair.repairVersion,
            reason: plan.autoRepair.reason,
          },
  }
}

/** Converts a stored rotation-plan DTO back to the domain shape (null → absent). */
export function rotationPlanFromSnapshotDto(
  dto: LeagueSnapshotRotationPlanDto,
): RotationPlanV1 {
  return {
    version: 1,
    teamId: dto.teamId,
    starters: dto.starters,
    minuteTargetsSeconds: dto.minuteTargetsSeconds,
    benchOrder: dto.benchOrder,
    source: dto.source,
    ...(dto.generation === null ? {} : { generation: dto.generation }),
    ...(dto.autoRepair === null ? {} : { autoRepair: dto.autoRepair }),
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
    2,
    `${path}.generatorVersion`,
    rejectStructure,
  )
  expectLiteral(
    source.detailedRatingsSchemaVersion,
    DETAILED_RATINGS_SCHEMA_VERSION,
    `${path}.detailedRatingsSchemaVersion`,
    rejectStructure,
  )
  expectLiteral(
    source.categoryDefinitionVersion,
    CATEGORY_DEFINITION_VERSION,
    `${path}.categoryDefinitionVersion`,
    rejectStructure,
  )
  const league: League = {
    id: parseAtPath(`${path}.id`, source.id, parseLeagueId),
    generatorVersion: 2,
    detailedRatingsSchemaVersion: DETAILED_RATINGS_SCHEMA_VERSION,
    categoryDefinitionVersion: CATEGORY_DEFINITION_VERSION,
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
    DETAILED_RATING_GENERATION_VERSION,
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
    ratingGenerationVersion: DETAILED_RATING_GENERATION_VERSION,
    ratings: parseRatingsDto(source.ratings, `${path}.ratings`),
    measurements: parseMeasurementsDto(
      source.measurements,
      `${path}.measurements`,
    ),
    tendencies: parseTendenciesDto(source.tendencies, `${path}.tendencies`),
  }
}

function parseRatingsDto(value: unknown, path: string): DetailedPlayerRatings {
  expectExactRecord(value, SUB_RATING_KEYS, path, rejectStructure)
  return parseAtPath(path, value, parseDetailedPlayerRatings)
}

function parseMeasurementsDto(value: unknown, path: string): PlayerMeasurements {
  const source = expectExactRecord(
    value,
    MEASUREMENT_KEYS,
    path,
    rejectStructure,
  )
  return {
    heightInches: expectSafeInteger(
      source.heightInches,
      `${path}.heightInches`,
      rejectStructure,
    ),
    weightPounds: expectSafeInteger(
      source.weightPounds,
      `${path}.weightPounds`,
      rejectStructure,
    ),
    wingspanInches: expectSafeInteger(
      source.wingspanInches,
      `${path}.wingspanInches`,
      rejectStructure,
    ),
    standingReachInches: expectSafeInteger(
      source.standingReachInches,
      `${path}.standingReachInches`,
      rejectStructure,
    ),
    handSizeInches: expectSafeInteger(
      source.handSizeInches,
      `${path}.handSizeInches`,
      rejectStructure,
    ),
  }
}

function parseTendenciesDto(value: unknown, path: string): PlayerTendencies {
  const source = expectExactRecord(value, TENDENCY_KEYS, path, rejectStructure)
  const tendency = (key: (typeof TENDENCY_KEYS)[number]): number =>
    expectSafeInteger(source[key], `${path}.${key}`, rejectStructure)
  return {
    usage: tendency('usage'),
    rim: tendency('rim'),
    midrange: tendency('midrange'),
    threePoint: tendency('threePoint'),
    catchAndShoot: tendency('catchAndShoot'),
    pullUp: tendency('pullUp'),
    movement: tendency('movement'),
    drive: tendency('drive'),
    shoot: tendency('shoot'),
    pass: tendency('pass'),
    isolation: tendency('isolation'),
    pickAndRoll: tendency('pickAndRoll'),
    rollPop: tendency('rollPop'),
    postUp: tendency('postUp'),
    cutRelocate: tendency('cutRelocate'),
    transition: tendency('transition'),
    contactSeeking: tendency('contactSeeking'),
    offensiveReboundCrash: tendency('offensiveReboundCrash'),
    stealAggression: tendency('stealAggression'),
    blockAggression: tendency('blockAggression'),
    passingRisk: tendency('passingRisk'),
    pacePreference: tendency('pacePreference'),
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

function parseRotationPlansDto(
  value: unknown,
  path: string,
  league: League,
): readonly LeagueSnapshotRotationPlanDto[] {
  const plans = parseDenseArray(
    value,
    path,
    (item, itemPath) => parseRotationPlanDto(item, itemPath, league),
    rejectStructure,
  )
  const seenTeams = new Set<string>()
  plans.forEach((plan, index) => {
    if (seenTeams.has(plan.teamId)) {
      throw invalid(
        'league_snapshot.rotation_plan.duplicate_team',
        `${path}[${index}].teamId`,
        'Only one rotation plan is allowed per team',
      )
    }
    seenTeams.add(plan.teamId)
  })
  return plans
}

function parseRotationPlanDto(
  value: unknown,
  path: string,
  league: League,
): LeagueSnapshotRotationPlanDto {
  const source = expectExactRecord(
    value,
    ROTATION_PLAN_KEYS,
    path,
    rejectStructure,
  )
  expectLiteral(source.version, 1, `${path}.version`, rejectStructure)
  const teamId = parseAtPath(`${path}.teamId`, source.teamId, parseTeamId)
  if (!league.teams.some((team) => team.id === teamId)) {
    throw invalid(
      'league_snapshot.rotation_plan.unknown_team',
      `${path}.teamId`,
      'A rotation plan must reference a team in the league',
    )
  }

  const dto: LeagueSnapshotRotationPlanDto = {
    version: 1,
    teamId,
    starters: parseDenseArray(
      source.starters,
      `${path}.starters`,
      (id, idPath) => parseAtPath(idPath, id, parsePlayerId),
      rejectStructure,
    ),
    minuteTargetsSeconds: parseMinuteTargetsRecord(
      source.minuteTargetsSeconds,
      `${path}.minuteTargetsSeconds`,
    ),
    benchOrder: parseDenseArray(
      source.benchOrder,
      `${path}.benchOrder`,
      (id, idPath) => parseAtPath(idPath, id, parsePlayerId),
      rejectStructure,
    ),
    source: expectOneOf(
      source.source,
      ROTATION_PLAN_SOURCES,
      `${path}.source`,
      rejectStructure,
    ),
    generation: parseRotationGenerationDto(
      source.generation,
      `${path}.generation`,
    ),
    autoRepair: parseRotationAutoRepairDto(
      source.autoRepair,
      `${path}.autoRepair`,
    ),
  }

  const teamPlayers = league.players.filter(
    (player) => player.teamId === teamId,
  )
  const { errors } = validateRotationPlan(
    rotationPlanFromSnapshotDto(dto),
    teamPlayers,
    MILESTONE_1_LEAGUE_RULES,
  )
  const firstError = errors[0]
  if (firstError !== undefined) {
    throw invalid(
      'league_snapshot.rotation_plan.invalid',
      `${path}.${firstError.path}`,
      firstError.message,
    )
  }
  return dto
}

function parseMinuteTargetsRecord(
  value: unknown,
  path: string,
): Readonly<Record<PlayerId, number>> {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    throw invalid(
      'league_snapshot.structure.invalid',
      path,
      'Expected a minute-targets record',
    )
  }
  const record: Record<string, number> = {}
  for (const key of Object.keys(value)) {
    const keyPath = `${path}.${key}`
    const playerId = parseAtPath(keyPath, key, parsePlayerId)
    record[playerId] = expectSafeInteger(
      (value as Record<string, unknown>)[key],
      keyPath,
      rejectStructure,
    )
  }
  return record as Readonly<Record<PlayerId, number>>
}

function parseRotationGenerationDto(
  value: unknown,
  path: string,
): LeagueSnapshotRotationPlanDto['generation'] {
  if (value === null) {
    return null
  }
  const source = expectExactRecord(
    value,
    ROTATION_GENERATION_KEYS,
    path,
    rejectStructure,
  )
  return {
    generatorVersion: expectLiteral(
      source.generatorVersion,
      ROTATION_GENERATOR_VERSION,
      `${path}.generatorVersion`,
      rejectStructure,
    ),
  }
}

function parseRotationAutoRepairDto(
  value: unknown,
  path: string,
): LeagueSnapshotRotationPlanDto['autoRepair'] {
  if (value === null) {
    return null
  }
  const source = expectExactRecord(
    value,
    ROTATION_AUTO_REPAIR_KEYS,
    path,
    rejectStructure,
  )
  return {
    repairVersion: expectLiteral(
      source.repairVersion,
      ROTATION_REPAIR_VERSION,
      `${path}.repairVersion`,
      rejectStructure,
    ),
    reason: expectOneOf(
      source.reason,
      ROTATION_REPAIR_REASONS,
      `${path}.reason`,
      rejectStructure,
    ),
  }
}

function serializeLeague(league: League): LeagueSnapshotLeagueDto {
  return {
    id: league.id,
    generatorVersion: league.generatorVersion,
    detailedRatingsSchemaVersion: league.detailedRatingsSchemaVersion,
    categoryDefinitionVersion: league.categoryDefinitionVersion,
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
      measurements: { ...player.measurements },
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
