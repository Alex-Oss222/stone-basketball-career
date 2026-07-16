import { afterEach, describe, expect, it, vi } from 'vitest'

import { createLeagueSnapshotV2Fixture } from './leagueSnapshotV2.fixture'

// This DTO is fully materialized before the test resets and mocks the module
// graph. Normal restoration therefore has no reason to create domain content.
const serializedFixture = JSON.parse(
  JSON.stringify(createLeagueSnapshotV2Fixture()),
) as unknown

describe('LeagueSnapshotV2 restoration architecture', () => {
  afterEach(() => {
    vi.doUnmock('../../src/app/commands/createSeasonFoundation')
    vi.doUnmock('../../src/generation/generateSchedule')
    vi.doUnmock('../../src/generation/generateLeague')
    vi.doUnmock('../../src/domain/schedule')
    vi.doUnmock('../../src/random/xoshiro128ss')
    vi.resetModules()
  })

  it('restores stored entities without regeneration or seeded randomization', async () => {
    const createSeasonFoundation = throwingSpy(
      'createSeasonFoundation must not run during V2 restoration',
    )
    const generateSchedule = throwingSpy(
      'schedule generation must not run during V2 restoration',
    )
    const generateLeague = throwingSpy(
      'league generation must not run during V2 restoration',
    )
    const buildOpponentRequirementMatrix = throwingSpy(
      'opponent-requirement generation must not run during V2 restoration',
    )
    const createRandomSource = throwingSpy(
      'seeded randomization must not run during V2 restoration',
    )

    vi.resetModules()
    vi.doMock(
      '../../src/app/commands/createSeasonFoundation',
      async () => {
        const actual = await vi.importActual<
          typeof import('../../src/app/commands/createSeasonFoundation')
        >('../../src/app/commands/createSeasonFoundation')
        return { ...actual, createSeasonFoundation }
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

    const { parseLeagueSnapshotV2 } = await import(
      '../../src/persistence/leagueSnapshotV2'
    )
    const restored = parseLeagueSnapshotV2(serializedFixture)

    expect(restored).toEqual(serializedFixture)
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
