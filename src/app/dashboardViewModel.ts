import type { TeamId } from '../domain/ids'
import type { League, Player, Position, Team } from '../domain/league'

export const LEAGUE_SETUP_PROGRESS_LABEL = 'League setup' as const
export const NO_SEASON_STARTED_LABEL = 'No season started' as const

export type SaveIndicatorState = 'saved' | 'saving' | 'error'

export const SAVE_INDICATOR_LABELS: Readonly<
  Record<SaveIndicatorState, string>
> = {
  saved: 'Saved locally',
  saving: 'Saving...',
  error: 'Save error',
}

export const DASHBOARD_HEADER_MODEL = {
  progressLabel: LEAGUE_SETUP_PROGRESS_LABEL,
  seasonStatus: NO_SEASON_STARTED_LABEL,
} as const

export interface DashboardLeagueState {
  readonly league: League
  readonly managedTeamId: TeamId | null
}

export interface DashboardActionLeagueState extends DashboardLeagueState {
  readonly hasSchedule: boolean
}

export type DashboardAction =
  | {
      readonly label: 'Create League'
      readonly target: 'create-league'
    }
  | {
      readonly label: 'Choose Team'
      readonly target: 'choose-team'
    }
  | {
      readonly label: 'View Schedule'
      readonly target: 'view-schedule'
    }

export type PlayerPositionFilter = Position | 'ALL'

export interface LeaguePlayerFilterResult {
  readonly player: Player
  readonly playerName: string
  readonly team: Team
  readonly teamName: string
  readonly teamAbbreviation: string
}

/** Returns the one action justified by the currently stored league state. */
export function deriveDashboardAction(
  state: DashboardActionLeagueState | null,
): DashboardAction {
  if (state === null) {
    return { label: 'Create League', target: 'create-league' }
  }
  if (state.managedTeamId === null) {
    return { label: 'Choose Team', target: 'choose-team' }
  }

  requireTeam(state.league, state.managedTeamId)
  if (!state.hasSchedule) {
    throw new RangeError('A managed league must have a schedule')
  }

  return { label: 'View Schedule', target: 'view-schedule' }
}

/**
 * Filters the persisted league player array without sorting it. Every result
 * includes its resolved team so callers never invent missing display data.
 */
export function filterLeaguePlayers(
  league: League,
  nameQuery: string,
  position: PlayerPositionFilter,
): readonly LeaguePlayerFilterResult[] {
  const normalizedQuery = nameQuery.trim().toLowerCase()
  const teamsById = new Map(
    league.teams.map((team) => [team.id, team] as const),
  )
  const results: LeaguePlayerFilterResult[] = []

  for (const player of league.players) {
    const playerName = `${player.firstName} ${player.lastName}`
    if (
      normalizedQuery.length > 0 &&
      !playerName.toLowerCase().includes(normalizedQuery)
    ) {
      continue
    }
    if (position !== 'ALL' && player.primaryPosition !== position) {
      continue
    }

    const team = teamsById.get(player.teamId)
    if (team === undefined) {
      throw new RangeError(`Player ${player.id} does not reference a league team`)
    }

    results.push({
      player,
      playerName,
      team,
      teamName: `${team.city} ${team.nickname}`,
      teamAbbreviation: team.abbreviation,
    })
  }

  return results
}

function requireTeam(league: League, teamId: TeamId): Team {
  const team = league.teams.find((candidate) => candidate.id === teamId)
  if (team === undefined) {
    throw new RangeError('Managed team ID does not reference a league team')
  }
  return team
}
