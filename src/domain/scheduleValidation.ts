import {
  isGameDayId,
  isGameId,
  isScheduleId,
  isTeamId,
} from './ids'
import type { GameDayId, GameId, SeasonId, TeamId } from './ids'
import { addDays, isLocalDate } from './localDate'
import type { LocalDate } from './localDate'
import {
  SCHEDULE_PUBLICATION_STATUSES,
  SCHEDULED_GAME_STATUSES,
  buildOpponentRequirementMatrix,
  classifyScheduleConstraints,
  getTeamPairKey,
  supportsTeamCount,
} from './schedule'
import type {
  LeagueSchedule,
  OpponentRequirement,
  ScheduleConstraint,
  ScheduleConstraintSeverity,
  ScheduleInvariantCode,
  ScheduleRuleSet,
  ScheduleValidationIssue,
  ScheduleValidationReport,
  ScheduledGame,
} from './schedule'

export interface ScheduleValidationTeamReference {
  readonly id: TeamId
}

export interface ValidateLeagueScheduleInput {
  readonly schedule: LeagueSchedule
  readonly seasonId: SeasonId
  readonly teams: readonly ScheduleValidationTeamReference[]
  readonly ruleSet: ScheduleRuleSet
  readonly regularSeasonStartDate: LocalDate
  readonly calendarDaySpacing: number
  readonly constraints?: readonly ScheduleConstraint[]
}

interface TeamScheduleCounts {
  games: number
  home: number
  away: number
}

interface PairScheduleCounts {
  total: number
  firstHome: number
  secondHome: number
  readonly meetingNumbers: Set<number>
}

interface IssueAssociation {
  readonly gameId?: GameId
  readonly gameDayId?: GameDayId
  readonly teamId?: TeamId
  readonly date?: LocalDate
}

/**
 * Reports every independently detectable schedule problem. It deliberately
 * does not throw on malformed schedule data so recovery tooling can present a
 * complete diagnostic report.
 */
