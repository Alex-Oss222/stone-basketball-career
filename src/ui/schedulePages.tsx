import { useId, useState } from 'react'
import {
  calculateTeamScheduleTotals,
  filterTeamScheduleGames,
  formatLocalDateForDisplay,
  getTeamLocation,
  getTeamScheduleGames,
  groupGamesByGameDay,
  isManagedTeamGame,
  resolveOpponent,
} from '../app/scheduleViewModel'
import type { TeamScheduleFilter } from '../app/scheduleViewModel'
import type {
  LeagueSnapshotV2,
  LeagueSnapshotV2ScheduledGameDto,
} from '../persistence/leagueSnapshotV2'
import { DashboardCard } from './dashboardShell'
import { formatTeamName } from './leagueViewModel'

export type { TeamScheduleFilter } from '../app/scheduleViewModel'

export interface SchedulePageProps {
  readonly snapshot: LeagueSnapshotV2 | null
}

export interface TeamScheduleContentProps extends SchedulePageProps {
  readonly initialFilter?: TeamScheduleFilter
}

const GAME_STATUS_LABELS = Object.freeze({
  scheduled: 'Scheduled',
  postponed: 'Postponed',
  completed: 'Completed',
  cancelled: 'Cancelled',
})

const PUBLICATION_STATUS_LABELS = Object.freeze({
  draft: 'Draft',
  published: 'Published',
  in_progress: 'In progress',
  complete: 'Complete',
})

