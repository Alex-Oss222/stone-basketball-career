import { describe, expect, it } from 'vitest'
import { resolveOpponent } from '../../src/app/scheduleViewModel'
import { DEFAULT_PAGE_ID } from '../../src/app/navigation'
import {
  parseLeagueSnapshot,
} from '../../src/persistence/leagueSnapshot'
import type {
  LeagueSnapshot,
  LeagueSnapshotScheduledGameDto,
} from '../../src/persistence/leagueSnapshot'
import { createLeagueSnapshotFixture } from '../persistence/leagueSnapshot.fixture'

describe('M2.1 calendar contract characterization', () => {
  it('preserves complete team-game identities and allows inspection independently of the managed team', () => {
    const snapshot = createLeagueSnapshotFixture()
    const before = structuredClone(snapshot)
    const inspectedTeamId = snapshot.league.teams[1].id

    expect(inspectedTeamId).not.toBe(snapshot.managedTeamId)

    const inspectedGames = snapshot.leagueSchedule.games.filter(
      (game) =>
        game.homeTeamId === inspectedTeamId ||
        game.awayTeamId === inspectedTeamId,
    )
    expect(inspectedGames.length).toBeGreaterThan(0)

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
    const snapshot = createLeagueSnapshotFixture()
    const before = structuredClone(snapshot)
    const storedGamesById = new Map(
      snapshot.leagueSchedule.games.map((game) => [game.id, game] as const),
    )
    const groups = snapshot.leagueSchedule.gameDays.map((gameDay) => ({
      gameDay,
      games: gameDay.gameIds.map((gameId) => {
        const game = storedGamesById.get(gameId)
        expect(game).toBeDefined()
        expect((game as LeagueSnapshotScheduledGameDto).gameDayId).toBe(
          gameDay.id,
        )
        return game as LeagueSnapshotScheduledGameDto
      }),
    }))
    const groupedGames = groups.flatMap((group) => group.games)
    const declaredGameIds = snapshot.leagueSchedule.gameDays.flatMap(
      (gameDay) => gameDay.gameIds,
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
        projectGameLifecycle(storedGame as LeagueSnapshotScheduledGameDto),
      )
    }

    const calendarEvents = snapshot.seasonCalendar.events.map((event) => event)
    expect(new Set(calendarEvents.map(({ id }) => id)).size).toBe(
      calendarEvents.length,
    )
    expect(calendarEvents).toEqual(snapshot.seasonCalendar.events)
    expect(snapshot).toEqual(before)
  })

  it('keeps Calendar preferences and navigation outside the serialized league truth', () => {
    const snapshot = createLeagueSnapshotFixture()
    const serialized = JSON.stringify(snapshot)
    const identityBefore = projectPersistedIdentity(snapshot)
    const revisionBefore = snapshot.revision

    const calendarPreferences = {
      view: 'calendar',
      scope: 'league',
      density: 'comfortable',
      selectedDate: snapshot.season.currentDate,
      inspectedTeamId: snapshot.league.teams[1].id,
      teamScheduleFilter: 'away',
    } as const

    expect(DEFAULT_PAGE_ID).toBe('home-today')
    expect(calendarPreferences.inspectedTeamId).not.toBe(
      snapshot.managedTeamId,
    )

    const restored = parseLeagueSnapshot(JSON.parse(serialized))
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

function projectGameLifecycle(game: LeagueSnapshotScheduledGameDto) {
  return {
    id: game.id,
    gameDayId: game.gameDayId,
    originalScheduledDate: game.originalScheduledDate,
    currentScheduledDate: game.currentScheduledDate,
    actualDate: game.actualDate,
  }
}

function projectPersistedIdentity(snapshot: LeagueSnapshot) {
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
