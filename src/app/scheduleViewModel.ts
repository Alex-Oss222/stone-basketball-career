import type { TeamId } from '../domain/ids'
import { compareLocalDates, parseLocalDate } from '../domain/localDate'
import type { LocalDate } from '../domain/localDate'
import type { SeasonPhase } from '../domain/season'
import type {
  LeagueSnapshotV2GameDayDto,
  LeagueSnapshotV2LeagueDto,
  LeagueSnapshotV2LeagueScheduleDto,
  LeagueSnapshotV2ScheduledGameDto,
  LeagueSnapshotV2TeamDto,
} from '../persistence/leagueSnapshotV2'

export type TeamScheduleLocation = 'home' | 'away'
export type TeamScheduleFilter = 'all' | TeamScheduleLocation

export interface TeamScheduleTotals {
  readonly totalGames: number
  readonly homeGames: number
  readonly awayGames: number
}

export interface ScheduleGameDayGroup {
  readonly gameDay: LeagueSnapshotV2GameDayDto
  readonly games: readonly LeagueSnapshotV2ScheduledGameDto[]
}

const MONTH_NAMES = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
] as const

const SEASON_PHASE_LABELS = {
  offseason: 'Offseason',
  training_camp: 'Training camp',
  preseason: 'Preseason',
  regular_season: 'Regular season',
  postseason: 'Postseason',
  complete: 'Complete',
} as const satisfies Readonly<Record<SeasonPhase, string>>

/** Returns a team's games in their authoritative stored schedule order. */
export function getTeamScheduleGames(
  schedule: LeagueSnapshotV2LeagueScheduleDto,
  teamId: TeamId,
): readonly LeagueSnapshotV2ScheduledGameDto[] {
  return schedule.games.filter((game) => isTeamInGame(game, teamId))
}

/** Resolves the opposing stored team without creating substitute display data. */
export function resolveOpponent(
  league: LeagueSnapshotV2LeagueDto,
  game: LeagueSnapshotV2ScheduledGameDto,
  teamId: TeamId,
): LeagueSnapshotV2TeamDto {
  const opponentTeamId = getOpponentTeamId(game, teamId)
  const opponent = league.teams.find((team) => team.id === opponentTeamId)

  if (opponent === undefined) {
    throw new RangeError(
      `Scheduled opponent ${opponentTeamId} does not reference a league team`,
    )
  }

  return opponent
}

/** Returns the selected team's home/away role in one stored matchup. */
export function getTeamLocation(
  game: LeagueSnapshotV2ScheduledGameDto,
  teamId: TeamId,
): TeamScheduleLocation {
  assertDistinctMatchup(game)
  if (game.homeTeamId === teamId) return 'home'
  if (game.awayTeamId === teamId) return 'away'

  throw new RangeError(`Team ${teamId} does not participate in game ${game.id}`)
}

/**
 * Finds the earliest dated, unplayed team game on or after currentDate.
 * Equal-date ties retain authoritative stored game order.
 */
export function findNextScheduledGame(
  schedule: LeagueSnapshotV2LeagueScheduleDto,
  teamId: TeamId,
  currentDate: LocalDate,
): LeagueSnapshotV2ScheduledGameDto | null {
  const parsedCurrentDate = parseLocalDate(currentDate)
  let nextGame: LeagueSnapshotV2ScheduledGameDto | null = null

  for (const game of schedule.games) {
    if (!isUpcomingTeamGame(game, teamId, parsedCurrentDate)) continue
    if (
      nextGame === null ||
      compareKnownScheduledDates(game, nextGame) < 0
    ) {
      nextGame = game
    }
  }

  return nextGame
}

/** Filters upcoming games without sorting or mutating their stored order. */
export function getUpcomingScheduledGames(
  schedule: LeagueSnapshotV2LeagueScheduleDto,
  teamId: TeamId,
  currentDate: LocalDate,
): readonly LeagueSnapshotV2ScheduledGameDto[] {
  const parsedCurrentDate = parseLocalDate(currentDate)
  return schedule.games.filter((game) =>
    isUpcomingTeamGame(game, teamId, parsedCurrentDate),
  )
}

/**
 * Groups games in stored game-day order and uses each game day's stored game-ID
 * order. Valid snapshots make every reference resolvable and unambiguous.
 */
