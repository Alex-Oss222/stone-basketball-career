import { useId, useState } from 'react'
import type { PlayerId, TeamId } from '../domain/ids'
import { POSITIONS, isPosition } from '../domain/league'
import type { League, Player, Team } from '../domain/league'
import {
  NO_SEASON_STARTED_LABEL,
  createSavedLeagueDashboardSummary,
  filterLeaguePlayers,
} from '../app/dashboardViewModel'
import type {
  PlayerPositionFilter,
  SaveIndicatorState,
} from '../app/dashboardViewModel'
import {
  calculateTeamScheduleTotals,
  findNextScheduledGame,
  formatLocalDateForDisplay,
  formatSeasonPhaseForDisplay,
  getTeamLocation,
  getUpcomingScheduledGames,
  resolveOpponent,
} from '../app/scheduleViewModel'
import type {
  LeagueSnapshotV2,
  LeagueSnapshotV2ScheduledGameDto,
} from '../persistence/leagueSnapshotV2'
import {
  createRatingDisplayRows,
  formatPlayerName,
  formatTeamName,
  getTeamRoster,
} from './leagueViewModel'
import { DashboardCard } from './dashboardShell'

export interface DashboardSaveState {
  readonly label: string
  readonly state: SaveIndicatorState
}

export interface DashboardOverviewContentProps {
  readonly saveState: DashboardSaveState | null
  readonly snapshot: LeagueSnapshotV2 | null
}

export function DashboardOverviewContent({
  saveState,
  snapshot,
}: DashboardOverviewContentProps) {
  const summary =
    snapshot === null
      ? null
      : createSavedLeagueDashboardSummary({
          league: snapshot.league,
          managedTeamId: snapshot.managedTeamId,
        })
  const managedTeam = summary?.managedTeam ?? null
  const managedTeamId = snapshot?.managedTeamId ?? null
  const scheduleTotals =
    snapshot === null || managedTeamId === null
      ? null
      : calculateTeamScheduleTotals(snapshot.leagueSchedule, managedTeamId)
  const nextGame =
    snapshot === null || managedTeamId === null
      ? null
      : findNextScheduledGame(
          snapshot.leagueSchedule,
          managedTeamId,
          snapshot.season.currentDate,
        )
  const followingGames =
    snapshot === null || managedTeamId === null
      ? []
      : getUpcomingScheduledGames(
          snapshot.leagueSchedule,
          managedTeamId,
          snapshot.season.currentDate,
        )
          .filter((game) => game.id !== nextGame?.id)
          .slice(0, 3)

  return (
    <div className="dashboard-overview-content">
      <DashboardCard title="Local save">
        {saveState === null ? (
          <p>No league is currently saved.</p>
        ) : (
          <p
            className="dashboard-save-state"
            data-save-state={saveState.state}
          >
            {saveState.label}
          </p>
        )}
      </DashboardCard>

      {summary === null ? (
        <DashboardCard title="League">
          <p>No league has been created.</p>
        </DashboardCard>
      ) : (
        <>
          <DashboardCard title="League">
            <dl className="dashboard-facts" aria-label="Saved league summary">
              <div>
                <dt>League ID</dt>
                <dd>{summary.leagueId}</dd>
              </div>
              <div>
                <dt>Teams</dt>
                <dd>{summary.teamCount}</dd>
              </div>
            </dl>
          </DashboardCard>

          {managedTeam !== null && (
            <DashboardCard title="Managed team">
              <p className="managed-team-identity">
                <strong>{managedTeam.teamName}</strong>
                <span>{managedTeam.abbreviation}</span>
              </p>

              <dl className="managed-team-facts">
                <div>
                  <dt>Roster size</dt>
                  <dd>{managedTeam.rosterSize}</dd>
                </div>
                <div>
                  <dt>Average age</dt>
                  <dd>{managedTeam.averageAge.toFixed(1)}</dd>
                </div>
              </dl>

              <dl
                className="position-breakdown"
                aria-label="Primary-position breakdown"
              >
                {POSITIONS.map((position) => (
                  <div key={position}>
                    <dt>{position}</dt>
                    <dd>{managedTeam.positionBreakdown[position]}</dd>
                  </div>
                ))}
              </dl>
            </DashboardCard>
          )}
        </>
      )}

      <DashboardCard title="Competitive season">
        {snapshot === null ? (
          <p className="season-status-copy">
            <strong>{NO_SEASON_STARTED_LABEL}</strong>
            <span>Create a league to establish its season foundation.</span>
          </p>
        ) : (
          <dl className="dashboard-facts" aria-label="Stored season summary">
            <div>
              <dt>Season</dt>
              <dd>{snapshot.season.displayLabel}</dd>
            </div>
            <div>
              <dt>Current date</dt>
              <dd>
                <time dateTime={snapshot.season.currentDate}>
                  {formatLocalDateForDisplay(snapshot.season.currentDate)}
                </time>
              </dd>
            </div>
            <div>
              <dt>Phase</dt>
              <dd>
                {formatSeasonPhaseForDisplay(snapshot.season.currentPhase)}
              </dd>
            </div>
          </dl>
        )}
      </DashboardCard>

      {snapshot !== null && managedTeamId !== null && scheduleTotals !== null && (
        <>
          <DashboardCard title="Team schedule">
            <dl
              className="dashboard-facts"
              aria-label="Managed-team schedule totals"
            >
              <div>
                <dt>Total games</dt>
                <dd>{scheduleTotals.totalGames}</dd>
              </div>
              <div>
                <dt>Home</dt>
                <dd>{scheduleTotals.homeGames}</dd>
              </div>
              <div>
                <dt>Away</dt>
                <dd>{scheduleTotals.awayGames}</dd>
              </div>
            </dl>
          </DashboardCard>

          <DashboardCard title="Next scheduled game">
            {nextGame === null ? (
              <p>
                No future scheduled game exists on or after the stored current
                date.
              </p>
            ) : (
              <DashboardScheduledGame
                snapshot={snapshot}
                game={nextGame}
                managedTeamId={managedTeamId}
              />
            )}
          </DashboardCard>

          <DashboardCard title="Following games">
            {followingGames.length === 0 ? (
              <p>No additional future scheduled games are available.</p>
            ) : (
              <ol className="dashboard-upcoming-games">
                {followingGames.map((game) => (
                  <li key={game.id}>
                    <DashboardScheduledGame
                      snapshot={snapshot}
                      game={game}
                      managedTeamId={managedTeamId}
                    />
                  </li>
                ))}
              </ol>
            )}
          </DashboardCard>
        </>
      )}
    </div>
  )
}

