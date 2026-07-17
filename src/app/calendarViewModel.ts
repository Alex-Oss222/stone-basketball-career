import {
  parseCalendarEventId,
  parseGameDayId,
  parseGameId,
  parseLeagueId,
  parseScheduleId,
  parseSeasonId,
  parseTeamId,
} from '../domain/ids'
import type {
  CalendarEventId,
  GameDayId,
  GameId,
  TeamId,
} from '../domain/ids'
import type { League, Team } from '../domain/league'
import { assertValidLeague } from '../domain/leagueValidation'
import { parseLocalDate } from '../domain/localDate'
import type { LocalDate } from '../domain/localDate'
import type {
  LeagueSchedule,
  ScheduleStage,
  ScheduledGame,
} from '../domain/schedule'
import { parseSeasonCalendar } from '../domain/seasonCalendar'
import type {
  CalendarDateStatus,
  CalendarEvent,
  CalendarEventKind,
  SeasonCalendar,
} from '../domain/seasonCalendar'
import {
  parseYearMonth,
  yearMonthFromLocalDate,
} from '../domain/yearMonth'
import type { YearMonth } from '../domain/yearMonth'

export type CalendarEntryKind = 'game' | 'league_event' | 'team_event'

/** Calendar events already define the complete shared presentation vocabulary. */
export type CalendarEntryStatus = CalendarDateStatus

export interface CalendarEntryViewModel {
  /** Namespaced source identity, never an array index. */
  readonly entryId: string
  readonly sourceId: GameId | CalendarEventId
  readonly kind: CalendarEntryKind
  /** Current calendar placement date; null means explicitly undated/TBA. */
  readonly date: LocalDate | null
  readonly originalDate: LocalDate | null
  readonly currentScheduledDate: LocalDate | null
  readonly actualDate: LocalDate | null
  readonly status: CalendarEntryStatus
  readonly competitionStage: ScheduleStage | null
  readonly title: string
  readonly shortLabel: string
  /**
   * Games use [homeTeamId, awayTeamId], team events use one TeamId, and
   * league events use an empty collection.
   */
  readonly teamIds: readonly TeamId[]
  readonly isManagedTeamEntry: boolean
  readonly homeTeamId: TeamId | null
  readonly awayTeamId: TeamId | null
  readonly gameDayId: GameDayId | null
  readonly calendarEventKind: CalendarEventKind | null
  readonly sortKey: string
}

export interface CreateCalendarEntriesInput {
  readonly league: League
  readonly schedule: LeagueSchedule
  readonly seasonCalendar: SeasonCalendar
  readonly managedTeamId: TeamId | null
}

export interface CalendarDateGroup {
  readonly date: LocalDate
  readonly entries: readonly CalendarEntryViewModel[]
}

interface ValidatedCalendarContext {
  readonly teamById: ReadonlyMap<TeamId, Team>
  readonly managedTeamId: TeamId | null
  readonly calendar: SeasonCalendar
  readonly gameDayIds: ReadonlySet<GameDayId>
}

/**
 * Creates one immutable, presentation-safe entry for every authoritative game
 * and calendar event. The result is derived application data and is never a
 * persistence DTO.
 */
export function createCalendarEntries({
  league,
  schedule,
  seasonCalendar,
  managedTeamId,
}: CreateCalendarEntriesInput): readonly CalendarEntryViewModel[] {
  const context = validateCalendarContext(
    league,
    schedule,
    seasonCalendar,
    managedTeamId,
  )
  const entries: CalendarEntryViewModel[] = []
  const gameIds = new Set<GameId>()

  for (const game of schedule.games) {
    const gameId = parseGameId(game.id)
    if (gameIds.has(gameId)) {
      throw new RangeError(`Calendar source contains duplicate GameId ${gameId}`)
    }
    gameIds.add(gameId)
    entries.push(createGameEntry(game, schedule, context))
  }

  for (const event of context.calendar.events) {
    entries.push(createEventEntry(event, context))
  }

  const entryIds = new Set<string>()
  for (const entry of entries) {
    if (entryIds.has(entry.entryId)) {
      throw new RangeError(
        `Calendar normalization produced duplicate entryId ${entry.entryId}`,
      )
    }
    entryIds.add(entry.entryId)
  }

  return sortAndFreezeEntries(entries)
}