export function validateLeagueSchedule(
  input: ValidateLeagueScheduleInput,
): ScheduleValidationReport {
  const hardViolations: ScheduleValidationIssue[] = []
  const softWarnings: ScheduleValidationIssue[] = []
  const report = (
    severity: ScheduleConstraintSeverity,
    code: ScheduleInvariantCode,
    message: string,
    association: IssueAssociation = {},
  ): void => {
    const issue = Object.freeze({ severity, code, message, ...association })
    if (severity === 'hard') {
      hardViolations.push(issue)
    } else {
      softWarnings.push(issue)
    }
  }

  const expectedTeamIds: TeamId[] = []
  const expectedTeamIdSet = new Set<TeamId>()
  for (const team of input.teams) {
    if (!isTeamId(team.id)) {
      report(
        'hard',
        'unknown_team',
        'The expected team list contains an invalid TeamId',
      )
      continue
    }
    expectedTeamIds.push(team.id)
    if (expectedTeamIdSet.has(team.id)) {
      report(
        'hard',
        'duplicate_team_id',
        `Expected team ${team.id} appears more than once`,
        { teamId: team.id },
      )
    }
    expectedTeamIdSet.add(team.id)
  }

  if (!supportsTeamCount(input.teams.length, input.ruleSet.teamCountPolicy)) {
    report(
      'hard',
      'wrong_team_count',
      `Expected team count ${input.teams.length} is not supported by rule set ${input.ruleSet.id}`,
    )
  }

  if (input.schedule.seasonId !== input.seasonId) {
    report(
      'hard',
      'wrong_season',
      `Schedule belongs to ${input.schedule.seasonId}, not ${input.seasonId}`,
    )
  }
  if (!isScheduleId(input.schedule.id)) {
    report(
      'hard',
      'invalid_schedule_id',
      'Schedule must have a valid stable ScheduleId',
    )
  }
  if (!isCanonicalScheduleSeed(input.schedule.scheduleSeed)) {
    report(
      'hard',
      'invalid_schedule_seed',
      'Schedule seed must be a nonblank canonical normalized seed',
    )
  }
  if (input.schedule.ruleSetId !== input.ruleSet.id) {
    report(
      'hard',
      'wrong_rule_set',
      `Schedule references rule set ${input.schedule.ruleSetId}, not ${input.ruleSet.id}`,
    )
  }
  if (
    !SCHEDULE_PUBLICATION_STATUSES.includes(input.schedule.publicationStatus)
  ) {
    report(
      'hard',
      'invalid_schedule_status',
      `Schedule has unsupported publication status ${String(input.schedule.publicationStatus)}`,
    )
  }

  validateScheduleNumbers(input, report)
  validateConstraints(input.constraints ?? [], report)

  const expectedRequirements = getExpectedRequirements(input, report)
  validateOpponentRequirements(
    input.schedule.opponentRequirements,
    expectedRequirements,
    report,
  )

  if (input.schedule.gameDays.length !== input.ruleSet.gameDayCount) {
    report(
      'hard',
      'wrong_game_day_count',
      `Schedule has ${input.schedule.gameDays.length} game days; expected ${input.ruleSet.gameDayCount}`,
    )
  }
  if (input.schedule.games.length !== input.ruleSet.expectedTotalGames) {
    report(
      'hard',
      'wrong_game_count',
      `Schedule has ${input.schedule.games.length} games; expected ${input.ruleSet.expectedTotalGames}`,
    )
  }

  const gameDayById = validateGameDays(input, report)
  const gamesByDayId = new Map<GameDayId, ScheduledGame[]>()
  const gameIds = new Set<GameId>()
  const teamCounts = new Map<TeamId, TeamScheduleCounts>(
    expectedTeamIds.map((teamId) => [
      teamId,
      { games: 0, home: 0, away: 0 },
    ]),
  )
  const pairCounts = new Map<string, PairScheduleCounts>()

  for (const game of input.schedule.games) {
    validateGameIdentityAndStatus(
      game,
      input,
      gameDayById,
      gameIds,
      report,
    )
    const gamesForDay = gamesByDayId.get(game.gameDayId) ?? []
    gamesForDay.push(game)
    gamesByDayId.set(game.gameDayId, gamesForDay)

    const homeKnown = expectedTeamIdSet.has(game.homeTeamId)
    const awayKnown = expectedTeamIdSet.has(game.awayTeamId)
    if (!homeKnown) {
      report(
        'hard',
        'unknown_team',
        `Game ${game.id} references unknown home team ${game.homeTeamId}`,
        isTeamId(game.homeTeamId)
          ? { gameId: game.id, teamId: game.homeTeamId }
          : { gameId: game.id },
      )
    }
    if (!awayKnown) {
      report(
        'hard',
        'unknown_team',
        `Game ${game.id} references unknown away team ${game.awayTeamId}`,
        isTeamId(game.awayTeamId)
          ? { gameId: game.id, teamId: game.awayTeamId }
          : { gameId: game.id },
      )
    }
    if (game.homeTeamId === game.awayTeamId) {
      report(
        'hard',
        'self_matchup',
        `Game ${game.id} assigns ${game.homeTeamId} as both teams`,
        isTeamId(game.homeTeamId)
          ? { gameId: game.id, teamId: game.homeTeamId }
          : { gameId: game.id },
      )
      continue
    }

    if (homeKnown) {
      const counts = teamCounts.get(game.homeTeamId)
      if (counts !== undefined) {
        counts.games += 1
        counts.home += 1
      }
    }
    if (awayKnown) {
      const counts = teamCounts.get(game.awayTeamId)
      if (counts !== undefined) {
        counts.games += 1
        counts.away += 1
      }
    }
    if (homeKnown && awayKnown) {
      const pairKey = getTeamPairKey(game.homeTeamId, game.awayTeamId)
      const pair =
        pairCounts.get(pairKey) ??
        { total: 0, firstHome: 0, secondHome: 0, meetingNumbers: new Set() }
      pair.total += 1
      const firstTeamId = pairKey.slice(0, pairKey.indexOf(':'))
      if (game.homeTeamId === firstTeamId) {
        pair.firstHome += 1
      } else {
        pair.secondHome += 1
      }
      pair.meetingNumbers.add(game.meetingNumber)
      pairCounts.set(pairKey, pair)
    }
  }

  validateGameDayMembership(
    input,
    gameDayById,
    gamesByDayId,
    expectedTeamIds,
    report,
  )
  validateTeamCounts(input.ruleSet, teamCounts, report)
  validatePairCounts(expectedRequirements, pairCounts, report)

  return Object.freeze({
    valid: hardViolations.length === 0,
    hardViolations: Object.freeze(hardViolations),
    softWarnings: Object.freeze(softWarnings),
  })
}

