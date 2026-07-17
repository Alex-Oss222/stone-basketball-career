import {
  formatLocalDateForDisplay,
  groupGamesByGameDay,
  isManagedTeamGame,
  resolveOpponent,
} from '../app/scheduleViewModel'
import type { LeaguePresentationBundle } from '../app/leagueSnapshotDomainAdapter'
import type { TeamScheduleSiteFilter } from '../app/teamScheduleViewModel'
import type { GameId, TeamId } from '../domain/ids'
import type { LeagueSnapshotV2 } from '../persistence/leagueSnapshotV2'
import { DashboardCard } from './dashboardShell'
import { formatTeamName } from './leagueViewModel'
import { TeamSchedulePage } from './teamSchedulePage'

export type { TeamScheduleSiteFilter } from '../app/teamScheduleViewModel'

export interface SchedulePageProps {
  readonly snapshot: LeagueSnapshotV2 | null
}

export interface TeamScheduleContentProps {
  readonly presentation: LeaguePresentationBundle | null
  readonly initialInspectedTeamId?: TeamId
  readonly initialFilter?: TeamScheduleSiteFilter
  readonly initialSelectedGameId?: GameId | null
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
  presentation,
  initialInspectedTeamId,
  initialFilter,
  initialSelectedGameId,
}: TeamScheduleContentProps) {
  if (presentation === null) return <NoLeagueScheduleAvailable />

  return (
    <TeamSchedulePage
      {...presentation}
      initialInspectedTeamId={initialInspectedTeamId}
      initialFilter={initialFilter}
      initialSelectedGameId={initialSelectedGameId}
    />
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
