import { readFileSync } from 'node:fs'
import { describe, expect, expectTypeOf, it } from 'vitest'
import { addDays, parseLocalDate } from '../../src/domain/localDate'
import type { LocalDate } from '../../src/domain/localDate'
import {
  addMonths,
  compareYearMonths,
  daysInMonth,
  firstDateOfMonth,
  getSundayFirstWeekdayIndex,
  isYearMonth,
  iterateYearMonthsInclusive,
  lastDateOfMonth,
  parseYearMonth,
  yearMonthFromLocalDate,
} from '../../src/domain/yearMonth'
import type { YearMonth } from '../../src/domain/yearMonth'

describe('YearMonth parsing', () => {
  it.each(['0000-01', '0099-12', '2026-07', '9999-12'])(
    'accepts canonical boundary value %s unchanged',
    (value) => {
      expect(parseYearMonth(value)).toBe(value)
      expect(isYearMonth(value)).toBe(true)
    },
  )

  it.each([
    '',
    ' 2026-01',
    '2026-01 ',
    '2026-1',
    '26-01',
    '2026-01-01',
    '2026-01T00:00:00Z',
    '+2026-01',
    '-001-01',
    '10000-01',
    '2026/01',
  ])('rejects malformed value %s without normalization', (value) => {
    expect(isYearMonth(value)).toBe(false)
    expect(() => parseYearMonth(value)).toThrow(TypeError)
  })

  it.each(['2026-00', '2026-13'])(
    'rejects impossible month %s',
    (value) => {
      expect(isYearMonth(value)).toBe(false)
      expect(() => parseYearMonth(value)).toThrow(RangeError)
    },
  )

  it.each([null, undefined, 202601, {}, [], Symbol('year-month')])(
    'rejects non-string input %#',
    (value) => {
      expect(isYearMonth(value)).toBe(false)
      expect(() => parseYearMonth(value)).toThrow(TypeError)
    },
  )

  it('remains an opaque string type distinct from LocalDate', () => {
    expectTypeOf<YearMonth>().toMatchTypeOf<string>()
    expectTypeOf<YearMonth>().not.toEqualTypeOf<string>()
    expectTypeOf<YearMonth>().not.toEqualTypeOf<LocalDate>()
    expectTypeOf<
      ReturnType<typeof iterateYearMonthsInclusive>
    >().toEqualTypeOf<readonly YearMonth[]>()
  })
})

describe('YearMonth extraction and comparison', () => {
  it.each([
    ['0000-01-01', '0000-01'],
    ['2026-07-16', '2026-07'],
    ['9999-12-31', '9999-12'],
  ] as const)('extracts %s as %s', (date, expected) => {
    expect(yearMonthFromLocalDate(parseLocalDate(date))).toBe(expected)
  })

  it('compares canonical months within and across years', () => {
    const june = parseYearMonth('2026-06')
    const july = parseYearMonth('2026-07')
    const january = parseYearMonth('2027-01')

    expect(compareYearMonths(june, july)).toBe(-1)
    expect(compareYearMonths(july, january)).toBe(-1)
    expect(compareYearMonths(january, july)).toBe(1)
    expect(compareYearMonths(july, july)).toBe(0)
  })
})

describe('YearMonth addition', () => {
  it.each([
    ['2026-12', 1, '2027-01'],
    ['2027-01', -1, '2026-12'],
    ['2099-12', 1, '2100-01'],
    ['2100-01', -1, '2099-12'],
    ['2026-07', 12, '2027-07'],
    ['2026-07', -12, '2025-07'],
    ['2026-07', 0, '2026-07'],
    ['0000-01', 119_999, '9999-12'],
    ['9999-12', -119_999, '0000-01'],
  ] as const)('adds %s plus %i month(s) as %s', (month, amount, expected) => {
    expect(addMonths(parseYearMonth(month), amount)).toBe(expected)
  })

  it('rejects results outside the supported month range', () => {
    expect(() => addMonths(parseYearMonth('0000-01'), -1)).toThrow(RangeError)
    expect(() => addMonths(parseYearMonth('9999-12'), 1)).toThrow(RangeError)
    expect(() =>
      addMonths(parseYearMonth('2026-07'), Number.MAX_SAFE_INTEGER),
    ).toThrow(RangeError)
    expect(() =>
      addMonths(parseYearMonth('2026-07'), Number.MIN_SAFE_INTEGER),
    ).toThrow(RangeError)
  })

  it.each([
    0.5,
    Number.NaN,
    Number.POSITIVE_INFINITY,
    Number.NEGATIVE_INFINITY,
    Number.MAX_SAFE_INTEGER + 1,
    Number.MIN_SAFE_INTEGER - 1,
  ])('rejects non-safe-integer amount %s', (amount) => {
    expect(() => addMonths(parseYearMonth('2026-07'), amount)).toThrow(
      TypeError,
    )
  })
})

