import type { Team } from '../domain/league'
import { formatTeamName } from '../domain/league'
import type { NavigationPageId } from '../app/navigation'
import { createTeamOverviewSummary } from '../app/teamOverviewViewModel'
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

/**
 * Coach's Chair — the command-center layout from Alex's reference
 * (2026-07-17), imposed honestly: everything that changed, everything that
 * needs a decision, and the cost of waiting. Real today: team identity, the
 * derived team rating, the next game, and the Schedule Pressure strip (real
 * schedule + real rest-day math). Every decision, matchup stat, readiness
 * figure, and conflict is a plainly-labelled Coming-later slot — nothing
 * fabricates a record, ranking, score, injury, metric, or dollar amount.
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
        <p>Create a league and choose a team to open the Coach&apos;s Chair.</p>
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
    <div className="team-overview coachs-chair">
      <p className="section-intro">
        Everything that changed, everything that needs a decision, and the cost
        of waiting.
      </p>

      <CoachsChairHeader
        snapshot={snapshot}
        team={team}
        averageRating={summary?.averageRating ?? null}
        managedTeamId={managedTeamId}
        nextGame={nextGame}
      />

      <div className="coachs-chair-command-row">
        <NextDecisionPointCard />
        <OpponentPrepCard
          snapshot={snapshot}
          managedTeamId={managedTeamId}
          nextGame={nextGame}
        />
        <DecisionStackCard />
      </div>

      <SchedulePressureCard
        snapshot={snapshot}
        managedTeamId={managedTeamId}
        games={upcomingGames}
        onNavigate={onNavigate}
      />

      <TeamPulseRow onNavigate={onNavigate} />

      <div className="coachs-chair-bottom-row">
        <LineupRealityCard onNavigate={onNavigate} />
        <LastTenGamesCard />
        <CrossDepartmentConflictsCard />
        <RecentTransactionsCard />
      </div>
    </div>
  )
}

/*
 * DEFERRED(§11): Record and last-10 identity fill from the standings and
 * statistics folds once games produce results.
 * DEFERRED(§8): the Rotation tile fills from the saved rotation plan.
 * DEFERRED(later): Availability needs the medical system; Team Readiness and
 * Chemistry need the morale system; Cap Room needs the financial model.
 */
