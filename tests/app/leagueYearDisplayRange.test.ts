import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import {
  buildCalendarMonthGrid,
  buildLeagueYearMonthGrids,
} from '../../src/app/calendarMonthGrid'
import type {
  CalendarDayCellModel,
  CalendarMonthGridModel,
} from '../../src/app/calendarMonthGrid'
import {
  createLeagueYearDisplayRange,
} from '../../src/app/leagueYearDisplayRange'
import type { LeagueYearDisplayRange } from '../../src/app/leagueYearDisplayRange'
import {
  parseLeagueId,
  parseScheduleId,
  parseSeasonId,
} from '../../src/domain/ids'
import {
  addDays,
  compareLocalDates,
  parseLocalDate,
} from '../../src/domain/localDate'
import type { LocalDate } from '../../src/domain/localDate'
import {
  InvalidSeasonError,
  createSeason,
} from '../../src/domain/season'
import type { Season } from '../../src/domain/season'
import {
  getSundayFirstWeekdayIndex,
  parseYearMonth,
  yearMonthFromLocalDate,
} from '../../src/domain/yearMonth'
import type { YearMonth } from '../../src/domain/yearMonth'

function formatYear(year: number): string {
  return String(year).padStart(4, '0')
}

function createTestSeason(
  startingYear: number,
  endingYear = startingYear + 1,
): Season {
  const identitySuffix = `${formatYear(startingYear)}_${formatYear(endingYear)}`

  return createSeason({
    id: parseSeasonId(`season_calendar_${identitySuffix}`),
    leagueId: parseLeagueId('league_calendar_test'),
    seasonNumber: 1,
    startingYear,
    endingYear,
    rulesVersion: 1,
    currentDate: parseLocalDate(`${formatYear(startingYear)}-07-01`),
    currentPhase: 'regular_season',
    scheduleId: parseScheduleId(`schedule_calendar_${identitySuffix}`),
    status: 'schedule_ready',
  })
}

function flattenGrid(
  grid: CalendarMonthGridModel,
): readonly CalendarDayCellModel[] {
  return grid.weeks.flatMap((week) => week.days)
}

function datesFromFirstThroughLast(
  firstDate: LocalDate,
  lastDate: LocalDate,
): readonly LocalDate[] {
  const dates: LocalDate[] = []
  let date = firstDate

  while (compareLocalDates(date, lastDate) <= 0) {
    dates.push(date)
    if (date === lastDate) break
    date = addDays(date, 1)
  }

  return dates
}

function expectGridInvariants(
  grid: CalendarMonthGridModel,
  range: LeagueYearDisplayRange,
): void {
  expect(grid.weeks).toHaveLength(grid.weekCount)
  expect([4, 5, 6]).toContain(grid.weekCount)

  for (const week of grid.weeks) {
    expect(week.days).toHaveLength(7)
    expect(week.days[0].weekdayIndex).toBe(0)
    expect(week.days[6].weekdayIndex).toBe(6)

    week.days.forEach((cell, position) => {
      expect(cell.weekdayIndex).toBe(position)
      expect(cell.weekdayIndex).toBe(
        getSundayFirstWeekdayIndex(cell.date),
      )
      expect(cell.month).toBe(yearMonthFromLocalDate(cell.date))
      expect(cell.belongsToMonth).toBe(cell.month === grid.month)
      expect(cell.isWithinLeagueYear).toBe(
        compareLocalDates(cell.date, range.startDate) >= 0 &&
          compareLocalDates(cell.date, range.endDate) <= 0,
      )
      expect(Number.isInteger(cell.weekdayIndex)).toBe(true)
      expect(Object.keys(cell)).toEqual([
        'date',
        'month',
        'weekdayIndex',
        'belongsToMonth',
        'isWithinLeagueYear',
      ])
    })
  }

  const cells = flattenGrid(grid)
  for (let index = 1; index < cells.length; index += 1) {
    expect(cells[index].date).toBe(addDays(cells[index - 1].date, 1))
  }

  const expectedMonthDates = datesFromFirstThroughLast(
    grid.firstDate,
    grid.lastDate,
  )
  const actualMonthDates = cells
    .filter((cell) => cell.belongsToMonth)
    .map((cell) => cell.date)

  expect(actualMonthDates).toEqual(expectedMonthDates)
  expect(new Set(actualMonthDates).size).toBe(expectedMonthDates.length)
}