export function getDatedCalendarEntries(
  entries: readonly CalendarEntryViewModel[],
): readonly CalendarEntryViewModel[] {
  return selectCalendarEntries(entries, (entry) => entry.date !== null)
}

export function getUndatedCalendarEntries(
  entries: readonly CalendarEntryViewModel[],
): readonly CalendarEntryViewModel[] {
  return selectCalendarEntries(entries, (entry) => entry.date === null)
}

export function getCalendarEntriesForDate(
  entries: readonly CalendarEntryViewModel[],
  date: LocalDate,
): readonly CalendarEntryViewModel[] {
  const validDate = parseLocalDate(date)
  return selectCalendarEntries(entries, (entry) => entry.date === validDate)
}

export function getCalendarEntriesForMonth(
  entries: readonly CalendarEntryViewModel[],
  month: YearMonth,
): readonly CalendarEntryViewModel[] {
  const validMonth = parseYearMonth(month)
  return selectCalendarEntries(
    entries,
    (entry) =>
      entry.date !== null &&
      yearMonthFromLocalDate(entry.date) === validMonth,
  )
}

export function getCalendarEntriesForTeam(
  entries: readonly CalendarEntryViewModel[],
  teamId: TeamId,
): readonly CalendarEntryViewModel[] {
  const validTeamId = parseTeamId(teamId)
  return selectCalendarEntries(entries, (entry) =>
    entry.teamIds.includes(validTeamId),
  )
}

export function getManagedTeamCalendarEntries(
  entries: readonly CalendarEntryViewModel[],
): readonly CalendarEntryViewModel[] {
  return selectCalendarEntries(entries, (entry) => entry.isManagedTeamEntry)
}

export function groupCalendarEntriesByDate(
  entries: readonly CalendarEntryViewModel[],
): readonly CalendarDateGroup[] {
  const datedEntries = getDatedCalendarEntries(entries)
  const groups: Array<{
    date: LocalDate
    entries: CalendarEntryViewModel[]
  }> = []

  for (const entry of datedEntries) {
    if (entry.date === null) {
      throw new RangeError('Dated calendar selector returned an undated entry')
    }

    const previousGroup = groups[groups.length - 1]
    if (previousGroup?.date === entry.date) {
      previousGroup.entries.push(entry)
    } else {
      groups.push({ date: entry.date, entries: [entry] })
    }
  }

  return Object.freeze(
    groups.map((group) =>
      Object.freeze({
        date: group.date,
        entries: Object.freeze([...group.entries]),
      }),
    ),
  )
}

export function createDayAgenda(
  entries: readonly CalendarEntryViewModel[],
  date: LocalDate,
): readonly CalendarEntryViewModel[] {
  return getCalendarEntriesForDate(entries, date)
}

function validateCalendarContext(
  league: League,
  schedule: LeagueSchedule,
  seasonCalendar: SeasonCalendar,
  managedTeamId: TeamId | null,
): ValidatedCalendarContext {
  assertValidLeague(league)
  const leagueId = parseLeagueId(league.id)
  const scheduleLeagueId = parseLeagueId(schedule.leagueId)
  parseScheduleId(schedule.id)
  const scheduleSeasonId = parseSeasonId(schedule.seasonId)
  const calendar = parseSeasonCalendar(seasonCalendar)

  if (scheduleLeagueId !== leagueId) {
    throw new RangeError(
      `Schedule league ${scheduleLeagueId} does not match supplied league ${leagueId}`,
    )
  }
  if (calendar.seasonId !== scheduleSeasonId) {
    throw new RangeError(
      `Season calendar ${calendar.id} and schedule ${schedule.id} reference different seasons`,
    )
  }

  const teamById = new Map(
    league.teams.map((team) => [parseTeamId(team.id), team] as const),
  )
  const validManagedTeamId =
    managedTeamId === null ? null : parseTeamId(managedTeamId)
  if (
    validManagedTeamId !== null &&
    !teamById.has(validManagedTeamId)
  ) {
    throw new RangeError(
      `Managed team ${validManagedTeamId} does not belong to league ${leagueId}`,
    )
  }

  const gameDayIds = validateGameDays(schedule)
  validateGameDayMembership(schedule, gameDayIds)

  for (const event of calendar.events) {
    if (event.seasonId !== scheduleSeasonId) {
      throw new RangeError(
        `Calendar event ${event.id} references a different season`,
      )
    }
    if (event.scope === 'team' && !teamById.has(event.teamId)) {
      throw new RangeError(
        `Calendar event ${event.id} references foreign team ${event.teamId}`,
      )
    }
  }

  return {
    teamById,
    managedTeamId: validManagedTeamId,
    calendar,
    gameDayIds,
  }
}

