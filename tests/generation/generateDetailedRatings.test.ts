import { describe, expect, it } from 'vitest'
import {
  DETAILED_CATEGORY_DEFINITIONS,
  DETAILED_CATEGORY_KEYS,
  SUB_RATING_KEYS,
  deriveCategoryScore,
  parseDetailedPlayerRatings,
} from '../../src/domain/detailedRatings'
import type { DetailedPlayerRatings } from '../../src/domain/detailedRatings'
import { parsePlayerId } from '../../src/domain/ids'
import { POSITIONS } from '../../src/domain/league'
import type { Position } from '../../src/domain/league'
import {
  CATEGORY_APTITUDE_SPREAD,
  DETAILED_RATING_GENERATION_VERSION,
  FIELD_VARIATION_SPREAD,
  POSITION_CATEGORY_BIASES,
  QUALITY_BASELINE_MAX,
  QUALITY_BASELINE_MIN,
  deriveDetailedCategorySeed,
  deriveDetailedQualitySeed,
  deriveDetailedSkillSeed,
  generateCategoryAptitude,
  generateDetailedPlayerRatings,
  generateDetailedRating,
  generateFieldVariation,
  generateQualityBaseline,
} from '../../src/generation/generateDetailedRatings'
import { deriveSeed } from '../../src/random/seed'
import { createRandomSource } from '../../src/random/xoshiro128ss'

const LEAGUE_SEED = 'r3-golden-league-seed'

const GOLDEN_PLAYER_IDS = {
  PG: parsePlayerId('player_r3golden_pg'),
  SG: parsePlayerId('player_r3golden_sg'),
  SF: parsePlayerId('player_r3golden_sf'),
  PF: parsePlayerId('player_r3golden_pf'),
  C: parsePlayerId('player_r3golden_c'),
} as const

/**
 * Golden vectors — full 91-value outputs pinned for one player per position
 * under DETAILED_RATING_GENERATION_VERSION 2. An intentional generator change
 * must bump the version and deliberately regenerate these; an accidental
 * change fails here.
 */
