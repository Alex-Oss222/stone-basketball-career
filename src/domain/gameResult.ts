import type { GameId, PlayerId, SeasonId, TeamId } from './ids'
import {
  MILESTONE_1_LEAGUE_RULES,
  deriveOvertimeTeamSeconds,
  deriveRegulationTeamSeconds,
} from './leagueRules'

/**
 * DRAFT result contract (roadmap §6). These shapes are being discovered by the
 * result / box-score / home screens against fixtures. They are disposable until
 * §6 exits; the screens are in charge. Per ADR 0005 a GameResult is a separate
 * immutable aggregate keyed to one GameId — never fields on ScheduledGame.
 *
 * Nothing simulates or persists this yet. The first real producer is the §9
 * kernel; the first persisted copy is the §10 snapshot bump.
 */
export const GAME_RESULT_DRAFT_VERSION = 1

export const REGULATION_PERIODS =
  MILESTONE_1_LEAGUE_RULES.regulation.periodCount
export const REGULATION_PERIOD_SECONDS =
  MILESTONE_1_LEAGUE_RULES.regulation.secondsPerPeriod
export const OVERTIME_PERIOD_SECONDS =
  MILESTONE_1_LEAGUE_RULES.overtime.secondsPerPeriod
export const PLAYERS_ON_COURT =
  MILESTONE_1_LEAGUE_RULES.lineup.playersOnCourt

/** Total player-seconds one team must account for in regulation. */
export const REGULATION_TEAM_SECONDS = deriveRegulationTeamSeconds(
  MILESTONE_1_LEAGUE_RULES,
)

/** Additional player-seconds one team must account for per overtime period. */
export const OVERTIME_TEAM_SECONDS = deriveOvertimeTeamSeconds(
  MILESTONE_1_LEAGUE_RULES,
)

export const DNP_REASONS = Object.freeze([
  'coachs_decision',
  'injury',
  'inactive',
] as const)
export type DnpReason = (typeof DNP_REASONS)[number]

const DNP_REASON_SET: ReadonlySet<string> = new Set(DNP_REASONS)

export function isDnpReason(value: unknown): value is DnpReason {
  return typeof value === 'string' && DNP_REASON_SET.has(value)
}

/** One player's line. Everything is integer counting stats or integer seconds. */
export interface PlayerBoxScoreLine {
  readonly playerId: PlayerId
  readonly teamId: TeamId
  readonly started: boolean
  readonly secondsPlayed: number
  readonly fieldGoalsMade: number
  readonly fieldGoalsAttempted: number
  readonly threePointersMade: number
  readonly threePointersAttempted: number
  readonly freeThrowsMade: number
  readonly freeThrowsAttempted: number
  readonly offensiveRebounds: number
  readonly defensiveRebounds: number
  readonly assists: number
  readonly steals: number
  readonly blocks: number
  readonly turnovers: number
  readonly personalFouls: number
  readonly plusMinus: number
  readonly points: number
  /** Non-null exactly when the player did not play. */
  readonly dnpReason: DnpReason | null
}

/** One team's scoring by period: 4 regulation entries plus one per overtime. */
export interface TeamPeriodScoring {
  readonly teamId: TeamId
  readonly periodPoints: readonly number[]
  readonly totalPoints: number
}

export interface GameResult {
  readonly gameId: GameId
  readonly seasonId: SeasonId
  readonly homeTeamId: TeamId
  readonly awayTeamId: TeamId
  readonly overtimePeriods: number
  readonly home: TeamPeriodScoring
  readonly away: TeamPeriodScoring
  readonly winnerTeamId: TeamId
  readonly playerLines: readonly PlayerBoxScoreLine[]
}

export interface GameResultIssue {
  readonly code: string
  readonly message: string
}

export class InvalidGameResultError extends RangeError {
  readonly issues: readonly GameResultIssue[]

