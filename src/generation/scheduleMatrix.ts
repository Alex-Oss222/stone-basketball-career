/**
 * A single scheduled meeting between two team indexes, home and away resolved.
 * Indexes refer to positions in the ordered league team list.
 */
export interface ScheduledMeeting {
  readonly homeIndex: number
  readonly awayIndex: number
}

export interface MeetingMatrixConfig {
  readonly teamCount: number
  readonly gamesPerTeam: number
}

/**
 * Builds a deterministic, perfectly balanced meeting matrix. Every team plays
 * exactly `gamesPerTeam` games split evenly into home and away, and each pair of
 * teams meets either two or three times, matching the NBA's 30-team, 82-game
 * shape (41 home and 41 away). No randomness is involved.
 *
 * Construction:
 *  - a double round robin gives every ordered pair one game (home once each way);
 *  - a set of extra "third meetings" on fixed circulant offsets adds the balance
 *    up to `gamesPerTeam`, oriented so each team gains equal extra home and away.
 */
export function buildBalancedMeetingMatrix({
  teamCount,
  gamesPerTeam,
}: MeetingMatrixConfig): readonly ScheduledMeeting[] {
  if (!Number.isSafeInteger(teamCount) || teamCount < 2 || teamCount % 2 !== 0) {
    throw new RangeError(
      `Team count must be an even integer of at least 2: ${String(teamCount)}`,
    )
  }
  const baseGames = 2 * (teamCount - 1)
  const extra = gamesPerTeam - baseGames
  if (!Number.isSafeInteger(gamesPerTeam) || extra < 0 || extra % 2 !== 0) {
    throw new RangeError(
      `Games per team must be an even number of extra games above the double round robin (${baseGames}): ${String(gamesPerTeam)}`,
    )
  }
  const extraHalf = extra / 2
  const maxPairedOffset = Math.floor((teamCount - 1) / 2)
  if (extraHalf > maxPairedOffset) {
    throw new RangeError(
      `Games per team ${gamesPerTeam} exceeds what ${teamCount} teams can support`,
    )
  }

  const meetings: ScheduledMeeting[] = []

  // Double round robin: every ordered pair meets once, home team is the first.
  for (let home = 0; home < teamCount; home += 1) {
    for (let away = 0; away < teamCount; away += 1) {
      if (home !== away) meetings.push({ homeIndex: home, awayIndex: away })
    }
  }

  // Extra third meetings on the top `extraHalf` circulant offsets.
  const firstOffset = maxPairedOffset - extraHalf + 1
  for (let offset = firstOffset; offset <= maxPairedOffset; offset += 1) {
    for (let home = 0; home < teamCount; home += 1) {
      const away = (home + offset) % teamCount
      meetings.push({ homeIndex: home, awayIndex: away })
    }
  }

  return Object.freeze(meetings)
}
