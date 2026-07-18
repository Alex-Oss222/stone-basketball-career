import {
  isLeagueId,
  isSeasonId,
  isTeamId,
  parseGameDayId,
  parseGameId,
  parseScheduleId,
} from '../domain/ids'
import type {
  GameDayId,
  GameId,
  LeagueId,
  ScheduleId,
  SeasonId,
  TeamId,
} from '../domain/ids'
import { addDays, parseLocalDate } from '../domain/localDate'
import type { LocalDate } from '../domain/localDate'
import {
  MILESTONE_1_REGULAR_SEASON_RULE_SET,
  buildOpponentRequirementMatrix,
  classifyScheduleConstraints,
  getCanonicalTeamPair,
  getTeamPairKey,
  supportsTeamCount,
} from '../domain/schedule'
import type {
  GameDay,
  LeagueSchedule,
  ScheduleConstraint,
  ScheduleRuleSet,
  ScheduledGame,
  UnsupportedScheduleConstraint,
} from '../domain/schedule'
import type { RandomSource } from '../random/randomSource'
import {
  deriveSeed,
  fingerprintDerivedSeed,
  normalizeSeed,
} from '../random/seed'
import { createRandomSource } from '../random/xoshiro128ss'
import { areJsonValuesEqual } from '../shared/areJsonValuesEqual'
import { validateLeagueSchedule } from '../domain/scheduleValidation'

export const SCHEDULE_GENERATION_VERSION = 1 as const

export const SCHEDULE_RANDOM_STREAM_LABELS = Object.freeze({
  scheduleIdentity: 'schedule/v1/identity',
  teamPermutation: 'schedule/v1/team_permutation',
  cycleOrder: 'schedule/v1/cycle_order',
  roundOrder: 'schedule/v1/round_order',
  homeAwayOrientation: 'schedule/v1/home_away_orientation',
  gameIdentity: 'schedule/v1/game_identity',
  gameDayIdentity: 'schedule/v1/game_day_identity',
})

const CYCLE_COUNT = 4
const ID_FINGERPRINT_LENGTH = 24

export interface ScheduleTeamReference {
  readonly id: TeamId
}

export interface GenerateRegularSeasonScheduleInput {
  readonly leagueId: LeagueId
  readonly seasonId: SeasonId
  readonly teams: readonly ScheduleTeamReference[]
  readonly scheduleSeed: string
  readonly regularSeasonStartDate: LocalDate
  readonly calendarDaySpacing: number
  readonly ruleSet: ScheduleRuleSet
  readonly constraints?: readonly ScheduleConstraint[]
}

export interface StableScheduleIdInput {
  readonly seasonId: SeasonId
  readonly teams: readonly ScheduleTeamReference[]
  readonly scheduleSeed: string
  readonly ruleSet: ScheduleRuleSet
}

export interface StableScheduledGameIdInput {
  readonly seasonId: SeasonId
  readonly ruleSet: ScheduleRuleSet
  readonly scheduleSeed: string
  readonly firstTeamId: TeamId
  readonly secondTeamId: TeamId
  /** Semantic four-cycle slot; deliberately not a placed game-day position. */
  readonly cycleSlot: number
}

interface RoundPair {
  readonly firstTeamId: TeamId
  readonly secondTeamId: TeamId
}

interface BaseRound {
  readonly index: number
  readonly pairs: readonly RoundPair[]
}

interface PlacedRound {
  readonly cycleSlot: number
  readonly baseRoundIndex: number
  readonly pairs: readonly RoundPair[]
}

export class UnsupportedScheduleConstraintsError extends Error {
  readonly unsupported: readonly UnsupportedScheduleConstraint[]

  constructor(unsupported: readonly UnsupportedScheduleConstraint[]) {
    super(
      `Schedule generation does not support ${unsupported.length} supplied constraint${unsupported.length === 1 ? '' : 's'}: ${unsupported.map(({ constraint }) => constraint.kind).join(', ')}`,
    )
    this.name = 'UnsupportedScheduleConstraintsError'
    this.unsupported = Object.freeze([...unsupported])
  }
}

