import { readFileSync } from 'node:fs'
import { describe, expect, expectTypeOf, it } from 'vitest'
import {
  createGameDetailsViewModel,
  createTeamScheduleViewModel,
  filterTeamScheduleRows,
  InvalidScheduleReadModelError,
} from '../../src/app/teamScheduleViewModel'
import type {
  GameDetailsViewModel,
  TeamScheduleRowViewModel,
  TeamScheduleSiteFilter,
  TeamScheduleViewModel,
} from '../../src/app/teamScheduleViewModel'
import {
  createCalendarEntries,
} from '../../src/app/calendarViewModel'
import type {
  CalendarEntryViewModel,
} from '../../src/app/calendarViewModel'
import {
  parseGameId,
  parseTeamId,
} from '../../src/domain/ids'
import type {
  GameId,
  TeamId,
} from '../../src/domain/ids'
import type {
  League,
} from '../../src/domain/league'
import {
  parseLocalDate,
} from '../../src/domain/localDate'
import type { LocalDate } from '../../src/domain/localDate'
import type {
  LeagueSchedule,
  ScheduledGame,
} from '../../src/domain/schedule'
import type { YearMonth } from '../../src/domain/yearMonth'
import {
  FIXTURE_MANAGED_TEAM_ID,
  createLeagueSeasonDomainFixture,
} from '../persistence/leagueSnapshot.fixture'

interface TeamScheduleTestContext {
  readonly league: League
  readonly schedule: LeagueSchedule
  readonly calendarEntries: readonly CalendarEntryViewModel[]
  readonly managedTeamId: TeamId | null
  readonly currentDate: LocalDate
}

const GWN_SEQUENCE_VECTOR = [
  1, 5, 9, 13, 17, 21, 25, 29, 33, 37, 41, 45, 49, 53, 57, 61, 65,
  69, 73, 77, 81, 85, 89, 93, 97, 101, 105, 109,
] as const

function createContext(
  managedTeamId: TeamId | null = FIXTURE_MANAGED_TEAM_ID,
): TeamScheduleTestContext {
  const fixture = createLeagueSeasonDomainFixture(managedTeamId)
  return createContextFromSchedule(
    fixture.league,
    fixture.foundation.schedule,
    fixture.foundation.calendar,
    fixture.managedTeamId,
    fixture.foundation.season.currentDate,
  )
}

function createContextFromSchedule(
  league: League,
  schedule: LeagueSchedule,
  seasonCalendar: ReturnType<
    typeof createLeagueSeasonDomainFixture
  >['foundation']['calendar'],
  managedTeamId: TeamId | null,
  currentDate: LocalDate,
): TeamScheduleTestContext {
  return {
    league,
    schedule,
    calendarEntries: createCalendarEntries({
      league,
      schedule,
      seasonCalendar,
      managedTeamId,
    }),
    managedTeamId,
    currentDate,
  }
}

function createTeamModel(
  context: TeamScheduleTestContext,
  inspectedTeamId: TeamId,
  currentDate = context.currentDate,
): TeamScheduleViewModel {
  return createTeamScheduleViewModel({
    ...context,
    inspectedTeamId,
    currentDate,
  })
}

function createDetails(
  context: TeamScheduleTestContext,
  gameId: GameId,
  perspectiveTeamId: TeamId | null,
  currentDate = context.currentDate,
): GameDetailsViewModel {
  return createGameDetailsViewModel({
    ...context,
    gameId,
    perspectiveTeamId,
    currentDate,
  })
}

function getInspectedTeamId(context: TeamScheduleTestContext): TeamId {
  return context.league.teams[1].id
}

function getOrderedScheduleGames(
  schedule: LeagueSchedule,
): readonly ScheduledGame[] {
  const gamesById = new Map(
    schedule.games.map((game) => [game.id, game] as const),
  )
  return schedule.gameDays.flatMap((gameDay) =>
    gameDay.gameIds.map((gameId) => {
      const game = gamesById.get(gameId)
      if (game === undefined) {
        throw new Error(`Missing fixture game ${gameId}`)
      }
      return game
    }),
  )
}

