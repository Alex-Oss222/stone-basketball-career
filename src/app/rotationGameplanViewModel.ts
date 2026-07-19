import type { PlayerId, TeamId } from '../domain/ids'
import type { Player } from '../domain/league'
import type { LeagueRulesV1 } from '../domain/leagueRules'
import {
  SECONDS_PER_MINUTE,
  STARTERS_REQUIRED,
  generateRotationPlan,
  repairRotationPlan,
} from '../domain/rotationPlan'
import type { RotationPlanSource, RotationPlanV1 } from '../domain/rotationPlan'

/**
 * The plan the Adjust Rotation editor opens on: the team's saved plan
 * (reconciled with the current roster) if one exists, otherwise a freshly
 * generated CPU default. The default is shown, never persisted, until the user
 * saves — matching the §8 "Auto Rotation previews; Save protects" contract.
 */
export function resolveRotationPlan(
  roster: readonly Player[],
  teamId: TeamId,
  savedPlan: RotationPlanV1 | null,
  rules: LeagueRulesV1,
): RotationPlanV1 {
  if (savedPlan === null) {
    return generateRotationPlan({ teamId, roster, rules })
  }
  return repairRotationPlan({ plan: savedPlan, roster, rules }).plan
}

/**
 * Editor working state: one ordered depth chart (every roster player, highest
 * priority first) plus each player's whole-minute target. The **top five of the
 * order are the starters** — the coach sets them by moving players up, not by a
 * toggle. Bench priority is simply the order after the fifth slot.
 */
export interface RotationDraft {
  readonly order: readonly PlayerId[]
  readonly minutesByPlayer: Readonly<Record<PlayerId, number>>
}

export function draftFromPlan(
  plan: RotationPlanV1,
  roster: readonly Player[],
): RotationDraft {
  const minutesByPlayer: Record<string, number> = {}
  for (const player of roster) {
    minutesByPlayer[player.id] = Math.round(
      (plan.minuteTargetsSeconds[player.id] ?? 0) / SECONDS_PER_MINUTE,
    )
  }

  const listed = new Set<PlayerId>([...plan.starters, ...plan.benchOrder])
  const remaining = roster
    .filter((player) => !listed.has(player.id))
    .sort((a, b) => {
      const minutesDelta =
        (minutesByPlayer[b.id] ?? 0) - (minutesByPlayer[a.id] ?? 0)
      if (minutesDelta !== 0) {
        return minutesDelta
      }
      return a.id < b.id ? -1 : a.id > b.id ? 1 : 0
    })
    .map((player) => player.id)

  return {
    order: dedupeToRoster([...plan.starters, ...plan.benchOrder, ...remaining], roster),
    minutesByPlayer: minutesByPlayer as Readonly<Record<PlayerId, number>>,
  }
}

/** The roster in board order (the draft's depth chart, starters first). */
export function displayOrder(
  draft: RotationDraft,
  roster: readonly Player[],
): readonly Player[] {
  const byId = new Map<PlayerId, Player>(
    roster.map((player) => [player.id, player]),
  )
  const seen = new Set<PlayerId>()
  const ordered: Player[] = []
  for (const id of draft.order) {
    const player = byId.get(id)
    if (player !== undefined && !seen.has(id)) {
      seen.add(id)
      ordered.push(player)
    }
  }
  for (const player of roster) {
    if (!seen.has(player.id)) {
      ordered.push(player)
    }
  }
  return ordered
}

/**
 * Rebuilds a plan from editor state: the top five of the order are the starters,
 * the playing players after that (in order) are the bench, and whole minutes
 * become integer seconds for every roster player.
 */
export function planFromDraft(
  draft: RotationDraft,
  teamId: TeamId,
  roster: readonly Player[],
  source: RotationPlanSource,
): RotationPlanV1 {
  const order = dedupeToRoster(draft.order, roster)
  const minuteTargetsSeconds: Record<string, number> = {}
  for (const player of roster) {
    minuteTargetsSeconds[player.id] =
      (draft.minutesByPlayer[player.id] ?? 0) * SECONDS_PER_MINUTE
  }
  const benchOrder = order
    .slice(STARTERS_REQUIRED)
    .filter((id) => (draft.minutesByPlayer[id] ?? 0) > 0)

  return {
    version: 1,
    teamId,
    starters: order.slice(0, STARTERS_REQUIRED),
    minuteTargetsSeconds: minuteTargetsSeconds as Readonly<
      Record<PlayerId, number>
    >,
    benchOrder,
    source,
  }
}

