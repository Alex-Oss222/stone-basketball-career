import type { PlayerId, TeamId } from './ids'
import type { Player } from './league'
import type { LeagueRulesV1 } from './leagueRules'
import { deriveRegulationTeamSeconds } from './leagueRules'
import { selectRotationAbility } from './rotationAbility'
import { addIssue } from './validationIssue'
import type { ValidationIssue } from './validationIssue'

/**
 * §8 — `RotationPlanV1`: what the coach *intends* (starters + a regulation
 * minute target per player + a bench-priority order). Distinct from the league
 * rules (what is legal, `leagueRules.ts`) and from the live rotation engine
 * (what actually happens at each dead ball, §9/§14). Pure and deterministic:
 * no wall-clock timestamps live in the plan, and identical roster + rules
 * produce a deeply-equal generated plan.
 *
 * Minutes are stored as **integer seconds** so the plan composes with
 * `deriveRegulationTeamSeconds(rules)`; V1 keeps every target a whole number of
 * minutes. `source` is the ownership boundary — a `user-edited` plan is never
 * overwritten by background CPU regeneration.
 *
 * The reward-peaks Overall never enters here; the CPU generator ranks players
 * through the versioned `selectRotationAbility` selector (`rotationAbility.ts`),
 * separate from the display Overall so a UI recalibration can never move a plan.
 *
 * §8A extension points (not built here): the `generation` metadata gains a
 * `coachProfileId`/version, generation gains a per-team seeded *exploration*
 * stream, and roster repair gains the conservative minimum-disturbance path.
 */
export const ROTATION_PLAN_VERSION = 1 as const
export type RotationPlanVersion = typeof ROTATION_PLAN_VERSION

export const ROTATION_GENERATOR_VERSION = 'rotation-generator-v1' as const
export const ROTATION_REPAIR_VERSION = 'rotation-repair-v1' as const

export const SECONDS_PER_MINUTE = 60
/** A player may be planned for at most a full regulation game. */
export const MAX_PLAYER_REGULATION_MINUTES = 48
/** A legal regulation lineup, and therefore the exact starter count. */
export const STARTERS_REQUIRED = 5
/** The CPU default rotation depth (a coach-independent §8 baseline). */
export const DEFAULT_ROTATION_SIZE = 9

/**
 * The coach-independent default nine-man workload template (whole minutes,
 * sums to 240 under the Milestone 1 pack). Treated as *weights* and normalized
 * to whatever `deriveRegulationTeamSeconds` derives, so a rules change never
 * leaves a plan off-total. §8A replaces this with per-coach basis-point shares.
 */
export const DEFAULT_ROTATION_MINUTE_TEMPLATE = [
  34, 33, 32, 31, 28, 24, 22, 20, 16,
] as const

/** Warning thresholds — display-only; never make a legal plan unsavable. */
export const STARTER_LOW_MINUTES_THRESHOLD = 12
export const DEEP_ROTATION_PLAYER_COUNT = 10
/** Baseline weights repair gives to a starter / bench player with no prior minutes. */
const REPAIR_STARTER_BASELINE_MINUTES = 28
const REPAIR_BENCH_BASELINE_MINUTES = 16

export const ROTATION_PLAN_SOURCES = ['cpu-generated', 'user-edited'] as const
export type RotationPlanSource = (typeof ROTATION_PLAN_SOURCES)[number]

export interface RotationPlanGenerationMeta {
  readonly generatorVersion: typeof ROTATION_GENERATOR_VERSION
}

/** §8 repair reasons; §8A adds `'player-unavailable'` for temporary absences. */
export const ROTATION_REPAIR_REASONS = [
  'player-removed',
  'starter-ineligible',
] as const
export type RotationRepairReason = (typeof ROTATION_REPAIR_REASONS)[number]

export interface RotationPlanAutoRepairMeta {
  readonly repairVersion: typeof ROTATION_REPAIR_VERSION
  readonly reason: RotationRepairReason
}

