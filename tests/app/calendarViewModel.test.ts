import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import {
  createCalendarEntries,
  createDayAgenda,
  getCalendarEntriesForDate,
  getCalendarEntriesForMonth,
  getCalendarEntriesForTeam,
  getDatedCalendarEntries,
  getManagedTeamCalendarEntries,
  getUndatedCalendarEntries,
  groupCalendarEntriesByDate,
} from '../../src/app/calendarViewModel'
import type {
  CalendarEntryViewModel,
  CreateCalendarEntriesInput,
} from '../../src/app/calendarViewModel'
import {
  parseLeagueId,
  parseSeasonCalendarId,
  parseSeasonId,
  parseTeamId,
} from '../../src/domain/ids'
import type { GameId, SeasonId, TeamId } from '../../src/domain/ids'
import { addDays, parseLocalDate } from '../../src/domain/localDate'
import type { LocalDate } from '../../src/domain/localDate'
import type {
  LeagueSchedule,
  ScheduledGame,
} from '../../src/domain/schedule'
import { parseSeasonCalendar } from '../../src/domain/seasonCalendar'
import type { SeasonCalendar } from '../../src/domain/seasonCalendar'
import { parseYearMonth } from '../../src/domain/yearMonth'
import {
  V2_FIXTURE_MANAGED_TEAM_ID,
  createLeagueSeasonDomainFixture,
} from '../persistence/leagueSnapshotV2.fixture'

function createInput(
  managedTeamId: TeamId | null = V2_FIXTURE_MANAGED_TEAM_ID,
): CreateCalendarEntriesInput {
  const fixture = createLeagueSeasonDomainFixture(managedTeamId)
  return {
    league: fixture.league,
    schedule: fixture.foundation.schedule,
    seasonCalendar: fixture.foundation.calendar,
    managedTeamId: fixture.managedTeamId,
  }
}

function findEntry(
  entries: readonly CalendarEntryViewModel[],
  sourceId: string,
): CalendarEntryViewModel {
  const entry = entries.find((candidate) => candidate.sourceId === sourceId)
  if (entry === undefined) {
    throw new Error(`Missing normalized entry for ${sourceId}`)
  }
  return entry
}

function replaceGame(
  game: ScheduledGame,
  patch: Partial<ScheduledGame>,
): ScheduledGame {
  const { actualDate: _actualDate, ...withoutActualDate } = game
  return Object.freeze({ ...withoutActualDate, ...patch })
}

function replaceScheduleGames(
  schedule: LeagueSchedule,
  patches: Readonly<Record<number, Partial<ScheduledGame>>>,
): LeagueSchedule {
  return Object.freeze({
    ...schedule,
    games: Object.freeze(
      schedule.games.map((game, index) =>
        replaceGame(game, patches[index] ?? {}),
      ),
    ),
  })
}

function createCalendar(
  seasonId: SeasonId,
  events: readonly Record<string, unknown>[],
): SeasonCalendar {
  return parseSeasonCalendar({
    id: parseSeasonCalendarId('season_calendar_calendar_view_model'),
    version: 1,
    seasonId,
    events,
  })
}

function scheduledEvent(
  id: string,
  seasonId: SeasonId,
  title: string,
  date: LocalDate,
  scope:
    | { readonly scope: 'league' }
    | { readonly scope: 'team'; readonly teamId: TeamId } = {
    scope: 'league',
  },
): Record<string, unknown> {
  return {
    id,
    version: 1,
    seasonId,
    kind: 'trade_deadline',
    ...scope,
    title,
    originalScheduledDate: date,
    scheduledDate: date,
    actualDate: null,
    dateStatus: 'scheduled',
    completionStatus: 'pending',
  }
}

