import { describe, expect, it } from 'vitest'
import { differenceInDays, parseLocalDate } from '../../src/domain/localDate'
import type { LocalDate } from '../../src/domain/localDate'
import {
  annotateTeamScheduleGames,
  computeTeamScheduleInsights,
} from '../../src/app/scheduleInsights'
import type {
  GameSite,
  TeamScheduleGame,
} from '../../src/app/scheduleInsights'

function game(date: string, site: GameSite): TeamScheduleGame {
  return { date: parseLocalDate(date), site }
}

const CURRENT_DATE: LocalDate = parseLocalDate('2026-10-05')

const SAMPLE_GAMES: readonly TeamScheduleGame[] = [
  game('2026-10-01', 'away'),
  game('2026-10-02', 'away'),
  game('2026-10-03', 'away'),
  game('2026-10-05', 'home'),
  game('2026-10-06', 'home'),
  game('2026-10-07', 'home'),
  game('2026-10-09', 'away'),
]

describe('differenceInDays', () => {
  it('returns a signed whole-day distance across months and leap days', () => {
    expect(
      differenceInDays(parseLocalDate('2026-10-05'), parseLocalDate('2026-10-06')),
    ).toBe(1)
    expect(
      differenceInDays(parseLocalDate('2026-10-06'), parseLocalDate('2026-10-05')),
    ).toBe(-1)
    expect(
      differenceInDays(parseLocalDate('2024-02-28'), parseLocalDate('2024-03-01')),
    ).toBe(2)
    expect(
      differenceInDays(parseLocalDate('2026-10-05'), parseLocalDate('2026-10-05')),
    ).toBe(0)
  })
})

describe('computeTeamScheduleInsights', () => {
  it('returns an empty derivation for no games', () => {
    const insights = computeTeamScheduleInsights([], CURRENT_DATE)

    expect(insights).toEqual({
      totalGames: 0,
      homeGames: 0,
      awayGames: 0,
      playedGames: 0,
      remainingGames: 0,
      backToBacks: 0,
      fiveInSevenStretches: 0,
      longestRoadTrip: null,
      longestHomestand: null,
      averageRestDays: null,
    })
  })

  it('derives counts, back-to-backs, and runs from unordered input', () => {
    const shuffled = [
      SAMPLE_GAMES[6],
      SAMPLE_GAMES[0],
      SAMPLE_GAMES[3],
      SAMPLE_GAMES[1],
      SAMPLE_GAMES[5],
      SAMPLE_GAMES[2],
      SAMPLE_GAMES[4],
    ]
    const insights = computeTeamScheduleInsights(shuffled, CURRENT_DATE)

    expect(insights.totalGames).toBe(7)
    expect(insights.homeGames).toBe(3)
    expect(insights.awayGames).toBe(4)
    expect(insights.playedGames).toBe(3)
    expect(insights.remainingGames).toBe(4)
    expect(insights.backToBacks).toBe(4)
    expect(insights.fiveInSevenStretches).toBe(1)
    expect(insights.averageRestDays).toBeCloseTo(2 / 6, 5)
    expect(insights.longestRoadTrip).toEqual({
      games: 3,
      startDate: '2026-10-01',
      endDate: '2026-10-03',
    })
    expect(insights.longestHomestand).toEqual({
      games: 3,
      startDate: '2026-10-05',
      endDate: '2026-10-07',
    })
  })

  it('annotates rest, back-to-backs, three-in-four, and run position', () => {
    const annotated = annotateTeamScheduleGames(SAMPLE_GAMES)

    expect(annotated).toHaveLength(7)
    // Oct 1: first away game of a three-game road trip.
    expect(annotated[0]).toMatchObject({
      restDays: null,
      isBackToBack: false,
      isThreeInFour: false,
      runIndex: 1,
      runLength: 3,
    })
    // Oct 2: zero rest → back-to-back, second of the road trip.
    expect(annotated[1]).toMatchObject({
      restDays: 0,
      isBackToBack: true,
      runIndex: 2,
      runLength: 3,
    })
    // Oct 3: three games (Oct 1-3) within four days.
    expect(annotated[2]).toMatchObject({
      isThreeInFour: true,
      runIndex: 3,
      runLength: 3,
    })
    // Oct 5: one rest day, first of the home stand.
    expect(annotated[3]).toMatchObject({
      site: 'home',
      restDays: 1,
      isBackToBack: false,
      runIndex: 1,
      runLength: 3,
    })
  })

  it('counts a lone game with no rest pairs and no runs longer than one', () => {
    const insights = computeTeamScheduleInsights(
      [game('2026-10-05', 'home')],
      CURRENT_DATE,
    )

    expect(insights.totalGames).toBe(1)
    expect(insights.backToBacks).toBe(0)
    expect(insights.averageRestDays).toBeNull()
    expect(insights.longestHomestand).toEqual({
      games: 1,
      startDate: '2026-10-05',
      endDate: '2026-10-05',
    })
    expect(insights.longestRoadTrip).toBeNull()
  })
})
