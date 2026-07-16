import {
  FICTIONAL_PLAYER_FIRST_NAMES,
  FICTIONAL_PLAYER_LAST_NAMES,
} from '../data/fictional/playerNames'
import { FICTIONAL_TEAM_IDENTITIES } from '../data/fictional/teamIdentities'
import type { FictionalTeamIdentity } from '../data/fictional/teamIdentities'
import { parseLeagueId, parsePlayerId, parseTeamId } from '../domain/ids'
import type { PlayerId } from '../domain/ids'
import {
  JERSEY_NUMBER_MAX,
  JERSEY_NUMBER_MIN,
  LEAGUE_TEAM_COUNT,
  PLAYER_AGE_MAX,
  PLAYER_AGE_MIN,
  PLAYERS_PER_TEAM,
  POSITIONS,
} from '../domain/league'
import type {
  League,
  Player,
  PlayerTendencies,
  Position,
  Team,
} from '../domain/league'
import { assertValidLeague } from '../domain/leagueValidation'
import {
  RATING_GENERATION_VERSION,
  RATING_KEYS,
  STORED_RATING_MAX,
  STORED_RATING_MIN,
  parsePlayerRatings,
  parseStoredRating,
} from '../domain/ratings'
import type { PlayerRatings, RatingKey } from '../domain/ratings'
import type { RandomSource } from '../random/randomSource'
import { deriveSeed, normalizeSeed } from '../random/seed'
import { createRandomSource } from '../random/xoshiro128ss'

export const LEAGUE_GENERATOR_VERSION = 1 as const
export const LEAGUE_RANDOM_STREAM_LABEL = 'league/v1' as const
export const RATING_RANDOM_STREAM_NAMESPACE = 'player-rating' as const

const SEED_FINGERPRINT_LENGTH = 8
const BASE_TALENT_MIN = 45
const BASE_TALENT_MAX = 82
const RATING_JITTER = 10

type RatingProfile = Readonly<Record<RatingKey, number>>
type RandomSourceFactory = (seed: string) => RandomSource

interface FictionalPlayerName {
  readonly firstName: string
  readonly lastName: string
}

const POSITION_RATING_BIASES: Readonly<Record<Position, RatingProfile>> = {
  PG: {
    insideScoring: 0,
    midRangeShooting: 3,
    threePointShooting: 4,
    freeThrowShooting: 4,
    passing: 10,
    ballHandling: 10,
    offensiveRebounding: -9,
    defensiveRebounding: -6,
    perimeterDefense: 6,
    interiorDefense: -10,
    stealing: 6,
    blocking: -10,
    speed: 9,
    strength: -7,
    endurance: 3,
    basketballIQ: 6,
  },
  SG: {
    insideScoring: 2,
    midRangeShooting: 5,
    threePointShooting: 8,
    freeThrowShooting: 5,
    passing: 2,
    ballHandling: 5,
    offensiveRebounding: -7,
    defensiveRebounding: -3,
    perimeterDefense: 4,
    interiorDefense: -7,
    stealing: 3,
    blocking: -7,
    speed: 7,
    strength: -4,
    endurance: 3,
    basketballIQ: 3,
  },
  SF: {
    insideScoring: 4,
    midRangeShooting: 3,
    threePointShooting: 3,
    freeThrowShooting: 2,
    passing: 0,
    ballHandling: 0,
    offensiveRebounding: 0,
    defensiveRebounding: 2,
    perimeterDefense: 2,
    interiorDefense: 0,
    stealing: 1,
    blocking: 0,
    speed: 3,
    strength: 2,
    endurance: 2,
    basketballIQ: 1,
  },
  PF: {
    insideScoring: 7,
    midRangeShooting: 0,
    threePointShooting: -4,
    freeThrowShooting: -1,
    passing: -3,
    ballHandling: -5,
    offensiveRebounding: 7,
    defensiveRebounding: 8,
    perimeterDefense: -2,
    interiorDefense: 7,
    stealing: -2,
    blocking: 5,
    speed: -3,
    strength: 8,
    endurance: 1,
    basketballIQ: 0,
  },
  C: {
    insideScoring: 9,
    midRangeShooting: -5,
    threePointShooting: -10,
    freeThrowShooting: -4,
    passing: -6,
    ballHandling: -10,
    offensiveRebounding: 11,
    defensiveRebounding: 12,
    perimeterDefense: -8,
    interiorDefense: 12,
    stealing: -5,
    blocking: 12,
    speed: -7,
    strength: 11,
    endurance: 0,
    basketballIQ: 0,
  },
}

const SECONDARY_POSITION_OPTIONS: Readonly<
  Record<Position, readonly Position[]>
