import { describe, expect, it } from 'vitest'

import {
  InvalidSeasonFoundationError,
  assertValidSeasonFoundation,
  createSeasonFoundation,
  deriveSeasonFoundationCalendarEventId,
  deriveSeasonFoundationCalendarId,
  deriveSeasonFoundationSeasonId,
  deriveSeasonFoundationTeamSeasonId,
  validateSeasonFoundation,
} from '../../../src/app/commands/createSeasonFoundation'
import type {
  CreateSeasonFoundationInput,
  SeasonFoundation,
} from '../../../src/app/commands/createSeasonFoundation'
import {
  parseCalendarEventId,
  parseLeagueId,
  parseScheduleId,
  parseSeasonCalendarId,
  parseSeasonId,
  parseTeamId,
  parseTeamSeasonId,
} from '../../../src/domain/ids'
import type { League } from '../../../src/domain/league'
import { InvalidLeagueError } from '../../../src/domain/leagueValidation'
import { addDays, parseLocalDate } from '../../../src/domain/localDate'
import type { LocalDate } from '../../../src/domain/localDate'
import { MILESTONE_1_REGULAR_SEASON_RULE_SET } from '../../../src/domain/schedule'
import type { LeagueSchedule } from '../../../src/domain/schedule'
import {
  CALENDAR_EVENT_VERSION,
  createCalendarEvent,
} from '../../../src/domain/seasonCalendar'
import { generateLeague } from '../../../src/generation/generateLeague'
import { generateRegularSeasonSchedule } from '../../../src/generation/generateSchedule'

const LEAGUE_SEED = 'season-foundation-league'
const SCHEDULE_SEED = 'season-foundation-schedule'
const STARTING_YEAR = 2026
const START_DATE = parseLocalDate('2026-10-05')
const CALENDAR_DAY_SPACING = 3
const EXPECTED_CONCLUSION_DATE = addDays(
  START_DATE,
  (MILESTONE_1_REGULAR_SEASON_RULE_SET.gameDayCount - 1) *
    CALENDAR_DAY_SPACING,
)

const league = generateLeague(LEAGUE_SEED)

function input(
  overrides: Partial<CreateSeasonFoundationInput> = {},
): CreateSeasonFoundationInput {
  return {
    league,
    startingYear: STARTING_YEAR,
    regularSeasonStartDate: START_DATE,
    calendarDaySpacing: CALENDAR_DAY_SPACING,
    scheduleSeed: SCHEDULE_SEED,
    ...overrides,
  }
}

function validate(
  foundation: SeasonFoundation,
  overrides: Partial<CreateSeasonFoundationInput> = {},
) {
  const creationInput = input(overrides)
  return validateSeasonFoundation({ ...creationInput, foundation })
}

function issueCodes(
  foundation: SeasonFoundation,
  overrides: Partial<CreateSeasonFoundationInput> = {},
): Set<string> {
  return new Set(validate(foundation, overrides).map(({ code }) => code))
}

function replaceSchedule(
  foundation: SeasonFoundation,
  schedule: LeagueSchedule,
): SeasonFoundation {
  return { ...foundation, schedule }
}