function getTeamGames(
  schedule: LeagueSchedule,
  teamId: TeamId,
): readonly ScheduledGame[] {
  return getOrderedScheduleGames(schedule).filter(
    (game) =>
      game.homeTeamId === teamId ||
      game.awayTeamId === teamId,
  )
}

function replaceScheduleGames(
  schedule: LeagueSchedule,
  patches: ReadonlyMap<GameId, Partial<ScheduledGame>>,
): LeagueSchedule {
  return Object.freeze({
    ...schedule,
    games: Object.freeze(
      schedule.games.map((game) => {
        const patch = patches.get(game.id)
        if (patch === undefined) return game
        const { actualDate: _actualDate, ...withoutActualDate } = game
        return Object.freeze({
          ...withoutActualDate,
          ...patch,
        })
      }),
    ),
  })
}

function createPatchedContext(
  patches: ReadonlyMap<GameId, Partial<ScheduledGame>>,
  managedTeamId: TeamId | null = FIXTURE_MANAGED_TEAM_ID,
): TeamScheduleTestContext {
  const fixture = createLeagueSeasonDomainFixture(managedTeamId)
  const schedule = replaceScheduleGames(
    fixture.foundation.schedule,
    patches,
  )
  return createContextFromSchedule(
    fixture.league,
    schedule,
    fixture.foundation.calendar,
    fixture.managedTeamId,
    fixture.foundation.season.currentDate,
  )
}

function expectStructuredError(operation: () => unknown): void {
  try {
    operation()
    throw new Error('Expected M2.6 read-model construction to fail')
  } catch (error) {
    expect(error).toBeInstanceOf(InvalidScheduleReadModelError)
    expect(
      typeof (error as InvalidScheduleReadModelError).code,
    ).toBe('string')
  }
}

