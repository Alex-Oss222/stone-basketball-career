import {
  useId,
  useMemo,
  useReducer,
  useRef,
} from 'react'
import type { ChangeEvent, MouseEvent } from 'react'
import {
  createGameDetailsViewModel,
  createTeamScheduleViewModel,
  filterTeamScheduleRows,
} from '../app/teamScheduleViewModel'
import type {
  TeamScheduleRowViewModel,
  TeamScheduleSiteFilter,
  TeamScheduleViewModel,
} from '../app/teamScheduleViewModel'
import type { LeaguePresentationBundle } from '../app/leagueSnapshotDomainAdapter'
import { buildLeagueYearMonthGrids } from '../app/calendarMonthGrid'
import type { CalendarDayCellModel, CalendarMonthGridModel } from '../app/calendarMonthGrid'
import { createLeagueYearDisplayRange } from '../app/leagueYearDisplayRange'
import { parseTeamId } from '../domain/ids'
import type { GameId, TeamId } from '../domain/ids'
import type { LocalDate } from '../domain/localDate'
import type { SeasonPhase } from '../domain/season'
import { yearMonthFromLocalDate } from '../domain/yearMonth'
import {
  createTeamScheduleUiState,
  reduceTeamScheduleUiState,
} from './teamScheduleUiState'
import type {
  TeamScheduleStage,
  TeamScheduleViewMode,
} from './teamScheduleUiState'
import {
  formatScheduleDateShort,
  formatScheduleMonthHeading,
  formatScheduledGameStatus,
} from './scheduleFormatting'
import { GameDetailsDialog } from './gameDetailsDialog'
import { SegmentedTabs } from './segmentedTabs'
import type { SegmentedTabOption } from './segmentedTabs'
import { ComingLaterPanel } from './comingLaterPanel'

const WEEKDAY_SHORT_LABELS = [
  'Sun',
  'Mon',
  'Tue',
  'Wed',
  'Thu',
  'Fri',
  'Sat',
] as const

const STAGE_TABS = [
  { value: 'preseason', label: 'Preseason', comingLater: true },
  { value: 'regular_season', label: 'Regular season' },
  { value: 'postseason', label: 'Postseason', comingLater: true },
  { value: 'offseason', label: 'Off-season', comingLater: true },
] as const satisfies readonly SegmentedTabOption<TeamScheduleStage>[]

/** Placeholder for a future stored GM identity; swap in a real name later. */
const GM_NAME_PLACEHOLDER = 'Your GM'

const VIEW_TABS = [
  { value: 'list', label: 'List' },
  { value: 'calendar', label: 'Calendar' },
  { value: 'results', label: 'Results', comingLater: true },
] as const satisfies readonly SegmentedTabOption<TeamScheduleViewMode>[]

export interface TeamSchedulePageProps extends LeaguePresentationBundle {
  readonly initialInspectedTeamId?: TeamId
  readonly initialStage?: TeamScheduleStage
  readonly initialViewMode?: TeamScheduleViewMode
  readonly initialFilter?: TeamScheduleSiteFilter
  readonly initialSelectedGameId?: GameId | null
}