export interface RotationPlanV1 {
  readonly version: RotationPlanVersion
  readonly teamId: TeamId
  /** Exactly five unique, on-roster player ids (validated, not type-enforced). */
  readonly starters: readonly PlayerId[]
  /** Integer seconds per roster player; whole minutes in V1; sums to the derived total. */
  readonly minuteTargetsSeconds: Readonly<Record<PlayerId, number>>
  /** Non-starter rotation players in descending priority (repair fills vacancies from here first). */
  readonly benchOrder: readonly PlayerId[]
  readonly source: RotationPlanSource
  readonly generation?: RotationPlanGenerationMeta
  readonly autoRepair?: RotationPlanAutoRepairMeta
}

/** Structured, machine-readable validation codes so the editor can pinpoint each issue. */
export const ROTATION_PLAN_ERROR_CODES = {
  version: 'rotation-plan/version',
  starterCount: 'rotation-plan/starter-count',
  duplicateStarter: 'rotation-plan/duplicate-starter',
  starterNotOnRoster: 'rotation-plan/starter-not-on-roster',
  targetNotOnRoster: 'rotation-plan/target-not-on-roster',
  minuteNotWhole: 'rotation-plan/minute-not-whole',
  minuteOutOfRange: 'rotation-plan/minute-out-of-range',
  minuteTotal: 'rotation-plan/minute-total',
  starterZeroMinutes: 'rotation-plan/starter-zero-minutes',
  tooFewPlayers: 'rotation-plan/too-few-players',
  benchOrderDuplicate: 'rotation-plan/bench-order-duplicate',
  benchOrderNotOnRoster: 'rotation-plan/bench-order-not-on-roster',
} as const

export const ROTATION_PLAN_WARNING_CODES = {
  onlyFivePlayers: 'rotation-plan/only-five-players',
  playerAtMax: 'rotation-plan/player-at-max',
  starterLowMinutes: 'rotation-plan/starter-low-minutes',
  deepRotation: 'rotation-plan/deep-rotation',
} as const

/**
 * The two tiers Alex approved (rotation.txt §7): **errors** block the save;
 * **warnings** flag a legal-but-unusual plan the user may still save on
 * purpose. The coach never "corrects" a valid plan it merely dislikes.
 */
export interface RotationPlanValidation {
  readonly errors: readonly ValidationIssue[]
  readonly warnings: readonly ValidationIssue[]
}

