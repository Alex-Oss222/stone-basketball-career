import { describe, expect, it } from 'vitest'
import { parseGameId, parseTeamId } from '../../src/domain/ids'
import {
  createTeamScheduleUiState,
  parseTeamScheduleSiteFilter,
  reduceTeamScheduleUiState,
} from '../../src/ui/teamScheduleUiState'
import type {
  TeamScheduleUiAction,
  TeamScheduleUiState,
} from '../../src/ui/teamScheduleUiState'
import { createLeagueSnapshotV2Fixture } from '../persistence/leagueSnapshotV2.fixture'

describe('Team Schedule transient UI state initialization', () => {
  it('starts with the managed team when one exists', () => {
    const snapshot = createLeagueSnapshotV2Fixture()

    const state = createTeamScheduleUiState({
      league: snapshot.league,
      managedTeamId: snapshot.managedTeamId,
    })

    expect(state).toEqual({
      inspectedTeamId: snapshot.managedTeamId,
      stage: 'regular_season',
      viewMode: 'calendar',
      siteFilter: 'all',
      visibleMonth: null,
      selectedGameId: null,
    })
    expect(Object.isFrozen(state)).toBe(true)
  })

  it('starts with the first canonical league team without a managed team', () => {
    const snapshot = createLeagueSnapshotV2Fixture(null)

    const state = createTeamScheduleUiState({
      league: snapshot.league,
      managedTeamId: null,
    })

    expect(state.inspectedTeamId).toBe(snapshot.league.teams[0].id)
    expect(state.siteFilter).toBe('all')
    expect(state.selectedGameId).toBeNull()
  })

  it('accepts explicit valid initial presentation preferences', () => {
    const snapshot = createLeagueSnapshotV2Fixture()
    const inspectedTeamId = snapshot.league.teams[3].id
    const selectedGameId = snapshot.leagueSchedule.games[4].id

    const state = createTeamScheduleUiState({
      league: snapshot.league,
      managedTeamId: snapshot.managedTeamId,
      initialInspectedTeamId: inspectedTeamId,
      initialFilter: 'away',
      initialSelectedGameId: selectedGameId,
    })

    expect(state).toEqual({
      inspectedTeamId,
      stage: 'regular_season',
      viewMode: 'calendar',
      siteFilter: 'away',
      visibleMonth: null,
      selectedGameId,
    })
  })

  it('rejects empty leagues and foreign inspected or managed teams', () => {
    const snapshot = createLeagueSnapshotV2Fixture()
    const emptyLeague = {
      ...snapshot.league,
      teams: [],
    }
    const foreignTeamId = parseTeamId('team_foreign_ui_state_test')

    expect(() =>
      createTeamScheduleUiState({
        league: emptyLeague,
        managedTeamId: null,
      }),
    ).toThrow(/at least one league team/)
    expect(() =>
      createTeamScheduleUiState({
        league: snapshot.league,
        managedTeamId: snapshot.managedTeamId,
        initialInspectedTeamId: foreignTeamId,
      }),
    ).toThrow(/does not belong to the league/)
    expect(() =>
      createTeamScheduleUiState({
        league: snapshot.league,
        managedTeamId: foreignTeamId,
      }),
    ).toThrow(/does not belong to the league/)
  })
})