function validateGameDays(schedule: LeagueSchedule): ReadonlySet<GameDayId> {
  const gameDayIds = new Set<GameDayId>()

  for (const gameDay of schedule.gameDays) {
    const gameDayId = parseGameDayId(gameDay.id)
    if (gameDayIds.has(gameDayId)) {
      throw new RangeError(
        `Calendar schedule contains duplicate GameDayId ${gameDayId}`,
      )
    }
    gameDayIds.add(gameDayId)

    if (parseSeasonId(gameDay.seasonId) !== schedule.seasonId) {
      throw new RangeError(
        `Game day ${gameDayId} references a different season`,
      )
    }
    if (
      !Number.isSafeInteger(gameDay.sequenceNumber) ||
      gameDay.sequenceNumber < 1
    ) {
      throw new RangeError(
        `Game day ${gameDayId} must have a positive safe sequence number`,
      )
    }
    parseLocalDate(gameDay.scheduledDate)

    const declaredGameIds = new Set<GameId>()
    for (const sourceGameId of gameDay.gameIds) {
      const gameId = parseGameId(sourceGameId)
      if (declaredGameIds.has(gameId)) {
        throw new RangeError(
          `Game day ${gameDayId} contains duplicate GameId ${gameId}`,
        )
      }
      declaredGameIds.add(gameId)
    }
  }

  return gameDayIds
}

function validateGameDayMembership(
  schedule: LeagueSchedule,
  gameDayIds: ReadonlySet<GameDayId>,
): void {
  const gameById = new Map<GameId, ScheduledGame>()
  for (const game of schedule.games) {
    const gameId = parseGameId(game.id)
    if (gameById.has(gameId)) {
      throw new RangeError(`Calendar schedule contains duplicate GameId ${gameId}`)
    }
    gameById.set(gameId, game)
  }

  const declarationCounts = new Map<GameId, number>()
  for (const gameDay of schedule.gameDays) {
    for (const gameId of gameDay.gameIds) {
      const game = gameById.get(gameId)
      if (game === undefined) {
        throw new RangeError(
          `Game day ${gameDay.id} references unknown game ${gameId}`,
        )
      }
      if (game.gameDayId !== gameDay.id) {
        throw new RangeError(
          `Game ${game.id} does not reference declaring game day ${gameDay.id}`,
        )
      }
      declarationCounts.set(gameId, (declarationCounts.get(gameId) ?? 0) + 1)
    }
  }

  for (const game of schedule.games) {
    const gameDayId = parseGameDayId(game.gameDayId)
    if (!gameDayIds.has(gameDayId)) {
      throw new RangeError(
        `Game ${game.id} references unknown game day ${gameDayId}`,
      )
    }
    if (declarationCounts.get(game.id) !== 1) {
      throw new RangeError(
        `Game ${game.id} must be declared by exactly one game day`,
      )
    }
  }
}

