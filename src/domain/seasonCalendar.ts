import {
  isCalendarEventId,
  isSeasonId,
  isTeamId,
  parseCalendarEventId,
  parseSeasonId,
  parseTeamId,
} from './ids'
import type { CalendarEventId, SeasonId, TeamId } from './ids'
import { isLocalDate, parseLocalDate } from './localDate'
import type { LocalDate } from './localDate'

export const SEASON_CALENDAR_VERSION = 1 as const
export const CALENDAR_EVENT_VERSION = 1 as const

export const CALENDAR_EVENT_KINDS = [
  'schedule_release',
  'training_camp_start',
  'preseason_start',
  'preseason_end',
  'regular_season_opening',
  'regular_season_conclusion',
  'trade_deadline',
  'all_star_break',
  'cup_event',
  'play_in_event',
  'playoffs_start',
  'finals_start',
  'latest_possible_finals_end',
  'actual_finals_end',
  'team_elimination',
  'team_offseason_start',
  'league_offseason_start',
  'draft_event',
  'free_agency_event',
] as const
export type CalendarEventKind = (typeof CALENDAR_EVENT_KINDS)[number]

export const CALENDAR_EVENT_SCOPES = ['league', 'team'] as const
export type CalendarEventScope = (typeof CALENDAR_EVENT_SCOPES)[number]

export const CALENDAR_DATE_STATUSES = [
  'tba',
  'estimated',
  'announced',
  'scheduled',
  'completed',
  'postponed',
  'cancelled',
] as const
export type CalendarDateStatus = (typeof CALENDAR_DATE_STATUSES)[number]

export const CALENDAR_COMPLETION_STATUSES = [
  'pending',
  'completed',
  'cancelled',
] as const
export type CalendarCompletionStatus =
  (typeof CALENDAR_COMPLETION_STATUSES)[number]

interface CalendarEventBase {
  readonly id: CalendarEventId
  readonly version: typeof CALENDAR_EVENT_VERSION
  readonly seasonId: SeasonId
  readonly kind: CalendarEventKind
  readonly title: string
  /** The first announced date; it remains unchanged after postponement. */
  readonly originalScheduledDate: LocalDate | null
  /** The currently scheduled date, which may change after postponement. */
  readonly scheduledDate: LocalDate | null
  /** The date the event actually occurred; it never replaces either schedule field. */
  readonly actualDate: LocalDate | null
  readonly dateStatus: CalendarDateStatus
  readonly completionStatus: CalendarCompletionStatus
}

export type CalendarEvent = CalendarEventBase &
  (
    | {
        readonly scope: 'league'
        readonly teamId?: never
      }
    | {
        readonly scope: 'team'
        readonly teamId: TeamId
      }
  )

export interface SeasonCalendar {
  readonly version: typeof SEASON_CALENDAR_VERSION
  readonly seasonId: SeasonId
  readonly events: readonly CalendarEvent[]
}

export interface CalendarValidationIssue {
  readonly code: string
  readonly path: string
  readonly message: string
}

export class InvalidCalendarEventError extends Error {
  readonly issues: readonly CalendarValidationIssue[]

  constructor(issues: readonly CalendarValidationIssue[]) {
    super(`Calendar event validation failed with ${issues.length} issue(s)`)
    this.name = 'InvalidCalendarEventError'
    this.issues = issues
  }
}

export class InvalidSeasonCalendarError extends Error {
  readonly issues: readonly CalendarValidationIssue[]

  constructor(issues: readonly CalendarValidationIssue[]) {
    super(`Season calendar validation failed with ${issues.length} issue(s)`)
    this.name = 'InvalidSeasonCalendarError'
    this.issues = issues
  }
}

export function isCalendarEventKind(value: unknown): value is CalendarEventKind {
  return CALENDAR_EVENT_KINDS.some((kind) => kind === value)
}

export function isCalendarEventScope(value: unknown): value is CalendarEventScope {
  return CALENDAR_EVENT_SCOPES.some((scope) => scope === value)
}

