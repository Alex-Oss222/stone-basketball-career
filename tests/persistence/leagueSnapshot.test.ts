import { describe, expect, expectTypeOf, it } from 'vitest'
import { parseTeamId } from '../../src/domain/ids'
import type { League, Player, Team } from '../../src/domain/league'
import { RATING_KEYS } from '../../src/domain/ratings'
import { generateLeague } from '../../src/generation/generateLeague'
import {
  InvalidLeagueSnapshotError,
  LEAGUE_SNAPSHOT_KIND,
  LEAGUE_SNAPSHOT_VERSION,
  createLeagueSnapshot,
  parseLeagueSnapshot,
} from '../../src/persistence/leagueSnapshot'
import type { LeagueSnapshotV1 } from '../../src/persistence/leagueSnapshot'

const ROOT_SEED = 'snapshot-codec-fixture'
const league = generateLeague(ROOT_SEED)
const snapshot = createLeagueSnapshot(ROOT_SEED, league, league.teams[0].id)

describe('league snapshot V1 creation and parsing', () => {
  it('exports and returns the exact V1 contract', () => {
    expect(LEAGUE_SNAPSHOT_KIND).toBe(
      'stone-basketball-gm-league-snapshot',
    )
    expect(LEAGUE_SNAPSHOT_VERSION).toBe(1)
    expectTypeOf(snapshot).toEqualTypeOf<LeagueSnapshotV1>()
    expect(Object.keys(snapshot)).toEqual([
      'kind',
      'snapshotVersion',
      'rootSeed',
      'league',
      'managedTeamId',
    ])
  })

  it('normalizes the seed when creating a detached snapshot', () => {
    const created = createLeagueSnapshot(
      '  snapshot-codec-fixture  ',
      league,
      null,
    )

    expect(created.rootSeed).toBe(ROOT_SEED)
    expect(created.managedTeamId).toBeNull()
    expect(created).not.toBe(snapshot)
    expect(created.league).not.toBe(league)
    expect(created.league.teams).not.toBe(league.teams)
    expect(created.league.players).not.toBe(league.players)
    expect(created.league).toEqual(league)
  })

  it('parses a JSON round trip without regenerating or changing stored data', () => {
    const input = JSON.parse(JSON.stringify(snapshot)) as unknown
    const parsed = parseLeagueSnapshot(input)

    expect(parsed).toEqual(snapshot)
    expect(parsed).not.toBe(input)
    expect(parsed.league).not.toBe(
      (input as { readonly league: unknown }).league,
    )
    expect(parsed.league.players).toHaveLength(96)
  })

  it('accepts no managed team before team selection', () => {
    const input = cloneSnapshot()
    input.managedTeamId = null

    expect(parseLeagueSnapshot(input).managedTeamId).toBeNull()
  })

  it.each([null, [], 'snapshot', 1])('rejects non-record input %#', (input) => {
    expectInvalid(input, '$')
  })
})