> = {
  PG: ['SG'],
  SG: ['PG', 'SF'],
  SF: ['SG', 'PF'],
  PF: ['SF', 'C'],
  C: ['PF'],
}

const SHOT_TENDENCY_BASES: Readonly<
  Record<Position, readonly [rim: number, midrange: number, threePoint: number]>
> = {
  PG: [35, 35, 45],
  SG: [30, 40, 55],
  SF: [40, 35, 40],
  PF: [55, 25, 25],
  C: [70, 15, 10],
}

const PASS_TENDENCY_BASES: Readonly<Record<Position, number>> = {
  PG: 70,
  SG: 45,
  SF: 40,
  PF: 30,
  C: 25,
}

export function generateLeague(rootSeed: string): League {
  const normalizedSeed = normalizeSeed(rootSeed)
  const leagueSeed = deriveSeed(normalizedSeed, LEAGUE_RANDOM_STREAM_LABEL)
  return generateLeagueWithRandomSource(
    normalizedSeed,
    createRandomSource(leagueSeed),
    createRandomSource,
  )
}

/**
 * Injectable generation core for deterministic tests and future application
 * composition. The caller must supply a fresh source initialized from
 * deriveSeed(normalizeSeed(rootSeed), LEAGUE_RANDOM_STREAM_LABEL).
 */
export function generateLeagueWithRandomSource(
  rootSeed: string,
  random: RandomSource,
  createRatingRandomSource: RandomSourceFactory = createRandomSource,
): League {
  const normalizedSeed = normalizeSeed(rootSeed)
  const leagueSeed = deriveSeed(normalizedSeed, LEAGUE_RANDOM_STREAM_LABEL)
  const seedFingerprint = fingerprintFromDerivedSeed(leagueSeed)
  const selectedIdentities = shuffled(FICTIONAL_TEAM_IDENTITIES, random).slice(
    0,
    LEAGUE_TEAM_COUNT,
  )
  const playerNames = shuffled(createPlayerNamePool(), random).slice(
    0,
    LEAGUE_TEAM_COUNT * PLAYERS_PER_TEAM,
  )

  const teams = createTeams(selectedIdentities, seedFingerprint)
  const players = createPlayers(
    teams,
    playerNames,
    seedFingerprint,
    leagueSeed,
    random,
    createRatingRandomSource,
  )
  const league: League = {
    id: parseLeagueId(`league_${seedFingerprint}`),
    generatorVersion: LEAGUE_GENERATOR_VERSION,
    seedFingerprint,
    teams,
    players,
  }

  assertValidLeague(league)
  return league
}

function createTeams(
  identities: readonly FictionalTeamIdentity[],
  seedFingerprint: string,
): readonly Team[] {
  return identities.map((identity, index) => ({
    id: parseTeamId(
      `team_${seedFingerprint}_${formatOrdinal(index + 1)}`,
    ),
    city: identity.city,
    nickname: identity.nickname,
    abbreviation: identity.abbreviation,
    colors: { ...identity.colors },
    mark: { kind: 'initials', text: identity.abbreviation },
  }))
}

function createPlayers(
  teams: readonly Team[],
  names: readonly FictionalPlayerName[],
  seedFingerprint: string,
  leagueSeed: string,
  random: RandomSource,
  createRatingRandomSource: RandomSourceFactory,
): readonly Player[] {
  const players: Player[] = []

  for (let teamIndex = 0; teamIndex < teams.length; teamIndex += 1) {
    const team = teams[teamIndex]
    const positions = createPositionTemplate(random)
    const jerseyNumbers = shuffled(
      integerRange(JERSEY_NUMBER_MIN, JERSEY_NUMBER_MAX),
      random,
    ).slice(0, PLAYERS_PER_TEAM)

    for (let rosterIndex = 0; rosterIndex < PLAYERS_PER_TEAM; rosterIndex += 1) {
      const name = names[teamIndex * PLAYERS_PER_TEAM + rosterIndex]
      const primaryPosition = positions[rosterIndex]
      const secondaryPosition = createSecondaryPosition(primaryPosition, random)
      const playerId = parsePlayerId(
        `player_${seedFingerprint}_${formatOrdinal(teamIndex + 1)}_${formatOrdinal(rosterIndex + 1)}`,
      )

      players.push({
        id: playerId,
        teamId: team.id,
        firstName: name.firstName,
        lastName: name.lastName,
        age:
          PLAYER_AGE_MIN +
          random.nextInt(PLAYER_AGE_MAX - PLAYER_AGE_MIN + 1),
        jerseyNumber: jerseyNumbers[rosterIndex],
        primaryPosition,
        secondaryPosition,
        ratingGenerationVersion: RATING_GENERATION_VERSION,
        ratings: createRatings(
          leagueSeed,
          playerId,
          primaryPosition,
          createRatingRandomSource,
        ),
        tendencies: createTendencies(primaryPosition, random),
      })
    }
  }

  return players
}