describe('Team Schedule authoritative projection', () => {
  it('projects the inspected GWN schedule in authoritative sequence', () => {
    const context = createContext()
    const inspectedTeamId = getInspectedTeamId(context)
    const model = createTeamModel(context, inspectedTeamId)

    expect(model).toMatchObject({
      inspectedTeamId,
      inspectedTeamName: 'Glasswater Navigators',
      inspectedTeamAbbreviation: 'GWN',
      managedTeamId: FIXTURE_MANAGED_TEAM_ID,
      isManagedTeamSchedule: false,
      totalGameCount: 28,
      datedGameCount: 28,
      undatedGameCount: 0,
      homeGameCount: 14,
      awayGameCount: 14,
      nextScheduledGameId: parseGameId(
        'game_3d9f43c02f2463ed5dc85ef7',
      ),
    })
    expect(model.rows.map((row) => row.scheduleSequence)).toEqual(
      GWN_SEQUENCE_VECTOR,
    )
    expect(model.rows.map((row) => row.gameDaySequence)).toEqual(
      Array.from({ length: 28 }, (_, index) => index + 1),
    )
    expect(model.rows[0]).toMatchObject({
      gameId: 'game_3d9f43c02f2463ed5dc85ef7',
      gameDayId: 'game_day_4ed686507cd871fe51a13e38',
      scheduleSequence: 1,
      gameDaySequence: 1,
      meetingNumber: 1,
      stage: 'regular_season',
      status: 'scheduled',
      placementDate: '2026-10-05',
      originalScheduledDate: '2026-10-05',
      currentScheduledDate: '2026-10-05',
      actualDate: null,
      month: '2026-10',
      inspectedTeamId,
      opponentTeamId: 'team_fd3dce80_07',
      opponentName: 'Alderreach Astrolabes',
      opponentAbbreviation: 'ARA',
      homeTeamId: 'team_fd3dce80_07',
      awayTeamId: inspectedTeamId,
      site: 'away',
      isManagedTeamSchedule: false,
      involvesManagedTeam: false,
      isNextScheduledGame: true,
      isCurrentDate: true,
      isPastDate: false,
      isFutureDate: false,
      isUndated: false,
    })
    expect(model.rows.filter((row) => row.involvesManagedTeam)).toHaveLength(
      4,
    )
    expect(model.rows.every((row) => !row.isManagedTeamSchedule)).toBe(true)
    expect(model.undatedGroup).toEqual({
      rows: [],
      gameCount: 0,
      isEmpty: true,
    })
  })

  it('creates chronological placement-month groups without empty months', () => {
    const context = createContext()
    const model = createTeamModel(context, getInspectedTeamId(context))

    expect(model.monthGroups.map((group) => group.month)).toEqual([
      '2026-10',
      '2026-11',
      '2026-12',
    ])
    expect(
      model.monthGroups.map(
        ({
          gameCount,
          homeGameCount,
          awayGameCount,
          managedTeamGameCount,
          scheduledCount,
          completedCount,
          postponedCount,
          cancelledCount,
          containsNextScheduledGame,
        }) => ({
          gameCount,
          homeGameCount,
          awayGameCount,
          managedTeamGameCount,
          scheduledCount,
          completedCount,
          postponedCount,
          cancelledCount,
          containsNextScheduledGame,
        }),
      ),
    ).toEqual([
      {
        gameCount: 9,
        homeGameCount: 3,
        awayGameCount: 6,
        managedTeamGameCount: 2,
        scheduledCount: 9,
        completedCount: 0,
        postponedCount: 0,
        cancelledCount: 0,
        containsNextScheduledGame: true,
      },
      {
        gameCount: 10,
        homeGameCount: 9,
        awayGameCount: 1,
        managedTeamGameCount: 1,
        scheduledCount: 10,
        completedCount: 0,
        postponedCount: 0,
        cancelledCount: 0,
        containsNextScheduledGame: false,
      },
      {
        gameCount: 9,
        homeGameCount: 2,
        awayGameCount: 7,
        managedTeamGameCount: 1,
        scheduledCount: 9,
        completedCount: 0,
        postponedCount: 0,
        cancelledCount: 0,
        containsNextScheduledGame: false,
      },
    ])
    expect(
      model.monthGroups.flatMap((group) => group.rows),
    ).toEqual(model.rows)
  })

  it('preserves the 28/14/14 and 9/10/9 facts for all eight teams', () => {
    const context = createContext()
    const teamAppearancesByGameId = new Map<GameId, number>()

    expect(context.league.teams).toHaveLength(8)
    for (const team of context.league.teams) {
      const model = createTeamModel(context, team.id)

      expect(model.totalGameCount).toBe(28)
      expect(model.homeGameCount).toBe(14)
      expect(model.awayGameCount).toBe(14)
      expect(model.monthGroups.map((group) => group.gameCount)).toEqual([
        9, 10, 9,
      ])
      expect(model.rows.filter((row) => row.involvesManagedTeam)).toHaveLength(
        team.id === context.managedTeamId ? 28 : 4,
      )
      expect(model.isManagedTeamSchedule).toBe(
        team.id === context.managedTeamId,
      )
      expect(
        model.rows.every(
          (row) =>
            row.isManagedTeamSchedule === model.isManagedTeamSchedule,
        ),
      ).toBe(true)
      for (const row of model.rows) {
        teamAppearancesByGameId.set(
          row.gameId,
          (teamAppearancesByGameId.get(row.gameId) ?? 0) + 1,
        )
      }
    }

    expect(teamAppearancesByGameId.size).toBe(112)
    expect(
      [...teamAppearancesByGameId.values()].every(
        (appearanceCount) => appearanceCount === 2,
      ),
    ).toBe(true)
  })

  it('keeps inspected and managed context distinct, including null managed context', () => {
    const context = createContext(null)
    const model = createTeamModel(context, getInspectedTeamId(context))

    expect(model.managedTeamId).toBeNull()
    expect(model.isManagedTeamSchedule).toBe(false)
    expect(model.rows.every((row) => !row.involvesManagedTeam)).toBe(true)
    expect(model.monthGroups.every(
      (group) => group.managedTeamGameCount === 0,
    )).toBe(true)
  })

  it('uses GameDay topology rather than schedule.games array order', () => {
    const source = createContext()
    const reversedSchedule = Object.freeze({
      ...source.schedule,
      games: Object.freeze([...source.schedule.games].reverse()),
    })
    const fixture = createLeagueSeasonDomainFixture()
    const reversed = createContextFromSchedule(
      source.league,
      reversedSchedule,
      fixture.foundation.calendar,
      source.managedTeamId,
      source.currentDate,
    )
    const inspectedTeamId = getInspectedTeamId(source)

    expect(
      createTeamModel(reversed, inspectedTeamId).rows.map(
        (row) => row.scheduleSequence,
      ),
    ).toEqual(GWN_SEQUENCE_VECTOR)
  })
})

