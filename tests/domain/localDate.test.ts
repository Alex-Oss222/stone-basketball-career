import { describe, expect, expectTypeOf, it } from 'vitest'
import {
  addDays,
  compareLocalDates,
  formatSeasonLabel,
  getCalendarYear,
  isLocalDate,
  parseLocalDate,
} from '../../src/domain/localDate'
import type { LocalDate } from '../../src/domain/localDate'

describe('LocalDate', () => {
  it.each([
    '2026-01-01',
    '2026-02-28',
    '2024-02-29',
    '2000-02-29',
    '0000-02-29',
    '9999-12-31',
  ])('strictly parses valid date %s', (value) => {
    expect(parseLocalDate(value)).toBe(value)
    expect(isLocalDate(value)).toBe(true)
  })

  it.each([
    '2026-02-29',
    '2026-02-30',
    '1900-02-29',
    '2026-04-31',
    '2026-00-10',
    '2026-13-01',
    '2026-01-00',
    '2026-1-01',
    '26-01-01',
    '2026-01-01T00:00:00Z',
    ' 2026-01-01',
    '',
  ])('rejects malformed or impossible date %s', (value) => {
    expect(isLocalDate(value)).toBe(false)
    expect(() => parseLocalDate(value)).toThrow()
  })

  it.each([null, undefined, 20260101, {}, new Date()])(
    'rejects non-string input %#',
    (value) => {
      expect(isLocalDate(value)).toBe(false)
      expect(() => parseLocalDate(value)).toThrow(TypeError)
    },
  )

  it('compares dates chronologically and deterministically', () => {
    const early = parseLocalDate('2026-10-03')
    const late = parseLocalDate('2027-01-01')

    expect(compareLocalDates(early, late)).toBe(-1)
    expect(compareLocalDates(late, early)).toBe(1)
    expect(compareLocalDates(early, early)).toBe(0)
  })

  it('adds calendar days across month, year, and leap-day boundaries', () => {
    expect(addDays(parseLocalDate('2026-01-31'), 1)).toBe('2026-02-01')
    expect(addDays(parseLocalDate('2024-02-28'), 1)).toBe('2024-02-29')
    expect(addDays(parseLocalDate('2024-02-28'), 2)).toBe('2024-03-01')
    expect(addDays(parseLocalDate('2027-01-01'), -1)).toBe('2026-12-31')
    expect(addDays(parseLocalDate('2026-06-15'), 0)).toBe('2026-06-15')
  })

  it('rejects fractional, non-finite, unsafe, and out-of-range additions', () => {
    const date = parseLocalDate('2026-01-01')

    for (const amount of [0.5, Number.NaN, Number.POSITIVE_INFINITY]) {
      expect(() => addDays(date, amount)).toThrow(TypeError)
    }
    expect(() => addDays(date, Number.MAX_SAFE_INTEGER + 1)).toThrow(TypeError)
    expect(() => addDays(parseLocalDate('0000-01-01'), -1)).toThrow(RangeError)
    expect(() => addDays(parseLocalDate('9999-12-31'), 1)).toThrow(RangeError)
  })

  it('extracts the stored calendar year without timezone conversion', () => {
    expect(getCalendarYear(parseLocalDate('2026-01-01'))).toBe(2026)
  })

  it('remains an opaque string type rather than a Date object', () => {
    expectTypeOf<LocalDate>().toMatchTypeOf<string>()
    expectTypeOf<LocalDate>().not.toEqualTypeOf<string>()
    expectTypeOf<LocalDate>().not.toEqualTypeOf<Date>()
  })
})

describe('formatSeasonLabel', () => {
  it('abbreviates an unambiguous ending year in the same century', () => {
    expect(formatSeasonLabel(2026, 2027)).toBe('2026–27')
    expect(formatSeasonLabel(2000, 2001)).toBe('2000–01')
  })

  it('uses both full years across a century boundary', () => {
    expect(formatSeasonLabel(2099, 2100)).toBe('2099–2100')
    expect(formatSeasonLabel(1999, 2000)).toBe('1999–2000')
  })

  it('rejects reversed, equal, fractional, and unsupported years', () => {
    expect(() => formatSeasonLabel(2027, 2026)).toThrow(RangeError)
    expect(() => formatSeasonLabel(2026, 2026)).toThrow(RangeError)
    expect(() => formatSeasonLabel(2026.5, 2027)).toThrow(RangeError)
    expect(() => formatSeasonLabel(-1, 2027)).toThrow(RangeError)
    expect(() => formatSeasonLabel(9999, 10000)).toThrow(RangeError)
  })
})