function createPositionTemplate(random: RandomSource): readonly Position[] {
  const positions: Position[] = [
    ...POSITIONS,
    ...POSITIONS,
    POSITIONS[random.nextInt(POSITIONS.length)],
    POSITIONS[random.nextInt(POSITIONS.length)],
  ]
  return shuffled(positions, random)
}

function createSecondaryPosition(
  primaryPosition: Position,
  random: RandomSource,
): Position | null {
  if (!random.chance(0.65)) {
    return null
  }

  const options = SECONDARY_POSITION_OPTIONS[primaryPosition]
  return options[random.nextInt(options.length)]
}

function createRatings(
  leagueSeed: string,
  playerId: PlayerId,
  position: Position,
  createRatingRandomSource: RandomSourceFactory,
): PlayerRatings {
  return parsePlayerRatings(
    Object.fromEntries(
      RATING_KEYS.map((ratingKey) => [
        ratingKey,
        generatePlayerRating(
          leagueSeed,
          playerId,
          position,
          ratingKey,
          createRatingRandomSource,
        ),
      ]),
    ),
  )
}

export function derivePlayerRatingSeed(
  leagueSeed: string,
  playerId: PlayerId,
  ratingKey: RatingKey,
): string {
  const label = `${RATING_RANDOM_STREAM_NAMESPACE}/v${RATING_GENERATION_VERSION}/${playerId}/${ratingKey}`
  return deriveSeed(leagueSeed, label)
}

export function generatePlayerRating(
  leagueSeed: string,
  playerId: PlayerId,
  position: Position,
  ratingKey: RatingKey,
  createRatingRandomSource: RandomSourceFactory = createRandomSource,
): number {
  const random = createRatingRandomSource(
    derivePlayerRatingSeed(leagueSeed, playerId, ratingKey),
  )
  const value =
    randomInteger(BASE_TALENT_MIN, BASE_TALENT_MAX, random) +
    POSITION_RATING_BIASES[position][ratingKey] +
    randomInteger(-RATING_JITTER, RATING_JITTER, random)

  return parseStoredRating(
    clamp(value, STORED_RATING_MIN, STORED_RATING_MAX),
  )
}

function createTendencies(
  position: Position,
  random: RandomSource,
): PlayerTendencies {
  const [rim, midrange, threePoint] = SHOT_TENDENCY_BASES[position]
  return {
    usage: randomInteger(1, 100, random),
    rim: clamp(rim + randomInteger(-10, 10, random), 0, 100),
    midrange: clamp(midrange + randomInteger(-10, 10, random), 0, 100),
    threePoint: clamp(threePoint + randomInteger(-10, 10, random), 0, 100),
    pass: clamp(
      PASS_TENDENCY_BASES[position] + randomInteger(-10, 10, random),
      0,
      100,
    ),
    drawFoul: randomInteger(20, 80, random),
  }
}

function createPlayerNamePool(): readonly FictionalPlayerName[] {
  return FICTIONAL_PLAYER_FIRST_NAMES.flatMap((firstName) =>
    FICTIONAL_PLAYER_LAST_NAMES.map((lastName) => ({ firstName, lastName })),
  )
}

function integerRange(minimum: number, maximum: number): readonly number[] {
  return Array.from(
    { length: maximum - minimum + 1 },
    (_, index) => minimum + index,
  )
}

function randomInteger(
  minimum: number,
  maximum: number,
  random: RandomSource,
): number {
  return minimum + random.nextInt(maximum - minimum + 1)
}

function shuffled<T>(items: readonly T[], random: RandomSource): T[] {
  const result = [...items]
  for (let index = result.length - 1; index > 0; index -= 1) {
    const swapIndex = random.nextInt(index + 1)
    const current = result[index]
    result[index] = result[swapIndex]
    result[swapIndex] = current
  }
  return result
}

function fingerprintFromDerivedSeed(derivedSeed: string): string {
  const separatorIndex = derivedSeed.lastIndexOf(':')
  const digest = derivedSeed.slice(separatorIndex + 1)

  if (digest.length < SEED_FINGERPRINT_LENGTH) {
    throw new Error('Derived seed digest is too short for a league fingerprint')
  }

  return digest.slice(0, SEED_FINGERPRINT_LENGTH)
}

function formatOrdinal(ordinal: number): string {
  return ordinal.toString().padStart(2, '0')
}

function clamp(value: number, minimum: number, maximum: number): number {
  return Math.min(maximum, Math.max(minimum, value))
}