  constructor(issues: readonly GameResultIssue[]) {
    super(
      `Invalid game result: ${issues
        .map((issue) => `${issue.code} — ${issue.message}`)
        .join('; ')}`,
    )
    this.name = 'InvalidGameResultError'
    this.issues = issues
  }
}

export function totalPointsFromLine(line: PlayerBoxScoreLine): number {
  const twoPointMakes = line.fieldGoalsMade - line.threePointersMade
  return twoPointMakes * 2 + line.threePointersMade * 3 + line.freeThrowsMade
}

export function totalReboundsFromLine(line: PlayerBoxScoreLine): number {
  return line.offensiveRebounds + line.defensiveRebounds
}

/**
 * Every structural invariant a result must satisfy before any screen or (later)
 * any save may trust it. Fixtures are run through this in tests, which is what
 * keeps §6 screen design honest: the screens only ever see producible data.
 */
export function collectGameResultIssues(
  result: GameResult,
): readonly GameResultIssue[] {
  const issues: GameResultIssue[] = []
  const report = (code: string, message: string) => {
    issues.push({ code, message })
  }

  if (result.homeTeamId === result.awayTeamId) {
    report('same_team', 'Home and away team are identical')
  }
  if (
    !Number.isSafeInteger(result.overtimePeriods) ||
    result.overtimePeriods < 0
  ) {
    report('overtime_periods', 'Overtime period count must be a non-negative integer')
  }

  const expectedPeriods = REGULATION_PERIODS + result.overtimePeriods
  for (const side of ['home', 'away'] as const) {
    const scoring = result[side]
    const expectedTeamId =
      side === 'home' ? result.homeTeamId : result.awayTeamId
    if (scoring.teamId !== expectedTeamId) {
      report('period_team', `${side} period scoring belongs to the wrong team`)
    }
    if (scoring.periodPoints.length !== expectedPeriods) {
      report(
        'period_count',
        `${side} has ${scoring.periodPoints.length} periods; expected ${expectedPeriods}`,
      )
    }
    let periodSum = 0
    for (const points of scoring.periodPoints) {
      if (!Number.isSafeInteger(points) || points < 0) {
        report('period_points', `${side} has a negative or non-integer period score`)
      }
      periodSum += points
    }
    if (periodSum !== scoring.totalPoints) {
      report(
        'period_total',
        `${side} period points sum to ${periodSum}, not the stored total ${scoring.totalPoints}`,
      )
    }
  }

  if (result.home.totalPoints === result.away.totalPoints) {
    report('tie', 'A completed game cannot end tied')
  }
  const derivedWinner =
    result.home.totalPoints > result.away.totalPoints
      ? result.homeTeamId
      : result.awayTeamId
  if (result.winnerTeamId !== derivedWinner) {
    report('winner', 'Stored winner does not match the higher total')
  }

  const seenPlayerIds = new Set<PlayerId>()
  const perTeam = new Map<
    TeamId,
    {
      points: number
      seconds: number
      plusMinus: number
      starters: number
      lines: number
    }
  >([
    [result.homeTeamId, { points: 0, seconds: 0, plusMinus: 0, starters: 0, lines: 0 }],
    [result.awayTeamId, { points: 0, seconds: 0, plusMinus: 0, starters: 0, lines: 0 }],
  ])

  const countingStats = [
    'secondsPlayed',
    'fieldGoalsMade',
    'fieldGoalsAttempted',
    'threePointersMade',
    'threePointersAttempted',
    'freeThrowsMade',
    'freeThrowsAttempted',
    'offensiveRebounds',
    'defensiveRebounds',
    'assists',
    'steals',
    'blocks',
    'turnovers',
    'personalFouls',
    'points',
  ] as const

  for (const line of result.playerLines) {
    const label = `player ${line.playerId}`
    if (seenPlayerIds.has(line.playerId)) {
      report('duplicate_player', `${label} appears twice`)
    }
    seenPlayerIds.add(line.playerId)

    if (line.dnpReason !== null && !isDnpReason(line.dnpReason)) {
      report('invalid_dnp_reason', `${label} has an unsupported DNP reason`)
    }

    const team = perTeam.get(line.teamId)
    if (team === undefined) {
      report('foreign_player', `${label} belongs to neither team`)
      continue
    }

    for (const key of countingStats) {
      const value = line[key]
      if (!Number.isSafeInteger(value) || value < 0) {
        report('negative_stat', `${label} has a negative or non-integer ${key}`)
      }
    }
    if (!Number.isSafeInteger(line.plusMinus)) {
      report('plus_minus', `${label} has a non-integer plus/minus`)
    }

    if (line.fieldGoalsMade > line.fieldGoalsAttempted) {
      report('makes_exceed_attempts', `${label} made more field goals than attempted`)
    }
    if (line.threePointersMade > line.threePointersAttempted) {
      report('makes_exceed_attempts', `${label} made more threes than attempted`)
    }
    if (line.freeThrowsMade > line.freeThrowsAttempted) {
      report('makes_exceed_attempts', `${label} made more free throws than attempted`)
    }
    if (line.threePointersMade > line.fieldGoalsMade) {
      report('three_point_subset', `${label} has more threes made than field goals made`)
    }
    if (line.threePointersAttempted > line.fieldGoalsAttempted) {
      report('three_point_subset', `${label} has more threes attempted than field goals attempted`)
    }

    if (line.points !== totalPointsFromLine(line)) {
      report(
        'points_arithmetic',
        `${label} stores ${line.points} points but the shooting line produces ${totalPointsFromLine(line)}`,
      )
    }

    if (line.dnpReason !== null) {
      const hasAnyStat = countingStats.some((key) => line[key] !== 0)
      if (hasAnyStat || line.plusMinus !== 0 || line.started) {
        report('dnp_with_stats', `${label} did not play but has recorded activity`)
      }
    } else if (line.secondsPlayed === 0) {
      report('zero_seconds_no_reason', `${label} played zero seconds without a DNP reason`)
    }

    team.points += line.points
    team.seconds += line.secondsPlayed
    team.plusMinus += line.plusMinus
    team.lines += 1
    if (line.started) {
      team.starters += 1
    }
  }

  const expectedTeamSeconds =
    REGULATION_TEAM_SECONDS + result.overtimePeriods * OVERTIME_TEAM_SECONDS
  const margin = result.home.totalPoints - result.away.totalPoints

  for (const [teamId, tally] of perTeam) {
    const side = teamId === result.homeTeamId ? 'home' : 'away'
    const scoring = side === 'home' ? result.home : result.away
    if (tally.lines < PLAYERS_ON_COURT) {
      report('too_few_players', `${side} has only ${tally.lines} player lines`)
    }
    if (tally.starters !== PLAYERS_ON_COURT) {
      report('starter_count', `${side} lists ${tally.starters} starters; expected ${PLAYERS_ON_COURT}`)
    }
    if (tally.points !== scoring.totalPoints) {
      report(
        'team_points',
        `${side} player points sum to ${tally.points}, not the team total ${scoring.totalPoints}`,
      )
    }
    if (tally.seconds !== expectedTeamSeconds) {
      report(
        'team_seconds',
        `${side} player seconds sum to ${tally.seconds}, not the required ${expectedTeamSeconds}`,
      )
    }
    const expectedPlusMinus =
      PLAYERS_ON_COURT * (side === 'home' ? margin : -margin)
    if (tally.plusMinus !== expectedPlusMinus) {
      report(
        'team_plus_minus',
        `${side} plus/minus sums to ${tally.plusMinus}, not the required ${expectedPlusMinus}`,
      )
    }
  }

  return issues
}

/** Throws InvalidGameResultError unless every invariant holds. */
export function assertValidGameResult(result: GameResult): void {
  const issues = collectGameResultIssues(result)
  if (issues.length > 0) {
    throw new InvalidGameResultError(issues)
  }
}
