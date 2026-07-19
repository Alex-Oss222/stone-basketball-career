import { ratingToGrade } from './ratings'
import type { Grade } from './ratings'

/**
 * §8C — the pure detailed-rating domain, rebuilt per ADR 0009 (Accepted
 * 2026-07-19, supersedes ADR 0008): 26 categories in 4 pillars over 91 stored
 * base ratings, weights in integer basis points (never floating-point config).
 * Base ratings are the single source of truth; category scores and letter
 * grades are derived at full precision and never stored. Each stored key
 * carries its Attribute-Framework `code` (the canonical identity the future
 * role-matching profiles threshold on); camelCase remains the persisted key.
 * `reboundReading` is stored once and weighted into both rebounding categories
 * (the sole documented sharing exception). No generation, persistence, or UI
 * lives here.
 *
 * Reserved for later monotonic bumps (not stored yet): the 5 hidden
 * development traits, the 8 hidden health values, and per-rating hidden
 * ceilings (Potential). Measurements and the 16 tendencies are stored on the
 * Player aggregate, not here. Derived display ratings (Pressure Handling, Rim
 * Deterrence, Functional Size, …) are computed by consumers, never stored.
 */

/** Bumps when the stored base-rating record shape changes. */
export const DETAILED_RATINGS_SCHEMA_VERSION = 2 as const
export type DetailedRatingsSchemaVersion =
  typeof DETAILED_RATINGS_SCHEMA_VERSION

/**
 * Bumps when a category, sub-rating, label, or display weight changes.
 * Display weights are presentation config — per ADR 0009 they are versioned
 * separately from any simulation-event weights, so changing a UI weight can
 * never change a game outcome.
 */
export const CATEGORY_DEFINITION_VERSION = 2 as const
export type CategoryDefinitionVersion = typeof CATEGORY_DEFINITION_VERSION

/**
 * Bumps when the deterministic generation formula, calibration, or seed labels
 * change. Lives in the domain so stored players and validation never import
 * from the generation layer; `src/generation/generateDetailedRatings.ts`
 * implements this contract.
 */
export const DETAILED_RATING_GENERATION_VERSION = 2 as const
export type DetailedRatingGenerationVersion =
  typeof DETAILED_RATING_GENERATION_VERSION

export const DETAILED_RATING_MIN = 0
export const DETAILED_RATING_MAX = 100

/** Every category's sub-rating weights must total exactly this. */
export const CATEGORY_WEIGHT_TOTAL_BPS = 10_000

/**
 * The 91 stored base-rating keys — the authoritative order for storage and
 * iteration, grouped by pillar → category. `reboundReading` is stored once
 * (listed under Offensive Rebounding) and weighted into both rebounding
 * categories.
 */
export const SUB_RATING_KEYS = Object.freeze([
  // ── Offense ──────────────────────────────────────────────────────────────
  // Rim Finishing
  'standingFinish',
  'drivingLayup',
  'contactFinishing',
  'dunking',
  'foulDrawing',
  // Post Scoring
  'postControlFootwork',
  'postFinishing',
  'postHookTouch',
  'postFadeaway',
  // Mid-Range Shooting
  'catchAndShootMid',
  'pullUpMid',
  'movementMid',
  'contestedMid',
  // Three-Point Shooting
  'catchAndShootThree',
  'pullUpThree',
  'movementThree',
  'contestedThree',
  // Free-Throw Shooting
  'freeThrowAccuracy',
  'freeThrowConsistency',
  // Passing
  'passAccuracy',
  'courtVision',
  'passTiming',
  // Ball Handling
  'dribbleControl',
  'ballSecurity',
  'changeOfDirection',
  'paceControl',
  // Off-Ball Offense
  'cutTiming',
  'relocation',
  'screenUse',
  'catchSecurity',
  // Screening
  'screenAngle',
  'screenTiming',
  'rollPopTiming',
  // Offensive Rebounding (reboundReading is shared, listed here)
  'offensivePositioning',
  'reboundReading',
  'reboundPursuit',
  'boxOutEscape',
  // ── Defense ──────────────────────────────────────────────────────────────
  // Perimeter Defense
  'onBallContainment',
  'lateralRecovery',
  'screenNavigation',
  'closeoutControl',
  // Off-Ball Defense
  'denial',
  'cutterTracking',
  'offBallScreenNavigation',
  // Interior Defense
  'postContainment',
  'paintPositioning',
  'verticality',
  'interiorRecovery',
  // Stealing
  'onBallSteal',
  'stripTechnique',
  'deflectionTiming',
  // Blocking
  'blockTiming',
  'helpSideBlocking',
  'recoveryChaseDownBlocking',
  // Defensive Rebounding (reboundReading shared, not repeated in the key list)
  'defensivePositioning',
  'boxOutTechnique',
  'reboundSecurity',
  // ── Physical ─────────────────────────────────────────────────────────────
  // Speed
  'acceleration',
  'topSpeed',
  // Agility
  'lateralQuickness',
  'agilityChangeOfDirection',
  'reactiveAgility',
  // Explosiveness & Body Control
  'firstStepBurst',
  'verticalLeap',
  'secondJump',
  'bodyControl',
  // Strength
  'lowerBodyStrength',
  'upperBodyStrength',
  'contactBalance',
  // Conditioning
  'stamina',
  'recoveryRate',
  'workloadCapacity',
  // Durability
  'injuryResistance',
  'loadTolerance',
  // ── Mental ───────────────────────────────────────────────────────────────
  // Offensive IQ
  'offensiveAwareness',
  'shotSelection',
  'decisionMaking',
  'spacingReadReact',
  // Defensive IQ
  'defensiveAwareness',
  'anticipation',
  'helpRecognition',
  'rotationDiscipline',
  'foulDiscipline',
  // Competitive Makeup
  'competitiveness',
  'composure',
  'motor',
  'focus',
  'resilience',
  // Team & Leadership
  'communication',
  'teamwork',
  'leadership',
] as const)

