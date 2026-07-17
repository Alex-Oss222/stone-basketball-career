import type {
  GameResult,
  PlayerBoxScoreLine,
} from '../domain/gameResult'
import { totalReboundsFromLine } from '../domain/gameResult'
import type { TeamId } from '../domain/ids'

/**
 * Pure derivations for the post-game screens (§6). Everything here is a fold
 * over one immutable GameResult — no randomness, no season context, and no
 * values a box score cannot produce. Anything needing play-by-play events
 * (lead changes, key moments, summaries) is deliberately absent: it arrives
 * with the simulation's event log, not before.
 */

export interface TeamStatTotals {
  readonly teamId: TeamId
  readonly fieldGoalsMade: number
  readonly fieldGoalsAttempted: number
  readonly threePointersMade: number
  readonly threePointersAttempted: number
  readonly freeThrowsMade: number
  readonly freeThrowsAttempted: number
  readonly offensiveRebounds: number
  readonly defensiveRebounds: number
  readonly totalRebounds: number
  readonly assists: number
  readonly steals: number
  readonly blocks: number
  readonly turnovers: number
  readonly personalFouls: number
  readonly points: number
}

export function deriveTeamStatTotals(
  result: GameResult,
  teamId: TeamId,
): TeamStatTotals {
  const lines = result.playerLines.filter((line) => line.teamId === teamId)
  const sum = (select: (line: PlayerBoxScoreLine) => number): number =>
    lines.reduce((total, line) => total + select(line), 0)

  return {
    teamId,
    fieldGoalsMade: sum((line) => line.fieldGoalsMade),
    fieldGoalsAttempted: sum((line) => line.fieldGoalsAttempted),
    threePointersMade: sum((line) => line.threePointersMade),
    threePointersAttempted: sum((line) => line.threePointersAttempted),
    freeThrowsMade: sum((line) => line.freeThrowsMade),
    freeThrowsAttempted: sum((line) => line.freeThrowsAttempted),
    offensiveRebounds: sum((line) => line.offensiveRebounds),
    defensiveRebounds: sum((line) => line.defensiveRebounds),
    totalRebounds: sum(totalReboundsFromLine),
    assists: sum((line) => line.assists),
    steals: sum((line) => line.steals),
    blocks: sum((line) => line.blocks),
    turnovers: sum((line) => line.turnovers),
    personalFouls: sum((line) => line.personalFouls),
    points: sum((line) => line.points),
  }
}

/** Null when there are zero attempts — never NaN, never 0%. */
export function derivePercentage(made: number, attempted: number): number | null {
  if (attempted === 0) {
    return null
  }
  return (made / attempted) * 100
}

export function formatPercentage(value: number | null): string {
  return value === null ? '—' : `${value.toFixed(1)}%`
}

/** Effective FG%: (FGM + 0.5 × 3PM) / FGA. Null with zero attempts. */
export function deriveEffectiveFieldGoalPercentage(
  totals: TeamStatTotals,
): number | null {
  if (totals.fieldGoalsAttempted === 0) {
    return null
  }
  return (
    ((totals.fieldGoalsMade + 0.5 * totals.threePointersMade) /
      totals.fieldGoalsAttempted) *
    100
  )
}

/** Offensive-rebound share: own OREB / (own OREB + opponent DREB). */
export function deriveOffensiveReboundPercentage(
  own: TeamStatTotals,
  opponent: TeamStatTotals,
): number | null {
  const chances = own.offensiveRebounds + opponent.defensiveRebounds
  if (chances === 0) {
    return null
  }
  return (own.offensiveRebounds / chances) * 100
}

/** Free throws made per field-goal attempt. Null with zero attempts. */
export function deriveFreeThrowRate(totals: TeamStatTotals): number | null {
  if (totals.fieldGoalsAttempted === 0) {
    return null
  }
  return (totals.freeThrowsMade / totals.fieldGoalsAttempted) * 100
}

export interface FourFactorRow {
  readonly label: string
  readonly home: string
  readonly away: string
  /** Which side this factor favors; null when equal or not derivable. */
  readonly leader: 'home' | 'away' | null
}

