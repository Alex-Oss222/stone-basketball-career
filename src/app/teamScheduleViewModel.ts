import {
  parseGameDayId,
  parseGameId,
  parseLeagueId,
  parseScheduleId,
  parseSeasonId,
  parseTeamId,
} from '../domain/ids'
import type {
  GameDayId,
  GameId,
  TeamId,
} from '../domain/ids'
import type { League, Team } from '../domain/league'
import { assertValidLeague } from '../domain/leagueValidation'
import {
  compareLocalDates,
  parseLocalDate,
} from '../domain/localDate'
import type { LocalDate } from '../domain/localDate'
import type {
  GameDay,
  LeagueSchedule,
  ScheduleStage,
  ScheduledGame,
  ScheduledGameStatus,
} from '../domain/schedule'
import {
  compareYearMonths,
  yearMonthFromLocalDate,
} from '../domain/yearMonth'
import type { YearMonth } from '../domain/yearMonth'
import {
  createScheduledGameCalendarProjection,
} from './calendarViewModel'
import type { CalendarEntryViewModel } from './calendarViewModel'

export const TEAM_SCHEDULE_SITES = ['home', 'away'] as const
export type TeamScheduleSite = (typeof TEAM_SCHEDULE_SITES)[number]

export const TEAM_SCHEDULE_SITE_FILTERS = ['all', 'home', 'away'] as const
export type TeamScheduleSiteFilter =
  (typeof TEAM_SCHEDULE_SITE_FILTERS)[number]

export type ScheduleReadModelErrorCode =
  | 'league_invalid'
  | 'schedule_invalid'
  | 'current_date_invalid'
  | 'inspected_team_invalid'
  | 'inspected_team_unknown'
  | 'managed_team_invalid'
  | 'managed_team_unknown'
  | 'managed_team_context_mismatch'
  | 'perspective_team_invalid'
  | 'perspective_team_unknown'
  | 'perspective_team_not_in_game'
  | 'calendar_entry_invalid'
  | 'duplicate_calendar_entry_id'
  | 'game_entry_mapping_invalid'
  | 'selected_game_invalid'
  | 'selected_game_unknown'
  | 'site_filter_invalid'
  | 'team_schedule_accounting_invalid'

export class InvalidScheduleReadModelError extends Error {
  readonly code: ScheduleReadModelErrorCode

  constructor(code: ScheduleReadModelErrorCode, message: string) {
    super(message)
    this.name = 'InvalidScheduleReadModelError'
    this.code = code
  }
}

export interface TeamScheduleRowViewModel {
  readonly gameId: GameId
  readonly gameDayId: GameDayId
  /**
   * One-based global position from the authoritative GameDay/game-ID topology.
   * This is display metadata and never replaces GameId identity.
   */
  readonly scheduleSequence: number
  readonly gameDaySequence: number
  readonly meetingNumber: number
  readonly stage: ScheduleStage
  readonly status: ScheduledGameStatus
  readonly placementDate: LocalDate | null
  readonly originalScheduledDate: LocalDate
  readonly currentScheduledDate: LocalDate | null
  readonly actualDate: LocalDate | null
  readonly month: YearMonth | null
  readonly inspectedTeamId: TeamId
  readonly opponentTeamId: TeamId
  readonly opponentName: string
  readonly opponentAbbreviation: string
  readonly homeTeamId: TeamId
  readonly awayTeamId: TeamId
  readonly site: TeamScheduleSite
  readonly isManagedTeamSchedule: boolean
  readonly involvesManagedTeam: boolean
  readonly isNextScheduledGame: boolean
  readonly isCurrentDate: boolean
  readonly isPastDate: boolean
  readonly isFutureDate: boolean
  readonly isUndated: boolean
}

export interface TeamScheduleMonthGroupViewModel {
  readonly month: YearMonth
  readonly rows: readonly TeamScheduleRowViewModel[]
  readonly gameCount: number
  readonly homeGameCount: number
  readonly awayGameCount: number
  readonly managedTeamGameCount: number
  readonly scheduledCount: number
  readonly completedCount: number
  readonly postponedCount: number
  readonly cancelledCount: number
  readonly containsNextScheduledGame: boolean
}

export interface UndatedTeamScheduleGroupViewModel {
  readonly rows: readonly TeamScheduleRowViewModel[]
  readonly gameCount: number
  readonly isEmpty: boolean
}

export interface TeamScheduleViewModel {
  readonly inspectedTeamId: TeamId
  readonly inspectedTeamName: string
  readonly inspectedTeamAbbreviation: string
  readonly managedTeamId: TeamId | null
  readonly isManagedTeamSchedule: boolean
  /** Complete inspected-team schedule in authoritative schedule sequence. */
  readonly rows: readonly TeamScheduleRowViewModel[]
  readonly monthGroups: readonly TeamScheduleMonthGroupViewModel[]
  readonly undatedGroup: UndatedTeamScheduleGroupViewModel
  readonly totalGameCount: number
  readonly datedGameCount: number
  readonly undatedGameCount: number
  readonly homeGameCount: number
  readonly awayGameCount: number
  readonly nextScheduledGameId: GameId | null
}

export interface CreateTeamScheduleViewModelInput {
  readonly league: League
  readonly schedule: LeagueSchedule
  readonly calendarEntries: readonly CalendarEntryViewModel[]
  readonly inspectedTeamId: TeamId
  readonly managedTeamId: TeamId | null
  readonly currentDate: LocalDate
}

