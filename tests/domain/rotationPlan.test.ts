import { describe, expect, it } from 'vitest'
import { generateLeague } from '../../src/generation/generateLeague'
import { MILESTONE_1_LEAGUE_RULES } from '../../src/domain/leagueRules'
import type { League, Player } from '../../src/domain/league'
import type { PlayerId, TeamId } from '../../src/domain/ids'
import {
  DEFAULT_ROTATION_SIZE,
  MAX_PLAYER_REGULATION_MINUTES,
  ROTATION_GENERATOR_VERSION,
  ROTATION_PLAN_ERROR_CODES,
  ROTATION_PLAN_WARNING_CODES,
  ROTATION_REPAIR_VERSION,
  SECONDS_PER_MINUTE,
  STARTERS_REQUIRED,
  allocateWholeMinutes,
  generateRotationPlan,
  regulationMinutes,
  repairRotationPlan,
  validateRotationPlan,
} from '../../src/domain/rotationPlan'
import type { RotationPlanV1 } from '../../src/domain/rotationPlan'

const RULES = MILESTONE_1_LEAGUE_RULES
const REG_MINUTES = regulationMinutes(RULES)

function rosterOf(league: League, teamId: TeamId): readonly Player[] {
  return league.players.filter((player) => player.teamId === teamId)
}

function requirePlayer(roster: readonly Player[], index: number): Player {
  const player = roster[index]
  if (player === undefined) {
    throw new Error(`No player at roster index ${index}`)
  }
  return player
}

function totalMinutes(plan: RotationPlanV1): number {
  return (
    Object.values(plan.minuteTargetsSeconds).reduce(
      (sum, seconds) => sum + seconds,
      0,
    ) / SECONDS_PER_MINUTE
  )
}

/** Build a hand-authored plan from roster indices and per-index whole minutes. */
function planFrom(
  teamId: TeamId,
  roster: readonly Player[],
  starterIndices: readonly number[],
  minutesByIndex: Readonly<Record<number, number>>,
  options: {
    readonly source?: RotationPlanV1['source']
    readonly benchOrder?: readonly number[]
  } = {},
): RotationPlanV1 {
  const record: Record<string, number> = {}
  roster.forEach((player, index) => {
    record[player.id] = (minutesByIndex[index] ?? 0) * SECONDS_PER_MINUTE
  })
  return {
    version: 1,
    teamId,
    starters: starterIndices.map((index) => requirePlayer(roster, index).id),
    minuteTargetsSeconds: record as Readonly<Record<PlayerId, number>>,
    benchOrder: (options.benchOrder ?? []).map(
      (index) => requirePlayer(roster, index).id,
    ),
    source: options.source ?? 'user-edited',
  }
}

const errorCodes = (plan: RotationPlanV1, roster: readonly Player[]): string[] =>
  validateRotationPlan(plan, roster, RULES).errors.map((issue) => issue.code)

const warningCodes = (
  plan: RotationPlanV1,
  roster: readonly Player[],
): string[] =>
  validateRotationPlan(plan, roster, RULES).warnings.map((issue) => issue.code)

describe('generateRotationPlan', () => {
  const league = generateLeague('rotation-generate-seed')

  it('produces a valid, exactly-regulation plan for every team', () => {
    for (const team of league.teams) {
      const roster = rosterOf(league, team.id)
      const plan = generateRotationPlan({ teamId: team.id, roster, rules: RULES })
      const { errors } = validateRotationPlan(plan, roster, RULES)

      expect(errors).toEqual([])
      expect(plan.starters).toHaveLength(STARTERS_REQUIRED)
      expect(new Set(plan.starters).size).toBe(STARTERS_REQUIRED)
      expect(totalMinutes(plan)).toBe(REG_MINUTES)
      expect(plan.source).toBe('cpu-generated')
      expect(plan.generation?.generatorVersion).toBe(ROTATION_GENERATOR_VERSION)
    }
  })

  it('starts the default rotation depth with positive minutes', () => {
    const team = requireFirstTeam(league)
    const roster = rosterOf(league, team.id)
    const plan = generateRotationPlan({ teamId: team.id, roster, rules: RULES })
    const positive = Object.values(plan.minuteTargetsSeconds).filter(
      (seconds) => seconds > 0,
    )
    expect(positive).toHaveLength(DEFAULT_ROTATION_SIZE)
    for (const starter of plan.starters) {
      expect(plan.minuteTargetsSeconds[starter]).toBeGreaterThan(0)
    }
  })

  it('is deterministic and independent of roster/processing order', () => {
    const team = requireFirstTeam(league)
    const roster = rosterOf(league, team.id)
    const planA = generateRotationPlan({ teamId: team.id, roster, rules: RULES })
    const planB = generateRotationPlan({
      teamId: team.id,
      roster: [...roster].reverse(),
      rules: RULES,
    })
    const planFromWholeLeague = generateRotationPlan({
      teamId: team.id,
      roster: league.players,
      rules: RULES,
    })

    expect(planB).toEqual(planA)
    expect(planFromWholeLeague).toEqual(planA)
  })

  it('reproduces deeply-equal plans from an identical seed', () => {
    const rebuilt = generateLeague('rotation-generate-seed')
    for (const team of league.teams) {
      const original = generateRotationPlan({
        teamId: team.id,
        roster: rosterOf(league, team.id),
        rules: RULES,
      })
      const again = generateRotationPlan({
        teamId: team.id,
        roster: rosterOf(rebuilt, team.id),
        rules: RULES,
      })
      expect(again).toEqual(original)
    }
  })
})