function CoachsChairHeader({
  snapshot,
  team,
  averageRating,
  managedTeamId,
  nextGame,
}: {
  readonly snapshot: LeagueSnapshot
  readonly team: Team
  readonly averageRating: number | null
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
    <section className="team-overview-header" aria-label="Coach's Chair header">
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
          value={averageRating === null ? null : String(averageRating)}
        />
        <ComingLaterChip label="Record" />
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
        <ComingLaterChip label="Rotation" />
        <ComingLaterChip label="Availability" />
        <ComingLaterChip label="Team Readiness" />
        <ComingLaterChip label="Chemistry" />
        <ComingLaterChip label="Cap Room" />
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

/* DEFERRED(later): decision points (lineup lock, deadlines) need the decision
 * system. */
function NextDecisionPointCard() {
  return (
    <DashboardCard title="Next Decision Point">
      <p className="coming-later-marker">Coming later</p>
      <p className="coming-later-requirement">
        Lineup locks, deadlines, and countdowns arrive with the decision
        system.
      </p>
    </DashboardCard>
  )
}

/*
 * DEFERRED(§11): matchup stats (half-court rank, paint attempts, turnover
 * rate) and the keys-to-the-game list fill from the statistics folds.
 */
function OpponentPrepCard({
  snapshot,
  managedTeamId,
  nextGame,
}: {
  readonly snapshot: LeagueSnapshot
  readonly managedTeamId: LeagueSnapshot['managedTeamId']
  readonly nextGame: LeagueSnapshotScheduledGameDto | null
}) {
  const opponent =
    managedTeamId === null || nextGame === null
      ? null
      : resolveOpponent(snapshot.league, nextGame, managedTeamId)
  const location =
    nextGame !== null && managedTeamId !== null
      ? getTeamLocation(nextGame, managedTeamId)
      : null

  return (
    <DashboardCard title="Opponent Prep">
      {opponent === null || nextGame === null ? (
        <p>No upcoming game is scheduled.</p>
      ) : (
        <div className="opponent-prep-matchup">
          <p className="opponent-prep-line">
            {location === 'home' ? 'vs' : '@'} {formatTeamName(opponent)}
            {nextGame.currentScheduledDate === null ? null : (
              <>
                {' · '}
                <time dateTime={nextGame.currentScheduledDate}>
                  {formatLocalDateForDisplay(nextGame.currentScheduledDate)}
                </time>
              </>
            )}
          </p>
          <dl className="pqv-field-rows">
            {[
              'Their half-court offense',
              'Paint attempts',
              'Turnover rate',
              'Keys to the game',
            ].map((label) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>—</dd>
              </div>
            ))}
          </dl>
          <p className="coming-later-requirement">
            What wins this matchup fills from real statistics once games
            produce box scores.
          </p>
        </div>
      )}
    </DashboardCard>
  )
}

/* DEFERRED(later): the decision stack needs the decision system. */
function DecisionStackCard() {
  return (
    <DashboardCard title="Decision Stack">
      <p className="coming-later-marker">Coming later</p>
      <p className="coming-later-requirement">
        Open decisions with act-before deadlines arrive with the decision,
        medical, and development systems.
      </p>
    </DashboardCard>
  )
}

/**
 * Schedule Pressure — workload context, not a game list. Real today: the
 * upcoming schedule and the rest-day math between games. Roomy by request:
 * one card per game with its rest context, not a compressed micro-strip.
 * DEFERRED(later): travel, recovery blocks, and workload flags need the
 * medical/travel systems.
 */
function SchedulePressureCard({
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
    <section className="player-page-card schedule-pressure" aria-label="Schedule pressure">
      <div className="panel-heading">
        <div>
          <p className="panel-kicker">Schedule pressure</p>
          <h3>Workload context, not a game list</h3>
        </div>
        {games.length > 0 && (
          <span className="count-badge">
            {games.length} games · next {games.length} game days
          </span>
        )}
      </div>

      {managedTeamId === null || games.length === 0 ? (
        <p>No future scheduled games are available.</p>
      ) : (
        <ol className="schedule-pressure-strip">
          {games.map((game, index) => {
            const opponent = resolveOpponent(
              snapshot.league,
              game,
              managedTeamId,
            )
            const location = getTeamLocation(game, managedTeamId)
            const previousDate =
              index === 0
                ? snapshot.season.currentDate
                : games[index - 1].currentScheduledDate
            const restDays =
              game.currentScheduledDate === null || previousDate === null
                ? null
                : daysBetweenIsoDates(previousDate, game.currentScheduledDate) - 1

            return (
              <li key={game.id} className="schedule-pressure-day">
                <p className="schedule-pressure-date">
                  {game.currentScheduledDate === null ? (
                    'TBA'
                  ) : (
                    <time dateTime={game.currentScheduledDate}>
                      {formatLocalDateForDisplay(game.currentScheduledDate)}
                    </time>
                  )}
                </p>
                <p className="schedule-pressure-opponent">
                  {location === 'home' ? 'vs' : '@'} {opponent.abbreviation}
                </p>
                <p className="schedule-pressure-context">
                  {location === 'home' ? 'Home' : 'Away'}
                  {restDays === null
                    ? ''
                    : restDays <= 0
                      ? ' · no rest'
                      : ` · ${restDays} ${restDays === 1 ? 'day' : 'days'} rest`}
                </p>
                {/* DEFERRED(later): travel and recovery context need their systems. */}
                <p className="schedule-pressure-load deferred-cell">
                  Workload —
                </p>
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
    </section>
  )
}

/*
 * DEFERRED(§8): the Rotation pulse tile fills from the rotation plan.
 * DEFERRED(§11): the Performance pulse tile fills from the statistics fold.
 * DEFERRED(later): Health and Development tiles need their systems.
 */
function TeamPulseRow({
  onNavigate,
}: {
  readonly onNavigate?: (pageId: NavigationPageId) => void
}) {
  const tiles = [
    {
      title: 'Rotation',
      detail: 'Minutes balance and plan conflicts will surface here.',
      target: 'team-rotation-gameplan' as const,
      action: 'Open Rotation',
    },
    {
      title: 'Health',
      detail: 'Participation decisions before lineup lock will surface here.',
      target: 'team-health' as const,
      action: 'Open Medical',
    },
    {
      title: 'Performance',
      detail: 'The largest competitive leaks will surface here.',
      target: 'schedule-team-schedule' as const,
      action: 'View Schedule',
    },
    {
      title: 'Development',
      detail: 'Players missing their required game reps will surface here.',
      target: 'team-development' as const,
      action: 'Open Development',
    },
  ]

  return (
    <section className="team-overview-attention" aria-label="Team pulse">
      <h3 className="team-overview-section-title">
        Team Pulse — the four things most likely to change results
      </h3>
      <div className="team-overview-attention-grid">
        {tiles.map((tile) => (
          <article key={tile.title} className="team-overview-attention-card">
            <h4>{tile.title}</h4>
            <p>{tile.detail}</p>
            <p className="coming-later-marker">Coming later</p>
            {onNavigate !== undefined && (
              <button
                type="button"
                className="secondary-button"
                onClick={() => onNavigate(tile.target)}
              >
                {tile.action}
              </button>
            )}
          </article>
        ))}
      </div>
    </section>
  )
}

/* DEFERRED(§8): projected opening/closing units come from the rotation plan;
 * projections themselves need the simulation (§9). */
function LineupRealityCard({
  onNavigate,
}: {
  readonly onNavigate?: (pageId: NavigationPageId) => void
}) {
  return (
    <DashboardCard title="Lineup Reality">
      <p className="coming-later-marker">Coming later</p>
      <p className="coming-later-requirement">
        Projected first and last six minutes come from the rotation plan and
        the simulation.
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

/* DEFERRED(§11): the last-10 identity (net rating trend, ranks) fills from the
 * statistics fold over box scores. */
function LastTenGamesCard() {
  return (
    <DashboardCard title="Last 10 Games">
      <p className="coming-later-marker">Coming later</p>
      <p className="coming-later-requirement">
        Team identity — net rating trend, defensive and offensive ranks —
        appears once games produce box scores.
      </p>
    </DashboardCard>
  )
}

/* DEFERRED(later): cross-department conflicts need the medical, rotation, and
 * development systems talking to each other. */
function CrossDepartmentConflictsCard() {
  return (
    <DashboardCard title="Cross-Department Conflicts">
      <p className="coming-later-marker">Coming later</p>
      <p className="coming-later-requirement">
        One decision, visible everywhere: medical caps vs rotation targets vs
        development reps surface here when those systems exist.
      </p>
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

/** Whole calendar days between two ISO local dates (display math only). */
function daysBetweenIsoDates(from: string, to: string): number {
  const [fromYear, fromMonth, fromDay] = from.split('-').map(Number)
  const [toYear, toMonth, toDay] = to.split('-').map(Number)
  return Math.round(
    (Date.UTC(toYear, toMonth - 1, toDay) -
      Date.UTC(fromYear, fromMonth - 1, fromDay)) /
      86_400_000,
  )
}
