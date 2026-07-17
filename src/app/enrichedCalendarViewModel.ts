import { parseTeamId } from '../domain/ids'
import type { TeamId } from '../domain/ids'
import {
  compareLocalDates,
  parseLocalDate,
} from '../domain/localDate'
import type { LocalDate } from '../domain/localDate'
import type { YearMonth } from '../domain/yearMonth'
import {
  buildLeagueYearMonthGrids,
} from './calendarMonthGrid'
import type {
  CalendarDayCellModel,
  CalendarMonthGridModel,
  CalendarMonthWeekCount,
  CalendarWeekModel,
} from './calendarMonthGrid'
import {
  createDayAgenda,
  getDatedCalendarEntries,
  getUndatedCalendarEntries,
  groupCalendarEntriesByDate,
} from './calendarViewModel'
import type { CalendarEntryViewModel } from './calendarViewModel'
import {
  assertValidLeagueYearDisplayRange,
} from './leagueYearDisplayRange'
import type { LeagueYearDisplayRange } from './leagueYearDisplayRange'

export const CALENDAR_SCOPES = ['managed_team', 'all_teams'] as const
export type CalendarScope = (typeof CALENDAR_SCOPES)[number]

export type LeagueYearCalendarModelErrorCode =
  | 'range_invalid'
  | 'structural_grids_invalid'
  | 'current_date_out_of_range'
  | 'selected_date_out_of_range'
  | 'visible_entry_limit_invalid'
  | 'calendar_scope_invalid'
  | 'managed_team_context_required'
  | 'managed_team_context_invalid'
  | 'managed_team_context_mismatch'
  | 'calendar_entry_invalid'
  | 'duplicate_calendar_entry_id'
  | 'calendar_accounting_invalid'

/**
 * A stable application-layer validation failure for the derived calendar.
 *
 * The error does not repair, normalize, or mutate any supplied data.
 */
export class InvalidLeagueYearCalendarModelError extends Error {
  readonly code: LeagueYearCalendarModelErrorCode

  constructor(code: LeagueYearCalendarModelErrorCode, message: string) {
    super(message)
    this.name = 'InvalidLeagueYearCalendarModelError'
    this.code = code
  }
}

export interface EnrichedCalendarDayCellModel {
  readonly date: LocalDate
  readonly month: YearMonth
  readonly weekdayIndex: number
  readonly belongsToMonth: boolean
  readonly isWithinLeagueYear: boolean
  readonly isCurrentDate: boolean
  readonly isPastDate: boolean
  readonly isFutureDate: boolean
  readonly isSelectedDate: boolean
  readonly entries: readonly CalendarEntryViewModel[]
  readonly visibleEntries: readonly CalendarEntryViewModel[]
  readonly overflowEntries: readonly CalendarEntryViewModel[]
  readonly overflowCount: number
  readonly hasManagedTeamEntry: boolean
}

export type EnrichedCalendarWeekDays = readonly [
  EnrichedCalendarDayCellModel,
  EnrichedCalendarDayCellModel,
  EnrichedCalendarDayCellModel,
  EnrichedCalendarDayCellModel,
  EnrichedCalendarDayCellModel,
  EnrichedCalendarDayCellModel,
  EnrichedCalendarDayCellModel,
]

export interface EnrichedCalendarWeekModel {
  readonly days: EnrichedCalendarWeekDays
}

export interface EnrichedCalendarMonthModel {
  readonly month: YearMonth
  readonly firstDate: LocalDate
  readonly lastDate: LocalDate
  readonly weeks: readonly EnrichedCalendarWeekModel[]
  readonly weekCount: CalendarMonthWeekCount
  /**
   * Summary counts include only cells that belong to this displayed month.
   * Adjacent-month padding is deliberately excluded.
   */
  readonly datedEntryCount: number
  readonly managedTeamEntryCount: number
  readonly gameEntryCount: number
  readonly eventEntryCount: number
  readonly hasEntries: boolean
}

export interface SelectedDayAgendaModel {
  readonly date: LocalDate
  readonly entries: readonly CalendarEntryViewModel[]
  readonly managedTeamEntries: readonly CalendarEntryViewModel[]
  readonly leagueEvents: readonly CalendarEntryViewModel[]
  readonly otherEntries: readonly CalendarEntryViewModel[]
  readonly isEmpty: boolean
}

