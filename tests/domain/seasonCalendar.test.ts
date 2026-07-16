import { describe, expect, it } from 'vitest'
import {
  CALENDAR_EVENT_KINDS,
  InvalidCalendarEventError,
  InvalidSeasonCalendarError,
  parseCalendarEvent,
  parseSeasonCalendar,
  validateCalendarEvent,
  validateSeasonCalendar,
} from '../../src/domain/seasonCalendar'

const BASE_EVENT = {
  id: 'calendar_event_opening',
  version: 1,
  seasonId: 'season_stone_01',
  kind: 'regular_season_opening',
  scope: 'league',
  title: 'Regular-season opening',
  originalScheduledDate: '2026-10-20',
  scheduledDate: '2026-10-20',
  actualDate: null,
  dateStatus: 'scheduled',
  completionStatus: 'pending',
} as const

describe('CalendarEvent', () => {
  it('supports every required event category', () => {
    expect(CALENDAR_EVENT_KINDS).toEqual(
      expect.arrayContaining([
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
      ]),
    )
  })

  it('parses and freezes a scheduled league-wide event', () => {
    const event = parseCalendarEvent(BASE_EVENT)

    expect(event).toEqual(BASE_EVENT)
    expect(Object.isFrozen(event)).toBe(true)
  })

  it('rejects unsupported event versions instead of assuming compatibility', () => {
    expect(validateCalendarEvent({ ...BASE_EVENT, version: 2 })).toContainEqual(
      expect.objectContaining({ code: 'calendar_event.version.invalid' }),
    )
  })

  it('allows an explicitly TBA event without invented dates', () => {
    const event = parseCalendarEvent({
      ...BASE_EVENT,
      id: 'calendar_event_draft',
      kind: 'draft_event',
      title: 'Draft',
      originalScheduledDate: null,
      scheduledDate: null,
      actualDate: null,
      dateStatus: 'tba',
    })

    expect(event.dateStatus).toBe('tba')
    expect(event.scheduledDate).toBeNull()
  })

  it('requires a scheduled date for scheduled events', () => {
    const issues = validateCalendarEvent({ ...BASE_EVENT, scheduledDate: null })

    expect(issues).toContainEqual(
      expect.objectContaining({
        code: 'calendar_event.scheduled_date.required',
      }),
    )
    expect(() =>
      parseCalendarEvent({ ...BASE_EVENT, scheduledDate: null }),
    ).toThrow(InvalidCalendarEventError)
  })

  it('requires an actual date for completed events', () => {
    const issues = validateCalendarEvent({
      ...BASE_EVENT,
      dateStatus: 'completed',
      completionStatus: 'completed',
      actualDate: null,
    })

    expect(issues).toContainEqual(
      expect.objectContaining({ code: 'calendar_event.actual_date.required' }),
    )
  })

  it('does not allow an actual date to replace either scheduled-date field', () => {
    const issues = validateCalendarEvent({
      ...BASE_EVENT,
      dateStatus: 'completed',
      completionStatus: 'completed',
      originalScheduledDate: null,
      scheduledDate: null,
      actualDate: '2026-10-21',
    })

    expect(issues).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          code: 'calendar_event.scheduled_date.required',
        }),
        expect.objectContaining({ code: 'calendar_event.actual_date.unanchored' }),
      ]),
    )
  })

  it('keeps actual and scheduled dates in separate fields', () => {
    const event = parseCalendarEvent({
      ...BASE_EVENT,
      dateStatus: 'completed',
      completionStatus: 'completed',
      actualDate: '2026-10-21',
    })

    expect(event.originalScheduledDate).toBe('2026-10-20')
    expect(event.scheduledDate).toBe('2026-10-20')
    expect(event.actualDate).toBe('2026-10-21')
  })

  it('requires a valid TeamId for a team event', () => {
    const missingIssues = validateCalendarEvent({
      ...BASE_EVENT,
      scope: 'team',
    })
    const invalidIssues = validateCalendarEvent({
      ...BASE_EVENT,
      scope: 'team',
      teamId: 'TEAM BAD',
    })

    expect(missingIssues).toContainEqual(
      expect.objectContaining({ code: 'calendar_event.team_id.required' }),
    )
    expect(invalidIssues).toContainEqual(
      expect.objectContaining({ code: 'calendar_event.team_id.required' }),
    )
    expect(
      parseCalendarEvent({
        ...BASE_EVENT,
        scope: 'team',
        teamId: 'team_stone_01',
      }).teamId,
    ).toBe('team_stone_01')
  })

  it('rejects any TeamId field on a league-wide event', () => {
    expect(
      validateCalendarEvent({ ...BASE_EVENT, teamId: 'team_stone_01' }),
    ).toContainEqual(
      expect.objectContaining({ code: 'calendar_event.team_id.forbidden' }),
    )
  })

  it('preserves a postponed event original date while allowing a new date', () => {
    const rescheduled = parseCalendarEvent({
      ...BASE_EVENT,
      dateStatus: 'postponed',
      originalScheduledDate: '2026-10-20',
      scheduledDate: '2026-10-24',
    })
    const stillTba = parseCalendarEvent({
      ...BASE_EVENT,
      dateStatus: 'postponed',
      originalScheduledDate: '2026-10-20',
      scheduledDate: null,
    })

    expect(rescheduled.originalScheduledDate).toBe('2026-10-20')
    expect(rescheduled.scheduledDate).toBe('2026-10-24')
    expect(stillTba.scheduledDate).toBeNull()
  })

  it('retains original and current dates after a postponed event completes', () => {
    const event = parseCalendarEvent({
      ...BASE_EVENT,
      dateStatus: 'completed',
      completionStatus: 'completed',
      originalScheduledDate: '2026-10-20',
      scheduledDate: '2026-10-24',
      actualDate: '2026-10-24',
    })

    expect(event.originalScheduledDate).toBe('2026-10-20')
    expect(event.scheduledDate).toBe('2026-10-24')
    expect(event.actualDate).toBe('2026-10-24')
  })

  it('rejects a postponed event that loses its original date', () => {
    const issues = validateCalendarEvent({
      ...BASE_EVENT,
      dateStatus: 'postponed',
      originalScheduledDate: null,
      scheduledDate: null,
    })

    expect(issues).toContainEqual(
      expect.objectContaining({ code: 'calendar_event.original_date.required' }),
    )
  })

  it('rejects malformed dates and inconsistent completion states', () => {
    expect(
      validateCalendarEvent({ ...BASE_EVENT, scheduledDate: '2026-02-30' }),
    ).toContainEqual(
      expect.objectContaining({ code: 'calendar_event.date.invalid' }),
    )
    expect(
      validateCalendarEvent({
        ...BASE_EVENT,
        completionStatus: 'completed',
        actualDate: '2026-10-20',
      }),
    ).toContainEqual(
      expect.objectContaining({ code: 'calendar_event.completion.invalid' }),
    )
    expect(
      validateCalendarEvent({ ...BASE_EVENT, actualDate: '2026-10-20' }),
    ).toContainEqual(
      expect.objectContaining({
        code: 'calendar_event.actual_date_status.invalid',
      }),
    )
    expect(
      validateCalendarEvent({
        ...BASE_EVENT,
        dateStatus: 'completed',
        completionStatus: 'pending',
        actualDate: '2026-10-20',
      }),
    ).toContainEqual(
      expect.objectContaining({ code: 'calendar_event.completion.invalid' }),
    )
  })
})

