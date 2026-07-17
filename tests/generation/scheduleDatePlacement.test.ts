import { describe, expect, it } from 'vitest'
import { buildBalancedMeetingMatrix } from '../../src/generation/scheduleMatrix'
import { placeMeetingsAcrossDates } from '../../src/generation/scheduleDatePlacement'

const NBA_MEETINGS = buildBalancedMeetingMatrix({
  teamCount: 30,
  gamesPerTeam: 82,
})
const WINDOW_DAYS = 174

describe('placeMeetingsAcrossDates', () => {
  it('places every NBA meeting with no team playing twice in a day', () => {
    const placements = placeMeetingsAcrossDates({
      meetings: NBA_MEETINGS,
      dateCount: WINDOW_DAYS,
    })

    expect(placements).toHaveLength(NBA_MEETINGS.length)

    const teamsByDay = new Map<number, Set<number>>()
    const gamesByTeam = new Map<number, number>()
    for (const placement of placements) {
      const meeting = NBA_MEETINGS[placement.meetingIndex]
      const day = teamsByDay.get(placement.dateIndex) ?? new Set<number>()
      expect(day.has(meeting.homeIndex)).toBe(false)
      expect(day.has(meeting.awayIndex)).toBe(false)
      day.add(meeting.homeIndex)
      day.add(meeting.awayIndex)
      teamsByDay.set(placement.dateIndex, day)
      gamesByTeam.set(
        meeting.homeIndex,
        (gamesByTeam.get(meeting.homeIndex) ?? 0) + 1,
      )
      gamesByTeam.set(
        meeting.awayIndex,
        (gamesByTeam.get(meeting.awayIndex) ?? 0) + 1,
      )
    }

    // Every team plays exactly 82 games, each on a distinct day.
    for (let team = 0; team < 30; team += 1) {
      expect(gamesByTeam.get(team)).toBe(82)
    }
    // A day never exceeds a full 15-game slate.
    for (const teams of teamsByDay.values()) {
      expect(teams.size).toBeLessThanOrEqual(30)
    }
  })

  it('spreads games across the whole window, not just the front', () => {
    const placements = placeMeetingsAcrossDates({
      meetings: NBA_MEETINGS,
      dateCount: WINDOW_DAYS,
    })
    const used = new Set(placements.map((placement) => placement.dateIndex))
    // Games appear in the last quarter of the window, not only the first days.
    expect(Math.max(...used)).toBeGreaterThan(WINDOW_DAYS * 0.6)
    expect(used.size).toBeGreaterThan(WINDOW_DAYS * 0.5)
  })

  it('is deterministic and rejects too-short windows', () => {
    const first = placeMeetingsAcrossDates({
      meetings: NBA_MEETINGS,
      dateCount: WINDOW_DAYS,
    })
    const second = placeMeetingsAcrossDates({
      meetings: NBA_MEETINGS,
      dateCount: WINDOW_DAYS,
    })
    expect(first).toEqual(second)

    expect(() =>
      placeMeetingsAcrossDates({ meetings: NBA_MEETINGS, dateCount: 50 }),
    ).toThrow(RangeError)
  })
})