describe('CalendarEntry normalization', () => {
  it('creates one collision-safe entry for every game and calendar event', () => {
    const input = createInput()
    const entries = createCalendarEntries(input)
    const gameEntries = entries.filter((entry) => entry.kind === 'game')
    const eventEntries = entries.filter((entry) => entry.kind !== 'game')

    expect(gameEntries).toHaveLength(112)
    expect(eventEntries).toHaveLength(input.seasonCalendar.events.length)
    expect(entries).toHaveLength(
      input.schedule.games.length + input.seasonCalendar.events.length,
    )
    expect(new Set(entries.map((entry) => entry.entryId)).size).toBe(
      entries.length,
    )
    expect(new Set(gameEntries.map((entry) => entry.sourceId))).toEqual(
      new Set(input.schedule.games.map((game) => game.id)),
    )
    expect(new Set(eventEntries.map((entry) => entry.sourceId))).toEqual(
      new Set(input.seasonCalendar.events.map((event) => event.id)),
    )
  })

  it('namespaces identical serialized game and event source IDs', () => {
    const input = createInput()
    const game = input.schedule.games[0]
    const calendar = createCalendar(input.schedule.seasonId, [
      scheduledEvent(
        game.id,
        input.schedule.seasonId,
        'Identity collision test',
        game.originalScheduledDate,
      ),
    ])
    const entries = createCalendarEntries({
      ...input,
      seasonCalendar: calendar,
    })
    const matching = entries.filter((entry) => entry.sourceId === game.id)

    expect(matching.map((entry) => entry.entryId).sort()).toEqual([
      `calendar-event:${game.id}`,
      `game:${game.id}`,
    ])
  })

  it('preserves authoritative game identity, teams, stage, and GameDay metadata', () => {
    const input = createInput()
    const source = input.schedule.games[0]
    const entry = findEntry(createCalendarEntries(input), source.id)
    const homeTeam = input.league.teams.find(
      (team) => team.id === source.homeTeamId,
    )
    const awayTeam = input.league.teams.find(
      (team) => team.id === source.awayTeamId,
    )

    expect(homeTeam).toBeDefined()
    expect(awayTeam).toBeDefined()
    expect(entry).toMatchObject({
      entryId: `game:${source.id}`,
      sourceId: source.id,
      kind: 'game',
      competitionStage: source.stage,
      homeTeamId: source.homeTeamId,
      awayTeamId: source.awayTeamId,
      gameDayId: source.gameDayId,
      calendarEventKind: null,
      teamIds: [source.homeTeamId, source.awayTeamId],
    })
    expect(entry.title).toBe(
      `${awayTeam?.city} ${awayTeam?.nickname} at ${homeTeam?.city} ${homeTeam?.nickname}`,
    )
    expect(entry.shortLabel).toBe(
      `${awayTeam?.abbreviation} @ ${homeTeam?.abbreviation}`,
    )
  })

  it('maps event kind and team scope only from authoritative event fields', () => {
    const input = createInput()
    const managedTeamId = input.managedTeamId as TeamId
    const longTitle =
      'Managed team deadline review with an intentionally complete title'
    const calendar = createCalendar(input.schedule.seasonId, [
      scheduledEvent(
        'calendar_event_managed_review',
        input.schedule.seasonId,
        longTitle,
        input.schedule.games[0].originalScheduledDate,
        { scope: 'team', teamId: managedTeamId },
      ),
      scheduledEvent(
        'calendar_event_league_review',
        input.schedule.seasonId,
        'League-wide team-name text is still league scoped',
        input.schedule.games[0].originalScheduledDate,
      ),
    ])
    const entries = createCalendarEntries({
      ...input,
      seasonCalendar: calendar,
    })
    const teamEvent = findEntry(entries, 'calendar_event_managed_review')
    const leagueEvent = findEntry(entries, 'calendar_event_league_review')

    expect(teamEvent).toMatchObject({
      kind: 'team_event',
      calendarEventKind: 'trade_deadline',
      teamIds: [managedTeamId],
      homeTeamId: null,
      awayTeamId: null,
      isManagedTeamEntry: true,
      title: longTitle,
      shortLabel: longTitle,
    })
    expect(leagueEvent).toMatchObject({
      kind: 'league_event',
      teamIds: [],
      isManagedTeamEntry: false,
    })
  })

  it('freezes entries, nested team collections, and the complete result', () => {
    const entries = createCalendarEntries(createInput())

    expect(Object.isFrozen(entries)).toBe(true)
    for (const entry of entries) {
      expect(Object.isFrozen(entry)).toBe(true)
      expect(Object.isFrozen(entry.teamIds)).toBe(true)
    }
  })
})

