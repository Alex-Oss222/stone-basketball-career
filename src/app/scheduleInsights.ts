import {
  compareLocalDates,
  differenceInDays,
  parseLocalDate,
} from '../domain/localDate'
import type { LocalDate } from '../domain/localDate'

export type GameSite = 'home' | 'away'

/** One dated game for a single team, used to derive schedule pressure. */
export interface TeamScheduleGame {
  readonly date: LocalDate
  readonly site: GameSite
}

/** A maximal run of consecutive same-site games. */
export interface ScheduleRun {
  readonly games: number
  readonly startDate: LocalDate
  readonly endDate: LocalDate
}

/**
 * Pure schedule-pressure derivations for one team. Everything here is a
 * function of the dated games plus the current date — no simulation, results,
 * standings, or randomness are involved.
 */
export interface TeamScheduleInsights {
  readonly totalGames: number
  readonly homeGames: number
  readonly awayGames: number
  readonly playedGames: number
  readonly remainingGames: number
  /** Games on consecutive calendar days (zero rest). */
  readonly backToBacks: number
  /** Non-overlapping runs of five games inside a seven-day window. */
  readonly fiveInSevenStretches: number
  readonly longestRoadTrip: ScheduleRun | null
  readonly longestHomestand: ScheduleRun | null
  /** Mean rest days between consecutive games, or null with fewer than two. */
  readonly averageRestDays: number | null
}

/** Per-game schedule-pressure annotation used for cell and row badges. */
export interface AnnotatedTeamGame {
  readonly date: LocalDate
  readonly site: GameSite
  /** Rest days before this game; null for the first game. */
  readonly restDays: number | null
  readonly isBackToBack: boolean
  /** Three games within a four-day window ending at this game. */
  readonly isThreeInFour: boolean
  /** 1-based position within the current home or away run. */
  readonly runIndex: number
  readonly runLength: number
}

const FIVE_IN_SEVEN_GAMES = 5
const FIVE_IN_SEVEN_SPAN_DAYS = 6
const THREE_IN_FOUR_SPAN_DAYS = 3

/**
 * Annotates each game with rest, back-to-back, three-in-four, and home/away
 * run position. Input order is not trusted; games are sorted by date first.
 */
export function annotateTeamScheduleGames(
  games: readonly TeamScheduleGame[],
): readonly AnnotatedTeamGame[] {
  const ordered = [...games]
    .map((game) => ({ date: parseLocalDate(game.date), site: game.site }))
    .sort((left, right) => compareLocalDates(left.date, right.date))

  const runIndexes = new Array<number>(ordered.length).fill(0)
  const runLengths = new Array<number>(ordered.length).fill(0)
  let start = 0
  while (start < ordered.length) {
    let end = start
    while (end < ordered.length && ordered[end].site === ordered[start].site) {
      end += 1
    }
    for (let index = start; index < end; index += 1) {
      runIndexes[index] = index - start + 1
      runLengths[index] = end - start
    }
    start = end
  }

  return Object.freeze(
    ordered.map((game, index) => {
      const restDays =
        index === 0
          ? null
          : differenceInDays(ordered[index - 1].date, game.date) - 1
      const isThreeInFour =
        index >= 2 &&
        differenceInDays(ordered[index - 2].date, game.date) <=
          THREE_IN_FOUR_SPAN_DAYS
      return Object.freeze({
        date: game.date,
        site: game.site,
        restDays,
        isBackToBack: restDays === 0,
        isThreeInFour,
        runIndex: runIndexes[index],
        runLength: runLengths[index],
      })
    }),
  )
}

/**
 * Derives schedule pressure for one team from its dated games. Input order is
 * not trusted; games are sorted by date first. The result is frozen.
 */
export function computeTeamScheduleInsights(
  games: readonly TeamScheduleGame[],
  currentDate: LocalDate,
): TeamScheduleInsights {
  const validCurrentDate = parseLocalDate(currentDate)
  const ordered = [...games]
    .map((game) => ({ date: parseLocalDate(game.date), site: game.site }))
    .sort((left, right) => compareLocalDates(left.date, right.date))

  let homeGames = 0
  let awayGames = 0
  let playedGames = 0
  let remainingGames = 0
  let backToBacks = 0
  let restTotal = 0
  let restPairs = 0

  for (let index = 0; index < ordered.length; index += 1) {
    const game = ordered[index]
    if (game.site === 'home') homeGames += 1
    else awayGames += 1

    if (compareLocalDates(game.date, validCurrentDate) < 0) playedGames += 1
    else remainingGames += 1

    if (index > 0) {
      const gap = differenceInDays(ordered[index - 1].date, game.date)
      restTotal += gap - 1
      restPairs += 1
      if (gap === 1) backToBacks += 1
    }
  }

  return Object.freeze({
    totalGames: ordered.length,
    homeGames,
    awayGames,
    playedGames,
    remainingGames,
    backToBacks,
    fiveInSevenStretches: countFiveInSevenStretches(ordered),
    longestRoadTrip: longestRun(ordered, 'away'),
    longestHomestand: longestRun(ordered, 'home'),
    averageRestDays: restPairs === 0 ? null : restTotal / restPairs,
  })
}

function countFiveInSevenStretches(
  ordered: readonly TeamScheduleGame[],
): number {
  let stretches = 0
  let index = 0
  while (index + FIVE_IN_SEVEN_GAMES - 1 < ordered.length) {
    const span = differenceInDays(
      ordered[index].date,
      ordered[index + FIVE_IN_SEVEN_GAMES - 1].date,
    )
    if (span <= FIVE_IN_SEVEN_SPAN_DAYS) {
      stretches += 1
      index += FIVE_IN_SEVEN_GAMES
    } else {
      index += 1
    }
  }
  return stretches
}

function longestRun(
  ordered: readonly TeamScheduleGame[],
  site: GameSite,
): ScheduleRun | null {
  let best: ScheduleRun | null = null
  let runStart = -1

  for (let index = 0; index <= ordered.length; index += 1) {
    const inRun = index < ordered.length && ordered[index].site === site
    if (inRun && runStart === -1) {
      runStart = index
    } else if (!inRun && runStart !== -1) {
      const games = index - runStart
      if (best === null || games > best.games) {
        best = Object.freeze({
          games,
          startDate: ordered[runStart].date,
          endDate: ordered[index - 1].date,
        })
      }
      runStart = -1
    }
  }

  return best
}
