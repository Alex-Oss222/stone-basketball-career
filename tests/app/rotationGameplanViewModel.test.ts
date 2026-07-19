import { describe, expect, it } from 'vitest'
import { generateLeague } from '../../src/generation/generateLeague'
import { MILESTONE_1_LEAGUE_RULES } from '../../src/domain/leagueRules'
import { generateRotationPlan } from '../../src/domain/rotationPlan'
import {
  deriveRotationTier,
  displayOrder,
  draftFromPlan,
  draftsEqual,
  minutesByPeriod,
  planFromDraft,
  reorder,
} from '../../src/app/rotationGameplanViewModel'

const league = generateLeague('rotation-view-model-seed')
const team = league.teams[0]
const roster = league.players.filter((player) => player.teamId === team.id)
const plan = generateRotationPlan({
  teamId: team.id,
  roster,
  rules: MILESTONE_1_LEAGUE_RULES,
})

describe('minutesByPeriod', () => {
  it('splits evenly and always sums back to the total', () => {
    expect(minutesByPeriod(34, 4)).toEqual([9, 9, 8, 8])
    expect(minutesByPeriod(48, 8)).toEqual([6, 6, 6, 6, 6, 6, 6, 6])
    for (const total of [0, 7, 16, 33, 41]) {
      const split = minutesByPeriod(total, 4)
      expect(split).toHaveLength(4)
      expect(split.reduce((sum, value) => sum + value, 0)).toBe(total)
    }
  })
})

describe('depth-chart draft model', () => {
  it('draftFromPlan then planFromDraft preserves starters, bench order, and minutes', () => {
    const draft = draftFromPlan(plan, roster)
    const rebuilt = planFromDraft(draft, team.id, roster, plan.source)
    expect(rebuilt.starters).toEqual(plan.starters)
    expect(rebuilt.benchOrder).toEqual(plan.benchOrder)
    expect(rebuilt.minuteTargetsSeconds).toEqual(plan.minuteTargetsSeconds)
  })

  it('makes the top five the starters and ranks the tiers by depth', () => {
    const draft = draftFromPlan(plan, roster)
    const ordered = displayOrder(draft, roster)
    expect(ordered).toHaveLength(roster.length)
    for (let index = 0; index < 5; index += 1) {
      expect(deriveRotationTier(draft, ordered[index].id)).toBe('Starter')
    }
    expect(deriveRotationTier(draft, ordered[5].id)).toBe('Sixth Man')
  })

  it('detects reordering as a change', () => {
    const draft = draftFromPlan(plan, roster)
    const moved = { ...draft, order: reorder(draft.order, draft.order[0], 1) }
    expect(draftsEqual(draft, moved, roster)).toBe(false)
    expect(draftsEqual(draft, draft, roster)).toBe(true)
  })
})
