import type { League, Position } from '../domain/league'
import { PLAYERS_PER_TEAM, POSITIONS, formatTeamName } from '../domain/league'
import type { TeamId } from '../domain/ids'
import { deriveVersionedOverall } from '../domain/playerDerivations'

/**
 * Header and roster facts for the Home page (§6), derived only from data that
 * exists today: identity, roster composition, and stored ratings. The summary
 * deliberately has no record, streak, seed, or statistics fields — those are
 * simulation-era facts, and until they are real the Home page marks their
 * slots "Coming later" instead of fabricating values.
 */
export interface HomeHeaderSummary {
  readonly teamName: string
  readonly abbreviation: string
  readonly rosterSize: number
  readonly rosterCapacity: number
  /** Rounded mean of the roster's versioned position-weighted overalls (derived, never stored). */
  readonly averageRating: number
  readonly positionCounts: Readonly<Record<Position, number>>
}

/**
 * Rounded mean of each roster player's versioned position-weighted overall
 * (OVERALL_MODEL_VERSION) — presentation data, derived only, never read by
 * the simulation.
 */
export function deriveTeamAverageRating(
  league: League,
  teamId: TeamId,
): number {
  const roster = league.players.filter((player) => player.teamId === teamId)
  if (roster.length === 0) {
    return 0
  }
  const overallSum = roster.reduce(
    (total, player) =>
      total +
      deriveVersionedOverall(player.ratings, player.primaryPosition),
    0,
  )
  return Math.round(overallSum / roster.length)
}

export function createHomeHeaderSummary(input: {
  readonly league: League
  readonly managedTeamId: TeamId | null
}): HomeHeaderSummary | null {
  const { league, managedTeamId } = input
  if (managedTeamId === null) {
    return null
  }
  const team = league.teams.find((candidate) => candidate.id === managedTeamId)
  if (team === undefined) {
    return null
  }
  const roster = league.players.filter(
    (player) => player.teamId === managedTeamId,
  )

  const positionCounts = Object.fromEntries(
    POSITIONS.map((position) => [
      position,
      roster.filter((player) => player.primaryPosition === position).length,
    ]),
  ) as Record<Position, number>

  return {
    teamName: formatTeamName(team),
    abbreviation: team.abbreviation,
    rosterSize: roster.length,
    rosterCapacity: PLAYERS_PER_TEAM,
    averageRating: deriveTeamAverageRating(league, managedTeamId),
    positionCounts,
  }
}
