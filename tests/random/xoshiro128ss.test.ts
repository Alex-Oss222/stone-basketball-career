import { describe, expect, it } from 'vitest'
import { deriveSeed } from '../../src/random/seed'
import { Xoshiro128StarStar } from '../../src/random/xoshiro128ss'

const UINT32_MAX = 0xffff_ffff
const FOUNDATION_SEED_GOLDEN_VECTOR = [
  2_341_670_934,
  1_337_852_881,
  2_409_395_222,
  1_845_917_642,
  664_759_644,
  236_574_613,
  1_249_132_112,
  54_091_194,
] as const

function takeUint32(seed: string, count: number): readonly number[] {
  const random = new Xoshiro128StarStar(seed)
  return Array.from({ length: count }, () => random.nextUint32())
}

describe('Xoshiro128StarStar', () => {
  it('produces identical sequences for identical seeds', () => {
    const first = takeUint32('foundation-seed', 32)
    const second = takeUint32('foundation-seed', 32)

    expect(first).toEqual(second)
  })

  it('pins the versioned generator sequence', () => {
    expect(takeUint32('foundation-seed', 8)).toEqual(
      FOUNDATION_SEED_GOLDEN_VECTOR,
    )
  })

  it('normally produces different sequences for different seeds', () => {
    const first = takeUint32('foundation-seed-alpha', 32)
    const second = takeUint32('foundation-seed-beta', 32)

    expect(first).not.toEqual(second)
  })

  it('keeps generated values within their documented ranges', () => {
    const random = new Xoshiro128StarStar('range-seed')

    for (let iteration = 0; iteration < 5_000; iteration += 1) {
      const uint32 = random.nextUint32()
      const float = random.nextFloat()
      const integer = random.nextInt(37)

      expect(Number.isInteger(uint32)).toBe(true)
      expect(uint32).toBeGreaterThanOrEqual(0)
      expect(uint32).toBeLessThanOrEqual(UINT32_MAX)
      expect(float).toBeGreaterThanOrEqual(0)
      expect(float).toBeLessThan(1)
      expect(Number.isInteger(integer)).toBe(true)
      expect(integer).toBeGreaterThanOrEqual(0)
      expect(integer).toBeLessThan(37)
    }
  })

  it('validates and honors the helper method contracts', () => {
    const random = new Xoshiro128StarStar('helper-seed')

    expect(random.chance(0)).toBe(false)
    expect(random.chance(1)).toBe(true)
    expect(
      random.pickWeighted(['excluded', 'selected'], (choice) =>
        choice === 'selected' ? 1 : 0,
      ),
    ).toBe('selected')

    expect(() => random.nextInt(0)).toThrow(RangeError)
    expect(() => random.chance(Number.NaN)).toThrow(RangeError)
    expect(() => random.pickWeighted([], () => 1)).toThrow(RangeError)
    expect(() => random.pickWeighted(['excluded'], () => 0)).toThrow(
      RangeError,
    )
  })
})

describe('deriveSeed', () => {
  it('derives stable versioned seeds', () => {
    expect(deriveSeed('  Stone League  ', 'league/v1')).toBe(
      'seed-derivation-v1:2783cf12fe7e11af6952f796ca1f4f8a',
    )
    expect(deriveSeed('Stone League', 'league/v1')).not.toBe(
      deriveSeed('Stone League', 'schedule/v1'),
    )
  })
})
