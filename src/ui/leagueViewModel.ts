import type { TeamId } from '../domain/ids'
import type { League, Player } from '../domain/league'
export { formatTeamName } from '../domain/league'
import {
  DETAILED_CATEGORY_DEFINITIONS,
  deriveCategoryScore,
} from '../domain/detailedRatings'
import type {
  DetailedCategoryGroup,
  DetailedCategoryKey,
  DetailedPlayerRatings,
} from '../domain/detailedRatings'
import { ratingToGrade } from '../domain/ratings'
import type { Grade } from '../domain/ratings'

export interface RatingDisplayRow {
  readonly key: DetailedCategoryKey
  readonly label: string
  readonly group: DetailedCategoryGroup
  /** Rounded for display only; the grade derives from the unrounded score. */
  readonly value: number
  readonly grade: Grade
}

const displayRowCache = new WeakMap<
  DetailedPlayerRatings,
  readonly RatingDisplayRow[]
>()

/**
 * The 26 derived category rows in registry order — display data, never
 * stored. Memoized per ratings reference; the cache is implicitly keyed by
 * CATEGORY_DEFINITION_VERSION because a definition change ships new code.
 */
export function createRatingDisplayRows(
  ratings: DetailedPlayerRatings,
): readonly RatingDisplayRow[] {
  const cached = displayRowCache.get(ratings)
  if (cached !== undefined) {
    return cached
  }

  const rows = DETAILED_CATEGORY_DEFINITIONS.map((definition) => {
    const score = deriveCategoryScore(ratings, definition.key)
    return {
      key: definition.key,
      label: definition.label,
      group: definition.group,
      value: Math.round(score),
      grade: ratingToGrade(score),
    }
  })
  displayRowCache.set(ratings, rows)
  return rows
}

export function getTeamRoster(
  league: League,
  teamId: TeamId,
): readonly Player[] {
  return league.players.filter((player) => player.teamId === teamId)
}

export function formatPlayerName(player: Player): string {
  return `${player.firstName} ${player.lastName}`
}
