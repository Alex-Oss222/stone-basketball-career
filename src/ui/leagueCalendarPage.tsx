import { useMemo, useReducer } from 'react'
import type {
  CalendarEntryStatus,
  CalendarEntryViewModel,
} from '../app/calendarViewModel'
import { buildLeagueYearMonthGrids } from '../app/calendarMonthGrid'
import {
  createLeagueYearCalendarModel,
} from '../app/enrichedCalendarViewModel'
import type {
  CalendarScope,
  EnrichedCalendarDayCellModel,
  EnrichedCalendarMonthModel,
  SelectedDayAgendaModel,
} from '../app/enrichedCalendarViewModel'
import { createLeagueYearDisplayRange } from '../app/leagueYearDisplayRange'
import type { LeaguePresentationBundle } from '../app/leagueSnapshotDomainAdapter'
import type { LocalDate } from '../domain/localDate'
import {
  createLeagueCalendarUiState,
  reduceLeagueCalendarUiState,
} from './leagueCalendarUiState'
import type { LeagueCalendarViewMode } from './leagueCalendarUiState'
import {
  BROADCAST_TABS,
  broadcastFilterLabel,
} from './broadcastFilter'
import type { BroadcastFilter } from './broadcastFilter'
import {
  formatScheduleDateLong,
  formatScheduleDateShort,
  formatScheduleMonthHeading,
} from './scheduleFormatting'
import { SegmentedTabs } from './segmentedTabs'
import type { SegmentedTabOption } from './segmentedTabs'
import { ComingLaterPanel } from './comingLaterPanel'

const MAX_VISIBLE_ENTRIES_PER_DAY = 4

const WEEKDAY_LABELS = [
  'Sunday',
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
  'Saturday',
] as const

const WEEKDAY_SHORT_LABELS = [
  'Sun',
  'Mon',
  'Tue',
  'Wed',
  'Thu',
  'Fri',
  'Sat',
] as const

const VIEW_TABS = [
  { value: 'calendar', label: 'Calendar' },
  { value: 'list', label: 'By date' },
  { value: 'by_team', label: 'By team', comingLater: true },
] as const satisfies readonly SegmentedTabOption<LeagueCalendarViewMode>[]

const SCOPE_TABS = [
  { value: 'all_teams', label: 'All teams' },
  { value: 'managed_team', label: 'My team' },
] as const satisfies readonly SegmentedTabOption<CalendarScope>[]

export interface LeagueCalendarPageProps extends LeaguePresentationBundle {
  readonly initialViewMode?: LeagueCalendarViewMode
}

