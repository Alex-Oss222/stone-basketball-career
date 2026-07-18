import {
  FICTIONAL_PLAYER_FIRST_NAMES,
  FICTIONAL_PLAYER_LAST_NAMES,
} from '../data/fictional/playerNames'
import { FICTIONAL_TEAM_IDENTITIES } from '../data/fictional/teamIdentities'
import type { FictionalTeamIdentity } from '../data/fictional/teamIdentities'
import { parseLeagueId, parsePlayerId, parseTeamId } from '../domain/ids'
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
  CATEGORY_DEFINITION_VERSION,
  DETAILED_RATING_GENERATION_VERSION,
  DETAILED_RATINGS_SCHEMA_VERSION,
} from '../domain/detailedRatings'
import type { RandomSource } from '../random/randomSource'
import {
  deriveSeed,
  fingerprintDerivedSeed,
  normalizeSeed,
} from '../random/seed'
import { createRandomSource } from '../random/xoshiro128ss'
import { generateDetailedPlayerRatings } from './generateDetailedRatings'

export const LEAGUE_GENERATOR_VERSION = 1 as const
export const LEAGUE_RANDOM_STREAM_LABEL = 'league/v1' as const

const SEED_FINGERPRINT_LENGTH = 8

type RandomSourceFactory = (seed: string) => RandomSource

interface FictionalPlayerName {
  readonly firstName: string
  readonly lastName: string
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
  const seedFingerprint = fingerprintDerivedSeed(
    leagueSeed,
    SEED_FINGERPRINT_LENGTH,
  )
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
    detailedRatingsSchemaVersion: DETAILED_RATINGS_SCHEMA_VERSION,
    categoryDefinitionVersion: CATEGORY_DEFINITION_VERSION,
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
        ratingGenerationVersion: DETAILED_RATING_GENERATION_VERSION,
        ratings: generateDetailedPlayerRatings(
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

function formatOrdinal(ordinal: number): string {
  return ordinal.toString().padStart(2, '0')
}

function clamp(value: number, minimum: number, maximum: number): number {
  return Math.min(maximum, Math.max(minimum, value))
}