const GOLDEN_VECTORS: Readonly<Record<Position, DetailedPlayerRatings>> = {
  PG: {
    standingFinish: 63, drivingLayup: 65, contactFinishing: 71, dunking: 61, foulDrawing: 72, postControlFootwork: 45,
    postFinishing: 56, postHookTouch: 56, postFadeaway: 55, catchAndShootMid: 71, pullUpMid: 73, movementMid: 74,
    contestedMid: 77, catchAndShootThree: 78, pullUpThree: 68, movementThree: 70, contestedThree: 78, freeThrowAccuracy: 73,
    freeThrowConsistency: 64, passAccuracy: 78, courtVision: 85, passTiming: 85, dribbleControl: 86, ballSecurity: 81,
    changeOfDirection: 89, paceControl: 93, cutTiming: 62, relocation: 66, screenUse: 64, catchSecurity: 68,
    screenAngle: 58, screenTiming: 57, rollPopTiming: 53, offensivePositioning: 69, reboundReading: 68, reboundPursuit: 61,
    boxOutEscape: 65, onBallContainment: 76, lateralRecovery: 85, screenNavigation: 86, closeoutControl: 78, denial: 65,
    cutterTracking: 71, offBallScreenNavigation: 72, postContainment: 52, paintPositioning: 57, verticality: 55, interiorRecovery: 58,
    onBallSteal: 74, stripTechnique: 66, deflectionTiming: 77, blockTiming: 64, helpSideBlocking: 64, recoveryChaseDownBlocking: 63,
    defensivePositioning: 66, boxOutTechnique: 76, reboundSecurity: 68, acceleration: 79, topSpeed: 77, lateralQuickness: 81,
    agilityChangeOfDirection: 86, reactiveAgility: 85, firstStepBurst: 74, verticalLeap: 71, secondJump: 77, bodyControl: 71,
    lowerBodyStrength: 54, upperBodyStrength: 59, contactBalance: 56, stamina: 76, recoveryRate: 78, workloadCapacity: 82,
    injuryResistance: 58, loadTolerance: 61, offensiveAwareness: 83, shotSelection: 82, decisionMaking: 80, spacingReadReact: 74,
    defensiveAwareness: 64, anticipation: 64, helpRecognition: 75, rotationDiscipline: 73, foulDiscipline: 71, competitiveness: 70,
    composure: 67, motor: 62, focus: 62, resilience: 61, communication: 77, teamwork: 78,
    leadership: 80,
  },
  SG: {
    standingFinish: 66, drivingLayup: 60, contactFinishing: 67, dunking: 61, foulDrawing: 67, postControlFootwork: 40,
    postFinishing: 41, postHookTouch: 41, postFadeaway: 40, catchAndShootMid: 59, pullUpMid: 61, movementMid: 60,
    contestedMid: 59, catchAndShootThree: 66, pullUpThree: 63, movementThree: 70, contestedThree: 66, freeThrowAccuracy: 59,
    freeThrowConsistency: 57, passAccuracy: 71, courtVision: 69, passTiming: 63, dribbleControl: 57, ballSecurity: 50,
    changeOfDirection: 47, paceControl: 52, cutTiming: 53, relocation: 52, screenUse: 52, catchSecurity: 55,
    screenAngle: 45, screenTiming: 50, rollPopTiming: 48, offensivePositioning: 41, reboundReading: 49, reboundPursuit: 38,
    boxOutEscape: 42, onBallContainment: 62, lateralRecovery: 61, screenNavigation: 65, closeoutControl: 58, denial: 48,
    cutterTracking: 45, offBallScreenNavigation: 50, postContainment: 50, paintPositioning: 58, verticality: 51, interiorRecovery: 55,
    onBallSteal: 61, stripTechnique: 56, deflectionTiming: 61, blockTiming: 45, helpSideBlocking: 45, recoveryChaseDownBlocking: 47,
    defensivePositioning: 55, boxOutTechnique: 57, reboundSecurity: 57, acceleration: 54, topSpeed: 61, lateralQuickness: 63,
    agilityChangeOfDirection: 53, reactiveAgility: 57, firstStepBurst: 64, verticalLeap: 55, secondJump: 61, bodyControl: 53,
    lowerBodyStrength: 61, upperBodyStrength: 60, contactBalance: 51, stamina: 54, recoveryRate: 51, workloadCapacity: 49,
    injuryResistance: 65, loadTolerance: 63, offensiveAwareness: 67, shotSelection: 65, decisionMaking: 65, spacingReadReact: 60,
    defensiveAwareness: 57, anticipation: 61, helpRecognition: 61, rotationDiscipline: 63, foulDiscipline: 57, competitiveness: 63,
    composure: 63, motor: 55, focus: 57, resilience: 57, communication: 45, teamwork: 45,
    leadership: 44,
  },
  SF: {
    standingFinish: 60, drivingLayup: 52, contactFinishing: 57, dunking: 55, foulDrawing: 58, postControlFootwork: 54,
    postFinishing: 59, postHookTouch: 56, postFadeaway: 50, catchAndShootMid: 51, pullUpMid: 49, movementMid: 44,
    contestedMid: 47, catchAndShootThree: 54, pullUpThree: 54, movementThree: 57, contestedThree: 58, freeThrowAccuracy: 52,
    freeThrowConsistency: 52, passAccuracy: 49, courtVision: 45, passTiming: 48, dribbleControl: 46, ballSecurity: 40,
    changeOfDirection: 40, paceControl: 45, cutTiming: 52, relocation: 52, screenUse: 52, catchSecurity: 48,
    screenAngle: 63, screenTiming: 61, rollPopTiming: 59, offensivePositioning: 60, reboundReading: 56, reboundPursuit: 61,
    boxOutEscape: 53, onBallContainment: 47, lateralRecovery: 50, screenNavigation: 56, closeoutControl: 47, denial: 50,
    cutterTracking: 53, offBallScreenNavigation: 58, postContainment: 54, paintPositioning: 47, verticality: 54, interiorRecovery: 55,
    onBallSteal: 49, stripTechnique: 50, deflectionTiming: 48, blockTiming: 45, helpSideBlocking: 47, recoveryChaseDownBlocking: 41,
    defensivePositioning: 44, boxOutTechnique: 48, reboundSecurity: 54, acceleration: 64, topSpeed: 62, lateralQuickness: 58,
    agilityChangeOfDirection: 55, reactiveAgility: 58, firstStepBurst: 45, verticalLeap: 50, secondJump: 55, bodyControl: 55,
    lowerBodyStrength: 41, upperBodyStrength: 43, contactBalance: 41, stamina: 49, recoveryRate: 53, workloadCapacity: 44,
    injuryResistance: 53, loadTolerance: 49, offensiveAwareness: 56, shotSelection: 61, decisionMaking: 56, spacingReadReact: 65,
    defensiveAwareness: 63, anticipation: 57, helpRecognition: 52, rotationDiscipline: 62, foulDiscipline: 62, competitiveness: 62,
    composure: 60, motor: 58, focus: 63, resilience: 53, communication: 53, teamwork: 49,
    leadership: 56,
  },
  PF: {
    standingFinish: 80, drivingLayup: 76, contactFinishing: 82, dunking: 75, foulDrawing: 75, postControlFootwork: 77,
    postFinishing: 86, postHookTouch: 81, postFadeaway: 82, catchAndShootMid: 64, pullUpMid: 69, movementMid: 60,
    contestedMid: 62, catchAndShootThree: 65, pullUpThree: 61, movementThree: 59, contestedThree: 65, freeThrowAccuracy: 68,
    freeThrowConsistency: 70, passAccuracy: 69, courtVision: 62, passTiming: 59, dribbleControl: 64, ballSecurity: 60,
    changeOfDirection: 67, paceControl: 61, cutTiming: 63, relocation: 54, screenUse: 63, catchSecurity: 57,
    screenAngle: 82, screenTiming: 76, rollPopTiming: 70, offensivePositioning: 82, reboundReading: 81, reboundPursuit: 76,
    boxOutEscape: 72, onBallContainment: 61, lateralRecovery: 62, screenNavigation: 66, closeoutControl: 62, denial: 78,
    cutterTracking: 74, offBallScreenNavigation: 73, postContainment: 89, paintPositioning: 80, verticality: 82, interiorRecovery: 84,
    onBallSteal: 63, stripTechnique: 65, deflectionTiming: 68, blockTiming: 66, helpSideBlocking: 68, recoveryChaseDownBlocking: 68,
    defensivePositioning: 88, boxOutTechnique: 86, reboundSecurity: 77, acceleration: 69, topSpeed: 70, lateralQuickness: 62,
    agilityChangeOfDirection: 72, reactiveAgility: 71, firstStepBurst: 79, verticalLeap: 79, secondJump: 81, bodyControl: 72,
    lowerBodyStrength: 73, upperBodyStrength: 72, contactBalance: 77, stamina: 78, recoveryRate: 79, workloadCapacity: 79,
    injuryResistance: 77, loadTolerance: 73, offensiveAwareness: 69, shotSelection: 68, decisionMaking: 67, spacingReadReact: 71,
    defensiveAwareness: 71, anticipation: 65, helpRecognition: 69, rotationDiscipline: 67, foulDiscipline: 71, competitiveness: 62,
    composure: 62, motor: 63, focus: 59, resilience: 67, communication: 73, teamwork: 71,
    leadership: 80,
  },
  C: {
    standingFinish: 90, drivingLayup: 93, contactFinishing: 91, dunking: 86, foulDrawing: 88, postControlFootwork: 84,
    postFinishing: 88, postHookTouch: 81, postFadeaway: 79, catchAndShootMid: 71, pullUpMid: 69, movementMid: 70,
    contestedMid: 68, catchAndShootThree: 63, pullUpThree: 68, movementThree: 59, contestedThree: 63, freeThrowAccuracy: 74,
    freeThrowConsistency: 72, passAccuracy: 59, courtVision: 69, passTiming: 61, dribbleControl: 81, ballSecurity: 80,
    changeOfDirection: 78, paceControl: 72, cutTiming: 80, relocation: 71, screenUse: 81, catchSecurity: 72,
    screenAngle: 92, screenTiming: 96, rollPopTiming: 100, offensivePositioning: 79, reboundReading: 78, reboundPursuit: 76,
    boxOutEscape: 84, onBallContainment: 64, lateralRecovery: 72, screenNavigation: 70, closeoutControl: 70, denial: 69,
    cutterTracking: 69, offBallScreenNavigation: 72, postContainment: 89, paintPositioning: 90, verticality: 85, interiorRecovery: 95,
    onBallSteal: 82, stripTechnique: 73, deflectionTiming: 80, blockTiming: 81, helpSideBlocking: 78, recoveryChaseDownBlocking: 83,
    defensivePositioning: 84, boxOutTechnique: 81, reboundSecurity: 83, acceleration: 69, topSpeed: 75, lateralQuickness: 74,
    agilityChangeOfDirection: 81, reactiveAgility: 79, firstStepBurst: 80, verticalLeap: 72, secondJump: 68, bodyControl: 73,
    lowerBodyStrength: 86, upperBodyStrength: 92, contactBalance: 93, stamina: 87, recoveryRate: 84, workloadCapacity: 79,
    injuryResistance: 85, loadTolerance: 84, offensiveAwareness: 80, shotSelection: 76, decisionMaking: 76, spacingReadReact: 86,
    defensiveAwareness: 86, anticipation: 82, helpRecognition: 81, rotationDiscipline: 89, foulDiscipline: 87, competitiveness: 72,
    composure: 71, motor: 65, focus: 77, resilience: 70, communication: 82, teamwork: 90,
    leadership: 80,
  },
}

