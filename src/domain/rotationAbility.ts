import {
  DETAILED_CATEGORY_GROUPS,
  DETAILED_CATEGORY_DEFINITIONS,
  deriveAllCategoryScores,
} from './detailedRatings'
import type {
  DetailedCategoryKey,
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
> = freezeGroupWeights({
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
})

interface CategoryGroupMetadata {
  readonly group: DetailedCategoryGroup
  readonly categoryKeys: readonly DetailedCategoryKey[]
}

const CATEGORY_GROUP_METADATA: readonly CategoryGroupMetadata[] =
  Object.freeze(
    DETAILED_CATEGORY_GROUPS.map((group) =>
      Object.freeze({
        group,
        categoryKeys: Object.freeze(
          DETAILED_CATEGORY_DEFINITIONS.filter(
            (definition) => definition.group === group,
          ).map((definition) => definition.key),
        ),
      }),
    ),
  )

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

  let ability = 0
  for (const { group, categoryKeys } of CATEGORY_GROUP_METADATA) {
    const total = categoryKeys.reduce(
      (sum, categoryKey) => sum + scores[categoryKey],
      0,
    )
    ability += (total / categoryKeys.length) * weights[group]
  }

  return Object.freeze({
    ability: ability / ROTATION_ABILITY_WEIGHT_TOTAL_BPS,
    endurance: scores.endurance,
  })
}

function freezeGroupWeights(
  weights: Record<Position, GroupWeights>,
): Readonly<Record<Position, GroupWeights>> {
  for (const groupWeights of Object.values(weights)) {
    Object.freeze(groupWeights)
  }
  return Object.freeze(weights)
}
