import {
  compareLocalDates,
  formatSeasonLabel,
} from '../domain/localDate'
import type { LocalDate } from '../domain/localDate'
import { parseSeason } from '../domain/season'
import type { Season } from '../domain/season'
import {
  firstDateOfMonth,
  iterateYearMonthsInclusive,
  lastDateOfMonth,
  parseYearMonth,
  yearMonthFromLocalDate,
} from '../domain/yearMonth'
import type { YearMonth } from '../domain/yearMonth'

/**
 * The explicit July-through-June display boundary for one adjacent-year
 * season. It is a derived read model and is not persisted.
 */
export interface LeagueYearDisplayRange {
  readonly startingYear: number
  readonly endingYear: number
  readonly startDate: LocalDate
  readonly endDate: LocalDate
  readonly startMonth: YearMonth
  readonly endMonth: YearMonth
  readonly seasonLabel: string
  readonly months: readonly YearMonth[]
}

const EXPECTED_MONTH_COUNT = 12

/**
 * Derives the current rule pack's July 1 through June 30 display range.
 *
 * The supplied Season is validated but never mutated or silently repaired.
 * This projection additionally requires adjacent season years.
 */
export function createLeagueYearDisplayRange(
  season: Season,
): LeagueYearDisplayRange {
  const validSeason = parseSeason(season)

  if (validSeason.endingYear !== validSeason.startingYear + 1) {
    throw new RangeError(
      'League-year display range requires adjacent starting and ending years',
    )
  }

  const startMonth = parseYearMonth(
    `${formatYear(validSeason.startingYear)}-07`,
  )
  const endMonth = parseYearMonth(`${formatYear(validSeason.endingYear)}-06`)
  const startDate = firstDateOfMonth(startMonth)
  const endDate = lastDateOfMonth(endMonth)
  const months = iterateYearMonthsInclusive(startMonth, endMonth)

  const range = Object.freeze({
    startingYear: validSeason.startingYear,
    endingYear: validSeason.endingYear,
    startDate,
    endDate,
    startMonth,
    endMonth,
    seasonLabel: validSeason.displayLabel,
    months: Object.freeze([...months]),
  })

  assertValidLeagueYearDisplayRange(range)
  return range
}

/**
 * Revalidates every semantic invariant owned by the July-through-June
 * league-year projection without repairing the supplied value.
 */
export function assertValidLeagueYearDisplayRange(
  range: LeagueYearDisplayRange,
): void {
  const authoritativeLabel = formatSeasonLabel(
    range.startingYear,
    range.endingYear,
  )

  if (range.endingYear !== range.startingYear + 1) {
    throw new RangeError(
      'League-year display range requires adjacent starting and ending years',
    )
  }

  const expectedStartMonth = parseYearMonth(
    `${formatYear(range.startingYear)}-07`,
  )
  const expectedEndMonth = parseYearMonth(
    `${formatYear(range.endingYear)}-06`,
  )
  const expectedStartDate = firstDateOfMonth(expectedStartMonth)
  const expectedEndDate = lastDateOfMonth(expectedEndMonth)
  const expectedMonths = iterateYearMonthsInclusive(
    expectedStartMonth,
    expectedEndMonth,
  )
  const validStartMonth = parseYearMonth(range.startMonth)
  const validEndMonth = parseYearMonth(range.endMonth)

  if (compareLocalDates(range.startDate, range.endDate) > 0) {
    throw new RangeError(
      'League-year display start date must not be later than its end date',
    )
  }
  if (
    range.startDate !== expectedStartDate ||
    range.endDate !== expectedEndDate
  ) {
    throw new RangeError(
      'League-year display dates must span July 1 through June 30',
    )
  }
  if (
    validStartMonth !== expectedStartMonth ||
    validEndMonth !== expectedEndMonth ||
    yearMonthFromLocalDate(range.startDate) !== validStartMonth ||
    yearMonthFromLocalDate(range.endDate) !== validEndMonth
  ) {
    throw new RangeError(
      'League-year display month boundaries must match its date boundaries',
    )
  }
  if (
    range.months.length !== EXPECTED_MONTH_COUNT ||
    expectedMonths.length !== EXPECTED_MONTH_COUNT
  ) {
    throw new RangeError(
      `League-year display range must contain exactly ${EXPECTED_MONTH_COUNT} months`,
    )
  }

  for (let index = 0; index < expectedMonths.length; index += 1) {
    if (parseYearMonth(range.months[index]) !== expectedMonths[index]) {
      throw new RangeError(
        'League-year display months must be canonical and chronologically ordered',
      )
    }
  }

  if (range.seasonLabel !== authoritativeLabel) {
    throw new RangeError(
      'League-year display label must match its authoritative season years',
    )
  }
}

function formatYear(year: number): string {
  return String(year).padStart(4, '0')
}
