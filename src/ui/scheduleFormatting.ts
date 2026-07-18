import type { ScheduledGameStatus, ScheduleStage } from '../domain/schedule'
import { parseLocalDate } from '../domain/localDate'
import type { LocalDate } from '../domain/localDate'
import {
  getSundayFirstWeekdayIndex,
  parseYearMonth,
} from '../domain/yearMonth'
import type { YearMonth } from '../domain/yearMonth'
import { assertNever } from '../shared/assertNever'

const MONTH_NAMES = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
] as const

export const SHORT_MONTH_NAMES = [
  'Jan',
  'Feb',
  'Mar',
  'Apr',
  'May',
  'Jun',
  'Jul',
  'Aug',
  'Sep',
  'Oct',
  'Nov',
  'Dec',
] as const

export const SHORT_WEEKDAY_NAMES = [
  'Sun',
  'Mon',
  'Tue',
  'Wed',
  'Thu',
  'Fri',
  'Sat',
] as const

export const WEEKDAY_NAMES = [
  'Sunday',
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
  'Saturday',
] as const

export function formatScheduleMonthHeading(month: YearMonth): string {
  const parsed = parseYearMonth(month)
  const year = parsed.slice(0, 4)
  const monthNumber = Number(parsed.slice(5, 7))
  return `${MONTH_NAMES[monthNumber - 1]} ${year}`
}

export function formatScheduleDateShort(date: LocalDate): string {
  const parsed = parseLocalDate(date)
  const monthNumber = Number(parsed.slice(5, 7))
  const day = Number(parsed.slice(8, 10))
  const weekday = SHORT_WEEKDAY_NAMES[getSundayFirstWeekdayIndex(parsed)]
  return `${weekday}, ${SHORT_MONTH_NAMES[monthNumber - 1]} ${day}`
}

/** "2026-10-09" → "Oct 9" for compact schedule rows. */
export function formatScheduleDateCompact(date: LocalDate): string {
  const parsed = parseLocalDate(date)
  const monthNumber = Number(parsed.slice(5, 7))
  const day = Number(parsed.slice(8, 10))
  return `${SHORT_MONTH_NAMES[monthNumber - 1]} ${day}`
}

export function formatScheduleDateHeading(date: LocalDate): string {
  const parsed = parseLocalDate(date)
  const year = parsed.slice(0, 4)
  const monthNumber = Number(parsed.slice(5, 7))
  const day = Number(parsed.slice(8, 10))
  const weekday = WEEKDAY_NAMES[getSundayFirstWeekdayIndex(parsed)]
  return `${weekday}, ${MONTH_NAMES[monthNumber - 1]} ${day}, ${year}`
}

export function formatScheduleDateLong(date: LocalDate): string {
  const parsed = parseLocalDate(date)
  const year = parsed.slice(0, 4)
  const monthNumber = Number(parsed.slice(5, 7))
  const day = Number(parsed.slice(8, 10))
  return `${MONTH_NAMES[monthNumber - 1]} ${day}, ${year}`
}

export function formatScheduledGameStatus(
  status: ScheduledGameStatus,
): string {
  switch (status) {
    case 'scheduled':
      return 'Scheduled'
    case 'completed':
      return 'Completed'
    case 'postponed':
      return 'Postponed'
    case 'cancelled':
      return 'Cancelled'
    default:
      return assertNever(status, 'Scheduled game status')
  }
}

export function formatScheduleStage(stage: ScheduleStage): string {
  switch (stage) {
    case 'preseason':
      return 'Preseason'
    case 'regular_season':
      return 'Regular season'
    case 'cup':
      return 'Cup'
    case 'play_in':
      return 'Play-In'
    case 'postseason':
      return 'Postseason'
    default:
      return assertNever(stage, 'Schedule stage')
  }
}