describe('CalendarEntry date and status semantics', () => {
  it('maps every ScheduledGame lifecycle without losing date history', () => {
    const input = createInput()
    const sourceGames = input.schedule.games.slice(0, 6)
    const completedCurrent = addDays(sourceGames[1].originalScheduledDate, 1)
    const completedActual = addDays(sourceGames[1].originalScheduledDate, 2)
    const postponedReplacement = addDays(
      sourceGames[2].originalScheduledDate,
      4,
    )
    const cancelledReplacement = addDays(
      sourceGames[4].originalScheduledDate,
      5,
    )
    const schedule = replaceScheduleGames(input.schedule, {
      1: {
        status: 'completed',
        currentScheduledDate: completedCurrent,
        actualDate: completedActual,
      },
      2: {
        status: 'postponed',
        currentScheduledDate: postponedReplacement,
      },
      3: { status: 'postponed', currentScheduledDate: null },
      4: {
        status: 'cancelled',
        currentScheduledDate: cancelledReplacement,
      },
      5: { status: 'cancelled', currentScheduledDate: null },
    })
    const entries = createCalendarEntries({ ...input, schedule })

    expect(findEntry(entries, sourceGames[0].id)).toMatchObject({
      status: 'scheduled',
      date: sourceGames[0].currentScheduledDate,
      originalDate: sourceGames[0].originalScheduledDate,
      currentScheduledDate: sourceGames[0].currentScheduledDate,
      actualDate: null,
    })
    expect(findEntry(entries, sourceGames[1].id)).toMatchObject({
      status: 'completed',
      date: completedActual,
      originalDate: sourceGames[1].originalScheduledDate,
      currentScheduledDate: completedCurrent,
      actualDate: completedActual,
    })
    expect(findEntry(entries, sourceGames[2].id)).toMatchObject({
      status: 'postponed',
      date: postponedReplacement,
      originalDate: sourceGames[2].originalScheduledDate,
      currentScheduledDate: postponedReplacement,
      actualDate: null,
    })
    expect(findEntry(entries, sourceGames[3].id)).toMatchObject({
      status: 'postponed',
      date: null,
      originalDate: sourceGames[3].originalScheduledDate,
      currentScheduledDate: null,
      actualDate: null,
    })
    expect(findEntry(entries, sourceGames[4].id)).toMatchObject({
      status: 'cancelled',
      date: cancelledReplacement,
      currentScheduledDate: cancelledReplacement,
    })
    expect(findEntry(entries, sourceGames[5].id)).toMatchObject({
      status: 'cancelled',
      date: sourceGames[5].originalScheduledDate,
      currentScheduledDate: null,
    })
  })

  it('maps every CalendarEvent date status exhaustively without fabrication', () => {
    const input = createInput()
    const seasonId = input.schedule.seasonId
    const calendar = createCalendar(seasonId, [
      {
        id: 'calendar_event_tba',
        version: 1,
        seasonId,
        kind: 'draft_event',
        scope: 'league',
        title: 'Draft date pending',
        originalScheduledDate: null,
        scheduledDate: null,
        actualDate: null,
        dateStatus: 'tba',
        completionStatus: 'pending',
      },
      {
        ...scheduledEvent(
          'calendar_event_estimated',
          seasonId,
          'Estimated event',
          parseLocalDate('2026-11-01'),
        ),
        dateStatus: 'estimated',
      },
      {
        ...scheduledEvent(
          'calendar_event_announced',
          seasonId,
          'Announced event',
          parseLocalDate('2026-11-02'),
        ),
        dateStatus: 'announced',
      },
      scheduledEvent(
        'calendar_event_scheduled',
        seasonId,
        'Scheduled event',
        parseLocalDate('2026-11-03'),
      ),
      {
        ...scheduledEvent(
          'calendar_event_completed',
          seasonId,
          'Completed event',
          parseLocalDate('2026-11-04'),
        ),
        scheduledDate: '2026-11-05',
        actualDate: '2026-11-06',
        dateStatus: 'completed',
        completionStatus: 'completed',
      },
      {
        ...scheduledEvent(
          'calendar_event_postponed_replacement',
          seasonId,
          'Postponed with replacement',
          parseLocalDate('2026-11-07'),
        ),
        scheduledDate: '2026-11-09',
        dateStatus: 'postponed',
      },
      {
        ...scheduledEvent(
          'calendar_event_postponed_tba',
          seasonId,
          'Postponed without replacement',
          parseLocalDate('2026-11-08'),
        ),
        scheduledDate: null,
        dateStatus: 'postponed',
      },
      {
        ...scheduledEvent(
          'calendar_event_cancelled_current',
          seasonId,
          'Cancelled on retained date',
          parseLocalDate('2026-11-10'),
        ),
        scheduledDate: '2026-11-11',
        dateStatus: 'cancelled',
        completionStatus: 'cancelled',
      },
      {
        ...scheduledEvent(
          'calendar_event_cancelled_original',
          seasonId,
          'Cancelled with original only',
          parseLocalDate('2026-11-12'),
        ),
        scheduledDate: null,
        dateStatus: 'cancelled',
        completionStatus: 'cancelled',
      },
      {
        id: 'calendar_event_cancelled_undated',
        version: 1,
        seasonId,
        kind: 'free_agency_event',
        scope: 'league',
        title: 'Cancelled before a date was announced',
        originalScheduledDate: null,
        scheduledDate: null,
        actualDate: null,
        dateStatus: 'cancelled',
        completionStatus: 'cancelled',
      },
    ])
    const entries = createCalendarEntries({
      ...input,
      seasonCalendar: calendar,
    })

    expect(findEntry(entries, 'calendar_event_tba')).toMatchObject({
      status: 'tba',
      date: null,
      originalDate: null,
      currentScheduledDate: null,
      actualDate: null,
    })
    expect(findEntry(entries, 'calendar_event_estimated')).toMatchObject({
      status: 'estimated',
      date: '2026-11-01',
    })
    expect(findEntry(entries, 'calendar_event_announced')).toMatchObject({
      status: 'announced',
      date: '2026-11-02',
    })
    expect(findEntry(entries, 'calendar_event_scheduled')).toMatchObject({
      status: 'scheduled',
      date: '2026-11-03',
    })
    expect(findEntry(entries, 'calendar_event_completed')).toMatchObject({
      status: 'completed',
      date: '2026-11-06',
      originalDate: '2026-11-04',
      currentScheduledDate: '2026-11-05',
      actualDate: '2026-11-06',
    })
    expect(
      findEntry(entries, 'calendar_event_postponed_replacement'),
    ).toMatchObject({
      status: 'postponed',
      date: '2026-11-09',
      originalDate: '2026-11-07',
      currentScheduledDate: '2026-11-09',
    })
    expect(findEntry(entries, 'calendar_event_postponed_tba')).toMatchObject({
      status: 'postponed',
      date: null,
      originalDate: '2026-11-08',
      currentScheduledDate: null,
    })
    expect(findEntry(entries, 'calendar_event_cancelled_current')).toMatchObject({
      status: 'cancelled',
      date: '2026-11-11',
    })
    expect(
      findEntry(entries, 'calendar_event_cancelled_original'),
    ).toMatchObject({
      status: 'cancelled',
      date: '2026-11-12',
      currentScheduledDate: null,
    })
    expect(findEntry(entries, 'calendar_event_cancelled_undated')).toMatchObject({
      status: 'cancelled',
      date: null,
      originalDate: null,
      currentScheduledDate: null,
      actualDate: null,
    })
  })

  it('rejects unsupported statuses instead of inferring from dates', () => {
    const input = createInput()
    const invalidSchedule = replaceScheduleGames(input.schedule, {
      0: { status: 'in_progress' as ScheduledGame['status'] },
    })

    expect(() =>
      createCalendarEntries({ ...input, schedule: invalidSchedule }),
    ).toThrow(/unsupported/)

    const invalidCalendar = {
      ...input.seasonCalendar,
      events: [
        {
          ...input.seasonCalendar.events[0],
          dateStatus: 'in_progress',
        },
      ],
    } as unknown as SeasonCalendar
    expect(() =>
      createCalendarEntries({ ...input, seasonCalendar: invalidCalendar }),
    ).toThrow()
  })
})

