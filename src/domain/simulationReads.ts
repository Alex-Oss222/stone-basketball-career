import { SUB_RATING_KEYS } from './detailedRatings'
import type { DetailedPlayerRatings, SubRatingKey } from './detailedRatings'

/**
 * §8B R8 — the frozen simulation rating-read registry. The §9 simulation may
 * read player sub-ratings ONLY through these versioned event selectors; it
 * never reads grades, category scores, the display Overall, or the raw
 * record. Durability and Intangibles never enter possession events (ADR 0008
 * review decisions) — they feed only the injury and
 * development/coach-fit/morale systems. Changing any dependency list bumps
 * SIM_RATING_READ_VERSION and is a golden-simulation event. Documented in
 * docs/SIMULATION_MODEL.md; a test keeps code and document in agreement.
 */
export const SIM_RATING_READ_VERSION = 1 as const
export type SimRatingReadVersion = typeof SIM_RATING_READ_VERSION

/** Sub-ratings possession events may never read. */
export const FORBIDDEN_SIM_SUB_RATINGS: readonly SubRatingKey[] =
  Object.freeze([
    'injuryResistance',
    'loadDurability',
    'competitiveness',
    'coachability',
    'composure',
    'workEthic',
  ])

export const SIM_EVENT_RATING_READS = freezeEventRatingReads({
  shotSelection: ['decisionMaking', 'offensiveAwareness'],
  rimShotResolution: [
    'standingFinish',
    'drivingLayup',
    'contactFinishing',
    'dunking',
    'postFinishing',
  ],
  midRangeShotResolution: [
    'catchAndShootMid',
    'pullUpMid',
    'contestedMid',
    'postFadeaway',
  ],
  threePointShotResolution: [
    'catchAndShootThree',
    'pullUpThree',
    'movementThree',
    'contestedThree',
  ],
  freeThrowResolution: [
    'freeThrowAccuracy',
    'freeThrowConsistency',
    'pressureFreeThrows',
  ],
  passResolution: ['passAccuracy', 'courtVision', 'passTiming'],
  turnoverResolution: [
    'ballSecurity',
    'pressureHandling',
    'dribbleControl',
    'changeOfDirection',
    'decisionMaking',
  ],
  stealResolution: [
    'onBallSteal',
    'passingLaneAnticipation',
    'deflectionTiming',
    'stripTechnique',
  ],
  blockResolution: [
    'blockTiming',
    'verticalContest',
    'helpSideBlocking',
    'recoveryBlocking',
  ],
  offensiveReboundResolution: [
    'offensivePositioning',
    'reboundPursuit',
    'reboundReading',
    'secondJump',
  ],
  defensiveReboundResolution: [
    'defensivePositioning',
    'boxOutTechnique',
    'reboundReading',
    'reboundSecurity',
  ],
  interiorDefenseResolution: [
    'postContainment',
    'rimDeterrence',
    'helpRotation',
    'paintPositioning',
  ],
  perimeterDefenseResolution: [
    'onBallContainment',
    'lateralRecovery',
    'screenNavigation',
    'closeoutControl',
  ],
  fatigueResolution: [
    'stamina',
    'recoveryRate',
    'workloadCapacity',
    'lateGameConditioning',
  ],
  physicalMatchup: [
    'acceleration',
    'topSpeed',
    'lateralQuickness',
    'agility',
    'lowerBodyStrength',
    'upperBodyStrength',
    'contactBalance',
    'physicalLeverage',
  ],
  defensiveAwarenessRead: ['defensiveAwareness'],
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

/** Every possession-relevant sub-rating; the forbidden six are excluded. */
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