export type SubRatingKey = (typeof SUB_RATING_KEYS)[number]

/** The one sub-rating stored once but weighted into two categories. */
export const SHARED_SUB_RATING_KEY = 'reboundReading' satisfies SubRatingKey

/** The stored record: exactly the 91 base ratings, integers 0–100. */
export type DetailedPlayerRatings = Readonly<Record<SubRatingKey, number>>

export const DETAILED_CATEGORY_KEYS = Object.freeze([
  // Offense
  'rimFinishing',
  'postScoring',
  'midRangeShooting',
  'threePointShooting',
  'freeThrowShooting',
  'passing',
  'ballHandling',
  'offBallOffense',
  'screening',
  'offensiveRebounding',
  // Defense
  'perimeterDefense',
  'offBallDefense',
  'interiorDefense',
  'stealing',
  'blocking',
  'defensiveRebounding',
  // Physical
  'speed',
  'agility',
  'explosiveness',
  'strength',
  'conditioning',
  'durability',
  // Mental
  'offensiveIQ',
  'defensiveIQ',
  'competitiveMakeup',
  'teamLeadership',
] as const)

export type DetailedCategoryKey = (typeof DETAILED_CATEGORY_KEYS)[number]

/** The four OVR pillars. Categories are grouped under exactly one. */
export const DETAILED_CATEGORY_GROUPS = Object.freeze([
  'offense',
  'defense',
  'physical',
  'mental',
] as const)

export type DetailedCategoryGroup = (typeof DETAILED_CATEGORY_GROUPS)[number]

