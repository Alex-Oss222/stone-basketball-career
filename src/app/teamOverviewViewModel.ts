import type { League, Position } from '../domain/league'
import { PLAYERS_PER_TEAM, POSITIONS, formatTeamName } from '../domain/league'
import type { TeamId } from '../domain/ids'
import { deriveTeamAverageRating } from './homeViewModel'

/**
 * Team Overview facts derived only from data that exists today: team identity,
 * roster composition, stored ages, and stored ratings. Like the Home summary
 * it deliberately has no record, streak, ranking, or statistics fields — those
 * are simulation-era facts (§9–§11). Until they are real, the screen marks
 * their slots "Coming later" instead of fabricating a value.
 */
export interface TeamOverviewSummary {
  readonly teamName: string
  readonly abbreviation: string
  readonly rosterSize: number
  readonly rosterCapacity: number
  readonly openSpots: number
  /** Rounded mean of the roster's versioned position-weighted overalls (derived, never stored). */
  readonly averageRating: number
  readonly positionCounts: Readonly<Record<Position, number>>
}

export function createTeamOverviewSummary(input: {
  readonly league: League
  readonly managedTeamId: TeamId | null
}): TeamOverviewSummary | null {
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
    openSpots: Math.max(0, PLAYERS_PER_TEAM - roster.length),
    averageRating: deriveTeamAverageRating(league, managedTeamId),
    positionCounts,
  }
}
