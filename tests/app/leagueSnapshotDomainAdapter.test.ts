import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import {
  adaptLeagueSnapshotV2ToDomain,
  createLeaguePresentationBundle,
} from '../../src/app/leagueSnapshotDomainAdapter'
import { parseTeamId } from '../../src/domain/ids'
import { createLeagueSnapshotV2Fixture } from '../persistence/leagueSnapshotV2.fixture'

describe('LeagueSnapshotV2 domain adapter', () => {
  it('hydrates one detached, validated live-domain projection', () => {
    const snapshot = createLeagueSnapshotV2Fixture()
    const before = JSON.stringify(snapshot)

    const domain = adaptLeagueSnapshotV2ToDomain(snapshot)

    expect(domain.league.id).toBe(snapshot.league.id)
    expect(domain.season.id).toBe(snapshot.season.id)
    expect(domain.seasonCalendar.id).toBe(snapshot.seasonCalendar.id)
    expect(domain.schedule.id).toBe(snapshot.leagueSchedule.id)
    expect(domain.managedTeamId).toBe(snapshot.managedTeamId)
    expect(domain.league.teams).toHaveLength(8)
    expect(domain.league.players).toHaveLength(96)
    expect(domain.schedule.gameDays).toHaveLength(28)
    expect(domain.schedule.games).toHaveLength(112)
    expect(domain.seasonCalendar.events).toHaveLength(
      snapshot.seasonCalendar.events.length,
    )

    expect(domain.league).not.toBe(snapshot.league)
    expect(domain.league.teams).not.toBe(snapshot.league.teams)
    expect(domain.schedule).not.toBe(snapshot.leagueSchedule)
    expect(domain.schedule.games).not.toBe(snapshot.leagueSchedule.games)
    expect(domain.seasonCalendar).not.toBe(snapshot.seasonCalendar)
    expect(JSON.stringify(snapshot)).toBe(before)
  })

  it('normalizes nullable DTO actual dates to the optional domain contract', () => {
    const snapshot = createLeagueSnapshotV2Fixture()
    const sourceGame = snapshot.leagueSchedule.games[0]
    expect(sourceGame.actualDate).toBeNull()

    const domain = adaptLeagueSnapshotV2ToDomain(snapshot)
    const game = domain.schedule.games.find(
      (candidate) => candidate.id === sourceGame.id,
    )

    expect(game).toBeDefined()
    expect(game?.actualDate).toBeUndefined()
    expect(Object.hasOwn(game ?? {}, 'actualDate')).toBe(false)
    expect(sourceGame.actualDate).toBeNull()
  })

  it('creates exactly one normalized entry per stored game and calendar event', () => {
    const snapshot = createLeagueSnapshotV2Fixture()

    const bundle = createLeaguePresentationBundle(snapshot)
    const expectedCount =
      snapshot.leagueSchedule.games.length +
      snapshot.seasonCalendar.events.length
    const gameSourceIds = new Set(
      bundle.calendarEntries
        .filter((entry) => entry.kind === 'game')
        .map((entry) => entry.sourceId),
    )
    const eventSourceIds = new Set(
      bundle.calendarEntries
        .filter((entry) => entry.kind !== 'game')
        .map((entry) => entry.sourceId),
    )

    expect(bundle.calendarEntries).toHaveLength(expectedCount)
    expect(gameSourceIds).toEqual(
      new Set(snapshot.leagueSchedule.games.map((game) => game.id)),
    )
    expect(eventSourceIds).toEqual(
      new Set(snapshot.seasonCalendar.events.map((event) => event.id)),
    )
    expect(
      new Set(bundle.calendarEntries.map((entry) => entry.entryId)).size,
    ).toBe(expectedCount)
  })

  it('preserves explicit null managed-team context without managed entries', () => {
    const snapshot = createLeagueSnapshotV2Fixture(null)

    const bundle = createLeaguePresentationBundle(snapshot)

    expect(bundle.managedTeamId).toBeNull()
    expect(
      bundle.calendarEntries.every((entry) => !entry.isManagedTeamEntry),
    ).toBe(true)
  })

  it('rejects a managed team that is not in the hydrated league', () => {
    const snapshot = createLeagueSnapshotV2Fixture()
    const malformed = {
      ...snapshot,
      managedTeamId: parseTeamId('team_foreign_adapter_test'),
    }

    expect(() => adaptLeagueSnapshotV2ToDomain(malformed)).toThrow(
      /must reference exactly one hydrated league team/,
    )
  })

  it('freezes the public projection and normalized presentation foundation', () => {
    const snapshot = createLeagueSnapshotV2Fixture()
    const projection = adaptLeagueSnapshotV2ToDomain(snapshot)
    const bundle = createLeaguePresentationBundle(snapshot)

    expect(Object.isFrozen(projection)).toBe(true)
    expect(Object.isFrozen(projection.league)).toBe(true)
    expect(Object.isFrozen(projection.league.teams)).toBe(true)
    expect(Object.isFrozen(projection.league.players)).toBe(true)
    expect(Object.isFrozen(projection.schedule)).toBe(true)
    expect(Object.isFrozen(projection.schedule.games)).toBe(true)
    expect(Object.isFrozen(projection.schedule.gameDays)).toBe(true)
    expect(Object.isFrozen(projection.seasonCalendar)).toBe(true)
    expect(Object.isFrozen(bundle)).toBe(true)
    expect(Object.isFrozen(bundle.calendarEntries)).toBe(true)
    expect(bundle.calendarEntries.every(Object.isFrozen)).toBe(true)
  })
})

describe('LeagueSnapshotV2 adapter architecture', () => {
  const source = readFileSync(
    new URL('../../src/app/leagueSnapshotDomainAdapter.ts', import.meta.url),
    'utf8',
  )

  it('does not import generation, React, browser storage, or seeded randomness', () => {
    const imports = [...source.matchAll(/\bfrom\s+['"]([^'"]+)['"]/g)].map(
      (match) => match[1],
    )

    expect(imports).not.toEqual(
      expect.arrayContaining([
        expect.stringMatching(
          /react|generation|createseasonfoundation|indexeddb|storage|random/i,
        ),
      ]),
    )
    expect(source).not.toContain('Math.random')
  })
})