describe('Team Schedule temporal and lifecycle behavior', () => {
  it('derives temporal state and next game solely from supplied currentDate', () => {
    const context = createContext()
    const inspectedTeamId = getInspectedTeamId(context)
    const onNovemberSixteenth = createTeamModel(
      context,
      inspectedTeamId,
      parseLocalDate('2026-11-16'),
    )

    expect(
      onNovemberSixteenth.rows.filter((row) => row.isPastDate),
    ).toHaveLength(14)
    expect(
      onNovemberSixteenth.rows.filter((row) => row.isCurrentDate),
    ).toHaveLength(1)
    expect(
      onNovemberSixteenth.rows.filter((row) => row.isFutureDate),
    ).toHaveLength(13)
    expect(
      onNovemberSixteenth.rows.filter(
        (row) => row.isNextScheduledGame,
      ),
    ).toEqual([
      expect.objectContaining({
        gameId: 'game_aa33efad41a8f2c8990487e6',
        scheduleSequence: 57,
      }),
    ])

    const afterSchedule = createTeamModel(
      context,
      inspectedTeamId,
      parseLocalDate('2026-12-26'),
    )
    expect(afterSchedule.rows.every((row) => row.isPastDate)).toBe(true)
    expect(afterSchedule.nextScheduledGameId).toBeNull()
    expect(
      afterSchedule.rows.some((row) => row.isNextScheduledGame),
    ).toBe(false)
  })

  it('is unaffected by the host timezone setting', () => {
    const context = createContext()
    const inspectedTeamId = getInspectedTeamId(context)
    const currentDate = parseLocalDate('2026-11-16')
    const originalTimezone = process.env.TZ

    try {
      process.env.TZ = 'Pacific/Kiritimati'
      const farEast = createTeamModel(
        context,
        inspectedTeamId,
        currentDate,
      )
      process.env.TZ = 'America/Adak'
      const farWest = createTeamModel(
        context,
        inspectedTeamId,
        currentDate,
      )

      expect(farWest).toEqual(farEast)
    } finally {
      if (originalTimezone === undefined) {
        delete process.env.TZ
      } else {
        process.env.TZ = originalTimezone
      }
    }
  })

  it('uses authoritative schedule sequence to break equal-date next-game ties', () => {
    const base = createContext()
    const inspectedTeamId = getInspectedTeamId(base)
    const [first, second] = getTeamGames(
      base.schedule,
      inspectedTeamId,
    )
    const context = createPatchedContext(
      new Map([
        [
          second.id,
          {
            status: 'postponed',
            currentScheduledDate: first.originalScheduledDate,
          },
        ],
      ]),
    )
    const reversedEntries = Object.freeze(
      [...context.calendarEntries].reverse(),
    )
    const model = createTeamScheduleViewModel({
      ...context,
      calendarEntries: reversedEntries,
      inspectedTeamId,
    })

    expect(
      model.rows.filter(
        (row) => row.placementDate === '2026-10-05',
      ).map((row) => row.scheduleSequence),
    ).toEqual([1, 5])
    expect(model.nextScheduledGameId).toBe(first.id)
    expect(
      model.rows.filter((row) => row.isNextScheduledGame),
    ).toEqual([
      expect.objectContaining({ gameId: first.id, scheduleSequence: 1 }),
    ])
  })

  it('skips completed, cancelled, and undated games when choosing next', () => {
    const base = createContext()
    const inspectedTeamId = getInspectedTeamId(base)
    const [first, second, third, fourth] = getTeamGames(
      base.schedule,
      inspectedTeamId,
    )
    const context = createPatchedContext(
      new Map([
        [
          first.id,
          {
            status: 'completed',
            actualDate: first.originalScheduledDate,
          },
        ],
        [second.id, { status: 'cancelled' }],
        [
          third.id,
          {
            status: 'postponed',
            currentScheduledDate: null,
          },
        ],
      ]),
    )
    const model = createTeamModel(context, inspectedTeamId)
    const undatedRow = model.rows.find((row) => row.gameId === third.id)

    expect(model.nextScheduledGameId).toBe(fourth.id)
    expect(model.undatedGameCount).toBe(1)
    expect(model.datedGameCount).toBe(27)
    expect(model.undatedGroup.rows).toEqual([undatedRow])
    expect(undatedRow).toMatchObject({
      status: 'postponed',
      placementDate: null,
      originalScheduledDate: '2026-10-11',
      currentScheduledDate: null,
      actualDate: null,
      month: null,
      isNextScheduledGame: false,
      isCurrentDate: false,
      isPastDate: false,
      isFutureDate: false,
      isUndated: true,
    })
    expect(model.monthGroups[0]).toMatchObject({
      month: '2026-10',
      gameCount: 8,
      scheduledCount: 6,
      completedCount: 1,
      postponedCount: 0,
      cancelledCount: 1,
    })

    const undatedDetails = createDetails(
      context,
      third.id,
      inspectedTeamId,
    )
    expect(undatedDetails).toMatchObject({
      placementDate: null,
      isUndated: true,
      isCurrentDate: false,
      isPastDate: false,
      isFutureDate: false,
      previousPerspectiveGameId: second.id,
      nextPerspectiveGameId: fourth.id,
    })
  })

  it('groups by placement month while retaining original schedule history and sequence', () => {
    const base = createContext()
    const inspectedTeamId = getInspectedTeamId(base)
    const source = getTeamGames(base.schedule, inspectedTeamId)[8]
    const context = createPatchedContext(
      new Map([
        [
          source.id,
          {
            status: 'postponed',
            currentScheduledDate: parseLocalDate('2026-11-02'),
          },
        ],
      ]),
    )
    const model = createTeamModel(
      context,
      inspectedTeamId,
      parseLocalDate('2026-10-30'),
    )
    const moved = model.rows.find((row) => row.gameId === source.id)

    expect(model.monthGroups.map((group) => group.gameCount)).toEqual([
      8, 11, 9,
    ])
    expect(moved).toMatchObject({
      scheduleSequence: 33,
      status: 'postponed',
      placementDate: '2026-11-02',
      originalScheduledDate: '2026-10-29',
      currentScheduledDate: '2026-11-02',
      month: '2026-11',
    })
    expect(model.nextScheduledGameId).toBe(
      parseGameId('game_e9cc41f6365fa65c0cbd4b52'),
    )
    expect(
      model.monthGroups[1].rows.map((row) => row.scheduleSequence),
    ).toEqual([33, 37, 41, 45, 49, 53, 57, 61, 65, 69, 73])
  })
})

