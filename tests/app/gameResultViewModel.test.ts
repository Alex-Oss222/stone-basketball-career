import { describe, expect, it } from 'vitest'
import {
  deriveEffectiveFieldGoalPercentage,
  deriveFourFactors,
  deriveTeamStatTotals,
  deriveTopPerformers,
  derivePercentage,
  formatFinalStatus,
  formatMinutes,
  formatPercentage,
  formatPeriodLabel,
  formatPlusMinus,
  groupBoxScoreLines,
} from '../../src/app/gameResultViewModel'
import {
  EXHIBITION_GAME_RESULT,
  EXHIBITION_PLAYER_INFO,
} from '../../src/dev/exhibitionGameResult'

const result = EXHIBITION_GAME_RESULT
const home = deriveTeamStatTotals(result, result.homeTeamId)
const away = deriveTeamStatTotals(result, result.awayTeamId)

describe('team stat totals', () => {
  it('folds the home box score into exact totals', () => {
    expect(home.fieldGoalsMade).toBe(43)
    expect(home.fieldGoalsAttempted).toBe(89)
    expect(home.threePointersMade).toBe(11)
    expect(home.threePointersAttempted).toBe(31)
    expect(home.freeThrowsMade).toBe(21)
    expect(home.freeThrowsAttempted).toBe(27)
    expect(home.points).toBe(118)
    expect(home.totalRebounds).toBe(
      home.offensiveRebounds + home.defensiveRebounds,
    )
  })

  it('folds the away box score into exact totals', () => {
    expect(away.fieldGoalsMade).toBe(41)
    expect(away.fieldGoalsAttempted).toBe(94)
    expect(away.points).toBe(112)
  })
})

describe('percentages', () => {
  it('never produces NaN — zero attempts derive null and render as a dash', () => {
    expect(derivePercentage(0, 0)).toBeNull()
    expect(formatPercentage(null)).toBe('—')
    expect(
      deriveEffectiveFieldGoalPercentage({
        ...home,
        fieldGoalsAttempted: 0,
      }),
    ).toBeNull()
  })

  it('derives ordinary shooting percentages', () => {
    expect(formatPercentage(derivePercentage(43, 89))).toBe('48.3%')
    expect(formatPercentage(derivePercentage(21, 27))).toBe('77.8%')
  })
})

describe('four factors', () => {
  it('marks the leader per factor from the box score alone', () => {
    const rows = deriveFourFactors(home, away)
    expect(rows.map((row) => row.label)).toEqual([
      'Effective FG%',
      'Turnovers',
      'Offensive rebound %',
      'FT made per FGA',
    ])
    const efg = rows[0]
    expect(efg.leader).toBe('home')
    const turnovers = rows[1]
    expect(turnovers.leader).toBe('home')
  })
})

describe('top performers', () => {
  it('orders by points with deterministic tie-breaks and skips DNP lines', () => {
    const homeTop = deriveTopPerformers(result, result.homeTeamId, 2)
    expect(homeTop.map((line) => line.points)).toEqual([27, 22])
    expect(
      EXHIBITION_PLAYER_INFO.get(homeTop[0].playerId)?.name,
    ).toBe('Dorian Vale')

    const awayTop = deriveTopPerformers(result, result.awayTeamId, 2)
    expect(awayTop.map((line) => line.points)).toEqual([26, 21])
    expect(awayTop.every((line) => line.dnpReason === null)).toBe(true)
  })
})

describe('box score grouping', () => {
  it('splits starters, bench, and DNP with deterministic ordering', () => {
    const groups = groupBoxScoreLines(result, result.homeTeamId)
    expect(groups.starters).toHaveLength(5)
    expect(groups.bench).toHaveLength(5)
    expect(groups.didNotPlay).toHaveLength(2)
    expect(groups.starters.every((line) => line.started)).toBe(true)
    const benchSeconds = groups.bench.map((line) => line.secondsPlayed)
    expect(benchSeconds).toEqual([...benchSeconds].sort((a, b) => b - a))
  })
})

describe('display formatting', () => {
  it('formats minutes, plus/minus, final status, and period labels', () => {
    expect(formatMinutes(38 * 60)).toBe('38')
    expect(formatPlusMinus(9)).toBe('+9')
    expect(formatPlusMinus(-8)).toBe('-8')
    expect(formatPlusMinus(0)).toBe('0')
    expect(formatFinalStatus(0)).toBe('Final')
    expect(formatFinalStatus(1)).toBe('Final / OT')
    expect(formatFinalStatus(3)).toBe('Final / 3OT')
    expect(formatPeriodLabel(0)).toBe('Q1')
    expect(formatPeriodLabel(3)).toBe('Q4')
    expect(formatPeriodLabel(4)).toBe('OT')
    expect(formatPeriodLabel(5)).toBe('OT2')
  })
})
