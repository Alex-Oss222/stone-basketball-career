import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import {
  createLeagueYearCalendarModel,
  InvalidLeagueYearCalendarModelError,
} from '../../src/app/enrichedCalendarViewModel'
import type {
  CalendarScope,
  LeagueYearCalendarModel,
} from '../../src/app/enrichedCalendarViewModel'
import {
  buildLeagueYearMonthGrids,
} from '../../src/app/calendarMonthGrid'
import {
  createCalendarEntries,
} from '../../src/app/calendarViewModel'
import type {
  CalendarEntryKind,
  CalendarEntryViewModel,
} from '../../src/app/calendarViewModel'
import {
  createLeagueYearDisplayRange,
} from '../../src/app/leagueYearDisplayRange'
import {
  parseCalendarEventId,
} from '../../src/domain/ids'
import type { TeamId } from '../../src/domain/ids'
import {
  compareLocalDates,
  parseLocalDate,
} from '../../src/domain/localDate'
import type { LocalDate } from '../../src/domain/localDate'
import {
  FIXTURE_MANAGED_TEAM_ID,
  createLeagueSeasonDomainFixture,
} from '../persistence/leagueSnapshot.fixture'

type EnrichedDayCell =
  LeagueYearCalendarModel['months'][number]['weeks'][number]['days'][number]

function createFixtureInput(
  scope: CalendarScope = 'all_teams',
  managedTeamId: TeamId | null = FIXTURE_MANAGED_TEAM_ID,
) {
  const fixture = createLeagueSeasonDomainFixture(managedTeamId)
  const range = createLeagueYearDisplayRange(fixture.foundation.season)
  const monthGrids = buildLeagueYearMonthGrids(range)
  const entries = createCalendarEntries({
    league: fixture.league,
    schedule: fixture.foundation.schedule,
    seasonCalendar: fixture.foundation.calendar,
    managedTeamId: fixture.managedTeamId,
  })

  return {
    range,
    monthGrids,
    entries,
    currentDate: fixture.foundation.season.currentDate,
    selectedDate: null,
    scope,
    managedTeamId: fixture.managedTeamId,
    maxVisibleEntriesPerDay: 3,
  } as const
}

function getAllCells(
  model: LeagueYearCalendarModel,
): readonly EnrichedDayCell[] {
  return model.months.flatMap((month) =>
    month.weeks.flatMap((week) => week.days),
  )
}

function getCellsForDate(
  model: LeagueYearCalendarModel,
  date: LocalDate,
): readonly EnrichedDayCell[] {
  return getAllCells(model).filter((cell) => cell.date === date)
}

function getOwningCell(
  model: LeagueYearCalendarModel,
  date: LocalDate,
): EnrichedDayCell {
  const cells = getCellsForDate(model, date).filter(
    (cell) => cell.belongsToMonth,
  )
  if (cells.length !== 1) {
    throw new Error(`Expected one owning calendar cell for ${date}`)
  }
  return cells[0]
}

function getEntryPriority(
  kind: CalendarEntryKind,
  isManagedTeamEntry: boolean,
): 0 | 1 | 2 | 3 | 4 {
  if (kind === 'league_event') return 0
  if (kind === 'game') return isManagedTeamEntry ? 1 : 2
  return isManagedTeamEntry ? 3 : 4
}

function createSortKey(
  entryId: string,
  kind: CalendarEntryKind,
  date: LocalDate | null,
  isManagedTeamEntry: boolean,
): string {
  return `${date === null ? '1' : '0'}:${date ?? '----------'}:${getEntryPriority(
    kind,
    isManagedTeamEntry,
  )}:${entryId}`
}

function patchEntry(
  entry: CalendarEntryViewModel,
  patch: Partial<CalendarEntryViewModel>,
): CalendarEntryViewModel {
  const source = { ...entry, ...patch }
  return Object.freeze({
    ...source,
    teamIds: Object.freeze([...source.teamIds]),
    sortKey: createSortKey(
      source.entryId,
      source.kind,
      source.date,
      source.isManagedTeamEntry,
    ),
  })
}