const GAME_STATUS_LABELS = {
  scheduled: 'Scheduled',
  postponed: 'Postponed',
  completed: 'Completed',
  cancelled: 'Cancelled',
} as const

function DashboardScheduledGame({
  snapshot,
  game,
  managedTeamId,
}: {
  readonly snapshot: LeagueSnapshotV2
  readonly game: LeagueSnapshotV2ScheduledGameDto
  readonly managedTeamId: TeamId
}) {
  const opponent = resolveOpponent(snapshot.league, game, managedTeamId)
  const location = getTeamLocation(game, managedTeamId)

  return (
    <article className="dashboard-scheduled-game">
      <p>
        {game.currentScheduledDate === null ? (
          'TBA'
        ) : (
          <time dateTime={game.currentScheduledDate}>
            {formatLocalDateForDisplay(game.currentScheduledDate)}
          </time>
        )}
      </p>
      <strong>
        {location === 'home' ? 'Home vs' : 'Away at'} {formatTeamName(opponent)}
      </strong>
      <span>{GAME_STATUS_LABELS[game.status]}</span>
    </article>
  )
}

export interface TeamRosterContentProps {
  readonly league: League | null
  readonly team: Team | null
  readonly selectedPlayerId: PlayerId | null
  readonly busy: boolean
  readonly onSelectPlayer: (playerId: PlayerId) => void
  readonly onChangeTeam: () => void
}

