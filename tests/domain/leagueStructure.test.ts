import { describe, expect, it } from 'vitest'
import {
  ALIGNED_TEAM_COUNT,
  CONFERENCES,
  DIVISIONS,
  DIVISION_CONFERENCE,
  alignTeamIndex,
  isConference,
  isDivision,
} from '../../src/domain/leagueStructure'

describe('league structure', () => {
  it('aligns 30 teams into six divisions of five across two conferences', () => {
    expect(ALIGNED_TEAM_COUNT).toBe(30)

    const perDivision = new Map<string, number>()
    const perConference = new Map<string, number>()
    for (let index = 0; index < ALIGNED_TEAM_COUNT; index += 1) {
      const alignment = alignTeamIndex(index)
      expect(DIVISION_CONFERENCE[alignment.division]).toBe(alignment.conference)
      perDivision.set(
        alignment.division,
        (perDivision.get(alignment.division) ?? 0) + 1,
      )
      perConference.set(
        alignment.conference,
        (perConference.get(alignment.conference) ?? 0) + 1,
      )
    }

    expect(perDivision.size).toBe(DIVISIONS.length)
    for (const count of perDivision.values()) expect(count).toBe(5)
    expect(perConference.get('east')).toBe(15)
    expect(perConference.get('west')).toBe(15)
  })

  it('places consecutive indexes in the same division', () => {
    expect(alignTeamIndex(0)).toEqual({
      conference: 'east',
      division: 'atlantic',
    })
    expect(alignTeamIndex(4).division).toBe('atlantic')
    expect(alignTeamIndex(5).division).toBe('central')
    expect(alignTeamIndex(29)).toEqual({
      conference: 'west',
      division: 'southwest',
    })
  })

  it('validates guards and rejects out-of-range indexes', () => {
    expect(isConference('east')).toBe(true)
    expect(isConference('midwest')).toBe(false)
    expect(isDivision('pacific')).toBe(true)
    expect(isDivision('mountain')).toBe(false)
    expect(CONFERENCES).toHaveLength(2)
    expect(() => alignTeamIndex(30)).toThrow(RangeError)
    expect(() => alignTeamIndex(-1)).toThrow(RangeError)
  })
})