export function assertValidLeagueSchedule(
  input: ValidateLeagueScheduleInput,
): void {
  const report = validateLeagueSchedule(input)
  if (!report.valid) {
    throw new Error(
      `Invalid league schedule: ${report.hardViolations.map(({ code, message }) => `${code}: ${message}`).join('; ')}`,
    )
  }
}

function validateScheduleNumbers(
  input: ValidateLeagueScheduleInput,
  report: ReportIssue,
): void {
  const numericFields = [
    ['generationVersion', input.schedule.generationVersion],
    ['calendarDaySpacing', input.schedule.calendarDaySpacing],
  ] as const
  for (const [field, value] of numericFields) {
    if (
      !Number.isSafeInteger(value) ||
      value < 0 ||
      (field === 'generationVersion' && value === 0)
    ) {
      report(
        'hard',
        'invalid_numeric_value',
        `${field} must be ${field === 'generationVersion' ? 'a positive' : 'a non-negative'} safe integer`,
      )
    }
  }

  if (
    !Number.isSafeInteger(input.calendarDaySpacing) ||
    input.calendarDaySpacing < 0
  ) {
    report(
      'hard',
      'invalid_numeric_value',
      'Expected calendar-day spacing must be a non-negative safe integer',
    )
  } else if (input.schedule.calendarDaySpacing !== input.calendarDaySpacing) {
    report(
      'hard',
      'wrong_game_day_spacing',
      `Schedule spacing ${input.schedule.calendarDaySpacing} does not match expected spacing ${input.calendarDaySpacing}`,
    )
  }

  const spacingRules = input.ruleSet.calendarSpacingRules
  if (
    input.schedule.calendarDaySpacing < spacingRules.minimumDaysBetweenGameDays ||
    (spacingRules.maximumDaysBetweenGameDays !== null &&
      input.schedule.calendarDaySpacing > spacingRules.maximumDaysBetweenGameDays)
  ) {
    report(
      'hard',
      'wrong_game_day_spacing',
      'Schedule spacing falls outside the rule-set calendar spacing bounds',
    )
  }
}

function validateConstraints(
  constraints: readonly ScheduleConstraint[],
  report: ReportIssue,
): void {
  const classification = classifyScheduleConstraints(constraints)
  for (const { constraint, reason } of classification.unsupported) {
    report(constraint.severity, 'unsupported_constraint', reason, {
      ...('teamId' in constraint ? { teamId: constraint.teamId } : {}),
      ...('date' in constraint ? { date: constraint.date } : {}),
    })
  }
}

function getExpectedRequirements(
  input: ValidateLeagueScheduleInput,
  report: ReportIssue,
): readonly OpponentRequirement[] {
  try {
    return buildOpponentRequirementMatrix(
      input.teams.map(({ id }) => id),
      input.ruleSet,
    )
  } catch (error) {
    report(
      'hard',
      'opponent_requirement_mismatch',
      error instanceof Error
        ? error.message
        : 'Opponent requirements could not be constructed',
    )
    return []
  }
}

