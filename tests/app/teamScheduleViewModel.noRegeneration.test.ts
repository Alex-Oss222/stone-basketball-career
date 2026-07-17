import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  createCalendarEntries,
} from '../../src/app/calendarViewModel'
import { createLeagueSeasonDomainFixture } from '../persistence/leagueSnapshot.fixture'

const domainFixture = createLeagueSeasonDomainFixture()
const inspectedTeamId = domainFixture.league.teams[1].id
const calendarEntries = createCalendarEntries({
  league: domainFixture.league,
  schedule: domainFixture.foundation.schedule,
  seasonCalendar: domainFixture.foundation.calendar,
  managedTeamId: domainFixture.managedTeamId,
})
const inspectedGame = domainFixture.foundation.schedule.games.find(
  (game) =>
    game.homeTeamId === inspectedTeamId ||
    game.awayTeamId === inspectedTeamId,
)

if (inspectedGame === undefined) {
  throw new Error('M2.6 fixture must contain an inspected-team game')
}

describe('Team Schedule and game-details no-regeneration architecture', () => {
  afterEach(() => {
    vi.doUnmock('../../src/app/commands/createSeasonFoundation')
    vi.doUnmock('../../src/generation/generateSchedule')
    vi.doUnmock('../../src/generation/generateLeague')
    vi.doUnmock('../../src/domain/schedule')
    vi.doUnmock('../../src/random/xoshiro128ss')
    vi.resetModules()
  })

  it('builds both read models and filters rows without generation or randomness', async () => {
    const foundationImport = vi.fn()
    const scheduleGeneratorImport = vi.fn()
    const leagueGeneratorImport = vi.fn()
    const opponentGeneratorImport = vi.fn()
    const randomSourceImport = vi.fn()

    vi.resetModules()
    vi.doMock('../../src/app/commands/createSeasonFoundation', () => {
      foundationImport()
      throw new Error('Team Schedule imported season creation')
    })
    vi.doMock('../../src/generation/generateSchedule', () => {
      scheduleGeneratorImport()
      throw new Error('Team Schedule imported schedule generation')
    })
    vi.doMock('../../src/generation/generateLeague', () => {
      leagueGeneratorImport()
      throw new Error('Team Schedule imported league generation')
    })
    vi.doMock('../../src/domain/schedule', () => {
      opponentGeneratorImport()
      throw new Error('Team Schedule imported opponent generation')
    })
    vi.doMock('../../src/random/xoshiro128ss', () => {
      randomSourceImport()
      throw new Error('Team Schedule imported seeded randomization')
    })

    const {
      createGameDetailsViewModel,
      createTeamScheduleViewModel,
      filterTeamScheduleRows,
    } = await import('../../src/app/teamScheduleViewModel')
    const teamSchedule = createTeamScheduleViewModel({
      league: domainFixture.league,
      schedule: domainFixture.foundation.schedule,
      calendarEntries,
      inspectedTeamId,
      managedTeamId: domainFixture.managedTeamId,
      currentDate: domainFixture.foundation.season.currentDate,
    })
    const details = createGameDetailsViewModel({
      league: domainFixture.league,
      schedule: domainFixture.foundation.schedule,
      calendarEntries,
      gameId: inspectedGame.id,
      perspectiveTeamId: inspectedTeamId,
      managedTeamId: domainFixture.managedTeamId,
      currentDate: domainFixture.foundation.season.currentDate,
    })
    const filtered = filterTeamScheduleRows(teamSchedule.rows, 'all')

    expect(teamSchedule).toBeDefined()
    expect(details).toBeDefined()
    expect(filtered).toHaveLength(teamSchedule.rows.length)
    expect(foundationImport).not.toHaveBeenCalled()
    expect(scheduleGeneratorImport).not.toHaveBeenCalled()
    expect(leagueGeneratorImport).not.toHaveBeenCalled()
    expect(opponentGeneratorImport).not.toHaveBeenCalled()
    expect(randomSourceImport).not.toHaveBeenCalled()
  })
})
