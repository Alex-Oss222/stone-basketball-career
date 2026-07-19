import type { TeamId } from '../domain/ids'
import { POSITIONS } from '../domain/league'
import type { NavigationPageId } from '../app/navigation'
import {
  createHomeHeaderSummary,
  deriveTeamAverageRating,
} from '../app/homeViewModel'
import type { SaveIndicatorState } from '../app/dashboardViewModel'
import {
  findNextScheduledGame,
  formatSeasonPhaseForDisplay,
  getTeamLocation,
  getUpcomingScheduledGames,
  resolveOpponent,
} from '../app/scheduleViewModel'
import {
  formatScheduleDateCompact,
  formatScheduleDateLong,
} from './scheduleFormatting'
import { formatTeamName } from '../domain/league'
import type {
  LeagueSnapshot,
  LeagueSnapshotScheduledGameDto,
} from '../persistence/leagueSnapshot'
import { DashboardCard } from './dashboardShell'

export interface HomeSaveState {
  readonly label: string
  readonly state: SaveIndicatorState
}

export interface HomeTodayContentProps {
  readonly snapshot: LeagueSnapshot | null
  readonly saveState: HomeSaveState | null
  /**
   * Navigates to another page. Card actions (Adjust Rotation, View Free
   * Agents, View Finances, View Full Schedule) go to their real destination —
   * a planned page honestly states what it still requires.
   */
  readonly onNavigate?: (pageId: NavigationPageId) => void
  /** DEV only: opens the fixture-driven post-game preview. Absent in production. */
  readonly onOpenGameResultPreview?: () => void
}

/**
 * Home (§6): the mockup card grid, without the duplicate Home subtab row.
 * Every value is one of three honest states: real data that exists today, a
 * real absence (no games completed yet), or a plainly-labelled "Coming later"
 * slot. Card buttons are live entry points into the sidebar's real pages.
 * Nothing fabricates a record, score, standing, injury, headline, or dollar
 * amount.
 */
