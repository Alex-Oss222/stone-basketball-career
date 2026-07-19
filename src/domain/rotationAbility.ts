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
 * §8C R7 — the versioned rotation-ability selector: the one player evaluation
 * the §8 CPU rotation generator consumes. Weighted over the four pillar groups
 * (offense / defense / physical / mental) per position, rekeyed from the old
 * six-group taxonomy (ADR 0009). Versioned separately from the display Overall
 * (playerDerivations.ts) so a UI recalibration can never change a CPU plan,
 * and separately from the simulation event reads (simulationReads.ts) so
 * planning weights can never change a game outcome. Derived only — never
 * stored.
 */
export const ROTATION_ABILITY_VERSION = 2 as const
export type RotationAbilityVersion = typeof ROTATION_ABILITY_VERSION

export const ROTATION_ABILITY_WEIGHT_TOTAL_BPS = 10_000

type GroupWeights = Readonly<Record<DetailedCategoryGroup, number>>

/** Per-position pillar weights in basis points; each column sums to 10 000. */
export const ROTATION_ABILITY_GROUP_WEIGHTS_BPS: Readonly<
  Record<Position, GroupWeights>
> = freezeGroupWeights({
  PG: { offense: 5000, defense: 2000, physical: 1500, mental: 1500 },
  SG: { offense: 4800, defense: 2200, physical: 1500, mental: 1500 },
  SF: { offense: 4200, defense: 2800, physical: 1600, mental: 1400 },
  PF: { offense: 3600, defense: 3200, physical: 1800, mental: 1400 },
  C: { offense: 3200, defense: 3600, physical: 1800, mental: 1400 },
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
  /** The conditioning category score — minute-allocation input, full precision. */
  readonly conditioning: number
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
    conditioning: scores.conditioning,
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
