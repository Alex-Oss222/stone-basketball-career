import { readFileSync } from 'node:fs'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { LeagueSnapshotV2 } from '../../src/persistence/leagueSnapshotV2'
import { createLeagueSnapshotV2Fixture } from '../persistence/leagueSnapshotV2.fixture'

const persistedSnapshot = JSON.parse(
  JSON.stringify(createLeagueSnapshotV2Fixture()),
) as LeagueSnapshotV2

describe('read-only V2 season and schedule identity preservation', () => {
  afterEach(() => {
    vi.doUnmock('../../src/app/commands/createSeasonFoundation')
    vi.doUnmock('../../src/generation/generateLeague')
    vi.doUnmock('../../src/generation/generateSchedule')
    vi.doUnmock('../../src/domain/schedule')
    vi.doUnmock('../../src/random/xoshiro128ss')
    vi.resetModules()
  })

  it('restores schedule identities, ordering, and dates exactly as stored', async () => {
    const { createLeagueSnapshotRepository } = await import(
      '../../src/persistence/leagueSnapshotRepository'
    )
    const storage = {
      read: vi.fn(async () => ({
        v1: { present: false, value: undefined },
        v2: {
          present: true,
          value: structuredClone({
            leagueId: persistedSnapshot.league.id,
            snapshot: persistedSnapshot,
          }),
        },
      })),
      transact: vi.fn(() => {
        throw new Error('Read-only restoration must not write storage')
      }),
    }
    const repository = createLeagueSnapshotRepository(storage)

    const result = await repository.restore()

    expect(result.kind).toBe('restored-v2')
    if (result.kind !== 'restored-v2') {
      throw new Error('Expected the persisted V2 fixture to restore')
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
    const foundationImport = vi.fn()
    const leagueGeneratorImport = vi.fn()
    const scheduleGeneratorImport = vi.fn()
    const opponentGeneratorImport = vi.fn()
    const randomSourceImport = vi.fn()

    vi.resetModules()
    vi.doMock('../../src/app/commands/createSeasonFoundation', () => {
      foundationImport()
      throw new Error('Presentation imported createSeasonFoundation')
    })
    vi.doMock('../../src/generation/generateLeague', () => {
      leagueGeneratorImport()
      throw new Error('Presentation imported league generation')
    })
    vi.doMock('../../src/generation/generateSchedule', () => {
      scheduleGeneratorImport()
      throw new Error('Presentation imported schedule generation')
    })
    vi.doMock('../../src/domain/schedule', () => {
      opponentGeneratorImport()
      throw new Error('Presentation imported opponent generation')
    })
    vi.doMock('../../src/random/xoshiro128ss', () => {
      randomSourceImport()
      throw new Error('Presentation imported seeded randomization')
    })

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
    const { DashboardOverviewContent } = await import(
      '../../src/ui/dashboardPages'
    )
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
      createElement(DashboardOverviewContent, {
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
    expect(dashboardMarkup).toContain('Next scheduled game')
    expect(headerMarkup).toContain(persistedSnapshot.season.displayLabel)
    expect(foundationImport).not.toHaveBeenCalled()
    expect(leagueGeneratorImport).not.toHaveBeenCalled()
    expect(scheduleGeneratorImport).not.toHaveBeenCalled()
    expect(opponentGeneratorImport).not.toHaveBeenCalled()
    expect(randomSourceImport).not.toHaveBeenCalled()
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
      /LeagueSnapshotV2|createLeaguePresentationBundle|createCalendarEntries/,
    )
    expect(pageSource).not.toMatch(
      /repository|IndexedDB|createSeasonFoundation|generateRegularSeasonSchedule|generateLeague|Math\.random|new Date/i,
    )
    expect(dialogSource).not.toMatch(
      /repository|LeagueSnapshotV2|generate|Math\.random|new Date/i,
    )
    expect(dialogSource).toContain('dialog.showModal()')
    expect(dialogSource).toContain('onCancel={(event) =>')
    expect(dialogSource).toContain('event.preventDefault()')
    expect(dialogSource).toContain('onRequestClose()')
    expect(dialogSource).toContain('returnTarget?.focus()')
  })
})

function projectGameDays(snapshot: LeagueSnapshotV2) {
  return snapshot.leagueSchedule.gameDays.map((gameDay) => ({
    id: gameDay.id,
    seasonId: gameDay.seasonId,
    sequenceNumber: gameDay.sequenceNumber,
    scheduledDate: gameDay.scheduledDate,
    gameIds: [...gameDay.gameIds],
  }))
}

function projectGames(snapshot: LeagueSnapshotV2) {
  return snapshot.leagueSchedule.games.map((game) => ({
    id: game.id,
    seasonId: game.seasonId,
    gameDayId: game.gameDayId,
    originalScheduledDate: game.originalScheduledDate,
    currentScheduledDate: game.currentScheduledDate,
    actualDate: game.actualDate,
  }))
}
