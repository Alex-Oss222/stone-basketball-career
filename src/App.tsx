import { useCallback, useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { createNewLeagueSnapshotV2 } from './app/commands/createNewLeagueSnapshotV2'
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
import type { LeagueId, PlayerId } from './domain/ids'
import type { Team } from './domain/league'
import { parseLocalDate } from './domain/localDate'
import {
  LeagueSnapshotConflictError,
  LeagueSnapshotQuotaError,
  createIndexedDbLeagueSnapshotRepository,
} from './persistence/indexedDbLeagueSnapshotStorage'
import {
  LeagueSnapshotRepositoryMigrationError,
} from './persistence/leagueSnapshotRepository'
import type { LeagueSnapshotRestorationResult } from './persistence/leagueSnapshotRepository'
import type { LeagueSnapshotV2 } from './persistence/leagueSnapshotV2'
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
  LeagueScheduleOverviewContent,
  ScheduleCalendarContent,
  TeamScheduleContent,
} from './ui/schedulePages'
import {
  LeagueCreationScreen,
  MigrationRequiredScreen,
  RestoreLoadingScreen,
  RestoreRecoveryScreen,
  TeamSelectionScreen,
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

let initialRestorePromise: Promise<LeagueSnapshotRestorationResult> | null = null

type BootState =
  | 'restoring'
  | 'ready'
  | 'migration-required'
  | 'recovery-required'
type PendingOperation =
  | 'idle'
  | 'creating'
  | 'migrating'
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
  const [snapshot, setSnapshot] = useState<LeagueSnapshotV2 | null>(null)
  const [migrationLeagueId, setMigrationLeagueId] =
    useState<LeagueId | null>(null)
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
    setMigrationLeagueId(null)
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

  const installSnapshot = useCallback((next: LeagueSnapshotV2): void => {
    const restoredTeam =
      next.managedTeamId === null
        ? null
        : next.league.teams.find(
            (team) => team.id === next.managedTeamId,
          ) ?? null

    setSnapshot(next)
    setMigrationLeagueId(null)
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
        case 'restored-v2':
          installSnapshot(result.snapshot)
          return
        case 'migration-required':
          setSnapshot(null)
          setMigrationLeagueId(result.leagueId)
          setSelectedPlayerId(null)
          setSetupView(null)
          setSeasonError(null)
          setBootState('migration-required')
          return
        case 'recovery-required':
          setSnapshot(null)
          setMigrationLeagueId(null)
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

    let nextSnapshot: LeagueSnapshotV2
    try {
      nextSnapshot = createNewLeagueSnapshotV2({
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
      const stored = await leagueSnapshotRepository.createV2(nextSnapshot)
      installSnapshot(stored)
    } catch (error) {
      setPersistenceError(storageWriteMessage(error, 'created'))
    } finally {
      setPendingOperation('idle')
    }
  }

  async function handleMigrate(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault()
    if (pendingOperation !== 'idle' || migrationLeagueId === null) return

    let creationInputs: SeasonFoundationConfiguration
    try {
      creationInputs = parseSeasonSetupValues(seasonValues)
      setSeasonError(null)
    } catch (error) {
      setSeasonError(readableError(error, 'The season setup is invalid.'))
      return
    }

    setPendingOperation('migrating')
    setPersistenceError(null)

    try {
      const migrated = await leagueSnapshotRepository.migrateV1ToV2({
        expectedV1LeagueId: migrationLeagueId,
        seasonCreationInputs: creationInputs,
      })
      installSnapshot(migrated)
    } catch (error) {
      setPersistenceError(migrationFailureMessage(error))
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
      'Start a new league? Both active local snapshot versions will be removed.',
    )
    if (!confirmed) return

    setPendingOperation('clearing')
    setPersistenceError(null)

    try {
      await leagueSnapshotRepository.clear({
        kind: 'v2',
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

  async function handleDiscardV1(): Promise<void> {
    if (migrationLeagueId === null || pendingOperation !== 'idle') return

    const confirmed = window.confirm(
      'Discard the version 1 saved league and start a new league? This cannot be undone.',
    )
    if (!confirmed) return

    setPendingOperation('clearing')
    setPersistenceError(null)

    try {
      await leagueSnapshotRepository.clear({
        kind: 'v1',
        expectedLeagueId: migrationLeagueId,
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

  if (bootState === 'migration-required') {
    return (
      <MigrationRequiredScreen
        seasonValues={seasonValues}
        seasonError={seasonError}
        actionError={persistenceError}
        isBusy={isBusy}
        onSeasonValueChange={handleSeasonValueChange}
        onMigrate={(event) => void handleMigrate(event)}
        onTryAgain={() => void restoreFromStorage(false)}
        onDiscard={() => void handleDiscardV1()}
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
        <AvailablePage page={activePage} section={activeSection}>
          {renderAvailablePage(
            activePage.id,
            snapshot,
            controlledTeam,
            selectedPlayerId,
            isBusy,
            saveState,
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
  snapshot: LeagueSnapshotV2 | null,
  controlledTeam: Team | null,
  selectedPlayerId: PlayerId | null,
  isBusy: boolean,
  saveState: SaveIndicatorState | null,
  onNavigate: (pageId: NavigationPageId) => void,
  onChangeTeam: () => void,
  onSelectPlayer: (playerId: PlayerId) => void,
) {
  switch (pageId) {
    case 'dashboard-overview':
      return (
        <DashboardOverviewContent
          snapshot={snapshot}
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
    case 'schedule-team-schedule':
      return <TeamScheduleContent snapshot={snapshot} />
    case 'schedule-calendar':
      return <ScheduleCalendarContent snapshot={snapshot} />
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
  snapshot: LeagueSnapshotV2,
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

function migrationFailureMessage(error: unknown): string {
  if (error instanceof LeagueSnapshotRepositoryMigrationError) {
    return `Migration stopped during ${error.stage.replaceAll('-', ' ')}. The version 1 save was kept unchanged. ${error.message}`
  }
  return storageWriteMessage(error, 'migrated')
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
