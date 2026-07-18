import type { PlayerId } from '../domain/ids'
import type { Position } from '../domain/league'
import {
  DETAILED_CATEGORY_DEFINITIONS,
  DETAILED_RATING_GENERATION_VERSION,
  DETAILED_RATING_MAX,
  DETAILED_RATING_MIN,
  SUB_RATING_KEYS,
  parseDetailedPlayerRatings,
} from '../domain/detailedRatings'
import type {
  DetailedCategoryKey,
  DetailedPlayerRatings,
  SubRatingKey,
} from '../domain/detailedRatings'
import type { RandomSource } from '../random/randomSource'
import { deriveSeed } from '../random/seed'
import { createRandomSource } from '../random/xoshiro128ss'

/**
 * §8B R3 — deterministic detailed-rating generation (ADR 0008 §5).
 *
 * generated value = player-quality baseline
 *                 + category aptitude
 *                 + primary-position bias (per category)
 *                 + field-specific variation,
 * clamped to a 0–100 integer.
 *
 * Every term draws from its own labeled stream — `player-quality/v1/{id}`,
 * `player-category/v1/{id}/{category}`, `player-skill/v1/{id}/{sub}` — so a
 * future field (or an archetype-bias term with its own label) shifts nothing
 * that exists today. Primary position biases generation only, never legality.
 */
export { DETAILED_RATING_GENERATION_VERSION }

export const PLAYER_QUALITY_STREAM_NAMESPACE = 'player-quality' as const
export const PLAYER_CATEGORY_STREAM_NAMESPACE = 'player-category' as const
export const PLAYER_SKILL_STREAM_NAMESPACE = 'player-skill' as const

/**
 * Starting calibration ranges — tuning inputs, not frozen constants
 * (ADR 0008 §5). Changing any of them still requires a
 * DETAILED_RATING_GENERATION_VERSION bump and new golden vectors.
 */
export const QUALITY_BASELINE_MIN = 45
export const QUALITY_BASELINE_MAX = 80
export const CATEGORY_APTITUDE_SPREAD = 8
export const FIELD_VARIATION_SPREAD = 6

type RandomSourceFactory = (seed: string) => RandomSource

type CategoryBiasProfile = Readonly<Record<DetailedCategoryKey, number>>

/**
 * Primary-position bias per category. The 16 categories shared with the
 * legacy model keep the V1 biases; the two new categories (Durability,
 * Intangibles) are position-neutral — toughness and character do not follow
 * the position someone plays.
 */
export const POSITION_CATEGORY_BIASES: Readonly<
  Record<Position, CategoryBiasProfile>
> = {
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
    durability: 0,
    basketballIQ: 6,
    intangibles: 0,
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
    durability: 0,
    basketballIQ: 3,
    intangibles: 0,
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
    durability: 0,
    basketballIQ: 1,
    intangibles: 0,
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
    durability: 0,
    basketballIQ: 0,
    intangibles: 0,
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
    durability: 0,
    basketballIQ: 0,
    intangibles: 0,
  },
}

/** The categories that weight each stored sub-rating (two for the shared one). */
const CATEGORIES_BY_SUB_RATING: ReadonlyMap<
  SubRatingKey,
  readonly DetailedCategoryKey[]
> = buildCategoriesBySubRating()

export function deriveDetailedQualitySeed(
  leagueSeed: string,
  playerId: PlayerId,
): string {
  return deriveSeed(
    leagueSeed,
    `${PLAYER_QUALITY_STREAM_NAMESPACE}/v${DETAILED_RATING_GENERATION_VERSION}/${playerId}`,
  )
}

export function deriveDetailedCategorySeed(
  leagueSeed: string,
  playerId: PlayerId,
  categoryKey: DetailedCategoryKey,
): string {
  return deriveSeed(
    leagueSeed,
    `${PLAYER_CATEGORY_STREAM_NAMESPACE}/v${DETAILED_RATING_GENERATION_VERSION}/${playerId}/${categoryKey}`,
  )
}

export function deriveDetailedSkillSeed(
  leagueSeed: string,
  playerId: PlayerId,
  subRatingKey: SubRatingKey,
): string {
  return deriveSeed(
    leagueSeed,
    `${PLAYER_SKILL_STREAM_NAMESPACE}/v${DETAILED_RATING_GENERATION_VERSION}/${playerId}/${subRatingKey}`,
  )
}

