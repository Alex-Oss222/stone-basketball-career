import { describe, expect, it } from 'vitest'
import {
  parseLeagueId,
  parseScheduleRuleSetId,
  parseSeasonId,
  parseTeamId,
} from '../../src/domain/ids'
import { parseLocalDate } from '../../src/domain/localDate'
import type { ScheduleRuleSet } from '../../src/domain/schedule'
import { generateNbaRegularSeasonSchedule } from '../../src/generation/generateNbaSchedule'

const TEAMS = Array.from({ length: 30 }, (_, index) => ({
  id: parseTeamId(`team_nba_${String(index).padStart(2, '0')}`),
}))

const NBA_RULE_SET: ScheduleRuleSet = Object.freeze({
  id: parseScheduleRuleSetId('schedule_rule_nba_regular_season_v1'),
  version: 1,
  stage: 'regular_season',
  teamCountPolicy: Object.freeze({ kind: 'exact', count: 30 }),
  gamesPerTeam: 82,
  expectedTotalGames: 1230,
  opponentPolicy: Object.freeze({
    kind: 'uniform_round_robin',
    meetingsPerOpponent: 2,
    homeGamesPerOpponent: 1,
    awayGamesPerOpponent: 1,
  }),
  expectedHomeGamesPerTeam: 41,
  expectedAwayGamesPerTeam: 41,
  gameDayCount: 174,
  expectedGamesPerGameDay: 7,
  everyTeamPlaysEachGameDay: false,
  allowsTbdOpponents: false,
  calendarSpacingRules: Object.freeze({
    minimumDaysBetweenGameDays: 0,
    maximumDaysBetweenGameDays: null,
  }),
})

const INPUT = {
  leagueId: parseLeagueId('league_nba_test'),
  seasonId: parseSeasonId('season_nba_test'),
  teams: TEAMS,
  scheduleSeed: 'nba-schedule-seed',
  ruleSet: NBA_RULE_SET,
  regularSeasonStartDate: parseLocalDate('2026-10-20'),
  windowDays: 174,
}

describe('generateNbaRegularSeasonSchedule', () => {
  it('produces a balanced 1230-game, 82-per-team season', () => {
    const schedule = generateNbaRegularSeasonSchedule(INPUT)

    expect(schedule.games).toHaveLength(1230)

    const home = new Map<string, number>()
    const away = new Map<string, number>()
    for (const game of schedule.games) {
      home.set(game.homeTeamId, (home.get(game.homeTeamId) ?? 0) + 1)
      away.set(game.awayTeamId, (away.get(game.awayTeamId) ?? 0) + 1)
      expect(game.stage).toBe('regular_season')
      expect(game.status).toBe('scheduled')
      expect(game.currentScheduledDate).toBe(game.originalScheduledDate)
    }
    for (const team of TEAMS) {
      expect(home.get(team.id)).toBe(41)
      expect(away.get(team.id)).toBe(41)
    }
  })

  it('never schedules a team twice on the same game-day and links game-days', () => {
    const schedule = generateNbaRegularSeasonSchedule(INPUT)
    const gamesById = new Map(schedule.games.map((game) => [game.id, game]))

    let linkedGames = 0
    for (const gameDay of schedule.gameDays) {
      const teams = new Set<string>()
      for (const gameId of gameDay.gameIds) {
        const game = gamesById.get(gameId)
        expect(game).toBeDefined()
        if (game === undefined) continue
        expect(game.gameDayId).toBe(gameDay.id)
        expect(teams.has(game.homeTeamId)).toBe(false)
        expect(teams.has(game.awayTeamId)).toBe(false)
        teams.add(game.homeTeamId)
        teams.add(game.awayTeamId)
        linkedGames += 1
      }
    }
    expect(linkedGames).toBe(1230)
  })

  it('derives consistent opponent requirements and stays in the window', () => {
    const schedule = generateNbaRegularSeasonSchedule(INPUT)

    expect(schedule.opponentRequirements).toHaveLength((30 * 29) / 2)
    for (const requirement of schedule.opponentRequirements) {
      expect([2, 3]).toContain(requirement.totalMeetings)
      expect(
        requirement.homeGamesForFirstTeam + requirement.homeGamesForSecondTeam,
      ).toBe(requirement.totalMeetings)
    }

    const start = INPUT.regularSeasonStartDate
    const end = parseLocalDate('2027-04-11') // start + 173 days
    for (const game of schedule.games) {
      expect(game.originalScheduledDate >= start).toBe(true)
      expect(game.originalScheduledDate <= end).toBe(true)
    }
  })

  it('is deterministic', () => {
    const first = generateNbaRegularSeasonSchedule(INPUT)
    const second = generateNbaRegularSeasonSchedule(INPUT)
    expect(first).toEqual(second)
  })
})