export interface GameDetailsTeamViewModel {
  readonly teamId: TeamId
  readonly name: string
  readonly abbreviation: string
}

export interface GameDetailsViewModel {
  readonly gameId: GameId
  readonly gameDayId: GameDayId
  readonly scheduleSequence: number
  readonly gameDaySequence: number
  readonly meetingNumber: number
  readonly competitionStage: ScheduleStage
  readonly status: ScheduledGameStatus
  readonly homeTeam: GameDetailsTeamViewModel
  readonly awayTeam: GameDetailsTeamViewModel
  readonly placementDate: LocalDate | null
  readonly originalScheduledDate: LocalDate
  readonly currentScheduledDate: LocalDate | null
  readonly actualDate: LocalDate | null
  readonly isUndated: boolean
  readonly perspectiveTeamId: TeamId | null
  readonly perspectiveSite: TeamScheduleSite | null
  readonly opponentTeamId: TeamId | null
  readonly isManagedTeamGame: boolean
  readonly isPerspectiveTeamManaged: boolean
  readonly isCurrentDate: boolean
  readonly isPastDate: boolean
  readonly isFutureDate: boolean
  readonly previousPerspectiveGameId: GameId | null
  readonly nextPerspectiveGameId: GameId | null
}

export interface CreateGameDetailsViewModelInput {
  readonly league: League
  readonly schedule: LeagueSchedule
  readonly calendarEntries: readonly CalendarEntryViewModel[]
  readonly gameId: GameId
  readonly perspectiveTeamId: TeamId | null
  readonly managedTeamId: TeamId | null
  readonly currentDate: LocalDate
}

interface ResolvedScheduleGame {
  readonly game: ScheduledGame
  readonly gameDay: GameDay
  readonly entry: CalendarEntryViewModel
  readonly homeTeam: Team
  readonly awayTeam: Team
  readonly scheduleSequence: number
}

interface ValidatedScheduleReadContext {
  readonly teamById: ReadonlyMap<TeamId, Team>
  readonly managedTeamId: TeamId | null
  readonly currentDate: LocalDate
  readonly resolvedGames: readonly ResolvedScheduleGame[]
}

interface SharedGameProjection {
  readonly gameId: GameId
  readonly gameDayId: GameDayId
  readonly scheduleSequence: number
  readonly gameDaySequence: number
  readonly meetingNumber: number
  readonly stage: ScheduleStage
  readonly status: ScheduledGameStatus
  readonly placementDate: LocalDate | null
  readonly originalScheduledDate: LocalDate
  readonly currentScheduledDate: LocalDate | null
  readonly actualDate: LocalDate | null
  readonly month: YearMonth | null
  readonly homeTeamId: TeamId
  readonly awayTeamId: TeamId
  readonly isCurrentDate: boolean
  readonly isPastDate: boolean
  readonly isFutureDate: boolean
  readonly isUndated: boolean
}

type TeamScheduleRowDraft = Omit<
  TeamScheduleRowViewModel,
  'isNextScheduledGame'
>

/**
 * Creates the complete schedule projection for one inspected team.
 *
 * Rows follow the one-based sequence obtained by flattening `gameDays` in
 * stored order and each GameDay's ordered `gameIds`. Month groups are ordered
 * chronologically, while their rows retain that authoritative sequence.
 */
export function createTeamScheduleViewModel({
  league,
  schedule,
  calendarEntries,
  inspectedTeamId,
  managedTeamId,
  currentDate,
}: CreateTeamScheduleViewModelInput): TeamScheduleViewModel {
  const context = createValidatedContext({
    league,
    schedule,
    calendarEntries,
    managedTeamId,
    currentDate,
  })
  const validInspectedTeamId = parseContextTeamId(
    inspectedTeamId,
    context.teamById,
    'inspected',
  )
  const inspectedTeam = requireTeam(
    context.teamById,
    validInspectedTeamId,
    'inspected_team_unknown',
    'Inspected team',
  )
  const relevantGames = context.resolvedGames.filter((resolved) =>
    gameContainsTeam(resolved.game, validInspectedTeamId),
  )
  const rowDrafts = relevantGames.map((resolved) =>
    createTeamScheduleRowDraft(
      resolved,
      validInspectedTeamId,
      context.managedTeamId,
      context.currentDate,
    ),
  )
  const nextScheduledGameId = findNextScheduledGameId(
    rowDrafts,
    context.currentDate,
  )
  const rows = Object.freeze(
    rowDrafts.map((row) =>
      Object.freeze({
        ...row,
        isNextScheduledGame: row.gameId === nextScheduledGameId,
      }),
    ),
  )
  const monthGroups = createMonthGroups(rows)
  const undatedRows = Object.freeze(
    rows.filter((row) => row.isUndated),
  )
  const undatedGroup = Object.freeze({
    rows: undatedRows,
    gameCount: undatedRows.length,
    isEmpty: undatedRows.length === 0,
  })
  const datedGameCount = rows.length - undatedRows.length
  const homeGameCount = countRows(rows, (row) => row.site === 'home')
  const awayGameCount = countRows(rows, (row) => row.site === 'away')
  const isManagedTeamSchedule =
    context.managedTeamId !== null &&
    validInspectedTeamId === context.managedTeamId

  validateTeamScheduleAccounting(
    rows,
    monthGroups,
    undatedGroup,
    nextScheduledGameId,
    relevantGames.length,
  )

  return Object.freeze({
    inspectedTeamId: validInspectedTeamId,
    inspectedTeamName: formatTeamName(inspectedTeam),
    inspectedTeamAbbreviation: inspectedTeam.abbreviation,
    managedTeamId: context.managedTeamId,
    isManagedTeamSchedule,
    rows,
    monthGroups,
    undatedGroup,
    totalGameCount: rows.length,
    datedGameCount,
    undatedGameCount: undatedRows.length,
    homeGameCount,
    awayGameCount,
    nextScheduledGameId,
  })
}

