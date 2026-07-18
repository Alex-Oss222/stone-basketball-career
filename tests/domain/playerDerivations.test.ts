import { describe, expect, it } from 'vitest'
import {
  SUB_RATING_KEYS,
  parseDetailedPlayerRatings,
} from '../../src/domain/detailedRatings'
import type { SubRatingKey } from '../../src/domain/detailedRatings'
import { POSITIONS } from '../../src/domain/league'
import {
  DEFENSE_CATEGORY_KEYS,
  OFFENSE_CATEGORY_KEYS,
  OVERALL_MODEL_VERSION,
  OVERALL_WEIGHT_TOTAL_BPS,
  POSITION_OVERALL_WEIGHTS_BPS,
  derivePositionProfile,
  deriveVersionedOverall,
} from '../../src/domain/playerDerivations'

function makeRatings(value: number) {
  return parseDetailedPlayerRatings(
    Object.fromEntries(
      SUB_RATING_KEYS.map((key) => [key, value]),
    ) as Record<SubRatingKey, number>,
  )
}

describe('position overall weight tables', () => {
  it('pins the model version', () => {
    expect(OVERALL_MODEL_VERSION).toBe(1)
  })

  it('gives every position positive integer weights totalling exactly 10 000 bps', () => {
    for (const position of POSITIONS) {
      const weights = POSITION_OVERALL_WEIGHTS_BPS[position]
      let total = 0
      for (const weight of Object.values(weights)) {
        expect(Number.isInteger(weight)).toBe(true)
        expect(weight).toBeGreaterThan(0)
        total += weight
      }
      expect(total).toBe(OVERALL_WEIGHT_TOTAL_BPS)
    }
  })

  it('splits offense and defense into disjoint category sets', () => {
    const overlap = OFFENSE_CATEGORY_KEYS.filter((key) =>
      DEFENSE_CATEGORY_KEYS.includes(key),
    )
    expect(overlap).toEqual([])
  })

  it('expresses positional emphasis: creation for guards, interior for bigs', () => {
    expect(POSITION_OVERALL_WEIGHTS_BPS.PG.passing).toBeGreaterThan(
      POSITION_OVERALL_WEIGHTS_BPS.C.passing,
    )
    expect(POSITION_OVERALL_WEIGHTS_BPS.C.interiorDefense).toBeGreaterThan(
      POSITION_OVERALL_WEIGHTS_BPS.PG.interiorDefense,
    )
    expect(POSITION_OVERALL_WEIGHTS_BPS.C.insideScoring).toBeGreaterThan(
      POSITION_OVERALL_WEIGHTS_BPS.PG.insideScoring,
    )
    expect(POSITION_OVERALL_WEIGHTS_BPS.SG.threePointShooting).toBeGreaterThan(
      POSITION_OVERALL_WEIGHTS_BPS.C.threePointShooting,
    )
  })
})

describe('derived overall and position profile', () => {
  it('a uniform record scores that value at every position, in every half', () => {
    const ratings = makeRatings(64)
    for (const position of POSITIONS) {
      const profile = derivePositionProfile(ratings, position)
      expect(profile.overall).toBe(64)
      expect(profile.offense).toBe(64)
      expect(profile.defense).toBe(64)
      expect(deriveVersionedOverall(ratings, position)).toBe(64)
    }
  })

  it('is monotonic: raising any sub-rating never lowers any score', () => {
    const base = makeRatings(50)
    for (const subRatingKey of ['courtVision', 'rimDeterrence', 'stamina'] as const) {
      const better = parseDetailedPlayerRatings({
        ...makeRatings(50),
        [subRatingKey]: 90,
      })
      for (const position of POSITIONS) {
        const baseProfile = derivePositionProfile(base, position)
        const betterProfile = derivePositionProfile(better, position)
        expect(betterProfile.overall).toBeGreaterThanOrEqual(
          baseProfile.overall,
        )
        expect(betterProfile.offense).toBeGreaterThanOrEqual(
          baseProfile.offense,
        )
        expect(betterProfile.defense).toBeGreaterThanOrEqual(
          baseProfile.defense,
        )
      }
    }
  })

  it('weights positions differently: a rim-protector rates higher at C than PG', () => {
    const rimProtector = parseDetailedPlayerRatings({
      ...makeRatings(50),
      rimDeterrence: 95,
      postContainment: 90,
      helpRotation: 90,
      paintPositioning: 90,
      blockTiming: 95,
      verticalContest: 95,
      boxOutTechnique: 90,
      defensivePositioning: 90,
      lowerBodyStrength: 90,
      upperBodyStrength: 90,
      contactBalance: 90,
    })

    expect(
      deriveVersionedOverall(rimProtector, 'C'),
    ).toBeGreaterThan(deriveVersionedOverall(rimProtector, 'PG'))
  })

  it('memoizes per ratings reference without changing results', () => {
    const ratings = makeRatings(71)
    const first = derivePositionProfile(ratings, 'SF')
    const second = derivePositionProfile(ratings, 'SF')
    expect(second).toBe(first)

    const equalButDistinct = makeRatings(71)
    const third = derivePositionProfile(equalButDistinct, 'SF')
    expect(third).not.toBe(first)
    expect(third).toEqual(first)
  })
})