describe('validateRotationPlan — blocking errors', () => {
  const league = generateLeague('rotation-validate-seed')
  const team = requireFirstTeam(league)
  const roster = rosterOf(league, team.id)

  it('accepts a generated plan with no errors', () => {
    const plan = generateRotationPlan({ teamId: team.id, roster, rules: RULES })
    expect(errorCodes(plan, roster)).toEqual([])
  })

  it('rejects a minute total that is not exactly regulation', () => {
    const plan = generateRotationPlan({ teamId: team.id, roster, rules: RULES })
    const broken: RotationPlanV1 = {
      ...plan,
      minuteTargetsSeconds: {
        ...plan.minuteTargetsSeconds,
        [requirePlayer(roster, 0).id]:
          (plan.minuteTargetsSeconds[requirePlayer(roster, 0).id] ?? 0) -
          SECONDS_PER_MINUTE,
      },
    }
    expect(errorCodes(broken, roster)).toContain(
      ROTATION_PLAN_ERROR_CODES.minuteTotal,
    )
  })

  it('rejects duplicate starters', () => {
    const plan = planFrom(team.id, roster, [0, 0, 1, 2, 3], {
      0: 48,
      1: 48,
      2: 48,
      3: 48,
      4: 48,
    })
    expect(errorCodes(plan, roster)).toContain(
      ROTATION_PLAN_ERROR_CODES.duplicateStarter,
    )
  })

  it('rejects fewer than five starters', () => {
    const plan = planFrom(team.id, roster, [0, 1, 2, 3], {
      0: 48,
      1: 48,
      2: 48,
      3: 48,
      4: 48,
    })
    expect(errorCodes(plan, roster)).toContain(
      ROTATION_PLAN_ERROR_CODES.starterCount,
    )
  })

  it('rejects a starter with zero minutes', () => {
    const plan = planFrom(team.id, roster, [0, 1, 2, 3, 4], {
      0: 48,
      1: 48,
      2: 48,
      3: 48,
      5: 48,
    })
    expect(errorCodes(plan, roster)).toContain(
      ROTATION_PLAN_ERROR_CODES.starterZeroMinutes,
    )
  })

  it('rejects minutes above the regulation cap', () => {
    const overCap: RotationPlanV1 = planFrom(team.id, roster, [0, 1, 2, 3, 4], {
      0: 48,
      1: 48,
      2: 48,
      3: 48,
      4: 48,
    })
    const broken: RotationPlanV1 = {
      ...overCap,
      minuteTargetsSeconds: {
        ...overCap.minuteTargetsSeconds,
        [requirePlayer(roster, 0).id]: 49 * SECONDS_PER_MINUTE,
        [requirePlayer(roster, 1).id]: 47 * SECONDS_PER_MINUTE,
      },
    }
    expect(errorCodes(broken, roster)).toContain(
      ROTATION_PLAN_ERROR_CODES.minuteOutOfRange,
    )
  })
})

describe('validateRotationPlan — non-blocking warnings', () => {
  const league = generateLeague('rotation-warning-seed')
  const team = requireFirstTeam(league)
  const roster = rosterOf(league, team.id)

  it('warns but does not error when only five players have minutes', () => {
    const plan = planFrom(team.id, roster, [0, 1, 2, 3, 4], {
      0: 48,
      1: 48,
      2: 48,
      3: 48,
      4: 48,
    })
    const { errors, warnings } = validateRotationPlan(plan, roster, RULES)
    expect(errors).toEqual([])
    expect(warnings.map((issue) => issue.code)).toContain(
      ROTATION_PLAN_WARNING_CODES.onlyFivePlayers,
    )
    expect(warnings.map((issue) => issue.code)).toContain(
      ROTATION_PLAN_WARNING_CODES.playerAtMax,
    )
  })

  it('warns about a very-low-minute starter', () => {
    const plan = planFrom(team.id, roster, [0, 1, 2, 3, 4], {
      0: 6,
      1: 48,
      2: 48,
      3: 48,
      4: 48,
      5: 42,
    })
    expect(errorCodes(plan, roster)).toEqual([])
    expect(warningCodes(plan, roster)).toContain(
      ROTATION_PLAN_WARNING_CODES.starterLowMinutes,
    )
  })

  it('warns about an unusually deep rotation', () => {
    const plan = planFrom(
      team.id,
      roster,
      [0, 1, 2, 3, 4],
      { 0: 24, 1: 24, 2: 24, 3: 24, 4: 24, 5: 20, 6: 20, 7: 20, 8: 20, 9: 20, 10: 20 },
      { benchOrder: [5, 6, 7, 8, 9, 10] },
    )
    expect(errorCodes(plan, roster)).toEqual([])
    expect(warningCodes(plan, roster)).toContain(
      ROTATION_PLAN_WARNING_CODES.deepRotation,
    )
  })
})

