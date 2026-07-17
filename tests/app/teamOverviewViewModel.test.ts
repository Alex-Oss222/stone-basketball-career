import { describe, expect, it } from 'vitest'
import { POSITIONS } from '../../src/domain/league'
import { createTeamOverviewSummary } from '../../src/app/teamOverviewViewModel'
import { createLeagueSnapshotFixture } from '../persistence/leagueSnapshot.fixture'

describe('team overview summary', () => {
  it('returns null without a managed team', () => {
    const snapshot = createLeagueSnapshotFixture()
    expect(
      createTeamOverviewSummary({
        league: snapshot.league,
        managedTeamId: null,
      }),
    ).toBeNull()
  })

  it('derives roster composition from real data only', () => {
    const snapshot = createLeagueSnapshotFixture()
    const managedTeamId = snapshot.managedTeamId
    expect(managedTeamId).not.toBeNull()

    const summary = createTeamOverviewSummary({
      league: snapshot.league,
      managedTeamId,
    })
    expect(summary).not.toBeNull()
    if (summary === null) {
      return
    }

    const roster = snapshot.league.players.filter(
      (player) => player.teamId === managedTeamId,
    )
    expect(summary.rosterSize).toBe(roster.length)
    expect(summary.openSpots).toBe(summary.rosterCapacity - summary.rosterSize)
    expect(summary.averageRating).toBeGreaterThan(0)

    // Every roster player is counted exactly once across the position split...
    const positionSum = POSITIONS.reduce(
      (sum, position) => sum + summary.positionCounts[position],
      0,
    )
    expect(positionSum).toBe(roster.length)
  })
})