describe('strict snapshot shape', () => {
  it.each([
    'kind',
    'snapshotVersion',
    'rootSeed',
    'league',
    'managedTeamId',
  ])('rejects a missing top-level %s field', (key) => {
    const input = cloneSnapshot()
    delete input[key]

    expectInvalid(input, `$.${key}`)
  })

  it('rejects additional top-level string and symbol fields', () => {
    const extra = cloneSnapshot()
    extra.unexpected = true
    expectInvalid(extra, '$.unexpected')

    const symbolExtra = cloneSnapshot()
    Reflect.set(symbolExtra, Symbol('unexpected'), true)
    expectInvalid(symbolExtra, '$')
  })

  it.each([
    {
      name: 'league',
      target: (input: MutableRecord) => record(input.league),
    },
    {
      name: 'team',
      target: (input: MutableRecord) => firstTeam(input),
    },
    {
      name: 'team colors',
      target: (input: MutableRecord) => record(firstTeam(input).colors),
    },
    {
      name: 'team mark',
      target: (input: MutableRecord) => record(firstTeam(input).mark),
    },
    {
      name: 'player',
      target: (input: MutableRecord) => firstPlayer(input),
    },
    {
      name: 'player tendencies',
      target: (input: MutableRecord) => record(firstPlayer(input).tendencies),
    },
  ])('rejects additional fields on $name records', ({ target }) => {
    const input = cloneSnapshot()
    target(input).unexpected = true

    expectInvalid(input)
  })

  it('rejects missing fields in nested records', () => {
    const missingTeamCity = cloneSnapshot()
    delete firstTeam(missingTeamCity).city
    expectInvalid(missingTeamCity, '$.league.teams[0].city')

    const missingPlayerAge = cloneSnapshot()
    delete firstPlayer(missingPlayerAge).age
    expectInvalid(missingPlayerAge, '$.league.players[0].age')

    const missingTendency = cloneSnapshot()
    delete record(firstPlayer(missingTendency).tendencies).usage
    expectInvalid(missingTendency, '$.league.players[0].tendencies.usage')
  })

  it('rejects accessors and non-plain record instances', () => {
    const accessor = cloneSnapshot()
    Object.defineProperty(accessor, 'rootSeed', {
      configurable: true,
      enumerable: true,
      get: () => ROOT_SEED,
    })
    expectInvalid(accessor, '$.rootSeed')

    const classLike = Object.assign(Object.create({}), cloneSnapshot())
    expectInvalid(classLike, '$')
  })

  it('rejects sparse and custom-property arrays', () => {
    const sparse = cloneSnapshot()
    delete array(record(sparse.league).teams)[0]
    expectInvalid(sparse, '$.league.teams')

    const custom = cloneSnapshot()
    const players = array(record(custom.league).players)
    Reflect.set(players, 'custom', true)
    expectInvalid(custom, '$.league.players')
  })
})

describe('snapshot discriminators and root seed', () => {
  it.each([
    ['kind', 'another-snapshot-kind'],
    ['snapshotVersion', 2],
    ['snapshotVersion', '1'],
  ])('rejects invalid %s value %#', (key, value) => {
    const input = cloneSnapshot()
    input[key] = value

    expectInvalid(input, `$.${key}`)
  })

  it.each(['', '   ', ` ${ROOT_SEED}`, `${ROOT_SEED} `, 'e\u0301'])(
    'rejects non-canonical stored root seed %# without correcting it',
    (rootSeed) => {
      const input = cloneSnapshot()
      input.rootSeed = rootSeed

      expectInvalid(input, '$.rootSeed')
      expect(input.rootSeed).toBe(rootSeed)
    },
  )

  it('normalizes Unicode when creating a snapshot', () => {
    expect(createLeagueSnapshot('  e\u0301  ', league, null).rootSeed).toBe('é')
  })
})