export function groupGamesByGameDay(
  schedule: LeagueSnapshotV2LeagueScheduleDto,
): readonly ScheduleGameDayGroup[] {
  const gamesById = new Map(
    schedule.games.map((game) => [game.id, game] as const),
  )
  if (gamesById.size !== schedule.games.length) {
    throw new RangeError('A schedule cannot group duplicate game IDs')
  }

  return schedule.gameDays.map((gameDay) => ({
    gameDay,
    games: gameDay.gameIds.map((gameId) => {
      const game = gamesById.get(gameId)
      if (game === undefined) {
        throw new RangeError(
          `Game day ${gameDay.id} references unknown game ${gameId}`,
        )
      }
      if (game.gameDayId !== gameDay.id) {
        throw new RangeError(
          `Game ${game.id} does not reference game day ${gameDay.id}`,
        )
      }
      return game
    }),
  }))
}

/** Fixed English display formatting with no Date, locale, or timezone APIs. */
export function formatLocalDateForDisplay(date: LocalDate): string {
  const parsed = parseLocalDate(date)
  const year = parsed.slice(0, 4)
  const month = Number(parsed.slice(5, 7))
  const day = Number(parsed.slice(8, 10))
  return `${MONTH_NAMES[month - 1]} ${day}, ${year}`
}

/** Counts every stored team matchup, independent of game status. */
export function calculateTeamScheduleTotals(
  schedule: LeagueSnapshotV2LeagueScheduleDto,
  teamId: TeamId,
): TeamScheduleTotals {
  let homeGames = 0
  let awayGames = 0

  for (const game of schedule.games) {
    if (!isTeamInGame(game, teamId)) continue
    if (getTeamLocation(game, teamId) === 'home') {
      homeGames += 1
    } else {
      awayGames += 1
    }
  }

  return {
    totalGames: homeGames + awayGames,
    homeGames,
    awayGames,
  }
}

/** Applies a home/away filter while retaining authoritative game order. */
export function filterTeamScheduleGames(
  schedule: LeagueSnapshotV2LeagueScheduleDto,
  teamId: TeamId,
  filter: TeamScheduleFilter,
): readonly LeagueSnapshotV2ScheduledGameDto[] {
  const teamGames = getTeamScheduleGames(schedule, teamId)
  if (filter === 'all') return teamGames
  return teamGames.filter((game) => getTeamLocation(game, teamId) === filter)
}

/** Identifies whether a matchup contains the selected managed team. */
export function isManagedTeamGame(
  game: LeagueSnapshotV2ScheduledGameDto,
  managedTeamId: TeamId | null,
): boolean {
  return managedTeamId !== null && isTeamInGame(game, managedTeamId)
}

export function formatSeasonPhaseForDisplay(phase: SeasonPhase): string {
  return SEASON_PHASE_LABELS[phase]
}

function isTeamInGame(
  game: LeagueSnapshotV2ScheduledGameDto,
  teamId: TeamId,
): boolean {
  return game.homeTeamId === teamId || game.awayTeamId === teamId
}

function getOpponentTeamId(
  game: LeagueSnapshotV2ScheduledGameDto,
  teamId: TeamId,
): TeamId {
  assertDistinctMatchup(game)
  if (game.homeTeamId === teamId) return game.awayTeamId
  if (game.awayTeamId === teamId) return game.homeTeamId

  throw new RangeError(`Team ${teamId} does not participate in game ${game.id}`)
}

function assertDistinctMatchup(game: LeagueSnapshotV2ScheduledGameDto): void {
  if (game.homeTeamId === game.awayTeamId) {
    throw new RangeError(`Game ${game.id} does not contain distinct teams`)
  }
}

function isUpcomingTeamGame(
  game: LeagueSnapshotV2ScheduledGameDto,
  teamId: TeamId,
  currentDate: LocalDate,
): boolean {
  return (
    isTeamInGame(game, teamId) &&
    (game.status === 'scheduled' || game.status === 'postponed') &&
    game.currentScheduledDate !== null &&
    compareLocalDates(game.currentScheduledDate, currentDate) >= 0
  )
}

function compareKnownScheduledDates(
  left: LeagueSnapshotV2ScheduledGameDto,
  right: LeagueSnapshotV2ScheduledGameDto,
): -1 | 0 | 1 {
  if (
    left.currentScheduledDate === null ||
    right.currentScheduledDate === null
  ) {
    throw new RangeError('An upcoming game must have a current scheduled date')
  }
  return compareLocalDates(left.currentScheduledDate, right.currentScheduledDate)
}
