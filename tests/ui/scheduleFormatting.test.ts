import { readFileSync } from 'node:fs'
import { afterEach, describe, expect, it } from 'vitest'
import type {
  ScheduledGameStatus,
  ScheduleStage,
} from '../../src/domain/schedule'
import { parseLocalDate } from '../../src/domain/localDate'
import { parseYearMonth } from '../../src/domain/yearMonth'
import {
  formatScheduledGameStatus,
  formatScheduleDateLong,
  formatScheduleDateShort,
  formatScheduleMonthHeading,
  formatScheduleStage,
} from '../../src/ui/scheduleFormatting'

const originalTimezone = process.env.TZ

afterEach(() => {
  process.env.TZ = originalTimezone
})

describe('Team Schedule English formatting', () => {
  it.each([
    ['0000-01', 'January 0000'],
    ['2026-10', 'October 2026'],
    ['9999-12', 'December 9999'],
  ])('formats canonical month %s as %s', (month, expected) => {
    expect(formatScheduleMonthHeading(parseYearMonth(month))).toBe(expected)
  })

  it.each([
    ['1970-01-01', 'Thu, Jan 1', 'January 1, 1970'],
    ['2024-02-29', 'Thu, Feb 29', 'February 29, 2024'],
    ['2026-10-06', 'Tue, Oct 6', 'October 6, 2026'],
    ['2026-12-25', 'Fri, Dec 25', 'December 25, 2026'],
  ])(
    'formats %s deterministically',
    (date, expectedShort, expectedLong) => {
      const parsed = parseLocalDate(date)
      expect(formatScheduleDateShort(parsed)).toBe(expectedShort)
      expect(formatScheduleDateLong(parsed)).toBe(expectedLong)
    },
  )

  it('is unchanged by the host timezone', () => {
    const date = parseLocalDate('2026-10-06')

    process.env.TZ = 'Pacific/Kiritimati'
    const positiveOffset = [
      formatScheduleDateShort(date),
      formatScheduleDateLong(date),
    ]
    process.env.TZ = 'America/Adak'
    const negativeOffset = [
      formatScheduleDateShort(date),
      formatScheduleDateLong(date),
    ]

    expect(positiveOffset).toEqual(['Tue, Oct 6', 'October 6, 2026'])
    expect(negativeOffset).toEqual(positiveOffset)
  })

  it.each([
    ['scheduled', 'Scheduled'],
    ['completed', 'Completed'],
    ['postponed', 'Postponed'],
    ['cancelled', 'Cancelled'],
  ] satisfies readonly (readonly [ScheduledGameStatus, string])[])(
    'maps game status %s exhaustively',
    (status, expected) => {
      expect(formatScheduledGameStatus(status)).toBe(expected)
    },
  )

  it.each([
    ['preseason', 'Preseason'],
    ['regular_season', 'Regular season'],
    ['cup', 'Cup'],
    ['play_in', 'Play-In'],
    ['postseason', 'Postseason'],
  ] satisfies readonly (readonly [ScheduleStage, string])[])(
    'maps schedule stage %s exhaustively',
    (stage, expected) => {
      expect(formatScheduleStage(stage)).toBe(expected)
    },
  )

  it('rejects malformed values instead of normalizing or inventing labels', () => {
    expect(() => formatScheduleMonthHeading('2026-1' as never)).toThrow()
    expect(() => formatScheduleDateShort('2026-02-30' as never)).toThrow()
    expect(() => formatScheduleDateLong(' 2026-10-06' as never)).toThrow()
    expect(() =>
      formatScheduledGameStatus('unknown' as ScheduledGameStatus),
    ).toThrow(/unsupported/)
    expect(() => formatScheduleStage('unknown' as ScheduleStage)).toThrow(
      /unsupported/,
    )
  })
})

describe('schedule formatting architecture', () => {
  const source = readFileSync(
    new URL('../../src/ui/scheduleFormatting.ts', import.meta.url),
    'utf8',
  )

  it('uses no clock, timezone conversion, Date, Intl, or locale API', () => {
    expect(source).not.toMatch(/\bnew\s+Date\b|\bDate\s*\(/)
    expect(source).not.toMatch(/\bDate\s*\.\s*(?:parse|UTC|now)\s*\(/)
    expect(source).not.toMatch(/\bIntl\b|\.toLocale\w*\s*\(/)
    expect(source).not.toMatch(
      /\b(?:window|document|navigator|performance|Temporal)\b/,
    )
  })
})
