import { parseGameId } from '../domain/ids'
import type { GameId, TeamId } from '../domain/ids'
import type { League } from '../domain/league'
import { parseYearMonth } from '../domain/yearMonth'
import type { YearMonth } from '../domain/yearMonth'
import type { TeamScheduleSiteFilter } from '../app/teamScheduleViewModel'

/** Scaffolded stage tabs. Only regular_season has authoritative games today. */
export type TeamScheduleStage =
  | 'preseason'
  | 'regular_season'
  | 'postseason'
  | 'offseason'

/** Scaffolded view tabs. Results has no game-result data until simulation. */
export type TeamScheduleViewMode = 'list' | 'calendar' | 'results'

export interface TeamScheduleUiState {
  readonly inspectedTeamId: TeamId
  readonly stage: TeamScheduleStage
  readonly viewMode: TeamScheduleViewMode
  readonly siteFilter: TeamScheduleSiteFilter
  /** Null means "auto-select" the current or first available month. */
  readonly visibleMonth: YearMonth | null
  readonly selectedGameId: GameId | null
}

export interface CreateTeamScheduleUiStateInput {
  readonly league: League
  readonly managedTeamId: TeamId | null
  readonly initialInspectedTeamId?: TeamId
  readonly initialStage?: TeamScheduleStage
  readonly initialViewMode?: TeamScheduleViewMode
  readonly initialFilter?: TeamScheduleSiteFilter
  readonly initialSelectedGameId?: GameId | null
}

export type TeamScheduleUiAction =
  | {
      readonly type: 'inspect_team'
      readonly teamId: TeamId
    }
  | {
      readonly type: 'set_stage'
      readonly stage: TeamScheduleStage
    }
  | {
      readonly type: 'set_view_mode'
      readonly viewMode: TeamScheduleViewMode
    }
  | {
      readonly type: 'set_site_filter'
      readonly filter: TeamScheduleSiteFilter
    }
  | {
      readonly type: 'set_visible_month'
      readonly month: YearMonth
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
  initialStage = 'regular_season',
  initialViewMode = 'calendar',
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
    stage: parseTeamScheduleStage(initialStage),
    viewMode: parseTeamScheduleViewMode(initialViewMode),
    siteFilter: parseTeamScheduleSiteFilter(initialFilter),
    visibleMonth: null,
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
        ...state,
        inspectedTeamId: action.teamId,
        siteFilter: 'all',
        visibleMonth: null,
        selectedGameId: null,
      })
    case 'set_stage':
      return Object.freeze({
        ...state,
        stage: parseTeamScheduleStage(action.stage),
        visibleMonth: null,
        selectedGameId: null,
      })
    case 'set_view_mode':
      return Object.freeze({
        ...state,
        viewMode: parseTeamScheduleViewMode(action.viewMode),
      })
    case 'set_site_filter':
      return Object.freeze({
        ...state,
        siteFilter: parseTeamScheduleSiteFilter(action.filter),
      })
    case 'set_visible_month':
      return Object.freeze({
        ...state,
        visibleMonth: parseYearMonth(action.month),
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

export function parseTeamScheduleStage(value: unknown): TeamScheduleStage {
  switch (value) {
    case 'preseason':
    case 'regular_season':
    case 'postseason':
    case 'offseason':
      return value
    default:
      throw new RangeError(
        `Team Schedule stage is unsupported: ${String(value)}`,
      )
  }
}

export function parseTeamScheduleViewMode(
  value: unknown,
): TeamScheduleViewMode {
  switch (value) {
    case 'list':
    case 'calendar':
    case 'results':
      return value
    default:
      throw new RangeError(
        `Team Schedule view mode is unsupported: ${String(value)}`,
      )
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