describe('entity reconstruction and whole-league validation', () => {
  it('rejects invalid IDs instead of branding untrusted strings', () => {
    const badLeagueId = cloneSnapshot()
    record(badLeagueId.league).id = 'League_Invalid'
    expectInvalid(badLeagueId, '$.league.id')

    const badTeamId = cloneSnapshot()
    firstTeam(badTeamId).id = 'Team_Invalid'
    expectInvalid(badTeamId, '$.league.teams[0].id')

    const badPlayerId = cloneSnapshot()
    firstPlayer(badPlayerId).id = 'Player_Invalid'
    expectInvalid(badPlayerId, '$.league.players[0].id')
  })

  it.each([
    ['age', Number.NaN],
    ['age', Number.POSITIVE_INFINITY],
    ['age', 25.5],
    ['jerseyNumber', -1],
    ['primaryPosition', 'G'],
    ['ratingGenerationVersion', 2],
  ])('rejects invalid player %s value %#', (key, value) => {
    const input = cloneSnapshot()
    firstPlayer(input)[key] = value

    expectInvalid(input)
  })

  it('rejects duplicate IDs and orphaned player ownership', () => {
    const duplicate = cloneSnapshot()
    const duplicatePlayers = array(record(duplicate.league).players)
    record(duplicatePlayers[1]).id = record(duplicatePlayers[0]).id
    expectInvalid(duplicate, '$.league.players[1].id')

    const orphaned = cloneSnapshot()
    firstPlayer(orphaned).teamId = 'team_missing'
    expectInvalid(orphaned, '$.league.players[0].teamId')
  })

  it('rejects malformed team identity, mark, colors, and tendencies', () => {
    const badMark = cloneSnapshot()
    record(firstTeam(badMark).mark).text = 'BAD'
    expectInvalid(badMark, '$.league.teams[0].mark')

    const badColor = cloneSnapshot()
    record(firstTeam(badColor).colors).primary = 'red'
    expectInvalid(badColor, '$.league.teams[0].colors.primary')

    const badTendency = cloneSnapshot()
    record(firstPlayer(badTendency).tendencies).usage = 0
    expectInvalid(badTendency, '$.league.players[0].tendencies.usage')
  })

  it('rejects an incorrect league size instead of accepting partial data', () => {
    const input = cloneSnapshot()
    array(record(input.league).players).pop()

    expectInvalid(input, '$.league.players')
  })

  it('accepts only a managed team that belongs to the parsed league', () => {
    const malformed = cloneSnapshot()
    malformed.managedTeamId = 'Team_Invalid'
    expectInvalid(malformed, '$.managedTeamId')

    const missing = cloneSnapshot()
    missing.managedTeamId = parseTeamId('team_missing')
    expectInvalid(missing, '$.managedTeamId')

    const valid = cloneSnapshot()
    valid.managedTeamId = league.teams[3].id
    expect(parseLeagueSnapshot(valid).managedTeamId).toBe(league.teams[3].id)
  })
})

describe('stored ratings in snapshots', () => {
  it.each(RATING_KEYS)('requires canonical rating %s', (ratingKey) => {
    const input = cloneSnapshot()
    delete record(firstPlayer(input).ratings)[ratingKey]

    expectInvalid(input, `$.league.players[0].ratings.${ratingKey}`)
  })

  it.each([
    '50',
    Number.NaN,
    Number.POSITIVE_INFINITY,
    Number.NEGATIVE_INFINITY,
    50.5,
    -1,
    101,
  ])('rejects invalid stored rating %#', (rating) => {
    const input = cloneSnapshot()
    record(firstPlayer(input).ratings).insideScoring = rating

    expectInvalid(input, '$.league.players[0].ratings')
  })

  it('rejects stored grades in ratings or player records', () => {
    const ratingGrade = cloneSnapshot()
    record(firstPlayer(ratingGrade).ratings).grade = 'A'
    expectInvalid(ratingGrade, '$.league.players[0].ratings.grade')

    const playerGrade = cloneSnapshot()
    firstPlayer(playerGrade).grade = 'A'
    expectInvalid(playerGrade, '$.league.players[0].grade')
  })
})

type MutableRecord = Record<string, unknown>

function cloneSnapshot(): MutableRecord {
  return JSON.parse(JSON.stringify(snapshot)) as MutableRecord
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

function firstTeam(input: MutableRecord): MutableRecord {
  return record(array(record(input.league).teams)[0])
}

function firstPlayer(input: MutableRecord): MutableRecord {
  return record(array(record(input.league).players)[0])
}

function expectInvalid(value: unknown, path?: string): void {
  try {
    parseLeagueSnapshot(value)
  } catch (error) {
    expect(error).toBeInstanceOf(InvalidLeagueSnapshotError)
    if (path !== undefined) {
      expect((error as InvalidLeagueSnapshotError).path).toBe(path)
    }
    return
  }

  throw new Error('Expected snapshot parsing to fail')
}

// Compile-time checks ensure snapshot parsing produces the existing entities,
// rather than introducing parallel team or player definitions.
expectTypeOf<LeagueSnapshotV1['league']>().toEqualTypeOf<League>()
expectTypeOf<LeagueSnapshotV1['league']['teams'][number]>().toEqualTypeOf<Team>()
expectTypeOf<LeagueSnapshotV1['league']['players'][number]>().toEqualTypeOf<Player>()
