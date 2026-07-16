import { afterEach, describe, expect, it, vi } from 'vitest'
import { createLeagueSnapshotV2Fixture } from './leagueSnapshotV2.fixture'

const snapshotFixture = JSON.parse(
  JSON.stringify(createLeagueSnapshotV2Fixture()),
) as ReturnType<typeof createLeagueSnapshotV2Fixture>
const storedRecordFixture = {
  leagueId: snapshotFixture.league.id,
  snapshot: snapshotFixture,
}

describe('LeagueSnapshot V2 repository restoration architecture', () => {
  afterEach(() => {
    vi.doUnmock('../../src/app/commands/createSeasonFoundation')
    vi.doUnmock('../../src/persistence/migrations/migrateLeagueSnapshotV1ToV2')
    vi.doUnmock('../../src/generation/generateSchedule')
    vi.doUnmock('../../src/generation/generateLeague')
    vi.doUnmock('../../src/domain/schedule')
    vi.doUnmock('../../src/random/xoshiro128ss')
    vi.resetModules()
  })

  it('restores authoritative V2 storage without migration or regeneration', async () => {
    const createSeasonFoundation = throwingSpy(
      'createSeasonFoundation must not run during repository restoration',
    )
    const migrateLeagueSnapshotV1ToV2 = throwingSpy(
      'V1 migration must not run during V2 repository restoration',
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
    vi.doMock(
      '../../src/persistence/migrations/migrateLeagueSnapshotV1ToV2',
      async () => {
        const actual = await vi.importActual<
          typeof import('../../src/persistence/migrations/migrateLeagueSnapshotV1ToV2')
        >('../../src/persistence/migrations/migrateLeagueSnapshotV1ToV2')
        return { ...actual, migrateLeagueSnapshotV1ToV2 }
      },
    )
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
        v1: { present: false, value: undefined },
        v2: {
          present: true,
          value: structuredClone(storedRecordFixture),
        },
      })),
      transact: vi.fn(() => {
        throw new Error('A read-only restore must not open a write transaction')
      }),
    }
    const repository = createLeagueSnapshotRepository(storage)

    const restored = await repository.restore()

    expect(restored).toEqual({
      kind: 'restored-v2',
      snapshot: snapshotFixture,
    })
    expect(storage.read).toHaveBeenCalledOnce()
    expect(storage.transact).not.toHaveBeenCalled()
    expect(createSeasonFoundation).not.toHaveBeenCalled()
    expect(migrateLeagueSnapshotV1ToV2).not.toHaveBeenCalled()
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