export function HomeTodayContent({
  snapshot,
  saveState,
  onNavigate,
  onOpenGameResultPreview,
}: HomeTodayContentProps) {
  if (snapshot === null) {
    return (
      <section className="home-empty empty-state" aria-label="No league">
        <h2>No league available</h2>
        <p>Create a league to open its home page.</p>
        {saveState !== null && (
          <p className="dashboard-save-state" data-save-state={saveState.state}>
            {saveState.label}
          </p>
        )}
      </section>
    )
  }

  const managedTeamId = snapshot.managedTeamId
  const header = createHomeHeaderSummary({
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
        )
          .filter((game) => game.id !== nextGame?.id)
          .slice(0, 5)

  return (
    <div className="home-today">
      <HomeCommandBar snapshot={snapshot} header={header} />

      <div className="home-grid">
        <div className="home-column">
          <NeedsAttentionCard
            snapshot={snapshot}
            managedTeamId={managedTeamId}
            nextGame={nextGame}
            onNavigate={onNavigate}
          />
          <RosterHealthCard header={header} onNavigate={onNavigate} />
          <FrontOfficeCard onNavigate={onNavigate} />
        </div>

        <div className="home-column">
          <NextGameCard
            snapshot={snapshot}
            managedTeamId={managedTeamId}
            nextGame={nextGame}
          />
          <div className="home-two-up">
            <RecentResultsCard
              onOpenGameResultPreview={onOpenGameResultPreview}
            />
            <UpcomingGamesCard
              snapshot={snapshot}
              managedTeamId={managedTeamId}
              games={upcomingGames}
              onNavigate={onNavigate}
            />
          </div>
          <StandingsCard />
        </div>

        <div className="home-column">
          <SeasonPulseCard />
          <HeadlinesCard />
          <TeamStatsCard />
        </div>
      </div>
    </div>
  )
}

/*
 * DEFERRED(§10): "Continue" goes live when advanceToNextGameDay exists.
 * DEFERRED(§12): "Sim to Next Event" goes live with multi-day advancement.
 * DEFERRED(§11): Record · Seed · Streak fills from the standings fold.
 */
function HomeCommandBar({
  snapshot,
  header,
}: {
  readonly snapshot: LeagueSnapshot
  readonly header: ReturnType<typeof createHomeHeaderSummary>
}) {
  return (
    <section className="home-command-bar" aria-label="Team status">
      <p className="home-command-context">
        {snapshot.season.displayLabel} ·{' '}
        {formatSeasonPhaseForDisplay(snapshot.season.currentPhase)} ·{' '}
        <time dateTime={snapshot.season.currentDate}>
          {formatScheduleDateLong(snapshot.season.currentDate)}
        </time>
      </p>

      <dl className="home-command-facts">
        <div>
          <dt>Record · Seed · Streak</dt>
          <dd>
            <span className="coming-later-marker">Coming later</span>
          </dd>
        </div>
        {header !== null && (
          <>
            <div>
              <dt>Avg rating</dt>
              <dd>{header.averageRating}</dd>
            </div>
            <div>
              <dt>Roster</dt>
              <dd>
                {header.rosterSize} / {header.rosterCapacity}
              </dd>
            </div>
          </>
        )}
      </dl>

      <div className="home-command-actions">
        <ComingLaterButton
          label="Continue"
          requirement="Advancing the game day arrives with the simulation."
          emphasis
        />
        <ComingLaterButton
          label="Sim to Next Event"
          requirement="Simulating ahead arrives with the simulation."
        />
      </div>
    </section>
  )
}

/**
 * With no injury, trade, contract, or fatigue systems yet, there is genuinely
 * nothing requiring action — the card shows the caught-up state with the real
 * next event. Its buttons are live entry points into the pages where those
 * decisions will happen.
 *
 * DEFERRED(later): actionable items (injuries, trade offers, deadlines,
 * roster problems) need systems not yet on the roadmap — schedule or cut
 * consciously at §19. Clickables: Review Offers -> 'front-office-market',
 * View Free Agents -> 'front-office-free-agency'.
 */
function NeedsAttentionCard({
  snapshot,
  managedTeamId,
  nextGame,
  onNavigate,
}: {
  readonly snapshot: LeagueSnapshot
  readonly managedTeamId: TeamId | null
  readonly nextGame: LeagueSnapshotScheduledGameDto | null
  readonly onNavigate?: (pageId: NavigationPageId) => void
}) {
  const opponent =
    managedTeamId === null || nextGame === null
      ? null
      : resolveOpponent(snapshot.league, nextGame, managedTeamId)

  return (
    <DashboardCard title="Needs Attention">
      <p className="home-caught-up">
        <span aria-hidden="true">✓</span> You&rsquo;re all caught up
      </p>
      <p className="home-caught-up-detail">
        {opponent === null
          ? 'No decisions are required before the next event.'
          : `Next event: Game ${
              nextGame !== null &&
              managedTeamId !== null &&
              getTeamLocation(nextGame, managedTeamId) === 'home'
                ? 'vs'
                : 'at'
            } ${formatTeamName(opponent)}`}
      </p>
      <p className="home-card-deferred">
        Injuries, trade offers, deadlines, and roster problems will surface
        here <span className="coming-later-marker">Coming later</span>
      </p>
      {onNavigate !== undefined && (
        <div className="home-card-actions">
          <button
            type="button"
            className="secondary-button"
            onClick={() => onNavigate('front-office-market')}
          >
            Review Offers
          </button>
          <button
            type="button"
            className="secondary-button"
            onClick={() => onNavigate('front-office-free-agency')}
          >
            View Free Agents
          </button>
        </div>
      )}
    </DashboardCard>
  )
}

/*
 * DEFERRED(§10): "Sim Game" goes live when commitGameResult exists.
 * DEFERRED(§14): "Watch Game" needs the possession event log.
 * DEFERRED(§11): Records · Ranks · Last 10 fills from standings/stat folds.
 * DEFERRED(later): Availability needs an injury system (not yet scheduled).
 */
function NextGameCard({
  snapshot,
  managedTeamId,
  nextGame,
}: {
  readonly snapshot: LeagueSnapshot
  readonly managedTeamId: TeamId | null
  readonly nextGame: LeagueSnapshotScheduledGameDto | null
}) {
  return (
    <DashboardCard title="Next Game">
      {managedTeamId === null || nextGame === null ? (
        <p>No upcoming event is currently scheduled.</p>
      ) : (
        <NextGameDetails
          snapshot={snapshot}
          game={nextGame}
          managedTeamId={managedTeamId}
        />
      )}
      <div className="home-card-actions">
        <ComingLaterButton
          label="Watch Game"
          requirement="Watching a game arrives with the simulation's event log."
          emphasis
        />
        <ComingLaterButton
          label="Sim Game"
          requirement="Simulating a game arrives with the simulation kernel."
        />
      </div>
    </DashboardCard>
  )
}

function NextGameDetails({
  snapshot,
  game,
  managedTeamId,
}: {
  readonly snapshot: LeagueSnapshot
  readonly game: LeagueSnapshotScheduledGameDto
  readonly managedTeamId: TeamId
}) {
  const opponent = resolveOpponent(snapshot.league, game, managedTeamId)
  const location = getTeamLocation(game, managedTeamId)
  const ownRating = deriveTeamAverageRating(snapshot.league, managedTeamId)
  const opponentRating = deriveTeamAverageRating(snapshot.league, opponent.id)

  return (
    <div className="home-next-event">
      <p className="home-next-event-kind">
        Regular Season Game ·{' '}
        {game.currentScheduledDate === null ? (
          'Date to be announced'
        ) : (
          <time dateTime={game.currentScheduledDate}>
            {formatScheduleDateLong(game.currentScheduledDate)}
          </time>
        )}
      </p>
      <p className="home-next-event-matchup">
        <strong>
          {location === 'home' ? 'vs' : '@'} {formatTeamName(opponent)}
        </strong>
        <span>
          {opponent.abbreviation} · {location === 'home' ? 'Home' : 'Away'}
        </span>
      </p>

      <dl className="home-next-event-comparison">
        <div>
          <dt>Avg rating</dt>
          <dd>
            {ownRating} · {opponentRating}
          </dd>
        </div>
        <div>
          <dt>Records · Ranks · Last 10</dt>
          <dd>
            <span className="coming-later-marker">Coming later</span>
          </dd>
        </div>
        <div>
          <dt>Availability</dt>
          <dd>
            <span className="coming-later-marker">Coming later</span>
          </dd>
        </div>
      </dl>
    </div>
  )
}

/* DEFERRED(§11): record, seed, GB, streak, last 10, net rating, power
 * ranking, and the trend chart all fill from the standings/statistics folds. */
function SeasonPulseCard() {
  return (
    <DashboardCard title="Season Pulse">
      <p className="coming-later-marker">Coming later</p>
      <p className="coming-later-requirement">
        Record, seed, games back, streak, last 10, net rating, power ranking,
        and the season trend appear once games produce results.
      </p>
    </DashboardCard>
  )
}

/*
 * DEFERRED(later): injuries, fatigue, and availability need player-health
 * systems not yet on the roadmap. (Adjust Rotation now lands on the functional
 * §8 rotation editor — that slot is cleared.)
 */
function RosterHealthCard({
  header,
  onNavigate,
}: {
  readonly header: ReturnType<typeof createHomeHeaderSummary>
  readonly onNavigate?: (pageId: NavigationPageId) => void
}) {
  return (
    <DashboardCard title="Roster Health">
      {header === null ? (
        <p>Select a team to see its roster status.</p>
      ) : (
        <>
          <p className="home-roster-count">
            <strong>
              {header.rosterSize} / {header.rosterCapacity}
            </strong>{' '}
            roster spots filled
          </p>
          <dl
            className="position-breakdown"
            aria-label="Primary-position breakdown"
          >
            {POSITIONS.map((position) => (
              <div key={position}>
                <dt>{position}</dt>
                <dd>{header.positionCounts[position]}</dd>
              </div>
            ))}
          </dl>
        </>
      )}
      <p className="home-card-deferred">
        Injuries, fatigue, and availability{' '}
        <span className="coming-later-marker">Coming later</span>
      </p>
      {onNavigate !== undefined && (
        <div className="home-card-actions">
          <button
            type="button"
            className="secondary-button"
            onClick={() => onNavigate('team-rotation-gameplan')}
          >
            Adjust Rotation
          </button>
        </div>
      )}
    </DashboardCard>
  )
}

/* DEFERRED(later): payroll, cap, tax, and contracts need the financial model
 * (not yet scheduled). Clickable: View Finances -> 'finances-overview'. */
function FrontOfficeCard({
  onNavigate,
}: {
  readonly onNavigate?: (pageId: NavigationPageId) => void
}) {
  return (
    <DashboardCard title="Front Office">
      <p className="coming-later-marker">Coming later</p>
      <p className="coming-later-requirement">
        Payroll, cap room, luxury tax, and contract counts appear with the
        financial model.
      </p>
      {onNavigate !== undefined && (
        <div className="home-card-actions">
          <button
            type="button"
            className="secondary-button"
            onClick={() => onNavigate('finances-overview')}
          >
            View Finances
          </button>
        </div>
      )}
    </DashboardCard>
  )
}

/* DEFERRED(§10): fills with real Final results the moment one game commits;
 * the dev-preview entry point can be retired then. */
function RecentResultsCard({
  onOpenGameResultPreview,
}: {
  readonly onOpenGameResultPreview?: () => void
}) {
  return (
    <DashboardCard title="Recent Results">
      <p>No completed games yet.</p>
      <p className="home-activity-empty-detail">
        Results appear here once the simulation can play a game to Final.
      </p>
      {onOpenGameResultPreview !== undefined && (
        <button
          type="button"
          className="secondary-button home-dev-preview-button"
          onClick={onOpenGameResultPreview}
        >
          Preview the post-game screen (design fixture)
        </button>
      )}
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
  readonly managedTeamId: TeamId | null
  readonly games: readonly LeagueSnapshotScheduledGameDto[]
  readonly onNavigate?: (pageId: NavigationPageId) => void
}) {
  return (
    <DashboardCard title="Upcoming Games">
      {managedTeamId === null || games.length === 0 ? (
        <p>No additional future scheduled games are available.</p>
      ) : (
        <ol className="home-timeline">
          {games.map((game) => {
            const opponent = resolveOpponent(
              snapshot.league,
              game,
              managedTeamId,
            )
            const location = getTeamLocation(game, managedTeamId)
            return (
              <li key={game.id}>
                <span className="home-timeline-date">
                  {game.currentScheduledDate === null ? (
                    'TBA'
                  ) : (
                    <time dateTime={game.currentScheduledDate}>
                      {formatScheduleDateCompact(game.currentScheduledDate)}
                    </time>
                  )}
                </span>
                <span className="home-timeline-event">
                  {location === 'home' ? 'vs' : '@'} {formatTeamName(opponent)}
                </span>
                <span className="home-timeline-context">
                  {location === 'home' ? 'Home' : 'Away'}
                </span>
              </li>
            )
          })}
        </ol>
      )}
      {onNavigate !== undefined && (
        <button
          type="button"
          className="secondary-button"
          onClick={() => onNavigate('schedule-team-schedule')}
        >
          View Full Schedule
        </button>
      )}
    </DashboardCard>
  )
}

/**
 * Two sections, one card — division and conference standings, per the spec.
 *
 * DEFERRED(§11): standings values fill from the standings fold (8-team league
 * standings can show here before divisions exist). Alex dislikes how this
 * card sits in the layout while empty — revisit its placement/format when the
 * real data lands.
 * DEFERRED(§15): the division/conference split needs the 30-team alignment.
 */
function StandingsCard() {
  return (
    <DashboardCard title="Standings">
      <section
        className="home-standings-section"
        aria-label="Division standings"
      >
        <h3>Division Standings</h3>
        <p className="coming-later-marker">Coming later</p>
        <p className="coming-later-requirement">
          Requires completed games plus the divisions that arrive with the
          30-team league.
        </p>
      </section>
      <section
        className="home-standings-section"
        aria-label="Conference standings"
      >
        <h3>Conference Standings</h3>
        <p className="coming-later-marker">Coming later</p>
        <p className="coming-later-requirement">
          Requires completed games plus the conferences that arrive with the
          30-team league.
        </p>
      </section>
    </DashboardCard>
  )
}

/* DEFERRED(later): needs a league news/headline system (not yet scheduled). */
function HeadlinesCard() {
  return (
    <DashboardCard title="Important Headlines">
      <p className="coming-later-marker">Coming later</p>
      <p className="coming-later-requirement">
        Trades, injuries, milestone performances, and league announcements
        appear with the news system.
      </p>
    </DashboardCard>
  )
}

/* DEFERRED(§11): offensive/defensive/net ratings with league ranks fill from
 * the season-statistics fold over box scores. */
function TeamStatsCard() {
  return (
    <DashboardCard title="Team Stats">
      <p className="coming-later-marker">Coming later</p>
      <p className="coming-later-requirement">
        Offensive, defensive, and net ratings with league ranks appear once
        games produce box scores.
      </p>
    </DashboardCard>
  )
}

function ComingLaterButton({
  label,
  requirement,
  emphasis = false,
}: {
  readonly label: string
  readonly requirement: string
  readonly emphasis?: boolean
}) {
  return (
    <button
      type="button"
      className={
        emphasis
          ? 'authoritative-action home-disabled-action'
          : 'secondary-button home-disabled-action'
      }
      disabled
      title={requirement}
    >
      {label} <span className="coming-later-marker">Coming later</span>
    </button>
  )
}
