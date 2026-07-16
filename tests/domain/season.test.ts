import { describe, expect, it } from 'vitest'
import {
  InvalidSeasonError,
  SEASON_PHASES,
  SEASON_STATUSES,
  createSeason,
  parseSeason,
  validateSeason,
} from '../../src/domain/season'
import {
  parseLeagueId,
  parseScheduleId,
  parseSeasonId,
} from '../../src/domain/ids'
import { parseLocalDate } from '../../src/domain/localDate'

const VALID_SEASON = {
  id: 'season_stone_01',
  leagueId: 'league_stone',
  seasonNumber: 1,
  startingYear: 2026,
  endingYear: 2027,
  displayLabel: '2026–27',
  rulesVersion: 1,
  currentDate: '2026-09-01',
  currentPhase: 'offseason',
  scheduleId: 'schedule_stone_01',
  status: 'planned',
} as const

describe('Season', () => {
  it('constructs an immutable season and derives its display label', () => {
    const season = createSeason({
      id: parseSeasonId(VALID_SEASON.id),
      leagueId: parseLeagueId(VALID_SEASON.leagueId),
      seasonNumber: VALID_SEASON.seasonNumber,
      startingYear: VALID_SEASON.startingYear,
      endingYear: VALID_SEASON.endingYear,
      rulesVersion: VALID_SEASON.rulesVersion,
      currentDate: parseLocalDate(VALID_SEASON.currentDate),
      currentPhase: VALID_SEASON.currentPhase,
      scheduleId: parseScheduleId(VALID_SEASON.scheduleId),
      status: VALID_SEASON.status,
    })

    expect(season).toEqual(VALID_SEASON)
    expect(Object.isFrozen(season)).toBe(true)
  })

  it('parses every supported broad phase and lifecycle status', () => {
    for (const currentPhase of SEASON_PHASES) {
      for (const status of SEASON_STATUSES) {
        expect(parseSeason({ ...VALID_SEASON, currentPhase, status })).toMatchObject({
          currentPhase,
          status,
        })
      }
    }
  })

  it('rejects an inconsistent stored display label', () => {
    const issues = validateSeason({ ...VALID_SEASON, displayLabel: 'Season One' })

    expect(issues).toContainEqual(
      expect.objectContaining({ code: 'season.display_label.mismatch' }),
    )
    expect(() =>
      parseSeason({ ...VALID_SEASON, displayLabel: 'Season One' }),
    ).toThrow(InvalidSeasonError)
  })

  it.each([
    ['id', 'Season Bad'],
    ['leagueId', 'LEAGUE_BAD'],
    ['seasonNumber', 0],
    ['seasonNumber', Number.NaN],
    ['startingYear', -1],
    ['endingYear', 10000],
    ['rulesVersion', 0],
    ['rulesVersion', 1.5],
    ['currentDate', '2026-02-30'],
    ['currentPhase', 'trade_deadline'],
    ['scheduleId', 'schedule-bad'],
    ['status', 'started'],
  ])('rejects invalid %s', (key, value) => {
    expect(validateSeason({ ...VALID_SEASON, [key]: value })).not.toHaveLength(0)
    expect(() => parseSeason({ ...VALID_SEASON, [key]: value })).toThrow(
      InvalidSeasonError,
    )
  })

  it('reports all detectable problems rather than stopping at the first', () => {
    const issues = validateSeason({
      ...VALID_SEASON,
      id: '',
      leagueId: '',
      seasonNumber: -1,
      startingYear: 2028,
      endingYear: 2027,
      displayLabel: '',
      currentDate: '2026-02-30',
      scheduleId: '',
    })

    expect(issues).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ code: 'season.id.invalid' }),
        expect.objectContaining({ code: 'season.league_id.invalid' }),
        expect.objectContaining({ code: 'season.number.invalid' }),
        expect.objectContaining({ code: 'season.year_order.invalid' }),
        expect.objectContaining({ code: 'season.current_date.invalid' }),
        expect.objectContaining({ code: 'season.schedule_id.invalid' }),
      ]),
    )
  })
})
