import { describe, expect, it } from 'vitest'
import {
  InvalidGameResultError,
  assertValidGameResult,
  collectGameResultIssues,
  totalPointsFromLine,
} from '../../src/domain/gameResult'
import type { GameResult, PlayerBoxScoreLine } from '../../src/domain/gameResult'
import {
  EXHIBITION_AWAY_TEAM,
  EXHIBITION_GAME_RESULT,
  EXHIBITION_HOME_TEAM,
  EXHIBITION_PLAYER_INFO,
} from '../../src/dev/exhibitionGameResult'

/**
 * The §6 guardrail: the design fixture must satisfy every structural invariant
 * a simulated result will have to satisfy, so the screens are only ever
 * designed against producible data.
 */
describe('exhibition design fixture', () => {
  it('satisfies every game-result invariant', () => {
    expect(collectGameResultIssues(EXHIBITION_GAME_RESULT)).toEqual([])
    expect(() => assertValidGameResult(EXHIBITION_GAME_RESULT)).not.toThrow()
  })

  it('is a one-overtime 118-112 home win between the two fixture teams', () => {
    expect(EXHIBITION_GAME_RESULT.home.totalPoints).toBe(118)
    expect(EXHIBITION_GAME_RESULT.away.totalPoints).toBe(112)
    expect(EXHIBITION_GAME_RESULT.overtimePeriods).toBe(1)
    expect(EXHIBITION_GAME_RESULT.winnerTeamId).toBe(EXHIBITION_HOME_TEAM.id)
    expect(EXHIBITION_GAME_RESULT.home.periodPoints).toHaveLength(5)
    expect(EXHIBITION_GAME_RESULT.away.periodPoints).toHaveLength(5)
  })

  it('uses only fictional identities and covers a full 12-player roster per side', () => {
    expect(EXHIBITION_HOME_TEAM.city).toBe('Emberlyn')
    expect(EXHIBITION_AWAY_TEAM.city).toBe('Duskmere')
    const homeLines = EXHIBITION_GAME_RESULT.playerLines.filter(
      (line) => line.teamId === EXHIBITION_HOME_TEAM.id,
    )
    const awayLines = EXHIBITION_GAME_RESULT.playerLines.filter(
      (line) => line.teamId === EXHIBITION_AWAY_TEAM.id,
    )
    expect(homeLines).toHaveLength(12)
    expect(awayLines).toHaveLength(12)
    expect(homeLines.filter((line) => line.dnpReason !== null)).toHaveLength(2)
    expect(awayLines.filter((line) => line.dnpReason !== null)).toHaveLength(2)
    for (const line of EXHIBITION_GAME_RESULT.playerLines) {
      expect(EXHIBITION_PLAYER_INFO.get(line.playerId)).toBeDefined()
    }
  })
})

describe('game-result invariant validation', () => {
  const base = EXHIBITION_GAME_RESULT

  function firstHomeLine(): PlayerBoxScoreLine {
    const line = base.playerLines.find(
      (candidate) =>
        candidate.teamId === base.homeTeamId && candidate.dnpReason === null,
    )
    if (line === undefined) {
      throw new Error('Fixture has no played home line')
    }
    return line
  }

  function withReplacedLine(
    replacement: PlayerBoxScoreLine,
  ): GameResult {
    return {
      ...base,
      playerLines: base.playerLines.map((line) =>
        line.playerId === replacement.playerId ? replacement : line,
      ),
    }
  }

  it('rejects a tied final score', () => {
    const tied: GameResult = {
      ...base,
      away: { ...base.away, totalPoints: 118 },
    }
    const codes = collectGameResultIssues(tied).map((issue) => issue.code)
    expect(codes).toContain('tie')
  })

  it('rejects a stored winner that does not match the higher total', () => {
    const wrongWinner: GameResult = { ...base, winnerTeamId: base.awayTeamId }
    const codes = collectGameResultIssues(wrongWinner).map(
      (issue) => issue.code,
    )
    expect(codes).toContain('winner')
  })

  it('rejects team totals that disagree with the period line', () => {
    const broken: GameResult = {
      ...base,
      home: { ...base.home, periodPoints: [28, 29, 32, 23, 7] },
    }
    const codes = collectGameResultIssues(broken).map((issue) => issue.code)
    expect(codes).toContain('period_total')
  })

  it('rejects player points that disagree with the shooting line', () => {
    const line = firstHomeLine()
    const codes = collectGameResultIssues(
      withReplacedLine({ ...line, points: line.points + 2 }),
    ).map((issue) => issue.code)
    expect(codes).toContain('points_arithmetic')
    expect(codes).toContain('team_points')
  })

  it('rejects makes exceeding attempts', () => {
    const line = firstHomeLine()
    const codes = collectGameResultIssues(
      withReplacedLine({
        ...line,
        fieldGoalsAttempted: line.fieldGoalsMade - 1,
      }),
    ).map((issue) => issue.code)
    expect(codes).toContain('makes_exceed_attempts')
  })

  it('rejects team minutes that do not reconcile', () => {
    const line = firstHomeLine()
    const codes = collectGameResultIssues(
      withReplacedLine({ ...line, secondsPlayed: line.secondsPlayed + 60 }),
    ).map((issue) => issue.code)
    expect(codes).toContain('team_seconds')
  })

  it('rejects a DNP line carrying recorded activity', () => {
    const dnp = base.playerLines.find((line) => line.dnpReason !== null)
    if (dnp === undefined) {
      throw new Error('Fixture has no DNP line')
    }
    const codes = collectGameResultIssues(
      withReplacedLine({ ...dnp, assists: 2 }),
    ).map((issue) => issue.code)
    expect(codes).toContain('dnp_with_stats')
  })

  it('rejects plus/minus that does not sum to five times the margin', () => {
    const line = firstHomeLine()
    const codes = collectGameResultIssues(
      withReplacedLine({ ...line, plusMinus: line.plusMinus + 1 }),
    ).map((issue) => issue.code)
    expect(codes).toContain('team_plus_minus')
  })

  it('rejects a team that does not list exactly five starters', () => {
    const starter = base.playerLines.find(
      (line) => line.teamId === base.homeTeamId && line.started,
    )
    if (starter === undefined) {
      throw new Error('Fixture has no home starter')
    }
    const codes = collectGameResultIssues(
      withReplacedLine({ ...starter, started: false }),
    ).map((issue) => issue.code)
    expect(codes).toContain('starter_count')
  })

  it('rejects negative counting stats', () => {
    const line = firstHomeLine()
    const codes = collectGameResultIssues(
      withReplacedLine({ ...line, steals: -1 }),
    ).map((issue) => issue.code)
    expect(codes).toContain('negative_stat')
  })

  it('throws a typed error carrying every issue', () => {
    const tied: GameResult = {
      ...base,
      away: { ...base.away, totalPoints: 118 },
    }
    try {
      assertValidGameResult(tied)
      expect.unreachable('assertValidGameResult must throw')
    } catch (error) {
      expect(error).toBeInstanceOf(InvalidGameResultError)
      if (error instanceof InvalidGameResultError) {
        expect(error.issues.length).toBeGreaterThan(0)
      }
    }
  })

  it('derives line points from twos, threes, and free throws', () => {
    const line = firstHomeLine()
    expect(totalPointsFromLine(line)).toBe(line.points)
  })
})
