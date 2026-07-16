import { describe, expect, it } from 'vitest'
import {
  InvalidTeamSeasonError,
  TEAM_COMPETITIVE_STATUSES,
  parseTeamSeason,
  validateTeamSeason,
} from '../../src/domain/teamSeason'

const ACTIVE_TEAM_SEASON = {
  version: 1,
  seasonId: 'season_stone_01',
  teamId: 'team_stone_01',
  competitiveStatus: 'active',
  eliminationDate: null,
  teamOffseasonStartDate: null,
  postseasonSeed: null,
} as const

describe('TeamSeason', () => {
  it('supports each competitive status without adding records or statistics', () => {
    expect(TEAM_COMPETITIVE_STATUSES).toEqual([
      'active',
      'eliminated',
      'season_complete',
    ])

    const active = parseTeamSeason(ACTIVE_TEAM_SEASON)
    const eliminated = parseTeamSeason({
      ...ACTIVE_TEAM_SEASON,
      competitiveStatus: 'eliminated',
      eliminationDate: '2027-04-20',
      teamOffseasonStartDate: '2027-04-21',
      postseasonSeed: 8,
    })
    const completed = parseTeamSeason({
      ...ACTIVE_TEAM_SEASON,
      competitiveStatus: 'season_complete',
      teamOffseasonStartDate: '2027-06-20',
      postseasonSeed: 1,
    })

    expect(active.competitiveStatus).toBe('active')
    expect(eliminated.eliminationDate).toBe('2027-04-20')
    expect(completed.competitiveStatus).toBe('season_complete')
    expect(Object.isFrozen(active)).toBe(true)
  })

  it('keeps each team offseason date independent', () => {
    const first = parseTeamSeason({
      ...ACTIVE_TEAM_SEASON,
      competitiveStatus: 'eliminated',
      eliminationDate: '2027-04-20',
      teamOffseasonStartDate: '2027-04-21',
    })
    const second = parseTeamSeason({
      ...ACTIVE_TEAM_SEASON,
      teamId: 'team_stone_02',
      competitiveStatus: 'season_complete',
      teamOffseasonStartDate: '2027-06-20',
    })

    expect(first.teamOffseasonStartDate).toBe('2027-04-21')
    expect(second.teamOffseasonStartDate).toBe('2027-06-20')
  })

  it.each([
    ['version', 0],
    ['version', 2],
    ['version', 1.5],
    ['seasonId', 'Season Bad'],
    ['teamId', 'Team Bad'],
    ['competitiveStatus', 'champion'],
    ['eliminationDate', '2027-02-29'],
    ['teamOffseasonStartDate', '2027-13-01'],
    ['postseasonSeed', 0],
    ['postseasonSeed', 1.5],
    ['postseasonSeed', Number.NaN],
  ])('rejects invalid %s', (key, value) => {
    const candidate = { ...ACTIVE_TEAM_SEASON, [key]: value }

    expect(validateTeamSeason(candidate)).not.toHaveLength(0)
    expect(() => parseTeamSeason(candidate)).toThrow(InvalidTeamSeasonError)
  })

  it('rejects competitive-date contradictions and reversed dates', () => {
    expect(
      validateTeamSeason({
        ...ACTIVE_TEAM_SEASON,
        eliminationDate: '2027-04-20',
      }),
    ).toContainEqual(
      expect.objectContaining({ code: 'team_season.active_dates.invalid' }),
    )

    expect(
      validateTeamSeason({
        ...ACTIVE_TEAM_SEASON,
        competitiveStatus: 'eliminated',
        eliminationDate: '2027-04-20',
        teamOffseasonStartDate: '2027-04-19',
      }),
    ).toContainEqual(
      expect.objectContaining({ code: 'team_season.offseason_date.invalid' }),
    )
  })
})