describe('managed-team context and deterministic labels', () => {
  it('marks exactly the authoritative managed-team associations', () => {
    const input = createInput()
    const managedTeamId = input.managedTeamId as TeamId
    const otherTeamId = input.league.teams.find(
      (team) => team.id !== managedTeamId,
    )?.id as TeamId
    const date = input.schedule.games[0].originalScheduledDate
    const calendar = createCalendar(input.schedule.seasonId, [
      scheduledEvent(
        'calendar_event_managed_team',
        input.schedule.seasonId,
        'Managed team event',
        date,
        { scope: 'team', teamId: managedTeamId },
      ),
      scheduledEvent(
        'calendar_event_other_team',
        input.schedule.seasonId,
        'Other team event',
        date,
        { scope: 'team', teamId: otherTeamId },
      ),
      scheduledEvent(
        'calendar_event_league',
        input.schedule.seasonId,
        'League event',
        date,
      ),
    ])
    const entries = createCalendarEntries({
      ...input,
      seasonCalendar: calendar,
    })

    expect(findEntry(entries, 'calendar_event_managed_team').isManagedTeamEntry)
      .toBe(true)
    expect(findEntry(entries, 'calendar_event_other_team').isManagedTeamEntry)
      .toBe(false)
    expect(findEntry(entries, 'calendar_event_league').isManagedTeamEntry)
      .toBe(false)

    for (const entry of entries.filter((candidate) => candidate.kind === 'game')) {
      expect(entry.isManagedTeamEntry).toBe(
        entry.teamIds.includes(managedTeamId),
      )
    }
  })

  it('produces no managed entries when managedTeamId is null', () => {
    const entries = createCalendarEntries(createInput(null))

    expect(entries.every((entry) => !entry.isManagedTeamEntry)).toBe(true)
    expect(getManagedTeamCalendarEntries(entries)).toEqual([])
  })

  it('does not change managed markers while filtering an inspected team', () => {
    const input = createInput()
    const entries = createCalendarEntries(input)
    const inspectedTeamId = input.league.teams[1].id
    const markersBefore = new Map(
      entries.map((entry) => [entry.entryId, entry.isManagedTeamEntry]),
    )
    const inspectedEntries = getCalendarEntriesForTeam(
      entries,
      inspectedTeamId,
    )

    for (const entry of inspectedEntries) {
      expect(entry.isManagedTeamEntry).toBe(markersBefore.get(entry.entryId))
    }
  })
})

