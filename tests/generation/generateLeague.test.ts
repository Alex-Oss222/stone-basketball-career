import { describe, expect, it } from 'vitest'
import {
  FICTIONAL_PLAYER_FIRST_NAMES,
  FICTIONAL_PLAYER_LAST_NAMES,
} from '../../src/data/fictional/playerNames'
import { FICTIONAL_TEAM_IDENTITIES } from '../../src/data/fictional/teamIdentities'
import {
  isLeagueId,
  isPlayerId,
  isTeamId,
} from '../../src/domain/ids'
import {
  LEAGUE_PLAYER_COUNT,
  LEAGUE_TEAM_COUNT,
  PLAYER_AGE_MAX,
  PLAYER_AGE_MIN,
  PLAYERS_PER_TEAM,
  POSITIONS,
  isPosition,
} from '../../src/domain/league'
import { validateLeague } from '../../src/domain/leagueValidation'
import {
  DETAILED_CATEGORY_KEYS,
  DETAILED_RATING_GENERATION_VERSION,
  DETAILED_RATING_MAX,
  DETAILED_RATING_MIN,
  SUB_RATING_KEYS,
} from '../../src/domain/detailedRatings'
import {
  deriveDetailedCategorySeed,
  deriveDetailedQualitySeed,
  deriveDetailedSkillSeed,
  generateDetailedRating,
} from '../../src/generation/generateDetailedRatings'
import {
  LEAGUE_RANDOM_STREAM_LABEL,
  generateLeague,
  generateLeagueWithRandomSource,
} from '../../src/generation/generateLeague'
import { deriveSeed, normalizeSeed } from '../../src/random/seed'
import { createRandomSource } from '../../src/random/xoshiro128ss'

const FIXTURE_SEED = 'stone-league-foundation'
const league = generateLeague(FIXTURE_SEED)

describe('generateLeague determinism', () => {
  it('produces an identical complete league for an identical seed', () => {
    expect(generateLeague(FIXTURE_SEED)).toEqual(league)
    expect(generateLeague(`  ${FIXTURE_SEED}  `)).toEqual(league)
  })

  it('normally produces a different league for a different seed', () => {
    expect(generateLeague('another-foundation-seed')).not.toEqual(league)
  })

  it('uses the dedicated injectable league random stream', () => {
    const normalizedSeed = normalizeSeed(FIXTURE_SEED)
    const random = createRandomSource(
      deriveSeed(normalizedSeed, LEAGUE_RANDOM_STREAM_LABEL),
    )

    expect(generateLeagueWithRandomSource(normalizedSeed, random)).toEqual(league)
  })

  it('draws every rating from the three labeled detailed streams only', () => {
    const normalizedSeed = normalizeSeed(FIXTURE_SEED)
    const leagueSeed = deriveSeed(normalizedSeed, LEAGUE_RANDOM_STREAM_LABEL)
    const random = createRandomSource(leagueSeed)
    const observedRatingSeeds: string[] = []
    const generated = generateLeagueWithRandomSource(
      normalizedSeed,
      random,
      (ratingSeed) => {
        observedRatingSeeds.push(ratingSeed)
        return createRandomSource(ratingSeed)
      },
    )
    const expectedSeeds = new Set(
      generated.players.flatMap((player) => [
        deriveDetailedQualitySeed(leagueSeed, player.id),
        ...DETAILED_CATEGORY_KEYS.map((categoryKey) =>
          deriveDetailedCategorySeed(leagueSeed, player.id, categoryKey),
        ),
        ...SUB_RATING_KEYS.map((subRatingKey) =>
          deriveDetailedSkillSeed(leagueSeed, player.id, subRatingKey),
        ),
      ]),
    )

    // Quality + 18 category + 67 skill streams per player, nothing else.
    expect(new Set(observedRatingSeeds)).toEqual(expectedSeeds)
    expect(expectedSeeds.size).toBe(
      LEAGUE_PLAYER_COUNT * (1 + DETAILED_CATEGORY_KEYS.length + SUB_RATING_KEYS.length),
    )
  })

  it('keeps existing rating values independent of rating evaluation order', () => {
    const leagueSeed = deriveSeed(
      normalizeSeed(FIXTURE_SEED),
      LEAGUE_RANDOM_STREAM_LABEL,
    )
    const player = league.players[0]
    const forward = Object.fromEntries(
      SUB_RATING_KEYS.map((subRatingKey) => [
        subRatingKey,
        generateDetailedRating(
          leagueSeed,
          player.id,
          player.primaryPosition,
          subRatingKey,
        ),
      ]),
    )
    const reverse = Object.fromEntries(
      [...SUB_RATING_KEYS].reverse().map((subRatingKey) => [
        subRatingKey,
        generateDetailedRating(
          leagueSeed,
          player.id,
          player.primaryPosition,
          subRatingKey,
        ),
      ]),
    )

    expect(forward).toEqual(player.ratings)
    expect(reverse).toEqual(forward)
  })

  it('pins the version 1 fingerprint and first generated records', () => {
    expect({
      id: league.id,
      seedFingerprint: league.seedFingerprint,
      team: league.teams[0],
      player: league.players[0],
    }).toEqual({
      id: 'league_43879753',
      seedFingerprint: '43879753',
      team: {
        id: 'team_43879753_01',
        city: 'Alderreach',
        nickname: 'Astrolabes',
        abbreviation: 'ARA',
        colors: {
          primary: '#26355d',
          secondary: '#f2b84b',
          accent: '#f5f1e8',
        },
        mark: { kind: 'initials', text: 'ARA' },
      },
      player: {
        id: 'player_43879753_01_01',
        teamId: 'team_43879753_01',
        firstName: 'Jori',
        lastName: 'Jast',
        age: 30,
        jerseyNumber: 83,
        primaryPosition: 'C',
        secondaryPosition: null,
        ratingGenerationVersion: 1,
        ratings: {
          standingFinish: 93, drivingLayup: 98, contactFinishing: 96,
          dunking: 89, postFinishing: 89, catchAndShootMid: 71, pullUpMid: 65,
          contestedMid: 69, postFadeaway: 67, catchAndShootThree: 62,
          pullUpThree: 68, movementThree: 69, contestedThree: 70,
          freeThrowAccuracy: 78, freeThrowConsistency: 84,
          pressureFreeThrows: 76, passAccuracy: 70, courtVision: 70,
          passTiming: 71, dribbleControl: 79, ballSecurity: 76,
          changeOfDirection: 80, pressureHandling: 75,
          offensivePositioning: 83, reboundPursuit: 86, reboundReading: 98,
          secondJump: 83, defensivePositioning: 97, boxOutTechnique: 92,
          reboundSecurity: 92, onBallContainment: 82, lateralRecovery: 83,
          screenNavigation: 82, closeoutControl: 78, postContainment: 87,
          rimDeterrence: 94, helpRotation: 87, paintPositioning: 95,
          onBallSteal: 82, passingLaneAnticipation: 85, deflectionTiming: 81,
          stripTechnique: 85, blockTiming: 96, verticalContest: 98,
          helpSideBlocking: 92, recoveryBlocking: 99, acceleration: 81,
          topSpeed: 71, lateralQuickness: 81, agility: 72,
          lowerBodyStrength: 89, upperBodyStrength: 100, contactBalance: 95,
          physicalLeverage: 89, stamina: 84, recoveryRate: 86,
          workloadCapacity: 85, lateGameConditioning: 82,
          injuryResistance: 70, loadDurability: 74, offensiveAwareness: 79,
          defensiveAwareness: 79, decisionMaking: 86, competitiveness: 84,
          coachability: 82, composure: 82, workEthic: 75,
        },
        tendencies: {
          usage: 47,
          rim: 67,
          midrange: 18,
          threePoint: 12,
          pass: 30,
          drawFoul: 73,
        },
      },
    })
  })
})

