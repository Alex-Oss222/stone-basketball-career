import {
  LeagueSnapshotConflictError,
  LeagueSnapshotStorageError,
} from '../../../src/persistence/leagueSnapshotRepository'
import type {
  LeagueSnapshotStorage,
  LeagueSnapshotStorageMutation,
  LeagueSnapshotStoragePhase,
  VersionedLeagueSnapshotStorageState,
} from '../../../src/persistence/leagueSnapshotRepository'

export type MemoryStorageOperation =
  | 'read-v1'
  | 'read-v2'
  | 'write-v2:add'
  | 'write-v2:put'
  | 'clear-v1'
  | 'clear-v2'
  | 'reread-v1'
  | 'reread-v2'
  | 'commit'

export interface TransactionalMemoryStorageOptions {
  readonly failPhase?: LeagueSnapshotStoragePhase
  readonly transformReread?: (
    state: VersionedLeagueSnapshotStorageState,
  ) => VersionedLeagueSnapshotStorageState
}

/**
 * A structured-cloning, rollback-capable test double for the repository's
 * transaction boundary. Mutations remain private until verification and the
 * simulated commit have both succeeded.
 */
export class TransactionalMemoryLeagueSnapshotStorage
  implements LeagueSnapshotStorage
{
  readonly operations: MemoryStorageOperation[] = []

  private committed: MutableVersionedState
  private failPhase: LeagueSnapshotStoragePhase | undefined
  private transformReread:
    | TransactionalMemoryStorageOptions['transformReread']
    | undefined

  constructor(
    initial: VersionedLeagueSnapshotStorageState = {
      v1: absentStorageSlot(),
      v2: absentStorageSlot(),
    },
    options: TransactionalMemoryStorageOptions = {},
  ) {
    this.committed = cloneState(initial)
    this.failPhase = options.failPhase
    this.transformReread = options.transformReread
  }

  async read(): Promise<VersionedLeagueSnapshotStorageState> {
    this.operations.push('read-v1', 'read-v2')
    this.throwIfConfigured('read')
    return cloneState(this.committed)
  }

  async transact<Result>(
    prepare: Parameters<LeagueSnapshotStorage['transact']>[0],
  ): Promise<Result> {
    const draft = cloneState(this.committed)
    const plan = prepare(cloneState(draft)) as ReturnType<typeof prepare>

    applyMutation(draft, plan.mutation, this.operations, () => {
      this.throwIfConfigured(
        plan.mutation.kind === 'write-v2' ? 'write-v2' : 'clear',
      )
    })

    this.throwIfConfigured('reread')
    this.operations.push('reread-v1', 'reread-v2')
    const reread = this.transformReread?.(cloneState(draft)) ?? draft
    const result = plan.verify(cloneState(reread))

    this.throwIfConfigured('commit')
    this.operations.push('commit')
    this.committed = cloneState(draft)
    return result as Result
  }

  inspect(): VersionedLeagueSnapshotStorageState {
    return cloneState(this.committed)
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

interface MutableVersionedState {
  v1: MutableStorageSlot
  v2: MutableStorageSlot
}

interface MutableStorageSlot {
  present: boolean
  value: unknown
}

function applyMutation(
  state: MutableVersionedState,
  mutation: LeagueSnapshotStorageMutation,
  operations: MemoryStorageOperation[],
  beforeMutation: () => void,
): void {
  beforeMutation()

  if (mutation.kind === 'clear-both') {
    operations.push('clear-v1', 'clear-v2')
    state.v1 = absentStorageSlot()
    state.v2 = absentStorageSlot()
    return
  }

  operations.push(`write-v2:${mutation.mode}`)
  if (mutation.mode === 'add' && state.v2.present) {
    throw new LeagueSnapshotConflictError(
      'The V2 storage location already contains a record',
    )
  }
  state.v2 = presentStorageSlot(clone(mutation.record))
}

function cloneState(
  state: VersionedLeagueSnapshotStorageState,
): MutableVersionedState {
  return {
    v1: {
      present: state.v1.present,
      value: clone(state.v1.value),
    },
    v2: {
      present: state.v2.present,
      value: clone(state.v2.value),
    },
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
