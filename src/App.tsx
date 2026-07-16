import { useCallback, useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import type { PlayerId, TeamId } from './domain/ids'
import type { League, Player, Team } from './domain/league'
import { generateLeague } from './generation/generateLeague'
import {
  InvalidLeagueSnapshotError,
  createLeagueSnapshot,
} from './persistence/leagueSnapshot'
import type { LeagueSnapshotV1 } from './persistence/leagueSnapshot'
import {
  LeagueSnapshotConflictError,
  LeagueSnapshotQuotaError,
  createIndexedDbLeagueSnapshotRepository,
} from './persistence/indexedDbLeagueSnapshotStorage'
import { normalizeSeed } from './random/seed'
import {
  createRatingDisplayRows,
  formatPlayerName,
  formatTeamName,
  getTeamRoster,
} from './ui/leagueViewModel'
import './App.css'

const DEFAULT_LEAGUE_SEED = 'stone-league-1'
const leagueSnapshotRepository = createIndexedDbLeagueSnapshotRepository()

let initialRestorePromise: Promise<LeagueSnapshotV1 | null> | null = null

type BootState = 'restoring' | 'ready' | 'invalid-save' | 'storage-error'
type PendingOperation = 'idle' | 'creating' | 'selecting-team' | 'clearing'

function restoreInitialSnapshot(): Promise<LeagueSnapshotV1 | null> {
  initialRestorePromise ??= leagueSnapshotRepository.restore().finally(() => {
    initialRestorePromise = null
  })
  return initialRestorePromise
}

function App() {
  const [seed, setSeed] = useState(DEFAULT_LEAGUE_SEED)
  const [snapshot, setSnapshot] = useState<LeagueSnapshotV1 | null>(null)
  const [viewedTeamId, setViewedTeamId] = useState<TeamId | null>(null)
  const [selectedPlayerId, setSelectedPlayerId] = useState<PlayerId | null>(null)
  const [seedError, setSeedError] = useState<string | null>(null)
  const [bootState, setBootState] = useState<BootState>('restoring')
  const [restoreError, setRestoreError] = useState<string | null>(null)
  const [persistenceError, setPersistenceError] = useState<string | null>(null)
  const [pendingOperation, setPendingOperation] =
    useState<PendingOperation>('idle')

  const league = snapshot?.league ?? null

  const selectedTeam =
    league?.teams.find((team) => team.id === viewedTeamId) ?? null
  const roster =
    league !== null && selectedTeam !== null
      ? getTeamRoster(league, selectedTeam.id)
      : []
  const selectedPlayer =
    roster.find((player) => player.id === selectedPlayerId) ?? roster[0] ?? null

  const restoreFromStorage = useCallback(
    async (
      useInitialRestore: boolean,
      isCancelled: () => boolean = () => false,
    ): Promise<void> => {
      setBootState('restoring')
      setRestoreError(null)
      setPersistenceError(null)

      try {
        const restoredSnapshot = await (useInitialRestore
          ? restoreInitialSnapshot()
          : leagueSnapshotRepository.restore())

        if (isCancelled()) return

        if (restoredSnapshot === null) {
          setSnapshot(null)
          setSeed(DEFAULT_LEAGUE_SEED)
          setViewedTeamId(null)
          setSelectedPlayerId(null)
          setBootState('ready')
          return
        }

        setSnapshot(restoredSnapshot)
        setSeed(restoredSnapshot.rootSeed)
        setViewedTeamId(restoredSnapshot.managedTeamId)
        setSelectedPlayerId(
          restoredSnapshot.managedTeamId === null
            ? null
            : getTeamRoster(
                restoredSnapshot.league,
                restoredSnapshot.managedTeamId,
              )[0]?.id ?? null,
        )
        setBootState('ready')
      } catch (error) {
        if (isCancelled()) return

        setSnapshot(null)
        setViewedTeamId(null)
        setSelectedPlayerId(null)

        if (hasInvalidSnapshotCause(error)) {
          setRestoreError(
            'The saved league is invalid or unsupported. It was left unchanged.',
          )
          setBootState('invalid-save')
        } else {
          setRestoreError(
            'Local browser storage could not be read. Your saved league was left unchanged.',
          )
          setBootState('storage-error')
        }
      }
    },
    [],
  )

  useEffect(() => {
    let cancelled = false
    void restoreFromStorage(true, () => cancelled)

    return () => {
      cancelled = true
    }
  }, [restoreFromStorage])

  async function handleGenerate(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault()

    if (pendingOperation !== 'idle') return

    let nextSnapshot: LeagueSnapshotV1
    let normalizedSeed: string

    try {
      normalizedSeed = normalizeSeed(seed)
      const generatedLeague = generateLeague(normalizedSeed)
      nextSnapshot = createLeagueSnapshot(
        normalizedSeed,
        generatedLeague,
        null,
      )
    } catch (error) {
      setSeedError(
        error instanceof Error
          ? error.message
          : 'The league could not be generated from that seed.',
      )
      return
    }

    setPendingOperation('creating')
    setPersistenceError(null)

    try {
      await leagueSnapshotRepository.create(nextSnapshot)
      setSeed(normalizedSeed)
      setSnapshot(nextSnapshot)
      setViewedTeamId(null)
      setSelectedPlayerId(null)
      setSeedError(null)
    } catch (error) {
      setPersistenceError(storageWriteMessage(error, 'created'))
    } finally {
      setPendingOperation('idle')
    }
  }

  function handleSeedChange(nextSeed: string): void {
    setSeed(nextSeed)
    setSeedError(null)
  }

  async function handleTeamSelection(team: Team): Promise<void> {
    if (snapshot === null || pendingOperation !== 'idle') return

    const teamRoster = getTeamRoster(snapshot.league, team.id)

    if (snapshot.managedTeamId === team.id) {
      setViewedTeamId(team.id)
      setSelectedPlayerId(teamRoster[0]?.id ?? null)
      setPersistenceError(null)
      return
    }

    const nextSnapshot = createLeagueSnapshot(
      snapshot.rootSeed,
      snapshot.league,
      team.id,
    )

    setPendingOperation('selecting-team')
    setPersistenceError(null)

    try {
      await leagueSnapshotRepository.update(nextSnapshot, snapshot.league.id)
      setSnapshot(nextSnapshot)
      setViewedTeamId(team.id)
      setSelectedPlayerId(teamRoster[0]?.id ?? null)
    } catch (error) {
      setPersistenceError(storageWriteMessage(error, 'updated'))
    } finally {
      setPendingOperation('idle')
    }
  }

  function handleBackToTeams(): void {
    setViewedTeamId(null)
    setSelectedPlayerId(null)
    setPersistenceError(null)
  }

  async function handleNewLeague(): Promise<void> {
    if (snapshot === null || pendingOperation !== 'idle') return

    const confirmed = window.confirm(
      'Start a new league? The active league saved in this browser will be removed.',
    )
    if (!confirmed) return

    setPendingOperation('clearing')
    setPersistenceError(null)

    try {
      await leagueSnapshotRepository.clear(snapshot.league.id)
      resetToLeagueCreation()
    } catch (error) {
      setPersistenceError(storageWriteMessage(error, 'removed'))
    } finally {
      setPendingOperation('idle')
    }
  }

  async function handleDiscardInvalidSave(): Promise<void> {
    if (pendingOperation !== 'idle') return

    const confirmed = window.confirm(
      'Discard the unreadable saved league and start a new league? This cannot be undone.',
    )
    if (!confirmed) return

    setPendingOperation('clearing')
    setPersistenceError(null)

    try {
      await leagueSnapshotRepository.clear()
      resetToLeagueCreation()
    } catch (error) {
      setPersistenceError(storageWriteMessage(error, 'removed'))
    } finally {
      setPendingOperation('idle')
    }
  }

  function resetToLeagueCreation(): void {
    setSnapshot(null)
    setSeed(DEFAULT_LEAGUE_SEED)
    setViewedTeamId(null)
    setSelectedPlayerId(null)
    setSeedError(null)
    setRestoreError(null)
    setPersistenceError(null)
    setBootState('ready')
  }

  const isBusy = bootState === 'restoring' || pendingOperation !== 'idle'
  const saveStatus = describeSaveStatus(
    bootState,
    pendingOperation,
    snapshot,
    persistenceError,
  )

  return (
    <div className="app-shell">
      <header className="site-header">
        <div className="brand-lockup">
          <span className="brand-mark" aria-hidden="true">
            S
          </span>
          <span>
            <span className="brand-name">Stone Basketball GM</span>
            <span className="brand-subtitle">Fictional league workshop</span>
          </span>
        </div>
        <div className="header-actions">
          <span className="mode-badge">Read-only preview</span>
          {snapshot !== null && (
            <button
              type="button"
              className="new-league-button"
              onClick={() => void handleNewLeague()}
              disabled={isBusy}
            >
              New league
            </button>
          )}
        </div>
      </header>

      <main aria-busy={isBusy}>
        {persistenceError !== null && bootState === 'ready' && (
          <div className="app-error" role="alert">
            {persistenceError}
          </div>
        )}

        {bootState === 'restoring' ? (
          <RestoreLoadingScreen />
        ) : bootState === 'invalid-save' ? (
          <RestoreRecoveryScreen
            kind="invalid-save"
            message={
              restoreError ??
              'The saved league is invalid or unsupported. It was left unchanged.'
            }
            actionError={persistenceError}
            isBusy={isBusy}
            onTryAgain={() => void restoreFromStorage(false)}
            onDiscard={() => void handleDiscardInvalidSave()}
          />
        ) : bootState === 'storage-error' ? (
          <RestoreRecoveryScreen
            kind="storage-error"
            message={
              restoreError ??
              'Local browser storage could not be read. Your saved league was left unchanged.'
            }
            actionError={persistenceError}
            isBusy={isBusy}
            onTryAgain={() => void restoreFromStorage(false)}
          />
        ) : league === null ? (
          <LeagueCreationScreen
            seed={seed}
            seedError={seedError}
            isBusy={isBusy}
            onSeedChange={handleSeedChange}
            onSubmit={handleGenerate}
          />
        ) : selectedTeam === null ? (
          <TeamSelectionScreen
            league={league}
            seed={seed}
            isBusy={isBusy}
            onSelectTeam={handleTeamSelection}
          />
        ) : (
          <RosterScreen
            team={selectedTeam}
            roster={roster}
            selectedPlayer={selectedPlayer}
            isBusy={isBusy}
            onSelectPlayer={setSelectedPlayerId}
            onBack={handleBackToTeams}
          />
        )}
      </main>

      <footer
        className="site-footer"
        role="status"
        aria-live="polite"
        aria-atomic="true"
      >
        {saveStatus}
      </footer>
    </div>
  )
}

function RestoreLoadingScreen() {
  return (
    <section className="state-layout" aria-labelledby="restore-loading-heading">
      <div className="state-panel">
        <p className="eyebrow">Local league</p>
        <h1 id="restore-loading-heading">Opening your league.</h1>
        <p className="lede">Checking this browser for a saved league…</p>
      </div>
    </section>
  )
}

interface RestoreRecoveryScreenProps {
  readonly kind: 'invalid-save' | 'storage-error'
  readonly message: string
  readonly actionError: string | null
  readonly isBusy: boolean
  readonly onTryAgain: () => void
  readonly onDiscard?: () => void
}

function RestoreRecoveryScreen({
  kind,
  message,
  actionError,
  isBusy,
  onTryAgain,
  onDiscard,
}: RestoreRecoveryScreenProps) {
  const headingRef = useFocusOnMount()
  const isInvalidSave = kind === 'invalid-save'

  return (
    <section
      className="state-layout"
      aria-labelledby="restore-recovery-heading"
      aria-busy={isBusy}
    >
      <div className="state-panel recovery-panel">
        <p className="eyebrow">Local save needs attention</p>
        <h1 id="restore-recovery-heading" ref={headingRef} tabIndex={-1}>
          {isInvalidSave
            ? 'We could not open your saved league.'
            : 'Local storage is not available.'}
        </h1>
        <p className="lede">{message}</p>
        {actionError !== null && (
          <p className="recovery-error" role="alert">
            {actionError}
          </p>
        )}
        <div className="recovery-actions">
          <button
            type="button"
            className="primary-button"
            onClick={onTryAgain}
            disabled={isBusy}
          >
            Try again
          </button>
          {isInvalidSave && onDiscard !== undefined && (
            <button
              type="button"
              className="secondary-button danger-button"
              onClick={onDiscard}
              disabled={isBusy}
            >
              {isBusy ? 'Removing saved league…' : 'Discard save and start new league'}
            </button>
          )}
        </div>
        {isInvalidSave && (
          <p className="recovery-note">
            The unreadable save will remain untouched unless you explicitly
            discard it.
          </p>
        )}
      </div>
    </section>
  )
}

interface LeagueCreationScreenProps {
  readonly seed: string
  readonly seedError: string | null
  readonly isBusy: boolean
  readonly onSeedChange: (seed: string) => void
  readonly onSubmit: (event: FormEvent<HTMLFormElement>) => void
}

function LeagueCreationScreen({
  seed,
  seedError,
  isBusy,
  onSeedChange,
  onSubmit,
}: LeagueCreationScreenProps) {
  const headingRef = useFocusOnMount()
  const seedDescriptionId = seedError === null ? 'seed-help' : 'seed-help seed-error'

  return (
    <section className="creation-layout" aria-labelledby="creation-heading">
      <div className="creation-copy">
        <p className="eyebrow">Milestone 1 · League lab</p>
        <h1 id="creation-heading" ref={headingRef} tabIndex={-1}>
          Build a league worth scouting.
        </h1>
        <p className="lede">
          One seed creates eight fictional clubs and 96 players. Reuse the seed
          whenever you want the exact same league again.
        </p>

        <form
          className="seed-form"
          onSubmit={onSubmit}
          aria-busy={isBusy}
          noValidate
        >
          <label htmlFor="league-seed">League seed</label>
          <div className="seed-controls">
            <input
              id="league-seed"
              name="leagueSeed"
              type="text"
              value={seed}
              onChange={(event) => onSeedChange(event.target.value)}
              aria-describedby={seedDescriptionId}
              aria-invalid={seedError !== null}
              autoComplete="off"
              spellCheck={false}
              disabled={isBusy}
            />
            <button type="submit" className="primary-button" disabled={isBusy}>
              {isBusy ? 'Saving league…' : 'Generate league'}
            </button>
          </div>
          <p id="seed-help" className="field-help">
            Seeds are case-sensitive. No account or internet connection is used.
          </p>
          {seedError !== null && (
            <p id="seed-error" className="field-error" role="alert">
              {seedError}
            </p>
          )}
        </form>
      </div>

      <aside className="creation-summary" aria-label="Generated league contents">
        <div className="court-mark" aria-hidden="true">
          <span>8</span>
        </div>
        <p className="summary-kicker">Every generated league includes</p>
        <dl className="league-facts">
          <div>
            <dt>Teams</dt>
            <dd>8 fictional clubs</dd>
          </div>
          <div>
            <dt>Players</dt>
            <dd>12 per roster</dd>
          </div>
          <div>
            <dt>Ratings</dt>
            <dd>16 skills per player</dd>
          </div>
        </dl>
      </aside>
    </section>
  )
}

interface TeamSelectionScreenProps {
  readonly league: League
  readonly seed: string
  readonly isBusy: boolean
  readonly onSelectTeam: (team: Team) => void
}

function TeamSelectionScreen({
  league,
  seed,
  isBusy,
  onSelectTeam,
}: TeamSelectionScreenProps) {
  const headingRef = useFocusOnMount()

  return (
    <section
      className="content-section"
      aria-labelledby="team-selection-heading"
      aria-busy={isBusy}
    >
      <div className="section-heading-row">
        <div>
          <p className="eyebrow">League generated · {league.seedFingerprint}</p>
          <h1 id="team-selection-heading" ref={headingRef} tabIndex={-1}>
            Choose your front office.
          </h1>
          <p className="section-intro">
            Eight fictional teams were generated from <strong>{seed}</strong>.
            Select one to inspect its roster.
          </p>
        </div>
        <span className="count-badge">8 teams</span>
      </div>

      <ul className="team-grid" aria-label="Generated teams">
        {league.teams.map((team) => (
          <li key={team.id}>
            <button
              type="button"
              className="team-card"
              onClick={() => void onSelectTeam(team)}
              aria-label={`Manage ${formatTeamName(team)}`}
              style={{ borderTopColor: team.colors.secondary }}
              disabled={isBusy}
            >
              <span
                className="team-card-mark"
                aria-hidden="true"
                style={{ backgroundColor: team.colors.primary }}
              >
                {team.mark.text}
              </span>
              <span className="team-card-copy">
                <span className="team-city">{team.city}</span>
                <span className="team-nickname">{team.nickname}</span>
                <span className="team-action">Inspect roster →</span>
              </span>
              <span className="team-swatches" aria-hidden="true">
                <span style={{ backgroundColor: team.colors.primary }} />
                <span style={{ backgroundColor: team.colors.secondary }} />
                <span style={{ backgroundColor: team.colors.accent }} />
              </span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}

interface RosterScreenProps {
  readonly team: Team
  readonly roster: readonly Player[]
  readonly selectedPlayer: Player | null
  readonly isBusy: boolean
  readonly onSelectPlayer: (playerId: PlayerId) => void
  readonly onBack: () => void
}

function RosterScreen({
  team,
  roster,
  selectedPlayer,
  isBusy,
  onSelectPlayer,
  onBack,
}: RosterScreenProps) {
  const headingRef = useFocusOnMount()

  return (
    <section
      className="content-section roster-section"
      aria-labelledby="roster-heading"
      aria-busy={isBusy}
    >
      <button
        type="button"
        className="back-button"
        onClick={onBack}
        disabled={isBusy}
      >
        ← Back to team selection
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
          <p className="eyebrow">Your selected team · {team.abbreviation}</p>
          <h1 id="roster-heading" ref={headingRef} tabIndex={-1}>
            {formatTeamName(team)}
          </h1>
          <p className="section-intro">
            Review the 12-player roster. Select a player to inspect every stored
            rating and its derived grade.
          </p>
        </div>
      </div>

      <div className="roster-layout">
        <div className="roster-panel">
          <div className="panel-heading">
            <div>
              <p className="panel-kicker">Active roster</p>
              <h2>Players</h2>
            </div>
            <span className="count-badge">{roster.length} players</span>
          </div>

          <div className="table-scroll">
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
                  const isSelected = player.id === selectedPlayer?.id
                  const playerName = formatPlayerName(player)

                  return (
                    <tr key={player.id} className={isSelected ? 'is-selected' : undefined}>
                      <th scope="row">
                        <span className="player-name">{playerName}</span>
                        <span className="jersey-number">#{player.jerseyNumber}</span>
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
                          disabled={isBusy}
                        >
                          {isSelected ? 'Viewing' : 'View ratings'}
                          <span className="visually-hidden"> for {playerName}</span>
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>

        {selectedPlayer !== null && <PlayerDetails player={selectedPlayer} />}
      </div>
    </section>
  )
}

function PlayerDetails({ player }: { readonly player: Player }) {
  const ratingRows = createRatingDisplayRows(player.ratings)

  return (
    <aside
      id="player-details"
      className="player-details"
      aria-labelledby="player-details-heading"
    >
      <p className="visually-hidden" aria-live="polite" aria-atomic="true">
        Showing ratings for {formatPlayerName(player)}
      </p>
      <div className="player-details-header">
        <div>
          <p className="panel-kicker">Player ratings</p>
          <h2 id="player-details-heading">{formatPlayerName(player)}</h2>
          <p>
            #{player.jerseyNumber} · {player.primaryPosition} · Age {player.age}
          </p>
        </div>
        <span className="rating-scale">0–100</span>
      </div>

      <div className="table-scroll">
        <table className="ratings-table">
          <caption className="visually-hidden">
            All stored ratings for {formatPlayerName(player)}
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

function useFocusOnMount() {
  const headingRef = useRef<HTMLHeadingElement>(null)

  useEffect(() => {
    headingRef.current?.focus()
  }, [])

  return headingRef
}

function hasInvalidSnapshotCause(error: unknown): boolean {
  const seen = new Set<unknown>()
  let current = error

  while (current instanceof Error && !seen.has(current)) {
    if (current instanceof InvalidLeagueSnapshotError) return true
    seen.add(current)
    current = current.cause
  }

  return false
}

function storageWriteMessage(error: unknown, action: string): string {
  if (error instanceof LeagueSnapshotConflictError) {
    return 'The active league changed in another tab. Nothing was overwritten. Reload and try again.'
  }

  if (error instanceof LeagueSnapshotQuotaError) {
    return `Browser storage is full, so the league could not be ${action}. The last confirmed league was kept.`
  }

  return `The league could not be ${action} in local browser storage. The last confirmed league was kept.`
}

function describeSaveStatus(
  bootState: BootState,
  pendingOperation: PendingOperation,
  snapshot: LeagueSnapshotV1 | null,
  persistenceError: string | null,
): string {
  if (bootState === 'restoring') {
    return 'Checking this browser for a saved league…'
  }
  if (pendingOperation === 'creating' || pendingOperation === 'selecting-team') {
    return 'Saving league locally…'
  }
  if (pendingOperation === 'clearing') {
    return 'Removing the active saved league…'
  }
  if (bootState === 'invalid-save') {
    return 'The saved league needs attention and was left unchanged.'
  }
  if (bootState === 'storage-error') {
    return 'Local browser storage is unavailable.'
  }
  if (persistenceError !== null) {
    return 'The latest change was not saved. The last confirmed league was kept.'
  }
  if (snapshot !== null) {
    return 'League saved locally in this browser.'
  }
  return 'No league is currently saved in this browser.'
}

export default App
