import {
  isLeagueId,
  isSeasonId,
  isTeamId,
  parseCalendarEventId,
  parseSeasonCalendarId,
  parseSeasonId,
  parseTeamSeasonId,
} from './ids'
import type {
  CalendarEventId,
  LeagueId,
  SeasonCalendarId,
  SeasonId,
  TeamId,
  TeamSeasonId,
} from './ids'
import {
  formatSeasonLabel,
  getCalendarYear,
  parseLocalDate,
} from './localDate'
import type { LocalDate } from './localDate'
import type { LeagueSchedule } from './schedule'
import type { Season } from './season'
import type { CalendarEventKind, SeasonCalendar } from './seasonCalendar'
import type { TeamSeason } from './teamSeason'
import {
  deriveSeed,
  fingerprintDerivedSeed,
  normalizeSeed,
} from '../random/seed'

export const SEASON_FOUNDATION_IDENTITY_VERSION = 1 as const

const IDENTITY_NAMESPACE =
  `season_foundation_identity/v${SEASON_FOUNDATION_IDENTITY_VERSION}` as const
const ID_FINGERPRINT_LENGTH = 24

export const FOUNDATION_CALENDAR_EVENT_KINDS = [
  'regular_season_opening',
  'regular_season_conclusion',
] as const satisfies readonly CalendarEventKind[]

export type FoundationCalendarEventKind =
  (typeof FOUNDATION_CALENDAR_EVENT_KINDS)[number]

export interface SeasonFoundationConfigurationInput {
  readonly startingYear: number
  readonly regularSeasonStartDate: LocalDate
  readonly calendarDaySpacing: number
  readonly scheduleSeed: string
}

export interface SeasonFoundationConfiguration {
  readonly startingYear: number
  readonly regularSeasonStartDate: LocalDate
  readonly calendarDaySpacing: number
  readonly scheduleSeed: string
}

export interface SeasonFoundation {
  readonly season: Season
  readonly calendar: SeasonCalendar
  readonly teamSeasons: readonly TeamSeason[]
  readonly schedule: LeagueSchedule
}

export function deriveSeasonFoundationSeasonId(
  leagueId: LeagueId,
  startingYear: number,
): SeasonId {
  if (!isLeagueId(leagueId)) {
    throw new TypeError('Season identity requires a valid LeagueId')
  }
  const endingYear = startingYear + 1
  formatSeasonLabel(startingYear, endingYear)
  return parseSeasonId(
    `season_${deriveIdentityFingerprint(
      leagueId,
      `${IDENTITY_NAMESPACE}/season/starting_year_${startingYear}`,
    )}`,
  )
}

/** Calendar identity deliberately excludes schedule seed and event dates. */
export function deriveSeasonFoundationCalendarId(
  seasonId: SeasonId,
): SeasonCalendarId {
  if (!isSeasonId(seasonId)) {
    throw new TypeError('Season calendar identity requires a valid SeasonId')
  }
  return parseSeasonCalendarId(
    `season_calendar_${deriveIdentityFingerprint(
      seasonId,
      `${IDENTITY_NAMESPACE}/calendar`,
    )}`,
  )
}

/** Team-season identity deliberately excludes schedule seed and lifecycle state. */
export function deriveSeasonFoundationTeamSeasonId(
  seasonId: SeasonId,
  teamId: TeamId,
): TeamSeasonId {
  if (!isSeasonId(seasonId) || !isTeamId(teamId)) {
    throw new TypeError(
      'Team-season identity requires valid SeasonId and TeamId values',
    )
  }
  return parseTeamSeasonId(
    `team_season_${deriveIdentityFingerprint(
      seasonId,
      `${IDENTITY_NAMESPACE}/team_season/${teamId.length}:${teamId}`,
    )}`,
  )
}

/** Event identity uses semantic kind, never title, array position, or date. */
export function deriveSeasonFoundationCalendarEventId(
  seasonId: SeasonId,
  kind: FoundationCalendarEventKind,
): CalendarEventId {
  if (!isSeasonId(seasonId)) {
    throw new TypeError('Calendar-event identity requires a valid SeasonId')
  }
  if (!FOUNDATION_CALENDAR_EVENT_KINDS.includes(kind)) {
    throw new TypeError('Calendar-event kind is not part of this foundation')
  }
  return parseCalendarEventId(
    `calendar_event_${deriveIdentityFingerprint(
      seasonId,
      `${IDENTITY_NAMESPACE}/calendar_event/${kind}`,
    )}`,
  )
}

export function parseSeasonFoundationConfiguration(
  input: SeasonFoundationConfigurationInput,
): SeasonFoundationConfiguration {
  const endingYear = input.startingYear + 1
  formatSeasonLabel(input.startingYear, endingYear)
  const regularSeasonStartDate = parseLocalDate(
    input.regularSeasonStartDate,
  )
  if (getCalendarYear(regularSeasonStartDate) !== input.startingYear) {
    throw new RangeError(
      'Regular-season start date must fall in the supplied starting year',
    )
  }
  if (
    !Number.isSafeInteger(input.calendarDaySpacing) ||
    input.calendarDaySpacing <= 0
  ) {
    throw new RangeError(
      'Calendar-day spacing must be a positive safe integer',
    )
  }

  const scheduleSeed = normalizeSeed(input.scheduleSeed)
  if (scheduleSeed !== input.scheduleSeed) {
    throw new RangeError(
      'Schedule seed must already be canonical, trimmed, and NFC-normalized',
    )
  }

  return {
    startingYear: input.startingYear,
    regularSeasonStartDate,
    calendarDaySpacing: input.calendarDaySpacing,
    scheduleSeed,
  }
}

function deriveIdentityFingerprint(root: string, label: string): string {
  return fingerprintDerivedSeed(
    deriveSeed(root, label),
    ID_FINGERPRINT_LENGTH,
  )
}
