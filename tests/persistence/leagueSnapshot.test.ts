import { describe, expect, expectTypeOf, it } from 'vitest'

import { RATING_KEYS } from '../../src/domain/ratings'
import {
  InvalidLeagueSnapshotError,
  LEAGUE_SNAPSHOT_VERSION,
  parseLeagueSnapshot,
} from '../../src/persistence/leagueSnapshot'
import type { LeagueSnapshot } from '../../src/persistence/leagueSnapshot'
import {
  createLeagueSnapshotFixture,
  createLegacyVersionSnapshotFixture,
  FIXTURE_CREATION_INPUTS,
  FIXTURE_MANAGED_TEAM_ID,
} from './leagueSnapshot.fixture'

const TOP_LEVEL_KEYS = [
  'kind',
  'snapshotVersion',
  'revision',
  'rootSeed',
  'managedTeamId',
  'league',
  'season',
  'seasonCalendar',
  'teamSeasons',
  'leagueSchedule',
  'creationMetadata',
] as const

const CREATION_METADATA_KEYS = [
  'startingYear',
  'regularSeasonStartDate',
  'gameDaySpacing',
  'scheduleSeed',
  'scheduleRuleSetId',
  'scheduleRuleSetVersion',
] as const

describe('LeagueSnapshot DTO contract', () => {
  it('uses the exact closed top-level and creation-metadata shapes', () => {
    const snapshot = createLeagueSnapshotFixture()

    expectTypeOf(snapshot).toEqualTypeOf<LeagueSnapshot>()
    expect(Object.keys(snapshot)).toEqual(TOP_LEVEL_KEYS)
    expect(Object.keys(snapshot.creationMetadata)).toEqual(
      CREATION_METADATA_KEYS,
    )
    expect(snapshot.snapshotVersion).toBe(LEAGUE_SNAPSHOT_VERSION)
    expect(snapshot.snapshotVersion).toBe(3)
    expect(snapshot.revision).toBe(1)
    expect(snapshot.creationMetadata).toMatchObject({
      startingYear: FIXTURE_CREATION_INPUTS.startingYear,
      regularSeasonStartDate:
        FIXTURE_CREATION_INPUTS.regularSeasonStartDate,
      gameDaySpacing: FIXTURE_CREATION_INPUTS.calendarDaySpacing,
      scheduleSeed: FIXTURE_CREATION_INPUTS.scheduleSeed,
      scheduleRuleSetId: snapshot.leagueSchedule.ruleSetId,
      scheduleRuleSetVersion: snapshot.season.rulesVersion,
    })
  })

  it('stores every allowed absence explicitly as null in the V2 DTO', () => {
    const snapshot = createLeagueSnapshotFixture(null)

    expect(snapshot.managedTeamId).toBeNull()
    expect(
      snapshot.seasonCalendar.events.every(
        ({ scope, teamId }) => scope !== 'league' || teamId === null,
      ),
    ).toBe(true)
    expect(
      snapshot.teamSeasons.every(
        ({ eliminationDate, teamOffseasonStartDate, postseasonSeed }) =>
          eliminationDate === null &&
          teamOffseasonStartDate === null &&
          postseasonSeed === null,
      ),
    ).toBe(true)
    expect(
      snapshot.leagueSchedule.games.every(
        ({ actualDate }) => actualDate === null,
      ),
    ).toBe(true)
  })

  it('restores both null and valid non-null managed-team selections', () => {
    expect(
      parseLeagueSnapshot(createLeagueSnapshotFixture(null))
        .managedTeamId,
    ).toBeNull()
    expect(
      parseLeagueSnapshot(createLeagueSnapshotFixture()).managedTeamId,
    ).toBe(FIXTURE_MANAGED_TEAM_ID)
  })

  it('accepts later positive safe-integer revisions without adding another revision field', () => {
    const input = mutableSnapshot()
    input.revision = 7

    const parsed = parseLeagueSnapshot(input)

    expect(parsed.revision).toBe(7)
    expect(Object.keys(parsed).filter((key) => /revision/i.test(key))).toEqual([
      'revision',
    ])
  })

  it.each([0, -1, 1.5, Number.NaN, Number.POSITIVE_INFINITY, -0])(
    'rejects invalid revision %#',
    (revision) => {
      const input = mutableSnapshot()
      input.revision = revision

      expectInvalid(input, '$.revision')
    },
  )

  it('rejects a record whose snapshotVersion is a past monotonic version', () => {
    expectInvalid(createLegacyVersionSnapshotFixture(2), '$.snapshotVersion')
  })
})