describe('createSeasonFoundation', () => {
  it('creates one valid, cross-referenced Milestone 1 season package', () => {
    const foundation = createSeasonFoundation(input())
    const { calendar, schedule, season, teamSeasons } = foundation

    expect(season).toMatchObject({
      leagueId: league.id,
      seasonNumber: 1,
      startingYear: 2026,
      endingYear: 2027,
      displayLabel: '2026–27',
      rulesVersion: MILESTONE_1_REGULAR_SEASON_RULE_SET.version,
      currentDate: START_DATE,
      currentPhase: 'regular_season',
      scheduleId: schedule.id,
      status: 'schedule_ready',
    })
    expect(schedule).toMatchObject({
      leagueId: league.id,
      seasonId: season.id,
      ruleSetId: MILESTONE_1_REGULAR_SEASON_RULE_SET.id,
      scheduleSeed: SCHEDULE_SEED,
      calendarDaySpacing: CALENDAR_DAY_SPACING,
    })
    expect(schedule.gameDays).toHaveLength(28)
    expect(schedule.games).toHaveLength(112)
    expect(schedule.opponentRequirements).toHaveLength(28)

    expect(teamSeasons).toHaveLength(league.teams.length)
    expect(teamSeasons.map(({ teamId }) => teamId)).toEqual(
      league.teams.map(({ id }) => id),
    )
    expect(new Set(teamSeasons.map(({ id }) => id)).size).toBe(8)
    for (const teamSeason of teamSeasons) {
      expect(teamSeason).toMatchObject({
        seasonId: season.id,
        competitiveStatus: 'active',
        eliminationDate: null,
        teamOffseasonStartDate: null,
        postseasonSeed: null,
      })
      expect(teamSeason.id).toBe(
        deriveSeasonFoundationTeamSeasonId(
          season.id,
          teamSeason.teamId,
        ),
      )
    }

    expect(calendar).toMatchObject({
      id: deriveSeasonFoundationCalendarId(season.id),
      version: 1,
      seasonId: season.id,
    })
    expect(calendar.events.map(({ kind }) => kind)).toEqual([
      'regular_season_opening',
      'regular_season_conclusion',
    ])
    expect(calendar.events.map(({ scheduledDate }) => scheduledDate)).toEqual([
      START_DATE,
      EXPECTED_CONCLUSION_DATE,
    ])
    expect(new Set(calendar.events.map(({ id }) => id)).size).toBe(2)
    for (const event of calendar.events) {
      if (
        event.kind !== 'regular_season_opening' &&
        event.kind !== 'regular_season_conclusion'
      ) {
        throw new Error(`Unexpected foundation event kind: ${event.kind}`)
      }
      expect(event).toMatchObject({
        seasonId: season.id,
        scope: 'league',
        originalScheduledDate: event.scheduledDate,
        actualDate: null,
        dateStatus: 'scheduled',
        completionStatus: 'pending',
      })
      expect(event.id).toBe(
        deriveSeasonFoundationCalendarEventId(season.id, event.kind),
      )
      expect('teamId' in event).toBe(false)
    }

    expect(schedule.gameDays.map(({ sequenceNumber }) => sequenceNumber)).toEqual(
      Array.from({ length: 28 }, (_, index) => index + 1),
    )
    expect(
      schedule.gameDays.map(({ scheduledDate }) => scheduledDate),
    ).toEqual(
      Array.from({ length: 28 }, (_, index) =>
        addDays(START_DATE, index * CALENDAR_DAY_SPACING),
      ),
    )
    expect(
      schedule.gameDays.every(({ seasonId }) => seasonId === season.id),
    ).toBe(true)
    expect(schedule.games.every(({ seasonId }) => seasonId === season.id)).toBe(
      true,
    )

    expect(validate(foundation)).toEqual([])
    expect(() =>
      assertValidSeasonFoundation({ ...input(), foundation }),
    ).not.toThrow()
  })

  it('is deeply deterministic for identical league and creation inputs', () => {
    expect(createSeasonFoundation(input())).toEqual(
      createSeasonFoundation(input()),
    )
  })

  it('keeps semantic IDs, dates, and the opponent matrix stable when only the schedule seed changes', () => {
    const first = createSeasonFoundation(input())
    const second = createSeasonFoundation(
      input({ scheduleSeed: 'season-foundation-schedule-two' }),
    )
    const { scheduleId: firstScheduleId, ...firstStableSeason } = first.season
    const { scheduleId: secondScheduleId, ...secondStableSeason } = second.season

    expect(second.season.id).toBe(first.season.id)
    expect(secondStableSeason).toEqual(firstStableSeason)
    expect(second.calendar).toEqual(first.calendar)
    expect(second.teamSeasons).toEqual(first.teamSeasons)
    expect(second.schedule.gameDays.map(({ scheduledDate }) => scheduledDate)).toEqual(
      first.schedule.gameDays.map(({ scheduledDate }) => scheduledDate),
    )
    expect(second.schedule.opponentRequirements).toEqual(
      first.schedule.opponentRequirements,
    )

    expect(second.schedule.id).not.toBe(first.schedule.id)
    expect(secondScheduleId).not.toBe(firstScheduleId)
    expect(second.schedule.games.map(({ id }) => id)).not.toEqual(
      first.schedule.games.map(({ id }) => id),
    )
    expect(second.schedule).not.toEqual(first.schedule)
  })

  it('derives semantic identities independently from schedule dates', () => {
    const laterStart = parseLocalDate('2026-11-02')
    const first = createSeasonFoundation(input())
    const later = createSeasonFoundation(
      input({ regularSeasonStartDate: laterStart }),
    )

    expect(
      deriveSeasonFoundationSeasonId(league.id, STARTING_YEAR),
    ).toBe(first.season.id)
    expect(later.season.id).toBe(first.season.id)
    expect(later.calendar.id).toBe(first.calendar.id)
    expect(later.teamSeasons.map(({ id }) => id)).toEqual(
      first.teamSeasons.map(({ id }) => id),
    )
    expect(later.calendar.events.map(({ id }) => id)).toEqual(
      first.calendar.events.map(({ id }) => id),
    )
    expect(later.schedule.id).toBe(first.schedule.id)
    expect(later.schedule.games.map(({ id }) => id)).toEqual(
      first.schedule.games.map(({ id }) => id),
    )
    expect(later.schedule.games.map(({ originalScheduledDate }) => originalScheduledDate)).not.toEqual(
      first.schedule.games.map(({ originalScheduledDate }) => originalScheduledDate),
    )
  })

  it('rejects malformed leagues, wrong team counts, duplicate teams, and foreign player ownership', () => {
    const malformedIdLeague: League = {
      ...league,
      id: 'League Invalid' as League['id'],
    }
    const wrongTeamCountLeague: League = {
      ...league,
      teams: league.teams.slice(0, 7),
    }
    const duplicateTeamLeague: League = {
      ...league,
      teams: [
        league.teams[0],
        { ...league.teams[1], id: league.teams[0].id },
        ...league.teams.slice(2),
      ],
    }
    const foreignOwnershipLeague: League = {
      ...league,
      players: [
        {
          ...league.players[0],
          teamId: parseTeamId('team_foreign_owner'),
        },
        ...league.players.slice(1),
      ],
    }

    for (const invalidLeague of [
      malformedIdLeague,
      wrongTeamCountLeague,
      duplicateTeamLeague,
      foreignOwnershipLeague,
    ]) {
      expect(() =>
        createSeasonFoundation(input({ league: invalidLeague })),
      ).toThrow(InvalidLeagueError)
    }
  })

  it.each([-1, 2026.5, 9999, Number.NaN])(
    'rejects invalid starting year %s',
    (startingYear) => {
      expect(() =>
        createSeasonFoundation(input({ startingYear })),
      ).toThrow()
    },
  )

  it('rejects malformed dates and dates outside the supplied starting year', () => {
    expect(() =>
      createSeasonFoundation(
        input({ regularSeasonStartDate: '2026-02-30' as LocalDate }),
      ),
    ).toThrow(/valid calendar date/i)
    expect(() =>
      createSeasonFoundation(
        input({ regularSeasonStartDate: parseLocalDate('2027-01-02') }),
      ),
    ).toThrow(/starting year/i)
  })

  it.each([0, -1, 1.5, Number.NaN, Number.POSITIVE_INFINITY])(
    'rejects invalid calendar-day spacing %s',
    (calendarDaySpacing) => {
      expect(() =>
        createSeasonFoundation(input({ calendarDaySpacing })),
      ).toThrow(/positive safe integer/i)
    },
  )

  it.each([' schedule-seed', 'schedule-seed ', 'e\u0301', '   '])(
    'rejects non-canonical schedule seed %j',
    (scheduleSeed) => {
      expect(() =>
        createSeasonFoundation(input({ scheduleSeed })),
      ).toThrow()
    },
  )

  it('rejects generated calendar dates that overflow the LocalDate range', () => {
    expect(() =>
      createSeasonFoundation(
        input({
          startingYear: 9998,
          regularSeasonStartDate: parseLocalDate('9998-12-31'),
          calendarDaySpacing: 366,
        }),
      ),
    ).toThrow(/supported year range/i)
  })

  it('rejects spacing that places the conclusion after the season ending year', () => {
    let caught: unknown
    try {
      createSeasonFoundation(
        input({
          regularSeasonStartDate: parseLocalDate('2026-12-31'),
          calendarDaySpacing: 100,
        }),
      )
    } catch (error) {
      caught = error
    }

    expect(caught).toBeInstanceOf(InvalidSeasonFoundationError)
    if (!(caught instanceof InvalidSeasonFoundationError)) {
      throw new Error('Expected season-foundation validation to fail')
    }
    expect(caught.issues).toContainEqual(
      expect.objectContaining({
        code: 'foundation.schedule.conclusion_outside_season',
      }),
    )
  })

  it('does not mutate or freeze the supplied league or any nested league data', () => {
    const leagueUnderTest = generateLeague('non-mutating-foundation-league')
    const teamsReference = leagueUnderTest.teams
    const playersReference = leagueUnderTest.players
    const firstTeamReference = leagueUnderTest.teams[0]
    const firstPlayerReference = leagueUnderTest.players[0]
    const ratingsReference = firstPlayerReference.ratings
    const before = JSON.parse(JSON.stringify(leagueUnderTest)) as unknown

    createSeasonFoundation(input({ league: leagueUnderTest }))

    expect(leagueUnderTest).toEqual(before)
    expect(leagueUnderTest.teams).toBe(teamsReference)
    expect(leagueUnderTest.players).toBe(playersReference)
    expect(leagueUnderTest.teams[0]).toBe(firstTeamReference)
    expect(leagueUnderTest.players[0]).toBe(firstPlayerReference)
    expect(leagueUnderTest.players[0].ratings).toBe(ratingsReference)
    expect(Object.isFrozen(leagueUnderTest)).toBe(false)
    expect(Object.isFrozen(leagueUnderTest.teams)).toBe(false)
    expect(Object.isFrozen(leagueUnderTest.players)).toBe(false)
    expect(Object.isFrozen(firstTeamReference)).toBe(false)
    expect(Object.isFrozen(firstPlayerReference)).toBe(false)
    expect(Object.isFrozen(ratingsReference)).toBe(false)
  })

  it('deeply freezes every newly created aggregate collection and entity', () => {
    const foundation = createSeasonFoundation(input())

    expect(Object.isFrozen(foundation)).toBe(true)
    expect(Object.isFrozen(foundation.season)).toBe(true)
    expect(Object.isFrozen(foundation.calendar)).toBe(true)
    expect(Object.isFrozen(foundation.calendar.events)).toBe(true)
    expect(foundation.calendar.events.every(Object.isFrozen)).toBe(true)
    expect(Object.isFrozen(foundation.teamSeasons)).toBe(true)
    expect(foundation.teamSeasons.every(Object.isFrozen)).toBe(true)
    expect(Object.isFrozen(foundation.schedule)).toBe(true)
    expect(Object.isFrozen(foundation.schedule.opponentRequirements)).toBe(true)
    expect(
      foundation.schedule.opponentRequirements.every(Object.isFrozen),
    ).toBe(true)
    expect(Object.isFrozen(foundation.schedule.gameDays)).toBe(true)
    expect(foundation.schedule.gameDays.every(Object.isFrozen)).toBe(true)
    expect(
      foundation.schedule.gameDays.every(({ gameIds }) =>
        Object.isFrozen(gameIds),
      ),
    ).toBe(true)
    expect(Object.isFrozen(foundation.schedule.games)).toBe(true)
    expect(foundation.schedule.games.every(Object.isFrozen)).toBe(true)
  })

  it('contains the canonical schedule produced directly by the generator', () => {
    const foundation = createSeasonFoundation(input())
    const direct = generateRegularSeasonSchedule({
      leagueId: league.id,
      seasonId: foundation.season.id,
      teams: league.teams,
      scheduleSeed: SCHEDULE_SEED,
      regularSeasonStartDate: START_DATE,
      calendarDaySpacing: CALENDAR_DAY_SPACING,
      ruleSet: MILESTONE_1_REGULAR_SEASON_RULE_SET,
    })

    expect(foundation.schedule).toEqual(direct)
  })

  it('publishes team seasons in stable TeamId order without mutating league order', () => {
    const reorderedLeague: League = {
      ...league,
      teams: [...league.teams].reverse(),
    }
    const suppliedOrder = reorderedLeague.teams.map(({ id }) => id)
    const expectedOrder = [...suppliedOrder].sort()
    const foundation = createSeasonFoundation(
      input({ league: reorderedLeague }),
    )

    expect(foundation.teamSeasons.map(({ teamId }) => teamId)).toEqual(
      expectedOrder,
    )
    expect(reorderedLeague.teams.map(({ id }) => id)).toEqual(suppliedOrder)
  })
})

