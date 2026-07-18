import { describe, expect, expectTypeOf, it } from 'vitest'
import {
  findNextScheduledGame,
  formatSeasonPhaseForDisplay,
  getTeamLocation,
  getUpcomingScheduledGames,
  resolveOpponent,
} from '../../src/app/scheduleViewModel'
import type { TeamScheduleLocation } from '../../src/app/scheduleViewModel'
import {
  parseGameDayId,
  parseGameId,
  parseLeagueId,
  parseScheduleId,
  parseScheduleRuleSetId,
  parseSeasonId,
  parseTeamId,
} from '../../src/domain/ids'
import { parseLocalDate } from '../../src/domain/localDate'
import type {
  LeagueSnapshotGameDayDto,
  LeagueSnapshotLeagueDto,
  LeagueSnapshotLeagueScheduleDto,
  LeagueSnapshotScheduledGameDto,
  LeagueSnapshotTeamDto,
} from '../../src/persistence/leagueSnapshot'

const TEAM_A_ID = parseTeamId('team_schedule_view_a')
const TEAM_B_ID = parseTeamId('team_schedule_view_b')
const TEAM_C_ID = parseTeamId('team_schedule_view_c')
const FOREIGN_TEAM_ID = parseTeamId('team_schedule_view_foreign')
const SEASON_ID = parseSeasonId('season_schedule_view_1')

const GAME_DAY_IDS = [1, 2, 3, 4, 5, 6].map((number) =>
  parseGameDayId(`game_day_schedule_view_${number}`),
)
const GAME_IDS = [1, 2, 3, 4, 5, 6].map((number) =>
  parseGameId(`game_schedule_view_${number}`),
)

const games = Object.freeze([
  game(0, 0, TEAM_A_ID, TEAM_B_ID, '2026-10-09', 'scheduled'),
  game(1, 1, TEAM_A_ID, TEAM_C_ID, '2026-10-05', 'completed'),
  game(2, 2, TEAM_B_ID, TEAM_A_ID, '2026-10-07', 'scheduled'),
  game(3, 3, TEAM_B_ID, TEAM_C_ID, '2026-10-08', 'scheduled'),
  game(4, 4, TEAM_C_ID, TEAM_A_ID, '2026-10-10', 'postponed'),
  game(5, 5, TEAM_A_ID, TEAM_C_ID, '2026-10-12', 'cancelled'),
])

const gameDays = Object.freeze([
  gameDay(1),
  gameDay(0),
  gameDay(2),
  gameDay(3),
  gameDay(4),
  gameDay(5),
])

const schedule: LeagueSnapshotLeagueScheduleDto = Object.freeze({
  id: parseScheduleId('schedule_view_model_fixture'),
  leagueId: parseLeagueId('league_schedule_view_model'),
  seasonId: SEASON_ID,
  ruleSetId: parseScheduleRuleSetId('schedule_rule_view_model_fixture'),
  generationVersion: 1,
  scheduleSeed: 'schedule-view-model-fixture',
  calendarDaySpacing: 1,
  publicationStatus: 'published',
  opponentRequirements: Object.freeze([]),
  gameDays,
  games,
})

const league: LeagueSnapshotLeagueDto = Object.freeze({
  id: schedule.leagueId,
  generatorVersion: 1,
  detailedRatingsSchemaVersion: 1,
  categoryDefinitionVersion: 1,
  seedFingerprint: 'scheduleview',
  teams: Object.freeze([
    team(TEAM_A_ID, 'Amber', 'Arches', 'AMA'),
    team(TEAM_B_ID, 'Beryl', 'Beacons', 'BRB'),
    team(TEAM_C_ID, 'Cinder', 'Comets', 'CIC'),
  ]),
  players: Object.freeze([]),
})

