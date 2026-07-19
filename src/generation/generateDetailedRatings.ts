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
 * §8C R3 — deterministic detailed-rating generation (ADR 0009 §5).
 *
 * generated value = player-quality baseline
 *                 + category aptitude
 *                 + primary-position bias (per category)
 *                 + field-specific variation,
 * clamped to a 0–100 integer.
 *
 * Every term draws from its own labeled stream — `player-quality/v2/{id}`,
 * `player-category/v2/{id}/{category}`, `player-skill/v2/{id}/{sub}` (the seed
 * labels interpolate DETAILED_RATING_GENERATION_VERSION) — so a future field
 * (or an archetype-bias term with its own label) shifts nothing that exists
 * today. Primary position biases generation only, never legality.
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
 * Primary-position bias per category, over the 26 categories of ADR 0009. The
 * position-neutral categories (Durability, Competitive Makeup) carry 0 — a
 * player's toughness and character do not follow the position he plays. Free
 * Throw is near-neutral. The shared Rebound Reading term averages the offensive
 * and defensive rebounding biases (see `deriveCategoryTerm`).
 */
export const POSITION_CATEGORY_BIASES: Readonly<
  Record<Position, CategoryBiasProfile>
> = freezePositionCategoryBiases({
  PG: {
    rimFinishing: 0,
    postScoring: -10,
    midRangeShooting: 3,
    threePointShooting: 4,
    freeThrowShooting: 4,
    passing: 10,
    ballHandling: 10,
    offBallOffense: 2,
    screening: -8,
    offensiveRebounding: -9,
    perimeterDefense: 6,
    offBallDefense: 2,
    interiorDefense: -10,
    stealing: 6,
    blocking: -10,
    defensiveRebounding: -6,
    speed: 9,
    agility: 9,
    explosiveness: 3,
    strength: -7,
    conditioning: 3,
    durability: 0,
    offensiveIQ: 6,
    defensiveIQ: 2,
    competitiveMakeup: 0,
    teamLeadership: 3,
  },
  SG: {
    rimFinishing: 2,
    postScoring: -7,
    midRangeShooting: 5,
    threePointShooting: 8,
    freeThrowShooting: 5,
    passing: 2,
    ballHandling: 5,
    offBallOffense: 4,
    screening: -6,
    offensiveRebounding: -7,
    perimeterDefense: 4,
    offBallDefense: 2,
    interiorDefense: -7,
    stealing: 3,
    blocking: -7,
    defensiveRebounding: -3,
    speed: 7,
    agility: 6,
    explosiveness: 4,
    strength: -4,
    conditioning: 3,
    durability: 0,
    offensiveIQ: 3,
    defensiveIQ: 2,
    competitiveMakeup: 0,
    teamLeadership: 1,
  },
  SF: {
    rimFinishing: 4,
    postScoring: 0,
    midRangeShooting: 3,
    threePointShooting: 3,
    freeThrowShooting: 2,
    passing: 0,
    ballHandling: 0,
    offBallOffense: 2,
    screening: 0,
    offensiveRebounding: 0,
    perimeterDefense: 2,
    offBallDefense: 1,
    interiorDefense: 0,
    stealing: 1,
    blocking: 0,
    defensiveRebounding: 2,
    speed: 3,
    agility: 2,
    explosiveness: 2,
    strength: 2,
    conditioning: 2,
    durability: 0,
    offensiveIQ: 1,
    defensiveIQ: 1,
    competitiveMakeup: 0,
    teamLeadership: 0,
  },
  PF: {
    rimFinishing: 7,
    postScoring: 7,
    midRangeShooting: 0,
    threePointShooting: -4,
    freeThrowShooting: -1,
    passing: -3,
    ballHandling: -5,
    offBallOffense: -1,
    screening: 6,
    offensiveRebounding: 7,
    perimeterDefense: -2,
    offBallDefense: 0,
    interiorDefense: 7,
    stealing: -2,
    blocking: 5,
    defensiveRebounding: 8,
    speed: -3,
    agility: -3,
    explosiveness: 2,
    strength: 8,
    conditioning: 1,
    durability: 0,
    offensiveIQ: 0,
    defensiveIQ: 1,
    competitiveMakeup: 0,
    teamLeadership: 0,
  },
  C: {
    rimFinishing: 9,
    postScoring: 11,
    midRangeShooting: -5,
    threePointShooting: -10,
    freeThrowShooting: -4,
    passing: -6,
    ballHandling: -10,
    offBallOffense: -3,
    screening: 9,
    offensiveRebounding: 11,
    perimeterDefense: -8,
    offBallDefense: -3,
    interiorDefense: 12,
    stealing: -5,
    blocking: 12,
    defensiveRebounding: 12,
    speed: -7,
    agility: -7,
    explosiveness: 2,
    strength: 11,
    conditioning: 0,
    durability: 0,
    offensiveIQ: 0,
    defensiveIQ: 2,
    competitiveMakeup: 0,
    teamLeadership: 0,
  },
})

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
  const owningCategories = getOwningCategories(subRatingKey)
  const quality = generateQualityBaseline(leagueSeed, playerId, createSource)
  const categoryTerm = deriveCategoryTerm(
    owningCategories,
    primaryPosition,
    (categoryKey) =>
      generateCategoryAptitude(
        leagueSeed,
        playerId,
        categoryKey,
        createSource,
      ),
  )
  const variation = generateFieldVariation(
    leagueSeed,
    playerId,
    subRatingKey,
    createSource,
  )

  return composeDetailedRating(quality, categoryTerm, variation)
}

/** Generates and validates the complete 91-field detailed record. */
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

function getOwningCategories(
  subRatingKey: SubRatingKey,
): readonly DetailedCategoryKey[] {
  const owningCategories = CATEGORIES_BY_SUB_RATING.get(subRatingKey)
  if (owningCategories === undefined) {
    throw new RangeError(`Unknown sub-rating: ${String(subRatingKey)}`)
  }
  return owningCategories
}

function deriveCategoryTerm(
  owningCategories: readonly DetailedCategoryKey[],
  primaryPosition: Position,
  getAptitude: (categoryKey: DetailedCategoryKey) => number,
): number {
  return Math.round(
    owningCategories.reduce(
      (total, categoryKey) =>
        total +
        getAptitude(categoryKey) +
        POSITION_CATEGORY_BIASES[primaryPosition][categoryKey],
      0,
    ) / owningCategories.length,
  )
}

function composeDetailedRating(
  quality: number,
  categoryTerm: number,
  variation: number,
): number {
  return clamp(
    quality + categoryTerm + variation,
    DETAILED_RATING_MIN,
    DETAILED_RATING_MAX,
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
  for (const categories of mapping.values()) {
    Object.freeze(categories)
  }
  return mapping
}

function freezePositionCategoryBiases(
  biases: Record<Position, CategoryBiasProfile>,
): Readonly<Record<Position, CategoryBiasProfile>> {
  for (const profile of Object.values(biases)) {
    Object.freeze(profile)
  }
  return Object.freeze(biases)
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
