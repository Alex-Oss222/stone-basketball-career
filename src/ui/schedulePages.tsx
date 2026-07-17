import type { LeaguePresentationBundle } from '../app/leagueSnapshotDomainAdapter'
import type { TeamScheduleSiteFilter } from '../app/teamScheduleViewModel'
import type { GameId, TeamId } from '../domain/ids'
import type { LeagueSnapshot } from '../persistence/leagueSnapshot'
import { DashboardCard } from './dashboardShell'
import { LeagueCalendarPage } from './leagueCalendarPage'
import type { LeagueCalendarViewMode } from './leagueCalendarUiState'
import { TeamSchedulePage } from './teamSchedulePage'
import type {
  TeamScheduleStage,
  TeamScheduleViewMode,
} from './teamScheduleUiState'

export type { TeamScheduleSiteFilter } from '../app/teamScheduleViewModel'

export interface SchedulePageProps {
  readonly snapshot: LeagueSnapshot | null
}

export interface TeamScheduleContentProps {
  readonly presentation: LeaguePresentationBundle | null
  readonly initialInspectedTeamId?: TeamId
  readonly initialStage?: TeamScheduleStage
  readonly initialViewMode?: TeamScheduleViewMode
  readonly initialFilter?: TeamScheduleSiteFilter
  readonly initialSelectedGameId?: GameId | null
}

const PUBLICATION_STATUS_LABELS = Object.freeze({
  draft: 'Draft',
  published: 'Published',
  in_progress: 'In progress',
  complete: 'Complete',
})

export function TeamScheduleContent({
  presentation,
  initialInspectedTeamId,
  initialStage,
  initialViewMode,
  initialFilter,
  initialSelectedGameId,
}: TeamScheduleContentProps) {
  if (presentation === null) return <NoLeagueScheduleAvailable />

  return (
    <TeamSchedulePage
      {...presentation}
      initialInspectedTeamId={initialInspectedTeamId}
      initialStage={initialStage}
      initialViewMode={initialViewMode}
      initialFilter={initialFilter}
      initialSelectedGameId={initialSelectedGameId}
    />
  )
}

export interface LeagueCalendarContentProps {
  readonly presentation: LeaguePresentationBundle | null
  readonly initialViewMode?: LeagueCalendarViewMode
}

export function LeagueCalendarContent({
  presentation,
  initialViewMode,
}: LeagueCalendarContentProps) {
  if (presentation === null) return <NoLeagueScheduleAvailable />

  return (
    <LeagueCalendarPage {...presentation} initialViewMode={initialViewMode} />
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
