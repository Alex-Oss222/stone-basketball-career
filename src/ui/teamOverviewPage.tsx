import type { Position, Team } from '../domain/league'
import { POSITIONS, formatTeamName } from '../domain/league'
import type { NavigationPageId } from '../app/navigation'
import { createTeamOverviewSummary } from '../app/teamOverviewViewModel'
import type { TeamOverviewSummary } from '../app/teamOverviewViewModel'
import {
  findNextScheduledGame,
  formatLocalDateForDisplay,
  getTeamLocation,
  getUpcomingScheduledGames,
  resolveOpponent,
} from '../app/scheduleViewModel'
import type {
  LeagueSnapshot,
  LeagueSnapshotScheduledGameDto,
} from '../persistence/leagueSnapshot'
import { DashboardCard } from './dashboardShell'

export interface TeamOverviewContentProps {
  readonly snapshot: LeagueSnapshot | null
  /** The managed team; carries identity, colors, and mark for the header. */
  readonly team: Team | null
  /**
   * Card actions are live entry points into the sidebar's real pages — a
   * planned target honestly states what it still requires.
   */
  readonly onNavigate?: (pageId: NavigationPageId) => void
}

/** Fixed, position-distinct swatch colors for the roster-breakdown donut. */
const POSITION_COLORS: Readonly<Record<Position, string>> = {
  PG: '#5b8def',
  SG: '#3fb6a8',
  SF: '#e0a44b',
  PF: '#c86fd6',
  C: '#e0685f',
}

/**
 * Team Overview: the Evergreens dashboard layout, with Roster Breakdown in the
 * old Recent-Form slot and Team Metrics in the old Cap & Asset slot. Every
 * value is one of three honest states — real data that exists today (identity,
 * rating, roster composition, ages, upcoming games), a real absence, or a
 * plainly-labelled "Coming later" slot. Nothing fabricates a record, ranking,
 * score, injury, metric, or dollar amount.
 */
export function TeamOverviewContent({
  snapshot,
  team,
  onNavigate,
}: TeamOverviewContentProps) {
  if (snapshot === null || team === null) {
    return (
      <section
        className="team-overview-empty empty-state"
        aria-label="No team"
      >
        <h2>No team selected</h2>
        <p>Create a league and choose a team to open its overview.</p>
      </section>
    )
  }

  const managedTeamId = snapshot.managedTeamId
  const summary = createTeamOverviewSummary({
    league: snapshot.league,
    managedTeamId,
  })
  const nextGame =
    managedTeamId === null
      ? null
      : findNextScheduledGame(
          snapshot.leagueSchedule,
          managedTeamId,
          snapshot.season.currentDate,
        )
  const upcomingGames =
    managedTeamId === null
      ? []
      : getUpcomingScheduledGames(
          snapshot.leagueSchedule,
          managedTeamId,
          snapshot.season.currentDate,
        ).slice(0, 5)

  return (
    <div className="team-overview">
      <TeamOverviewHeader
        snapshot={snapshot}
        team={team}
        summary={summary}
        managedTeamId={managedTeamId}
        nextGame={nextGame}
      />

      <NeedsAttentionRow onNavigate={onNavigate} />

      <div className="team-overview-body">
        <div className="team-overview-column">
          <StartingFiveRotationCard onNavigate={onNavigate} />
          <StrengthsWeaknessesCard />
          <RosterBreakdownCard summary={summary} />
          <RecentTransactionsCard />
        </div>

        <div className="team-overview-column">
          <HealthSummaryCard onNavigate={onNavigate} />
          <DevelopmentWatchCard onNavigate={onNavigate} />
          <TeamMetricsCard />
          <UpcomingGamesCard
            snapshot={snapshot}
            managedTeamId={managedTeamId}
            games={upcomingGames}
            onNavigate={onNavigate}
          />
        </div>
      </div>
    </div>
  )
}

/*
 * DEFERRED(§11): Record · Conf Rank · GB · Streak · Off/Def Rank fill from the
 * standings/statistics folds once games produce results.
 * DEFERRED(later): Cap Status needs the financial model; Unavailable needs an
 * injury system; Team Direction needs the ownership/objective system.
 */
