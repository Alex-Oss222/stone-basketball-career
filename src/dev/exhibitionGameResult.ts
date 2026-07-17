import type { GameResult, PlayerBoxScoreLine, DnpReason } from '../domain/gameResult'
import type { Position, Team } from '../domain/league'
import {
  parseGameId,
  parsePlayerId,
  parseSeasonId,
  parseTeamId,
} from '../domain/ids'
import type { PlayerId, TeamId } from '../domain/ids'

/**
 * DEV/TEST ONLY — the hand-written exhibition result the §6 screens are
 * designed against. It must never reach a real game: real games have no result
 * until the simulation exists, and the app keeps showing that honest absence.
 *
 * Every number reconciles (team points = player points = period points, 265
 * player-minutes per team for the one-overtime game, plus/minus sums to five
 * times the margin). tests/domain/gameResult.test.ts proves it against
 * assertValidGameResult, so screen design only ever sees producible data.
 */

export interface ExhibitionPlayerInfo {
  readonly name: string
  readonly position: Position
  readonly jerseyNumber: number
}

const HOME_TEAM_ID = parseTeamId('fixture_team_emberlyn')
const AWAY_TEAM_ID = parseTeamId('fixture_team_duskmere')

export const EXHIBITION_HOME_TEAM: Team = {
  id: HOME_TEAM_ID,
  city: 'Emberlyn',
  nickname: 'Forgekeepers',
  abbreviation: 'EFK',
  colors: { primary: '#7a2e2e', secondary: '#e36f3d', accent: '#f3d6a3' },
  mark: { kind: 'initials', text: 'EF' },
}

export const EXHIBITION_AWAY_TEAM: Team = {
  id: AWAY_TEAM_ID,
  city: 'Duskmere',
  nickname: 'Nightjars',
  abbreviation: 'DMN',
  colors: { primary: '#342a5e', secondary: '#8fb8de', accent: '#e8e3f2' },
  mark: { kind: 'initials', text: 'DN' },
}

interface LineSpec {
  readonly id: string
  readonly name: string
  readonly position: Position
  readonly jersey: number
  readonly started: boolean
  readonly minutes: number
  readonly fg: readonly [number, number]
  readonly tp: readonly [number, number]
  readonly ft: readonly [number, number]
  readonly oreb: number
  readonly dreb: number
  readonly ast: number
  readonly stl: number
  readonly blk: number
  readonly to: number
  readonly pf: number
  readonly plusMinus: number
}

interface DnpSpec {
  readonly id: string
  readonly name: string
  readonly position: Position
  readonly jersey: number
  readonly reason: DnpReason
}

function playedLine(teamId: TeamId, spec: LineSpec): PlayerBoxScoreLine {
  const twoPointMakes = spec.fg[0] - spec.tp[0]
  return {
    playerId: parsePlayerId(spec.id),
    teamId,
    started: spec.started,
    secondsPlayed: spec.minutes * 60,
    fieldGoalsMade: spec.fg[0],
    fieldGoalsAttempted: spec.fg[1],
    threePointersMade: spec.tp[0],
    threePointersAttempted: spec.tp[1],
    freeThrowsMade: spec.ft[0],
    freeThrowsAttempted: spec.ft[1],
    offensiveRebounds: spec.oreb,
    defensiveRebounds: spec.dreb,
    assists: spec.ast,
    steals: spec.stl,
    blocks: spec.blk,
    turnovers: spec.to,
    personalFouls: spec.pf,
    plusMinus: spec.plusMinus,
    points: twoPointMakes * 2 + spec.tp[0] * 3 + spec.ft[0],
    dnpReason: null,
  }
}

function dnpLine(teamId: TeamId, spec: DnpSpec): PlayerBoxScoreLine {
  return {
    playerId: parsePlayerId(spec.id),
    teamId,
    started: false,
    secondsPlayed: 0,
    fieldGoalsMade: 0,
    fieldGoalsAttempted: 0,
    threePointersMade: 0,
    threePointersAttempted: 0,
    freeThrowsMade: 0,
    freeThrowsAttempted: 0,
    offensiveRebounds: 0,
    defensiveRebounds: 0,
    assists: 0,
    steals: 0,
    blocks: 0,
    turnovers: 0,
    personalFouls: 0,
    plusMinus: 0,
    points: 0,
    dnpReason: spec.reason,
  }
}

