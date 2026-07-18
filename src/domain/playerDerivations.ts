import {
  DETAILED_CATEGORY_KEYS,
  deriveAllCategoryScores,
} from './detailedRatings'
import type {
  DetailedCategoryKey,
  DetailedPlayerRatings,
} from './detailedRatings'
import type { Position } from './league'

/**
 * §8B R5 — the versioned, position-weighted, derived-only player overall and
 * per-position offense/defense profile (ADR 0008: Overall is display-only,
 * never stored, never read by the simulation; Potential does not exist).
 * Weights are display config in integer basis points — changing them bumps
 * OVERALL_MODEL_VERSION and can never change a game outcome (they are
 * versioned separately from any simulation weights, per ADR 0008 §4).
 */
export const OVERALL_MODEL_VERSION = 1 as const
export type OverallModelVersion = typeof OVERALL_MODEL_VERSION

export const OVERALL_WEIGHT_TOTAL_BPS = 10_000

type PositionWeights = Readonly<Record<DetailedCategoryKey, number>>

/**
 * Position-weighted category weights for the derived Overall. Each position's
 * column sums to exactly 10 000 bps. A uniform rating record therefore scores
 * identically at every position — the weights express emphasis, not scale.
 */
export const POSITION_OVERALL_WEIGHTS_BPS: Readonly<
  Record<Position, PositionWeights>
> = freezePositionWeights({
  PG: {
    insideScoring: 500,
    midRangeShooting: 700,
    threePointShooting: 900,
    freeThrowShooting: 400,
    passing: 1200,
    ballHandling: 1200,
    offensiveRebounding: 100,
    defensiveRebounding: 300,
    perimeterDefense: 900,
    interiorDefense: 200,
    stealing: 600,
    blocking: 100,
    speed: 900,
    strength: 200,
    endurance: 500,
    durability: 200,
    basketballIQ: 900,
    intangibles: 200,
  },
  SG: {
    insideScoring: 600,
    midRangeShooting: 900,
    threePointShooting: 1200,
    freeThrowShooting: 500,
    passing: 700,
    ballHandling: 900,
    offensiveRebounding: 150,
    defensiveRebounding: 350,
    perimeterDefense: 900,
    interiorDefense: 250,
    stealing: 550,
    blocking: 150,
    speed: 800,
    strength: 300,
    endurance: 500,
    durability: 200,
    basketballIQ: 750,
    intangibles: 300,
  },
  SF: {
    insideScoring: 800,
    midRangeShooting: 700,
    threePointShooting: 900,
    freeThrowShooting: 400,
    passing: 600,
    ballHandling: 600,
    offensiveRebounding: 400,
    defensiveRebounding: 600,
    perimeterDefense: 800,
    interiorDefense: 500,
    stealing: 400,
    blocking: 350,
    speed: 700,
    strength: 500,
    endurance: 500,
    durability: 250,
    basketballIQ: 700,
    intangibles: 300,
  },
  PF: {
    insideScoring: 1000,
    midRangeShooting: 500,
    threePointShooting: 500,
    freeThrowShooting: 350,
    passing: 450,
    ballHandling: 350,
    offensiveRebounding: 800,
    defensiveRebounding: 900,
    perimeterDefense: 450,
    interiorDefense: 900,
    stealing: 300,
    blocking: 700,
    speed: 450,
    strength: 900,
    endurance: 400,
    durability: 300,
    basketballIQ: 450,
    intangibles: 300,
  },
  C: {
    insideScoring: 1200,
    midRangeShooting: 400,
    threePointShooting: 250,
    freeThrowShooting: 350,
    passing: 400,
    ballHandling: 250,
    offensiveRebounding: 900,
    defensiveRebounding: 1000,
    perimeterDefense: 300,
    interiorDefense: 1100,
    stealing: 250,
    blocking: 900,
    speed: 350,
    strength: 1000,
    endurance: 400,
    durability: 350,
    basketballIQ: 400,
    intangibles: 200,
  },
})

/** Categories that count toward the offense half of a position profile. */
export const OFFENSE_CATEGORY_KEYS: readonly DetailedCategoryKey[] =
  Object.freeze([
    'insideScoring',
    'midRangeShooting',
    'threePointShooting',
    'freeThrowShooting',
    'passing',
    'ballHandling',
    'offensiveRebounding',
  ])

/** Categories that count toward the defense half of a position profile. */
export const DEFENSE_CATEGORY_KEYS: readonly DetailedCategoryKey[] =
  Object.freeze([
    'perimeterDefense',
    'interiorDefense',
    'stealing',
    'blocking',
    'defensiveRebounding',
  ])

export interface PositionProfile {
  /** Weighted offense score at this position, full precision. */
  readonly offense: number
  /** Weighted defense score at this position, full precision. */
  readonly defense: number
  /** The versioned position-weighted overall, full precision. */
  readonly overall: number
}

const profileCache = new WeakMap<
  DetailedPlayerRatings,
  Map<Position, PositionProfile>
>()

/**
 * The versioned position-weighted Overall, rounded for display. Derived only
 * — never stored, never read by the simulation.
 */
export function deriveVersionedOverall(
  ratings: DetailedPlayerRatings,
  position: Position,
): number {
  return Math.round(derivePositionProfile(ratings, position).overall)
}

/**
 * Offense / defense / overall at a position, memoized per ratings reference.
 * Grades are always taken from the unrounded scores (ADR 0008 §3).
 */
export function derivePositionProfile(
  ratings: DetailedPlayerRatings,
  position: Position,
): PositionProfile {
  const cached = profileCache.get(ratings)?.get(position)
  if (cached !== undefined) {
    return cached
  }

  const scores = deriveAllCategoryScores(ratings)
  const weights = POSITION_OVERALL_WEIGHTS_BPS[position]

  const overall =
    DETAILED_CATEGORY_KEYS.reduce(
      (total, key) => total + scores[key] * weights[key],
      0,
    ) / OVERALL_WEIGHT_TOTAL_BPS
  const offense = weightedSubset(scores, weights, OFFENSE_CATEGORY_KEYS)
  const defense = weightedSubset(scores, weights, DEFENSE_CATEGORY_KEYS)

  const profile: PositionProfile = Object.freeze({ offense, defense, overall })
  const byPosition =
    profileCache.get(ratings) ?? new Map<Position, PositionProfile>()
  byPosition.set(position, profile)
  profileCache.set(ratings, byPosition)
  return profile
}

function weightedSubset(
  scores: Readonly<Record<DetailedCategoryKey, number>>,
  weights: PositionWeights,
  keys: readonly DetailedCategoryKey[],
): number {
  const weightTotal = keys.reduce((total, key) => total + weights[key], 0)
  const weighted = keys.reduce(
    (total, key) => total + scores[key] * weights[key],
    0,
  )
  return weighted / weightTotal
}

function freezePositionWeights(
  weights: Record<Position, PositionWeights>,
): Readonly<Record<Position, PositionWeights>> {
  for (const positionWeights of Object.values(weights)) {
    Object.freeze(positionWeights)
  }
  return Object.freeze(weights)
}
