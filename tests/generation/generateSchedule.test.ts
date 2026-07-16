import { describe, expect, it } from 'vitest'

import { parseSeasonId, parseTeamId } from '../../src/domain/ids'
import { addDays, parseLocalDate } from '../../src/domain/localDate'
import {
  MILESTONE_1_REGULAR_SEASON_RULE_SET,
  buildOpponentRequirementMatrix,
  getTeamPairKey,
} from '../../src/domain/schedule'
import { validateLeagueSchedule } from '../../src/domain/scheduleValidation'
import {
  UnsupportedScheduleConstraintsError,
  deriveStableScheduledGameId,
  generateRegularSeasonSchedule,
} from '../../src/generation/generateSchedule'

const seasonId = parseSeasonId('season_schedule_test_01')
const teams = Array.from({ length: 8 }, (_, index) => ({
  id: parseTeamId(`team_schedule_test_${String(index + 1).padStart(2, '0')}`),
}))
const regularSeasonStartDate = parseLocalDate('2026-10-05')
const calendarDaySpacing = 3

function generate(seed = 'schedule-seed-one') {
  return generateRegularSeasonSchedule({
    seasonId,
    teams,
    scheduleSeed: seed,
    regularSeasonStartDate,
    calendarDaySpacing,
    ruleSet: MILESTONE_1_REGULAR_SEASON_RULE_SET,
  })
}

