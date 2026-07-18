import {
  DETAILED_CATEGORY_DEFINITIONS,
  deriveAllCategoryScores,
  deriveCategoryScore,
} from './detailedRatings'
import type {
  DetailedCategoryGroup,
  DetailedPlayerRatings,
} from './detailedRatings'
import type { Position } from './league'

/**
 * §8B R7 — the versioned rotation-ability selector: the one player evaluation
 * the §8 CPU rotation generator consumes. Weighted over the six category
 * groups per position. Versioned separately from the display Overall
 * (playerDerivations.ts) so a UI recalibration can never change a CPU plan,
 * and separately from the simulation event reads (simulationReads.ts) so
 * planning weights can never change a game outcome. Derived only — never
 * stored.
 */
export const ROTATION_ABILITY_VERSION = 1 as const
export type RotationAbilityVersion = typeof ROTATION_ABILITY_VERSION

export const ROTATION_ABILITY_WEIGHT_TOTAL_BPS = 10_000

type GroupWeights = Readonly<Record<DetailedCategoryGroup, number>>

/** Per-position group weights in basis points; each column sums to 10 000. */
export const ROTATION_ABILITY_GROUP_WEIGHTS_BPS: Readonly<
  Record<Position, GroupWeights>
> = {
  PG: {
    scoring: 2400,
    creation: 2600,
    rebounding: 400,
    defense: 1900,
    physical: 1500,
    mental: 1200,
  },
  SG: {
    scoring: 3000,
    creation: 1800,
    rebounding: 500,
    defense: 2000,
    physical: 1500,
    mental: 1200,
  },
  SF: {
    scoring: 2700,
    creation: 1300,
    rebounding: 900,
    defense: 2200,
    physical: 1700,
    mental: 1200,
  },
  PF: {
    scoring: 2500,
    creation: 800,
    rebounding: 1600,
    defense: 2300,
    physical: 1800,
    mental: 1000,
  },
  C: {
    scoring: 2400,
    creation: 600,
    rebounding: 1800,
    defense: 2500,
    physical: 1800,
    mental: 900,
  },
}

export interface RotationAbility {
  /** Weighted planning ability at the position, full precision. */
  readonly ability: number
  /** The endurance category score — minute-allocation input, full precision. */
  readonly endurance: number
}

/**
 * Evaluates one player for CPU rotation planning at a position. Rotation
 * legality never depends on this — the rules require five legal players,
 * not a score.
 */
export function selectRotationAbility(
  ratings: DetailedPlayerRatings,
  position: Position,
): RotationAbility {
  const scores = deriveAllCategoryScores(ratings)
  const weights = ROTATION_ABILITY_GROUP_WEIGHTS_BPS[position]

  const groupMeans = new Map<DetailedCategoryGroup, number>()
  const groupCounts = new Map<DetailedCategoryGroup, number>()
  for (const definition of DETAILED_CATEGORY_DEFINITIONS) {
    groupMeans.set(
      definition.group,
      (groupMeans.get(definition.group) ?? 0) + scores[definition.key],
    )
    groupCounts.set(
      definition.group,
      (groupCounts.get(definition.group) ?? 0) + 1,
    )
  }

  let ability = 0
  for (const [group, total] of groupMeans) {
    const count = groupCounts.get(group) ?? 1
    ability += (total / count) * weights[group]
  }

  return {
    ability: ability / ROTATION_ABILITY_WEIGHT_TOTAL_BPS,
    endurance: deriveCategoryScore(ratings, 'endurance'),
  }
}