/**
 * Creates schedule-only game details. Perspective controls only relative
 * home/away, opponent, and neighboring-game fields.
 */
export function createGameDetailsViewModel({
  league,
  schedule,
  calendarEntries,
  gameId,
  perspectiveTeamId,
  managedTeamId,
  currentDate,
}: CreateGameDetailsViewModelInput): GameDetailsViewModel {
  const context = createValidatedContext({
    league,
    schedule,
    calendarEntries,
    managedTeamId,
    currentDate,
  })
  const validGameId = parseSelectedGameId(gameId)
  const resolved = context.resolvedGames.find(
    (candidate) => candidate.game.id === validGameId,
  )
  if (resolved === undefined) {
    throw invalidReadModel(
      'selected_game_unknown',
      `Selected game ${validGameId} does not exist in the supplied schedule`,
    )
  }

  const shared = createSharedGameProjection(resolved, context.currentDate)
  let validPerspectiveTeamId: TeamId | null = null
  let perspectiveSite: TeamScheduleSite | null = null
  let opponentTeamId: TeamId | null = null
  let previousPerspectiveGameId: GameId | null = null
  let nextPerspectiveGameId: GameId | null = null

  if (perspectiveTeamId !== null) {
    const parsedPerspectiveTeamId = parsePerspectiveTeamId(
      perspectiveTeamId,
      context.teamById,
    )
    validPerspectiveTeamId = parsedPerspectiveTeamId
    if (!gameContainsTeam(resolved.game, parsedPerspectiveTeamId)) {
      throw invalidReadModel(
        'perspective_team_not_in_game',
        `Perspective team ${parsedPerspectiveTeamId} does not participate in game ${validGameId}`,
      )
    }

    perspectiveSite =
      resolved.game.homeTeamId === parsedPerspectiveTeamId ? 'home' : 'away'
    opponentTeamId =
      perspectiveSite === 'home'
        ? resolved.game.awayTeamId
        : resolved.game.homeTeamId

    const perspectiveGames = context.resolvedGames.filter((candidate) =>
      gameContainsTeam(candidate.game, parsedPerspectiveTeamId),
    )
    const selectedIndex = perspectiveGames.findIndex(
      (candidate) => candidate.game.id === validGameId,
    )
    if (selectedIndex < 0) {
      throw invalidReadModel(
        'team_schedule_accounting_invalid',
        `Selected game ${validGameId} is absent from its perspective-team sequence`,
      )
    }
    previousPerspectiveGameId =
      perspectiveGames[selectedIndex - 1]?.game.id ?? null
    nextPerspectiveGameId =
      perspectiveGames[selectedIndex + 1]?.game.id ?? null
  }

  return Object.freeze({
    gameId: shared.gameId,
    gameDayId: shared.gameDayId,
    scheduleSequence: shared.scheduleSequence,
    gameDaySequence: shared.gameDaySequence,
    meetingNumber: shared.meetingNumber,
    competitionStage: shared.stage,
    status: shared.status,
    homeTeam: createTeamIdentity(resolved.homeTeam),
    awayTeam: createTeamIdentity(resolved.awayTeam),
    placementDate: shared.placementDate,
    originalScheduledDate: shared.originalScheduledDate,
    currentScheduledDate: shared.currentScheduledDate,
    actualDate: shared.actualDate,
    isUndated: shared.isUndated,
    perspectiveTeamId: validPerspectiveTeamId,
    perspectiveSite,
    opponentTeamId,
    isManagedTeamGame:
      context.managedTeamId !== null &&
      gameContainsTeam(resolved.game, context.managedTeamId),
    isPerspectiveTeamManaged:
      validPerspectiveTeamId !== null &&
      validPerspectiveTeamId === context.managedTeamId,
    isCurrentDate: shared.isCurrentDate,
    isPastDate: shared.isPastDate,
    isFutureDate: shared.isFutureDate,
    previousPerspectiveGameId,
    nextPerspectiveGameId,
  })
}

export function filterTeamScheduleRows(
  rows: readonly TeamScheduleRowViewModel[],
  filter: TeamScheduleSiteFilter,
): readonly TeamScheduleRowViewModel[] {
  switch (filter) {
    case 'all':
      return Object.freeze([...rows])
    case 'home':
    case 'away':
      return Object.freeze(rows.filter((row) => row.site === filter))
    default:
      throw invalidReadModel(
        'site_filter_invalid',
        `Team Schedule site filter is unsupported: ${String(filter)}`,
      )
  }
}

