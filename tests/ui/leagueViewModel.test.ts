import { describe, expect, it } from 'vitest'
import { RATING_KEYS, parsePlayerRatings, ratingToGrade } from '../../src/domain/ratings'
import { generateLeague } from '../../src/generation/generateLeague'
import {
  RATING_LABELS,
  createRatingDisplayRows,
  formatPlayerName,
  formatTeamName,
  getTeamRoster,
} from '../../src/ui/leagueViewModel'

describe('league roster view-model helpers', () => {
  it('derives one ordered numeric and letter-grade row per canonical rating', () => {
    const ratings = parsePlayerRatings(
      Object.fromEntries(
        RATING_KEYS.map((key, index) => [key, Math.min(index * 7, 100)]),
      ),
    )

    const rows = createRatingDisplayRows(ratings)

    expect(rows.map((row) => row.key)).toEqual(RATING_KEYS)
    expect(rows).toHaveLength(16)
    for (const row of rows) {
      expect(row.label).toBe(RATING_LABELS[row.key])
      expect(row.value).toBe(ratings[row.key])
      expect(row.grade).toBe(ratingToGrade(row.value))
    }
    expect(Object.keys(ratings)).not.toContain('grade')
  })

  it('formats the labels that cannot be inferred safely from camel case', () => {
    expect(RATING_LABELS.midRangeShooting).toBe('Mid-range shooting')
    expect(RATING_LABELS.threePointShooting).toBe('Three-point shooting')
    expect(RATING_LABELS.basketballIQ).toBe('Basketball IQ')
  })

  it('selects only the twelve players owned by a team', () => {
    const league = generateLeague('roster-view-model')
    const team = league.teams[0]
    const roster = getTeamRoster(league, team.id)

    expect(roster).toHaveLength(12)
    expect(roster.every((player) => player.teamId === team.id)).toBe(true)
    expect(formatTeamName(team)).toBe(`${team.city} ${team.nickname}`)
    expect(formatPlayerName(roster[0])).toBe(
      `${roster[0].firstName} ${roster[0].lastName}`,
    )
  })
})