/** `validateRotationPlan` takes no coach profile — legality never depends on style. */
export function validateRotationPlan(
  plan: RotationPlanV1,
  roster: readonly Player[],
  rules: LeagueRulesV1,
): RotationPlanValidation {
  const errors: ValidationIssue[] = []
  const warnings: ValidationIssue[] = []

  const rosterIds = new Set<PlayerId>(roster.map((player) => player.id))
  const regulationSeconds = deriveRegulationTeamSeconds(rules)
  const maxPlayerSeconds = MAX_PLAYER_REGULATION_MINUTES * SECONDS_PER_MINUTE

  if (plan.version !== ROTATION_PLAN_VERSION) {
    addIssue(
      errors,
      ROTATION_PLAN_ERROR_CODES.version,
      'version',
      `Rotation plan version must be ${ROTATION_PLAN_VERSION}`,
    )
  }

  if (plan.starters.length !== STARTERS_REQUIRED) {
    addIssue(
      errors,
      ROTATION_PLAN_ERROR_CODES.starterCount,
      'starters',
      `A rotation needs exactly ${STARTERS_REQUIRED} starters; found ${plan.starters.length}`,
    )
  }
  const seenStarter = new Set<PlayerId>()
  plan.starters.forEach((id, index) => {
    if (seenStarter.has(id)) {
      addIssue(
        errors,
        ROTATION_PLAN_ERROR_CODES.duplicateStarter,
        `starters[${index}]`,
        `${id} appears more than once in the starting lineup`,
      )
    }
    seenStarter.add(id)
    if (!rosterIds.has(id)) {
      addIssue(
        errors,
        ROTATION_PLAN_ERROR_CODES.starterNotOnRoster,
        `starters[${index}]`,
        `Starter ${id} is not on the roster`,
      )
    }
  })

  const entries = Object.entries(plan.minuteTargetsSeconds) as [
    PlayerId,
    number,
  ][]
  let totalSeconds = 0
  let positiveMinutePlayers = 0
  for (const [id, seconds] of entries) {
    const path = `minuteTargetsSeconds.${id}`
    if (!rosterIds.has(id)) {
      addIssue(
        errors,
        ROTATION_PLAN_ERROR_CODES.targetNotOnRoster,
        path,
        `${id} has planned minutes but is not on the roster`,
      )
    }
    if (
      !Number.isSafeInteger(seconds) ||
      seconds % SECONDS_PER_MINUTE !== 0
    ) {
      addIssue(
        errors,
        ROTATION_PLAN_ERROR_CODES.minuteNotWhole,
        path,
        `Minutes for ${id} must be a whole number`,
      )
    }
    if (seconds < 0 || seconds > maxPlayerSeconds) {
      addIssue(
        errors,
        ROTATION_PLAN_ERROR_CODES.minuteOutOfRange,
        path,
        `Minutes for ${id} must be between 0 and ${MAX_PLAYER_REGULATION_MINUTES}`,
      )
    }
    totalSeconds += seconds
    if (seconds > 0) {
      positiveMinutePlayers += 1
    }
  }

  if (totalSeconds !== regulationSeconds) {
    addIssue(
      errors,
      ROTATION_PLAN_ERROR_CODES.minuteTotal,
      'minuteTargetsSeconds',
      `Planned minutes total ${secondsToMinutes(totalSeconds)}; the rotation requires exactly ${secondsToMinutes(regulationSeconds)}`,
    )
  }
  if (positiveMinutePlayers < STARTERS_REQUIRED) {
    addIssue(
      errors,
      ROTATION_PLAN_ERROR_CODES.tooFewPlayers,
      'minuteTargetsSeconds',
      `At least ${STARTERS_REQUIRED} players must have minutes; found ${positiveMinutePlayers}`,
    )
  }

  plan.starters.forEach((id, index) => {
    const seconds = plan.minuteTargetsSeconds[id] ?? 0
    if (seconds <= 0) {
      addIssue(
        errors,
        ROTATION_PLAN_ERROR_CODES.starterZeroMinutes,
        `starters[${index}]`,
        `Starter ${id} must be planned for positive minutes`,
      )
    }
  })

  const seenBench = new Set<PlayerId>()
  plan.benchOrder.forEach((id, index) => {
    if (seenBench.has(id)) {
      addIssue(
        errors,
        ROTATION_PLAN_ERROR_CODES.benchOrderDuplicate,
        `benchOrder[${index}]`,
        `${id} appears more than once in the bench order`,
      )
    }
    seenBench.add(id)
    if (!rosterIds.has(id)) {
      addIssue(
        errors,
        ROTATION_PLAN_ERROR_CODES.benchOrderNotOnRoster,
        `benchOrder[${index}]`,
        `Bench player ${id} is not on the roster`,
      )
    }
  })

  // Warnings — legal, saveable, but worth a second look.
  if (positiveMinutePlayers === STARTERS_REQUIRED) {
    addIssue(
      warnings,
      ROTATION_PLAN_WARNING_CODES.onlyFivePlayers,
      'minuteTargetsSeconds',
      'Only five players have minutes; a real game usually needs bench depth',
    )
  }
  for (const [id, seconds] of entries) {
    if (seconds === maxPlayerSeconds) {
      addIssue(
        warnings,
        ROTATION_PLAN_WARNING_CODES.playerAtMax,
        `minuteTargetsSeconds.${id}`,
        `${id} is planned for the full ${MAX_PLAYER_REGULATION_MINUTES} minutes`,
      )
    }
  }
  plan.starters.forEach((id, index) => {
    const minutes = secondsToMinutes(plan.minuteTargetsSeconds[id] ?? 0)
    if (minutes > 0 && minutes < STARTER_LOW_MINUTES_THRESHOLD) {
      addIssue(
        warnings,
        ROTATION_PLAN_WARNING_CODES.starterLowMinutes,
        `starters[${index}]`,
        `Starter ${id} is planned for only ${minutes} minutes`,
      )
    }
  })
  if (positiveMinutePlayers > DEEP_ROTATION_PLAYER_COUNT) {
    addIssue(
      warnings,
      ROTATION_PLAN_WARNING_CODES.deepRotation,
      'minuteTargetsSeconds',
      `${positiveMinutePlayers} players have minutes; that is an unusually deep rotation`,
    )
  }

  return { errors, warnings }
}