function createValidatedContext({
  league,
  schedule,
  calendarEntries,
  managedTeamId,
  currentDate,
}: Omit<
  CreateTeamScheduleViewModelInput,
  'inspectedTeamId'
>): ValidatedScheduleReadContext {
  try {
    assertValidLeague(league)
  } catch (error) {
    throw invalidReadModel(
      'league_invalid',
      `League is invalid: ${getErrorMessage(error)}`,
    )
  }

  const teamById = new Map(
    league.teams.map((team) => [parseTeamId(team.id), team] as const),
  )
  const validManagedTeamId =
    managedTeamId === null
      ? null
      : parseContextTeamId(managedTeamId, teamById, 'managed')
  const validCurrentDate = parseCurrentDate(currentDate)

  let leagueId
  let scheduleLeagueId
  let scheduleSeasonId
  try {
    leagueId = parseLeagueId(league.id)
    scheduleLeagueId = parseLeagueId(schedule.leagueId)
    parseScheduleId(schedule.id)
    scheduleSeasonId = parseSeasonId(schedule.seasonId)
  } catch (error) {
    throw invalidReadModel(
      'schedule_invalid',
      `Schedule identity is invalid: ${getErrorMessage(error)}`,
    )
  }
  if (scheduleLeagueId !== leagueId) {
    throw invalidReadModel(
      'schedule_invalid',
      `Schedule league ${scheduleLeagueId} does not match supplied league ${leagueId}`,
    )
  }

  validateCalendarEntryCollection(
    calendarEntries,
    teamById,
    validManagedTeamId,
  )

  const gameById = validateScheduleGames(
    schedule,
    scheduleSeasonId,
    teamById,
  )
  const gameEntryById = createGameEntryMap(calendarEntries)
  const resolvedGames: ResolvedScheduleGame[] = []
  const gameDayIds = new Set<GameDayId>()
  const declaredGameIds = new Set<GameId>()
  let scheduleSequence = 1

  for (
    let gameDayIndex = 0;
    gameDayIndex < schedule.gameDays.length;
    gameDayIndex += 1
  ) {
    const gameDay = schedule.gameDays[gameDayIndex]
    const gameDayId = validateGameDay(
      gameDay,
      gameDayIndex,
      scheduleSeasonId,
      gameDayIds,
    )

    for (const sourceGameId of gameDay.gameIds) {
      const declaredGameId = parseScheduleGameId(sourceGameId)
      if (declaredGameIds.has(declaredGameId)) {
        throw invalidReadModel(
          'schedule_invalid',
          `Game ${declaredGameId} is declared by more than one GameDay slot`,
        )
      }
      declaredGameIds.add(declaredGameId)

      const game = gameById.get(declaredGameId)
      if (game === undefined) {
        throw invalidReadModel(
          'schedule_invalid',
          `GameDay ${gameDayId} references unknown game ${declaredGameId}`,
        )
      }
      if (game.gameDayId !== gameDayId) {
        throw invalidReadModel(
          'schedule_invalid',
          `Game ${declaredGameId} does not reference declaring GameDay ${gameDayId}`,
        )
      }
      if (game.originalScheduledDate !== gameDay.scheduledDate) {
        throw invalidReadModel(
          'schedule_invalid',
          `Game ${declaredGameId} original date does not match GameDay ${gameDayId}`,
        )
      }

      const entry = gameEntryById.get(declaredGameId)
      if (entry === undefined) {
        throw invalidReadModel(
          'game_entry_mapping_invalid',
          `Game ${declaredGameId} has no normalized calendar entry`,
        )
      }
      validateGameEntryMapping(game, entry, validManagedTeamId)

      const homeTeam = requireTeam(
        teamById,
        game.homeTeamId,
        'schedule_invalid',
        'Home team',
      )
      const awayTeam = requireTeam(
        teamById,
        game.awayTeamId,
        'schedule_invalid',
        'Away team',
      )
      resolvedGames.push(
        Object.freeze({
          game,
          gameDay,
          entry,
          homeTeam,
          awayTeam,
          scheduleSequence,
        }),
      )
      scheduleSequence += 1
    }
  }

  if (
    declaredGameIds.size !== gameById.size ||
    resolvedGames.length !== schedule.games.length
  ) {
    throw invalidReadModel(
      'schedule_invalid',
      'Every schedule game must be declared by exactly one GameDay slot',
    )
  }
  if (gameEntryById.size !== gameById.size) {
    throw invalidReadModel(
      'game_entry_mapping_invalid',
      'Normalized game entries must map one-to-one with schedule games',
    )
  }
  for (const gameEntryId of gameEntryById.keys()) {
    if (!gameById.has(gameEntryId)) {
      throw invalidReadModel(
        'game_entry_mapping_invalid',
        `Normalized game entry ${gameEntryId} has no schedule game`,
      )
    }
  }

  return {
    teamById,
    managedTeamId: validManagedTeamId,
    currentDate: validCurrentDate,
    resolvedGames: Object.freeze(resolvedGames),
  }
}