export function LeagueCalendarPage({
  season,
  calendarEntries,
  managedTeamId,
  initialViewMode,
}: LeagueCalendarPageProps) {
  const range = useMemo(
    () => createLeagueYearDisplayRange(season),
    [season],
  )
  const monthGrids = useMemo(
    () => buildLeagueYearMonthGrids(range),
    [range],
  )
  const [uiState, dispatch] = useReducer(
    reduceLeagueCalendarUiState,
    undefined,
    () =>
      createLeagueCalendarUiState({
        range,
        currentDate: season.currentDate,
        managedTeamId,
        initialViewMode,
      }),
  )

  const calendarModel = useMemo(
    () =>
      createLeagueYearCalendarModel({
        range,
        monthGrids,
        entries: calendarEntries,
        currentDate: season.currentDate,
        selectedDate: uiState.selectedDate,
        scope: uiState.scope,
        managedTeamId,
        maxVisibleEntriesPerDay: MAX_VISIBLE_ENTRIES_PER_DAY,
      }),
    [
      calendarEntries,
      managedTeamId,
      monthGrids,
      range,
      season.currentDate,
      uiState.scope,
      uiState.selectedDate,
    ],
  )

  const visibleMonthIndex = Math.max(
    0,
    range.months.findIndex((month) => month === uiState.visibleMonth),
  )
  const visibleMonth = calendarModel.months[visibleMonthIndex]
  const previousMonth = range.months[visibleMonthIndex - 1] ?? null
  const nextMonth = range.months[visibleMonthIndex + 1] ?? null

  if (visibleMonth === undefined) {
    throw new RangeError('League Calendar has no month to display')
  }

  return (
    <div className="league-calendar-page">
      <LeagueCalendarToolbar
        seasonLabel={range.seasonLabel}
        monthHeading={formatScheduleMonthHeading(visibleMonth.month)}
        viewMode={uiState.viewMode}
        scope={uiState.scope}
        broadcast={uiState.broadcast}
        canManagedScope={managedTeamId !== null}
        onPreviousMonth={
          previousMonth === null
            ? null
            : () => dispatch({ type: 'show_month', month: previousMonth })
        }
        onNextMonth={
          nextMonth === null
            ? null
            : () => dispatch({ type: 'show_month', month: nextMonth })
        }
        onViewMode={(viewMode) =>
          dispatch({ type: 'set_view_mode', viewMode })
        }
        onBroadcast={(broadcast) =>
          dispatch({ type: 'set_broadcast', broadcast })
        }
        onScope={(scope) => dispatch({ type: 'set_scope', scope })}
      />

      <div className="league-calendar-body">
        <div className="league-calendar-primary">
          {uiState.broadcast !== 'all' ? (
            <ComingLaterPanel
              title={`${broadcastFilterLabel(uiState.broadcast)} games`}
              requirement="Requires TV broadcast scheduling for this rule pack."
            />
          ) : uiState.viewMode === 'by_team' ? (
            <ComingLaterPanel
              title="By team"
              requirement="Requires a per-team league calendar filter."
            />
          ) : uiState.viewMode === 'calendar' ? (
            <CalendarMonthTable
              month={visibleMonth}
              onSelectDate={(date) =>
                dispatch({ type: 'select_date', date })
              }
            />
          ) : (
            <CalendarMonthList
              month={visibleMonth}
              onSelectDate={(date) =>
                dispatch({ type: 'select_date', date })
              }
            />
          )}

          {uiState.broadcast === 'all' &&
            (uiState.viewMode === 'calendar' ||
              uiState.viewMode === 'list') &&
            calendarModel.undatedEntries.count > 0 && (
              <UndatedEntriesSection
                entries={calendarModel.undatedEntries.entries}
              />
            )}
        </div>

        <aside className="league-calendar-aside">
          <MonthSummary month={visibleMonth} scope={uiState.scope} />
          <SelectedDayAgenda
            agenda={calendarModel.selectedDayAgenda}
            onClear={() => dispatch({ type: 'clear_selection' })}
          />
          <CalendarLegend />
        </aside>
      </div>
    </div>
  )
}

function LeagueCalendarToolbar({
  seasonLabel,
  monthHeading,
  viewMode,
  scope,
  broadcast,
  canManagedScope,
  onPreviousMonth,
  onNextMonth,
  onViewMode,
  onBroadcast,
  onScope,
}: {
  readonly seasonLabel: string
  readonly monthHeading: string
  readonly viewMode: LeagueCalendarViewMode
  readonly scope: CalendarScope
  readonly broadcast: BroadcastFilter
  readonly canManagedScope: boolean
  readonly onPreviousMonth: (() => void) | null
  readonly onNextMonth: (() => void) | null
  readonly onViewMode: (viewMode: LeagueCalendarViewMode) => void
  readonly onBroadcast: (broadcast: BroadcastFilter) => void
  readonly onScope: (scope: CalendarScope) => void
}) {
  return (
    <section
      className="league-calendar-toolbar"
      aria-labelledby="league-calendar-heading"
    >
      <div className="league-calendar-identity">
        <p className="page-status">{seasonLabel} league calendar</p>
        <div className="league-calendar-month-nav">
          <button
            type="button"
            className="league-calendar-month-step"
            onClick={onPreviousMonth ?? undefined}
            disabled={onPreviousMonth === null}
            aria-label="Show previous month"
          >
            <span aria-hidden="true">‹</span>
          </button>
          <h2 id="league-calendar-heading" aria-live="polite">
            {monthHeading}
          </h2>
          <button
            type="button"
            className="league-calendar-month-step"
            onClick={onNextMonth ?? undefined}
            disabled={onNextMonth === null}
            aria-label="Show next month"
          >
            <span aria-hidden="true">›</span>
          </button>
        </div>
      </div>

      <div className="league-calendar-controls">
        <SegmentedTabs
          legend="View"
          name="league-calendar-view"
          value={viewMode}
          options={VIEW_TABS}
          onChange={onViewMode}
        />
        <SegmentedTabs
          legend="Broadcast"
          name="league-calendar-broadcast"
          value={broadcast}
          options={BROADCAST_TABS}
          onChange={onBroadcast}
        />
        {canManagedScope && (
          <SegmentedTabs
            legend="Teams"
            name="league-calendar-scope"
            value={scope}
            options={SCOPE_TABS}
            onChange={onScope}
          />
        )}
      </div>
    </section>
  )
}

