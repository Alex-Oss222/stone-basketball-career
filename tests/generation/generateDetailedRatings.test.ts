import { describe, expect, it } from 'vitest'
import {
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

const LEAGUE_SEED = 'r3-golden-league-seed'

const GOLDEN_PLAYER_IDS = {
  PG: parsePlayerId('player_r3golden_pg'),
  SG: parsePlayerId('player_r3golden_sg'),
  SF: parsePlayerId('player_r3golden_sf'),
  PF: parsePlayerId('player_r3golden_pf'),
  C: parsePlayerId('player_r3golden_c'),
} as const

/**
 * Golden vectors — full 67-value outputs pinned for one player per position
 * under DETAILED_RATING_GENERATION_VERSION 1. An intentional generator change
 * must bump the version and deliberately regenerate these; an accidental
 * change fails here.
 */
const GOLDEN_VECTORS: Readonly<Record<Position, DetailedPlayerRatings>> = {
  PG: {
    standingFinish: 53, drivingLayup: 57, contactFinishing: 58, dunking: 64,
    postFinishing: 62, catchAndShootMid: 66, pullUpMid: 65, contestedMid: 64,
    postFadeaway: 60, catchAndShootThree: 65, pullUpThree: 69,
    movementThree: 62, contestedThree: 67, freeThrowAccuracy: 57,
    freeThrowConsistency: 46, pressureFreeThrows: 49, passAccuracy: 62,
    courtVision: 64, passTiming: 59, dribbleControl: 65, ballSecurity: 71,
    changeOfDirection: 72, pressureHandling: 73, offensivePositioning: 47,
    reboundPursuit: 52, reboundReading: 51, secondJump: 44,
    defensivePositioning: 42, boxOutTechnique: 42, reboundSecurity: 37,
    onBallContainment: 64, lateralRecovery: 68, screenNavigation: 67,
    closeoutControl: 72, postContainment: 41, rimDeterrence: 39,
    helpRotation: 44, paintPositioning: 47, onBallSteal: 57,
    passingLaneAnticipation: 63, deflectionTiming: 60, stripTechnique: 58,
    blockTiming: 37, verticalContest: 35, helpSideBlocking: 41,
    recoveryBlocking: 44, acceleration: 71, topSpeed: 61,
    lateralQuickness: 65, agility: 69, lowerBodyStrength: 50,
    upperBodyStrength: 56, contactBalance: 56, physicalLeverage: 55,
    stamina: 63, recoveryRate: 55, workloadCapacity: 61,
    lateGameConditioning: 64, injuryResistance: 49, loadDurability: 51,
    offensiveAwareness: 61, defensiveAwareness: 62, decisionMaking: 64,
    competitiveness: 50, coachability: 52, composure: 50, workEthic: 57,
  },
  SG: {
    standingFinish: 83, drivingLayup: 72, contactFinishing: 79, dunking: 83,
    postFinishing: 77, catchAndShootMid: 76, pullUpMid: 71, contestedMid: 78,
    postFadeaway: 76, catchAndShootThree: 68, pullUpThree: 79,
    movementThree: 77, contestedThree: 71, freeThrowAccuracy: 82,
    freeThrowConsistency: 74, pressureFreeThrows: 80, passAccuracy: 74,
    courtVision: 69, passTiming: 74, dribbleControl: 71, ballSecurity: 66,
    changeOfDirection: 74, pressureHandling: 72, offensivePositioning: 63,
    reboundPursuit: 56, reboundReading: 67, secondJump: 61,
    defensivePositioning: 63, boxOutTechnique: 63, reboundSecurity: 75,
    onBallContainment: 63, lateralRecovery: 63, screenNavigation: 61,
    closeoutControl: 64, postContainment: 75, rimDeterrence: 72,
    helpRotation: 69, paintPositioning: 74, onBallSteal: 59,
    passingLaneAnticipation: 61, deflectionTiming: 70, stripTechnique: 59,
    blockTiming: 58, verticalContest: 62, helpSideBlocking: 64,
    recoveryBlocking: 54, acceleration: 74, topSpeed: 63,
    lateralQuickness: 75, agility: 72, lowerBodyStrength: 68,
    upperBodyStrength: 68, contactBalance: 71, physicalLeverage: 69,
    stamina: 75, recoveryRate: 77, workloadCapacity: 71,
    lateGameConditioning: 73, injuryResistance: 69, loadDurability: 63,
    offensiveAwareness: 84, defensiveAwareness: 81, decisionMaking: 76,
    competitiveness: 68, coachability: 60, composure: 67, workEthic: 60,
  },
  SF: {
    standingFinish: 68, drivingLayup: 76, contactFinishing: 71, dunking: 65,
    postFinishing: 72, catchAndShootMid: 70, pullUpMid: 66, contestedMid: 75,
    postFadeaway: 75, catchAndShootThree: 70, pullUpThree: 66,
    movementThree: 69, contestedThree: 70, freeThrowAccuracy: 60,
    freeThrowConsistency: 57, pressureFreeThrows: 68, passAccuracy: 57,
    courtVision: 59, passTiming: 61, dribbleControl: 47, ballSecurity: 49,
    changeOfDirection: 56, pressureHandling: 47, offensivePositioning: 64,
    reboundPursuit: 63, reboundReading: 55, secondJump: 53,
    defensivePositioning: 58, boxOutTechnique: 53, reboundSecurity: 53,
    onBallContainment: 62, lateralRecovery: 63, screenNavigation: 55,
    closeoutControl: 56, postContainment: 67, rimDeterrence: 63,
    helpRotation: 72, paintPositioning: 65, onBallSteal: 48,
    passingLaneAnticipation: 59, deflectionTiming: 47, stripTechnique: 50,
    blockTiming: 66, verticalContest: 68, helpSideBlocking: 67,
    recoveryBlocking: 56, acceleration: 52, topSpeed: 57,
    lateralQuickness: 64, agility: 58, lowerBodyStrength: 54,
    upperBodyStrength: 62, contactBalance: 63, physicalLeverage: 55,
    stamina: 52, recoveryRate: 60, workloadCapacity: 60,
    lateGameConditioning: 57, injuryResistance: 59, loadDurability: 51,
    offensiveAwareness: 49, defensiveAwareness: 60, decisionMaking: 57,
    competitiveness: 54, coachability: 53, composure: 46, workEthic: 58,
  },
  PF: {
    standingFinish: 53, drivingLayup: 55, contactFinishing: 57, dunking: 62,
    postFinishing: 58, catchAndShootMid: 48, pullUpMid: 54, contestedMid: 54,
    postFadeaway: 48, catchAndShootThree: 44, pullUpThree: 46,
    movementThree: 46, contestedThree: 46, freeThrowAccuracy: 45,
    freeThrowConsistency: 45, pressureFreeThrows: 46, passAccuracy: 47,
    courtVision: 45, passTiming: 46, dribbleControl: 43, ballSecurity: 39,
    changeOfDirection: 42, pressureHandling: 38, offensivePositioning: 59,
    reboundPursuit: 49, reboundReading: 56, secondJump: 48,
    defensivePositioning: 54, boxOutTechnique: 57, reboundSecurity: 58,
    onBallContainment: 47, lateralRecovery: 41, screenNavigation: 45,
    closeoutControl: 46, postContainment: 55, rimDeterrence: 63,
    helpRotation: 60, paintPositioning: 64, onBallSteal: 48,
    passingLaneAnticipation: 44, deflectionTiming: 55, stripTechnique: 48,
    blockTiming: 50, verticalContest: 45, helpSideBlocking: 51,
    recoveryBlocking: 50, acceleration: 48, topSpeed: 49,
    lateralQuickness: 49, agility: 41, lowerBodyStrength: 60,
    upperBodyStrength: 58, contactBalance: 63, physicalLeverage: 60,
    stamina: 42, recoveryRate: 44, workloadCapacity: 49,
    lateGameConditioning: 40, injuryResistance: 44, loadDurability: 39,
    offensiveAwareness: 51, defensiveAwareness: 51, decisionMaking: 42,
    competitiveness: 46, coachability: 49, composure: 57, workEthic: 47,
  },
  C: {
    standingFinish: 76, drivingLayup: 88, contactFinishing: 80, dunking: 88,
    postFinishing: 85, catchAndShootMid: 64, pullUpMid: 63, contestedMid: 63,
    postFadeaway: 69, catchAndShootThree: 49, pullUpThree: 59,
    movementThree: 49, contestedThree: 56, freeThrowAccuracy: 70,
    freeThrowConsistency: 74, pressureFreeThrows: 72, passAccuracy: 63,
    courtVision: 71, passTiming: 71, dribbleControl: 52, ballSecurity: 49,
    changeOfDirection: 53, pressureHandling: 56, offensivePositioning: 81,
    reboundPursuit: 86, reboundReading: 83, secondJump: 84,
    defensivePositioning: 82, boxOutTechnique: 89, reboundSecurity: 89,
    onBallContainment: 77, lateralRecovery: 66, screenNavigation: 67,
    closeoutControl: 67, postContainment: 71, rimDeterrence: 75,
    helpRotation: 78, paintPositioning: 75, onBallSteal: 59,
    passingLaneAnticipation: 61, deflectionTiming: 61, stripTechnique: 64,
    blockTiming: 85, verticalContest: 90, helpSideBlocking: 80,
    recoveryBlocking: 81, acceleration: 59, topSpeed: 60,
    lateralQuickness: 54, agility: 60, lowerBodyStrength: 79,
    upperBodyStrength: 80, contactBalance: 84, physicalLeverage: 76,
    stamina: 81, recoveryRate: 81, workloadCapacity: 81,
    lateGameConditioning: 74, injuryResistance: 78, loadDurability: 72,
    offensiveAwareness: 67, defensiveAwareness: 72, decisionMaking: 75,
    competitiveness: 71, coachability: 67, composure: 66, workEthic: 76,
  },
}

describe('detailed generation golden vectors (generation v1)', () => {
  it('reproduces every pinned 67-value record exactly', () => {
    expect(DETAILED_RATING_GENERATION_VERSION).toBe(1)
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

describe('labeled stream isolation (ADR 0008 §5)', () => {
  it('pins the exact three seed-label formats', () => {
    const playerId = GOLDEN_PLAYER_IDS.PG
    expect(deriveDetailedQualitySeed(LEAGUE_SEED, playerId)).toBe(
      deriveSeed(LEAGUE_SEED, `player-quality/v1/${playerId}`),
    )
    expect(
      deriveDetailedCategorySeed(LEAGUE_SEED, playerId, 'insideScoring'),
    ).toBe(deriveSeed(LEAGUE_SEED, `player-category/v1/${playerId}/insideScoring`))
    expect(
      deriveDetailedSkillSeed(LEAGUE_SEED, playerId, 'standingFinish'),
    ).toBe(deriveSeed(LEAGUE_SEED, `player-skill/v1/${playerId}/standingFinish`))
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
    // Margins sit well below the expected bias gaps (22 / 16 / 14) so a
    // legitimate future reseed of the fixture stays green while a lost or
    // inverted bias still fails.
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