describe('validateSeasonFoundation aggregate contracts', () => {
  it('reports missing, duplicate, foreign, and reordered team-season records', () => {
    const foundation = createSeasonFoundation(input())
    const missing: SeasonFoundation = {
      ...foundation,
      teamSeasons: foundation.teamSeasons.slice(0, 7),
    }
    const duplicate: SeasonFoundation = {
      ...foundation,
      teamSeasons: [
        ...foundation.teamSeasons.slice(0, 7),
        foundation.teamSeasons[0],
      ],
    }
    const foreign: SeasonFoundation = {
      ...foundation,
      teamSeasons: [
        ...foundation.teamSeasons.slice(0, 7),
        {
          ...foundation.teamSeasons[7],
          teamId: parseTeamId('team_foreign_foundation'),
        },
      ],
    }
    const reordered: SeasonFoundation = {
      ...foundation,
      teamSeasons: [...foundation.teamSeasons].reverse(),
    }

    expect(issueCodes(missing).has('foundation.team_season.count_mismatch')).toBe(
      true,
    )
    expect(issueCodes(missing).has('foundation.team_season.team_id_missing')).toBe(
      true,
    )
    expect(issueCodes(duplicate).has('foundation.team_season.team_id_duplicate')).toBe(
      true,
    )
    expect(issueCodes(duplicate).has('foundation.team_season.team_id_missing')).toBe(
      true,
    )
    expect(issueCodes(foreign).has('foundation.team_season.team_id_unknown')).toBe(
      true,
    )
    expect(issueCodes(reordered).has('foundation.team_season.order_mismatch')).toBe(
      true,
    )
    expect(() =>
      assertValidSeasonFoundation({ ...input(), foundation: missing }),
    ).toThrow(InvalidSeasonFoundationError)
  })

  it('reports foreign league references on both season and schedule', () => {
    const foundation = createSeasonFoundation(input())
    const foreignLeagueId = parseLeagueId('league_foreign_foundation')
    const invalid: SeasonFoundation = {
      ...foundation,
      season: { ...foundation.season, leagueId: foreignLeagueId },
      schedule: { ...foundation.schedule, leagueId: foreignLeagueId },
    }
    const codes = issueCodes(invalid)

    expect(codes.has('foundation.season.league_id_mismatch')).toBe(true)
    expect(codes.has('foundation.schedule.league_id_mismatch')).toBe(true)
    expect(codes.has('wrong_league')).toBe(true)
  })

  it('reports mismatched schedule references and schedule identity', () => {
    const foundation = createSeasonFoundation(input())
    const foreignScheduleId = parseScheduleId('schedule_foreign_foundation')
    const mismatchedReference: SeasonFoundation = {
      ...foundation,
      season: { ...foundation.season, scheduleId: foreignScheduleId },
    }
    const mismatchedIdentity: SeasonFoundation = {
      ...foundation,
      schedule: { ...foundation.schedule, id: foreignScheduleId },
    }

    expect(
      issueCodes(mismatchedReference).has(
        'foundation.season.schedule_id_mismatch',
      ),
    ).toBe(true)
    expect(
      issueCodes(mismatchedIdentity).has('foundation.schedule.id_mismatch'),
    ).toBe(true)
    expect(
      issueCodes(mismatchedIdentity).has(
        'foundation.season.schedule_id_mismatch',
      ),
    ).toBe(true)
  })

  it('reports mismatched calendar, team-season, and calendar-event identities', () => {
    const foundation = createSeasonFoundation(input())
    const invalid: SeasonFoundation = {
      ...foundation,
      calendar: {
        ...foundation.calendar,
        id: parseSeasonCalendarId('season_calendar_foreign_foundation'),
        events: [
          {
            ...foundation.calendar.events[0],
            id: parseCalendarEventId('calendar_event_foreign_foundation'),
          },
          foundation.calendar.events[1],
        ],
      },
      teamSeasons: [
        {
          ...foundation.teamSeasons[0],
          id: parseTeamSeasonId('team_season_foreign_foundation'),
        },
        ...foundation.teamSeasons.slice(1),
      ],
    }
    const codes = issueCodes(invalid)

    expect(codes.has('foundation.calendar.id_mismatch')).toBe(true)
    expect(codes.has('foundation.calendar_event.id_mismatch')).toBe(true)
    expect(codes.has('foundation.team_season.id_mismatch')).toBe(true)
  })

  it('reports wrong season references across schedule, calendar, child records, and events', () => {
    const foundation = createSeasonFoundation(input())
    const foreignSeasonId = parseSeasonId('season_foreign_foundation')
    const wrongSeasonIdentity: SeasonFoundation = {
      ...foundation,
      season: { ...foundation.season, id: foreignSeasonId },
    }
    const invalid: SeasonFoundation = {
      ...foundation,
      schedule: {
        ...foundation.schedule,
        seasonId: foreignSeasonId,
        gameDays: [
          { ...foundation.schedule.gameDays[0], seasonId: foreignSeasonId },
          ...foundation.schedule.gameDays.slice(1),
        ],
        games: [
          { ...foundation.schedule.games[0], seasonId: foreignSeasonId },
          ...foundation.schedule.games.slice(1),
        ],
      },
      calendar: {
        ...foundation.calendar,
        seasonId: foreignSeasonId,
        events: [
          { ...foundation.calendar.events[0], seasonId: foreignSeasonId },
          ...foundation.calendar.events.slice(1),
        ],
      },
      teamSeasons: [
        { ...foundation.teamSeasons[0], seasonId: foreignSeasonId },
        ...foundation.teamSeasons.slice(1),
      ],
    }
    const codes = issueCodes(invalid)

    expect(
      issueCodes(wrongSeasonIdentity).has('foundation.season.id_mismatch'),
    ).toBe(true)
    expect(codes.has('foundation.season_reference.mismatch')).toBe(true)
    expect(codes.has('foundation.game_day.season_id_mismatch')).toBe(true)
    expect(codes.has('foundation.game.season_id_mismatch')).toBe(true)
    expect(codes.has('foundation.calendar_event.season_id_mismatch')).toBe(true)
    expect(codes.has('foundation.team_season.season_id_mismatch')).toBe(true)
    expect(codes.has('wrong_season')).toBe(true)
  })

  it('reports a malformed season identity without throwing from aggregate validation', () => {
    const foundation = createSeasonFoundation(input())
    const invalid: SeasonFoundation = {
      ...foundation,
      season: {
        ...foundation.season,
        id: 'Season Invalid' as SeasonFoundation['season']['id'],
      },
    }

    expect(() => validate(invalid)).not.toThrow()
    const codes = issueCodes(invalid)
    expect(codes.has('season.id.invalid')).toBe(true)
    expect(codes.has('foundation.season.id_mismatch')).toBe(true)
    expect(codes.has('foundation.calendar.identity_input.invalid')).toBe(true)
  })

  it.each([
    ['null team season', (foundation: SeasonFoundation) => ({
      ...foundation,
      teamSeasons: [null] as never,
    })],
    ['null calendar event', (foundation: SeasonFoundation) => ({
      ...foundation,
      calendar: { ...foundation.calendar, events: [null] as never },
    })],
    ['missing schedule games', (foundation: SeasonFoundation) => ({
      ...foundation,
      schedule: { ...foundation.schedule, games: undefined as never },
    })],
  ] as const)(
    'reports malformed nested runtime data without throwing: %s',
    (_label, mutate) => {
      const malformed = mutate(createSeasonFoundation(input()))
      const validationInput = {
        ...input(),
        foundation: malformed as SeasonFoundation,
      }

      expect(() => validateSeasonFoundation(validationInput)).not.toThrow()
      expect(validateSeasonFoundation(validationInput)).toContainEqual(
        expect.objectContaining({ code: 'foundation.structure.invalid' }),
      )
    },
  )

  it('reports a self-matchup without stopping before other schedule diagnostics', () => {
    const foundation = createSeasonFoundation(input())
    const firstGame = foundation.schedule.games[0]
    const invalid = replaceSchedule(foundation, {
      ...foundation.schedule,
      games: [
        { ...firstGame, awayTeamId: firstGame.homeTeamId },
        ...foundation.schedule.games.slice(1),
      ],
    })
    const codes = issueCodes(invalid)

    expect(codes.has('self_matchup')).toBe(true)
    expect(codes.has('duplicate_team_appearance')).toBe(true)
    expect(codes.has('missing_team_appearance')).toBe(true)
    expect(validate(invalid).length).toBeGreaterThan(3)
  })

  it('rejects a structurally valid but unsupported future calendar event', () => {
    const foundation = createSeasonFoundation(input())
    const futureEvent = createCalendarEvent({
      id: parseCalendarEventId('calendar_event_future_draft'),
      version: CALENDAR_EVENT_VERSION,
      seasonId: foundation.season.id,
      kind: 'draft_event',
      scope: 'league',
      title: 'Draft',
      originalScheduledDate: null,
      scheduledDate: null,
      actualDate: null,
      dateStatus: 'tba',
      completionStatus: 'pending',
    })
    const invalid: SeasonFoundation = {
      ...foundation,
      calendar: {
        ...foundation.calendar,
        events: [...foundation.calendar.events, futureEvent],
      },
    }
    const codes = issueCodes(invalid)

    expect(codes.has('foundation.calendar.event_kind.unsupported')).toBe(true)
    expect(codes.has('foundation.calendar.event_count_mismatch')).toBe(true)
  })

  it('reports changed configuration rather than accepting a valid package under different inputs', () => {
    const foundation = createSeasonFoundation(input())
    const codes = issueCodes(foundation, {
      scheduleSeed: 'another-valid-schedule-seed',
    })

    expect(codes.has('foundation.schedule.id_mismatch')).toBe(true)
    expect(codes.has('foundation.schedule.configuration_mismatch')).toBe(true)
  })

  it('rejects a rule-valid schedule that is not the exact initial generator output', () => {
    const foundation = createSeasonFoundation(input())
    const invalid = replaceSchedule(foundation, {
      ...foundation.schedule,
      publicationStatus: 'published',
    })
    const codes = issueCodes(invalid)

    expect(codes.has('foundation.schedule.not_canonical')).toBe(true)
  })
})
