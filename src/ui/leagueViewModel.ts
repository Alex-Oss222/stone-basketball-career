import type { TeamId } from '../domain/ids'
import type { League, Player, Team } from '../domain/league'
import { RATING_KEYS, ratingToGrade } from '../domain/ratings'
import type {
  Grade,
  PlayerRatings,
  RatingKey,
} from '../domain/ratings'

export const RATING_LABELS = {
  insideScoring: 'Inside scoring',
  midRangeShooting: 'Mid-range shooting',
  threePointShooting: 'Three-point shooting',
  freeThrowShooting: 'Free-throw shooting',
  passing: 'Passing',
  ballHandling: 'Ball handling',
  offensiveRebounding: 'Offensive rebounding',
  defensiveRebounding: 'Defensive rebounding',
  perimeterDefense: 'Perimeter defense',
  interiorDefense: 'Interior defense',
  stealing: 'Stealing',
  blocking: 'Blocking',
  speed: 'Speed',
  strength: 'Strength',
  endurance: 'Endurance',
  basketballIQ: 'Basketball IQ',
} as const satisfies Readonly<Record<RatingKey, string>>

export interface RatingDisplayRow {
  readonly key: RatingKey
  readonly label: string
  readonly value: number
  readonly grade: Grade
}

export function createRatingDisplayRows(
  ratings: PlayerRatings,
): readonly RatingDisplayRow[] {
  return RATING_KEYS.map((key) => ({
    key,
    label: RATING_LABELS[key],
    value: ratings[key],
    grade: ratingToGrade(ratings[key]),
  }))
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

export function formatTeamName(team: Team): string {
  return `${team.city} ${team.nickname}`
}