function TeamOverviewHeader({
  snapshot,
  team,
  summary,
  managedTeamId,
  nextGame,
}: {
  readonly snapshot: LeagueSnapshot
  readonly team: Team
  readonly summary: TeamOverviewSummary | null
  readonly managedTeamId: LeagueSnapshot['managedTeamId']
  readonly nextGame: LeagueSnapshotScheduledGameDto | null
}) {
  const nextOpponent =
    managedTeamId === null || nextGame === null
      ? null
      : resolveOpponent(snapshot.league, nextGame, managedTeamId)
  const nextLocation =
    nextGame !== null && managedTeamId !== null
      ? getTeamLocation(nextGame, managedTeamId)
      : null

  return (
    <section className="team-overview-header" aria-label="Team overview header">
      <div className="team-overview-identity">
        <div
          className="team-overview-badge"
          style={{
            background: team.colors.primary,
            color: team.colors.accent,
            borderColor: team.colors.secondary,
          }}
          aria-hidden="true"
        >
          {team.mark.text}
        </div>
        <div className="team-overview-identity-text">
          <h2>{formatTeamName(team)}</h2>
          <p>{snapshot.season.displayLabel} Season</p>
        </div>
      </div>

      <dl className="team-overview-facts">
        <FactChip
          label="Team Rating"
          value={summary === null ? null : String(summary.averageRating)}
        />
        <FactChip
          label="Roster"
          value={
            summary === null
              ? null
              : `${summary.rosterSize} / ${summary.rosterCapacity}`
          }
        />
        <FactChip
          label="Open Spots"
          value={summary === null ? null : String(summary.openSpots)}
        />
        <FactChip
          label="Next Game"
          value={
            nextOpponent === null
              ? 'None scheduled'
              : `${nextLocation === 'home' ? 'vs' : '@'} ${
                  nextOpponent.abbreviation
                }`
          }
        />
        <ComingLaterChip label="Record" />
        <ComingLaterChip label="Conf Rank" />
        <ComingLaterChip label="Games Back" />
        <ComingLaterChip label="Streak" />
        <ComingLaterChip label="Off Rank" />
        <ComingLaterChip label="Def Rank" />
        <ComingLaterChip label="Cap Status" />
        <ComingLaterChip label="Unavailable" />
        <ComingLaterChip label="Team Direction" />
      </dl>
    </section>
  )
}

function FactChip({
  label,
  value,
}: {
  readonly label: string
  readonly value: string | null
}) {
  return (
    <div className="team-overview-fact">
      <dt>{label}</dt>
      <dd>
        {value === null ? (
          <span className="coming-later-marker">Coming later</span>
        ) : (
          value
        )}
      </dd>
    </div>
  )
}

function ComingLaterChip({ label }: { readonly label: string }) {
  return (
    <div className="team-overview-fact">
      <dt>{label}</dt>
      <dd>
        <span className="coming-later-marker">Coming later</span>
      </dd>
    </div>
  )
}

/*
 * DEFERRED(§8): "Review Rotation" -> 'team-rotation-gameplan' lands on the
 * functional §8 rotation editor.
 * DEFERRED(later): the alerts themselves (availability, injury returns,
 * contract risk, development blocks) need injury/contract/development systems
 * not yet scheduled. Clickables: Medical Department -> 'team-health',
 * Front Office -> 'front-office-overview', View Development -> 'team-development'.
 */
function NeedsAttentionRow({
  onNavigate,
}: {
  readonly onNavigate?: (pageId: NavigationPageId) => void
}) {
  return (
    <section className="team-overview-attention" aria-label="Needs attention">
      <h3 className="team-overview-section-title">Needs Attention</h3>
      <div className="team-overview-attention-grid">
        <AttentionCard
          title="Rotation & Availability"
          detail="Lineup and availability alerts will surface here."
          actionLabel="Review Rotation"
          target="team-rotation-gameplan"
          onNavigate={onNavigate}
        />
        <AttentionCard
          title="Medical Report"
          detail="Injuries and return-to-play alerts will surface here."
          actionLabel="Medical Department"
          target="team-health"
          onNavigate={onNavigate}
        />
        <AttentionCard
          title="Contract Situations"
          detail="Extension and re-sign risks will surface here."
          actionLabel="Front Office"
          target="front-office-overview"
          onNavigate={onNavigate}
        />
        <AttentionCard
          title="Development Blocks"
          detail="Prospects blocked from minutes will surface here."
          actionLabel="View Development"
          target="team-development"
          onNavigate={onNavigate}
        />
      </div>
    </section>
  )
}

