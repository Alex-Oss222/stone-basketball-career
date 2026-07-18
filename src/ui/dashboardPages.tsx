import { useEffect, useId, useRef, useState } from 'react'
import type { PlayerId, TeamId } from '../domain/ids'
import { POSITIONS, isPosition } from '../domain/league'
import type { League, Team } from '../domain/league'
import { filterLeaguePlayers } from '../app/dashboardViewModel'
import type { PlayerPositionFilter } from '../app/dashboardViewModel'
import { deriveVersionedOverall } from '../domain/playerDerivations'
import {
  formatPlayerName,
  formatTeamName,
  getTeamRoster,
} from './leagueViewModel'
import { PlayerQuickView } from './playerQuickView'
import { RosterDepthChart } from './rosterDepthChart'

export interface TeamRosterContentProps {
  readonly league: League | null
  readonly team: Team | null
  readonly busy: boolean
  /** Clicking a player opens the full player page. */
  readonly onOpenPlayer: (playerId: PlayerId) => void
  readonly onChangeTeam: () => void
  /** Dev/test convenience only; the tab is transient UI state. */
  readonly initialTab?: 'players' | 'depth'
}

export function TeamRosterContent({
  league,
  team,
  busy,
  onOpenPlayer,
  onChangeTeam,
  initialTab = 'players',
}: TeamRosterContentProps) {
  /** Hover/focus preview — transient UI state, never persisted. The popover
   * anchors to the hovered row so it appears beside the cursor, clamped so it
   * never runs past the bottom of the roster panel. Dwelling for a few
   * seconds pins it: it stays put, becomes interactive, and gains the Health
   * and Development tabs. */
  const [preview, setPreview] = useState<{
    readonly playerId: PlayerId
    readonly top: number
  } | null>(null)
  const [isPinned, setIsPinned] = useState(false)
  const [rosterTab, setRosterTab] = useState<'players' | 'depth'>(initialTab)
  const rosterPanelRef = useRef<HTMLDivElement>(null)
  const previewPlayerId = preview?.playerId ?? null

  useEffect(() => {
    if (previewPlayerId === null) {
      setIsPinned(false)
      return
    }
    const timer = window.setTimeout(
      () => setIsPinned(true),
      QUICK_VIEW_PIN_DELAY_MS,
    )
    return () => window.clearTimeout(timer)
  }, [previewPlayerId])

  useEffect(() => {
    if (!isPinned) return
    function onKeyDown(event: KeyboardEvent): void {
      if (event.key === 'Escape') {
        setIsPinned(false)
        setPreview(null)
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [isPinned])

  function showPreview(playerId: PlayerId, anchor: HTMLElement): void {
    const panel = rosterPanelRef.current
    if (panel === null) {
      setPreview({ playerId, top: 0 })
      return
    }
    // Track the hovered row, but shift up as needed so the whole popover
    // stays inside the visible viewport.
    const panelTop = panel.getBoundingClientRect().top
    const rowTop = anchor.getBoundingClientRect().top
    const highestVisibleTop = window.innerHeight - POPOVER_CLEARANCE
    const top = Math.max(8, Math.min(rowTop, highestVisibleTop) - panelTop)
    setPreview({ playerId, top })
  }

  function closeQuickView(): void {
    setIsPinned(false)
    setPreview(null)
  }

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
  const previewPlayer =
    roster.find((player) => player.id === preview?.playerId) ?? null

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
            Hover a player to preview them; click a player to open their full
            page.
          </p>
        </div>
      </div>

      <nav className="player-page-tabs roster-tabs" aria-label="Roster sections">
        <button
          type="button"
          className="player-tab"
          aria-current={rosterTab === 'players'}
          onClick={() => setRosterTab('players')}
        >
          Players
        </button>
        <button
          type="button"
          className="player-tab"
          aria-current={rosterTab === 'depth'}
          onClick={() => setRosterTab('depth')}
        >
          Depth &amp; Roles
        </button>
        {/* DEFERRED(later): Contracts and Compare need their systems. */}
        <button
          type="button"
          className="player-tab"
          disabled
          title="Contract details arrive with the financial model."
        >
          Contracts <span className="coming-later-marker">Coming later</span>
        </button>
        <button
          type="button"
          className="player-tab"
          disabled
          title="Player comparison arrives later."
        >
          Compare <span className="coming-later-marker">Coming later</span>
        </button>
      </nav>

      {rosterTab === 'depth' ? (
        <div className="roster-depth-tab">
          <RosterDepthChart roster={roster} />
        </div>
      ) : (
        <div
          className="roster-panel"
          ref={rosterPanelRef}
          onMouseLeave={() => {
            if (!isPinned) setPreview(null)
          }}
        >
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
                  <th scope="col">Status</th>
                  <th scope="col">Pos / Role</th>
                  <th scope="col">Age</th>
                  <th scope="col">OVR</th>
                  <th scope="col">Target</th>
                  <th scope="col">Actual</th>
                  <th scope="col">USG%</th>
                  <th scope="col">Form</th>
                  <th scope="col">Impact</th>
                  <th scope="col">Contract</th>
                  <th scope="col">Dev</th>
                </tr>
              </thead>
              <tbody>
                {roster.map((player) => {
                  const isPreviewed = player.id === preview?.playerId
                  const playerName = formatPlayerName(player)

                  return (
                    <tr
                      key={player.id}
                      className={isPreviewed ? 'is-selected' : undefined}
                      onMouseEnter={(event) => {
                        if (!isPinned) {
                          showPreview(player.id, event.currentTarget)
                        }
                      }}
                    >
                      <th scope="row">
                        <button
                          type="button"
                          className="player-name-button"
                          onClick={() => onOpenPlayer(player.id)}
                          onFocus={(event) => {
                            if (!isPinned) {
                              showPreview(player.id, event.currentTarget)
                            }
                          }}
                          onBlur={() => {
                            if (!isPinned) setPreview(null)
                          }}
                          disabled={busy}
                        >
                          <span className="player-name">{playerName}</span>
                          <span className="jersey-number">
                            #{player.jerseyNumber}
                          </span>
                          <span className="visually-hidden">
                            Open the full player page
                          </span>
                        </button>
                      </th>
                      {/* DEFERRED(later): availability status needs the medical system. */}
                      <td className="deferred-cell">—</td>
                      <td>
                        <span className="pos-role-position">
                          {player.primaryPosition}
                        </span>
                        {/* DEFERRED(§8): the role badge comes from the rotation plan. */}
                        <span className="pos-role-role">—</span>
                      </td>
                      <td>{player.age}</td>
                      <td className="rating-value">
                        {deriveVersionedOverall(
                          player.ratings,
                          player.primaryPosition,
                        )}
                      </td>
                      {/* DEFERRED(§8): target minutes come from the rotation plan. */}
                      <td className="deferred-cell">—</td>
                      {/* DEFERRED(§11): actual minutes, usage, and form need real statistics. */}
                      <td className="deferred-cell">—</td>
                      <td className="deferred-cell">—</td>
                      <td className="deferred-cell">—</td>
                      {/* DEFERRED(§11): impact needs real per-game statistics. */}
                      <td className="deferred-cell">—</td>
                      {/* DEFERRED(later): contract years need the financial model. */}
                      <td className="deferred-cell">—</td>
                      {/* DEFERRED(later): development trend needs the development system. */}
                      <td className="deferred-cell">—</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {previewPlayer !== null && preview !== null && (
            <div
              className={
                isPinned
                  ? 'player-quick-view-popover is-pinned'
                  : 'player-quick-view-popover'
              }
              style={{ top: preview.top }}
            >
              <PlayerQuickView
                player={previewPlayer}
                team={team}
                pinned={isPinned}
                onClose={closeQuickView}
              />
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/** Dwell time before the hover quick view pins and becomes interactive. */
const QUICK_VIEW_PIN_DELAY_MS = 5000

/** Popover height (plus margin) used to keep it fully inside the viewport. */
const POPOVER_CLEARANCE = 580

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

