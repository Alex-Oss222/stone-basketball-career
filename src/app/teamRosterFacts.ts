import type { TeamId } from '../domain/ids'
import type { League, Player, Position, Team } from '../domain/league'
import { deriveOverall } from '../domain/playerDerivations'

export interface TeamRosterFacts {
  readonly team: Team
  readonly roster: readonly Player[]
  readonly averageRating: number
  readonly positionCounts: Readonly<Record<Position, number>>
}

export function deriveRosterAverageRating(
  roster: readonly Player[],
): number {
  if (roster.length === 0) {
    return 0
  }

  const overallSum = roster.reduce(
    (total, player) => total + deriveOverall(player),
    0,
  )
  return Math.round(overallSum / roster.length)
}

export function deriveTeamAverageRating(
  league: League,
  teamId: TeamId,
): number {
  return deriveRosterAverageRating(
    league.players.filter((player) => player.teamId === teamId),
  )
}

export function createTeamRosterFacts(
  league: League,
  teamId: TeamId,
): TeamRosterFacts | null {
  const team = league.teams.find((candidate) => candidate.id === teamId)
  if (team === undefined) {
    return null
  }

  const roster = league.players.filter((player) => player.teamId === teamId)
  const positionCounts: Record<Position, number> = {
    PG: 0,
    SG: 0,
    SF: 0,
    PF: 0,
    C: 0,
  }
  for (const player of roster) {
    positionCounts[player.primaryPosition] += 1
  }

  return {
    team,
    roster,
    averageRating: deriveRosterAverageRating(roster),
    positionCounts,
  }
}
