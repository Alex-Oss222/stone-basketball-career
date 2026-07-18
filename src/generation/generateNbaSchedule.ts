import { parseGameDayId, parseScheduleId } from '../domain/ids'
import type { GameId, LeagueId, SeasonId, TeamId } from '../domain/ids'
import { addDays } from '../domain/localDate'
import type { LocalDate } from '../domain/localDate'
import {
  createOpponentRequirement,
  getCanonicalTeamPair,
  getTeamPairKey,
} from '../domain/schedule'
import type {
  GameDay,
  LeagueSchedule,
  OpponentRequirement,
  ScheduledGame,
  ScheduleRuleSet,
} from '../domain/schedule'
import {
  deriveSeed,
  fingerprintDerivedSeed,
  normalizeSeed,
} from '../random/seed'
import { buildBalancedMeetingMatrix } from './scheduleMatrix'
import { placeMeetingsAcrossDates } from './scheduleDatePlacement'
import {
  SCHEDULE_GENERATION_VERSION,
  deriveStableScheduledGameId,
} from './generateSchedule'
import type { ScheduleTeamReference } from './generateSchedule'

const ID_FINGERPRINT_LENGTH = 24

export interface GenerateNbaScheduleInput {
  readonly leagueId: LeagueId
  readonly seasonId: SeasonId
  readonly teams: readonly ScheduleTeamReference[]
  readonly scheduleSeed: string
  readonly ruleSet: ScheduleRuleSet
  readonly regularSeasonStartDate: LocalDate
  /** Number of days in the scheduling window (e.g. 174 for a real NBA season). */
  readonly windowDays: number
}

interface WorkingMeeting {
  readonly homeTeamId: TeamId
  readonly awayTeamId: TeamId
  readonly dateIndex: number
  readonly meetingNumber: number
}

/**
 * Generates a balanced NBA-shaped regular season: every team plays
 * `ruleSet.gamesPerTeam` games (41 home / 41 away for 82), spread across the day
 * window so no team plays twice in a day. It composes the pure meeting-matrix
 * and date-placement engines and reuses the shared stable-identity derivation,
 * so the result is fully deterministic. Opponent requirements are derived from
 * the generated games and therefore always agree with them.
 */