function createSyntheticEventEntry({
  id,
  date,
  teamId = null,
  managedTeamId,
}: {
  readonly id: string
  readonly date: LocalDate | null
  readonly teamId?: TeamId | null
  readonly managedTeamId: TeamId | null
}): CalendarEntryViewModel {
  const sourceId = parseCalendarEventId(id)
  const entryId = `calendar-event:${sourceId}`
  const kind = teamId === null ? 'league_event' : 'team_event'
  const teamIds = Object.freeze(teamId === null ? [] : [teamId])
  const isManagedTeamEntry =
    managedTeamId !== null && teamIds.includes(managedTeamId)

  return Object.freeze({
    entryId,
    sourceId,
    kind,
    date,
    originalDate: date,
    currentScheduledDate: date,
    actualDate: null,
    status: date === null ? 'tba' : 'scheduled',
    competitionStage: null,
    title: `Synthetic event ${id}`,
    shortLabel: `Synthetic event ${id}`,
    teamIds,
    isManagedTeamEntry,
    homeTeamId: null,
    awayTeamId: null,
    gameDayId: null,
    calendarEventKind: 'draft_event',
    sortKey: createSortKey(entryId, kind, date, isManagedTeamEntry),
  })
}

function expectStructuredError(
  operation: () => unknown,
  code?: string,
): void {
  try {
    operation()
    throw new Error('Expected calendar model construction to fail')
  } catch (error) {
    expect(error).toBeInstanceOf(InvalidLeagueYearCalendarModelError)
    if (code !== undefined) {
      expect(
        (error as InvalidLeagueYearCalendarModelError).code,
      ).toBe(code)
    }
  }
}

describe('enriched calendar structural preservation', () => {
  it('preserves all twelve structural month grids without mutation', () => {
    const input = createFixtureInput()
    const before = JSON.stringify(input.monthGrids)
    const model = createLeagueYearCalendarModel(input)

    expect(model.months).toHaveLength(12)
    expect(model.months.map((month) => month.month)).toEqual(
      input.range.months,
    )

    model.months.forEach((month, monthIndex) => {
      const structuralMonth = input.monthGrids[monthIndex]
      expect(month.weekCount).toBe(structuralMonth.weekCount)
      expect(month.weeks).toHaveLength(structuralMonth.weeks.length)

      month.weeks.forEach((week, weekIndex) => {
        const structuralWeek = structuralMonth.weeks[weekIndex]
        expect(week.days).toHaveLength(7)
        expect(
          week.days.map(
            ({
              date,
              month: cellMonth,
              weekdayIndex,
              belongsToMonth,
              isWithinLeagueYear,
            }) => ({
              date,
              month: cellMonth,
              weekdayIndex,
              belongsToMonth,
              isWithinLeagueYear,
            }),
          ),
        ).toEqual(structuralWeek.days)
      })
    })

    expect(JSON.stringify(input.monthGrids)).toBe(before)
  })
})

describe('enriched calendar scope', () => {
  it('includes every normalized entry for all-teams scope', () => {
    const input = createFixtureInput('all_teams')
    const model = createLeagueYearCalendarModel(input)

    expect(input.entries).toHaveLength(114)
    expect(model.totalEntryCount).toBe(114)
    expect(model.datedEntryCount).toBe(114)
    expect(model.undatedEntryCount).toBe(0)
    expect(model.outOfRangeEntryCount).toBe(0)
    expect(model.datedEntries.map((entry) => entry.entryId)).toEqual(
      input.entries.map((entry) => entry.entryId),
    )
  })

  it('keeps managed-team entries and league events while excluding unrelated entries', () => {
    const input = createFixtureInput('managed_team')
    const before = JSON.stringify(input.entries)
    const model = createLeagueYearCalendarModel(input)

    expect(model.totalEntryCount).toBe(30)
    expect(
      model.datedEntries.filter((entry) => entry.kind === 'game'),
    ).toHaveLength(28)
    expect(
      model.datedEntries.filter((entry) => entry.kind === 'league_event'),
    ).toHaveLength(2)
    expect(
      model.datedEntries.every(
        (entry) =>
          entry.isManagedTeamEntry || entry.kind === 'league_event',
      ),
    ).toBe(true)
    expect(
      model.datedEntries.filter(
        (entry) =>
          entry.kind === 'game' &&
          entry.homeTeamId === input.managedTeamId,
      ),
    ).toHaveLength(14)
    expect(
      model.datedEntries.filter(
        (entry) =>
          entry.kind === 'game' &&
          entry.awayTeamId === input.managedTeamId,
      ),
    ).toHaveLength(14)
    expect(JSON.stringify(input.entries)).toBe(before)
  })

  it('allows all-teams scope without managed-team context', () => {
    const input = createFixtureInput('all_teams', null)
    const model = createLeagueYearCalendarModel(input)

    expect(model.totalEntryCount).toBe(114)
    expect(
      model.datedEntries.every((entry) => !entry.isManagedTeamEntry),
    ).toBe(true)
  })

  it('rejects managed-team scope without managed-team context', () => {
    const input = createFixtureInput('managed_team', null)

    expectStructuredError(
      () => createLeagueYearCalendarModel(input),
      'managed_team_context_required',
    )
  })
})