function AttentionCard({
  title,
  detail,
  actionLabel,
  target,
  onNavigate,
}: {
  readonly title: string
  readonly detail: string
  readonly actionLabel: string
  readonly target: NavigationPageId
  readonly onNavigate?: (pageId: NavigationPageId) => void
}) {
  return (
    <article className="team-overview-attention-card">
      <h4>{title}</h4>
      <p>{detail}</p>
      <p className="coming-later-marker">Coming later</p>
      {onNavigate !== undefined && (
        <button
          type="button"
          className="secondary-button"
          onClick={() => onNavigate(target)}
        >
          {actionLabel}
        </button>
      )}
    </article>
  )
}

/*
 * DEFERRED(§8): starters, roles, and target minutes come from the rotation plan
 * and its editor; "View Rotation" -> 'team-rotation-gameplan'.
 * DEFERRED(later): player Status needs an injury/availability system.
 */
function StartingFiveRotationCard({
  onNavigate,
}: {
  readonly onNavigate?: (pageId: NavigationPageId) => void
}) {
  return (
    <DashboardCard title="Starting Five / Rotation">
      <p className="coming-later-marker">Coming later</p>
      <p className="coming-later-requirement">
        Starters, roles, and target minutes arrive with the rotation plan and
        editor; player availability arrives with the injury system.
      </p>
      {onNavigate !== undefined && (
        <div className="team-overview-card-actions">
          <button
            type="button"
            className="secondary-button"
            onClick={() => onNavigate('team-rotation-gameplan')}
          >
            View Rotation
          </button>
        </div>
      )}
    </DashboardCard>
  )
}

/* DEFERRED(§11): offensive/defensive efficiency, pace, shooting, ball security,
 * rebounding, rim/perimeter defense, and bench production with league ranks all
 * fill from the season-statistics fold over box scores. */
function StrengthsWeaknessesCard() {
  return (
    <DashboardCard title="Team Strengths & Weaknesses">
      <p className="coming-later-marker">Coming later</p>
      <p className="coming-later-requirement">
        Efficiency, pace, shooting, rebounding, and defensive ranks appear once
        games produce box scores.
      </p>
    </DashboardCard>
  )
}

/* DEFERRED(later): injuries, return timelines, and day-to-day status need a
 * player-health system (not yet scheduled). Clickable: View Health ->
 * 'team-health'. */
function HealthSummaryCard({
  onNavigate,
}: {
  readonly onNavigate?: (pageId: NavigationPageId) => void
}) {
  return (
    <DashboardCard title="Health Summary">
      <p className="coming-later-marker">Coming later</p>
      <p className="coming-later-requirement">
        Injuries, return timelines, and day-to-day status appear with the
        medical system.
      </p>
      {onNavigate !== undefined && (
        <div className="team-overview-card-actions">
          <button
            type="button"
            className="secondary-button"
            onClick={() => onNavigate('team-health')}
          >
            View Health
          </button>
        </div>
      )}
    </DashboardCard>
  )
}

/* DEFERRED(later): prospect progress, development goals, and G-League minutes
 * need a player-development system (not yet scheduled). Clickable: View
 * Development -> 'team-development'. */
function DevelopmentWatchCard({
  onNavigate,
}: {
  readonly onNavigate?: (pageId: NavigationPageId) => void
}) {
  return (
    <DashboardCard title="Development Watch">
      <p className="coming-later-marker">Coming later</p>
      <p className="coming-later-requirement">
        Prospect progress and development goals appear with the development
        system.
      </p>
      {onNavigate !== undefined && (
        <div className="team-overview-card-actions">
          <button
            type="button"
            className="secondary-button"
            onClick={() => onNavigate('team-development')}
          >
            View Development
          </button>
        </div>
      )}
    </DashboardCard>
  )
}

/**
 * Roster Breakdown (real): players by primary position and by age band, both
 * derived from today's roster. Replaces the Evergreens "Recent Form" slot.
 */
