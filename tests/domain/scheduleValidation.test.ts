import { describe, expect, it } from 'vitest'

import {
  parseGameDayId,
  parseGameId,
  parseScheduleRuleSetId,
  parseSeasonId,
  parseTeamId,
} from '../../src/domain/ids'
import { parseLocalDate } from '../../src/domain/localDate'
import type { LocalDate } from '../../src/domain/localDate'
import {
  MILESTONE_1_REGULAR_SEASON_RULE_SET,
} from '../../src/domain/schedule'
import type {
  LeagueSchedule,
  ScheduleInvariantCode,
  ScheduledGame,
} from '../../src/domain/schedule'
import { validateLeagueSchedule } from '../../src/domain/scheduleValidation'
import { generateRegularSeasonSchedule } from '../../src/generation/generateSchedule'

const seasonId = parseSeasonId('season_validator_test')
const teams = Array.from({ length: 8 }, (_, index) => ({
  id: parseTeamId(`team_validator_${String(index + 1).padStart(2, '0')}`),
}))
const regularSeasonStartDate = parseLocalDate('2026-10-01')
const calendarDaySpacing = 2

function createSchedule(): LeagueSchedule {
  return generateRegularSeasonSchedule({
    seasonId,
    teams,
    scheduleSeed: 'validator-fixture',
    regularSeasonStartDate,
    calendarDaySpacing,
    ruleSet: MILESTONE_1_REGULAR_SEASON_RULE_SET,
  })
}

function validate(
  schedule: LeagueSchedule,
  options: {
    readonly validationTeams?: typeof teams
    readonly validationSeasonId?: typeof seasonId
    readonly constraints?: Parameters<
      typeof validateLeagueSchedule
    >[0]['constraints']
  } = {},
) {
  return validateLeagueSchedule({
    schedule,
    seasonId: options.validationSeasonId ?? seasonId,
    teams: options.validationTeams ?? teams,
    ruleSet: MILESTONE_1_REGULAR_SEASON_RULE_SET,
    regularSeasonStartDate,
    calendarDaySpacing,
    constraints: options.constraints,
  })
}

function codes(schedule: LeagueSchedule): Set<ScheduleInvariantCode> {
  return new Set(validate(schedule).hardViolations.map(({ code }) => code))
}

function replaceGame(
  schedule: LeagueSchedule,
  index: number,
  replacement: Partial<ScheduledGame>,
): LeagueSchedule {
  return {
    ...schedule,
    games: schedule.games.map((game, gameIndex) =>
      gameIndex === index ? { ...game, ...replacement } : game,
    ),
  }
}

