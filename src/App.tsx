import { useCallback, useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import {
  SAVE_INDICATOR_LABELS,
  createSavedLeagueDashboardSummary,
  deriveDashboardAction,
} from './app/dashboardViewModel'
import type {
  DashboardAction,
  SaveIndicatorState,
} from './app/dashboardViewModel'
import {
  DEFAULT_PAGE_ID,
  getPageById,
  getSectionForPage,
} from './app/navigation'
import type { NavigationPageId } from './app/navigation'
import type { AvailableNavigationPageId } from './app/navigation'
import type { PlayerId } from './domain/ids'
import type { Team } from './domain/league'
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
  DashboardOverviewContent,
  LeaguePlayersContent,
  LeagueTeamsContent,
  TeamRosterContent,
} from './ui/dashboardPages'
import {
  ApplicationShell,
  AvailablePage,
  ComingLaterPage,
} from './ui/dashboardShell'
import { getTeamRoster } from './ui/leagueViewModel'
import {
  LeagueCreationScreen,
  RestoreLoadingScreen,
  RestoreRecoveryScreen,
  TeamSelectionScreen,
} from './ui/setupPages'
import './App.css'

const DEFAULT_LEAGUE_SEED = 'stone-league-1'
const leagueSnapshotRepository = createIndexedDbLeagueSnapshotRepository()

let initialRestorePromise: Promise<LeagueSnapshotV1 | null> | null = null

type BootState = 'restoring' | 'ready' | 'invalid-save' | 'storage-error'
type PendingOperation = 'idle' | 'creating' | 'selecting-team' | 'clearing'
type SetupView = 'create-league' | 'choose-team' | null

function restoreInitialSnapshot(): Promise<LeagueSnapshotV1 | null> {
  initialRestorePromise ??= leagueSnapshotRepository.restore().finally(() => {
    initialRestorePromise = null
  })
  return initialRestorePromise
}

