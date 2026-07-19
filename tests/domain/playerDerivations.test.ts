import { describe, expect, it } from 'vitest'
import {
  SUB_RATING_KEYS,
  parseDetailedPlayerRatings,
} from '../../src/domain/detailedRatings'
import type { SubRatingKey } from '../../src/domain/detailedRatings'
import { POSITIONS } from '../../src/domain/league'
import type { PlayerMeasurements } from '../../src/domain/league'
import {
  DEFENSE_POSITION_WEIGHTS_BPS,
  FUNCTIONAL_SIZE_REFERENCE,
  MENTAL_POSITION_WEIGHTS_BPS,
  OFFENSE_POSITION_WEIGHTS_BPS,
  OVERALL_MODEL_VERSION,
  OVERALL_WEIGHT_TOTAL_BPS,
  PEAK_BLEND,
  PHYSICAL_POSITION_WEIGHTS_BPS,
  PILLAR_POSITION_WEIGHTS_BPS,
  deriveAvailability,
  deriveFunctionalSize,
  deriveOverall,
  derivePositionProfile,
  deriveRoleFit,
} from '../../src/domain/playerDerivations'

function makeRatings(value: number) {
  return parseDetailedPlayerRatings(
    Object.fromEntries(
      SUB_RATING_KEYS.map((key) => [key, value]),
    ) as Record<SubRatingKey, number>,
  )
}

/** Reference-mean measurements — Functional Size derives to exactly 50. */
const REFERENCE_MEASUREMENTS: PlayerMeasurements = {
  heightInches: FUNCTIONAL_SIZE_REFERENCE.heightInches.mean,
  weightPounds: 220,
  wingspanInches: FUNCTIONAL_SIZE_REFERENCE.wingspanInches.mean,
  standingReachInches: FUNCTIONAL_SIZE_REFERENCE.standingReachInches.mean,
  handSizeInches: 9,
}

const WEIGHT_TABLES = [
  OFFENSE_POSITION_WEIGHTS_BPS,
  DEFENSE_POSITION_WEIGHTS_BPS,
  PHYSICAL_POSITION_WEIGHTS_BPS,
  MENTAL_POSITION_WEIGHTS_BPS,
  PILLAR_POSITION_WEIGHTS_BPS,
] as const

describe('4-pillar overall weight tables (RATINGS_REHAUL §8)', () => {
  it('pins the model version and the reward-peaks blend', () => {
    expect(OVERALL_MODEL_VERSION).toBe(3)
    expect(PEAK_BLEND).toBe(0.35)
  })

  it('every step table gives each position positive weights totalling 10 000 bps', () => {
    for (const table of WEIGHT_TABLES) {
      expect(Object.isFrozen(table)).toBe(true)
      for (const position of POSITIONS) {
        const weights = table[position]
        expect(Object.isFrozen(weights)).toBe(true)
        let total = 0
        for (const weight of Object.values(weights) as number[]) {
          expect(Number.isInteger(weight)).toBe(true)
          expect(weight).toBeGreaterThan(0)
          total += weight
        }
        expect(total).toBe(OVERALL_WEIGHT_TOTAL_BPS)
      }
    }
  })

  it('expresses positional emphasis verbatim from the spec tables', () => {
    // Guards create; bigs bang.
    expect(OFFENSE_POSITION_WEIGHTS_BPS.PG.passing).toBe(2500)
    expect(OFFENSE_POSITION_WEIGHTS_BPS.C.passing).toBe(700)
    expect(OFFENSE_POSITION_WEIGHTS_BPS.C.postScoring).toBe(1800)
    expect(DEFENSE_POSITION_WEIGHTS_BPS.C.interiorDefense).toBe(3200)
    expect(DEFENSE_POSITION_WEIGHTS_BPS.PG.perimeterDefense).toBe(3500)
    expect(PHYSICAL_POSITION_WEIGHTS_BPS.C.functionalSize).toBe(2500)
    // Step 6 pillar mix shifts offense→defense from guard to big.
    expect(PILLAR_POSITION_WEIGHTS_BPS.PG.offense).toBe(5000)
    expect(PILLAR_POSITION_WEIGHTS_BPS.C.defense).toBe(3800)
  })
})

