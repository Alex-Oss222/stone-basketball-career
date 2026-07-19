import { describe, expect, it } from 'vitest'
import { generateLeague } from '../../src/generation/generateLeague'
import { POSITIONS } from '../../src/domain/league'
import {
  deriveDepthChart,
  derivePositionCoverage,
  isEligibleAt,
  reorderDepth,
} from '../../src/app/depthRolesViewModel'

const league = generateLeague('depth-roles-seed')
const team = league.teams[0]
const roster = league.players.filter((player) => player.teamId === team.id)

describe('deriveDepthChart', () => {
  const chart = deriveDepthChart(roster)

  it('lists exactly the naturally-eligible players at each position', () => {
    for (const position of POSITIONS) {
      const eligible = roster
        .filter((player) => isEligibleAt(player, position))
        .map((player) => player.id)
      expect([...chart[position]].sort()).toEqual([...eligible].sort())
    }
  })

  it('places every player in at least one position', () => {
    const placed = new Set(POSITIONS.flatMap((position) => chart[position]))
    for (const player of roster) {
      expect(placed.has(player.id)).toBe(true)
    }
  })
})

describe('reorderDepth', () => {
  it('moves a player to a new depth index within a position', () => {
    const chart = deriveDepthChart(roster)
    const pgList = chart.PG
    if (pgList.length < 2) {
      return
    }
    const mover = pgList[pgList.length - 1]
    const next = reorderDepth(chart, 'PG', mover, 0)
    expect(next.PG[0]).toBe(mover)
    expect([...next.PG].sort()).toEqual([...pgList].sort())
  })
})

describe('derivePositionCoverage', () => {
  it('classifies each of the five positions exactly once', () => {
    const coverage = derivePositionCoverage(deriveDepthChart(roster))
    expect(coverage.strong + coverage.average + coverage.weak).toBe(
      POSITIONS.length,
    )
  })
})
