import { describe, expect, it } from 'vitest'
import { areJsonValuesEqual } from '../../src/shared/areJsonValuesEqual'

describe('areJsonValuesEqual', () => {
  it('compares nested JSON records without depending on property order', () => {
    expect(
      areJsonValuesEqual(
        { alpha: 1, nested: { values: [true, null, 'stone'] } },
        { nested: { values: [true, null, 'stone'] }, alpha: 1 },
      ),
    ).toBe(true)
  })

  it('keeps array order and value types significant', () => {
    expect(areJsonValuesEqual([1, 2], [2, 1])).toBe(false)
    expect(areJsonValuesEqual({ value: 1 }, { value: '1' })).toBe(false)
    expect(areJsonValuesEqual({ value: 1 }, { value: 1, extra: null })).toBe(
      false,
    )
  })

  it('handles primitives and nested differences', () => {
    expect(areJsonValuesEqual(null, null)).toBe(true)
    expect(areJsonValuesEqual('stone', 'stone')).toBe(true)
    expect(
      areJsonValuesEqual(
        { nested: [{ value: 1 }] },
        { nested: [{ value: 2 }] },
      ),
    ).toBe(false)
  })
})
