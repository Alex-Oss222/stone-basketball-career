import type {
  GameDayId,
  GameId,
  ScheduleId,
  ScheduleRuleSetId,
  SeasonId,
  TeamId,
} from './ids'
import { parseScheduleRuleSetId } from './ids'
import type { LocalDate } from './localDate'

export const SCHEDULE_STAGES = [
  'preseason',
  'regular_season',
  'cup',
  'play_in',
  'postseason',
] as const

export type ScheduleStage = (typeof SCHEDULE_STAGES)[number]

export const SCHEDULE_PUBLICATION_STATUSES = [
  'draft',
  'published',
  'in_progress',
  'complete',
] as const

export type SchedulePublicationStatus =
  (typeof SCHEDULE_PUBLICATION_STATUSES)[number]

export const SCHEDULED_GAME_STATUSES = [
  'scheduled',
  'postponed',
  'completed',
  'cancelled',
] as const

export type ScheduledGameStatus = (typeof SCHEDULED_GAME_STATUSES)[number]

export type SupportedTeamCountPolicy =
  | {
      readonly kind: 'exact'
      readonly count: number
    }
  | {
      readonly kind: 'range'
      readonly minimum: number
      readonly maximum: number | null
    }
  | {
      readonly kind: 'allowed_counts'
      readonly counts: readonly number[]
    }

/**
 * Describes how opponent requirements are supplied without making the generic
 * schedule model assume that every competition is an equal round robin.
 */
export type OpponentRequirementPolicy =
  | {
      readonly kind: 'uniform_round_robin'
      readonly meetingsPerOpponent: number
      readonly homeGamesPerOpponent: number
      readonly awayGamesPerOpponent: number
      readonly sourceTag?: string
    }
  | {
      readonly kind: 'explicit_matrix'
      readonly requirements: readonly OpponentRequirement[]
      readonly sourceTag?: string
    }

export interface CalendarSpacingRules {
  readonly minimumDaysBetweenGameDays: number
  readonly maximumDaysBetweenGameDays: number | null
}

/** Generic, versioned inputs and invariants for one schedule stage. */
export interface ScheduleRuleSet {
  readonly id: ScheduleRuleSetId
  readonly version: number
  readonly stage: ScheduleStage
  readonly teamCountPolicy: SupportedTeamCountPolicy
  readonly gamesPerTeam: number
  readonly expectedTotalGames: number
  readonly opponentPolicy: OpponentRequirementPolicy
  readonly expectedHomeGamesPerTeam: number
  readonly expectedAwayGamesPerTeam: number
  readonly gameDayCount: number
  readonly expectedGamesPerGameDay: number
  readonly everyTeamPlaysEachGameDay: boolean
  readonly allowsTbdOpponents: boolean
  readonly calendarSpacingRules: CalendarSpacingRules
}

export const MILESTONE_1_REGULAR_SEASON_RULE_SET_ID =
  parseScheduleRuleSetId('schedule_rule_milestone_1_regular_season_v1')

export const MILESTONE_1_REGULAR_SEASON_RULE_SET_VERSION = 1 as const

export const MILESTONE_1_REGULAR_SEASON_RULE_SET: ScheduleRuleSet =
  Object.freeze({
    id: MILESTONE_1_REGULAR_SEASON_RULE_SET_ID,
    version: MILESTONE_1_REGULAR_SEASON_RULE_SET_VERSION,
    stage: 'regular_season',
    teamCountPolicy: Object.freeze({ kind: 'exact', count: 8 }),
    gamesPerTeam: 28,
    expectedTotalGames: 112,
    opponentPolicy: Object.freeze({
      kind: 'uniform_round_robin',
      meetingsPerOpponent: 4,
      homeGamesPerOpponent: 2,
      awayGamesPerOpponent: 2,
      sourceTag: 'milestone_1_equal_round_robin',
    }),
    expectedHomeGamesPerTeam: 14,
    expectedAwayGamesPerTeam: 14,
    gameDayCount: 28,
    expectedGamesPerGameDay: 4,
    everyTeamPlaysEachGameDay: true,
    allowsTbdOpponents: false,
    calendarSpacingRules: Object.freeze({
      minimumDaysBetweenGameDays: 1,
      maximumDaysBetweenGameDays: null,
    }),
  })

export interface CanonicalTeamPair {
  readonly firstTeamId: TeamId
  readonly secondTeamId: TeamId
}

export interface OpponentRequirement extends CanonicalTeamPair {
  readonly totalMeetings: number
  readonly homeGamesForFirstTeam: number
  readonly homeGamesForSecondTeam: number
  readonly stage: ScheduleStage
  readonly sourceTag?: string
}

