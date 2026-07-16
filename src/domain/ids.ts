declare const stableIdBrand: unique symbol

type StableId<Kind extends string> = string & {
  readonly [stableIdBrand]: Kind
}

export type LeagueId = StableId<'LeagueId'>
export type TeamId = StableId<'TeamId'>
export type PlayerId = StableId<'PlayerId'>
export type GameId = StableId<'GameId'>
export type SaveId = StableId<'SaveId'>
export type SeasonId = StableId<'SeasonId'>
export type ScheduleId = StableId<'ScheduleId'>
export type CalendarEventId = StableId<'CalendarEventId'>
export type GameDayId = StableId<'GameDayId'>
export type ScheduleRuleSetId = StableId<'ScheduleRuleSetId'>
export type SeasonCalendarId = StableId<'SeasonCalendarId'>
export type TeamSeasonId = StableId<'TeamSeasonId'>

const INVALID_ID_CHARACTER = /[^a-z0-9_]/

export function isLeagueId(value: unknown): value is LeagueId {
  return isStableId(value)
}

export function isTeamId(value: unknown): value is TeamId {
  return isStableId(value)
}

export function isPlayerId(value: unknown): value is PlayerId {
  return isStableId(value)
}

export function isGameId(value: unknown): value is GameId {
  return isStableId(value)
}

export function isSaveId(value: unknown): value is SaveId {
  return isStableId(value)
}

export function isSeasonId(value: unknown): value is SeasonId {
  return isStableId(value)
}

export function isScheduleId(value: unknown): value is ScheduleId {
  return isStableId(value)
}

export function isCalendarEventId(value: unknown): value is CalendarEventId {
  return isStableId(value)
}

export function isGameDayId(value: unknown): value is GameDayId {
  return isStableId(value)
}

export function isScheduleRuleSetId(value: unknown): value is ScheduleRuleSetId {
  return isStableId(value)
}

export function isSeasonCalendarId(value: unknown): value is SeasonCalendarId {
  return isStableId(value)
}

export function isTeamSeasonId(value: unknown): value is TeamSeasonId {
  return isStableId(value)
}

export function parseLeagueId(value: unknown): LeagueId {
  return parseStableId(value, 'LeagueId')
}

export function parseTeamId(value: unknown): TeamId {
  return parseStableId(value, 'TeamId')
}

export function parsePlayerId(value: unknown): PlayerId {
  return parseStableId(value, 'PlayerId')
}

export function parseGameId(value: unknown): GameId {
  return parseStableId(value, 'GameId')
}

export function parseSaveId(value: unknown): SaveId {
  return parseStableId(value, 'SaveId')
}

export function parseSeasonId(value: unknown): SeasonId {
  return parseStableId(value, 'SeasonId')
}

export function parseScheduleId(value: unknown): ScheduleId {
  return parseStableId(value, 'ScheduleId')
}

export function parseCalendarEventId(value: unknown): CalendarEventId {
  return parseStableId(value, 'CalendarEventId')
}

export function parseGameDayId(value: unknown): GameDayId {
  return parseStableId(value, 'GameDayId')
}

export function parseScheduleRuleSetId(value: unknown): ScheduleRuleSetId {
  return parseStableId(value, 'ScheduleRuleSetId')
}

export function parseSeasonCalendarId(value: unknown): SeasonCalendarId {
  return parseStableId(value, 'SeasonCalendarId')
}

export function parseTeamSeasonId(value: unknown): TeamSeasonId {
  return parseStableId(value, 'TeamSeasonId')
}

function isStableId(value: unknown): value is string {
  return (
    typeof value === 'string' &&
    value.length > 0 &&
    !INVALID_ID_CHARACTER.test(value)
  )
}

function parseStableId<Id extends string>(value: unknown, kind: string): Id {
  if (!isStableId(value)) {
    throw new TypeError(
      `${kind} must be a non-empty string containing only lowercase ASCII letters, digits, and underscores`,
    )
  }

  return value as Id
}