/** True when the plan has no blocking errors (warnings are allowed). */
export function isRotationPlanValid(
  plan: RotationPlanV1,
  roster: readonly Player[],
  rules: LeagueRulesV1,
): boolean {
  return validateRotationPlan(plan, roster, rules).errors.length === 0
}

export interface GenerateRotationPlanInput {
  readonly teamId: TeamId
  readonly roster: readonly Player[]
  readonly rules: LeagueRulesV1
}

/**
 * Deterministic CPU rotation plan (§8 default, coach-independent). Ranks the
 * team's players by the versioned rotation-ability selector with a playerId
 * tie-break, starts the top five, spreads the default template across the top
 * `DEFAULT_ROTATION_SIZE`, and normalizes to exactly the derived regulation
 * minutes. No randomness — §8A layers the per-coach seeded exploration on top.
 * Team processing order never changes a team's output.
 */
export function generateRotationPlan(
  input: GenerateRotationPlanInput,
): RotationPlanV1 {
  const { teamId, rules } = input
  const teamPlayers = input.roster.filter((player) => player.teamId === teamId)
  if (teamPlayers.length < STARTERS_REQUIRED) {
    throw new RangeError(
      `A rotation needs at least ${STARTERS_REQUIRED} players; team ${teamId} has ${teamPlayers.length}`,
    )
  }

  const ranked = rankPlayersByAbility(teamPlayers)
  const rotationSize = Math.min(DEFAULT_ROTATION_SIZE, ranked.length)
  const rotationPlayers = ranked.slice(0, rotationSize)
  const starters = rotationPlayers
    .slice(0, STARTERS_REQUIRED)
    .map((player) => player.id)

  const weights = new Map<PlayerId, number>()
  rotationPlayers.forEach((player, index) => {
    weights.set(player.id, DEFAULT_ROTATION_MINUTE_TEMPLATE[index] ?? 1)
  })
  const minutes = allocateWholeMinutes(
    weights,
    regulationMinutes(rules),
    rotationPlayers.map((player) => player.id),
  )

  const benchOrder = rotationPlayers
    .slice(STARTERS_REQUIRED)
    .filter((player) => (minutes.get(player.id) ?? 0) > 0)
    .map((player) => player.id)

  return {
    version: ROTATION_PLAN_VERSION,
    teamId,
    starters,
    minuteTargetsSeconds: buildSecondsRecord(teamPlayers, minutes),
    benchOrder,
    source: 'cpu-generated',
    generation: { generatorVersion: ROTATION_GENERATOR_VERSION },
  }
}

export interface RepairRotationPlanInput {
  readonly plan: RotationPlanV1
  readonly roster: readonly Player[]
  readonly rules: LeagueRulesV1
}

export interface RepairRotationPlanResult {
  readonly plan: RotationPlanV1
  readonly repaired: boolean
}

/**
 * Reconciles a saved plan with a changed roster (a *permanent* change — trade,
 * release, retirement). Removes departed players, keeps every survivor's
 * starter status, fills starter vacancies (a `user-edited` plan drains its own
 * bench order first, a CPU plan uses ability), then re-normalizes to exactly the
 * derived regulation minutes and re-validates. Returns the plan untouched when
 * nothing needs fixing. `source` is preserved; the result is marked
 * auto-repaired. (Temporary one-game absences are §9's overlay, never a repair.)
 */
