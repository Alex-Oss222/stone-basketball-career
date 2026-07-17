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
  TeamScheduleMonthGroupViewModel,
  TeamScheduleRowViewModel,
  TeamScheduleSiteFilter,
  TeamScheduleViewModel,
} from '../app/teamScheduleViewModel'
import type { LeaguePresentationBundle } from '../app/leagueSnapshotDomainAdapter'
import { parseTeamId } from '../domain/ids'
import type { GameId, TeamId } from '../domain/ids'
import {
  createTeamScheduleUiState,
  reduceTeamScheduleUiState,
} from './teamScheduleUiState'
import {
  formatScheduleDateShort,
  formatScheduleMonthHeading,
  formatScheduledGameStatus,
} from './scheduleFormatting'
import { GameDetailsDialog } from './gameDetailsDialog'

export interface TeamSchedulePageProps extends LeaguePresentationBundle {
  readonly initialInspectedTeamId?: TeamId
  readonly initialFilter?: TeamScheduleSiteFilter
  readonly initialSelectedGameId?: GameId | null
}

interface VisibleMonthGroup {
  readonly source: TeamScheduleMonthGroupViewModel
  readonly rows: readonly TeamScheduleRowViewModel[]
  readonly homeGameCount: number
  readonly awayGameCount: number
  readonly containsNextScheduledGame: boolean
}

export function TeamSchedulePage({
  league,
  season,
  schedule,
  calendarEntries,
  managedTeamId,
  initialInspectedTeamId,
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
        initialFilter,
        initialSelectedGameId,
      }),
  )
  const returnFocusRef = useRef<HTMLButtonElement | null>(null)

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
  const visibleMonthGroups = useMemo(
    () =>
      Object.freeze(
        viewModel.monthGroups.flatMap((group) => {
          const rows = filterTeamScheduleRows(
            group.rows,
            uiState.siteFilter,
          )
          if (rows.length === 0) return []
          return [
            Object.freeze({
              source: group,
              rows,
              homeGameCount: countRows(rows, 'home'),
              awayGameCount: countRows(rows, 'away'),
              containsNextScheduledGame: rows.some(
                (row) => row.isNextScheduledGame,
              ),
            }),
          ]
        }),
      ),
    [uiState.siteFilter, viewModel.monthGroups],
  )
  const visibleUndatedRows = useMemo(
    () =>
      filterTeamScheduleRows(
        viewModel.undatedGroup.rows,
        uiState.siteFilter,
      ),
    [uiState.siteFilter, viewModel.undatedGroup.rows],
  )
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
      <TeamScheduleToolbar
        league={league}
        viewModel={viewModel}
        filter={uiState.siteFilter}
        onInspectTeam={inspectTeam}
        onSelectTeam={handleTeamSelection}
        onFilter={(filter) =>
          dispatch({ type: 'set_site_filter', filter })
        }
      />

      <TeamScheduleSummary viewModel={viewModel} />

      <p className="team-schedule-result-count" role="status" aria-live="polite">
        Showing {filteredRows.length} of {viewModel.totalGameCount} games
      </p>

      {filteredRows.length === 0 ? (
        <FilteredScheduleEmptyState
          filter={uiState.siteFilter}
          onClear={() =>
            dispatch({ type: 'set_site_filter', filter: 'all' })
          }
        />
      ) : (
        <>
          <div className="team-schedule-months">
            {visibleMonthGroups.map((group) => (
              <TeamScheduleMonthSection
                key={group.source.month}
                group={group}
                inspectedTeamName={viewModel.inspectedTeamName}
                onOpenGame={openGame}
              />
            ))}
          </div>

          {visibleUndatedRows.length > 0 && (
            <UndatedTeamScheduleSection
              rows={visibleUndatedRows}
              inspectedTeamName={viewModel.inspectedTeamName}
              onOpenGame={openGame}
            />
          )}
        </>
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

function TeamScheduleToolbar({
  league,
  viewModel,
  filter,
  onInspectTeam,
  onSelectTeam,
  onFilter,
}: {
  readonly league: LeaguePresentationBundle['league']
  readonly viewModel: TeamScheduleViewModel
  readonly filter: TeamScheduleSiteFilter
  readonly onInspectTeam: (teamId: TeamId) => void
  readonly onSelectTeam: (event: ChangeEvent<HTMLSelectElement>) => void
  readonly onFilter: (filter: TeamScheduleSiteFilter) => void
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
            <span aria-hidden="true">★</span> Managed team
          </p>
        )}
      </div>

      <div className="team-schedule-controls">
        <div className="team-schedule-team-selector">
          <label htmlFor={selectorId}>Inspect team</label>
          <select
            id={selectorId}
            value={viewModel.inspectedTeamId}
            onChange={onSelectTeam}
          >
            {league.teams.map((team) => (
              <option key={team.id} value={team.id}>
                {team.city} {team.nickname} ({team.abbreviation})
                {team.id === viewModel.managedTeamId ? ' — Managed team' : ''}
              </option>
            ))}
          </select>
          {!isInspectingManagedTeam && controlledTeamId !== null && (
            <button
              type="button"
              className="return-managed-team-button"
              onClick={() => onInspectTeam(controlledTeamId)}
            >
              Return to managed team
            </button>
          )}
        </div>

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
      </div>
    </section>
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

function TeamScheduleMonthSection({
  group,
  inspectedTeamName,
  onOpenGame,
}: {
  readonly group: VisibleMonthGroup
  readonly inspectedTeamName: string
  readonly onOpenGame: (
    gameId: GameId,
    event: MouseEvent<HTMLButtonElement>,
  ) => void
}) {
  const headingId = `team-schedule-month-${group.source.month}`
  const heading = formatScheduleMonthHeading(group.source.month)

  return (
    <section className="team-schedule-month" aria-labelledby={headingId}>
      <header className="team-schedule-month-header">
        <div>
          <h2 id={headingId}>{heading}</h2>
          {group.containsNextScheduledGame && (
            <span className="next-game-month-marker">Contains next game</span>
          )}
        </div>
        <dl aria-label={`${heading} schedule totals`}>
          <div>
            <dt>Games</dt>
            <dd>{group.rows.length}</dd>
          </div>
          <div>
            <dt>Home</dt>
            <dd>{group.homeGameCount}</dd>
          </div>
          <div>
            <dt>Away</dt>
            <dd>{group.awayGameCount}</dd>
          </div>
        </dl>
      </header>
      <TeamScheduleTable
        rows={group.rows}
        caption={`${heading} schedule for ${inspectedTeamName}`}
        onOpenGame={onOpenGame}
      />
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

function FilteredScheduleEmptyState({
  filter,
  onClear,
}: {
  readonly filter: TeamScheduleSiteFilter
  readonly onClear: () => void
}) {
  const description =
    filter === 'all'
      ? 'No games match this filter.'
      : `No ${filter} games match this filter.`

  return (
    <section className="empty-state" aria-labelledby="schedule-filter-empty">
      <h2 id="schedule-filter-empty">No matching games</h2>
      <p>{description}</p>
      {filter !== 'all' && (
        <button type="button" onClick={onClear}>
          Clear filter
        </button>
      )}
    </section>
  )
}

function countRows(
  rows: readonly TeamScheduleRowViewModel[],
  site: 'home' | 'away',
): number {
  return rows.filter((row) => row.site === site).length
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
