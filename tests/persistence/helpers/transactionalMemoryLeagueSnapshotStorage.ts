import {
  LeagueSnapshotConflictError,
  LeagueSnapshotStorageError,
} from '../../../src/persistence/leagueSnapshotRepository'
import type {
  LeagueSnapshotStorage,
  LeagueSnapshotStorageMutation,
  LeagueSnapshotStoragePhase,
  LeagueSnapshotStorageSlot,
} from '../../../src/persistence/leagueSnapshotRepository'

export type MemoryStorageOperation =
  | 'read'
  | 'write:add'
  | 'write:put'
  | 'clear'
  | 'reread'
  | 'commit'

export interface TransactionalMemoryStorageOptions {
  readonly failPhase?: LeagueSnapshotStoragePhase
  readonly transformReread?: (
    slot: LeagueSnapshotStorageSlot,
  ) => LeagueSnapshotStorageSlot
}

/**
 * A structured-cloning, rollback-capable test double for the repository's
 * single-slot transaction boundary. The mutation remains private until
 * verification and the simulated commit have both succeeded.
 */
export class TransactionalMemoryLeagueSnapshotStorage
  implements LeagueSnapshotStorage
{
  readonly operations: MemoryStorageOperation[] = []

  private committed: MutableStorageSlot
  private failPhase: LeagueSnapshotStoragePhase | undefined
  private transformReread:
    | TransactionalMemoryStorageOptions['transformReread']
    | undefined

  constructor(
    initial: LeagueSnapshotStorageSlot = absentStorageSlot(),
    options: TransactionalMemoryStorageOptions = {},
  ) {
    this.committed = cloneSlot(initial)
    this.failPhase = options.failPhase
    this.transformReread = options.transformReread
  }

  async read(): Promise<LeagueSnapshotStorageSlot> {
    this.operations.push('read')
    this.throwIfConfigured('read')
    return cloneSlot(this.committed)
  }

  async transact<Result>(
    prepare: Parameters<LeagueSnapshotStorage['transact']>[0],
  ): Promise<Result> {
    const draft = cloneSlot(this.committed)
    const plan = prepare(cloneSlot(draft)) as ReturnType<typeof prepare>

    applyMutation(draft, plan.mutation, this.operations, () => {
      this.throwIfConfigured(
        plan.mutation.kind === 'write' ? 'write' : 'clear',
      )
    })

    this.throwIfConfigured('reread')
    this.operations.push('reread')
    const reread = this.transformReread?.(cloneSlot(draft)) ?? draft
    const result = plan.verify(cloneSlot(reread))

    this.throwIfConfigured('commit')
    this.operations.push('commit')
    this.committed = cloneSlot(draft)
    return result as Result
  }

  inspect(): LeagueSnapshotStorageSlot {
    return cloneSlot(this.committed)
  }

  setFailure(phase: LeagueSnapshotStoragePhase | undefined): void {
    this.failPhase = phase
  }

  setRereadTransform(
    transform: TransactionalMemoryStorageOptions['transformReread'],
  ): void {
    this.transformReread = transform
  }

  private throwIfConfigured(phase: LeagueSnapshotStoragePhase): void {
    if (this.failPhase !== phase) return
    throw new LeagueSnapshotStorageError(
      `Deliberate ${phase} failure`,
      undefined,
      phase,
    )
  }
}

interface MutableStorageSlot {
  present: boolean
  value: unknown
}

function applyMutation(
  slot: MutableStorageSlot,
  mutation: LeagueSnapshotStorageMutation,
  operations: MemoryStorageOperation[],
  beforeMutation: () => void,
): void {
  beforeMutation()

  if (mutation.kind === 'clear') {
    operations.push('clear')
    slot.present = false
    slot.value = undefined
    return
  }

  operations.push(`write:${mutation.mode}`)
  if (mutation.mode === 'add' && slot.present) {
    throw new LeagueSnapshotConflictError(
      'The active league location already contains a record',
    )
  }
  slot.present = true
  slot.value = clone(mutation.record)
}

function cloneSlot(slot: LeagueSnapshotStorageSlot): MutableStorageSlot {
  return {
    present: slot.present,
    value: clone(slot.value),
  }
}

export function absentStorageSlot(): {
  readonly present: false
  readonly value: undefined
} {
  return { present: false, value: undefined }
}

export function presentStorageSlot(value: unknown): {
  readonly present: true
  readonly value: unknown
} {
  return { present: true, value }
}

function clone<Value>(value: Value): Value {
  return structuredClone(value)
}