function RosterBreakdownCard({
  summary,
}: {
  readonly summary: TeamOverviewSummary | null
}) {
  if (summary === null) {
    return (
      <DashboardCard title="Roster Breakdown">
        <p>Select a team to see its roster breakdown.</p>
      </DashboardCard>
    )
  }

  const total = POSITIONS.reduce(
    (sum, position) => sum + summary.positionCounts[position],
    0,
  )
  let accumulated = 0
  const segments = POSITIONS.map((position) => {
    const start = total === 0 ? 0 : (accumulated / total) * 360
    accumulated += summary.positionCounts[position]
    const end = total === 0 ? 0 : (accumulated / total) * 360
    return `${POSITION_COLORS[position]} ${start}deg ${end}deg`
  })
  const donutStyle =
    total > 0 ? { background: `conic-gradient(${segments.join(', ')})` } : undefined

  return (
    <DashboardCard title="Roster Breakdown">
      <div className="roster-breakdown roster-breakdown--positions-only">
        <div className="roster-breakdown-positions">
          <div className="roster-donut" style={donutStyle}>
            <div className="roster-donut-hole">
              <span className="roster-donut-total">{total}</span>
              <span className="roster-donut-label">Players</span>
            </div>
          </div>
          <dl className="roster-position-legend" aria-label="Players by position">
            {POSITIONS.map((position) => (
              <div key={position}>
                <dt>
                  <span
                    className="roster-position-swatch"
                    style={{ background: POSITION_COLORS[position] }}
                    aria-hidden="true"
                  />
                  {position}
                </dt>
                <dd>{summary.positionCounts[position]}</dd>
              </div>
            ))}
          </dl>
        </div>
      </div>
    </DashboardCard>
  )
}

/* DEFERRED(§11): offensive/defensive/net rating, pace, eFG%, 3P%, FT%, and the
 * per-game rebound/assist/turnover rates all fill from the season-statistics
 * fold over box scores. Replaces the Evergreens "Cap & Asset" slot. */
const TEAM_METRIC_LABELS = [
  'Off Rating',
  'Def Rating',
  'Net Rating',
  'Pace',
  'eFG%',
  '3P%',
  'FT%',
  'Reb / GM',
  'Ast / GM',
  'TO / GM',
] as const

function TeamMetricsCard() {
  return (
    <DashboardCard title="Team Metrics">
      <div className="team-metrics-grid" aria-hidden="true">
        {TEAM_METRIC_LABELS.map((label) => (
          <div key={label} className="team-metric-tile">
            <span className="team-metric-value">—</span>
            <span className="team-metric-label">{label}</span>
          </div>
        ))}
      </div>
      <p className="coming-later-marker">Coming later</p>
      <p className="coming-later-requirement">
        Ratings, shooting splits, and per-game rates appear once games produce
        box scores.
      </p>
    </DashboardCard>
  )
}

function UpcomingGamesCard({
  snapshot,
  managedTeamId,
  games,
  onNavigate,
}: {
  readonly snapshot: LeagueSnapshot
  readonly managedTeamId: LeagueSnapshot['managedTeamId']
  readonly games: readonly LeagueSnapshotScheduledGameDto[]
  readonly onNavigate?: (pageId: NavigationPageId) => void
}) {
  return (
    <DashboardCard title="Upcoming Games">
      {managedTeamId === null || games.length === 0 ? (
        <p>No future scheduled games are available.</p>
      ) : (
        <ol className="team-overview-timeline">
          {games.map((game) => {
            const opponent = resolveOpponent(
              snapshot.league,
              game,
              managedTeamId,
            )
            const location = getTeamLocation(game, managedTeamId)
            return (
              <li key={game.id}>
                <span className="team-overview-timeline-date">
                  {game.currentScheduledDate === null ? (
                    'TBA'
                  ) : (
                    <time dateTime={game.currentScheduledDate}>
                      {formatLocalDateForDisplay(game.currentScheduledDate)}
                    </time>
                  )}
                </span>
                <span className="team-overview-timeline-event">
                  {location === 'home' ? 'vs' : '@'} {formatTeamName(opponent)}
                </span>
                <span className="team-overview-timeline-context">
                  {location === 'home' ? 'Home' : 'Away'}
                </span>
              </li>
            )
          })}
        </ol>
      )}
      {onNavigate !== undefined && (
        <div className="team-overview-card-actions">
          <button
            type="button"
            className="secondary-button"
            onClick={() => onNavigate('schedule-team-schedule')}
          >
            View Full Schedule
          </button>
        </div>
      )}
    </DashboardCard>
  )
}

/* DEFERRED(later): signings, trades, and league news need a transaction/news
 * system (not yet scheduled). */
function RecentTransactionsCard() {
  return (
    <DashboardCard title="Recent Transactions / News">
      <p className="coming-later-marker">Coming later</p>
      <p className="coming-later-requirement">
        Signings, trades, and league news appear with the transaction and news
        systems.
      </p>
    </DashboardCard>
  )
}
