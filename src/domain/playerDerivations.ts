import { deriveAllCategoryScores } from './detailedRatings'
import type {
  DetailedCategoryKey,
  DetailedPlayerRatings,
} from './detailedRatings'
import type { PlayerMeasurements, Position } from './league'

/**
 * §8C R5 / §6d — the versioned, position-weighted, derived-only player ratings
 * (ADR 0009 §5, RATINGS_REHAUL §8, DESIGN_OVERVIEW §6d). Both scores below are
 * display-only, never stored, never read by the simulation. The model is the
 * five-step 4-pillar hierarchy:
 *
 *   sub-ratings → 26 category scores
 *     → position-adjusted Offense / Defense / Physical / Mental pillar scores
 *       (Physical includes the derived Functional Size and EXCLUDES Durability)
 *     → per-role pillar-weighted score.
 *
 * Two distinct headline numbers derive from that hierarchy:
 *
 * - **Role Fit** (`deriveRoleFit` / `profile.roleFit`): the straight
 *   position-pillar-weighted mean of the four pillar scores — "how well this
 *   player satisfies what we value *at this position*". This is the original
 *   position-weighted Overall, unchanged; it grades positions on different
 *   scales and is NOT a cross-position ranking.
 * - **Headline OVR** (`deriveOverall`): the reward-peaks interim ("Path A now",
 *   §6d). Within each pillar it blends the pillar mean with that pillar's single
 *   best category so peaks are rewarded over pure averaging, then takes the
 *   position-pillar-weighted mean of the four blended values, and finally the
 *   best such value across the player's eligible roles. It is an interim inside
 *   the pillar frame — it does NOT fix cross-position comparability or
 *   double-counting; only the future impact system does.
 *
 * Weights are display config in integer basis points — changing them (or
 * PEAK_BLEND) bumps OVERALL_MODEL_VERSION and can never change a game outcome
 * (versioned separately from any simulation weights). Durability leaves both
 * scores entirely and becomes a separate Availability grade
 * (`deriveAvailability`), shown but never in OVR.
 */
export const OVERALL_MODEL_VERSION = 3 as const
export type OverallModelVersion = typeof OVERALL_MODEL_VERSION

export const OVERALL_WEIGHT_TOTAL_BPS = 10_000

/**
 * Reward-peaks blend for Headline OVR (DESIGN_OVERVIEW §6d): the share each
 * pillar's single best category contributes over the pillar's position-weighted
 * mean. 0 reproduces Role Fit's straight averaging; 1 would use only peaks.
 * A tunable display constant — changing it bumps OVERALL_MODEL_VERSION and can
 * never change a game outcome.
 */
export const PEAK_BLEND = 0.35

/** The four OVR pillars, in canonical order. */
export const OVERALL_PILLARS = [
  'offense',
  'defense',
  'physical',
  'mental',
] as const
export type OverallPillar = (typeof OVERALL_PILLARS)[number]

/**
 * The derived Physical-pillar item keys: the five physical category scores that
 * feed OVR plus the derived Functional Size. Durability is deliberately absent
 * (it feeds Availability, never OVR).
 */
type PhysicalItemKey =
  | 'functionalSize'
  | 'speed'
  | 'agility'
  | 'explosiveness'
  | 'strength'
  | 'conditioning'

type OffenseWeights = Readonly<Record<OffenseCategoryKey, number>>
type DefenseWeights = Readonly<Record<DefenseCategoryKey, number>>
type PhysicalWeights = Readonly<Record<PhysicalItemKey, number>>
type MentalWeights = Readonly<Record<MentalCategoryKey, number>>
type PillarWeights = Readonly<Record<OverallPillar, number>>

type OffenseCategoryKey =
  | 'rimFinishing'
  | 'postScoring'
  | 'midRangeShooting'
  | 'threePointShooting'
  | 'freeThrowShooting'
  | 'passing'
  | 'ballHandling'
  | 'offBallOffense'
  | 'screening'
  | 'offensiveRebounding'

type DefenseCategoryKey =
  | 'perimeterDefense'
  | 'offBallDefense'
  | 'interiorDefense'
  | 'stealing'
  | 'blocking'
  | 'defensiveRebounding'

