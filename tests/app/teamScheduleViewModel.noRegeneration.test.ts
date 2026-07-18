import { afterEach, describe, expect, it } from 'vitest'
import {
  createCalendarEntries,
} from '../../src/app/calendarViewModel'
import { createLeagueSeasonDomainFixture } from '../persistence/leagueSnapshot.fixture'
import {
  expectNoGenerationImports,
  installGenerationTripwires,
  removeGenerationTripwires,
} from '../helpers/noRegenerationTripwire'

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
    removeGenerationTripwires()
  })

  it('builds both read models and filters rows without generation or randomness', async () => {
    const spies = installGenerationTripwires('Team Schedule')

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
    expectNoGenerationImports(spies)
  })
})