/** The one player-quality baseline draw shared by all of a player's fields. */
export function generateQualityBaseline(
  leagueSeed: string,
  playerId: PlayerId,
  createSource: RandomSourceFactory = createRandomSource,
): number {
  const random = createSource(deriveDetailedQualitySeed(leagueSeed, playerId))
  return randomInteger(QUALITY_BASELINE_MIN, QUALITY_BASELINE_MAX, random)
}

/** The per-category aptitude draw, independent of every other category. */
export function generateCategoryAptitude(
  leagueSeed: string,
  playerId: PlayerId,
  categoryKey: DetailedCategoryKey,
  createSource: RandomSourceFactory = createRandomSource,
): number {
  const random = createSource(
    deriveDetailedCategorySeed(leagueSeed, playerId, categoryKey),
  )
  return randomInteger(
    -CATEGORY_APTITUDE_SPREAD,
    CATEGORY_APTITUDE_SPREAD,
    random,
  )
}

/** The per-field variation draw, independent of every other field. */
export function generateFieldVariation(
  leagueSeed: string,
  playerId: PlayerId,
  subRatingKey: SubRatingKey,
  createSource: RandomSourceFactory = createRandomSource,
): number {
  const random = createSource(
    deriveDetailedSkillSeed(leagueSeed, playerId, subRatingKey),
  )
  return randomInteger(-FIELD_VARIATION_SPREAD, FIELD_VARIATION_SPREAD, random)
}

/**
 * Generates one stored sub-rating. For the shared Rebound Reading the
 * category term is the rounded mean of its two categories' (aptitude + bias)
 * — the deterministic rule for the taxonomy's sole shared field.
 */
export function generateDetailedRating(
  leagueSeed: string,
  playerId: PlayerId,
  primaryPosition: Position,
  subRatingKey: SubRatingKey,
  createSource: RandomSourceFactory = createRandomSource,
): number {
  const owningCategories = CATEGORIES_BY_SUB_RATING.get(subRatingKey)
  if (owningCategories === undefined) {
    throw new RangeError(`Unknown sub-rating: ${String(subRatingKey)}`)
  }

  const quality = generateQualityBaseline(leagueSeed, playerId, createSource)
  const categoryTerm = Math.round(
    owningCategories.reduce(
      (total, categoryKey) =>
        total +
        generateCategoryAptitude(
          leagueSeed,
          playerId,
          categoryKey,
          createSource,
        ) +
        POSITION_CATEGORY_BIASES[primaryPosition][categoryKey],
      0,
    ) / owningCategories.length,
  )
  const variation = generateFieldVariation(
    leagueSeed,
    playerId,
    subRatingKey,
    createSource,
  )

  return clamp(
    quality + categoryTerm + variation,
    DETAILED_RATING_MIN,
    DETAILED_RATING_MAX,
  )
}

/** Generates and validates the complete 67-field detailed record. */
export function generateDetailedPlayerRatings(
  leagueSeed: string,
  playerId: PlayerId,
  primaryPosition: Position,
  createSource: RandomSourceFactory = createRandomSource,
): DetailedPlayerRatings {
  return parseDetailedPlayerRatings(
    Object.fromEntries(
      SUB_RATING_KEYS.map((subRatingKey) => [
        subRatingKey,
        generateDetailedRating(
          leagueSeed,
          playerId,
          primaryPosition,
          subRatingKey,
          createSource,
        ),
      ]),
    ),
  )
}

function buildCategoriesBySubRating(): ReadonlyMap<
  SubRatingKey,
  readonly DetailedCategoryKey[]
> {
  const mapping = new Map<SubRatingKey, DetailedCategoryKey[]>()
  for (const definition of DETAILED_CATEGORY_DEFINITIONS) {
    for (const subRating of definition.subRatings) {
      const existing = mapping.get(subRating.key)
      if (existing === undefined) {
        mapping.set(subRating.key, [definition.key])
      } else {
        existing.push(definition.key)
      }
    }
  }
  return mapping
}

function randomInteger(
  minimum: number,
  maximum: number,
  random: RandomSource,
): number {
  return minimum + random.nextInt(maximum - minimum + 1)
}

function clamp(value: number, minimum: number, maximum: number): number {
  return Math.min(maximum, Math.max(minimum, value))
}