describe('Team Schedule row filtering', () => {
  it('returns frozen All/Home/Away projections without reordering or mutation', () => {
    const context = createContext()
    const model = createTeamModel(context, getInspectedTeamId(context))
    const before = JSON.stringify(model.rows)
    const all = filterTeamScheduleRows(model.rows, 'all')
    const home = filterTeamScheduleRows(model.rows, 'home')
    const away = filterTeamScheduleRows(model.rows, 'away')

    expect(all).toEqual(model.rows)
    expect(all).not.toBe(model.rows)
    expect(home).toHaveLength(14)
    expect(away).toHaveLength(14)
    expect(home.every((row) => row.site === 'home')).toBe(true)
    expect(away.every((row) => row.site === 'away')).toBe(true)
    expect(home).toEqual(model.rows.filter((row) => row.site === 'home'))
    expect(away).toEqual(model.rows.filter((row) => row.site === 'away'))
    expect(Object.isFrozen(all)).toBe(true)
    expect(Object.isFrozen(home)).toBe(true)
    expect(Object.isFrozen(away)).toBe(true)
    expect(JSON.stringify(model.rows)).toBe(before)
  })

  it('exports a closed site-filter type and rejects unsupported filters', () => {
    expectTypeOf<TeamScheduleSiteFilter>().toEqualTypeOf<
      'all' | 'home' | 'away'
    >()
    const model = createTeamModel(
      createContext(),
      parseTeamId('team_fd3dce80_02'),
    )

    expectStructuredError(() =>
      filterTeamScheduleRows(
        model.rows,
        'neutral' as TeamScheduleSiteFilter,
      ),
    )
  })
})

