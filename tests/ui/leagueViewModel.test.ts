import { describe, expect, it } from 'vitest'
import {
  DETAILED_CATEGORY_DEFINITIONS,
  DETAILED_CATEGORY_KEYS,
  SUB_RATING_KEYS,
  deriveCategoryScore,
  parseDetailedPlayerRatings,
} from '../../src/domain/detailedRatings'
import type { SubRatingKey } from '../../src/domain/detailedRatings'
import { ratingToGrade } from '../../src/domain/ratings'
import { generateLeague } from '../../src/generation/generateLeague'
import {
  createRatingDisplayRows,
  formatPlayerName,
  formatTeamName,
  getTeamRoster,
} from '../../src/ui/leagueViewModel'

function makeRatings(value: number) {
  return parseDetailedPlayerRatings(
    Object.fromEntries(
      SUB_RATING_KEYS.map((key) => [key, value]),
    ) as Record<SubRatingKey, number>,
  )
}

describe('league roster view-model helpers', () => {
  it('derives one ordered category row per registry entry', () => {
    const ratings = makeRatings(72)
    const rows = createRatingDisplayRows(ratings)

    expect(rows.map((row) => row.key)).toEqual([...DETAILED_CATEGORY_KEYS])
    expect(rows).toHaveLength(26)
    for (const [index, row] of rows.entries()) {
      const definition = DETAILED_CATEGORY_DEFINITIONS[index]
      expect(row.label).toBe(definition.label)
      expect(row.group).toBe(definition.group)
      expect(row.value).toBe(72)
      expect(row.grade).toBe('B-')
    }
  })

  it('rounds the display value but grades from the unrounded score', () => {
    const ratings = parseDetailedPlayerRatings({
      ...makeRatings(50),
      freeThrowAccuracy: 90,
      freeThrowConsistency: 89,
    })
    const row = createRatingDisplayRows(ratings).find(
      (candidate) => candidate.key === 'freeThrowShooting',
    )

    // Score is 89.85: displays as 90, but grades as A- from the unrounded value.
    expect(row?.value).toBe(90)
    expect(row?.grade).toBe('A-')
    expect(row?.grade).toBe(
      ratingToGrade(deriveCategoryScore(ratings, 'freeThrowShooting')),
    )
  })

  it('memoizes the display rows per ratings reference', () => {
    const ratings = makeRatings(63)
    expect(createRatingDisplayRows(ratings)).toBe(
      createRatingDisplayRows(ratings),
    )
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
