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

/**
 * The 16 behavioural tendency families (RATINGS_REHAUL §7, ADR 0009 §6). Each
 * value is a 0–100 frequency/preference integer (`usage` is 1–100). Tendencies
 * describe what a player *chooses* to do and how often — they never raise OVR
 * and are never read as rating factors. Multi-component families are stored as
 * their listed components: the shot-diet family stays `rim`/`midrange`/
 * `threePoint` as independent values that do **not** sum to 100 (the §9
 * tendency-normalization inputs); the jump-shot-creation and drive/shoot/pass
 * families likewise keep their components. `contactSeeking` is the renamed
 * former `drawFoul`.
 */
export interface PlayerTendencies {
  // Touches and Usage
  readonly usage: number
  // Rim, Mid and Three shot diet (independent; do not sum to 100)
  readonly rim: number
  readonly midrange: number
  readonly threePoint: number
  // Catch-and-Shoot, Pull-Up and Movement (jump-shot creation type)
  readonly catchAndShoot: number
  readonly pullUp: number
  readonly movement: number
  // Drive, Shoot and Pass (post-catch choice)
  readonly drive: number
  readonly shoot: number
  readonly pass: number
  // Isolation
  readonly isolation: number
  // Pick-and-Roll Handler
  readonly pickAndRoll: number
  // Roll, Pop and Short Roll
  readonly rollPop: number
  // Post-Up
  readonly postUp: number
  // Cutting and Relocating
  readonly cutRelocate: number
  // Transition Aggression
  readonly transition: number
  // Contact Seeking (formerly drawFoul)
  readonly contactSeeking: number
  // Offensive-Rebound Crash
  readonly offensiveReboundCrash: number
  // Steal Aggression
  readonly stealAggression: number
  // Block Aggression
  readonly blockAggression: number
  // Passing Risk
  readonly passingRisk: number
  // Pace Preference
  readonly pacePreference: number
}

/**
 * The five raw physical measurements (ADR 0009 §4), stored integers. They are a
 * separate stored layer — never averaged into Strength, never a hard gate. The
 * derived Functional Size (playerDerivations.ts) z-scores height/wingspan/
 * standing reach against a fixed reference set; hand size is a soft input to a
 * few derived ratings only.
 */
export interface PlayerMeasurements {
  readonly heightInches: number
  readonly weightPounds: number
  readonly wingspanInches: number
  readonly standingReachInches: number
  readonly handSizeInches: number
}

/** The ordered measurement keys — the authoritative order for storage. */
export const MEASUREMENT_KEYS = [
  'heightInches',
  'weightPounds',
  'wingspanInches',
  'standingReachInches',
  'handSizeInches',
] as const

/** The ordered tendency keys — the authoritative order for storage. */
export const TENDENCY_KEYS = [
  'usage',
  'rim',
  'midrange',
  'threePoint',
  'catchAndShoot',
  'pullUp',
  'movement',
  'drive',
  'shoot',
  'pass',
  'isolation',
  'pickAndRoll',
  'rollPop',
  'postUp',
  'cutRelocate',
  'transition',
  'contactSeeking',
  'offensiveReboundCrash',
  'stealAggression',
  'blockAggression',
  'passingRisk',
  'pacePreference',
] as const

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
  /** The 91 authoritative base ratings (ADR 0009); everything else is derived. */
  readonly ratings: DetailedPlayerRatings
  /** The five raw physical measurements (ADR 0009 §4). */
  readonly measurements: PlayerMeasurements
  readonly tendencies: PlayerTendencies
}

/**
 * A complete generated league snapshot; player records are stored explicitly.
 * The save carries the detailed skill-schema and category-definition versions
 * (ADR 0008) alongside each player's generation version.
 */
export interface League {
  readonly id: LeagueId
  readonly generatorVersion: 2
  readonly detailedRatingsSchemaVersion: DetailedRatingsSchemaVersion
  readonly categoryDefinitionVersion: CategoryDefinitionVersion
  readonly seedFingerprint: string
  readonly teams: readonly Team[]
  readonly players: readonly Player[]
}

export function isPosition(value: unknown): value is Position {
  return typeof value === 'string' && POSITIONS.some((position) => position === value)
}