describe('CalendarEntry selectors and sort contract', () => {
  it('partitions dated and undated entries without loss or source mutation', () => {
    const input = createInput()
    const tbaCalendar = createCalendar(input.schedule.seasonId, [
      {
        id: 'calendar_event_tba_partition',
        version: 1,
        seasonId: input.schedule.seasonId,
        kind: 'draft_event',
        scope: 'league',
        title: 'Undated draft',
        originalScheduledDate: null,
        scheduledDate: null,
        actualDate: null,
        dateStatus: 'tba',
        completionStatus: 'pending',
      },
    ])
    const entries = createCalendarEntries({
      ...input,
      seasonCalendar: tbaCalendar,
    })
    const before = JSON.stringify(entries)
    const dated = getDatedCalendarEntries(entries)
    const undated = getUndatedCalendarEntries(entries)
    const grouped = groupCalendarEntriesByDate(entries)

    expect(dated.every((entry) => entry.date !== null)).toBe(true)
    expect(undated.every((entry) => entry.date === null)).toBe(true)
    expect([...dated, ...undated]).toHaveLength(entries.length)
    expect(
      new Set([...dated, ...undated].map((entry) => entry.entryId)).size,
    ).toBe(entries.length)
    expect(Object.isFrozen(dated)).toBe(true)
    expect(Object.isFrozen(undated)).toBe(true)
    expect(
      grouped.flatMap((group) => group.entries).some(
        (entry) => entry.entryId === 'calendar-event:calendar_event_tba_partition',
      ),
    ).toBe(false)
    expect(JSON.stringify(entries)).toBe(before)
  })

  it('groups every dated entry once in chronological date order', () => {
    const entries = createCalendarEntries(createInput())
    const groups = groupCalendarEntriesByDate(entries)
    const groupedEntries = groups.flatMap((group) => group.entries)

    expect(groupedEntries).toEqual(getDatedCalendarEntries(entries))
    expect(groups.map((group) => group.date)).toEqual(
      [...groups.map((group) => group.date)].sort(),
    )
    expect(new Set(groupedEntries.map((entry) => entry.entryId)).size).toBe(
      groupedEntries.length,
    )
    expect(Object.isFrozen(groups)).toBe(true)
    for (const group of groups) {
      expect(Object.isFrozen(group)).toBe(true)
      expect(Object.isFrozen(group.entries)).toBe(true)
    }
  })

  it('uses the documented complete same-date priority and source-ID tie break', () => {
    const input = createInput()
    const managedTeamId = input.managedTeamId as TeamId
    const otherTeamId = input.league.teams[1].id
    const date = input.schedule.games[0].currentScheduledDate as LocalDate
    const calendar = createCalendar(input.schedule.seasonId, [
      scheduledEvent(
        'calendar_event_league_priority',
        input.schedule.seasonId,
        'League priority',
        date,
      ),
      scheduledEvent(
        'calendar_event_managed_priority',
        input.schedule.seasonId,
        'Managed event priority',
        date,
        { scope: 'team', teamId: managedTeamId },
      ),
      scheduledEvent(
        'calendar_event_other_priority',
        input.schedule.seasonId,
        'Other team priority',
        date,
        { scope: 'team', teamId: otherTeamId },
      ),
    ])
    const entries = createCalendarEntries({
      ...input,
      seasonCalendar: calendar,
    })
    const agenda = createDayAgenda(entries, date)
    const managedGames = agenda.filter(
      (entry) => entry.kind === 'game' && entry.isManagedTeamEntry,
    )
    const otherGames = agenda.filter(
      (entry) => entry.kind === 'game' && !entry.isManagedTeamEntry,
    )

    expect(agenda).toEqual([
      findEntry(entries, 'calendar_event_league_priority'),
      ...managedGames,
      ...otherGames,
      findEntry(entries, 'calendar_event_managed_priority'),
      findEntry(entries, 'calendar_event_other_priority'),
    ])
    expect(otherGames.map((entry) => entry.entryId)).toEqual(
      [...otherGames.map((entry) => entry.entryId)].sort(),
    )
  })

  it('filters dates and months by placement date rather than date history', () => {
    const input = createInput()
    const sourceGame = input.schedule.games[0]
    const actualDate = parseLocalDate('2026-11-02')
    const schedule = replaceScheduleGames(input.schedule, {
      0: {
        status: 'completed',
        currentScheduledDate: addDays(sourceGame.originalScheduledDate, 1),
        actualDate,
      },
    })
    const entries = createCalendarEntries({ ...input, schedule })
    const completedEntry = findEntry(entries, sourceGame.id)

    expect(
      getCalendarEntriesForDate(entries, actualDate).map(
        (entry) => entry.entryId,
      ),
    ).toContain(completedEntry.entryId)
    expect(
      getCalendarEntriesForMonth(entries, parseYearMonth('2026-11')).map(
        (entry) => entry.entryId,
      ),
    ).toContain(completedEntry.entryId)
    expect(
      getCalendarEntriesForMonth(entries, parseYearMonth('2026-10'))
        .map((entry) => entry.entryId)
        .includes(completedEntry.entryId),
    ).toBe(false)
  })

  it('filters team context without including unassociated league events', () => {
    const input = createInput()
    const teamId = input.league.teams[0].id
    const entries = createCalendarEntries(input)
    const teamEntries = getCalendarEntriesForTeam(entries, teamId)

    expect(teamEntries.every((entry) => entry.teamIds.includes(teamId))).toBe(
      true,
    )
    expect(teamEntries.some((entry) => entry.kind === 'league_event')).toBe(
      false,
    )
    expect(getManagedTeamCalendarEntries(entries)).toEqual(
      entries.filter((entry) => entry.isManagedTeamEntry),
    )
  })

  it('returns deterministic frozen ordering for arbitrarily reordered input', () => {
    const entries = createCalendarEntries(createInput())
    const reversed = Object.freeze([...entries].reverse())
    const originalReversed = [...reversed]

    expect(getDatedCalendarEntries(reversed)).toEqual(
      getDatedCalendarEntries(entries),
    )
    expect(reversed).toEqual(originalReversed)
  })

  it('rejects malformed selector value objects through existing parsers', () => {
    const entries = createCalendarEntries(createInput())

    expect(() =>
      getCalendarEntriesForDate(
        entries,
        '2026-02-30' as LocalDate,
      ),
    ).toThrow()
    expect(() =>
      getCalendarEntriesForMonth(
        entries,
        '2026-13' as ReturnType<typeof parseYearMonth>,
      ),
    ).toThrow()
    expect(() =>
      getCalendarEntriesForTeam(
        entries,
        'TEAM BAD' as TeamId,
      ),
    ).toThrow()
  })
})

