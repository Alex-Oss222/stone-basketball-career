import { describe, expect, it } from 'vitest'
import { parseTeamId } from '../../src/domain/ids'
import type { League, Player, Position, Team } from '../../src/domain/league'
import {
  InvalidLeagueError,
  assertValidLeague,
  validateLeague,
} from '../../src/domain/leagueValidation'
import {
  RATING_GENERATION_VERSION,
  RATING_KEYS,
} from '../../src/domain/ratings'
import { generateLeague } from '../../src/generation/generateLeague'

const validLeague = generateLeague('league-validation-fixture')

describe('validateLeague', () => {
  it('accepts a generated league', () => {
    expect(validateLeague(validLeague)).toEqual([])
    expect(() => assertValidLeague(validLeague)).not.toThrow()
  })

  it('rejects duplicate IDs', () => {
    const invalid = replacePlayer(validLeague, 1, {
      id: validLeague.players[0].id,
    })

    expect(issueCodes(invalid)).toContain('id.duplicate')
  })

  it('rejects players that do not belong to exactly one league team', () => {
    const invalid = replacePlayer(validLeague, 0, {
      teamId: parseTeamId('team_missing'),
    })

    expect(issueCodes(invalid)).toContain('player.team_ownership.invalid')
  })

  it('rejects incorrect league and roster sizes', () => {
    const invalid: League = {
      ...validLeague,
      players: validLeague.players.slice(1),
    }
    const codes = issueCodes(invalid)

    expect(codes).toContain('league.player_count.invalid')
    expect(codes).toContain('team.roster_size.invalid')
  })

  it('rejects an incorrect team count and orphaned ownership links', () => {
    const invalid: League = {
      ...validLeague,
      teams: validLeague.teams.slice(1),
    }
    const codes = issueCodes(invalid)

    expect(codes).toContain('league.team_count.invalid')
    expect(codes).toContain('player.team_ownership.invalid')
  })

  it.each([
    {
      name: 'an age below the documented range',
      create: () => replacePlayer(validLeague, 0, { age: 18 }),
      code: 'player.age.invalid',
    },
    {
      name: 'a NaN age',
      create: () => replacePlayer(validLeague, 0, { age: Number.NaN }),
      code: 'player.age.invalid',
    },
    {
      name: 'a negative jersey number',
      create: () => replacePlayer(validLeague, 0, { jerseyNumber: -1 }),
      code: 'player.jersey_number.invalid',
    },
    {
      name: 'an invalid position',
      create: () =>
        replacePlayer(validLeague, 0, {
          primaryPosition: 'G' as Position,
        }),
      code: 'player.primary_position.invalid',
    },
    {
      name: 'an invalid tendency',
      create: () =>
        replacePlayer(validLeague, 0, {
          tendencies: { ...validLeague.players[0].tendencies, usage: 0 },
        }),
      code: 'player.tendency.invalid',
    },
  ])('rejects $name', ({ create, code }) => {
    expect(issueCodes(create())).toContain(code)
  })

  it('requires the canonical rating generation version', () => {
    expect(
      validLeague.players.every(
        (player) =>
          player.ratingGenerationVersion === RATING_GENERATION_VERSION,
      ),
    ).toBe(true)
  })

  it.each([undefined, 0, 2, 1.5, '1', Number.NaN])(
    'rejects invalid rating generation version %#',
    (ratingGenerationVersion) => {
      const invalid = replacePlayer(validLeague, 0, {
        ratingGenerationVersion:
          ratingGenerationVersion as Player['ratingGenerationVersion'],
      })

      expect(issueCodes(invalid)).toContain(
        'player.rating_generation_version.invalid',
      )
    },
  )

  it.each(RATING_KEYS)('rejects ratings missing %s', (ratingKey) => {
    const invalid = replaceRatings(validLeague, (ratings) => {
      delete ratings[ratingKey]
    })

    expect(issueCodes(invalid)).toContain('player.rating.missing')
  })

  it('rejects additional rating keys', () => {
    const invalid = replaceRatings(validLeague, (ratings) => {
      ratings.potential = 75
    })

    expect(issueCodes(invalid)).toContain('player.rating.unexpected')
  })

  it.each([
    { name: 'a non-number', value: '50' },
    { name: 'NaN', value: Number.NaN },
    { name: 'positive Infinity', value: Number.POSITIVE_INFINITY },
    { name: 'negative Infinity', value: Number.NEGATIVE_INFINITY },
    { name: 'a decimal', value: 50.5 },
    { name: 'a value below zero', value: -1 },
    { name: 'a value above one hundred', value: 101 },
  ])('rejects $name stored rating', ({ value }) => {
    const invalid = replaceRatings(validLeague, (ratings) => {
      ratings.insideScoring = value
    })

    expect(issueCodes(invalid)).toContain('player.rating.invalid')
  })

  it.each([null, [], 'ratings'])('rejects non-object ratings %#', (ratings) => {
    const invalid = replacePlayer(validLeague, 0, {
      ratings: ratings as unknown as Player['ratings'],
    })

    expect(issueCodes(invalid)).toContain('player.ratings.invalid')
  })

  it('rejects duplicate jersey numbers within a team', () => {
    const invalid = replacePlayer(validLeague, 1, {
      jerseyNumber: validLeague.players[0].jerseyNumber,
    })

    expect(issueCodes(invalid)).toContain('player.jersey_number.duplicate')
  })

  it('rejects team display data that violates entity rules', () => {
    const invalid = replaceTeam(validLeague, 0, {
      mark: { kind: 'initials', text: 'BAD' },
      colors: { ...validLeague.teams[0].colors, primary: 'not-a-color' },
    })
    const codes = issueCodes(invalid)

    expect(codes).toContain('team.mark.invalid')
    expect(codes).toContain('team.color.invalid')
  })

  it('throws a structured error when assertion fails', () => {
    const invalid = replacePlayer(validLeague, 0, { age: 99 })

    expect(() => assertValidLeague(invalid)).toThrow(InvalidLeagueError)
    try {
      assertValidLeague(invalid)
    } catch (error) {
      expect(error).toBeInstanceOf(InvalidLeagueError)
      expect((error as InvalidLeagueError).issues).not.toHaveLength(0)
    }
  })
})

function replacePlayer(
  league: League,
  index: number,
  replacement: Partial<Player>,
): League {
  return {
    ...league,
    players: league.players.map((player, playerIndex) =>
      playerIndex === index ? { ...player, ...replacement } : player,
    ),
  }
}

function replaceTeam(
  league: League,
  index: number,
  replacement: Partial<Team>,
): League {
  return {
    ...league,
    teams: league.teams.map((team, teamIndex) =>
      teamIndex === index ? { ...team, ...replacement } : team,
    ),
  }
}

function replaceRatings(
  league: League,
  mutate: (ratings: Record<string, unknown>) => void,
): League {
  const ratings: Record<string, unknown> = {
    ...league.players[0].ratings,
  }
  mutate(ratings)

  return replacePlayer(league, 0, {
    ratings: ratings as Player['ratings'],
  })
}

function issueCodes(league: League): readonly string[] {
  return validateLeague(league).map((issue) => issue.code)
}
