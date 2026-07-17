import type { SegmentedTabOption } from './segmentedTabs'

/** Broadcast filter shared by the schedule surfaces. Only "all" has data now. */
export type BroadcastFilter = 'all' | 'non_televised' | 'local' | 'national'

export const BROADCAST_TABS = [
  { value: 'all', label: 'All' },
  { value: 'non_televised', label: 'Non-televised', comingLater: true },
  { value: 'local', label: 'Local TV', comingLater: true },
  { value: 'national', label: 'National TV', comingLater: true },
] as const satisfies readonly SegmentedTabOption<BroadcastFilter>[]

export function parseBroadcastFilter(value: unknown): BroadcastFilter {
  switch (value) {
    case 'all':
    case 'non_televised':
    case 'local':
    case 'national':
      return value
    default:
      throw new RangeError(`Broadcast filter is unsupported: ${String(value)}`)
  }
}

export function broadcastFilterLabel(broadcast: BroadcastFilter): string {
  switch (broadcast) {
    case 'all':
      return 'All'
    case 'non_televised':
      return 'Non-televised'
    case 'local':
      return 'Local TV'
    case 'national':
      return 'National TV'
    default:
      return assertNever(broadcast)
  }
}

function assertNever(value: never): never {
  throw new RangeError(`Unsupported broadcast filter: ${String(value)}`)
}
