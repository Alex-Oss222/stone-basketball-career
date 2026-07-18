import type { League, Position } from '../domain/league'
import { PLAYERS_PER_TEAM, formatTeamName } from '../domain/league'
import type { TeamId } from '../domain/ids'
import { createTeamRosterFacts } from './teamRosterFacts'

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
  const facts = createTeamRosterFacts(league, managedTeamId)
  if (facts === null) {
    return null
  }

  return {
    teamName: formatTeamName(facts.team),
    abbreviation: facts.team.abbreviation,
    rosterSize: facts.roster.length,
    rosterCapacity: PLAYERS_PER_TEAM,
    openSpots: Math.max(0, PLAYERS_PER_TEAM - facts.roster.length),
    averageRating: facts.averageRating,
    positionCounts: facts.positionCounts,
  }
}