describe('CalendarEntry cross-reference validation', () => {
  it('rejects foreign managed teams, schedule teams, and event teams', () => {
    const input = createInput()
    expect(() =>
      createCalendarEntries({
        ...input,
        managedTeamId: parseTeamId('team_foreign'),
      }),
    ).toThrow(/Managed team/)

    const foreignSchedule = replaceScheduleGames(input.schedule, {
      0: { homeTeamId: parseTeamId('team_foreign') },
    })
    expect(() =>
      createCalendarEntries({ ...input, schedule: foreignSchedule }),
    ).toThrow(/foreign league team/)

    const foreignEventCalendar = createCalendar(input.schedule.seasonId, [
      scheduledEvent(
        'calendar_event_foreign_team',
        input.schedule.seasonId,
        'Foreign team event',
        input.schedule.games[0].originalScheduledDate,
        { scope: 'team', teamId: parseTeamId('team_foreign') },
      ),
    ])
    expect(() =>
      createCalendarEntries({
        ...input,
        seasonCalendar: foreignEventCalendar,
      }),
    ).toThrow(/foreign team/)
  })

  it('rejects mismatched league and season references', () => {
    const input = createInput()
    expect(() =>
      createCalendarEntries({
        ...input,
        schedule: {
          ...input.schedule,
          leagueId: parseLeagueId('league_foreign'),
        },
      }),
    ).toThrow(/does not match/)

    const wrongSeason = parseSeasonId('season_foreign')
    const wrongCalendar = createCalendar(wrongSeason, [])
    expect(() =>
      createCalendarEntries({
        ...input,
        seasonCalendar: wrongCalendar,
      }),
    ).toThrow(/different seasons/)
  })

  it('rejects duplicate, self-matching, and wrong-season games', () => {
    const input = createInput()
    const duplicateSchedule = replaceScheduleGames(input.schedule, {
      1: { id: input.schedule.games[0].id },
    })
    expect(() =>
      createCalendarEntries({ ...input, schedule: duplicateSchedule }),
    ).toThrow()

    const selfMatchSchedule = replaceScheduleGames(input.schedule, {
      0: { awayTeamId: input.schedule.games[0].homeTeamId },
    })
    expect(() =>
      createCalendarEntries({ ...input, schedule: selfMatchSchedule }),
    ).toThrow(/assign one team twice/)

    const wrongSeasonSchedule = replaceScheduleGames(input.schedule, {
      0: { seasonId: parseSeasonId('season_foreign') },
    })
    expect(() =>
      createCalendarEntries({ ...input, schedule: wrongSeasonSchedule }),
    ).toThrow(/different season/)
  })
})

