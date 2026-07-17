import { parseGameId } from '../domain/ids'
import type { GameId, TeamId } from '../domain/ids'
import type { League } from '../domain/league'
import type { TeamScheduleSiteFilter } from '../app/teamScheduleViewModel'

export interface TeamScheduleUiState {
  readonly inspectedTeamId: TeamId
  readonly siteFilter: TeamScheduleSiteFilter
  readonly selectedGameId: GameId | null
}

export interface CreateTeamScheduleUiStateInput {
  readonly league: League
  readonly managedTeamId: TeamId | null
  readonly initialInspectedTeamId?: TeamId
  readonly initialFilter?: TeamScheduleSiteFilter
  readonly initialSelectedGameId?: GameId | null
}

export type TeamScheduleUiAction =
  | {
      readonly type: 'inspect_team'
      readonly teamId: TeamId
    }
  | {
      readonly type: 'set_site_filter'
      readonly filter: TeamScheduleSiteFilter
    }
  | {
      readonly type: 'open_game'
      readonly gameId: GameId
    }
  | {
      readonly type: 'close_game'
    }

export function createTeamScheduleUiState({
  league,
  managedTeamId,
  initialInspectedTeamId,
  initialFilter = 'all',
  initialSelectedGameId = null,
}: CreateTeamScheduleUiStateInput): TeamScheduleUiState {
  const firstTeam = league.teams[0]
  if (firstTeam === undefined) {
    throw new RangeError('Team Schedule requires at least one league team')
  }
  const inspectedTeamId =
    initialInspectedTeamId ?? managedTeamId ?? firstTeam.id
  if (!league.teams.some((team) => team.id === inspectedTeamId)) {
    throw new RangeError(
      `Inspected team ${inspectedTeamId} does not belong to the league`,
    )
  }
  if (
    managedTeamId !== null &&
    !league.teams.some((team) => team.id === managedTeamId)
  ) {
    throw new RangeError(
      `Managed team ${managedTeamId} does not belong to the league`,
    )
  }

  return Object.freeze({
    inspectedTeamId,
    siteFilter: parseTeamScheduleSiteFilter(initialFilter),
    selectedGameId:
      initialSelectedGameId === null
        ? null
        : parseGameId(initialSelectedGameId),
  })
}

export function reduceTeamScheduleUiState(
  state: TeamScheduleUiState,
  action: TeamScheduleUiAction,
): TeamScheduleUiState {
  switch (action.type) {
    case 'inspect_team':
      return Object.freeze({
        inspectedTeamId: action.teamId,
        siteFilter: 'all',
        selectedGameId: null,
      })
    case 'set_site_filter':
      return Object.freeze({
        ...state,
        siteFilter: parseTeamScheduleSiteFilter(action.filter),
      })
    case 'open_game':
      return Object.freeze({
        ...state,
        selectedGameId: parseGameId(action.gameId),
      })
    case 'close_game':
      return Object.freeze({
        ...state,
        selectedGameId: null,
      })
    default:
      return assertNever(action)
  }
}

export function parseTeamScheduleSiteFilter(
  value: unknown,
): TeamScheduleSiteFilter {
  switch (value) {
    case 'all':
    case 'home':
    case 'away':
      return value
    default:
      throw new RangeError(
        `Team Schedule site filter is unsupported: ${String(value)}`,
      )
  }
}

function assertNever(value: never): never {
  throw new RangeError(`Unsupported Team Schedule UI action: ${String(value)}`)
}
