import { ratingToGrade } from './ratings'
import type { Grade } from './ratings'

/**
 * §8B R2 — the pure detailed-rating domain, transcribed from ADR 0008
 * (Accepted 2026-07-17): 18 categories, 67 stored sub-ratings, weights in
 * integer basis points (never floating-point config). Sub-ratings are the
 * single source of truth; category scores and letter grades are derived at
 * full precision and never stored. No generation (R3), no persistence (R4),
 * no UI (R5/R6) lives here.
 */

/** Bumps when the stored sub-rating record shape changes. */
export const DETAILED_RATINGS_SCHEMA_VERSION = 1 as const
export type DetailedRatingsSchemaVersion =
  typeof DETAILED_RATINGS_SCHEMA_VERSION

/**
 * Bumps when a category, sub-rating, label, or display weight changes.
 * Display weights are presentation config — per ADR 0008 §4 they are
 * versioned separately from any simulation-event weights, so changing a UI
 * weight can never change a game outcome.
 */
export const CATEGORY_DEFINITION_VERSION = 1 as const
export type CategoryDefinitionVersion = typeof CATEGORY_DEFINITION_VERSION

/**
 * Bumps when the deterministic generation formula, calibration, or seed
 * labels change (ADR 0008 §5). Lives in the domain like the legacy
 * RATING_GENERATION_VERSION so stored players and validation never import
 * from the generation layer; `src/generation/generateDetailedRatings.ts`
 * implements this contract.
 */
export const DETAILED_RATING_GENERATION_VERSION = 1 as const
export type DetailedRatingGenerationVersion =
  typeof DETAILED_RATING_GENERATION_VERSION

export const DETAILED_RATING_MIN = 0
export const DETAILED_RATING_MAX = 100

/** Every category's sub-rating weights must total exactly this. */
export const CATEGORY_WEIGHT_TOTAL_BPS = 10_000

/**
 * The 67 stored sub-rating keys — the authoritative order for storage and
 * iteration. `reboundReading` is stored once and weighted into both
 * rebounding categories (the sole documented sharing exception).
 */
export const SUB_RATING_KEYS = [
  // Scoring — Inside Scoring
  'standingFinish',
  'drivingLayup',
  'contactFinishing',
  'dunking',
  'postFinishing',
  // Scoring — Mid-Range Shooting
  'catchAndShootMid',
  'pullUpMid',
  'contestedMid',
  'postFadeaway',
  // Scoring — Three-Point Shooting
  'catchAndShootThree',
  'pullUpThree',
  'movementThree',
  'contestedThree',
  // Scoring — Free-Throw Shooting
  'freeThrowAccuracy',
  'freeThrowConsistency',
  'pressureFreeThrows',
  // Creation — Passing
  'passAccuracy',
  'courtVision',
  'passTiming',
  // Creation — Ball Handling
  'dribbleControl',
  'ballSecurity',
  'changeOfDirection',
  'pressureHandling',
  // Rebounding — Offensive Rebounding
  'offensivePositioning',
  'reboundPursuit',
  'reboundReading',
  'secondJump',
  // Rebounding — Defensive Rebounding (reboundReading is shared, not repeated)
  'defensivePositioning',
  'boxOutTechnique',
  'reboundSecurity',
  // Defense — Perimeter Defense
  'onBallContainment',
  'lateralRecovery',
  'screenNavigation',
  'closeoutControl',
  // Defense — Interior Defense
  'postContainment',
  'rimDeterrence',
  'helpRotation',
  'paintPositioning',
  // Defense — Stealing
  'onBallSteal',
  'passingLaneAnticipation',
  'deflectionTiming',
  'stripTechnique',
  // Defense — Blocking
  'blockTiming',
  'verticalContest',
  'helpSideBlocking',
  'recoveryBlocking',
  // Physical — Speed
  'acceleration',
  'topSpeed',
  'lateralQuickness',
  'agility',
  // Physical — Strength
  'lowerBodyStrength',
  'upperBodyStrength',
  'contactBalance',
  'physicalLeverage',
  // Physical — Endurance
  'stamina',
  'recoveryRate',
  'workloadCapacity',
  'lateGameConditioning',
  // Physical — Durability
  'injuryResistance',
  'loadDurability',
  // Mental — Basketball IQ
  'offensiveAwareness',
  'defensiveAwareness',
  'decisionMaking',
  // Mental — Intangibles
  'competitiveness',
  'coachability',
  'composure',
  'workEthic',
] as const