export function TeamRosterContent({
  league,
  team,
  selectedPlayerId,
  busy,
  onSelectPlayer,
  onChangeTeam,
}: TeamRosterContentProps) {
  if (league === null) {
    return (
      <section
        className="team-roster-content empty-state"
        aria-labelledby="team-roster-no-league-heading"
      >
        <h2 id="team-roster-no-league-heading">No league available</h2>
        <p>Create a league before opening a team roster.</p>
      </section>
    )
  }

  if (team === null) {
    return (
      <section
        className="team-roster-content empty-state"
        aria-labelledby="team-roster-empty-heading"
      >
        <h2 id="team-roster-empty-heading">No team selected</h2>
        <p>Select the team you control before opening its roster.</p>
        <button
          type="button"
          className="secondary-button"
          onClick={onChangeTeam}
          disabled={busy}
        >
          Choose team
        </button>
      </section>
    )
  }

  const roster = getTeamRoster(league, team.id)
  const selectedPlayer =
    roster.find((player) => player.id === selectedPlayerId) ?? null

  return (
    <div
      className="roster-section team-roster-content"
      aria-labelledby="team-roster-heading"
      aria-busy={busy}
    >
      <button
        type="button"
        className="back-button"
        onClick={onChangeTeam}
        disabled={busy}
      >
        Change team
      </button>

      <div className="team-identity-panel">
        <span
          className="large-team-mark"
          aria-hidden="true"
          style={{
            backgroundColor: team.colors.primary,
            borderColor: team.colors.secondary,
          }}
        >
          {team.mark.text}
        </span>
        <div>
          <p className="eyebrow">Controlled team · {team.abbreviation}</p>
          <h2 id="team-roster-heading">{formatTeamName(team)}</h2>
          <p className="section-intro">
            Select a player to inspect every stored rating and its derived
            grade.
          </p>
        </div>
      </div>

      <div className="roster-layout">
        <div className="roster-panel">
          <div className="panel-heading">
            <div>
              <p className="panel-kicker">Active roster</p>
              <h3>Players</h3>
            </div>
            <span className="count-badge">{roster.length} players</span>
          </div>

          <div
            className="table-scroll"
            role="region"
            aria-label={`${formatTeamName(team)} roster table`}
            tabIndex={0}
          >
            <table className="roster-table">
              <caption className="visually-hidden">
                {formatTeamName(team)} player roster
              </caption>
              <thead>
                <tr>
                  <th scope="col">Player</th>
                  <th scope="col">Position</th>
                  <th scope="col">Age</th>
                  <th scope="col">Details</th>
                </tr>
              </thead>
              <tbody>
                {roster.map((player) => {
                  const isSelected = player.id === selectedPlayerId
                  const playerName = formatPlayerName(player)

                  return (
                    <tr
                      key={player.id}
                      className={isSelected ? 'is-selected' : undefined}
                    >
                      <th scope="row">
                        <span className="player-name">{playerName}</span>
                        <span className="jersey-number">
                          #{player.jerseyNumber}
                        </span>
                      </th>
                      <td>{player.primaryPosition}</td>
                      <td>{player.age}</td>
                      <td>
                        <button
                          type="button"
                          className="player-detail-button"
                          onClick={() => onSelectPlayer(player.id)}
                          aria-pressed={isSelected}
                          aria-controls="player-details"
                          disabled={busy}
                        >
                          {isSelected ? 'Viewing' : 'View ratings'}
                          <span className="visually-hidden">
                            {' '}
                            for {playerName}
                          </span>
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>

        {selectedPlayer === null ? (
          <aside
            id="player-details"
            className="player-details player-details-empty"
            aria-label="Player details"
          >
            <div className="empty-state">
              <p>Select a player to view all 16 stored ratings.</p>
            </div>
          </aside>
        ) : (
          <PlayerDetails player={selectedPlayer} />
        )}
      </div>
    </div>
  )
}

export interface LeagueTeamsContentProps {
  readonly league: League | null
  readonly controlledTeamId: TeamId | null
  readonly busy: boolean
  readonly onOpenControlledRoster: () => void
}

export function LeagueTeamsContent({
  league,
  controlledTeamId,
  busy,
  onOpenControlledRoster,
}: LeagueTeamsContentProps) {
  if (league === null) {
    return (
      <section
        className="league-teams-content empty-state"
        aria-labelledby="league-teams-empty-heading"
      >
        <h2 id="league-teams-empty-heading">No league available</h2>
        <p>No league has been created.</p>
      </section>
    )
  }

  return (
    <div className="league-teams-content">
      <p className="content-count">{league.teams.length} fictional teams</p>

      <div
        className="table-scroll"
        role="region"
        aria-label="League teams table"
        tabIndex={0}
      >
        <table className="league-teams-table league-table">
          <caption className="visually-hidden">
            All teams in league {league.id}
          </caption>
          <thead>
            <tr>
              <th scope="col">Team</th>
              <th scope="col">Abbreviation</th>
              <th scope="col">Players</th>
              <th scope="col">Roster</th>
            </tr>
          </thead>
          <tbody>
            {league.teams.map((team) => {
              const rosterSize = getTeamRoster(league, team.id).length
              const isControlled = team.id === controlledTeamId

              return (
                <tr key={team.id}>
                  <th scope="row">{formatTeamName(team)}</th>
                  <td>{team.abbreviation}</td>
                  <td>{rosterSize}</td>
                  <td>
                    {isControlled ? (
                      <button
                        type="button"
                        className="player-detail-button"
                        onClick={onOpenControlledRoster}
                        disabled={busy}
                      >
                        Open controlled roster
                        <span className="visually-hidden">
                          {' '}
                          for {formatTeamName(team)}
                        </span>
                      </button>
                    ) : (
                      <span aria-label="Not controlled">—</span>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export interface LeaguePlayersContentProps {
  readonly league: League | null
}

export function LeaguePlayersContent({ league }: LeaguePlayersContentProps) {
  const [nameQuery, setNameQuery] = useState('')
  const [position, setPosition] =
    useState<PlayerPositionFilter>('ALL')
  const nameFilterId = useId()
  const positionFilterId = useId()

  if (league === null) {
    return (
      <section
        className="league-players-content empty-state"
        aria-labelledby="league-players-empty-heading"
      >
        <h2 id="league-players-empty-heading">No league available</h2>
        <p>No league has been created.</p>
      </section>
    )
  }

  const players = filterLeaguePlayers(league, nameQuery, position)

  return (
    <div className="league-players-content">
      <p className="content-count" role="status" aria-live="polite">
        {players.length} matching players
      </p>

      <form
        className="player-filter-form"
        onSubmit={(event) => event.preventDefault()}
      >
        <div className="filter-field">
          <label htmlFor={nameFilterId}>Player name</label>
          <input
            id={nameFilterId}
            type="search"
            value={nameQuery}
            onChange={(event) => setNameQuery(event.currentTarget.value)}
            autoComplete="off"
          />
        </div>
        <div className="filter-field">
          <label htmlFor={positionFilterId}>Primary position</label>
          <select
            id={positionFilterId}
            value={position}
            onChange={(event) => {
              const nextPosition = event.currentTarget.value
              if (nextPosition === 'ALL' || isPosition(nextPosition)) {
                setPosition(nextPosition)
              }
            }}
          >
            <option value="ALL">All positions</option>
            {POSITIONS.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </div>
      </form>

      <div
        className="table-scroll"
        role="region"
        aria-label="League players table"
        tabIndex={0}
      >
        <table className="league-players-table league-table">
          <caption className="visually-hidden">
            Players matching the league directory filters
          </caption>
          <thead>
            <tr>
              <th scope="col">Player</th>
              <th scope="col">Team</th>
              <th scope="col">Age</th>
              <th scope="col">Primary position</th>
            </tr>
          </thead>
          <tbody>
            {players.length === 0 ? (
              <tr>
                <td colSpan={4}>No players match these filters.</td>
              </tr>
            ) : (
              players.map((result) => (
                <tr key={result.player.id}>
                  <th scope="row">{result.playerName}</th>
                  <td>
                    {result.teamName} ({result.teamAbbreviation})
                  </td>
                  <td>{result.player.age}</td>
                  <td>{result.player.primaryPosition}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function PlayerDetails({ player }: { readonly player: Player }) {
  const ratingRows = createRatingDisplayRows(player.ratings)
  const playerName = formatPlayerName(player)

  return (
    <aside
      id="player-details"
      className="player-details"
      aria-labelledby="player-details-heading"
    >
      <p className="visually-hidden" aria-live="polite" aria-atomic="true">
        Showing ratings for {playerName}
      </p>
      <div className="player-details-header">
        <div>
          <p className="panel-kicker">Player ratings</p>
          <h3 id="player-details-heading">{playerName}</h3>
          <p>
            #{player.jerseyNumber} · {player.primaryPosition} · Age {player.age}
          </p>
        </div>
        <span className="rating-scale">0–100</span>
      </div>

      <div
        className="table-scroll"
        role="region"
        aria-label={`Ratings for ${playerName}`}
        tabIndex={0}
      >
        <table className="ratings-table">
          <caption className="visually-hidden">
            All stored ratings for {playerName}
          </caption>
          <thead>
            <tr>
              <th scope="col">Rating</th>
              <th scope="col">Value</th>
              <th scope="col">Grade</th>
            </tr>
          </thead>
          <tbody>
            {ratingRows.map((rating) => (
              <tr key={rating.key}>
                <th scope="row">{rating.label}</th>
                <td className="rating-value">{rating.value}</td>
                <td>
                  <span
                    className={`grade-badge grade-${rating.grade.charAt(0).toLowerCase()}`}
                    aria-label={`Letter grade ${rating.grade}`}
                  >
                    {rating.grade}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="derived-note">
        Letter grades are derived from the numeric rating and are never stored.
      </p>
    </aside>
  )
}
