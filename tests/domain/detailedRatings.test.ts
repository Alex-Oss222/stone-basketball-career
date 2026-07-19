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
  SUB_RATING_CODE_BY_KEY,
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

describe('detailed-rating registry integrity (ADR 0009)', () => {
  it('locks exactly 26 categories and 91 stored base ratings', () => {
    expect(DETAILED_CATEGORY_KEYS).toHaveLength(26)
    expect(DETAILED_CATEGORY_DEFINITIONS).toHaveLength(26)
    expect(SUB_RATING_KEYS).toHaveLength(91)
    expect(new Set(SUB_RATING_KEYS).size).toBe(91)
    expect(new Set(DETAILED_CATEGORY_KEYS).size).toBe(26)
  })

  it('keeps the definition order identical to the canonical key order', () => {
    expect(DETAILED_CATEGORY_DEFINITIONS.map((d) => d.key)).toEqual([
      ...DETAILED_CATEGORY_KEYS,
    ])
  })

  it('references 92 weight slots: every stored key once, reboundReading twice', () => {
    const references = DETAILED_CATEGORY_DEFINITIONS.flatMap((definition) =>
      definition.subRatings.map((subRating) => subRating.key),
    )
    expect(references).toHaveLength(92)

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

  it('assigns every category to one of four pillars with the ADR group sizes', () => {
    expect([...DETAILED_CATEGORY_GROUPS]).toEqual([
      'offense',
      'defense',
      'physical',
      'mental',
    ])
    const groupCounts = new Map<string, number>()
    for (const definition of DETAILED_CATEGORY_DEFINITIONS) {
      expect(DETAILED_CATEGORY_GROUPS).toContain(definition.group)
      groupCounts.set(
        definition.group,
        (groupCounts.get(definition.group) ?? 0) + 1,
      )
    }
    expect(Object.fromEntries(groupCounts)).toEqual({
      offense: 10,
      defense: 6,
      physical: 6,
      mental: 4,
    })
  })

  it('keeps labels present and unique (Rebound Reading shared aside)', () => {
    const categoryLabels = DETAILED_CATEGORY_DEFINITIONS.map((d) => d.label)
    expect(new Set(categoryLabels).size).toBe(26)

    const subRatingLabels = DETAILED_CATEGORY_DEFINITIONS.flatMap((d) =>
      d.subRatings.map((s) => s.label),
    )
    for (const label of subRatingLabels) {
      expect(label.trim().length).toBeGreaterThan(0)
    }
    const uniqueLabels = new Set(subRatingLabels)
    // 92 references minus two label collisions: Rebound Reading (the shared
    // key, twice) and "Change of Direction" (Ball Handling and Agility both use
    // that label for distinct keys).
    expect(uniqueLabels.size).toBe(90)
  })

  it('spot-checks the distinctive ADR weights exactly', () => {
    const weightOf = (category: string, key: SubRatingKey): number | undefined =>
      DETAILED_CATEGORY_DEFINITIONS.find((d) => d.key === category)
        ?.subRatings.find((s) => s.key === key)?.weightBps

    expect(weightOf('freeThrowShooting', 'freeThrowAccuracy')).toBe(8500)
    expect(weightOf('freeThrowShooting', 'freeThrowConsistency')).toBe(1500)
    expect(weightOf('offensiveRebounding', 'reboundReading')).toBe(2500)
    expect(weightOf('defensiveRebounding', 'reboundReading')).toBe(2000)
    expect(weightOf('durability', 'injuryResistance')).toBe(5500)
    expect(weightOf('durability', 'loadTolerance')).toBe(4500)
    expect(weightOf('conditioning', 'stamina')).toBe(4500)
    expect(weightOf('passing', 'passAccuracy')).toBe(4000)
    expect(weightOf('offensiveIQ', 'decisionMaking')).toBe(3000)
  })

  it('maps every stored key to a unique canonical attribute code (bijection)', () => {
    const codes = SUB_RATING_KEYS.map((key) => SUB_RATING_CODE_BY_KEY[key])
    expect(codes).toHaveLength(91)
    expect(new Set(codes).size).toBe(91)
    for (const code of codes) {
      expect(typeof code).toBe('string')
      expect(code.length).toBeGreaterThan(0)
    }
    // Every registry sub-rating's code matches the registry entry (first-wins
    // for the shared key → its offensive code).
    for (const definition of DETAILED_CATEGORY_DEFINITIONS) {
      for (const subRating of definition.subRatings) {
        if (subRating.key === SHARED_SUB_RATING_KEY) continue
        expect(SUB_RATING_CODE_BY_KEY[subRating.key]).toBe(subRating.code)
      }
    }
    expect(SUB_RATING_CODE_BY_KEY[SHARED_SUB_RATING_KEY]).toBe('OFF_OREB_READING')
  })

  it('is deeply frozen so no consumer can mutate the taxonomy', () => {
    expect(Object.isFrozen(SUB_RATING_KEYS)).toBe(true)
    expect(Object.isFrozen(DETAILED_CATEGORY_KEYS)).toBe(true)
    expect(Object.isFrozen(DETAILED_CATEGORY_GROUPS)).toBe(true)
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
    expect(DETAILED_RATINGS_SCHEMA_VERSION).toBe(2)
    expect(CATEGORY_DEFINITION_VERSION).toBe(2)
    expect(DETAILED_RATING_MIN).toBe(0)
    expect(DETAILED_RATING_MAX).toBe(100)
    expect(CATEGORY_WEIGHT_TOTAL_BPS).toBe(10_000)
  })
})

/**
 * Independent transcription of ADR 0009 §2 — deliberately duplicated here so a
 * silent edit to the module registry (keys, order, groups) fails against this
 * manifest instead of the code asserting itself. Changing either side is a
 * deliberate act that bumps CATEGORY_DEFINITION_VERSION.
 */
const EXPECTED_SUB_RATING_KEYS = [
  // Offense
  'standingFinish',
  'drivingLayup',
  'contactFinishing',
  'dunking',
  'foulDrawing',
  'postControlFootwork',
  'postFinishing',
  'postHookTouch',
  'postFadeaway',
  'catchAndShootMid',
  'pullUpMid',
  'movementMid',
  'contestedMid',
  'catchAndShootThree',
  'pullUpThree',
  'movementThree',
  'contestedThree',
  'freeThrowAccuracy',
  'freeThrowConsistency',
  'passAccuracy',
  'courtVision',
  'passTiming',
  'dribbleControl',
  'ballSecurity',
  'changeOfDirection',
  'paceControl',
  'cutTiming',
  'relocation',
  'screenUse',
  'catchSecurity',
  'screenAngle',
  'screenTiming',
  'rollPopTiming',
  'offensivePositioning',
  'reboundReading',
  'reboundPursuit',
  'boxOutEscape',
  // Defense
  'onBallContainment',
  'lateralRecovery',
  'screenNavigation',
  'closeoutControl',
  'denial',
  'cutterTracking',
  'offBallScreenNavigation',
  'postContainment',
  'paintPositioning',
  'verticality',
  'interiorRecovery',
  'onBallSteal',
  'stripTechnique',
  'deflectionTiming',
  'blockTiming',
  'helpSideBlocking',
  'recoveryChaseDownBlocking',
  'defensivePositioning',
  'boxOutTechnique',
  'reboundSecurity',
  // Physical
  'acceleration',
  'topSpeed',
  'lateralQuickness',
  'agilityChangeOfDirection',
  'reactiveAgility',
  'firstStepBurst',
  'verticalLeap',
  'secondJump',
  'bodyControl',
  'lowerBodyStrength',
  'upperBodyStrength',
  'contactBalance',
  'stamina',
  'recoveryRate',
  'workloadCapacity',
  'injuryResistance',
  'loadTolerance',
  // Mental
  'offensiveAwareness',
  'shotSelection',
  'decisionMaking',
  'spacingReadReact',
  'defensiveAwareness',
  'anticipation',
  'helpRecognition',
  'rotationDiscipline',
  'foulDiscipline',
  'competitiveness',
  'composure',
  'motor',
  'focus',
  'resilience',
  'communication',
  'teamwork',
  'leadership',
] as const

const EXPECTED_CATEGORY_KEYS = [
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
  'perimeterDefense',
  'offBallDefense',
  'interiorDefense',
  'stealing',
  'blocking',
  'defensiveRebounding',
  'speed',
  'agility',
  'explosiveness',
  'strength',
  'conditioning',
  'durability',
  'offensiveIQ',
  'defensiveIQ',
  'competitiveMakeup',
  'teamLeadership',
] as const

describe('frozen taxonomy manifest (independent ADR 0009 transcription)', () => {
  it('pins the 91 stored keys, names and order alike', () => {
    expect([...SUB_RATING_KEYS]).toEqual([...EXPECTED_SUB_RATING_KEYS])
  })

  it('pins the 26 category keys in canonical order', () => {
    expect([...DETAILED_CATEGORY_KEYS]).toEqual([...EXPECTED_CATEGORY_KEYS])
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
    expect(isSubRatingKey('rimFinishing')).toBe(false) // category, not sub-rating
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
  it('accepts the exact 91-key integer record without mutating it', () => {
    const input = { ...makeRatings(50) }
    const parsed = parseDetailedPlayerRatings(input)

    expect(parsed).toEqual(input)
    expect(parsed).not.toBe(input)
    expect(Object.isFrozen(parsed)).toBe(true)
    expect(Reflect.set(parsed, 'standingFinish', 99)).toBe(false)
    expect(parsed.standingFinish).toBe(50)
    expect(Reflect.ownKeys(parsed)).toHaveLength(91)
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
    delete incomplete.leadership
    expect(() => parseDetailedPlayerRatings(incomplete)).toThrowError(
      TypeError,
    )
  })

  it('rejects an extra field', () => {
    const extra = { ...makeRatings(50), overall: 90 }
    expect(() => parseDetailedPlayerRatings(extra)).toThrowError(TypeError)
  })

  it('rejects a legacy sub-rating smuggled in place of a current one', () => {
    const renamed: Record<string, number> = { ...makeRatings(50) }
    delete renamed.loadTolerance
    renamed.loadDurability = 50
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

  it('round-trips a record with 91 distinct values exactly', () => {
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
      freeThrowConsistency: 89,
    })
    // (90·8500 + 89·1500) / 10000 = 89.85 — never rounded.
    expect(deriveCategoryScore(ratings, 'freeThrowShooting')).toBe(89.85)
  })

  it('grades from the unrounded score, never the rounded one', () => {
    const ratings = parseDetailedPlayerRatings({
      ...makeRatings(50),
      freeThrowAccuracy: 90,
      freeThrowConsistency: 89,
    })
    // 89.85 is A-; grading a rounded 90 would wrongly award A.
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
    expect(deriveCategoryScore(better, 'rimFinishing')).toBe(50)
  })

  it('deriveAllCategoryScores covers all 26 categories in canonical order', () => {
    const scores = deriveAllCategoryScores(
      parseDetailedPlayerRatings(makeRatings(75)),
    )
    expect(Object.keys(scores)).toEqual([...DETAILED_CATEGORY_KEYS])
    expect(Object.isFrozen(scores)).toBe(true)
    expect(Reflect.set(scores, 'rimFinishing', 0)).toBe(false)
    for (const categoryKey of DETAILED_CATEGORY_KEYS) {
      expect(scores[categoryKey]).toBe(75)
    }
  })
})
