import { describe, expect, it } from 'vitest'
import {
  CATEGORY_DEFINITION_VERSION,
  CATEGORY_WEIGHT_TOTAL_BPS,
  DETAILED_CATEGORY_DEFINITIONS,
  DETAILED_CATEGORY_GROUPS,
  DETAILED_CATEGORY_KEYS,
  DETAILED_RATING_MAX,
  DETAILED_RATING_MIN,
  DETAILED_RATINGS_SCHEMA_VERSION,
  SHARED_SUB_RATING_KEY,
  SUB_RATING_KEYS,
  deriveAllCategoryScores,
  deriveCategoryGrade,
  deriveCategoryScore,
  getCategoryDefinition,
  isDetailedCategoryKey,
  isSubRatingKey,
  parseDetailedPlayerRatings,
  parseDetailedRating,
} from '../../src/domain/detailedRatings'
import type {
  DetailedPlayerRatings,
  SubRatingKey,
} from '../../src/domain/detailedRatings'

function makeRatings(value: number): DetailedPlayerRatings {
  return Object.fromEntries(
    SUB_RATING_KEYS.map((key) => [key, value]),
  ) as Record<SubRatingKey, number>
}

describe('detailed-rating registry integrity (ADR 0008)', () => {
  it('locks exactly 18 categories and 67 stored sub-ratings', () => {
    expect(DETAILED_CATEGORY_KEYS).toHaveLength(18)
    expect(DETAILED_CATEGORY_DEFINITIONS).toHaveLength(18)
    expect(SUB_RATING_KEYS).toHaveLength(67)
    expect(new Set(SUB_RATING_KEYS).size).toBe(67)
    expect(new Set(DETAILED_CATEGORY_KEYS).size).toBe(18)
  })

  it('keeps the definition order identical to the canonical key order', () => {
    expect(DETAILED_CATEGORY_DEFINITIONS.map((d) => d.key)).toEqual([
      ...DETAILED_CATEGORY_KEYS,
    ])
  })

  it('references 68 weight slots: every stored key once, reboundReading twice', () => {
    const references = DETAILED_CATEGORY_DEFINITIONS.flatMap((definition) =>
      definition.subRatings.map((subRating) => subRating.key),
    )
    expect(references).toHaveLength(68)

    const counts = new Map<string, number>()
    for (const key of references) {
      counts.set(key, (counts.get(key) ?? 0) + 1)
    }
    for (const key of SUB_RATING_KEYS) {
      expect(counts.get(key)).toBe(key === SHARED_SUB_RATING_KEY ? 2 : 1)
    }
    // The shared key sits in exactly the two rebounding categories.
    const sharingCategories = DETAILED_CATEGORY_DEFINITIONS.filter(
      (definition) =>
        definition.subRatings.some(
          (subRating) => subRating.key === SHARED_SUB_RATING_KEY,
        ),
    ).map((definition) => definition.key)
    expect(sharingCategories).toEqual([
      'offensiveRebounding',
      'defensiveRebounding',
    ])
  })

  it('gives every category positive integer weights totalling exactly 10 000 bps', () => {
    for (const definition of DETAILED_CATEGORY_DEFINITIONS) {
      let total = 0
      for (const subRating of definition.subRatings) {
        expect(Number.isInteger(subRating.weightBps)).toBe(true)
        expect(subRating.weightBps).toBeGreaterThan(0)
        total += subRating.weightBps
      }
      expect(total).toBe(CATEGORY_WEIGHT_TOTAL_BPS)
    }
  })

  it('assigns every category a valid group with the ADR group sizes', () => {
    const groupCounts = new Map<string, number>()
    for (const definition of DETAILED_CATEGORY_DEFINITIONS) {
      expect(DETAILED_CATEGORY_GROUPS).toContain(definition.group)
      groupCounts.set(
        definition.group,
        (groupCounts.get(definition.group) ?? 0) + 1,
      )
    }
    expect(Object.fromEntries(groupCounts)).toEqual({
      scoring: 4,
      creation: 2,
      rebounding: 2,
      defense: 4,
      physical: 4,
      mental: 2,
    })
  })

  it('keeps labels present and unique (Rebound Reading shared aside)', () => {
    const categoryLabels = DETAILED_CATEGORY_DEFINITIONS.map((d) => d.label)
    expect(new Set(categoryLabels).size).toBe(18)

    const subRatingLabels = DETAILED_CATEGORY_DEFINITIONS.flatMap((d) =>
      d.subRatings.map((s) => s.label),
    )
    for (const label of subRatingLabels) {
      expect(label.trim().length).toBeGreaterThan(0)
    }
    const uniqueLabels = new Set(subRatingLabels)
    // 68 references, one duplicated label pair (Rebound Reading).
    expect(uniqueLabels.size).toBe(67)
  })

  it('spot-checks the distinctive ADR weights exactly', () => {
    const weightOf = (category: string, key: SubRatingKey): number | undefined =>
      DETAILED_CATEGORY_DEFINITIONS.find((d) => d.key === category)
        ?.subRatings.find((s) => s.key === key)?.weightBps

    expect(weightOf('freeThrowShooting', 'freeThrowAccuracy')).toBe(7000)
    expect(weightOf('freeThrowShooting', 'pressureFreeThrows')).toBe(1000)
    expect(weightOf('offensiveRebounding', 'reboundReading')).toBe(2500)
    expect(weightOf('defensiveRebounding', 'reboundReading')).toBe(2000)
    expect(weightOf('durability', 'injuryResistance')).toBe(6000)
    expect(weightOf('durability', 'loadDurability')).toBe(4000)
    expect(weightOf('endurance', 'stamina')).toBe(4000)
    expect(weightOf('passing', 'courtVision')).toBe(4000)
    expect(weightOf('basketballIQ', 'decisionMaking')).toBe(3000)
  })

  it('is deeply frozen so no consumer can mutate the taxonomy', () => {
    expect(Object.isFrozen(DETAILED_CATEGORY_DEFINITIONS)).toBe(true)
    for (const definition of DETAILED_CATEGORY_DEFINITIONS) {
      expect(Object.isFrozen(definition)).toBe(true)
      expect(Object.isFrozen(definition.subRatings)).toBe(true)
      for (const subRating of definition.subRatings) {
        expect(Object.isFrozen(subRating)).toBe(true)
      }
    }
  })

  it('pins the R2 version constants and rating bounds', () => {
    expect(DETAILED_RATINGS_SCHEMA_VERSION).toBe(1)
    expect(CATEGORY_DEFINITION_VERSION).toBe(1)
    expect(DETAILED_RATING_MIN).toBe(0)
    expect(DETAILED_RATING_MAX).toBe(100)
    expect(CATEGORY_WEIGHT_TOTAL_BPS).toBe(10_000)
  })
})