const HOME_PLAYED: readonly LineSpec[] = [
  { id: 'fixture_efk_01', name: 'Dorian Vale', position: 'PG', jersey: 4, started: true, minutes: 38, fg: [9, 19], tp: [3, 7], ft: [6, 6], oreb: 1, dreb: 4, ast: 8, stl: 2, blk: 0, to: 3, pf: 2, plusMinus: 9 },
  { id: 'fixture_efk_02', name: 'Marek Ashwood', position: 'SG', jersey: 12, started: true, minutes: 36, fg: [8, 15], tp: [4, 9], ft: [2, 2], oreb: 0, dreb: 3, ast: 4, stl: 1, blk: 0, to: 2, pf: 3, plusMinus: 7 },
  { id: 'fixture_efk_03', name: 'Tobin Rooke', position: 'SF', jersey: 23, started: true, minutes: 34, fg: [7, 13], tp: [2, 4], ft: [5, 6], oreb: 2, dreb: 5, ast: 3, stl: 1, blk: 1, to: 1, pf: 2, plusMinus: 8 },
  { id: 'fixture_efk_04', name: 'Caspian Ferro', position: 'PF', jersey: 31, started: true, minutes: 30, fg: [6, 10], tp: [0, 1], ft: [2, 4], oreb: 3, dreb: 6, ast: 2, stl: 0, blk: 1, to: 2, pf: 4, plusMinus: 4 },
  { id: 'fixture_efk_05', name: 'Aldous Wren', position: 'C', jersey: 55, started: true, minutes: 32, fg: [6, 9], tp: [0, 0], ft: [3, 5], oreb: 4, dreb: 7, ast: 1, stl: 0, blk: 3, to: 2, pf: 3, plusMinus: 5 },
  { id: 'fixture_efk_06', name: 'Silas Marlow', position: 'SG', jersey: 8, started: false, minutes: 25, fg: [4, 9], tp: [1, 4], ft: [2, 2], oreb: 1, dreb: 3, ast: 3, stl: 1, blk: 0, to: 1, pf: 2, plusMinus: 1 },
  { id: 'fixture_efk_07', name: 'Eamon Frost', position: 'PG', jersey: 3, started: false, minutes: 22, fg: [2, 6], tp: [1, 3], ft: [0, 0], oreb: 0, dreb: 2, ast: 2, stl: 0, blk: 0, to: 1, pf: 1, plusMinus: -2 },
  { id: 'fixture_efk_08', name: 'Rowan Ketch', position: 'PF', jersey: 41, started: false, minutes: 20, fg: [1, 4], tp: [0, 2], ft: [1, 2], oreb: 1, dreb: 2, ast: 1, stl: 1, blk: 1, to: 0, pf: 2, plusMinus: 0 },
  { id: 'fixture_efk_09', name: 'Jorah Lindell', position: 'SF', jersey: 19, started: false, minutes: 16, fg: [0, 3], tp: [0, 1], ft: [0, 0], oreb: 0, dreb: 2, ast: 1, stl: 0, blk: 0, to: 1, pf: 1, plusMinus: -1 },
  { id: 'fixture_efk_10', name: 'Petyr Stroud', position: 'C', jersey: 50, started: false, minutes: 12, fg: [0, 1], tp: [0, 0], ft: [0, 0], oreb: 0, dreb: 1, ast: 0, stl: 0, blk: 0, to: 0, pf: 1, plusMinus: -1 },
]

const HOME_DNP: readonly DnpSpec[] = [
  { id: 'fixture_efk_11', name: 'Colm Bracken', position: 'SG', jersey: 27, reason: 'coachs_decision' },
  { id: 'fixture_efk_12', name: 'Idris Fenwick', position: 'PF', jersey: 44, reason: 'inactive' },
]