describe('detailed generation golden vectors (generation v2)', () => {
  it('reproduces every pinned 91-value record exactly', () => {
    expect(DETAILED_RATING_GENERATION_VERSION).toBe(2)
    for (const position of POSITIONS) {
      const generated = generateDetailedPlayerRatings(
        LEAGUE_SEED,
        GOLDEN_PLAYER_IDS[position],
        position,
      )
      expect(generated).toEqual(GOLDEN_VECTORS[position])
    }
  })

  it('is deterministic and player-distinct', () => {
    const first = generateDetailedPlayerRatings(
      LEAGUE_SEED,
      GOLDEN_PLAYER_IDS.PG,
      'PG',
    )
    const second = generateDetailedPlayerRatings(
      LEAGUE_SEED,
      GOLDEN_PLAYER_IDS.PG,
      'PG',
    )
    const otherPlayer = generateDetailedPlayerRatings(
      LEAGUE_SEED,
      GOLDEN_PLAYER_IDS.SG,
      'PG',
    )

    expect(second).toEqual(first)
    expect(otherPlayer).not.toEqual(first)
  })
})

describe('labeled stream isolation (ADR 0009 §5)', () => {
  it('pins the exact three seed-label formats (v2)', () => {
    const playerId = GOLDEN_PLAYER_IDS.PG
    expect(deriveDetailedQualitySeed(LEAGUE_SEED, playerId)).toBe(
      deriveSeed(LEAGUE_SEED, `player-quality/v2/${playerId}`),
    )
    expect(
      deriveDetailedCategorySeed(LEAGUE_SEED, playerId, 'rimFinishing'),
    ).toBe(deriveSeed(LEAGUE_SEED, `player-category/v2/${playerId}/rimFinishing`))
    expect(
      deriveDetailedSkillSeed(LEAGUE_SEED, playerId, 'standingFinish'),
    ).toBe(deriveSeed(LEAGUE_SEED, `player-skill/v2/${playerId}/standingFinish`))
  })

  it('every field of the full record equals its independent single-field generation', () => {
    for (const position of ['PG', 'C'] as const) {
      const record = generateDetailedPlayerRatings(
        LEAGUE_SEED,
        GOLDEN_PLAYER_IDS[position],
        position,
      )
      for (const subRatingKey of SUB_RATING_KEYS) {
        expect(
          generateDetailedRating(
            LEAGUE_SEED,
            GOLDEN_PLAYER_IDS[position],
            position,
            subRatingKey,
          ),
        ).toBe(record[subRatingKey])
      }
    }
  })

  it('preserves the injected source-factory invocation contract', () => {
    const playerId = GOLDEN_PLAYER_IDS.PG
    const observedSeeds: string[] = []
    const ratings = generateDetailedPlayerRatings(
      LEAGUE_SEED,
      playerId,
      'PG',
      (seed) => {
        observedSeeds.push(seed)
        return createRandomSource(seed)
      },
    )
    const expectedSeeds = SUB_RATING_KEYS.flatMap((subRatingKey) => [
      deriveDetailedQualitySeed(LEAGUE_SEED, playerId),
      ...DETAILED_CATEGORY_DEFINITIONS.filter((definition) =>
        definition.subRatings.some(
          (subRating) => subRating.key === subRatingKey,
        ),
      ).map((definition) =>
        deriveDetailedCategorySeed(
          LEAGUE_SEED,
          playerId,
          definition.key,
        ),
      ),
      deriveDetailedSkillSeed(LEAGUE_SEED, playerId, subRatingKey),
    ])

    expect(ratings).toEqual(GOLDEN_VECTORS.PG)
    // 91 keys: each draws quality + its categories (reboundReading twice) + skill.
    expect(observedSeeds).toHaveLength(274)
    expect(observedSeeds).toEqual(expectedSeeds)
  })

  it('recomposes a value exactly from its term streams', () => {
    const playerId = GOLDEN_PLAYER_IDS.SF
    const quality = generateQualityBaseline(LEAGUE_SEED, playerId)
    const aptitude = generateCategoryAptitude(
      LEAGUE_SEED,
      playerId,
      'passing',
    )
    const variation = generateFieldVariation(
      LEAGUE_SEED,
      playerId,
      'courtVision',
    )
    const bias = POSITION_CATEGORY_BIASES.SF.passing

    const expected = Math.min(
      100,
      Math.max(0, quality + aptitude + bias + variation),
    )
    expect(
      generateDetailedRating(LEAGUE_SEED, playerId, 'SF', 'courtVision'),
    ).toBe(expected)
  })

  it('the shared Rebound Reading averages its two category terms', () => {
    const playerId = GOLDEN_PLAYER_IDS.C
    const quality = generateQualityBaseline(LEAGUE_SEED, playerId)
    const offensiveTerm =
      generateCategoryAptitude(LEAGUE_SEED, playerId, 'offensiveRebounding') +
      POSITION_CATEGORY_BIASES.C.offensiveRebounding
    const defensiveTerm =
      generateCategoryAptitude(LEAGUE_SEED, playerId, 'defensiveRebounding') +
      POSITION_CATEGORY_BIASES.C.defensiveRebounding
    const variation = generateFieldVariation(
      LEAGUE_SEED,
      playerId,
      'reboundReading',
    )

    const expected = Math.min(
      100,
      Math.max(
        0,
        quality + Math.round((offensiveTerm + defensiveTerm) / 2) + variation,
      ),
    )
    expect(
      generateDetailedRating(LEAGUE_SEED, playerId, 'C', 'reboundReading'),
    ).toBe(expected)
  })

  it('honors the injected source factory and pins both clamp bounds', () => {
    const maxFactory = () => ({
      nextUint32: () => 0,
      nextFloat: () => 0,
      nextInt: (maxExclusive: number) => maxExclusive - 1,
      chance: () => false,
      pickWeighted: <T,>(choices: readonly T[]) => choices[0],
    })
    const minFactory = () => ({
      nextUint32: () => 0,
      nextFloat: () => 0,
      nextInt: () => 0,
      chance: () => false,
      pickWeighted: <T,>(choices: readonly T[]) => choices[0],
    })

    // Max draws: 80 quality + 8 aptitude + 12 C bias + 6 variation = 106 → 100.
    expect(
      generateDetailedRating(
        LEAGUE_SEED,
        GOLDEN_PLAYER_IDS.C,
        'C',
        'defensivePositioning',
        maxFactory,
      ),
    ).toBe(100)
    // Min draws: 45 quality − 8 aptitude − 10 PG bias − 6 variation = 21.
    expect(
      generateDetailedRating(
        LEAGUE_SEED,
        GOLDEN_PLAYER_IDS.PG,
        'PG',
        'postContainment',
        minFactory,
      ),
    ).toBe(21)
  })

  it('term draws stay inside their calibration ranges', () => {
    expect(Object.isFrozen(POSITION_CATEGORY_BIASES)).toBe(true)
    for (const position of POSITIONS) {
      expect(Object.isFrozen(POSITION_CATEGORY_BIASES[position])).toBe(true)
    }

    for (let index = 0; index < 25; index += 1) {
      const playerId = parsePlayerId(`player_r3range_${index}`)
      const quality = generateQualityBaseline(LEAGUE_SEED, playerId)
      expect(quality).toBeGreaterThanOrEqual(QUALITY_BASELINE_MIN)
      expect(quality).toBeLessThanOrEqual(QUALITY_BASELINE_MAX)

      const aptitude = generateCategoryAptitude(
        LEAGUE_SEED,
        playerId,
        DETAILED_CATEGORY_KEYS[index % DETAILED_CATEGORY_KEYS.length],
      )
      expect(Math.abs(aptitude)).toBeLessThanOrEqual(CATEGORY_APTITUDE_SPREAD)

      const variation = generateFieldVariation(
        LEAGUE_SEED,
        playerId,
        SUB_RATING_KEYS[index % SUB_RATING_KEYS.length],
      )
      expect(Math.abs(variation)).toBeLessThanOrEqual(FIELD_VARIATION_SPREAD)
    }
  })
})