export function repairRotationPlan(
  input: RepairRotationPlanInput,
): RepairRotationPlanResult {
  const { plan, rules } = input
  const teamPlayers = input.roster.filter(
    (player) => player.teamId === plan.teamId,
  )
  const rosterIds = new Set<PlayerId>(teamPlayers.map((player) => player.id))

  const removedTargets = (
    Object.keys(plan.minuteTargetsSeconds) as PlayerId[]
  ).filter((id) => !rosterIds.has(id))
  const starterOffRoster = plan.starters.some((id) => !rosterIds.has(id))
  const alreadyValid =
    validateRotationPlan(plan, teamPlayers, rules).errors.length === 0

  if (removedTargets.length === 0 && !starterOffRoster && alreadyValid) {
    return { plan, repaired: false }
  }
  if (teamPlayers.length < STARTERS_REQUIRED) {
    throw new RangeError(
      `Cannot repair a rotation for team ${plan.teamId}: only ${teamPlayers.length} players remain`,
    )
  }

  const ranked = rankPlayersByAbility(teamPlayers)
  const survivingStarters = plan.starters.filter((id) => rosterIds.has(id))
  const newStarters = fillStarterVacancies(
    survivingStarters,
    plan,
    ranked,
    rosterIds,
  )
  const starterSet = new Set<PlayerId>(newStarters)

  // Rotation pool: starters + surviving players who still have minutes, topped
  // up from ability order to the default depth so the plan keeps real bench.
  const poolOrder: PlayerId[] = [...newStarters]
  const inPool = new Set<PlayerId>(newStarters)
  const addToPool = (id: PlayerId) => {
    if (!inPool.has(id)) {
      inPool.add(id)
      poolOrder.push(id)
    }
  }
  for (const player of ranked) {
    if (
      !starterSet.has(player.id) &&
      (plan.minuteTargetsSeconds[player.id] ?? 0) > 0
    ) {
      addToPool(player.id)
    }
  }
  for (const player of ranked) {
    if (poolOrder.length >= Math.min(DEFAULT_ROTATION_SIZE, ranked.length)) {
      break
    }
    addToPool(player.id)
  }

  // Weights preserve each survivor's minutes; replacements take a role baseline.
  const weights = new Map<PlayerId, number>()
  for (const id of poolOrder) {
    const existingMinutes = secondsToMinutes(
      plan.minuteTargetsSeconds[id] ?? 0,
    )
    if (existingMinutes > 0) {
      weights.set(id, existingMinutes)
    } else {
      weights.set(
        id,
        starterSet.has(id)
          ? REPAIR_STARTER_BASELINE_MINUTES
          : REPAIR_BENCH_BASELINE_MINUTES,
      )
    }
  }
  const minutes = allocateWholeMinutes(weights, regulationMinutes(rules), poolOrder)

  const benchOrder = poolOrder.filter(
    (id) => !starterSet.has(id) && (minutes.get(id) ?? 0) > 0,
  )

  const repairedPlan: RotationPlanV1 = {
    version: ROTATION_PLAN_VERSION,
    teamId: plan.teamId,
    starters: newStarters,
    minuteTargetsSeconds: buildSecondsRecord(teamPlayers, minutes),
    benchOrder,
    source: plan.source,
    ...(plan.generation === undefined ? {} : { generation: plan.generation }),
    autoRepair: {
      repairVersion: ROTATION_REPAIR_VERSION,
      reason: starterOffRoster ? 'starter-ineligible' : 'player-removed',
    },
  }

  return { plan: repairedPlan, repaired: true }
}

/** Whole-minute target for one player, for view models and the editor. */
export function plannedMinutes(
  plan: RotationPlanV1,
  playerId: PlayerId,
): number {
  return secondsToMinutes(plan.minuteTargetsSeconds[playerId] ?? 0)
}

/** The derived regulation team minutes a plan must total (240 under Milestone 1). */
export function regulationMinutes(rules: LeagueRulesV1): number {
  return secondsToMinutes(deriveRegulationTeamSeconds(rules))
}

