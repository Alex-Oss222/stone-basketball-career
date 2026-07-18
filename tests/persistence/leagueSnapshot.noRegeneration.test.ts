import { afterEach, describe, expect, it, vi } from 'vitest'

import { createLeagueSnapshotFixture } from './leagueSnapshot.fixture'
import { removeGenerationTripwires } from '../helpers/noRegenerationTripwire'

// This DTO is fully materialized before the test resets and mocks the module
// graph. Normal restoration therefore has no reason to create domain content.
const serializedFixture = JSON.parse(
  JSON.stringify(createLeagueSnapshotFixture()),
) as unknown

describe('LeagueSnapshot restoration architecture', () => {
  afterEach(() => {
    removeGenerationTripwires()
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

    const { parseLeagueSnapshot } = await import(
      '../../src/persistence/leagueSnapshot'
    )
    const restored = parseLeagueSnapshot(serializedFixture)

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