function createGameEntry(
  game: ScheduledGame,
  schedule: LeagueSchedule,
  context: ValidatedCalendarContext,
): CalendarEntryViewModel {
  const gameId = parseGameId(game.id)
  const seasonId = parseSeasonId(game.seasonId)
  if (seasonId !== schedule.seasonId) {
    throw new RangeError(`Game ${gameId} references a different season`)
  }

  const gameDayId = parseGameDayId(game.gameDayId)
  if (!context.gameDayIds.has(gameDayId)) {
    throw new RangeError(
      `Game ${gameId} references unknown game day ${gameDayId}`,
    )
  }

  const homeTeamId = parseTeamId(game.homeTeamId)
  const awayTeamId = parseTeamId(game.awayTeamId)
  if (homeTeamId === awayTeamId) {
    throw new RangeError(`Game ${gameId} cannot assign one team twice`)
  }

  const homeTeam = context.teamById.get(homeTeamId)
  const awayTeam = context.teamById.get(awayTeamId)
  if (homeTeam === undefined || awayTeam === undefined) {
    throw new RangeError(`Game ${gameId} references a foreign league team`)
  }

  if (!Number.isSafeInteger(game.meetingNumber) || game.meetingNumber < 1) {
    throw new RangeError(
      `Game ${gameId} must have a positive safe meeting number`,
    )
  }

  const competitionStage = validateScheduleStage(game.stage)
  const originalDate = parseLocalDate(game.originalScheduledDate)
  const currentScheduledDate =
    game.currentScheduledDate === null
      ? null
      : parseLocalDate(game.currentScheduledDate)
  const actualDate =
    game.actualDate === undefined ? null : parseLocalDate(game.actualDate)
  const status = validateGameLifecycle(
    game,
    originalDate,
    currentScheduledDate,
    actualDate,
  )
  const date = getGamePlacementDate(
    status,
    originalDate,
    currentScheduledDate,
    actualDate,
  )
  const teamIds = Object.freeze([homeTeamId, awayTeamId])
  const isManagedTeamEntry =
    context.managedTeamId !== null &&
    teamIds.includes(context.managedTeamId)
  const entryId = `game:${gameId}`
  const kind = 'game' as const

  return Object.freeze({
    entryId,
    sourceId: gameId,
    kind,
    date,
    originalDate,
    currentScheduledDate,
    actualDate,
    status,
    competitionStage,
    title: `${formatTeamName(awayTeam)} at ${formatTeamName(homeTeam)}`,
    shortLabel: `${awayTeam.abbreviation} @ ${homeTeam.abbreviation}`,
    teamIds,
    isManagedTeamEntry,
    homeTeamId,
    awayTeamId,
    gameDayId,
    calendarEventKind: null,
    sortKey: createSortKey(entryId, kind, date, isManagedTeamEntry),
  })
}

function createEventEntry(
  event: CalendarEvent,
  context: ValidatedCalendarContext,
): CalendarEntryViewModel {
  const eventId = parseCalendarEventId(event.id)
  const status = validateEventStatus(event)
  const date = getEventPlacementDate(event, status)
  const kind =
    event.scope === 'league' ? ('league_event' as const) : ('team_event' as const)
  const teamIds =
    event.scope === 'league'
      ? Object.freeze([] as TeamId[])
      : Object.freeze([parseTeamId(event.teamId)])
  const isManagedTeamEntry =
    context.managedTeamId !== null &&
    teamIds.includes(context.managedTeamId)
  const entryId = `calendar-event:${eventId}`

  return Object.freeze({
    entryId,
    sourceId: eventId,
    kind,
    date,
    originalDate: event.originalScheduledDate,
    currentScheduledDate: event.scheduledDate,
    actualDate: event.actualDate,
    status,
    competitionStage: null,
    title: event.title,
    shortLabel: event.title,
    teamIds,
    isManagedTeamEntry,
    homeTeamId: null,
    awayTeamId: null,
    gameDayId: null,
    calendarEventKind: event.kind,
    sortKey: createSortKey(entryId, kind, date, isManagedTeamEntry),
  })
}

function validateGameLifecycle(
  game: ScheduledGame,
  originalDate: LocalDate,
  currentScheduledDate: LocalDate | null,
  actualDate: LocalDate | null,
): CalendarEntryStatus {
  switch (game.status) {
    case 'scheduled':
      if (
        currentScheduledDate === null ||
        currentScheduledDate !== originalDate ||
        actualDate !== null
      ) {
        throw new RangeError(
          `Scheduled game ${game.id} has inconsistent lifecycle dates`,
        )
      }
      return 'scheduled'
    case 'postponed':
      if (actualDate !== null) {
        throw new RangeError(
          `Postponed game ${game.id} cannot contain an actual date`,
        )
      }
      return 'postponed'
    case 'completed':
      if (currentScheduledDate === null || actualDate === null) {
        throw new RangeError(
          `Completed game ${game.id} requires current and actual dates`,
        )
      }
      return 'completed'
    case 'cancelled':
      if (actualDate !== null) {
        throw new RangeError(
          `Cancelled game ${game.id} cannot contain an actual date`,
        )
      }
      return 'cancelled'
    default:
      return assertNever(game.status, 'ScheduledGame status')
  }
}