export function deriveFourFactors(
  home: TeamStatTotals,
  away: TeamStatTotals,
): readonly FourFactorRow[] {
  const compare = (
    homeValue: number | null,
    awayValue: number | null,
    lowerIsBetter: boolean,
  ): 'home' | 'away' | null => {
    if (homeValue === null || awayValue === null || homeValue === awayValue) {
      return null
    }
    const homeLeads = lowerIsBetter
      ? homeValue < awayValue
      : homeValue > awayValue
    return homeLeads ? 'home' : 'away'
  }

  const homeEfg = deriveEffectiveFieldGoalPercentage(home)
  const awayEfg = deriveEffectiveFieldGoalPercentage(away)
  const homeOreb = deriveOffensiveReboundPercentage(home, away)
  const awayOreb = deriveOffensiveReboundPercentage(away, home)
  const homeFtRate = deriveFreeThrowRate(home)
  const awayFtRate = deriveFreeThrowRate(away)

  return [
    {
      label: 'Effective FG%',
      home: formatPercentage(homeEfg),
      away: formatPercentage(awayEfg),
      leader: compare(homeEfg, awayEfg, false),
    },
    {
      label: 'Turnovers',
      home: String(home.turnovers),
      away: String(away.turnovers),
      leader: compare(home.turnovers, away.turnovers, true),
    },
    {
      label: 'Offensive rebound %',
      home: formatPercentage(homeOreb),
      away: formatPercentage(awayOreb),
      leader: compare(homeOreb, awayOreb, false),
    },
    {
      label: 'FT made per FGA',
      home: formatPercentage(homeFtRate),
      away: formatPercentage(awayFtRate),
      leader: compare(homeFtRate, awayFtRate, false),
    },
  ]
}

/**
 * Leading scorers for one team, ordered by points, then seconds played, then
 * player ID so ordering is stable without consuming randomness.
 */
export function deriveTopPerformers(
  result: GameResult,
  teamId: TeamId,
  count: number,
): readonly PlayerBoxScoreLine[] {
  return result.playerLines
    .filter((line) => line.teamId === teamId && line.dnpReason === null)
    .toSorted(
      (a, b) =>
        b.points - a.points ||
        b.secondsPlayed - a.secondsPlayed ||
        a.playerId.localeCompare(b.playerId),
    )
    .slice(0, count)
}

export function formatMinutes(secondsPlayed: number): string {
  return String(Math.round(secondsPlayed / 60))
}

export function formatShootingLine(made: number, attempted: number): string {
  return `${made}-${attempted}`
}

export function formatPlusMinus(plusMinus: number): string {
  if (plusMinus > 0) {
    return `+${plusMinus}`
  }
  return String(plusMinus)
}

export function formatFinalStatus(overtimePeriods: number): string {
  if (overtimePeriods === 0) {
    return 'Final'
  }
  if (overtimePeriods === 1) {
    return 'Final / OT'
  }
  return `Final / ${overtimePeriods}OT`
}

export function formatPeriodLabel(index: number): string {
  if (index < 4) {
    return `Q${index + 1}`
  }
  const overtimeNumber = index - 3
  return overtimeNumber === 1 ? 'OT' : `OT${overtimeNumber}`
}

export interface BoxScoreGroups {
  readonly starters: readonly PlayerBoxScoreLine[]
  readonly bench: readonly PlayerBoxScoreLine[]
  readonly didNotPlay: readonly PlayerBoxScoreLine[]
}

export function groupBoxScoreLines(
  result: GameResult,
  teamId: TeamId,
): BoxScoreGroups {
  const lines = result.playerLines.filter((line) => line.teamId === teamId)
  const bySecondsThenId = (
    a: PlayerBoxScoreLine,
    b: PlayerBoxScoreLine,
  ): number =>
    b.secondsPlayed - a.secondsPlayed || a.playerId.localeCompare(b.playerId)

  return {
    starters: lines.filter((line) => line.started).toSorted(bySecondsThenId),
    bench: lines
      .filter((line) => !line.started && line.dnpReason === null)
      .toSorted(bySecondsThenId),
    didNotPlay: lines
      .filter((line) => line.dnpReason !== null)
      .toSorted((a, b) => a.playerId.localeCompare(b.playerId)),
  }
}

export const DNP_REASON_LABELS = {
  coachs_decision: "Coach's decision",
  injury: 'Injury',
  inactive: 'Inactive',
} as const