describe('shared game details', () => {
  it('preserves middle-game identity, context, dates, and team-sequence neighbors', () => {
    const context = createContext()
    const inspectedTeamId = getInspectedTeamId(context)
    const gameId = parseGameId('game_aa33efad41a8f2c8990487e6')
    const details = createDetails(
      context,
      gameId,
      inspectedTeamId,
      parseLocalDate('2026-11-16'),
    )

    expect(details).toEqual({
      gameId,
      gameDayId: 'game_day_263ab37efcfa4808b7735141',
      scheduleSequence: 57,
      gameDaySequence: 15,
      meetingNumber: 3,
      competitionStage: 'regular_season',
      status: 'scheduled',
      homeTeam: {
        teamId: inspectedTeamId,
        name: 'Glasswater Navigators',
        abbreviation: 'GWN',
      },
      awayTeam: {
        teamId: 'team_fd3dce80_05',
        name: 'Juniper Reach Wayfarers',
        abbreviation: 'JRW',
      },
      placementDate: '2026-11-16',
      originalScheduledDate: '2026-11-16',
      currentScheduledDate: '2026-11-16',
      actualDate: null,
      isUndated: false,
      perspectiveTeamId: inspectedTeamId,
      perspectiveSite: 'home',
      opponentTeamId: 'team_fd3dce80_05',
      isManagedTeamGame: false,
      isPerspectiveTeamManaged: false,
      isCurrentDate: true,
      isPastDate: false,
      isFutureDate: false,
      previousPerspectiveGameId:
        'game_5b23fdbb5a50328ecde30796',
      nextPerspectiveGameId:
        'game_ebbea7ea1222641739448293',
    })

    const row = createTeamModel(
      context,
      inspectedTeamId,
      parseLocalDate('2026-11-16'),
    ).rows.find((candidate) => candidate.gameId === gameId)
    if (row === undefined) {
      throw new Error(`Expected Team Schedule row for ${gameId}`)
    }
    expect(details).toMatchObject({
      gameId: row.gameId,
      gameDayId: row.gameDayId,
      scheduleSequence: row.scheduleSequence,
      gameDaySequence: row.gameDaySequence,
      meetingNumber: row.meetingNumber,
      competitionStage: row.stage,
      status: row.status,
      placementDate: row.placementDate,
      originalScheduledDate: row.originalScheduledDate,
      currentScheduledDate: row.currentScheduledDate,
      actualDate: row.actualDate,
      isUndated: row.isUndated,
      isCurrentDate: row.isCurrentDate,
      isPastDate: row.isPastDate,
      isFutureDate: row.isFutureDate,
    })
  })

  it('uses the same complete team sequence for first, middle, and last neighbors', () => {
    const context = createContext()
    const inspectedTeamId = getInspectedTeamId(context)
    const model = createTeamModel(context, inspectedTeamId)

    for (const index of [0, 14, 27]) {
      const row = model.rows[index]
      const details = createDetails(
        context,
        row.gameId,
        inspectedTeamId,
      )
      expect(details.previousPerspectiveGameId).toBe(
        model.rows[index - 1]?.gameId ?? null,
      )
      expect(details.nextPerspectiveGameId).toBe(
        model.rows[index + 1]?.gameId ?? null,
      )
    }
  })

  it('derives perspective and managed flags without changing authoritative game identity', () => {
    const context = createContext()
    const inspectedTeamId = getInspectedTeamId(context)
    const gameId = parseGameId('game_9be451e16f6a14d55550ca92')
    const inspected = createDetails(context, gameId, inspectedTeamId)
    const managed = createDetails(
      context,
      gameId,
      context.managedTeamId,
    )
    const neutral = createDetails(context, gameId, null)

    expect(inspected).toMatchObject({
      gameId,
      homeTeam: { teamId: context.managedTeamId },
      awayTeam: { teamId: inspectedTeamId },
      perspectiveTeamId: inspectedTeamId,
      perspectiveSite: 'away',
      opponentTeamId: context.managedTeamId,
      isManagedTeamGame: true,
      isPerspectiveTeamManaged: false,
    })
    expect(managed).toMatchObject({
      gameId,
      perspectiveTeamId: context.managedTeamId,
      perspectiveSite: 'home',
      opponentTeamId: inspectedTeamId,
      isManagedTeamGame: true,
      isPerspectiveTeamManaged: true,
    })
    expect(neutral).toMatchObject({
      gameId,
      perspectiveTeamId: null,
      perspectiveSite: null,
      opponentTeamId: null,
      isManagedTeamGame: true,
      isPerspectiveTeamManaged: false,
      previousPerspectiveGameId: null,
      nextPerspectiveGameId: null,
    })
    expect([
      inspected.gameDayId,
      managed.gameDayId,
      neutral.gameDayId,
    ]).toEqual([
      inspected.gameDayId,
      inspected.gameDayId,
      inspected.gameDayId,
    ])
  })

  it('contains no fabricated result, score, winner, venue, tipoff, or broadcast fields', () => {
    const context = createContext()
    const details = createDetails(
      context,
      parseGameId('game_aa33efad41a8f2c8990487e6'),
      getInspectedTeamId(context),
    )
    const serialized = JSON.stringify(details)

    expect(serialized).not.toMatch(
      /"score"|"winner"|"result"|"venue"|"tipoff"|"broadcast"/i,
    )
  })
})

