import type { League, Position } from '../domain/league'
import { PLAYERS_PER_TEAM, POSITIONS, formatTeamName } from '../domain/league'
import type { TeamId } from '../domain/ids'
import { RATING_KEYS } from '../domain/ratings'

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
  /** Plain mean of every stored rating on the roster, rounded. Labeled as an average, not an "overall". */
  readonly averageRating: number
  readonly positionCounts: Readonly<Record<Position, number>>
}

/**
 * Plain mean of every stored rating on one team's roster, rounded. A
 * transparent presentation average — deliberately not an "overall" formula,
 * which is a versioned simulation decision (§9).
 */
export function deriveTeamAverageRating(
  league: League,
  teamId: TeamId,
): number {
  const roster = league.players.filter((player) => player.teamId === teamId)
  const ratingCount = roster.length * RATING_KEYS.length
  if (ratingCount === 0) {
    return 0
  }
  const ratingSum = roster.reduce(
    (total, player) =>
      total +
      RATING_KEYS.reduce((sum, key) => sum + player.ratings[key], 0),
    0,
  )
  return Math.round(ratingSum / ratingCount)
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