/**
 * Independent transcription of ADR 0008 §2 — deliberately duplicated here so
 * a silent edit to the module registry (weights, labels, groups, keys, order)
 * fails against this manifest instead of the code asserting itself. Changing
 * either side is a deliberate act that bumps CATEGORY_DEFINITION_VERSION.
 */
const EXPECTED_SUB_RATING_KEYS = [
  'standingFinish',
  'drivingLayup',
  'contactFinishing',
  'dunking',
  'postFinishing',
  'catchAndShootMid',
  'pullUpMid',
  'contestedMid',
  'postFadeaway',
  'catchAndShootThree',
  'pullUpThree',
  'movementThree',
  'contestedThree',
  'freeThrowAccuracy',
  'freeThrowConsistency',
  'pressureFreeThrows',
  'passAccuracy',
  'courtVision',
  'passTiming',
  'dribbleControl',
  'ballSecurity',
  'changeOfDirection',
  'pressureHandling',
  'offensivePositioning',
  'reboundPursuit',
  'reboundReading',
  'secondJump',
  'defensivePositioning',
  'boxOutTechnique',
  'reboundSecurity',
  'onBallContainment',
  'lateralRecovery',
  'screenNavigation',
  'closeoutControl',
  'postContainment',
  'rimDeterrence',
  'helpRotation',
  'paintPositioning',
  'onBallSteal',
  'passingLaneAnticipation',
  'deflectionTiming',
  'stripTechnique',
  'blockTiming',
  'verticalContest',
  'helpSideBlocking',
  'recoveryBlocking',
  'acceleration',
  'topSpeed',
  'lateralQuickness',
  'agility',
  'lowerBodyStrength',
  'upperBodyStrength',
  'contactBalance',
  'physicalLeverage',
  'stamina',
  'recoveryRate',
  'workloadCapacity',
  'lateGameConditioning',
  'injuryResistance',
  'loadDurability',
  'offensiveAwareness',
  'defensiveAwareness',
  'decisionMaking',
  'competitiveness',
  'coachability',
  'composure',
  'workEthic',
] as const