export function getCanonicalTeamPair(
  teamAId: TeamId,
  teamBId: TeamId,
): CanonicalTeamPair {
  if (teamAId === teamBId) {
    throw new RangeError('An opponent pair must contain two different teams')
  }

  const [firstTeamId, secondTeamId] =
    teamAId < teamBId ? [teamAId, teamBId] : [teamBId, teamAId]

  return Object.freeze({ firstTeamId, secondTeamId })
}

export function getTeamPairKey(teamAId: TeamId, teamBId: TeamId): string {
  const pair = getCanonicalTeamPair(teamAId, teamBId)
  return `${pair.firstTeamId}:${pair.secondTeamId}`
}

/**
 * Creates one requirement while preserving which input team receives the
 * supplied home allocation after canonical pair ordering.
 */
export function createOpponentRequirement(
  teamAId: TeamId,
  teamBId: TeamId,
  totalMeetings: number,
  homeGamesForTeamA: number,
  homeGamesForTeamB: number,
  stage: ScheduleStage,
  sourceTag?: string,
): OpponentRequirement {
  assertNonNegativeSafeInteger(totalMeetings, 'Total meetings')
  assertNonNegativeSafeInteger(
    homeGamesForTeamA,
    'Home games for the first input team',
  )
  assertNonNegativeSafeInteger(
    homeGamesForTeamB,
    'Home games for the second input team',
  )
  if (homeGamesForTeamA + homeGamesForTeamB !== totalMeetings) {
    throw new RangeError('Opponent home-game allocations must equal total meetings')
  }

  const pair = getCanonicalTeamPair(teamAId, teamBId)
  const inputOrderIsCanonical = pair.firstTeamId === teamAId

  return Object.freeze({
    ...pair,
    totalMeetings,
    homeGamesForFirstTeam: inputOrderIsCanonical
      ? homeGamesForTeamA
      : homeGamesForTeamB,
    homeGamesForSecondTeam: inputOrderIsCanonical
      ? homeGamesForTeamB
      : homeGamesForTeamA,
    stage,
    ...(sourceTag === undefined ? {} : { sourceTag }),
  })
}

/**
 * Builds requirements before dates or game-day positions are considered.
 * Explicit matrices are validated and canonicalized rather than interpreted
 * as equal round robins.
 */
export function buildOpponentRequirementMatrix(
  teamIds: readonly TeamId[],
  ruleSet: ScheduleRuleSet,
): readonly OpponentRequirement[] {
  assertSupportedTeamCount(teamIds.length, ruleSet.teamCountPolicy)

  const sortedTeamIds = [...teamIds].sort()
  if (new Set(sortedTeamIds).size !== sortedTeamIds.length) {
    throw new RangeError('Opponent requirements require unique team IDs')
  }

  if (ruleSet.opponentPolicy.kind === 'explicit_matrix') {
    const validTeamIds = new Set(sortedTeamIds)
    const requirements: OpponentRequirement[] = []
    const seenPairKeys = new Set<string>()

    for (const requirement of ruleSet.opponentPolicy.requirements) {
      if (
        !validTeamIds.has(requirement.firstTeamId) ||
        !validTeamIds.has(requirement.secondTeamId)
      ) {
        throw new RangeError(
          'An explicit opponent requirement references an unknown team',
        )
      }
      if (requirement.stage !== ruleSet.stage) {
        throw new RangeError(
          'An explicit opponent requirement must use the rule-set stage',
        )
      }

      const canonicalRequirement = createOpponentRequirement(
        requirement.firstTeamId,
        requirement.secondTeamId,
        requirement.totalMeetings,
        requirement.homeGamesForFirstTeam,
        requirement.homeGamesForSecondTeam,
        requirement.stage,
        requirement.sourceTag ?? ruleSet.opponentPolicy.sourceTag,
      )
      const pairKey = getTeamPairKey(
        canonicalRequirement.firstTeamId,
        canonicalRequirement.secondTeamId,
      )
      if (seenPairKeys.has(pairKey)) {
        throw new RangeError(
          'An explicit opponent matrix must not repeat a canonical team pair',
        )
      }

      seenPairKeys.add(pairKey)
      requirements.push(canonicalRequirement)
    }

    requirements.sort((left, right) => {
      const leftKey = getTeamPairKey(left.firstTeamId, left.secondTeamId)
      const rightKey = getTeamPairKey(right.firstTeamId, right.secondTeamId)
      return leftKey < rightKey ? -1 : leftKey > rightKey ? 1 : 0
    })
    return Object.freeze(requirements)
  }

  const requirements: OpponentRequirement[] = []
  const policy = ruleSet.opponentPolicy

  for (let firstIndex = 0; firstIndex < sortedTeamIds.length; firstIndex += 1) {
    for (
      let secondIndex = firstIndex + 1;
      secondIndex < sortedTeamIds.length;
      secondIndex += 1
    ) {
      requirements.push(
        createOpponentRequirement(
          sortedTeamIds[firstIndex],
          sortedTeamIds[secondIndex],
          policy.meetingsPerOpponent,
          policy.homeGamesPerOpponent,
          policy.awayGamesPerOpponent,
          ruleSet.stage,
          policy.sourceTag,
        ),
      )
    }
  }

  return Object.freeze(requirements)
}