export function isCalendarDateStatus(value: unknown): value is CalendarDateStatus {
  return CALENDAR_DATE_STATUSES.some((status) => status === value)
}

export function isCalendarCompletionStatus(
  value: unknown,
): value is CalendarCompletionStatus {
  return CALENDAR_COMPLETION_STATUSES.some((status) => status === value)
}

export function createCalendarEvent(event: CalendarEvent): CalendarEvent {
  return parseCalendarEvent(event)
}

export function validateCalendarEvent(
  value: unknown,
): readonly CalendarValidationIssue[] {
  return validateCalendarEventAtPath(value, '$')
}

export function parseCalendarEvent(value: unknown): CalendarEvent {
  const issues = validateCalendarEvent(value)
  if (issues.length > 0) {
    throw new InvalidCalendarEventError(issues)
  }

  return freezeCalendarEvent(value as Record<string, unknown>)
}

export function createSeasonCalendar(calendar: SeasonCalendar): SeasonCalendar {
  return parseSeasonCalendar(calendar)
}

export function validateSeasonCalendar(
  value: unknown,
): readonly CalendarValidationIssue[] {
  const issues: CalendarValidationIssue[] = []
  if (!isRecord(value)) {
    addIssue(issues, 'calendar.invalid', '$', 'Season calendar must be an object')
    return issues
  }

  if (value.version !== SEASON_CALENDAR_VERSION) {
    addIssue(
      issues,
      'calendar.version.invalid',
      '$.version',
      `Calendar version must equal ${SEASON_CALENDAR_VERSION}`,
    )
  }
  if (!isSeasonId(value.seasonId)) {
    addIssue(
      issues,
      'calendar.season_id.invalid',
      '$.seasonId',
      'Calendar season ID is invalid',
    )
  }
  if (!Array.isArray(value.events)) {
    addIssue(issues, 'calendar.events.invalid', '$.events', 'Events must be an array')
    return issues
  }

  const eventIds = new Set<string>()
  for (let index = 0; index < value.events.length; index += 1) {
    const event = value.events[index]
    const path = `$.events[${index}]`
    issues.push(...validateCalendarEventAtPath(event, path))

    if (!isRecord(event)) {
      continue
    }
    if (isCalendarEventId(event.id)) {
      if (eventIds.has(event.id)) {
        addIssue(
          issues,
          'calendar.event_id.duplicate',
          `${path}.id`,
          'Calendar event IDs must be unique',
        )
      }
      eventIds.add(event.id)
    }
    if (
      isSeasonId(value.seasonId) &&
      isSeasonId(event.seasonId) &&
      event.seasonId !== value.seasonId
    ) {
      addIssue(
        issues,
        'calendar.event_season_id.mismatch',
        `${path}.seasonId`,
        'Calendar event must reference the calendar season',
      )
    }
  }

  return issues
}

export function parseSeasonCalendar(value: unknown): SeasonCalendar {
  const issues = validateSeasonCalendar(value)
  if (issues.length > 0) {
    throw new InvalidSeasonCalendarError(issues)
  }

  const source = value as Record<string, unknown>
  const events = (source.events as readonly unknown[]).map((event) =>
    parseCalendarEvent(event),
  )
  return Object.freeze({
    version: SEASON_CALENDAR_VERSION,
    seasonId: parseSeasonId(source.seasonId),
    events: Object.freeze(events),
  })
}

