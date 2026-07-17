import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  buildLeagueYearMonthGrids,
} from '../../src/app/calendarMonthGrid'
import {
  createCalendarEntries,
} from '../../src/app/calendarViewModel'
import {
  createLeagueYearDisplayRange,
} from '../../src/app/leagueYearDisplayRange'
import { createLeagueSeasonDomainFixture } from '../persistence/leagueSnapshot.fixture'

const domainFixture = createLeagueSeasonDomainFixture()
const range = createLeagueYearDisplayRange(domainFixture.foundation.season)
const monthGrids = buildLeagueYearMonthGrids(range)
const entries = createCalendarEntries({
  league: domainFixture.league,
  schedule: domainFixture.foundation.schedule,
  seasonCalendar: domainFixture.foundation.calendar,
  managedTeamId: domainFixture.managedTeamId,
})

describe('enriched calendar no-regeneration architecture', () => {
  afterEach(() => {
    vi.doUnmock('../../src/app/commands/createSeasonFoundation')
    vi.doUnmock('../../src/generation/generateSchedule')
    vi.doUnmock('../../src/generation/generateLeague')
    vi.doUnmock('../../src/domain/schedule')
    vi.doUnmock('../../src/random/xoshiro128ss')
    vi.resetModules()
  })

  it('enriches normalized entries without generation or seeded randomness', async () => {
    const foundationImport = vi.fn()
    const scheduleGeneratorImport = vi.fn()
    const leagueGeneratorImport = vi.fn()
    const opponentGeneratorImport = vi.fn()
    const randomSourceImport = vi.fn()

    vi.resetModules()
    vi.doMock('../../src/app/commands/createSeasonFoundation', () => {
      foundationImport()
      throw new Error('Calendar enrichment imported season creation')
    })
    vi.doMock('../../src/generation/generateSchedule', () => {
      scheduleGeneratorImport()
      throw new Error('Calendar enrichment imported schedule generation')
    })
    vi.doMock('../../src/generation/generateLeague', () => {
      leagueGeneratorImport()
      throw new Error('Calendar enrichment imported league generation')
    })
    vi.doMock('../../src/domain/schedule', () => {
      opponentGeneratorImport()
      throw new Error('Calendar enrichment imported opponent generation')
    })
    vi.doMock('../../src/random/xoshiro128ss', () => {
      randomSourceImport()
      throw new Error('Calendar enrichment imported seeded randomization')
    })

    const { createLeagueYearCalendarModel } = await import(
      '../../src/app/enrichedCalendarViewModel'
    )
    const model = createLeagueYearCalendarModel({
      range,
      monthGrids,
      entries,
      currentDate: domainFixture.foundation.season.currentDate,
      selectedDate: null,
      scope: 'all_teams',
      managedTeamId: domainFixture.managedTeamId,
      maxVisibleEntriesPerDay: 3,
    })

    expect(model.months).toHaveLength(12)
    expect(model.totalEntryCount).toBe(114)
    expect(foundationImport).not.toHaveBeenCalled()
    expect(scheduleGeneratorImport).not.toHaveBeenCalled()
    expect(leagueGeneratorImport).not.toHaveBeenCalled()
    expect(opponentGeneratorImport).not.toHaveBeenCalled()
    expect(randomSourceImport).not.toHaveBeenCalled()
  })
})
