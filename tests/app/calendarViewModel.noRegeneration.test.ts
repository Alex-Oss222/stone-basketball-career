import { afterEach, describe, expect, it, vi } from 'vitest'
import { createLeagueSeasonDomainFixture } from '../persistence/leagueSnapshotV2.fixture'

const domainFixture = createLeagueSeasonDomainFixture()

describe('CalendarEntry no-regeneration architecture', () => {
  afterEach(() => {
    vi.doUnmock('../../src/app/commands/createSeasonFoundation')
    vi.doUnmock('../../src/generation/generateSchedule')
    vi.doUnmock('../../src/generation/generateLeague')
    vi.doUnmock('../../src/domain/schedule')
    vi.doUnmock('../../src/random/xoshiro128ss')
    vi.resetModules()
  })

  it('normalizes and selects entries without generation or seeded randomness', async () => {
    const foundationImport = vi.fn()
    const scheduleGeneratorImport = vi.fn()
    const leagueGeneratorImport = vi.fn()
    const opponentGeneratorImport = vi.fn()
    const randomSourceImport = vi.fn()

    vi.resetModules()
    vi.doMock('../../src/app/commands/createSeasonFoundation', () => {
      foundationImport()
      throw new Error('Calendar normalization imported season creation')
    })
    vi.doMock('../../src/generation/generateSchedule', () => {
      scheduleGeneratorImport()
      throw new Error('Calendar normalization imported schedule generation')
    })
    vi.doMock('../../src/generation/generateLeague', () => {
      leagueGeneratorImport()
      throw new Error('Calendar normalization imported league generation')
    })
    vi.doMock('../../src/domain/schedule', () => {
      opponentGeneratorImport()
      throw new Error('Calendar normalization imported opponent generation')
    })
    vi.doMock('../../src/random/xoshiro128ss', () => {
      randomSourceImport()
      throw new Error('Calendar normalization imported seeded randomization')
    })

    const {
      createCalendarEntries,
      getDatedCalendarEntries,
      groupCalendarEntriesByDate,
    } = await import('../../src/app/calendarViewModel')
    const entries = createCalendarEntries({
      league: domainFixture.league,
      schedule: domainFixture.foundation.schedule,
      seasonCalendar: domainFixture.foundation.calendar,
      managedTeamId: domainFixture.managedTeamId,
    })

    expect(entries.filter((entry) => entry.kind === 'game')).toHaveLength(112)
    expect(getDatedCalendarEntries(entries)).toHaveLength(entries.length)
    expect(groupCalendarEntriesByDate(entries)).not.toHaveLength(0)
    expect(foundationImport).not.toHaveBeenCalled()
    expect(scheduleGeneratorImport).not.toHaveBeenCalled()
    expect(leagueGeneratorImport).not.toHaveBeenCalled()
    expect(opponentGeneratorImport).not.toHaveBeenCalled()
    expect(randomSourceImport).not.toHaveBeenCalled()
  })
})