export function TeamSchedulePage({
  league,
  season,
  schedule,
  calendarEntries,
  managedTeamId,
  initialInspectedTeamId,
  initialStage,
  initialViewMode,
  initialFilter,
  initialSelectedGameId,
}: TeamSchedulePageProps) {
  const [uiState, dispatch] = useReducer(
    reduceTeamScheduleUiState,
    undefined,
    () =>
      createTeamScheduleUiState({
        league,
        managedTeamId,
        initialInspectedTeamId,
        initialStage: initialStage ?? mapPhaseToStage(season.currentPhase),
        initialViewMode,
        initialFilter,
        initialSelectedGameId,
      }),
  )
  const returnFocusRef = useRef<HTMLButtonElement | null>(null)

  const range = useMemo(
    () => createLeagueYearDisplayRange(season),
    [season],
  )
  const monthGrids = useMemo(
    () => buildLeagueYearMonthGrids(range),
    [range],
  )

  const viewModel = useMemo(
    () =>
      createTeamScheduleViewModel({
        league,
        schedule,
        calendarEntries,
        inspectedTeamId: uiState.inspectedTeamId,
        managedTeamId,
        currentDate: season.currentDate,
      }),
    [
      calendarEntries,
      league,
      managedTeamId,
      schedule,
      season.currentDate,
      uiState.inspectedTeamId,
    ],
  )

  const filteredRows = useMemo(
    () => filterTeamScheduleRows(viewModel.rows, uiState.siteFilter),
    [uiState.siteFilter, viewModel.rows],
  )
  const rowsByDate = useMemo(() => {
    const map = new Map<LocalDate, TeamScheduleRowViewModel[]>()
    for (const row of filteredRows) {
      if (row.placementDate === null) continue
      const existing = map.get(row.placementDate)
      if (existing === undefined) {
        map.set(row.placementDate, [row])
      } else {
        existing.push(row)
      }
    }
    return map
  }, [filteredRows])

  const details = useMemo(
    () =>
      uiState.selectedGameId === null
        ? null
        : createGameDetailsViewModel({
            league,
            schedule,
            calendarEntries,
            gameId: uiState.selectedGameId,
            perspectiveTeamId: uiState.inspectedTeamId,
            managedTeamId,
            currentDate: season.currentDate,
          }),
    [
      calendarEntries,
      league,
      managedTeamId,
      schedule,
      season.currentDate,
      uiState.inspectedTeamId,
      uiState.selectedGameId,
    ],
  )

  const currentMonth = yearMonthFromLocalDate(season.currentDate)
  const defaultMonth = range.months.some((month) => month === currentMonth)
    ? currentMonth
    : viewModel.monthGroups[0]?.month ?? range.startMonth
  const effectiveMonth = uiState.visibleMonth ?? defaultMonth
  const monthIndex = range.months.findIndex(
    (month) => month === effectiveMonth,
  )
  const previousMonth = range.months[monthIndex - 1] ?? null
  const nextMonth = range.months[monthIndex + 1] ?? null

  const visibleGrid =
    monthGrids.find((grid) => grid.month === effectiveMonth) ?? null
  const visibleGroup =
    viewModel.monthGroups.find(
      (group) => group.month === effectiveMonth,
    ) ?? null
  const monthRows = filterTeamScheduleRows(
    visibleGroup?.rows ?? [],
    uiState.siteFilter,
  )
  const visibleUndatedRows = filterTeamScheduleRows(
    viewModel.undatedGroup.rows,
    uiState.siteFilter,
  )

  function inspectTeam(teamId: TeamId): void {
    dispatch({ type: 'inspect_team', teamId })
  }

  function handleTeamSelection(event: ChangeEvent<HTMLSelectElement>): void {
    const teamId = parseTeamId(event.currentTarget.value)
    if (!league.teams.some((team) => team.id === teamId)) {
      throw new RangeError(`Selected team ${teamId} does not belong to the league`)
    }
    inspectTeam(teamId)
  }

  function openGame(
    gameId: GameId,
    event: MouseEvent<HTMLButtonElement>,
  ): void {
    returnFocusRef.current = event.currentTarget
    dispatch({ type: 'open_game', gameId })
  }

  return (
    <div className="team-schedule-page">
      <div className="team-schedule-stage-tabs">
        <SegmentedTabs
          legend="Stage"
          name="team-schedule-stage"
          value={uiState.stage}
          options={STAGE_TABS}
          onChange={(stage) => dispatch({ type: 'set_stage', stage })}
        />
        <p className="schedule-stage-note">
          The selected stage follows the season phase. Preseason, postseason,
          and the off-season calendar fill in as the season reaches them.
        </p>
      </div>

      <TeamScheduleIdentity
        league={league}
        viewModel={viewModel}
        onInspectTeam={inspectTeam}
        onSelectTeam={handleTeamSelection}
      />

      <TeamScheduleSiteFilter
        filter={uiState.siteFilter}
        onFilter={(filter) => dispatch({ type: 'set_site_filter', filter })}
      />

      <SegmentedTabs
        legend="View"
        name="team-schedule-view"
        value={uiState.viewMode}
        options={VIEW_TABS}
        onChange={(viewMode) => dispatch({ type: 'set_view_mode', viewMode })}
      />

      <TeamScheduleSummary viewModel={viewModel} />

      {uiState.stage !== 'regular_season' ? (
        <ComingLaterPanel
          title={`${stageLabel(uiState.stage)} schedule`}
          requirement={stageRequirement(uiState.stage)}
        />
      ) : uiState.viewMode === 'results' ? (
        <ComingLaterPanel
          title="Results"
          requirement="Requires game simulation and completed game results."
        />
      ) : (
        <section
          className="team-schedule-stage-body"
          aria-labelledby="team-schedule-month-heading"
        >
          <MonthNavBar
            monthHeading={formatScheduleMonthHeading(effectiveMonth)}
            onPreviousMonth={
              previousMonth === null
                ? null
                : () =>
                    dispatch({ type: 'set_visible_month', month: previousMonth })
            }
            onNextMonth={
              nextMonth === null
                ? null
                : () =>
                    dispatch({ type: 'set_visible_month', month: nextMonth })
            }
          />

          <p
            className="team-schedule-result-count"
            role="status"
            aria-live="polite"
          >
            {monthRows.length}{' '}
            {monthRows.length === 1 ? 'game' : 'games'} in{' '}
            {formatScheduleMonthHeading(effectiveMonth)}
          </p>

          {uiState.viewMode === 'calendar' ? (
            visibleGrid === null ? null : (
              <TeamCalendarMonth
                grid={visibleGrid}
                rowsByDate={rowsByDate}
                currentDate={season.currentDate}
                inspectedTeamName={viewModel.inspectedTeamName}
                onOpenGame={openGame}
              />
            )
          ) : monthRows.length === 0 ? (
            <EmptyMonthState
              monthHeading={formatScheduleMonthHeading(effectiveMonth)}
            />
          ) : (
            <TeamScheduleTable
              rows={monthRows}
              caption={`${formatScheduleMonthHeading(effectiveMonth)} schedule for ${viewModel.inspectedTeamName}`}
              onOpenGame={openGame}
            />
          )}

          {uiState.viewMode === 'list' && visibleUndatedRows.length > 0 && (
            <UndatedTeamScheduleSection
              rows={visibleUndatedRows}
              inspectedTeamName={viewModel.inspectedTeamName}
              onOpenGame={openGame}
            />
          )}
        </section>
      )}

      <GameDetailsDialog
        details={details}
        returnFocusRef={returnFocusRef}
        onSelectGame={(gameId) => dispatch({ type: 'open_game', gameId })}
        onRequestClose={() => dispatch({ type: 'close_game' })}
      />
    </div>
  )
}