describe('derived Functional Size', () => {
  it('is exactly 50 at the reference means', () => {
    expect(deriveFunctionalSize(REFERENCE_MEASUREMENTS)).toBe(50)
  })

  it('rises with length and clamps to [0, 100]', () => {
    const bigger = deriveFunctionalSize({
      ...REFERENCE_MEASUREMENTS,
      standingReachInches: 120,
      wingspanInches: 95,
      heightInches: 90,
    })
    expect(bigger).toBeGreaterThan(50)
    expect(bigger).toBeLessThanOrEqual(100)

    const tiny = deriveFunctionalSize({
      ...REFERENCE_MEASUREMENTS,
      standingReachInches: 60,
      wingspanInches: 60,
      heightInches: 60,
    })
    expect(tiny).toBeGreaterThanOrEqual(0)
    expect(tiny).toBeLessThan(50)
  })
})

describe('derived Availability (out of OVR)', () => {
  it('is the 0.55/0.45 blend of the two Durability sub-ratings', () => {
    const ratings = parseDetailedPlayerRatings({
      ...makeRatings(50),
      injuryResistance: 80,
      loadTolerance: 60,
    })
    expect(deriveAvailability(ratings)).toBeCloseTo(0.55 * 80 + 0.45 * 60, 10)
  })

  it('never depends on the Durability keys inside the OVR', () => {
    const healthy = parseDetailedPlayerRatings({
      ...makeRatings(50),
      injuryResistance: 100,
      loadTolerance: 100,
    })
    const fragile = parseDetailedPlayerRatings({
      ...makeRatings(50),
      injuryResistance: 0,
      loadTolerance: 0,
    })
    for (const position of POSITIONS) {
      const healthyProfile = derivePositionProfile(
        healthy,
        REFERENCE_MEASUREMENTS,
        position,
      )
      const fragileProfile = derivePositionProfile(
        fragile,
        REFERENCE_MEASUREMENTS,
        position,
      )
      expect(healthyProfile.roleFit).toBe(fragileProfile.roleFit)
      expect(healthyProfile.headline).toBe(fragileProfile.headline)
    }
  })
})