function validateCalendarEntryCollection(
  entries: readonly CalendarEntryViewModel[],
  teamById: ReadonlyMap<TeamId, Team>,
  managedTeamId: TeamId | null,
): void {
  if (!Array.isArray(entries)) {
    throw invalidReadModel(
      'calendar_entry_invalid',
      'Calendar entries must be an array',
    )
  }

  const entryIds = new Set<string>()
  for (const entry of entries) {
    if (
      entry === null ||
      typeof entry !== 'object' ||
      typeof entry.entryId !== 'string' ||
      entry.entryId.length === 0 ||
      !Array.isArray(entry.teamIds) ||
      typeof entry.isManagedTeamEntry !== 'boolean'
    ) {
      throw invalidReadModel(
        'calendar_entry_invalid',
        'Calendar entries must use the normalized M2.4 structure',
      )
    }
    if (!Object.isFrozen(entry) || !Object.isFrozen(entry.teamIds)) {
      throw invalidReadModel(
        'calendar_entry_invalid',
        `Calendar entry ${entry.entryId} must be immutable`,
      )
    }
    if (entryIds.has(entry.entryId)) {
      throw invalidReadModel(
        'duplicate_calendar_entry_id',
        `Calendar entry ID ${entry.entryId} appears more than once`,
      )
    }
    entryIds.add(entry.entryId)

    if (entry.date !== null) {
      try {
        parseLocalDate(entry.date)
      } catch (error) {
        throw invalidReadModel(
          'calendar_entry_invalid',
          `Calendar entry ${entry.entryId} has an invalid placement date: ${getErrorMessage(error)}`,
        )
      }
    }

    const validEntryTeamIds: TeamId[] = []
    for (const teamId of entry.teamIds) {
      let validTeamId
      try {
        validTeamId = parseTeamId(teamId)
      } catch (error) {
        throw invalidReadModel(
          'calendar_entry_invalid',
          `Calendar entry ${entry.entryId} has an invalid TeamId: ${getErrorMessage(error)}`,
        )
      }
      if (!teamById.has(validTeamId)) {
        throw invalidReadModel(
          'calendar_entry_invalid',
          `Calendar entry ${entry.entryId} references foreign team ${validTeamId}`,
        )
      }
      validEntryTeamIds.push(validTeamId)
    }

    const expectedManagedMarker =
      managedTeamId !== null &&
      validEntryTeamIds.includes(managedTeamId)
    if (entry.isManagedTeamEntry !== expectedManagedMarker) {
      throw invalidReadModel(
        'managed_team_context_mismatch',
        `Calendar entry ${entry.entryId} does not match the supplied managed-team context`,
      )
    }
  }
}

function validateScheduleGames(
  schedule: LeagueSchedule,
  seasonId: ReturnType<typeof parseSeasonId>,
  teamById: ReadonlyMap<TeamId, Team>,
): ReadonlyMap<GameId, ScheduledGame> {
  const gameById = new Map<GameId, ScheduledGame>()

  for (const game of schedule.games) {
    const gameId = parseScheduleGameId(game.id)
    if (gameById.has(gameId)) {
      throw invalidReadModel(
        'schedule_invalid',
        `GameId ${gameId} appears more than once`,
      )
    }
    gameById.set(gameId, game)

    let gameSeasonId: ReturnType<typeof parseSeasonId>
    try {
      gameSeasonId = parseSeasonId(game.seasonId)
      parseGameDayId(game.gameDayId)
      createScheduledGameCalendarProjection(game)
    } catch (error) {
      throw invalidReadModel(
        'schedule_invalid',
        `Game ${gameId} has invalid identity or date fields: ${getErrorMessage(error)}`,
      )
    }
    if (gameSeasonId !== seasonId) {
      throw invalidReadModel(
        'schedule_invalid',
        `Game ${gameId} references a different season`,
      )
    }
    const homeTeamId = parseScheduleTeamId(game.homeTeamId, gameId, 'home')
    const awayTeamId = parseScheduleTeamId(game.awayTeamId, gameId, 'away')
    if (homeTeamId === awayTeamId) {
      throw invalidReadModel(
        'schedule_invalid',
        `Game ${gameId} cannot assign one team twice`,
      )
    }
    if (!teamById.has(homeTeamId) || !teamById.has(awayTeamId)) {
      throw invalidReadModel(
        'schedule_invalid',
        `Game ${gameId} references a team outside the supplied league`,
      )
    }

    if (!Number.isSafeInteger(game.meetingNumber) || game.meetingNumber < 1) {
      throw invalidReadModel(
        'schedule_invalid',
        `Game ${gameId} must have a positive safe meeting number`,
      )
    }
    parseScheduleStage(game.stage)
  }

  return gameById
}

function validateGameDay(
  gameDay: GameDay,
  gameDayIndex: number,
  seasonId: ReturnType<typeof parseSeasonId>,
  seenGameDayIds: Set<GameDayId>,
): GameDayId {
  let gameDayId
  try {
    gameDayId = parseGameDayId(gameDay.id)
    if (parseSeasonId(gameDay.seasonId) !== seasonId) {
      throw new RangeError('GameDay references a different season')
    }
    parseLocalDate(gameDay.scheduledDate)
  } catch (error) {
    throw invalidReadModel(
      'schedule_invalid',
      `GameDay at index ${gameDayIndex} is invalid: ${getErrorMessage(error)}`,
    )
  }

  if (seenGameDayIds.has(gameDayId)) {
    throw invalidReadModel(
      'schedule_invalid',
      `GameDayId ${gameDayId} appears more than once`,
    )
  }
  seenGameDayIds.add(gameDayId)
  if (gameDay.sequenceNumber !== gameDayIndex + 1) {
    throw invalidReadModel(
      'schedule_invalid',
      `GameDay ${gameDayId} has sequence ${gameDay.sequenceNumber}; expected ${gameDayIndex + 1}`,
    )
  }
  if (!Array.isArray(gameDay.gameIds)) {
    throw invalidReadModel(
      'schedule_invalid',
      `GameDay ${gameDayId} must contain an ordered game-ID array`,
    )
  }
  if (new Set(gameDay.gameIds).size !== gameDay.gameIds.length) {
    throw invalidReadModel(
      'schedule_invalid',
      `GameDay ${gameDayId} declares a GameId more than once`,
    )
  }

  return gameDayId
}