describe('validateLeagueSchedule', () => {
  it('accepts the generated baseline schedule', () => {
    expect(validate(createSchedule())).toEqual({
      valid: true,
      hardViolations: [],
      softWarnings: [],
    })
  })

  it('reports duplicate expected teams and a wrong current-rule team count', () => {
    const validationTeams = [...teams.slice(0, 7), teams[0]]
    const report = validate(createSchedule(), { validationTeams })
    const issueCodes = new Set(
      report.hardViolations.map(({ code }) => code),
    )

    expect(issueCodes).toContain('duplicate_team_id')
    expect(issueCodes).toContain('unknown_team')

    const shortReport = validateLeagueSchedule({
      schedule: createSchedule(),
      seasonId,
      teams: teams.slice(0, 7),
      ruleSet: MILESTONE_1_REGULAR_SEASON_RULE_SET,
      regularSeasonStartDate,
      calendarDaySpacing,
    })
    expect(shortReport.hardViolations.map(({ code }) => code)).toContain(
      'wrong_team_count',
    )
  })

  it('rejects unknown teams and self-matchups', () => {
    const schedule = createSchedule()
    const unknownTeamId = parseTeamId('team_validator_unknown')
    const unknown = replaceGame(schedule, 0, { homeTeamId: unknownTeamId })
    const self = replaceGame(schedule, 0, {
      awayTeamId: schedule.games[0].homeTeamId,
    })

    expect(codes(unknown)).toContain('unknown_team')
    expect(codes(self)).toContain('self_matchup')
  })

  it('rejects duplicate GameIds and duplicate GameDayIds', () => {
    const schedule = createSchedule()
    const duplicateGame = replaceGame(schedule, 1, {
      id: schedule.games[0].id,
    })
    const duplicateDay: LeagueSchedule = {
      ...schedule,
      gameDays: schedule.gameDays.map((gameDay, index) =>
        index === 1 ? { ...gameDay, id: schedule.gameDays[0].id } : gameDay,
      ),
    }

    expect(codes(duplicateGame)).toContain('duplicate_game_id')
    expect(codes(duplicateDay)).toContain('duplicate_game_day_id')
  })

  it('reports duplicate and missing team appearances on a game day', () => {
    const schedule = createSchedule()
    const firstDayId = schedule.gameDays[0].id
    const dayGameIndexes = schedule.games
      .map((game, index) => ({ game, index }))
      .filter(({ game }) => game.gameDayId === firstDayId)
      .map(({ index }) => index)
    const firstGame = schedule.games[dayGameIndexes[0]]
    const secondGame = schedule.games[dayGameIndexes[1]]
    const repeatedTeamId = firstGame.homeTeamId
    const displacedTeamId = secondGame.awayTeamId
    const malformed = replaceGame(schedule, dayGameIndexes[1], {
      awayTeamId: repeatedTeamId,
    })
    const report = validate(malformed)

    expect(
      report.hardViolations.some(
        (issue) =>
          issue.code === 'duplicate_team_appearance' &&
          issue.teamId === repeatedTeamId,
      ),
    ).toBe(true)
    expect(
      report.hardViolations.some(
        (issue) =>
          issue.code === 'missing_team_appearance' &&
          issue.teamId === displacedTeamId,
      ),
    ).toBe(true)
  })

  it('rejects incorrect home-and-away balance', () => {
    const schedule = createSchedule()
    const game = schedule.games[0]
    const swapped = replaceGame(schedule, 0, {
      homeTeamId: game.awayTeamId,
      awayTeamId: game.homeTeamId,
    })

    expect(codes(swapped)).toContain('wrong_pair_home_balance')
  })

  it('rejects duplicate or missing meeting numbers for a pair', () => {
    const schedule = createSchedule()
    const first = schedule.games[0]
    const matchingIndex = schedule.games.findIndex(
      (game, index) =>
        index > 0 &&
        new Set([game.homeTeamId, game.awayTeamId]).has(first.homeTeamId) &&
        new Set([game.homeTeamId, game.awayTeamId]).has(first.awayTeamId),
    )
    const malformed = replaceGame(schedule, matchingIndex, {
      meetingNumber: first.meetingNumber,
    })

    expect(codes(malformed)).toContain('wrong_pair_meeting_count')
  })

  it('rejects malformed game-day and game dates and incorrect spacing', () => {
    const schedule = createSchedule()
    const malformedDate = '2026-02-30' as LocalDate
    const invalidDay: LeagueSchedule = {
      ...schedule,
      gameDays: schedule.gameDays.map((gameDay, index) =>
        index === 0
          ? { ...gameDay, scheduledDate: malformedDate }
          : gameDay,
      ),
    }
    const invalidCurrent = replaceGame(schedule, 0, {
      currentScheduledDate: malformedDate,
    })
    const wrongSpacing: LeagueSchedule = {
      ...schedule,
      gameDays: schedule.gameDays.map((gameDay, index) =>
        index === 1
          ? { ...gameDay, scheduledDate: parseLocalDate('2026-10-06') }
          : gameDay,
      ),
    }

    expect(codes(invalidDay)).toContain('invalid_scheduled_date')
    expect(codes(invalidCurrent)).toContain('invalid_scheduled_date')
    expect(codes(wrongSpacing)).toContain('wrong_game_day_spacing')
  })

  it('requires completed games to have actual dates', () => {
    const schedule = createSchedule()
    const completed = replaceGame(schedule, 0, {
      status: 'completed',
      actualDate: undefined,
    })

    expect(codes(completed)).toContain('completed_game_missing_actual_date')
  })

  it('keeps current and original dates equal while scheduled but allows a completed postponed date', () => {
    const schedule = createSchedule()
    const changedScheduled = replaceGame(schedule, 0, {
      currentScheduledDate: parseLocalDate('2026-12-20'),
    })
    const changedCompleted = replaceGame(schedule, 0, {
      status: 'completed',
      currentScheduledDate: parseLocalDate('2026-12-20'),
      actualDate: parseLocalDate('2026-12-20'),
    })
    const validPostponement = replaceGame(schedule, 0, {
      status: 'postponed',
      currentScheduledDate: parseLocalDate('2026-12-20'),
    })

    expect(codes(changedScheduled)).toContain('invalid_scheduled_date')
    expect(codes(changedCompleted)).not.toContain('invalid_scheduled_date')
    expect(codes(validPostponement)).not.toContain(
      'lost_original_scheduled_date',
    )
  })

  it('requires scheduled games to retain a current date', () => {
    const schedule = createSchedule()
    const malformed = replaceGame(schedule, 0, {
      status: 'scheduled',
      currentScheduledDate: null,
    })

    expect(codes(malformed)).toContain('invalid_scheduled_date')
  })

  it('requires completed games to retain a current scheduled date', () => {
    const schedule = createSchedule()
    const malformed = replaceGame(schedule, 0, {
      status: 'completed',
      currentScheduledDate: null,
      actualDate: parseLocalDate('2026-10-01'),
    })

    expect(codes(malformed)).toContain('invalid_scheduled_date')
  })

  it('rejects actual dates on games that are not completed', () => {
    const schedule = createSchedule()
    const malformed = replaceGame(schedule, 0, {
      status: 'scheduled',
      actualDate: parseLocalDate('2026-10-01'),
    })

    expect(codes(malformed)).toContain('invalid_game_status')
  })

  it('rejects postponed games that lose their original date', () => {
    const schedule = createSchedule()
    const postponed = replaceGame(schedule, 0, {
      status: 'postponed',
      originalScheduledDate: undefined as unknown as LocalDate,
      currentScheduledDate: null,
    })

    expect(codes(postponed)).toContain('lost_original_scheduled_date')
  })

  it('rejects schedules, game days, and games referencing the wrong SeasonId', () => {
    const schedule = createSchedule()
    const wrongSeasonId = parseSeasonId('season_wrong')
    const wrong: LeagueSchedule = {
      ...schedule,
      seasonId: wrongSeasonId,
      gameDays: schedule.gameDays.map((gameDay, index) =>
        index === 0 ? { ...gameDay, seasonId: wrongSeasonId } : gameDay,
      ),
      games: schedule.games.map((game, index) =>
        index === 0 ? { ...game, seasonId: wrongSeasonId } : game,
      ),
    }
    const report = validate(wrong)

    expect(report.hardViolations.filter(({ code }) => code === 'wrong_season')).not
      .toHaveLength(0)
  })

  it('rejects the wrong rule-set identity explicitly', () => {
    const schedule: LeagueSchedule = {
      ...createSchedule(),
      ruleSetId: parseScheduleRuleSetId('schedule_rule_future_v2'),
    }

    expect(codes(schedule)).toContain('wrong_rule_set')
  })

  it('rejects malformed schedule identity and noncanonical or blank seeds', () => {
    const baseline = createSchedule()
    const invalidId: LeagueSchedule = {
      ...baseline,
      id: 'Schedule Invalid' as never,
    }
    const blankSeed: LeagueSchedule = { ...baseline, scheduleSeed: '   ' }
    const noncanonicalSeed: LeagueSchedule = {
      ...baseline,
      scheduleSeed: '  validator-fixture  ',
    }

    expect(codes(invalidId)).toContain('invalid_schedule_id')
    expect(codes(blankSeed)).toContain('invalid_schedule_seed')
    expect(codes(noncanonicalSeed)).toContain('invalid_schedule_seed')
  })

  it('rejects an unsupported schedule publication status', () => {
    const schedule: LeagueSchedule = {
      ...createSchedule(),
      publicationStatus: 'hidden' as never,
    }

    expect(codes(schedule)).toContain('invalid_schedule_status')
  })

  it('rejects mismatched opponent requirements independently of games', () => {
    const baseline = createSchedule()
    const schedule: LeagueSchedule = {
      ...baseline,
      opponentRequirements: baseline.opponentRequirements.slice(1),
    }

    expect(codes(schedule)).toContain('opponent_requirement_mismatch')
  })

  it('rejects game-day reference mismatches', () => {
    const schedule = createSchedule()
    const malformed = replaceGame(schedule, 0, {
      gameDayId: parseGameDayId('game_day_missing'),
    })

    expect(codes(malformed)).toContain('game_day_reference_mismatch')
  })

  it('rejects invalid or negative numeric values', () => {
    const baseline = createSchedule()
    const schedule: LeagueSchedule = {
      ...baseline,
      generationVersion: Number.NaN,
      games: baseline.games.map((game, index) =>
        index === 0 ? { ...game, meetingNumber: -1 } : game,
      ),
    }

    expect(codes(schedule)).toContain('invalid_numeric_value')

    const zeroVersion: LeagueSchedule = {
      ...createSchedule(),
      generationVersion: 0,
    }
    expect(codes(zeroVersion)).toContain('invalid_numeric_value')
  })

  it('reports calendar overflow as a diagnostic instead of throwing', () => {
    const schedule = createSchedule()
    const runValidation = () =>
      validateLeagueSchedule({
        schedule,
        seasonId,
        teams,
        ruleSet: MILESTONE_1_REGULAR_SEASON_RULE_SET,
        regularSeasonStartDate: parseLocalDate('9999-12-31'),
        calendarDaySpacing: 2,
      })

    expect(runValidation).not.toThrow()
    expect(
      runValidation().hardViolations.map(({ code }) => code),
    ).toContain('wrong_game_day_spacing')
  })

  it('reports unsupported constraints instead of silently ignoring them', () => {
    const hardReport = validate(createSchedule(), {
      constraints: [
        {
          kind: 'team_unavailable_on_date',
          severity: 'hard',
          teamId: teams[0].id,
          date: regularSeasonStartDate,
        },
      ],
    })
    const softReport = validate(createSchedule(), {
      constraints: [
        {
          kind: 'showcase_game_preference',
          severity: 'soft',
          firstTeamId: teams[0].id,
          secondTeamId: teams[1].id,
        },
      ],
    })

    expect(hardReport.valid).toBe(false)
    expect(hardReport.hardViolations.map(({ code }) => code)).toContain(
      'unsupported_constraint',
    )
    expect(softReport.valid).toBe(true)
    expect(softReport.softWarnings.map(({ code }) => code)).toContain(
      'unsupported_constraint',
    )
  })

  it('collects multiple detectable violations instead of stopping early', () => {
    const baseline = createSchedule()
    const firstGame = baseline.games[0]
    const schedule: LeagueSchedule = {
      ...baseline,
      generationVersion: -1,
      gameDays: baseline.gameDays.slice(1),
      games: baseline.games.map((game, index) => {
        if (index === 0) {
          return {
            ...game,
            id: parseGameId('game_duplicate_for_report'),
            homeTeamId: firstGame.awayTeamId,
            awayTeamId: firstGame.awayTeamId,
            status: 'completed',
            actualDate: undefined,
          }
        }
        if (index === 1) {
          return { ...game, id: parseGameId('game_duplicate_for_report') }
        }
        return game
      }),
    }
    const issueCodes = codes(schedule)

    expect(issueCodes).toEqual(
      expect.objectContaining({
        size: expect.any(Number),
      }),
    )
    expect(issueCodes).toContain('invalid_numeric_value')
    expect(issueCodes).toContain('wrong_game_day_count')
    expect(issueCodes).toContain('duplicate_game_id')
    expect(issueCodes).toContain('self_matchup')
    expect(issueCodes).toContain('completed_game_missing_actual_date')
    expect(issueCodes.size).toBeGreaterThanOrEqual(5)
  })
})