describe('M2.6 validation', () => {
  it('rejects foreign inspected and managed teams and malformed current dates', () => {
    const context = createContext()

    expectStructuredError(() =>
      createTeamScheduleViewModel({
        ...context,
        inspectedTeamId: parseTeamId('team_m2_6_foreign'),
      }),
    )
    expectStructuredError(() =>
      createTeamScheduleViewModel({
        ...context,
        inspectedTeamId: getInspectedTeamId(context),
        managedTeamId: parseTeamId('team_m2_6_foreign'),
      }),
    )
    expectStructuredError(() =>
      createTeamScheduleViewModel({
        ...context,
        inspectedTeamId: getInspectedTeamId(context),
        currentDate: '2026-02-30' as LocalDate,
      }),
    )
  })

  it('rejects unknown games and a nonparticipating perspective', () => {
    const context = createContext()
    const inspectedTeamId = getInspectedTeamId(context)
    const gameId = parseGameId('game_aa33efad41a8f2c8990487e6')
    const nonparticipant = context.league.teams[2].id

    expectStructuredError(() =>
      createDetails(
        context,
        parseGameId('game_m2_6_unknown'),
        inspectedTeamId,
      ),
    )
    expectStructuredError(() =>
      createDetails(context, gameId, nonparticipant),
    )
  })

  it('rejects missing and duplicate normalized game entries', () => {
    const context = createContext()
    const inspectedTeamId = getInspectedTeamId(context)
    const firstGameEntry = context.calendarEntries.find(
      (entry) => entry.kind === 'game',
    )
    if (firstGameEntry === undefined) {
      throw new Error('M2.6 fixture must contain a game entry')
    }

    expectStructuredError(() =>
      createTeamScheduleViewModel({
        ...context,
        inspectedTeamId,
        calendarEntries: Object.freeze(
          context.calendarEntries.filter(
            (entry) => entry.entryId !== firstGameEntry.entryId,
          ),
        ),
      }),
    )
    expectStructuredError(() =>
      createTeamScheduleViewModel({
        ...context,
        inspectedTeamId,
        calendarEntries: Object.freeze([
          ...context.calendarEntries,
          firstGameEntry,
        ]),
      }),
    )
  })

  it('reports malformed schedule identities and lifecycle dates as structured errors', () => {
    const context = createContext()
    const inspectedTeamId = getInspectedTeamId(context)
    const sourceGame = context.schedule.games[0]
    const malformedPatches: readonly Partial<ScheduledGame>[] = [
      {
        seasonId: 'SEASON_NOT_CANONICAL' as ScheduledGame['seasonId'],
      },
      {
        gameDayId: 'GAME_DAY_NOT_CANONICAL' as ScheduledGame['gameDayId'],
      },
      {
        currentScheduledDate: null,
      },
    ]

    for (const patch of malformedPatches) {
      const malformedSchedule = replaceScheduleGames(
        context.schedule,
        new Map([[sourceGame.id, patch]]),
      )
      expectStructuredError(() =>
        createTeamScheduleViewModel({
          ...context,
          schedule: malformedSchedule,
          inspectedTeamId,
        }),
      )
    }
  })
})

