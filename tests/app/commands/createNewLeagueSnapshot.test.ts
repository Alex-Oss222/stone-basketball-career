import { describe, expect, it, vi } from 'vitest'
import * as seasonFoundationModule from '../../../src/app/commands/createSeasonFoundation'
import {
  createNewLeagueSnapshot,
} from '../../../src/app/commands/createNewLeagueSnapshot'
import type { CreateNewLeagueSnapshotInput } from '../../../src/app/commands/createNewLeagueSnapshot'
import { parseLocalDate } from '../../../src/domain/localDate'
import { MILESTONE_1_REGULAR_SEASON_RULE_SET } from '../../../src/domain/schedule'
import {
  LEAGUE_SNAPSHOT_VERSION,
  parseLeagueSnapshot,
} from '../../../src/persistence/leagueSnapshot'

const INPUT = Object.freeze({
  rootSeed: 'new-league-v2-fixture',
  startingYear: 2026,
  regularSeasonStartDate: parseLocalDate('2026-10-06'),
  calendarDaySpacing: 3,
  scheduleSeed: 'new-league-v2-schedule',
}) satisfies CreateNewLeagueSnapshotInput

describe('createNewLeagueSnapshot', () => {
  it('creates one strict initial V2 snapshot directly from explicit inputs', () => {
    const snapshot = createNewLeagueSnapshot(INPUT)

    expect(snapshot).toMatchObject({
      snapshotVersion: LEAGUE_SNAPSHOT_VERSION,
      revision: 1,
      rootSeed: INPUT.rootSeed,
      managedTeamId: null,
      creationMetadata: {
        startingYear: INPUT.startingYear,
        regularSeasonStartDate: INPUT.regularSeasonStartDate,
        gameDaySpacing: INPUT.calendarDaySpacing,
        scheduleSeed: INPUT.scheduleSeed,
        scheduleRuleSetId: MILESTONE_1_REGULAR_SEASON_RULE_SET.id,
        scheduleRuleSetVersion:
          MILESTONE_1_REGULAR_SEASON_RULE_SET.version,
      },
    })
    expect(snapshot.leagueSchedule).toMatchObject({
      leagueId: snapshot.league.id,
      seasonId: snapshot.season.id,
      ruleSetId: MILESTONE_1_REGULAR_SEASON_RULE_SET.id,
      scheduleSeed: INPUT.scheduleSeed,
      calendarDaySpacing: INPUT.calendarDaySpacing,
    })
    expect(snapshot.season.scheduleId).toBe(snapshot.leagueSchedule.id)
    expect(snapshot.teamSeasons).toHaveLength(snapshot.league.teams.length)
    expect(parseLeagueSnapshot(snapshot)).toEqual(snapshot)
  })

  it('is deeply deterministic for identical explicit inputs', () => {
    expect(createNewLeagueSnapshot({ ...INPUT })).toEqual(
      createNewLeagueSnapshot({ ...INPUT }),
    )
  })

  it('coordinates exactly one season foundation for the snapshot', () => {
    const foundationSpy = vi.spyOn(
      seasonFoundationModule,
      'createSeasonFoundation',
    )

    createNewLeagueSnapshot(INPUT)

    expect(foundationSpy).toHaveBeenCalledOnce()
    foundationSpy.mockRestore()
  })

  it('normalizes the league seed only through its existing creation contract', () => {
    const snapshot = createNewLeagueSnapshot({
      ...INPUT,
      rootSeed: `  ${INPUT.rootSeed}  `,
    })

    expect(snapshot.rootSeed).toBe(INPUT.rootSeed)
    expect(snapshot.league).toEqual(createNewLeagueSnapshot(INPUT).league)
  })

  it.each([
    ['blank league seed', { rootSeed: '   ' }],
    ['malformed local date', { regularSeasonStartDate: '2026-02-30' }],
    ['date outside starting year', { regularSeasonStartDate: '2027-01-01' }],
    ['fractional starting year', { startingYear: 2026.5 }],
    ['unsupported ending year', { startingYear: 9999 }],
    ['zero spacing', { calendarDaySpacing: 0 }],
    ['negative spacing', { calendarDaySpacing: -1 }],
    ['fractional spacing', { calendarDaySpacing: 1.5 }],
    ['blank schedule seed', { scheduleSeed: '' }],
    ['padded schedule seed', { scheduleSeed: ' schedule-seed ' }],
    ['non-NFC schedule seed', { scheduleSeed: 'e\u0301' }],
  ])('rejects %s without mutating the input', (_name, overrides) => {
    const candidate = {
      ...INPUT,
      ...overrides,
    } as unknown as CreateNewLeagueSnapshotInput
    const before = structuredClone(candidate)

    expect(() => createNewLeagueSnapshot(candidate)).toThrow()
    expect(candidate).toEqual(before)
  })

  it('does not mutate a deeply frozen input or retain its object identity', () => {
    const input = deepFreeze({ ...INPUT })
    const snapshot = createNewLeagueSnapshot(input)

    expect(input).toEqual(INPUT)
    expect(snapshot.creationMetadata).not.toBe(input)
  })
})

function deepFreeze<Value>(value: Value): Value {
  if (value !== null && typeof value === 'object') {
    for (const nested of Object.values(value)) {
      deepFreeze(nested)
    }
    Object.freeze(value)
  }
  return value
}