describe('YearMonth boundaries and month lengths', () => {
  const COMMON_YEAR_LENGTHS = [
    31,
    28,
    31,
    30,
    31,
    30,
    31,
    31,
    30,
    31,
    30,
    31,
  ] as const

  it('returns the correct length and boundary dates for every month', () => {
    for (let monthNumber = 1; monthNumber <= 12; monthNumber += 1) {
      const month = parseYearMonth(
        `2026-${String(monthNumber).padStart(2, '0')}`,
      )
      const expectedLength = COMMON_YEAR_LENGTHS[monthNumber - 1]

      expect(daysInMonth(month)).toBe(expectedLength)
      expect(firstDateOfMonth(month)).toBe(`${month}-01`)
      expect(lastDateOfMonth(month)).toBe(
        `${month}-${String(expectedLength).padStart(2, '0')}`,
      )
      expect(parseLocalDate(firstDateOfMonth(month))).toBe(
        firstDateOfMonth(month),
      )
      expect(parseLocalDate(lastDateOfMonth(month))).toBe(lastDateOfMonth(month))
    }
  })

  it.each([
    ['2024-02', 29, '2024-02-29'],
    ['2026-02', 28, '2026-02-28'],
    ['1900-02', 28, '1900-02-28'],
    ['2000-02', 29, '2000-02-29'],
    ['0000-02', 29, '0000-02-29'],
    ['2026-04', 30, '2026-04-30'],
    ['2026-01', 31, '2026-01-31'],
    ['9999-12', 31, '9999-12-31'],
  ] as const)(
    'derives %s length and last date from LocalDate rules',
    (value, expectedLength, expectedLastDate) => {
      const month = parseYearMonth(value)
      expect(daysInMonth(month)).toBe(expectedLength)
      expect(lastDateOfMonth(month)).toBe(expectedLastDate)
    },
  )

  it('agrees with LocalDate day arithmetic at month boundaries', () => {
    for (let monthNumber = 1; monthNumber <= 12; monthNumber += 1) {
      const month = parseYearMonth(
        `2024-${String(monthNumber).padStart(2, '0')}`,
      )
      const nextMonth = addMonths(month, 1)
      expect(lastDateOfMonth(month)).toBe(
        addDays(firstDateOfMonth(nextMonth), -1),
      )
    }
  })
})

describe('Sunday-first weekday calculation', () => {
  it.each([
    ['0000-01-01', 6],
    ['0000-02-29', 2],
    ['0000-03-01', 3],
    ['1970-01-01', 4],
    ['2000-01-01', 6],
    ['2024-02-29', 4],
    ['2026-07-16', 4],
    ['9999-12-31', 5],
  ] as const)('maps %s to Sunday-first index %i', (value, expected) => {
    const result = getSundayFirstWeekdayIndex(parseLocalDate(value))
    expect(result).toBe(expected)
    expect(Number.isInteger(result)).toBe(true)
    expect(result).toBeGreaterThanOrEqual(0)
    expect(result).toBeLessThanOrEqual(6)
  })

  it('does not change when the process timezone changes', () => {
    const originalTimezone = process.env.TZ
    const date = parseLocalDate('2026-07-16')

    try {
      const results = [
        'UTC',
        'Pacific/Kiritimati',
        'America/Los_Angeles',
      ].map((timezone) => {
        process.env.TZ = timezone
        return getSundayFirstWeekdayIndex(date)
      })

      expect(results).toEqual([4, 4, 4])
    } finally {
      if (originalTimezone === undefined) {
        delete process.env.TZ
      } else {
        process.env.TZ = originalTimezone
      }
    }
  })

  it.each([
    '0000-01-01',
    '0000-02-28',
    '1899-12-31',
    '1900-02-28',
    '1999-12-31',
    '2000-02-28',
    '2024-02-28',
    '9999-12-30',
  ])('advances one weekday when LocalDate advances from %s', (value) => {
    const date = parseLocalDate(value)
    expect(getSundayFirstWeekdayIndex(addDays(date, 1))).toBe(
      (getSundayFirstWeekdayIndex(date) + 1) % 7,
    )
  })
})