describe('LeagueSnapshot strict serialized-value parsing', () => {
  it.each(TOP_LEVEL_KEYS)(
    'rejects a missing top-level %s field',
    (key) => {
      const input = mutableSnapshot()
      delete input[key]

      expectInvalid(input, `$.${key}`)
    },
  )

  it('rejects additional top-level string and symbol properties', () => {
    const extra = mutableSnapshot()
    extra.unexpected = true
    expectInvalid(extra, '$.unexpected')

    const symbolExtra = mutableSnapshot()
    Reflect.set(symbolExtra, Symbol('unexpected'), true)
    expectInvalid(symbolExtra, '$')
  })

  it.each([
    ['season', (input: MutableRecord) => record(input.season)],
    [
      'season calendar',
      (input: MutableRecord) => record(input.seasonCalendar),
    ],
    ['calendar event', firstCalendarEvent],
    ['team season', firstTeamSeason],
    ['league schedule', leagueSchedule],
    ['opponent requirement', firstOpponentRequirement],
    ['game day', firstGameDay],
    ['scheduled game', firstGame],
    ['creation metadata', creationMetadata],
    ['league player', firstPlayer],
  ] as const)(
    'rejects additional properties on a %s record',
    (_name, select) => {
      const input = mutableSnapshot()
      select(input).unexpected = true

      expectInvalid(input)
    },
  )

  it('rejects missing fields in nested records', () => {
    const missingSeasonStatus = mutableSnapshot()
    delete record(missingSeasonStatus.season).status
    expectInvalid(missingSeasonStatus, '$.season.status')

    const missingEventDate = mutableSnapshot()
    delete firstCalendarEvent(missingEventDate).scheduledDate
    expectInvalid(
      missingEventDate,
      '$.seasonCalendar.events[0].scheduledDate',
    )

    const missingGameStatus = mutableSnapshot()
    delete firstGame(missingGameStatus).status
    expectInvalid(
      missingGameStatus,
      '$.leagueSchedule.games[0].status',
    )

    const missingMetadataSeed = mutableSnapshot()
    delete creationMetadata(missingMetadataSeed).scheduleSeed
    expectInvalid(
      missingMetadataSeed,
      '$.creationMetadata.scheduleSeed',
    )
  })

  it.each([
    ['league teams', '$.league.teams', leagueTeams],
    ['league players', '$.league.players', leaguePlayers],
    ['calendar events', '$.seasonCalendar.events', calendarEvents],
    ['team seasons', '$.teamSeasons', teamSeasons],
    [
      'opponent requirements',
      '$.leagueSchedule.opponentRequirements',
      opponentRequirements,
    ],
    ['game days', '$.leagueSchedule.gameDays', gameDays],
    ['game-day game IDs', '$.leagueSchedule.gameDays[0].gameIds', gameIds],
    ['scheduled games', '$.leagueSchedule.games', games],
  ] as const)(
    'rejects a sparse %s array',
    (_name, path, select) => {
      const input = mutableSnapshot()
      delete select(input)[0]

      expectInvalid(input, path)
    },
  )

  it.each([
    ['league teams', '$.league.teams', leagueTeams],
    ['calendar events', '$.seasonCalendar.events', calendarEvents],
    ['team seasons', '$.teamSeasons', teamSeasons],
    [
      'opponent requirements',
      '$.leagueSchedule.opponentRequirements',
      opponentRequirements,
    ],
    ['game days', '$.leagueSchedule.gameDays', gameDays],
    ['game-day game IDs', '$.leagueSchedule.gameDays[0].gameIds', gameIds],
    ['scheduled games', '$.leagueSchedule.games', games],
  ] as const)(
    'rejects custom string properties on the %s array',
    (_name, path, select) => {
      const input = mutableSnapshot()
      Reflect.set(select(input), 'custom', true)

      expectInvalid(input, path)
    },
  )

  it('rejects symbol properties on arrays', () => {
    const input = mutableSnapshot()
    Reflect.set(games(input), Symbol('custom'), true)

    expectInvalid(input, '$.leagueSchedule.games')
  })

  it('rejects accessors without invoking them', () => {
    const input = mutableSnapshot()
    let getterCalls = 0
    Object.defineProperty(input, 'rootSeed', {
      configurable: true,
      enumerable: true,
      get: () => {
        getterCalls += 1
        return 'must-not-be-read'
      },
    })

    expectInvalid(input, '$.rootSeed')
    expect(getterCalls).toBe(0)
  })

  it('rejects accessor array items without invoking them', () => {
    const input = mutableSnapshot()
    const scheduledGames = games(input)
    let getterCalls = 0
    Object.defineProperty(scheduledGames, '0', {
      configurable: true,
      enumerable: true,
      get: () => {
        getterCalls += 1
        return undefined
      },
    })

    expectInvalid(input, '$.leagueSchedule.games[0]')
    expect(getterCalls).toBe(0)
  })

  it.each([
    ['Date', new Date('2026-01-01T00:00:00Z')],
    ['Map', new Map<string, string>()],
    ['Set', new Set<string>()],
    ['class instance', new NonPlainRecord()],
  ])('rejects a non-plain %s object', (_name, value) => {
    const input = mutableSnapshot()
    input.season = value

    expectInvalid(input, '$.season')
  })

  it.each([
    ['undefined', undefined],
    ['function', () => true],
    ['symbol', Symbol('not-json')],
    ['bigint', 1n],
    ['NaN', Number.NaN],
    ['Infinity', Number.POSITIVE_INFINITY],
  ])('rejects a %s value that cannot round-trip through JSON', (_name, value) => {
    const input = mutableSnapshot()
    input.rootSeed = value

    expectInvalid(input, '$.rootSeed')
  })

  it('rejects circular records', () => {
    const input = mutableSnapshot()
    input.circular = input

    expectInvalid(input, '$.circular')
  })
})