function CalendarMonthTable({
  month,
  onSelectDate,
}: {
  readonly month: EnrichedCalendarMonthModel
  readonly onSelectDate: (date: LocalDate) => void
}) {
  const heading = formatScheduleMonthHeading(month.month)

  return (
    <div className="league-calendar-grid-wrap">
      <table className="league-calendar-grid">
        <caption className="visually-hidden">
          {heading} league calendar grid, Sunday through Saturday
        </caption>
        <thead>
          <tr>
            {WEEKDAY_SHORT_LABELS.map((label, index) => (
              <th key={label} scope="col">
                <span aria-hidden="true">{label}</span>
                <span className="visually-hidden">{WEEKDAY_LABELS[index]}</span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {month.weeks.map((week) => (
            <tr key={week.days[0].date}>
              {week.days.map((day) => (
                <CalendarDayCell
                  key={day.date}
                  day={day}
                  onSelectDate={onSelectDate}
                />
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function CalendarDayCell({
  day,
  onSelectDate,
}: {
  readonly day: EnrichedCalendarDayCellModel
  readonly onSelectDate: (date: LocalDate) => void
}) {
  const dayNumber = Number(day.date.slice(8, 10))
  const className = [
    'league-calendar-cell',
    day.belongsToMonth ? '' : 'is-adjacent',
    day.isCurrentDate ? 'is-current' : '',
    day.isSelectedDate ? 'is-selected' : '',
    day.hasManagedTeamEntry ? 'has-managed' : '',
  ]
    .filter(Boolean)
    .join(' ')

  if (!day.belongsToMonth) {
    return (
      <td className={className} aria-hidden="true">
        <span className="league-calendar-daynumber">{dayNumber}</span>
      </td>
    )
  }

  const summary =
    day.entries.length === 0
      ? 'no games'
      : `${day.entries.length} ${day.entries.length === 1 ? 'entry' : 'entries'}`

  return (
    <td className={className}>
      <button
        type="button"
        className="league-calendar-daybutton"
        aria-pressed={day.isSelectedDate}
        aria-label={`${formatScheduleDateLong(day.date)}, ${summary}${day.isCurrentDate ? ', current date' : ''}`}
        onClick={() => onSelectDate(day.date)}
      >
        <span className="league-calendar-daynumber">{dayNumber}</span>
        {day.isCurrentDate && (
          <span className="league-calendar-today" aria-hidden="true">
            Today
          </span>
        )}
        <span className="league-calendar-chips">
          {day.visibleEntries.map((entry) => (
            <CalendarEntryChip key={entry.entryId} entry={entry} />
          ))}
          {day.overflowCount > 0 && (
            <span className="league-calendar-overflow">
              +{day.overflowCount} more
            </span>
          )}
        </span>
      </button>
    </td>
  )
}

function CalendarEntryChip({
  entry,
}: {
  readonly entry: CalendarEntryViewModel
}) {
  const className = [
    'league-calendar-chip',
    entry.kind === 'game' ? 'is-game' : 'is-event',
    entry.isManagedTeamEntry ? 'is-managed' : '',
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <span className={className}>
      {entry.isManagedTeamEntry && (
        <span className="managed-star" aria-hidden="true">
          ★
        </span>
      )}
      {entry.shortLabel}
    </span>
  )
}

function CalendarMonthList({
  month,
  onSelectDate,
}: {
  readonly month: EnrichedCalendarMonthModel
  readonly onSelectDate: (date: LocalDate) => void
}) {
  const dayGroups = month.weeks
    .flatMap((week) => week.days)
    .filter((day) => day.belongsToMonth && day.entries.length > 0)

  const heading = formatScheduleMonthHeading(month.month)

  if (dayGroups.length === 0) {
    return (
      <section
        className="empty-state league-calendar-empty"
        aria-labelledby="league-calendar-empty-heading"
      >
        <h3 id="league-calendar-empty-heading">No games in {heading}</h3>
        <p>Use the month controls to move to a month with scheduled games.</p>
      </section>
    )
  }

  return (
    <ol className="league-calendar-list" aria-label={`${heading} games by day`}>
      {dayGroups.map((day) => (
        <li key={day.date} className="league-calendar-list-day">
          <button
            type="button"
            className={
              day.isSelectedDate
                ? 'league-calendar-list-daybutton is-selected'
                : 'league-calendar-list-daybutton'
            }
            aria-pressed={day.isSelectedDate}
            onClick={() => onSelectDate(day.date)}
          >
            <time dateTime={day.date}>{formatScheduleDateShort(day.date)}</time>
            {day.isCurrentDate && (
              <span className="league-calendar-today">Today</span>
            )}
            <span className="league-calendar-list-count">
              {day.entries.length}{' '}
              {day.entries.length === 1 ? 'entry' : 'entries'}
            </span>
          </button>
          <ul className="league-calendar-list-entries">
            {day.entries.map((entry) => (
              <li key={entry.entryId}>
                <CalendarEntryChip entry={entry} />
              </li>
            ))}
          </ul>
        </li>
      ))}
    </ol>
  )
}

function SelectedDayAgenda({
  agenda,
  onClear,
}: {
  readonly agenda: SelectedDayAgendaModel | null
  readonly onClear: () => void
}) {
  if (agenda === null) {
    return (
      <section
        className="league-calendar-agenda"
        aria-labelledby="league-calendar-agenda-heading"
      >
        <h3 id="league-calendar-agenda-heading">Selected day</h3>
        <p>Select a day to see its games and events.</p>
      </section>
    )
  }

  return (
    <section
      className="league-calendar-agenda"
      aria-labelledby="league-calendar-agenda-heading"
    >
      <header className="league-calendar-agenda-header">
        <h3 id="league-calendar-agenda-heading">
          {formatScheduleDateLong(agenda.date)}
        </h3>
        <button type="button" onClick={onClear}>
          Clear
        </button>
      </header>

      {agenda.isEmpty ? (
        <p>No games or events are scheduled for this day.</p>
      ) : (
        <ul className="league-calendar-agenda-entries">
          {agenda.entries.map((entry) => (
            <li key={entry.entryId} className="league-calendar-agenda-entry">
              <div className="league-calendar-agenda-title">
                {entry.isManagedTeamEntry && (
                  <span className="managed-star" aria-hidden="true">
                    ★
                  </span>
                )}
                {entry.title}
              </div>
              <div className="league-calendar-agenda-meta">
                {entry.kind === 'game' ? 'Game' : 'Event'} ·{' '}
                {formatEntryStatus(entry.status)}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

function MonthSummary({
  month,
  scope,
}: {
  readonly month: EnrichedCalendarMonthModel
  readonly scope: CalendarScope
}) {
  return (
    <section
      className="league-calendar-summary"
      aria-labelledby="league-calendar-summary-heading"
    >
      <h3 id="league-calendar-summary-heading">
        {formatScheduleMonthHeading(month.month)} summary
      </h3>
      <dl>
        <div>
          <dt>Scope</dt>
          <dd>{scope === 'all_teams' ? 'All teams' : 'My team'}</dd>
        </div>
        <div>
          <dt>Dated entries</dt>
          <dd>{month.datedEntryCount}</dd>
        </div>
        <div>
          <dt>Games</dt>
          <dd>{month.gameEntryCount}</dd>
        </div>
        <div>
          <dt>Events</dt>
          <dd>{month.eventEntryCount}</dd>
        </div>
        <div>
          <dt>Managed-team entries</dt>
          <dd>{month.managedTeamEntryCount}</dd>
        </div>
      </dl>
    </section>
  )
}

function UndatedEntriesSection({
  entries,
}: {
  readonly entries: readonly CalendarEntryViewModel[]
}) {
  return (
    <section
      className="league-calendar-undated"
      aria-labelledby="league-calendar-undated-heading"
    >
      <h3 id="league-calendar-undated-heading">Date to be announced</h3>
      <ul className="league-calendar-undated-entries">
        {entries.map((entry) => (
          <li key={entry.entryId}>
            <CalendarEntryChip entry={entry} />
          </li>
        ))}
      </ul>
    </section>
  )
}

function formatEntryStatus(status: CalendarEntryStatus): string {
  switch (status) {
    case 'scheduled':
      return 'Scheduled'
    case 'postponed':
      return 'Postponed'
    case 'completed':
      return 'Completed'
    case 'cancelled':
      return 'Cancelled'
    case 'tba':
      return 'TBA'
    case 'estimated':
      return 'Estimated'
    case 'announced':
      return 'Announced'
    default:
      return assertNever(status)
  }
}

function assertNever(value: never): never {
  throw new RangeError(`Unsupported calendar value: ${String(value)}`)
}

function CalendarLegend() {
  return (
    <section
      className="league-calendar-legend"
      aria-labelledby="league-calendar-legend-heading"
    >
      <h3 id="league-calendar-legend-heading">Legend</h3>
      <ul>
        <li>
          <span className="league-calendar-chip is-game" aria-hidden="true">
            AWAY @ HOME
          </span>{' '}
          Scheduled game
        </li>
        <li>
          <span className="managed-star" aria-hidden="true">
            ★
          </span>{' '}
          Managed-team entry
        </li>
        <li>
          <span className="league-calendar-today">Today</span> Current league
          date
        </li>
      </ul>
    </section>
  )
}