describe('LeagueYearDisplayRange', () => {
  it('derives the authoritative July-through-June range and twelve months', () => {
    const season = createTestSeason(2026)
    const range = createLeagueYearDisplayRange(season)

    expect(range).toEqual({
      startingYear: 2026,
      endingYear: 2027,
      startDate: '2026-07-01',
      endDate: '2027-06-30',
      startMonth: '2026-07',
      endMonth: '2027-06',
      seasonLabel: season.displayLabel,
      months: [
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
      ],
    })
    expect(range.months).toHaveLength(12)
    expect(range.seasonLabel).toBe('2026–27')
  })

  it.each([
    [0, '0000-07-01', '0001-06-30', '0000–01'],
    [99, '0099-07-01', '0100-06-30', '0099–0100'],
    [2099, '2099-07-01', '2100-06-30', '2099–2100'],
    [9998, '9998-07-01', '9999-06-30', '9998–99'],
  ] as const)(
    'supports starting year %i through its complete ending year',
    (startingYear, expectedStart, expectedEnd, expectedLabel) => {
      const range = createLeagueYearDisplayRange(
        createTestSeason(startingYear),
      )

      expect(range.startDate).toBe(expectedStart)
      expect(range.endDate).toBe(expectedEnd)
      expect(range.seasonLabel).toBe(expectedLabel)
      expect(range.months[5]).toBe(`${formatYear(startingYear)}-12`)
      expect(range.months[6]).toBe(
        `${formatYear(startingYear + 1)}-01`,
      )
    },
  )

  it('rejects a domain-valid season whose years are not adjacent', () => {
    const season = createTestSeason(2026, 2028)

    expect(() => createLeagueYearDisplayRange(season)).toThrow(RangeError)
  })

  it('retains existing Season validation for an unsupported ending year', () => {
    const source = {
      ...createTestSeason(9998),
      startingYear: 9999,
      endingYear: 10000,
      displayLabel: '9999–10000',
      currentDate: '9999-07-01',
    } as unknown as Season

    expect(() => createLeagueYearDisplayRange(source)).toThrow(
      InvalidSeasonError,
    )
  })

  it('freezes its data and does not mutate the supplied Season', () => {
    const season = createTestSeason(2026)
    const originalSeason = JSON.stringify(season)
    const range = createLeagueYearDisplayRange(season)

    expect(Object.isFrozen(range)).toBe(true)
    expect(Object.isFrozen(range.months)).toBe(true)
    expect(() =>
      (range.months as YearMonth[]).push(parseYearMonth('2027-07')),
    ).toThrow(TypeError)
    expect(JSON.stringify(season)).toBe(originalSeason)
  })
})