export type SubRatingKey = (typeof SUB_RATING_KEYS)[number]

/** The one sub-rating stored once but weighted into two categories. */
export const SHARED_SUB_RATING_KEY = 'reboundReading' satisfies SubRatingKey

/** The stored record: exactly the 67 sub-ratings, integers 0–100. */
export type DetailedPlayerRatings = Readonly<Record<SubRatingKey, number>>

export const DETAILED_CATEGORY_KEYS = [
  'insideScoring',
  'midRangeShooting',
  'threePointShooting',
  'freeThrowShooting',
  'passing',
  'ballHandling',
  'offensiveRebounding',
  'defensiveRebounding',
  'perimeterDefense',
  'interiorDefense',
  'stealing',
  'blocking',
  'speed',
  'strength',
  'endurance',
  'durability',
  'basketballIQ',
  'intangibles',
] as const

export type DetailedCategoryKey = (typeof DETAILED_CATEGORY_KEYS)[number]

export const DETAILED_CATEGORY_GROUPS = [
  'scoring',
  'creation',
  'rebounding',
  'defense',
  'physical',
  'mental',
] as const

export type DetailedCategoryGroup = (typeof DETAILED_CATEGORY_GROUPS)[number]

export interface SubRatingWeight {
  readonly key: SubRatingKey
  readonly label: string
  /** Integer basis points; a category's weights total exactly 10 000. */
  readonly weightBps: number
}

export interface DetailedCategoryDefinition {
  readonly key: DetailedCategoryKey
  readonly label: string
  readonly group: DetailedCategoryGroup
  readonly subRatings: readonly SubRatingWeight[]
}

/**
 * The single authoritative registry (ADR 0008 §2). Weights are the V1
 * starting definition; recalibrating them bumps CATEGORY_DEFINITION_VERSION.
 * `durability` feeds the future injury system and `intangibles` feeds
 * development/coach-fit/morale — the simulation's possession events never
 * read either (ADR 0008 review decisions).
 */
