export const CONFERENCES = ['east', 'west'] as const
export type Conference = (typeof CONFERENCES)[number]

export const DIVISIONS = [
  'atlantic',
  'central',
  'southeast',
  'northwest',
  'pacific',
  'southwest',
] as const
export type Division = (typeof DIVISIONS)[number]

/** Which conference each division belongs to (three divisions per conference). */
export const DIVISION_CONFERENCE = {
  atlantic: 'east',
  central: 'east',
  southeast: 'east',
  northwest: 'west',
  pacific: 'west',
  southwest: 'west',
} as const satisfies Record<Division, Conference>

export const TEAMS_PER_DIVISION = 5
export const ALIGNED_TEAM_COUNT = DIVISIONS.length * TEAMS_PER_DIVISION

export interface LeagueAlignment {
  readonly conference: Conference
  readonly division: Division
}

/**
 * Assigns a team's ordered index to its conference and division for the aligned
 * 30-team league (six divisions of five, three divisions per conference).
 * Deterministic and index-based, so it composes with the seeded team list
 * without depending on identities.
 */
export function alignTeamIndex(index: number): LeagueAlignment {
  if (!Number.isSafeInteger(index) || index < 0 || index >= ALIGNED_TEAM_COUNT) {
    throw new RangeError(
      `Team index must be from 0 through ${ALIGNED_TEAM_COUNT - 1}: ${String(index)}`,
    )
  }
  const division = DIVISIONS[Math.floor(index / TEAMS_PER_DIVISION)]
  return Object.freeze({
    conference: DIVISION_CONFERENCE[division],
    division,
  })
}

export function isConference(value: unknown): value is Conference {
  return CONFERENCES.some((conference) => conference === value)
}

export function isDivision(value: unknown): value is Division {
  return DIVISIONS.some((division) => division === value)
}