export interface UndatedCalendarEntriesModel {
  readonly entries: readonly CalendarEntryViewModel[]
  readonly games: readonly CalendarEntryViewModel[]
  readonly leagueEvents: readonly CalendarEntryViewModel[]
  readonly teamEvents: readonly CalendarEntryViewModel[]
  readonly managedTeamEntries: readonly CalendarEntryViewModel[]
  readonly count: number
  readonly isEmpty: boolean
}

export interface LeagueYearCalendarModel {
  readonly range: LeagueYearDisplayRange
  readonly scope: CalendarScope
  readonly currentDate: LocalDate
  readonly selectedDate: LocalDate | null
  readonly months: readonly EnrichedCalendarMonthModel[]
  /** Scoped, dated entries whose placement dates are inside the display range. */
  readonly datedEntries: readonly CalendarEntryViewModel[]
  readonly undatedEntries: UndatedCalendarEntriesModel
  /**
   * Scoped dated entries outside the display range. They remain authoritative
   * and may also appear on an exact matching padding cell for continuity.
   */
  readonly outOfRangeEntries: readonly CalendarEntryViewModel[]
  readonly selectedDayAgenda: SelectedDayAgendaModel | null
  readonly totalEntryCount: number
  readonly datedEntryCount: number
  readonly undatedEntryCount: number
  readonly outOfRangeEntryCount: number
}

export interface CreateLeagueYearCalendarModelInput {
  readonly range: LeagueYearDisplayRange
  readonly monthGrids: readonly CalendarMonthGridModel[]
  readonly entries: readonly CalendarEntryViewModel[]
  readonly currentDate: LocalDate
  readonly selectedDate: LocalDate | null
  readonly scope: CalendarScope
  /**
   * Explicit transient context used to validate M2.4 managed-entry markers.
   * It is not stored in the resulting model or any persistence DTO.
   */
  readonly managedTeamId: TeamId | null
  readonly maxVisibleEntriesPerDay: number
}

interface EnrichmentContext {
  readonly currentDate: LocalDate
  readonly selectedDate: LocalDate | null
  readonly maxVisibleEntriesPerDay: number
  readonly entriesByDate: ReadonlyMap<
    LocalDate,
    readonly CalendarEntryViewModel[]
  >
}

/**
 * Builds the immutable July-through-June presentation model from already
 * normalized calendar entries. It performs no I/O and owns no authoritative
 * league, schedule, event, or persistence state.
 */