describe('Team Schedule transient UI state reducer', () => {
  it('changes inspected team while resetting filter and selected game', () => {
    const snapshot = createLeagueSnapshotV2Fixture()
    const initial = createTeamScheduleUiState({
      league: snapshot.league,
      managedTeamId: snapshot.managedTeamId,
      initialFilter: 'home',
      initialSelectedGameId: snapshot.leagueSchedule.games[0].id,
    })
    const inspectedTeamId = snapshot.league.teams[5].id

    const next = reduceTeamScheduleUiState(initial, {
      type: 'inspect_team',
      teamId: inspectedTeamId,
    })

    expect(next).toEqual({
      inspectedTeamId,
      stage: 'regular_season',
      viewMode: 'calendar',
      siteFilter: 'all',
      visibleMonth: null,
      selectedGameId: null,
    })
    expect(initial.siteFilter).toBe('home')
    expect(initial.selectedGameId).toBe(snapshot.leagueSchedule.games[0].id)
    expect(Object.isFrozen(next)).toBe(true)
  })

  it('sets All/Home/Away without changing inspected or selected context', () => {
    const snapshot = createLeagueSnapshotV2Fixture()
    const initial = createTeamScheduleUiState({
      league: snapshot.league,
      managedTeamId: snapshot.managedTeamId,
      initialSelectedGameId: snapshot.leagueSchedule.games[0].id,
    })

    for (const filter of ['all', 'home', 'away'] as const) {
      const next = reduceTeamScheduleUiState(initial, {
        type: 'set_site_filter',
        filter,
      })
      expect(next).toEqual({ ...initial, siteFilter: filter })
      expect(Object.isFrozen(next)).toBe(true)
    }
  })

  it('opens and closes one canonical game without changing other UI state', () => {
    const snapshot = createLeagueSnapshotV2Fixture()
    const initial = createTeamScheduleUiState({
      league: snapshot.league,
      managedTeamId: snapshot.managedTeamId,
      initialFilter: 'away',
    })
    const gameId = snapshot.leagueSchedule.games[7].id

    const opened = reduceTeamScheduleUiState(initial, {
      type: 'open_game',
      gameId,
    })
    const closed = reduceTeamScheduleUiState(opened, { type: 'close_game' })

    expect(opened).toEqual({ ...initial, selectedGameId: gameId })
    expect(closed).toEqual({ ...initial, selectedGameId: null })
    expect(Object.isFrozen(opened)).toBe(true)
    expect(Object.isFrozen(closed)).toBe(true)
  })

  it('rejects unsupported filter values, malformed game IDs, and unknown actions', () => {
    const snapshot = createLeagueSnapshotV2Fixture()
    const initial = createTeamScheduleUiState({
      league: snapshot.league,
      managedTeamId: snapshot.managedTeamId,
    })

    expect(() => parseTeamScheduleSiteFilter('status')).toThrow(/unsupported/)
    expect(() =>
      reduceTeamScheduleUiState(initial, {
        type: 'set_site_filter',
        filter: 'status',
      } as never),
    ).toThrow(/unsupported/)
    expect(() =>
      reduceTeamScheduleUiState(initial, {
        type: 'open_game',
        gameId: 'Not a game ID',
      } as never),
    ).toThrow()
    expect(() =>
      reduceTeamScheduleUiState(initial, {
        type: 'unsupported',
      } as never),
    ).toThrow(/Unsupported Team Schedule UI action/)
  })

  it('never mutates or persists transient inspected, filter, and selected state', () => {
    const snapshot = createLeagueSnapshotV2Fixture()
    const serializedBefore = JSON.stringify(snapshot)
    const revisionBefore = snapshot.revision
    const managedTeamBefore = snapshot.managedTeamId
    let state = createTeamScheduleUiState({
      league: snapshot.league,
      managedTeamId: snapshot.managedTeamId,
    })

    state = reduceTeamScheduleUiState(state, {
      type: 'inspect_team',
      teamId: snapshot.league.teams[2].id,
    })
    state = reduceTeamScheduleUiState(state, {
      type: 'set_site_filter',
      filter: 'home',
    })
    state = reduceTeamScheduleUiState(state, {
      type: 'open_game',
      gameId: snapshot.leagueSchedule.games[3].id,
    })

    expect(state.inspectedTeamId).not.toBe(managedTeamBefore)
    expect(snapshot.managedTeamId).toBe(managedTeamBefore)
    expect(snapshot.revision).toBe(revisionBefore)
    expect(JSON.stringify(snapshot)).toBe(serializedBefore)
    expect(Object.hasOwn(snapshot, 'inspectedTeamId')).toBe(false)
    expect(Object.hasOwn(snapshot, 'siteFilter')).toBe(false)
    expect(Object.hasOwn(snapshot, 'selectedGameId')).toBe(false)
  })
})

describe('Team Schedule UI state closed contracts', () => {
  it.each(['all', 'home', 'away'] as const)(
    'parses supported site filter %s',
    (filter) => {
      expect(parseTeamScheduleSiteFilter(filter)).toBe(filter)
    },
  )

  it('retains canonical branded identity types at runtime', () => {
    const gameId = parseGameId('game_ui_state_runtime_identity')
    const teamId = parseTeamId('team_ui_state_runtime_identity')
    const state: TeamScheduleUiState = Object.freeze({
      inspectedTeamId: teamId,
      stage: 'regular_season',
      viewMode: 'calendar',
      siteFilter: 'all',
      visibleMonth: null,
      selectedGameId: gameId,
    })
    const action: TeamScheduleUiAction = {
      type: 'close_game',
    }

    expect(reduceTeamScheduleUiState(state, action).selectedGameId).toBeNull()
  })
})