describe('inclusive YearMonth iteration', () => {
  it('returns one month for an equal range', () => {
    expect(
      iterateYearMonthsInclusive(
        parseYearMonth('2026-07'),
        parseYearMonth('2026-07'),
      ),
    ).toEqual(['2026-07'])
  })

  it('returns exactly twelve ordered July-through-June months', () => {
    expect(
      iterateYearMonthsInclusive(
        parseYearMonth('2026-07'),
        parseYearMonth('2027-06'),
      ),
    ).toEqual([
      '2026-07',
      '2026-08',
      '2026-09',
      '2026-10',
      '2026-11',
      '2026-12',
      '2027-01',
      '2027-02',
      '2027-03',
      '2027-04',
      '2027-05',
      '2027-06',
    ])
  })

  it('covers the complete supported range without truncation', () => {
    const months = iterateYearMonthsInclusive(
      parseYearMonth('0000-01'),
      parseYearMonth('9999-12'),
    )

    expect(months).toHaveLength(120_000)
    expect(months[0]).toBe('0000-01')
    expect(months.at(-1)).toBe('9999-12')
  })

  it.each([
    ['2026-12', '2027-02', ['2026-12', '2027-01', '2027-02']],
    ['2099-12', '2100-02', ['2099-12', '2100-01', '2100-02']],
  ] as const)('iterates %s through %s', (start, end, expected) => {
    expect(
      iterateYearMonthsInclusive(
        parseYearMonth(start),
        parseYearMonth(end),
      ),
    ).toEqual(expected)
  })

  it('rejects reverse ranges', () => {
    expect(() =>
      iterateYearMonthsInclusive(
        parseYearMonth('2027-01'),
        parseYearMonth('2026-12'),
      ),
    ).toThrow(RangeError)
  })

  it('returns new frozen collections without mutating inputs', () => {
    const start = parseYearMonth('2026-12')
    const end = parseYearMonth('2027-02')
    const first = iterateYearMonthsInclusive(start, end)
    const second = iterateYearMonthsInclusive(start, end)

    expect(first).not.toBe(second)
    expect(Object.isFrozen(first)).toBe(true)
    expect(start).toBe('2026-12')
    expect(end).toBe('2027-02')
  })
})

describe('YearMonth architecture', () => {
  const source = readFileSync(
    new URL('../../src/domain/yearMonth.ts', import.meta.url),
    'utf8',
  )

  it('imports only the LocalDate domain module', () => {
    const importSources = [...source.matchAll(/\bfrom\s+['"]([^'"]+)['"]/g)].map(
      (match) => match[1],
    )

    expect(new Set(importSources)).toEqual(new Set(['./localDate']))
    expect(source).not.toMatch(/^\s*import\s+['"]/m)
    expect(source).not.toMatch(/\bimport\s*\(/)
  })

  it('contains no random, browser, Date, timezone, or locale API usage', () => {
    expect(source).not.toContain('Math.random')
    expect(source).not.toMatch(
      /\b(?:window|document|indexedDB|localStorage|sessionStorage|navigator|fetch|location|history|performance|Temporal|process)\b/,
    )
    expect(source).not.toMatch(/\bDate\s*\(/)
    expect(source).not.toMatch(/\bDate\s*\.\s*(?:parse|UTC|now)\s*\(/)
    expect(source).not.toMatch(/\bIntl\b|\.toLocale\w*\s*\(/)
  })
})