export function createLeagueYearCalendarModel({
  range,
  monthGrids,
  entries,
  currentDate,
  selectedDate,
  scope,
  managedTeamId,
  maxVisibleEntriesPerDay,
}: CreateLeagueYearCalendarModelInput): LeagueYearCalendarModel {
  const validRange = validateAndDetachRange(range)
  validateStructuralMonthGrids(validRange, monthGrids)
  const validScope = parseCalendarScope(scope)
  const validManagedTeamId = validateManagedTeamContext(
    validScope,
    managedTeamId,
  )
  const validCurrentDate = parseModelDate(currentDate, 'current date')
  assertDateWithinRange(
    validCurrentDate,
    validRange,
    'current_date_out_of_range',
    'Current date',
  )
  const validSelectedDate =
    selectedDate === null
      ? null
      : parseModelDate(selectedDate, 'selected date')
  if (validSelectedDate !== null) {
    assertDateWithinRange(
      validSelectedDate,
      validRange,
      'selected_date_out_of_range',
      'Selected date',
    )
  }
  validateVisibleEntryLimit(maxVisibleEntriesPerDay)
  validateCalendarEntries(entries, validManagedTeamId)

  const scopedEntries = selectScopedEntries(entries, validScope)
  const allDatedEntries = getDatedCalendarEntries(scopedEntries)
  const undatedEntryList = getUndatedCalendarEntries(scopedEntries)
  const datedEntries: CalendarEntryViewModel[] = []
  const outOfRangeEntries: CalendarEntryViewModel[] = []

  for (const entry of allDatedEntries) {
    if (entry.date === null) {
      throw invalidModel(
        'calendar_entry_invalid',
        `Dated selector returned undated entry ${entry.entryId}`,
      )
    }

    if (isDateWithinRange(entry.date, validRange)) {
      datedEntries.push(entry)
    } else {
      outOfRangeEntries.push(entry)
    }
  }

  const frozenDatedEntries = Object.freeze(datedEntries)
  const frozenOutOfRangeEntries = Object.freeze(outOfRangeEntries)
  const undatedEntries = createUndatedEntriesModel(undatedEntryList)
  const entriesByDate = new Map(
    groupCalendarEntriesByDate(allDatedEntries).map(
      (group) => [group.date, group.entries] as const,
    ),
  )
  const context: EnrichmentContext = {
    currentDate: validCurrentDate,
    selectedDate: validSelectedDate,
    maxVisibleEntriesPerDay,
    entriesByDate,
  }
  const months = Object.freeze(
    monthGrids.map((grid) => enrichCalendarMonth(grid, context)),
  )
  const countedDatedEntries = months.reduce(
    (count, month) => count + month.datedEntryCount,
    0,
  )
  const currentOwningCellCount = countOwningCellsForDate(
    months,
    validCurrentDate,
  )
  const selectedCellCount =
    validSelectedDate === null
      ? 0
      : countSelectedCells(months)
  const selectedDayAgenda =
    validSelectedDate === null
      ? null
      : createSelectedDayAgenda(scopedEntries, validSelectedDate)
  const totalEntryCount = scopedEntries.length
  const datedEntryCount = frozenDatedEntries.length
  const undatedEntryCount = undatedEntries.count
  const outOfRangeEntryCount = frozenOutOfRangeEntries.length

  if (
    totalEntryCount !==
    datedEntryCount + undatedEntryCount + outOfRangeEntryCount
  ) {
    throw invalidModel(
      'calendar_accounting_invalid',
      'Scoped calendar entries do not form a complete dated, undated, and out-of-range partition',
    )
  }
  if (countedDatedEntries !== datedEntryCount) {
    throw invalidModel(
      'calendar_accounting_invalid',
      'Own-month calendar cells do not account for every in-range dated entry exactly once',
    )
  }
  if (
    currentOwningCellCount !== 1 ||
    (validSelectedDate !== null && selectedCellCount !== 1)
  ) {
    throw invalidModel(
      'calendar_accounting_invalid',
      'Current and selected dates must each resolve to exactly one owning calendar cell',
    )
  }

  return Object.freeze({
    range: validRange,
    scope: validScope,
    currentDate: validCurrentDate,
    selectedDate: validSelectedDate,
    months,
    datedEntries: frozenDatedEntries,
    undatedEntries,
    outOfRangeEntries: frozenOutOfRangeEntries,
    selectedDayAgenda,
    totalEntryCount,
    datedEntryCount,
    undatedEntryCount,
    outOfRangeEntryCount,
  })
}

function validateAndDetachRange(
  range: LeagueYearDisplayRange,
): LeagueYearDisplayRange {
  try {
    assertValidLeagueYearDisplayRange(range)
  } catch (error) {
    throw invalidModel(
      'range_invalid',
      `League-year display range is invalid: ${getErrorMessage(error)}`,
    )
  }

  return Object.freeze({
    startingYear: range.startingYear,
    endingYear: range.endingYear,
    startDate: range.startDate,
    endDate: range.endDate,
    startMonth: range.startMonth,
    endMonth: range.endMonth,
    seasonLabel: range.seasonLabel,
    months: Object.freeze([...range.months]),
  })
}

function validateStructuralMonthGrids(
  range: LeagueYearDisplayRange,
  monthGrids: readonly CalendarMonthGridModel[],
): void {
  if (!Array.isArray(monthGrids) || monthGrids.length !== 12) {
    throw invalidModel(
      'structural_grids_invalid',
      'League-year calendar requires exactly twelve structural month grids',
    )
  }

  const expectedGrids = buildLeagueYearMonthGrids(range)
  for (let monthIndex = 0; monthIndex < expectedGrids.length; monthIndex += 1) {
    const expected = expectedGrids[monthIndex]
    const actual = monthGrids[monthIndex]
    if (actual === undefined || !monthGridsMatch(actual, expected)) {
      throw invalidModel(
        'structural_grids_invalid',
        `Structural month grid at index ${monthIndex} does not match the supplied league-year range`,
      )
    }
  }
}