/**
 * Generates the current eight-team regular season without sharing a mutable
 * random stream between permutation, placement, orientation, and identity.
 */
export function generateRegularSeasonSchedule(
  input: GenerateRegularSeasonScheduleInput,
): LeagueSchedule {
  assertSupportedInput(input)

  const normalizedScheduleSeed = normalizeSeed(input.scheduleSeed)
  const sortedTeamIds = input.teams.map(({ id }) => id).sort(compareIds)
  const opponentRequirements = buildOpponentRequirementMatrix(
    sortedTeamIds,
    input.ruleSet,
  )
  const seedNamespace = createSeedNamespace(
    normalizedScheduleSeed,
    input.seasonId,
    input.ruleSet,
  )
  const participantFingerprint = createParticipantFingerprint(
    seedNamespace,
    sortedTeamIds,
  )
  const scheduleId = deriveStableScheduleId({
    seasonId: input.seasonId,
    teams: input.teams,
    scheduleSeed: normalizedScheduleSeed,
    ruleSet: input.ruleSet,
  })
  const teamPermutation = shuffledWithSeed(
    sortedTeamIds,
    deriveSeed(seedNamespace, SCHEDULE_RANDOM_STREAM_LABELS.teamPermutation),
  )
  const baseRounds = createCircleRounds(teamPermutation)
  const placedRounds = orderCyclesAndRounds(baseRounds, seedNamespace)
  const meetingCounts = new Map<string, number>()
  const games: ScheduledGame[] = []
  const gameDays: GameDay[] = []

  for (let roundPosition = 0; roundPosition < placedRounds.length; roundPosition += 1) {
    const placedRound = placedRounds[roundPosition]
    const sequenceNumber = roundPosition + 1
    const scheduledDate = addDays(
      input.regularSeasonStartDate,
      roundPosition * input.calendarDaySpacing,
    )
    const gameDayId = createStableGameDayId(
      seedNamespace,
      participantFingerprint,
      placedRound.cycleSlot,
      placedRound.baseRoundIndex,
    )
    const dayGames = placedRound.pairs.map((pair) => {
      const pairKey = getTeamPairKey(pair.firstTeamId, pair.secondTeamId)
      const meetingNumber = (meetingCounts.get(pairKey) ?? 0) + 1
      meetingCounts.set(pairKey, meetingNumber)

      return createScheduledGame({
        seedNamespace,
        stableGameId: deriveStableScheduledGameId({
          seasonId: input.seasonId,
          ruleSet: input.ruleSet,
          scheduleSeed: normalizedScheduleSeed,
          firstTeamId: pair.firstTeamId,
          secondTeamId: pair.secondTeamId,
          cycleSlot: placedRound.cycleSlot,
        }),
        seasonId: input.seasonId,
        gameDayId,
        scheduledDate,
        pair,
        cycleSlot: placedRound.cycleSlot,
        meetingNumber,
        stage: input.ruleSet.stage,
      })
    })

    games.push(...dayGames)
    gameDays.push(
      Object.freeze({
        id: gameDayId,
        seasonId: input.seasonId,
        sequenceNumber,
        scheduledDate,
        gameIds: Object.freeze(dayGames.map(({ id }) => id)),
      }),
    )
  }

  const schedule: LeagueSchedule = Object.freeze({
    id: scheduleId,
    leagueId: input.leagueId,
    seasonId: input.seasonId,
    ruleSetId: input.ruleSet.id,
    generationVersion: SCHEDULE_GENERATION_VERSION,
    scheduleSeed: normalizedScheduleSeed,
    calendarDaySpacing: input.calendarDaySpacing,
    publicationStatus: 'draft',
    opponentRequirements,
    gameDays: Object.freeze(gameDays),
    games: Object.freeze(games),
  })
  const report = validateLeagueSchedule({
    schedule,
    leagueId: input.leagueId,
    seasonId: input.seasonId,
    teams: input.teams,
    ruleSet: input.ruleSet,
    regularSeasonStartDate: input.regularSeasonStartDate,
    calendarDaySpacing: input.calendarDaySpacing,
    constraints: input.constraints ?? [],
  })

  if (!report.valid) {
    const details = report.hardViolations
      .map(({ code, message }) => `${code}: ${message}`)
      .join('; ')
    throw new Error(`Generated schedule failed validation: ${details}`)
  }

  return schedule
}

