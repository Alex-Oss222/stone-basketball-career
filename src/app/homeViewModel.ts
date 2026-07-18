import type { League, Position } from '../domain/league'
import { PLAYERS_PER_TEAM, formatTeamName } from '../domain/league'
import type { TeamId } from '../domain/ids'
import { createTeamRosterFacts } from './teamRosterFacts'
export { deriveTeamAverageRating } from './teamRosterFacts'

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

export function createHomeHeaderSummary(input: {
  readonly league: League
  readonly managedTeamId: TeamId | null
}): HomeHeaderSummary | null {
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
    averageRating: facts.averageRating,
    positionCounts: facts.positionCounts,
  }
}
