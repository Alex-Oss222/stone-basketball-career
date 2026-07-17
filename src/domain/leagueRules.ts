/**
 * The versioned league rule pack (roadmap §8). NBA-style values for a
 * fictional league. The simulation reads rules, never scattered constants —
 * changing any value is a rules-version bump, and results record the rules
 * version they were produced under.
 *
 * Scope discipline: this object defines only what is LEGAL. Coaching intent
 * lives in RotationPlan; what actually happens is decided by the live
 * rotation engine (§9/§14). Strategy preferences (lineup balance, nine-man
 * rotations, who closes games) are deliberately not league rules.
 */
export const LEAGUE_RULES_VERSION = 1

export interface LeagueRulesV1 {
  readonly rulesVersion: typeof LEAGUE_RULES_VERSION

  readonly regulation: {
    readonly periodCount: number
    readonly secondsPerPeriod: number
  }

  readonly overtime: {
    readonly secondsPerPeriod: number
    /** Overtime repeats until one period ends with a winner. */
    readonly repeatUntilWinner: true
    /**
     * Termination guard, not a basketball rule: after this many tied full
     * overtime periods the deterministic sudden-death free-throw tiebreak
     * resolves the game. Approved product rule; unreachable in normal play.
     */
    readonly maxTiedPeriodsBeforeTiebreak: number
  }

  readonly lineup: {
    readonly playersOnCourt: number
    /** Personal fouls that disqualify a player. */
    readonly personalFoulLimit: number
    /** Players may leave and re-enter without limit. */
    readonly unlimitedReentry: true
  }

  readonly clocks: {
    readonly shotClockSeconds: number
    /** Shot clock after an offensive rebound off the rim. */
    readonly offensiveReboundResetSeconds: number
    /** Seconds to advance the ball past the backcourt line. */
    readonly backcourtAdvanceSeconds: number
  }

  readonly teamFouls: {
    /** Common team fouls per regulation period before the penalty applies. */
    readonly regulationNonPenaltyFouls: number
    /** Common team fouls per overtime period before the penalty applies. */
    readonly overtimeNonPenaltyFouls: number
    /**
     * Late-period rule: when a team is below the period quota, it is allowed
     * only this many non-penalty common fouls inside the closing window
     * before the penalty applies anyway.
     */
    readonly latePeriodRule: {
      readonly windowSeconds: number
      readonly nonPenaltyFoulsAllowedWhenBelowQuota: number
    }
    /** Offensive fouls count against the player, never toward the bonus. */
    readonly offensiveFoulsCountTowardBonus: false
  }

  readonly freeThrows: {
    readonly missedTwoPointShootingFoulAttempts: number
    readonly missedThreePointShootingFoulAttempts: number
    /** The and-one attempt when the fouled shot is made. */
    readonly madeBasketShootingFoulAttempts: number
    /** Attempts for a non-shooting foul once the team is in the penalty. */
    readonly penaltyFoulAttempts: number
  }

  readonly substitutions: {
    /** Substitutions happen only at legal dead-ball opportunities. */
    readonly requireDeadBall: true
  }
}

/**
 * The approved Milestone 1 pack: 4×12-minute quarters, 5-minute unlimited
 * overtime with the 20-OT guard, 24/14 shot clocks, 8-second backcourt, six
 * personal fouls, penalty on the 5th regulation team foul / 4th in overtime
 * with the final-2:00 single-foul rule, 2/3/1 shooting-foul free throws and
 * 2 in the penalty, dead-ball substitutions with unlimited re-entry.
 */
export const MILESTONE_1_LEAGUE_RULES: LeagueRulesV1 = Object.freeze({
  rulesVersion: LEAGUE_RULES_VERSION,
  regulation: Object.freeze({ periodCount: 4, secondsPerPeriod: 12 * 60 }),
  overtime: Object.freeze({
    secondsPerPeriod: 5 * 60,
    repeatUntilWinner: true,
    maxTiedPeriodsBeforeTiebreak: 20,
  }),
  lineup: Object.freeze({
    playersOnCourt: 5,
    personalFoulLimit: 6,
    unlimitedReentry: true,
  }),
  clocks: Object.freeze({
    shotClockSeconds: 24,
    offensiveReboundResetSeconds: 14,
    backcourtAdvanceSeconds: 8,
  }),
  teamFouls: Object.freeze({
    regulationNonPenaltyFouls: 4,
    overtimeNonPenaltyFouls: 3,
    latePeriodRule: Object.freeze({
      windowSeconds: 120,
      nonPenaltyFoulsAllowedWhenBelowQuota: 1,
    }),
    offensiveFoulsCountTowardBonus: false,
  }),
  freeThrows: Object.freeze({
    missedTwoPointShootingFoulAttempts: 2,
    missedThreePointShootingFoulAttempts: 3,
    madeBasketShootingFoulAttempts: 1,
    penaltyFoulAttempts: 2,
  }),
  substitutions: Object.freeze({ requireDeadBall: true }),
})

/**
 * Regulation player-seconds one team must account for — derived, never a
 * stored magic number. 4 × 720 × 5 = 14,400 (240 minutes) under the
 * Milestone 1 pack. A RotationPlan's planned minutes must total exactly this.
 */
export function deriveRegulationTeamSeconds(rules: LeagueRulesV1): number {
  return (
    rules.regulation.periodCount *
    rules.regulation.secondsPerPeriod *
    rules.lineup.playersOnCourt
  )
}

/** Additional player-seconds per overtime period — assigned at runtime by the
 * rotation engine, never edited into the saved regulation plan. */
