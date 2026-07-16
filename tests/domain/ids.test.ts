import { describe, expect, expectTypeOf, it } from 'vitest'
import {
  isCalendarEventId,
  isGameId,
  isGameDayId,
  isLeagueId,
  isPlayerId,
  isSaveId,
  isScheduleId,
  isScheduleRuleSetId,
  isSeasonCalendarId,
  isSeasonId,
  isTeamId,
  isTeamSeasonId,
  parseCalendarEventId,
  parseGameId,
  parseGameDayId,
  parseLeagueId,
  parsePlayerId,
  parseSaveId,
  parseScheduleId,
  parseScheduleRuleSetId,
  parseSeasonCalendarId,
  parseSeasonId,
  parseTeamId,
  parseTeamSeasonId,
} from '../../src/domain/ids'
import type {
  CalendarEventId,
  GameId,
  GameDayId,
  LeagueId,
  PlayerId,
  SaveId,
  ScheduleId,
  ScheduleRuleSetId,
  SeasonCalendarId,
  SeasonId,
  TeamId,
  TeamSeasonId,
} from '../../src/domain/ids'

interface RuntimeIdCase {
  readonly name: string
  readonly isValid: (value: unknown) => boolean
  readonly parse: (value: unknown) => string
}

const RUNTIME_ID_CASES: readonly RuntimeIdCase[] = [
  { name: 'LeagueId', isValid: isLeagueId, parse: parseLeagueId },
  { name: 'TeamId', isValid: isTeamId, parse: parseTeamId },
  { name: 'PlayerId', isValid: isPlayerId, parse: parsePlayerId },
  { name: 'GameId', isValid: isGameId, parse: parseGameId },
  { name: 'SaveId', isValid: isSaveId, parse: parseSaveId },
  { name: 'SeasonId', isValid: isSeasonId, parse: parseSeasonId },
  { name: 'ScheduleId', isValid: isScheduleId, parse: parseScheduleId },
  {
    name: 'CalendarEventId',
    isValid: isCalendarEventId,
    parse: parseCalendarEventId,
  },
  { name: 'GameDayId', isValid: isGameDayId, parse: parseGameDayId },
  {
    name: 'ScheduleRuleSetId',
    isValid: isScheduleRuleSetId,
    parse: parseScheduleRuleSetId,
  },
  {
    name: 'SeasonCalendarId',
    isValid: isSeasonCalendarId,
    parse: parseSeasonCalendarId,
  },
  {
    name: 'TeamSeasonId',
    isValid: isTeamSeasonId,
    parse: parseTeamSeasonId,
  },
]

const VALID_IDS = ['a', 'valid_id_123', '0', '_'] as const
const INVALID_IDS: readonly unknown[] = [
  '',
  'has space',
  ' leading',
  'trailing ',
  'Uppercase',
  'has-hyphen',
  'has.period',
  'nonascii_é',
  'newline\n',
  42,
  null,
  undefined,
  {},
]

describe.each(RUNTIME_ID_CASES)('$name runtime validation', ({ isValid, parse }) => {
  it.each(VALID_IDS)('accepts %s without changing it', (value) => {
    expect(isValid(value)).toBe(true)
    expect(parse(value)).toBe(value)
  })

  it.each(INVALID_IDS)('rejects invalid input %#', (value) => {
    expect(isValid(value)).toBe(false)
    expect(() => parse(value)).toThrow(TypeError)
  })
})

it('keeps stable entity ID types distinct', () => {
  expectTypeOf<LeagueId>().not.toEqualTypeOf<TeamId>()
  expectTypeOf<TeamId>().not.toEqualTypeOf<PlayerId>()
  expectTypeOf<PlayerId>().not.toEqualTypeOf<GameId>()
  expectTypeOf<GameId>().not.toEqualTypeOf<SaveId>()
  expectTypeOf<SaveId>().not.toEqualTypeOf<SeasonId>()
  expectTypeOf<SeasonId>().not.toEqualTypeOf<ScheduleId>()
  expectTypeOf<ScheduleId>().not.toEqualTypeOf<CalendarEventId>()
  expectTypeOf<CalendarEventId>().not.toEqualTypeOf<GameDayId>()
  expectTypeOf<GameDayId>().not.toEqualTypeOf<ScheduleRuleSetId>()
  expectTypeOf<ScheduleRuleSetId>().not.toEqualTypeOf<SeasonCalendarId>()
  expectTypeOf<SeasonCalendarId>().not.toEqualTypeOf<TeamSeasonId>()
})
