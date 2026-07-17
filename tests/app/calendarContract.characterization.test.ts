import { describe, expect, it } from 'vitest'
import {
  getTeamScheduleGames,
  groupGamesByGameDay,
  resolveOpponent,
} from '../../src/app/scheduleViewModel'
import { DEFAULT_PAGE_ID } from '../../src/app/navigation'
import type { NavigationPageId } from '../../src/app/navigation'
import {
  parseLeagueSnapshotV2,
} from '../../src/persistence/leagueSnapshotV2'
import type {
  LeagueSnapshotV2,
  LeagueSnapshotV2ScheduledGameDto,
} from '../../src/persistence/leagueSnapshotV2'
import { createLeagueSnapshotV2Fixture } from '../persistence/leagueSnapshotV2.fixture'

describe('M2.1 calendar contract characterization', () => {
  it('preserves complete team-game identities and allows inspection independently of the managed team', () => {
    const snapshot = createLeagueSnapshotV2Fixture()
    const before = structuredClone(snapshot)
    const inspectedTeamId = snapshot.league.teams[1].id

    expect(inspectedTeamId).not.toBe(snapshot.managedTeamId)

    const expectedGames = snapshot.leagueSchedule.games.filter(
      (game) =>
        game.homeTeamId === inspectedTeamId ||
        game.awayTeamId === inspectedTeamId,
    )
    const inspectedGames = getTeamScheduleGames(
      snapshot.leagueSchedule,
      inspectedTeamId,
    )

    expect(inspectedGames.map(projectGameReference)).toEqual(
      expectedGames.map(projectGameReference),
    )

    for (const game of inspectedGames) {
      const expectedOpponentId =
        game.homeTeamId === inspectedTeamId
          ? game.awayTeamId
          : game.homeTeamId
      expect(resolveOpponent(snapshot.league, game, inspectedTeamId).id).toBe(
        expectedOpponentId,
      )
    }

    expect(snapshot.managedTeamId).toBe(before.managedTeamId)
    expect(snapshot).toEqual(before)
  })

  it('projects every stored game into one GameDay slate without changing identity or date history', () => {
    const snapshot = createLeagueSnapshotV2Fixture()
    const before = structuredClone(snapshot)
    const groups = groupGamesByGameDay(snapshot.leagueSchedule)
    const groupedGames = groups.flatMap((group) => group.games)
    const declaredGameIds = snapshot.leagueSchedule.gameDays.flatMap(
      (gameDay) => gameDay.gameIds,
    )
    const storedGamesById = new Map(
      snapshot.leagueSchedule.games.map((game) => [game.id, game] as const),
    )

    expect(groups.map(({ gameDay }) => gameDay.id)).toEqual(
      snapshot.leagueSchedule.gameDays.map(({ id }) => id),
    )
    expect(groupedGames.map(({ id }) => id)).toEqual(declaredGameIds)
    expect(new Set(groupedGames.map(({ id }) => id)).size).toBe(
      groupedGames.length,
    )
    expect([...groupedGames.map(({ id }) => id)].sort()).toEqual(
      [...snapshot.leagueSchedule.games.map(({ id }) => id)].sort(),
    )

    for (const game of groupedGames) {
      const storedGame = storedGamesById.get(game.id)
      expect(storedGame).toBeDefined()
      expect(game).toBe(storedGame)
      expect(projectGameLifecycle(game)).toEqual(
        projectGameLifecycle(storedGame as LeagueSnapshotV2ScheduledGameDto),
      )
    }

    const calendarEvents = snapshot.seasonCalendar.events.map((event) => event)
    expect(new Set(calendarEvents.map(({ id }) => id)).size).toBe(
      calendarEvents.length,
    )
    expect(calendarEvents).toEqual(snapshot.seasonCalendar.events)
    expect(snapshot).toEqual(before)
  })

  it('keeps Calendar preferences and navigation outside the serialized V2 league truth', () => {
    const snapshot = createLeagueSnapshotV2Fixture()
    const serialized = JSON.stringify(snapshot)
    const identityBefore = projectPersistedIdentity(snapshot)
    const revisionBefore = snapshot.revision

    let activePageId: NavigationPageId = 'schedule-calendar'
    const calendarPreferences = {
      view: 'calendar',
      scope: 'league',
      density: 'comfortable',
      selectedDate: snapshot.season.currentDate,
      inspectedTeamId: snapshot.league.teams[1].id,
      teamScheduleFilter: 'away',
    } as const

    activePageId = DEFAULT_PAGE_ID
    expect(activePageId).toBe('home-today')
    activePageId = 'schedule-calendar'
    expect(activePageId).toBe('schedule-calendar')
    expect(calendarPreferences.inspectedTeamId).not.toBe(
      snapshot.managedTeamId,
    )

    const restored = parseLeagueSnapshotV2(JSON.parse(serialized))
    for (const preferenceKey of [
      'activePageId',
      'calendarView',
      'calendarScope',
      'calendarDensity',
      'selectedDate',
      'inspectedTeamId',
      'teamScheduleFilter',
    ]) {
      expect(Object.hasOwn(restored, preferenceKey)).toBe(false)
    }

    expect(restored.revision).toBe(revisionBefore)
    expect(projectPersistedIdentity(restored)).toEqual(identityBefore)
    expect(snapshot.revision).toBe(revisionBefore)
    expect(JSON.stringify(snapshot)).toBe(serialized)
  })
})

function projectGameReference(game: LeagueSnapshotV2ScheduledGameDto) {
  return {
    id: game.id,
    gameDayId: game.gameDayId,
  }
}

function projectGameLifecycle(game: LeagueSnapshotV2ScheduledGameDto) {
  return {
    id: game.id,
    gameDayId: game.gameDayId,
    originalScheduledDate: game.originalScheduledDate,
    currentScheduledDate: game.currentScheduledDate,
    actualDate: game.actualDate,
  }
}

function projectPersistedIdentity(snapshot: LeagueSnapshotV2) {
  return {
    seasonId: snapshot.season.id,
    seasonScheduleId: snapshot.season.scheduleId,
    scheduleId: snapshot.leagueSchedule.id,
    gameDayIds: snapshot.leagueSchedule.gameDays.map(({ id }) => id),
    gameIds: snapshot.leagueSchedule.games.map(({ id }) => id),
    calendarEventIds: snapshot.seasonCalendar.events.map(({ id }) => id),
    gameOrderAndDates: snapshot.leagueSchedule.games.map(projectGameLifecycle),
  }
}