export function deriveOvertimeTeamSeconds(rules: LeagueRulesV1): number {
  return rules.overtime.secondsPerPeriod * rules.lineup.playersOnCourt
}

export interface LeagueRulesIssue {
  readonly code: string
  readonly message: string
}

export class InvalidLeagueRulesError extends RangeError {
  readonly issues: readonly LeagueRulesIssue[]

  constructor(issues: readonly LeagueRulesIssue[]) {
    super(
      `Invalid league rules: ${issues
        .map((issue) => `${issue.code} — ${issue.message}`)
        .join('; ')}`,
    )
    this.name = 'InvalidLeagueRulesError'
    this.issues = issues
  }
}

export function collectLeagueRulesIssues(
  rules: LeagueRulesV1,
): readonly LeagueRulesIssue[] {
  const issues: LeagueRulesIssue[] = []
  const report = (code: string, message: string) => {
    issues.push({ code, message })
  }
  const requirePositiveInteger = (label: string, value: number) => {
    if (!Number.isSafeInteger(value) || value <= 0) {
      report('positive_integer', `${label} must be a positive integer`)
    }
  }
  const requireNonNegativeInteger = (label: string, value: number) => {
    if (!Number.isSafeInteger(value) || value < 0) {
      report('non_negative_integer', `${label} must be a non-negative integer`)
    }
  }

  if (rules.rulesVersion !== LEAGUE_RULES_VERSION) {
    report(
      'rules_version',
      `rulesVersion must be ${LEAGUE_RULES_VERSION}; got ${rules.rulesVersion}`,
    )
  }

  requirePositiveInteger('regulation.periodCount', rules.regulation.periodCount)
  requirePositiveInteger(
    'regulation.secondsPerPeriod',
    rules.regulation.secondsPerPeriod,
  )
  requirePositiveInteger(
    'overtime.secondsPerPeriod',
    rules.overtime.secondsPerPeriod,
  )
  requirePositiveInteger(
    'overtime.maxTiedPeriodsBeforeTiebreak',
    rules.overtime.maxTiedPeriodsBeforeTiebreak,
  )
  requirePositiveInteger('lineup.playersOnCourt', rules.lineup.playersOnCourt)
  requirePositiveInteger(
    'lineup.personalFoulLimit',
    rules.lineup.personalFoulLimit,
  )
  requirePositiveInteger('clocks.shotClockSeconds', rules.clocks.shotClockSeconds)
  requirePositiveInteger(
    'clocks.offensiveReboundResetSeconds',
    rules.clocks.offensiveReboundResetSeconds,
  )
  requirePositiveInteger(
    'clocks.backcourtAdvanceSeconds',
    rules.clocks.backcourtAdvanceSeconds,
  )
  requireNonNegativeInteger(
    'teamFouls.regulationNonPenaltyFouls',
    rules.teamFouls.regulationNonPenaltyFouls,
  )
  requireNonNegativeInteger(
    'teamFouls.overtimeNonPenaltyFouls',
    rules.teamFouls.overtimeNonPenaltyFouls,
  )
  requirePositiveInteger(
    'teamFouls.latePeriodRule.windowSeconds',
    rules.teamFouls.latePeriodRule.windowSeconds,
  )
  requireNonNegativeInteger(
    'teamFouls.latePeriodRule.nonPenaltyFoulsAllowedWhenBelowQuota',
    rules.teamFouls.latePeriodRule.nonPenaltyFoulsAllowedWhenBelowQuota,
  )
  requirePositiveInteger(
    'freeThrows.missedTwoPointShootingFoulAttempts',
    rules.freeThrows.missedTwoPointShootingFoulAttempts,
  )
  requirePositiveInteger(
    'freeThrows.missedThreePointShootingFoulAttempts',
    rules.freeThrows.missedThreePointShootingFoulAttempts,
  )
  requirePositiveInteger(
    'freeThrows.madeBasketShootingFoulAttempts',
    rules.freeThrows.madeBasketShootingFoulAttempts,
  )
  requirePositiveInteger(
    'freeThrows.penaltyFoulAttempts',
    rules.freeThrows.penaltyFoulAttempts,
  )

  if (
    rules.clocks.offensiveReboundResetSeconds > rules.clocks.shotClockSeconds
  ) {
    report(
      'shot_clock_order',
      'The offensive-rebound reset cannot exceed the full shot clock',
    )
  }
  if (rules.clocks.shotClockSeconds > rules.regulation.secondsPerPeriod) {
    report('shot_clock_length', 'The shot clock cannot exceed the period length')
  }
  if (rules.clocks.backcourtAdvanceSeconds > rules.clocks.shotClockSeconds) {
    report(
      'backcourt_length',
      'The backcourt advance limit cannot exceed the shot clock',
    )
  }
  if (rules.overtime.secondsPerPeriod > rules.regulation.secondsPerPeriod) {
    report(
      'overtime_length',
      'An overtime period cannot be longer than a regulation period',
    )
  }
  if (
    rules.teamFouls.latePeriodRule.windowSeconds >
    rules.regulation.secondsPerPeriod
  ) {
    report(
      'late_period_window',
      'The late-period foul window cannot exceed the period length',
    )
  }

  return issues
}

/** Throws InvalidLeagueRulesError unless the pack is internally consistent. */
export function assertValidLeagueRules(rules: LeagueRulesV1): void {
  const issues = collectLeagueRulesIssues(rules)
  if (issues.length > 0) {
    throw new InvalidLeagueRulesError(issues)
  }
}
