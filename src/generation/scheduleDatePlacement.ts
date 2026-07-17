import type { ScheduledMeeting } from './scheduleMatrix'

export interface MeetingPlacement {
  /** Index into the supplied meetings array. */
  readonly meetingIndex: number
  /** Zero-based day offset within the scheduling window. */
  readonly dateIndex: number
}

export interface DatePlacementConfig {
  readonly meetings: readonly ScheduledMeeting[]
  readonly dateCount: number
}

/**
 * Places every meeting on a day within the window such that no team plays twice
 * on the same day. Each day is therefore a matching (capped naturally at
 * teamCount / 2 games). Placement is deterministic: meeting k starts its search
 * at day `k mod dateCount` and takes the first day both teams are free, which
 * spreads a team's games across the window rather than clumping them.
 *
 * The window must be long enough for the busiest team — a team playing G games
 * needs at least G distinct days. Feasibility is otherwise guaranteed because
 * any two teams always share a free day when neither is yet fully scheduled.
 */
export function placeMeetingsAcrossDates({
  meetings,
  dateCount,
}: DatePlacementConfig): readonly MeetingPlacement[] {
  if (!Number.isSafeInteger(dateCount) || dateCount < 1) {
    throw new RangeError(`Date count must be a positive integer: ${String(dateCount)}`)
  }

  const teamGames = new Map<number, number>()
  for (const meeting of meetings) {
    teamGames.set(meeting.homeIndex, (teamGames.get(meeting.homeIndex) ?? 0) + 1)
    teamGames.set(meeting.awayIndex, (teamGames.get(meeting.awayIndex) ?? 0) + 1)
  }
  const busiest = Math.max(0, ...teamGames.values())
  if (busiest > dateCount) {
    throw new RangeError(
      `Window of ${dateCount} days is too short for a team playing ${busiest} games`,
    )
  }

  const teamDays = new Map<number, Set<number>>()
  const placements: MeetingPlacement[] = []

  for (let index = 0; index < meetings.length; index += 1) {
    const meeting = meetings[index]
    const homeDays = daysFor(teamDays, meeting.homeIndex)
    const awayDays = daysFor(teamDays, meeting.awayIndex)

    const start = index % dateCount
    let placed = false
    for (let step = 0; step < dateCount; step += 1) {
      const dateIndex = (start + step) % dateCount
      if (!homeDays.has(dateIndex) && !awayDays.has(dateIndex)) {
        homeDays.add(dateIndex)
        awayDays.add(dateIndex)
        placements.push({ meetingIndex: index, dateIndex })
        placed = true
        break
      }
    }
    if (!placed) {
      throw new RangeError(
        `Could not place meeting ${index}; window of ${dateCount} days is too tight`,
      )
    }
  }

  return Object.freeze(
    placements.sort(
      (left, right) =>
        left.dateIndex - right.dateIndex ||
        left.meetingIndex - right.meetingIndex,
    ),
  )
}

function daysFor(teamDays: Map<number, Set<number>>, team: number): Set<number> {
  let days = teamDays.get(team)
  if (days === undefined) {
    days = new Set<number>()
    teamDays.set(team, days)
  }
  return days
}
