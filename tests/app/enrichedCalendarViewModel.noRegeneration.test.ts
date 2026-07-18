import { afterEach, describe, expect, it } from 'vitest'
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
import {
  expectNoGenerationImports,
  installGenerationTripwires,
  removeGenerationTripwires,
} from '../helpers/noRegenerationTripwire'

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
    removeGenerationTripwires()
  })

  it('enriches normalized entries without generation or seeded randomness', async () => {
    const spies = installGenerationTripwires('Calendar enrichment')

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
    expectNoGenerationImports(spies)
  })
})