describe('position profile and overall', () => {
  it('a uniform-50 record with reference measurements scores 50 everywhere', () => {
    const ratings = makeRatings(50)
    for (const position of POSITIONS) {
      const profile = derivePositionProfile(
        ratings,
        REFERENCE_MEASUREMENTS,
        position,
      )
      expect(profile.offense).toBe(50)
      expect(profile.defense).toBe(50)
      expect(profile.physical).toBe(50)
      expect(profile.mental).toBe(50)
      expect(profile.roleFit).toBe(50)
      expect(profile.headline).toBe(50)
      expect(deriveRoleFit(ratings, REFERENCE_MEASUREMENTS, position)).toBe(50)
    }
  })

  it('is monotonic: raising any sub-rating never lowers any pillar', () => {
    const base = makeRatings(50)
    for (const subRatingKey of ['courtVision', 'blockTiming', 'stamina'] as const) {
      const better = parseDetailedPlayerRatings({
        ...makeRatings(50),
        [subRatingKey]: 90,
      })
      for (const position of POSITIONS) {
        const baseProfile = derivePositionProfile(
          base,
          REFERENCE_MEASUREMENTS,
          position,
        )
        const betterProfile = derivePositionProfile(
          better,
          REFERENCE_MEASUREMENTS,
          position,
        )
        expect(betterProfile.roleFit).toBeGreaterThanOrEqual(
          baseProfile.roleFit,
        )
        expect(betterProfile.headline).toBeGreaterThanOrEqual(
          baseProfile.headline,
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

  it('weights positions differently: a rim protector rates higher at C than PG', () => {
    const rimProtector = parseDetailedPlayerRatings({
      ...makeRatings(50),
      postContainment: 95,
      paintPositioning: 90,
      verticality: 95,
      interiorRecovery: 90,
      blockTiming: 95,
      helpSideBlocking: 90,
      recoveryChaseDownBlocking: 90,
      boxOutTechnique: 90,
      defensivePositioning: 90,
      lowerBodyStrength: 90,
      upperBodyStrength: 90,
      contactBalance: 90,
    })

    expect(
      deriveRoleFit(rimProtector, REFERENCE_MEASUREMENTS, 'C'),
    ).toBeGreaterThan(
      deriveRoleFit(rimProtector, REFERENCE_MEASUREMENTS, 'PG'),
    )
  })

  it('the Headline OVR is clamp(round(max over the eligible roles), 0, 99)', () => {
    const bigSkills = parseDetailedPlayerRatings({
      ...makeRatings(50),
      postControlFootwork: 90,
      postFinishing: 90,
      postHookTouch: 90,
      postFadeaway: 90,
      postContainment: 90,
      paintPositioning: 90,
      verticality: 90,
      interiorRecovery: 90,
      blockTiming: 90,
      helpSideBlocking: 90,
      recoveryChaseDownBlocking: 90,
    })
    const player = {
      ratings: bigSkills,
      measurements: REFERENCE_MEASUREMENTS,
      primaryPosition: 'PG' as const,
      secondaryPosition: 'C' as const,
    }
    const atPG = derivePositionProfile(bigSkills, REFERENCE_MEASUREMENTS, 'PG')
      .headline
    const atC = derivePositionProfile(bigSkills, REFERENCE_MEASUREMENTS, 'C')
      .headline
    // The big role wins, and the Headline OVR is that role's peaks value.
    expect(atC).toBeGreaterThan(atPG)
    expect(deriveOverall(player)).toBe(
      Math.min(99, Math.max(0, Math.round(Math.max(atPG, atC)))),
    )
  })

  it('a single-role player scores at exactly its one role', () => {
    const ratings = makeRatings(64)
    const player = {
      ratings,
      measurements: REFERENCE_MEASUREMENTS,
      primaryPosition: 'SF' as const,
      secondaryPosition: null,
    }
    const atSF = derivePositionProfile(ratings, REFERENCE_MEASUREMENTS, 'SF')
      .headline
    expect(deriveOverall(player)).toBe(
      Math.min(99, Math.max(0, Math.round(atSF))),
    )
  })

  it('the reward-peaks Headline never drops below Role Fit, and a lone peak lifts it', () => {
    // A peak can only add: each pillar peak ≥ its mean, so headline ≥ roleFit.
    for (const value of [40, 55, 70] as const) {
      const ratings = makeRatings(value)
      for (const position of POSITIONS) {
        const profile = derivePositionProfile(
          ratings,
          REFERENCE_MEASUREMENTS,
          position,
        )
        expect(profile.headline).toBeGreaterThanOrEqual(profile.roleFit)
      }
    }

    // One elite category (an offense peak) strictly lifts the Headline.
    const spiky = parseDetailedPlayerRatings({
      ...makeRatings(50),
      catchAndShootThree: 100,
      pullUpThree: 100,
      movementThree: 100,
      contestedThree: 100,
    })
    for (const position of POSITIONS) {
      const profile = derivePositionProfile(
        spiky,
        REFERENCE_MEASUREMENTS,
        position,
      )
      expect(profile.headline).toBeGreaterThan(profile.roleFit)
    }
  })

  it('memoizes per ratings reference without changing results', () => {
    const ratings = makeRatings(71)
    const first = derivePositionProfile(ratings, REFERENCE_MEASUREMENTS, 'SF')
    const second = derivePositionProfile(ratings, REFERENCE_MEASUREMENTS, 'SF')
    expect(second).toBe(first)
    expect(Object.isFrozen(first)).toBe(true)
    const roleFitBefore = first.roleFit
    expect(Reflect.set(first, 'roleFit', 0)).toBe(false)
    expect(first.roleFit).toBe(roleFitBefore)

    const equalButDistinct = makeRatings(71)
    const third = derivePositionProfile(
      equalButDistinct,
      REFERENCE_MEASUREMENTS,
      'SF',
    )
    expect(third).not.toBe(first)
    expect(third).toEqual(first)
  })
})