describe('generated record validity and distribution report', () => {
  it('every generated record parses as a strict detailed record', () => {
    for (const seed of ['alpha', 'beta', 'gamma']) {
      for (const position of POSITIONS) {
        const record = generateDetailedPlayerRatings(
          `r3-validity-${seed}`,
          parsePlayerId(`player_r3v_${seed}_${position.toLowerCase()}`),
          position,
        )
        expect(() => parseDetailedPlayerRatings(record)).not.toThrow()
      }
    }
  })

  it('position bias shows up in the aggregate distribution, not just goldens', () => {
    const PLAYERS_PER_POSITION = 80
    const means = new Map<Position, Record<string, number>>()

    for (const position of POSITIONS) {
      let interiorDefenseTotal = 0
      let passingTotal = 0
      let threeTotal = 0
      let overallTotal = 0

      for (let index = 0; index < PLAYERS_PER_POSITION; index += 1) {
        const record = generateDetailedPlayerRatings(
          'r3-distribution-seed',
          parsePlayerId(`player_r3d_${position.toLowerCase()}_${index}`),
          position,
        )
        interiorDefenseTotal += deriveCategoryScore(record, 'interiorDefense')
        passingTotal += deriveCategoryScore(record, 'passing')
        threeTotal += deriveCategoryScore(record, 'threePointShooting')
        overallTotal +=
          DETAILED_CATEGORY_KEYS.reduce(
            (total, key) => total + deriveCategoryScore(record, key),
            0,
          ) / DETAILED_CATEGORY_KEYS.length
      }

      means.set(position, {
        interiorDefense: interiorDefenseTotal / PLAYERS_PER_POSITION,
        passing: passingTotal / PLAYERS_PER_POSITION,
        three: threeTotal / PLAYERS_PER_POSITION,
        overall: overallTotal / PLAYERS_PER_POSITION,
      })
    }

    const pg = means.get('PG')
    const c = means.get('C')
    if (pg === undefined || c === undefined) throw new Error('missing means')

    // Directional biases: centers protect the rim, guards run the offense.
    expect(c.interiorDefense - pg.interiorDefense).toBeGreaterThan(10)
    expect(pg.passing - c.passing).toBeGreaterThan(7)
    expect(pg.three - c.three).toBeGreaterThan(5)

    // Global sanity: every positional mean sits in a playable band.
    for (const position of POSITIONS) {
      const positionMeans = means.get(position)
      if (positionMeans === undefined) throw new Error('missing means')
      expect(positionMeans.overall).toBeGreaterThan(52)
      expect(positionMeans.overall).toBeLessThan(72)
    }
  })
})
