import { Suspense, lazy, useCallback, useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { createNewLeagueSnapshot } from './app/commands/createNewLeagueSnapshot'
import {
  parseSeasonFoundationConfiguration,
} from './app/commands/createSeasonFoundation'
import type { SeasonFoundationConfiguration } from './app/commands/createSeasonFoundation'
import { requestCorruptLeagueStoragePurge } from './app/commands/requestCorruptLeagueStoragePurge'
import {
  SAVE_INDICATOR_LABELS,
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
import type { AvailableNavigationPageId } from './app/navigation'
import type { NavigationPageId } from './app/navigation'
import {
  createLeaguePresentationBundle,
} from './app/leagueSnapshotDomainAdapter'
import type {
  LeaguePresentationBundle,
} from './app/leagueSnapshotDomainAdapter'
import type { PlayerId } from './domain/ids'
import type { Team } from './domain/league'
import { parseLocalDate } from './domain/localDate'
import {
  LeagueSnapshotConflictError,
  LeagueSnapshotQuotaError,
  createIndexedDbLeagueSnapshotRepository,
} from './persistence/indexedDbLeagueSnapshotStorage'
import type { LeagueSnapshotRestorationResult } from './persistence/leagueSnapshotRepository'
import type { LeagueSnapshot } from './persistence/leagueSnapshot'
import { normalizeSeed } from './random/seed'
import {
  LeaguePlayersContent,
  LeagueTeamsContent,
  TeamRosterContent,
} from './ui/dashboardPages'
import { HomeTodayContent } from './ui/homePage'
import { TeamOverviewContent } from './ui/teamOverviewPage'
import {
  ApplicationShell,
  AvailablePage,
  ComingLaterPage,
} from './ui/dashboardShell'
import { getTeamRoster } from './ui/leagueViewModel'
import {
  LeagueCalendarContent,
  LeagueScheduleOverviewContent,
  TeamScheduleContent,
} from './ui/schedulePages'
import {
  LeagueCreationScreen,
  RestoreLoadingScreen,
  RestoreRecoveryScreen,
  TeamSelectionScreen,
  VersionMismatchScreen,
} from './ui/setupPages'
import type {
  SeasonSetupFormField,
  SeasonSetupFormValues,
} from './ui/setupPages'
import './App.css'

const DEFAULT_LEAGUE_SEED = 'stone-league-1'
const DEFAULT_SEASON_SETUP_VALUES = Object.freeze({
  startingYear: '2026',
  regularSeasonStartDate: '2026-10-06',
  calendarDaySpacing: '3',
  scheduleSeed: 'stone-league-1-schedule',
}) satisfies SeasonSetupFormValues

const leagueSnapshotRepository = createIndexedDbLeagueSnapshotRepository()

/**
 * DEV only: the fixture-driven post-game design preview (roadmap §6). The
 * ternary folds to null in production builds, so the lazy chunk — and the
 * fixture inside it — is unreachable and dropped from the bundle.
 */
const DevGameResultPreview = import.meta.env.DEV
  ? lazy(() => import('./ui/devGameResultPreview'))
  : null

let initialRestorePromise: Promise<LeagueSnapshotRestorationResult> | null = null

type BootState =
  | 'restoring'
  | 'ready'
  | 'version-mismatch'
  | 'recovery-required'
type PendingOperation =
  | 'idle'
  | 'creating'
  | 'selecting-team'
  | 'clearing'
  | 'purging-corrupt-storage'
type SetupView = 'create-league' | 'choose-team' | null
type RecoveryKind = 'invalid-save' | 'storage-error'

function restoreInitialSnapshot(): Promise<LeagueSnapshotRestorationResult> {
  initialRestorePromise ??= leagueSnapshotRepository.restore().finally(() => {
    initialRestorePromise = null
  })
  return initialRestorePromise
}

function App() {
  const [seed, setSeed] = useState(DEFAULT_LEAGUE_SEED)
  const [seasonValues, setSeasonValues] = useState<SeasonSetupFormValues>(() =>
    createDefaultSeasonValues(),
  )
  const [snapshot, setSnapshot] = useState<LeagueSnapshot | null>(null)
  const [mismatchStoredVersion, setMismatchStoredVersion] =
    useState<number | null>(null)
  const [selectedPlayerId, setSelectedPlayerId] =
    useState<PlayerId | null>(null)
  const [seedError, setSeedError] = useState<string | null>(null)
  const [seasonError, setSeasonError] = useState<string | null>(null)
  const [bootState, setBootState] = useState<BootState>('restoring')
  const [recoveryKind, setRecoveryKind] =
    useState<RecoveryKind>('invalid-save')
  const [restoreError, setRestoreError] = useState<string | null>(null)
  const [persistenceError, setPersistenceError] = useState<string | null>(null)
  const [pendingOperation, setPendingOperation] =
    useState<PendingOperation>('idle')
  const [devPreviewOpen, setDevPreviewOpen] = useState(false)
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
  const dashboardAction = deriveDashboardAction(
    dashboardState === null
      ? null
      : { ...dashboardState, hasSchedule: true },
  )
  const leagueProgress =
    snapshot === null
      ? undefined
      : {
          seasonLabel: snapshot.season.displayLabel,
          currentDate: snapshot.season.currentDate,
          currentPhase: snapshot.season.currentPhase,
        }

  const resetToLeagueCreation = useCallback((): void => {
    setSnapshot(null)
    setMismatchStoredVersion(null)
    setSeed(DEFAULT_LEAGUE_SEED)
    setSeasonValues(createDefaultSeasonValues())
    setSelectedPlayerId(null)
    setSeedError(null)
    setSeasonError(null)
    setRestoreError(null)
    setPersistenceError(null)
    setActivePageId(DEFAULT_PAGE_ID)
    setSetupView('create-league')
    setBootState('ready')
  }, [])

  const installSnapshot = useCallback((next: LeagueSnapshot): void => {
    const restoredTeam =
      next.managedTeamId === null
        ? null
        : next.league.teams.find(
            (team) => team.id === next.managedTeamId,
          ) ?? null

    setSnapshot(next)
    setMismatchStoredVersion(null)
    setSeed(next.rootSeed)
    setSeasonValues(seasonValuesFromSnapshot(next))
    setSelectedPlayerId(
      restoredTeam === null
        ? null
        : getTeamRoster(next.league, restoredTeam.id)[0]?.id ?? null,
    )
    setSeedError(null)
    setSeasonError(null)
    setRestoreError(null)
    setPersistenceError(null)
    setActivePageId(
      restoredTeam === null ? DEFAULT_PAGE_ID : 'team-roster',
    )
    setSetupView(restoredTeam === null ? 'choose-team' : null)
    setBootState('ready')
  }, [])

  const restoreFromStorage = useCallback(
    async (
      useInitialRestore: boolean,
      isCancelled: () => boolean = () => false,
    ): Promise<void> => {
      setBootState('restoring')
      setRestoreError(null)
      setPersistenceError(null)

      const result = await (useInitialRestore
        ? restoreInitialSnapshot()
        : leagueSnapshotRepository.restore())

      if (isCancelled()) return

      switch (result.kind) {
        case 'empty':
          resetToLeagueCreation()
          return
        case 'restored':
          installSnapshot(result.snapshot)
          return
        case 'version-mismatch':
          setSnapshot(null)
          setMismatchStoredVersion(result.storedVersion)
          setSelectedPlayerId(null)
          setSetupView(null)
          setBootState('version-mismatch')
          return
        case 'recovery-required':
          setSnapshot(null)
          setMismatchStoredVersion(null)
          setSelectedPlayerId(null)
          setSetupView(null)
          setRecoveryKind(
            result.source === 'storage' ? 'storage-error' : 'invalid-save',
          )
          setRestoreError(result.message)
          setBootState('recovery-required')
          return
        default:
          assertNever(result)
      }
    },
    [installSnapshot, resetToLeagueCreation],
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

    let creationInputs: SeasonFoundationConfiguration
    try {
      creationInputs = parseSeasonSetupValues(seasonValues)
      setSeasonError(null)
    } catch (error) {
      setSeasonError(readableError(error, 'The season setup is invalid.'))
      return
    }

    let rootSeed: string
    try {
      rootSeed = normalizeSeed(seed)
      setSeedError(null)
    } catch (error) {
      setSeedError(readableError(error, 'The league seed is invalid.'))
      return
    }

    let nextSnapshot: LeagueSnapshot
    try {
      nextSnapshot = createNewLeagueSnapshot({
        rootSeed,
        ...creationInputs,
      })
    } catch (error) {
      setSeasonError(
        readableError(
          error,
          'The league and season foundation could not be created from those inputs.',
        ),
      )
      return
    }

    setPendingOperation('creating')
    setPersistenceError(null)

    try {
      const stored = await leagueSnapshotRepository.create(nextSnapshot)
      installSnapshot(stored)
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

    setPendingOperation('selecting-team')
    setPersistenceError(null)

    try {
      const updated = await leagueSnapshotRepository.updateManagedTeam({
        expectedLeagueId: snapshot.league.id,
        expectedRevision: snapshot.revision,
        managedTeamId: team.id,
      })
      setSnapshot(updated)
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
      setSelectedPlayerId(
        getTeamRoster(league, controlledTeam.id)[0]?.id ?? null,
      )
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

    if (setupView === null && activePageId === 'schedule-team-schedule') {
      document.getElementById('page-schedule-team-schedule-heading')?.focus()
      return
    }

    handleNavigate('schedule-team-schedule')
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
      'Start a new league? The active local league will be removed.',
    )
    if (!confirmed) return

    setPendingOperation('clearing')
    setPersistenceError(null)

    try {
      await leagueSnapshotRepository.clear({
        kind: 'snapshot',
        expectedLeagueId: snapshot.league.id,
        expectedRevision: snapshot.revision,
      })
      resetToLeagueCreation()
    } catch (error) {
      setPersistenceError(storageWriteMessage(error, 'removed'))
    } finally {
      setPendingOperation('idle')
    }
  }

  async function handleStartOverFromVersionMismatch(): Promise<void> {
    if (mismatchStoredVersion === null || pendingOperation !== 'idle') return

    setPendingOperation('clearing')
    setPersistenceError(null)

    try {
      await leagueSnapshotRepository.clear({
        kind: 'version-mismatch',
        expectedStoredVersion: mismatchStoredVersion,
      })
      resetToLeagueCreation()
    } catch (error) {
      setPersistenceError(storageWriteMessage(error, 'removed'))
    } finally {
      setPendingOperation('idle')
    }
  }

  async function handlePurgeCorruptLeagueStorage(): Promise<void> {
    if (
      bootState !== 'recovery-required' ||
      pendingOperation !== 'idle'
    ) {
      return
    }

    try {
      const result = await requestCorruptLeagueStoragePurge({
        confirm: (message) => window.confirm(message),
        purge: async () => {
          setPendingOperation('purging-corrupt-storage')
          setPersistenceError(null)
          await leagueSnapshotRepository.purgeCorruptLeagueStorage()
        },
      })

      if (result === 'purged') {
        resetToLeagueCreation()
      }
    } catch {
      setPersistenceError(
        'The local league save could not be permanently deleted. Existing records remain, and you can retry.',
      )
    } finally {
      setPendingOperation('idle')
    }
  }

  function handleSeasonValueChange(
    field: SeasonSetupFormField,
    value: string,
  ): void {
    setSeasonValues((current) => ({ ...current, [field]: value }))
    setSeasonError(null)
    setPersistenceError(null)
  }

  if (bootState === 'restoring') {
    return <RestoreLoadingScreen />
  }

  if (bootState === 'version-mismatch') {
    return (
      <VersionMismatchScreen
        actionError={persistenceError}
        isBusy={isBusy}
        onStartNewLeague={() => void handleStartOverFromVersionMismatch()}
      />
    )
  }

  if (bootState === 'recovery-required') {
    return (
      <RestoreRecoveryScreen
        kind={recoveryKind}
        message={
          restoreError ??
          'The saved league could not be restored and was left unchanged.'
        }
        actionError={persistenceError}
        isBusy={isBusy}
        onTryAgain={() => void restoreFromStorage(false)}
        onPurgeCorruptStorage={() =>
          void handlePurgeCorruptLeagueStorage()
        }
      />
    )
  }

  if (DevGameResultPreview !== null && devPreviewOpen) {
    return (
      <Suspense fallback={<p className="dev-preview-loading">Loading preview…</p>}>
        <DevGameResultPreview onBack={() => setDevPreviewOpen(false)} />
      </Suspense>
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
      progress={leagueProgress}
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
          seasonValues={seasonValues}
          seasonError={seasonError}
          isBusy={isBusy}
          onSeedChange={(nextSeed) => {
            setSeed(nextSeed)
            setSeedError(null)
          }}
          onSeasonValueChange={handleSeasonValueChange}
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
        <AvailablePage
          page={activePage}
          section={activeSection}
          heading={
            activePage.id === 'home-today' && controlledTeam !== null
              ? `${controlledTeam.city} ${controlledTeam.nickname}`
              : undefined
          }
        >
          <AvailableWorkspacePage
            pageId={activePage.id}
            snapshot={snapshot}
            controlledTeam={controlledTeam}
            selectedPlayerId={selectedPlayerId}
            isBusy={isBusy}
            saveState={saveState}
            onNavigate={handleNavigate}
            onChangeTeam={handleChangeTeam}
            onSelectPlayer={setSelectedPlayerId}
            onOpenGameResultPreview={
              DevGameResultPreview === null
                ? undefined
                : () => setDevPreviewOpen(true)
            }
          />
        </AvailablePage>
      )}
    </ApplicationShell>
  )
}

interface AvailableWorkspacePageProps {
  readonly pageId: AvailableNavigationPageId
  readonly snapshot: LeagueSnapshot | null
  readonly controlledTeam: Team | null
  readonly selectedPlayerId: PlayerId | null
  readonly isBusy: boolean
  readonly saveState: SaveIndicatorState | null
  readonly onNavigate: (pageId: NavigationPageId) => void
  readonly onChangeTeam: () => void
  readonly onSelectPlayer: (playerId: PlayerId) => void
  readonly onOpenGameResultPreview?: () => void
}

/**
 * Lives beneath the shared WorkspaceErrorBoundary. The authoritative DTO is
 * hydrated and normalized once per snapshot reference, while Team Schedule
 * inspection, filtering, and game selection remain downstream UI state.
 */
function AvailableWorkspacePage({
  pageId,
  snapshot,
  controlledTeam,
  selectedPlayerId,
  isBusy,
  saveState,
  onNavigate,
  onChangeTeam,
  onSelectPlayer,
  onOpenGameResultPreview,
}: AvailableWorkspacePageProps) {
  const presentation = useMemo(
    () =>
      snapshot === null
        ? null
        : createLeaguePresentationBundle(snapshot),
    [snapshot],
  )

  return renderAvailablePage(
    pageId,
    snapshot,
    presentation,
    controlledTeam,
    selectedPlayerId,
    isBusy,
    saveState,
    onNavigate,
    onChangeTeam,
    onSelectPlayer,
    onOpenGameResultPreview,
  )
}

function renderAvailablePage(
  pageId: AvailableNavigationPageId,
  snapshot: LeagueSnapshot | null,
  presentation: LeaguePresentationBundle | null,
  controlledTeam: Team | null,
  selectedPlayerId: PlayerId | null,
  isBusy: boolean,
  saveState: SaveIndicatorState | null,
  onNavigate: (pageId: NavigationPageId) => void,
  onChangeTeam: () => void,
  onSelectPlayer: (playerId: PlayerId) => void,
  onOpenGameResultPreview?: () => void,
) {
  switch (pageId) {
    case 'home-today':
      return (
        <HomeTodayContent
          snapshot={snapshot}
          saveState={
            saveState === null
              ? null
              : { label: SAVE_INDICATOR_LABELS[saveState], state: saveState }
          }
          onNavigate={onNavigate}
          onOpenGameResultPreview={onOpenGameResultPreview}
        />
      )
    case 'team-overview':
      return (
        <TeamOverviewContent
          snapshot={snapshot}
          team={controlledTeam}
          onNavigate={onNavigate}
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
    case 'schedule-team-schedule':
      return <TeamScheduleContent presentation={presentation} />
    case 'schedule-calendar':
      return <LeagueCalendarContent presentation={presentation} />
    case 'league-overview':
      return <LeagueScheduleOverviewContent snapshot={snapshot} />
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

function createDefaultSeasonValues(): SeasonSetupFormValues {
  return { ...DEFAULT_SEASON_SETUP_VALUES }
}

function seasonValuesFromSnapshot(
  snapshot: LeagueSnapshot,
): SeasonSetupFormValues {
  return {
    startingYear: String(snapshot.creationMetadata.startingYear),
    regularSeasonStartDate: snapshot.creationMetadata.regularSeasonStartDate,
    calendarDaySpacing: String(snapshot.creationMetadata.gameDaySpacing),
    scheduleSeed: snapshot.creationMetadata.scheduleSeed,
  }
}

function parseSeasonSetupValues(
  values: SeasonSetupFormValues,
): SeasonFoundationConfiguration {
  return parseSeasonFoundationConfiguration({
    startingYear: parseCanonicalFormInteger(
      values.startingYear,
      'Starting year',
      true,
    ),
    regularSeasonStartDate: parseLocalDate(values.regularSeasonStartDate),
    calendarDaySpacing: parseCanonicalFormInteger(
      values.calendarDaySpacing,
      'Days between game days',
      false,
    ),
    scheduleSeed: values.scheduleSeed,
  })
}

function parseCanonicalFormInteger(
  value: string,
  label: string,
  allowZero: boolean,
): number {
  const pattern = allowZero ? /^(?:0|[1-9]\d*)$/ : /^[1-9]\d*$/
  if (!pattern.test(value)) {
    throw new RangeError(`${label} must be a canonical integer`)
  }
  const parsed = Number(value)
  if (!Number.isSafeInteger(parsed)) {
    throw new RangeError(`${label} must be a safe integer`)
  }
  return parsed
}

function readableError(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback
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

function assertNever(value: never): never {
  throw new RangeError(`Unexpected value: ${String(value)}`)
}

export default App