export const DETAILED_CATEGORY_DEFINITIONS: readonly DetailedCategoryDefinition[] =
  deepFreezeCategories([
    {
      key: 'insideScoring',
      label: 'Inside Scoring',
      group: 'scoring',
      subRatings: [
        { key: 'standingFinish', label: 'Standing Finish', weightBps: 1500 },
        { key: 'drivingLayup', label: 'Driving Layup', weightBps: 2500 },
        { key: 'contactFinishing', label: 'Contact Finishing', weightBps: 2500 },
        { key: 'dunking', label: 'Dunking', weightBps: 1500 },
        { key: 'postFinishing', label: 'Post Finishing', weightBps: 2000 },
      ],
    },
    {
      key: 'midRangeShooting',
      label: 'Mid-Range Shooting',
      group: 'scoring',
      subRatings: [
        { key: 'catchAndShootMid', label: 'Catch-and-Shoot Mid', weightBps: 2500 },
        { key: 'pullUpMid', label: 'Pull-Up Mid', weightBps: 3000 },
        { key: 'contestedMid', label: 'Contested Mid', weightBps: 2500 },
        { key: 'postFadeaway', label: 'Post Fadeaway', weightBps: 2000 },
      ],
    },
    {
      key: 'threePointShooting',
      label: 'Three-Point Shooting',
      group: 'scoring',
      subRatings: [
        {
          key: 'catchAndShootThree',
          label: 'Catch-and-Shoot Three',
          weightBps: 3000,
        },
        { key: 'pullUpThree', label: 'Pull-Up Three', weightBps: 2500 },
        { key: 'movementThree', label: 'Movement Three', weightBps: 2000 },
        { key: 'contestedThree', label: 'Contested Three', weightBps: 2500 },
      ],
    },
    {
      key: 'freeThrowShooting',
      label: 'Free-Throw Shooting',
      group: 'scoring',
      subRatings: [
        { key: 'freeThrowAccuracy', label: 'Free-Throw Accuracy', weightBps: 7000 },
        {
          key: 'freeThrowConsistency',
          label: 'Free-Throw Consistency',
          weightBps: 2000,
        },
        {
          key: 'pressureFreeThrows',
          label: 'Pressure Free Throws',
          weightBps: 1000,
        },
      ],
    },
    {
      key: 'passing',
      label: 'Passing',
      group: 'creation',
      subRatings: [
        { key: 'passAccuracy', label: 'Pass Accuracy', weightBps: 3500 },
        { key: 'courtVision', label: 'Court Vision', weightBps: 4000 },
        { key: 'passTiming', label: 'Pass Timing', weightBps: 2500 },
      ],
    },
    {
      key: 'ballHandling',
      label: 'Ball Handling',
      group: 'creation',
      subRatings: [
        { key: 'dribbleControl', label: 'Dribble Control', weightBps: 2500 },
        { key: 'ballSecurity', label: 'Ball Security', weightBps: 3000 },
        { key: 'changeOfDirection', label: 'Change of Direction', weightBps: 2000 },
        { key: 'pressureHandling', label: 'Pressure Handling', weightBps: 2500 },
      ],
    },
    {
      key: 'offensiveRebounding',
      label: 'Offensive Rebounding',
      group: 'rebounding',
      subRatings: [
        {
          key: 'offensivePositioning',
          label: 'Offensive Positioning',
          weightBps: 3000,
        },
        { key: 'reboundPursuit', label: 'Rebound Pursuit', weightBps: 2500 },
        { key: 'reboundReading', label: 'Rebound Reading', weightBps: 2500 },
        { key: 'secondJump', label: 'Second Jump', weightBps: 2000 },
      ],
    },
    {
      key: 'defensiveRebounding',
      label: 'Defensive Rebounding',
      group: 'rebounding',
      subRatings: [
        {
          key: 'defensivePositioning',
          label: 'Defensive Positioning',
          weightBps: 2500,
        },
        { key: 'boxOutTechnique', label: 'Box-Out Technique', weightBps: 3000 },
        { key: 'reboundReading', label: 'Rebound Reading', weightBps: 2000 },
        { key: 'reboundSecurity', label: 'Rebound Security', weightBps: 2500 },
      ],
    },
    {
      key: 'perimeterDefense',
      label: 'Perimeter Defense',
      group: 'defense',
      subRatings: [
        { key: 'onBallContainment', label: 'On-Ball Containment', weightBps: 3000 },
        { key: 'lateralRecovery', label: 'Lateral Recovery', weightBps: 2500 },
        { key: 'screenNavigation', label: 'Screen Navigation', weightBps: 2000 },
        { key: 'closeoutControl', label: 'Closeout Control', weightBps: 2500 },
      ],
    },
    {
      key: 'interiorDefense',
      label: 'Interior Defense',
      group: 'defense',
      subRatings: [
        { key: 'postContainment', label: 'Post Containment', weightBps: 2500 },
        { key: 'rimDeterrence', label: 'Rim Deterrence', weightBps: 3000 },
        { key: 'helpRotation', label: 'Help Rotation', weightBps: 2500 },
        { key: 'paintPositioning', label: 'Paint Positioning', weightBps: 2000 },
      ],
    },
    {
      key: 'stealing',
      label: 'Stealing',
      group: 'defense',
      subRatings: [
        { key: 'onBallSteal', label: 'On-Ball Steal', weightBps: 2500 },
        {
          key: 'passingLaneAnticipation',
          label: 'Passing-Lane Anticipation',
          weightBps: 3000,
        },
        { key: 'deflectionTiming', label: 'Deflection Timing', weightBps: 2500 },
        { key: 'stripTechnique', label: 'Strip Technique', weightBps: 2000 },
      ],
    },
    {
      key: 'blocking',
      label: 'Blocking',
      group: 'defense',
      subRatings: [
        { key: 'blockTiming', label: 'Block Timing', weightBps: 3000 },
        { key: 'verticalContest', label: 'Vertical Contest', weightBps: 2500 },
        { key: 'helpSideBlocking', label: 'Help-Side Blocking', weightBps: 2500 },
        { key: 'recoveryBlocking', label: 'Recovery Blocking', weightBps: 2000 },
      ],
    },
    {
      key: 'speed',
      label: 'Speed',
      group: 'physical',
      subRatings: [
        { key: 'acceleration', label: 'Acceleration', weightBps: 3000 },
        { key: 'topSpeed', label: 'Top Speed', weightBps: 2500 },
        { key: 'lateralQuickness', label: 'Lateral Quickness', weightBps: 2500 },
        { key: 'agility', label: 'Agility', weightBps: 2000 },
      ],
    },
    {
      key: 'strength',
      label: 'Strength',
      group: 'physical',
      subRatings: [
        { key: 'lowerBodyStrength', label: 'Lower-Body Strength', weightBps: 2500 },
        { key: 'upperBodyStrength', label: 'Upper-Body Strength', weightBps: 2000 },
        { key: 'contactBalance', label: 'Contact Balance', weightBps: 3000 },
        { key: 'physicalLeverage', label: 'Physical Leverage', weightBps: 2500 },
      ],
    },
    {
      key: 'endurance',
      label: 'Endurance',
      group: 'physical',
      subRatings: [
        { key: 'stamina', label: 'Stamina', weightBps: 4000 },
        { key: 'recoveryRate', label: 'Recovery Rate', weightBps: 2500 },
        { key: 'workloadCapacity', label: 'Workload Capacity', weightBps: 2000 },
        {
          key: 'lateGameConditioning',
          label: 'Late-Game Conditioning',
          weightBps: 1500,
        },
      ],
    },
    {
      key: 'durability',
      label: 'Durability',
      group: 'physical',
      subRatings: [
        { key: 'injuryResistance', label: 'Injury Resistance', weightBps: 6000 },
        { key: 'loadDurability', label: 'Load Durability', weightBps: 4000 },
      ],
    },
    {
      key: 'basketballIQ',
      label: 'Basketball IQ',
      group: 'mental',
      subRatings: [
        { key: 'offensiveAwareness', label: 'Offensive Awareness', weightBps: 3500 },
        { key: 'defensiveAwareness', label: 'Defensive Awareness', weightBps: 3500 },
        { key: 'decisionMaking', label: 'Decision-Making', weightBps: 3000 },
      ],
    },
    {
      key: 'intangibles',
      label: 'Intangibles',
      group: 'mental',
      subRatings: [
        { key: 'competitiveness', label: 'Competitiveness', weightBps: 3000 },
        { key: 'coachability', label: 'Coachability', weightBps: 2500 },
        { key: 'composure', label: 'Composure', weightBps: 2500 },
        { key: 'workEthic', label: 'Work Ethic', weightBps: 2000 },
      ],
    },
  ])