const AWAY_PLAYED: readonly LineSpec[] = [
  { id: 'fixture_dmn_01', name: 'Lucan Merrow', position: 'PG', jersey: 7, started: true, minutes: 39, fg: [10, 21], tp: [2, 6], ft: [4, 5], oreb: 0, dreb: 5, ast: 9, stl: 1, blk: 0, to: 4, pf: 2, plusMinus: -8 },
  { id: 'fixture_dmn_02', name: 'Basil Thorne', position: 'SG', jersey: 11, started: true, minutes: 35, fg: [7, 16], tp: [3, 8], ft: [3, 3], oreb: 1, dreb: 2, ast: 3, stl: 2, blk: 0, to: 2, pf: 3, plusMinus: -6 },
  { id: 'fixture_dmn_03', name: 'Corin Vesper', position: 'SF', jersey: 21, started: true, minutes: 36, fg: [8, 14], tp: [1, 3], ft: [4, 4], oreb: 2, dreb: 6, ast: 4, stl: 1, blk: 1, to: 3, pf: 4, plusMinus: -7 },
  { id: 'fixture_dmn_04', name: 'Hadrian Moss', position: 'PF', jersey: 33, started: true, minutes: 31, fg: [5, 11], tp: [1, 2], ft: [0, 0], oreb: 2, dreb: 5, ast: 2, stl: 0, blk: 2, to: 1, pf: 3, plusMinus: -3 },
  { id: 'fixture_dmn_05', name: 'Osric Dunmore', position: 'C', jersey: 40, started: true, minutes: 30, fg: [5, 8], tp: [0, 0], ft: [4, 6], oreb: 3, dreb: 8, ast: 1, stl: 0, blk: 2, to: 2, pf: 5, plusMinus: -4 },
  { id: 'fixture_dmn_06', name: 'Alaric Penn', position: 'SF', jersey: 15, started: false, minutes: 26, fg: [3, 8], tp: [2, 5], ft: [2, 2], oreb: 0, dreb: 3, ast: 2, stl: 1, blk: 0, to: 1, pf: 2, plusMinus: -1 },
  { id: 'fixture_dmn_07', name: 'Cormac Slate', position: 'PG', jersey: 2, started: false, minutes: 24, fg: [2, 7], tp: [1, 4], ft: [1, 2], oreb: 1, dreb: 2, ast: 3, stl: 0, blk: 0, to: 2, pf: 2, plusMinus: 1 },
  { id: 'fixture_dmn_08', name: 'Evander Holt', position: 'C', jersey: 52, started: false, minutes: 19, fg: [1, 5], tp: [0, 2], ft: [2, 2], oreb: 1, dreb: 3, ast: 1, stl: 1, blk: 1, to: 1, pf: 3, plusMinus: -1 },
  { id: 'fixture_dmn_09', name: 'Gideon Marsh', position: 'SG', jersey: 9, started: false, minutes: 14, fg: [0, 2], tp: [0, 1], ft: [0, 0], oreb: 0, dreb: 1, ast: 1, stl: 0, blk: 0, to: 0, pf: 1, plusMinus: 0 },
  { id: 'fixture_dmn_10', name: 'Lysander Cole', position: 'PF', jersey: 34, started: false, minutes: 11, fg: [0, 2], tp: [0, 0], ft: [0, 0], oreb: 1, dreb: 1, ast: 0, stl: 0, blk: 0, to: 1, pf: 1, plusMinus: -1 },
]

const AWAY_DNP: readonly DnpSpec[] = [
  { id: 'fixture_dmn_11', name: 'Orin Blackwell', position: 'SF', jersey: 18, reason: 'injury' },
  { id: 'fixture_dmn_12', name: 'Percival Yates', position: 'PG', jersey: 6, reason: 'coachs_decision' },
]

export const EXHIBITION_GAME_RESULT: GameResult = {
  gameId: parseGameId('fixture_exhibition_final_ot'),
  seasonId: parseSeasonId('fixture_season_exhibition'),
  homeTeamId: HOME_TEAM_ID,
  awayTeamId: AWAY_TEAM_ID,
  overtimePeriods: 1,
  home: {
    teamId: HOME_TEAM_ID,
    periodPoints: [28, 29, 32, 23, 6],
    totalPoints: 118,
  },
  away: {
    teamId: AWAY_TEAM_ID,
    periodPoints: [25, 31, 26, 30, 0],
    totalPoints: 112,
  },
  winnerTeamId: HOME_TEAM_ID,
  playerLines: [
    ...HOME_PLAYED.map((spec) => playedLine(HOME_TEAM_ID, spec)),
    ...HOME_DNP.map((spec) => dnpLine(HOME_TEAM_ID, spec)),
    ...AWAY_PLAYED.map((spec) => playedLine(AWAY_TEAM_ID, spec)),
    ...AWAY_DNP.map((spec) => dnpLine(AWAY_TEAM_ID, spec)),
  ],
}

function collectPlayerInfo(): ReadonlyMap<PlayerId, ExhibitionPlayerInfo> {
  const entries = new Map<PlayerId, ExhibitionPlayerInfo>()
  for (const spec of [...HOME_PLAYED, ...AWAY_PLAYED]) {
    entries.set(parsePlayerId(spec.id), {
      name: spec.name,
      position: spec.position,
      jerseyNumber: spec.jersey,
    })
  }
  for (const spec of [...HOME_DNP, ...AWAY_DNP]) {
    entries.set(parsePlayerId(spec.id), {
      name: spec.name,
      position: spec.position,
      jerseyNumber: spec.jersey,
    })
  }
  return entries
}

export const EXHIBITION_PLAYER_INFO: ReadonlyMap<PlayerId, ExhibitionPlayerInfo> =
  collectPlayerInfo()