function getGamePlacementDate(
  status: CalendarEntryStatus,
  originalDate: LocalDate,
  currentScheduledDate: LocalDate | null,
  actualDate: LocalDate | null,
): LocalDate | null {
  switch (status) {
    case 'scheduled':
      return requireDate(currentScheduledDate, 'Scheduled game')
    case 'postponed':
      return currentScheduledDate
    case 'completed':
      return requireDate(actualDate, 'Completed game')
    case 'cancelled':
      return currentScheduledDate ?? originalDate
    case 'tba':
    case 'estimated':
    case 'announced':
      throw new RangeError(`Status ${status} is not a ScheduledGame status`)
    default:
      return assertNever(status, 'Calendar entry status')
  }
}

function validateEventStatus(event: CalendarEvent): CalendarEntryStatus {
  switch (event.dateStatus) {
    case 'tba':
      return 'tba'
    case 'estimated':
      return 'estimated'
    case 'announced':
      return 'announced'
    case 'scheduled':
      return 'scheduled'
    case 'completed':
      return 'completed'
    case 'postponed':
      return 'postponed'
    case 'cancelled':
      return 'cancelled'
    default:
      return assertNever(event.dateStatus, 'CalendarEvent date status')
  }
}

function getEventPlacementDate(
  event: CalendarEvent,
  status: CalendarEntryStatus,
): LocalDate | null {
  switch (status) {
    case 'tba':
      return null
    case 'estimated':
    case 'announced':
    case 'scheduled':
      return requireDate(event.scheduledDate, `${status} calendar event`)
    case 'completed':
      return requireDate(event.actualDate, 'Completed calendar event')
    case 'postponed':
      return event.scheduledDate
    case 'cancelled':
      return event.scheduledDate ?? event.originalScheduledDate
    default:
      return assertNever(status, 'Calendar entry status')
  }
}

function validateScheduleStage(stage: ScheduleStage): ScheduleStage {
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

function formatTeamName(team: Team): string {
  return `${team.city} ${team.nickname}`
}

/**
 * Sort order is dated before undated, then LocalDate, then:
 * league event, managed game, other game, managed team event, other team
 * event. The namespaced entry ID is the unique final tie-breaker.
 */
function createSortKey(
  entryId: string,
  kind: CalendarEntryKind,
  date: LocalDate | null,
  isManagedTeamEntry: boolean,
): string {
  const datedMarker = date === null ? '1' : '0'
  const dateComponent = date ?? '----------'
  const priority = getEntryPriority(kind, isManagedTeamEntry)
  return `${datedMarker}:${dateComponent}:${priority}:${entryId}`
}

function getEntryPriority(
  kind: CalendarEntryKind,
  isManagedTeamEntry: boolean,
): 0 | 1 | 2 | 3 | 4 {
  switch (kind) {
    case 'league_event':
      return 0
    case 'game':
      return isManagedTeamEntry ? 1 : 2
    case 'team_event':
      return isManagedTeamEntry ? 3 : 4
    default:
      return assertNever(kind, 'Calendar entry kind')
  }
}

function selectCalendarEntries(
  entries: readonly CalendarEntryViewModel[],
  predicate: (entry: CalendarEntryViewModel) => boolean,
): readonly CalendarEntryViewModel[] {
  return sortAndFreezeEntries(entries.filter(predicate))
}

function sortAndFreezeEntries(
  entries: readonly CalendarEntryViewModel[],
): readonly CalendarEntryViewModel[] {
  const ordered = [...entries].sort((left, right) => {
    if (left.sortKey < right.sortKey) return -1
    if (left.sortKey > right.sortKey) return 1
    return 0
  })
  return Object.freeze(ordered)
}

function requireDate(
  date: LocalDate | null,
  label: string,
): LocalDate {
  if (date === null) {
    throw new RangeError(`${label} requires an authoritative date`)
  }
  return date
}

function assertNever(value: never, label: string): never {
  throw new RangeError(`${label} is unsupported: ${String(value)}`)
}