/** Swap a player one slot up (`-1`) or down (`1`) in the depth chart. */
export function reorder(
  order: readonly PlayerId[],
  playerId: PlayerId,
  direction: -1 | 1,
): readonly PlayerId[] {
  const from = order.indexOf(playerId)
  const to = from + direction
  if (from < 0 || to < 0 || to >= order.length) {
    return order
  }
  const next = [...order]
  const moved = next[from]
  const displaced = next[to]
  if (moved === undefined || displaced === undefined) {
    return order
  }
  next[from] = displaced
  next[to] = moved
  return next
}

/** Move a player to an absolute index in the depth chart (drag-and-drop). */
export function moveToIndex(
  order: readonly PlayerId[],
  playerId: PlayerId,
  toIndex: number,
): readonly PlayerId[] {
  const from = order.indexOf(playerId)
  if (from < 0) {
    return order
  }
  const next = [...order]
  next.splice(from, 1)
  const clamped = Math.max(0, Math.min(toIndex, next.length))
  next.splice(clamped, 0, playerId)
  return next
}

export const ROTATION_TIERS = [
  'Starter',
  'Sixth Man',
  'Rotation',
  'Bench',
  'Reserve',
] as const
export type RotationTier = (typeof ROTATION_TIERS)[number]

/**
 * The player's rotation tier from their depth-chart rank: the five starters,
 * then the top bench player (Sixth Man), the next few (Rotation), the rest of
 * the playing bench (Bench), and everyone at zero minutes (Reserve).
 */
export function deriveRotationTier(
  draft: RotationDraft,
  playerId: PlayerId,
): RotationTier {
  const index = draft.order.indexOf(playerId)
  if (index >= 0 && index < STARTERS_REQUIRED) {
    return 'Starter'
  }
  if ((draft.minutesByPlayer[playerId] ?? 0) <= 0) {
    return 'Reserve'
  }
  const benchRank = index - STARTERS_REQUIRED
  if (benchRank === 0) {
    return 'Sixth Man'
  }
  if (benchRank >= 1 && benchRank <= 3) {
    return 'Rotation'
  }
  return 'Bench'
}

/** Splits whole-game minutes evenly across periods (largest-remainder). */
export function minutesByPeriod(
  totalMinutes: number,
  periods: number,
): readonly number[] {
  if (periods <= 0) {
    return []
  }
  const base = Math.floor(totalMinutes / periods)
  let remainder = totalMinutes - base * periods
  const result: number[] = []
  for (let period = 0; period < periods; period += 1) {
    result.push(base + (remainder > 0 ? 1 : 0))
    if (remainder > 0) {
      remainder -= 1
    }
  }
  return result
}

export function totalDraftMinutes(
  draft: RotationDraft,
  roster: readonly Player[],
): number {
  return roster.reduce(
    (sum, player) => sum + (draft.minutesByPlayer[player.id] ?? 0),
    0,
  )
}

export function rotationPlayerCount(
  draft: RotationDraft,
  roster: readonly Player[],
): number {
  return roster.reduce(
    (count, player) =>
      (draft.minutesByPlayer[player.id] ?? 0) > 0 ? count + 1 : count,
    0,
  )
}

/**
 * A stable content signature for a saved plan, used as the editor's React key so
 * it re-initializes only when the persisted plan actually changes.
 */
export function rotationPlanSignature(plan: RotationPlanV1 | null): string {
  if (plan === null) {
    return 'none'
  }
  const minutes = Object.keys(plan.minuteTargetsSeconds)
    .sort()
    .map((id) => `${id}:${plan.minuteTargetsSeconds[id as PlayerId] ?? 0}`)
    .join(',')
  return `${plan.source}|${plan.starters.join('>')}|${plan.benchOrder.join('>')}|${minutes}`
}

/** True when two drafts describe the same depth-chart order and minutes. */
export function draftsEqual(
  a: RotationDraft,
  b: RotationDraft,
  roster: readonly Player[],
): boolean {
  if (a.order.length !== b.order.length) {
    return false
  }
  if (!a.order.every((id, index) => id === b.order[index])) {
    return false
  }
  return roster.every(
    (player) =>
      (a.minutesByPlayer[player.id] ?? 0) ===
      (b.minutesByPlayer[player.id] ?? 0),
  )
}

/** Keeps only on-roster ids, de-duplicated, then appends any missing roster ids. */
function dedupeToRoster(
  order: readonly PlayerId[],
  roster: readonly Player[],
): readonly PlayerId[] {
  const rosterIds = new Set<PlayerId>(roster.map((player) => player.id))
  const seen = new Set<PlayerId>()
  const result: PlayerId[] = []
  for (const id of order) {
    if (rosterIds.has(id) && !seen.has(id)) {
      seen.add(id)
      result.push(id)
    }
  }
  for (const player of roster) {
    if (!seen.has(player.id)) {
      result.push(player.id)
    }
  }
  return result
}