describe('generated league identity and ownership', () => {
  it('creates exactly eight teams and ninety-six explicit players', () => {
    expect(league.teams).toHaveLength(LEAGUE_TEAM_COUNT)
    expect(league.players).toHaveLength(LEAGUE_PLAYER_COUNT)
  })

  it('creates stable, valid, globally unique IDs from the seed fingerprint', () => {
    const ids = [
      league.id,
      ...league.teams.map((team) => team.id),
      ...league.players.map((player) => player.id),
    ]

    expect(isLeagueId(league.id)).toBe(true)
    expect(league.id).toBe(`league_${league.seedFingerprint}`)
    expect(new Set(ids).size).toBe(ids.length)

    league.teams.forEach((team, teamIndex) => {
      const teamOrdinal = formatOrdinal(teamIndex + 1)
      expect(isTeamId(team.id)).toBe(true)
      expect(team.id).toBe(`team_${league.seedFingerprint}_${teamOrdinal}`)
    })

    league.players.forEach((player, playerIndex) => {
      const teamOrdinal = formatOrdinal(
        Math.floor(playerIndex / PLAYERS_PER_TEAM) + 1,
      )
      const rosterOrdinal = formatOrdinal(
        (playerIndex % PLAYERS_PER_TEAM) + 1,
      )
      expect(isPlayerId(player.id)).toBe(true)
      expect(player.id).toBe(
        `player_${league.seedFingerprint}_${teamOrdinal}_${rosterOrdinal}`,
      )
    })
  })

  it('assigns every player to exactly one twelve-player team roster', () => {
    const teamIds = new Set(league.teams.map((team) => team.id))

    for (const team of league.teams) {
      const roster = league.players.filter((player) => player.teamId === team.id)
      expect(roster).toHaveLength(PLAYERS_PER_TEAM)
      expect(new Set(roster.map((player) => player.id)).size).toBe(
        PLAYERS_PER_TEAM,
      )
    }

    for (const player of league.players) {
      expect(teamIds.has(player.teamId)).toBe(true)
    }
  })

  it('uses unique curated fictional identities, palettes, and player names', () => {
    const allowedTeamIdentities = new Set(
      FICTIONAL_TEAM_IDENTITIES.map(teamIdentitySignature),
    )
    const generatedTeamIdentities = league.teams.map(teamIdentitySignature)
    const generatedPalettes = league.teams.map((team) =>
      [team.colors.primary, team.colors.secondary, team.colors.accent].join('|'),
    )
    const generatedPlayerNames = league.players.map(
      (player) => `${player.firstName}|${player.lastName}`,
    )

    expect(new Set(generatedTeamIdentities).size).toBe(LEAGUE_TEAM_COUNT)
    expect(new Set(generatedPalettes).size).toBe(LEAGUE_TEAM_COUNT)
    expect(new Set(generatedPlayerNames).size).toBe(LEAGUE_PLAYER_COUNT)

    for (const team of league.teams) {
      expect(allowedTeamIdentities.has(teamIdentitySignature(team))).toBe(true)
      expect(team.mark).toEqual({ kind: 'initials', text: team.abbreviation })
    }

    for (const player of league.players) {
      expect(FICTIONAL_PLAYER_FIRST_NAMES).toContain(player.firstName)
      expect(FICTIONAL_PLAYER_LAST_NAMES).toContain(player.lastName)
    }
  })

  it('stores the whole league as a JSON-safe snapshot', () => {
    const loadedSnapshot = JSON.parse(JSON.stringify(league)) as unknown

    expect(loadedSnapshot).toEqual(league)
    expect(
      (loadedSnapshot as { readonly players: readonly unknown[] }).players,
    ).toHaveLength(LEAGUE_PLAYER_COUNT)
  })
})

