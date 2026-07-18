import type { LeagueId, PlayerId, TeamId } from './ids'
import type {
  CategoryDefinitionVersion,
  DetailedPlayerRatings,
  DetailedRatingGenerationVersion,
  DetailedRatingsSchemaVersion,
} from './detailedRatings'

export const POSITIONS = ['PG', 'SG', 'SF', 'PF', 'C'] as const
export type Position = (typeof POSITIONS)[number]

export const PLAYER_AGE_MIN = 19
export const PLAYER_AGE_MAX = 36
export const JERSEY_NUMBER_MIN = 0
export const JERSEY_NUMBER_MAX = 99
export const LEAGUE_TEAM_COUNT = 8
export const PLAYERS_PER_TEAM = 12
export const LEAGUE_PLAYER_COUNT = LEAGUE_TEAM_COUNT * PLAYERS_PER_TEAM

export interface PlayerTendencies {
  readonly usage: number
  readonly rim: number
  readonly midrange: number
  readonly threePoint: number
  readonly pass: number
  readonly drawFoul: number
}

export interface TeamColors {
  readonly primary: string
  readonly secondary: string
  readonly accent: string
}

export interface TeamMark {
  readonly kind: 'initials'
  readonly text: string
}

export interface Team {
  readonly id: TeamId
  readonly city: string
  readonly nickname: string
  readonly abbreviation: string
  readonly colors: TeamColors
  readonly mark: TeamMark
}

/** Canonical full team name shared by every application and UI read model. */
export function formatTeamName(team: Team): string {
  return `${team.city} ${team.nickname}`
}

export interface Player {
  readonly id: PlayerId
  readonly teamId: TeamId
  readonly firstName: string
  readonly lastName: string
  readonly age: number
  readonly jerseyNumber: number
  readonly primaryPosition: Position
  readonly secondaryPosition: Position | null
  /** Version of the deterministic detailed-rating generation that produced `ratings`. */
  readonly ratingGenerationVersion: DetailedRatingGenerationVersion
  /** The 67 authoritative sub-ratings (ADR 0008); everything else is derived. */
  readonly ratings: DetailedPlayerRatings
  readonly tendencies: PlayerTendencies
}

/**
 * A complete generated league snapshot; player records are stored explicitly.
 * The save carries the detailed skill-schema and category-definition versions
 * (ADR 0008) alongside each player's generation version.
 */
export interface League {
  readonly id: LeagueId
  readonly generatorVersion: 1
  readonly detailedRatingsSchemaVersion: DetailedRatingsSchemaVersion
  readonly categoryDefinitionVersion: CategoryDefinitionVersion
  readonly seedFingerprint: string
  readonly teams: readonly Team[]
  readonly players: readonly Player[]
}

export function isPosition(value: unknown): value is Position {
  return typeof value === 'string' && POSITIONS.some((position) => position === value)
}