const EXPECTED_REGISTRY = [
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
      { key: 'pressureFreeThrows', label: 'Pressure Free Throws', weightBps: 1000 },
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
] as const

describe('frozen taxonomy manifest (independent ADR 0008 transcription)', () => {
  it('pins the 67 stored keys, names and order alike', () => {
    expect([...SUB_RATING_KEYS]).toEqual([...EXPECTED_SUB_RATING_KEYS])
  })

  it('pins the 18 category keys in canonical order', () => {
    expect([...DETAILED_CATEGORY_KEYS]).toEqual(
      EXPECTED_REGISTRY.map((category) => category.key),
    )
  })

  it('pins the entire registry — every key, label, group, and weight', () => {
    expect(DETAILED_CATEGORY_DEFINITIONS).toEqual(EXPECTED_REGISTRY)
  })

  it('wires the definition lookup to the matching definition object', () => {
    DETAILED_CATEGORY_DEFINITIONS.forEach((definition, index) => {
      expect(getCategoryDefinition(DETAILED_CATEGORY_KEYS[index])).toBe(
        definition,
      )
      expect(getCategoryDefinition(definition.key).key).toBe(definition.key)
    })
  })
})

describe('detailed-rating key guards', () => {
  it('recognizes every canonical key and rejects strangers', () => {
    for (const key of SUB_RATING_KEYS) {
      expect(isSubRatingKey(key)).toBe(true)
    }
    for (const key of DETAILED_CATEGORY_KEYS) {
      expect(isDetailedCategoryKey(key)).toBe(true)
    }
    expect(isSubRatingKey('insideScoring')).toBe(false) // category, not sub-rating
    expect(isDetailedCategoryKey('standingFinish')).toBe(false)
    expect(isSubRatingKey(42)).toBe(false)
    expect(isDetailedCategoryKey(null)).toBe(false)
  })

  it('getCategoryDefinition throws on an unknown category', () => {
    expect(() =>
      getCategoryDefinition('notACategory' as never),
    ).toThrowError(RangeError)
  })
})

describe('parseDetailedPlayerRatings', () => {
  it('accepts the exact 67-key integer record without mutating it', () => {
    const input = { ...makeRatings(50) }
    const parsed = parseDetailedPlayerRatings(input)

    expect(parsed).toEqual(input)
    expect(parsed).not.toBe(input)
    expect(Reflect.ownKeys(parsed)).toHaveLength(67)
    expect(input.standingFinish).toBe(50)
  })

  it('accepts the boundary values 0 and 100', () => {
    expect(() => parseDetailedPlayerRatings(makeRatings(0))).not.toThrow()
    expect(() => parseDetailedPlayerRatings(makeRatings(100))).not.toThrow()
  })

  it('rejects non-objects', () => {
    for (const bad of [null, undefined, 7, 'ratings', [makeRatings(50)]]) {
      expect(() => parseDetailedPlayerRatings(bad)).toThrowError(TypeError)
    }
  })

  it('rejects a missing sub-rating', () => {
    const incomplete: Record<string, number> = { ...makeRatings(50) }
    delete incomplete.workEthic
    expect(() => parseDetailedPlayerRatings(incomplete)).toThrowError(
      TypeError,
    )
  })

  it('rejects an extra field', () => {
    const extra = { ...makeRatings(50), overall: 90 }
    expect(() => parseDetailedPlayerRatings(extra)).toThrowError(TypeError)
  })

  it('rejects a legacy macro key smuggled in place of a sub-rating', () => {
    const renamed: Record<string, number> = { ...makeRatings(50) }
    delete renamed.standingFinish
    renamed.insideScoring = 50
    expect(() => parseDetailedPlayerRatings(renamed)).toThrowError(TypeError)
  })

  it('rejects non-integer, non-finite, and out-of-range values', () => {
    for (const bad of [50.5, Number.NaN, Infinity, -Infinity, -1, 101]) {
      const record: Record<string, unknown> = { ...makeRatings(50) }
      record.composure = bad
      expect(() => parseDetailedPlayerRatings(record)).toThrowError(
        RangeError,
      )
    }
    const notANumber: Record<string, unknown> = { ...makeRatings(50) }
    notANumber.composure = '50'
    expect(() => parseDetailedPlayerRatings(notANumber)).toThrowError(
      TypeError,
    )
  })

  it('round-trips a record with 67 distinct values exactly', () => {
    const distinct = Object.fromEntries(
      SUB_RATING_KEYS.map((key, index) => [key, index]),
    ) as Record<SubRatingKey, number>
    const parsed = parseDetailedPlayerRatings(distinct)

    expect(parsed).toEqual(distinct)
    for (const [index, key] of SUB_RATING_KEYS.entries()) {
      expect(parsed[key]).toBe(index)
    }
  })

  it('rejects a symbol-keyed extra property', () => {
    const smuggled = { ...makeRatings(50), [Symbol('extra')]: 1 }
    expect(() => parseDetailedPlayerRatings(smuggled)).toThrowError(TypeError)
  })

  it('rejects a non-enumerable extra property', () => {
    const smuggled = Object.defineProperty({ ...makeRatings(50) }, 'extra', {
      value: 1,
      enumerable: false,
    })
    expect(() => parseDetailedPlayerRatings(smuggled)).toThrowError(TypeError)
  })

  it('rejects ratings inherited from the prototype chain', () => {
    const inherited = Object.create(makeRatings(50)) as object
    expect(() => parseDetailedPlayerRatings(inherited)).toThrowError(TypeError)
  })

  it('parseDetailedRating mirrors the stored-rating rules', () => {
    expect(parseDetailedRating(0)).toBe(0)
    expect(parseDetailedRating(100)).toBe(100)
    expect(() => parseDetailedRating('60')).toThrowError(TypeError)
    expect(() => parseDetailedRating(60.5)).toThrowError(RangeError)
  })
})

