declare const localDateBrand: unique symbol

/** A timezone-free ISO calendar date serialized as YYYY-MM-DD. */
export type LocalDate = string & {
  readonly [localDateBrand]: 'LocalDate'
}

interface DateParts {
  readonly year: number
  readonly month: number
  readonly day: number
}

const LOCAL_DATE_PATTERN = /^(\d{4})-(\d{2})-(\d{2})$/
const MONTH_LENGTHS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31] as const
const MINIMUM_YEAR = 0
const MAXIMUM_YEAR = 9999

export function isLocalDate(value: unknown): value is LocalDate {
  try {
    parseLocalDate(value)
    return true
  } catch {
    return false
  }
}

/**
 * Strictly parses a calendar date without timezone conversion or correction.
 * Invalid dates such as 2026-02-30 are rejected rather than normalized.
 */
export function parseLocalDate(value: unknown): LocalDate {
  if (typeof value !== 'string') {
    throw new TypeError('LocalDate must be a string in YYYY-MM-DD format')
  }

  const match = LOCAL_DATE_PATTERN.exec(value)
  if (match === null) {
    throw new TypeError('LocalDate must use exactly YYYY-MM-DD format')
  }

  const year = Number(match[1])
  const month = Number(match[2])
  const day = Number(match[3])
  const maximumDay = daysInMonth(year, month)

  if (maximumDay === 0 || day < 1 || day > maximumDay) {
    throw new RangeError(`${value} is not a valid calendar date`)
  }

  return value as LocalDate
}

/** Returns -1, 0, or 1 using chronological calendar ordering. */
export function compareLocalDates(left: LocalDate, right: LocalDate): -1 | 0 | 1 {
  const validLeft = parseLocalDate(left)
  const validRight = parseLocalDate(right)

  if (validLeft < validRight) {
    return -1
  }
  if (validLeft > validRight) {
    return 1
  }
  return 0
}

/** Adds whole calendar days without constructing or returning a mutable Date. */
export function addDays(date: LocalDate, amount: number): LocalDate {
  if (!Number.isSafeInteger(amount)) {
    throw new TypeError('Calendar day amount must be a safe integer')
  }

  const parts = getDateParts(parseLocalDate(date))
  const targetOrdinal = toOrdinal(parts) + amount
  const maximumOrdinal = daysBeforeYear(MAXIMUM_YEAR + 1) - 1

  if (targetOrdinal < 0 || targetOrdinal > maximumOrdinal) {
    throw new RangeError('Calendar day addition is outside the supported year range')
  }

  return formatDateParts(fromOrdinal(targetOrdinal))
}

export function getCalendarYear(date: LocalDate): number {
  return getDateParts(parseLocalDate(date)).year
}

/** Signed whole-day count from `from` to `to` in the proleptic calendar. */
export function differenceInDays(from: LocalDate, to: LocalDate): number {
  return (
    toOrdinal(getDateParts(parseLocalDate(to))) -
    toOrdinal(getDateParts(parseLocalDate(from)))
  )
}

/**
 * Formats a season range with an abbreviated ending year only when both years
 * are in the same century. An en dash separates the stored numeric years.
 */
export function formatSeasonLabel(startingYear: number, endingYear: number): string {
  assertCalendarYear(startingYear, 'Starting year')
  assertCalendarYear(endingYear, 'Ending year')

  if (endingYear <= startingYear) {
    throw new RangeError('Ending year must be later than starting year')
  }

  const start = formatYear(startingYear)
  const sameCentury =
    Math.floor(startingYear / 100) === Math.floor(endingYear / 100)
  const end = sameCentury
    ? String(endingYear % 100).padStart(2, '0')
    : formatYear(endingYear)

  return `${start}–${end}`
}

function getDateParts(date: LocalDate): DateParts {
  return {
    year: Number(date.slice(0, 4)),
    month: Number(date.slice(5, 7)),
    day: Number(date.slice(8, 10)),
  }
}

function daysInMonth(year: number, month: number): number {
  if (month < 1 || month > 12) {
    return 0
  }
  if (month === 2 && isLeapYear(year)) {
    return 29
  }
  return MONTH_LENGTHS[month - 1]
}

function isLeapYear(year: number): boolean {
  return year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0)
}

/** Number of days in the proleptic Gregorian calendar before January 1. */
function daysBeforeYear(year: number): number {
  return (
    365 * year +
    Math.floor((year + 3) / 4) -
    Math.floor((year + 99) / 100) +
    Math.floor((year + 399) / 400)
  )
}

function toOrdinal(parts: DateParts): number {
  let ordinal = daysBeforeYear(parts.year)
  for (let month = 1; month < parts.month; month += 1) {
    ordinal += daysInMonth(parts.year, month)
  }
  return ordinal + parts.day - 1
}

function fromOrdinal(ordinal: number): DateParts {
  let low = MINIMUM_YEAR
  let high = MAXIMUM_YEAR + 1

  while (low + 1 < high) {
    const middle = Math.floor((low + high) / 2)
    if (daysBeforeYear(middle) <= ordinal) {
      low = middle
    } else {
      high = middle
    }
  }

  const year = low
  let dayOfYear = ordinal - daysBeforeYear(year)
  let month = 1
  while (dayOfYear >= daysInMonth(year, month)) {
    dayOfYear -= daysInMonth(year, month)
    month += 1
  }

  return { year, month, day: dayOfYear + 1 }
}

function formatDateParts(parts: DateParts): LocalDate {
  return `${formatYear(parts.year)}-${String(parts.month).padStart(2, '0')}-${String(parts.day).padStart(2, '0')}` as LocalDate
}

function formatYear(year: number): string {
  return String(year).padStart(4, '0')
}

function assertCalendarYear(value: number, label: string): void {
  if (
    !Number.isSafeInteger(value) ||
    value < MINIMUM_YEAR ||
    value > MAXIMUM_YEAR
  ) {
    throw new RangeError(`${label} must be an integer from 0 through 9999`)
  }
}