/** Concise alias for callers that already know the configured schedule stage. */
export const generateSchedule = generateRegularSeasonSchedule

/**
 * Derives the generator's authoritative schedule identity from stable season,
 * rule, seed, and canonical participant inputs. LeagueId is intentionally
 * omitted because a valid SeasonId already belongs to exactly one league.
 */
export function deriveStableScheduleId(input: StableScheduleIdInput): ScheduleId {
  assertStableScheduleIdentityInput(input)
  const scheduleSeed = normalizeSeed(input.scheduleSeed)
  const sortedTeamIds = input.teams.map(({ id }) => id).sort(compareIds)
  const seedNamespace = createSeedNamespace(
    scheduleSeed,
    input.seasonId,
    input.ruleSet,
  )
  const participantFingerprint = createParticipantFingerprint(
    seedNamespace,
    sortedTeamIds,
  )
  const scheduleIdentitySeed = deriveSeed(
    seedNamespace,
    `${SCHEDULE_RANDOM_STREAM_LABELS.scheduleIdentity}/participants_${participantFingerprint}`,
  )
  return parseScheduleId(
    `schedule_${fingerprintDerivedSeed(scheduleIdentitySeed, ID_FINGERPRINT_LENGTH)}`,
  )
}

/**
 * Derives a game identity only from stable schedule identity inputs. Placement
 * sequence, dates, round order, and output array indexes are intentionally not
 * accepted and therefore cannot affect the result.
 */
export function deriveStableScheduledGameId(
  input: StableScheduledGameIdInput,
): GameId {
  if (!isSeasonId(input.seasonId)) {
    throw new TypeError('Stable game identity requires a valid SeasonId')
  }
  if (!isTeamId(input.firstTeamId) || !isTeamId(input.secondTeamId)) {
    throw new TypeError('Stable game identity requires valid TeamIds')
  }
  if (
    !Number.isSafeInteger(input.cycleSlot) ||
    input.cycleSlot < 0 ||
    input.cycleSlot >= CYCLE_COUNT
  ) {
    throw new RangeError(`Cycle slot must be an integer from 0 through ${CYCLE_COUNT - 1}`)
  }
  const scheduleSeed = normalizeSeed(input.scheduleSeed)
  const pair = getCanonicalTeamPair(input.firstTeamId, input.secondTeamId)
  const pairKey = getTeamPairKey(pair.firstTeamId, pair.secondTeamId)
  const seedNamespace = createSeedNamespace(
    scheduleSeed,
    input.seasonId,
    input.ruleSet,
  )
  const identitySeed = deriveSeed(
    seedNamespace,
    `${SCHEDULE_RANDOM_STREAM_LABELS.gameIdentity}/${pairKey}/cycle_${input.cycleSlot}`,
  )
  return parseGameId(
    `game_${fingerprintDerivedSeed(identitySeed, ID_FINGERPRINT_LENGTH)}`,
  )
}