type MentalCategoryKey =
  | 'offensiveIQ'
  | 'defensiveIQ'
  | 'competitiveMakeup'
  | 'teamLeadership'

/**
 * Fixed reference means/SDs (inches) for the Functional Size z-score
 * (RATINGS_REHAUL §3). These are a **versioned constant set** — never
 * recomputed per season, so a player's Functional Size never drifts because the
 * league grew taller or shorter. Changing them bumps OVERALL_MODEL_VERSION.
 */
export const FUNCTIONAL_SIZE_REFERENCE = Object.freeze({
  standingReachInches: Object.freeze({ mean: 105, sd: 5 }),
  wingspanInches: Object.freeze({ mean: 83, sd: 4 }),
  heightInches: Object.freeze({ mean: 79, sd: 3.5 }),
})

/**
 * Step 2 — position-adjusted offensive weights (RATINGS_REHAUL §8, verbatim).
 * Each column sums to exactly 10 000 bps.
 */
export const OFFENSE_POSITION_WEIGHTS_BPS: Readonly<
  Record<Position, OffenseWeights>
> = freeze({
  PG: {
    rimFinishing: 1000, postScoring: 100, midRangeShooting: 1000,
    threePointShooting: 1500, freeThrowShooting: 400, passing: 2500,
    ballHandling: 2300, offBallOffense: 800, screening: 100,
    offensiveRebounding: 300,
  },
  SG: {
    rimFinishing: 1300, postScoring: 200, midRangeShooting: 1300,
    threePointShooting: 2200, freeThrowShooting: 500, passing: 1200,
    ballHandling: 1400, offBallOffense: 1300, screening: 200,
    offensiveRebounding: 400,
  },
  SF: {
    rimFinishing: 1400, postScoring: 500, midRangeShooting: 1200,
    threePointShooting: 2000, freeThrowShooting: 400, passing: 1000,
    ballHandling: 1000, offBallOffense: 1400, screening: 400,
    offensiveRebounding: 700,
  },
  PF: {
    rimFinishing: 1800, postScoring: 1200, midRangeShooting: 800,
    threePointShooting: 1500, freeThrowShooting: 400, passing: 700,
    ballHandling: 600, offBallOffense: 1000, screening: 900,
    offensiveRebounding: 1100,
  },
  C: {
    rimFinishing: 2300, postScoring: 1800, midRangeShooting: 500,
    threePointShooting: 800, freeThrowShooting: 400, passing: 700,
    ballHandling: 300, offBallOffense: 700, screening: 1200,
    offensiveRebounding: 1300,
  },
})

/**
 * Step 3 — position-adjusted defensive weights (RATINGS_REHAUL §8, verbatim).
 */
export const DEFENSE_POSITION_WEIGHTS_BPS: Readonly<
  Record<Position, DefenseWeights>
> = freeze({
  PG: {
    perimeterDefense: 3500, offBallDefense: 2500, interiorDefense: 300,
    stealing: 2500, blocking: 200, defensiveRebounding: 1000,
  },
  SG: {
    perimeterDefense: 3000, offBallDefense: 2500, interiorDefense: 700,
    stealing: 2000, blocking: 500, defensiveRebounding: 1300,
  },
  SF: {
    perimeterDefense: 2500, offBallDefense: 2500, interiorDefense: 1500,
    stealing: 1300, blocking: 800, defensiveRebounding: 1400,
  },
  PF: {
    perimeterDefense: 1500, offBallDefense: 2000, interiorDefense: 2500,
    stealing: 800, blocking: 1500, defensiveRebounding: 1700,
  },
  C: {
    perimeterDefense: 500, offBallDefense: 1500, interiorDefense: 3200,
    stealing: 500, blocking: 2500, defensiveRebounding: 1800,
  },
})

/**
 * Step 4 — position-adjusted physical weights (RATINGS_REHAUL §8, verbatim).
 * Functional Size is the derived value; Durability is excluded.
 */
export const PHYSICAL_POSITION_WEIGHTS_BPS: Readonly<
  Record<Position, PhysicalWeights>
