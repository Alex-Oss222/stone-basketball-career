import { addDays, parseLocalDate } from './localDate'
import type { LocalDate } from './localDate'
import { getSundayFirstWeekdayIndex } from './yearMonth'

/** Sunday-first weekday indexes, matching getSundayFirstWeekdayIndex. */
const SUNDAY = 0
const TUESDAY = 2

/**
 * The deterministic NBA-style season timeline, derived purely from anchor rules
 * over the starting calendar year. No simulation, randomness, or league data is
 * involved — every date is a function of the starting year and the weekday math
 * in LocalDate. The regular season runs from a Tuesday in October 18–24 through
 * exactly 174 inclusive days (opening plus 173).
 */
export interface SeasonTimeline {
  readonly startingYear: number
  readonly endingYear: number
  readonly trainingCampOpens: LocalDate
  readonly preseasonStart: LocalDate
  readonly preseasonEnd: LocalDate
  readonly openingNight: LocalDate
  readonly cupKnockout: LocalDate
  readonly tradeDeadline: LocalDate
  /** Last regular-season day before the All-Star break (a Thursday). */
  readonly allStarBreakStart: LocalDate
  readonly allStarSunday: LocalDate
  /** First regular-season day after the All-Star break (a Thursday). */
  readonly regularSeasonResumes: LocalDate
  readonly regularSeasonEnd: LocalDate
  readonly playInStart: LocalDate
  readonly playInEnd: LocalDate
  readonly playoffsStart: LocalDate
  readonly draftLottery: LocalDate
  readonly finalsStart: LocalDate
  readonly latestFinalsGame7: LocalDate
  readonly draftNightOne: LocalDate
  readonly draftNightTwo: LocalDate
  readonly freeAgencyNegotiations: LocalDate
  readonly freeAgencySignings: LocalDate
  readonly summerLeagueStart: LocalDate
}

const REGULAR_SEASON_INCLUSIVE_DAYS = 174

/**
 * Builds the full season timeline for a season that opens in the given starting
 * year (the regular season concludes and the postseason falls in the following
 * calendar year). The result is frozen.
 */
export function buildSeasonTimeline(startingYear: number): SeasonTimeline {
  assertYear(startingYear)
  const endingYear = startingYear + 1
  assertYear(endingYear)

  // Opening Night: the Tuesday within October 18-24 of the starting year.
  const openingNight = firstWeekdayOnOrAfter(
    localDate(startingYear, 10, 18),
    TUESDAY,
  )

  const trainingCampOpens = addDays(openingNight, -22)
  const preseasonStart = addDays(openingNight, -18)
  const preseasonEnd = addDays(openingNight, -4)

  // NBA Cup knockout: the second Tuesday of December.
  const cupKnockout = nthWeekdayOfMonth(startingYear, 12, TUESDAY, 2)

  // Regular season: opening plus 173 days is the 174th inclusive day.
  const regularSeasonEnd = addDays(openingNight, REGULAR_SEASON_INCLUSIVE_DAYS - 1)

  // All-Star Sunday: the third Sunday of February in the ending year.
  const allStarSunday = nthWeekdayOfMonth(endingYear, 2, SUNDAY, 3)
  const allStarBreakStart = addDays(allStarSunday, -3)
  const regularSeasonResumes = addDays(allStarSunday, 4)
  // Trade deadline: All-Star Sunday minus 10 days (a Thursday).
  const tradeDeadline = addDays(allStarSunday, -10)

  // Play-In: Tuesday, Wednesday, Friday after the final Sunday.
  const playInStart = addDays(regularSeasonEnd, 2)
  const playInEnd = addDays(regularSeasonEnd, 5)
  const playoffsStart = addDays(regularSeasonEnd, 6)

  // Draft Lottery: roughly playoffs plus 23 days, moved to the following Sunday.
  const draftLottery = firstWeekdayOnOrAfter(
    addDays(playoffsStart, 23),
    SUNDAY,
  )
  const finalsStart = addDays(playoffsStart, 47)
  const latestFinalsGame7 = addDays(playoffsStart, 64)
  const draftNightOne = addDays(latestFinalsGame7, 3)
  const draftNightTwo = addDays(latestFinalsGame7, 4)

  const freeAgencyNegotiations = localDate(endingYear, 6, 30)
  const freeAgencySignings = localDate(endingYear, 7, 6)
  const summerLeagueStart = localDate(endingYear, 7, 8)

  return Object.freeze({
    startingYear,
    endingYear,
    trainingCampOpens,
    preseasonStart,
    preseasonEnd,
    openingNight,
    cupKnockout,
    tradeDeadline,
    allStarBreakStart,
    allStarSunday,
    regularSeasonResumes,
    regularSeasonEnd,
    playInStart,
    playInEnd,
    playoffsStart,
    draftLottery,
    finalsStart,
    latestFinalsGame7,
    draftNightOne,
    draftNightTwo,
    freeAgencyNegotiations,
    freeAgencySignings,
    summerLeagueStart,
  })
}

function localDate(year: number, month: number, day: number): LocalDate {
  return parseLocalDate(
    `${String(year).padStart(4, '0')}-${pad(month)}-${pad(day)}`,
  )
}

function pad(value: number): string {
  return String(value).padStart(2, '0')
}

/** The nth (1-based) occurrence of a Sunday-first weekday in a month. */
function nthWeekdayOfMonth(
  year: number,
  month: number,
  weekday: number,
  occurrence: number,
): LocalDate {
  const first = localDate(year, month, 1)
  const firstWeekday = getSundayFirstWeekdayIndex(first)
  const offsetToFirst = (weekday - firstWeekday + 7) % 7
  const day = 1 + offsetToFirst + (occurrence - 1) * 7
  return localDate(year, month, day)
}

/** The first given weekday on or after the supplied date. */
function firstWeekdayOnOrAfter(date: LocalDate, weekday: number): LocalDate {
  const offset = (weekday - getSundayFirstWeekdayIndex(date) + 7) % 7
  return addDays(date, offset)
}

function assertYear(year: number): void {
  if (!Number.isSafeInteger(year) || year < 0 || year > 9998) {
    throw new RangeError(
      `Season starting year must be an integer from 0 through 9998: ${String(year)}`,
    )
  }
}