const CATEGORY_DEFINITIONS_BY_KEY: ReadonlyMap<
  DetailedCategoryKey,
  DetailedCategoryDefinition
> = new Map(
  DETAILED_CATEGORY_DEFINITIONS.map((definition) => [
    definition.key,
    definition,
  ]),
)

const SUB_RATING_KEY_SET: ReadonlySet<string> = new Set(SUB_RATING_KEYS)
const DETAILED_CATEGORY_KEY_SET: ReadonlySet<string> = new Set(
  DETAILED_CATEGORY_KEYS,
)

export function isSubRatingKey(value: unknown): value is SubRatingKey {
  return typeof value === 'string' && SUB_RATING_KEY_SET.has(value)
}

export function isDetailedCategoryKey(
  value: unknown,
): value is DetailedCategoryKey {
  return typeof value === 'string' && DETAILED_CATEGORY_KEY_SET.has(value)
}

export function getCategoryDefinition(
  categoryKey: DetailedCategoryKey,
): DetailedCategoryDefinition {
  const definition = CATEGORY_DEFINITIONS_BY_KEY.get(categoryKey)
  if (definition === undefined) {
    throw new RangeError(`Unknown detailed category: ${String(categoryKey)}`)
  }
  return definition
}

export function isDetailedRating(value: unknown): value is number {
  return (
    typeof value === 'number' &&
    Number.isFinite(value) &&
    Number.isInteger(value) &&
    value >= DETAILED_RATING_MIN &&
    value <= DETAILED_RATING_MAX
  )
}

