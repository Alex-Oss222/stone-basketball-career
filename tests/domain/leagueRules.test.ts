import { describe, expect, it } from 'vitest'
import {
  OVERTIME_TEAM_SECONDS,
  PLAYERS_ON_COURT,
  REGULATION_PERIODS,
  REGULATION_PERIOD_SECONDS,
  REGULATION_TEAM_SECONDS,
} from '../../src/domain/gameResult'
import {
  InvalidLeagueRulesError,
  LEAGUE_RULES_VERSION,
  MILESTONE_1_LEAGUE_RULES,
  assertValidLeagueRules,
  collectLeagueRulesIssues,
  deriveOvertimeTeamSeconds,
  deriveRegulationTeamSeconds,
} from '../../src/domain/leagueRules'
import type { LeagueRulesV1 } from '../../src/domain/leagueRules'

describe('the approved Milestone 1 rule pack', () => {
  it('encodes exactly the approved baseline', () => {
    expect(MILESTONE_1_LEAGUE_RULES).toEqual({
      rulesVersion: 1,
      regulation: { periodCount: 4, secondsPerPeriod: 720 },
      overtime: {
        secondsPerPeriod: 300,
        repeatUntilWinner: true,
        maxTiedPeriodsBeforeTiebreak: 20,
      },
      lineup: {
        playersOnCourt: 5,
        personalFoulLimit: 6,
        unlimitedReentry: true,
      },
      clocks: {
        shotClockSeconds: 24,
        offensiveReboundResetSeconds: 14,
        backcourtAdvanceSeconds: 8,
      },
      teamFouls: {
        regulationNonPenaltyFouls: 4,
        overtimeNonPenaltyFouls: 3,
        latePeriodRule: {
          windowSeconds: 120,
          nonPenaltyFoulsAllowedWhenBelowQuota: 1,
        },
        offensiveFoulsCountTowardBonus: false,
      },
      freeThrows: {
        missedTwoPointShootingFoulAttempts: 2,
        missedThreePointShootingFoulAttempts: 3,
        madeBasketShootingFoulAttempts: 1,
        penaltyFoulAttempts: 2,
      },
      substitutions: { requireDeadBall: true },
    })
    expect(MILESTONE_1_LEAGUE_RULES.rulesVersion).toBe(LEAGUE_RULES_VERSION)
    expect(Object.isFrozen(MILESTONE_1_LEAGUE_RULES)).toBe(true)
    expect(Object.isFrozen(MILESTONE_1_LEAGUE_RULES.teamFouls)).toBe(true)
  })

  it('passes its own validator', () => {
    expect(collectLeagueRulesIssues(MILESTONE_1_LEAGUE_RULES)).toEqual([])
    expect(() =>
      assertValidLeagueRules(MILESTONE_1_LEAGUE_RULES),
    ).not.toThrow()
  })

  it('derives 240 regulation player-minutes instead of storing the number', () => {
    expect(deriveRegulationTeamSeconds(MILESTONE_1_LEAGUE_RULES)).toBe(
      4 * 720 * 5,
    )
    expect(deriveRegulationTeamSeconds(MILESTONE_1_LEAGUE_RULES) / 60).toBe(240)
    expect(deriveOvertimeTeamSeconds(MILESTONE_1_LEAGUE_RULES) / 60).toBe(25)
  })

  it('agrees with the frozen result-contract time constants', () => {
    expect(MILESTONE_1_LEAGUE_RULES.regulation.periodCount).toBe(
      REGULATION_PERIODS,
    )
    expect(MILESTONE_1_LEAGUE_RULES.regulation.secondsPerPeriod).toBe(
      REGULATION_PERIOD_SECONDS,
    )
    expect(MILESTONE_1_LEAGUE_RULES.lineup.playersOnCourt).toBe(
      PLAYERS_ON_COURT,
    )
    expect(deriveRegulationTeamSeconds(MILESTONE_1_LEAGUE_RULES)).toBe(
      REGULATION_TEAM_SECONDS,
    )
    expect(deriveOvertimeTeamSeconds(MILESTONE_1_LEAGUE_RULES)).toBe(
      OVERTIME_TEAM_SECONDS,
    )
  })

  it('distinguishes the regulation and overtime penalty thresholds', () => {
    expect(MILESTONE_1_LEAGUE_RULES.teamFouls.regulationNonPenaltyFouls).toBe(4)
    expect(MILESTONE_1_LEAGUE_RULES.teamFouls.overtimeNonPenaltyFouls).toBe(3)
    expect(
      MILESTONE_1_LEAGUE_RULES.teamFouls.offensiveFoulsCountTowardBonus,
    ).toBe(false)
  })
})

describe('rule-pack validation', () => {
  function withOverrides(
    overrides: (rules: LeagueRulesV1) => LeagueRulesV1,
  ): LeagueRulesV1 {
    return overrides(structuredClone(MILESTONE_1_LEAGUE_RULES))
  }

  it('rejects non-positive or fractional values', () => {
    const zeroFouls = withOverrides((rules) => ({
      ...rules,
      lineup: { ...rules.lineup, personalFoulLimit: 0 },
    }))
    expect(collectLeagueRulesIssues(zeroFouls).map((i) => i.code)).toContain(
      'positive_integer',
    )

    const fractional = withOverrides((rules) => ({
      ...rules,
      clocks: { ...rules.clocks, shotClockSeconds: 23.5 },
    }))
    expect(collectLeagueRulesIssues(fractional).map((i) => i.code)).toContain(
      'positive_integer',
    )
  })

  it('rejects an offensive-rebound reset longer than the full clock', () => {
    const broken = withOverrides((rules) => ({
      ...rules,
      clocks: { ...rules.clocks, offensiveReboundResetSeconds: 30 },
    }))
    expect(collectLeagueRulesIssues(broken).map((i) => i.code)).toContain(
      'shot_clock_order',
    )
  })

  it('rejects a backcourt limit longer than the shot clock', () => {
    const broken = withOverrides((rules) => ({
      ...rules,
      clocks: { ...rules.clocks, backcourtAdvanceSeconds: 25 },
    }))
    expect(collectLeagueRulesIssues(broken).map((i) => i.code)).toContain(
      'backcourt_length',
    )
  })

  it('rejects an overtime longer than a regulation period', () => {
    const broken = withOverrides((rules) => ({
      ...rules,
      overtime: { ...rules.overtime, secondsPerPeriod: 800 },
    }))
    expect(collectLeagueRulesIssues(broken).map((i) => i.code)).toContain(
      'overtime_length',
    )
  })

  it('rejects a late-period window longer than the period', () => {
    const broken = withOverrides((rules) => ({
      ...rules,
      teamFouls: {
        ...rules.teamFouls,
        latePeriodRule: {
          ...rules.teamFouls.latePeriodRule,
          windowSeconds: 900,
        },
      },
    }))
    expect(collectLeagueRulesIssues(broken).map((i) => i.code)).toContain(
      'late_period_window',
    )
  })

  it('throws a typed error carrying every issue', () => {
    const broken = withOverrides((rules) => ({
      ...rules,
      lineup: { ...rules.lineup, playersOnCourt: -1 },
    }))
    try {
      assertValidLeagueRules(broken)
      expect.unreachable('assertValidLeagueRules must throw')
    } catch (error) {
      expect(error).toBeInstanceOf(InvalidLeagueRulesError)
      if (error instanceof InvalidLeagueRulesError) {
        expect(error.issues.length).toBeGreaterThan(0)
      }
    }
  })
})
