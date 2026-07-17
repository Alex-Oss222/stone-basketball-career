import { isLocalDate, parseLocalDate } from './localDate'
import type { LocalDate } from './localDate'

declare const yearMonthBrand: unique symbol

/** A timezone-free calendar month serialized as canonical YYYY-MM. */
export type YearMonth = string & {
  readonly [yearMonthBrand]: 'YearMonth'
}

const YEAR_MONTH_PATTERN = /^(\d{4})-(\d{2})$/
const MONTHS_PER_YEAR = 12
const MINIMUM_MONTH_INDEX = 0
const MAXIMUM_MONTH_INDEX = 9999 * MONTHS_PER_YEAR + 11
const POSSIBLE_MONTH_LENGTHS = [31, 30, 29, 28] as const

// Sakamoto offsets for a proleptic Gregorian calendar.
const WEEKDAY_MONTH_OFFSETS = [0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4] as const

export function isYearMonth(value: unknown): value is YearMonth {
  try {
    parseYearMonth(value)
    return true
  } catch {
    return false
  }
}

/** Strictly parses a calendar month without trimming or correction. */
export function parseYearMonth(value: unknown): YearMonth {
  if (typeof value !== 'string') {
    throw new TypeError('YearMonth must be a string in YYYY-MM format')
  }

  if (!YEAR_MONTH_PATTERN.test(value)) {
    throw new TypeError('YearMonth must use exactly YYYY-MM format')
  }

  // LocalDate remains authoritative for the supported year and month range.
  parseLocalDate(`${value}-01`)
  return value as YearMonth
}

export function yearMonthFromLocalDate(date: LocalDate): YearMonth {
  return parseYearMonth(parseLocalDate(date).slice(0, 7))
}

export function compareYearMonths(
  left: YearMonth,
  right: YearMonth,
): -1 | 0 | 1 {
  const validLeft = parseYearMonth(left)
  const validRight = parseYearMonth(right)

  if (validLeft < validRight) return -1
  if (validLeft > validRight) return 1
  return 0
}

export function addMonths(month: YearMonth, amount: number): YearMonth {
  if (!Number.isSafeInteger(amount)) {
    throw new TypeError('Calendar month amount must be a safe integer')
  }

  const sourceIndex = getMonthIndex(month)
  if (
    amount < MINIMUM_MONTH_INDEX - sourceIndex ||
    amount > MAXIMUM_MONTH_INDEX - sourceIndex
  ) {
    throw new RangeError(
      'Calendar month addition is outside the supported year range',
    )
  }

  return yearMonthFromIndex(sourceIndex + amount)
}

export function firstDateOfMonth(month: YearMonth): LocalDate {
  return parseLocalDate(`${parseYearMonth(month)}-01`)
}

export function lastDateOfMonth(month: YearMonth): LocalDate {
  const validMonth = parseYearMonth(month)
  return parseLocalDate(
    `${validMonth}-${String(daysInMonth(validMonth)).padStart(2, '0')}`,
  )
}

/** Uses LocalDate validation so month lengths share its Gregorian rules. */
export function daysInMonth(month: YearMonth): number {
  const validMonth = parseYearMonth(month)

  for (const day of POSSIBLE_MONTH_LENGTHS) {
    if (isLocalDate(`${validMonth}-${day}`)) return day
  }

  throw new RangeError(`YearMonth ${validMonth} has no valid calendar days`)
}

/**
 * Returns the proleptic-Gregorian weekday using Sunday = 0 through Saturday = 6.
 */
export function getSundayFirstWeekdayIndex(date: LocalDate): number {
  const validDate = parseLocalDate(date)
  let year = Number(validDate.slice(0, 4))
  const month = Number(validDate.slice(5, 7))
  const day = Number(validDate.slice(8, 10))

  // Sakamoto treats January and February as months of the preceding year.
  if (month < 3) year -= 1

  const rawIndex =
    year +
    Math.floor(year / 4) -
    Math.floor(year / 100) +
    Math.floor(year / 400) +
    WEEKDAY_MONTH_OFFSETS[month - 1] +
    day

  return ((rawIndex % 7) + 7) % 7
}

export function iterateYearMonthsInclusive(
  start: YearMonth,
  end: YearMonth,
): readonly YearMonth[] {
  const startIndex = getMonthIndex(start)
  const endIndex = getMonthIndex(end)

  if (endIndex < startIndex) {
    throw new RangeError(
      'Ending YearMonth must not be earlier than starting YearMonth',
    )
  }

  const months = Array.from(
    { length: endIndex - startIndex + 1 },
    (_, offset) => yearMonthFromIndex(startIndex + offset),
  )
  return Object.freeze(months)
}

function getMonthIndex(month: YearMonth): number {
  const validMonth = parseYearMonth(month)
  const year = Number(validMonth.slice(0, 4))
  const monthNumber = Number(validMonth.slice(5, 7))
  return year * MONTHS_PER_YEAR + monthNumber - 1
}

function yearMonthFromIndex(index: number): YearMonth {
  const year = Math.floor(index / MONTHS_PER_YEAR)
  const month = (index % MONTHS_PER_YEAR) + 1
  return parseYearMonth(
    `${String(year).padStart(4, '0')}-${String(month).padStart(2, '0')}`,
  )
}