function validateOpponentRequirements(
  actual: readonly OpponentRequirement[],
  expected: readonly OpponentRequirement[],
  report: ReportIssue,
): void {
  const expectedByPair = new Map(
    expected.map((requirement) => [
      getTeamPairKey(requirement.firstTeamId, requirement.secondTeamId),
      requirement,
    ]),
  )
  const seen = new Set<string>()

  for (const requirement of actual) {
    let pairKey: string
    try {
      pairKey = getTeamPairKey(
        requirement.firstTeamId,
        requirement.secondTeamId,
      )
    } catch {
      report(
        'hard',
        'opponent_requirement_mismatch',
        'Opponent requirements cannot contain self-matchups',
      )
      continue
    }
    if (
      requirement.firstTeamId >= requirement.secondTeamId ||
      seen.has(pairKey)
    ) {
      report(
        'hard',
        'opponent_requirement_mismatch',
        `Opponent requirement ${pairKey} is duplicated or not canonically ordered`,
      )
    }
    seen.add(pairKey)
    const expectedRequirement = expectedByPair.get(pairKey)
    if (
      expectedRequirement === undefined ||
      requirement.totalMeetings !== expectedRequirement.totalMeetings ||
      requirement.homeGamesForFirstTeam !==
        expectedRequirement.homeGamesForFirstTeam ||
      requirement.homeGamesForSecondTeam !==
        expectedRequirement.homeGamesForSecondTeam ||
      requirement.stage !== expectedRequirement.stage
    ) {
      report(
        'hard',
        'opponent_requirement_mismatch',
        `Opponent requirement ${pairKey} does not match the rule-set matrix`,
      )
    }
  }

  for (const pairKey of expectedByPair.keys()) {
    if (!seen.has(pairKey)) {
      report(
        'hard',
        'opponent_requirement_mismatch',
        `Opponent requirement ${pairKey} is missing`,
      )
    }
  }
}

function validateGameDays(
  input: ValidateLeagueScheduleInput,
  report: ReportIssue,
): Map<GameDayId, LeagueSchedule['gameDays'][number]> {
  const gameDayById = new Map<GameDayId, LeagueSchedule['gameDays'][number]>()

  for (let index = 0; index < input.schedule.gameDays.length; index += 1) {
    const gameDay = input.schedule.gameDays[index]
    if (!isGameDayId(gameDay.id)) {
      report(
        'hard',
        'duplicate_game_day_id',
        'A game day has an invalid stable ID',
      )
    } else if (gameDayById.has(gameDay.id)) {
      report(
        'hard',
        'duplicate_game_day_id',
        `GameDayId ${gameDay.id} appears more than once`,
        { gameDayId: gameDay.id },
      )
    }
    gameDayById.set(gameDay.id, gameDay)

    if (gameDay.seasonId !== input.schedule.seasonId) {
      report(
        'hard',
        'wrong_season',
        `Game day ${gameDay.id} belongs to the wrong season`,
        { gameDayId: gameDay.id },
      )
    }
    if (
      !Number.isSafeInteger(gameDay.sequenceNumber) ||
      gameDay.sequenceNumber < 1
    ) {
      report(
        'hard',
        'invalid_numeric_value',
        `Game day ${gameDay.id} has an invalid sequence number`,
        { gameDayId: gameDay.id },
      )
    }
    if (gameDay.sequenceNumber !== index + 1) {
      report(
        'hard',
        'invalid_game_day_sequence',
        `Game day ${gameDay.id} has sequence ${gameDay.sequenceNumber}; expected ${index + 1}`,
        { gameDayId: gameDay.id },
      )
    }

    if (!isLocalDate(gameDay.scheduledDate)) {
      report(
        'hard',
        'invalid_scheduled_date',
        `Game day ${gameDay.id} has an invalid scheduled date`,
        { gameDayId: gameDay.id },
      )
    } else if (
      Number.isSafeInteger(input.calendarDaySpacing) &&
      input.calendarDaySpacing >= 0 &&
      isLocalDate(input.regularSeasonStartDate)
    ) {
      let expectedDate: LocalDate | null = null
      try {
        expectedDate = addDays(
          input.regularSeasonStartDate,
          index * input.calendarDaySpacing,
        )
      } catch {
        report(
          'hard',
          'wrong_game_day_spacing',
          `Expected date for game day ${gameDay.id} falls outside the supported calendar range`,
          { gameDayId: gameDay.id, date: gameDay.scheduledDate },
        )
      }
      if (
        expectedDate !== null &&
        gameDay.scheduledDate !== expectedDate
      ) {
        report(
          'hard',
          'wrong_game_day_spacing',
          `Game day ${gameDay.id} is scheduled for ${gameDay.scheduledDate}; expected ${expectedDate}`,
          { gameDayId: gameDay.id, date: gameDay.scheduledDate },
        )
      }
    }

    if (gameDay.gameIds.length !== input.ruleSet.expectedGamesPerGameDay) {
      report(
        'hard',
        'wrong_games_per_game_day',
        `Game day ${gameDay.id} lists ${gameDay.gameIds.length} games; expected ${input.ruleSet.expectedGamesPerGameDay}`,
        { gameDayId: gameDay.id },
      )
    }
    if (new Set(gameDay.gameIds).size !== gameDay.gameIds.length) {
      report(
        'hard',
        'game_day_reference_mismatch',
        `Game day ${gameDay.id} lists a game more than once`,
        { gameDayId: gameDay.id },
      )
    }
  }

  return gameDayById
}