describe('generated player rules', () => {
  it('creates position-balanced rosters with unique jersey numbers', () => {
    for (const team of league.teams) {
      const roster = league.players.filter((player) => player.teamId === team.id)
      const positionCounts = new Map<(typeof POSITIONS)[number], number>(
        POSITIONS.map((position) => [position, 0] as const),
      )

      for (const player of roster) {
        positionCounts.set(
          player.primaryPosition,
          (positionCounts.get(player.primaryPosition) ?? 0) + 1,
        )
      }

      for (const position of POSITIONS) {
        expect(positionCounts.get(position)).toBeGreaterThanOrEqual(2)
      }
      expect(new Set(roster.map((player) => player.jerseyNumber)).size).toBe(
        PLAYERS_PER_TEAM,
      )
    }
  })

  it('keeps ages, ratings, tendencies, and positions in their ranges', () => {
    for (const player of league.players) {
      expect(Number.isInteger(player.age)).toBe(true)
      expect(player.age).toBeGreaterThanOrEqual(PLAYER_AGE_MIN)
      expect(player.age).toBeLessThanOrEqual(PLAYER_AGE_MAX)
      expect(isPosition(player.primaryPosition)).toBe(true)
      expect(
        player.secondaryPosition === null || isPosition(player.secondaryPosition),
      ).toBe(true)

      expect(Object.keys(player.ratings).sort()).toEqual(
        [...SUB_RATING_KEYS].sort(),
      )
      expect(player.ratingGenerationVersion).toBe(
        DETAILED_RATING_GENERATION_VERSION,
      )
      for (const rating of Object.values(player.ratings)) {
        expect(Number.isInteger(rating)).toBe(true)
        expect(rating).toBeGreaterThanOrEqual(DETAILED_RATING_MIN)
        expect(rating).toBeLessThanOrEqual(DETAILED_RATING_MAX)
      }

      expect(player.tendencies.usage).toBeGreaterThanOrEqual(1)
      expect(player.tendencies.usage).toBeLessThanOrEqual(100)
      for (const tendency of Object.values(player.tendencies)) {
        expect(Number.isInteger(tendency)).toBe(true)
        expect(tendency).toBeGreaterThanOrEqual(0)
        expect(tendency).toBeLessThanOrEqual(100)
      }
      expect(
        player.tendencies.rim +
          player.tendencies.midrange +
          player.tendencies.threePoint,
      ).toBeGreaterThan(0)
    }
  })

  it('never generates a negative, non-finite, or NaN numeric value', () => {
    for (const seed of Array.from({ length: 20 }, (_, index) => `seed_${index}`)) {
      const generated = generateLeague(seed)
      for (const value of collectNumbers(generated)) {
        expect(Number.isFinite(value), seed).toBe(true)
        expect(Number.isNaN(value), seed).toBe(false)
        expect(value, seed).toBeGreaterThanOrEqual(0)
      }
      expect(validateLeague(generated), seed).toEqual([])
    }
  })
})

function teamIdentitySignature(team: {
  readonly city: string
  readonly nickname: string
  readonly abbreviation: string
}): string {
  return `${team.city}|${team.nickname}|${team.abbreviation}`
}

function formatOrdinal(value: number): string {
  return value.toString().padStart(2, '0')
}

function collectNumbers(value: unknown): readonly number[] {
  if (typeof value === 'number') {
    return [value]
  }
  if (Array.isArray(value)) {
    return value.flatMap(collectNumbers)
  }
  if (value !== null && typeof value === 'object') {
    return Object.values(value).flatMap(collectNumbers)
  }
  return []
}