> = freeze({
  PG: {
    functionalSize: 500, speed: 2300, agility: 2700, explosiveness: 1500,
    strength: 1000, conditioning: 2000,
  },
  SG: {
    functionalSize: 800, speed: 2100, agility: 2300, explosiveness: 1800,
    strength: 1200, conditioning: 1800,
  },
  SF: {
    functionalSize: 1200, speed: 1800, agility: 2000, explosiveness: 1800,
    strength: 1600, conditioning: 1600,
  },
  PF: {
    functionalSize: 1800, speed: 1200, agility: 1300, explosiveness: 1800,
    strength: 2300, conditioning: 1600,
  },
  C: {
    functionalSize: 2500, speed: 700, agility: 800, explosiveness: 1800,
    strength: 2700, conditioning: 1500,
  },
})

/**
 * Step 5 — position-adjusted mental weights (RATINGS_REHAUL §8, verbatim).
 */
export const MENTAL_POSITION_WEIGHTS_BPS: Readonly<
  Record<Position, MentalWeights>
> = freeze({
  PG: {
    offensiveIQ: 4000, defensiveIQ: 2500, competitiveMakeup: 2000,
    teamLeadership: 1500,
  },
  SG: {
    offensiveIQ: 3500, defensiveIQ: 3000, competitiveMakeup: 2500,
    teamLeadership: 1000,
  },
  SF: {
    offensiveIQ: 3000, defensiveIQ: 3500, competitiveMakeup: 2500,
    teamLeadership: 1000,
  },
  PF: {
    offensiveIQ: 2500, defensiveIQ: 4000, competitiveMakeup: 2500,
    teamLeadership: 1000,
  },
  C: {
    offensiveIQ: 2000, defensiveIQ: 4500, competitiveMakeup: 2500,
    teamLeadership: 1000,
  },
})

/**
 * Step 6 — per-role pillar weights (RATINGS_REHAUL §8, verbatim). Each row sums
 * to exactly 10 000 bps.
 */
export const PILLAR_POSITION_WEIGHTS_BPS: Readonly<
  Record<Position, PillarWeights>
> = freeze({
  PG: { offense: 5000, defense: 1800, physical: 1200, mental: 2000 },
  SG: { offense: 4800, defense: 2200, physical: 1500, mental: 1500 },
  SF: { offense: 4200, defense: 3000, physical: 1500, mental: 1300 },
  PF: { offense: 3600, defense: 3400, physical: 1800, mental: 1200 },
  C: { offense: 3200, defense: 3800, physical: 2000, mental: 1000 },
})

const OFFENSE_CATEGORY_KEYS = Object.keys(
  OFFENSE_POSITION_WEIGHTS_BPS.PG,
) as readonly OffenseCategoryKey[]
const DEFENSE_CATEGORY_KEYS = Object.keys(
  DEFENSE_POSITION_WEIGHTS_BPS.PG,
) as readonly DefenseCategoryKey[]
const MENTAL_CATEGORY_KEYS = Object.keys(
  MENTAL_POSITION_WEIGHTS_BPS.PG,
) as readonly MentalCategoryKey[]

/**
 * The Physical-pillar category scores eligible for the reward-peaks peak
 * (DESIGN_OVERVIEW §6d). Durability is excluded; the derived Functional Size is
 * added to these candidates at the call site.
 */
const PHYSICAL_PEAK_CATEGORY_KEYS = [
  'speed',
  'agility',
  'explosiveness',
  'strength',
  'conditioning',
] as const satisfies readonly DetailedCategoryKey[]

/** Availability weights (ADR 0009 §5): a separate grade, never part of OVR. */
export const AVAILABILITY_INJURY_RESISTANCE_WEIGHT = 0.55
export const AVAILABILITY_LOAD_TOLERANCE_WEIGHT = 0.45

export interface PlayerPillarScores {
  /** Position-adjusted offensive pillar score, full precision. */
  readonly offense: number
  /** Position-adjusted defensive pillar score, full precision. */
  readonly defense: number
  /** Position-adjusted physical pillar score (Functional Size in, Durability out). */
  readonly physical: number
  /** Position-adjusted mental pillar score, full precision. */
  readonly mental: number
}

export interface PositionProfile extends PlayerPillarScores {
  /**
   * Role Fit at this position: the position-pillar-weighted mean of the four
   * pillar scores, full precision. (Formerly `overall`.)
   */
  readonly roleFit: number
  /**
   * The reward-peaks Headline value at this position, full precision. Clamped
   * and rounded only at the player level (`deriveOverall`).
   */
  readonly headline: number
}