export interface SubRatingWeight {
  readonly key: SubRatingKey
  readonly label: string
  /** Attribute-Framework canonical code (e.g. `OFF_RIM_STANDING_FINISH`). */
  readonly code: string
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
 * The single authoritative registry (ADR 0009). Weights are the V2 starting
 * definition; recalibrating them bumps CATEGORY_DEFINITION_VERSION. `durability`
 * feeds the future injury system and is excluded from OVR (a separate
 * Availability grade); the sim's possession events read base ratings, never a
 * category shortcut.
 */
export const DETAILED_CATEGORY_DEFINITIONS: readonly DetailedCategoryDefinition[] =
  deepFreezeCategories([
    // ── Offense ────────────────────────────────────────────────────────────
    {
      key: 'rimFinishing',
      label: 'Rim Finishing',
      group: 'offense',
      subRatings: [
        { key: 'standingFinish', label: 'Standing Finish', code: 'OFF_RIM_STANDING_FINISH', weightBps: 1500 },
        { key: 'drivingLayup', label: 'Driving Layup', code: 'OFF_RIM_DRIVING_LAYUP', weightBps: 2500 },
        { key: 'contactFinishing', label: 'Contact Finishing', code: 'OFF_RIM_CONTACT_FINISHING', weightBps: 2500 },
        { key: 'dunking', label: 'Dunking', code: 'OFF_RIM_DUNKING', weightBps: 2000 },
        { key: 'foulDrawing', label: 'Foul Drawing', code: 'OFF_RIM_FOUL_DRAWING', weightBps: 1500 },
      ],
    },
    {
      key: 'postScoring',
      label: 'Post Scoring',
      group: 'offense',
      subRatings: [
        { key: 'postControlFootwork', label: 'Post Control & Footwork', code: 'OFF_POST_CONTROL_FOOTWORK', weightBps: 3000 },
        { key: 'postFinishing', label: 'Post Finishing', code: 'OFF_POST_FINISHING', weightBps: 3000 },
        { key: 'postHookTouch', label: 'Post Hook & Touch', code: 'OFF_POST_HOOK_TOUCH', weightBps: 2000 },
        { key: 'postFadeaway', label: 'Post Fadeaway', code: 'OFF_POST_FADEAWAY', weightBps: 2000 },
      ],
    },
    {
      key: 'midRangeShooting',
      label: 'Mid-Range Shooting',
      group: 'offense',
      subRatings: [
        { key: 'catchAndShootMid', label: 'Catch-and-Shoot Mid', code: 'OFF_MID_CATCH_SHOOT', weightBps: 2500 },
        { key: 'pullUpMid', label: 'Pull-Up Mid', code: 'OFF_MID_PULL_UP', weightBps: 3000 },
        { key: 'movementMid', label: 'Movement Mid', code: 'OFF_MID_MOVEMENT', weightBps: 2000 },
        { key: 'contestedMid', label: 'Contested Mid', code: 'OFF_MID_CONTESTED', weightBps: 2500 },
      ],
    },
    {
      key: 'threePointShooting',
      label: 'Three-Point Shooting',
      group: 'offense',
      subRatings: [
        { key: 'catchAndShootThree', label: 'Catch-and-Shoot Three', code: 'OFF_3PT_CATCH_SHOOT', weightBps: 3000 },
        { key: 'pullUpThree', label: 'Pull-Up Three', code: 'OFF_3PT_PULL_UP', weightBps: 2500 },
        { key: 'movementThree', label: 'Movement Three', code: 'OFF_3PT_MOVEMENT', weightBps: 2000 },
        { key: 'contestedThree', label: 'Contested Three', code: 'OFF_3PT_CONTESTED', weightBps: 2500 },
      ],
    },
    {
      key: 'freeThrowShooting',
      label: 'Free-Throw Shooting',
      group: 'offense',
      subRatings: [
        { key: 'freeThrowAccuracy', label: 'Free-Throw Accuracy', code: 'OFF_FT_ACCURACY', weightBps: 8500 },
        { key: 'freeThrowConsistency', label: 'Free-Throw Consistency', code: 'OFF_FT_CONSISTENCY', weightBps: 1500 },
      ],
    },
    {
      key: 'passing',
      label: 'Passing',
      group: 'offense',
      subRatings: [
        { key: 'passAccuracy', label: 'Pass Accuracy', code: 'OFF_PASS_ACCURACY', weightBps: 4000 },
        { key: 'courtVision', label: 'Court Vision', code: 'OFF_PASS_COURT_VISION', weightBps: 3500 },
        { key: 'passTiming', label: 'Pass Timing', code: 'OFF_PASS_TIMING', weightBps: 2500 },
      ],
    },
    {
      key: 'ballHandling',
      label: 'Ball Handling',
      group: 'offense',
      subRatings: [
        { key: 'dribbleControl', label: 'Dribble Control', code: 'OFF_BH_DRIBBLE_CONTROL', weightBps: 3000 },
        { key: 'ballSecurity', label: 'Ball Security', code: 'OFF_BH_BALL_SECURITY', weightBps: 3000 },
        { key: 'changeOfDirection', label: 'Change of Direction', code: 'OFF_BH_CHANGE_DIRECTION', weightBps: 2500 },
        { key: 'paceControl', label: 'Pace Control', code: 'OFF_BH_PACE_CONTROL', weightBps: 1500 },
      ],
    },
    {
      key: 'offBallOffense',
      label: 'Off-Ball Offense',
      group: 'offense',
      subRatings: [
        { key: 'cutTiming', label: 'Cut Timing', code: 'OFF_OFFBALL_CUT_TIMING', weightBps: 3000 },
        { key: 'relocation', label: 'Relocation', code: 'OFF_OFFBALL_RELOCATION', weightBps: 2500 },
        { key: 'screenUse', label: 'Screen Use', code: 'OFF_OFFBALL_SCREEN_USE', weightBps: 2000 },
        { key: 'catchSecurity', label: 'Catch Security', code: 'OFF_OFFBALL_CATCH_SECURITY', weightBps: 2500 },
      ],
    },
    {
      key: 'screening',
      label: 'Screening',
      group: 'offense',
      subRatings: [
        { key: 'screenAngle', label: 'Screen Angle', code: 'OFF_SCREEN_ANGLE', weightBps: 3500 },
        { key: 'screenTiming', label: 'Screen Timing', code: 'OFF_SCREEN_TIMING', weightBps: 3500 },
        { key: 'rollPopTiming', label: 'Roll or Pop Timing', code: 'OFF_SCREEN_ROLL_POP_TIMING', weightBps: 3000 },
      ],
    },
    {
      key: 'offensiveRebounding',
      label: 'Offensive Rebounding',
      group: 'offense',
      subRatings: [
        { key: 'offensivePositioning', label: 'Offensive Positioning', code: 'OFF_OREB_POSITIONING', weightBps: 3000 },
        { key: 'reboundReading', label: 'Rebound Reading', code: 'OFF_OREB_READING', weightBps: 2500 },
        { key: 'reboundPursuit', label: 'Rebound Pursuit', code: 'OFF_OREB_PURSUIT', weightBps: 2500 },
        { key: 'boxOutEscape', label: 'Box-Out Escape', code: 'OFF_OREB_BOXOUT_ESCAPE', weightBps: 2000 },
      ],
    },
    // ── Defense ────────────────────────────────────────────────────────────
    {
      key: 'perimeterDefense',
      label: 'Perimeter Defense',
      group: 'defense',
      subRatings: [
        { key: 'onBallContainment', label: 'On-Ball Containment', code: 'DEF_PERIM_ONBALL_CONTAINMENT', weightBps: 3000 },
        { key: 'lateralRecovery', label: 'Lateral Recovery', code: 'DEF_PERIM_LATERAL_RECOVERY', weightBps: 2500 },
        { key: 'screenNavigation', label: 'Screen Navigation', code: 'DEF_PERIM_SCREEN_NAVIGATION', weightBps: 2500 },
        { key: 'closeoutControl', label: 'Closeout Control', code: 'DEF_PERIM_CLOSEOUT_CONTROL', weightBps: 2000 },
      ],
    },
    {
      key: 'offBallDefense',
      label: 'Off-Ball Defense',
      group: 'defense',
      subRatings: [
        { key: 'denial', label: 'Denial', code: 'DEF_OFFBALL_DENIAL', weightBps: 3500 },
        { key: 'cutterTracking', label: 'Cutter Tracking', code: 'DEF_OFFBALL_CUTTER_TRACKING', weightBps: 3500 },
        { key: 'offBallScreenNavigation', label: 'Off-Ball Screen Navigation', code: 'DEF_OFFBALL_SCREEN_NAVIGATION', weightBps: 3000 },
      ],
    },
    {
      key: 'interiorDefense',
      label: 'Interior Defense',
      group: 'defense',
      subRatings: [
        { key: 'postContainment', label: 'Post Containment', code: 'DEF_INT_POST_CONTAINMENT', weightBps: 3000 },
        { key: 'paintPositioning', label: 'Paint Positioning', code: 'DEF_INT_PAINT_POSITIONING', weightBps: 2500 },
        { key: 'verticality', label: 'Verticality', code: 'DEF_INT_VERTICALITY', weightBps: 2500 },
        { key: 'interiorRecovery', label: 'Interior Recovery', code: 'DEF_INT_RECOVERY', weightBps: 2000 },
      ],
    },
    {
      key: 'stealing',
      label: 'Stealing',
      group: 'defense',
      subRatings: [
        { key: 'onBallSteal', label: 'On-Ball Steal', code: 'DEF_STEAL_ONBALL', weightBps: 3500 },
        { key: 'stripTechnique', label: 'Strip Technique', code: 'DEF_STEAL_STRIP', weightBps: 3000 },
        { key: 'deflectionTiming', label: 'Deflection Timing', code: 'DEF_STEAL_DEFLECTION_TIMING', weightBps: 3500 },
      ],
    },
    {
      key: 'blocking',
      label: 'Blocking',
      group: 'defense',
      subRatings: [
        { key: 'blockTiming', label: 'Block Timing', code: 'DEF_BLOCK_TIMING', weightBps: 4000 },
        { key: 'helpSideBlocking', label: 'Help-Side Blocking', code: 'DEF_BLOCK_HELP_SIDE', weightBps: 3000 },
        { key: 'recoveryChaseDownBlocking', label: 'Recovery & Chase-Down Blocking', code: 'DEF_BLOCK_RECOVERY_CHASEDOWN', weightBps: 3000 },
      ],
    },
    {
      key: 'defensiveRebounding',
      label: 'Defensive Rebounding',
      group: 'defense',
      subRatings: [
        { key: 'defensivePositioning', label: 'Defensive Positioning', code: 'DEF_DREB_POSITIONING', weightBps: 3000 },
        { key: 'boxOutTechnique', label: 'Box-Out Technique', code: 'DEF_DREB_BOXOUT_TECHNIQUE', weightBps: 3000 },
        { key: 'reboundReading', label: 'Rebound Reading', code: 'DEF_DREB_READING', weightBps: 2000 },
        { key: 'reboundSecurity', label: 'Rebound Security', code: 'DEF_DREB_SECURITY', weightBps: 2000 },
      ],
    },
    // ── Physical ───────────────────────────────────────────────────────────
    {
      key: 'speed',
      label: 'Speed',
      group: 'physical',
      subRatings: [
        { key: 'acceleration', label: 'Acceleration', code: 'PHYS_SPEED_ACCELERATION', weightBps: 5000 },
        { key: 'topSpeed', label: 'Top Speed', code: 'PHYS_SPEED_TOP_SPEED', weightBps: 5000 },
      ],
    },
    {
      key: 'agility',
      label: 'Agility',
      group: 'physical',
      subRatings: [
        { key: 'lateralQuickness', label: 'Lateral Quickness', code: 'PHYS_AGILITY_LATERAL_QUICKNESS', weightBps: 4000 },
        { key: 'agilityChangeOfDirection', label: 'Change of Direction', code: 'PHYS_AGILITY_CHANGE_DIRECTION', weightBps: 3500 },
        { key: 'reactiveAgility', label: 'Reactive Agility', code: 'PHYS_AGILITY_REACTIVE', weightBps: 2500 },
      ],
    },
    {
      key: 'explosiveness',
      label: 'Explosiveness & Body Control',
      group: 'physical',
      subRatings: [
        { key: 'firstStepBurst', label: 'First-Step Burst', code: 'PHYS_EXP_FIRST_STEP', weightBps: 3000 },
        { key: 'verticalLeap', label: 'Vertical Leap', code: 'PHYS_EXP_VERTICAL_LEAP', weightBps: 3000 },
        { key: 'secondJump', label: 'Second Jump', code: 'PHYS_EXP_SECOND_JUMP', weightBps: 2000 },
        { key: 'bodyControl', label: 'Body Control', code: 'PHYS_EXP_BODY_CONTROL', weightBps: 2000 },
      ],
    },
    {
      key: 'strength',
      label: 'Strength',
      group: 'physical',
      subRatings: [
        { key: 'lowerBodyStrength', label: 'Lower-Body Strength', code: 'PHYS_STRENGTH_LOWER', weightBps: 4000 },
        { key: 'upperBodyStrength', label: 'Upper-Body Strength', code: 'PHYS_STRENGTH_UPPER', weightBps: 2500 },
        { key: 'contactBalance', label: 'Contact Balance', code: 'PHYS_STRENGTH_CONTACT_BALANCE', weightBps: 3500 },
      ],
    },
    {
      key: 'conditioning',
      label: 'Conditioning',
      group: 'physical',
      subRatings: [
        { key: 'stamina', label: 'Stamina', code: 'PHYS_COND_STAMINA', weightBps: 4500 },
        { key: 'recoveryRate', label: 'Recovery Rate', code: 'PHYS_COND_RECOVERY_RATE', weightBps: 3000 },
        { key: 'workloadCapacity', label: 'Workload Capacity', code: 'PHYS_COND_WORKLOAD', weightBps: 2500 },
      ],
    },
    {
      key: 'durability',
      label: 'Durability',
      group: 'physical',
      subRatings: [
        { key: 'injuryResistance', label: 'Injury Resistance', code: 'PHYS_DUR_INJURY_RESISTANCE', weightBps: 5500 },
        { key: 'loadTolerance', label: 'Load Tolerance', code: 'PHYS_DUR_LOAD_TOLERANCE', weightBps: 4500 },
      ],
    },
    // ── Mental ─────────────────────────────────────────────────────────────
    {
      key: 'offensiveIQ',
      label: 'Offensive IQ',
      group: 'mental',
      subRatings: [
        { key: 'offensiveAwareness', label: 'Offensive Awareness', code: 'MENTAL_OFF_AWARENESS', weightBps: 2500 },
        { key: 'shotSelection', label: 'Shot Selection', code: 'MENTAL_OFF_SHOT_SELECTION', weightBps: 2500 },
        { key: 'decisionMaking', label: 'Decision-Making', code: 'MENTAL_OFF_DECISION_MAKING', weightBps: 3000 },
        { key: 'spacingReadReact', label: 'Spacing & Read-and-React', code: 'MENTAL_OFF_SPACING_READ', weightBps: 2000 },
      ],
    },
    {
      key: 'defensiveIQ',
      label: 'Defensive IQ',
      group: 'mental',
      subRatings: [
        { key: 'defensiveAwareness', label: 'Defensive Awareness', code: 'MENTAL_DEF_AWARENESS', weightBps: 2500 },
        { key: 'anticipation', label: 'Anticipation', code: 'MENTAL_DEF_ANTICIPATION', weightBps: 2000 },
        { key: 'helpRecognition', label: 'Help Recognition', code: 'MENTAL_DEF_HELP_RECOGNITION', weightBps: 2000 },
        { key: 'rotationDiscipline', label: 'Rotation Discipline', code: 'MENTAL_DEF_ROTATION_DISCIPLINE', weightBps: 2000 },
        { key: 'foulDiscipline', label: 'Foul Discipline', code: 'MENTAL_DEF_FOUL_DISCIPLINE', weightBps: 1500 },
      ],
    },
    {
      key: 'competitiveMakeup',
      label: 'Competitive Makeup',
      group: 'mental',
      subRatings: [
        { key: 'competitiveness', label: 'Competitiveness', code: 'MENTAL_COMP_COMPETITIVENESS', weightBps: 2500 },
        { key: 'composure', label: 'Composure', code: 'MENTAL_COMP_COMPOSURE', weightBps: 2500 },
        { key: 'motor', label: 'Motor', code: 'MENTAL_COMP_MOTOR', weightBps: 2000 },
        { key: 'focus', label: 'Focus', code: 'MENTAL_COMP_FOCUS', weightBps: 1500 },
        { key: 'resilience', label: 'Resilience', code: 'MENTAL_COMP_RESILIENCE', weightBps: 1500 },
      ],
    },
    {
      key: 'teamLeadership',
      label: 'Team & Leadership',
      group: 'mental',
      subRatings: [
        { key: 'communication', label: 'Communication', code: 'MENTAL_TEAM_COMMUNICATION', weightBps: 3500 },
        { key: 'teamwork', label: 'Teamwork', code: 'MENTAL_TEAM_TEAMWORK', weightBps: 3500 },
        { key: 'leadership', label: 'Leadership', code: 'MENTAL_TEAM_LEADERSHIP', weightBps: 3000 },
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

/**
 * The canonical Attribute-Framework code for each stored key (first occurrence
 * wins; the shared `reboundReading` maps to its offensive code). This is the
 * stable identity the future role-matching profiles threshold on.
 */
export const SUB_RATING_CODE_BY_KEY: Readonly<Record<SubRatingKey, string>> =
  Object.freeze(
    Object.fromEntries(
      (() => {
        const seen = new Map<SubRatingKey, string>()
        for (const definition of DETAILED_CATEGORY_DEFINITIONS) {
          for (const subRating of definition.subRatings) {
            if (!seen.has(subRating.key)) {
              seen.set(subRating.key, subRating.code)
            }
          }
        }
        return SUB_RATING_KEYS.map((key) => [key, seen.get(key)])
      })(),
    ),
  ) as Readonly<Record<SubRatingKey, string>>

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

/** Validates one stored base rating without coercing or clamping it. */
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

/** Validates the exact persisted 91-base-rating record and rejects extra fields. */
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
  return Object.freeze(
    Object.fromEntries(
      SUB_RATING_KEYS.map((key) => [key, parseDetailedRating(source[key])]),
    ),
  ) as DetailedPlayerRatings
}

/**
 * The weighted category score at full precision — never rounded here. Grades
 * are always taken from the unrounded score (ADR 0009).
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
  return Object.freeze(
    Object.fromEntries(
      DETAILED_CATEGORY_KEYS.map((categoryKey) => [
        categoryKey,
        deriveCategoryScore(ratings, categoryKey),
      ]),
    ),
  ) as Readonly<Record<DetailedCategoryKey, number>>
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
