import { describe, expect, expectTypeOf, it } from 'vitest'
import type { Position } from '../../src/domain/league'
import { generateLeague } from '../../src/generation/generateLeague'
import {
  DASHBOARD_HEADER_MODEL,
  LEAGUE_SETUP_PROGRESS_LABEL,
  NO_SEASON_STARTED_LABEL,
  createSavedLeagueDashboardSummary,
  deriveDashboardAction,
  filterLeaguePlayers,
} from '../../src/app/dashboardViewModel'
import type {
  DashboardAction,
  PlayerPositionFilter,
} from '../../src/app/dashboardViewModel'
import { formatPlayerName, formatTeamName } from '../../src/ui/leagueViewModel'

const league = generateLeague('dashboard-view-model-fixture')

describe('dashboard header and action models', () => {
  it('uses only the approved setup progression copy', () => {
    expect(LEAGUE_SETUP_PROGRESS_LABEL).toBe('League setup')
    expect(NO_SEASON_STARTED_LABEL).toBe('No season started')
    expect(DASHBOARD_HEADER_MODEL).toEqual({
      progressLabel: 'League setup',
      seasonStatus: 'No season started',
    })
  })

  it.each<
    readonly [
      string,
      Parameters<typeof deriveDashboardAction>[0],
      DashboardAction,
    ]
  >([
    [
      'no league',
      null,
      { label: 'Create League', target: 'create-league' },
    ],
    [
      'league without a managed team',
      { league, managedTeamId: null, hasSchedule: true },
      { label: 'Choose Team', target: 'choose-team' },
    ],
    [
      'managed league with a schedule',
      { league, managedTeamId: league.teams[0].id, hasSchedule: true },
      { label: 'View Schedule', target: 'view-schedule' },
    ],
  ])('derives the authoritative action for %s', (_name, state, expected) => {
    expect(deriveDashboardAction(state)).toEqual(expected)
  })

  it('does not imply a schedule action when a managed league has no schedule', () => {
    expect(() =>
      deriveDashboardAction({
        league,
        managedTeamId: league.teams[0].id,
        hasSchedule: false,
      }),
    ).toThrow('A managed league must have a schedule')
  })
})

describe('saved league dashboard summary', () => {
  it('reports only real saved league and managed-roster facts', () => {
    const team = league.teams[3]
    const roster = league.players.filter((player) => player.teamId === team.id)
    const summary = createSavedLeagueDashboardSummary({
      league,
      managedTeamId: team.id,
    })

    expect(Object.keys(summary)).toEqual([
      'leagueId',
      'teamCount',
      'managedTeam',
    ])
    expect(summary.leagueId).toBe(league.id)
    expect(summary.teamCount).toBe(league.teams.length)
    expect(summary.managedTeam).toEqual({
      teamId: team.id,
      teamName: formatTeamName(team),
      abbreviation: team.abbreviation,
      rosterSize: roster.length,
      averageAge:
        roster.reduce((total, player) => total + player.age, 0) / roster.length,
      positionBreakdown: {
        PG: countPosition(roster, 'PG'),
        SG: countPosition(roster, 'SG'),
        SF: countPosition(roster, 'SF'),
        PF: countPosition(roster, 'PF'),
        C: countPosition(roster, 'C'),
      },
    })
    expect(Object.keys(summary.managedTeam ?? {})).not.toEqual(
      expect.arrayContaining(['record', 'date', 'wins', 'losses', 'statistics']),
    )
  })

  it('does not invent managed-team facts before team selection', () => {
    expect(
      createSavedLeagueDashboardSummary({ league, managedTeamId: null }),
    ).toEqual({
      leagueId: league.id,
      teamCount: league.teams.length,
      managedTeam: null,
    })
  })
})

describe('league-wide player filtering', () => {
  it('returns every player in persisted order for blank query and ALL positions', () => {
    const results = filterLeaguePlayers(league, '   ', 'ALL')

    expect(results.map((result) => result.player.id)).toEqual(
      league.players.map((player) => player.id),
    )
    expect(results).toHaveLength(league.players.length)
  })

  it('trims and matches names case-insensitively', () => {
    const player = league.players[27]
    const query = `  ${formatPlayerName(player).toUpperCase()}  `
    const results = filterLeaguePlayers(league, query, 'ALL')

    expect(results.map((result) => result.player.id)).toContain(player.id)
    expect(
      results.every(
        (result) =>
          result.playerName.toLowerCase() ===
          formatPlayerName(player).toLowerCase(),
      ),
    ).toBe(true)
  })

  it('combines primary-position and name filters without reordering results', () => {
    const matchingPlayers = league.players.filter(
      (player) =>
        player.primaryPosition === 'PG' &&
        formatPlayerName(player).toLowerCase().includes('a'),
    )
    const results = filterLeaguePlayers(league, ' A ', 'PG')

    expect(results.map((result) => result.player.id)).toEqual(
      matchingPlayers.map((player) => player.id),
    )
    expect(results.every((result) => result.player.primaryPosition === 'PG')).toBe(
      true,
    )
  })

  it('resolves each result to its real team and display identity', () => {
    const results = filterLeaguePlayers(league, '', 'C')

    for (const result of results) {
      const team = league.teams.find(
        (candidate) => candidate.id === result.player.teamId,
      )
      expect(team).toBeDefined()
      expect(result.team).toBe(team)
      expect(result.teamName).toBe(formatTeamName(result.team))
      expect(result.teamAbbreviation).toBe(result.team.abbreviation)
    }
  })

  it('defines the filter as ALL or one canonical position', () => {
    expectTypeOf<PlayerPositionFilter>().toEqualTypeOf<Position | 'ALL'>()
  })
})

function countPosition(
  players: typeof league.players,
  position: Position,
): number {
  return players.filter((player) => player.primaryPosition === position).length
}