describe('LeagueSnapshot restoration and cross-object validation', () => {
  it('survives a complete JSON round trip without changing authoritative data', () => {
    const snapshot = createLeagueSnapshotFixture()
    const serialized = JSON.stringify(snapshot)
    const parsed = parseLeagueSnapshot(
      JSON.parse(serialized) as unknown,
    )

    expect(parsed).toEqual(snapshot)
    expect(JSON.parse(JSON.stringify(parsed))).toEqual(JSON.parse(serialized))
    expect(parsed.leagueSchedule.games.map(({ id }) => id)).toEqual(
      snapshot.leagueSchedule.games.map(({ id }) => id),
    )
    expect(
      parsed.leagueSchedule.games.map(({ originalScheduledDate }) =>
        originalScheduledDate,
      ),
    ).toEqual(
      snapshot.leagueSchedule.games.map(({ originalScheduledDate }) =>
        originalScheduledDate,
      ),
    )
    expect(
      parsed.leagueSchedule.games.map(({ currentScheduledDate }) =>
        currentScheduledDate,
      ),
    ).toEqual(
      snapshot.leagueSchedule.games.map(({ currentScheduledDate }) =>
        currentScheduledDate,
      ),
    )
    expect(parsed.seasonCalendar.events).toEqual(
      snapshot.seasonCalendar.events,
    )
    expect(parsed.teamSeasons).toEqual(snapshot.teamSeasons)
  })

  it('preserves stored game order and lifecycle dates without regeneration', () => {
    const input = mutableSnapshot()
    const schedule = leagueSchedule(input)
    schedule.publicationStatus = 'in_progress'
    record(input.season).status = 'in_progress'

    const scheduledGames = games(input)
    const first = record(scheduledGames[0])
    first.status = 'completed'
    first.actualDate = first.currentScheduledDate
    const second = record(scheduledGames[1])
    second.status = 'postponed'
    second.currentScheduledDate = '2026-10-06'
    scheduledGames.reverse()
    const expectedOrder = scheduledGames.map((game) => record(game).id)

    const parsed = parseLeagueSnapshot(input)

    expect(parsed.leagueSchedule.games.map(({ id }) => id)).toEqual(
      expectedOrder,
    )
    expect(
      parsed.leagueSchedule.games.find(({ id }) => id === first.id),
    ).toMatchObject({
      originalScheduledDate: first.originalScheduledDate,
      currentScheduledDate: first.currentScheduledDate,
      actualDate: first.actualDate,
      status: 'completed',
    })
    expect(
      parsed.leagueSchedule.games.find(({ id }) => id === second.id),
    ).toMatchObject({
      originalScheduledDate: second.originalScheduledDate,
      currentScheduledDate: '2026-10-06',
      actualDate: null,
      status: 'postponed',
    })
  })

  it('returns a detached value and never mutates the supplied DTO', () => {
    const input = createLeagueSnapshotFixture()
    const before = structuredClone(input)
    const parsed = parseLeagueSnapshot(input)

    expect(input).toEqual(before)
    expect(parsed).not.toBe(input)
    expect(parsed.league).not.toBe(input.league)
    expect(parsed.league.teams).not.toBe(input.league.teams)
    expect(parsed.league.players).not.toBe(input.league.players)
    expect(parsed.seasonCalendar).not.toBe(input.seasonCalendar)
    expect(parsed.teamSeasons).not.toBe(input.teamSeasons)
    expect(parsed.leagueSchedule).not.toBe(input.leagueSchedule)
    expect(parsed.leagueSchedule.games).not.toBe(
      input.leagueSchedule.games,
    )
  })

  it('contains canonical numeric ratings and no stored letter grades', () => {
    const snapshot = parseLeagueSnapshot(
      createLeagueSnapshotFixture(),
    )

    expect(Object.keys(snapshot.league.players[0].ratings)).toEqual(
      RATING_KEYS,
    )
    expect(collectPropertyNames(snapshot)).not.toContain('grade')
    expect(collectPropertyNames(snapshot)).not.toContain('letterGrade')
  })

  it('rejects a foreign managed team', () => {
    const input = mutableSnapshot()
    input.managedTeamId = 'team_foreign_snapshot_v2'

    expectInvalid(input, '$.managedTeamId')
  })

  it.each([
    [
      'season identity',
      (input: MutableRecord) => {
        record(input.season).id = 'season_foreign_snapshot_v2'
      },
    ],
    [
      'season LeagueId',
      (input: MutableRecord) => {
        record(input.season).leagueId = 'league_foreign_snapshot_v2'
      },
    ],
    [
      'schedule LeagueId',
      (input: MutableRecord) => {
        leagueSchedule(input).leagueId = 'league_foreign_snapshot_v2'
      },
    ],
    [
      'schedule SeasonId',
      (input: MutableRecord) => {
        leagueSchedule(input).seasonId = 'season_foreign_snapshot_v2'
      },
    ],
    [
      'team-season SeasonId',
      (input: MutableRecord) => {
        firstTeamSeason(input).seasonId = 'season_foreign_snapshot_v2'
      },
    ],
    [
      'game-day SeasonId',
      (input: MutableRecord) => {
        firstGameDay(input).seasonId = 'season_foreign_snapshot_v2'
      },
    ],
    [
      'game SeasonId',
      (input: MutableRecord) => {
        firstGame(input).seasonId = 'season_foreign_snapshot_v2'
      },
    ],
    [
      'season ScheduleId',
      (input: MutableRecord) => {
        record(input.season).scheduleId = 'schedule_foreign_snapshot_v2'
      },
    ],
    [
      'calendar SeasonId',
      (input: MutableRecord) => {
        record(input.seasonCalendar).seasonId = 'season_foreign_snapshot_v2'
      },
    ],
    [
      'calendar-event SeasonId',
      (input: MutableRecord) => {
        firstCalendarEvent(input).seasonId = 'season_foreign_snapshot_v2'
      },
    ],
    [
      'game team reference',
      (input: MutableRecord) => {
        firstGame(input).homeTeamId = 'team_foreign_snapshot_v2'
      },
    ],
    [
      'game self-matchup',
      (input: MutableRecord) => {
        const game = firstGame(input)
        game.awayTeamId = game.homeTeamId
      },
    ],
    [
      'opponent requirement',
      (input: MutableRecord) => {
        firstOpponentRequirement(input).totalMeetings = 5
      },
    ],
  ] as const)(
    'rejects an inconsistent %s cross-reference',
    (_name, mutate) => {
      const input = mutableSnapshot()
      mutate(input)

      expectInvalid(input)
    },
  )

  it('rejects duplicate and missing team-season records', () => {
    const duplicate = mutableSnapshot()
    const duplicateTeamSeasons = teamSeasons(duplicate)
    duplicateTeamSeasons[duplicateTeamSeasons.length - 1] = structuredClone(
      duplicateTeamSeasons[0],
    )
    expectInvalid(duplicate)

    const missing = mutableSnapshot()
    teamSeasons(missing).pop()
    expectInvalid(missing)
  })

  it('rejects a foreign team-season reference', () => {
    const input = mutableSnapshot()
    firstTeamSeason(input).teamId = 'team_foreign_snapshot_v2'

    expectInvalid(input)
  })

  it('rejects a foreign team-scoped calendar event', () => {
    const input = mutableSnapshot()
    const event = firstCalendarEvent(input)
    event.scope = 'team'
    event.teamId = 'team_foreign_snapshot_v2'

    expectInvalid(input)
  })

  it('requires regular-season boundary events to remain league-scoped', () => {
    const input = mutableSnapshot()
    const opening = calendarEventByKind(input, 'regular_season_opening')
    opening.scope = 'team'
    opening.teamId = leagueTeams(input).map(record)[0].id

    expectInvalid(input)
  })

  it('allows unsupported future events only as undated pending TBA records', () => {
    const tba = mutableSnapshot()
    calendarEvents(tba).push({
      id: 'calendar_event_future_trade_deadline_v1',
      version: 1,
      seasonId: record(tba.season).id,
      kind: 'trade_deadline',
      scope: 'league',
      teamId: null,
      title: 'Future trade deadline',
      originalScheduledDate: null,
      scheduledDate: null,
      actualDate: null,
      dateStatus: 'tba',
      completionStatus: 'pending',
    })
    expect(parseLeagueSnapshot(tba).seasonCalendar.events).toHaveLength(3)

    const dated = structuredClone(tba)
    const future = record(calendarEvents(dated)[2])
    future.originalScheduledDate = '2027-02-01'
    future.scheduledDate = '2027-02-01'
    future.dateStatus = 'scheduled'
    expectInvalid(dated)
  })

  it('rejects a boundary actual date that is not supported by game results', () => {
    const input = mutableSnapshot()
    const opening = calendarEventByKind(input, 'regular_season_opening')
    opening.actualDate = opening.scheduledDate
    opening.dateStatus = 'completed'
    opening.completionStatus = 'completed'

    expectInvalid(input)
  })

  it('preserves an unknown conclusion while a non-cancelled game is postponed TBA', () => {
    const input = mutableSnapshot()
    const finalGame = record(games(input).at(-1))
    finalGame.status = 'postponed'
    finalGame.currentScheduledDate = null
    const conclusion = calendarEventByKind(
      input,
      'regular_season_conclusion',
    )
    conclusion.scheduledDate = null
    conclusion.dateStatus = 'postponed'

    const parsed = parseLeagueSnapshot(input)

    expect(
      parsed.seasonCalendar.events.find(
        ({ kind }) => kind === 'regular_season_conclusion',
      )?.scheduledDate,
    ).toBeNull()
  })

  it('does not let a cancelled game extend the current conclusion date', () => {
    const input = mutableSnapshot()
    const finalGame = record(games(input).at(-1))
    finalGame.status = 'cancelled'
    finalGame.currentScheduledDate = '2099-12-31'

    expect(parseLeagueSnapshot(input).leagueSchedule.games.at(-1)).toEqual(
      expect.objectContaining({
        status: 'cancelled',
        currentScheduledDate: '2099-12-31',
      }),
    )
  })

  it('rejects inconsistent regular-season opening and conclusion dates', () => {
    const badOpening = mutableSnapshot()
    const opening = calendarEventByKind(
      badOpening,
      'regular_season_opening',
    )
    opening.originalScheduledDate = '2026-10-06'
    opening.scheduledDate = '2026-10-06'
    expectInvalid(badOpening)

    const badConclusion = mutableSnapshot()
    const conclusion = calendarEventByKind(
      badConclusion,
      'regular_season_conclusion',
    )
    conclusion.originalScheduledDate = '2026-12-31'
    conclusion.scheduledDate = '2026-12-31'
    expectInvalid(badConclusion)
  })

  it.each([
    [
      'season-calendar identity',
      (input: MutableRecord) => {
        record(input.seasonCalendar).id =
          'season_calendar_foreign_snapshot_v2'
      },
    ],
    [
      'boundary-event identity',
      (input: MutableRecord) => {
        firstCalendarEvent(input).id = 'calendar_event_foreign_snapshot_v2'
      },
    ],
    [
      'team-season identity',
      (input: MutableRecord) => {
        firstTeamSeason(input).id = 'team_season_foreign_snapshot_v2'
      },
    ],
    [
      'schedule identity after a seed change',
      (input: MutableRecord) => {
        creationMetadata(input).scheduleSeed = 'changed-v2-schedule-seed'
        leagueSchedule(input).scheduleSeed = 'changed-v2-schedule-seed'
      },
    ],
  ] as const)('rejects an inconsistent %s', (_name, mutate) => {
    const input = mutableSnapshot()
    mutate(input)

    expectInvalid(input)
  })

  it.each([
    [
      'starting year',
      (input: MutableRecord) => {
        const metadata = creationMetadata(input)
        metadata.startingYear = 2027
        metadata.regularSeasonStartDate = '2027-10-05'
      },
    ],
    [
      'regular-season start date',
      (input: MutableRecord) => {
        creationMetadata(input).regularSeasonStartDate = '2026-10-06'
      },
    ],
    [
      'game-day spacing',
      (input: MutableRecord) => {
        creationMetadata(input).gameDaySpacing = 2
      },
    ],
    [
      'schedule seed',
      (input: MutableRecord) => {
        creationMetadata(input).scheduleSeed = 'another-v2-schedule-seed'
      },
    ],
  ] as const)(
    'rejects inconsistent creation metadata: %s',
    (_name, mutate) => {
      const input = mutableSnapshot()
      mutate(input)

      expectInvalid(input)
    },
  )

  it('rejects an unsupported registered rule-set version', () => {
    const input = mutableSnapshot()
    creationMetadata(input).scheduleRuleSetVersion = 2
    record(input.season).rulesVersion = 2

    const error = expectInvalid(input)

    expect(error.issues).toContainEqual(
      expect.objectContaining({
        code: expect.stringMatching(/rule_set/),
        path: '$.creationMetadata.scheduleRuleSetVersion',
      }),
    )
  })

  it('rejects an unknown rule-set identity', () => {
    const input = mutableSnapshot()
    creationMetadata(input).scheduleRuleSetId = 'schedule_rule_unknown_v1'
    leagueSchedule(input).ruleSetId = 'schedule_rule_unknown_v1'

    const error = expectInvalid(input)

    expect(error.issues).toContainEqual(
      expect.objectContaining({
        code: expect.stringMatching(/rule_set/),
        path: '$.creationMetadata.scheduleRuleSetId',
      }),
    )
  })

  it('rejects an unsupported schedule generation version', () => {
    const input = mutableSnapshot()
    leagueSchedule(input).generationVersion = 2

    const error = expectInvalid(input)

    expect(error.issues).toContainEqual(
      expect.objectContaining({
        code: expect.stringMatching(/generation_version/),
        path: '$.leagueSchedule.generationVersion',
      }),
    )
  })
})

