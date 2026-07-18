import type { TeamId } from '../domain/ids'
import { compareLocalDates, parseLocalDate } from '../domain/localDate'
import type { LocalDate } from '../domain/localDate'
import type { SeasonPhase } from '../domain/season'
import type {
  LeagueSnapshotLeagueDto,
  LeagueSnapshotLeagueScheduleDto,
  LeagueSnapshotScheduledGameDto,
  LeagueSnapshotTeamDto,
} from '../persistence/leagueSnapshot'

export type TeamScheduleLocation = 'home' | 'away'

const SEASON_PHASE_LABELS = {
  offseason: 'Offseason',
  training_camp: 'Training camp',
  preseason: 'Preseason',
  regular_season: 'Regular season',
  postseason: 'Postseason',
  complete: 'Complete',
} as const satisfies Readonly<Record<SeasonPhase, string>>

/** Resolves the opposing stored team without creating substitute display data. */
export function resolveOpponent(
  league: LeagueSnapshotLeagueDto,
  game: LeagueSnapshotScheduledGameDto,
  teamId: TeamId,
): LeagueSnapshotTeamDto {
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
  game: LeagueSnapshotScheduledGameDto,
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
  schedule: LeagueSnapshotLeagueScheduleDto,
  teamId: TeamId,
  currentDate: LocalDate,
): LeagueSnapshotScheduledGameDto | null {
  const parsedCurrentDate = parseLocalDate(currentDate)
  let nextGame: LeagueSnapshotScheduledGameDto | null = null

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
  schedule: LeagueSnapshotLeagueScheduleDto,
  teamId: TeamId,
  currentDate: LocalDate,
): readonly LeagueSnapshotScheduledGameDto[] {
  const parsedCurrentDate = parseLocalDate(currentDate)
  return schedule.games.filter((game) =>
    isUpcomingTeamGame(game, teamId, parsedCurrentDate),
  )
}

export function formatSeasonPhaseForDisplay(phase: SeasonPhase): string {
  return SEASON_PHASE_LABELS[phase]
}

function getOpponentTeamId(
  game: LeagueSnapshotScheduledGameDto,
  teamId: TeamId,
): TeamId {
  assertDistinctMatchup(game)
  if (game.homeTeamId === teamId) return game.awayTeamId
  if (game.awayTeamId === teamId) return game.homeTeamId

  throw new RangeError(`Team ${teamId} does not participate in game ${game.id}`)
}

function assertDistinctMatchup(game: LeagueSnapshotScheduledGameDto): void {
  if (game.homeTeamId === game.awayTeamId) {
    throw new RangeError(`Game ${game.id} does not contain distinct teams`)
  }
}

function isUpcomingTeamGame(
  game: LeagueSnapshotScheduledGameDto,
  teamId: TeamId,
  currentDate: LocalDate,
): boolean {
  return (
    (game.homeTeamId === teamId || game.awayTeamId === teamId) &&
    (game.status === 'scheduled' || game.status === 'postponed') &&
    game.currentScheduledDate !== null &&
    compareLocalDates(game.currentScheduledDate, currentDate) >= 0
  )
}

function compareKnownScheduledDates(
  left: LeagueSnapshotScheduledGameDto,
  right: LeagueSnapshotScheduledGameDto,
): -1 | 0 | 1 {
  if (
    left.currentScheduledDate === null ||
    right.currentScheduledDate === null
  ) {
    throw new RangeError('An upcoming game must have a current scheduled date')
  }
  return compareLocalDates(left.currentScheduledDate, right.currentScheduledDate)
}