function validateCalendarEventAtPath(
  value: unknown,
  path: string,
): CalendarValidationIssue[] {
  const issues: CalendarValidationIssue[] = []
  if (!isRecord(value)) {
    addIssue(issues, 'calendar_event.invalid', path, 'Calendar event must be an object')
    return issues
  }

  if (!isCalendarEventId(value.id)) {
    addIssue(
      issues,
      'calendar_event.id.invalid',
      `${path}.id`,
      'Calendar event ID is invalid',
    )
  }
  if (value.version !== CALENDAR_EVENT_VERSION) {
    addIssue(
      issues,
      'calendar_event.version.invalid',
      `${path}.version`,
      `Calendar event version must equal ${CALENDAR_EVENT_VERSION}`,
    )
  }
  if (!isSeasonId(value.seasonId)) {
    addIssue(
      issues,
      'calendar_event.season_id.invalid',
      `${path}.seasonId`,
      'Calendar event season ID is invalid',
    )
  }
  if (!isCalendarEventKind(value.kind)) {
    addIssue(
      issues,
      'calendar_event.kind.invalid',
      `${path}.kind`,
      'Calendar event kind is invalid',
    )
  }
  if (!isCalendarEventScope(value.scope)) {
    addIssue(
      issues,
      'calendar_event.scope.invalid',
      `${path}.scope`,
      'Calendar event scope is invalid',
    )
  } else if (value.scope === 'team') {
    if (!isTeamId(value.teamId)) {
      addIssue(
        issues,
        'calendar_event.team_id.required',
        `${path}.teamId`,
        'A team-scoped event requires a valid TeamId',
      )
    }
  } else if (value.teamId !== undefined) {
    addIssue(
      issues,
      'calendar_event.team_id.forbidden',
      `${path}.teamId`,
      'A league-scoped event must not contain a TeamId',
    )
  }

  if (typeof value.title !== 'string' || value.title.trim().length === 0) {
    addIssue(
      issues,
      'calendar_event.title.invalid',
      `${path}.title`,
      'Calendar event title must not be empty',
    )
  }

  validateNullableDate(value.originalScheduledDate, `${path}.originalScheduledDate`, issues)
  validateNullableDate(value.scheduledDate, `${path}.scheduledDate`, issues)
  validateNullableDate(value.actualDate, `${path}.actualDate`, issues)

  if (!isCalendarDateStatus(value.dateStatus)) {
    addIssue(
      issues,
      'calendar_event.date_status.invalid',
      `${path}.dateStatus`,
      'Calendar event date status is invalid',
    )
  } else {
    validateDateState(value, path, issues)
  }

  if (!isCalendarCompletionStatus(value.completionStatus)) {
    addIssue(
      issues,
      'calendar_event.completion_status.invalid',
      `${path}.completionStatus`,
      'Calendar event completion status is invalid',
    )
  } else if (isCalendarDateStatus(value.dateStatus)) {
    validateCompletionState(value, path, issues)
  }

  return issues
}

function validateDateState(
  event: Record<string, unknown>,
  path: string,
  issues: CalendarValidationIssue[],
): void {
  const originalDate = event.originalScheduledDate
  const scheduledDate = event.scheduledDate
  const actualDate = event.actualDate

  if (event.dateStatus === 'tba') {
    if (originalDate !== null || scheduledDate !== null || actualDate !== null) {
      addIssue(
        issues,
        'calendar_event.tba_date.invalid',
        `${path}.dateStatus`,
        'A TBA event must not contain scheduled or actual dates',
      )
    }
    return
  }

  if (
    (event.dateStatus === 'estimated' ||
      event.dateStatus === 'announced' ||
      event.dateStatus === 'scheduled' ||
      event.dateStatus === 'completed') &&
    !isLocalDate(scheduledDate)
  ) {
    addIssue(
      issues,
      'calendar_event.scheduled_date.required',
      `${path}.scheduledDate`,
      'This date status requires a current scheduled date',
    )
  }

  if (event.dateStatus === 'completed' && !isLocalDate(actualDate)) {
    addIssue(
      issues,
      'calendar_event.actual_date.required',
      `${path}.actualDate`,
      'A completed event requires an actual date',
    )
  }

  if (event.dateStatus === 'postponed') {
    if (!isLocalDate(originalDate)) {
      addIssue(
        issues,
        'calendar_event.original_date.required',
        `${path}.originalScheduledDate`,
        'A postponed event must retain its original scheduled date',
      )
    }
    if (actualDate !== null) {
      addIssue(
        issues,
        'calendar_event.postponed_actual_date.invalid',
        `${path}.actualDate`,
        'A postponed event cannot have an actual date',
      )
    }
  }

  if (isLocalDate(scheduledDate) && !isLocalDate(originalDate)) {
    addIssue(
      issues,
      'calendar_event.original_date.required',
      `${path}.originalScheduledDate`,
      'A scheduled date requires a separately preserved original date',
    )
  }
  if (isLocalDate(actualDate) && event.dateStatus !== 'completed') {
    addIssue(
      issues,
      'calendar_event.actual_date_status.invalid',
      `${path}.actualDate`,
      'An actual date requires completed date status',
    )
  }
  if (
    isLocalDate(actualDate) &&
    (!isLocalDate(originalDate) || !isLocalDate(scheduledDate))
  ) {
    addIssue(
      issues,
      'calendar_event.actual_date.unanchored',
      `${path}.actualDate`,
      'An actual date cannot replace missing original or current scheduled dates',
    )
  }
}

