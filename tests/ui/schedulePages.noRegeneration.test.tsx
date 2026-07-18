import { readFileSync } from 'node:fs'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { LeagueSnapshot } from '../../src/persistence/leagueSnapshot'
import { createLeagueSnapshotFixture } from '../persistence/leagueSnapshot.fixture'
import {
  expectNoGenerationImports,
  installGenerationTripwires,
  removeGenerationTripwires,
} from '../helpers/noRegenerationTripwire'

const persistedSnapshot = JSON.parse(
  JSON.stringify(createLeagueSnapshotFixture()),
) as LeagueSnapshot

describe('read-only V2 season and schedule identity preservation', () => {
  afterEach(() => {
    removeGenerationTripwires()
  })

  it('restores schedule identities, ordering, and dates exactly as stored', async () => {
    const { createLeagueSnapshotRepository } = await import(
      '../../src/persistence/leagueSnapshotRepository'
    )
    const storage = {
      read: vi.fn(async () => ({
        present: true,
        value: structuredClone({
          leagueId: persistedSnapshot.league.id,
          snapshot: persistedSnapshot,
        }),
      })),
      transact: vi.fn(() => {
        throw new Error('Read-only restoration must not write storage')
      }),
    }
    const repository = createLeagueSnapshotRepository(storage)

    const result = await repository.restore()

    expect(result.kind).toBe('restored')
    if (result.kind !== 'restored') {
      throw new Error('Expected the persisted fixture to restore')
    }

    const restored = result.snapshot
    expect(restored.season.id).toBe(persistedSnapshot.season.id)
    expect(restored.season.scheduleId).toBe(
      persistedSnapshot.season.scheduleId,
    )
    expect(restored.leagueSchedule.id).toBe(
      persistedSnapshot.leagueSchedule.id,
    )
    expect(restored.leagueSchedule.seasonId).toBe(
      persistedSnapshot.leagueSchedule.seasonId,
    )
    expect(restored.leagueSchedule.gameDays.map(({ id }) => id)).toEqual(
      persistedSnapshot.leagueSchedule.gameDays.map(({ id }) => id),
    )
    expect(restored.leagueSchedule.games.map(({ id }) => id)).toEqual(
      persistedSnapshot.leagueSchedule.games.map(({ id }) => id),
    )
    expect(projectGameDays(restored)).toEqual(
      projectGameDays(persistedSnapshot),
    )
    expect(projectGames(restored)).toEqual(projectGames(persistedSnapshot))
    expect(restored.leagueSchedule.opponentRequirements).toEqual(
      persistedSnapshot.leagueSchedule.opponentRequirements,
    )
    expect(restored.managedTeamId).toBe(persistedSnapshot.managedTeamId)
    expect(restored.seasonCalendar).toEqual(
      persistedSnapshot.seasonCalendar,
    )
    expect(restored.teamSeasons).toEqual(persistedSnapshot.teamSeasons)
    expect(storage.read).toHaveBeenCalledOnce()
    expect(storage.transact).not.toHaveBeenCalled()
  })

  it('renders every schedule view without importing generation modules', async () => {
    const spies = installGenerationTripwires('Presentation')

    const { createElement } = await import('react')
    const { renderToStaticMarkup } = await import('react-dom/server')
    const {
      LeagueCalendarContent,
      LeagueScheduleOverviewContent,
      TeamScheduleContent,
    } = await import('../../src/ui/schedulePages')
    const { createLeaguePresentationBundle } = await import(
      '../../src/app/leagueSnapshotDomainAdapter'
    )
    const { HomeTodayContent } = await import('../../src/ui/homePage')
    const { AppHeader } = await import('../../src/ui/dashboardShell')

    const presentation = createLeaguePresentationBundle(persistedSnapshot)
    const teamScheduleMarkup = renderToStaticMarkup(
      createElement(TeamScheduleContent, { presentation }),
    )
    const calendarMarkup = renderToStaticMarkup(
      createElement(LeagueCalendarContent, { presentation }),
    )
    const overviewMarkup = renderToStaticMarkup(
      createElement(LeagueScheduleOverviewContent, {
        snapshot: persistedSnapshot,
      }),
    )
    const dashboardMarkup = renderToStaticMarkup(
      createElement(HomeTodayContent, {
        snapshot: persistedSnapshot,
        saveState: { label: 'Saved locally', state: 'saved' },
      }),
    )
    const controlledTeam = persistedSnapshot.league.teams.find(
      (team) => team.id === persistedSnapshot.managedTeamId,
    )
    if (controlledTeam === undefined) {
      throw new Error('Persisted fixture managed team is missing')
    }
    const headerMarkup = renderToStaticMarkup(
      createElement(AppHeader, {
        controlledTeam,
        saveState: 'saved',
        dashboardAction: {
          label: 'View Schedule',
          target: 'view-schedule',
        },
        progress: {
          seasonLabel: persistedSnapshot.season.displayLabel,
          currentDate: persistedSnapshot.season.currentDate,
          currentPhase: persistedSnapshot.season.currentPhase,
        },
        busy: false,
        onMainMenu: () => undefined,
        onAuthoritativeAction: () => undefined,
      }),
    )

    expect(teamScheduleMarkup).toContain('Inspected team schedule')
    expect(calendarMarkup).toContain('league calendar')
    expect(overviewMarkup).toContain(persistedSnapshot.season.displayLabel)
    expect(dashboardMarkup).toContain('Next Game')
    expect(headerMarkup).toContain(persistedSnapshot.season.displayLabel)
    expectNoGenerationImports(spies)
  })

  it('keeps Team Schedule hydration snapshot-memoized and preferences downstream', () => {
    const appSource = readFileSync(
      new URL('../../src/App.tsx', import.meta.url),
      'utf8',
    )
    const pageSource = readFileSync(
      new URL('../../src/ui/teamSchedulePage.tsx', import.meta.url),
      'utf8',
    )
    const dialogSource = readFileSync(
      new URL('../../src/ui/gameDetailsDialog.tsx', import.meta.url),
      'utf8',
    )

    expect(appSource).toMatch(
      /useMemo\([\s\S]*createLeaguePresentationBundle\(snapshot\)[\s\S]*\[snapshot\]/,
    )
    expect(pageSource).not.toMatch(
      /LeagueSnapshot|createLeaguePresentationBundle|createCalendarEntries/,
    )
    expect(pageSource).not.toMatch(
      /repository|IndexedDB|createSeasonFoundation|generateRegularSeasonSchedule|generateLeague|Math\.random|new Date/i,
    )
    expect(dialogSource).not.toMatch(
      /repository|LeagueSnapshot|generate|Math\.random|new Date/i,
    )
    expect(dialogSource).toContain('dialog.showModal()')
    expect(dialogSource).toContain('onCancel={(event) =>')
    expect(dialogSource).toContain('event.preventDefault()')
    expect(dialogSource).toContain('onRequestClose()')
    expect(dialogSource).toContain('returnTarget?.focus()')
  })
})

function projectGameDays(snapshot: LeagueSnapshot) {
  return snapshot.leagueSchedule.gameDays.map((gameDay) => ({
    id: gameDay.id,
    seasonId: gameDay.seasonId,
    sequenceNumber: gameDay.sequenceNumber,
    scheduledDate: gameDay.scheduledDate,
    gameIds: [...gameDay.gameIds],
  }))
}

function projectGames(snapshot: LeagueSnapshot) {
  return snapshot.leagueSchedule.games.map((game) => ({
    id: game.id,
    seasonId: game.seasonId,
    gameDayId: game.gameDayId,
    originalScheduledDate: game.originalScheduledDate,
    currentScheduledDate: game.currentScheduledDate,
    actualDate: game.actualDate,
  }))
}