function createGameEntryMap(
  entries: readonly CalendarEntryViewModel[],
): ReadonlyMap<GameId, CalendarEntryViewModel> {
  const gameEntryById = new Map<GameId, CalendarEntryViewModel>()

  for (const entry of entries) {
    if (entry.kind !== 'game') continue
    let gameId
    try {
      gameId = parseGameId(entry.sourceId)
    } catch (error) {
      throw invalidReadModel(
        'game_entry_mapping_invalid',
        `Game entry ${entry.entryId} has an invalid source GameId: ${getErrorMessage(error)}`,
      )
    }
    if (gameEntryById.has(gameId)) {
      throw invalidReadModel(
        'game_entry_mapping_invalid',
        `Game ${gameId} has more than one normalized calendar entry`,
      )
    }
    gameEntryById.set(gameId, entry)
  }

  return gameEntryById
}

function validateGameEntryMapping(
  game: ScheduledGame,
  entry: CalendarEntryViewModel,
  managedTeamId: TeamId | null,
): void {
  let dateProjection
  try {
    dateProjection = createScheduledGameCalendarProjection(game)
  } catch (error) {
    throw invalidReadModel(
      'schedule_invalid',
      `Game ${game.id} has invalid date fields: ${getErrorMessage(error)}`,
    )
  }
  const expectedManagedMarker =
    managedTeamId !== null && gameContainsTeam(game, managedTeamId)

  if (
    entry.entryId !== `game:${game.id}` ||
    entry.sourceId !== game.id ||
    entry.kind !== 'game' ||
    entry.gameDayId !== game.gameDayId ||
    entry.competitionStage !== game.stage ||
    entry.status !== dateProjection.status ||
    entry.date !== dateProjection.placementDate ||
    entry.originalDate !== dateProjection.originalScheduledDate ||
    entry.currentScheduledDate !== dateProjection.currentScheduledDate ||
    entry.actualDate !== dateProjection.actualDate ||
    entry.homeTeamId !== game.homeTeamId ||
    entry.awayTeamId !== game.awayTeamId ||
    entry.teamIds.length !== 2 ||
    entry.teamIds[0] !== game.homeTeamId ||
    entry.teamIds[1] !== game.awayTeamId ||
    entry.isManagedTeamEntry !== expectedManagedMarker
  ) {
    throw invalidReadModel(
      'game_entry_mapping_invalid',
      `Normalized entry for game ${game.id} does not match its authoritative schedule record`,
    )
  }

  if (entry.date !== null) {
    parseLocalDate(entry.date)
  }
}

function parseScheduleStage(stage: ScheduleStage): ScheduleStage {
  switch (stage) {
    case 'preseason':
    case 'regular_season':
    case 'cup':
    case 'play_in':
    case 'postseason':
      return stage
    default:
      return assertNever(stage, 'Schedule stage')
  }
}

function createTeamScheduleRowDraft(
  resolved: ResolvedScheduleGame,
  inspectedTeamId: TeamId,
  managedTeamId: TeamId | null,
  currentDate: LocalDate,
): TeamScheduleRowDraft {
  const shared = createSharedGameProjection(resolved, currentDate)
  const site: TeamScheduleSite =
    shared.homeTeamId === inspectedTeamId ? 'home' : 'away'
  const opponent =
    site === 'home' ? resolved.awayTeam : resolved.homeTeam

  return {
    gameId: shared.gameId,
    gameDayId: shared.gameDayId,
    scheduleSequence: shared.scheduleSequence,
    gameDaySequence: shared.gameDaySequence,
    meetingNumber: shared.meetingNumber,
    stage: shared.stage,
    status: shared.status,
    placementDate: shared.placementDate,
    originalScheduledDate: shared.originalScheduledDate,
    currentScheduledDate: shared.currentScheduledDate,
    actualDate: shared.actualDate,
    month: shared.month,
    inspectedTeamId,
    opponentTeamId: opponent.id,
    opponentName: formatTeamName(opponent),
    opponentAbbreviation: opponent.abbreviation,
    homeTeamId: shared.homeTeamId,
    awayTeamId: shared.awayTeamId,
    site,
    isManagedTeamSchedule:
      managedTeamId !== null && inspectedTeamId === managedTeamId,
    involvesManagedTeam:
      managedTeamId !== null &&
      gameContainsTeam(resolved.game, managedTeamId),
    isCurrentDate: shared.isCurrentDate,
    isPastDate: shared.isPastDate,
    isFutureDate: shared.isFutureDate,
    isUndated: shared.isUndated,
  }
}

