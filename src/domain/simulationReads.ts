import { SUB_RATING_KEYS } from './detailedRatings'
import type { DetailedPlayerRatings, SubRatingKey } from './detailedRatings'

/**
 * §8C R8 — the frozen simulation rating-read registry (re-derived over the 91
 * base ratings, ADR 0009). The §9 simulation may read player sub-ratings ONLY
 * through these versioned event selectors; it never reads grades, category
 * scores, the display Overall, or the raw record. Each event reads BASE ratings
 * only — never a removed-derived shortcut (interior defense reads
 * verticality/interiorRecovery/paintPositioning/postContainment, never a
 * derived Rim Deterrence; free throws read freeThrowAccuracy/freeThrow
 * Consistency, never a derived Pressure Free Throws). Offensive IQ and
 * Defensive IQ sub-ratings DO enter possession events. Changing any dependency
 * list bumps SIM_RATING_READ_VERSION and is a golden-simulation event.
 * Documented in docs/SIMULATION_MODEL.md; a test keeps code and document in
 * agreement.
 */
export const SIM_RATING_READ_VERSION = 2 as const
export type SimRatingReadVersion = typeof SIM_RATING_READ_VERSION

/**
 * Sub-ratings possession events may never read (ADR 0009 §10):
 * - the two Durability keys — they feed Availability and the injury system only;
 * - the three Team & Leadership keys — they feed morale/development, not shots;
 * - the development/morale-facing Competitive Makeup keys (Competitiveness,
 *   Focus, Resilience) — they feed morale/development, not shot-making.
 * Composure and Motor stay readable: composure enters pressure/late-game
 * events, motor enters hustle/rebounding events.
 */
export const FORBIDDEN_SIM_SUB_RATINGS: readonly SubRatingKey[] =
  Object.freeze([
    // Durability → Availability only
    'injuryResistance',
    'loadTolerance',
    // Team & Leadership → morale/development
    'communication',
    'teamwork',
    'leadership',
    // Development/morale-facing Competitive Makeup
    'competitiveness',
    'focus',
    'resilience',
  ])

export const SIM_EVENT_RATING_READS = freezeEventRatingReads({
  shotSelection: [
    'shotSelection',
    'decisionMaking',
    'offensiveAwareness',
    'spacingReadReact',
  ],
  rimShotResolution: [
    'standingFinish',
    'drivingLayup',
    'contactFinishing',
    'dunking',
  ],
  postScoringResolution: [
    'postControlFootwork',
    'postFinishing',
    'postHookTouch',
    'postFadeaway',
  ],
  midRangeShotResolution: [
    'catchAndShootMid',
    'pullUpMid',
    'movementMid',
    'contestedMid',
  ],
  threePointShotResolution: [
    'catchAndShootThree',
    'pullUpThree',
    'movementThree',
    'contestedThree',
  ],
  freeThrowResolution: ['freeThrowAccuracy', 'freeThrowConsistency'],
  foulDrawingResolution: ['foulDrawing'],
  passResolution: ['passAccuracy', 'courtVision', 'passTiming'],
  turnoverResolution: [
    'ballSecurity',
    'dribbleControl',
    'changeOfDirection',
    'paceControl',
    'decisionMaking',
  ],
  offBallOffenseResolution: [
    'cutTiming',
    'relocation',
    'screenUse',
    'catchSecurity',
  ],
  screeningResolution: ['screenAngle', 'screenTiming', 'rollPopTiming'],
  stealResolution: [
    'onBallSteal',
    'anticipation',
    'deflectionTiming',
    'stripTechnique',
  ],
  blockResolution: [
    'blockTiming',
    'verticality',
    'helpSideBlocking',
    'recoveryChaseDownBlocking',
  ],
  offensiveReboundResolution: [
    'offensivePositioning',
    'reboundPursuit',
    'reboundReading',
    'boxOutEscape',
    'secondJump',
    'motor',
  ],
  defensiveReboundResolution: [
    'defensivePositioning',
    'boxOutTechnique',
    'reboundReading',
    'reboundSecurity',
  ],
  interiorDefenseResolution: [
    'postContainment',
    'paintPositioning',
    'verticality',
    'interiorRecovery',
  ],
  perimeterDefenseResolution: [
    'onBallContainment',
    'lateralRecovery',
    'screenNavigation',
    'closeoutControl',
  ],
  offBallDefenseResolution: [
    'denial',
    'cutterTracking',
    'offBallScreenNavigation',
  ],
  defensiveIQRead: [
    'defensiveAwareness',
    'helpRecognition',
    'rotationDiscipline',
    'foulDiscipline',
  ],
  fatigueResolution: [
    'stamina',
    'recoveryRate',
    'workloadCapacity',
    'composure',
  ],
  physicalMatchup: [
    'acceleration',
    'topSpeed',
    'lateralQuickness',
    'agilityChangeOfDirection',
    'reactiveAgility',
    'firstStepBurst',
    'verticalLeap',
    'bodyControl',
    'lowerBodyStrength',
    'upperBodyStrength',
    'contactBalance',
  ],
} as const satisfies Readonly<Record<string, readonly SubRatingKey[]>>)

export type SimEventKey = keyof typeof SIM_EVENT_RATING_READS

export const SIM_EVENT_KEYS: readonly SimEventKey[] = Object.freeze(
  Object.keys(SIM_EVENT_RATING_READS) as SimEventKey[],
)

const FORBIDDEN_SIM_SUB_RATING_SET = new Set<SubRatingKey>(
  FORBIDDEN_SIM_SUB_RATINGS,
)
const READABLE_SIM_SUB_RATINGS: readonly SubRatingKey[] = Object.freeze(
  SUB_RATING_KEYS.filter((key) => !FORBIDDEN_SIM_SUB_RATING_SET.has(key)),
)

/**
 * The one read path for §9: the unweighted mean of the event's frozen
 * dependency list, full precision. Event formulas (§9) consume this factor;
 * per-dependency weighting inside an event is a §9 decision that would bump
 * SIM_RATING_READ_VERSION.
 */
export function selectSimEventFactor(
  event: SimEventKey,
  ratings: DetailedPlayerRatings,
): number {
  const dependencies = SIM_EVENT_RATING_READS[event]
  const total = dependencies.reduce(
    (sum: number, key: SubRatingKey) => sum + ratings[key],
    0,
  )
  return total / dependencies.length
}

/** Every possession-relevant sub-rating; the forbidden eight are excluded. */
export function listReadableSubRatings(): readonly SubRatingKey[] {
  return READABLE_SIM_SUB_RATINGS
}

function freezeEventRatingReads<
  const Reads extends Readonly<Record<string, readonly SubRatingKey[]>>,
>(reads: Reads): Reads {
  for (const dependencies of Object.values(reads)) {
    Object.freeze(dependencies)
  }
  return Object.freeze(reads)
}
