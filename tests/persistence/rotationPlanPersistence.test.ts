import { describe, expect, it } from 'vitest'
import {
  createLeagueSnapshotRepository,
  createStoredLeagueSnapshotRecord,
} from '../../src/persistence/leagueSnapshotRepository'
import { rotationPlanToSnapshotDto } from '../../src/persistence/leagueSnapshot'
import { MILESTONE_1_LEAGUE_RULES } from '../../src/domain/leagueRules'
import { generateRotationPlan } from '../../src/domain/rotationPlan'
import {
  createLeagueSeasonDomainFixture,
  createLeagueSnapshotFixture,
} from './leagueSnapshot.fixture'
import {
  TransactionalMemoryLeagueSnapshotStorage,
  presentStorageSlot,
} from './helpers/transactionalMemoryLeagueSnapshotStorage'

const { league } = createLeagueSeasonDomainFixture()
const team = league.teams[0]
const roster = league.players.filter((player) => player.teamId === team.id)
const plan = generateRotationPlan({
  teamId: team.id,
  roster,
  rules: MILESTONE_1_LEAGUE_RULES,
})
const planDto = rotationPlanToSnapshotDto(plan)

function setup() {
  const snapshot = createLeagueSnapshotFixture()
  const storage = new TransactionalMemoryLeagueSnapshotStorage(
    presentStorageSlot(createStoredLeagueSnapshotRecord(snapshot)),
  )
  const repository = createLeagueSnapshotRepository(storage)
  return { snapshot, storage, repository }
}

describe('rotation plan persistence', () => {
  it('saves a plan, bumps the revision, and round-trips through storage', async () => {
    const { snapshot, repository } = setup()

    const updated = await repository.updateRotationPlan({
      expectedLeagueId: snapshot.league.id,
      expectedRevision: snapshot.revision,
      plan: planDto,
    })

    expect(updated.revision).toBe(snapshot.revision + 1)
    expect(updated.rotationPlans).toHaveLength(1)
    expect(updated.rotationPlans[0]?.teamId).toBe(team.id)

    const restored = await repository.restore()
    expect(restored.kind).toBe('restored')
    if (restored.kind !== 'restored') {
      throw new Error('Expected a restored snapshot')
    }
    expect(restored.snapshot.rotationPlans).toEqual(updated.rotationPlans)
  })

  it('upserts one plan per team instead of duplicating', async () => {
    const { snapshot, repository } = setup()

    const once = await repository.updateRotationPlan({
      expectedLeagueId: snapshot.league.id,
      expectedRevision: snapshot.revision,
      plan: planDto,
    })
    const twice = await repository.updateRotationPlan({
      expectedLeagueId: once.league.id,
      expectedRevision: once.revision,
      plan: planDto,
    })

    expect(twice.rotationPlans).toHaveLength(1)
    expect(twice.revision).toBe(snapshot.revision + 2)
  })

  it('rejects an invalid plan and leaves the stored snapshot untouched', async () => {
    const { snapshot, storage, repository } = setup()
    const starter = plan.starters[0]
    if (starter === undefined) {
      throw new Error('Generated plan has no starters')
    }
    const brokenDto = {
      ...planDto,
      minuteTargetsSeconds: {
        ...planDto.minuteTargetsSeconds,
        [starter]: (planDto.minuteTargetsSeconds[starter] ?? 0) - 60,
      },
    }

    await expect(
      repository.updateRotationPlan({
        expectedLeagueId: snapshot.league.id,
        expectedRevision: snapshot.revision,
        plan: brokenDto,
      }),
    ).rejects.toThrow()

    const restored = await repository.restore()
    expect(restored.kind).toBe('restored')
    if (restored.kind !== 'restored') {
      throw new Error('Expected a restored snapshot')
    }
    expect(restored.snapshot.revision).toBe(snapshot.revision)
    expect(restored.snapshot.rotationPlans).toEqual([])
    expect(storage.operations).not.toContain('write:put')
  })

  it('rejects a stale-revision save', async () => {
    const { snapshot, repository } = setup()
    await expect(
      repository.updateRotationPlan({
        expectedLeagueId: snapshot.league.id,
        expectedRevision: snapshot.revision + 5,
        plan: planDto,
      }),
    ).rejects.toThrow()
  })
})
