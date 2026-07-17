import { describe, expect, it } from 'vitest'
import { buildBalancedMeetingMatrix } from '../../src/generation/scheduleMatrix'

function summarize(teamCount: number, gamesPerTeam: number) {
  const meetings = buildBalancedMeetingMatrix({ teamCount, gamesPerTeam })
  const home = new Array<number>(teamCount).fill(0)
  const away = new Array<number>(teamCount).fill(0)
  const pairCounts = new Map<string, number>()
  for (const meeting of meetings) {
    home[meeting.homeIndex] += 1
    away[meeting.awayIndex] += 1
    const key = [meeting.homeIndex, meeting.awayIndex]
      .sort((a, b) => a - b)
      .join('-')
    pairCounts.set(key, (pairCounts.get(key) ?? 0) + 1)
  }
  return { meetings, home, away, pairCounts }
}

describe('buildBalancedMeetingMatrix', () => {
  it('produces a balanced 30-team, 82-game NBA-shaped schedule', () => {
    const { meetings, home, away, pairCounts } = summarize(30, 82)

    // 30 teams x 82 games / 2 = 1230 total league games.
    expect(meetings).toHaveLength(1230)
    for (let team = 0; team < 30; team += 1) {
      expect(home[team]).toBe(41)
      expect(away[team]).toBe(41)
    }
    // Every pair meets either two or three times, and the split is exact.
    const counts = [...pairCounts.values()]
    expect(pairCounts.size).toBe((30 * 29) / 2)
    expect(counts.every((count) => count === 2 || count === 3)).toBe(true)
    // Each team plays 24 opponents three times and 5 twice.
    expect(counts.filter((count) => count === 3)).toHaveLength((30 * 24) / 2)
    expect(counts.filter((count) => count === 2)).toHaveLength((30 * 5) / 2)
  })

  it('is deterministic', () => {
    const first = buildBalancedMeetingMatrix({ teamCount: 30, gamesPerTeam: 82 })
    const second = buildBalancedMeetingMatrix({ teamCount: 30, gamesPerTeam: 82 })
    expect(first).toEqual(second)
  })

  it('supports a plain double round robin with no extra games', () => {
    const { home, away, pairCounts } = summarize(8, 14)
    for (let team = 0; team < 8; team += 1) {
      expect(home[team]).toBe(7)
      expect(away[team]).toBe(7)
    }
    expect([...pairCounts.values()].every((count) => count === 2)).toBe(true)
  })

  it('rejects invalid configurations', () => {
    expect(() =>
      buildBalancedMeetingMatrix({ teamCount: 7, gamesPerTeam: 82 }),
    ).toThrow(RangeError)
    expect(() =>
      buildBalancedMeetingMatrix({ teamCount: 30, gamesPerTeam: 57 }),
    ).toThrow(RangeError)
    expect(() =>
      buildBalancedMeetingMatrix({ teamCount: 30, gamesPerTeam: 400 }),
    ).toThrow(RangeError)
  })
})