class NonPlainRecord {
  readonly value = true
}

type MutableRecord = Record<string, unknown>

function mutableSnapshot(): MutableRecord {
  return structuredClone(
    createLeagueSnapshotFixture(),
  ) as unknown as MutableRecord
}

function record(value: unknown): MutableRecord {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    throw new TypeError('Test fixture value is not a record')
  }
  return value as MutableRecord
}

function array(value: unknown): unknown[] {
  if (!Array.isArray(value)) {
    throw new TypeError('Test fixture value is not an array')
  }
  return value
}

function league(input: MutableRecord): MutableRecord {
  return record(input.league)
}

function leagueTeams(input: MutableRecord): unknown[] {
  return array(league(input).teams)
}

function leaguePlayers(input: MutableRecord): unknown[] {
  return array(league(input).players)
}

function firstPlayer(input: MutableRecord): MutableRecord {
  return record(leaguePlayers(input)[0])
}

function calendarEvents(input: MutableRecord): unknown[] {
  return array(record(input.seasonCalendar).events)
}

function firstCalendarEvent(input: MutableRecord): MutableRecord {
  return record(calendarEvents(input)[0])
}

function calendarEventByKind(
  input: MutableRecord,
  kind: string,
): MutableRecord {
  const event = calendarEvents(input).find(
    (candidate) => record(candidate).kind === kind,
  )
  if (event === undefined) {
    throw new TypeError(`Missing fixture calendar event ${kind}`)
  }
  return record(event)
}