describe('repairRotationPlan', () => {
  const league = generateLeague('rotation-repair-seed')
  const team = requireFirstTeam(league)
  const roster = rosterOf(league, team.id)

  it('leaves an intact, valid plan untouched', () => {
    const plan = generateRotationPlan({ teamId: team.id, roster, rules: RULES })
    const result = repairRotationPlan({ plan, roster, rules: RULES })
    expect(result.repaired).toBe(false)
    expect(result.plan).toBe(plan)
  })

  it('repairs a bench departure back to a valid, exact plan', () => {
    const plan = generateRotationPlan({ teamId: team.id, roster, rules: RULES })
    const departed = requirePlayer(roster, roster.length - 1).id
    const trimmed = roster.filter((player) => player.id !== departed)

    const result = repairRotationPlan({ plan, roster: trimmed, rules: RULES })
    expect(result.repaired).toBe(true)
    expect(errorCodes(result.plan, trimmed)).toEqual([])
    expect(totalMinutes(result.plan)).toBe(REG_MINUTES)
    expect(result.plan.source).toBe(plan.source)
    expect(result.plan.autoRepair?.repairVersion).toBe(ROTATION_REPAIR_VERSION)
    expect(result.plan.minuteTargetsSeconds[departed]).toBeUndefined()
  })

  it('replaces a departed starter and stays valid', () => {
    const plan = generateRotationPlan({ teamId: team.id, roster, rules: RULES })
    const departedStarter = plan.starters[0]
    if (departedStarter === undefined) {
      throw new Error('Generated plan is missing starters')
    }
    const trimmed = roster.filter((player) => player.id !== departedStarter)

    const result = repairRotationPlan({ plan, roster: trimmed, rules: RULES })
    expect(result.repaired).toBe(true)
    expect(result.plan.starters).toHaveLength(STARTERS_REQUIRED)
    expect(new Set(result.plan.starters).size).toBe(STARTERS_REQUIRED)
    expect(result.plan.starters).not.toContain(departedStarter)
    expect(errorCodes(result.plan, trimmed)).toEqual([])
    expect(result.plan.autoRepair?.reason).toBe('starter-ineligible')
  })

  it('fills a user-edited starter vacancy from its own bench order first', () => {
    // Bench index 7 is the user's declared top backup; index 6 out-ranks it by
    // ability, so a bench-order-first repair must still pick 7.
    const plan = planFrom(
      team.id,
      roster,
      [0, 1, 2, 3, 4],
      { 0: 30, 1: 30, 2: 30, 3: 30, 4: 30, 6: 30, 7: 30, 8: 30 },
      { source: 'user-edited', benchOrder: [7, 6, 8] },
    )
    expect(errorCodes(plan, roster)).toEqual([])

    const departedStarter = requirePlayer(roster, 0).id
    const trimmed = roster.filter((player) => player.id !== departedStarter)
    const result = repairRotationPlan({ plan, roster: trimmed, rules: RULES })

    expect(result.plan.starters).toContain(requirePlayer(roster, 7).id)
    expect(result.plan.starters).not.toContain(requirePlayer(roster, 6).id)
    expect(errorCodes(result.plan, trimmed)).toEqual([])
  })

  it('repairs deterministically', () => {
    const plan = generateRotationPlan({ teamId: team.id, roster, rules: RULES })
    const trimmed = roster.filter(
      (player) => player.id !== requirePlayer(roster, 2).id,
    )
    const first = repairRotationPlan({ plan, roster: trimmed, rules: RULES })
    const second = repairRotationPlan({ plan, roster: trimmed, rules: RULES })
    expect(second.plan).toEqual(first.plan)
  })
})

describe('allocateWholeMinutes', () => {
  it('always sums to the requested total and respects the cap', () => {
    // A dominant weight would exceed the cap; six players make 240 reachable.
    const ids = ['a', 'b', 'c', 'd', 'e', 'f'] as unknown as PlayerId[]
    const weights = new Map<PlayerId, number>(
      ids.map((id, index) => [id, index === 0 ? 100 : 1]),
    )
    const allocation = allocateWholeMinutes(weights, REG_MINUTES, ids)
    const sum = [...allocation.values()].reduce((total, m) => total + m, 0)
    expect(sum).toBe(REG_MINUTES)
    for (const minutes of allocation.values()) {
      expect(minutes).toBeLessThanOrEqual(MAX_PLAYER_REGULATION_MINUTES)
    }
    // The dominant weight is capped, not overrun.
    const dominant = ids[0]
    if (dominant === undefined) {
      throw new Error('missing id')
    }
    expect(allocation.get(dominant)).toBe(MAX_PLAYER_REGULATION_MINUTES)
  })
})

function requireFirstTeam(league: League) {
  const team = league.teams[0]
  if (team === undefined) {
    throw new Error('Generated league has no teams')
  }
  return team
}