function monthGridsMatch(
  actual: CalendarMonthGridModel,
  expected: CalendarMonthGridModel,
): boolean {
  if (
    actual.month !== expected.month ||
    actual.firstDate !== expected.firstDate ||
    actual.lastDate !== expected.lastDate ||
    actual.weekCount !== expected.weekCount ||
    !Array.isArray(actual.weeks) ||
    actual.weeks.length !== expected.weeks.length
  ) {
    return false
  }

  return expected.weeks.every((expectedWeek, weekIndex) => {
    const actualWeek = actual.weeks[weekIndex]
    if (
      actualWeek === undefined ||
      !Array.isArray(actualWeek.days) ||
      actualWeek.days.length !== 7
    ) {
      return false
    }

    return expectedWeek.days.every((expectedDay, dayIndex) => {
      const actualDay = actualWeek.days[dayIndex]
      return (
        actualDay !== undefined &&
        actualDay.date === expectedDay.date &&
        actualDay.month === expectedDay.month &&
        actualDay.weekdayIndex === expectedDay.weekdayIndex &&
        actualDay.belongsToMonth === expectedDay.belongsToMonth &&
        actualDay.isWithinLeagueYear === expectedDay.isWithinLeagueYear
      )
    })
  })
}

function parseCalendarScope(value: CalendarScope): CalendarScope {
  switch (value) {
    case 'managed_team':
    case 'all_teams':
      return value
    default:
      throw invalidModel(
        'calendar_scope_invalid',
        `Calendar scope is unsupported: ${String(value)}`,
      )
  }
}

function validateManagedTeamContext(
  scope: CalendarScope,
  managedTeamId: TeamId | null,
): TeamId | null {
  if (scope === 'managed_team' && managedTeamId === null) {
    throw invalidModel(
      'managed_team_context_required',
      'Managed-team calendar scope requires an explicit managed TeamId',
    )
  }

  if (managedTeamId === null) {
    return null
  }

  try {
    return parseTeamId(managedTeamId)
  } catch (error) {
    throw invalidModel(
      'managed_team_context_invalid',
      `Managed TeamId is invalid: ${getErrorMessage(error)}`,
    )
  }
}

function parseModelDate(value: unknown, label: string): LocalDate {
  try {
    return parseLocalDate(value)
  } catch (error) {
    throw invalidModel(
      'calendar_entry_invalid',
      `Calendar ${label} is invalid: ${getErrorMessage(error)}`,
    )
  }
}

function assertDateWithinRange(
  date: LocalDate,
  range: LeagueYearDisplayRange,
  code:
    | 'current_date_out_of_range'
    | 'selected_date_out_of_range',
  label: string,
): void {
  if (!isDateWithinRange(date, range)) {
    throw invalidModel(
      code,
      `${label} ${date} is outside ${range.startDate} through ${range.endDate}`,
    )
  }
}

function isDateWithinRange(
  date: LocalDate,
  range: LeagueYearDisplayRange,
): boolean {
  return (
    compareLocalDates(date, range.startDate) >= 0 &&
    compareLocalDates(date, range.endDate) <= 0
  )
}

function validateVisibleEntryLimit(value: number): void {
  if (!Number.isSafeInteger(value) || value <= 0) {
    throw invalidModel(
      'visible_entry_limit_invalid',
      'Maximum visible entries per day must be a positive safe integer',
    )
  }
}