function teamSeasons(input: MutableRecord): unknown[] {
  return array(input.teamSeasons)
}

function firstTeamSeason(input: MutableRecord): MutableRecord {
  return record(teamSeasons(input)[0])
}

function leagueSchedule(input: MutableRecord): MutableRecord {
  return record(input.leagueSchedule)
}

function opponentRequirements(input: MutableRecord): unknown[] {
  return array(leagueSchedule(input).opponentRequirements)
}

function firstOpponentRequirement(input: MutableRecord): MutableRecord {
  return record(opponentRequirements(input)[0])
}

function gameDays(input: MutableRecord): unknown[] {
  return array(leagueSchedule(input).gameDays)
}

function firstGameDay(input: MutableRecord): MutableRecord {
  return record(gameDays(input)[0])
}

function gameIds(input: MutableRecord): unknown[] {
  return array(firstGameDay(input).gameIds)
}

function games(input: MutableRecord): unknown[] {
  return array(leagueSchedule(input).games)
}

function firstGame(input: MutableRecord): MutableRecord {
  return record(games(input)[0])
}

function creationMetadata(input: MutableRecord): MutableRecord {
  return record(input.creationMetadata)
}

function expectInvalid(
  value: unknown,
  expectedPath?: string,
): InvalidLeagueSnapshotError {
  try {
    parseLeagueSnapshot(value)
  } catch (error) {
    expect(error).toBeInstanceOf(InvalidLeagueSnapshotError)
    const invalidError = error as InvalidLeagueSnapshotError
    if (expectedPath !== undefined) {
      expect(invalidError.path).toBe(expectedPath)
    }
    expect(invalidError.issues.length).toBeGreaterThan(0)
    return invalidError
  }

  throw new Error('Expected LeagueSnapshot parsing to fail')
}

function collectPropertyNames(value: unknown): readonly string[] {
  if (Array.isArray(value)) {
    return value.flatMap(collectPropertyNames)
  }
  if (value === null || typeof value !== 'object') {
    return []
  }
  return Object.entries(value).flatMap(([key, nestedValue]) => [
    key,
    ...collectPropertyNames(nestedValue),
  ])
}