describe('full current CalendarEntry fixture', () => {
  it('preserves current 112-game and managed-team 28/14/14 facts', () => {
    const input = createInput()
    const entries = createCalendarEntries(input)
    const games = entries.filter((entry) => entry.kind === 'game')
    const managedGames = games.filter((entry) => entry.isManagedTeamEntry)

    expect(games).toHaveLength(112)
    expect(managedGames).toHaveLength(28)
    expect(
      managedGames.filter(
        (entry) => entry.homeTeamId === input.managedTeamId,
      ),
    ).toHaveLength(14)
    expect(
      managedGames.filter(
        (entry) => entry.awayTeamId === input.managedTeamId,
      ),
    ).toHaveLength(14)
  })

  it('is deterministic, survives JSON restoration, and never mutates sources', () => {
    const input = createInput()
    const before = JSON.stringify(input)
    const first = createCalendarEntries(input)
    const second = createCalendarEntries(input)
    const restored = JSON.parse(
      JSON.stringify(input),
    ) as CreateCalendarEntriesInput
    const afterRestoration = createCalendarEntries(restored)

    expect(first).toEqual(second)
    expect(afterRestoration).toEqual(first)
    expect(JSON.stringify(input)).toBe(before)
    expect(input.schedule.games.map((game) => game.id)).toEqual(
      JSON.parse(before).schedule.games.map(
        (game: { readonly id: GameId }) => game.id,
      ),
    )
  })
})