export function supportsTeamCount(
  teamCount: number,
  policy: SupportedTeamCountPolicy,
): boolean {
  if (!Number.isSafeInteger(teamCount) || teamCount < 0) {
    return false
  }

  switch (policy.kind) {
    case 'exact':
      return teamCount === policy.count
    case 'range':
      return (
        teamCount >= policy.minimum &&
        (policy.maximum === null || teamCount <= policy.maximum)
      )
    case 'allowed_counts':
      return policy.counts.includes(teamCount)
  }
}

function assertSupportedTeamCount(
  teamCount: number,
  policy: SupportedTeamCountPolicy,
): void {
  if (!supportsTeamCount(teamCount, policy)) {
    throw new RangeError(
      `Team count ${teamCount} is not supported by this schedule rule set`,
    )
  }
}

function assertNonNegativeSafeInteger(value: number, label: string): void {
  if (!Number.isSafeInteger(value) || value < 0) {
    throw new RangeError(`${label} must be a non-negative safe integer`)
  }
}

export interface LeagueSchedule {
  readonly id: ScheduleId
  readonly seasonId: SeasonId
  readonly ruleSetId: ScheduleRuleSetId
  readonly generationVersion: number
  readonly scheduleSeed: string
  readonly calendarDaySpacing: number
  readonly publicationStatus: SchedulePublicationStatus
  /** Requirements are retained independently from their eventual placement. */
  readonly opponentRequirements: readonly OpponentRequirement[]
  readonly gameDays: readonly GameDay[]
  readonly games: readonly ScheduledGame[]
}

export interface GameDay {
  readonly id: GameDayId
  readonly seasonId: SeasonId
  readonly sequenceNumber: number
  readonly scheduledDate: LocalDate
  readonly gameIds: readonly GameId[]
}

export interface ScheduledGame {
  readonly id: GameId
  readonly seasonId: SeasonId
  readonly gameDayId: GameDayId
  readonly stage: ScheduleStage
  readonly homeTeamId: TeamId
  readonly awayTeamId: TeamId
  readonly originalScheduledDate: LocalDate
  readonly currentScheduledDate: LocalDate | null
  readonly actualDate?: LocalDate
  readonly status: ScheduledGameStatus
  readonly meetingNumber: number
}

export const SCHEDULE_CONSTRAINT_SEVERITIES = ['hard', 'soft'] as const
export type ScheduleConstraintSeverity =
  (typeof SCHEDULE_CONSTRAINT_SEVERITIES)[number]

interface ScheduleConstraintBase {
  readonly severity: ScheduleConstraintSeverity
}

export interface TeamUnavailableConstraint extends ScheduleConstraintBase {
  readonly kind: 'team_unavailable_on_date'
  readonly teamId: TeamId
  readonly date: LocalDate
}

export interface VenueUnavailableConstraint extends ScheduleConstraintBase {
  readonly kind: 'venue_unavailable_on_date'
  /** Opaque reference only; venue entities are intentionally outside this model. */
  readonly venueReference: string
  readonly date: LocalDate
}

export interface FixedMatchupConstraint
  extends ScheduleConstraintBase,
    CanonicalTeamPair {
  readonly kind: 'fixed_matchup_on_date'
  readonly date: LocalDate
}

export interface PreferredMatchupConstraint
  extends ScheduleConstraintBase,
    CanonicalTeamPair {
  readonly kind: 'preferred_matchup_on_date'
  readonly date: LocalDate
}

export interface MinimumRestDaysConstraint extends ScheduleConstraintBase {
  readonly kind: 'minimum_rest_days'
  readonly minimumRestDays: number
  readonly teamId?: TeamId
}

export interface MaximumGamesInDateWindowConstraint
  extends ScheduleConstraintBase {
  readonly kind: 'maximum_games_in_date_window'
  readonly windowDays: number
  readonly maximumGames: number
  readonly teamId?: TeamId
}

export interface MaximumConsecutiveHomeGamesConstraint
  extends ScheduleConstraintBase {
  readonly kind: 'maximum_consecutive_home_games'
  readonly maximumGames: number
  readonly teamId?: TeamId
}

export interface MaximumConsecutiveAwayGamesConstraint
  extends ScheduleConstraintBase {
  readonly kind: 'maximum_consecutive_away_games'
  readonly maximumGames: number
  readonly teamId?: TeamId
}