function assertSupportedInput(input: GenerateRegularSeasonScheduleInput): void {
  if (!isLeagueId(input.leagueId)) {
    throw new TypeError('Schedule generation requires a valid LeagueId')
  }
  if (!isSeasonId(input.seasonId)) {
    throw new TypeError('Schedule generation requires a valid SeasonId')
  }

  if (!isExactMilestoneOneRuleSet(input.ruleSet)) {
    throw new RangeError(
      'This generator supports only the Milestone 1 regular-season rule set v1',
    )
  }

  if (!supportsTeamCount(input.teams.length, input.ruleSet.teamCountPolicy)) {
    throw new RangeError(
      `Team count ${input.teams.length} is not supported by this schedule rule set`,
    )
  }

  const teamIds = input.teams.map(({ id }) => id)
  if (teamIds.some((teamId) => !isTeamId(teamId))) {
    throw new TypeError('Every schedule participant must have a valid TeamId')
  }
  if (new Set(teamIds).size !== teamIds.length) {
    throw new RangeError('Schedule participants must have unique TeamIds')
  }

  parseLocalDate(input.regularSeasonStartDate)
  if (
    !Number.isSafeInteger(input.calendarDaySpacing) ||
    input.calendarDaySpacing < input.ruleSet.calendarSpacingRules.minimumDaysBetweenGameDays ||
    (input.ruleSet.calendarSpacingRules.maximumDaysBetweenGameDays !== null &&
      input.calendarDaySpacing >
        input.ruleSet.calendarSpacingRules.maximumDaysBetweenGameDays)
  ) {
    throw new RangeError(
      'Calendar-day spacing must be a supported positive safe integer',
    )
  }

  const classification = classifyScheduleConstraints(input.constraints ?? [])
  if (classification.unsupported.length > 0) {
    throw new UnsupportedScheduleConstraintsError(classification.unsupported)
  }
}

function assertStableScheduleIdentityInput(input: StableScheduleIdInput): void {
  if (!isSeasonId(input.seasonId)) {
    throw new TypeError('Stable schedule identity requires a valid SeasonId')
  }
  if (!isExactMilestoneOneRuleSet(input.ruleSet)) {
    throw new RangeError(
      'Stable schedule identity supports only the Milestone 1 regular-season rule set v1',
    )
  }
  if (!supportsTeamCount(input.teams.length, input.ruleSet.teamCountPolicy)) {
    throw new RangeError(
      `Team count ${input.teams.length} is not supported by this schedule rule set`,
    )
  }
  const teamIds = input.teams.map(({ id }) => id)
  if (teamIds.some((teamId) => !isTeamId(teamId))) {
    throw new TypeError('Stable schedule identity requires valid TeamIds')
  }
  if (new Set(teamIds).size !== teamIds.length) {
    throw new RangeError(
      'Stable schedule identity requires unique TeamIds',
    )
  }
  normalizeSeed(input.scheduleSeed)
}

function isExactMilestoneOneRuleSet(ruleSet: ScheduleRuleSet): boolean {
  return areJsonValuesEqual(
    ruleSet,
    MILESTONE_1_REGULAR_SEASON_RULE_SET,
  )
}

function createSeedNamespace(
  scheduleSeed: string,
  seasonId: SeasonId,
  ruleSet: ScheduleRuleSet,
): string {
  return deriveSeed(
    scheduleSeed,
    `schedule/v${SCHEDULE_GENERATION_VERSION}/${seasonId}/${ruleSet.id}/rules_v${ruleSet.version}`,
  )
}

function createCircleRounds(teamIds: readonly TeamId[]): readonly BaseRound[] {
  let rotation = [...teamIds]
  const rounds: BaseRound[] = []

  for (let roundIndex = 0; roundIndex < teamIds.length - 1; roundIndex += 1) {
    const pairs: RoundPair[] = []
    for (let pairIndex = 0; pairIndex < teamIds.length / 2; pairIndex += 1) {
      const teamAId = rotation[pairIndex]
      const teamBId = rotation[rotation.length - 1 - pairIndex]
      pairs.push(Object.freeze(getCanonicalTeamPair(teamAId, teamBId)))
    }
    rounds.push(
      Object.freeze({ index: roundIndex, pairs: Object.freeze(pairs) }),
    )

    rotation = [
      rotation[0],
      rotation[rotation.length - 1],
      ...rotation.slice(1, rotation.length - 1),
    ]
  }

  return Object.freeze(rounds)
}