describe('calendar month-grid structures', () => {
  it.each([
    [2025, '2026-02', 4, 28, '2026-02-01', '2026-02-28'],
    [2026, '2026-07', 5, 31, '2026-06-28', '2026-08-01'],
    [2026, '2026-08', 6, 31, '2026-07-26', '2026-09-05'],
    [2023, '2024-02', 5, 29, '2024-01-28', '2024-03-02'],
    [1899, '1900-02', 5, 28, '1900-01-28', '1900-03-03'],
    [1999, '2000-02', 5, 29, '2000-01-30', '2000-03-04'],
  ] as const)(
    'builds %s as a %i-week grid with %i in-month dates',
    (
      startingYear,
      month,
      expectedWeeks,
      expectedInMonthDays,
      expectedGridStart,
      expectedGridEnd,
    ) => {
      const range = createLeagueYearDisplayRange(
        createTestSeason(startingYear),
      )
      const grid = buildCalendarMonthGrid(parseYearMonth(month), range)
      const cells = flattenGrid(grid)

      expect(grid.weekCount).toBe(expectedWeeks)
      expect(grid.weeks).toHaveLength(expectedWeeks)
      expect(cells.filter((cell) => cell.belongsToMonth)).toHaveLength(
        expectedInMonthDays,
      )
      expect(cells[0].date).toBe(expectedGridStart)
      expect(cells.at(-1)?.date).toBe(expectedGridEnd)
      expectGridInvariants(grid, range)
    },
  )

  it('uses real adjacent dates and keeps month and range flags independent', () => {
    const range = createLeagueYearDisplayRange(createTestSeason(2026))
    const july = buildCalendarMonthGrid(parseYearMonth('2026-07'), range)
    const august = buildCalendarMonthGrid(parseYearMonth('2026-08'), range)
    const june = buildCalendarMonthGrid(parseYearMonth('2027-06'), range)

    expect(flattenGrid(july).slice(0, 3)).toEqual([
      {
        date: '2026-06-28',
        month: '2026-06',
        weekdayIndex: 0,
        belongsToMonth: false,
        isWithinLeagueYear: false,
      },
      {
        date: '2026-06-29',
        month: '2026-06',
        weekdayIndex: 1,
        belongsToMonth: false,
        isWithinLeagueYear: false,
      },
      {
        date: '2026-06-30',
        month: '2026-06',
        weekdayIndex: 2,
        belongsToMonth: false,
        isWithinLeagueYear: false,
      },
    ])

    const augustTrailing = flattenGrid(august).at(-1)
    expect(augustTrailing).toMatchObject({
      date: '2026-09-05',
      month: '2026-09',
      belongsToMonth: false,
      isWithinLeagueYear: true,
    })

    expect(flattenGrid(june).at(-1)).toMatchObject({
      date: '2027-07-03',
      month: '2027-07',
      belongsToMonth: false,
      isWithinLeagueYear: false,
    })
  })

  it('preserves December-to-January padding across a year boundary', () => {
    const range = createLeagueYearDisplayRange(createTestSeason(2026))
    const december = buildCalendarMonthGrid(
      parseYearMonth('2026-12'),
      range,
    )
    const january = buildCalendarMonthGrid(
      parseYearMonth('2027-01'),
      range,
    )

    expect(flattenGrid(december)[0].date).toBe('2026-11-29')
    expect(flattenGrid(december).at(-1)?.date).toBe('2027-01-02')
    expect(flattenGrid(january)[0].date).toBe('2026-12-27')
    expect(flattenGrid(january).at(-1)?.date).toBe('2027-02-06')
    expectGridInvariants(december, range)
    expectGridInvariants(january, range)
  })

  it.each([
    [0, '0000-07', '0000-06-25'],
    [9998, '9999-06', '9999-07-03'],
  ] as const)(
    'keeps boundary padding valid for the league year starting %i',
    (startingYear, month, expectedBoundaryDate) => {
      const range = createLeagueYearDisplayRange(
        createTestSeason(startingYear),
      )
      const grid = buildCalendarMonthGrid(parseYearMonth(month), range)
      const cells = flattenGrid(grid)

      expect(
        startingYear === 0 ? cells[0].date : cells.at(-1)?.date,
      ).toBe(expectedBoundaryDate)
      for (const cell of cells) {
        expect(parseLocalDate(cell.date)).toBe(cell.date)
      }
      expectGridInvariants(grid, range)
    },
  )

  it('rejects requested months outside the supplied league-year range', () => {
    const range = createLeagueYearDisplayRange(createTestSeason(2026))

    expect(() =>
      buildCalendarMonthGrid(parseYearMonth('2026-06'), range),
    ).toThrow(RangeError)
    expect(() =>
      buildCalendarMonthGrid(parseYearMonth('2027-07'), range),
    ).toThrow(RangeError)
  })

  it('does not mutate its month or range inputs', () => {
    const range = createLeagueYearDisplayRange(createTestSeason(2026))
    const month = parseYearMonth('2026-08')
    const originalRange = JSON.stringify(range)

    buildCalendarMonthGrid(month, range)

    expect(month).toBe('2026-08')
    expect(JSON.stringify(range)).toBe(originalRange)
  })

  it('returns recursively frozen structural records and collections', () => {
    const range = createLeagueYearDisplayRange(createTestSeason(2026))
    const grid = buildCalendarMonthGrid(parseYearMonth('2026-08'), range)

    expect(Object.isFrozen(grid)).toBe(true)
    expect(Object.isFrozen(grid.weeks)).toBe(true)
    for (const week of grid.weeks) {
      expect(Object.isFrozen(week)).toBe(true)
      expect(Object.isFrozen(week.days)).toBe(true)
      for (const cell of week.days) {
        expect(Object.isFrozen(cell)).toBe(true)
      }
    }
    expect(Object.keys(grid)).toEqual([
      'month',
      'firstDate',
      'lastDate',
      'weeks',
      'weekCount',
    ])
  })

  it('produces stable values across process timezone settings', () => {
    const originalTimezone = process.env.TZ
    const range = createLeagueYearDisplayRange(createTestSeason(2026))

    try {
      const results = [
        'UTC',
        'Pacific/Kiritimati',
        'America/Los_Angeles',
      ].map((timezone) => {
        process.env.TZ = timezone
        return buildCalendarMonthGrid(parseYearMonth('2026-08'), range)
      })

      expect(results[0]).toEqual(results[1])
      expect(results[1]).toEqual(results[2])
    } finally {
      if (originalTimezone === undefined) {
        delete process.env.TZ
      } else {
        process.env.TZ = originalTimezone
      }
    }
  })
})