function isCanonicalScheduleSeed(value: unknown): value is string {
  if (typeof value !== 'string') {
    return false
  }
  const normalized = value.normalize('NFC').trim()
  return normalized.length > 0 && normalized === value
}

function validateGameIdentityAndStatus(
  game: ScheduledGame,
  input: ValidateLeagueScheduleInput,
  gameDayById: ReadonlyMap<GameDayId, LeagueSchedule['gameDays'][number]>,
  gameIds: Set<GameId>,
  report: ReportIssue,
): void {
  if (!isGameId(game.id) || gameIds.has(game.id)) {
    report(
      'hard',
      'duplicate_game_id',
      `GameId ${game.id} is invalid or appears more than once`,
      isGameId(game.id) ? { gameId: game.id } : {},
    )
  }
  gameIds.add(game.id)

  if (game.seasonId !== input.schedule.seasonId) {
    report('hard', 'wrong_season', `Game ${game.id} belongs to the wrong season`, {
      gameId: game.id,
    })
  }
  if (game.stage !== input.ruleSet.stage) {
    report(
      'hard',
      'wrong_rule_set',
      `Game ${game.id} has stage ${game.stage}, not ${input.ruleSet.stage}`,
      { gameId: game.id },
    )
  }
  const gameDay = gameDayById.get(game.gameDayId)
  if (gameDay === undefined) {
    report(
      'hard',
      'game_day_reference_mismatch',
      `Game ${game.id} references unknown game day ${game.gameDayId}`,
      { gameId: game.id, gameDayId: game.gameDayId },
    )
  }

  if (!Number.isSafeInteger(game.meetingNumber) || game.meetingNumber < 1) {
    report(
      'hard',
      'invalid_numeric_value',
      `Game ${game.id} has an invalid meeting number`,
      { gameId: game.id },
    )
  }

  if (!isLocalDate(game.originalScheduledDate)) {
    report(
      'hard',
      'lost_original_scheduled_date',
      `Game ${game.id} does not retain a valid original scheduled date`,
      { gameId: game.id },
    )
  } else if (
    gameDay !== undefined &&
    isLocalDate(gameDay.scheduledDate) &&
    game.originalScheduledDate !== gameDay.scheduledDate
  ) {
    report(
      'hard',
      'lost_original_scheduled_date',
      `Game ${game.id} original date no longer matches its game day`,
      { gameId: game.id, date: game.originalScheduledDate },
    )
  }

  if (
    game.currentScheduledDate !== null &&
    !isLocalDate(game.currentScheduledDate)
  ) {
    report(
      'hard',
      'invalid_scheduled_date',
      `Game ${game.id} has an invalid current scheduled date`,
      { gameId: game.id },
    )
  }
  if (game.actualDate !== undefined && !isLocalDate(game.actualDate)) {
    report(
      'hard',
      'invalid_scheduled_date',
      `Game ${game.id} has an invalid actual date`,
      { gameId: game.id },
    )
  }

  if (!SCHEDULED_GAME_STATUSES.includes(game.status)) {
    report(
      'hard',
      'invalid_game_status',
      `Game ${game.id} has unsupported status ${String(game.status)}`,
      { gameId: game.id },
    )
    return
  }
  if (
    (game.status === 'scheduled' || game.status === 'completed') &&
    game.currentScheduledDate === null
  ) {
    report(
      'hard',
      'invalid_scheduled_date',
      `${game.status === 'completed' ? 'Completed' : 'Scheduled'} game ${game.id} requires a current scheduled date`,
      { gameId: game.id },
    )
  }
  if (
    game.status === 'scheduled' &&
    game.currentScheduledDate !== game.originalScheduledDate
  ) {
    report(
      'hard',
      'invalid_scheduled_date',
      `Scheduled game ${game.id} must retain its original date as its current scheduled date`,
      { gameId: game.id },
    )
  }
  if (game.status === 'completed' && game.actualDate === undefined) {
    report(
      'hard',
      'completed_game_missing_actual_date',
      `Completed game ${game.id} requires an actual date`,
      { gameId: game.id },
    )
  }
  if (game.status !== 'completed' && game.actualDate !== undefined) {
    report(
      'hard',
      'invalid_game_status',
      `Non-completed game ${game.id} must not contain an actual date`,
      { gameId: game.id },
    )
  }
}