export function TeamScheduleContent({
  snapshot,
  initialFilter = 'all',
}: TeamScheduleContentProps) {
  const [filter, setFilter] = useState<TeamScheduleFilter>(initialFilter)
  const filterId = useId()

  if (snapshot === null) return <NoLeagueScheduleAvailable />

  const managedTeam =
    snapshot.managedTeamId === null
      ? null
      : snapshot.league.teams.find(
          (team) => team.id === snapshot.managedTeamId,
        ) ?? null

  if (managedTeam === null) {
    return (
      <section
        className="empty-state"
        aria-labelledby="team-schedule-no-team-heading"
      >
        <h2 id="team-schedule-no-team-heading">No managed team selected</h2>
        <p>Choose a team before opening its regular-season schedule.</p>
      </section>
    )
  }

  const allGames = getTeamScheduleGames(
    snapshot.leagueSchedule,
    managedTeam.id,
  )
  const games = filterTeamScheduleGames(
    snapshot.leagueSchedule,
    managedTeam.id,
    filter,
  )
  const totals = calculateTeamScheduleTotals(
    snapshot.leagueSchedule,
    managedTeam.id,
  )
  const gameDayGroups = groupGamesByGameDay(snapshot.leagueSchedule)
  const gameDaysByGameId = new Map(
    gameDayGroups.flatMap(({ gameDay, games: groupedGames }) =>
      groupedGames.map((game) => [game.id, gameDay] as const),
    ),
  )

  return (
    <div className="team-schedule-content league-players-content">
      <p className="content-count" role="status" aria-live="polite">
        {games.length} {filter === 'all' ? 'scheduled games' : `${filter} games`}
      </p>

      <form
        className="player-filter-form"
        onSubmit={(event) => event.preventDefault()}
      >
        <div className="filter-field">
          <label htmlFor={filterId}>Schedule view</label>
          <select
            id={filterId}
            value={filter}
            onChange={(event) => {
              const nextFilter = event.currentTarget.value
              if (isTeamScheduleFilter(nextFilter)) setFilter(nextFilter)
            }}
          >
            <option value="all">All games ({allGames.length})</option>
            <option value="home">Home games ({totals.homeGames})</option>
            <option value="away">Away games ({totals.awayGames})</option>
          </select>
        </div>
      </form>

      <div
        className="table-scroll"
        role="region"
        aria-label={`${formatTeamName(managedTeam)} schedule table`}
        tabIndex={0}
      >
        <table className="league-table">
          <caption>
            {snapshot.season.displayLabel} regular-season schedule for{' '}
            {formatTeamName(managedTeam)}
          </caption>
          <thead>
            <tr>
              <th scope="col">Game day</th>
              <th scope="col">Scheduled date</th>
              <th scope="col">Location</th>
              <th scope="col">Opponent</th>
              <th scope="col">Status</th>
            </tr>
          </thead>
          <tbody>
            {games.map((game) => {
              const gameDay = gameDaysByGameId.get(game.id)
              if (gameDay === undefined) {
                throw new RangeError(
                  `Scheduled game is not assigned to a game day: ${game.id}`,
                )
              }
              const location = getTeamLocation(game, managedTeam.id)
              const opponent = resolveOpponent(
                snapshot.league,
                game,
                managedTeam.id,
              )

              return (
                <tr key={game.id} data-schedule-game={game.id}>
                  <th scope="row">{gameDay.sequenceNumber}</th>
                  <td>{renderCurrentGameDate(game)}</td>
                  <td>{location === 'home' ? 'Home' : 'Away'}</td>
                  <td>
                    {location === 'home' ? 'vs ' : 'at '}
                    {formatTeamName(opponent)} ({opponent.abbreviation})
                  </td>
                  <td>{GAME_STATUS_LABELS[game.status]}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export function ScheduleCalendarContent({ snapshot }: SchedulePageProps) {
  if (snapshot === null) return <NoLeagueScheduleAvailable />

  const managedTeamId = snapshot.managedTeamId
  const gameDayGroups = groupGamesByGameDay(snapshot.leagueSchedule)

  return (
    <div className="schedule-calendar-content">
      <p className="content-count">
        {snapshot.leagueSchedule.gameDays.length} game days ·{' '}
        {snapshot.leagueSchedule.games.length} games
      </p>

      {gameDayGroups.map(({ gameDay, games }) => {
        const headingId = `schedule-game-day-${gameDay.sequenceNumber}`

        return (
          <section
            key={gameDay.id}
            data-game-day={gameDay.sequenceNumber}
            aria-labelledby={headingId}
          >
            <h2 id={headingId}>
              Game day {gameDay.sequenceNumber} ·{' '}
              <time dateTime={gameDay.scheduledDate}>
                {formatLocalDateForDisplay(gameDay.scheduledDate)}
              </time>
            </h2>
            <div
              className="table-scroll"
              role="region"
              aria-label={`Game day ${gameDay.sequenceNumber} matchups`}
              tabIndex={0}
            >
              <table className="league-table">
                <caption>
                  All matchups for game day {gameDay.sequenceNumber} on{' '}
                  {formatLocalDateForDisplay(gameDay.scheduledDate)}
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Away team</th>
                    <th scope="col">Home team</th>
                    <th scope="col">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {games.map((game) => {
                    const awayTeam = resolveOpponent(
                      snapshot.league,
                      game,
                      game.homeTeamId,
                    )
                    const homeTeam = resolveOpponent(
                      snapshot.league,
                      game,
                      game.awayTeamId,
                    )

                    return (
                      <tr key={game.id} data-calendar-game={game.id}>
                        <th scope="row">
                          {formatTeamName(awayTeam)} ({awayTeam.abbreviation})
                          {isManagedTeamGame(game, managedTeamId) &&
                            managedTeamId === awayTeam.id && (
                              <ManagedTeamMarker />
                            )}
                        </th>
                        <td>
                          {formatTeamName(homeTeam)} ({homeTeam.abbreviation})
                          {isManagedTeamGame(game, managedTeamId) &&
                            managedTeamId === homeTeam.id && (
                              <ManagedTeamMarker />
                            )}
                        </td>
                        <td>{GAME_STATUS_LABELS[game.status]}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </section>
        )
      })}
    </div>
  )
}

export function LeagueScheduleOverviewContent({ snapshot }: SchedulePageProps) {
  if (snapshot === null) return <NoLeagueScheduleAvailable />

  const schedule = snapshot.leagueSchedule
  const regularSeasonGameCount = schedule.games.filter(
    (game) => game.stage === 'regular_season',
  ).length

  return (
    <div className="dashboard-overview-content">
      <DashboardCard title="Season schedule">
        <dl className="dashboard-facts" aria-label="Season schedule summary">
          <div>
            <dt>Season</dt>
            <dd>{snapshot.season.displayLabel}</dd>
          </div>
          <div>
            <dt>Publication status</dt>
            <dd>{PUBLICATION_STATUS_LABELS[schedule.publicationStatus]}</dd>
          </div>
          <div>
            <dt>Game days</dt>
            <dd>{schedule.gameDays.length}</dd>
          </div>
          <div>
            <dt>Regular-season games</dt>
            <dd>{regularSeasonGameCount}</dd>
          </div>
          <div>
            <dt>Teams</dt>
            <dd>{snapshot.league.teams.length}</dd>
          </div>
        </dl>
      </DashboardCard>
    </div>
  )
}

function ManagedTeamMarker() {
  return <span aria-label="Managed team"> · Managed team</span>
}

function NoLeagueScheduleAvailable() {
  return (
    <section
      className="empty-state"
      aria-labelledby="league-schedule-empty-heading"
    >
      <h2 id="league-schedule-empty-heading">
        No league schedule available
      </h2>
      <p>Create or restore a league before opening its season schedule.</p>
    </section>
  )
}

function renderCurrentGameDate(game: LeagueSnapshotV2ScheduledGameDto) {
  if (game.currentScheduledDate === null) {
    return (
      <>
        TBA
        <span className="visually-hidden">
          {' '}
          (originally {formatLocalDateForDisplay(game.originalScheduledDate)})
        </span>
      </>
    )
  }

  return (
    <time dateTime={game.currentScheduledDate}>
      {formatLocalDateForDisplay(game.currentScheduledDate)}
    </time>
  )
}

function isTeamScheduleFilter(value: string): value is TeamScheduleFilter {
  return value === 'all' || value === 'home' || value === 'away'
}