describe('full league-year month grids', () => {
  it('returns all twelve July-through-June grids, including empty months', () => {
    const range = createLeagueYearDisplayRange(createTestSeason(2026))
    const originalRange = JSON.stringify(range)
    const grids = buildLeagueYearMonthGrids(range)

    expect(grids).toHaveLength(12)
    expect(grids.map((grid) => grid.month)).toEqual(range.months)
    expect(grids[0].month).toBe('2026-07')
    expect(grids.at(-1)?.month).toBe('2027-06')
    expect(grids.every((grid) => grid.weeks.length >= 4)).toBe(true)
    expect(JSON.stringify(range)).toBe(originalRange)
  })

  it('represents every league-year date in its own month grid', () => {
    const range = createLeagueYearDisplayRange(createTestSeason(2026))
    const grids = buildLeagueYearMonthGrids(range)
    const ownMonthDates = new Set(
      grids.flatMap((grid) =>
        flattenGrid(grid)
          .filter((cell) => cell.belongsToMonth)
          .map((cell) => cell.date),
      ),
    )

    for (const date of datesFromFirstThroughLast(
      range.startDate,
      range.endDate,
    )) {
      expect(ownMonthDates.has(date)).toBe(true)
    }
  })

  it('freezes the full collection and all nested grid values', () => {
    const range = createLeagueYearDisplayRange(createTestSeason(2026))
    const grids = buildLeagueYearMonthGrids(range)

    expect(Object.isFrozen(grids)).toBe(true)
    for (const grid of grids) {
      expect(Object.isFrozen(grid)).toBe(true)
      expect(Object.isFrozen(grid.weeks)).toBe(true)
      for (const week of grid.weeks) {
        expect(Object.isFrozen(week)).toBe(true)
        expect(Object.isFrozen(week.days)).toBe(true)
        expect(week.days.every(Object.isFrozen)).toBe(true)
      }
    }
  })
})

describe('league-year calendar architecture', () => {
  const rangeSource = readFileSync(
    new URL('../../src/app/leagueYearDisplayRange.ts', import.meta.url),
    'utf8',
  )
  const gridSource = readFileSync(
    new URL('../../src/app/calendarMonthGrid.ts', import.meta.url),
    'utf8',
  )

  it('imports only the pure LocalDate, Season, YearMonth, and range modules', () => {
    const importSources = [rangeSource, gridSource].flatMap((source) =>
      [...source.matchAll(/\bfrom\s+['"]([^'"]+)['"]/g)].map(
        (match) => match[1],
      ),
    )

    expect(new Set(importSources)).toEqual(
      new Set([
        '../domain/localDate',
        '../domain/season',
        '../domain/yearMonth',
        './leagueYearDisplayRange',
      ]),
    )
    expect(importSources).not.toEqual(
      expect.arrayContaining([
        expect.stringMatching(/react|persist|storage|generation|schedule/i),
      ]),
    )
  })

  it('uses no random, browser, JavaScript Date, timezone, or locale APIs', () => {
    const source = `${rangeSource}\n${gridSource}`

    expect(source).not.toContain('Math.random')
    expect(source).not.toMatch(
      /\b(?:window|document|indexedDB|localStorage|sessionStorage|navigator|fetch|location|history|performance|Temporal|process)\b/,
    )
    expect(source).not.toMatch(/\bDate\s*\(/)
    expect(source).not.toMatch(/\bDate\s*\.\s*(?:parse|UTC|now)\s*\(/)
    expect(source).not.toMatch(/\bIntl\b|\.toLocale\w*\s*\(/)
  })
})