function validateGameDayMembership(
  input: ValidateLeagueScheduleInput,
  gameDayById: ReadonlyMap<GameDayId, LeagueSchedule['gameDays'][number]>,
  gamesByDayId: ReadonlyMap<GameDayId, readonly ScheduledGame[]>,
  expectedTeamIds: readonly TeamId[],
  report: ReportIssue,
): void {
  for (const [gameDayId, games] of gamesByDayId) {
    if (!gameDayById.has(gameDayId)) {
      continue
    }
    if (games.length !== input.ruleSet.expectedGamesPerGameDay) {
      report(
        'hard',
        'wrong_games_per_game_day',
        `Game day ${gameDayId} contains ${games.length} games; expected ${input.ruleSet.expectedGamesPerGameDay}`,
        { gameDayId },
      )
    }
  }

  for (const gameDay of input.schedule.gameDays) {
    const games = gamesByDayId.get(gameDay.id) ?? []
    const actualIds = new Set(games.map(({ id }) => id))
    const declaredIds = new Set(gameDay.gameIds)
    for (const gameId of actualIds) {
      if (!declaredIds.has(gameId)) {
        report(
          'hard',
          'game_day_reference_mismatch',
          `Game ${gameId} is assigned to ${gameDay.id} but is not listed by it`,
          { gameId, gameDayId: gameDay.id },
        )
      }
    }
    for (const gameId of declaredIds) {
      if (!actualIds.has(gameId)) {
        report(
          'hard',
          'game_day_reference_mismatch',
          `Game day ${gameDay.id} lists game ${gameId}, but that game is not assigned to it`,
          { gameId, gameDayId: gameDay.id },
        )
      }
    }

    if (input.ruleSet.everyTeamPlaysEachGameDay) {
      const appearances = new Map<TeamId, number>()
      for (const game of games) {
        appearances.set(
          game.homeTeamId,
          (appearances.get(game.homeTeamId) ?? 0) + 1,
        )
        appearances.set(
          game.awayTeamId,
          (appearances.get(game.awayTeamId) ?? 0) + 1,
        )
      }
      for (const teamId of expectedTeamIds) {
        const count = appearances.get(teamId) ?? 0
        if (count === 0) {
          report(
            'hard',
            'missing_team_appearance',
            `Team ${teamId} does not play on game day ${gameDay.id}`,
            { teamId, gameDayId: gameDay.id },
          )
        } else if (count > 1) {
          report(
            'hard',
            'duplicate_team_appearance',
            `Team ${teamId} appears ${count} times on game day ${gameDay.id}`,
            { teamId, gameDayId: gameDay.id },
          )
        }
      }
    }
  }
}

