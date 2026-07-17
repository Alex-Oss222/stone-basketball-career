import { describe, expect, it } from 'vitest'
import { parseLocalDate } from '../../src/domain/localDate'
import {
  deriveLeagueMilestones,
  nextLeagueMilestone,
} from '../../src/app/leagueMilestones'

const OPENING = parseLocalDate('2026-10-05')
const CONCLUSION = parseLocalDate('2027-04-12')

describe('deriveLeagueMilestones', () => {
  it('places milestones in season order between opening and off-season', () => {
    const milestones = deriveLeagueMilestones(OPENING, CONCLUSION)
    const kinds = milestones.map((milestone) => milestone.kind)

    expect(kinds).toEqual([
      'all_star_break',
      'trade_deadline',
      'play_in_event',
      'playoffs_start',
      'finals_start',
      'draft_event',
      'free_agency_event',
    ])

    // Dates are strictly increasing.
    for (let index = 1; index < milestones.length; index += 1) {
      expect(milestones[index].date > milestones[index - 1].date).toBe(true)
    }
    // In-season events land between opening and conclusion.
    const allStar = milestones[0]
    expect(allStar.date > OPENING).toBe(true)
    expect(allStar.date < CONCLUSION).toBe(true)
    // Off-season events land after the conclusion.
    expect(milestones[2].date > CONCLUSION).toBe(true)
    expect(Object.isFrozen(milestones)).toBe(true)
  })

  it('returns nothing when the conclusion is not after the opening', () => {
    expect(deriveLeagueMilestones(CONCLUSION, OPENING)).toEqual([])
    expect(deriveLeagueMilestones(OPENING, OPENING)).toEqual([])
  })

  it('finds the next milestone on or after the current date', () => {
    const milestones = deriveLeagueMilestones(OPENING, CONCLUSION)

    const early = nextLeagueMilestone(milestones, parseLocalDate('2026-10-06'))
    expect(early?.kind).toBe('all_star_break')

    const late = nextLeagueMilestone(milestones, parseLocalDate('2027-12-31'))
    expect(late).toBeNull()
  })
})
