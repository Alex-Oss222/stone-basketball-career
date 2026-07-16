import { describe, expect, it, vi } from 'vitest'
import * as seasonFoundationModule from '../../../src/app/commands/createSeasonFoundation'
import {
  createNewLeagueSnapshotV2,
} from '../../../src/app/commands/createNewLeagueSnapshotV2'
import type { CreateNewLeagueSnapshotV2Input } from '../../../src/app/commands/createNewLeagueSnapshotV2'
import { parseLocalDate } from '../../../src/domain/localDate'
import { MILESTONE_1_REGULAR_SEASON_RULE_SET } from '../../../src/domain/schedule'
import {
  LEAGUE_SNAPSHOT_V2_VERSION,
  parseLeagueSnapshotV2,
} from '../../../src/persistence/leagueSnapshotV2'
import * as leagueSnapshotV1Module from '../../../src/persistence/leagueSnapshot'

const INPUT = Object.freeze({
  rootSeed: 'new-league-v2-fixture',
  startingYear: 2026,
  regularSeasonStartDate: parseLocalDate('2026-10-06'),
  calendarDaySpacing: 3,
  scheduleSeed: 'new-league-v2-schedule',
}) satisfies CreateNewLeagueSnapshotV2Input

describe('createNewLeagueSnapshotV2', () => {
  it('creates one strict initial V2 snapshot directly from explicit inputs', () => {
    const snapshot = createNewLeagueSnapshotV2(INPUT)

    expect(snapshot).toMatchObject({
      snapshotVersion: LEAGUE_SNAPSHOT_V2_VERSION,
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
    expect(parseLeagueSnapshotV2(snapshot)).toEqual(snapshot)
  })

  it('is deeply deterministic for identical explicit inputs', () => {
    expect(createNewLeagueSnapshotV2({ ...INPUT })).toEqual(
      createNewLeagueSnapshotV2({ ...INPUT }),
    )
  })

  it('coordinates one season foundation without constructing an intermediate V1 snapshot', () => {
    const foundationSpy = vi.spyOn(
      seasonFoundationModule,
      'createSeasonFoundation',
    )
    const v1CreationSpy = vi.spyOn(
      leagueSnapshotV1Module,
      'createLeagueSnapshot',
    )

    createNewLeagueSnapshotV2(INPUT)

    expect(foundationSpy).toHaveBeenCalledOnce()
    expect(v1CreationSpy).not.toHaveBeenCalled()
    foundationSpy.mockRestore()
    v1CreationSpy.mockRestore()
  })

  it('normalizes the league seed only through its existing creation contract', () => {
    const snapshot = createNewLeagueSnapshotV2({
      ...INPUT,
      rootSeed: `  ${INPUT.rootSeed}  `,
    })

    expect(snapshot.rootSeed).toBe(INPUT.rootSeed)
    expect(snapshot.league).toEqual(createNewLeagueSnapshotV2(INPUT).league)
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
    } as unknown as CreateNewLeagueSnapshotV2Input
    const before = structuredClone(candidate)

    expect(() => createNewLeagueSnapshotV2(candidate)).toThrow()
    expect(candidate).toEqual(before)
  })

  it('does not mutate a deeply frozen input or retain its object identity', () => {
    const input = deepFreeze({ ...INPUT })
    const snapshot = createNewLeagueSnapshotV2(input)

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