export interface ShowcaseGamePreferenceConstraint
  extends ScheduleConstraintBase,
    CanonicalTeamPair {
  readonly kind: 'showcase_game_preference'
  readonly preferredDate?: LocalDate
}

export interface TravelRegionPreferenceConstraint
  extends ScheduleConstraintBase {
  readonly kind: 'travel_region_preference'
  readonly teamId: TeamId
  readonly regionTag: string
  readonly startDate?: LocalDate
  readonly endDate?: LocalDate
}

export type ScheduleConstraint =
  | TeamUnavailableConstraint
  | VenueUnavailableConstraint
  | FixedMatchupConstraint
  | PreferredMatchupConstraint
  | MinimumRestDaysConstraint
  | MaximumGamesInDateWindowConstraint
  | MaximumConsecutiveHomeGamesConstraint
  | MaximumConsecutiveAwayGamesConstraint
  | ShowcaseGamePreferenceConstraint
  | TravelRegionPreferenceConstraint

export type ScheduleConstraintKind = ScheduleConstraint['kind']

export const SCHEDULE_CONSTRAINT_KINDS = [
  'team_unavailable_on_date',
  'venue_unavailable_on_date',
  'fixed_matchup_on_date',
  'preferred_matchup_on_date',
  'minimum_rest_days',
  'maximum_games_in_date_window',
  'maximum_consecutive_home_games',
  'maximum_consecutive_away_games',
  'showcase_game_preference',
  'travel_region_preference',
] as const satisfies readonly ScheduleConstraintKind[]

/** The first generator deliberately supports no optimization constraints. */
export const MILESTONE_1_SUPPORTED_CONSTRAINT_KINDS = [] as const satisfies readonly ScheduleConstraintKind[]

export interface UnsupportedScheduleConstraint {
  readonly constraint: ScheduleConstraint
  readonly reason: string
}

export interface ScheduleConstraintClassification {
  readonly supported: readonly ScheduleConstraint[]
  readonly unsupported: readonly UnsupportedScheduleConstraint[]
}

export function classifyScheduleConstraints(
  constraints: readonly ScheduleConstraint[],
  supportedKinds: readonly ScheduleConstraintKind[] =
    MILESTONE_1_SUPPORTED_CONSTRAINT_KINDS,
): ScheduleConstraintClassification {
  const supportedKindSet = new Set<ScheduleConstraintKind>(supportedKinds)
  const supported: ScheduleConstraint[] = []
  const unsupported: UnsupportedScheduleConstraint[] = []

  for (const constraint of constraints) {
    if (supportedKindSet.has(constraint.kind)) {
      supported.push(constraint)
    } else {
      unsupported.push(
        Object.freeze({
          constraint,
          reason: `Constraint kind ${constraint.kind} is not supported by this generator`,
        }),
      )
    }
  }

  return Object.freeze({
    supported: Object.freeze(supported),
    unsupported: Object.freeze(unsupported),
  })
}

export const SCHEDULE_INVARIANT_CODES = [
  'invalid_schedule_id',
  'invalid_schedule_seed',
  'invalid_schedule_status',
  'wrong_season',
  'wrong_rule_set',
  'wrong_team_count',
  'duplicate_team_id',
  'unknown_team',
  'wrong_game_count',
  'wrong_game_day_count',
  'wrong_games_per_game_day',
  'wrong_games_per_team',
  'wrong_home_game_count',
  'wrong_away_game_count',
  'wrong_pair_meeting_count',
  'wrong_pair_home_balance',
  'opponent_requirement_mismatch',
  'self_matchup',
  'duplicate_game_id',
  'duplicate_game_day_id',
  'duplicate_team_appearance',
  'missing_team_appearance',
  'invalid_game_day_sequence',
  'invalid_scheduled_date',
  'lost_original_scheduled_date',
  'wrong_game_day_spacing',
  'game_day_reference_mismatch',
  'completed_game_missing_actual_date',
  'invalid_game_status',
  'invalid_numeric_value',
  'unsupported_constraint',
] as const

export type ScheduleInvariantCode =
  (typeof SCHEDULE_INVARIANT_CODES)[number]

export interface ScheduleValidationIssue {
  readonly severity: ScheduleConstraintSeverity
  readonly code: ScheduleInvariantCode
  readonly message: string
  readonly gameId?: GameId
  readonly gameDayId?: GameDayId
  readonly teamId?: TeamId
  readonly date?: LocalDate
}

export interface ScheduleValidationReport {
  readonly valid: boolean
  readonly hardViolations: readonly ScheduleValidationIssue[]
  readonly softWarnings: readonly ScheduleValidationIssue[]
}