function validateCalendarEntries(
  entries: readonly CalendarEntryViewModel[],
  managedTeamId: TeamId | null,
): void {
  if (!Array.isArray(entries)) {
    throw invalidModel(
      'calendar_entry_invalid',
      'Calendar entries must be an array',
    )
  }

  const entryIds = new Set<string>()
  for (const entry of entries) {
    if (
      entry === null ||
      typeof entry !== 'object' ||
      typeof entry.entryId !== 'string' ||
      entry.entryId.length === 0 ||
      typeof entry.sortKey !== 'string' ||
      !Array.isArray(entry.teamIds)
    ) {
      throw invalidModel(
        'calendar_entry_invalid',
        'Calendar entries must use the normalized M2.4 structure',
      )
    }
    if (!Object.isFrozen(entry) || !Object.isFrozen(entry.teamIds)) {
      throw invalidModel(
        'calendar_entry_invalid',
        `Calendar entry ${entry.entryId} must be immutable`,
      )
    }
    if (entryIds.has(entry.entryId)) {
      throw invalidModel(
        'duplicate_calendar_entry_id',
        `Calendar entry ID ${entry.entryId} appears more than once`,
      )
    }
    entryIds.add(entry.entryId)

    if (entry.date !== null) {
      parseModelDate(entry.date, `entry ${entry.entryId} placement date`)
    }

    for (const teamId of entry.teamIds) {
      try {
        parseTeamId(teamId)
      } catch (error) {
        throw invalidModel(
          'calendar_entry_invalid',
          `Calendar entry ${entry.entryId} has an invalid TeamId: ${getErrorMessage(error)}`,
        )
      }
    }

    const expectedManagedMarker =
      managedTeamId !== null && entry.teamIds.includes(managedTeamId)
    if (entry.isManagedTeamEntry !== expectedManagedMarker) {
      throw invalidModel(
        'managed_team_context_mismatch',
        `Calendar entry ${entry.entryId} does not match the supplied managed-team context`,
      )
    }
  }
}

function selectScopedEntries(
  entries: readonly CalendarEntryViewModel[],
  scope: CalendarScope,
): readonly CalendarEntryViewModel[] {
  const candidates =
    scope === 'all_teams'
      ? [...entries]
      : entries.filter(
          (entry) =>
            entry.kind === 'league_event' || entry.isManagedTeamEntry,
        )
  const dated = getDatedCalendarEntries(candidates)
  const undated = getUndatedCalendarEntries(candidates)
  return Object.freeze([...dated, ...undated])
}

function enrichCalendarMonth(
  grid: CalendarMonthGridModel,
  context: EnrichmentContext,
): EnrichedCalendarMonthModel {
  const weeks = Object.freeze(
    grid.weeks.map((week) => enrichCalendarWeek(week, context)),
  )
  let datedEntryCount = 0
  let managedTeamEntryCount = 0
  let gameEntryCount = 0
  let eventEntryCount = 0

  for (const week of weeks) {
    for (const day of week.days) {
      if (!day.belongsToMonth || !day.isWithinLeagueYear) {
        continue
      }

      for (const entry of day.entries) {
        datedEntryCount += 1
        if (entry.isManagedTeamEntry) {
          managedTeamEntryCount += 1
        }
        if (entry.kind === 'game') {
          gameEntryCount += 1
        } else {
          eventEntryCount += 1
        }
      }
    }
  }

  return Object.freeze({
    month: grid.month,
    firstDate: grid.firstDate,
    lastDate: grid.lastDate,
    weeks,
    weekCount: grid.weekCount,
    datedEntryCount,
    managedTeamEntryCount,
    gameEntryCount,
    eventEntryCount,
    hasEntries: datedEntryCount > 0,
  })
}

function enrichCalendarWeek(
  week: CalendarWeekModel,
  context: EnrichmentContext,
): EnrichedCalendarWeekModel {
  const [
    sunday,
    monday,
    tuesday,
    wednesday,
    thursday,
    friday,
    saturday,
  ] = week.days
  const days = Object.freeze([
    enrichCalendarDay(sunday, context),
    enrichCalendarDay(monday, context),
    enrichCalendarDay(tuesday, context),
    enrichCalendarDay(wednesday, context),
    enrichCalendarDay(thursday, context),
    enrichCalendarDay(friday, context),
    enrichCalendarDay(saturday, context),
  ] as const)

  return Object.freeze({ days })
}