/**
 * Deterministic capped largest-remainder allocator (60-second granularity):
 * floor each weight's share of `totalMinutes`, cap at a full game, then hand out
 * the remainder by descending fractional part with the supplied id order as the
 * final tie-break. Never float-accumulates and patches the last player. Reused
 * by generation and repair, and by §8A's basis-point workload shares.
 */
export function allocateWholeMinutes(
  weights: ReadonlyMap<PlayerId, number>,
  totalMinutes: number,
  order: readonly PlayerId[],
): Map<PlayerId, number> {
  const ids = order.filter((id) => weights.has(id))
  const result = new Map<PlayerId, number>()
  if (ids.length === 0) {
    return result
  }

  const orderIndex = new Map<PlayerId, number>()
  ids.forEach((id, index) => orderIndex.set(id, index))

  const totalWeight = ids.reduce((sum, id) => sum + (weights.get(id) ?? 0), 0)
  const fractional = new Map<PlayerId, number>()
  let assigned = 0

  for (const id of ids) {
    const exact =
      totalWeight > 0
        ? ((weights.get(id) ?? 0) / totalWeight) * totalMinutes
        : totalMinutes / ids.length
    const floored = Math.min(Math.floor(exact), MAX_PLAYER_REGULATION_MINUTES)
    result.set(id, floored)
    fractional.set(id, exact - Math.floor(exact))
    assigned += floored
  }

  const byRemainder = [...ids].sort((a, b) => {
    const fractionDelta = (fractional.get(b) ?? 0) - (fractional.get(a) ?? 0)
    if (fractionDelta !== 0) {
      return fractionDelta
    }
    return (orderIndex.get(a) ?? 0) - (orderIndex.get(b) ?? 0)
  })

  let leftover = totalMinutes - assigned
  while (leftover > 0) {
    let advanced = false
    for (const id of byRemainder) {
      if (leftover <= 0) {
        break
      }
      const current = result.get(id) ?? 0
      if (current < MAX_PLAYER_REGULATION_MINUTES) {
        result.set(id, current + 1)
        leftover -= 1
        advanced = true
      }
    }
    if (!advanced) {
      break
    }
  }

  return result
}

function rankPlayersByAbility(
  players: readonly Player[],
): readonly Player[] {
  return [...players].sort((a, b) => {
    const abilityA = selectRotationAbility(a.ratings, a.primaryPosition).ability
    const abilityB = selectRotationAbility(b.ratings, b.primaryPosition).ability
    if (abilityB !== abilityA) {
      return abilityB - abilityA
    }
    return comparePlayerIds(a.id, b.id)
  })
}

function fillStarterVacancies(
  survivingStarters: readonly PlayerId[],
  plan: RotationPlanV1,
  ranked: readonly Player[],
  rosterIds: ReadonlySet<PlayerId>,
): readonly PlayerId[] {
  const starters = [...survivingStarters]
  const chosen = new Set<PlayerId>(starters)

  const preferred =
    plan.source === 'user-edited'
      ? plan.benchOrder.filter(
          (id) => rosterIds.has(id) && !chosen.has(id),
        )
      : []
  const candidateOrder: PlayerId[] = [
    ...preferred,
    ...ranked
      .map((player) => player.id)
      .filter((id) => !chosen.has(id) && !preferred.includes(id)),
  ]

  for (const id of candidateOrder) {
    if (starters.length >= STARTERS_REQUIRED) {
      break
    }
    starters.push(id)
    chosen.add(id)
  }
  return starters
}

function buildSecondsRecord(
  players: readonly Player[],
  minutesByPlayer: ReadonlyMap<PlayerId, number>,
): Readonly<Record<PlayerId, number>> {
  const record: Record<string, number> = {}
  for (const player of players) {
    record[player.id] =
      (minutesByPlayer.get(player.id) ?? 0) * SECONDS_PER_MINUTE
  }
  return record as Readonly<Record<PlayerId, number>>
}

function secondsToMinutes(seconds: number): number {
  return Math.round(seconds / SECONDS_PER_MINUTE)
}

function comparePlayerIds(a: PlayerId, b: PlayerId): number {
  return a < b ? -1 : a > b ? 1 : 0
}
