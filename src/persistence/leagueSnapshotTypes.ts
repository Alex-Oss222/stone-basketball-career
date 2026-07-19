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
  PlayerMeasurements,
  PlayerTendencies,
  Position,
  TeamColors,
  TeamMark,
} from '../domain/league'
import type { LocalDate } from '../domain/localDate'
import type {
  CATEGORY_DEFINITION_VERSION,
  DETAILED_RATING_GENERATION_VERSION,
  DETAILED_RATINGS_SCHEMA_VERSION,
  DetailedPlayerRatings,
} from '../domain/detailedRatings'
import type {
  SchedulePublicationStatus,
  ScheduleStage,
  ScheduledGameStatus,
} from '../domain/schedule'
import type {
  CalendarCompletionStatus,
  CalendarDateStatus,
  CalendarEventKind,
  CalendarEventScope,
} from '../domain/seasonCalendar'
import type {
  SeasonPhase,
  SeasonStatus,
} from '../domain/season'
import type {
  RotationPlanSource,
  RotationRepairReason,
  ROTATION_GENERATOR_VERSION,
  ROTATION_REPAIR_VERSION,
} from '../domain/rotationPlan'
import type { TeamCompetitiveStatus } from '../domain/teamSeason'

export const LEAGUE_SNAPSHOT_KIND =
  'stone-basketball-gm-league-snapshot' as const

/**
 * The one current snapshot version. Deliberately monotonic — versions 1–5
 * shipped to local browser storage during development and must be refused,
 * never mis-parsed, so this constant never resets. Version 5 was the ADR 0009
 * ratings rehaul; version 6 (§8) adds the stored per-team `rotationPlans`. Per
 * §7 there is no migration — an old record offers "start a new league."
 */
export const LEAGUE_SNAPSHOT_VERSION = 6 as const

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
  readonly ratingGenerationVersion: typeof DETAILED_RATING_GENERATION_VERSION
  readonly ratings: DetailedPlayerRatings
  readonly measurements: PlayerMeasurements
  readonly tendencies: PlayerTendencies
}

export interface LeagueSnapshotLeagueDto {
  readonly id: LeagueId
  readonly generatorVersion: 2
  readonly detailedRatingsSchemaVersion: typeof DETAILED_RATINGS_SCHEMA_VERSION
  readonly categoryDefinitionVersion: typeof CATEGORY_DEFINITION_VERSION
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

/**
 * A stored §8 rotation plan (one per team, at most). Mirrors the domain
 * `RotationPlanV1` but keeps the optional generation/repair metadata as
 * always-present nullable keys, since a stored record has an exact key set and
 * JSON cannot carry `undefined`. Minutes are integer seconds keyed by player.
 */
export interface LeagueSnapshotRotationPlanDto {
  readonly version: 1
  readonly teamId: TeamId
  readonly starters: readonly PlayerId[]
  readonly minuteTargetsSeconds: Readonly<Record<PlayerId, number>>
  readonly benchOrder: readonly PlayerId[]
  readonly source: RotationPlanSource
  readonly generation: {
    readonly generatorVersion: typeof ROTATION_GENERATOR_VERSION
  } | null
  readonly autoRepair: {
    readonly repairVersion: typeof ROTATION_REPAIR_VERSION
    readonly reason: RotationRepairReason
  } | null
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
  /** Saved per-team rotation plans (§8); empty until a plan is saved. */
  readonly rotationPlans: readonly LeagueSnapshotRotationPlanDto[]
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