describe('derived category scores and grades', () => {
  it('a uniform record scores that value in every category', () => {
    const ratings = parseDetailedPlayerRatings(makeRatings(60))
    for (const categoryKey of DETAILED_CATEGORY_KEYS) {
      expect(deriveCategoryScore(ratings, categoryKey)).toBe(60)
      expect(deriveCategoryGrade(ratings, categoryKey)).toBe('C')
    }
  })

  it('computes the weighted score at full precision', () => {
    const ratings = parseDetailedPlayerRatings({
      ...makeRatings(50),
      freeThrowAccuracy: 90,
      freeThrowConsistency: 90,
      pressureFreeThrows: 89,
    })
    // (90·7000 + 90·2000 + 89·1000) / 10000 = 89.9 — never rounded to 90.
    expect(deriveCategoryScore(ratings, 'freeThrowShooting')).toBe(89.9)
  })

  it('grades from the unrounded score, never the rounded one', () => {
    const ratings = parseDetailedPlayerRatings({
      ...makeRatings(50),
      freeThrowAccuracy: 90,
      freeThrowConsistency: 90,
      pressureFreeThrows: 89,
    })
    // 89.9 is A-; grading a rounded 90 would wrongly award A.
    expect(deriveCategoryGrade(ratings, 'freeThrowShooting')).toBe('A-')
  })

  it('the shared Rebound Reading moves both rebounding categories by its weights', () => {
    const base = parseDetailedPlayerRatings(makeRatings(50))
    const better = parseDetailedPlayerRatings({
      ...makeRatings(50),
      reboundReading: 60,
    })

    expect(
      deriveCategoryScore(better, 'offensiveRebounding') -
        deriveCategoryScore(base, 'offensiveRebounding'),
    ).toBeCloseTo(2.5, 10)
    expect(
      deriveCategoryScore(better, 'defensiveRebounding') -
        deriveCategoryScore(base, 'defensiveRebounding'),
    ).toBeCloseTo(2, 10)
    // And nothing outside rebounding moves.
    expect(deriveCategoryScore(better, 'insideScoring')).toBe(50)
  })

  it('deriveAllCategoryScores covers all 18 categories in canonical order', () => {
    const scores = deriveAllCategoryScores(
      parseDetailedPlayerRatings(makeRatings(75)),
    )
    expect(Object.keys(scores)).toEqual([...DETAILED_CATEGORY_KEYS])
    for (const categoryKey of DETAILED_CATEGORY_KEYS) {
      expect(scores[categoryKey]).toBe(75)
    }
  })
})