interface DerivationInputs {
  readonly ratings: DetailedPlayerRatings
  readonly measurements: PlayerMeasurements
}

const profileCache = new WeakMap<
  DetailedPlayerRatings,
  Map<Position, PositionProfile>
>()

/**
 * The derived Functional Size (0–100, RATINGS_REHAUL §3): a clamped z-score of
 * standing reach, wingspan, and height against the fixed reference set. Never
 * stored; never recomputed against a live-league distribution.
 */
export function deriveFunctionalSize(measurements: PlayerMeasurements): number {
  const zReach = zScore(
    measurements.standingReachInches,
    FUNCTIONAL_SIZE_REFERENCE.standingReachInches,
  )
  const zWingspan = zScore(
    measurements.wingspanInches,
    FUNCTIONAL_SIZE_REFERENCE.wingspanInches,
  )
  const zHeight = zScore(
    measurements.heightInches,
    FUNCTIONAL_SIZE_REFERENCE.heightInches,
  )
  const raw = 50 + 10 * (0.6 * zReach + 0.25 * zWingspan + 0.15 * zHeight)
  return clamp(raw, 0, 100)
}

/**
 * The separate Availability grade input (ADR 0009 §5): a weighted blend of the
 * two Durability sub-ratings. Full precision; never part of OVR. Graded via the
 * shared rating scale by the caller.
 */
export function deriveAvailability(ratings: DetailedPlayerRatings): number {
  return (
    AVAILABILITY_INJURY_RESISTANCE_WEIGHT * ratings.injuryResistance +
    AVAILABILITY_LOAD_TOLERANCE_WEIGHT * ratings.loadTolerance
  )
}

/**
 * The four position-adjusted pillar scores (steps 2–5). The physical pillar
 * substitutes the derived Functional Size for a would-be category and omits
 * Durability, exactly as the healthy-OVR model requires.
 */
export function derivePillarScores(
  ratings: DetailedPlayerRatings,
  measurements: PlayerMeasurements,
  position: Position,
): PlayerPillarScores {
  return derivePositionProfile(ratings, measurements, position)
}

/**
 * Offense / defense / physical / mental / overall at a position, memoized per
 * ratings reference. Grades are always taken from the unrounded scores.
 */
export function derivePositionProfile(
  ratings: DetailedPlayerRatings,
  measurements: PlayerMeasurements,
  position: Position,
): PositionProfile {
  const cached = profileCache.get(ratings)?.get(position)
  if (cached !== undefined) {
    return cached
  }

  const profile = computePositionProfile({ ratings, measurements }, position)
  const byPosition =
    profileCache.get(ratings) ?? new Map<Position, PositionProfile>()
  byPosition.set(position, profile)
  profileCache.set(ratings, byPosition)
  return profile
}

/**
 * Role Fit at a position, rounded for display (formerly `deriveVersionedOverall`).
 * Derived only — never stored, never read by the simulation.
 */
export function deriveRoleFit(
  ratings: DetailedPlayerRatings,
  measurements: PlayerMeasurements,
  position: Position,
): number {
  return Math.round(derivePositionProfile(ratings, measurements, position).roleFit)
}

/**
 * The player's Headline OVR (DESIGN_OVERVIEW §6d, reward-peaks interim):
 * clamp(round(max over eligible roles of the reward-peaks value), 0, 99), where
 * the eligible roles are the primary and secondary positions.
 */
export function deriveOverall(player: {
  readonly ratings: DetailedPlayerRatings
  readonly measurements: PlayerMeasurements
  readonly primaryPosition: Position
  readonly secondaryPosition: Position | null
}): number {
  const roles: readonly Position[] =
    player.secondaryPosition === null
      ? [player.primaryPosition]
      : [player.primaryPosition, player.secondaryPosition]

  const best = roles.reduce((bestHeadline, position) => {
    const headline = derivePositionProfile(
      player.ratings,
      player.measurements,
      position,
    ).headline
    return headline > bestHeadline ? headline : bestHeadline
  }, Number.NEGATIVE_INFINITY)

  return clamp(Math.round(best), 0, 99)
}