function createSharedGameProjection(
  resolved: ResolvedScheduleGame,
  currentDate: LocalDate,
): SharedGameProjection {
  const placementDate = resolved.entry.date
  const temporal = getTemporalState(placementDate, currentDate)

  return {
    gameId: resolved.game.id,
    gameDayId: resolved.gameDay.id,
    scheduleSequence: resolved.scheduleSequence,
    gameDaySequence: resolved.gameDay.sequenceNumber,
    meetingNumber: resolved.game.meetingNumber,
    stage: resolved.game.stage,
    status: resolved.game.status,
    placementDate,
    originalScheduledDate: resolved.game.originalScheduledDate,
    currentScheduledDate: resolved.entry.currentScheduledDate,
    actualDate: resolved.entry.actualDate,
    month:
      placementDate === null
        ? null
        : yearMonthFromLocalDate(placementDate),
    homeTeamId: resolved.game.homeTeamId,
    awayTeamId: resolved.game.awayTeamId,
    ...temporal,
  }
}

function getTemporalState(
  placementDate: LocalDate | null,
  currentDate: LocalDate,
): Pick<
  SharedGameProjection,
  'isCurrentDate' | 'isPastDate' | 'isFutureDate' | 'isUndated'
> {
  if (placementDate === null) {
    return {
      isCurrentDate: false,
      isPastDate: false,
      isFutureDate: false,
      isUndated: true,
    }
  }

  const comparison = compareLocalDates(placementDate, currentDate)
  return {
    isCurrentDate: comparison === 0,
    isPastDate: comparison < 0,
    isFutureDate: comparison > 0,
    isUndated: false,
  }
}

function findNextScheduledGameId(
  rows: readonly TeamScheduleRowDraft[],
  currentDate: LocalDate,
): GameId | null {
  let nextRow: TeamScheduleRowDraft | null = null

  for (const row of rows) {
    if (
      row.placementDate === null ||
      row.status === 'completed' ||
      row.status === 'cancelled' ||
      compareLocalDates(row.placementDate, currentDate) < 0
    ) {
      continue
    }
    if (nextRow === null || compareNextRows(row, nextRow) < 0) {
      nextRow = row
    }
  }

  return nextRow?.gameId ?? null
}

function compareNextRows(
  left: TeamScheduleRowDraft,
  right: TeamScheduleRowDraft,
): -1 | 0 | 1 {
  if (left.placementDate === null || right.placementDate === null) {
    throw invalidReadModel(
      'team_schedule_accounting_invalid',
      'Next-game comparison requires dated rows',
    )
  }

  const dateComparison = compareLocalDates(
    left.placementDate,
    right.placementDate,
  )
  if (dateComparison !== 0) return dateComparison
  if (left.scheduleSequence < right.scheduleSequence) return -1
  if (left.scheduleSequence > right.scheduleSequence) return 1
  if (left.gameId < right.gameId) return -1
  if (left.gameId > right.gameId) return 1
  return 0
}

function createMonthGroups(
  rows: readonly TeamScheduleRowViewModel[],
): readonly TeamScheduleMonthGroupViewModel[] {
  const rowsByMonth = new Map<YearMonth, TeamScheduleRowViewModel[]>()
  for (const row of rows) {
    if (row.month === null) continue
    const monthRows = rowsByMonth.get(row.month) ?? []
    monthRows.push(row)
    rowsByMonth.set(row.month, monthRows)
  }

  const months = [...rowsByMonth.keys()].sort(compareYearMonths)
  return Object.freeze(
    months.map((month) => {
      const monthRows = Object.freeze([
        ...(rowsByMonth.get(month) ?? []),
      ])
      return Object.freeze({
        month,
        rows: monthRows,
        gameCount: monthRows.length,
        homeGameCount: countRows(
          monthRows,
          (row) => row.site === 'home',
        ),
        awayGameCount: countRows(
          monthRows,
          (row) => row.site === 'away',
        ),
        managedTeamGameCount: countRows(
          monthRows,
          (row) => row.involvesManagedTeam,
        ),
        scheduledCount: countStatus(monthRows, 'scheduled'),
        completedCount: countStatus(monthRows, 'completed'),
        postponedCount: countStatus(monthRows, 'postponed'),
        cancelledCount: countStatus(monthRows, 'cancelled'),
        containsNextScheduledGame: monthRows.some(
          (row) => row.isNextScheduledGame,
        ),
      })
    }),
  )
}