function validateTeamCounts(
  ruleSet: ScheduleRuleSet,
  teamCounts: ReadonlyMap<TeamId, TeamScheduleCounts>,
  report: ReportIssue,
): void {
  for (const [teamId, counts] of teamCounts) {
    if (counts.games !== ruleSet.gamesPerTeam) {
      report(
        'hard',
        'wrong_games_per_team',
        `Team ${teamId} has ${counts.games} games; expected ${ruleSet.gamesPerTeam}`,
        { teamId },
      )
    }
    if (counts.home !== ruleSet.expectedHomeGamesPerTeam) {
      report(
        'hard',
        'wrong_home_game_count',
        `Team ${teamId} has ${counts.home} home games; expected ${ruleSet.expectedHomeGamesPerTeam}`,
        { teamId },
      )
    }
    if (counts.away !== ruleSet.expectedAwayGamesPerTeam) {
      report(
        'hard',
        'wrong_away_game_count',
        `Team ${teamId} has ${counts.away} away games; expected ${ruleSet.expectedAwayGamesPerTeam}`,
        { teamId },
      )
    }
  }
}

function validatePairCounts(
  requirements: readonly OpponentRequirement[],
  pairCounts: ReadonlyMap<string, PairScheduleCounts>,
  report: ReportIssue,
): void {
  const expectedKeys = new Set<string>()
  for (const requirement of requirements) {
    const pairKey = getTeamPairKey(
      requirement.firstTeamId,
      requirement.secondTeamId,
    )
    expectedKeys.add(pairKey)
    const counts = pairCounts.get(pairKey)
    if (
      counts === undefined ||
      counts.total !== requirement.totalMeetings ||
      counts.meetingNumbers.size !== requirement.totalMeetings ||
      !integerSequenceIsComplete(
        counts.meetingNumbers,
        requirement.totalMeetings,
      )
    ) {
      report(
        'hard',
        'wrong_pair_meeting_count',
        `Pair ${pairKey} does not have meetings 1 through ${requirement.totalMeetings} exactly once`,
      )
    }
    if (
      counts === undefined ||
      counts.firstHome !== requirement.homeGamesForFirstTeam ||
      counts.secondHome !== requirement.homeGamesForSecondTeam
    ) {
      report(
        'hard',
        'wrong_pair_home_balance',
        `Pair ${pairKey} does not match its required home-and-away allocation`,
      )
    }
  }

  for (const pairKey of pairCounts.keys()) {
    if (!expectedKeys.has(pairKey)) {
      report(
        'hard',
        'opponent_requirement_mismatch',
        `Scheduled pair ${pairKey} is absent from the opponent matrix`,
      )
    }
  }
}

function integerSequenceIsComplete(
  values: ReadonlySet<number>,
  maximum: number,
): boolean {
  for (let value = 1; value <= maximum; value += 1) {
    if (!values.has(value)) {
      return false
    }
  }
  return true
}

type ReportIssue = (
  severity: ScheduleConstraintSeverity,
  code: ScheduleInvariantCode,
  message: string,
  association?: IssueAssociation,
) => void
