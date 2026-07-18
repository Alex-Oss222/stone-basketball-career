import { afterEach, describe, expect, it, vi } from 'vitest'
import { createLeagueSnapshotFixture } from './leagueSnapshot.fixture'
import { removeGenerationTripwires } from '../helpers/noRegenerationTripwire'

const snapshotFixture = JSON.parse(
  JSON.stringify(createLeagueSnapshotFixture()),
) as ReturnType<typeof createLeagueSnapshotFixture>
const storedRecordFixture = {
  leagueId: snapshotFixture.league.id,
  snapshot: snapshotFixture,
}

describe('LeagueSnapshot repository restoration architecture', () => {
  afterEach(() => {
    removeGenerationTripwires()
  })

  it('restores stored snapshot storage without regeneration', async () => {
    const createSeasonFoundation = throwingSpy(
      'createSeasonFoundation must not run during repository restoration',
    )
    const generateSchedule = throwingSpy(
      'schedule generation must not run during repository restoration',
    )
    const generateLeague = throwingSpy(
      'league generation must not run during repository restoration',
    )
    const buildOpponentRequirementMatrix = throwingSpy(
      'opponent generation must not run during repository restoration',
    )
    const createRandomSource = throwingSpy(
      'seeded randomization must not run during repository restoration',
    )

    vi.resetModules()
    vi.doMock('../../src/app/commands/createSeasonFoundation', async () => {
      const actual = await vi.importActual<
        typeof import('../../src/app/commands/createSeasonFoundation')
      >('../../src/app/commands/createSeasonFoundation')
      return { ...actual, createSeasonFoundation }
    })
    vi.doMock('../../src/generation/generateSchedule', async () => {
      const actual = await vi.importActual<
        typeof import('../../src/generation/generateSchedule')
      >('../../src/generation/generateSchedule')
      return {
        ...actual,
        generateRegularSeasonSchedule: generateSchedule,
        generateSchedule,
      }
    })
    vi.doMock('../../src/generation/generateLeague', async () => {
      const actual = await vi.importActual<
        typeof import('../../src/generation/generateLeague')
      >('../../src/generation/generateLeague')
      return { ...actual, generateLeague }
    })
    vi.doMock('../../src/domain/schedule', async () => {
      const actual = await vi.importActual<
        typeof import('../../src/domain/schedule')
      >('../../src/domain/schedule')
      return { ...actual, buildOpponentRequirementMatrix }
    })
    vi.doMock('../../src/random/xoshiro128ss', async () => {
      const actual = await vi.importActual<
        typeof import('../../src/random/xoshiro128ss')
      >('../../src/random/xoshiro128ss')
      return { ...actual, createRandomSource }
    })

    const { createLeagueSnapshotRepository } = await import(
      '../../src/persistence/leagueSnapshotRepository'
    )
    const storage = {
      read: vi.fn(async () => ({
        present: true,
        value: structuredClone(storedRecordFixture),
      })),
      transact: vi.fn(() => {
        throw new Error('A read-only restore must not open a write transaction')
      }),
    }
    const repository = createLeagueSnapshotRepository(storage)

    const restored = await repository.restore()

    expect(restored).toEqual({
      kind: 'restored',
      snapshot: snapshotFixture,
    })
    expect(storage.read).toHaveBeenCalledOnce()
    expect(storage.transact).not.toHaveBeenCalled()
    expect(createSeasonFoundation).not.toHaveBeenCalled()
    expect(generateSchedule).not.toHaveBeenCalled()
    expect(generateLeague).not.toHaveBeenCalled()
    expect(buildOpponentRequirementMatrix).not.toHaveBeenCalled()
    expect(createRandomSource).not.toHaveBeenCalled()
  })
})

function throwingSpy(message: string) {
  return vi.fn((): never => {
    throw new Error(message)
  })
}
