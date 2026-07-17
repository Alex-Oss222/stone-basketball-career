import { describe, expect, it } from 'vitest'
import { RATING_KEYS } from '../../src/domain/ratings'
import { generateLeague } from '../../src/generation/generateLeague'
import {
  createHomeHeaderSummary,
  deriveTeamAverageRating,
} from '../../src/app/homeViewModel'
import { formatTeamName } from '../../src/domain/league'

const league = generateLeague('home-view-model-fixture')

describe('home header summary', () => {
  it('derives only facts that exist today: identity, roster, stored ratings', () => {
    const team = league.teams[2]
    const roster = league.players.filter((player) => player.teamId === team.id)
    const summary = createHomeHeaderSummary({
      league,
      managedTeamId: team.id,
    })

    expect(summary).not.toBeNull()
    expect(summary?.teamName).toBe(formatTeamName(team))
    expect(summary?.abbreviation).toBe(team.abbreviation)
    expect(summary?.rosterSize).toBe(12)
    expect(summary?.rosterCapacity).toBe(12)

    const expectedAverage = Math.round(
      roster.reduce(
        (total, player) =>
          total + RATING_KEYS.reduce((sum, key) => sum + player.ratings[key], 0),
        0,
      ) /
        (roster.length * RATING_KEYS.length),
    )
    expect(summary?.averageRating).toBe(expectedAverage)
    expect(
      Object.values(summary?.positionCounts ?? {}).reduce(
        (total, count) => total + count,
        0,
      ),
    ).toBe(12)
  })

  /**
   * Moved from the deleted saved-league dashboard summary: the home view model
   * must expose no simulation-era keys. Those slots render "Coming later" in
   * the UI and become real in roadmap §10-§11 — never before.
   */
  it('exposes no record, wins, losses, streak, standings, or statistics keys', () => {
    const summary = createHomeHeaderSummary({
      league,
      managedTeamId: league.teams[0].id,
    })

    expect(Object.keys(summary ?? {})).not.toEqual(
      expect.arrayContaining([
        'record',
        'wins',
        'losses',
        'streak',
        'seed',
        'standings',
        'statistics',
      ]),
    )
  })

  it('derives nothing before a team is selected', () => {
    expect(createHomeHeaderSummary({ league, managedTeamId: null })).toBeNull()
  })
})

describe('team average rating', () => {
  it('is a transparent rounded mean over every stored rating, per team', () => {
    for (const team of league.teams) {
      const roster = league.players.filter(
        (player) => player.teamId === team.id,
      )
      const expected = Math.round(
        roster.reduce(
          (total, player) =>
            total +
            RATING_KEYS.reduce((sum, key) => sum + player.ratings[key], 0),
          0,
        ) /
          (roster.length * RATING_KEYS.length),
      )
      expect(deriveTeamAverageRating(league, team.id)).toBe(expected)
    }
  })

  it('matches the header summary for the managed team', () => {
    const team = league.teams[1]
    const summary = createHomeHeaderSummary({ league, managedTeamId: team.id })
    expect(summary?.averageRating).toBe(
      deriveTeamAverageRating(league, team.id),
    )
  })
})