describe('stored matchup opponent and location resolution', () => {
  it('resolves the real opponent and selected-team location', () => {
    expect(resolveOpponent(league, games[0], TEAM_A_ID)).toBe(league.teams[1])
    expect(resolveOpponent(league, games[2], TEAM_A_ID)).toBe(league.teams[1])
    expect(getTeamLocation(games[0], TEAM_A_ID)).toBe('home')
    expect(getTeamLocation(games[2], TEAM_A_ID)).toBe('away')
  })

  it('rejects nonparticipants, missing opponents, and ambiguous self-matchups', () => {
    expect(() => getTeamLocation(games[0], FOREIGN_TEAM_ID)).toThrow(
      /does not participate/,
    )

    const leagueWithoutB = { ...league, teams: [league.teams[0], league.teams[2]] }
    expect(() => resolveOpponent(leagueWithoutB, games[0], TEAM_A_ID)).toThrow(
      /does not reference a league team/,
    )

    const selfMatchup = {
      ...games[0],
      awayTeamId: games[0].homeTeamId,
    }
    expect(() => getTeamLocation(selfMatchup, TEAM_A_ID)).toThrow(
      /distinct teams/,
    )
  })
})

describe('upcoming schedule selection', () => {
  const currentDate = parseLocalDate('2026-10-06')

  it('preserves stored order for upcoming games while excluding completed and cancelled games', () => {
    expect(
      getUpcomingScheduledGames(schedule, TEAM_A_ID, currentDate).map(
        ({ id }) => id,
      ),
    ).toEqual([GAME_IDS[0], GAME_IDS[2], GAME_IDS[4]])
  })

  it('finds the earliest calendar date without sorting or mutating stored games', () => {
    const before = structuredClone(schedule.games)
    expect(findNextScheduledGame(schedule, TEAM_A_ID, currentDate)?.id).toBe(
      GAME_IDS[2],
    )
    expect(schedule.games).toEqual(before)
    expect(
      findNextScheduledGame(
        schedule,
        TEAM_A_ID,
        parseLocalDate('2026-10-11'),
      ),
    ).toBeNull()
  })

  it('retains the first stored game when next-game dates tie', () => {
    const tiedSchedule = {
      ...schedule,
      games: [
        { ...games[0], currentScheduledDate: parseLocalDate('2026-10-07') },
        games[2],
      ],
    }
    expect(findNextScheduledGame(tiedSchedule, TEAM_A_ID, currentDate)?.id).toBe(
      GAME_IDS[0],
    )
  })
})

describe('deterministic schedule display formatting', () => {
  it('uses explicit labels for every broad season phase', () => {
    expect([
      formatSeasonPhaseForDisplay('offseason'),
      formatSeasonPhaseForDisplay('training_camp'),
      formatSeasonPhaseForDisplay('preseason'),
      formatSeasonPhaseForDisplay('regular_season'),
      formatSeasonPhaseForDisplay('postseason'),
      formatSeasonPhaseForDisplay('complete'),
    ]).toEqual([
      'Offseason',
      'Training camp',
      'Preseason',
      'Regular season',
      'Postseason',
      'Complete',
    ])
  })

  it('exports the narrow team-location type', () => {
    expectTypeOf<TeamScheduleLocation>().toEqualTypeOf<'home' | 'away'>()
  })
})

function game(
  index: number,
  gameDayIndex: number,
  homeTeamId: typeof TEAM_A_ID,
  awayTeamId: typeof TEAM_A_ID,
  currentScheduledDate: string,
  status: LeagueSnapshotScheduledGameDto['status'],
): LeagueSnapshotScheduledGameDto {
  const date = parseLocalDate(currentScheduledDate)
  return Object.freeze({
    id: GAME_IDS[index],
    seasonId: SEASON_ID,
    gameDayId: GAME_DAY_IDS[gameDayIndex],
    stage: 'regular_season',
    homeTeamId,
    awayTeamId,
    originalScheduledDate: date,
    currentScheduledDate: date,
    actualDate: status === 'completed' ? date : null,
    status,
    meetingNumber: 1,
  })
}

function gameDay(index: number): LeagueSnapshotGameDayDto {
  return Object.freeze({
    id: GAME_DAY_IDS[index],
    seasonId: SEASON_ID,
    sequenceNumber: index + 1,
    scheduledDate: games[index].originalScheduledDate,
    gameIds: Object.freeze([GAME_IDS[index]]),
  })
}

function team(
  id: typeof TEAM_A_ID,
  city: string,
  nickname: string,
  abbreviation: string,
): LeagueSnapshotTeamDto {
  return Object.freeze({
    id,
    city,
    nickname,
    abbreviation,
    colors: Object.freeze({
      primary: '#111111',
      secondary: '#222222',
      accent: '#ff9900',
    }),
    mark: Object.freeze({ kind: 'initials', text: abbreviation }),
  })
}