function validateTeamScheduleAccounting(
  rows: readonly TeamScheduleRowViewModel[],
  monthGroups: readonly TeamScheduleMonthGroupViewModel[],
  undatedGroup: UndatedTeamScheduleGroupViewModel,
  nextScheduledGameId: GameId | null,
  expectedGameCount: number,
): void {
  const datedRows = monthGroups.flatMap((group) => group.rows)
  const authoritativeIds = new Set(rows.map((row) => row.gameId))
  const groupedIds = new Set([
    ...datedRows.map((row) => row.gameId),
    ...undatedGroup.rows.map((row) => row.gameId),
  ])
  const nextRows = rows.filter((row) => row.isNextScheduledGame)

  if (
    rows.length !== expectedGameCount ||
    authoritativeIds.size !== rows.length ||
    datedRows.length + undatedGroup.gameCount !== rows.length ||
    groupedIds.size !== rows.length ||
    [...groupedIds].some((gameId) => !authoritativeIds.has(gameId)) ||
    countRows(rows, (row) => row.site === 'home') +
      countRows(rows, (row) => row.site === 'away') !==
      rows.length ||
    nextRows.length > 1 ||
    (nextScheduledGameId === null
      ? nextRows.length !== 0
      : nextRows.length !== 1 ||
        nextRows[0].gameId !== nextScheduledGameId)
  ) {
    throw invalidReadModel(
      'team_schedule_accounting_invalid',
      'Team Schedule rows, groups, totals, or next-game marker are inconsistent',
    )
  }

  for (const group of monthGroups) {
    if (
      group.rows.length === 0 ||
      group.gameCount !== group.rows.length ||
      group.rows.some((row) => row.month !== group.month) ||
      group.scheduledCount +
        group.completedCount +
        group.postponedCount +
        group.cancelledCount !==
        group.gameCount
    ) {
      throw invalidReadModel(
        'team_schedule_accounting_invalid',
        `Month group ${group.month} has inconsistent rows or counts`,
      )
    }
  }
}

function parseContextTeamId(
  value: unknown,
  teamById: ReadonlyMap<TeamId, Team>,
  context: 'inspected' | 'managed',
): TeamId {
  let teamId
  try {
    teamId = parseTeamId(value)
  } catch (error) {
    throw invalidReadModel(
      context === 'inspected'
        ? 'inspected_team_invalid'
        : 'managed_team_invalid',
      `${capitalize(context)} TeamId is invalid: ${getErrorMessage(error)}`,
    )
  }
  if (!teamById.has(teamId)) {
    throw invalidReadModel(
      context === 'inspected'
        ? 'inspected_team_unknown'
        : 'managed_team_unknown',
      `${capitalize(context)} team ${teamId} does not belong to the supplied league`,
    )
  }
  return teamId
}

function parsePerspectiveTeamId(
  value: unknown,
  teamById: ReadonlyMap<TeamId, Team>,
): TeamId {
  let teamId
  try {
    teamId = parseTeamId(value)
  } catch (error) {
    throw invalidReadModel(
      'perspective_team_invalid',
      `Perspective TeamId is invalid: ${getErrorMessage(error)}`,
    )
  }
  if (!teamById.has(teamId)) {
    throw invalidReadModel(
      'perspective_team_unknown',
      `Perspective team ${teamId} does not belong to the supplied league`,
    )
  }
  return teamId
}

function parseCurrentDate(value: unknown): LocalDate {
  try {
    return parseLocalDate(value)
  } catch (error) {
    throw invalidReadModel(
      'current_date_invalid',
      `Current date is invalid: ${getErrorMessage(error)}`,
    )
  }
}

function parseSelectedGameId(value: unknown): GameId {
  try {
    return parseGameId(value)
  } catch (error) {
    throw invalidReadModel(
      'selected_game_invalid',
      `Selected GameId is invalid: ${getErrorMessage(error)}`,
    )
  }
}

function parseScheduleGameId(value: unknown): GameId {
  try {
    return parseGameId(value)
  } catch (error) {
    throw invalidReadModel(
      'schedule_invalid',
      `Schedule contains an invalid GameId: ${getErrorMessage(error)}`,
    )
  }
}

function parseScheduleTeamId(
  value: unknown,
  gameId: GameId,
  role: 'home' | 'away',
): TeamId {
  try {
    return parseTeamId(value)
  } catch (error) {
    throw invalidReadModel(
      'schedule_invalid',
      `Game ${gameId} has an invalid ${role} TeamId: ${getErrorMessage(error)}`,
    )
  }
}

function requireTeam(
  teamById: ReadonlyMap<TeamId, Team>,
  teamId: TeamId,
  code: ScheduleReadModelErrorCode,
  label: string,
): Team {
  const team = teamById.get(teamId)
  if (team === undefined) {
    throw invalidReadModel(
      code,
      `${label} ${teamId} does not belong to the supplied league`,
    )
  }
  return team
}

function createTeamIdentity(team: Team): GameDetailsTeamViewModel {
  return Object.freeze({
    teamId: team.id,
    name: formatTeamName(team),
    abbreviation: team.abbreviation,
  })
}

function formatTeamName(team: Team): string {
  return `${team.city} ${team.nickname}`
}

function gameContainsTeam(game: ScheduledGame, teamId: TeamId): boolean {
  return game.homeTeamId === teamId || game.awayTeamId === teamId
}

function countRows(
  rows: readonly TeamScheduleRowViewModel[],
  predicate: (row: TeamScheduleRowViewModel) => boolean,
): number {
  return rows.reduce(
    (count, row) => count + (predicate(row) ? 1 : 0),
    0,
  )
}

function countStatus(
  rows: readonly TeamScheduleRowViewModel[],
  status: ScheduledGameStatus,
): number {
  return countRows(rows, (row) => row.status === status)
}

function capitalize(value: string): string {
  return `${value.slice(0, 1).toUpperCase()}${value.slice(1)}`
}

function invalidReadModel(
  code: ScheduleReadModelErrorCode,
  message: string,
): InvalidScheduleReadModelError {
  return new InvalidScheduleReadModelError(code, message)
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}

function assertNever(value: never, label: string): never {
  throw invalidReadModel(
    'schedule_invalid',
    `${label} is unsupported: ${String(value)}`,
  )
}