function computePositionProfile(
  inputs: DerivationInputs,
  position: Position,
): PositionProfile {
  const scores = deriveAllCategoryScores(inputs.ratings)
  const functionalSize = deriveFunctionalSize(inputs.measurements)

  const offense = weightedCategories(
    scores,
    OFFENSE_POSITION_WEIGHTS_BPS[position],
    OFFENSE_CATEGORY_KEYS,
  )
  const defense = weightedCategories(
    scores,
    DEFENSE_POSITION_WEIGHTS_BPS[position],
    DEFENSE_CATEGORY_KEYS,
  )
  const physical = weightedPhysical(
    scores,
    functionalSize,
    PHYSICAL_POSITION_WEIGHTS_BPS[position],
  )
  const mental = weightedCategories(
    scores,
    MENTAL_POSITION_WEIGHTS_BPS[position],
    MENTAL_CATEGORY_KEYS,
  )

  const pillarWeights = PILLAR_POSITION_WEIGHTS_BPS[position]
  const roleFit = pillarWeightedMean(
    { offense, defense, physical, mental },
    pillarWeights,
  )

  // Reward-peaks: blend each pillar mean with that pillar's single best
  // category, then take the same position-pillar-weighted mean of the blends.
  const headline = pillarWeightedMean(
    {
      offense: pillarPeak(offense, maxCategoryScore(scores, OFFENSE_CATEGORY_KEYS)),
      defense: pillarPeak(defense, maxCategoryScore(scores, DEFENSE_CATEGORY_KEYS)),
      physical: pillarPeak(
        physical,
        Math.max(
          functionalSize,
          maxCategoryScore(scores, PHYSICAL_PEAK_CATEGORY_KEYS),
        ),
      ),
      mental: pillarPeak(mental, maxCategoryScore(scores, MENTAL_CATEGORY_KEYS)),
    },
    pillarWeights,
  )

  return Object.freeze({ offense, defense, physical, mental, roleFit, headline })
}

/** Blends a pillar's position-weighted mean with its single best category. */
function pillarPeak(mean: number, peak: number): number {
  return (1 - PEAK_BLEND) * mean + PEAK_BLEND * peak
}

/** The highest category score among the given category keys. */
function maxCategoryScore(
  scores: Readonly<Record<DetailedCategoryKey, number>>,
  keys: readonly DetailedCategoryKey[],
): number {
  return keys.reduce(
    (best, key) => (scores[key] > best ? scores[key] : best),
    Number.NEGATIVE_INFINITY,
  )
}

/** The position-pillar-weighted mean of the four pillar values. */
function pillarWeightedMean(
  values: PlayerPillarScores,
  weights: PillarWeights,
): number {
  return (
    (values.offense * weights.offense +
      values.defense * weights.defense +
      values.physical * weights.physical +
      values.mental * weights.mental) /
    OVERALL_WEIGHT_TOTAL_BPS
  )
}

function weightedCategories<Key extends DetailedCategoryKey>(
  scores: Readonly<Record<DetailedCategoryKey, number>>,
  weights: Readonly<Record<Key, number>>,
  keys: readonly Key[],
): number {
  const weighted = keys.reduce(
    (total, key) => total + scores[key] * weights[key],
    0,
  )
  return weighted / OVERALL_WEIGHT_TOTAL_BPS
}

function weightedPhysical(
  scores: Readonly<Record<DetailedCategoryKey, number>>,
  functionalSize: number,
  weights: PhysicalWeights,
): number {
  const weighted =
    functionalSize * weights.functionalSize +
    scores.speed * weights.speed +
    scores.agility * weights.agility +
    scores.explosiveness * weights.explosiveness +
    scores.strength * weights.strength +
    scores.conditioning * weights.conditioning
  return weighted / OVERALL_WEIGHT_TOTAL_BPS
}

function zScore(value: number, reference: { mean: number; sd: number }): number {
  return (value - reference.mean) / reference.sd
}

function clamp(value: number, minimum: number, maximum: number): number {
  return Math.min(maximum, Math.max(minimum, value))
}

function freeze<T extends Record<Position, object>>(weights: T): Readonly<T> {
  for (const positionWeights of Object.values(weights)) {
    Object.freeze(positionWeights)
  }
  return Object.freeze(weights)
}