export function generateNbaRegularSeasonSchedule(
  input: GenerateNbaScheduleInput,
): LeagueSchedule {
  const teamCount = input.teams.length
  const sortedTeamIds = input.teams
    .map(({ id }) => id)
    .sort((left, right) => (left < right ? -1 : left > right ? 1 : 0))
  const scheduleSeed = normalizeSeed(input.scheduleSeed)

  const matrix = buildBalancedMeetingMatrix({
    teamCount,
    gamesPerTeam: input.ruleSet.gamesPerTeam,
  })
  const placements = placeMeetingsAcrossDates({
    meetings: matrix,
    dateCount: input.windowDays,
  })

  // Assign chronological meeting numbers per unordered pair (placements are
  // already sorted by date, so earlier games get earlier meeting numbers).
  const meetingCounts = new Map<string, number>()
  const working: WorkingMeeting[] = placements.map((placement) => {
    const meeting = matrix[placement.meetingIndex]
    const homeTeamId = sortedTeamIds[meeting.homeIndex]
    const awayTeamId = sortedTeamIds[meeting.awayIndex]
    const pair = getCanonicalTeamPair(homeTeamId, awayTeamId)
    const pairKey = getTeamPairKey(pair.firstTeamId, pair.secondTeamId)
    const meetingNumber = (meetingCounts.get(pairKey) ?? 0) + 1
    meetingCounts.set(pairKey, meetingNumber)
    return {
      homeTeamId,
      awayTeamId,
      dateIndex: placement.dateIndex,
      meetingNumber,
    }
  })

  const seedNamespace = deriveSeed(
    scheduleSeed,
    `schedule/v${SCHEDULE_GENERATION_VERSION}/${input.seasonId}/${input.ruleSet.id}/rules_v${input.ruleSet.version}/nba`,
  )

  // Build the game-days by placed date so each distinct used day is a game-day.
  const usedDateIndexes = [
    ...new Set(working.map((meeting) => meeting.dateIndex)),
  ].sort((left, right) => left - right)
  const gameDayIdByDate = new Map<number, ReturnType<typeof parseGameDayId>>()
  const gameIdsByDate = new Map<number, GameId[]>()

  usedDateIndexes.forEach((dateIndex) => {
    gameDayIdByDate.set(
      dateIndex,
      parseGameDayId(
        `game_day_${fingerprintDerivedSeed(
          deriveSeed(seedNamespace, `nba_game_day/date_${dateIndex}`),
          ID_FINGERPRINT_LENGTH,
        )}`,
      ),
    )
  })

  const games: ScheduledGame[] = working.map((meeting) => {
    const gameDayId = gameDayIdByDate.get(meeting.dateIndex)
    if (gameDayId === undefined) {
      throw new Error('Internal: missing game-day for a placed meeting')
    }
    const scheduledDate = addDays(input.regularSeasonStartDate, meeting.dateIndex)
    const id = deriveStableScheduledGameId({
      seasonId: input.seasonId,
      ruleSet: input.ruleSet,
      scheduleSeed,
      firstTeamId: meeting.homeTeamId,
      secondTeamId: meeting.awayTeamId,
      cycleSlot: meeting.meetingNumber - 1,
    })
    const dayGameIds = gameIdsByDate.get(meeting.dateIndex) ?? []
    dayGameIds.push(id)
    gameIdsByDate.set(meeting.dateIndex, dayGameIds)

    return Object.freeze({
      id,
      seasonId: input.seasonId,
      gameDayId,
      stage: input.ruleSet.stage,
      homeTeamId: meeting.homeTeamId,
      awayTeamId: meeting.awayTeamId,
      originalScheduledDate: scheduledDate,
      currentScheduledDate: scheduledDate,
      status: 'scheduled' as const,
      meetingNumber: meeting.meetingNumber,
    })
  })

  const gameDays: GameDay[] = usedDateIndexes.map((dateIndex, position) => {
    const gameDayId = gameDayIdByDate.get(dateIndex)
    if (gameDayId === undefined) {
      throw new Error('Internal: missing game-day identity')
    }
    return Object.freeze({
      id: gameDayId,
      seasonId: input.seasonId,
      sequenceNumber: position + 1,
      scheduledDate: addDays(input.regularSeasonStartDate, dateIndex),
      gameIds: Object.freeze([...(gameIdsByDate.get(dateIndex) ?? [])]),
    })
  })

  const opponentRequirements = buildOpponentRequirementsFromGames(
    games,
    input.ruleSet,
  )

  const scheduleId = parseScheduleId(
    `schedule_${fingerprintDerivedSeed(
      deriveSeed(seedNamespace, 'nba_schedule_identity'),
      ID_FINGERPRINT_LENGTH,
    )}`,
  )

  return Object.freeze({
    id: scheduleId,
    leagueId: input.leagueId,
    seasonId: input.seasonId,
    ruleSetId: input.ruleSet.id,
    generationVersion: SCHEDULE_GENERATION_VERSION,
    scheduleSeed,
    calendarDaySpacing: 1,
    publicationStatus: 'draft',
    opponentRequirements,
    gameDays: Object.freeze(gameDays),
    games: Object.freeze(games),
  })
}

function buildOpponentRequirementsFromGames(
  games: readonly ScheduledGame[],
  ruleSet: ScheduleRuleSet,
): readonly OpponentRequirement[] {
  interface Tally {
    readonly firstTeamId: TeamId
    readonly secondTeamId: TeamId
    total: number
    homeForFirst: number
    homeForSecond: number
  }
  const tallies = new Map<string, Tally>()

  for (const game of games) {
    const pair = getCanonicalTeamPair(game.homeTeamId, game.awayTeamId)
    const key = getTeamPairKey(pair.firstTeamId, pair.secondTeamId)
    let tally = tallies.get(key)
    if (tally === undefined) {
      tally = {
        firstTeamId: pair.firstTeamId,
        secondTeamId: pair.secondTeamId,
        total: 0,
        homeForFirst: 0,
        homeForSecond: 0,
      }
      tallies.set(key, tally)
    }
    tally.total += 1
    if (game.homeTeamId === pair.firstTeamId) tally.homeForFirst += 1
    else tally.homeForSecond += 1
  }

  return Object.freeze(
    [...tallies.values()]
      .map((tally) =>
        createOpponentRequirement(
          tally.firstTeamId,
          tally.secondTeamId,
          tally.total,
          tally.homeForFirst,
          tally.homeForSecond,
          ruleSet.stage,
        ),
      )
      .sort((left, right) =>
        getTeamPairKey(left.firstTeamId, left.secondTeamId) <
        getTeamPairKey(right.firstTeamId, right.secondTeamId)
          ? -1
          : 1,
      ),
  )
}