function enrichCalendarDay(
  cell: CalendarDayCellModel,
  context: EnrichmentContext,
): EnrichedCalendarDayCellModel {
  const entries = Object.freeze([
    ...(context.entriesByDate.get(cell.date) ?? []),
  ])
  const visibleEntries = Object.freeze(
    entries.slice(0, context.maxVisibleEntriesPerDay),
  )
  const overflowEntries = Object.freeze(
    entries.slice(context.maxVisibleEntriesPerDay),
  )
  const dateComparison = compareLocalDates(cell.date, context.currentDate)

  return Object.freeze({
    date: cell.date,
    month: cell.month,
    weekdayIndex: cell.weekdayIndex,
    belongsToMonth: cell.belongsToMonth,
    isWithinLeagueYear: cell.isWithinLeagueYear,
    isCurrentDate: dateComparison === 0,
    isPastDate: dateComparison < 0,
    isFutureDate: dateComparison > 0,
    isSelectedDate:
      cell.belongsToMonth &&
      context.selectedDate !== null &&
      cell.date === context.selectedDate,
    entries,
    visibleEntries,
    overflowEntries,
    overflowCount: overflowEntries.length,
    hasManagedTeamEntry: entries.some(
      (entry) => entry.isManagedTeamEntry,
    ),
  })
}

function createSelectedDayAgenda(
  entries: readonly CalendarEntryViewModel[],
  date: LocalDate,
): SelectedDayAgendaModel {
  const agendaEntries = createDayAgenda(entries, date)
  const leagueEvents = freezeSelectedEntries(
    agendaEntries,
    (entry) => entry.kind === 'league_event',
  )
  const managedTeamEntries = freezeSelectedEntries(
    agendaEntries,
    (entry) =>
      entry.kind !== 'league_event' && entry.isManagedTeamEntry,
  )
  const otherEntries = freezeSelectedEntries(
    agendaEntries,
    (entry) =>
      entry.kind !== 'league_event' && !entry.isManagedTeamEntry,
  )

  if (
    agendaEntries.length !==
    leagueEvents.length + managedTeamEntries.length + otherEntries.length
  ) {
    throw invalidModel(
      'calendar_accounting_invalid',
      `Selected-day agenda for ${date} does not form a complete partition`,
    )
  }

  return Object.freeze({
    date,
    entries: agendaEntries,
    managedTeamEntries,
    leagueEvents,
    otherEntries,
    isEmpty: agendaEntries.length === 0,
  })
}

function countOwningCellsForDate(
  months: readonly EnrichedCalendarMonthModel[],
  date: LocalDate,
): number {
  let count = 0
  for (const month of months) {
    for (const week of month.weeks) {
      for (const day of week.days) {
        if (day.belongsToMonth && day.date === date) {
          count += 1
        }
      }
    }
  }
  return count
}

function countSelectedCells(
  months: readonly EnrichedCalendarMonthModel[],
): number {
  let count = 0
  for (const month of months) {
    for (const week of month.weeks) {
      for (const day of week.days) {
        if (day.isSelectedDate) {
          count += 1
        }
      }
    }
  }
  return count
}

function createUndatedEntriesModel(
  entries: readonly CalendarEntryViewModel[],
): UndatedCalendarEntriesModel {
  const frozenEntries = Object.freeze([...entries])
  const games = freezeSelectedEntries(
    frozenEntries,
    (entry) => entry.kind === 'game',
  )
  const leagueEvents = freezeSelectedEntries(
    frozenEntries,
    (entry) => entry.kind === 'league_event',
  )
  const teamEvents = freezeSelectedEntries(
    frozenEntries,
    (entry) => entry.kind === 'team_event',
  )
  const managedTeamEntries = freezeSelectedEntries(
    frozenEntries,
    (entry) => entry.isManagedTeamEntry,
  )

  if (
    frozenEntries.length !==
    games.length + leagueEvents.length + teamEvents.length
  ) {
    throw invalidModel(
      'calendar_accounting_invalid',
      'Undated calendar entries do not form a complete kind partition',
    )
  }

  return Object.freeze({
    entries: frozenEntries,
    games,
    leagueEvents,
    teamEvents,
    managedTeamEntries,
    count: frozenEntries.length,
    isEmpty: frozenEntries.length === 0,
  })
}

function freezeSelectedEntries(
  entries: readonly CalendarEntryViewModel[],
  predicate: (entry: CalendarEntryViewModel) => boolean,
): readonly CalendarEntryViewModel[] {
  return Object.freeze(entries.filter(predicate))
}

function invalidModel(
  code: LeagueYearCalendarModelErrorCode,
  message: string,
): InvalidLeagueYearCalendarModelError {
  return new InvalidLeagueYearCalendarModelError(code, message)
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}