function orderCyclesAndRounds(
  baseRounds: readonly BaseRound[],
  seedNamespace: string,
): readonly PlacedRound[] {
  const cycleSlots = shuffledWithSeed(
    Array.from({ length: CYCLE_COUNT }, (_, index) => index),
    deriveSeed(seedNamespace, SCHEDULE_RANDOM_STREAM_LABELS.cycleOrder),
  )
  const result: PlacedRound[] = []

  for (const cycleSlot of cycleSlots) {
    const orderedRounds = shuffledWithSeed(
      baseRounds,
      deriveSeed(
        seedNamespace,
        `${SCHEDULE_RANDOM_STREAM_LABELS.roundOrder}/cycle_${cycleSlot}`,
      ),
    )
    for (const round of orderedRounds) {
      result.push(
        Object.freeze({
          cycleSlot,
          baseRoundIndex: round.index,
          pairs: round.pairs,
        }),
      )
    }
  }

  return Object.freeze(result)
}

function createStableGameDayId(
  seedNamespace: string,
  participantFingerprint: string,
  cycleSlot: number,
  baseRoundIndex: number,
): GameDayId {
  const identitySeed = deriveSeed(
    seedNamespace,
    `${SCHEDULE_RANDOM_STREAM_LABELS.gameDayIdentity}/participants_${participantFingerprint}/cycle_${cycleSlot}/round_${baseRoundIndex}`,
  )
  return parseGameDayId(
    `game_day_${fingerprintDerivedSeed(identitySeed, ID_FINGERPRINT_LENGTH)}`,
  )
}

function createParticipantFingerprint(
  seedNamespace: string,
  sortedTeamIds: readonly TeamId[],
): string {
  const unambiguousParticipantSet = sortedTeamIds
    .map((teamId) => `${teamId.length}:${teamId}`)
    .join('/')
  return fingerprintDerivedSeed(
    deriveSeed(
      seedNamespace,
      `schedule/v${SCHEDULE_GENERATION_VERSION}/participants/${unambiguousParticipantSet}`,
    ),
    ID_FINGERPRINT_LENGTH,
  )
}

function createScheduledGame(input: {
  readonly seedNamespace: string
  readonly stableGameId: GameId
  readonly seasonId: SeasonId
  readonly gameDayId: GameDayId
  readonly scheduledDate: LocalDate
  readonly pair: RoundPair
  readonly cycleSlot: number
  readonly meetingNumber: number
  readonly stage: ScheduleRuleSet['stage']
}): ScheduledGame {
  const pairKey = getTeamPairKey(
    input.pair.firstTeamId,
    input.pair.secondTeamId,
  )
  const orientationRandom = createRandomSource(
    deriveSeed(
      input.seedNamespace,
      `${SCHEDULE_RANDOM_STREAM_LABELS.homeAwayOrientation}/${pairKey}`,
    ),
  )
  const firstTeamHostsEvenCycles = orientationRandom.nextInt(2) === 0
  const firstTeamIsHome =
    input.cycleSlot % 2 === 0
      ? firstTeamHostsEvenCycles
      : !firstTeamHostsEvenCycles
  const homeTeamId = firstTeamIsHome
    ? input.pair.firstTeamId
    : input.pair.secondTeamId
  const awayTeamId = firstTeamIsHome
    ? input.pair.secondTeamId
    : input.pair.firstTeamId

  return Object.freeze({
    id: input.stableGameId,
    seasonId: input.seasonId,
    gameDayId: input.gameDayId,
    stage: input.stage,
    homeTeamId,
    awayTeamId,
    originalScheduledDate: input.scheduledDate,
    currentScheduledDate: input.scheduledDate,
    status: 'scheduled',
    meetingNumber: input.meetingNumber,
  })
}

function shuffledWithSeed<T>(items: readonly T[], seed: string): T[] {
  return shuffled(items, createRandomSource(seed))
}

function shuffled<T>(items: readonly T[], random: RandomSource): T[] {
  const result = [...items]
  for (let index = result.length - 1; index > 0; index -= 1) {
    const swapIndex = random.nextInt(index + 1)
    const current = result[index]
    result[index] = result[swapIndex]
    result[swapIndex] = current
  }
  return result
}

function compareIds(left: TeamId, right: TeamId): number {
  if (left < right) {
    return -1
  }
  if (left > right) {
    return 1
  }
  return 0
}