describe('generateRegularSeasonSchedule', () => {
  it('generates and validates the complete current 8-team schedule', () => {
    const schedule = generate()
    const report = validateLeagueSchedule({
      schedule,
      seasonId,
      teams,
      ruleSet: MILESTONE_1_REGULAR_SEASON_RULE_SET,
      regularSeasonStartDate,
      calendarDaySpacing,
    })

    expect(report).toEqual({
      valid: true,
      hardViolations: [],
      softWarnings: [],
    })
    expect(schedule.gameDays).toHaveLength(28)
    expect(schedule.games).toHaveLength(112)
    expect(schedule.gameDays.every((gameDay) => gameDay.gameIds.length === 4)).toBe(
      true,
    )
    expect(new Set(schedule.gameDays.map(({ id }) => id))).toHaveLength(28)
    expect(new Set(schedule.games.map(({ id }) => id))).toHaveLength(112)
  })

  it('produces exactly 28 games, 14 home games, and 14 away games per team', () => {
    const schedule = generate()

    for (const team of teams) {
      const games = schedule.games.filter(
        (game) =>
          game.homeTeamId === team.id || game.awayTeamId === team.id,
      )
      expect(games).toHaveLength(28)
      expect(games.filter(({ homeTeamId }) => homeTeamId === team.id)).toHaveLength(
        14,
      )
      expect(games.filter(({ awayTeamId }) => awayTeamId === team.id)).toHaveLength(
        14,
      )
    }
  })

  it('gives every pair four meetings split two home games apiece', () => {
    const schedule = generate()

    for (const requirement of schedule.opponentRequirements) {
      const games = schedule.games.filter(
        (game) =>
          getTeamPairKey(game.homeTeamId, game.awayTeamId) ===
          getTeamPairKey(
            requirement.firstTeamId,
            requirement.secondTeamId,
          ),
      )
      expect(games).toHaveLength(4)
      expect(
        games.filter(
          ({ homeTeamId }) => homeTeamId === requirement.firstTeamId,
        ),
      ).toHaveLength(2)
      expect(
        games.filter(
          ({ homeTeamId }) => homeTeamId === requirement.secondTeamId,
        ),
      ).toHaveLength(2)
      expect(games.map(({ meetingNumber }) => meetingNumber).sort()).toEqual([
        1, 2, 3, 4,
      ])
    }
  })

  it('places every team exactly once on each game day', () => {
    const schedule = generate()
    const gamesById = new Map(schedule.games.map((game) => [game.id, game]))

    for (const gameDay of schedule.gameDays) {
      const appearances = gameDay.gameIds.flatMap((gameId) => {
        const game = gamesById.get(gameId)
        if (game === undefined) {
          throw new Error(`Missing test game ${gameId}`)
        }
        return [game.homeTeamId, game.awayTeamId]
      })
      expect(new Set(appearances)).toEqual(new Set(teams.map(({ id }) => id)))
      expect(appearances).toHaveLength(8)
    }
  })

  it('uses exact calendar-day spacing and preserves original scheduled dates', () => {
    const schedule = generate()

    schedule.gameDays.forEach((gameDay, index) => {
      expect(gameDay.sequenceNumber).toBe(index + 1)
      expect(gameDay.scheduledDate).toBe(
        addDays(regularSeasonStartDate, index * calendarDaySpacing),
      )
      const games = schedule.games.filter(
        ({ gameDayId }) => gameDayId === gameDay.id,
      )
      expect(
        games.every(
          (game) =>
            game.originalScheduledDate === gameDay.scheduledDate &&
            game.currentScheduledDate === gameDay.scheduledDate,
        ),
      ).toBe(true)
    })
  })

  it('is deeply deterministic for identical inputs and insensitive to team input order', () => {
    const first = generate()
    const second = generate()
    const reversedTeams = generateRegularSeasonSchedule({
      seasonId,
      teams: [...teams].reverse(),
      scheduleSeed: 'schedule-seed-one',
      regularSeasonStartDate,
      calendarDaySpacing,
      ruleSet: MILESTONE_1_REGULAR_SEASON_RULE_SET,
    })

    expect(second).toEqual(first)
    expect(reversedTeams).toEqual(first)
  })

  it('binds schedule and game-day identities to the canonical participant set', () => {
    const first = generate()
    const changedParticipants = [
      ...teams.slice(0, 7),
      { id: parseTeamId('team_schedule_test_replacement') },
    ]
    const changed = generateRegularSeasonSchedule({
      seasonId,
      teams: changedParticipants,
      scheduleSeed: 'schedule-seed-one',
      regularSeasonStartDate,
      calendarDaySpacing,
      ruleSet: MILESTONE_1_REGULAR_SEASON_RULE_SET,
    })

    expect(changed.id).not.toBe(first.id)
    expect(changed.gameDays.map(({ id }) => id)).not.toEqual(
      first.gameDays.map(({ id }) => id),
    )
  })

  it('pins stable schedule, game-day, and game identity golden vectors', () => {
    const schedule = generate()

    expect(schedule.id).toBe('schedule_cc00d4b97d634c3d5c739209')
    expect(schedule.gameDays[0].id).toBe(
      'game_day_16fc81f0ce10777cd05d0c54',
    )
    expect(schedule.gameDays[0].gameIds[0]).toBe(
      'game_cbd856da2af74dc4d1fdc587',
    )
  })

  it('lets different seeds alter placement without changing opponent totals', () => {
    const first = generate('schedule-seed-one')
    const second = generate('schedule-seed-two')

    expect(second.gameDays.map(({ gameIds }) => gameIds)).not.toEqual(
      first.gameDays.map(({ gameIds }) => gameIds),
    )
    expect(second.opponentRequirements).toEqual(first.opponentRequirements)
    expect(
      second.opponentRequirements.map(
        ({ firstTeamId, secondTeamId, totalMeetings }) => ({
          pair: getTeamPairKey(firstTeamId, secondTeamId),
          totalMeetings,
        }),
      ),
    ).toEqual(
      first.opponentRequirements.map(
        ({ firstTeamId, secondTeamId, totalMeetings }) => ({
          pair: getTeamPairKey(firstTeamId, secondTeamId),
          totalMeetings,
        }),
      ),
    )
  })

  it('constructs the opponent matrix before and independently from date placement', () => {
    const expectedMatrix = buildOpponentRequirementMatrix(
      teams.map(({ id }) => id),
      MILESTONE_1_REGULAR_SEASON_RULE_SET,
    )
    const first = generate()
    const moved = generateRegularSeasonSchedule({
      seasonId,
      teams,
      scheduleSeed: 'schedule-seed-one',
      regularSeasonStartDate: parseLocalDate('2027-01-12'),
      calendarDaySpacing: 5,
      ruleSet: MILESTONE_1_REGULAR_SEASON_RULE_SET,
    })

    expect(first.opponentRequirements).toEqual(expectedMatrix)
    expect(moved.opponentRequirements).toEqual(expectedMatrix)
    expect(moved.games.map(({ id }) => id)).toEqual(
      first.games.map(({ id }) => id),
    )
    expect(moved.games.map(({ originalScheduledDate }) => originalScheduledDate)).not.toEqual(
      first.games.map(({ originalScheduledDate }) => originalScheduledDate),
    )
  })

  it('derives game IDs from pair and cycle identity without placement inputs', () => {
    const common = {
      seasonId,
      ruleSet: MILESTONE_1_REGULAR_SEASON_RULE_SET,
      scheduleSeed: 'stable-game-seed',
      cycleSlot: 2,
    } as const
    const first = deriveStableScheduledGameId({
      ...common,
      firstTeamId: teams[0].id,
      secondTeamId: teams[7].id,
    })
    const reversedPair = deriveStableScheduledGameId({
      ...common,
      firstTeamId: teams[7].id,
      secondTeamId: teams[0].id,
    })
    const anotherCycle = deriveStableScheduledGameId({
      ...common,
      cycleSlot: 3,
      firstTeamId: teams[0].id,
      secondTeamId: teams[7].id,
    })

    expect(reversedPair).toBe(first)
    expect(anotherCycle).not.toBe(first)
  })

  it('generates no NaN or negative numeric schedule values', () => {
    const schedule = generate()
    const values = [
      schedule.generationVersion,
      schedule.calendarDaySpacing,
      ...schedule.gameDays.map(({ sequenceNumber }) => sequenceNumber),
      ...schedule.games.map(({ meetingNumber }) => meetingNumber),
    ]

    expect(values.every((value) => Number.isFinite(value) && value >= 0)).toBe(
      true,
    )
  })

  it('rejects a wrong team count and duplicate team IDs', () => {
    expect(() =>
      generateRegularSeasonSchedule({
        seasonId,
        teams: teams.slice(0, 7),
        scheduleSeed: 'wrong-count',
        regularSeasonStartDate,
        calendarDaySpacing,
        ruleSet: MILESTONE_1_REGULAR_SEASON_RULE_SET,
      }),
    ).toThrow(/team count/i)
    expect(() =>
      generateRegularSeasonSchedule({
        seasonId,
        teams: [...teams.slice(0, 7), teams[0]],
        scheduleSeed: 'duplicate-team',
        regularSeasonStartDate,
        calendarDaySpacing,
        ruleSet: MILESTONE_1_REGULAR_SEASON_RULE_SET,
      }),
    ).toThrow(/unique TeamIds/i)
  })

  it('rejects a structurally mutated rule set that spoofs the current ID and version', () => {
    const spoofedRuleSet = {
      ...MILESTONE_1_REGULAR_SEASON_RULE_SET,
      expectedTotalGames: 111,
    }

    expect(() =>
      generateRegularSeasonSchedule({
        seasonId,
        teams,
        scheduleSeed: 'spoofed-rules',
        regularSeasonStartDate,
        calendarDaySpacing,
        ruleSet: spoofedRuleSet,
      }),
    ).toThrow(/only the Milestone 1 regular-season rule set v1/i)
  })

  it('rejects malformed dates, invalid spacing, and unsupported constraints', () => {
    expect(() =>
      generateRegularSeasonSchedule({
        seasonId,
        teams,
        scheduleSeed: 'bad-date',
        regularSeasonStartDate: '2026-02-30' as never,
        calendarDaySpacing,
        ruleSet: MILESTONE_1_REGULAR_SEASON_RULE_SET,
      }),
    ).toThrow(/valid calendar date/i)
    expect(() =>
      generateRegularSeasonSchedule({
        seasonId,
        teams,
        scheduleSeed: 'bad-spacing',
        regularSeasonStartDate,
        calendarDaySpacing: -1,
        ruleSet: MILESTONE_1_REGULAR_SEASON_RULE_SET,
      }),
    ).toThrow(/spacing/i)
    expect(() =>
      generateRegularSeasonSchedule({
        seasonId,
        teams,
        scheduleSeed: 'constraint',
        regularSeasonStartDate,
        calendarDaySpacing,
        ruleSet: MILESTONE_1_REGULAR_SEASON_RULE_SET,
        constraints: [
          {
            kind: 'team_unavailable_on_date',
            severity: 'hard',
            teamId: teams[0].id,
            date: regularSeasonStartDate,
          },
        ],
      }),
    ).toThrow(UnsupportedScheduleConstraintsError)
  })
})
