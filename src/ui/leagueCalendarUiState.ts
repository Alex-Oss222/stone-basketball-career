import type { TeamId } from '../domain/ids'
import { parseLocalDate } from '../domain/localDate'
import type { LocalDate } from '../domain/localDate'
import {
  parseYearMonth,
  yearMonthFromLocalDate,
} from '../domain/yearMonth'
import type { YearMonth } from '../domain/yearMonth'
import type { CalendarScope } from '../app/enrichedCalendarViewModel'
import type { LeagueYearDisplayRange } from '../app/leagueYearDisplayRange'
import { parseBroadcastFilter } from './broadcastFilter'
import type { BroadcastFilter } from './broadcastFilter'
import { assertNever } from '../shared/assertNever'

export type LeagueCalendarViewMode = 'calendar' | 'list' | 'by_team'

/**
 * Transient League Calendar presentation preferences. Per ADR 0004 these never
 * touch league truth: no persistence, revision, or Season.currentDate change.
 */
export interface LeagueCalendarUiState {
  readonly viewMode: LeagueCalendarViewMode
  readonly scope: CalendarScope
  readonly broadcast: BroadcastFilter
  readonly visibleMonth: YearMonth
  readonly selectedDate: LocalDate | null
}

export interface CreateLeagueCalendarUiStateInput {
  readonly range: LeagueYearDisplayRange
  readonly currentDate: LocalDate
  readonly managedTeamId: TeamId | null
  readonly initialViewMode?: LeagueCalendarViewMode
}

export type LeagueCalendarUiAction =
  | {
      readonly type: 'set_view_mode'
      readonly viewMode: LeagueCalendarViewMode
    }
  | {
      readonly type: 'set_scope'
      readonly scope: CalendarScope
    }
  | {
      readonly type: 'set_broadcast'
      readonly broadcast: BroadcastFilter
    }
  | {
      readonly type: 'show_month'
      readonly month: YearMonth
    }
  | {
      readonly type: 'select_date'
      readonly date: LocalDate
    }
  | {
      readonly type: 'clear_selection'
    }

/**
 * Initializes selection from the stored current date when it is in range,
 * otherwise from the range start, without advancing the stored season.
 */
export function createLeagueCalendarUiState({
  range,
  currentDate,
  managedTeamId,
  initialViewMode = 'calendar',
}: CreateLeagueCalendarUiStateInput): LeagueCalendarUiState {
  const validCurrentDate = parseLocalDate(currentDate)
  const currentMonth = yearMonthFromLocalDate(validCurrentDate)
  const currentInRange = range.months.some((month) => month === currentMonth)

  return Object.freeze({
    viewMode: parseViewMode(initialViewMode),
    scope: managedTeamId === null ? 'all_teams' : 'managed_team',
    broadcast: 'all',
    visibleMonth: currentInRange ? currentMonth : range.startMonth,
    selectedDate: currentInRange ? validCurrentDate : range.startDate,
  })
}

export function reduceLeagueCalendarUiState(
  state: LeagueCalendarUiState,
  action: LeagueCalendarUiAction,
): LeagueCalendarUiState {
  switch (action.type) {
    case 'set_view_mode':
      return Object.freeze({
        ...state,
        viewMode: parseViewMode(action.viewMode),
      })
    case 'set_scope':
      return Object.freeze({ ...state, scope: parseScope(action.scope) })
    case 'set_broadcast':
      return Object.freeze({
        ...state,
        broadcast: parseBroadcastFilter(action.broadcast),
      })
    case 'show_month':
      return Object.freeze({
        ...state,
        visibleMonth: parseYearMonth(action.month),
      })
    case 'select_date':
      return Object.freeze({
        ...state,
        selectedDate: parseLocalDate(action.date),
      })
    case 'clear_selection':
      return Object.freeze({ ...state, selectedDate: null })
    default:
      return assertNever(action, 'League Calendar UI action')
  }
}

export function parseViewMode(value: unknown): LeagueCalendarViewMode {
  switch (value) {
    case 'calendar':
    case 'list':
    case 'by_team':
      return value
    default:
      throw new RangeError(
        `League Calendar view mode is unsupported: ${String(value)}`,
      )
  }
}

function parseScope(value: unknown): CalendarScope {
  switch (value) {
    case 'all_teams':
    case 'managed_team':
      return value
    default:
      throw new RangeError(
        `League Calendar scope is unsupported: ${String(value)}`,
      )
  }
}

