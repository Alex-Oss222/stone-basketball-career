import type { PlayerId } from '../domain/ids'
import type { Player, Position } from '../domain/league'
import { POSITIONS } from '../domain/league'
import { selectRotationAbility } from '../domain/rotationAbility'

/**
 * §8 Depth & Roles — a per-position depth chart, derived (v1) from natural
 * eligibility × the versioned rotation-ability selector. Each position holds an
 * ordered list of the players eligible there (best first); the coach reorders it
 * by drag-and-drop. Display-only for now (not persisted, never read by the sim);
 * "Save Depth Plan" and cross-position eligibility toggles come later.
 */
export type DepthChart = Readonly<Record<Position, readonly PlayerId[]>>

/** A player is naturally eligible at their primary or secondary position. */
export function isEligibleAt(player: Player, position: Position): boolean {
  return (
    player.primaryPosition === position ||
    player.secondaryPosition === position
  )
}

export function deriveDepthChart(roster: readonly Player[]): DepthChart {
  const chart = {} as Record<Position, PlayerId[]>
  for (const position of POSITIONS) {
    const eligible = roster.filter((player) => isEligibleAt(player, position))
    eligible.sort((a, b) => {
      const abilityA = selectRotationAbility(a.ratings, position).ability
      const abilityB = selectRotationAbility(b.ratings, position).ability
      if (abilityB !== abilityA) {
        return abilityB - abilityA
      }
      return a.id < b.id ? -1 : a.id > b.id ? 1 : 0
    })
    chart[position] = eligible.map((player) => player.id)
  }
  return chart
}

/**
 * Moves `playerId` to `toIndex` within `position`'s depth list (a within-row
 * reorder). Returns the chart unchanged if the player is not in that list.
 */
export function reorderDepth(
  chart: DepthChart,
  position: Position,
  playerId: PlayerId,
  toIndex: number,
): DepthChart {
  const list = [...chart[position]]
  const from = list.indexOf(playerId)
  if (from === -1) {
    return chart
  }
  list.splice(from, 1)
  const clamped = Math.max(0, Math.min(toIndex, list.length))
  list.splice(clamped, 0, playerId)
  return { ...chart, [position]: list }
}

export const DEPTH_TIER_LABELS = [
  'Starter',
  'Primary Backup',
  'Emergency',
] as const

/** The rotation-status label for a given depth rank at a position. */
export function depthTierLabel(rank: number): string {
  return DEPTH_TIER_LABELS[rank] ?? 'Depth'
}

export interface PositionCoverage {
  readonly strong: number
  readonly average: number
  readonly weak: number
}

/** Coverage per position: 3+ deep = strong, 2 = average, 0–1 = weak. */
export function derivePositionCoverage(chart: DepthChart): PositionCoverage {
  let strong = 0
  let average = 0
  let weak = 0
  for (const position of POSITIONS) {
    const depth = chart[position].length
    if (depth >= 3) {
      strong += 1
    } else if (depth === 2) {
      average += 1
    } else {
      weak += 1
    }
  }
  return { strong, average, weak }
}

/** Positions with thin coverage, for the depth alerts. */
export function deriveDepthAlerts(chart: DepthChart): readonly string[] {
  const alerts: string[] = []
  for (const position of POSITIONS) {
    const depth = chart[position].length
    if (depth === 0) {
      alerts.push(`No ${position} is eligible on the roster`)
    } else if (depth === 1) {
      alerts.push(`No backup ${position} — only one eligible player`)
    } else if (depth === 2) {
      alerts.push(`${position} depth is thin (no emergency option)`)
    }
  }
  return alerts
}
