import type { ScheduleId, ScheduleRuleSetId, SeasonId } from '../domain/ids'
import type { TeamId } from '../domain/ids'
import {
  MILESTONE_1_REGULAR_SEASON_RULE_SET,
} from '../domain/schedule'
import type { ScheduleRuleSet } from '../domain/schedule'
import {
  SCHEDULE_GENERATION_VERSION,
  deriveStableScheduleId,
} from '../generation/generateSchedule'

export interface PersistedScheduleIdentityInput {
  readonly seasonId: SeasonId
  readonly teams: readonly { readonly id: TeamId }[]
  readonly scheduleSeed: string
}

export interface SupportedScheduleRuleSetRegistration {
  readonly ruleSet: ScheduleRuleSet
  readonly scheduleGenerationVersion: number
  readonly deriveScheduleId: (
    input: PersistedScheduleIdentityInput,
  ) => ScheduleId
}

const MILESTONE_1_REGISTRATION: SupportedScheduleRuleSetRegistration =
  Object.freeze({
    ruleSet: MILESTONE_1_REGULAR_SEASON_RULE_SET,
    scheduleGenerationVersion: SCHEDULE_GENERATION_VERSION,
    deriveScheduleId: (input: PersistedScheduleIdentityInput) =>
      deriveStableScheduleId({
        ...input,
        ruleSet: MILESTONE_1_REGULAR_SEASON_RULE_SET,
      }),
  })

/**
 * Historical persistence support is explicit and keyed by both ID and
 * version. Only rule sets genuinely implemented by the codebase belong here.
 */
export const SUPPORTED_SCHEDULE_RULE_SET_REGISTRATIONS = Object.freeze([
  MILESTONE_1_REGISTRATION,
])

export function findSupportedScheduleRuleSet(
  id: ScheduleRuleSetId,
  version: number,
): SupportedScheduleRuleSetRegistration | null {
  return (
    SUPPORTED_SCHEDULE_RULE_SET_REGISTRATIONS.find(
      ({ ruleSet }) => ruleSet.id === id && ruleSet.version === version,
    ) ?? null
  )
}

export function hasRegisteredScheduleRuleSetId(
  id: ScheduleRuleSetId,
): boolean {
  return SUPPORTED_SCHEDULE_RULE_SET_REGISTRATIONS.some(
    ({ ruleSet }) => ruleSet.id === id,
  )
}
