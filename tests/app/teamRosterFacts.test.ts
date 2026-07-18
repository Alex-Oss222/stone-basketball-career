import { describe, expect, it } from 'vitest'
import { createTeamRosterFacts } from '../../src/app/teamRosterFacts'
import { parseTeamId } from '../../src/domain/ids'
import { POSITIONS } from '../../src/domain/league'
import { generateLeague } from '../../src/generation/generateLeague'

const league = generateLeague('team-roster-facts-fixture')

describe('team roster facts', () => {
  it('derives one reusable roster projection for summary view models', () => {
    const team = league.teams[3]
    const expectedRoster = league.players.filter(
      (player) => player.teamId === team.id,
    )
    const facts = createTeamRosterFacts(league, team.id)

    expect(facts).not.toBeNull()
    expect(facts?.team).toBe(team)
    expect(facts?.roster).toEqual(expectedRoster)
    expect(facts?.averageRating).toBeGreaterThan(0)
    expect(
      POSITIONS.reduce(
        (total, position) =>
          total + (facts?.positionCounts[position] ?? 0),
        0,
      ),
    ).toBe(expectedRoster.length)
  })

  it('returns null when the team is outside the league', () => {
    expect(
      createTeamRosterFacts(
        league,
        parseTeamId('team_roster_facts_foreign'),
      ),
    ).toBeNull()
  })
})
