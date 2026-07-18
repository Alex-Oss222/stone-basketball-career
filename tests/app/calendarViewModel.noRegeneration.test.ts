import { afterEach, describe, expect, it } from 'vitest'
import { createLeagueSeasonDomainFixture } from '../persistence/leagueSnapshot.fixture'
import {
  expectNoGenerationImports,
  installGenerationTripwires,
  removeGenerationTripwires,
} from '../helpers/noRegenerationTripwire'

const domainFixture = createLeagueSeasonDomainFixture()

describe('CalendarEntry no-regeneration architecture', () => {
  afterEach(() => {
    removeGenerationTripwires()
  })

  it('normalizes and selects entries without generation or seeded randomness', async () => {
    const spies = installGenerationTripwires('Calendar normalization')

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
    expectNoGenerationImports(spies)
  })
})