describe('CalendarEntry architecture', () => {
  const source = readFileSync(
    new URL('../../src/app/calendarViewModel.ts', import.meta.url),
    'utf8',
  )

  it('imports only pure domain modules and no persistence or generation code', () => {
    const importSources = [...source.matchAll(/\bfrom\s+['"]([^'"]+)['"]/g)].map(
      (match) => match[1],
    )

    expect(new Set(importSources)).toEqual(
      new Set([
        '../domain/ids',
        '../domain/league',
        '../domain/leagueValidation',
        '../domain/localDate',
        '../domain/schedule',
        '../domain/seasonCalendar',
        '../domain/yearMonth',
      ]),
    )
    expect(importSources).not.toEqual(
      expect.arrayContaining([
        expect.stringMatching(
          /react|persist|indexeddb|generation|createseasonfoundation|random/i,
        ),
      ]),
    )
  })

  it('contains no browser, random, JavaScript Date, or locale APIs', () => {
    expect(source).not.toContain('Math.random')
    expect(source).not.toMatch(
      /\b(?:window|document|indexedDB|localStorage|sessionStorage|navigator|fetch|location|history|performance|Temporal|process)\b/,
    )
    expect(source).not.toMatch(/\bDate\s*\(/)
    expect(source).not.toMatch(/\bDate\s*\.\s*(?:parse|UTC|now)\s*\(/)
    expect(source).not.toMatch(/\bIntl\b|\.toLocale\w*\s*\(/)
  })
})