describe('entry placement and completeness', () => {
  it('places entries by exact LocalDate and retains padding continuity without authoritative duplication', () => {
    const input = createFixtureInput()
    const model = createLeagueYearCalendarModel(input)
    const decemberFirst = parseLocalDate('2026-12-01')
    const matchingCells = getCellsForDate(model, decemberFirst)
    const sourceEntries = input.entries.filter(
      (entry) => entry.date === decemberFirst,
    )

    expect(sourceEntries).toHaveLength(4)
    expect(matchingCells).toHaveLength(2)
    expect(matchingCells.map((cell) => cell.belongsToMonth).sort()).toEqual([
      false,
      true,
    ])
    for (const cell of matchingCells) {
      expect(cell.entries).toEqual(sourceEntries)
    }
    for (const entry of sourceEntries) {
      expect(
        model.datedEntries.filter(
          (candidate) => candidate.entryId === entry.entryId,
        ),
      ).toHaveLength(1)
    }

    const ownCellOccurrences = model.months.flatMap((month) =>
      month.weeks.flatMap((week) =>
        week.days
          .filter((cell) => cell.belongsToMonth)
          .flatMap((cell) => cell.entries),
      ),
    )
    expect(ownCellOccurrences).toHaveLength(114)
    expect(new Set(ownCellOccurrences.map((entry) => entry.entryId)).size)
      .toBe(114)
  })

  it('uses placement date rather than GameDay identity and preserves date history', () => {
    const input = createFixtureInput()
    const source = input.entries.find((entry) => entry.kind === 'game')
    if (source === undefined) throw new Error('Fixture game is missing')

    const replacementDate = parseLocalDate('2026-07-02')
    const moved = patchEntry(source, {
      date: replacementDate,
      currentScheduledDate: replacementDate,
    })
    const entries = Object.freeze(
      input.entries.map((entry) =>
        entry.entryId === source.entryId ? moved : entry,
      ),
    )
    const originalDateHistory = {
      originalDate: moved.originalDate,
      currentScheduledDate: moved.currentScheduledDate,
      actualDate: moved.actualDate,
      gameDayId: moved.gameDayId,
    }
    const model = createLeagueYearCalendarModel({ ...input, entries })

    expect(
      getOwningCell(model, replacementDate).entries.map(
        (entry) => entry.entryId,
      ),
    ).toContain(moved.entryId)
    expect(
      getOwningCell(model, source.date as LocalDate).entries.map(
        (entry) => entry.entryId,
      ),
    ).not.toContain(moved.entryId)
    expect(moved).toMatchObject(originalDateHistory)
  })
})