function App() {
  const [seed, setSeed] = useState(DEFAULT_LEAGUE_SEED)
  const [snapshot, setSnapshot] = useState<LeagueSnapshotV1 | null>(null)
  const [selectedPlayerId, setSelectedPlayerId] =
    useState<PlayerId | null>(null)
  const [seedError, setSeedError] = useState<string | null>(null)
  const [bootState, setBootState] = useState<BootState>('restoring')
  const [restoreError, setRestoreError] = useState<string | null>(null)
  const [persistenceError, setPersistenceError] = useState<string | null>(null)
  const [pendingOperation, setPendingOperation] =
    useState<PendingOperation>('idle')
  const [activePageId, setActivePageId] =
    useState<NavigationPageId>(DEFAULT_PAGE_ID)
  const [setupView, setSetupView] = useState<SetupView>(null)

  const league = snapshot?.league ?? null
  const controlledTeam =
    league?.teams.find((team) => team.id === snapshot?.managedTeamId) ?? null
  const isBusy = pendingOperation !== 'idle'
  const saveState: SaveIndicatorState | null =
    persistenceError !== null
      ? 'error'
      : pendingOperation !== 'idle'
        ? 'saving'
        : snapshot === null
          ? null
          : 'saved'
  const dashboardState =
    snapshot === null
      ? null
      : { league: snapshot.league, managedTeamId: snapshot.managedTeamId }
  const dashboardAction = deriveDashboardAction(dashboardState)
  const dashboardSummary =
    dashboardState === null
      ? null
      : createSavedLeagueDashboardSummary(dashboardState)

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
          resetToLeagueCreation()
          return
        }

        const restoredTeam =
          restoredSnapshot.managedTeamId === null
            ? null
            : restoredSnapshot.league.teams.find(
                (team) => team.id === restoredSnapshot.managedTeamId,
              ) ?? null

        setSnapshot(restoredSnapshot)
        setSeed(restoredSnapshot.rootSeed)
        setSelectedPlayerId(
          restoredTeam === null
            ? null
            : getTeamRoster(restoredSnapshot.league, restoredTeam.id)[0]?.id ??
                null,
        )
        setActivePageId(
          restoredTeam === null ? DEFAULT_PAGE_ID : 'team-roster',
        )
        setSetupView(restoredTeam === null ? 'choose-team' : null)
        setBootState('ready')
      } catch (error) {
        if (isCancelled()) return

        setSnapshot(null)
        setSelectedPlayerId(null)
        setSetupView(null)

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

    let normalizedSeed: string
    let nextSnapshot: LeagueSnapshotV1

    try {
      normalizedSeed = normalizeSeed(seed)
      nextSnapshot = createLeagueSnapshot(
        normalizedSeed,
        generateLeague(normalizedSeed),
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
      setSelectedPlayerId(null)
      setSeedError(null)
      setActivePageId(DEFAULT_PAGE_ID)
      setSetupView('choose-team')
    } catch (error) {
      setPersistenceError(storageWriteMessage(error, 'created'))
    } finally {
      setPendingOperation('idle')
    }
  }

  async function handleTeamSelection(team: Team): Promise<void> {
    if (snapshot === null || pendingOperation !== 'idle') return

    const teamRoster = getTeamRoster(snapshot.league, team.id)

    if (snapshot.managedTeamId === team.id) {
      setSelectedPlayerId(teamRoster[0]?.id ?? null)
      setPersistenceError(null)
      setActivePageId('team-roster')
      setSetupView(null)
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
      setSelectedPlayerId(teamRoster[0]?.id ?? null)
      setActivePageId('team-roster')
      setSetupView(null)
    } catch (error) {
      setPersistenceError(storageWriteMessage(error, 'updated'))
    } finally {
      setPendingOperation('idle')
    }
  }

  function handleNavigate(pageId: NavigationPageId): void {
    if (pendingOperation !== 'idle') return

    setActivePageId(pageId)
    setSetupView(null)

    if (
      pageId === 'team-roster' &&
      league !== null &&
      controlledTeam !== null &&
      selectedPlayerId === null
    ) {
      setSelectedPlayerId(getTeamRoster(league, controlledTeam.id)[0]?.id ?? null)
    }
  }

  function handleMainMenu(): void {
    if (pendingOperation !== 'idle') return

    setActivePageId(DEFAULT_PAGE_ID)
    setSetupView(null)
  }

  function handleAuthoritativeAction(action: DashboardAction): void {
    if (pendingOperation !== 'idle') return

    if (action.target === 'create-league') {
      if (setupView === 'create-league') {
        document.getElementById('league-seed')?.focus()
        return
      }
      setActivePageId(DEFAULT_PAGE_ID)
      setSetupView('create-league')
      return
    }

    if (action.target === 'choose-team') {
      if (setupView === 'choose-team') {
        document
          .querySelector<HTMLButtonElement>('[data-team-choice]')
          ?.focus()
        return
      }
      setActivePageId(DEFAULT_PAGE_ID)
      setSetupView('choose-team')
      return
    }

    if (setupView === null && activePageId === 'team-roster') {
      document.getElementById('page-team-roster-heading')?.focus()
      return
    }

    handleNavigate('team-roster')
  }

  function handleChangeTeam(): void {
    if (pendingOperation !== 'idle') return

    setSelectedPlayerId(null)
    setActivePageId('team-roster')
    setSetupView('choose-team')
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
    setSelectedPlayerId(null)
    setSeedError(null)
    setRestoreError(null)
    setPersistenceError(null)
    setActivePageId(DEFAULT_PAGE_ID)
    setSetupView('create-league')
    setBootState('ready')
  }

  if (bootState === 'restoring') {
    return <RestoreLoadingScreen />
  }

  if (bootState === 'invalid-save') {
    return (
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
    )
  }

  if (bootState === 'storage-error') {
    return (
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
    )
  }

  const activePage = getPageById(activePageId)
  const activeSection = getSectionForPage(activePageId)
  if (activePage === undefined || activeSection === undefined) {
    throw new RangeError(`Navigation page ${activePageId} is not configured`)
  }

  return (
    <ApplicationShell
      activePageId={activePageId}
      pageNavigationActive={setupView === null}
      controlledTeam={controlledTeam}
      saveState={saveState}
      dashboardAction={dashboardAction}
      busy={isBusy}
      onNavigate={handleNavigate}
      onMainMenu={handleMainMenu}
      onAuthoritativeAction={handleAuthoritativeAction}
      onNewLeague={snapshot === null ? undefined : () => void handleNewLeague()}
    >
      {persistenceError !== null && (
        <p className="app-error" role="alert">
          {persistenceError}
        </p>
      )}

      {setupView === 'create-league' ? (
        <LeagueCreationScreen
          seed={seed}
          seedError={seedError}
          isBusy={isBusy}
          onSeedChange={(nextSeed) => {
            setSeed(nextSeed)
            setSeedError(null)
          }}
          onSubmit={(event) => void handleGenerate(event)}
          onMainMenu={handleMainMenu}
        />
      ) : setupView === 'choose-team' && league !== null ? (
        <TeamSelectionScreen
          league={league}
          seed={seed}
          controlledTeamId={snapshot?.managedTeamId ?? null}
          isBusy={isBusy}
          onSelectTeam={(team) => void handleTeamSelection(team)}
          onMainMenu={handleMainMenu}
        />
      ) : activePage.availability === 'planned' ? (
        <ComingLaterPage page={activePage} section={activeSection} />
      ) : (
        <AvailablePage page={activePage} section={activeSection}>
          {renderAvailablePage(
            activePage.id,
            snapshot,
            controlledTeam,
            selectedPlayerId,
            isBusy,
            saveState,
            dashboardSummary,
            handleNavigate,
            handleChangeTeam,
            setSelectedPlayerId,
          )}
        </AvailablePage>
      )}
    </ApplicationShell>
  )
}

function renderAvailablePage(
  pageId: AvailableNavigationPageId,
  snapshot: LeagueSnapshotV1 | null,
  controlledTeam: Team | null,
  selectedPlayerId: PlayerId | null,
  isBusy: boolean,
  saveState: SaveIndicatorState | null,
  dashboardSummary: ReturnType<typeof createSavedLeagueDashboardSummary> | null,
  onNavigate: (pageId: NavigationPageId) => void,
  onChangeTeam: () => void,
  onSelectPlayer: (playerId: PlayerId) => void,
) {
  switch (pageId) {
    case 'dashboard-overview':
      return (
        <DashboardOverviewContent
          summary={dashboardSummary}
          saveState={
            saveState === null
              ? null
              : { label: SAVE_INDICATOR_LABELS[saveState], state: saveState }
          }
        />
      )
    case 'team-roster':
      return (
        <TeamRosterContent
          league={snapshot?.league ?? null}
          team={controlledTeam}
          selectedPlayerId={selectedPlayerId}
          busy={isBusy}
          onSelectPlayer={onSelectPlayer}
          onChangeTeam={onChangeTeam}
        />
      )
    case 'league-teams':
      return (
        <LeagueTeamsContent
          league={snapshot?.league ?? null}
          controlledTeamId={snapshot?.managedTeamId ?? null}
          busy={isBusy}
          onOpenControlledRoster={() => onNavigate('team-roster')}
        />
      )
    case 'league-players':
      return <LeaguePlayersContent league={snapshot?.league ?? null} />
    default:
      return assertNever(pageId)
  }
}

function assertNever(value: never): never {
  throw new RangeError(`Available navigation page ${String(value)} has no view`)
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

export default App