describe('M2.6 determinism, restoration, and immutability', () => {
  it('is deterministic for reversed entry input and does not mutate sources', () => {
    const context = createContext()
    const inspectedTeamId = getInspectedTeamId(context)
    const before = JSON.stringify(context)
    const first = createTeamModel(context, inspectedTeamId)
    const second = createTeamModel(context, inspectedTeamId)
    const reversed = createTeamScheduleViewModel({
      ...context,
      inspectedTeamId,
      calendarEntries: Object.freeze(
        [...context.calendarEntries].reverse(),
      ),
    })

    expect(second).toEqual(first)
    expect(reversed).toEqual(first)
    expect(JSON.stringify(context)).toBe(before)
  })

  it('is deeply identical after JSON restoration and renormalization', () => {
    const fixture = createLeagueSeasonDomainFixture()
    const restored = JSON.parse(JSON.stringify(fixture)) as typeof fixture
    const baseline = createContext()
    const restoredContext = createContextFromSchedule(
      restored.league,
      restored.foundation.schedule,
      restored.foundation.calendar,
      restored.managedTeamId,
      restored.foundation.season.currentDate,
    )
    const inspectedTeamId = restored.league.teams[1].id
    const gameId = parseGameId('game_aa33efad41a8f2c8990487e6')

    expect(createTeamModel(restoredContext, inspectedTeamId)).toEqual(
      createTeamModel(baseline, inspectedTeamId),
    )
    expect(
      createDetails(restoredContext, gameId, inspectedTeamId),
    ).toEqual(createDetails(baseline, gameId, inspectedTeamId))
  })

  it('recursively freezes schedule, row, group, and detail projections', () => {
    const context = createContext()
    const inspectedTeamId = getInspectedTeamId(context)
    const model = createTeamModel(context, inspectedTeamId)
    const details = createDetails(
      context,
      model.rows[14].gameId,
      inspectedTeamId,
    )

    expect(Object.isFrozen(model)).toBe(true)
    expect(Object.isFrozen(model.rows)).toBe(true)
    expect(model.rows.every(Object.isFrozen)).toBe(true)
    expect(Object.isFrozen(model.monthGroups)).toBe(true)
    for (const group of model.monthGroups) {
      expect(Object.isFrozen(group)).toBe(true)
      expect(Object.isFrozen(group.rows)).toBe(true)
    }
    expect(Object.isFrozen(model.undatedGroup)).toBe(true)
    expect(Object.isFrozen(model.undatedGroup.rows)).toBe(true)
    expect(Object.isFrozen(details)).toBe(true)
    expect(Object.isFrozen(details.homeTeam)).toBe(true)
    expect(Object.isFrozen(details.awayTeam)).toBe(true)
  })
})

describe('M2.6 architecture', () => {
  const source = readFileSync(
    new URL('../../src/app/teamScheduleViewModel.ts', import.meta.url),
    'utf8',
  )

  it('imports no React, persistence, browser, or generation code', () => {
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

  it('uses no browser, random, JavaScript Date, or locale APIs', () => {
    expect(source).not.toContain('Math.random')
    expect(source).not.toMatch(
      /\b(?:window|document|indexedDB|localStorage|sessionStorage|navigator|fetch|location|history|performance|Temporal)\b/,
    )
    expect(source).not.toMatch(/\bDate\s*\(/)
    expect(source).not.toMatch(/\bDate\s*\.\s*(?:parse|UTC|now)\s*\(/)
    expect(source).not.toMatch(/\bIntl\b|\.toLocale\w*\s*\(/)
  })

  it('exports the documented narrow read-model types', () => {
    expectTypeOf<TeamScheduleRowViewModel['site']>().toEqualTypeOf<
      'home' | 'away'
    >()
    expectTypeOf<TeamScheduleRowViewModel['month']>().toEqualTypeOf<
      YearMonth | null
    >()
    expectTypeOf<GameDetailsViewModel['perspectiveSite']>().toEqualTypeOf<
      'home' | 'away' | null
    >()
  })
})
