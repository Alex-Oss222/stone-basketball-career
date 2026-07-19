import { existsSync, readFileSync, readdirSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import {
  SUB_RATING_KEYS,
  parseDetailedPlayerRatings,
} from '../../src/domain/detailedRatings'
import type { SubRatingKey } from '../../src/domain/detailedRatings'
import { POSITIONS } from '../../src/domain/league'
import {
  ROTATION_ABILITY_GROUP_WEIGHTS_BPS,
  ROTATION_ABILITY_VERSION,
  ROTATION_ABILITY_WEIGHT_TOTAL_BPS,
  selectRotationAbility,
} from '../../src/domain/rotationAbility'
import {
  FORBIDDEN_SIM_SUB_RATINGS,
  SIM_EVENT_KEYS,
  SIM_EVENT_RATING_READS,
  SIM_RATING_READ_VERSION,
  listReadableSubRatings,
  selectSimEventFactor,
} from '../../src/domain/simulationReads'

function makeRatings(value: number) {
  return parseDetailedPlayerRatings(
    Object.fromEntries(
      SUB_RATING_KEYS.map((key) => [key, value]),
    ) as Record<SubRatingKey, number>,
  )
}

describe('rotation-ability selector (R7)', () => {
  it('pins the version and the four-pillar weight totals', () => {
    expect(ROTATION_ABILITY_VERSION).toBe(2)
    expect(Object.isFrozen(ROTATION_ABILITY_GROUP_WEIGHTS_BPS)).toBe(true)
    for (const position of POSITIONS) {
      const weights = ROTATION_ABILITY_GROUP_WEIGHTS_BPS[position]
      expect(Object.isFrozen(weights)).toBe(true)
      expect(Object.keys(weights).sort()).toEqual([
        'defense',
        'mental',
        'offense',
        'physical',
      ])
      const total = Object.values(weights).reduce(
        (sum, weight) => sum + weight,
        0,
      )
      expect(total).toBe(ROTATION_ABILITY_WEIGHT_TOTAL_BPS)
      for (const weight of Object.values(weights)) {
        expect(Number.isInteger(weight)).toBe(true)
        expect(weight).toBeGreaterThan(0)
      }
    }
  })

  it('a uniform record scores that value at every position', () => {
    const ratings = makeRatings(58)
    for (const position of POSITIONS) {
      const result = selectRotationAbility(ratings, position)
      const { ability, conditioning } = result
      expect(Object.isFrozen(result)).toBe(true)
      expect(ability).toBeCloseTo(58, 10)
      expect(conditioning).toBe(58)
    }
  })

  it('weights positions differently: creators rate higher at PG than C', () => {
    const playmaker = parseDetailedPlayerRatings({
      ...makeRatings(50),
      passAccuracy: 95,
      courtVision: 95,
      passTiming: 95,
      dribbleControl: 90,
      ballSecurity: 90,
      changeOfDirection: 90,
      paceControl: 90,
    })
    expect(
      selectRotationAbility(playmaker, 'PG').ability,
    ).toBeGreaterThan(selectRotationAbility(playmaker, 'C').ability)
  })

  it('is deterministic and monotonic in a raised sub-rating', () => {
    const base = makeRatings(50)
    const better = parseDetailedPlayerRatings({
      ...makeRatings(50),
      blockTiming: 90,
    })
    for (const position of POSITIONS) {
      expect(selectRotationAbility(base, position)).toEqual(
        selectRotationAbility(base, position),
      )
      expect(
        selectRotationAbility(better, position).ability,
      ).toBeGreaterThanOrEqual(selectRotationAbility(base, position).ability)
    }
  })
})

describe('simulation rating-read registry (R8)', () => {
  it('pins the read version', () => {
    expect(SIM_RATING_READ_VERSION).toBe(2)
  })

  it('every event dependency is a valid stored sub-rating', () => {
    expect(Object.isFrozen(SIM_EVENT_RATING_READS)).toBe(true)
    expect(Object.isFrozen(SIM_EVENT_KEYS)).toBe(true)
    const valid = new Set<string>(SUB_RATING_KEYS)
    for (const event of SIM_EVENT_KEYS) {
      const reads = SIM_EVENT_RATING_READS[event]
      expect(Object.isFrozen(reads)).toBe(true)
      expect(reads.length).toBeGreaterThan(0)
      expect(new Set(reads).size).toBe(reads.length)
      for (const key of reads) {
        expect(valid.has(key)).toBe(true)
      }
    }
  })

  it('possession events never read a forbidden sub-rating', () => {
    expect(Object.isFrozen(FORBIDDEN_SIM_SUB_RATINGS)).toBe(true)
    expect(FORBIDDEN_SIM_SUB_RATINGS).toHaveLength(8)
    expect([...FORBIDDEN_SIM_SUB_RATINGS].sort()).toEqual(
      [
        'communication',
        'competitiveness',
        'focus',
        'injuryResistance',
        'leadership',
        'loadTolerance',
        'resilience',
        'teamwork',
      ].sort(),
    )
    const forbidden = new Set<string>(FORBIDDEN_SIM_SUB_RATINGS)
    for (const event of SIM_EVENT_KEYS) {
      for (const key of SIM_EVENT_RATING_READS[event]) {
        expect(forbidden.has(key)).toBe(false)
      }
    }
  })

  it('covers exactly the 83 possession-relevant sub-ratings', () => {
    const readable = listReadableSubRatings()
    expect(readable).toHaveLength(83)
    expect(Object.isFrozen(readable)).toBe(true)
    expect(listReadableSubRatings()).toBe(readable)

    const covered = new Set<string>(
      SIM_EVENT_KEYS.flatMap((event) => [...SIM_EVENT_RATING_READS[event]]),
    )
    for (const key of readable) {
      expect(covered.has(key), key).toBe(true)
    }
    expect(covered.size).toBe(83)
  })

  it('the event factor is the unweighted mean of the frozen reads', () => {
    const ratings = parseDetailedPlayerRatings({
      ...makeRatings(40),
      freeThrowAccuracy: 90,
      freeThrowConsistency: 60,
    })
    expect(selectSimEventFactor('freeThrowResolution', ratings)).toBe(75)
    expect(selectSimEventFactor('passResolution', makeRatings(72))).toBe(72)
  })

  it('agrees with the frozen table in docs/SIMULATION_MODEL.md', () => {
    const doc = readFileSync(
      join(__dirname, '..', '..', 'docs', 'SIMULATION_MODEL.md'),
      'utf8',
    )
    for (const event of SIM_EVENT_KEYS) {
      const row = `| \`${event}\` | ${SIM_EVENT_RATING_READS[event]
        .map((key) => `\`${key}\``)
        .join(', ')} |`
      expect(doc, `missing/stale row for ${event}`).toContain(row)
    }
    expect(doc).toContain(`SIM_RATING_READ_VERSION = ${SIM_RATING_READ_VERSION}`)
  })

  it('architecture guard: src/simulation may import ratings only via simulationReads', () => {
    const simulationDir = join(__dirname, '..', '..', 'src', 'simulation')
    if (!existsSync(simulationDir)) {
      // §9 has not started; the wall stands ready for it.
      return
    }
    for (const file of readdirSync(simulationDir, { recursive: true })) {
      const filePath = join(simulationDir, String(file))
      if (!filePath.endsWith('.ts')) continue
      const source = readFileSync(filePath, 'utf8')
      expect(source, filePath).not.toMatch(
        /from '.*domain\/(detailedRatings|playerDerivations)'/,
      )
      expect(source, filePath).not.toMatch(/Math\.random/)
    }
  })
})