describe('SeasonCalendar', () => {
  it('parses a versioned immutable event collection for one season', () => {
    const calendar = parseSeasonCalendar({
      id: 'season_calendar_stone_01',
      version: 1,
      seasonId: BASE_EVENT.seasonId,
      events: [BASE_EVENT],
    })

    expect(calendar.id).toBe('season_calendar_stone_01')
    expect(calendar.version).toBe(1)
    expect(calendar.events).toHaveLength(1)
    expect(Object.isFrozen(calendar)).toBe(true)
    expect(Object.isFrozen(calendar.events)).toBe(true)
  })

  it('rejects duplicate event IDs and wrong season references', () => {
    const issues = validateSeasonCalendar({
      id: 'season_calendar_stone_01',
      version: 1,
      seasonId: BASE_EVENT.seasonId,
      events: [
        BASE_EVENT,
        {
          ...BASE_EVENT,
          seasonId: 'season_other',
        },
      ],
    })

    expect(issues).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ code: 'calendar.event_id.duplicate' }),
        expect.objectContaining({
          code: 'calendar.event_season_id.mismatch',
        }),
      ]),
    )
    expect(() =>
      parseSeasonCalendar({
        id: 'season_calendar_stone_01',
        version: 1,
        seasonId: BASE_EVENT.seasonId,
        events: [BASE_EVENT, BASE_EVENT],
      }),
    ).toThrow(InvalidSeasonCalendarError)
  })

  it('rejects unsupported calendar versions explicitly', () => {
    expect(
      validateSeasonCalendar({
        id: 'season_calendar_stone_01',
        version: 2,
        seasonId: BASE_EVENT.seasonId,
        events: [],
      }),
    ).toContainEqual(
      expect.objectContaining({ code: 'calendar.version.invalid' }),
    )
  })

  it('rejects an invalid SeasonCalendarId', () => {
    expect(
      validateSeasonCalendar({
        id: 'Season Calendar Bad',
        version: 1,
        seasonId: BASE_EVENT.seasonId,
        events: [],
      }),
    ).toContainEqual(
      expect.objectContaining({ code: 'calendar.id.invalid' }),
    )
  })
})
