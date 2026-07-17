import {
  addDays,
  compareLocalDates,
} from '../domain/localDate'
import type { LocalDate } from '../domain/localDate'
import {
  daysInMonth,
  firstDateOfMonth,
  getSundayFirstWeekdayIndex,
  lastDateOfMonth,
  parseYearMonth,
  yearMonthFromLocalDate,
} from '../domain/yearMonth'
import type { YearMonth } from '../domain/yearMonth'
import type { LeagueYearDisplayRange } from './leagueYearDisplayRange'

export interface CalendarDayCellModel {
  readonly date: LocalDate
  /** The actual month containing this cell's date, including padding cells. */
  readonly month: YearMonth
  /** Sunday = 0 through Saturday = 6. */
  readonly weekdayIndex: number
  readonly belongsToMonth: boolean
  readonly isWithinLeagueYear: boolean
}

export type CalendarWeekDays = readonly [
  CalendarDayCellModel,
  CalendarDayCellModel,
  CalendarDayCellModel,
  CalendarDayCellModel,
  CalendarDayCellModel,
  CalendarDayCellModel,
  CalendarDayCellModel,
]

export interface CalendarWeekModel {
  readonly days: CalendarWeekDays
}

export type CalendarMonthWeekCount = 4 | 5 | 6

export interface CalendarMonthGridModel {
  readonly month: YearMonth
  readonly firstDate: LocalDate
  readonly lastDate: LocalDate
  readonly weeks: readonly CalendarWeekModel[]
  readonly weekCount: CalendarMonthWeekCount
}

/**
 * Builds a complete Sunday-through-Saturday structural grid.
 *
 * This operation intentionally accepts only a month contained in the supplied
 * valid league-year range. That boundary keeps adjacent padding representable
 * throughout the LocalDate-supported years.
 */
export function buildCalendarMonthGrid(
  month: YearMonth,
  leagueYearRange: LeagueYearDisplayRange,
): CalendarMonthGridModel {
  const validMonth = parseYearMonth(month)
  if (!leagueYearRange.months.includes(validMonth)) {
    throw new RangeError(
      `Calendar month ${validMonth} is outside the supplied league-year range`,
    )
  }

  const firstDate = firstDateOfMonth(validMonth)
  const lastDate = lastDateOfMonth(validMonth)
  const leadingDayCount = getSundayFirstWeekdayIndex(firstDate)
  const weekCount = parseWeekCount(
    Math.ceil((leadingDayCount + daysInMonth(validMonth)) / 7),
  )
  const gridStartDate = addDays(firstDate, -leadingDayCount)
  const weeks: CalendarWeekModel[] = []

  for (let weekIndex = 0; weekIndex < weekCount; weekIndex += 1) {
    const weekStartDate = addDays(gridStartDate, weekIndex * 7)
    const days = Object.freeze([
      createDayCell(weekStartDate, validMonth, leagueYearRange, 0),
      createDayCell(
        addDays(weekStartDate, 1),
        validMonth,
        leagueYearRange,
        1,
      ),
      createDayCell(
        addDays(weekStartDate, 2),
        validMonth,
        leagueYearRange,
        2,
      ),
      createDayCell(
        addDays(weekStartDate, 3),
        validMonth,
        leagueYearRange,
        3,
      ),
      createDayCell(
        addDays(weekStartDate, 4),
        validMonth,
        leagueYearRange,
        4,
      ),
      createDayCell(
        addDays(weekStartDate, 5),
        validMonth,
        leagueYearRange,
        5,
      ),
      createDayCell(
        addDays(weekStartDate, 6),
        validMonth,
        leagueYearRange,
        6,
      ),
    ] as const)

    weeks.push(Object.freeze({ days }))
  }

  return Object.freeze({
    month: validMonth,
    firstDate,
    lastDate,
    weeks: Object.freeze(weeks),
    weekCount,
  })
}

/**
 * Builds one structural grid for every month, including months with no future
 * games or events.
 */
export function buildLeagueYearMonthGrids(
  range: LeagueYearDisplayRange,
): readonly CalendarMonthGridModel[] {
  if (range.months.length !== 12) {
    throw new RangeError(
      'League-year month grids require exactly twelve range months',
    )
  }

  return Object.freeze(
    range.months.map((month) => buildCalendarMonthGrid(month, range)),
  )
}

function createDayCell(
  date: LocalDate,
  requestedMonth: YearMonth,
  range: LeagueYearDisplayRange,
  expectedWeekdayIndex: number,
): CalendarDayCellModel {
  const month = yearMonthFromLocalDate(date)
  const weekdayIndex = getSundayFirstWeekdayIndex(date)

  if (weekdayIndex !== expectedWeekdayIndex) {
    throw new RangeError(
      'Calendar cell weekday must match its Sunday-first week position',
    )
  }

  return Object.freeze({
    date,
    month,
    weekdayIndex,
    belongsToMonth: month === requestedMonth,
    isWithinLeagueYear:
      compareLocalDates(date, range.startDate) >= 0 &&
      compareLocalDates(date, range.endDate) <= 0,
  })
}

function parseWeekCount(value: number): CalendarMonthWeekCount {
  if (value === 4 || value === 5 || value === 6) {
    return value
  }

  throw new RangeError('Calendar month grid must contain four, five, or six weeks')
}