describe('current and selected dates', () => {
  it('derives mutually exclusive temporal markers from supplied currentDate', () => {
    const input = createFixtureInput()
    const model = createLeagueYearCalendarModel(input)
    const owningCurrentCells = getAllCells(model).filter(
      (cell) =>
        cell.belongsToMonth &&
        cell.date === input.currentDate &&
        cell.isCurrentDate,
    )

    expect(owningCurrentCells).toHaveLength(1)
    for (const cell of getAllCells(model)) {
      const comparison = compareLocalDates(cell.date, input.currentDate)
      expect(cell.isCurrentDate).toBe(comparison === 0)
      expect(cell.isPastDate).toBe(comparison < 0)
      expect(cell.isFutureDate).toBe(comparison > 0)
      expect(
        [cell.isCurrentDate, cell.isPastDate, cell.isFutureDate].filter(
          Boolean,
        ),
      ).toHaveLength(1)
    }
  })

  it('produces no selection or agenda for a null selected date', () => {
    const model = createLeagueYearCalendarModel(createFixtureInput())

    expect(model.selectedDate).toBeNull()
    expect(model.selectedDayAgenda).toBeNull()
    expect(getAllCells(model).every((cell) => !cell.isSelectedDate)).toBe(
      true,
    )
  })

  it('marks one owning cell and creates a complete untruncated selected-day agenda', () => {
    const input = {
      ...createFixtureInput(),
      selectedDate: parseLocalDate('2026-10-05'),
      maxVisibleEntriesPerDay: 2,
    }
    const model = createLeagueYearCalendarModel(input)
    const selectedCells = getAllCells(model).filter(
      (cell) => cell.isSelectedDate,
    )
    const agenda = model.selectedDayAgenda

    expect(selectedCells).toHaveLength(1)
    expect(selectedCells[0].belongsToMonth).toBe(true)
    expect(agenda).not.toBeNull()
    expect(agenda?.entries).toHaveLength(5)
    expect(agenda?.managedTeamEntries).toHaveLength(1)
    expect(agenda?.leagueEvents).toHaveLength(1)
    expect(agenda?.otherEntries).toHaveLength(3)
    expect(agenda?.isEmpty).toBe(false)
    expect(agenda?.entries).toEqual(
      getOwningCell(model, input.selectedDate).entries,
    )
  })

  it('represents an explicitly selected empty day without fabricating an agenda entry', () => {
    const selectedDate = parseLocalDate('2026-07-01')
    const model = createLeagueYearCalendarModel({
      ...createFixtureInput(),
      selectedDate,
    })

    expect(getOwningCell(model, selectedDate).isSelectedDate).toBe(true)
    expect(model.selectedDayAgenda).toMatchObject({
      date: selectedDate,
      entries: [],
      managedTeamEntries: [],
      leagueEvents: [],
      otherEntries: [],
      isEmpty: true,
    })
  })

  it('is stable across process timezone changes', () => {
    const input = {
      ...createFixtureInput(),
      selectedDate: parseLocalDate('2026-12-01'),
    }
    const originalTimezone = process.env.TZ

    try {
      const results = [
        'UTC',
        'Pacific/Kiritimati',
        'America/Los_Angeles',
      ].map((timezone) => {
        process.env.TZ = timezone
        return createLeagueYearCalendarModel(input)
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

describe('visible-entry overflow', () => {
  it.each([
    [2, 2, 3],
    [5, 5, 0],
    [6, 5, 0],
  ] as const)(
    'partitions a five-entry date at limit %i',
    (limit, expectedVisible, expectedOverflow) => {
      const input = {
        ...createFixtureInput(),
        maxVisibleEntriesPerDay: limit,
      }
      const model = createLeagueYearCalendarModel(input)
      const cell = getOwningCell(model, parseLocalDate('2026-10-05'))

      expect(cell.entries).toHaveLength(5)
      expect(cell.visibleEntries).toEqual(
        cell.entries.slice(0, expectedVisible),
      )
      expect(cell.overflowEntries).toEqual(
        cell.entries.slice(expectedVisible),
      )
      expect(cell.overflowEntries).toHaveLength(expectedOverflow)
      expect(cell.overflowCount).toBe(expectedOverflow)
      expect([...cell.visibleEntries, ...cell.overflowEntries]).toEqual(
        cell.entries,
      )
      expect(
        new Set(
          [...cell.visibleEntries, ...cell.overflowEntries].map(
            (entry) => entry.entryId,
          ),
        ).size,
      ).toBe(cell.entries.length)
    },
  )

  it('keeps an empty date honest with no overflow', () => {
    const model = createLeagueYearCalendarModel(createFixtureInput())
    const cell = getOwningCell(model, parseLocalDate('2026-07-01'))

    expect(cell.entries).toEqual([])
    expect(cell.visibleEntries).toEqual([])
    expect(cell.overflowEntries).toEqual([])
    expect(cell.overflowCount).toBe(0)
  })
})

describe('month summaries', () => {
  it('counts only owning-month dates and leaves empty months present', () => {
    const model = createLeagueYearCalendarModel(createFixtureInput())
    const october = model.months.find((month) => month.month === '2026-10')
    const november = model.months.find((month) => month.month === '2026-11')
    const december = model.months.find((month) => month.month === '2026-12')
    const july = model.months.find((month) => month.month === '2026-07')

    expect(october).toMatchObject({
      datedEntryCount: 37,
      managedTeamEntryCount: 9,
      gameEntryCount: 36,
      eventEntryCount: 1,
      hasEntries: true,
    })
    expect(november).toMatchObject({
      datedEntryCount: 40,
      managedTeamEntryCount: 10,
      gameEntryCount: 40,
      eventEntryCount: 0,
      hasEntries: true,
    })
    expect(december).toMatchObject({
      datedEntryCount: 37,
      managedTeamEntryCount: 9,
      gameEntryCount: 36,
      eventEntryCount: 1,
      hasEntries: true,
    })
    expect(july).toMatchObject({
      datedEntryCount: 0,
      managedTeamEntryCount: 0,
      gameEntryCount: 0,
      eventEntryCount: 0,
      hasEntries: false,
    })

    const novemberPaddingCount = november?.weeks
      .flatMap((week) => week.days)
      .filter((cell) => !cell.belongsToMonth)
      .reduce((count, cell) => count + cell.entries.length, 0)
    expect(novemberPaddingCount).toBe(8)
    expect(november?.datedEntryCount).toBe(40)
  })

  it('summarizes the managed scope without treating league events as managed', () => {
    const model = createLeagueYearCalendarModel(
      createFixtureInput('managed_team'),
    )
    const summaries = model.months
      .filter((month) => month.hasEntries)
      .map((month) => ({
        month: month.month,
        dated: month.datedEntryCount,
        managed: month.managedTeamEntryCount,
        games: month.gameEntryCount,
        events: month.eventEntryCount,
      }))

    expect(summaries).toEqual([
      {
        month: '2026-10',
        dated: 10,
        managed: 9,
        games: 9,
        events: 1,
      },
      {
        month: '2026-11',
        dated: 10,
        managed: 10,
        games: 10,
        events: 0,
      },
      {
        month: '2026-12',
        dated: 10,
        managed: 9,
        games: 9,
        events: 1,
      },
    ])
  })
})

describe('undated and out-of-range entries', () => {
  it('keeps every undated entry separate and partitions it by authoritative kind', () => {
    const input = createFixtureInput()
    const managedGame = input.entries.find(
      (entry) => entry.kind === 'game' && entry.isManagedTeamEntry,
    )
    if (managedGame === undefined) {
      throw new Error('Managed fixture game is missing')
    }
    const otherTeamId = createLeagueSeasonDomainFixture().league.teams.find(
      (team) => team.id !== input.managedTeamId,
    )?.id
    if (otherTeamId === undefined) {
      throw new Error('Other fixture team is missing')
    }

    const undatedGame = patchEntry(managedGame, {
      date: null,
      currentScheduledDate: null,
      status: 'postponed',
    })
    const addedEntries = [
      createSyntheticEventEntry({
        id: 'calendar_event_m25_undated_league',
        date: null,
        managedTeamId: input.managedTeamId,
      }),
      createSyntheticEventEntry({
        id: 'calendar_event_m25_undated_managed',
        date: null,
        teamId: input.managedTeamId,
        managedTeamId: input.managedTeamId,
      }),
      createSyntheticEventEntry({
        id: 'calendar_event_m25_undated_other',
        date: null,
        teamId: otherTeamId,
        managedTeamId: input.managedTeamId,
      }),
    ] as const
    const entries = Object.freeze([
      ...input.entries.map((entry) =>
        entry.entryId === managedGame.entryId ? undatedGame : entry,
      ),
      ...addedEntries,
    ])
    const model = createLeagueYearCalendarModel({ ...input, entries })

    expect(model.totalEntryCount).toBe(117)
    expect(model.datedEntryCount).toBe(113)
    expect(model.undatedEntryCount).toBe(4)
    expect(model.undatedEntries.count).toBe(4)
    expect(model.undatedEntries.games).toHaveLength(1)
    expect(model.undatedEntries.leagueEvents).toHaveLength(1)
    expect(model.undatedEntries.teamEvents).toHaveLength(2)
    expect(model.undatedEntries.managedTeamEntries).toHaveLength(2)
    expect(model.undatedEntries.isEmpty).toBe(false)
    expect(
      getAllCells(model).flatMap((cell) => cell.entries).some(
        (entry) => entry.date === null,
      ),
    ).toBe(false)
    expect(
      model.undatedEntries.entries.every((entry) => entry.date === null),
    ).toBe(true)
  })

  it('applies managed scope to undated entries without fabricating dates', () => {
    const input = createFixtureInput('managed_team')
    const managedGame = input.entries.find(
      (entry) => entry.kind === 'game' && entry.isManagedTeamEntry,
    )
    if (managedGame === undefined) {
      throw new Error('Managed fixture game is missing')
    }
    const otherTeamId = createLeagueSeasonDomainFixture().league.teams.find(
      (team) => team.id !== input.managedTeamId,
    )?.id
    if (otherTeamId === undefined) {
      throw new Error('Other fixture team is missing')
    }

    const entries = Object.freeze([
      ...input.entries.map((entry) =>
        entry.entryId === managedGame.entryId
          ? patchEntry(entry, {
              date: null,
              currentScheduledDate: null,
              status: 'postponed',
            })
          : entry,
      ),
      createSyntheticEventEntry({
        id: 'calendar_event_m25_scope_league',
        date: null,
        managedTeamId: input.managedTeamId,
      }),
      createSyntheticEventEntry({
        id: 'calendar_event_m25_scope_managed',
        date: null,
        teamId: input.managedTeamId,
        managedTeamId: input.managedTeamId,
      }),
      createSyntheticEventEntry({
        id: 'calendar_event_m25_scope_other',
        date: null,
        teamId: otherTeamId,
        managedTeamId: input.managedTeamId,
      }),
    ])
    const model = createLeagueYearCalendarModel({ ...input, entries })

    expect(model.undatedEntries.entries).toHaveLength(3)
    expect(
      model.undatedEntries.entries.some(
        (entry) =>
          entry.entryId ===
          'calendar-event:calendar_event_m25_scope_other',
      ),
    ).toBe(false)
    expect(
      model.undatedEntries.entries.every(
        (entry) =>
          entry.isManagedTeamEntry || entry.kind === 'league_event',
      ),
    ).toBe(true)
  })

  it('accounts for outside entries separately while preserving exact-date padding continuity', () => {
    const input = createFixtureInput()
    const outsideDate = parseLocalDate('2027-07-01')
    const outside = createSyntheticEventEntry({
      id: 'calendar_event_m25_outside_range',
      date: outsideDate,
      managedTeamId: input.managedTeamId,
    })
    const entries = Object.freeze([...input.entries, outside])
    const model = createLeagueYearCalendarModel({ ...input, entries })

    expect(model.totalEntryCount).toBe(115)
    expect(model.datedEntryCount).toBe(114)
    expect(model.undatedEntryCount).toBe(0)
    expect(model.outOfRangeEntryCount).toBe(1)
    expect(model.outOfRangeEntries).toEqual([outside])
    expect(getCellsForDate(model, outsideDate)).toHaveLength(1)
    expect(getCellsForDate(model, outsideDate)[0]).toMatchObject({
      belongsToMonth: false,
      isWithinLeagueYear: false,
      entries: [outside],
    })
    expect(
      getAllCells(model)
        .flatMap((cell) => cell.entries)
        .filter((entry) => entry.entryId === outside.entryId),
    ).toHaveLength(1)
    expect(
      model.months.find((month) => month.month === '2027-06'),
    ).toMatchObject({
      datedEntryCount: 0,
      gameEntryCount: 0,
      eventEntryCount: 0,
      hasEntries: false,
    })
  })
})

describe('validation', () => {
  it('rejects incomplete and reordered structural grids', () => {
    const input = createFixtureInput()

    expectStructuredError(() =>
      createLeagueYearCalendarModel({
        ...input,
        monthGrids: Object.freeze(input.monthGrids.slice(0, 11)),
      }),
    )
    expectStructuredError(() =>
      createLeagueYearCalendarModel({
        ...input,
        monthGrids: Object.freeze([
          input.monthGrids[1],
          input.monthGrids[0],
          ...input.monthGrids.slice(2),
        ]),
      }),
    )
  })

  it('rejects an inconsistent range', () => {
    const input = createFixtureInput()

    expectStructuredError(() =>
      createLeagueYearCalendarModel({
        ...input,
        range: {
          ...input.range,
          endDate: parseLocalDate('2027-06-29'),
        },
      }),
    )
  })

  it.each([
    0,
    -1,
    1.5,
    Number.NaN,
    Number.POSITIVE_INFINITY,
    Number.MAX_SAFE_INTEGER + 1,
  ])('rejects invalid visible-entry limit %s', (limit) => {
    const input = createFixtureInput()

    expectStructuredError(() =>
      createLeagueYearCalendarModel({
        ...input,
        maxVisibleEntriesPerDay: limit,
      }),
    )
  })

  it('rejects malformed or out-of-range current and selected dates', () => {
    const input = createFixtureInput()

    expectStructuredError(() =>
      createLeagueYearCalendarModel({
        ...input,
        currentDate: '2026-02-30' as LocalDate,
      }),
    )
    expectStructuredError(() =>
      createLeagueYearCalendarModel({
        ...input,
        currentDate: parseLocalDate('2026-06-30'),
      }),
    )
    expectStructuredError(() =>
      createLeagueYearCalendarModel({
        ...input,
        selectedDate: parseLocalDate('2027-07-01'),
      }),
    )
  })

  it('rejects duplicate entry IDs and malformed placement dates', () => {
    const input = createFixtureInput()
    const first = input.entries[0]

    expectStructuredError(() =>
      createLeagueYearCalendarModel({
        ...input,
        entries: Object.freeze([...input.entries, first]),
      }),
    )
    expectStructuredError(() =>
      createLeagueYearCalendarModel({
        ...input,
        entries: Object.freeze([
          patchEntry(first, {
            date: '2026-02-30' as LocalDate,
          }),
          ...input.entries.slice(1),
        ]),
      }),
    )
  })
})

describe('determinism, restoration, and immutability', () => {
  it('is deterministic for reordered inputs and never mutates source values', () => {
    const input = {
      ...createFixtureInput(),
      selectedDate: parseLocalDate('2026-10-05'),
      maxVisibleEntriesPerDay: 2,
    }
    const before = JSON.stringify(input)
    const first = createLeagueYearCalendarModel(input)
    const second = createLeagueYearCalendarModel(input)
    const reversed = createLeagueYearCalendarModel({
      ...input,
      entries: Object.freeze([...input.entries].reverse()),
    })

    expect(second).toEqual(first)
    expect(reversed).toEqual(first)
    expect(JSON.stringify(input)).toBe(before)
  })

  it('is deeply identical after JSON restoration and authoritative renormalization', () => {
    const fixture = createLeagueSeasonDomainFixture()
    const restored = JSON.parse(JSON.stringify(fixture)) as typeof fixture
    const baselineInput = createFixtureInput()
    const restoredRange = createLeagueYearDisplayRange(
      restored.foundation.season,
    )
    const restoredEntries = createCalendarEntries({
      league: restored.league,
      schedule: restored.foundation.schedule,
      seasonCalendar: restored.foundation.calendar,
      managedTeamId: restored.managedTeamId,
    })
    const restoredModel = createLeagueYearCalendarModel({
      range: restoredRange,
      monthGrids: buildLeagueYearMonthGrids(restoredRange),
      entries: restoredEntries,
      currentDate: restored.foundation.season.currentDate,
      selectedDate: null,
      scope: 'all_teams',
      managedTeamId: restored.managedTeamId,
      maxVisibleEntriesPerDay: 3,
    })

    expect(restoredModel).toEqual(
      createLeagueYearCalendarModel(baselineInput),
    )
  })

  it('recursively freezes every derived model and collection', () => {
    const input = {
      ...createFixtureInput(),
      selectedDate: parseLocalDate('2026-10-05'),
    }
    const model = createLeagueYearCalendarModel(input)

    expect(Object.isFrozen(model)).toBe(true)
    expect(Object.isFrozen(model.months)).toBe(true)
    expect(Object.isFrozen(model.datedEntries)).toBe(true)
    expect(Object.isFrozen(model.outOfRangeEntries)).toBe(true)
    expect(Object.isFrozen(model.undatedEntries)).toBe(true)
    expect(Object.isFrozen(model.undatedEntries.entries)).toBe(true)
    expect(Object.isFrozen(model.undatedEntries.games)).toBe(true)
    expect(Object.isFrozen(model.undatedEntries.leagueEvents)).toBe(true)
    expect(Object.isFrozen(model.undatedEntries.teamEvents)).toBe(true)
    expect(Object.isFrozen(model.undatedEntries.managedTeamEntries)).toBe(
      true,
    )
    expect(Object.isFrozen(model.selectedDayAgenda)).toBe(true)
    expect(Object.isFrozen(model.selectedDayAgenda?.entries)).toBe(true)
    expect(Object.isFrozen(model.selectedDayAgenda?.managedTeamEntries)).toBe(
      true,
    )
    expect(Object.isFrozen(model.selectedDayAgenda?.leagueEvents)).toBe(true)
    expect(Object.isFrozen(model.selectedDayAgenda?.otherEntries)).toBe(true)

    for (const month of model.months) {
      expect(Object.isFrozen(month)).toBe(true)
      expect(Object.isFrozen(month.weeks)).toBe(true)
      for (const week of month.weeks) {
        expect(Object.isFrozen(week)).toBe(true)
        expect(Object.isFrozen(week.days)).toBe(true)
        for (const cell of week.days) {
          expect(Object.isFrozen(cell)).toBe(true)
          expect(Object.isFrozen(cell.entries)).toBe(true)
          expect(Object.isFrozen(cell.visibleEntries)).toBe(true)
          expect(Object.isFrozen(cell.overflowEntries)).toBe(true)
        }
      }
    }
  })
})

describe('enriched calendar architecture', () => {
  const source = readFileSync(
    new URL('../../src/app/enrichedCalendarViewModel.ts', import.meta.url),
    'utf8',
  )

  it('does not import React, persistence, browser, or generation code', () => {
    const importSources = [...source.matchAll(/\bfrom\s+['"]([^'"]+)['"]/g)].map(
      (match) => match[1],
    )

    expect(importSources).not.toEqual(
      expect.arrayContaining([
        expect.stringMatching(
          /react|persist|indexeddb|storage|generation|createseasonfoundation|random/i,
        ),
      ]),
    )
  })

  it('contains no browser, random, JavaScript Date, or locale APIs', () => {
    expect(source).not.toContain('Math.random')
    expect(source).not.toMatch(
      /\b(?:window|document|indexedDB|localStorage|sessionStorage|navigator|fetch|location|history|performance|Temporal)\b/,
    )
    expect(source).not.toMatch(/\bDate\s*\(/)
    expect(source).not.toMatch(/\bDate\s*\.\s*(?:parse|UTC|now)\s*\(/)
    expect(source).not.toMatch(/\bIntl\b|\.toLocale\w*\s*\(/)
  })
})