/** Validates one stored sub-rating without coercing or clamping it. */
export function parseDetailedRating(value: unknown): number {
  if (typeof value !== 'number') {
    throw new TypeError('Detailed rating must be a number')
  }
  if (!isDetailedRating(value)) {
    throw new RangeError(
      `Detailed rating must be a finite integer from ${DETAILED_RATING_MIN} through ${DETAILED_RATING_MAX}`,
    )
  }
  return value
}

/** Validates the exact persisted 67-sub-rating record and rejects extra fields. */
export function parseDetailedPlayerRatings(
  value: unknown,
): DetailedPlayerRatings {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    throw new TypeError('Detailed player ratings must be an object')
  }

  const ownKeys = Reflect.ownKeys(value)
  if (
    ownKeys.length !== SUB_RATING_KEYS.length ||
    ownKeys.some((key) => !isSubRatingKey(key))
  ) {
    throw new TypeError(
      'Detailed player ratings must contain exactly the stored sub-rating keys',
    )
  }

  const source = value as Record<SubRatingKey, unknown>
  return Object.fromEntries(
    SUB_RATING_KEYS.map((key) => [key, parseDetailedRating(source[key])]),
  ) as DetailedPlayerRatings
}

/**
 * The weighted category score at full precision — never rounded here. Grades
 * are always taken from the unrounded score (ADR 0008 §3).
 */
export function deriveCategoryScore(
  ratings: DetailedPlayerRatings,
  categoryKey: DetailedCategoryKey,
): number {
  const definition = getCategoryDefinition(categoryKey)
  const weighted = definition.subRatings.reduce(
    (total, subRating) => total + ratings[subRating.key] * subRating.weightBps,
    0,
  )
  return weighted / CATEGORY_WEIGHT_TOTAL_BPS
}

export function deriveAllCategoryScores(
  ratings: DetailedPlayerRatings,
): Readonly<Record<DetailedCategoryKey, number>> {
  return Object.fromEntries(
    DETAILED_CATEGORY_KEYS.map((categoryKey) => [
      categoryKey,
      deriveCategoryScore(ratings, categoryKey),
    ]),
  ) as Record<DetailedCategoryKey, number>
}

/** Letter grade from the unrounded category score, via the one grade scale. */
export function deriveCategoryGrade(
  ratings: DetailedPlayerRatings,
  categoryKey: DetailedCategoryKey,
): Grade {
  return ratingToGrade(deriveCategoryScore(ratings, categoryKey))
}

function deepFreezeCategories(
  definitions: readonly DetailedCategoryDefinition[],
): readonly DetailedCategoryDefinition[] {
  for (const definition of definitions) {
    for (const subRating of definition.subRatings) {
      Object.freeze(subRating)
    }
    Object.freeze(definition.subRatings)
    Object.freeze(definition)
  }
  return Object.freeze(definitions)
}
