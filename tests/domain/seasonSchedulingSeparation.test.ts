import { describe, expect, it } from 'vitest'
import { parseSeasonId, parseTeamId } from '../../src/domain/ids'
import { parseLocalDate } from '../../src/domain/localDate'
import { MILESTONE_1_REGULAR_SEASON_RULE_SET } from '../../src/domain/schedule'
import {
  parseCalendarEvent,
  parseSeasonCalendar,
} from '../../src/domain/seasonCalendar'
import { parseTeamSeason } from '../../src/domain/teamSeason'
import { generateRegularSeasonSchedule } from '../../src/generation/generateSchedule'

const seasonId = parseSeasonId('season_separation_test_01')
const teams = Array.from({ length: 8 }, (_, index) => ({
  id: parseTeamId(`team_separation_${String(index + 1).padStart(2, '0')}`),
}))

function generateSchedule() {
  return generateRegularSeasonSchedule({
    seasonId,
    teams,
    scheduleSeed: 'calendar-separation-seed',
    regularSeasonStartDate: parseLocalDate('2026-10-12'),
    calendarDaySpacing: 3,
    ruleSet: MILESTONE_1_REGULAR_SEASON_RULE_SET,
  })
}

describe('season, calendar, and schedule separation', () => {
  it('does not alter generated games when a valid TBA event is added', () => {
    const scheduleBeforeCalendarChange = generateSchedule()
    const tbaEvent = parseCalendarEvent({
      id: 'calendar_event_future_draft',
      version: 1,
      seasonId,
      kind: 'draft_event',
      scope: 'league',
      title: 'Future draft',
      originalScheduledDate: null,
      scheduledDate: null,
      actualDate: null,
      dateStatus: 'tba',
      completionStatus: 'pending',
    })
    const calendar = parseSeasonCalendar({
      version: 1,
      seasonId,
      events: [tbaEvent],
    })
    const scheduleAfterCalendarChange = generateSchedule()

    expect(calendar.events).toEqual([tbaEvent])
    expect(scheduleAfterCalendarChange.games).toEqual(
      scheduleBeforeCalendarChange.games,
    )
    expect(scheduleAfterCalendarChange).toEqual(scheduleBeforeCalendarChange)
  })

  it('keeps a team offseason start independent from the league offseason event', () => {
    const teamSeason = parseTeamSeason({
      version: 1,
      seasonId,
      teamId: teams[0].id,
      competitiveStatus: 'eliminated',
      eliminationDate: '2027-04-18',
      teamOffseasonStartDate: '2027-04-19',
      postseasonSeed: 8,
    })
    const leagueOffseasonEvent = parseCalendarEvent({
      id: 'calendar_event_league_offseason',
      version: 1,
      seasonId,
      kind: 'league_offseason_start',
      scope: 'league',
      title: 'League offseason begins',
      originalScheduledDate: '2027-06-30',
      scheduledDate: '2027-06-30',
      actualDate: null,
      dateStatus: 'scheduled',
      completionStatus: 'pending',
    })
    const calendar = parseSeasonCalendar({
      version: 1,
      seasonId,
      events: [leagueOffseasonEvent],
    })

    expect(teamSeason.teamOffseasonStartDate).toBe('2027-04-19')
    expect(calendar.events[0].scheduledDate).toBe('2027-06-30')
    expect(teamSeason.teamOffseasonStartDate).not.toBe(
      calendar.events[0].scheduledDate,
    )
    expect('teamId' in calendar.events[0]).toBe(false)
  })
})