function validateCompletionState(
  event: Record<string, unknown>,
  path: string,
  issues: CalendarValidationIssue[],
): void {
  if (
    event.completionStatus === 'completed' &&
    (event.dateStatus !== 'completed' || !isLocalDate(event.actualDate))
  ) {
    addIssue(
      issues,
      'calendar_event.completion.invalid',
      `${path}.completionStatus`,
      'Completed status requires completed date status and an actual date',
    )
  }
  if (event.dateStatus === 'completed' && event.completionStatus !== 'completed') {
    addIssue(
      issues,
      'calendar_event.completion.invalid',
      `${path}.completionStatus`,
      'Completed date status requires completed completion status',
    )
  }
  if (
    (event.completionStatus === 'cancelled') !==
    (event.dateStatus === 'cancelled')
  ) {
    addIssue(
      issues,
      'calendar_event.cancellation.invalid',
      `${path}.completionStatus`,
      'Cancelled date and completion statuses must agree',
    )
  }
  if (
    event.completionStatus === 'pending' &&
    (event.dateStatus === 'completed' || event.dateStatus === 'cancelled')
  ) {
    addIssue(
      issues,
      'calendar_event.pending.invalid',
      `${path}.completionStatus`,
      'A completed or cancelled event cannot remain pending',
    )
  }
}

function validateNullableDate(
  value: unknown,
  path: string,
  issues: CalendarValidationIssue[],
): void {
  if (value !== null && !isLocalDate(value)) {
    addIssue(
      issues,
      'calendar_event.date.invalid',
      path,
      'Calendar event date must be a valid LocalDate or null',
    )
  }
}

function freezeCalendarEvent(source: Record<string, unknown>): CalendarEvent {
  const base: CalendarEventBase = {
    id: parseCalendarEventId(source.id),
    version: CALENDAR_EVENT_VERSION,
    seasonId: parseSeasonId(source.seasonId),
    kind: source.kind as CalendarEventKind,
    title: source.title as string,
    originalScheduledDate:
      source.originalScheduledDate === null
        ? null
        : parseLocalDate(source.originalScheduledDate),
    scheduledDate:
      source.scheduledDate === null ? null : parseLocalDate(source.scheduledDate),
    actualDate:
      source.actualDate === null ? null : parseLocalDate(source.actualDate),
    dateStatus: source.dateStatus as CalendarDateStatus,
    completionStatus: source.completionStatus as CalendarCompletionStatus,
  }

  if (source.scope === 'team') {
    return Object.freeze({
      ...base,
      scope: 'team',
      teamId: parseTeamId(source.teamId),
    })
  }

  return Object.freeze({ ...base, scope: 'league' })
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function addIssue(
  issues: CalendarValidationIssue[],
  code: string,
  path: string,
  message: string,
): void {
  issues.push({ code, path, message })
}