function MonthNavBar({
  monthHeading,
  onPreviousMonth,
  onNextMonth,
}: {
  readonly monthHeading: string
  readonly onPreviousMonth: (() => void) | null
  readonly onNextMonth: (() => void) | null
}) {
  return (
    <div className="team-schedule-month-nav">
      <button
        type="button"
        className="league-calendar-month-step"
        onClick={onPreviousMonth ?? undefined}
        disabled={onPreviousMonth === null}
        aria-label="Show previous month"
      >
        <span aria-hidden="true">‹</span>
      </button>
      <h2 id="team-schedule-month-heading" aria-live="polite">
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
  )
}

function TeamCalendarMonth({
  grid,
  rowsByDate,
  currentDate,
  inspectedTeamName,
  onOpenGame,
}: {
  readonly grid: CalendarMonthGridModel
  readonly rowsByDate: ReadonlyMap<LocalDate, readonly TeamScheduleRowViewModel[]>
  readonly currentDate: LocalDate
  readonly inspectedTeamName: string
  readonly onOpenGame: (
    gameId: GameId,
    event: MouseEvent<HTMLButtonElement>,
  ) => void
}) {
  const heading = formatScheduleMonthHeading(grid.month)

  return (
    <div className="league-calendar-grid-wrap">
      <table className="league-calendar-grid team-calendar-grid">
        <caption className="visually-hidden">
          {heading} calendar for {inspectedTeamName}
        </caption>
        <thead>
          <tr>
            {WEEKDAY_SHORT_LABELS.map((label) => (
              <th key={label} scope="col">
                {label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {grid.weeks.map((week) => (
            <tr key={week.days[0].date}>
              {week.days.map((day) => (
                <TeamCalendarDayCell
                  key={day.date}
                  day={day}
                  rows={rowsByDate.get(day.date) ?? []}
                  isCurrent={day.date === currentDate}
                  onOpenGame={onOpenGame}
                />
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function TeamCalendarDayCell({
  day,
  rows,
  isCurrent,
  onOpenGame,
}: {
  readonly day: CalendarDayCellModel
  readonly rows: readonly TeamScheduleRowViewModel[]
  readonly isCurrent: boolean
  readonly onOpenGame: (
    gameId: GameId,
    event: MouseEvent<HTMLButtonElement>,
  ) => void
}) {
  const dayNumber = Number(day.date.slice(8, 10))
  const className = [
    'league-calendar-cell',
    day.belongsToMonth ? '' : 'is-adjacent',
    isCurrent && day.belongsToMonth ? 'is-current' : '',
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

  return (
    <td className={className}>
      <div className="team-calendar-cell-inner">
        <span className="league-calendar-daynumber">{dayNumber}</span>
        {isCurrent && (
          <span className="league-calendar-today" aria-hidden="true">
            Today
          </span>
        )}
        <div className="league-calendar-chips">
          {rows.map((row) => (
            <button
              key={row.gameId}
              type="button"
              className={`league-calendar-chip is-game team-calendar-chip site-${row.site}`}
              onClick={(event) => onOpenGame(row.gameId, event)}
              aria-label={`Open game ${row.scheduleSequence}: ${row.site === 'home' ? 'vs' : 'at'} ${row.opponentName}`}
            >
              {row.site === 'home' ? 'vs' : '@'} {row.opponentAbbreviation}
            </button>
          ))}
        </div>
      </div>
    </td>
  )
}

function TeamScheduleIdentity({
  league,
  viewModel,
  onInspectTeam,
  onSelectTeam,
}: {
  readonly league: LeaguePresentationBundle['league']
  readonly viewModel: TeamScheduleViewModel
  readonly onInspectTeam: (teamId: TeamId) => void
  readonly onSelectTeam: (event: ChangeEvent<HTMLSelectElement>) => void
}) {
  const selectorId = useId()
  const isInspectingManagedTeam = viewModel.isManagedTeamSchedule
  const controlledTeamId = viewModel.managedTeamId

  return (
    <section
      className="team-schedule-toolbar"
      aria-labelledby="team-schedule-inspected-team"
    >
      <div className="team-schedule-identity">
        <p className="page-status">Inspected team schedule</p>
        <h2 id="team-schedule-inspected-team">
          {viewModel.inspectedTeamName}{' '}
          <span>({viewModel.inspectedTeamAbbreviation})</span>
        </h2>
        {isInspectingManagedTeam && (
          <p className="managed-team-label">
            <span aria-hidden="true">★</span> {GM_NAME_PLACEHOLDER}
          </p>
        )}
      </div>

      <div className="team-schedule-team-selector">
        <label htmlFor={selectorId}>Team</label>
        <select
          id={selectorId}
          value={viewModel.inspectedTeamId}
          onChange={onSelectTeam}
        >
          {league.teams.map((team) => (
            <option key={team.id} value={team.id}>
              {team.city} {team.nickname} ({team.abbreviation})
              {team.id === viewModel.managedTeamId
                ? ` — ${GM_NAME_PLACEHOLDER}`
                : ''}
            </option>
          ))}
        </select>
        {!isInspectingManagedTeam && controlledTeamId !== null && (
          <button
            type="button"
            className="return-managed-team-button"
            onClick={() => onInspectTeam(controlledTeamId)}
          >
            Return to my team
          </button>
        )}
      </div>
    </section>
  )
}

function TeamScheduleSiteFilter({
  filter,
  onFilter,
}: {
  readonly filter: TeamScheduleSiteFilter
  readonly onFilter: (filter: TeamScheduleSiteFilter) => void
}) {
  return (
    <fieldset className="team-schedule-site-filters">
      <legend>Game site</legend>
      {(['all', 'home', 'away'] as const).map((value) => (
        <label
          key={value}
          className={
            filter === value
              ? 'team-schedule-filter is-active'
              : 'team-schedule-filter'
          }
        >
          <input
            type="radio"
            name="team-schedule-site"
            value={value}
            checked={filter === value}
            onChange={() => onFilter(value)}
          />
          {filterLabel(value)}
        </label>
      ))}
    </fieldset>
  )
}

function TeamScheduleSummary({
  viewModel,
}: {
  readonly viewModel: TeamScheduleViewModel
}) {
  const nextGame = viewModel.rows.find((row) => row.isNextScheduledGame)

  return (
    <section
      className="team-schedule-summary"
      aria-labelledby="team-schedule-summary-heading"
    >
      <h2 id="team-schedule-summary-heading" className="visually-hidden">
        Schedule summary
      </h2>
      <dl>
        <div>
          <dt>Total games</dt>
          <dd>{viewModel.totalGameCount}</dd>
        </div>
        <div>
          <dt>Home games</dt>
          <dd>{viewModel.homeGameCount}</dd>
        </div>
        <div>
          <dt>Away games</dt>
          <dd>{viewModel.awayGameCount}</dd>
        </div>
        <div>
          <dt>Next scheduled game</dt>
          <dd>
            {nextGame === undefined ? (
              'None'
            ) : nextGame.placementDate === null ? (
              'TBA'
            ) : (
              <time dateTime={nextGame.placementDate}>
                {formatScheduleDateShort(nextGame.placementDate)}
              </time>
            )}
          </dd>
        </div>
      </dl>
    </section>
  )
}

function UndatedTeamScheduleSection({
  rows,
  inspectedTeamName,
  onOpenGame,
}: {
  readonly rows: readonly TeamScheduleRowViewModel[]
  readonly inspectedTeamName: string
  readonly onOpenGame: (
    gameId: GameId,
    event: MouseEvent<HTMLButtonElement>,
  ) => void
}) {
  return (
    <section
      className="team-schedule-month team-schedule-undated"
      aria-labelledby="team-schedule-undated-heading"
    >
      <header className="team-schedule-month-header">
        <div>
          <h2 id="team-schedule-undated-heading">Date to be announced</h2>
          <span>{rows.length} undated games</span>
        </div>
      </header>
      <TeamScheduleTable
        rows={rows}
        caption={`Undated schedule games for ${inspectedTeamName}`}
        onOpenGame={onOpenGame}
      />
    </section>
  )
}

function TeamScheduleTable({
  rows,
  caption,
  onOpenGame,
}: {
  readonly rows: readonly TeamScheduleRowViewModel[]
  readonly caption: string
  readonly onOpenGame: (
    gameId: GameId,
    event: MouseEvent<HTMLButtonElement>,
  ) => void
}) {
  return (
    <div className="team-schedule-table-wrap">
      <table className="team-schedule-table">
        <caption>
          {caption}. Game numbers use the one-based authoritative league
          schedule sequence.
        </caption>
        <thead>
          <tr>
            <th scope="col">Game</th>
            <th scope="col">Date</th>
            <th scope="col">Opponent</th>
            <th scope="col">Site</th>
            <th scope="col">Status</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <TeamScheduleTableRow
              key={row.gameId}
              row={row}
              onOpenGame={onOpenGame}
            />
          ))}
        </tbody>
      </table>
    </div>
  )
}

function TeamScheduleTableRow({
  row,
  onOpenGame,
}: {
  readonly row: TeamScheduleRowViewModel
  readonly onOpenGame: (
    gameId: GameId,
    event: MouseEvent<HTMLButtonElement>,
  ) => void
}) {
  const status = formatScheduledGameStatus(row.status)
  const dateLabel =
    row.placementDate === null
      ? 'TBA'
      : formatScheduleDateShort(row.placementDate)

  return (
    <tr
      data-schedule-game={row.gameId}
      className={[
        row.isPastDate ? 'is-past' : '',
        row.isCurrentDate ? 'is-current' : '',
        row.isNextScheduledGame ? 'is-next' : '',
      ]
        .filter(Boolean)
        .join(' ')}
    >
      <th scope="row" data-label="Game">
        <button
          type="button"
          className="team-schedule-game-button"
          onClick={(event) => onOpenGame(row.gameId, event)}
          aria-label={`Open game ${row.scheduleSequence} details: ${row.opponentName}, ${row.site}, ${dateLabel}`}
        >
          <span>Schedule #{row.scheduleSequence}</span>
          {row.isNextScheduledGame && (
            <strong className="next-game-marker">Next game</strong>
          )}
          {row.isCurrentDate && (
            <strong className="current-date-marker">Current date</strong>
          )}
        </button>
      </th>
      <td data-label="Date">
        {row.placementDate === null ? (
          'TBA'
        ) : (
          <time dateTime={row.placementDate}>{dateLabel}</time>
        )}
      </td>
      <td data-label="Opponent">
        <strong>{row.opponentName}</strong>{' '}
        <span>({row.opponentAbbreviation})</span>
      </td>
      <td data-label="Site">{row.site === 'home' ? 'Home' : 'Away'}</td>
      <td data-label="Status">{status}</td>
    </tr>
  )
}

function EmptyMonthState({
  monthHeading,
}: {
  readonly monthHeading: string
}) {
  return (
    <section className="empty-state" aria-labelledby="team-schedule-empty-month">
      <h3 id="team-schedule-empty-month">No games in {monthHeading}</h3>
      <p>Use the month controls to move to a month with scheduled games.</p>
    </section>
  )
}

function stageLabel(stage: TeamScheduleStage): string {
  switch (stage) {
    case 'preseason':
      return 'Preseason'
    case 'regular_season':
      return 'Regular season'
    case 'postseason':
      return 'Postseason'
    case 'offseason':
      return 'Off-season'
    default:
      return assertNever(stage)
  }
}

function stageRequirement(stage: TeamScheduleStage): string {
  switch (stage) {
    case 'preseason':
      return 'Requires preseason scheduling for this rule pack.'
    case 'regular_season':
      return 'Regular-season games are available now.'
    case 'postseason':
      return 'Requires postseason qualification and a playoff bracket.'
    case 'offseason':
      return 'A fourth off-season calendar tied to the season timeline (draft, free agency, summer). It activates when the season reaches the off-season.'
    default:
      return assertNever(stage)
  }
}

/** Selects the stage tab that matches where the stored season currently is. */
function mapPhaseToStage(phase: SeasonPhase): TeamScheduleStage {
  switch (phase) {
    case 'offseason':
    case 'complete':
      return 'offseason'
    case 'training_camp':
    case 'preseason':
      return 'preseason'
    case 'regular_season':
      return 'regular_season'
    case 'postseason':
      return 'postseason'
    default:
      return assertNever(phase)
  }
}

function filterLabel(filter: TeamScheduleSiteFilter): string {
  switch (filter) {
    case 'all':
      return 'All'
    case 'home':
      return 'Home'
    case 'away':
      return 'Away'
    default:
      return assertNever(filter)
  }
}

function assertNever(value: never): never {
  throw new RangeError(`Unsupported Team Schedule value: ${String(value)}`)
}
